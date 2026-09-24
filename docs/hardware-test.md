# Hardware test, 2026-09-24

These tests ran on one SCOOPER over USB. Two passes on firmware v3.1 used about 110 audio captures. Then v3.2 was flashed and FINE IN was re-checked. v3.2 differs from v3.1 only in the FINE IN constant, so the other v3.1 results carry over.

## Method

- **Patching.** Each test patch was built live over MIDI SysEx, the same messages the Customizer sends, and every write was read back.
- **Playing.** Notes came from MIDI note messages through a MIDINOTE module.
- **Recording.** Audio came from the unit's USB output (OUTPUT 1-2) at 48 kHz.
- **Measuring pitch.** Each spectral peak was fitted with a Hann-windowed DTFT, which is precise to well under 0.01 cent on these tones.
- **Afterwards.** The user's patch was saved first and put back when the tests finished.

Scripts are in `tools/live/`, and raw numbers are in `evidence/hardware-test-*.json`.

## Pitch vs the stock SQR

For each note, the SYSTEM OSC (TRI, RANGE 32') and the stock SQR (RANGE 32') were recorded one after the other:

| Note | Equal temperament (Hz) | SYSTEM OSC | Stock SQR |
|---:|---:|---:|---:|
| 36 | 65.406 | 65.406 (0.00 c) | 65.392 (−0.39 c) |
| 48 | 130.813 | 130.813 (0.00 c) | 130.784 (−0.39 c) |
| 60 | 261.626 | 261.626 (0.00 c) | 261.567 (−0.38 c) |
| 72 | 523.251 | 523.251 (0.00 c) | 523.135 (−0.38 c) |
| 84 | 1046.502 | 1046.502 (0.00 c) | 1046.270 (−0.38 c) |

The stock SQR runs a constant 0.38 cents flat; that's Roland's own tuning. The stock SAW runs 10.6 cents flat, and its FINE knob moves pitch about 1 cent per step. `VOICE_S1M_SYNC_DEMO.bin` sets the SAW's FINE to 61 to compensate.

**RANGE.** At note 60, SYSTEM RANGE 64'/32'/16'/8'/4' measured 130.813 / 261.626 / 523.251 / 1046.502 / 2093.005 Hz, 0.00 cents in every case. That's the same pitch as the SQR's RANGE setting with the same label.

## All waves, in every slot

The SYSTEM OSC was placed in slot 1, slot 2 and slot 6. Every wave was played at note 60. Slot 1 matters because Roland's RANGE table sits inside slot 1's program area.

| Wave | Slot 1 | Slot 6 |
|---|---:|---:|
| FM | 0.00 c | 0.00 c |
| FM+SYNC | 0.00 c | 0.00 c |
| TRI | 0.00 c | 0.00 c |
| LOGIC | −0.17 c | −0.18 c |
| NOISE SAW | +3.3 c | +3.3 c |
| VOWEL | +0.5 c | +0.5 c |
| CB (second partial) | 391.916 Hz (expected 391.92) | 391.914 Hz |

- **LOGIC, NOISE SAW and VOWEL** have spectra that aren't a single clean harmonic series, so they read slightly off. Their spectra match captures of the earlier v1 firmware exactly, so this is how the SYSTEM-1m code behaves; nothing new was introduced.
- **Two SYSTEM OSCs at once** (TRI 32' in slot 1 and FM 16' in slot 6) both measured exact.

## FINE IN (v3.2)

MIDINOTE's CV (note/120) was patched into FINE IN of both oscillators:

| | CV 0.5 (note 60) | CV 0.6 (note 72) |
|---|---:|---:|
| Stock SQR | +59.99 c | +71.99 c |
| SYSTEM OSC v3.2 | +60.00 c | +72.00 c |
| SYSTEM OSC v3.1 | +50.00 c | +60.00 c |

v3.1 used 100 cents per 1.0. v3.2 changes one constant to match the stock 120.

## COLOR IN

