"""Original-job timing adaptation; software checks do not simulate the NPU."""
import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from hullcirq.domain import DomainError
from hullcirq.postlayout_testbench import timed_testbench, timed_testbench_v2
from hullcirq.verification import content_hash, object_hash


class TimedTestbenchV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        layout = json.loads((ROOT / 'results/npu_layout_continuous_flow/layout_record.json').read_text(encoding='utf-8'))
        cls.plan = layout['verification_plan']
        cls.settings = layout['settings']

    def test_reverse_v2_only_restores_exact_original_job_and_assertions(self):
        before = object_hash(self.plan)
        adapted, meta = timed_testbench_v2(self.plan, self.settings)
        annotation = adapted.index('  initial begin\n    $display("HULLCIRQ_S14_ANNOTATION_BEGIN")')
        restored = adapted[:annotation] + 'endmodule' + adapted.split('endmodule', 1)[1]
        restored = restored.removeprefix('`timescale 1ns/1ps\n')
        restored = restored.replace('  always #25 clk=~clk;', '  always #5 clk=~clk;')
        restored = restored.replace('  initial begin\n    #24; // 1 ns before the first external receiving edge\n    forever begin\n',
                                    '  always @(posedge clk) begin\n')
        restored = restored.replace('      #50; // one original logical cycle\n    end\n', '')
        restored = restored.replace('  initial begin #1000000;', '  initial begin #200000;')
        self.assertEqual(restored, self.plan['testbench'])
        self.assertEqual(object_hash(self.plan), before)
        self.assertFalse(meta['original_job_values_changed'])
        self.assertFalse(meta['original_expected_outputs_changed'])
        self.assertEqual(meta['vector_hash'], self.plan['vector_hash'])
        self.assertEqual(meta['public_boundary_vector_hash'], self.plan['public_boundary_vector_hash'])

    def test_checker_and_backpressure_counter_phase_include_first_edge(self):
        adapted, meta = timed_testbench_v2(self.plan, self.settings)
        self.assertEqual(meta['checker_first_sample_ns'], 24)
        self.assertEqual(meta['checker_period_ns'], 50)
        self.assertTrue(meta['original_counter_and_backpressure_cycle_phase_preserved'])
        original_posedges = [25 + 50 * index for index in range(20)]
        sampled = [meta['checker_first_sample_ns'] + 50 * index for index in range(20)]
        self.assertEqual(sampled, [edge - 1 for edge in original_posedges])
        # Each falling-edge stimulus sees the same completed checker count.
        for negedge in range(50, 1001, 50):
            original_cycles = sum(edge < negedge for edge in original_posedges)
            adapted_cycles = sum(edge < negedge for edge in sampled)
            self.assertEqual(adapted_cycles, original_cycles)
            self.assertEqual(adapted_cycles % 5 in (1, 3, 4), original_cycles % 5 in (1, 3, 4))
        self.assertIn('    #24; // 1 ns before the first external receiving edge', adapted)

    def test_v1_candidate_and_original_hash_remain_distinct_unchanged(self):
        old_before, old_meta = timed_testbench(self.plan, self.settings)
        adapted, meta = timed_testbench_v2(self.plan, self.settings)
        old_after, after_meta = timed_testbench(self.plan, self.settings)
        self.assertEqual(old_before, old_after)
        self.assertEqual(old_meta, after_meta)
        self.assertIn('always @(negedge clk) begin\n    #24;', old_after)
        self.assertNotEqual(meta['timed_testbench_sha256'], old_meta['timed_testbench_sha256'])
        self.assertEqual(meta['v1_candidate_sha256'], old_meta['timed_testbench_sha256'])
        self.assertEqual(content_hash(adapted), meta['timed_testbench_sha256'])
        self.assertEqual(meta['original_testbench_sha256'], self.plan['testbench_sha256'])

    def test_unknown_checker_boundary_is_rejected_even_with_new_base_hash(self):
        plan = copy.deepcopy(self.plan)
        plan['testbench'] = plan['testbench'].replace('    expected[0]', '    expected [0]')
        plan['testbench_sha256'] = content_hash(plan['testbench'])
        with self.assertRaises(DomainError):
            timed_testbench_v2(plan, self.settings)


if __name__ == '__main__':
    unittest.main()
