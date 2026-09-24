"""SYSTEM OSCILLATOR v3.1 wave programs: v3's jack set with a lighter adapter. Offline; no device I/O.

Jacks (unchanged from v3): in1 CV IN, in2 FINE IN (1.0 = 1 semitone), in3 COLOR IN (+ P3/100, now clamped 0..1),
in4 SYNC TRIG IN (rising edge through 0.3: hard sync of every wave; CB strike).

Adapter per wave (every record is a native Roland record shape):
  pitch  1e05 0fe0 2fe2 | IN2 IN1            r0 = FINE, r2 = CV
         0805 0422      | 0002 <1/120>       r0 = FINE/120 + CV          (SYSTEM-1m base rec 31 shape)
         0904 0430      | <10.0>             r0 = r0 * 10                (SYSTEM-1m base rec 87 shape)
         0c03 8fe0      | lb                 -> 2004   (replaces the two MIXER MAC chains + constant loader: -14 records)
  COLOR  1e05 0fe0 1fe2 | IN3 C033           r0 = COLOR IN, r1 = COLOR knob
         0902 0c01                           r0 = r0 + r1                (AMP rec 2)
         0c03 1fe0      | e021               r1 = 1.0
         1b04 8001 1fe0 | e000               r0 = min(r0, 1); r1 = 0     (CROSSFADE rec 4)
         1b04 8401 2fe0 | e022               r0 = max(r0, 0)             (CROSSFADE rec 5)
         0c03 8fe0      | COLW               -> 2006
  SYNC   stock S&H trigger detector (recs 20-25), strike -> TRIGW, a = 1 - strike -> 2007 (sync gate), 1.0 from E021
P4 is no longer read by the DSP (it was the x10 MAC gain).
"""
import struct, sys
from pathlib import Path
OLD = Path('C:/Users/admin/Documents/Codex/2026-09-22/files-mentioned-by-the-user-handoff')
sys.path.insert(0, str(OLD / 'work'))
from next_system_interface import records
from system_cell2_probe_program import serial
from system_cell_midi_program import layout
from system_osc_v3 import WAVES, PRIV, donor, used_words, data_ports, nmicro

ONE_120TH = (0x0222, 0x2222)   # 0x02222222 = 1/120 in the [s][e2][m29] immediate format (e=0: m/2^32)
TEN = (0x4a00, 0x0000)         # 0x4a000000 = 10.0 (e=2: m/2^24)


def c32(hi, lo):
    v = (hi << 16) | lo
    return (-1 if v >> 31 else 1) * (v & 0x1fffffff) * 2.0 ** (4 * ((v >> 29) & 3) - 32)


assert abs(c32(*ONE_120TH) - 1 / 120) < 1e-9 and c32(*TEN) == 10.0


