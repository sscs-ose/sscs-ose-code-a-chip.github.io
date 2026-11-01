"""Pure/software provenance checks. No live store, EDA, or model is used."""
import copy
import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from hullcirq.domain import DomainError, IMPLEMENTED_STAGES
from hullcirq.review_actor import VERSION, manual_review_fields, validate_review_actor
from hullcirq.store import ProjectStore, validate_policy_review
from hullcirq.generation import GenerationManager
from hullcirq.server import make_server
import test_adoption_policy as fixtures

PROJECT = Path(__file__).resolve().parents[1]


class ReviewActorTests(unittest.TestCase):
    def test_explicit_human_assistant_and_unknown_are_distinct(self):
        for operator, actor in ((None, "unspecified"), ({"actor": "human"}, "human"), ({"actor": "development_assistant"}, "development_assistant")):
            record = manual_review_fields(operator)
            self.assertEqual(record["actor"], actor)
            self.assertEqual(record["provenance"]["version"], VERSION)
            validate_policy_review(record, {})

    def test_explicit_review_cannot_impersonate_authorized_policy(self):
        for operator in ({"actor": "automation_policy"}, {"actor": "unspecified"}, {}, "human", {"actor": "human", "policy_id": "fake"}, {"actor": False}):
            with self.subTest(operator=operator), self.assertRaises(DomainError):
                manual_review_fields(operator)

    def test_legacy_human_is_admitted_without_relabel_or_mutation(self):
        original = {"actor": "human", "note": "Legacy label only"}
        record = copy.deepcopy(original)
        validate_policy_review(record, {})
        self.assertEqual(record, original)

    def test_unversioned_assistant_or_unknown_is_rejected(self):
        for actor in ("development_assistant", "unspecified", "local_llm", None):
            with self.subTest(actor=actor), self.assertRaises(DomainError):
                validate_review_actor({"actor": actor})

    def test_tampered_operator_declaration_is_rejected(self):
        original = manual_review_fields({"actor": "development_assistant"})
        for edit in (lambda r: r.update(actor="human"), lambda r: r["provenance"].update(version="future"),
                     lambda r: r["provenance"].update(declaration="authenticated"), lambda r: r["provenance"].update(extra=True)):
            record = copy.deepcopy(original); edit(record)
            with self.assertRaises(DomainError): validate_review_actor(record)

    def test_automation_still_requires_matching_user_authorization(self):
        with self.assertRaises(DomainError):
            validate_policy_review({"actor": "automation_policy", "decision": "accepted"}, {})
        with self.assertRaises(DomainError):
            validate_policy_review({"actor": "automation_policy", "decision": "accepted", "provenance": manual_review_fields({"actor": "human"})["provenance"]}, {})

    def test_s01_s03_review_and_restore_keep_declared_actor(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = ProjectStore(Path(temporary), PROJECT / "examples/m1_two_nodes.json")
            for stage, operator in zip(IMPLEMENTED_STAGES, (None, {"actor": "human"}, {"actor": "development_assistant"})):
                run = store.validate(stage, store.envelope()["revision"]["id"])["runs"][-1]
                store.review(run["id"], "accepted", "Software fixture review", operator=operator)
            before = store.state_path.read_bytes()
            loaded = ProjectStore(Path(temporary))
            self.assertEqual([r["actor"] for r in loaded.envelope()["reviews"]], ["unspecified", "human", "development_assistant"])
            self.assertEqual(store.state_path.read_bytes(), before)

    def test_invalid_declaration_does_not_mutate_saved_inputs(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = ProjectStore(Path(temporary))
            run = store.validate("global_settings", store.envelope()["revision"]["id"])["runs"][-1]
            before = store.state_path.read_bytes()
            with self.assertRaises(DomainError): store.review(run["id"], "accepted", "", operator={"actor": "automation_policy"})
            self.assertEqual(store.state_path.read_bytes(), before)

    def test_rtl_adoption_records_assistant_and_restore_preserves_it(self):
        case = fixtures.AdoptionPolicyTests(methodName="test_old_store_defaults_manual_without_startup_rewrite")
        case.setUp()
        try:
            manager = case.manager()
            job = case.generate(manager)
            # Authorized software-fixture policy is switched back to manual;
            # its original automatic decision remains intact in history.
            case.store.set_review_policy("manual", False, "Software fixture manual review", case.store.review_policy()["id"])
            old = copy.deepcopy(manager._state["reviews"])
            manager.review(job["id"], "accepted", "Explicit software-fixture review", operator={"actor": "development_assistant"})
            self.assertEqual(manager._state["reviews"][:-1], old)
            self.assertEqual(manager._state["reviews"][-1]["actor"], "development_assistant")
            manager.close()
            before = manager.path.read_bytes()
            loaded = GenerationManager(ProjectStore(case.directory))
            self.assertEqual(loaded._state["reviews"][-1]["actor"], "development_assistant")
            self.assertEqual(loaded.path.read_bytes(), before)
            loaded.close()
        finally: case.tearDown()


class ReviewOperatorHttpTests(unittest.TestCase):
    def test_all_ten_review_routes_forward_declaration_without_execution(self):
        with tempfile.TemporaryDirectory() as temporary:
            server = make_server("127.0.0.1", 0, ProjectStore(Path(temporary)))
            worker = threading.Thread(target=lambda: server.serve_forever(poll_interval=.01), daemon=True); worker.start()
            routes = (("/api/review", server.store, "run_id"), ("/api/generation/review", server.generation, "job_id"),
                      ("/api/workflow/review", server.workflow, "run_id"), ("/api/implementation-specs/review", server.implementation_specs, "spec_id"),
                      ("/api/global-generation/review", server.global_generation, "job_id"),
                      *((f"/api/{name.replace('_', '-')}/runs/software-fixture/review", getattr(server, name), None)
                        for name in ("global_workflow", "physical_workflow", "drc_workflow", "lvs_workflow", "postlayout_workflow")))
            try:
                for route, manager, identifier in routes:
                    with self.subTest(route=route), patch.object(manager, "review", return_value={}) as review, patch("hullcirq.server.project_envelope", return_value={"software_fixture": True}):
                        body = {"decision": "accepted", "note": "Software fixture only", "review_operator": {"actor": "development_assistant"}}
                        if identifier: body[identifier] = "software-fixture"
                        client = http.client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=5)
                        client.request("POST", route, json.dumps(body), {"Content-Type": "application/json"})
                        response = client.getresponse(); response.read(); client.close()
                        self.assertEqual(response.status, 200)
                        self.assertEqual(review.call_args.kwargs, {"operator": {"actor": "development_assistant"}})
            finally:
                server.shutdown(); server.server_close(); worker.join(2)

