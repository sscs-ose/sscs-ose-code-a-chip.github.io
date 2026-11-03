"""Audit every retained guard trace and its finite design decision.
SPDX-License-Identifier: Apache-2.0
"""
import copy,hashlib,io,json,zipfile
import numpy as np
from guard_consumer import HERE,save
from guard_circuit import generate,generate_condition,CONDITIONS
from por_circuit import measure
from por_evidence import direct_verdict
from sequence_evidence import normalize_deck

def load_vectors(item):
    with zipfile.ZipFile(HERE/'results/guard/raw_evidence.zip') as z:blob=z.read(item['id']+'/vectors.npz')
    if hashlib.sha256(blob).hexdigest()!=item['vector_sha256']:raise ValueError('Saved vectors differ')
    with np.load(io.BytesIO(blob),allow_pickle=False) as a:return a['vectors'].copy()

def policy_evidence(record):
    rows=copy.deepcopy(record['primary'])
    for row in rows:
        if row['condition']=='slow_zero':
            fine=next(c for c in record['cases'] if c['group']=='refinement' and c['condition']=='slow_zero' and c['variant']==row['variant'])
            assert fine['result']['observed_pass'] and fine['result']['declared_precondition_verified']
            row['source_work_delivered_J']=fine['result']['source_work']['delivered_J']
    return dict(status='audited',rows=rows,scope='Primary qualification with a common refined 1 us slow-recovery source-work anchor. Post-hoc teaching policies, not lifetime energy or new experiments.')

def audit():
    folder=HERE/'results/guard';manifest=json.loads((folder/'evidence_manifest.json').read_text());archive=folder/'raw_evidence.zip';rows=[]
    assert hashlib.sha256(archive.read_bytes()).hexdigest()==manifest['archive_sha256']
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for name,digest in manifest['declaration_hashes'].items():assert hashlib.sha256(z.read(name)).hexdigest()==digest
        for item in manifest['cases']:
            prefix=item['id']+'/'
            for name,digest in item['raw_hashes'].items():assert hashlib.sha256(z.read(prefix+name)).hexdigest()==digest
            if item['group']=='pilot':text,args=generate(item['event'],item['command'],item['variant'],item['max_step_s'])
            else:text,args=generate_condition(item['condition'],item['variant'],item['max_step_s'])
            assert normalize_deck(text)==normalize_deck(z.read(prefix+'input.cir').decode())
            blob=z.read(prefix+'vectors.npz');assert hashlib.sha256(blob).hexdigest()==item['vector_sha256']
            with np.load(io.BytesIO(blob),allow_pickle=False) as a:d=a['vectors']
            assert d.shape[1]==(19 if item['variant']=='digital_guard' else 16) and np.isfinite(d).all()
            q=measure(d[:,:16],*args,item['command']);reference=item['reference']
            for key in ['observed_pass','declared_precondition_verified','alternate_state_exercised','sampled_restoration_observed']:assert q[key]==reference[key]
            assert q['observed_pass']==direct_verdict(d[:,:16],args[-1])
            assert q['powered_reset_witness']['observed']==reference['powered_reset_witness']['observed']
            for key in ['delivered_J','returned_J','net_J']:assert abs(q['source_work'][key]-reference['source_work'][key])<1e-18
            row={k:item[k] for k in ['id','group','condition','event','command','variant','max_step_s','vector_sha256']};row.update(result=q,source_functions=dict(analog=args[0],digital=args[1],data=args[2],clock=args[3]));rows.append(row)
    assert len(rows)==22
    primary=[]
    for row in [r for r in rows if r['group']=='challenge']:
        q=row['result'];storage=CONDITIONS[row['condition']]['storage'];met=q['minimum_q_final_hold_V']>=1.44 if storage else q['observed_pass']
        primary.append(dict(condition=row['condition'],variant=row['variant'],status='completed',cold_pass=q['events'][0]['pass_contract'],prior_verified=q['declared_precondition_verified'],functional_requirement_met=bool(met),qualified=bool(met and q['events'][0]['pass_contract'] and q['declared_precondition_verified']),source_work_delivered_J=q['source_work']['delivered_J']))
    pairs=[]
    for condition in CONDITIONS:
        a,b=[next(r for r in primary if r['condition']==condition and r['variant']==v) for v in ['original','digital_guard']]
        old,new=[next(r for r in rows if r['group']=='challenge' and r['condition']==condition and r['variant']==v) for v in ['original','digital_guard']]
        assert old['source_functions']==new['source_functions']
        eligible=a['qualified'] and b['qualified'];pairs.append(dict(condition=condition,original_qualified=a['qualified'],guard_qualified=b['qualified'],working_relative_work_change=b['source_work_delivered_J']/a['source_work_delivered_J']-1 if eligible else None))
    refinement=[]
    for row in [r for r in rows if r['group']=='refinement']:
        old=next(r for r in rows if r['group']=='challenge' and r['condition']==row['condition'] and r['variant']==row['variant']);a,b=old['result'],row['result']
        assert old['source_functions']==row['source_functions']
        for key in ['observed_pass','declared_precondition_verified','alternate_state_exercised','sampled_restoration_observed']:assert a[key]==b[key]
        assert a['powered_reset_witness']['observed']==b['powered_reset_witness']['observed']
        refinement.append(dict(condition=row['condition'],variant=row['variant'],classifications_agree=True,working_relative_work_difference=abs(a['source_work']['delivered_J']-b['source_work']['delivered_J'])/max(a['source_work']['delivered_J'],b['source_work']['delivered_J']) if a['observed_pass'] and b['observed_pass'] else None))
    record=dict(status='passed',evidence_kind='saved data, no fresh simulation',complete_count=22,cases=rows,primary=primary,pairs=pairs,refinement=refinement,scope=manifest['scope'])
    save(folder/'evidence_audit.json',record);print('PASS: all 22 guard traces regenerated and remeasured.',flush=True);return record
if __name__=='__main__':audit()
