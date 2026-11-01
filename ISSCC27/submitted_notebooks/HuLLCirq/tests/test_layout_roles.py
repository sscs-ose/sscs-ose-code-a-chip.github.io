"""Read-only layout annotation QA; small graphs are software fixtures only."""
from __future__ import annotations
import copy
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from hullcirq import layout_roles as roles


def module(cells, nets):
    return {"cells": cells, "netnames": {name: {"hide_name": 0, "bits": [bit]} for name, bit in nets.items()}}


def cell(master, pins, directions, source=None):
    return {"type": master, "connections": {pin: [bit] for pin, bit in pins.items()},
            "port_directions": directions, "attributes": {"src": source} if source else {}}


def verilog(cells, nets):
    def expr(net):
        return net if net.replace("_", "").isalnum() and not net[0].isdigit() else "\\" + net + " "
    declarations = "\n".join("wire " + expr(net) + ";" for net in nets)
    instances = "\n".join(master + " " + name + " (" + ",".join("." + pin + "(" + expr(net) + ")" for pin, net in pins.items()) + ");"
                           for name, (master, pins) in cells.items())
    return roles.parse_structural_verilog("module fixture();\n" + declarations + "\n" + instances + "\nendmodule")


class StructuralParsingTests(unittest.TestCase):
    def test_alias_bus_and_escaped_literal_are_normalized_without_losing_identity(self):
        parsed = roles.parse_structural_verilog("""/* harmless writer header */ module fixture(a,z);
input [3:0] a; output z; wire n; wire \\u_control.value[3] ;
assign n = a[2];
sky130_fd_sc_hd__buf_1 renamed (.A(n),.X(\\u_control.value[3] ));
sky130_fd_sc_hd__buf_1 out (.A(\\u_control.value[3] ),.X(z));
endmodule""")
        self.assertEqual(parsed["cells"]["renamed"]["pins"], {"A": "a[2]", "X": "u_control.value[3]"})
        self.assertIn("a[3]", parsed["declarations"])
        self.assertEqual(parsed["aliases"]["n"], "a[2]")

    def test_unsupported_expression_duplicate_and_truncation_fail_closed(self):
        invalid = ["module fixture(); wire n; assign n = a & b; buf u(.A(n)); endmodule",
                   "module fixture(); buf u(.A(a)); buf u(.A(b)); endmodule",
                   "module fixture(); buf u(.A(a)) endmodule",
                   "module fixture(); assign 1'b0 = 1'b1; buf u(.A(a)); endmodule"]
        for text in invalid:
            with self.subTest(text=text), self.assertRaises(roles.LayoutRoleError):
                roles.parse_structural_verilog(text)

    def test_def_count_duplicates_and_master_inventory_are_checked(self):
        self.assertEqual(roles.parse_def_components("COMPONENTS 1 ; - actual buf + PLACED ( 0 0 ) N ; END COMPONENTS"), {"actual": "buf"})
        for text in ("COMPONENTS 2 ; - a buf ; END COMPONENTS", "COMPONENTS 2 ; - a buf ; - a inv ; END COMPONENTS"):
            with self.assertRaises(roles.LayoutRoleError):
                roles.parse_def_components(text)


