"""Pinned, shell-free S11 LibreLane adapter and saved-proof validation.

Fresh PDK mapping uses the unchanged adopted top and every manifest RTL file.
Earlier generic netlist verification is a lineage prerequisite, not mapped/SDF
verification.
"""
from __future__ import annotations
import copy
from decimal import Decimal
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import subprocess
import tempfile
import time

from .domain import DomainError, VERILOG_IDENTIFIER, VERILOG_KEYWORDS
from .global_workflow import source_bundle
from .store import strict_loads
from .verification import content_hash,object_hash,trusted_command,_wsl_path
from .physical_repair import is_repair, has_pnr_headroom, pnr_sdc, implementation_kind, uses_closure_flow, closure_launcher, V5_LAUNCHER_SHA, validate_configuration as validate_repair_configuration, snapshot_resume, validate_resume
from . import physical_repair_generic as generic_repair
from .block_recipe import (is_block_configuration, effective_configuration as block_effective_configuration,
                           source_input as block_source_input, recipe_for, runtime_for,
                           BLOCK_ARTIFACTS, OPENROAD_COMMIT, V1 as BLOCK_V1)

RELEASE='3.0.16'
IMAGE_SHA='428df0d6d7ce167de6a31bc46001f1167b7fb1fbc1ed95fba278367a95883147'
PDK_REVISION='8afc8346a57fe1ab7934ba5a6056ea8b43078e71'
SDC_SHA='34c8f331c366db51a78ed8a0d2a7bbac3b6c1cfe0277a04c6aca9ba4948e7f78'
WORKER_V1_SHA='955341ebe17cbf9457dddada8814c5a6588ef06fab19e7e207b7a72b006a09ff'
WORKER_V2_SHA='589b6b2841f1e31b8fde26f9b9fd8f872b2c9de0e396fb99bdb5a920b1a2220f'
VERSION_CAPTURE_SHA='d1aa8290668ec384c2c556a5eec60d491f74696c83aa9cacdc3319dc93173ce1'
# Public historical constants remain the exact v1 pins for old callers/tests.
BLOCK_FLOW_SHA=BLOCK_V1.flow_sha256
BLOCK_RUNTIME_SHA=BLOCK_V1.runtime_sha256
SCOPE='SKY130_routed_layout_not_DRC_LVS_SDF'
TAG='physical'
ROOT=Path(__file__).resolve().parents[2]
LEGACY_NODE_IDS=('node-control','node-buffer','node-scheduler','node-pe','node-post','node-fifo')
NODE_FILE_IDENTIFIER=re.compile(r'[A-Za-z_][A-Za-z0-9_-]*')

def _has_pnr_headroom(configuration):
    return has_pnr_headroom(configuration) or generic_repair.is_generic(configuration)

def _closure_recipe(configuration):
    if generic_repair.is_generic(configuration):
        recipe=generic_repair.recipe_for(configuration)
        require(sha(ROOT/'configs'/recipe.PROFILE_FILE)==recipe.PROFILE_SHA
                and sha(ROOT/'scripts'/recipe.LAUNCHER)==recipe.LAUNCHER_SHA,
                'generic_physical_recipe_changed','Preserve the pinned generic fresh-closure profile and launcher.')
        require('resume' not in configuration and 'block_plan' not in configuration,
                'generic_physical_fresh_required','Generic electrical closure requires a complete fresh mixed-placement run.')
        return recipe.LAUNCHER,recipe.FLOW,recipe.LAUNCHER_SHA
    return closure_launcher(configuration) if uses_closure_flow(configuration) else None

def require(condition,code,message):
    if not condition:raise DomainError(code,message)

def effective_configuration(configuration,design,root=None):
    """Preflight new saved plans without changing the frozen v1 recipe.

    Historical configuration projection deliberately does not use this guard:
    failed non-grid attempts must remain reconstructible and inspectable.
    """
    result=block_effective_configuration(configuration,design,root)
    if is_block_configuration(result):
        plan=result['block_plan']
        rectangles=[('Core',plan['core_um']),*(('Region '+region['id'],region['rect_um']) for region in plan['regions'])]
        for label,rectangle in rectangles:
            for axis,value in zip(('x_min','y_min','x_max','y_max'),rectangle):
                ticks=Decimal(str(value))*200
                # Match the client float-boundary tolerance, without changing
                # the saved value or weakening the frozen OpenDB runtime guard.
                require(abs(ticks-ticks.to_integral_value())<Decimal('1e-7'),'block_region_coordinate_grid',
                        f'{label} {axis} = {value} um is not on the fixed 0.005 um (1/200 um) placement grid. '
                        'Regenerate the tiling or explicitly edit the saved coordinate before S11; coordinates are not rounded automatically.')
    return result

def io_path(path):
    """Use extended Windows paths only at the I/O boundary, never in recipes."""
    value=os.path.abspath(os.fspath(path))
    if os.name=='nt' and not value.startswith('\\\\?\\'):
        require(re.match(r'^[A-Za-z]:\\',value) is not None,'physical_io_path','Use a local Windows drive for physical I/O.')
        value='\\\\?\\'+value
    return Path(value)

def file_stat(path):return io_path(path).stat()
def file_exists(path):return io_path(path).is_file()
def read_bytes(path):return io_path(path).read_bytes()
def read_text(path,**kwargs):return io_path(path).read_text(**kwargs)

def sha(path):
    with io_path(path).open('rb') as handle:return hashlib.file_digest(handle,'sha256').hexdigest()

def load(path):return strict_loads(read_text(path,encoding='utf-8'))

