"""Check completed host work, asynchronous source costs and compound-command guidance."""
import copy
import hashlib
import json
import tempfile
import threading
from pathlib import Path
from unittest.mock import patch

from capacity_meter import TokenLedger, InvalidMeasurement
from capacity_tool_router import ToolRouter
from qualify_capacity_events import associate_completed
from self_check_capacity_router import event, denied, native
from study_protocol import write_json

ROOT=Path(__file__).resolve().parents[1]


def check():
    ledger=TokenLedger(limit=250)
    def usage(n):return dict(input_tokens=n-10,output_tokens=10,total_tokens=n,cached_input_tokens=0,reasoning_output_tokens=0)
    first=ledger.record('session','byte-20',usage(100))
    ledger.record('session','byte-200',usage(300))
    capture=dict(session='session',call_id='child',parent_call_id='origin',
        source_sha256={'rtl/design.sv':'fixture'},completion_fence=dict(bytes=150,sha256='a'*64),
        response_admission=dict(event_key='byte-20',parent_call_id='origin',tokens=100,usage_sha256=first['sha256']))
    events=[dict(subtype='custom_tool_call',call_id='origin',event_key='byte-0'),
            dict(subtype='token_count',event_key='byte-20'),
            dict(subtype='custom_tool_call_output',call_id='origin',event_key='byte-40'),
            dict(subtype='function_call',call_id='wait',event_key='byte-100'),
            dict(subtype='function_call_output',call_id='wait',event_key='byte-180'),
            dict(subtype='token_count',event_key='byte-200')]
    assert associate_completed(events,capture,ledger)
    scored=ledger.state['snapshots'][-1]
    assert scored['tokens']==300 and not scored['budget_admissible']
    assert associate_completed(events[:-1],capture,ledger,interrupted=True) is False
    for fault in ('no_watermark','bad_owner','bad_admission'):
        bad=copy.deepcopy(capture);stream=events
        if fault=='no_watermark':stream=events[:-1]
        elif fault=='bad_owner':bad['parent_call_id']='wrong'
        else:bad['response_admission']['tokens']=1
        try:associate_completed(stream,bad,ledger)
        except InvalidMeasurement:pass
        else:raise AssertionError(fault+' accepted')
    with tempfile.TemporaryDirectory(prefix='completion-check-') as directory:
        root=Path(directory);work=root/'work';work.mkdir()
        (work/'spec').mkdir();(work/'spec/task.txt').write_text('fixture')
        entered,release=threading.Event(),threading.Event();replies=[]
        def tool(*args,**kwargs):
            entered.set();assert release.wait(5)
            return dict(exit_code=0),'HOST_DONE'
        with ToolRouter(work,root/'ledger',authorize=lambda:True) as router:
            request=event(work,'async','sleep 1')
            with patch('capacity_tool_router.execute_development',side_effect=tool):
                worker=threading.Thread(target=lambda:replies.append(router.handle(request)))
                worker.start();assert entered.wait(5)
                assert denied(router.handle(event(work,'too-early','pwd')))
                release.set();worker.join(5);assert not worker.is_alive()
            assert router.active is None and not denied(replies[0])
            # The original async cell can be cancelled or its PostToolUse delayed indefinitely.
            following=event(work,'after-cancel','cat spec/task.txt')
            reply=router.handle(following);assert not denied(reply)
            assert native(work,reply['hookSpecificOutput']['updatedInput']['command']).stdout=='fixture'
            pending=event(work,'patch','*** Begin Patch\n*** Add File: rtl/new.sv\n+module new;endmodule\n*** End Patch','apply_patch')
            assert not denied(router.handle(pending))
            router.handle(dict(request,hook_event_name='PostToolUse'))
            assert router.active=='patch', 'Late old PostToolUse cleared a different operation'
            router.handle(dict(pending,hook_event_name='PostToolUse'))
            req=event(work,'compound','pwd && capacity-check status')
            reply=router.handle(req)
            actual=native(work,reply['hookSpecificOutput']['updatedInput']['command'])
            assert actual.returncode==2 and 'standalone command' in actual.stdout
            req=event(work,'standalone','capacity-check status');reply=router.handle(req)
            actual=native(work,reply['hookSpecificOutput']['updatedInput']['command'])
            assert actual.returncode==0 and json.loads(actual.stdout)['dispatch_allowed']
    result=dict(passed=True,model_calls=0,physical_runs=0,synthetic=True,checks=[
        'real in-flight work blocks another tool; completed host work releases ownership',
        'missing or delayed original PostToolUse cannot lock subsequent shell calls',
        'late original PostToolUse cannot clear a new patch',
        'async wait costs charged after actual source completion, not before the tool',
        'over-budget completion excluded; interrupted prefix preserved',
        'missing watermark and changed response owner/admission rejected',
        'compound capacity-check gives actionable instructions; standalone status remains available'])
    write_json(ROOT/'checks/completion-boundaries.json',result)
    return result


if __name__=='__main__':print(json.dumps(check()))
