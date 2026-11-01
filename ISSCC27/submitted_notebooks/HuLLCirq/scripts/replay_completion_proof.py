"""Verify the saved completion archive; optionally rerun S14 in fresh space.

Archive-only checking needs no original tools or working directories. Actual
replay currently uses the retained local S11 files and pinned installed runtime;
it does not modify the GUI store, regenerate RTL, or adopt a new result.
"""
from __future__ import annotations
import argparse
import copy
import gzip
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from hullcirq.verification import object_hash
from hullcirq.postroute_tools import run_postlayout, validate_postlayout_result
from hullcirq.postlayout_workflow import POST_ROUTE_REQUIRED_FILES

def load(path):return json.loads(path.read_text(encoding='utf-8'))
def save(path,value):
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

def _read_entry(archive, relative, entry):
    path=archive_path(archive,relative)
    require(type(entry.get('bytes')) is int and 0<=entry['bytes']<MAX_RAW_BYTES and path.is_file()
            and path.stat().st_size==entry['bytes'],'Missing or invalid archive file: '+relative)
    payload=path.read_bytes()
    require(len(payload)==entry['bytes'] and hashlib.sha256(payload).hexdigest()==entry.get('sha256'),'Archive hash mismatch: '+relative)
    if 'raw_bytes' not in entry:return payload
    require(type(entry.get('raw_bytes')) is int and 0<=entry['raw_bytes']<MAX_RAW_BYTES,'Invalid decompressed size: '+relative)
    if entry.get('compression')=='gzip':
        with gzip.GzipFile(fileobj=io.BytesIO(payload)) as stream:raw=stream.read(entry['raw_bytes']+1)
    else:
        require(entry.get('compression') is None,'Unknown archive compression: '+relative)
        raw=payload
    require(len(raw)==entry['raw_bytes'] and hashlib.sha256(raw).hexdigest()==entry.get('raw_sha256'),'Raw archive hash mismatch: '+relative)
    return raw

def verify(archive):
    """Check saved bytes and lineage only; do not re-run EDA or claim new results."""
    archive=Path(archive).resolve()
    manifest=load(archive/'manifest.json')
    require(manifest.get('schema')=='hullcirq-completion-evidence-v1' and manifest.get('status')=='Passed'
            and manifest.get('method')=='post_route_functional_plus_sta','Unexpected completion archive method/schema.')
    files,record_files=manifest['files'],manifest['record_files']
    require(type(files) is dict and type(record_files) is dict and not set(files)&set(record_files)
            and set(record_files)=={name+'-record.json' for name in STAGES}
            and set(manifest['records'])==set(STAGES),'Require exactly four distinct final stage records.')
    index={};total=0
    for relative,entry in {**files,**record_files}.items():
        raw=_read_entry(archive,relative,entry)
        original=entry.get('original_path',relative)
        archive_path(archive,original)
        require(original not in index and relative==original+('.gz' if entry.get('compression')=='gzip' else ''),
                'Duplicate or inconsistent original archive path: '+original)
        index[original]=(relative,entry)
        total+=len(raw)
    def original_bytes(name):
        require(name in index,'Missing bound evidence: '+name)
        relative,entry=index[name]
        return _read_entry(archive,relative,entry)
    records={name:json.loads(original_bytes(name+'-record.json')) for name in STAGES}
    for name,run in records.items():
        reference=manifest['records'][name]
        require(object_hash(run)==reference['sha256'] and run['id']==reference['id']
                and run['revision_id']==reference['revision_id'],'A final record differs from its manifest.')
        require(run['record_hash']==object_hash({k:v for k,v in run.items() if k!='record_hash'}),'Invalid saved record hash.')
        require(run['execution_status']=='Completed' and run['validation_status']=='Passed' and run['review_status']=='Accepted',
                'A final record is not completed, passed and adopted.')
        # DRC/LVS carry the plan through their exact S11 snapshot, not duplicate
        # top-level plan fields. Preserve the real stage schema when checking it.
        plan_source=run
        if name in ('drc','lvs'):
            require(run.get('layout_snapshot')==records['physical']
                    and run.get('layout_run_id')==records['physical']['id']
                    and run.get('layout_record_sha256')==object_hash(records['physical']),
                    'DRC/LVS must retain the exact archived physical snapshot.')
            plan_source=run['layout_snapshot']
        require(plan_source['verification_plan_sha256']==manifest['verification_plan_sha256']
                and plan_source['vector_hash']==manifest['vector_hash']
                and object_hash(plan_source['verification_plan'])==plan_source['verification_plan_sha256'],
                'The original verification plan differs across stages.')
        history=json.loads(original_bytes('history/'+name+'_workflow.json'))
        require(history['runs'][-1]==run and run['source_key']==history['source_key']
                and run['acceptance_epoch']==history['source_epoch'],'The archived adoption is stale or differs from its history.')
        reviews=[item for item in history['reviews'] if item['run_id']==run['id']]
        require(reviews and reviews[-1]['decision']=='accepted' and reviews[-1]['source_key']==run['source_key']
                and reviews[-1]['acceptance_epoch']==run['acceptance_epoch'],'The recorded adoption is missing or inconsistent.')
        for key in ('artifacts','retained_files'):
            entries=run['checks'].get(key,[])
            for item in entries:
                original=name+'/'+item['relative_path']
                require(original in index,'A bound raw artifact is absent: '+original)
                relative,entry=index[original]
                require(entry.get('raw_sha256',entry['sha256'])==item['sha256']
                        and entry.get('raw_bytes',entry['bytes'])==item['bytes'],'A raw artifact differs from its run manifest: '+original)
    final=records['postlayout']
    for short,name in (('layout','physical'),('drc','drc'),('lvs','lvs')):
        require(final[short+'_record_sha256']==object_hash(records[name]) and final[short+'_run_id']==records[name]['id']
                and final[short+'_snapshot']==records[name],'Final post-layout lineage differs.')
    require(records['drc']['layout_record_sha256']==object_hash(records['physical'])
            and records['lvs']['layout_record_sha256']==object_hash(records['physical'])
            and records['lvs']['drc_record_sha256']==object_hash(records['drc'])
            and records['lvs']['drc_run_id']==records['drc']['id']
            and records['lvs']['drc_snapshot']==records['drc'],'DRC/LVS lineage differs.')
    checked=final['checks']
    require(POST_ROUTE_REQUIRED_FILES<={item['id'] for item in checked['artifacts']},'Mandatory final functional/STA evidence is missing.')
    require(final['execution_scope']==final['runtime_configuration']['execution_scope']==checked['execution_scope']=='post_route_functional_plus_sta'
            and checked.get('origin')=='trusted_fixed_postlayout_adapter' and checked.get('executed') is True
            and final.get('verification_supported') is True,'Require actual supported functional plus STA evidence.')
    require(checked['summary']==manifest['summary'] and checked['summary']['functional_status']==checked['summary']['sta_status']=='Passed'
            and all(checked['checks'].get(key,{}).get('validation_status')=='Passed' for key in
                    ('source_identity','configuration','functional','parasitics','constraints','setup_hold','electrical')),
            'A required functional or timing criterion is not Passed.')
    require(manifest.get('dynamic_SDF_simulation_passed') is False,'The archive cannot imply dynamic SDF qualification.')
    for name in ('generation.json','global_generation.json'):
        require(original_bytes('history/'+name)==original_bytes('history-before/'+name),
                'The zero-new-model-call claim differs from the saved generation histories.')
    baseline=json.loads(original_bytes('history-before/physical_workflow.json'))['runs'][-1]
    require(all(records['physical'][key]==baseline[key] for key in
                ('global_rtl_sha256','source_manifest_sha256','settings_sha256','verification_plan_sha256')),
            'The completion changed the original RTL, node source, settings or verification plan.')
    for item in manifest.get('new_attempts',[]):
        run=json.loads(original_bytes(item['record_path']))
        history=json.loads(original_bytes('history/'+item['stage']+'_workflow.json'))
        require(object_hash(run)==item['record_sha256'] and run['id']==item['id']
                and run in history['runs'] and run['execution_status']==item['execution_status']
                and run['validation_status']==item['validation_status'],'A retained diagnostic attempt differs from its history.')
    return {'status':'Passed','kind':'archive_integrity_and_record_lineage_not_new_EDA',
            'file_count':len(files)+len(record_files),'raw_bytes':total,'records':records}

