"""S11 isolated software fixtures; no EDA/model calls or physical proof."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

PROJECT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PROJECT/"src"))
import test_global_workflow as fixtures
from hullcirq.domain import DomainError
from hullcirq.global_workflow import STAGES, source_bundle
from hullcirq.physical_workflow import (CLEANUP_BLOCKED, PhysicalWorkflowManager, REQUIRED_FILES,
    validate_artifact_manifest, validate_physical_proof, validate_revalidation_link, _file_ids, _required_files)
from hullcirq.verification import content_hash, object_hash


def fixture_validator(result,rtl,manifest,settings,configuration):
    """SOFTWARE QA only. Production must use the real fixed-adapter validator."""
    if result.get("software_qa_fixture") is not True or result.get("fixture_marker")!="explicitly_simulated_not_hardware_evidence":
        raise DomainError("fixture_proof_invalid","SOFTWARE QA fixture marker is missing")


def fixture_runner(rtl,manifest,settings,configuration,cancel_event=None):
    parent=Path(configuration["working_directory"]); parent.mkdir(parents=True,exist_ok=True)
    import tempfile
    folder=Path(tempfile.mkdtemp(prefix="physical-software-fixture-",dir=parent))
    artifacts=[]
    for artifact_id in sorted(REQUIRED_FILES):
        payload=("SOFTWARE QA ONLY: "+artifact_id+"\n").encode()
        (folder/artifact_id).write_bytes(payload)
        artifacts.append({"id":artifact_id,"kind":artifact_id,"relative_path":artifact_id,"bytes":len(payload),"sha256":hashlib.sha256(payload).hexdigest(),
            "content_type":"image/png" if artifact_id=="png" else "application/octet-stream" if artifact_id=="gds" else "text/plain; charset=utf-8"})
    return {"validation_status":"Passed","executed":True,"exit_code":0,"diagnostics":[],"commands":[{"executed":True,"status":"Completed","exit_code":0,"command":["SOFTWARE_QA_NO_EXECUTION"],"stdout":"SOFTWARE QA fixture\n","stderr":""}],
        "stdout":"SOFTWARE QA fixture\n","stderr":"","global_rtl_sha256":content_hash(rtl),"source_manifest_sha256":object_hash(manifest),
        "settings_sha256":object_hash(settings),"runtime_configuration_sha256":object_hash(configuration),"source_bundle":source_bundle(rtl,manifest),
        "artifacts_directory":str(folder),"artifacts":artifacts,"metrics":{"software_qa_fixture":True},
        "checks":{"source_identity":{"validation_status":"Passed"},"configuration":{"validation_status":"Passed"},
                  "routing":{"validation_status":"Passed","executed":True,"completed":True},"timing":{"validation_status":"Passed","executed":True}},
        "software_qa_fixture":True,"fixture_marker":"explicitly_simulated_not_hardware_evidence"}


class PhysicalWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.base=fixtures.GlobalWorkflowTests(methodName="runTest"); self.base.setUp(); self.addCleanup(self.base.doCleanups)
        self.store=self.base.store; self.global_manager=self.base.global_manager; self.global_workflow=self.base.manager
        self.synthesis=self.base.run_stage(); self.simulation=self.base.run_stage(STAGES[1],self.synthesis["id"])
        self.configuration={"version":"SOFTWARE_QA_ONLY","working_directory":str(self.base.base.directory/"physical-artifacts"),
            "pdk":"sky130A","cell_library":"sky130_fd_sc_hd","core_utilization_percent":35,"origin":"SOFTWARE_QA_PROFILE"}
        self.manager=self.new_manager(); self.addCleanup(self.manager.close)

    def new_manager(self,configuration=None,runner=fixture_runner,validator=fixture_validator):
        return PhysicalWorkflowManager(self.store,self.global_manager,self.global_workflow,self.configuration if configuration is None else configuration,runner,validator)

    def run_layout(self,runner=None):
        if runner is not None: self.manager._runner=runner
        self.manager.start("layout",self.base.job["id"],self.synthesis["id"],self.simulation["id"],self.base.job["revision_id"])
        self.manager._worker.join(20); self.assertFalse(self.manager._worker.is_alive())
        return self.manager.envelope()["physical_workflow"]["runs"][-1]

    def test_exact_inherited_sources_and_separate_profile_adopt_restart(self):
        before=[m.path.read_bytes() for m in (self.global_manager,self.global_workflow)]
        run=self.run_layout(); self.assertEqual(run["review_status"],"Accepted"); self.assertEqual(run["freshness"],"Current")
        self.assertEqual(run["evidence_kind"],"software_qa_fixture")
        self.assertEqual(run["settings"],self.store.envelope()["design"]["settings"])
        self.assertNotIn("core_utilization_percent",run["settings"])
        self.assertEqual(run["verification_plan"],self.base.job["context"]["verification_plan"])
        self.assertEqual(run["global_rtl"],self.base.job["rtl"])
        self.assertEqual(before,[m.path.read_bytes() for m in (self.global_manager,self.global_workflow)])
        reopened=self.new_manager(); self.addCleanup(reopened.close)
        self.assertEqual(reopened.run(run["id"])["review_status"],"Accepted")
        self.assertEqual(reopened.envelope()["physical_workflow"]["accepted_run_id"],run["id"])
        self.assertEqual(self.manager._state["reviews"][-1]["actor"],"automation_policy")

    def test_missing_runtime_or_wrong_source_cannot_start(self):
        manager=PhysicalWorkflowManager(self.store,self.global_manager,self.global_workflow); self.addCleanup(manager.close)
        self.assertFalse(manager.envelope()["physical_workflow"]["tool_ready"])
        with self.assertRaises(DomainError): manager.start("layout",self.base.job["id"],self.synthesis["id"],self.simulation["id"])
        for field in (0,1,2):
            ids=[self.base.job["id"],self.synthesis["id"],self.simulation["id"]]; ids[field]="wrong"
            with self.assertRaises(DomainError): self.manager.start("layout",*ids)
        self.assertFalse(self.manager._state["runs"])

    def test_s10_withdraw_and_restore_never_revives_physical_adoption(self):
        run=self.run_layout()
        self.global_workflow.review(self.simulation["id"],"changes_requested","SOFTWARE QA withdraw")
        self.assertEqual(self.manager.run(run["id"])["freshness"],"Stale")
        self.global_workflow.review(self.simulation["id"],"accepted","SOFTWARE QA explicit reaccept")
        self.assertEqual(self.manager.run(run["id"])["review_status"],"Awaiting Review")
        with self.assertRaises(DomainError): self.manager.review(run["id"],"accepted","")

    def test_runtime_profile_change_does_not_revive_old_layout(self):
        run=self.run_layout(); original=copy.deepcopy(self.manager.tool_configuration)
        self.manager.tool_configuration["core_utilization_percent"]=40
        self.assertEqual(self.manager.run(run["id"])["freshness"],"Stale")
        self.manager.tool_configuration=original
        self.assertEqual(self.manager.run(run["id"])["freshness"],"Stale")

    def test_during_execution_adoption_change_blocks_auto_acceptance(self):
        def changed(*args,**kwargs):
            result=fixture_runner(*args,**kwargs)
            self.global_workflow.review(self.simulation["id"],"changes_requested","SOFTWARE QA inflight withdrawal")
            return result
        run=self.run_layout(changed)
        self.assertEqual(run["validation_status"],"Passed"); self.assertEqual(run["review_status"],"Awaiting Review")
        self.assertEqual(run["freshness"],"Stale")
        self.assertTrue(any(d["code"]=="automatic_adoption_blocked" for d in run["diagnostics"]))

    def test_typed_proof_hash_commands_and_required_artifacts_rejected(self):
        run=self.run_layout()
        for mutation in (lambda r:r["checks"].update(exit_code=False),lambda r:r["checks"].update(settings_sha256="0"*64),
                lambda r:r["checks"]["checks"]["routing"].update(completed=False),lambda r:r["checks"]["checks"]["timing"].update(executed=False),
                lambda r:r["checks"]["commands"][0].update(exit_code=False),lambda r:r["checks"]["artifacts"].pop(),
                lambda r:r["checks"].update(cleanup_unresolved=True),
                lambda r:r["checks"].update(fixture_marker="fabricated")):
            bad=copy.deepcopy(run); mutation(bad)
            with self.subTest(mutation=mutation),self.assertRaises(DomainError): validate_physical_proof(bad,fixture_validator)

    def test_fixed_artifacts_download_and_tamper_detection(self):
        run=self.run_layout()
        payload,kind=self.manager.artifact_bytes(run["id"],"png")
        self.assertEqual(kind,"image/png"); self.assertIn(b"SOFTWARE QA ONLY",payload)
        self.assertEqual(self.manager.artifact(run["id"],"settings"),run["settings"])
        self.assertEqual(self.manager.artifact(run["id"],"rtl-top"),"SOFTWARE QA ONLY: rtl-top\n")
        with self.assertRaises(DomainError): self.manager.artifact_file(run["id"],"../../state.json")
        entry=self.manager.artifact_file(run["id"],"gds"); original=entry["path"].read_bytes(); entry["path"].write_bytes(original+b"changed")
        with self.assertRaises(DomainError): self.manager.artifact_bytes(run["id"],"gds")
        with self.assertRaises(DomainError): self.new_manager()
        entry["path"].write_bytes(original)

    def test_artifact_manifest_rejects_traversal_duplicate_and_boolean_size(self):
        run=self.run_layout()
        for mutation in (lambda r:r["artifacts"][0].update(relative_path="../state.json"),
                lambda r:r["artifacts"].append(copy.deepcopy(r["artifacts"][0])),lambda r:r["artifacts"][0].update(bytes=True),
                lambda r:r["artifacts"][0].update(relative_path="C:/outside"),lambda r:r["artifacts"][0].update(content_type="image/png\r\nInjected: yes")):
            result=copy.deepcopy(run["checks"]); mutation(result)
            with self.subTest(mutation=mutation),self.assertRaises(DomainError): validate_artifact_manifest(result,True)

    def test_artifact_manifest_derives_eleven_node_ids_from_immutable_source_bundle(self):
        node_ids=('npu2-control','npu2-buffer','npu2-scheduler','npu2-dispatcher','npu2-pe00','npu2-pe01',
                  'npu2-pe10','npu2-pe11','npu2-collector','npu2-post','npu2-fifo')
        bundle=[{'file':'candidate_top.v','module_name':'hullcirq_npu2_top','sha256':'0'*64},
                *({'file':node_id+'.v','module_name':'module_'+node_id.replace('-','_'),'sha256':'0'*64} for node_id in node_ids)]
        with tempfile.TemporaryDirectory(prefix='physical-dynamic-artifacts-software-qa-') as temporary:
            folder=Path(temporary);result={'source_bundle':bundle,'artifacts_directory':str(folder),'artifacts':[]}
            expected_rtl={'rtl-'+node_id for node_id in node_ids}
            self.assertEqual({identifier for identifier in _file_ids(result) if identifier.startswith('rtl-') and identifier!='rtl-top'},expected_rtl)
            self.assertEqual({identifier for identifier in _required_files(result) if identifier.startswith('rtl-') and identifier!='rtl-top'},expected_rtl)
            self.assertFalse(any(identifier.startswith('rtl-node-') for identifier in _file_ids(result)))
            for identifier in sorted(_required_files(result)):
                payload=('SOFTWARE QA ONLY: '+identifier+'\n').encode();path=folder/identifier;path.write_bytes(payload)
                result['artifacts'].append({'id':identifier,'kind':'physical','relative_path':identifier,'bytes':len(payload),
                    'sha256':hashlib.sha256(payload).hexdigest(),'content_type':'text/plain; charset=utf-8'})
            validate_artifact_manifest(result,True)
            for changed_file in ('../escape.v','nested/path.v','node.ok.v','Candidate_Top.v','top.v'):
                changed=copy.deepcopy(result);changed['source_bundle'][1]['file']=changed_file
                with self.subTest(changed_file=changed_file),self.assertRaises(DomainError):
                    validate_artifact_manifest(changed,True)
            duplicate=copy.deepcopy(result);duplicate['source_bundle'][2]['file']=duplicate['source_bundle'][1]['file']
            with self.assertRaises(DomainError):validate_artifact_manifest(duplicate,True)
            duplicate_case=copy.deepcopy(result)
            duplicate_case['source_bundle'][2]['file']=duplicate_case['source_bundle'][1]['file'][:-2].upper()+'.v'
            with self.assertRaises(DomainError):validate_artifact_manifest(duplicate_case,True)

    def test_rehashed_history_rejects_source_plan_profile_and_origin_tampering(self):
        self.run_layout(); original=self.manager.path.read_bytes()
        mutations=(lambda r:r["verification_plan"]["recipe"]["source_job"].update(k=4.0),
            lambda r:r["source_identity"].update(netlist_run_id="different"),lambda r:r["settings"].update(clock_period_ns=50.0),
            lambda r:r["runtime_configuration"].update(core_utilization_percent=99),lambda r:r.update(evidence_kind="trusted_fixed_tool_execution"))
        for mutation in mutations:
            state=json.loads(original); mutation(state["runs"][0]); run=state["runs"][0]
            run["record_hash"]=object_hash({k:v for k,v in run.items() if k!="record_hash"}); self.manager.path.write_text(json.dumps(state),encoding="utf-8")
            with self.subTest(mutation=mutation),self.assertRaises(DomainError): self.new_manager()
        self.manager.path.write_bytes(original)

    def test_unverified_pass_flag_retains_raw_failure_without_adoption(self):
        def rejected(*args,**kwargs):
            result=fixture_runner(*args,**kwargs); result["checks"]["routing"]["completed"]=False; return result
        run=self.run_layout(rejected)
        self.assertEqual(run["execution_status"],"Failed"); self.assertEqual(run["validation_status"],"Not Checked")
        self.assertEqual(run["review_status"],"Awaiting Review"); self.assertTrue(run["checks"]["commands"])
        self.assertFalse(self.manager._state["reviews"])

    def test_terminal_unresolved_cleanup_blocks_admission_and_policy_after_restart(self):
        calls=[]
        def unresolved(*args,**kwargs):
            calls.append("SOFTWARE QA only")
            result=fixture_runner(*args,**kwargs); result["cleanup_unresolved"]=True
            return result
        run=self.run_layout(unresolved)
        self.assertEqual(run["execution_status"],"Failed")
        self.assertEqual(run["validation_status"],"Not Checked")
        self.assertTrue(run["checks"]["cleanup_unresolved"])
        self.assertFalse(self.manager._state["reviews"])
        self.manager.close()
        reopened=self.new_manager(runner=unresolved); self.addCleanup(reopened.close)
        for manager in (self.manager,reopened):
            with self.subTest(restarted=manager is reopened):
                state=manager.envelope()["physical_workflow"]
                self.assertEqual(state["runs"][-1]["execution_status"],"Failed")
                self.assertTrue(manager.is_active())
                self.assertFalse(state["ready"])
                self.assertIn("termination is verified",state["blocked_reason"])
                with self.assertRaises(DomainError) as blocked:
                    manager.start("layout",self.base.job["id"],self.synthesis["id"],self.simulation["id"])
                self.assertEqual(blocked.exception.code,"physical_cleanup_unresolved")
                policy=self.store.review_policy()
                with self.assertRaises(DomainError) as adoption:
                    manager._review(run["id"],"accepted","SOFTWARE QA policy attempt",None,
                        "automation_policy",self.store.policy_provenance(policy["id"]))
                self.assertEqual(adoption.exception.code,"physical_cleanup_unresolved")
                self.assertEqual(len(manager._state["runs"]),1)
                self.assertFalse(manager._state["reviews"])
        self.assertEqual(calls,["SOFTWARE QA only"])

    def test_cancel_busy_and_restart_do_not_repeat_tools(self):
        entered=threading.Event(); release=threading.Event()
        def slow(*args,**kwargs): entered.set(); release.wait(5); return fixture_runner(*args,**kwargs)
        self.manager._runner=slow
        self.manager.start("layout",self.base.job["id"],self.synthesis["id"],self.simulation["id"]); self.assertTrue(entered.wait(5))
        identifier=self.manager._state["runs"][-1]["id"]
        with self.assertRaises(DomainError): self.manager.start("layout",self.base.job["id"],self.synthesis["id"],self.simulation["id"])
        self.manager.cancel(identifier); release.set(); self.manager._worker.join(10)
        run=self.manager.run(identifier); self.assertEqual(run["execution_status"],"Cancelled"); self.assertEqual(run["review_status"],"Awaiting Review")
        saved=json.loads(self.manager.path.read_text(encoding="utf-8")); saved["runs"][0]["execution_status"]="Running"
        saved["runs"][0]["record_hash"]=object_hash({k:v for k,v in saved["runs"][0].items() if k!="record_hash"})
        self.manager.path.write_text(json.dumps(saved),encoding="utf-8")
        with patch.object(self.manager,"_runner") as runner:
            reopened=self.new_manager(); self.addCleanup(reopened.close)
            restarted=reopened.run(identifier)
            self.assertEqual(restarted["execution_status"],"Interrupted")
            self.assertTrue(restarted["checks"]["cleanup_unresolved"])
            state=reopened.envelope()["physical_workflow"]
            self.assertFalse(state["ready"]); self.assertEqual(state["blocked_reason"],CLEANUP_BLOCKED)
            with self.assertRaises(DomainError) as blocked:
                reopened.start("layout",self.base.job["id"],self.synthesis["id"],self.simulation["id"])
            self.assertEqual(blocked.exception.code,"physical_cleanup_unresolved")
            self.assertEqual(len(reopened._state["runs"]),1); runner.assert_not_called()

    def test_backflow_target_and_failed_durable_review_preserve_original(self):
        run=self.run_layout()
        with self.assertRaises(DomainError): self.manager.review(run["id"],"return_to_stage","future","drc")
        original=self.manager.path.read_bytes()
        with patch("hullcirq.physical_workflow.os.replace",side_effect=OSError("SOFTWARE QA disk failure")):
            with self.assertRaises(OSError): self.manager.review(run["id"],"changes_requested","SOFTWARE QA save failure")
        self.assertEqual(self.manager.path.read_bytes(),original); self.assertEqual(self.manager.run(run["id"])["review_status"],"Accepted")
        self.manager.review(run["id"],"return_to_stage","SOFTWARE QA return","global_netlist_simulation")
        self.assertEqual(self.manager.run(run["id"])["review_status"],"Changes Requested")

    def prepare_saved_actual_double(self):
        """Explicit unit-only production-adapter doubles; never hardware evidence.

        The actual product rejects injected software fixtures. These patched
        module functions exercise that production branch without any tool call.
        All files still contain the conspicuous SOFTWARE QA fixture text.
        """
        self.manager.close()
        self.calls={"new_tool_double":0,"saved_recheck_double":0}
        def actual_adapter_double(*args,**kwargs):
            self.calls["new_tool_double"]+=1
            result=fixture_runner(*args,**kwargs)
            result.pop("software_qa_fixture")
            result.update(origin="trusted_fixed_tool_adapter",validation_status="Failed",
                diagnostics=[{"code":"software_QA_saved_parser_error","severity":"error","message":"Explicit software QA parser-failure double, not actual EDA evidence."}])
            result["commands"]=[{**result["commands"][0],"command":["SOFTWARE_QA_NO_EXECUTION",operation]} for operation in ("version","layout")]
            return result
        def actual_validator_double(result,*args):
            if result.get("fixture_marker")!="explicitly_simulated_not_hardware_evidence" or result.get("metrics",{}).get("software_qa_fixture") is not True:
                raise DomainError("software_QA_double_invalid","Explicit software QA double marker missing")
        def saved_recheck_double(rtl,manifest,settings,configuration,previous_result,prior_run_id,cancel_event=None):
            self.calls["saved_recheck_double"]+=1
            result=copy.deepcopy(previous_result)
            result.update(validation_status="Passed",diagnostics=[],execution_reused=True,revalidated_from_run_id=prior_run_id,
                previous_result_sha256=object_hash(previous_result),revalidation_tool_starts=0,revalidation_model_calls=0)
            return result
        self.saved_recheck_double=saved_recheck_double
        for target,value in (("hullcirq.physical_tools.run_layout",actual_adapter_double),("hullcirq.physical_tools.validate_layout_result",actual_validator_double),
                             ("hullcirq.physical_tools.revalidate_layout",saved_recheck_double)):
            started=patch(target,side_effect=value); started.start(); self.addCleanup(started.stop)
        self.manager=PhysicalWorkflowManager(self.store,self.global_manager,self.global_workflow,self.configuration)
        self.addCleanup(self.manager.close)
        self.run_layout()
        # Match the observed v1 parser-error run status while preserving this
        # unit-only original thereafter. No live project or EDA is involved.
        with self.manager.lock:
            original=self.manager._state["runs"][-1]
            original.update(execution_status="Failed",validation_status="Not Checked",
                error={"code":"software_QA_parser_error","message":"Explicit software QA only"})
            self.manager._persist()
            return copy.deepcopy(original)

    def recheck_saved(self,identifier):
        self.manager.revalidate(identifier)
        self.manager._worker.join(20); self.assertFalse(self.manager._worker.is_alive())
        return self.manager.envelope()["physical_workflow"]["runs"][-1]

    def test_saved_revalidation_appends_new_adopted_record_preserves_original_and_restarts(self):
        original=self.prepare_saved_actual_double()
        upstream=[m.path.read_bytes() for m in (self.global_manager,self.global_workflow)]
        result=self.recheck_saved(original["id"])
        self.assertEqual(result["execution_status"],"Completed"); self.assertEqual(result["validation_status"],"Passed")
        self.assertEqual(result["review_status"],"Accepted"); self.assertEqual(result["evidence_kind"],"trusted_saved_tool_revalidation")
        self.assertEqual(result["execution_kind"],"saved_outputs_no_new_tool_start")
        self.assertEqual(result["prior_record_sha256"],object_hash(original))
        self.assertEqual(result["previous_result_sha256"],object_hash(original["checks"]))
        self.assertEqual(original,self.manager._state["runs"][0])
        self.assertEqual(upstream,[m.path.read_bytes() for m in (self.global_manager,self.global_workflow)])
        validate_revalidation_link(result,original)
        reopened=PhysicalWorkflowManager(self.store,self.global_manager,self.global_workflow,self.configuration); self.addCleanup(reopened.close)
        self.assertEqual(reopened.run(result["id"])["review_status"],"Accepted")
        self.assertEqual(reopened._state["runs"][0],original)
        self.assertEqual(self.calls,{"new_tool_double":1,"saved_recheck_double":1})
        self.assertEqual(self.manager._state["reviews"][-1]["actor"],"automation_policy")

    def test_saved_revalidation_never_promotes_injected_fixtures(self):
        original=self.run_layout()
        before=self.manager.path.read_bytes()
        with self.assertRaises(DomainError) as error: self.manager.revalidate(original["id"])
        self.assertEqual(error.exception.code,"physical_fixture_rejected")
        self.assertEqual(before,self.manager.path.read_bytes())

    def test_saved_revalidation_requires_current_latest_exact_runtime_and_complete_actual_exits(self):
        original=self.prepare_saved_actual_double()
        for mutation in (lambda r:r["checks"].update(exit_code=False),lambda r:r["checks"]["commands"][0].update(exit_code=False),
                lambda r:r["checks"]["commands"].pop(),lambda r:r.update(execution_status="Interrupted"),
                lambda r:r["checks"].update(software_qa_fixture=True),lambda r:r["checks"].update(cleanup_unresolved=True)):
            self.manager._state["runs"][0]=copy.deepcopy(original); mutation(self.manager._state["runs"][0]); self.manager._persist()
            with self.subTest(mutation=mutation),self.assertRaises(DomainError): self.manager.revalidate(original["id"])
            self.assertEqual(len(self.manager._state["runs"]),1)
        self.manager._state["runs"][0]=copy.deepcopy(original); self.manager._persist()
        config=copy.deepcopy(self.manager.tool_configuration); self.manager.tool_configuration["core_utilization_percent"]=36
        with self.assertRaises(DomainError): self.manager.revalidate(original["id"])
        self.manager.tool_configuration=config
        with self.assertRaises(DomainError): self.manager.revalidate(original["id"])  # Epoch never revives.
        self.assertEqual(self.calls["saved_recheck_double"],0)

    def test_saved_revalidation_link_rejects_rehashed_prior_and_typed_report_metadata(self):
        original=self.prepare_saved_actual_double(); result=self.recheck_saved(original["id"])
        durable=self.manager.path.read_bytes()
        mutations=(lambda r:r.update(previous_result_sha256="0"*64),lambda r:r.update(prior_record_sha256="0"*64),
            lambda r:r.update(prior_run_id=r["id"]),lambda r:r["checks"].update(revalidation_tool_starts=False),
            lambda r:r["checks"].update(revalidation_model_calls=False),lambda r:r["checks"].update(execution_reused=1),
            lambda r:r["checks"].update(artifacts_directory="different"),lambda r:r["checks"]["commands"][0].update(stdout="modified"))
        for mutation in mutations:
            state=json.loads(durable); child=state["runs"][-1]; mutation(child)
            child["record_hash"]=object_hash({k:v for k,v in child.items() if k!="record_hash"}); self.manager.path.write_text(json.dumps(state),encoding="utf-8")
            with self.subTest(mutation=mutation),self.assertRaises(DomainError):
                PhysicalWorkflowManager(self.store,self.global_manager,self.global_workflow,self.configuration)
        state=json.loads(durable); state["runs"][0]["error"]["message"]="changed prior failure"
        state["runs"][0]["record_hash"]=object_hash({k:v for k,v in state["runs"][0].items() if k!="record_hash"})
        self.manager.path.write_text(json.dumps(state),encoding="utf-8")
        with self.assertRaises(DomainError): PhysicalWorkflowManager(self.store,self.global_manager,self.global_workflow,self.configuration)
        self.manager.path.write_bytes(durable)
        with self.assertRaises(DomainError): self.manager.revalidate(original["id"])
        with self.assertRaises(DomainError): self.manager.revalidate(result["id"])

    def test_malformed_revalidation_report_stays_failed_debug_evidence_without_adoption(self):
        original=self.prepare_saved_actual_double()
        def malformed(*args,**kwargs):
            result=self.saved_recheck_double(*args,**kwargs); result["revalidation_tool_starts"]=False; return result
        with patch("hullcirq.physical_tools.revalidate_layout",side_effect=malformed): result=self.recheck_saved(original["id"])
        self.assertEqual(result["execution_status"],"Failed"); self.assertEqual(result["checks"],{})
        self.assertIs(result["revalidation_rejected_report"]["revalidation_tool_starts"],False)
        self.assertEqual(result["review_status"],"Awaiting Review"); self.assertFalse(self.manager._state["reviews"])
        reopened=PhysicalWorkflowManager(self.store,self.global_manager,self.global_workflow,self.configuration); self.addCleanup(reopened.close)
        self.assertEqual(reopened._state["runs"][0],original)

    def test_saved_revalidation_cancel_and_busy(self):
        original=self.prepare_saved_actual_double(); entered=threading.Event(); release=threading.Event()
        def slow(*args,**kwargs):
            entered.set(); release.wait(5); return self.saved_recheck_double(*args,**kwargs)
        with patch("hullcirq.physical_tools.revalidate_layout",side_effect=slow):
            self.manager.revalidate(original["id"]); self.assertTrue(entered.wait(5))
            identifier=self.manager._state["runs"][-1]["id"]
            with self.assertRaises(DomainError): self.manager.revalidate(original["id"])
            self.manager.cancel(identifier); release.set(); self.manager._worker.join(20)
        self.assertEqual(self.manager.run(identifier)["execution_status"],"Cancelled")
        self.assertFalse(self.manager._state["reviews"]); self.assertEqual(original,self.manager._state["runs"][0])

    def test_saved_revalidation_inflight_source_withdrawal_blocks_adoption(self):
        original=self.prepare_saved_actual_double()
        def source_changed(*args,**kwargs):
            result=self.saved_recheck_double(*args,**kwargs)
            self.global_workflow.review(self.simulation["id"],"changes_requested","SOFTWARE QA inflight saved-output source withdrawal")
            return result
        with patch("hullcirq.physical_tools.revalidate_layout",side_effect=source_changed): result=self.recheck_saved(original["id"])
        self.assertEqual(result["validation_status"],"Passed")
        self.assertEqual(result["freshness"],"Stale"); self.assertEqual(result["review_status"],"Awaiting Review")
        self.assertTrue(any(d["code"]=="automatic_adoption_blocked" for d in result["diagnostics"]))
        self.assertEqual(original,self.manager._state["runs"][0])

    def test_saved_revalidation_durable_admission_failure_preserves_original(self):
        original=self.prepare_saved_actual_double(); durable=self.manager.path.read_bytes()
        with patch("hullcirq.physical_workflow.os.replace",side_effect=OSError("SOFTWARE QA admission save failure")):
            with self.assertRaises(OSError): self.manager.revalidate(original["id"])
        self.assertEqual(durable,self.manager.path.read_bytes()); self.assertEqual(self.manager._state["runs"],[original])
        self.assertEqual(self.calls["saved_recheck_double"],0)


if __name__=="__main__": unittest.main()
