"""SYSTEM cell 2 with a cable pitch input (v2). Offline builder; no hardware I/O.

Hardware result of the fixed probe (2026-09-22, USB-measured):
    f = 16.3516 Hz * 2**(in2004) * in2005      (within ~0.05 cent)
    2008 = triangle, 200A = 200C = saw, 2006 = triangle shape/colour.
AIRA MIDINOTE publishes note/120, so in2004 = 10*CV with in2005 = 0.5 is concert pitch.

Variants (physical slot selects the variant; every type-28 slot gets one):
  'cable': 2004 <- cable input 1 (raw CV). Used as a precise CV meter.
  'mac10': 2004 <- two copied native MIXER multiply-accumulate chains:
           A = 4*g*CV;  B = 2*g*A + 2*g*CV = (8g^2 + 2g)*CV,  g = C034 (P4/100).
           P4 = 100 -> 10*CV (concert with P1 = 2).  P4 = 25 -> 1*CV (identity).
Common: 2005 <- C035 (P1 via float table: 0.125,0.25,0.5,1,2,4), 2006 <- C033 (P3/100),
        2007 <- original 1506 constant, out1 <- triangle, out2 <- saw.
The kernel's 291 non-relocating halfwords are unchanged, exactly as in the sounding probe.
"""
from pathlib import Path
import hashlib, struct
from system_cell2_probe_program import source_material, serial
from next_system_interface import records

SYS_INPUTS = (0x2004, 0x2005, 0x2006, 0x2007)
SYS_OUTPUTS = (0x2008, 0x200a, 0x200c)
VARIANTS = ('cable', 'mac10')
SLOT_VARIANTS = ('mac10', 'cable', 'mac10', 'cable', 'mac10', 'cable')  # physical slots 1..6
RANGE_TABLE = (0.125, 0.25, 0.5, 1.0, 2.0, 4.0)

# Native AIRA MIXER type 10, slot 0, records 1..5 (hardware-proven 4-term chain):
#   1e05 2fe0 7fe2 IN1 G1 | 5f07 0487 1042 2fe0 7fe2 IN2 G2 |
#   5408 048f 9ec2 2fe2 7fe4 0000 IN3 G3 | 5408 048f 9ec2 2fe2 7fe4 0000 IN4 G4 |
#   2806 048f 9ec2 7fe2 0000 G5
# Only the relocating operands (IN*, G*) are substituted.
MIXER_CHAIN = (
    ([0x1e05, 0x2fe0, 0x7fe2], ('IN1', 'G1')),
    ([0x5f07, 0x0487, 0x1042, 0x2fe0, 0x7fe2], ('IN2', 'G2')),
    ([0x5408, 0x048f, 0x9ec2, 0x2fe2, 0x7fe4, 0x0000], ('IN3', 'G3')),
    ([0x5408, 0x048f, 0x9ec2, 0x2fe2, 0x7fe4, 0x0000], ('IN4', 'G4')),
    ([0x2806, 0x048f, 0x9ec2, 0x7fe2, 0x0000], ('G5',)),
)


