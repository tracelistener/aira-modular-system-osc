"""SYSTEM OSCILLATOR v3 wave programs: the seven v2 waves with the stock-oscillator jack set. Offline; no device I/O.

Jacks (cable inputs of the type-28 slot, same order as the stock SAW/SQR oscillators):
  in1 CV IN        pitch, unchanged (two copied MIXER MAC chains, x10)
  in2 FINE IN      pitch += FINE/12  (1.0 = 1 semitone; the stock SAW scales its FINE sum by ~0.083)
  in3 COLOR IN     COLOR = P3/100 + COLOR IN   (the stock SAW's own 'CV + knob' add, 2c83)
  in4 SYNC TRIG IN rising edge through 0.3 -> hard sync of the wave (all waves) and the CB strike

Hard sync uses the SYSTEM cells' own sync input 2007 ('a'): phase = a*(wrap(phase+inc)+1)-1, a = 1 free running,
a = 0 for one sample = reset (SYSTEM-1m base drives OSC2 SYNC this way; OSC1 gets a constant 1.0).

Every added record is a native Roland record shape (source noted per record):
  FINE+COLOR:  1e05 0fe0 2fe2 | IN2 lb             load FINE, pitch
               0805 0422      | 0002 1555 5555     r0 = FINE*(1/12) + r2          (SYSTEM-1m base rec 31 shape)
               1e05 2fe0 3fe2 | IN3 C033           load COLOR IN, COLOR knob
               0902 2c83                           r2 = r2 + r3                   (stock SAW rec 2 op)
               0c03 8fe0      | lb                 pitch incl. FINE -> 2004
               0c03 afe0      | COLW               COLOR sum -> 2006
  SYNC:        3107 1050 a412 0fe4 | 24cc 0000 IN4  r1 = 0.3, r2 = 0, r0 = SYNC in     (stock S&H rec 20)
               0a02 8e09                           r0 = in - 0.3                  (S&H rec 21)
               0c03 1fe0 | XPREV                   r1 = x one sample earlier      (S&H rec 22)
               3d06 1a12 0fe0 0fe2 | e000 e021     r0 = x = (in > 0.3)            (S&H rec 23)
               3406 0c09 1fe0 8fe2 | e000 XCUR     r0 = x - x_prev; r1 = 0; x -> XCUR  (S&H rec 24)
               1b04 8401 1fe0 | const1             r0 = max(r0, 0) = strike; r1 = 1.0 (S&H rec 25 op; min/max
                                                   decoded against the plug-out's pitch clamp)
               1804 0c48 8fe0 | TRIGW              r0 = 1 - strike; strike -> TRIGW  (S&H rec 19 shape)
               0001                                gap
               0c03 8fe0 | AW                      a -> 2007
CB (cell 9) additionally: rec 1's A116 load is split out and reads TRIGW; rec 3 reads E000 instead of A118;
rec 4 ('2ecc 3002', the only consumer of A000/A118) is removed. A000 -> E000 for every wave (was: cable in2).
"""
import hashlib, struct, sys
from pathlib import Path
OLD = Path('C:/Users/admin/Documents/Codex/2026-09-22/files-mentioned-by-the-user-handoff')
sys.path.insert(0, str(OLD / 'work'))
from next_system_interface import expanded, program, records, BASE
from system_cell2_probe_program import serial
from system_cell2_midi_program import mixer_chain
from system_cell_midi_program import layout, cell_source, SYS_INPUTS, SYS_OUTPUTS, SCALARS
from cowbell_program import source as cb_source

