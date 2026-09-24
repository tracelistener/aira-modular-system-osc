# Tools

These are the scripts that built and tested this firmware, copied as they were used. They're research code, not a one-command build:

- File paths are hard-coded to the original workspace.
- The build chain also reads earlier intermediate images.
- The build needs Roland's official firmware files, which aren't included: AIRA Modular system program 1.05 and SYSTEM-1m 1.30.

Python 3.12 with `numpy`. Some scripts also need `unicorn`, `scipy`, `Pillow` or `mido`.

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

## live/

These scripts drive the SCOOPER over USB. They save and restore the patch on the unit, and they need the Customizer to be closed.

| Script | Purpose |
|---|---|
| `aira_live.py` | SysEx patch read/write with read-back, notes, and WinMM capture of OUTPUT 1-2. |
| `v31_hw_test.py`, `v31_hw_test2.py` | The two hardware test passes in [../docs/hardware-test.md](../docs/hardware-test.md). |
| `analyze_captures.py` | Precise offline re-analysis of the captures. |
| `v32_check_and_restore.py` | v3.2 FINE IN check, plus the safe restore. Safe restore empties the patch, waits, then rebuilds it; it never overwrites slots in place. |
