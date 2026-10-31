#!/usr/bin/env python3
"""One server command: real conditioner, RTL, faster ADC and full wrapper GDS.

Independent physical work proceeds even if the C-only ADC diagnostic is
incomplete. No old run, physical view, notebook or signoff gate is overwritten.
"""
from __future__ import annotations
import argparse
from contextlib import redirect_stdout, ExitStack
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import flow2_integration_common as common
from scripts import run_flow2_conditioner as conditioner
from scripts import run_flow2_adc_c_only as adc
from scripts import run_flow2_wrapper_rtl as rtl
from scripts import run_flow2_mixed_wrapper_gds as gds
from scripts import run_flow2_wrapper_pdk_lint as pdk_lint
from scripts import prepare_flow2_mixed_wrapper as prepare
from scripts import run_flow2_wrapper_integration as campaign
from scripts import run_flow2_readout_closure as closure
from scripts.run_flow2_acquisition_transient_recovery import DEFAULT_PDK


def source_items(root, value):
    """Carry referenced project inputs into the single download; exclude PDK."""
    if isinstance(value,dict):
        if isinstance(value.get('path'),str) and isinstance(value.get('sha256'),str):
            path=(root/value['path']).resolve()
            if path.is_relative_to(root):
                common._verified(root,value)
                yield value
        else:
            for v in value.values():yield from source_items(root,v)
    elif isinstance(value,list):
        for v in value:yield from source_items(root,v)


