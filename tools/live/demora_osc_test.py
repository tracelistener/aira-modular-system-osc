"""SYSTEM OSC v3.2 on the DEMORA personality (2026-09-30).

Same method as the SCOOPER v3.1 test: oscillator -> MIXER -> main outputs,
compared with the stock SQR. Then every wave, two SYSTEM OSCs at once, and a
burst through DEMORA's own effect. Snapshots the patch first and restores it
with the safe loader (empty, wait, rebuild).
"""
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))        # aira_any.py sits next to this script
from aira_any import AiraAny
import aira_live
from aira_live import capture, analyze
sys.path.insert(0, r"C:\Users\admin\Documents\Codex\2026-09-23\c-users-admin-documents-codex-2026\work\live-v31")
from v32_check_and_restore import clear, load as safe_load

OUTD = Path(r"C:\Users\admin\Documents\aira-demora-test-2026-09-30\test")
OUTD.mkdir(parents=True, exist_ok=True)
aira_live.CAP = OUTD
OUT = lambda s, i=0: 10 + 2 * (s - 1) + i
IN = lambda s, i=0: 10 + 4 * (s - 1) + i
MIDI, SYS, REF, SYS2, MIX = 1, 2, 3, 4, 6
WAVES = ['FM', 'FM+SYNC', 'TRI', 'LOGIC', 'NOISE SAW', 'VOWEL', 'CB']


