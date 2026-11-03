"""Execute the new counter contract with the reused public Role/TaskGraph runtime."""
from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from chip_nebula.taskgraph.static_cli import run_workflow,cancel_workflow_attempts
from chip_nebula.taskgraph.static_store import StaticTaskGraphStore
from prepare_counter_transfer import prepare,bench
from study_budget import BudgetPool
from study_portability import private_context
from study_isolation import prepare_credentials
from study_protocol import digest,write_json

CASE=Path(__file__).resolve().parents[1]


def worker(root,private):
    prepare_credentials(private)
    wrappers=private/'wrapper';wrappers.mkdir(exist_ok=True)
    wrapper=wrappers/'codex'
    wrapper.write_text('#!'+sys.executable+'\nimport os,sys\nos.execv(sys.executable,[sys.executable,'+
                      repr(str(CASE/'scripts/study_isolation.py'))+',*sys.argv[1:]])\n');wrapper.chmod(0o700)
    os.environ.update(CHIP_STUDY_PROJECT=str(root),CHIP_STUDY_PRIVATE_HOME=str(private),PATH=str(wrappers)+os.pathsep+os.environ['PATH'])
    pool=BudgetPool(root.parent/'results/budget.json',total_deadline=time.monotonic()+1200)
    state=run_workflow(root,root/'.chip_nebula/shared/memory/taskgraph-v2.db','counter-transfer',pool,workers=1)
    write_json(root.parent/'results/workflow.json',{'state':state.value})


def run(experiment):
    folder=experiment/'transfer/counter'
    if folder.exists():raise ValueError('Existing counter experiment retained')
    results=folder/'results';results.mkdir(parents=True)
    root=folder/'project';prepare(root)
    private=private_context(experiment,'counter')
    if private.exists():raise ValueError('Prior model context retained; do not reuse')
    started=time.monotonic();timed_out=False
    cmd=[sys.executable,str(Path(__file__).resolve()),'--worker',str(root),'--private',str(private)]
    with (results/'workflow.log').open('w') as log:
        process=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        try:process.wait(timeout=1200)
        except subprocess.TimeoutExpired:
            timed_out=True;os.killpg(process.pid,signal.SIGTERM)
            try:process.wait(timeout=20)
            except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait()
            cancel_workflow_attempts(root,root/'.chip_nebula/shared/memory/taskgraph-v2.db','counter-transfer',reason='Frozen transfer budget exhausted')
    duration=time.monotonic()-started
    with StaticTaskGraphStore(root/'.chip_nebula/shared/memory/taskgraph-v2.db') as store:
        delivery=store.deliveries('counter-transfer:designer').get('rtl')
        artifact=store.get_artifact(delivery.artifact_id) if delivery else None
        state=store.get_workflow('counter-transfer').status.value
    outcome={'passed':False,'workflow_state':state,'timed_out':timed_out,'engineering_seconds':duration,
             'model': 'gpt-6.1-sol','reasoning_effort':'high','budget_seconds':1200,
             'hidden_planner_calls':0,'manual_design_interventions':0,'source_sha256':{}}
    if artifact:
        selected=results/'selected';selected.mkdir()
        entries=subprocess.run(['git','ls-tree','-r','--name-only',artifact.content.commit,'rtl'],cwd=root,text=True,capture_output=True,check=True).stdout.splitlines()
        for relative in entries:
            if Path(relative).suffix not in ('.v','.sv'):continue
            destination=selected/relative;destination.parent.mkdir(parents=True,exist_ok=True)
            destination.write_bytes(subprocess.run(['git','show',artifact.content.commit+':'+relative],cwd=root,capture_output=True,check=True).stdout)
            outcome['source_sha256'][relative]=digest(destination)
        checker=results/'counter_acceptance_tb.sv';checker.write_text(bench(True))
        sources=[str(selected/path) for path in outcome['source_sha256']]
        commands=[['iverilog','-g2012','-s','counter_check_tb','-o',str(results/'sim'),*sources,str(checker)],
                  ['vvp',str(results/'sim')],['yosys','-Q','-T','-p','read_slang --top counter '+' '.join(sources)+'; proc; opt; check -assert']]
        codes=[]
        for name,command in zip(('compile','acceptance','synthesis'),commands):
            result=subprocess.run(command,text=True,capture_output=True,timeout=120)
            (results/(name+'.log')).write_text(result.stdout+result.stderr);codes.append(result.returncode)
            if result.returncode:break
        outcome.update(passed=codes==[0,0,0] and 'COUNTER_CHECK_PASS checks=2051' in (results/'acceptance.log').read_text(),
                       final_check_exit_codes=codes,final_checker_sha256=digest(checker),source_delivery=artifact.id)
    from run_configuration_study import usage_and_repairs
    outcome['usage']=usage_and_repairs(private,results,{})
    write_json(results/'result.json',outcome)
    print(json.dumps(outcome,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--experiment',type=Path)
    p.add_argument('--worker',type=Path);p.add_argument('--private',type=Path)
    a=p.parse_args()
    if a.worker:worker(a.worker.resolve(),a.private.resolve())
    else:
        if not a.experiment:p.error('--experiment required')
        run(a.experiment.resolve())
