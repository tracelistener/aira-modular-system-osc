"""Hardware test of the v3.1 SYSTEM OSCILLATOR on the SCOOPER over USB (user-requested, 2026-09-24).

Uses the proven live helpers (Roland patch sysex with read-back, WinMM capture of OUTPUT 1-2).
Snapshots the user's patch first and restores it at the end. DSP load of every test patch stays < ~260 records.
Sections: A pitch vs stock SQR (notes, RANGE, all waves); B FINE IN; C COLOR IN (+clamp); D SYNC TRIG IN hard sync;
E CB strike; F LFO -> SYNC TRIG IN (the reported crash scenario) with liveness checks.
"""
import json, math, sys, time
from pathlib import Path
import numpy as np
sys.path.insert(0, 'C:/Users/admin/Documents/Codex/2026-09-22/files-mentioned-by-the-user-handoff/work/live')
import aira_live
from aira_live import Aira, capture, analyze

ROOT = Path(__file__).resolve().parents[2]
OUTD = ROOT / 'outputs/wave-selector-v31-inputs/hw-test'
OUTD.mkdir(parents=True, exist_ok=True)
aira_live.CAP = OUTD                     # captures go next to the release
OUT = lambda s, i=0: 10 + 2 * (s - 1) + i
IN = lambda s, i=0: 10 + 4 * (s - 1) + i
MIDI, SYS, REF, AUX, LFO, MIX = 1, 2, 3, 4, 5, 6
WAVES = ['FM', 'FM+SYNC', 'TRI', 'LOGIC', 'NOISE SAW', 'VOWEL', 'CB']
R = []