def verify_pdk_file(root,relative,metadata,code='physical_pdk_conflict'):
    """Check every lexical component without following links, then exact bytes."""
    from pathlib import PurePosixPath
    require(type(relative) is str and '\\' not in relative and ':' not in relative,
            code+'_path','PDK inventory requires safe relative paths.')
    rel=PurePosixPath(relative)
    require(bool(rel.parts) and not rel.is_absolute() and rel.as_posix()==relative
            and all(part not in ('.','..') for part in rel.parts),code+'_path','PDK inventory path escaped its root.')
    root=Path(root).absolute();path=root
    require('..' not in root.parts,code+'_path','PDK root must not contain parent traversal.')
    try:
        for ancestor in reversed(root.parents):
            parent_info=os.lstat(io_path(ancestor))
            require(stat.S_ISDIR(parent_info.st_mode) and not stat.S_ISLNK(parent_info.st_mode)
                    and not getattr(parent_info,'st_file_attributes',0)&0x400,
                    code+'_link','PDK root ancestor is not an ordinary directory: '+relative)
        for part in (None,*rel.parts):
            if part is not None:path=path/part
            info=os.lstat(io_path(path))
            require(not stat.S_ISLNK(info.st_mode) and not getattr(info,'st_file_attributes',0)&0x400,
                    code+'_link','PDK inventory contains a link/reparse point: '+relative)
            if path!=root/Path(*rel.parts):
                require(stat.S_ISDIR(info.st_mode),code+'_kind','PDK path parent is not a directory: '+relative)
        require(stat.S_ISREG(info.st_mode),code+'_kind','PDK input is not a regular file: '+relative)
        size=info.st_size;digest=sha(path)
    except FileNotFoundError as error:
        raise DomainError(code+'_missing','Installed PDK input is missing: '+relative) from error
    except OSError as error:
        raise DomainError(code+'_unreadable','Installed PDK input cannot be read: '+relative+' ('+type(error).__name__+')') from error
    require(size==metadata['bytes'] and digest==metadata['sha256'],code,'Installed PDK bytes changed: '+relative)
    return path

def artifact_files(folder,*,reject_links=False):
    """Complete long-path traversal; never descend through directory links."""
    folder=Path(folder).resolve();pending=[folder]
    while pending:
        parent=pending.pop()
        try:entries=os.scandir(io_path(parent))
        except FileNotFoundError:
            if parent==folder:return
            raise
        with entries:
            for entry in entries:
                path=parent/entry.name
                info=entry.stat(follow_symlinks=False)
                linked=stat.S_ISLNK(info.st_mode) or getattr(info,'st_file_attributes',0)&0x400
                require(not reject_links or not linked,'physical_output_path_invalid','Strict runtime inventory contains a link/reparse point.')
                if stat.S_ISDIR(info.st_mode) and not linked:pending.append(path)
                elif entry.is_file():
                    target=path.resolve()
                    require(target.is_relative_to(folder),'physical_output_path_invalid','Artifact link escaped the isolated run.')
                    yield path
                elif linked:
                    require(path.resolve().is_relative_to(folder),'physical_output_path_invalid','Artifact directory link escaped the isolated run.')

def artifact_glob(folder,pattern):
    from pathlib import PurePosixPath
    depth=len(PurePosixPath(pattern).parts)
    return [path for path in artifact_files(folder)
            if len(path.relative_to(folder).parts)==depth and path.relative_to(folder).match(pattern)]

def _top_identifier(value):
    require(type(value) is str and VERILOG_IDENTIFIER.fullmatch(value) is not None and value not in VERILOG_KEYWORDS,
            'physical_settings_unsupported','The physical top must be one plain non-keyword Verilog identifier.')
    return value

def source_filenames(source_manifest=None):
    """Return safe deterministic node filenames without changing legacy callers.

    DRC/LVS validation historically called ``configuration_projection`` without
    the S08 manifest.  That path retains the original six filenames exactly.
    Every fresh/revalidated S11 call supplies its immutable source manifest.
    """
    if source_manifest is None:
        node_ids=LEGACY_NODE_IDS
    else:
        require(type(source_manifest) is dict and type(source_manifest.get('nodes')) is list and source_manifest['nodes'],
                'physical_source_manifest_invalid','Physical mapping requires a nonempty adopted source manifest.')
        node_ids=[];seen_files={'candidate_top.v'};seen_artifact_ids={'rtl-top'}
        for node in source_manifest['nodes']:
            node_id=node.get('node_id') if type(node) is dict else None
            require(type(node_id) is str and NODE_FILE_IDENTIFIER.fullmatch(node_id) is not None,
                    'physical_source_identifier_invalid','Each physical source node ID must be a safe filename identifier.')
            filename=(node_id+'.v').casefold();artifact_id=('rtl-'+node_id).casefold()
            require(filename not in seen_files and artifact_id not in seen_artifact_ids,
                    'physical_source_identifier_invalid','Physical source node IDs must produce unique nonreserved filenames and artifact IDs.')
            seen_files.add(filename);seen_artifact_ids.add(artifact_id);node_ids.append(node_id)
    return ['candidate_top.v',*(node_id+'.v' for node_id in node_ids)]

def load_tool_json(path):
    """Preserve LibreLane's nonstandard nonfinite tokens as explicit tags.

    Raw tool bytes remain the downloadable artifact. A tagged nonfinite value
    can never satisfy the finite numeric metrics required by metric_checks.
    Project/config/request JSON still uses strict_loads without this exception.
    """
    def unique(pairs):
        result={}
        for key,value in pairs:
            require(key not in result,'physical_duplicate_tool_key','Duplicate key in raw tool JSON: '+key)
            result[key]=value
        return result
    return json.loads(read_text(Path(path),encoding='utf-8'),object_pairs_hook=unique,
                      parse_constant=lambda value:{'librelane_nonfinite':value})

