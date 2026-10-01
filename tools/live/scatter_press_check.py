"""Monitored SCATTER press check on recplay-grf6-customizer-restored.

A tone feeds the looper while the user presses SCATTER. Any phantom REC/PLAY
press would start a recording; after the presses the tone keeps running long
enough for such a recording to close at maximum length and play. Then the tone
is muted: an audible loop means a phantom press happened. The looper is cleared
if needed and the starting patch is restored.
"""
import json
import sys
import time

import mido
import numpy as np

WORK = r"C:\Users\admin\Documents\Codex\2026-09-29\files-pasted-by-the-user-i\work"
sys.path.insert(0, WORK)
import test_grf6_native_direct as base

LABEL = "claude_scatter_press_" + time.strftime("%Y%m%d-%H%M%S")
DIAGNOSTIC = {0x494E4401, 0x494E4402, 0x494E4403}


def rms(x):
    return round(float(np.sqrt(np.mean(x * x))), 6)


def main():
    a = base.Aira()
    report = {"label": LABEL}

    def word(low, high):
        d = [a.read(low, 3), a.read(high, 3)]
        return (d[0][0] << 14 | d[0][1] << 7 | d[0][2]) | (d[1][0] << 14 | d[1][1] << 7 | d[1][2]) << 21

    assert word([16, 33, 0, 0], [16, 33, 0, 3]) not in DIAGNOSTIC
    assert word([16, 33, 0, 6], [16, 33, 0, 9]) not in DIAGNOSTIC
    start = a.snapshot()
    (base.OUTD / f"{LABEL}_starting_patch.json").write_text(json.dumps(start, indent=2) + "\n")
    assert start[2 + 7]["data"] == [0] * 34, "GRF6 must remain completely unrouted"
    assert start[0]["data"][2] == 0, "SCATTER effect must start off"
    ports = [n for n in mido.get_output_names() if "KeyStep 32" in n]
    assert len(ports) == 1, ports
    ks = mido.open_output(ports[0])

    def gate(on):
        for ch in range(16):
            ks.send(mido.Message("note_on" if on else "note_off", channel=ch,
                                 note=60, velocity=100 if on else 0))

    def pitch(n):
        a.note(n, True)
        time.sleep(0.03)
        a.note(n, False)

    try:
        base.clear(a)
        a.slot(1, [31, 3, 12, 0, 0])
        a.slot(2, [28, 2, 2, 0, 100])
        a.slot(6, [10, 0, 0, 0, 0])
        for out, inp in ((base.OUT(1), base.IN(2)), (base.OUT(2), base.IN(6)),
                         (base.OUT(6), 2), (base.OUT(6), 3), (8, 0), (9, 1)):
            a.cable(out, inp, 1)
        a.write([0x10, 0, 0, 1], [0, 0])
        a.write([0x10, 0, 0, 5], [50, 50])
        assert a.read([0x10, 0x20, 7, 0], 34) == [0] * 34
        # Clear any existing loop with the native hold, then check silence.
        gate(False)
        time.sleep(0.3)
        gate(True)
        time.sleep(3.5)
        gate(False)
        time.sleep(0.6)
        pitch(62)
        pitch(60)
        _, before, _ = base.capture(f"{LABEL}_before", 1.5)
        report["before_rms"] = rms(before[:, 0])
        if report["before_rms"] > 0.001:
            report["aborted"] = "loop audible before the press window"
            return
        a.param(6, 1, 10)  # tone on: the user's cue
        t0 = time.monotonic()
        last = a.read([0x10, 0, 0, 2], 1)[0]
        toggles = []
        while True:
            value = a.read([0x10, 0, 0, 2], 1)[0]
            now = time.monotonic() - t0
            if value != last:
                toggles.append([round(now, 2), value])
                last = value
            if len(toggles) >= 20 and now - toggles[-1][0] > 4:
                break
            if toggles and now - toggles[-1][0] > 20:
                break
            if not toggles and now > 90:
                break
            if now > 180:
                break
            time.sleep(0.05)
        report["scatter_toggles_seen"] = len(toggles)
        report["toggles"] = toggles
        report["scatter_final"] = last
        # Keep the tone on so a phantom-started recording closes (10 s max) and plays.
        end = (toggles[-1][0] if toggles else time.monotonic() - t0) + 12.0
        while time.monotonic() - t0 < end:
            time.sleep(0.1)
        a.param(6, 1, 0)
        time.sleep(0.3)
        _, after, _ = base.capture(f"{LABEL}_after_mute", 3.0)
        report["after_mute_rms"] = rms(after[:, 0])
        report["phantom_loop_detected"] = report["after_mute_rms"] > 0.001
        report["grf6_unrouted_after"] = a.read([0x10, 0x20, 7, 0], 34) == [0] * 34
        if report["phantom_loop_detected"]:
            gate(True)
            time.sleep(3.5)
            gate(False)
            time.sleep(0.6)
            _, cleared, _ = base.capture(f"{LABEL}_cleared", 1.5)
            report["after_clear_rms"] = rms(cleared[:, 0])
    finally:
        gate(False)
        ks.close()
        a.all_notes_off()
        time.sleep(0.5)
        try:
            report["patch_restored"] = base.safe_load(a, start)
        except Exception as exc:
            report["patch_restored"] = f"FAILED: {exc!r}"
        (base.OUTD / f"{LABEL}_report.json").write_text(json.dumps(report, indent=2) + "\n")
        a.close()
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
