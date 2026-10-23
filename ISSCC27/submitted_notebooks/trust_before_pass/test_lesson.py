"""Automation of interaction plumbing; NOT evidence of human learning."""
import tempfile
from pathlib import Path
import unittest
import numpy as np
from lesson import Investigation, experiment, load_case, plot_cases
from simple_baseline import check


class LessonTests(unittest.TestCase):
    def test_repeat_prediction_preserves_initial_attempt(self):
        s=Investigation();s.predict('w','first answer','first reason')
        s.observe('w','old_nonlinear',observe_until_ms=2.5)
        s.reflect('w','deadline not yet visible')
        s.predict('w','second answer','longer observation')
        self.assertEqual(s.history[0]['entry']['prediction'],'first answer')
        self.assertIn('feedback',s.history[0]['entry'])

    def test_journal_requires_prediction_then_explanation(self):
        s=Investigation()
        with self.assertRaises(ValueError): s.observe('window','old_nonlinear')
        with self.assertRaises(ValueError): s.predict('window','','because')
        s.predict('window','Functional failure','I expect a completed deadline')
        s.observe('window','old_nonlinear')
        with self.assertRaises(ValueError): s.reflect('window','')
        self.assertIn('FAIL',s.reflect('window','Deadline is visible; no new POR rise'))
        s.observe('window','old_nonlinear',observe_until_ms=2.5)
        self.assertNotIn('feedback',s.entries['window'])
        self.assertEqual(s.entries['window']['report']['functional']['status'],'INSUFFICIENT_EVIDENCE')
        with tempfile.TemporaryDirectory() as d:
            s.save(Path(d)/'journal.json');self.assertTrue((Path(d)/'journal.json').exists())

    def test_rules_change_scalar_not_measurement_or_function(self):
        a=experiment('corrected_nonlinear');b=experiment('corrected_nonlinear',scalar_max_ms=1)
        self.assertEqual(a['measurement'],b['measurement'])
        self.assertEqual((a['scalar_spec'],b['scalar_spec']),('PASS','FAIL'))
        self.assertEqual(a['functional'],b['functional'])

    def test_bad_controls_rejected(self):
        for kw in [dict(observe_until_ms=100),dict(measurement_start_ms=5),dict(threshold_v=2),dict(deadline_ms=-1)]:
            with self.assertRaises(ValueError): experiment(**kw)

    def test_independent_challenge(self):
        r=experiment('slow_supply',observe_until_ms=4.4)
        self.assertEqual((r['measurement'],r['functional']['status']),('INVALID','INSUFFICIENT_EVIDENCE'))
        r=experiment('slow_supply')
        self.assertEqual((r['measurement'],r['functional']['status']),('VALID','PASS'))

    def test_baseline_agrees_on_supported_real_cases(self):
        for case in ['old_nonlinear','corrected_nonlinear','old_linear','corrected_linear','slow_supply']:
            with self.subTest(case=case):
                a,_=load_case(case);b=check(a);r=experiment(case)
                self.assertEqual((b['measurement'],b['scalar_spec'],b['functional']),
                                 (r['measurement'],r['scalar_spec'],r['functional']['status']))
                if b['startup_s'] is not None: self.assertAlmostEqual(b['startup_s'],r['startup_s'])

    def test_plot_does_not_reveal_unobserved_future(self):
        import matplotlib.pyplot as plt
        fig=plot_cases(['slow_supply'],observe_until_ms=4.4)
        for line in fig.axes[0].lines: self.assertLessEqual(np.max(line.get_xdata()),4.4+1e-9)
        plt.close(fig)


if __name__=='__main__': unittest.main()
