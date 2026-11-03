"""Pure fixture checks for explicit external wiring; no model or native EDA."""
import copy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from hullcirq import generic_global_verification as generic, global_generation as generation, external_io
from hullcirq.context import physical_interface
from hullcirq.domain import DomainError
from hullcirq.workspace import blank_design


def fixture(array=False):
    design = blank_design('fixture-project', 'Fixture only', 'fixture-system', 'Fixture only', 'fixture_top')
    design['settings'].update(clock_name='clock_x', reset_name='reset_x')
    node = {'id': '3-arbitrary-node', 'name': 'Fixture scalar', 'module_name': 'fixture_scalar', 'parent_id': None,
            'behavior': 'Software fixture specification.', 'test_expectations': 'Software fixture only.',
            'constraints': {'latency_cycles': 1, 'protocol': 'valid_ready'}, 'ports': []}
    for name, direction in [('in_data', 'input'), ('out_data', 'output')]:
        node['ports'].append({'id': 'node-'+name, 'name': name, 'direction': direction, 'width': 4,
                              'signed': False, 'protocol': 'valid_ready', 'clock': 'clock_x', 'reset': 'reset_x'})
    if array: node['instance_array'] = {'rows': 1, 'columns': 2}
    design['nodes'] = [node]
    members = [[0, 0], [0, 1]] if array else [None]
    for member in members:
        suffix = f'_r{member[0]}c{member[1]}' if member is not None else ''
        for name, direction, node_port in [('public_in', 'input', 'in_data'), ('public_out', 'output', 'out_data')]:
            identifier = name+suffix
            design['external_io']['ports'].append({'id': identifier, 'name': identifier, 'direction': direction,
                                                   'width': 4, 'signed': False, 'protocol': 'valid_ready'})
            design['external_io']['connections'].append({'id': 'bind-'+identifier, 'external_port_id': identifier,
                'node_id': node['id'], 'port_id': 'node-'+node_port,
                **({'instance_index': member} if member is not None else {})})
    ports = external_io.expanded_ports(design)
    design['global_integration'] = {'public_ports': ports, 'behavior': 'Connect the explicitly saved fixture boundary.'}
    inputs = {p['name']: 0 for p in ports if p['direction'] == 'input'}
    outputs = {p['name']: 0 for p in ports if p['direction'] == 'output'}
    changed = {k: 1 for k in inputs}
    design['global_verification'] = {'kind': 'generic_cycle_vectors', 'version': 1, 'cycles': [
        {'reset': 1, 'drive': inputs, 'expect': outputs}, {'reset': 0, 'drive': changed, 'expect': outputs}]}
    manifest = {'design': design, 'nodes': [{'node_id': node['id'], 'module_name': node['module_name'],
                                           'public_interface': physical_interface(design, node), 'rtl': '// fixture only'}]}
    return manifest


def rtl_fixture(manifest, aliases=False):
    design = manifest['design']; interface = generic.top_interface(design)
    def declaration(port):
        return port['direction'] + (' signed' if port['signed'] else '') + (f" [{port['width']-1}:0]" if port['width'] > 1 else '') + ' ' + port['name']
    lines = ['module fixture_top('+', '.join(map(declaration, interface['ports']))+');']
    binds = external_io.bindings(design)
    for instance in generic.external_instances(design):
        pins = {'clock_x': 'clock_x', 'reset_x': 'reset_x'}
        for binding in binds:
            if binding['node_id'] != instance['node_id'] or binding.get('instance_index') != instance.get('instance_index'): continue
            name = binding['external_name']
            if aliases:
                wire = 'wire_'+name
                lines.append('wire'+(' signed' if binding['signed'] else '')+(f" [{binding['width']-1}:0]" if binding['width'] > 1 else '')+' '+wire+';')
                lines.append(f'assign {wire} = {name};' if binding['direction'] == 'input' else f'assign {name} = {wire};')
                name = wire
            pins[binding['node_pin']] = name
        lines.append(instance['module_name']+' '+instance['instance_name']+'('+', '.join(f'.{pin}({signal})' for pin, signal in pins.items())+');')
    return '\n'.join(lines+['endmodule'])


