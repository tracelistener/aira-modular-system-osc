# REC/PLAY from the GRF 6 jack (v3.5, experimental)

**Status:** tested on one SCOOPER on 2026-09-30 (see [Tests](#tests)). v3.5 is v3.2 plus 274 changed bytes in the application. Every change is listed in [`evidence/v35-diff-vs-v32.json`](../evidence/v35-diff-vs-v32.json).

## Why firmware

On stock firmware nothing outside the unit can press REC/PLAY. Before writing any patch, I checked that over USB:

- None of 4,000+ MIDI messages triggered REC/PLAY: notes, CCs, pitch bend, pressure and transport, on all 16 channels.
- The unit sends no MIDI and changes no readable parameter when the button is pressed.

Some people wire a jack across the button. v3.5 does the same job in firmware, using the GRF 6 jack.

## The SCATTER button shares the GRF 6 input

The SCATTER button and the GRF 6 jack are combined before the firmware sees them. Pressing SCATTER raises the GRF 6 reading by about twice what a KeyStep gate adds.

These are measured values: the firmware's scaled value for GRF 6, with the KeyStep connected.

| SCATTER button | Gate low | Gate high |
|---|---:|---:|
| Released | 0.00 | 0.50 |
| Held | 0.99 | 1.36 |

So one threshold can't work. The decoder reads the button's own switch contact (GPIO port `0x4002D034`, bit 15):

- With SCATTER released, a reading of 0.25 or more is a gate.
- With SCATTER held, a reading of 1.17 or more is a gate.

Each threshold has at least 0.17 of margin on both sides. The noise was about 0.0002.

While the button is moving, the reading sits somewhere between the levels. So after every change of the switch contact, bounce included, the decoder keeps its previous answer for 20 ticks of Roland's 1 kHz system tick. This hold is needed because Roland's REC/PLAY input reacts to a single active reading: in an emulator run of Roland's own debounce code, one active reading is enough for a press, and release needs seven inactive readings in a row.

The decoder:

```text
button = GPIO bit 15                     ; 1 = released
if button changed:                       ; press, release or bounce
    remember button and the current tick; keep the previous answer
elif fewer than 20 ticks since then:
    keep the previous answer
else:
    answer = sample >= (0.25 if released else 1.17)
```

## How the SCOOPER reads its buttons

A routine at `0x6009A0F4` (firmware 1.05, build 0493) collects five inputs. Roland's debounce code turns them into press and release events.

| Input | Stock | v3.5 |
|---:|---|---|
| 0 | REC/PLAY button: GPIO bit 12, reads 0 when pressed | REC/PLAY button **or** the GRF 6 gate |
| 1 | Button: GPIO bit 13 | unchanged |
| 2 | SCATTER button: GPIO bit 15 | unchanged |
| 3 | A gate the ARM reads back from the DSP | unchanged |
| 4 | A second read-back gate | always 0 |

Input 0 is the REC/PLAY button's own input, so everything after it is Roland's code: debounce, record and play, hold-to-delete, and waiting for a SYNC TRIG clock. This input routine is byte-identical to v3.3's (`tools/build/recplay_patch.py`).

## What v3.5 changes

The GRF 6 path:

1. GRF 6 enters the DSP as input `6009`, and Roland's DSP scales it.
2. **Changed:** the scaled value is stored in the register the ARM's gate reader uses (`A01A`), instead of the Customizer patch export (`A103`).
3. **Changed:** the gate reader hands that value to the new decoder.
4. **Changed:** the decoder's answer becomes input 0 of the routine above.

Because the GRF 6 reading no longer drives SCATTER, the SCATTER button gets its own handling:

- A hook in the panel event broker toggles the SCATTER setting (area 4, parameter `0x69`) once per physical press. It latches, so a held button can't toggle twice, and it passes every original event on.
- The SCATTER lamp (LED 5) shows that setting.

All changes, as application addresses:

| Address | Bytes | Change |
|---|---:|---|
| `0x6009A0F8` | 46 | Input routine: REC/PLAY = button OR GRF 6 gate |
| `0x6006C66E` | 2 | DSP: GRF 6's scaled value goes to `A01A` instead of `A103` |
| `0x6006CA24` | 2 | DSP: an old read-back report now goes to `A103`, so a GRF 6 cable in a patch no longer carries the jack |
| `0x60011138` | 14 | The gate reader branches to the decoder |
| `0x60088280` | 80 | Decoder |
| `0x6000025C` | 4 | The panel event broker branches to the SCATTER hook |
| `0x60088380` | 96 | SCATTER hook |
| `0x6000AA90` | 6 | The SCATTER lamp calls the lamp helper |
| `0x60088480` | 12 | Lamp helper: returns the SCATTER setting |
| `0x60088C00` | 20 | Decoder and hook state |

The new code lives in the unused BITRAZER area right after the SYSTEM OSC master programs, so v3.5 is SCOOPER-only, like v3.2. The firmware file is the v3.2 update container with this application inside, and the boot and updater regions are unchanged.

## Tests

On v3.5 itself, on 2026-09-30, over USB:

- The KeyStep 32's GATE was patched into GRF 6.
- Gates were sent to the KeyStep as MIDI notes.
- Audio was captured from OUTPUT 1-2.
- Each script saved the patch first and restored it at the end.

| Test | Result | Evidence |
|---|---|---|
| Record and play: two 125 ms gates, then mute the source | A 3 s two-note loop kept playing at the live level (RMS 0.02455) | [`hardware-test-v35-recplay.json`](../evidence/hardware-test-v35-recplay.json) |
| Delete: hold the gate for 3.5 s | Silent afterwards; later short gates brought nothing back | same file |
| Customizer bulk commands | All 44 bulk cable rows read back equal to the individual cable reads; a bulk write changed a cable; the patch was restored exactly | [`hardware-test-v35-native-bulk.json`](../evidence/hardware-test-v35-native-bulk.json) |
| SCATTER presses with the gate low | 20 presses while a tone fed the looper. Muted 12 s after the last press: silent, so no recording was started | [`hardware-test-v35-scatter-presses.json`](../evidence/hardware-test-v35-scatter-presses.json) |
| By hand | REC/PLAY light, SCATTER lamp and a patch loaded from the Customizer app all worked | user report |
| GRF 6 routes | All 34 empty before and after every test | all of the above |

Earlier the same day, a diagnostic build was tested. Its gate, button and lamp code is byte-identical to v3.5's ([`hardware-test-v35-scatter-held-gates.json`](../evidence/hardware-test-v35-scatter-held-gates.json)):

- Gates while SCATTER was held worked REC/PLAY without changing SCATTER.
- Press, hold, release, press toggled SCATTER on, then off.

Offline checks, all in a Unicorn ARM emulator:

- **Decoder:** threshold boundaries, button press and release with the gate high and low, bounce, and tick-counter rollover.
- **Hook and lamp:** the SCATTER hook and the lamp code.
- **Roland's debounce:** its REC/PLAY debounce path.

## Limits

- **Calibration:** the levels above were set on one SCOOPER with a KeyStep 32. A much lower gate voltage might not reach 1.17 while SCATTER is held.
- **20 ms after SCATTER:** a gate that starts within 20 ms after a SCATTER press or release registers late. A gate that starts and ends inside that window is missed.
  - The 20 ms was chosen, not measured.
  - The press test found no false REC/PLAY presses, but slow roll-offs and long holds weren't part of it.
- **Gate plus button:** while either is active, the other can't start a new press.
- **Patches:** GRF 6 no longer works as a patch input. Remove GRF 6 cables.
- **Power-up:** a gate held high during power-up hasn't been tested. The start-up check could see REC/PLAY as held.
- **USB audio:** not tested while USB audio is streaming into the unit. Per the DSP trace, Roland's GRF 6 processing also adds in one USB audio channel. It was silent in every test.
- **Converted units:** not tested on BITRAZER, DEMORA or TORCIDO hardware switched to SCOOPER.

## History

- **v3.3 (2026-09-25)** used the same input routine but a different gate. That gate turned out to follow whichever jack was cabled to the SYNC TRIG input. With gates arriving there, REC/PLAY waited for the next gate (Roland's sync rule), so taps acted one late. Removed from `firmware/`; it's in the git history.
- **v3.4** failed on hardware and was never published.
- **v3.5** reads GRF 6 directly and handles the SCATTER button separately.
