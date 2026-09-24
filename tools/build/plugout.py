"""Read-only helpers for the installed SYSTEM-1 plug-out DLL (x64)."""
import struct, re
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
PATH = r'C:/Program Files/Common Files/VST3/Roland/SYSTEM-1/SYSTEM-1(VST3 64bit).vst3'
B = open(PATH, 'rb').read()
TEXT_RAW, TEXT_VA, TEXT_SIZE = 0x400, 0x1000, 0x3b1200
RDATA_RAW, RDATA_VA = 0x3b1600, 0x3b3000
DATA_RAW, DATA_VA = 0x507800, 0x50a000
md = Cs(CS_ARCH_X86, CS_MODE_64)
md.detail = False

def f32(u):
    return struct.unpack('<f', struct.pack('<I', u & 0xffffffff))[0]

def va2off(va):
    if TEXT_VA <= va < TEXT_VA + TEXT_SIZE: return va - TEXT_VA + TEXT_RAW
    if RDATA_VA <= va < RDATA_VA + 0x15609e: return va - RDATA_VA + RDATA_RAW
    if DATA_VA <= va < DATA_VA + 0x17f50: return va - DATA_VA + DATA_RAW
    return None

def dis(off, n):
    return list(md.disasm(B[off:off + n], off - TEXT_RAW + TEXT_VA))

def aligned_start(target, back=0x300):
    for s in range(target - back, target):
        for i in md.disasm(B[s:target + 16], s):
            if i.address == target:
                return s
            if i.address > target:
                break
    return None

def ctor_fields(lo, hi, reg='rcx'):
    s = aligned_start(lo)
    fields = {}
    for i in md.disasm(B[s:hi], s):
        m = re.match(r'dword ptr \[%s \+ (0x[0-9a-f]+)\], (0x[0-9a-f]+|\d+)$' % reg, i.op_str)
        if i.mnemonic == 'mov' and m:
            fields[int(m.group(1), 16)] = int(m.group(2), 0)
    return fields

import json as _json, os as _os
_CF = _os.path.join(_os.path.dirname(__file__), 'ctor_fields.json')
CTOR = {int(k, 16): v for k, v in _json.load(open(_CF)).items()} if _os.path.exists(_CF) else {}

def annotate(i):
    s = '%08x  %-7s %s' % (i.address, i.mnemonic, i.op_str)
    for m in re.finditer(r'\[(r\w+) \+ (0x[0-9a-f]+)\]', i.op_str):
        d = int(m.group(2), 16)
        if d in CTOR:
            s += '   ; [%s]=%.9g' % (hex(d), f32(CTOR[d]))
    return s

def fn_range(entry):
    """entry: file offset of function start; returns list of instrs until ret followed by int3."""
    out = []
    for i in md.disasm(B[entry:entry + 0x40000], entry):
        out.append(i)
        if i.mnemonic == 'ret' and B[i.address + 1] == 0xcc:
            break
    return out

def rip_value(i, kind='f'):
    """Resolve [rip + disp] for an instruction disassembled at FILE offsets; returns (va, value)."""
    m = re.search(r'\[rip ([+-]) (0x[0-9a-f]+)\]', i.op_str)
    if not m:
        return None
    disp = int(m.group(2), 16) * (1 if m.group(1) == '+' else -1)
    va = (i.address - TEXT_RAW + TEXT_VA) + i.size + disp
    off = va2off(va)
    if off is None:
        return (va, None)
    if kind == 'd':
        return (va, struct.unpack_from('<d', B, off)[0])
    return (va, struct.unpack_from('<f', B, off)[0])
