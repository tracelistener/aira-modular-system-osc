"""Live native bulk cable roundtrip, with a reversible cable to an empty slot.

Only run after diagnostics have been removed from the bulk descriptor table.
Reads must match all ordinary cable rows before any write is attempted.
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0,r'C:\Users\admin\Documents\Codex\2026-09-22\files-mentioned-by-the-user-handoff\work\live')
from aira_live import Aira

ROOT=Path(__file__).resolve().parent.parent

def encode(value):
    assert 0<=value<1<<17
    return [value>>14&127,value>>7&127,value&127]

def decode(data):
    return data[0]<<14|data[1]<<7|data[2]

def address(row):
    return [16,33,3*row//128,3*row%128]

def main():
    a=Aira()
    result={'status':'STARTED','native_bulk_rows':0}
    restore=None
    out=ROOT/'outputs/recplay-grf6-customizer-restored/hardware-tests'
    out.mkdir(parents=True,exist_ok=True)
    try:
        before=a.snapshot()
        assert before[2+7]['data']==[0]*34,'GRF6 must remain unrouted'
        rows=[]
        for row in range(44):
            source,part=divmod(row,2)
            cables=before[2+source]['data'][part*17:(part+1)*17]
            expected=sum(bool(value)<<i for i,value in enumerate(cables))
            data=a.read(address(row),3)
            assert decode(data)==expected,(row,data,expected,'Bulk diagnostics may still be running')
            rows.append(data)
            result['native_bulk_rows']+=1
        empty=[slot for slot in range(6) if before[1]['data'][slot*5]==0]
        assert empty,'No empty module slot for a safe reversible bulk write test'
        target=10+empty[0]*4
        row=target//17  # physical source0; GRF6 is not touched
        mask=1<<(target%17)
        old=decode(rows[row])
        restore=(address(row),rows[row])
        changed=old^mask
        a.write(address(row),encode(changed))
        assert a.read([16,32,0,target],1)==[int(bool(changed&mask))]
        a.write(*restore)
        restore=None
        after=a.snapshot()
        assert all(x['data']==y['data'] for x,y in zip(before,after)),'Patch did not restore exactly'
        result.update(status='PASS',bulk_read_matches_individual=True,
            bulk_write_changes_individual_cable=True,patch_restored=True,
            test_connection={'source':0,'target':target,'empty_slot':empty[0]+1},
            grf6_unrouted=after[2+7]['data']==[0]*34)
    finally:
        if restore is not None:
            try:
                a.write(*restore)
                result['emergency_restore']='Native bulk row restored'
            except Exception as exc:
                result['emergency_restore']=repr(exc)
        a.close()
        path=out/(time.strftime('%Y%m%d-%H%M%S')+'-native-bulk.json')
        path.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':
    main()
