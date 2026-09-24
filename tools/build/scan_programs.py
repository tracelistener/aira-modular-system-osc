"""Enumerate every {dst,len,src} DSP program descriptor in an image (records() must parse)."""
import struct, json, sys
from esc import MAIN, SEC, BASE, records, swap

def scan(img):
    found = {}
    n = len(img)
    for off in range(0, n - 12, 4):
        dst, ln, src = struct.unpack_from('<III', img, off)
        if not (BASE <= src < BASE + n and 8 <= ln < 0x10000 and ln % 2 == 0 and src + ln <= BASE + n):
            continue
        if dst > 0x10000:
            continue
        h = struct.unpack('<%dH' % (ln // 2), img[src - BASE:src - BASE + ln])
        w = swap(list(h))
        try:
            rr = records(w)
        except AssertionError:
            continue
        found[off] = dict(desc=off, dst=dst, n=ln, src=src, nrec=len(rr))
    return found

if __name__ == '__main__':
    out = {}
    for name, img in (('main', MAIN), ('sec', SEC)):
        f = scan(img)
        out[name] = list(f.values())
        srcs = {}
        for v in f.values():
            srcs.setdefault(v['src'], []).append(v)
        print(name, 'descriptors', len(f), 'distinct bodies', len(srcs))
    json.dump(out, open('programs.json', 'w'), indent=1)
