"""SYSTEM-1m OSC1 cells (0, 1, 2) with the proven v2 MIDI adapter. Offline builder; no hardware I/O.

Cells 0/1/2 share the same interface (verified from the four original voice placements):
inputs 2004 pitch, 2005 range, 2006 colour, 2007 constant; outputs 2008 main, 200A/200C saw;
scratch scalars 19/2B/32/68; working cluster inside E0..FF; no tag-A dependency.
Adapter (identical to v2 'mac10', hardware-verified on cell 2):
  2004 <- (8g^2+2g)*CV via two copied native MIXER MAC chains, g = C034 (P4/100; 100 -> x10)
  2005 <- C035 (P1 RANGE table), 2006 <- C033 (P3 COLOR), 2007 <- original 1506 constant
  out1 <- 2008 capture (main), out2 <- 200A capture (saw, hard-syncs native oscillators)
"""
from functools import lru_cache
import hashlib, struct
from next_system_interface import expanded, program, records, BASE
from system_cell2_probe_program import serial
from system_cell2_midi_program import mixer_chain

SYS_INPUTS = (0x2004, 0x2005, 0x2006, 0x2007)
SYS_OUTPUTS = (0x2008, 0x200a, 0x200c)
SCALARS = (0x19, 0x2b, 0x32, 0x68)
SOURCE_SHA = '14218bb15c4c128d6df17f888ba1939a873358b3c6b40c4eab89837fa0cde71e'


