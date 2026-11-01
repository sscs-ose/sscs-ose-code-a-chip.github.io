"""Isolated S13 browser QA. Explicit doubles never execute EDA or a model.

Fixture reports, counts, geometry and GDS bytes test software only; they are not
evidence that any circuit passed LVS. No live project directory is accessed.
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
from test_drc_workflow_gui import DRCDouble


class LVSDouble(InMemorySubmissionDouble):
    """Controllable API state; fake report geometry is explicitly labeled."""
    def __init__(self, store, physical, drc):
        self.store, self.physical, self.drc = store, physical, drc
        self.lock = threading.RLock()
        self.runs, self.reviews, self.calls, self.review_calls = [], [], [], []
        self.cancel_calls = []
        self.ready = True
        self.large_output = False
        self.files = {
            "input-gds": (b"SOFTWARE QA ONLY: not real GDS\x00\xff\r\n", "application/octet-stream"),
            "input-def": (b"SOFTWARE QA ONLY: not real DEF\r\n", "text/plain; charset=utf-8"),
            "input-netlist": (b"// SOFTWARE QA ONLY: no circuit evidence\r\n", "text/plain; charset=utf-8"),
            "input-powered-netlist": (b"// SOFTWARE QA ONLY: no powered circuit evidence\r\n", "text/plain; charset=utf-8"),
            "extracted-spice": (b"* SOFTWARE QA ONLY: not real extracted SPICE\r\n", "text/plain; charset=utf-8"),
            "lvs-report": (b"SOFTWARE QA ONLY: fixture comparison report\r\n", "text/plain; charset=utf-8"),
            "extraction-feedback": (b"SOFTWARE QA ONLY: fixture extraction feedback\r\n", "text/plain; charset=utf-8"),
            "extraction-markers": (b"SOFTWARE QA ONLY: fixture extraction markers\r\n", "text/plain; charset=utf-8"),
            "lvs-script": (b"# SOFTWARE QA ONLY: no commands executed\r\n", "text/plain; charset=utf-8"),
        }
        for field in ("config", "initial-state", "final-state", "metrics", "tool-versions", "lvs-summary", "lvs-json"):
            self.files[field] = (b'{"software_qa_fixture":true,"wide_integer":1267650600228229401496703205377}\r\n', "application/json")
        self._init_submission_memory(runs=self.runs, reviews=self.reviews)

    def envelope(self):
        with self.lock:
            latest = self.runs[-1] if self.runs else None
            return {"lvs_workflow": {"implemented": True, "stage_id": "lvs",
                    "runs": copy.deepcopy(self.runs), "reviews": copy.deepcopy(self.reviews),
                    "latest_run_id": latest["id"] if latest else None,
                    "accepted_run_id": latest["id"] if latest and latest["review_status"] == "Accepted" else None,
                    "ready": self.ready, "blocked_reason": None if self.ready else "SOFTWARE QA changed S11 source",
                    "tool_ready": True, "storage_error": None,
                    "configuration_sha256": "software-qa-lvs-config",
                    "source_inputs": {"powered_netlist": {"sha256": "software-qa-powered-netlist-hash"}},
                    "runtime_configuration": {"software_qa_fixture": True, "tool_processes": 0}}}

    def is_active(self):
        with self.lock:
            return any(run["execution_status"] in ("Queued", "Running") for run in self.runs)

    def start(self, stage, layout, drc, revision, *, _submission=None):
        with self.lock:
            self.calls.append((stage, layout, drc, revision))
            source = self.physical.run(layout)
            run = {"id": "software-qa-lvs-" + str(len(self.runs) + 1), "stage_id": stage,
                              "layout_run_id": layout, "drc_run_id": drc, "revision_id": revision,
                              "drc_snapshot": self.drc.run(drc), "drc_record_sha256": "software-qa-drc-record-hash",
                              "input_netlist_sha256": next(item["sha256"] for item in source["artifacts"] if item["id"] == "netlist"),
                              "input_powered_netlist_sha256": "software-qa-powered-netlist-hash",
                              "layout_record_sha256": "software-qa-layout-record-hash",
                              "input_gds_sha256": next(item["sha256"] for item in source["artifacts"] if item["id"] == "gds"),
                              "configuration_sha256": "software-qa-lvs-config", "layout_snapshot": source,
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
                             "checks": {"source_identity": {"status": "Passed"}, "configuration": {"status": "Passed"}, "extraction": {"status": "Passed", "executed": False}, "lvs": {"status": "Failed" if failed else "Passed", "executed": False}},
                             "metrics": {"software_qa_fixture": True, "netgen__lvs_error__count": 1 if failed else 0},
                             "summary": {"software_qa_fixture": True, "extraction": {"illegal_overlap_count": 0, "feedback_item_count": 3, "non_overlap_feedback_count": 3,
                                "feedback_scope": "SOFTWARE QA ONLY: these extraction warnings are not claimed harmless or resolved.",
                                "feedback": [{"description": "SOFTWARE QA extraction warning " + str(i)} for i in range(3)]},
                                "lvs": {"error_count": 1 if failed else 0, "device_difference_count": 0, "net_difference_count": 1 if failed else 0, "property_fail_count": 0, "unmatched_device_count": 0, "unmatched_net_count": 1 if failed else 0, "unmatched_pin_count": 0, "match_status": "Mismatch" if failed else "Unique match", "comparison_count": 1},
                                "mismatches": [{"kind": "SOFTWARE QA unmatched net", "net": "fixture.unconnected", "detail": "SOFTWARE QA expected connection absent"}] if failed else [],
                                "limits": ["SOFTWARE QA ONLY: no EDA or model was executed"]},
                             "stdout": "SOFTWARE QA ONLY: no EDA or model process was executed", "retained_files": []}
            run["diagnostics"] = ([{"code": "software_qa_lvs_mismatch", "severity": "error", "message": "SOFTWARE QA simulated missing circuit connection"}] if failed else []) + [{"code": "software_qa_extraction_feedback", "severity": "warning", "message": "SOFTWARE QA three extraction warnings remain inspectable; no harmless or resolved claim."}]
            run["artifacts"] = [{"id": field, "kind": "software_fixture", "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw), "content_type": mime, "url": "/api/artifacts/lvs-workflow/" + run["id"] + "/" + field} for field, (raw, mime) in self.files.items()]
            if self.large_output:
                run["checks"]["stdout"] = "SOFTWARE QA FIRST RECORD SEGMENT\n" + ("SOFTWARE QA large diagnostic record line\n" * 32768) + "SOFTWARE QA LAST RECORD SEGMENT"
            if status == "accepted":
                run["review_status"] = "Accepted"
                self.reviews.append({"id": "software-qa-lvs-policy", "run_id": run["id"], "decision": "accepted", "actor": "automation_policy", "provenance": {"policy_id": self.store.review_policy()["id"]}, "note": "SOFTWARE QA simulated policy only"})
            self._persist()

    def run(self, identifier):
        with self.lock:
            return copy.deepcopy(next(run for run in self.runs if run["id"] == identifier))

    def artifact(self, identifier, field):
        run = self.run(identifier)
        return {"layout-record": run["layout_snapshot"], "drc-record": run["drc_snapshot"], "source-identity": run["source_identity"], "runtime-configuration": run["runtime_configuration"], "artifact-manifest": run["artifacts"]}[field]

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

    def cancel(self, identifier):
        with self.lock:
            self.cancel_calls.append(identifier)
            run = next(run for run in self.runs if run["id"] == identifier)
            run.update(execution_status="Cancelled", validation_status="Not Checked", finished_at=utc_now())
            self._persist()

    def close(self):
        pass


class LVSControlHandler(RequestHandler):
    def do_POST(self):
        if self.path == "/software-qa/transition":
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            self.server.lvs_workflow.transition(body["state"])
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
            self.server.lvs_workflow.external_source_changed()
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
    assert.equal(await test('drc-workflow-continue').innerText(), 'Continue to LVS');
    await test('drc-workflow-continue').click();
    await page.waitForFunction(() => !document.querySelector('[data-testid="lvs-workflow-run"]')?.disabled);
    await test('lvs-workflow-run').click();
    await page.waitForFunction(() => document.querySelector('[data-testid="stage-lvs"]')?.textContent.includes('Running'));
    assert.ok((await test('lvs-workflow-lineage').innerText()).includes('Adopted S11 software-qa-layout'));
    await page.route('**/api/lvs-workflow', route => route.fulfill({ status: 503, contentType: 'application/json', body: '{"error":"SOFTWARE QA interrupted read"}' }));
    await test('lvs-workflow-reconnect').waitFor(); await page.unroute('**/api/lvs-workflow'); await test('lvs-workflow-reconnect').click();
    await page.waitForFunction(() => !document.querySelector('[data-testid="lvs-workflow-refresh"]')?.disabled);
    await context.request.post(url + 'software-qa/transition', { data: { state: 'failed' } });
    await page.waitForFunction(() => document.querySelector('[data-testid="lvs-workflow-status"]')?.textContent.includes('Failed'));
    assert.equal(await test('lvs-workflow-accept').isDisabled(), true);
    assert.ok((await test('lvs-workflow-mismatches').innerText()).includes('fixture.unconnected'));
    assert.ok((await test('lvs-workflow-comparison-summary').innerText()).includes('Unmatched nets: 1'));
    assert.ok((await test('lvs-workflow-comparison-summary').innerText()).includes('LVS match status: Mismatch'));
    assert.ok((await test('lvs-workflow-comparison-summary').innerText()).includes('Extraction feedback items: 3'));
    assert.ok((await test('lvs-workflow-comparison-summary').innerText()).includes('Non-overlap extraction feedback: 3'));
    const diagnosticText = (await test('lvs-workflow-diagnostic').allTextContents()).join('\n');
    assert.ok(diagnosticText.includes('software_qa_lvs_mismatch') && diagnosticText.includes('SOFTWARE QA simulated missing circuit connection'));
    assert.ok(diagnosticText.includes('software_qa_extraction_feedback') && diagnosticText.includes('three extraction warnings'));
    assert.ok(!(await test('lvs-workflow-result').innerText()).includes('[object HTMLDivElement]'));
    await test('review-operator').selectOption('development_assistant');
    await test('lvs-workflow-feedback').fill('SOFTWARE QA simulated missing connection correction');
    await test('lvs-workflow-return').click(); await test('physical-workflow-run').waitFor();
    await test('stage-lvs').click(); await page.waitForFunction(() => !document.querySelector('[data-testid="lvs-workflow-run"]')?.disabled);
    await test('lvs-workflow-run').click();
    await page.waitForFunction(() => document.querySelector('[data-testid="lvs-workflow-status"]')?.textContent.includes('software-qa-lvs-2'));
    await context.request.post(url + 'software-qa/transition', { data: { state: 'awaiting' } });
    await page.waitForFunction(() => document.querySelector('[data-testid="lvs-workflow-status"]')?.textContent.includes('Passed'));
    await context.request.post(url + 'software-qa/transition', { data: { state: 'accepted' } });
    await page.waitForFunction(() => document.querySelector('[data-testid="stage-lvs"]')?.textContent.includes('Complete'));
    assert.ok((await test('lvs-workflow-diagnostic').innerText()).includes('three extraction warnings'));
    assert.ok((await test('lvs-workflow-comparison-summary').innerText()).includes('not claimed harmless or resolved'));
    assert.ok((await test('lvs-workflow-adoption-provenance').innerText()).includes(original.review_policy.id));
    assert.equal(await test('lvs-workflow-continue').isDisabled(), false);
    assert.ok((await test('stage-post_layout_verification').innerText()).includes('Not run'));
    const rawIds = ['input-gds', 'input-def', 'input-netlist', 'input-powered-netlist', 'config', 'initial-state', 'final-state', 'metrics', 'tool-versions', 'lvs-summary', 'extracted-spice', 'lvs-report', 'lvs-json', 'extraction-feedback', 'extraction-markers', 'lvs-script'];
    for (const id of ['run', 'layout-record', 'drc-record', 'source-identity', 'runtime-configuration', 'artifact-manifest', ...rawIds]) {
      const route = id === 'run' ? 'api/lvs-workflow/runs/software-qa-lvs-2' : 'api/artifacts/lvs-workflow/software-qa-lvs-2/' + id;
      const expected = await (await context.request.get(url + route)).body(), downloaded = page.waitForEvent('download'); await test('lvs-workflow-download-' + id).click();
      const actual = await fs.readFile(await (await downloaded).path()); assert.deepEqual(actual, expected, 'lossless fixture artifact: ' + id);
      if (id === 'source-identity' || id === 'config') assert.ok(actual.toString('utf8').includes('1267650600228229401496703205377'));
    }
    await test('stage-global_settings').click(); await test('project-name').fill('SOFTWARE QA unsaved LVS draft'); await test('stage-lvs').click();
    assert.equal(await test('lvs-workflow-run').isDisabled(), true);
    const earlier = await page.locator('#stage-tabs .stage-tab').evaluateAll(nodes => nodes.slice(0, 8).map(node => node.textContent));
    await context.request.post(url + 'software-qa/external-source', { data: {} });
    await page.waitForFunction(() => !document.querySelector('[data-testid="lvs-workflow-refresh"]')?.disabled); await test('lvs-workflow-refresh').click();
    await page.waitForFunction(() => document.querySelector('[data-testid="lvs-workflow-status"]')?.textContent.includes('Stale'));
    assert.ok((await test('stage-lvs').innerText()).includes('Not run'));
    assert.ok((await test('stage-layout').innerText()).includes('Not run'));
    assert.deepEqual(await page.locator('#stage-tabs .stage-tab').evaluateAll(nodes => nodes.slice(0, 8).map(node => node.textContent)), earlier);
    await test('stage-global_settings').click(); assert.equal(await test('project-name').inputValue(), 'SOFTWARE QA unsaved LVS draft');
    assert.ok((await page.locator('#revision-label').innerText()).includes(original.revision.id));
    assert.equal(await page.evaluate(() => JSON.parse(localStorage.getItem('hullcirq.m1.draft.v1')).base_revision_id), original.revision.id);
    assert.deepEqual(writes, ['/api/lvs-workflow/runs', '/api/lvs-workflow/runs/software-qa-lvs-1/review', '/api/lvs-workflow/runs']);
    assert.deepEqual(errors, []);
    console.log(JSON.stringify({ status: 'Passed', software_qa_fixture: true, eda_calls: 0, model_calls: 0, lossless_downloads: 22, failed_mismatches_visible: true, diagnostics_and_feedback_counts_visible: true, warnings_remain_visible_after_policy: true, explicit_feedback_return: true, read_only_reconnect: true, source_and_draft_preserved: true, policy_provenance: true }));
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
    await page.goto(url); await test('stage-lvs').click();
    const logs = test('lvs-workflow-logs'), segment = test('lvs-workflow-logs-segment');
    await logs.evaluate(node => { node.open = true; });
    assert.ok((await test('lvs-workflow-logs-range').innerText()).includes('Segment 1 of'));
    assert.ok((await segment.textContent()).includes('SOFTWARE QA FIRST RECORD SEGMENT'));
    assert.ok((await segment.textContent()).length <= 32768);
    await test('lvs-workflow-logs-next').click();
    const cursor = await test('lvs-workflow-logs-range').innerText(); assert.ok(cursor.includes('Segment 2 of'));
    await test('lvs-workflow-refresh').click();
    await page.waitForFunction(() => !document.querySelector('[data-testid="lvs-workflow-refresh"]')?.disabled);
    assert.equal(await test('lvs-workflow-logs-range').innerText(), cursor, 'read-only refresh must preserve the inspector cursor');
    assert.equal(await logs.evaluate(node => node.open), true, 'refresh must preserve expanded state');
    await test('lvs-workflow-logs-last').click();
    assert.ok((await segment.textContent()).includes('SOFTWARE QA LAST RECORD SEGMENT'));
    assert.equal(await test('lvs-workflow-logs-next').isDisabled(), true);
    assert.ok((await segment.textContent()).length <= 32768);
    // The whole record is retained in readonly segments; inspect every one.
    await test('lvs-workflow-logs-first').click();
    const chunks = [];
    while (true) { chunks.push(await segment.textContent()); if (await test('lvs-workflow-logs-next').isDisabled()) break; await test('lvs-workflow-logs-next').click(); }
    const original = await (await context.request.get(url + 'api/lvs-workflow/runs/software-qa-lvs-1')).body();
    const record = JSON.parse(original.toString('utf8'));
    assert.equal(chunks.join(''), JSON.stringify(record.checks, null, 2), 'all segments must reconstruct the complete displayed record without omissions');
    assert.ok(chunks.length > 30);
    await page.screenshot({ fullPage: true, timeout: 20000 });
    const downloaded = page.waitForEvent('download'); await test('lvs-workflow-download-run').click();
    assert.deepEqual(await fs.readFile(await (await downloaded).path()), original, 'the full raw backend record must remain lossless');
    assert.deepEqual(writes, []); assert.deepEqual(errors, []);
    console.log(JSON.stringify({ status: 'Passed', software_qa_fixture: true, eda_calls: 0, model_calls: 0, large_record_chars: chunks.join('').length, all_segments_reconstruct_exactly: true, segments: chunks.length, cursor_and_open_state_preserved: true, full_record_download_lossless: true, expanded_screenshot_completed: true }));
  } finally { await browser.close(); }
})().catch(error => { console.error(error.stack || error); process.exitCode = 1; });
"""


