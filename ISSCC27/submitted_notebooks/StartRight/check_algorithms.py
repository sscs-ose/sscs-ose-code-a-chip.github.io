"""Check root boundary handling and rejection before interpreting DC data."""
import numpy as np
from unittest.mock import patch
from pilot import HERE
from widlar_pilot import find_roots,audit_return_case
from circuits import CIRCUITS
from startright import verify_circuit

x=np.linspace(0,1,5)
for returned,expected in [(np.full_like(x,.5),[.5]),(np.zeros_like(x),[0]),(np.ones_like(x),[1]),(np.full_like(x,.3),[.3]),(x+x*(x-.5)*(x-1),[0,.5,1])]:
    roots=find_roots(np.column_stack([x,returned]))
    assert np.allclose([r['vin_V'] for r in roots],expected)
    assert np.allclose([r['vin_V'] for r in find_roots(np.column_stack([x,returned])[::-1])],expected)
for data in [np.column_stack([x,x]),np.array([[0,1],[0,2]]),np.array([[0,np.nan],[1,1]])]:
    try:find_roots(data)
    except ValueError:pass
    else:raise AssertionError('Ambiguous or invalid curve was accepted.')
fixture=HERE/'results/fixtures/rejected_contact'
assert not audit_return_case(fixture)['accepted']
with patch('startright.verify_models',return_value={'scope':'test fixture; no simulation'}),patch('startright.simulate',return_value=fixture) as simulator:
    rejected=verify_circuit(CIRCUITS['beta_multiplier'],load_resistance=123456)
    assert rejected['status']=='rejected_dc_data'
    assert 'candidate_operating_points' not in rejected and 'loaded_test' not in rejected
    assert simulator.call_count==1
print('PASS: exact and endpoint roots, reversed curves, invalid curves and early rejection of real invalid DC output.')
