"""Automated physical GRF 6 direct-read REC/PLAY probe test via KeyStep USB MIDI-to-CV.

Requires the KeyStep GATE output to remain patched into SCOOPER GRF 6.
Gate path is separately checked by test_keystep_gate_path.py. Uses normal
Customizer patch control and audio capture. Restores starting patch.
"""
import json
import sys
import time
from pathlib import Path

import mido
import numpy as np

HERE = Path(__file__).resolve().parent
OUTD = HERE.parent / "outputs" / "recplay-live-test"
OUTD.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, r"C:\Users\admin\Documents\Codex\2026-09-22\files-mentioned-by-the-user-handoff\work\live")
sys.path.insert(0, r"C:\Users\admin\Documents\Codex\2026-09-23\c-users-admin-documents-codex-2026\work\live-v31")
import aira_live
from aira_live import Aira, capture
from v32_check_and_restore import clear, load as safe_load

aira_live.CAP = OUTD
OUT = lambda s, i=0: 10 + 2 * (s - 1) + i
IN = lambda s, i=0: 10 + 4 * (s - 1) + i
LABEL = "grf6_native_direct"


def main():
    a = Aira()
    start = a.snapshot()
    (OUTD / f"{LABEL}_starting_patch.json").write_text(json.dumps(start, indent=2) + "\n")
    ports = [name for name in mido.get_output_names() if "KeyStep 32" in name]
    assert len(ports) == 1, ports
    ks = mido.open_output(ports[0])
    report = {"gate_events": [], "control_source": "physical GRF 6 via firmware readback"}

    def gate(on, t0):
        for channel in range(16):
            ks.send(mido.Message("note_on" if on else "note_off", channel=channel,
                                 note=60, velocity=100 if on else 0))
        report["gate_events"].append({"t": round(time.monotonic() - t0, 3), "on": on})

    try:
        clear(a)
        a.slot(1, [31, 3, 12, 0, 0])
        a.slot(2, [28, 2, 2, 0, 100])
        a.slot(6, [10, 10, 0, 0, 0])
        for out, inp in ((OUT(1), IN(2)), (OUT(2), IN(6, 0)),
                         (OUT(6), 2), (OUT(6), 3), (8, 0), (9, 1)):
            a.cable(out, inp, 1)
        a.write([0x10, 0, 0, 1], [0, 0])
        a.write([0x10, 0, 0, 5], [50, 50])
        a.note(62, True)
        time.sleep(0.3)
        a.note(62, False)
        a.note(60, True)
        time.sleep(0.1)
        a.note(60, False)

        a.param(6, 1, 0)
        _, stale, _ = capture(f"{LABEL}_stale", 1.5)
        report["stale_loop_rms"] = round(float(np.sqrt(np.mean(stale[:, 0] ** 2))), 6)
        if report["stale_loop_rms"] > 0.001:
            report["aborted"] = "existing loop audible before test"
            return report
        a.param(6, 1, 10)

        def during():
            t0 = time.monotonic()
            def wait_until(t):
                while time.monotonic() - t0 < t:
                    time.sleep(0.01)
            print("Tone on; first physical gate at 5 s, second at 8 s.", flush=True)
            wait_until(5)
            gate(True, t0)
            wait_until(5.5)
            gate(False, t0)
            wait_until(8)
            gate(True, t0)
            wait_until(8.5)
            gate(False, t0)
            wait_until(9.5)
            a.param(6, 1, 0)
            report["mute_t"] = round(time.monotonic() - t0, 3)
            print("Source muted; checking for loop.", flush=True)
            wait_until(20)
            gate(True, t0)
            wait_until(23.5)
            gate(False, t0)

        _, audio, rate = capture(LABEL, 30.0, during=during)
        y = audio[:, 0]
        def rms(t1, t2):
            z = y[int(t1 * rate):int(t2 * rate)]
            return round(float(np.sqrt(np.mean(z * z))), 6)
        report["source_on_rms"] = rms(2, 4)
        report["recording_window_rms"] = rms(6, 7.5)
        report["loop_after_mute_rms"] = rms(11, 14)
        report["after_hold_rms"] = rms(25, 29)
        report["no_effect_switch_gate_routes"] = all(a.read([0x10, 0x20, 7, inp], 1) == [0] for inp in (4, 5))
        report["loop_audible_after_mute"] = report["loop_after_mute_rms"] > 0.001
    finally:
        for channel in range(16):
            ks.send(mido.Message("note_off", channel=channel, note=60, velocity=0))
        ks.close()
        a.all_notes_off()
        time.sleep(0.5)
        try:
            report["patch_restored"] = safe_load(a, start)
        except Exception as exc:
            report["patch_restored"] = f"FAILED: {exc!r}"
        (OUTD / f"{LABEL}_report.json").write_text(json.dumps(report, indent=2) + "\n")
        a.close()
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()






