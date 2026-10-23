"""Apply the same named-signal monitor to a pinned upstream resettable flip-flop.
SPDX-License-Identifier: Apache-2.0
"""
from pathlib import Path
import argparse,copy,hashlib,json,math,subprocess,time,uuid
import numpy as np
import pilot
from schematic_support import verify_models
from reset_contract import Band,Window,evaluate,source_work,waveform
from external_circuit import generate
from detector_design import validate_scale

HERE=Path(__file__).resolve().parent
SOURCES=['detector_design.py','external_consumer.py','external_circuit.py','external_spec.json','external_sources.json',
         'reset_contract.py','sequence_circuits.py','schematic_support.py','pilot.py']


def specification():
    return json.loads((HERE/'external_spec.json').read_text())


def save(path,value):
    Path(path).write_text(json.dumps(value,indent=2,allow_nan=False),encoding='utf8')


def verify_external_sources():
    manifest=json.loads((HERE/'external_sources.json').read_text())
    for item in manifest['files']:
        data=(HERE/item['path']).read_bytes()
        if hashlib.sha256(data).hexdigest()!=item['sha256'] or hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()!=item['git_blob']:
            raise ValueError('External source differs: '+item['path'])
    return dict(verified_files=len(manifest['files']),manifest_sha256=hashlib.sha256((HERE/'external_sources.json').read_bytes()).hexdigest())


def measure(data,config,scenario,contract,points,windows,data_points,clock_points):
    expected=11 if config['variant']=='rc' else 13
    d=np.asarray(data)
    if d.ndim!=2 or d.shape[1]!=expected or not np.isfinite(d).all():
        raise ValueError('Missing or nonfinite external-consumer vectors')
    t,v=waveform(d[:,0],dict(q=d[:,1],c=d[:,2],vdd=d[:,3],vsg=d[:,3]-d[:,2],clk=d[:,5],data=d[:,6]))
    if np.max(abs(d[0,[1,2,3]]))>1e-5:
        raise ValueError('Not the declared zero-supply initial state')
    for name,pwl,col in [('clock',clock_points,5),('data',data_points,6)]:
        ordinary=np.ones(len(t),dtype=bool)
        for instant,_ in pwl:ordinary &= abs(t-instant)>1e-7
        if not ordinary.any() or np.max(abs(d[ordinary,col]-np.interp(t[ordinary],[p[0] for p in pwl],[p[1] for p in pwl])))>.005:
            raise ValueError('Ordinary input witness differs: '+name)
    V=scenario['supply_V'];intended=[Band('q',upper=contract['logic_low_fraction']*V)]
    alternate=[Band('q',lower=contract['logic_high_fraction']*V)];rail=[Band('vdd',lower=contract['supply_ready_fraction']*V)]
    guard=points[4][0]-1e-7
    result=evaluate(t,v,supply_points=points,
                    windows=[Window(w['id'],w['start_s'],w['ramp_end_s'],w['stop_s']) for w in windows],
                    state_bands=rail+intended,release_bands=rail+[Band('c',lower=contract['reset_release_fraction']*V),Band('vsg',upper=.05*V)],
                    state_delay_s=contract['logic_deadline_after_ramp_s'],release_delay_s=contract['release_deadline_after_ramp_s'],hold_s=contract['hold_s'],
                    precondition_interval=(guard-5e-6,guard),prior_bands=intended if scenario['normal_set'].get('skip_command') else alternate,alternate_bands=alternate)
    work=source_work(t,dict(VDD=(d[:,3],d[:,4]),clock=(d[:,7],d[:,8]),data=(d[:,9],d[:,10])))
    hold=d[t>=points[-1][0]-contract['hold_s'],1]
    result.update(final_q_V=float(d[-1,1]),minimum_q_final_hold_V=float(np.min(hold)),maximum_q_final_hold_V=float(np.max(hold)),source_work=work,eligible_delivered_J=work['delivered_J'] if result['observed_pass'] and result['declared_precondition_verified'] else None,
                  final_source_current_A=float(-d[-1,4]),final_detector_current_A=float(d[-1,12]) if expected==13 else None,
                  scope='Original upstream schematic/default zero diffusion geometry and NRD/NRS. Ideal reset passives. VDD/clock/data source work counted; zero-volt detector probe does no work. No energy ranking across consumers or failed circuits.')
    return result


