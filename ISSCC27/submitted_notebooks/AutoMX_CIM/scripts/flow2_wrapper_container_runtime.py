"""Check both Python executors inside the same pinned image before native EDA."""
import json
from pathlib import Path
import subprocess

from scripts import flow2_integration_common as common
from scripts import flow2_wrapper_pdn as pdn
from scripts import run_flow2_core_bound_fanout as fanout


def commands(root,native_command,image):
    """Reuse production mounts/user/PDK settings, with separate short probes."""
    end=native_command.index(image)+1
    checker=list(native_command[:end])
    checker[checker.index('--entrypoint')+1]='python3'
    if '--name' in checker:checker[checker.index('--name')+1]+='-checker'
    checker.extend([str(Path(root)/pdn.RECIPE),'--self-test'])
    return [('DEF_checker',checker,'automx-cim-wrapper-def-checker-runtime-v1'),
            ('OpenROAD_Python',fanout.runtime_command(native_command,Path(root)),
             'automx-cim-openroad-python-runtime-v1')]


def _record(text,expected):
    decoder=json.JSONDecoder()
    for index,char in enumerate(text):
        if char!='{':continue
        try:value,_=decoder.raw_decode(text[index:])
        except ValueError:continue
        if isinstance(value,dict) and value.get('format')==expected:return value
    return None


def run(root,native_command,image,folder):
    root,folder=Path(root),Path(folder)
    report={'format':'automx-cim-wrapper-container-preflight-v1','image':image,
            'status':'PASS','checks':{},'scope':'runtime smoke only; no EDA or analog PASS inferred'}
    for name,cmd,expected in commands(root,native_command,image):
        print('Container preflight: '+name,flush=True)
        try:
            result=subprocess.run(cmd,cwd=root,text=True,capture_output=True,timeout=30)
            code=result.returncode;output=result.stdout+'\n'+result.stderr
        except (OSError,subprocess.TimeoutExpired) as error:
            code=None;output=str(error)
        log=folder/('container_'+name.lower()+'.log')
        log.parent.mkdir(parents=True,exist_ok=True);log.write_text(output,encoding='utf-8')
        record=_record(output,expected)
        passed=code==0 and record is not None and record.get('status')=='PASS'
        if name=='DEF_checker':passed=passed and pdn.CHECKER_SELF_TEST_MARKER in output
        report['checks'][name]={'command':cmd,'returncode':code,
            'status':'PASS' if passed else 'FAIL','runtime':record,'log':common._item(root,log)}
        if not passed:
            report['status']='BLOCKED_NATIVE_CONTAINER_RUNTIME'
            break
    common._save(folder/'container_runtime.json',report)
    return report
