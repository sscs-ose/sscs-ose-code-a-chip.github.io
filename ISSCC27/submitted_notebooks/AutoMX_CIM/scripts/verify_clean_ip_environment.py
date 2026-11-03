"""Extract the reusable IP into /tmp and verify in a separate isolated Python environment."""
from pathlib import Path
import argparse,json,os,subprocess,sys,tarfile,tempfile,time
from scripts.package_mha_ip import package

def run(root,work,analog_views=None):
    root=Path(root).resolve();work=Path(work).resolve();work.mkdir(parents=True,exist_ok=True)
    archive=package(root,analog_views=analog_views);extracted=Path(tempfile.mkdtemp(prefix='automx_clean_ip_'))
    with tarfile.open(archive) as stream:
        assert all(not Path(n.name).is_absolute() and '..' not in Path(n.name).parts for n in stream.getmembers())
        stream.extractall(extracted)
    submission=extracted/'AutoMX_MHA_IP';image=json.loads((root/'standalone.json').read_text())['openlane_image']
    orchestration='''import json,subprocess,sys,time
from pathlib import Path
import numpy
base=Path(__file__).resolve().parent;out=base/'output';out.mkdir()
print('CLEAN_ENVIRONMENT',sys.version,numpy.__version__,flush=True)
jobs=[['ip/automx_mha/verify.py','--root',str(base),'--work',str(out/'mha')],
 ['scripts/verify_ternary_backend.py','--root',str(base),'--work',str(out/'ternary')],
 ['scripts/verify_binary_decoder.py','--root',str(base),'--work',str(out/'decoder')]]
for args in jobs:
 q=subprocess.run([sys.executable,*args],cwd=base,check=True)
report={'status':'PASS','python':sys.version,'numpy':numpy.__version__,'checks':jobs,
 'original_workspace_required':False,'isolated_site_packages':True}
(out/'clean_environment.json').write_text(json.dumps(report,indent=2))
print('CLEAN_ENVIRONMENT_IP_PASS',flush=True)
'''
    (submission/'clean_check.py').write_text(orchestration)
    venv=extracted/'venv'
    subprocess.run([sys.executable,'-m','venv','--copies',str(venv)],check=True)
    python=venv/'bin/python'
    with (work/'dependencies.log').open('w') as stream:
        wheels=root/'tools/python_wheels'
        offline=['--no-index','--find-links',str(wheels)] if list(wheels.glob('numpy-1.26.4-cp'+str(sys.version_info.major)+str(sys.version_info.minor)+'-*.whl')) else []
        subprocess.run([python,'-m','pip','install','--disable-pip-version-check',*offline,'numpy==1.26.4'],stdout=stream,stderr=subprocess.STDOUT,check=True,timeout=180)
    args=[str(python),str(submission/'clean_check.py')]
    start=time.monotonic()
    with (work/'container.log').open('w') as stream:q=subprocess.run(args,cwd=submission,env={k:v for k,v in os.environ.items() if k not in ('PYTHONPATH','PYTHONHOME')},stdout=stream,stderr=subprocess.STDOUT,timeout=900)
    if q.returncode:raise RuntimeError((work/'container.log').read_text()[-3000:])
    result=json.loads((submission/'output/clean_environment.json').read_text())
    result.update(elapsed_s=time.monotonic()-start,extraction=str(submission),environment=str(venv),
      scope='Clean extracted source-IP tests with an isolated Python environment and newly installed NumPy; native Icarus is the declared host dependency. This is not a full notebook rerun or a separate physical host.')
    (work/'verification.json').write_text(json.dumps(result,indent=2)+'\n');print('CLEAN_IP_PASS',round(result['elapsed_s'],2),flush=True);return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--work',type=Path,required=True);p.add_argument('--analog-views',type=Path);a=p.parse_args();run(a.root,a.work,a.analog_views)
