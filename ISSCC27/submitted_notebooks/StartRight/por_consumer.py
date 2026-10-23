"""Fresh declared supply-history experiment on published reset IP.
SPDX-License-Identifier: Apache-2.0
"""
from pathlib import Path
import argparse,hashlib,json,math,subprocess,time,uuid
import numpy as np
import pilot
from schematic_support import verify_models
from external_consumer import verify_external_sources
from por_models import verify_sources
from por_circuit import generate,measure,EVENTS
HERE=Path(__file__).resolve().parent
SOURCES=['por_consumer.py','por_models.py','por_circuit.py','powered_reset.py','por_spec.json','por_sources.json','reset_contract.py','pilot.py','passive_models.py','dependency_manifest.json']


def save(path,value):
    Path(path).write_text(json.dumps(value,indent=2,allow_nan=False),encoding='utf8')


def run_por(*,event='digital_zero',command=True,solver=None,max_step=None,output=None):
    spec=json.loads((HERE/'por_spec.json').read_text());solver=solver or spec['solver'];step=spec['max_step_s'] if max_step is None else max_step
    if event not in EVENTS or not isinstance(command,bool) or solver not in ['sparse','klu']:raise ValueError('Declare a supported event, prior-state operation and backend')
    if isinstance(step,bool) or not math.isfinite(step) or step<=0:raise ValueError('Positive finite maximum step required')
    tool=verify_models();external=verify_external_sources();por=verify_sources()
    out=Path(output) if output else HERE/'results/por_runs'/('run_'+uuid.uuid4().hex[:10]);out.mkdir(parents=True,exist_ok=False)
    text,ap,vp,dp,cp,windows=generate(event,command,step,spec['profile'])
    (out/'input.cir').write_text(text,encoding='utf8');(out/'.spiceinit').write_text(f'set ngbehavior=hsa\noption {solver}\nset num_threads=1\n',encoding='utf8')
    record=dict(status='in_progress',evidence_kind='fresh execution',event=event,command=command,solver=solver,max_step_s=step,profile=spec['profile'],spec=spec,
        tool=tool,external_sources=external,por_sources=por,output_dir=str(out),source_hashes={n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in SOURCES},
        written_deck_sha256=hashlib.sha256((out/'input.cir').read_bytes()).hexdigest(),source_functions=dict(analog=ap,digital=vp,data=dp,clock=cp))
    save(out/'run.json',record);start=time.perf_counter()
    try:
        result=subprocess.run([str(pilot.EXE),'-b','-o','ngspice.log','input.cir'],cwd=out,capture_output=True,text=True,timeout=spec['budget_s']);(out/'console.log').write_text(result.stdout+result.stderr,encoding='utf8')
        log=(out/'ngspice.log').read_text(errors='replace')
        if result.returncode or 'Error' in log or 'Transient op started' in log or 'timestep too small' in log.lower():raise ValueError('Incomplete acquisition or operating-point fallback')
        measured=measure(np.loadtxt(out/'history.dat',skiprows=1),ap,vp,dp,cp,windows,command)
        record.update(status='completed',result=measured)
        if event=='none':record['normal_storage_control_pass']=bool(measured['minimum_q_final_hold_V']>=1.44 if command else measured['maximum_q_final_hold_V']<=.36)
    except Exception as exc:
        record.update(status='unresolved',result=dict(status='unresolved',observed_pass=None,sampled_restoration_observed=None),reason=type(exc).__name__+': '+str(exc))
        for attr,name in [('stdout','timeout_stdout.log'),('stderr','timeout_stderr.log')]:
            value=getattr(exc,attr,None)
            if value:(out/name).write_bytes(value if isinstance(value,bytes) else value.encode())
    record['wall_s']=time.perf_counter()-start;save(out/'run.json',record)
    print('Published POR',event,'command:',command,record['status'],'observed:',record['result']['observed_pass'],flush=True);return record


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--event',choices=EVENTS,default='digital_zero');parser.add_argument('--retain-state',action='store_true');parser.add_argument('--solver',choices=['sparse','klu'],default=None);parser.add_argument('--max-step-us',type=float,default=None);args=parser.parse_args()
    result=run_por(event=args.event,command=not args.retain_state,solver=args.solver,max_step=None if args.max_step_us is None else args.max_step_us*1e-6)
    print('Recorded:',result['output_dir'],flush=True);return 0 if result['status']=='completed' else 2


if __name__=='__main__':raise SystemExit(main())
