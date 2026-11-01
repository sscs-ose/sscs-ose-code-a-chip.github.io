"""Versioned GUI preparation upgrade QA. Explicit doubles; no tool execution."""
import copy
import hashlib
import json
import unittest
from unittest.mock import patch

from hullcirq import lvs_repair_session as session
from hullcirq.domain import DomainError
import test_lvs_repair_session as fixtures


class LvsRepairUpgradeSessionTests(unittest.TestCase):
    def setUp(self):
        self.qa = fixtures.LvsRepairSessionTests('runTest'); self.qa.setUp()
        self.addCleanup(self.qa.doCleanups)
        self.qa.prepare()
        self.previous_raw = self.qa.path.read_bytes(); self.previous_mtime = self.qa.path.stat().st_mtime_ns
        self.previous = json.loads(self.previous_raw)
        failed = copy.deepcopy(self.qa.records['lvs'])
        failed.update(id='lvs-software-failed-v3', execution_status='Failed', validation_status='Failed',
            review_status='Awaiting Review', runtime_configuration=copy.deepcopy(self.qa.server.lvs_workflow.tool_configuration),
            layout_run_id='physical-software', drc_run_id='drc-software',
            checks={'cleanup_unresolved': False, 'executed': True, 'status': 'Failed', 'exit_code': 1})
        fixtures.checksum(failed); self.failed = failed
        self.qa.histories['lvs']['runs'].append(failed); self.qa.write_histories()
        self.qa.server.lvs_workflow._state['runs'] = [copy.deepcopy(self.qa.records['lvs']), copy.deepcopy(failed)]
        (self.qa.root/'configs/lvs_profile_sky130_v4.json').write_text(json.dumps({'profile_version': session.UPGRADE_PROFILE}), encoding='utf-8')
        self.path = self.qa.directory/session.UPGRADE_BUNDLE_NAME
        self.failed_proof = self.qa.stack.enter_context(patch('hullcirq.lvs_tools.validate_failed_lvs_result',
            return_value={'validation_status': 'Passed', 'scope': 'actual_failed_v3_execution_proof_only_not_LVS_success'}))

    def prepare(self, **changes):
        body = {'layout_run_id': 'physical-software', 'drc_run_id': 'drc-software',
                'source_lvs_run_id': self.failed['id'], 'revision_id': self.qa.revision}
        body.update(changes)
        return session.prepare_repair(self.qa.server, **body)

    def test_explicit_upgrade_keeps_original_source_v3_bundle_and_every_old_record(self):
        before = {path: path.read_bytes() for path in self.qa.system.iterdir()}
        status = self.prepare()
        self.assertEqual(status['profile_version'], session.UPGRADE_PROFILE)
        self.assertEqual(status['source_identity'], self.previous['source_identity'])
        self.assertEqual(status['previous_bundle_sha256'], hashlib.sha256(self.previous_raw).hexdigest())
        config = self.qa.server.lvs_workflow.tool_configuration
        self.assertEqual(config['repair_source_binding'], self.previous['configuration']['repair_source_binding'])
        self.assertEqual(config['repair_upgrade_binding'], session._upgrade_identity(self.previous_raw, self.failed))
        self.assertEqual(config['physical_runtime'], self.qa.base[2])
        self.assertEqual(self.qa.path.read_bytes(), self.previous_raw)
        self.assertEqual(self.qa.path.stat().st_mtime_ns, self.previous_mtime)
        self.assertEqual(before, {path: path.read_bytes() for path in before})
        self.failed_proof.assert_called_once()

    def test_reopen_reconstructs_both_bundles_and_failed_proof_with_v4_priority(self):
        self.prepare(); raw = self.path.read_bytes()
        restored, status = self.qa.restore()
        self.assertTrue(status['configured'], status['error'])
        self.assertEqual(status['profile_version'], session.UPGRADE_PROFILE)
        self.assertEqual(restored[4], self.qa.server.lvs_workflow.tool_configuration)
        self.assertEqual(restored[:4], self.qa.base[:4]); self.assertEqual(restored[5], self.qa.base[5])
        self.assertEqual(self.failed_proof.call_count, 2)
        self.assertEqual(self.path.read_bytes(), raw); self.assertEqual(self.qa.path.read_bytes(), self.previous_raw)

    def test_repeated_upgrade_is_idempotent_and_different_source_never_overwrites(self):
        self.prepare(); raw = self.path.read_bytes(); mtime = self.path.stat().st_mtime_ns
        self.qa.server.lvs_workflow.current = False
        self.assertEqual(self.prepare()['profile_version'], session.UPGRADE_PROFILE)
        self.assertEqual(self.path.read_bytes(), raw); self.assertEqual(self.path.stat().st_mtime_ns, mtime)
        with self.assertRaises(DomainError): self.prepare(source_lvs_run_id='different-failure')
        self.assertEqual(self.path.read_bytes(), raw); self.assertEqual(self.qa.path.read_bytes(), self.previous_raw)

    def test_v4_restore_keeps_historical_failed_v3_when_newer_run_exists(self):
        self.prepare()
        self.qa.histories['lvs']['runs'].append({'id': 'later-software-v4-run'})
        self.qa.write_histories()
        restored, status = self.qa.restore()
        self.assertTrue(status['configured'], status['error'])
        self.assertEqual(restored[4]['profile']['profile_version'], session.UPGRADE_PROFILE)

    def test_bad_v4_checksum_recomputed_paths_or_binding_remain_preserved_and_rejected(self):
        self.prepare(); raw = self.path.read_bytes()
        for change in (lambda b: b['configuration'].update(working_directory='arbitrary'),
                       lambda b: b['upgrade_identity'].update(failed_lvs_execution_sha256='0'*64),
                       lambda b: b.update(previous_bundle_sha256='0'*64)):
            with self.subTest(change=change):
                bundle = json.loads(raw); change(bundle); fixtures.checksum(bundle)
                self.path.write_text(json.dumps(bundle), encoding='utf-8'); changed = self.path.read_bytes()
                restored, status = self.qa.restore()
                self.assertFalse(status['configured']); self.assertEqual(restored, self.qa.base)
                self.assertEqual(self.path.read_bytes(), changed); self.assertEqual(self.qa.path.read_bytes(), self.previous_raw)

    def test_durable_failed_record_mutation_or_failed_worker_proof_refuses_upgrade(self):
        self.failed_proof.side_effect = DomainError('unproven-failed-worker', 'Software QA proof failure', 409)
        with self.assertRaises(DomainError): self.prepare()
        self.assertFalse(self.path.exists())
        self.failed_proof.side_effect = None
        self.failed['checks']['cleanup_unresolved'] = True; fixtures.checksum(self.failed)
        self.qa.write_histories()
        self.qa.server.lvs_workflow._state['runs'][-1] = copy.deepcopy(self.failed)
        with self.assertRaises(DomainError): self.prepare()
        self.assertFalse(self.path.exists()); self.assertEqual(self.qa.path.read_bytes(), self.previous_raw)

    def test_wrong_failed_proof_result_cannot_authorize_configuration(self):
        for result in (None, {'validation_status': 'Failed'}, {'validation_status': 'Passed', 'scope': 'wrong'}):
            self.failed_proof.return_value = result
            with self.subTest(result=result), self.assertRaises(DomainError): self.prepare()
            self.assertFalse(self.path.exists())

    def test_readonly_busy_stale_revision_stale_failure_and_foreign_parent_refuse_without_bundle(self):
        self.qa.server.workspace.identity['read_only'] = True
        with self.assertRaises(DomainError): self.prepare()
        self.qa.server.workspace.identity['read_only'] = False
        self.qa.server.generation.active = True
        with self.assertRaises(DomainError): self.prepare()
        self.qa.server.generation.active = False
        with self.assertRaises(DomainError): self.prepare(revision_id='stale')
        with self.assertRaises(DomainError): self.prepare(layout_run_id='foreign-layout')
        self.qa.server.lvs_workflow.current = False
        with self.assertRaises(DomainError): self.prepare()
        self.assertFalse(self.path.exists()); self.assertEqual(self.qa.path.read_bytes(), self.previous_raw)

    def test_upgrade_eligibility_is_readonly_distinguishes_original_and_failed_identities(self):
        before = copy.deepcopy(self.qa.server.lvs_workflow._state)
        meta = session.eligibility(self.qa.server)
        self.assertTrue(meta['eligible'], meta['blocked_reason']); self.assertEqual(meta['mode'], 'upgrade_v4')
        self.assertEqual(meta['source']['source_lvs_run_id'], self.failed['id'])
        self.assertEqual(meta['source']['historical_lvs_run_id'], self.qa.records['lvs']['id'])
        self.assertEqual(meta['source']['previous_bundle_sha256'], hashlib.sha256(self.previous_raw).hexdigest())
        self.assertEqual(self.qa.server.lvs_workflow._state, before); self.assertFalse(self.path.exists())
        self.failed_proof.assert_not_called()

    def test_v3_bundle_is_mandatory_and_cannot_be_changed_behind_v4(self):
        self.prepare(); v4raw = self.path.read_bytes()
        self.qa.path.write_bytes(self.previous_raw+b'\n')
        restored, status = self.qa.restore()
        self.assertFalse(status['configured']); self.assertEqual(restored, self.qa.base)
        self.assertEqual(self.path.read_bytes(), v4raw)
        self.qa.path.unlink()  # Only this disposable software fixture.
        restored, status = self.qa.restore()
        self.assertFalse(status['configured']); self.assertEqual(restored, self.qa.base)


if __name__ == '__main__': unittest.main()
