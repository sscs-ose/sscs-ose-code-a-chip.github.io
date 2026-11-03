"""Replay unchanged original-job inputs with a separately pinned event recorder.

This development-assistant experiment cannot adopt S14. Original input bytes,
native readback, value-change recording and functional results stay separate.
No live workflow store is read or written by the experiment.
"""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from hullcirq.physical_tools import load, require, sha
from hullcirq.postlayout_execution import execute, fixed_worker_definition
from hullcirq.postlayout_execution_audit import validate_completed_execution
from hullcirq.verification import trusted_command, _wsl_path, object_hash

SOURCE = ROOT/'.work/m2k/dynamic/original-job-yfyg25m7'
EVIDENCE = ROOT/'results/npu_postlayout_diagnostic_v2/evidence.json'
EVIDENCE_SHA = '93bfa502b27afec1e56f6e676d9e475b94ac57759431e94b46c071aa62d35850'

def save(path, value):
    with path.open('x',encoding='utf-8') as stream:
        json.dump(value,stream,ensure_ascii=False,allow_nan=False,indent=2);stream.write('\n')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare-only',action='store_true')
    args=parser.parse_args()
    require(sha(EVIDENCE)==EVIDENCE_SHA,'event_source_conflict','Retain the exact earlier diagnostic evidence.')
    evidence=load(EVIDENCE)
    original_audits={op:validate_completed_execution(SOURCE,op,worker_version='v2') for op in ('compile','simulate')}
    require(object_hash(original_audits)==object_hash(evidence['execution_audits']),
            'event_source_conflict','The complete original input and process bindings changed.')
    definition=fixed_worker_definition('v3')
    parent=ROOT/'.work/m2l/dynamic';parent.mkdir(parents=True,exist_ok=True)
    folder=Path(tempfile.mkdtemp(prefix='original-job-',dir=parent))
    # The source v2 testbench remains byte-identical, including original vectors,
    # receiving-edge phase, assertions and complete-hierarchy VCD recording.
    names=set(definition['COMPILE_INPUTS'])|{'verification-plan.json','testbench-adapter.json',
          'hullcirq_readback.c','hullcirq_readback.vpi','sdf-readback-manifest.tsv'}
    original_hashes={}
    for name in sorted(names):
        source=SOURCE/name;raw=source.read_bytes();(folder/name).write_bytes(raw)
        original_hashes[name]=hashlib.sha256(raw).hexdigest()
    event_plugin=ROOT/'.work/m2l/events/build'
    for name in ('postlayout_event_capture.c','hullcirq_event_capture.vpi','event-signal-manifest.tsv'):
        raw=(event_plugin/name).read_bytes()
        require(hashlib.sha256(raw).hexdigest()==definition['PLUGIN_SHA256'][name],
                'event_plugin_conflict','Use the independently qualified, byte-pinned event recorder.')
        (folder/name).write_bytes(raw)
    shutil.copyfile(__file__,folder/'event-orchestrator-source.py')
    compiler=definition['CONFIGURATION'];save(folder/'compiler-config.json',compiler)
    save(folder/'source-binding.json',{'kind':'hullcirq-unchanged-original-job-event-experiment-v1',
        'original_folder':str(SOURCE),'original_evidence_sha256':EVIDENCE_SHA,
        'original_source_binding':evidence['original_source_binding'],
        'original_execution_audits':original_audits,'unchanged_inputs':original_hashes,
        'original_job_changed':False,'rtl_changed':False,'sdf_changed':False,'cell_models_changed':False,
        'event_plugin_inputs':definition['PLUGIN_SHA256'],
        'scope':'event-observation experiment; native delay-binding issues remain; no adoption',
        'adoption_permitted':False})
    print(json.dumps({'folder':str(folder),'prepared':True,'original_job_changed':False}),flush=True)
    if args.prepare_only:return
    for operation,argv,timeout in (('compile',definition['COMPILE_ARGV'],300),
            ('simulate',definition['simulation_argv'](_wsl_path(folder)),900)):
        command=trusted_command(compiler,argv[0],list(argv[1:]),folder)
        result=execute(command,compiler,folder,operation,None,timeout,worker_version='v3')
        save(folder/(operation+'-execution.json'),result)
        if result.get('exit_code')!=0 or result.get('cleanup_unresolved'):
            print(json.dumps({'folder':str(folder),'operation':operation,'status':result.get('status'),
                  'exit_code':result.get('exit_code'),'cleanup_unresolved':result.get('cleanup_unresolved'),
                  'S14_adopted':False}),flush=True);return
        save(folder/(operation+'-execution-audit.json'),validate_completed_execution(folder,operation,worker_version='v3'))
    summary=load(folder/'hullcirq-events-summary.json')
    stdout=(folder/'simulate/stdout.log').read_text(encoding='utf-8')
    save(folder/'experiment-summary.json',{'scope':'same original job with value-change recorder; not timing qualification',
        'functional_pass_marker':'HULLCIRQ_GLOBAL_PASS outputs=16' in stdout,
        'event_capture_summary':summary,'event_transcript_sha256':sha(folder/'hullcirq-events.tsv'),
        'adoption_permitted':False,'S14_status':'Unsupported'})
    print(json.dumps({'folder':str(folder),'functional_pass_marker':'HULLCIRQ_GLOBAL_PASS outputs=16' in stdout,
         'event_transcript_bytes':(folder/'hullcirq-events.tsv').stat().st_size,
         'S14_adopted':False}),flush=True)

if __name__=='__main__':main()
