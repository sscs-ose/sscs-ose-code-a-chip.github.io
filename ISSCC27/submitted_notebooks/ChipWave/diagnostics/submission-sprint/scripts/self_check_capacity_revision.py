"""Prove retained costs cannot be erased or converted into extra new attempts."""
import copy
import json
import tempfile
from pathlib import Path
from capacity_protocol import protocol,PHYSICAL_LIMITS
from capacity_budget import reserve
from import_capacity_prior import validate_inherited
from study_protocol import write_json,digest

ROOT=Path(__file__).resolve().parents[1]


def rejected(fn):
    try:fn()
    except (ValueError,FileNotFoundError):return
    raise AssertionError('Changed inherited allowance accepted')


def check():
    with tempfile.TemporaryDirectory(prefix='capacity-revised-budget-') as temp:
        root=Path(temp);rules=protocol();rules.update(pilot_launch_allowed=True,formal_launch_allowed=True)
        write_json(root/'protocol.json',rules)
        origin=root/'provenance/original.json';write_json(origin,dict(fixture=True))
        counts=dict(reference_module=4,reference_integration=4,preformal_calibration=1,retained_invalid_pilot=1)
        rows=[dict(identity=f'{k}-{i}',trial=f'{k}-{i}',category=k,status='failed' if k=='retained_invalid_pilot' else 'passed') for k,n in counts.items() for i in range(n)]
        ledger=dict(limits=PHYSICAL_LIMITS,absolute_total=194,attempts=rows)
        write_json(root/'physical-ledger.json',ledger)
        write_json(root/'checks/inherited-attempts.json',dict(passed=True,attempts=rows,source_files={'provenance/original.json':digest(origin)}))
        validate_inherited(root)
        for category in counts:rejected(lambda:reserve(root,category,'extra','extra-'+category))
        for category in ('pilot','formal'):
            for job in rules[category+'_jobs']:
                for index in range(2):reserve(root,category,job['id'],job['id']+'-'+str(index))
                rejected(lambda:reserve(root,category,job['id'],job['id']+'-third'))
        state=json.loads((root/'physical-ledger.json').read_text());assert len(state['attempts'])==194
        validate_inherited(root)
        original=copy.deepcopy(state)
        state['attempts'].pop(0);write_json(root/'physical-ledger.json',state)
        rejected(lambda:validate_inherited(root))
        write_json(root/'physical-ledger.json',original)
        origin.write_text('changed');rejected(lambda:validate_inherited(root))
        assert rules['design_session_token_ceiling']==93_000_000
        assert len(rules['pilot_jobs'])==8 and len(rules['formal_jobs'])==84
        assert all(j['id']!='pilot-luna-A1' for j in rules['pilot_jobs'])
    receipt=dict(passed=True,model_calls=0,physical_runs=0,checks=['ten retained debits immutable','no new reference/calibration/retained slots','eight fresh pilots and 84 formal sessions limited to two attempts each','combined ceiling exactly 194','third attempts rejected','erased debit and changed provenance rejected','93M design ceiling includes original invalid session'])
    write_json(ROOT/'checks/revised-budget.json',receipt)
    return receipt

if __name__=='__main__':print(json.dumps(check()))
