"""Exercise the real fixed graph with mocked AI decisions and physical measurements."""
from __future__ import annotations

import contextlib
import io
import json
import os
import tempfile
import sys
from pathlib import Path
from unittest.mock import patch

from chip_nebula.models.task_manifest import AgentResult
from chip_nebula.taskgraph.static_cli import run_workflow
from chip_nebula.taskgraph.static_store import StaticTaskGraphStore
from chip_nebula.taskgraph.tool_executor import DeterministicToolExecutor, ToolExecutionResult
import run_ppa_workflow_study as study
from study_protocol import BASELINE, preregistration, rule_candidate, write_json
from export_study_results import graph


class MockRoles:
    def __init__(self, root, reject_once):
        self.root = root; self.reject_once = reject_once
        self.proposals = 0; self.reviews = 0
        self.review_history_checks = 0

    def dispatch(self, task, workspace, **kwargs):
        if task.assigned_agent == 'ppa-proposer':
            self.proposals += 1
            metadata = json.loads((self.root/'session.json').read_text())
            config, reason = rule_candidate(study.history(self.root,metadata))
            document = {'configuration':config,'rationale':json.dumps(reason)}
            write_json(workspace/'proposal/candidate.json',document)
            payload = {'candidate':document}
        else:
            self.reviews += 1
            observations=len(list((self.root/'candidates').glob('*/evaluation.json')))
            if observations:
                histories=[]
                for path in (workspace/'.nebula_inputs').rglob('report.json'):
                    report=json.loads(path.read_text())
                    if report.get('history'):histories.append(report['history'])
                assert any(len(history)==observations+1 and history[-1]['candidate_index']==observations
                           for history in histories), 'Reviewer cannot inspect the current captured EDA history'
                self.review_history_checks += 1
            verdict = 'failed' if self.reject_once and self.reviews == 1 else 'passed'
            report = {'subject':'candidate','verdict':verdict,'repair_summary':'Test one review rejection; preserve the same owner.' if verdict=='failed' else 'none'}
            write_json(workspace/'reports/review.json',report)
            payload = {'report':report}
        return AgentResult(success=True,execution_log='NEBULA_OUTPUT: '+json.dumps(payload))

    def terminate(self, *args):
        pass


