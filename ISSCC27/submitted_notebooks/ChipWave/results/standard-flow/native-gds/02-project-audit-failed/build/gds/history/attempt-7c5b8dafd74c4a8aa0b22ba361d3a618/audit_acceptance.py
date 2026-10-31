import collections
import hashlib
import json
from pathlib import Path
import subprocess

root=Path(__file__).resolve().parents[2]
out=root/'build/gds'
def read(path): return json.loads((root/path).read_text())
def write(name,data): (out/name).write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')
def sha(path):
    h=hashlib.sha256()
    with (root/path).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()

acceptance=read('.nebula_inputs/artifact-8bfa326445194758816c2d0d07307a6f/artifact.json')
verification=read('.nebula_inputs/artifact-7295759bd83c446780157c3cdc2d72ae/artifact.json')
layout=read('.nebula_inputs/artifact-d2ef1f1f7d194cf0b4a0c9e746873b2c/artifact.json')
plan=acceptance['payload']
snapshot=read('reports/pnr/delivery_snapshot.json')
assert layout['payload']['snapshot_id']==snapshot['snapshot_id']
assert verification['payload']['spec_digest']==plan['spec_digest']
assert read('reports/pnr/input_audit.json')['spec_digest']==plan['spec_digest']
assert read('reports/verification/baseline-revalidation.json')['verdict']=='passed'
assert sha('spec/acceptance.plan.yaml')=='ec381baedf0e96f4d3546966afd47b238e7f8a65b758a3093d316507a1409861'

# Verify captured Git objects as well as manifest hashes; filenames alone are insufficient.
bindings=[]
for rec in [acceptance,verification,layout,read('.nebula_inputs/artifact-971f6c7042664af69515024a25a72bc2/artifact.json')]:
    paths=rec['content']['paths']
    raw=subprocess.check_output(['git','ls-tree','-r','-z',rec['content']['commit'],'--',*paths],cwd=root)
    blobs={row.split(b'\t',1)[1].decode():row.split(b'\t',1)[0].split()[2].decode() for row in raw.split(b'\0') if row}
    for path in paths:
        p=root/path
        h=hashlib.sha1(f'blob {p.stat().st_size}\0'.encode())
        with p.open('rb') as f:
            for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
        assert h.hexdigest()==blobs[path],path
    bindings.append(dict(artifact_id=rec['id'],commit=rec['content']['commit'],files_checked=len(paths),status='passed'))
manifest=read('reports/verification/evidence-manifest.json')
for row in manifest['files']:
    path=row['path']
    assert path.startswith(('reports/verification/','reports/performance/')),path
    assert sha(path)==row['sha256'] and (root/path).stat().st_size==row['bytes'],path
assert all(sha(p)==h for p,h in snapshot['files'].items())
write('upstream_binding.json',dict(status='passed',git_artifacts=bindings,
                                 verification_manifest_files_checked=len(manifest['files']),
                                 snapshot_id=snapshot['snapshot_id'],functional_evidence_origin='reused qualified verifier execution',
                                 evidence_reuse='reports/verification/evidence-reuse.json',
                                 rtl_to_mapped_note=read('reports/pnr/upstream_receipts.json')['rtl_to_synthesis_formal_equivalence']))

prior={c['id']:c for c in verification['payload']['checks']}
by_id={}
for check in plan['checks']:
    old=prior[check['id']]
    row=dict(id=check['id'],title=check['title'],responsible_stage=check['responsible_stage'],
             requirement_ids=check['requirement_ids'],design_groups=check['design_groups'],dependencies=check['dependencies'],
             verdict=old['verdict'],execution_status='PASS' if old['verdict']=='passed' else 'PENDING',
             result_origin=old.get('result_origin','upstream'),scenarios=old.get('scenarios',[]),
             reason=old.get('reason','Qualified original verification evidence retained without rerunning.'),
             evidence=old['evidence'],evidence_binding='build/gds/upstream_binding.json',snapshot_id=snapshot['snapshot_id'])
    config=check['detail'].split('Configuration: ',1)[1].split('. Dependencies:',1)[0]
    row['configurations']=['rv32i_five_stage_cpu ENABLE_XNEBULA=0','rv32i_five_stage_cpu ENABLE_XNEBULA=1'] if config=='both core configurations' else [config]
    by_id[row['id']]=row

