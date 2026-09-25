"""v3.3 hardware test: does a gate into the SCOOPER's SCATTER control input (efx sw2) work REC/PLAY?

Patch: MIDINOTE -> SYSTEM OSC TRI -> MIXER -> SCOOPER in 1/2 -> SCOOPER out 1/2 -> OUTPUT 1/2,
       MIDINOTE GATE -> SCOOPER efx sw2 (main input 5). SCOOPER PITCH/FILTER set to centre (50) for the test.
Sequence: short gate (REC) -> 1.5 s tone recorded -> short gate (PLAY) -> source muted -> is the loop playing?
          -> gate held 3 s (delete) -> silence? Snapshot/restore with the safe clear-then-rebuild method.
"""
import json, math, sys, time
from pathlib import Path
import numpy as np
sys.path.insert(0, 'C:/Users/admin/Documents/Codex/2026-09-22/files-mentioned-by-the-user-handoff/work/live')
sys.path.insert(0, str(Path(__file__).resolve().parent))
import aira_live
from aira_live import Aira, capture
from v32_check_and_restore import load as safe_load, clear

ROOT = Path(__file__).resolve().parents[2]
OUTD = ROOT / 'outputs/wave-selector-v33-recplay/hw-test'
OUTD.mkdir(parents=True, exist_ok=True)
aira_live.CAP = OUTD
OUT = lambda s, i=0: 10 + 2 * (s - 1) + i
IN = lambda s, i=0: 10 + 4 * (s - 1) + i
MIDI, SYS, MIX = 1, 2, 6
EFX_IN1, EFX_IN2, EFX_SW2, EFX_OUT1, EFX_OUT2 = 2, 3, 5, 8, 9


def level(label, secs=1.5, wait=0.4):
    time.sleep(wait)
    _, x, rate = capture(label, secs)
    y = x[int(0.05 * rate):, 0]
    sp = np.abs(np.fft.rfft(y * np.hanning(len(y)))); fr = np.fft.rfftfreq(len(y), 1 / rate)
    k = int(np.argmax(np.where(fr > 40, sp, 0)))
    return dict(rms=round(float(np.sqrt(np.mean(y * y))), 5), peak_hz=round(float(fr[k]), 1))


def gate(a, secs):
    a.note(60, True); time.sleep(secs); a.note(60, False)


def main():
    a = Aira()
    start = a.snapshot()
    (OUTD / 'start_snapshot.json').write_text(json.dumps(start) + '\n')
    rep = {}
    try:
        clear(a)
        a.slot(MIDI, [31, 3, 12, 0, 0]); a.slot(SYS, [28, 2, 2, 0, 100]); a.slot(MIX, [10, 10, 0, 0, 0])
        for o, i in ((OUT(MIDI), IN(SYS)), (OUT(SYS), IN(MIX, 0)), (OUT(MIX), EFX_IN1), (OUT(MIX), EFX_IN2),
                     (EFX_OUT1, 0), (EFX_OUT2, 1)):
            a.cable(o, i, 1)
        a.write([0x10, 0, 0, 1], [0, 0])               # SYNC TRIG / SCATTER buttons off
        a.write([0x10, 0, 0, 5], [50, 50])             # PITCH and FILTER centred so the loop plays back as recorded
        a.note(62, True); time.sleep(0.3); a.note(62, False)
        a.note(60, True); time.sleep(0.1); a.note(60, False)   # TRI at C4 before the gate is patched
        a.cable(OUT(MIDI, 1), EFX_SW2, 1)             # from now on every note = a REC/PLAY press
        time.sleep(0.5)
        rep['1_source_on_no_loop'] = level('1_source_on')
        gate(a, 0.06)                                  # tap 1: REC
        time.sleep(1.5)                                # records 1.5 s of the tone
        gate(a, 0.06)                                  # tap 2: PLAY
        time.sleep(0.2)
        a.param(MIX, 1, 0)                             # mute the source: only a recorded loop can sound now
        rep['2_after_taps_source_muted'] = level('2_after_taps_muted', 2.0, 0.6)
        gate(a, 3.0)                                   # held gate = hold REC/PLAY = delete
        rep['3_after_hold'] = level('3_after_hold', 1.5, 0.6)
        a.param(MIX, 1, 10)
        rep['4_source_back'] = level('4_source_back')
        try:
            a.read([0x10, 0x10, 0, 0], 5); rep['alive'] = True
        except Exception:
            rep['alive'] = False
    finally:
        a.all_notes_off(); time.sleep(0.5)
        try:
            rep['restored'] = safe_load(a, start)
        except Exception as e:
            rep['restored'] = 'FAILED: %r' % e
        (OUTD / 'report.json').write_text(json.dumps(rep, indent=1) + '\n')
        a.close()
    return rep


if __name__ == '__main__':
    r = main()
    print(json.dumps(r, indent=1))
    loop = r.get('2_after_taps_source_muted', {}).get('rms', 0) > 1e-3
    gone = r.get('3_after_hold', {}).get('rms', 1) < 1e-3
    print('LOOP PLAYED AFTER GATE TAPS:', loop, '| DELETED BY HELD GATE:', gone)
