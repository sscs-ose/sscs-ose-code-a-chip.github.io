"""Export only native accounting/association fields and replay their arithmetic offline."""
import hashlib
import json
from pathlib import Path

from capacity_meter import TokenLedger,FIELDS
from capacity_native_usage import NativeUsage
from qualify_capacity_events import associate,associate_completed,CALLS,OUTPUTS
from study_protocol import digest,write_json


def usage_fields(usage):
    fields=(*FIELDS,'total_tokens','cache_write_input_tokens')
    return {field:usage[field] for field in fields if field in usage}


def public_payload(kind,payload):
    if kind=='session_meta':return dict(id=payload['id'])
    if kind=='turn_context':return {k:payload[k] for k in ('model','effort')}
    if kind=='token_usage_record':
        return dict(session_id=payload['session_id'],response_id=payload['response_id'],
            **{k:usage_fields(payload[k]) for k in ('usage','thread_token_usage')})
    if kind=='compacted':return dict(compaction_response_id=payload.get('compaction_response_id'))
    if kind=='event_msg' and payload.get('type')=='token_count':
        return dict(type='token_count',info=dict(total_token_usage=usage_fields(payload['info']['total_token_usage'])))
    if kind=='response_item' and payload.get('type') in (*CALLS,*OUTPUTS):
        return dict(type=payload['type'],call_id=payload.get('call_id'))
    return None


def export(private,runtime,output,model):
    private,runtime,output=Path(private),Path(runtime),Path(output)
    if output.exists():raise ValueError('Preserve existing accounting export')
    ledger=json.loads((runtime/'usage.json').read_text())
    streams=[]
    for name,prefix in ledger.get('transcript_prefixes',{}).items():
        path=private/name
        if Path(name).is_absolute() or '..' in Path(name).parts or path.is_symlink() or not path.resolve().is_relative_to(private.resolve()):
            raise ValueError('Unsafe native transcript path')
        data=path.read_bytes()[:prefix['bytes']]
        if len(data)!=prefix['bytes'] or hashlib.sha256(data).hexdigest()!=prefix['sha256']:
            raise ValueError('Native prefix differs from observed evidence')
        events=[];offset=0
        for line in data.splitlines(keepends=True):
            source=json.loads(line);payload=public_payload(source['type'],source.get('payload',{}))
            if payload is not None:events.append(dict(offset=offset,kind=source['type'],payload=payload))
            offset+=len(line)
        streams.append(dict(path=name,observed_prefix=prefix,events=events))
    packet=dict(model=model,streams=streams,usage_sha256=digest(runtime/'usage.json'),
        scope='Protected collector export: native usage, model identity and tool IDs only. Account identity, prompts, tool content and transport settings omitted. Original byte offsets and prefix hashes are provenance; removed bytes are not reconstructed.')
    write_json(output,packet)
    return packet


def replay(packet_path,runtime):
    runtime=Path(runtime);packet=json.loads(Path(packet_path).read_text())
    expected=json.loads((runtime/'usage.json').read_text())
    if digest(runtime/'usage.json')!=packet['usage_sha256']:raise ValueError('Usage receipt changed')
    if not expected['valid']:return dict(passed=False,status='retained_invalid_measurement',errors=expected['errors'])
    usages={};streams={};contexts=set()
    for source in packet['streams']:
        if source['observed_prefix']!=expected['transcript_prefixes'].get(source['path']):
            raise ValueError('Native prefix identity differs')
        native=NativeUsage();events=[];last=-1
        for row in source['events']:
            if type(row['offset']) is not int or row['offset']<=last:raise ValueError('Bad native event order')
            last=row['offset'];kind,payload=row['kind'],row['payload']
            if kind=='turn_context':
                if payload!={'model':packet['model'],'effort':'high'} or not native.session:
                    raise ValueError('Wrong model/effort/context')
                contexts.add(native.session)
            usage=native.observe(kind,payload);key='byte-'+str(row['offset'])
            if usage is not None:
                if native.session not in contexts:raise ValueError('Usage lacks qualified context')
                usages[native.session+':'+key]=usage
            if kind in ('response_item','event_msg'):
                events.append(dict(kind=kind,subtype=payload.get('type'),call_id=payload.get('call_id'),
                    event_key=key,usage=usage if payload.get('type')=='token_count' else None))
        if not native.session or native.session in streams:raise ValueError('Duplicate/missing session')
        streams[native.session]=events
    if set(usages)!=set(expected['events']):raise ValueError('Missing or extra usage events')
    meter=TokenLedger(limit=expected['limit'])
    for key,original in expected['events'].items():
        session,event=key.rsplit(':',1)
        if meter.record(session,event,usages[key])!=original:raise ValueError('Recomputed usage differs')
    for snapshot in expected['snapshots']:
        folder=runtime/'tools/snapshots'/snapshot['id']
        if not folder.resolve().is_relative_to((runtime/'tools/snapshots').resolve()):raise ValueError('Unsafe snapshot')
        capture=json.loads((folder/'capture.json').read_text())
        if capture['source_sha256']!=snapshot['source_sha256'] or capture['session']!=snapshot['session']:
            raise ValueError('Source capture differs')
        sources={}
        for name,sha in snapshot['source_sha256'].items():
            path=folder/name
            if Path(name).is_absolute() or '..' in Path(name).parts or path.is_symlink() or not path.resolve().is_relative_to(folder.resolve()) or digest(path)!=sha:
                raise ValueError('Snapshot source changed')
            sources[name]=dict(sha256=sha,text=path.read_text())
        if capture.get('capture_phase')=='before_deterministic_tool':
            admission=capture.get('response_admission',{})
            entry=meter.state['events'].get(capture['session']+':'+admission.get('event_key',''))
            if (not entry or admission.get('parent_call_id')!=capture.get('parent_call_id') or
                admission.get('tokens')!=entry['global_tokens'] or admission.get('usage_sha256')!=entry['sha256']):
                raise ValueError('Physical source admission differs')
            meter.snapshot(snapshot_id=snapshot['id'],source_sha256=snapshot['source_sha256'],
                session=snapshot['session'],event_key=admission['event_key'],witness=snapshot['witness'])
        elif capture.get('capture_phase')=='after_controlled_tool':
            if not associate_completed(streams[snapshot['session']],capture,meter,interrupted=True):
                raise ValueError('Scored completed source has no watermark')
        else:
            associate(streams[snapshot['session']],[dict(capture,event='PostToolUse',sources=sources)],
                ledger=meter,interrupted=True)
        if meter.state['snapshots'][-1]!=snapshot:raise ValueError('Recomputed snapshot differs')
    if meter.summary()['actual_tokens']!=expected['actual_tokens']:raise ValueError('Total usage mismatch')
    return dict(passed=True,status='recomputed',tokens=meter.summary()['actual_tokens'],
        snapshots=len(meter.state['snapshots']),contexts=len(contexts),
        scope='Offline arithmetic and protected source association replay, not independent provider billing verification')


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--packet',required=True,type=Path)
    parser.add_argument('--runtime',required=True,type=Path)
    args=parser.parse_args()
    result=replay(args.packet,args.runtime)
    print(json.dumps(result))
    raise SystemExit(0 if result['passed'] else 1)
