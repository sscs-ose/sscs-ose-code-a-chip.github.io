"""Readiness guards use archived original-job input, never a replacement job."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from hullcirq.domain import DomainError
from hullcirq.postlayout_testbench import timed_testbench
from hullcirq.postlayout_tools import runtime_descriptor, source_inputs, validate_postlayout_result
from hullcirq.verification import content_hash, object_hash


class PostlayoutToolsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.layout = json.loads((ROOT / 'results/npu_layout_continuous_flow/layout_record.json').read_text(encoding='utf-8'))
        cls.plan = cls.layout['verification_plan']
        cls.settings = cls.layout['settings']

    def test_original_job_constants_and_assertions_remain_exact(self):
        plan = copy.deepcopy(self.plan); before = object_hash(plan)
        adapted, meta = timed_testbench(plan, self.settings)
        base = plan['testbench']
        # Reverse only the explicitly supported timing edits; no input, expected
        # value, assertion or handshake code can have changed.
        annotation = adapted.index('  initial begin\n    $display("HULLCIRQ_S14_ANNOTATION_BEGIN")')
        restored = adapted[:annotation] + 'endmodule' + adapted.split('endmodule', 1)[1]
        restored = restored.removeprefix('`timescale 1ns/1ps\n')
        restored = restored.replace('  always #25 clk=~clk;', '  always #5 clk=~clk;')
        restored = restored.replace('  always @(negedge clk) begin\n    #24; // 1 ns before the external receiving edge', '  always @(posedge clk) begin')
        restored = restored.replace('  initial begin #1000000;', '  initial begin #200000;')
        self.assertEqual(restored, base)
        self.assertEqual(object_hash(plan), before)
        self.assertFalse(meta['original_job_values_changed'])
        self.assertEqual(meta['original_plan_sha256'], self.layout['verification_plan_sha256'])
        self.assertEqual(meta['timed_testbench_sha256'], content_hash(adapted))
        self.assertEqual(plan['output_count'], 16)

    def test_modified_base_hash_is_rejected(self):
        plan = copy.deepcopy(self.plan); plan['testbench'] += '\n//changed'
        with self.assertRaises(DomainError): timed_testbench(plan, self.settings)

    def test_unknown_timing_syntax_even_with_new_hash_is_rejected(self):
        plan = copy.deepcopy(self.plan); plan['testbench'] = plan['testbench'].replace('always #5', 'always #6')
        plan['testbench_sha256'] = content_hash(plan['testbench'])
        with self.assertRaises(DomainError): timed_testbench(plan, self.settings)

    def test_unsupported_clock_reset_contract_is_rejected(self):
        for changes in ({'clock_name': 'clk2'}, {'reset_kind': 'asynchronous'}, {'clock_period_ns': 2}, {'clock_period_ns': True}):
            with self.subTest(changes=changes), self.assertRaises(DomainError):
                timed_testbench(self.plan, {**self.settings, **changes})

    def test_missing_runtime_never_claims_support(self):
        descriptor = runtime_descriptor(None)
        self.assertFalse(descriptor['available']); self.assertFalse(descriptor['verification_supported'])

    def test_profile_override_cannot_enable_simulation(self):
        profile = json.loads((ROOT / 'configs/postlayout_preflight_sky130_v1.json').read_text(encoding='utf-8'))
        profile['verification_supported'] = True
        descriptor = runtime_descriptor({'profile': profile})
        self.assertFalse(descriptor['available']); self.assertFalse(descriptor['verification_supported'])

    def test_fabricated_pass_always_rejected_by_actual_validator(self):
        with self.assertRaises(DomainError) as error:
            validate_postlayout_result({'validation_status': 'Passed', 'executed': True}, {}, {}, {}, {})
        self.assertEqual(error.exception.code, 'postlayout_unsupported')


if __name__ == '__main__': unittest.main()
