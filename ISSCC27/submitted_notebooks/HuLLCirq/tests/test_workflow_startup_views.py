"""Presentation-pass reuse must not become an execution/adoption cache."""
from __future__ import annotations

import copy
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from hullcirq.domain import DomainError
from hullcirq.workflow import WorkflowManager, ensure_current_verification_plan


class WorkflowStartupViewsTests(unittest.TestCase):
    def make_manager(self, count=8):
        manager = WorkflowManager.__new__(WorkflowManager)
        manager.lock = threading.RLock()
        manager._storage_error = None
        manager.observe_design = Mock()
        manager.store = SimpleNamespace(lock=threading.RLock(), envelope=Mock(return_value={
            'design': {'value': 1}, 'revision': {'id': 'revision'}}))
        manager.generation = SimpleNamespace(lock=threading.RLock(),
            current_candidate_selection=Mock(return_value={'node': 'candidate'}),
            _state={'jobs': [{'id': 'candidate', 'rtl': 'module node; endmodule', 'operation': 'generate', 'base_job_id': None}]})
        synthesis = {'id': 'synth', 'node_id': 'node', 'stage_id': 'local_synthesis',
            'candidate_id': 'candidate', 'input_hash': 'input', 'revision_id': 'revision',
            'execution_status': 'Completed', 'validation_status': 'Passed',
            'review_status': 'Accepted', 'acceptance_epoch': 1, 'netlist': 'netlist',
            'netlist_sha256': 'netlist-hash', 'verification_plan': None}
        plan = {'kind': 'npu2_control_original_job', 'template': 'v1', 'value': 1}
        simulations = [{**copy.deepcopy(synthesis), 'id': f'sim-{index}',
            'stage_id': 'local_netlist_simulation', 'prior_run_id': 'synth',
            'verification_plan': copy.deepcopy(plan)} for index in range(count)]
        batch = {'id': 'batch', 'revision_id': 'revision', 'stage_id': 'local_netlist_simulation',
            'execution_status': 'Completed', 'items': [{'node_id': 'node', 'candidate_id': 'candidate',
                'prior_run_id': 'synth', 'run_id': simulations[-1]['id'], 'status': 'Passed'}]}
        manager._state = {'runs': [synthesis, *simulations], 'batches': [batch], 'reviews': [],
                          'node_inputs': {'node': 'input'}, 'node_epochs': {'node': 1}}
        # Match the real constructor's memory-only durable receipt snapshot.
        manager._committed = copy.deepcopy(manager._state)
        return manager, plan

    def patches(self, plan):
        return (patch('hullcirq.workflow.build_verification_plan', return_value=copy.deepcopy(plan)),
                patch('hullcirq.workflow.verification_template_version', side_effect=lambda p: p['template']),
                patch('hullcirq.workflow.compare_attempt', return_value=None))

    def test_one_read_view_matches_uncached_records_and_batches(self):
        manager, plan = self.make_manager()
        raw = copy.deepcopy(manager._state)
        build, template, compare = self.patches(plan)
        with build as builder, template, compare:
            expected_runs = [manager._decorate(run) for run in manager._state['runs']]
            expected_batches = [manager._decorate_batch(batch) for batch in manager._state['batches']]
            manager.generation.current_candidate_selection.reset_mock()
            builder.reset_mock()
            actual = manager.envelope()
            self.assertEqual(actual['workflow_runs'], expected_runs)
            self.assertEqual(actual['workflow_batches'], expected_batches)
            self.assertEqual(manager.generation.current_candidate_selection.call_count, 1)
            self.assertEqual(builder.call_count, 1)
        self.assertEqual(manager._state, raw)
        actual['workflow_runs'][0]['netlist'] = 'caller change'
        self.assertEqual(manager._state, raw)

    def test_new_read_and_default_execution_guard_recheck_sources(self):
        manager, plan = self.make_manager()
        build, template, compare = self.patches(plan)
        with build as builder, template, compare:
            self.assertEqual(manager.envelope()['workflow_nodes'][-1]['accepted_run_id'], 'sim-7')
            manager.generation.current_candidate_selection.return_value = {'node': None}
            self.assertIsNone(manager.envelope()['workflow_nodes'][-1]['accepted_run_id'])
            with self.assertRaises(DomainError) as error:
                manager._fifo_source_current('candidate', 'node', 'synth', plan)
            self.assertEqual(error.exception.code, 'candidate_not_adopted')
            self.assertEqual(manager.generation.current_candidate_selection.call_count, 3)
            self.assertEqual(builder.call_count, 1)

    def test_each_saved_plan_is_checked_even_when_reference_is_shared(self):
        manager, plan = self.make_manager()
        manager._state['runs'][-1]['verification_plan']['value'] = 2
        build, template, compare = self.patches(plan)
        with build as builder, template, compare:
            result = manager.envelope()
            self.assertEqual(builder.call_count, 1)
        self.assertEqual(result['workflow_runs'][-2]['freshness'], 'Current')
        self.assertEqual(result['workflow_runs'][-1]['freshness'], 'Stale')
        self.assertEqual(result['workflow_runs'][-1]['review_status'], 'Awaiting Review')
        self.assertIsNone(result['workflow_nodes'][-1]['accepted_run_id'])

    def test_changed_original_input_is_checked_on_next_read(self):
        manager, plan = self.make_manager()
        build, template, compare = self.patches(plan)
        with build as builder, template, compare:
            self.assertEqual(manager.envelope()['workflow_runs'][-1]['freshness'], 'Current')
            builder.return_value = {**plan, 'value': 99}
            self.assertEqual(manager.envelope()['workflow_runs'][-1]['freshness'], 'Stale')
            self.assertEqual(builder.call_count, 2)

    def test_templates_are_separate_and_default_plan_guard_is_not_cached(self):
        plan = {'kind': 'npu2_control_original_job', 'template': 'v1', 'value': 1}
        other = {**plan, 'template': 'v2'}
        cache = {}
        with patch('hullcirq.workflow.verification_template_version', side_effect=lambda p: p['template']), \
                patch('hullcirq.workflow.build_verification_plan', side_effect=lambda d, n, t: {**plan, 'template': t}) as builder:
            ensure_current_verification_plan({}, 'node', plan, rebuilt_plans=cache)
            ensure_current_verification_plan({}, 'node', other, rebuilt_plans=cache)
            ensure_current_verification_plan({}, 'node', plan, rebuilt_plans=cache)
            self.assertEqual(builder.call_count, 2)
            ensure_current_verification_plan({}, 'node', plan)
            ensure_current_verification_plan({}, 'node', plan)
            self.assertEqual(builder.call_count, 4)

    def test_presentation_input_capture_holds_source_locks(self):
        manager, plan = self.make_manager()
        def selection():
            self.assertTrue(manager.lock._is_owned())
            self.assertTrue(manager.generation.lock._is_owned())
            self.assertTrue(manager.store.lock._is_owned())
            return {'node': 'candidate'}
        manager.generation.current_candidate_selection.side_effect = selection
        build, template, compare = self.patches(plan)
        with build, template, compare:
            self.assertEqual(manager.envelope()['workflow_runs'][-1]['freshness'], 'Current')


if __name__ == '__main__':
    unittest.main()