def run_external(*,command=True,solver=None,low_V=.9,output=None,detector_scale=None):
    spec=specification();solver=solver or spec['solver']
    if not isinstance(command,bool) or solver not in ['sparse','klu']:
        raise ValueError('Declare a Boolean prior-state operation and a supported backend')
    if isinstance(low_V,bool) or not isinstance(low_V,(int,float)) or not math.isfinite(low_V) or not 0<=low_V<=1.8:
        raise ValueError('Dip voltage must be finite and between 0 and 1.8 V')
    if detector_scale is not None:detector_scale=validate_scale(detector_scale)
    source=verify_models();external=verify_external_sources()
    out=Path(output) if output else HERE/'results/external_runs'/('run_'+uuid.uuid4().hex[:10]);out.mkdir(parents=True,exist_ok=False)
    record=dict(status='in_progress',consumer=spec['consumer'],evidence_kind='fresh execution',solver=solver,settings=spec['settings'],
                contract=spec['contract'],absolute_tolerances=spec['absolute_tolerances'],source=source,external_sources=external,acquisition_budget_s=spec['acquisition_budget_s'],output_dir=str(out),
                source_hashes={name:hashlib.sha256((HERE/name).read_bytes()).hexdigest() for name in SOURCES},cases=[])
    save(out/'run.json',record)
    for item in spec['configurations']:
        config=copy.deepcopy(item['configuration'])
        if detector_scale is not None and config['variant']=='supply_sensitive':config['detector_scale']=detector_scale
        scenario=copy.deepcopy(item['scenario']);scenario['normal_set']['skip_command']=not command;scenario['recovery']['low_V']=low_V;scenario['id']=f'external_tt_clock_{int(command)}_dip_{low_V:g}'
        text,points,windows,dp,cp=generate(config,scenario,spec['contract'],spec['settings'],spec['absolute_tolerances'])
        label=config['variant'];raw=out/'raw'/label;raw.mkdir(parents=True,exist_ok=False)
        (raw/'input.cir').write_text(text,encoding='utf8');(raw/'.spiceinit').write_text(f'set ngbehavior=hsa\noption {solver}\nset num_threads=1\n',encoding='utf8')
        row=dict(reset_network=label,configuration=config,scenario=scenario,raw_case='raw/'+label,
                 generated_deck_sha256=hashlib.sha256(text.encode()).hexdigest(),written_deck_sha256=hashlib.sha256((raw/'input.cir').read_bytes()).hexdigest())
        begin=time.perf_counter()
        try:
            result=subprocess.run([str(pilot.EXE),'-b','-o','ngspice.log','input.cir'],cwd=raw,capture_output=True,text=True,timeout=spec['acquisition_budget_s'])
            (raw/'console.log').write_text(result.stdout+result.stderr,encoding='utf8');log=(raw/'ngspice.log').read_text(errors='replace')
            if result.returncode or 'Error' in log or 'Transient op started' in log or 'timestep too small' in log.lower():
                raise ValueError('Execution error, incomplete transient or operating-point fallback')
            row.update(measure(np.loadtxt(raw/'sequence.dat',skiprows=1),config,scenario,spec['contract'],points,windows,dp,cp))
        except Exception as error:
            for attribute,name in [('stdout','timeout_stdout.log'),('stderr','timeout_stderr.log')]:
                data=getattr(error,attribute,None)
                if data:(raw/name).write_bytes(data if isinstance(data,bytes) else data.encode())
            row.update(status='unresolved',observed_pass=None,declared_precondition_verified=None,alternate_state_exercised=None,sampled_restoration_observed=None,reason=type(error).__name__+': '+str(error))
        row['wall_s']=time.perf_counter()-begin;record['cases'].append(row);save(out/'run.json',record)
        print('upstream DFF',label,row['status'],'observed pass:',row['observed_pass'],'other state:',row.get('alternate_state_exercised'),flush=True)
    record['status']='completed' if all(row['status']=='measured' for row in record['cases']) else 'has_unresolved'
    save(out/'run.json',record);return record


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--retain-state',action='store_true');p.add_argument('--solver',choices=['sparse','klu'],default=None);p.add_argument('--dip-V',type=float,default=.9);p.add_argument('--detector-scale',type=int,choices=[1,2,4],default=None);a=p.parse_args()
    record=run_external(command=not a.retain_state,solver=a.solver,low_V=a.dip_V,detector_scale=a.detector_scale)
    print('Recorded:',record['output_dir'],flush=True)
    return 0 if record['status']=='completed' else 2


if __name__=='__main__':
    raise SystemExit(main())
