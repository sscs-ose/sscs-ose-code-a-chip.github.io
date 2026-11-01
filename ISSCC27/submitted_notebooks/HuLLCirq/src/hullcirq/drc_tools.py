"""Fixed S12 Magic/KLayout checks on the unchanged adopted S11 GDS.

No RTL/model/mapping/placement/routing operation. Raw evidence remains immutable.
"""
from __future__ import annotations

import copy
import json
import re
import tempfile
from pathlib import Path, PurePosixPath
import xml.etree.ElementTree as ET

from .domain import DomainError
from .store import strict_loads
from .verification import object_hash, _wsl_path, trusted_command
from . import physical_tools as physical

ROOT = Path(__file__).resolve().parents[2]
TAG = 'drc'
SCOPE = 'exact_adopted_GDS_Magic_full_and_KLayout_pinned_open_source_DRC'
FILE_TYPES = {'input-gds':'application/octet-stream', 'config':'application/json',
    'initial-state':'application/json','final-state':'application/json','metrics':'application/json',
    'tool-versions':'application/json','drc-summary':'application/json','klayout-violations':'application/json',
    'magic-report':'text/plain; charset=utf-8','magic-markers':'application/xml','klayout-report':'application/xml'}
FIXED_FILES = {'input-gds':'input.gds','config':'config.json','initial-state':'initial-state.json',
    'tool-versions':'tool-versions.json','drc-summary':'drc-summary.json',
    'magic-report':'runs/drc/1-magic-drc/reports/drc.magic.rpt',
    'magic-markers':'runs/drc/1-magic-drc/reports/drc.magic.lyrdb',
    'klayout-report':'runs/drc/2-klayout-drc/reports/drc.klayout.lyrdb',
    'klayout-violations':'runs/drc/2-klayout-drc/reports/drc.klayout.json',
    'final-state':'runs/drc/2-klayout-drc/state_out.json',
    'metrics':'runs/drc/final/metrics.json'}
require = physical.require
sha = physical.sha
load = physical.load
file_stat = physical.file_stat
file_exists = physical.file_exists
read_bytes = physical.read_bytes
read_text = physical.read_text
artifact_files = physical.artifact_files

def configuration_projection(layout, configuration):
    require(type(configuration) is dict and type(configuration.get('physical_runtime')) is dict,
            'drc_configuration_invalid','Use the explicit pinned S12 runtime configuration.')
    runtime = configuration['physical_runtime']
    require(object_hash(runtime)==object_hash(layout['runtime_configuration']),
            'drc_runtime_conflict','S12 must retain the same pinned runtime and PDK as adopted S11.')
    physical.configuration_projection(layout['settings'],runtime,layout.get('source_manifest'))
    profile = configuration.get('profile')
    require(type(profile) is dict and object_hash(profile)==object_hash(load(ROOT/'configs/drc_profile_sky130.json')),
            'drc_profile_invalid','Use both fixed DRC steps and the complete recorded rule options.')
    require(type(configuration.get('working_directory')) is str and Path(configuration['working_directory']).is_absolute(),
            'drc_path_invalid','S12 requires its own absolute isolated work directory.')
    return {'meta':{'version':2,'flow':profile['flow']},'DESIGN_NAME':layout['settings']['top_module'],**copy.deepcopy(profile['config'])}

def drc_capability(configuration):
    if configuration is None:return {'available':False,'reason':'No trusted S12 DRC runtime is configured.'}
    try:
        require(type(configuration) is dict and type(configuration.get('physical_runtime')) is dict,
                'drc_configuration_invalid','Configure the pinned S12 runtime.')
        runtime=configuration['physical_runtime']
        require(runtime.get('appimage_sha256')==physical.IMAGE_SHA and runtime.get('pdk_revision')==physical.PDK_REVISION
                and object_hash(configuration.get('profile'))==object_hash(load(ROOT/'configs/drc_profile_sky130.json')),
                'drc_configuration_invalid','Use the supported fixed DRC runtime/profile.')
        require(file_exists(Path(runtime['appimage_path'])) and file_exists(Path(runtime['pdk_manifest_path'])),
                'drc_runtime_missing','Prepare the pinned physical runtime first.')
        return {'available':True,'reason':None}
    except (DomainError,KeyError,TypeError,OSError,ValueError) as error:return {'available':False,'reason':str(error)}