def configuration_projection(settings,configuration,source_manifest=None):
    require(type(configuration) is dict and configuration.get('kind')=='wsl' and configuration.get('release')==RELEASE
            and configuration.get('appimage_sha256')==IMAGE_SHA and configuration.get('pdk_revision')==PDK_REVISION
            and configuration.get('base_sdc_sha256')==SDC_SHA and bool(configuration.get('origin')),
            'physical_configuration_invalid','Use the pinned LibreLane 3.0.16 / SKY130 execution profile.')
    top=_top_identifier(settings.get('top_module'))
    source_design=source_manifest.get('design') if type(source_manifest) is dict else None
    generic_contract=source_design.get('global_verification') if type(source_design) is dict else None
    generic_design=(type(generic_contract) is dict and generic_contract.get('kind')=='generic_cycle_vectors'
                    and type(generic_contract.get('version')) is int and generic_contract['version']==1)
    if generic_design:
        clock=_top_identifier(settings.get('clock_name'))
        reset=_top_identifier(settings.get('reset_name'))
        require(clock!=reset,'physical_settings_unsupported','Clock and synchronous reset must be distinct ports.')
    require((generic_design or settings.get('clock_name')=='clk')
            and type(settings.get('clock_period_ns')) in (int,float) and math.isfinite(settings['clock_period_ns'])
            and settings['clock_period_ns']>0 and settings.get('reset_kind')=='synchronous'
            and (settings.get('reset_active') in ('high','low') if generic_design else settings.get('reset_active')=='high')
            and (generic_design or settings.get('reset_name')=='rst')
            and settings.get('pdk')=='sky130A' and settings.get('cell_library')=='sky130_fd_sc_hd',
            'physical_settings_unsupported','Use the saved single-clock, synchronous-reset digital design and selected SKY130A / HD toolchain.')
    profile=configuration.get('profile')
    block_mode=is_block_configuration(configuration)
    block_recipe=recipe_for(configuration)
    generic_mode=generic_repair.is_generic(configuration)
    profile_name=generic_repair.recipe_for(configuration).PROFILE_FILE if generic_mode else block_recipe.profile_file if block_mode else ('physical_profile_sky130_repair_'+profile['profile_version'].rsplit('-',1)[-1]+'.json') if is_repair(configuration) else 'physical_profile_sky130.json'
    require(type(profile) is dict and object_hash(profile)==object_hash(load(ROOT/'configs'/profile_name)),
            'physical_profile_invalid','Use the complete versioned physical assumptions; do not relabel them as original GUI inputs.')
    if block_mode:
        require(sha(ROOT/'configs'/block_recipe.profile_file)==block_recipe.profile_sha256,
                'block_region_recipe_changed','The pinned block-placement profile changed.')
    if generic_mode:
        generic_repair.validate_configuration(configuration,settings,source_manifest)
        _closure_recipe(configuration)
    elif is_repair(configuration):validate_repair_configuration(configuration)
    else:require('resume' not in configuration,'physical_resume_configuration','The original fresh-mapping profile cannot resume a checkpoint.')
    require(type(configuration.get('executable')) is str and configuration['executable'].endswith('/librelane-devshell-x86_64.AppImage')
            and configuration['executable'].startswith('/') and type(configuration.get('working_directory')) is str
            and Path(configuration['working_directory']).is_absolute()
            and type(configuration.get('appimage_path')) is str
            and configuration['executable']==_wsl_path(Path(configuration['appimage_path'])),
            'physical_configuration_invalid','Use a fixed absolute AppImage and retained working directory.')
    config=copy.deepcopy(profile['config'])
    if generic_mode and profile['profile_version']=='hullcirq-sky130-generic-closure-v2':
        config['FP_CORE_UTIL']=configuration['generic_retry_source_binding']['core_utilization']
    config.update(DESIGN_NAME=top,VERILOG_FILES=['dir::'+name for name in source_filenames(source_manifest)],
                  CLOCK_PORT=settings['clock_name'],CLOCK_PERIOD=settings['clock_period_ns'],PNR_SDC_FILE='dir::physical.sdc',SIGNOFF_SDC_FILE='dir::physical.sdc')
    if block_mode:
        inputs=block_source_input(configuration,source_manifest,top)
        core=inputs['plan']['core_um']
        config.update(CORE_AREA=core,DIE_AREA=[0,0,core[2]+10,core[3]+10],HULLCIRQ_BLOCK_INPUT='dir::block-input.json')
        require(sha(ROOT/'scripts'/block_recipe.launcher)==block_recipe.flow_sha256 and sha(ROOT/'src/hullcirq'/block_recipe.runtime_file)==block_recipe.runtime_sha256,
                'block_region_recipe_changed','The pinned block-placement flow or pure runtime changed.')
    if _has_pnr_headroom(configuration):config['PNR_SDC_FILE']='dir::physical_pnr.sdc'
    return config

def fixed_commands(configuration,folder,recipe='v2'):
    block_recipe=recipe_for(configuration)
    folder=Path(folder).resolve()
    require(folder.parent==Path(configuration['working_directory']).resolve() and folder.name.startswith('hullcirq-layout-'),
            'physical_path_conflict','Physical tools require their configured isolated result directory.')
    version_args=['python3',_wsl_path(folder/'capture_physical_versions.py' if recipe=='v2' else ROOT/'scripts/capture_physical_versions.py'),_wsl_path(folder/'tool-versions.json')]
    layout_args=['librelane','--flow','Classic','--pdk','sky130A','--scl','sky130_fd_sc_hd','--pdk-root',_wsl_path(Path(configuration['pdk_root'])),
                 '--jobs','2','--run-tag',TAG,'--to','KLayout.Render','--hide-progress-bar',_wsl_path(folder/'config.json')]
    if is_repair(configuration):
        validate_repair_configuration(configuration)
        layout_args[-1:-1]=['--from',configuration['resume']['from_step'],'--with-initial-state',_wsl_path(folder/'resume-state.json')]
    closure=_closure_recipe(configuration)
    if closure is not None:
        launcher, flow, _ = closure
        layout_args[0:3]=['python3',_wsl_path(folder/launcher),'--flow',flow]
    if block_recipe is not None:
        layout_args[0:3]=['python3',_wsl_path(folder/block_recipe.launcher),'--flow',block_recipe.flow]
    return [trusted_command(configuration,configuration['executable'],args,folder) for args in (version_args,layout_args)]

def _execute(command,configuration,folder,operation,cancel_event,timeout):
    """Supervise Linux process groups; closing wsl.exe alone is insufficient."""
    if cancel_event is not None and cancel_event.is_set():
        return {'command':command,'executed':False,'exit_code':None,'status':'Cancelled','stdout':'','stderr':''}
    logs=folder/operation;logs.mkdir()
    argv=command[command.index('--exec')+1:]
    worker=logs/'worker.py'
    worker.write_bytes(read_bytes((ROOT/'scripts/physical_worker_v2.py')))
    worker_sha=sha(worker)
    require(worker_sha==WORKER_V2_SHA,'physical_worker_conflict','Use the fixed supported supervisor version before launching tools.')
    request={'version':'hullcirq-physical-worker-v2','argv':argv,'cwd':_wsl_path(folder),'timeout_seconds':timeout,'worker_sha256':worker_sha}
    (logs/'request.json').write_text(json.dumps(request,indent=2)+'\n',encoding='utf-8')
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
    cleanup=load(logs/'cleanup-result.json') if file_exists((logs/'cleanup-result.json')) else {}
    cleanup_verified=cleanup.get('whole_process_group_terminated_on_cancel') is True
    if not (logs/'process-result.json').exists():
        return {'command':command,'supervisor_command':supervisor,'worker_sha256':worker_sha,'request_sha256':request_sha,
                'executed':file_exists((logs/'process-start.json')),'exit_code':None,'status':'Failed','recovery':recovery,'cleanup_unresolved':not cleanup_verified,
                'stdout':read_text((logs/'stdout.log'),encoding='utf-8',errors='replace') if file_exists((logs/'stdout.log')) else supervisor_out,
                'stderr':(read_text((logs/'stderr.log'),encoding='utf-8',errors='replace') if file_exists((logs/'stderr.log')) else '')+supervisor_err+'\nLinux worker did not save an exit record; tool termination is not assumed.'}
    result=load(logs/'process-result.json')
    require(result['argv']==argv,'physical_command_conflict','The Linux worker executed a different command.')
    result.update(command=command,supervisor_command=supervisor,worker_sha256=worker_sha,request_sha256=request_sha,
                  stdout=read_text((logs/'stdout.log'),encoding='utf-8',errors='replace'),stderr=read_text((logs/'stderr.log'),encoding='utf-8',errors='replace'),
                  supervisor_stdout=supervisor_out,supervisor_stderr=supervisor_err)
    if recovery is not None:
        result['recovery']=recovery;result['status']='Failed'
    result['cleanup_unresolved']=not (result.get('whole_process_group_terminated') is True or cleanup_verified)
    return result

