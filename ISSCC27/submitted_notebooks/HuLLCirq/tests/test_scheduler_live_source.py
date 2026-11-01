"""Isolated software QA: live scheduler source guards and stream persistence.

The HTTP SSE source and compiler/behavior/synthesis responses are explicitly
software fixtures. No actual model or EDA tool executes; actual evidence and
the live user's project are read-only.

The source-guard cases explicitly exercise historical queued requests with
frozen behavioral plans. Current S04 requests are interface-only; the separate
current-scope case below verifies that no behavioral run is implied.
"""
from __future__ import annotations

import copy
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import shutil
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))
from hullcirq.context import node_fingerprint
from hullcirq.domain import DomainError, IMPLEMENTED_STAGES
from hullcirq.generation import GenerationManager, request_hash
from hullcirq.store import ProjectStore
from hullcirq.verification import build_verification_plan, content_hash
from hullcirq.workflow import WorkflowManager


def software_format(*args, **kwargs):
    return {"validation_status": "Passed", "diagnostics": [], "checks": {
        "interface": {"validation_status": "Passed"},
        "syntax": {"validation_status": "Passed", "executed": True, "exit_code": 0},
        "functional_verification": {"validation_status": "Not Run", "executed": False}}}


def software_behavior(rtl, plan, compiler, **kwargs):
    return {"validation_status": "Passed", "executed": True, "exit_code": 0, "diagnostics": [],
            "scope": "software_fixture_not_actual_simulation",
            "vector_hash": plan["vector_hash"], "testbench_sha256": plan["testbench_sha256"],
            "rtl_sha256": content_hash(rtl)}


class SchedulerLiveSourceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        source = self.directory / "proposal.json"
        source.write_bytes((PROJECT / "examples/npu_scheduler_project.json").read_bytes())
        self.store = ProjectStore(self.directory / "project", source)
        self.store.set_review_policy("accept_on_pass", True, "Isolated software QA authorization.")
        for stage in IMPLEMENTED_STAGES:
            self.store.validate(stage, self.store.envelope()["revision"]["id"])
        self.manager = GenerationManager(self.store)
        self.addCleanup(self.manager.close)
        self.manager.save_profile({"id": "software-fixture", "name": "Software QA only",
                                   "execution_location": "Local", "base_url": "http://127.0.0.1:9/v1",
                                   "model": "software-fixture-no-model", "context_window": 131072})

    def run_generation(self, mutate=None, emitter=None, real_transport=False, padding=0, legacy=True):
        state = self.store.envelope()
        preview = self.manager.preview("node-scheduler", state["revision"]["id"])
        rtl = preview["requested_module_header"] + "// Software fixture, no actual RTL behavior.\n" + "//" + "x" * padding + "\nendmodule\n"
        raw = "```verilog\n" + rtl + "```"
        def response(messages, parameters, cancel, on_event):
            if mutate:
                mutate()
            if emitter:
                emitter(raw, on_event)
            return {"raw_content": raw, "raw_reasoning": "", "execution_status": "Completed",
                    "finish_reason": "stop", "usage": {"completion_tokens": 1}, "error": None}
        execute = self.manager._execute
        def historical_request(job_id, cancelled):
            # A declared historical queued-record fixture, not an available
            # current GUI generation mode or a modified real saved request.
            if legacy:
                with self.manager.lock:
                    job = self.manager._stored_job(job_id)
                    job.pop("validation_scope")
                    job["context"].pop("validation_scope")
                    job["context_id"] = request_hash(job["context"], job["profile_revision_id"],
                                                     job["parameters"], job["operation"], job["base_job_id"])
                    job["verification_plan"] = build_verification_plan(
                        self.store.snapshot(job["revision_id"]), job["node_id"])
                    self.manager._persist()
            return execute(job_id, cancelled)
        with patch("hullcirq.generation.check_rtl", side_effect=software_format), \
             patch("hullcirq.generation.verify_behavior", side_effect=software_behavior) as behavior, \
             patch.object(self.manager, "_execute", side_effect=historical_request):
            if real_transport:
                self.manager.start("node-scheduler", state["revision"]["id"], preview["context_id"], preview["profile_revision_id"])
                self.manager._worker.join(20)
            else:
                with patch("hullcirq.generation.ChatCompletionsClient") as client:
                    client.return_value.generate.side_effect = response
                    self.manager.start("node-scheduler", state["revision"]["id"], preview["context_id"], preview["profile_revision_id"])
                    self.manager._worker.join(20)
            self.assertFalse(self.manager._worker.is_alive())
            if not legacy:
                behavior.assert_not_called()
        return self.manager.envelope()["generation"]["jobs"][-1], raw

    def test_current_s04_checks_interface_and_defers_behavior_without_a_plan(self):
        job, _ = self.run_generation(legacy=False)
        self.assertEqual(job["validation_status"], "Passed")
        self.assertEqual(job["review_status"], "Accepted")
        self.assertIsNone(job["verification_plan"])
        self.assertEqual(job["checks"]["behavioral"]["deferred_to_stage"], "local_netlist_simulation")

    def wrong_live_type_and_layout(self):
        state = self.store.envelope()
        design = state["design"]
        design["verification_jobs"][0]["k"] = 4.0
        design["layout"]["nodes"]["node-scheduler"]["x"] += 1
        self.store.save(design, state["revision"]["id"])
        self.assertIs(type(self.store.envelope()["design"]["verification_jobs"][0]["k"]), float)

    def restore_integer_with_layout_change(self):
        state = self.store.envelope()
        design = state["design"]
        design["verification_jobs"][0]["k"] = 4
        design["layout"]["nodes"]["node-scheduler"]["x"] += 1
        self.store.save(design, state["revision"]["id"])

    def test_healthy_source_keeps_exact_frozen_context_plan_and_adoption(self):
        job, _ = self.run_generation()
        before = self.manager.path.read_bytes()
        self.assertEqual(job["freshness"], "Current")
        self.assertEqual(job["review_status"], "Accepted")
        self.assertEqual(self.manager.job(job["id"])["context"], job["context"])
        self.assertEqual(self.manager.job(job["id"])["verification_plan"], job["verification_plan"])
        self.assertEqual(self.manager.path.read_bytes(), before)

    def test_invalid_live_type_with_equal_hash_withdraws_once_and_restore_does_not_revive(self):
        job, _ = self.run_generation()
        original_hash = node_fingerprint(self.store.envelope()["design"], "node-scheduler")
        original_epoch = self.manager._state["node_epochs"]["node-scheduler"]
        self.wrong_live_type_and_layout()
        self.assertEqual(node_fingerprint(self.store.envelope()["design"], "node-scheduler"), original_hash)
        current = self.manager.job(job["id"])
        self.assertEqual(current["freshness"], "Stale")
        self.assertEqual(current["review_status"], "Awaiting Review")
        self.assertEqual(current["current_source_validation"]["validation_status"], "Failed")
        self.assertEqual(self.manager._state["node_epochs"]["node-scheduler"], original_epoch + 1)
        durable = self.manager.path.read_bytes()
        self.manager.job(job["id"])
        self.assertEqual(self.manager.path.read_bytes(), durable)
        self.restore_integer_with_layout_change()
        restored = self.manager.job(job["id"])
        self.assertEqual(restored["freshness"], "Current")
        self.assertEqual(restored["review_status"], "Awaiting Review")
        self.assertEqual(restored["context"], job["context"])
        self.assertEqual(restored["verification_plan"], job["verification_plan"])

    def test_invalid_live_source_blocks_historical_acceptance_behavior_and_next_tools(self):
        job, _ = self.run_generation()
        workflow = WorkflowManager(self.store, self.manager)
        self.addCleanup(workflow.close)
        self.wrong_live_type_and_layout()
        with self.assertRaises(DomainError):
            self.manager.review(job["id"], "accepted", "Must reject invalid current source.")
        for stage in ("local_synthesis", "local_netlist_simulation"):
            with self.subTest(stage=stage), self.assertRaises(DomainError):
                workflow.start(stage, "node-scheduler", job["id"], self.store.envelope()["revision"]["id"])
        preview = self.manager.preview("node-scheduler", self.store.envelope()["revision"]["id"])
        # Current S04 does not validate numeric simulation jobs. The behavioral
        # plan still rejects invalid typing before any simulation or model call.
        self.assertTrue(preview["ready_to_generate"])
        with self.assertRaises(DomainError), patch("hullcirq.generation.ChatCompletionsClient") as client:
            build_verification_plan(self.store.envelope()["design"], "node-scheduler")
        client.assert_not_called()
        self.assertEqual(len(self.manager.envelope()["generation"]["jobs"]), 1)

    def test_invalid_live_source_during_completion_blocks_automatic_adoption(self):
        job, _ = self.run_generation(mutate=self.wrong_live_type_and_layout)
        self.assertEqual(job["validation_status"], "Passed")  # Software fixture only.
        self.assertEqual(job["freshness"], "Stale")
        self.assertEqual(job["review_status"], "Awaiting Review")
        self.assertEqual(self.manager.envelope()["generation"]["reviews"], [])

    def test_historical_tool_adoption_is_stale_on_invalid_source_and_after_restore(self):
        job, _ = self.run_generation()
        workflow = WorkflowManager(self.store, self.manager)
        self.addCleanup(workflow.close)
        def synthesis(rtl, module, synthesizer, directory, cancel=None):
            return {"validation_status": "Passed", "executed": True, "exit_code": 0, "diagnostics": [],
                    "netlist": rtl, "netlist_sha256": content_hash(rtl), "rtl_sha256": content_hash(rtl),
                    "scope": "software_fixture_not_actual_synthesis"}
        with patch("hullcirq.workflow.synthesize_generic", side_effect=synthesis):
            result = workflow.start("local_synthesis", "node-scheduler", job["id"], self.store.envelope()["revision"]["id"])
            workflow._worker.join(10)
        run_id = result["workflow_runs"][-1]["id"]
        # Historical S05 records inherited the S04 plan. Current S05 records
        # intentionally have no behavioral plan; reproduce only the declared
        # old software-record schema for this compatibility guard test.
        with workflow.lock:
            historical = workflow._run(run_id)
            historical.pop("workflow_scope_version")
            historical.update(verification_plan=copy.deepcopy(job["verification_plan"]),
                              vector_hash=job["verification_plan"]["vector_hash"],
                              testbench_sha256=job["verification_plan"]["testbench_sha256"])
            workflow._persist()
        self.assertEqual(workflow.run(run_id)["review_status"], "Accepted")
        self.wrong_live_type_and_layout()
        self.assertEqual(workflow.run(run_id)["freshness"], "Stale")
        self.assertEqual(workflow.run(run_id)["review_status"], "Awaiting Review")
        self.restore_integer_with_layout_change()
        self.assertEqual(workflow.run(run_id)["freshness"], "Stale")
        self.assertEqual(workflow.run(run_id)["review_status"], "Awaiting Review")

    def test_withdrawal_survives_restart_without_editing_saved_prompt(self):
        job, _ = self.run_generation()
        self.wrong_live_type_and_layout()
        self.manager.job(job["id"])
        self.manager.close()
        reloaded = GenerationManager(ProjectStore(self.store.state_path.parent))
        self.addCleanup(reloaded.close)
        self.assertEqual(reloaded.job(job["id"])["freshness"], "Stale")
        self.assertEqual(reloaded.job(job["id"])["context"], job["context"])
        self.restore_integer_with_layout_change()
        # Reload its store to observe the restored source, retaining the epoch.
        restored = GenerationManager(ProjectStore(self.store.state_path.parent))
        self.addCleanup(restored.close)
        self.assertEqual(restored.job(job["id"])["review_status"], "Awaiting Review")

    def test_old_PE_saved_history_and_contexts_remain_byte_preserved(self):
        target = self.directory / "old-pe"
        target.mkdir()
        for filename in ("state.json", "generation.json"):
            shutil.copy2(PROJECT / "results/npu_pe_continuous_flow" / filename, target / filename)
        before = (target / "generation.json").read_bytes()
        old = GenerationManager(ProjectStore(target))
        self.addCleanup(old.close)
        passed = old.envelope()["generation"]["jobs"][-1]
        self.assertEqual(passed["review_status"], "Accepted")
        self.assertEqual(passed["freshness"], "Current")
        self.assertEqual((target / "generation.json").read_bytes(), before)

    def test_large_scheduler_plan_many_real_HTTP_SSE_chunks_coalesce_and_reload_exactly(self):
        preview = self.manager.preview("node-scheduler", self.store.envelope()["revision"]["id"])
        raw = "```verilog\n" + preview["requested_module_header"] + "// Software fixture, no actual RTL behavior.\n//" + "x" * 16000 + "\nendmodule\n```"
        chunks = [raw[position:position + 7] for position in range(0, len(raw), 7)]
        reasoning = "software reasoning fixture \u03bb"
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def do_POST(self):
                self.rfile.read(int(self.headers["Content-Length"]))
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Connection", "close")
                self.end_headers()
                def emit(payload):
                    self.wfile.write(("data: " + json.dumps(payload) + "\n\n").encode("utf-8"))
                emit({"id": "software-sse", "choices": [{"delta": {"reasoning_content": reasoning}, "finish_reason": None}]})
                for chunk in chunks:
                    emit({"id": "software-sse", "choices": [{"delta": {"content": chunk}, "finish_reason": None}]})
                emit({"choices": [{"delta": {}, "finish_reason": "stop"}]})
                emit({"choices": [], "usage": {"completion_tokens": len(chunks)}})
                self.wfile.write(b"data: [DONE]\n\n")
                self.wfile.flush()
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(lambda: (server.shutdown(), server.server_close(), thread.join(2)))
        profile = self.manager.envelope()["llm"]["profile"]
        profile["base_url"] = f"http://127.0.0.1:{server.server_port}/v1"
        self.manager.save_profile(profile, self.manager.envelope()["llm"]["profile_revision_id"])
        with patch.object(self.manager, "_persist", wraps=self.manager._persist) as persist:
            job, _ = self.run_generation(real_transport=True, padding=16000)
            self.assertLess(persist.call_count, len(chunks) // 10)
        self.assertGreater(len(chunks), 2000)
        self.assertGreater(len(json.dumps(job["verification_plan"])), 400000)
        self.assertEqual(job["raw_content"], raw)
        self.assertEqual(job["raw_reasoning"], reasoning)
        self.assertEqual(job["usage"], {"completion_tokens": len(chunks)})
        self.assertEqual([event["content"] for event in job["events"] if event["type"] == "content"], chunks)
        self.assertEqual([event["sequence"] for event in job["events"]], list(range(1, len(job["events"]) + 1)))
        self.assertEqual(job["execution_status"], "Completed")
        self.manager.close()
        reloaded = GenerationManager(ProjectStore(self.store.state_path.parent))
        self.addCleanup(reloaded.close)
        self.assertEqual(reloaded.job(job["id"])["events"], job["events"])
        self.assertEqual(reloaded.job(job["id"])["raw_content"], raw)
        self.assertEqual(reloaded.job(job["id"])["usage"], job["usage"])

    def test_time_checkpoint_and_terminal_event_flush_keep_pending_text_durable(self):
        clock = [0.0]
        captured = []
        def emitter(raw, on_event):
            on_event({"type": "content", "content": raw[:5]})
            captured.append(json.loads(self.manager.path.read_text(encoding="utf-8"))["jobs"][-1]["raw_content"])
            clock[0] = 0.6
            on_event({"type": "content", "content": raw[5:10]})
            captured.append(json.loads(self.manager.path.read_text(encoding="utf-8"))["jobs"][-1]["raw_content"])
            on_event({"type": "content", "content": raw[10:]})
            on_event({"type": "finish", "finish_reason": "stop"})
            captured.append(json.loads(self.manager.path.read_text(encoding="utf-8"))["jobs"][-1]["raw_content"])
        with patch("hullcirq.generation.time", SimpleNamespace(monotonic=lambda: clock[0])):
            job, raw = self.run_generation(emitter=emitter)
        self.assertEqual(captured, ["", raw[:10], raw])
        self.assertEqual(job["raw_content"], raw)
        self.assertEqual(job["events"][-1]["type"], "finished")


if __name__ == "__main__":
    unittest.main()
