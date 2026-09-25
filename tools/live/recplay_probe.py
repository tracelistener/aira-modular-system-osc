"""Does any MIDI message already work the SCOOPER's REC/PLAY button? (user-approved probe, 2026-09-24)

Detector: SYSTEM OSC TRI -> MIXER (gain = source on/off) -> SCOOPER efx in 1/2 -> efx out 1/2 -> OUTPUT 1/2.
A batch of candidate messages is sent twice as 'presses' while the tone plays (REC/PLAY: 1st press records,
2nd press plays). Then the tone is muted and both SCOOPER buttons are reset; sound that keeps coming out is a
recorded loop. A positive batch is narrowed down with single presses: each REC/PLAY press toggles play/stop.
Safe set only: note on/off, CC 0-119, pitch bend, channel pressure, transport. No program change, no SysEx writes
beyond the usual patch/parameter blocks, no channel-mode CCs (120-127). 20 ms between messages.
Restores the patch that was on the unit when the probe started (clear -> wait -> rebuild).
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
OUTD.mkdir(parents=True, exist_ok=True)
aira_live.CAP = OUTD
OUT = lambda s, i=0: 10 + 2 * (s - 1) + i
IN = lambda s, i=0: 10 + 4 * (s - 1) + i
MIDI, SYS, MIX = 1, 2, 6
EFX_IN1, EFX_IN2, EFX_OUT1, EFX_OUT2 = 2, 3, 8, 9      # main-module jack indices (Customizer 'main' layout)
GAP = 0.02
LOG = []


def rms(x, skip=0.1, rate=48000):
    y = x[int(skip * rate):, 0]
    return float(np.sqrt(np.mean(y * y)))


class Probe:
    def __init__(self, a, port):
        self.a, self.port = a, port

    def send(self, m):
        self.port.send(m); time.sleep(GAP)

    def press(self, c):
        kind, ch, n = c
        if kind == 'note':
            self.send(mido.Message('note_on', channel=ch, note=n, velocity=127))
            self.send(mido.Message('note_off', channel=ch, note=n, velocity=0))
        elif kind == 'cc':
            self.send(mido.Message('control_change', channel=ch, control=n, value=127))
            self.send(mido.Message('control_change', channel=ch, control=n, value=0))
        elif kind == 'bend':
            self.send(mido.Message('pitchwheel', channel=ch, pitch=8191))
            self.send(mido.Message('pitchwheel', channel=ch, pitch=0))
        elif kind == 'pressure':
            self.send(mido.Message('aftertouch', channel=ch, value=127))
            self.send(mido.Message('aftertouch', channel=ch, value=0))
        elif kind == 'rt':
            self.send(mido.Message(n))

    def source(self, on):
        self.a.param(MIX, 1, 10 if on else 0)

    def buttons_off(self):
        self.a.write([0x10, 0, 0, 1], [0, 0])          # SCOOPER P1 (SYNC TRIG) and P2 (SCATTER) off

    def level(self, label, wait=0.8, secs=1.0):
        time.sleep(wait)
        _, x, _ = capture(label, secs)
        return rms(x)

    def batch(self, cands, label):
        self.source(True)
        self.a.note(60, True)                            # MIDINOTE on ch1 gives the TRI a pitch
        for c in cands:
            self.press(c)
        time.sleep(0.4)
        for c in cands:
            self.press(c)
        self.source(False); self.buttons_off()
        self.a.all_notes_off()
        return self.level(label)


def main():
    a = Aira()
    start = a.snapshot()
    (OUTD / 'start_snapshot.json').write_text(json.dumps(start) + '\n')
    rep = dict(batches=[], found=None)
    try:
        clear(a)
        a.slot(MIDI, [31, 3, 12, 0, 0]); a.slot(SYS, [28, 2, 2, 0, 100]); a.slot(MIX, [10, 10, 0, 0, 0])
        for o, i in ((OUT(MIDI), IN(SYS)), (OUT(SYS), IN(MIX, 0)), (OUT(MIX), EFX_IN1), (OUT(MIX), EFX_IN2),
                     (EFX_OUT1, 0), (EFX_OUT2, 1)):
            a.cable(o, i, 1)
        P = Probe(a, a.np)
        P.buttons_off()
        # ---- stage 0: is the SCOOPER passing the tone, and is it silent when muted?
        a.note(62, True); time.sleep(0.3); a.note(62, False)
        a.note(60, True); P.source(True)
        on = P.level('s0_source_on', 0.5)
        P.source(False); a.all_notes_off()
        off = P.level('s0_source_off', 0.8)
        rep['stage0'] = dict(pass_through_rms=on, muted_rms=off)
        print('stage0 pass-through rms %.5f  muted rms %.6f' % (on, off), flush=True)
        if on < 20 * max(off, 1e-5):
            main_block = a.read([0x10, 0, 0, 0], 11)
            rep['stage0']['main_params'] = main_block
            print('no pass-through; SCOOPER main params:', main_block, flush=True)
            return rep
        thr = max(20 * off, 3e-4)
        # ---- candidate list: transport first, then the ModWiggler lead (ch 9/10), then everything else
        cands = [('rt', 0, 'start'), ('rt', 0, 'continue'), ('rt', 0, 'stop')]
        order = [8, 9] + [c for c in range(16) if c not in (8, 9)]
        for ch in order:
            cands += [('note', ch, n) for n in range(128)] + [('cc', ch, n) for n in range(120)]
            cands += [('bend', ch, 0), ('pressure', ch, 0)]
        batches = [cands[:3]] + [cands[i:i + 64] for i in range(3, len(cands), 64)]
        t0 = time.time()
        for k, b in enumerate(batches):
            lvl = P.batch(b, 'batch_%03d' % k)
            ok = True
            try:
                a.read([0x10, 0x10, 0, 0], 5)
            except Exception:
                ok = False
            rep['batches'].append(dict(k=k, first=b[0], last=b[-1], rms=lvl, alive=ok))
            print('batch %3d  %-28s .. %-28s rms %.6f %s  (%.0fs)' % (k, b[0], b[-1], lvl, '' if ok else 'NO SYSEX REPLY',
                                                                  time.time() - t0), flush=True)
            if not ok:
                rep['aborted'] = 'unit stopped answering SysEx'
                return rep
            if lvl > thr:
                rep['found'] = narrow(P, b, thr, rep)
                return rep
        return rep
    finally:
        a.all_notes_off(); time.sleep(0.5)
        try:
            rep['restored'] = safe_load(a, start)
        except Exception as e:
            rep['restored'] = 'FAILED: %r' % e
        (OUTD / 'probe_report.json').write_text(json.dumps(rep, indent=1, default=str) + '\n')
        a.close()
        print('restored:', rep['restored'], flush=True)


def narrow(P, cands, thr, rep):
    """A loop is playing. Each REC/PLAY press toggles play/stop, so a subset that flips the state contains it."""
    playing = True
    steps = []
    while len(cands) > 1:
        half = cands[:len(cands) // 2]
        for c in half:
            P.press(c)
        now = P.level('narrow_%d' % len(steps)) > thr
        flipped = now != playing
        steps.append(dict(tested=[half[0], half[-1]], n=len(half), playing_after=now, flipped=flipped))
        print('  narrow: %d candidates -> flipped=%s' % (len(half), flipped), flush=True)
        playing = now
        cands = half if flipped else cands[len(cands) // 2:]
    c = cands[0]
    toggles = []
    for _ in range(3):
        P.press(c); now = P.level('confirm_%d' % len(toggles)) > thr
        toggles.append(now);
    # delete the loop the way the button does: hold for 2.5 s
    kind, ch, n = c
    if kind == 'note':
        P.send(mido.Message('note_on', channel=ch, note=n, velocity=127)); time.sleep(2.5)
        P.send(mido.Message('note_off', channel=ch, note=n, velocity=0))
    elif kind == 'cc':
        P.send(mido.Message('control_change', channel=ch, control=n, value=127)); time.sleep(2.5)
        P.send(mido.Message('control_change', channel=ch, control=n, value=0))
    after_hold = P.level('after_hold') > thr
    rep['narrow_steps'] = steps
    return dict(candidate=c, confirm_toggles=toggles, playing_after_hold=after_hold)


if __name__ == '__main__':
    r = main()
    print(json.dumps({k: v for k, v in r.items() if k != 'batches'}, indent=1, default=str))
