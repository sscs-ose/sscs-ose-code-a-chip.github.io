"""Temporary component projection/provenance fixtures; no circuit execution."""
import base64
import copy
import gzip
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hullcirq.components import validate_package
from hullcirq.domain import DomainError
from hullcirq.store import ProjectStore
from hullcirq.workspace import WorkspaceRegistry, digest
from test_external_io import design_fixture


class ExternalIoComponentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.snapshot = design_fixture()
        other = copy.deepcopy(self.snapshot["nodes"][0])
        other.update(id="other-counter", name="Other Counter", module_name="other_counter_module")
        for port in other["ports"]:
            port["id"] = "other-" + port["id"]
        self.snapshot["nodes"].append(other)
        original_io = copy.deepcopy(self.snapshot["external_io"])
        for port in original_io["ports"]:
            port["id"] = "other-" + port["id"]
            port["name"] = "other_" + port["name"]
            self.snapshot["external_io"]["ports"].append(port)
        for connection in original_io["connections"]:
            connection.update(id="other-" + connection["id"], external_port_id="other-" + connection["external_port_id"],
                              node_id="other-counter", port_id="other-" + connection["port_id"])
            self.snapshot["external_io"]["connections"].append(connection)
        fixture = self.root / "fixture.json"
        fixture.write_text(json.dumps(self.snapshot), encoding="utf-8")
        self.source = self.root / "source"
        ProjectStore(self.source, fixture)
        self.registry = WorkspaceRegistry(self.root / "workspace")
        self.registered = self.registry.register_legacy(self.source, "Source")
        self.source = Path(self.registry.resolve_system(self.registered["project_id"], self.registered["system_id"])["path"])

    def publish(self, selected=None):
        meta = self.registry.publish_component(self.registered["project_id"], self.registered["system_id"], node_ids=selected, name="Boundary fixture")
        return meta, self.registry.component_package(meta["id"], meta["version"])

    def test_subset_retains_only_its_boundaries_and_complete_original_evidence(self):
        source_file = self.source / "state.json"
        before_bytes, before_mtime = source_file.read_bytes(), source_file.stat().st_mtime_ns
        _, package = self.publish(["counter"])
        self.assertEqual([p["id"] for p in package["design"]["external_io"]["ports"]], ["top-in", "top-out"])
        self.assertTrue(all(c["node_id"] == "counter" for c in package["design"]["external_io"]["connections"]))
        self.assertEqual(package["source_snapshot"], self.snapshot)
        original = next(item for item in package["source_history"] if item["file"] == "state.json")
        retained = gzip.decompress(base64.b64decode(original["data"]))
        self.assertEqual(retained, before_bytes)
        self.assertEqual(source_file.read_bytes(), before_bytes)
        self.assertEqual(source_file.stat().st_mtime_ns, before_mtime)
        validate_package(package)

    def test_full_selection_retains_the_whole_io_model_including_unbound_draft(self):
        store = ProjectStore(self.source)
        old = store.envelope()
        edited = copy.deepcopy(old["design"])
        edited["external_io"]["ports"].append({"id": "future-port", "name": "future_signal", "direction": "input",
                                               "width": 1, "signed": False, "protocol": "raw"})
        store.save(edited, old["revision"]["id"])
        _, package = self.publish()
        self.assertEqual(package["design"]["external_io"], edited["external_io"])
        self.assertEqual(package["source_snapshot"], edited)

    def test_self_consistent_tampered_boundary_still_fails_source_projection(self):
        _, package = self.publish(["counter"])
        changed = copy.deepcopy(package)
        changed["design"]["external_io"]["ports"][0]["name"] = "invented_boundary_alias"
        changed["sha256"] = digest({key: value for key, value in changed.items() if key != "sha256"})
        with self.assertRaises(DomainError) as caught:
            validate_package(changed)
        self.assertEqual(caught.exception.code, "component_source_mismatch")

    def test_omitting_new_bindings_from_package_cannot_claim_the_original_source(self):
        _, package = self.publish(["counter"])
        changed = copy.deepcopy(package); del changed["design"]["external_io"]
        changed["sha256"] = digest({key: value for key, value in changed.items() if key != "sha256"})
        with self.assertRaises(DomainError) as caught:
            validate_package(changed)
        self.assertEqual(caught.exception.code, "component_source_mismatch")

    def test_instantiation_keeps_target_top_boundary_empty_and_remaps_component_ports(self):
        metadata, _ = self.publish(["counter"])
        target = self.registry.create_project("Target")
        resolved = self.registry.resolve_system(target["project_id"], target["system_id"])
        before = ProjectStore(resolved["path"]).envelope()
        result = self.registry.instantiate_component(target["project_id"], target["system_id"], metadata["id"], metadata["version"],
                                                     before["revision"]["id"], "Counter unit")
        self.assertEqual(result["envelope"]["design"]["external_io"], before["design"]["external_io"])
        self.assertEqual(len(result["instance"]["public_ports"]), 2)
        self.assertTrue(all(p["node_id"] != "counter" for p in result["instance"]["public_ports"]))
        self.assertEqual(result["envelope"]["runs"], [])
        self.assertEqual(result["envelope"]["reviews"], [])


if __name__ == "__main__":
    unittest.main()
