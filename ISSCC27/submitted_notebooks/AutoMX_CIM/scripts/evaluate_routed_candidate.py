"""Measure a bounded candidate electrical envelope without bypassing adoption gates."""
from pathlib import Path
import json
import numpy as np
from scripts.run_electrical_qualification import Measurements,profile,case,PATTERNS,LEVELS,ALPHABET


def run(root,pwm,core_views,work,jobs=8):
    root=Path(root).resolve();work=Path(work).resolve();work.mkdir(parents=True,exist_ok=False)
    pwm=Path(pwm).resolve();physical=json.loads(pwm.read_text())
    checks=('zero_code_ok','nonzero_full_swing','single_pulse_ok','unselected_lines_quiet',
            'strict_width_order','strict_bitline_order','bitline_polarity_ok')
    assert len(physical['measurements'])==64
    requests=[];metadata=[]
    for row in range(4):
        for activation in (-12,-2,-1,0,1,2,12):
            acts=np.zeros(4,dtype=int);acts[row]=activation
            weights=np.zeros((4,4),dtype=int);weights[row,0]=1
            p=profile(4*(row//2),pwm,core_views=core_views);p['core_pex']=False
            requests.append({'activation_x2':acts.tolist(),'weights':weights.tolist(),'column':0,'profile':p})
            metadata.append({'row':row,'activation_x2':activation,'expected_partial_sum':activation})
    native=Measurements(root,work,jobs)
    measured=native.many(requests);rows=[]
    for meta,result in zip(metadata,measured):
        entry={**meta,'folder':result['folder'],'resolved':'result_code_12bit' in result}
        if entry['resolved']:entry.update(raw_code=result['result_code_12bit'],start_to_eoc_s=result['start_to_eoc_s'])
        else:entry['error']=result.get('error','Missing resolved native code')
        rows.append(entry)
    unresolved=sum(not row['resolved'] for row in rows)
    aliases=[]
    for row in range(4):
        group=[r for r in rows if r['row']==row and r['resolved']]
        zero=next((r['raw_code'] for r in group if r['activation_x2']==0),None)
        if zero is None:continue
        for entry in group:
            if entry['activation_x2'] and abs(entry['raw_code']-zero)<=1:
                aliases.append({'row':row,'activation_x2':entry['activation_x2'],'zero_code':zero,
                    'raw_code':entry['raw_code'],'difference_codes':entry['raw_code']-zero})
    failed=[k for k in checks if not physical[k]]
    calibration=None;matched=[];calibration_unresolved=0
    if not failed and not aliases and unresolved==0:
        calibration_requests=[]
        for bank in range(8):
            for level in LEVELS:
                pair=next((int(a),int(b)) for a in ALPHABET for b in ALPHABET if a+b==level)
                p=profile(bank,pwm,core_views=core_views);p['core_pex']=False
                calibration_requests.append(case(bank,pair,p))
        print('CANDIDATE_CALIBRATION',len(calibration_requests),'fresh conversions',flush=True)
        anchors=native.many(calibration_requests)
        calibration_unresolved=sum('result_code_12bit' not in r for r in anchors)
        if calibration_unresolved==0:
            codes=np.array([r['result_code_12bit'] for r in anchors]).reshape(8,39)
            strict=np.all(np.diff(codes,axis=1)>0,axis=1)
            calibration={'levels':LEVELS.tolist(),'codes':codes.tolist(),'strictly_increasing':strict.tolist(),
                'minimum_adjacent_code_step':np.diff(codes,axis=1).min(axis=1).tolist()}
            thresholds=(codes[:,:-1]+codes[:,1:]+1)//2
            tests=[]
            for bank in range(8):
                for pair in PATTERNS:
                    p=profile(bank,pwm,core_views=core_views);p['core_pex']=False
                    tests.append(case(bank,pair,p))
            observed=native.many(tests)
            for i,r in enumerate(observed):
                bank=i//12;expected=sum(PATTERNS[i%12]);entry={'bank':bank,'pattern':PATTERNS[i%12],
                    'expected':expected,'resolved':'result_code_12bit' in r,'bank_has_valid_ordered_calibration':bool(strict[bank]),'folder':r['folder']}
                if entry['resolved']:
                    entry['raw_code']=r['result_code_12bit']
                    if strict[bank]:entry['decoded']=int(LEVELS[np.searchsorted(thresholds[bank],r['result_code_12bit'],side='right')])
                matched.append(entry)
            (work/'calibration.json').write_text(json.dumps(calibration,indent=2)+'\n')
            (work/'matched_sum.json').write_text(json.dumps(matched,indent=2)+'\n')
    unresolved+=calibration_unresolved+sum(not row['resolved'] for row in matched)
    rejected=bool(failed or aliases or (calibration and not all(calibration['strictly_increasing'])) or
        any(row.get('decoded')!=row['expected'] for row in matched if row['bank_has_valid_ordered_calibration']))
    report={'status':'UNRESOLVED' if unresolved else ('EVALUATED_REJECTED' if rejected else 'EVALUATED_REQUIRES_APPLICATION_QUALIFICATION'),
        'failed_pulse_checks':failed,'physical_cases':64,'native_conversions':len(rows),
        'native_unresolved':unresolved,'single_row_codes':rows,'zero_aliases_within_one_code':aliases,
        'calibration':calibration,'matched_sum':matched,
        'additional_calibration_conversions':312 if calibration is not None else 0,
        'additional_matched_sum_conversions':len(matched),'unique_native_jobs':len(native.cache),
        'adopted':False,'stimulus':'Actual candidate routed PWL; compact transistor/MIM receiver reference; real SAR/comparator feedback',
        'scope':'Fixed signed single-row electrical diagnostic at TT, 1.8 V / 25 C. No expected-sum responses are injected. Missing waveforms remain missing and are not replaced by ideal pulses. This evaluation never authorizes candidate adoption or supplies calibration to the separate ideal-stimulus campaign.'}
    (work/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print('CANDIDATE_ELECTRICAL_EVALUATION',report['status'],'native',len(rows),'unresolved',unresolved,'zero aliases',len(aliases),flush=True)
    return report
