import csv
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import subprocess
from datetime import datetime, timezone

root = Path(__file__).resolve().parents[2]
report = root / 'reports/pnr'
result = root / 'build/pnr/results'
c = json.loads((root / 'physical/chip-nebula/implementation.constraints.json').read_text())


def load(name):
    return json.loads((report / name).read_text())


def write(name, data):
    (report / name).write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')


def tsv(name):
    with (report / name).open() as f:
        return list(csv.DictReader(f, delimiter='\t'))


def graphs(name):
    nets = defaultdict(set)
    for row in tsv(name): nets[row['net']].add(row['terminal'])
    return Counter(tuple(sorted(v)) for v in nets.values())


def paths(name):
    parsed = defaultdict(list)
    text = (report / name).read_text()
    for chunk in text.split('Startpoint:')[1:]:
        endpoint = re.search(r'^Endpoint:\s*(.+)$', chunk, re.M)
        group = re.search(r'^Path Group:\s*(.+)$', chunk, re.M)
        kind = re.search(r'^Path Type:\s*(.+)$', chunk, re.M)
        slack = re.search(r'^\s*([-+]?\d+(?:\.\d+)?)\s+slack\b', chunk, re.M)
        assert endpoint and group and kind and slack, name
        key = (chunk.splitlines()[0].strip(), endpoint[1], group[1], kind[1])
        parsed[key].append(float(slack[1]))
    assert parsed, name
    return {k: sorted(v) for k,v in parsed.items()}


database, sta = load('database_timing.json'), load('sta_timing.json')
odb_instances = tsv('database_instances.tsv')
keep = {r['instance']:r['master'] for r in odb_instances if r['sta_preserved']=='1'}
independent = {r['instance']:r['master'] for r in tsv('sta_instances.tsv')}
antenna_db = {r['instance'] for r in odb_instances if r['antenna']=='1'}
antenna_sta = {n for n,m in independent.items() if m == c['pdn']['antenna_diode']}
instance_mismatch = keep != independent
connectivity_mismatch = graphs('database_signal_connectivity.tsv') != graphs('sta_signal_connectivity.tsv')
path_delta = 0.0
path_count = 0
path_mismatch = False
for family in ('setup','hold'):
    dbp, stap = paths(f'database_{family}_paths.rpt'), paths(f'sta_{family}_paths.rpt')
    if dbp.keys() != stap.keys(): path_mismatch = True
    for key in dbp.keys() & stap.keys():
        if len(dbp[key]) != len(stap[key]): path_mismatch = True
        for x,y in zip(dbp[key],stap[key]):
            path_delta = max(path_delta,abs(x-y)); path_count += 1
annotation = (report / 'sta_parasitic_annotation.rpt').read_text()
unannotated = re.search(r'(\d+)\s+unannotated', annotation, re.I)
assert unannotated, 'No actual SPEF annotation count found; inspect report instead of assuming zero.'
unannotated_drivers=[s.strip() for s in annotation.splitlines() if s.strip() and not s.startswith('Found ')]
assert len(unannotated_drivers)==int(unannotated[1])
all_terminals={row['terminal']:row['net'] for row in tsv('sta_all_signal_pins.tsv')}
missing_drivers=[]
for d in unannotated_drivers:
    terminal='I:'+d if 'I:'+d in all_terminals else 'P:'+d
    if terminal not in all_terminals or all_terminals[terminal]:missing_drivers.append(d)
missing_binding = len(missing_drivers)
write('spef_binding_audit.json',dict(schema_version=1,tool_unannotated_driver_count=len(unannotated_drivers),
                                  missing_connected_driver_count=missing_binding,missing_connected_drivers=missing_drivers,
                                  disconnected_unannotated_drivers=[d for d in unannotated_drivers if d not in missing_drivers],
                                  basis='Raw annotation includes unused unconnected tie-cell HI/LO outputs. Only actual connected signal-net drivers own parasitics. Every exclusion is checked against exported net connectivity; no functional connected net is exempted.',
                                  evidence=['reports/pnr/sta_parasitic_annotation.rpt','reports/pnr/sta_all_signal_pins.tsv']))
