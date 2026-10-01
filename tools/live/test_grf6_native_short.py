"""Short-pulse, distinct-pattern verification of direct physical GRF6 REC/PLAY."""
import json
import time
import mido
import numpy as np
import test_grf6_native_direct as base

LABEL = 'grf6_native_short'

def main():
    a = base.Aira()
    start = a.snapshot()
    (base.OUTD / f'{LABEL}_starting_patch.json').write_text(json.dumps(start, indent=2)+'\n')
    ports = [n for n in mido.get_output_names() if 'KeyStep 32' in n]
    assert len(ports) == 1, ports
    ks = mido.open_output(ports[0])
    report = {'gate_events': [], 'pulse_seconds': 0.12}
    def gate(on):
        for ch in range(16):
            ks.send(mido.Message('note_on' if on else 'note_off', channel=ch,
                                 note=60, velocity=100 if on else 0))
    def pitch(n):
        a.note(n, True)
        time.sleep(0.03)
        a.note(n, False)
    try:
        base.clear(a)
        a.slot(1, [31, 3, 12, 0, 0])
        a.slot(2, [28, 2, 2, 0, 100])
        a.slot(6, [10, 0, 0, 0, 0])
        for out, inp in ((base.OUT(1), base.IN(2)), (base.OUT(2), base.IN(6)),
                         (base.OUT(6), 2), (base.OUT(6), 3), (8, 0), (9, 1)):
            a.cable(out, inp, 1)
        a.write([0x10, 0, 0, 1], [0, 0])
        a.write([0x10, 0, 0, 5], [50, 50])
        route = a.read([0x10, 0x20, 7, 0], 34)
        report['grf6_route_before'] = route
        assert route == [0]*34, route
        gate(False)
        time.sleep(0.3)
        gate(True)
        time.sleep(3.5)
        gate(False)
        time.sleep(0.6)
        pitch(62)
        pitch(60)
        a.param(6, 1, 10)
        def during():
            t0 = time.monotonic()
            def at(t):
                while time.monotonic()-t0 < t:
                    time.sleep(0.005)
            def event(t, on):
                at(t)
                gate(on)
                report['gate_events'].append({'t': round(time.monotonic()-t0, 3), 'on': on})
            print('Short pulses: record at5s, octave change at6.5s, play at8s.', flush=True)
            event(5, True)
            event(5.12, False)
            at(6.5)
            pitch(72)
            report['pitch_change_t'] = round(time.monotonic()-t0, 3)
            event(8, True)
            event(8.12, False)
            at(8.2)
            a.param(6, 1, 0)
            report['mute_t'] = round(time.monotonic()-t0, 3)
            print('Live source muted; measuring recorded two-note pattern.', flush=True)
            event(19, True)
            event(22.5, False)
            event(24, True)
            event(24.12, False)
            event(26, True)
            event(26.12, False)
            # Clear the silent recording so the user's device ends with no test loop.
            event(28, True)
            event(31.5, False)
        _, audio, rate = base.capture(LABEL, 33.0, during=during)
        y = audio[:,0]
        def rms(t1, t2):
            z = y[int(t1*rate):int(t2*rate)]
            return round(float(np.sqrt(np.mean(z*z))),6)
        report['live_rms'] = rms(2,4)
        report['loop_after_mute_rms'] = rms(9,18)
        report['after_hold_rms'] = rms(23,23.8)
        report['after_new_short_pulses_rms'] = rms(26.5,27.5)
        windows=[]
        for t in np.arange(8.5, 18.6, 0.25):
            z = y[int(t*rate):int((t+0.2)*rate)]
            mag = np.abs(np.fft.rfft((z-z.mean())*np.hanning(len(z))))
            freq = np.fft.rfftfreq(len(z), 1/rate)
            band = (freq >= 220)&(freq <= 600)
            peak = float(freq[band][np.argmax(mag[band])])
            windows.append({'t': round(float(t),2), 'peak_hz': round(peak,2),
                            'note': 'high' if peak > 400 else 'low'})
        report['loop_pitch_windows'] = windows
        report['both_recorded_pitches_present'] = {w['note'] for w in windows} == {'low','high'}
        report['grf6_route_after'] = a.read([0x10,0x20,7,0],34)
        report['grf6_completely_unrouted'] = report['grf6_route_before'] == report['grf6_route_after'] == [0]*34
        report['passed'] = (report['loop_after_mute_rms'] > 0.001 and
                            report['after_hold_rms'] < 0.001 and
                            report['after_new_short_pulses_rms'] < 0.001 and
                            report['both_recorded_pitches_present'] and
                            report['grf6_completely_unrouted'])
    finally:
        gate(False)
        ks.close()
        a.all_notes_off()
        time.sleep(0.5)
        try:
            report['patch_restored'] = base.safe_load(a,start)
        except Exception as exc:
            report['patch_restored'] = f'FAILED: {exc!r}'
        (base.OUTD/f'{LABEL}_report.json').write_text(json.dumps(report,indent=2)+'\n')
        a.close()
    print(json.dumps(report,indent=2),flush=True)

if __name__ == '__main__':
    main()