def fixed_commands(configuration, folder):
    folder=Path(folder).resolve();runtime=configuration['physical_runtime']
    require(folder.parent==Path(configuration['working_directory']).resolve() and folder.name.startswith('hullcirq-drc-'),
            'drc_path_invalid','Use a new configured isolated S12 directory.')
    arguments=[['python3',_wsl_path(folder/'capture_physical_versions.py'),_wsl_path(folder/'tool-versions.json')],
        ['librelane','--pdk','sky130A','--scl','sky130_fd_sc_hd','--pdk-root',_wsl_path(Path(runtime['pdk_root'])),
         '--jobs','2','--run-tag',TAG,'--with-initial-state',_wsl_path(folder/'initial-state.json'),
         '--hide-progress-bar',_wsl_path(folder/'config.json')]]
    return [trusted_command(runtime,runtime['executable'],args,folder) for args in arguments]

def _safe(root, relative):
    require(type(relative) is str and '\\' not in relative and ':' not in relative and not any(ord(c)<32 for c in relative),
            'drc_artifact_path_invalid','Use a safe saved relative artifact path.')
    rel=PurePosixPath(relative)
    require(not rel.is_absolute() and bool(rel.parts) and rel.as_posix()==relative and not any(p in ('.','..') for p in rel.parts),
            'drc_artifact_path_invalid','Artifacts must remain below their saved directory.')
    p=(root/Path(*rel.parts)).resolve()
    require(p.is_relative_to(root) and file_exists(p),'drc_artifact_missing','A retained DRC artifact is missing: '+relative)
    return p

def _entry(identifier,path,root):
    return {'id':identifier,'kind':'drc','relative_path':path.relative_to(root).as_posix(),
        'sha256':sha(path),'bytes':file_stat(path).st_size,'content_type':FILE_TYPES[identifier]}

def _count(value):
    require(type(value) is int and value>=0,'drc_metric_invalid','DRC counts must be explicit nonnegative integers, never missing or nonfinite.')
    return value

def read_markers(path,tool):
    raw=read_bytes(Path(path))
    require(b'<!DOCTYPE' not in raw.upper() and b'<!ENTITY' not in raw.upper(),'drc_report_invalid','External/entity XML declarations are unsupported.')
    document=ET.fromstring(raw)
    require(document.tag=='report-database' and document.find('items') is not None and document.find('categories') is not None,
            'drc_report_invalid','Require a complete KLayout marker database even for zero violations.')
    descriptions={c.findtext('name'):c.findtext('description','') for c in document.findall('./categories/category')}
    violations=[]
    for item in document.findall('./items/item'):
        category=item.findtext('category','');name=category.strip("'")
        violations.append({'tool':tool,'category':category,'description':descriptions.get(name,''),
            'cell':item.findtext('cell',''),'geometry':[v.text or '' for v in item.findall('./values/value')]})
    categories=[{'name':name,'description':text,'count':sum(v['category'].strip("'")==name for v in violations)} for name,text in descriptions.items()]
    return {'error_count':len(violations),'categories':categories},violations