def set_result(check,passed,reason,evidence,origin='revalidated upstream'):
    by_id[check].update(verdict='passed' if passed else 'failed',execution_status='PASS' if passed else 'FAIL',
                        reason=reason,evidence=evidence,result_origin=origin)

audit=read('reports/pnr/input_audit.json')
identity=read('reports/pnr/tool_identity.json')
revalidation=read('reports/pnr/restored_snapshot_revalidation.json')
set_result('AC-PHYSICAL-INPUTS',audit['verdict']=='passed' and revalidation['status']=='passed',
           'Frozen V2 inputs, installed views, selected 4a7cf tool/2 threads and same-spec mapped input revalidated upstream; immutable reports verified here.',
           ['reports/pnr/input_audit.json','reports/pnr/tool_identity.json','reports/pnr/orfs_flow_identity.json','reports/pnr/restored_snapshot_revalidation.json','reports/pnr/commands.json'])
geo=read('reports/pnr/geometry_acceptance.json')
placed=read('reports/pnr/placement_geometry/geometry_acceptance.json')
set_result('AC-FLOORPLAN',geo['status']=='passed' and placed['status']=='passed' and not geo['errors'] and min(geo['actual_margins_um'].values())>=10,
           'Native planned versus legal-row bounds, integer DBU, margins, sites, placement and pin legality pass at placement/final snapshot.',
           ['reports/pnr/geometry_acceptance.json','reports/pnr/placement_geometry/geometry_acceptance.json','reports/pnr/database_rows.tsv','reports/pnr/database_pin_locations.tsv','reports/pnr/database_placed_instances.tsv','reports/pnr/floorplan.log'])
connectivity=read('reports/pnr/final_connectivity.json')
set_result('AC-PDN-ROUTING',geo['unconnected_pg_terminal_count']==0 and connectivity['status']=='passed' and connectivity['unrouted_net_count']==0,
           'Actual PG/support inventory, frozen PDN/track/route scripts and routed signal connectivity retained in the same snapshot.',
           ['reports/pnr/database_power_connections.tsv','reports/pnr/geometry_acceptance.json','reports/pnr/database_instances.tsv','reports/pnr/input_audit.json','reports/pnr/grt.log','reports/pnr/route.log','reports/pnr/final_connectivity.json'])
consistency=read('reports/pnr/post_route_export_consistency.json')
set_result('AC-POSTROUTE-STA',consistency['sta_setup_slack_ns']>=0 and consistency['sta_hold_slack_ns']>=0 and consistency['status']=='passed',
           'TT 25C/1.8V, propagated 100 ns clock, uncertainty 0.1 ns, nominal R/C and derates 1.0; setup and hold pass. Single corner only.',
           ['reports/pnr/sta_timing.json','reports/pnr/sta_setup_paths.rpt','reports/pnr/sta_hold_paths.rpt','reports/pnr/sta_unconstrained_paths.rpt','reports/pnr/cts.log','build/pnr/results/6_final.sta.v','build/pnr/results/6_final.spef','build/pnr/results/6_final.sdc'])
electrical=read('reports/pnr/electrical.json')
reset=read('reports/pnr/external_reset_dependency.json')
set_result('AC-ELECTRICAL',all(v==0 for v in electrical['violations'].values()) and reset['status']=='passed',
           'Characterized slew/capacitance, recovery/removal/pulse checks and frozen external reset waveform pass; characterized fanout ceiling unavailable, structural maximum reported.',
           electrical['evidence']+['reports/pnr/external_reset_dependency.json','reports/pnr/reset_evidence/reset-waveform.vcd','reports/pnr/area_and_fanout.json'])
