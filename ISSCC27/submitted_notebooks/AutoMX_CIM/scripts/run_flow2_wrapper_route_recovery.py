#!/usr/bin/env python3
"""Continue measured post-diode geometry via fresh prep, without repeating CTS.

No run directory is cloned or preseeded; only routing resources may change.
Every final physical/timing gate is measured again under the new native tag.
"""
from __future__ import annotations
import argparse
from contextlib import redirect_stdout
import json
from pathlib import Path
import shutil
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts import run_flow2_wrapper_physical_recovery as physical
from scripts import run_flow2_mixed_wrapper as wrapper
common=wrapper.common


def run(root,*,tag='mixed_wrapper_srv_20261021_03',source_tag='mixed_wrapper_srv_20261021_02_impl',execute=False,
        routing_options=None,min_free_gib=4,checkpoint_stage='post_diode'):
    root=Path(root).resolve();common.tag_ok(tag);common.tag_ok(source_tag)
    if len(tag)>43:raise ValueError('parent tag must have at most 43 characters')
    source=root/common.BASE/source_tag/'summary.json';previous=json.loads(source.read_text())
    child=tag+'_impl_gds';source_gds=previous['child_tags']['gds']
    repair_item=previous.get('branches',{}).get('gds',{}).get('core_full_drc_repair')
    core_repair_tag=None
    if repair_item:
        repair_path=common._verified(root,repair_item)
        core_repair_tag=repair_path.parent.name
    report={'format':'automx-cim-wrapper-physical-recovery-v1','tag':tag,'requested_tag':tag,
        'wrapper_tag':tag+'_impl','status':'PREPARED','execution_mode':'VERIFIED_ROUTE_CHECKPOINT',
        'source_campaign':source_tag,'source_gds':source_gds,'new_ADC_SPICE_jobs':0,
        'analog_signoff':'PENDING_MEASURED_EVIDENCE',
        'routing_settings':wrapper.gds.routing_settings(routing_options),'checkpoint_stage':checkpoint_stage}
    if not execute:return report
    if min_free_gib<0:raise ValueError('minimum free disk must be nonnegative')
    if shutil.disk_usage(root).free/1024**3<min_free_gib:
        raise RuntimeError('insufficient free disk for routing/export')
    if any((root/base/tag).exists() for base in (common.BASE,common.BUILD,common.PHYSICAL)):
        raise FileExistsError('use a fresh route recovery parent tag')
    store=common.Store(root,tag,{'source':common._item(root,source),'runner':common._sha(Path(__file__)),
        'gds_runner':common._sha(Path(wrapper.gds.__file__)),
        'checkpoint_helper':common._sha(root/'scripts/flow2_wrapper_route_checkpoint.py'),
        'routing_settings':report['routing_settings'],'checkpoint_stage':checkpoint_stage})
    import fcntl
    with (store.folder/'runner.lock').open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        try:
            with (store.folder/'history.log').open('a') as history, common.export_mode('deferred'):
                with redirect_stdout(wrapper.campaign._Tee(sys.stdout,history)):
                    store.note('START fresh prep then verified '+checkpoint_stage+' checkpoint import; source front-end reused')
                    gr=wrapper.gds.run(root,pdk_root=wrapper.DEFAULT_PDK,tag=child,
                        condition_tag=previous['child_tags']['conditioner'],rtl_tag=previous['child_tags']['rtl'],
                        execute=True,route_checkpoint_from=source_gds,routing_options=routing_options,
                        route_checkpoint_stage=checkpoint_stage,core_repair_tag=core_repair_tag)
            branch={**previous,'tag':tag+'_impl','child_tags':{**previous['child_tags'],'gds':child},
                    'branches':{**previous['branches'],'gds':gr}}
            report['wrapper']=branch
            report['native_executed']=gr.get('native_executed',False)
            common.save_summary(root/common.BASE/branch['tag']/'summary.json',branch)
            report['gates']={'wrapper_PDN':gr.get('pdn',{}).get('status','NOT_MEASURED'),
                'wrapper_layout':gr['status'],'digital_STA':gr.get('digital_sta_status','NOT_MEASURED'),
                'transistor_LVS_RC_PEX':gr.get('composite_transistor_checks',{}).get('status','NOT_MEASURED'),
                'ADC_readout':'NOT_QUALIFIED','Stage6_v2':'TT_ONLY_PROTOTYPE_NOT_QUALIFIED','strict_Stage8':'BLOCKED_QUALIFICATION'}
            report['status']='PHYSICAL_WRAPPER_PROTOTYPE_COMPLETE_ANALOG_PENDING' if physical.completed_physical(report) else 'PHYSICAL_WRAPPER_INCOMPLETE'
        except KeyboardInterrupt:
            report['status']='INTERRUPTED';raise
        except Exception as error:report.update(status='BLOCKED_ROUTE_CHECKPOINT',error=f'{type(error).__name__}: {error}')
        finally:
            common.save_summary(store.folder/'summary.json',report);store.note('END '+report['status'])
            items=list(wrapper.source_items(root,report))
            for t in [child,child+'_dev',tag+'_impl']:
                for base in (common.BASE,common.BUILD,common.PHYSICAL):items.extend(wrapper.closure._files(root,base/t))
            with common.export_mode('zip_only'):target=common.bundle(root,tag,items)
            print('Download: '+str(target.parent),flush=True)
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=ROOT)
    p.add_argument('--tag',default='mixed_wrapper_srv_20261021_03');p.add_argument('--source-tag',default='mixed_wrapper_srv_20261021_02_impl')
    p.add_argument('--global-min-layer',choices=['met1','met2'],default='met1')
    p.add_argument('--checkpoint-stage',choices=['post_diode','post_cts'],default='post_diode')
    p.add_argument('--detailed-min-layer',choices=['met1','met2'],default='met1')
    p.add_argument('--routing-cores',type=int,default=8)
    p.add_argument('--global-iters',type=int,default=30)
    p.add_argument('--detailed-iters',type=int,default=16)
    p.add_argument('--routing-reserve',type=float,default=.15)
    p.add_argument('--min-free-gib',type=float,default=4)
    p.add_argument('--allow-global-congestion',action='store_true',
        help='let detailed routing resolve global overflow; final DRC/LVS gates stay enabled')
    p.add_argument('--run',action='store_true');a=p.parse_args()
    options={'RT_MIN_LAYER':a.global_min_layer,'DRT_MIN_LAYER':a.detailed_min_layer,
             'ROUTING_CORES':a.routing_cores,'GRT_OVERFLOW_ITERS':a.global_iters,'DRT_OPT_ITERS':a.detailed_iters,
             'GRT_ADJUSTMENT':a.routing_reserve}
    if a.allow_global_congestion:options['GRT_ALLOW_CONGESTION']=1
    print(json.dumps(run(a.root,tag=a.tag,source_tag=a.source_tag,execute=a.run,
                         routing_options=options,min_free_gib=a.min_free_gib,checkpoint_stage=a.checkpoint_stage),indent=2))
