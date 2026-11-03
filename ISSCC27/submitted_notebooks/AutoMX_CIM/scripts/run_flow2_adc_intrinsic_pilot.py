#!/usr/bin/env python3
"""Bounded native ADC experiment retaining real MOS/MIM and modeled resistors.

Omit extracted wire R and parasitic C for a fast intrinsic-device prototype.
This is deliberately NOT RC PEX, ADC timing, loaded readout or qualification.
"""
from __future__ import annotations
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import run_flow2_adc_operating_point as operating
from scripts import flow2_adc_c_only as reduction
finish=operating.finish
common=finish.common


def intrinsic_network(text):
    contracted,proof=reduction.reduce_text(text)
    kept=[];removed=0;devices=Counter()
    for row in reduction.cards(contracted):
        f=row.split()
        if f and f[0][0].lower()=='c' and len(f)==4:
            removed+=1
            continue
        if f and f[0][0].lower() in ('x','m'):
            devices[' '.join(f)]+=1
        kept.append(row)
    original_devices=Counter(' '.join(row.split()) for row in reduction.cards(contracted)
        if row.split() and row.split()[0][0].lower() in ('x','m'))
    if devices!=original_devices or not removed:
        raise ValueError('intrinsic approximation must retain every contracted MOS/MIM and omit explicit parasitic C')
    proof.pop('node_aliases',None)
    proof.update(omitted_extracted_capacitors=removed,retained_physical_device_cards=sum(devices.values()),
        assumption='all extracted parasitic C omitted; MOS intrinsic capacitances and all physical MIM devices retained',
        qualification='NOT_QUALIFIED',analog_timing='NOT_PEX_TIMING')
    derived='* INTRINSIC DEVICE APPROXIMATION: extracted parasitic capacitors omitted.\n'+'\n'.join(kept)+'\n'
    proof['wire_contraction_intermediate_sha256']=proof['derived_sha256']
    proof['derived_sha256']=sha256(derived.encode()).hexdigest()
    return derived,proof


def run(root,*,tag='adc_intrinsic_20261021_01',timeout_s=300,execute=False):
    root=Path(root).resolve();common.tag_ok(tag)
    report={'format':'automx-cim-intrinsic-adc-pilot-v1','tag':tag,'status':'PREPARED',
        'qualification':'NOT_QUALIFIED','scope':'one ideal-driven ADC input; intrinsic MOS/MIM approximation, not RC PEX or coupled readout',
        'tolerances':{'reltol':1e-3,'abstol':1e-12,'vntol':1e-5},'wall_budget_s':timeout_s}
    if timeout_s<=0:raise ValueError('positive wall budget required')
    if not execute:return report
    previous,net,model,pins,_,_=finish.verify_source(root,'readout_progress_20261018_04',check_fanout=False)
    tool,version=finish.adc.runtime.select(root)
    if common._sha(Path(tool))!=previous['branches']['adc']['runtime']['binary_sha256']:
        raise ValueError('previously validated native simulator required')
    points,items=operating.operating_points(root,'mixed_wrapper_20261020_01_cond')
    point=points[-1]
    items += [common._item(root,p) for p in (net,model,Path(__file__),Path(reduction.__file__))]
    identity={'sources':items,'binary':common._sha(Path(tool)),'point':point,
        'profile':finish.profile.PROFILE,'tolerances':report['tolerances'],'approximation':'INTRINSIC_MOS_MIM_NO_EXTRACTED_C'}
    folder=root/common.BASE/tag
    if (folder/'inputs.json').exists():raise FileExistsError('retain prior intrinsic pilot; choose a fresh tag')
    store=common.Store(root,tag,identity)
    report.update(runtime=version,point=point,inputs=identity)
    try:
        store.note('START bounded intrinsic ADC approximation; original IP and qualified gates unchanged')
        text,proof=intrinsic_network(net.read_text())
        selected=store.build/'adc_intrinsic.spice';selected.write_text(text)
        report['reduction']=proof
        text,names=finish.profile.deck(model,selected,pins,{'input_switches':{}},task='conversion',cm=point['cm_v'],diff=point['diff_v'])
        text=text.replace('.option klu method=gear reltol=1e-4 abstol=1e-13',
                          '.option klu method=gear reltol=1e-3 abstol=1e-12 vntol=1e-5')
        circuit=store.build/'circuit.spice';circuit.write_text(text)
        result,vectors,proofs=finish.sessions.case(store.build/'sessions',executable=tool,circuit=circuit,
            points=finish.profile.points('conversion'),names=names,identity=identity,timeout_s=timeout_s,
            conversion=True,maximum_gap_s=1.1e-9,save_states=False,num_threads=1)
        report.update(native_session=result,raw_segments=proofs,source_circuit=common._item(root,circuit))
        report['status']='INCOMPLETE_INTRINSIC_ADC_PILOT'
        if result['status']=='NATIVE_TRAJECTORY_RETURNED':
            report['analysis']=finish.profile.analyze(vectors,{},task='conversion',cm=point['cm_v'],diff=point['diff_v'])
            report['status']='REAL_EOC_STABLE_WORD_INTRINSIC_APPROXIMATION_ONLY'
    except KeyboardInterrupt:
        report['status']='INTERRUPTED_INTRINSIC_ADC_PILOT';raise
    except Exception as error:report.update(status='BLOCKED_INTRINSIC_ADC_PILOT',error=f'{type(error).__name__}: {error}')
    finally:
        common.save_summary(store.folder/'summary.json',report)
        store.note('END '+report['status'])
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path,default=ROOT)
    parser.add_argument('--tag',default='adc_intrinsic_20261021_01');parser.add_argument('--timeout-s',type=int,default=300)
    parser.add_argument('--run',action='store_true');args=parser.parse_args()
    print(json.dumps(run(args.root,tag=args.tag,timeout_s=args.timeout_s,execute=args.run),indent=2))
