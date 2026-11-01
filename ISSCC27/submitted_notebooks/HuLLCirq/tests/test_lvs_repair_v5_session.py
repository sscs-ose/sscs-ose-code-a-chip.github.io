"""Three-generation correction sessions; isolated doubles and no EDA."""
import copy
import hashlib
import json
import unittest

from hullcirq import lvs_repair_session as session
from hullcirq.domain import DomainError
import test_lvs_repair_upgrade_session as fixtures
from test_lvs_repair_session import checksum


class LvsRepairV5SessionTests(unittest.TestCase):
    def setUp(self):
        self.base = fixtures.LvsRepairUpgradeSessionTests('runTest'); self.base.setUp()
        self.addCleanup(self.base.doCleanups)
        self.base.prepare(); self.qa = self.base.qa
        self.v4_raw = self.base.path.read_bytes(); self.v4_mtime = self.base.path.stat().st_mtime_ns
        self.failed = copy.deepcopy(self.base.failed)
        self.failed.update(id='lvs-software-failed-v4', runtime_configuration=copy.deepcopy(self.qa.server.lvs_workflow.tool_configuration))
        checksum(self.failed)
        self.qa.histories['lvs']['runs'].append(self.failed); self.qa.write_histories()
        self.qa.server.lvs_workflow._state['runs'].append(copy.deepcopy(self.failed))
        self.base.failed_proof.side_effect = lambda result, drc, layout, config: {
            'validation_status': 'Passed', 'scope': 'actual_failed_'+config['profile']['profile_version'].rsplit('-', 1)[-1]+'_execution_proof_only_not_LVS_success'}
        (self.qa.root/'configs/lvs_profile_sky130_v5.json').write_text(json.dumps({'profile_version': session.V5_PROFILE}), encoding='utf-8')
        self.path = session._upgrade_path(self.qa.directory, session.V5_PROFILE)

    def prepare(self):
        return session.prepare_repair(self.qa.server, 'physical-software', 'drc-software', self.failed['id'], self.qa.revision)

    def test_explicit_v5_preserves_both_ancestor_bundles_and_original_v2_binding(self):
        old = {p: p.read_bytes() for p in self.qa.system.iterdir()}
        status = self.prepare(); self.assertEqual(status['profile_version'], session.V5_PROFILE)
        config = self.qa.server.lvs_workflow.tool_configuration
        self.assertEqual(config['repair_source_binding'], self.base.previous['configuration']['repair_source_binding'])
        self.assertEqual(config['repair_upgrade_binding']['previous_profile_version'], session.UPGRADE_PROFILE)
        self.assertEqual(config['repair_upgrade_binding']['previous_bundle_sha256'], hashlib.sha256(self.v4_raw).hexdigest())
        self.assertEqual(config['repair_upgrade_binding']['failed_lvs_run_id'], self.failed['id'])
        self.assertEqual(self.base.path.read_bytes(), self.v4_raw); self.assertEqual(self.base.path.stat().st_mtime_ns, self.v4_mtime)
        self.assertEqual(self.qa.path.read_bytes(), self.base.previous_raw)
        self.assertEqual(old, {p: p.read_bytes() for p in old})

    def test_restore_reconstructs_all_ancestors_and_keeps_v5_after_later_record(self):
        self.prepare(); self.qa.histories['lvs']['runs'].append({'id': 'later-v5-software-run'}); self.qa.write_histories()
        restored, status = self.qa.restore()
        self.assertTrue(status['configured'], status['error']); self.assertEqual(status['profile_version'], session.V5_PROFILE)
        self.assertEqual(restored[4], self.qa.server.lvs_workflow.tool_configuration)
        self.assertEqual(restored[:4], self.qa.base[:4]); self.assertEqual(restored[5], self.qa.base[5])

    def test_v5_metadata_distinguishes_failed_v4_and_historical_v2(self):
        before = copy.deepcopy(self.qa.server.lvs_workflow._state)
        meta = session.eligibility(self.qa.server)
        self.assertTrue(meta['eligible'], meta['blocked_reason']); self.assertEqual(meta['mode'], 'upgrade_v5')
        self.assertEqual(meta['source']['previous_profile_version'], session.UPGRADE_PROFILE)
        self.assertEqual(meta['source']['previous_bundle_sha256'], hashlib.sha256(self.v4_raw).hexdigest())
        self.assertEqual(meta['source']['source_lvs_run_id'], self.failed['id'])
        self.assertEqual(meta['source']['historical_lvs_run_id'], self.qa.records['lvs']['id'])
        self.assertEqual(self.qa.server.lvs_workflow._state, before); self.assertFalse(self.path.exists())

    def test_same_v5_prepare_is_idempotent(self):
        self.prepare(); raw = self.path.read_bytes(); mtime = self.path.stat().st_mtime_ns
        self.qa.server.lvs_workflow.current = False
        self.assertEqual(self.prepare()['profile_version'], session.V5_PROFILE)
        self.assertEqual(self.path.read_bytes(), raw); self.assertEqual(self.path.stat().st_mtime_ns, mtime)

    def test_changed_v4_ancestor_or_orphan_v5_never_restores(self):
        self.prepare(); raw = self.path.read_bytes()
        self.base.path.write_bytes(self.v4_raw+b'\n')
        restored, status = self.qa.restore()
        self.assertFalse(status['configured']); self.assertEqual(restored, self.qa.base); self.assertEqual(self.path.read_bytes(), raw)
        self.base.path.unlink()  # Disposable software fixture only.
        restored, status = self.qa.restore()
        self.assertFalse(status['configured']); self.assertEqual(restored, self.qa.base); self.assertEqual(self.path.read_bytes(), raw)

    def test_wrong_failed_version_scope_and_unknown_recipe_fail_closed(self):
        self.base.failed_proof.side_effect = None
        self.base.failed_proof.return_value = {'validation_status': 'Passed', 'scope': 'actual_failed_v3_execution_proof_only_not_LVS_success'}
        with self.assertRaises(DomainError): self.prepare()
        self.assertFalse(self.path.exists())
        with self.assertRaises(DomainError): session._upgrade_path(self.qa.directory, 'arbitrary-v6')


if __name__ == '__main__': unittest.main()
