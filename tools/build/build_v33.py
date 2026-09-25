"""v3.3 = the flashed v3.2 + REC/PLAY from the SCATTER jack (see recplay_patch.py). Offline; no device I/O."""
import hashlib, json, shutil, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OLD = Path('C:/Users/admin/Documents/Codex/2026-09-22/files-mentioned-by-the-user-handoff')
sys.path[:0] = [str(ROOT / 'work/deps'), str(OLD / 'work'), str(HERE)]
from repack_aira import unpack_record, pack_application, validate_outer, APP_RECORD, APP_END
from recplay_patch import patch, emulate, FN, FN_END, B

sha = lambda b: hashlib.sha256(b).hexdigest()
V32 = ROOT / 'outputs/wave-selector-v32-inputs'
V31 = ROOT / 'outputs/wave-selector-v31-inputs'
OUT = ROOT / 'outputs/wave-selector-v33-recplay'
V32_SHA = '03f4f5f8221092dba6aacaa33c98ba1cc1eddeaf96ae254759388ce5460f51a9'

fw32 = (V32 / 'firmware/AIRA_MODULAR_UPD.BIN').read_bytes()
assert sha(fw32) == V32_SHA
app32, _ = unpack_record(fw32, APP_RECORD, APP_END)
assert app32 == (ROOT / 'work/selector-v32/application.bin').read_bytes()
app33, code = patch(app32)
cases = emulate(app33)
diff = [i for i in range(len(app32)) if app32[i] != app33[i]]
assert diff and B + min(diff) >= FN and B + max(diff) < FN_END, 'change must stay inside the input routine'
fw33 = pack_application(fw32, app33)
back, record = unpack_record(fw33, APP_RECORD, APP_END)
assert back == app33 and pack_application(fw32, back) == fw33
assert fw33[:0x40000] == fw32[:0x40000]
for d in ('firmware', 'rollback-v32', 'rollback-v31', 'presets', 'evidence', 'source'):
    (OUT / d).mkdir(parents=True, exist_ok=True)
(OUT / 'firmware/AIRA_MODULAR_UPD.BIN').write_bytes(fw33)
(OUT / 'rollback-v32/AIRA_MODULAR_UPD.BIN').write_bytes(fw32)
shutil.copy2(V31 / 'firmware/AIRA_MODULAR_UPD.BIN', OUT / 'rollback-v31/AIRA_MODULAR_UPD.BIN')
for p in (V32 / 'presets').glob('*.bin'):
    shutil.copy2(p, OUT / 'presets' / p.name)
for p in (HERE / 'recplay_patch.py', HERE / 'armdis.py', HERE / 'build_v33.py'):
    shutil.copy2(p, OUT / 'source' / p.name)
meta = dict(status='OFFLINE CHECKS PASSED; NOT FLASHED', base='v3.2 ' + V32_SHA,
            firmware_sha256=sha(fw33), application_sha256=sha(app33), record=record,
            outer=validate_outer(fw33, fw32),
            change=dict(routine=hex(FN), bytes_changed=len(diff), new_code_bytes=len(code),
                        behaviour='SCATTER CV input (GRF 6 jack by default) high = REC/PLAY held; SCATTER CV no longer '
                                  'toggles SCATTER; SYNC TRIG CV, REC/PLAY/GRF5/GRF6 buttons unchanged'),
            emulated_cases=len(cases))
(OUT / 'evidence/build.json').write_text(json.dumps(meta, indent=2, default=str) + '\n')
print(json.dumps({k: v for k, v in meta.items() if k != 'outer'}, indent=1, default=str))
