import hashlib
import json
from pathlib import Path

root=Path(__file__).resolve().parents[2]
out=root/'build/gds'
def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def read(name):return json.loads((out/name).read_text())
inputs=read('current_input_snapshot.json')
assert all(sha(root/p)==h for p,h in inputs['files'].items())
checks=read('checks.json')
gds=read('readability.json')
assert checks['status']=='passed' and gds['readable'] and read('preservation.json')['status']=='passed'
result=dict(schema_version=1,type='gds',export_engineering_verdict='passed',project_engineering_verdict=read('project_acceptance.json')['verdict'],
            snapshot_id=inputs['snapshot_id'],gds_path='build/gds/nebula_cpu_npu_top.gds',gds_sha256=sha(out/'nebula_cpu_npu_top.gds'),
            gds_bytes=gds['bytes'],top_cell=gds['top_cell'],readability='build/gds/readability.json',
            layer_map='build/gds/layer_map.txt',technology='build/gds/streamout.lyt',
            actual_master_coverage='build/gds/readability.json',resources='build/gds/resources.json',
            port_boundary='build/gds/port_boundary.json',
            commands='build/gds/commands.json',input_artifacts='build/gds/input_records.json',
            klayout_runtime_identity='build/gds/klayout_runtime_identity.json',
            snapshot_preservation='build/gds/preservation.json',geometry_identity='build/gds/geometry_comparison.json',
            current_input_preservation='build/gds/current_input_snapshot.json',reuse_validation='build/gds/reuse_validation.json',
            current_klayout_identity='build/gds/current_klayout_identity.json',
            delivery_synthesis_revalidation='build/gds/delivery_synthesis_revalidation.json',
            original_export_inputs='build/gds/input_records.json',current_acceptance_inputs='build/gds/upstream_binding.json',
            prior_failed_audit='build/gds/history/attempt-7c5b8dafd74c4a8aa0b22ba361d3a618/project_acceptance.json',
            drc=dict(violations=checks['positive_drc']['violations'],report='build/gds/drc.lyrdb'),
            lvs=dict(matched=checks['positive_lvs']['matched'],extracted_devices=checks['positive_lvs']['extracted_device_count'],report='build/gds/lvs.lvsdb',netlist='build/gds/extracted.cir'),
            negative_controls=dict(evidence='build/gds/checks.json',files='build/gds/negative/',eligible_for_release=False),
            project_acceptance='build/gds/project_acceptance.json',gate_evidence='build/gds/exit_gates.json',checksums='build/gds/SHA256SUMS',
            signoff_status='not_released',scope=checks['scope'],formal_gaps=read('project_acceptance.json')['limitations'])
(out/'manifest.json').write_text(json.dumps(result,indent=2)+'\n')
files=sorted(p for p in out.rglob('*') if p.is_file() and p!=out/'SHA256SUMS')
(out/'SHA256SUMS').write_text(''.join(f'{sha(p)}  {p.relative_to(root)}\n' for p in files))
for row in (out/'SHA256SUMS').read_text().splitlines():
    h,p=row.split('  ',1)
    assert sha(root/p)==h
print('GDS_MANIFEST_CHECKSUMS_PRESERVATION_PASS',len(files))
