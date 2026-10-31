"""A hook failure cannot be returned as a valid native design invocation."""
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from capacity_live_usage import LiveUsage
from capacity_runtime import run
from capacity_tool_router import ToolRouter
from study_protocol import write_json

ROOT=Path(__file__).resolve().parents[1]


def check():
    rows=[]
    with tempfile.TemporaryDirectory(prefix='lifecycle-validity-') as folder:
        for fault in ('router_error','unfinished_patch'):
            base=Path(folder)/fault;work=base/'work';work.mkdir(parents=True)
            private=base/'private';private.mkdir();(private/'config.toml').write_text('')
            record=base/'runtime'
            config=dict(record=str(record),private=str(private),project=str(work),workspace=str(work),
                        model='gpt-6-luna',limit=1000,active_seconds=60,scored=False)
            enter=ToolRouter.__enter__
            def entered(router):
                if fault=='unfinished_patch':router.active='unfinished'
                return enter(router)
            def wait(observer,process,**kwargs):
                process.wait(timeout=5)
                if fault=='router_error':write_json(record/'tools/router-error.json',dict(error='Synthetic post-tool failure'))
                return dict(reason='native_exit',exit_code=0,wall_seconds=.05,**observer.ledger.summary())
            with patch('capacity_runtime.prepare_credentials'),\
                 patch('capacity_runtime.sandbox_command',return_value=['/bin/sleep','.05']),\
                 patch.object(ToolRouter,'__enter__',entered),patch.object(LiveUsage,'wait',wait):
                result,_=run(config,'fixture')
            assert result['exit_code']==0 and not result['passed'] and not result['measurement_valid'], result
            assert result['reason']=='source_association_invalid'
            rows.append(dict(fault=fault,passed=True,reason=result['reason']))
    report=dict(passed=True,synthetic=True,model_calls=0,physical_runs=0,rows=rows)
    write_json(ROOT/'checks/lifecycle-errors.json',report)
    return report


if __name__=='__main__':print(json.dumps(check()))
