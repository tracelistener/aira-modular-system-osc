"""SCOOPER-only WAVE selector v3.2 (v3.1 + stock FINE IN scale): the seven v2 waves with the stock-oscillator jack set
(CV IN, FINE IN, COLOR IN, SYNC TRIG IN). Offline build; no device I/O.

ARM code (entry, boot sync, select stub), hooks, table layout and state are byte-identical to v2 (asserted).
Data changes versus v2:
  * every wave master is the v3 program (work/cowbell2/system_osc_v32.py); relocation lists regenerated
  * masters are placed first-fit in the Torcido pool, overflow after the relocation lists in the Bitrazer area
  * each slot's type-28 program area and descriptor size are initialised with that slot's default wave in v3 form,
    so a slot that is never re-selected also runs the v3 adapter (v1/v2 relied on v6 == v1 masters here)
"""
from pathlib import Path
import sys, struct, json
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OLD = Path('C:/Users/admin/Documents/Codex/2026-09-22/files-mentioned-by-the-user-handoff')
sys.path[:0] = [str(ROOT / 'work/deps'), str(OLD / 'work'), str(ROOT / 'work/cowbell2')]
from system_osc_v32 import build_program as v3_program, WAVES
from repack_aira import unpack_record, pack_application, validate_outer, APP_RECORD, APP_END, sha

B = 0x60000000
OUT = ROOT / 'outputs/wave-selector-v32-inputs'
V2_APP = ROOT / 'work/selector-v2/application.bin'
V2_FW = ROOT / 'outputs/wave-selector-v2-cowbell/firmware/AIRA_MODULAR_UPD.BIN'
V2_FW_SHA = 'b9258bf3408f4d8e6437d7c3c4401a47af167824b076189c25e05bbd780432d8'
V1_FW = ROOT / 'outputs/wave-selector-v1/firmware/AIRA_MODULAR_UPD.BIN'
V1_FW_SHA = '2089ec2d2d77bf17452b78dcfa8a36f4c5e77a890823805411082d1fbbee1317'
NW = len(WAVES)
CODE = B + 0x874a0
BOOT = CODE + 0x200
SELECT = CODE + 0x300
TABLE = CODE + 0x500
STATE = CODE + 0x570
RELOCS = CODE + 0x580
BITRAZER_END = CODE + 6302
MASTER = B + 0x89860
TORCIDO_END = MASTER + 7364
RANGE_TABLE = 0x825c0


def SLOT_AREA(s):
    return B + 0x81ffc + 0x5e0 * s


def word(b, o):
    return struct.unpack_from('<I', b, o)[0]


def program(slot, w):
    return v3_program(slot, WAVES[w][1])['serialized']


