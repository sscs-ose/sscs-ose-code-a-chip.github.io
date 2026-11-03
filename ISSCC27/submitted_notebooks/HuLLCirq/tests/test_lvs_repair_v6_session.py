"""Fourth versioned LVS preparation; isolated records and no EDA."""
import copy
import hashlib
import json
import unittest

from hullcirq import lvs_repair_session as session
from hullcirq.domain import DomainError
import test_lvs_repair_v5_session as fixtures
from test_lvs_repair_session import checksum


class LvsRepairV6SessionTests(unittest.TestCase):
    def setUp(self):
        self.base = fixtures.LvsRepairV5SessionTests('runTest'); self.base.setUp()
        self.addCleanup(self.base.doCleanups)
        self.base.prepare(); self.qa = self.base.qa
        self.v5raw = self.base.path.read_bytes(); self.v5mtime = self.base.path.stat().st_mtime_ns
        self.failed = copy.deepcopy(self.base.failed)
        self.failed.update(id='lvs-software-failed-v5', runtime_configuration=copy.deepcopy(self.qa.server.lvs_workflow.tool_configuration))
        checksum(self.failed); self.qa.histories['lvs']['runs'].append(self.failed); self.qa.write_histories()
        self.qa.server.lvs_workflow._state['runs'].append(copy.deepcopy(self.failed))
        (self.qa.root/'configs/lvs_profile_sky130_v6.json').write_text(json.dumps({'profile_version': session.V6_PROFILE}), encoding='utf-8')
        self.path = session._upgrade_path(self.qa.directory, session.V6_PROFILE)

    def prepare(self):
        return session.prepare_repair(self.qa.server, 'physical-software', 'drc-software', self.failed['id'], self.qa.revision)

    def test_explicit_v6_keeps_original_binding_and_all_three_prior_bundles(self):
        old = {path: path.read_bytes() for path in self.qa.directory.glob('*.json')}
        stores = {path: path.read_bytes() for path in self.qa.system.iterdir()}
        status = self.prepare(); self.assertEqual(status['profile_version'], session.V6_PROFILE)
        config = self.qa.server.lvs_workflow.tool_configuration
        self.assertEqual(config['repair_upgrade_binding']['previous_profile_version'], session.V5_PROFILE)
        self.assertEqual(config['repair_upgrade_binding']['previous_bundle_sha256'], hashlib.sha256(self.v5raw).hexdigest())
        self.assertEqual(config['repair_upgrade_binding']['failed_lvs_run_id'], self.failed['id'])
        self.assertEqual(status['source_identity'], self.qa.server.lvs_repair_session['source_identity'])
        self.assertEqual(config['repair_source_binding'], self.base.base.previous['configuration']['repair_source_binding'])
        self.assertEqual(old, {path: path.read_bytes() for path in old}); self.assertEqual(stores, {path: path.read_bytes() for path in stores})

    def test_restore_revalidates_complete_chain_after_later_run(self):
        self.prepare(); self.qa.histories['lvs']['runs'].append({'id': 'later-v6-software'}); self.qa.write_histories()
        restored, status = self.qa.restore()
        self.assertTrue(status['configured'], status['error']); self.assertEqual(status['profile_version'], session.V6_PROFILE)
        self.assertEqual(restored[4], self.qa.server.lvs_workflow.tool_configuration)
        self.assertEqual(restored[:4], self.qa.base[:4]); self.assertEqual(restored[5], self.qa.base[5])

    def test_idempotent_v6_never_overwrites_ancestor_or_target(self):
        self.prepare(); raw = self.path.read_bytes(); mtime = self.path.stat().st_mtime_ns
        self.qa.server.lvs_workflow.current = False
        self.assertEqual(self.prepare()['profile_version'], session.V6_PROFILE)
        self.assertEqual(self.path.read_bytes(), raw); self.assertEqual(self.path.stat().st_mtime_ns, mtime)
        self.assertEqual(self.base.path.read_bytes(), self.v5raw); self.assertEqual(self.base.path.stat().st_mtime_ns, self.v5mtime)

    def test_recomputed_changed_or_missing_v5_ancestor_never_restores_v6(self):
        self.prepare(); raw = self.path.read_bytes()
        changed = json.loads(self.v5raw); changed['configuration']['working_directory'] = 'foreign'; checksum(changed)
        self.base.path.write_text(json.dumps(changed), encoding='utf-8')
        restored, status = self.qa.restore()
        self.assertFalse(status['configured']); self.assertEqual(restored, self.qa.base); self.assertEqual(self.path.read_bytes(), raw)
        self.base.path.unlink()  # Disposable software fixture only.
        restored, status = self.qa.restore()
        self.assertFalse(status['configured']); self.assertEqual(restored, self.qa.base); self.assertEqual(self.path.read_bytes(), raw)

    def test_readonly_metadata_binds_failed_v5_and_original_v2_separately(self):
        before = copy.deepcopy(self.qa.server.lvs_workflow._state)
        meta = session.eligibility(self.qa.server)
        self.assertTrue(meta['eligible'], meta['blocked_reason']); self.assertEqual(meta['mode'], 'upgrade_v6')
        self.assertEqual(meta['source']['source_lvs_run_id'], self.failed['id'])
        self.assertEqual(meta['source']['previous_profile_version'], session.V5_PROFILE)
        self.assertEqual(meta['source']['previous_bundle_sha256'], hashlib.sha256(self.v5raw).hexdigest())
        self.assertEqual(meta['source']['historical_lvs_run_id'], self.qa.records['lvs']['id'])
        self.assertEqual(self.qa.server.lvs_workflow._state, before); self.assertFalse(self.path.exists())

    def test_failed_v5_requires_exact_dynamic_scope_not_v4_or_success(self):
        proof = self.base.base.failed_proof; original = proof.side_effect
        def wrong_scope(result, drc, layout, config):
            if config['profile']['profile_version'] == session.V5_PROFILE:
                return {'validation_status': 'Passed', 'scope': 'actual_failed_v4_execution_proof_only_not_LVS_success'}
            return original(result, drc, layout, config)
        proof.side_effect = wrong_scope
        with self.assertRaises(DomainError): self.prepare()
        self.assertFalse(self.path.exists())


if __name__ == '__main__': unittest.main()