def et(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def cents(f, ref):
    return round(1200 * math.log2(f / ref), 2) if f and ref else None


def rms(x):
    return round(float(np.sqrt(np.mean(x * x))), 6)


def main():
    a = AiraAny()
    report = {'identity': a.ident, 'pitch': [], 'waves': [], 'alive': []}
    snap = a.snapshot()
    (OUTD / 'pre_snapshot.json').write_text(json.dumps(snap) + '\n')

    def alive(tag):
        try:
            a.read([0x10, 0x10, 0, 0], 5)
            ok = True
        except Exception:
            ok = False
        report['alive'].append([tag, ok])
        assert ok, f'unit stopped answering after {tag}'

    def meas(label, note, secs=1.2, hold=0.3):
        a.note(note, True)
        time.sleep(hold)
        try:
            _, x, rate = capture(label, secs)
        finally:
            a.note(note, False)
        L = analyze(x[:, 0], rate)
        return {'label': label, 'note': note, 'f0': L.get('f0_hz'), 'rms': round(L['rms'], 5),
                'peak': round(L['peak'], 4), 'state': L['state']}

    def gains(p1, p2):
        a.param(MIX, 1, p1)
        a.param(MIX, 2, p2)

    try:
        clear(a)
        a.slot(MIDI, [31, 3, 12, 0, 0])
        a.slot(MIX, [10, 10, 10, 0, 0])
        a.cable(OUT(MIX), 0, 1)
        a.cable(OUT(MIX), 1, 1)
        a.slot(SYS, [28, 2, 2, 0, 100])          # SYSTEM OSC: RANGE 2, WAVE 2 = TRI
        a.slot(REF, [30, 1, 50, 0, 50])          # stock SQR: RANGE 1 (same footage)
        a.cable(OUT(MIDI), IN(SYS), 1)
        a.cable(OUT(MIDI), IN(REF), 1)
        a.cable(OUT(SYS), IN(MIX, 0), 1)
        a.cable(OUT(REF), IN(MIX, 1), 1)
        a.note(62, True); time.sleep(0.2); a.note(62, False); time.sleep(0.3)   # MIDINOTE warm-up
        alive('setup')

        # A: TRI pitch vs equal temperament and vs the stock SQR
        for n in (48, 60, 72):
            gains(10, 0)
            s = meas(f'A_tri_n{n}', n)
            gains(0, 10)
            q = meas(f'A_sqr_n{n}', n)
            row = {'note': n, 'tri_f0': s['f0'], 'sqr_f0': q['f0'], 'tri_rms': s['rms'],
                   'tri_cents_et': cents(s['f0'], et(n)), 'sqr_cents_et': cents(q['f0'], et(n)),
                   'tri_cents_vs_sqr': cents(s['f0'], q['f0'])}
            report['pitch'].append(row)
            print('A', row, flush=True)
        alive('pitch')

        # B: every wave at note 60, SYSTEM OSC only (CB struck through SYNC TRIG IN)
        gains(10, 0)
        for w, name in enumerate(WAVES):
            a.param(SYS, 2, w)
            time.sleep(0.6)
            if name == 'CB':
                a.param(SYS, 3, 50)               # COLOR 50: longer ring
                a.cable(OUT(MIDI, 1), IN(SYS, 3), 1)
                time.sleep(0.3)

                def strike():
                    time.sleep(0.25)
                    a.note(60, True)
                    time.sleep(0.15)
                    a.note(60, False)
                _, x, rate = capture('B_wave_CB', 1.5, during=strike)
                y = x[:, 0]
                r = {'label': 'B_wave_CB', 'note': 60, 'rms_before': rms(y[:int(0.2 * rate)]),
                     'rms_after_strike': rms(y[int(0.3 * rate):int(0.9 * rate)]),
                     'peak': round(float(np.max(np.abs(y))), 4)}
                a.cable(OUT(MIDI, 1), IN(SYS, 3), 0)
                a.param(SYS, 3, 0)
            else:
                r = meas(f'B_wave_{name.replace(" ", "_").replace("+", "")}', 60)
                r['cents_et'] = cents(r['f0'], et(60))
            r['wave'] = name
            report['waves'].append(r)
            print('B', r, flush=True)
            alive(f'wave {name}')
        a.param(SYS, 2, 2)
        time.sleep(0.6)

        # C: two SYSTEM OSCs at once (TRI + FM), stock SQR removed first
        a.cable(OUT(REF), IN(MIX, 1), 0)
        a.cable(OUT(MIDI), IN(REF), 0)
        a.slot(REF, [0, 0, 0, 0, 0])
        time.sleep(1.0)
        a.slot(SYS2, [28, 2, 0, 0, 100])         # second SYSTEM OSC, WAVE 0 = FM
        time.sleep(1.0)
        a.cable(OUT(MIDI), IN(SYS2), 1)
        a.cable(OUT(SYS2), IN(MIX, 1), 1)
        gains(10, 10)
        two = meas('C_two_sys', 60)
        report['two_sys'] = two
        print('C', two, flush=True)
        alive('two SYSTEM OSCs')
        a.cable(OUT(SYS2), IN(MIX, 1), 0)
        a.cable(OUT(MIDI), IN(SYS2), 0)
        a.slot(SYS2, [0, 0, 0, 0, 0])
        time.sleep(1.0)
        gains(0, 0)

        # D: a short TRI burst, first straight out, then through DEMORA's effect
        def burst():
            time.sleep(0.3)
            a.param(MIX, 1, 10)
            time.sleep(0.12)
            a.param(MIX, 1, 0)

        def windows(y, rate):
            seg = lambda t1, t2: rms(y[int(t1 * rate):int(t2 * rate)])
            return {'before': seg(0.0, 0.25), 'burst': seg(0.3, 0.5), 'tail_0.7_1.4': seg(0.7, 1.4),
                    'tail_1.4_2.2': seg(1.4, 2.2), 'tail_2.2_3.0': seg(2.2, 3.0)}

        a.note(60, True)
        _, x, rate = capture('D_burst_direct', 3.0, during=burst)
        report['effect_direct'] = windows(x[:, 0], rate)
        a.cable(OUT(MIX), 0, 0)
        a.cable(OUT(MIX), 1, 0)
        for o, i in ((OUT(MIX), 2), (OUT(MIX), 3), (6, 4), (7, 5), (8, 0), (9, 1)):
            a.cable(o, i, 1)
        time.sleep(0.5)
        _, x, rate = capture('D_burst_effect', 3.0, during=burst)
        a.note(60, False)
        report['effect_path'] = windows(x[:, 0], rate)
        print('D direct', report['effect_direct'], flush=True)
        print('D effect', report['effect_path'], flush=True)
        alive('effect')
    finally:
        a.all_notes_off()
        time.sleep(0.5)
        try:
            report['patch_restored'] = safe_load(a, snap)
        except Exception as exc:
            report['patch_restored'] = f'FAILED: {exc!r}'
        (OUTD / 'demora_osc_test_report.json').write_text(json.dumps(report, indent=2) + '\n')
        a.close()
    print(json.dumps({k: report[k] for k in ('alive', 'patch_restored')}, indent=1), flush=True)


if __name__ == '__main__':
    main()
