"""Derive the v3.2 sources from v3.1. The only DSP change is the FINE IN constant: 1/120 -> 1/100, so FINE IN
matches the stock SAW/SQR scale measured over USB on 2026-09-24 (+1.0 = 0.1 octave = 120 cents; v3.1 gave 100)."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
V31, V32, CB = ROOT / 'work/selector-v31', ROOT / 'work/selector-v32', ROOT / 'work/cowbell2'


def derive(src, dst, subs):
    t = src.read_text(encoding='utf-8')
    for old, new in subs:
        assert t.count(old) >= 1, (src.name, old)
        t = t.replace(old, new)
    dst.write_text(t, encoding='utf-8')
    print('wrote', dst.relative_to(ROOT))


derive(CB / 'system_osc_v31.py', CB / 'system_osc_v32.py', [
    ("SYSTEM OSCILLATOR v3.1 wave programs: v3's jack set with a lighter adapter.",
     "SYSTEM OSCILLATOR v3.2 wave programs: v3.1 with the stock FINE IN scale."),
    ('in2 FINE IN (1.0 = 1 semitone)', 'in2 FINE IN (1.0 = 0.1 octave = 1.2 semitones, the stock SAW/SQR scale)'),
    ('0002 <1/120>       r0 = FINE/120 + CV', '0002 <1/100>       r0 = FINE/100 + CV'),
    ('ONE_120TH = (0x0222, 0x2222)   # 0x02222222 = 1/120 in the [s][e2][m29] immediate format (e=0: m/2^32)',
     'FINE_K = (0x028f, 0x5c29)      # 0x028F5C29 = 1/100 in the [s][e2][m29] immediate format (e=0: m/2^32)'),
    ('abs(c32(*ONE_120TH) - 1 / 120) < 1e-9', 'abs(c32(*FINE_K) - 1 / 100) < 1e-9'),
    ('ONE_120TH[0], ONE_120TH[1]', 'FINE_K[0], FINE_K[1]'),
])
derive(V31 / 'build_wave_selector_v31.py', V32 / 'build_wave_selector_v32.py', [
    ('SCOOPER-only WAVE selector v3.1 (v3 jacks, lighter adapter, COLOR clamp)',
     'SCOOPER-only WAVE selector v3.2 (v3.1 + stock FINE IN scale)'),
    ('work/cowbell2/system_osc_v31.py', 'work/cowbell2/system_osc_v32.py'),
    ('from system_osc_v31 import', 'from system_osc_v32 import'),
    ("outputs/wave-selector-v31-inputs", "outputs/wave-selector-v32-inputs"),
    ('in2 FINE IN (1.0 = 1 semitone)', 'in2 FINE IN (1.0 = 1.2 semitones, stock SAW/SQR scale)'),
])
derive(V31 / 'verify_wave_selector_v31.py', V32 / 'verify_wave_selector_v32.py', [
    ('from build_wave_selector_v31 import *', 'from build_wave_selector_v32 import *'),
])