antenna=read('reports/pnr/final_antenna.json')
pnr_summary=read('reports/pnr/result_summary.json')
metrics={m['id']:m['value'] for m in pnr_summary['metrics']}
set_result('AC-ROUTE-CLEAN',metrics['drc.violations']==0 and antenna['violations']==0 and connectivity['unrouted_net_count']==0 and read('reports/pnr/execution_status.json')['status']=='succeeded',
           'Final router DRC/antenna are zero, all functional nets routed, completed execution bound to unchanged final ODB.',
           ['reports/pnr/5_2_route.log','reports/pnr/final_antenna.json','reports/pnr/final_connectivity.json','reports/pnr/execution_status.json','reports/pnr/result_summary.json'])
set_result('AC-EXPORT-CONSISTENCY',consistency['status']=='passed' and consistency['path_slack_max_abs_delta_ns']<=1e-6 and not any(consistency[k] for k in ['instance_mismatch','connectivity_mismatch','path_population_mismatch']) and consistency['missing_spef_binding_count']==0,
           'Final ODB versus STA netlist/SPEF identity, ownership/connectivity and 9734 path reload comparisons pass within 1e-6 ns.',
           ['reports/pnr/post_route_export_consistency.json','reports/pnr/spef_binding_audit.json','reports/pnr/equivalence.json','reports/pnr/delivery_snapshot.json'])
checks=read('build/gds/checks.json')
set_result('AC-DRC-LVS',checks['status']=='passed',
           'Installed frozen decks on this exact export: DRC zero, nonempty MOS-device-extracted hierarchical LVS matched; metal-width and missing-poly negative controls detected. FEOL DRC/general density excluded.',
           ['build/gds/checks.json','build/gds/drc.lyrdb','build/gds/lvs.lvsdb','build/gds/extracted.cir','build/gds/commands.json','build/gds/resources.json','build/gds/negative/mutations.json','build/gds/negative/drc_width.lyrdb','build/gds/negative/lvs_missing_gate.lvsdb'],origin='newly executed')
readable=read('build/gds/readability.json')
set_result('AC-GDS',readable['readable'] and readable['bytes']>0 and readable['top_cell']=='nebula_cpu_npu_top' and read('build/gds/geometry_comparison.json')['status']=='passed',
           'Streamed from read-only final ODB via byte-identical regenerated DEF; top/master multiplicities/port labels match; all GDS geometry equals accepted upstream export. AC-POWER-AREA remains a blocking dependency.',
           ['build/gds/readability.json','build/gds/port_boundary.json','build/gds/geometry_comparison.json','build/gds/preservation.json','build/gds/result_summary.json','build/gds/nebula_cpu_npu_top.gds'],origin='newly executed')

for cid,reason,ev in [
    ('AC-DELIVERY','Verifier measured and validated the operator-delivered root contract previously; actual delivered root byte object and delivery manifest are absent from these four captured inputs. Their hash/report alone cannot prove current retrievability.',['reports/verification/delivery.json','reports/verification/delivery-checker-tests.json']),
    ('AC-ORIGINAL','Original-source/checker inventory is retained, but full mapped synthesis confirmation is not directly delivered in this authorized read scope. An upstream Gate receipt alone does not close all original-implementation requirements.',['reports/verification/structure/summary.json','reports/pnr/upstream_receipts.json']),
    ('AC-SYNTHESIS','Mapped netlist and synthesis summary/Gate receipt are available via PnR; raw synthesis structural, cell/blackbox and state-to-netlist evidence is outside this task read scope and not reproduced here. Full checkpoint remains pending.',['build/pnr/results/1_2_yosys.v','reports/pnr/upstream_receipts.json','reports/pnr/equivalence_state_audit.json']),
    ('AC-RESOURCES',prior['AC-RESOURCES']['reason'],prior['AC-RESOURCES']['evidence']),
    ('AC-EVALUATOR-RELEASE',prior['AC-EVALUATOR-RELEASE']['reason'],prior['AC-EVALUATOR-RELEASE']['evidence']),
    ('AC-POWER-AREA','Final area accounting is available, but DOT64/GEMM8/CONV3 post-route workload execution and activity windows are absent. Report-only power unavailability is allowed; mandatory final-design functional reruns are not waived.',['reports/pnr/area_and_fanout.json','reports/performance/workloads.json','build/gds/power_area.json'])]:
    by_id[cid].update(verdict='deferred',execution_status='PENDING',reason=reason,evidence=ev)

