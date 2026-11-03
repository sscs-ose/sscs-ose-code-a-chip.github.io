"""Component integrity and graph-copy checks; no LLM or EDA execution."""
import base64
import copy
import gzip
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from hullcirq.domain import DomainError
from hullcirq.store import ProjectStore, strict_loads
from hullcirq.workspace import WorkspaceRegistry, digest


class ComponentTests(unittest.TestCase):
    def setUp(self):
        qa = Path(__file__).resolve().parents[1] / ".work" / "cm"
        qa.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=qa)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.registry = WorkspaceRegistry(self.root / "workspace")
        source_path = self.root / "source"
        ProjectStore(source_path)
        source = self.registry.register_legacy(source_path, "Source")
        self.pid, self.sid = source["project_id"], source["system_id"]
        self.target = self.registry.create_project("Target")

    def publish(self, node_ids=None):
        return self.registry.publish_component(self.pid, self.sid, node_ids=node_ids, name="Sequence")

    def target_store(self):
        return ProjectStore(self.registry.resolve_system(self.target["project_id"], self.target["system_id"])["path"])

    def instantiate(self, metadata, name="Unit"):
        env = self.target_store().envelope()
        return self.registry.instantiate_component(self.target["project_id"], self.target["system_id"], metadata["id"], metadata["version"], env["revision"]["id"], name)

    def test_whole_graph_publish_preserves_source_snapshot_history_and_is_immutable(self):
        meta = self.publish()
        package = self.registry.component_package(meta["id"], meta["version"])
        self.assertEqual(meta["node_count"], 2)
        self.assertEqual(len(package["design"]["edges"]), 1)
        state = next(f for f in package["source_history"] if f["file"] == "state.json")
        retained = strict_loads(gzip.decompress(base64.b64decode(state["data"])).decode("utf-8"))
        self.assertEqual(retained["design"], package["source_snapshot"])
        self.assertIn("provenance", package["source"]["evidence_scope"])
        self.assertTrue(self.registry.import_component_package(package)["already_present"])
        changed = copy.deepcopy(package)
        changed["component"]["name"] = "Other"
        changed["sha256"] = digest({k: v for k, v in changed.items() if k != "sha256"})
        with self.assertRaises(DomainError) as caught:
            self.registry.import_component_package(changed)
        self.assertEqual(caught.exception.code, "component_version_conflict")

    def test_subgraph_exports_crossing_port_boundary(self):
        meta = self.publish(["node-producer"])
        package = self.registry.component_package(meta["id"], meta["version"])
        self.assertEqual(len(package["design"]["nodes"]), 1)
        self.assertEqual(package["design"]["edges"], [])
        self.assertEqual(len(package["public_ports"]), 1)
        self.assertEqual(package["public_ports"][0]["direction"], "output")
        self.assertEqual(package["public_ports"][0]["port_id"], "port-producer-data")

    def test_repeated_instantiation_uses_unique_ids_modules_and_no_adopted_results(self):
        meta = self.publish()
        first = self.instantiate(meta, "First")
        second = self.instantiate(meta, "Second")
        design = second["envelope"]["design"]
        self.assertEqual(len(design["nodes"]), 4)
        self.assertEqual(len(design["edges"]), 2)
        self.assertEqual(len({n["id"] for n in design["nodes"]}), 4)
        self.assertEqual(len({n["module_name"] for n in design["nodes"]}), 4)
        self.assertEqual(second["envelope"]["runs"], [])
        self.assertEqual(second["envelope"]["reviews"], [])
        self.assertEqual(len(design["component_instances"]), 2)
        self.assertNotEqual(first["instance"]["id"], second["instance"]["id"])
        self.assertTrue(all(n["component_ref"]["version"] == 1 for n in design["nodes"]))

    def test_new_version_leaves_existing_instance_pinned(self):
        first = self.publish()
        self.instantiate(first)
        second = self.registry.publish_component(self.pid, self.sid, name="Sequence revision", component_id=first["id"])
        self.assertEqual(second["version"], 2)
        design = self.target_store().envelope()["design"]
        self.assertEqual(design["component_instances"][0]["version"], 1)
        self.assertEqual(design["component_instances"][0]["package_sha256"], first["sha256"])

    def test_corruption_unknown_endpoint_cycle_and_contract_rejected(self):
        meta = self.publish(["node-producer"])
        original = self.registry.component_package(meta["id"], 1)
        for mutation in ("checksum", "endpoint", "cycle", "width", "history", "boundary"):
            value = copy.deepcopy(original)
            if mutation == "checksum":
                value["sha256"] = "0" * 64
            elif mutation == "endpoint":
                value["public_ports"][0]["node_id"] = "missing"
            elif mutation == "cycle":
                value["design"]["nodes"][0]["parent_id"] = value["design"]["nodes"][0]["id"]
            elif mutation == "width":
                value["public_ports"][0]["width"] = 31
            elif mutation == "history":
                value["source_history"][0]["file"] = "../escape.json"
            else:
                value["public_ports"] = []
            if mutation != "checksum":
                value["sha256"] = digest({k: v for k, v in value.items() if k != "sha256"})
            with self.subTest(mutation=mutation), self.assertRaises(DomainError):
                self.registry.import_component_package(value)

    def test_stale_revision_readonly_target_and_domain_mismatch_do_not_mutate(self):
        meta = self.publish()
        path = self.target_store().state_path
        old = path.read_bytes()
        with self.assertRaises(DomainError):
            self.registry.instantiate_component(self.target["project_id"], self.target["system_id"], meta["id"], 1, "stale", "Unit")
        self.assertEqual(path.read_bytes(), old)
        source_env = ProjectStore(self.registry.resolve_system(self.pid, self.sid)["path"]).envelope()
        with self.assertRaises(DomainError):
            self.registry.instantiate_component(self.pid, self.sid, meta["id"], 1, source_env["revision"]["id"], "Unit")
        env = self.target_store().envelope()
        env["design"]["settings"]["reset_active"] = "low"
        self.target_store().save(env["design"], env["revision"]["id"])
        previous = path.read_bytes()
        with self.assertRaises(DomainError):
            self.instantiate(meta)
        self.assertEqual(path.read_bytes(), previous)

    def test_sideband_public_interface_uses_new_associated_stream_id(self):
        editable = self.registry.duplicate_system(self.pid, self.sid, "Sideband source")
        resolved = self.registry.resolve_system(editable["project_id"], editable["system_id"])
        store = ProjectStore(resolved["path"])
        env = store.envelope()
        node = env["design"]["nodes"][0]
        node["ports"].append({"id": "port-producer-meta", "name": "metadata", "direction": "output", "width": 8,
                              "signed": False, "protocol": "raw", "clock": "clk", "reset": "rst",
                              "sideband": {"kind": "metadata", "associated_port_id": "port-producer-data"}})
        store.save(env["design"], env["revision"]["id"])
        metadata = self.registry.publish_component(editable["project_id"], editable["system_id"], [node["id"]], "Sideband")
        result = self.instantiate(metadata)
        imported = result["envelope"]["design"]["nodes"][0]
        stream = next(p for p in imported["ports"] if p["protocol"] == "valid_ready")
        exposed = next(p for p in result["instance"]["public_ports"] if p["protocol"] == "raw")
        self.assertEqual(exposed["sideband"]["associated_port_id"], stream["id"])


if __name__ == "__main__":
    unittest.main()
