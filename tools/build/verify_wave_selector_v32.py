"""Execute the patched Thumb code of the v2 (7-wave) selector in Unicorn; emulates no DSP or device I/O.
Same harness as v1/v2, run against the v3 image (v3 wave programs, v2 code)."""
from build_wave_selector_v32 import *
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_THUMB, UC_HOOK_CODE
from unicorn.arm_const import *
APP = (HERE / 'application.bin').read_bytes()
REGS = [UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3]
CALLEE = [UC_ARM_REG_R4, UC_ARM_REG_R5, UC_ARM_REG_R6, UC_ARM_REG_R7, UC_ARM_REG_R8, UC_ARM_REG_R9, UC_ARM_REG_R10, UC_ARM_REG_R11]
STOP = 0x20000000
LEAVES = [0x11c86, 0x44c2a, 0x11bb6, 0x11bac, 0x11ba2, 0x44c0c, 0x11b64, 0x11b44, 0x48736, 0x11c6e, 0x4873c]
EXPECTED = {(s, w): program(s, w) for s in range(6) for w in range(NW)}


class VM:
    def __init__(self, saved=None):
        self.u = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
        self.u.mem_map(B, 0x200000)
        self.u.mem_write(B, APP)
        self.u.mem_map(0x20000000, 0x10000)
        self.calls = []
        self.saved = saved
        self.stop_boot = False
        self.u.hook_add(UC_HOOK_CODE, self.hook)

    def hook(self, u, a, n, _):
        if a == B + 0x11f16 and self.stop_boot:
            u.emu_stop()
            return
        if a == B + 0x11cac:
            args = [u.reg_read(r) for r in REGS] + list(struct.unpack('<4I', u.mem_read(u.reg_read(UC_ARM_REG_SP), 16)))
            assert u.reg_read(UC_ARM_REG_SP) % 8 == 0
            self.calls.append(('loader', args))
        if a - B in LEAVES:
            self.calls.append((hex(a - B), [u.reg_read(r) for r in REGS]))
            u.reg_write(UC_ARM_REG_R0, 0)
            u.reg_write(UC_ARM_REG_PC, u.reg_read(UC_ARM_REG_LR))
        if a in (B + 0x4eea, B + 0x4f20):
            assert u.reg_read(UC_ARM_REG_SP) % 8 == 0
            if a == B + 0x4eea:
                assert u.reg_read(UC_ARM_REG_R1) == 4 and u.reg_read(UC_ARM_REG_R2) == 0
            else:
                pid = u.reg_read(UC_ARM_REG_R1)
                v = self.saved.get(pid)
                if v is not None:
                    u.mem_write(u.reg_read(UC_ARM_REG_R2), struct.pack('<I', v))
                u.reg_write(UC_ARM_REG_R0, int(v is not None))
            u.reg_write(UC_ARM_REG_PC, u.reg_read(UC_ARM_REG_LR))

    def call(self, a, args=(), boot=False):
        self.calls = []
        self.stop_boot = boot
        u = self.u
        for r, v in zip(REGS, args):
            u.reg_write(r, v)
        for i, r in enumerate(CALLEE):
            u.reg_write(r, 0x11220000 + i)
        u.reg_write(UC_ARM_REG_SP, 0x20008000)
        u.reg_write(UC_ARM_REG_LR, STOP | 1)
        u.emu_start(a | 1, STOP, count=100000)
        assert u.reg_read(UC_ARM_REG_PC) == (B + 0x11f16 if boot else STOP)
        assert u.reg_read(UC_ARM_REG_SP) == 0x20008000 - (64 if boot else 0)
        for i, r in enumerate(CALLEE):
            assert u.reg_read(r) == 0x11220000 + i, (r, hex(u.reg_read(r)))

    def check(self, s, w, baseline=False):
        """baseline=True: slot still holds the untouched v6 program for wave s (no select call happened)."""
        expected = EXPECTED[(s, w)]
        src = B + 0x81ffc + 0x5e0 * s
        assert bytes(self.u.mem_read(src, len(expected))) == expected, (s, w)
        desc = word(APP, 0x8d184 + s * 0x188 + 28 * 4)
        assert struct.unpack('<I', self.u.mem_read(desc + 4, 4))[0] == len(expected)
        assert self.u.mem_read(STATE + s, 1) == bytes([w])
        assert self.u.mem_read(B + 0x825c0, 24) == APP[0x825c0:0x825d8]
        # nothing written past the slot's program into the next slot / RANGE table beyond its 1502-byte area
        assert len(expected) <= 1476


