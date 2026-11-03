"""Post-route adapter contract tests; synthetic transcripts are software QA only."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from hullcirq import postroute_tools as tools
from hullcirq.domain import DomainError
from hullcirq.verification import object_hash


class PostRouteToolsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.layout = tools.load(ROOT/'results/npu_layout_continuous_flow/layout_record.json')
        cls.plan = cls.layout['verification_plan']

    def test_functional_adapter_changes_only_clock_watchdog_and_recording(self):
        adapted = tools.functional_testbench(self.plan, self.layout['settings'])
        marker = adapted.index('  initial begin\n    $display("HULLCIRQ_ROUTED_FUNCTIONAL_NO_SDF")')
        restored = adapted[:marker] + 'endmodule' + adapted.split('endmodule', 1)[1]
        restored = restored.removeprefix('`timescale 1ns/1ps\n').replace('  always #25 clk=~clk;', '  always #5 clk=~clk;')
        restored = restored.replace('  initial begin #1000000;', '  initial begin #200000;')
        self.assertEqual(restored, self.plan['testbench'])
        self.assertNotIn('$sdf_annotate', adapted)
        invalid = copy.deepcopy(self.plan)
        invalid['testbench'] += '// changed software fixture'
        with self.assertRaises(DomainError):
            tools.functional_testbench(invalid, self.layout['settings'])

    def transcript(self):
        return '\n'.join(['HULLCIRQ_ROUTED_FUNCTIONAL_NO_SDF', *[
            f'HULLCIRQ_OUTPUT index={i} value={v} cycle={i+1}'
            for i, v in enumerate(self.plan['recipe']['expected_outputs'])],
            f"HULLCIRQ_GLOBAL_PASS outputs=16 vector_hash={self.plan['vector_hash']}"])

    def test_npu2_output_count_drives_the_exact_transcript_contract(self):
        plan = copy.deepcopy(self.plan)
        plan['kind'] = 'npu2-global-original-matrix-v1'
        plan['output_count'] = 4
        plan['recipe']['expected_outputs'] = plan['recipe']['expected_outputs'][:4]
        adapted = tools.functional_testbench(plan, self.layout['settings'])
        self.assertIn('HULLCIRQ_ROUTED_FUNCTIONAL_NO_SDF', adapted)
        source = '\n'.join(['HULLCIRQ_ROUTED_FUNCTIONAL_NO_SDF', *[
            f'HULLCIRQ_OUTPUT index={i} value={v} cycle={i+1}'
            for i, v in enumerate(plan['recipe']['expected_outputs'])],
            f"HULLCIRQ_GLOBAL_PASS outputs=4 vector_hash={plan['vector_hash']}"])
        self.assertEqual(tools.parse_functional(source, plan)['validation_status'], 'Passed')
        self.assertEqual(tools.parse_functional(source.replace('outputs=4', 'outputs=16'), plan)['validation_status'], 'Failed')
        invalid = copy.deepcopy(plan)
        invalid['output_count'] = 5
        with self.assertRaises(DomainError):
            tools.functional_testbench(invalid, self.layout['settings'])
        with self.assertRaises(DomainError):
            tools.parse_functional(source, invalid)

    def test_original_expected_values_marker_and_unknown_outputs_are_checked(self):
        source = self.transcript()
        self.assertEqual(tools.parse_functional(source, self.plan)['validation_status'], 'Passed')
        cases = [source.replace('index=0', 'index=1'), source.replace('cycle=1\n', 'cycle=0\n'),
                 source.replace('value=113', 'value=x'), source.replace(self.plan['vector_hash'], 'wrong'),
                 source + '\nHULLCIRQ_OUTPUT index=16 value=x cycle=17', source + '\nHULLCIRQ_FAIL fixture',
                 source + '\nHULLCIRQ_ROUTED_FUNCTIONAL_NO_SDF']
        for text in cases:
            with self.subTest(text=text[-90:]):
                self.assertEqual(tools.parse_functional(text, self.plan)['validation_status'], 'Failed')

    def test_runtime_pins_are_taken_from_unchanged_retained_worker(self):
        pins = tools.runtime_pins()
        self.assertEqual(len(pins), 39)
        self.assertEqual(pins['usr/bin/iverilog'], 'e29c891c741689c5d06791dc57f12e3a6df2eeac010a3913f7be57e9ef493bb3')
        self.assertEqual(pins['usr/bin/vvp'], 'a97a941d8d32415537b36397e4dab991bf8087896840c0ac53dd0e4b14fd04f8')
        self.assertFalse(tools.runtime_descriptor({'execution_scope': tools.SCOPE})['available'])

    @staticmethod
    def _wsl_path(path):
        path = Path(path).resolve()
        return f'/mnt/{path.drive[0].lower()}/{path.as_posix()[3:]}'

    def test_public_package_inventory_is_source_pinned_and_manifest_tamper_is_rejected(self):
        manifest = tools._compiler_package_manifest()
        self.assertEqual(object_hash(manifest), tools.COMPILER_MANIFEST_SHA256)
        self.assertEqual(len(manifest['files']), 83)
        self.assertEqual(manifest['provenance']['links'], {})
        self.assertEqual(manifest['files']['usr/bin/iverilog']['sha256'],
                         'a6071e4b4a68feafca0c8ee0e6aa275eee9a43a108c62801cfd1eca6eab6d8a3')
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            changed = copy.deepcopy(manifest)
            changed['files']['usr/bin/iverilog']['sha256'] = '0'*64
            (root/'configs').mkdir()
            (root/'configs/iverilog_12_runtime_manifest.json').write_text(json.dumps(changed), encoding='utf-8')
            with patch.object(tools, 'ROOT', root), self.assertRaises(DomainError):
                tools._compiler_package_manifest()

    def test_v3_profile_is_derived_from_the_public_package_and_exact_runtime_inventory(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            compiler_root = root/'.work/m2/iverilog'
            required = {
                'usr/bin/iverilog': b'compiler', 'usr/bin/vvp': b'runtime',
                'usr/lib/x86_64-linux-gnu/ivl/ivl': b'ivl',
                'usr/lib/x86_64-linux-gnu/ivl/ivlpp': b'preprocessor',
                'usr/lib/x86_64-linux-gnu/ivl/vvp.conf': b'configuration',
                'usr/lib/x86_64-linux-gnu/ivl/vvp.tgt': b'target',
                'usr/share/doc/iverilog/copyright': b'license proof',
            }
            for relative, raw in required.items():
                path = compiler_root/relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw)
            package = compiler_root.parent/tools.COMPILER_PACKAGE_NAME
            package.write_bytes(b'public pinned package software fixture')
            package_manifest = {
                'schema': 'hullcirq-iverilog-package-inventory-v1',
                'package': {'name': tools.COMPILER_PACKAGE_NAME, 'sha256': tools.sha(package),
                            'bytes': package.stat().st_size, 'source': tools.COMPILER_PACKAGE_SOURCE},
                'provenance': {'links': {}},
                'files': {name: {'sha256': tools.sha(compiler_root/name), 'bytes': len(raw)}
                          for name, raw in required.items()},
            }
            (root/'configs').mkdir()
            (root/'configs/iverilog_12_runtime_manifest.json').write_text(json.dumps(package_manifest), encoding='utf-8')
            linux_root = self._wsl_path(compiler_root)
            compiler = {'kind': 'wsl', 'distribution': 'Ubuntu',
                        'executable': linux_root+'/usr/bin/iverilog',
                        'base_directory': linux_root+'/usr/lib/x86_64-linux-gnu/ivl',
                        'working_directory': str(root/'.work/m2/syntax')}
            (root/'.work/m2/compiler.json').write_text(json.dumps(compiler), encoding='utf-8')
            image = root/'.work/physical/runtime.AppImage'
            image.parent.mkdir(parents=True, exist_ok=True)
            image.write_bytes(b'physical runtime')
            pdk_root = root/'.work/physical/pdks'
            manifest = {'root': str(pdk_root), 'files': {}}
            for relative in tools.MODEL_FILES.values():
                path = pdk_root/relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(relative.encode('utf-8'))
                manifest['files'][relative] = {'sha256': tools.sha(path), 'bytes': path.stat().st_size}
            pdk_manifest = root/'.work/physical/pdk-input-manifest.json'
            pdk_manifest.write_text(json.dumps(manifest), encoding='utf-8')
            runtime = {'kind': 'wsl', 'appimage_path': str(image), 'appimage_sha256': tools.sha(image),
                       'pdk_manifest_path': str(pdk_manifest), 'pdk_manifest_sha256': tools.sha(pdk_manifest)}
            layout = {'runtime_configuration': runtime}
            working = root/'.work/workspace/runtime_profiles/project/system/runs'
            with patch.object(tools, 'ROOT', root), \
                    patch.object(tools, 'COMPILER_PACKAGE_SHA256', tools.sha(package)), \
                    patch.object(tools, 'COMPILER_MANIFEST_SHA256', object_hash(package_manifest)), \
                    patch.object(tools.physical, 'IMAGE_SHA', tools.sha(image)):
                configuration = tools.prepare_configuration(layout, compiler, working)
                self.assertEqual(configuration['profile_version'], tools.PROFILE_V3)
                self.assertEqual(configuration['sta_annotation_policy'], tools.postroute_sta.ANNOTATION_V2)
                self.assertEqual(set(configuration['compiler_runtime_pins']), set(required))
                self.assertNotIn('path', configuration['compiler_package'])
                self.assertTrue(tools.runtime_descriptor(configuration)['available'])
                legacy = copy.deepcopy(configuration)
                legacy['profile_version'] = tools.PROFILE_V2
                legacy.pop('sta_annotation_policy')
                self.assertTrue(tools.runtime_descriptor(legacy)['available'])
                changed_policy = copy.deepcopy(configuration)
                changed_policy['sta_annotation_policy'] = 'unknown-software-qa-policy'
                self.assertFalse(tools.runtime_descriptor(changed_policy)['available'])
                legacy['sta_annotation_policy'] = tools.postroute_sta.ANNOTATION_V2
                self.assertFalse(tools.runtime_descriptor(legacy)['available'])
                (compiler_root/'usr/bin/vvp').write_bytes(b'changed runtime')
                self.assertFalse(tools.runtime_descriptor(configuration)['available'])
                # A second Prepare cannot bless bytes changed before preparation.
                with self.assertRaises(DomainError):
                    tools.prepare_configuration(layout, compiler, working)
                (compiler_root/'usr/bin/vvp').write_bytes(required['usr/bin/vvp'])
                (compiler_root/'usr/lib/x86_64-linux-gnu/ivl/extra.vpi').write_bytes(b'extra plugin')
                with self.assertRaises(DomainError):
                    tools.prepare_configuration(layout, compiler, working)

    def test_v2_profile_rejects_redirected_compiler_and_working_paths(self):
        compiler = {'kind': 'wsl', 'distribution': 'Ubuntu',
                    'executable': '/mnt/c/untrusted/usr/bin/iverilog',
                    'base_directory': '/mnt/c/untrusted/usr/lib/x86_64-linux-gnu/ivl'}
        with self.assertRaises(DomainError):
            tools.prepare_configuration({'runtime_configuration': {}}, compiler, ROOT/'.work/s14')
        with self.assertRaises(DomainError):
            tools.prepare_configuration({'runtime_configuration': {}}, compiler, ROOT.parent/'outside')

    def test_windows_output_budget_rejects_unreadable_terminal_proof_before_execution(self):
        with patch.object(tools.os, 'name', 'nt'):
            tools._check_output_path_budget(Path('C:/short/runtime'))
            with self.assertRaises(DomainError) as caught:
                tools._check_output_path_budget(Path('C:/') / ('long' * 60))
        self.assertEqual(caught.exception.code, 'postroute_path_length')

    def test_compiled_program_runtime_and_input_manifest_cannot_be_substituted(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            native = '/software-qa-runtime'
            configuration = {'compiler': {'executable': native+'/usr/bin/iverilog'}}
            manifest = {'runtime_root': native, 'runtime_pins': tools.runtime_pins(), 'files': []}
            versions = {'compiler': configuration['compiler']['executable'], 'runtime_pins': tools.runtime_pins()}
            tools._save(folder/'functional-inputs.json', manifest)
            tools._save(folder/'functional-versions.json', versions)
            tools._save(folder/'simulation.vvp', b'SOFTWARE QA ONLY, not executable')
            program = {'input_manifest_sha256': tools.sha(folder/'functional-inputs.json'),
                'version_report_sha256': tools.sha(folder/'functional-versions.json'),
                'program_sha256': tools.sha(folder/'simulation.vvp'), 'program_bytes': (folder/'simulation.vvp').stat().st_size,
                'command': [native+'/usr/bin/iverilog', '-B', native+'/usr/lib/x86_64-linux-gnu/ivl', '-g2005',
                            '-DFUNCTIONAL', '-DUNIT_DELAY=', '-s', 'hullcirq_global_tb', '-o', 'simulation.vvp',
                            'primitives.v', 'cell_models.v', 'input.nl.v', 'functional-testbench.v']}
            tools._save(folder/'functional-program.json', program)
            tools._validate_functional_program(folder, configuration)
            for name in ('input_manifest_sha256', 'version_report_sha256', 'program_sha256'):
                invalid = {**program, name: '0'*64}
                (folder/'functional-program.json').write_bytes(tools._bytes(invalid))
                with self.subTest(field=name), self.assertRaises(DomainError):
                    tools._validate_functional_program(folder, configuration)
            (folder/'functional-program.json').write_bytes(tools._bytes(program))
            (folder/'simulation.vvp').write_bytes(b'altered software fixture program')
            with self.assertRaises(DomainError):
                tools._validate_functional_program(folder, configuration)

    def test_sta_results_must_be_for_the_same_layout_netlist_runtime_and_clock(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            layout = {'id': 'SOFTWARE_QA_LAYOUT', 'settings': {'clock_period_ns': 50}}
            runtime = {'executable': '/SOFTWARE_QA_ONLY'}
            tools._save(folder/'sta/inputs/netlist.v', b'SOFTWARE QA ONLY')
            inventory_hash = object_hash({'files': 'SOFTWARE QA TIMING INPUTS'})
            manifest = {'physical_runtime_sha256': object_hash(runtime), 'appimage_executable': runtime['executable'],
                        'source_inventory_sha256': inventory_hash}
            tools._save(folder/'sta/sta-inputs.json', manifest)
            inputs = {'netlist': {'sha256': tools.sha(folder/'sta/inputs/netlist.v')},
                      'timing_sources': {'sha256': inventory_hash}}
            sta = {'layout_run_id': layout['id'], 'layout_record_sha256': object_hash(layout), 'clock_period_ns': 50,
                   'source_inventory_sha256': inventory_hash}
            tools._validate_sta_binding(folder, sta, layout, runtime, inputs)
            policy = 'unconnected-clock-load-output-v2'
            with self.assertRaises(DomainError):
                tools._validate_sta_binding(folder, sta, layout, runtime, inputs, policy)
            (folder/'sta/sta-inputs.json').write_bytes(tools._bytes({**manifest, 'annotation_policy': policy}))
            with self.assertRaises(DomainError):
                tools._validate_sta_binding(folder, sta, layout, runtime, inputs, policy)
            tools._validate_sta_binding(folder, {**sta, 'annotation_policy': policy}, layout, runtime, inputs, policy)
            (folder/'sta/sta-inputs.json').write_bytes(tools._bytes(manifest))
            for key in ('layout_run_id', 'layout_record_sha256', 'clock_period_ns', 'source_inventory_sha256'):
                with self.subTest(field=key), self.assertRaises(DomainError):
                    tools._validate_sta_binding(folder, {**sta, key: 'other'}, layout, runtime, inputs)
            (folder/'sta/sta-inputs.json').write_bytes(tools._bytes({**manifest, 'source_inventory_sha256': '0'*64}))
            with self.assertRaises(DomainError):
                tools._validate_sta_binding(folder, sta, layout, runtime, inputs)
            (folder/'sta/sta-inputs.json').write_bytes(tools._bytes(manifest))
            with self.assertRaises(DomainError):
                tools._validate_sta_binding(folder, sta, layout, {'executable': '/OTHER'}, inputs)
            (folder/'sta/inputs/netlist.v').write_bytes(b'OTHER SOFTWARE QA NETLIST')
            with self.assertRaises(DomainError):
                tools._validate_sta_binding(folder, sta, layout, runtime, inputs)

    def test_timing_source_changes_invalidate_source_identity(self):
        runtime = self.layout['runtime_configuration']
        model_manifest = {'files': {relative: {'sha256': 'a'*64, 'bytes': 1} for relative in tools.MODEL_FILES.values()}}
        inventory = {'files': [{'relative_path': 'inputs/nom.spef', 'sha256': 'b'*64, 'bytes': 4}]}
        with patch.object(tools, '_configuration', return_value=(runtime, None, model_manifest, None)), \
                patch.object(tools.lvs_tools, 'source_inputs', return_value={}), \
                patch.object(tools.postroute_sta, 'source_inventory', return_value=inventory):
            before = copy.deepcopy(tools.source_inputs(self.layout, {}))
            self.assertEqual(before['timing_sources']['sha256'], object_hash(inventory))
            inventory['files'][0]['sha256'] = 'c'*64
            after = tools.source_inputs(self.layout, {})
            self.assertNotEqual(object_hash(before), object_hash(after))
            self.assertEqual(before['functional_testbench'], after['functional_testbench'])

    def test_frozen_functional_manifest_cannot_omit_an_input(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            tools._save(folder/'functional-inputs.json', {'files': []})
            with self.assertRaises(DomainError) as error:
                tools._validate_functional_inputs(folder, {}, {}, {})
            self.assertEqual(error.exception.code, 'postroute_source')


if __name__ == '__main__':
    unittest.main()