area=read('reports/pnr/area_and_fanout.json')
write('power_area.json',dict(schema_version=1,status='partial',snapshot_id=snapshot['snapshot_id'],area=area,
                           die_area_um2=metrics['design.die_area'],core_area_um2=geo['actual_core_area_um2'],mapped_area_um2=audit['mapped_area_um2'],
                           workloads=[dict(workload=w,postroute_functional_status='not_run',cycles=None,activity_window=None,annotation_coverage=None,dynamic_mW=None,leakage_mW=None,total_mW=None,
                                           reason='No final-design gate workload execution or eligible activity/model binding supplied; this scope authorizes no functional simulator.') for w in ['DOT64','GEMM8','CONV3']]))
by_id['AC-PROJECT-COMPLETION'].update(verdict='failed',execution_status='FAIL',result_origin='new audit',
                                    reason='Mandatory pending checkpoints and unproven typed adapter results prevent whole-project acceptance.',
                                    evidence=['build/gds/project_acceptance.json','build/gds/adapter_audit.json','build/gds/requirements_audit.json'])

# Preserve each frozen checkpoint and requirement; do not turn declarations into executed adapters.
adapters=[]
contract_rows={c['contract_id']:c for c in read('reports/verification/contract-bindings.json')}
for obligation in plan['plan']['adapter_obligations']:
    c=contract_rows[obligation['contract_id']]
    pending=[i for i in c['check_results'] if by_id[i]['verdict']!='passed']
    adapters.append(dict(contract_id=c['contract_id'],requirement_ids=obligation['requirement_ids'],frozen_interface=c['frozen_interface'],
                         check_ids=c['check_results'],nonpassing_checks=pending,
                         execution_status='PENDING',verdict='deferred',
                         reason='Upstream contract bindings declare typed interfaces and link measured check evidence; no separately retrievable per-operand adapter result is proven by this audit. '+('Mandatory linked checks remain nonpassing.' if pending else 'Linked checks pass in their stated scope.'),
                         evidence=['reports/verification/contract-bindings.json','reports/verification/traceability.json']))
delivery=read('reports/verification/delivery.json')
authority=next(c for c in adapters if c['contract_id']=='SPEC_AUTHORITY')
authority.update(reason='Prior verifier delivery measurement is preserved, but actual byte object and manifest are not captured here; current direct operand verification is pending.',
                 prior_measurement=contract_rows['SPEC_AUTHORITY']['measurement'],
                 unavailable_objects=[delivery['path'],delivery['manifest']],evidence=['reports/verification/delivery.json'])
write('adapter_audit.json',adapters)
requirements=[]
for req in sorted(plan['requirement_ids']):
    linked=[c for c in by_id.values() if req in c['requirement_ids']]
    assert linked,req
    check_pass=all(c['verdict']=='passed' for c in linked)
    linked_adapters=[a for a in adapters if req in a['requirement_ids']]
    requirements.append(dict(id=req,verdict='passed' if check_pass and all(a['verdict']=='passed' for a in linked_adapters) else 'deferred',
                             check_evidence_verdict='passed' if check_pass else 'deferred',
                             check_ids=[c['id'] for c in linked],nonpassing_checks=[c['id'] for c in linked if c['verdict']!='passed'],
                             adapter_ids=[a['contract_id'] for a in linked_adapters],
                             evidence=sorted({e for c in linked for e in c['evidence']}),snapshot_id=snapshot['snapshot_id']))
