"""Isolated software integration QA; no live project, model or tool execution."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

PROJECT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(PROJECT / "src"), str(PROJECT / "tests")]

from hullcirq import npu2_array_verification as array
from hullcirq.block_layout import expanded_targets, validate_block_plan
from hullcirq.context import build_node_context, node_fingerprint, physical_interface
from hullcirq.domain import DomainError, revision_hashes, validate_shape, validate_stage
from hullcirq.generation import scheduler_live_source_error
from hullcirq.implementation_specs import build_node_implementation_spec
from hullcirq.global_generation import (PROMPT_TEMPLATE_V5, build_global_plan, compiler_public_hierarchy,
    expected_instance_counts, expected_output_count, expected_pe_records, instrument_public_testbench,
    integration_messages, integration_projection, prompt_template, public_transfer_counts,
    required_node_ids, validate_global_plan)
from hullcirq.global_workflow import compiler_netlist_public_hierarchy, source_bundle, synthesis_script
from hullcirq.presentation_revision import same_source_design
from hullcirq.store import ProjectStore
from hullcirq.verification import build_verification_plan, content_hash, object_hash
from hullcirq.workflow import ensure_current_verification_plan
from hullcirq.workspace import WorkspaceRegistry
from hullcirq.workspace_server import workspace_post
from test_npu2_array_verification import source_design, scopes


def complete_manifest(design):
    nodes = []
    for node in design["nodes"]:
        # Deliberately nonfunctional software-only RTL fixture. No checker or
        # tool receives it, and it cannot become actual project evidence.
        rtl = "module " + node["module_name"] + "; endmodule\n"
        nodes.append({"node_id": node["id"], "module_name": node["module_name"],
                      "public_interface": physical_interface(design, node),
                      "rtl": rtl, "rtl_sha256": content_hash(rtl)})
    return {"design": copy.deepcopy(design), "nodes": nodes}


def actual_region_plan(design):
    targets = expanded_targets(design)
    return {"version": "block-regions-v1", "core_um": [10, 10, 1210, 1210], "regions": [
        {"id": "block_" + str(index), "targets": [target],
         "rect_um": [10 + index % 4 * 300, 10 + index // 4 * 300,
                     310 + index % 4 * 300, 310 + index // 4 * 300]}
        for index, target in enumerate(targets)]}


def software_only_spec_sources(design, node_id):
    """Synthetic S04/S05/S06 records for the pure S07 consistency function.

    No compiler/model is invoked and no fixture is saved into a system store.
    Executed/Passed flags and pass markers are MOCK DATA for exercising the
    existing proof-schema guards, never evidence of actual circuit execution.
    """
    plan = build_verification_plan(design, node_id)
    interface = physical_interface(design, next(node for node in design["nodes"] if node["id"] == node_id))
    declarations = []
    for port in interface["ports"]:
        declarations.append(port["direction"] + " wire" + (" signed" if port["signed"] else "")
                            + (f" [{port['width']-1}:0]" if port["width"] > 1 else "") + " " + port["name"])
    rtl = "module " + interface["module_name"] + " (\n" + ",\n".join(declarations) + ");\nendmodule\n"
    rtl_hash = content_hash(rtl)
    source_hash = node_fingerprint(design, node_id)
    candidate = {"id": "software-only-candidate-" + node_id, "node_id": node_id,
                 "revision_id": "software-only-revision", "execution_status": "Completed",
                 "validation_status": "Passed", "input_hash": source_hash,
                 "rtl": rtl, "rtl_sha256": rtl_hash, "verification_plan": None,
                 "evidence_kind": "software_qa_fixture_not_actual_execution",
                 "checks": {"interface": {"validation_status": "Passed"}}}
    common = {"candidate_id": candidate["id"], "node_id": node_id, "revision_id": candidate["revision_id"],
              "execution_status": "Completed", "validation_status": "Passed", "input_hash": source_hash,
              "design_hash": revision_hashes(design)["semantic_hash"], "rtl_sha256": rtl_hash,
              "workflow_scope_version": "stage-boundary-v2", "module_name": interface["module_name"],
              "evidence_kind": "software_qa_fixture_not_actual_execution", "netlist": rtl, "netlist_sha256": rtl_hash}
    synthesis = {**copy.deepcopy(common), "id": "software-only-synthesis-" + node_id, "stage_id": "local_synthesis",
                 "verification_plan": None, "vector_hash": None, "testbench_sha256": None,
                 "checks": {"validation_status": "Passed", "executed": True, "exit_code": 0,
                            "rtl_sha256": rtl_hash, "netlist_sha256": rtl_hash, "netlist": rtl,
                            "scope": "generic_technology_independent_no_pdk_no_delay",
                            "fixture_notice": "MOCK DATA; no actual synthesis executed"}}
    marker = f"HULLCIRQ_PASS vectors={plan['vector_count']} vector_hash={plan['vector_hash']}"
    simulation = {**copy.deepcopy(common), "id": "software-only-simulation-" + node_id,
                  "stage_id": "local_netlist_simulation", "prior_run_id": synthesis["id"],
                  "verification_plan": plan, "vector_hash": plan["vector_hash"],
                  "testbench_sha256": plan["testbench_sha256"],
                  "checks": {"validation_status": "Passed", "executed": True, "exit_code": 0,
                             "rtl_sha256": rtl_hash, **{key: copy.deepcopy(plan[key]) for key in
                                 ("vector_hash", "testbench_sha256", "reference_trace_hash", "vector_count", "coverage")},
                             "stdout": "SOFTWARE_QA_FIXTURE_NOT_ACTUAL_EXECUTION\n" + marker,
                             "commands": [{"executed": True, "status": "Completed", "exit_code": 0,
                                           "command": ["SOFTWARE_QA_NOT_EXECUTED"], "stdout": marker if index == 2 else ""}
                                          for index in range(3)],
                             "scope": "software_qa_mock_execution_schema_only"}}
    for run in (synthesis, simulation):
        run["record_hash"] = object_hash(run)
    return design, candidate, synthesis, simulation


class ArrayIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.design = array.collapse_explicit_design(source_design())

    def test_graph_member_aware_drivers_distinguish_four_PE_instances(self):
        validate_shape(self.design)
        findings = validate_stage(self.design, "graph_editor")
        self.assertFalse([finding for finding in findings if finding["severity"] == "error"], findings)
        changed = copy.deepcopy(self.design)
        incoming = [edge for edge in changed["edges"] if edge["target"]["node_id"] == array.PE_ID]
        incoming[1]["target"]["instance_index"] = copy.deepcopy(incoming[0]["target"]["instance_index"])
        self.assertIn("multiple_drivers", [finding["code"] for finding in validate_stage(changed, "graph_editor")])

    def test_local_context_contains_original_job_array_shape_and_member_endpoints(self):
        pe = build_node_context(self.design, "software-qa", array.PE_ID)
        self.assertEqual(pe["context"]["design_verification_job"], self.design["verification_jobs"][0])
        self.assertEqual(pe["context"]["node"]["instance_array"], {"rows": 2, "columns": 2})
        self.assertEqual(pe["interface"]["module_name"], array.PE_MODULE)
        self.assertEqual(len(pe["interface"]["ports"]), 8)
        dispatcher = build_node_context(self.design, "software-qa", "npu2-dispatcher")
        boundary = next(item for item in dispatcher["context"]["adjacent_interfaces"] if item["node_id"] == array.PE_ID)
        self.assertEqual(boundary["instance_array"], {"rows": 2, "columns": 2})
        self.assertEqual(len([edge for edge in pe["context"]["connected_edges"]
                              if any(edge[side].get("instance_index") == [1, 1] for side in ("source", "target"))]), 2)

    def test_physical_only_edits_leave_exact_logical_source_and_plans_unchanged(self):
        original = copy.deepcopy(self.design)
        physical = copy.deepcopy(original)
        physical["physical_design"] = actual_region_plan(physical)
        validate_block_plan(physical["physical_design"], physical)
        self.assertEqual(revision_hashes(physical)["semantic_hash"], revision_hashes(original)["semantic_hash"])
        source_store = SimpleNamespace(snapshot=lambda revision_id: copy.deepcopy(original),
                                       envelope=lambda: {"design": physical})
        self.assertEqual(same_source_design(source_store, "software-qa"), original)
        self.assertEqual(build_global_plan(physical), build_global_plan(original))
        for node_id in array.NODE_IDS:
            self.assertEqual(node_fingerprint(physical, node_id), node_fingerprint(original, node_id))
            self.assertEqual(build_verification_plan(physical, node_id), build_verification_plan(original, node_id))

    def test_changed_or_typed_invalid_original_job_fails_current_plan_guards(self):
        plan = build_verification_plan(self.design, array.PE_ID)
        record = {"node_id": array.PE_ID, "verification_plan": plan}
        self.assertIsNone(scheduler_live_source_error(self.design, record))
        ensure_current_verification_plan(self.design, array.PE_ID, plan)
        for mutate in (lambda d: d["verification_jobs"][0].update(k=3.0),
                       lambda d: d["verification_jobs"][0]["A"][0].__setitem__(0, True),
                       lambda d: d["verification_jobs"][0]["A"][0].__setitem__(0, -7)):
            changed = copy.deepcopy(self.design); mutate(changed)
            for node_id in array.NODE_IDS:
                self.assertNotEqual(node_fingerprint(changed, node_id), node_fingerprint(self.design, node_id))
            self.assertIsNotNone(scheduler_live_source_error(changed, record))
            with self.assertRaises(DomainError):
                ensure_current_verification_plan(changed, array.PE_ID, plan)

    def test_old_prompt_golden_qa_v1_through_v4_still_passes(self):
        # Reuse independent pre-array golden fixtures. Their adapters are
        # explicitly mocked software records, never actual compiler results.
        from test_global_prompt_projection import GlobalPromptProjectionTests
        for name in ("test_v1_golden_prompt_and_v2_preserve_headers_algorithm_and_plan",
                     "test_explicit_v3_golden_is_unchanged_and_v4_ends_with_exact_repair_correction"):
            case = GlobalPromptProjectionTests(name)
            qa = PROJECT / ".work" / "array_qa"
            qa.mkdir(parents=True, exist_ok=True)
            with patch("tempfile.tempdir", str(qa)):
                try:
                    case.setUp()
                    getattr(case, name)()
                finally:
                    case.doCleanups()

    def test_V5_prompt_uses_one_PE_definition_and_explicit_member_endpoints(self):
        manifest = complete_manifest(self.design)
        before = object_hash(manifest)
        self.assertEqual(prompt_template(self.design), PROMPT_TEMPLATE_V5)
        projection = integration_projection(manifest)
        self.assertEqual(len(projection["adopted_modules"]), 8)
        self.assertEqual(projection["instance_arrays"], [{"node_id": array.PE_ID, "module_name": array.PE_MODULE,
                          "rows": 2, "columns": 2, "instance_names": ["pe00", "pe01", "pe10", "pe11"]}])
        endpoints = [endpoint for edge in projection["edges"] for endpoint in edge[:2]]
        for lane in array.LANES:
            suffix = "[" + lane[0] + "," + lane[1] + "]"
            self.assertIn(array.PE_MODULE + suffix + ".pair_data", endpoints)
            self.assertIn(array.PE_MODULE + suffix + ".sum_data", endpoints)
        messages = integration_messages(manifest, "Software QA final correction")
        self.assertIn("ONE adopted scalar module", messages[-1]["content"])
        self.assertTrue(messages[-1]["content"].endswith("Software QA final correction"))
        self.assertEqual(object_hash(manifest), before)

    def test_S08_S09_S10_dispatch_keep_eight_sources_and_eleven_actual_instances(self):
        manifest = complete_manifest(self.design)
        self.assertEqual(required_node_ids(self.design), array.NODE_IDS)
        plan = build_global_plan(self.design)
        validate_global_plan(self.design, plan)
        files = source_bundle("module " + array.TOP_MODULE + "; endmodule\n", manifest)
        self.assertEqual(len(files), 9)
        self.assertEqual(sum(item["module_name"] == array.PE_MODULE for item in files), 1)
        self.assertEqual(synthesis_script(manifest).count("read_verilog "), 9)
        counts = expected_instance_counts(manifest)
        self.assertEqual(sum(counts.values()), 11)
        self.assertEqual(counts[array.PE_ID], 4)
        self.assertEqual(expected_output_count(plan), 4)
        self.assertEqual(len(expected_pe_records(plan)), 4)
        actual = scopes(self.design)
        rtl_hierarchy = compiler_public_hierarchy(actual, manifest)
        synthesized_hierarchy = compiler_netlist_public_hierarchy(actual, manifest)
        self.assertEqual(rtl_hierarchy, synthesized_hierarchy)
        instrumented, monitor = instrument_public_testbench(plan, synthesized_hierarchy)
        self.assertIn(array.TOP_MODULE + " dut", instrumented)
        for lane in array.LANES:
            self.assertIn("dut.pe" + lane + ".sum_data", monitor)
        self.assertEqual(public_transfer_counts(plan)["fifo_output"], 4)

    def test_full_S07_specification_builds_for_all_eight_mocked_scope_chains(self):
        for node_id in array.NODE_IDS:
            with self.subTest(node_id=node_id):
                data = software_only_spec_sources(copy.deepcopy(self.design), node_id)
                before = object_hash(data)
                plan = data[3]["verification_plan"]
                trace_hash = object_hash(plan["reference_trace"])
                document = build_node_implementation_spec(*data)
                self.assertEqual(object_hash(data), before)
                self.assertEqual(object_hash(plan["reference_trace"]), trace_hash)
                self.assertEqual(document["checks"]["validation_status"], "Passed")
                self.assertEqual(document["original_requirements"]["node"]["id"], node_id)
                self.assertEqual(document["lineage"]["verification_plan_sha256"], object_hash(plan))
                self.assertEqual(document["lineage"]["reference_trace_hash"], trace_hash)
                self.assertEqual(document["public_interface"]["module_name"], array.MODULE_NAMES[node_id])
                self.assertGreater(document["observed_facts"]["checked_assertion_count"], 0)
                if node_id == "npu2-fifo":
                    self.assertNotIn("stimulus_timing", document["observed_facts"])
                    self.assertNotIn("harness_maximum_attempts_per_offer", document["observed_facts"])
                    self.assertNotIn("recipe_step", document["observed_facts"].get("vector_unit", ""))
                else:
                    self.assertEqual(document["observed_facts"]["harness_maximum_attempts_per_offer"], 64)


class ArrayVariantPersistenceTests(unittest.TestCase):
    def setUp(self):
        qa = PROJECT / ".work" / "array_qa"
        qa.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=qa)
        self.addCleanup(self.temp.cleanup)
        self.registry = WorkspaceRegistry(Path(self.temp.name) / "workspace")
        self.source = self.registry.create_project("Explicit QA", "Original", "hullcirq_npu2_top")
        self.resolved = self.registry.resolve_system(self.source["project_id"], self.source["system_id"])
        store = ProjectStore(self.resolved["path"])
        old = store.envelope()
        design = source_design()
        design["project"] = old["design"]["project"]
        design["system"] = old["design"]["system"]
        store.save(design, old["revision"]["id"])
        policy = store.review_policy()
        store.set_review_policy("accept_on_pass", True, "Software fixture authorization", policy["id"])
        current = store.envelope()
        store.validate("global_settings", current["revision"]["id"])
        # Explicitly non-executable retained fixture history checks no copying.
        (self.resolved["path"] / "generation.json").write_text('{"software_fixture_history":"retained"}\n', encoding="utf-8")

    def test_new_variant_is_result_free_manual_policy_and_source_bytes_unchanged(self):
        before = {path.name: (hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_mtime_ns)
                  for path in self.resolved["path"].glob("*.json")}
        result = self.registry.create_array_variant(self.source["project_id"], self.source["system_id"], "Shared array QA")
        resolved = self.registry.resolve_system(result["project_id"], result["system_id"])
        self.assertNotEqual(result["project_id"], self.source["project_id"])
        self.assertEqual([path.name for path in resolved["path"].glob("*.json")], ["state.json"])
        new_store = ProjectStore(resolved["path"])
        envelope = new_store.envelope()
        self.assertEqual(envelope["runs"], [])
        self.assertEqual(envelope["reviews"], [])
        self.assertEqual(envelope["review_policy"]["mode"], "manual")
        self.assertTrue(all(item["execution_status"] == "Not Run" for item in envelope["workflow"]))
        self.assertEqual(len(envelope["design"]["nodes"]), 8)
        self.assertEqual(envelope["design"]["verification_jobs"], source_design()["verification_jobs"])
        self.assertEqual(envelope["design"]["copy_provenance"]["source_state_sha256"], before["state.json"][0])
        after = {path.name: (hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_mtime_ns)
                 for path in self.resolved["path"].glob("*.json")}
        self.assertEqual(before, after)

    def test_failed_unrecognized_conversion_creates_no_project_or_source_mutation(self):
        store = ProjectStore(self.resolved["path"])
        envelope = store.envelope(); altered = copy.deepcopy(envelope["design"])
        altered["nodes"][4]["behavior"] = "Unrecognized behavior"
        store.save(altered, envelope["revision"]["id"])
        original = (self.resolved["path"] / "state.json").read_bytes()
        before = self.registry.catalog()
        with self.assertRaises(DomainError):
            self.registry.create_array_variant(self.source["project_id"], self.source["system_id"], "Rejected QA")
        self.assertEqual(self.registry.catalog(), before)
        self.assertEqual((self.resolved["path"] / "state.json").read_bytes(), original)

    def test_explicit_route_checks_session_idle_then_activates_only_new_result(self):
        runtime = Mock()
        runtime.registry = self.registry
        runtime.identity = {"project_id": self.source["project_id"], "system_id": self.source["system_id"]}
        runtime.response.return_value = {"software_fixture": "response"}
        handler = SimpleNamespace(server=SimpleNamespace(workspace=runtime), _required=lambda value, key: value[key])
        result = workspace_post(handler, "/api/workspace/array-variant", {
            "project_id": self.source["project_id"], "system_id": self.source["system_id"], "name": "Route QA"})
        runtime.require_management_session.assert_called_once_with(handler)
        runtime.require_idle.assert_called_once_with(handler)
        activated = runtime.activate_result.call_args.args[0]
        self.assertNotEqual(activated["project_id"], self.source["project_id"])
        self.assertEqual(result, {"software_fixture": "response"})


if __name__ == "__main__":
    unittest.main()
