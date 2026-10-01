"""Offline tests for the independent GRF6 decoder; never accesses hardware.

The tests enter the real native reader at 0x6001112A, including its embedded
runtime scalar accessor. The caller provides an unpacked application image.
"""
import collections
import json
import struct
import sys
from pathlib import Path

B = 0x60000000
GATE_FN = 0x60088280
STATE = 0x60088C00
READER = 0x6001112A
CLOCK = 0x01015188
GPIO = 0x4002D034
SCALAR = 0x40101068
RETURN = 0x20000100
STACK = 0x20000F00
CONTEXT = 0x20000000
GUARD = 20
MASK32 = 0xFFFFFFFF
THRESHOLDS = {1: 0x3E800000, 0: 0x3F95C28F}  # float32 0.25 / 1.17


def _bits(value):
    return struct.unpack('<I', struct.pack('<f', value))[0]


def _float(bits):
    return struct.unpack('<f', struct.pack('<I', bits))[0]


def verify_gate(app):
    """Return a verification summary, or raise AssertionError on any mismatch."""
    deps = Path(r'C:\Users\admin\Documents\Codex\2026-09-23\c-users-admin-documents-codex-2026\work\deps')
    if str(deps) not in sys.path:
        sys.path.insert(0, str(deps))
    from unicorn import Uc, UC_ARCH_ARM, UC_MODE_THUMB, UC_HOOK_MEM_WRITE
    from unicorn.arm_const import (
        UC_ARM_REG_R0, UC_ARM_REG_R4, UC_ARM_REG_R5, UC_ARM_REG_R6,
        UC_ARM_REG_R7, UC_ARM_REG_R8, UC_ARM_REG_R9, UC_ARM_REG_R10,
        UC_ARM_REG_R11, UC_ARM_REG_LR, UC_ARM_REG_SP, UC_ARM_REG_PC,
    )

    app = bytes(app)
    assert 0x9B038 <= len(app) <= 0xA0000, 'Expected unpacked application image'
    counts = collections.Counter()
    sequences = []
    preserved = (UC_ARM_REG_R4, UC_ARM_REG_R5, UC_ARM_REG_R6,
                 UC_ARM_REG_R7, UC_ARM_REG_R8, UC_ARM_REG_R9,
                 UC_ARM_REG_R10, UC_ARM_REG_R11)
    canaries = {reg: 0xA1B20000 + 0x101 * n for n, reg in enumerate(preserved, 1)}

    class Rig:
        def __init__(self, bank, pin=MASK32, change_tick=0, previous_gate=0):
            self.bank = bank
            self.model = [pin, change_tick & MASK32, previous_gate]
            self.u = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
            self.u.mem_map(B, 0xA0000)
            self.u.mem_write(B, app)
            self.u.mem_map(0x01000000, 0x20000)
            self.u.mem_write(0x01000300, app[0x91D90:0x91D90 + 0x9190])
            self.u.mem_map(0x40101000, 0x1000)
            self.u.mem_map(0x4002D000, 0x1000)
            self.u.mem_map(0x20000000, 0x10000)
            self.u.mem_write(CONTEXT, struct.pack('<I', bank))
            self.u.mem_write(STATE, struct.pack('<3I', *self.model))
            self.writes = []
            self.u.hook_add(UC_HOOK_MEM_WRITE, self.write_hook)

        def write_hook(self, uc, access, address, size, value, user):
            self.writes.append((address, size))

        def run(self, category, name, now, pin, value=None, raw_bits=None,
                expected=None):
            assert pin in (0, 1)
            now &= MASK32
            raw = _bits(value) if raw_bits is None else raw_bits
            scalar = _float(raw)
            old_pin, changed_at, previous = self.model
            if pin != old_pin:
                old_pin, changed_at = pin, now
            if (now - changed_at) & MASK32 < GUARD:
                wanted = previous
            else:
                wanted = int(scalar >= _float(THRESHOLDS[pin]))
            if expected is not None:
                assert wanted == expected, (name, 'reference scenario error', wanted, expected)
            self.model = [old_pin, changed_at, wanted]
            # The inactive bank deliberately holds the opposite stable state.
            opposite = 0.0 if scalar >= _float(THRESHOLDS[pin]) else 2.0
            self.u.mem_write(SCALAR + self.bank * 0x400, struct.pack('<I', raw))
            self.u.mem_write(SCALAR + (1 - self.bank) * 0x400, struct.pack('<f', opposite))
            self.u.mem_write(CLOCK, struct.pack('<I', now))
            port = 0x40000FFF | (1 << 12) | (1 << 13) | (pin << 15)
            self.u.mem_write(GPIO, struct.pack('<I', port))
            self.u.reg_write(UC_ARM_REG_R0, CONTEXT)
            self.u.reg_write(UC_ARM_REG_SP, STACK)
            self.u.reg_write(UC_ARM_REG_LR, RETURN | 1)
            for reg, canary in canaries.items():
                self.u.reg_write(reg, canary)
            self.writes.clear()
            self.u.emu_start(READER | 1, RETURN, count=500)
            got = self.u.reg_read(UC_ARM_REG_R0)
            tag = (name, 'bank', self.bank, 'tick', now, 'GPIO15', pin,
                   'scalar', scalar, 'raw', hex(raw))
            assert self.u.reg_read(UC_ARM_REG_PC) == RETURN, (tag, 'did not return')
            assert got == wanted, (tag, 'result', got, 'expected', wanted)
            actual_state = list(struct.unpack('<3I', self.u.mem_read(STATE, 12)))
            assert actual_state == self.model, (tag, 'state', actual_state, self.model)
            assert self.u.reg_read(UC_ARM_REG_SP) == STACK, (tag, 'stack imbalance')
            for reg, canary in canaries.items():
                assert self.u.reg_read(reg) == canary, (tag, 'callee-saved register changed', reg)
            for address, size in self.writes:
                on_stack = STACK - 0x200 <= address and address + size <= STACK
                in_state = STATE <= address and address + size <= STATE + 12
                assert on_stack or in_state, (tag, 'unexpected memory write', hex(address), size)
            counts[category] += 1
            return got

    # Independent stable truth table, including adjacent representable values at
    # each threshold, both GPIO positions, and both scalar banks.
    values = [-100.0, -1.0, -0.1, -0.0, 0.0, 0.0001, 0.249, 0.5019,
              0.9947, 1.125, 1.3558, 2.0]
    for bank in (0, 1):
        for pin in (0, 1):
            for value in values:
                rig = Rig(bank, pin=pin)
                rig.run('stable_levels', f'stable-{pin}-{value}', 100, pin, value)
            for delta in (-1, 0, 1):
                rig = Rig(bank, pin=pin)
                rig.run('threshold_boundaries', f'threshold-{pin}-{delta}', 100,
                        pin, raw_bits=THRESHOLDS[pin] + delta,
                        expected=int(delta >= 0))

    scenarios = [
        ('startup_released_high', (MASK32, 0, 0), [
            (100, 1, 0.5019, 0), (119, 1, 0.5019, 0), (120, 1, 0.5019, 1),
            (500, 1, 0.5019, 1), (3500, 1, 0.5019, 1), (3501, 1, 0.0001, 0)]),
        ('startup_button_held', (MASK32, 0, 0), [
            (100, 0, 0.9947, 0), (119, 0, 1.3558, 0), (120, 0, 1.3558, 1),
            (121, 0, 0.9947, 0)]),
        ('button_press_gate_low', (1, 0, 0), [
            (100, 1, 0.0001, 0), (101, 0, 0.0001, 0), (110, 0, 1.3558, 0),
            (120, 0, 0.9947, 0), (121, 0, 0.9947, 0), (122, 0, 1.3558, 1),
            (123, 0, 0.9947, 0)]),
        ('button_press_gate_high', (1, 0, 1), [
            (100, 1, 0.5019, 1), (101, 0, 0.5019, 1), (110, 0, 0.9947, 1),
            (120, 0, 1.3558, 1), (121, 0, 1.3558, 1), (3121, 0, 1.3558, 1),
            (3122, 0, 0.9947, 0)]),
        ('button_release_gate_low', (0, 0, 0), [
            (100, 0, 0.9947, 0), (101, 1, 0.9947, 0), (110, 1, 0.5019, 0),
            (120, 1, 0.3, 0), (121, 1, 0.0001, 0)]),
        ('button_release_gate_high', (0, 0, 1), [
            (100, 0, 1.3558, 1), (101, 1, 1.3558, 1), (110, 1, 0.0001, 1),
            (120, 1, 0.1, 1), (121, 1, 0.5019, 1), (122, 1, 0.0001, 0)]),
        ('bounce_restarts_guard', (1, 0, 0), [
            (100, 0, 0.9947, 0), (109, 1, 0.9947, 0), (115, 0, 0.9947, 0),
            (120, 0, 1.3558, 0), (128, 0, 1.3558, 0), (134, 0, 1.3558, 0),
            (135, 0, 1.3558, 1)]),
        ('counter_rollover', (1, 0xFFFFFFC0, 0), [
            (0xFFFFFFF0, 1, 0.0001, 0), (0xFFFFFFF8, 0, 0.9947, 0),
            (0x00000005, 0, 1.3558, 0), (0x0000000B, 0, 1.3558, 0),
            (0x0000000C, 0, 1.3558, 1), (0x0000000D, 0, 0.9947, 0)]),
        ('pulse_inside_guard_is_ignored', (1, 0, 0), [
            (100, 0, 0.9947, 0), (105, 0, 1.3558, 0), (115, 0, 0.9947, 0),
            (120, 0, 0.9947, 0)]),
        ('persistent_gate_change_during_guard', (0, 0, 1), [
            (100, 1, 1.3558, 1), (105, 1, 0.0001, 1),
            (119, 1, 0.0001, 1), (120, 1, 0.0001, 0)]),
    ]
    for bank in (0, 1):
        for name, initial, steps in scenarios:
            rig = Rig(bank, *initial)
            for n, (tick, pin, value, expected) in enumerate(steps):
                rig.run('transition_sequences', f'{name}-step{n}', tick,
                        pin, value, expected=expected)
            sequences.append({'name': name, 'bank': bank, 'steps': len(steps)})

    return {
        'case_count': sum(counts.values()),
        'categories': dict(counts),
        'threshold_float32': {str(pin): _float(bits) for pin, bits in THRESHOLDS.items()},
        'guard_ticks': GUARD,
        'reader_entry': hex(READER),
        'decoder_entry': hex(GATE_FN),
        'banks_tested': [0, 1],
        'sequences': sequences,
        'abi_checks': 'R4-R11, SP and return address preserved on every call',
        'memory_checks': 'Writes restricted to local stack and 12-byte decoder state',
        'limitation_verified': 'A gate pulse wholly within the 20-tick button guard is ignored',
    }


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('Usage: verify_grf6_independent.py unpacked-application.bin')
    print(json.dumps(verify_gate(Path(sys.argv[1]).read_bytes()), indent=2))
