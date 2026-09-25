"""REC/PLAY from a jack: rewrite the SCOOPER's raw-input gatherer (0x6009A0F4, build 0493 layout).

Stock routine: raw[0..2] = GPIO 0x4002D034 bits 12/13/15 (REC/PLAY, GRF5, GRF6 buttons; pressed = 0 for REC/PLAY),
raw[3] = SYNC TRIG CV flag (DSP read-back, 0x6008DB40), raw[4] = SCATTER CV flag (0x6008DB44).
Patched routine: a high SCATTER-CV gate holds REC/PLAY's input 'pressed' (raw[0] = 0), exactly like a finger on
the button (short trigger = press, gate held about 2 s = hold-to-delete); raw[4] is held inactive so the SCATTER
jack no longer toggles SCATTER. SYNC TRIG CV and all three physical buttons are unchanged.
Offline only: assembles, checks size/literals, emulates every input combination.
"""
import struct, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'deps'))
from keystone import Ks, KS_ARCH_ARM, KS_MODE_THUMB
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_THUMB
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_LR, UC_ARM_REG_SP
from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB

B = 0x60000000
FN, FN_END = 0x6009A0F4, 0x6009A126          # routine start, next function (config getter)
LIT_GPIO, LIT_F3, LIT_F4 = 0x6009A134, 0x6009A138, 0x6009A13C
GPIO, FLAG3, FLAG4 = 0x4002D000, 0x6008DB40, 0x6008DB44
STOCK_BYTES_SHA = None

ASM = """
    ldr   r1, [pc, #{g}]
    ldr   r2, [r1, #0x34]
    ldr   r3, [pc, #{f4}]
    ldr   r3, [r3]
    ubfx  r1, r2, #12, #1
    cbz   r3, keep
    movs  r1, #0
keep:
    str   r1, [r0]
    ubfx  r1, r2, #13, #1
    str   r1, [r0, #4]
    ubfx  r1, r2, #15, #1
    str   r1, [r0, #8]
    ldr   r1, [pc, #{f3}]
    ldr   r1, [r1]
    cbz   r1, f3z
    movs  r1, #1
f3z:
    str   r1, [r0, #12]
    movs  r1, #0
    str   r1, [r0, #16]
    bx    lr
"""


def assemble():
    ks = Ks(KS_ARCH_ARM, KS_MODE_THUMB)
    # pc-relative offsets depend on each ldr's position: assemble once with placeholders, then solve
    offs = {'g': 0, 'f4': 0, 'f3': 0}
    for _ in range(3):
        enc, _ = ks.asm(ASM.format(**offs), FN)
        code = bytes(enc)
        md = Cs(CS_ARCH_ARM, CS_MODE_THUMB)
        ldrs = [i for i in md.disasm(code, FN) if i.mnemonic == 'ldr' and 'pc' in i.op_str]
        want = [LIT_GPIO, LIT_F4, LIT_F3]
        new = {}
        for key, ins, lit in zip(('g', 'f4', 'f3'), ldrs, want):
            new[key] = lit - ((ins.address + 4) & ~3)
        if new == offs:
            return code
        offs = new
    raise RuntimeError('literal offsets did not converge')


def patch(app):
    app = bytearray(app)
    assert struct.unpack_from('<I', app, LIT_GPIO - B)[0] == GPIO
    assert struct.unpack_from('<I', app, LIT_F3 - B)[0] == FLAG3
    assert struct.unpack_from('<I', app, LIT_F4 - B)[0] == FLAG4
    code = assemble()
    room = FN_END - FN
    assert len(code) <= room, (len(code), room)
    nop = b'\x00\xbf'
    app[FN - B:FN_END - B] = code + nop * ((room - len(code)) // 2)
    return bytes(app), code


def emulate(app):
    """Run the patched routine for every combination of the three pins and both CV flags."""
    results = []
    for bits in range(8):
        for f3 in (0, 7):
            for f4 in (0, 1):
                u = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
                u.mem_map(B, 0x100000); u.mem_write(B, app[:0x100000])
                u.mem_map(GPIO, 0x1000)
                port = ((bits & 1) << 12) | (((bits >> 1) & 1) << 13) | (((bits >> 2) & 1) << 15) | 0x4000_0FFF
                u.mem_write(GPIO + 0x34, struct.pack('<I', port))
                u.mem_write(FLAG3, struct.pack('<I', f3)); u.mem_write(FLAG4, struct.pack('<I', f4))
                u.mem_map(0x20000000, 0x10000)
                buf = 0x20001000
                u.mem_write(buf, b'\xAA' * 20)
                u.reg_write(UC_ARM_REG_R0, buf); u.reg_write(UC_ARM_REG_SP, 0x2000F000)
                u.reg_write(UC_ARM_REG_LR, 0x20000001)
                u.emu_start(FN | 1, 0x20000000, count=100)
                raw = struct.unpack('<5I', u.mem_read(buf, 20))
                want = ((bits & 1) if not f4 else 0, (bits >> 1) & 1, (bits >> 2) & 1, 1 if f3 else 0, 0)
                assert raw == want, (bits, f3, f4, raw, want)
                results.append((bits, f3, f4, raw))
    return results


if __name__ == '__main__':
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else \
        Path(__file__).resolve().parents[1] / 'selector-v32/application.bin'
    app = src.read_bytes()
    new, code = patch(app)
    md = Cs(CS_ARCH_ARM, CS_MODE_THUMB)
    for i in md.disasm(new[FN - B:FN_END - B], FN):
        print('%08x  %-6s %s' % (i.address, i.mnemonic, i.op_str))
    res = emulate(new)
    diff = [i for i in range(len(app)) if app[i] != new[i]]
    print('code bytes', len(code), 'of', FN_END - FN, '| emulated cases', len(res), 'all correct',
          '| changed bytes', len(diff), 'range', hex(B + min(diff)), '-', hex(B + max(diff)))
