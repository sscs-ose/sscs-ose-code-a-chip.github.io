"""Audit all accepted and unresolved published-reset-IP evidence offline.
SPDX-License-Identifier: Apache-2.0
"""
import hashlib,io,json,zipfile
import numpy as np
from por_consumer import HERE,save
from por_models import verify_sources,nominal_deck
from por_circuit import generate,measure
from reset_contract import source_work
from powered_reset import fixtures
from sequence_evidence import normalize_deck


def direct_verdict(data,windows):
    d=np.asarray(data);t=d[:,0]
    for window in windows:
        lo=window.ramp_end_s+.012;hi=window.stop_s;tx=np.unique(np.r_[lo,t[(t>lo)&(t<hi)],hi])
        q,c,dv,av=[np.interp(tx,t,d[:,col]) for col in [1,2,3,11]]
        if not (np.all(q<=.36) and np.all(c>=1.71) and np.all(dv>=1.71) and np.all(av>=3.135)):return False
    return True


def summary(rows):
    primary=[r for r in rows if r['kind']=='coupled' and r['acquisition_status']=='measured' and r['group']!='refined_domain_absolute']
    matrix=[]
    for event in ['none','analog_half','digital','analog','digital_zero','both']:
        a,b=[next(r for r in primary if r['domain']==event and r['command']==command) for command in [False,True]]
        matrix.append(dict(event=event,retained_pass=a['result']['observed_pass'],written_state_pass=b['result']['observed_pass'],prior_verified=b['result']['declared_precondition_verified'],
            powered_reset_witness=b['result']['powered_reset_witness']['observed'],final_q_V=b['result']['final_q_V']))
    refinement=[]
    for row in [r for r in rows if r['group']=='refined_domain_absolute']:
        old=next(r for r in primary if r['domain']==row['domain'] and r['command']);x,y=old['result'],row['result'];timing=[]
        for key in ['observed_pass','declared_precondition_verified','alternate_state_exercised','sampled_restoration_observed']:assert x[key]==y[key]
        for a,b in zip(x['events'],y['events']):
            for criterion in ['state','release']:
                u,v=a[criterion]['final_entry_s'],b[criterion]['final_entry_s'];assert (u is None)==(v is None)
                if u is not None:timing.append(abs(u-v))
        refinement.append(dict(event=row['domain'],max_entry_difference_s=max(timing),working_case_relative_work_difference=abs(x['source_work']['delivered_J']-y['source_work']['delivered_J'])/x['source_work']['delivered_J'] if x['observed_pass'] else None))
    return dict(matrix=matrix,refinement=refinement,scope='Finite source-specific integration requirements, not upstream guarantees, physical retention or an energy ranking across architectures. A conventional threshold check agrees on every complete coupled case.')


def audit():
    source=verify_sources();root=HERE/'results/por';manifest=json.loads((root/'evidence_manifest.json').read_text());archive=root/'raw_evidence.zip';rows=[]
    assert hashlib.sha256(archive.read_bytes()).hexdigest()==manifest['archive_sha256']
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for name,digest in manifest['declaration_hashes'].items():assert hashlib.sha256(z.read(name)).hexdigest()==digest
        for item in manifest['cases']:
            prefix=item['id']+'/'
            for name,digest in item['raw_hashes'].items():assert hashlib.sha256(z.read(prefix+name)).hexdigest()==digest
            if item['kind']=='nominal':text=nominal_deck(item['mapped'])
            else:text,ap,vp,dp,cp,windows=generate(item['domain'],item['command'],item['max_step_s'],item['profile'])
            assert normalize_deck(text)==normalize_deck(z.read(prefix+'input.cir').decode())
            assert 'option '+item['solver'] in z.read(prefix+'.spiceinit').decode()
            row={k:item[k] for k in ['id','group','kind','profile','solver','domain','command','max_step_s','acquisition_status']}
            if item['acquisition_status']=='measured':
                blob=z.read(prefix+'vectors.npz');assert hashlib.sha256(blob).hexdigest()==item['vector_sha256']
                with np.load(io.BytesIO(blob),allow_pickle=False) as npz:d=npz['vectors']
                if item['kind']=='nominal':
                    assert d.shape[1]==10 and np.isfinite(d).all() and abs(d[-1,0]-.020)<1e-12
                    hold=d[d[:,0]>=.019];released=bool(np.min(hold[:,1])>=3.135 and np.min(hold[:,2])>=1.71 and np.max(hold[:,3])<=.36)
                    result=dict(released_in_final_hold=released,source_work=source_work(d[:,0],dict(analog=(d[:,4],d[:,6]),digital=(d[:,5],d[:,7]))));assert released==item['reference']['released_in_final_hold']
                else:
                    result=measure(d,ap,vp,dp,cp,windows,item['command']);assert result['observed_pass']==direct_verdict(d,windows)
                    for key in ['observed_pass','declared_precondition_verified','alternate_state_exercised','sampled_restoration_observed']:assert result[key]==item['reference'][key]
                    assert result['powered_reset_witness']['observed']==item['reference']['powered_reset_witness']['observed']
                for key in ['delivered_J','returned_J','net_J']:assert abs(result['source_work'][key]-item['reference']['source_work'][key])<1e-20
                row['result']=result;row['vector_sha256']=item['vector_sha256']
            else:
                assert item['reference'] is None and item['reason'];row.update(result=None,reason=item['reason'])
            rows.append(row)
    complete=sum(r['acquisition_status']=='measured' for r in rows);assert len(rows)==31 and complete==17
    record=dict(status='passed',evidence_kind='saved data, no fresh simulation',complete_count=complete,unresolved_count=len(rows)-complete,cases=rows,source=source,summary=summary(rows),fixture=fixtures(),scope=manifest['scope'])
    save(root/'evidence_audit.json',record);print('PASS: 17 complete POR traces remeasured; 14 unresolved attempts retained.',flush=True);return record


def load_vectors(item):
    with zipfile.ZipFile(HERE/'results/por/raw_evidence.zip') as z:
        blob=z.read(item['id']+'/vectors.npz')
        if hashlib.sha256(blob).hexdigest()!=item['vector_sha256']:raise ValueError('Vector identity differs')
        with np.load(io.BytesIO(blob),allow_pickle=False) as d:return d['vectors'].copy()


if __name__=='__main__':audit()