binding_warnings = []
for name in ('export_sta_netlist.log','netlist_spef_with_diodes.log'):
    for line in (report / name).read_text().splitlines():
        if re.search(r'(not found|missing|unmatched|unannotated)',line,re.I): binding_warnings.append(line)
consistency_ok = (not instance_mismatch and not connectivity_mismatch and not path_mismatch and missing_binding==0 and not binding_warnings
                  and antenna_db==antenna_sta and path_delta <= 1e-6
                  and abs(database['setup_slack_ns']-sta['setup_slack_ns'])<=1e-6
                  and abs(database['hold_slack_ns']-sta['hold_slack_ns'])<=1e-6)
consistency = dict(schema_version=1,status='passed' if consistency_ok else 'failed',
                   database_odb='build/pnr/results/6_final.odb',sta_netlist='build/pnr/results/6_final.sta.v',
                   spef='build/pnr/results/6_final.spef',sdc='build/pnr/results/6_final.sdc',
                   missing_spef_binding_count=missing_binding,
                   unannotated_disconnected_driver_count=len(unannotated_drivers)-missing_binding,
                   database_hold_slack_ns=database['hold_slack_ns'],sta_hold_slack_ns=sta['hold_slack_ns'],
                   database_setup_slack_ns=database['setup_slack_ns'],sta_setup_slack_ns=sta['setup_slack_ns'],
                   path_slack_max_abs_delta_ns=path_delta,
                   timing_instances=dict(database=len(keep),sta_netlist=len(independent)),
                   antenna_instances=dict(database=len(antenna_db),sta_netlist=len(antenna_sta)),
                   checked_path_count=path_count, instance_mismatch=instance_mismatch,
                   connectivity_mismatch=connectivity_mismatch,path_population_mismatch=path_mismatch,
                   binding_warnings=binding_warnings,
                   evidence=['reports/pnr/export_sta_netlist.log','reports/pnr/netlist_spef_with_diodes.log',
                             'reports/pnr/database_instances.tsv','reports/pnr/sta_instances.tsv',
                             'reports/pnr/database_timing.json','reports/pnr/sta_timing.json',
                             'reports/pnr/sta_parasitic_annotation.rpt'])
write('post_route_export_consistency.json',consistency)
physical = load('physical_checks.json')
drc_history = [int(n) for n in re.findall(r'Number of violations = (\d+)',(report / '5_2_route.log').read_text())]
assert drc_history, 'No measured detailed-route DRC count'
drc = drc_history[-1]
write('routing_drc_history.json',dict(schema_version=1,final_violations=drc,completed_iteration_counts=drc_history,
    in_iteration_progress=[dict(progress_percent=int(p),violations=int(n)) for p,n in re.findall(r'Completing (\d+)% with (\d+) violations',(report / '5_2_route.log').read_text())],
    evidence=['reports/pnr/5_2_route.log','reports/pnr/stages/5_route_drc.rpt'],inputs=load('input_audit.json')['inputs']))
geometry = load('database_geometry.json')
x0,y0,x1,y1=geometry['die_dbu']; die_area=(x1-x0)*(y1-y0)/geometry['dbu_per_micron']**2
electrical = {}
for kind in ('max_slew','max_capacitance','max_fanout','recovery','removal','min_pulse_width'):
    text = (report / f'database_{kind}.rpt').read_text()
    electrical[kind] = len(re.findall(r'\(VIOLATED\)',text))
snapshot_paths = ['build/pnr/results/6_final.odb','build/pnr/results/6_final.sta.v','build/pnr/results/6_final.spef','build/pnr/results/6_final.sdf','build/pnr/results/6_final.sdc','build/pnr/results/6_final.def','build/pnr/results/6_final.gds','build/pnr/results/6_final.cdl']
snapshot = {p:hashlib.sha256((root / p).read_bytes()).hexdigest() for p in snapshot_paths}
snapshot_id = hashlib.sha256(json.dumps(snapshot,sort_keys=True).encode()).hexdigest()
write('delivery_snapshot.json',dict(schema_version=1,snapshot_id='sha256:'+snapshot_id, files=snapshot,
                                   frozen_sdc_sha256=hashlib.sha256((root / c['sdc_path']).read_bytes()).hexdigest(),
                                   liberty_sha256=c['view_binding']['views'][c['view_binding']['liberty']]['sha256'],
                                   extraction_rules_sha256=c['view_binding']['views']['rcx_patterns.rules']['sha256'],
                                   inputs=load('input_audit.json')['inputs']))
