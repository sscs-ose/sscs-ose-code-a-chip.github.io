"""Bounded software-only regression for the S12 terminal/read lock cycle.

No project managers, model, tool, saved design, or HTTP listener are started.
"""
from __future__ import annotations

import copy
import io
from email.message import Message
from pathlib import Path
import sys
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))
from hullcirq import observation
from hullcirq.observation import readonly_observation_scope
from hullcirq.physical_workflow import PhysicalWorkflowManager
from hullcirq.server import RequestHandler
from hullcirq.verification import object_hash


class OrderedPhysicalEnvelopeTests(unittest.TestCase):
    def manager(self, lock=None, store=None, source=None, error=None):
        design = {"settings": {"clock_period_ns": 50}, "physical_design": {"version": "mixed-v1"}}
        configuration = {"version": "SOFTWARE_QA_ONLY", "fixture": "no tool execution"}
        manager = SimpleNamespace(lock=lock or threading.RLock(),
            store=store or SimpleNamespace(envelope=lambda: {"design": copy.deepcopy(design)}),
            tool_configuration=configuration, _state={"runs": [], "reviews": []}, _storage_error=None,
            observe_design=lambda: ("fixture-source", source, error), _cleanup_unresolved=lambda: False,
            _decorate=lambda value: copy.deepcopy(value))
        # Match the real constructor without creating or persisting a store.
        manager._committed = copy.deepcopy(manager._state)
        return manager, design, configuration

    def run_cycle(self, legacy=False):
        """Force exactly store->physical versus old physical->store edges.

        All lock waits are bounded. The old expression raises rather than
        leaving deadlocked threads behind; the real fixed envelope completes.
        """
        physical_entered = threading.Event()
        store_held = threading.Event()
        worker_obtained_physical = threading.Event()
        worker_errors = []
        reader_errors = []
        store_lock = threading.RLock()

        class PhysicalLock:
            def __init__(self):
                self.raw = threading.RLock()

            def __enter__(self):
                if not self.raw.acquire(timeout=2):
                    raise TimeoutError("bounded physical lock wait")
                if threading.current_thread().name == "software-qa-reader":
                    physical_entered.set()
                    if not store_held.wait(2):
                        self.raw.release()
                        raise TimeoutError("source worker did not acquire fixture store")
                return self

            def __exit__(self, *unused):
                self.raw.release()

        physical_lock = PhysicalLock()

        def snapshot():
            if not store_lock.acquire(timeout=0.4):
                raise TimeoutError("bounded store lock wait: physical/store inversion")
            try:
                return {"design": {"settings": {"clock_period_ns": 50},
                                   "physical_design": {"version": "mixed-v1"}}}
            finally:
                store_lock.release()

        manager, _, configuration = self.manager(physical_lock, SimpleNamespace(envelope=snapshot),
                                                  {"configuration": {"version": "SOFTWARE_QA_ONLY"}, "identity": {}})

        def source_worker():
            try:
                if not physical_entered.wait(2):
                    raise TimeoutError("reader did not acquire fixture physical lock")
                with store_lock:
                    store_held.set()
                    with physical_lock:
                        worker_obtained_physical.set()
            except Exception as error:
                worker_errors.append(error)

        results = []

        def reader():
            try:
                if legacy:
                    # The exact removed order, isolated from product/live data.
                    manager.observe_design()
                    manager.store.envelope()["design"]["settings"]
                    with manager.lock:
                        manager.store.envelope()["design"]
                else:
                    results.append(PhysicalWorkflowManager.envelope(manager))
            except Exception as error:
                reader_errors.append(error)

        worker = threading.Thread(target=source_worker, name="software-qa-source", daemon=True)
        reader_thread = threading.Thread(target=reader, name="software-qa-reader", daemon=True)
        worker.start(); reader_thread.start()
        reader_thread.join(4); worker.join(4)
        self.assertFalse(reader_thread.is_alive()); self.assertFalse(worker.is_alive())
        self.assertFalse(worker_errors)
        self.assertTrue(worker_obtained_physical.is_set())
        return results, reader_errors

    def test_removed_order_reproduces_bounded_deadlock(self):
        _, errors = self.run_cycle(legacy=True)
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], TimeoutError)
        self.assertIn("physical/store inversion", str(errors[0]))

    def test_terminal_source_worker_and_real_envelope_both_finish(self):
        results, errors = self.run_cycle()
        self.assertEqual(errors, [])
        self.assertTrue(results[0]["physical_workflow"]["ready"])

    def test_one_store_snapshot_outside_result_lock_and_source_guard_once(self):
        lock = threading.RLock()
        calls = []
        observations = []
        design = {"settings": {"clock_period_ns": 50}, "physical_design": {"version": "mixed-v1"}}

        def snapshot():
            self.assertFalse(lock._is_owned())
            calls.append(True)
            return {"design": copy.deepcopy(design)}

        manager, _, configuration = self.manager(lock, SimpleNamespace(envelope=snapshot))
        manager.observe_design = lambda: (observations.append(True), None,
            {"code": "fixture_source_stale", "message": "Original source is stale."})
        before = copy.deepcopy(manager._state)
        with patch("hullcirq.physical_workflow.effective_configuration", return_value=configuration) as effective:
            with readonly_observation_scope():
                result = PhysicalWorkflowManager.envelope(manager)["physical_workflow"]
        self.assertEqual(calls, [True]); self.assertEqual(observations, [True])
        effective.assert_called_once_with(configuration, design)
        self.assertFalse(result["ready"])
        self.assertEqual(result["blocked_reason"], "Original source is stale.")
        self.assertEqual(result["settings_projection"], design["settings"])
        self.assertEqual(result["physical_design"], design["physical_design"])
        self.assertEqual(result["runtime_configuration_sha256"], object_hash(configuration))
        self.assertEqual(manager._state, before)


