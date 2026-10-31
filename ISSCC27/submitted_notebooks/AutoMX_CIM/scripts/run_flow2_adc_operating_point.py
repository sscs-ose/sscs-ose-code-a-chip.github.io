#!/usr/bin/env python3
"""Real ADC conversions at remeasured conditioner PEX output levels.

The ADC input is still an ideal source: this tests compatibility of the
measured operating points, not coupled kickback/retention or analog signoff.
All devices and tolerances are retained. One native thread is an explicit
performance experiment, not a promised speedup. Old sessions are untouched.
"""
from __future__ import annotations
import argparse
from contextlib import redirect_stdout
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import run_flow2_adc_finish as finish
from scripts import run_flow2_conditioner as conditioner
from scripts import flow2_adc_c_only as reduction

common,profile,sessions=finish.common,finish.profile,finish.sessions
PASS='MEASURED_ADC_THREE_POINT_OPERATING_PILOT'


def operating_points(root,condition_tag):
    root=Path(root).resolve();common.tag_ok(condition_tag)
    source=root/common.BASE/condition_tag/'summary.json'
    saved=json.loads(source.read_text(encoding='utf-8'))
    electrical=saved.get('electrical',{})
    if (saved.get('status')!='BLOCK_DRC_TRANSISTOR_LVS_RC_PEX_PASS' or
        electrical.get('status')!='MEASURED_CONDITIONER_TT_PILOT'):
        raise ValueError('passed conditioner physical and eight-point electrical evidence required')
    jobs=electrical.get('jobs',[])
    identities={(j['variant'],j['selected_column']) for j in jobs}
    if len(jobs)!=8 or identities!={(v,c) for v in ('schematic','pex') for c in range(4)}:
        raise ValueError('eight unique conditioner points required')
    proof=[finish.core.acq._item(root,source)];points=[]
    for j in jobs:
        if j.get('status')!='MEASURED_CONDITIONER_POINT':raise ValueError('incomplete conditioner point')
        raw=common._verified(root,j['raw']);measured=conditioner.analyze_point(raw)
        for key in ('output_diff_v','output_cm_v'):
            if abs(measured[key]-j[key])>1e-10:raise ValueError('conditioner raw/summary differs: '+key)
        deck=root/common.BUILD/condition_tag/f"tt_{j['variant']}_{j['selected_column']}"/'bench.spice'
        if common._sha(deck)!=j['inputs']['deck']:raise ValueError('conditioner stimulus changed')
        proof += [j['raw'],finish.core.acq._item(root,deck)]
        if j['variant']=='pex' and j['selected_column'] in (0,1,3):
            points.append({'name':{0:'negative',1:'zero',3:'positive'}[j['selected_column']],
                'selected_column':j['selected_column'],'conditioner_input_diff_v':j['input_diff_v'],
                'diff_v':measured['output_diff_v'],'cm_v':measured['output_cm_v']})
    return sorted(points,key=lambda p:p['diff_v']),proof


def code_order(jobs):
    codes=[j['analysis']['result_code_12bit'] for j in jobs]
    if len(codes)!=3 or not (all(a<b for a,b in zip(codes,codes[1:])) or
                            all(a>b for a,b in zip(codes,codes[1:]))):
        raise ValueError('three fresh conversion codes must be distinct and monotonic')
    return {'codes':codes,'increasing_with_differential':codes[-1]>codes[0],
            'scope':'three operating points only; not DNL/INL or full transfer'}


