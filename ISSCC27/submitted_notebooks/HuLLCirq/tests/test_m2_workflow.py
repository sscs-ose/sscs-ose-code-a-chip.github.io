"""Node context, generated-candidate, and workflow acceptance tests for M2-A.

Fake transport and fixed RTL fixtures are software-development evidence only.
They do not establish local-model RTL generation or circuit behavior.
"""

from __future__ import annotations

import copy
from contextlib import nullcontext
from functools import partial
import http.client
import json
import os
from pathlib import Path
import sys
import subprocess
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))

from hullcirq.context import build_node_context, node_fingerprint
from hullcirq.domain import DomainError
from hullcirq.generation import GenerationManager
from hullcirq.rtl_checks import check_rtl, compare_rtl, extract_rtl
from hullcirq.server import make_server
from hullcirq.store import ProjectStore

from test_m2_provider import FakeChatServer, FIXTURE_ORIGIN, FIXTURE_RTL, profile, sse_events


def fixture():
    return json.loads((PROJECT / "examples" / "m1_two_nodes.json").read_text(encoding="utf-8"))


class NodeContextTests(unittest.TestCase):
    def setUp(self):
        self.design = fixture()
        self.node_id = "node-producer"

    def test_context_contains_target_and_incident_edge_but_no_peer_private_behavior(self):
        self.design["nodes"][0]["behavior"] = "OWN_REQUIRED_BEHAVIOR"
        self.design["nodes"][1]["behavior"] = "PRIVATE_PEER_BEHAVIOR_EXCLUDED"
        self.design["nodes"][1]["test_expectations"] = "PRIVATE_PEER_TESTS_EXCLUDED"
        self.design["edges"][0]["behavior"] = "INCIDENT_EDGE_TRANSFER_RULE"
        preview = build_node_context(self.design, "revision-fixture", self.node_id)
        serialized = json.dumps(preview, ensure_ascii=False)
        self.assertIn("OWN_REQUIRED_BEHAVIOR", serialized)
        self.assertIn("INCIDENT_EDGE_TRANSFER_RULE", serialized)
        self.assertIn("port-consumer-data", serialized)
        self.assertNotIn("PRIVATE_PEER_BEHAVIOR_EXCLUDED", serialized)
        self.assertNotIn("PRIVATE_PEER_TESTS_EXCLUDED", serialized)
        self.assertEqual(preview["node_id"], self.node_id)
        self.assertEqual(preview["revision_id"], "revision-fixture")
        self.assertEqual(preview["node_input_hash"], node_fingerprint(self.design, self.node_id))

    def test_unrelated_node_and_unreferenced_peer_port_do_not_leak_into_context(self):
        unrelated = copy.deepcopy(self.design["nodes"][1])
        unrelated.update(id="node-unrelated", name="Unrelated", module_name="m1_unrelated",
                         behavior="UNRELATED_PRIVATE_BEHAVIOR", test_expectations="UNRELATED_PRIVATE_TESTS")
        unrelated["ports"][0]["id"] = "port-unrelated"
        self.design["nodes"].append(unrelated)
        unused_port = copy.deepcopy(self.design["nodes"][1]["ports"][0])
        unused_port.update(id="peer-unreferenced-port", name="unused_peer_input")
        self.design["nodes"][1]["ports"].append(unused_port)
        serialized = json.dumps(build_node_context(self.design, "revision-fixture", self.node_id))
        self.assertNotIn("UNRELATED_PRIVATE_BEHAVIOR", serialized)
        self.assertNotIn("UNRELATED_PRIVATE_TESTS", serialized)
        self.assertNotIn("node-unrelated", serialized)
        self.assertNotIn("peer-unreferenced-port", serialized)

    def test_node_fingerprint_ignores_layout_and_peer_private_specification_edits(self):
        original = node_fingerprint(self.design, self.node_id)
        changed = copy.deepcopy(self.design)
        changed["layout"]["nodes"][self.node_id]["x"] += 100
        changed["nodes"][1]["behavior"] = "Private behavior change."
        changed["nodes"][1]["test_expectations"] = "Private test change."
        self.assertEqual(node_fingerprint(changed, self.node_id), original)

    def test_node_fingerprint_ignores_unrelated_node_changes(self):
        unrelated = copy.deepcopy(self.design["nodes"][1])
        unrelated.update(id="unrelated", name="Unrelated", module_name="unrelated")
        unrelated["ports"][0]["id"] = "unrelated-port"
        original = node_fingerprint(self.design, self.node_id)
        self.design["nodes"].append(unrelated)
        self.assertEqual(node_fingerprint(self.design, self.node_id), original)
        self.design["nodes"][-1]["behavior"] = "Changed unrelated internal requirement."
        self.assertEqual(node_fingerprint(self.design, self.node_id), original)

    def test_adjacent_boundary_change_invalidates_local_node_input(self):
        original = node_fingerprint(self.design, self.node_id)
        self.design["nodes"][1]["ports"][0]["width"] = 16
        self.assertNotEqual(node_fingerprint(self.design, self.node_id), original)

    def test_target_behavior_and_incident_transfer_rule_change_node_input(self):
        for change in (lambda design: design["nodes"][0].update(behavior="A changed local requirement."),
                       lambda design: design["edges"][0].update(behavior="A changed transfer contract.")):
            changed = copy.deepcopy(self.design)
            change(changed)
            self.assertNotEqual(node_fingerprint(changed, self.node_id), node_fingerprint(self.design, self.node_id))

    def test_equivalent_json_numbers_do_not_stale_a_node(self):
        original = node_fingerprint(self.design, self.node_id)
        self.design["settings"]["clock_period_ns"] = 50
        self.assertEqual(node_fingerprint(self.design, self.node_id), original)

    def test_valid_ready_logical_port_expands_to_explicit_physical_contract(self):
        preview = build_node_context(self.design, "revision-fixture", self.node_id)
        ports = {port["name"]: port for port in preview["interface"]["ports"]}
        self.assertEqual(set(ports), {"clk", "rst", "data_out", "data_out_valid", "data_out_ready"})
        self.assertEqual((ports["data_out"]["direction"], ports["data_out"]["width"], ports["data_out"]["signed"]),
                         ("output", 32, True))
        self.assertEqual((ports["data_out_valid"]["direction"], ports["data_out_valid"]["width"]), ("output", 1))
        self.assertEqual((ports["data_out_ready"]["direction"], ports["data_out_ready"]["width"]), ("input", 1))

    def test_current_prompt_carries_a_fixed_header_matching_the_physical_contract(self):
        preview = build_node_context(self.design, "revision-fixture", self.node_id)
        self.assertEqual(preview["prompt_template_version"], "node-verilog-2005-v10")
        header = preview["requested_module_header"]
        self.assertIn("output wire signed [31:0] data_out", header)
        self.assertIn("output wire data_out_valid", header)
        self.assertIn("input wire data_out_ready", header)
        user_message = preview["messages"][-1]["content"]
        payload, _ = json.JSONDecoder().raw_decode(user_message)
        self.assertNotIn("required_module_header", payload)
        self.assertEqual(preview["messages"][1]["content"].count(header), 1)
        self.assertIn(header, user_message)
        checked = check_rtl(header + "endmodule\n", preview["interface"], "m1_producer", compiler=None)
        self.assertEqual(checked["checks"]["interface"]["validation_status"], "Passed")
        self.assertFalse(checked["checks"]["syntax"]["executed"])
        for version in ("node-verilog-2005-v1", "node-verilog-2005-v2", "node-verilog-2005-v3"):
            historical = build_node_context(self.design, "revision-fixture", self.node_id, template_version=version)
            self.assertEqual(historical["node_input_hash"], preview["node_input_hash"])
            self.assertNotIn("requested_module_header", historical)

    def test_unknown_node_is_rejected_before_any_provider_request(self):
        with self.assertRaises(DomainError):
            build_node_context(self.design, "revision-fixture", "node-does-not-exist")

    def test_repair_keeps_previous_rtl_and_selected_diagnostic_in_preview(self):
        preview = build_node_context(self.design, "revision-fixture", self.node_id,
                                     instruction="Repair this node only.", previous_rtl=FIXTURE_RTL,
                                     diagnostics=[{"code": "fixture_diagnostic", "message": "SELECTED_FIXTURE_DIAGNOSTIC"}])
        serialized = json.dumps(preview, ensure_ascii=False)
        self.assertIn("Repair this node only.", serialized)
        self.assertIn("SELECTED_FIXTURE_DIAGNOSTIC", serialized)
        self.assertIn("m1_producer", serialized)
        self.assertGreater(preview["estimated_input_tokens"], 0)
        self.assertTrue(preview["token_estimate_method"])