def _run(root, *, pdk_root=DEFAULT_PDK, tag="mixed_wrapper_20261020_01", execute=False,
         run_openlane=False, adc_timeout_s=1800, tool_timeout_s=1800,
         reuse_tag=None, skip_adc=False, physical_priority=False, resume_gds_tag=None,
         routing_options=None, core_repair_tag=None):
    root=Path(root).resolve();common.tag_ok(tag)
    if len(tag)>50 or min(adc_timeout_s,tool_timeout_s)<=0:raise ValueError("short tag and positive time budgets required")
    if resume_gds_tag:common.tag_ok(resume_gds_tag)
    children={"rtl":tag+"_rtl","conditioner":tag+"_cond","adc_c_only":tag+"_adc","gds":tag+"_gds",
              "pdk_lint":tag+"_lint"}
    prior=None;prior_path=None
    if reuse_tag:
        common.tag_ok(reuse_tag)
        if reuse_tag==tag:raise ValueError('recovery requires a new parent/GDS tag')
        prior_path=root/common.BASE/reuse_tag/'summary.json'
        prior=json.loads(prior_path.read_text(encoding='utf-8'))
        frozen=json.loads((prior_path.parent/'inputs.json').read_text(encoding='utf-8'))
        for key,path in [('topology',Path(prepare.d.__file__))]:
            if frozen.get(key)!=common._sha(path):raise ValueError('cannot reuse changed wrapper '+key)
        if prior.get('format')!='automx-cim-complete-wrapper-campaign-v1':raise ValueError('not a wrapper source campaign')
        for branch_name in ('rtl','conditioner','adc_c_only'):
            child=prior['child_tags'][branch_name];common.tag_ok(child);children[branch_name]=child
        # A digital repair invalidates the RTL transaction receipt, not the
        # immutable analog layout/PEX or standalone ADC inputs.
        if frozen.get('sequencer')!=common._sha(root/'rtl/automx_cim_readout_seq.sv'):
            children['rtl']=tag+'_rtl'
    report={"format":"automx-cim-complete-wrapper-campaign-v1","tag":tag,"status":"PREPARED",
        "child_tags":children,"branches":{},"planned_new_spice_jobs_maximum":8 if skip_adc else 10,
        "OpenLane_requested":run_openlane,"physical_priority":physical_priority,"resume_gds_tag":resume_gds_tag,"signoff_status":"NOT_SIGNOFF",
        "not_signoff":"all new native outcomes pending until measured; C-only ADC excludes wire R; calibration/PWM/reference/LIB/noise/PVT remain separate gates"}
    if prior_path:report['reused_campaign']={'path':prior_path.relative_to(root).as_posix(),'sha256':common._sha(prior_path)}
    report['ADC_requested']=not skip_adc
    report["connectivity"]=prepare.generate(root,root/common.BUILD/tag/"connectivity")
    if not execute:
        common._save(root/common.BUILD/tag/"plan.json",report)
        return report
    store=common.Store(root,tag,{"topology":common._sha(Path(prepare.d.__file__)),
        "sequencer":common._sha(root/"rtl/automx_cim_readout_seq.sv"),
        "runner":common._sha(Path(__file__)),"native_pdk":str(pdk_root),"run_openlane":run_openlane,
        'reuse_tag':reuse_tag,'skip_adc':skip_adc,'physical_priority':physical_priority,'resume_gds_tag':resume_gds_tag,
        'reused_campaign_sha256':common._sha(prior_path) if prior_path else None,
        'routing_settings':gds.routing_settings(routing_options), 'core_repair_tag':core_repair_tag})
    def branch(name, operation):
        store.note("BRANCH_START "+name)
        try:r=operation()
        except FileExistsError:raise
        except Exception as error:r={"status":"BLOCKED_BRANCH","error":f"{type(error).__name__}: {error}"}
        report["branches"][name]=r;store.note("BRANCH_END "+name+": "+r['status'])
        if r.get('electrical'):store.note(name+' electrical: '+r['electrical']['status'])
        common.save_summary(store.folder/"summary.json",report)
        return r
    try:
        with (store.folder/"history.log").open("a",encoding="utf-8") as history:
            with redirect_stdout(campaign._Tee(sys.stdout,history)):
                store.note("START mixed-signal wrapper; existing source _04/Stage5/leaves reused")
                branch("rtl",lambda:rtl.run(root,tag=children['rtl'],execute=True))
                branch("conditioner",lambda:conditioner.run(root,pdk_root=pdk_root,tag=children['conditioner'],execute=True,timeout_s=tool_timeout_s))
                # Complete the cheap digital/physical work before launching
                # an expensive ADC trajectory; either branch keeps its receipt.
                if skip_adc:
                    old=prior['branches'].get('adc_c_only',{}) if prior else {}
                    # Keep incomplete evidence explicit. No conversion or EOC
                    # is inferred by deferring this branch for layout recovery.
                    report['branches']['adc_c_only']={
                        'status':'DEFERRED_ADC_EVIDENCE','previous_status':old.get('status','NOT_RUN'),
                        'previous_completed_sims':old.get('completed_sims',0),'new_simulations':0,
                        'scope':'GDS recovery only; original ADC evidence remains pending'}
                    store.note('SKIP ADC: retain diagnostic; no new long conversion launched')
                if run_openlane:
                    source_gds=prior.get('child_tags',{}).get('gds') if prior else None
                    source_design=root/common.BUILD/source_gds/'design' if source_gds else None
                    probe=None
                    if not physical_priority and source_design and (source_design/'config.json').is_file():
                        probe=branch('pdk_lint',lambda:pdk_lint.run(root,source_design=source_design,
                            tag=children['pdk_lint'],execute=True,synthesis=True,timeout_s=tool_timeout_s))
                    else:
                        report['branches']['pdk_lint']={'status':'INCLUDED_IN_PRODUCTION_FLOW'}
                        store.note('Native full-top lint/Yosys will run once in production OpenLane')
                    if probe and probe['status']!='PASS_FULL_WRAPPER_PDK_SYNTHESIS':
                        report['branches']['gds']={'status':'BLOCKED_FULL_TOP_PDK_SYNTHESIS',
                            'error':'native PDK lint/synthesis preflight failed; inspect pdk_lint branch before routing'}
                    else:branch("gds",lambda:gds.run(root,pdk_root=pdk_root,tag=children['gds'],condition_tag=children['conditioner'],rtl_tag=children['rtl'],execute=True,resume_from=resume_gds_tag,routing_options=routing_options,core_repair_tag=core_repair_tag))
                else:report['branches']['gds']={"status":"NOT_REQUESTED"}
                if not skip_adc:
                    branch("adc_c_only",lambda:adc.run(root,tag=children['adc_c_only'],execute=True,timeout_s=adc_timeout_s))
        gr=report['branches'].get('gds',{})
        actual_gds=gr.get('views',{}).get('gds')
        report['status']=("MIXED_SIGNAL_PROTOTYPE_GDS_EXISTS" if actual_gds else "WRAPPER_IMPLEMENTATION_WITH_PENDING_GATES")
        if (gr.get('status')=='MIXED_WRAPPER_LAYOUT_AND_DIGITAL_STA_PASS' and
            gr.get('composite_transistor_checks',{}).get('status')=='BLOCK_DRC_TRANSISTOR_LVS_RC_PEX_PASS' and
            report['branches']['adc_c_only']['status']=='MEASURED_ADC_C_ONLY_TWO_CODE_PROTOTYPE'):
            report['status']='MIXED_SIGNAL_PROTOTYPE_PHYSICAL_PASS'
        report['remaining_gates']={
            "ADC_two_code_C_only":report['branches']['adc_c_only']['status'],
            "composite_transistor_LVS_PEX":gr.get('composite_transistor_checks',{}).get('status','PENDING'),
            "wrapper_LIB":gr.get('final_wrapper_LIB','PENDING_NATIVE_OPENSTA_MODEL'),
            "loaded_core_to_ADC_transfer_and_new_MHA":"PENDING_NEW_OPERATING_POINT_AND_CALIBRATION",
            "reference_startup_and_PWM_width":"PENDING_NATIVE_MEASUREMENTS",
            "noise_offset_full_PVT":"PENDING",
            "strict_Stage8_macro_bound":"PENDING_COMPLETE_WRAPPER_GATE_RECEIPT"}
    except FileExistsError:raise
    except KeyboardInterrupt:
        report['status']='INTERRUPTED';raise
    finally:
        if sys.exc_info()[0] is not FileExistsError:
            common.save_summary(store.folder/'summary.json',report)
            store.note('END '+report['status'])
            items=[]
            for child in [*children.values(),children['gds']+'_dev']:
                for base in (common.BASE,common.BUILD,common.PHYSICAL):items.extend(closure._files(root,base/child))
                for filename in ('summary.json','inputs.json'):
                    p=root/common.BASE/child/filename
                    if p.is_file():items.extend(source_items(root,json.loads(p.read_text(encoding='utf-8'))))
            target=common.bundle(root,tag,items)
            print('Download folder: '+str(target.parent),flush=True)
    return report


