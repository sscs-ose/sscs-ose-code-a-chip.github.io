"""Predeclared load/PWM ablation and unseen-pattern analog/RTL challenge."""
from pathlib import Path
from datetime import datetime,timezone
from concurrent.futures import ThreadPoolExecutor
import json,os,sys,time
ROOT=Path(__file__).resolve().parents[1]


def run():
    session=json.loads((ROOT/'docs/flow2_fresh_session_20261023.json').read_text());old=Path(session['work'])
    sys.path.insert(0,str(old/'notebook_sources'));sys.path.insert(0,str(ROOT))
    from automx_nb_inline_v1 import fresh_pilot,support,mha_engine
    base=Path('/media/nam/EDABK/Code_a_Chip_submission_20261023')
    study=base/('native_study_'+datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S'));study.mkdir(exist_ok=False)
    patterns=[
      ('sum_p3_low',[2,1,0,0],[1,1,1,1]),
      ('sum_p3_high',[6,-4,2,-1],[1,1,1,1]),
      ('sum_n3_low',[-2,-1,0,0],[1,1,1,1]),
      ('sum_n3_high',[-6,4,-2,1],[1,1,1,1]),
      ('active_zero',[4,4,-4,-4],[1,1,1,1]),
      ('sum_p5_high',[6,2,-2,-1],[1,1,1,1]),
      ('sum_n5_high',[-6,-2,2,1],[1,1,1,1]),
      ('mixed_weights',[4,-2,1,-1],[1,-1,-1,1])]
    original={}
    for p in old.glob('conversion_*/case.json'):
        d=json.loads(p.read_text());key=json.dumps(d,sort_keys=True);original[key]=str(p)
    requests=[]
    for label,a,w in patterns:
        key,payload=mha_engine.Experiment.payload(a,w)
        if json.dumps(payload,sort_keys=True) in original:raise ValueError('Challenge overlaps earlier pattern: '+label)
        requests.append((label,key,payload))
    fit=json.loads((old/'calibration.json').read_text())
    protocol={'declared_utc':datetime.now(timezone.utc).isoformat(),'source_session':str(old),'factorial_primary':'column 0 signed sum12-sum11 gap at t=1.9 ns',
       'factorial_conditions':[{'load_ff':c,'pwm_unit_ps':p} for c in (200,800) for p in (50,100)],
       'new_factorial_conditions':[[200,50],[800,100]],'prior_verified_conditions':[[200,100],[800,50]],
       'challenge_patterns':[{'label':name,**payload} for name,key,payload in requests],
       'calibration':fit,'calibration_frozen':True,'prior_pattern_overlap':0,
       'challenge_primary':'decoded sum mismatch and unrounded residual using frozen 3-point calibration',
       'scope':'Finite deterministic TT matched-pattern ablation and diagnostic challenge; no retuning after challenge.'}
    (study/'protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
    (ROOT/'docs/code_a_chip_study_location.json').write_text(json.dumps({'study':str(study),'source_session':str(old)},indent=2)+'\n')
    def factorial():
        def condition(point):return fresh_pilot.measure_pair(ROOT,study,*point)
        with ThreadPoolExecutor(max_workers=2) as pool:new=list(pool.map(condition,[(200,50),(800,100)]))
        prior=[json.loads((old/f'fresh_pex_c{c}_pwm{p}'/'measured.json').read_text()) for c,p in ((200,100),(800,50))]
        rows=[]
        for d in prior+new:
            for job in d['jobs']:
                if job['returncode']:raise ValueError('Incomplete factorial job')
            rows.append({**d,'acquisition':'new_native' if d in new else 'prior_verified_native'})
        result={'protocol':'protocol.json','conditions':rows,'no_new_calibration':True}
        (study/'factorial.json').write_text(json.dumps(result,indent=2)+'\n');return result
    def challenge():
        lib=study/'tools/ngspice_shared44/install/lib/libngspice.so';lib.parent.mkdir(parents=True);lib.symlink_to('/media/nam/EDABK/AutoMX_CIM_tools/ngspice_shared44/libngspice.so')
        flow=support.Flow(support.Settings(root=ROOT,cache=study,tag='challenge',reuse=False,timeout_s=180,jobs=3))
        experiment=mha_engine.Experiment(flow)
        observed=experiment.many([(key,payload) for _,key,payload in requests]);rows=[]
        for label,key,payload in requests:
            d=observed[key];truth=sum(a*w[0] for a,w in zip(payload['activation_x2'],payload['weights']))
            estimate=(d['result_code_12bit']-fit['offset_code'])/fit['slope_codes_per_integer_sum'];decoded=int(__import__('numpy').rint(estimate))
            rows.append({'label':label,'case':str(flow.work/('conversion_'+key)/'summary.json'),'reference_integer_sum':truth,
                'activity':sum(abs(a*w[0]) for a,w in zip(payload['activation_x2'],payload['weights'])),
                'raw_ADC_code':d['result_code_12bit'],'unrounded_calibrated_sum':estimate,'decoded_integer_sum':decoded,
                'error_integer_sum':decoded-truth,'residual_integer_sum':estimate-truth})
        result={'patterns':rows,'samples':len(rows),'decode_mismatches':sum(r['error_integer_sum']!=0 for r in rows),'calibration_frozen':True,'prior_pattern_overlap':0}
        (study/'challenge.json').write_text(json.dumps(result,indent=2)+'\n');return result
    started=time.monotonic()
    with ThreadPoolExecutor(max_workers=2) as pool:
        jobs=[pool.submit(factorial),pool.submit(challenge)]
        result=[job.result() for job in jobs]
    summary={'status':'NATIVE_STUDY_COMPLETED','elapsed_s':time.monotonic()-started,'study':str(study),'challenge_mismatches':result[1]['decode_mismatches'],'challenge_samples':result[1]['samples']}
    (study/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2),flush=True)
    return summary

def resume_factorial():
    """Resume an interrupted study without rerunning completed ADC challenges."""
    location=json.loads((ROOT/'docs/code_a_chip_study_location.json').read_text())
    study=Path(location['study']);old=Path(location['source_session'])
    sys.path.insert(0,str(old/'notebook_sources'));sys.path.insert(0,str(ROOT))
    from automx_nb_inline_v1 import fresh_pilot
    started=time.monotonic()
    def condition(point):
        path=study/f'fresh_pex_c{point[0]}_pwm{point[1]}'/'measured.json'
        if path.is_file():return json.loads(path.read_text())
        if path.parent.exists():
            path.parent.rename(path.parent.with_name(path.parent.name+'_interrupted_'+datetime.now(timezone.utc).strftime('%H%M%S')))
        return fresh_pilot.measure_pair(ROOT,study,*point)
    with ThreadPoolExecutor(max_workers=2) as pool:
        new=list(pool.map(condition,[(200,50),(800,100)]))
    prior=[json.loads((old/f'fresh_pex_c{c}_pwm{p}'/'measured.json').read_text()) for c,p in ((200,100),(800,50))]
    rows=[{**d,'acquisition':label} for label,group in [('prior_verified_native',prior),('new_native',new)] for d in group]
    if any(job['returncode'] for row in rows for job in row['jobs']):raise ValueError('Incomplete factorial job')
    (study/'factorial.json').write_text(json.dumps({'protocol':'protocol.json','conditions':rows,'no_new_calibration':True},indent=2)+'\n')
    challenge=json.loads((study/'challenge.json').read_text())
    summary={'status':'NATIVE_STUDY_COMPLETED','resumed_factorial':True,'resume_elapsed_s':time.monotonic()-started,
       'challenge_mismatches':challenge['decode_mismatches'],'challenge_samples':challenge['samples']}
    (study/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary),flush=True)

if __name__=='__main__':
    if '--resume-factorial' in sys.argv:resume_factorial()
    else:run()