class RtlCandidateChecksTests(unittest.TestCase):
    def setUp(self):
        self.preview = build_node_context(fixture(), "revision-fixture", "node-producer")

    def check(self, rtl):
        return check_rtl(rtl, self.preview["interface"], "m1_producer", compiler=None)

    def test_fixed_rtl_is_development_fixture_and_one_fenced_block_is_extracted(self):
        self.assertEqual(FIXTURE_ORIGIN, "development_assistant")
        extracted = extract_rtl("Fixture explanation.\n```verilog\n" + FIXTURE_RTL + "```\n")
        self.assertEqual(extracted["rtl"].strip(), FIXTURE_RTL.strip())

    def test_ambiguous_multiple_rtl_blocks_are_not_silently_combined(self):
        extracted = extract_rtl("```verilog\n" + FIXTURE_RTL + "```\n```verilog\n" + FIXTURE_RTL + "```")
        self.assertFalse(extracted["rtl"])
        self.assertTrue(extracted["diagnostics"])

    def test_non_rtl_answer_does_not_create_a_candidate(self):
        extracted = extract_rtl("```python\nprint('This is not RTL')\n```")
        self.assertFalse(extracted["rtl"])
        self.assertTrue(extracted["diagnostics"])

    def test_missing_compiler_never_reports_passed_syntax_or_acceptability(self):
        checked = self.check(FIXTURE_RTL)
        self.assertEqual(checked["validation_status"], "Unsupported")
        self.assertTrue(checked["diagnostics"])

    def test_changed_data_width_fails_declared_physical_interface(self):
        checked = self.check(FIXTURE_RTL.replace("[31:0]", "[15:0]"))
        self.assertEqual(checked["validation_status"], "Failed")
        self.assertTrue(checked["diagnostics"])

    def test_wrong_module_and_missing_ready_port_fail_contract(self):
        for rtl in (FIXTURE_RTL.replace("m1_producer", "wrong_module"),
                    FIXTURE_RTL.replace("data_out_ready", "unexpected_ready")):
            checked = self.check(rtl)
            self.assertEqual(checked["validation_status"], "Failed")

    def test_include_and_file_system_task_are_rejected_without_compiler_execution(self):
        for rtl in ('`include "outside-file.v"\n' + FIXTURE_RTL,
                    FIXTURE_RTL.replace("always @(posedge clk)", 'initial $readmemh("outside.mem", data_out);\nalways @(posedge clk)')):
            checked = self.check(rtl)
            self.assertEqual(checked["validation_status"], "Failed")
            self.assertTrue(checked["diagnostics"])

    def test_diff_identifies_actual_candidate_change(self):
        changed = FIXTURE_RTL.replace("data_out + 32'sd1", "data_out + 32'sd2")
        diff = compare_rtl(FIXTURE_RTL, changed)
        self.assertIn("data_out + 32'sd1", diff)
        self.assertIn("data_out + 32'sd2", diff)

    def test_wsl_cleanup_warning_preserves_check_result_and_uses_persistent_cwd(self):
        # Simulate the process result and delayed Windows cleanup, without
        # claiming that this fixed development RTL fixture was compiled here.
        with tempfile.TemporaryDirectory() as temporary:
            persistent = Path(temporary)
            retained = persistent / "retained-candidate"
            retained.mkdir()
            compiler = {"kind": "wsl", "distribution": "Ubuntu", "executable": "/usr/bin/iverilog",
                        "working_directory": str(persistent)}
            outcome = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
            with patch("hullcirq.rtl_checks.tempfile.TemporaryDirectory",
                       return_value=nullcontext(str(retained))) as candidate_directory, \
                    patch("hullcirq.rtl_checks.subprocess.run", return_value=outcome) as run:
                checked = check_rtl(FIXTURE_RTL, self.preview["interface"], "m1_producer", compiler)
            self.assertTrue(candidate_directory.call_args.kwargs["ignore_cleanup_errors"])
            self.assertEqual(checked["validation_status"], "Passed")
            syntax = checked["checks"]["syntax"]
            self.assertEqual(syntax["validation_status"], "Passed")
            self.assertTrue(syntax["executed"])
            self.assertEqual(syntax["exit_code"], 0)
            self.assertEqual(syntax["cleanup_status"], "Incomplete")
            self.assertEqual(syntax["cleanup_directory"], str(retained))
            cleanup_warning = next(item for item in checked["diagnostics"]
                                   if item["code"] == "syntax_cleanup_incomplete")
            self.assertEqual(cleanup_warning["severity"], "warning")
            self.assertEqual(run.call_args.kwargs["cwd"], str(persistent))
            command = run.call_args.args[0]
            expected_cwd = "/mnt/" + persistent.drive[0].lower() + "/" + persistent.as_posix()[3:]
            self.assertEqual(command[command.index("--cd") + 1], expected_cwd)
            self.assertNotEqual(run.call_args.kwargs["cwd"], str(retained))
            self.assertEqual((retained / "candidate.v").read_text(encoding="utf-8"), FIXTURE_RTL)


