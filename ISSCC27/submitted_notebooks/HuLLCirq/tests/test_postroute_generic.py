"""Generic adapter software QA: synthetic saved text only, no tool calls."""
import copy
from pathlib import Path
import sys
import threading
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from hullcirq import postroute_generic as generic, postroute_tools as tools
from hullcirq.domain import DomainError
from hullcirq.verification import content_hash, object_hash
from hullcirq.postlayout_workflow import PostLayoutWorkflowManager


def fixture():
    vector = object_hash({'fixture': 'independent counter expected values'})
    text = '''module counter_check;
  reg pulse=0;
  reg reset_l=0;
  wire [7:0] observed;
  counter_core unit_under_check(.tick(pulse), .resetn(reset_l), .count(observed));
  always #2 pulse=~pulse;
  initial begin #4000; $display("COUNTER_FAIL watchdog"); $finish; end
  initial begin
    $display("COUNT_RECORD index=%0d value=%0d cycle=%0d",0,observed,1);
    $display("COUNTER_DONE"); $finish;
  end
endmodule
'''
    plan = {'kind': 'non_npu_counter_fixture', 'testbench': text, 'testbench_sha256': content_hash(text),
            'vector_hash': vector, 'output_count': 3, 'recipe': {'expected_outputs': [0, 1, 2]}}
    settings = {'top_module': 'counter_core', 'clock_name': 'tick', 'clock_period_ns': 12}
    contract = {'version': generic.VERSION, 'testbench_module': 'counter_check', 'dut_instance': 'unit_under_check',
                'clock_signal': 'pulse', 'clock_statement': '  always #2 pulse=~pulse;',
                'timeout_statement': '  initial begin #4000;', 'output_prefix': 'COUNT_RECORD',
                'pass_marker': 'COUNTER_DONE', 'failure_markers': ['COUNTER_FAIL']}
    layout = {'verification_plan': plan, 'verification_plan_sha256': object_hash(plan), 'settings': settings}
    return layout, contract


