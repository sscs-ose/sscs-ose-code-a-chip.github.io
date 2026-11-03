"""Subject-disjoint wearable classification using the exact AutoMX MHA contract.

Copyright 2026 EDABK Laboratory. SPDX-License-Identifier: Apache-2.0.
Feature extraction, embedding and classification are software; only the
two-token MHA block is the candidate hardware accelerator.
"""
from pathlib import Path
from copy import deepcopy
import argparse, json, time
import numpy as np
import torch
from torch import nn
from sklearn.metrics import accuracy_score, f1_score, confusion_matrix, recall_score
from sklearn.linear_model import LogisticRegression

MAGNITUDES = (0., .5, 1., 1.5, 2., 3., 4., 6.)
LABELS = ('WALKING','WALKING_UPSTAIRS','WALKING_DOWNSTAIRS','SITTING','STANDING','LAYING')

def save(path, value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2)+'\n')

def load_features(folder, split):
    """Mean/RMS of 6 axes in each 64-reading half; no fitted parameters."""
    folder=Path(folder);signals=[]
    for name in ('total_acc_x','total_acc_y','total_acc_z','body_gyro_x','body_gyro_y','body_gyro_z'):
        signals.append(np.loadtxt(folder/split/'Inertial Signals'/f'{name}_{split}.txt',dtype=np.float32))
    x=np.stack(signals,axis=-1).reshape(-1,2,64,6)
    features=np.concatenate((x.mean(2),np.sqrt((x*x).mean(2))),axis=-1)
    y=np.loadtxt(folder/split/f'y_{split}.txt',dtype=int)-1
    subjects=np.loadtxt(folder/split/f'subject_{split}.txt',dtype=int)
    assert features.shape==(len(y),2,12) and np.isfinite(features).all()
    return features,y,subjects

def quantize(values):
    mags=values.new_tensor(MAGNITUDES)
    indices=(values.abs().unsqueeze(-1)-mags).abs().argmin(-1)
    hard=values.sign()*mags[indices]
    return values+(hard-values).detach()

