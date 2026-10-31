"""Exercise all-or-nothing prerequisite admission with explicit synthetic reference evidence."""
import json
import tempfile
import os
import sys
import subprocess
from pathlib import Path
from unittest.mock import patch

import calibrate_capacity_packages as calibration
import freeze_capacity_campaign as campaign
from capacity_protocol import TASKS,GDS_GATES,CONSTRAINT_GATES,protocol
from study_protocol import digest,write_json
from study_portability import case_root


def fixture(root):
    rows=[]
    for task in TASKS:
        for kind in ('module','integration'):
            identity='reference-'+kind+'-'+task;folder=root/'physical'/identity
            write_json(folder/'qualification.json',dict(qualified=True,integrated_95mhz_qualified=kind=='integration',
                period_ns=10.526 if kind=='integration' else 100))
            rows.append(dict(identity=identity,status='passed'))
        source=root/'integration'/task;source.mkdir(parents=True)
        (source/'source.txt').write_text('Frozen integration fixture')
        write_json(source/'freeze-draft.json',dict(source_sha256={'source.txt':digest(source/'source.txt')}))
        write_json(source/'qualification/qualification.json',dict(passed=True))
        for variant in ('pilot','formal'):
            package=root/'task-packages'/variant/task
            write_json(package/'agent/spec/scorecard.json',dict(calibrated=False))
            write_json(package/'agent/spec/task.json',dict(task=task))
            write_json(package/'build.json',{})
            write_json(package/'package.json',dict(passed=True,calibrated=False,frozen=False,
                source_sha256={str(p.relative_to(package)):digest(p) for p in (package/'agent').rglob('*') if p.is_file()}))
    write_json(root/'physical-ledger.json',dict(attempts=rows))
    write_json(root/'protocol.json',protocol())


