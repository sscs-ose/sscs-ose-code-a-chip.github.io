"""Audited finite-grid DC checks and loaded cold starts for declared SKY130 benches.
SPDX-License-Identifier: Apache-2.0
"""
from pathlib import Path
import argparse,hashlib,json,subprocess,uuid
import numpy as np
from pilot import simulate,PDK,EXE,HERE
from widlar_pilot import audit_return_case,find_roots
from measurements import measure_loaded
from circuits import CIRCUITS,WidlarCircuit


def verify_models():
    manifest=json.loads((HERE/'dependency_manifest.json').read_text())
    for relative,info in manifest['pdk_files'].items():
        path=PDK/relative
        if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest()!=info['sha256']:
            raise RuntimeError(f'Model source check failed: {relative}')
    version=subprocess.check_output([str(EXE),'--version'],text=True)
    if 'ngspice-47 ' not in version:raise RuntimeError('This validated example requires ngspice 47.')
    return {'model_commit':manifest['pdk_commit'],'verified_files':len(manifest['pdk_files']),'ngspice_version':version}


def verify_circuit(circuit,gmin=1e-15,load_resistance=1e5,ramp=1e-6):
    """Run one circuit adapter through fresh scans, intact OPs and a cold start.

    Adapters must preserve DC loading when cutting their declared gate. The
    supplied models disable DC gate leakage. No exhaustive state claim follows.
    """
    if not all(np.isfinite(x) and x>0 for x in [gmin,load_resistance,ramp]):
        raise ValueError('GMIN, resistance and ramp must be positive and finite.')
    source=verify_models()
    width=getattr(circuit,'startup_width',None)
    tag=f'verify_{circuit.name}_{uuid.uuid4().hex[:8]}'
    output=HERE/'results'/'verification'/tag
    output.mkdir(parents=True,exist_ok=True)
    report={'status':'in_progress','circuit':circuit.name,'description':circuit.description,'scope':'Declared SKY130 schematic bench with junction geometry and default zero NRD/NRS; finite-grid evidence only.','parameters':{'startup_width_um':width,'gmin_S':gmin,'load_resistance_ohm':load_resistance,'ramp_s':ramp,'compatibility':'hsa','solver':'klu','threads':1},'source':source,'return_scans':[]}
    def finish(status):
        report['status']=status
        (output/'report.json').write_text(json.dumps(report,indent=2))
        return report
    arrays=[]
    for direction in [1,-1]:
        folder=simulate(f'{tag}_dc{direction}',circuit.return_deck(gmin,direction,load_resistance),compatibility='hsa',solver='klu',threads=1)
        audit=audit_return_case(folder,3601)
        report['return_scans'].append({'case':folder.name,'audit':audit})
        if not audit['accepted']:return finish('rejected_dc_data')
        d=np.loadtxt(folder/'return.dat',skiprows=1)
        arrays.append(d if direction==1 else d[::-1])
    disagreement=float(abs(arrays[0][:,1]-arrays[1][:,1]).max())
    report['max_forward_reverse_difference_V']=disagreement
    if disagreement>1e-5:return finish('ambiguous_return_curve')
    candidates=find_roots(arrays[0]);confirmed=[]
    for k,root in enumerate(candidates):
        b=root['vin_V']
        state=[float(np.interp(b,arrays[0][:,0],arrays[0][:,2])),b,float(np.interp(b,arrays[0][:,0],arrays[0][:,3]))]
        folder=simulate(f'{tag}_op{k}',circuit.intact_deck(state,gmin,load_resistance),compatibility='hsa',solver='klu',threads=1)
        d=np.loadtxt(folder/'op.dat',skiprows=1)
        state_error=float(abs(d[1:4]-state).max())
        error=float(abs(d[2]-b))
        fallback='Transient op started' in (folder/'ngspice.log').read_text()
        confirmed.append({**root,'intact_state_V':dict(zip(circuit.state_vectors,map(float,d[1:4]))),'intact_b_V':float(d[2]),'bias_difference_V':error,'max_state_difference_V':state_error,'confirmed':state_error<1e-5 and not fallback,'dc_transient_fallback':fallback})
    report['candidate_operating_points']=confirmed
    if not confirmed or not all(r['confirmed'] for r in confirmed):return finish('unconfirmed_operating_points')
    golden=simulate(f'{tag}_loaded_op',circuit.loaded_deck(gmin,load_resistance,ramp,op=True),compatibility='hsa',solver='klu',threads=1)
    op=np.loadtxt(golden/'op.dat',skiprows=1);target=float(op[7])
    fallback='Transient op started' in (golden/'ngspice.log').read_text()
    # This intended operating point defines a target; it is not cold-start evidence.
    report['target_operating_point']={'output_A':target,'bias_V':float(op[2]),'output_V':float(op[6]),'dc_transient_fallback':fallback}
    if not np.isfinite(op).all() or target<=0 or op[2]<circuit.minimum_intended_bias_V or op[6]<.3 or fallback:
        return finish('invalid_useful_operating_point')
    folder=simulate(f'{tag}_loaded_cold',circuit.loaded_deck(gmin,load_resistance,ramp),compatibility='hsa',solver='klu',threads=1)
    cold=np.loadtxt(folder/'cold.dat',skiprows=1)
    report['loaded_test']={'case':folder.name,'nominal_target_A':target,'final_output_A':float(cold[-1,7]),'final_bias_V':float(cold[-1,2]),**measure_loaded(cold,target,ramp+1e-6+.001)}
    report['startup_verdict']='passes_declared_bench' if report['loaded_test']['meets_contract'] else 'fails_declared_bench'
    return finish('completed')


def verify_case(startup_width=.42,gmin=1e-15,load_resistance=1e5,ramp=1e-6):
    """Backward-compatible entry point for the original inverse-Widlar example."""
    if startup_width is not None and (not np.isfinite(startup_width) or startup_width<.42):
        raise ValueError('Startup width must be at least 0.42 um in this example.')
    return verify_circuit(WidlarCircuit(startup_width),gmin,load_resistance,ramp)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--circuit',choices=['inverse_widlar',*CIRCUITS],default='inverse_widlar')
    parser.add_argument('--startup-width',default='.42',help='Inverse-Widlar NMOS width in um, or none for its unassisted control')
    parser.add_argument('--gmin',type=float,default=1e-15)
    parser.add_argument('--load-resistance',type=float,default=1e5)
    parser.add_argument('--ramp',type=float,default=1e-6)
    args=parser.parse_args()
    if args.circuit=='inverse_widlar':
        width=None if args.startup_width.lower()=='none' else float(args.startup_width)
        report=verify_case(width,args.gmin,args.load_resistance,args.ramp)
    else:
        if args.startup_width!='.42':parser.error('--startup-width applies only to inverse_widlar')
        report=verify_circuit(CIRCUITS[args.circuit],args.gmin,args.load_resistance,args.ramp)
    print(json.dumps({'status':report['status'],'circuit':report['circuit'],'startup_verdict':report.get('startup_verdict','not_assessed'),'candidate_count':len(report.get('candidate_operating_points',[])),'loaded_test':report.get('loaded_test')},indent=2))
    if report['status']!='completed':raise SystemExit(1)

if __name__=='__main__':main()
