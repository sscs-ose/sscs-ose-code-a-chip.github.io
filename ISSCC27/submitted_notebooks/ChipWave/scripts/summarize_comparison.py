#!/usr/bin/env python3
"""Recompute pilot statistics from trial-local usage evidence, without a model account."""
import argparse
import json
import statistics
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
KEYS=('input_tokens','cached_input_tokens','output_tokens','reasoning_output_tokens')


def capture_usage(root,mode,number):
    """Explicit opt-in for a fresh pilot: export only token/model metadata from its own sessions."""
    mapping=[]
    if mode=='platform':
        folder=root/'comparison'/f'platform-{number}/.chip_nebula/shared/memory/session_ids'/f'npu-pilot-{number}'
        mapping=[dict(file=p.name,session_id=p.read_text().strip()) for p in sorted(folder.glob('*.txt'))]
        ids=sorted({m['session_id'] for m in mapping if m['session_id']})
    else:
        events=[]
        for line in (root/'results/comparison'/f'direct-{number}/agent.log').read_text().splitlines():
            try:events.append(json.loads(line))
            except json.JSONDecodeError:continue
        ids=sorted({e['thread_id'] for e in events if e.get('type')=='thread.started'})
    if not ids:raise ValueError(f'missing session identifiers: {mode}-{number}')
    sessions=[]
    for sid in ids:
        paths=list((Path.home()/'.codex/sessions').rglob('*'+sid+'.jsonl'))
        if len(paths)!=1:raise ValueError(f'expected one local session log for {sid}')
        events=[json.loads(line) for line in paths[0].read_text().splitlines()]
        contexts=[e['payload'] for e in events if e.get('type')=='turn_context']
        usage=[e for e in events if e.get('type')=='event_msg' and e.get('payload',{}).get('type')=='token_count']
        if not contexts or not usage:raise ValueError('model context or token event missing: '+sid)
        event,context=usage[-1],contexts[-1]
        sessions.append(dict(session_id=sid,model_context={'model':context['model'],'reasoning_effort':context['effort']},
            terminal_usage_event={'timestamp':event['timestamp'],'type':event['type'],
                'payload':{'type':'token_count','info':event['payload']['info']}}))
    record=dict(format_version=1,mode=mode,trial=number,session_mapping=mapping,sessions=sessions,
        extraction='Terminal token_count and model/effort fields from original local Codex JSONL; prompts, responses, account rate limits and credentials excluded.')
    path=root/'results/comparison'/f'{mode}-{number}/usage.json'
    if path.exists():raise ValueError('existing usage evidence is preserved: '+str(path))
    path.write_text(json.dumps(record,indent=2)+'\n')


def trial_usage(path,mode,number):
    record=json.loads(path.read_text())
    assert record['format_version']==1 and record['mode']==mode and record['trial']==number
    sessions=record['sessions'];assert sessions
    assert len({s['session_id'] for s in sessions})==len(sessions)
    result={k:0 for k in KEYS}
    for session in sessions:
        event=session['terminal_usage_event']
        assert event['type']=='event_msg' and event['payload']['type']=='token_count'
        values=event['payload']['info']['total_token_usage']
        assert all(type(values[k]) is int and values[k]>=0 for k in KEYS)
        assert values['cached_input_tokens']<=values['input_tokens']
        for key in KEYS:result[key]+=values[key]
    result['uncached_input_tokens']=result['input_tokens']-result['cached_input_tokens']
    return [s['session_id'] for s in sessions],result


def summarize(root=ROOT,capture=False):
    folder=root/'results/comparison';rows=[]
    for mode in ('direct','platform'):
        for number in range(1,6):
            path=folder/f'{mode}-{number}/result.json'
            if not path.is_file():raise ValueError('comparison has not finished: '+str(path))
            receipt=path.parent/'usage.json'
            if capture and not receipt.exists():capture_usage(root,mode,number)
            row=json.loads(path.read_text())
            row['model_sessions'],row['usage']=trial_usage(receipt,mode,number)
            contexts=json.loads(receipt.read_text())['sessions']
            assert all(s['model_context']=={'model':row['model'],'reasoning_effort':row['reasoning_effort']} for s in contexts), 'recorded model/effort differs from trial conditions'
            row['usage_evidence']=str(receipt.relative_to(root))
            rows.append(row)
    assert len(rows)==10
    summary={'complete':True,'scope':'NPU RTL generation pilot only; no full CPU/GDS platform causality claim',
        'timing_scope':'model engineering workflow, including platform planning/public gates/audit when applicable; separate shared final acceptance is excluded',
        'usage_evidence':'trial-local usage.json; sanitized terminal Codex token_count event for every recorded model session',
        'dollar_cost':None,'dollar_cost_reason':'ChatGPT-authenticated Codex sessions; actual API dollar charges were not measured',
        'rows':rows,'treatments':{}}
    for mode in ('direct','platform'):
        selected=[r for r in rows if r['mode']==mode]
        summary['treatments'][mode]={'passed':sum(r['passed'] for r in selected),'attempted':5,
            'median_engineering_seconds':statistics.median(r['elapsed_seconds'] for r in selected),
            'mean_engineering_seconds':statistics.mean(r['elapsed_seconds'] for r in selected),
            'total_recorded_usage':{k:sum(r['usage'][k] for r in selected) for k in selected[0]['usage']}}
    summary['finding']='Both treatments passed all five scheduled trials. This pilot shows no success-rate advantage for ChipWave; its measured planning, checking and artifact overhead must be included.'
    (folder/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary['treatments'],indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-root',type=Path,default=ROOT)
    parser.add_argument('--capture-usage',action='store_true',help='For a new pilot only: export token metadata from your own local Codex sessions')
    args=parser.parse_args();summarize(args.run_root.resolve(),args.capture_usage)
