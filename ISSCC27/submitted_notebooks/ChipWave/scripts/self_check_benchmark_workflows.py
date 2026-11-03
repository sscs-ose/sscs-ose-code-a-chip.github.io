"""Run actual F0/F1/F2 TaskGraphs with synthetic roles/EDA; no model or physical calls."""
import contextlib
import argparse
import io
import json
import os
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

from chip_nebula.models.task_manifest import AgentResult
from chip_nebula.taskgraph.static_cli import run_workflow
from chip_nebula.taskgraph.static_store import StaticTaskGraphStore
from chip_nebula.taskgraph.tool_executor import DeterministicToolExecutor,ToolExecutionResult
import run_benchmark_ppa as study
from study_protocol import BASELINE,write_json

NO_ACTION=dict(operand_isolation=False,reduce_width=False)


class Roles:
    def __init__(self,root,reject_once):
        self.root=root;self.reject_once=reject_once;self.proposals=0;self.reviews=0;self.seen_history=[]
    def dispatch(self,task,workspace,**kwargs):
        if task.assigned_agent=='ppa-optimizer':
            history=study.observations(self.root,json.loads((self.root/'session.json').read_text()))
            index=len(history)
            config=dict(BASELINE,repair_margin=(index-1)*10,abc_area=1)
            document=dict(configuration=config,rtl_actions=NO_ACTION,rationale='Synthetic self-check proposal')
            write_json(workspace/'proposal/candidate.json',document)
            self.proposals+=1;payload=dict(candidate=document)
        else:
            self.reviews+=1
            captured=[]
            for path in (workspace/'.nebula_inputs').rglob('artifact.json'):
                a=json.loads(path.read_text())
                if a['type']=='ppa.route.report':captured.extend(a['payload']['history'])
            assert captured,'Reviewer lacks current captured report history'
            self.seen_history.append(max(row.get('candidate_index',0) for row in captured))
            report=dict(subject='candidate',verdict='failed' if self.reject_once and self.reviews==1 else 'passed',
                        repair_summary='One synthetic review repair' if self.reviews==1 else 'Actual captured evidence inspected')
            write_json(workspace/'reports/review.json',report);payload=dict(report=report)
        return AgentResult(success=True,execution_log='NEBULA_OUTPUT: '+json.dumps(payload))
    def terminate(self,*args):pass