UNCERTAIN_START_BROWSER_TEST = r"""
const assert = require('node:assert/strict');
const { chromium } = require(process.env.HULLCIRQ_PLAYWRIGHT_PATH || 'playwright');
(async () => {
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  try {
    const context = await browser.newContext(), page = await context.newPage(), test = id => page.getByTestId(id), url = process.env.HULLCIRQ_SOFTWARE_QA_URL, writes = [], errors = [];
    page.setDefaultTimeout(20000); page.on('pageerror', error => errors.push(error.message));
    page.on('request', request => { if (request.method() === 'POST' && new URL(request.url()).pathname.startsWith('/api/')) writes.push(new URL(request.url()).pathname); });
    await page.route('**/api/lvs-workflow/runs', async route => {
      if (route.request().method() !== 'POST') { await route.continue(); return; }
      // The server records this one request, but the response is lost. Never resend it.
      await route.fetch(); await route.abort('failed');
    });
    await page.goto(url); await test('stage-lvs').click(); await test('lvs-workflow-run').click();
    await test('execution-submission-refresh').waitFor(); assert.equal(await test('lvs-workflow-run').isDisabled(), true);
    // The durable marker is painted before POST. Wait for the intercepted ACK
    // loss to settle before asserting the unknown-outcome recovery wording.
    await page.waitForFunction(() => document.querySelector('[data-testid="execution-submission-refresh"]')?.disabled === false);
    assert.ok((await test('next-step').innerText()).includes('Retry same request reuses the original identity'));
    await page.unroute('**/api/lvs-workflow/runs'); await test('execution-submission-refresh').click();
    await page.waitForFunction(() => document.querySelector('[data-testid="lvs-workflow-status"]')?.textContent.includes('Running'));
    for (const [stage, control] of [['local_synthesis', 'workflow-run'], ['node_implementation_specs', 'implementation-spec-run'], ['global_rtl_generation', 'global-context-preview'], ['global_synthesis', 'global-workflow-run'], ['layout', 'physical-workflow-run'], ['drc', 'drc-workflow-run']]) {
      await test('stage-' + stage).click(); assert.equal(await test(control).isDisabled(), true, stage + ' must not start while LVS is active');
    }
    await test('stage-local_rtl_generation').click(); assert.ok((await page.locator('#generation-gate').innerText()).includes('LVS tool run is active'));
    await test('stage-lvs').click(); await test('lvs-workflow-cancel').click();
    await page.waitForFunction(() => document.querySelector('[data-testid="lvs-workflow-status"]')?.textContent.includes('Cancelled'));
    assert.equal(await test('lvs-workflow-accept').isDisabled(), true);
    assert.deepEqual(writes, ['/api/lvs-workflow/runs', '/api/lvs-workflow/runs/software-qa-lvs-1/cancel']); assert.deepEqual(errors, []);
    console.log(JSON.stringify({ status: 'Passed', software_qa_fixture: true, eda_calls: 0, model_calls: 0, uncertain_start_not_retried: true, reconnect_is_readonly: true, explicit_cancel: true, shared_busy_gates: true }));
  } finally { await browser.close(); }
})().catch(error => { console.error(error.stack || error); process.exitCode = 1; });
"""


