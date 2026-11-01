"""Software queue QA only: stubbed synthesis is never circuit/EDA evidence."""
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
from hullcirq.context import node_fingerprint, physical_interface
from hullcirq.domain import DomainError
from hullcirq.store import ProjectStore
from hullcirq.verification import content_hash, object_hash
from hullcirq.workflow import WorkflowManager


class SoftwareCandidates:
    def __init__(self, store):
        self.store = store
        self.lock, self._worker, self._state = threading.RLock(), None, {"jobs": []}
        state = store.envelope()
        self.jobs, self.selected, self.latest = {}, {}, {}
        for node in state["design"]["nodes"]:
            interface = physical_interface(state["design"], node)
            identifier = "fixture-" + node["id"]
            self.jobs[identifier] = {"id": identifier, "node_id": node["id"], "revision_id": state["revision"]["id"],
                "input_hash": node_fingerprint(state["design"], node["id"]), "rtl": "module " + interface["module_name"] + "; endmodule\n",
                "context": {"interface": interface}, "execution_status": "Completed", "validation_status": "Passed", "review_status": "Accepted"}
            self.selected[node["id"]] = identifier
            self.latest[node["id"]] = identifier

    def job(self, identifier):
        result = copy.deepcopy(self.jobs[identifier])
        result["freshness"] = "Current" if result["input_hash"] == node_fingerprint(self.store.envelope()["design"], result["node_id"]) else "Stale"
        return result

    def envelope(self):
        return {"generation": {"nodes": [{"node_id": node, "accepted_job_id": identifier, "latest_job_id": self.latest[node]} for node, identifier in self.selected.items()]}}