def summarize(root,layout):
    root=Path(root).resolve()
    metrics=load(_safe(root,FIXED_FILES['metrics']))
    magic_count=_count(metrics.get('magic__drc_error__count'))
    klayout_count=_count(metrics.get('klayout__drc_error__count'))
    magic,first=read_markers(_safe(root,FIXED_FILES['magic-markers']),'Magic')
    klayout,second=read_markers(_safe(root,FIXED_FILES['klayout-report']),'KLayout')
    require(magic['error_count']==magic_count and klayout['error_count']==klayout_count,
            'drc_count_conflict','Raw marker items and final metrics must agree for both tools.')
    raw=read_text(_safe(root,FIXED_FILES['magic-report']),encoding='utf-8')
    counts=re.findall(r'^\[INFO\] COUNT: ([0-9]+)\s*$',raw,re.M)
    require(len(counts)==1 and int(counts[0])==magic_count and raw.splitlines()[0]==layout['settings']['top_module'],
            'drc_count_conflict','Magic raw report count and design must match its markers and metrics.')
    counts_json=load(_safe(root,FIXED_FILES['klayout-violations']))
    require(type(counts_json) is dict and _count(counts_json.get('total'))==klayout_count
            and sum(_count(v) for k,v in counts_json.items() if k!='total')==klayout_count,
            'drc_count_conflict','KLayout raw category totals must match final metrics and markers.')
    gds=next(e for e in layout['checks']['artifacts'] if e['id']=='gds')
    summary={'design':layout['settings']['top_module'],'input_gds_sha256':gds['sha256'],'units':'micrometre',
        'magic':magic,'klayout':klayout,'violations':first+second,'limits':load(ROOT/'configs/drc_profile_sky130.json')['limits']}
    status='Passed' if magic_count==klayout_count==0 else 'Failed'
    checks={'source_identity':{'validation_status':'Passed'},'configuration':{'validation_status':'Passed'},
        'drc':{'validation_status':status,'executed':True,'completed':True,'magic_error_count':magic_count,
               'klayout_error_count':klayout_count,'waivers':0,'ignored_categories':[]}}
    return summary,metrics,checks

