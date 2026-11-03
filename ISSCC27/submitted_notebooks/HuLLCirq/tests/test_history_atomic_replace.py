"""Injected local I/O faults; fake HTTP is software QA, never model evidence."""
from __future__ import annotations

import copy
import errno
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))
from hullcirq import store as store_module
from hullcirq.drc_workflow import DrcWorkflowManager
from hullcirq.generation import GenerationManager
from hullcirq.global_generation import GlobalGenerationManager
from hullcirq.global_workflow import GlobalWorkflowManager
from hullcirq.implementation_specs import ImplementationSpecManager
from hullcirq.lvs_workflow import LvsWorkflowManager
from hullcirq.physical_workflow import PhysicalWorkflowManager
from hullcirq.provider import ChatCompletionsClient
from hullcirq.store import ProjectStore
from hullcirq.workflow import WorkflowManager
import test_m2_workflow as fixtures


def denied():
    error = PermissionError(errno.EACCES, "SYNTHETIC_LOCAL_EXCEPTION_PAYLOAD")
    error.winerror = 5
    return error


class HistoryPersistenceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        store = ProjectStore(self.directory)
        generation = GenerationManager(store)
        workflow = WorkflowManager(store, generation)
        specifications = ImplementationSpecManager(store, generation, workflow)
        global_generation = GlobalGenerationManager(store, generation, workflow, specifications)
        global_workflow = GlobalWorkflowManager(store, generation, specifications, global_generation)
        physical = PhysicalWorkflowManager(store, global_generation, global_workflow)
        drc = DrcWorkflowManager(store, physical)
        lvs = LvsWorkflowManager(store, drc)
        self.managers = (generation, workflow, specifications, global_generation,
                         global_workflow, physical, drc, lvs)
        for manager in self.managers:
            if hasattr(manager, "close"):
                self.addCleanup(manager.close)
            # Some managers defer their first save until an operation occurs.
            with manager.lock:
                manager._persist()

    def test_all_eight_history_writers_retry_same_fsynced_bytes_before_commit(self):
        actual_replace = store_module.os.replace
        actual_fsync = store_module.os.fsync
        for manager in self.managers:
            with self.subTest(history=manager.path.name), manager.lock:
                previous = copy.deepcopy(manager._committed)
                previous_bytes = manager.path.read_bytes()
                staged = []

                def replace(source, destination):
                    self.assertEqual(store_module._io_path(destination), store_module._io_path(manager.path))
                    self.assertEqual(manager._committed, previous)
                    self.assertEqual(manager.path.read_bytes(), previous_bytes)
                    staged.append((source, Path(source).read_bytes()))
                    if len(staged) == 1:
                        raise denied()
                    actual_replace(source, destination)

                with patch.object(store_module, "sys", SimpleNamespace(platform="win32")), \
                        patch.object(store_module.os, "replace", side_effect=replace), \
                        patch.object(store_module.os, "fsync", wraps=actual_fsync) as fsync, \
                        patch.object(store_module.time, "sleep") as sleep:
                    manager._persist()
                self.assertEqual(len(staged), 2)
                self.assertEqual(staged[0], staged[1])
                self.assertEqual(manager.path.read_bytes(), staged[0][1])
                self.assertEqual(json.loads(staged[0][1]), manager._committed)
                self.assertIsNone(manager._storage_error)
                self.assertEqual(fsync.call_count, 1)
                self.assertEqual(sleep.call_count, 1)
                self.assertEqual(list(self.directory.glob(".*.tmp")), [])

    def test_all_eight_history_writers_exhaust_and_restore_prior_durable_state(self):
        for manager in self.managers:
            with self.subTest(history=manager.path.name), manager.lock:
                previous = copy.deepcopy(manager._committed)
                previous_bytes = manager.path.read_bytes()
                # Deliberately pending internal test data must never become durable.
                manager._state["uncommitted_software_fault_probe"] = True
                clock = [0.0]
                waits = []

                def sleep(delay):
                    waits.append(delay)
                    clock[0] += delay

                with patch.object(store_module, "sys", SimpleNamespace(platform="win32")), \
                        patch.object(store_module.os, "replace", side_effect=denied()) as replace, \
                        patch.object(store_module.time, "monotonic", side_effect=lambda: clock[0]), \
                        patch.object(store_module.time, "sleep", side_effect=sleep), \
                        self.assertRaises(PermissionError):
                    manager._persist()
                self.assertGreater(replace.call_count, 1)
                self.assertLessEqual(replace.call_count, 6)
                self.assertLessEqual(sum(waits), 0.3)
                self.assertEqual(manager.path.read_bytes(), previous_bytes)
                self.assertEqual(manager._state, previous)
                self.assertEqual(manager._committed, previous)
                self.assertEqual(manager._storage_error["code"], "storage_error")
                self.assertEqual(list(self.directory.glob(".*.tmp")), [])


class StreamCheckpointPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.GenerationWorkflowTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.accept_inputs()

    def test_usage_checkpoint_recovers_without_resending_or_losing_candidate(self):
        case = self.fixture
        actual_replace = store_module.os.replace
        denied_bytes = []
        with fixtures.FakeChatServer(fixtures.sse_events("```verilog\n" + fixtures.FIXTURE_RTL + "```")) as server, \
                patch("hullcirq.generation.check_rtl", case.simulated_pass_check):
            case.configure(server)

            def replace(source, destination):
                if store_module._io_path(destination) == store_module._io_path(case.manager.path):
                    candidate = json.loads(Path(source).read_text(encoding="utf-8"))
                    jobs = candidate["jobs"]
                    if jobs and jobs[-1]["events"] and jobs[-1]["events"][-1]["type"] == "usage":
                        denied_bytes.append((source, Path(source).read_bytes()))
                        if len(denied_bytes) <= 2:
                            raise denied()
                actual_replace(source, destination)

            with patch.object(store_module, "sys", SimpleNamespace(platform="win32")), \
                    patch.object(store_module.os, "replace", side_effect=replace):
                job = case.wait(case.start())
            self.assertEqual(len(server.requests), 1)
        self.assertEqual(len(denied_bytes), 3)
        self.assertTrue(all(item == denied_bytes[0] for item in denied_bytes))
        self.assertEqual(job["execution_status"], "Completed")
        self.assertEqual(job["validation_status"], "Passed")
        self.assertEqual(job["review_status"], "Awaiting Review")
        self.assertEqual(job["raw_content"], "```verilog\n" + fixtures.FIXTURE_RTL + "```")
        self.assertEqual(job["finish_reason"], "stop")
        self.assertEqual(job["usage"]["total_tokens"], 20)
        self.assertEqual(job["rtl"].strip(), fixtures.FIXTURE_RTL.strip())
        self.assertIsNone(job["error"])
        self.assertIn("usage", [event["type"] for event in job["events"]])
        preview = case.request(operation="repair", base_job_id=job["id"], instruction="Same-node software repair")
        self.assertEqual(preview["base_job_id"], job["id"])
        restarted = GenerationManager(case.store)
        self.addCleanup(restarted.close)
        self.assertEqual(restarted.job(job["id"]), job)

    def test_permanent_checkpoint_denial_retains_prior_state_and_reports_storage(self):
        case = self.fixture
        actual_replace = store_module.os.replace
        failure = {"enabled": False, "prior_bytes": None}
        with fixtures.FakeChatServer(fixtures.sse_events("```verilog\n" + fixtures.FIXTURE_RTL + "```")) as server, \
                patch("hullcirq.generation.check_rtl", side_effect=case.simulated_pass_check) as checker:
            case.configure(server)

            def replace(source, destination):
                if store_module._io_path(destination) == store_module._io_path(case.manager.path):
                    candidate = json.loads(Path(source).read_text(encoding="utf-8"))
                    jobs = candidate["jobs"]
                    if jobs and jobs[-1]["events"] and jobs[-1]["events"][-1]["type"] == "usage":
                        failure["enabled"] = True
                        failure["prior_bytes"] = case.manager.path.read_bytes()
                    if failure["enabled"]:
                        raise denied()
                actual_replace(source, destination)

            with patch.object(store_module, "sys", SimpleNamespace(platform="win32")), \
                    patch.object(store_module.os, "replace", side_effect=replace):
                case.start()
                case.manager._worker.join(timeout=3)
                self.assertFalse(case.manager._worker.is_alive())
                envelope = case.manager.envelope()
                self.assertEqual(envelope["generation"]["storage_error"]["code"], "storage_error")
                self.assertEqual(case.manager.path.read_bytes(), failure["prior_bytes"])
                self.assertEqual(case.manager._state, case.manager._committed)
                self.assertEqual(len(server.requests), 1)
                checker.assert_not_called()
        self.assertTrue(failure["enabled"])
        self.assertNotIn("connection_error", json.dumps(envelope))
        self.assertNotIn("SYNTHETIC_LOCAL_EXCEPTION_PAYLOAD", json.dumps(envelope))
        self.assertEqual(envelope["generation"]["reviews"], [])
        self.assertEqual(list(case.path.glob(".generation-*.tmp")), [])


class ProviderCallbackOriginTests(unittest.TestCase):
    def test_callback_io_error_is_storage_failure_with_received_data_and_no_retry(self):
        answer = "```verilog\n" + fixtures.FIXTURE_RTL + "```"

        def callback(event):
            if event["type"] == "usage":
                raise denied()

        with fixtures.FakeChatServer(fixtures.sse_events(answer)) as server:
            result = ChatCompletionsClient(fixtures.profile(server.base_url)).generate(
                [{"role": "user", "content": "Software transport fixture only"}], on_event=callback)
            self.assertEqual(len(server.requests), 1)
        self.assertEqual(result["execution_status"], "Failed")
        self.assertEqual(result["error"]["code"], "storage_error")
        self.assertEqual(result["raw_content"], answer)
        self.assertEqual(result["finish_reason"], "stop")
        self.assertEqual(result["usage"]["total_tokens"], 20)
        self.assertNotIn("SYNTHETIC_LOCAL_EXCEPTION_PAYLOAD", json.dumps(result))

    def test_callback_non_io_error_is_not_invalid_provider_response_or_connection(self):
        def callback(event):
            if event["type"] == "usage":
                raise ValueError("SYNTHETIC_LOCAL_EXCEPTION_PAYLOAD")

        with fixtures.FakeChatServer(fixtures.sse_events("complete software fixture")) as server:
            result = ChatCompletionsClient(fixtures.profile(server.base_url)).generate(
                [{"role": "user", "content": "Software transport fixture only"}], on_event=callback)
            self.assertEqual(len(server.requests), 1)
        self.assertEqual(result["execution_status"], "Failed")
        self.assertEqual(result["error"]["code"], "event_handler_error")
        self.assertNotIn("SYNTHETIC_LOCAL_EXCEPTION_PAYLOAD", json.dumps(result))


if __name__ == "__main__":
    unittest.main()