def validate_worker_binding(request,record,start,folder,worker_hash):
    """Cross-bind the raw birth record, request and terminal execution proof."""
    expected={'version':'hullcirq-physical-worker-v2','argv':request['argv'],'cwd':_wsl_path(folder),
              'request_sha256':record['request_sha256'],'worker_sha256':worker_hash}
    require(all(object_hash(start.get(key))==object_hash(value) and object_hash(record.get(key))==object_hash(value) for key,value in expected.items())
            and all(type(record.get(key)) is int and record[key]>0 and type(start.get(key)) is int and start[key]==record[key] for key in ('process_group','leader_starttime'))
            and type(start.get('boot_id')) is str and bool(start['boot_id'])
            and start.get('observed_child_cwd')==record.get('observed_child_cwd')
            and record.get('whole_process_group_terminated') is True and record.get('cleanup_unresolved') is False,
            'physical_worker_conflict','The worker request, process birth and verified exit must describe the same actual execution.')

def _native(path,folder):
    require(type(path) is str,'physical_output_missing','A concrete physical output path is required.')
    match=re.fullmatch(r'/mnt/([a-zA-Z])/(.+)',path)
    candidate=Path(match[1].upper()+':/'+match[2]) if match else Path(path)
    candidate=candidate.resolve()
    require(candidate.is_relative_to(folder) and file_exists(candidate),'physical_output_path_invalid','Physical output must be a real file within the isolated run.')
    return candidate

def _entry(identifier,path,folder,content_type):
    return {'id':identifier,'kind':'physical_layout','relative_path':path.relative_to(folder).as_posix(),'sha256':sha(path),'bytes':file_stat(path).st_size,'content_type':content_type}

def metric_checks(metrics,require_electrical=False):
    require(type(metrics) is dict,'physical_metrics_invalid','Retain the actual flat final metrics object.')
    required=('design__core__area','design__die__area','design__instance__area','design__instance__count','route__wirelength',
              'route__drc_errors','design__disconnected_pin__count','design__instance_unmapped__count','synthesis__check_error__count',
              'timing__setup__wns','timing__hold__wns','timing__setup_vio__count','timing__hold_vio__count')
    for name in required:
        value=metrics.get(name)
        require(type(value) in (int,float) and math.isfinite(value),'physical_metric_missing','Missing/nonfinite physical metric: '+name)
    route_ok=all(metrics[name]==0 for name in ('route__drc_errors','design__disconnected_pin__count','design__instance_unmapped__count','synthesis__check_error__count'))
    timing_ok=all(metrics[name]>=0 for name in ('timing__setup__wns','timing__hold__wns')) and all(metrics[name]==0 for name in ('timing__setup_vio__count','timing__hold_vio__count'))
    area_ok=all(metrics[name]>0 for name in ('design__core__area','design__die__area','design__instance__area','design__instance__count','route__wirelength'))
    checks={'configuration':{'validation_status':'Passed'},'source_identity':{'validation_status':'Passed'},
            'routing':{'validation_status':'Passed' if route_ok and area_ok else 'Failed','executed':True,'completed':True,'routing_DRC_is_not_signoff_DRC':True},
            'timing':{'validation_status':'Passed' if timing_ok else 'Failed','executed':True,'scope':'extracted_STA_not_dynamic_SDF_simulation',
                      'setup_wns_ns':metrics['timing__setup__wns'],'hold_wns_ns':metrics['timing__hold__wns']}}
    if require_electrical:
        names=('design__max_slew_violation__count','design__max_cap_violation__count','design__max_fanout_violation__count')
        for name in names:
            require(type(metrics.get(name)) is int and metrics[name]>=0,'physical_metric_missing','Require the actual nonnegative electrical violation count: '+name)
        checks['electrical']={'validation_status':'Passed' if all(metrics[name]==0 for name in names) else 'Failed',
                              'executed':True,'max_slew_violations':metrics[names[0]],'max_capacitance_violations':metrics[names[1]],
                              'max_fanout_violations':metrics[names[2]],'scope':'recorded_multicorner_slew_capacitance_fanout_constraints'}
    return checks

def _configuration_metric_checks(metrics,configuration):
    """New generic closure requires real electrical counts at every corner.

    Historical profiles keep their original metric projection. A missing
    corner is never replaced by an aggregate zero or inferred from a tool exit.
    """
    generic_mode=generic_repair.is_generic(configuration)
    checks=metric_checks(metrics,is_repair(configuration) or generic_mode)
    if generic_mode:
        corners=configuration['profile']['config']['STA_CORNERS']
        names={'slew':'design__max_slew_violation__count',
               'capacitance':'design__max_cap_violation__count',
               'fanout':'design__max_fanout_violation__count'}
        observed={}
        for corner in corners:
            observed[corner]={}
            for label,name in names.items():
                value=metrics.get(name+'__corner:'+corner)
                require(type(value) is int and value>=0,'physical_metric_missing',
                        'Require the actual nonnegative electrical count at every signoff corner: '+name+'__corner:'+corner)
                observed[corner][label]=value
        checks['electrical'].update(corner_counts=observed,corner_count=len(corners))
        if any(value!=0 for counts in observed.values() for value in counts.values()):
            checks['electrical']['validation_status']='Failed'
    return checks