class GenerationWorkflowTests(unittest.TestCase):
    """Real store/worker/HTTP with an explicitly simulated syntax-check result.

    Candidate acceptance here tests human-review bookkeeping. The checker stub
    is not compilation evidence and the HTTP responder is not a local model.
    """

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "project"
        self.store = ProjectStore(self.path, PROJECT / "examples" / "m1_two_nodes.json")
        self.manager = GenerationManager(self.store, compiler=None)
        self.addCleanup(lambda: self.manager.close())

    def accept_inputs(self):
        for stage in ("global_settings", "graph_editor", "specifications"):
            revision_id = self.store.envelope()["revision"]["id"]
            run = self.store.validate(stage, revision_id)["runs"][-1]
            self.store.review(run["id"], "accepted", "Checked the fixture input contract.")

    def configure(self, server, **overrides):
        return self.manager.save_profile(profile(server.base_url, **overrides),
                                         self.manager.envelope()["llm"]["profile_revision_id"])

    def request(self, node_id="node-producer", operation="generate", base_job_id=None, instruction=""):
        revision_id = self.store.envelope()["revision"]["id"]
        preview = self.manager.preview(node_id, revision_id, operation, base_job_id, instruction)
        return {"node_id": node_id, "revision_id": revision_id, "operation": operation,
                "base_job_id": base_job_id, "instruction": instruction,
                "context_id": preview["context_id"], "profile_revision_id": preview["profile_revision_id"]}

    def start(self, **kwargs):
        result = self.manager.start(**self.request(**kwargs))
        return result["generation"]["latest_job_id"]

    def wait(self, job_id):
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            job = self.manager.job(job_id)
            if job["execution_status"] not in ("Queued", "Running") and job.get("finished_at"):
                return job
            time.sleep(0.01)
        self.fail("Fixture generation worker did not settle within five seconds.")

    def save_change(self, edit):
        before = self.store.envelope()
        design = copy.deepcopy(before["design"])
        edit(design)
        self.store.save(design, before["revision"]["id"])
        self.manager.observe_design()

    @staticmethod
    def simulated_pass_check(*args, **kwargs):
        return {"validation_status": "Passed", "diagnostics": [],
                "checks": {"syntax": {"validation_status": "Passed", "executed": True, "exit_code": 0,
                                      "scope": "simulated_test_checker_not_actual_compilation",
                                      "evidence": "simulated test checker only"},
                           "interface": {"validation_status": "Passed"},
                           "functional_verification": {"validation_status": "Not Run", "executed": False}}}

    def completed_fixture_history(self, accepted=False):
        self.accept_inputs()
        with FakeChatServer(sse_events("```verilog\n" + FIXTURE_RTL + "```")) as server, \
                patch("hullcirq.generation.check_rtl", self.simulated_pass_check):
            self.configure(server)
            job = self.wait(self.start())
            if accepted:
                self.manager.review(job["id"], "accepted", "Reviewed the explicitly simulated-checker fixture.")
        self.manager.close()
        return json.loads(self.manager.path.read_text(encoding="utf-8"))

    def assert_saved_history_rejected_without_overwrite(self, state):
        self.manager.path.write_text(json.dumps(state), encoding="utf-8")
        corrupted_bytes = self.manager.path.read_bytes()
        with self.assertRaises(DomainError) as caught:
            GenerationManager(self.store)
        self.assertEqual(caught.exception.code, "invalid_generation_store")
        self.assertEqual(self.manager.path.read_bytes(), corrupted_bytes)

    def test_generation_requires_explicitly_accepted_saved_inputs(self):
        with FakeChatServer(sse_events("```verilog\n" + FIXTURE_RTL + "```")) as server:
            self.configure(server)
            with self.assertRaises(DomainError):
                self.start()
            self.assertEqual(server.requests, [])
            self.assertEqual(self.manager.envelope()["generation"]["jobs"], [])

    def test_complete_candidate_keeps_frozen_request_and_waits_for_human_review(self):
        self.accept_inputs()
        with FakeChatServer(sse_events("```verilog\n" + FIXTURE_RTL + "```")) as server, \
                patch("hullcirq.generation.check_rtl", self.simulated_pass_check):
            self.configure(server)
            revision_id = self.store.envelope()["revision"]["id"]
            job = self.wait(self.start())
            self.assertEqual(job["execution_status"], "Completed", job)
            self.assertEqual(job["validation_status"], "Passed")
            self.assertEqual(job["review_status"], "Awaiting Review")
            self.assertEqual(job["revision_id"], revision_id)
            self.assertEqual(job["context"]["node_id"], "node-producer")
            self.assertEqual(job["rtl"].strip(), FIXTURE_RTL.strip())
            self.assertIn("```verilog", job["raw_content"])
            self.assertEqual(job["usage"]["total_tokens"], 20)
            self.assertTrue(job["events"])
            self.assertEqual([item["sequence"] for item in job["events"]], sorted(item["sequence"] for item in job["events"]))
            self.assertFalse(self.manager.envelope()["generation"]["all_nodes_accepted"])
            self.manager.review(job["id"], "accepted", "Reviewed the simulated-checker fixture proposal.")
            self.assertEqual(self.manager.job(job["id"])["review_status"], "Accepted")
            self.assertFalse(self.manager.envelope()["generation"]["all_nodes_accepted"])

    def test_candidate_stays_running_and_blocks_review_until_checks_finish(self):
        self.accept_inputs()
        checking = threading.Event()
        release_checks = threading.Event()

        def blocked_fixture_check(*args, **kwargs):
            checking.set()
            if not release_checks.wait(3):
                raise AssertionError("The simulated candidate checker was not released.")
            return self.simulated_pass_check(*args, **kwargs)

        with FakeChatServer(sse_events("```verilog\n" + FIXTURE_RTL + "```")) as server, \
                patch("hullcirq.generation.check_rtl", blocked_fixture_check):
            self.configure(server)
            job_id = self.start()
            try:
                self.assertTrue(checking.wait(2), "The simulated candidate check did not start.")
                pending = self.manager.job(job_id)
                self.assertEqual(pending["execution_status"], "Running")
                self.assertIsNone(pending["finished_at"])
                self.assertEqual(pending["review_status"], "Awaiting Review")
                for decision in ("accepted", "changes_requested"):
                    with self.subTest(decision=decision), self.assertRaises(DomainError) as caught:
                        self.manager.review(job_id, decision, "Checks are still pending.")
                    self.assertIn(caught.exception.status, (403, 409))
                self.assertEqual(self.manager.job(job_id)["review_status"], "Awaiting Review")
            finally:
                release_checks.set()
            completed = self.wait(job_id)
            self.assertEqual(completed["execution_status"], "Completed")
            self.assertEqual(completed["validation_status"], "Passed")
            self.assertTrue(completed["finished_at"])
            self.assertEqual(completed["review_status"], "Awaiting Review")
            self.manager.review(job_id, "accepted", "Reviewed the completed simulated-checker fixture.")
            self.assertEqual(self.manager.job(job_id)["review_status"], "Accepted")

    def test_s04_interface_pass_does_not_require_s05_syntax_compiler(self):
        self.accept_inputs()
        with FakeChatServer(sse_events("```verilog\n" + FIXTURE_RTL + "```")) as server:
            self.configure(server)
            job = self.wait(self.start())
            self.assertEqual(job["execution_status"], "Completed")
            self.assertEqual(job["validation_status"], "Passed")
            self.assertEqual(job["stage_validation"]["scope"], "external_interface")
            self.assertEqual(job["stage_validation"]["syntax_stage_id"], "local_synthesis")
            self.assertEqual(job["stage_validation"]["behavioral_stage_id"], "local_netlist_simulation")
            self.manager.review(job["id"], "accepted", "Reviewed the S04 external interface; synthesis and behavior remain separate stages.")
            self.assertEqual(self.manager.job(job["id"])["review_status"], "Accepted")

    def test_stale_preview_and_revision_are_rejected_without_sending(self):
        self.accept_inputs()
        with FakeChatServer(sse_events("fixture")) as server:
            self.configure(server)
            request = self.request()
            broken = dict(request, context_id="0" * 64)
            with self.assertRaises(DomainError):
                self.manager.start(**broken)
            self.save_change(lambda design: design["layout"]["nodes"]["node-producer"].update(x=777))
            with self.assertRaises(DomainError) as caught:
                self.manager.start(**request)
            self.assertEqual(caught.exception.status, 409)
            self.assertEqual(server.requests, [])

    def test_active_duplicate_job_is_rejected_instead_of_resending(self):
        self.accept_inputs()
        with FakeChatServer(sse_events("```verilog\n" + FIXTURE_RTL + "```"), delay=0.3) as server:
            self.configure(server)
            request = self.request()
            job_id = self.manager.start(**request)["generation"]["latest_job_id"]
            with self.assertRaises(DomainError) as caught:
                self.manager.start(**request)
            self.assertEqual(caught.exception.status, 409)
            self.wait(job_id)
            self.assertEqual(len(server.requests), 1)

    def test_oversized_context_is_rejected_without_truncating_or_sending(self):
        self.accept_inputs()
        self.save_change(lambda design: design["nodes"][0].update(behavior="x" * 20000))
        self.accept_inputs()
        with FakeChatServer(sse_events("unused")) as server:
            self.configure(server)
            with self.assertRaises(DomainError):
                self.start()
            self.assertEqual(server.requests, [])
            self.assertEqual(self.manager.envelope()["generation"]["jobs"], [])

    def test_profile_changes_do_not_mutate_an_inflight_request_snapshot(self):
        self.accept_inputs()
        with FakeChatServer(sse_events("```verilog\n" + FIXTURE_RTL + "```"), delay=0.2) as server:
            first = self.configure(server)
            first_profile_id = first["llm"]["profile_revision_id"]
            job_id = self.start()
            self.configure(server, model="changed-profile-model", seed=202)
            job = self.wait(job_id)
            self.assertEqual(job["profile_revision_id"], first_profile_id)
            self.assertEqual(job["profile"]["model"], "fixture-model")
            self.assertEqual(job["parameters"]["seed"], 101)
            self.assertEqual(server.requests[0]["body"]["model"], "fixture-model")

    def test_layout_changes_preserve_candidate_but_boundary_change_stales_it(self):
        self.accept_inputs()
        with FakeChatServer(sse_events("```verilog\n" + FIXTURE_RTL + "```")) as server, \
                patch("hullcirq.generation.check_rtl", self.simulated_pass_check):
            self.configure(server)
            job = self.wait(self.start())
            self.manager.review(job["id"], "accepted", "Review fixture proposal.")
            self.save_change(lambda design: design["layout"]["nodes"]["node-producer"].update(x=321))
            self.assertEqual(self.manager.job(job["id"])["freshness"], "Current")
            self.assertEqual(self.manager.job(job["id"])["review_status"], "Accepted")
            self.save_change(lambda design: design["nodes"][1]["ports"][0].update(width=16))
            stale = self.manager.job(job["id"])
            self.assertEqual(stale["freshness"], "Stale")
            self.assertEqual(stale["rtl"], job["rtl"])
            with self.assertRaises(DomainError):
                self.manager.review(job["id"], "accepted", "Cannot adopt older adjacent boundary.")

    def test_restore_prior_node_input_keeps_proof_but_requires_new_review(self):
        self.accept_inputs()
        with FakeChatServer(sse_events("```verilog\n" + FIXTURE_RTL + "```")) as server, \
                patch("hullcirq.generation.check_rtl", self.simulated_pass_check):
            self.configure(server)
            job = self.wait(self.start())
            self.manager.review(job["id"], "accepted", "Original fixture proposal.")
            original_behavior = self.store.envelope()["design"]["nodes"][0]["behavior"]
            self.save_change(lambda design: design["nodes"][0].update(behavior="Changed node requirement."))
            self.save_change(lambda design: design["nodes"][0].update(behavior=original_behavior))
            restored = self.manager.job(job["id"])
            self.assertEqual(restored["freshness"], "Current")
            self.assertEqual(restored["validation_status"], "Passed")
            self.assertEqual(restored["review_status"], "Awaiting Review")
            self.assertEqual(restored["rtl"], job["rtl"])
            self.accept_inputs()
            self.manager.review(job["id"], "accepted", "Reviewed restored node intent again.")
            self.assertEqual(self.manager.job(job["id"])["review_status"], "Accepted")

    def test_human_change_request_and_return_reason_are_persisted(self):
        self.accept_inputs()
        with FakeChatServer(sse_events("```verilog\n" + FIXTURE_RTL + "```")) as server:
            self.configure(server)
            job = self.wait(self.start())
            self.manager.review(job["id"], "changes_requested", "Clarify reset semantics.")
            self.manager.review(job["id"], "return_to_stage", "Update the required behavior.", "specifications")
            self.assertEqual(self.manager.job(job["id"])["review_status"], "Changes Requested")
            self.manager.close()
            self.manager = GenerationManager(self.store)
            saved = self.manager.job(job["id"])
            self.assertEqual(saved["review_status"], "Changes Requested")
            self.assertIn("Update the required behavior.", (self.path / "generation.json").read_text(encoding="utf-8"))

    def test_failed_partial_response_is_saved_and_cannot_be_accepted(self):
        self.accept_inputs()
        with FakeChatServer(sse_events("partial fixture", finish_reason="length")) as server:
            self.configure(server)
            job = self.wait(self.start())
            self.assertEqual(job["execution_status"], "Failed")
            self.assertEqual(job["raw_content"], "partial fixture")
            self.assertTrue(job["error"])
            with self.assertRaises(DomainError):
                self.manager.review(job["id"], "accepted", "Cannot accept truncation.")
            self.manager.close()
            self.manager = GenerationManager(self.store)
            self.assertEqual(self.manager.job(job["id"])["raw_content"], "partial fixture")

    def test_repair_uses_same_node_base_and_shows_recorded_candidate_diff(self):
        self.accept_inputs()
        with FakeChatServer(sse_events("```verilog\n" + FIXTURE_RTL + "```")) as server, \
                patch("hullcirq.generation.check_rtl", self.simulated_pass_check):
            self.configure(server)
            original = self.wait(self.start())
            with self.assertRaises(DomainError):
                self.request("node-consumer", "repair", original["id"], "Repair another node.")
            changed = FIXTURE_RTL.replace("data_out + 32'sd1", "data_out + 32'sd2")
            server.payload = sse_events("```verilog\n" + changed + "```")
            repaired = self.wait(self.start(operation="repair", base_job_id=original["id"], instruction="Increment by two."))
            self.assertEqual(repaired["operation"], "repair")
            self.assertEqual(repaired["base_job_id"], original["id"])
            self.assertEqual(repaired["review_status"], "Awaiting Review")
            self.assertIn("data_out + 32'sd1", repaired["diff"])
            self.assertIn("data_out + 32'sd2", repaired["diff"])

    def test_restart_interrupts_recorded_active_job_without_resending(self):
        self.accept_inputs()
        with FakeChatServer(sse_events("```verilog\n" + FIXTURE_RTL + "```"), delay=0.3) as server:
            self.configure(server)
            job_id = self.start()
            active_state = (self.path / "generation.json").read_bytes()
            self.assertIn(self.manager.job(job_id)["execution_status"], ("Queued", "Running"))
            self.manager.close()
            self.wait(job_id)
            # Reproduce the persisted file a process would leave at crash time.
            (self.path / "generation.json").write_bytes(active_state)
            requests_before = len(server.requests)
            self.manager = GenerationManager(self.store)
            restored = self.manager.job(job_id)
            self.assertEqual(restored["execution_status"], "Interrupted")
            self.assertNotEqual(restored["review_status"], "Accepted")
            time.sleep(0.05)
            self.assertEqual(len(server.requests), requests_before)

    def test_older_prompt_history_survives_restart_and_still_requires_input_review(self):
        self.accept_inputs()
        older_jobs = []
        with FakeChatServer(sse_events("```verilog\n" + FIXTURE_RTL + "```")) as server, \
                patch("hullcirq.generation.check_rtl", self.simulated_pass_check):
            self.configure(server)
            for version in ("node-verilog-2005-v1", "node-verilog-2005-v2", "node-verilog-2005-v3"):
                def legacy_context(*args, **kwargs):
                    # Current preview explicitly passes template_version=None;
                    # select the declared historical renderer for this fixture.
                    kwargs["template_version"] = version
                    return build_node_context(*args, **kwargs)
                with patch("hullcirq.generation.build_node_context",
                           legacy_context):
                    older_job = self.wait(self.start())
                self.assertEqual(older_job["context"]["prompt_template_version"], version)
                self.assertEqual(older_job["review_status"], "Awaiting Review")
                older_jobs.append(older_job)
            # Peer-private changes require a new specification review without
            # changing this producer's local generation input or saved prompt.
            self.save_change(lambda design: design["nodes"][1].update(behavior="A changed private consumer requirement."))
            self.assertEqual(self.manager.job(older_job["id"])["freshness"], "Current")
        self.manager.close()
        saved_bytes = self.manager.path.read_bytes()
        self.manager = GenerationManager(self.store)
        self.assertEqual(self.manager.path.read_bytes(), saved_bytes)
        for older_job in older_jobs:
            restored = self.manager.job(older_job["id"])
            self.assertEqual(restored["context"], older_job["context"])
            self.assertEqual(restored["raw_content"], older_job["raw_content"])
            self.assertEqual(restored["rtl"], older_job["rtl"])
            self.assertEqual(restored["validation_status"], "Passed")
            self.assertEqual(restored["review_status"], "Awaiting Review")
        with self.assertRaises(DomainError) as caught:
            self.manager.review(older_job["id"], "accepted", "Input specifications still need review.")
        self.assertEqual(caught.exception.status, 409)
        self.accept_inputs()
        self.manager.review(older_job["id"], "accepted", "Reviewed the retained older-prompt fixture candidate.")
        self.assertEqual(self.manager.job(older_job["id"])["review_status"], "Accepted")

    def test_generation_state_does_not_replace_m1_saved_input_or_review_history(self):
        self.accept_inputs()
        original_bytes = self.store.state_path.read_bytes()
        with FakeChatServer(sse_events("```verilog\n" + FIXTURE_RTL + "```")) as server:
            self.configure(server)
            self.wait(self.start())
            self.assertEqual(self.store.state_path.read_bytes(), original_bytes)
            restarted_store = ProjectStore(self.path)
            self.assertEqual(restarted_store.envelope()["design"], self.store.envelope()["design"])
            self.assertEqual(restarted_store.envelope()["reviews"], self.store.envelope()["reviews"])

    def test_electrically_invalid_m1_draft_remains_loadable_with_generation_attached(self):
        self.save_change(lambda design: design["nodes"][0]["ports"][0].update(width=0))
        saved = self.store.envelope()
        self.assertEqual(saved["design"]["nodes"][0]["ports"][0]["width"], 0)
        generation = self.manager.envelope()
        self.assertEqual(generation["generation"]["jobs"], [])
        restarted_store = ProjectStore(self.path)
        restarted_manager = GenerationManager(restarted_store)
        self.addCleanup(restarted_manager.close)
        self.assertEqual(restarted_store.envelope()["design"], saved["design"])
        self.assertEqual(restarted_manager.envelope()["generation"]["jobs"], [])

    def test_inconsistent_generation_input_hash_is_rejected_at_restart_without_overwriting(self):
        self.accept_inputs()
        with FakeChatServer(sse_events("```verilog\n" + FIXTURE_RTL + "```")) as server:
            self.configure(server)
            self.wait(self.start())
        self.manager.close()
        path = self.path / "generation.json"
        state = json.loads(path.read_text(encoding="utf-8"))
        state["jobs"][0]["input_hash"] = "0" * 64
        path.write_text(json.dumps(state), encoding="utf-8")
        corrupted = path.read_bytes()
        with self.assertRaises(DomainError) as caught:
            GenerationManager(self.store)
        self.assertEqual(caught.exception.code, "invalid_generation_store")
        self.assertEqual(path.read_bytes(), corrupted)

    def test_failed_profile_persistence_preserves_disk_and_committed_in_memory_profile(self):
        before = self.manager.save_profile(profile(), None)
        original_bytes = self.manager.path.read_bytes()
        profile_revision_id = before["llm"]["profile_revision_id"]
        with patch("hullcirq.generation.os.replace", side_effect=OSError("Fixture replace failure.")):
            with self.assertRaises(OSError):
                self.manager.save_profile(profile(model="unsaved-model"), profile_revision_id)
        self.assertEqual(self.manager.path.read_bytes(), original_bytes)
        after = self.manager.envelope()
        self.assertEqual(after["llm"], before["llm"])
        self.assertEqual(after["generation"]["jobs"], before["generation"]["jobs"])
        self.assertEqual(after["generation"]["nodes"], before["generation"]["nodes"])
        restarted = GenerationManager(self.store)
        self.addCleanup(restarted.close)
        self.assertEqual(restarted.envelope()["llm"], before["llm"])

    def test_modified_raw_answer_or_rtl_is_rejected_without_overwriting_evidence(self):
        self.accept_inputs()
        with FakeChatServer(sse_events("```verilog\n" + FIXTURE_RTL + "```")) as server:
            self.configure(server)
            job = self.wait(self.start())
        self.manager.close()
        self.assertTrue(job["raw_content_sha256"])
        self.assertTrue(job["rtl_sha256"])
        clean_state = json.loads(self.manager.path.read_text(encoding="utf-8"))
        for field in ("raw_content", "rtl"):
            with self.subTest(field=field):
                modified = copy.deepcopy(clean_state)
                modified["jobs"][0][field] += "\n// Tampered fixture evidence.\n"
                self.manager.path.write_text(json.dumps(modified), encoding="utf-8")
                corrupted_bytes = self.manager.path.read_bytes()
                with self.assertRaises(DomainError) as caught:
                    GenerationManager(self.store)
                self.assertEqual(caught.exception.code, "invalid_generation_store")
                self.assertEqual(self.manager.path.read_bytes(), corrupted_bytes)

    def test_changed_saved_context_view_cannot_disagree_with_its_source_and_sent_prompt(self):
        self.accept_inputs()
        with FakeChatServer(sse_events("```verilog\n" + FIXTURE_RTL + "```")) as server:
            self.configure(server)
            self.wait(self.start())
        self.manager.close()
        state = json.loads(self.manager.path.read_text(encoding="utf-8"))
        state["jobs"][0]["context"]["context"]["node"]["behavior"] = "Tampered human-input view."
        self.manager.path.write_text(json.dumps(state), encoding="utf-8")
        corrupted_bytes = self.manager.path.read_bytes()
        with self.assertRaises(DomainError) as caught:
            GenerationManager(self.store)
        self.assertEqual(caught.exception.code, "invalid_generation_store")
        self.assertEqual(self.manager.path.read_bytes(), corrupted_bytes)

    def test_backend_credential_value_is_not_saved_in_generation_history(self):
        self.accept_inputs()
        fake_key = "fixture-only-bearer-secret"
        with FakeChatServer(sse_events("```verilog\n" + FIXTURE_RTL + "```")) as server, \
                patch.dict(os.environ, {"HULLCIRQ_TEST_KEY": fake_key}):
            self.configure(server, credential_env="HULLCIRQ_TEST_KEY")
            job = self.wait(self.start())
            self.assertEqual(job["execution_status"], "Completed")
            self.assertEqual(server.requests[0]["authorization"], "Bearer " + fake_key)
            self.assertNotIn(fake_key, self.manager.path.read_text(encoding="utf-8"))
            self.assertNotIn(fake_key, json.dumps(self.manager.envelope()))

    def test_accepted_candidate_requires_a_matching_human_review_record_at_restart(self):
        state = self.completed_fixture_history(accepted=True)
        self.assertEqual(state["jobs"][0]["review_status"], "Accepted")
        self.assertTrue(state["reviews"])
        state["reviews"] = []
        self.assert_saved_history_rejected_without_overwrite(state)

    def test_saved_origin_must_match_its_frozen_provider_location(self):
        state = self.completed_fixture_history()
        self.assertEqual(state["jobs"][0]["profile"]["execution_location"], "Local")
        state["jobs"][0]["origin"] = "remote_llm"
        self.assert_saved_history_rejected_without_overwrite(state)

    def test_nonobject_saved_context_is_a_domain_error_and_preserves_history(self):
        state = self.completed_fixture_history()
        state["jobs"][0]["context"] = "malformed context object"
        self.assert_saved_history_rejected_without_overwrite(state)

    def test_malformed_saved_job_identifier_or_checks_are_rejected_before_use(self):
        clean_state = self.completed_fixture_history()
        for field, value in (("id", 123), ("checks", [])):
            with self.subTest(field=field):
                state = copy.deepcopy(clean_state)
                state["jobs"][0][field] = value
                self.assert_saved_history_rejected_without_overwrite(state)