class ConnectivityBridgeTests(unittest.TestCase):
    def test_renamed_shuffled_cells_and_anonymous_wires_use_connectivity_not_indices(self):
        m = module({"json-z": cell("inv_1", {"A": 11, "Y": 12}, {"A": "input", "Y": "output"}),
                    "json-a": cell("buf_1", {"A": 12, "X": 13}, {"A": "input", "X": "output"})}, {"input": 11, "u_control.q": 13})
        v = verilog({"random_42": ("buf_1", {"A": "anonymous", "X": "u_control.q"}),
                     "random_3": ("inv_1", {"A": "input", "Y": "anonymous"})}, ["input", "anonymous", "u_control.q"])
        mapping, report = roles.bridge_synthesis(m, v)
        self.assertEqual(mapping, {"random_3": "json-z", "random_42": "json-a"})
        self.assertEqual(report["cells_checked"], 2)
        self.assertEqual(report["ambiguous_cells"], 0)

    def test_identical_signatures_never_transfer_source_attributes_arbitrarily(self):
        m = module({name: cell("buf_1", {"A": 1, "X": 2}, {"A": "input", "X": "output"}, "/src/node-control.v:1.1-2.1")
                    for name in ("j1", "j2")}, {"a": 1, "z": 2})
        v = verilog({name: ("buf_1", {"A": "a", "X": "z"}) for name in ("v1", "v2")}, ["a", "z"])
        mapping, report = roles.bridge_synthesis(m, v)
        self.assertEqual(mapping, {})
        self.assertEqual(report["ambiguous_cells"], 2)
        cells, _ = roles.annotate_cells(m, v, v, {"v1": "buf_1", "v2": "buf_1"})
        self.assertTrue(all(c["status"] == "unknown" for c in cells))
        self.assertTrue(all(not any(e["kind"] == "unique_synthesis_src_attribute" for e in c["evidence"]) for c in cells))

    def test_pin_mismatch_and_unresolved_disconnected_symmetry_are_rejected(self):
        m = module({"j": cell("buf_1", {"A": 1, "X": 2}, {"A": "input", "X": "output"})}, {"a": 1, "z": 2})
        bad = verilog({"v": ("buf_1", {"A": "a", "X": "a"})}, ["a", "z"])
        with self.assertRaises(roles.LayoutRoleError):
            roles.bridge_synthesis(m, bad)
        disconnected = module({"j1": cell("buf_1", {"A": 1, "X": 2}, {}), "j2": cell("buf_1", {"A": 3, "X": 4}, {})}, {})
        unanchored = verilog({"v1": ("buf_1", {"A": "n1", "X": "n2"}), "v2": ("buf_1", {"A": "n3", "X": "n4"})}, ["n1", "n2", "n3", "n4"])
        with self.assertRaises(roles.LayoutRoleError):
            roles.bridge_synthesis(disconnected, unanchored)


