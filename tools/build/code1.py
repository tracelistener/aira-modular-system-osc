"""Decode the SYSTEM-1 plug-out hardware payload (Code1.Dat) into main/secondary ESC2 ARM images (in memory)."""
import struct, sys
sys.path.insert(0, 'C:/Users/admin/Documents/Codex/2026-08-23/i-ah/work')
from analyze_system1_code_dat import xor_decode, reconstruct_bank
from decompress_aira_application import decompress_lzss
SRC = r'C:/Program Files/Common Files/VST3/Roland/SYSTEM-1/Script/Code1.Dat'

def images():
    dec = xor_decode(open(SRC, 'rb').read())
    out = {}
    for name, start, populated in (("main", 0, 840), ("secondary", 2048, 265)):
        c = reconstruct_bank(dec, start, populated)
        load, delta, stored, checksum, entry, size = struct.unpack_from('<6I', c, 0x28)
        exp, used = decompress_lzss(c[delta:delta + stored], size)
        assert used == stored
        out[name] = dict(load=load, entry=entry, img=exp, record=c[:40].rstrip(b'\0').decode('ascii', 'replace'))
    return out