class LVSWorkflowGUIRegressionTests(unittest.TestCase):
    def _server(self, directory):
        store = ProjectStore(Path(directory) / "project", PROJECT / "examples/npu_all_nodes_project.json")
        store.set_review_policy("accept_on_pass", True, "SOFTWARE QA only; not circuit proof")
        server = make_server("127.0.0.1", 0, store, PROJECT)
        server.lvs_workflow.close(); server.drc_workflow.close(); server.physical_workflow.close(); server.global_workflow.close(); server.global_generation.close()
        server.global_workflow = AcceptedBaselineDouble(store)
        server.global_generation = GlobalGenerationDouble(store.envelope()["revision"]["id"])
        server.physical_workflow = physical = PhysicalDouble(store)
        physical.files["netlist"] = (b"// SOFTWARE QA ONLY: mapped-netlist API fixture\r\n", "text/plain; charset=utf-8")
        physical.start("layout", "software-qa-global", "software-qa-s09", "software-qa-s10", store.envelope()["revision"]["id"])
        physical.transition("accepted")
        server.drc_workflow = drc = DRCDouble(store, physical)
        drc.start("drc", "software-qa-layout", store.envelope()["revision"]["id"]); drc.transition("accepted")
        server.lvs_workflow = double = LVSDouble(store, physical, drc)
        server.RequestHandlerClass = LVSControlHandler
        thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": .02}, daemon=True); thread.start()
        return server, thread, double

    def _close(self, server, thread):
        server.shutdown(); server.server_close(); server.workflow.close(); server.generation.close(); thread.join(2)

    def test_lvs_failure_locations_feedback_policy_raw_downloads_and_draft_preservation(self):
        executable = shutil.which("node")
        if not executable:
            self.skipTest("Node and Playwright are required for browser software QA.")
        with tempfile.TemporaryDirectory(prefix="hullcirq-lvs-gui-software-qa-") as directory:
            server, thread, double = self._server(directory)
            try:
                environment = browser_environment(); environment["HULLCIRQ_SOFTWARE_QA_URL"] = f"http://127.0.0.1:{server.server_address[1]}/"
                result = subprocess.run([executable, "-e", BROWSER_TEST], env=environment, cwd=PROJECT, text=True, encoding="utf-8", capture_output=True, timeout=100)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(len(double.calls), 2)
                self.assertEqual(double.review_calls[0][1:], ("return_to_stage", "SOFTWARE QA simulated missing connection correction", "layout"))
                self.assertEqual(json.loads(result.stdout.strip().splitlines()[-1])["lossless_downloads"], 22)
            finally:
                self._close(server, thread)

    def test_readonly_recorder_captures_exact_fixture_reports_without_start_or_review(self):
        executable = shutil.which("node")
        if not executable:
            self.skipTest("Node and Playwright are required for browser software QA.")
        with tempfile.TemporaryDirectory(prefix="hullcirq-lvs-recorder-software-qa-") as directory:
            server, thread, double = self._server(directory)
            try:
                double.start("lvs", "software-qa-layout", "software-qa-drc-1", server.store.envelope()["revision"]["id"]); double.transition("accepted")
                environment = browser_environment(); environment.update(HULLCIRQ_NPU_URL=f"http://127.0.0.1:{server.server_address[1]}/", HULLCIRQ_GUI_OUTPUT_ROOT=str(Path(directory) / "recording"), HULLCIRQ_LVS_WAIT_MS="30000")
                result = subprocess.run([executable, str(PROJECT / "scripts/run_lvs_workflow_gui.cjs"), "observe-lvs"], env=environment, cwd=PROJECT, text=True, encoding="utf-8", capture_output=True, timeout=100)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                reports = list((Path(directory) / "recording").glob("*/gui-operation.json")); self.assertEqual(len(reports), 1)
                report = json.loads(reports[0].read_text(encoding="utf-8"))
                self.assertEqual(report["allowed_mutation_requests"], 0); self.assertEqual(len(report["downloads"]), 22)
                self.assertTrue(all(item["exact_backend_match"] for item in report["downloads"]))
                self.assertEqual(len(double.calls), 1, "Only explicit fixture setup may call start.")
                self.assertEqual(double.review_calls, [])
            finally:
                self._close(server, thread)

    def test_start_recorder_makes_one_explicit_start_and_no_review_or_retry(self):
        executable = shutil.which("node")
        if not executable:
            self.skipTest("Node and Playwright are required for browser software QA.")
        with tempfile.TemporaryDirectory(prefix="hullcirq-lvs-start-recorder-software-qa-") as directory:
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
                environment = browser_environment(); environment.update(HULLCIRQ_NPU_URL=f"http://127.0.0.1:{server.server_address[1]}/", HULLCIRQ_GUI_OUTPUT_ROOT=str(Path(directory) / "recording"), HULLCIRQ_LVS_WAIT_MS="30000")
                result = subprocess.run([executable, str(PROJECT / "scripts/run_lvs_workflow_gui.cjs"), "lvs"], env=environment, cwd=PROJECT, text=True, encoding="utf-8", capture_output=True, timeout=100)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                reports = list((Path(directory) / "recording").glob("*/gui-operation.json")); self.assertEqual(len(reports), 1)
                report = json.loads(reports[0].read_text(encoding="utf-8"))
                self.assertEqual(report["allowed_mutation_requests"], 1); self.assertFalse(report["mutation_retry"])
                self.assertEqual(len(report["requests"]), 1); self.assertEqual(report["requests"][0]["path"], "/api/lvs-workflow/runs")
                self.assertEqual(len(double.calls), 1); self.assertEqual(double.review_calls, [])
                metadata = json.loads((reports[0].parent / "start-response-metadata.json").read_text(encoding="utf-8"))
                self.assertEqual(metadata["status"], 202); self.assertFalse(metadata["response_body_captured"])
                self.assertEqual(len(report["downloads"]), 22)
            finally:
                stop.set(); transition.join(1); self._close(server, thread)

    def test_large_record_all_segments_render_and_survive_refresh_with_lossless_download(self):
        executable = shutil.which("node")
        if not executable:
            self.skipTest("Node and Playwright are required for browser software QA.")
        with tempfile.TemporaryDirectory(prefix="hullcirq-large-lvs-record-software-qa-") as directory:
            server, thread, double = self._server(directory)
            try:
                double.large_output = True
                double.start("lvs", "software-qa-layout", "software-qa-drc-1", server.store.envelope()["revision"]["id"]); double.transition("accepted")
                environment = browser_environment(); environment["HULLCIRQ_SOFTWARE_QA_URL"] = f"http://127.0.0.1:{server.server_address[1]}/"
                result = subprocess.run([executable, "-e", LARGE_RECORD_BROWSER_TEST], env=environment, cwd=PROJECT, text=True, encoding="utf-8", capture_output=True, timeout=100)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                report = json.loads(result.stdout.strip().splitlines()[-1]); self.assertGreater(report["large_record_chars"], 1024 * 1024)
                self.assertTrue(report["all_segments_reconstruct_exactly"]); self.assertTrue(report["cursor_and_open_state_preserved"])
                self.assertEqual(len(double.calls), 1); self.assertEqual(double.review_calls, [])
            finally:
                self._close(server, thread)

    def test_uncertain_start_readonly_reconnect_explicit_cancel_and_shared_busy_gates(self):
        executable = shutil.which("node")
        if not executable:
            self.skipTest("Node and Playwright are required for browser software QA.")
        with tempfile.TemporaryDirectory(prefix="hullcirq-lvs-uncertain-start-software-qa-") as directory:
            server, thread, double = self._server(directory)
            try:
                environment = browser_environment(); environment["HULLCIRQ_SOFTWARE_QA_URL"] = f"http://127.0.0.1:{server.server_address[1]}/"
                result = subprocess.run([executable, "-e", UNCERTAIN_START_BROWSER_TEST], env=environment, cwd=PROJECT, text=True, encoding="utf-8", capture_output=True, timeout=100)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(len(double.calls), 1); self.assertEqual(double.cancel_calls, ["software-qa-lvs-1"])
                self.assertEqual(double.review_calls, [])
            finally:
                self._close(server, thread)


if __name__ == "__main__":
    unittest.main()
