"""Parser guards for new STA reports; these fixtures are not NPU evidence."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from hullcirq import postroute_sta as sta
from hullcirq.domain import DomainError
from hullcirq.postroute_sta import CORNERS, ENV_KEYS, SCHEMA, _environment, _layout_identifiers, _script, collect_sta, parse_corner
from hullcirq.verification import _wsl_path, object_hash


NETLIST = '''module hullcirq_npu(clk, out);
input clk;
output out;
sky130_fd_sc_hd__buf_1 clkload0 (.A(clk), .X());
sky130_fd_sc_hd__buf_1 logical (.A(clk), .X(out));
sky130_fd_sc_hd__fill_1 FILLER_0 ();
endmodule
'''
INVERTER_LIBERTY = '''library ("software_fixture") {
    cell ("sky130_fd_sc_hd__inv_6") {
        pin ("A") {
            direction : "input";
        }
        pin ("Y") {
            direction : "output";
            function : "(!A)";
            timing () { related_pin : "A"; }
        }
    }
}
'''


def fixture(**changes):
    metrics = {'setup_ws_ns': 18.2, 'hold_ws_ns': 0.1, 'setup_tns_ns': 0, 'hold_tns_ns': 0,
               'setup_violations': 0, 'hold_violations': 0, 'max_slew_violations': 0,
               'max_cap_violations': 0, 'max_fanout_violations': 0, 'clock_count': 1,
               'clock_period_ns': 50, 'clock_propagated': 1, 'clock_virtual': 0,
               'register_clock_pins': 1991}
    metrics.update(changes)
    sections = {'SETUP': 'Startpoint: logical\nEndpoint: out\nslack (MET)\n',
                'HOLD': 'Startpoint: logical\nEndpoint: out\nslack (MET)\n',
                'COVERAGE': '', 'ANNOTATION': 'Found 1 unannotated drivers.\n clkload0/X\nFound 0 partially unannotated drivers.\n',
                'ELECTRICAL': '', 'METRICS': '\n'.join(f'{key} {value}' for key, value in metrics.items()) + '\n'}
    if any(metrics[key] for key in ('max_slew_violations', 'max_cap_violations', 'max_fanout_violations')):
        sections['ELECTRICAL'] = 'logical/X 0.75 0.8 -0.05 (VIOLATED)\n'
    return ''.join(f'HULLCIRQ_BEGIN_{key}\n{value}HULLCIRQ_END_{key}\n' for key, value in sections.items()) + 'HULLCIRQ_STA_COMPLETE_' + CORNERS[0] + '\n'


class PostrouteStaTests(unittest.TestCase):
    def parse(self, text):
        return parse_corner(text, CORNERS[0], NETLIST, 50)

    def prepare_binding_fixture(self, root, top_module, clock_name, explicit_binding, annotation_policy=None):
        source = root / 'source'
        source.mkdir()
        appimage = source / 'runtime.AppImage'
        appimage.write_bytes(b'software QA pinned runtime')
        runtime_sha = sta.sha(appimage)
        runtime = {'appimage_sha256': runtime_sha, 'appimage_path': str(appimage),
                   'executable': _wsl_path(appimage)}
        layout = {'id': 'software-qa-layout',
                  'settings': {'top_module': top_module, 'clock_name': clock_name, 'clock_period_ns': 50},
                  'runtime_configuration': runtime}
        constraints = {key: (clock_name if key == 'CLOCK_PORT' else '50' if key == 'CLOCK_PERIOD' else '1')
                       for key in ENV_KEYS}
        environment = ''.join(f'set ::env({key}) {value}\n' for key, value in constraints.items()).encode('utf-8')
        inputs = {'inputs/netlist.v': f'module {top_module}(input {clock_name}); endmodule\n'.encode('utf-8'),
                  'inputs/physical.sdc': f'create_clock -name {clock_name} -period 50 [get_ports {clock_name}]\n'.encode('utf-8'),
                  'inputs/physical-final-state.json': b'{}\n',
                  **{f'inputs/{rc}.spef': (rc + ' SPEF\n').encode('utf-8') for rc in ('nom', 'min', 'max')},
                  **{f'inputs/{pvt}.lib': (INVERTER_LIBERTY if annotation_policy else pvt + ' Liberty\n').encode('utf-8')
                     for pvt in ('tt_025C_1v80', 'ss_100C_1v60', 'ff_n40C_1v95')},
                  **{f'inputs/{corner}.env.tcl': environment for corner in CORNERS}}
        files = []
        for relative, raw in inputs.items():
            path = source / relative.replace('/', '__')
            path.write_bytes(raw)
            files.append({'relative_path': relative, 'source_path': str(path),
                          'sha256': sta.sha(path), 'bytes': len(raw), 'origin': 'software_QA'})
        inventory = {'layout_run_id': layout['id'], 'layout_record_sha256': object_hash(layout),
                     'physical_runtime_sha256': object_hash(runtime), 'corners': list(CORNERS),
                     'clock_period_ns': 50, 'constraints': constraints, 'files': files}
        if explicit_binding:
            inventory.update(top_module=top_module, clock_name=clock_name)
        output = root / 'sta'
        with patch.object(sta.physical, 'IMAGE_SHA', runtime_sha), \
                patch.object(sta, 'source_inventory', return_value=inventory), \
                patch.object(sta, 'trusted_command', side_effect=lambda _configuration, executable, args, _cwd:
                             [executable, *args]):
            prepared = sta.prepare_sta(layout, runtime, output, annotation_policy=annotation_policy)
        return prepared, output, inventory, runtime_sha

    def test_finite_timing_and_unconnected_load_annotation_pass(self):
        report = self.parse(fixture())
        self.assertEqual(report['validation_status'], 'Passed')
        self.assertEqual(report['unconnected_clock_load_outputs'][0]['connection'], '')
        self.assertEqual(report['waivers'], [])

    def test_connected_unannotated_driver_fails(self):
        report = self.parse(fixture().replace(' clkload0/X\n', ' logical/X\n'))
        self.assertEqual(report['annotation_status'], 'Failed')
        self.assertEqual(report['unresolved_unannotated_drivers'], ['logical/X'])

    def test_original_openroad_omitted_clockload_output_is_unconnected(self):
        report = parse_corner(fixture(), CORNERS[0], NETLIST.replace(', .X()', ''), 50)
        self.assertEqual(report['annotation_status'], 'Passed')
        self.assertEqual(report['unconnected_clock_load_outputs'][0]['Verilog_representation'], 'omitted_named_port')
        report = parse_corner(fixture(), CORNERS[0], NETLIST.replace('.X()', '.X(out)'), 50)
        self.assertEqual(report['annotation_status'], 'Failed')

    def test_low_power_clock_inverter_unused_output_is_explicitly_classified(self):
        text = fixture().replace('clkload0/X', 'clkload0/Y')
        for binding in ('', ', .Y()'):
            netlist = NETLIST.replace('sky130_fd_sc_hd__buf_1 clkload0 (.A(clk), .X());',
                                     'sky130_fd_sc_hd__clkinvlp_4 clkload0 (.A(clk)' + binding + ');')
            report = parse_corner(text, CORNERS[0], netlist, 50)
            self.assertEqual(report['annotation_status'], 'Passed')
            self.assertEqual(report['unconnected_clock_load_outputs'][0]['cell'], 'sky130_fd_sc_hd__clkinvlp_4')
            self.assertEqual(report['waivers'], [])

    def test_low_power_clock_inverter_connected_or_unknown_output_still_fails(self):
        text = fixture().replace('clkload0/X', 'clkload0/Y')
        for cell, name, binding in (('clkinvlp_4', 'clkload0', ', .Y(out)'),
                                    ('clkinvlp_4', 'data_load', ''),
                                    ('unknown_4', 'clkload0', '')):
            netlist = NETLIST.replace('sky130_fd_sc_hd__buf_1 clkload0 (.A(clk), .X());',
                                     'sky130_fd_sc_hd__' + cell + ' ' + name + ' (.A(clk)' + binding + ');')
            report = parse_corner(text.replace('clkload0/Y', name + '/Y'), CORNERS[0], netlist, 50)
            self.assertEqual(report['annotation_status'], 'Failed')

    def test_v2_exact_unused_inv6_output_preserves_legacy_failure(self):
        text = fixture().replace('clkload0/X', 'clkload0/Y')
        for binding in ('', ', .Y()'):
            netlist = NETLIST.replace('sky130_fd_sc_hd__buf_1 clkload0 (.A(clk), .X());',
                                     'sky130_fd_sc_hd__inv_6 clkload0 (.A(clk)' + binding + ');')
            legacy = parse_corner(text, CORNERS[0], netlist, 50)
            self.assertEqual(legacy['annotation_status'], 'Failed')
            self.assertEqual(legacy['unresolved_unannotated_drivers'], ['clkload0/Y'])
            self.assertNotIn('annotation_policy', legacy)
            report = parse_corner(text, CORNERS[0], netlist, 50, annotation_policy=sta.ANNOTATION_V2)
            self.assertEqual(report['validation_status'], 'Passed')
            self.assertEqual(report['annotation_policy'], sta.ANNOTATION_V2)
            self.assertEqual(report['unconnected_clock_load_outputs'][0]['cell'], 'sky130_fd_sc_hd__inv_6')
            self.assertEqual(report['waivers'], [])

    def test_v2_does_not_ignore_connected_nonclock_missing_input_or_other_inverters(self):
        text = fixture().replace('clkload0/X', 'clkload0/Y')
        for cell, name, a, y in (('inv_6', 'clkload0', 'clk', ', .Y(out)'),
                                 ('inv_6', 'data_load', 'clk', ''),
                                 ('inv_6', 'clkload0', '', ''),
                                 ('inv_8', 'clkload0', 'clk', '')):
            netlist = NETLIST.replace('sky130_fd_sc_hd__buf_1 clkload0 (.A(clk), .X());',
                                     'sky130_fd_sc_hd__' + cell + ' ' + name + ' (.A(' + a + ')' + y + ');')
            report = parse_corner(text.replace('clkload0/Y', name + '/Y'), CORNERS[0], netlist, 50,
                                  annotation_policy=sta.ANNOTATION_V2)
            self.assertEqual(report['annotation_status'], 'Failed')

    def test_v2_annotation_classification_does_not_waive_electrical_failures(self):
        text = fixture(max_slew_violations=1).replace('clkload0/X', 'clkload0/Y')
        netlist = NETLIST.replace('sky130_fd_sc_hd__buf_1 clkload0 (.A(clk), .X());',
                                 'sky130_fd_sc_hd__inv_6 clkload0 (.A(clk));')
        report = parse_corner(text, CORNERS[0], netlist, 50, annotation_policy=sta.ANNOTATION_V2)
        self.assertEqual(report['annotation_status'], 'Passed')
        self.assertEqual(report['electrical_status'], 'Failed')
        self.assertEqual(report['validation_status'], 'Failed')
        self.assertEqual(report['metrics']['max_slew_violations'], 1)

    def test_unknown_annotation_policy_is_rejected(self):
        with self.assertRaises(DomainError):
            parse_corner(fixture(), CORNERS[0], NETLIST, 50, annotation_policy='unknown')
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            (folder / 'sta-inputs.json').write_text(json.dumps({'annotation_policy': 'unknown'}))
            with self.assertRaises(DomainError) as error:
                collect_sta(folder, {})
            self.assertEqual(error.exception.code, 'postroute_sta_annotation_policy')

    def test_partially_unannotated_driver_fails(self):
        self.assertEqual(self.parse(fixture().replace('Found 0 partially', 'Found 1 partially'))['validation_status'], 'Failed')

    def test_slew_cap_and_fanout_each_fail_independently(self):
        for key in ('max_slew_violations', 'max_cap_violations', 'max_fanout_violations'):
            with self.subTest(key=key):
                report = self.parse(fixture(**{key: 1}))
                self.assertEqual(report['electrical_status'], 'Failed')
                self.assertEqual(report['setup_hold_status'], 'Passed')

    def test_negative_hold_slack_fails(self):
        self.assertEqual(self.parse(fixture(hold_ws_ns=-0.001))['setup_hold_status'], 'Failed')

    def test_unconstrained_or_missing_clock_fails(self):
        self.assertEqual(self.parse(fixture().replace('HULLCIRQ_END_COVERAGE', 'Warning: unconstrained endpoint\nHULLCIRQ_END_COVERAGE'))['constraint_coverage_status'], 'Failed')
        for key, value in (('clock_propagated', 0), ('clock_virtual', 1), ('clock_period_ns', 100), ('register_clock_pins', 0)):
            with self.subTest(key=key):
                self.assertEqual(self.parse(fixture(**{key: value}))['constraint_coverage_status'], 'Failed')

    def test_missing_truncated_duplicate_and_nonfinite_metrics_rejected(self):
        for text in (fixture().replace('setup_ws_ns 18.2\n', ''), fixture().replace('HULLCIRQ_END_METRICS', ''),
                     fixture().replace('setup_ws_ns 18.2\n', 'setup_ws_ns 18.2\nsetup_ws_ns 18.2\n'),
                     fixture(setup_ws_ns=float('nan')), fixture(clock_count=0.5)):
            with self.subTest(text=text[-100:]):
                with self.assertRaises((DomainError, ValueError)):
                    self.parse(text)

    def test_counter_and_electrical_report_disagreement_rejected(self):
        with self.assertRaises(DomainError):
            self.parse(fixture(max_cap_violations=1).replace(' (VIOLATED)', ' (MET)'))

    def test_unlinked_logic_model_fails(self):
        report = self.parse('Warning: design.v line 3, module logic not found. Creating black box for logical.\n' + fixture())
        self.assertEqual(report['timing_model_coverage_status'], 'Failed')

    def test_power_only_physical_blackbox_retained_and_classified(self):
        warning = 'Warning: design.v line 3, module sky130_fd_sc_hd__fill_1 not found. Creating black box for FILLER_0.\n'
        report = self.parse(warning + fixture())
        self.assertEqual(report['validation_status'], 'Passed')
        self.assertEqual(len(report['warnings']), 1)

    def test_missing_real_paths_and_annotation_count_rejected(self):
        for text in (fixture().replace('Startpoint: logical', 'No paths found.'), fixture().replace('Found 1 unannotated', 'Found 2 unannotated')):
            with self.assertRaises(DomainError):
                self.parse(text)

    def test_constraint_environment_requires_unique_complete_scalars(self):
        with self.assertRaises(DomainError):
            _environment('set ::env(CLOCK_PERIOD) 50\n')

    def test_saved_top_and_clock_identifiers_drive_script_without_changing_legacy_defaults(self):
        values = {key: '1' for key in ENV_KEYS}
        files = {key: Path(tempfile.gettempdir()) / (key + '.txt')
                 for key in ('liberty', 'netlist', 'sdc', 'spef')}
        legacy = _script(CORNERS[0], values, files).decode('utf-8')
        self.assertIn('link_design hullcirq_npu\n', legacy)
        self.assertIn('set clock [get_clocks clk]\n', legacy)
        explicit = _script(CORNERS[0], values, files, 'hullcirq_npu2_top', 'core_clk').decode('utf-8')
        self.assertIn('link_design hullcirq_npu2_top\n', explicit)
        self.assertIn('set clock [get_clocks core_clk]\n', explicit)
        escaped = _script(CORNERS[0], values, files, 'dut$mapped', 'clk$core').decode('utf-8')
        self.assertIn('link_design {dut$mapped}\n', escaped)
        self.assertIn('set clock [get_clocks {clk$core}]\n', escaped)

    def test_saved_top_and_clock_identifiers_are_strictly_validated(self):
        self.assertEqual(_layout_identifiers({'settings': {'top_module': 'hullcirq_npu2_top',
                                                           'clock_name': 'clk'}}),
                         ('hullcirq_npu2_top', 'clk'))
        for top, clock in (('module', 'clk'), ('bad;top', 'clk'), ('safe_top', 'always'),
                           ('safe_top', 'clock name'), (None, 'clk')):
            with self.subTest(top=top, clock=clock), self.assertRaises(DomainError):
                _layout_identifiers({'settings': {'top_module': top, 'clock_name': clock}})

    def test_prepare_binds_saved_identifiers_and_collect_reproduces_their_scripts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepared, output, inventory, runtime_sha = self.prepare_binding_fixture(
                root, 'hullcirq_npu2_top', 'core_clk', True)
            self.assertEqual(prepared['manifest']['top_module'], 'hullcirq_npu2_top')
            self.assertEqual(prepared['manifest']['clock_name'], 'core_clk')
            script_path = output / 'scripts' / (CORNERS[0] + '.tcl')
            script = script_path.read_text(encoding='utf-8')
            self.assertIn('link_design hullcirq_npu2_top\n', script)
            self.assertIn('set clock [get_clocks core_clk]\n', script)

            script_path.write_text(script.replace('link_design hullcirq_npu2_top', 'link_design substituted_top'),
                                   encoding='utf-8', newline='')
            manifest = sta.load(output / 'sta-inputs.json')
            item = next(item for item in manifest['files'] if item['relative_path'] == 'scripts/' + CORNERS[0] + '.tcl')
            item.update(sha256=sta.sha(script_path), bytes=script_path.stat().st_size)
            (output / 'sta-inputs.json').write_bytes(sta._json(manifest))
            with patch.object(sta.physical, 'IMAGE_SHA', runtime_sha), \
                    patch.object(sta.physical, 'SDC_SHA', sta.sha(output / 'inputs/physical.sdc')), \
                    patch.object(sta, 'source_inventory', return_value=inventory), \
                    self.assertRaises(DomainError) as error:
                collect_sta(output, {corner: {} for corner in CORNERS})
            self.assertEqual(error.exception.code, 'postroute_sta_source')
            self.assertEqual(str(error.exception), 'The actual STA script must reproduce the fixed analysis recipe.')

    def test_v2_manifest_binds_all_pvt_liberty_qualification_without_changing_scripts(self):
        with tempfile.TemporaryDirectory() as directory:
            prepared, output, inventory, runtime_sha = self.prepare_binding_fixture(
                Path(directory), 'hullcirq_npu2_top', 'clk', True, sta.ANNOTATION_V2)
            manifest = prepared['manifest']
            self.assertEqual(manifest['annotation_policy'], sta.ANNOTATION_V2)
            proof = manifest['annotation_policy_qualification']
            self.assertEqual(proof['cell'], 'sky130_fd_sc_hd__inv_6')
            self.assertEqual(len(proof['liberty_models']), 3)
            self.assertTrue(all(model['input_direction'] == 'input' and model['output_direction'] == 'output'
                                and model['output_function'] == '!A' for model in proof['liberty_models']))
            self.assertEqual((output / 'run_sta.py').read_bytes(), sta.LAUNCHER)
            corner = CORNERS[0]
            expected_script = _script(corner, inventory['constraints'], {
                'netlist': output / 'inputs/netlist.v', 'sdc': output / 'inputs/physical.sdc',
                'spef': output / 'inputs/nom.spef', 'liberty': output / 'inputs/tt_025C_1v80.lib'},
                'hullcirq_npu2_top', 'clk')
            self.assertEqual((output / 'scripts' / (corner + '.tcl')).read_bytes(), expected_script)
            self.assertEqual(len(prepared['commands']), 9)

            manifest['annotation_policy_qualification']['liberty_models'].pop()
            (output / 'sta-inputs.json').write_bytes(sta._json(manifest))
            with patch.object(sta.physical, 'IMAGE_SHA', runtime_sha), self.assertRaises(DomainError) as error:
                collect_sta(output, {corner: {} for corner in CORNERS})
            self.assertEqual(error.exception.code, 'postroute_sta_annotation_model')

    def test_v2_qualification_rejects_different_direction_function_and_missing_model(self):
        with tempfile.TemporaryDirectory() as directory:
            _, _, inventory, _ = self.prepare_binding_fixture(
                Path(directory), 'hullcirq_npu2_top', 'clk', True, sta.ANNOTATION_V2)
            item = next(item for item in inventory['files'] if item['relative_path'] == 'inputs/ss_100C_1v60.lib')
            path = Path(item['source_path'])
            raw = path.read_bytes()
            for changed in (raw.replace(b'direction : "output";', b'direction : "input";'),
                            raw.replace(b'function : "(!A)";', b'function : "A";'),
                            raw.replace(b'pin ("Y")', b'pin ("Z")')):
                path.write_bytes(changed)
                item.update(sha256=sta.sha(path), bytes=len(changed))
                with self.assertRaises(DomainError):
                    sta._annotation_qualification(inventory['files'])
            path.write_bytes(raw)
            item.update(sha256=sta.sha(path), bytes=len(raw))
            with self.assertRaises(DomainError):
                sta._annotation_qualification([entry for entry in inventory['files'] if entry is not item])

    def test_legacy_manifest_without_identifiers_is_valid_only_for_exact_legacy_binding(self):
        with tempfile.TemporaryDirectory() as directory:
            prepared, output, inventory, runtime_sha = self.prepare_binding_fixture(
                Path(directory), 'hullcirq_npu', 'clk', False)
            self.assertNotIn('top_module', inventory)
            self.assertNotIn('clock_name', inventory)
            self.assertNotIn('top_module', prepared['manifest'])
            self.assertNotIn('clock_name', prepared['manifest'])
            self.assertNotIn('annotation_policy', prepared['manifest'])
            self.assertNotIn('annotation_policy_qualification', prepared['manifest'])
            self.assertEqual(prepared['manifest']['source_inventory_sha256'], object_hash(inventory))
            script = (output / 'scripts' / (CORNERS[0] + '.tcl')).read_text(encoding='utf-8')
            self.assertIn('link_design hullcirq_npu\n', script)
            self.assertIn('set clock [get_clocks clk]\n', script)

            with patch.object(sta.physical, 'IMAGE_SHA', runtime_sha), \
                    patch.object(sta.physical, 'SDC_SHA', sta.sha(output / 'inputs/physical.sdc')), \
                    patch.object(sta, 'source_inventory', return_value=inventory), \
                    self.assertRaises(DomainError) as accepted_source:
                collect_sta(output, {corner: {} for corner in CORNERS})
            self.assertEqual(accepted_source.exception.code, 'postroute_sta_execution')

            wrong = {**inventory, 'top_module': 'hullcirq_npu2_top', 'clock_name': 'clk'}
            with patch.object(sta.physical, 'IMAGE_SHA', runtime_sha), \
                    patch.object(sta.physical, 'SDC_SHA', sta.sha(output / 'inputs/physical.sdc')), \
                    patch.object(sta, 'source_inventory', return_value=wrong), \
                    self.assertRaises(DomainError) as rejected_source:
                collect_sta(output, {corner: {} for corner in CORNERS})
            self.assertEqual(rejected_source.exception.code, 'postroute_sta_source')

    def test_collector_rejects_missing_corner(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            (folder / 'sta-inputs.json').write_text(json.dumps({'schema': SCHEMA, 'corners': list(CORNERS), 'files': []}))
            with self.assertRaises(DomainError):
                collect_sta(folder, {CORNERS[0]: {'executed': True}})

    def test_collector_rejects_changed_frozen_input(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            (folder / 'source.txt').write_bytes(b'changed')
            (folder / 'sta-inputs.json').write_text(json.dumps({'schema': SCHEMA, 'corners': list(CORNERS),
                'files': [{'relative_path': 'source.txt', 'sha256': '0' * 64, 'bytes': 7, 'source_path': None}]}))
            with self.assertRaises(DomainError):
                collect_sta(folder, {c: {} for c in CORNERS})

    def test_collector_rejects_unexecuted_or_failed_tools(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            (folder / 'inputs').mkdir()
            (folder / 'inputs/netlist.v').write_text(NETLIST)
            (folder / 'sta-inputs.json').write_text(json.dumps({'schema': SCHEMA, 'corners': list(CORNERS), 'files': []}))
            for record in ({'executed': False}, {'executed': True, 'status': 'Completed', 'exit_code': 1}):
                with self.assertRaises(DomainError):
                    collect_sta(folder, {c: record for c in CORNERS})


if __name__ == '__main__':
    unittest.main()
