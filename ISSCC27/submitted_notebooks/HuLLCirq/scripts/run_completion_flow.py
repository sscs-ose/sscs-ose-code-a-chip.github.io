"""Run the saved project's remaining physical stages through normal managers.

Uses the existing acceptance policy; a non-Passed result stops progression.
The English GUI remains available while the tools run. No RTL or model calls.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
import threading
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from hullcirq.server import make_server
from hullcirq.store import ProjectStore

def load(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime-dir',type=Path,required=True)
    parser.add_argument('--data-dir',type=Path,default=ROOT/'.work/projects/npu')
    parser.add_argument('--port',type=int,default=8769)
    parser.add_argument('--from-stage',choices=['layout','drc','lvs','postlayout'],default='layout')
    args=parser.parse_args();config=args.runtime_dir
    server=make_server('127.0.0.1',args.port,ProjectStore(args.data_dir),ROOT,
        load(ROOT/'.work/m2/compiler.json'),load(ROOT/'.work/m2b/synthesizer.json'),
        *[load(config/(name+'_runtime.json')) for name in ('physical','drc','lvs','postlayout')])
    threading.Thread(target=server.serve_forever,daemon=True).start()
    print(json.dumps({'GUI':f'http://127.0.0.1:{args.port}/','from_stage':args.from_stage}),flush=True)
    stages=['layout','drc','lvs','postlayout'];start=stages.index(args.from_stage)
    try:
        for stage in stages[start:]:
            physical=server.physical_workflow._state['runs'][-1]
            if stage=='layout':
                manager=server.physical_workflow
                manager.start('layout',physical['global_job_id'],physical['synthesis_run_id'],physical['netlist_run_id'],physical['revision_id'])
            elif stage=='drc':
                manager=server.drc_workflow;manager.start('drc',physical['id'],physical['revision_id'])
            elif stage=='lvs':
                manager=server.lvs_workflow;manager.start('lvs',physical['id'],server.drc_workflow._state['runs'][-1]['id'],physical['revision_id'])
            else:
                manager=server.postlayout_workflow;manager.start('post_layout_verification',physical['id'],
                    server.drc_workflow._state['runs'][-1]['id'],server.lvs_workflow._state['runs'][-1]['id'],physical['revision_id'])
            print(json.dumps({'stage':stage,'started':manager._state['runs'][-1]['id']}),flush=True)
            # Completion status is persisted before the authorized policy review.
            # Wait for both tool completion and the manager's adoption transaction.
            while manager.is_active() or (manager._worker is not None and manager._worker.is_alive()):time.sleep(1)
            with manager.lock:run=manager._decorate(manager._state['runs'][-1])
            print(json.dumps({'stage':stage,**{k:run.get(k) for k in ('id','execution_status','validation_status','review_status','freshness','error','diagnostics')}}),flush=True)
            if not all(run.get(k)==v for k,v in [('execution_status','Completed'),('validation_status','Passed'),('review_status','Accepted'),('freshness','Current')]):
                print('Progression stopped; inspect the retained result in the GUI.',flush=True);break
        print('GUI server remains available. Ctrl+C stops it.',flush=True)
        while True:time.sleep(1)
    except KeyboardInterrupt:pass
    finally:server.shutdown();server.server_close()
if __name__=='__main__':main()
