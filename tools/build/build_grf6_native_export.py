"""Direct GRF6 gate via native DSP export: swap two reporting destinations.

Uses v3.3's button surrogate and original native ARM readback. The GRF6 producer
exports straight to A01A. The old report instead goes to unused A103. Effect
input201F is unchanged. Offline builder; hardware confirmation needed.
"""
import hashlib
import json
import struct
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
OLD = Path(r'C:\Users\admin\Documents\Codex\2026-09-23\c-users-admin-documents-codex-2026')
sys.path.insert(0, str(OLD / 'work/deps'))
sys.path.insert(0, str(OLD / 'repo/aira-modular-system-osc/tools/build'))
from repack_aira import unpack_record, pack_application, validate_outer, APP_RECORD, APP_END
import recplay_patch
from keystone import Ks, KS_ARCH_ARM, KS_MODE_THUMB
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_THUMB
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_LR, UC_ARM_REG_SP

def verify_threshold(app):
    cases = []
    for bank in (0, 1):
        for value in (-1.0, -0.1, -0.0, 0.0, 0.01, 0.24, 0.25, 0.49, 0.5, 1.0):
            u = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
            u.mem_map(0x60000000, 0xA0000); u.mem_write(0x60000000, app)
            u.mem_map(0x01000000, 0x10000)
            u.mem_write(0x01000300, app[0x91D90:0x91D90+0x9190])
            u.mem_map(0x40101000, 0x1000)
            u.mem_write(0x40101068 + bank*0x400, struct.pack('<f', value))
            u.mem_map(0x20000000, 0x1000)
            u.mem_write(0x20000000, struct.pack('<I', bank))
            u.reg_write(UC_ARM_REG_R0, 0x20000000)
            u.reg_write(UC_ARM_REG_SP, 0x20000F00)
            u.reg_write(UC_ARM_REG_LR, 0x20000101)
            u.emu_start(0x6001112B, 0x20000100, count=100)
            actual = u.reg_read(UC_ARM_REG_R0)
            assert actual == int(value >= 0.25), (bank, value, actual)
            cases.append({'bank': bank, 'gate_value': value, 'pressed': bool(actual)})
    return cases

