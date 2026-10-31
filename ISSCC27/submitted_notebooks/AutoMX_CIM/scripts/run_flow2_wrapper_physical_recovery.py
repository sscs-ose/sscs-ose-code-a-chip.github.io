#!/usr/bin/env python3
"""Prioritize the physical mixed wrapper after the ADC VPWR PDN failure.

One native production flow, no new ADC SPICE jobs. Keep actual PDN/DRC/LVS
gates. Export one ZIP of build/results/physical instead of many nested copies.
"""
from __future__ import annotations

import argparse
from contextlib import redirect_stdout
import json
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import run_flow2_mixed_wrapper as wrapper
from scripts import flow2_wrapper_pdn as pdn
from scripts import flow2_wrapper_run_state as run_state
common=wrapper.common
TAG='mixed_wrapper_20261021_09'
SOURCE='mixed_wrapper_20261021_05_impl'
PHYSICAL_STATUSES={'MIXED_WRAPPER_LAYOUT_AND_DIGITAL_STA_PASS','MIXED_WRAPPER_LAYOUT_PASS_TIMING_PENDING'}


def input_identity(root, *, pdk_root, reuse_tag, resume_gds_tag, routing_options=None, core_repair_tag=None):
    common.tag_ok(reuse_tag)
    if resume_gds_tag:common.tag_ok(resume_gds_tag)
    source=root/common.BASE/reuse_tag/'summary.json'
    return {'source_campaign':{'path':source.relative_to(root).as_posix(),
        'sha256':common._sha(source)},'pdk':str(pdk_root),
        'runner':common._sha(Path(__file__)),'wrapper_runner':common._sha(Path(wrapper.__file__)),
        'gds_runner':common._sha(Path(wrapper.gds.__file__)),
        'sequencer':common._sha(root/'rtl/automx_cim_readout_seq.sv'),
        'rtl_testbench':common._sha(root/'tests/rtl/tb_flow2_readout_seq.sv'),
        'rtl_runner':common._sha(Path(wrapper.rtl.__file__)),
        'transistor_runner':common._sha(root/'scripts/run_flow2_wrapper_transistor_lvs.py'),
        'run_state':common._sha(Path(run_state.__file__)),
        'fanout_splitter':common._sha(root/wrapper.gds.fanout.SPLITTER),
        'fanout_legalize':common._sha(root/wrapper.gds.fanout.LEGALIZE),
        'generator':common._sha(Path(wrapper.prepare.__file__)),
        'topology':common._sha(Path(wrapper.prepare.d.__file__)),
        'container_runtime':common._sha(Path(wrapper.gds.container_runtime.__file__)),
        'pdn_checker':common._sha(Path(pdn.__file__)),
        'pdn_recipe':common._sha(root/pdn.RECIPE),'pdn_tcl':common._sha(root/pdn.PDN_TCL),
        'resume_gds_tag':resume_gds_tag,'routing_settings':wrapper.gds.routing_settings(routing_options),
        'core_repair':common._item(root,root/common.BASE/core_repair_tag/'summary.json') if core_repair_tag else None}


def select_tag(root, requested, identity, *, held_locks=()):
    """Reserve fresh parent/child output for conflicts and incomplete evidence."""
    common.tag_ok(requested)
    if len(requested)>43:raise ValueError('parent tag must have at most 43 characters')
    state=run_state.classify_parent_run(root,requested,identity,held_locks=held_locks)
    if state['state']==run_state.ACTIVE:
        raise RuntimeError('physical recovery already running; active lock: '+', '.join(state['active_locks']))
    if state['state'] in (run_state.EMPTY,run_state.COMPLETED):return requested
    for index in range(1,1000):
        candidate=requested[:38]+f'_r{index:03d}'
        cached=root/common.BASE/candidate/'inputs.json'
        candidate_state=run_state.classify_parent_run(root,candidate,identity)
        if cached.is_file() and candidate_state['state'] in (run_state.EMPTY,run_state.COMPLETED):return candidate
        if candidate_state['occupied_paths']:continue
        try:(root/common.BASE/candidate).mkdir(parents=True,exist_ok=False)
        except FileExistsError:continue
        return candidate
    raise FileExistsError('cannot reserve a fresh wrapper output tag')


