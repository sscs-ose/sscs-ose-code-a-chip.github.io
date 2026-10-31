"""Install a tested report-classification correction only at a stopped session boundary."""
from pathlib import Path
import datetime
import json
import shutil
import sys

ROOT=Path(__file__).resolve().parent
CASE=ROOT.parents[1]/'CodeAChip_Submission/ISSCC27/submitted_notebooks/ChipNebula_CPU'
sys.path[:0]=[str(CASE/'runtime/src'),str(CASE/'scripts')]
from classify_study_failures import classify,read_reports
from study_protocol import digest,write_json


def load(path):
    return json.loads(path.read_text())


def reports(physical):
    raw,native,errors=read_reports(physical/'evidence')
    row=load(physical/'summary.json')
    native_pass=(not row['timed_out'] and row['exit_code']==0 and row['task_state']=='satisfied'
                 and native.get('status') in ('passed','physical_passed'))
    reconstructed=dict(row,physical_qualified=native_pass,failure_classes=errors)
    return row,reconstructed,raw,native


def freeze():
    if load(ROOT/'advance-state.json')['phase']!='first_ppa_session_finished':
        raise ValueError('The first session must terminate before helper changes')
    inspected=ROOT/'checks/first-ppa-path-inspected.json'
    if not load(inspected)['passed']:raise ValueError('Actual report feedback was not checked')
    first=load(ROOT/'ppa/W1-3/results/search-summary.json')
    if not first['finished'] or first['physical_launches']>3 or str(first.get('workflow_state','')).startswith('inspect-'):
        raise ValueError('Inspect the preserved first-session result')
    for job in load(ROOT/'protocol.json')['ppa']['sessions']:
        if job['id']!='W1-3' and (ROOT/'ppa'/job['id']).exists():
            raise ValueError('Another session already exists; do not switch helpers during execution')
    specification=load(ROOT/'source-correction/manifest.json')
    proof=load(ROOT/'checks/staged-measurement.json')
    expected={name:version['corrected_sha256'] for name,version in specification['files'].items()}
    expected['classify_study_failures.py']=specification['classifier_sha256']
    if not proof['passed'] or proof['checked_code_sha256']!=expected:
        raise ValueError('Staged rejection tests do not cover the current correction')
    if digest(CASE/'scripts/classify_study_failures.py')!=specification['classifier_sha256']:
        raise ValueError('Tested classifier changed')
    observations=[]
    baseline=ROOT/'baseline/mhz95-run03'
    physical,reconstructed,raw,native=reports(baseline)
    assert not classify(reconstructed,raw,native) and load(baseline/'evaluation-v4.json')['rank_eligible']
    for path in sorted((ROOT/'ppa/W1-3/candidates').glob('*/evaluation.json')):
        old=load(path);physical,reconstructed,raw,native=reports(path.parent/'physical')
        corrected=classify(reconstructed,raw,native)
        if physical['physical_qualified'] and not old['rank_eligible']:
            raise ValueError('Resolve incomplete qualified-candidate measurements before continuing')
        if set(corrected)!=set(old['failure_classes']):
            raise ValueError('Correction changes an observed first-session report; inspect instead of silently adopting')
        qualified=reconstructed['physical_qualified'] and not corrected
        if qualified!=old['rank_eligible']:raise ValueError('Observed qualification would change')
        observations.append({'candidate':path.parent.name,'failure_classes':corrected,'rank_eligible':qualified,
                             'original_evaluation_sha256':digest(path)})
    if len(observations)!=len(first['candidates']):raise ValueError('Missing completed candidate reports')
    bindings=ROOT/'ppa/source-bindings.json';original=ROOT/'ppa/source-bindings-v1.json'
    if not original.exists():shutil.copy2(bindings,original)
    old_bindings=load(original);archive=ROOT/'ppa/executed-helpers-v1';archive.mkdir(exist_ok=True)
    for name,versions in specification['files'].items():
        target=CASE/'scripts'/name;staged=ROOT/'source-correction'/name
        if digest(staged)!=versions['corrected_sha256']:raise ValueError('Staged correction changed: '+name)
        if digest(target) not in (versions['original_sha256'],versions['corrected_sha256']):
            raise ValueError('Unexpected live helper revision: '+name)
    for name,expected in old_bindings.items():
        preserved=archive/name
        if not preserved.exists():
            source=ROOT/'source-correction'/('original-'+name) if name in specification['files'] else CASE/'scripts'/name
            if digest(source)!=expected:raise ValueError('Original executed helper changed: '+name)
            shutil.copy2(source,preserved)
        if digest(preserved)!=expected:raise ValueError('Executed helper archive changed: '+name)
    for name,versions in specification['files'].items():
        target=CASE/'scripts'/name;staged=ROOT/'source-correction'/name
        if digest(target)==versions['original_sha256']:
            temporary=target.with_suffix('.next');temporary.write_bytes(staged.read_bytes());temporary.replace(target)
    revised={name:digest(CASE/'scripts'/name) for name in old_bindings}
    revised['classify_study_failures.py']=specification['classifier_sha256']
    write_json(bindings,revised)
    record={'installed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'reason':specification['scope'],'original_bindings':'source-bindings-v1.json',
        'original_helpers':'executed-helpers-v1/','corrected_bindings':'source-bindings.json',
        'completed_observations_unchanged':observations,'common_baseline_unchanged':True,
        'staged_test_proof_sha256':digest(ROOT/'checks/staged-measurement.json'),
        'earlier_reports_rewritten':False,'models_or_workflows_changed':False,'extra_physical_runs':0}
    write_json(ROOT/'ppa/measurement-source-correction.json',record)
    write_json(ROOT/'ppa/W1-3/executed-source-binding.json',{'bindings':'../source-bindings-v1.json',
        'bindings_sha256':digest(original),'scope':'Verified executed source set for the first session; original session metadata and reports retained'})
    write_json(ROOT/'checks/first-ppa-path-approved.json',{'passed':True,
        'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'actual_feedback_inspection_sha256':digest(inspected),
        'correction_record_sha256':digest(ROOT/'ppa/measurement-source-correction.json'),
        'scope':'Executing-agent deterministic checks; not independent competition review'})
    print('CORRECTIVE_FREEZE_COMPLETE: completed observations preserved; remaining session boundary released')


if __name__=='__main__':freeze()
