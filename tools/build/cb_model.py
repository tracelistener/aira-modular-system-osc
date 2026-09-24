"""Numerical model of the SYSTEM-1 CB wave, transcribed from the SYSTEM-1 plug-out's native code
(VST3 x64 .text 0x18ccaa-0x18d0b8 in the process routine at file offset 0x1861f0). Runs at 96 kHz, the DSP rate
implied by the plug-out's own pitch/decay (and by the SCOOPER's measured TRI pitch). Same constants as the
SYSTEM-1m ESC2 cell 9."""
import math
import numpy as np
FS = 96000

def wrap(x):
    return math.fmod(x + 1.0, 2.0) - 1.0 if x > 1.0 else x

def sgn(x):
    return -1.0 if x < 0 else (1.0 if x > 0 else 0.0)

def render(pitch, rng, color, trig, a=1.0):
    """pitch, rng, color: arrays or scalars per sample (SYSTEM units: pitch=(note-12)/12, color 0..1);
    trig: array of trigger values (1.0 for one sample at note-on). Returns (out_main, saw, square)."""
    n = len(trig)
    P = np.broadcast_to(np.asarray(pitch, float), (n,)); R = np.broadcast_to(np.asarray(rng, float), (n,))
    C = np.broadcast_to(np.asarray(color, float), (n,))
    out = np.zeros(n); saw = np.zeros(n); sq = np.zeros(n)
    env = 0.0; p1 = p2 = 0.0; bp = lp = 0.0; yA = yB = yC = 0.0
    for i in range(n):
        c = C[i]
        k = 0.999 + 0.0009999 * (1.8 * c - 0.8 * c * c)
        k = -1.0 if k < -1.0 else min(k, 1.0)
        d = trig[i] - env
        env = (d * 1.0 + env) if d > 0 else env * k
        env += 5.42101086e-20
        f1 = min(2.0 ** max(-20.0, min(9.0, P[i] - 4.75)), 512.0) * R[i]
        f2 = f1 * 1.498
        p1 = a * wrap(p1 + f1 * 0.0091666663) + a - 1.0
        p2 = a * wrap(p2 + f2 * 0.0091666663) + a - 1.0
        s1 = sgn(p1 + 0.104); s2 = sgn(p2 + 0.09)
        x = 2.2 * s1 + 2.2 * s2
        hp = x - 0.186 * bp - lp
        bp = bp + 0.0564 * hp
        lp = lp + 0.0564 * bp
        y0 = 0.2 * hp
        dA = y0 - yA; yA = yA + 0.021519 * dA; zA = 0.824 * dA
        dB = zA - yB; yB = yB + 0.5 * dB; zB = yB
        dC = zB - yC; yC = yC + 0.4 * dC; zC = -yC
        out[i] = zC * env * 1.0525
        saw[i] = p1; sq[i] = s1
    return out, saw, sq

def hits(seconds, onsets):
    t = np.zeros(int(seconds * FS))
    for s in onsets:
        t[int(s * FS)] = 1.0
    return t