def completed_physical(report):
    child=report.get('wrapper',{}).get('branches',{}).get('gds',{})
    return (child.get('status') in PHYSICAL_STATUSES and
            child.get('composite_transistor_checks',{}).get('status')=='BLOCK_DRC_TRANSISTOR_LVS_RC_PEX_PASS')


def audit(root, *, tag, identity=None, requested_tag=None, state=None):
    """Inspect saved evidence in memory; no Store, export, generation or EDA."""
    root=Path(root).resolve()
    state=state or run_state.classify_parent_run(root,tag,identity)
    if state['state']==run_state.ACTIVE:
        raise RuntimeError('physical recovery already running; active lock: '+', '.join(state['active_locks']))
    report=run_state.read_json(root/common.BASE/tag/'summary.json') or {}
    report.update(format='automx-cim-wrapper-physical-recovery-v1',tag=tag,
                  requested_tag=requested_tag or tag,execution_mode='AUDIT_ONLY',
                  run_state=state,native_executed=False,new_ADC_SPICE_jobs=0,
                  analog_signoff='PENDING_MEASURED_EVIDENCE',wrapper_tag=tag+'_impl')
    child=run_state.read_json(root/common.BASE/(tag+'_impl')/'summary.json') or {}
    gr=run_state.read_json(root/common.BASE/(tag+'_impl_gds')/'summary.json') or {}
    native=root/common.BUILD/(tag+'_impl_gds')/'design/runs'/(tag+'_impl_gds')
    gr.update(wrapper.gds.audit(native))
    gr['execution_mode']='AUDIT_ONLY'
    # Validate cached references without launching transistor checks or render.
    try:
        list(wrapper.source_items(root,gr))
    except (OSError,ValueError) as error:
        gr.pop('composite_transistor_checks',None)
        gr.update(status='BLOCKED_WRAPPER_IMPLEMENTATION',audit_error=str(error))
    child.setdefault('branches',{})['gds']=gr
    report['wrapper']=child
    report['gates']={'wrapper_PDN':gr.get('pdn',{}).get('status','NOT_MEASURED'),
        'wrapper_layout':gr.get('status','NOT_MEASURED'),
        'digital_STA':gr.get('digital_sta_status','NOT_MEASURED'),
        'transistor_LVS_RC_PEX':gr.get('composite_transistor_checks',{}).get('status','NOT_MEASURED'),
        'ADC_offset_noise_PVT':'DEFERRED_NOT_SIGNOFF','Stage6_v2':'NOT_QUALIFIED',
        'strict_Stage8':'BLOCKED_ANALOG_CHARACTERIZATION'}
    report['status']=('PHYSICAL_WRAPPER_PROTOTYPE_COMPLETE_ANALOG_PENDING'
        if state['state']==run_state.COMPLETED and completed_physical(report)
        else 'PHYSICAL_WRAPPER_INCOMPLETE')
    return report


