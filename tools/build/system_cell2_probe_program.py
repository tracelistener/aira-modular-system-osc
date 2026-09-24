"""Experimental SYSTEM cell2 donor transform. Emits no firmware or flash data.

The four original inputs are retained but driven by a deliberately bounded
fixed-control hypothesis. No arithmetic semantics or pitch scaling is claimed.
"""
from pathlib import Path
from functools import lru_cache
import hashlib,json,struct
from next_system_interface import expanded,program,records,BASE

HERE=Path(__file__).resolve().parent
SOURCE_EXPECTED='14218bb15c4c128d6df17f888ba1939a873358b3c6b40c4eab89837fa0cde71e'
SYS_INPUTS=(0x2004,0x2005,0x2006,0x2007)
SYS_OUTPUTS=(0x2008,0x200a,0x200c)
DEFAULT_ENDPOINTS=(0x200a,0x2008,0x2008,0x2008,0x200c,0x2008)

def serial(words):
    """Invert the original 16-bit lane permutation, including odd final word."""
    swapped=[words[i^1] if i^1<len(words) else words[i] for i in range(len(words))]
    return struct.pack('<%dH'%len(words),*swapped)

@lru_cache(maxsize=1)
def source_material():
    raw=expanded();assert hashlib.sha256(raw).hexdigest()==SOURCE_EXPECTED
    # Exact same-shape stored placements define the writable donor fields.
    variants=[program(raw,0x4c7c4+0x60*t,2) for t in (0,2,4,6)]
    words=variants[0]['words']
    assert len(words)==343 and len(records(words))==78
    assert all(len(p['words'])==len(words) for p in variants)
    fields=sorted(i for i in range(len(words)) if len({p['words'][i] for p in variants})>1)
    assert len(fields)==52
    original_values={words[i] for i in fields}
    assert {x for x in original_values if x>=0x1000}==set(SYS_INPUTS+SYS_OUTPUTS)
    assert {x for x in original_values if x<0xe0}=={0x19,0x2b,0x32,0x68}
    assert all(0xe0<=x<=0xfa for x in original_values if 0xe0<=x<0x1000)
    # Locate the unmodified base producer and immediately following pure store.
    base_ptr=struct.unpack_from('<I',raw,0x4c784)[0]
    dest,n,src=struct.unpack_from('<III',raw,base_ptr-BASE)
    data=raw[src-BASE:src-BASE+n]
    words_base=list(struct.unpack('<%dH'%(n//2),data))
    words_base=[words_base[i^1] if i^1<len(words_base) else words_base[i] for i in range(len(words_base))]
    base_records=records(words_base)
    producer=base_records[22][1]
    store=base_records[23][1]
    assert producer==[0x1506,0x0060,0x1063,0x0000,0x0030,0x0000]
    assert store==[0x1e05,0x8fe0,0x9fe2,0x0034,0x0035]
    assert base_records[22][0]==0xaf and base_records[23][0]==0xb5
    return dict(words=words,fields=fields,variant_descriptors=[{k:v for k,v in p.items() if k!='words'} for p in variants],
                producer=producer,store=store,base_descriptor=base_ptr,base_program_destination=dest,base_program_source=src,
                base_program_sha256=hashlib.sha256(data).hexdigest())

def build_program(slot,output_original=0x2008):
    """Return {serialized, words, metadata} and descriptive aliases; slot0..5."""
    if not isinstance(slot,int) or not 0<=slot<6:raise ValueError('slot must be0..5')
    if output_original not in SYS_OUTPUTS:raise ValueError('select original2008,200A,or200C')
    s=source_material();original=s['words'];base=48*slot
    mapping={x:base+x-0xe0 for x in range(0xe0,0x100)}
    mapping.update({0x19:base+32,0x2b:base+33,0x32:base+34,0x68:base+35})
    mapping.update({0x2004:0xc035+8*slot,0x2005:0xc032+8*slot,0x2006:0xc033+8*slot,0x2007:base+37})
    mapping.update({x:base+38+(x-0x2008) for x in SYS_OUTPUTS})
    # Every source value must resolve consistently. Exact position whitelist is
    # derived from stock placements, so equal-looking literals remain unchanged.
    transformed=original.copy();edits=[]
    for i in s['fields']:
        old=original[i];assert old in mapping
        transformed[i]=mapping[old]
        edits.append(dict(original_logical_index=i,before=old,after=transformed[i]))
    assert [i for i,(a,b) in enumerate(zip(original,transformed)) if a!=b]==s['fields']
    assert all(transformed[i]==original[i] for i in range(len(original)) if i not in set(s['fields']))
    assert len(records(transformed))==78
    assert len({mapping[x] for x in {original[i] for i in s['fields']}})==len({original[i] for i in s['fields']})
    assert transformed[:2]==[0xa02,0xff71]
    assert transformed[-5:]==original[-5:]
    producer=s['producer'].copy()
    init_store=s['store'].copy();init_store[-2:]=[base+36,base+37]
    selected=mapping[output_original]
    # This uses the same pure storelocal/loadlocal/publication tail pattern as
    # the native modules. Equivalence of tag2 and scratch capture is experimental.
    tail_load=[0x0c03,0x0fe0,selected]
    tail_store=[0x0c03,0x8fe0,0x2022+6*slot]
    inserted=producer+init_store
    words=transformed[:2]+inserted+transformed[2:-5]+tail_load+tail_store+transformed[-5:]
    rr=records(words)
    assert len(rr)==82 and len(words)==360
    assert words[2:8]==producer and words[8:13]==init_store
    kernel_recovered=words[:2]+words[13:-11]+words[-5:]
    assert kernel_recovered==transformed
    for a in range(0xe0,0x100):
        for b in range(a,0x100):assert mapping[b]-mapping[a]==b-a
    for a in SYS_OUTPUTS:
        for b in SYS_OUTPUTS:assert mapping[b]-mapping[a]==b-a
    assert [mapping[x] for x in SYS_OUTPUTS]==[base+38,base+40,base+42]
    assert max(v for k,v in mapping.items() if v<0x1000)==base+42
    assert min(v for k,v in mapping.items() if v<0x1000)>=base
    # Original input bindings at raw prologue positions, including both formerly
    # discarded sources, survive asfour separate sources with exactlyone read.
    inputs=[];outputs=[]
    original_rr=records(original)
    for j,(p,r) in enumerate(original_rr):
        for k in range(1,len(r)):
            i=p+k
            if i not in s['fields']:continue
            if r[k] in SYS_INPUTS:inputs.append(dict(source=r[k],target=transformed[i],record=j,field=i))
            if r[k] in SYS_OUTPUTS:outputs.append(dict(source=r[k],capture=transformed[i],record=j,field=i))
    assert sorted(x['source'] for x in inputs)==list(SYS_INPUTS)
    assert sorted(x['source'] for x in outputs)==list(SYS_OUTPUTS)
    assert len({x['target'] for x in inputs})==4
    body=serial(words)
    assert len(body)==720
    stored=list(struct.unpack('<360H',body))
    assert [stored[i^1] for i in range(len(stored))]==words
    metadata=dict(status='STRUCTURAL_EXPERIMENT_ONLY_NOT_A_DSP_SEMANTICS_PROOF',slot_zero_based=slot,physical_slot=slot+1,
        source_application_sha256=SOURCE_EXPECTED,source_descriptors=s['variant_descriptors'],source_cell=2,
        source_program_bytes=len(original)*2,source_record_count=78,program_bytes=len(body),record_count=82,
        source_program_sha256=hashlib.sha256(serial(original)).hexdigest(),program_sha256=hashlib.sha256(body).hexdigest(),
        requested_original_output=output_original,selected_private_capture=selected,native_first_output=0x2022+6*slot,
        source_field_count=len(s['fields']),source_field_rewrites=edits,input_bindings=inputs,output_bindings=outputs,
        working_reserved_cluster=dict(source_start=0xe0,source_end=0xff,target_start=base,target_end=base+31),
        working_scalar_temporaries={hex(x):mapping[x] for x in (0x19,0x2b,0x32,0x68)},
        working_constant_outputs=[base+36,base+37],working_output_captures=[base+38,base+40,base+42],
        constant_source=dict(base_descriptor=s['base_descriptor'],base_program_destination=s['base_program_destination'],base_program_source=s['base_program_source'],base_program_sha256=s['base_program_sha256'],producer_record=22,producer_original_words=s['producer'],store_record=23,store_original_words=s['store'],store_rebound_words=init_store),
        appended_records=[tail_load,tail_store],
        checks=dict(original_arithmetic_halfwords_verbatim=True,only_stock_variant_fields_rewritten=True,
            all_original_inputs_retained=True,all_original_outputs_captured=True,cluster_full32_value_affine_spacing_preserved=True,
            all_three_output_address_differences_preserved=True,working_targets_within_48_value_slot=True,
            record_tiling_and_terminal_preserved=True,lane_serialization_roundtrips=True),
        hypotheses=[
            'C035 enumfloat0..5 is an exploratory fixed drive for SYSTEM2004; no original pitch quantity or calibratedMIDI correspondence is established.',
            'C032 nativep2 andC033 nativep3 values are trial inputs for SYSTEM2005/2006; matching ranges are not a proof of musical units.',
            'Original1506 producer is executed unchanged to populate both original34/35 results; its numeric values and register semantics remain unknown.',
            'Input2007 reads the captured second constant-producer result; pure-store direction/register decoding is assumed.',
            'Original output stores are redirected from tag2 transport to private scratch, then a selected result is published by pureload/store; this experimentally assumes scalar register preservation across memory classes.',
            'WholeE0..FF spacing is preserved, but unobserved implicit accesses outside it are not excluded.',
            'Host range callback must be replaced withC035 control publication; nativeSAW P-memory writes must not target this donor layout.',
            'NativeSAW DSP output scaling stage is absent. This probe has no proven amplitude or pitch calibration.'
        ])
    return dict(serialized=body,words=words,program_bytes=body,logical_words=words,metadata=metadata)

def main():
    outputs=[build_program(slot,endpoint) for slot,endpoint in enumerate(DEFAULT_ENDPOINTS)]
    # Check every endpoint in every physical slot, not merely selected defaults.
    variants=[build_program(slot,endpoint) for slot in range(6) for endpoint in SYS_OUTPUTS]
    result=dict(scope='Offline donor transformation only. No updater image, descriptor table, CPU code, or hardware is modified.',
                function_api='build_program(slot_zero_based, original_output_address) returns serialized:bytes, words:list, metadata:dict (program_bytes/logical_words are aliases)',
                endpoint_choices=[hex(x) for x in SYS_OUTPUTS],tested_combinations=len(variants),
                defaults=[dict(metadata=x['metadata'],logical_words=x['logical_words']) for x in outputs])
    path=HERE/'system_cell2_probe_program.json';path.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(result=str(path),tested_combinations=len(variants),default_program_bytes=[len(x['program_bytes']) for x in outputs],sha256=[x['metadata']['program_sha256'] for x in outputs]),indent=2))

if __name__=='__main__':main()