def _check_artifact(path,identifier,settings):
    raw=read_bytes(path)
    require(len(raw)>0,'physical_output_empty','A physical artifact is empty: '+identifier)
    if identifier=='gds':require(len(raw)>1024 and raw[:4]==b'\x00\x06\x00\x02','physical_gds_invalid','GDS must have a valid stream header and nonempty geometry.')
    if identifier=='png':require(len(raw)>1024 and raw[:8]==b'\x89PNG\r\n\x1a\n' and int.from_bytes(raw[16:20],'big')>0 and int.from_bytes(raw[20:24],'big')>0,'physical_png_invalid','Retain the actual nonempty rendered layout.')
    if identifier=='def':
        text=raw.decode('utf-8')
        require('DESIGN '+settings['top_module']+' ;' in text and 'END DESIGN' in text and re.search(r'COMPONENTS\s+[1-9][0-9]*\s*;',text) and re.search(r'NETS\s+[1-9][0-9]*\s*;',text) and ('+ ROUTED' in text or '+ FIXED' in text),'physical_def_invalid','DEF must contain the routed target design.')

def _block_region_checks(configuration,manifest,settings,paths):
    runtime=runtime_for(configuration)
    block_inputs=block_source_input(configuration,manifest,settings['top_module'])
    require(object_hash(load(paths['block-input']))==object_hash(block_inputs)
            and object_hash(load(paths['block-plan']))==configuration['block_plan_sha256'], 'block_region_source','Retain the unchanged current physical plan and source-bound input.')
    ownership=runtime.build_ownership(load(paths['block-synthesis']),block_inputs)
    require(object_hash(load(paths['block-ownership']))==object_hash(ownership),'block_region_source','Rebuild region ownership only from the preserved technology-mapped synthesis hierarchy.')
    proof=load(paths['block-placement-proof'])
    runtime.validate_capacity(ownership,load(paths['block-capacity']))
    runtime.validate_placement(ownership,proof)
    runtime.validate_def_binding(read_text(paths['def'],encoding='utf-8'),ownership,proof)
    return {'validation_status':'Passed','executed':True,'placement_mode':'same_chip_fence_regions',
            'regions':len(ownership['regions']),'mapped_cells':len(proof['cells']),'outside_region_cells':0,
            'ownership_origin':ownership['ownership_origin'],'plan_sha256':configuration['block_plan_sha256'],'scope':ownership['scope']}

def _validate_generic_fresh_mapping(result,folder,configuration):
    if not generic_repair.is_generic(configuration):return
    synthesis=list(artifact_glob((folder/'runs'/TAG),'*-yosys-synthesis/state_out.json'))
    require(result.get('implementation_kind')==generic_repair.IMPLEMENTATION_KIND
            and result.get('upstream_technology_mapping_reused') is False
            and result.get('technology_mapping_executed') is True and len(synthesis)==1
            and not (folder/'resume-state.json').exists() and not (folder/'resume-manifest.json').exists(),
            'generic_physical_fresh_required','Require actual fresh technology mapping and no checkpoint reuse for generic closure.')

