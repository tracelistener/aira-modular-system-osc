"""Shared offline helpers for the cowbell continuation (read-only on firmware files)."""
from pathlib import Path
import sys, struct
OLD = Path('C:/Users/admin/Documents/Codex/2026-09-22/files-mentioned-by-the-user-handoff')
sys.path.insert(0, str(OLD / 'work'))
from next_system_interface import expanded, records, BASE  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MAIN = (ROOT / 'work/cowbell/main.bin').read_bytes()
SEC = expanded()
AIRA_STOCK = Path('C:/Users/admin/Documents/Codex/2026-08-23/i-ah/work/AIRA_v105_build0493_application_decompressed.bin').read_bytes()


def swap(h):
    return [h[i ^ 1] if i ^ 1 < len(h) else h[i] for i in range(len(h))]


def prog_at(img, desc_off):
    """desc_off = image offset of {dst,len,src} descriptor."""
    dst, n, src = struct.unpack_from('<III', img, desc_off)
    h = struct.unpack('<%dH' % (n // 2), img[src - BASE:src - BASE + n])
    return dict(dst=dst, n=n, src=src, words=swap(list(h)))


def fmt(r):
    return ' '.join('%04x' % x for x in r)


def dump(words, lo=0, hi=None, mark=()):
    rr = records(words)
    hi = len(rr) if hi is None else hi
    for j in range(lo, hi):
        p, r = rr[j]
        m = '*' if any(x in r[1:] for x in mark) else ' '
        print('%s%4d %5d  %s' % (m, j, p, fmt(r)))
    return rr
