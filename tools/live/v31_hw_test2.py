"""v3.1 hardware test, pass 2: parity with the stock SQR/SAW jacks, CB strike, slot placement, stress, shipped presets.
Snapshot -> blank -> tests -> restore (in finally). Every patch stays <= 285 DSP records (known-good limit ~303)."""
import json, math, sys, time
from pathlib import Path
import numpy as np
sys.path.insert(0, 'C:/Users/admin/Documents/Codex/2026-09-22/files-mentioned-by-the-user-handoff/work/live')
import aira_live
from aira_live import Aira, capture, analyze

ROOT = Path(__file__).resolve().parents[2]
REL = ROOT / 'outputs/wave-selector-v31-inputs'
OUTD = REL / 'hw-test'
aira_live.CAP = OUTD
OUT = lambda s, i=0: 10 + 2 * (s - 1) + i
IN = lambda s, i=0: 10 + 4 * (s - 1) + i
WAVES = ['FM', 'FM+SYNC', 'TRI', 'LOGIC', 'NOISE SAW', 'VOWEL', 'CB']
R = {}


def et(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def cents(f, r):
    return round(1200 * math.log2(f / r), 3) if f and r else None


def line(x, rate, f_guess, span=0.012):
    """Precise frequency of the spectral line near f_guess (Hann DTFT maximum, golden section)."""
    y = x[int(0.15 * rate):]; y = (y - y.mean()) * np.hanning(len(y)); t = np.arange(len(y)) / rate
    mag = lambda f: abs(np.dot(y, np.exp(-2j * np.pi * f * t)))
    fs = np.linspace(f_guess * (1 - span), f_guess * (1 + span), 121); m = [mag(f) for f in fs]; k = int(np.argmax(m))
    a_, b_ = fs[max(k - 1, 0)], fs[min(k + 1, 120)]; g = (math.sqrt(5) - 1) / 2
    c_, d_ = b_ - g * (b_ - a_), a_ + g * (b_ - a_)
    for _ in range(40):
        if mag(c_) > mag(d_):
            b_ = d_
        else:
            a_ = c_
        c_, d_ = b_ - g * (b_ - a_), a_ + g * (b_ - a_)
    return round((a_ + b_) / 2, 4)


def fund(x, rate, lo, hi):
    """Strongest spectral line between lo and hi Hz, refined with line()."""
    y = x[int(0.15 * rate):]; y = y - y.mean()
    sp = np.abs(np.fft.rfft(y * np.hanning(len(y)))); fr = np.fft.rfftfreq(len(y), 1 / rate)
    sp[(fr < lo) | (fr > hi)] = 0
    return line(x, rate, float(fr[int(np.argmax(sp))]), 0.004)


a = Aira()
snap = a.snapshot()
(OUTD / 'pre_snapshot_pass2.json').write_text(json.dumps(snap) + '\n')


def alive():
    try:
        a.read([0x10, 0x10, 0, 0], 5); return True
    except Exception:
        return False


def grab(label, note, secs=1.6, hold=0.3):
    a.note(note, True); time.sleep(hold)
    try:
        _, x, rate = capture(label, secs)
    finally:
        a.note(note, False)
    time.sleep(0.05)
    return x[:, 0], rate


def build(slots, cables):
    a.all_notes_off(); a.blank()
    for s, v in sorted(slots.items()):
        a.slot(s, v)
    for o, i in cables:
        a.cable(o, i, 1)


def log(key, **kw):
    R[key] = kw
    print(key, json.dumps(kw), flush=True)


try:
    # ================= T1: stock SAW / SQR / SYSTEM tuning at 64' and 32' (mixer in0 SYS, in1 SQR, in2 SAW)
    MIDI, SYS, SAW, SQR, MIX = 1, 2, 3, 4, 6
    build({MIDI: [31, 3, 12, 0, 0], SYS: [28, 1, 2, 0, 100], SAW: [29, 0, 50, 0, 50], SQR: [30, 1, 50, 0, 50],
           MIX: [10, 0, 0, 0, 0]},
          [(OUT(MIDI), IN(SYS)), (OUT(MIDI), IN(SAW)), (OUT(MIDI), IN(SQR)),
           (OUT(SYS), IN(MIX, 0)), (OUT(SQR), IN(MIX, 1)), (OUT(SAW), IN(MIX, 2)), (OUT(MIX), 0), (OUT(MIX), 1)])
    def solo(k):
        for j in range(3):
            a.param(MIX, j + 1, 10 if j == k else 0)
    solo(2); grab('warm2', 62)
    x, r_ = grab('T1_saw64_n60', 60); f_saw64 = line(x, r_, et(60) / 2); log('T1_saw64_n60', f=f_saw64, cents_et=cents(f_saw64, et(60) / 2))
    a.param(SAW, 1, 1)
    x, r_ = grab('T1_saw32_n60', 60); f = line(x, r_, et(60)); log('T1_saw32_n60', f=f, cents_et=cents(f, et(60)))
    a.param(SAW, 1, 0)
    solo(1); x, r_ = grab('T1_sqr32_n60', 60); f = line(x, r_, et(60)); log('T1_sqr32_n60', f=f, cents_et=cents(f, et(60)))
    solo(0); x, r_ = grab('T1_sys64_n60', 60); f = line(x, r_, et(60) / 2); log('T1_sys64_n60', f=f, cents_et=cents(f, et(60) / 2))
    # ================= T2: hard-sync parity. Master = stock SAW 64'. Slaves: SYSTEM TRI 32' and stock SQR 32'
    a.param(SYS, 1, 2)
    a.cable(OUT(SAW), IN(SYS, 3), 1); a.cable(OUT(SAW), IN(SQR, 3), 1)
    for fine in (50, 80):
        a.param(SAW, 2, fine)
        solo(2); x, r_ = grab('T2_master_saw_fine%d' % fine, 60); fm = line(x, r_, et(60) / 2 * 2 ** ((fine - 50) / 1200), 0.02)
        solo(0); x, r_ = grab('T2_sys_synced_fine%d' % fine, 60); fs_ = line(x, r_, 2 * fm, 0.003)
        solo(1); x, r_ = grab('T2_sqr_synced_fine%d' % fine, 60); fq = line(x, r_, 2 * fm, 0.003)
        log('T2_sync_fine%d' % fine, master=fm, sys_line_over2=round(fs_ / 2, 4), sqr_line_over2=round(fq / 2, 4),
            sys_vs_master_c=cents(fs_ / 2, fm), sqr_vs_master_c=cents(fq / 2, fm))
    a.param(SAW, 2, 50)
    a.cable(OUT(SAW), IN(SYS, 3), 0); a.cable(OUT(SAW), IN(SQR, 3), 0)
    # SYSTEM SYNC OUT (out 1) as master for the stock SQR: SYSTEM at 64', SQR at 32'
    a.param(SYS, 1, 1); a.cable(OUT(SYS, 1), IN(SQR, 3), 1)
    solo(1); x, r_ = grab('T2_sqr_synced_to_sys_syncout', 60); fq = line(x, r_, et(60), 0.003)
    log('T2_sysout_master', sqr_line_over2=round(fq / 2, 4), vs_sys64_c=cents(fq / 2, et(60) / 2))
    a.cable(OUT(SYS, 1), IN(SQR, 3), 0); a.param(SYS, 1, 2)
    # ================= T3: FINE IN parity (MIDINOTE CV into FINE IN of both)
    a.cable(OUT(MIDI), IN(SQR, 1), 1); a.cable(OUT(MIDI), IN(SYS, 1), 1)
    for n in (60, 72):
        solo(1); x, r_ = grab('T3_sqr_fineCV_n%d' % n, n); fq = fund(x, r_, et(n) * 0.7, et(n) * 1.9)
        solo(0); x, r_ = grab('T3_sys_fineCV_n%d' % n, n); fs_ = fund(x, r_, et(n) * 0.7, et(n) * 1.9)
        log('T3_fine_n%d' % n, sqr_shift_c=cents(fq, et(n) * 2 ** (-0.38 / 1200)), sys_shift_c=cents(fs_, et(n)),
            expected_c=round(100 * n / 120, 2))
    a.cable(OUT(MIDI), IN(SQR, 1), 0); a.cable(OUT(MIDI), IN(SYS, 1), 0)
    # ================= T4: stock SQR COLOR IN (pulse width): knob 50 vs knob 0 + CV 0.5 vs knob 100 + CV 0.5
    def duty(x):
        y = x[int(0.15 * 48000):]; th = (np.percentile(y, 2) + np.percentile(y, 98)) / 2
        return round(float((y > th).mean()), 4)
    solo(1)
    a.param(SQR, 3, 50); x, _ = grab('T4_sqr_color50', 60); d50 = duty(x)
    a.param(SQR, 3, 0); x, _ = grab('T4_sqr_color0', 60); d0 = duty(x)
    a.cable(OUT(MIDI), IN(SQR, 2), 1)
    x, _ = grab('T4_sqr_color0_cv05', 60); d0cv = duty(x)
    a.param(SQR, 3, 100); x, _ = grab('T4_sqr_color100_cv05', 60); d100cv = duty(x); rms100cv = float(np.sqrt((x ** 2).mean()))
    a.cable(OUT(MIDI), IN(SQR, 2), 0)
    x, _ = grab('T4_sqr_color100', 60); d100 = duty(x); rms100 = float(np.sqrt((x ** 2).mean()))
    log('T4_sqr_color', duty_k0=d0, duty_k50=d50, duty_k0_cv05=d0cv, duty_k100=d100, duty_k100_cv05=d100cv,
        rms_k100=round(rms100, 5), rms_k100_cv05=round(rms100cv, 5))
    a.param(SQR, 3, 0)
    # ================= T5: CB strike (note sent during the capture), level vs TRI, decay vs model
    solo(0); a.param(SYS, 2, 2); x, _ = grab('T5_tri_ref_n60', 60); tri_peak = float(np.abs(x[4800:]).max())
    a.param(SYS, 2, 6); time.sleep(0.3)
    a.cable(OUT(MIDI, 1), IN(SYS, 3), 1)
    exp = {0: 0.072, 70: 0.545}
    for col in (70, 0):
        a.param(SYS, 3, col); time.sleep(0.2)
        for n in (60, 72):
            def hit():
                time.sleep(0.25); a.note(n, True); time.sleep(0.06); a.note(n, False)
            _, xx, rate = capture('T5_cb_color%d_n%d' % (col, n), 1.4, during=hit); x = xx[:, 0]
            L = int(0.002 * rate); nb = len(x) // L
            env = 20 * np.log10(np.maximum(np.sqrt((x[:nb * L].reshape(nb, L) ** 2).mean(1)), 1e-9))
            i0 = int(np.argmax(env)); below = np.where(env[i0:] < env[i0] - 40)[0]
            t40 = below[0] * L / rate if len(below) else None
            seg = x[i0 * L:i0 * L + int(0.25 * rate)]
            f1 = et(n)                     # CB f1 at RANGE 32' = the note's pitch; f2 = 1.498 f1
            l3 = line(np.concatenate([np.zeros(int(0.15 * rate)), seg]), rate, 3 * f1, 0.01)
            l2 = line(np.concatenate([np.zeros(int(0.15 * rate)), seg]), rate, 1.498 * f1, 0.01)
            log('T5_cb_color%d_n%d' % (col, n), attack_peak=round(float(np.abs(x).max()), 4), tri_peak=round(tri_peak, 4),
                cb_vs_tri_db=round(20 * math.log10(np.abs(x).max() / tri_peak), 1), t_minus40dB_s=t40,
                model_t_minus60dB_s=exp[col], line_3f1=l3, expect_3f1=round(3 * f1, 2), line_f2=l2, expect_f2=round(1.498 * f1, 2))
    a.cable(OUT(MIDI, 1), IN(SYS, 3), 0)
    # CB with nothing in SYNC TRIG IN must stay silent; CB retriggered by a 4 Hz LFO keeps striking
    x, _ = grab('T5_cb_untriggered', 60, 1.0); log('T5_cb_untriggered', rms=round(float(np.sqrt((x ** 2).mean())), 6))
    a.param(SYS, 3, 0); a.param(SYS, 2, 2)

    # ================= T6: slot placement (slot 1 hosts the RANGE table area; slot 6 is the last area); two instances
    for sys_slot, midi_slot in ((1, 2), (6, 1)):
        mix = 5 if sys_slot == 6 else 6
        build({midi_slot: [31, 3, 12, 0, 0], sys_slot: [28, 2, 0, 0, 100], mix: [10, 10, 0, 0, 0]},
              [(OUT(midi_slot), IN(sys_slot)), (OUT(midi_slot, 1), IN(sys_slot, 3)), (OUT(sys_slot), IN(mix, 0)),
               (OUT(mix), 0), (OUT(mix), 1)])
        grab('warm6', 62, 0.6)
        res = {}
        for w in range(7):
            a.param(sys_slot, 2, w); time.sleep(0.3)
            lab = 'T6_slot%d_%s' % (sys_slot, WAVES[w].replace(' ', '').replace('+', ''))
            if w == 6:
                a.param(sys_slot, 3, 70); time.sleep(0.2)
                def hit6():
                    time.sleep(0.2); a.note(60, True); time.sleep(0.06); a.note(60, False)
                _, xx, r_ = capture(lab, 1.2, during=hit6); x = xx[:, 0]
                i0 = int(np.argmax(np.abs(x)))
                seg = np.concatenate([np.zeros(int(0.15 * r_)), x[i0:i0 + int(0.25 * r_)]])
                res[WAVES[w]] = dict(peak=round(float(np.abs(x).max()), 4), line_f2=line(seg, r_, 1.498 * et(60), 0.01),
                                     expect_f2=round(1.498 * et(60), 2))
                a.param(sys_slot, 3, 0)
            else:
                x, r_ = grab(lab, 60, 1.2)
                f = line(x, r_, et(60), 0.02); res[WAVES[w]] = dict(f=f, c=cents(f, et(60)), rms=round(float(np.sqrt((x[7200:] ** 2).mean())), 4))
        a.param(sys_slot, 2, 2)
        for rg in (1, 5):
            a.param(sys_slot, 1, rg); x, r_ = grab('T6_slot%d_range%d' % (sys_slot, rg), 60, 1.2)
            mult = {1: 0.5, 5: 8}[rg]; f = line(x, r_, et(60) * mult, 0.02); res['RANGE%d' % rg] = dict(f=f, c=cents(f, et(60) * mult))
        log('T6_sys_in_slot%d' % sys_slot, alive=alive(), **res)
    # two instances, different RANGE, different waves: slot 1 TRI 32', slot 6 FM 16'
    build({1: [28, 2, 2, 0, 100], 2: [31, 3, 12, 0, 0], 6: [28, 3, 0, 0, 100], 5: [10, 0, 0, 0, 0]},
          [(OUT(2), IN(1)), (OUT(2), IN(6)), (OUT(1), IN(5, 0)), (OUT(6), IN(5, 1)), (OUT(5), 0), (OUT(5), 1)])
    a.param(5, 1, 10); a.param(5, 2, 0); grab('warm6b', 62, 0.6)
    x, r_ = grab('T6_two_inst_slot1', 60); f1_ = line(x, r_, et(60), 0.02)
    a.param(5, 1, 0); a.param(5, 2, 10); x, r_ = grab('T6_two_inst_slot6', 60); f6_ = line(x, r_, 2 * et(60), 0.02)
    log('T6_two_instances', slot1_tri32=f1_, c1=cents(f1_, et(60)), slot6_fm16=f6_, c6=cents(f6_, 2 * et(60)), alive=alive())

    # ================= T7: stress. Held note; LFO -> SYNC + COLOR, CV -> FINE; WAVE / RANGE / COLOR stepped fast
    MIDI, SYS, LFO, MIX = 1, 2, 5, 6
    build({MIDI: [31, 3, 12, 0, 0], SYS: [28, 2, 2, 0, 100], LFO: [1, 0, 70, 100, 50], MIX: [10, 10, 0, 0, 0]},
          [(OUT(MIDI), IN(SYS)), (OUT(MIDI), IN(SYS, 1)), (OUT(LFO), IN(SYS, 3)), (OUT(LFO), IN(SYS, 2)),
           (OUT(SYS), IN(MIX, 0)), (OUT(MIX), 0), (OUT(MIX), 1)])
    grab('warm7', 62, 0.5)
    a.note(60, True)
    t0 = time.time(); steps = 0
    for rep in range(3):
        for w in list(range(7)) + list(range(5, -1, -1)):
            a.param(SYS, 2, w); steps += 1; time.sleep(0.12)
        for rg in (1, 2, 3, 4, 5, 4, 3, 2):
            a.param(SYS, 1, rg); steps += 1; time.sleep(0.08)
        for col in range(0, 101, 20):
            a.param(SYS, 3, col); steps += 1; time.sleep(0.05)
    a.note(60, False)
    ok_alive = alive()
    a.cable(OUT(LFO), IN(SYS, 3), 0); a.cable(OUT(LFO), IN(SYS, 2), 0); a.cable(OUT(MIDI), IN(SYS, 1), 0)
    a.param(SYS, 1, 2); a.param(SYS, 2, 2); a.param(SYS, 3, 0); time.sleep(0.3)
    x, r_ = grab('T7_after_stress_tri_n60', 60); f = line(x, r_, et(60), 0.02)
    log('T7_stress', steps=steps, seconds=round(time.time() - t0, 1), alive=ok_alive, after_f=f, after_c=cents(f, et(60)),
        after_rms=round(float(np.sqrt((x[7200:] ** 2).mean())), 4))

    # ================= T8: heavy patch ~285 records: VOWEL (128) + NOISE SAW (129) + MIDINOTE (16) + MIXER (12)
    build({1: [31, 3, 12, 0, 0], 2: [28, 2, 5, 40, 100], 3: [28, 2, 4, 30, 100], 6: [10, 10, 10, 0, 0]},
          [(OUT(1), IN(2)), (OUT(1), IN(3)), (OUT(1, 1), IN(2, 3)), (OUT(1, 1), IN(3, 3)),
           (OUT(2), IN(6, 0)), (OUT(3), IN(6, 1)), (OUT(6), 0), (OUT(6), 1)])
    def phrase():
        time.sleep(0.2)
        for n in (48, 55, 60, 67, 72, 60):
            a.note(n, True); time.sleep(0.35); a.note(n, False); time.sleep(0.08)
    _, xx, rate = capture('T8_heavy_285', 3.2, during=phrase)
    al1 = alive()
    a.param(3, 2, 1); time.sleep(0.4); a.param(3, 2, 4); time.sleep(0.4)       # swap NOISE SAW -> FM+SYNC -> back
    x, r_ = grab('T8_heavy_after_swap_n60', 60)
    log('T8_heavy', phrase_rms=round(float(np.sqrt((xx[:, 0] ** 2).mean())), 4), alive=al1, alive_after_swap=alive(),
        after_rms=round(float(np.sqrt((x[7200:] ** 2).mean())), 4))

    # ================= T9: every shipped preset, loaded as modules + cables, phrase played, pitch per note
    PH = [48, 55, 60, 67, 72]
    for p in sorted((REL / 'presets').glob('VOICE_*.bin')):
        b = p.read_bytes(); assert len(b) == 1212 and b[:16] == b'HabPatchFile0001'
        slots = {s + 1: list(b[56 + s * 8:56 + s * 8 + 5]) for s in range(6) if list(b[56 + s * 8:56 + s * 8 + 5]) != [0] * 5}
        cables = [(o, i) for o in range(22) for i in range(34) if b[120 + o * 42 + i]]
        build(slots, cables)
        def play():
            time.sleep(0.3)
            for n in PH:
                a.note(n, True); time.sleep(0.55); a.note(n, False); time.sleep(0.15)
        _, xx, rate = capture('T9_' + p.stem, 4.2, during=play); y = xx[:, 0]
        notes = []
        is_cb = any(v[0] == 28 and v[2] == 6 for v in slots.values())
        for k, n in enumerate(PH):
            t0_ = 0.3 + k * 0.7 + (0.02 if is_cb else 0.15)
            seg = np.concatenate([np.zeros(int(0.15 * rate)), y[int(t0_ * rate):int((t0_ + 0.35) * rate)]])
            if is_cb:
                f = line(seg, rate, 1.498 * et(n), 0.012); notes.append(dict(n=n, f2=f, c=cents(f, 1.498 * et(n)),
                                                                            pk=round(float(np.abs(seg).max()), 4)))
            else:
                fg = et(n)
                f = line(seg, rate, fg, 0.03); notes.append(dict(n=n, f=f, c=cents(f, fg), pk=round(float(np.abs(seg).max()), 4)))
        tail = float(np.sqrt(np.mean(y[int(4.0 * rate):] ** 2)))
        log('T9_' + p.stem, notes=notes, tail_rms=round(tail, 6), alive=alive())
finally:
    a.all_notes_off(); time.sleep(0.5)
    try:
        ok = a.restore(snap)
    except Exception as e:
        ok = False; print('restore error:', repr(e))
    (OUTD / 'results_pass2.json').write_text(json.dumps(dict(restored=ok, results=R), indent=1) + '\n')
    a.close()
    print('RESTORED user patch' if ok else 'RESTORE INCOMPLETE (see pre_snapshot_pass2.json)', flush=True)
