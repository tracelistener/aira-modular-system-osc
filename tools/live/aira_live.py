"""Live AIRA SCOOPER control + USB audio capture helpers.

Uses only the documented Customizer patch protocol (Roland DT1/RQ1, model 0x18):
  [10 00 00 00] x11  main module values
  [10 10 00 00] x30  six sub-module blocks: type, p1..p4
  [10 20 oo ii] x1   single cable output oo -> input ii
Every write is read back. snapshot() + restore() return the patch to its exact prior state.
No firmware, service, or diagnostic commands.
"""
import ctypes as c, time, wave, json
from pathlib import Path
import numpy as np
import mido

HERE = Path(__file__).resolve().parent
CAP = HERE.parent.parent / 'outputs' / 'live-captures'
CAP.mkdir(exist_ok=True)
MODEL = 0x18


class Aira:
    def __init__(self):
        ins = [n for n in mido.get_input_names() if 'AIRA MODULAR CTRL' in n]
        outs = [n for n in mido.get_output_names() if 'AIRA MODULAR CTRL' in n]
        notes = [n for n in mido.get_output_names() if 'AIRA MODULAR' in n and 'CTRL' not in n]
        assert len(ins) == len(outs) == len(notes) == 1, (ins, outs, notes)
        self.ip = mido.open_input(ins[0])
        self.op = mido.open_output(outs[0])
        self.np = mido.open_output(notes[0])
        self.op.send(mido.Message('sysex', data=[0x7e, 0x7f, 6, 1]))
        ident = self._rx(lambda d: len(d) >= 10 and d[0] == 0x7e and d[2:5] == [6, 2, 0x41])
        assert ident[5:7] == [0x18, 3], ident
        self.dev = ident[1]
        self.log = []

    def close(self):
        for p in (self.ip, self.op, self.np):
            try:
                p.close()
            except Exception:
                pass

    def _rx(self, pred, timeout=2.0):
        t = time.monotonic() + timeout
        while time.monotonic() < t:
            m = self.ip.poll()
            if m is not None and m.type == 'sysex':
                d = list(m.data)
                if pred(d):
                    return d
            time.sleep(0.002)
        raise TimeoutError('no sysex reply')

    def read(self, addr, n, tries=4):
        body = list(addr) + [0, 0, 0, n]
        pre = [0x41, self.dev, 0, 0, 0, MODEL, 0x12] + list(addr)
        for k in range(tries):
            self.op.send(mido.Message('sysex', data=[0x41, self.dev, 0, 0, 0, MODEL, 0x11] + body + [(-sum(body)) & 127]))
            try:
                d = self._rx(lambda d: d[:11] == pre)
                break
            except TimeoutError:
                if k == tries - 1:
                    raise
                time.sleep(1.0)
                while self.ip.poll() is not None:   # drain stale input
                    pass
        assert len(d) == 12 + n and sum(d[7:]) % 128 == 0
        return d[11:-1]

    def write(self, addr, data, settle=0.06):
        data = [int(v) & 0x7f for v in data]
        body = list(addr) + data
        self.op.send(mido.Message('sysex', data=[0x41, self.dev, 0, 0, 0, MODEL, 0x12] + body + [(-sum(body)) & 127]))
        self.log.append({'addr': list(addr), 'data': data, 't': time.time()})
        time.sleep(settle)
        back = self.read(addr, len(data))
        assert back == data, ('readback mismatch', addr, data, back)

    # patch helpers ---------------------------------------------------------
    def slot(self, s, values):  # s = 1..6, values = [type,p1,p2,p3,p4]
        assert 1 <= s <= 6 and len(values) == 5
        self.write([0x10, 0x10, 0, (s - 1) * 5], values, settle=0.6)

    def param(self, s, k, v):  # k = 1..4
        self.write([0x10, 0x10, 0, (s - 1) * 5 + k], [v], settle=0.08)

    def cable(self, o, i, v):
        self.write([0x10, 0x20, o, i], [1 if v else 0])

    def snapshot(self):
        reqs = [([0x10, 0, 0, 0], 11), ([0x10, 0x10, 0, 0], 30)] + [([0x10, 0x20, i, 0], 34) for i in range(22)]
        return [{'address': a, 'data': self.read(a, n)} for a, n in reqs]

    def restore(self, snap):
        # NOTE: twice the SCOOPER stopped answering sysex during a restore that used 0.25 s module settles
        # (2026-09-22); the second time it needed a power cycle. Module type changes load DSP programs, so
        # give them time: disconnect new cables, then modules with long settles, then the remaining cables.
        cur = self.snapshot()
        for b0, b1 in zip(snap[2:], cur[2:]):          # 1) remove cables that weren't there
            o = b0['address'][2]
            for i, (v0, v1) in enumerate(zip(b0['data'], b1['data'])):
                if v1 and not v0:
                    self.write([0x10, 0x20, o, i], [0], settle=0.1)
        if snap[1]['data'] != cur[1]['data']:          # 2) module blocks, slowly
            for s in range(6):
                a, b = snap[1]['data'][s * 5:s * 5 + 5], cur[1]['data'][s * 5:s * 5 + 5]
                if a != b:
                    self.write([0x10, 0x10, 0, s * 5], a, settle=1.0)
        cur = self.snapshot()
        for b0, b1 in zip(snap[2:], cur[2:]):          # 3) add back original cables
            o = b0['address'][2]
            for i, (v0, v1) in enumerate(zip(b0['data'], b1['data'])):
                if v0 != v1:
                    self.write([0x10, 0x20, o, i], [v0], settle=0.1)
        if snap[0]['data'] != cur[0]['data']:
            self.write([0x10, 0, 0, 1], snap[0]['data'][1:])
        final = self.snapshot()
        ok = all(x['data'] == y['data'] for x, y in zip(final, snap))
        return ok

    def note(self, n, on=True, ch=0, vel=100):
        self.np.send(mido.Message('note_on' if on else 'note_off', channel=ch, note=n, velocity=vel if on else 0))

    def all_notes_off(self, ch=0):
        self.np.send(mido.Message('control_change', channel=ch, control=123, value=0))

    def blank(self):
        """Disconnect every cable and empty every slot (known starting state)."""
        cur = self.snapshot()
        for b in cur[2:]:
            o = b['address'][2]
            for i, v in enumerate(b['data']):
                if v:
                    self.write([0x10, 0x20, o, i], [0])
        for s in range(6):
            if cur[1]['data'][s * 5:s * 5 + 5] != [0] * 5:
                self.write([0x10, 0x10, 0, s * 5], [0] * 5, settle=0.25)