def verify_mixer_template(app: bytes) -> None:
    """Check the chain template against the stock AIRA MIXER body in every slot."""
    base = 0x60000000
    for slot in range(6):
        p = struct.unpack_from('<I', app, 0x8D184 + slot * 0x188 + 10 * 4)[0]
        d, n, s = struct.unpack_from('<III', app, p - base)
        w = struct.unpack('<%dH' % (n // 2), app[s - base:s - base + n])
        w = [w[i ^ 1] if i ^ 1 < len(w) else w[i] for i in range(len(w))]
        rr = records(w)
        ops = dict(IN1=0x200a + 4 * slot, IN2=0x200b + 4 * slot, IN3=0x200c + 4 * slot, IN4=0x200d + 4 * slot,
                   G1=0xc032 + 8 * slot, G2=0xc033 + 8 * slot, G3=0xc034 + 8 * slot, G4=0xc035 + 8 * slot,
                   G5=0xc030 + 8 * slot)
        for (fixed, names), (_, rec) in zip(MIXER_CHAIN, rr[1:6]):
            assert rec == fixed + [ops[k] for k in names], (slot, [hex(x) for x in rec])


def mixer_chain(ins, gains):
    """ins: 4 operand addresses, gains: 5 operand addresses -> logical words."""
    ops = dict(IN1=ins[0], IN2=ins[1], IN3=ins[2], IN4=ins[3],
               G1=gains[0], G2=gains[1], G3=gains[2], G4=gains[3], G5=gains[4])
    out = []
    for fixed, names in MIXER_CHAIN:
        out += fixed + [ops[k] for k in names]
    return out


def build_program(slot, variant):
    if not isinstance(slot, int) or not 0 <= slot < 6:
        raise ValueError('slot must be 0..5')
    if variant not in VARIANTS:
        raise ValueError(variant)
    s = source_material(); original = s['words']; base = 48 * slot
    cable_in1 = 0x200a + 4 * slot
    g = 0xc034 + 8 * slot            # P4 coefficient (native OSCSAW P4 writer)
    la, lb = base + 44, base + 46    # private scratch for the MAC results
    mapping = {x: base + x - 0xe0 for x in range(0xe0, 0x100)}
    mapping.update({0x19: base + 32, 0x2b: base + 33, 0x32: base + 34, 0x68: base + 35})
    mapping.update({0x2004: cable_in1 if variant == 'cable' else lb,
                    0x2005: 0xc035 + 8 * slot,     # P1 float-table RANGE
                    0x2006: 0xc033 + 8 * slot,     # P3
                    0x2007: base + 37})
    mapping.update({x: base + 38 + (x - 0x2008) for x in SYS_OUTPUTS})
    transformed = original.copy(); edits = []
    for i in s['fields']:
        old = original[i]; transformed[i] = mapping[old]
        edits.append(dict(index=i, before=old, after=transformed[i]))
    assert [i for i, (a, b) in enumerate(zip(original, transformed)) if a != b] == s['fields']
    assert len(records(transformed)) == 78 and transformed[:2] == [0xa02, 0xff71]
    producer = s['producer'].copy()
    init_store = s['store'].copy(); init_store[-2:] = [base + 36, base + 37]
    pre = producer + init_store
    if variant == 'mac10':
        chain1 = mixer_chain([cable_in1] * 4, [g] * 5) + [0x0c03, 0x8fe0, la]
        chain2 = mixer_chain([la, la, cable_in1, cable_in1], [g] * 5) + [0x0c03, 0x8fe0, lb]
        pre += chain1 + chain2
    tri, saw = base + 38, base + 40
    tail = [0x1e05, 0x0fe0, 0x1fe2, tri, saw, 0x1e05, 0x8fe0, 0x9fe2, 0x2022 + 6 * slot, 0x2025 + 6 * slot]
    words = transformed[:2] + pre + transformed[2:-5] + tail + transformed[-5:]
    rr = records(words)
    kernel = words[:2] + words[2 + len(pre):-(5 + len(tail))] + words[-5:]
    assert kernel == transformed
    assert len(words) % 2 == 0
    # all private operands inside the 48-value slot stride
    priv = [v for v in mapping.values() if v < 0x1000] + ([la, lb] if variant == 'mac10' else [])
    assert min(priv) >= base and max(priv) <= base + 47
    body = serial(words)
    stored = list(struct.unpack('<%dH' % len(words), body))
    assert [stored[i ^ 1] for i in range(len(stored))] == words
    meta = dict(slot_zero_based=slot, physical_slot=slot + 1, variant=variant, program_bytes=len(body),
                record_count=len(rr), program_sha256=hashlib.sha256(body).hexdigest(),
                source_cell=2, kernel_field_rewrites=len(edits),
                bindings={'2004': hex(mapping[0x2004]), '2005': hex(mapping[0x2005]), '2006': hex(mapping[0x2006]),
                          '2007': hex(mapping[0x2007])},
                outputs={'out1_triangle': hex(0x2022 + 6 * slot), 'out2_saw': hex(0x2025 + 6 * slot)},
                mac=dict(gain=hex(g), scratch=[la, lb], formula='(8g^2+2g)*CV') if variant == 'mac10' else None)
    return dict(serialized=body, words=words, metadata=meta)


if __name__ == '__main__':
    import json
    from decompress_aira_application import decompress_lzss  # noqa: F401  (import check)
    app = Path(r'C:/Users/admin/Documents/Codex/2026-08-23/i-ah/work/AIRA_v105_build0493_application_decompressed.bin').read_bytes()
    verify_mixer_template(app)
    for slot, v in enumerate(SLOT_VARIANTS):
        b = build_program(slot, v)
        print(json.dumps(b['metadata']))
