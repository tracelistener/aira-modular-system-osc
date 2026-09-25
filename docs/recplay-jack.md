# REC/PLAY from a jack (v3.3, experimental)

**Status:** built and checked offline. **Not yet tested on hardware.**

The SCOOPER's REC/PLAY button can't be triggered from outside on stock firmware. Before writing this patch, I tested that on the unit over USB:
- none of 4,000+ MIDI messages worked (notes, CCs, pitch bend, pressure and transport on all 16 channels);
- the unit sends no MIDI when the button is pressed, and no readable parameter changes.

Some people have added a hardware jack wired across the button. v3.3 does the same thing in firmware, using an existing jack.

## How the SCOOPER reads its buttons

One small routine at `0x6009A0F4` (firmware 1.05, build 0493) collects five inputs. A debounce routine then turns them into press/release events for the panel code.

| Input | Source |
|---:|---|
| 0 | REC/PLAY button: GPIO port `0x4002D034`, bit 12 (reads 0 when pressed) |
| 1 | GRF 5 button: bit 13 |
| 2 | GRF 6 button: bit 15 |
| 3 | SYNC TRIG control input: a CV gate the ARM reads back from the DSP |
| 4 | SCATTER control input: a CV gate read back the same way |

The mapping comes from two pieces of evidence:

- **Buttons.** The updater reads the same three bits in the same order. Its backup gesture ("press GRF 5 ten times") counts presses of ID 1, which was confirmed live.
- **Gates.** Inputs 3 and 4 are filled from DSP read-back values, which the panel code also shows on the GRF 5 and GRF 6 LEDs. That's why a gate into the GRF 5 or GRF 6 jack acts like pressing that button.

## The change

v3.3 replaces that routine with this one (46 bytes in the original 50, using the routine's own constants):

```text
ldr   r1, =0x4002D000      ; GPIO
ldr   r2, [r1, #0x34]      ; sample the port once
ldr   r3, =SCATTER_GATE
ldr   r3, [r3]
ubfx  r1, r2, #12, #1      ; REC/PLAY button
cbz   r3, 1f
movs  r1, #0               ; SCATTER gate high -> REC/PLAY reads "pressed"
1: str r1, [r0]
ubfx  r1, r2, #13, #1      ; GRF 5, unchanged
str   r1, [r0, #4]
ubfx  r1, r2, #15, #1      ; GRF 6, unchanged
str   r1, [r0, #8]
ldr   r1, =SYNC_TRIG_GATE  ; SYNC TRIG gate, unchanged
ldr   r1, [r1]
cbz   r1, 2f
movs  r1, #1
2: str r1, [r0, #12]
movs  r1, #0               ; SCATTER gate no longer reported as its own input
str   r1, [r0, #16]
bx    lr
```

The gate stands in for a finger on the button, and everything after that is Roland's own code. So debounce, record/play, hold-to-delete and waiting for the SYNC TRIG clock behave the same as with the physical button.

## Checks

- An ARM emulator (Unicorn) ran the patched routine for all 32 combinations of the three buttons and the two gates. Every output was as intended.
- The application image differs from v3.2 in 42 bytes, all inside the routine. The update container round-trips cleanly, and the boot region is identical.
- Hardware test, not run yet (`tools/live/v33_recplay_test.py`):
  1. Patch a MIDI gate into the SCATTER input.
  2. Tap to record, then tap to play.
  3. Mute the source and check the loop plays.
  4. Hold the gate and check the loop is deleted.

## Caution

Don't have a gate high on that input while powering on. The start-up check could see REC/PLAY as held and open the overdub setting. It's probably harmless, since the gate values are likely not read yet at that point, but that hasn't been confirmed.
