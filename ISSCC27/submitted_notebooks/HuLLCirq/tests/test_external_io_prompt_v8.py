"""Immutable V6/V7 and bounded V8 prompt fixtures; no provider/native calls."""
import copy
import json
from pathlib import Path
import sys
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'tests'))
from hullcirq import generic_global_verification as generic, global_generation as generation
from hullcirq.verification import content_hash, object_hash
from test_external_io_generation import fixture, rtl_fixture


def failed_parent():
    return {'id': 'software-failed-parent', 'rtl': '`timescale 1ns / 1ps\n'+rtl_fixture(fixture()),
            'diagnostics': [{'code': 'unsafe_directive', 'severity': 'error',
                'message': 'Preprocessor directives, includes, and macros are not permitted in this fixed candidate check.'}]}


# Captured from the unmodified V7 implementation BEFORE adding V8, for the
# deterministic scalar/array fixtures and both generate/repair projections.
LEGACY_GOLDENS = {
    (False, 6): ('9531d5a51690ae4eea6729f358f09744193b14c760c6d3e67639ac48f754b2f5',
                 '90b3a7e7ede9b2481b7ad4b18f7b45c8e842775bc4f27f2b94108cfcf8368140',
                 'f48f156383030eaeabb03783049dbb6042d8519fedeca652b685187633eef0ea'),
    (False, 7): ('94eb8c039efade4762f59ca84e55e40be5cc892fec7757a80e7cf0686c09a114',
                 'ee8cfd24be985b10e73477d45a2cd0489130ed382fd7731685fe8c11b3a7abc1',
                 '0c0040766d4bc6b833b2aeb1309967b12052c9616125cd98fe21909a64b188d1'),
    (True, 6): ('0f23cfd7637d20f03566dd7bd021c9c5c3e57de9f025a2d064a0c3ddb465243a',
                '3d9461aaef10aaa17cd1c614dc22cb3865e13d975532db2ee245176c7ef75d88',
                'ef3b65d728c670d8e80186dfccba24f90dfec4ba8245b614de0803e019433b29'),
    (True, 7): ('c98399f44fd63e9d4b1f6f9efe6a39c136f40b79399bcbce85edc1c81caceb2e',
                '1237fec8de15f6c81eec27528228e3bde9bb197c1499153f7e458c1844bbca20',
                'cd4c2c409436063ad66292c672dc66d63aee95d70dcf715f273eee0d85bffed6'),
}


