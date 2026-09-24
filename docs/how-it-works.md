# How it works

## The platform

The AIRA Modular units pair an ARM microcontroller with a Roland ESC2 DSP. The DSP is floating point and runs its programs at 96 kHz.

- **Modules.** A Customizer patch fills six slots with modules. Each module is a DSP program that the ARM loads into the slot's program area.
- **Knobs and cables.** The ARM sends knob values to the DSP as coefficients. Cables are routes between input and output registers.
- **Shared chips.** The SYSTEM-1m and TR-8 use the same DSP family and the same instruction format. That's why SYSTEM-1m code can run on the SCOOPER at all.

## Where the waves come from

Each SYSTEM-1m oscillator wave is a self-contained program, a "cell", on its secondary DSP. The waves here are cells taken from SYSTEM-1m firmware 1.30:

| Wave | Cell |
|---|---:|
| FM | 10 |
| FM+SYNC | 14 |
| TRI | 2 |
| LOGIC | 21 |
| NOISE SAW | 13 |
| VOWEL | 6 |
| CB | 9 |

A cell reads four inputs and writes three outputs:

| Register | Role |
|---|---|
| `2004` | Pitch. f = 16.3516 Hz × 2^pitch × range |
| `2005` | Range multiplier |
| `2006` | COLOR, 0..1 |
| `2007` | Sync gate `a`, where phase = a·(wrap + 1) − 1. 1 runs, 0 resets |
| `2008`, `200A`, `200C` | Outputs |

The port renames those registers to the SCOOPER's slot addresses and gives every cell a private block of data memory, so several instances can run side by side.

## The adapter

Each wave program starts with a short adapter. Every record in it has a shape found in Roland's own programs:

- **Pitch.** `pitch = 10 × (CV IN + FINE IN / 100)`, written to `2004`.
  - MIDINOTE's CV is note/120, so this gives note/12, the SYSTEM-1m's pitch unit.
  - FINE IN adds a tenth of an octave per 1.0, the stock SAW/SQR scale.
  - This is two multiplies. Their record shapes come from SYSTEM-1m records 31 and 87.
- **RANGE.** The knob indexes Roland's own RANGE table (0.125 … 4). The SCOOPER writes the result into a per-slot coefficient, which feeds `2005`.
- **COLOR.** `min(max(knob + COLOR IN, 0), 1)`, written to `2006`. The add is an AMP record; the clamp uses the CROSSFADE module's min/max records.
- **SYNC TRIG IN.** This is Roland's own trigger detector, copied from the stock S&H module. The input is compared against 0.3 to give 1.0 or 0.0. That value minus its previous sample, floored at 0, gives `strike`, which is 1 for exactly one sample on each rising edge. `2007 = 1 − strike`, which resets the cell's phase.
- **CB.** `strike` also goes to CB's envelope trigger, the slot the SYSTEM-1m's main DSP drives on note-on.

CB is the SYSTEM-1's cowbell. Its native code in the SYSTEM-1 plug-out (x64) uses the same constants as cell 9:

- **Tone.** Two pulse waves, at f and 1.498·f, are mixed and run through a high-pass state-variable filter and three one-pole filters.
- **Envelope.** `env = trig if trig > env else env·k`, with `k = 0.999 + 0.0009999·(1.8c − 0.8c²)`, where c is COLOR. So COLOR is decay.
- **Trigger.** The envelope starts at zero and needs a trigger. That's why CB is silent until something hits SYNC TRIG IN.

## The WAVE selector

Roland's firmware loads one fixed program for each module type. A small ARM patch hooks the loader for module type 28, which was FORMANT FILTER:

1. When a type-28 module is created, or its WAVE knob (P2) changes, the patch picks the program for that wave.
2. It copies the program into that slot's program area and patches the slot-dependent addresses from a relocation list.
3. It then reloads the slot through Roland's own mute → send → unmute path. A repeat of the same wave doesn't reload.

