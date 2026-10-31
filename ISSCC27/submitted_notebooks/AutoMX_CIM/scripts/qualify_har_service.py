"""Frozen-model validation challenges and observed-RTL sensor-to-label replay."""
from pathlib import Path
import argparse,json,time
import numpy as np
import torch
from automx_cim.application_har import TinyAttention,load_features,metrics,LABELS

def run(root,application,rtl,work):
    root=Path(root).resolve();application=Path(application).resolve();rtl=Path(rtl).resolve()
    work=Path(work).resolve();work.mkdir(parents=True,exist_ok=True)
    torch.set_num_threads(2)
    contract=json.loads((application/'training_contract.json').read_text())
    deploy=json.loads((application/'deployment.json').read_text())
    # Fixed challenge definitions are committed before any challenge outcomes.
    challenge={'selection':'validation subjects only; no model or threshold changes',
       'cases':{'clean':'original features','missing_half':'second half replaced by first half',
          'gain_10_percent':'all six raw sensor axes multiplied by 1.10',
          'acc_x_bias_0p05g':'total acceleration x biased by +0.05 g'},
       'validation_subjects':contract['validation_subjects'],'test_used_for_tuning':False}
    (work/'challenge_contract.json').write_text(json.dumps(challenge,indent=2)+'\n')
    model=TinyAttention();model.load_state_dict(torch.load(application/'deployed_model.pt',map_location='cpu',weights_only=True));model.eval()
    uniform=TinyAttention();uniform.load_state_dict(torch.load(application/'uniform_model.pt',map_location='cpu',weights_only=True));uniform.eval()
    folder=root/'data/uci_har/UCI HAR Dataset'
    signals=[]
    for name in ('total_acc_x','total_acc_y','total_acc_z','body_gyro_x','body_gyro_y','body_gyro_z'):
        signals.append(np.loadtxt(folder/'train/Inertial Signals'/f'{name}_train.txt',dtype=np.float32))
    windows=np.stack(signals,axis=-1).reshape(-1,2,64,6)
    y=np.loadtxt(folder/'train/y_train.txt',dtype=int)-1
    subjects=np.loadtxt(folder/'train/subject_train.txt',dtype=int)
    mask=np.isin(subjects,contract['validation_subjects']);windows=windows[mask];y=y[mask]
    mean=np.asarray(contract['normalization_mean'],dtype=np.float32)
    std=np.asarray(contract['normalization_std'],dtype=np.float32)
    results=[]
    for name in challenge['cases']:
        w=windows.copy()
        if name=='missing_half':w[:,1]=w[:,0]
        if name=='gain_10_percent':w*=1.1
        if name=='acc_x_bias_0p05g':w[:,:,:,0]+=.05
        features=np.concatenate((w.mean(2),np.sqrt((w*w).mean(2))),axis=-1)
        x=torch.from_numpy(((features-mean)/std).astype(np.float32))
        with torch.no_grad():
            for label,m,attention in [('learned',model,'learned'),('uniform_retrained',uniform,'uniform'),('identity_frozen',model,'identity')]:
                pred=m(x,True,attention).argmax(-1).numpy()
                row={'challenge':name,'model':label,'windows':len(y),**metrics(y,pred)}
                results.append(row);print('VALIDATION_CHALLENGE',name,label,f"F1={row['macro_f1']:.6f}",flush=True)
    data=np.load(application/'application_vectors.npz');test_y=data['y']
    lines=(rtl/'observed_binary.memh').read_text().splitlines();assert len(lines)==len(test_y)
    observed=np.empty((len(lines),2,4),dtype=int)
    for i,line in enumerate(lines):
        word=int(line,16)
        for j in range(8):
            value=(word>>(12*j))&4095;observed[i,j//4,j%4]=value-4096 if value&2048 else value
    assert np.array_equal(observed,data['output_x2']), 'Observed hardware outputs differ from frozen vectors'
    head=np.asarray(deploy['head_weight']);bias=np.asarray(deploy['head_bias'])
    pred=(observed.reshape(-1,8)/2@head.T+bias).argmax(1)
    assert np.array_equal(pred,data['predictions'])
    # Host timings are wall-clock measurements on this host, not accelerator cycles.
    test_signals=[]
    for name in ('total_acc_x','total_acc_y','total_acc_z','body_gyro_x','body_gyro_y','body_gyro_z'):
        test_signals.append(np.loadtxt(folder/'test/Inertial Signals'/f'{name}_test.txt',dtype=np.float32))
    test_windows=np.stack(test_signals,axis=-1).reshape(-1,2,64,6)
    indices=[int(np.flatnonzero(test_y==label)[0]) for label in range(6)]
    ew=np.asarray(deploy['embedding_weight'],dtype=np.float32);eb=np.asarray(deploy['embedding_bias'],dtype=np.float32)
    alphabet=np.array([0,.5,1,1.5,2,3,4,6],dtype=np.float32)
    def preprocess(window):
        feature=np.concatenate((window.mean(1),np.sqrt((window*window).mean(1))),axis=-1)
        feature=(feature-mean)/std;act=np.tanh(feature@ew.T+eb)*3
        return (np.sign(act)*alphabet[np.abs(np.abs(act)[...,None]-alphabet).argmin(-1)]*2).astype(int)
    for i in indices:assert np.array_equal(preprocess(test_windows[i]),data['activation_x2'][i])
    timing=[]
    for rep in range(510):
        i=indices[rep%6];t=time.perf_counter_ns();acts=preprocess(test_windows[i]);mid=time.perf_counter_ns()
        logits=observed[i].reshape(8)/2@head.T+bias;end=time.perf_counter_ns()
        if rep>=10:timing.append(((mid-t)/1000,(end-mid)/1000))
    timing=np.array(timing)
    frames=[{'index':i,'activity':LABELS[int(test_y[i])],'predicted':LABELS[int(pred[i])],
        'activation_x2':data['activation_x2'][i].tolist(),'observed_output_x2':observed[i].tolist(),
        'hardware_output_mismatches':0} for i in indices]
    report={'status':'PASS','validation_challenges':results,'sensor_to_label':metrics(test_y,pred),
      'rtl_frames':len(lines),'rtl_output_values':len(lines)*8,'rtl_prediction_mismatches':0,'six_class_frames':frames,
      'host_timing_us':{'samples':500,'preprocess_embedding_median':float(np.median(timing[:,0])),
         'preprocess_embedding_p95':float(np.quantile(timing[:,0],.95)),
         'head_median':float(np.median(timing[:,1])),'head_p95':float(np.quantile(timing[:,1],.95))},
      'resident_configuration_payload':{'ternary_weight_masks_bits':128,'calibration_bits':304*12,
          'request_bits':40,'response_bits':96,'transport':'actual RTL parallel ready/valid; no SPI/CPU power model'},
      'scope':'Frozen deployment, validation-only fixed corruptions, observed RTL values for all test windows, measured CPU preprocessing/head timing. Native analog coverage is recorded separately.'}
    (work/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print('SENSOR_TO_LABEL_PASS',len(lines),'frames',json.dumps(report['host_timing_us']),flush=True)
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--application',type=Path,required=True);p.add_argument('--rtl',type=Path,required=True);p.add_argument('--work',type=Path,required=True);a=p.parse_args();run(a.root,a.application,a.rtl,a.work)