class TinyAttention(nn.Module):
    def __init__(self):
        super().__init__()
        self.embedding=nn.Linear(12,4)
        self.weights=nn.ParameterList([nn.Parameter(torch.empty(4,4).uniform_(-.8,.8)) for _ in range(4)])
        self.head=nn.Linear(8,6)
        import math
        self.register_buffer('lut',torch.tensor([round(32768/(1+math.exp(-i/8))) for i in range(65)],dtype=torch.long))

    def ternary(self,w):
        hard=w.sign()*(w.abs()>=.35)
        return w+(hard-w).detach()

    def datapath(self, features, quantized=True, attention='learned'):
        x=torch.tanh(self.embedding(features))*3
        if quantized:x=quantize(x)
        weights=[self.ternary(w) if quantized else w for w in self.weights]
        q,k,v=[(x@w).reshape(-1,2,2,2).transpose(1,2) for w in weights[:3]]
        scores=(q@k.transpose(-1,-2))/(2**.5)
        p=torch.sigmoid(scores[...,0]-scores[...,1])
        if quantized:
            integer_scores=(q*2)@(k*2).transpose(-1,-2)
            d=(integer_scores[...,0]-integer_scores[...,1]).detach().round().long()
            m=d.abs();scaled=m*181;index=(scaled//128).clamp(max=63);fraction=scaled%128
            val=self.lut[index]+((self.lut[index+1]-self.lut[index])*fraction+64)//128
            val=torch.where(m>=46,torch.full_like(val,32768),val)
            val=torch.where(d<0,32768-val,val).float()/32768
            p=p+(val-p).detach()
        if attention=='uniform':p=torch.full_like(p,.5)
        elif attention=='identity':
            p=torch.zeros_like(p);p[...,0]=1
        a=torch.stack((p,1-p),dim=-1)
        context=(a@v).transpose(1,2).reshape(-1,2,4)
        if quantized:context=quantize(context)
        output=context@weights[3]
        return output,x,context,a

    def forward(self, features, quantized=True, attention='learned'):
        output,*_=self.datapath(features,quantized,attention)
        return self.head(output.flatten(1))

def metrics(y, pred):
    return {'accuracy':float(accuracy_score(y,pred)),'macro_f1':float(f1_score(y,pred,average='macro',zero_division=0)),
            'per_class_recall':recall_score(y,pred,average=None,labels=np.arange(6),zero_division=0).tolist(),
            'confusion_matrix':confusion_matrix(y,pred,labels=np.arange(6)).tolist()}

def train(model,x,y,train_mask,val_mask,*,seed,epochs,quantized,attention='learned',lr=.012):
    torch.manual_seed(seed);rng=np.random.default_rng(seed)
    optimizer=torch.optim.Adam(model.parameters(),lr=lr,weight_decay=1e-5)
    ids=np.flatnonzero(train_mask);x_t=torch.from_numpy(x);y_t=torch.from_numpy(y).long()
    best=-1.;state=None;history=[];start=time.monotonic()
    for epoch in range(epochs):
        model.train()
        for batch in np.array_split(rng.permutation(ids),max(1,len(ids)//512)):
            optimizer.zero_grad();loss=nn.functional.cross_entropy(model(x_t[batch],quantized,attention),y_t[batch]);loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(),5);optimizer.step()
            with torch.no_grad():
                for w in model.weights:w.clamp_(-1,1)
        if epoch%10==0 or epoch==epochs-1:
            model.eval()
            with torch.no_grad():pred=model(x_t[val_mask],quantized,attention).argmax(-1).numpy()
            score=float(f1_score(y[val_mask],pred,average='macro',zero_division=0))
            history.append({'epoch':epoch+1,'validation_macro_f1':score})
            if score>best:best=score;state=deepcopy(model.state_dict())
            if epoch%40==0:print('TRAIN',json.dumps({'seed':seed,'quantized':quantized,'attention':attention,'epoch':epoch+1,'validation_macro_f1':score}),flush=True)
    model.load_state_dict(state)
    return {'validation_macro_f1':best,'history':history,'elapsed_s':time.monotonic()-start,'seed':seed,'quantized':quantized,'attention':attention}

def run(root,work,epochs=160):
    root=Path(root).resolve();work=Path(work).resolve();work.mkdir(parents=True,exist_ok=True)
    torch.set_num_threads(2);torch.manual_seed(2027);np.random.seed(2027)
    folder=root/'data/uci_har/UCI HAR Dataset'
    raw,y,subjects=load_features(folder,'train')
    unique=np.unique(subjects);val_subjects=np.random.default_rng(2027).permutation(unique)[:5]
    val_mask=np.isin(subjects,val_subjects);train_mask=~val_mask
    mean=raw[train_mask].mean((0,1),keepdims=True);std=raw[train_mask].std((0,1),keepdims=True).clip(.001)
    x=((raw-mean)/std).astype(np.float32)
    contract={'dataset':'UCI HAR, DOI 10.24432/C54S4K','source_url':'https://archive.ics.uci.edu/dataset/240/human+activity+recognition+using+smartphones',
        'dataset_license':'CC BY 4.0','dataset_creators':'Reyes-Ortiz, Anguita, Ghio, Oneto and Parra (2013)',
        'features':'Two half-windows; mean/RMS of total_acc xyz and body_gyro xyz; 12 software features/token',
        'fit_subjects':np.unique(subjects[train_mask]).tolist(),'validation_subjects':sorted(val_subjects.tolist()),
        'selection':'Validation macro-F1 only; fixed 3 QAT seeds; no test-label model selection',
        'configuration':{'tokens':2,'channels':4,'heads':2,'ternary_threshold':.35,'shared_activation_scale':1},
        'normalization_mean':mean.reshape(-1).tolist(),'normalization_std':std.reshape(-1).tolist(),
        'software_components':['feature extraction','12-to-4 embedding','8-to-6 classification head'],
        'hardware_candidate':'Only Q/K/V, attention, context quantization and O projection'}
    save(work/'training_contract.json',contract)
    teacher=TinyAttention();teacher_report=train(teacher,x,y,train_mask,val_mask,seed=2027,epochs=epochs,quantized=False)
    torch.save(teacher.state_dict(),work/'float_model.pt');save(work/'float_training.json',teacher_report)
    candidates=[];best=None
    for seed in (2027,2028,2029):
        model=deepcopy(teacher)
        if seed!=2027:
            torch.manual_seed(seed)
            with torch.no_grad():
                for w in model.weights:w.add_(torch.randn_like(w)*.025)
        report=train(model,x,y,train_mask,val_mask,seed=seed,epochs=epochs,quantized=True)
        torch.save(model.state_dict(),work/f'qat_{seed}.pt');save(work/f'qat_{seed}.json',report);candidates.append(report)
        if best is None or report['validation_macro_f1']>best[0]:best=(report['validation_macro_f1'],model,seed)
    model=best[1];torch.save(model.state_dict(),work/'deployed_model.pt')
    uniform=deepcopy(teacher);uniform_report=train(uniform,x,y,train_mask,val_mask,seed=2027,epochs=epochs,quantized=True,attention='uniform')
    torch.save(uniform.state_dict(),work/'uniform_model.pt');save(work/'uniform_training.json',uniform_report)
    linear=LogisticRegression(C=1,max_iter=1500).fit(x[train_mask].reshape(-1,24),y[train_mask])
    with torch.no_grad():
        weights={n:model.ternary(w).round().long().tolist() for n,w in zip(('Q','K','V','O'),model.weights)}
    # Freeze selection and all deployment inputs BEFORE loading test labels.
    deployment={'selected_seed':best[2],'selection_validation_macro_f1':best[0],
       'weights':weights,'embedding_weight':model.embedding.weight.detach().tolist(),
       'embedding_bias':model.embedding.bias.detach().tolist(),'head_weight':model.head.weight.detach().tolist(),
       'head_bias':model.head.bias.detach().tolist(),'normalization':{'mean':contract['normalization_mean'],'std':contract['normalization_std']},
       'test_used_for_selection':False,'seeds_compared':[2027,2028,2029],'activation_gain':3}
    save(work/'deployment.json',deployment)
    raw_test,test_y,test_subjects=load_features(folder,'test')
    assert not set(subjects)&set(test_subjects)
    test_x=((raw_test-mean)/std).astype(np.float32);tensor=torch.from_numpy(test_x)
    model.eval();teacher.eval();uniform.eval()
    with torch.no_grad():
        logits=model(tensor).numpy();out,acts,context,attention=model.datapath(tensor)
        predictions={'float':teacher(tensor,False).argmax(-1).numpy(),'integer_mha':logits.argmax(-1),
          'uniform_retrained':uniform(tensor,True,'uniform').argmax(-1).numpy(),
          'uniform_frozen':model(tensor,True,'uniform').argmax(-1).numpy(),
          'identity_frozen':model(tensor,True,'identity').argmax(-1).numpy(),
          'linear_features':linear.predict(test_x.reshape(-1,24)),
          'majority':np.full(len(test_y),np.bincount(y[train_mask]).argmax())}
    input_x2=(acts.numpy()*2).round().astype(int);output_x2=(out.numpy()*2).round().astype(int)
    from ip.automx_mha.verify import reference, pack
    array_weights={k:np.array(v,dtype=int) for k,v in weights.items()}
    expected=np.stack([reference(a,array_weights)['output_x2'] for a in input_x2])
    assert np.array_equal(expected,output_x2),'Training forward differs from independent IP integer reference'
    report={'status':'PASS','test_windows':len(test_y),'test_subjects':np.unique(test_subjects).tolist(),
      'selected_seed':best[2],'test_not_used_for_selection':True,'integer_reference_output_mismatches':int(np.count_nonzero(expected-output_x2)),
      'models':{name:metrics(test_y,p) for name,p in predictions.items()},
      'per_subject':{str(int(s)):{name:metrics(test_y[test_subjects==s],p[test_subjects==s]) for name,p in predictions.items()} for s in np.unique(test_subjects)},
      'input_nonzero_fraction':float(np.mean(input_x2!=0)),'scope':'Software application evaluation with exact integer MHA; separate RTL and native SPICE verification required.'}
    save(work/'application_metrics.json',report)
    np.savez_compressed(work/'application_vectors.npz',activation_x2=input_x2,output_x2=output_x2,y=test_y,subjects=test_subjects,features=test_x,predictions=predictions['integer_mha'])
    masks=[]
    for stage in ('Q','K','V','O'):
        for row in array_weights[stage]:
            masks.append(sum(int(v>0)<<i for i,v in enumerate(row))|(sum(int(v<0)<<i for i,v in enumerate(row))<<4))
    for name,values,width in [('activations',[pack(a,5) for a in input_x2],10),('weights',[pack(masks,8)]*len(test_y),32),('outputs',[pack(a,12) for a in expected],24)]:
        (work/f'{name}.memh').write_text('\n'.join(f'{v:0{width}x}' for v in values)+'\n')
    import csv
    with (work/'model_comparison.csv').open('w') as f:
        writer=csv.writer(f);writer.writerow(['model','accuracy','macro_f1'])
        for name,m in report['models'].items():writer.writerow([name,m['accuracy'],m['macro_f1']])
    print('APPLICATION_PASS',json.dumps({k:report[k] for k in ('test_windows','test_subjects','integer_reference_output_mismatches','models')}),flush=True)
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--work',type=Path,required=True);p.add_argument('--epochs',type=int,default=160)
    a=p.parse_args();import sys;sys.path.insert(0,str(a.root.resolve()));run(a.root,a.work,a.epochs)
