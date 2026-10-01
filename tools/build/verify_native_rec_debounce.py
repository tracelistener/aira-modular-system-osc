"""Execute native raw REC input filtering through the original event broker.

Only raw hardware samples and the terminal event sink are substituted. The
native filter, runtime byte ring, ring decoder and broker execute normally.
This script never accesses hardware or modifies a firmware image.
"""
import json
import struct
import sys
from pathlib import Path

B = 0x60000000
POLL = 0x010086B4
GATHER = 0x01008664
FILTER = 0x010086FC
BROKER = 0x6000025C
DRAIN = 0x6000027A
SINK = 0x6000081A
STATE = 0x200010E0
STACK = 0x20004000
RETURN = 0x20000300
NOTIFY = 0x20000310


def verify_debounce(app):
    deps = Path(r'C:\Users\admin\Documents\Codex\2026-09-23\c-users-admin-documents-codex-2026\work\deps')
    if str(deps) not in sys.path:
        sys.path.insert(0, str(deps))
    from unicorn import Uc, UC_ARCH_ARM, UC_MODE_THUMB, UC_HOOK_CODE
    from unicorn.arm_const import (
        UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_LR,
        UC_ARM_REG_SP, UC_ARM_REG_PC,
    )

    app = bytes(app)
    assert len(app) >= 0x9AFD8
    assert struct.unpack_from('<3I', app, 0x9AF9C) == (0, 0, 7)
    assert app[0x4B6BE] == 0, 'Expected raw code0 to map to REC event id0'
    results = []

    def one(name, samples, press_count=0, expected_broker=None):
        u = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
        u.mem_map(B, 0xA0000)
        u.mem_write(B, app)
        u.mem_map(0x01000000, 0x20000)
        u.mem_write(0x01000300, app[0x91D90:0x91D90+0x9190])
        u.mem_map(0x20000000, 0x10000)
        # Native configuration copied by the firmware startup initializer.
        u.mem_write(0x20000000, app[0x9AF9C:0x9AFD8])
        u.mem_write(0x20000004, struct.pack('<I', press_count))
        # Runtime callback and byte-ring initialization, matching002AC/02810.
        u.mem_write(0x20000084, struct.pack('<I', 0x01004C61))
        u.mem_write(0x2000003C, struct.pack('<4I', 1, 0x2000009C,
                                         0x2000009C, NOTIFY | 1))
        broker, published, state_trace = [], [], []
        tick = 0
        raw = 1
        filter_calls = 0

        def code(uc, pc, size, user):
            nonlocal filter_calls
            if pc == GATHER:
                # Raw0 REC active-low; all four other inputs stay inactive.
                uc.mem_write(uc.reg_read(UC_ARM_REG_R0),
                             struct.pack('<5I', raw, 1, 1, 0, 0))
                uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))
            elif pc == FILTER:
                filter_calls += 1
            elif pc == NOTIFY:
                uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))
            elif pc == BROKER:
                broker.append((tick, uc.reg_read(UC_ARM_REG_R0),
                               uc.reg_read(UC_ARM_REG_R1)))
            elif pc == SINK:
                packet = bytes(uc.mem_read(uc.reg_read(UC_ARM_REG_R0), 2))
                published.append((tick, packet[0], packet[1]))
                uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))

        u.hook_add(UC_HOOK_CODE, code)
        counter = countdown = 0
        reference_events = []
        for tick, raw in enumerate(samples):
            # Literal native algorithm, independently checked against RAM after
            # every poll. A currently inactive input does not clear a pending
            # press counter while countdown is zero.
            event = None
            if raw == 0:
                if counter < press_count:
                    counter += 1
                else:
                    if countdown == 0:
                        event = 1
                    countdown = 7
            elif countdown:
                countdown -= 1
                if countdown == 0:
                    counter = 0
                    event = 0
            if event is not None:
                reference_events.append((tick, 0, event))
            for entry in (POLL, DRAIN):
                u.reg_write(UC_ARM_REG_SP, STACK)
                u.reg_write(UC_ARM_REG_LR, RETURN | 1)
                u.emu_start(entry | 1, RETURN, count=2000)
                assert u.reg_read(UC_ARM_REG_PC) == RETURN, (name, tick, 'did not return')
                assert u.reg_read(UC_ARM_REG_SP) == STACK, (name, tick, 'stack imbalance')
            actual = struct.unpack('<2I', u.mem_read(STATE, 8))
            assert actual == (counter, countdown), (name, tick, actual, (counter, countdown))
            assert broker == reference_events, (name, tick, broker, reference_events)
            state_trace.append({'poll': tick, 'raw0': raw,
                                'press_counter': counter, 'release_countdown': countdown})
        assert filter_calls == 5*len(samples), (name, 'native five-input poll missing')
        assert published == [(t, 2 if e else 1, i) for t, i, e in broker], (
            name, 'broker packet mapping', published, broker)
        if expected_broker is not None:
            assert broker == expected_broker, (name, broker, expected_broker)
        result = {'name': name, 'configuration': [0, press_count, 7],
                  'poll_count': len(samples), 'broker_events': broker,
                  'published_events': published, 'state_trace': state_trace}
        results.append(result)

    one('single_active_sample_is_a_press', [1]*10+[0]+[1]*8,
        expected_broker=[(10, 0, 1), (17, 0, 0)])
    one('six_inactive_samples_do_not_release_held_gate',
        [0]*2+[1]*6+[0]+[1]*7,
        expected_broker=[(0, 0, 1), (15, 0, 0)])
    one('seven_inactive_samples_release_then_next_active_represses',
        [0]+[1]*7+[0], expected_broker=[(0, 0, 1), (7, 0, 0), (8, 0, 1)])
    one('short_repeated_active_samples_extend_one_press',
        [0, 1]*5+[1]*7, expected_broker=[(0, 0, 1), (15, 0, 0)])
    one('twenty_poll_gate_is_accepted_on_first_poll',
        [1]*3+[0]*20+[1]*7, expected_broker=[(3, 0, 1), (29, 0, 0)])
    one('inactive_scat_release_glitch_yields_false_rec_press',
        [1]*4+[0]+[1]*7, expected_broker=[(4, 0, 1), (11, 0, 0)])
    one('hypothetical_press_count7_accumulates_separated_glitches',
        [0, 1]*7+[0]+[1]*7, press_count=7,
        expected_broker=[(14, 0, 1), (21, 0, 0)])
    one('hypothetical_press_count7_needs_eighth_active_sample',
        [0]*8+[1]*7, press_count=7,
        expected_broker=[(7, 0, 1), (14, 0, 0)])
    return {
        'scenario_count': len(results),
        'native_poll_count': sum(r['poll_count'] for r in results),
        'native_filter_call_count': 5*sum(r['poll_count'] for r in results),
        'native_configuration': [0, 0, 7],
        'executed_path': ['0x010086b4 poll', '0x010086fc filter',
                          '0x01004c60 callback', '0x01004c7c byte ring',
                          '0x6000027a drain', '0x6000025c event broker'],
        'substitutions': ['Raw hardware gatherer supplies specified five values',
                          'Queue notify callback returns immediately',
                          'Terminal0x6000081a event sink records two-byte packets'],
        'conclusion': 'Press accepted on first active sample; release needs seven consecutive inactive polls',
        'press_count_warning': 'Nonzero press count accumulates active samples across inactive gaps before a press',
        'timing_scope': 'Poll counts only; no milliseconds assumed',
        'guard_removal_result': 'Native release filtering cannot reject a one-poll false active glitch while idle',
        'scenarios': results,
    }


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('Usage: verify_native_rec_debounce.py unpacked-application.bin')
    print(json.dumps(verify_debounce(Path(sys.argv[1]).read_bytes()), indent=2))
