"""Archive current S11-S14 completion without EDA or changing live history.

Large raw working files are individually gzip-compressed with both compressed
and original hashes. Earlier results are referenced, never rewritten.
"""
from __future__ import annotations
import argparse
import gzip
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from hullcirq.verification import object_hash
from hullcirq.physical_tools import sha, validate_layout_result
from hullcirq.physical_workflow import validate_physical_proof
from hullcirq.drc_tools import validate_drc_result
from hullcirq.drc_workflow import validate_drc_proof
from hullcirq.lvs_tools import validate_lvs_result
from hullcirq.lvs_workflow import validate_lvs_proof
from hullcirq.postlayout_tools import validate_postlayout_result
from hullcirq.postlayout_workflow import validate_postlayout_proof

def load(path):return json.loads(path.read_text(encoding='utf-8'))
def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8',newline='\n') as f:json.dump(value,f,indent=2,ensure_ascii=False,allow_nan=False);f.write('\n')

STAGES = ('physical','drc','lvs','postlayout')
MAX_RAW_BYTES = 512*1024*1024

def require(condition, message):
    if not condition:raise ValueError(message)

def archive_path(root, relative):
    require(type(relative) is str and relative and '\\' not in relative and ':' not in relative,
            'Use a relative archive path.')
    parts=PurePosixPath(relative)
    require(not parts.is_absolute() and parts.as_posix()==relative and not any(p in ('','.','..') for p in parts.parts),
            'Archive paths cannot escape or alias their directory.')
    path=(root/relative).resolve()
    require(path!=root.resolve() and path.is_relative_to(root.resolve()),'Archive path escaped its directory.')
    return path

