"""An exhausted shared budget ends the actual public graph without retry dispatches."""
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
    with tempfile.TemporaryDirectory(prefix='capacity-workflow-stop-') as temp:
        root=Path(temp);project=root/'project';(project/'spec').mkdir(parents=True)
        (project/'spec/task.md').write_text('Synthetic resource-termination fixture.\n')
        database=freeze(project,'C3','gpt-6-luna')
        record=root/'runtime'
        pool=ContextPool(root/'private',root/'contexts.json','gpt-6-luna',
                         runtime=dict(record=str(record),limit=100,active_seconds=60))
        calls=[]
        def reply(instance,task,workspace,**kwargs):
            calls.append(task.stage)
            (workspace/'rtl').mkdir(exist_ok=True)
            (workspace/'rtl/fixture.sv').write_text('module fixture(input a,output y);assign y=a;endmodule\n')
            write_json(record/'usage.json',dict(valid=True,actual_tokens=100,limit=100))
            return AgentResult(success=True,execution_log='NEBULA_OUTPUT: {"rtl":{"module":"fixture"}}')
        with patch.object(AgentPoolManager,'dispatch',reply):
            status=run_workflow(project,database,'capacity',pool,workers=1)
        with StaticTaskGraphStore(database) as store:
            attempts=sum(len(store.list_attempts(task.id)) for task in store.list_tasks('capacity'))
            active=sum(store.active_attempt(task.id) is not None for task in store.list_tasks('capacity'))
        assert status.value=='paused' and calls==['implementation'] and attempts==1 and active==0, (status.value,calls,attempts,active)
        assert json.loads((record/'trial-stop.json').read_text())['reason']=='token_budget'
    report=dict(passed=True,model_calls=0,physical_runs=0,
        scope='Actual public C3 graph with one synthetic role response; shared budget prevents further dispatch and leaves no active attempt')
    write_json(Path(__file__).resolve().parents[1]/'checks/workflow-budget-stop.json',report)
    return report


if __name__=='__main__':
    print(json.dumps(check()))