class ExternalIoGenerationTests(unittest.TestCase):
    def assertRejected(self, rtl, manifest):
        result = generic.check_external_wiring(rtl, manifest)
        self.assertEqual(result['validation_status'], 'Failed', result)
        self.assertTrue(result['diagnostics'])

    def test_exact_direct_mapping_includes_reverse_ready_and_controls(self):
        manifest = fixture(); result = generic.check_external_wiring(rtl_fixture(manifest), manifest)
        self.assertEqual(result['validation_status'], 'Passed', result)
        self.assertEqual(result['checked_signal_count'], 6)
        self.assertIn(('public_in_ready', 'in_data_ready', 'output'),
                      [(r['external_name'], r['node_pin'], r['direction']) for r in result['connections']])
        self.assertEqual(len(result['instances']), 1)

    def test_plain_typed_wire_aliases_are_verified(self):
        manifest = fixture(); result = generic.check_external_wiring(rtl_fixture(manifest, True), manifest)
        self.assertEqual(result['validation_status'], 'Passed', result)
        self.assertEqual(len(result['aliases']), 6)

    def test_top_declaration_must_match_explicit_types(self):
        manifest = fixture(); manifest['design']['global_integration']['public_ports'][0]['width'] = 3
        with self.assertRaises(DomainError): generic.top_interface(manifest['design'])

    def test_duplicate_top_declaration_is_not_silently_collapsed(self):
        manifest = fixture(); ports = manifest['design']['global_integration']['public_ports']
        ports.append(copy.deepcopy(ports[0]))
        with self.assertRaises(DomainError): generic.top_interface(manifest['design'])

    def test_wiring_mismatch_is_rejected_before_native_tool_start(self):
        manifest = fixture(); rtl = rtl_fixture(manifest).replace('.in_data(public_in)', '.in_data(public_out)')
        self.assertRejected(rtl, manifest)
        with patch.object(generation, 'execute_fixed', side_effect=AssertionError('No EDA permitted')) as execute:
            result = generation.check_global_rtl(rtl, manifest, generation.build_global_plan(manifest['design']), None)
        execute.assert_not_called()
        self.assertEqual(result['validation_status'], 'Failed')
        self.assertFalse(result['executed'])

    def test_reverse_ready_cannot_be_replaced_with_valid(self):
        manifest = fixture(); self.assertRejected(rtl_fixture(manifest).replace('.out_data_ready(public_out_ready)', '.out_data_ready(public_in_valid)'), manifest)

    def test_clock_and_reset_cannot_be_swapped(self):
        manifest = fixture(); self.assertRejected(rtl_fixture(manifest).replace('.clock_x(clock_x)', '.clock_x(reset_x)'), manifest)

    def test_alias_cycles_are_rejected_even_when_unused(self):
        manifest = fixture(); self.assertRejected(rtl_fixture(manifest).replace('endmodule', 'wire a,b; assign a=b; assign b=a; endmodule'), manifest)

    def test_multiple_drivers_are_rejected(self):
        manifest = fixture(); self.assertRejected(rtl_fixture(manifest).replace('endmodule', 'assign public_out = public_in; endmodule'), manifest)

    def test_alias_width_conversion_is_rejected(self):
        manifest = fixture(); self.assertRejected(rtl_fixture(manifest, True).replace('wire [3:0] wire_public_in;', 'wire [2:0] wire_public_in;'), manifest)

    def test_constant_and_expression_connections_fail_closed(self):
        manifest = fixture(); rtl = rtl_fixture(manifest)
        for expression in ["4'b0", 'public_in + public_out', 'public_in[3:0]', '{public_in}']:
            with self.subTest(expression=expression):
                self.assertRejected(rtl.replace('.in_data(public_in)', f'.in_data({expression})'), manifest)

    def test_behavioral_logic_is_not_a_wiring_only_top(self):
        manifest = fixture(); self.assertRejected(rtl_fixture(manifest).replace('endmodule', 'always @(*) begin end endmodule'), manifest)

    def test_missing_extra_or_renamed_instances_are_rejected(self):
        manifest = fixture(); rtl = rtl_fixture(manifest); instance = generic.external_instances(manifest['design'])[0]['instance_name']
        self.assertRejected(rtl.replace(instance, 'unrequested_instance'), manifest)
        line = next(line for line in rtl.splitlines() if line.startswith('fixture_scalar '))
        self.assertRejected(rtl.replace(line, ''), manifest)
        self.assertRejected(rtl.replace('endmodule', line+'\nendmodule'), manifest)

    def test_arbitrary_ids_have_unique_plain_instance_names(self):
        manifest = fixture(); names = []
        for identifier in ['a-b', 'a_b', '3-node', 'u_encoded_61']:
            design = copy.deepcopy(manifest['design']); design['nodes'][0]['id'] = identifier
            names.append(generic.external_instances(design)[0]['instance_name'])
        self.assertEqual(len(set(names)), 4)
        self.assertTrue(all(generic.identifier(name) for name in names))

    def test_array_members_have_distinct_verified_bindings(self):
        manifest = fixture(True); result = generic.check_external_wiring(rtl_fixture(manifest), manifest)
        self.assertEqual(result['validation_status'], 'Passed', result)
        self.assertEqual(result['checked_signal_count'], 12)
        self.assertEqual(len(result['instances']), 2)
        self.assertRejected(rtl_fixture(manifest).replace('.in_data(public_in_r0c0)', '.in_data(public_in_r0c1)'), manifest)

    def test_v7_projection_contains_exact_bindings_and_no_reference_values(self):
        manifest = fixture(); before = copy.deepcopy(manifest)
        self.assertEqual(generic.EXTERNAL_PROMPT, generation.PROMPT_TEMPLATE_V7)
        projection = generation.integration_projection(manifest, generation.PROMPT_TEMPLATE_V7)
        self.assertEqual(projection['external_connections'], external_io.bindings(manifest['design']))
        self.assertEqual(projection['required_direct_instances'], generic.external_instances(manifest['design']))
        self.assertNotIn('global_verification', projection)
        self.assertNotIn('cycles', repr(projection))
        messages = generation.integration_messages(manifest, '', template_version=generation.PROMPT_TEMPLATE_V7)
        self.assertIn('external_connections is the authoritative', messages[-1]['content'])
        self.assertEqual(manifest, before)

    def test_legacy_v6_projection_and_no_extra_proof_remain(self):
        manifest = fixture(); manifest['design'].pop('external_io')
        self.assertEqual(generation.prompt_template(manifest['design']), generation.PROMPT_TEMPLATE_V6)
        self.assertNotIn('external_connections', generation.integration_projection(manifest))
        self.assertIsNone(generic.check_external_wiring('', manifest))
        self.assertTrue(generic.external_wiring_proof_matches({}, manifest))

    def test_saved_wiring_proof_and_version_must_reconstruct(self):
        manifest = fixture(); rtl = rtl_fixture(manifest); proof = generic.check_external_wiring(rtl, manifest)
        job = {'rtl': rtl, 'context': {'template_version': generic.EXTERNAL_PROMPT}, 'checks': {
            'external_io_wiring_proof': proof, 'checks': {'external_io_wiring': {'validation_status': 'Passed'}}}}
        self.assertTrue(generic.external_wiring_proof_matches(job, manifest))
        changed = copy.deepcopy(job); changed['checks']['external_io_wiring_proof']['connections'][0]['external_name'] = 'changed'
        self.assertFalse(generic.external_wiring_proof_matches(changed, manifest))
        changed = copy.deepcopy(job); changed['context']['template_version'] = generic.PROMPT
        self.assertFalse(generic.external_wiring_proof_matches(changed, manifest))
        changed = copy.deepcopy(job); changed['checks'].pop('external_io_wiring_proof')
        self.assertFalse(generic.external_wiring_proof_matches(changed, manifest))


if __name__ == '__main__': unittest.main()