def et(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def cents(f, ref):
    return 1200 * math.log2(f / ref) if f and ref else None


def peaks(x, rate, n=8, lo=40):
    y = x[int(0.1 * rate):]; y = y - y.mean()
    sp = np.abs(np.fft.rfft(y * np.hanning(len(y)))); fr = np.fft.rfftfreq(len(y), 1 / rate)
    sp[fr < lo] = 0
    out, s = [], sp.copy()
    for _ in range(n):
        k = int(np.argmax(s))
        if s[k] <= 0:
            break
        # parabolic refine
        if 0 < k < len(sp) - 1:
            a_, b_, g_ = np.log(sp[k - 1] + 1e-30), np.log(sp[k] + 1e-30), np.log(sp[k + 1] + 1e-30)
            d = a_ - 2 * b_ + g_; p = 0.5 * (a_ - g_) / d if d else 0
        else:
            p = 0
        out.append((round(float((k + p) * rate / len(y)), 2), round(20 * math.log10(sp[k] / sp.max() + 1e-12), 1)))
        s[max(0, k - 6):k + 7] = 0
    return sorted(out)


def env_slope(x, rate, lo_db=50):
    L = int(0.005 * rate); n = len(x) // L
    db = 20 * np.log10(np.maximum(np.sqrt((x[:n * L].reshape(n, L) ** 2).mean(1)), 1e-9))
    i0 = int(np.argmax(db)) + 2
    idx = [i for i in range(i0, n) if db[i] > db[i0 - 2] - lo_db]
    if len(idx) < 5:
        return None, float(db.max())
    t = np.array(idx) * L / rate
    return float(np.polyfit(t, db[idx], 1)[0]), float(db.max())


a = Aira()
snap = a.snapshot()
(OUTD / 'pre_snapshot.json').write_text(json.dumps(snap) + '\n')


def alive():
    try:
        a.read([0x10, 0x10, 0, 0], 5)
        return True
    except Exception:
        return False


def meas(label, note, secs=1.6, hold=0.3, **meta):
    a.note(note, True); time.sleep(hold)
    try:
        path, x, rate = capture(label, secs)
    finally:
        a.note(note, False)
    L = analyze(x[:, 0], rate)
    r = dict(label=label, note=note, f0=L.get('f0_hz'), rms=round(L['rms'], 5), peak=round(L['peak'], 4),
             state=L['state'], harm_db=L.get('harm_db'), **meta)
    R.append(r)
    print('%-28s n%-3d f0=%-10s rms=%.4f %s' % (label, note, r['f0'], r['rms'],
                                               {k: v for k, v in meta.items() if k not in ('expect_hz',)}), flush=True)
    return r, x, rate


def gains(p1, p2):
    a.param(MIX, 1, p1); a.param(MIX, 2, p2)


try:
    a.all_notes_off(); a.blank()
    a.slot(MIDI, [31, 3, 12, 0, 0])
    a.slot(MIX, [10, 10, 10, 0, 0])
    a.cable(OUT(MIX), 0, 1); a.cable(OUT(MIX), 1, 1)
    a.slot(SYS, [28, 2, 2, 0, 100])                 # SYSTEM OSC: RANGE 2 (32'), WAVE 2 = TRI
    a.slot(REF, [30, 1, 50, 0, 50])                 # stock SQR: RANGE 1 (32'), FINE centre, PW 0, LEVEL 50
    a.cable(OUT(MIDI), IN(SYS), 1); a.cable(OUT(MIDI), IN(REF), 1)
    a.cable(OUT(SYS), IN(MIX, 0), 1); a.cable(OUT(REF), IN(MIX, 1), 1)
    gains(10, 0)
    meas('warmup', 61)
    # ---- A1: pitch across the keyboard, SYSTEM TRI vs stock SQR
    for n in (36, 48, 60, 72, 84):
        gains(10, 0); rs, _, _ = meas('A1_sys_tri_n%d' % n, n, part='A1', osc='SYS TRI')
        gains(0, 10); rq, _, _ = meas('A1_sqr_n%d' % n, n, part='A1', osc='stock SQR')
        rs['cents_et'] = cents(rs['f0'], et(n)); rq['cents_et'] = cents(rq['f0'], et(n))
        rs['cents_vs_sqr'] = cents(rs['f0'], rq['f0'])
    # ---- A2: RANGE footage pairs at note 60 (SYSTEM P1 1..5 vs SQR P1 0..4)
    for ps, pq in ((1, 0), (3, 2), (4, 3), (5, 4)):
        a.param(SYS, 1, ps); a.param(REF, 1, pq)
        gains(10, 0); rs, _, _ = meas('A2_sys_range%d' % ps, 60, part='A2', sys_p1=ps)
        gains(0, 10); rq, _, _ = meas('A2_sqr_range%d' % pq, 60, part='A2', sqr_p1=pq)
        rs['cents_vs_sqr'] = cents(rs['f0'], rq['f0'])
    a.param(SYS, 1, 2); a.param(REF, 1, 1)
    # ---- A3: every wave at notes 48 and 72 (autocorrelation f0; CB checked by spectral peaks)
    gains(10, 0)
    for w, name in enumerate(WAVES):
        a.param(SYS, 2, w); time.sleep(0.3)
        for n in (48, 72):
            r, x, rate = meas('A3_%s_n%d' % (name.replace(' ', '').replace('+', ''), n), n, part='A3', wave=name)
            r['cents_et'] = cents(r['f0'], et(n))
            r['peaks'] = peaks(x[:, 0], rate)
    a.param(SYS, 2, 2)
    a.slot(REF, [0, 0, 0, 0, 0])                    # stock SQR no longer needed
    # ---- B: FINE IN fed with the MIDINOTE CV (note/120): expected +note/120 semitone = +10*note/12 cents
    a.cable(OUT(MIDI), IN(SYS, 1), 1)
    for n in (60, 72):
        r, _, _ = meas('B_fine_cv_n%d' % n, n, part='B')
        r['cents_et'] = cents(r['f0'], et(n)); r['expect_cents'] = 100 * n / 120
    a.cable(OUT(MIDI), IN(SYS, 1), 0)
    # ---- C: COLOR IN (TRI): knob 0 + CV 0.5 (note 60) vs knob 50; knob 100 + CV (clamp) vs knob 100
    a.param(SYS, 3, 50); rc50, _, _ = meas('C_knob50', 60, part='C')
    a.param(SYS, 3, 0); a.cable(OUT(MIDI), IN(SYS, 2), 1); rcv, _, _ = meas('C_knob0_cv05', 60, part='C')
    a.param(SYS, 3, 100); rclamp, _, _ = meas('C_knob100_cv05', 60, part='C')
    a.cable(OUT(MIDI), IN(SYS, 2), 0); rc100, _, _ = meas('C_knob100', 60, part='C')
    a.param(SYS, 3, 0)
    # ---- D: SYNC TRIG IN hard sync: stock SAW one octave down (64') drives it
    a.slot(AUX, [29, 0, 50, 0, 50])
    a.cable(OUT(MIDI), IN(AUX), 1)
    rfree, _, _ = meas('D_tri_unsynced_n60', 60, part='D')
    a.cable(OUT(AUX), IN(SYS, 3), 1)
    rsync, _, _ = meas('D_tri_synced_to_saw64_n60', 60, part='D', expect_hz=et(60) / 2)
    a.param(AUX, 2, 80); rdet, _, _ = meas('D_synced_saw_fine80_n60', 60, part='D')
    a.param(AUX, 2, 50)
    a.cable(OUT(AUX), IN(SYS, 3), 0); a.cable(OUT(MIDI), IN(AUX), 0)
    a.slot(AUX, [0, 0, 0, 0, 0])
    # ---- E: CB struck from SYNC TRIG IN (gate), COLOR 70
    a.param(SYS, 2, 6); a.param(SYS, 3, 70); time.sleep(0.3)
    a.cable(OUT(MIDI, 1), IN(SYS, 3), 1)
    r, x, rate = meas('E_cb_strike_n60', 60, secs=1.8, hold=0.02, part='E')
    r['peaks'] = peaks(x[:, 0], rate); r['slope_db_s'], r['peak_db'] = env_slope(x[:, 0], rate)
    a.cable(OUT(MIDI, 1), IN(SYS, 3), 0)
    r, x, rate = meas('E_cb_no_trigger_n62', 62, secs=1.0, part='E', note_='no cable into SYNC TRIG IN -> expect silence')
    a.param(SYS, 3, 0)
    # ---- F: LFO -> SYNC TRIG IN (reported crash scenario), heaviest waves; liveness after each
    a.slot(LFO, [1, 0, 50, 100, 50])
    a.cable(OUT(LFO), IN(SYS, 3), 1)
    for w in (2, 6, 4, 5):                          # TRI, CB, NOISE SAW, VOWEL
        a.param(SYS, 2, w); time.sleep(0.3)
        r, _, _ = meas('F_lfo_sync_%s' % WAVES[w].replace(' ', ''), 60, secs=2.0, part='F', wave=WAVES[w])
        r['alive_after'] = alive()
        print('   alive:', r['alive_after'], flush=True)
    a.param(LFO, 2, 100)                            # fastest LFO rate
    r, _, _ = meas('F_lfo_fast_sync_VOWEL', 60, secs=2.0, part='F', wave='VOWEL', lfo_rate=100)
    r['alive_after'] = alive()
    a.cable(OUT(LFO), IN(SYS, 2), 1)                # LFO also into COLOR IN
    r, _, _ = meas('F_lfo_sync_and_color_VOWEL', 60, secs=2.0, part='F', wave='VOWEL')
    r['alive_after'] = alive()
    a.cable(OUT(LFO), IN(SYS, 2), 0); a.cable(OUT(LFO), IN(SYS, 3), 0)
    a.slot(LFO, [0, 0, 0, 0, 0]); a.param(SYS, 2, 2)
finally:
    a.all_notes_off(); time.sleep(0.5)
    try:
        ok = a.restore(snap)
    except Exception as e:
        ok = False; print('restore error:', repr(e))
    (OUTD / 'results.json').write_text(json.dumps(dict(restored=ok, results=R), indent=1) + '\n')
    a.close()
    print('RESTORED user patch' if ok else 'RESTORE INCOMPLETE (see pre_snapshot.json)', flush=True)
