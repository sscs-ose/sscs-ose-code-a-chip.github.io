"""Isolated S08 software QA. Fixture sources are never demonstration evidence.

Model transport and successful proofs below are explicitly simulated software
fixtures. Optional Icarus cases execute only these isolated fixtures, never the
live project, its adopted node sources, or a real model.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))
from hullcirq.context import node_fingerprint, physical_interface
from hullcirq.domain import DomainError, IMPLEMENTED_STAGES
from hullcirq.global_generation import (GlobalGenerationManager, NODE_IDS, build_global_plan,
    check_global_rtl, fixed_global_commands, integration_messages, load_words, matrix_results,
    original_job, top_interface, validate_global_plan, compiler_public_hierarchy,
    instrument_public_testbench, public_transfer_counts)
from hullcirq.provider import validate_profile
from hullcirq.store import ProjectStore, strict_loads
from hullcirq.verification import content_hash, object_hash, trusted_command, execute_fixed, _wsl_path

SOFTWARE_TOP_BODY="""// Handwritten SOFTWARE QA top; never a model/submission artifact.
wire [133:0] sc; wire scv,scr; wire [128:0] pc; wire pcv,pcr; wire transfer;
hullcirq_control u_control(.clk(clk),.rst(rst),.config_data(config_data),.config_data_valid(config_data_valid),.config_data_ready(config_data_ready),.schedule_config(sc),.schedule_config_valid(scv),.schedule_config_ready(scr),.post_config(pc),.post_config_valid(pcv),.post_config_ready(pcr),.output_transfer(transfer),.busy(busy),.job_done(job_done));
wire [15:0] req,resp,pair; wire reqv,reqr,respv,respr,pairv,pairr,lr;
wire [5:0] meta; wire clear,dispatch_done;
assign load_data_ready=lr&&!busy;
hullcirq_buffer u_buffer(.clk(clk),.rst(rst),.load_data(load_data),.load_data_valid(load_data_valid&&!busy),.load_data_ready(lr),.read_request(req),.read_request_valid(reqv),.read_request_ready(reqr),.read_response(resp),.read_response_valid(respv),.read_response_ready(respr));
hullcirq_scheduler u_scheduler(.clk(clk),.rst(rst),.schedule_config(sc),.schedule_config_valid(scv),.schedule_config_ready(scr),.read_request(req),.read_request_valid(reqv),.read_request_ready(reqr),.read_response(resp),.read_response_valid(respv),.read_response_ready(respr),.pair_data(pair),.pair_data_valid(pairv),.pair_data_ready(pairr),.pair_meta(meta),.pe_clear(clear),.schedule_done(dispatch_done));
wire [15:0] pir,pov,por; wire signed [31:0] pod [0:15];
reg pending; reg [3:0] held_lane; reg held_last;
wire signed [31:0] acc=pod[held_lane]; wire av=pending&&held_last&&pov[held_lane]; wire ar;
assign pairr=!pending&&pir[meta[3:0]];
always @(posedge clk) begin
 if(rst||clear) begin pending<=0;held_lane<=0;held_last<=0;end
 else if(pending&&pov[held_lane]&&por[held_lane]) pending<=0;
 else if(pairv&&pairr) begin pending<=1;held_lane<=meta[3:0];held_last<=meta[5];end
end
genvar i;
generate for(i=0;i<16;i=i+1) begin: g
 assign por[i]=pending&&(held_lane==i)&&(!held_last||ar);
 hullcirq_pe u_pe(.clk(clk),.rst(rst||clear),.pair_data(pair),.pair_data_valid(pairv&&!pending&&(meta[3:0]==i)),.pair_data_ready(pir[i]),.acc_data(pod[i]),.acc_data_valid(pov[i]),.acc_data_ready(por[i]));
