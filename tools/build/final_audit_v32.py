"""Independent read-back audit of the packaged v3.2 outputs (no device I/O)."""
from pathlib import Path
import sys, struct, json, hashlib
ROOT = Path(__file__).resolve().parents[2]
OLD = Path('C:/Users/admin/Documents/Codex/2026-09-22/files-mentioned-by-the-user-handoff')
sys.path[:0] = [str(ROOT / 'work/deps'), str(OLD / 'work'), str(ROOT / 'work/cowbell2')]
from repack_aira import unpack_record, APP_RECORD, APP_END
OUT = ROOT / 'outputs/wave-selector-v32-inputs'
V31 = ROOT / 'outputs/wave-selector-v31-inputs'
sha = lambda b: hashlib.sha256(b).hexdigest()
manifest = json.loads((OUT / 'MANIFEST.json').read_text())
fw = (OUT / 'firmware/AIRA_MODULAR_UPD.BIN').read_bytes()
v31fw = (OUT / 'rollback-v31/AIRA_MODULAR_UPD.BIN').read_bytes()
v2fw = (OUT / 'rollback-v2/AIRA_MODULAR_UPD.BIN').read_bytes()
v1fw = (OUT / 'rollback-v1/AIRA_MODULAR_UPD.BIN').read_bytes()
v6fw = (ROOT / 'outputs/wave-selector-v1/rollback-v6/AIRA_MODULAR_UPD.BIN').read_bytes()
assert sha(fw) == manifest['firmware_sha256']
assert sha(v31fw) == '192d0cfce81befb560077d7ce190a742ab6665c423a790b6296c2263d487f040'
assert sha(v2fw) == 'b9258bf3408f4d8e6437d7c3c4401a47af167824b076189c25e05bbd780432d8'
assert sha(v1fw) == '2089ec2d2d77bf17452b78dcfa8a36f4c5e77a890823805411082d1fbbee1317'
app, _ = unpack_record(fw, APP_RECORD, APP_END)
a31, _ = unpack_record(v31fw, APP_RECORD, APP_END)
ref, _ = unpack_record(v6fw, APP_RECORD, APP_END)
assert sha(app) == manifest['application_sha256']
assert fw[:0x40000] == v31fw[:0x40000] == v2fw[:0x40000], 'boot/header region differs'
# 1) v3.2 = v3.1 (hardware-tested) with only the FINE IN constant changed
OLDC, NEWC = (0x02222222).to_bytes(4, 'little'), (0x028F5C29).to_bytes(4, 'little')
diff = [i for i in range(len(a31)) if a31[i] != app[i]]
sites = sorted({i - k for i in diff for k in range(4) if a31[i - k:i - k + 4] == OLDC and app[i - k:i - k + 4] == NEWC})
patched = bytearray(a31)
for s in sites:
    patched[s:s + 4] = NEWC
assert bytes(patched) == app and len(sites) == 13, (len(sites), len(diff))
# 2) every stock (non-type-28) slot program and P2 entry unchanged versus stock-lineage v6
count = 0
for s in range(6):
    for t in range(49):
        if t == 28:
            continue
        p = 0x8d184 + 0x188 * s + 4 * t
        assert app[p:p + 4] == ref[p:p + 4]
        d = struct.unpack_from('<I', ref, p)[0] - 0x60000000
        _, n, src = struct.unpack_from('<III', ref, d)
        src -= 0x60000000
        assert app[d:d + 12] == ref[d:d + 12] and app[src:src + n] == ref[src:src + n]
        count += 1
# 3) native-shape audit of every v3.2 program record, and the new constant decodes to 1/100
from corpus import load
from esc import records
from isa import split
from system_osc_v32 import build_program, WAVES, c32, FINE_K
assert abs(c32(*FINE_K) - 0.01) < 1e-9
native = {(r[0], tuple(split(r)[0])) for name, w in load() for p, r in records(w)}
bad = [(n, r) for n, c in WAVES for s in range(6) for p, r in records(build_program(s, c)['words'])
       if (r[0], tuple(split(r)[0])) not in native]
assert not bad, bad[:3]
# 4) presets: identical to v3.1 except SYNC_DEMO's SAW FINE (50 -> 61)
pchg = {}
for p in sorted((OUT / 'presets').glob('*.bin')):
    a, b = (V31 / 'presets' / p.name).read_bytes(), p.read_bytes()
    d = [i for i in range(len(a)) if a[i] != b[i]]
    pchg[p.name] = d
    assert d == ([66] if p.name == 'VOICE_S1M_SYNC_DEMO.bin' else []), (p.name, d)
assert (OUT / 'presets/VOICE_S1M_SYNC_DEMO.bin').read_bytes()[64:69] == bytes([29, 1, 61, 0, 50])
result = dict(passed=True, firmware_sha256=sha(fw), application_sha256=sha(app),
              diff_vs_v31=dict(sites=[hex(s) for s in sites], differing_bytes=len(diff), change='0x02222222 (1/120) -> 0x028F5C29 (1/100)'),
              boot_header_identical_to_v31_and_v2=True, unchanged_native_slot_programs=count, all_records_native_shapes=True,
              preset_changes={k: v for k, v in pchg.items() if v},
              records_per_wave={n: build_program(0, c)['records'] for n, c in WAVES})
(OUT / 'evidence/final-audit.json').write_text(json.dumps(result, indent=2))
print(json.dumps(result, indent=1))
