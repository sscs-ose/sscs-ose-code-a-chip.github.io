"""v7 admits completed v6 comparison failure only; no real tools."""
import copy
import hashlib
import json
import unittest

from hullcirq import lvs_repair_session as session
from hullcirq.domain import DomainError
import test_lvs_repair_v6_session as fixtures
from test_lvs_repair_session import checksum


class LvsRepairV7SessionTests(unittest.TestCase):
    def setUp(self):
        self.base = fixtures.LvsRepairV6SessionTests('runTest'); self.base.setUp()
        self.addCleanup(self.base.doCleanups)
        self.base.prepare(); self.qa = self.base.qa
        self.v6raw = self.base.path.read_bytes()
        self.failed = copy.deepcopy(self.base.failed)
        self.failed.update(id='lvs-software-completed-failed-v6', execution_status='Completed',
            runtime_configuration=copy.deepcopy(self.qa.server.lvs_workflow.tool_configuration),
            checks={'status': 'Completed', 'validation_status': 'Failed', 'exit_code': 0,
                    'cleanup_unresolved': False, 'executed': True,
                    'checks': {'extraction': {'validation_status': 'Passed'}, 'lvs': {'validation_status': 'Failed'}}})
        checksum(self.failed); self.qa.histories['lvs']['runs'].append(self.failed); self.qa.write_histories()
        self.qa.server.lvs_workflow._state['runs'].append(copy.deepcopy(self.failed))
        (self.qa.root/'configs/lvs_profile_sky130_v7.json').write_text(json.dumps({'profile_version': session.V7_PROFILE}), encoding='utf-8')
        self.path = session._upgrade_path(self.qa.directory, session.V7_PROFILE)

    def prepare(self):
        return session.prepare_repair(self.qa.server, 'physical-software', 'drc-software', self.failed['id'], self.qa.revision)

    def test_v7_keeps_all_prior_bundles_and_original_accepted_v2_binding(self):
        old = {path: path.read_bytes() for path in self.qa.directory.glob('*.json')}
        stores = {path: path.read_bytes() for path in self.qa.system.iterdir()}
        status = self.prepare(); self.assertEqual(status['profile_version'], session.V7_PROFILE)
        config = self.qa.server.lvs_workflow.tool_configuration
        self.assertEqual(config['repair_upgrade_binding']['previous_profile_version'], session.V6_PROFILE)
        self.assertEqual(config['repair_upgrade_binding']['previous_bundle_sha256'], hashlib.sha256(self.v6raw).hexdigest())
        self.assertEqual(config['repair_upgrade_binding']['failed_lvs_run_id'], self.failed['id'])
        self.assertEqual(old, {path: path.read_bytes() for path in old}); self.assertEqual(stores, {path: path.read_bytes() for path in stores})
        self.assertEqual(config['repair_source_binding']['historical_lvs_run_id'], self.qa.records['lvs']['id'])

    def test_v7_restore_after_later_run_and_idempotence_preserve_exact_bundle(self):
        self.prepare(); raw = self.path.read_bytes(); mtime = self.path.stat().st_mtime_ns
        self.qa.server.lvs_workflow.current = False
        self.assertEqual(self.prepare()['profile_version'], session.V7_PROFILE)
        self.assertEqual(self.path.read_bytes(), raw); self.assertEqual(self.path.stat().st_mtime_ns, mtime)
        self.qa.histories['lvs']['runs'].append({'id': 'later-v7-fixture'}); self.qa.write_histories()
        restored, status = self.qa.restore()
        self.assertTrue(status['configured'], status['error']); self.assertEqual(status['profile_version'], session.V7_PROFILE)
        self.assertEqual(restored[4], self.qa.server.lvs_workflow.tool_configuration)

    def test_incomplete_v6_launch_or_passed_validation_cannot_prepare_v7(self):
        for execution, validation in (('Failed', 'Failed'), ('Running', 'Failed'), ('Completed', 'Passed')):
            original = copy.deepcopy(self.failed)
            self.failed.update(execution_status=execution, validation_status=validation); checksum(self.failed)
            self.qa.histories['lvs']['runs'][-1] = self.failed; self.qa.write_histories()
            self.qa.server.lvs_workflow._state['runs'][-1] = copy.deepcopy(self.failed)
            with self.subTest(execution=execution, validation=validation), self.assertRaises(DomainError): self.prepare()
            self.assertFalse(self.path.exists()); self.failed = original
        for previous in (session.PROFILE, session.UPGRADE_PROFILE, session.V5_PROFILE):
            self.assertFalse(session._upgrade_failure_status({'execution_status': 'Completed', 'validation_status': 'Failed'}, previous))
        incomplete = copy.deepcopy(self.failed)
        incomplete['checks']['checks']['extraction']['validation_status'] = 'Failed'
        self.assertFalse(session._upgrade_failure_status(incomplete, session.V6_PROFILE))

    def test_v7_metadata_exposes_completed_failed_v6_without_proof_or_write(self):
        before = copy.deepcopy(self.qa.server.lvs_workflow._state)
        meta = session.eligibility(self.qa.server)
        self.assertTrue(meta['eligible'], meta['blocked_reason']); self.assertEqual(meta['mode'], 'upgrade_v7')
        self.assertEqual(meta['source']['previous_profile_version'], session.V6_PROFILE)
        self.assertEqual(meta['source']['source_lvs_run_id'], self.failed['id'])
        self.assertEqual(meta['source']['previous_bundle_sha256'], hashlib.sha256(self.v6raw).hexdigest())
        self.assertEqual(meta['source']['historical_lvs_run_id'], self.qa.records['lvs']['id'])
        self.assertEqual(self.qa.server.lvs_workflow._state, before); self.assertFalse(self.path.exists())

    def test_changed_or_missing_v6_ancestor_does_not_restore_v7(self):
        self.prepare(); raw = self.path.read_bytes()
        self.base.path.write_bytes(self.v6raw+b'\n')
        restored, status = self.qa.restore()
        self.assertFalse(status['configured']); self.assertEqual(restored, self.qa.base); self.assertEqual(self.path.read_bytes(), raw)
        self.base.path.unlink()  # Disposable software fixture only.
        restored, status = self.qa.restore()
        self.assertFalse(status['configured']); self.assertEqual(restored, self.qa.base)

    def test_full_completed_v6_failure_proof_scope_is_required(self):
        proof = self.base.base.base.failed_proof; original = proof.side_effect
        def wrong_scope(result, drc, layout, config):
            if config['profile']['profile_version'] == session.V6_PROFILE:
                return {'validation_status': 'Passed', 'scope': 'actual_failed_v5_execution_proof_only_not_LVS_success'}
            return original(result, drc, layout, config)
        proof.side_effect = wrong_scope
        with self.assertRaises(DomainError): self.prepare()
        self.assertFalse(self.path.exists())


if __name__ == '__main__': unittest.main()
