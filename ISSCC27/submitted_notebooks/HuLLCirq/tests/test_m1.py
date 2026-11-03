"""Behavioral acceptance tests for M1 input validation and human review.

Only deterministic input checks are exercised here. These tests do not claim
LLM generation, RTL simulation, synthesis, or physical verification evidence.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))

from hullcirq.domain import DomainError, fingerprint, revision_hashes, validate_shape, validate_stage
from hullcirq.store import ProjectStore


def fixture():
    return json.loads((PROJECT / "examples" / "m1_two_nodes.json").read_text(encoding="utf-8"))


class DesignValidationTests(unittest.TestCase):
    def setUp(self):
        self.design = fixture()

    def test_example_satisfies_all_implemented_input_checks(self):
        validate_shape(self.design)
        for stage in ("global_settings", "graph_editor", "specifications"):
            with self.subTest(stage=stage):
                diagnostics = validate_stage(self.design, stage)
                self.assertFalse([item for item in diagnostics if item["severity"] == "error"], diagnostics)

    def test_unknown_schema_version_is_not_silently_imported(self):
        self.design["schema_version"] = "99.0"
        with self.assertRaises(DomainError):
            validate_shape(self.design)

    def test_nodes_must_be_an_array(self):
        self.design["nodes"] = {"producer": {}}
        with self.assertRaises(DomainError):
            validate_shape(self.design)

    def test_missing_required_fields_are_rejected(self):
        del self.design["nodes"]
        with self.assertRaises(DomainError):
            validate_shape(self.design)

    def graph_errors(self):
        validate_shape(self.design)  # Electrical faults must remain editable drafts.
        return [item for item in validate_stage(self.design, "graph_editor") if item["severity"] == "error"]

    def test_port_width_rejects_boolean_string_fraction_and_nonfinite_values(self):
        for width in (True, "32", 31.5, float("nan"), float("inf")):
            with self.subTest(width=width):
                design = fixture()
                design["nodes"][0]["ports"][0]["width"] = width
                with self.assertRaises(DomainError):
                    validate_shape(design)

    def test_nonfinite_layout_coordinate_cannot_be_saved_as_json(self):
        self.design["layout"]["nodes"]["node-producer"]["x"] = float("nan")
        with self.assertRaises(DomainError):
            validate_shape(self.design)

    def test_unrepresentable_clock_number_is_a_domain_error(self):
        for period in (10 ** 1000, -(10 ** 1000)):
            with self.subTest(sign=period > 0):
                design = fixture()
                design["settings"]["clock_period_ns"] = period
                with self.assertRaises(DomainError):
                    validate_shape(design)

    def test_connected_width_mismatch_is_reported_at_the_edge(self):
        self.design["nodes"][1]["ports"][0]["width"] = 16
        findings = self.graph_errors()
        self.assertTrue(any(item["code"] == "edge_width_mismatch" and
                            item.get("edge_id") == "edge-producer-consumer" for item in findings), findings)

    def test_dangling_port_reference_identifies_node_port_and_edge(self):
        self.design["edges"][0]["target"]["port_id"] = "deleted-port"
        findings = self.graph_errors()
        self.assertTrue(any(item["code"] == "missing_port" and
                            item.get("node_id") == "node-consumer" and
                            item.get("port_id") == "deleted-port" and
                            item.get("edge_id") == "edge-producer-consumer" for item in findings), findings)

    def test_wrong_direction_is_reported(self):
        edge = self.design["edges"][0]
        edge["source"], edge["target"] = edge["target"], edge["source"]
        self.assertTrue(any(item["code"] == "edge_direction" for item in self.graph_errors()))

    def test_signedness_and_clock_contracts_are_checked(self):
        consumer_port = self.design["nodes"][1]["ports"][0]
        consumer_port["signed"] = False
        consumer_port["clock"] = "other_clock"
        findings = self.graph_errors()
        self.assertTrue(any(item["code"] == "edge_signed_mismatch" for item in findings), findings)
        self.assertTrue(any(item.get("port_id") == consumer_port["id"] and
                            item["code"] == "clock_domain" for item in findings), findings)

    def test_hierarchy_cycle_is_detected_without_rejecting_the_draft_shape(self):
        producer, consumer = self.design["nodes"]
        producer["parent_id"] = consumer["id"]
        consumer["parent_id"] = producer["id"]
        self.assertTrue(any(item["code"] == "hierarchy_cycle" for item in self.graph_errors()))

    def test_duplicate_stable_ids_are_reported(self):
        duplicate = copy.deepcopy(self.design["nodes"][0])
        duplicate["name"] = "Duplicate"
        duplicate["module_name"] = "duplicate_module"
        self.design["nodes"].append(duplicate)
        self.assertTrue(any(item["code"] == "duplicate_id" for item in self.graph_errors()))

    def test_second_independent_source_cannot_drive_the_same_input(self):
        source = copy.deepcopy(self.design["nodes"][0])
        source.update(id="node-second-producer", name="Second Producer", module_name="m1_second_producer")
        source["ports"][0]["id"] = "port-second-producer-data"
        self.design["nodes"].append(source)
        self.design["layout"]["nodes"][source["id"]] = {"x": 100, "y": 400}
        second_edge = copy.deepcopy(self.design["edges"][0])
        second_edge["id"] = "edge-second-producer-consumer"
        second_edge["source"] = {"node_id": source["id"], "port_id": source["ports"][0]["id"]}
        self.design["edges"].append(second_edge)
        findings = self.graph_errors()
        self.assertTrue(any(item["code"] == "multiple_drivers" and
                            item.get("port_id") == "port-consumer-data" for item in findings), findings)

    def test_blank_behavior_and_test_expectations_are_incomplete_specifications(self):
        node = self.design["nodes"][0]
        node["behavior"] = "  "
        node["test_expectations"] = ""
        findings = validate_stage(self.design, "specifications")
        self.assertGreaterEqual(sum(item["severity"] == "error" and
                                    item.get("node_id") == node["id"] for item in findings), 2)

    def test_layout_changes_do_not_change_semantic_or_stage_fingerprints(self):
        moved = copy.deepcopy(self.design)
        moved["layout"]["nodes"]["node-producer"] = {"x": 222, "y": 333}
        moved["layout"]["viewport"]["zoom"] = 1.5
        self.assertEqual(revision_hashes(self.design)["semantic_hash"], revision_hashes(moved)["semantic_hash"])
        self.assertNotEqual(revision_hashes(self.design)["layout_hash"], revision_hashes(moved)["layout_hash"])
        for stage in ("global_settings", "graph_editor", "specifications"):
            self.assertEqual(fingerprint(self.design, stage), fingerprint(moved, stage))

    def test_behavior_change_requires_specification_review_without_rechecking_ports(self):
        changed = copy.deepcopy(self.design)
        changed["nodes"][0]["behavior"] += " Additional requirement: start from zero."
        self.assertNotEqual(revision_hashes(self.design)["semantic_hash"], revision_hashes(changed)["semantic_hash"])
        self.assertEqual(fingerprint(self.design, "global_settings"), fingerprint(changed, "global_settings"))
        self.assertEqual(fingerprint(self.design, "graph_editor"), fingerprint(changed, "graph_editor"))
        self.assertNotEqual(fingerprint(self.design, "specifications"), fingerprint(changed, "specifications"))


class ProjectPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "project"
        self.store = ProjectStore(self.path, fixture_path=PROJECT / "examples" / "m1_two_nodes.json")

    def envelope(self):
        return self.store.envelope()

    def stage(self, stage_id, envelope=None):
        return next(item for item in (envelope or self.envelope())["workflow"] if item["id"] == stage_id)

    def validate(self, stage_id):
        result = self.store.validate(stage_id, self.envelope()["revision"]["id"])
        return result["runs"][-1]

    def accept(self, stage_id):
        run = self.validate(stage_id)
        self.assertEqual(run["validation_status"], "Passed", run["diagnostics"])
        self.store.review(run["id"], "accepted", "Checked the M1 input diagnostics.")
        return run

    def accept_inputs(self):
        for stage in ("global_settings", "graph_editor", "specifications"):
            self.accept(stage)

    def save_change(self, edit):
        original = self.envelope()
        changed = copy.deepcopy(original["design"])
        edit(changed)
        return self.store.save(changed, original["revision"]["id"])

    def assert_corrupt_store_rejected_without_overwrite(self, edit):
        state = json.loads(self.store.state_path.read_text(encoding="utf-8"))
        edit(state)
        self.store.state_path.write_text(json.dumps(state, ensure_ascii=False) + "\n", encoding="utf-8")
        corrupted_bytes = self.store.state_path.read_bytes()
        with self.assertRaises(DomainError) as caught:
            ProjectStore(self.path)
        self.assertEqual(caught.exception.code, "invalid_store")
        self.assertEqual(self.store.state_path.read_bytes(), corrupted_bytes)

    def test_new_project_contains_no_fabricated_execution_or_human_review(self):
        envelope = self.envelope()
        self.assertEqual(envelope["runs"], [])
        self.assertEqual(envelope["reviews"], [])
        self.assertEqual(envelope["design"], fixture())

    def test_restart_preserves_initial_design_and_revision_identity(self):
        original = self.envelope()
        restarted = ProjectStore(self.path).envelope()
        self.assertEqual(restarted["design"], original["design"])
        self.assertEqual(restarted["revision"], original["revision"])

    def test_malformed_saved_run_is_rejected_at_startup_without_overwriting(self):
        self.assert_corrupt_store_rejected_without_overwrite(lambda state: state.update(runs=["malformed-run"]))

    def test_saved_design_revision_and_snapshot_must_agree_before_loading(self):
        self.assert_corrupt_store_rejected_without_overwrite(
            lambda state: state["design"]["nodes"][1]["ports"][0].update(width=16))

    def test_saved_run_hash_must_match_its_source_snapshot(self):
        self.validate("global_settings")
        self.assert_corrupt_store_rejected_without_overwrite(
            lambda state: state["runs"][0].update(input_hash="0" * 64))

    def test_validation_rejects_outdated_revision_without_recording_run(self):
        original = self.envelope()
        with self.assertRaises(DomainError) as caught:
            self.store.validate("global_settings", "not-the-current-revision")
        self.assertEqual(caught.exception.status, 409)
        self.assertEqual(self.envelope(), original)

    def test_save_rejects_outdated_revision_without_overwriting(self):
        original = self.envelope()
        with self.assertRaises(DomainError) as caught:
            self.store.save(copy.deepcopy(original["design"]), "not-the-current-revision")
        self.assertEqual(caught.exception.status, 409)
        self.assertEqual(self.envelope(), original)

    def test_invalid_import_leaves_current_design_and_evidence_unchanged(self):
        original = self.envelope()
        malformed = copy.deepcopy(original["design"])
        malformed["schema_version"] = "99.0"
        with self.assertRaises(DomainError):
            self.store.save(malformed, original["revision"]["id"])
        self.assertEqual(self.envelope(), original)

    def test_unrepresentable_number_cannot_overwrite_current_project(self):
        original = self.envelope()
        malformed = copy.deepcopy(original["design"])
        malformed["settings"]["clock_period_ns"] = -(10 ** 1000)
        with self.assertRaises(DomainError):
            self.store.save(malformed, original["revision"]["id"])
        self.assertEqual(self.envelope(), original)

    def test_unimplemented_stage_never_fabricates_success(self):
        original = self.envelope()
        with self.assertRaises(DomainError):
            self.store.validate("local_rtl_generation", original["revision"]["id"])
        self.assertEqual(self.envelope()["runs"], [])
        self.assertEqual(self.envelope()["reviews"], [])

    def test_unknown_review_does_not_create_an_accepted_result(self):
        with self.assertRaises(DomainError):
            self.store.review("unknown-run", "accepted", "Reviewed the evidence.")
        self.assertEqual(self.envelope()["runs"], [])
        self.assertEqual(self.envelope()["reviews"], [])

    def test_all_fourteen_stages_are_visible_but_future_stages_are_unsupported(self):
        stages = self.envelope()["workflow"]
        self.assertEqual(len(stages), 14)
        self.assertEqual([item["index"] for item in stages], list(range(1, 15)))
        for item in stages[3:]:
            self.assertFalse(item["implemented"])
            self.assertEqual(item["execution_status"], "Not Run")
            self.assertEqual(item["validation_status"], "Unsupported")
            self.assertNotEqual(item["review_status"], "Accepted")

    def test_passing_verification_awaits_a_separate_human_decision(self):
        run = self.validate("global_settings")
        self.assertEqual(run["execution_status"], "Completed")
        self.assertEqual(run["validation_status"], "Passed")
        self.assertEqual(run["review_status"], "Awaiting Review")
        self.assertEqual(self.envelope()["reviews"], [])
        self.assertEqual(self.stage("graph_editor")["execution_status"], "Not Run")
        result = self.store.review(run["id"], "accepted", "Reviewed settings.")
        self.assertEqual(self.stage("global_settings", result)["review_status"], "Accepted")
        self.assertEqual(self.stage("graph_editor", result)["execution_status"], "Not Run")

    def test_human_acceptance_requires_current_predecessor_acceptance(self):
        graph_run = self.validate("graph_editor")
        self.assertEqual(graph_run["validation_status"], "Passed")
        with self.assertRaises(DomainError) as caught:
            self.store.review(graph_run["id"], "accepted", "Review attempted before settings.")
        self.assertEqual(caught.exception.status, 409)
        self.assertEqual(self.envelope()["reviews"], [])
        self.accept("global_settings")
        self.store.review(graph_run["id"], "accepted", "Settings and graph checked.")
        specs_run = self.validate("specifications")
        self.store.review(specs_run["id"], "accepted", "Checked documented requirements.")
        self.assertTrue(all(item["review_status"] == "Accepted" for item in self.envelope()["workflow"][:3]))

    def test_failed_graph_check_cannot_be_accepted_and_has_linked_diagnostics(self):
        self.accept("global_settings")
        self.save_change(lambda design: design["nodes"][1]["ports"][0].update(width=16))
        run = self.validate("graph_editor")
        self.assertEqual(run["validation_status"], "Failed")
        self.assertTrue(any(item.get("edge_id") == "edge-producer-consumer" and
                            item["severity"] == "error" for item in run["diagnostics"]))
        with self.assertRaises(DomainError) as caught:
            self.store.review(run["id"], "accepted", "Cannot accept failed port checks.")
        self.assertEqual(caught.exception.status, 409)
        self.assertNotEqual(self.stage("graph_editor")["review_status"], "Accepted")

    def test_rerun_does_not_inherit_human_acceptance(self):
        old_run = self.accept("global_settings")
        new_run = self.validate("global_settings")
        self.assertNotEqual(new_run["id"], old_run["id"])
        self.assertEqual(self.stage("global_settings")["latest_run_id"], new_run["id"])
        self.assertEqual(self.stage("global_settings")["review_status"], "Awaiting Review")
        with self.assertRaises(DomainError) as caught:
            self.store.review(old_run["id"], "accepted", "Old rerun result.")
        self.assertEqual(caught.exception.status, 409)

    def test_changes_requested_and_return_to_stage_retain_human_notes(self):
        self.accept("global_settings")
        graph_run = self.validate("graph_editor")
        self.store.review(graph_run["id"], "changes_requested", "Explain the producer reset rule.", operator={"actor": "human"})
        self.store.review(graph_run["id"], "return_to_stage", "Recheck clock assumptions.", "global_settings", operator={"actor": "human"})
        result = self.envelope()
        self.assertEqual(self.stage("graph_editor", result)["review_status"], "Changes Requested")
        feedback = result["reviews"][-2:]
        self.assertEqual([item["decision"] for item in feedback], ["changes_requested", "return_to_stage"])
        self.assertEqual(feedback[0]["note"], "Explain the producer reset rule.")
        self.assertEqual(feedback[1]["target_stage"], "global_settings")
        self.assertTrue(all(item["actor"] == "human" and item["run_id"] == graph_run["id"] for item in feedback))
        restarted = ProjectStore(self.path).envelope()
        self.assertEqual(restarted["reviews"], result["reviews"])

    def test_requested_changes_require_feedback_and_return_must_be_to_an_earlier_stage(self):
        graph_run = self.validate("graph_editor")
        for decision, note, target in (("changes_requested", " ", None),
                                       ("return_to_stage", " ", "global_settings"),
                                       ("return_to_stage", "Wrong direction.", "specifications"),
                                       ("return_to_stage", "Same stage.", "graph_editor")):
            with self.subTest(decision=decision, target=target):
                with self.assertRaises(DomainError):
                    self.store.review(graph_run["id"], decision, note, target)
        self.assertEqual(self.envelope()["reviews"], [])

    def test_save_reload_keeps_ids_ports_behavior_connections_hierarchy_and_layout(self):
        def edit(design):
            design["nodes"][1]["parent_id"] = design["nodes"][0]["id"]
            design["nodes"][0]["behavior"] += " Updated input statement."
            design["layout"]["nodes"]["node-consumer"] = {"x": 700, "y": 280}
        original = self.envelope()
        saved = self.save_change(edit)
        self.assertNotEqual(saved["revision"]["id"], original["revision"]["id"])
        restarted = ProjectStore(self.path).envelope()
        self.assertEqual(restarted["design"], saved["design"])
        self.assertEqual(restarted["revision"], saved["revision"])
        self.assertEqual(restarted["design"]["edges"], original["design"]["edges"])
        self.assertEqual(restarted["design"]["nodes"][0]["ports"], original["design"]["nodes"][0]["ports"])
        self.assertEqual([node["id"] for node in restarted["design"]["nodes"]],
                         [node["id"] for node in original["design"]["nodes"]])

    def test_position_only_save_retains_accepted_current_results_and_old_source_snapshot(self):
        self.accept_inputs()
        original = self.envelope()
        moved = self.save_change(lambda design: design["layout"]["nodes"]["node-producer"].update(x=333, y=444))
        self.assertEqual(moved["revision"]["semantic_hash"], original["revision"]["semantic_hash"])
        self.assertNotEqual(moved["revision"]["layout_hash"], original["revision"]["layout_hash"])
        self.assertNotEqual(moved["revision"]["id"], original["revision"]["id"])
        self.assertEqual(moved["reviews"], original["reviews"])
        self.assertEqual(moved["runs"], original["runs"])
        self.assertTrue(all(item["freshness"] == "Current" and item["review_status"] == "Accepted"
                            for item in moved["workflow"][:3]))
        old_revision = original["revision"]["id"]
        self.assertEqual(self.store.snapshot(old_revision), original["design"])
        self.assertEqual(self.store.snapshot(moved["revision"]["id"]), moved["design"])

    def test_browser_numeric_roundtrip_and_layout_save_preserve_semantic_evidence_and_acceptance(self):
        self.accept_inputs()
        original = self.envelope()
        browser_design = copy.deepcopy(original["design"])
        self.assertEqual(browser_design["settings"]["clock_period_ns"], 50.0)
        # JSON.stringify converts the fixture's 50.0 to 50 without a semantic edit.
        browser_design["settings"]["clock_period_ns"] = 50
        browser_design["layout"]["nodes"]["node-producer"]["x"] += 25
        self.assertEqual(revision_hashes(browser_design)["semantic_hash"], original["revision"]["semantic_hash"])
        for stage in ("global_settings", "graph_editor", "specifications"):
            self.assertEqual(fingerprint(browser_design, stage), fingerprint(original["design"], stage))
        saved = self.store.save(browser_design, original["revision"]["id"])
        self.assertNotEqual(saved["revision"]["id"], original["revision"]["id"])
        self.assertNotEqual(saved["revision"]["layout_hash"], original["revision"]["layout_hash"])
        self.assertEqual(saved["revision"]["semantic_hash"], original["revision"]["semantic_hash"])
        for stage in ("global_settings", "graph_editor", "specifications"):
            self.assertEqual(self.stage(stage, saved)["freshness"], "Current")
            self.assertEqual(self.stage(stage, saved)["review_status"], "Accepted")
        self.assertEqual(saved["reviews"], original["reviews"])

    def test_behavior_edit_stales_specs_but_keeps_graph_and_settings_current(self):
        self.accept_inputs()
        original = self.envelope()
        changed = self.save_change(lambda design: design["nodes"][0].update(behavior="Start at zero after reset."))
        self.assertEqual(self.stage("global_settings", changed)["freshness"], "Current")
        self.assertEqual(self.stage("graph_editor", changed)["freshness"], "Current")
        self.assertEqual(self.stage("specifications", changed)["freshness"], "Stale")
        specs_run = original["runs"][-1]
        with self.assertRaises(DomainError) as caught:
            self.store.review(specs_run["id"], "accepted", "Outdated behavior cannot be accepted.")
        self.assertEqual(caught.exception.status, 409)
        self.assertEqual(self.envelope()["reviews"], original["reviews"])
        restarted = ProjectStore(self.path)
        self.assertEqual(restarted.envelope()["runs"], changed["runs"])
        self.assertEqual(restarted.snapshot(specs_run["source_snapshot_id"]), original["design"])
        self.assertEqual(changed["runs"][-1]["diagnostics"], specs_run["diagnostics"])
        self.assertEqual(changed["runs"][-1]["artifacts"], specs_run["artifacts"])

    def test_restoring_prior_semantic_inputs_reuses_evidence_but_requires_new_human_acceptance(self):
        self.accept_inputs()
        original = self.envelope()
        original_spec_run = original["runs"][-1]
        changed = self.save_change(lambda design: design["nodes"][0].update(behavior="A different proposed requirement."))
        self.assertEqual(self.stage("specifications", changed)["freshness"], "Stale")
        restored = self.store.save(copy.deepcopy(original["design"]), changed["revision"]["id"])
        self.assertNotEqual(restored["revision"]["id"], original["revision"]["id"])
        spec_status = self.stage("specifications", restored)
        self.assertEqual(spec_status["freshness"], "Current")
        self.assertEqual(spec_status["validation_status"], "Passed")
        self.assertEqual(spec_status["latest_run_id"], original_spec_run["id"])
        self.assertEqual(spec_status["review_status"], "Awaiting Review")
        self.assertEqual(restored["reviews"], original["reviews"])
        self.assertEqual(len(restored["runs"]), len(original["runs"]))
        self.assertEqual(self.store.snapshot(original_spec_run["source_snapshot_id"]), original["design"])
        restarted = ProjectStore(self.path)
        self.assertEqual(self.stage("specifications", restarted.envelope())["review_status"], "Awaiting Review")
        reviewed = restarted.review(original_spec_run["id"], "accepted", "Rechecked the restored requirement and its saved evidence.")
        self.assertEqual(self.stage("specifications", reviewed)["review_status"], "Accepted")
        self.assertEqual(reviewed["reviews"][-1]["note"], "Rechecked the restored requirement and its saved evidence.")

    def test_port_change_stales_graph_and_specs_without_deleting_prior_evidence(self):
        self.accept_inputs()
        original = self.envelope()
        changed = self.save_change(lambda design: design["nodes"][1]["ports"][0].update(width=16))
        self.assertEqual(self.stage("global_settings", changed)["freshness"], "Current")
        self.assertEqual(self.stage("graph_editor", changed)["freshness"], "Stale")
        self.assertEqual(self.stage("specifications", changed)["freshness"], "Stale")
        self.assertEqual(len(changed["runs"]), len(original["runs"]))
        self.assertEqual(changed["reviews"], original["reviews"])
        self.assertEqual(self.store.snapshot(original["revision"]["id"]), original["design"])
        with self.assertRaises(DomainError):
            self.store.review(original["runs"][1]["id"], "accepted", "Cannot reuse older port contract.")

    def test_importing_different_project_identity_cannot_reuse_prior_acceptance(self):
        self.accept_inputs()
        original = self.envelope()
        changed = self.save_change(lambda design: design["project"].update(id="a-different-project"))
        for stage in ("global_settings", "graph_editor", "specifications"):
            self.assertEqual(self.stage(stage, changed)["freshness"], "Stale")
            old_run = next(item for item in original["runs"] if item["stage_id"] == stage)
            with self.assertRaises(DomainError):
                self.store.review(old_run["id"], "accepted", "Prior project evidence cannot be reused.")
        self.assertEqual(changed["reviews"], original["reviews"])

    def test_two_editors_cannot_overwrite_a_newer_saved_revision(self):
        original = self.envelope()
        editor_a = copy.deepcopy(original["design"])
        editor_b = copy.deepcopy(original["design"])
        editor_a["nodes"][0]["behavior"] += " Saved by editor A."
        editor_b["nodes"][0]["behavior"] += " Saved by editor B."
        first = self.store.save(editor_a, original["revision"]["id"])
        with self.assertRaises(DomainError) as caught:
            self.store.save(editor_b, original["revision"]["id"])
        self.assertEqual(caught.exception.status, 409)
        self.assertEqual(self.envelope(), first)
        self.assertEqual(ProjectStore(self.path).envelope()["design"], editor_a)

    def test_envelope_edits_do_not_mutate_the_saved_project(self):
        original = self.envelope()
        local_copy = self.envelope()
        local_copy["design"]["nodes"][0]["behavior"] = "Unsaved change."
        self.assertEqual(self.envelope(), original)


if __name__ == "__main__":
    unittest.main()
