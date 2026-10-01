"""Fixed-address read-only telemetry through the legacy bulk RQ1 descriptors.

Diagnostic only: based on v3.2, no synthetic REC/PLAY input. Does not flash.
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
from keystone import Ks, KS_ARCH_ARM, KS_MODE_THUMB
from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_THUMB, UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_LR, UC_ARM_REG_SP
from repack_aira import unpack_record, pack_application, validate_outer, APP_RECORD, APP_END

B, FN, END = 0x60000000, 0x6001112A, 0x60011146
SETTER = FN + 10
TABLE = 0x6857C
TARGETS = [('gpio_port', 0x4002D034), ('signature', 0x60011428)]
for index in (41, 40, 0x103, 0x102):
    for bank, base in ((0, 0x40140000), (1, 0x40160000)):
        for plane in (0, 1):
            TARGETS.append((f'work_b{bank}_p{plane}_{index:03x}', base + plane * 0x4000 + index * 4))
TARGETS += [('C_b1_41_data', 0x4016C294), ('C_b1_41_mirror', 0x4016C298),
            ('scalar_b1_3', 0x4010140C), ('scalar_b0_26', 0x40101068)]
assert len(TARGETS) == 22

ASM = '''
ldr r0, [r0]
lsls r1, r1, #31
bpl low
lsrs r0, r0, #21
low:
bx lr
movs r0, #0
bx lr
'''

def verify(app):
    cases = 0
    for sample in (0, 1, 0x3F800000, 0x40000000, 0x80000000, 0xDEADBEEF, 0xFFFFFFFF):
        for chunk in (0, 1):
            u = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
            u.mem_map(B, 0xA0000); u.mem_write(B, app)
            u.mem_map(0x20000000, 0x1000)
            u.mem_map(0x40160000, 0x1000)
            u.mem_write(0x401600A4, struct.pack('<I', sample))
            writes = []
            u.hook_add(UC_HOOK_MEM_WRITE, lambda uc, access, addr, size, data, user: writes.append((addr, data)))
            u.reg_write(UC_ARM_REG_R0, 0x401600A4)
            u.reg_write(UC_ARM_REG_R1, 0xAA + chunk)
            u.reg_write(UC_ARM_REG_LR, 0x20000101)
            u.reg_write(UC_ARM_REG_SP, 0x20000F00)
            u.emu_start(FN | 1, 0x20000100, count=20)
            result = u.reg_read(UC_ARM_REG_R0)
            assert result == (sample if not chunk else sample >> 21)
            assert not writes
            packet = [(result >> shift) & 127 for shift in (14, 7, 0)]
            recovered = (packet[0] << 14) | (packet[1] << 7) | packet[2]
            assert recovered == ((sample & 0x1FFFFF) if not chunk else sample >> 21)
            # Repurposed bulk setters are explicit no-ops even with a pointer context.
            u.reg_write(UC_ARM_REG_R0, 0x401600A4)
            u.reg_write(UC_ARM_REG_LR, 0x20000101)
            u.emu_start(SETTER | 1, 0x20000100, count=10)
            assert u.reg_read(UC_ARM_REG_R0) == 0 and not writes
            cases += 1
    return cases

def main():
    base = (ROOT / 'outputs/recplay-grf1/rollback-v32/AIRA_MODULAR_UPD.BIN').read_bytes()
    assert hashlib.sha256(base).hexdigest() == '03f4f5f8221092dba6aacaa33c98ba1cc1eddeaf96ae254759388ce5460f51a9'
    old, _ = unpack_record(base, APP_RECORD, APP_END)
    app = bytearray(old)
    ks = Ks(KS_ARCH_ARM, KS_MODE_THUMB)
    code = bytes(ks.asm(ASM, FN)[0])
    assert len(code) == 14
    md = Cs(CS_ARCH_ARM, CS_MODE_THUMB)
    prior = list(md.disasm(old[0x1223C:0x12240], B + 0x1223C))
    assert len(prior) == 1 and prior[0].mnemonic == 'bl' and prior[0].op_str == '#0x6001112a'
    app[0x1223C:0x12240] = bytes(ks.asm('movs r0, #0; nop', B + 0x1223C)[0])
    app[FN-B:END-B] = code + b'\x00\xbf' * ((END-FN-len(code)) // 2)
    requests = []
    changed_allowed = set(range(FN-B, END-B)) | set(range(0x1223C, 0x12240))
    for n, (label, pointer) in enumerate(TARGETS):
        pair = []
        for chunk in (0, 1):
            row = TABLE + (2*n + chunk)*24
            address, width, setter, getter, context, parameter = struct.unpack_from('<6I', old, row)
            assert width == 3 and getter == 0x60003F97 and setter == 0x60003F89
            assert context == 4 and parameter == 0xAA + 2*n + chunk
            struct.pack_into('<III', app, row+8, SETTER | 1, FN | 1, pointer)
            changed_allowed.update(range(row+8, row+20))
            pair.append(list(struct.pack('<I', address)))
        requests.append({'label': label, 'pointer': hex(pointer), 'rq1_low': pair[0], 'rq1_high': pair[1]})
    app = bytes(app)
    changed = [i for i,(x,y) in enumerate(zip(old,app)) if x != y]
    assert all(i in changed_allowed for i in changed)
    assert app[0x9A0F4:0x9A126] == old[0x9A0F4:0x9A126], 'physical button gatherer must be stock v3.2'
    count = verify(app)
    image = pack_application(base, app)
    decoded, record = unpack_record(image, APP_RECORD, APP_END)
    assert decoded == app and pack_application(base, decoded) == image
    outer = validate_outer(image, base)
    out = ROOT / 'outputs/recplay-grf6-telemetry'
    out.mkdir(parents=True, exist_ok=True)
    (out / 'AIRA_MODULAR_UPD.BIN').write_bytes(image)
    manifest = {'status': 'READ-ONLY DIAGNOSTIC; DOES NOT IMPLEMENT GATE REC/PLAY',
        'sha256': hashlib.sha256(image).hexdigest(), 'base': 'tested v3.2',
        'queries': requests, 'offline_getter_setter_cases': count,
        'application_bytes_changed': len(changed),
        'patch_regions': ['0x6001112A..0x60011146 telemetry and no-op setter',
                          '0x6001223C periodic read replaced by zero', '44 legacy bulk descriptor callback/context triples'],
        'compatibility': 'Legacy bulk-cable RQ1 reads become telemetry; corresponding DT1 writes ignored. Individual cable and module controls retain their original descriptors.',
        'limits': 'Addresses are fixed native readable apertures. Relationship to the raw GRF6 gate remains to be measured. No arbitrary address reads or writes are exposed.',
        'record': record, 'outer': outer}
    (out / 'MANIFEST.json').write_text(json.dumps(manifest, indent=2)+'\n')
    (out / 'telemetry-disassembly.txt').write_text('\n'.join(f'{x.address:08x} {x.mnemonic} {x.op_str}'for x in md.disasm(code,FN))+'\n')
    print(json.dumps({'output': str(out), 'sha256': manifest['sha256'], 'read_only_cases': count, 'queries': len(requests)}, indent=2))

if __name__ == '__main__':
    main()
