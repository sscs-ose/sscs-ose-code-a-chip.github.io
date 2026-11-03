"""Hand-computed checks for coverage, threshold crossings and source accounting.
SPDX-License-Identifier: Apache-2.0
"""
import copy
import numpy as np
from reset_contract import Band, Window, evaluate, source_work


def checks():
    t = np.array([0., 1., 2., 3., 4.])
    v = dict(vdd=np.array([0., 1., 1., 1., 1.]), q=np.array([0., 0., 0., 1., 1.]), reset_n=np.array([0., 0., 0., 1., 1.]))
    options = dict(supply_points=[[0., 0.], [1., 1.], [4., 1.]], windows=[Window('recovery', 1., 2., 4.)],
                   state_bands=[Band('vdd', lower=.95), Band('q', lower=.8)], release_bands=[Band('reset_n', lower=.95)],
                   state_delay_s=1., release_delay_s=1., hold_s=1., precondition_interval=(1., 2.),
                   prior_bands=[Band('q', upper=.2)], alternate_bands=[Band('q', upper=.2)])
    r = evaluate(t, v, **options)
    assert r['observed_pass'] and r['sampled_restoration_observed']
    assert abs(r['events'][0]['state']['final_entry_s']-2.8) < 1e-12
    assert abs(r['events'][0]['release']['final_entry_s']-2.95) < 1e-12
    tests = ['one-node reuse example and hand-computed state/release crossings']
    retained = copy.deepcopy(v); retained['q'][:] = 1
    k = dict(options, prior_bands=[Band('q', lower=.8)])
    r = evaluate(t, retained, **k)
    assert r['observed_pass'] and r['declared_precondition_verified'] and not r['alternate_state_exercised'] and not r['sampled_restoration_observed']
    tests.append('a valid retained-state pass does not become restoration coverage')
    late = copy.deepcopy(v); late['q'][3] = 0.
    assert not evaluate(t, late, **options)['observed_pass']
    bad_prior = copy.deepcopy(v); bad_prior['q'][1] = .5
    r = evaluate(t, bad_prior, **options)
    assert r['observed_pass'] and not r['declared_precondition_verified'] and not r['sampled_restoration_observed']
    tests.append('late state and incorrect prior state cannot qualify restoration')
    # Both individual bounds enter at 0.8. The sampled minimum would enter at
    # 0.8333 because a different bound is active at each endpoint.
    x = dict(vdd=np.ones(5), x=np.array([0., 1., 1., 1., 1.]), y=np.array([-.8, .2, .2, .2, .2]))
    kw = dict(options, supply_points=[[0., 1.], [4., 1.]], windows=[Window('cold', 0., 0., 4.)],
              state_bands=[Band('x', lower=.8), Band('y', lower=0.)], release_bands=[Band('x', lower=.8)],
              precondition_interval=None)
    r = evaluate(t, x, **kw)
    assert abs(r['events'][0]['state']['final_entry_s']-.8) < 1e-12
    tests.append('separate bound interpolation handles changing active constraints')
    rejected = 0
    for tm, sig, kwarg in [(t[:-1], {n:a[:-1] for n,a in v.items()}, options),
                           (np.array([0., 1., 1., 3., 4.]), v, options),
                           (t, dict(v, q=np.array([0., 0., np.nan, 1., 1.])), options),
                           (t, v, dict(options, release_delay_s=3.)),
                           (t, v, dict(options, state_bands=[])),
                           (t, v, dict(options, state_bands=[Band('missing', lower=0)]))]:
        try:
            evaluate(tm, sig, **kwarg)
        except ValueError:
            rejected += 1
    assert rejected == 6
    tests.append('truncated, duplicate, nonfinite, unobserved and undeclared data rejected')
    work = source_work(np.array([0., 1., 2.]), dict(main=(np.ones(3), np.array([-2., 0., 2.])), input=(2*np.ones(3), -np.ones(3))))
    assert work['sources']['main'] == dict(delivered_J=1., returned_J=1., net_J=0.)
    assert work['delivered_J'] == 5. and work['returned_J'] == 1. and work['net_J'] == 4.
    tests.append('independent input work, delivery and returned energy counted by hand')
    return tests


if __name__ == '__main__':
    for item in checks():
        print('PASS:', item)
