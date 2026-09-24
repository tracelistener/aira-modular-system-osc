"""Offline re-analysis of the v3.1 hardware captures (precise pitch, v1-vs-v3.1 wave spectra, sync comb, CB envelope)."""
import math, wave, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
HW = ROOT / 'outputs/wave-selector-v31-inputs/hw-test'
V1 = Path('C:/Users/admin/Documents/Codex/2026-09-22/files-mentioned-by-the-user-handoff/outputs/live-captures')


def load(p):
    with wave.open(str(p)) as f:
        rate = f.getframerate(); x = np.frombuffer(f.readframes(f.getnframes()), '<i2').reshape(-1, 2) / 32768.0
    return x[:, 0].astype(float), rate


def et(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def dtft_peak(x, rate, f_guess, span=0.01):
    """Frequency of the spectral line near f_guess by maximising the Hann-windowed DTFT (golden section)."""
    y = x[int(0.15 * rate):]; y = (y - y.mean()) * np.hanning(len(y)); t = np.arange(len(y)) / rate
    mag = lambda f: abs(np.dot(y, np.exp(-2j * np.pi * f * t)))
    lo, hi = f_guess * (1 - span), f_guess * (1 + span)
    fs = np.linspace(lo, hi, 81); m = [mag(f) for f in fs]; k = int(np.argmax(m))
    a, b = fs[max(k - 1, 0)], fs[min(k + 1, 80)]
    g = (math.sqrt(5) - 1) / 2
    c, d = b - g * (b - a), a + g * (b - a)
    for _ in range(40):
        if mag(c) > mag(d):
            b = d
        else:
            a = c
        c, d = b - g * (b - a), a + g * (b - a)
    return (a + b) / 2


def cents(f, r):
    return 1200 * math.log2(f / r)


def top_peaks(x, rate, n=10, fmax=3000):
    y = x[int(0.15 * rate):]; y = y - y.mean(); N = len(y)
    sp = np.abs(np.fft.rfft(y * np.hanning(N), 4 * N)); fr = np.fft.rfftfreq(4 * N, 1 / rate)
    sp[(fr < 40) | (fr > fmax)] = 0
    loc = [i for i in range(1, len(sp) - 1) if sp[i] > sp[i - 1] and sp[i] >= sp[i + 1] and sp[i] > sp.max() * 10 ** (-40 / 20)]
    loc = sorted(loc, key=lambda i: -sp[i])[:n]
    return sorted((round(fr[i], 2), round(20 * math.log10(sp[i] / sp.max()), 1)) for i in loc)


print('=== A1/A2 precise pitch (DTFT line fit, 1.45 s) ===')
for n in (36, 48, 60, 72, 84):
    fs = dtft_peak(load(HW / ('A1_sys_tri_n%d.wav' % n))[0], 48000, et(n))
    fq = dtft_peak(load(HW / ('A1_sqr_n%d.wav' % n))[0], 48000, et(n))
    print('note %d  ET %.3f  SYS %.3f (%+.2f c)  SQR %.3f (%+.2f c)  SYS-SQR %+.2f c' % (
        n, et(n), fs, cents(fs, et(n)), fq, cents(fq, et(n)), cents(fs, fq)))
for ps, pq, mult in ((1, 0, 0.5), (3, 2, 2), (4, 3, 4), (5, 4, 8)):
    f = et(60) * mult
    fs = dtft_peak(load(HW / ('A2_sys_range%d.wav' % ps))[0], 48000, f)
    fq = dtft_peak(load(HW / ('A2_sqr_range%d.wav' % pq))[0], 48000, f)
    print('RANGE sys%d/sqr%d  expect %.2f  SYS %.3f (%+.2f c)  SQR %.3f (%+.2f c)  SYS-SQR %+.2f c' % (
        ps, pq, f, fs, cents(fs, f), fq, cents(fq, f), cents(fs, fq)))

print('\n=== A3 spectra: v3.1 now vs v1-era capture (same wave, same note) ===')
for w in ('FM', 'FMSYNC', 'TRI', 'LOGIC', 'NOISESAW', 'VOWEL'):
    for n in (48, 72):
        new = HW / ('A3_%s_n%d.wav' % (w, n)); old = V1 / ('%s_n%d.wav' % (w, n))
        xn, _ = load(new)
        f1n = dtft_peak(xn, 48000, et(n), 0.004)
        line = '%-8s n%d  fund now %.3f (%+.2f c)' % (w, n, f1n, cents(f1n, et(n)))
        if old.exists():
            xo, _ = load(old)
            f1o = dtft_peak(xo, 48000, et(n), 0.004)
            line += '  v1 %.3f (%+.2f c)' % (f1o, cents(f1o, et(n)))
        print(line)
        print('    now:', top_peaks(xn, 48000, 8, 2 * et(n) + 50 if n == 72 else 700))
        if old.exists():
            print('    v1 :', top_peaks(xo, 48000, 8, 2 * et(n) + 50 if n == 72 else 700))

print('\n=== D hard sync: long-lag periodicity ===')
for lab in ('D_tri_unsynced_n60', 'D_tri_synced_to_saw64_n60', 'D_synced_saw_fine80_n60'):
    x, rate = load(HW / (lab + '.wav'))
    y = x[int(0.15 * rate):]; y = y - y.mean()
    ac = np.fft.irfft(np.abs(np.fft.rfft(y, 2 * len(y))) ** 2)[:len(y)]; ac /= ac[0]
    lo, hi = int(rate / 300), int(rate / 60)
    j = lo + int(np.argmax(ac[lo:hi]))
    a_, b_, g_ = ac[j - 1], ac[j], ac[j + 1]; q = 0.5 * (a_ - g_) / (a_ - 2 * b_ + g_)
    print('%-28s best period in 60..300 Hz: %.3f Hz (ac %.4f)   peaks %s' % (lab, rate / (j + q), ac[j], top_peaks(x, rate, 8, 700)))

print('\n=== E CB strike envelope ===')
x, rate = load(HW / 'E_cb_strike_n60.wav')
L = int(0.005 * rate); nb = len(x) // L
env = 20 * np.log10(np.maximum(np.sqrt((x[:nb * L].reshape(nb, L) ** 2).mean(1)), 1e-9))
i = int(np.argmax(env))
print('loudest 5 ms at t=%.3f s: %.1f dBFS (abs peak %.4f); env at +100/+300/+600 ms: %s' % (
    i * L / rate, env[i], np.abs(x).max(), [round(env[min(i + k, nb - 1)], 1) for k in (20, 60, 120)]))
