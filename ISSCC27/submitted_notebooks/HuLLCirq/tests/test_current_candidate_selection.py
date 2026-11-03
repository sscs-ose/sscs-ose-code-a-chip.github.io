"""Selection guards use live source identities without rendering full histories."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch, Mock

PROJECT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PROJECT/"src"))
from hullcirq.generation import GenerationManager
from hullcirq.workflow import WorkflowManager
from hullcirq.store import ProjectStore
from hullcirq.domain import IMPLEMENTED_STAGES
from hullcirq.context import node_fingerprint
from hullcirq.npu2_control_verification import build_control_plan
from test_adoption_policy import design_fixture, software_profile, format_fixture


class CurrentCandidateSelectionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=PROJECT/".work")
        self.addCleanup(self.tmp.cleanup)
        self.store=ProjectStore(self.tmp.name)
        self.store.save(design_fixture(False),self.store.envelope()["revision"]["id"])
        self.store.set_review_policy("accept_on_pass",True,"isolated software QA",self.store.review_policy()["id"])
        for stage in IMPLEMENTED_STAGES: self.store.validate(stage,self.store.envelope()["revision"]["id"])
        self.manager=GenerationManager(self.store); self.addCleanup(self.manager.close)
        self.manager.save_profile(software_profile())
        revision=self.store.envelope()["revision"]["id"]
        preview=self.manager.preview("node-producer",revision)
        rtl=preview["requested_module_header"]+"endmodule\n"
        response={"execution_status":"Completed","raw_content":"\x60\x60\x60verilog\n"+rtl+"\x60\x60\x60","error":None,"finish_reason":"stop"}
        with patch("hullcirq.generation.ChatCompletionsClient") as provider, patch("hullcirq.generation.check_rtl",side_effect=format_fixture):
            provider.return_value.generate.return_value=response
            self.manager.start("node-producer",revision,preview["context_id"],preview["profile_revision_id"])
            self.manager._worker.join(10)
            self.assertFalse(self.manager._worker.is_alive())
        self.job=self.manager._state["jobs"][-1]
        self.assertEqual(self.job["review_status"],"Accepted")

    def full_selection(self):
        nodes=self.manager.envelope()["generation"]["nodes"]
        return {node["node_id"]:node.get("accepted_job_id") if node.get("accepted_job_id")==node.get("latest_job_id") else None for node in nodes}

    def test_matches_full_envelope_under_latest_review_and_epoch_changes(self):
        self.assertEqual(self.manager.current_candidate_selection(),self.full_selection())
        for status in ("Awaiting Review","Changes Requested","Accepted"):
            self.job["review_status"]=status
            self.assertEqual(self.manager.current_candidate_selection(),self.full_selection())
        self.job["acceptance_epoch"]-=1
        self.assertEqual(self.manager.current_candidate_selection(),self.full_selection())
        self.assertIsNone(self.manager.current_candidate_selection()["node-producer"])

    def test_new_unaccepted_candidate_supersedes_older_accepted_candidate(self):
        other=copy.deepcopy(self.job); other.update(id="newer-unreviewed-fixture",review_status="Awaiting Review")
        self.manager._state["jobs"].append(other)
        self.assertEqual(self.manager.current_candidate_selection(),self.full_selection())
        self.assertIsNone(self.manager.current_candidate_selection()["node-producer"])
        other["review_status"]="Accepted"
        self.assertEqual(self.manager.current_candidate_selection()["node-producer"],other["id"])

    def test_guard_never_decorates_or_estimates_full_provider_messages(self):
        before=self.manager.path.read_bytes()
        with patch.object(self.manager,"envelope",side_effect=AssertionError("full history rendering forbidden")), patch.object(self.manager,"_decorate",side_effect=AssertionError("candidate GUI decoration forbidden")), patch("hullcirq.generation.estimate_message_input",side_effect=AssertionError("token accounting forbidden")):
            self.assertEqual(self.manager.current_candidate_selection()["node-producer"],self.job["id"])
        self.assertEqual(self.manager.path.read_bytes(),before)

    def test_each_call_observes_current_input_and_does_not_cache_selection(self):
        self.assertEqual(self.manager.current_candidate_selection()["node-producer"],self.job["id"])
        changed=copy.deepcopy(self.store.envelope()["design"])
        changed["nodes"][0]["behavior"]+=" changed isolated requirement"
        self.store.save(changed,self.store.envelope()["revision"]["id"])
        self.assertIsNone(self.manager.current_candidate_selection()["node-producer"])
        self.assertEqual(self.manager.current_candidate_selection(),self.full_selection())

    def test_strict_live_contract_type_check_with_normalized_hash_is_preserved(self):
        design=json.loads((PROJECT/"examples/npu_2x2_explicit_project.json").read_text(encoding="utf-8"))
        plan=build_control_plan(design,"npu2-control")
        original_fingerprint=node_fingerprint(design,"npu2-control")
        manager=GenerationManager.__new__(GenerationManager)
        manager.lock=threading.RLock(); manager._persist=Mock()
        source={"design":design,"revision":{"id":"software-source"}}
        manager.store=Mock(); manager.store.envelope.side_effect=lambda:source
        manager._state={"node_inputs":{node["id"]:node_fingerprint(design,node["id"]) for node in design["nodes"]},"node_epochs":{node["id"]:0 for node in design["nodes"]},"jobs":[{"id":"strict-current-control","node_id":"npu2-control","input_hash":original_fingerprint,"review_status":"Accepted","acceptance_epoch":0,"verification_plan":plan}]}
        self.assertEqual(manager.current_candidate_selection()["npu2-control"],"strict-current-control")
        design["verification_jobs"][0]["bias"][0]=3.0
        self.assertEqual(node_fingerprint(design,"npu2-control"),original_fingerprint)
        self.assertIsNone(manager.current_candidate_selection()["npu2-control"])
        self.assertEqual(manager._state["node_epochs"]["npu2-control"],1)
        design["verification_jobs"][0]["bias"][0]=3
        self.assertIsNone(manager.current_candidate_selection()["npu2-control"])

    def test_workflow_uses_scalar_guard_with_legacy_fixture_fallback(self):
        workflow=WorkflowManager.__new__(WorkflowManager)
        workflow.generation=self.manager
        with patch.object(self.manager,"envelope",side_effect=AssertionError("full envelope forbidden")):
            self.assertEqual(workflow._selected_candidates()["node-producer"],self.job["id"])
        legacy=Mock(spec=["envelope"])
        legacy.envelope.return_value={"generation":{"nodes":[{"node_id":"a","accepted_job_id":"x","latest_job_id":"x"},{"node_id":"b","accepted_job_id":"y","latest_job_id":"z"}]}}
        workflow.generation=legacy
        self.assertEqual(workflow._selected_candidates(),{"a":"x","b":None})


if __name__=="__main__": unittest.main()