def replay(archive, output, checked=None):
    checked=checked or verify(archive)
    output=Path(output).resolve()
    require(not output.exists() and output.is_relative_to((ROOT/'.work').resolve()),'Use a fresh replay directory below HuLLCirq/.work.')
    output.mkdir(parents=True)
    records=checked['records'];original=records['postlayout'];configuration=copy.deepcopy(original['runtime_configuration'])
    configuration['working_directory']=str(output/'runs')
    save(output/'replay-source.json',{'archive_manifest_sha256':hashlib.sha256((Path(archive)/'manifest.json').read_bytes()).hexdigest(),
         'original_run_id':original['id'],'original_record_sha256':object_hash(original),
         'original_configuration_sha256':object_hash(original['runtime_configuration']),
         'configuration':configuration,'live_store_modified':False,'adopted':False,'model_calls':0,
         'requirements':'Retained same-host local S11 files, pinned installed tools and PDK paths are required.'})
    summary={'status':'Failed','kind':'actual_saved_input_postroute_replay','original_run_id':original['id'],
             'verification_plan_sha256':original['verification_plan_sha256'],
             'live_store_modified':False,'adopted':False,'new_RTL_or_model_generation':False}
    try:
        result=run_postlayout(records['lvs'],records['drc'],records['physical'],configuration)
        save(output/'result.json',result)
        validate_postlayout_result(result,records['lvs'],records['drc'],records['physical'],configuration)
        summary.update(status='Passed',summary=result['summary'])
    except Exception as error:
        summary.update(error_type=type(error).__name__,error=str(error))
        raise
    finally:
        save(output/'summary.json',summary)
    return summary

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive',type=Path,default=ROOT/'results/npu_completion_v1')
    parser.add_argument('--verify-only',action='store_true')
    parser.add_argument('--output',type=Path,help='Fresh ignored output; required for actual S14 replay.')
    args=parser.parse_args()
    if args.verify_only and args.output is not None:parser.error('--verify-only does not accept an execution output directory')
    if not args.verify_only and args.output is None:parser.error('--output is required for actual replay; use --verify-only for portable checking')
    checked=verify(args.archive)
    if args.verify_only:
        print(json.dumps({k:v for k,v in checked.items() if k!='records'}));return
    summary=replay(args.archive,args.output,checked)
    print(json.dumps(summary))
if __name__=='__main__':main()