class GenericPostrouteTests(unittest.TestCase):
    def setUp(self):
        self.layout, self.contract = fixture()
        self.plan, self.settings = self.layout['verification_plan'], self.layout['settings']

    def transcript(self):
        return '\n'.join(['HULLCIRQ_ROUTED_FUNCTIONAL_NO_SDF',
            'COUNT_RECORD index=0 value=0 cycle=1', 'COUNT_RECORD index=1 value=1 cycle=2',
            'COUNT_RECORD index=2 value=2 cycle=3', 'COUNTER_DONE'])

    def test_non_npu_names_clock_and_watchdog_preserve_original_cycles(self):
        before = copy.deepcopy(self.layout)
        adapted = generic.functional_testbench(self.plan, self.settings, self.contract)
        self.assertIn('always #6 pulse=~pulse;', adapted)
        self.assertIn('initial begin #12000;', adapted)
        self.assertIn('$dumpvars(1, counter_check)', adapted)
        self.assertNotIn('output_data', adapted)
        self.assertEqual(before, self.layout)

    def test_arbitrary_plan_kind_does_not_change_contract_eligibility(self):
        for kind in ('custom_fir', 'counter_v9', 'serial_controller', 'npu2-array-global-original-matrix-v1'):
            plan = {**self.plan, 'kind': kind}
            self.assertEqual(generic.validate_contract(plan, self.settings, self.contract), self.contract)

    def test_expected_outputs_and_original_testbench_cannot_be_overridden(self):
        for key, value in [('expected_outputs', [8]), ('clock_period_ns', 1), ('testbench', 'fabricated')]:
            with self.subTest(key=key), self.assertRaises(DomainError):
                generic.validate_contract(self.plan, self.settings, {**self.contract, key: value})
        changed = {**self.plan, 'testbench': self.plan['testbench'] + '// changed'}
        with self.assertRaises(DomainError): generic.validate_contract(changed, self.settings, self.contract)

    def test_exact_finite_transcript_and_unconditionally_required_failures(self):
        self.assertEqual(generic.parse_functional(self.transcript(), self.plan, self.settings, self.contract)['validation_status'], 'Passed')
        for source in [self.transcript().replace('value=2', 'value=3'), self.transcript()+'\nCOUNT_RECORD malformed',
                       self.transcript()+'\nERROR hidden', self.transcript()+'\nFATAL hidden',
                       self.transcript().replace('cycle=2', 'cycle=1'), self.transcript().replace('value=0', 'value=x'),
                       self.transcript()+'\nCOUNTER_DONE', self.transcript().replace('COUNTER_DONE', '')]:
            with self.subTest(source=source[-60:]):
                self.assertEqual(generic.parse_functional(source, self.plan, self.settings, self.contract)['validation_status'], 'Failed')

    def test_no_internal_hierarchy_shell_files_or_sdf_can_be_added(self):
        for extra in ['wire x=unit_under_check.internal;', '$system("echo unsafe");',
                      '$fopen("outside");', '$readmemh("outside",x);', '$sdf_annotate("outside",unit_under_check);',
                      '`include "outside.v"', '$dumpfile("outside.vcd");']:
            plan = copy.deepcopy(self.plan); plan['testbench'] = plan['testbench'].replace('endmodule', extra+'\nendmodule')
            plan['testbench_sha256'] = content_hash(plan['testbench'])
            with self.subTest(extra=extra), self.assertRaises(DomainError): generic.validate_contract(plan, self.settings, self.contract)

    def test_ambiguous_clock_and_wrong_top_or_clock_port_rejected(self):
        for mutate in [lambda p,s,c: s.update(top_module='different_top'), lambda p,s,c: s.update(clock_name='wrong_clock'),
                       lambda p,s,c: c.update(clock_signal='other'), lambda p,s,c: c.update(dut_instance='other'),
                       lambda p,s,c: p.update(testbench=p['testbench'].replace('endmodule', 'always #9 pulse=~pulse;\nendmodule'))]:
            plan, settings, contract = copy.deepcopy((self.plan, self.settings, self.contract))
            mutate(plan, settings, contract); plan['testbench_sha256'] = content_hash(plan['testbench'])
            with self.assertRaises(DomainError): generic.validate_contract(plan, settings, contract)

    def test_binding_rejects_plan_clock_metadata_or_implementation_changes(self):
        descriptor = generic.binding(self.plan, self.settings, self.contract)
        self.assertEqual(generic.validate_binding(self.plan, self.settings, descriptor), self.contract)
        for key in ('module_sha256', 'contract_sha256', 'verification_plan_sha256', 'settings_sha256', 'testbench_sha256'):
            with self.subTest(key=key), self.assertRaises(DomainError):
                generic.validate_binding(self.plan, self.settings, {**descriptor, key: '0'*64})

    def test_v4_dispatch_and_launcher_use_exact_generic_tb_module(self):
        configuration = {'profile_version': tools.PROFILE_V4,
                         'functional_adapter': generic.binding(self.plan, self.settings, self.contract)}
        self.assertEqual(tools._testbench(self.layout, configuration), generic.functional_testbench(self.plan, self.settings, self.contract))
        self.assertIn(b"'-s', 'counter_check'", tools._launcher(configuration))
        self.assertEqual(tools._functional_report(self.transcript(), self.layout, configuration)['validation_status'], 'Passed')
        for version in (tools.PROFILE_V1, tools.PROFILE_V2, tools.PROFILE_V3):
            self.assertIs(tools._launcher({'profile_version': version}), tools.LAUNCHER)
            self.assertEqual(tools._testbench_module({'profile_version': version}), 'hullcirq_global_tb')

    def test_metadata_derivation_uses_saved_tb_and_not_circuit_kind(self):
        plan = copy.deepcopy(self.plan)
        marker = f"HULLCIRQ_GLOBAL_PASS outputs=3 vector_hash={plan['vector_hash']}"
        plan['testbench'] = plan['testbench'].replace('COUNTER_DONE', marker)
        plan['testbench_sha256'] = content_hash(plan['testbench'])
        contract = generic.derive_contract(plan, self.settings)
        self.assertEqual(contract['testbench_module'], 'counter_check')
        self.assertEqual(contract['output_prefix'], 'COUNT_RECORD')
        self.assertEqual(contract['pass_marker'], marker)
        self.assertEqual(generic.functional_testbench(plan, self.settings, contract).count('endmodule'), 1)

    def test_profile_prepare_needed_checks_generic_plan_settings_and_saved_metadata(self):
        original = {'verification_profile': 'generic_cycle_vectors', 'verification_plan_sha256': 'plan-a', 'settings_sha256': 'settings-a'}
        metadata = {'adapter_contract_original': original, 'adapter_contract_sha256': 'contract-a',
                    'adapter_contract_source': 'derived_saved_testbench'}
        descriptor = {'verification_plan_sha256': 'plan-a', 'settings_sha256': 'settings-a', 'contract_sha256': 'contract-a'}
        manager = SimpleNamespace(tool_configuration={'profile_version': tools.PROFILE_V4, 'functional_adapter': descriptor},
                                  _profile_prepare_available=lambda: True)
        self.assertFalse(PostLayoutWorkflowManager._adapter_profile_prepare_needed(manager, metadata))
        for key in ('verification_plan_sha256', 'settings_sha256'):
            changed = copy.deepcopy(metadata); changed['adapter_contract_original'][key] = 'changed'
            self.assertTrue(PostLayoutWorkflowManager._adapter_profile_prepare_needed(manager, changed))
        manager.tool_configuration = {'profile_version': tools.PROFILE_V3}
        self.assertTrue(PostLayoutWorkflowManager._adapter_profile_prepare_needed(manager, metadata))
        metadata['adapter_contract_original']['verification_profile'] = 'global-original-matrix-v1'
        self.assertFalse(PostLayoutWorkflowManager._adapter_profile_prepare_needed(manager, metadata))
        metadata['adapter_contract_source'] = 'saved_gui_contract'
        self.assertTrue(PostLayoutWorkflowManager._adapter_profile_prepare_needed(manager, metadata))

    def test_metadata_projection_reads_original_inputs_without_writing_source(self):
        layout = {'id': 'software-layout', **self.layout}
        physical = SimpleNamespace(lock=threading.RLock(), _state={'runs': [layout]})
        before = copy.deepcopy(physical._state)
        manager = SimpleNamespace(physical_workflow=physical, _profile_prepare_available=lambda: True,
                                  _adapter_contract_for=lambda selected: (copy.deepcopy(self.contract), 'saved_gui_contract'))
        metadata = PostLayoutWorkflowManager._adapter_metadata(manager)
        self.assertEqual(metadata['adapter_contract_original']['testbench'], self.plan['testbench'])
        self.assertEqual(metadata['adapter_contract_original']['expected_outputs'], [0, 1, 2])
        self.assertEqual(metadata['adapter_contract_original']['clock_period_ns'], 12)
        self.assertEqual(metadata['adapter_contract_sha256'], object_hash(self.contract))
        self.assertEqual(physical._state, before)


if __name__ == '__main__': unittest.main()