def _validate_complete_layout_result(result,rtl,manifest,settings,configuration,expected_status):
    """Rebuild the fixed recipe and verify retained output bytes; no tools run."""
    expected_config=configuration_projection(settings,configuration,manifest)
    require(type(result) is dict and result.get('origin')=='trusted_fixed_tool_adapter' and result.get('scope')==SCOPE
            and result.get('global_rtl_sha256')==content_hash(rtl) and result.get('source_manifest_sha256')==object_hash(manifest)
            and result.get('settings_sha256')==object_hash(settings) and result.get('runtime_configuration_sha256')==object_hash(configuration)
            and object_hash(result.get('source_bundle'))==object_hash(source_bundle(rtl,manifest)),'physical_source_conflict','Preserve the exact source/settings/profile identity.')
    folder=Path(result['artifacts_directory']).resolve()
    if generic_repair.is_generic(configuration):
        generic_repair.validate_source(configuration,rtl,manifest,settings)
        _validate_generic_fresh_mapping(result,folder,configuration)
    if is_repair(configuration):
        validate_resume(configuration,folder,rtl,manifest,settings)
        require(result.get('implementation_kind')==implementation_kind(configuration)
                and result.get('upstream_technology_mapping_reused') is True
                and result.get('technology_mapping_executed') is False
                and result.get('checkpoint_manifest_sha256')==sha(folder/'resume-manifest.json'),
                'physical_resume_scope','Record checkpoint reuse explicitly; no fresh synthesis is implied.')
    recipe=result.get('adapter_recipe','v1')
    require(recipe in ('v1','v2'),'physical_recipe_unsupported','Unknown physical execution recipe.')
    commands=fixed_commands(configuration,folder,recipe)
    require(type(result.get('commands')) is list and len(result['commands'])==2,'physical_command_conflict','Both fixed version and layout executions are required.')
    for record,command in zip(result['commands'],commands):
        require(record.get('command')==command and record.get('executed') is True and type(record.get('exit_code')) is int and record['exit_code']==0 and record.get('status')=='Completed',
                'physical_command_conflict','Only the executed, successful fixed commands establish this proof.')
    for operation,record in zip(('version','layout'),result['commands']):
        logs=folder/operation
        request=load(logs/'request.json');exit_record=load(logs/'process-result.json')
        if recipe=='v2':
            worker=logs/'worker.py';worker_hash=sha(worker)
            supervisor=trusted_command(configuration,'/usr/bin/python3',[_wsl_path(worker),_wsl_path(logs/'request.json'),'--request-sha256',sha(logs/'request.json'),'--worker-sha256',worker_hash],folder)
            require(worker_hash==WORKER_V2_SHA and object_hash(request)==object_hash({'version':'hullcirq-physical-worker-v2','argv':record['command'][record['command'].index('--exec')+1:],'cwd':_wsl_path(folder),'timeout_seconds':120 if operation=='version' else 7200,'worker_sha256':worker_hash})
                    and record.get('request_unchanged_at_completion') is True and record.get('worker_unchanged_at_completion') is True
                    and record.get('cwd')==_wsl_path(folder) and record.get('observed_child_cwd') in (None,_wsl_path(folder)),
                    'physical_worker_conflict','The frozen v2 source/request and actual cwd must match.')
            require(record.get('process_start_sha256')==sha(logs/'process-start.json'),'physical_worker_conflict','Preserve the actual child process-start proof.')
            validate_worker_binding(request,record,load(logs/'process-start.json'),folder,worker_hash)
        else:
            worker_hash=WORKER_V1_SHA
            supervisor=trusted_command(configuration,'/usr/bin/python3',[_wsl_path(ROOT/'scripts/physical_worker.py'),_wsl_path(logs/'request.json')],folder)
        require(record.get('supervisor_command')==supervisor and record.get('worker_sha256')==worker_hash
                and record.get('request_sha256')==sha(logs/'request.json') and request['argv']==record['command'][record['command'].index('--exec')+1:]
                and all(object_hash(record[k])==object_hash(v) for k,v in exit_record.items())
                and record['stdout']==read_text((logs/'stdout.log'),encoding='utf-8',errors='replace')
                and record['stderr']==read_text((logs/'stderr.log'),encoding='utf-8',errors='replace'),
                'physical_worker_conflict','The actual Linux exit record, command and raw logs must match.')
    entries=result.get('artifacts',[])
    require(type(entries) is list and len({e['id'] for e in entries})==len(entries),'physical_artifact_invalid','Retain a unique fixed artifact manifest.')
    byid={e['id']:e for e in entries}
    required={'config','sdc','metrics','def','gds','png','netlist','final-state','tool-versions','input-manifest','rtl-top',*('rtl-'+n['node_id'] for n in manifest['nodes'])}
    if is_block_configuration(configuration):required |= BLOCK_ARTIFACTS
    require(set(byid)==required,'physical_artifact_missing','All source, settings and physical output files are required.')
    paths={}
    for identifier,entry in byid.items():
        path=(folder/entry['relative_path']).resolve()
        require(path.is_relative_to(folder) and file_exists(path) and file_stat(path).st_size==entry['bytes'] and sha(path)==entry['sha256'],
                'physical_artifact_changed','A retained physical artifact changed: '+identifier)
        paths[identifier]=path
    require(object_hash(load(paths['config']))==object_hash(expected_config) and sha(paths['sdc'])==SDC_SHA,'physical_configuration_conflict','Config and base SDC must preserve the fixed projection.')
    if _has_pnr_headroom(configuration):
        require(read_bytes((folder/'physical_pnr.sdc'))==pnr_sdc(read_bytes(paths['sdc'])),
                'physical_configuration_conflict','The PnR-only fanout headroom must preserve the unchanged original signoff SDC.')
    closure=_closure_recipe(configuration)
    if closure is not None:
        launcher, _, launcher_sha = closure
        require(sha(folder/launcher)==launcher_sha,
                'physical_configuration_conflict','Retain the fixed standard-flow corner override launcher.')
    require(sha(folder/'pdk-input-manifest.json')==configuration['pdk_manifest_sha256']
            and load(folder/'pdk-input-manifest.json')['ciel_revision']==PDK_REVISION,'physical_pdk_conflict','Preserve the exact installed PDK file manifest.')
    require(read_bytes(paths['rtl-top'])==rtl.encode('utf-8'),'physical_rtl_changed','Top RTL bytes changed.')
    for node in manifest['nodes']:require(read_bytes(paths['rtl-'+node['node_id']])==node['rtl'].encode('utf-8'),'physical_rtl_changed','Node RTL bytes changed.')
    inputs=load(paths['input-manifest'])
    require(object_hash(inputs)==object_hash({'settings':settings,'runtime_configuration':configuration,'source_bundle':source_bundle(rtl,manifest),'source_manifest_sha256':object_hash(manifest),'global_rtl_sha256':content_hash(rtl)}),'physical_input_changed','Recorded physical assumptions/source identity changed.')
    versions=load(paths['tool-versions'])
    if recipe=='v2':require(sha(folder/'capture_physical_versions.py')==VERSION_CAPTURE_SHA,'physical_version_conflict','Preserve the frozen executed version-capture source.')
    require(versions.get('librelane')==RELEASE and set(versions.get('tools',{}))=={'yosys','openroad','klayout','magic','ciel'},'physical_version_conflict','Actual bundled versions must be retained.')
    if is_block_configuration(configuration):
        block_recipe=recipe_for(configuration,required=True)
        require(result.get('placement_mode')=='block-regions-v1' and sha(paths['block-flow'])==block_recipe.flow_sha256 and sha(paths['block-runtime'])==block_recipe.runtime_sha256
                and OPENROAD_COMMIT in versions['tools']['openroad'].get('stdout',''), 'block_region_recipe_changed','Require the exact frozen block flow/runtime and pinned OpenROAD build.')
    state=load_tool_json(paths['final-state'])
    require('klayout-render' in paths['final-state'].parent.name.lower(),'physical_completion_missing','Require the actual KLayout.Render terminal step.')
    for identifier,key in (('def','def'),('gds','gds'),('png','render'),('netlist','nl')):
        require(_native(state.get(key),folder)==paths[identifier],'physical_output_conflict','Rendered/routed state and artifact paths disagree.')
        _check_artifact(paths[identifier],identifier,settings)
    metrics=load_tool_json(paths['metrics'])
    require(object_hash(result.get('metrics'))==object_hash(metrics) and object_hash(state.get('metrics'))==object_hash(metrics),'physical_metrics_conflict','Retain exact final-state metrics, not invented summary values.')
    checks=_configuration_metric_checks(metrics,configuration)
    if is_block_configuration(configuration):checks['block_regions']=_block_region_checks(configuration,manifest,settings,paths)
    require(object_hash(result.get('checks'))==object_hash(checks)
            and all(v['validation_status']=='Passed' for v in checks.values()) == (expected_status == 'Passed'),
            'physical_checks_failed','The complete actual metrics must reproduce the declared pass or failure without waivers.')
    retained=result.get('retained_files',[])
    require(type(retained) is list and len({r['relative_path'] for r in retained})==len(retained),'physical_retained_invalid','Retain unique raw step records.')
    for item in retained:
        path=(folder/item['relative_path']).resolve()
        require(path.is_relative_to(folder) and file_exists(path) and file_stat(path).st_size==item['bytes'] and sha(path)==item['sha256'],'physical_retained_changed','A raw physical log/config/state record changed.')
    require(result.get('executed') is True and type(result.get('exit_code')) is int and result['exit_code']==0
            and result.get('validation_status')==expected_status,
            'physical_status_conflict','A complete layout needs the actual successful tool exit and reproduced checks.')


def validate_layout_result(result,rtl,manifest,settings,configuration):
    _validate_complete_layout_result(result,rtl,manifest,settings,configuration,'Passed')


def validate_failed_layout_result(result,rtl,manifest,settings,configuration):
    """Reproduce a complete failure before fixed correction; never adopt it."""
    _validate_complete_layout_result(result,rtl,manifest,settings,configuration,'Failed')

