"""GET source observation is ephemeral; explicit actions retain durable guards.

All circuit results below are isolated software fixtures, never live EDA.
"""
import copy
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest

import test_postlayout_workflow as fixtures
from hullcirq.domain import DomainError
from hullcirq.generation import GenerationManager
from hullcirq.implementation_specs import ImplementationSpecManager
from hullcirq.observation import (ObservedState, persist_observation,
                                  readonly_observation_scope, require_durable_write)
from hullcirq.server import RequestHandler, project_envelope
from hullcirq.store import ProjectStore
from hullcirq.workflow import WorkflowManager
from hullcirq.workspace_server import MANAGERS, build_context, close_context


def get_view(action):
    """Exercise the actual GET entry scope without opening a network socket."""
    return RequestHandler.do_GET(SimpleNamespace(
        path="/api/project", server=SimpleNamespace(context_lock=threading.RLock()), _do_GET=action))


def files(managers):
    return {m.path: m.path.read_bytes() if m.path.exists() else None for m in managers}


class ObservationScopeTests(unittest.TestCase):
    def test_only_metadata_is_copied_nested_scope_and_exception_are_isolated(self):
        manager = ObservedState()
        manager.lock = threading.RLock()
        manager._state = {"source_key": "old", "source_epoch": 2,
                          "source_transitions": [{"epoch": 2}],
                          "node_epochs": {"node": 4}, "jobs": [{"rtl": "unchanged"}]}
        durable = manager._state
        with self.assertRaisesRegex(RuntimeError, "fixture exception"):
            with readonly_observation_scope():
                projected = manager._state
                self.assertIsNot(projected, durable)
                self.assertIs(projected["jobs"], durable["jobs"])
                projected["node_epochs"]["node"] = 99
                projected["source_transitions"].append({"epoch": 3})
                with readonly_observation_scope():
                    self.assertIs(manager._state, projected)
                raise RuntimeError("fixture exception")
        self.assertIs(manager._state, durable)
        self.assertEqual(durable["node_epochs"], {"node": 4})
        self.assertEqual(durable["source_transitions"], [{"epoch": 2}])

    def test_worker_thread_has_authoritative_state_and_can_persist(self):
        class Manager(ObservedState):
            def _persist(self):
                require_durable_write()
                self.writes += 1
        manager = Manager()
        manager.lock = threading.RLock()
        manager._state = {"source_epoch": 1}
        manager.writes = 0
        errors = []
        def worker():
            try:
                manager._state["source_epoch"] += 1
                persist_observation(manager)
            except BaseException as error:
                errors.append(error)
        with readonly_observation_scope():
            manager._state["source_epoch"] = 101
            persist_observation(manager)
            self.assertEqual(manager.writes, 0)
            with self.assertRaises(DomainError) as caught:
                manager._persist()
            self.assertEqual(caught.exception.code, "read_only_observation_violation")
            with self.assertRaises(DomainError):
                manager._state = {"source_epoch": 555}
            thread = threading.Thread(target=worker)
            thread.start(); thread.join(5)
            self.assertFalse(thread.is_alive())
            self.assertEqual(manager._state["source_epoch"], 101)
        self.assertEqual(errors, [])
        self.assertEqual(manager._state["source_epoch"], 2)
        self.assertEqual(manager.writes, 1)


class LocalObservationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.store = ProjectStore(Path(self.temp.name) / "project")
        generation = GenerationManager(self.store)
        workflow = WorkflowManager(self.store, generation)
        specs = ImplementationSpecManager(self.store, generation, workflow)
        self.managers = [generation, workflow, specs]
        for manager in self.managers:
            if hasattr(manager, "close"):
                self.addCleanup(manager.close)

    def test_local_source_change_gets_do_not_mutate_states_or_files(self):
        before = copy.deepcopy([m._state for m in self.managers])
        committed = copy.deepcopy([m._committed for m in self.managers])
        current = self.store.envelope()
        changed = copy.deepcopy(current["design"])
        changed["nodes"][0]["behavior"] += " SOFTWARE QA changed source"
        self.store.save(changed, current["revision"]["id"])
        saved = files(self.managers)
        with readonly_observation_scope():
            for manager in self.managers:
                with self.assertRaises(DomainError) as caught:
                    manager._persist()
                self.assertEqual(caught.exception.code, "read_only_observation_violation")
        for _ in range(3):
            def inspect():
                for manager in self.managers:
                    manager.envelope()
                    self.assertGreater(manager._state["node_epochs"]["node-producer"],
                                       before[self.managers.index(manager)]["node_epochs"]["node-producer"])
            get_view(inspect)
            self.assertEqual([m._state for m in self.managers], before)
            self.assertEqual([m._committed for m in self.managers], committed)
            self.assertEqual(files(self.managers), saved)
        # The same observations outside a GET remain durable.
        for manager in self.managers:
            manager.observe_design()
        self.assertNotEqual([m._state for m in self.managers], before)
        self.assertNotEqual(files(self.managers), saved)

    def test_complete_project_get_keeps_all_real_manager_states_and_files_unchanged(self):
        context = build_context(self.store, (None,) * 6)
        self.addCleanup(close_context, context)
        managers = [getattr(context, name) for name in MANAGERS]
        before = copy.deepcopy([m._state for m in managers])
        current = self.store.envelope()
        changed = copy.deepcopy(current["design"])
        changed["nodes"][0]["behavior"] += " SOFTWARE QA new saved input"
        self.store.save(changed, current["revision"]["id"])
        directory = self.store.path
        saved = {p.name: p.read_bytes() for p in directory.glob("*.json")}
        for _ in range(3):
            get_view(lambda: project_envelope(context))
            self.assertEqual([m._state for m in managers], before)
            self.assertEqual({p.name: p.read_bytes() for p in directory.glob("*.json")}, saved)


