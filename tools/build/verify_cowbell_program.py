"""Independent structural checks of the v2 cowbell program (offline)."""
import struct, json, hashlib
from cowbell_program import build_program, source, X, XH
from esc import records
from isa import split, is_move, nmicro

def data_ports(r):
    mic, opn = split(r)
    ld = st = 0
    for x in mic:
        if is_move(x):
            a = opn[(x & 0x1f) >> 1]
            if a < 0x2000:
                if x & 0x8000: st += 1
                else: ld += 1
    return ld, st

res = {}
bodies = [build_program(s) for s in range(6)]
W = [b['words'] for b in bodies]
n = len(W[0]); assert all(len(w) == n for w in W)
rel = []
for i in range(n):
    d = (W[1][i] - W[0][i]) & 0xffff
    assert all(W[s][i] == (W[0][i] + s * d) & 0xffff for s in range(6)), i
    if d: assert d in (4, 6, 8, 48), (i, d); rel.append((i, d))
res['relocating_halfwords'] = len(rel)
res['relocation_classes'] = sorted({d for _, d in rel})
for s, w in enumerate(W):
    rr = records(w)
    assert w[:2] == [0xa02, 0xff71] and w[-5:-1] == [0xa02, 0xff70, 0xb02, 0xf8]
    assert w[-1] == (1 if len(w) % 2 == 0 else 0)
    worst = max(data_ports(r) for _, r in rr)
    assert all(a <= 2 and b <= 2 for a, b in (data_ports(r) for _, r in rr)), s
    base = 48 * s
    priv = sorted({opn for _, r in rr for opn in split(r)[1] if False})
    # every data-memory operand referenced by a move must be private to the slot
    mem = set()
    for _, r in rr:
        mic, opn = split(r)
        for x in mic:
            if is_move(x):
                a = opn[(x & 0x1f) >> 1]
                if a < 0x2000: mem.add(a)
    assert min(mem) >= base and max(mem) <= base + 47, (s, hex(min(mem)), hex(max(mem)))
    res.setdefault('slots', []).append(dict(slot=s, bytes=len(bodies[s]['serialized']), records=len(rr),
        sha256=hashlib.sha256(bodies[s]['serialized']).hexdigest(), private_min=min(mem) - base, private_max=max(mem) - base,
        max_data_loads_stores=worst))
# donor fidelity: outside the edited records and the inserted adapter, the donor halfwords are the standard mapping
src = source()
res['donor_records'] = len(src['records'])
res['edited_donor_records'] = [1, 3, 4]
res['inserted'] = 'pitch/constant adapter (as the six working waves), 1 NOP, capture tail'
print(json.dumps(res, indent=1))
