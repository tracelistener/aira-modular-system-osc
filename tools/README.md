# Tools

These are the scripts that built and tested this firmware, copied as they were used. They're research code, not a one-command build:

- File paths are hard-coded to the original workspace.
- The build chain also reads earlier intermediate images.
- The build needs Roland's official firmware files, which aren't included: AIRA Modular system program 1.05 and SYSTEM-1m 1.30.

Python 3.12 with `numpy`. Some scripts also need `unicorn`, `keystone-engine`, `capstone`, `scipy`, `Pillow` or `mido`.

## build/

| Script | Purpose |
|---|---|
| `system_osc_v32.py` | Builds one wave program for one slot: the SYSTEM-1m cell, renamed to slot addresses, with the pitch/RANGE/COLOR/SYNC adapter. |
| `system_osc_v31.py`, `system_osc_v3.py` | The earlier adapters it derives from (donor extraction, private data layout). |
| `make_v32_sources.py` | Derives the v3.2 sources from v3.1. The only change is the FINE IN constant. |
| `build_wave_selector_v32.py` | Places the seven master programs, the per-slot areas and the relocation lists into the application image. |
| `verify_wave_selector_v32.py` | Runs the patched ARM selector in Unicorn: wave changes, boot restores, invalid values, CB round trips. |
| `package_selector_v32.py` | Packs the image into the update container and asserts that v3.2 equals v3.1 plus the 13 constant changes. |
| `final_audit_v32.py` | Independent read-back audit of the packaged files. |
| `repack_aira.py`, `aira_lzss.py`, `decompress_aira_application.py` | The update container and its LZSS compression. |
| `next_system_interface.py`, `system_cell*_program.py` | Read the SYSTEM-1m firmware and lay out a cell for a SCOOPER slot. |
| `esc.py`, `isa.py`, `corpus.py`, `scan_programs.py`, `const.py` | ESC2 program parsing, instruction layout and the 422-program corpus scan. |
| `cowbell_program.py`, `verify_cowbell_program.py` | CB port (v2 design) and its checks. |
| `cb_model.py`, `plugout.py`, `code1.py`, `render_cb_plugout.py` | CB sound model transcribed from the SYSTEM-1 plug-out, and plug-out helpers. |
| `picker.py`, `package_selector_v31.py` | Customizer art: SYSTEM OSCILLATOR panel jacks and module-menu page, built from Roland's own glyphs. |
| `aira_preset.py` | Writes Customizer `.bin` patch files. |
| `recplay_patch.py` | The input routine shared by v3.3 and v3.5 (REC/PLAY = button OR gate): assembles it, places it, and emulates all 32 input cases. |
| `build_v33.py` | Builds v3.3 from v3.2 and checks that only the input routine changed. v3.3 has been removed from `firmware/`, but v3.5's first step reads its output. |
| `build_grf6_native_export.py` | v3.5, step 1: v3.2 plus the input routine; moves the GRF 6 DSP store to the register the gate reader uses. |
| `build_grf6_telemetry.py` | Container and assembler helpers used by the v3.5 builders. It also built a USB telemetry image for measurements. |
| `build_native_button_diagnostic.py` | Diagnostic image used to measure the button and gate levels. Its diagnostics borrow the Customizer's bulk commands. |
| `build_grf6_independent.py` | Adds the gate decoder, the SCATTER hook and the lamp change. |
| `build_grf6_customizer_restored.py` | v3.5, last step: gives the Customizer bulk commands back and removes the diagnostics. |
| `verify_grf6_independent.py`, `verify_grf6_button_hook.py` | Run the decoder, the SCATTER hook and the lamp code in Unicorn. |
| `verify_native_rec_debounce.py` | Runs Roland's own REC/PLAY debounce path in Unicorn. It shows why the decoder needs its 20 ms hold. |
| `armdis.py` | Small Thumb-2 disassembly and cross-reference helpers used to trace the button handling. |

## live/

These scripts drive the SCOOPER over USB. They save and restore the patch on the unit, and they need the Customizer to be closed.

| Script | Purpose |
|---|---|
| `aira_live.py` | SysEx patch read/write with read-back, notes, and WinMM capture of OUTPUT 1-2. |
| `v31_hw_test.py`, `v31_hw_test2.py` | The two hardware test passes in [../docs/hardware-test.md](../docs/hardware-test.md). |
| `analyze_captures.py` | Precise offline re-analysis of the captures. |
| `v32_check_and_restore.py` | v3.2 FINE IN check, plus the safe restore. Safe restore empties the patch, waits, then rebuilds it; it never overwrites slots in place. |
| `recplay_probe.py` | Sends 4,000+ MIDI messages to check whether anything already triggers REC/PLAY on stock firmware. Nothing did. |
| `recplay_watch.py` | Logs everything the unit sends while someone presses the real REC/PLAY button. |
| `v33_recplay_test.py` | v3.3 hardware test (historical): tap the gate to record and play, check the loop plays, hold the gate to delete. |
| `test_grf6_native_direct.py`, `test_grf6_native_short.py` | v3.5 audio test: KeyStep gates into GRF 6 record, play, mute and delete a loop. |
| `test_grf6_native_bulk.py` | Customizer bulk cable read/write round trip. |
| `scatter_press_check.py` | SCATTER press check: a tone feeds the looper while you press SCATTER, then the script listens for a loop. |
