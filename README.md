# SYSTEM OSCILLATOR for the Roland AIRA Modular SCOOPER

This custom firmware brings the SYSTEM-1m's oscillator waves to the SCOOPER. In the AIRA Modular Customizer, it takes the place of the FORMANT FILTER module. The wave programs are Roland's own SYSTEM-1m DSP code (firmware 1.30). They're adapted to run on the SCOOPER's DSP, which uses the same chip family.

It's unofficial: not made, endorsed or supported by Roland. Flash at your own risk.

![The VOICE_S1M_CB preset in the Customizer: the MIDI gate goes into SYNC TRIG IN to strike the cowbell](docs/img/customizer-patch.png)

## What you get

- **Seven waves on the WAVE knob:** FM, FM+SYNC, TRI, LOGIC, NOISE SAW, VOWEL and CB (cowbell).
- **Three knobs:** RANGE (64' to 4'), WAVE and COLOR.
- **The same jacks as the stock SAW and SQR oscillators:**

| Jack | What it does |
|---|---|
| CV IN | Pitch, same scale as the stock oscillators. |
| FINE IN | +1.0 raises pitch 1.2 semitones (a tenth of an octave), same as the stock SAW/SQR. |
| COLOR IN | Added to the COLOR knob. +1.0 covers the knob's full range, and the total stays inside that range. |
| SYNC TRIG IN | Each rising edge through 0.3 restarts the wave (hard sync). On CB it strikes the bell. |
| OUT | Audio. |
| SYNC OUT | The SYSTEM saw. Patch it into another oscillator's SYNC TRIG IN to sync that oscillator. |

It's tested on hardware:

- Pitch is exact equal temperament.
- RANGE labels match the stock oscillators.
- FINE IN, COLOR IN and SYNC TRIG IN behave the same as on the stock SQR.

Details are in [docs/hardware-test.md](docs/hardware-test.md).

## CB needs something to hit it

CB is a percussion voice, the SYSTEM-1's 808-style cowbell, not a held tone. It only makes sound when something hits SYNC TRIG IN.

On a SYSTEM-1, each key press hits it internally. The SCOOPER's module has no gate input, so the hit comes in through SYNC TRIG IN.

- Patch MIDINOTE's GATE into SYNC TRIG IN. `VOICE_S1M_CB.bin` is wired this way.
- Any rising edge through 0.3 works: a gate, a clock, an LFO, or another oscillator for metallic buzzes.
- COLOR sets the decay. At 100 it rings for minutes.

**With nothing patched into SYNC TRIG IN, CB is silent.**

## SCOOPER only

One Roland update file (AIRA Modular system program 1.05) serves all four AIRA Modular units: DEMORA, TORCIDO, BITRAZER and SCOOPER. Each unit runs its own part of it. This firmware stores the new wave programs in the space used by the TORCIDO and BITRAZER parts, so on those units it would break their built-in effect. The DEMORA part is untouched, but this firmware has never been tried on a DEMORA. Only flash it on a SCOOPER.

## Install

You need a SCOOPER, the AIRA Modular Customizer (Windows) and Python 3.

1. In the Customizer, load `presets/SAFE_EMPTY.bin` and send it to the unit, so it starts up with an empty patch.
2. Check the firmware hash. It must be `03f4f5f8221092dba6aacaa33c98ba1cc1eddeaf96ae254759388ce5460f51a9`:
   ```
   certutil -hashfile firmware\AIRA_MODULAR_UPD.BIN SHA256
   ```
3. Flash `firmware/AIRA_MODULAR_UPD.BIN` with Roland's normal update procedure.
4. Close the Customizer, then run from this folder:
   ```bash
   python customizer/install_customizer.py
   ```
   The installer backs up everything it replaces and prints the command to undo it. If it doesn't recognise your Customizer version, it stops without changing anything. It also switches on safe patch loading: the Customizer empties the unit before sending a patch, which avoids overload hangs.
5. Open the Customizer. SYSTEM OSCILLATOR is in the module menu where FORMANT FILTER was. Load a preset to start.

## Presets

| File | Patch |
|---|---|
| `VOICE_SYSTEM_TRI.bin` | Simple TRI voice: MIDINOTE → SYSTEM OSC → AMP, with an ADSR. |
| `VOICE_S1M_FM.bin`, `_FMSYNC`, `_LOGIC`, `_NOISESAW`, `_VOWEL` | The same voice on each of the other waves. |
| `VOICE_S1M_CB.bin` | Cowbell, with the gate patched into SYNC TRIG IN. |
| `VOICE_S1M_SYNC_DEMO.bin` | A stock SAW hard-syncs a SYSTEM TRI while the envelope sweeps the TRI's pitch (classic sync sweep). |
| `SAFE_EMPTY.bin` | Empty patch. |

## Experimental: REC/PLAY from the GRF 6 jack (v3.5)

v3.5 is v3.2 plus one feature: a gate into the **GRF 6 jack** works REC/PLAY, as if you pressed the button. It's tested on one SCOOPER with an Arturia KeyStep 32's GATE output.

