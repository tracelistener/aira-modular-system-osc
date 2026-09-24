"""SYSTEM-1m CB (cell 9) as a SCOOPER type-28 wave -- v2 design. Offline builder; no device I/O.

Changes versus the six working waves' builder (system_cell_midi_program.build_program):
  * Record 4 of the donor, '0803 2ecc 3002', is the ONLY consumer of A000 (r3) and A118 (r4); both registers
    are overwritten (r3 by 3472 in rec 11, r4 by 4041 in rec 8) before anything else reads them, and its only
    output is r2 -> E0, the envelope trigger read at rec 52.  The SYSTEM-1 plug-out's native CB (same constants)
    drives that trigger with a one-sample 1.0 pulse at note-on.  v2 therefore replaces rec 4 with Roland's own
    edge-detector pattern (main DSP program, records 293-299: store current, read address+1 = previous sample,
    'r2 = r0 - r2', one-record gap) fed from a GATE on cable input 3:
        rec 1  3e07 0fe0 1fe2 2fe4 | pitch  COLOR  FC        (A116 slot -> FC; r2 is reloaded in rec 4)
        rec 3  3e07 8fe0 9fe2 0fe4 | 68     2B     IN3       (r0 <- gate;          was r4 <- A118)
        rec 4  1e05 8fe0 2fe2      | FB     FC               (store gate -> FB; r2 <- FC = previous gate)
        rec 4b 0902 2c0a                                     (r2 = r0 - r2 = gate - previous)
        rec 4c 0001                                          (gap)
        rec 5  0c03 afe0           | E0                      (unchanged: trigger -> E0)
    Records 4..4c are main-DSP program 1 records 294..296 verbatim except for the two addresses.
    A rising gate gives +1 for one sample; a falling gate gives -1, which the donor's envelope ignores
    (env = trig if trig > env else env * k).  FB/FC sit in the unused tail of the preserved E0..FF block.
  * No copy of the main-DSP 'A118 producer' (that was the SYSTEM-1m master stereo filter chain feeding A118/A119).
  * A000 keeps the standard 'cable input 2' binding (now dead: r3 is never read).
Everything else (pitch MAC x10 adapter, RANGE/COLOR/constant inputs, captures, terminal parity) is the standard build.
"""
import hashlib, struct, sys
from pathlib import Path
OLD = Path('C:/Users/admin/Documents/Codex/2026-09-22/files-mentioned-by-the-user-handoff')
sys.path.insert(0, str(OLD / 'work'))
from next_system_interface import expanded, program, records, BASE
from system_cell2_probe_program import serial
from system_cell2_midi_program import mixer_chain
from system_cell_midi_program import layout, SYS_INPUTS, SYS_OUTPUTS, SCALARS

CELL = 9
SOURCE_SHA = '14218bb15c4c128d6df17f888ba1939a873358b3c6b40c4eab89837fa0cde71e'
GATE_INPUT = 3            # 1-based cable input number (0x200a + 4*slot + GATE_INPUT - 1)
X, XH = 0xfb, 0xfc        # gate store / previous-gate read (FC = FB one sample later)