def run():
    rows = []
    with tempfile.TemporaryDirectory(prefix='chip-ppa-feedback-') as temporary:
        base=Path(temporary)
        protocol=base/'protocol.json';write_json(protocol,preregistration())
        baseline=base/'baseline.json';write_json(baseline,{'rank_eligible':True,'configuration':BASELINE,
            'candidate_index':0,'score':1.,'energy_ratio':1.,'cell_area_um2':100.,'failure_classes':[]})
        cases=[('W0',True,False),('W1',False,False),('W2',True,False),('W2',False,False),('W2',True,True)]
        for workflow,last_passes,preflight_fails in cases:
            root=base/(workflow+str(last_passes)+str(preflight_fails));root.mkdir();(root/'results').mkdir();(root/'candidates').mkdir()
            metadata={'job':{'workflow':workflow,'id':workflow+'-test','repetition':0},'baseline':str(baseline),
                      'baseline_sha256':study.digest(baseline),'protocol':str(protocol),'rtl_source':'TEST_ONLY_NO_EDA'}
            write_json(root/'session.json',metadata);study.prepare(root,metadata)

            def fake_physical(output, source, config, period):
                assert period==10526 and str(source)=='TEST_ONLY_NO_EDA'
                if preflight_fails and int(output.parent.name)==1:
                    output.mkdir()
                    raise RuntimeError('Physical environment not ready: synthetic KLayout version-probe failure')
                output.mkdir();write_json(output/'fixture.json',config)

            def fake_measure(output, source):
                index=int(output.parent.name)
                eligible=index==1 or (index==3 and last_passes)
                result={'rank_eligible':eligible,'physical_qualified':eligible,
                        'configuration':json.loads((output/'fixture.json').read_text()),
                        'cell_area_um2':100.,'physical_wall_seconds':1.,'postprocess_wall_seconds':1.,
                        'failure_classes':[] if eligible else ['electrical']}
                if eligible:result.update(score=1.-index/10,energy_ratio=1.-index/10)
                return result

            def tools(_executor, workspace, commands):
                command=list(commands)[0]
                action=command.command.rsplit(' ',1)[-1]
                assert action in ('propose','evaluate','finalize')
                stream=io.StringIO()
                with contextlib.redirect_stdout(stream):study.tool_action(action,workspace)
                if preflight_fails and action=='evaluate':
                    before=len(list((root/'candidates').glob('*/launch.json')))
                    with contextlib.redirect_stdout(io.StringIO()):study.tool_action(action,workspace)
                    assert len(list((root/'candidates').glob('*/launch.json')))==before
                return ToolExecutionResult('succeeded','passed',(),stream.getvalue())

            pool=MockRoles(root,workflow=='W2')
            with patch.dict(os.environ,{'CHIP_PPA_SESSION':str(root),'CHIP_STUDY_CASE':str(study.CASE),'CHIP_STUDY_PYTHON':sys.executable}), \
                 patch.object(study,'run_physical',fake_physical), \
                 patch.object(study,'evaluate_measurement',fake_measure), \
                 patch.object(DeterministicToolExecutor,'execute',tools):
                state=run_workflow(root/'project',root/'project/.chip_nebula/shared/memory/taskgraph-v2.db','ppa-search',pool,workers=1)
                summary=study.summarize_session(root,metadata)
            if summary['physical_launches']!=3 or len(summary['candidates'])!=3:
                with StaticTaskGraphStore(root/'project/.chip_nebula/shared/memory/taskgraph-v2.db') as store:
                    failures=[{'task':task.key,'reason':attempt.diagnostics.get('failure_reason'),
                               'log':attempt.diagnostics.get('execution_log','')[-1000:],
                               'gates':attempt.diagnostics.get('gate_reports')} for task in store.list_tasks('ppa-search')
                              for attempt in store.list_attempts(task.id)]
                raise AssertionError(json.dumps({'workflow':workflow,'state':state.value,'summary':summary,'attempts':failures}))
            assert summary['best_qualified_candidate']['candidate_index']==(3 if last_passes else 1)
            if preflight_fails:
                first=summary['candidates'][0]
                assert not first['rank_eligible'] and first['failure_classes']==['infrastructure','preflight']
                assert first['cell_area_um2'] is None and not first['energy_j']
                assert 'KLayout' in first['preparation_error']
            assert state.value==('complete' if last_passes else 'paused')
            if workflow=='W0':assert pool.proposals==0 and pool.reviews==0
            if workflow=='W2':
                assert pool.reviews==4 and pool.proposals==4
                assert pool.review_history_checks==2
            with StaticTaskGraphStore(root/'project/.chip_nebula/shared/memory/taskgraph-v2.db') as store:
                assert store.task_state('ppa-search:finalizer').value=='satisfied'
                assert len(store.list_attempts('ppa-search:evaluator'))==3
            exported=root/'exported-taskgraph.json';graph(root/'project','ppa-search',exported)
            record=json.loads(exported.read_text());work={item['id']:item for item in record['work_items']}
            artifacts={item['id']:item for item in record['artifacts']}
            assert all(task['frozen'] and task['brief'] for task in record['tasks'])
            assert set(record['deliveries'])=={task['id'] for task in record['tasks']}
            assert all(delivery['artifact_id'] in artifacts for outputs in record['deliveries'].values()
                       for delivery in outputs.values())
            assert all(identity in work for attempt in record['attempts'] for identity in attempt['work_item_ids'])
            if workflow=='W2':
                histories=[artifacts[identity]['payload'].get('history') for attempt in record['attempts']
                    if attempt['task_id']=='ppa-search:reviewer' for wid in attempt['work_item_ids']
                    for identity in work[wid]['evidence_artifact_ids']]
                assert any(history and len(history)>=2 for history in histories), 'Export lost the reviewer feedback history'
            if workflow=='W2' and last_passes:
                with patch.object(StaticTaskGraphStore,'work_items',return_value=[]):
                    try:graph(root/'project','ppa-search',root/'incomplete-export.json')
                    except ValueError:pass
                    else:raise AssertionError('Export accepted missing captured work records')
                assert not (root/'incomplete-export.json').exists()
                with patch.object(StaticTaskGraphStore,'list_artifacts',return_value=[]):
                    try:graph(root/'project','ppa-search',root/'incomplete-export.json')
                    except ValueError:pass
                    else:raise AssertionError('Export accepted missing input/evidence artifacts')
                assert not (root/'incomplete-export.json').exists()
            rows.append({'workflow':workflow,'last_candidate_passes':last_passes,'state':state.value,
                         'synthetic_preflight_failure':preflight_fails,
                         'physical_launches':summary['physical_launches'],'role_proposals':pool.proposals,
                         'role_reviews':pool.reviews,'review_history_checks':pool.review_history_checks,
                         'best_candidate':summary['best_qualified_candidate']['candidate_index']})
    print(json.dumps({'passed':True,'cases':rows,'actual_model_calls':0,'actual_physical_calls':0,
                      'scope':'Real TaskGraph, SQLite, immutable delivery bindings, gates, owner feedback and terminal routes; synthetic decisions and measurements'},indent=2))


if __name__=='__main__':run()