def _run(root, *, source_tag='readout_progress_20261018_04',
        condition_tag='mixed_wrapper_20261020_01_cond',tag='adc_operating_20261020_04',
        execute=False,timeout_s=14400,num_threads=1,network='c_only'):
    root=Path(root).resolve();common.tag_ok(tag)
    if timeout_s<=0 or type(num_threads) is not int or not 1<=num_threads<=32 or network not in ('c_only','rc'):
        raise ValueError('positive time budget, native thread count 1..32 and c_only/rc required')
    points,items=operating_points(root,condition_tag)
    report={'format':'automx-cim-adc-operating-point-pilot-v1','tag':tag,'status':'PREPARED',
        'points':points,'network':network,'num_threads':num_threads,'planned_sims':3,'completed_sims':0,'jobs':[],
        'analog_signoff':'PENDING','not_signoff':'ideal driven ADC inputs at measured conditioner levels; ideal external VCM; '
        'no coupled core/conditioner/ADC trajectory, physical reference startup, full transfer, offset/noise or PVT qualification'}
    if not execute:return report
    previous,net,model,pins,_,source=finish.verify_source(root,source_tag,check_fanout=False)
    tool,version=finish.adc.runtime.select(root)
    if common._sha(Path(tool))!=previous['branches']['adc']['runtime']['binary_sha256']:
        raise ValueError('use the previously validated isolated native ngspice')
    items += [finish.core.acq._item(root,p) for p in (net,model,root/common.BASE/source_tag/'summary.json')]
    identity={'sources':items,'points':points,'network':network,'num_threads':num_threads,
        'binary':common._sha(Path(tool)),'profile':profile.PROFILE,
        'runner':common._sha(Path(__file__)),'sessions':common._sha(Path(sessions.__file__)),
        'waveform_analysis':common._sha(Path(profile.adc.__file__)),
        'reducer':common._sha(Path(reduction.__file__))}
    store=common.Store(root,tag,identity)
    report.update(ngspice_version=version,sources=items)
    try:
        with (store.folder/'history.log').open('a',encoding='utf-8') as history:
            with redirect_stdout(finish.closure._Tee(sys.stdout,history)):
                store.note('START three-point ADC operating pilot; no tolerance relaxation or forced EOC')
                selected=net
                if network=='c_only':
                    selected=store.build/'adc_top.c_only.spice'
                    proof=reduction.prepare(net,selected);proof.pop('node_aliases')
                    report['reduction']=proof
                report['command_probe']=sessions.script_probe(store.build/'command_probe',executable=tool)
                for point in points:
                    name=point['name'];folder=store.build/name;folder.mkdir(exist_ok=True)
                    text,names=profile.deck(model,selected,pins,{'input_switches':{}},task='conversion',
                                             cm=point['cm_v'],diff=point['diff_v'])
                    circuit=folder/'circuit.spice'
                    if circuit.exists() and circuit.read_text(encoding='utf-8')!=text:
                        raise FileExistsError('ADC operating stimulus changed; use a new tag')
                    if not circuit.exists():circuit.write_text(text,encoding='utf-8')
                    job={**point,'status':'STARTED'};report['jobs'].append(job)
                    store.note('CASE_START '+name+f" CM={point['cm_v']:.9g}V diff={point['diff_v']:.9g}V")
                    begun=time.monotonic()
                    result,vectors,proofs=sessions.case(folder/'sessions',executable=tool,circuit=circuit,
                        points=profile.points('conversion'),names=names,identity=identity,timeout_s=timeout_s,
                        conversion=True,maximum_gap_s=1.1e-9,save_states=False,num_threads=num_threads)
                    job.update(native_session=result,raw_segments=proofs,elapsed_wall_s=time.monotonic()-begun,
                               saved_transient_end_s=result.get('observed_at_s',0.))
                    if result['status']!='NATIVE_TRAJECTORY_RETURNED':
                        job['status']='INCOMPLETE_ADC_OPERATING_CONVERSION'
                    else:
                        try:
                            job['analysis']=profile.analyze(vectors,{},task='conversion',cm=point['cm_v'],diff=point['diff_v'])
                            job['status']='REAL_EOC_AND_STABLE_WORD';report['completed_sims']+=1
                        except ValueError as error:job.update(status='BLOCKED_ADC_ACCEPTANCE',error=str(error))
                    store.note('CASE_END '+name+': '+job['status'])
                    common.save_summary(store.folder/'summary.json',report)
                    if job['status']!='REAL_EOC_AND_STABLE_WORD':break
                if report['completed_sims']==3:
                    report['three_point_transfer']=code_order(report['jobs']);report['status']=PASS
                else:report['status']='PENDING_ADC_OPERATING_POINT_EVIDENCE'
    except FileExistsError:raise
    except KeyboardInterrupt:
        report['status']='INTERRUPTED_INCOMPLETE_CONVERSION_RESTARTS_FROM_ZERO';raise
    except Exception as error:report.update(status='BLOCKED_ADC_OPERATING_POINT',error=f'{type(error).__name__}: {error}')
    finally:
        if sys.exc_info()[0] is not FileExistsError:
            common.save_summary(store.folder/'summary.json',report);store.note('END '+report['status'])
            common.bundle(root,tag,items)
    return report


def run(root, **kwargs):
    if not kwargs.get('execute',False):return _run(root,**kwargs)
    if sys.platform!='linux':raise RuntimeError('native ADC runs on the prepared Linux server only')
    import fcntl
    tag=kwargs.get('tag','adc_operating_20261020_04');common.tag_ok(tag)
    folder=Path(root).resolve()/common.BASE/tag;folder.mkdir(parents=True,exist_ok=True)
    with (folder/'runner.lock').open('a+') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError as error:raise RuntimeError('ADC pilot already running; follow history.log') from error
        return _run(root,**kwargs)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=ROOT)
    p.add_argument('--source-tag',default='readout_progress_20261018_04')
    p.add_argument('--condition-tag',default='mixed_wrapper_20261020_01_cond')
    p.add_argument('--tag',default='adc_operating_20261020_04');p.add_argument('--run',action='store_true')
    p.add_argument('--timeout-s',type=int,default=14400);p.add_argument('--num-threads',type=int,default=1)
    p.add_argument('--network',choices=('c_only','rc'),default='c_only');a=p.parse_args()
    r=run(a.root,source_tag=a.source_tag,condition_tag=a.condition_tag,tag=a.tag,execute=a.run,
          timeout_s=a.timeout_s,num_threads=a.num_threads,network=a.network)
    print(json.dumps(r,indent=2))
    if a.run and r['status']!=PASS:raise SystemExit(1)
