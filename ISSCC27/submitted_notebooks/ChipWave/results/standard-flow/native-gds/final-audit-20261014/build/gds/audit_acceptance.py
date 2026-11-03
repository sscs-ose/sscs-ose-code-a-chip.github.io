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
context=read('.nebula_inputs/attempt-context.json')
layout=read('.nebula_inputs/'+context['input_deliveries']['layout']+'/artifact.json')
synth_base=Path('.nebula_inputs/artifact-0b514721fd8641408ffcec0d7f4350ec')
synthesis=read(str(synth_base/'artifact.json'))
delivery_base=Path('.nebula_inputs/authorized-root-project-delivery')
delivery_record=read(str(delivery_base/'artifact.json'))
delivery_root=delivery_base/'delivery/standard-project'
delivery_manifest=read(str(delivery_root/'project-delivery.manifest.json'))
assert hashlib.sha256(delivery_record['payload']['content'].encode()).hexdigest()==delivery_record['payload']['content_digest'].removeprefix('sha256:')
plan=acceptance['payload']
snapshot=read('reports/pnr/delivery_snapshot.json')
assert layout['payload']['snapshot_id']==snapshot['snapshot_id']
assert verification['payload']['spec_digest']==plan['spec_digest']
assert read('reports/pnr/input_audit.json')['spec_digest']==plan['spec_digest']
assert read('reports/verification/baseline-revalidation.json')['verdict']=='passed'
assert sha('spec/acceptance.plan.yaml')=='ec381baedf0e96f4d3546966afd47b238e7f8a65b758a3093d316507a1409861'

# Verify captured Git objects as well as manifest hashes; filenames alone are insufficient.
bindings=[]
for rec,base in [(acceptance,Path('.')),(verification,Path('.')),(layout,Path('.')),
                 (read('.nebula_inputs/artifact-971f6c7042664af69515024a25a72bc2/artifact.json'),Path('.')),
                 (synthesis,synth_base),(delivery_record,delivery_base)]:
    paths=rec['content']['paths'] if rec!=delivery_record else [
        'project-delivery.manifest.json','delivery/standard-project/project-delivery.manifest.json',
        'delivery/standard-project/t09-base-contract.md','delivery/standard-project/spec/acceptance.md',
        *['delivery/standard-project/'+p for p in delivery_manifest['rtl_sha256']]]
    raw=subprocess.check_output(['git','ls-tree','-r','-z',rec['content']['commit'],'--',*paths],cwd=root)
    blobs={row.split(b'\t',1)[1].decode():row.split(b'\t',1)[0].split()[2].decode() for row in raw.split(b'\0') if row}
    for path in paths:
        p=root/base/path
        h=hashlib.sha1(f'blob {p.stat().st_size}\0'.encode())
        with p.open('rb') as f:
            for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
        assert h.hexdigest()==blobs[path],path
    bindings.append(dict(artifact_id=rec['id'],commit=rec['content']['commit'],base_path=str(base),files_checked=len(paths),status='passed'))
manifest=read('reports/verification/evidence-manifest.json')
for row in manifest['files']:
    path=row['path']
    assert path.startswith(('reports/verification/','reports/performance/')),path
    assert sha(path)==row['sha256'] and (root/path).stat().st_size==row['bytes'],path
assert all(sha(p)==h for p,h in snapshot['files'].items())
assert read('build/gds/reuse_validation.json')['status']=='passed'
assert read('build/gds/current_klayout_identity.json')['status']=='passed'
source_sha=sha('spec/source-contract.md')
source_suffix=b''.join((root/'spec/source-contract.md').read_bytes().splitlines(keepends=True)[18:])
base_path=str(delivery_root/'t09-base-contract.md')
manifest_path=str(delivery_root/'project-delivery.manifest.json')
actual_base=(root/base_path).read_bytes()
assert (root/base_path).is_file() and not (root/base_path).is_symlink()
assert actual_base==source_suffix and len(actual_base)==6930
assert sha(base_path)==delivery_manifest['root_contract']['sha256']=='1021e4b88446ed12c7b6a3cc6f46847f16a44c70a47660fff24f5f91ca778958'
assert source_sha==delivery_manifest['root_contract']['source_sha256']
assert sha(str(delivery_root/'spec/acceptance.md'))==sha('spec/acceptance.md')==delivery_manifest['companion_acceptance']['sha256']
rtl_binding={r['path']:r['sha256'] for r in read('reports/verification/evidence-reuse.json')['rtl_source_binding']}
assert rtl_binding==delivery_manifest['rtl_sha256']
for path,h in rtl_binding.items():
    assert sha(str(delivery_root/path))==sha(str(synth_base/path))==h,path
    assert delivery_manifest['content_files_sha256'][path]==h,path