assert len(requirements)==443 and len(by_id)==48 and len(adapters)==26
write('requirements_audit.json',requirements)
evidence={e for c in by_id.values() for e in c['evidence'] if e!='build/gds/project_acceptance.json'}
for e in evidence: assert (root/e).is_file(),e
for c in by_id.values():
    c['nonpassing_dependencies']=[i for i in c['dependencies'] if by_id[i]['verdict']!='passed']
    c['evidence_sha256']={e:sha(e) for e in c['evidence'] if e!='build/gds/project_acceptance.json'}
counts=collections.Counter(c['verdict'] for c in by_id.values())
gaps=['AC-DELIVERY','AC-ORIGINAL','AC-SYNTHESIS','AC-RESOURCES','AC-EVALUATOR-RELEASE','AC-POWER-AREA','AC-PROJECT-COMPLETION']
adapter_proven=sum(a['verdict']=='passed' for a in adapters)
limitations=['FEOL DRC disabled in frozen deck; general metal density not covered beyond vpp overlap rules.',
             'Only Sky130HD tt_025C_1v80 nominal 100 ns scenario; no multi-corner STA/foundry signoff.',
             'Independent ERC, EM/IR, pad/package qualification and foundry authorization unavailable.',
             'Full RTL-to-synthesis formal equivalence was not supplied; mapped-to-post-route equivalence is retained.',
             'No fabricated-silicon evidence or tapeout.release/signoff claim. Negative GDS files are deliberate corruptions for checker tests only.']
result=dict(schema_version=1,verdict='failed',engineering_verdict='failed',accepted=False,publishable=False,
            summary=f'GDS export and installed-scope DRC/device LVS/negative controls passed; project audit fails: {counts["passed"]}/48 checks pass, {counts["deferred"]} mandatory checks pending and {26-adapter_proven} typed adapter results not proven.',
            scope='Frozen installed-scope project acceptance; no formal tapeout release',snapshot_id=snapshot['snapshot_id'],
            acceptance_artifact_id=acceptance['id'],acceptance_commit=acceptance['content']['commit'],spec_digest=plan['spec_digest'],
            constraints_revision=2,constraints_sha256=plan['plan']['physical_revision']['constraints_sha256'],
            counts=dict(total=48,passed=counts['passed'],deferred=counts['deferred'],failed=counts['failed'],requirements_total=443,
                        requirements_with_passing_check_evidence=sum(r['check_evidence_verdict']=='passed' for r in requirements),requirements_accepted=sum(r['verdict']=='passed' for r in requirements),adapters_total=26,adapters_execution_proven=adapter_proven),
            checks=list(by_id.values()),blocking_checks=gaps,adapter_audit='build/gds/adapter_audit.json',requirements_audit='build/gds/requirements_audit.json',
            limitations=limitations,upstream_binding='build/gds/upstream_binding.json',functional_summary=read('reports/verification/result_summary.json'),
            coverage=read('reports/verification/coverage.json')['measures'],tool_identity='build/gds/tool_identity.json')
write('project_acceptance.json',result)
lines=['# Frozen project acceptance audit','',result['summary'],'','**Verdict: FAILED / NOT ACCEPTED.** Export success is not signoff or tapeout release.','',
       f'Final snapshot: `{snapshot["snapshot_id"]}`. Frozen acceptance revision 2, constraints revision 2, unchanged signed specification.','',
       '| Check | Result | Evidence / reason |','|---|---|---|']
for c in by_id.values():
    lines.append(f'| {c["id"]} | {c["execution_status"]} | {c["reason"].replace("|","/")} Evidence: '+', '.join(c['evidence'][:2])+' |')
lines+=['',f'26 required adapters are explicitly listed in adapter_audit.json; {adapter_proven} has direct operand execution proof. Typed declarations/check links alone are not counted as proven per-operand adapter execution. All 443 requirement rows are retained in requirements_audit.json. Check-level passing evidence does not imply project requirement closure.','','Remaining scope limitations:','']+['- '+s for s in limitations]
(out/'project_acceptance.md').write_text('\n'.join(lines)+'\n')
assert result['verdict']=='failed' and result['accepted'] is False and all(by_id[i]['verdict']!='passed' for i in gaps)
print(result['summary'])
