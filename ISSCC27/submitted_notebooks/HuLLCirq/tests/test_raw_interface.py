"""Software checks for explicit raw boundaries; no circuit proof is claimed."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from hullcirq.context import build_node_context, node_fingerprint, physical_interface
from hullcirq.domain import DomainError, validate_shape, validate_stage
from hullcirq.store import ProjectStore


def fixture():
    design = json.loads((ROOT / 'examples/m1_two_nodes.json').read_text(encoding='utf-8'))
    for node in design['nodes']:
        direction = node['ports'][0]['direction']
        stream_id = node['ports'][0]['id']
        prefix = node['id']
        node['ports'].append({'id': prefix + '-meta', 'name': 'pair_meta', 'direction': direction,
                              'width': 6, 'signed': False, 'protocol': 'raw', 'clock': 'clk', 'reset': 'rst',
                              'sideband': {'kind': 'metadata', 'associated_port_id': stream_id,
                                           'meaning': 'Lane[3:0], first[4], last[5], synchronous with the stream.',
                                           'fields': [{'name': 'lane', 'lsb': 0, 'width': 4}],
                                           'user_extension': {'preserve': True}}})
        node['ports'].append({'id': prefix + '-pulse', 'name': 'pe_clear', 'direction': direction,
                              'width': 1, 'signed': False, 'protocol': 'raw', 'clock': 'clk', 'reset': 'rst',
                              'sideband': {'kind': 'pulse', 'associated_port_id': None,
                                           'meaning': 'Independent synchronous one-cycle clear.'}})
    design['edges'].append({'id': 'edge-raw-metadata', 'source': {'node_id': 'node-producer', 'port_id': 'node-producer-meta'},
                            'target': {'node_id': 'node-consumer', 'port_id': 'node-consumer-meta'},
                            'protocol': 'raw', 'behavior': 'Metadata accompanies the existing data stream and remains stable while stalled.'})
    return design


class RawInterfaceTests(unittest.TestCase):
    def errors(self, design, stage='graph_editor'):
        validate_shape(design)
        return [finding for finding in validate_stage(design, stage) if finding['severity'] == 'error']

    def test_explicit_raw_ports_have_one_signal_and_preserve_sideband_fields(self):
        design = fixture()
        node = design['nodes'][0]
        interface = physical_interface(design, node)
        self.assertEqual([p['name'] for p in interface['ports']], ['clk', 'rst', 'data_out', 'data_out_valid', 'data_out_ready', 'pair_meta', 'pe_clear'])
        metadata = interface['ports'][-2]
        self.assertEqual(metadata['role'], 'sideband')
        self.assertEqual(metadata['protocol'], 'raw')
        self.assertEqual(metadata['sideband'], node['ports'][1]['sideband'])
        metadata['sideband']['user_extension']['preserve'] = False
        self.assertTrue(node['ports'][1]['sideband']['user_extension']['preserve'])
        preview = build_node_context(design, 'software-qa-revision', node['id'])
        self.assertIn('output wire [5:0] pair_meta', preview['requested_module_header'])
        self.assertNotIn('pair_meta_valid', preview['requested_module_header'])
        self.assertIn('no extra valid/ready signals', preview['messages'][0]['content'])

    def test_raw_graph_and_node_protocol_exception_pass_all_input_checks(self):
        design = fixture()
        for stage in ('global_settings', 'graph_editor', 'specifications'):
            self.assertFalse(self.errors(design, stage), stage)
        self.assertEqual(design['nodes'][0]['constraints']['protocol'], 'valid_ready')

    def test_metadata_requires_explicit_same_node_stream_association(self):
        for association in (None, 'missing', 'node-producer-meta', 'port-consumer-data'):
            with self.subTest(association=association):
                design = fixture()
                design['nodes'][0]['ports'][1]['sideband']['associated_port_id'] = association
                self.assertTrue(self.errors(design))
                self.assertTrue(self.errors(design, 'specifications'))
                with self.assertRaises(DomainError):
                    physical_interface(design, design['nodes'][0])

    def test_association_direction_and_domain_must_match(self):
        for field, value in (('direction', 'input'), ('clock', 'other_clock'), ('reset', 'other_reset')):
            with self.subTest(field=field):
                design = fixture()
                design['nodes'][0]['ports'][1][field] = value
                self.assertIn('sideband_' + field + '_mismatch', [f['code'] for f in self.errors(design)])
                with self.assertRaises(DomainError):
                    physical_interface(design, design['nodes'][0])

    def test_independent_pulse_is_one_bit_unsigned_and_global_domain(self):
        for field, value in (('width', 2), ('signed', True), ('clock', 'other_clock'), ('reset', 'other_reset')):
            with self.subTest(field=field):
                design = fixture()
                design['nodes'][0]['ports'][2][field] = value
                self.assertTrue(self.errors(design))
                with self.assertRaises(DomainError):
                    physical_interface(design, design['nodes'][0])

    def test_independent_level_retains_one_bit_interface_and_rejects_wide_signed(self):
        design = fixture()
        port = design['nodes'][0]['ports'][2]
        port['name'] = 'busy'
        port['sideband'] = {'kind': 'level', 'associated_port_id': None}
        self.assertFalse(self.errors(design))
        self.assertEqual(physical_interface(design, design['nodes'][0])['ports'][-1]['sideband']['kind'], 'level')
        for field, value in (('width', 2), ('signed', True)):
            changed = copy.deepcopy(design)
            changed['nodes'][0]['ports'][2][field] = value
            self.assertIn('invalid_sideband_level', [item['code'] for item in self.errors(changed)])

    def test_raw_declaration_types_are_strict_but_electrical_drafts_remain_editable(self):
        for sideband in ([], {'kind': True, 'associated_port_id': None}, {'kind': 'pulse', 'associated_port_id': 3}, {'kind': 'pulse'}):
            with self.subTest(sideband=sideband):
                design = fixture()
                design['nodes'][0]['ports'][2]['sideband'] = sideband
                with self.assertRaises(DomainError):
                    validate_shape(design)
        design = fixture()
        del design['nodes'][0]['ports'][2]['sideband']
        self.assertIn('invalid_sideband', [f['code'] for f in self.errors(design)])

    def test_raw_names_colliding_with_implicit_handshake_clock_reset_are_rejected(self):
        for name in ('data_out', 'data_out_valid', 'data_out_ready', 'clk', 'rst'):
            with self.subTest(name=name):
                design = fixture()
                design['nodes'][0]['ports'][2]['name'] = name
                self.assertIn('interface_collision', [f['code'] for f in self.errors(design)])
                with self.assertRaises(DomainError):
                    physical_interface(design, design['nodes'][0])

    def test_raw_edge_requires_matching_typed_boundary_and_protocol(self):
        for field, value, expected in (('width', 5, 'edge_width_mismatch'), ('signed', True, 'edge_signed_mismatch'),
                                      ('direction', 'output', 'edge_direction'), ('protocol', 'valid_ready', 'edge_protocol_mismatch')):
            with self.subTest(field=field):
                design = fixture()
                design['nodes'][1]['ports'][1][field] = value
                self.assertIn(expected, [f['code'] for f in self.errors(design)])
        design = fixture()
        design['nodes'][1]['ports'][1]['sideband']['kind'] = 'pulse'
        self.assertIn('edge_sideband_kind_mismatch', [f['code'] for f in self.errors(design)])

    def test_raw_width_bool_and_signed_nonboolean_reject_shape(self):
        for field, value in (('width', True), ('signed', 'false')):
            design = fixture()
            design['nodes'][0]['ports'][1][field] = value
            with self.assertRaises(DomainError):
                validate_shape(design)

    def test_original_pe_context_and_all_six_saved_prompts_are_unchanged(self):
        source = ROOT / 'results/npu_pe_continuous_flow'
        state = json.loads((source / 'state.json').read_text(encoding='utf-8'))
        generation = json.loads((source / 'generation.json').read_text(encoding='utf-8'))
        for job in generation['jobs']:
            saved = job['context']
            previous = None if job['base_job_id'] is None else next(item for item in generation['jobs'] if item['id'] == job['base_job_id'])['rtl']
            # Diagnostics are at the prompt payload level, rather than source.
            payload = json.loads(saved['messages'][1]['content'].split('\nRequired interface header')[0])
            rebuilt = build_node_context(state['snapshots'][job['revision_id']], job['revision_id'], job['node_id'],
                                        job['instruction'], previous, payload['selected_diagnostics'], saved['prompt_template_version'])
            for field in ('context', 'interface', 'messages', 'prompt_text', 'node_input_hash', 'requested_module_header'):
                self.assertEqual(rebuilt[field], saved[field], (job['id'], field))

    def test_import_and_save_retain_unknown_raw_metadata_without_schema_migration(self):
        design = fixture()
        with tempfile.TemporaryDirectory() as temporary:
            store = ProjectStore(Path(temporary))
            envelope = store.envelope()
            imported = store.save(design, envelope['revision']['id'])
            exported = store.envelope()['design']
            self.assertEqual(exported, design)
            self.assertEqual(exported['schema_version'], '0.1')
            self.assertEqual(imported['design']['nodes'][0]['ports'][1]['sideband'], design['nodes'][0]['ports'][1]['sideband'])

    def test_scheduler_fingerprint_and_context_include_only_the_referenced_current_job(self):
        design = fixture()
        job = {'id': 'software-qa-matrix', 'matrix_a': [[1]], 'matrix_b': [[2]]}
        design['verification_jobs'] = [copy.deepcopy(job), {'id': 'unrelated-job', 'data': [9]}]
        node = design['nodes'][0]
        node['verification'] = {'kind': 'npu_scheduler_stream', 'source_job': copy.deepcopy(job)}
        before = node_fingerprint(design, node['id'])
        preview = build_node_context(design, 'software-qa-revision', node['id'])
        self.assertEqual(preview['context']['design_verification_job'], job)
        changed = copy.deepcopy(design)
        changed['verification_jobs'][1]['data'][0] = 10
        self.assertEqual(node_fingerprint(changed, node['id']), before)
        changed['verification_jobs'][0]['matrix_a'][0][0] = 3
        self.assertNotEqual(node_fingerprint(changed, node['id']), before)
        self.assertEqual(build_node_context(changed, 'new-revision', node['id'])['context']['design_verification_job']['matrix_a'], [[3]])

    def test_missing_or_duplicate_scheduler_jobs_never_fall_back_to_the_copied_contract_job(self):
        design = fixture()
        job = {'id': 'software-qa-matrix', 'matrix_a': [[1]]}
        design['verification_jobs'] = [job]
        node = design['nodes'][0]
        node['verification'] = {'kind': 'npu_scheduler_stream', 'source_job': copy.deepcopy(job)}
        before = node_fingerprint(design, node['id'])
        for current_jobs, status in (([], 'missing'), ([job, job], 'ambiguous'), (None, 'invalid_job_list')):
            with self.subTest(status=status):
                changed = copy.deepcopy(design)
                changed['verification_jobs'] = copy.deepcopy(current_jobs)
                preview = build_node_context(changed, 'new-revision', node['id'])
                self.assertIsNone(preview['context']['design_verification_job'])
                self.assertEqual(preview['context']['design_verification_job_lookup']['status'], status)
                self.assertNotEqual(node_fingerprint(changed, node['id']), before)
                # Invalid raw drafts still observe global job changes via fallback.
                changed['nodes'][0]['ports'][1]['sideband']['associated_port_id'] = 'missing'
                invalid_before = node_fingerprint(changed, node['id'])
                changed['verification_jobs'] = [dict(job, matrix_a=[[8]])]
                self.assertNotEqual(node_fingerprint(changed, node['id']), invalid_before)


if __name__ == '__main__':
    unittest.main()