synth_report=read(str(synth_base/'reports/synthesis/report.json'))
synth_baseline=read(str(synth_base/'reports/synthesis/baseline_revalidation.json'))
assert synth_baseline['spec_digest']==plan['spec_digest'] and synth_baseline['acceptance_revision']==2 and synth_baseline['constraints_revision']==2
assert {r['path']:r['sha256'] for r in synth_baseline['rtl_checks']}==rtl_binding
assert sha(str(synth_base/'build/synth/nebula_cpu_npu_top.v'))==sha('build/pnr/results/1_2_yosys.v')==synth_report['netlist_sha256']
cells=read(str(synth_base/'reports/synthesis/cell_audit.json'))
mapped=read(str(synth_base/'build/synth/mapped.json'))['modules']['nebula_cpu_npu_top']
assert dict(collections.Counter(c['type'] for c in mapped['cells'].values()))==cells['counts']
assert len(mapped['cells'])==cells['standard_cell_count']==16683 and cells['macro_count']==cells['latch_count']==0
assert cells['all_used_cells_in_liberty_lef_gds_cdl'] and not cells['forbidden_cells'] and not cells['unmapped_cells']
assert {p:{'direction':v['direction'],'width':len(v['bits'])} for p,v in mapped['ports'].items()}==cells['ports']
structure=read(str(synth_base/'reports/synthesis/structure_audit.json'))
assert len(structure['rf_sequential_cells'])==1024 and all(g['count']>0 for g in structure['pipeline_groups'].values())
assert all(read(str(synth_base/'reports/synthesis'/name))['verdict']=='passed' for name in [
    'structure_audit.json','cell_audit.json','input_audit.json','baseline_revalidation.json','memory_mapping.json','timing_audit.json','warnings.json','gates.json'])
assert synth_report['measured']['setup_slack_ns']>=0
write('delivery_synthesis_revalidation.json',dict(status='passed',snapshot_id=snapshot['snapshot_id'],
    delivery=dict(artifact_id=delivery_record['id'],base_path=base_path,bytes=len(actual_base),sha256=sha(base_path),
                  manifest_path=manifest_path,manifest_sha256=sha(manifest_path),source_sha256=source_sha,
                  source_suffix_equal=True,companion_equal=True,rtl_sha256=rtl_binding,
                  scope='Relevant root contract/manifest/RTL only; historical root-delivery physical settings not used.'),
    synthesis=dict(artifact_id=synthesis['id'],commit=synthesis['content']['commit'],mapped_sha256=synth_report['netlist_sha256'],
                   source_identical=True,standard_cells=len(mapped['cells']),macro_count=0,latch_count=0,rf_flops=1024,
                   evidence=[str(synth_base/f) for f in ['reports/synthesis/report.json','reports/synthesis/structure_audit.json','reports/synthesis/cell_audit.json','reports/synthesis/baseline_revalidation.json']]),
    result_origin='Existing immutable native owner evidence independently revalidated; no synthesis/functional rerun.'))
