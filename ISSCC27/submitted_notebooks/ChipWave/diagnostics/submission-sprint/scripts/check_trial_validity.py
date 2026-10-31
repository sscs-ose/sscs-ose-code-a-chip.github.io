"""Exercise real trial finalization with synthetic, explicitly unscored backends."""
import json
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

REV=Path(__file__).resolve().parent
ROOT=REV.parent
sys.path.append(str(ROOT/'scripts'))
import run_capacity_trial as trial
from capacity_meter import TokenLedger
from capacity_results import observation
from capacity_protocol import protocol
from study_protocol import write_json


def check():
    rows=[]
    scenarios=[('normal','native_exit',0,True,None,True),
               ('token_stop','token_budget',-15,True,None,True),
               ('time_stop','active_time_budget',-15,True,None,True),
               ('unexpected_exit','native_exit',-15,True,None,False),
               ('missing_receipt',None,None,True,None,False),
               ('missing_exit_code','token_budget',None,True,None,False),
               ('invalid_measurement','measurement_invalid',-15,False,None,False),
               ('manual_intervention','native_exit',0,True,[dict(reason='fixture intervention',recorded_at='2026-10-21T00:00:00Z')],False),
               ('malformed_interventions','native_exit',0,True,{},False)]
    with tempfile.TemporaryDirectory(prefix='capacity-trial-validity-') as temporary:
        root=Path(temporary);original=protocol()['pilot_jobs'][0]
        write_json(root/'campaign-freeze.json',{})
        write_json(root/'physical-ledger.json',dict(attempts=[]))
        package=root/'task-packages/pilot'/original['task']
        write_json(package/'package.json',{})
        write_json(package/'agent/spec/scorecard.json',dict(reference={}))
        for name,reason,code,measured,interventions,expected in scenarios:
            job=dict(original,id=name)
            def native(config,prompt):
                runtime=Path(config['record']);ledger=TokenLedger()
                ledger.record('fixture','response',dict(input_tokens=40,cached_input_tokens=10,
                    output_tokens=10,reasoning_output_tokens=5,total_tokens=50))
                write_json(runtime/'usage.json',ledger.state)
                write_json(runtime/'invocations/0001/request.json',dict(role=None,stage=None))
                control=dict(reason=reason or 'native_exit',exit_code=code,measurement_valid=measured,
                    invocation_tokens=50,invocation_active_seconds=1,invocation_physical_seconds=0)
                if reason is not None:write_json(runtime/'invocations/0001/result.json',control)
                if interventions is not None:write_json(runtime.parent/'interventions.json',interventions)
                return control,runtime/'stdout'
            def grader(command,**kwargs):
                request=json.loads(Path(command[command.index('--request')+1]).read_text())
                row=dict(budget=request['budget'],measurement_valid=True,functional_pass=True,
                    gds_pass=True,joint_pass=True,constraint_pass=True,final_score=50,
                    source_tokens=50,errors=[],snapshot_id='fixture-only')
                write_json(Path(request['output'])/'score.json',row)
                return SimpleNamespace(returncode=0)
            with patch.object(trial,'ROOT',root),patch.object(trial,'admit_trial',return_value=job),\
                 patch.object(trial,'prepare',return_value=None),patch.object(trial,'run_native',side_effect=native),\
                 patch.object(trial,'run_group',side_effect=grader),\
                 patch.object(trial,'private_context',return_value=root/'private'/name):
                result=trial._run('pilot',name)
            assert result['measurement_valid'] is expected,(name,result)
            assert result['usage']['actual_tokens']==50
            assert result['final_score']==50,'Diagnostic measurement was overwritten'
            assert observation(result)['final_score']==(50 if expected else 0)
            assert result['credited_outcomes']==observation(result)
            for point in result['checkpoints']:
                assert point['measurement_valid'] is expected
                assert observation(point)['final_score']==(50 if expected else 0)
            if name=='manual_intervention':assert result['manual_interventions']==1
            if name=='malformed_interventions':assert result['manual_interventions'] is None
            rows.append(dict(case=name,comparison_valid=result['measurement_valid'],
                raw_score=result['final_score'],credited_score=observation(result)['final_score'],
                recorded_tokens=result['usage']['actual_tokens'],manual_interventions=result['manual_interventions']))
    result=dict(passed=True,model_calls=0,physical_runs=0,rows=rows,
        scope='Synthetic backend outcomes test actual revised collector and unchanged observation logic; no design or hardware results.')
    write_json(ROOT/'checks/trial-validity.json',result)
    return result

if __name__=='__main__':print(json.dumps(check()))
