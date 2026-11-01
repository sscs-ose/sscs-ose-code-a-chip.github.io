"""Fresh warnings go directly to latest fixed recipe, never known failures."""
import copy
import json
import unittest
from unittest.mock import patch

from hullcirq import lvs_repair_session as session
from hullcirq.domain import DomainError
import test_lvs_repair_session as fixtures


class DirectV7SessionTests(unittest.TestCase):
    def setUp(self):
        self.qa = fixtures.LvsRepairSessionTests('runTest'); self.qa.setUp(); self.addCleanup(self.qa.doCleanups)
        base = list(self.qa.base); base[4] = copy.deepcopy(base[4]); base[4]['profile'] = {'profile_version': 'hullcirq-sky130-lvs-v2'}
        self.qa.base = tuple(base); self.qa.server.workspace.configurations = copy.deepcopy(self.qa.base)
        self.qa.records['lvs']['runtime_configuration'] = copy.deepcopy(base[4]); fixtures.checksum(self.qa.records['lvs'])
        self.qa.server.lvs_workflow.tool_configuration = copy.deepcopy(base[4])
        self.qa.server.lvs_workflow._state['runs'] = [copy.deepcopy(self.qa.records['lvs'])]; self.qa.write_histories()
        self.qa.stack.enter_context(patch('hullcirq.physical_repair_session.load_repair_configurations', return_value=(self.qa.base, {'error': None})))
        (self.qa.root/'configs/lvs_profile_sky130_v7.json').write_text(json.dumps({'profile_version': session.V7_PROFILE}), encoding='utf-8')
        self.path = session._direct_path(self.qa.directory)

    def prepare(self):
        return session.prepare_repair(self.qa.server, 'physical-software', 'drc-software', 'lvs-software', self.qa.revision)

    def test_new_initial_action_is_direct_v7_without_any_intermediate_attempt(self):
        old = {path: path.read_bytes() for path in self.qa.system.iterdir()}
        with patch.object(session, '_prepare_v3', side_effect=AssertionError('No broken intermediate preparation')):
            status = self.prepare()
        self.assertEqual(status['preparation_kind'], 'direct_v7'); self.assertEqual(status['profile_version'], session.V7_PROFILE)
        config = self.qa.server.lvs_workflow.tool_configuration
        self.assertEqual(config['repair_preparation_kind'], 'direct_v7'); self.assertNotIn('repair_upgrade_binding', config)
        self.assertEqual(config['repair_source_binding'], session._identity(self.qa.records))
        self.assertFalse(self.qa.path.exists()); self.assertFalse(any(session._upgrade_path(self.qa.directory, v).exists() for v in session.UPGRADES))
        self.assertEqual(old, {path: path.read_bytes() for path in old})

    def test_direct_restore_and_idempotence_do_not_need_ancestor_or_latest_record(self):
        self.prepare(); raw = self.path.read_bytes(); mtime = self.path.stat().st_mtime_ns
        self.qa.server.lvs_workflow.current = False
        self.assertEqual(self.prepare()['profile_version'], session.V7_PROFILE)
        self.assertEqual(self.path.read_bytes(), raw); self.assertEqual(self.path.stat().st_mtime_ns, mtime)
        self.qa.histories['lvs']['runs'].append({'id': 'later-direct-v7-fixture'}); self.qa.write_histories()
        restored, status = self.qa.restore()
        self.assertTrue(status['configured'], status['error']); self.assertEqual(status['preparation_kind'], 'direct_v7')
        self.assertEqual(restored[4], self.qa.server.lvs_workflow.tool_configuration)

    def test_initial_metadata_is_readonly_latest_v7_and_exact_accepted_original(self):
        before = copy.deepcopy(self.qa.server.lvs_workflow._state)
        meta = session.eligibility(self.qa.server)
        self.assertTrue(meta['eligible'], meta['blocked_reason']); self.assertEqual(meta['mode'], 'initial_v7')
        self.assertEqual(meta['profile_version'], session.V7_PROFILE)
        self.assertEqual(meta['source']['source_lvs_run_id'], 'lvs-software')
        self.assertFalse(self.path.exists()); self.assertEqual(self.qa.server.lvs_workflow._state, before)

    def test_first_lvs_run_is_required_without_instructing_warning_adoption(self):
        self.qa.server.lvs_workflow._state['runs'] = []
        before = copy.deepcopy(self.qa.server.lvs_workflow._state)
        files = {path: path.read_bytes() for path in self.qa.system.iterdir()}
        meta = session.eligibility(self.qa.server)
        self.assertTrue(meta['available'])
        self.assertFalse(meta['eligible'])
        self.assertIsNone(meta['source'])
        self.assertIn('Run the original LVS check and inspect its extraction feedback', meta['blocked_reason'])
        self.assertIn('Adoption is not required', meta['blocked_reason'])
        self.assertNotIn('Run and adopt', meta['blocked_reason'])
        self.assertEqual(self.qa.server.lvs_workflow._state, before)
        self.assertEqual({path: path.read_bytes() for path in self.qa.system.iterdir()}, files)
        self.assertFalse(self.path.exists())

    def test_missing_latest_recipe_never_falls_back_to_v3(self):
        (self.qa.root/'configs/lvs_profile_sky130_v7.json').unlink()  # Disposable fixture.
        self.assertFalse(session.eligibility(self.qa.server)['eligible'])
        with self.assertRaises(DomainError): self.prepare()
        self.assertFalse(self.path.exists()); self.assertFalse(self.qa.path.exists())

    def test_conflicting_legacy_bundle_is_not_bypassed_or_overwritten(self):
        self.qa.directory.mkdir(parents=True, exist_ok=True)
        self.qa.path.write_bytes(b'SOFTWARE_QA_EXISTING_IMMUTABLE_CHAIN')
        with self.assertRaises(DomainError): self.prepare()
        self.assertFalse(self.path.exists()); self.assertEqual(self.qa.path.read_bytes(), b'SOFTWARE_QA_EXISTING_IMMUTABLE_CHAIN')
        self.qa.path.unlink(); self.prepare(); raw = self.path.read_bytes()
        self.qa.path.write_bytes(b'SOFTWARE_QA_CONFLICT')
        restored, status = self.qa.restore()
        self.assertFalse(status['configured']); self.assertEqual(restored, self.qa.base); self.assertEqual(self.path.read_bytes(), raw)

    def test_recomputed_direct_configuration_checksum_does_not_authorize_changes(self):
        self.prepare(); bundle = json.loads(self.path.read_bytes()); bundle['configuration']['working_directory'] = 'foreign'
        fixtures.checksum(bundle); self.path.write_text(json.dumps(bundle), encoding='utf-8'); raw = self.path.read_bytes()
        restored, status = self.qa.restore()
        self.assertFalse(status['configured']); self.assertEqual(restored, self.qa.base); self.assertEqual(self.path.read_bytes(), raw)


if __name__ == '__main__': unittest.main()
