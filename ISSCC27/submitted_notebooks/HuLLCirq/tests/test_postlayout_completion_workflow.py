"""Mode-specific S14 contracts using explicit software fixtures only."""
from __future__ import annotations
import copy
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import test_postlayout_workflow as existing
from hullcirq import postlayout_tools
from hullcirq.domain import DomainError
from hullcirq.postlayout_workflow import (
    POST_ROUTE_SCOPE, POST_ROUTE_REQUIRED_CHECKS, POST_ROUTE_REQUIRED_FILES,
    validate_artifact_manifest, validate_postlayout_proof,
)


def completion_runner(*args, **kwargs):
    result = existing.fixture_runner(*args, **kwargs)
    result['execution_scope'] = POST_ROUTE_SCOPE
    result['checks'] = {key: {'validation_status': 'Passed'} for key in POST_ROUTE_REQUIRED_CHECKS}
    result['artifacts'] = [entry for entry in result['artifacts'] if entry['id'] in POST_ROUTE_REQUIRED_FILES]
    return result


class PostRouteCompletionWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.base = existing.PostLayoutWorkflowTests('runTest')
        self.base.setUp()
        self.addCleanup(self.base.doCleanups)
        self.manager = self.base.manager
        self.manager.tool_configuration['execution_scope'] = POST_ROUTE_SCOPE
        self.capability = patch.object(self.manager, '_capability', return_value={
            'available': True, 'verification_supported': True, 'execution_scope': POST_ROUTE_SCOPE,
            'reason': 'SOFTWARE QA ONLY: no tool execution',
        })
        self.capability.start()
        self.addCleanup(self.capability.stop)

    def test_complete_mode_is_adoptable_without_claiming_sdf_annotation(self):
        run = self.base.run_postlayout(completion_runner)
        self.assertEqual((run['execution_status'], run['validation_status'], run['review_status']),
                         ('Completed', 'Passed', 'Accepted'))
        self.assertEqual(run['evidence_kind'], 'software_qa_fixture')
        self.assertTrue(run['checks']['software_qa_fixture'])
        self.assertEqual(set(run['checks']['checks']), set(POST_ROUTE_REQUIRED_CHECKS))
        self.assertNotIn('annotation', run['checks']['checks'])
        self.assertNotIn('input-sdf', {entry['id'] for entry in run['checks']['artifacts']})
        validate_postlayout_proof(run, existing.fixture_validator)
        reopened = self.base.new_manager()
        self.addCleanup(reopened.close)
        self.assertEqual(reopened._state['runs'][-1]['review_status'], 'Accepted')

    def test_each_required_sta_or_functional_check_blocks_adoption_if_missing_or_unsupported(self):
        run = self.base.run_postlayout(completion_runner)
        for key in POST_ROUTE_REQUIRED_CHECKS:
            for missing in (False, True):
                invalid = copy.deepcopy(run)
                if missing:
                    invalid['checks']['checks'].pop(key)
                else:
                    invalid['checks']['checks'][key]['validation_status'] = 'Unsupported'
                with self.subTest(check=key, missing=missing), self.assertRaises(DomainError) as error:
                    validate_postlayout_proof(invalid, existing.fixture_validator)
                self.assertEqual(error.exception.code, 'postlayout_proof_conflict')

    def test_each_mode_artifact_is_mandatory_and_hash_tamper_is_rejected(self):
        run = self.base.run_postlayout(completion_runner)
        for identifier in POST_ROUTE_REQUIRED_FILES:
            result = copy.deepcopy(run['checks'])
            result['artifacts'] = [entry for entry in result['artifacts'] if entry['id'] != identifier]
            with self.subTest(artifact=identifier), self.assertRaises(DomainError) as error:
                validate_artifact_manifest(result, True)
            self.assertEqual(error.exception.code, 'postlayout_artifact_missing')
        result = copy.deepcopy(run['checks'])
        result['artifacts'][0]['sha256'] = '0' * 64
        with self.assertRaises(DomainError) as error:
            validate_artifact_manifest(result, True)
        self.assertEqual(error.exception.code, 'postlayout_artifact_hash_conflict')

    def test_result_or_run_cannot_switch_verification_method(self):
        run = self.base.run_postlayout(completion_runner)
        for container in ('checks', 'run'):
            invalid = copy.deepcopy(run)
            (invalid['checks'] if container == 'checks' else invalid)['execution_scope'] = 'saved_event_diagnostic_review'
            with self.subTest(container=container), self.assertRaises(DomainError) as error:
                validate_postlayout_proof(invalid, existing.fixture_validator)
            self.assertEqual(error.exception.code, 'postlayout_method_conflict')

    def test_failed_electrical_result_is_retained_and_cannot_be_adopted(self):
        def failed(*args, **kwargs):
            result = completion_runner(*args, **kwargs)
            result['validation_status'] = 'Failed'
            result['checks']['electrical']['validation_status'] = 'Failed'
            return result
        run = self.base.run_postlayout(failed)
        self.assertEqual((run['execution_status'], run['validation_status'], run['review_status']),
                         ('Completed', 'Failed', 'Awaiting Review'))
        self.assertEqual(self.manager._state['reviews'], [])
        with self.assertRaises(DomainError):
            self.manager.review(run['id'], 'accepted', '')


class PostRouteDispatchTests(unittest.TestCase):
    def test_four_entrypoints_dispatch_only_explicit_mode_and_forward_arguments(self):
        configuration = {'execution_scope': POST_ROUTE_SCOPE, 'software_qa_fixture': True}
        result, lvs, drc, layout, cancel = (object() for _ in range(5))
        adapter = SimpleNamespace(**{name: Mock(return_value=name) for name in (
            'runtime_descriptor', 'source_inputs', 'run_postlayout', 'validate_postlayout_result')})
        with patch('hullcirq.postroute_tools', adapter, create=True):
            self.assertEqual(postlayout_tools.runtime_descriptor(configuration), 'runtime_descriptor')
            self.assertEqual(postlayout_tools.source_inputs(layout, configuration), 'source_inputs')
            self.assertEqual(postlayout_tools.run_postlayout(lvs, drc, layout, configuration, cancel), 'run_postlayout')
            self.assertEqual(postlayout_tools.validate_postlayout_result(result, lvs, drc, layout, configuration), 'validate_postlayout_result')
            adapter.run_postlayout.assert_called_once_with(lvs, drc, layout, configuration, cancel_event=cancel)
            adapter.validate_postlayout_result.assert_called_once_with(result, lvs, drc, layout, configuration)
            prior = adapter.runtime_descriptor.call_count
            unsupported = postlayout_tools.runtime_descriptor(None)
            self.assertFalse(unsupported['available'])
            self.assertFalse(unsupported['verification_supported'])
            self.assertEqual(adapter.runtime_descriptor.call_count, prior)


if __name__ == '__main__':
    unittest.main()
