"""Functional Map integration QA: read-only original bytes and isolated faults."""
from __future__ import annotations
import base64
import copy
import gzip
import hashlib
import http.client
import json
from pathlib import Path
import re
import sys
import threading
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tests")]
import test_global_generation as fixtures
from hullcirq import layout_role_view as view
from hullcirq.domain import DomainError
from hullcirq.server import make_server
from hullcirq.store import strict_loads
from hullcirq.verification import object_hash


class ReadOnlyPhysicalDouble:
    """Isolated route state; actual archived record bytes are only read."""
    def __init__(self):
        self.lock = threading.RLock()
        self.record = strict_loads((ROOT / view.SOURCE_ROOT / "layout_record.json").read_text(encoding="utf-8"))
        self._state = {"runs": [self.record]}
        self.freshness = "Current"
        self.run_calls = []
        self.observe_design = Mock(side_effect=AssertionError("Read-only feature must not observe or save"))
        self._persist = Mock(side_effect=AssertionError("Read-only feature must not save"))
        self.start = Mock(side_effect=AssertionError("No EDA"))
        self.review = Mock(side_effect=AssertionError("No adoption writes"))

    def _run(self, identifier):
        result = next((run for run in self._state["runs"] if run["id"] == identifier), None)
        if result is None:
            raise DomainError("physical_run_not_found", "Selected layout run does not exist.", 404)
        return result

    def _decorate(self, record):
        result = copy.deepcopy(record)
        result["freshness"] = self.freshness
        if self.freshness != "Current" and result["review_status"] == "Accepted":
            result["review_status"] = "Awaiting Review"
        return result

    def run(self, identifier):
        self.run_calls.append(identifier)
        return self._decorate(self._run(identifier))

    def artifact(self, identifier, artifact):
        self._run(identifier)
        raise DomainError("physical_artifact_not_found", "Unknown fixed artifact.", 404)

    def is_active(self):
        return False

    def close(self):
        pass