def source():
    raw = expanded()
    assert hashlib.sha256(raw).hexdigest() == SOURCE_SHA
    variants = [program(raw, 0x4c7c4 + 0x60 * t, CELL) for t in (0, 2, 4, 6)]
    words = variants[0]['words']
    assert all(len(p['words']) == len(words) for p in variants)
    rr = records(words)
    fields = sorted(i for i in range(len(words)) if len({p['words'][i] for p in variants}) > 1)
    vals = {words[i] for i in fields}
    assert {v for v in vals if v >> 12 == 0xa} == {0xa000, 0xa116}
    assert {v for v in vals if v >= 0x1000 and v >> 12 != 0xa} == set(SYS_INPUTS + SYS_OUTPUTS)
    assert {v for v in vals if v < 0xe0} == set(SCALARS)
    cluster = sorted(v for v in vals if 0xe0 <= v < 0x1000)
    assert cluster[-1] == 0xf9 and X > cluster[-1] and XH <= 0xff
    # Donor records this design edits, asserted exactly.
    assert rr[1][1] == [0x3e07, 0x0fe0, 0x1fe2, 0x2fe4, 0x2004, 0x2006, 0xa116]
    assert rr[3][1] == [0x3e07, 0x8fe0, 0x9fe2, 0x4fe4, 0x0068, 0x002b, 0xa118]
    assert rr[4][1] == [0x0803, 0x2ecc, 0x3002]
    assert rr[5][1] == [0x0c03, 0xafe0, 0x00e0]
    assert rr[52][1] == [0x1e05, 0x0fe0, 0x1fe2, 0x00e0, 0x0019]        # E0 (trigger) read by the envelope
    # r4 (A118) is overwritten by 4041 in rec 8; r3 (A000) by 3472 in rec 11.
    assert rr[8][1][:3] == [0x1505, 0x0c20, 0x4041] and rr[11][1][:3] == [0x1108, 0x3472, 0x20a1]
    # FB/FC are not referenced anywhere in the donor.
    assert not any(v in (X, XH) for v in words)
    base_ptr = struct.unpack_from('<I', raw, 0x4c784)[0]
    dest, n, src = struct.unpack_from('<III', raw, base_ptr - BASE)
    w = list(struct.unpack('<%dH' % (n // 2), raw[src - BASE:src - BASE + n]))
    w = [w[i ^ 1] if i ^ 1 < len(w) else w[i] for i in range(len(w))]
    br = records(w)
    producer, store = br[22][1], br[23][1]
    assert producer == [0x1506, 0x0060, 0x1063, 0x0000, 0x0030, 0x0000]
    assert store == [0x1e05, 0x8fe0, 0x9fe2, 0x0034, 0x0035]
    return dict(words=words, fields=fields, records=rr, producer=producer, store=store, cluster_max=cluster[-1])


def build_program(slot):
    if not 0 <= slot < 6:
        raise ValueError('slot 0..5')
    s = source(); original = s['words']; rr = s['records']; base = 48 * slot
    cable_in1 = 0x200a + 4 * slot
    gate_in = 0x200a + 4 * slot + GATE_INPUT - 1
    g = 0xc034 + 8 * slot
    L = layout(slot, s['cluster_max'])
    assert not L['compact']
    la, lb = L['la'], L['lb']
    mapping = dict(L['map'])
    mapping.update({0x2004: lb, 0x2005: 0xc035 + 8 * slot, 0x2006: 0xc033 + 8 * slot, 0x2007: L['const_y']})
    mapping[0xa000] = 0x200b + 4 * slot
    mapping[0xa116] = mapping[XH]            # previous gate
    mapping.update(L['cap'])
    t = original.copy()
    for i in s['fields']:
        t[i] = mapping[original[i]]
    # rec 3: third move 'load r4 <- A118' -> 'load r0 <- gate'
    p3 = rr[3][0]
    assert t[p3:p3 + 7] == [0x3e07, 0x8fe0, 0x9fe2, 0x4fe4, mapping[0x68], mapping[0x2b], 0xa118]
    t[p3 + 3] = 0x0fe4
    t[p3 + 6] = gate_in
    # rec 4: '0803 2ecc 3002' -> '1804 2c0a 8fe0 FB' + '0001'
    p4 = rr[4][0]
    assert t[p4:p4 + 3] == [0x0803, 0x2ecc, 0x3002]
    t = t[:p4] + [0x1e05, 0x8fe0, 0x2fe2, mapping[X], mapping[XH], 0x0902, 0x2c0a, 0x0001] + t[p4 + 3:]
    init_store = s['store'].copy(); init_store[-2:] = [L['const_x'], L['const_y']]
    chain1 = mixer_chain([cable_in1] * 4, [g] * 5) + [0x0c03, 0x8fe0, la]
    chain2 = mixer_chain([la, la, cable_in1, cable_in1], [g] * 5) + [0x0c03, 0x8fe0, lb]
    pre = s['producer'] + init_store + chain1 + chain2
    tail = [0x1e05, 0x0fe0, 0x1fe2, L['cap'][0x2008], L['cap'][0x200a],
            0x1e05, 0x8fe0, 0x9fe2, 0x2022 + 6 * slot, 0x2025 + 6 * slot]
    words = t[:2] + pre + t[2:-5] + tail + t[-5:]
    words[-1] = 1 if len(words) % 2 == 0 else 0
    out = records(words)
    body = serial(words)
    h = list(struct.unpack('<%dH' % (len(body) // 2), body))
    assert [h[i ^ 1] if i ^ 1 < len(h) else h[i] for i in range(len(h))] == words
    return dict(serialized=body, words=words, records=len(out),
                private=sorted({v for v in mapping.values() if v < 0x1000} | {la, lb}),
                bindings=dict(pitch=hex(cable_in1) + ' via x10 MAC -> ' + hex(lb), gate=hex(gate_in),
                              gate_store=hex(mapping[X]), gate_prev=hex(mapping[XH]), range=hex(0xc035 + 8 * slot),
                              color=hex(0xc033 + 8 * slot), const=hex(L['const_y']), a000=hex(0x200b + 4 * slot),
                              out1=hex(0x2022 + 6 * slot), out2=hex(0x2025 + 6 * slot)))

if __name__ == '__main__':
    import json
    for slot in range(6):
        b = build_program(slot)
        print(slot, len(b['serialized']), b['records'], hashlib.sha256(b['serialized']).hexdigest()[:16], json.dumps(b['bindings']))
