from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
from chip_nebula.gates import PostRouteConsistencyGate, MetricCheckGate, FileCheckGate
from chip_nebula.models.task_manifest import ExitCriterion

root = Path(__file__).resolve().parents[2]
folder = root / 'reports/pnr'
reports = []
criterion = ExitCriterion(type='post_route_consistency',source='reports/pnr/post_route_export_consistency.json',threshold=1e-6,error_class='post_route_export_mismatch',on_failure='retry')
reports.append(dict(name='post-route-export-consistency',report=asdict(PostRouteConsistencyGate().check(criterion,root))))
for name,metric,op,value,error in [('post-route-setup-closure','timing.setup_slack','>=',0,'physical_timing_violation'),
                                   ('post-route-hold-closure','timing.hold_slack','>=',0,'physical_timing_violation'),
                                   ('detailed-route-drc-clean','drc.violations','<=',0,'physical_drc_violation'),
                                   ('antenna-clean','antenna.violations','<=',0,'physical_antenna_violation')]:
    criterion = ExitCriterion(type='metric_check',source='reports/pnr/result_summary.json',metric=metric,operator=op,threshold=value,error_class=error,on_failure='retry')
    reports.append(dict(name=name,report=asdict(MetricCheckGate().check(criterion,root))))
summary = json.loads((folder / 'summary_gate.json').read_text())
reports.append(dict(name='pnr-result-summary',report=dict(passed=summary['exit_code']==0,evidence=summary['evidence'],details=summary)))
checks = {
    'connectivity':json.loads((folder / 'final_connectivity.json').read_text())['status']=='passed',
    'equivalence':json.loads((folder / 'equivalence.json').read_text())['status']=='passed',
    'actual_gds_masters':json.loads((folder / 'gds_master_audit.json').read_text())['status']=='passed',
    'independent_decks':json.loads((folder / 'independent_decks.json').read_text())['status']=='passed',
    'electrical':all(v==0 for v in json.loads((folder / 'electrical.json').read_text())['violations'].values()),
    'external_reset_waveform':json.loads((folder / 'external_reset_dependency.json').read_text())['status']=='passed',
    'placement_geometry':json.loads((folder / 'placement_geometry/geometry_acceptance.json').read_text())['status']=='passed',
    'frozen_geometry':json.loads((folder / 'geometry_acceptance.json').read_text())['status']=='passed',
    'all_orfs_commands_completed':all(x.get('exit_code')==0 or x.get('resolved_by_command_index') is not None for x in json.loads((folder / 'commands.json').read_text())),
}
passed=all(r['report']['passed'] for r in reports) and all(checks.values())
status=json.loads((folder / 'execution_status.json').read_text())
status.update(status='succeeded' if passed else 'failed',completed=passed,flow_snapshot_completed=checks['all_orfs_commands_completed'],acceptance_completed=passed,exit_code=0 if passed else 1,
              completed_at=datetime.now(timezone.utc).isoformat(),closure_checks=checks,
              delivery_snapshot='reports/pnr/delivery_snapshot.json',
              final_database='build/pnr/results/6_final.odb',
              post_route_netlist_paths=['build/pnr/results/6_final.sta.v'],
              parasitic_paths=['build/pnr/results/6_final.spef','build/pnr/results/6_final.sdf'],
              connectivity_evidence='reports/pnr/final_connectivity.json',antenna_evidence='reports/pnr/final_antenna.json',
              evidence=['reports/pnr/commands.json','reports/pnr/5_2_route.log','reports/pnr/finish.log',
                        'reports/pnr/post_route_export_consistency.json','reports/pnr/final_connectivity.json',
                        'reports/pnr/final_antenna.json','reports/pnr/independent_decks.json',
                        'reports/pnr/equivalence.json','reports/pnr/exit_gates.json'],
              reason='Completed physical engineering checks; no tapeout-release claim.' if passed else 'Physical closure or frozen acceptance checks failed; inspect closure_checks and direct evidence. Layout is not publishable.')
(folder / 'execution_status.json').write_text(json.dumps(status,indent=2)+'\n')
criterion=ExitCriterion(type='file_check',paths=['reports/pnr/execution_status.json'],min_files=1,error_class='pnr_evidence_missing',on_failure='retry')
reports.append(dict(name='execution-status',report=asdict(FileCheckGate().check(criterion,root))))
(folder / 'exit_gates.json').write_text(json.dumps(dict(schema_version=1,passed=passed,gates=reports,additional_engineering_checks=checks),indent=2)+'\n')
print(json.dumps(dict(passed=passed,gates=reports,additional_engineering_checks=checks),indent=2))
raise SystemExit(0 if passed else 1)
