"""Eight fresh matched guard acquisitions; no saved substitution.
SPDX-License-Identifier: Apache-2.0
"""
from concurrent.futures import ThreadPoolExecutor,as_completed
import platform,sys,time
from guard_consumer import HERE,run_guard,save
from guard_evidence import audit
from check_guard import checks

def main():
    saved=audit();fixtures=checks(saved);jobs=[]
    for variant in ['original','digital_guard']:
        jobs.extend([dict(variant=variant,event='digital_zero'),dict(variant=variant,event='none'),dict(variant=variant,condition='half_depth'),dict(variant=variant,condition='slow_zero',max_step=1e-6)])
    dest=HERE/'results/reproduction/guard_short.json';start=time.monotonic()
    record=dict(status='in_progress',python=sys.version.split()[0],platform=platform.platform(),jobs=jobs,runs=[],saved_complete=22,fixture_checks=fixtures,scope='Eight fresh TT acquisitions at four matched histories, including a refined common working cost anchor. No independent-machine, physical qualification, globally unseen challenge or publication claim.')
    save(dest,record)
    with ThreadPoolExecutor(max_workers=2) as pool:
        for future in as_completed([pool.submit(run_guard,**job) for job in jobs]):record['runs'].append(future.result());save(dest,record)
    assert len(record['runs'])==8 and all(r['status']=='completed' for r in record['runs'])
    for row in record['runs']:
        q=row['result'];assert q['declared_precondition_verified'] and q['alternate_state_exercised'] and q['events'][0]['pass_contract']
        if row['event']=='none':assert row['normal_storage_control_pass']
        else:assert q['observed_pass']==(row['variant']=='digital_guard' or row['condition']=='slow_zero')
    record.update(status='passed',elapsed_s=time.monotonic()-start);save(dest,record);print('PASS: eight fresh matched guard cases.',flush=True);return record
if __name__=='__main__':main()
