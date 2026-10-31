"""Measured timing/PWM calibration, matched-sum/PVT, settling and six HAR frames."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import argparse,csv,json,subprocess,sys,time
import numpy as np
from scripts.run_har_native import LEVELS,ALPHABET
from ip.automx_mha.verify import reference,probability_fixed,quantize_x2

CORE_PEX=False
PATTERNS=[(0,0),(1,-1),(12,-12),(12,0),(6,6),(4,8),(-12,0),(-6,-6),(-4,-8),(4,0),(2,2),(6,-2)]
CONDITIONS=[('tt_25', 'tt',1.8,25),('tt_0','tt',1.8,0),('tt_70','tt',1.8,70),
    ('tt_1p62','tt',1.62,25),('tt_1p95','tt',1.95,25),('ss_hot','ss',1.62,70),('ff_cold','ff',1.95,0)]

def case_key(case):
    def normalize(value):
        if isinstance(value,dict):return {k:normalize(v) for k,v in value.items()}
        if isinstance(value,(list,tuple)):return [normalize(v) for v in value]
        if isinstance(value,bool):return value
        if isinstance(value,(int,float,np.integer,np.floating)):return float(value)
        return value
    return json.dumps(normalize(case),sort_keys=True)

class Measurements:
    def __init__(self,root,work,jobs):
        self.root=Path(root).resolve();self.work=Path(work).resolve();self.work.mkdir(parents=True,exist_ok=True)
        self.jobs=jobs;self.cache={};self.counter=0
        for folder in sorted((self.work/'conversions').glob('case_*')):
            self.counter=max(self.counter,int(folder.name.split('_')[-1])+1)
            if (folder/'summary.json').is_file():
                try:case=json.loads((folder/'case.json').read_text());row=json.loads((folder/'summary.json').read_text())
                except (OSError,json.JSONDecodeError):continue
                row['folder']=str(folder);self.cache[case_key(case)]=row
    def many(self,cases):
        fresh={}
        for case in cases:
            key=case_key(case)
            if key not in self.cache and key not in fresh:
                folder=self.work/'conversions'/f'case_{self.counter:05d}';self.counter+=1;fresh[key]=(folder,case)
        # Keep one native circuit alive for a bounded sequence of cases.
        # Each case reprograms real external controls and precharges again.
        groups={}
        for key,(folder,c) in fresh.items():
            p=c.get('profile',{});group=tuple(p.get(k) for k in ('corner','supply_v','temperature_c','core_pex','rshunt_ohm','quiet_step_ns','core_schematic','core_pex_path'))
            groups.setdefault(group,[]).append((key,folder,c))
        chunks=[]
        for values in groups.values():
            chunks.extend(values[i::self.jobs] for i in range(min(self.jobs,len(values))))
        def batch(entries):
            marker=entries[0][1].name;folder=self.work/'batches';folder.mkdir(exist_ok=True)
            manifest=folder/(marker+'.json');rows=[]
            for key,dest,c in entries:
                dest.mkdir(parents=True,exist_ok=False);(dest/'case.json').write_text(json.dumps(c,indent=2)+'\n')
            manifest.write_text(json.dumps([{'folder':str(dest)} for key,dest,c in entries],indent=2)+'\n')
            args=[sys.executable,'-u',str(self.root/'scripts/qualified_cim_sar_stream.py'),'--root',str(self.root),
                '--library',str(self.root/'tools/ngspice/libngspice.so'),'--batch',str(manifest)]
            start=time.monotonic()
            try:
                with manifest.with_suffix('.log').open('w') as log:q=subprocess.run(args,stdout=log,stderr=subprocess.STDOUT,timeout=max(420,60*len(entries)+300))
                failure='' if q.returncode==0 else manifest.with_suffix('.log').read_text()[-1200:]
            except subprocess.TimeoutExpired as error:failure=str(error)
            for key,dest,c in entries:
                if (dest/'summary.json').is_file():row=json.loads((dest/'summary.json').read_text());row['folder']=str(dest)
                else:row={'status':'UNRESOLVED','error':failure,'folder':str(dest)};(dest/'failure.json').write_text(json.dumps(row,indent=2)+'\n')
                rows.append((key,row))
            receipt={'cases':len(entries),'resolved':sum('result_code_12bit' in r for k,r in rows),'elapsed_s':time.monotonic()-start}
            manifest.with_suffix('.step.json').write_text(json.dumps(receipt,indent=2)+'\n')
            if receipt['resolved']!=receipt['cases']:print('NATIVE_BATCH_UNRESOLVED',marker,receipt,flush=True)
            return rows
        with ThreadPoolExecutor(max_workers=self.jobs) as pool:
            for rows in pool.map(batch,chunks):
                for key,row in rows:self.cache[key]=row
        return [self.cache[case_key(c)] for c in cases]

def profile(bank,pwm=None,condition=CONDITIONS[0],settle=16,timing=None,core_views=None):
    name,corner,supply,temp=condition;c=bank%4
    select=[240,1760,3280,4760][c]-c*(16-settle)*40
    start=[920,2440,3960,5440][c]-(c+1)*(16-settle)*40
    p={'corner':corner,'supply_v':supply,'temperature_c':temp,'core_pex':CORE_PEX,'max_step_ns':1,
       'timing':timing or {'pre_release_ns':80,'pulse_ns':120,'track_end_ns':160,'select_ns':select,'adc_start_ns':start}}
    if pwm:p['pwm_measurements']=str(Path(pwm).resolve())
    if core_views:
        folder=Path(core_views).resolve();fast=folder/'core_acquisition.grouped.pex.spice'
        if not fast.is_file():fast=folder/'core_acquisition.fast.pex.spice'
        schematic=folder/'core_acquisition.compact.spice'
        p.update(core_schematic=str(schematic if schematic.is_file() else folder/'core_acquisition.spice'),core_pex_path=str(fast if fast.is_file() else folder/'core_acquisition.pex.spice'))
    return p

def case(bank,pair,p):
    acts=np.zeros(4,dtype=int);acts[2*(bank//4):2*(bank//4)+2]=pair
    weights=np.zeros((4,4),dtype=int);weights[2*(bank//4):2*(bank//4)+2,bank%4]=1
    return {'activation_x2':acts.tolist(),'weights':weights.tolist(),'column':bank%4,'profile':p}

def decode(code,thresholds):return int(LEVELS[np.searchsorted(thresholds,code,side='right')])

def run(root,application,timing,work,pwm=None,jobs=6,pilot=False,core_pex=False,core_views=None):
    global CORE_PEX
    CORE_PEX=core_pex
    from functools import partial
    make_profile=partial(profile,core_views=core_views)
    root=Path(root).resolve();work=Path(work).resolve();native=Measurements(root,work,jobs)
    if pwm:
        physical=json.loads(Path(pwm).read_text());assert physical['zero_code_ok'] and physical['nonzero_full_swing'],'PWM contract must pass before physical calibration'
        assert physical.get('rc_model','distributed')=='distributed','Use detailed RC for the adopted calibration'
    contract={'core_model':'PEX' if core_pex else 'transistor schematic; physical-driver loading separately uses core PEX','patterns':PATTERNS,'conditions':CONDITIONS,'pvt_banks':[0,3,4,7],
       'core_view_directory':str(Path(core_views).resolve()) if core_views else None,'pvt_anchors':[-24,-12,0,12,24],'settle_clocks':[16,8,4,2],
       'stimulus':'routed measured PWM' if pwm else 'ideal 50ps unit; analog/timing diagnostic only',
       'calibration_policy':'312 nominal levels at maximum observed bank hold age; held-out arithmetic patterns not used to fit thresholds'}
    (work/'campaign_contract.json').write_text(json.dumps(contract,indent=2)+'\n')
    if pilot:
        cases=[case(bank,pair,make_profile(bank,pwm)) for bank in (0,3) for pair in [(0,0),(1,0),(12,0),(6,6)]]
        rows=native.many(cases);result={'status':'PILOT_COMPLETE','measurements':rows,'contract':contract}
        (work/'pilot.json').write_text(json.dumps(result,indent=2)+'\n');return result
    requests=[]
    for bank in range(8):
        for level in LEVELS:
            pair=next((int(a),int(b)) for a in ALPHABET for b in ALPHABET if a+b==level)
            requests.append(case(bank,pair,make_profile(bank,pwm)))
    print('NATIVE_CALIBRATION_START',len(requests),'conversions',flush=True)
    cal=native.many(requests);unresolved=[r for r in cal if 'result_code_12bit' not in r]
    if unresolved:raise RuntimeError(f'{len(unresolved)} unresolved nominal calibration jobs; inspect failure.json')
    codes=np.array([r['result_code_12bit'] for r in cal]).reshape(8,39)
    monotonic=np.all(np.diff(codes,axis=1)>0,axis=1)
    (work/'calibration.json').write_text(json.dumps({'levels':LEVELS.tolist(),'codes':codes.tolist(),'strictly_increasing':monotonic.tolist()},indent=2)+'\n')
    print('NATIVE_CALIBRATION',312,'conversions; strict banks',int(monotonic.sum()),'; minimum adjacent code step',int(np.diff(codes,axis=1).min()),flush=True)
    assert monotonic.all(),'Actual timing/PWM does not support a strictly increasing 39-level calibration'
    thresholds=((codes[:,:-1]+codes[:,1:]+1)//2).astype(int)
    (work/'thresholds.memh').write_text('\n'.join(f'{v:03x}' for v in thresholds.flat)+'\n')
    requests=[case(bank,pair,make_profile(bank,pwm)) for bank in range(8) for pair in PATTERNS]
    nominal=native.many(requests);nominal_rows=[]
    for i,r in enumerate(nominal):
        bank=i//12;truth=sum(PATTERNS[i%12]);anchor_pair=next((int(a),int(b)) for a in ALPHABET for b in ALPHABET if a+b==truth)
        row={'bank':bank,'pattern':PATTERNS[i%12],'expected':truth,'is_calibration_anchor':PATTERNS[i%12]==anchor_pair,'folder':r['folder']}
        if 'result_code_12bit' in r:
            code=r['result_code_12bit'];pos=int(np.flatnonzero(LEVELS==truth)[0]);lo=thresholds[bank,pos-1] if pos else 0;hi=thresholds[bank,pos] if pos<38 else 4096
            row.update(code=code,decoded=decode(code,thresholds[bank]),margin_codes=int(min(code-lo,hi-1-code)))
        else:row.update(unresolved=True)
        nominal_rows.append(row)
    (work/'matched_sum.json').write_text(json.dumps(nominal_rows,indent=2)+'\n')
    print('MATCHED_SUM',len(nominal_rows),'wrong',sum(r.get('decoded')!=r['expected'] for r in nominal_rows),'minimum margin',min(r.get('margin_codes',-999) for r in nominal_rows),flush=True)
    pvt_requests=[];pvt_meta=[]
    anchors=[-24,-12,0,12,24];held=[(1,-1),(12,-12),(6,6),(4,8),(-6,-6),(2,2),(6,-2)]
    for condition in CONDITIONS:
        for bank in (0,3,4,7):
            pairs=[next((int(a),int(b)) for a in ALPHABET for b in ALPHABET if a+b==level) for level in anchors]+held
            for i,pair in enumerate(pairs):pvt_requests.append(case(bank,pair,make_profile(bank,pwm,condition)));pvt_meta.append((condition[0],bank,i,sum(pair)))
    print('PVT_START',len(CONDITIONS),'conditions',len(pvt_requests),'conversions',flush=True)
    pvt=native.many(pvt_requests);pvt_groups=[]
    for g in range(28):
        rows=pvt[g*12:(g+1)*12];name,bank,_,_=pvt_meta[g*12]
        valid=all('result_code_12bit' in r for r in rows);entry={'condition':name,'bank':bank,'conversions':12,'unresolved':sum('result_code_12bit' not in r for r in rows)}
        if valid:
            a=np.array([r['result_code_12bit'] for r in rows[:5]]);increasing=bool(np.all(np.diff(a)>0));entry['anchor_codes']=a.tolist();entry['strict_anchors']=increasing
            truth=[m[3] for m in pvt_meta[g*12+5:g*12+12]]
            entry['frozen_tt_wrong']=sum(decode(r['result_code_12bit'],thresholds[bank])!=t for r,t in zip(rows[5:],truth))
            if increasing:
                interpolated=np.interp(LEVELS,anchors,a);t=((interpolated[:-1]+interpolated[1:])/2)
                entry['five_anchor_recalibrated_wrong']=sum(decode(r['result_code_12bit'],t)!=s for r,s in zip(rows[5:],truth))
        pvt_groups.append(entry)
    (work/'pvt.json').write_text(json.dumps({'logical_conversions':336,'groups':pvt_groups,'policy':'Five measured anchors with piecewise interpolation; not 39 measured levels at every condition. PWM remains nominal unless a corner-specific waveform path is supplied.'},indent=2)+'\n')
    print('PVT_RESULT','unresolved',sum(r['unresolved'] for r in pvt_groups),'frozen wrong',sum(r.get('frozen_tt_wrong',0) for r in pvt_groups),'recalibrated wrong',sum(r.get('five_anchor_recalibrated_wrong',0) for r in pvt_groups),flush=True)
    settling=[]
    for wait in (16,8,4,2):
        cases=[case(bank,pair,make_profile(bank,pwm,settle=wait)) for bank in range(8) for pair in [(12,0),(6,6),(12,-12)]]
        rows=native.many(cases);wrong=0;unresolved=0;drift=[]
        for i,r in enumerate(rows):
            bank=i//3;truth=[12,12,0][i%3]
            if 'result_code_12bit' not in r:unresolved+=1;continue
            wrong+=decode(r['result_code_12bit'],thresholds[bank])!=truth
            drift.append(r['result_code_12bit']-codes[bank,np.flatnonzero(LEVELS==truth)[0]])
        settling.append({'settle_clocks':wait,'conversions':24,'wrong':int(wrong),'unresolved':unresolved,'max_abs_anchor_drift_codes':int(max(map(abs,drift))) if drift else None})
    print('SETTLING_RESULT',json.dumps(settling),flush=True)
    (work/'settling.json').write_text(json.dumps(settling,indent=2)+'\n')
    app=Path(application);data=np.load(app/'application_vectors.npz');indices=[int(np.flatnonzero(data['y']==i)[0]) for i in range(6)]
    weights={k:np.array(v,dtype=int) for k,v in json.loads((app/'deployment.json').read_text())['weights'].items()}
    all_times=list(csv.DictReader(Path(timing).open()));assert len(all_times)>=384
    times=all_times[:384]
    frames=[];traces=[];adc_words=[]
    for frame_no,index in enumerate(indices):
        projections={}
        def project(activation,weight,stage):
            req=[];coords=[]
            for token in range(2):
                for phase in range(2):
                    partial=activation[token].copy();partial[:2*phase]=0;partial[2*phase+2:]=0
                    for column in range(4):
                        ordinal=len(traces)+len(req)
                        t=times[ordinal];assert int(t['phase'])==phase and int(t['column'])==column
                        prof=make_profile(phase*4+column,pwm,timing={k:float(t[k]) for k in ('pre_release_ns','pulse_ns','track_end_ns','select_ns','adc_start_ns')})
                        req.append({'activation_x2':partial.tolist(),'weights':weight.tolist(),'column':column,'profile':prof});coords.append((token,phase,column))
            measured=native.many(req);out=np.zeros((2,4),dtype=int)
            for c,m,(token,phase,column) in zip(req,measured,coords):
                if 'result_code_12bit' not in m:raise RuntimeError('Unresolved application conversion: '+m['folder'])
                bank=4*phase+column;value=decode(m['result_code_12bit'],thresholds[bank]);out[token,column]+=value
                truth=int(np.array(c['activation_x2'])@weight[:,column]);adc_words.append(m['result_word_16bit'])
                traces.append({'frame_index':index,'stage':stage,'token':token,'phase':phase,'column':column,'bank':bank,'raw_code':m['result_code_12bit'],
                  'raw_word':m['result_word_16bit'],'decoded':value,'expected':truth,'case':m['folder'],'start_to_eoc_s':m['start_to_eoc_s']})
            return out
        for stage in ('Q','K','V'):projections[stage]=project(data['activation_x2'][index],weights[stage],stage)
        context=np.zeros((2,4),dtype=np.int64)
        for head in range(2):
            hs=slice(2*head,2*head+2);scores=projections['Q'][:,hs]@projections['K'][:,hs].T
            for row in range(2):
                p=probability_fixed(int(scores[row,0]-scores[row,1]));context[row,hs]=np.array([p,32768-p])@projections['V'][:,hs]
        output=project(quantize_x2(context),weights['O'],'O');gold=reference(data['activation_x2'][index],weights)['output_x2']
        frames.append({'index':index,'label':int(data['y'][index]),'output_x2':output.tolist(),'output_mismatches':int(np.count_nonzero(output!=gold))})
        print('QUALIFIED_NATIVE_FRAME',index,frames[-1]['output_mismatches'],flush=True)
    with (work/'native_frame_trace.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(traces[0]));w.writeheader();w.writerows(traces)
    (work/'adc_words.memh').write_text('\n'.join(f'{v:04x}' for v in adc_words)+'\n')
    errors=sum(t['decoded']!=t['expected'] for t in traces)
    result={'status':'PASS' if errors==0 and all(f['output_mismatches']==0 for f in frames) else 'APPLICATION_DECODE_MISMATCH',
       'frames':frames,'logical_conversions':384,'partial_decode_mismatches':errors,'nominal_matched_sum_conversions':96,
       'nominal_held_out_cases':sum(not r['is_calibration_anchor'] for r in nominal_rows),'nominal_anchor_rechecks':sum(r['is_calibration_anchor'] for r in nominal_rows),'nominal_matched_sum_wrong':sum(r.get('decoded')!=r['expected'] for r in nominal_rows),'pvt_conversions':336,
       'additional_direct_mode_control_requests':len(all_times)-384,'settling_conversions':96,'unique_native_jobs':len(native.cache),'contract':contract,
       'scope':'Timing-profiled measurement-driven partition. Per-conversion initial acquisition is repeated; energies must not be summed as a continuous-frame supply measurement.'}
    (work/'verification.json').write_text(json.dumps(result,indent=2)+'\n');print('ELECTRICAL_QUALIFICATION',result['status'],errors,flush=True);return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--application',type=Path,required=True);p.add_argument('--timing',type=Path,required=True);p.add_argument('--work',type=Path,required=True);p.add_argument('--pwm',type=Path);p.add_argument('--jobs',type=int,default=6);p.add_argument('--pilot',action='store_true');p.add_argument('--core-pex',action='store_true');p.add_argument('--core-views',type=Path);a=p.parse_args();run(a.root,a.application,a.timing,a.work,a.pwm,a.jobs,a.pilot,a.core_pex,a.core_views)
