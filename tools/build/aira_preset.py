"""Byte-exact Python port of the Customizer's PatchFileIO.SavePatchFile (patchfileio.js).

Layout (1212 bytes, no checksum): 'HabPatchFile0001' | 'AiraEfx ' | 'Patch           ' |
main values x16 | 8 sub-modules x 8 bytes | 26 outputs x 42 inputs connection bytes.
Verified by reproducing the Roland-serialized probe presets byte for byte (see __main__).
"""
from pathlib import Path
import json, hashlib

TEMPLATE = Path('C:/Users/admin/AppData/Local/Roland/AIRA Modular Customizer/bin/SCOOPER_Initial.bin')
TEMPLATE_SHA = '51d59239d3e0cafbb6939c1f81227d620f51805efa21767295fb5f294a8308d0'
OUT = lambda m, i: 10 + 2 * (m - 1) + i
IN = lambda m, i: 10 + 4 * (m - 1) + i


def template_main():
    t = TEMPLATE.read_bytes()
    assert hashlib.sha256(t).hexdigest() == TEMPLATE_SHA
    main = list(t[40:56])
    return main


def make_preset(slots, routes, main=None):
    """slots: {1..6: [type,p1,p2,p3,p4]}; routes: [(out_connector, in_connector, value)]."""
    main = template_main() if main is None else main
    b = bytearray()
    b += b'HabPatchFile0001' + b'AiraEfx ' + b'Patch           '
    b += bytes(main[:11] + [0] * 5)
    for m in range(1, 9):
        v = list(slots.get(m, [0, 0, 0, 0, 0])) if m <= 6 else [0] * 5
        b += bytes(v + [0, 0, 0])
    matrix = bytearray(26 * 42)
    for o, i, v in routes:
        assert 0 <= o < 22 and 0 <= i < 34
        matrix[o * 42 + i] = v
    b += matrix
    assert len(b) == 1212
    return bytes(b)


def route_list(spec_routes):
    r = []
    for item in spec_routes:
        om, oi, im, ii = item[:4]
        color = item[4] if len(item) > 4 else 1
        r.append((oi if om == 0 else OUT(om, oi), ii if im == 0 else IN(im, ii), color))
    return r


if __name__ == '__main__':
    # Reproduce the six Roland-serialized probe presets exactly.
    root = Path(__file__).resolve().parent.parent
    val = json.loads((root / 'outputs/system-cell2-fixed-probe/presets/VALIDATION.json').read_text())
    for p in val['presets']:
        slots = {s + 1: v for s, v in enumerate(p['slots'])}
        data = make_preset(slots, [tuple(x) for x in p['routes']])
        ref = (root / 'outputs/system-cell2-fixed-probe/presets' / p['file']).read_bytes()
        assert data == ref, p['file']
    print('reproduced', len(val['presets']), 'Roland-serialized presets byte-for-byte')
