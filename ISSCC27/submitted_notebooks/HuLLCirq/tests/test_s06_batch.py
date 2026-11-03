"""Isolated scheduling QA: tool stubs are never actual circuit evidence."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))
from hullcirq.domain import DomainError
from hullcirq.readonly_view import SavedFiles, SavedManager
from hullcirq.store import ProjectStore
from hullcirq.verification import build_verification_plan, content_hash, object_hash
from hullcirq.workflow import WorkflowManager
from test_continuous_flow import original_design
from test_s05_batch import SoftwareCandidates

S05, S06 = "local_synthesis", "local_netlist_simulation"


class S06BatchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=PROJECT / ".work")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.calls = []
        self.make_sources()

    def make_sources(self, unsupported_second=False):
        if hasattr(self, "manager"):
            self.manager.close()
        design = original_design()
        second = copy.deepcopy(design["nodes"][0])
        second.update(id="node-mac-second", module_name="m2a_mac_second", name="Second MAC")
        for port in second["ports"]:
            port["id"] += "-second"
        if unsupported_second:
            second.pop("verification")
        design["nodes"] = [design["nodes"][0], second]
        design["edges"] = []
        design["layout"]["nodes"] = {node["id"]: {"x": index * 300, "y": 100} for index, node in enumerate(design["nodes"])}
        fixture = self.root / ("unsupported.json" if unsupported_second else "input.json")
        fixture.write_text(json.dumps(design), encoding="utf-8")
        self.store = ProjectStore(self.root / ("unsupported-project" if unsupported_second else "project"), fixture)
        for stage in ("global_settings", "graph_editor", "specifications"):
            run = self.store.validate(stage, self.store.envelope()["revision"]["id"])["runs"][-1]
            self.store.review(run["id"], "accepted", "Software fixture input.")
        self.store.set_review_policy("accept_on_pass", True, "Software scheduler QA only.")
        self.candidates = SoftwareCandidates(self.store)
        self.manager = WorkflowManager(self.store, self.candidates,
            compiler={"kind": "native", "executable": "iverilog"},
            synthesizer={"kind": "native", "executable": "yosys"})
        self.addCleanup(lambda: self.manager.close())
        with patch("hullcirq.workflow.synthesize_generic", self.synthesize):
            self.wait(self.start("s05-setup-request", S05)["id"])

    @staticmethod
    def synthesize(rtl, module, configuration, directory, cancelled):
        netlist = rtl + "// isolated software synthesis stub\n"
        return {"validation_status": "Passed", "executed": True, "exit_code": 0, "diagnostics": [],
                "netlist": netlist, "netlist_sha256": content_hash(netlist), "scope": "software_stub_no_eda"}

    def verify(self, netlist, plan, configuration, directory, cancelled, **options):
        self.assertIs(options.get("record_waveform"), True)
        self.calls.append({"netlist": netlist, "plan": copy.deepcopy(plan), "configuration": copy.deepcopy(configuration)})
        return {"validation_status": "Passed", "executed": True, "exit_code": 0, "diagnostics": [],
                "stdout": "software verification stub", "scope": "software_stub_no_simulation"}

    def start(self, request="s06-software-request", stage=S06):
        envelope = self.manager.start_batch(self.store.envelope()["revision"]["id"], request, stage_id=stage)
        return next(batch for batch in envelope["workflow_batches"] if batch["request_id"] == request)

    def wait(self, identifier):
        deadline = time.monotonic() + 6
        while time.monotonic() < deadline:
            batch = self.manager.batch(identifier)
            if batch["execution_status"] not in {"Queued", "Running"} and not self.manager.is_active():
                return batch
            time.sleep(.01)
        self.fail("Isolated software batch did not settle")

    def test_sequence_uses_exact_s05_netlists_and_original_saved_plans(self):
        originals = {node["id"]: build_verification_plan(self.store.envelope()["design"], node["id"])
                     for node in self.store.envelope()["design"]["nodes"]}
        with patch("hullcirq.workflow.verify_behavior", self.verify), patch("hullcirq.workflow.synthesize_generic", side_effect=AssertionError("S06 must never synthesize")):
            batch = self.wait(self.start()["id"])
        self.assertEqual(batch["stage_id"], S06)
        self.assertEqual(batch["accepted_node_count"], 2)
        self.assertEqual(batch["validation_status"], "Passed")
        self.assertEqual([item["status"] for item in batch["items"]], ["Passed", "Passed"])
        self.assertEqual(len(self.calls), 2)
        for item, call in zip(batch["items"], self.calls):
            prior = self.manager.run(item["prior_run_id"])
            run = self.manager.run(item["run_id"])
            self.assertEqual(call["netlist"], prior["netlist"])
            self.assertEqual(call["plan"], originals[item["node_id"]])
            self.assertEqual(item["verification_plan_sha256"], object_hash(call["plan"]))
            self.assertEqual(run["prior_run_id"], prior["id"])
            self.assertEqual(run["netlist_sha256"], prior["netlist_sha256"])
            self.assertEqual(run["candidate_id"], item["candidate_id"])

    def test_exact_accepted_s06_is_reused_without_tools(self):
        with patch("hullcirq.workflow.verify_behavior", self.verify):
            first = self.wait(self.start()["id"])
        with patch("hullcirq.workflow.verify_behavior", side_effect=AssertionError("Reuse cannot simulate")):
            second = self.wait(self.start("s06-second-request")["id"])
        self.assertEqual([item["status"] for item in second["items"]], ["Skipped", "Skipped"])
        self.assertEqual([item["run_id"] for item in first["items"]], [item["run_id"] for item in second["items"]])
        self.assertEqual(second["accepted_node_count"], 2)

    def test_new_s05_run_of_identical_rtl_requires_new_s06_lineage(self):
        with patch("hullcirq.workflow.verify_behavior", self.verify):
            old = self.wait(self.start()["id"])
        first = old["items"][0]
        with patch("hullcirq.workflow.synthesize_generic", self.synthesize):
            self.manager.start(S05, first["node_id"], first["candidate_id"], old["revision_id"])
            deadline = time.monotonic() + 5
            while self.manager.is_active() and time.monotonic() < deadline:
                time.sleep(.01)
        self.assertFalse(self.manager.batch(old["id"])["source_current"])
        self.assertEqual(self.manager.run(first["run_id"])["freshness"], "Stale")
        with patch("hullcirq.workflow.verify_behavior", self.verify):
            new = self.wait(self.start("s06-new-lineage")["id"])
        self.assertEqual([item["status"] for item in new["items"]], ["Passed", "Skipped"])
        self.assertNotEqual(new["items"][0]["prior_run_id"], first["prior_run_id"])
        self.assertEqual(len(self.calls), 3)

    def test_failure_keeps_other_success_and_explicit_retry_only_reruns_failure(self):
        def fail_first(*arguments, **options):
            result = self.verify(*arguments, **options)
            if len(self.calls) == 1:
                result.update(validation_status="Failed", exit_code=1,
                              diagnostics=[{"code": "software_mismatch", "severity": "error", "message": "fixture mismatch"}])
            return result
        with patch("hullcirq.workflow.verify_behavior", fail_first):
            batch = self.wait(self.start()["id"])
        self.assertEqual([item["status"] for item in batch["items"]], ["Failed", "Passed"])
        self.assertEqual(batch["execution_status"], "Completed")
        self.assertEqual(batch["validation_status"], "Failed")
        self.assertEqual(batch["accepted_node_count"], 1)
        with patch("hullcirq.workflow.verify_behavior", self.verify):
            retry = self.wait(self.start("s06-explicit-retry")["id"])
        self.assertEqual([item["status"] for item in retry["items"]], ["Passed", "Skipped"])

    def test_missing_checker_is_unsupported_and_other_node_runs(self):
        self.make_sources(unsupported_second=True)
        with patch("hullcirq.workflow.verify_behavior", self.verify):
            batch = self.wait(self.start()["id"])
        self.assertEqual([item["status"] for item in batch["items"]], ["Passed", "Unsupported"])
        self.assertEqual(batch["items"][1]["error"]["code"], "verification_contract_missing")
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(batch["accepted_node_count"], 1)
        self.manager.close()
        self.manager = WorkflowManager(self.store, self.candidates)
        self.assertEqual(self.manager.batch(batch["id"])["items"][1]["status"], "Unsupported")

    def test_missing_adopted_s05_blocks_only_that_node(self):
        first = self.manager.envelope()["workflow_runs"][0]
        self.manager.review(first["id"], "changes_requested", "Software fixture withdrawal.")
        with patch("hullcirq.workflow.verify_behavior", self.verify):
            batch = self.wait(self.start()["id"])
        self.assertEqual([item["status"] for item in batch["items"]], ["Blocked", "Passed"])
        self.assertEqual(batch["items"][0]["error"]["code"], "synthesis_not_adopted")
        self.assertEqual(len(self.calls), 1)

    def test_tool_exception_or_unsupported_result_keeps_remaining_node_eligible(self):
        for first_outcome in ("exception", "unsupported"):
            with self.subTest(first_outcome=first_outcome):
                self.calls.clear()
                attempts = []
                def outcome(*arguments, **options):
                    attempts.append(arguments)
                    if len(attempts) == 1:
                        if first_outcome == "exception":
                            raise DomainError("software_tool_failed", "Isolated tool stub failure.")
                        return {"validation_status": "Unsupported", "executed": False, "exit_code": None,
                                "diagnostics": [{"code": "unsupported_software_fixture", "message": "Isolated unsupported tool."}]}
                    return self.verify(*arguments, **options)
                with patch("hullcirq.workflow.verify_behavior", outcome):
                    # A distinct compiler forces neither circuit changes nor a
                    # new candidate. Withdraw the second adoption to exercise it.
                    previous = [run for run in self.manager.envelope()["workflow_runs"] if run["stage_id"] == S06]
                    if previous:
                        self.manager.review(previous[-1]["id"], "changes_requested", "Software fixture rerun.")
                    batch = self.wait(self.start("s06-outcome-" + first_outcome)["id"])
                self.assertEqual(len(attempts), 2)
                self.assertEqual([item["status"] for item in batch["items"]],
                                 ["Failed" if first_outcome == "exception" else "Unsupported", "Passed"])

    def test_later_failed_s06_withdraws_older_batch_current_adoption_count(self):
        with patch("hullcirq.workflow.verify_behavior", self.verify):
            batch = self.wait(self.start()["id"])
        first = batch["items"][0]
        def failure(*arguments, **options):
            result = self.verify(*arguments, **options)
            result.update(validation_status="Failed", exit_code=1)
            return result
        with patch("hullcirq.workflow.verify_behavior", failure):
            self.manager.start(S06, first["node_id"], first["candidate_id"], batch["revision_id"])
            deadline = time.monotonic() + 5
            while self.manager.is_active() and time.monotonic() < deadline:
                time.sleep(.01)
        historical = self.manager.batch(batch["id"])
        self.assertEqual(historical["validation_status"], "Passed")
        self.assertEqual(historical["accepted_node_count"], 1)
        self.assertEqual(self.manager.run(first["run_id"])["review_status"], "Accepted")

    def test_missing_s04_blocks_only_that_node(self):
        self.candidates.selected[next(iter(self.candidates.selected))] = None
        with patch("hullcirq.workflow.verify_behavior", self.verify):
            batch = self.wait(self.start()["id"])
        self.assertEqual([item["status"] for item in batch["items"]], ["Blocked", "Passed"])
        self.assertEqual(len(self.calls), 1)

    def test_no_compiler_or_invalid_stage_produces_no_batch(self):
        before = self.manager.path.read_bytes()
        self.manager.compiler = None
        with self.assertRaises(DomainError) as caught:
            self.start()
        self.assertEqual(caught.exception.code, "compiler_unavailable")
        with self.assertRaises(DomainError) as caught:
            self.start(stage="local_rtl_generation")
        self.assertEqual(caught.exception.code, "invalid_batch_request")
        self.assertEqual(before, self.manager.path.read_bytes())

    def test_request_id_is_idempotent_and_conflicts_across_stages(self):
        with patch("hullcirq.workflow.verify_behavior", self.verify):
            first = self.wait(self.start()["id"])
            again = self.start()
        self.assertEqual(first["id"], again["id"])
        self.assertEqual(len(self.calls), 2)
        with self.assertRaises(DomainError) as caught:
            self.start(stage=S05)
        self.assertEqual(caught.exception.code, "batch_request_conflict")

    def test_cancel_interrupts_current_and_never_starts_remaining_node(self):
        entered = threading.Event()
        def hold(netlist, plan, configuration, directory, cancelled, **options):
            entered.set(); cancelled.wait(3)
            return self.verify(netlist, plan, configuration, directory, cancelled, **options)
        with patch("hullcirq.workflow.verify_behavior", hold):
            batch = self.start()
            self.assertTrue(entered.wait(2))
            self.manager.cancel_batch(batch["id"])
            result = self.wait(batch["id"])
        self.assertEqual(result["execution_status"], "Cancelled")
        self.assertEqual([item["status"] for item in result["items"]], ["Cancelled", "Cancelled"])
        self.assertEqual(len(self.calls), 1)

    def test_s05_adoption_change_interrupts_running_batch_without_false_adoption(self):
        entered = threading.Event()
        def hold(netlist, plan, configuration, directory, cancelled, **options):
            entered.set(); cancelled.wait(3)
            return self.verify(netlist, plan, configuration, directory, cancelled, **options)
        with patch("hullcirq.workflow.verify_behavior", hold):
            batch = self.start()
            self.assertTrue(entered.wait(2))
            self.manager.review(batch["items"][0]["prior_run_id"], "changes_requested", "Withdraw source during fixture.")
            result = self.wait(batch["id"])
        self.assertEqual(result["execution_status"], "Interrupted")
        self.assertEqual(result["error"]["code"], "batch_source_changed")
        self.assertEqual(result["accepted_node_count"], 0)
        self.assertEqual(len(self.calls), 1)

    def test_saved_revision_change_interrupts_running_batch(self):
        entered = threading.Event()
        def hold(netlist, plan, configuration, directory, cancelled, **options):
            entered.set(); cancelled.wait(3)
            return self.verify(netlist, plan, configuration, directory, cancelled, **options)
        with patch("hullcirq.workflow.verify_behavior", hold):
            batch = self.start()
            self.assertTrue(entered.wait(2))
            state = self.store.envelope()
            state["design"]["layout"]["nodes"]["node-mac"]["x"] += 1
            self.store.save(state["design"], state["revision"]["id"])
            result = self.wait(batch["id"])
        self.assertEqual(result["execution_status"], "Interrupted")
        self.assertFalse(result["source_current"])
        self.assertEqual(result["items"][1]["status"], "Blocked")

    def test_new_unadopted_rtl_request_interrupts_running_batch(self):
        entered = threading.Event()
        def hold(netlist, plan, configuration, directory, cancelled, **options):
            entered.set(); cancelled.wait(3)
            return self.verify(netlist, plan, configuration, directory, cancelled, **options)
        with patch("hullcirq.workflow.verify_behavior", hold):
            batch = self.start()
            self.assertTrue(entered.wait(2))
            self.candidates.latest[batch["items"][1]["node_id"]] = "software-new-unadopted-rtl"
            result = self.wait(batch["id"])
        self.assertEqual(result["execution_status"], "Interrupted")
        self.assertEqual(result["accepted_node_count"], 0)
        self.assertEqual(len(self.calls), 1)

    def test_compiler_is_frozen_per_batch(self):
        entered, release = threading.Event(), threading.Event()
        def hold(*arguments, **options):
            entered.set(); release.wait(3)
            return self.verify(*arguments, **options)
        with patch("hullcirq.workflow.verify_behavior", hold):
            batch = self.start()
            self.assertTrue(entered.wait(2))
            self.manager.compiler = {"changed": "software fixture"}
            release.set()
            self.wait(batch["id"])
        self.assertEqual([call["configuration"] for call in self.calls], [batch["tool_configuration"]] * 2)

    def test_manual_policy_requires_each_result_review_and_does_not_reuse_unadopted_pass(self):
        self.store.set_review_policy("manual", False, "Software manual review.", self.store.review_policy()["id"])
        with patch("hullcirq.workflow.verify_behavior", self.verify):
            batch = self.wait(self.start()["id"])
        self.assertEqual(batch["validation_status"], "Passed")
        self.assertEqual(batch["accepted_node_count"], 0)
        for item in batch["items"]:
            self.manager.review(item["run_id"], "accepted", "Software review.")
        with patch("hullcirq.workflow.verify_behavior", side_effect=AssertionError("Reuse only")):
            reused = self.wait(self.start("s06-manually-adopted")["id"])
        self.assertEqual([item["status"] for item in reused["items"]], ["Skipped", "Skipped"])

    def test_restart_marks_unfinished_batch_interrupted_without_resend(self):
        with patch("hullcirq.workflow.verify_behavior", self.verify):
            batch = self.wait(self.start()["id"])
        self.manager.close()
        state = json.loads(self.manager.path.read_text(encoding="utf-8"))
        record = state["batches"][-1]
        record.update(execution_status="Running", validation_status="Not Checked", finished_at=None)
        record["items"][1].update(status="Queued", run_id=None)
        record["record_hash"] = object_hash({key: value for key, value in record.items() if key != "record_hash"})
        self.manager.path.write_text(json.dumps(state), encoding="utf-8")
        with patch("hullcirq.workflow.verify_behavior", side_effect=AssertionError("Restart must not simulate")):
            self.manager = WorkflowManager(self.store, self.candidates)
        recovered = self.manager.batch(batch["id"])
        self.assertEqual(recovered["execution_status"], "Interrupted")
        self.assertEqual([item["status"] for item in recovered["items"]], ["Passed", "Interrupted"])
        self.assertFalse(self.manager.is_active())

    def test_saved_s06_reopens_without_rewrite_and_readonly_batch_remains_inspectable(self):
        with patch("hullcirq.workflow.verify_behavior", self.verify):
            batch = self.wait(self.start()["id"])
        self.manager.close()
        before = self.manager.path.read_bytes()
        self.manager = WorkflowManager(self.store, self.candidates)
        self.assertEqual(self.manager.path.read_bytes(), before)
        saved = SavedManager(SavedFiles(self.store.path), "workflow", self.store)
        readonly = saved.batch(batch["id"])
        self.assertEqual(readonly["stage_id"], S06)
        self.assertEqual(readonly["items"], batch["items"])
        self.assertEqual(readonly["status_origin"], "recorded_snapshot")
        self.assertEqual(self.manager.path.read_bytes(), before)

    def test_rehashed_tampered_netlist_source_is_rejected_without_overwrite(self):
        with patch("hullcirq.workflow.verify_behavior", self.verify):
            self.wait(self.start()["id"])
        self.manager.close()
        state = json.loads(self.manager.path.read_text(encoding="utf-8"))
        record = state["batches"][-1]
        record["items"][0]["netlist_sha256"] = "not-the-s05-netlist"
        record["record_hash"] = object_hash({key: value for key, value in record.items() if key != "record_hash"})
        self.manager.path.write_text(json.dumps(state), encoding="utf-8")
        before = self.manager.path.read_bytes()
        with self.assertRaises(DomainError) as caught:
            WorkflowManager(self.store, self.candidates)
        self.assertEqual(caught.exception.code, "invalid_workflow_store")
        self.assertEqual(self.manager.path.read_bytes(), before)

    def test_legacy_s05_batch_without_stage_remains_readable_and_default_start_is_s05(self):
        self.manager.close()
        state = json.loads(self.manager.path.read_text(encoding="utf-8"))
        record = state["batches"][0]
        record.pop("stage_id")
        record["record_hash"] = object_hash({key: value for key, value in record.items() if key != "record_hash"})
        self.manager.path.write_text(json.dumps(state), encoding="utf-8")
        self.manager = WorkflowManager(self.store, self.candidates, synthesizer={"kind": "native", "executable": "yosys"})
        self.assertEqual(self.manager.batch(record["id"])["stage_id"], S05)
        with patch("hullcirq.workflow.synthesize_generic", side_effect=AssertionError("Exact S05 reused")):
            response = self.manager.start_batch(self.store.envelope()["revision"]["id"], "default-s05-request")
            batch = self.wait(response["workflow_batches"][-1]["id"])
        self.assertEqual(batch["stage_id"], S05)
        self.assertEqual(batch["validation_status"], "Passed")


if __name__ == "__main__":
    unittest.main()