class GenerationHttpIntegrationTests(unittest.TestCase):
    def test_input_check_and_review_responses_keep_the_saved_provider_and_generation_subsections(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = ProjectStore(Path(temporary) / "project")
            server = make_server("127.0.0.1", 0, store)
            thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
            thread.start()

            def request(method, path, body=None):
                connection = http.client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=3)
                try:
                    raw = json.dumps(body).encode() if body is not None else None
                    headers = {"Content-Type": "application/json"} if body is not None else {}
                    connection.request(method, path, body=raw, headers=headers)
                    response = connection.getresponse()
                    return response.status, json.loads(response.read())
                finally:
                    connection.close()

            try:
                status, configured = request("POST", "/api/llm/profile", {
                    "profile": profile(), "expected_profile_revision_id": None})
                self.assertEqual(status, 200)
                profile_revision_id = configured["llm"]["profile_revision_id"]
                status, checked = request("POST", "/api/validate", {
                    "stage_id": "global_settings", "revision_id": configured["revision"]["id"]})
                self.assertEqual(status, 200)
                self.assertEqual(checked["llm"]["profile_revision_id"], profile_revision_id)
                self.assertTrue(checked["generation"]["implemented"])
                status, reviewed = request("POST", "/api/review", {
                    "run_id": checked["runs"][-1]["id"], "decision": "accepted", "note": "Checked settings."})
                self.assertEqual(status, 200)
                self.assertEqual(reviewed["llm"]["profile_revision_id"], profile_revision_id)
                self.assertEqual(reviewed["generation"]["jobs"], [])
                self.assertEqual(reviewed["workflow"][0]["review_status"], "Accepted")
            finally:
                server.generation.close()
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
