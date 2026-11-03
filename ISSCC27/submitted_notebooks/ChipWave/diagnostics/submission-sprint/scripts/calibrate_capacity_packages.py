"""Publish reference-derived scorecards only after all four CPU integrations qualify."""
import json

from capacity_integration_physical import ROOT,verified_integration
from capacity_physical_evidence import audit
from capacity_protocol import TASKS,score
from study_protocol import digest,write_json


def calibrate():
    if (ROOT/'campaign-freeze.json').exists():raise ValueError('Frozen campaign cannot be recalibrated')
    ledger=json.loads((ROOT/'physical-ledger.json').read_text())['attempts']
    selected={}
    for task in TASKS:
        module=ROOT/'physical'/('reference-module-'+task)/'qualification.json'
        if not json.loads(module.read_text())['qualified']:
            raise ValueError('Module reference not qualified: '+task)
        names={'reference-integration-'+task,'calibration-integration-'+task}
        matches=[row for row in ledger if row['identity'] in names and row['status']=='passed']
        if len(matches)!=1:raise ValueError('Exactly one qualified integrated reference required: '+task)
        selected[task]=ROOT/'physical'/matches[0]['identity']
        qualified=json.loads((selected[task]/'qualification.json').read_text())
        if not qualified['integrated_95mhz_qualified'] or qualified['period_ns']!=10.526:
            raise ValueError('Reference does not qualify the frozen 95 MHz target: '+task)
        verified_integration(task)
    # Finish every independent physical/measurement audit before changing public task data.
    references={}
    for task,run in selected.items():
        history=ROOT/'checks/reference-calibration'/task
        output=history/f'audit-{1+len(list(history.glob("audit-*"))):03d}'
        evidence=audit(run,output)
        result=score(dict(function=True,integration=True),evidence['gds'],evidence['constraints'],
                     evidence['measurements'],evidence['measurements'])
        if not result['constraint_pass'] or abs(result['final_score']-50)>1e-9:
            raise ValueError('Reference evidence/measurement gate failed: '+task)
        references[task]=dict(run=str(run.relative_to(ROOT)),
            qualification_sha256=digest(run/'qualification.json'),
            audit=str((output/'audit.json').relative_to(ROOT)),
            audit_sha256=digest(output/'audit.json'),reference=evidence['measurements'])
    for variant in ('pilot','formal'):
        for task in TASKS:
            package=ROOT/'task-packages'/variant/task
            receipt=json.loads((package/'package.json').read_text())
            if not receipt['passed'] or receipt['frozen']:raise ValueError('Task is unqualified or already frozen')
            for name,sha in receipt['source_sha256'].items():
                if digest(package/name)!=sha:raise ValueError('Task changed after qualification: '+name)
    for variant in ('pilot','formal'):
        for task in TASKS:
            package=ROOT/'task-packages'/variant/task
            card=package/'agent/spec/scorecard.json';data=json.loads(card.read_text())
            data.update(calibrated=True,reference=references[task]['reference'],
                reference_score=50,maximum_score=100,
                note='Complete CPU integration reference; modeled postroute power, not silicon measurements')
            write_json(card,data)
            path=package/'agent/spec/task.json';data=json.loads(path.read_text())
            data['scope']='Assigned subsystem in a frozen, reference-qualified 95 MHz CPU integration'
            write_json(path,data)
            receipt=json.loads((package/'package.json').read_text())
            receipt.update(calibrated=True,frozen=True,reference_evidence=references[task],
                source_sha256={str(p.relative_to(package)):digest(p) for name in ('agent','grader')
                    for p in sorted((package/name).rglob('*')) if p.is_file()})
            write_json(package/'package.json',receipt)
            build=json.loads((package/'build.json').read_text())
            build.update(source_sha256=receipt['source_sha256'],status='qualified_calibrated_frozen')
            write_json(package/'build.json',build)
    result=dict(passed=True,references=references,packages=8,model_calls=0,physical_runs=0)
    write_json(ROOT/'checks/reference-calibration.json',result)
    return result


if __name__=='__main__':print(json.dumps(calibrate()))
