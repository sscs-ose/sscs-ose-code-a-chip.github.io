"""Isolated S12 browser QA. Explicit doubles never execute EDA or a model.

Fixture reports, counts, geometry and GDS bytes test software only; they are not
evidence that any circuit passed DRC. No live project directory is accessed.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from browser_qa_runtime import browser_environment

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))
sys.path.insert(0, str(PROJECT / "tests"))
from hullcirq.server import RequestHandler, make_server
from hullcirq.store import ProjectStore, utc_now
from test_global_workflow_gui import GlobalGenerationDouble, InMemorySubmissionDouble
from test_physical_workflow_gui import AcceptedBaselineDouble, PhysicalDouble


class DRCDouble(InMemorySubmissionDouble):
    """Controllable API state; fake report geometry is explicitly labeled."""
    def __init__(self, store, physical):
        self.store, self.physical = store, physical
        self.lock = threading.RLock()
        self.runs, self.reviews, self.calls, self.review_calls = [], [], [], []
        self.ready = True
        self.large_output = False
        self.files = {
            "input-gds": (b"SOFTWARE QA ONLY: not real GDS\x00\xff\r\n", "application/octet-stream"),
            "magic-report": (b"SOFTWARE QA ONLY: fixture rule report\r\n", "text/plain; charset=utf-8"),
            "magic-markers": (b'<report-database><description>SOFTWARE QA ONLY</description></report-database>\r\n', "application/xml"),
            "klayout-report": (b'<report-database><description>SOFTWARE QA ONLY</description></report-database>\r\n', "application/xml"),
        }
        for field in ("config", "initial-state", "final-state", "metrics", "tool-versions", "drc-summary", "klayout-violations"):
            self.files[field] = (b'{"software_qa_fixture":true,"wide_integer":1267650600228229401496703205377}\r\n', "application/json")
        self._init_submission_memory(runs=self.runs, reviews=self.reviews)

    def envelope(self):
        with self.lock:
            latest = self.runs[-1] if self.runs else None
            return {"drc_workflow": {"implemented": True, "stage_id": "drc",
                    "runs": copy.deepcopy(self.runs), "reviews": copy.deepcopy(self.reviews),
                    "latest_run_id": latest["id"] if latest else None,
                    "accepted_run_id": latest["id"] if latest and latest["review_status"] == "Accepted" else None,
                    "ready": self.ready, "blocked_reason": None if self.ready else "SOFTWARE QA changed S11 source",
                    "tool_ready": True, "storage_error": None,
                    "configuration_sha256": "software-qa-drc-config",
                    "runtime_configuration": {"software_qa_fixture": True, "tool_processes": 0}}}

    def is_active(self):
        with self.lock:
            return any(run["execution_status"] in ("Queued", "Running") for run in self.runs)

    def start(self, stage, layout, revision, *, _submission=None):
        with self.lock:
            self.calls.append((stage, layout, revision))
            source = self.physical.run(layout)
            run = {"id": "software-qa-drc-" + str(len(self.runs) + 1), "stage_id": stage,
                              "layout_run_id": layout, "revision_id": revision,
                              "layout_record_sha256": "software-qa-layout-record-hash",
                              "input_gds_sha256": next(item["sha256"] for item in source["artifacts"] if item["id"] == "gds"),
                              "configuration_sha256": "software-qa-drc-config", "layout_snapshot": source,
                              "runtime_configuration": {"software_qa_fixture": True},
                              "source_identity": {"software_qa_fixture": True, "wide_integer": 2**100 + 1},
                              "execution_status": "Running", "validation_status": "Not Checked",
                              "review_status": "Awaiting Review", "freshness": "Current",
                              "created_at": utc_now(), "finished_at": None,
                              "checks": {}, "diagnostics": [], "artifacts": [], "software_qa_fixture": True}
            if _submission is not None:
                run["submission_id"] = _submission.submission_id
                _submission.bind(run["id"])
            self.runs.append(run)
            self._persist()

    def transition(self, status):
        with self.lock:
            run = self.runs[-1]
            failed = status == "failed"
            run.update(execution_status="Completed", validation_status="Failed" if failed else "Passed", finished_at=utc_now())
            run["checks"] = {"executed": False, "software_qa_fixture": True,
                             "checks": {"software_fixture_only": "Failed" if failed else "Passed"},
                             "metrics": {"software_qa_fixture": True, "magic_errors": 1 if failed else 0, "klayout_errors": 0},
                             "summary": {"software_qa_fixture": True, "units": "micrometre", "violations": [{"tool": "SOFTWARE QA Magic fixture", "category": "fixture.spacing", "description": "SOFTWARE QA simulated spacing issue", "cell": "software_qa_only", "geometry": ["box (1,2;3,4)"]}] if failed else []},
                             "stdout": "SOFTWARE QA ONLY: no EDA or model process was executed", "retained_files": []}
            run["artifacts"] = [{"id": field, "kind": "software_fixture", "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw), "content_type": mime, "url": "/api/artifacts/drc-workflow/" + run["id"] + "/" + field} for field, (raw, mime) in self.files.items()]
            if self.large_output:
                run["checks"]["stdout"] = "SOFTWARE QA FIRST RECORD SEGMENT\n" + ("SOFTWARE QA large diagnostic record line\n" * 32768) + "SOFTWARE QA LAST RECORD SEGMENT"
            if status == "accepted":
                run["review_status"] = "Accepted"
                self.reviews.append({"id": "software-qa-drc-policy", "run_id": run["id"], "decision": "accepted", "actor": "automation_policy", "provenance": {"policy_id": self.store.review_policy()["id"]}, "note": "SOFTWARE QA simulated policy only"})
            self._persist()

    def run(self, identifier):
        with self.lock:
            return copy.deepcopy(next(run for run in self.runs if run["id"] == identifier))

    def artifact(self, identifier, field):
        run = self.run(identifier)
        return {"layout-record": run["layout_snapshot"], "source-identity": run["source_identity"], "runtime-configuration": run["runtime_configuration"], "artifact-manifest": run["artifacts"]}[field]

    def artifact_bytes(self, identifier, field):
        self.run(identifier)
        return self.files[field]

    def review(self, identifier, decision, note, target_stage=None, *, operator=None):
        with self.lock:
            self.review_calls.append((identifier, decision, note, target_stage))
            self.reviews.append({"id": "software-qa-feedback", "run_id": identifier, "decision": decision, "note": note, "target_stage": target_stage, "actor": (operator or {}).get("actor", "unspecified")})
            self._persist()

    def external_source_changed(self):
        with self.lock:
            self.ready = False
            for run in self.runs:
                run.update(freshness="Stale", review_status="Awaiting Review")
            self._persist()

    def close(self):
        pass


class DRCControlHandler(RequestHandler):
    def do_POST(self):
        if self.path == "/software-qa/transition":
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            self.server.drc_workflow.transition(body["state"])
            self._json({"software_qa_fixture": True})
            return
        if self.path == "/software-qa/external-source":
            self.rfile.read(int(self.headers["Content-Length"]))
            current = self.server.store.envelope()
            design = copy.deepcopy(current["design"])
            design["project"]["name"] = "SOFTWARE QA external edit"
            self.server.store.save(design, current["revision"]["id"])
            self.server.physical_workflow.external_source_changed()
            self.server.drc_workflow.external_source_changed()
            self._json({"software_qa_fixture": True})
            return
        super().do_POST()


BROWSER_TEST = r"""
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const { chromium } = require(process.env.HULLCIRQ_PLAYWRIGHT_PATH || 'playwright');
(async () => {
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  try {
    const context = await browser.newContext(), page = await context.newPage(), writes = [], errors = [], test = id => page.getByTestId(id), url = process.env.HULLCIRQ_SOFTWARE_QA_URL;
    page.setDefaultTimeout(20000); page.on('pageerror', error => errors.push(error.message));
    page.on('request', request => { if (request.method() === 'POST' && new URL(request.url()).pathname.startsWith('/api/')) writes.push(new URL(request.url()).pathname); });
    const original = await (await context.request.get(url + 'api/project')).json();
    const layoutBefore = await (await context.request.get(url + 'api/physical-workflow/runs/software-qa-layout')).body();
    await page.goto(url); await test('stage-layout').click();
    assert.equal(await test('physical-workflow-continue').innerText(), 'Continue to DRC');
    await test('physical-workflow-continue').click();
    await page.waitForFunction(() => !document.querySelector('[data-testid="drc-workflow-run"]')?.disabled);
    await test('drc-workflow-run').click();
    await page.waitForFunction(() => document.querySelector('[data-testid="stage-drc"]')?.textContent.includes('Running'));
    assert.ok((await test('drc-workflow-lineage').innerText()).includes('Adopted S11 software-qa-layout'));
    await page.route('**/api/drc-workflow', route => route.fulfill({ status: 503, contentType: 'application/json', body: '{"error":"SOFTWARE QA interrupted read"}' }));
    await test('drc-workflow-reconnect').waitFor(); await page.unroute('**/api/drc-workflow'); await test('drc-workflow-reconnect').click();
    await page.waitForFunction(() => !document.querySelector('[data-testid="drc-workflow-refresh"]')?.disabled);
    await context.request.post(url + 'software-qa/transition', { data: { state: 'failed' } });
    await page.waitForFunction(() => document.querySelector('[data-testid="drc-workflow-status"]')?.textContent.includes('Failed'));
    assert.equal(await test('drc-workflow-accept').isDisabled(), true);
    assert.ok((await test('drc-workflow-locations').innerText()).includes('fixture.spacing'));
    assert.ok((await test('drc-workflow-locations').innerText()).includes('box (1,2;3,4)'));
    await test('review-operator').selectOption('development_assistant');
    await test('drc-workflow-feedback').fill('SOFTWARE QA simulated spacing correction');
    await test('drc-workflow-return').click(); await test('physical-workflow-run').waitFor();
    await test('stage-drc').click(); await page.waitForFunction(() => !document.querySelector('[data-testid="drc-workflow-run"]')?.disabled);
    await test('drc-workflow-run').click();
    await page.waitForFunction(() => document.querySelector('[data-testid="drc-workflow-status"]')?.textContent.includes('software-qa-drc-2'));
    await context.request.post(url + 'software-qa/transition', { data: { state: 'awaiting' } });
    await page.waitForFunction(() => document.querySelector('[data-testid="drc-workflow-status"]')?.textContent.includes('Passed'));
    await context.request.post(url + 'software-qa/transition', { data: { state: 'accepted' } });
    await page.waitForFunction(() => document.querySelector('[data-testid="stage-drc"]')?.textContent.includes('Complete'));
    assert.ok((await test('drc-workflow-adoption-provenance').innerText()).includes(original.review_policy.id));
    assert.equal(await test('drc-workflow-continue').isDisabled(), false);
    assert.equal(await test('drc-workflow-continue').innerText(), 'Continue to LVS');
    assert.ok(!(await test('stage-lvs').innerText()).includes('Not implemented'));
    assert.ok((await test('stage-post_layout_verification').innerText()).includes('Not run'));
    const rawIds = ['input-gds', 'config', 'initial-state', 'final-state', 'metrics', 'tool-versions', 'drc-summary', 'klayout-violations', 'magic-report', 'magic-markers', 'klayout-report'];
    for (const id of ['run', 'layout-record', 'source-identity', 'runtime-configuration', 'artifact-manifest', ...rawIds]) {
      const route = id === 'run' ? 'api/drc-workflow/runs/software-qa-drc-2' : 'api/artifacts/drc-workflow/software-qa-drc-2/' + id;
      const expected = await (await context.request.get(url + route)).body(), downloaded = page.waitForEvent('download'); await test('drc-workflow-download-' + id).click();
      const actual = await fs.readFile(await (await downloaded).path()); assert.deepEqual(actual, expected, 'lossless fixture artifact: ' + id);
      if (id === 'source-identity' || id === 'config') assert.ok(actual.toString('utf8').includes('1267650600228229401496703205377'));
    }
    await test('stage-global_settings').click(); await test('project-name').fill('SOFTWARE QA unsaved DRC draft'); await test('stage-drc').click();
    assert.equal(await test('drc-workflow-run').isDisabled(), true);
    const earlier = await page.locator('#stage-tabs .stage-tab').evaluateAll(nodes => nodes.slice(0, 8).map(node => node.textContent));
    await context.request.post(url + 'software-qa/external-source', { data: {} });
    await page.waitForFunction(() => !document.querySelector('[data-testid="drc-workflow-refresh"]')?.disabled); await test('drc-workflow-refresh').click();
    await page.waitForFunction(() => document.querySelector('[data-testid="drc-workflow-status"]')?.textContent.includes('Stale'));
    assert.ok((await test('stage-drc').innerText()).includes('Not run'));
    assert.ok((await test('stage-layout').innerText()).includes('Not run'));
    assert.deepEqual(await page.locator('#stage-tabs .stage-tab').evaluateAll(nodes => nodes.slice(0, 8).map(node => node.textContent)), earlier);
    await test('stage-global_settings').click(); assert.equal(await test('project-name').inputValue(), 'SOFTWARE QA unsaved DRC draft');
    assert.ok((await page.locator('#revision-label').innerText()).includes(original.revision.id));
    assert.equal(await page.evaluate(() => JSON.parse(localStorage.getItem('hullcirq.m1.draft.v1')).base_revision_id), original.revision.id);
    assert.deepEqual(writes, ['/api/drc-workflow/runs', '/api/drc-workflow/runs/software-qa-drc-1/review', '/api/drc-workflow/runs']);
    assert.deepEqual(errors, []);
    console.log(JSON.stringify({ status: 'Passed', software_qa_fixture: true, eda_calls: 0, model_calls: 0, lossless_downloads: 16, failed_rule_locations_visible: true, explicit_feedback_return: true, read_only_reconnect: true, source_and_draft_preserved: true, policy_provenance: true }));
  } finally { await browser.close(); }
})().catch(error => { console.error(error.stack || error); process.exitCode = 1; });
"""


LARGE_RECORD_BROWSER_TEST = r"""
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const { chromium } = require(process.env.HULLCIRQ_PLAYWRIGHT_PATH || 'playwright');
(async () => {
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  try {
    const context = await browser.newContext(), page = await context.newPage(), test = id => page.getByTestId(id), url = process.env.HULLCIRQ_SOFTWARE_QA_URL, writes = [], errors = [];
    page.setDefaultTimeout(20000); page.on('pageerror', error => errors.push(error.message));
    page.on('request', request => { if (request.method() === 'POST' && new URL(request.url()).pathname.startsWith('/api/')) writes.push(new URL(request.url()).pathname); });
    await page.goto(url); await test('stage-drc').click();
    const logs = test('drc-workflow-logs'), segment = test('drc-workflow-logs-segment');
    await logs.evaluate(node => { node.open = true; });
    assert.ok((await test('drc-workflow-logs-range').innerText()).includes('Segment 1 of'));
    assert.ok((await segment.textContent()).includes('SOFTWARE QA FIRST RECORD SEGMENT'));
    assert.ok((await segment.textContent()).length <= 32768);
    await test('drc-workflow-logs-next').click();
    const cursor = await test('drc-workflow-logs-range').innerText(); assert.ok(cursor.includes('Segment 2 of'));
    await test('drc-workflow-refresh').click();
    await page.waitForFunction(() => !document.querySelector('[data-testid="drc-workflow-refresh"]')?.disabled);
    assert.equal(await test('drc-workflow-logs-range').innerText(), cursor, 'read-only refresh must preserve the inspector cursor');
    assert.equal(await logs.evaluate(node => node.open), true, 'refresh must preserve expanded state');
    await test('drc-workflow-logs-last').click();
    assert.ok((await segment.textContent()).includes('SOFTWARE QA LAST RECORD SEGMENT'));
    assert.equal(await test('drc-workflow-logs-next').isDisabled(), true);
    assert.ok((await segment.textContent()).length <= 32768);
    // The whole record is retained in readonly segments; inspect every one.
    await test('drc-workflow-logs-first').click();
    const chunks = [];
    while (true) { chunks.push(await segment.textContent()); if (await test('drc-workflow-logs-next').isDisabled()) break; await test('drc-workflow-logs-next').click(); }
    const original = await (await context.request.get(url + 'api/drc-workflow/runs/software-qa-drc-1')).body();
    const record = JSON.parse(original.toString('utf8'));
    assert.equal(chunks.join(''), JSON.stringify(record.checks, null, 2), 'all segments must reconstruct the complete displayed record without omissions');
    assert.ok(chunks.length > 30);
    await page.screenshot({ fullPage: true, timeout: 20000 });
    const downloaded = page.waitForEvent('download'); await test('drc-workflow-download-run').click();
    assert.deepEqual(await fs.readFile(await (await downloaded).path()), original, 'the full raw backend record must remain lossless');
    assert.deepEqual(writes, []); assert.deepEqual(errors, []);
    console.log(JSON.stringify({ status: 'Passed', software_qa_fixture: true, eda_calls: 0, model_calls: 0, large_record_chars: chunks.join('').length, all_segments_reconstruct_exactly: true, segments: chunks.length, cursor_and_open_state_preserved: true, full_record_download_lossless: true, expanded_screenshot_completed: true }));
  } finally { await browser.close(); }
})().catch(error => { console.error(error.stack || error); process.exitCode = 1; });
"""


class DRCWorkflowGUIRegressionTests(unittest.TestCase):
    def _server(self, directory):
        store = ProjectStore(Path(directory) / "project", PROJECT / "examples/npu_all_nodes_project.json")
        store.set_review_policy("accept_on_pass", True, "SOFTWARE QA only; not circuit proof")
        server = make_server("127.0.0.1", 0, store, PROJECT)
        server.drc_workflow.close(); server.physical_workflow.close(); server.global_workflow.close(); server.global_generation.close()
        server.global_workflow = AcceptedBaselineDouble(store)
        server.global_generation = GlobalGenerationDouble(store.envelope()["revision"]["id"])
        server.physical_workflow = physical = PhysicalDouble(store)
        physical.start("layout", "software-qa-global", "software-qa-s09", "software-qa-s10", store.envelope()["revision"]["id"])
        physical.transition("accepted")
        server.drc_workflow = double = DRCDouble(store, physical)
        server.RequestHandlerClass = DRCControlHandler
        thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": .02}, daemon=True); thread.start()
        return server, thread, double

    def _close(self, server, thread):
        server.shutdown(); server.server_close(); server.workflow.close(); server.generation.close(); thread.join(2)

    def test_drc_failure_locations_feedback_policy_raw_downloads_and_draft_preservation(self):
        executable = shutil.which("node")
        if not executable:
            self.skipTest("Node and Playwright are required for browser software QA.")
        with tempfile.TemporaryDirectory(prefix="hullcirq-drc-gui-software-qa-") as directory:
            server, thread, double = self._server(directory)
            try:
                environment = browser_environment(); environment["HULLCIRQ_SOFTWARE_QA_URL"] = f"http://127.0.0.1:{server.server_address[1]}/"
                result = subprocess.run([executable, "-e", BROWSER_TEST], env=environment, cwd=PROJECT, text=True, encoding="utf-8", capture_output=True, timeout=100)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(len(double.calls), 2)
                self.assertEqual(double.review_calls[0][1:], ("return_to_stage", "SOFTWARE QA simulated spacing correction", "layout"))
                self.assertEqual(json.loads(result.stdout.strip().splitlines()[-1])["lossless_downloads"], 16)
            finally:
                self._close(server, thread)

    def test_readonly_recorder_captures_exact_fixture_reports_without_start_or_review(self):
        executable = shutil.which("node")
        if not executable:
            self.skipTest("Node and Playwright are required for browser software QA.")
        with tempfile.TemporaryDirectory(prefix="hullcirq-drc-recorder-software-qa-") as directory:
            server, thread, double = self._server(directory)
            try:
                double.start("drc", "software-qa-layout", server.store.envelope()["revision"]["id"]); double.transition("accepted")
                environment = browser_environment(); environment.update(HULLCIRQ_NPU_URL=f"http://127.0.0.1:{server.server_address[1]}/", HULLCIRQ_GUI_OUTPUT_ROOT=str(Path(directory) / "recording"), HULLCIRQ_DRC_WAIT_MS="30000")
                result = subprocess.run([executable, str(PROJECT / "scripts/run_drc_workflow_gui.cjs"), "observe-drc"], env=environment, cwd=PROJECT, text=True, encoding="utf-8", capture_output=True, timeout=100)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                reports = list((Path(directory) / "recording").glob("*/gui-operation.json")); self.assertEqual(len(reports), 1)
                report = json.loads(reports[0].read_text(encoding="utf-8"))
                self.assertEqual(report["allowed_mutation_requests"], 0); self.assertEqual(len(report["downloads"]), 16)
                self.assertTrue(all(item["exact_backend_match"] for item in report["downloads"]))
                self.assertEqual(len(double.calls), 1, "Only explicit fixture setup may call start.")
                self.assertEqual(double.review_calls, [])
            finally:
                self._close(server, thread)

    def test_start_recorder_makes_one_explicit_start_and_no_review_or_retry(self):
        executable = shutil.which("node")
        if not executable:
            self.skipTest("Node and Playwright are required for browser software QA.")
        with tempfile.TemporaryDirectory(prefix="hullcirq-drc-start-recorder-software-qa-") as directory:
            server, thread, double = self._server(directory)
            stop = threading.Event()
            def simulate_completion():
                deadline = time.monotonic() + 35
                while not stop.wait(.02) and time.monotonic() < deadline:
                    if double.calls:
                        double.transition("accepted")
                        return
            transition = threading.Thread(target=simulate_completion, daemon=True); transition.start()
            try:
                environment = browser_environment(); environment.update(HULLCIRQ_NPU_URL=f"http://127.0.0.1:{server.server_address[1]}/", HULLCIRQ_GUI_OUTPUT_ROOT=str(Path(directory) / "recording"), HULLCIRQ_DRC_WAIT_MS="30000")
                result = subprocess.run([executable, str(PROJECT / "scripts/run_drc_workflow_gui.cjs"), "drc"], env=environment, cwd=PROJECT, text=True, encoding="utf-8", capture_output=True, timeout=100)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                reports = list((Path(directory) / "recording").glob("*/gui-operation.json")); self.assertEqual(len(reports), 1)
                report = json.loads(reports[0].read_text(encoding="utf-8"))
                self.assertEqual(report["allowed_mutation_requests"], 1); self.assertFalse(report["mutation_retry"])
                self.assertEqual(len(report["requests"]), 1); self.assertEqual(report["requests"][0]["path"], "/api/drc-workflow/runs")
                self.assertEqual(len(double.calls), 1); self.assertEqual(double.review_calls, [])
                metadata = json.loads((reports[0].parent / "start-response-metadata.json").read_text(encoding="utf-8"))
                self.assertEqual(metadata["status"], 202); self.assertFalse(metadata["response_body_captured"])
                self.assertEqual(len(report["downloads"]), 16)
            finally:
                stop.set(); transition.join(1); self._close(server, thread)

    def test_large_record_all_segments_render_and_survive_refresh_with_lossless_download(self):
        executable = shutil.which("node")
        if not executable:
            self.skipTest("Node and Playwright are required for browser software QA.")
        with tempfile.TemporaryDirectory(prefix="hullcirq-large-drc-record-software-qa-") as directory:
            server, thread, double = self._server(directory)
            try:
                double.large_output = True
                double.start("drc", "software-qa-layout", server.store.envelope()["revision"]["id"]); double.transition("accepted")
                environment = browser_environment(); environment["HULLCIRQ_SOFTWARE_QA_URL"] = f"http://127.0.0.1:{server.server_address[1]}/"
                result = subprocess.run([executable, "-e", LARGE_RECORD_BROWSER_TEST], env=environment, cwd=PROJECT, text=True, encoding="utf-8", capture_output=True, timeout=100)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                report = json.loads(result.stdout.strip().splitlines()[-1]); self.assertGreater(report["large_record_chars"], 1024 * 1024)
                self.assertTrue(report["all_segments_reconstruct_exactly"]); self.assertTrue(report["cursor_and_open_state_preserved"])
                self.assertEqual(len(double.calls), 1); self.assertEqual(double.review_calls, [])
            finally:
                self._close(server, thread)


if __name__ == "__main__":
    unittest.main()