def build_program(slot, cell):
    if not 0 <= slot < 6:
        raise ValueError('slot 0..5')
    s = donor(cell)
    original = s['words']; base = 48 * slot
    IN = [0x200a + 4 * slot + k for k in range(4)]
    L = layout(slot, s['cluster_max'])
    lb = L['lb']
    P = {k: base + v for k, v in PRIV[cell].items()}
    XCUR, XPREV, COLW, AW, TRIGW = P['XCUR'], P['XCUR'] + 1, P['COLW'], P['AW'], P['TRIGW']
    mapping = dict(L['map'])
    mapping.update({0x2004: lb, 0x2005: 0xc035 + 8 * slot, 0x2006: COLW, 0x2007: AW, 0xa000: 0xe000})
    mapping.update(L['cap'])
    if cell == 9:
        mapping[0xa116] = TRIGW
    probe = original.copy()
    pm = dict(mapping)
    pm.update({0x2006: 0xc0ff, 0x2007: 0xc0ff})
    if cell == 9:
        pm[0xa116] = 0xc0ff
    for i in s['fields']:
        probe[i] = pm[original[i]]
    donor_used = used_words(probe, base)
    for w in (XCUR, COLW, AW) + ((TRIGW,) if cell == 9 else ()):
        assert w - base not in donor_used, (cell, w - base)
    assert lb - base not in (XCUR - base, XPREV - base, COLW - base, AW - base, TRIGW - base)
    t = original.copy()
    for i in s['fields']:
        t[i] = mapping[original[i]]
    if cell == 9:
        rr = s['records']
        p1, p3, p4 = rr[1][0], rr[3][0], rr[4][0]
        assert t[p1:p1 + 7] == [0x3e07, 0x0fe0, 0x1fe2, 0x2fe4, lb, COLW, TRIGW]
        assert t[p3:p3 + 7] == [0x3e07, 0x8fe0, 0x9fe2, 0x4fe4, mapping[0x68], mapping[0x2b], 0xa118]
        assert t[p4:p4 + 3] == [0x0803, 0x2ecc, 0x3002]
        t[p3 + 6] = 0xe000
        t = t[:p1] + [0x1e05, 0x0fe0, 0x1fe2, lb, COLW, 0x0c03, 0x2fe0, TRIGW] + t[p1 + 7:p4] + t[p4 + 3:]
    sync = [0x3107, 0x1050, 0xa412, 0x0fe4, 0x24cc, 0x0000, IN[3],
            0x0a02, 0x8e09,
            0x0c03, 0x1fe0, XPREV,
            0x3d06, 0x1a12, 0x0fe0, 0x0fe2, 0xe000, 0xe021,
            0x3406, 0x0c09, 0x1fe0, 0x8fe2, 0xe000, XCUR,
            0x1b04, 0x8401, 0x1fe0, 0xe021,
            0x1804, 0x0c48, 0x8fe0, TRIGW,
            0x0001,
            0x0c03, 0x8fe0, AW]
    pitch = [0x1e05, 0x0fe0, 0x2fe2, IN[1], IN[0],
             0x0805, 0x0422, 0x0002, ONE_120TH[0], ONE_120TH[1],
             0x0904, 0x0430, TEN[0], TEN[1],
             0x0c03, 0x8fe0, lb]
    color = [0x1e05, 0x0fe0, 0x1fe2, IN[2], 0xc033 + 8 * slot,
             0x0902, 0x0c01,
             0x0c03, 0x1fe0, 0xe021,
             0x1b04, 0x8001, 0x1fe0, 0xe000,
             0x1b04, 0x8401, 0x2fe0, 0xe022,
             0x0c03, 0x8fe0, COLW]
    pre = sync + pitch + color
    tail = [0x1e05, 0x0fe0, 0x1fe2, L['cap'][0x2008], L['cap'][0x200a],
            0x1e05, 0x8fe0, 0x9fe2, 0x2022 + 6 * slot, 0x2025 + 6 * slot]
    words = t[:2] + pre + t[2:-5] + tail + t[-5:]
    words[-1] = 1 if len(words) % 2 == 0 else 0
    rr = records(words)
    pos_read = next(p for p, r in rr if r == [0x0c03, 0x1fe0, XPREV])
    for p, r in rr:
        if p >= pos_read:
            break
        m = nmicro(r[0])
        for x in r[1:1 + m]:
            if (x & 0x0fe1) == 0x0fe0 and (x & 0x0fff) >= 0xfe0 and x & 0x8000:
                assert r[1 + m + ((x & 0x1f) >> 1)] != XPREV
    assert all(a <= 2 and b <= 2 for a, b in (data_ports(r) for _, r in rr)), cell
    priv = used_words(words, base)
    assert min(priv) >= 0 and max(priv) <= 47, (cell, sorted(priv))
    body = serial(words)
    h = list(struct.unpack('<%dH' % (len(body) // 2), body))
    assert [h[i ^ 1] if i ^ 1 < len(h) else h[i] for i in range(len(h))] == words
    return dict(serialized=body, words=words, records=len(rr), private=sorted(priv))


if __name__ == '__main__':
    for name, cell in WAVES:
        sizes = {(len(build_program(s, cell)['serialized']), build_program(s, cell)['records']) for s in range(6)}
        assert len(sizes) == 1
        n, r = sizes.pop()
        print('%-9s cell %2d  %4d bytes  %3d records' % (name, cell, n, r))
