"""Check resumed cumulative Tokens and source-bound repair accounting without a model."""
from pathlib import Path
import json
import tempfile

from run_configuration_study import usage_and_repairs
from study_protocol import write_json
from summarize_ppa_study import context_audit


def session(path,name,counts):
    events=[{'type':'session_meta','payload':{'id':name}},
        {'type':'turn_context','payload':{'model':'gpt-6.1-sol','effort':'high'}}]
    for input_tokens,cached,output,reasoning in counts:
        events.append({'type':'event_msg','timestamp':'2026-10-16T00:00:00Z',
            'payload':{'type':'token_count','info':{'total_token_usage':{
                'input_tokens':input_tokens,'cached_input_tokens':cached,
                'output_tokens':output,'reasoning_output_tokens':reasoning}}}})
    path.write_text('\n'.join(json.dumps(event) for event in events)+'\n')


def run():
    with tempfile.TemporaryDirectory() as temporary:
        root=Path(temporary);private=root/'private';(private/'sessions').mkdir(parents=True)
        output=root/'output';output.mkdir()
        session(private/'sessions/a.jsonl','session-a',[(10,4,3,1),(30,20,10,4)])
        session(private/'sessions/b.jsonl','session-b',[(15,10,5,2)])
        checks=[('a',False),('a',False),('b',True),('b',True),('c',True)]
        for i,(source,passed) in enumerate(checks):
            write_json(output/'development-checks'/f'check-{i:04d}.json',
                {'source_sha256':{'rtl/top.sv':source},'passed':passed})
        result=usage_and_repairs(private,output,{'source_sha256':{'rtl/top.sv':'d'}})
        assert result['tokens']=={'input_tokens':45,'cached_input_tokens':30,
                                 'output_tokens':15,'reasoning_output_tokens':6}
        assert result['model_sessions']==2 and result['repair_iterations']==1
        assert result['unchanged_source_rechecks']==2 and result['final_source_changed_since_last_development_check']
        before=(output/'usage.json').read_bytes()
        (private/'sessions/duplicate.jsonl').write_bytes((private/'sessions/a.jsonl').read_bytes())
        try:usage_and_repairs(private,output,{})
        except ValueError:pass
        else:raise AssertionError('Duplicate session usage was silently counted twice')
        assert (output/'usage.json').read_bytes()==before
        usage=json.loads(before)
        assert context_audit(usage,'W1')['passed']
        assert context_audit({},'W0')['passed'] and not context_audit(usage,'W0')['passed']
        assert not context_audit({'totals':{'input_tokens':1}},'W0')['passed']
        changed=json.loads(before);changed['totals']['input_tokens']+=1
        assert not context_audit(changed,'W1')['passed']
        changed=json.loads(before);changed['sessions'][0]['model']='another-model'
        assert not context_audit(changed,'W1')['passed']
        changed=json.loads(before);changed['sessions'][0]['tokens']['cached_input_tokens']=1000
        assert not context_audit(changed,'W2')['passed']
    print('STUDY_USAGE_SELF_CHECK_PASS: last cumulative event per session, cached input, reasoning not double-added, repair/recheck distinction and duplicate rejection; model_calls=0')


if __name__=='__main__':run()
