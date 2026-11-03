"""Extract differential output reflection from the independently verified TIA."""
from environment import ROOT,configure
configure()
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

import numpy as np
import skrf as rf
import tia_sim as T
import multiturn_experiment as M


def simulate(base,folder,excitation,matched=False,loaded=False):
    folder.mkdir(parents=True,exist_ok=False)
    source=base.split('\n.control',1)[0]
    source,count=re.subn(r'^Iin 0 pd dc 0 ac 1$',
                         f'Iin 0 pd dc 0 ac {int(excitation=="input")}',source,flags=re.M)
    if count!=1:raise ValueError('Missing input test source')
    if not loaded:
        for name,node in (('RLDp','outp'),('RLDn','outn')):
            old=f'{name} {node} 0 50'
            if source.count(old)!=1:raise ValueError('Unexpected output termination')
            source=source.replace(old,f'{name} {node} 0 1e12 noisy=0')
    if matched:source+='\nCmatch pd pd_match 1u\nRmatch pd_match 0 50 noisy=0'
    if excitation=='p':source+='\nIprobe 0 outp dc 0 ac 1'
    elif excitation=='n':source+='\nIprobe 0 outn dc 0 ac 1'
    elif excitation=='differential':source+='\nIprobeP 0 outp dc 0 ac 1\nIprobeN outn 0 dc 0 ac 1'
    elif excitation!='input':raise ValueError('Unsupported excitation')
    op_print=re.search(r'^print .*$',base,flags=re.M).group()
    source+='\n.control\nset filetype=ascii\nop\n'+op_print+'\nac lin 991 1G 100G\nwrdata voltages.txt v(outp) v(outn)\nquit\n.endc\n.end\n'
    (folder/'test.cir').write_text(source)
    shutil.copy2(Path(T.HERE)/'.spiceinit',folder/'.spiceinit')
    run=subprocess.run(['bash',T.NGSPICE,str((folder/'test.cir').resolve())],cwd=folder,capture_output=True,text=True,timeout=600)
    (folder/'ngspice.log').write_text(run.stdout+run.stderr)
    if run.returncode or not (folder/'voltages.txt').exists():raise RuntimeError('Output-reflection circuit evaluation failed')
    data=np.loadtxt(folder/'voltages.txt')
    if data.shape!=(991,6) or not np.isfinite(data).all():raise ValueError('Invalid complex AC output table')
    np.testing.assert_array_equal(data[:,0],data[:,3])
    volts=np.column_stack((data[:,1]+1j*data[:,2],data[:,4]+1j*data[:,5]))
    op={k:float(v) for k,v in re.findall(r'^((?:v|i)\(\w+\)) = ([-+0-9.eE]+)',run.stdout,re.M)}
    return data[:,0],volts,op


def build(output,root=ROOT):
    root=Path(root)
    from workflow import require_circuit_tools
    require_circuit_tools()
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=False)
    final=json.loads((root/'data/final_design.json').read_text())
    comparison=json.loads((root/'results/comparison.json').read_text())
    passives=root/'data/passives'
    l1,lb=[M.circuit_model(rf.Network(str(passives/name))) for name in ('L1.s2p','LB.s2p')]
    results={};checks={}
    for name in ('with_transformer','without_transformer'):
        xf=M.circuit_model(rf.Network(str(passives/'transformer.s4p')),[3,2,0,1]) if name=='with_transformer' else None
        base=T.netlist(final['params'],xf,l1,lb,'123');directory=output/name
        f,v,op=simulate(base,directory/'loaded','input',loaded=True)
        with np.load(root/f'results/{name}.npz',allow_pickle=False) as saved:
            np.testing.assert_allclose(f,saved['f'],rtol=0,atol=1)
            np.testing.assert_allclose(v[:,0]-v[:,1],saved['zt'],rtol=1e-8,atol=1e-9)
        expected=comparison['runs'][name]['metrics']['op']
        np.testing.assert_allclose([op[k] for k in expected],list(expected.values()),rtol=1e-8,atol=1e-10)
        columns=[]
        for terminal in ('p','n'):
            fp,vp,opp=simulate(base,directory/terminal,terminal,matched=True)
            np.testing.assert_array_equal(fp,f)
            np.testing.assert_allclose([opp[k] for k in op],list(op.values()),rtol=1e-7,atol=1e-9)
            columns.append(vp)
        network=rf.Network(f=f,z=np.stack(columns,axis=-1),z0=50)
        network.se2gmm(1)
        np.testing.assert_allclose(network.z0,np.broadcast_to([100.,25.],network.z0.shape),rtol=1e-12)
        gamma=network.s[:,0,0]
        _,direct,_=simulate(base,directory/'differential_check','differential',matched=True,loaded=True)
        direct_gamma=(direct[:,0]-direct[:,1])/50-1
        np.testing.assert_allclose(direct_gamma,gamma,rtol=1e-5,atol=2e-7)
        results.update(f=f,**{name:gamma});checks[name]=float(abs(direct_gamma-gamma).max())
    path=output/'output_reflection.npz';np.savez_compressed(path,**results)
    inputs=['data/final_design.json','results/comparison.json','results/with_transformer.npz','results/without_transformer.npz']
    inputs+=['data/passives/'+f for f in ('transformer.s4p','L1.s2p','LB.s2p')]
    metadata=dict(quantity='differential output Sdd22',reference_differential_ohm=100,reference_common_mode_ohm=25,
        input_termination_ohm=50,input_dc_blocking_capacitance_f=1e-6,common_mode_termination='matched',
        output_reference_planes=['outp','outn'],frequency_grid_ghz=[1,100,.1],
        data_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        source_sha256={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in inputs},
        method='Two independent output current probes, Z to mixed-mode S conversion and a direct differential-current cross-check.',
        direct_check_max_complex_error=checks)
    (output/'output_reflection.json').write_text(json.dumps(metadata,indent=2)+'\n')
    return metadata



if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--result-root',type=Path,required=True)
    args=parser.parse_args();print(json.dumps(build(args.output,root=args.result_root),indent=2))
