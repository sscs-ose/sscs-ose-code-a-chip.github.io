"""Request-only view reuse; mutations and other requests must remain fresh."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import tempfile
import threading
import time
import unittest

from hullcirq.envelope_cache import envelope_read_scope, memoized_envelope, read_scope
from hullcirq.server import make_server, project_envelope
from hullcirq.store import ProjectStore
from hullcirq.verification import object_hash

ROOT = Path(__file__).resolve().parents[1]


class MutableReadFixture:
    def __init__(self):
        self.value, self.calls = 0, 0

    @memoized_envelope
    def envelope(self):
        self.calls += 1
        return {"value": self.value}


class EnvelopeCacheTests(unittest.TestCase):
    def test_internal_reads_share_one_view_but_new_project_call_observes_mutation(self):
        manager = MutableReadFixture()

        @envelope_read_scope
        def project():
            return manager.envelope(), manager.envelope()

        first, repeated = project()
        self.assertIs(first, repeated)
        self.assertEqual(manager.calls, 1)
        manager.value = 7
        self.assertEqual(project()[0], {"value": 7})
        self.assertEqual(manager.calls, 2)

    def test_direct_calls_never_cache_action_or_worker_reads(self):
        manager = MutableReadFixture()
        self.assertEqual(manager.envelope()["value"], 0)
        manager.value = 1
        self.assertEqual(manager.envelope()["value"], 1)
        self.assertEqual(manager.calls, 2)

    def test_exception_discards_the_failed_request_cache(self):
        manager = MutableReadFixture()
        with self.assertRaises(RuntimeError), read_scope():
            manager.envelope()
            raise RuntimeError("Software QA exception")
        manager.value = 2
        self.assertEqual(manager.envelope()["value"], 2)

    def test_nested_scopes_restore_the_outer_snapshot_without_leaking_inner_values(self):
        manager = MutableReadFixture()
        with read_scope():
            self.assertEqual(manager.envelope()["value"], 0)
            manager.value = 1
            with read_scope():
                self.assertEqual(manager.envelope()["value"], 1)
            self.assertEqual(manager.envelope()["value"], 0)
        self.assertEqual(manager.envelope()["value"], 1)

    def test_concurrent_worker_and_other_request_do_not_inherit_parent_cache(self):
        manager, observations = MutableReadFixture(), []
        with read_scope():
            self.assertEqual(manager.envelope()["value"], 0)
            def other_thread():
                manager.value = 3
                observations.append(manager.envelope()["value"])
                with read_scope():
                    observations.append(manager.envelope()["value"])
            worker = threading.Thread(target=other_thread)
            worker.start(); worker.join(timeout=2)
            self.assertFalse(worker.is_alive())
            self.assertEqual(observations, [3, 3])
            self.assertEqual(manager.envelope()["value"], 0)
        self.assertEqual(manager.envelope()["value"], 3)

    def test_real_terminal_proof_effective_values_are_identical_and_histories_unchanged(self):
        source = ROOT / "results/npu_scheduler_continuous_flow"
        names = ("state.json", "generation.json", "workflow.json", "implementation_specs.json")
        if not all((source / name).is_file() for name in names):
            self.skipTest("Preserved terminal proof is unavailable.")
        original = {name: (source / name).read_bytes() for name in names}
        scratch = ROOT / ".work/m2e/envelope-cache-qa"
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="proof-", dir=scratch) as name:
            directory = Path(name)
            for filename, value in original.items():
                (directory / filename).write_bytes(value)
            server = make_server("127.0.0.1", 0, ProjectStore(directory), ROOT)
            try:
                uncached_function = getattr(project_envelope, "__wrapped__", project_envelope)
                start = time.perf_counter(); uncached = uncached_function(server); uncached_seconds = time.perf_counter() - start
                start = time.perf_counter(); cached = envelope_read_scope(uncached_function)(server); cached_seconds = time.perf_counter() - start
                self.assertEqual(object_hash(cached), object_hash(uncached))
                self.assertEqual({node["node_id"] for node in cached["implementation_spec_nodes"] if node["accepted_spec_id"]}, {"node-scheduler", "node-pe"})
                self.assertEqual({filename: (directory / filename).read_bytes() for filename in names}, original)
                (scratch / "report.json").write_text(json.dumps({"record_kind": "read_scope_cache_software_QA", "validation_status": "Passed",
                    "uncached_seconds": uncached_seconds, "cached_seconds": cached_seconds, "identical_effective_object_hash": object_hash(cached),
                    "LLM_calls": 0, "EDA_calls": 0, "source_and_copied_histories_unchanged": True}, indent=2), encoding="utf-8")
            finally:
                if hasattr(server, "global_generation"):
                    server.global_generation.close()
                server.workflow.close(); server.generation.close(); server.server_close()
        self.assertEqual({name: (source / name).read_bytes() for name in names}, original)
