"""Replay actual retained preflight usage without exporting account metadata."""
import copy
import json
import tempfile
from pathlib import Path

from capacity_accounting_replay import export,replay,public_payload
from study_portability import private_context
from study_protocol import write_json

ROOT=Path(__file__).resolve().parents[1]


def check():
    rows=[]
    cases=(('live-taskgraph-c3-v2','capacity-live-taskgraph-c3-v2'),
           ('native-compaction-stop-probe','capacity-compaction-stop'),
           ('native-eda-admission','capacity-eda-admission'))
    with tempfile.TemporaryDirectory(prefix='capacity-accounting-replay-') as temporary:
        folder=Path(temporary)
        for label,context in cases:
            runtime=ROOT/'checks'/label/'runtime'
            if not (runtime/'usage.json').exists():runtime=ROOT/'checks'/label
            output=folder/(label+'.json')
            packet=export(private_context(ROOT,context),runtime,output,'gpt-6-luna')
            result=replay(output,runtime);assert result['passed'],result
            original=json.loads(output.read_text())
            for fault in ('usage','model','missing_event'):
                broken=copy.deepcopy(original)
                if fault=='usage':
                    event=next(e for s in broken['streams'] for e in s['events'] if e['kind']=='token_usage_record')
                    event['payload']['usage']['input_tokens']+=1
                elif fault=='model':broken['model']='gpt-6.1-sol'
                else:
                    stream=next(s for s in broken['streams'] if any(e['kind']=='token_usage_record' for e in s['events']))
                    index=next(i for i,e in enumerate(stream['events']) if e['kind']=='token_usage_record')
                    del stream['events'][index]
                write_json(output,broken)
                try:replay(output,runtime)
                except ValueError:pass
                else:raise AssertionError('Damaged public accounting accepted: '+fault)
            rows.append(dict(probe=label,**result))
            # Persist only the passing filtered accounting packet; no private context copy.
            write_json(ROOT/'checks/accounting-replay'/output.name,packet)
        assert public_payload('session_meta',dict(id='session',creator_account_id='private',base_instructions='private'))==dict(id='session')
        assert public_payload('response_item',dict(type='function_call',call_id='call',arguments='private'))==dict(type='function_call',call_id='call')
        assert public_payload('unknown',dict(secret='private')) is None
    result=dict(passed=True,model_calls=0,physical_runs=0,rows=rows,
        scope='Actual old preflight evidence replay; no new design samples',
        privacy='Explicit field whitelist removes account identity, instructions, transport and tool content')
    write_json(ROOT/'checks/accounting-replay.json',result)
    return result


if __name__=='__main__':print(json.dumps(check()))
