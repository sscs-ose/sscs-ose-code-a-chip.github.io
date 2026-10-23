"""Acquire a declared reference-controller case without saved-data fallback.
SPDX-License-Identifier: Apache-2.0
"""
from pathlib import Path
import argparse,hashlib,subprocess,time,uuid
import numpy as np
import pilot
from por_consumer import save,verify_models,verify_external_sources,verify_sources
from reference_devices import provenance
from reference_circuit import CASES,VARIANTS,generate,measure_application
HERE=Path(__file__).resolve().parent
SOURCES=['reference_consumer.py','reference_circuit.py','reference_loop.py','reference_devices.py','reference_sources.json',
    'results/reference/characterization/results.json','guard_circuit.py','guard_spec.json','por_circuit.py','por_models.py',
    'application_circuit.py','applicability_spec.json','powered_reset.py','reset_contract.py','pilot.py',
    'por_sources.json','external_sources.json','dependency_manifest.json']

def run_reference(*,case='cold_shallow',variant='reference_supervisor',group='primary',max_step=2e-6,output=None):
    tool=verify_models();external=verify_external_sources();por=verify_sources();reference=provenance()
    text,args=generate(case,variant,max_step,group)
    out=Path(output) if output else HERE/'results/reference_runs'/('run_'+uuid.uuid4().hex[:10])
    out.mkdir(parents=True,exist_ok=False)
    (out/'input.cir').write_text(text,encoding='utf-8')
    (out/'.spiceinit').write_text('set ngbehavior=hsa\noption sparse\nset num_threads=1\n',encoding='utf-8')
    record=dict(status='in_progress',evidence_kind='fresh execution',case=case,variant=variant,group=group,
        max_step_s=max_step,solver='sparse',output_dir=str(out),tool=tool,external_sources=external,
        por_sources=por,reference_sources=reference,
        source_hashes={n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in SOURCES},
        written_deck_sha256=hashlib.sha256((out/'input.cir').read_bytes()).hexdigest(),
        source_functions=dict(analog=args[0],digital=args[1],data=args[2],clock=args[3]))
    save(out/'run.json',record);start=time.perf_counter()
    try:
        sub=subprocess.run([str(pilot.EXE),'-b','-o','ngspice.log','input.cir'],cwd=out,capture_output=True,text=True,timeout=180)
        (out/'console.log').write_text(sub.stdout+sub.stderr,encoding='utf-8')
        log=(out/'ngspice.log').read_text(errors='replace')
        if sub.returncode or 'Error' in log or 'Transient op started' in log or 'timestep too small' in log.lower():
            raise ValueError('Incomplete acquisition or operating-point fallback')
        d=np.loadtxt(out/'history.dat',skiprows=1)
        record.update(status='completed',result=measure_application(d,args,case,variant),
            raw_sha256=hashlib.sha256((out/'history.dat').read_bytes()).hexdigest())
    except Exception as exc:
        record.update(status='unresolved',result=None,reason=type(exc).__name__+': '+str(exc))
        for attr in ('stdout','stderr'):
            b=getattr(exc,attr,None)
            if b:(out/('timeout_'+attr+'.log')).write_bytes(b if isinstance(b,bytes) else b.encode())
    record['elapsed_s']=time.perf_counter()-start;save(out/'run.json',record)
    print(case,variant,group,record['status'],record['result']['diagnosis'] if record['result'] else None,flush=True)
    return record

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--case',choices=CASES,default='cold_shallow')
    p.add_argument('--variant',choices=VARIANTS,default='reference_supervisor')
    p.add_argument('--group',choices=['primary','step','trough'],default='primary')
    p.add_argument('--max-step-us',type=float,default=2.)
    a=p.parse_args();r=run_reference(case=a.case,variant=a.variant,group=a.group,max_step=a.max_step_us*1e-6)
    return 0 if r['status']=='completed' else 2
if __name__=='__main__':raise SystemExit(main())
