"""Five independent random starts, followed by a gated restart from their best valid candidate."""
from environment import ROOT,CODE,configure
BUDGET=configure()
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import shutil
import subprocess
import sys
import time

import workflow as W


def stop(process):
    if process.poll() is None:
        os.killpg(process.pid,signal.SIGTERM)
        try:process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid,signal.SIGKILL);process.wait()


def cpu_profile(processes,mask):
    pids=[process.pid for process in processes if process.poll() is None];seen=set();threads=0;union=set()
    for pid in pids:
        if pid in seen:continue
        seen.add(pid);base=Path('/proc')/str(pid)
        try:
            pids.extend(int(x) for x in (base/'task'/str(pid)/'children').read_text().split())
            tasks=list((base/'task').iterdir())
        except FileNotFoundError:continue
        for task in tasks:
            try:
                allowed=set(os.sched_getaffinity(int(task.name)))
                if not allowed<=mask:
                    os.sched_setaffinity(int(task.name),mask);allowed=set(os.sched_getaffinity(int(task.name)))
                if not allowed<=mask:raise RuntimeError('Worker affinity exceeds the CPU budget')
                union|=allowed;threads+=1
            except ProcessLookupError:continue
    return dict(status='PASS',processes=len(seen),threads=threads,cpu_union=sorted(union),maximum_cpu_count=len(mask))


