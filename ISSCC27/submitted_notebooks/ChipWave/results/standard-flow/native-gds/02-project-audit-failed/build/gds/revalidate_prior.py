import hashlib
import json
from pathlib import Path
import subprocess

root=Path(__file__).resolve().parents[2]
out=root/'build/gds'
def read(path): return json.loads((root/path).read_text())
def sha(path):
    h=hashlib.sha256()
    with (root/path).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()
def write(name,data): (out/name).write_text(json.dumps(data,indent=2)+'\n')

history=out/'history/attempt-7c5b8dafd74c4a8aa0b22ba361d3a618'
if not history.exists():
    for row in (out/'SHA256SUMS').read_text().splitlines():
        h,p=row.split('  ',1)
        assert sha(p)==h,p
    history.mkdir(parents=True)
    saved={}
    for name in ['README.md','audit_acceptance.py','audit_acceptance.log','project_acceptance.json','project_acceptance.md',
                 'requirements_audit.json','adapter_audit.json','power_area.json','upstream_binding.json',
                 'exit_gates.json','gate_preflight.log','summary_gate.log','manifest.json','finalize.py','finalize.log','SHA256SUMS']:
        src=out/name
        (history/name).write_bytes(src.read_bytes())
        saved[str(src.relative_to(root))]=sha(str(src.relative_to(root)))
    write('history/attempt-7c5b8dafd74c4a8aa0b22ba361d3a618/archive.json',
          dict(workspace_commit='04658a99d4d2d1cb185a4bb5a887f683c43da315',files_sha256=saved,
               verdict='failed',reason='Mandatory evidence unavailable in prior capture; preserved without relabeling.'))

archive=read('build/gds/history/attempt-7c5b8dafd74c4a8aa0b22ba361d3a618/archive.json')
if not (history/'README.md').exists():
    (history/'README.md').write_bytes(subprocess.check_output(['git','show',archive['workspace_commit']+':build/gds/README.md'],cwd=root))
    archive['files_sha256']['build/gds/README.md']=sha(str((history/'README.md').relative_to(root)))
    write('history/attempt-7c5b8dafd74c4a8aa0b22ba361d3a618/archive.json',archive)

snapshot=read('reports/pnr/delivery_snapshot.json')
old=read('build/gds/input_snapshot.json')
assert old['snapshot_id']==snapshot['snapshot_id']
protected={p:h for p,h in old['files'].items() if p.startswith('build/pnr/') and p!='build/pnr/README.txt'}
assert all(sha(p)==h for p,h in protected.items())
assert all(sha(p)==h for p,h in snapshot['files'].items())
changed=[p for p,h in old['files'].items() if sha(p)!=h]
assert set(changed)=={'build/pnr/README.txt','reports/pnr/delivery_snapshot.json','reports/pnr/report.json'},changed
for row in (history/'SHA256SUMS').read_text().splitlines():
    h,p=row.split('  ',1)
    if p not in archive['files_sha256']:
        assert sha(p)==h,p
resources=read('build/gds/resources.json')
for view in resources['views']: assert sha(view['path'])==view['sha256'],view['name']
assert sha(str(Path(resources['flow'])/'util/def2stream.py'))==resources['def2stream_sha256']
identity=read('build/gds/tool_identity.json')
assert sha(identity['klayout_requested'])==identity['klayout_wrapper_sha256']
assert sha(identity['openroad_resolved'])==identity['openroad_sha256']
checks=read('build/gds/checks.json')
assert checks['status']=='passed' and checks['positive_drc']['violations']==0 and checks['positive_lvs']['matched']
assert checks['positive_lvs']['mos_extraction_present'] and not checks['negative_lvs']['matched']
gds=read('build/gds/readability.json')
assert sha('build/gds/nebula_cpu_npu_top.gds')==gds['sha256'] and gds['top_cell']=='nebula_cpu_npu_top'
assert sha('build/gds/final.def')==snapshot['files']['build/pnr/results/6_final.def']
assert read('build/gds/geometry_comparison.json')['status']=='passed'
write('reuse_validation.json',dict(status='passed',snapshot_id=snapshot['snapshot_id'],
    prior_workspace_commit='04658a99d4d2d1cb185a4bb5a887f683c43da315',
    reused=['stream-out','KLayout readability/top/master/ports','GDS geometry comparison','DRC','device-extracted LVS','negative controls'],
    origin='Completed prior attempt; exact input/output/resource/tool hashes revalidated, no rerun.',
    protected_database_files_checked=len(protected),changed_upstream_reports=changed,
    preserved_history=str(history.relative_to(root)),gds_sha256=gds['sha256'],
    original_commands='build/gds/commands.json',original_tool_identity='build/gds/tool_identity.json'))
current={str(p):sha(str(p)) for base in ['build/pnr','reports/pnr'] for p in (root/base).rglob('*') if p.is_file()}
# Normalize absolute discovery paths to workspace-relative names.
current={str(Path(p).relative_to(root)):h for p,h in current.items()}
write('current_input_snapshot.json',dict(snapshot_id=snapshot['snapshot_id'],files=current))
print('PRIOR_GDS_DECK_NEGATIVE_RESULTS_EXACT_REUSE_PASS',len(protected))
