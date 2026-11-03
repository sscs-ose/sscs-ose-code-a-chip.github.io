"""Check export completeness and restore boundaries without a new physical run."""
import copy
import json
import subprocess
import tempfile
from pathlib import Path

from capacity_physical_export import export,restore
from study_protocol import write_json,digest


def reject(call):
    try:call()
    except (ValueError,FileNotFoundError):return
    raise AssertionError('Invalid physical export/restore accepted')


def check():
    with tempfile.TemporaryDirectory(prefix='physical-export-boundaries-') as temp:
        root=Path(temp);run=root/'run';run.mkdir()
        write_json(run/'qualification.json',dict(status='running'))
        reject(lambda:export(run,root/'running-export'));assert not (root/'running-export').exists()
        write_json(run/'qualification.json',dict(status='failed'))
        for name,contents in (('evidence/orfs-work/objects/connectivity.cdl','subckt fixture\n'),
                              ('evidence/declared.opaque','Required opaque data\n'),
                              ('workloads/short/trace.vcd','$comment fixture $end\n'),
                              ('workloads/obj/cache.log','Do not retain rebuildable cache\n')):
            path=run/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(contents)
        write_json(run/'evidence/failed-attempt.json',dict(files=[dict(path='declared.opaque')]))
        (run/'project').mkdir();subprocess.run(['git','init','-q'],cwd=run/'project',check=True)
        out=root/'export';manifest=export(run,out)
        assert manifest['bundle'] is None
        names={r['path'] for r in manifest['files']}
        assert 'evidence/orfs-work/objects/connectivity.cdl' in names
        assert 'evidence/declared.opaque' in names
        assert not any('/obj/' in name for name in names)
        assert next(r for r in manifest['files'] if r['path'].endswith('.vcd'))['encoding']=='gzip'
        restored=root/'restored';restore(out,restored)
        for name in names:assert digest(run/name)==digest(restored/name)
        reject(lambda:export(run,out));reject(lambda:restore(out,restored))
        manifest_path=out/'physical-export.json'
        for label,badpath in (('traversal','../outside'),('metadata','project/.git/config')):
            broken=copy.deepcopy(manifest);broken['files'][0]['path']=badpath;write_json(manifest_path,broken)
            target=root/label;reject(lambda:restore(out,target));assert not target.exists()
        write_json(manifest_path,manifest)
        stored=out/manifest['files'][0]['stored'];original=stored.read_bytes();stored.write_bytes(original+b'changed')
        reject(lambda:restore(out,root/'changed'))
        stored.write_bytes(original)
        broken=copy.deepcopy(manifest)
        item=next(r for r in broken['files'] if r['encoding']=='gzip');item['bytes']=1
        write_json(manifest_path,broken);reject(lambda:restore(out,root/'oversized'))
        write_json(manifest_path,manifest)
        (run/'evidence/declared.opaque').unlink()
        reject(lambda:export(run,root/'missing-declared'))
        branched=root/'branched';project=branched/'project';project.mkdir(parents=True)
        write_json(branched/'qualification.json',dict(status='failed'))
        def git(*args):
            return subprocess.check_output(['git','-c','user.name=Fixture','-c',
                'user.email=fixture@example.invalid',*args],cwd=project,text=True).strip()
        git('init','-q');(project/'source.txt').write_text('initial\n')
        git('add','source.txt');git('commit','-qm','Initial fixture')
        branch=git('symbolic-ref','--short','HEAD')
        git('checkout','-qb','delivery');(project/'source.txt').write_text('routed fixture\n')
        git('commit','-qam','Delivery fixture');delivery=git('rev-parse','HEAD')
        git('checkout','-q',branch)
        export(branched,root/'bundle-one');restore(root/'bundle-one',root/'restored-one')
        export(root/'restored-one',root/'bundle-two');restore(root/'bundle-two',root/'restored-two')
        recovered=subprocess.check_output(['git','show',delivery+':source.txt'],
            cwd=root/'restored-two/project',text=True)
        assert recovered=='routed fixture\n'
    result=dict(passed=True,model_calls=0,physical_runs=0,synthetic=True,checks=[
        'running source and existing destinations rejected',
        'all declared files and ORFS objects retained; only compiler caches excluded',
        'early failed attempt without Git commit can be preserved',
        'decoded hashes match; changed storage, unsafe paths and size overflow rejected',
        'nondefault delivery commits remain reachable through two export/restore generations'])
    write_json(Path(__file__).resolve().parents[1]/'checks/physical-export-boundaries.json',result)
    return result


if __name__=='__main__':print(json.dumps(check()))