# Inherited-debit failures have their own explicit ledger tests.
@patch('import_capacity_prior.validate_inherited', return_value={})
def check(_inherited):
    with tempfile.TemporaryDirectory(prefix='capacity-freeze-check-') as temp:
        root=Path(temp);fixture(root)
        relocated=root/'public-package'
        for name in ('runtime/src/chip_nebula/__init__.py','toolchain/orfs/source-manifest.json'):
            target=relocated/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_text('{}')
        with patch.dict(os.environ):
            os.environ.pop('CHIPNEBULA_CASE_ROOT',None)
            assert case_root(relocated/'experiments/capacity')==relocated
        env=dict(os.environ,PYTHONPATH=str(Path(__file__).parent),CHIPNEBULA_CASE_ROOT=str(relocated),
            CHIPNEBULA_YOSYS_ROOT=str(relocated/'yosys'),CHIPNEBULA_ABC_ROOT=str(relocated/'abc'))
        code='from capacity_integration_physical import CASE;from capacity_candidate import YOSYS_ROOT,ABC_ROOT;import json;print(json.dumps([str(CASE),str(YOSYS_ROOT),str(ABC_ROOT)]))'
        actual=json.loads(subprocess.check_output([sys.executable,'-c',code],env=env,text=True,timeout=30))
        assert actual==[str(relocated),str(relocated/'yosys'),str(relocated/'abc')]
        def integration(task):
            source=root/'integration'/task
            return source,json.loads((source/'freeze-draft.json').read_text())
        values=dict(cell_area=100,die_area=200,workloads=dict(test=dict(throughput=10,latency=2,power=3,energy=.3)))
        def audit(run,out):
            data=dict(gds=dict.fromkeys(GDS_GATES,True),constraints=dict.fromkeys(CONSTRAINT_GATES,True),
                      measurements=values,scope='Synthetic freeze-transaction fixture; no physical evidence')
            write_json(out/'audit.json',data);return data
        with patch.object(calibration,'ROOT',root),patch.object(calibration,'verified_integration',side_effect=integration),\
             patch.object(calibration,'audit',side_effect=audit):
            ledger=root/'physical-ledger.json';original=json.loads(ledger.read_text())
            broken=json.loads(ledger.read_text());broken['attempts'][-1]['status']='failed';write_json(ledger,broken)
            card=root/'task-packages/pilot/A1/agent/spec/scorecard.json';before=digest(card)
            try:calibration.calibrate()
            except ValueError:pass
            else:raise AssertionError('Missing integrated reference accepted')
            assert digest(card)==before and not (root/'checks/reference-calibration').exists()
            write_json(ledger,original)
            result=calibration.calibrate();assert result['passed'] and result['packages']==8
            assert json.loads(card.read_text())['reference_score']==50
            for variant in ('pilot','formal'):
                for task in TASKS:
                    package=root/'task-packages'/variant/task;receipt=json.loads((package/'package.json').read_text())
                    assert receipt['calibrated'] and receipt['frozen']
                    assert all(digest(package/name)==sha for name,sha in receipt['source_sha256'].items())
        for name in campaign.CHECKS:
            path=root/'checks'/(name+'.json')
            if not path.exists():write_json(path,dict(passed=True,synthetic=True))
        for name in campaign.LIVE:write_json(root/'checks'/name/'result.json',dict(passed=True,synthetic=True))
        for model in campaign.MODELS.values():
            write_json(root/'checks'/('connectivity-'+model.replace('.','-'))/'result.json',
                dict(connectivity_pass=True,observed_contexts=[dict(model=model,effort='high')],synthetic=True))
        (root/'scripts').mkdir();(root/'scripts/fixture.py').write_text('# synthetic\n')
        (root/'scripts/capacity_notebook_cells.py').write_text('# Manuscript fixture\n')
        with patch.object(campaign,'ROOT',root),patch.object(campaign,'verified_integration',side_effect=integration),\
             patch.object(campaign,'external_sources',return_value=dict(external_files={},tool_paths={},container_images={},native_binary='fixture')):
            key=root/'checks/tool-router.json';write_json(key,dict(passed=False))
            try:campaign.freeze()
            except ValueError:pass
            else:raise AssertionError('Failed runtime qualification accepted')
            assert not (root/'campaign-freeze.json').exists()
            assert not json.loads((root/'protocol.json').read_text())['pilot_launch_allowed']
            write_json(key,dict(passed=True,synthetic=True))
            assert campaign.freeze()['pilot_launch_allowed']
            frozen=json.loads((root/'campaign-freeze.json').read_text())
            assert 'scripts/fixture.py' in frozen['files']
            assert 'scripts/capacity_notebook_cells.py' not in frozen['files']
            (root/'scripts/capacity_notebook_cells.py').write_text('# Revised wording\n')
            assert all(digest(root/name)==sha for name,sha in frozen['files'].items())
            try:campaign.freeze()
            except ValueError:pass
            else:raise AssertionError('Existing freeze overwritten')
    report=dict(passed=True,model_calls=0,physical_runs=0,
        scope='Synthetic evidence tests freeze mechanics only; real reference qualification remains separate',
        checks=['incomplete references cannot modify scorecards','eight packages share reference calibration and source hashes',
                'failed runtime gate prevents launch','freeze binds sources and cannot be overwritten',
                'manuscript wording is excluded while runtime sources remain frozen'])
    write_json(Path(__file__).resolve().parents[1]/'checks/campaign-freeze.json',report)
    source=Path(__file__).resolve().parent
    write_json(source.parent/'checks/portable-paths.json',dict(passed=True,model_calls=0,physical_runs=0,
        scope='Relocated package and explicit tool-root discovery; not a complete archive reproduction',
        source_sha256={name:digest(source/name) for name in
            ('study_portability.py','capacity_candidate.py','capacity_integration_physical.py','self_check_capacity_freeze.py')}))
    return report


if __name__=='__main__':print(json.dumps(check()))
