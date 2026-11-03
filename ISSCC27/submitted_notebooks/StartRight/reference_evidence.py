"""Regenerate and remeasure the preserved reference-supervisor study.
SPDX-License-Identifier: Apache-2.0
"""
from pathlib import Path
import hashlib,io,json,zipfile
import numpy as np
import reference_devices as dev,reference_loop as loop,reference_circuit as app
from guard_policy import choose
from guard_consumer import save
from sequence_evidence import normalize_deck
HERE=Path(__file__).resolve().parent
FOLDER=HERE/'results/reference'
sha=lambda b:hashlib.sha256(b).hexdigest()

def load_vectors(row):
    with zipfile.ZipFile(FOLDER/row['archive']) as z:b=z.read(row['id']+'/vectors.npz')
    if sha(b)!=row['vector_sha256']:raise ValueError('Reference vectors differ')
    with np.load(io.BytesIO(b),allow_pickle=False) as a:return a['vectors'].copy()

def policy_evidence(record):
    rows=[]
    for r in record['cases']:
        if r['kind']!='application' or not (r['id'].startswith('primary/') or r.get('group')=='trough'):continue
        q=r['result'];ref=q['reference']
        functional=q['normal_storage_pass'] and q['reset_inactive_pass'] if q['storage_requirement'] else ref['observed_pass']
        condition=('trough_' if r['group']=='trough' else '')+r['case']
        rows.append(dict(condition=condition,variant=r['variant'],status='completed',cold_pass=ref['events'][0]['pass_contract'],
            prior_verified=ref['declared_precondition_verified'],functional_requirement_met=functional,
            source_work_delivered_J=ref['source_work']['delivered_J']))
    for r in record['cases']:
        if r.get('group')=='step' and r['case'] in ('nominal_storage','nominal_analog'):
            target=next(q for q in rows if q['condition']==r['case'] and q['variant']==r['variant'])
            target['source_work_delivered_J']=r['result']['reference']['source_work']['delivered_J']
    return dict(status='audited',rows=rows)

def audit():
    sources=dev.provenance();manifest=json.loads((FOLDER/'evidence_manifest.json').read_text(encoding='utf-8'));rows=[]
    for archive,expected in manifest['archives'].items():
        path=FOLDER/archive;assert sha(path.read_bytes())==expected['sha256'] and path.stat().st_size==expected['bytes']
        with zipfile.ZipFile(path) as z:
            assert z.testzip() is None
            for name,digest in manifest['declarations'][archive].items():assert sha(z.read(name))==digest
            for item in [r for r in manifest['cases'] if r['archive']==archive]:
                prefix=item['id']+'/'
                for name,digest in item['raw_hashes'].items():assert sha(z.read(prefix+name))==digest
                assert 'option sparse' in z.read(prefix+'.spiceinit').decode()
                d=load_vectors(item);assert list(d.shape)==item['shape'] and np.isfinite(d).all()
                if item['kind']=='characterization':
                    text=dev.char_deck(item['nominal_current_uA'],item['temp_C']);assert d.shape==(1,4)
                    q=dict(vbe_unit_V=float(d[0,1]),vbe_eight_V=float(d[0,2]),delta_V=float(d[0,1]-d[0,2]),supply_current_A=float(-d[0,3]))
                    assert abs(q['supply_current_A']-2*item['nominal_current_uA']*1e-6*(item['temp_C']+273.15)/300.15)<1e-12
                elif item['kind']=='loop':text=loop.build(item['temp_C'],item['startup']);q=loop.measure(d)
                else:
                    text,args=app.generate(item['case'],item['variant'],item['max_step_s'],item['group'])
                    q=app.measure_application(d,args,item['case'],item['variant'])
                    if 'source_functions' in item:assert item['source_functions']==dict(analog=args[0],digital=args[1],data=args[2],clock=args[3])
                assert normalize_deck(text)==normalize_deck(z.read(prefix+'input.cir').decode())
                assert q==item['reference'],item['id']
                rows.append({**{k:v for k,v in item.items() if k not in ('reference','raw_hashes')},'result':q})
    assert len(rows)==56
    summary=manifest['failed_adapter_attempt']
    counts={status:sum(r['status']==status for r in summary['rows']) for status in set(r['status'] for r in summary['rows'])}
    assert counts==dict(completed=3,generation_failed_before_SPICE=3,not_started_after_adapter_error=8)
    with zipfile.ZipFile(FOLDER/'components_evidence.zip') as z:
        assert sha(z.read('original_sources/reference_supervisor_pilot.py'))==summary['source_sha256']
    with zipfile.ZipFile(FOLDER/'adapter_evidence.zip') as z:
        for r in summary['rows']:
            if r['status']=='generation_failed_before_SPICE':
                prefix='failed_generation/'+r['case']+'_'+r['variant']+'/'
                assert not any(n.startswith(prefix) and n.endswith(('input.cir','history.dat')) for n in z.namelist())
    # Pin the development fit to the acquired one-uA characterization values.
    fitted=loop.fit();char={r['temp_C']:r for r in rows if r['kind']=='characterization' and r['nominal_current_uA']==1.}
    k=(char[-40]['result']['vbe_unit_V']-char[125]['result']['vbe_unit_V'])/(char[125]['result']['delta_V']-char[-40]['result']['delta_V'])
    assert fitted['ratio']==k and fitted['R1_ohm']==char[27]['result']['delta_V']/1e-6
    for temp,r in char.items():assert fitted['characterization_raw_hashes'][str(temp)]==r['original_text_sha256']
    record=dict(status='passed',evidence_kind='saved audit, no SPICE execution',complete_count=56,cases=rows,
        failed_adapter_attempt=manifest['failed_adapter_attempt'],source_verification=sources,scope=manifest['scope'])
    e=policy_evidence(record)
    record['choices']=dict(limited=choose(e,required=['nominal_storage'],anchor='nominal_storage'),
        nominal_reset=choose(e,required=['nominal_storage','nominal_shallow'],anchor='nominal_storage'),
        expanded=choose(e,required=['nominal_storage','hot_shallow','cold_shallow','trough_cold_storage','trough_hot_storage'],anchor='nominal_storage'),
        unmeasured=choose(e,required=['nominal_storage','unmeasured_short_zero'],anchor='nominal_storage'))
    assert record['choices']==dict(limited='original',nominal_reset='digital_guard',expanded='reference_supervisor',unmeasured=None)
    save(FOLDER/'evidence_audit.json',record)
    print('PASS: all 56 saved reference acquisitions regenerated and remeasured.',flush=True)
    return record
if __name__=='__main__':audit()
