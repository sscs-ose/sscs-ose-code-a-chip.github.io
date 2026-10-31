import json
from pathlib import Path
import pya

out = Path(__file__).resolve().parent
def value(obj,name):
    member=getattr(obj,name)
    return member() if callable(member) else member

def drc(path):
    rdb=pya.ReportDatabase()
    rdb.load(str(path))
    categories=[]
    for c in rdb.each_category():
        n=sum(1 for _ in rdb.each_item_per_category(c.rdb_id()))
        if n: categories.append(dict(name=value(c,'name'),violations=n))
    return dict(violations=rdb.num_items(),categories=categories)

def lvs(path):
    db=pya.LayoutVsSchematic()
    db.read(str(path))
    xref=db.xref()
    assert xref is not None
    pairs=[]
    for p in xref.each_circuit_pair():
        a,b,s=value(p,'first'),value(p,'second'),value(p,'status')
        pairs.append(dict(layout=value(a,'name') if a else None, schematic=value(b,'name') if b else None,
                          status=str(s), matched=s==pya.NetlistCrossReference.Match))
    circuits=[]
    for c in db.netlist().each_circuit():
        devices=list(c.each_device())
        circuits.append(dict(name=c.name, devices=len(devices), classes=sorted({d.device_class().name for d in devices})))
    top=[p for p in pairs if (p['layout'] or '').lower()=='nebula_cpu_npu_top' and (p['schematic'] or '').lower()=='nebula_cpu_npu_top']
    return dict(matched=bool(top) and all(p['matched'] for p in pairs),pairs=pairs,
                extracted_circuits=circuits, extracted_device_count=sum(c['devices'] for c in circuits),
                device_count_scope='Stored per-circuit devices after deck simplification; hierarchical count, not flattened transistor population',
                mos_extraction_present=any('nfet' in cls or 'pfet' in cls for c in circuits for cls in c['classes']))

positive_drc=drc(out/'drc.lyrdb')
negative_drc=drc(out/'negative/drc_width.lyrdb')
positive_lvs=lvs(out/'lvs.lvsdb')
negative_lvs=lvs(out/'negative/lvs_missing_gate.lvsdb')
passed=(positive_drc['violations']==0 and positive_lvs['matched'] and positive_lvs['extracted_device_count']>0 and positive_lvs['mos_extraction_present']
        and any(c['name']=='m1.1' and c['violations']>0 for c in negative_drc['categories']) and not negative_lvs['matched'])
result=dict(schema_version=1,status='passed' if passed else 'failed',positive_drc=positive_drc,
            positive_lvs=positive_lvs,negative_drc=negative_drc,negative_lvs=negative_lvs,
            scope='Frozen installed Sky130HD decks; DRC BEOL/off-grid, partial vpp density; LVS MOS geometry extraction, hierarchical CDL comparison. FEOL DRC and general metal density excluded.')
(out/'checks.json').write_text(json.dumps(result,indent=2)+'\n')
assert passed, 'Positive checks or negative-control detection failed'
print('INSTALLED_DRC_DEVICE_LVS_NEGATIVE_CONTROLS_PASS',positive_lvs['extracted_device_count'])
