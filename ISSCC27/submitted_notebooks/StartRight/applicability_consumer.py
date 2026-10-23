"""Fresh acquisition of declared application histories or isolated DC sweeps.
SPDX-License-Identifier: Apache-2.0
"""
from pathlib import Path
import argparse,hashlib,json,subprocess,time,uuid
import numpy as np
import pilot
from guard_consumer import HERE,save,verify_models,verify_external_sources,verify_sources
from application_circuit import generate_application,measure_application,HISTORIES
from guard_window import generate_window,measure_window,CORNERS,TEMPERATURES,RESISTANCES_MOHM
SOURCES=['applicability_consumer.py','application_circuit.py','guard_window.py','applicability_spec.json',
         'guard_circuit.py','por_circuit.py','por_models.py','reset_contract.py','pilot.py',
         'dependency_manifest.json','por_sources.json','external_sources.json']

def acquire(*,kind='application',history='triangle',variant='digital_guard',max_step=2e-6,
            corner='tt',temp_C=27,direction='up',resistance_Mohm=40,output=None):
    if kind not in ('application','window'):raise ValueError('Declare application or window acquisition')
    spec=json.loads((HERE/'applicability_spec.json').read_text())
    tool=verify_models()
    if kind=='application':
        external,por=verify_external_sources(),verify_sources()
        text,args=generate_application(history,variant,max_step)
        settings=dict(history=history,variant=variant,max_step_s=max_step);raw='history.dat';budget=spec['application_budget_s']
    else:
        external=por=None;text=generate_window(corner,temp_C,direction,resistance_Mohm)
        settings=dict(corner=corner,temp_C=temp_C,direction=direction,resistance_Mohm=resistance_Mohm);raw='transfer.dat';budget=spec['window_budget_s']
    out=Path(output) if output else HERE/'results/applicability_runs'/('run_'+uuid.uuid4().hex[:10])
    out.mkdir(parents=True,exist_ok=False)
    (out/'input.cir').write_text(text,encoding='utf-8');(out/'.spiceinit').write_text('set ngbehavior=hsa\noption sparse\nset num_threads=1\n')
    record=dict(status='in_progress',evidence_kind='fresh execution',kind=kind,settings=settings,tool=tool,
        external_sources=external,por_sources=por,output_dir=str(out),spec=spec,
        source_hashes={n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in SOURCES},
        written_deck_sha256=hashlib.sha256((out/'input.cir').read_bytes()).hexdigest())
    if kind=='application':record['source_functions']=dict(analog=args[0],digital=args[1],data=args[2],clock=args[3])
    save(out/'run.json',record);start=time.monotonic()
    try:
        sub=subprocess.run([str(pilot.EXE),'-b','-o','ngspice.log','input.cir'],cwd=out,capture_output=True,text=True,timeout=budget)
        (out/'console.log').write_text(sub.stdout+sub.stderr);log=(out/'ngspice.log').read_text(errors='replace')
        if sub.returncode or 'Error' in log or 'Transient op started' in log or 'timestep too small' in log.lower():raise ValueError('Incomplete acquisition or operating-point fallback')
        d=np.loadtxt(out/raw,skiprows=1)
        if not np.isfinite(d).all():raise ValueError('Nonfinite vectors')
        if kind=='application':
            if d.shape[1]!=(19 if variant=='digital_guard' else 16):raise ValueError('Missing application vectors')
            result=measure_application(d,args,history)
        else:result=measure_window(d)
        record.update(status='completed',result=result,raw_sha256=hashlib.sha256((out/raw).read_bytes()).hexdigest())
    except Exception as exc:
        record.update(status='unresolved',result=None,reason=type(exc).__name__+': '+str(exc))
        for attr in ('stdout','stderr'):
            value=getattr(exc,attr,None)
            if value:(out/('timeout_'+attr+'.log')).write_bytes(value if isinstance(value,bytes) else value.encode())
    record['elapsed_s']=time.monotonic()-start;save(out/'run.json',record)
    print('Applicability',kind,settings,record['status'],record['result'].get('diagnosis') if record['result'] else None,flush=True)
    return record

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--kind',choices=['application','window'],default='application')
    p.add_argument('--history',choices=HISTORIES,default='triangle');p.add_argument('--variant',choices=['original','digital_guard'],default='digital_guard')
    p.add_argument('--max-step-us',type=float,default=2);p.add_argument('--corner',choices=CORNERS,default='tt');p.add_argument('--temp-C',type=int,choices=TEMPERATURES,default=27)
    p.add_argument('--direction',choices=['up','down'],default='up');p.add_argument('--resistance-Mohm',type=int,choices=RESISTANCES_MOHM,default=40)
    a=p.parse_args();r=acquire(kind=a.kind,history=a.history,variant=a.variant,max_step=a.max_step_us*1e-6,corner=a.corner,temp_C=a.temp_C,direction=a.direction,resistance_Mohm=a.resistance_Mohm)
    return 0 if r['status']=='completed' else 2
if __name__=='__main__':raise SystemExit(main())