end endgenerate
wire signed [31:0] result; wire rv,rr;
hullcirq_post u_post(.clk(clk),.rst(rst),.acc_data(acc),.acc_data_valid(av),.acc_data_ready(ar),.post_config(pc),.post_config_valid(pcv),.post_config_ready(pcr),.result_data(result),.result_data_valid(rv),.result_data_ready(rr));
hullcirq_fifo u_fifo(.clk(clk),.rst(rst),.result_data(result),.result_data_valid(rv),.result_data_ready(rr),.output_data(output_data),.output_data_valid(output_data_valid),.output_data_ready(output_data_ready),.output_transfer(transfer));
endmodule
"""


def header(interface):
    return "module " + interface["module_name"] + "(" + ",".join(
        p["direction"] + (" signed" if p["signed"] else "") +
        (f" [{p['width']-1}:0]" if p["width"] > 1 else "") + " " + p["name"] for p in interface["ports"]) + ");\n"


class Sources:
    """Minimal trusted-manager doubles; no node proof is claimed by this QA."""
    def __init__(self, store):
        current = store.envelope(); design = current["design"]; revision = current["revision"]
        self.profile = {"revision_id": "software-profile", "profile": validate_profile({
            "id": "software-fixture", "name": "S08 software QA only", "execution_location": "Local",
            "base_url": "http://127.0.0.1:9/v1", "model": "no-actual-model", "context_window": 131072,
            "reasoning_effort": "none"})}
        self.generation = SimpleNamespace(lock=threading.RLock(), observe_design=lambda: None,
            _state={"jobs": [], "reviews": [], "node_epochs": {n:1 for n in NODE_IDS}, "profiles": [self.profile]})
        self.workflow = SimpleNamespace(lock=threading.RLock(), observe_design=lambda: None,
            _state={"runs": [], "reviews": [], "node_epochs": {n:1 for n in NODE_IDS}})
        self.specs = SimpleNamespace(lock=threading.RLock(), observe_design=lambda: None,
            _state={"specs": [], "reviews": [], "node_epochs": {n:1 for n in NODE_IDS}})
        for node_id in NODE_IDS:
            node = next(n for n in design["nodes"] if n["id"] == node_id)
            common = {"node_id": node_id, "revision_id": revision["id"], "input_hash": node_fingerprint(design,node_id),
                "execution_status": "Completed", "validation_status": "Passed", "review_status": "Accepted",
                "acceptance_epoch": 1, "record_hash": "software-fixture-not-node-proof"}
            rtl = header(physical_interface(design,node)) + "// SOFTWARE QA ONLY\nendmodule\n"
            candidate = dict(common,id="candidate-"+node_id,rtl=rtl,rtl_sha256=content_hash(rtl))
            synthesis = dict(common,id="synthesis-"+node_id,stage_id="local_synthesis",candidate_id=candidate["id"],prior_run_id=None)
            netlist = dict(common,id="netlist-"+node_id,stage_id="local_netlist_simulation",candidate_id=candidate["id"],prior_run_id=synthesis["id"])
            self.generation._state["jobs"].append(candidate)
            self.workflow._state["runs"].extend([synthesis,netlist])
            adoptions=[]
            for kind,record,manager,key in (("candidate",candidate,self.generation,"job_id"),
                    ("synthesis",synthesis,self.workflow,"run_id"),("netlist_simulation",netlist,self.workflow,"run_id")):
                review={"id":"review-"+record["id"],key:record["id"],"decision":"accepted","actor":"human","note":"SOFTWARE QA"}
                manager._state["reviews"].append(review); adoptions.append({"kind":kind,"review":copy.deepcopy(review)})
            specification={"original_requirements":{"verification_jobs":copy.deepcopy(design["verification_jobs"])},
                "lineage":{"synthesis_run_id":synthesis["id"]},"software_qa_fixture":True}
            spec=dict(common,id="spec-"+node_id,candidate_id=candidate["id"],source_run_id=netlist["id"],
                design_hash=revision["semantic_hash"],specification=specification,specification_sha256=object_hash(specification),source_adoptions=adoptions)
            self.specs._state["specs"].append(spec)
            self.specs._state["reviews"].append({"id":"review-"+spec["id"],"spec_id":spec["id"],"decision":"accepted","actor":"human","note":"SOFTWARE QA"})
        self.generation._stored_job=lambda i: next(j for j in self.generation._state["jobs"] if j["id"]==i)
        self.generation._require_profile=lambda revision=None: self.profile
        self.workflow._run=lambda i: next(j for j in self.workflow._state["runs"] if j["id"]==i)
        self.specs._spec=lambda i: next(j for j in self.specs._state["specs"] if j["id"]==i)


def fixture_proof(rtl, manifest, plan, compiler, cancel=None):
    """Fake executed records test persistence/adoption, never hardware proof."""
    directory=Path(compiler["working_directory"]) / "hullcirq-global-software-qa"
    outputs=[{"index":i,"value":v,"cycle":100+i*2} for i,v in enumerate(plan["recipe"]["expected_outputs"])]
    stdout="".join(f"HULLCIRQ_OUTPUT index={x['index']} value={x['value']} cycle={x['cycle']}\n" for x in outputs)
    stream_records=[{"stream":name,"transfers":count} for name,count in public_transfer_counts(plan).items()]
    pe_records=[{"instance":i,"lane":i,"inputs":plan["recipe"]["source_job"]["k"],"outputs":plan["recipe"]["source_job"]["k"]} for i in range(16)]
    stdout+="".join(f"HULLCIRQ_PUBLIC stream={r['stream']} transfers={r['transfers']}\n" for r in stream_records)
    stdout+="".join(f"HULLCIRQ_PE instance={r['instance']} lane={r['lane']} inputs={r['inputs']} outputs={r['outputs']}\n" for r in pe_records)
    stdout+=f"HULLCIRQ_PUBLIC_PASS vector_hash={plan['public_boundary_vector_hash']}\n"
    stdout+=f"HULLCIRQ_GLOBAL_PASS outputs=16 vector_hash={plan['vector_hash']}\n"
    scopes=['S_tb .scope module, "hullcirq_global_tb" "hullcirq_global_tb" 1 1;',
            'S_dut .scope module, "dut" "hullcirq_npu" 1 1, 2 1 0, S_tb;']
    for ni,entry in enumerate(manifest["nodes"]):
        for pi in range(16 if entry["node_id"]=="node-pe" else 1):
            scopes.append(f'S_n{ni}p{pi} .scope module, "u_{ni}_{pi}" "{entry["module_name"]}" 1 1, 2 1 0, S_dut;')
    hierarchy=compiler_public_hierarchy(scopes,manifest)
    instrumented,monitor=instrument_public_testbench(plan,hierarchy)
    commands=[{"executed":True,"status":"Completed","exit_code":0,"command":c,"stdout":stdout if i==3 else "SOFTWARE QA\n","stderr":""}
              for i,c in enumerate(fixed_global_commands(compiler,manifest,directory))]
    return {"validation_status":"Passed","executed":True,"exit_code":0,"rtl_sha256":content_hash(rtl),
        "source_manifest_sha256":object_hash(manifest),"vector_hash":plan["vector_hash"],"testbench_sha256":plan["testbench_sha256"],
        "tool_configuration":copy.deepcopy(compiler),"artifacts_directory":str(directory),"stdout":stdout,"stderr":"",
        "actual_output_transfers":outputs,"commands":commands,"diagnostics":[],
        "checks":{k:{"validation_status":"Passed"} for k in ("interface","elaboration","functional","public_boundary")},
        "public_port_hierarchy":hierarchy,"hierarchy_scope_lines":scopes,"hierarchy_scope_sha256":object_hash(scopes),
        "public_monitor_source":monitor,"public_monitor_sha256":content_hash(monitor),
        "instrumented_testbench_sha256":content_hash(instrumented),"public_boundary_vector_hash":plan["public_boundary_vector_hash"],
        "actual_public_stream_transfers":stream_records,"actual_pe_lane_transfers":pe_records,
        "elaborated_instance_counts":{n:16 if n=="node-pe" else 1 for n in NODE_IDS},"software_qa_fixture":True}


class GlobalSoftwareTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.directory=Path(self.temp.name)
        self.store=ProjectStore(self.directory/"project",PROJECT/"examples/npu_all_nodes_project.json")
        self.store.set_review_policy("accept_on_pass",True,"SOFTWARE QA authorization only")
        for stage in IMPLEMENTED_STAGES: self.store.validate(stage,self.store.envelope()["revision"]["id"])
        self.sources=Sources(self.store)
        self.compiler={"kind":"native","executable":str(self.directory/"iverilog.exe"),"working_directory":str(self.directory/"tools")}
        self.manager=self.new_manager(); self.addCleanup(self.manager.close)

    def new_manager(self):
        return GlobalGenerationManager(self.store,self.sources.generation,self.sources.workflow,self.sources.specs,self.compiler)

    def run_job(self, mutate=None, proof=fixture_proof, chunks=1, status="Completed", operation="generate", base=None, instruction=""):
        revision=self.store.envelope()["revision"]["id"]
        preview=self.manager.preview(revision,operation,base,instruction)
        rtl=header(top_interface(preview["source_manifest"]["design"]))+"// SOFTWARE QA TOP ONLY\nendmodule\n"
        raw="```verilog\n"+rtl+"```"
        def generate(messages,parameters,cancel,on_event):
            if mutate: mutate()
            for index in range(0,len(raw),max(1,len(raw)//chunks)): on_event({"type":"delta","content":raw[index:index+max(1,len(raw)//chunks)]})
            on_event({"type":"reasoning","content":"QA reasoning retained"})
            return {"raw_content":raw,"raw_reasoning":"QA reasoning retained","execution_status":status,"usage":{"completion_tokens":8},"finish_reason":"stop","error":None}
        with patch("hullcirq.global_generation.ChatCompletionsClient") as client,patch("hullcirq.global_generation.check_global_rtl",side_effect=proof):
            client.return_value.generate.side_effect=generate
            self.manager.start(revision,preview["context_id"],preview["profile_revision_id"],operation,base,instruction)
            self.manager._worker.join(20); self.assertFalse(self.manager._worker.is_alive())
        return self.manager.envelope()["global_generation"]["jobs"][-1]

    def test_original_job_values_and_external_address_mapping(self):
        job=original_job(self.store.envelope()["design"])
        self.assertEqual(matrix_results(job),[113,-112,-135,2147482606,-1145,522,-633,-2147483644,
            387,-1133,1876,-2147483523,-131,16394,-32520,2147482999])
        words=load_words(job); self.assertEqual(len(words),32)
        self.assertEqual(words[:4],[0x0080,0x01fd,0x0200,0x037f])
        self.assertEqual(words[4],0x1002); self.assertEqual(words[16],0x4080); self.assertEqual(words[-1],0x4fff)
        self.assertTrue(all(w<32768 for w in words))

    def test_strict_job_type_and_regenerated_plan_tampering(self):
        design=self.store.envelope()["design"]; plan=build_global_plan(design); validate_global_plan(design,plan)
        for field,value in (("k",4.0),("relu",0)):
            changed=copy.deepcopy(design); changed["verification_jobs"][0][field]=value
            with self.subTest(field=field),self.assertRaises(DomainError): build_global_plan(changed)
        for field in ("expected_outputs","load_words"):
            changed=copy.deepcopy(plan); changed["recipe"][field][0]+=1
            changed["vector_hash"]=object_hash(changed["recipe"])
            with self.subTest(field=field),self.assertRaises(DomainError): validate_global_plan(design,changed)

    def test_all_six_gate_and_exact_revision_latest_epoch_lineage(self):
        self.assertTrue(self.manager.envelope()["global_generation"]["ready"])
        for mutation in (lambda s:s.specs._state["specs"].pop(),
                lambda s:s.specs._state["specs"][0].update(review_status="Awaiting Review"),
                lambda s:s.generation._state["jobs"][0].update(revision_id="mixed"),
                lambda s:s.generation._state["node_epochs"].update({NODE_IDS[0]:2}),
                lambda s:s.workflow._state["runs"][1].update(prior_run_id="wrong"),
                lambda s:s.generation._state["reviews"][0].update(decision="changes_requested")):
            original=copy.deepcopy([m._state for m in (self.sources.generation,self.sources.workflow,self.sources.specs)])
            mutation(self.sources)
            with self.subTest(mutation=mutation),self.assertRaises(DomainError): self.manager.source_manifest()
            for manager,state in zip((self.sources.generation,self.sources.workflow,self.sources.specs),original): manager._state=state
        self.assertFalse(self.manager.path.exists())

    def test_manifest_exact_sources_and_prompt_excludes_numeric_test_job(self):
        manifest=self.manager.source_manifest(); untouched=copy.deepcopy(manifest)
        self.assertEqual([n["node_id"] for n in manifest["nodes"]],list(NODE_IDS))
        self.assertFalse(manifest["internal_nets_used_as_API"])
        for entry in manifest["nodes"]:
            self.assertEqual(entry["rtl"],self.sources.generation._stored_job(entry["candidate_id"])["rtl"])
        manifest["nodes"][0]["rtl"]="tampered local copy"
        self.assertEqual(self.manager.source_manifest(),untouched)
        preview=self.manager.preview(self.store.envelope()["revision"]["id"])
        text=json.dumps(preview["messages"],ensure_ascii=False)
        self.assertLess(len(text.encode()),11000)
        self.assertNotIn('"A":',text); self.assertNotIn('"expected_outputs"',text)
        self.assertNotIn("2147483647",text)
        self.assertIn("output_transfer",text); self.assertIn("pair_meta",text)
        self.assertEqual(preview["verification_plan"]["recipe"]["source_job"],self.store.envelope()["design"]["verification_jobs"][0])

    def test_presentation_save_preserves_original_manifest_adoption_and_reopen(self):
        job = self.run_job()
        manifest = self.manager.source_manifest()
        epoch = self.manager._state["source_epoch"]
        original_bytes = self.manager.path.read_bytes()
        current = self.store.envelope()
        changed = copy.deepcopy(current["design"])
        changed["layout"]["viewport"]["x"] += 17
        changed["layout"]["nodes"]["node-control"]["x"] += 11
        changed["project"]["name"] += " display title"
        saved = self.store.save(changed, current["revision"]["id"])
        self.assertNotEqual(saved["revision"]["id"], manifest["revision_id"])
        self.assertEqual(self.manager.source_manifest(), manifest)
        data = self.manager.envelope()["global_generation"]
        self.assertTrue(data["ready"])
        self.assertIsNone(data["blocked_code"])
        self.assertEqual((data["jobs"][-1]["id"], data["jobs"][-1]["review_status"], data["jobs"][-1]["freshness"]),
                         (job["id"], "Accepted", "Current"))
        self.assertEqual(self.manager._state["source_epoch"], epoch)
        self.assertEqual(self.manager.path.read_bytes(), original_bytes)
        reopened = self.new_manager(); self.addCleanup(reopened.close)
        self.assertEqual(reopened.source_manifest(), manifest)
        self.assertEqual(reopened.envelope()["global_generation"]["jobs"][-1]["review_status"], "Accepted")
        self.assertEqual(self.manager.path.read_bytes(), original_bytes)

    def test_new_request_after_presentation_save_retains_source_and_actual_request_revisions(self):
        original = self.store.envelope()
        changed = copy.deepcopy(original["design"])
        changed["layout"]["viewport"]["zoom"] *= 1.25
        saved = self.store.save(changed, original["revision"]["id"])
        context = self.manager.preview(saved["revision"]["id"])
        self.assertEqual(context["revision_id"], original["revision"]["id"])
        self.assertEqual(context["requested_revision_id"], saved["revision"]["id"])
        with self.assertRaises(DomainError):
            self.manager.preview(original["revision"]["id"])
        job = self.run_job()
        self.assertEqual(job["revision_id"], original["revision"]["id"])
        self.assertEqual(job["requested_revision_id"], saved["revision"]["id"])
        self.assertEqual(job["review_status"], "Accepted")
        self.assertEqual(self.manager._state["reviews"][-1]["reviewed_revision_id"], saved["revision"]["id"])
        reopened = self.new_manager(); self.addCleanup(reopened.close)
        self.assertIsNone(reopened.envelope()["global_generation"]["storage_error"])

    def test_display_save_between_preview_and_start_lock_rejects_stale_request(self):
        current = self.store.envelope()
        context = self.manager.preview(current["revision"]["id"])
        original_preview = self.manager.preview
        def preview_then_save(*args, **kwargs):
            result = original_preview(*args, **kwargs)
            changed = copy.deepcopy(current["design"])
            changed["layout"]["viewport"]["x"] += 1
            self.store.save(changed, current["revision"]["id"])
            return result
        with patch.object(self.manager, "preview", side_effect=preview_then_save), \
                patch("hullcirq.global_generation.ChatCompletionsClient") as client:
            with self.assertRaises(DomainError) as changed:
                self.manager.start(current["revision"]["id"], context["context_id"], context["profile_revision_id"])
            self.assertEqual(changed.exception.code, "revision_conflict")
            client.assert_not_called()
        self.assertEqual(self.manager._state["jobs"], [])

    def test_presentation_equivalence_does_not_allow_mixed_or_missing_source_snapshots(self):
        current = self.store.envelope()
        manifest = self.manager.source_manifest()  # prime the read-plan cache
        changed = copy.deepcopy(current["design"])
        changed["layout"]["viewport"]["x"] += 1
        saved = self.store.save(changed, current["revision"]["id"])
        candidate = self.sources.generation._state["jobs"][0]
        candidate["revision_id"] = saved["revision"]["id"]
        with self.assertRaises(DomainError) as mixed:
            self.manager.source_manifest()
        self.assertEqual(mixed.exception.code, "global_revision_conflict")
        candidate["revision_id"] = manifest["revision_id"]
        self.assertEqual(self.manager.source_manifest(), manifest)
        del self.store._state["snapshots"][manifest["revision_id"]]
        with self.assertRaises(DomainError):
            self.manager.source_manifest()

    def test_strict_semantic_numeric_types_are_not_presentation_changes(self):
        current = self.store.envelope()
        changed = copy.deepcopy(current["design"])
        changed["settings"]["clock_period_ns"] = float(changed["settings"]["clock_period_ns"])
        changed["layout"]["viewport"]["x"] += 1
        # The general revision hash normalizes integral floats, but evidence
        # source equivalence must still retain the original numeric types.
        saved = self.store.save(changed, current["revision"]["id"])
        self.assertEqual(saved["revision"]["semantic_hash"], current["revision"]["semantic_hash"])
        with self.assertRaises(DomainError) as mismatch:
            self.manager.source_manifest()
        self.assertEqual(mismatch.exception.code, "source_revision_conflict")

    def test_semantic_change_and_revert_does_not_revive_prior_accepted_epoch(self):
        job = self.run_job()
        original = self.store.envelope()
        changed = copy.deepcopy(original["design"])
        changed["settings"]["clock_period_ns"] += 1
        saved = self.store.save(changed, original["revision"]["id"])
        blocked = self.manager.envelope()["global_generation"]
        self.assertFalse(blocked["ready"])
        self.assertNotEqual(blocked["jobs"][-1]["review_status"], "Accepted")
        self.store.save(original["design"], saved["revision"]["id"])
        for stage in IMPLEMENTED_STAGES:
            self.store.validate(stage, self.store.envelope()["revision"]["id"])
        data = self.manager.envelope()["global_generation"]
        self.assertTrue(data["ready"])
        self.assertEqual(data["jobs"][-1]["id"], job["id"])
        self.assertEqual(data["jobs"][-1]["review_status"], "Awaiting Review")

    def test_pass_adoption_lossless_restart_and_repair(self):
        job=self.run_job(); self.assertEqual(job["review_status"],"Accepted"); self.assertEqual(job["freshness"],"Current")
        self.assertEqual(self.manager._state["reviews"][-1]["actor"],"automation_policy")
        restored=self.new_manager(); self.addCleanup(restored.close)
        self.assertEqual(restored.job(job["id"])["context"],job["context"])
        repaired=self.run_job(operation="repair",base=job["id"],instruction="SOFTWARE QA repair feedback")
        self.assertIn(job["rtl"],repaired["context"]["messages"][-1]["content"])
        self.assertEqual(repaired["origin"],"local_llm")
        self.assertEqual(len(strict_loads(self.manager.path.read_text(encoding="utf-8"))["jobs"]),2)

    def test_failed_proof_and_provider_failure_never_adopt(self):
        def failed(*args):
            proof=fixture_proof(*args); proof["validation_status"]="Failed"; return proof
        job=self.run_job(proof=failed); self.assertEqual(job["validation_status"],"Failed"); self.assertEqual(job["review_status"],"Awaiting Review")
        with self.assertRaises(DomainError): self.manager.review(job["id"],"accepted","")
        job=self.run_job(status="Failed"); self.assertEqual(job["execution_status"],"Failed")
        self.assertTrue(job["raw_content"]); self.assertIsNone(job["rtl"])

    def test_checksum_updated_forged_proof_cannot_auto_adopt(self):
        def forged(*args):
            proof=fixture_proof(*args); proof["commands"][-1]["stdout"]=""; return proof
        job=self.run_job(proof=forged)
        self.assertEqual(job["review_status"],"Awaiting Review")
        with self.assertRaises(DomainError): self.new_manager()

    def test_source_withdrawal_restoration_cannot_resurrect_adoption(self):
        job=self.run_job(); source=self.sources.specs._state["specs"][0]
        source["review_status"]="Changes Requested"
        self.assertEqual(self.manager.job(job["id"])["freshness"],"Stale")
        source["review_status"]="Accepted"
        current=self.manager.job(job["id"])
        self.assertEqual(current["freshness"],"Current"); self.assertEqual(current["review_status"],"Awaiting Review")
        self.assertEqual(self.manager._state["reviews"][0]["decision"],"accepted")

    def test_source_change_during_model_execution_retains_pass_without_adoption(self):
        job=self.run_job(mutate=lambda:self.sources.specs._state["specs"][0].update(review_status="Changes Requested"))
        self.assertEqual(job["validation_status"],"Passed"); self.assertEqual(job["freshness"],"Stale")
        self.assertEqual(job["review_status"],"Awaiting Review")
        self.manager.review(job["id"],"return_to_stage","SOFTWARE QA return to correct source","node_implementation_specs",operator={"actor":"human"})
        self.assertEqual(self.manager._state["reviews"][-1]["actor"],"human")

    def test_live_wrong_type_and_layout_change_block_model_before_call(self):
        current=self.store.envelope(); changed=copy.deepcopy(current["design"])
        changed["verification_jobs"][0]["k"]=4.0; changed["layout"]["nodes"]["node-control"]["x"]+=1
        self.store.save(changed,current["revision"]["id"])
        with patch("hullcirq.global_generation.ChatCompletionsClient") as client,self.assertRaises(DomainError):
            self.manager.preview(self.store.envelope()["revision"]["id"])
        client.assert_not_called(); self.assertFalse(self.manager.path.exists())

    def test_local_active_and_stale_preview_refuse_without_global_attempt(self):
        revision=self.store.envelope()["revision"]["id"]; context=self.manager.preview(revision)
        self.sources.generation._state["jobs"][0]["execution_status"]="Running"
        with self.assertRaises(DomainError): self.manager.start(revision,context["context_id"],context["profile_revision_id"])
        self.assertEqual(self.manager._state["jobs"],[])
        self.sources.generation._state["jobs"][0]["execution_status"]="Completed"
        with self.assertRaises(DomainError): self.manager.start(revision,"wrong-context",context["profile_revision_id"])
        self.assertFalse(self.manager.path.exists())

    def test_event_chunks_checkpoint_coalesced_but_terminal_exact(self):
        with patch.object(self.manager,"_persist",wraps=self.manager._persist) as persist:
            job=self.run_job(chunks=1000)
        self.assertGreater(len(job["events"]),300); self.assertLess(persist.call_count,15)
        restored=self.new_manager(); self.addCleanup(restored.close)
        self.assertEqual(restored.job(job["id"])["events"],job["events"])
        self.assertEqual(restored.job(job["id"])["raw_content"],job["raw_content"])
        self.assertEqual(restored.job(job["id"])["usage"],job["usage"])

    def test_checksum_updated_context_plan_prompt_profile_lineage_tamper_refused(self):
        self.run_job(); original=self.manager.path.read_bytes()
        for mutation in (lambda j:j["context"]["verification_plan"]["recipe"]["expected_outputs"].__setitem__(0,99),
                lambda j:j["context"]["messages"][-1].update(content="forged prompt"),
                lambda j:j["context"]["source_manifest"]["nodes"][0].update(rtl="forged source"),
                lambda j:j.update(profile_revision_id="missing-profile"),
                lambda j:j["checks"]["commands"][-1].update(command=["echo","forged"]),
                lambda j:j["checks"]["actual_output_transfers"][0].update(value=113.0)):
            state=strict_loads(original.decode()); job=state["jobs"][0]; mutation(job)
            # Re-sign all enclosing generic hashes. Semantic checks must still
            # reject the edit; a checksum alone is not a source-of-truth check.
            context=job["context"]; context["source_key"]=object_hash(context["source_manifest"]); job["source_key"]=context["source_key"]
            context["context_id"]=object_hash({k:v for k,v in context.items() if k!="context_id"}); job["context_id"]=context["context_id"]
            job["record_hash"]=object_hash({k:v for k,v in job.items() if k!="record_hash"})
            self.manager.path.write_text(json.dumps(state),encoding="utf-8"); saved=self.manager.path.read_bytes()
            with self.subTest(mutation=mutation),self.assertRaises(DomainError): self.new_manager()
            self.assertEqual(self.manager.path.read_bytes(),saved)
        self.manager.path.write_bytes(original)

    def test_restart_active_request_interrupted_without_resend(self):
        self.run_job(); self.manager._state["reviews"]=[]; job=self.manager._state["jobs"][0]
        job.update(execution_status="Running",validation_status="Not Checked",review_status="Awaiting Review")
        self.manager._persist()
        with patch("hullcirq.global_generation.ChatCompletionsClient") as client:
            restored=self.new_manager(); self.addCleanup(restored.close)
        client.assert_not_called(); result=restored.job(job["id"])
        self.assertEqual(result["execution_status"],"Interrupted"); self.assertTrue(result["raw_content"])

    def test_monitor_vectors_are_same_original_per_lane_operands_and_partials(self):
        plan=build_global_plan(self.store.envelope()["design"]); v=plan["public_boundary_vectors"]
        self.assertEqual(v["pe_lanes"][0]["pairs"],[0x8080,0x05fd,0x0300,0x807f])
        self.assertEqual(v["pe_lanes"][0]["partial_sums"],[16384,16369,16369,113])
        self.assertEqual(v["metadata"][:5],[16,0,0,32,17])
        self.assertEqual(len(v["requests"]),64); self.assertEqual(len(v["pe_lanes"]),16)
        changed=copy.deepcopy(plan); changed["public_boundary_vectors"]["pe_lanes"][0]["pairs"][0]+=1
        changed["public_boundary_vector_hash"]=object_hash(changed["public_boundary_vectors"])
        with self.assertRaises(DomainError): validate_global_plan(self.store.envelope()["design"],changed)

    def test_actual_icarus_rejects_unused_instances_even_if_external_constants_pass(self):
        config=PROJECT/".work/m2/compiler.json"
        if not config.exists(): self.skipTest("Trusted Icarus configuration unavailable")
        compiler=strict_loads(config.read_text(encoding="utf-8-sig")); compiler["working_directory"]=str(PROJECT/".work/m2e/software-qa-tools")
        manifest=self.manager.source_manifest(); design=manifest["design"]; plan=build_global_plan(design)
        for entry in manifest["nodes"]:
            interface=entry["public_interface"]
            outputs=[p for p in interface["ports"] if p["direction"]=="output"]
            entry["rtl"]=header(interface)+"\n".join("assign "+p["name"]+"="+("1'b1" if p["name"].endswith("_ready") else f"{p['width']}'d0")+";" for p in outputs)+"\nendmodule\n"
            entry["rtl_sha256"]=content_hash(entry["rtl"])
        rtl=header(top_interface(design)).replace("output busy","output reg busy").replace("output job_done","output reg job_done").replace("output signed [31:0] output_data","output reg signed [31:0] output_data")
        rtl+="integer index; assign config_data_ready=!busy; assign load_data_ready=!busy; assign output_data_valid=busy;\n"
        rtl+="always @(posedge clk) begin if(rst) begin index<=0;busy<=0;job_done<=0;end else begin job_done<=0; if(config_data_valid&&config_data_ready) begin busy<=1;index<=0;end else if(busy&&output_data_ready) begin if(index==15) begin busy<=0;job_done<=1;end else index<=index+1;end end end\n"
        rtl+="always @* begin case(index)\n"+"\n".join(f"{i}:output_data=32'h{v&0xffffffff:08x};" for i,v in enumerate(plan["recipe"]["expected_outputs"]))+"\ndefault:output_data=0;endcase end\n"
        for ni,entry in enumerate(manifest["nodes"]):
            for pi in range(16 if entry["node_id"]=="node-pe" else 1):
                connections=[]
                for p in entry["public_interface"]["ports"]:
                    value=p["name"] if p["name"] in ("clk","rst") else f"{p['width']}'d0" if p["direction"]=="input" else ""
                    connections.append("."+p["name"]+"("+value+")")
                rtl+=entry["module_name"]+f" unused_{ni}_{pi}("+",".join(connections)+");\n"
        rtl+="endmodule\n"
        proof=check_global_rtl(rtl,manifest,plan,compiler)
        self.assertEqual(proof["checks"]["interface"]["validation_status"],"Passed",proof["diagnostics"])
        self.assertEqual(proof["checks"]["elaboration"]["validation_status"],"Passed",proof)
        self.assertEqual(len(proof["commands"]),4,proof)
        self.assertEqual(proof["commands"][2]["exit_code"],0,proof["stderr"])
        self.assertEqual(proof["validation_status"],"Failed")
        self.assertIn("HULLCIRQ_FAIL",proof["stdout"])
        # Confirm this particular bypass fixture would fool external-only
        # validation; the instrumented run above is the product's decision.
        directory=Path(proof["artifacts_directory"])
        runtime=compiler["executable"].rsplit("/",1)[0]+"/vvp"
        arguments=["-M",compiler["base_directory"],_wsl_path(directory/"hierarchy.vvp")]
        external=execute_fixed(trusted_command(compiler,runtime,arguments,directory.parent),directory.parent)
        self.assertEqual(external["exit_code"],0,external)
        self.assertIn("HULLCIRQ_GLOBAL_PASS",external["stdout"])
        self.assertNotIn("HULLCIRQ_FAIL",external["stdout"])

    def test_actual_icarus_positive_all_original_public_transactions_and_faults(self):
        config=PROJECT/".work/m2/compiler.json"
        if not config.exists(): self.skipTest("Trusted Icarus configuration unavailable")
        from test_control_verification import SOFTWARE_FIXTURE_RTL as control
        from test_scheduler_verification import SOFTWARE_FIXTURE_RTL as scheduler
        from test_npu_nodes_verification import FIXTURES
        from test_continuous_flow import SOFTWARE_FIXTURE_RTL as pe
        compiler=strict_loads(config.read_text(encoding="utf-8-sig")); compiler["working_directory"]=str(PROJECT/".work/m2e/software-qa-tools")
        manifest=self.manager.source_manifest(); plan=build_global_plan(manifest["design"])
        sources=dict(FIXTURES,**{"node-control":control,"node-scheduler":scheduler,"node-pe":pe.replace("module m2a_mac(","module hullcirq_pe(")})
        for entry in manifest["nodes"]:
            entry["rtl"]=sources[entry["node_id"]]; entry["rtl_sha256"]=content_hash(entry["rtl"])
        rtl=header(top_interface(manifest["design"]))+SOFTWARE_TOP_BODY
        proof=check_global_rtl(rtl,manifest,plan,compiler)
        self.assertEqual(proof["validation_status"],"Passed",proof)
        self.assertEqual(len(proof["actual_output_transfers"]),16)
        self.assertEqual([r["value"] for r in proof["actual_output_transfers"]],plan["recipe"]["expected_outputs"])
        self.assertEqual(sorted(r["lane"] for r in proof["actual_pe_lane_transfers"]),list(range(16)))
        self.assertEqual(len(proof["actual_public_stream_transfers"]),15)
        job={"rtl":rtl,"context":{"source_manifest":manifest,"verification_plan":plan,"tool_configuration":compiler},"checks":proof}
        self.assertTrue(self.manager._passed(job))
        # One corruption targets actual dispatch; another targets the final
        # completion feedback. Every run uses the unchanged original job.
        for bad in (rtl.replace(".pair_data(pair),.pair_data_valid(pairv&&!pending", ".pair_data(pair^16'h0001),.pair_data_valid(pairv&&!pending"),
                    rtl.replace(".output_transfer(transfer),.busy(busy)",".output_transfer(1'b0),.busy(busy)")):
            failed=check_global_rtl(bad,manifest,plan,compiler)
            self.assertEqual(failed["validation_status"],"Failed",failed)
            self.assertIn("HULLCIRQ_FAIL",failed["stdout"])


if __name__=="__main__": unittest.main()
