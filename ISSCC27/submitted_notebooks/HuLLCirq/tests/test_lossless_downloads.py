"""Read-only HTTP downloads of the actual scheduler's 134-bit evidence.

The four preserved histories are copied to an ephemeral server. No model,
compiler, synthesizer, extraction, review or replacement vectors are run.
"""
from __future__ import annotations

import hashlib
import http.client
import json
from pathlib import Path
import shutil
import tempfile
import threading
import unittest

from hullcirq.server import make_server
from hullcirq.store import ProjectStore
from hullcirq.verification import object_hash

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "results" / "npu_scheduler_continuous_flow"
HISTORIES = ("state.json", "generation.json", "workflow.json", "implementation_specs.json")


def hashes(directory):
    return {name: hashlib.sha256((directory / name).read_bytes()).hexdigest() for name in HISTORIES}


def wide_integers(value):
    if type(value) is int:
        return [value] if abs(value) > 2**53 else []
    if isinstance(value, dict):
        return [number for item in value.values() for number in wide_integers(item)]
    if isinstance(value, list):
        return [number for item in value for number in wide_integers(item)]
    return []


class LosslessDownloadHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not all((EVIDENCE / name).is_file() for name in HISTORIES):
            raise unittest.SkipTest("The actual scheduler continuation evidence has not been preserved.")
        cls.source_hashes = hashes(EVIDENCE)
        cls.temporary = tempfile.TemporaryDirectory(prefix="hullcirq-lossless-downloads-")
        cls.copied = Path(cls.temporary.name)
        for name in HISTORIES:
            shutil.copyfile(EVIDENCE / name, cls.copied / name)
        cls.server = make_server("127.0.0.1", 0, ProjectStore(cls.copied), ROOT)
        cls.copied_hashes = hashes(cls.copied)
        cls.thread = threading.Thread(target=cls.server.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True)
        cls.thread.start()
        cls.raw = {name: json.loads((EVIDENCE / name).read_text(encoding="utf-8")) for name in HISTORIES}
        cls.scheduler = next(job for job in reversed(cls.raw["generation.json"]["jobs"]) if job["node_id"] == "node-scheduler")
        cls.pe = next(job for job in reversed(cls.raw["generation.json"]["jobs"]) if job["node_id"] == "node-pe")
        cls.spec = next(record for record in reversed(cls.raw["implementation_specs.json"]["specs"]) if record["node_id"] == "node-scheduler")

    @classmethod
    def tearDownClass(cls):
        cls.server.generation.close()
        cls.server.workflow.close()
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)
        try:
            if hashes(EVIDENCE) != cls.source_hashes:
                raise AssertionError("The original preserved evidence changed during read-only HTTP QA.")
            if hashes(cls.copied) != cls.copied_hashes:
                raise AssertionError("A download or context preview changed a durable copied history.")
        finally:
            cls.temporary.cleanup()

    def request(self, path, body=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_address[1], timeout=20)
        headers = {"Content-Type": "application/json"} if body is not None else {}
        try:
            connection.request("POST" if body is not None else "GET", path,
                               json.dumps(body) if body is not None else None, headers)
            response = connection.getresponse()
            raw = response.read()
            return response.status, dict(response.getheaders()), raw, json.loads(raw)
        finally:
            connection.close()

    def assert_artifact(self, path, expected, require_wide=False):
        status, headers, raw, actual = self.request(path)
        self.assertEqual(status, 200, actual)
        self.assertTrue(headers["Content-Type"].startswith("application/json"))
        self.assertEqual(object_hash(actual), object_hash(expected))
        # The response itself remains the authoritative Python serialization.
        self.assertEqual(raw, json.dumps(expected, ensure_ascii=False, allow_nan=False).encode("utf-8"))
        if require_wide:
            self.assertTrue(wide_integers(actual), "No actual wide configuration integer was checked.")
            self.assertTrue(any(number.bit_length() > 130 for number in wide_integers(actual)))
        return actual

    def test_s07_document_full_record_and_s06_source_preserve_actual_134_bit_values(self):
        spec = self.server.implementation_specs.spec(self.spec["id"])
        self.assert_artifact(f'/api/implementation-specs/{spec["id"]}', spec, True)
        self.assert_artifact(f'/api/artifacts/implementation-specs/{spec["id"]}/specification', spec["specification"], True)
        source = self.server.workflow.run(spec["source_run_id"])
        self.assert_artifact(f'/api/workflow/runs/{source["id"]}', source, True)
        self.assert_artifact(f'/api/artifacts/workflow/{source["id"]}/verification-plan', source["verification_plan"], True)

    def test_s05_and_s06_saved_plan_downloads_keep_the_same_frozen_scheduler_plan(self):
        runs = [run for run in self.raw["workflow.json"]["runs"] if run["candidate_id"] == self.scheduler["id"]]
        self.assertEqual({run["stage_id"] for run in runs}, {"local_synthesis", "local_netlist_simulation"})
        for saved in runs:
            run = self.server.workflow.run(saved["id"])
            self.assert_artifact(f'/api/workflow/runs/{run["id"]}', run, True)
            self.assert_artifact(f'/api/artifacts/workflow/{run["id"]}/verification-plan', self.scheduler["verification_plan"], True)

    def test_saved_scheduler_and_pe_generation_contexts_are_unmodified(self):
        for saved in (self.scheduler, self.pe):
            job = self.server.generation.job(saved["id"])
            self.assert_artifact(f'/api/generation/jobs/{job["id"]}', job, saved is self.scheduler)
            self.assert_artifact(f'/api/artifacts/generation/{job["id"]}/context', saved["context"])

    def test_context_preview_download_is_exact_and_old_evicted_preview_is_actionable(self):
        contexts = []
        for index in range(17):
            status, _, raw, preview = self.request('/api/generation/context', {
                "node_id": "node-pe", "revision_id": self.raw["state.json"]["revision"]["id"],
                "instruction": f"Read-only download QA {index}; unicode: λ\nNo model request.",
            })
            self.assertEqual(status, 200, preview)
            contexts.append((raw, preview))
        first = contexts[0][1]
        status, _, _, error = self.request(f'/api/artifacts/generation-preview/{first["context_id"]}/context')
        self.assertEqual(status, 404)
        self.assertEqual(error["error"]["code"], "preview_not_found")
        self.assertIn("Context Preview again", error["error"]["message"])
        latest_raw, latest = contexts[-1]
        status, _, downloaded, _ = self.request(f'/api/artifacts/generation-preview/{latest["context_id"]}/context')
        self.assertEqual(status, 200)
        self.assertEqual(downloaded, latest_raw)

    def test_artifact_whitelist_rejects_arbitrary_fields_paths_and_mutations(self):
        identifier = self.spec["id"]
        for path in (
            f'/api/artifacts/implementation-specs/{identifier}/source_context',
            f'/api/artifacts/implementation-specs/{identifier}/specification/public_ports',
            '/api/artifacts/files/state.json/content',
            '/api/artifacts/workflow/%2e%2e%2fstate.json/verification-plan',
            '/api/artifacts/workflow/%5cstate.json/verification-plan',
            '/api/artifacts/workflow/missing/verification-plan',
        ):
            with self.subTest(path=path):
                self.assertEqual(self.request(path)[0], 404)
        self.assertEqual(self.request(f'/api/artifacts/implementation-specs/{identifier}/specification', {})[0], 404)
        self.assertEqual(hashes(self.copied), self.copied_hashes)

    def test_service_metadata_describes_current_partial_scope(self):
        status, _, _, envelope = self.request('/api/project')
        self.assertEqual(status, 200)
        self.assertEqual(envelope["implementation"]["milestone"], "M2-J")
        self.assertEqual(envelope["implementation"]["scope"], "node_global_functional_verification_routed_layout_drc_lvs_and_postlayout_preflight")
        for stage_id in ("global_synthesis", "global_netlist_simulation", "layout", "drc", "lvs"):
            stage = next(s for s in envelope["workflow"] if s["id"] == stage_id)
            self.assertTrue(stage["implemented"])
            # This preserved two-node fixture has no adopted S08 result.
            self.assertEqual(stage["execution_status"], "Not Run")
            self.assertIsNone(stage["accepted_run_id"])
        accepted = [node for node in envelope["implementation_spec_nodes"] if node["accepted_spec_id"]]
        self.assertEqual({node["node_id"] for node in accepted}, {"node-scheduler", "node-pe"})
        self.assertFalse(envelope["implementation"]["layout_executed"])
        self.assertFalse(envelope["implementation"]["pdk_used"])


if __name__ == "__main__":
    unittest.main()