class FunctionalMapHTTPTests(unittest.TestCase):
    def test_repaired_npu2_map_is_bound_to_new_run_and_withholds_changed_family(self):
        run_id = 'physical-workflow-4e818ce3905c4bd1ad0e9b50033271cb'
        registration = view._registration(run_id)
        run = strict_loads((ROOT / registration['source_root'] / 'layout_record.json').read_text(encoding='utf-8'))
        display = {'status': {key: run[key] for key in
                            ('execution_status', 'validation_status', 'review_status')}, 'historical': False}
        display['status']['freshness'] = 'Current'
        missing = DomainError('physical_artifact_missing', 'Saved source is unavailable on this host.', 409)
        with patch.object(view, '_artifact_path', side_effect=missing):
            metadata = view.functional_map_metadata(ROOT, run, display)
            raw, _, _, _ = view.functional_map_bytes(ROOT, run, 'functional-map-data')
        self.assertTrue(metadata['available'])
        self.assertEqual(metadata['source_binding']['layout_run_id'], run_id)
        self.assertNotEqual(registration['view_root'], view._registration(
            'physical-workflow-7490fdd470a941c9b097033613816d72')['view_root'])
        mapping = strict_loads(gzip.decompress(raw).decode('utf-8'))
        self.assertEqual(mapping['summary']['final_cells'], 33681)
        self.assertEqual([r['id'] for r in mapping['roles'] if r.get('group') == 'pe'],
                         ['pe00', 'pe01', 'pe10', 'pe11'])
        changed = next(c for c in mapping['cells'] if c['id'] == '_4186_')
        self.assertEqual((changed['role'], changed['status']), ('unknown', 'unknown'))
        self.assertEqual(mapping['summary']['annotation_policy'], 'changed_family_unknown_v1')
        self.assertFalse(any(json.loads(e)['kind'] == 'retained_synthesis_instance' for e in changed['evidence']))
        corrupted = Mock()
        corrupted.read_bytes.return_value = b'not the final repaired layout'
        with patch.object(view, '_artifact_path', return_value=corrupted):
            self.assertEqual(view.functional_map_metadata(ROOT, run, display)['reason']['code'],
                             'functional_map_integrity_error')
        relabeled = copy.deepcopy(run)
        relabeled['id'] = 'physical-workflow-7490fdd470a941c9b097033613816d72'
        relabeled['record_hash'] = object_hash({k: v for k, v in relabeled.items() if k != 'record_hash'})
        with patch.object(view, '_artifact_path', side_effect=missing):
            self.assertEqual(view.functional_map_metadata(ROOT, relabeled, display)['reason']['code'],
                             'functional_map_binding_mismatch')

    def test_current_npu2_bundle_is_exactly_registered_and_has_four_explicit_pes(self):
        run_id = "physical-workflow-7490fdd470a941c9b097033613816d72"
        registration = view._registration(run_id)
        source_root = ROOT / registration["source_root"]
        run = strict_loads((source_root / "layout_record.json").read_text(encoding="utf-8"))
        display = {"status": {key: run[key] for key in
                              ("execution_status", "validation_status", "review_status")},
                   "historical": False}
        display["status"]["freshness"] = "Current"
        missing = DomainError("physical_artifact_missing", "Saved source is unavailable on this host.", 409)
        with patch.object(view, "_artifact_path", side_effect=missing):
            metadata = view.functional_map_metadata(ROOT, run, display)
            raw, mime, disposition, filename = view.functional_map_bytes(
                ROOT, run, "functional-map-data")
        self.assertTrue(metadata["available"])
        self.assertEqual(metadata["source_binding"]["layout_run_id"], run_id)
        self.assertEqual(metadata["source_binding"]["artifact_verification"],
                         "registered_source_archive_fallback")
        self.assertEqual((mime, disposition, filename),
                         ("application/gzip", "attachment", "layout_roles.json.gz"))
        mapping = strict_loads(gzip.decompress(raw).decode("utf-8"))
        self.assertEqual(mapping["top_module"], "hullcirq_npu2_top")
        self.assertEqual(mapping["summary"]["final_cells"], 35193)
        self.assertEqual([role["id"] for role in mapping["roles"] if role.get("group") == "pe"],
                         ["pe00", "pe01", "pe10", "pe11"])
        self.assertTrue(all(mapping["summary"]["by_role"][role] > 0 for role in
                            ("control", "buffer", "scheduler", "dispatcher", "pe00", "pe01",
                             "pe10", "pe11", "collector", "post", "fifo")))
        corrupted = Mock()
        corrupted.read_bytes.return_value = b"different retained result bytes"
        with patch.object(view, "_artifact_path", return_value=corrupted):
            rejected = view.functional_map_metadata(ROOT, run, display)
        self.assertFalse(rejected["available"])
        self.assertEqual(rejected["reason"]["code"], "functional_map_integrity_error")

    def setUp(self):
        self.qa = fixtures.GlobalSoftwareTests("test_manifest_exact_sources_and_prompt_excludes_numeric_test_job")
        self.qa.setUp()
        self.addCleanup(self.qa.doCleanups)
        self.server = make_server("127.0.0.1", 0, self.qa.store, ROOT)
        self.original = self.server.physical_workflow
        self.double = ReadOnlyPhysicalDouble()
        self.server.physical_workflow = self.double
        old_source = ROOT / view.SOURCE_ROOT
        archived_artifacts = {
            "gds": old_source / "artifacts/runs/physical/57-magic-streamout/hullcirq_npu.gds",
            "def": old_source / "artifacts/runs/physical/53-odb-cellfrequencytables/hullcirq_npu.def",
            "netlist": old_source / "artifacts/runs/physical/52-openroad-fillinsertion/hullcirq_npu.nl.v",
        }
        self.artifact_patch = patch.object(
            view, "_artifact_path", side_effect=lambda checks, entry: archived_artifacts[entry["id"]])
        self.artifact_patch.start()
        self.addCleanup(self.artifact_patch.stop)
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": .02}, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop)
        self.prefix = "/api/physical-workflow/runs/" + view.RUN_ID + "/functional-map"
        self.artifacts = "/api/artifacts/physical-workflow/" + view.RUN_ID + "/"

    def stop(self):
        self.server.shutdown()
        self.server.server_close()
        self.original.close()
        self.server.workflow.close()
        self.server.generation.close()
        self.thread.join(3)

    def request(self, path, method="GET"):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_address[1], timeout=30)
        try:
            connection.request(method, path, "{}" if method == "POST" else None,
                               {"Content-Type": "application/json"} if method == "POST" else {})
            response = connection.getresponse()
            return response.status, response.read(), response.getheaders()
        finally:
            connection.close()

    def metadata(self):
        status, raw, headers = self.request(self.prefix)
        self.assertEqual(status, 200)
        return strict_loads(raw.decode("utf-8"))

    def assert_read_only(self):
        for method in (self.double.observe_design, self.double._persist, self.double.start, self.double.review):
            method.assert_not_called()

    def test_exact_bound_run_metadata_and_all_five_original_downloads(self):
        before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in (self.qa.directory / "project").glob("*.json")}
        metadata = self.metadata()
        self.assertTrue(metadata["available"])
        self.assertFalse(metadata["historical"])
        self.assertEqual(metadata["run_id"], view.RUN_ID)
        self.assertEqual(metadata["source_binding"]["layout_run_id"], view.RUN_ID)
        self.assertEqual(metadata["source_binding"]["source_manifest_sha256"], self.double.record["source_manifest_sha256"])
        self.assertEqual(metadata["status_scope"], "recorded_physical_workflow_state")
        self.assertIsNone(metadata["reason"])
        for identifier, (filename, mime, disposition) in view.FILES.items():
            with self.subTest(identifier=identifier):
                status, raw, header_list = self.request(self.artifacts + identifier)
                headers = dict(header_list)
                self.assertEqual(status, 200)
                self.assertEqual(raw, (ROOT / view.VIEW_ROOT / filename).read_bytes())
                self.assertEqual(headers["Content-Type"], mime)
                self.assertEqual(headers["Content-Disposition"], f'{disposition}; filename="{filename}"')
                self.assertEqual(int(headers["Content-Length"]), len(raw))
                self.assertEqual(headers["Cache-Control"], "no-store")
                self.assertEqual(len([h for h in header_list if h[0].lower() == "content-security-policy"]), 1)
        self.assertEqual({p: hashlib.sha256(p.read_bytes()).hexdigest() for p in (self.qa.directory / "project").glob("*.json")}, before)
        self.assertEqual(self.double.run_calls, [])
        self.assert_read_only()

    def test_html_has_one_hash_only_csp_and_normal_gui_policy_is_unchanged(self):
        status, html, headers = self.request(self.artifacts + "functional-map-html")
        self.assertEqual(status, 200)
        policy = dict(headers)["Content-Security-Policy"]
        body = re.search(rb"<script>\s*(.*?)</script>", html, re.S)[0]
        exact = re.search(rb"<script>(.*?)</script>", body, re.S)[1]
        expected_hash = base64.b64encode(hashlib.sha256(exact).digest()).decode("ascii")
        self.assertIn("script-src 'sha256-" + expected_hash + "'", policy)
        self.assertNotIn("script-src 'unsafe-inline'", policy)
        self.assertIn("frame-ancestors 'self'", policy)
        self.assertIn("connect-src 'none'", policy)
        self.assertIn("form-action 'none'", policy)
        for path in ("/", self.artifacts + "functional-map-png", self.prefix):
            _, _, header_list = self.request(path)
            default = dict(header_list)["Content-Security-Policy"]
            self.assertIn("script-src 'self'", default)
            self.assertIn("frame-ancestors 'none'", default)
            self.assertEqual(len([h for h in header_list if h[0].lower() == "content-security-policy"]), 1)
        self.assert_read_only()

    def test_stale_review_and_newer_same_epoch_run_are_explicit_history(self):
        self.double.freshness = "Stale"
        stale = self.metadata()
        self.assertTrue(stale["available"])
        self.assertTrue(stale["historical"])
        self.assertEqual(stale["status"]["freshness"], "Stale")
        self.assertEqual(stale["status"]["review_status"], "Awaiting Review")
        self.double.freshness = "Current"
        newer = copy.deepcopy(self.double.record)
        newer["id"] = "newer-same-epoch-run"
        self.double._state["runs"].append(newer)
        historical = self.metadata()
        self.assertTrue(historical["available"])
        self.assertTrue(historical["historical"])
        self.assertEqual(historical["status"]["freshness"], "Current")
        self.double._state["runs"].pop()
        self.double.record["review_status"] = "Changes Requested"
        self.double.record["record_hash"] = object_hash({k: v for k, v in self.double.record.items() if k != "record_hash"})
        reviewed = self.metadata()
        self.assertTrue(reviewed["available"])
        self.assertTrue(reviewed["historical"])
        self.assertEqual(reviewed["status"]["review_status"], "Changes Requested")
        self.assert_read_only()

    def test_same_geometry_predecessor_other_run_and_default_never_inherit_view(self):
        other = copy.deepcopy(self.double.record)
        other["id"] = "physical-workflow-301f86d714ca4312ac087a9202d3d4d4"
        self.double._state["runs"].append(other)
        status, raw, _ = self.request("/api/physical-workflow/runs/" + other["id"] + "/functional-map")
        self.assertEqual(status, 200)
        metadata = strict_loads(raw.decode())
        self.assertFalse(metadata["available"])
        self.assertIsNone(metadata["html_url"])
        self.assertIsNone(metadata["source_binding"])
        self.assertEqual(metadata["reason"]["code"], "functional_map_not_available")
        status, _, _ = self.request("/api/artifacts/physical-workflow/" + other["id"] + "/functional-map-html")
        self.assertEqual(status, 409)
        self.double._state["runs"] = []
        self.assertEqual(self.request(self.prefix)[0], 404)
        self.assert_read_only()

    def test_modified_lineage_or_hash_declarations_fail_closed_even_with_new_record_hash(self):
        original = copy.deepcopy(self.double.record)
        for field in ("revision_id", "source_manifest_sha256", "global_job_id", "source_key"):
            self.double.record[field] = "changed-software-fixture"
            self.double.record["record_hash"] = object_hash({k: v for k, v in self.double.record.items() if k != "record_hash"})
            with self.subTest(field=field):
                metadata = self.metadata()
                self.assertFalse(metadata["available"])
                self.assertIsNone(metadata["html_url"])
                self.assertEqual(metadata["reason"]["code"], "functional_map_binding_mismatch")
                self.assertEqual(self.request(self.artifacts + "functional-map-html")[0], 409)
            self.double.record.clear()
            self.double.record.update(copy.deepcopy(original))
        self.assert_read_only()

    def test_corrupt_immutable_html_is_unavailable_and_never_served(self):
        original_read = view._read_below
        def altered(root, relative):
            raw = original_read(root, relative)
            return raw + b"INJECTED SOFTWARE FAULT" if str(relative) == "layout_roles.html" else raw
        with patch.object(view, "_read_below", side_effect=altered):
            metadata = self.metadata()
            self.assertFalse(metadata["available"])
            self.assertEqual(metadata["reason"]["code"], "functional_map_integrity_error")
            status, raw, _ = self.request(self.artifacts + "functional-map-html")
            self.assertEqual(status, 409)
            self.assertNotIn(b"INJECTED SOFTWARE FAULT", raw)
        self.assert_read_only()

    def test_fixed_allowlist_path_rejection_and_no_post_action(self):
        paths = [self.artifacts + "functional-map-unknown", self.artifacts + "../../state.json",
                 self.artifacts + "%2e%2e%2fstate.json", self.artifacts + "functional-map-html/extra",
                 "/api/artifacts/physical-workflow/bad%5Cid/functional-map-html", self.prefix + "/extra"]
        for path in paths:
            with self.subTest(path=path):
                self.assertEqual(self.request(path)[0], 404)
        self.assertEqual(self.request(self.prefix, "POST")[0], 404)
        self.assert_read_only()

    def test_dynamic_descriptor_and_artifact_pin_same_immutable_publication(self):
        # Declared publication doubles; only existing immutable payloads are read.
        first = dict(view._registration(view.RUN_ID), job_id="functional-map-" + "1" * 32)
        second = dict(first, job_id="functional-map-" + "2" * 32)
        with patch("hullcirq.layout_map_generation.read_registration", return_value=first) as current:
            metadata = self.metadata()
            suffix = "?map_generation=" + first["job_id"]
            self.assertEqual(metadata["source_binding"]["registration_job_id"], first["job_id"])
            for name in ("html", "png", "report"):
                self.assertEqual(metadata[name + "_url"], self.artifacts + "functional-map-" + name + suffix)
            current.return_value = second  # publication changed before iframe navigation
            with patch("hullcirq.layout_map_generation.read_registration_version", return_value=first) as version:
                for name in ("html", "png", "report"):
                    status, raw, _ = self.request(metadata[name + "_url"])
                    self.assertEqual(status, 200)
                    self.assertEqual(raw, (ROOT / view.VIEW_ROOT / view.FILES["functional-map-" + name][0]).read_bytes())
                    self.assertEqual(version.call_args.args[2], first["job_id"])
                self.assertEqual(current.call_count, 1, "Pinned reads must not consult the current pointer")
        self.assert_read_only()

    def test_bad_or_unknown_publication_never_falls_back(self):
        error = DomainError("functional_map_not_available", "Unknown declared publication", 409)
        with patch("hullcirq.layout_map_generation.read_registration_version", side_effect=error) as version, \
             patch("hullcirq.layout_map_generation.read_registration") as current:
            for suffix in ("?map_generation=", "?map_generation=a&map_generation=b"):
                self.assertEqual(self.request(self.artifacts + "functional-map-html" + suffix)[0], 409)
            version.assert_not_called()
            self.assertEqual(self.request(self.artifacts + "functional-map-html?map_generation=functional-map-" + "9" * 32)[0], 409)
            self.assertEqual(version.call_count, 1)
            current.assert_not_called()
        self.assert_read_only()

    def test_selected_version_metadata_never_uses_the_latest_pointer(self):
        registration = dict(view._registration(view.RUN_ID), job_id="functional-map-" + "1" * 32)
        suffix = "?map_generation=" + registration["job_id"]
        with patch("hullcirq.layout_map_generation.read_registration_version", return_value=registration) as version, \
             patch("hullcirq.layout_map_generation.read_registration", side_effect=AssertionError("Do not substitute latest")):
            status, raw, _ = self.request(self.prefix + suffix)
            self.assertEqual(status, 200)
            metadata = strict_loads(raw.decode("utf-8"))
            self.assertTrue(metadata["available"])
            self.assertEqual(metadata["source_binding"]["registration_job_id"], registration["job_id"])
            self.assertEqual(version.call_args.args[1]["id"], view.RUN_ID)
            self.assertEqual(version.call_args.args[2], registration["job_id"])
            for name in ("html", "png", "report"):
                self.assertEqual(metadata[name + "_url"], self.artifacts + "functional-map-" + name + suffix)
        self.assert_read_only()

    def test_foreign_or_missing_version_metadata_and_ambiguous_query_do_not_fallback(self):
        error = DomainError("functional_map_integrity_error", "Version belongs to a different source", 409)
        with patch("hullcirq.layout_map_generation.read_registration_version", side_effect=error) as version, \
             patch("hullcirq.layout_map_generation.read_registration", side_effect=AssertionError("Do not substitute latest")):
            for suffix in ("?map_generation=", "?map_generation=a&map_generation=b"):
                self.assertEqual(self.request(self.prefix + suffix)[0], 409)
            version.assert_not_called()
            status, raw, _ = self.request(self.prefix + "?map_generation=functional-map-" + "9" * 32)
            self.assertEqual(status, 200)
            metadata = strict_loads(raw.decode("utf-8"))
            self.assertFalse(metadata["available"])
            self.assertEqual(metadata["reason"]["code"], error.code)
            self.assertIsNone(metadata["html_url"])
        self.assert_read_only()


if __name__ == "__main__":
    unittest.main()
