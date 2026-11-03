import csv
import hashlib
import json
from pathlib import Path
import subprocess
from checkpoint import save

root=Path(__file__).resolve().parents[2]
folder=root/'reports/pnr'
def load(name):return json.loads((folder/name).read_text())
def write(name,data):(folder/name).write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')
def rows(name):
    with (folder/name).open() as stream:return list(csv.DictReader(stream,delimiter='\t'))
snapshot=load('delivery_snapshot.json');summary=load('result_summary.json')
gates=load('exit_gates.json');decks=load('independent_decks.json');geometry=load('geometry_acceptance.json')
assert load('equivalence.json')['implementation_sha256']==snapshot['files']['build/pnr/results/6_final.sta.v']
assert decks['final_gds_sha256']==snapshot['files']['build/pnr/results/6_final.gds']
assert geometry['database_sha256']==snapshot['files']['build/pnr/results/6_final.odb']
tool=load('input_audit.json')['tool_identity']['path']
with (folder/'fanout_and_area.log').open('w') as stream:
    subprocess.run([tool,'-threads','2','-no_init','-exit','build/pnr/fanout_and_area.tcl'],cwd=root,stdout=stream,stderr=subprocess.STDOUT,check=True)
groups={}
for row in rows('placed_area.tsv'):
    group=groups.setdefault(row['type'],dict(count=0,footprint_um2=0.0))
    group['count']+=1;group['footprint_um2']+=int(row['footprint_dbu2'])/1e6
fanout=sorted(rows('structural_fanout.tsv'),key=lambda row:int(row['sink_count']),reverse=True)
write('area_and_fanout.json',dict(schema_version=1,database_sha256=geometry['database_sha256'],
      placed_instance_count=sum(g['count'] for g in groups.values()),total_footprint_um2=sum(g['footprint_um2'] for g in groups.values()),
      master_type_groups=groups,max_structural_fanout=max(int(row['sink_count']) for row in fanout),largest_signal_nets=fanout[:10],
      fanout_ceiling='No characterized Liberty fanout ceiling; no hard ceiling invented.',
      evidence=['reports/pnr/structural_fanout.tsv','reports/pnr/placed_area.tsv','reports/pnr/fanout_and_area.log']))
scope=summary['metrics'][0]['scope']
for id,label,value,unit in [('custom.core_area','Actual Core Area',geometry['actual_core_area_um2'],'um2'),
                            ('custom.klayout_drc_violations','KLayout fixed-deck DRC',decks['klayout_drc_violations'],'count'),
                            ('custom.vpp_density_violations','Fixed-deck vpp density violations',decks['density_violations'],'count'),
                            ('lvs.matched','LVS 一致',decks['lvs_matched'],'boolean')]:
    summary['metrics'].append(dict(id=id,label=label,value=value,unit=unit,status='measured',scope=scope+'; '+decks['drc_scope']+'; '+decks['density_scope'],
       evidence=['reports/pnr/geometry_acceptance.json' if id=='custom.core_area' else 'reports/pnr/independent_decks.json','reports/pnr/delivery_snapshot.json']))
summary['metrics'].append(dict(id='custom.general_density_violations',label='General metal density violations',value=None,unit='count',status='not_measured',scope=scope,
       evidence=['reports/pnr/independent_decks.json'],reason=decks['density_scope']))
summary['status']='completed' if gates['passed'] else 'partial'
summary['summary']+=(' Frozen geometry and physical closure checks passed; no tapeout-release claim.' if gates['passed'] else ' Closure checks failed; layout is not publishable.')
write('result_summary.json',summary)
gate=load('summary_gate.json')['command']
with (folder/'summary_gate.log').open('w') as stream:
    rc=subprocess.run(gate,cwd=root,stdout=stream,stderr=subprocess.STDOUT).returncode
write('summary_gate.json',dict(command=gate,exit_code=rc,evidence='reports/pnr/summary_gate.log'))
assert rc==0,'Frozen summary Gate rejected final summary'
report=load('report.json') if (folder/'report.json').exists() else dict(schema_version=1)
report.update(verdict='passed' if gates['passed'] else 'failed',publishable=gates['passed'],result_summary=summary,snapshot_id=snapshot['snapshot_id'],
       summary=summary['summary'],geometry_acceptance=geometry,tool_identity='reports/pnr/tool_identity.json',
       density=dict(fixed_deck_vpp_violations=decks['density_violations'],general_chip_metal_density='not_measured; fixed deck does not implement it'),
       repair_limits='V2 planning and native legal-row geometry checked separately under authorized OpenROAD/2-thread policy. Stock tracks and route options inherited; final electrical thresholds unchanged.',
       risk='Nominal single-corner physical engineering closure does not establish tapeout-release qualification.' if gates['passed'] else 'Inspect closure/dependency evidence; physical metrics do not substitute for external reset waveform or tapeout release.')
report.pop('blocking_issue',None)
write('report.json',report)
execution=load('execution_status.json');execution['snapshot_id']=snapshot['snapshot_id'];write('execution_status.json',execution)
evidence=[p for p in folder.iterdir() if p.is_file() and p.suffix in ['.rpt','.tsv','.log','.json'] and p.name not in ['delivery_snapshot.json','report.json','execution_status.json']]
snapshot['evidence_sha256']={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in evidence}
write('delivery_snapshot.json',snapshot)
save('final_export',root/'build/pnr/results/6_final.odb','finish')
print(json.dumps(dict(verdict=report['verdict'],snapshot_id=snapshot['snapshot_id']),indent=2))