class FunctionalAnnotationTests(unittest.TestCase):
    def test_versioned_changed_family_is_unknown_and_stops_fanin_inference(self):
        m = module({
            'j0': cell('buf_1', {'A': 1, 'X': 2}, {'A': 'input', 'X': 'output'}),
            'j1': cell('inv_2', {'A': 2, 'Y': 3}, {'A': 'input', 'Y': 'output'}, '/src/npu2-control.v:1'),
            'j2': cell('buf_1', {'A': 3, 'X': 4}, {'A': 'input', 'X': 'output'}, '/src/npu2-control.v:2'),
        }, {'a': 1, 'n': 2, 'control.mid': 3, 'control.q': 4})
        v = verilog({'upstream': ('buf_1', {'A': 'a', 'X': 'n'}),
                     'clkbuf_changed': ('inv_2', {'A': 'n', 'Y': 'control.mid'}),
                     'anchor': ('buf_1', {'A': 'control.mid', 'X': 'control.q'})}, list(m['netnames']))
        f = copy.deepcopy(v)
        f['cells']['clkbuf_changed']['master'] = 'clkinv_4'
        f['cells']['anchor']['master'] = 'buf_2'
        components = {name: c['master'] for name, c in f['cells'].items()}
        with self.assertRaisesRegex(roles.LayoutRoleError, 'logical master'):
            roles.annotate_cells(m, v, f, components, roles._NPU2_ROLE_PROFILE)
        cells, summary = roles.annotate_cells(m, v, f, components, roles._NPU2_ROLE_PROFILE,
                                             'changed_family_unknown_v1')
        by_id = {c['id']: c for c in cells}
        for name in ('clkbuf_changed', 'upstream'):
            self.assertEqual((by_id[name]['role'], by_id[name]['status']), ('unknown', 'unknown'))
        self.assertEqual(by_id['anchor']['status'], 'source_confirmed')
        changed = by_id['clkbuf_changed']['evidence']
        self.assertFalse(any(e['kind'] in ('retained_synthesis_instance', 'unique_synthesis_src_attribute',
                                          'role_named_output_net', 'bounded_combinational_fanin_cone',
                                          'CTS_instance_prefix') for e in changed))
        self.assertTrue(any(e['kind'] == 'changed_logical_family_attribution_withheld' and
                            e['attribution_withheld'] for e in changed))
        self.assertEqual([c['id'] for c in summary['resized_cells']], ['anchor'])
        self.assertEqual([c['id'] for c in summary['unattributed_family_changes']], ['clkbuf_changed'])
        bad = copy.deepcopy(f)
        bad['cells']['clkbuf_changed']['pins']['BAD'] = 'a'
        with self.assertRaisesRegex(roles.LayoutRoleError, 'pin interface'):
            roles.annotate_cells(m, v, bad, components, roles._NPU2_ROLE_PROFILE, 'changed_family_unknown_v1')
        with self.assertRaisesRegex(roles.LayoutRoleError, 'annotation policy'):
            roles.annotate_cells(m, v, f, components, roles._NPU2_ROLE_PROFILE, 'unregistered')

    def test_npu2_role_profile_has_exact_explicit_nodes_and_no_legacy_lanes(self):
        legacy_ids = [item["id"] for item in roles.role_definitions()]
        self.assertEqual(legacy_ids, ["control", "buffer", "scheduler", "post", "fifo"] +
                         [f"pe:{index}" for index in range(16)] +
                         ["integration", "clock", "physical", "unknown", "shared"])
        definitions = roles.role_definitions(roles._NPU2_ROLE_PROFILE)
        identifiers = [item["id"] for item in definitions]
        self.assertEqual(identifiers[:11], list(roles._NPU2_ROLES))
        self.assertFalse(any(identifier.startswith("pe:") for identifier in identifiers))
        pe10 = next(item for item in definitions if item["id"] == "pe10")
        self.assertEqual(pe10["label"], "PE 10 (row 1, column 0)")
        self.assertEqual(pe10["group"], "pe")
        self.assertIn("row 1, column 0", pe10["description"])
        self.assertTrue(all(item.get("group") != "pe" for item in definitions if item["id"] not in {"pe00", "pe01", "pe10", "pe11"}))
        with self.assertRaisesRegex(roles.LayoutRoleError, "Unsupported layout role profile"):
            roles.role_definitions("unregistered")

    def test_npu2_source_and_net_rules_are_exact_and_fail_closed(self):
        profile = roles._NPU2_ROLE_PROFILE
        self.assertEqual(roles._source_role("/saved/npu2-dispatcher.v:1.1-2.1", profile), "dispatcher")
        self.assertEqual(roles._source_role(r"C:\\saved\\npu2-pe10.v:1.1-2.1", profile), "pe10")
        self.assertEqual(roles._source_role("/saved/candidate_top.v:1.1-2.1", profile), "integration")
        self.assertEqual(roles._source_role("/a/npu2-pe00.v:1|/a/npu2-pe00.v:2", profile), "pe00")
        self.assertIsNone(roles._source_role("/a/npu2-pe00.v:1|/a/npu2-pe01.v:2", profile))
        self.assertIsNone(roles._source_role("/a/npu2-pe0.v:1", profile))
        self.assertEqual(roles._role("buffer.read_index[2]", profile), "scheduler")
        self.assertEqual(roles._role("batch_data[31]", profile), "scheduler")
        for identifier in roles._NPU2_ROLES:
            self.assertEqual(roles._role(identifier + ".state", profile), identifier)
        self.assertIsNone(roles._role("buffer.read_index[x]", profile))
        self.assertIsNone(roles._role("batch_data_valid", profile))
        self.assertIsNone(roles._role("pe12.state", profile))

    def test_npu2_scheduler_receiver_alias_is_allowed_but_other_conflicts_fail(self):
        profile = roles._NPU2_ROLE_PROFILE
        m = module({"j": cell("dfxtp_1", {"D": 1, "Q": 2}, {"D": "input", "Q": "output"},
                                   "/src/npu2-scheduler.v:1.1-2.1")},
                   {"a": 1, "buffer.read_index[0]": 2})
        v = verilog({"v": ("dfxtp_1", {"D": "a", "Q": "buffer.read_index[0]"})},
                    ["a", "buffer.read_index[0]"])
        cells, _ = roles.annotate_cells(m, v, v, {"v": "dfxtp_1"}, profile)
        self.assertEqual((cells[0]["role"], cells[0]["status"]), ("scheduler", "source_confirmed"))
        m_net = module({"j": cell("dfxtp_1", {"D": 1, "Q": 2}, {"D": "input", "Q": "output"})},
                       {"a": 1, "buffer.read_index[0]": 2})
        net_cells, _ = roles.annotate_cells(m_net, v, v, {"v": "dfxtp_1"}, profile)
        self.assertIn({"kind": "role_named_output_net", "nets": ["buffer.read_index[0]"]},
                      net_cells[0]["evidence"])
        bad_m = module({"j": cell("dfxtp_1", {"D": 1, "Q": 2}, {"D": "input", "Q": "output"},
                                       "/src/npu2-scheduler.v:1.1-2.1")},
                       {"a": 1, "buffer.other": 2})
        bad = verilog({"v": ("dfxtp_1", {"D": "a", "Q": "buffer.other"})}, ["a", "buffer.other"])
        with self.assertRaisesRegex(roles.LayoutRoleError, "Source-role"):
            roles.annotate_cells(bad_m, bad, bad, {"v": "dfxtp_1"}, profile)

    def test_source_roles_pe_lane_inference_shared_cones_and_physical_unknown_are_distinct(self):
        m = module({
            "j0": cell("sky130_fd_sc_hd__buf_1", {"A": 1, "X": 2}, {"A": "input", "X": "output"}),
            "j1": cell("sky130_fd_sc_hd__dfxtp_1", {"CLK": 3, "D": 2, "Q": 4}, {"CLK": "input", "D": "input", "Q": "output"}, "/src/node-control.v:1.1-2.1"),
            "j2": cell("sky130_fd_sc_hd__dfxtp_1", {"CLK": 3, "D": 2, "Q": 5}, {"CLK": "input", "D": "input", "Q": "output"}, "/src/node-pe.v:1.1-2.1"),
            "j3": cell("sky130_fd_sc_hd__dfxtp_1", {"CLK": 3, "D": 1, "Q": 6}, {"CLK": "input", "D": "input", "Q": "output"}),
        }, {"a": 1, "n": 2, "clk": 3, "u_control.q": 4, "pe_inst[3].u_pe.acc_data[0]": 5, "u_buffer.memory[0]": 6})
        vc = {"combine": ("sky130_fd_sc_hd__buf_1", {"A": "a", "X": "n"}),
              "ctrl": ("sky130_fd_sc_hd__dfxtp_1", {"CLK": "clk", "D": "n", "Q": "u_control.q"}),
              "lane": ("sky130_fd_sc_hd__dfxtp_1", {"CLK": "clk", "D": "n", "Q": "pe_inst[3].u_pe.acc_data[0]"}),
              "mem": ("sky130_fd_sc_hd__dfxtp_1", {"CLK": "clk", "D": "a", "Q": "u_buffer.memory[0]"})}
        v = verilog(vc, list(m["netnames"]))
        f = copy.deepcopy(v)
        f["cells"]["combine"]["master"] = "sky130_fd_sc_hd__buf_2"
        f["cells"].update({"fill1": {"master": "sky130_fd_sc_hd__fill_1", "pins": {}},
                           "clkbuf_1": {"master": "sky130_fd_sc_hd__clkbuf_1", "pins": {"A": "clk", "X": "clock1"}},
                           "ordinary_buffer": {"master": "sky130_fd_sc_hd__clkbuf_1", "pins": {"A": "a", "X": "other"}}})
        cells, report = roles.annotate_cells(m, v, f, {name: c["master"] for name, c in f["cells"].items()})
        by_id = {c["id"]: c for c in cells}
        self.assertEqual((by_id["ctrl"]["role"], by_id["ctrl"]["status"]), ("control", "source_confirmed"))
        self.assertEqual((by_id["lane"]["role"], by_id["lane"]["status"]), ("pe:3", "source_and_connectivity"))
        self.assertEqual((by_id["mem"]["role"], by_id["mem"]["status"]), ("buffer", "connectivity_inferred"))
        self.assertEqual((by_id["combine"]["role"], by_id["combine"]["status"]), ("shared", "connectivity_inferred"))
        self.assertEqual(by_id["fill1"]["role"], "physical")
        self.assertEqual(by_id["clkbuf_1"]["role"], "clock")
        self.assertEqual(by_id["ordinary_buffer"]["role"], "unknown")
        self.assertEqual(len(report["resized_cells"]), 1)
        with self.assertRaises(roles.LayoutRoleError):
            roles.annotate_cells(m, v, f, {name: "wrong" for name in f["cells"]})
        changed = copy.deepcopy(f)
        changed["cells"]["ctrl"]["pins"]["WRONG"] = "a"
        with self.assertRaises(roles.LayoutRoleError):
            roles.annotate_cells(m, v, changed, {name: c["master"] for name, c in changed["cells"].items()})

    def test_source_pe_template_without_lane_or_named_output_remains_unknown(self):
        m = module({"j": cell("dfxtp_1", {"D": 1, "Q": 2}, {"D": "input", "Q": "output"}, "/src/node-pe.v:1.1-2.1")}, {"a": 1, "anonymous_q": 2})
        v = verilog({"v": ("dfxtp_1", {"D": "a", "Q": "anonymous_q"})}, ["a", "anonymous_q"])
        cells, _ = roles.annotate_cells(m, v, v, {"v": "dfxtp_1"})
        self.assertEqual(cells[0]["role"], "unknown")
        self.assertEqual(cells[0]["status"], "unknown")
        self.assertTrue(any(e["kind"] == "unique_synthesis_src_attribute" for e in cells[0]["evidence"]))

    def test_source_role_conflict_is_rejected_and_delay_gates_are_not_sequential(self):
        m = module({"j": cell("sky130_fd_sc_hd__dfxtp_1", {"D": 1, "Q": 2}, {"D": "input", "Q": "output"}, "/src/node-control.v:1.1-2.1")}, {"a": 1, "u_post.q": 2})
        v = verilog({"v": ("sky130_fd_sc_hd__dfxtp_1", {"D": "a", "Q": "u_post.q"})}, ["a", "u_post.q"])
        with self.assertRaisesRegex(roles.LayoutRoleError, "Source-role"):
            roles.annotate_cells(m, v, v, {"v": "sky130_fd_sc_hd__dfxtp_1"})
        self.assertTrue(roles._sequential("sky130_fd_sc_hd__dfxtp_1"))
        self.assertTrue(roles._sequential("sky130_fd_sc_hd__dlxtp_1"))
        self.assertFalse(roles._sequential("sky130_fd_sc_hd__dlygate4sd3_1"))

    def test_input_byte_substitution_is_rejected_even_with_readable_manifest(self):
        import json
        with tempfile.TemporaryDirectory() as temporary:
            archive = Path(temporary) / roles._BASE
            relative = roles._INPUTS["synthesis_json"]
            path = archive / relative
            path.parent.mkdir(parents=True)
            path.write_bytes(b"tampered bytes")
            raw = json.dumps({"validation_status": "Passed", "files": {relative: {"sha256": "0" * 64, "bytes": 14}}}).encode()
            (archive / "manifest.json").write_bytes(raw)
            with patch.object(roles, "_ARCHIVE_MANIFEST_SHA256", hashlib.sha256(raw).hexdigest()), \
                    self.assertRaisesRegex(roles.LayoutRoleError, "input hash/size"):
                roles.collect_layout_roles(Path(temporary))

    def test_manifest_substitution_fails_before_any_annotation(self):
        with tempfile.TemporaryDirectory() as temporary:
            archive = Path(temporary) / roles._BASE
            archive.mkdir(parents=True)
            (archive / "manifest.json").write_text('{"validation_status":"Passed"}', encoding="utf-8")
            with self.assertRaisesRegex(roles.LayoutRoleError, "manifest identity"):
                roles.collect_layout_roles(Path(temporary))

    def test_explicit_source_profile_is_complete_and_path_bounded(self):
        profile = roles.source_profile_values()
        self.assertEqual(roles.source_profile_values(profile), profile)
        npu2 = {**profile, 'role_profile': roles._NPU2_ROLE_PROFILE}
        self.assertEqual(roles.source_profile_values(npu2), npu2)
        explicit = {**npu2, 'annotation_policy': 'changed_family_unknown_v1'}
        self.assertEqual(roles.source_profile_values(explicit), explicit)
        for changed in ({**profile, 'source_root': '../outside'},
                        {**profile, 'expected_final_cells': 0},
                        {**profile, 'source_manifest_sha256': 'unverified'},
                        {key: value for key, value in profile.items() if key != 'inputs'},
                        {**profile, 'role_profile': 'unregistered'},
                        {**npu2, 'annotation_policy': 'unregistered'},
                        {**profile, 'annotation_policy': 'changed_family_unknown_v1'}):
            with self.assertRaises(roles.LayoutRoleError):
                roles.source_profile_values(changed)

    def test_explicit_profile_cannot_relabel_original_archive_as_new_run(self):
        profile = {**roles.source_profile_values(), 'layout_run_id': 'physical-workflow-' + '0' * 32}
        with self.assertRaisesRegex(roles.LayoutRoleError, 'layout disagree'):
            roles.collect_layout_roles(ROOT, profile)

    def test_actual_retained_graph_has_exact_binding_and_no_source_overclaim(self):
        paths = [ROOT / roles._BASE / relative for relative in roles._INPUTS.values()]
        before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
        result = roles.collect_layout_roles(ROOT)
        self.assertEqual(len(result["cells"]), 66315)
        self.assertEqual(result["summary"]["bridge"]["uniquely_bridged_cells"], 9369)
        self.assertEqual(result["summary"]["bridge"]["ambiguous_cells"], 0)
        self.assertEqual(len(result["summary"]["resized_cells"]), 19)
        self.assertEqual(result["summary"]["by_status"]["source_confirmed"], 348)
        self.assertEqual(result["summary"]["by_status"]["source_and_connectivity"], 528)
        self.assertTrue(all(result["summary"]["by_role"].get(f"pe:{i}", 0) > 0 for i in range(16)))
        self.assertGreater(result["summary"]["by_role"]["unknown"], 0)
        self.assertGreater(result["summary"]["by_role"]["shared"], 0)
        self.assertEqual({p: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}, before)


if __name__ == "__main__":
    unittest.main()
