"""Train either five-member surrogate from regenerated EM arrays and fixed partitions."""
from environment import ROOT, configure
BUDGET=configure()
DEFAULT_THREADS=min(4,BUDGET)
DEFAULT_JOBS=min(3,max(1,BUDGET//DEFAULT_THREADS))
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import json
import multiprocessing
from pathlib import Path

import numpy as np
import torch
import surrogate as S
from learning_metrics import EpochR2, SCHEMA


def member(seed,kind_name,data_path,output,epochs,threads,device):
    torch.set_num_threads(threads)
    data=dict(np.load(data_path,allow_pickle=False))
    kind=S.kind_for('xfmr','unified',3) if kind_name=='transformer' else S.KINDS['spiral']
    cfg=dict(arch='res',width=256,depth=4,drop=.05)
    tr,va=data['tr'],data['va']
    r2=EpochR2(data,kind)
    state,history=S.train_one(data['xn'][tr],data['yn'][tr],data['xn'][va],data['yn'][va],
                             cfg,epochs,2e-3,64,device,seed,True,(data['ymax']-data['ymin'])/2,len(kind.sel),epoch_callback=r2)
    path=Path(output)/f'member_{seed}.pt'
    torch.save(dict(state=state,history=history,r2_history=r2.rows),path)
    return seed,str(path)


def train(kind_name,output,epochs=2000,ensemble=5,jobs=DEFAULT_JOBS,threads=DEFAULT_THREADS,data_path=None,device='cpu'):
    if min(epochs,ensemble,jobs,threads)<1 or jobs*threads>BUDGET:
        raise ValueError(f'Positive training settings must satisfy jobs*threads <= {BUDGET}')
    if device not in ('cpu','cuda'):raise ValueError('Choose cpu or cuda')
    if device=='cuda' and not torch.cuda.is_available():raise RuntimeError('CUDA was requested but is unavailable')
    output=Path(output)
    output.mkdir(parents=True,exist_ok=False)
    data_path=Path(data_path or ROOT/'runs'/(kind_name+'_data.npz')).resolve()
    try:
        data_reference=str(data_path.relative_to(ROOT))
    except ValueError:
        data_reference=data_path.name
    data=dict(np.load(data_path,allow_pickle=False))
    kind=S.kind_for('xfmr','unified',3) if kind_name=='transformer' else S.KINDS['spiral']
    torch.set_num_threads(threads)
    members={}
    with ProcessPoolExecutor(max_workers=jobs,mp_context=multiprocessing.get_context('spawn')) as pool:
        futures=[pool.submit(member,seed,kind_name,str(data_path),str(output),epochs,threads,device) for seed in range(ensemble)]
        for task in as_completed(futures):
            seed,path=task.result();members[seed]=torch.load(path,map_location='cpu',weights_only=False)
    data.update(data_dir=data_reference,max_index=int(data['idx'].max())+1)
    model=output/(kind_name+'.pt');cfg=dict(arch='res',width=256,depth=4,drop=.05)
    S.save_checkpoint(str(model),kind,[members[k]['state'] for k in range(ensemble)],cfg,data)
    predictor=S.Surrogate(str(model))
    report=S.test_metrics(predictor,data['geo'][data['te']],data['s'][data['te']])
    for label,partition in (('train','tr'),('val','va'),('test','te')):
        sel=data[partition];error=predictor.predict(data['geo'][sel])-data['s'][sel]
        report['mae_'+label]=float(np.stack([abs(error[:,:,i,j]) for i,j in kind.sel],axis=-1).mean())
    report.update(epochs=epochs,ensemble=ensemble,cfg=cfg,n_samples=len(data['geo']),
                  n_split=[len(data[k]) for k in ('tr','va','te')],history_all=[members[k]['history'] for k in range(ensemble)],
                  r2_history_all=[members[k]['r2_history'] for k in range(ensemble)],r2_schema=SCHEMA,
                  training_device=device,member_seeds=list(range(ensemble)),
                  model_sha256=hashlib.sha256(model.read_bytes()).hexdigest(),feature_count=data['xn'].shape[1],augmentation=None,
                  prepared_data_reference=data_reference,prepared_data_sha256=hashlib.sha256(data_path.read_bytes()).hexdigest())
    (output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(f"{kind_name}: complete, test complex-S error {report['dS_mean']:.2e}")


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kind',choices=('transformer','spiral'),required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--data',type=Path,help='Prepared arrays; defaults to runs/<kind>_data.npz')
    parser.add_argument('--epochs',type=int,default=2000)
    parser.add_argument('--ensemble',type=int,default=5)
    parser.add_argument('--jobs',type=int,default=DEFAULT_JOBS)
    parser.add_argument('--threads',type=int,default=DEFAULT_THREADS)
    parser.add_argument('--device',choices=('cpu','cuda'),default='cpu')
    args=parser.parse_args();train(args.kind,args.output,args.epochs,args.ensemble,args.jobs,args.threads,args.data,args.device)
