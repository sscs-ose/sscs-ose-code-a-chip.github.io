"""Program the same MHA IP for a retrained uniform-attention control."""
from pathlib import Path
import argparse,json
import numpy as np
import torch
from automx_cim.application_har import TinyAttention,metrics
from ip.automx_mha.verify import reference,pack
from scripts.verify_har_application_rtl import verify

def run(root,application,work):
    root=Path(root).resolve();application=Path(application).resolve();work=Path(work).resolve();work.mkdir(parents=True,exist_ok=True)
    torch.set_num_threads(2);data=np.load(application/'application_vectors.npz')
    model=TinyAttention();model.load_state_dict(torch.load(application/'uniform_model.pt',weights_only=True,map_location='cpu'));model.eval()
    with torch.no_grad():
        out,acts,context,attention=model.datapath(torch.from_numpy(data['features']),True,'uniform')
        prediction=model(torch.from_numpy(data['features']),True,'uniform').argmax(-1).numpy()
        weights={n:model.ternary(w).round().long().numpy() for n,w in zip(('Q','K','V','O'),model.weights)}
    # The unchanged hardware obtains uniform attention by Q=0, hence equal
    # scores and exactly 0.5/0.5 probabilities; V/O and the host head stay trained.
    weights['Q']=np.zeros((4,4),dtype=int);acts=(acts.numpy()*2).round().astype(int)
    expected=np.stack([reference(a,weights)['output_x2'] for a in acts]);assert np.array_equal(expected,(out.numpy()*2).round().astype(int))
    deployment={'weights':{k:v.tolist() for k,v in weights.items()},'embedding_weight':model.embedding.weight.detach().tolist(),
       'embedding_bias':model.embedding.bias.detach().tolist(),'head_weight':model.head.weight.detach().tolist(),'head_bias':model.head.bias.detach().tolist(),
       'configuration':'Retrained uniform attention through Q=0; no RTL changes or test-set tuning'}
    head=np.array(deployment['head_weight']);bias=np.array(deployment['head_bias']);observed=(expected.reshape(-1,8)/2@head.T+bias).argmax(1);assert np.array_equal(observed,prediction)
    indices=[int(np.flatnonzero(data['y']==i)[0]) for i in range(6)];small=work/'vectors';small.mkdir(exist_ok=True)
    (small/'deployment.json').write_text(json.dumps(deployment,indent=2)+'\n')
    np.savez_compressed(small/'application_vectors.npz',activation_x2=acts[indices],output_x2=expected[indices],y=data['y'][indices])
    masks=[]
    for stage in ('Q','K','V','O'):
        for row in weights[stage]:masks.append(sum(int(v>0)<<i for i,v in enumerate(row))|(sum(int(v<0)<<i for i,v in enumerate(row))<<4))
    for name,values,width in [('activations',[pack(a,5) for a in acts[indices]],10),('weights',[pack(masks,8)]*6,32),('outputs',[pack(a,12) for a in expected[indices]],24)]:
        (small/(name+'.memh')).write_text('\n'.join(f'{v:0{width}x}' for v in values)+'\n')
    rtl=verify(root,small,work/'rtl')
    result={'status':'PASS','configuration':deployment['configuration'],'software_test_windows':len(data['y']),
       'uniform_test_metrics':metrics(data['y'],prediction),'rtl_frames_per_path':6,'rtl_paths':len(rtl['results']),
       'integer_reference_output_mismatches':0,'primary_model_changed':False,'scope':'A second frozen weight configuration on the same IP/host interface, six real RTL frames per path; functional ADC fixture. Native analog coverage belongs to the primary model campaign.'}
    (work/'verification.json').write_text(json.dumps(result,indent=2)+'\n');print('SECOND_CONFIGURATION_PASS','software_windows',len(data['y']),'macro_F1',round(result['uniform_test_metrics']['macro_f1'],6),'RTL_paths',len(rtl['results']),'frames/path',6,'mismatches',0,flush=True);return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--application',type=Path,required=True);p.add_argument('--work',type=Path,required=True);a=p.parse_args();run(a.root,a.application,a.work)