def validate_drc_result(result,layout,configuration,artifact_root=None):
    """Validate a completed execution, including valid Failed DRC evidence.

    An alternate saved root enables portable inspection; command provenance still
    uses the original unmodified logical work directory. No tools are started.
    """
    config=configuration_projection(layout,configuration)
    logical=Path(result['artifacts_directory']).resolve();root=Path(artifact_root).resolve() if artifact_root else logical
    gds=next(e for e in layout['checks']['artifacts'] if e['id']=='gds')
    require(result.get('origin')=='trusted_fixed_drc_adapter' and result.get('scope')==SCOPE
            and result.get('layout_run_id')==layout['id'] and result.get('layout_record_sha256')==object_hash(layout)
            and result.get('input_gds_sha256')==gds['sha256'] and result.get('configuration_sha256')==object_hash(configuration),
            'drc_source_conflict','Preserve the unchanged complete S11 record, GDS and S12 configuration.')
    require(result.get('status')=='Completed' and result.get('executed') is True and type(result.get('exit_code')) is int and result['exit_code']==0
            and result.get('cleanup_unresolved') is False and len(result.get('commands',[]))==2,
            'drc_execution_conflict','Both actual fixed commands must complete with verified cleanup.')
    runtime=configuration['physical_runtime']
    for operation,record,command,timeout in zip(('version','drc'),result['commands'],fixed_commands(configuration,logical),(120,7200)):
        logs=root/operation;logical_logs=logical/operation
        request=load(logs/'request.json');terminal=load(logs/'process-result.json');start=load(logs/'process-start.json')
        worker_sha=sha(logs/'worker.py')
        expected={'version':'hullcirq-physical-worker-v2','argv':command[command.index('--exec')+1:],
            'cwd':_wsl_path(logical),'timeout_seconds':timeout,'worker_sha256':physical.WORKER_V2_SHA}
        supervisor=trusted_command(runtime,'/usr/bin/python3',[_wsl_path(logical_logs/'worker.py'),_wsl_path(logical_logs/'request.json'),
            '--request-sha256',sha(logs/'request.json'),'--worker-sha256',worker_sha],logical)
        require(worker_sha==physical.WORKER_V2_SHA and record.get('worker_sha256')==worker_sha
                and record.get('command')==command and record.get('supervisor_command')==supervisor
                and object_hash(request)==object_hash(expected) and record.get('request_sha256')==sha(logs/'request.json')
                and record.get('process_start_sha256')==sha(logs/'process-start.json')
                and record.get('status')=='Completed' and record.get('executed') is True
                and type(record.get('exit_code')) is int and record['exit_code']==0
                and all(object_hash(record.get(k))==object_hash(v) for k,v in terminal.items())
                and record.get('request_unchanged_at_completion') is True and record.get('worker_unchanged_at_completion') is True
                and record.get('observed_child_cwd') in (None,_wsl_path(logical)),
                'drc_worker_conflict','Actual frozen worker/request/birth/exit must match the fixed DRC recipe.')
        physical.validate_worker_binding(request,record,start,logical,worker_sha)
        require(record.get('stdout')==read_text((logs/'stdout.log'),encoding='utf-8',errors='replace')
                and record.get('stderr')==read_text((logs/'stderr.log'),encoding='utf-8',errors='replace'),
                'drc_log_conflict','Preserve the original raw tool logs.')
    require(result['stdout']==''.join(r['stdout'] for r in result['commands']) and result['stderr']==''.join(r['stderr'] for r in result['commands']),
            'drc_log_conflict','Combined logs must preserve both actual commands.')
    entries=result.get('artifacts',[])
    require(type(entries) is list and len(entries)==len(FILE_TYPES) and {e['id'] for e in entries}==set(FILE_TYPES),
            'drc_artifact_missing','Require both complete raw reports and all fixed inputs/outputs.')
    for entry in entries:
        require(entry['relative_path']==FIXED_FILES[entry['id']] and entry['content_type']==FILE_TYPES[entry['id']],
                'drc_artifact_conflict','Use the fixed raw output paths and media types.')
        path=_safe(root,entry['relative_path'])
        require(type(entry['bytes']) is int and entry['bytes']>0 and file_stat(path).st_size==entry['bytes'] and sha(path)==entry['sha256'],
                'drc_artifact_changed','Retained artifact bytes changed.')
    require(sha(root/'input.gds')==gds['sha256'] and file_stat((root/'input.gds')).st_size==gds['bytes']
            and object_hash(load(root/'config.json'))==object_hash(config)
            and object_hash(load(root/'initial-state.json'))==object_hash({'gds':_wsl_path(logical/'input.gds'),'metrics':{}}),
            'drc_input_conflict','Require unchanged full GDS and an empty initial metrics set.')
    require(sha(root/'pdk-input-manifest.json')==runtime['pdk_manifest_sha256']
            and load(root/'pdk-input-manifest.json')['ciel_revision']==physical.PDK_REVISION
            and sha(root/'capture_physical_versions.py')==physical.VERSION_CAPTURE_SHA,
            'drc_runtime_conflict','Retain the unchanged pinned PDK manifest and version-capture source.')
    require(sha(root/'drc_tools.py')==result.get('adapter_source_sha256'),'drc_adapter_source_conflict','Preserve the frozen adapter source from before execution.')
    inputs=load(root/'input-manifest.json')
    require(object_hash(inputs)==object_hash({'layout_run_id':layout['id'],'layout_record_sha256':object_hash(layout),
            'input_gds':gds,'configuration':configuration,'adapter_source_sha256':result['adapter_source_sha256']}), 'drc_input_conflict','Retain the exact S11-to-S12 input binding.')
    versions=load(root/'tool-versions.json')
    require(versions.get('librelane')==physical.RELEASE and set(versions.get('tools',{}))=={'magic','klayout','yosys','openroad','ciel'}
            and all(type(v.get('exit_code')) is int and v['exit_code']==0 for v in versions['tools'].values()),
            'drc_version_conflict','Actual bundled tool-version queries must succeed.')
    # Re-read the resolved per-step settings, proving no skipped deck or blackboxes.
    for step in ('1-magic-drc','2-klayout-drc'):
        resolved=load(root/'runs/drc'/step/'config.json')
        require(resolved.get('DESIGN_NAME')==layout['settings']['top_module'],'drc_configuration_conflict','Retain the expected top cell.')
        if step.startswith('1'):
            require(resolved.get('MAGIC_DRC_USE_GDS') is True and resolved.get('MAGIC_DRC_MAGLEFS') in (None,[])
                    and resolved.get('MAGIC_GDS_FLATGLOB') in (None,[]),'drc_configuration_conflict','Run full GDS checks without abstract-cell substitutions.')
            require(str(resolved.get('MAGICRC','')).endswith('/libs.tech/magic/sky130A.magicrc'),
                    'drc_configuration_conflict','Use the pinned SKY130 Magic technology.')
        else:
            require(str(resolved.get('KLAYOUT_DRC_RUNSET','')).endswith('/libs.tech/klayout/drc/sky130A_mr.drc')
                    and object_hash(resolved.get('KLAYOUT_DRC_DEFINES'))==object_hash(config['KLAYOUT_DRC_DEFINES'])
                    and resolved.get('KLAYOUT_DRC_THREADS')==2,'drc_configuration_conflict','Run the pinned KLayout deck and complete saved options.')
    state=load(root/FIXED_FILES['final-state']);summary,metrics,checks=summarize(root,layout)
    require(state.get('gds')==_wsl_path(logical/'input.gds') and object_hash(state.get('metrics'))==object_hash(metrics)
            and object_hash(result.get('metrics'))==object_hash(metrics) and object_hash(result.get('checks'))==object_hash(checks)
            and object_hash(load(root/'drc-summary.json'))==object_hash(summary) and object_hash(result.get('summary'))==object_hash(summary)
            and result.get('validation_status')==checks['drc']['validation_status'],
            'drc_result_conflict','Reconstruct checks from actual raw reports, final state and metrics.')
    retained=result.get('retained_files',[])
    require(type(retained) is list and len({e['relative_path'] for e in retained})==len(retained),'drc_retained_invalid','Require unique retained raw records.')
    for entry in retained:
        path=_safe(root,entry['relative_path'])
        require(file_stat(path).st_size==entry['bytes'] and sha(path)==entry['sha256'],'drc_retained_changed','A retained raw record changed.')

