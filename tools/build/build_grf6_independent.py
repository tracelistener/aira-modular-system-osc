"""Measured GRF6 / SCATTER separation; offline build, never flashes hardware."""
import hashlib
import json
import shutil
import struct
from pathlib import Path
import build_grf6_telemetry as t

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'outputs/recplay-grf6-independent'
B = 0x60000000
GATE_FN, BUTTON_FN, LED_FN, STATE = 0x60088280, 0x60088380, 0x60088480, 0x60088C00

GATE_ASM = f'''
    ldr r1, =0x4002d034
    ldr r1, [r1]
    ubfx r1, r1, #15, #1
    ldr r2, ={STATE}
    ldr r3, =0x01015188
    ldr r3, [r3]
    ldr r4, [r2]
    cmp r1, r4
    bne edge
    ldr r4, [r2, #4]
    subs r3, r3, r4
    cmp r3, #20
    blo retained
    cmp r1, #0
    beq pressed
    ldr r4, =0x3e800000
    b classify
pressed:
    ldr r4, =0x3f95c28f
classify:
    cmp r0, r4
    ite ge
    movge r0, #1
    movlt r0, #0
    str r0, [r2, #8]
    pop {{r4, pc}}
edge:
    str r1, [r2]
    str r3, [r2, #4]
retained:
    ldr r0, [r2, #8]
    pop {{r4, pc}}
'''

BUTTON_ASM = '''
    push {r0, r1, r4, lr}
    cmp r0, #2
    bne forward
    ldr r4, =0x60088c10
    cmp r1, #0
    bne check_press
    str r1, [r4]
    b forward
check_press:
    cmp r1, #1
    bne forward
    ldr r2, [r4]
    cmp r2, #0
    bne forward
    str r1, [r4]
    movs r0, #4
    movs r1, #0x69
    bl 0x60004328
    cmp r0, #0
    ite eq
    moveq r2, #1
    movne r2, #0
    movs r0, #4
    movs r1, #0x69
    bl 0x60003a84
    bl 0x6000aa72
forward:
    pop.w {r0, r1, r4, lr}
    push {r3, lr}
    cbz r1, released
    cmp r1, #1
    bne done
    movs r1, #2
emit:
    strb.w r1, [sp]
    strb.w r0, [sp, #1]
    mov r0, sp
    bl 0x6000081a
done:
    pop {r3, pc}
released:
    movs r1, #1
    b emit
'''

LED_ASM = '''
    push {r3, lr}
    movs r0, #4
    movs r1, #0x69
    bl 0x60004328
    pop {r3, pc}
'''

