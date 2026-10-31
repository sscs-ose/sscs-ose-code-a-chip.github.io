import hashlib
import json
from pathlib import Path
import pya

root = Path(__file__).resolve().parents[2]
report = root / 'reports/pnr'
def value(obj,name):
    member=getattr(obj,name)
    return member() if callable(member) else member
rdb = pya.ReportDatabase()
rdb.load(str(report / 'stages/6_drc.lyrdb'))
categories=[]
for category in rdb.each_category():
    count=sum(1 for _ in rdb.each_item_per_category(category.rdb_id()))
    if count:categories.append(dict(name=value(category,'name'),violations=count))
lvs=pya.LayoutVsSchematic()
lvs.read(str(report / '6_lvs.lvsdb'))
xref=lvs.xref()
assert xref is not None,'Missing actual LVS comparison result'
circuits=[]
for pair in xref.each_circuit_pair():
    first,second,status=value(pair,'first'),value(pair,'second'),value(pair,'status')
    circuits.append(dict(layout=value(first,'name') if first is not None else None,
                         schematic=value(second,'name') if second is not None else None,
                         status=str(status),matched=status==pya.NetlistCrossReference.Match))
assert circuits,'Empty LVS cannot count as matched'
top='nebula_cpu_npu_top'
top_matches=[p for p in circuits if (p['layout'] or '').lower()==top and (p['schematic'] or '').lower()==top]
matched=bool(top_matches) and all(p['matched'] for p in circuits)
result=dict(schema_version=1,status='passed' if rdb.num_items()==0 and matched else 'failed',
            klayout_drc_violations=rdb.num_items(),drc_categories=categories,lvs_matched=matched,
            lvs_circuits=circuits,drc_scope='Frozen deck: BEOL and off-grid checks; FEOL is disabled in the frozen runset.',
            density_scope='Frozen deck implements vpp overlap density rules only; general chip-level metal-density qualification is not measured.',
            density_violations=sum(p['violations'] for p in categories if p['name'] in ['vpp.5a','vpp.5b','vpp.5c']),
            final_gds_sha256=hashlib.sha256((root / 'build/pnr/results/6_final.gds').read_bytes()).hexdigest(),
            evidence=['reports/pnr/stages/6_drc.lyrdb','reports/pnr/independent_drc.log','reports/pnr/6_lvs.lvsdb','reports/pnr/independent_lvs.log','reports/pnr/deck_commands.json'])
(report / 'independent_decks.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:result[k] for k in ['status','klayout_drc_violations','lvs_matched','density_violations']},indent=2))