# --------------------------------------------------------------------------
# WinMM capture from 'OUTPUT 1-2 (AIRA MODULAR)'
_w = c.WinDLL('winmm')


class _Caps(c.Structure):
    _fields_ = [('mid', c.c_ushort), ('pid', c.c_ushort), ('ver', c.c_uint), ('name', c.c_wchar * 32),
                ('formats', c.c_uint), ('channels', c.c_ushort), ('reserved', c.c_ushort)]


class _Fmt(c.Structure):
    _pack_ = 2
    _fields_ = [('tag', c.c_ushort), ('channels', c.c_ushort), ('rate', c.c_uint), ('byte_rate', c.c_uint),
                ('align', c.c_ushort), ('bits', c.c_ushort), ('extra', c.c_ushort)]


class _Hdr(c.Structure):
    _fields_ = [('data', c.c_void_p), ('length', c.c_uint), ('recorded', c.c_uint), ('user', c.c_size_t),
                ('flags', c.c_uint), ('loops', c.c_uint), ('next', c.c_void_p), ('reserved', c.c_size_t)]


_w.waveInGetDevCapsW.argtypes = [c.c_size_t, c.POINTER(_Caps), c.c_uint]
_w.waveInOpen.argtypes = [c.POINTER(c.c_void_p), c.c_uint, c.POINTER(_Fmt), c.c_size_t, c.c_size_t, c.c_uint]
for _fn in ('waveInPrepareHeader', 'waveInAddBuffer', 'waveInUnprepareHeader'):
    getattr(_w, _fn).argtypes = [c.c_void_p, c.POINTER(_Hdr), c.c_uint]
for _fn in ('waveInStart', 'waveInStop', 'waveInReset', 'waveInClose'):
    getattr(_w, _fn).argtypes = [c.c_void_p]


