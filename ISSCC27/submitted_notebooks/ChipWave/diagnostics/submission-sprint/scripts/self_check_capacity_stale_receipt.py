"""A successful old receipt cannot validate a rejected later role launch."""
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
from chip_nebula.adapters.pool_manager import AgentPoolManager
from chip_nebula.models.task_manifest import AgentResult
from chip_nebula.taskgraph.static_cli import run_workflow
from chip_nebula.taskgraph.static_store import StaticTaskGraphStore
from capacity_context import ContextPool
from capacity_graph import freeze
from study_protocol import write_json


def check():
    with tempfile.TemporaryDirectory(prefix='capacity-stale-receipt-') as folder:
        root=Path(folder);project=root/'project';(project/'spec').mkdir(parents=True)
        (project/'spec/task.md').write_text('Synthetic role launch failure fixture.')
        database=freeze(project,'C3','gpt-6-luna');record=root/'runtime'
        pool=ContextPool(root/'private',root/'contexts.json','gpt-6-luna',runtime=dict(record=str(record),limit=1000,active_seconds=60))
        calls=[]
        def dispatch(instance,task,workspace,**kwargs):
            calls.append(task.stage)
            if len(calls)==1:
                (workspace/'rtl').mkdir(exist_ok=True);(workspace/'rtl/fixture.sv').write_text('module fixture;endmodule\n')
                write_json(record/'usage.json',dict(valid=True,actual_tokens=50,limit=1000))
                write_json(record/'invocations/0001/result.json',dict(reason='native_exit',exit_code=0))
                return AgentResult(success=True,execution_log='NEBULA_OUTPUT: {"rtl":{"module":"fixture"}}')
            assert len(calls)==2,'Rejected dispatch was retried'
            return AgentResult(success=False,execution_log='Launch gate closed before native invocation')
        with patch.object(AgentPoolManager,'dispatch',dispatch):
            status=run_workflow(project,database,'capacity',pool,workers=1)
        with StaticTaskGraphStore(database) as store:
            count=sum(len(store.list_attempts(t.id)) for t in store.list_tasks('capacity'))
        assert status.value=='paused' and len(calls)==2 and count==2
        assert json.loads((record/'trial-stop.json').read_text())['reason']=='runtime_infrastructure_error'
    result=dict(passed=True,synthetic=True,model_calls=0,physical_runs=0,
        scope='Actual C3 graph; second native launch fails before creating a receipt. Prior success cannot cause repeated launches.')
    write_json(Path(__file__).resolve().parents[1]/'checks/stale-invocation-receipt.json',result)
    return result


if __name__=='__main__':print(json.dumps(check()))
