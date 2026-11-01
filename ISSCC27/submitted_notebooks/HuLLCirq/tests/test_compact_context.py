"""Lossless prompt rendering for original GUI-saved verification vectors."""
import json
import copy
import hashlib
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from hullcirq.context import build_node_context, decode_field_row_table, field_row_table
from hullcirq.verification import build_verification_plan, object_hash, verification_template_version


def decode_prompt_source(source):
    decoded = copy.deepcopy(source)
    decoded['node']['ports'] = decode_field_row_table(source['node']['ports'])
    decoded['physical_interface']['ports'] = decode_field_row_table(source['physical_interface']['ports'])
    for peer, original in zip(decoded['adjacent_interfaces'], source['adjacent_interfaces'], strict=True):
        peer['ports'] = decode_field_row_table(original['ports'])
    return decoded


class CompactContextTests(unittest.TestCase):
    def test_full_initial_contract_is_preserved_while_rendering_fits_budget(self):
        design = json.loads((ROOT / 'examples/npu_project.json').read_text(encoding='utf-8'))
        old = build_node_context(design, 'same-snapshot', 'node-pe', template_version='node-verilog-2005-v4')
        new = build_node_context(design, 'same-snapshot', 'node-pe', template_version='node-verilog-2005-v6')
        self.assertEqual(old['context'], new['context'])
        self.assertEqual(old['node_input_hash'], new['node_input_hash'])
        self.assertEqual(old['requested_module_header'], new['requested_module_header'])
        delimiter = '\nRequired interface header'
        old_payload = json.loads(old['messages'][1]['content'].split(delimiter)[0])
        new_payload = json.loads(new['messages'][1]['content'].split(delimiter)[0])
        self.assertEqual(old_payload, new_payload)
        self.assertEqual(new['prompt_template_version'], 'node-verilog-2005-v6')
        self.assertLess(new['estimated_input_tokens'], old['estimated_input_tokens'])
        self.assertLessEqual(new['estimated_input_tokens'] + 2048, 16384)

    def test_repair_keeps_previous_candidate_and_restates_correction_at_end(self):
        design = json.loads((ROOT / 'examples/npu_project.json').read_text(encoding='utf-8'))
        previous = 'module previous_candidate; endmodule'
        instruction = 'Fix the saved failing behavior; do not replace the original vectors.'
        new = build_node_context(design, 'same-snapshot', 'node-pe', instruction=instruction, previous_rtl=previous, template_version='node-verilog-2005-v6')
        old = build_node_context(design, 'same-snapshot', 'node-pe', instruction=instruction, previous_rtl=previous, template_version='node-verilog-2005-v5')
        self.assertEqual(old['context'], new['context'])
        self.assertIn(previous, new['messages'][1]['content'])
        self.assertEqual(new['messages'][1]['content'].count(instruction), 2)
        self.assertEqual(old['messages'][1]['content'].count(instruction), 1)
        self.assertGreater(new['messages'][1]['content'].rfind(instruction), new['messages'][1]['content'].rfind(previous))

    def test_v7_table_roundtrip_preserves_key_order_presence_types_and_contiguous_groups(self):
        records = [{'name': 'a', 'extra': None}, {'name': 'b', 'extra': {'preserved': [1, 1.0, True]}},
                   {'extra': None, 'name': 'c'}, {'name': 'd'}, {'name': 'e', 'extra': None}]
        table = field_row_table(records)
        self.assertEqual([len(group['rows']) for group in table['field_rows']], [2, 1, 1, 1])
        rebuilt = decode_field_row_table(table)
        self.assertEqual(json.dumps(rebuilt, separators=(',', ':')), json.dumps(records, separators=(',', ':')))
        self.assertNotIn('extra', rebuilt[3])
        self.assertIsNone(rebuilt[4]['extra'])
        rebuilt[1]['extra']['preserved'][0] = 9
        self.assertEqual(records[1]['extra']['preserved'][0], 1)
        self.assertEqual(decode_field_row_table(field_row_table([])), [])

    def test_v7_prompt_decodes_exact_full_source_and_keeps_interface_header_and_hash(self):
        design = json.loads((ROOT / 'examples/npu_scheduler_project.json').read_text(encoding='utf-8'))
        old = build_node_context(design, 'same-snapshot', 'node-scheduler', template_version='node-verilog-2005-v6')
        new = build_node_context(design, 'same-snapshot', 'node-scheduler', template_version='node-verilog-2005-v7')
        payload = json.loads(new['messages'][1]['content'].split('\nRequired interface header')[0])
        decoded = decode_prompt_source(payload['design_context'])
        self.assertEqual(json.dumps(decoded, ensure_ascii=False), json.dumps(old['context'], ensure_ascii=False))
        self.assertEqual(new['context'], old['context'])
        self.assertEqual(new['node_input_hash'], old['node_input_hash'])
        self.assertEqual(new['interface'], old['interface'])
        self.assertEqual(new['requested_module_header'], old['requested_module_header'])
        self.assertIn(old['requested_module_header'], new['messages'][1]['content'])
        self.assertEqual(decoded['design_verification_job'], design['verification_jobs'][0])
        self.assertEqual(decoded['node']['verification']['source_job'], design['verification_jobs'][0])

    def test_v7_rtl_margin_projection_preserves_newlines_comments_and_original_hash(self):
        design = json.loads((ROOT / 'examples/npu_project.json').read_text(encoding='utf-8'))
        previous = '  module comment_example;   \n    // comment must terminate here   \n    wire a; // trailing comment\n    /* comment with spaces */ assign a=1;   \n  endmodule\n'
        new = build_node_context(design, 'same-snapshot', 'node-pe', previous_rtl=previous, template_version='node-verilog-2005-v7')
        payload = json.loads(new['messages'][1]['content'].split('\nRequired interface header')[0])
        projected = payload['previous_rtl']
        self.assertEqual(projected, '\n'.join(line.strip() for line in previous.split('\n')))
        self.assertEqual(projected.count('\n'), previous.count('\n'))
        self.assertIn('// comment must terminate here\nwire a;', projected)
        self.assertEqual(new['prompt_projection']['previous_rtl_original_sha256'], hashlib.sha256(previous.encode()).hexdigest())
        self.assertEqual(new['prompt_projection']['previous_rtl_prompt_sha256'], hashlib.sha256(projected.encode()).hexdigest())

    def test_all_six_original_pe_saved_prompt_versions_remain_exact(self):
        folder = ROOT / 'results/npu_pe_continuous_flow'
        state = json.loads((folder / 'state.json').read_text(encoding='utf-8'))
        generation = json.loads((folder / 'generation.json').read_text(encoding='utf-8'))
        for job in generation['jobs']:
            saved = job['context']
            previous = None if job['base_job_id'] is None else next(record['rtl'] for record in generation['jobs'] if record['id'] == job['base_job_id'])
            payload = json.loads(saved['messages'][1]['content'].split('\nRequired interface header')[0])
            rebuilt = build_node_context(state['snapshots'][job['revision_id']], job['revision_id'], job['node_id'],
                                        job['instruction'], previous, payload['selected_diagnostics'], saved['prompt_template_version'])
            for field in ('context', 'interface', 'messages', 'prompt_text', 'node_input_hash', 'requested_module_header'):
                self.assertEqual(saved[field], rebuilt[field], (job['id'], field))

    def test_v7_fresh_thousand_byte_instruction_and_exact_header_once_fit_16k_with_output(self):
        design = json.loads((ROOT / 'examples/npu_scheduler_project.json').read_text(encoding='utf-8'))
        instruction = 'Cycle 2 config_ready must stay low for K=0. Preserve all saved data and rules. ' + 'x' * 922
        self.assertGreaterEqual(len(instruction.encode()), 1000)
        new = build_node_context(design, 'software-budget-check', 'node-scheduler', instruction=instruction, diagnostics=[], template_version='node-verilog-2005-v7')
        request = new['messages'][1]['content']
        self.assertEqual(request.count(instruction), 1)
        self.assertEqual(request.count(new['requested_module_header']), 1)
        payload = json.loads(request.split('\nRequired interface header')[0])
        self.assertNotIn('human_instruction', payload)
        self.assertNotIn('required_module_header', payload)
        self.assertEqual(decode_prompt_source(payload['design_context']), new['context'])
        self.assertLessEqual(new['estimated_input_tokens'] + 2048, 16384)

    def test_v8_plain_hardware_view_preserves_all_hardware_fields_and_hashes_omitted_inputs(self):
        design = json.loads((ROOT / 'examples/npu_scheduler_project.json').read_text(encoding='utf-8'))
        old = build_node_context(design, 'same-snapshot', 'node-scheduler', template_version='node-verilog-2005-v7')
        new = build_node_context(design, 'same-snapshot', 'node-scheduler', instruction='Keep the exact saved hardware requirements.', template_version='node-verilog-2005-v8')
        payload = json.loads(new['messages'][1]['content'].split('\nRequired interface header')[0])
        expected = copy.deepcopy(old['context'])
        del expected['node']['verification']
        del expected['design_verification_job']
        del expected['physical_interface']['ports']
        self.assertEqual(json.dumps(payload['design_context']), json.dumps(expected))
        self.assertIsInstance(payload['design_context']['node']['ports'], list)
        self.assertTrue(all(isinstance(peer['ports'], list) for peer in payload['design_context']['adjacent_interfaces']))
        self.assertEqual(new['context'], old['context'])
        self.assertEqual(new['node_input_hash'], old['node_input_hash'])
        self.assertEqual(new['interface'], old['interface'])
        self.assertEqual(new['requested_module_header'], old['requested_module_header'])
        refs = payload['verification_references']
        verification = old['context']['node']['verification']
        self.assertEqual(refs['node_verification'], {'kind': verification['kind'], 'object_sha256': object_hash(verification),
                                                    'source_job_sha256': object_hash(verification['source_job']),
                                                    'exercise_sha256': object_hash(verification['exercise'])})
        self.assertEqual(refs['design_verification_job']['object_sha256'], object_hash(old['context']['design_verification_job']))
        self.assertEqual(refs['physical_interface_ports']['object_sha256'], object_hash(old['interface']['ports']))
        self.assertEqual(new['prompt_projection']['verification_references'], refs)
        self.assertTrue(new['prompt_projection']['verification_inputs_retained_in_full_artifact_and_frozen_plan'])
        self.assertNotIn('human_instruction', payload)
        self.assertNotIn('required_module_header', payload)

    def test_v8_pe_frozen_verification_remains_in_full_source_and_references(self):
        design = json.loads((ROOT / 'examples/npu_project.json').read_text(encoding='utf-8'))
        new = build_node_context(design, 'same-snapshot', 'node-pe', template_version='node-verilog-2005-v8')
        payload = json.loads(new['messages'][1]['content'].split('\nRequired interface header')[0])
        verification = new['context']['node']['verification']
        self.assertEqual(len(verification['vectors']), 42)
        self.assertNotIn('verification', payload['design_context']['node'])
        self.assertEqual(payload['verification_references']['node_verification']['object_sha256'], object_hash(verification))
        self.assertIsNone(payload['verification_references']['node_verification']['source_job_sha256'])
        self.assertEqual(build_verification_plan(design, 'node-pe')['vector_count'], 42)

    def test_v8_repair_projection_has_previous_rtl_and_exact_once_instruction_without_mutating_full_source(self):
        design = json.loads((ROOT / 'examples/npu_scheduler_project.json').read_text(encoding='utf-8'))
        original = copy.deepcopy(design)
        previous = '  module old_bad_rtl;\n    // preserve newline\n    wire a;\n  endmodule\n'
        instruction = 'Repair the failed output assignments using internal registers and continuous assignments.'
        diagnostics = [{'code': 'software_qa_diagnostic', 'message': 'Check original failed syntax.'}]
        new = build_node_context(design, 'same-snapshot', 'node-scheduler', instruction, previous, diagnostics, template_version='node-verilog-2005-v8')
        payload = json.loads(new['messages'][1]['content'].split('\nRequired interface header')[0])
        self.assertEqual(payload['previous_rtl'], '\n'.join(line.strip() for line in previous.split('\n')))
        self.assertEqual(payload['selected_diagnostics'], diagnostics)
        self.assertEqual(new['messages'][1]['content'].count(instruction), 1)
        self.assertGreater(new['messages'][1]['content'].rfind(instruction), new['messages'][1]['content'].find('old_bad_rtl'))
        self.assertEqual(design, original)
        self.assertEqual(new['prompt_projection']['previous_rtl_original_sha256'], hashlib.sha256(previous.encode()).hexdigest())

    def test_saved_pre_v8_scheduler_and_pe_prompts_remain_exact_when_actual_records_are_available(self):
        folders = [ROOT / 'results/npu_scheduler_continuous_flow', ROOT / '.work/projects/npu']
        folder = next((path for path in folders if (path / 'state.json').is_file() and (path / 'generation.json').is_file()), None)
        if folder is None:
            self.skipTest('Actual scheduler history is not available in this checkout; original PE history is covered separately.')
        state = json.loads((folder / 'state.json').read_text(encoding='utf-8'))
        generation = json.loads((folder / 'generation.json').read_text(encoding='utf-8'))
        historical = [job for job in generation['jobs'] if job['context']['prompt_template_version'] in {f'node-verilog-2005-v{version}' for version in range(1, 8)}]
        self.assertTrue(historical)
        for job in historical:
            saved = job['context']
            previous = None if job['base_job_id'] is None else next(record['rtl'] for record in generation['jobs'] if record['id'] == job['base_job_id'])
            payload = json.loads(saved['messages'][1]['content'].split('\nRequired interface header')[0])
            rebuilt = build_node_context(state['snapshots'][job['revision_id']], job['revision_id'], job['node_id'],
                                        job['instruction'], previous, payload['selected_diagnostics'], saved['prompt_template_version'])
            for field in ('context', 'interface', 'messages', 'prompt_text', 'node_input_hash', 'requested_module_header'):
                self.assertEqual(saved[field], rebuilt[field], (job['id'], field))
            if 'prompt_projection' in saved:
                self.assertEqual(saved['prompt_projection'], rebuilt['prompt_projection'])


if __name__ == '__main__':
    unittest.main()