def capture(label, seconds=3.0, rate=48000, during=None):
    """Record `seconds` from AIRA OUTPUT 1-2. `during()` runs right after recording starts."""
    idx = None
    for i in range(_w.waveInGetNumDevs()):
        cap = _Caps(); _w.waveInGetDevCapsW(i, c.byref(cap), c.sizeof(cap))
        if 'AIRA MODULAR' in cap.name and cap.name.startswith('OUTPUT 1-2'):
            idx = i
    assert idx is not None, 'AIRA OUTPUT 1-2 not found'
    fmt = _Fmt(1, 2, rate, rate * 4, 4, 16, 0)
    h = c.c_void_p()
    rc = _w.waveInOpen(c.byref(h), idx, c.byref(fmt), 0, 0, 0)
    if rc != 0:
        raise RuntimeError('waveInOpen failed rc=%d (4 = device in use by another app)' % rc)
    buf = c.create_string_buffer(int(rate * seconds) * 4)
    hdr = _Hdr(c.addressof(buf), len(buf), 0, 0, 0, 0, None, 0)
    prep = False
    try:
        assert _w.waveInPrepareHeader(h, c.byref(hdr), c.sizeof(hdr)) == 0; prep = True
        assert _w.waveInAddBuffer(h, c.byref(hdr), c.sizeof(hdr)) == 0
        assert _w.waveInStart(h) == 0
        if during is not None:
            during()
        t = time.monotonic() + seconds + 3
        while not hdr.flags & 1 and time.monotonic() < t:
            time.sleep(0.01)
        assert hdr.flags & 1 and hdr.recorded == len(buf)
        data = buf.raw[:hdr.recorded]
    finally:
        _w.waveInStop(h); _w.waveInReset(h)
        if prep:
            _w.waveInUnprepareHeader(h, c.byref(hdr), c.sizeof(hdr))
        _w.waveInClose(h)
    path = CAP / (label + '.wav')
    with wave.open(str(path), 'wb') as f:
        f.setnchannels(2); f.setsampwidth(2); f.setframerate(rate); f.writeframes(data)
    x = np.frombuffer(data, dtype='<i2').reshape(-1, 2).astype(float) / 32768.0
    return path, x, rate


def analyze(s, rate):
    s = s[int(0.1 * rate):]
    y = s - s.mean()
    res = dict(peak=float(np.abs(s).max()), rms=float(np.sqrt(np.mean(y * y))), dc=float(s.mean()))
    if res['rms'] < 2e-5:
        res['state'] = 'silent'
        return res
    N = len(y)
    sp = np.abs(np.fft.rfft(y * np.hanning(N)))
    fr = np.fft.rfftfreq(N, 1 / rate)
    sp[fr < 1.5] = 0
    k = int(np.argmax(sp))
    p = 0.0
    if 0 < k < len(sp) - 1:
        a, b, g = np.log(sp[k - 1] + 1e-30), np.log(sp[k] + 1e-30), np.log(sp[k + 1] + 1e-30)
        den = a - 2 * b + g
        p = 0.5 * (a - g) / den if den else 0.0
    fpk = (k + p) * rate / N
    ac = np.fft.irfft(np.abs(np.fft.rfft(y, 2 * N)) ** 2)[:N]
    ac = ac / ac[0]
    lo = max(int(rate / 6000), 2); hi = min(int(rate / 1.5), N - 2)
    # first strong peak (avoid octave errors): take the earliest local max within 0.9 of global max
    seg = ac[lo:hi]
    gmax = seg.max()
    cand = [i for i in range(1, len(seg) - 1) if seg[i] >= seg[i - 1] and seg[i] >= seg[i + 1] and seg[i] > 0.9 * gmax]
    j = (cand[0] if cand else int(np.argmax(seg))) + lo
    a, b, g = ac[j - 1], ac[j], ac[j + 1]
    den = a - 2 * b + g
    q = 0.5 * (a - g) / den if den else 0.0
    f0 = rate / (j + q)
    if not np.isfinite(f0) or not 1.5 < f0 < rate / 2:   # degenerate autocorrelation (e.g. a lost note)
        f0 = fpk
    harm = []
    for hh in range(1, 11):
        fh = f0 * hh
        if fh >= rate / 2:
            break
        jj = int(round(fh * N / rate))
        if jj >= len(sp):
            break
        harm.append(float(sp[max(jj - 4, 0):jj + 5].max()))
    h1 = harm[0] if harm and harm[0] > 0 else 1.0
    res.update(state='signal', fft_peak_hz=round(float(fpk), 4), f0_hz=round(float(f0), 4),
               ac_strength=round(float(ac[j]), 4),
               harm_db=[round(20 * np.log10(v / h1 + 1e-12), 1) for v in harm],
               min=float(s.min()), max=float(s.max()))
    return res
