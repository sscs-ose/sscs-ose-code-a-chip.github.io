"""Software-only array contract QA; never a substitute for actual EDA evidence."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import unittest

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))

from hullcirq.domain import DomainError
from hullcirq.instance_arrays import array_shape, instance_indices, instance_name, validate_endpoint, validate_design_arrays
from hullcirq import npu2_array_verification as array
from hullcirq import npu2_global_verification as explicit
from hullcirq.verification import object_hash, build_verification_plan, validate_plan, verification_template_version


def source_design():
    return json.loads((PROJECT / "examples/npu_2x2_explicit_project.json").read_text(encoding="utf-8"))


def manifest(design):
    return {"design": design, "nodes": [{"node_id": node["id"], "module_name": node["module_name"]}
                                        for node in design["nodes"]]}


def scopes(design):
    lines = ['S_root .scope module, "hullcirq_global_tb" "hullcirq_global_tb";',
             'S_top .scope module, "dut" "hullcirq_npu2_array_top", S_root;']
    for index, node in enumerate(design["nodes"]):
        names = ["pe" + lane for lane in array.LANES] if node["id"] == array.PE_ID else ["u_" + node["id"].replace("-", "_")]
        for member, name in enumerate(names):
            lines.append(f'S_n{index}_{member} .scope module, "{name}" "{node["module_name"]}", S_top;')
    return lines


class InstanceArrayTests(unittest.TestCase):
    def test_shape_and_row_major_instances_are_strict(self):
        node = {"id": "pe", "instance_array": {"rows": 2, "columns": 3}}
        self.assertEqual(array_shape(node), (2, 3))
        self.assertEqual(instance_indices(node), [[0, 0], [0, 1], [0, 2], [1, 0], [1, 1], [1, 2]])
        self.assertEqual(instance_indices({"id": "scalar"}), [None])
        self.assertEqual(instance_name(node, [1, 2]), "element_1_2")
        for bad in (None, {}, {"rows": True, "columns": 2}, {"rows": 2.0, "columns": 2},
                    {"rows": 0, "columns": 2}, {"rows": 17, "columns": 2},
                    {"rows": 2, "columns": 2, "broadcast": True}):
            with self.subTest(bad=bad), self.assertRaises(DomainError):
                array_shape({"instance_array": bad})

    def test_each_array_endpoint_requires_exact_in_range_member(self):
        node = {"id": "pe", "instance_array": {"rows": 2, "columns": 2}}
        for bad in (None, [0], [0, 0, 0], [True, 0], [0.0, 0], [-1, 0], [0, 2], "00"):
            with self.subTest(bad=bad), self.assertRaises(DomainError):
                validate_endpoint(node, {"node_id": "pe", "instance_index": bad})
        self.assertEqual(validate_endpoint(node, {"node_id": "pe", "instance_index": [1, 0]}), [1, 0])
        with self.assertRaises(DomainError):
            validate_endpoint({"id": "scalar"}, {"node_id": "scalar", "instance_index": [0, 0]})


class SharedArrayVerificationTests(unittest.TestCase):
    def setUp(self):
        self.explicit = source_design()
        self.design = array.collapse_explicit_design(self.explicit)

    def test_conversion_is_pure_and_preserves_original_job(self):
        before = object_hash(self.explicit)
        converted = array.collapse_explicit_design(self.explicit)
        self.assertEqual(object_hash(self.explicit), before)
        self.assertEqual(len(converted["nodes"]), 8)
        self.assertEqual(converted["verification_jobs"], self.explicit["verification_jobs"])
        self.assertEqual([node["module_name"] for node in converted["nodes"]].count(array.PE_MODULE), 1)
        self.assertEqual(array.recognize_design(converted)["instance_counts"][array.PE_ID], 4)
        self.assertEqual(array.original_job(converted), self.explicit["verification_jobs"][0])
        self.assertEqual(array.top_interface(converted)["module_name"], array.TOP_MODULE)
        self.assertEqual(explicit.recognize_design(self.explicit)["node_ids"], list(explicit.NODE_IDS))

    def test_verifier_projection_reconstructs_same_independent_contracts(self):
        expanded, witness = array.expand_for_contracts(self.design)
        self.assertEqual(witness["kind"], "verifier_only_expansion_witness_not_RTL_or_compiler_hierarchy")
        self.assertEqual(tuple(node["id"] for node in expanded["nodes"]), explicit.NODE_IDS)
        self.assertEqual(expanded["verification_jobs"], self.explicit["verification_jobs"])
        self.assertEqual(expanded["edges"], self.explicit["edges"])
        self.assertEqual(sum(item["logical_node_id"] == array.PE_ID for item in witness["mapping"]), 4)

    def test_mutated_shape_behavior_language_and_typed_job_fail_closed(self):
        mutations = [
            lambda d: d["nodes"][4]["instance_array"].update(rows=3),
            lambda d: d["nodes"][4].update(behavior="unverified MAC"),
            lambda d: d["edges"][4]["target"].pop("instance_index", None),
            lambda d: d["edges"][0].update(behavior="changed"),
            lambda d: d["verification_jobs"][0].update(k=3.0),
            lambda d: d["verification_jobs"][0]["A"][0].__setitem__(0, True),
            lambda d: d["global_integration"].update(one_instance_per_graph_node=True),
        ]
        # Pick a known array endpoint rather than assuming the source edge order.
        def missing_member(d):
            next(e[side] for e in d["edges"] for side in ("source", "target")
                 if e[side]["node_id"] == array.PE_ID).pop("instance_index")
        mutations[2] = missing_member
        for mutation in mutations:
            changed = copy.deepcopy(self.design); mutation(changed)
            with self.subTest(mutation=mutation), self.assertRaises(DomainError):
                array.recognize_design(changed)

    def test_all_eight_node_plans_use_new_version_actual_source_and_rebuild(self):
        before = object_hash(self.design)
        for node_id in array.NODE_IDS:
            with self.subTest(node_id=node_id):
                plan = array.build_node_plan(self.design, node_id)
                array.validate_node_plan(plan)
                self.assertEqual(plan["kind"], array.NODE_KIND)
                self.assertEqual(plan["testbench_template_version"], array.NODE_TEMPLATE)
                self.assertEqual(plan["contract"]["source_node"]["id"], node_id)
                self.assertEqual(plan["contract"]["source_job"], self.design["verification_jobs"][0])
                self.assertTrue(array.node_asserted_trace(plan))
        self.assertEqual(object_hash(self.design), before)

    def test_parent_verification_routes_new_family_before_old_fixed_node_ids(self):
        for node_id in array.NODE_IDS:
            plan = build_verification_plan(self.design, node_id)
            self.assertEqual(plan["kind"], array.NODE_KIND)
            self.assertEqual(verification_template_version(plan), array.NODE_TEMPLATE)
            validate_plan(plan)

    def test_shared_scalar_PE_tests_all_four_original_lanes_not_four_sources(self):
        plan = array.build_node_plan(self.design, array.PE_ID)
        self.assertEqual(plan["module_name"], array.PE_MODULE)
        self.assertEqual(plan["coverage"]["original_job_lanes_checked"], list(array.LANES))
        self.assertEqual(plan["coverage"]["scalar_DUT_instances"], 1)
        self.assertFalse(plan["coverage"]["full_array_concurrency_checked"])
        self.assertEqual(plan["testbench"].count(array.PE_MODULE + " dut"), 1)
        sums = [item["before"]["sum_data"] for item in plan["reference_trace"] if item["sum_data_transfer"]]
        self.assertEqual(sums, [value & 0xffffffff for value in (-47, -47, 58, 58, 56, 56, 11, 11)])

    def test_physical_and_view_edits_do_not_change_logical_node_or_global_plans(self):
        original = array.build_node_plan(self.design, array.PE_ID)
        global_plan = array.build_plan(self.design)
        changed = copy.deepcopy(self.design)
        changed["physical_design"] = {"version": "mixed-v1"}
        changed["layout"]["viewport"].update(x=30, zoom=2)
        changed["project"]["name"] = "Display name only"
        self.assertEqual(array.build_node_plan(changed, array.PE_ID), original)
        self.assertEqual(array.build_plan(changed), global_plan)

    def test_rehashed_tampered_node_plan_is_not_valid(self):
        plan = array.build_node_plan(self.design, array.PE_ID)
        plan["expanded_vectors"][4]["pair_data"] ^= 1
        plan["vector_hash"] = object_hash(plan["expanded_vectors"])
        with self.assertRaises(DomainError):
            array.validate_node_plan(plan)

    def test_global_original_job_values_and_four_shared_instances(self):
        plan = array.build_plan(self.design)
        array.validate_plan(self.design, plan)
        self.assertEqual(plan["kind"], array.PLAN_KIND)
        self.assertEqual(plan["recipe"]["expected_outputs"], [-44, 56, 59, 9])
        self.assertEqual(plan["recipe"]["source_job"], self.explicit["verification_jobs"][0])
        self.assertEqual(array.expected_instance_counts(manifest(self.design)),
                         {node_id: 4 if node_id == array.PE_ID else 1 for node_id in array.NODE_IDS})
        self.assertEqual(array.expected_pe_records(plan)[2],
                         {"node_id": array.PE_ID, "instance_index": [1, 0], "lane": "10", "inputs": 3, "outputs": 1})

    def test_actual_compiler_scope_binding_requires_exact_shared_names_and_counts(self):
        actual_scopes = scopes(self.design)
        hierarchy = array.compiler_public_hierarchy(actual_scopes, manifest(self.design))
        self.assertEqual(hierarchy[array.PE_ID], ["dut.pe" + lane for lane in array.LANES])
        for changed in (actual_scopes[:-1], actual_scopes + [actual_scopes[-1]],
                        [line.replace('"pe01"', '"pe99"') for line in actual_scopes]):
            with self.subTest(changed=changed[-1]), self.assertRaises(DomainError):
                array.compiler_public_hierarchy(changed, manifest(self.design))

    def test_monitor_checks_each_actual_shared_PE_port_and_every_saved_edge(self):
        plan = array.build_plan(self.design)
        hierarchy = array.compiler_public_hierarchy(scopes(self.design), manifest(self.design))
        tb, monitor = array.instrument_public_testbench(plan, hierarchy)
        for lane in array.LANES:
            self.assertIn("dut.pe" + lane + ".pair_data_valid", monitor)
            self.assertIn("dut.pe" + lane + ".sum_data_valid", monitor)
            self.assertIn("HULLCIRQ_PE node=npu2-pe lane=" + lane, monitor)
            self.assertNotIn("HULLCIRQ_PE node=npu2-pe" + lane, monitor)
        self.assertIn("verify_public_completion;", tb)
        self.assertGreaterEqual(monitor.count("public stream connection mismatch"), 15)

    def test_runtime_parser_rejects_missing_duplicate_or_wrong_lane_participation(self):
        plan = array.build_plan(self.design)
        lines = [f"HULLCIRQ_OUTPUT index={i} value={v} cycle={20+i}" for i, v in enumerate(plan["recipe"]["expected_outputs"])]
        lines += [f"HULLCIRQ_PUBLIC stream={name} transfers={count}" for name, count in array.public_transfer_counts(plan).items()]
        lines += [f"HULLCIRQ_PE node=npu2-pe lane={lane} inputs=3 outputs=1" for lane in array.LANES]
        lines += [f"HULLCIRQ_GLOBAL_PASS outputs=4 vector_hash={plan['vector_hash']}",
                  f"HULLCIRQ_PUBLIC_PASS vector_hash={plan['public_boundary_vector_hash']}"]
        text = "\n".join(lines)
        self.assertTrue(array.runtime_records_pass(text, plan)[0])
        for changed in (text.replace("lane=10 inputs=3", "lane=10 inputs=2"),
                        text.replace("lane=11", "lane=10"), text + "\n" + lines[-3],
                        text.replace("value=-44", "value=0")):
            self.assertFalse(array.runtime_records_pass(changed, plan)[0])


if __name__ == "__main__":
    unittest.main()
