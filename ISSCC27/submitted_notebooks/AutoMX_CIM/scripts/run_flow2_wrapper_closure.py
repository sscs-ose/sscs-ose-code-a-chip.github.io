#!/usr/bin/env python3
"""One server command: repair/harden wrapper, test ADC at measured CM, export.

Layout completion, transistor connectivity, ADC functional evidence and analog
signoff remain separate. A three-code pilot can never produce signoff PASS.
"""
from __future__ import annotations
import argparse
from contextlib import redirect_stdout
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import run_flow2_mixed_wrapper as wrapper
from scripts import run_flow2_adc_operating_point as adc
common=wrapper.common


def gates(physical,conversion):
    gds=physical.get('branches',{}).get('gds',{})
    result={
        'wrapper_layout_and_digital_STA':gds.get('status','NOT_MEASURED'),
        'wrapper_transistor_LVS_RC_PEX':gds.get('composite_transistor_checks',{}).get('status','NOT_MEASURED'),
        'wrapper_native_boundary_LIB':gds.get('final_wrapper_LIB','NOT_MEASURED'),
        'ADC_at_measured_conditioner_levels':conversion.get('status','NOT_MEASURED'),
        'ADC_wire_model':conversion.get('network','NOT_MEASURED'),
        'coupled_core_conditioner_ADC_kickback_retention':'NOT_MEASURED',
        'physical_VCM_startup_and_PWM_width':'NOT_MEASURED',
        'full_ADC_transfer_offset_noise_PVT':'NOT_MEASURED',
        'new_MHA_and_Stage6_v2':'NOT_QUALIFIED',
        'analog_signoff':'PENDING_MEASURED_EVIDENCE',
        'strict_Stage8':'BLOCKED_ANALOG_CHARACTERIZATION'}
    return result


def run(root, *, pdk_root=wrapper.DEFAULT_PDK,tag='mixed_wrapper_20261020_04',
        reuse_tag='mixed_wrapper_20261020_03',execute=False,adc_timeout_s=14400,
        tool_timeout_s=1800,num_threads=1,network='c_only',skip_adc=False):
    root=Path(root).resolve();common.tag_ok(tag);common.tag_ok(reuse_tag)
    if len(tag)>42 or tag==reuse_tag or min(adc_timeout_s,tool_timeout_s)<=0:
        raise ValueError('new short tag and positive native timeouts required')
    report={'format':'automx-cim-wrapper-closure-campaign-v1','tag':tag,'status':'PREPARED',
        'wrapper_tag':tag+'_impl','adc_tag':tag+'_adc_op','branches':{},
        'analog_signoff':'PENDING_MEASURED_EVIDENCE','planned_new_ADC_conversions_maximum':0 if skip_adc else 3}
    if not execute:return report
    if sys.platform!='linux':raise RuntimeError('native closure campaign runs on the prepared Linux server only')
    import fcntl
    lockdir=root/common.BASE/tag;lockdir.mkdir(parents=True,exist_ok=True)
    with (lockdir/'runner.lock').open('a+') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError as error:raise RuntimeError('closure campaign already running; follow history.log') from error
        identity={'source_tag':reuse_tag,'source_summary':common._sha(root/common.BASE/reuse_tag/'summary.json'),
            'runner':common._sha(Path(__file__)),'wrapper_runner':common._sha(Path(wrapper.__file__)),
            'adc_runner':common._sha(Path(adc.__file__)),'pdk':str(pdk_root),
            'adc_timeout_s':adc_timeout_s,'num_threads':num_threads,'network':network,'skip_adc':skip_adc}
        store=common.Store(root,tag,identity)
        try:
            with (store.folder/'history.log').open('a',encoding='utf-8') as history:
                with redirect_stdout(wrapper.campaign._Tee(sys.stdout,history)):
                    print('START wrapper synthesis/layout first, then native ADC operating pilot',flush=True)
                    physical=wrapper.run(root,pdk_root=pdk_root,tag=report['wrapper_tag'],reuse_tag=reuse_tag,
                        execute=True,run_openlane=True,skip_adc=True,tool_timeout_s=tool_timeout_s)
                    report['branches']['wrapper']=physical
                    common.save_summary(store.folder/'summary.json',report)
                    if skip_adc:conversion={'status':'NOT_REQUESTED','network':network}
                    else:
                        conversion=adc.run(root,condition_tag=physical['child_tags']['conditioner'],
                            tag=report['adc_tag'],execute=True,timeout_s=adc_timeout_s,
                            num_threads=num_threads,network=network)
                    report['branches']['adc']=conversion
                    report['gates']=gates(physical,conversion)
                    report['status']='PROTOTYPE_CLOSURE_RECORDED_ANALOG_GATES_PENDING'
                    print('END '+report['status'],flush=True)
        except FileExistsError:raise
        except KeyboardInterrupt:
            report['status']='INTERRUPTED';raise
        except Exception as error:report.update(status='BLOCKED_WRAPPER_CLOSURE',error=f'{type(error).__name__}: {error}')
        finally:
            if sys.exc_info()[0] is not FileExistsError:
                common.save_summary(store.folder/'summary.json',report)
                items=[]
                for value in report['branches'].values():
                    items.extend(wrapper.source_items(root,value))
                    tags=[value.get('tag')]+list(value.get('child_tags',{}).values())
                    if value.get('child_tags',{}).get('gds'):tags.append(value['child_tags']['gds']+'_dev')
                    for child in filter(None,tags):
                        for base in (common.BASE,common.BUILD,common.PHYSICAL):
                            items.extend(wrapper.closure._files(root,base/child))
                target=common.bundle(root,tag,items)
                print('Download folder: '+str(target.parent),flush=True)
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=ROOT)
    p.add_argument('--pdk-root',type=Path,default=wrapper.DEFAULT_PDK)
    p.add_argument('--tag',default='mixed_wrapper_20261020_04');p.add_argument('--reuse-tag',default='mixed_wrapper_20261020_03')
    p.add_argument('--run',action='store_true');p.add_argument('--skip-adc',action='store_true')
    p.add_argument('--adc-timeout-s',type=int,default=14400);p.add_argument('--tool-timeout-s',type=int,default=1800)
    p.add_argument('--num-threads',type=int,default=1);p.add_argument('--network',choices=('c_only','rc'),default='c_only')
    a=p.parse_args();r=run(a.root,pdk_root=a.pdk_root,tag=a.tag,reuse_tag=a.reuse_tag,execute=a.run,
        skip_adc=a.skip_adc,adc_timeout_s=a.adc_timeout_s,tool_timeout_s=a.tool_timeout_s,
        num_threads=a.num_threads,network=a.network)
    print(json.dumps(r,indent=2))
    if a.run and (r.get('branches',{}).get('wrapper',{}).get('branches',{}).get('gds',{}).get('status')!=
        'MIXED_WRAPPER_LAYOUT_AND_DIGITAL_STA_PASS' or
        (not a.skip_adc and r.get('branches',{}).get('adc',{}).get('status')!=adc.PASS)):raise SystemExit(1)