- **Short gate:** a press. The first one records, the next one plays.
- **Gate held for about 3.5 s:** deletes the loop, the same as holding the button.
- **REC/PLAY button:** still works. The gate and the button act like two buttons wired together: while one is down, the other can't start a new press.
- **SCATTER button:** still switches SCATTER, and its lamp shows whether SCATTER is on. Gates never switch SCATTER.
- **Clock in SYNC TRIG:** the gate goes through the same code as the button. With a clock patched into SYNC TRIG it should wait for the next pulse, just as the button does. This wasn't tested separately.

**GRF 6 becomes a REC/PLAY input only.** It no longer feeds Customizer patches. Remove every cable from GRF 6 in your patches, including the GRF 6 → SCATTER cable in the default SCOOPER patch.

**Install:** follow the steps under Install, but flash `firmware/experimental/v3.5-grf6-recplay/AIRA_MODULAR_UPD.BIN` instead. Its SHA-256 is `f516953ae85d0b2291db3eb72ed773ba5641acda1f866832eace52f664f7bee8`. The Customizer files are the same as for v3.2.

**Limits:**

- **Calibration:** the gate levels were set on one SCOOPER with the KeyStep 32. A gate with a much lower voltage might not register while SCATTER is held.
- **20 ms after SCATTER:** for 20 ms after you press or release SCATTER, the firmware ignores changes on GRF 6. A gate that starts in that window registers late, and one shorter than 20 ms can be missed.
- **Power-up:** keep the gate low while powering on. A gate held during power-up hasn't been tested.
- **USB audio:** not tested while USB audio is streaming into the unit.
- **SCOOPER only,** like v3.2.

**Converted units:** BITRAZER, DEMORA and TORCIDO hardware has no REC/PLAY button. On a unit switched to SCOOPER (for example with [aira-switcher](https://github.com/tracelistener/aira-switcher)), this is a way to record. It hasn't been tested on those units. Switch first, then flash v3.5, because aira-switcher only accepts stock firmware.

**v3.3 is gone.** It only reacted to a gate cabled to the SYNC TRIG input, so REC/PLAY waited for the next gate. It's still in the git history.

How it works and how it was tested: [docs/recplay-jack.md](docs/recplay-jack.md).

## DSP load: stay under about 300

A patch that asks for more DSP than the SCOOPER has will hang it: light-blue LED, and you have to power-cycle. The ceiling is about 300 program records.

| Module | Records |
|---|---:|
| SYSTEM OSC | 94–129 depending on the wave: FM 98, FM+SYNC 124, TRI 99, LOGIC 94, NOISE SAW 129, VOWEL 128, CB 96 |
| ADSR, LFO | 48 each |
| stock SAW | 45 |
| AMP | 19 |
| MIDINOTE | 16 |
| MIXER | 12 |

- One SYSTEM OSC fits in any normal patch.
- Two SYSTEM OSCs plus an ADSR, AMP and MIXER comes to about 302 records, and that hung the unit in testing.
- When you swap a module, the unit counts the old and new ones together for a moment. Empty a slot before putting something heavy in it.

## Known issues

- **Stuck note (seen once, 2026-09-24).** While playing, a note stayed on until the unit was restarted. The cause is unknown and it hasn't been reproduced. If it happens, sending All Notes Off (CC 123) from your controller may clear it without a restart. If you can reproduce it, open an issue saying what you were doing at the time: turning WAVE while holding keys, loading a patch, which wave was selected.
- **A CB that won't stop isn't stuck.** With COLOR near 100 the bell rings for up to several minutes; that's how it's designed. Turn COLOR down, or put an AMP with an envelope after it.

## Going back

1. Flash Roland's official AIRA Modular system program 1.05 (`airamod_sys_v105.zip` from Roland's support site for any AIRA Modular unit).
2. Undo the Customizer change with the command the installer printed:
   ```bash
   python customizer/install_customizer.py --restore "<backup folder>"
   ```

## What's in here

| Folder | Contents |
|---|---|
| `firmware/` | v3.2, the exact image that was flashed and tested. `firmware/experimental/` holds v3.5 (REC/PLAY from the GRF 6 jack), tested on one SCOOPER. `SHA256SUMS.txt` lists every file's hash. |
| `presets/` | Customizer patch files. |
| `customizer/` | The six changed Customizer files and the installer. |
| `docs/` | [How it works](docs/how-it-works.md), the [hardware test results](docs/hardware-test.md) and [REC/PLAY from the GRF 6 jack](docs/recplay-jack.md). |
| `evidence/` | Raw JSON from the offline audit, the ARM emulation run and the USB hardware tests. |
| `tools/` | The build and test scripts, as used. See [tools/README.md](tools/README.md). |

## Credits and legal

- The firmware image is Roland's AIRA Modular firmware with modifications, and it contains DSP programs from Roland's SYSTEM-1m firmware. Roland owns that code.
- The files in `customizer/files/` are modified Roland Customizer files.
- Roland, AIRA, SCOOPER, SYSTEM-1, SYSTEM-1m and TR-808 are trademarks of Roland Corporation.
