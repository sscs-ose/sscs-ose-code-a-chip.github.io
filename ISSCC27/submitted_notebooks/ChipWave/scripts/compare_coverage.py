"""Compare the same fixed T09 check groups; missing results remain unmeasured."""
from pathlib import Path
import argparse,json
BASE=Path(__file__).resolve().parents[1]/'results/functional.json'

def compare(baseline,candidate):
    rows=[]
    for name,base in baseline.items():
        bpassed,btotal=base['cases_passed'],base['cases_total']
        assert type(bpassed) is int and type(btotal) is int and 0<=bpassed<=btotal and btotal>0
        observed=candidate.get(name)
        if observed is None:
            passed=total=percentage=None;status='unmeasured'
        else:
            passed,total=observed['cases_passed'],observed['cases_total']
            if type(passed) is not int or type(total) is not int or not 0<=passed<=total or total!=btotal:raise ValueError('Invalid counts or changed fixed checker denominator: '+name)
            percentage=100*passed/total;status='all_passed' if passed==total else 'partial_or_failed'
        rows.append({'category':name,'baseline_passed':bpassed,'expected_checks':btotal,'baseline_percent':100*bpassed/btotal,'standard_passed':passed,'standard_executed_denominator':total,'standard_percent':percentage,'standard_status':status})
    if set(candidate)-set(baseline):raise ValueError('Unexpected checker groups')
    return rows

def self_check():
    base={'ISA':{'cases_passed':4,'cases_total':4},'RESET':{'cases_passed':2,'cases_total':2}}
    rows=compare(base,{'ISA':{'cases_passed':3,'cases_total':4}})
    assert rows[0]['standard_percent']==75 and rows[1]['standard_percent'] is None
    for invalid in ({'ISA':{'cases_passed':True,'cases_total':4}},{'ISA':{'cases_passed':3,'cases_total':3}},{'OTHER':{'cases_passed':1,'cases_total':1}}):
        try:compare(base,invalid)
        except ValueError:pass
        else:raise AssertionError('Invalid or incomparable checker result accepted')
    print('COVERAGE_SELF_CHECK_PASS: partial/missing groups and denominator/boolean/unknown-group rejection')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path);p.add_argument('--output',type=Path);p.add_argument('--self-check',action='store_true');a=p.parse_args()
    if a.self_check:self_check()
    else:
        if not a.candidate or not a.output:raise ValueError('Candidate and output paths required')
        if a.output.exists():raise ValueError('Prior comparison preserved; choose new output')
        baseline=json.loads(BASE.read_text())['base']['groups'];candidate=json.loads(a.candidate.read_text())
        result={'scope':'Fixed T09 check-category coverage, not RTL code coverage or a population success rate','candidate_phase':candidate.get('phase','unknown'),'rows':compare(baseline,candidate.get('groups',{})),'no_aggregate_percentage':'Check groups exercise overlapping behaviors; do not weight results by NPU exhaustive arithmetic counts','candidate_file':str(a.candidate.resolve())}
        a.output.write_text(json.dumps(result,indent=2)+'\n')
