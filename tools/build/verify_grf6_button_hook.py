"""Offline Unicorn checks for the independent physical SCATTER hook.

Import ``verify_button(app)`` from the builder after assembling the candidate.
This module neither builds firmware nor opens MIDI/audio/hardware devices.
"""
import struct
import sys
from pathlib import Path

try:
    import unicorn
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(
        r'C:\Users\admin\Documents\Codex\2026-09-23\c-users-admin-documents-codex-2026'
    ) / 'work/deps'))
    import unicorn
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_THUMB, UC_HOOK_CODE
from unicorn.arm_const import (
    UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3,
    UC_ARM_REG_R4, UC_ARM_REG_R5, UC_ARM_REG_R6, UC_ARM_REG_R7,
    UC_ARM_REG_R8, UC_ARM_REG_R9, UC_ARM_REG_R10, UC_ARM_REG_R11,
    UC_ARM_REG_R12, UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_PC,
)

B = 0x60000000
BROKER = B + 0x25C
BROKER_HOOK = B + 0x88380
GETTER = B + 0x4328
SETTER = B + 0x3A84
BROADCAST = B + 0x81A
LED_REFRESH = B + 0xAA72
LED_HELPER = B + 0x88480
LED_WRITE = B + 0x44E14
BUTTON_LATCH = B + 0x88C10
STACK_BASE = 0x20000000
STACK_TOP = STACK_BASE + 0x1F00
RETURN = STACK_BASE + 0x100
PRESERVED = (
    UC_ARM_REG_R4, UC_ARM_REG_R5, UC_ARM_REG_R6,
    UC_ARM_REG_R7, UC_ARM_REG_R8, UC_ARM_REG_R9, UC_ARM_REG_R10,
    UC_ARM_REG_R11,
)


def _machine(app):
    uc = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
    size = max(0x200000, (len(app) + 0xFFF) & ~0xFFF)
    uc.mem_map(B, size)
    uc.mem_write(B, bytes(app))
    uc.mem_map(STACK_BASE, 0x2000)
    uc.mem_write(STACK_BASE, b'\xA5' * 0x2000)
    uc.mem_write(B + 0x9B3E0, struct.pack('<I', 0))
    uc.mem_write(BUTTON_LATCH, struct.pack('<I', 0))
    return uc


def _prepare(uc, r0=0, r1=0):
    saved = {}
    for n, reg in enumerate(PRESERVED):
        value = 0xC0301000 + n * 0x101
        uc.reg_write(reg, value)
        saved[reg] = value
    uc.reg_write(UC_ARM_REG_R0, r0)
    uc.reg_write(UC_ARM_REG_R1, r1)
    uc.reg_write(UC_ARM_REG_R2, 0xC0202020)
    uc.reg_write(UC_ARM_REG_R3, 0xC0303030)
    uc.reg_write(UC_ARM_REG_R12, 0xC1212121)
    uc.reg_write(UC_ARM_REG_SP, STACK_TOP)
    uc.reg_write(UC_ARM_REG_LR, RETURN | 1)
    return saved


def _assert_return(uc, saved, label):
    assert uc.reg_read(UC_ARM_REG_PC) == RETURN, (label, 'did not return')
    assert uc.reg_read(UC_ARM_REG_SP) == STACK_TOP, (label, 'SP not restored')
    for reg, value in saved.items():
        assert uc.reg_read(reg) == value, (label, 'saved register changed', reg)
    assert bytes(uc.mem_read(STACK_TOP, 32)) == b'\xA5' * 32, (
        label, 'caller stack overwritten')


def _stub_return(uc, result=0):
    # These are AAPCS caller-saved. Clobber them to expose a hook that relies
    # on a lucky native implementation rather than preserving its arguments.
    for n, reg in enumerate((UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2,
                             UC_ARM_REG_R3, UC_ARM_REG_R12)):
        uc.reg_write(reg, 0xD0000100 + n)
    uc.reg_write(UC_ARM_REG_R0, result)
    uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))


