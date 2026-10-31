"""Measure column/phase calibration and deployed HAR frames with native SAR feedback."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import argparse,json,subprocess,time,sys
import numpy as np
from ip.automx_mha.verify import reference,probability_fixed,quantize_x2

LEVELS=np.array([-24,-20,-18,*range(-16,17),18,20,24])
ALPHABET=np.array([-12,-8,-6,-4,-3,-2,-1,0,1,2,3,4,6,8,12])

class Native:
    def __init__(self,root,work,jobs=4):
        self.root=Path(root).resolve();self.work=Path(work).resolve();self.work.mkdir(parents=True,exist_ok=True)
        self.jobs=jobs;self.cache={};self.counter=0;self.records=[]
    def many(self,requests):
        fresh={}
        for case in requests:
            key=json.dumps(case,sort_keys=True)
            if key not in self.cache and key not in fresh:
                folder=self.work/'conversions'/f'case_{self.counter:05d}';self.counter+=1
                fresh[key]=(folder,case)
        def measure(item):
            key,(folder,case)=item;folder.mkdir(parents=True,exist_ok=True)
            (folder/'case.json').write_text(json.dumps(case,indent=2)+'\n')
            start=time.monotonic()
            args=[sys.executable,'-u',str(self.root/'scripts/portable_cim_sar.py'),'--root',str(self.root),
                '--work',str(folder),'--library',str(self.root/'tools/ngspice/libngspice.so'),'--case',str(folder/'case.json')]
            with (folder/'console.log').open('w') as log:r=subprocess.run(args,stdout=log,stderr=subprocess.STDOUT,timeout=180)
            if r.returncode:raise RuntimeError(str(folder)+': '+(folder/'console.log').read_text()[-1200:])
            result=json.loads((folder/'summary.json').read_text());result['folder']=str(folder)
            result['elapsed_s']=time.monotonic()-start
            assert result['activation_x2']==case['activation_x2'] and result['weights']==case['weights'] and result['column']==case['column']
            return key,result
        with ThreadPoolExecutor(max_workers=self.jobs) as pool:
            for key,result in pool.map(measure,fresh.items()):
                self.cache[key]=result;self.records.append(result)
        return [self.cache[json.dumps(c,sort_keys=True)] for c in requests]

def payload(acts,weights,column):return {'activation_x2':np.asarray(acts,dtype=int).tolist(),'weights':np.asarray(weights,dtype=int).tolist(),'column':int(column),'pwm_unit_ps':50}

def run(root,application,work,pilot=False,jobs=4):
    root=Path(root).resolve();work=Path(work).resolve();native=Native(root,work,jobs)
    levels=np.array([-24,-8,0,8,24]) if pilot else LEVELS
    requests=[]
    for phase in range(2):
        for column in range(4):
            for level in levels:
                pair=next((a,b) for a in ALPHABET for b in ALPHABET if a+b==level)
                acts=np.zeros(4,dtype=int);acts[2*phase:2*phase+2]=pair
                weights=np.zeros((4,4),dtype=int);weights[2*phase:2*phase+2,column]=1
                requests.append(payload(acts,weights,column))
    print('NATIVE_CALIBRATION_START',len(requests),flush=True)
    cal=native.many(requests);codes=np.array([c['result_code_12bit'] for c in cal]).reshape(8,len(levels))
    signs=np.sign(np.diff(codes,axis=1));direction=[]
    for bank in range(8):
        sign=-1 if np.all(signs[bank]<0) else (1 if np.all(signs[bank]>0) else 0);direction.append(sign)
        print('NATIVE_BANK',bank,'LEVELS',levels.tolist(),'CODES',codes[bank].tolist(),'DIRECTION',sign,flush=True)
    result={'status':'CALIBRATION_PILOT_COMPLETE' if pilot else 'CALIBRATION_COMPLETE','levels':levels.tolist(),'codes':codes.tolist(),
       'direction':direction,'unique_native_jobs':len(native.records),'calibration_source':'new native circuit/SAR jobs, separate from application frames',
       'scope':'Native transistor/RTL SAR partition with ideal 50ps-unit activation drivers and schematic CIM/conditioner. Not full-chip transistor co-simulation.'}
    (work/'calibration.json').write_text(json.dumps(result,indent=2)+'\n')
    if pilot:return result
    assert all(v==1 for v in direction),'Crossed ADC inputs must give increasing code in every bank'
    ascending=codes;thresholds=((ascending[:,:-1]+ascending[:,1:]+1)//2).astype(int)
    assert np.all(np.diff(thresholds,axis=1)>0)
    (work/'thresholds.memh').write_text('\n'.join(f'{v:03x}' for v in thresholds.flat)+'\n')
    # Selection is fixed by test label/index, before circuit outcomes are seen.
    app=Path(application);data=np.load(app/'application_vectors.npz')
    indices=[int(np.flatnonzero(data['y']==label)[0]) for label in (0,1)]
    weights={k:np.array(v,dtype=int) for k,v in json.loads((app/'deployment.json').read_text())['weights'].items()}
    (work/'frame_selection.json').write_text(json.dumps({'indices':indices,'rule':'first test index in classes 0 and 1; frozen before application measurements','thresholds_frozen':True},indent=2)+'\n')
    traces=[];frames=[];adc_words=[]
    for index in indices:
        acts=data['activation_x2'][index];projections={}
        def project(activation,weight,stage):
            req=[];coordinates=[]
            for token in range(2):
                for phase in range(2):
                    partial=activation[token].copy();partial[:2*phase]=0;partial[2*phase+2:]=0
                    for column in range(4):req.append(payload(partial,weight,column));coordinates.append((token,phase,column))
            measurements=native.many(req);out=np.zeros((2,4),dtype=int)
            for case,m,(token,phase,column) in zip(req,measurements,coordinates):
                code=m['result_code_12bit'];bank=4*phase+column
                decoded=int(LEVELS[np.searchsorted(thresholds[bank],code,side='right')])
                truth=int(np.asarray(case['activation_x2'])@weight[:,column]);out[token,column]+=decoded
                row={'frame_index':index,'stage':stage,'token':token,'phase':phase,'column':column,'bank':bank,
                   'raw_code':code,'raw_word':m['result_word_16bit'],'decoded':decoded,'expected':truth,'case':m['folder'],
                   'energy_j':m['energy']['monitored_total_j'],'start_to_eoc_s':m['start_to_eoc_s']}
                traces.append(row);adc_words.append(m['result_word_16bit'])
            return out
        for stage in ('Q','K','V'):projections[stage]=project(acts,weights[stage],stage)
        context=np.zeros((2,4),dtype=np.int64)
        for head in range(2):
            hs=slice(2*head,2*head+2);scores=projections['Q'][:,hs]@projections['K'][:,hs].T
            for row in range(2):
                p=probability_fixed(int(scores[row,0]-scores[row,1]));context[row,hs]=np.array([p,32768-p])@projections['V'][:,hs]
        context_x2=quantize_x2(context);output=project(context_x2,weights['O'],'O')
        gold=reference(acts,weights)['output_x2'];frames.append({'index':index,'label':int(data['y'][index]),'activation_x2':acts.tolist(),
            'observed_qkv':{k:v.tolist() for k,v in projections.items()},'context_x2':context_x2.tolist(),'output_x2':output.tolist(),
            'reference_output_x2':gold.tolist(),'output_mismatches':int(np.count_nonzero(output!=gold))})
        print('NATIVE_APPLICATION_FRAME',json.dumps(frames[-1]),flush=True)
    import csv
    with (work/'native_frame_trace.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(traces[0]));w.writeheader();w.writerows(traces)
    (work/'adc_words.memh').write_text('\n'.join(f'{v:04x}' for v in adc_words)+'\n')
    mismatches=sum(t['decoded']!=t['expected'] for t in traces)
    result.update(status='PASS' if mismatches==0 and all(f['output_mismatches']==0 for f in frames) else 'APPLICATION_DECODE_MISMATCH',
        frames=frames,logical_conversions=len(traces),unique_native_jobs=len(native.records),partial_decode_mismatches=mismatches,
        logical_analog_energy_j=sum(t['energy_j'] for t in traces),calibration_energy_j=sum(m['energy']['monitored_total_j'] for m in cal))
    (work/'verification.json').write_text(json.dumps(result,indent=2)+'\n');print('NATIVE_APPLICATION_RESULT',result['status'],'errors',mismatches,flush=True)
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--application',type=Path,required=True);p.add_argument('--work',type=Path,required=True);p.add_argument('--pilot',action='store_true')
    p.add_argument('--jobs',type=int,default=4)
    a=p.parse_args();run(a.root,a.application,a.work,a.pilot,a.jobs)