def collect(data, output, history_before=None):
    data,output=Path(data).resolve(),Path(output).resolve()
    require(data.is_dir() and data.is_relative_to((ROOT/'.work').resolve()),'Read an existing local project below HuLLCirq/.work.')
    require(not output.exists() and (output.is_relative_to((ROOT/'results').resolve()) or output.is_relative_to((ROOT/'.work').resolve())),
            'Use a new archive directory below HuLLCirq/results or .work; previous evidence is immutable.')
    history_before=Path(history_before or ROOT/'.work/m2m/history-before').resolve()
    require(history_before.is_dir() and history_before.is_relative_to((ROOT/'.work').resolve()),'Keep the before-development history snapshot below HuLLCirq/.work.')
    records={};histories={};raws={}
    project_raws={path.name:path.read_bytes() for path in data.glob('*.json')}
    for name in STAGES:
        path=data/(name+'_workflow.json');raws[name]=project_raws[path.name];histories[name]=json.loads(raws[name]);records[name]=histories[name]['runs'][-1]
        run=records[name]
        require(run['execution_status']=='Completed' and run['validation_status']=='Passed' and run['review_status']=='Accepted','Every final stage must be completed, passed and adopted.')
        require(run['source_key']==histories[name]['source_key'] and run['acceptance_epoch']==histories[name]['source_epoch'],'An adopted result is stale.')
        require(run['record_hash']==object_hash({k:v for k,v in run.items() if k!='record_hash'}),'A saved record changed.')
    validate_physical_proof(records['physical'],validate_layout_result)
    validate_drc_proof(records['drc'],validate_drc_result)
    validate_lvs_proof(records['lvs'],validate_lvs_result)
    validate_postlayout_proof(records['postlayout'],validate_postlayout_result)
    require(records['postlayout']['execution_scope']=='post_route_functional_plus_sta','Collect the explicit functional plus STA completion method.')
    for short,name in (('layout','physical'),('drc','drc'),('lvs','lvs')):
        require(records['postlayout'][short+'_record_sha256']==object_hash(records[name]),'Final stages must describe one adopted chain.')
    before_physical=load(history_before/'physical_workflow.json')['runs'][-1]
    require(all(records['physical'][key]==before_physical[key] for key in
                ('global_rtl_sha256','source_manifest_sha256','settings_sha256','verification_plan_sha256')),
            'Completion must retain the original RTL, node sources, GUI settings and verification plan.')
    for name in ('generation.json','global_generation.json'):
        require((history_before/name).read_bytes()==project_raws[name],'Model generation history changed; do not claim zero new model calls.')
    output.mkdir(parents=True)
    captured={}
    def copy_raw(source,relative):
        require(source.stat().st_size<MAX_RAW_BYTES,'Raw evidence exceeds the archive reader limit: '+str(source))
        raw=source.read_bytes();checksum=hashlib.sha256(raw).hexdigest()
        original=relative
        compress=len(raw)>262144 and source.suffix.lower() not in ('.png','.gz')
        if compress:relative+='.gz'
        path=archive_path(output,relative);path.parent.mkdir(parents=True,exist_ok=True)
        require(not path.exists(),'Duplicate archive destination: '+relative)
        payload=gzip.compress(raw,mtime=0) if compress else raw
        with path.open('xb') as f:f.write(payload)
        captured[relative]={'original_path':original,'sha256':hashlib.sha256(payload).hexdigest(),'bytes':len(payload),
                            'raw_sha256':checksum,'raw_bytes':len(raw),'compression':'gzip' if compress else None}
    for name,run in records.items():
        save(output/(name+'-record.json'),run)
        copy_raw(data/(name+'_workflow.json'),'history/'+name+'_workflow.json')
        folder=Path(run['checks']['artifacts_directory']).resolve()
        require(folder.is_dir() and folder.is_relative_to((ROOT/'.work').resolve()),'Execution evidence must remain below HuLLCirq/.work.')
        selected={entry['relative_path'] for key in ('artifacts','retained_files') for entry in run['checks'].get(key,[])}
        if name=='postlayout':
            selected|={p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file()}
        else:
            selected|={p.relative_to(folder).as_posix() for p in folder.glob('**/*')
                       if p.is_file() and p.parent.name in ('version','layout','drc','lvs')}
        if name=='physical':
            selected|={p.relative_to(folder).as_posix() for p in folder.glob('resume*.json')}
        for relative in sorted(selected):
            path=archive_path(folder,relative)
            require(path.is_file(),'A retained artifact is missing: '+relative)
            copy_raw(path,name+'/'+relative)
    for path in sorted(data.glob('*.json')):
        if path.name not in {name+'_workflow.json' for name in records}:copy_raw(path,'history/'+path.name)
    attempts=[]
    for name in STAGES:
        baseline_path=history_before/(name+'_workflow.json')
        before=load(baseline_path) if baseline_path.is_file() else {'runs':[]}
        prior_ids={r['id'] for r in before['runs']}
        if baseline_path.is_file():copy_raw(baseline_path,'history-before/'+baseline_path.name)
        for run in histories[name]['runs']:
            if run['id'] in prior_ids or run['id']==records[name]['id']:continue
            require(run['execution_status'] not in ('Queued','Running'),'Wait for new attempts to finish before collecting.')
            prefix='attempts/'+name+'/'+run['id']
            require('/' not in run['id'] and '\\' not in run['id'],'Invalid saved run ID.')
            save(archive_path(output,prefix+'/record.json'),run)
            path=archive_path(output,prefix+'/record.json')
            captured[prefix+'/record.json']={'original_path':prefix+'/record.json','sha256':sha(path),'bytes':path.stat().st_size,
                                           'raw_sha256':sha(path),'raw_bytes':path.stat().st_size,'compression':None}
            directory=run['checks'].get('artifacts_directory')
            folder=Path(directory).resolve() if directory else None
            require(folder is None and not run['checks'].get('commands') or folder is not None and folder.is_dir()
                    and folder.is_relative_to((ROOT/'.work').resolve()),'New attempt diagnostics are missing or outside the workspace.')
            selected=[p for p in folder.rglob('*') if p.is_file() and p.suffix.lower() in ('.json','.log','.rpt','.txt','.py','.v','.sdc','.tcl')] if folder else []
            for path in sorted(selected):
                require(path.resolve().is_relative_to(folder),'Attempt diagnostic escaped its execution directory.')
                copy_raw(path,prefix+'/raw/'+path.relative_to(folder).as_posix())
            attempts.append({'stage':name,'id':run['id'],'record_sha256':object_hash(run),'record_path':prefix+'/record.json',
                             'execution_status':run['execution_status'],'validation_status':run['validation_status'],
                             'scope':'All raw text logs, reports, source/configuration and supervisor records; incomplete binary layout intermediates excluded.'})
    for name in ('generation.json','global_generation.json'):copy_raw(history_before/name,'history-before/'+name)
    for path in sorted((ROOT/'src').rglob('*')):
        if path.is_file() and '__pycache__' not in path.parts and path.suffix in ('.py','.js','.css','.html','.svg','.json'):
            copy_raw(path,'implementation/'+path.relative_to(ROOT).as_posix())
    for name in ('collect_completion_proof.py','replay_completion_proof.py','collect_completion_replay.py','physical_worker_v2.py','postlayout_worker_v2.py',
                 'route_closure_v5.py','prepare_physical_repair_runtime.py','run_completion_flow.py'):
        path=ROOT/'scripts'/name
        if path.is_file():copy_raw(path,'implementation/scripts/'+name)
    prior_archives=[]
    for name in ('npu_layout_continuous_flow','npu_drc_continuous_flow','npu_lvs_continuous_flow',
                 'npu_postlayout_readiness','npu_postlayout_diagnostic_v2','npu_postlayout_event_diagnostic_v1'):
        path=ROOT/'results'/name/'manifest.json'
        if path.is_file():prior_archives.append({'path':path.relative_to(ROOT).as_posix(),'sha256':sha(path),'bytes':path.stat().st_size})
    for name,raw in project_raws.items():require((data/name).read_bytes()==raw,'Project history changed during collection; partial archive is not complete.')
    manifest={'schema':'hullcirq-completion-evidence-v1','status':'Passed','method':'post_route_functional_plus_sta',
              'records':{name:{'id':run['id'],'sha256':object_hash(run),'revision_id':run['revision_id']} for name,run in records.items()},
              'verification_plan_sha256':records['postlayout']['verification_plan_sha256'],
              'vector_hash':records['postlayout']['vector_hash'],'summary':records['postlayout']['checks']['summary'],
              'dynamic_SDF_simulation_passed':False,'new_model_calls':0,'new_RTL_modifications':[],
              'physical_implementation':records['physical']['checks'].get('implementation_kind','fresh_technology_mapping_and_routing'),
              'physical_profile_version':records['physical']['runtime_configuration']['profile']['profile_version'],
              'new_attempts':attempts,'prior_archive_references':prior_archives,
              'replay_limits':'Verify-only is portable; actual S14 replay requires the retained same-host local sources, pinned tools and PDK paths.',
              'files':captured,'record_files':{name+'-record.json':{'sha256':sha(output/(name+'-record.json')),'bytes':(output/(name+'-record.json')).stat().st_size} for name in records}}
    save(output/'manifest.json',manifest)
    from replay_completion_proof import verify
    verify(output)
    return manifest

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir',type=Path,default=ROOT/'.work/projects/npu')
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--history-before',type=Path,default=ROOT/'.work/m2m/history-before')
    args=parser.parse_args();result=collect(args.data_dir,args.output,args.history_before)
    print(json.dumps({'status':result['status'],'output':str(args.output),'records':{k:v['id'] for k,v in result['records'].items()}}))
if __name__=='__main__':main()
