"""Data-fixture controls for the external-consumer adapter, not SPICE trials.
SPDX-License-Identifier: Apache-2.0
"""
import json,io,contextlib
from unittest.mock import patch
import external_consumer
import numpy as np
from external_consumer import HERE,generate,measure
from external_evidence import load_vectors


def checks():
    items=json.loads((HERE/'results/external/evidence_manifest.json').read_text())['cases']
    item=next(r for r in items if r['group']=='common_tt_gear_rt1e-06_dt2us' and r['solver']=='sparse' and r['configuration']['variant']=='supply_sensitive' and not r['scenario']['normal_set'].get('skip_command'))
    original=load_vectors(item);_,points,windows,dp,cp=generate(item['configuration'],item['scenario'],item['contract'],item['settings'])
    def evaluate(data):return measure(data,item['configuration'],item['scenario'],item['contract'],points,windows,dp,cp)
    positive=evaluate(original);assert positive['observed_pass'] and positive['sampled_restoration_observed']
    tested=['complete reference normal-operation trace qualifies the declared prior state and restoration']
    synthetic=original.copy();before=points[4][0]-1e-7;mask=(synthetic[:,0]>=before-6e-6)&(synthetic[:,0]<=before+1e-8);synthetic[mask,1]=0.
    r=evaluate(synthetic);assert r['observed_pass'] and not r['declared_precondition_verified'] and not r['sampled_restoration_observed']
    tested.append('a passing result after an unwritten prior state is not promoted into restoration coverage')
    rejected=0
    variants=[]
    bad=original.copy();bad[:,5]=0.;variants.append(bad)
    bad=original.copy();bad[:,6]=0.;variants.append(bad)
    bad=original.copy();bad[10,4]=np.nan;variants.append(bad)
    variants.append(original[:,:10])
    variants.append(original[original[:,0]<points[-1][0]-1e-3])
    for data in variants:
        try:evaluate(data)
        except ValueError:rejected+=1
    assert rejected==5
    tested.append('absent clock/data commands, nonfinite source current, missing vectors and truncated observation rejected')
    with patch('sys.argv',['external_consumer.py']),contextlib.redirect_stdout(io.StringIO()):
        with patch('external_consumer.run_external',return_value=dict(status='has_unresolved',output_dir='data fixture, no acquisition')):
            assert external_consumer.main()==2
        with patch('external_consumer.run_external',return_value=dict(status='completed',output_dir='data fixture, no acquisition',cases=[dict(observed_pass=False)])):
            assert external_consumer.main()==0
    tested.append('CLI distinguishes incomplete acquisition from a completed failed-circuit experiment')
    return tested


if __name__=='__main__':
    for result in checks():print('PASS:',result)
