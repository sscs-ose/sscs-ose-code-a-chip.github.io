"""Create fresh frozen study inputs; this command makes no model or EDA calls."""
import argparse
import json
from pathlib import Path

from study_protocol import digest, preregistration, write_json

CASE=Path(__file__).resolve().parents[1]


def initialize(output):
    if output.exists():raise ValueError('Choose a new experiment directory')
    output.mkdir(parents=True)
    (output/'generation').mkdir();(output/'ppa').mkdir();(output/'baseline').mkdir()
    write_json(output/'protocol.json',preregistration())
    names=json.loads((CASE/'results/configurable-study/ppa/source-bindings.json').read_text())
    names=sorted(set(names) | {'study_portability.py', 'audit_study_ip.py', 'study_checks.py','study_ppa_proposal.py'})
    write_json(output/'ppa/source-bindings.json',{name:digest(CASE/'scripts'/name) for name in names})
    write_json(output/'source-bindings.json',{'common_contract_runner':digest(CASE/'scripts/run_configuration_study.py'),
        'final_checker':digest(CASE/'verification/npu_acceptance_tb.sv'),
        'public_checker':digest(CASE/'generation_seed/tb/npu_smoke_tb.sv'),
        'original_pe':digest(CASE/'ip/model2gds-dot4/rtl/gemm_pe.sv'),
        'isolation_helper':digest(CASE/'scripts/study_isolation.py'),
        'budget_helper':digest(CASE/'scripts/study_budget.py'),
        'trusted_checks':digest(CASE/'scripts/study_checks.py')})
    print('FRESH_STUDY_READY; no model or EDA calls: '+str(output))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    initialize(parser.parse_args().output.resolve())