def _run(root, *, pdk_root=wrapper.DEFAULT_PDK,tag=TAG,reuse_tag=SOURCE,execute=False,
        tool_timeout_s=1800,min_free_gib=4,resume_gds_tag=None,requested_tag=None,routing_options=None,core_repair_tag=None):
    root=Path(root).resolve();common.tag_ok(tag);common.tag_ok(reuse_tag)
    if resume_gds_tag:common.tag_ok(resume_gds_tag)
    if len(tag)>43 or tag==reuse_tag or tool_timeout_s<=0 or min_free_gib<0:
        raise ValueError('new short tag and positive timeout required')
    report={'format':'automx-cim-wrapper-physical-recovery-v1','tag':tag,'status':'PREPARED',
        'requested_tag':requested_tag or tag,'execution_mode':'EXECUTE' if execute else 'PLAN',
        'native_executed':False,
        'wrapper_tag':tag+'_impl','reuse_tag':reuse_tag,'pdn_policy':pdn.POLICY,
        'resume_gds_tag':resume_gds_tag,
        'routing_settings':wrapper.gds.routing_settings(routing_options),
        'native_mode':'FRESH_NATIVE_FLOW_REUSING_VERIFIED_HARD_MACROS',
        'new_ADC_SPICE_jobs':0,'plan':['reuse measured conditioner and core/acquisition',
        'pinned container Python/DEF checker and OpenROAD/ODB runtime preflight',
        'full-top native lint and synthesis once','floorplan and VPWR/VGND connectivity',
        'placement/CTS/fanout/route','Magic/KLayout DRC and LEF-macro LVS',
        'independent transistor LVS and RC PEX','publish GDS/LEF/LIB/SPEF and render'],
        'analog_signoff':'PENDING_MEASURED_EVIDENCE'}
    if requested_tag and requested_tag!=tag:report['requested_tag']=requested_tag
    if resume_gds_tag:report['resume_status']='NOT_SUPPORTED_BY_PINNED_PREP; full native flow used'
    if not execute:return report
    if sys.platform!='linux':raise RuntimeError('physical recovery runs on the prepared Linux server only')
    free=shutil.disk_usage(root).free/1024**3
    if free<min_free_gib:
        raise RuntimeError(f'free disk {free:.2f} GiB; need at least {min_free_gib:g} GiB for wrapper routing/PEX/export')
    store=common.Store(root,tag,input_identity(root,pdk_root=pdk_root,reuse_tag=reuse_tag,resume_gds_tag=resume_gds_tag,
        routing_options=routing_options,core_repair_tag=core_repair_tag))
    report['disk_free_gib_at_start']=round(free,3)
    try:
        store.note('START physical wrapper recovery; 0 new ADC jobs; one final ZIP export')
        if requested_tag and requested_tag!=tag:store.note('NEW_OUTPUT_TAG '+requested_tag+' -> '+tag+'; prior snapshot retained')
        with (store.folder/'history.log').open('a',encoding='utf-8') as history:
            with redirect_stdout(wrapper.campaign._Tee(sys.stdout,history)), common.export_mode('deferred'):
                physical=wrapper.run(root,pdk_root=pdk_root,tag=report['wrapper_tag'],reuse_tag=reuse_tag,
                    execute=True,run_openlane=True,skip_adc=True,physical_priority=True,tool_timeout_s=tool_timeout_s,
                    resume_gds_tag=resume_gds_tag,routing_options=routing_options,core_repair_tag=core_repair_tag)
        report['wrapper']=physical
        gds=physical.get('branches',{}).get('gds',{})
        report['native_executed']=gds.get('openlane_returncode') is not None
        report['gates']={'wrapper_PDN':gds.get('pdn',{}).get('status','NOT_MEASURED'),
            'wrapper_layout':gds.get('status','NOT_MEASURED'),
            'digital_STA':gds.get('digital_sta_status','NOT_MEASURED'),
            'transistor_LVS_RC_PEX':gds.get('composite_transistor_checks',{}).get('status','NOT_MEASURED'),
            'ADC_offset_noise_PVT':'DEFERRED_NOT_SIGNOFF','Stage6_v2':'NOT_QUALIFIED',
            'strict_Stage8':'BLOCKED_ANALOG_CHARACTERIZATION'}
        report['status']=('PHYSICAL_WRAPPER_PROTOTYPE_COMPLETE_ANALOG_PENDING' if completed_physical(report)
                          else 'PHYSICAL_WRAPPER_INCOMPLETE')
    except FileExistsError:
        raise
    except KeyboardInterrupt:
        report['status']='INTERRUPTED';raise
    except Exception as error:
        report.update(status='BLOCKED_PHYSICAL_WRAPPER_RECOVERY',error=f'{type(error).__name__}: {error}')
    finally:
        if sys.exc_info()[0] is not FileExistsError:
            # Recover child evidence even if an exception prevented a return.
            child_path=root/common.BASE/report['wrapper_tag']/'summary.json'
            child=report.get('wrapper',{})
            if not child and child_path.is_file():
                child=json.loads(child_path.read_text(encoding='utf-8'));report['wrapper']=child
            common.save_summary(store.folder/'summary.json',report)
            store.note('END '+report['status'])
            items=list(wrapper.source_items(root,child))
            children=[report['wrapper_tag'],*child.get('child_tags',{}).values()]
            if child.get('child_tags',{}).get('gds'):children.append(child['child_tags']['gds']+'_dev')
            for name in filter(None,children):
                common.tag_ok(name)
                for base in (common.BASE,common.BUILD,common.PHYSICAL):
                    items.extend(wrapper.closure._files(root,base/name))
            with common.export_mode('zip_only'):
                target=common.bundle(root,tag,items)
            print('Download this folder: '+str(target.parent),flush=True)
    return report