Where things live:

| Item | Address or location |
|---|---|
| ARM code | `0x600874A0` |
| Wave table | `+0x500` (16 bytes per wave) |
| State | `+0x570` |
| Relocation lists | `+0x580` |
| Seven master programs | The space used by the TORCIDO personality (7,364 bytes), overflowing into the BITRAZER space. A SCOOPER never runs those; this is why the firmware is SCOOPER-only. |
| Per-slot program areas | `0x60081FFC + 0x5E0 × slot` |

Roland's RANGE table sits at `0x825C0`, inside slot 1's program area, so every program must fit in 1,476 bytes. Out-of-range WAVE values fall back to FM.

## ESC2 instruction format (what was decoded)

- **Records.** A program is a list of records. The record header's low 5 bits give its length. The header's highest set bit gives the number of micro-op words:

  | Highest bit | Micro-ops |
  |---|---|
  | 11 | 1 |
  | 12 | 2 |
  | 13 | 3 |
  | 14 | 4 |
  | 15 | `5 + ((H >> 6) & 3)` |

  The rest of the record is operand words. This holds for all 30,498 records in 422 Roland programs (AIRA, SYSTEM-1m, TR-8).
- **Moves.** `S RRR 1111 111k kkk0` loads or stores register RRR from or to operand k.
- **ALU micro-ops.** Bits [15:12] are the destination (bit 15 selects the alternate function), [11:8] the op, [7:6] source A, [5:4] the mode (immediate modes read a constant from the operand region), and [3:0] source B (bit 3 = negate or accumulate).

  | Op | Function | With bit 15 set |
  |---|---|---|
  | 4 | multiply | max |
  | 0 | move/load | min |
  | C | add | — |
  | E (`8ecc` etc.) | `rN − r(N+4)` | — |

  Extra operand words act as addends: `000N` adds rN, and `003B` adds the constant at byte B.
- **Constants.** A 16-, 24- or 32-bit constant is stored as `[sign][2-bit exponent][magnitude]` and means ±m·2^(4e − N), with N the bit width (16, 24 or 32). Examples: 1/100 = `0x028F5C29`, 10.0 = `0x4A000000`, 0.3 = `0x24CC`. `E000` = 0.0 and `E021` = 1.0 are fixed constant addresses.
- **Data memory is a delay line.** Address + 1 holds the value written to the address one sample earlier. Edge detectors and filters rely on this.
- **Hardware rules** (breaking them hangs the DSP):
  - At most 2 data-memory loads and 2 stores per instruction.
  - A program's last halfword must be 1 if its length is even, otherwise 0.
  - About 300 records per patch in total. Roland's own modules are cheaper per record, so six of the 152-record CRVCON load fine.

## How it was checked

- **Record shapes.** Every record of every wave in every slot has a header and micro-op combination that appears in Roland's own programs.
- **ARM emulation (Unicorn).** The patched ARM code was run in an emulator:
  - 588 wave transitions,
  - 450 saved-patch boot configurations,
  - 60 invalid WAVE values,
  - 36 CB round trips.

  The checks covered program bytes, sizes, stack and registers, loader call order and the RANGE table.
- **Untouched regions.** All 288 stock module programs and the boot/header region are byte-identical to the previous release.
- **v3.2 against v3.1.** v3.2 equals v3.1, the version tested on hardware, with exactly 13 constants swapped (1/120 → 1/100) and nothing else changed.
- **Hardware.** See [hardware-test.md](hardware-test.md).

## Versions

| Version | Changes |
|---|---|
| v1 | Six-wave selector. |
| v2 | Adds CB, with a separate trigger jack. |
| v3 | Stock SAW/SQR jack set. Superseded: too heavy. |
| v3.1 | Lighter adapter (about 5 records over v2) and the COLOR clamp. Hardware-tested. |
| v3.2 | FINE IN matches the stock scale (1.2 semitones per 1.0). This release. |
