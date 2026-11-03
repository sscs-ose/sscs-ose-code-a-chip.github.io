"""Host orchestration for the fixed original-job Icarus 13 Linux worker.

Derived by the development assistant from physical_tools._execute; process-group
cleanup and immutable birth/exit records retain that supervisor's semantics.
This separate adapter changes no original S11/DRC/LVS worker or live workflow.
It is an execution mechanism, not a dynamic verification acceptance validator.
"""
from __future__ import annotations
import json
from pathlib import Path
import runpy
import subprocess
import time

from .physical_tools import require, sha, load
from .verification import object_hash, trusted_command, _wsl_path

ROOT = Path(__file__).resolve().parents[2]
WORKER_SOURCE = ROOT / 'scripts/postlayout_worker_v1.py'
WORKER_SHA256 = '1b1dadd83b974d2414fdcf606d662f3a62ae8e98c257ef9c3117b2bf8f497e48'
WORKER_V2_SOURCE = ROOT / 'scripts/postlayout_worker_v2.py'
WORKER_V2_SHA256 = '1ef52ce064ddd736eef2fc5e88b193a4815b8444325d96f4d660b50bfc7382a0'
WORKER_V3_SOURCE = ROOT / 'scripts/postlayout_worker_v3.py'
WORKER_V3_SHA256 = '7e369865fac299d68a00c4598aee83116b4acb20c3d2349ee59169c6f0801d24'


def fixed_worker_definition(worker_version='v1'):
    versions = {'v1': (WORKER_SOURCE, WORKER_SHA256),
                'v2': (WORKER_V2_SOURCE, WORKER_V2_SHA256),
                'v3': (WORKER_V3_SOURCE, WORKER_V3_SHA256)}
    require(worker_version in versions,'postlayout_worker_conflict','Use a fixed supported worker version.')
    source, expected = versions[worker_version]
    require(sha(source)==expected,'postlayout_worker_conflict','Use the exact pinned postlayout process supervisor.')
    definition = runpy.run_path(str(source))
    definition['_worker_source'] = source
    definition['_worker_sha256'] = expected
    return definition