class StaticRequestScopeTests(unittest.TestCase):
    def invoke(self, path, api):
        entered = []
        inspected = []

        class ContextLock:
            def __enter__(self):
                entered.append(True)
                if not api:
                    raise AssertionError("static content acquired project context lock")

            def __exit__(self, *unused):
                entered.append(False)

        handler = RequestHandler.__new__(RequestHandler)
        handler.server = SimpleNamespace(context_lock=ContextLock())
        handler.path = path
        handler._do_GET = lambda: inspected.append(observation._READ_OBSERVATIONS.get() is not None)
        RequestHandler.do_GET(handler)
        self.assertEqual(inspected, [api])
        self.assertEqual(entered, [True, False] if api else [])
        self.assertIsNone(observation._READ_OBSERVATIONS.get())

    def test_static_root_assets_and_missing_files_bypass_context(self):
        for path in ("/", "/index.html", "/app.js", "/styles.css", "/favicon.ico", "/missing.js"):
            with self.subTest(path=path): self.invoke(path, False)

    def test_api_and_encoded_api_keep_context_and_readonly_scope(self):
        for path in ("/api/project", "/api/drc-workflow", "/%61pi/project", "/api%2Fproject"):
            with self.subTest(path=path): self.invoke(path, True)

    def static_handler(self, path, host=None):
        handler = RequestHandler.__new__(RequestHandler)
        handler.path = path
        handler.server = SimpleNamespace(server_address=("127.0.0.1", 12345), project_root=PROJECT,
                                         workspace=None)
        handler.headers = Message(); handler.headers["Host"] = host or "127.0.0.1:12345"
        handler.wfile = io.BytesIO()
        handler.close_connection = False
        captured = []
        handler._headers = lambda status, mime, length, *args, **kwargs: captured.append((status, mime, length))
        handler.log_error = lambda *unused: None
        return handler, captured

    def test_static_root_still_uses_original_html_and_host_security(self):
        handler, response = self.static_handler("/")
        RequestHandler.do_GET(handler)
        self.assertEqual(response[0][0], 200)
        self.assertEqual(handler.wfile.getvalue(), (PROJECT / "src/gui/index.html").read_bytes())
        bad, response = self.static_handler("/", host="untrusted.invalid:12345")
        RequestHandler.do_GET(bad)
        self.assertEqual(response[0][0], 403)
        self.assertIn(b"invalid_host", bad.wfile.getvalue())

    def test_static_traversal_still_rejected_without_context(self):
        for path in ("/../hullcirq/server.py", "/%2e%2e/hullcirq/server.py", "/assets/branding/../../AGENTS.md"):
            handler, response = self.static_handler(path)
            RequestHandler.do_GET(handler)
            self.assertEqual(response[0][0], 404)
            self.assertIn(b"file_not_found", handler.wfile.getvalue())


if __name__ == "__main__":
    unittest.main()