def build():
    fw = (OLD / 'outputs/system-waves-v6/firmware/AIRA_MODULAR_UPD.BIN').read_bytes()
    assert sha(fw) == '42691be6964ac05fb1e3751b91f027fd8ff8beecaf3230506c4c780cc1fd1e7e'
    v2fw = V2_FW.read_bytes()
    assert sha(v2fw) == V2_FW_SHA
    v2, _ = unpack_record(v2fw, APP_RECORD, APP_END)
    ref, _ = unpack_record(fw, APP_RECORD, APP_END)
    app = bytearray(v2)            # start from the packaged v2 image: identical code, hooks, table layout
    regions = []

    def put(addr, data):
        off = addr - B
        app[off:off + len(data)] = data
        regions.append((off, off + len(data)))

    progs = [[program(s, w) for s in range(6)] for w in range(NW)]
    rels = []
    for w in range(NW):
        bodies = progs[w]
        n = len(bodies[0])
        assert all(len(x) == n for x in bodies)
        assert n <= RANGE_TABLE - (SLOT_AREA(0) - B), 'slot-0 program would reach the RANGE table'
        hw = [struct.unpack('<%dH' % (n // 2), x) for x in bodies]
        rel = []
        for i in range(n // 2):
            d = hw[1][i] - hw[0][i]
            assert all(hw[s][i] == (hw[0][i] + d * s) & 65535 for s in range(6))
            if d:
                assert d in (4, 6, 8, 48)
                rel.append((2 * i, d))
        terminal_index = ((n // 2 - 1) ^ 1) if (n // 2) % 2 == 0 else n // 2 - 1
        assert hw[0][terminal_index] == (1 if (n // 2) % 2 == 0 else 0)
        rels.append(rel)
    rp = RELOCS
    reloc_addr = []
    for rel in rels:
        put(rp, b''.join(struct.pack('<HH', *r) for r in rel))
        reloc_addr.append(rp)
        rp += 4 * len(rel)
    bitrazer_free = (rp + 3) & ~3
    mp_t, mp_b = MASTER, bitrazer_free
    waves = []
    for w, (name, cell) in enumerate(WAVES):
        n = len(progs[w][0])
        if mp_t + n <= TORCIDO_END:
            m = mp_t; mp_t += n; pool = 'torcido'
        else:
            m = mp_b; mp_b += (n + 3) & ~3; pool = 'bitrazer'
        put(m, progs[w][0])
        put(TABLE + 16 * w, struct.pack('<IIII', m, n, reloc_addr[w], len(rels[w])))
        waves.append(dict(name=name, cell=cell, bytes=n, relocations=len(rels[w]), master=m, reloc=reloc_addr[w], pool=pool,
                          records=v3_program(0, cell)['records']))
    assert mp_t <= TORCIDO_END and mp_b <= BITRAZER_END
    assert bytes(app[STATE - B:STATE - B + 6]) == bytes(range(6))
    slots = []
    for s in range(6):
        desc = word(ref, 0x8d184 + 0x188 * s + 28 * 4)
        dest, size, src = struct.unpack_from('<III', ref, desc - B)
        assert dest == 0x3000 + 0x900 * s and src == SLOT_AREA(s)
        body = progs[s][s]
        put(src, body)
        put(desc + 4, struct.pack('<I', len(body)))
        slots.append(dict(slot=s, descriptor=desc, source=src, default_wave=WAVES[s][0], bytes=len(body)))
    assert app[RANGE_TABLE:RANGE_TABLE + 24] == ref[RANGE_TABLE:RANGE_TABLE + 24], 'RANGE table'
    assert len(app) == len(v2)
    assert all(a == b or any(lo <= i < hi for lo, hi in regions) for i, (a, b) in enumerate(zip(v2, app)))
    for lo, hi in ((CODE, CODE + 0x200), (BOOT, BOOT + 0x100), (SELECT, SELECT + 0x200)):
        assert app[lo - B:hi - B] == v2[lo - B:hi - B]
    for off in (0x17070, 0x171ee, 0x11f12):
        assert app[off:off + 4] == v2[off:off + 4]
    diff = [i for i in range(len(v2)) if v2[i] != app[i]]
    (HERE / 'application.bin').write_bytes(app)
    meta = dict(status='BUILD CANDIDATE; OFFLINE VALIDATION PENDING; HARDWARE UNTESTED', product='SCOOPER ONLY',
                waves=waves, slots=slots, regions=regions, baseline_sha256=sha(fw), application_sha256=sha(app),
                v2_lineage=dict(v2_firmware_sha256=V2_FW_SHA, v2_application_sha256=sha(v2), differing_bytes=len(diff),
                                code_and_hooks_identical=True),
                pools=dict(torcido_used=mp_t - MASTER, torcido_size=7364, relocs_end=hex(rp), bitrazer_masters_end=hex(mp_b),
                           bitrazer_end=hex(BITRAZER_END)),
                encoding='P2 0..6: FM, FM+SYNC, TRI, LOGIC, NOISE SAW, VOWEL, CB; >=7 -> FM',
                jacks='in1 CV IN, in2 FINE IN (1.0 = 1.2 semitones, stock SAW/SQR scale), in3 COLOR IN (+ P3/100), '
                      'in4 SYNC TRIG IN (rising through 0.3: hard sync; CB strike)')
    (HERE / 'build.json').write_text(json.dumps(meta, indent=2))
    return bytes(app), fw, meta


if __name__ == '__main__':
    app, fw, meta = build()
    print(json.dumps(dict(waves=[(w['name'], w['bytes'], w['records'], w['relocations'], hex(w['master']), w['pool'])
                                 for w in meta['waves']], pools=meta['pools'], lineage=meta['v2_lineage']), indent=1))
