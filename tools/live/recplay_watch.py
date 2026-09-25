"""Watch the SCOOPER while the user presses the physical REC/PLAY button (user's idea, 2026-09-24).

Logs, with timestamps from the start of the audio capture:
  * every MIDI message the unit sends on both of its MIDI inputs to the PC,
  * the readable main-effect and slot parameter blocks (polled every second),
  * the audio: SYSTEM OSC TRI -> MIXER -> SCOOPER in -> SCOOPER out -> OUTPUT, with the live note alternating
    C4/G4 every 0.5 s, so a playing loop shows up as pitch that no longer follows the live notes.
Restores the user's patch afterwards (clear -> wait -> rebuild).
"""
import json, sys, time
from pathlib import Path
import numpy as np
import mido
sys.path.insert(0, 'C:/Users/admin/Documents/Codex/2026-09-22/files-mentioned-by-the-user-handoff/work/live')
sys.path.insert(0, str(Path(__file__).resolve().parent))
import aira_live
from aira_live import Aira, capture
from v32_check_and_restore import load as safe_load, clear

ROOT = Path(__file__).resolve().parents[2]
OUTD = ROOT / 'outputs/recplay-probe'
aira_live.CAP = OUTD
OUT = lambda s, i=0: 10 + 2 * (s - 1) + i
IN = lambda s, i=0: 10 + 4 * (s - 1) + i
MIDI, SYS, MIX = 1, 2, 6
SECS = float(sys.argv[1]) if len(sys.argv) > 1 else 150.0
NOTES = (60, 67)


def main():
    a = Aira()
    start = a.snapshot()
    (OUTD / 'watch_start_snapshot.json').write_text(json.dumps(start) + '\n')
    other = mido.open_input('2- AIRA MODULAR 0')
    ev = dict(midi=[], params=[], notes=[])
    t0 = [0.0]
    orig_rx = a._rx

    def rx(pred, timeout=2.0):                          # log anything unsolicited that arrives on the CTRL port
        t = time.monotonic() + timeout
        while time.monotonic() < t:
            m = a.ip.poll()
            if m is not None:
                if m.type == 'sysex' and pred(list(m.data)):
                    return list(m.data)
                ev['midi'].append(dict(t=round(time.monotonic() - t0[0], 3), port='CTRL', msg=str(m)))
            time.sleep(0.002)
        raise TimeoutError('no sysex reply')
    a._rx = rx
    try:
        clear(a)
        a.slot(MIDI, [31, 3, 12, 0, 0]); a.slot(SYS, [28, 2, 2, 0, 100]); a.slot(MIX, [10, 10, 0, 0, 0])
        for o, i in ((OUT(MIDI), IN(SYS)), (OUT(SYS), IN(MIX, 0)), (OUT(MIX), 2), (OUT(MIX), 3), (8, 0), (9, 1)):
            a.cable(o, i, 1)
        a.note(62, True); time.sleep(0.3); a.note(62, False)
        last = {'main': a.read([0x10, 0, 0, 0], 11), 'slots': a.read([0x10, 0x10, 0, 0], 30)}
        ev['params'].append(dict(t=0.0, **last))

        def watch():
            t0[0] = time.monotonic()
            k, next_note, next_poll = 0, 0.0, 1.0
            while time.monotonic() - t0[0] < SECS - 0.3:
                now = time.monotonic() - t0[0]
                if now >= next_note:
                    n = NOTES[k % 2]; a.note(n, True); a.note(NOTES[(k + 1) % 2], False)
                    ev['notes'].append((round(now, 3), n)); k += 1; next_note += 0.5
                for m in other.iter_pending():
                    ev['midi'].append(dict(t=round(now, 3), port='MAIN', msg=str(m)))
                if now >= next_poll:
                    cur = {'main': a.read([0x10, 0, 0, 0], 11), 'slots': a.read([0x10, 0x10, 0, 0], 30)}
                    if cur != last:
                        ev['params'].append(dict(t=round(now, 3), **cur)); last.update(cur)
                    next_poll += 1.0
                time.sleep(0.005)
        print('WATCHING for %.0f s' % SECS, flush=True)
        _, x, rate = capture('press_watch', SECS, during=watch)
        a.all_notes_off()
        ev['analysis'] = analyse(x[:, 0], rate, ev['notes'])
    finally:
        a._rx = orig_rx
        a.all_notes_off(); time.sleep(0.5)
        try:
            ev['restored'] = safe_load(a, start)
        except Exception as e:
            ev['restored'] = 'FAILED: %r' % e
        other.close(); a.close()
        (OUTD / 'press_watch.json').write_text(json.dumps(ev, indent=1) + '\n')
    return ev


def analyse(y, rate, notes, hop=0.05):
    """Per 50 ms: output level, which of the two note pitches dominates, and whether it matches the live note."""
    f = {n: 440 * 2 ** ((n - 69) / 12) for n in NOTES}
    L = int(hop * rate); seg = []
    def live(t):                                        # live note at time t (30 ms allowance for latency)
        return next((n for (tn, n) in reversed(notes) if tn <= t - 0.03), None)
    tt = np.arange(L) / rate
    for i in range(len(y) // L):
        s = y[i * L:(i + 1) * L]; r = float(np.sqrt(np.mean(s * s)))
        mags = {n: abs(np.dot(s * np.hanning(L), np.exp(-2j * np.pi * fr * tt))) for n, fr in f.items()}
        top = max(mags, key=mags.get) if r > 3e-4 else None
        seg.append((round(i * hop, 2), round(r, 5), top, live(i * hop)))
    # compress into runs of state: silent / follows live / loop (pitch not following the live note)
    runs = []
    for t, r, top, lv in seg:
        st = 'silent' if top is None else ('follows' if top == lv else 'other')
        if runs and runs[-1]['state'] == st:
            runs[-1]['end'] = t + hop
        else:
            runs.append(dict(state=st, start=t, end=t + hop))
    merged = []
    for r in runs:                                     # 'other' blips shorter than 0.15 s are note-change edges
        if merged and (r['end'] - r['start'] < 0.15) and r['state'] == 'other':
            merged[-1]['end'] = r['end']; continue
        if merged and merged[-1]['state'] == r['state']:
            merged[-1]['end'] = r['end']
        else:
            merged.append(dict(r))
    return [dict(state=m['state'], start=round(m['start'], 2), end=round(m['end'], 2)) for m in merged]


if __name__ == '__main__':
    e = main()
    print('MIDI from unit:', e['midi'][:40])
    print('param changes:', [(p['t'], p['main']) for p in e['params']][:20])
    print('audio states:', e.get('analysis'))
    print('restored:', e['restored'])
