"""Audit the complete saved finite sizing study before selecting or plotting.
SPDX-License-Identifier: Apache-2.0
"""
import copy,hashlib,io,json,zipfile
import numpy as np
from external_consumer import HERE,generate,measure,save,verify_external_sources
from sequence_evidence import normalize_deck
from detector_design import choose


def summarize(rows):
    pilot=[r for r in rows if r['group']=='detector_scaling_tt']
    selected=choose(pilot);assert selected==4
    # Fixture controls: a cheap but invalid candidate cannot win.
    bad=copy.deepcopy(pilot)
    next(r for r in bad if r['scale']==4 and r['history']=='no_dip')['result']['minimum_q_final_hold_V']=0.
    assert choose(bad)==2
    assert choose([r for r in pilot if r['history']!='normal']) is None
    bad=copy.deepcopy(pilot);bad[0]['comparison_id']='different experiment'
    try:choose(bad)
    except ValueError:pass
    else:raise AssertionError('Mixed comparisons accepted')
    comparisons=[]
    for condition in ['tt_nominal','sf_27','tt_85','tt_low_supply','tt_high_supply']:
        group='detector_scaling_tt' if condition=='tt_nominal' else 'detector_challenge_frozen_v2'
        cohort=[r for r in rows if r['group']==group and r['comparison_id']==condition]
        assert choose(cohort)==selected
        for history in ['retained','normal']:
            a,b=[next(r for r in cohort if r['history']==history and r['scale']==scale) for scale in [1,selected]]
            for key in ['scenario','contract','settings','absolute_tolerances']:assert a[key]==b[key]
            ca,cb=[{k:v for k,v in r['configuration'].items() if k!='detector_scale'} for r in [a,b]];assert ca==cb
            x,y=a['result'],b['result'];assert x['eligible_delivered_J'] is not None and y['eligible_delivered_J'] is not None
            comparisons.append(dict(condition=condition,history=history,reference_delivered_J=x['source_work']['delivered_J'],selected_delivered_J=y['source_work']['delivered_J'],
                reduction_fraction=1-y['source_work']['delivered_J']/x['source_work']['delivered_J'],extra_release_delay_s=y['events'][-1]['release']['final_entry_s']-x['events'][-1]['release']['final_entry_s']))
    refinement=[]
    for row in [r for r in rows if r['group']=='detector_scaling_refined']:
        group='detector_scaling_tt' if row['comparison_id']=='tt_nominal' else 'detector_challenge_frozen_v2'
        reference=next(r for r in rows if r['group']==group and r['comparison_id']==row['comparison_id'] and r['scale']==row['scale'] and r['history']==row['history'])
        x,y=reference['result'],row['result']
        for key in ['observed_pass','declared_precondition_verified','alternate_state_exercised','sampled_restoration_observed']:assert x[key]==y[key]
        if x['eligible_delivered_J'] is not None:refinement.append(abs(x['source_work']['delivered_J']-y['source_work']['delivered_J'])/x['source_work']['delivered_J'])
    return dict(selected_scale=selected,comparisons=comparisons,maximum_refined_work_difference=max(refinement),selection_fixtures='Invalid no-dip candidate excluded, missing history abstains, mixed comparison rejected.',
        scope='Finite conventional constrained search. Selection uses the original nine-case TT pilot only. Later cases check that frozen choice; SF was previously explored for the original. No continuous PVT, optimum, optimized-reference or physical-area claim.')


def audit():
    verify_external_sources();root=HERE/'results/scaling';manifest=json.loads((root/'evidence_manifest.json').read_text());archive=root/'raw_evidence.zip'
    assert hashlib.sha256(archive.read_bytes()).hexdigest()==manifest['archive_sha256'];rows=[]
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for name,digest in manifest['declaration_hashes'].items():assert hashlib.sha256(z.read(name)).hexdigest()==digest
        for item in manifest['cases']:
            prefix=item['id']+'/'
            for name,digest in item['raw_hashes'].items():assert hashlib.sha256(z.read(prefix+name)).hexdigest()==digest
            assert 'option sparse' in z.read(prefix+'.spiceinit').decode()
            text,points,windows,dp,cp=generate(item['configuration'],item['scenario'],item['contract'],item['settings'],item['absolute_tolerances'])
            assert normalize_deck(text)==normalize_deck(z.read(prefix+'input.cir').decode())
            blob=z.read(prefix+'vectors.npz');assert hashlib.sha256(blob).hexdigest()==item['vector_sha256']
            with np.load(io.BytesIO(blob),allow_pickle=False) as data:result=measure(data['vectors'],item['configuration'],item['scenario'],item['contract'],points,windows,dp,cp)
            for key in ['observed_pass','declared_precondition_verified','alternate_state_exercised','sampled_restoration_observed']:assert result[key]==item['reference'][key]
            for key in ['delivered_J','returned_J','net_J']:assert abs(result['source_work'][key]-item['reference']['source_work'][key])<1e-21
            row={k:item[k] for k in ['id','group','scale','history','comparison_id','configuration','scenario','contract','settings','absolute_tolerances']}
            row.update(result=result,supply_V=item['scenario']['supply_V']);rows.append(row)
    assert len(rows)==51
    record=dict(status='passed',evidence_kind='saved-data audit, no fresh simulation',cases=rows,summary=summarize(rows),scope=manifest['scope'])
    save(root/'evidence_audit.json',record);print('PASS: 51 complete sizing traces remeasured; frozen choice and refinement checked.',flush=True);return record


if __name__=='__main__':audit()