def execute(command,configuration,folder,operation,cancel_event,timeout,*,worker_version="v1"):
    """Supervise Linux process groups; closing wsl.exe alone is insufficient."""
    if cancel_event is not None and cancel_event.is_set():
        return {'command':command,'executed':False,'exit_code':None,'status':'Cancelled','stdout':'','stderr':''}
    folder=Path(folder).resolve()
    definition = fixed_worker_definition(worker_version)
    require(type(configuration) is dict and object_hash(configuration)==object_hash(definition["CONFIGURATION"]),
            "postlayout_configuration_conflict", "Use the exact pinned Icarus 13 configuration.")
    require(operation in ("compile", "simulate"), "postlayout_operation_conflict", "Use a fixed postlayout operation.")
    expected_argv = definition["COMPILE_ARGV"] if operation=="compile" else (definition["simulation_argv"](_wsl_path(folder)) if worker_version in ("v2","v3") else definition["SIMULATION_ARGV"])
    expected_command = trusted_command(configuration, expected_argv[0], list(expected_argv[1:]), folder)
    require(command==expected_command, "postlayout_command_conflict", "Use the exact shell-free operation command.")
    definition["validate_operation"](list(expected_argv), _wsl_path(folder))
    logs=folder/operation;logs.mkdir()
    argv=command[command.index('--exec')+1:]
    worker=logs/'worker.py'
    worker.write_bytes(definition["_worker_source"].read_bytes())
    worker_sha=sha(worker)
    require(worker_sha==definition["_worker_sha256"],'postlayout_worker_conflict','Use the fixed supported supervisor version before launching tools.')
    input_names = definition["validate_operation"](argv, _wsl_path(folder))
    input_files = {name:sha(folder/name) for name in input_names}
    request={'version':definition['VERSION'],'argv':argv,'cwd':_wsl_path(folder),'timeout_seconds':timeout,'worker_sha256':worker_sha,
             'input_files':input_files, 'configuration_sha256':object_hash(configuration)}
    (logs/'request.json').write_text(json.dumps(request,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    request_sha=sha(logs/'request.json')
    supervisor_args=[_wsl_path(worker),_wsl_path(logs/'request.json'),'--request-sha256',request_sha,'--worker-sha256',worker_sha]
    supervisor=trusted_command(configuration,'/usr/bin/python3',supervisor_args,folder)
    started=time.monotonic();cancel_started=None;recovery=None
    try:process=subprocess.Popen(supervisor,cwd=folder,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',errors='replace',shell=False)
    except OSError as error:return {'command':command,'supervisor_command':supervisor,'executed':False,'exit_code':None,'status':'Unsupported','stdout':'','stderr':str(error)}
    while process.poll() is None:
        if (cancel_event is not None and cancel_event.is_set()) or time.monotonic()-started>timeout+15:
            (logs/'cancel.request').write_bytes(b'cancel\n')
            if cancel_started is None:cancel_started=time.monotonic()
        if cancel_started is not None and time.monotonic()-cancel_started>20:
            cleanup=trusted_command(configuration,'/usr/bin/python3',supervisor_args+['--cleanup'],folder)
            try:
                recovered=subprocess.run(cleanup,cwd=folder,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=20,shell=False)
                recovery={'command':cleanup,'exit_code':recovered.returncode,'stdout':recovered.stdout.decode('utf-8',errors='replace'),'stderr':recovered.stderr.decode('utf-8',errors='replace')}
            except (OSError,subprocess.TimeoutExpired) as error:recovery={'command':cleanup,'exit_code':None,'error':str(error)}
            try:process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                try:process.wait(timeout=3)
                except subprocess.TimeoutExpired:pass
            break
        time.sleep(.2)
    try:supervisor_out,supervisor_err=process.communicate(timeout=3)
    except subprocess.TimeoutExpired:
        process.kill()
        supervisor_out,supervisor_err='','Host supervisor did not become waitable after bounded recovery.'
    cleanup=load(logs/'cleanup-result.json') if (logs/'cleanup-result.json').is_file() else {}
    cleanup_verified=cleanup.get('whole_process_group_terminated_on_cancel') is True
    if not (logs/'process-result.json').exists():
        return {'command':command,'supervisor_command':supervisor,'worker_sha256':worker_sha,'request_sha256':request_sha,
                'executed':(logs/'process-start.json').is_file(),'exit_code':None,'status':'Failed','recovery':recovery,'cleanup_unresolved':not cleanup_verified,
                'stdout':(logs/'stdout.log').read_text(encoding='utf-8',errors='replace') if (logs/'stdout.log').is_file() else supervisor_out,
                'stderr':((logs/'stderr.log').read_text(encoding='utf-8',errors='replace') if (logs/'stderr.log').is_file() else '')+supervisor_err+'\nLinux worker did not save an exit record; tool termination is not assumed.'}
    result=load(logs/'process-result.json')
    require(result['argv']==argv,'postlayout_command_conflict','The Linux worker executed a different command.')
    require(result.get('version')==definition['VERSION'] and result.get('input_files')==input_files
            and result.get('configuration_sha256')==object_hash(configuration),
            'postlayout_worker_conflict','The terminal record must bind every frozen operation input and runtime configuration.')
    result.update(command=command,supervisor_command=supervisor,worker_sha256=worker_sha,request_sha256=request_sha,
                  stdout=(logs/'stdout.log').read_text(encoding='utf-8',errors='replace'),stderr=(logs/'stderr.log').read_text(encoding='utf-8',errors='replace'),
                  supervisor_stdout=supervisor_out,supervisor_stderr=supervisor_err)
    if recovery is not None:
        result['recovery']=recovery;result['status']='Failed'
    result['cleanup_unresolved']=not (result.get('whole_process_group_terminated') is True or cleanup_verified)
    return result
