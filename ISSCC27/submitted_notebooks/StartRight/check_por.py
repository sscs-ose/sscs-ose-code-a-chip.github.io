"""Data-quality fixtures for the additional supply and source-current vectors.
SPDX-License-Identifier: Apache-2.0
"""
import contextlib,io,json
from unittest.mock import patch
import numpy as np
import por_consumer
from por_consumer import HERE
from por_circuit import generate,measure
from por_evidence import load_vectors
from powered_reset import fixtures


def checks():
    items=json.loads((HERE/'results/por/evidence_manifest.json').read_text())['cases']
    item=next(r for r in items if r['group']=='common_domain_absolute' and r['domain']=='analog' and r['command'] and r['solver']=='sparse')
    data=load_vectors(item);_,ap,vp,dp,cp,windows=generate(item['domain'],item['command'],item['max_step_s'],item['profile'])
    def check(d):return measure(d,ap,vp,dp,cp,windows,item['command'])
    result=check(data);assert result['sampled_restoration_observed'] and set(result['source_work']['sources'])=={'analog','digital','clock','data'}
    bad=[]
    x=data.copy();x[100,11]+=.01;bad.append(x)
    x=data.copy();x[100,12]=np.nan;bad.append(x)
    bad.append(data[:,:15])
    for x in bad:
        try:check(x)
        except ValueError:pass
        else:raise AssertionError('Incomplete/contradictory supply or current accepted')
    with patch('sys.argv',['por_consumer.py']),contextlib.redirect_stdout(io.StringIO()):
        for status,expected in [('completed',0),('unresolved',2)]:
            with patch('por_consumer.run_por',return_value=dict(status=status,output_dir='fixture, no acquisition')):assert por_consumer.main()==expected
    return ['Secondary supply mismatch, nonfinite analog-source current and missing vector rejected.',fixtures(),'CLI distinguishes a complete experiment from unresolved acquisition.']


if __name__=='__main__':
    for result in checks():print('PASS:',result)