def main():
    base = (ROOT / 'outputs/recplay-grf1/rollback-v32/AIRA_MODULAR_UPD.BIN').read_bytes()
    v33 = (OLD / 'outputs/wave-selector-v33-recplay/firmware/AIRA_MODULAR_UPD.BIN').read_bytes()
    assert hashlib.sha256(v33).hexdigest() == '4ba0061925a86ba3806a601f58f57da351c7b41e8ed7b7c49ee09c56bfbca139'
    original, _ = unpack_record(v33, APP_RECORD, APP_END)
    app = bytearray(original)
    descriptor = struct.unpack_from('<3I', app, 0x6CA88)
    assert descriptor == (0x604, 0x6A, 0x6006C9C8)
    dest, length, source = descriptor
    source -= 0x60000000
    offset = lambda logical: source + ((logical - dest) ^ 2)
    words = lambda addr, count: [struct.unpack_from('<H', app, offset(addr+2*i))[0] for i in range(count)]
    assert words(0x644, 5) == [0x1E05, 0x0FE0, 0x1FE2, 0x201F, 0xA01A]
    assert words(0x65E, 3) == [0x0C03, 0x9FE0, 0xA01A]
    assert words(0x64E, 3) == [0x0C03, 0x2FE0, 0xA01B]
    # Confirm A103's upstream native producer still exists, byte-identical.
    assert struct.unpack_from('<3I', app, 0x6CAA0) == (0x140, 0x4C4, 0x6006C504)
    upoff = lambda addr: 0x6C504 + ((addr - 0x140) ^ 2)
    upstream = [struct.unpack_from('<H', app, upoff(0x29C+2*i))[0] for i in range(7)]
    assert upstream == [0x5F07, 0x0405, 0x3CC1, 0x6FE0, 0xAFE2, 0xC002, 0xA103]
    gate_store = upoff(0x2A8)
    old_report_store = offset(0x662)
    assert gate_store == 0x6C66E and old_report_store == 0x6CA24
    assert struct.unpack_from('<H', app, gate_store)[0] == 0xA103
    assert struct.unpack_from('<H', app, old_report_store)[0] == 0xA01A
    struct.pack_into('<H', app, gate_store, 0xA01A)
    struct.pack_into('<H', app, old_report_store, 0xA103)
    # GRF6's measured gate is approximately0.5 on the stock FINE scale.
    # Compare native scalar IEEE bits against positive0.25. Signed comparison
    # rejects negative values; this avoids a near-zero negative reading looking pressed.
    ks = Ks(KS_ARCH_ARM, KS_MODE_THUMB)
    tail = bytes(ks.asm('cmp.w r0, #0x3e800000; ite ge; movge r0, #1; movlt r0, #0; pop {r4, pc}', 0x60011138)[0])
    assert len(tail) <= 14 and len(tail) % 2 == 0
    app[0x11138:0x11146] = tail + b'\x00\xbf' * ((14-len(tail))//2)
    app = bytes(app)
    diff = [i for i,(x,y) in enumerate(zip(original,app)) if x != y]
    allowed = set(range(0x11138,0x11146)) | {0x6C66E,0x6C66F,0x6CA24,0x6CA25}
    assert all(i in allowed for i in diff)
    # Apart from the threshold tail, ARM code and physical-button handling
    # remain identical to v3.3. Only the two listed DSP operands change.
    assert app[0x1110E:0x11138] == original[0x1110E:0x11138]
    assert app[0x9A0F4:0x9A126] == original[0x9A0F4:0x9A126]
    button_cases = recplay_patch.emulate(app)
    threshold_cases = verify_threshold(app)
    image = pack_application(base, app)
    decoded, record = unpack_record(image, APP_RECORD, APP_END)
    assert decoded == app and pack_application(base, decoded) == image
    outer = validate_outer(image, base)
    out = ROOT / 'outputs/recplay-grf6-native-direct'
    out.mkdir(parents=True, exist_ok=True)
    (out / 'AIRA_MODULAR_UPD.BIN').write_bytes(image)
    manifest = {'status': 'DIRECT GRF6 CANDIDATE; hardware test pending',
        'sha256': hashlib.sha256(image).hexdigest(), 'basis': 'v3.3 with stock native ARM DSP readback',
        'patches': [
            {'program_descriptor': '0x6006CAA0', 'logical_address': '0x2A8',
             'application_offset': hex(gate_store), 'old': '0xA103', 'new': '0xA01A'},
            {'program_descriptor': '0x6006CA88', 'logical_address': '0x662',
             'application_offset': hex(old_report_store), 'old': '0xA01A', 'new': '0xA103'}],
        'changed_application_bytes_from_v33': len(diff), 'button_emulation_cases': len(button_cases),
        'positive_gate_threshold': 0.25, 'threshold_emulation_cases': threshold_cases,
        'intent': 'GRF6 stream producer writes directly to A01A readback. Old201F report writes to unused A103 stream. Actual effect input201F is untouched.',
        'routing': 'Physical KeyStep gate intoGRF6. No Customizer routes fromGRF6 at all.',
        'independence': 'Physical button GPIO handling retained. Separate SYNC TRIG input remains routed normally. Must verify both on hardware.',
        'limits': 'DSP execution is not emulated. The former GRF6 Customizer streamA103 now carries the old switch report; user requested no GRF6 routes. Producer gate behavior must be validated by two-pulse loop timing, hold-to-delete and physical SCATTER tests.',
        'record': record, 'outer': outer}
    (out / 'MANIFEST.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(json.dumps({'output': str(out), 'sha256': manifest['sha256'], 'changed_bytes': len(diff), 'button_cases': len(button_cases)}, indent=2))

if __name__ == '__main__':
    main()
