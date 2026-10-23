"""Reproduce the full finite matrix with fresh simulations, including failures.
SPDX-License-Identifier: Apache-2.0
"""
from concurrent.futures import ThreadPoolExecutor,as_completed
import platform,sys,time
from por_consumer import HERE,run_por,save
from por_circuit import EVENTS
from por_evidence import audit
from check_por import checks


def main():
    saved=audit();fixture_checks=checks();jobs=[dict(event=event,command=command) for event in EVENTS for command in [False,True]];begin=time.monotonic()
    record=dict(status='in_progress',fixture_checks=fixture_checks,python=sys.version.split()[0],platform=platform.platform(),jobs=jobs,runs=[],saved_complete=saved['complete_count'],saved_unresolved=saved['unresolved_count'],
        scope='Twelve fresh TT/27 C dual-rail acquisitions, six events at two prior states. Several reset-state failures are expected reproduced results; no-dip Q=1 is healthy storage behavior. No saved substitute, upstream defect, energy superiority or physical retention claim.')
    dest=HERE/'results/reproduction/por_short.json';save(dest,record)
    with ThreadPoolExecutor(max_workers=2) as pool:
        for future in as_completed([pool.submit(run_por,**job) for job in jobs]):
            record['runs'].append(future.result());save(dest,record)
    assert len(record['runs'])==12 and all(r['status']=='completed' for r in record['runs'])
    for run in record['runs']:
        result=run['result'];restores=run['event'] in ['analog','both']
        assert result['declared_precondition_verified'] and result['alternate_state_exercised']==run['command']
        assert result['events'][0]['pass_contract'] and result['events'][1]['release']['pass_contract']
        assert result['observed_pass']==(not run['command'] or restores)
        assert result['powered_reset_witness']['observed']==restores
        if run['event']=='none':assert run['normal_storage_control_pass']
    record.update(status='passed',elapsed_s=time.monotonic()-begin);save(dest,record);print('PASS: complete fresh POR/DFF supply-event matrix.',flush=True);return record


if __name__=='__main__':main()