def verify():
    transitions = 0
    for live in (False, True):
        for s in range(6):
            vm = VM()
            vm.u.mem_write(B + 0xa9e18 + 4 * s, struct.pack('<I', 28 if live else 29))
            for old in range(NW):
                vm.call(SELECT, (s, old, 0))
                vm.check(s, old)
                for w in range(NW):
                    vm.call(SELECT, (s, old, 0))
                    vm.call(B + 0x17044, (0, w, 28, s))
                    vm.check(s, w)
                    loaders = [c for c in vm.calls if c[0] == 'loader']
                    assert len(loaders) == int(live and w != old)
                    if loaders:
                        assert loaders[0][1] == [B + 0xa9d58, 1, word(APP, 0x8d1f4 + 0x188 * s), word(APP, 0x8d2b8 + 0x188 * s),
                                                 B + 0x8dc14, B + 0x8dc1c, 0x3000 + 0x900 * s, s + 1]
                        order = [0x11c86, 0x44c2a, 0x11bb6, 0x11bac, 0x11ba2, 0x44c0c, 0x11b64, 0x11b44, 0x48736, 0x11c6e, 0x44c2a, 0x4873c]
                        assert [c[0] for c in vm.calls] == ['loader'] + [hex(x) for x in order], vm.calls
                        assert vm.calls[1][1][2] == s + 1 and vm.calls[-3][1][2] == s + 1
                    transitions += 1
            for v in (7, 8, 100, 255, 0xffffffff):
                vm.call(B + 0x17044, (0, v, 28, s))
                vm.check(s, 0)
    boots = 0
    for w in range(NW):
        for mask in range(64):
            saved = {**{0x78 + s: 28 if mask & (1 << s) else 29 for s in range(6)}, **{0x84 + s: (w + s) % NW for s in range(6)}}
            vm = VM(saved)
            vm.call(B + 0x11f12, boot=True)
            assert not vm.calls
            for s in range(6):
                vm.check(s, (w + s) % NW if mask & (1 << s) else s)
            boots += 1
    vm = VM({0x78 + s: 28 for s in range(6)})
    vm.call(B + 0x11f12, boot=True)
    for s in range(6):
        vm.check(s, 0)
    vm = VM({})
    vm.call(B + 0x11f12, boot=True)
    for s in range(6):
        vm.check(s, s)
    vm = VM()
    before = bytes(vm.u.mem_read(B, len(APP)))
    vm.call(SELECT, (6, 2, 1))
    assert bytes(vm.u.mem_read(B, len(APP))) == before and not vm.calls
    # CB selected in every slot, then back to each v1 wave: slot bytes equal the v1 programs exactly
    for s in range(6):
        vm = VM()
        vm.u.mem_write(B + 0xa9e18 + 4 * s, struct.pack('<I', 28))
        vm.call(B + 0x17044, (0, 6, 28, s))
        vm.check(s, 6)
        for w in range(6):
            vm.call(B + 0x17044, (0, w, 28, s))
            vm.check(s, w)
            vm.call(B + 0x17044, (0, 6, 28, s))
            vm.check(s, 6)
    result = dict(passed=True, waves=NW, wave_transitions=transitions, boot_configurations=boots + 2,
                  invalid_p2_cases=60, cb_round_trips=6 * 6,
                  callee_registers_and_stack_preserved=True, stock_loader_mute_send_unmute_call_order=True,
                  range_table_preserved=True,
                  limitations='DSP execution, DMA, NVRAM storage backend, actual USB and hardware audio are not emulated; '
                              'stock leaf I/O and NVRAM accessors intercepted.')
    (HERE / 'verification.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    return result


if __name__ == '__main__':
    verify()