def run(root, *, audit_only=False, **kwargs):
    if audit_only and kwargs.get('execute',False):raise ValueError('--run and --audit-only are mutually exclusive')
    if audit_only:
        return audit(root,tag=kwargs.get('tag',TAG),requested_tag=kwargs.get('requested_tag'))
    if not kwargs.get('execute',False):return _run(root,**kwargs)
    if sys.platform!='linux':raise RuntimeError('physical recovery runs on the prepared Linux server only')
    import fcntl
    tag=kwargs.get('tag',TAG);common.tag_ok(tag)
    root=Path(root).resolve()
    if len(tag)>43:raise ValueError('parent tag must have at most 43 characters')
    identity=input_identity(root,pdk_root=kwargs.get('pdk_root',wrapper.DEFAULT_PDK),
        reuse_tag=kwargs.get('reuse_tag',SOURCE),resume_gds_tag=kwargs.get('resume_gds_tag'),
        routing_options=kwargs.get('routing_options'),core_repair_tag=kwargs.get('core_repair_tag'))
    initial=run_state.classify_parent_run(root,tag,identity)
    if initial['state']==run_state.ACTIVE:
        raise RuntimeError('physical recovery already running; active lock: '+', '.join(initial['active_locks']))
    if initial['state']==run_state.COMPLETED:
        print('AUDIT_ONLY completed wrapper run; no new native execution: '+tag,flush=True)
        return audit(root,tag=tag,identity=identity,state=initial)
    folder=root/common.BASE/tag;folder.mkdir(parents=True,exist_ok=True)
    with (folder/'runner.lock').open('a+') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError('physical recovery already running; follow '+str(folder/'history.log')) from error
        selected=select_tag(root,tag,identity,held_locks=[folder/'runner.lock'])
        if selected==tag:return _run(root,**kwargs)
        print('Existing output '+initial['state']+'; keeping '+tag+' and using '+selected,flush=True)
        print('History: '+str(root/common.BASE/selected/'history.log'),flush=True)
        with (root/common.BASE/selected/'runner.lock').open('a+') as selected_lock:
            try:fcntl.flock(selected_lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError as error:raise RuntimeError('selected wrapper output is already running: '+selected) from error
            selected_state=run_state.classify_parent_run(root,selected,identity,
                held_locks=[root/common.BASE/selected/'runner.lock'])
            if selected_state['state']==run_state.COMPLETED:
                print('AUDIT_ONLY completed wrapper run; no new native execution: '+selected,flush=True)
                return audit(root,tag=selected,identity=identity,requested_tag=tag,state=selected_state)
            if selected_state['state']!=run_state.EMPTY:
                raise RuntimeError('selected wrapper namespace became occupied; retain evidence and retry with a fresh --tag: '+selected)
            return _run(root,**{**kwargs,'tag':selected,'requested_tag':tag})


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=ROOT)
    p.add_argument('--pdk-root',type=Path,default=wrapper.DEFAULT_PDK);p.add_argument('--tag',default=TAG)
    p.add_argument('--reuse-tag',default=SOURCE)
    mode=p.add_mutually_exclusive_group();mode.add_argument('--run',action='store_true')
    mode.add_argument('--audit-only',action='store_true',help='read existing native evidence without tools, output writes or export')
    p.add_argument('--resume-gds-tag',help='legacy option retained in report; pinned prep requires a fresh native run')
    p.add_argument('--tool-timeout-s',type=int,default=1800);p.add_argument('--min-free-gib',type=float,default=4)
    p.add_argument('--core-repair-tag',help='verified full-DRC core tap/access receipt')
    p.add_argument('--detailed-iters',type=int,default=16);p.add_argument('--routing-cores',type=int,default=8)
    a=p.parse_args();r=run(a.root,pdk_root=a.pdk_root,tag=a.tag,reuse_tag=a.reuse_tag,execute=a.run,audit_only=a.audit_only,
        tool_timeout_s=a.tool_timeout_s,min_free_gib=a.min_free_gib,resume_gds_tag=a.resume_gds_tag,
        routing_options={'DRT_OPT_ITERS':a.detailed_iters,'ROUTING_CORES':a.routing_cores},core_repair_tag=a.core_repair_tag)
    print(json.dumps(r,indent=2))
    if a.run and not completed_physical(r):raise SystemExit(1)
