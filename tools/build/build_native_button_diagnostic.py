"""Read-only button/gate telemetry on the otherwise unchanged native-direct image."""
import hashlib
import json
import shutil
import struct
from pathlib import Path
import build_grf6_telemetry as t

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT/'outputs/recplay-grf6-button-diagnostic'
FN = 0x60088260
END = FN+16
TARGETS = [
    ('gpio_port',0x4002D034), ('signature',0x60011428),
    ('flag3',0x6008DB40), ('flag4_recplay',0x6008DB44),
    ('gate_sample',0x40101068), ('old_report',0x4010140C),
] + [(f'usb_scalar_{n}',0x40101000+4*n) for n in range(10)] + [
    ('work0_9',0x40140024), ('work1_9',0x40144024),
    ('ui_state',0x6009B3E0), ('report24',0x40101060),
    ('enable25',0x40101064), ('enable27',0x4010106C),
]
assert len(TARGETS)==22

def main():
    baseline=ROOT/'outputs/recplay-grf6-native-direct/AIRA_MODULAR_UPD.BIN'
    seed=baseline.read_bytes()
    assert hashlib.sha256(seed).hexdigest()=='cedf579af87c712affab8b37836cdf66dafb0cc6fafbbc58f53482ec93656b00'
    original,_=t.unpack_record(seed,t.APP_RECORD,t.APP_END)
    # This region is inside the retired Bitrazer pool, after all live v3.2
    # selector code, state, tables and relocations. No wave master occupies it.
    layout=json.loads((t.OLD/'outputs/wave-selector-v32-inputs/evidence/build.json').read_text())
    assert int(layout['pools']['bitrazer_masters_end'],16)==0x60088254
    assert int(layout['pools']['bitrazer_end'],16)==0x60088D3E
    assert 0x60088254 <= FN < END <= 0x60088D3E
    assert all(w['pool']=='torcido' for w in layout['waves'])
    app=bytearray(original)
    code=bytes(t.Ks(t.KS_ARCH_ARM,t.KS_MODE_THUMB).asm(t.ASM,FN)[0])
    assert len(code)==14
    app[FN-t.B:END-t.B]=code+b'\x00\xbf'
    allowed=set(range(FN-t.B,END-t.B))
    queries=[]
    for n,(label,pointer) in enumerate(TARGETS):
        addresses=[]
        for chunk in (0,1):
            row=t.TABLE+(2*n+chunk)*24
            address,width,setter,getter,context,pid=struct.unpack_from('<6I',original,row)
            assert (width,setter,getter,context,pid)==(3,0x60003F89,0x60003F97,4,0xAA+2*n+chunk)
            struct.pack_into('<III',app,row+8,(FN+10)|1,FN|1,pointer)
            allowed.update(range(row+8,row+20))
            addresses.append(list(struct.pack('<I',address)))
        queries.append({'label':label,'pointer':hex(pointer),'rq1_low':addresses[0],'rq1_high':addresses[1]})
    app=bytes(app)
    changed=[i for i,(a,b) in enumerate(zip(original,app)) if a!=b]
    assert all(i in allowed for i in changed)
    for lo,hi in ((0x1110E,0x11146),(0x12230,0x12278),(0x9A0F4,0x9A126),(0x6C504,0x6CA2E)):
        assert app[lo:hi]==original[lo:hi]
    t.FN=FN
    t.SETTER=FN+10
    cases=t.verify(app)
    fw=t.pack_application(seed,app)
    decoded,record=t.unpack_record(fw,t.APP_RECORD,t.APP_END)
    assert decoded==app and t.pack_application(seed,decoded)==fw
    outer=t.validate_outer(fw,seed)
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'AIRA_MODULAR_UPD.BIN').write_bytes(fw)
    result={'status':'DIAGNOSTIC: existing GRF6 recording behavior retained; SCATTER independence is not fixed yet',
        'sha256':hashlib.sha256(fw).hexdigest(),'baseline_sha256':hashlib.sha256(seed).hexdigest(),
        'queries':queries,'get_set_cases':cases,'application_bytes_changed':len(changed),
        'preserved':'All existing button, gate, DSP processing, updater code and ordinary individual patch controls',
        'changed':'Read-only fixed-address telemetry via legacy bulk descriptors AA..D5; their setters become no-ops',
        'code_pool':{'first_free':'0x60088254','used_start':hex(FN),'used_end':hex(END),'pool_end':'0x60088D3E'},
        'limits':'Legacy bulk cable reads expose telemetry, bulk writes ignored. Individual cable/module operations remain available. Hardware telemetry pending.',
        'record':record,'outer':outer}
    (OUT/'MANIFEST.json').write_text(json.dumps(result,indent=2)+'\n')
    (OUT/'README.txt').write_text('''SCATTER / GRF6 diagnostic image

This is a diagnostic, not a completed fix. The previous GRF6 REC/PLAY behavior
is unchanged. It adds fixed read-only USB queries so Codex can measure the
physical button pins and the internal gate value while you press SCATTER.

Flash normally, leave KeyStep GATE in GRF6, leave all GRF6 routes empty, and tell
Codex when ready. The next test compares the gate alone and SCATTER alone.
Do not press buttons during startup; use the usual update procedure.

The boot updater and ordinary individual patch controls are preserved. Legacy
bulk cable queries are temporarily used for telemetry; bulk cable writes are
ignored. The current image's SCATTER coupling remains until diagnosed/fixed.

SHA256: '''+result['sha256']+'\n')
    print(json.dumps({'output':str(OUT),'sha256':result['sha256'],'cases':cases,'unchanged_gate_and_button_code':True},indent=2))

if __name__=='__main__':
    main()