def run(root, **kwargs):
    if not kwargs.get('execute',False):return _run(root,**kwargs)
    if sys.platform!='linux':raise RuntimeError('native wrapper campaign runs on prepared Linux server only')
    tag=kwargs.get('tag','mixed_wrapper_20261020_01');common.tag_ok(tag)
    folder=Path(root).resolve()/common.BASE/tag;folder.mkdir(parents=True,exist_ok=True)
    folders=[folder]
    if kwargs.get('reuse_tag'):
        common.tag_ok(kwargs['reuse_tag'])
        if kwargs['reuse_tag']==tag:raise ValueError('recovery requires a new parent/GDS tag')
        folders.append(Path(root).resolve()/common.BASE/kwargs['reuse_tag'])
    import fcntl
    with ExitStack() as stack:
        for where in folders:
            lock=stack.enter_context((where/'runner.lock').open('a+'))
            try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError as error:raise RuntimeError('wrapper campaign or reused source is already running; follow '+str(where/'history.log')) from error
        return _run(root,**kwargs)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=ROOT)
    p.add_argument('--pdk-root',type=Path,default=DEFAULT_PDK);p.add_argument('--tag',default='mixed_wrapper_20261020_01')
    p.add_argument('--run',action='store_true');p.add_argument('--run-openlane',action='store_true')
    p.add_argument('--reuse-tag',help='reuse verified RTL/conditioner work, retaining a fresh parent/GDS tag')
    p.add_argument('--skip-adc',action='store_true',help='continue physical wrapper work without rerunning incomplete ADC conversion')
    p.add_argument('--adc-timeout-s',type=int,default=1800);p.add_argument('--tool-timeout-s',type=int,default=1800)
    a=p.parse_args();r=run(a.root,pdk_root=a.pdk_root,tag=a.tag,execute=a.run,run_openlane=a.run_openlane,
        adc_timeout_s=a.adc_timeout_s,tool_timeout_s=a.tool_timeout_s,
        reuse_tag=a.reuse_tag,skip_adc=a.skip_adc);print(json.dumps(r,indent=2))
    if a.run and r['status']!='MIXED_SIGNAL_PROTOTYPE_PHYSICAL_PASS':raise SystemExit(1)