def verify_button(app):
    """Assert broker/LED semantics and return a compact verification report."""
    assert len(app) > 0x88490, 'expected expanded application bytes'
    broker_cases = 0
    for input_id in range(5):
        for state in (0, 1, 2):
            for initial in (0, 1):
                label = ('broker', input_id, state, initial)
                uc = _machine(app)
                saved = _prepare(uc, input_id, state)
                calls, events, visited = [], [], set()
                parameter = [initial]

                def broker_stub(cpu, address, size, user):
                    visited.add(address)
                    if address not in (GETTER, SETTER, LED_REFRESH, BROADCAST):
                        return
                    assert cpu.reg_read(UC_ARM_REG_SP) % 8 == 0, (
                        label, 'stack misaligned at native call', hex(address))
                    a0 = cpu.reg_read(UC_ARM_REG_R0)
                    a1 = cpu.reg_read(UC_ARM_REG_R1)
                    a2 = cpu.reg_read(UC_ARM_REG_R2)
                    if address == GETTER:
                        assert (a0, a1) == (4, 0x69), (label, 'getter args', a0, a1)
                        calls.append(('get', parameter[0]))
                        _stub_return(cpu, parameter[0])
                    elif address == SETTER:
                        assert (a0, a1) == (4, 0x69), (label, 'setter args', a0, a1)
                        assert a2 in (0, 1), (label, 'nonboolean setter value', a2)
                        calls.append(('set', a2))
                        parameter[0] = a2
                        _stub_return(cpu)
                    elif address == LED_REFRESH:
                        calls.append(('led',))
                        _stub_return(cpu)
                    else:
                        events.append(bytes(cpu.mem_read(a0, 2)))
                        calls.append(('broadcast',))
                        _stub_return(cpu)

                uc.hook_add(UC_HOOK_CODE, broker_stub)
                uc.emu_start(BROKER | 1, RETURN, count=600)
                _assert_return(uc, saved, label)
                assert BROKER_HOOK in visited, (label, 'new broker not reached')
                expected_events = [bytes((state + 1, input_id))] if state < 2 else []
                assert events == expected_events, (label, 'event mismatch', events)
                toggles = input_id == 2 and state == 1
                assert parameter[0] == (1 - initial if toggles else initial), label
                assert sum(c[0] == 'get' for c in calls) == int(toggles), (label, calls)
                assert sum(c[0] == 'set' for c in calls) == int(toggles), (label, calls)
                assert sum(c[0] == 'led' for c in calls) == int(toggles), (label, calls)
                broker_cases += 1

    repeat_cases = 0
    for initial in (0, 1):
        uc = _machine(app)
        parameter = [initial]
        calls, events = [], []

        def repeat_stub(cpu, address, size, user):
            if address not in (GETTER, SETTER, LED_REFRESH, BROADCAST):
                return
            assert cpu.reg_read(UC_ARM_REG_SP) % 8 == 0, ('repeat', 'SP alignment')
            a0 = cpu.reg_read(UC_ARM_REG_R0)
            a1 = cpu.reg_read(UC_ARM_REG_R1)
            if address == GETTER:
                assert (a0, a1) == (4, 0x69)
                calls.append(('get', parameter[0]))
                _stub_return(cpu, parameter[0])
            elif address == SETTER:
                assert (a0, a1) == (4, 0x69)
                value = cpu.reg_read(UC_ARM_REG_R2)
                assert value in (0, 1)
                calls.append(('set', value))
                parameter[0] = value
                _stub_return(cpu)
            elif address == LED_REFRESH:
                calls.append(('led',))
                _stub_return(cpu)
            else:
                events.append(bytes(cpu.mem_read(a0, 2)))
                _stub_return(cpu)

        uc.hook_add(UC_HOOK_CODE, repeat_stub)
        # Other input events and invalid states must not clear a held latch.
        sequence = ((2, 1), (2, 1), (0, 0), (2, 2), (2, 1),
                    (2, 0), (2, 0), (2, 1), (2, 1), (2, 0))
        expected_events, latch, toggles = [], 0, 0
        for input_id, state in sequence:
            label = ('repeat', initial, input_id, state, repeat_cases)
            before_sets = sum(c[0] == 'set' for c in calls)
            expected_toggle = input_id == 2 and state == 1 and latch == 0
            if input_id == 2 and state in (0, 1):
                latch = state
            if expected_toggle:
                toggles += 1
            if state < 2:
                expected_events.append(bytes((state + 1, input_id)))
            saved = _prepare(uc, input_id, state)
            uc.emu_start(BROKER | 1, RETURN, count=600)
            _assert_return(uc, saved, label)
            after_sets = sum(c[0] == 'set' for c in calls)
            assert after_sets - before_sets == int(expected_toggle), (label, calls)
            assert parameter[0] == initial ^ (toggles & 1), (label, parameter)
            actual_latch = struct.unpack('<I', bytes(uc.mem_read(BUTTON_LATCH, 4)))[0]
            assert actual_latch == latch, (label, 'button latch', actual_latch, latch)
            assert events == expected_events, (label, events)
            repeat_cases += 1
        assert toggles == 2
        assert sum(c[0] == 'get' for c in calls) == 2
        assert sum(c[0] == 'led' for c in calls) == 2

    led_cases = 0
    for flag3 in (0, 1):
        for flag4 in (0, 1, 0xFFFFFFFF):
            for parameter in (0, 1):
                label = ('led', flag3, flag4, parameter)
                uc = _machine(app)
                uc.mem_write(B + 0x8DB40, struct.pack('<II', flag3, flag4))
                saved = _prepare(uc, 0x12345678, 0x87654321)
                calls, getters, visited = [], [], set()

                def led_stub(cpu, address, size, user):
                    visited.add(address)
                    if address not in (GETTER, LED_WRITE):
                        return
                    sp = cpu.reg_read(UC_ARM_REG_SP)
                    assert sp % 8 == 0, (label, 'stack misaligned', hex(address))
                    args = tuple(cpu.reg_read(reg) for reg in (
                        UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3))
                    if address == GETTER:
                        assert args[:2] == (4, 0x69), (label, 'getter args', args)
                        getters.append(args[:2])
                        _stub_return(cpu, parameter)
                    else:
                        stack_arg = struct.unpack('<I', bytes(cpu.mem_read(sp, 4)))[0]
                        calls.append(args + (stack_arg,))
                        _stub_return(cpu)

                uc.hook_add(UC_HOOK_CODE, led_stub)
                uc.emu_start(LED_REFRESH | 1, RETURN, count=300)
                _assert_return(uc, saved, label)
                assert LED_HELPER in visited, (label, 'LED helper not reached')
                assert getters == [(4, 0x69)], (label, getters)
                assert calls == [
                    (B + 0x9A1FC, 4, int(bool(flag3)), 9, 0),
                    (B + 0x9A1FC, 5, parameter, 9, 0),
                ], (label, 'LED arguments mismatch', calls)
                led_cases += 1

    return {
        'broker_cases': broker_cases,
        'repeat_event_cases': repeat_cases,
        'led_cases': led_cases,
        'passed': True,
        'checks': [
            'native events preserved for IDs0..4 and states0,1,2',
            'parameter69 toggles once only on physical SCATTER press',
            'replayed press events do not toggle again until release',
            'native-call arguments, stack alignment, R4-R11 and SP preservation',
            'LED4 follows flag3; LED5 follows parameter69 independently of flag4',
        ],
    }
