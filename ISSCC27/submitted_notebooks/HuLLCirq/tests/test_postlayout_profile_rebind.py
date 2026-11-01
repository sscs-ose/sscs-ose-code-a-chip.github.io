"""Preparation-only recovery from an available but old-layout S14 profile."""
import copy
from contextlib import nullcontext
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from hullcirq.domain import DomainError
from hullcirq.postlayout_workflow import PostLayoutWorkflowManager
from hullcirq.verification import object_hash


def source_fixture():
    current = {'revision': {'id': 'revision-current-gui'}}
    records = {name: {'id': name+'-new-adopted', 'record_hash': name+'-saved-checksum',
                     'revision_id': 'revision-original-source'} for name in ('layout', 'drc', 'lvs')}
    records['layout'].update(runtime_configuration={'profile': 'new-source-bound-physical'},
        verification_plan_sha256='original-plan-hash', settings_sha256='original-clock-settings-hash')
    manager = SimpleNamespace(_profile_prepare_available=lambda: True,
        _source_locks=lambda: nullcontext(), _adopted_sources_locked=Mock(return_value=(current, {}, records, {})))
    return manager, records


class PostlayoutProfileRebindTests(unittest.TestCase):
    def test_preparation_metadata_exposes_exact_adopted_chain_without_mutation(self):
        manager, records = source_fixture(); before = copy.deepcopy(records)
        value = PostLayoutWorkflowManager._profile_preparation_sources(manager)
        self.assertTrue(value['available'])
        self.assertEqual(value['scope'], 'adopted_source_chain_for_explicit_profile_preparation_only')
        self.assertEqual(value['revision_id'], 'revision-current-gui')
        self.assertEqual(value['source_revision_id'], 'revision-original-source')
        for name, record in records.items():
            self.assertEqual(value[name+'_run_id'], record['id'])
            self.assertEqual(value[name+'_record_hash'], record['record_hash'])
        self.assertEqual(value['physical_runtime_sha256'], object_hash(records['layout']['runtime_configuration']))
        self.assertEqual(value['verification_plan_sha256'], 'original-plan-hash')
        self.assertEqual(value['settings_sha256'], 'original-clock-settings-hash')
        self.assertEqual(records, before)

    def test_explicit_or_injected_profile_has_no_preparation_candidate(self):
        manager, _ = source_fixture(); manager._profile_prepare_available = lambda: False
        value = PostLayoutWorkflowManager._profile_preparation_sources(manager)
        self.assertFalse(value['available']); manager._adopted_sources_locked.assert_not_called()
        self.assertNotIn('layout_run_id', value)

    def test_stale_withdrawn_or_missing_chain_is_not_exposed_as_preparation_ready(self):
        for error in (DomainError('postlayout_sources_not_adopted', 'Latest source is stale.'),
                      DomainError('postlayout_adoption_conflict', 'Adoption was withdrawn.'),
                      FileNotFoundError('Missing saved source'), KeyError('Missing source field')):
            manager, _ = source_fixture(); manager._adopted_sources_locked.side_effect = error
            value = PostLayoutWorkflowManager._profile_preparation_sources(manager)
            self.assertFalse(value['available']); self.assertNotIn('layout_run_id', value)
            self.assertTrue(value['blocked_reason'])

    def test_preparation_projection_does_not_read_old_runtime_or_replace_it(self):
        manager, _ = source_fixture()
        manager.tool_configuration = {'profile_version': 'hullcirq-postroute-functional-sta-v4',
                                      'physical_runtime': {'old-layout': True}}
        before = copy.deepcopy(manager.tool_configuration)
        value = PostLayoutWorkflowManager._profile_preparation_sources(manager)
        self.assertTrue(value['available']); self.assertEqual(manager.tool_configuration, before)

    def test_available_old_runtime_stays_execution_blocked_with_separate_prepare_identity(self):
        manager, _ = source_fixture()
        prepare = PostLayoutWorkflowManager._profile_preparation_sources(manager)
        old = {'profile_version': 'hullcirq-postroute-functional-sta-v4', 'physical_runtime': {'old': True}}
        state = {'runs': [], 'reviews': [], 'source_key': 'blocked-key', 'source_epoch': 4}
        view = SimpleNamespace(lock=threading.RLock(), _state=state, tool_configuration=old,
            _storage_error=None, _explicit_configuration=False, _configuration_error=None,
            observe_design=lambda: ('blocked-key', None, {'message': 'Use the selected layout runtime.'}),
            _capability=lambda: {'available': True, 'verification_supported': True,
                                'execution_scope': 'post_route_functional_plus_sta'},
            _adapter_metadata=lambda: {}, _cleanup_unresolved=lambda: False,
            _profile_prepare_available=lambda: True, _profile_update_available=lambda: False,
            _profile_prepare_needed=lambda: True, _adapter_profile_prepare_needed=lambda metadata: False,
            _profile_preparation_sources=lambda: copy.deepcopy(prepare))
        # Match the real constructor's memory-only durable receipt snapshot.
        view._committed = copy.deepcopy(state)
        before = copy.deepcopy((state, old))
        value = PostLayoutWorkflowManager.envelope(view)['postlayout_workflow']
        self.assertTrue(value['tool_ready']); self.assertFalse(value['ready'])
        self.assertTrue(value['profile_prepare_needed'])
        self.assertEqual(value['blocked_reason'], 'Use the selected layout runtime.')
        self.assertTrue(value['profile_preparation_sources']['available'])
        for key in ('layout_run_id', 'drc_run_id', 'lvs_run_id', 'source_inputs', 'input_gds_sha256', 'input_netlist_sha256'):
            self.assertIsNone(value[key])
        self.assertEqual((state, old), before)

    def test_execution_ready_source_does_not_use_preparation_fallback(self):
        # The new metadata cannot substitute for execution inputs or revive an
        # old accepted S14. Existing ready-source behavior remains authoritative.
        manager, _ = source_fixture()
        manager._profile_prepare_available = lambda: False
        self.assertFalse(PostLayoutWorkflowManager._profile_preparation_sources(manager)['available'])
        self.assertNotIn('ready', PostLayoutWorkflowManager._profile_preparation_sources(manager))


if __name__ == '__main__':
    unittest.main()