WAVES = [('FM', 10), ('FM+SYNC', 14), ('TRI', 2), ('LOGIC', 21), ('NOISE SAW', 13), ('VOWEL', 6), ('CB', 9)]
# Slot-relative private words chosen from each wave's unused set (see free-word audit):
#   XCUR must be untouched by the wave; XPREV = XCUR+1 must not be written before the sync block reads it
#   (the block runs first); COLW/AW/TRIGW are written by the adapter and read by the wave's first two records.
PRIV = {10: dict(XCUR=24, COLW=26, AW=27, TRIGW=28),
        14: dict(XCUR=24, COLW=26, AW=27, TRIGW=28),
        2: dict(XCUR=28, COLW=30, AW=31, TRIGW=39),
        21: dict(XCUR=24, COLW=26, AW=27, TRIGW=28),
        13: dict(XCUR=35, COLW=37, AW=47, TRIGW=47),
        6: dict(XCUR=45, COLW=33, AW=35, TRIGW=35),
        9: dict(XCUR=29, COLW=31, AW=39, TRIGW=41)}
ONE_TWELFTH = (0x1555, 0x5555)    # 0x15555555 = 0.0833333 in the [s][e2][m29] immediate format


def data_ports(r):
    mic, opn = r[1:1 + nmicro(r[0])], r[1 + nmicro(r[0]):]
    ld = st = 0
    for x in mic:
        if (x & 0x0fe1) == 0x0fe0 and (x & 0x0fff) >= 0xfe0:
            a = opn[(x & 0x1f) >> 1]
            if a < 0x2000:
                if x & 0x8000: st += 1
                else: ld += 1
    return ld, st


def nmicro(H):
    if H & 0x8000:
        return 5 + ((H >> 6) & 3)
    for b, m in ((0x4000, 4), (0x2000, 3), (0x1000, 2), (0x0800, 1)):
        if H & b:
            return m
    return 0


def donor(cell):
    if cell == 9:
        s = cb_source()
        return dict(words=s['words'], fields=s['fields'], records=s['records'], producer=s['producer'], store=s['store'],
                    cluster_max=s['cluster_max'])
    s = cell_source(cell)
    return dict(s, records=records(s['words']))


def used_words(words, base):
    used = set()
    for p, r in records(words):
        m = nmicro(r[0])
        for x in r[1:1 + m]:
            if (x & 0x0fe1) == 0x0fe0 and (x & 0x0fff) >= 0xfe0:
                a = r[1 + m + ((x & 0x1f) >> 1)]
                if a < 0x2000:
                    used.add(a - base)
    return used


