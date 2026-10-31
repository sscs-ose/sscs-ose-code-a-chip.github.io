"""Exercise the entire corrective freeze in copied fixtures, never in the live campaign."""
from pathlib import Path
import importlib.util
import json
import shutil
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
CASE=ROOT.parents[1]/'CodeAChip_Submission/ISSCC27/submitted_notebooks/ChipNebula_CPU'
sys.path[:0]=[str(CASE/'runtime/src'),str(CASE/'scripts')]
from study_protocol import digest,write_json

spec=importlib.util.spec_from_file_location('freeze_fixture',ROOT/'freeze_measurement_correction.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


def reports(source,target):
    for name in ('summary.json','evaluation-v4.json'):
        if (source/name).exists():
            (target/name).parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source/name,target/name)
    for path in (source/'evidence').glob('orfs-work/logs/**/6_report.json'):
        destination=target/path.relative_to(source);destination.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,destination)
    shutil.copy2(source/'evidence/summary.json',target/'evidence/summary.json')


def run():
    with tempfile.TemporaryDirectory(prefix='chip-freeze-check-') as temporary:
        root=Path(temporary);experiment=root/'experiment';case=root/'case'
        (case/'scripts').mkdir(parents=True)
        bindings=json.loads((ROOT/'ppa/source-bindings.json').read_text())
        for name in (*bindings,'classify_study_failures.py'):
            shutil.copy2(CASE/'scripts'/name,case/'scripts'/name)
        shutil.copytree(ROOT/'source-correction',experiment/'source-correction')
        write_json(experiment/'ppa/source-bindings.json',bindings)
        shutil.copy2(ROOT/'protocol.json',experiment/'protocol.json')
        write_json(experiment/'advance-state.json',{'phase':'first_ppa_session_finished'})
        write_json(experiment/'checks/first-ppa-path-inspected.json',{'passed':True})
        shutil.copy2(ROOT/'checks/staged-measurement.json',experiment/'checks/staged-measurement.json')
        reports(ROOT/'baseline/mhz95-run03',experiment/'baseline/mhz95-run03')
        source=ROOT/'ppa/W1-3/candidates/01';target=experiment/'ppa/W1-3/candidates/01'
        reports(source/'physical',target/'physical');shutil.copy2(source/'evaluation.json',target/'evaluation.json')
        write_json(experiment/'ppa/W1-3/results/search-summary.json',{'finished':True,'physical_launches':1,
            'workflow_state':'paused','candidates':[json.loads((target/'evaluation.json').read_text())]})
        before=digest(target/'evaluation.json');module.ROOT=experiment;module.CASE=case
        module.freeze();module.freeze()
        staged=json.loads((experiment/'source-correction/manifest.json').read_text())
        for name,versions in staged['files'].items():
            assert digest(case/'scripts'/name)==versions['corrected_sha256']
            assert digest(experiment/'ppa/executed-helpers-v1'/name)==versions['original_sha256']
        assert digest(target/'evaluation.json')==before
        assert json.loads((experiment/'checks/first-ppa-path-approved.json').read_text())['passed']
        (experiment/'ppa/W2-3').mkdir()
        try:module.freeze()
        except ValueError:pass
        else:raise AssertionError('Changed helpers while another session exists')
    print('CORRECTIVE_FREEZE_SELF_CHECK_PASS: archive, patch hashes, unchanged data, idempotence and active-session rejection; zero model/EDA calls')


if __name__=='__main__':run()