class S05BatchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = ProjectStore(Path(self.temp.name) / "project", PROJECT / "examples/m1_two_nodes.json")
        for stage in ("global_settings", "graph_editor", "specifications"):
            run = self.store.validate(stage, self.store.envelope()["revision"]["id"])["runs"][-1]
            self.store.review(run["id"], "accepted", "Software fixture input review.")
        self.store.set_review_policy("accept_on_pass", True, "Software queue QA only.")
        self.candidates = SoftwareCandidates(self.store)
        self.manager = WorkflowManager(self.store, self.candidates, synthesizer={"kind": "native", "executable": "yosys"})
        self.addCleanup(lambda: self.manager.close())
        self.calls = []

    def synthesize(self, rtl, module, configuration, directory, cancelled):
        self.calls.append((module, copy.deepcopy(configuration)))
        return {"validation_status": "Passed", "executed": True, "exit_code": 0, "diagnostics": [],
                "netlist": rtl, "netlist_sha256": content_hash(rtl), "scope": "software_fixture_no_actual_synthesis"}

    def start(self, request="software-batch-request"):
        return self.manager.start_batch(self.store.envelope()["revision"]["id"], request)["workflow_batches"][-1]

    def wait(self, batch_id):
        deadline = time.monotonic() + 6
        while time.monotonic() < deadline:
            batch = self.manager.batch(batch_id)
            if batch["execution_status"] not in {"Queued", "Running"} and not self.manager.is_active():
                return batch
            time.sleep(.01)
        self.fail("Software batch did not settle")

    def test_sequential_nodes_adopt_each_and_reuse_exact_success_on_next_batch(self):
        with patch("hullcirq.workflow.synthesize_generic", self.synthesize), patch("hullcirq.workflow.verify_behavior", side_effect=AssertionError("S05 never runs S06")):
            batch = self.wait(self.start()["id"])
            self.assertEqual(batch["validation_status"], "Passed")
            self.assertEqual([item["status"] for item in batch["items"]], ["Passed", "Passed"])
            self.assertEqual(batch["accepted_node_count"], 2)
            self.assertEqual(len(self.calls), 2)
            self.assertEqual(len(self.manager.envelope()["workflow_reviews"]), 2)
            next_batch = self.wait(self.start("software-batch-next")["id"])
            self.assertEqual([item["status"] for item in next_batch["items"]], ["Skipped", "Skipped"])
            self.assertEqual(len(self.calls), 2)
        self.manager.close()
        original = self.manager.path.read_bytes()
        self.manager = WorkflowManager(self.store, self.candidates)
        self.assertEqual(self.manager.path.read_bytes(), original)
        self.assertEqual(self.manager.batch(batch["id"])["accepted_node_count"], 2)

    def test_failure_does_not_discard_success_or_stop_other_node(self):
        def synthesize(*args):
            result = self.synthesize(*args)
            if len(self.calls) == 1:
                result.update(validation_status="Failed", netlist=None, exit_code=1, diagnostics=[{"code": "software_failure", "message": "fixture failure"}])
            return result
        with patch("hullcirq.workflow.synthesize_generic", synthesize):
            batch = self.wait(self.start()["id"])
        self.assertEqual(batch["execution_status"], "Completed")
        self.assertEqual(batch["validation_status"], "Failed")
        self.assertEqual([item["status"] for item in batch["items"]], ["Failed", "Passed"])
        self.assertEqual(batch["accepted_node_count"], 1)
        with patch("hullcirq.workflow.synthesize_generic", self.synthesize):
            resumed = self.wait(self.start("software-explicit-retry")["id"])
        self.assertEqual([item["status"] for item in resumed["items"]], ["Passed", "Skipped"])
        self.assertEqual(len(self.manager.envelope()["workflow_runs"]), 3)

    def test_missing_s04_is_blocked_while_ready_node_runs(self):
        first = next(iter(self.candidates.selected))
        self.candidates.selected[first] = None
        with patch("hullcirq.workflow.synthesize_generic", self.synthesize):
            batch = self.wait(self.start()["id"])
        self.assertEqual([item["status"] for item in batch["items"]], ["Blocked", "Passed"])
        self.assertEqual(len(self.calls), 1)

    def test_idempotent_start_same_request_is_one_batch_and_one_run_per_node(self):
        entered, release = threading.Event(), threading.Event()
        def hold(*args):
            entered.set(); release.wait(3)
            return self.synthesize(*args)
        with patch("hullcirq.workflow.synthesize_generic", hold):
            first = self.start()
            self.assertTrue(entered.wait(2))
            same = self.start()
            self.assertEqual(first["id"], same["id"])
            with self.assertRaises(DomainError) as caught:
                self.start("software-other-request")
            self.assertEqual(caught.exception.code, "workflow_busy")
            node = first["items"][0]
            with self.assertRaises(DomainError):
                self.manager.start("local_synthesis", node["node_id"], node["candidate_id"], first["revision_id"])
            release.set()
            self.wait(first["id"])
            same = self.start()
        self.assertEqual(same["id"], first["id"])
        self.assertEqual(len(self.manager.envelope()["workflow_batches"]), 1)
        self.assertEqual(len(self.calls), 2)

    def test_cancel_stops_current_and_prevents_next_node(self):
        entered = threading.Event()
        def hold(rtl, module, configuration, directory, cancelled):
            entered.set(); cancelled.wait(3)
            return self.synthesize(rtl, module, configuration, directory, cancelled)
        with patch("hullcirq.workflow.synthesize_generic", hold):
            batch = self.start()
            self.assertTrue(entered.wait(2))
            self.manager.cancel_batch(batch["id"])
            batch = self.wait(batch["id"])
        self.assertEqual(batch["execution_status"], "Cancelled")
        self.assertEqual([item["status"] for item in batch["items"]], ["Cancelled", "Cancelled"])
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(len(self.manager.envelope()["workflow_reviews"]), 0)

    def test_revision_change_cancels_current_and_blocks_remaining(self):
        entered = threading.Event()
        def hold(rtl, module, configuration, directory, cancelled):
            entered.set(); cancelled.wait(3)
            return self.synthesize(rtl, module, configuration, directory, cancelled)
        with patch("hullcirq.workflow.synthesize_generic", hold):
            batch = self.start()
            self.assertTrue(entered.wait(2))
            state = self.store.envelope()
            state["design"]["layout"]["nodes"][batch["items"][0]["node_id"]]["x"] += 1
            self.store.save(state["design"], state["revision"]["id"])
            batch = self.wait(batch["id"])
        self.assertEqual(batch["execution_status"], "Interrupted")
        self.assertEqual(batch["error"]["code"], "batch_source_changed")
        self.assertFalse(batch["source_current"])
        self.assertEqual([item["status"] for item in batch["items"]], ["Cancelled", "Blocked"])
        self.assertEqual(len(self.calls), 1)

    def test_adopted_candidate_change_stops_same_revision_batch(self):
        entered = threading.Event()
        def hold(rtl, module, configuration, directory, cancelled):
            entered.set(); cancelled.wait(3)
            return self.synthesize(rtl, module, configuration, directory, cancelled)
        with patch("hullcirq.workflow.synthesize_generic", hold):
            batch = self.start()
            self.assertTrue(entered.wait(2))
            self.candidates.selected[batch["items"][1]["node_id"]] = None
            batch = self.wait(batch["id"])
        self.assertEqual(batch["execution_status"], "Interrupted")
        self.assertFalse(batch["source_current"])
        self.assertEqual(len(self.calls), 1)

    def test_new_unadopted_candidate_blocks_old_accepted_rtl(self):
        first = next(iter(self.candidates.selected))
        self.candidates.latest[first] = "software-new-unadopted-job"
        with patch("hullcirq.workflow.synthesize_generic", self.synthesize):
            batch = self.wait(self.start()["id"])
        self.assertEqual([item["status"] for item in batch["items"]], ["Blocked", "Passed"])
        self.assertIsNone(batch["items"][0]["candidate_id"])
        self.assertEqual(len(self.calls), 1)

    def test_new_candidate_same_input_withdraws_aggregate_without_rewriting_old_adoption(self):
        with patch("hullcirq.workflow.synthesize_generic", self.synthesize):
            batch = self.wait(self.start()["id"])
        first = next(iter(self.candidates.selected))
        old_id = self.candidates.selected[first]
        saved_run_id = batch["items"][0]["run_id"]
        original_history = self.manager.path.read_bytes()
        new_id = "software-repaired-same-input"
        self.candidates.jobs[new_id] = dict(self.candidates.jobs[old_id], id=new_id, rtl="module repaired; endmodule\n")
        self.candidates.selected[first] = self.candidates.latest[first] = new_id
        current = self.manager.envelope()
        node = next(item for item in current["workflow_nodes"] if item["node_id"] == first and item["stage_id"] == "local_synthesis")
        self.assertEqual(node["latest_run_id"], saved_run_id)
        self.assertIsNone(node["accepted_run_id"])
        historical = self.manager.run(saved_run_id)
        self.assertEqual(historical["review_status"], "Accepted")
        self.assertEqual(historical["candidate_id"], old_id)
        self.assertEqual(self.manager.path.read_bytes(), original_history)

    def test_new_pending_job_stops_batch_while_previous_adoption_is_retained(self):
        entered = threading.Event()
        def hold(rtl, module, configuration, directory, cancelled):
            entered.set(); cancelled.wait(3)
            return self.synthesize(rtl, module, configuration, directory, cancelled)
        with patch("hullcirq.workflow.synthesize_generic", hold):
            batch = self.start()
            self.assertTrue(entered.wait(2))
            self.candidates.latest[batch["items"][1]["node_id"]] = "software-new-pending-job"
            batch = self.wait(batch["id"])
        self.assertEqual(batch["execution_status"], "Interrupted")
        self.assertFalse(batch["source_current"])
        self.assertEqual(batch["accepted_node_count"], 0)
        self.assertEqual(len(self.calls), 1)

    def test_frozen_configuration_is_used_even_if_runtime_setting_changes(self):
        entered, release = threading.Event(), threading.Event()
        def hold(*args):
            entered.set(); release.wait(3)
            return self.synthesize(*args)
        with patch("hullcirq.workflow.synthesize_generic", hold):
            batch = self.start()
            self.assertTrue(entered.wait(2))
            self.manager.synthesizer = {"kind": "native", "executable": "yosys", "changed": True}
            release.set()
            self.wait(batch["id"])
        self.assertEqual([config for _, config in self.calls], [batch["tool_configuration"]] * 2)

    def test_restart_marks_interrupted_without_resending_and_keeps_success(self):
        with patch("hullcirq.workflow.synthesize_generic", self.synthesize):
            batch = self.wait(self.start()["id"])
        self.manager.close()
        state = json.loads(self.manager.path.read_text(encoding="utf-8"))
        record = state["batches"][0]
        record.update(execution_status="Running", validation_status="Not Checked", finished_at=None)
        record["items"][1].update(status="Queued", run_id=None)
        record["record_hash"] = object_hash({key: value for key, value in record.items() if key != "record_hash"})
        self.manager.path.write_text(json.dumps(state), encoding="utf-8")
        with patch("hullcirq.workflow.synthesize_generic", side_effect=AssertionError("Restart cannot execute tools")):
            self.manager = WorkflowManager(self.store, self.candidates)
        recovered = self.manager.batch(batch["id"])
        self.assertEqual(recovered["execution_status"], "Interrupted")
        self.assertEqual(recovered["items"][0]["status"], "Passed")
        self.assertEqual(recovered["items"][1]["status"], "Interrupted")
        self.assertFalse(self.manager.is_active())

    def test_old_store_reopen_is_byte_unchanged_and_missing_tool_has_no_batch(self):
        old = self.manager.path.read_bytes()
        self.manager.close()
        self.manager = WorkflowManager(self.store, self.candidates)
        self.assertEqual(self.manager.path.read_bytes(), old)
        self.assertNotIn("batches", json.loads(old))
        with self.assertRaises(DomainError) as caught:
            self.start()
        self.assertEqual(caught.exception.code, "synthesizer_unavailable")
        self.assertEqual(self.manager.path.read_bytes(), old)

    def test_tampered_batch_manifest_is_rejected_without_overwrite(self):
        with patch("hullcirq.workflow.synthesize_generic", self.synthesize):
            self.wait(self.start()["id"])
        self.manager.close()
        state = json.loads(self.manager.path.read_text(encoding="utf-8"))
        state["batches"][0]["items"][0]["candidate_id"] = "wrong-candidate"
        self.manager.path.write_text(json.dumps(state), encoding="utf-8")
        tampered = self.manager.path.read_bytes()
        with self.assertRaises(DomainError) as caught:
            WorkflowManager(self.store, self.candidates)
        self.assertEqual(caught.exception.code, "invalid_workflow_store")
        self.assertEqual(self.manager.path.read_bytes(), tampered)


if __name__ == "__main__":
    unittest.main()
