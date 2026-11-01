"""Derive the scheduler proposal from the preserved real GUI project.

This edits specification only. It does not generate RTL or claim execution.
The source job and existing PE contract/edge are preserved exactly.
"""
from __future__ import annotations
import copy
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]

def build_proposal(design):
    proposal = copy.deepcopy(design)
    proposal['project']['implementation_scope'] = 'PE template and serial scheduler first; 16-PE array/global integration not implemented'
    scheduler = next(n for n in proposal['nodes'] if n['id'] == 'node-scheduler')
    scheduler['behavior'] = (
        'Serial row-major16-lane dispatch, no instantiated array yet. '
        'Config: K[4:0]=1..16, ReLU[5], signed32 biases[6+32*i+:32]; ignore ReLU/bias in scheduler. '
        'IDLE config_ready=!rst && K in1..16, independent of valid. Config handshake latches K, zeroes lane/index/data, enters CLEAR. '
        'CLEAR pulses pe_clear1cycle then ISSUE. ISSUE holds request_valid/address until handshake then WAIT. '
        'Request[5:0]=row*16+k_index; [13:8]=k_index*4+column; reserved[7:6]/[15:14]=0. '
        'WAIT response_ready=1; handshake stores16bits then EMIT. Pair low8=A/high8=B signed8. '
        'EMIT holds pair_valid/data/meta until pair_ready handshake. Meta[3:0]=lane=row*4+column,[4]=index0,[5]=indexK-1; only valid with pair_valid. '
        'Pair handshake advances index; after K pairs lane++/index0; lane15 last pair->DONE; otherwise ISSUE. '
        'DONE pulses schedule_done one cycle: dispatch completion, not final output completion. '
        'Sync high rst overrides, clears state/counters/data, gates all ready/valid/pulses low. '
        'Config_ready only IDLE,response_ready only WAIT,request_valid only ISSUE,pair_valid only EMIT; one outstanding read. Pair_data holds between responses. '
        'Future integration: broadcast pe_clear reset before first product; first is metadata. Drain intermediate PE sums; retain final metadata. Buffer shares reset/cancels old responses.'
    )
    scheduler['test_expectations'] = (
        'Same original job/frozen independent recipe for RTL/netlist. Held-pair abort forces pair_ready0 after5pairs until EMIT held, then reset. '
        'Final K4 dispatch64pairs/16lanes; stalls/delays, invalidK0/17, busy config, two reset aborts. Public checks only; no full-NPU/exhaustive claim.'
    )
    scheduler['constraints'] = {'latency_cycles': 1, 'protocol': 'valid_ready', 'dispatch_strategy': 'serial_row_major', 'outstanding_reads': 1}
    scheduler['ports'] = [p for p in scheduler['ports'] if p['protocol'] != 'raw']
    for name, width, kind, associated in [('pair_meta',6,'metadata','port-scheduler-pair_data'),('pe_clear',1,'pulse',None),('schedule_done',1,'pulse',None)]:
        scheduler['ports'].append({'id': 'port-scheduler-'+name, 'name':name, 'direction':'output', 'width':width, 'signed':False,
            'protocol':'raw', 'clock':'clk', 'reset':'rst', 'sideband':{'kind':kind,'associated_port_id':associated}})
    scheduler['verification'] = {'kind':'npu_scheduler_stream','version':1,'source_job':copy.deepcopy(proposal['verification_jobs'][0]),
        'exercise':{'kind':'complete_cancel_restart_v1','request_ready_pattern':[0,0,1,1], 'pair_ready_pattern':[0,1,0,1,1],
            'response_delays':[0,2,1,3], 'cancel_after_pair_transfers':5,'cancel_states':['response_pending','pair_held'],'invalid_k':[0,17]}}
    edge = next(e for e in proposal['edges'] if e['id']=='edge-scheduler-buffer')
    edge['behavior'] = ('valid/ready transfer; hold under stalls; clk/sync high rst. One A/B read pending: [5:0]=row*16+k (A),[13:8]=k*4+column (B),[7:6]/[15:14]=0. '
        'Responses ordered; shared reset cancels pending. Buffer RTL pending.')
    return proposal

def main():
    runtime = ROOT/'.work/projects/npu'
    backup = ROOT/'.work/m2d/original_runtime'
    if backup.exists():
        raise SystemExit('Baseline already exists; refusing to replace the preserved original runtime.')
    backup.mkdir(parents=True)
    hashes={}
    for name in ['state.json','generation.json','workflow.json','implementation_specs.json']:
        source=runtime/name
        if source.exists():
            shutil.copy2(source,backup/name)
            hashes[name]=hashlib.sha256(source.read_bytes()).hexdigest()
    state=json.loads((backup/'state.json').read_text(encoding='utf-8'))
    baseline={'record_kind':'preserved_actual_project_before_scheduler_specification','revision':state['revision'], 'files':hashes}
    (backup.parent/'baseline.json').write_text(json.dumps(baseline,indent=2)+'\n',encoding='utf-8')
    proposal=build_proposal(state['design'])
    (ROOT/'examples/npu_scheduler_project.json').write_text(json.dumps(proposal,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'baseline_revision':state['revision']['id'],'proposal':'examples/npu_scheduler_project.json','original_job_unchanged':proposal['verification_jobs']==state['design']['verification_jobs']}))

if __name__=='__main__':
    main()
