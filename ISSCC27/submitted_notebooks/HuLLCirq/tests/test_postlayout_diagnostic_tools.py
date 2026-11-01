"""Isolated software QA for saved-review guards; never circuit evidence."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from hullcirq import postlayout_diagnostic_tools as diagnostic
from hullcirq import postlayout_tools
from hullcirq.domain import DomainError
from hullcirq.verification import object_hash


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def raw_sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class SavedDiagnosticTests(unittest.TestCase):
    def setUp(self):
        private = ROOT / '.work/m2k/software_qa_tmp'
        private.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix='saved-review-software-qa-', dir=private)
        self.root = Path(self.temp.name)
        self.folder = self.root / diagnostic.ORIGINAL_JOB_RELATIVE_PATH
        self.folder.mkdir(parents=True)
        self.adapter = b'// SOFTWARE QA ONLY - no circuit simulation\n'
        (self.folder / 'timed-testbench.v').write_bytes(self.adapter)
        self.original = {'execution_scope': 'compatibility_preflight_only', 'verification_supported': False,
            'software_qa_fixture': True}
        self.inputs = {name: {'sha256': 'a' * 64, 'bytes': 1, 'origin': 'software_qa_fixture'}
            for name in (*diagnostic.PHYSICAL_INPUTS, 'sdf', 'cell_models', 'primitives', 'verification_plan', 'public_vectors', 'timed_adapter')}
        self.layout = {'id': 'software-qa-layout', 'revision_id': 'software-qa-revision',
            'verification_plan': {'software_qa_fixture': True}}
        self.layout['verification_plan_sha256'] = object_hash(self.layout['verification_plan'])
        self.drc = {'id': 'software-qa-drc', 'revision_id': self.layout['revision_id'],
            'layout_record_sha256': object_hash(self.layout)}
        self.lvs = {'id': 'software-qa-lvs', 'revision_id': self.layout['revision_id'],
            'layout_record_sha256': object_hash(self.layout), 'drc_record_sha256': object_hash(self.drc),
            'source_inputs': copy.deepcopy(self.inputs)}
        self.commands = [{'software_qa_fixture': True, 'operation': operation, 'executed': True,
            'status': 'Completed', 'exit_code': 0} for operation in ('compile', 'simulate')]
        for name, command in zip(('compile-execution.json', 'simulation-execution.json'), self.commands):
            write_json(self.folder / name, command)
        self.audits = {operation: {'software_qa_fixture': True, 'operation': operation,
            'execution_binding_verified': True} for operation in ('compile', 'simulate')}
        manifest = [{'id': 'timed-testbench', 'relative_path': 'timed-testbench.v',
            'sha256': raw_sha(self.folder / 'timed-testbench.v'), 'bytes': len(self.adapter),
            'content_type': 'text/plain; charset=utf-8'}]
        review_inputs = copy.deepcopy(self.inputs)
        review_inputs['timed_adapter'] = {'sha256': raw_sha(self.folder / 'timed-testbench.v'),
            'bytes': len(self.adapter), 'origin': 'executed_original_job_timed_v2_full_hierarchy_dump'}
        self.evidence = {'schema_version': diagnostic.SCHEMA,
            'original_source_binding': {'revision_id': self.layout['revision_id'],
                'verification_plan_sha256': self.layout['verification_plan_sha256'],
                **{name + '_run_id': record['id'] for name, record in (('layout', self.layout), ('drc', self.drc), ('lvs', self.lvs))},
                **{name + '_record_sha256': object_hash(record) for name, record in (('layout', self.layout), ('drc', self.drc), ('lvs', self.lvs))}},
            'original_source_inputs': self.inputs, 'review_source_inputs': review_inputs,
            'frozen_result': {'status': 'Completed', 'validation_status': 'Unsupported',
                'executed': True, 'verification_supported': False, 'cleanup_unresolved': False,
                'diagnostics': [], 'commands': self.commands, 'artifacts_directory': str(self.folder),
                'artifacts': manifest, 'configuration_sha256': 'f' * 64},
            'artifact_manifest': manifest, 'execution_audits': self.audits}
        self.profile_path = self.root / 'configs/postlayout_saved_diagnostic_sky130_v1.json'
        self.profile = {'version': 'hullcirq-sky130-saved-diagnostic-review-v1',
            'execution_scope': diagnostic.SCOPE, 'verification_supported': False,
            'archive_relative_path': diagnostic.ARCHIVE_RELATIVE_PATH,
            'original_preflight_configuration_sha256': object_hash(self.original),
            'reason': 'SOFTWARE QA ONLY: unsupported, no EDA run.'}
        self.patches = [patch.object(diagnostic, 'ROOT', self.root),
            patch.object(diagnostic, 'PROFILE', self.profile_path),
            patch.object(postlayout_tools, '_configuration', return_value=(None,) * 5),
            patch.object(diagnostic, 'validate_completed_execution', side_effect=lambda folder, operation, **kwargs: self.audits[operation])]
        for item in self.patches: item.start()
        self.freeze()

    def freeze(self):
        evidence_path = self.root / diagnostic.ARCHIVE_RELATIVE_PATH
        write_json(evidence_path, self.evidence)
        self.profile['evidence_sha256'] = raw_sha(evidence_path)
        write_json(self.profile_path, self.profile)
        if hasattr(self, 'pin'): self.pin.stop()
        self.pin = patch.object(diagnostic, 'PROFILE_SHA256', raw_sha(self.profile_path))
        self.pin.start()
        self.configuration = {'profile': copy.deepcopy(self.profile),
            'original_preflight_configuration': self.original,
            'execution_scope': diagnostic.SCOPE, 'verification_supported': False}

    def tearDown(self):
        self.pin.stop()
        for item in reversed(self.patches): item.stop()
        self.temp.cleanup()

    def test_available_does_not_claim_qualification_and_dispatch_keeps_mode(self):
        capability = postlayout_tools.runtime_descriptor(self.configuration)
        self.assertTrue(capability['available'])
        self.assertFalse(capability['verification_supported'])
        self.assertFalse(capability['execution_started_by_this_review'])
        self.assertEqual(capability['execution_scope'], diagnostic.SCOPE)

    def test_source_binding_and_retained_result_are_copied_without_process(self):
        with patch.object(postlayout_tools, 'source_inputs', return_value=self.inputs), \
             patch('subprocess.Popen', side_effect=AssertionError('No EDA launch is allowed')):
            inputs = diagnostic.source_inputs(self.layout, self.configuration)
            result = diagnostic.run_postlayout(self.lvs, self.drc, self.layout, self.configuration)
        self.assertTrue(result['executed'])
        self.assertFalse(result['execution_started_by_this_review'])
        self.assertEqual(result['validation_status'], 'Unsupported')
        self.assertEqual(result['configuration_sha256'], object_hash(self.configuration))
        self.assertEqual(result['retained_execution_configuration_sha256'], 'f' * 64)
        self.assertEqual(result['commands'], self.commands)
        inputs['timed_adapter']['bytes'] = 123
        result['commands'][0]['exit_code'] = 999
        self.assertEqual(self.commands[0]['exit_code'], 0)
        self.assertEqual(self.evidence['review_source_inputs']['timed_adapter']['bytes'], len(self.adapter))

    def test_invalid_diagnostic_configuration_never_falls_back_to_readiness(self):
        for changes in ({'verification_supported': True}, {'executable': 'arbitrary'},
                        {'execution_scope': 'compatibility_preflight_only'}):
            with self.subTest(changes=changes):
                capability = postlayout_tools.runtime_descriptor({**self.configuration, **changes})
                self.assertFalse(capability['available'])
                self.assertEqual(capability['execution_scope'], diagnostic.SCOPE)
        changed = copy.deepcopy(self.configuration)
        changed['profile']['archive_relative_path'] = '../different.json'
        self.assertFalse(diagnostic.runtime_descriptor(changed)['available'])

    def test_profile_and_evidence_raw_byte_changes_are_rejected(self):
        self.profile_path.write_bytes(self.profile_path.read_bytes() + b' ')
        self.assertFalse(diagnostic.runtime_descriptor(self.configuration)['available'])
        self.freeze()
        path = self.root / diagnostic.ARCHIVE_RELATIVE_PATH
        path.write_bytes(path.read_bytes() + b' ')
        self.assertFalse(diagnostic.runtime_descriptor(self.configuration)['available'])

    def test_original_preflight_configuration_change_is_rejected(self):
        changed = copy.deepcopy(self.configuration)
        changed['original_preflight_configuration']['pdk_root'] = 'other'
        self.assertFalse(diagnostic.runtime_descriptor(changed)['available'])

    def test_artifact_changed_without_changing_archive_is_rejected(self):
        (self.folder / 'timed-testbench.v').write_bytes(b'changed software QA')
        self.assertFalse(diagnostic.runtime_descriptor(self.configuration)['available'])

    def test_signed_timing_or_finite_output_results_cannot_be_promoted(self):
        for key, value in (('validation_status', 'Passed'), ('verification_supported', True),
                           ('executed', False), ('cleanup_unresolved', True)):
            original = self.evidence['frozen_result'][key]
            self.evidence['frozen_result'][key] = value; self.freeze()
            self.assertFalse(diagnostic.runtime_descriptor(self.configuration)['available'])
            self.evidence['frozen_result'][key] = original
        with self.assertRaises(DomainError) as error:
            postlayout_tools.validate_postlayout_result({'validation_status': 'Passed'}, {}, {}, {}, self.configuration)
        self.assertEqual(error.exception.code, 'postlayout_unsupported')

    def test_source_plan_or_adopted_record_substitution_is_rejected(self):
        with patch.object(postlayout_tools, 'source_inputs', return_value=self.inputs):
            with self.assertRaises(DomainError):
                diagnostic.source_inputs({**self.layout, 'id': 'other-layout'}, self.configuration)
            with self.assertRaises(DomainError):
                diagnostic.run_postlayout({**self.lvs, 'id': 'other-lvs'}, self.drc, self.layout, self.configuration)
        changed = copy.deepcopy(self.inputs); changed['sdf']['sha256'] = 'b' * 64
        with patch.object(postlayout_tools, 'source_inputs', return_value=changed), self.assertRaises(DomainError):
            diagnostic.source_inputs(self.layout, self.configuration)

    def test_request_birth_terminal_or_command_substitution_is_rejected(self):
        self.evidence['execution_audits'] = copy.deepcopy(self.audits)
        self.evidence['execution_audits']['compile']['worker_sha256'] = 'changed'
        self.freeze()
        self.assertFalse(diagnostic.runtime_descriptor(self.configuration)['available'])
        self.evidence['execution_audits'] = self.audits
        self.evidence['frozen_result']['commands'] = copy.deepcopy(self.commands)
        self.evidence['frozen_result']['commands'][0]['exit_code'] = 1
        self.freeze()
        self.assertFalse(diagnostic.runtime_descriptor(self.configuration)['available'])

    def test_cancel_keeps_retained_actual_execution_distinct(self):
        event = threading.Event(); event.set()
        with patch.object(postlayout_tools, 'source_inputs', return_value=self.inputs):
            result = diagnostic.run_postlayout(self.lvs, self.drc, self.layout, self.configuration, event)
        self.assertTrue(result['executed'])
        self.assertFalse(result['execution_started_by_this_review'])
        self.assertEqual(result['status'], 'Cancelled')
        self.assertEqual(result['validation_status'], 'Not Checked')


if __name__ == '__main__': unittest.main()