def _retain(result):
    root=Path(result['artifacts_directory'])
    result['artifacts']=[_entry(k,root/v,root) for k,v in FIXED_FILES.items() if file_exists((root/v))]
    selected=[]
    for path in sorted(artifact_files(root)):
        if file_exists(path) and path.suffix in ('.json','.log','.tcl','.py','.lyrdb','.rpt') and path.name!='adapter-report.json':
            selected.append({'relative_path':path.relative_to(root).as_posix(),'sha256':sha(path),'bytes':file_stat(path).st_size})
    result['retained_files']=selected

def run_drc(layout,configuration,cancel_event=None):
    config=configuration_projection(layout,configuration);runtime=configuration['physical_runtime']
    parent=Path(configuration['working_directory']).resolve();parent.mkdir(parents=True,exist_ok=True)
    root=Path(tempfile.mkdtemp(prefix='hullcirq-drc-',dir=parent))
    gds=next(e for e in layout['checks']['artifacts'] if e['id']=='gds')
    result={'origin':'trusted_fixed_drc_adapter','scope':SCOPE,'status':'Failed','validation_status':'Failed','executed':False,'exit_code':None,
        'layout_run_id':layout['id'],'layout_record_sha256':object_hash(layout),'input_gds_sha256':gds['sha256'],
        'configuration_sha256':object_hash(configuration),'artifacts_directory':str(root),'commands':[],'checks':{},
        'metrics':{},'artifacts':[],'retained_files':[],'diagnostics':[],'stdout':'','stderr':'','cleanup_unresolved':False,
        'adapter_source_sha256':sha(Path(__file__))}
    try:
        require(sha(runtime['appimage_path'])==physical.IMAGE_SHA,'drc_runtime_changed','Pinned AppImage bytes changed.')
        require(sha(runtime['pdk_manifest_path'])==runtime['pdk_manifest_sha256'],'drc_pdk_changed','Pinned PDK manifest changed.')
        pdk_manifest=load(runtime['pdk_manifest_path']);pdk=Path(pdk_manifest['root']).absolute()
        require(pdk_manifest['ciel_revision']==physical.PDK_REVISION and pdk.is_relative_to(Path(runtime['pdk_root']).resolve()),
                'drc_pdk_changed','Retain the exact pinned PDK below the configured cache.')
        for relative,entry in pdk_manifest['files'].items():
            physical.verify_pdk_file(pdk,relative,entry,'drc_pdk_changed')
        for relative,digest in configuration['profile']['deck_files'].items():
            require(sha(_safe(pdk,relative))==digest,'drc_deck_changed','Pinned DRC deck changed.')
        source=_safe(Path(layout['checks']['artifacts_directory']).resolve(),gds['relative_path'])
        require(sha(source)==gds['sha256'] and file_stat(source).st_size==gds['bytes'],'drc_gds_changed','The adopted S11 GDS changed.')
        (root/'drc_tools.py').write_bytes(read_bytes(Path(__file__)))
        require(sha(root/'drc_tools.py')==result['adapter_source_sha256'],'drc_adapter_source_conflict','Adapter source changed during input freeze.')
        (root/'input.gds').write_bytes(read_bytes(source))
        (root/'pdk-input-manifest.json').write_bytes(read_bytes(Path(runtime['pdk_manifest_path'])))
        (root/'capture_physical_versions.py').write_bytes(read_bytes((ROOT/'scripts/capture_physical_versions.py')))
        require(sha(root/'capture_physical_versions.py')==physical.VERSION_CAPTURE_SHA,'drc_version_conflict','Use the pinned version-capture source.')
        for name,value in [('config.json',config),('initial-state.json',{'gds':_wsl_path(root/'input.gds'),'metrics':{}}),
            ('input-manifest.json',{'layout_run_id':layout['id'],'layout_record_sha256':object_hash(layout),'input_gds':gds,'configuration':configuration,'adapter_source_sha256':result['adapter_source_sha256']})]:
            (root/name).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf-8')
        for operation,command,timeout in zip(('version','drc'),fixed_commands(configuration,root),(120,7200)):
            execution=physical._execute(command,runtime,root,operation,cancel_event,timeout)
            result['commands'].append(execution);result['stdout']+=execution['stdout'];result['stderr']+=execution['stderr']
            result['executed']=any(c['executed'] for c in result['commands']);result['exit_code']=execution['exit_code'];result['cleanup_unresolved']=execution.get('cleanup_unresolved') is True
            if execution['status']!='Completed' or execution['exit_code']!=0:
                result['status']='Cancelled' if execution['status']=='Cancelled' else 'Failed'
                if not physical._record_cancelled_command(result, execution, 'drc'):
                    result['diagnostics'].append({'code':'drc_tool_failed','severity':'error','message':'Inspect retained '+operation+' command output: '+execution['status']})
                return result
        result['status']='Completed'
        summary,metrics,checks=summarize(root,layout)
        (root/'drc-summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n',encoding='utf-8')
        result.update(metrics=metrics,checks=checks,summary=summary,validation_status=checks['drc']['validation_status'])
        if result['validation_status']=='Failed':result['diagnostics'].append({'code':'drc_violations','severity':'error','message':'Actual Magic/KLayout violations remain; inspect raw reports and locations.'})
        _retain(result)
        validate_drc_result(result,layout,configuration)
    except (DomainError,OSError,ValueError,KeyError,TypeError,StopIteration,ET.ParseError) as error:
        result['validation_status']='Failed';result['diagnostics'].append({'code':getattr(error,'code','drc_tool_error'),'severity':'error','message':str(error)})
    finally:_retain(result)
    return result
