"""Compare real GDS component placements against the accepted baseline.

All non-fill originals must remain; only the counted new diode instances
may be added. Count equality alone cannot detect a shifted/mirrored macro.
"""
import argparse
from collections import Counter
import json
from pathlib import Path


def compare(before, after, expected_diodes):
    missing=before-after;added=after-before
    valid=not missing and sum(added.values())==expected_diodes and all(
        key[0]=='sky130_fd_sc_hd__diode_2' for key in added)
    return {'status':'PRESERVED_GDS_PLACEMENTS' if valid else 'FAIL_GDS_PLACEMENTS',
            'original_instances':sum(before.values()),'new_instances':sum(after.values()),
            'missing_or_moved_instances':sum(missing.values()),'added_diodes':sum(added.values()),
            'missing_examples':list(missing.items())[:12],
            'scope':'Component master/orientation/physical origin only; no full GDS connectivity/DRC/LVS claim.'}


if __name__=='__main__':
    import pya
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--baseline',required=True);p.add_argument('--candidate',required=True)
    p.add_argument('--masters',type=Path,required=True);p.add_argument('--diodes',type=int,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    masters=set(json.loads(a.masters.read_text()))
    snapshots=[]
    for path in (a.baseline,a.candidate):
        layout=pya.Layout();layout.read(path);top=layout.cell('automx_cim_mixed_signal_proto')
        if top is None:raise ValueError('top missing')
        signatures=Counter()
        for inst in top.each_inst():
            name=inst.cell.name
            if name not in masters:continue
            for trans in inst.cell_inst.each_trans():
                key=(name,trans.angle,trans.is_mirror(),round(trans.disp.x*layout.dbu,6),round(trans.disp.y*layout.dbu,6))
                signatures[key]+=1
        snapshots.append(signatures)
    report=compare(snapshots[0],snapshots[1],a.diodes)
    a.output.write_text(json.dumps(report,indent=2)+'\n');print(report)
    if report['status']!='PRESERVED_GDS_PLACEMENTS':raise SystemExit(1)
