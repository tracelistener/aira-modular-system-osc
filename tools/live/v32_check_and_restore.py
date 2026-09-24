"""After the power cycle: (optional) FINE IN parity check vs the stock SQR, then restore the user's patch safely.

Safe restore = clear every cable -> empty every slot -> wait 1.5 s (module removal is delayed on the SCOOPER) ->
add modules one by one -> cables -> main block -> read back. Never overwrite a slot in place (that stacked old + new
programs past the ~300-record DSP budget on 2026-09-24 and hung the unit).
Usage: python v32_check_and_restore.py [--restore-only]
"""
import json, math, sys, time
from pathlib import Path
import numpy as np
sys.path.insert(0, 'C:/Users/admin/Documents/Codex/2026-09-22/files-mentioned-by-the-user-handoff/work/live')
import aira_live
from aira_live import Aira, capture

ROOT = Path(__file__).resolve().parents[2]
USER = ROOT / 'outputs/wave-selector-v31-inputs/hw-test/pre_snapshot_pass2.json'   # the user's patch (both passes identical)
OUTD = ROOT / 'outputs/wave-selector-v32-inputs/hw-test'
OUTD.mkdir(parents=True, exist_ok=True)
aira_live.CAP = OUTD
OUT = lambda s, i=0: 10 + 2 * (s - 1) + i
IN = lambda s, i=0: 10 + 4 * (s - 1) + i
et = lambda n: 440.0 * 2 ** ((n - 69) / 12)


def line(x, rate, f_guess, span):
    y = x[int(0.15 * rate):]; y = (y - y.mean()) * np.hanning(len(y)); t = np.arange(len(y)) / rate
    mag = lambda f: abs(np.dot(y, np.exp(-2j * np.pi * f * t)))
    fs = np.linspace(f_guess * (1 - span), f_guess * (1 + span), 121); k = int(np.argmax([mag(f) for f in fs]))
    a_, b_ = fs[max(k - 1, 0)], fs[min(k + 1, 120)]; g = (math.sqrt(5) - 1) / 2
    for _ in range(40):
        c_, d_ = b_ - g * (b_ - a_), a_ + g * (b_ - a_)
        if mag(c_) > mag(d_):
            b_ = d_
        else:
            a_ = c_
    return (a_ + b_) / 2


def clear(a):
    a.all_notes_off(); a.blank(); time.sleep(1.5)


def load(a, snap):
    clear(a)
    slots = snap[1]['data']
    for s in range(6):
        v = slots[s * 5:s * 5 + 5]
        if v != [0] * 5:
            a.write([0x10, 0x10, 0, s * 5], v, settle=1.0)
    for b in snap[2:]:
        o = b['address'][2]
        for i, v in enumerate(b['data']):
            if v:
                a.write([0x10, 0x20, o, i], [v], settle=0.1)
    a.write([0x10, 0, 0, 1], snap[0]['data'][1:])
    return all(x['data'] == y['data'] for x, y in zip(a.snapshot(), snap))


def fine_check(a):
    MIDI, SYS, SQR, MIX = 1, 2, 3, 6
    clear(a)
    for s, v in ((MIDI, [31, 3, 12, 0, 0]), (SYS, [28, 2, 2, 0, 100]), (SQR, [30, 1, 50, 0, 50]), (MIX, [10, 10, 0, 0, 0])):
        a.slot(s, v)
    for o, i in ((OUT(MIDI), IN(SYS)), (OUT(MIDI), IN(SQR)), (OUT(MIDI), IN(SYS, 1)), (OUT(MIDI), IN(SQR, 1)),
                 (OUT(SYS), IN(MIX, 0)), (OUT(SQR), IN(MIX, 1)), (OUT(MIX), 0), (OUT(MIX), 1)):
        a.cable(o, i, 1)
    a.note(62, True); time.sleep(0.4); a.note(62, False)
    res = {}
    for n in (60, 72):
        for k, name in ((0, 'sys'), (1, 'sqr')):
            a.param(MIX, 1, 10 if k == 0 else 0); a.param(MIX, 2, 10 if k == 1 else 0)
            a.note(n, True); time.sleep(0.3)
            try:
                _, x, rate = capture('v32_fine_%s_n%d' % (name, n), 1.6)
            finally:
                a.note(n, False)
            base = et(n) * (2 ** (-0.38 / 1200) if name == 'sqr' else 1)
            f = line(x[:, 0], rate, et(n) * 2 ** (n / 1200), 0.02)
            res['%s_n%d_shift_cents' % (name, n)] = round(1200 * math.log2(f / base), 3)
    res['expected_cents'] = {'n60': 60.0, 'n72': 72.0}
    print(json.dumps(res, indent=1))
    return res


def slots_of(snap):
    d = snap[1]['data']
    return [d[s * 5:s * 5 + 5] for s in range(6)]


def leftover_test_state(now, user):
    """True if the unit holds something my tests could have left: empty, a v3.1 preset, or a half-done restore."""
    cur = slots_of(now)
    if all(v == [0] * 5 for v in cur):
        return True
    pre = {p.name: [list(p.read_bytes()[56 + s * 8:61 + s * 8]) for s in range(6)]
           for p in (ROOT / 'outputs/wave-selector-v31-inputs/presets').glob('VOICE_*.bin')}
    if cur in pre.values():
        return True
    return all(c == u or c == t for c, u, t in zip(cur, slots_of(user), pre['VOICE_SYSTEM_TRI.bin']))


if __name__ == '__main__':
    user = json.loads(USER.read_text())
    a = Aira()
    now = a.snapshot()
    (OUTD / 'post_flash_snapshot.json').write_text(json.dumps(now) + '\n')
    if now == user:
        target, why = user, 'unit came back with your pre-test patch'
    elif leftover_test_state(now, user):
        target, why = user, 'unit came back with a leftover test state; restoring your pre-test patch'
    else:
        target, why = now, 'unit holds a different patch than before the tests (you loaded it?); keeping that one'
    print('current slots:', slots_of(now)); print('restore target:', why, flush=True)
    rep = {'restore_target': why}
    try:
        if '--restore-only' not in sys.argv:
            rep['fine'] = fine_check(a)
    finally:
        ok = load(a, target)
        rep['restored'] = ok
        (OUTD / 'v32_check.json').write_text(json.dumps(rep, indent=1) + '\n')
        a.close()
        print('RESTORED user patch' if ok else 'RESTORE INCOMPLETE')
