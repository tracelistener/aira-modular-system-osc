"""Re-render the SYSTEM-1 plug-out CB wave with clean note-on hits (offline, no audio/MIDI devices).
Run with the plug-out venv: .../work/.venv-vst/Scripts/python.exe render_cb_plugout.py"""
import sys, json, wave
from pathlib import Path
import numpy as np
sys.path.insert(0, 'C:/Users/admin/Documents/Codex/2026-09-22/files-mentioned-by-the-user-handoff/work')
import plugout_reference as ref
OUT = Path(__file__).resolve().parents[2] / 'outputs/cowbell-v2/reference-plugout'
OUT.mkdir(parents=True, exist_ok=True)
SR = 48000
ref.MIX1 = 60

def render(color, events, seconds, rng=1):
    ref.bare_patch(); ref.setp('osc1_range', rng)
    ref.setp('osc1_wave', 5); ref.setp('osc1_extend', 1); ref.setp('osc1_color', color)
    y = ref.p(events, duration=seconds, sample_rate=SR, num_channels=2, reset=True)
    return np.asarray(y)[0]

def envdb(y, hop=0.005):
    L = int(hop * SR); n = len(y) // L
    r = np.sqrt((y[:n * L].reshape(n, L) ** 2).mean(1))
    return 20 * np.log10(np.maximum(r, 1e-9))

if __name__ == '__main__':
    rows = []
    # hits: note-on at 0.5 s (held 0.3 s), 1.5 s (held 1.0 s, different key), 3.0 s (same key as first)
    ev = [(bytes([0x90, 69, 100]), 0.5), (bytes([0x80, 69, 0]), 0.8),
          (bytes([0x90, 72, 100]), 1.5), (bytes([0x80, 72, 0]), 2.5),
          (bytes([0x90, 69, 100]), 3.0), (bytes([0x80, 69, 0]), 3.2)]
    for color in (0, 64, 128, 192, 240, 255):
        y = render(color, ev, 4.5)
        e = envdb(y)
        with wave.open(str(OUT / f'CB_plugout_color{color:03d}.wav'), 'wb') as f:
            f.setnchannels(1); f.setsampwidth(2); f.setframerate(SR)
            f.writeframes((np.clip(y * 4, -1, 1) * 32767).astype('<i2').tobytes())
        np.save(OUT / f'CB_plugout_color{color:03d}.npy', y.astype(np.float32))
        marks = {t: float(e[int(t / 0.005)]) for t in (0.45, 0.505, 0.55, 0.6, 0.7, 0.9, 1.45, 1.505, 1.6, 2.0, 2.9, 3.005, 3.1)}
        rows.append(dict(color=color, peak=float(np.abs(y).max()), db=marks))
        print(color, 'peak %.4f' % np.abs(y).max(), ' '.join('%s:%.0f' % (k, v) for k, v in marks.items()))
    (OUT / 'render.json').write_text(json.dumps(rows, indent=1))
