import json
import os
from pathlib import Path
import shutil
import hashlib
import re
from datetime import datetime, timezone


def save(stage, source, next_stage, event_metrics=None):
    source = source.resolve()
    root = Path(__file__).resolve().parents[2]
    folder = root / 'build/pnr/checkpoints'
    slots = [folder / f'slot-{s}.odb' for s in ('a', 'b')]
    slot = min(slots, key=lambda p: p.stat().st_mtime if p.exists() else 0)
    temp = slot.with_suffix('.odb.tmp')
    assert source.stat().st_size > 0
    shutil.copyfile(source, temp)
    with temp.open('rb') as f:
        os.fsync(f.fileno())
    temp.replace(slot)
    audit = json.loads((root / 'reports/pnr/input_audit.json').read_text())
    metrics = {}
    prefixes={'floorplan':'2_', 'place':'3_', 'cts':'4_', 'grt':'5_1_',
              '5_2_route':'5_2_', 'route':'5_3_', 'finish':'6_'}
    if stage in prefixes:
        for p in sorted((root / 'reports/pnr/logs').glob(prefixes[stage]+'*.json')):
            metrics.update(json.loads(p.read_text()))
    if stage=='final_export':
        for p in (root / 'reports/pnr/database_timing.json', root / 'reports/pnr/physical_checks.json'):
            if p.exists(): metrics.update(json.loads(p.read_text()))
    if stage in ('detailed_route','antenna_legalized'):
        log=root/'reports/pnr/5_2_route.log'
        counts=re.findall(r'Number of violations = (\d+)',log.read_text()) if log.exists() else []
        if counts:
            metrics['last_completed_route_drc_violations']=int(counts[-1])
            metrics['drc_violations']=int(counts[-1]) if stage=='detailed_route' else None
        metrics['timing_scope']='Not re-extracted at this checkpoint; final STA remains required.'
    if event_metrics: metrics.update(event_metrics)
    summary=root / 'reports/pnr/result_summary.json'
    if stage=='final_export' and summary.exists():
        for metric in json.loads(summary.read_text())['metrics']:
            if metric['status']=='measured':metrics[metric['id']]=metric['value']
    metadata = dict(schema_version=1, active_slot=str(slot.relative_to(root)), stage=stage,
                    created_at=datetime.now(timezone.utc).isoformat(), tool_version=audit['tool_version'],
                    tool_identity=audit.get('tool_identity'),
                    inputs=audit['inputs'], metrics=metrics, odb_sha256=hashlib.sha256(slot.read_bytes()).hexdigest(),
                    restore_command=('python3 -B build/pnr/export_and_sta.py --restore' if stage=='final_export' else f'python3 -B build/pnr/run.py --restore --from-stage {next_stage}'),
                    script_entry=('build/pnr/export_and_sta.py' if stage=='final_export' else 'build/pnr/run.py'), source_database=str(source.relative_to(root)))
    if stage in ('detailed_route','antenna_legalized'):
        metadata['restore_database']='build/pnr/results/4_cts.odb'
        metadata['restore_command']='python3 -B build/pnr/run.py --restore --rebuild --from-stage grt'
    temp = folder / 'latest.json.tmp'
    temp.write_text(json.dumps(metadata, indent=2) + '\n')
    temp.replace(folder / 'latest.json')


def restore():
    root = Path(__file__).resolve().parents[2]
    data = json.loads((root / 'build/pnr/checkpoints/latest.json').read_text())
    slot = root / data['active_slot']
    assert hashlib.sha256(slot.read_bytes()).hexdigest()==data['odb_sha256'], 'Checkpoint digest mismatch'
    shutil.copyfile(slot, root / data.get('restore_database',data['source_database']))


if __name__=='__main__':
    import sys
    stage, source, count, antenna = sys.argv[1:]
    assert stage in ('detailed_route','antenna_legalized')
    save(stage,Path(source),'grt',dict(instance_count=int(count),antenna_violations=int(antenna)))
