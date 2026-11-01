"""Read-only integration QA for all saved contracts and historical evidence."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import unittest

PROJECT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PROJECT/"src"))
from hullcirq.context import build_node_context,node_fingerprint,physical_interface
from hullcirq.domain import DomainError,sideband_findings,validate_stage
from hullcirq.generation import GenerationManager,scheduler_live_source_error
from hullcirq.implementation_specs import build_node_implementation_spec
from hullcirq.verification import build_verification_plan,object_hash,validate_plan,verification_template_version

COUNTS={"node-control":14,"node-buffer":11,"node-scheduler":17,"node-pe":8,"node-post":11,"node-fifo":9}
PROJECTED=[node for node in COUNTS if node!="node-pe"]


def design():return json.loads((PROJECT/"examples/npu_all_nodes_project.json").read_text(encoding="utf-8"))


class AllNodeDispatchTests(unittest.TestCase):
    def test_all_six_contracts_dispatch_validate_and_export_exact_physical_boundaries(self):
        original=design()
        for node_id,count in COUNTS.items():
            with self.subTest(node=node_id):
                node=next(n for n in original["nodes"] if n["id"]==node_id)
                interface=physical_interface(original,node)
                self.assertEqual(len(interface["ports"]),count)
                plan=build_verification_plan(original,node_id)
                validate_plan(plan)
                self.assertEqual(build_verification_plan(original,node_id,verification_template_version(plan)),plan)
                self.assertEqual(plan["module_name"],node["module_name"])
                self.assertEqual(plan["node_input_hash"],node_fingerprint(original,node_id))
                for port in node["ports"]:
                    physical={p["name"]:p for p in interface["ports"]}
                    if port["protocol"]=="raw":
                        self.assertIn(port["name"],physical)
                        self.assertNotIn(port["name"]+"_valid",physical)
                        self.assertNotIn(port["name"]+"_ready",physical)
                        self.assertEqual(physical[port["name"]]["sideband"],port["sideband"])

    def test_original_matrix_job_and_pe42_inputs_are_preserved_exactly(self):
        original=design()
        preserved=json.loads((PROJECT/"results/npu_pe_continuous_flow/design.json").read_text(encoding="utf-8"))
        self.assertEqual(object_hash(original["verification_jobs"]),object_hash(preserved["verification_jobs"]))
        pe=next(n for n in original["nodes"] if n["id"]=="node-pe")
        old=next(n for n in preserved["nodes"] if n["id"]=="node-pe")
        self.assertEqual(object_hash(pe["verification"]),object_hash(old["verification"]))
        self.assertEqual(len(pe["verification"]["vectors"]),42)
        for node in original["nodes"]:
            if node["id"] in PROJECTED:self.assertEqual(object_hash(node["verification"]["source_job"]),object_hash(original["verification_jobs"][0]))

    def test_each_projected_node_rejects_changed_current_canonical_job_and_invalidates_fingerprint(self):
        original=design();changed=copy.deepcopy(original)
        changed["verification_jobs"][0]["A"][0][0]=-127
        for node in PROJECTED:
            with self.subTest(node=node):
                plan=build_verification_plan(original,node)
                self.assertNotEqual(node_fingerprint(original,node),node_fingerprint(changed,node))
                validate_plan(plan)  # Historical artifact remains valid historical evidence.
                self.assertIsNotNone(scheduler_live_source_error(changed,{"node_id":node,"verification_plan":plan}))
                with self.assertRaises(DomainError):build_verification_plan(changed,node)
                value,error=GenerationManager._verification_plan(changed,node)
                self.assertIsNone(value);self.assertIsNotNone(error)

    def test_normalized_hash_float_equivalence_never_revives_invalid_live_source(self):
        original=design();changed=copy.deepcopy(original);changed["verification_jobs"][0]["k"]=4.0
        for node in PROJECTED:
            with self.subTest(node=node):
                # Existing generic hashes intentionally normalize 4.0 to4;
                # the strict live proof independently rejects its invalid type.
                self.assertEqual(node_fingerprint(original,node),node_fingerprint(changed,node))
                plan=build_verification_plan(original,node)
                self.assertIsNotNone(scheduler_live_source_error(changed,{"node_id":node,"verification_plan":plan}))
                with self.assertRaises(DomainError):build_verification_plan(changed,node)

    def test_consistently_changed_new_job_cannot_relabel_old_frozen_plans_or_s07_proof(self):
        original=design();changed=copy.deepcopy(original)
        changed["verification_jobs"][0]["A"][0][0]=-127
        for item in changed["nodes"]:
            if item["id"] in PROJECTED:item["verification"]["source_job"]=copy.deepcopy(changed["verification_jobs"][0])
        for node in PROJECTED:
            with self.subTest(node=node):
                old=build_verification_plan(original,node);new=build_verification_plan(changed,node)
                self.assertNotEqual(object_hash(old),object_hash(new))
                self.assertIsNotNone(scheduler_live_source_error(changed,{"node_id":node,"verification_plan":old}))
                with self.assertRaises(DomainError):
                    build_node_implementation_spec(changed,{"node_id":node,"verification_plan":old},{},{})

    def test_raw_busy_level_and_fifo_completion_pulse_are_explicit_checked_boundaries(self):
        original=design();control=next(n for n in original["nodes"] if n["id"]=="node-control")
        busy=next(p for p in control["ports"] if p["name"]=="busy")
        self.assertEqual(busy["sideband"]["kind"],"level")
        self.assertIsNone(busy["sideband"]["associated_port_id"])
        self.assertEqual(sideband_findings(control,busy),[])
        bad=copy.deepcopy(busy);bad["width"]=2
        self.assertIn("invalid_sideband_level",[code for code,_ in sideband_findings(control,bad)])
        fifo=next(n for n in original["nodes"] if n["id"]=="node-fifo")
        pulse=next(p for p in fifo["ports"] if p["name"]=="output_transfer")
        self.assertEqual(pulse["sideband"]["kind"],"pulse")
        target=next(p for p in control["ports"] if p["name"]=="output_transfer")
        links=[e for e in original["edges"] if e["source"]=={"node_id":"node-fifo","port_id":pulse["id"]}
               and e["target"]=={"node_id":"node-control","port_id":target["id"]}]
        self.assertEqual(len(links),1)
        self.assertEqual(links[0]["protocol"],"raw")
        self.assertFalse([f for f in validate_stage(original,"graph_editor") if f["severity"]=="error"])

    def test_v8_hardware_view_keeps_original_inputs_and_strict_references_in_saved_artifact(self):
        original=design()
        for node in COUNTS:
            context=build_node_context(original,"qa-readonly",node,template_version="node-verilog-2005-v8")
            full=context["context"]
            payload=json.loads(context["messages"][1]["content"].split("\nRequired interface header")[0])
            self.assertEqual(full["node"]["verification"],next(n for n in original["nodes"] if n["id"]==node)["verification"])
            self.assertNotIn("verification",payload["design_context"]["node"])
            self.assertEqual(payload["verification_references"]["node_verification"]["object_sha256"],object_hash(full["node"]["verification"]))
            if node in PROJECTED:
                self.assertEqual(full["design_verification_job"],original["verification_jobs"][0])
                self.assertEqual(payload["verification_references"]["design_verification_job"]["object_sha256"],object_hash(original["verification_jobs"][0]))

    def test_historical_pe_and_scheduler_plans_and_specs_rebuild_without_migration(self):
        source=PROJECT/"results/npu_scheduler_continuous_flow"
        original=json.loads((source/"design.json").read_text(encoding="utf-8"))
        for node in ("node-pe","node-scheduler"):
            directory=source/"nodes"/node
            read=lambda name:json.loads((directory/name).read_text(encoding="utf-8"))
            plan=read("verification_plan.json")
            self.assertEqual(build_verification_plan(original,node,verification_template_version(plan)),plan)
            validate_plan(plan)
            result=build_node_implementation_spec(original,read("candidate_record.json"),read("synthesis_record.json"),read("netlist_record.json"))
            self.assertEqual(result,read("node_implementation_spec.json"))


if __name__=="__main__":unittest.main()
