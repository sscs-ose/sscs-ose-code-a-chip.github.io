"""Fresh matched published-POR recovery experiment.
SPDX-License-Identifier: Apache-2.0
"""
from pathlib import Path
import argparse,hashlib,json,math,subprocess,time,uuid
import numpy as np
import pilot
from por_consumer import save,verify_models,verify_external_sources,verify_sources
from por_circuit import measure,EVENTS
from guard_circuit import generate,generate_condition,CONDITIONS
HERE=Path(__file__).resolve().parent
SOURCES=['guard_consumer.py','guard_circuit.py','guard_spec.json','guard_policy.py','por_circuit.py','por_models.py','powered_reset.py','reset_contract.py','pilot.py','por_sources.json','external_sources.json','dependency_manifest.json']

def run_guard(*,variant='digital_guard',condition=None,event='digital_zero',command=True,max_step=None,solver=None,output=None):
    spec=json.loads((HERE/'guard_spec.json').read_text());step=spec['max_step_s'] if max_step is None else max_step;solver=solver or spec['solver']
    if variant not in ['original','digital_guard'] or solver not in ['sparse','klu'] or not isinstance(command,bool):raise ValueError('Declare variant, backend and Boolean operation')
    if isinstance(step,bool) or not math.isfinite(step) or step<=0:raise ValueError('Positive finite maximum step required')
    if condition is not None and (condition not in CONDITIONS or not command):raise ValueError('Named challenge conditions use ordinary Q=1 operation')
    tool=verify_models();external=verify_external_sources();por=verify_sources()
    if condition is None:text,args=generate(event,command,variant,step)
    else:text,args=generate_condition(condition,variant,step)
    out=Path(output) if output else HERE/'results/guard_runs'/('run_'+uuid.uuid4().hex[:10]);out.mkdir(parents=True,exist_ok=False)
    (out/'input.cir').write_text(text,encoding='utf-8');(out/'.spiceinit').write_text(f'set ngbehavior=hsa\noption {solver}\nset num_threads=1\n')
    record=dict(status='in_progress',evidence_kind='fresh execution',variant=variant,condition=condition,event=event if condition is None else None,command=command,max_step_s=step,solver=solver,
                tool=tool,external_sources=external,por_sources=por,spec=spec,output_dir=str(out),source_hashes={n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in SOURCES},
                written_deck_sha256=hashlib.sha256((out/'input.cir').read_bytes()).hexdigest(),source_functions=dict(analog=args[0],digital=args[1],data=args[2],clock=args[3]))
    save(out/'run.json',record);start=time.perf_counter()
    try:
        sub=subprocess.run([str(pilot.EXE),'-b','-o','ngspice.log','input.cir'],cwd=out,capture_output=True,text=True,timeout=spec['budget_s']);(out/'console.log').write_text(sub.stdout+sub.stderr)
        log=(out/'ngspice.log').read_text(errors='replace')
        if sub.returncode or 'Error' in log or 'Transient op started' in log or 'timestep too small' in log.lower():raise ValueError('Incomplete acquisition or operating-point fallback')
        d=np.loadtxt(out/'history.dat',skiprows=1)
        if d.shape[1]!=(19 if variant=='digital_guard' else 16) or not np.isfinite(d).all():raise ValueError('Missing/nonfinite raw vectors')
        result=measure(d[:,:16],*args,command);record.update(status='completed',result=result)
        storage=CONDITIONS[condition]['storage'] if condition is not None else event=='none'
        if storage:record['normal_storage_control_pass']=bool(result['minimum_q_final_hold_V']>=1.44 if command else result['maximum_q_final_hold_V']<=.36)
    except Exception as exc:
        record.update(status='unresolved',result=None,reason=type(exc).__name__+': '+str(exc))
        for attr in ['stdout','stderr']:
            value=getattr(exc,attr,None)
            if value:(out/('timeout_'+attr+'.log')).write_bytes(value if isinstance(value,bytes) else value.encode())
    record['elapsed_s']=time.perf_counter()-start;save(out/'run.json',record)
    print('Guard',variant,condition or event,record['status'],record['result']['observed_pass'] if record['result'] else None,flush=True);return record

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--variant',choices=['original','digital_guard'],default='digital_guard');p.add_argument('--condition',choices=list(CONDITIONS));p.add_argument('--event',choices=EVENTS,default='digital_zero');p.add_argument('--retain-state',action='store_true');p.add_argument('--max-step-us',type=float);p.add_argument('--solver',choices=['sparse','klu']);a=p.parse_args()
    r=run_guard(variant=a.variant,condition=a.condition,event=a.event,command=not a.retain_state,max_step=None if a.max_step_us is None else a.max_step_us*1e-6,solver=a.solver);return 0 if r['status']=='completed' else 2
if __name__=='__main__':raise SystemExit(main())