def _retain_available(result,source_manifest,configuration):
    folder=Path(result['artifacts_directory']).resolve()
    available={e['id'] for e in result['artifacts']}
    candidates={'config':folder/'config.json','sdc':folder/'physical.sdc','input-manifest':folder/'input-manifest.json',
                'rtl-top':folder/'candidate_top.v','tool-versions':folder/'tool-versions.json'}
    candidates.update({'rtl-'+n['node_id']:folder/(n['node_id']+'.v') for n in source_manifest['nodes']})
    if result.get('placement_mode')=='block-regions-v1':
        block_recipe=recipe_for(configuration,required=True)
        candidates.update({'block-input':folder/'block-input.json','block-plan':folder/'block-plan.json','block-synthesis':folder/'block-synthesis.json',
                           'block-ownership':folder/'block-ownership.json','block-capacity':folder/'block-region-capacity.json','block-placement-proof':folder/'block-placement-proof.json',
                           'block-flow':folder/block_recipe.launcher,'block-runtime':folder/'block_layout_runtime.py'})
    terminal=sorted(artifact_glob((folder/'runs'/TAG),'*-klayout-render/state_out.json'))
    if len(terminal)==1:
        candidates['final-state']=terminal[0]
        try:
            state=load_tool_json(terminal[0])
            for identifier,key in (('def','def'),('gds','gds'),('png','render'),('netlist','nl')):
                try:candidates[identifier]=_native(state.get(key),folder)
                except DomainError:pass
        except (DomainError,OSError,ValueError,TypeError):pass
    candidates['metrics']=folder/'runs'/TAG/'final/metrics.json'
    for identifier,path in candidates.items():
        if identifier not in available and file_exists(path):
            result['artifacts'].append(_entry(identifier,path,folder,'image/png' if identifier=='png' else 'application/octet-stream' if identifier=='gds'
                else 'application/json' if identifier in ('config','input-manifest','tool-versions','final-state','metrics') or identifier.startswith('block-') and identifier not in ('block-flow','block-runtime') else 'text/plain; charset=utf-8'))
    bound={(folder/e['relative_path']).resolve() for e in result['artifacts']}
    result['retained_files']=[{'relative_path':p.relative_to(folder).as_posix(),'sha256':sha(p),'bytes':file_stat(p).st_size}
                              for p in sorted(artifact_files(folder)) if file_exists(p) and p.resolve() not in bound and (p.suffix in ('.log','.rpt','.json','.sdc','.py') or p.is_relative_to(folder/'resume-files'))]
    result['technology_mapping_executed']=any(artifact_glob((folder/'runs'/TAG),'*-yosys-synthesis/state_out.json'))

def _finish_layout_result(result,rtl,source_manifest,settings,configuration):
    """Rebuild checks from actual retained output; no commands or writes."""
    folder=Path(result['artifacts_directory']).resolve();run=folder/'runs'/TAG
    terminal=sorted(artifact_glob(run,'*-klayout-render/state_out.json'))
    require(len(terminal)==1,'physical_completion_missing','KLayout.Render did not produce one terminal state.')
    state=load_tool_json(terminal[0]);metrics_path=run/'final/metrics.json';metrics=load_tool_json(metrics_path)
    result['metrics']=metrics
    _retain_available(result,source_manifest,configuration)
    result['checks']=_configuration_metric_checks(metrics,configuration)
    if is_block_configuration(configuration):
        paths={entry['id']:folder/entry['relative_path'] for entry in result['artifacts']}
        result['checks']['block_regions']=_block_region_checks(configuration,source_manifest,settings,paths)
    if all(v['validation_status']=='Passed' for v in result['checks'].values()):
        result['validation_status']='Passed'
        validate_layout_result(result,rtl,source_manifest,settings,configuration)
    else:result['diagnostics'].append({'code':'physical_checks_failed','severity':'error','message':'Layout exists, but required routing/connectivity/mapping/timing metrics did not all pass.'})
    return result

def revalidate_layout(rtl,source_manifest,settings,configuration,previous_result,prior_run_id,cancel_event=None):
    """Append-only workflow recheck of saved actual tool exits and raw outputs.

    No model/EDA command runs and no original output bytes are rewritten. The
    manager binds the prior report hash and source identity in a separate run.
    """
    configuration_projection(settings,configuration,source_manifest)
    require(type(previous_result) is dict and type(prior_run_id) is str
            and previous_result.get('origin')=='trusted_fixed_tool_adapter'
            and previous_result.get('executed') is True and type(previous_result.get('exit_code')) is int and previous_result['exit_code']==0
            and previous_result.get('cleanup_unresolved') is not True
            and len(previous_result.get('commands',[]))==2
            and all(c.get('executed') is True and c.get('status')=='Completed' and type(c.get('exit_code')) is int and c['exit_code']==0 for c in previous_result['commands']),
            'physical_revalidation_unavailable','Recheck only saved successful tool executions with resolved cleanup.')
    result=copy.deepcopy(previous_result)
    result.update(validation_status='Failed',diagnostics=[],artifacts=[],retained_files=[],checks={},metrics={},
                  execution_reused=True,revalidated_from_run_id=prior_run_id,previous_result_sha256=object_hash(previous_result),
                  revalidation_tool_starts=0,revalidation_model_calls=0)
    result.setdefault('adapter_recipe','v1')
    try:
        require(cancel_event is None or not cancel_event.is_set(),'physical_revalidation_cancelled','Saved-output verification was cancelled.')
        _finish_layout_result(result,rtl,source_manifest,settings,configuration)
    except (DomainError,OSError,ValueError,KeyError,TypeError) as error:
        result['validation_status']='Failed';result['diagnostics'].append({'code':getattr(error,'code','physical_tool_error'),'severity':'error','message':str(error)})
    finally:_retain_available(result,source_manifest,configuration)
    return result

def _record_cancelled_command(result, execution, stage):
    """Classify a trusted cancelled command without changing its raw evidence."""
    if execution.get('status') != 'Cancelled':
        return False
    result.update(status='Cancelled', validation_status='Not Checked')
    label = {'physical': 'S11 layout', 'drc': 'S12 DRC', 'lvs': 'S13 LVS',
             'postroute': 'S14 post-layout verification'}[stage]
    if result.get('cleanup_unresolved') is True or execution.get('cleanup_unresolved') is True:
        result['cleanup_unresolved'] = True
        diagnostic = {'code': stage + '_cancel_cleanup_unresolved', 'severity': 'error',
            'message': label + ' was cancelled, but process cleanup is unresolved. Verify retained process/cleanup evidence before starting another execution.'}
    else:
        diagnostic = {'code': stage + '_cancelled', 'severity': 'info',
            'message': label + ' was cancelled. Required checks were not completed; retained commands, exit records and logs remain available. Cancellation alone does not establish a circuit defect.'}
    result['diagnostics'].append(diagnostic)
    return True


