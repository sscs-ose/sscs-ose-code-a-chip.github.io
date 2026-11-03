"""Pure external-boundary contracts and temporary-store preservation fixtures.

These tests execute no model, circuit compiler, simulator or physical tool.
"""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hullcirq import external_io
from hullcirq.domain import DomainError, fingerprint, revision_hashes, validate_shape, validate_stage
from hullcirq.store import ProjectStore
from hullcirq.workspace import blank_design


def design_fixture():
    design = blank_design("project-io-software", "Software boundary fixture", "system-io-software", "Software fixture", "boundary_top")
    def port(identity, name, direction):
        return {"id": identity, "name": name, "direction": direction, "width": 4, "signed": False,
                "protocol": "valid_ready", "clock": "clk", "reset": "rst"}
    design["nodes"] = [{"id": "counter", "name": "Counter", "module_name": "counter_module", "parent_id": None,
                         "behavior": "Software contract fixture only.", "test_expectations": "Independent software fixture.",
                         "constraints": {"latency_cycles": 1, "protocol": "valid_ready"},
                         "ports": [port("node-in", "incoming", "input"), port("node-out", "outgoing", "output")]}]
    design["external_io"] = {"version": 1, "ports": [
        {"id": "top-in", "name": "commands", "direction": "input", "width": 4, "signed": False, "protocol": "valid_ready"},
        {"id": "top-out", "name": "results", "direction": "output", "width": 4, "signed": False, "protocol": "valid_ready"}],
        "connections": [
            {"id": "bind-in", "external_port_id": "top-in", "node_id": "counter", "port_id": "node-in"},
            {"id": "bind-out", "external_port_id": "top-out", "node_id": "counter", "port_id": "node-out"}]}
    return design


