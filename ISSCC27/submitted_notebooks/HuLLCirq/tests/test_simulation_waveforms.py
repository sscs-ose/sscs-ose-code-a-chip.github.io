"""Isolated recording/proof QA; tool calls are mocked, never circuit evidence."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from hullcirq import simulation_waveforms_v1 as wave, verification, global_workflow
from hullcirq.domain import DomainError
from test_generic_verification import interface, contract, runtime
from test_generic_global_verification import manifest_fixture, scope_fixture, transcript
from hullcirq.generic_verification import build_cycle_plan
from hullcirq.global_generation import build_global_plan

ROOT = Path(__file__).resolve().parents[1]
VCD = '$timescale 1ps $end\n$var wire 9 ! hc_p4 $end\n$enddefinitions $end\n#0\nbx !\n#26000\nb0 !\n#150000\n'


class SavedWaveformTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT/'.work/qa')
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.compiler = {'kind': 'native', 'executable': str(self.folder/'iverilog.exe'), 'working_directory': str(self.folder)}
        self.plan = build_cycle_plan(interface(), contract())

    def execute_local(self, *, capture=True, fail=False, omit_wave=False, compile_fail=False):
        calls = []
        def execute(command, cwd, cancel=None, timeout=60):
            calls.append((command, Path(cwd)))
            n = len(calls)
            out = {'executed': True, 'status': 'Completed', 'exit_code': 0, 'stdout': '', 'stderr': '', 'command': command}
            if n == 2 and compile_fail:
                out.update(exit_code=1, stderr='SOFTWARE QA compile failure')
            if n == 3:
                if capture and not omit_wave:
                    (Path(cwd)/'simulation.vcd').write_text(VCD, encoding='utf-8', newline='\n')
                out.update(stdout='HULLCIRQ_FAIL SOFTWARE QA\n' if fail else runtime(self.plan), exit_code=1 if fail else 0)
            return out
        with patch.object(verification, 'execute_fixed', side_effect=execute):
            result = verification.verify_behavior('module CedarCore; endmodule // SOFTWARE QA', self.plan, self.compiler,
                                                  self.folder, record_waveform=capture)
        return result, calls

    def test_recording_reuses_s14_but_retains_original_plan_assertions_and_timing(self):
        original = copy.deepcopy(self.plan)
        text = wave.instrument(self.plan, self.plan['testbench'], self.plan['testbench_module'])
        self.assertEqual(self.plan, original)
        self.assertEqual(text.count('$dumpfile("simulation.vcd")'), 1)
        self.assertIn('$dumpvars(1, '+self.plan['testbench_module']+')', text)
        self.assertNotIn('ROUTED_FUNCTIONAL', text)
        prefix, end = self.plan['testbench'].split('endmodule')
        self.assertTrue(text.startswith(prefix)); self.assertTrue(text.endswith('endmodule'+end))

    def test_local_capture_is_opt_in_and_keeps_s04_behavior_unchanged(self):
        result, calls = self.execute_local(capture=False)
        self.assertEqual(result['validation_status'], 'Passed')
        self.assertNotIn('waveform_recording', result)
        self.assertEqual(calls[-1][1], self.folder)
        self.assertEqual(Path(result['artifacts_directory'],'contract_tb.v').read_text(), self.plan['testbench'])

    def test_s06_capture_retains_vcd_hash_and_isolates_runtime_directory(self):
        result, calls = self.execute_local()
        self.assertEqual(result['validation_status'], 'Passed')
        self.assertEqual(calls[-1][1], Path(result['artifacts_directory']))
        self.assertNotEqual(calls[-1][1], self.folder)
        self.assertIn('recorded_job_tb.v', ' '.join(calls[1][0]))
        self.assertTrue(any(a['id']=='simulation-waveform' for a in result['artifacts']))
        wave.validate(result, self.plan, self.plan['testbench'], self.plan['testbench_module'])

    def test_failed_runtime_retains_partial_vcd_without_becoming_a_pass(self):
        result, _ = self.execute_local(fail=True)
        self.assertEqual(result['validation_status'], 'Failed')
        self.assertTrue(any(a['id']=='simulation-waveform' for a in result['artifacts']))

    def test_compile_failure_retains_original_and_recording_sources(self):
        result, calls = self.execute_local(compile_fail=True)
        self.assertEqual(len(calls), 2)
        self.assertEqual(result['validation_status'], 'Failed')
        self.assertTrue({'original-testbench','recorded-testbench','simulation-stderr'} <= {a['id'] for a in result['artifacts']})

    def test_missing_waveform_does_not_silently_claim_new_capture_passed(self):
        result, _ = self.execute_local(omit_wave=True)
        self.assertEqual(result['validation_status'], 'Failed')
        self.assertTrue(any(d['code']=='simulation_waveform_missing' for d in result['diagnostics']))

    def test_recording_and_vcd_tamper_fail_closed(self):
        result, _ = self.execute_local()
        (Path(result['artifacts_directory'])/'simulation.vcd').write_text('changed', encoding='utf-8')
        with self.assertRaises(DomainError): wave.validate(result, self.plan, self.plan['testbench'], self.plan['testbench_module'])

    def test_s10_mocked_capture_rebuilds_new_commands_and_original_plan(self):
        manifest = manifest_fixture(); plan = build_global_plan(manifest['design']); before = copy.deepcopy(plan)
        calls = []
        def execute(command, cwd, cancel=None, timeout=60):
            calls.append((command, Path(cwd)))
            if len(calls)==2:
                Path(command[command.index('-o')+1]).write_text('\n'.join(scope_fixture(manifest)), encoding='utf-8')
            if len(calls)==4:
                (Path(cwd)/'simulation.vcd').write_text(VCD, encoding='utf-8', newline='\n')
            return {'executed': True,'status': 'Completed','exit_code': 0,'stdout': transcript(plan) if len(calls)==4 else '', 'stderr': '', 'command': command}
        netlist='module byte_pipeline; endmodule // SOFTWARE QA'
        with patch.object(global_workflow,'execute_fixed',side_effect=execute), patch.object(global_workflow,'netlist_public_interfaces',return_value={}):
            result=global_workflow.check_global_netlist(netlist,manifest,plan,self.compiler)
            self.assertEqual(result['validation_status'],'Passed')
            self.assertEqual(calls[-1][1], Path(result['artifacts_directory']))
            self.assertIn('recorded_job_tb.v', ' '.join(calls[2][0]))
            run={'checks':result,'source_manifest':manifest,'verification_plan':plan,'tool_configuration':self.compiler,'netlist':netlist,
                 'netlist_sha256':verification.content_hash(netlist),'source_manifest_sha256':verification.object_hash(manifest)}
            global_workflow.validate_netlist_proof(run)
        self.assertEqual(plan,before)

    def test_legacy_commands_remain_separate_and_unchanged(self):
        plan=build_global_plan(manifest_fixture()['design']); folder=self.folder/'hullcirq-global-netlist-old'
        old=global_workflow.fixed_global_netlist_commands(self.compiler,folder,plan)
        new=global_workflow.fixed_global_netlist_commands(self.compiler,folder,plan,record_waveform=True)
        self.assertEqual(old[:2],new[:2]); self.assertIn('instrumented_job_tb.v',' '.join(old[2])); self.assertIn('recorded_job_tb.v',' '.join(new[2]))

    def test_recording_marker_does_not_rename_an_identically_named_dut(self):
        source=interface(); source['module_name']='HULLCIRQ_ROUTED_FUNCTIONAL_NO_SDF'
        plan=build_cycle_plan(source,contract())
        text=wave.instrument(plan,plan['testbench'],plan['testbench_module'])
        self.assertIn('HULLCIRQ_ROUTED_FUNCTIONAL_NO_SDF dut (',text)
        self.assertIn('$display("'+wave.MARKER+'")',text)

    def test_legacy_public_monitor_remains_before_added_recording(self):
        plan={'kind':'legacy_software_fixture','testbench':'module hullcirq_global_tb;\ninitial $finish;\nendmodule\n'}
        base=plan['testbench'].replace('endmodule','// existing public monitor\ninitial $display("PUBLIC_MONITOR");\nendmodule')
        text=wave.instrument(plan,base,'hullcirq_global_tb')
        self.assertTrue(text.startswith(base.split('endmodule')[0]))
        self.assertIn('PUBLIC_MONITOR',text);self.assertEqual(text.count('$dumpvars'),1)

    def test_artifact_directory_outside_checkout_is_rejected_before_reads(self):
        with self.assertRaises(DomainError): wave.artifacts(ROOT.parent)
