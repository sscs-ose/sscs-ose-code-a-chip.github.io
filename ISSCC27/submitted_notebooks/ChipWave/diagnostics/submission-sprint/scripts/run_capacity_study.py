"""Execute frozen trials serially, retaining terminal failures and never replacing a run."""
import fcntl
import json
import os
import subprocess
import sys

from capacity_admission import admit_trial
from capacity_integration_physical import ROOT
from decide_capacity_pilots import finalize
from study_protocol import digest,write_json


def batch(category):
    rules=json.loads((ROOT/'protocol.json').read_text())
    jobs=rules['pilot_jobs' if category=='pilot' else 'formal_jobs']
    folder=ROOT/'batch'/category;folder.mkdir(parents=True,exist_ok=True)
    state=dict(category=category,pid=os.getpid(),status='running',planned=len(jobs),completed=[],running=None)
    with (folder/'.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        try:
            if jobs:admit_trial(category,jobs[0]['id'])
            for job in jobs:
                path=ROOT/'trials'/category/job['id']/'result.json'
                if not path.exists():
                    admit_trial(category,job['id'])
                    # A partial launch cannot be reset by restarting this batch controller.
                    if path.parent.exists():raise ValueError('Unfinished existing trial retained: '+job['id'])
                    state['running']=job['id'];write_json(folder/'state.json',state)
                    with (folder/(job['id']+'.log')).open('x') as log:
                        child=subprocess.run([sys.executable,str(ROOT/'scripts/run_capacity_trial.py'),
                            '--category',category,'--trial',job['id']],stdout=log,stderr=subprocess.STDOUT)
                    if not path.exists():
                        raise RuntimeError('Trial ended without terminal evidence: '+job['id']+' exit '+str(child.returncode))
                result=json.loads(path.read_text())
                if result.get('terminal') is not True or result.get('job')!=job:
                    raise ValueError('Mismatched or nonterminal result: '+job['id'])
                state['completed'].append(dict(id=job['id'],status=result['status'],
                    result_sha256=digest(path),final_score=result.get('final_score',0)))
                state['running']=None;write_json(folder/'state.json',state)
                print(json.dumps(dict(category=category,completed=len(state['completed']),
                    planned=len(jobs),trial=job['id'],status=result['status'])),flush=True)
            state['status']='terminal';write_json(folder/'state.json',state)
            return state
        except BaseException as error:
            state.update(status='stopped',error=type(error).__name__+': '+str(error))
            write_json(folder/'state.json',state)
            raise


def run():
    rules=json.loads((ROOT/'protocol.json').read_text())
    print(json.dumps(dict(resource_ceilings=dict(
        pilot_sessions=len(rules['pilot_jobs']),formal_sessions=len(rules['formal_jobs']),
        logical_tokens_per_session=rules['token_limit'],physical_attempts_per_session=2,
        physical_attempts_global=rules['physical_total'],active_seconds_per_session=rules['active_seconds'],
        physical_seconds_per_attempt=rules['physical_seconds'],postprocess_seconds_per_attempt=rules['postprocess_seconds']),
        warning='Resource ceilings, not a forecast; in-flight Token overshoot and offline evaluation are separately reported')),flush=True)
    decision=ROOT/'pilot-decision.json'
    if not decision.exists():
        batch('pilot');result=finalize()
    else:
        result=json.loads(decision.read_text())
    if not result['formal_launch_allowed']:
        print(json.dumps(dict(status='stopped_after_pilots',reason=result['reason'],
            note='Formal study is incomplete; retain all results and revise the protocol explicitly')),flush=True)
        return result
    return batch('formal')


if __name__=='__main__':run()
