"""Check that diagnostic labels cannot bypass complete-primary or provenance gates."""
import json
import tempfile
from pathlib import Path
from submission_studies import validate,digest


def check():
    with tempfile.TemporaryDirectory() as temporary:
        root=Path(temporary)
        def write(name,data):
            p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(data));return p
        primary={'ppa_complete':True,'missing_required_evidence':[]}
        analysis=write('results/benchmark-study/analysis.json',primary)
        declaration=dict(schema_version=1,primary=[dict(id='Benchmark_PPA_20261018',analysis='results/benchmark-study/analysis.json',required_complete=True)],diagnostic=[])
        for identity,state,folder in [('WorkflowCapacity_20261021','stopped','stopped-capacity'),('SubmissionSprint_20261027','not_admitted','submission-sprint')]:
            directory='diagnostics/'+folder
            declaration['diagnostic'].append(dict(id=identity,status=state,path=directory,comparison_qualified=False))
            data=dict(formal_launch_allowed=False,design_sessions=0,new_physical_attempts=0,registered_jobs=[])
            p=write(directory+'/status.json',data)
            write(directory+'/diagnostic-manifest.json',dict(comparison_qualified=False,files=[dict(path='status.json',bytes=p.stat().st_size,sha256=digest(p))]))
        write('submission-studies.json',declaration);assert validate(root)['passed']
        def rejected():
            try:validate(root)
            except (ValueError,OSError):return
            raise AssertionError('Invalid submission declaration accepted')
        write('results/benchmark-study/analysis.json',dict(primary,ppa_complete=False));rejected();write('results/benchmark-study/analysis.json',primary)
        declaration['diagnostic'][0]['comparison_qualified']=True
        write('submission-studies.json',declaration);rejected()
        declaration['diagnostic'][0]['comparison_qualified']=False;write('submission-studies.json',declaration)
        p=root/'diagnostics/stopped-capacity/status.json';saved=p.read_bytes();p.write_text('{}');rejected();p.write_bytes(saved)
        extra=write('diagnostics/stopped-capacity/unlisted.json',{});rejected();extra.unlink()
        p.unlink();p.symlink_to(analysis);rejected();p.unlink();p.write_bytes(saved)
        assert validate(root)['passed']
    return dict(passed=True,cases=['valid supplement','incomplete primary rejected','credited diagnostic rejected','tampered data rejected','unlisted data rejected','symlink rejected'])


if __name__=='__main__':print(json.dumps(check()))