def build_program(slot, cell):
    if not 0 <= slot < 6:
        raise ValueError('slot 0..5')
    s = donor(cell)
    original = s['words']; base = 48 * slot
    IN = [0x200a + 4 * slot + k for k in range(4)]
    g = 0xc034 + 8 * slot
    L = layout(slot, s['cluster_max'])
    la, lb = L['la'], L['lb']
    P = {k: base + v for k, v in PRIV[cell].items()}
    XCUR, XPREV, COLW, AW, TRIGW = P['XCUR'], P['XCUR'] + 1, P['COLW'], P['AW'], P['TRIGW']
    mapping = dict(L['map'])
    mapping.update({0x2004: lb, 0x2005: 0xc035 + 8 * slot, 0x2006: COLW, 0x2007: AW, 0xa000: 0xe000})
    mapping.update(L['cap'])
    if cell == 9:
        mapping[0xa116] = TRIGW
    t = original.copy()
    for i in s['fields']:
        t[i] = mapping[original[i]]
    # the donor's own private words must not collide with the adapter's (inputs routed to a dummy coefficient
    # address for this check, so the intended reads of COLW/AW/TRIGW are not counted as the donor's own words)
    probe = original.copy()
    pm = dict(mapping)
    pm.update({0x2006: 0xc0ff, 0x2007: 0xc0ff})
    if cell == 9:
        pm[0xa116] = 0xc0ff
    for i in s['fields']:
        probe[i] = pm[original[i]]
    donor_used = used_words(probe, base)
    assert (P['XCUR'] - base) not in donor_used and (COLW - base) not in donor_used and (AW - base) not in donor_used, cell
    assert cell != 9 or (TRIGW - base) not in donor_used
    if cell == 9:
        rr = s['records']
        p1, p3, p4 = rr[1][0], rr[3][0], rr[4][0]
        assert t[p1:p1 + 7] == [0x3e07, 0x0fe0, 0x1fe2, 0x2fe4, lb, COLW, TRIGW]
        assert t[p3:p3 + 7] == [0x3e07, 0x8fe0, 0x9fe2, 0x4fe4, mapping[0x68], mapping[0x2b], 0xa118]
        assert t[p4:p4 + 3] == [0x0803, 0x2ecc, 0x3002]
        t[p3 + 6] = 0xe000                                   # r4 <- 0.0 instead of A118 (r4 is dead until rec 8)
        # rec 1: three data loads would break the <=2 data loads rule -> split the trigger load out
        new1 = [0x1e05, 0x0fe0, 0x1fe2, lb, COLW, 0x0c03, 0x2fe0, TRIGW]
        t = t[:p1] + new1 + t[p1 + 7:p4] + t[p4 + 3:]       # ... and drop rec 4
    init_store = s['store'].copy(); init_store[-2:] = [L['const_x'], L['const_y']]
    chain1 = mixer_chain([IN[0]] * 4, [g] * 5) + [0x0c03, 0x8fe0, la]
    chain2 = mixer_chain([la, la, IN[0], IN[0]], [g] * 5) + [0x0c03, 0x8fe0, lb]
    fine_color = [0x1e05, 0x0fe0, 0x2fe2, IN[1], lb,                    # r0 = FINE IN, r2 = pitch
                  0x0805, 0x0422, 0x0002, ONE_TWELFTH[0], ONE_TWELFTH[1],  # r0 = FINE/12 + pitch (base rec 31)
                  0x0c03, 0x8fe0, lb,                                   # -> 2004 (base rec 32 adjacency)
                  0x1e05, 0x0fe0, 0x1fe2, IN[2], 0xc033 + 8 * slot,     # r0 = COLOR IN, r1 = COLOR knob (AMP rec 1)
                  0x0902, 0x0c01,                                       # r0 = r0 + r1 (AMP rec 2 verbatim)
                  0x0001,
                  0x0c03, 0x8fe0, COLW]                                 # -> 2006
    sync = [0x3107, 0x1050, 0xa412, 0x0fe4, 0x24cc, 0x0000, IN[3],
            0x0a02, 0x8e09,
            0x0c03, 0x1fe0, XPREV,
            0x3d06, 0x1a12, 0x0fe0, 0x0fe2, 0xe000, 0xe021,
            0x3406, 0x0c09, 0x1fe0, 0x8fe2, 0xe000, XCUR,
            0x1b04, 0x8401, 0x1fe0, L['const_y'],
            0x1804, 0x0c48, 0x8fe0, TRIGW,
            0x0001,
            0x0c03, 0x8fe0, AW]
    # sync block first: nothing may write XPREV before it is read; then the constant producer
    # (const_y = 1.0 must exist before the sync block reads it -> producer goes first, it only writes la/const)
    pre = s['producer'] + init_store + sync + chain1 + chain2 + fine_color
    tail = [0x1e05, 0x0fe0, 0x1fe2, L['cap'][0x2008], L['cap'][0x200a],
            0x1e05, 0x8fe0, 0x9fe2, 0x2022 + 6 * slot, 0x2025 + 6 * slot]
    words = t[:2] + pre + t[2:-5] + tail + t[-5:]
    words[-1] = 1 if len(words) % 2 == 0 else 0
    rr = records(words)
    # nothing before the sync block's XPREV read may write XPREV
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
    return dict(serialized=body, words=words, records=len(rr), private=sorted(priv),
                bindings=dict(cv=hex(IN[0]), fine=hex(IN[1]), color=hex(IN[2]), sync=hex(IN[3]), pitch=hex(lb),
                              color_word=hex(COLW), sync_gate=hex(AW), strike=hex(TRIGW), x=hex(XCUR)))


if __name__ == '__main__':
    import json
    for name, cell in WAVES:
        sizes = []
        for slot in range(6):
            b = build_program(slot, cell)
            sizes.append((len(b['serialized']), b['records']))
        assert len(set(sizes)) == 1
        print('%-9s cell %2d  %4d bytes  %3d records' % (name, cell, sizes[0][0], sizes[0][1]))