def main():
    source = ROOT/'outputs/recplay-grf6-button-diagnostic'
    seed = (source/'AIRA_MODULAR_UPD.BIN').read_bytes()
    assert hashlib.sha256(seed).hexdigest() == 'dc5716107c11027c84d98106e8324a3a3e22dd39563d6b540d5d8c99f62c619b'
    original, _ = t.unpack_record(seed, t.APP_RECORD, t.APP_END)
    layout = json.loads((t.OLD/'outputs/wave-selector-v32-inputs/evidence/build.json').read_text())
    assert int(layout['pools']['bitrazer_masters_end'],16) == 0x60088254
    assert int(layout['pools']['bitrazer_end'],16) == 0x60088D3E
    assert all(w['pool']=='torcido' for w in layout['waves'])
    app = bytearray(original)
    allowed, patches = set(), []
    ks = t.Ks(t.KS_ARCH_ARM, t.KS_MODE_THUMB)
    def patch(address, code, label):
        off = address-B
        assert 0 <= off < len(app) and off+len(code) <= len(app)
        app[off:off+len(code)] = code
        allowed.update(range(off,off+len(code)))
        patches.append({'address':hex(address),'length':len(code),'purpose':label})
    def asm(text, address):
        return bytes(ks.asm(text,address)[0])
    for address, end, sourcecode, label in (
        (GATE_FN, BUTTON_FN, GATE_ASM, 'GPIO-aware gate decoder with transition guard'),
        (BUTTON_FN, LED_FN, BUTTON_ASM, 'SCATTER parameter toggle and original event forwarding'),
        (LED_FN, STATE, LED_ASM, 'Read actual SCATTER parameter for lamp'),
    ):
        code = asm(sourcecode,address)
        assert address+len(code) <= end
        patch(address,code,label)
    assert STATE+20 <= 0x60088D3E
    patch(STATE, struct.pack('<5I',0xFFFFFFFF,0,0,0x494E4401,0),'Gate state, read-only image signature, SCATTER press latch')
    assert original[0x25C:0x260] == bytes.fromhex('08b551b1')
    branch = asm(f'b.w {BUTTON_FN}', B+0x25C)
    assert len(branch)==4
    patch(B+0x25C,branch,'Debounced physical button hook')
    assert original[0xAA90:0xAA96] == bytes.fromhex('ec4800940068')
    led = asm(f'str r4, [sp]; bl {LED_FN}',B+0xAA90)
    assert len(led)==6
    patch(B+0xAA90,led,'LED5 follows SCATTER effect state')
    tail = asm(f'b.w {GATE_FN}', B+0x11138)
    assert len(tail)==4
    patch(B+0x11138,tail+b'\x00\xbf'*5,'Native scalar read uses separated gate decoder')
    queries = json.loads((source/'MANIFEST.json').read_text())['queries']
    updates = {'signature':('signature',STATE+12),
        'usb_scalar_6':('native_clock',0x01015188),
        'usb_scalar_7':('decoded_button',STATE),
        'usb_scalar_8':('button_edge_tick',STATE+4),
        'usb_scalar_9':('decoded_gate',STATE+8)}
    for n,q in enumerate(queries):
        if q['label'] in updates:
            q['label'], pointer = updates[q['label']]
            q['pointer'] = hex(pointer)
            for chunk in (0,1):
                patch(B+t.TABLE+(2*n+chunk)*24+16,struct.pack('<I',pointer),'Fixed read-only diagnostic context')
    app = bytes(app)
    changed = [i for i,(x,y) in enumerate(zip(original,app)) if x!=y]
    assert all(i in allowed for i in changed)
    for lo,hi in ((0x6C504,0x6CA2E),(0x9A0F4,0x9A126),(0x12230,0x12278),(0x874A0,0x88254)):
        assert app[lo:hi] == original[lo:hi], (hex(lo),hex(hi))
    from verify_grf6_independent import verify_gate
    from verify_grf6_button_hook import verify_button
    gate_tests = verify_gate(app)
    button_tests = verify_button(app)
    t.FN, t.SETTER = 0x60088260, 0x6008826A
    telemetry_tests = t.verify(app)
    fw = t.pack_application(seed,app)
    decoded, record = t.unpack_record(fw,t.APP_RECORD,t.APP_END)
    assert decoded==app and t.pack_application(seed,decoded)==fw
    outer = t.validate_outer(fw,seed)
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'AIRA_MODULAR_UPD.BIN').write_bytes(fw)
    (OUT/'application.bin').write_bytes(app)
    result = {'status':'CANDIDATE: offline verification passed; hardware independence test pending',
        'sha256':hashlib.sha256(fw).hexdigest(),'source_sha256':hashlib.sha256(seed).hexdigest(),
        'application_bytes_changed':len(changed),'patches':patches,'queries':queries,
        'gate_tests':gate_tests,'button_tests':button_tests,'telemetry_cases':telemetry_tests,
        'thresholds':{'scatter_released':0.25,'scatter_held':1.17},
        'guard':{'ticks':20,'clock':'native SysTick lowword 0x01015188','units':'milliseconds inferred from native timing configuration and existing timeouts'},
        'routing':'KeyStep GATE directly into GRF6; all GRF6 Customizer routes empty',
        'limits':['This gate calibration is based on this unit and the measured KeyStep voltage.',
          'A gate pulse entirely inside the SCATTER transition guard can be missed.',
          'Legacy bulk cable descriptors remain read-only diagnostics; individual controls remain available.',
          'Shared special-mode handler reachability and behavior have not been established on SCOOPER.',
          'Special boot/button combinations have not been tested; original button events are forwarded.'],
        'record':record,'outer':outer}
    (OUT/'MANIFEST.json').write_text(json.dumps(result,indent=2)+'\n')
    (OUT/'README.txt').write_text('''GRF6 REC/PLAY with independent physical SCATTER -- candidate

Connect KeyStep GATE to physical GRF6. Leave ALL GRF6 Customizer routes empty.
GRF6 acts as REC/PLAY, including native hold-to-clear behavior. SCATTER toggles
the SCATTER effect and its lamp follows that effect. Hardware verification of
this combined behavior is still required after flashing.

This build separates the four measured gate/button levels using physical
GPIO15, with a 20-tick settling guard around button transitions. A gate pulse
entirely inside that short guard can be missed. Thresholds are calibrated to
the measured KeyStep connection on this unit.

All wave-selector code, native DSP export and REC/PLAY gatherer are preserved.
Read-only diagnostics temporarily replace legacy bulk cable queries/writes;
ordinary individual Customizer operations remain available.

Special button modes remain untested. A shared internal selection handler
was found, but its reachability on SCOOPER has not been established.

Flash using the usual procedure, with buttons released during normal startup.
Then tell Codex when the unit is back on for the recording and SCATTER tests.
SHA256: '''+result['sha256']+'\n')
    for name in ('build_grf6_independent.py','verify_grf6_independent.py','verify_grf6_button_hook.py'):
        shutil.copy2(ROOT/'work'/name, OUT/name)
    print(json.dumps({'output':str(OUT),'sha256':result['sha256'],'changed_bytes':len(changed),
        'gate_tests':gate_tests,'button_tests':button_tests},indent=2))

if __name__=='__main__':
    main()
