"""Display evidence and comparison limits; isolated sources, no tools or model."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from hullcirq.repair_guidance import build_repair_guidance
from hullcirq.repair_explanation import build_repair_explanation


class RepairExplanationTests(unittest.TestCase):
    def setUp(self):
        self.rtl = "module example(input clk, input rst);\nreg [7:0] bank [0:1];\nalways @(posedge clk) if (rst) begin\n bank <= 8'd0;\nend\nendmodule\n"
        self.design = {'nodes': [{'id': 'node', 'behavior': 'Reset retains storage bytes.', 'ports': []}], 'edges': [], 'settings': {'reset_name': 'rst'}}
        self.parent = {'id': 'parent', 'node_id': 'node', 'revision_id': 'revision', 'operation': 'generate', 'rtl': self.rtl}
        self.job = {**self.parent, 'id': 'candidate', 'operation': 'repair', 'base_job_id': 'parent', 'instruction': 'Remove unsupported whole-array reset writes.'}
        self.prior = {'id': 'prior-run', 'node_id': 'node', 'candidate_id': 'parent', 'stage_id': 'local_synthesis', 'input_hash': 'input', 'execution_status': 'Completed', 'validation_status': 'Failed', 'tool_configuration': {'kind': 'generic'}, 'checks': {'executed': True, 'stderr': 'candidate.v:4: ERROR: Invalid array access.', 'stdout': ''}}
        self.run = {**copy.deepcopy(self.prior), 'id': 'current-run', 'candidate_id': 'candidate'}

    def explain(self):
        jobs, runs = [self.parent, self.job], [self.prior, self.run]
        guidance = build_repair_guidance(self.design, self.run, self.job, jobs, runs)
        before = copy.deepcopy([guidance, jobs, runs])
        explanation = build_repair_explanation(guidance, self.run, self.job, jobs, runs)
        self.assertEqual([guidance, jobs, runs], before)
        return explanation

    def test_identical_rtl_is_distinct_from_same_error_and_includes_unapplied_instruction(self):
        result = self.explain()
        self.assertTrue(result['comparison']['rtl_identical'])
        self.assertIn('Requested source changes were not applied', result['comparison']['explanation'])
        self.assertEqual(result['previous_instruction']['text'], self.job['instruction'])
        self.assertEqual(result['previous_instruction']['diff'], '')
        self.assertEqual(result['issues'][0]['diagnostic']['line'], 4)
        self.assertEqual(result['issues'][0]['code_context'][2], {'line': 4, 'text': " bank <= 8'd0;", 'is_target': True})
        self.assertIn('Remove whole-array reset writes', result['issues'][0]['actions'][0])

    def test_changed_rtl_with_same_diagnostic_does_not_claim_identical_source(self):
        self.job['rtl'] = self.rtl.replace('module example', '// A real new comment\nmodule example')
        self.run['checks']['stderr'] = 'candidate.v:5: ERROR: Invalid array access.'
        result = self.explain()
        self.assertEqual(result['comparison']['outcome'], 'same_diagnostic')
        self.assertFalse(result['comparison']['rtl_identical'])
        self.assertEqual(len(result['diagnostic_comparison']['remaining']), 1)
        self.assertNotIn('not applied', result['comparison']['explanation'])

    def test_changed_diagnostics_are_not_proof_that_earlier_errors_were_fixed(self):
        self.job['rtl'] = self.rtl.replace("bank <= 8'd0", 'mystery <= 1')
        self.run['checks']['stderr'] = 'candidate.v:4: ERROR: unknown construct mystery.'
        result = self.explain()
        self.assertEqual(result['comparison']['outcome'], 'new_diagnostic')
        self.assertEqual(len(result['diagnostic_comparison']['not_reported']), 1)
        self.assertEqual(len(result['diagnostic_comparison']['newly_reported']), 1)
        self.assertIn('does not mean resolved', result['diagnostic_comparison']['limits'])
        self.assertNotIn('resolved', result['diagnostic_comparison'])

    def test_unknown_cause_and_missing_anchor_do_not_invent_actions_or_locations(self):
        self.run['checks']['stderr'] = 'ERROR: unexplained failure'
        result = self.explain()
        issue = result['issues'][0]
        self.assertEqual(issue['confidence'], 'unknown')
        self.assertEqual(issue['actions'], [])
        self.assertEqual(issue['code_context'], [])
        self.assertIn('No source-backed cause', issue['explanation'])

    def test_tool_changes_disable_baseline_comparison(self):
        self.run['tool_configuration'] = {'kind': 'different-tool'}
        result = self.explain()
        self.assertEqual(result['comparison']['outcome'], 'not_comparable')
        self.assertIsNone(result['comparison']['rtl_identical'])
        self.assertEqual(result['diagnostic_comparison']['remaining'], [])

    def test_context_contains_actual_comments_without_interpreting_source(self):
        self.job['rtl'] = self.parent['rtl'] = self.rtl.replace(' bank <=', ' // <script>untrusted()</script>\n bank <=')
        self.run['checks']['stderr'] = self.prior['checks']['stderr'] = 'candidate.v:5: ERROR: Invalid array access.'
        result = self.explain()
        self.assertIn('<script>untrusted()</script>', result['issues'][0]['code_context'][1]['text'])
        self.assertEqual(result['source']['candidate_id'], 'candidate')
        self.assertEqual(result['comparison']['previous_rtl_url'], '/api/generation/jobs/parent')

    def test_final_check_driver_target_keeps_qualified_actions_without_inventing_error_line(self):
        self.job['rtl'] = self.parent['rtl'] = "module example(input clk, output busy);\nalways @(posedge clk) busy <= 1'b0;\nassign busy = 1'b1;\nendmodule\n"
        # Use separate-line procedural write as required by the existing narrow
        # lexical driver rule; this is display QA rather than a circuit run.
        self.job['rtl'] = self.parent['rtl'] = self.job['rtl'].replace("always @(posedge clk) busy", "always @(posedge clk)\n busy")
        self.run['checks']['stderr'] = self.prior['checks']['stderr'] = 'Warning: multiple conflicting drivers for example.busy:'
        result = self.explain()
        self.assertIsNone(result['issues'][0]['diagnostic']['line'])
        self.assertEqual(result['issues'][0]['code_context'], [])
        self.assertEqual(result['issues'][0]['confidence'], 'confirmed')
        self.assertIn('Use exactly one output driver', result['issues'][0]['actions'][0])
        self.assertEqual([row['line'] for row in result['issues'][0]['related_locations']], [3, 4])

    def test_reviewed_model_cause_stays_hypothesis_instead_of_missing_analysis_message(self):
        jobs, runs = [self.parent, self.job], [self.prior, self.run]
        guidance = build_repair_guidance(self.design, self.run, self.job, jobs, runs)
        guidance['changes'] = [{'rule_id': 'model_assisted_analysis_v1', 'confidence': 'hypothesis', 'cause': 'An analyzed candidate cause.', 'facts': [], 'locations': [{'line': 4}], 'actions': ['A proposed edit.'], 'preserve': [], 'assumptions': ['Unverified.'], 'expected_result': 'Tool should parse the changed source.'}]
        guidance['analysis_reviewed'] = True
        result = build_repair_explanation(guidance, self.run, self.job, jobs, runs)
        issue = result['issues'][0]
        self.assertEqual(issue['confidence'], 'hypothesis')
        self.assertIn('Model-proposed cause (not validated): An analyzed candidate cause.', issue['explanation'])
        self.assertNotIn('preview model-assisted', issue['explanation'])
        self.assertEqual(issue['expected_result'], ['Tool should parse the changed source.'])


if __name__ == '__main__':
    unittest.main()