write('upstream_binding.json',dict(status='passed',git_artifacts=bindings,
                                 verification_manifest_files_checked=len(manifest['files']),
                                 snapshot_id=snapshot['snapshot_id'],functional_evidence_origin='reused qualified verifier execution',
                                 evidence_reuse='reports/verification/evidence-reuse.json',
                                 captured_feedback='build/gds/delivery_synthesis_revalidation.json',
                                 physical_export_reuse='build/gds/reuse_validation.json',
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

set_result('AC-DELIVERY',True,'Actual native 6930-byte root contract equals frozen source lines19..EOF; regular path, manifest, companion and source-identical RTL directly revalidated. Prior missing-input audit is preserved.',
           [base_path,manifest_path,'spec/source-contract.md','build/gds/delivery_synthesis_revalidation.json'])
set_result('AC-ORIGINAL',True,'Qualified verifier source/checker lineage and unchanged RTL inventory are now joined to the real captured synthesizable V2 mapped design; no new originality or reference-release claims inferred.',
           ['reports/verification/structure/summary.json','reports/verification/fixed-final.json','reports/verification/baseline-revalidation.json',str(synth_base/'reports/synthesis/baseline_revalidation.json'),'build/gds/delivery_synthesis_revalidation.json'])
set_result('AC-SYNTHESIS',True,'Source-identical frozen V2 mapping directly checked: 16683 characterized cells, no macro/latch/unmapped/forbidden cells, exact ports, 1024 RF flops and nonempty pipeline/NPU state groups. Existing synthesis/STA logs pass; full formal RTL equivalence remains unexecuted.',
           [str(synth_base/f) for f in ['build/synth/nebula_cpu_npu_top.v','build/synth/mapped.json','reports/synthesis/report.json','reports/synthesis/structure_audit.json','reports/synthesis/cell_audit.json','reports/synthesis/memory_mapping.json','reports/synthesis/timing_audit.json','reports/synthesis/yosys.log','reports/synthesis/sta.log','reports/synthesis/tool_identity.json','reports/synthesis/gates.json']])

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
           ['build/gds/checks.json','build/gds/drc.lyrdb','build/gds/lvs.lvsdb','build/gds/extracted.cir','build/gds/commands.json','build/gds/resources.json','build/gds/negative/mutations.json','build/gds/negative/drc_width.lyrdb','build/gds/negative/lvs_missing_gate.lvsdb','build/gds/reuse_validation.json'],origin='reused completed prior attempt; exact binding revalidated')
readable=read('build/gds/readability.json')
set_result('AC-GDS',readable['readable'] and readable['bytes']>0 and readable['top_cell']=='nebula_cpu_npu_top' and read('build/gds/geometry_comparison.json')['status']=='passed',
           'Streamed from read-only final ODB via byte-identical regenerated DEF; top/master multiplicities/port labels match; all GDS geometry equals accepted upstream export. AC-POWER-AREA remains a blocking dependency.',
           ['build/gds/readability.json','build/gds/port_boundary.json','build/gds/geometry_comparison.json','build/gds/preservation.json','build/gds/result_summary.json','build/gds/nebula_cpu_npu_top.gds','build/gds/reuse_validation.json'],origin='reused completed prior attempt; exact binding revalidated')

for cid,reason,ev in [
    ('AC-EVALUATOR-RELEASE','Full source-bound known-reference hazard/exception/handshake evaluator-owner release audit is absent. Parent common-checker replay and three preset NPU faults do not satisfy this obligation.',['reports/verification/downstream-obligations.json','build/gds/operator_feedback.json']),
    ('AC-POWER-AREA','PnR owner supplied exact-snapshot area/model/program/expected-output inventories. All three final-design workload runs/activity remain unavailable; report-only power unavailability cannot waive mandatory functional execution.',['reports/pnr/power_area.json','reports/pnr/power_area/input_inventory.json','reports/pnr/power_area/model_inventory.json','reports/pnr/power_area/DOT64.json','reports/pnr/power_area/GEMM8.json','reports/pnr/power_area/CONV3.json','build/gds/power_area.json'])]:
    by_id[cid].update(verdict='deferred',execution_status='PENDING',reason=reason,evidence=ev)

write('operator_feedback.json',dict(source='.nebula_inputs/attempt-context.json',source_sha256=sha('.nebula_inputs/attempt-context.json'),work_items=context['work_items']))
resource_item=next(w for w in context['work_items'] if w['id']=='work-c655d44e66df41a0be62929047fefc23')
assert 'already exceeds 2h' in resource_item['summary']
write('resource_audit.json',dict(verdict='failed',wall_time_budget_seconds=7200,observed_budget_exceeded=True,
    exact_elapsed_seconds=None,peak_ram_bytes=None,peak_writable_disk_bytes=None,cumulative_tokens=None,
    observation_source='Captured operator observation in work-c655d44e66df41a0be62929047fefc23; exact values unavailable, not invented.',
    evidence=['build/gds/operator_feedback.json','reports/verification/downstream-obligations.json'],
    history_policy='Historical development exceedance cannot be erased by a new run.'))
set_result('AC-RESOURCES',False,'Captured operator observation confirms historical standard RTL development exceeds frozen 2h budget. Historical peak RAM/disk, cumulative tokens/allocation receipts remain unavailable; no retrospective rerun can erase the failure.',
           ['build/gds/resource_audit.json','build/gds/operator_feedback.json','reports/verification/downstream-obligations.json'],origin='captured operator observation plus availability audit')
power=read('reports/pnr/power_area.json')
assert power['snapshot_id']==snapshot['snapshot_id'] and power['database_sha256']==snapshot['files']['build/pnr/results/6_final.odb']
assert power['netlist_sha256']==snapshot['files']['build/pnr/results/6_final.sta.v'] and power['spef_sha256']==snapshot['files']['build/pnr/results/6_final.spef']
assert {w['workload'] for w in power['workloads']}=={'DOT64','GEMM8','CONV3'}
for workload in power['workloads']:
    for obj in workload['inputs']: assert sha(obj['path'])==obj['sha256'],obj['path']
    assert read('build/pnr/power_area/'+workload['workload']+'/expected_outputs.json')==workload['expected_outputs']
    assert workload['functional_status']==workload['activity_status']=='unavailable'
write('power_area.json',dict(schema_version=1,status='unavailable',engineering_verdict='unavailable',
    snapshot_id=snapshot['snapshot_id'],source='reports/pnr/power_area.json',source_sha256=sha('reports/pnr/power_area.json'),
    workloads=power['workloads'],measured_area=power['measured_area'],conditions=power['conditions'],
    model_inventory='reports/pnr/power_area/model_inventory.json',input_inventory='reports/pnr/power_area/input_inventory.json',
    reason='Existing owner inventory and qualified workload objects revalidated; no granted gate runtime/source-matched harness or eligible activity. No RTL/vectorless substitution.'))
by_id['AC-PROJECT-COMPLETION'].update(verdict='failed',execution_status='FAIL',result_origin='new audit',
                                    reason='Historical resource failure, pending evaluator release/power-area and unproven typed adapters prevent whole-project acceptance.',
                                    evidence=['build/gds/project_acceptance.json','build/gds/adapter_audit.json','build/gds/requirements_audit.json'])

for c in by_id.values(): c['acceptance_verdict']=c['verdict']
for _ in by_id:
    for c in by_id.values():
        if c['acceptance_verdict']=='passed' and any(by_id[i]['acceptance_verdict']!='passed' for i in c['dependencies']):
            c['acceptance_verdict']='deferred'

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
authority.update(verdict='passed',execution_status='PASS',reason='Nine typed delivery operands evaluated from actual native bytes/regular path/source suffix/companion/manifest; no declaration-only PASS.',
    operands=dict(frozen_source_digest=int(source_sha,16),frozen_base_digest=int(hashlib.sha256(source_suffix).hexdigest(),16),
                  delivered_file_digest=int(sha(base_path),16),delivered_file_bytes=len(actual_base),delivery_manifest_digest=int(sha(manifest_path),16),
                  delivered_file_exists=(root/base_path).is_file(),correct_delivery_path=delivery_manifest['root_contract']['path']=='t09-base-contract.md',
                  base_bytes_equal=actual_base==source_suffix,
                  base_delivery_pass=(actual_base==source_suffix and len(actual_base)==6930 and (root/base_path).is_file()
                      and not (root/base_path).is_symlink() and sha(base_path)==delivery_manifest['root_contract']['sha256']
                      and source_sha==delivery_manifest['root_contract']['source_sha256'])),
    evidence=[base_path,manifest_path,'spec/source-contract.md','build/gds/delivery_synthesis_revalidation.json'])
assert set(authority['operands'])==set(authority['frozen_interface'])
for key,value in authority['operands'].items():
    typ=authority['frozen_interface'][key]['type']
    assert (type(value) is bool) if typ['kind']=='bit' else (type(value) is int and 0<=value<2**typ['width'])
next(a for a in adapters if a['contract_id']=='PROJECT_RESOURCES').update(verdict='failed',execution_status='FAIL',
    reason=by_id['AC-RESOURCES']['reason'],evidence=by_id['AC-RESOURCES']['evidence'])
write('adapter_audit.json',adapters)
requirements=[]
for req in sorted(plan['requirement_ids']):
    linked=[c for c in by_id.values() if req in c['requirement_ids']]
    assert linked,req
    check_pass=all(c['acceptance_verdict']=='passed' for c in linked)
    linked_adapters=[a for a in adapters if req in a['requirement_ids']]
    failed=any(c['acceptance_verdict']=='failed' for c in linked) or any(a['verdict']=='failed' for a in linked_adapters)
    requirements.append(dict(id=req,verdict='failed' if failed else ('passed' if check_pass and all(a['verdict']=='passed' for a in linked_adapters) else 'deferred'),
                             check_evidence_verdict='passed' if check_pass else 'deferred',
                             check_ids=[c['id'] for c in linked],nonpassing_checks=[c['id'] for c in linked if c['acceptance_verdict']!='passed'],
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
gaps=[c['id'] for c in by_id.values() if c['verdict']!='passed']
adapter_proven=sum(a['verdict']=='passed' for a in adapters)
limitations=['FEOL DRC disabled in frozen deck; general metal density not covered beyond vpp overlap rules.',
             'Only Sky130HD tt_025C_1v80 nominal 100 ns scenario; no multi-corner STA/foundry signoff.',
             'Independent ERC, EM/IR, pad/package qualification and foundry authorization unavailable.',
             'Full RTL-to-synthesis formal equivalence was not supplied; mapped-to-post-route equivalence is retained.',
             'No fabricated-silicon evidence or tapeout.release/signoff claim. Negative GDS files are deliberate corruptions for checker tests only.']
result=dict(schema_version=1,verdict='failed',engineering_verdict='failed',accepted=False,publishable=False,
            summary=f'Physical/export checks preserved as passed; whole-project verdict failed. Direct check outcomes: {counts["passed"]}/48 passed, {counts["deferred"]} pending, {counts["failed"]} failed. Typed adapters: {adapter_proven}/26 proven; no acceptance override.',
            scope='Frozen installed-scope project acceptance; no formal tapeout release',snapshot_id=snapshot['snapshot_id'],
            acceptance_artifact_id=acceptance['id'],acceptance_commit=acceptance['content']['commit'],spec_digest=plan['spec_digest'],
            constraints_revision=2,constraints_sha256=plan['plan']['physical_revision']['constraints_sha256'],
            physical_export_acceptance=dict(verdict='passed',scope='Unchanged accepted single-corner physical implementation and GDS installed-scope DRC/device LVS/negative controls; excludes workload/power and whole-project acceptance.',
                                            evidence=['build/gds/reuse_validation.json','reports/pnr/power_area/gate_preflight.json','build/gds/checks.json']),
            whole_project_acceptance=dict(verdict='failed',blocking_checks=gaps,reason='Historical resource exceedance plus unresolved mandatory owner evidence.'),
            prior_audit='build/gds/history/attempt-7c5b8dafd74c4a8aa0b22ba361d3a618/project_acceptance.json',
            counts=dict(total=48,passed=counts['passed'],deferred=counts['deferred'],failed=counts['failed'],requirements_total=443,
                        acceptance_qualified_checks=sum(c['acceptance_verdict']=='passed' for c in by_id.values()),requirements_with_passing_check_evidence=sum(r['check_evidence_verdict']=='passed' for r in requirements),requirements_accepted=sum(r['verdict']=='passed' for r in requirements),adapters_total=26,adapters_execution_proven=adapter_proven),
            checks=list(by_id.values()),blocking_checks=gaps,adapter_audit='build/gds/adapter_audit.json',requirements_audit='build/gds/requirements_audit.json',
            limitations=limitations,upstream_binding='build/gds/upstream_binding.json',functional_summary=read('reports/verification/result_summary.json'),
            coverage=read('reports/verification/coverage.json')['measures'],tool_identity='build/gds/tool_identity.json')
write('project_acceptance.json',result)
lines=['# Frozen project acceptance audit','',result['summary'],'','**Physical/export engineering: PASSED. Whole-project acceptance: FAILED / NOT ACCEPTED.** Export success is not signoff or tapeout release.','',
       f'Final snapshot: `{snapshot["snapshot_id"]}`. Frozen acceptance revision 2, constraints revision 2, unchanged signed specification.','',
       '| Check | Direct result | Acceptance result | Evidence / reason |','|---|---|---|---|']
for c in by_id.values():
    lines.append(f'| {c["id"]} | {c["execution_status"]} | {c["acceptance_verdict"]} | {c["reason"].replace("|","/")} Evidence: '+', '.join(c['evidence'][:2])+' |')
lines+=['',f'26 required adapters are explicitly listed in adapter_audit.json; {adapter_proven} has direct operand execution proof. Typed declarations/check links alone are not counted as proven per-operand adapter execution. All 443 requirement rows are retained in requirements_audit.json. Check-level passing evidence does not imply project requirement closure.','','Remaining scope limitations:','']+['- '+s for s in limitations]
(out/'project_acceptance.md').write_text('\n'.join(lines)+'\n')
assert result['verdict']=='failed' and result['accepted'] is False and all(by_id[i]['verdict']!='passed' for i in gaps)
assert by_id['AC-RESOURCES']['verdict']=='failed' and by_id['AC-GDS']['verdict']=='passed' and by_id['AC-GDS']['acceptance_verdict']=='deferred'
assert authority['verdict']=='passed' and by_id['AC-EVALUATOR-RELEASE']['verdict']!='passed'
print(result['summary'])
