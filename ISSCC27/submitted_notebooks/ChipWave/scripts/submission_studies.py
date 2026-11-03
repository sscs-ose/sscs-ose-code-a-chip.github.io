"""Validate declared evidence roles in addition to the existing primary-study checks."""
import hashlib
import json
from pathlib import Path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def checked(root, name):
    path=root/name
    if Path(name).is_absolute() or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('Study evidence escapes submission')
    if any(p.is_symlink() for p in (path,*path.parents) if p.is_relative_to(root)):
        raise ValueError('Study evidence uses a symlink')
    return path


def validate(root):
    root=Path(root).resolve()
    manifest=json.loads((root/'submission-studies.json').read_text())
    expected=[dict(id='Benchmark_PPA_20261018',analysis='results/benchmark-study/analysis.json',required_complete=True)]
    if manifest.get('schema_version')!=1 or manifest.get('primary')!=expected:
        raise ValueError('Unrecognized primary study declaration; retain scientific qualification')
    primary=json.loads(checked(root,expected[0]['analysis']).read_text())
    if primary.get('ppa_complete') is not True or primary.get('missing_required_evidence')!=[]:
        raise ValueError('Incomplete primary scientific study')
    expected_diagnostics={'WorkflowCapacity_20261021':('stopped','diagnostics/stopped-capacity'),
                          'SubmissionSprint_20261027':('not_admitted','diagnostics/submission-sprint')}
    rows=manifest.get('diagnostic',[])
    if len(rows)!=2 or {r['id'] for r in rows}!=set(expected_diagnostics):
        raise ValueError('Missing or duplicate diagnostic declaration')
    count=0
    for row in rows:
        state,folder=expected_diagnostics[row['id']]
        if row.get('comparison_qualified') is not False or (row.get('status'),row.get('path'))!=(state,folder):
            raise ValueError('Stopped diagnostics cannot be credited as a comparison')
        directory=checked(root,folder)
        receipt=json.loads((directory/'diagnostic-manifest.json').read_text())
        if receipt.get('comparison_qualified') is not False:raise ValueError('Diagnostic role differs')
        items=receipt['files'];names={x['path'] for x in items}
        actual={str(p.relative_to(directory)) for p in directory.rglob('*') if p.is_file()
                and '__pycache__' not in p.parts and p.name!='diagnostic-manifest.json'}
        if len(names)!=len(items) or names!=actual:raise ValueError('Diagnostic inventory differs')
        for item in items:
            p=checked(directory,item['path'])
            if p.stat().st_size!=item['bytes'] or digest(p)!=item['sha256']:
                raise ValueError('Diagnostic bytes differ: '+item['path'])
        count+=len(items)
    status=json.loads((root/'diagnostics/submission-sprint/status.json').read_text())
    if (status.get('formal_launch_allowed') is not False or status.get('design_sessions')!=0
            or status.get('new_physical_attempts')!=0 or status.get('registered_jobs')!=[]):
        raise ValueError('Unadmitted sprint cannot contain credited design sessions')
    return dict(passed=True,primary_studies=1,diagnostic_studies=2,diagnostic_files=count,
        scope='Evidence-role and checksum supplement; existing complete-primary scientific gates still required')


if __name__=='__main__':print(json.dumps(validate(Path(__file__).resolve().parents[1])))
