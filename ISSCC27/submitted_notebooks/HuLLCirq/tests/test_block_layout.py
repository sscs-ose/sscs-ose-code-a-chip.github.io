"""Isolated planning/recipe QA only; no model, OpenROAD or live-data writes."""
import ast
import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tests")]
from hullcirq.block_layout import (BLOCK_ARTIFACTS, VERSION, MAPPED_TIE_MASTER, build_ownership, effective_configuration,
    expanded_targets, mapped_tie_names, protect_mapped_ties, object_hash, source_input, validate_block_plan, validate_capacity, validate_def_binding, validate_placement)
from hullcirq.domain import DomainError
from hullcirq.physical_tools import (BLOCK_FLOW_SHA, BLOCK_RUNTIME_SHA, configuration_projection, fixed_commands)
from hullcirq.physical_workflow import _file_ids, _required_files
from test_physical_tools import PhysicalToolTests
from test_physical_workflow import PhysicalWorkflowTests


class BlockLayoutTests(unittest.TestCase):
    def setUp(self):
        self.design = {"nodes": [{"id": "npu2-pe", "module_name": "pe", "instance_array": {"rows": 2, "columns": 2}}]}
        self.plan = {"version": VERSION, "core_um": [10, 10, 110, 110], "regions": [
            {"id": "pe" + str(r) + str(c), "targets": [{"node_id": "npu2-pe", "instance_index": [r, c]}],
             "rect_um": [10 + c * 50, 10 + r * 50, 60 + c * 50, 60 + r * 50]} for r in range(2) for c in range(2)]}
        self.inputs = {"version": VERSION, "top_module": "top", "design": self.design, "plan": self.plan,
                       "plan_sha256": object_hash(self.plan), "source_manifest_sha256": "a" * 64}
        self.synthesis = {"modules": {"top": {"cells": {"pe" + str(r) + str(c): {"type": "pe"} for r in range(2) for c in range(2)}},
            "pe": {"cells": {"sum_reg[0]": {"type": "sky130_fd_sc_hd__dfxtp_1"}}}}}

    def test_plan_expands_one_logical_node_into_four_independent_targets(self):
        original = copy.deepcopy(self.plan)
        self.assertEqual(len(expanded_targets(self.design)), 4)
        self.assertEqual(validate_block_plan(self.plan, self.design), original)
        self.assertEqual(self.plan, original)

    def test_absent_and_explicit_mixed_are_distinct_supported_modes(self):
        self.assertIsNone(validate_block_plan(None, self.design))
        self.assertEqual(validate_block_plan({"version": "mixed-v1"}, self.design), {"version": "mixed-v1"})
        with self.assertRaises(DomainError): validate_block_plan({"version": "mixed-v1", "regions": []}, self.design)

    def test_overlap_outside_nonfinite_bool_duplicate_missing_target_rejected(self):
        mutations = [lambda p: p["regions"][1].update(rect_um=p["regions"][0]["rect_um"]),
                     lambda p: p["regions"][0].update(rect_um=[0, 0, 20, 20]),
                     lambda p: p["core_um"].__setitem__(2, float("nan")),
                     lambda p: p["core_um"].__setitem__(2, True),
                     lambda p: p["regions"][1].update(id=p["regions"][0]["id"]),
                     lambda p: p["regions"].pop(),
                     lambda p: p["regions"][1].update(targets=p["regions"][0]["targets"]),
                     lambda p: p["regions"][0]["targets"][0].update(instance_index=[False, 0])]
        for mutation in mutations:
            invalid = copy.deepcopy(self.plan); mutation(invalid)
            with self.subTest(mutation=mutation), self.assertRaises(DomainError): validate_block_plan(invalid, self.design)

    def test_scalar_node_cannot_be_indexed_and_array_requires_index(self):
        scalar = {"nodes": [{"id": "one", "module_name": "one"}]}
        p = {"version": VERSION, "core_um": [10, 10, 110, 110], "regions": [{"id": "r", "rect_um": [10, 10, 110, 110], "targets": [{"node_id": "one"}]}]}
        validate_block_plan(p, scalar)
        p["regions"][0]["targets"][0]["instance_index"] = [0, 0]
        with self.assertRaises(DomainError): validate_block_plan(p, scalar)
        p = copy.deepcopy(self.plan); p["regions"][0]["targets"][0].pop("instance_index")
        with self.assertRaises(DomainError): validate_block_plan(p, self.design)

    def test_exact_mapped_hierarchy_ownership_not_functional_color(self):
        ownership = build_ownership(self.synthesis, self.inputs)
        self.assertEqual([r["cells"][0]["name"] for r in ownership["regions"]], ["pe00/sum_reg[0]", "pe01/sum_reg[0]", "pe10/sum_reg[0]", "pe11/sum_reg[0]"])
        self.assertEqual(ownership["ownership_origin"], "exact_preserved_technology_mapped_module_hierarchy")
        self.assertEqual(sum(len(r["cells"]) for r in ownership["regions"]), 4)

    def tie_ownership(self):
        synthesis = copy.deepcopy(self.synthesis)
        synthesis["modules"]["pe"]["cells"]["tie_constant"] = {"type": MAPPED_TIE_MASTER}
        return build_ownership(synthesis, self.inputs)

    def test_explicit_mapped_tie_protection_only_touches_exact_owned_cells(self):
        class Instance:
            def __init__(self, master): self.master, self.protected = master, False
            def getMaster(self): return self
            def getName(self): return self.master
            def setDoNotTouch(self, value): self.protected = value
            def isDoNotTouch(self): return self.protected
        ownership = self.tie_ownership()
        instances = {cell["name"]: Instance(cell["master"]) for region in ownership["regions"] for cell in region["cells"]}
        instances["inserted_support_tie"] = Instance(MAPPED_TIE_MASTER)
        expected = ["pe" + lane + "/tie_constant" for lane in ("00", "01", "10", "11")]
        self.assertEqual(protect_mapped_ties(ownership, instances), expected)
        self.assertEqual(mapped_tie_names(ownership), expected)
        self.assertEqual(sorted(name for name, inst in instances.items() if inst.protected), expected)
        instances[expected[0]].master = "sky130_fd_sc_hd__buf_1"
        with self.assertRaises(DomainError): protect_mapped_ties(ownership, instances)
        instances.pop(expected[0])
        with self.assertRaises(DomainError): protect_mapped_ties(ownership, instances)

    def test_missing_or_unretained_mapped_tie_protection_is_rejected(self):
        class Unprotected:
            def getMaster(self): return self
            def getName(self): return MAPPED_TIE_MASTER
            def setDoNotTouch(self, value): pass
            def isDoNotTouch(self): return False
        ownership = self.tie_ownership()
        with self.assertRaises(DomainError):
            protect_mapped_ties(ownership, {name: Unprotected() for name in mapped_tie_names(ownership)})

    def test_final_tie_proof_cannot_waive_missing_identity_master_or_protection(self):
        ownership, proof = self.proof()
        for region in ownership["regions"]:
            region["cells"][0]["master"] = MAPPED_TIE_MASTER
        proof["ownership_sha256"] = object_hash(ownership)
        for cell in proof["cells"]:
            cell.update(master=MAPPED_TIE_MASTER, mapped_tie_protected=True)
        validate_placement(ownership, proof)
        for mutation in (lambda p: p["cells"][0].pop("mapped_tie_protected"),
                         lambda p: p["cells"][0].update(mapped_tie_protected=False),
                         lambda p: p["cells"][0].update(master="sky130_fd_sc_hd__buf_1"),
                         lambda p: p["cells"].pop()):
            invalid = copy.deepcopy(proof); mutation(invalid)
            with self.subTest(mutation=mutation), self.assertRaises(DomainError): validate_placement(ownership, invalid)

    def test_capacity_records_exact_owned_tie_protection(self):
        ownership = self.tie_ownership()
        capacity = {"version": VERSION, "ownership_sha256": object_hash(ownership),
                    "protected_mapped_ties": mapped_tie_names(ownership), "regions": [
                        {"id": r["id"], "cell_area_um2": 70, "row_area_um2": 100, "maximum_utilization": 0.7}
                        for r in ownership["regions"]]}
        validate_capacity(ownership, capacity)
        capacity["protected_mapped_ties"].pop()
        with self.assertRaises(DomainError): validate_capacity(ownership, capacity)

    def test_flattened_missing_lane_and_nonmapped_leaf_rejected(self):
        for mutation in (lambda s: s["modules"]["top"]["cells"].pop("pe11"),
                         lambda s: s["modules"]["pe"]["cells"]["sum_reg[0]"].update(type="$add"),
                         lambda s: s["modules"]["pe"].update(cells={}),
                         lambda s: s["modules"]["pe"]["cells"]["sum_reg[0]"].update(type="pe")):
            invalid = copy.deepcopy(self.synthesis); mutation(invalid)
            with self.subTest(mutation=mutation), self.assertRaises(DomainError): build_ownership(invalid, self.inputs)

    def proof(self):
        ownership = build_ownership(self.synthesis, self.inputs)
        cells = []
        for region in ownership["regions"]:
            x, y = region["rect_um"][:2]
            cells.append({"name": region["cells"][0]["name"], "master": "sky130_fd_sc_hd__dfxtp_1", "region_id": region["id"],
                          "bbox_um": [x, y, x + 1, y + 2], "origin_dbu": [x * 1000, y * 1000], "orient": "R0", "placed": True, "group_member": True})
        return ownership, {"version": VERSION, "ownership_sha256": object_hash(ownership), "database_units_per_micron": 1000, "cells": cells, "validation_status": "Passed"}

    def test_final_cell_containment_group_membership_and_exact_count(self):
        ownership, proof = self.proof(); validate_placement(ownership, proof)
        for mutation in (lambda p: p["cells"][0].update(bbox_um=[9, 10, 11, 12]),
                         lambda p: p["cells"][0].update(group_member=False),
                         lambda p: p["cells"][0].update(placed=False), lambda p: p["cells"].pop(),
                         lambda p: p["cells"].__setitem__(1, p["cells"][0]),
                         lambda p: p.update(ownership_sha256="0" * 64)):
            invalid = copy.deepcopy(proof); mutation(invalid)
            with self.subTest(mutation=mutation), self.assertRaises(DomainError): validate_placement(ownership, invalid)

    def test_capacity_requires_actual_finite_row_area_fixed_seventy_percent(self):
        ownership, _ = self.proof()
        capacity = {"version": VERSION, "ownership_sha256": object_hash(ownership), "regions": [
            {"id": r["id"], "cell_area_um2": 70, "row_area_um2": 100, "maximum_utilization": 0.7} for r in ownership["regions"]]}
        validate_capacity(ownership, capacity)
        for value in (True, None, float("nan"), 71):
            invalid = copy.deepcopy(capacity); invalid["regions"][0]["cell_area_um2"] = value
            with self.subTest(value=value), self.assertRaises(DomainError): validate_capacity(ownership, invalid)

    def test_final_def_bound_to_actual_cell_positions_masters_and_units(self):
        ownership, proof = self.proof()
        text = "UNITS DISTANCE MICRONS 1000 ;\nCOMPONENTS 4 ;\n" + "\n".join(
            "- " + c["name"] + " " + c["master"] + " + PLACED ( " + str(c["origin_dbu"][0]) + " " + str(c["origin_dbu"][1]) + " ) N ;" for c in proof["cells"]) + "\nEND COMPONENTS\n"
        validate_def_binding(text, ownership, proof)
        scaled = text.replace('MICRONS 1000', 'MICRONS 100')
        for cell in proof['cells']:
            x,y = cell['origin_dbu']
            scaled = scaled.replace('( '+str(x)+' '+str(y)+' )','( '+str(x//10)+' '+str(y//10)+' )')
        validate_def_binding(scaled, ownership, proof)
        for invalid in (text.replace("MICRONS 1000", "MICRONS 2000"), text.replace("10000 10000", "10001 10000"), text.replace("dfxtp_1", "dfxtp_2")):
            with self.assertRaises(DomainError): validate_def_binding(invalid, ownership, proof)

    def test_effective_block_runtime_never_resumes_old_flat_checkpoint(self):
        base = {"profile": {"profile_version": "old-repair"}, "resume": {"old": True}, "repair_source_binding": {}, "repair_checkpoint_inventory": {}, "working_directory": "unchanged"}
        design = {**self.design, "physical_design": self.plan}
        config = effective_configuration(base, design, ROOT)
        self.assertNotIn("resume", config); self.assertNotIn("repair_source_binding", config)
        self.assertEqual(config["profile"]["config"]["SYNTH_HIERARCHY_MODE"], "keep")
        self.assertIs(config["profile"]["config"]["SYNTH_AUTONAME"], True)
        self.assertIs(config["profile"]["config"]["PL_RESIZER_SETUP_BUFFER_REMOVAL"], False)
        self.assertIs(config["profile"]["config"]["PL_RESIZER_SETUP_GATE_CLONING"], False)
        self.assertEqual(config["block_plan_sha256"], object_hash(self.plan))
        mixed = effective_configuration(base, {**self.design, "physical_design": {"version": "mixed-v1"}}, ROOT)
        self.assertNotIn("resume", mixed); self.assertNotIn("block_plan", mixed)
        self.assertEqual(mixed["profile"]["profile_version"], "hullcirq-sky130-layout-v1")
        self.assertNotIn("PL_RESIZER_SETUP_BUFFER_REMOVAL", mixed["profile"]["config"])
        self.assertNotIn("PL_RESIZER_SETUP_GATE_CLONING", mixed["profile"]["config"])
        self.assertEqual(effective_configuration(base, self.design, ROOT), base)
        self.assertIn("resume", base)

    def test_configuration_projects_core_files_fixed_flow_and_original_clock(self):
        fixture = PhysicalToolTests(); fixture.setUp()
        design = {**self.design, "physical_design": self.plan}
        config = effective_configuration(fixture.config, design, ROOT)
        config['pdk_root']=str(ROOT/'.work/software-fixture/pdks')
        manifest = {"nodes": [{"node_id": "npu2-pe", "module_name": "pe"}]}
        projected = configuration_projection(fixture.settings, config, manifest)
        self.assertEqual(projected["CORE_AREA"], self.plan["core_um"])
        self.assertEqual(projected["DIE_AREA"], [0, 0, 120, 120])
        self.assertEqual(projected["CLOCK_PERIOD"], 50)
        command = fixed_commands(config, Path(config["working_directory"]) / "hullcirq-layout-test")[1]
        self.assertIn("HuLLCirqBlockRegionsV1", command)
        self.assertFalse("--with-initial-state" in command)
        self.assertEqual(source_input(config, manifest, "top")["plan_sha256"], object_hash(self.plan))

    def test_conditional_required_artifacts_do_not_change_legacy_recipe(self):
        legacy = {"source_bundle": [{"file": "candidate_top.v"}, {"file": "npu2-pe.v"}]}
        block = {**legacy, "placement_mode": VERSION}
        self.assertFalse(BLOCK_ARTIFACTS & _file_ids(legacy))
        self.assertTrue(BLOCK_ARTIFACTS <= _required_files(block))

    def test_frozen_runtime_and_launcher_hashes_and_syntax(self):
        launcher = ROOT / "scripts/block_region_flow_v1.py"
        runtime = ROOT / "src/hullcirq/block_layout.py"
        self.assertEqual(hashlib.sha256(launcher.read_bytes()).hexdigest(), BLOCK_FLOW_SHA)
        self.assertEqual(hashlib.sha256(runtime.read_bytes()).hexdigest(), BLOCK_RUNTIME_SHA)
        ast.parse(launcher.read_text(encoding="utf-8")); ast.parse(runtime.read_text(encoding="utf-8"))


class BlockLayoutSourceTests(unittest.TestCase):
    def setUp(self):
        self.fixture = PhysicalWorkflowTests(methodName="runTest")
        self.fixture.setUp(); self.addCleanup(self.fixture.doCleanups)
        self.manager, self.store = self.fixture.manager, self.fixture.store

    def physical_design(self):
        design = self.store.envelope()["design"]
        targets = expanded_targets(design)
        design["physical_design"] = {"version": VERSION, "core_um": [10, 10, 1010, 1010], "regions": [
            {"id": "region_" + str(i), "targets": [target], "rect_um": [10 + i * 100, 10, 100 + i * 100, 1010]} for i, target in enumerate(targets)]}
        return design

    def save(self, design):
        self.store.save(design, self.store.envelope()["revision"]["id"])

    def test_current_physical_plan_changes_only_s11_key_not_frozen_logical_source(self):
        before_key, before, error = self.manager._source_state(); self.assertIsNone(error)
        self.save(self.physical_design())
        after_key, after, error = self.manager._source_state(); self.assertIsNone(error)
        self.assertNotEqual(before_key, after_key)
        self.assertEqual(before["job"]["id"], after["job"]["id"])
        self.assertEqual(before["manifest"], after["manifest"])
        self.assertNotIn("physical_design", after["manifest"]["design"])
        self.assertEqual(after["configuration"]["block_plan_sha256"], after["identity"]["physical_design_sha256"])
        self.assertNotIn("resume", after["configuration"])
        self.assertEqual(self.manager.envelope()["physical_workflow"]["placement_mode"], "block_regions")

    def test_viewport_save_does_not_change_region_source_key(self):
        self.save(self.physical_design())
        before_key, before, error = self.manager._source_state(); self.assertIsNone(error)
        design = self.store.envelope()["design"]
        design["layout"]["viewport"]["zoom"] += 0.1
        self.save(design)
        after_key, after, error = self.manager._source_state(); self.assertIsNone(error)
        self.assertEqual(before_key, after_key)
        self.assertNotEqual(before["physical_design_revision_id"], after["physical_design_revision_id"])

    def test_saved_physical_plan_provenance_requires_the_same_logical_circuit(self):
        self.save(self.physical_design())
        f = self.fixture
        self.manager.start("layout", f.base.job["id"], f.synthesis["id"], f.simulation["id"], self.store.envelope()["revision"]["id"])
        self.manager._worker.join(20)
        run = self.manager._state["runs"][-1]
        self.assertEqual(run["validation_status"], "Passed")
        original = self.manager.path.read_bytes()
        design = self.store.envelope()["design"]
        design["nodes"][0]["behavior"] += " Different logical source for software tamper test."
        self.save(design)
        bad = json.loads(original)
        bad["runs"][-1]["physical_design_revision_id"] = self.store.envelope()["revision"]["id"]
        bad["runs"][-1]["record_hash"] = object_hash({k: v for k, v in bad["runs"][-1].items() if k != "record_hash"})
        self.manager.path.write_text(json.dumps(bad), encoding="utf-8")
        try:
            with self.assertRaises(DomainError): self.fixture.new_manager()
        finally:
            self.manager.path.write_bytes(original)


if __name__ == "__main__": unittest.main()
