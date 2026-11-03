"""Reproduce the old open-parent assumption with a completed asynchronous call."""
import importlib.util
import json
import tempfile
from pathlib import Path

from capacity_tool_router import ToolRouter
from study_protocol import write_json

ROOT=Path(__file__).resolve().parents[1]
OLD=Path('/home/asic03/project/user37/CodeAChip_Experiments/WorkflowCapacity_20261021/revised-batch-01/scripts/capacity_tool_router.py')


def check():
    spec=importlib.util.spec_from_file_location('retained_old_router',OLD)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    rows=[]
    for label,cls in (('original',module.ToolRouter),('repair',ToolRouter)):
        with tempfile.TemporaryDirectory(prefix='async-owner-reproduction-') as directory:
            root=Path(directory);work=root/'work';work.mkdir()
            private=root/'private';(private/'sessions').mkdir(parents=True)
            transcript=private/'sessions/prefix-fixture.jsonl'
            opened=dict(type='response_item',payload=dict(type='custom_tool_call',call_id='origin'))
            transcript.write_text(json.dumps(opened)+'\n')
            with cls(work,root/'ledger',private=private,authorize=lambda:True,
                     admit_usage=lambda *args:None) as router:
                (work/'rtl/probe.sv').write_text('module probe;endmodule\n')
                event=dict(cwd=str(work),session_id='fixture',tool_use_id='child',tool_name='apply_patch',hook_event_name='PostToolUse')
                router.parents['child']=router.parent_witness(event);router.active='child'
                # The outer async exec has returned its cell handle; there is no open parent now.
                with transcript.open('a') as output:
                    output.write(json.dumps(dict(type='response_item',payload=dict(type='custom_tool_call_output',call_id='origin')))+'\n')
                try:router.handle(event)
                except ValueError as error:
                    rows.append(dict(implementation=label,error=str(error),active=router.active))
                    assert label=='original' and router.active=='child'
                else:
                    assert label=='repair' and router.active is None
                    receipt=json.loads((root/'ledger/snapshots/child/capture.json').read_text())
                    assert receipt['capture_phase']=='after_controlled_tool'
                    rows.append(dict(implementation=label,active=router.active,completion_fence_recorded=True))
    result=dict(passed=True,synthetic=True,model_calls=0,physical_runs=0,rows=rows)
    write_json(ROOT/'checks/async-owner-reproduction.json',result)
    return result


if __name__=='__main__':print(json.dumps(check()))
