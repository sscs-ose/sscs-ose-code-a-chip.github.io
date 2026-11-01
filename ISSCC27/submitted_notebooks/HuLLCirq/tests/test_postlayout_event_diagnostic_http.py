"""Loopback software doubles for event diagnostic routes, never NPU evidence."""
import copy
import unittest
import test_postlayout_workflow_http as existing


EVENT_IDS = {'event-transcript', 'event-manifest', 'event-summary', 'event-audit-report',
    'conditional-path-report', 'native-delay-readback', 'native-delay-manifest', 'functional-provenance'}


class SavedEventDiagnosticHTTPTests(unittest.TestCase):
    setUp = existing.PostLayoutWorkflowHTTPTests.setUp
    stop = existing.PostLayoutWorkflowHTTPTests.stop
    request = existing.PostLayoutWorkflowHTTPTests.request
    json_request = existing.PostLayoutWorkflowHTTPTests.json_request

    def test_event_reports_keep_exact_bytes_and_fixed_routes(self):
        self.assertTrue(EVENT_IDS <= set(self.double.binary))
        for name in EVENT_IDS:
            with self.subTest(artifact=name):
                expected, mime = self.double.binary[name]
                status, raw, headers = self.request('/api/artifacts/postlayout-workflow/software-postlayout/' + name)
                self.assertEqual(status, 200)
                self.assertEqual(raw, expected)
                self.assertEqual(headers['Content-Type'], mime)
                self.assertEqual(int(headers['Content-Length']), len(expected))
                self.assertEqual(headers['Cache-Control'], 'no-store')
                self.assertEqual(headers['X-Content-Type-Options'], 'nosniff')
                self.assertEqual(self.request('/api/artifacts/postlayout-workflow/software-postlayout/' + name + '/extra')[0], 404)
        self.assertFalse(self.double.calls)

    def test_saved_event_scope_summary_and_unsupported_state_are_returned_without_execution(self):
        original = self.double.envelope
        self.double.visible = True
        self.double.record.update(execution_scope='saved_event_diagnostic_review', validation_status='Unsupported',
            checks={'executed': True, 'execution_started_by_this_review': False,
                'summary': {'software_qa_fixture': True, 'event_scope': 'SOFTWARE QA ONLY'}})
        def envelope():
            result = copy.deepcopy(original())
            result['postlayout_workflow'].update(execution_scope='saved_event_diagnostic_review', verification_supported=False)
            return result
        self.double.envelope = envelope
        status, _, result, _ = self.json_request('/api/project')
        self.assertEqual(status, 200)
        flow = result['postlayout_workflow']
        self.assertEqual(flow['execution_scope'], 'saved_event_diagnostic_review')
        self.assertFalse(flow['verification_supported'])
        self.assertIsNone(flow['accepted_run_id'])
        run = flow['runs'][0]
        self.assertEqual(run['validation_status'], 'Unsupported')
        self.assertFalse(run['checks']['execution_started_by_this_review'])
        self.assertEqual(run['checks']['summary']['event_scope'], 'SOFTWARE QA ONLY')
        self.assertFalse(self.double.calls)


if __name__ == '__main__': unittest.main()
