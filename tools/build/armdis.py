"""Offline Thumb-2 helpers for the AIRA application image (read-only)."""
import struct
from functools import lru_cache
from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB

B = 0x60000000
STOCK = 'C:/Users/admin/Documents/Codex/2026-08-23/i-ah/work/AIRA_v105_build0493_application_decompressed.bin'
APP = open(STOCK, 'rb').read()
md = Cs(CS_ARCH_ARM, CS_MODE_THUMB)
md.detail = False


def dis(addr, n=40, img=APP):
    off = addr - B
    out = []
    for ins in md.disasm(img[off:off + n * 4], addr):
        out.append('%08x  %-8s %s' % (ins.address, ins.mnemonic, ins.op_str))
        if len(out) >= n:
            break
    return '\n'.join(out)


def u32(addr, img=APP):
    return struct.unpack_from('<I', img, addr - B)[0]


@lru_cache(None)
def bl_index(img=APP):
    """All Thumb-2 BL/BLX(imm) sites -> target (scans every halfword boundary)."""
    idx = {}
    for off in range(0, len(img) - 4, 2):
        h1, h2 = struct.unpack_from('<HH', img, off)
        if (h1 & 0xF800) == 0xF000 and (h2 & 0xC000) == 0xC000:
            s = (h1 >> 10) & 1; imm10 = h1 & 0x3FF
            j1 = (h2 >> 13) & 1; j2 = (h2 >> 11) & 1; imm11 = h2 & 0x7FF
            i1 = 1 - (j1 ^ s); i2 = 1 - (j2 ^ s)
            imm = (s << 24) | (i1 << 23) | (i2 << 22) | (imm10 << 12) | (imm11 << 1)
            if s:
                imm -= 1 << 25
            pc = B + off + 4
            blx = not (h2 & 0x1000)
            tgt = (pc + imm) & (~3 if blx else ~0)
            idx[B + off] = (tgt, 'blx' if blx else 'bl')
    return idx


def callers(target, img=APP):
    return sorted(a for a, (t, k) in bl_index(img).items() if t == (target & ~1))


def literal_refs(value, img=APP):
    pat = struct.pack('<I', value)
    out, p = [], img.find(pat)
    while p >= 0:
        if p % 4 == 0:
            out.append(B + p)
        p = img.find(pat, p + 1)
    return out
