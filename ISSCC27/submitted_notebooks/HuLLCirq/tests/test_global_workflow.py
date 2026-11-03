"""Isolated software QA for S09/S10; simulated proofs are never project evidence."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import re
import sys
import threading
import unittest
from unittest.mock import patch

PROJECT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PROJECT/"src"))
import test_global_generation as fixtures
from hullcirq.context import physical_interface
from hullcirq.domain import DomainError
from hullcirq.global_generation import (build_global_plan, expected_instance_counts,
    expected_output_count, expected_pe_records, public_transfer_counts, top_interface)
from hullcirq.global_workflow import (GlobalWorkflowManager, STAGES, source_bundle, synthesis_script,
    fixed_global_synthesis_commands, fixed_global_netlist_commands, netlist_public_interfaces,
    compiler_netlist_public_hierarchy, synthesize_global_generic, check_global_netlist,
    validate_synthesis_proof, validate_netlist_proof, _records)
from hullcirq.verification import content_hash, object_hash


def synthesis_fixture(rtl,manifest,synthesizer,directory=None,cancel_event=None):
    """SOFTWARE QA fake tool records only; no synthesis or circuit proof claimed."""
    netlist=rtl+"\n"+"\n".join(n["rtl"] for n in manifest["nodes"])
    folder=Path(synthesizer["working_directory"])/"hullcirq-global-synth-software-qa"
    files=source_bundle(rtl,manifest); script=synthesis_script(manifest)
    commands=[{"command":c,"executed":True,"status":"Completed","exit_code":0,"stdout":"SOFTWARE QA\n","stderr":""}
        for c in fixed_global_synthesis_commands(synthesizer,manifest,folder)]
    return {"validation_status":"Passed","executed":True,"exit_code":0,"stdout":"SOFTWARE QA\n","stderr":"","diagnostics":[],
        "commands":commands,"artifacts_directory":str(folder),"tool_configuration":copy.deepcopy(synthesizer),
        "global_rtl_sha256":content_hash(rtl),"source_manifest_sha256":object_hash(manifest),"source_bundle":files,"source_bundle_sha256":object_hash(files),
        "synthesis_script":script,"synthesis_script_sha256":content_hash(script),"netlist":netlist,"netlist_sha256":content_hash(netlist),
        "netlist_public_interfaces":netlist_public_interfaces(netlist,manifest),"software_qa_fixture":True}


def simulation_fixture(netlist,manifest,plan,compiler,cancel_event=None):
    proof=fixtures.fixture_proof(netlist,manifest,plan,compiler,cancel_event)
    folder=Path(compiler["working_directory"])/"hullcirq-global-netlist-software-qa"
    for command,expected in zip(proof["commands"],fixed_global_netlist_commands(compiler,folder)): command["command"]=expected
    proof.update(artifacts_directory=str(folder),netlist_sha256=content_hash(netlist),verification_plan_sha256=object_hash(plan),
        netlist_public_interfaces=netlist_public_interfaces(netlist,manifest),compiled_design_sources=[{"file":"netlist.v","sha256":content_hash(netlist)}],source_rtl_linked=False)
    return proof


def explicit_2x2_sources():
    """Small source/interface projection; never a generated-design proof."""
    design=json.loads((PROJECT/"examples/npu_2x2_explicit_project.json").read_text(encoding="utf-8"))
    nodes=[]
    for node in design["nodes"]:
        interface=physical_interface(design,node)
        rtl=fixtures.header(interface)+"// SOFTWARE QA INTERFACE ONLY\nendmodule\n"
        nodes.append({"node_id":node["id"],"module_name":node["module_name"],
            "rtl":rtl,"rtl_sha256":content_hash(rtl),"public_interface":interface})
    manifest={"version":2,"design":design,"nodes":nodes}
    top=fixtures.header(top_interface(design))+"// SOFTWARE QA INTERFACE ONLY\nendmodule\n"
    return top,manifest,build_global_plan(design)


class Explicit2x2GlobalWorkflowTests(unittest.TestCase):
    def test_dynamic_sources_interfaces_hierarchy_and_records(self):
        top,manifest,plan=explicit_2x2_sources()
        bundle=source_bundle(top,manifest); script=synthesis_script(manifest)
        self.assertEqual(len(bundle),12)
        self.assertEqual(script.count("read_verilog"),12)
        self.assertEqual(expected_instance_counts(manifest),{node["node_id"]:1 for node in manifest["nodes"]})
        self.assertEqual(expected_output_count(plan),4)
        self.assertEqual(expected_pe_records(plan),[
            {"node_id":"npu2-pe"+lane,"lane":lane,"inputs":3,"outputs":1}
            for lane in ("00","01","10","11")])

        netlist=top+"\n"+"\n".join(node["rtl"] for node in manifest["nodes"])
        self.assertEqual(len(netlist_public_interfaces(netlist,manifest)),12)
        scopes=['S_tb .scope module, "hullcirq_global_tb" "hullcirq_global_tb" 1 1;',
                f'S_dut .scope module, "dut" "{top_interface(manifest["design"])["module_name"]}" 1 1, 2 1 0, S_tb;']
        for index,node in enumerate(manifest["nodes"]):
            scopes.append(f'S_n{index} .scope module, "u_{index}" "{node["module_name"]}" 1 1, 2 1 0, S_dut;')
        hierarchy=compiler_netlist_public_hierarchy(scopes,manifest)
        self.assertEqual({node_id:len(paths) for node_id,paths in hierarchy.items()},
                         expected_instance_counts(manifest))

        outputs=[{"index":i,"value":value,"cycle":100+i*2}
                 for i,value in enumerate(plan["recipe"]["expected_outputs"])]
        streams=[{"stream":name,"transfers":count} for name,count in public_transfer_counts(plan).items()]
        pes=expected_pe_records(plan)
        stdout="".join(f"HULLCIRQ_OUTPUT index={x['index']} value={x['value']} cycle={x['cycle']}\n" for x in outputs)
        stdout+="".join(f"HULLCIRQ_PUBLIC stream={x['stream']} transfers={x['transfers']}\n" for x in streams)
        stdout+="".join(f"HULLCIRQ_PE node={x['node_id']} lane={x['lane']} inputs={x['inputs']} outputs={x['outputs']}\n" for x in pes)
        stdout+=f"HULLCIRQ_PUBLIC_PASS vector_hash={plan['public_boundary_vector_hash']}\n"
        stdout+=f"HULLCIRQ_GLOBAL_PASS outputs=4 vector_hash={plan['vector_hash']}\n"
        self.assertEqual(_records(stdout,plan),(True,outputs,streams,pes))
        self.assertFalse(_records(stdout.replace("outputs=4 vector_hash=","outputs=16 vector_hash="),plan)[0])


class GlobalWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.base=fixtures.GlobalSoftwareTests(methodName="runTest"); self.base.setUp(); self.addCleanup(self.base.doCleanups)
        self.store=self.base.store; self.global_manager=self.base.manager; self.sources=self.base.sources
        self.compiler=self.base.compiler
        self.synthesizer={"kind":"native","executable":str(self.base.directory/"yosys.exe"),"working_directory":str(self.base.directory/"synthesis")}
        self.job=self.base.run_job()
        self.manager=self.new_manager(); self.addCleanup(self.manager.close)

    def new_manager(self):
        return GlobalWorkflowManager(self.store,self.sources.generation,self.sources.specs,self.global_manager,self.compiler,self.synthesizer)

    def run_stage(self,stage=STAGES[0],synthesis=None,synth=synthesis_fixture,simulate=simulation_fixture):
        with patch("hullcirq.global_workflow.synthesize_global_generic",side_effect=synth),patch("hullcirq.global_workflow.check_global_netlist",side_effect=simulate):
            self.manager.start(stage,self.job["id"],synthesis)
            self.manager._worker.join(20); self.assertFalse(self.manager._worker.is_alive())
        return self.manager.envelope()["global_workflow"]["runs"][-1]

    def test_two_stages_inherit_exact_plan_adopt_and_restart(self):
        synthesis=self.run_stage(); self.assertEqual(synthesis["review_status"],"Accepted")
        simulation=self.run_stage(STAGES[1],synthesis["id"])
        self.assertEqual(simulation["review_status"],"Accepted"); self.assertEqual(simulation["freshness"],"Current")
        self.assertEqual(simulation["verification_plan"],self.job["context"]["verification_plan"])
        self.assertEqual(simulation["netlist"],synthesis["netlist"])
        self.assertFalse(simulation["checks"]["source_rtl_linked"])
        self.assertEqual([r["actor"] for r in self.manager._state["reviews"]],["automation_policy"]*2)
        reopened=self.new_manager(); self.addCleanup(reopened.close)
        self.assertEqual(reopened.run(simulation["id"])["review_status"],"Accepted")
        self.assertEqual(reopened.envelope()["global_workflow"]["stages"][-1]["accepted_run_id"],simulation["id"])

    def test_netlist_only_fixed_commands_and_nonflatten_script(self):
        manifest=self.job["context"]["source_manifest"]
        script=synthesis_script(manifest)
        self.assertEqual(script.count("read_verilog"),7); self.assertIn(" -noabc\n",script); self.assertNotIn("flatten",script)
        folder=Path(self.compiler["working_directory"])/"hullcirq-global-netlist-software-qa"
        commands=fixed_global_netlist_commands(self.compiler,folder)
        for command in commands[1:3]:
            self.assertEqual(sum(str(x).endswith("netlist.v") for x in command),1)
            self.assertFalse(any(str(x).endswith("candidate_top.v") or str(x).endswith("node-pe.v") for x in command))
        with self.assertRaises(DomainError): fixed_global_netlist_commands(self.compiler,folder.parent/"arbitrary")

    def test_reject_nonadopted_global_and_missing_or_wrong_prior(self):
        with self.assertRaises(DomainError): self.manager.start(STAGES[1],self.job["id"])
        with self.assertRaises(DomainError): self.manager.start(STAGES[0],"wrong-global")
        self.global_manager.review(self.job["id"],"changes_requested","SOFTWARE QA withdrawal")
        self.assertFalse(self.manager.envelope()["global_workflow"]["ready"])
        with self.assertRaises(DomainError): self.manager.start(STAGES[0],self.job["id"])

    def test_active_peer_model_or_node_tool_blocks_standalone_manager(self):
        for manager,field in ((self.sources.generation,"jobs"),(self.sources.workflow,"runs")):
            before=manager._state[field][-1]["execution_status"]
            manager._state[field][-1]["execution_status"]="Running"
            with self.subTest(field=field),self.assertRaises(DomainError): self.manager.start(STAGES[0],self.job["id"])
            manager._state[field][-1]["execution_status"]=before
        self.assertFalse(self.manager._state["runs"])

    def test_source_withdraw_restore_does_not_revive_tool_adoption(self):
        run=self.run_stage(); self.assertEqual(run["review_status"],"Accepted")
        node=self.sources.specs._state["specs"][0]; old=node["review_status"]
        node["review_status"]="Changes Requested"; self.manager.envelope()
        node["review_status"]=old
        value=self.manager.run(run["id"])
        self.assertEqual(value["freshness"],"Stale"); self.assertEqual(value["review_status"],"Awaiting Review")
        with self.assertRaises(DomainError): self.manager.review(run["id"],"accepted","cannot revive")

    def test_synthesis_withdraw_reaccept_invalidates_existing_simulation(self):
        synthesis=self.run_stage(); simulation=self.run_stage(STAGES[1],synthesis["id"])
        self.manager.review(synthesis["id"],"changes_requested","SOFTWARE QA synthesis withdrawal")
        self.assertEqual(self.manager.run(simulation["id"])["freshness"],"Stale")
        self.manager.review(synthesis["id"],"accepted","SOFTWARE QA explicit reacceptance")
        self.assertEqual(self.manager.run(simulation["id"])["freshness"],"Stale")
        with self.assertRaises(DomainError): self.manager.review(simulation["id"],"accepted","")

    def test_inflight_source_change_blocks_policy_adoption(self):
        def changed(*args,**kwargs):
            result=synthesis_fixture(*args,**kwargs)
            self.sources.generation._state["node_epochs"][fixtures.NODE_IDS[0]]+=1
            return result
        run=self.run_stage(synth=changed)
        self.assertEqual(run["validation_status"],"Passed"); self.assertEqual(run["review_status"],"Awaiting Review")
        self.assertEqual(run["freshness"],"Stale"); self.assertTrue(any(x["code"]=="automatic_adoption_blocked" for x in run["diagnostics"]))

    def test_forged_pass_logs_commands_and_numeric_types_rejected(self):
        synthesis=self.run_stage(); simulation=self.run_stage(STAGES[1],synthesis["id"])
        changes=[lambda r:r["checks"].update(source_rtl_linked=True),
            lambda r:r["checks"]["commands"][1]["command"].append("node-pe.v"),
            lambda r:r["checks"]["actual_output_transfers"][0].update(value=float(r["checks"]["actual_output_transfers"][0]["value"])),
            lambda r:r["checks"]["commands"][-1].update(exit_code=False),
            lambda r:r["checks"]["commands"][-1].update(stdout=r["checks"]["commands"][-1]["stdout"].replace("inputs=4","inputs=3",1)),
            lambda r:r["checks"].update(instrumented_testbench_sha256="0"*64)]
        for change in changes:
            bad=copy.deepcopy(simulation); change(bad)
            with self.subTest(change=change),self.assertRaises(DomainError): validate_netlist_proof(bad)
        for change in (lambda r:r["checks"].update(netlist=r["netlist"]+"// changed\n"),
                       lambda r:r["checks"]["source_bundle"][0].update(sha256="f"*64)):
            bad=copy.deepcopy(synthesis); change(bad)
            with self.assertRaises(DomainError): validate_synthesis_proof(bad)

    def test_rehashed_saved_source_plan_and_netlist_substitution_rejected(self):
        synthesis=self.run_stage(); self.run_stage(STAGES[1],synthesis["id"])
        original=self.manager.path.read_bytes()
        for change in (lambda s:s["runs"][1]["verification_plan"]["recipe"]["source_job"].update(k=4.0),
                       lambda s:s["runs"][1].update(netlist=s["runs"][1]["netlist"]+"// substitute\n"),
                       lambda s:s["runs"][0]["source_manifest"]["nodes"][0].update(candidate_id="other"),
                       lambda s:s["runs"][1]["source_identity"].update(global_acceptance_epoch=True)):
            saved=json.loads(original); change(saved)
            for run in saved["runs"]: run["record_hash"]=object_hash({k:v for k,v in run.items() if k!="record_hash"})
            self.manager.path.write_text(json.dumps(saved),encoding="utf-8")
            with self.subTest(change=change),self.assertRaises(DomainError): self.new_manager()
        self.manager.path.write_bytes(original)

    def test_cancel_retains_result_without_adoption_and_busy_rejects(self):
        entered=threading.Event(); release=threading.Event()
        def slow(*args,**kwargs):
            entered.set(); release.wait(5); return synthesis_fixture(*args,**kwargs)
        with patch("hullcirq.global_workflow.synthesize_global_generic",side_effect=slow):
            self.manager.start(STAGES[0],self.job["id"]); self.assertTrue(entered.wait(5))
            run_id=self.manager._state["runs"][-1]["id"]
            with self.assertRaises(DomainError): self.manager.start(STAGES[0],self.job["id"])
            self.manager.cancel(run_id); release.set(); self.manager._worker.join(10)
        run=self.manager.run(run_id)
        self.assertEqual(run["execution_status"],"Cancelled"); self.assertEqual(run["validation_status"],"Not Checked")
        self.assertEqual(run["review_status"],"Awaiting Review")

    def test_restart_interrupts_queued_without_tool_execution(self):
        run=self.run_stage(); saved=json.loads(self.manager.path.read_text(encoding="utf-8"))
        saved["runs"][0].update(execution_status="Running",validation_status="Not Checked",review_status="Awaiting Review")
        saved["reviews"]=[]
        saved["runs"][0]["record_hash"]=object_hash({k:v for k,v in saved["runs"][0].items() if k!="record_hash"})
        self.manager.path.write_text(json.dumps(saved),encoding="utf-8")
        with patch("hullcirq.global_workflow.execute_fixed") as execute:
            reopened=self.new_manager(); self.addCleanup(reopened.close)
            self.assertEqual(reopened.run(run["id"])["execution_status"],"Interrupted"); execute.assert_not_called()

    def test_safe_escaped_netlist_hierarchy_and_reject_injection(self):
        manifest=self.job["context"]["source_manifest"]; plan=self.job["context"]["verification_plan"]
        proof=fixtures.fixture_proof(self.job["rtl"],manifest,plan,self.compiler)
        scopes=proof["hierarchy_scope_lines"]
        pe_name=next(n["module_name"] for n in manifest["nodes"] if n["node_id"]=="node-pe")
        for i,line in enumerate(scopes):
            if '"'+pe_name+'"' in line:
                scopes[i]=replaced=line.replace('"u_3_', '"pe_inst[')
                # Preserve original compiler fields; only the fixture instance name changes.
                prefix,end=replaced.split('"pe_inst[',1)
                index,tail=end.split('"',1)
                scopes[i]=prefix+'"pe_inst['+index+'].u_pe"'+tail
        hierarchy=compiler_netlist_public_hierarchy(scopes,manifest)
        self.assertTrue(all(path.startswith("dut.\\pe_inst[") and path.endswith(".u_pe ") for path in hierarchy["node-pe"]))
        instrumented,_=fixtures.instrument_public_testbench(plan,hierarchy)
        self.assertIn(".u_pe .pair_data",instrumented)
        bad=copy.deepcopy(scopes); bad[2]=bad[2].replace('"u_0_0"','"u_0_0; $finish"')
        with self.assertRaises(DomainError): compiler_netlist_public_hierarchy(bad,manifest)

    def test_fixed_artifact_allowlist_return_targets_and_durable_failure(self):
        synthesis=self.run_stage()
        self.assertEqual(self.manager.artifact(synthesis["id"],"netlist"),synthesis["netlist"])
        self.assertEqual(self.manager.artifact(synthesis["id"],"verification-plan"),self.job["context"]["verification_plan"])
        with self.assertRaises(DomainError): self.manager.artifact(synthesis["id"],"../../state.json")
        with self.assertRaises(DomainError): self.manager.review(synthesis["id"],"return_to_stage","bad future",STAGES[1])
        before=self.manager.path.read_bytes()
        with patch("hullcirq.global_workflow.os.replace",side_effect=OSError("SOFTWARE QA disk failure")):
            with self.assertRaises(OSError): self.manager.review(synthesis["id"],"changes_requested","SOFTWARE QA save failure")
        self.assertEqual(self.manager.path.read_bytes(),before)
        self.assertEqual(self.manager.run(synthesis["id"])["review_status"],"Accepted")

    def test_lowered_signedness_allowed_but_port_loss_or_order_rejected(self):
        synthesis=self.run_stage(); manifest=synthesis["source_manifest"]; netlist=synthesis["netlist"]
        netlist_public_interfaces(netlist.replace("output signed [31:0]","output [31:0]"),manifest)
        for bad in (netlist.replace("[31:0] output_data","[0:31] output_data"),
                    netlist.replace("output output_transfer","output renamed_transfer")):
            self.assertNotEqual(bad,netlist)
            with self.assertRaises(DomainError): netlist_public_interfaces(bad,manifest)

    def test_actual_tools_netlist_only_positive_and_corrupted_pe_input(self):
        """Optional isolated fixture EDA: never a live-project or model artifact."""
        compiler_path=PROJECT/".work/m2/compiler.json"; synth_path=PROJECT/".work/m2b/synthesizer.json"
        if not compiler_path.exists() or not synth_path.exists(): self.skipTest("Trusted isolated Icarus/Yosys configurations unavailable")
        from test_control_verification import SOFTWARE_FIXTURE_RTL as control
        from test_scheduler_verification import SOFTWARE_FIXTURE_RTL as scheduler
        from test_npu_nodes_verification import FIXTURES
        from test_continuous_flow import SOFTWARE_FIXTURE_RTL as pe
        from hullcirq.store import strict_loads
        compiler=strict_loads(compiler_path.read_text(encoding="utf-8-sig")); synthesizer=strict_loads(synth_path.read_text(encoding="utf-8-sig"))
        compiler["working_directory"]=str(PROJECT/".work/m2f/software-qa-icarus")
        synthesizer["working_directory"]=str(PROJECT/".work/m2f/software-qa-yosys")
        manifest=copy.deepcopy(self.job["context"]["source_manifest"]); plan=copy.deepcopy(self.job["context"]["verification_plan"])
        sources=dict(FIXTURES,**{"node-control":control,"node-scheduler":scheduler,"node-pe":pe.replace("module m2a_mac(","module hullcirq_pe(")})
        for node in manifest["nodes"]: node.update(rtl=sources[node["node_id"]],rtl_sha256=content_hash(sources[node["node_id"]]))
        rtl=fixtures.header(fixtures.top_interface(manifest["design"]))+fixtures.SOFTWARE_TOP_BODY
        synthesized=synthesize_global_generic(rtl,manifest,synthesizer)
        self.assertEqual(synthesized["validation_status"],"Passed",synthesized)
        netlist=synthesized["netlist"]
        checked=check_global_netlist(netlist,manifest,plan,compiler)
        self.assertEqual(checked["validation_status"],"Passed",checked)
        self.assertFalse(checked["source_rtl_linked"])
        top=fixtures.top_interface(manifest["design"])["module_name"]
        top_match=re.search(r'\bmodule\s+'+re.escape(top)+r'\b[\s\S]*?\bendmodule\b',netlist)
        self.assertIsNotNone(top_match)
        source=top_match[0]
        # Corrupt the actual synthesized PE port only; do not change stimulus,
        # expected results, hierarchy, other nodes, or any live project bytes.
        pattern=r'(\bhullcirq_pe\s+\S+\s*\([\s\S]*?\.pair_data\s*\()([^)]*)(\))'
        changed,count=re.subn(pattern,lambda m:m[1]+"("+m[2].strip()+" ^ 16'h0001)"+m[3],source,count=1)
        self.assertEqual(count,1,"Locate exactly one synthesized PE input for the isolated corruption")
        broken=netlist[:top_match.start()]+changed+netlist[top_match.end():]
        failed=check_global_netlist(broken,manifest,plan,compiler)
        self.assertEqual(failed["checks"]["elaboration"]["validation_status"],"Passed",failed)
        self.assertEqual(failed["validation_status"],"Failed",failed)
        self.assertIn("HULLCIRQ_FAIL",failed["stdout"])
        self.assertEqual(plan,self.job["context"]["verification_plan"])


if __name__=="__main__": unittest.main()
