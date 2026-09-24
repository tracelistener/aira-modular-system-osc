"""Package v3.2 = the hardware-tested v3.1 with the stock FINE IN scale (one constant, 13 sites). No device I/O.

outputs/wave-selector-v32-inputs/
  firmware/AIRA_MODULAR_UPD.BIN        v3.2
  rollback-v31/, rollback-v2/, rollback-v1/
  presets/                             v3.1 presets; SYNC_DEMO's stock SAW FINE 50 -> 61 (the stock SAW runs 10.6 cents flat)
  evidence/, source/
The Customizer needs no change (the installed v3.1 panel and menu are correct for v3.2).
"""
import shutil, json
from build_wave_selector_v32 import *

V31_OUT = ROOT / 'outputs/wave-selector-v31-inputs'
V31_FW_SHA = '192d0cfce81befb560077d7ce190a742ab6665c423a790b6296c2263d487f040'
V31_APP = ROOT / 'work/selector-v31/application.bin'
OLDC, NEWC = (0x02222222).to_bytes(4, 'little'), (0x028F5C29).to_bytes(4, 'little')   # 1/120 -> 1/100
HW = V31_OUT / 'hw-test'


def fine_sites(a31, app):
    sites, p = [], a31.find(OLDC)
    while p >= 0:
        if app[p:p + 4] == NEWC:
            sites.append(p)
        p = a31.find(OLDC, p + 1)
    c = bytearray(a31)
    for s in sites:
        c[s:s + 4] = NEWC
    assert bytes(c) == app, 'v3.2 differs from v3.1 by more than the FINE constant'
    return sites


def package():
    app, fw, meta = build()
    from verify_wave_selector_v32 import verify
    meta['verification'] = verify()
    sites = fine_sites(V31_APP.read_bytes(), app)
    areas = [0x81ffc + 0x5e0 * s for s in range(6)]
    assert len(sites) == 13 and [s - a for s, a in zip(sites[:6], areas)] == [92] * 6
    image = pack_application(fw, app)
    decoded, record = unpack_record(image, APP_RECORD, APP_END)
    assert decoded == app and pack_application(fw, decoded) == image
    v31fw = (V31_OUT / 'firmware/AIRA_MODULAR_UPD.BIN').read_bytes()
    v2fw, v1fw = V2_FW.read_bytes(), V1_FW.read_bytes()
    assert sha(v31fw) == V31_FW_SHA and sha(v2fw) == V2_FW_SHA and sha(v1fw) == V1_FW_SHA
    assert image[:0x40000] == v31fw[:0x40000]
    meta.update(status='OFFLINE CHECKS PASSED; v3.1 BASE HARDWARE-TESTED 2026-09-24; v3.2 CONSTANT CHANGE NOT YET FLASHED',
                firmware_sha256=sha(image), record=record, outer=validate_outer(image, fw),
                diff_vs_v31=dict(application_sites=[hex(s) for s in sites], old='0x02222222 (1/120)', new='0x028F5C29 (1/100)',
                                 meaning='FINE IN: 1.0 = 0.1 octave (120 cents), the stock SAW/SQR scale; v3.1 gave 100 cents'))
    for d in ['firmware', 'rollback-v31', 'rollback-v2', 'rollback-v1', 'presets', 'evidence', 'source']:
        (OUT / d).mkdir(parents=True, exist_ok=True)
    (OUT / 'firmware/AIRA_MODULAR_UPD.BIN').write_bytes(image)
    (OUT / 'rollback-v31/AIRA_MODULAR_UPD.BIN').write_bytes(v31fw)
    (OUT / 'rollback-v2/AIRA_MODULAR_UPD.BIN').write_bytes(v2fw)
    (OUT / 'rollback-v1/AIRA_MODULAR_UPD.BIN').write_bytes(v1fw)
    plist = []
    for p in sorted((V31_OUT / 'presets').glob('*.bin')):
        b = bytearray(p.read_bytes())
        src = 'v3.1 (unchanged)'
        if p.name == 'VOICE_S1M_SYNC_DEMO.bin':
            assert list(b[64:69]) == [29, 1, 50, 0, 50]
            b[66] = 61                      # stock SAW FINE: +11 steps ~ +10.9 cents (measured SAW offset -10.6 cents)
            src = 'v3.1 preset, sync master SAW FINE 50 -> 61 so the synced voice plays in tune'
        (OUT / 'presets' / p.name).write_bytes(bytes(b))
        plist.append(dict(file=p.name, source=src, sha256=sha(bytes(b))))
    (OUT / 'presets/VALIDATION.json').write_text(json.dumps(plist, indent=2))
    shutil.copy2(HERE / 'verification.json', OUT / 'evidence/selector-verification.json')
    shutil.copy2(HERE / 'build.json', OUT / 'evidence/build.json')
    for n in ('results.json', 'results_pass2.json'):
        shutil.copy2(HW / n, OUT / 'evidence' / ('v31-hardware-' + n))
    live = ROOT / 'work/live-v31'
    for pth in list(HERE.iterdir()) + [ROOT / 'work/cowbell2' / n for n in (
            'system_osc_v3.py', 'system_osc_v31.py', 'system_osc_v32.py', 'cowbell_program.py', 'cb_model.py', 'isa.py', 'esc.py')] + \
            [live / n for n in ('v31_hw_test.py', 'v31_hw_test2.py', 'analyze_captures.py')]:
        if pth.suffix in ('.py', '.s', '.txt'):
            shutil.copy2(pth, OUT / 'source' / pth.name)
    meta['presets'] = plist
    meta['customizer'] = 'unchanged from v3.1 (outputs/wave-selector-v31-inputs/customizer, already installed)'
    (OUT / 'MANIFEST.json').write_text(json.dumps(meta, indent=2, default=str) + '\n')
    print('PACKAGED', sha(image), 'sites', len(sites))
    return meta


if __name__ == '__main__':
    package()
