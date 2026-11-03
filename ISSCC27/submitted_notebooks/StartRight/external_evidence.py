"""Remeasure complete external-consumer traces; preserve unresolved verdicts.
SPDX-License-Identifier: Apache-2.0
"""
import hashlib,io,json,zipfile
import numpy as np
from external_consumer import HERE,generate,measure,verify_external_sources,save
from sequence_evidence import normalize_deck
from external_analysis import numerical_summary


def load_vectors(case):
    with zipfile.ZipFile(HERE/'results/external/raw_evidence.zip') as z:
        with np.load(io.BytesIO(z.read(case['id']+'/vectors.npz')),allow_pickle=False) as arrays:
            return arrays['vectors']


def audit():
    sources=verify_external_sources();root=HERE/'results/external';manifest=json.loads((root/'evidence_manifest.json').read_text());archive=root/'raw_evidence.zip'
    assert hashlib.sha256(archive.read_bytes()).hexdigest()==manifest['archive_sha256']
    rows=[]
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for item in manifest['cases']:
            prefix=item['id']+'/'
            for name,digest in item['raw_hashes'].items():assert hashlib.sha256(z.read(prefix+name)).hexdigest()==digest
            text,points,windows,dp,cp=generate(item['configuration'],item['scenario'],item['contract'],item['settings'],item.get('absolute_tolerances'))
            assert normalize_deck(text)==normalize_deck(z.read(prefix+'input.cir').decode())
            assert 'option '+item['solver'] in z.read(prefix+'.spiceinit').decode()
            row={k:item[k] for k in ['id','group','selection','solver','settings','configuration','scenario','contract','acquisition_status','absolute_tolerances']}
            if item['acquisition_status']=='measured':
                blob=z.read(prefix+'vectors.npz');assert hashlib.sha256(blob).hexdigest()==item['vector_sha256']
                with np.load(io.BytesIO(blob),allow_pickle=False) as data:
                    result=measure(data['vectors'],item['configuration'],item['scenario'],item['contract'],points,windows,dp,cp)
                for key in ['observed_pass','declared_precondition_verified','alternate_state_exercised','sampled_restoration_observed']:assert result[key]==item['reference'][key]
                for key in ['delivered_J','returned_J','net_J']:assert abs(result['source_work'][key]-item['reference']['source_work'][key])<1e-21
                row['result']=result
            else:
                assert item['reference_observed_pass'] is None and item['reason']
                row.update(result=dict(status='unresolved',observed_pass=None,sampled_restoration_observed=None),reason=item['reason'])
            rows.append(row)
    record=dict(status='passed',evidence_kind='saved-data audit; no fresh SPICE',cases=rows,source_check=sources,selection=manifest['selection'],scope=manifest['scope'])
    record['numerical_comparison']=numerical_summary(rows)
    save(root/'numerical_comparison.json',record['numerical_comparison'])
    save(root/'evidence_audit.json',record)
    print('PASS: external source/deck/data audit:',sum(r['acquisition_status']=='measured' for r in rows),'complete,',sum(r['acquisition_status']=='unresolved' for r in rows),'unresolved attempts retained.',flush=True)
    return record


if __name__=='__main__':audit()
