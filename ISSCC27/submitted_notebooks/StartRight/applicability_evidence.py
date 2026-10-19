"""Regenerate and remeasure the retained applicability successes and failures.
SPDX-License-Identifier: Apache-2.0
"""
import hashlib,io,json,zipfile
import numpy as np
from guard_consumer import HERE,save
from application_circuit import generate_application,measure_application
from guard_window import generate_window,measure_window,crossing_brackets
from sequence_evidence import normalize_deck

def load_vectors(item):
    with zipfile.ZipFile(HERE/'results/applicability/raw_evidence.zip') as z:blob=z.read(item['id']+'/vectors.npz')
    if hashlib.sha256(blob).hexdigest()!=item['vector_sha256']:raise ValueError('Saved applicability vectors differ')
    with np.load(io.BytesIO(blob),allow_pickle=False) as a:return a['vectors'].copy()

def audit():
    folder=HERE/'results/applicability';manifest=json.loads((folder/'evidence_manifest.json').read_text())
    archive=folder/'raw_evidence.zip';assert hashlib.sha256(archive.read_bytes()).hexdigest()==manifest['archive_sha256']
    rows=[]
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for name,digest in manifest['declaration_hashes'].items():assert hashlib.sha256(z.read(name)).hexdigest()==digest
        for item in manifest['cases']:
            prefix=item['id']+'/'
            for name,digest in item['raw_hashes'].items():assert hashlib.sha256(z.read(prefix+name)).hexdigest()==digest
            init=z.read(prefix+'.spiceinit').decode();assert 'set ngbehavior=hsa' in init and 'option sparse' in init
            if item['kind']=='window':text=generate_window(item['corner'],item['temp_C'],item['direction'],item['resistance_Mohm'])
            else:text,args=generate_application(item['history'],item['variant'],item['max_step_s'])
            assert normalize_deck(text)==normalize_deck(z.read(prefix+'input.cir').decode())
            d=load_vectors(item);assert list(d.shape)==item['shape'] and np.isfinite(d).all()
            if item['kind']=='window':
                q=measure_window(d);assert q==item['reference']
            else:
                q=measure_application(d,args,item['history']);reference=item['reference']
                assert q['reference']==reference['reference'] and q['qualified']==reference['qualified']
                for key in ('normal_storage_pass','reset_inactive_pass','supply_in_declared_band','minimum_q_V','minimum_reset_margin_V','final_q_V'):
                    if key in reference:assert q[key]==reference[key]
            row={k:v for k,v in item.items() if k not in ('reference','raw_hashes','scope')};row['result']=q
            if item['kind']=='window':row['crossing_brackets_V']=crossing_brackets(d)
            rows.append(row)
    assert len(rows)==72
    application=[r for r in rows if r['kind']=='application'];pairs=[]
    for group,history in dict.fromkeys((r['group'],r['history']) for r in application):
        members=[r for r in application if r['group']==group and r['history']==history]
        if len(members)!=2:continue
        old,new=[next(r for r in members if r['variant']==v) for v in ('original','digital_guard')]
        _,a=generate_application(history,'original',old['max_step_s']);_,b=generate_application(history,'digital_guard',new['max_step_s']);assert a==b
        eligible=old['result']['qualified'] and new['result']['qualified']
        work=lambda r:r['result']['reference']['source_work']['delivered_J']
        pairs.append(dict(group=group,history=history,both_working_for_energy=eligible,guard_relative_work_change=work(new)/work(old)-1 if eligible else None))
    from guard_evidence import audit as guard_audit,policy_evidence
    from guard_policy import choose
    evidence=policy_evidence(guard_audit());policyrows=list(evidence['rows'])
    for row in application:
        if row['group'] not in ('ripple','temperature'):continue
        q=row['result'];r=q['reference']
        policyrows.append(dict(condition=row['history'],variant=row['variant'],status='completed',cold_pass=r['events'][0]['pass_contract'],prior_verified=r['declared_precondition_verified'],functional_requirement_met=q['functional_requirement_met'],source_work_delivered_J=r['source_work']['delivered_J']))
    evidence=dict(status='audited',rows=policyrows);required=['slow_zero','warm_storage','shallow_depth','triangle']
    choices=dict(bounded=choose(evidence,required=required,anchor='slow_zero'),hot=choose(evidence,required=required+['hot_shallow_reset'],anchor='slow_zero'),cold=choose(evidence,required=required+['cold_storage'],anchor='slow_zero'))
    assert choices==dict(bounded='digital_guard',hot=None,cold=None)
    record=dict(status='passed',evidence_kind='saved data, no fresh simulation',complete_count=72,cases=rows,pairs=pairs,choices=choices,policy_rows=policyrows,scope=manifest['scope'])
    save(folder/'evidence_audit.json',record);print('PASS: all 72 applicability acquisitions regenerated and remeasured.',flush=True);return record

if __name__=='__main__':audit()
