"""Run actual public TaskGraphs and feedback with explicitly synthetic role replies."""
import json
import tempfile
from pathlib import Path

from chip_nebula.models.task_manifest import AgentResult
from chip_nebula.taskgraph.static_cli import run_workflow
from chip_nebula.taskgraph.static_store import StaticTaskGraphStore
from capacity_graph import freeze
from study_protocol import write_json


class Roles:
    def __init__(self):
        self.calls=[]
        self.rejected=False
    def dispatch(self,task,workspace,**kwargs):
        assert task.stage!="workflow-planning","Unexpected hidden planner"
        self.calls.append(dict(stage=task.stage,role=task.assigned_agent,workspace=str(workspace)))
        stage=task.stage
        if stage in ("implementation","revision","autonomous"):
            target=workspace/"rtl/fixture.sv";target.parent.mkdir(exist_ok=True)
            target.write_text("module capacity_fixture(input a,output y);assign y=a;endmodule\n")
            payload=dict(rtl=dict(module="capacity_fixture"))
        else:
            reject=stage=="verification" and not self.rejected
            self.rejected |= reject
            report=dict(subject="fixture",verdict="failed" if reject else "passed",
                        repair_summary="Synthetic failing-check evidence; revise once" if reject else "Synthetic fixture accepted")
            write_json(workspace/"reports"/stage/"report.json",report)
            payload=dict(report=report)
        return AgentResult(success=True,execution_log="NEBULA_OUTPUT: "+json.dumps(payload))
    def terminate(self,*args):
        pass


def check():
    results=[]
    with tempfile.TemporaryDirectory(prefix="capacity-graph-") as temp:
        for flow in ("C1","C2","C3","C6"):
            root=Path(temp)/flow
            (root/"spec").mkdir(parents=True)
            (root/"spec/task.md").write_text("Synthetic TaskGraph fixture; not a chip experiment.\n")
            database=freeze(root,flow,"gpt-6-luna")
            pool=Roles()
            status=run_workflow(root,database,"capacity",pool,workers=1)
            with StaticTaskGraphStore(database) as store:
                attempts={task.key:store.list_attempts(task.id) for task in store.list_tasks("capacity")}
                failures=[dict(task=key,diagnostics=a.diagnostics) for key,rows in attempts.items()
                          for a in rows if a.diagnostics.get("failure_reason")]
            assert status.value=="complete",(flow,status.value,failures)
            if flow!="C1":
                assert pool.rejected and len(attempts["implementation"])>=2
                assert len(attempts["verification"])>=2
            results.append(dict(workflow=flow,status=status.value,calls=pool.calls,
                                attempts={key:len(rows) for key,rows in attempts.items()},
                                synthetic_rejection=pool.rejected))
    report=dict(passed=True,model_calls=0,physical_runs=0,workflows=results,
        scope="Actual public Recipe, Artifact, TaskGraph and feedback; synthetic role content only")
    write_json(Path(__file__).resolve().parents[1]/"checks/taskgraph-feedback.json",report)
    return report


if __name__=="__main__":
    print(json.dumps(check()))