def run_layout(rtl,source_manifest,settings,configuration,cancel_event=None):
    config=configuration_projection(settings,configuration,source_manifest)
    if generic_repair.is_generic(configuration):
        generic_repair.validate_source(configuration,rtl,source_manifest,settings)
    parent=Path(configuration['working_directory']).resolve();parent.mkdir(parents=True,exist_ok=True)
    folder=Path(tempfile.mkdtemp(prefix='hullcirq-layout-',dir=parent))
    result={'validation_status':'Failed','executed':False,'exit_code':None,'diagnostics':[],'commands':[],'stdout':'','stderr':'',
            'global_rtl_sha256':content_hash(rtl),'source_manifest_sha256':object_hash(source_manifest),'settings_sha256':object_hash(settings),
            'runtime_configuration_sha256':object_hash(configuration),'source_bundle':source_bundle(rtl,source_manifest),
            'artifacts_directory':str(folder),'artifacts':[],'retained_files':[],'checks':{},'metrics':{},'origin':'trusted_fixed_tool_adapter','scope':SCOPE,'technology_mapping_executed':False,'adapter_recipe':'v2'}
    if is_block_configuration(configuration):result['placement_mode']='block-regions-v1'
    if generic_repair.is_generic(configuration):
        result.update(implementation_kind=generic_repair.IMPLEMENTATION_KIND,upstream_technology_mapping_reused=False)
    try:
        require(sha(configuration['appimage_path'])==IMAGE_SHA and sha(configuration['base_sdc_path'])==SDC_SHA,'physical_runtime_changed','Pinned runtime/base SDC bytes do not match.')
        pdk_manifest=Path(configuration['pdk_manifest_path'])
        require(sha(pdk_manifest)==configuration['pdk_manifest_sha256'],'physical_pdk_conflict','The installed PDK manifest changed.')
        pdk_data=load(pdk_manifest);pdk=Path(pdk_data['root']).absolute()
        require(pdk_data['ciel_revision']==PDK_REVISION and pdk.is_relative_to(Path(configuration['pdk_root']).absolute()),'physical_pdk_conflict','Use the release-pinned PDK below the configured cache.')
        for relative,metadata in pdk_data['files'].items():
            verify_pdk_file(pdk,relative,metadata,'physical_pdk_conflict')
        (folder/'pdk-input-manifest.json').write_bytes(read_bytes(pdk_manifest))
        (folder/'candidate_top.v').write_bytes(rtl.encode('utf-8'))
        for node in source_manifest['nodes']:(folder/(node['node_id']+'.v')).write_bytes(node['rtl'].encode('utf-8'))
        (folder/'physical.sdc').write_bytes(read_bytes(Path(configuration['base_sdc_path'])))
        if is_block_configuration(configuration):
            block_recipe=recipe_for(configuration,required=True)
            (folder/block_recipe.launcher).write_bytes(read_bytes((ROOT/'scripts'/block_recipe.launcher)))
            (folder/'block_layout_runtime.py').write_bytes(read_bytes((ROOT/'src/hullcirq'/block_recipe.runtime_file)))
            require(sha(folder/block_recipe.launcher)==block_recipe.flow_sha256 and sha(folder/'block_layout_runtime.py')==block_recipe.runtime_sha256,'block_region_recipe_changed','Preserve the pinned block-placement execution recipe.')
            for name,value in (('block-input.json',block_source_input(configuration,source_manifest,settings['top_module'])),('block-plan.json',configuration['block_plan'])):
                (folder/name).write_text(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
        if _has_pnr_headroom(configuration):(folder/'physical_pnr.sdc').write_bytes(pnr_sdc(read_bytes((folder/'physical.sdc'))))
        closure=_closure_recipe(configuration)
        if closure is not None:
            launcher, _, launcher_sha = closure
            (folder/launcher).write_bytes(read_bytes((ROOT/'scripts'/launcher)))
            require(sha(folder/launcher)==launcher_sha,'physical_configuration_conflict','Use the fixed standard-flow corner override launcher.')
        (folder/'capture_physical_versions.py').write_bytes(read_bytes((ROOT/'scripts/capture_physical_versions.py')))
        require(sha(folder/'capture_physical_versions.py')==VERSION_CAPTURE_SHA,'physical_version_conflict','Use the supported immutable version-capture script.')
        (folder/'config.json').write_text(json.dumps(config,indent=2)+'\n',encoding='utf-8')
        (folder/'input-manifest.json').write_text(json.dumps({'settings':settings,'runtime_configuration':configuration,'source_bundle':result['source_bundle'],'source_manifest_sha256':object_hash(source_manifest),'global_rtl_sha256':content_hash(rtl)},indent=2)+'\n',encoding='utf-8')
        if is_repair(configuration):
            snapshot_resume(configuration,folder,rtl,source_manifest,settings)
            result.update(implementation_kind=implementation_kind(configuration),upstream_technology_mapping_reused=True,
                          checkpoint_manifest_sha256=sha(folder/'resume-manifest.json'))
        commands=fixed_commands(configuration,folder)
        for index,command in enumerate(commands):
            execution=_execute(command,configuration,folder,'version' if index==0 else 'layout',cancel_event,120 if index==0 else 7200)
            result['commands'].append(execution);result['stdout']+=execution['stdout'];result['stderr']+=execution['stderr']
            result['executed']=any(c['executed'] for c in result['commands']);result['exit_code']=execution['exit_code']
            result['cleanup_unresolved']=execution.get('cleanup_unresolved') is True
            if execution['status']!='Completed' or execution['exit_code']!=0:
                if not _record_cancelled_command(result, execution, 'physical'):
                    result['diagnostics'].append({'code':'physical_tool_failed','severity':'error','message':'Inspect the retained '+('version' if index==0 else 'layout')+' tool output: '+execution['status']})
                return result
        _finish_layout_result(result,rtl,source_manifest,settings,configuration)
    except (DomainError,OSError,ValueError,KeyError,TypeError) as error:
        result['validation_status']='Failed';result['diagnostics'].append({'code':getattr(error,'code','physical_tool_error'),'severity':'error','message':str(error)})
    finally:
        # Failed/cancelled executions retain inputs and raw diagnostics too.
        # Never synthesize a missing final state or fabricate a Passed output.
        _retain_available(result,source_manifest,configuration)
    return result
