"""Raw stock variant comparison; no firmware builder or previous layout import."""
from pathlib import Path
import struct,json,hashlib,collections
from decompress_aira_application import decompress_lzss
HERE=Path(__file__).resolve().parent
BASE=0x60000000
SYS=Path(r'C:/Users/admin/AI-Projects/sys1m_sys_v130/SYSTEM1M_UPD.BIN')
def expanded():
    b=SYS.read_bytes(); off=0x130000
    d,n=struct.unpack_from('<II',b,off+0x2c); z=struct.unpack_from('<I',b,off+0x3c)[0]
    raw,used=decompress_lzss(b[off+d:off+d+n],z);assert used==n
    assert hashlib.sha256(raw).hexdigest()=='14218bb15c4c128d6df17f888ba1939a873358b3c6b40c4eab89837fa0cde71e'
    return raw
def program(raw,table,c):
    p=struct.unpack_from('<I',raw,table+c*4)[0]
    d,n,s=struct.unpack_from('<III',raw,p-BASE)
    assert n%2==0 and BASE<=s<=BASE+len(raw)-n
    body=raw[s-BASE:s-BASE+n];w=struct.unpack('<%dH'%(n//2),body)
    return dict(descriptor=p,destination=d,source=s,size=n,sha256=hashlib.sha256(body).hexdigest(),words=[w[i^1] if i^1<len(w) else w[i] for i in range(len(w))])
def records(w):
    p=0;out=[]
    while p<len(w)-5:
        n=w[p]&31;assert n and p+n<=len(w)-5
        out.append((p,w[p:p+n]));p+=n
    assert p==len(w)-5 and w[-5:-1]==[0xa02,0xff70,0xb02,0xf8]
    return out
def flagrun(r):
    runs=[]
    for i in range(1,len(r)):
        if r[i]&0xfff not in (0xfe0,0xfe2):continue
        j=i
        while j<len(r) and r[j]&0xfff==(r[i]&0xfff)+2*(j-i):j+=1
        runs.append(list(range(i,j)))
    return max(runs,key=len) if runs else []
def main():
    raw=expanded(); tables=[0x4c7c4+0x60*t for t in range(8)]
    cells=[];text=[]
    for c in range(24):
        pp=[program(raw,t,c) for t in tables]
        variants=[pp[i] for i in (0,2,4,6)]
        assert len({len(p['words']) for p in variants})==1
        w=variants[0]['words']; rr=records(w)
        differences={i:[p['words'][i] for p in variants] for i in range(len(w)) if len({p['words'][i] for p in variants})>1}
        fields=[]
        for i,v in differences.items():
            kind='unknown'
            if v==[v[0],v[0]+400,v[0],v[0]+400] and v[0]<0x1000:kind='voice_local'
            elif v==[v[0],v[0]+400,v[0]+400,v[0]+800] and v[0]<0x1000:kind='other_local'
            elif all(x>>12==2 for x in v):kind='tag2'
            elif all(x>>12==0xa for x in v):kind='tagA'
            elif all(x>>12==0xc for x in v):kind='tagC'
            elif all(x<0x1000 for x in v):kind='working_other'
            ordinal,p,r=next((j,p,r) for j,(p,r) in enumerate(rr) if p<=i<p+len(r))
            fields.append(dict(index=i,record=ordinal,record_start=p,within_record=i-p,class_word=r[0],values=v,kind=kind))
        variable_positions=set(differences)
        # Pure move classes are stable, explicit contracts only. Mixed classes are
        # assigned a binding layout only where exactly one contiguous run agrees
        # with the raw variant positions. No arithmetic semantics are inferred.
        bindings=[];layout_ambiguous=[]
        for j,(p,r) in enumerate(rr):
            f=flagrun(r)
            if not f:continue
            candidates=[]
            for gap in (1,2,3):
                start=f[-1]+gap;pos=list(range(start,start+len(f)))
                if pos[-1]>=len(r):continue
                hits=sum(p+x in variable_positions for x in pos)
                if hits:candidates.append((hits,gap,pos))
            if not candidates:continue
            maxhits=max(x[0] for x in candidates);best=[x for x in candidates if x[0]==maxhits]
            if len(best)!=1:
                layout_ambiguous.append(dict(record=j,word_offset=p,raw=r,candidates=candidates));continue
            hits,gap,pos=best[0]
            for fi,ai in zip(f,pos):
                if p+ai not in variable_positions:continue
                bindings.append(dict(index=p+ai,record=j,value=r[ai],store=bool(r[fi]&0x8000),register=(r[fi]>>12)&7,gap=gap))
        local_values=sorted({f['values'][0] for f in fields if f['kind']=='voice_local'})
        working_values=sorted({f['values'][0] for f in fields if f['values'][0]<0x1000})
        globals_=[x for x in working_values if x<0xe0]
        cluster=[x for x in working_values if x>=0xe0]
        # This count is a lower-bound packing budget, not proof of implicit span size.
        cluster_span=max(cluster)-min(cluster)+1 if cluster else 0
        reads={b['value'] for b in bindings if not b['store']};stores={b['value'] for b in bindings if b['store']}
        pure=[dict(ordinal=j,word_offset=p,raw=r) for j,(p,r) in enumerate(rr) if r[0] in (0xc03,0x1e05,0x3e07,0x7809)]
        row=dict(cell=c,descriptors=[{k:v for k,v in p.items() if k!='words'} for p in pp],record_count=len(rr),variable_fields=fields,binding_hypotheses=bindings,ambiguous_binding_records=layout_ambiguous,working_values=working_values,voice_local_values=local_values,global_temporaries=globals_,cluster_span=cluster_span,minimum_packed_working_values=cluster_span+len(globals_),alleged_ro_working=sorted(v for v in reads-stores if v<0x1000),tag2_values=sorted({f['values'][0] for f in fields if f['kind']=='tag2'}),tagA_values=sorted({f['values'][0] for f in fields if f['kind']=='tagA'}),pure_transfers=pure)
        cells.append(row)
        text.append(f"cell {c:02} size={pp[0]['size']} records={len(rr)} cluster={hex(min(cluster)) if cluster else '-'}..{hex(max(cluster)) if cluster else '-'} span={cluster_span} globals={','.join(hex(x) for x in globals_)} total-lower-bound={cluster_span+len(globals_)} tagA={','.join(hex(x) for x in row['tagA_values'])}")
    candidate=[]
    for cell in (2,10):
        row=cells[cell];w=program(raw,tables[0],cell)['words'];rr=records(w)
        globals_fields=[f for f in row['variable_fields'] if f['values'][0] in row['global_temporaries']]
        assert all(f['class_word'] in (0xc03,0x1e05,0x3e07,0x7809) for f in globals_fields)
        local_map={x:x-0xe0 for x in row['working_values'] if x>=0xe0}
        # Preserve a complete 32-value aligned block, including unused holes and
        # padding through FF, before packing scalar prologue temporaries.
        local_map.update({x:32+i for i,x in enumerate(row['global_temporaries'])})
        assert max(local_map.values())<48 and len(set(local_map.values()))==len(local_map)
        original_matrix=[]
        for a in range(0xe0,0x100):
            for b in range(a,0x100):original_matrix.append((b-a,(b-0xe0)-(a-0xe0)))
        assert all(a==b for a,b in original_matrix)
        writefirst={}
        for j,pure in enumerate(row['pure_transfers']):
            r=pure['raw'];f=flagrun(r);start=f[-1]+1
            for fi,ai in zip(f,range(start,start+len(f))):
                value=r[ai]
                if value in row['global_temporaries'] and value not in writefirst:
                    writefirst[value]=bool(r[fi]&0x8000)
        assert all(writefirst[x] for x in row['global_temporaries'])
        candidate.append(dict(cell=cell,working_map_slot0={hex(x):hex(y) for x,y in sorted(local_map.items())},slot_working_stride=48,reserved_cluster_source=[0xe0,0xff],reserved_cluster_target=[0,31],scalar_temporary_target=[32,35],input_map_slot0={hex(x):hex(0x200a+i) for i,x in enumerate(range(0x2004,0x2008))},slot_input_stride=4,all_global_occurrences_in_pure_binding_records=True,all_global_temporaries_first_explicit_use_store=True,global_fields=globals_fields,output_map='UNRESOLVED: three original publications 2008/200A/200C; native AIRA slot exposes two outputs. Do not call2008 dead or silently change its memory class.',tagA_contract='NONE' if not row['tagA_values'] else 'A000 is loaded, but its meaning and AIRA equivalent have not been established.',relocation_limit='Affine working translation preserves every difference inside fullE0..FF span, but does not prove that no implicit access reaches outside that span. Scalar temporary packing assumes documented pure binding interpretation.'))
    wave_map=list(struct.unpack_from('<12I',raw,0x4c794))
    assert wave_map==[0,1,2,3,4,5,13,21,10,14,6,9]
    result=dict(source=str(SYS),source_sha256=hashlib.sha256(SYS.read_bytes()).hexdigest(),tables=tables,method='Halfwords that differ in original same-shape table0/2/4/6 variants; zero inherited opcode/layout semantics. Bindings hypotheses fitted from flags and varying positions, retained as hypotheses.',stock_selector_mapping=wave_map,candidates=candidate,cells=cells)
    (HERE/'next_system_interface.json').write_text(json.dumps(result,indent=2)+'\n')
    (HERE/'next_system_interface_summary.txt').write_text('\n'.join(text)+'\n')
    print('\n'.join(text))
if __name__=='__main__':main()