class ExternalIoTests(unittest.TestCase):
    def test_new_workspace_default_is_two_implicit_groups_not_circuit_nodes(self):
        first = blank_design("p", "New", "s", "Main", "top")
        second = blank_design("p2", "New", "s2", "Main", "top2")
        self.assertEqual(first["external_io"], {"version": 1, "ports": [], "connections": []})
        self.assertEqual(first["nodes"], [])
        self.assertEqual(first["edges"], [])
        first["external_io"]["ports"].append({})
        self.assertEqual(second["external_io"]["ports"], [])

    def test_legacy_hashes_and_unconnected_meaning_are_unchanged(self):
        design = json.loads((ROOT / "examples/m1_two_nodes.json").read_text(encoding="utf-8"))
        before = copy.deepcopy(design)
        self.assertEqual(fingerprint(design, "graph_editor"), "e5a29c632c2fa2ae0c2f5357f8543199776f8f4afae4a54e84ade4bd19b94823")
        self.assertEqual(revision_hashes(design), {
            "semantic_hash": "20ffe8d773956e7f5553b01012117bbf3198cf11624e482ddb15504d47b0c482",
            "layout_hash": "7030165f6400df43b0ac2293d8e1631295918022716063375368ef31d5fee605"})
        self.assertEqual(external_io.bindings(design), [])
        validate_stage(design, "graph_editor")
        self.assertEqual(design, before)
        self.assertNotIn("external_io", design)

    def test_explicit_boundaries_cover_only_the_two_real_node_ports(self):
        design = design_fixture()
        before = copy.deepcopy(design)
        validate_shape(design)
        self.assertEqual(external_io.findings(design), [])
        self.assertEqual(external_io.covered_endpoints(design), {("counter", "node-in", ()), ("counter", "node-out", ())})
        self.assertFalse([d for d in validate_stage(design, "graph_editor") if d["severity"] in ("warning", "error")])
        self.assertEqual(design, before)

    def test_stream_expansion_preserves_reverse_ready_and_distinct_top_names(self):
        records = external_io.bindings(design_fixture())
        self.assertEqual([(r["external_name"], r["node_pin"], r["direction"], r["width"]) for r in records], [
            ("commands", "incoming", "input", 4), ("commands_valid", "incoming_valid", "input", 1),
            ("commands_ready", "incoming_ready", "output", 1), ("results", "outgoing", "output", 4),
            ("results_valid", "outgoing_valid", "output", 1), ("results_ready", "outgoing_ready", "input", 1)])
        self.assertEqual(len(external_io.expanded_ports(design_fixture())), 6)
        self.assertNotIn("clk", [p["name"] for p in external_io.expanded_ports(design_fixture())])

    def test_missing_binding_keeps_both_external_and_node_warnings(self):
        design = design_fixture()
        design["external_io"]["connections"].pop()
        codes = [d["code"] for d in validate_stage(design, "graph_editor")]
        self.assertIn("external_unconnected_port", codes)
        self.assertIn("unconnected_port", codes)
        self.assertEqual(len(external_io.expanded_ports(design)), 6)
        with self.assertRaises(DomainError):
            external_io.bindings(design)

    def test_declaring_same_named_top_without_a_binding_does_not_hide_warning(self):
        design = design_fixture()
        design["external_io"]["connections"] = []
        design["external_io"]["ports"][0]["name"] = "incoming"
        self.assertEqual(len([d for d in validate_stage(design, "graph_editor") if d["code"] == "unconnected_port"]), 2)
        self.assertEqual(external_io.covered_endpoints(design), set())

    def test_port_contract_mismatches_are_saveable_but_never_connected(self):
        mutations = [("direction", "output"), ("width", 8), ("signed", True), ("protocol", "raw")]
        for field, wrong in mutations:
            with self.subTest(field=field):
                design = design_fixture()
                design["external_io"]["ports"][0][field] = wrong
                validate_shape(design)
                self.assertIn("external_" + field + "_mismatch", [d["code"] for d in external_io.findings(design)])
                self.assertNotIn(("counter", "node-in", ()), external_io.covered_endpoints(design))
                with self.assertRaises(DomainError):
                    external_io.bindings(design)

    def test_clock_and_reset_domain_mismatch_are_not_qualified(self):
        for field in ("clock", "reset"):
            with self.subTest(field=field):
                design = design_fixture()
                design["nodes"][0]["ports"][0][field] = "other"
                self.assertIn("external_" + field + "_mismatch", [d["code"] for d in external_io.findings(design)])
                self.assertNotIn(("counter", "node-in", ()), external_io.covered_endpoints(design))

    def test_external_name_collisions_include_implicit_ready_and_global_clock(self):
        for name in ("commands_ready", "clk", "rst"):
            with self.subTest(name=name):
                design = design_fixture()
                design["external_io"]["ports"][1].update(name=name, protocol="raw")
                self.assertIn("external_name_collision", [d["code"] for d in external_io.findings(design)])
                with self.assertRaises(DomainError):
                    external_io.expanded_ports(design)

    def test_duplicate_ids_names_and_bindings_fail_closed(self):
        for kind in ("id", "name", "external_binding", "node_binding"):
            with self.subTest(kind=kind):
                design = design_fixture()
                io = design["external_io"]
                if kind == "id":
                    io["ports"][0]["id"] = "counter"
                elif kind == "name":
                    io["ports"][1]["name"] = io["ports"][0]["name"]
                else:
                    extra = copy.deepcopy(io["connections"][0]); extra["id"] = "extra"
                    if kind == "node_binding":
                        extra["external_port_id"] = "top-out"
                    io["connections"].append(extra)
                validate_shape(design)
                self.assertTrue(any(d["severity"] == "error" for d in external_io.findings(design)))
                with self.assertRaises(DomainError):
                    external_io.bindings(design)

    def test_deleted_node_or_port_is_not_a_valid_external_connection(self):
        for key in ("node_id", "port_id", "external_port_id"):
            with self.subTest(key=key):
                design = design_fixture()
                design["external_io"]["connections"][0][key] = "deleted"
                self.assertTrue(any(d["severity"] == "error" for d in external_io.findings(design)))
                self.assertNotIn(("counter", "node-in", ()), external_io.covered_endpoints(design))

    def test_internal_edge_and_boundary_cannot_double_bind_one_logical_port(self):
        design = design_fixture()
        other = copy.deepcopy(design["nodes"][0])
        other.update(id="other", name="Other", module_name="other_module")
        for p in other["ports"]:
            p["id"] = "other-" + p["id"]
        design["nodes"].append(other)
        design["edges"] = [{"id": "internal", "protocol": "valid_ready", "behavior": "Fixture edge.",
                            "source": {"node_id": "other", "port_id": "other-node-out"},
                            "target": {"node_id": "counter", "port_id": "node-in"}}]
        validate_shape(design)
        self.assertIn("external_internal_collision", [d["code"] for d in external_io.findings(design)])
        self.assertNotIn(("counter", "node-in", ()), external_io.covered_endpoints(design))

    def test_array_binding_requires_exact_member_and_keeps_index_in_pin_records(self):
        design = design_fixture()
        design["nodes"][0]["instance_array"] = {"rows": 2, "columns": 2}
        for connection in design["external_io"]["connections"]:
            connection["instance_index"] = [1, 0]
        self.assertEqual(external_io.covered_endpoints(design), {("counter", "node-in", (1, 0)), ("counter", "node-out", (1, 0))})
        self.assertTrue(all(r["instance_index"] == [1, 0] for r in external_io.bindings(design)))
        self.assertEqual(len([d for d in validate_stage(design, "graph_editor") if d["code"] == "unconnected_port"]), 6)
        for wrong in (None, [-1, 0], [2, 0]):
            with self.subTest(index=wrong):
                copied = copy.deepcopy(design)
                if wrong is None:
                    del copied["external_io"]["connections"][0]["instance_index"]
                else:
                    copied["external_io"]["connections"][0]["instance_index"] = wrong
                validate_shape(copied)
                self.assertIn("external_instance_index", [d["code"] for d in external_io.findings(copied)])

    def test_scalar_does_not_accept_an_array_index(self):
        design = design_fixture()
        design["external_io"]["connections"][0]["instance_index"] = [0, 0]
        self.assertIn("external_instance_index", [d["code"] for d in external_io.findings(design)])

    def test_raw_boundary_expands_only_one_signal(self):
        design = design_fixture()
        for p in design["external_io"]["ports"]:
            p["protocol"] = "raw"
        for p in design["nodes"][0]["ports"]:
            p.update(protocol="raw", sideband={"kind": "level", "associated_port_id": None}, width=1)
        for p in design["external_io"]["ports"]:
            p["width"] = 1
        self.assertEqual(len(external_io.bindings(design)), 2)
        self.assertFalse([d for d in validate_stage(design, "graph_editor") if d["severity"] in ("error", "warning")])

    def test_invalid_node_pin_name_or_expanded_collision_never_produces_bindings(self):
        for name in ("bad;pin", "incoming_valid", "clk"):
            with self.subTest(name=name):
                design = design_fixture()
                design["nodes"][0]["ports"][1]["name"] = name
                self.assertTrue(any(d["severity"] == "error" for d in external_io.findings(design)))
                with self.assertRaises(DomainError):
                    external_io.bindings(design)

    def test_malformed_shapes_are_rejected_without_implicit_migration(self):
        for change in (lambda v: v.update(version=True), lambda v: v.update(ports={}),
                       lambda v: v["ports"][0].update(width=True),
                       lambda v: v["connections"][0].update(instance_index=[True, 0]),
                       lambda v: v["connections"][0].update(unknown="not interpreted")):
            with self.subTest(change=change):
                design = design_fixture(); change(design["external_io"])
                with self.assertRaises(DomainError):
                    validate_shape(design)

    def test_binding_changes_invalidate_graph_but_layout_changes_do_not(self):
        design = design_fixture(); original = fingerprint(design, "graph_editor")
        design["layout"]["viewport"]["zoom"] = 0.5
        self.assertEqual(fingerprint(design, "graph_editor"), original)
        design["external_io"]["ports"][0]["name"] = "renamed_commands"
        self.assertNotEqual(fingerprint(design, "graph_editor"), original)

    def test_store_roundtrip_retains_old_snapshot_runs_and_review(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)
            legacy = design_fixture(); del legacy["external_io"]
            fixture = path / "fixture.json"; fixture.write_text(json.dumps(legacy), encoding="utf-8")
            store = ProjectStore(path / "store", fixture)
            start = store.envelope()
            checked = store.validate("global_settings", start["revision"]["id"])
            store.review(checked["runs"][-1]["id"], "accepted", "Software fixture review.", operator={"actor": "development_assistant"})
            old = copy.deepcopy(store._state)
            edited = copy.deepcopy(legacy); edited["external_io"] = design_fixture()["external_io"]
            saved = store.save(edited, start["revision"]["id"])
            reopened = ProjectStore(path / "store")
            self.assertEqual(reopened._state["snapshots"][start["revision"]["id"]], legacy)
            self.assertEqual(reopened._state["runs"], old["runs"])
            self.assertEqual(reopened._state["reviews"], old["reviews"])
            self.assertEqual(saved["design"]["external_io"], edited["external_io"])
            self.assertEqual(reopened.envelope()["design"], saved["design"])

    def test_invalid_electrical_draft_and_failed_diagnostics_survive_restart(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)
            initial = design_fixture()
            fixture = path / "fixture.json"; fixture.write_text(json.dumps(initial), encoding="utf-8")
            store = ProjectStore(path / "store", fixture)
            original = store.envelope()
            edited = copy.deepcopy(initial); edited["external_io"]["ports"][0]["width"] = 8
            saved = store.save(edited, original["revision"]["id"])
            checked = store.validate("graph_editor", saved["revision"]["id"])
            self.assertEqual(checked["runs"][-1]["validation_status"], "Failed")
            self.assertIn("external_width_mismatch", [d["code"] for d in checked["runs"][-1]["diagnostics"]])
            reopened = ProjectStore(path / "store")
            self.assertEqual(reopened._state["runs"], store._state["runs"])
            self.assertEqual(reopened._state["snapshots"][original["revision"]["id"]], initial)
            self.assertEqual(reopened.envelope()["design"], edited)


if __name__ == "__main__":
    unittest.main()