class ExternalIoPromptV8Tests(unittest.TestCase):
    def test_retained_v6_v7_projection_and_messages_match_prechange_goldens(self):
        base = failed_parent()
        for (array, number), (projection_hash, generate_hash, repair_hash) in LEGACY_GOLDENS.items():
            with self.subTest(array=array, version=number):
                manifest = fixture(array)
                version = {6: generation.PROMPT_TEMPLATE_V6, 7: generation.PROMPT_TEMPLATE_V7}[number]
                self.assertEqual(object_hash(generation.integration_projection(manifest, version)), projection_hash)
                self.assertEqual(object_hash(generation.integration_messages(manifest, '', template_version=version)), generate_hash)
                self.assertEqual(object_hash(generation.integration_messages(manifest,
                    'Remove all directives; preserve saved bindings.', base, version)), repair_hash)

    def test_only_future_external_previews_select_v8(self):
        manifest = fixture()
        self.assertEqual(generation.prompt_template(manifest['design']), generation.PROMPT_TEMPLATE_V8)
        self.assertEqual(generic.EXTERNAL_PROMPT, 'generic-explicit-external-io-cycle-vectors-v7')
        manifest['design'].pop('external_io')
        self.assertEqual(generation.prompt_template(manifest['design']), generation.PROMPT_TEMPLATE_V6)

    def test_v8_bans_directives_in_system_and_user_without_changing_bindings(self):
        manifest = fixture(); before = copy.deepcopy(manifest)
        messages = generation.integration_messages(manifest, '')
        for message in messages:
            self.assertIn('`timescale', message['content'])
            self.assertIn('`include', message['content'])
            self.assertIn('`define', message['content'])
            self.assertIn('preprocessor directive', message['content'])
        self.assertIn('start with module and end with endmodule', messages[0]['content'])
        self.assertIn('first non-whitespace token must be module', messages[1]['content'])
        self.assertEqual(generation.integration_projection(manifest, generation.PROMPT_TEMPLATE_V8),
                         generation.integration_projection(manifest, generation.PROMPT_TEMPLATE_V7))
        self.assertEqual(manifest, before)

    def test_v8_repair_preview_freezes_parent_and_correction_last_without_saving_design(self):
        manifest = fixture(); manifest['revision_id'] = 'software-current-revision'
        base = failed_parent(); before = copy.deepcopy((manifest, base))
        provider = {'revision_id': 'software-provider', 'profile': {'execution_location': 'Local',
                    'temperature': .2, 'seed': 104, 'max_output_tokens': 4000, 'context_window': 16384}}
        manager = generation.GlobalGenerationManager.__new__(generation.GlobalGenerationManager)
        manager.lock = threading.RLock(); manager._previews = {}; manager._state = {'jobs': [base]}
        manager.store = SimpleNamespace(envelope=lambda: {'revision': {'id': manifest['revision_id']}})
        manager.generation = SimpleNamespace(lock=threading.RLock(), _require_profile=lambda: copy.deepcopy(provider))
        manager.compiler = None
        manager.observe_design = lambda: ('software-source-key', copy.deepcopy(manifest), None)
        instruction = 'Remove all directives; preserve saved bindings.'
        context = manager.preview(manifest['revision_id'], 'repair', base['id'], instruction)
        self.assertEqual(context['template_version'], generation.PROMPT_TEMPLATE_V8)
        self.assertEqual(context['operation'], 'repair')
        self.assertEqual(context['base_job_id'], base['id'])
        self.assertEqual(context['source_manifest'], manifest)
        self.assertEqual(context['profile_revision_id'], provider['revision_id'])
        self.assertEqual(context['parameters'], {'temperature': .2, 'seed': 104, 'max_tokens': 4000})
        self.assertIn(base['rtl'], context['messages'][-1]['content'])
        self.assertIn('Recorded diagnostics:', context['messages'][-1]['content'])
        self.assertTrue(context['messages'][-1]['content'].endswith('Development-assistant/user correction (final instruction): '+instruction))
        self.assertEqual(context['prompt_projection_sha256'], object_hash(generation.integration_projection(manifest, generation.PROMPT_TEMPLATE_V8)))
        unhashed = copy.deepcopy(context); identifier = unhashed.pop('context_id')
        self.assertEqual(identifier, object_hash(unhashed))
        self.assertEqual(context['estimated_input_tokens'], len(json.dumps(context['messages'], ensure_ascii=False, allow_nan=False).encode('utf-8')))
        self.assertEqual((manifest, base), before)

    def test_v7_and_v8_keep_identical_structural_proof_and_reject_unknown_versions(self):
        manifest = fixture(); rtl = rtl_fixture(manifest); proof = generic.check_external_wiring(rtl, manifest)
        job = {'rtl': rtl, 'context': {}, 'checks': {'external_io_wiring_proof': proof,
                 'checks': {'external_io_wiring': {'validation_status': 'Passed'}}}}
        for version in (generic.EXTERNAL_PROMPT, generic.EXTERNAL_PROMPT_V8):
            job['context']['template_version'] = version
            self.assertTrue(generic.external_wiring_proof_matches(job, manifest))
        job['context']['template_version'] = 'unrecognized-future-version'
        self.assertFalse(generic.external_wiring_proof_matches(job, manifest))

    def test_directive_candidate_is_rejected_unchanged_before_native_commands(self):
        manifest = fixture(); original = failed_parent()['rtl']
        plan = generation.build_global_plan(manifest['design'])
        with patch.object(generation, 'execute_fixed', side_effect=AssertionError('No native execution')) as execute:
            result = generation.check_global_rtl(original, manifest, plan, None)
        execute.assert_not_called()
        self.assertEqual(result['validation_status'], 'Failed')
        self.assertFalse(result['executed']); self.assertEqual(result['commands'], [])
        self.assertEqual(result['rtl_sha256'], content_hash(original))
        self.assertTrue(original.startswith('`timescale'))
        self.assertTrue(any(d['code'] == 'unsafe_directive' for d in result['diagnostics']))

    def test_direct_wiring_candidate_still_requires_real_compiler_qualification(self):
        manifest = fixture(); rtl = rtl_fixture(manifest)
        with patch.object(generation, 'execute_fixed', side_effect=AssertionError('No native execution')) as execute:
            result = generation.check_global_rtl(rtl, manifest, generation.build_global_plan(manifest['design']), None)
        execute.assert_not_called()
        self.assertEqual(result['validation_status'], 'Unsupported')
        self.assertEqual(result['checks']['interface']['validation_status'], 'Passed')
        self.assertEqual(result['checks']['external_io_wiring']['validation_status'], 'Passed')

    def test_independent_vectors_remain_withheld_from_v8_messages(self):
        manifest = fixture(); before = generation.integration_messages(manifest, '')
        for row in manifest['design']['global_verification']['cycles']:
            row['expect'] = {name: 1 for name in row['expect']}
        self.assertEqual(generation.integration_messages(manifest, ''), before)
        self.assertNotIn('global_verification', generation.integration_projection(manifest))


if __name__ == '__main__': unittest.main()