def main(output=None):
    if output is not None and output.exists():
        raise ValueError('Previous lesson results are preserved; choose a new output path')
    rows=[]
    with tempfile.TemporaryDirectory(prefix='chip-workflow-branches-') as temp:
        campaign=Path(temp)
        limits=dict(reference=6,demonstration=3,common_baseline=1,ppa=27,high_frequency=4,preformal_calibration=3,absolute_total=44)
        protocol=dict(ppa=dict(allowed_rtl_actions=[NO_ACTION]))
        write_json(campaign/'protocol.json',protocol)
        physical_manifest=dict(period_ps=10526,sdc_sha256='synthetic-sdc',threads=2)
        baseline=campaign/'baseline.json'
        write_json(baseline,dict(rank_eligible=True,configuration=BASELINE,rtl_actions=NO_ACTION,candidate_index=0,
            score=1.,energy_ratio=1.,cell_area_um2=100.,energy_j=dict(DOT64=1.,GEMM8=1.,CONV3=1.),
            physical_manifest=physical_manifest))
        for flow in ('F0','F1','F2'):
            for pattern in ((True,True,False),(True,False,True)):
                write_json(campaign/'launch-ledger.json',dict(limits=limits,launches=[]))
                root=campaign/(flow+''.join(str(int(v)) for v in pattern));root.mkdir();(root/'results').mkdir();(root/'candidates').mkdir()
                meta=dict(job=dict(id=root.name,workflow=flow),campaign=str(campaign),baseline=str(baseline),
                    baseline_sha256=study.digest(baseline),protocol=str(campaign/'protocol.json'),started_monotonic=time.monotonic())
                write_json(root/'session.json',meta);study.prepare(root,meta)
                calls=[]; routes=[]
                def physical(output,source,configuration,period):
                    assert period==10526
                    output.mkdir()
                    write_json(output/'fixture.json',dict(configuration=configuration,source=str(source)))
                    calls.append(int(output.parent.name))
                def measure(output):
                    data=json.loads((output/'fixture.json').read_text());index=int(output.parent.name)
                    source=Path(data['source'])
                    manifest=dict(physical_manifest,rtl_sha256=json.loads((source/'selected-delivery.json').read_text())['exported_source_sha256'])
                    row=dict(rank_eligible=pattern[index-1],physical_qualified=pattern[index-1],physical_manifest=manifest,
                        cell_area_um2=100.-index,energy_j=dict(DOT64=1.,GEMM8=1.,CONV3=1.),failure_classes=[] if pattern[index-1] else ['electrical'])
                    return row
                def tools(_executor,workspace,commands):
                    command=list(commands)[0].command
                    action=command.rsplit(' ',1)[-1]
                    assert action in ('route','reviewed','direct','finalize')
                    if action in ('reviewed','direct'):
                        routes.append(action)
                    out=io.StringIO()
                    with contextlib.redirect_stdout(out):study.tool_action(action,workspace)
                    if action in ('reviewed','direct'):
                        before=list(calls)
                        with contextlib.redirect_stdout(io.StringIO()):study.tool_action(action,workspace)
                        assert calls==before, 'Publication replay launched duplicate physical work'
                    return ToolExecutionResult('succeeded','passed',(),out.getvalue())
                roles=Roles(root,flow!='F0')
                with patch.dict(os.environ,dict(CHIP_BENCHMARK_PPA_SESSION=str(root),CHIP_STUDY_CASE=str(study.CASE),CHIP_STUDY_PYTHON=__import__('sys').executable)), \
                     patch.object(study,'run_physical',physical),patch.object(study,'evaluate',measure), \
                     patch.object(DeterministicToolExecutor,'execute',tools):
                    status=run_workflow(root/'project',root/'project/.chip_nebula/shared/memory/taskgraph-v2.db','workflow-ppa',roles,workers=1)
                result=study.summarize(root,meta)
                if calls!=[1,2,3]:
                    with StaticTaskGraphStore(root/'project/.chip_nebula/shared/memory/taskgraph-v2.db') as store:
                        errors=[dict(task=t.key,status=store.task_state(t.id).value,attempts=[dict(reason=a.diagnostics.get('failure_reason'),log=a.diagnostics.get('execution_log','')[-1500:]) for a in store.list_attempts(t.id)]) for t in store.list_tasks('workflow-ppa')]
                    raise AssertionError(json.dumps(dict(flow=flow,pattern=pattern,calls=calls,errors=errors)))
                expected=0 if flow=='F0' else 3 if flow=='F1' else 1+int(not pattern[0])+int(not pattern[1])
                assert roles.reviews==expected+(flow!='F0'),(flow,roles.reviews,expected)
                assert result['accepted_candidates']==3 and result['unused_candidate_slots']==0
                counts=study.native_counts(root)
                assert counts['review_rejections']==int(flow!='F0')
                assert counts['review_feedback_optimizer_dispatches']>=int(flow!='F0')
                assert routes.count('reviewed')==expected
                assert routes.count('direct')==3-expected
                assert result['best_new_qualified']['candidate_index']==(3 if pattern[2] else 2)
                with StaticTaskGraphStore(root/'project/.chip_nebula/shared/memory/taskgraph-v2.db') as store:
                    assert store.task_state('workflow-ppa:finalizer').value=='satisfied'
                rows.append(dict(workflow=flow,qualified_pattern=pattern,physical_evaluations=calls,reviews=roles.reviews,
                                 reviewer_history=roles.seen_history,status=status.value,best_new=result['best_new_qualified']['candidate_index'],
                                 candidate_paths=routes,native_counts=counts))
    result=dict(passed=True,cases=rows,actual_model_calls=0,actual_physical_calls=0,
        scope='Teaching mechanism test: real TaskGraph, synthetic role responses and physical outcomes; not a chip-design experiment')
    if output is not None:write_json(output,result)
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,help='Save the account-free branch demonstration as JSON')
    main(parser.parse_args().output)
