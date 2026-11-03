"""A short declared check of frozen predictions, six RTL frames and GDS hierarchy."""
from pathlib import Path
import argparse,json,subprocess,sys,time
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from ip.automx_mha.verify import reference,pack
from scripts.verify_har_application_rtl import verify

def run(root,work,application=None,gds=None):
    root=Path(root).resolve();work=Path(work).resolve();work.mkdir(parents=True,exist_ok=False)
    app=Path(application).resolve() if application else root/'ip/automx_mha/examples/har'
    start=time.monotonic();deployment=json.loads((app/'deployment.json').read_text());data=np.load(app/'application_vectors.npz')
    weights={k:np.array(v,dtype=int) for k,v in deployment['weights'].items()}
    ew=np.array(deployment['embedding_weight'],dtype=np.float32);eb=np.array(deployment['embedding_bias'],dtype=np.float32)
    values=np.tanh(data['features']@ew.T+eb)*3;alphabet=np.array([0,.5,1,1.5,2,3,4,6],dtype=np.float32)
    acts=(np.sign(values)*alphabet[np.abs(np.abs(values)[...,None]-alphabet).argmin(-1)]*2).astype(int)
    assert np.array_equal(acts,data['activation_x2'])
    outputs=np.stack([reference(a,weights)['output_x2'] for a in acts]);assert np.array_equal(outputs,data['output_x2'])
    head=np.array(deployment['head_weight']);bias=np.array(deployment['head_bias'])
    predictions=(outputs.reshape(-1,8)/2@head.T+bias).argmax(1);assert np.array_equal(predictions,data['predictions'])
    print('FROZEN_PREDICTIONS_PASS',len(predictions),'windows',flush=True)
    indices=[int(np.flatnonzero(data['y']==i)[0]) for i in range(6)];small=work/'six_frames';small.mkdir()
    (small/'deployment.json').write_text(json.dumps(deployment,indent=2)+'\n')
    np.savez_compressed(small/'application_vectors.npz',**{k:data[k][indices] for k in ('activation_x2','output_x2','y','subjects','features','predictions')})
    masks=[]
    for stage in ('Q','K','V','O'):
        for row in weights[stage]:masks.append(sum(int(v>0)<<i for i,v in enumerate(row))|(sum(int(v<0)<<i for i,v in enumerate(row))<<4))
    for name,values,width in [('activations',[pack(a,5) for a in acts[indices]],10),('weights',[pack(masks,8)]*6,32),('outputs',[pack(a,12) for a in outputs[indices]],24)]:
        (small/f'{name}.memh').write_text('\n'.join(f'{v:0{width}x}' for v in values)+'\n')
    rtl=verify(root,small,work/'rtl')
    gds=Path(gds).resolve() if gds else root/'exports/AutoMX_CIM_five_block_top.gds';proof=work/'gds.json';script=work/'gds_check.py'
    script.write_text('import pya,json\nl=pya.Layout();l.read('+repr(str(gds))+')\nt=l.cell("automx_cim_mixed_signal_proto");assert t is not None\n'
       'names=sorted({l.cell(i.cell_index).name for i in t.each_inst()})\n'
       'assert "automx_mha_ip" in names and "automx_cim_readout_seq" in names\n'
       'json.dump(dict(status="PASS",top=t.name,children=names,cells=l.cells()),open('+repr(str(proof))+',"w"),indent=2)\n')
    q=subprocess.run(['klayout','-b','-r',str(script)],capture_output=True,text=True,timeout=90)
    (work/'klayout.log').write_text(q.stdout+q.stderr);assert q.returncode==0,(q.stdout+q.stderr)[-1200:]
    geometry=json.loads(proof.read_text())
    report={'status':'PASS','elapsed_s':time.monotonic()-start,'software_windows':len(predictions),'software_output_mismatches':0,
      'rtl_frames_per_path':6,'rtl_paths':len(rtl['results']),'rtl_output_values_per_path':48,'six_test_indices':indices,
      'gds':geometry,'training_rerun':False,'native_conversions_rerun':0,'physical_route_rerun':False,
      'scope':'Frozen deployment/input fixture re-evaluated from features; six preselected class frames through four actual RTL paths; current GDS hierarchy read by KLayout. Full Run All is the fresh circuit/physical acquisition path.'}
    (work/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print('QUICK_REVIEW_PASS',round(report['elapsed_s'],2),'s',flush=True);return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=ROOT);p.add_argument('--work',type=Path,required=True);p.add_argument('--application',type=Path);p.add_argument('--gds',type=Path);a=p.parse_args();run(a.root,a.work,a.application,a.gds)
