"""Regenerate the finite cross-circuit reuse check with fresh simulations."""
import json
from pilot import HERE
from startright import verify_case,verify_circuit
from circuits import CIRCUITS


def main():
    destination=HERE/'results'/'reuse';destination.mkdir(exist_ok=True)
    records=[]
    for circuit in CIRCUITS.values():
        for gmin in [1e-12,1e-15]:
            for resistance in [1e5,1e6]:
                for ramp in [1e-6,1e-3]:
                    result=verify_circuit(circuit,gmin,resistance,ramp)
                    assert result['status']=='completed',result
                    assert len(result['candidate_operating_points'])==1,result
                    assert result['startup_verdict']=='passes_declared_bench',result
                    records.append(result)
                    print(circuit.name,gmin,resistance,ramp,result['startup_verdict'],flush=True)
                    (destination/'family_checks.json').write_text(json.dumps({'status':'in_progress','cases':records},indent=2))
    regressions=[]
    for width,gmin,expected_count,expected_pass in [(None,1e-12,1,False),(None,1e-15,3,False),(.42,1e-15,1,True)]:
        result=verify_case(width,gmin)
        assert result['status']=='completed',result
        assert len(result['candidate_operating_points'])==expected_count,result
        assert result['loaded_test']['meets_contract']==expected_pass,result
        regressions.append(result)
        print('Original circuit:',width,gmin,result['startup_verdict'],flush=True)
    summary={'status':'passed','scope':'Finite TT/27 C schematic reuse check on the same Windows/ngspice 47 host. No new-circuit PVT, mismatch, extraction or silicon validation. Each circuit/load/GMIN target is computed from its own intended operating point. No energy ranking between circuit families.','contract':{'current_tolerance_fraction':.05,'minimum_VDD_V':1.7,'minimum_output_V':.3,'deadline_after_supply_ramp_s':.001,'hold_s':.002},'cases':records,'original_circuit_regressions':regressions}
    (destination/'family_checks.json').write_text(json.dumps(summary,indent=2))
    print('PASS:',len(records),'additional cases and',len(regressions),'original-circuit regressions.',flush=True)


if __name__=='__main__':main()