@lru_cache(maxsize=None)
def cell_source(cell):
    raw = expanded()
    assert hashlib.sha256(raw).hexdigest() == SOURCE_SHA
    variants = [program(raw, 0x4c7c4 + 0x60 * t, cell) for t in (0, 2, 4, 6)]
    words = variants[0]['words']
    assert all(len(p['words']) == len(words) for p in variants)
    rr = records(words)
    fields = sorted(i for i in range(len(words)) if len({p['words'][i] for p in variants}) > 1)
    vals = {words[i] for i in fields}
    # The six SYSTEM-1 "added" waves also read one per-voice host register (A000/A001); it is loaded once
    # into local E0 and never read explicitly again. No other tag-A register is accepted here (CB also
    # reads A116/A118 and is rejected until those are understood).
    tag_a = {v for v in vals if v >> 12 == 0xa}
    assert tag_a <= {0xa000}, (cell, [hex(v) for v in tag_a])
    assert {v for v in vals if v >= 0x1000} - tag_a == set(SYS_INPUTS + SYS_OUTPUTS), cell
    assert {v for v in vals if v < 0xe0} == set(SCALARS), cell
    cluster_max = max(v for v in vals if 0xe0 <= v < 0x1000)
    assert cluster_max - 0xe0 + 1 <= 40, (cell, hex(cluster_max))   # compact layout needs n + 8 <= 48
    assert words[:2] == [0xa02, 0xff71] and words[-5:-1] == [0xa02, 0xff70, 0xb02, 0xf8]
    # the original fixed base producer of the constant input (same for every cell)
    base_ptr = struct.unpack_from('<I', raw, 0x4c784)[0]
    dest, n, src = struct.unpack_from('<III', raw, base_ptr - BASE)
    w = list(struct.unpack('<%dH' % (n // 2), raw[src - BASE:src - BASE + n]))
    w = [w[i ^ 1] if i ^ 1 < len(w) else w[i] for i in range(len(w))]
    br = records(w)
    producer, store = br[22][1], br[23][1]
    assert producer == [0x1506, 0x0060, 0x1063, 0x0000, 0x0030, 0x0000]
    assert store == [0x1e05, 0x8fe0, 0x9fe2, 0x0034, 0x0035]
    return dict(words=words, fields=fields, records=len(rr), producer=producer, store=store, tag_a=sorted(tag_a),
                cluster_max=cluster_max,
                descriptors=[{k: v for k, v in p.items() if k != 'words'} for p in variants])


def layout(slot, cluster_max):
    """Private-memory map for one slot (48 values).
    standard (cluster within E0..FF, hardware-verified with cells 0/1/2/10/14/21):
        E0..FF -> 0..31, scalars 32..35, 1506 results 36/37, captures 2008/200A/200C -> 38/40/42, MAC 44/46
    compact (cluster runs past FF, n = cluster size <= 40):
        E0.. -> 0..n-1 (affine, holes kept), scalars n..n+3, constant (2007) n+4,
        MAC la n+5 / lb n+6, 200A capture n+7; values with disjoint lifetimes share:
        1506 first result and 2008 capture -> la (written before chain 1 / after chain 2 read it),
        200C capture -> lb (written by the epilogue after the prologue consumed lb)."""
    base = 48 * slot
    if cluster_max <= 0xff:
        m = {x: base + x - 0xe0 for x in range(0xe0, 0x100)}
        m.update({0x19: base + 32, 0x2b: base + 33, 0x32: base + 34, 0x68: base + 35})
        return dict(map=m, const_x=base + 36, const_y=base + 37, la=base + 44, lb=base + 46,
                    cap={0x2008: base + 38, 0x200a: base + 40, 0x200c: base + 42}, compact=False)
    n = cluster_max - 0xe0 + 1
    m = {x: base + x - 0xe0 for x in range(0xe0, cluster_max + 1)}
    m.update({0x19: base + n, 0x2b: base + n + 1, 0x32: base + n + 2, 0x68: base + n + 3})
    la, lb = base + n + 5, base + n + 6
    return dict(map=m, const_x=la, const_y=base + n + 4, la=la, lb=lb,
                cap={0x2008: la, 0x200a: base + n + 7, 0x200c: lb}, compact=True)


def build_program(slot, cell):
    if not 0 <= slot < 6:
        raise ValueError('slot 0..5')
    s = cell_source(cell); original = s['words']; base = 48 * slot
    cable_in1 = 0x200a + 4 * slot
    g = 0xc034 + 8 * slot
    L = layout(slot, s['cluster_max'])
    la, lb = L['la'], L['lb']
    mapping = dict(L['map'])
    mapping.update({0x2004: lb, 0x2005: 0xc035 + 8 * slot, 0x2006: 0xc033 + 8 * slot, 0x2007: L['const_y']})
    mapping[0xa000] = 0x200b + 4 * slot    # per-voice host register of the added waves -> cable input 2
    mapping.update(L['cap'])
    transformed = original.copy()
    for i in s['fields']:
        transformed[i] = mapping[original[i]]
    assert [i for i, (a, b) in enumerate(zip(original, transformed)) if a != b] == s['fields']
    assert len(records(transformed)) == s['records']
    init_store = s['store'].copy(); init_store[-2:] = [L['const_x'], L['const_y']]
    chain1 = mixer_chain([cable_in1] * 4, [g] * 5) + [0x0c03, 0x8fe0, la]
    chain2 = mixer_chain([la, la, cable_in1, cable_in1], [g] * 5) + [0x0c03, 0x8fe0, lb]
    pre = s['producer'] + init_store + chain1 + chain2
    tail = [0x1e05, 0x0fe0, 0x1fe2, L['cap'][0x2008], L['cap'][0x200a],
            0x1e05, 0x8fe0, 0x9fe2, 0x2022 + 6 * slot, 0x2025 + 6 * slot]
    words = transformed[:2] + pre + transformed[2:-5] + tail + transformed[-5:]
    rr = records(words)
    assert words[:2] + words[2 + len(pre):-(5 + len(tail))] + words[-5:] == transformed
    # Terminal word invariant, exceptionless across all 294 native AIRA programs and all 24 SYSTEM-1m
    # cells: final halfword = 1 when the total halfword count is even, 0 when odd. Inserting the adapter
    # changes the parity, so the donor's terminal must be recomputed (v3 SQR shipped odd+1 and crashed).
    assert words[-1] in (0, 1)
    words[-1] = 1 if len(words) % 2 == 0 else 0
    priv = [v for v in mapping.values() if v < 0x1000] + [la, lb]
    assert min(priv) >= base and max(priv) <= base + 47
    body = serial(words)
    stored = list(struct.unpack('<%dH' % (len(body) // 2), body[:len(body) - len(body) % 4] if False else body))
    back = [stored[i ^ 1] if i ^ 1 < len(stored) else stored[i] for i in range(len(stored))]
    assert back == words
    meta = dict(slot_zero_based=slot, physical_slot=slot + 1, cell=cell, program_bytes=len(body),
                record_count=len(rr), program_sha256=hashlib.sha256(body).hexdigest(),
                kernel_field_rewrites=len(s['fields']),
                bindings={'2004': hex(lb) + ' (x10 MAC of ' + hex(cable_in1) + ')', '2005': hex(0xc035 + 8 * slot),
                          '2006': hex(0xc033 + 8 * slot), '2007': hex(L['const_y'])}, layout='compact' if L['compact'] else 'standard',
                outputs={'out1_main_2008': hex(0x2022 + 6 * slot), 'out2_200A': hex(0x2025 + 6 * slot)})
    return dict(serialized=body, words=words, metadata=meta)


if __name__ == '__main__':
    import json
    for cell in (0, 1, 2):
        for slot in range(6):
            b = build_program(slot, cell)
            if slot in (0, 2):
                print(json.dumps(b['metadata']))
    # cell 2 = the hardware-verified v2 program except the corrected terminal word
    from system_cell2_midi_program import build_program as v2
    for slot in range(6):
        a, b = build_program(slot, 2)['words'], v2(slot, 'mac10')['words']
        assert a[:-1] == b[:-1] and (a[-1], b[-1]) == (1, 0), slot
    print('cell 2 = verified v2 mac10 programs except terminal 0 -> 1 (even length), all six slots')
