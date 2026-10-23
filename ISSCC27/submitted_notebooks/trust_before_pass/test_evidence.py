"""Synthetic software tests; these are NOT circuit-failure evidence."""
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
from evidence import Contract, rising_crossings, assess_run, coverage


class EvidenceTests(unittest.TestCase):
    def fixture(self, root, *, scalar=1e-3, log='', stop=.004, exit_code=0, terminated=None):
        p = Path(root)
        t = np.array([0, .0015, .0016, .0017, .0026, .0027, .003, .004])
        a = np.column_stack([t, t*0+3.3,
                             [0,0,0,1.8,1.8,1.8,1.8,1.8],
                             [0,0,0,0,0,1.8,1.8,1.8],t*0,t*0])
        a = a[t <= stop]
        np.savetxt(p/'wave.tsv', a, header='t avdd osc por timed_out pwup', comments='')
        (p/'response_0.data').write_text(f'3e-5\n{scalar}\n')
        (p/'stdout.log').write_text(log)
        (p/'provenance.json').write_text(json.dumps({'conditions':{'corner':'tt','temperature':27}}))
        (p/'resources.json').write_text(json.dumps(dict(exit_code=exit_code,
            termination_reason=terminated,wall_seconds=1,peak_windows_wset=1024)))
        return p

    def test_interpolation_and_initial_high(self):
        np.testing.assert_allclose(rising_crossings([0,1,2],[0,2,2],1), [.5])
        self.assertEqual(len(rising_crossings([0,1],[2,2],1)), 0)

    def test_invalid_time_and_nonfinite(self):
        for t,v in [([0,0],[0,1]), ([1,0],[0,1]), ([0,1],[0,float('nan')])]:
            with self.assertRaises(ValueError): rising_crossings(t,v,.9)

    def test_valid_and_spec_failure_remain_distinct(self):
        with tempfile.TemporaryDirectory() as d:
            p = self.fixture(d)
            r = assess_run(p)
            self.assertEqual((r['measurement'],r['verdict']), ('VALID','PASS'))
            r = assess_run(p,Contract(startup_max_s=.0008))
            self.assertEqual((r['measurement'],r['verdict']), ('VALID','FAIL'))

    def test_exit_zero_does_not_override_measurement_error(self):
        with tempfile.TemporaryDirectory() as d:
            r = assess_run(self.fixture(d,log='Error: measure por_start when: out of interval'))
            self.assertEqual((r['execution'],r['measurement'],r['verdict']),
                             ('COMPLETE','INVALID','NOT_EVALUATED'))

    def test_scalar_mismatch_nan_and_zero(self):
        for value in [0, float('nan'), .003]:
            with tempfile.TemporaryDirectory() as d:
                self.assertEqual(assess_run(self.fixture(d,scalar=value))['measurement'], 'INVALID')

    def test_budget_and_nonzero_exit(self):
        with tempfile.TemporaryDirectory() as d:
            r = assess_run(self.fixture(d,terminated='wall_budget'))
            self.assertEqual(r['execution'], 'INCOMPLETE')
            r = assess_run(self.fixture(d,exit_code=1))
            self.assertEqual(r['execution'], 'ERROR')

    def test_empty_scalar_file(self):
        with tempfile.TemporaryDirectory() as d:
            p=self.fixture(d); (p/'response_0.data').write_text('\n\n')
            r=assess_run(p)
            self.assertEqual(r['measurement'],'INVALID')
            self.assertIn('invalid_scalar_artifact',r['reasons'])

    def test_truncated_trace(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(assess_run(self.fixture(d,stop=.003))['execution'], 'INCOMPLETE')

    def test_absent_window_event(self):
        with tempfile.TemporaryDirectory() as d:
            p = self.fixture(d)
            a = np.loadtxt(p/'wave.tsv',skiprows=1); a[:,3] = 1.8
            np.savetxt(p/'wave.tsv',a,header='t avdd osc por timed_out pwup',comments='')
            r = assess_run(p)
            self.assertIn('missing_por_event_in_window',r['reasons'])
            self.assertIsNone(r['startup_s'])

    def test_missing_coverage_is_not_a_failing_sample(self):
        c = coverage([{'conditions':{'corner':'tt','temperature':27}}])
        self.assertEqual(c['observed_expected'],1)
        self.assertEqual(len(c['missing']),8)

    def test_contract_rejects_impossible_bounds(self):
        with self.assertRaises(ValueError): Contract(window_start_s=.005)


if __name__ == '__main__': unittest.main()