def run(output,trials=6000,jobs=8,seed=0,parallel=3,verify=False,model=None,spiral_model=None):
    if trials<1 or not 1<=jobs<=BUDGET or not 1<=parallel<=5 or seed<0:raise ValueError('Invalid random-start budget')
    model=Path(model or ROOT/'models/transformer.pt').resolve()
    spiral_model=Path(spiral_model or ROOT/'models/spiral.pt').resolve()
    if not model.is_file() or not spiral_model.is_file():raise FileNotFoundError('Both surrogate checkpoints are required')
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=False)
    mask=set(os.sched_getaffinity(0));registry=output/'restart_registry.json'
    controller_sha=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    attempts=[dict(index=i,seed=seed+i,mode='random',directory=f'random_{i:02d}',status='pending') for i in range(5)]
    processes={};logs={};selected=None
    def save(status):
        if hashlib.sha256(Path(__file__).read_bytes()).hexdigest()!=controller_sha:
            raise RuntimeError('The multistart controller changed during execution')
        data=dict(status=status,random_starts=5,trials_per_stage=trials,jobs=jobs,parallel=parallel,
                  affinity=sorted(mask),attempts=attempts,controller_sha256=controller_sha)
        temp=registry.with_suffix('.tmp');W.write(temp,data);temp.replace(registry)
    def candidate(directory,item):
        nonlocal selected
        proposal=directory/'best.json';search_record=directory/'staged_search.json'
        if verify:
            import qualification_candidates as Q
            pool=Q.prepare(directory,model=model,spiral_model=spiral_model);record=Q.validate_pool(pool);passed=False
            for entry in record['entries']:
                proposal=pool/entry['proposal'];q=pool/f"em_{entry['rank']:02d}"
                try:W.qualify(proposal,q,threads=BUDGET,model=model,spiral_model=spiral_model)
                except RuntimeError as error:
                    if str(error)!='The new proposal did not pass independent qualification':raise
                    if Q.record_outcome(pool,entry['rank'],q,output) is not False:raise
                    assessment=W.read(q/'final_design.json')
                    if (not assessment['network_quality']['eligible_for_optimization']
                            or not all(row['eligible_for_optimization'] for row in assessment['spiral_network_quality'].values())):
                        continue
                    from em_active_refinement import refine
                    other=[pool/e['proposal'] for e in record['entries'] if e['rank']!=entry['rank']]
                    refined=refine(proposal,q,q/'active_refinement',cross_candidates=other[:4],
                                   model=model,spiral_model=spiral_model)
                    if refined is None:continue
                    Q.record_refinement(pool,entry['rank'],q,refined)
                    proposal,q=refined['proposal'],refined['qualification']
                else:
                    if Q.record_outcome(pool,entry['rank'],q,output) is not True:
                        raise ValueError('Qualification command returned without a qualified result')
                passed=True;break
            if not passed:
                Q.require_exhausted(pool,output)
                item.update(status='qualification_failed',qualification=str((pool/'em_00').relative_to(output)),
                            qualification_pool=str(pool.relative_to(output)))
                return False
            from qualified_results import build
            build(proposal,search_record,q,output/'final_results')
            item.update(status='qualified',qualification=str(q.relative_to(output)),
                        qualification_pool=str(pool.relative_to(output)))
        shutil.copy2(proposal,output/'best.json');shutil.copy2(search_record,output/'staged_search.json')
        selected=dict(initialization=W.read(search_record)['initialization'],proposal='best.json',
            search_record='staged_search.json',source_directory=str(directory.relative_to(output)),
            source_proposal=str(proposal.relative_to(output)),
            result_root='final_results' if verify else None,status='qualified' if verify else 'awaiting_independent_em')
        W.write(output/'selection.json',selected)
        return True
    save('running_random_starts')
    try:
        while True:
            active=sum(p.poll() is None for p in processes.values())
            for item in attempts:
                if active>=parallel:break
                if item['status']!='pending':continue
                index=item['index'];directory=output/item['directory'];log=(output/f'random_{index:02d}.log').open('w');logs[index]=log
                command=[sys.executable,str(CODE/'workflow.py'),'optimize-staged','--output',str(directory),
                         '--trials',str(trials),'--jobs',str(jobs),'--seed',str(item['seed']),
                         '--model',str(model),'--spiral-model',str(spiral_model)]
                processes[index]=subprocess.Popen(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                item['status']='running';active+=1;save('running_random_starts')
            for item in attempts:
                index=item['index']
                if item['status']!='running' or processes[index].poll() is None:continue
                directory=output/item['directory'];progress=W.read(directory/'staged_search.json');code=processes[index].returncode
                expected=(2,'no_feasible_proposal') if progress['status']=='no_feasible_proposal' else (0,'awaiting_independent_em')
                if (code,progress['status'])!=expected:
                    item['status']='execution_failed';save('execution_failed');raise RuntimeError('Random search did not finish normally')
                item.update(status=progress['status'],stages=progress['stages'])
                if progress['status']=='awaiting_independent_em' and candidate(directory,item):break
            W.write(output/'affinity_verification.json',cpu_profile(list(processes.values()),mask))
            if selected is not None:break
            if all(item['status'] not in ('pending','running') for item in attempts):
                status='five_random_searches_failed_after_em' if any(a['status']=='qualification_failed' for a in attempts) else 'five_random_searches_failed'
                save(status)
                from conditional_restart import run as restart
                snapshot=output/'five_random_failures.json';shutil.copy2(registry,snapshot)
                for warm_index in range(5):
                    directory=output/f'conditional_restart_{warm_index:02d}'
                    progress=restart(snapshot,directory,trials,jobs,seed+5+warm_index,trials,
                                     model=model,spiral_model=spiral_model)
                    if progress['status']=='awaiting_independent_em' and candidate(directory,dict(status='awaiting_independent_em')):
                        break
                break
            save('running_random_starts');time.sleep(2)
        for item in attempts:
            index=item['index']
            if index not in processes or item['status']!='running':continue
            if processes[index].poll() is None:
                stop(processes[index]);item['status']='stopped_after_selection'
            else:
                completed=W.read(output/item['directory']/'staged_search.json')
                if completed['status'] not in ('no_feasible_proposal','awaiting_independent_em'):
                    raise RuntimeError('A completed random start has an invalid status')
                item.update(status=completed['status'],stages=completed['stages'])
        if selected is not None:save(selected['status'])
        else:save('no_qualified_candidate')
        return selected
    except BaseException:
        for process in processes.values():stop(process)
        raise
    finally:
        for stream in logs.values():stream.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--trials',type=int,default=6000)
    parser.add_argument('--jobs',type=int,default=8);parser.add_argument('--seed',type=int,default=0)
    parser.add_argument('--parallel',type=int,default=3);parser.add_argument('--verify',action='store_true')
    parser.add_argument('--model',type=Path);parser.add_argument('--spiral-model',type=Path)
    args=parser.parse_args();result=run(args.output,args.trials,args.jobs,args.seed,args.parallel,args.verify,args.model,args.spiral_model)
    print(json.dumps(result,indent=2))
    if result is None:raise SystemExit(2)
