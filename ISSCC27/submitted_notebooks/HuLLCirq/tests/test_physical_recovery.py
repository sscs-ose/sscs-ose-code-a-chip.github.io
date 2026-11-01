"""Generic handoff guards; no native tool, model, real design store or browser."""
import copy
import json
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace as NS
import unittest

from hullcirq import physical_recovery as recovery
from hullcirq.domain import DomainError
from hullcirq.verification import object_hash


class PhysicalRecoveryTests(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).resolve().parents[1] / '.work/qa'
        temp = tempfile.TemporaryDirectory(dir=root); self.addCleanup(temp.cleanup)
        self.run = {'id': 'qa-run', 'record_hash': '', 'execution_status': 'Completed',
                    'checks': {'checks': {'lvs': {'validation_status': 'Failed'}}, 'summary': {'error_count': 2}},
                    'diagnostics': [{'code': 'qa-mismatch', 'message': 'SOFTWARE QA: not circuit evidence'}]}
        self.seal()
        manager = NS(lock=threading.RLock(), _state={'runs': [self.run]}, _storage_error=None,
                     is_active=lambda: False, _decorate=lambda r: {**r, 'freshness': 'Current'})
        self.design = {'nodes': [{'id': 'arbitrary-definition', 'name': 'Not an NPU'}]}
        self.envelope = {'revision': {'id': 'qa-revision'}, 'design': self.design}
        self.job = {'id': 'qa-rtl', 'rtl': 'SOFTWARE QA ONLY', 'node_id': 'arbitrary-definition',
                    'freshness': 'Current', 'review_status': 'Accepted'}
        generation = NS(lock=threading.RLock(), _state={'jobs': [self.job]}, job=lambda _: copy.deepcopy(self.job))
        self.server = NS(workspace=NS(context=object(), identity={'project_id': 'qa-project', 'system_id': 'qa-system', 'read_only': False}),
            store=NS(state_path=Path(temp.name)/'state.json', envelope=lambda: copy.deepcopy(self.envelope)),
            generation=generation, global_generation=generation,
            **{name: manager for name in recovery.STAGES.values()})

    def seal(self):
        self.run['record_hash'] = object_hash({k: v for k, v in self.run.items() if k != 'record_hash'})

    def prepare(self, target='node_rtl'):
        return recovery.prepare(self.server, 'lvs', 'qa-run', 'qa-revision', target,
            'arbitrary-definition' if target == 'node_rtl' else None, 'Inspect the reported mismatch; preserve the oracle.')

    def body(self, record):
        return dict(operation='repair', base_job_id='qa-rtl', node_id='arbitrary-definition', revision_id='qa-revision', instruction=record['instruction'])

    def test_generic_source_and_complete_diagnostics_are_bound_without_workflow_edits(self):
        old = copy.deepcopy((self.run, self.job, self.envelope))
        record = self.prepare()
        self.assertIn('qa-mismatch', record['instruction'])
        self.assertEqual(record['target_stage'], 'local_rtl_generation')
        self.assertEqual(record['evidence']['summary']['error_count'], 2)
        self.assertEqual(recovery.validate(self.server, record['id']), record)
        recovery.validate_instruction(self.server, self.body(record), 'node_rtl')
        self.assertEqual((self.run, self.job, self.envelope), old)

    def test_wrong_project_revision_source_rtl_or_instruction_are_rejected(self):
        record = self.prepare()
        for obj, key, value in [(self.server.workspace.identity, 'project_id', 'other'),
                                 (self.envelope['revision'], 'id', 'new'), (self.run, 'id', 'new-run'),
                                 (self.job, 'rtl', 'changed')]:
            previous = obj[key]; obj[key] = value
            with self.assertRaises(DomainError): recovery.validate(self.server, record['id'])
            obj[key] = previous
        body = self.body(record); body['instruction'] += '\nRelax checks'
        with self.assertRaises(DomainError): recovery.validate_instruction(self.server, body, 'node_rtl')
        with self.assertRaises(DomainError): recovery.validate_instruction(self.server, self.body(record), 'global_rtl')

    def test_other_stage_categories_need_no_model_candidate_and_remain_hypotheses(self):
        for target in ('environment', 'extraction', 'physical', 'global_rtl'):
            record = self.prepare(target)
            self.assertIn('hypothesis', record['certainty'])
            self.assertEqual(record['target_stage'], recovery.TARGETS[target])
            self.assertEqual(recovery.validate(self.server, record['id']), record)

    def test_unproven_owner_unresolved_cleanup_stale_readonly_and_bad_id_fail_closed(self):
        with self.assertRaises(DomainError): recovery.prepare(self.server, 'lvs', 'qa-run', 'qa-revision', 'node_rtl', 'missing', 'reason')
        self.run['checks']['cleanup_unresolved'] = True; self.seal()
        with self.assertRaises(DomainError): self.prepare()
        self.run['checks']['cleanup_unresolved'] = False; self.seal()
        self.server.workspace.identity['read_only'] = True
        with self.assertRaises(DomainError): self.prepare()
        with self.assertRaises(DomainError): recovery.path(self.server, '../outside')

    def test_diagnostic_mutation_even_with_recomputed_source_hash_invalidates_handoff(self):
        record = self.prepare(); self.run['checks']['summary']['error_count'] = 0; self.seal()
        with self.assertRaises(DomainError): recovery.validate(self.server, record['id'])

    def test_unrelated_existing_manual_repair_instruction_is_preserved(self):
        recovery.validate_instruction(self.server, {'instruction': 'Existing explicit repair'}, 'node_rtl')

    def test_recomputed_handoff_checksum_cannot_replace_frozen_diagnostics(self):
        record = self.prepare()
        record['evidence']['summary']['error_count'] = 0
        record['instruction'] = recovery.instruction(record)
        record['record_hash'] = object_hash({k: v for k, v in record.items() if k != 'record_hash'})
        recovery.path(self.server, record['id']).write_text(json.dumps(record), encoding='utf-8')
        with self.assertRaises(DomainError): recovery.validate(self.server, record['id'])

    def test_saved_history_read_does_not_change_bytes_or_metadata(self):
        record = self.prepare(); saved = recovery.path(self.server, record['id'])
        before = saved.read_bytes(), saved.stat().st_mtime_ns
        self.assertEqual(recovery.history(self.server, 'lvs')['records'], [record])
        self.assertEqual((saved.read_bytes(), saved.stat().st_mtime_ns), before)

    def test_long_project_path_can_save_validate_and_read_history(self):
        base = self.server.store.state_path.parent
        directory = base / ('long-' + 'x' * max(80, 270 - len(str(base))))
        self.server.store.state_path = directory/'state.json'
        recovery.io_path(directory).mkdir()
        saved = None
        try:
            record = self.prepare(); saved = recovery.path(self.server, record['id'])
            self.assertGreater(len(str(saved)), 260)
            self.assertEqual(recovery.validate(self.server, record['id']), record)
            self.assertEqual(recovery.history(self.server, 'lvs')['records'], [record])
        finally:
            if saved is not None: recovery.io_path(saved).unlink()
            recovery.io_path(directory/'physical_recovery').rmdir()
            recovery.io_path(directory).rmdir()