write('final_connectivity.json',dict(schema_version=1,status='passed' if physical['routed'] and not connectivity_mismatch else 'failed',
                                   database_odb='build/pnr/results/6_final.odb',database_sha256=snapshot[snapshot_paths[0]],
                                   design_is_routed=physical['routed'],signal_graph_matches_export=not connectivity_mismatch,
                                   unrouted_net_count=0 if physical['routed'] else None,
                                   evidence=['reports/pnr/export_sta_netlist.log','reports/pnr/database_signal_connectivity.tsv','reports/pnr/sta_signal_connectivity.tsv']))
write('final_antenna.json',dict(schema_version=1,status='passed' if physical['antenna_violations']==0 else 'failed',
                              violations=physical['antenna_violations'],diode_instances=len(antenna_db),
                              database_odb='build/pnr/results/6_final.odb',database_sha256=snapshot[snapshot_paths[0]],
                              evidence=['reports/pnr/final_antenna.rpt','reports/pnr/export_sta_netlist.log']))
write('electrical.json',dict(schema_version=1,violations=electrical,
                           fanout_limit='Liberty has no characterized fanout ceiling; report structural fanout, without inventing a hard limit.',
                           evidence=[f'reports/pnr/database_{k}.rpt' for k in electrical]))
scope = 'Sky130HD tt_025C_1v80, 25 C/1.8 V; nebula_clock 100 ns, propagated CTS; setup/hold uncertainty 0.1 ns; nominal OpenRCX rcx_patterns.rules, R/C and early/late derates 1.0; frozen IO/reset constraints; final snapshot sha256:'+snapshot_id
def metric(id,label,value,unit,evidence):
    return dict(id=id,label=label,value=value,unit=unit,status='measured',scope=scope,evidence=evidence+['reports/pnr/delivery_snapshot.json'])
metrics = [metric('design.die_area','Die Area',die_area,'um2',['reports/pnr/database_geometry.json']),
           metric('timing.setup_slack','Setup Slack',sta['setup_slack_ns'],'ns',['reports/pnr/sta_timing.json','reports/pnr/sta_setup_paths.rpt']),
           metric('timing.hold_slack','Hold Slack',sta['hold_slack_ns'],'ns',['reports/pnr/sta_timing.json','reports/pnr/sta_hold_paths.rpt']),
           metric('drc.violations','DRC 违规',drc,'count',['reports/pnr/5_2_route.log','reports/pnr/stages/5_route_drc.rpt']),
           metric('antenna.violations','天线违规',physical['antenna_violations'],'count',['reports/pnr/final_antenna.json','reports/pnr/final_antenna.rpt'])]
write('result_summary.json',dict(schema_version=1,stage='pnr',status='partial',
                               summary=f'Routed/extracted snapshot: die area {die_area:.6f} um2; TT setup {sta["setup_slack_ns"]:.12f} ns, hold {sta["hold_slack_ns"]:.12f} ns; router DRC {drc}, antenna {physical["antenna_violations"]}. Final engineering Gate evaluation is recorded separately.',metrics=metrics))
gate = ['/tmp/chipnebula-public-repro-user37/bin/python','-m','chip_nebula.taskgraph.result_summary','reports/pnr/result_summary.json','--profile','pnr']
for kind, ids in [('--required',['antenna.violations','design.die_area','drc.violations','timing.hold_slack','timing.setup_slack']),('--measured',['design.die_area','timing.setup_slack','timing.hold_slack','drc.violations','antenna.violations'])]:
    for id in ids: gate.extend([kind,id])
with (report / 'summary_gate.log').open('w') as f:
    rc=subprocess.run(gate,cwd=root,stdout=f,stderr=subprocess.STDOUT).returncode
write('summary_gate.json',dict(command=gate,exit_code=rc,evidence='reports/pnr/summary_gate.log'))
assert rc==0, 'Frozen result-summary Gate failed'
print(json.dumps(dict(snapshot_id=snapshot_id,die_area_um2=die_area,timing=sta,drc=drc,antenna=physical['antenna_violations'],electrical=electrical,consistency=consistency_ok),indent=2))
