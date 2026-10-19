"""Repeat the declared ten-case subset of the frozen reference comparison.
SPDX-License-Identifier: Apache-2.0
"""
import concurrent.futures,hashlib,json,time
from reference_consumer import HERE,run_reference,save
from reference_evidence import audit
from check_reference import checks
SPEC=HERE/'reference_reproduction_spec.json'

def main():
    declaration=json.loads(SPEC.read_text(encoding='utf-8'))
    saved=audit();software_checks=checks(saved);start=time.perf_counter()
    jobs=declaration['jobs'];runs=[]
    record=dict(status='in_progress',declaration=declaration,declaration_sha256=hashlib.sha256(SPEC.read_bytes()).hexdigest(),saved_complete=saved['complete_count'],software_checks=software_checks,runs=runs)
    folder=HERE/'results/reproduction';folder.mkdir(exist_ok=True);output=folder/'reference_short.json';save(output,record)
    def acquire(job):return run_reference(case=job['case'],variant=job['variant'],group=job['group'],max_step=job['max_step_s'])
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        for r in pool.map(acquire,jobs):runs.append(r);save(output,record)
    if any(r['status']!='completed' for r in runs):
        record.update(status='has_unresolved',elapsed_seconds=time.perf_counter()-start);save(output,record);return 2
    for job,r in zip(jobs,runs):assert r['result']['diagnosis']==job['expected_diagnosis']
    prices=[]
    for case in ('nominal_storage','nominal_analog'):
        selected=[r for r in runs if r['case']==case]
        assert all(r['result']['qualified'] for r in selected)
        assert all(r['source_functions']==selected[0]['source_functions'] for r in selected)
        a=next(r for r in selected if r['variant']=='original');b=next(r for r in selected if r['variant']=='reference_supervisor')
        work=lambda r:r['result']['reference']['source_work']['delivered_J']
        change=work(b)/work(a)-1
        assert (change>0) if case=='nominal_storage' else (change<0)
        prices.append(dict(history=case,reference_relative_work_change=change,original_delivered_J=work(a),reference_delivered_J=work(b),both_working=True))
    record.update(status='passed',fresh_acquisitions=len(runs),working_comparisons=prices,elapsed_seconds=time.perf_counter()-start,
        scope='Ten deliberately selected development reproductions, not held-out tests or a full fresh matrix. Same frozen one-uA design. Nominal source-work anchors use one-us maximum step. Cold/hot action and benign cold trough use two us. Completed setup/functional misses are expected evidence, not execution errors. Every independent source is included; energy is compared only for working matched histories.')
    save(output,record);print('PASS: ten fresh reference-controller acquisitions.',flush=True);return 0
if __name__=='__main__':raise SystemExit(main())
