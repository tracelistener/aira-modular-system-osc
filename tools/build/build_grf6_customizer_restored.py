"""Restore native bulk Customizer access in the tested independent image.

Offline only. No MIDI, audio, hardware access, or automatic firmware flashing.
The tested gate/button/LED implementation is preserved byte for byte.
"""
import hashlib
import json
import shutil
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OLD = Path(r'C:\Users\admin\Documents\Codex\2026-09-23\c-users-admin-documents-codex-2026')
sys.path.insert(0, str(OLD / 'repo/aira-modular-system-osc/tools/build'))
from repack_aira import (
    unpack_record, pack_application, validate_outer, APP_RECORD, APP_END,
)

B = 0x60000000
TABLE, COUNT, STRIDE = 0x6857C, 44, 24
TELEMETRY = (0x88260, 0x88270)
SOURCE = ROOT / 'outputs/recplay-grf6-independent'
NATIVE = ROOT / 'outputs/recplay-grf6-native-direct'
OUT = ROOT / 'outputs/recplay-grf6-customizer-restored'
SOURCE_SHA = '0b931c6624732b10b4cb0ab12304652ac7bc3600d240f3663bc0bad854f96dc4'
NATIVE_SHA = 'cedf579af87c712affab8b37836cdf66dafb0cc6fafbbc58f53482ec93656b00'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verify_native_bulk(app, native):
    """Concrete native table/callback regression checks, with no live calls."""
    rows = []
    for n in range(COUNT):
        off = TABLE + n * STRIDE
        address, width, setter, getter, context, pid = struct.unpack_from('<6I', app, off)
        assert app[off:off + STRIDE] == native[off:off + STRIDE], n
        expected_address = bytes((0x10, 0x21, (3*n) // 128, (3*n) % 128))
        assert struct.pack('<I', address) == expected_address, n
        assert (width, setter, getter, context, pid) == (
            3, 0x60003F89, 0x60003F97, 4, 0xAA+n,
        ), n
        assert setter & 1 and getter & 1, 'native callbacks must enter Thumb code'
        assert all(v < 128 for v in expected_address), 'address is not MIDI-safe'
        rows.append({
            'parameter_id': hex(pid), 'address': list(expected_address), 'width': width,
            'setter': hex(setter), 'getter': hex(getter), 'context': context,
        })

    # Verify both the native callback implementation and its downstream target.
    # 03F88: UBFX r2,r2,#0,#17; UXTH r1,r1; UXTB r0,r0; B 03A84.
    # 03F96: UXTH r1,r1; UXTB r0,r0; B.W 04328.
    setter_bytes = bytes.fromhex('c2f3100289b2c0b278e5')
    getter_bytes = bytes.fromhex('89b2c0b200f0c5b9')
    assert app[0x3F88:0x3F92] == native[0x3F88:0x3F92] == setter_bytes
    assert app[0x3F96:0x3F9E] == native[0x3F96:0x3F9E] == getter_bytes
    assert app[0x3A84:0x3AC4] == native[0x3A84:0x3AC4]
    assert app[0x4328:0x4346] == native[0x4328:0x4346]
    assert len({tuple(row['address']) for row in rows}) == COUNT
    assert {row['parameter_id'] for row in rows} == {hex(n) for n in range(0xAA, 0xD6)}
    return {
        'passed': True,
        'kind': 'exact native table and callback machine-code checks',
        'rows_checked': COUNT,
        'native_getter': '60003F96 -> 60004328, area4 and PIDAA..D5',
        'native_setter': '60003F88 -> 60003A84, native 17-bit value mask',
        'diagnostic_contexts_removed': True,
        'read_only_noop_setters_removed': True,
        'rows': rows,
    }


def main():
    seed = (SOURCE / 'AIRA_MODULAR_UPD.BIN').read_bytes()
    native_fw = (NATIVE / 'AIRA_MODULAR_UPD.BIN').read_bytes()
    assert sha(seed) == SOURCE_SHA, 'unexpected tested independent source'
    assert sha(native_fw) == NATIVE_SHA, 'unexpected native descriptor source'
    source_manifest = json.loads((SOURCE / 'MANIFEST.json').read_text())
    assert source_manifest['sha256'] == SOURCE_SHA
    original, _ = unpack_record(seed, APP_RECORD, APP_END)
    native, _ = unpack_record(native_fw, APP_RECORD, APP_END)
    assert len(native) == len(original)

    app = bytearray(original)
    ranges = ((TABLE, TABLE + COUNT * STRIDE), TELEMETRY)
    for start, end in ranges:
        app[start:end] = native[start:end]
    app = bytes(app)
    allowed = set()
    for start, end in ranges:
        allowed.update(range(start, end))
        assert app[start:end] == native[start:end]
    changed = [n for n, (a, b) in enumerate(zip(original, app)) if a != b]
    assert changed and all(n in allowed for n in changed)
    # This equality is stronger than checking selected gate snippets: every
    # byte outside the two explicitly restored ranges stays identical.
    preserved = bytearray(app)
    for start, end in ranges:
        preserved[start:end] = original[start:end]
    assert bytes(preserved) == original

    native_checks = verify_native_bulk(app, native)
    retained_patches = []
    for patch in source_manifest['patches']:
        start = int(patch['address'], 16) - B
        end = start + patch['length']
        if any(start < hi and end > lo for lo, hi in ranges):
            assert TABLE <= start and end <= TABLE + COUNT * STRIDE, patch
            continue
        assert app[start:end] == original[start:end], patch
        retained_patches.append(patch)
    assert {int(p['address'], 16) for p in retained_patches} >= {
        B+0x25C, B+0xAA90, B+0x11138, B+0x88280,
        B+0x88380, B+0x88480, B+0x88C00,
    }

    firmware = pack_application(seed, app)
    decoded, record = unpack_record(firmware, APP_RECORD, APP_END)
    assert decoded == app
    assert pack_application(seed, decoded) == firmware
    outer = validate_outer(firmware, seed)
    result = {
        'status': 'OFFLINE VERIFIED: native bulk Customizer access restored; gate/button/LED code exactly matches hardware-tested independent source',
        'sha256': sha(firmware),
        'application_sha256': sha(app),
        'source_sha256': SOURCE_SHA,
        'native_descriptor_source_sha256': NATIVE_SHA,
        'application_bytes_changed': len(changed),
        'restored_ranges': [
            {'start': hex(B+lo), 'end_exclusive': hex(B+hi), 'length': hi-lo}
            for lo, hi in ranges
        ],
        'every_other_application_byte_preserved': True,
        'preserved_independent_patches': retained_patches,
        'native_bulk_checks': native_checks,
        'container_roundtrip_passed': True,
        'source_hardware_status': source_manifest['status'],
        'package_hardware_status': 'This restored package has not been flashed or hardware-tested by this builder.',
        'routing': source_manifest['routing'],
        'thresholds': source_manifest['thresholds'],
        'guard': source_manifest['guard'],
        'limits': [
            'Gate thresholds retain the calibration for this SCOOPER and measured KeyStep connection.',
            'A gate pulse entirely inside the 20 ms SCATTER transition guard can be missed.',
            'Special boot/button combinations have not been hardware-tested.',
        ],
        'record': record,
        'outer': outer,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'AIRA_MODULAR_UPD.BIN').write_bytes(firmware)
    (OUT / 'application.bin').write_bytes(app)
    (OUT / 'MANIFEST.json').write_text(json.dumps(result, indent=2)+'\n')
    (OUT / 'README.txt').write_text('''GRF6 REC/PLAY, independent SCATTER, native Customizer access restored

KeyStep GATE connects directly to GRF6. Keep GRF6 Customizer routes empty.
GRF6 controls REC/PLAY, including the native hold-to-clear behavior.
The physical SCATTER button toggles SCATTER; its lamp follows the effect.

This package restores all 44 original bulk Customizer descriptors and removes
the unused diagnostic getter. Native bulk patch reads and writes are restored.
The tested gate, physical-button, lamp, DSP and wave-selector code is unchanged.
Every other application byte matches the hardware-tested independent image.

Offline verification passed: all 44 native table rows and callback code,
allowlisted differences, firmware compression roundtrip and updater envelope.
The restored package itself has not yet been tested on hardware.

The gate thresholds retain the calibration for this unit and KeyStep connection.
A gate pulse entirely within the 20 ms SCATTER transition guard can be missed.
Use the usual firmware update procedure with buttons released during startup.

SHA256: '''+result['sha256']+'\n')
    shutil.copy2(Path(__file__).resolve(), OUT / Path(__file__).name)
    print(json.dumps({
        'output': str(OUT), 'sha256': result['sha256'],
        'application_bytes_changed': len(changed),
        'native_bulk_rows_verified': COUNT,
        'other_application_bytes_preserved': True,
        'container_roundtrip_passed': True,
    }, indent=2))


if __name__ == '__main__':
    main()
