"""Generic saved-S11 annotation fixtures, not real circuit/EDA evidence."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tests")]
from hullcirq import layout_map_source as source
from hullcirq.layout_roles import GENERIC_ROLE_PROFILE, collect_layout_roles, generic_role_context
from hullcirq.verification import content_hash, object_hash
import test_layout_map_source as source_tests


class GenericSavedMapTests(unittest.TestCase):
    def setUp(self):
        self.fixture = source_tests.LayoutMapSourceTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        f = self.fixture
        names = [("bias_stage", "AmberAdder", "offset.v")] + [("lane_" + letter, "QuartzTile", "tile.v") for letter in "abcd"]
        rtl = {"candidate_top.v": "module RiverTop(input a);\n" + "\n".join(
            module + " " + name + "(.A(a));" for name, module, _ in names) + "\nendmodule\n",
            "offset.v": "module AmberAdder(input A); endmodule\n",
            "tile.v": "module QuartzTile(input A); endmodule\n"}
        design = {"nodes": [{"id": "offset", "module_name": "AmberAdder", "name": "Offset adjuster"},
                             {"id": "tile", "module_name": "QuartzTile", "name": "Repeated arithmetic", "instance_array": {"rows": 2, "columns": 2}}]}
        manifest = {"design": design, "nodes": [{"node_id": n["id"], "module_name": n["module_name"],
                    "rtl": rtl[n["id"] + ".v"], "rtl_sha256": content_hash(rtl[n["id"] + ".v"])} for n in design["nodes"]]}
        artifacts = [{"id": "rtl-top" if filename == "candidate_top.v" else "rtl-" + filename[:-2],
                      **f._put(filename, text.encode())} for filename, text in rtl.items()]
        wires = [name + ".q" for name, _, _ in names]
        structural = ("module RiverTop(a); input a;\n" + "\n".join("wire \\" + name + " ;" for name in wires) + "\n" +
                      "\n".join("sky130_fd_sc_hd__buf_1 c" + str(i) + " (.A(a),.X(\\" + name + ".q ));" for i, (name, _, _) in enumerate(names)) + "\nendmodule\n").encode()
        module = {"cells": {"j" + str(i): {"type": "sky130_fd_sc_hd__buf_1", "connections": {"A": [2], "X": [i + 3]},
                    "port_directions": {"A": "input", "X": "output"},
                    "attributes": {"src": "C:/private/build/" + filename + ":2.1-3.2"}}
                    for i, (_, _, filename) in enumerate(names)},
                  "netnames": {"a": {"hide_name": 0, "bits": [2]}, **{name: {"hide_name": 0, "bits": [i + 3]} for i, name in enumerate(wires)}}}
        synthesis = f._bytes({"modules": {"RiverTop": module}})
        final_def = ("COMPONENTS 5 ;\n" + "\n".join("- c" + str(i) + " sky130_fd_sc_hd__buf_1 + PLACED ( 0 0 ) N ;" for i in range(5)) + "\nEND COMPONENTS\n").encode()
        artifacts += [{"id": identifier, **f._put(path, raw)} for identifier, path, raw in (
            ("gds", "final.gds", b"fixture-not-circuit-evidence"), ("def", "final.def", final_def), ("netlist", "final.nl.v", structural))]
        relative = "runs/physical/06-yosys-synthesis/RiverTop.nl.v.json"
        f.run.update(global_rtl=rtl["candidate_top.v"], global_rtl_sha256=content_hash(rtl["candidate_top.v"]),
                     source_manifest=manifest, source_manifest_sha256=object_hash(manifest))
        bundle = [{"file": filename, "module_name": "RiverTop" if filename == "candidate_top.v" else "AmberAdder" if filename == "offset.v" else "QuartzTile",
                   "sha256": content_hash(text)} for filename, text in rtl.items()]
        f.run["checks"].update(source_bundle=bundle, artifacts=artifacts, retained_files=[f._put(relative, synthesis), f._put(relative[:-5], structural)])
        for artifact in artifacts:
            artifact["content_type"] = "application/octet-stream"
        f._hash()

    def capture(self):
        f = self.fixture
        return source.capture_source(f.root, f.run, f.output)

    def test_arbitrary_module_and_node_names_do_not_use_s08_finite_gate(self):
        f = self.fixture
        self.assertTrue(source.eligibility(f.run)["supported"])
        before = f._work_snapshot()
        profile = self.capture()
        self.assertEqual(profile["role_profile"], GENERIC_ROLE_PROFILE)
        self.assertEqual(before, f._work_snapshot())
        result = collect_layout_roles(f.root, profile)
        self.assertEqual(result["top_module"], "RiverTop")
        self.assertEqual(len(result["provenance"]["source_rtl"]), 3)
        self.assertEqual(len(result["role_context"]["definitions"]), 2)
        self.assertEqual(len(result["role_context"]["instances"]), 5)
        self.assertEqual(result["summary"]["final_cells"], 5)

    def test_shared_definition_instances_are_distinct_but_not_source_confirmed_lanes(self):
        f = self.fixture
        result = collect_layout_roles(f.root, self.capture())
        cells = {cell["id"]: cell for cell in result["cells"]}
        self.assertEqual((cells["c0"]["role"], cells["c0"]["status"]), ("instance:bias_stage", "source_confirmed"))
        for i, letter in enumerate("abcd", 1):
            self.assertEqual((cells["c" + str(i)]["role"], cells["c" + str(i)]["status"]),
                             ("instance:lane_" + letter, "source_and_connectivity"))
        repeated = [role for role in result["roles"] if role.get("group") == "pe"]
        self.assertEqual(len(repeated), 4)
        self.assertNotIn("C:/private", json.dumps(result))

    def test_missing_mapping_is_all_unknown_not_an_npu_or_execution_gate(self):
        f = self.fixture
        f.run["checks"]["retained_files"] = []
        f._hash()
        profile = self.capture()
        result = collect_layout_roles(f.root, profile)
        self.assertEqual(profile["expected_synthesis_cells"], 0)
        self.assertEqual(result["summary"]["by_role"], {"unknown": 5})
        self.assertEqual(result["summary"]["by_status"], {"unknown": 5})

    def test_hierarchical_mapping_is_retained_without_invented_flat_attribution(self):
        f = self.fixture
        entry = f.run["checks"]["retained_files"][0]
        document = json.loads((f.artifacts / entry["relative_path"]).read_bytes())
        document["modules"]["AnotherSavedModule"] = {"cells": {}, "attributes": {}}
        entry.update(f._put(entry["relative_path"], f._bytes(document)))
        f._hash()
        result = collect_layout_roles(f.root, self.capture())
        self.assertEqual(result["summary"]["by_role"], {"unknown": 5})
        self.assertTrue((f.output / "artifacts/synthesis.json").is_file())

    def test_missing_final_input_and_changed_graph_module_fail_closed(self):
        f = self.fixture
        f.run["source_manifest"]["design"]["nodes"][0]["module_name"] = "Different"
        f.run["source_manifest_sha256"] = object_hash(f.run["source_manifest"])
        f._hash()
        self.assertFalse(source.eligibility(f.run)["supported"])
        self.assertFalse(f.output.exists())

    def test_unknown_source_attribute_does_not_invent_instance_ownership(self):
        f = self.fixture
        e = f.run["checks"]["retained_files"][0]
        document = json.loads((f.artifacts / e["relative_path"]).read_bytes())
        for cell in document["modules"]["RiverTop"]["cells"].values():
            cell["attributes"] = {"src": "unrecognized.v:1"}
        e.update(f._put(e["relative_path"], f._bytes(document)))
        f._hash()
        result = collect_layout_roles(f.root, self.capture())
        self.assertTrue(all(c["status"] == "connectivity_inferred" for c in result["cells"]))

    def test_generate_syntax_never_confirms_a_lexical_instance_as_elaborated(self):
        f = self.fixture
        context = generic_role_context("RiverTop", f.run["checks"]["source_bundle"], f.run["source_manifest"],
                                       f.run["global_rtl"] + "\ngenerate for (i=0;i<4;i=i+1) begin end endgenerate")
        self.assertTrue(context["instances"])
        self.assertTrue(all(not item["direct_source_scope"] for item in context["instances"]))

    def test_generic_context_is_manifest_bound_and_cannot_be_relabelled(self):
        f = self.fixture
        profile = self.capture()
        profile["role_context"]["instances"][0]["label"] = "Forged ownership"
        with self.assertRaisesRegex(ValueError, "context differs"):
            collect_layout_roles(f.root, profile)

    def test_valid_saved_revalidation_retains_exact_no_new_tool_provenance(self):
        f = self.fixture
        f.run.update(evidence_kind="trusted_saved_tool_revalidation", execution_kind="saved_outputs_no_new_tool_start", prior_run_id="physical-workflow-" + "a" * 32)
        f.run["checks"].update(execution_reused=True, revalidated_from_run_id=f.run["prior_run_id"], revalidation_tool_starts=0, revalidation_model_calls=0)
        f._hash()
        self.assertTrue(source.eligibility(f.run)["supported"])
        self.capture()
        self.assertEqual(json.loads((f.output / "layout_record.json").read_bytes()), f.run)


if __name__ == "__main__":
    unittest.main()
