"""Analytically specified synthetic monitor tests; not real circuit defects."""
import unittest
from dataclasses import replace
from pathlib import Path
import numpy as np
from functional import FunctionalContract, assess_function
from evidence import assess_run


class FunctionalTests(unittest.TestCase):
    def setUp(self):
        self.t = np.arange(0, 4.001, .001) * 1e-3
        self.v = np.minimum(self.t/.001, 1)*3.3
        self.c = FunctionalContract()

    def response(self, when=None):
        if when is None:
            return np.zeros_like(self.t)
        # Linear 2 us ramp centered on the analytically known crossing.
        return np.clip((self.t-when+1e-6)/2e-6, 0, 1)*1.8

    def run_case(self, when=None, stop=None, supply=None, contract=None):
        mask = self.t <= (stop if stop is not None else 1)
        return assess_function(self.t[mask], (self.v if supply is None else supply)[mask],
                               self.response(when)[mask], contract or self.c)

    def test_timely_response(self):
        r = self.run_case(.0015)
        self.assertEqual(r['status'], 'PASS')
        self.assertAlmostEqual(r['trigger_s'], .001*3/3.3)
        self.assertAlmostEqual(r['witness_s'], .0015)

    def test_missing_early_and_late_response(self):
        for when in [None, .0005, .0035]:
            with self.subTest(when=when):
                self.assertEqual(self.run_case(when)['status'], 'FAIL')

    def test_exact_deadline_is_inclusive(self):
        # Trigger = 0.90909.. ms; set deadline to known 2 ms witness.
        c = replace(self.c, response_deadline_s=.002-.001*3/3.3)
        self.assertEqual(self.run_case(.002, contract=c)['status'], 'PASS')
        self.assertEqual(self.run_case(.00201, contract=c)['status'], 'FAIL')

    def test_short_observation_is_not_functional_failure(self):
        r = self.run_case(None, stop=.002)
        self.assertEqual(r['status'], 'INSUFFICIENT_EVIDENCE')
        self.assertEqual(r['reason'], 'deadline_not_observed')

    def test_no_trigger_is_not_vacuous_pass(self):
        r = self.run_case(.0015, supply=self.v*0)
        self.assertEqual(r['status'], 'NOT_TRIGGERED')

    def test_initial_high_and_partial_history(self):
        self.assertEqual(self.run_case(.0015,supply=self.v*0+3.3)['status'], 'INSUFFICIENT_EVIDENCE')
        r = assess_function(self.t[10:],self.v[10:],self.response(.0015)[10:],self.c)
        self.assertEqual(r['reason'], 'missing_initial_history')

    def test_brownout_is_out_of_scope(self):
        v=self.v.copy();v[(self.t>.0011)&(self.t<.0013)]=2
        self.assertEqual(self.run_case(.0015,supply=v)['status'], 'INSUFFICIENT_EVIDENCE')

    def test_sparse_samples_and_malformed_data(self):
        r=assess_function(self.t[::10],self.v[::10],self.response(.0015)[::10],self.c)
        self.assertEqual(r['status'],'INSUFFICIENT_EVIDENCE')
        for t,v,p in [([0,0],[0,3.3],[0,1.8]),([0,1],[0,float('nan')],[0,0]),([0,1],[0,3.3],[0]),(['bad',1],[0,3.3],[0,1.8])]:
            self.assertEqual(assess_function(t,v,p,self.c)['status'],'INSUFFICIENT_EVIDENCE')

    def test_contract_validation(self):
        for kwargs in [dict(response_deadline_s=0),dict(source=''),dict(max_sample_gap_s=-1),dict(por_threshold_v=float('nan')),dict(response_deadline_s='2ms'),dict(supply_trigger_v=None)]:
            with self.assertRaises(ValueError): FunctionalContract(**kwargs)

    def test_real_missing_measurement_can_fail_function(self):
        root=Path(__file__).parent/'data/runs'
        r=assess_run(root/'tt27_continuous_nanoamp',functional_contract=self.c)
        self.assertEqual((r['execution'],r['measurement'],r['scalar_spec'],r['functional']['status']),
                         ('COMPLETE','INVALID','NOT_EVALUATED','FAIL'))
        r=assess_run(root/'tt27_continuous_fossi',functional_contract=self.c)
        self.assertEqual((r['measurement'],r['scalar_spec'],r['functional']['status']),('VALID','PASS','PASS'))
        r=assess_run(root/'tt27_continuous_fossi')
        self.assertEqual(r['functional']['status'],'NOT_EVALUATED')


if __name__=='__main__': unittest.main()