class ChainObservationTests(unittest.TestCase):
    def setUp(self):
        self.base = fixtures.PostLayoutWorkflowTests("runTest")
        self.base.setUp(); self.addCleanup(self.base.doCleanups)
        self.base.run_postlayout()
        global_base = self.base.base.base.base.base
        self.managers = [global_base.global_manager, global_base.manager,
                         self.base.physical, self.base.drc, self.base.lvs, self.base.manager]
        self.store = self.base.store

    def change_design(self):
        current = self.store.envelope()
        changed = copy.deepcopy(current["design"])
        changed["nodes"][0]["behavior"] += " SOFTWARE QA semantic change"
        self.store.save(changed, current["revision"]["id"])
        return current["design"]

    def test_all_durable_writers_refuse_get_before_mutating_record_checksums(self):
        before = copy.deepcopy([m._state for m in self.managers])
        saved = files(self.managers)
        with readonly_observation_scope():
            for manager in self.managers:
                with self.subTest(manager=type(manager).__name__), self.assertRaises(DomainError) as caught:
                    manager._persist()
                self.assertEqual(caught.exception.code, "read_only_observation_violation")
        self.assertEqual([m._state for m in self.managers], before)
        self.assertEqual(files(self.managers), saved)

    def test_all_downstream_gets_derive_stale_without_any_memory_or_file_edits(self):
        before = copy.deepcopy([m._state for m in self.managers])
        committed = copy.deepcopy([m._committed for m in self.managers])
        self.change_design()
        saved = files(self.managers)
        def inspect():
            for manager in self.managers:
                data = next(iter(manager.envelope().values()))
                self.assertFalse(data["ready"])
                record = data.get("jobs", data.get("runs"))[-1]
                self.assertEqual(record["freshness"], "Stale")
                self.assertEqual(record["review_status"], "Awaiting Review")
                # Individual record and artifact GET guards use the same view.
                if hasattr(manager, "job"):
                    manager.job(record["id"])
                else:
                    manager.run(record["id"])
        for _ in range(3):
            get_view(inspect)
            self.assertEqual([m._state for m in self.managers], before)
            self.assertEqual([m._committed for m in self.managers], committed)
            self.assertEqual(files(self.managers), saved)
        def fail():
            inspect()
            raise RuntimeError("fixture response failure")
        with self.assertRaises(RuntimeError):
            get_view(fail)
        self.assertEqual([m._state for m in self.managers], before)
        self.assertEqual(files(self.managers), saved)

    def test_explicit_observation_persists_and_reversion_cannot_revive_adoption(self):
        original = self.change_design()
        saved = files(self.managers)
        for manager in self.managers:
            manager.envelope()  # Explicit Save/Run response, not GET scope.
        self.assertNotEqual(files(self.managers), saved)
        epoch = [m._state["source_epoch"] for m in self.managers]
        current = self.store.envelope()
        self.store.save(original, current["revision"]["id"])
        for manager in self.managers:
            data = next(iter(manager.envelope().values()))
            record = data.get("jobs", data.get("runs"))[-1]
            self.assertNotEqual(record["review_status"], "Accepted")
        self.assertGreater(self.managers[0]._state["source_epoch"], epoch[0])
        saved = files(self.managers)
        get_view(lambda: [m.envelope() for m in self.managers])
        self.assertEqual(files(self.managers), saved)


if __name__ == "__main__":
    unittest.main()
