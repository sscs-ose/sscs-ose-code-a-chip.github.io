"""Derive a bounded code-margin budget from newly acquired circuit reports."""
from pathlib import Path
import argparse,json


def run(work):
    work=Path(work).resolve()
    def read(name):return json.loads((work/'electrical'/name).read_text())
    nominal=read('matched_sum.json');settling=read('settling.json')
    pvt=read('pvt.json')['groups'];contract=read('campaign_contract.json')
    assert len(nominal)==96 and len(settling)==4 and len(pvt)==28
    accepted=[r for r in settling if r['wrong']==r['unresolved']==0]
    displacement=max(r['max_abs_anchor_drift_codes'] for r in accepted) if accepted else None
    rows=[]
    for bank in range(8):
        cases=[r for r in nominal if r['bank']==bank]
        resolved=[r for r in cases if not r.get('unresolved')]
        guard=min(r['margin_codes'] for r in resolved) if resolved else None
        wrong=sum(r.get('decoded')!=r['expected'] for r in cases)
        remaining=guard-displacement if guard is not None and displacement is not None else None
        rows.append({'bank':bank,'matched_sum_cases':len(cases),'wrong':wrong,
            'unresolved':len(cases)-len(resolved),'minimum_observed_guard_codes':guard,
            'additional_sampled_settling_debit_codes':displacement,
            'allocated_noise_offset_codes':0,'remaining_conditional_guard_codes':remaining,
            'conditional_positive_guard':bool(remaining is not None and remaining>0 and wrong==0),
            'scope':'Sampled nominal patterns and accepted settling policies; the settling debit conservatively includes pattern displacement. No stochastic noise or mismatch model is allocated.'})
    result={'status':'MEASURED_BUDGET','banks':rows,
        'stimulus':contract['stimulus'],
        'sampled_correct_settle_clocks':[r['settle_clocks'] for r in accepted],
        'retained_comparison_settle_clocks':16,
        'pvt_frozen_tt_wrong':sum(g.get('frozen_tt_wrong',0) for g in pvt),
        'pvt_recalibrated_wrong':sum(g.get('five_anchor_recalibrated_wrong',0) for g in pvt),
        'pvt_held_out_conversions':196,'pvt_unresolved':sum(g['unresolved'] for g in pvt),
        'scope':'A conservative arithmetic budget derived from measured raw-code guards. It is conditional on the declared finite pattern/condition set, without extrapolation to noise, offset, yield or ENOB. The matched power comparison retains its measured 16-clock policy.'}
    (work/'margin_budget.json').write_text(json.dumps(result,indent=2)+'\n')
    print('MARGIN_BUDGET',len(rows),'banks; minimum conditional guard',min((r['remaining_conditional_guard_codes'] for r in rows if r['remaining_conditional_guard_codes'] is not None),default=None),'codes; sampled correct settle clocks',result['sampled_correct_settle_clocks'],flush=True)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True)
    run(p.parse_args().work)