**Stock SQR** (COLOR = pulse width):

| Setting | Duty cycle |
|---|---:|
| knob 0 | 0.500 |
| knob 50 | 0.388 |
| knob 0 + CV 0.5 | 0.388 |
| knob 100 | 0.051 |
| knob 100 + CV 0.5 | 0.051 |

**SYSTEM OSC TRI** (measured by output level):

| Setting | Output level |
|---|---:|
| knob 50 | 0.02147 |
| knob 0 + CV 0.5 | 0.02147 |
| knob 100 | 0.01458 |
| knob 100 + CV 0.5 | 0.01459 |

Both oscillators work the same way: +1.0 covers the knob's full range, and the total stops at the end of the range.

## SYNC TRIG IN

- **Stock SAW as the master.** The master was a stock SAW at 64'. Both slaves were at 32': the SYSTEM TRI and a stock SQR. A synced output repeats at the master's rate, so its partials sit at exact multiples of the master frequency. Master frequencies below come from recording the SAW alone; slave values are the frequency of the slave's second partial, halved.

| Master | Master frequency | SYSTEM TRI | Stock SQR |
|---|---:|---:|---:|
| SAW, FINE 50 | 130.0154 Hz | 130.0155 Hz | 130.0154 Hz |
| SAW, FINE 80 | 132.2788 Hz | 132.2788 Hz | 132.2788 Hz |

- **SYSTEM OSC's SYNC OUT as the master.** Patched into the stock SQR's SYNC TRIG IN, it locked the SQR to the SYSTEM OSC exactly: 130.8128 Hz, 0.00 c.

## CB

The CB was hit through SYNC TRIG IN from MIDINOTE's gate. TRI's peak level was 0.040.

| Setting | Peak vs TRI | Time to −40 dB | Model, −60 dB | Second partial |
|---|---:|---:|---:|---:|
| COLOR 70, note 60 | +2.1 dB | 0.31 s | 0.55 s | 391.915 Hz |
| COLOR 70, note 72 | +5.6 dB | 0.35 s | 0.55 s | 783.829 Hz |
| COLOR 0, note 60 | +4.8 dB | 0.040 s | 0.072 s | 392.364 Hz |
| COLOR 0, note 72 | +1.5 dB | 0.048 s | 0.072 s | 783.762 Hz |

- **Decay.** The model is a transcription of the SYSTEM-1 plug-out's CB code; see [how-it-works.md](how-it-works.md). The measured decay rates match the model.
- **No trigger.** With nothing in SYNC TRIG IN, the output stayed at digital silence (RMS 1.5e-5, the noise floor), which is the intended behaviour.

## Stability

- **LFO into SYNC TRIG IN.** This was the earlier crash report. It was tested on TRI, CB, NOISE SAW and VOWEL, at the fastest LFO rate, and together with an LFO on COLOR IN. There were no crashes, and the unit answered SysEx after every run.
- **Stress.** A note was held with an LFO on SYNC TRIG IN and COLOR IN and CV on FINE IN. Meanwhile WAVE, RANGE and COLOR were changed 81 times in 18 s. The unit stayed responsive, and TRI measured 261.6255 Hz (0.00 c) afterwards.
- **Heavy patch.** VOWEL (128), NOISE SAW (129), MIDINOTE (16) and MIXER (12) come to 285 records. A phrase was played and one oscillator's wave was swapped in the middle; it was fine.
- **Presets.** All eight presets were loaded and played. Every note was in tune, apart from the wave-specific offsets above. Every tail ended in silence.

## The one hang

While my script was restoring the user's patch after the tests, it overwrote slots in place. For a moment that stacked two SYSTEM OSCs, an ADSR, an AMP and a MIXER: about 302 records, plus modules not yet unloaded. The unit hung (light-blue LED), and a power cycle recovered it.

This is the DSP-load ceiling described in the README, not a firmware bug. The restore script now empties the patch first, waits, and then rebuilds it.
