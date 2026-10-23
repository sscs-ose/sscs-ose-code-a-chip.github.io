"""Eight fresh application/DC acquisitions, including known functional misses.
SPDX-License-Identifier: Apache-2.0
"""
from concurrent.futures import ThreadPoolExecutor,as_completed
import platform,sys,time
from applicability_consumer import HERE,acquire,save
from applicability_evidence import audit
from check_applicability import checks

def main():
    saved=audit();fixtures=checks(saved)
    jobs=[]
    for variant in ['original','digital_guard']:
        jobs.extend([dict(history='triangle',variant=variant),dict(history='hot_shallow_reset',variant=variant,max_step=1e-6 if variant=='digital_guard' else 2e-6),
            dict(history='cold_storage',variant=variant,max_step=1e-6 if variant=='original' else 2e-6)])
    jobs.extend([dict(kind='window',corner=c) for c in ['tt','fs']])
    record=dict(status='in_progress',python=sys.version.split()[0],platform=platform.platform(),jobs=jobs,runs=[],saved_complete=72,fixture_checks=fixtures,
        scope='Six fresh intact TT-temperature cases and two fresh isolated DC sweeps. Includes known hot reset misses and cold unestablished prior states. These are deliberate regression repeats, not unseen tests. Wider 72-case study is saved Windows data. No independent-machine, noise, silicon, energy superiority or publication claim.')
    dest=HERE/'results/reproduction/applicability_short.json';save(dest,record);start=time.monotonic()
    with ThreadPoolExecutor(max_workers=2) as pool:
        for future in as_completed([pool.submit(acquire,**job) for job in jobs]):record['runs'].append(future.result());save(dest,record)
    assert len(record['runs'])==8 and all(r['status']=='completed' for r in record['runs'])
    for row in record['runs']:
        q=row['result'];settings=row['settings']
        if row['kind']=='application':
            expected={'triangle':'requirement_met','cold_storage':'not_exercised_cold_start','hot_shallow_reset':'functional_requirement_missed'}[settings['history']]
            assert q['diagnosis']==expected
        else:
            assert q['asserted_at_1p35'] and q['released_at_1p62']
            assert len(q['high_band_crossings_V'])==(2 if settings['corner']=='fs' else 1)
    for history in ['triangle','cold_storage','hot_shallow_reset']:
        pair=[r for r in record['runs'] if r['kind']=='application' and r['settings']['history']==history]
        assert len(pair)==2 and pair[0]['source_functions']==pair[1]['source_functions']
    record.update(status='passed',elapsed_s=time.monotonic()-start);save(dest,record);print('PASS: eight fresh applicability acquisitions with distinct failure diagnoses.',flush=True);return record
if __name__=='__main__':main()
