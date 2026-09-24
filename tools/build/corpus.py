"""All parseable ESC2 programs we have locally: AIRA stock, SYSTEM-1m main+secondary, TR-8 main+secondary."""
import struct, json
from pathlib import Path
from esc import MAIN, SEC, AIRA_STOCK, BASE, records, swap
from scan_programs import scan

TR8 = Path('C:/Users/admin/Documents/Codex/2026-09-22/files-mentioned-by-the-user-handoff/work/tr8_firmware')


def body(img, desc):
    dst, n, src = struct.unpack_from('<III', img, desc)
    h = struct.unpack('<%dH' % (n // 2), img[src - BASE:src - BASE + n])
    return dst, n, src, swap(list(h))


def load():
    progs = []  # (name, words)
    seen = set()
    def add(name, w):
        k = tuple(w)
        if k in seen:
            return
        seen.add(k)
        progs.append((name, w))
    for s in range(6):
        for t in range(49):
            d = struct.unpack_from('<I', AIRA_STOCK, 0x8d184 + s * 0x188 + 4 * t)[0] - BASE
            dst, n, src, w = body(AIRA_STOCK, d)
            try:
                records(w)
            except AssertionError:
                continue
            add(f'aira s{s} t{t}', w)
    for name, img in (('s1m-main', MAIN), ('s1m-sec', SEC)):
        for off in sorted(scan(img)):
            dst, n, src, w = body(img, off)
            add(f'{name} {off:#x}', w)
    for name in ('main', 'secondary'):
        img = (TR8 / f'tr8_{name}.bin').read_bytes()
        for off in sorted(scan(img)):
            dst, n, src, w = body(img, off)
            add(f'tr8-{name} {off:#x}', w)
    return progs

if __name__ == '__main__':
    P = load()
    import collections
    c = collections.Counter(n.split()[0] for n, _ in P)
    print(len(P), c)
    print('records', sum(len(records(w)) for _, w in P))
