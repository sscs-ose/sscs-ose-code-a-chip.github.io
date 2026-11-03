"""Isolated S11 browser software QA; doubles and bytes are not circuit proof.

Exercises real production GUI/HTTP integration without EDA, models, a live
project or a real GDS. The one-pixel PNG is a declared software preview fixture.
"""
from __future__ import annotations

import base64
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
import unittest
from browser_qa_runtime import browser_environment

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))
sys.path.insert(0, str(PROJECT / "tests"))
from hullcirq.server import RequestHandler, make_server
from hullcirq.store import ProjectStore, utc_now
from test_global_workflow_gui import ControlledWorkflowDouble, GlobalGenerationDouble, InMemorySubmissionDouble


class AcceptedBaselineDouble(ControlledWorkflowDouble):
    """Accepted S09/S10 fixture labels only; no synthesis or simulation."""
    def __init__(self, store):
        super().__init__(store)
        for stage, identifier in (("global_synthesis", "software-qa-s09"),
                                  ("global_netlist_simulation", "software-qa-s10")):
            self.runs.append({"id": identifier, "stage_id": stage,
                              "revision_id": store.envelope()["revision"]["id"],
                              "global_job_id": "software-qa-global", "prior_run_id": "software-qa-s09",
                              "execution_status": "Completed", "validation_status": "Passed",
                              "review_status": "Accepted", "freshness": "Current",
                              "checks": {}, "diagnostics": [], "software_qa_fixture": True})
        self._persist()


class PhysicalDouble(InMemorySubmissionDouble):
    """Controllable physical API; never creates a model/tool process."""
    def __init__(self, store):
        self.store = store
        self.lock = threading.RLock()
        self.runs, self.reviews, self.calls, self.revalidations = [], [], [], []
        self.ready = True
        self.files = {
            "png": (base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jh1kAAAAASUVORK5CYII="), "image/png"),
            "gds": (b"SOFTWARE QA ONLY: not a real GDS\x00\xff\r\n", "application/octet-stream"),
            "def": (b"# SOFTWARE QA ONLY; not actual routed DEF\r\nEND DESIGN\r\n", "text/plain; charset=utf-8"),
            "config": (b'{"software_qa_fixture":true,"wide_integer":1267650600228229401496703205377}\r\n', "application/json"),
        }
        self._init_submission_memory(runs=self.runs, reviews=self.reviews)

    def envelope(self):
        with self.lock:
            latest = self.runs[-1] if self.runs else None
            return {"physical_workflow": {"implemented": True, "stage_id": "layout",
                    "runs": copy.deepcopy(self.runs), "reviews": copy.deepcopy(self.reviews),
                    "latest_run_id": latest["id"] if latest else None,
                    "accepted_run_id": latest["id"] if latest and latest["review_status"] == "Accepted" else None,
                    "ready": self.ready, "blocked_reason": None if self.ready else "SOFTWARE QA changed source",
                    "tool_ready": True, "tool_blocked_reason": None, "storage_error": None,
                    "settings_projection": copy.deepcopy(self.store.envelope()["design"]["settings"]),
                    "runtime_configuration_sha256": "software-qa-runtime-hash",
                    "runtime_configuration": {"software_qa_fixture": True, "utilization": 35}}}

    def is_active(self):
        with self.lock:
            return any(run["execution_status"] in ("Queued", "Running") for run in self.runs)

    def start(self, stage, job, synthesis, netlist, revision, *, _submission=None):
        with self.lock:
            self.calls.append((stage, job, synthesis, netlist, revision))
            run = {"id": "software-qa-layout", "stage_id": stage,
                              "global_job_id": job, "synthesis_run_id": synthesis,
                              "netlist_run_id": netlist, "revision_id": revision,
                              "execution_status": "Running", "validation_status": "Not Checked",
                              "review_status": "Awaiting Review", "freshness": "Current",
                              "created_at": utc_now(), "finished_at": None,
                              "checks": {}, "diagnostics": [], "artifacts": [],
                              "source_manifest": {"software_qa_fixture": True},
                              "verification_plan": {"software_qa_fixture": True, "wide_integer": 2**100 + 1},
                              "settings": copy.deepcopy(self.store.envelope()["design"]["settings"]),
                              "runtime_configuration": {"software_qa_fixture": True, "utilization": 35},
                              "evidence_kind": "trusted_fixed_tool_execution",
                              "software_qa_fixture": True}
            if _submission is not None:
                run["submission_id"] = _submission.submission_id
                _submission.bind(run["id"])
            self.runs.append(run)
            self._persist()

    def revalidate(self, identifier):
        """Simulate the API metadata only: no trusted physical proof is made."""
        with self.lock:
            original = self.run(identifier)
            self.revalidations.append(identifier)
            run = copy.deepcopy(original)
            # Revalidation is a distinct, explicitly unkeyed software action;
            # it cannot inherit the original execution's logical nonce.
            run.pop("submission_id", None)
            run.update(id="software-qa-layout-revalidation", prior_run_id=identifier,
                       execution_kind="saved_outputs_no_new_tool_start",
                       evidence_kind="trusted_saved_tool_revalidation",
                       previous_result_sha256="software-qa-original-result-hash",
                       prior_record_sha256="software-qa-original-record-hash",
                       execution_status="Running", validation_status="Not Checked",
                       review_status="Awaiting Review", finished_at=None, error=None)
            run["checks"].update(execution_reused=True, revalidated_from_run_id=identifier,
                                previous_result_sha256=run["previous_result_sha256"],
                                revalidation_tool_starts=0, revalidation_model_calls=0)
            self.runs.append(run)
            self._persist()

    def transition(self, status):
        with self.lock:
            run = self.runs[-1]
            if status == "failed":
                # Declared metadata fixture for a parser failure after exit 0;
                # no EDA was actually started by this isolated test double.
                run.update(execution_status="Failed", validation_status="Not Checked", finished_at=utc_now(),
                           error={"code": "software_qa_parser_failure", "message": "SOFTWARE QA simulated saved-output parser failure"})
                run["checks"] = {"executed": True, "exit_code": 0, "software_qa_fixture": True,
                                 "stdout": "SOFTWARE QA: simulated command metadata; no process executed"}
                self._persist()
                return
            run.update(execution_status="Completed", validation_status="Passed", finished_at=utc_now())
            run["checks"] = {**run["checks"], "executed": False, "software_qa_fixture": True,
                             "implementation_kind": "resumed_post_GRT_route_repair",
                             "checks": {"software_fixture_only": "Passed"},
                             "metrics": {"software_qa_fixture": True, "fixture_count": 1},
                             "stdout": "SOFTWARE QA: no EDA or model executed"}
            run["diagnostics"] = [{"severity": "warning", "code": "software_qa_visible_diagnostic",
                                   "message": "SOFTWARE QA diagnostic must render as an element"}]
            run["artifacts"] = [{"id": identifier, "kind": "software_fixture", "bytes": len(payload),
                                 "sha256": hashlib.sha256(payload).hexdigest(), "content_type": mime,
                                 "url": "/api/artifacts/physical-workflow/" + run["id"] + "/" + identifier}
                                for identifier, (payload, mime) in self.files.items()]
            if status == "accepted":
                run["review_status"] = "Accepted"
                self.reviews.append({"id": "software-qa-physical-policy", "run_id": run["id"],
                                     "decision": "accepted", "actor": "automation_policy",
                                     "provenance": {"policy_id": self.store.review_policy()["id"]},
                                     "note": "SOFTWARE QA controlled policy transition; not circuit proof"})
            elif status != "awaiting":
                raise ValueError("Unknown software-only transition")
            self._persist()

    def run(self, identifier):
        with self.lock:
            return copy.deepcopy(next(run for run in self.runs if run["id"] == identifier))

    def artifact(self, identifier, field):
        run = self.run(identifier)
        if field == "artifact-manifest":
            return run["artifacts"]
        if field in ("source-manifest", "verification-plan", "settings", "runtime-configuration"):
            return run[field.replace("-", "_")]
        return self.files[field][0].decode("utf-8")

    def artifact_bytes(self, identifier, field):
        self.run(identifier)
        return self.files[field]

    def external_source_changed(self):
        with self.lock:
            self.ready = False
            for run in self.runs:
                run.update(freshness="Stale", review_status="Awaiting Review")
            self._persist()

    def close(self):
        pass


class PhysicalControlHandler(RequestHandler):
    def do_POST(self):
        if self.path == "/software-qa/transition":
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            self.server.physical_workflow.transition(body["state"])
            self._json({"software_qa_fixture": True})
            return
        if self.path == "/software-qa/external-source":
            self.rfile.read(int(self.headers["Content-Length"]))
            current = self.server.store.envelope()
            changed = copy.deepcopy(current["design"])
            changed["project"]["name"] = "SOFTWARE QA external source"
            self.server.store.save(changed, current["revision"]["id"])
            self.server.global_workflow.external_source_changed()
            self.server.physical_workflow.external_source_changed()
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
    const context = await browser.newContext(), page = await context.newPage();
    page.setDefaultTimeout(20000);
    const errors = [], writes = [], test = id => page.getByTestId(id);
    page.on('pageerror', error => errors.push(error.message));
    page.on('request', request => { if (request.method() === 'POST' && new URL(request.url()).pathname.startsWith('/api/')) writes.push(new URL(request.url()).pathname); });
    const url = process.env.HULLCIRQ_SOFTWARE_QA_URL;
    const original = await (await context.request.get(url + 'api/project')).json();
    await page.goto(url); await test('stage-global_netlist_simulation').click();
    assert.equal(await test('global-workflow-continue').innerText(), 'Continue to Layout');
    await test('global-workflow-continue').click();
    await test('physical-workflow-run').waitFor();
    assert.equal(await test('physical-workflow-run').isEnabled(), true, await test('physical-workflow-run').getAttribute('title'));
    await test('physical-workflow-run').click();
    await page.waitForFunction(() => document.querySelector('[data-testid="stage-layout"]')?.textContent.includes('Running'));
    assert.ok((await test('physical-workflow-status').innerText()).includes('Running'));

    // A lost polling response must offer read-only reconnect, never replay start.
    await page.route('**/api/physical-workflow', route => route.fulfill({ status: 503, contentType: 'application/json', body: '{"error":"SOFTWARE QA interrupted read"}' }));
    await test('physical-workflow-reconnect').waitFor();
    await page.unroute('**/api/physical-workflow');
    await test('physical-workflow-reconnect').click();
    await page.waitForFunction(() => !document.querySelector('[data-testid="physical-workflow-refresh"]')?.disabled);
    await test('stage-global_settings').click();
    await test('project-name').fill('SOFTWARE QA physical unsaved draft');
    await test('stage-layout').click();
    const awaitingRead = page.waitForResponse(response => response.url().endsWith('/api/project') && response.request().method() === 'GET');
    await context.request.post(url + 'software-qa/transition', { data: { state: 'awaiting' } });
    await awaitingRead;
    await page.waitForFunction(() => !document.querySelector('[data-testid="physical-workflow-refresh"]')?.disabled);
    await page.waitForFunction(() => {
      const text = document.querySelector('[data-testid="physical-workflow-status"]')?.textContent || '';
      return text.includes('Completed') && text.includes('Passed') && text.includes('Awaiting Review');
    });
    await context.request.post(url + 'software-qa/transition', { data: { state: 'accepted' } });
    await page.waitForFunction(() => document.querySelector('[data-testid="physical-workflow-status"]')?.textContent.includes('Accepted'));
    assert.ok((await test('stage-layout').innerText()).includes('Not run'), 'unsaved source must not look complete');
    assert.ok((await test('physical-workflow-adoption-provenance').innerText()).includes(original.review_policy.id));
    assert.ok((await test('physical-workflow-implementation').innerText()).includes('post-global-route checkpoint'));
    assert.ok((await test('physical-workflow-scope').innerText()).includes('Earlier technology mapping, placement and CTS are reused'));
    assert.equal(await test('physical-workflow-result').locator('.diagnostic').count(), 1);
    assert.ok((await test('physical-workflow-result').innerText()).includes('software_qa_visible_diagnostic'));
    assert.ok(!(await test('physical-workflow-result').innerText()).includes('[object HTMLDivElement]'));
    assert.ok((await test('physical-workflow-lineage').innerText()).includes('S10 software-qa-s10'));
    assert.equal(await test('physical-workflow-continue').isDisabled(), true);
    assert.ok((await test('stage-drc').innerText()).includes('Not run'));
    assert.ok(!(await test('stage-lvs').innerText()).includes('Not implemented'));
    assert.ok((await test('stage-post_layout_verification').innerText()).includes('Not run'));

    await page.waitForFunction(() => { const image = document.querySelector('[data-testid="physical-workflow-layout-image"]'); return image?.complete && image.naturalWidth === 1; });
    await test('physical-workflow-zoom').focus(); await test('physical-workflow-zoom').press('Home');
    for (let i = 0; i < 7; i++) await test('physical-workflow-zoom').press('ArrowRight');
    assert.equal(await test('physical-workflow-zoom').inputValue(), '200');
    assert.equal(await test('physical-workflow-layout-image').evaluate(image => image.style.width), '200%');
    await test('physical-workflow-fit').click();
    assert.equal(await test('physical-workflow-zoom').inputValue(), '100');
    for (const id of ['run', 'verification-plan', 'config', 'def', 'gds', 'png']) {
      const route = id === 'run' ? 'api/physical-workflow/runs/software-qa-layout' : 'api/artifacts/physical-workflow/software-qa-layout/' + id;
      const response = await context.request.get(url + route);
      const expected = id === 'config' ? Buffer.from(await response.json(), 'utf8') : await response.body();
      const downloaded = page.waitForEvent('download');
      await test('physical-workflow-download-' + id).click();
      const actual = await fs.readFile(await (await downloaded).path());
      assert.deepEqual(actual, expected, 'lossless software fixture download: ' + id);
      if (id === 'run' || id === 'verification-plan') assert.ok(actual.toString('utf8').includes('1267650600228229401496703205377'));
    }
    assert.ok((await page.locator('#save-state').innerText()).includes('Unsaved design inputs'));
    const earlierRows = await page.locator('#stage-tabs .stage-tab').evaluateAll(nodes => nodes.slice(0, 8).map(node => node.textContent));
    await context.request.post(url + 'software-qa/external-source', { data: {} });
    await page.waitForFunction(() => !document.querySelector('[data-testid="physical-workflow-refresh"]')?.disabled);
    await test('physical-workflow-refresh').click();
    await page.waitForFunction(() => document.querySelector('[data-testid="physical-workflow-status"]')?.textContent.includes('Stale'));
    assert.ok((await test('stage-layout').innerText()).includes('Not run'));
    assert.ok((await test('physical-workflow-status').innerText()).includes('Stale'));
    assert.ok((await test('stage-global_synthesis').innerText()).includes('Not run'));
    assert.deepEqual(await page.locator('#stage-tabs .stage-tab').evaluateAll(nodes => nodes.slice(0, 8).map(node => node.textContent)), earlierRows);
    await test('stage-global_settings').click();
    assert.equal(await test('project-name').inputValue(), 'SOFTWARE QA physical unsaved draft');
    assert.ok((await page.locator('#revision-label').innerText()).includes(original.revision.id));
    assert.equal(await page.evaluate(() => JSON.parse(localStorage.getItem('hullcirq.m1.draft.v1')).base_revision_id), original.revision.id);
    assert.deepEqual(writes, ['/api/physical-workflow/runs']);
    assert.deepEqual(errors, []);
    console.log(JSON.stringify({ status: 'Passed', software_qa_fixture: true, eda_calls: 0, model_calls: 0,
      start_requests: writes.length, adoption_refresh: true, draft_and_save_base_preserved: true,
      lossless_downloads: true, preview_zoom: true, separate_unimplemented_signoff: true }));
  } finally { await browser.close(); }
})().catch(error => { console.error(error.stack || error); process.exitCode = 1; });
"""


BROWSER_REVALIDATION_TEST = r"""
const assert = require('node:assert/strict');
const { chromium } = require(process.env.HULLCIRQ_PLAYWRIGHT_PATH || 'playwright');
(async () => {
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  try {
    const context = await browser.newContext(), page = await context.newPage();
    page.setDefaultTimeout(20000);
    const test = id => page.getByTestId(id), writes = [], errors = [], url = process.env.HULLCIRQ_SOFTWARE_QA_URL;
    page.on('pageerror', error => errors.push(error.message));
    page.on('request', request => { if (request.method() === 'POST' && new URL(request.url()).pathname.startsWith('/api/')) writes.push(new URL(request.url()).pathname); });
    const originalProject = await (await context.request.get(url + 'api/project')).json();
    const originalRun = await (await context.request.get(url + 'api/physical-workflow/runs/software-qa-layout')).body();
    await page.goto(url); await test('stage-layout').click();
    await test('physical-workflow-revalidate').waitFor();
    assert.equal(await test('physical-workflow-revalidate').innerText(), 'Recheck saved outputs (no EDA rerun)');
    assert.equal(await test('physical-workflow-revalidate').isEnabled(), true, await test('physical-workflow-revalidate').getAttribute('title'));
    await test('stage-global_settings').click(); await test('project-name').fill('SOFTWARE QA unsaved recheck input');
    await test('stage-layout').click();
    assert.equal(await test('physical-workflow-revalidate').isDisabled(), true, 'draft inputs must block saved-output recheck');
    await test('stage-global_settings').click(); await test('project-name').fill(originalProject.design.project.name);
    await test('stage-layout').click();
    await page.waitForFunction(() => { const button = document.querySelector('[data-testid="physical-workflow-revalidate"]'); return button && !button.disabled; });
    await test('physical-workflow-revalidate').click();
    await page.waitForFunction(() => document.querySelector('[data-testid="physical-workflow-status"]')?.textContent.includes('software-qa-layout-revalidation'));
    assert.ok((await test('physical-workflow-result').innerText()).includes('Checking saved physical outputs; EDA tools are not rerun'));
    assert.ok((await test('physical-workflow-revalidation-provenance').innerText()).includes('software-qa-layout'));
    await context.request.post(url + 'software-qa/transition', { data: { state: 'awaiting' } });
    await page.waitForFunction(() => document.querySelector('[data-testid="physical-workflow-status"]')?.textContent.includes('Passed'));
    await context.request.post(url + 'software-qa/transition', { data: { state: 'accepted' } });
    await page.waitForFunction(() => document.querySelector('[data-testid="stage-layout"]')?.textContent.includes('Complete'));
    assert.ok((await test('physical-workflow-adoption-provenance').innerText()).includes(originalProject.review_policy.id));
    const latest = await (await context.request.get(url + 'api/physical-workflow/runs/software-qa-layout-revalidation')).json();
    assert.equal(latest.execution_kind, 'saved_outputs_no_new_tool_start');
    assert.equal(latest.prior_run_id, 'software-qa-layout');
    assert.equal(latest.checks.revalidation_tool_starts, 0); assert.equal(latest.checks.revalidation_model_calls, 0);
    assert.deepEqual(await (await context.request.get(url + 'api/physical-workflow/runs/software-qa-layout')).body(), originalRun, 'the original failure must be preserved byte-for-byte');
    await test('physical-workflow-run-software-qa-layout').click();
    assert.equal(await test('physical-workflow-revalidate').isDisabled(), true, 'superseded failures cannot be rechecked');
    assert.ok((await test('physical-workflow-result').innerText()).includes('software_qa_parser_failure'));
    await test('physical-workflow-run-software-qa-layout-revalidation').click();
    assert.equal(await test('physical-workflow-revalidate').count(), 0, 'a passed revalidation must not offer another recheck');
    assert.ok((await test('physical-workflow-lineage').innerText()).includes('S10 software-qa-s10'));
    assert.deepEqual(writes, ['/api/physical-workflow/runs/software-qa-layout/revalidate']);
    assert.deepEqual(errors, []);
    console.log(JSON.stringify({ status: 'Passed', software_qa_fixture: true, eda_calls: 0, model_calls: 0,
      saved_output_recheck_requests: 1, original_failure_preserved: true, dirty_and_superseded_gates: true, policy_refresh: true }));
  } finally { await browser.close(); }
})().catch(error => { console.error(error.stack || error); process.exitCode = 1; });
"""


class PhysicalWorkflowGUIRegressionTests(unittest.TestCase):
    def test_physical_polling_reconnect_preview_downloads_and_source_preservation(self):
        executable = shutil.which("node")
        if not executable:
            self.skipTest("Node and Playwright are required for browser software QA.")
        with tempfile.TemporaryDirectory(prefix="hullcirq-physical-gui-software-qa-") as directory:
            store = ProjectStore(Path(directory) / "project", PROJECT / "examples/npu_all_nodes_project.json")
            store.set_review_policy("accept_on_pass", True, "SOFTWARE QA only; not circuit proof")
            original_revision = store.envelope()["revision"]["id"]
            server = make_server("127.0.0.1", 0, store, PROJECT)
            server.physical_workflow.close(); server.global_workflow.close(); server.global_generation.close()
            server.global_workflow = AcceptedBaselineDouble(store)
            server.global_generation = GlobalGenerationDouble(store.envelope()["revision"]["id"])
            server.physical_workflow = double = PhysicalDouble(store)
            server.RequestHandlerClass = PhysicalControlHandler
            thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": .02}, daemon=True)
            thread.start()
            try:
                environment = browser_environment()
                environment["HULLCIRQ_SOFTWARE_QA_URL"] = f"http://127.0.0.1:{server.server_address[1]}/"
                result = subprocess.run([executable, "-e", BROWSER_TEST], env=environment, cwd=PROJECT,
                                        text=True, encoding="utf-8", capture_output=True, timeout=80)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(double.calls, [("layout", "software-qa-global", "software-qa-s09", "software-qa-s10", original_revision)])
                self.assertTrue(json.loads(result.stdout.strip().splitlines()[-1])["lossless_downloads"])
            finally:
                server.shutdown(); server.server_close(); server.workflow.close(); server.generation.close()
                thread.join(2)

    def test_saved_output_recheck_has_one_request_no_tool_start_and_preserved_failure(self):
        executable = shutil.which("node")
        if not executable:
            self.skipTest("Node and Playwright are required for browser software QA.")
        with tempfile.TemporaryDirectory(prefix="hullcirq-physical-recheck-software-qa-") as directory:
            store = ProjectStore(Path(directory) / "project", PROJECT / "examples/npu_all_nodes_project.json")
            store.set_review_policy("accept_on_pass", True, "SOFTWARE QA only; not circuit proof")
            server = make_server("127.0.0.1", 0, store, PROJECT)
            server.physical_workflow.close(); server.global_workflow.close(); server.global_generation.close()
            server.global_workflow = AcceptedBaselineDouble(store)
            server.global_generation = GlobalGenerationDouble(store.envelope()["revision"]["id"])
            server.physical_workflow = double = PhysicalDouble(store)
            double.start("layout", "software-qa-global", "software-qa-s09", "software-qa-s10", store.envelope()["revision"]["id"])
            double.transition("failed")
            server.RequestHandlerClass = PhysicalControlHandler
            thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": .02}, daemon=True)
            thread.start()
            try:
                environment = browser_environment()
                environment["HULLCIRQ_SOFTWARE_QA_URL"] = f"http://127.0.0.1:{server.server_address[1]}/"
                result = subprocess.run([executable, "-e", BROWSER_REVALIDATION_TEST], env=environment, cwd=PROJECT,
                                        text=True, encoding="utf-8", capture_output=True, timeout=80)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(len(double.calls), 1, "Only the explicit initial fixture setup may call start.")
                self.assertEqual(double.revalidations, ["software-qa-layout"])
                self.assertTrue(json.loads(result.stdout.strip().splitlines()[-1])["original_failure_preserved"])
            finally:
                server.shutdown(); server.server_close(); server.workflow.close(); server.generation.close()
                thread.join(2)


REPAIR_CLIENT = r"""
// Declared isolated DOM/API fixtures: none of these statuses are EDA evidence.
const fs=require('fs'), vm=require('vm'), assert=require('assert/strict');
const source=fs.readFileSync('src/gui/physical_workflow.js','utf8')
  .replace(/^import[^\n]*\n/gm,'').replace('export class PhysicalWorkflow','class PhysicalWorkflow');
class DOMDouble {
  constructor(tag='div',attrs={}) { this.tag=tag; Object.assign(this,attrs); this.children=[]; this.isConnected=true; }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children=[]; this.append(...children); }
  querySelector(selector) {
    const id=selector.match(/^\[data-testid="([^"]+)"\]$/)?.[1];
    return descend(this).find(node=>node && typeof node==='object' && (id ? node['data-testid']===id : selector[0]==='#' && node.id===selector.slice(1))) || null;
  }
  setAttribute(key,value) { this[key]=value; }
  focus() { document.activeElement=this; }
  setSelectionRange(start,end) { this.selectionStart=start; this.selectionEnd=end; }
  click() { return this.disabled ? undefined : this.onclick?.(); }
}
const descend=host=>host.children.flatMap(child=>child && typeof child==='object' ? [child,...descend(child)] : [child]);
const text=host=>[host.text,host.textContent,...descend(host).map(node=>typeof node==='string' ? node : node.text ?? node.textContent ?? '')].filter(Boolean).join('\n');
const el=(tag,attrs={},...children)=>{ const node=new DOMDouble(tag,attrs); node.append(...children.flat(Infinity).filter(x=>x!=null && x!==false)); return node; };
const document={activeElement:null},requests=[],toasts=[],notices=[],navigations=[];
const sandbox={el,document,badge:text=>el('span',{text}),field:(label,value,change,attrs)=>el('select',{value,...attrs,onchange:change}),
  downloadJsonResponse(){},sessionFetch(){throw new Error('Unexpected fetch in isolated client');},console,setTimeout:()=>1,clearTimeout(){}};
vm.createContext(sandbox); vm.runInContext(source+'\nglobalThis.PhysicalWorkflow=PhysicalWorkflow;',sandbox);
const normalized=value=>JSON.parse(JSON.stringify(value));
const accepted=(id,extra={})=>({id,revision_id:'software-qa-revision',execution_status:'Completed',validation_status:'Passed',review_status:'Accepted',freshness:'Current',...extra});
const job=accepted('software-qa-global'),synthesis=accepted('software-qa-s09',{global_job_id:job.id}),netlist=accepted('software-qa-s10',{global_job_id:job.id,synthesis_run_id:synthesis.id});
let project={stage:'layout',dirty:false,conflict:null,busy:false,readOnly:false,envelope:{revision:{id:'software-qa-revision'},workflow:[{id:'layout',implemented:true}],
  global_generation:{ready:true,jobs:[job],latest_job_id:job.id},global_workflow:{runs:[synthesis,netlist],stages:[{stage_id:'global_synthesis',accepted_run_id:synthesis.id},{stage_id:'global_netlist_simulation',accepted_run_id:netlist.id}]},
  physical_repair_session:{configured:true,profile_version:'hullcirq-sky130-route-repair-npu2v1'}}};
let responder=async()=>project.envelope;
const flow=new sandbox.PhysicalWorkflow({project:()=>project,request:async(route,body)=>{requests.push({route,body}); return responder(route,body);},
  envelope:envelope=>{project.envelope=envelope;flow.receive(envelope);},workflow:value=>flow.receive({...project.envelope,physical_workflow:value}),
  notify:(...args)=>notices.push(args),toast:value=>toasts.push(value),navigate:stage=>navigations.push(stage),chrome(){}});
const failure=()=>({id:'software-qa-failed-layout',revision_id:'software-qa-revision',execution_status:'Completed',validation_status:'Failed',freshness:'Current',review_status:'Awaiting Review',error:null,
  evidence_kind:'trusted_fixed_tool_execution',runtime_configuration:{profile:{profile_version:'hullcirq-sky130-route-repair-npu2v1'}},
  diagnostics:[{code:'physical_checks_failed',severity:'error',message:'SOFTWARE QA only: electrical violations'}],artifacts:[],
  checks:{origin:'trusted_fixed_tool_adapter',validation_status:'Failed',executed:true,exit_code:0,cleanup_unresolved:false,technology_mapping_executed:false,upstream_technology_mapping_reused:true,
    implementation_kind:'resumed_pre_CTS_route_repair',commands:[0,1].map(()=>({executed:true,status:'Completed',exit_code:0,cleanup_unresolved:false})),
    checks:Object.fromEntries(['configuration','source_identity','routing','timing','electrical'].map(name=>[name,{validation_status:name==='electrical'?'Failed':'Passed'}]))}});
flow.data={implemented:true,ready:true,tool_ready:true,runs:[],reviews:[],runtime_configuration_sha256:'software-qa-v1'};
const host=new DOMDouble('main');flow.render(host);
const find=id=>host.querySelector(`[data-testid="${id}"]`);
const install=run=>{flow.data={...flow.data,runs:[run],latest_run_id:run.id};flow.runId=run.id;project.envelope.physical_workflow=flow.data;flow.refresh();};
const deferred=()=>{let resolve;const promise=new Promise(r=>resolve=r);return {promise,resolve};};
"""


class PhysicalRepairClientTests(unittest.TestCase):
    """Production client plus isolated fixtures; no browser/live stores/EDA."""
    def run_client(self,body):
        node=shutil.which("node")
        if not node: self.skipTest("Node is required for the isolated physical repair client checks.")
        result=subprocess.run([node,"-e",REPAIR_CLIENT+"\n(async()=>{\n"+body+
            "\nconsole.log('Passed: isolated physical repair software fixture');\n})().catch(error=>{console.error(error.stack||error);process.exitCode=1;});"],
            cwd=PROJECT,capture_output=True,text=True,encoding="utf-8",timeout=20)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_gui_preparation_is_explicit_ids_only_without_eda_and_preserves_failed_attempt(self):
        self.run_client(r"""
const run=failure();install(run);const original=JSON.stringify(run);
assert.equal(find('physical-workflow-repair-card').hidden,false);
assert.equal(find('physical-workflow-prepare-repair').disabled,false);
assert.match(text(find('physical-workflow-repair-card')),/50 ns.*SDC.*expected values/);
assert.match(text(find('physical-workflow-repair-card')),/new S11 → S12 → S13 → S14/);
assert.equal(requests.length,0);
responder=async()=>({...project.envelope,physical_repair_session:{configured:true,repair_generation:2,profile_version:'hullcirq-sky130-route-repair-npu2v2'},
  physical_workflow:{...flow.data,runtime_configuration_sha256:'software-qa-v2',runs:[{...normalized(run),freshness:'Stale'}]}});
await find('physical-workflow-prepare-repair').click();
assert.deepEqual(normalized(requests),[{route:'physical-workflow/repair-profile',body:{failed_layout_id:run.id,revision_id:'software-qa-revision'}}]);
assert.equal(JSON.stringify(run),original);assert.equal(flow.data.runs.length,1);assert.equal(flow.selected().validation_status,'Failed');
assert.equal(find('physical-workflow-prepare-repair'),null);assert.equal(find('physical-workflow-repair-card').hidden,false);
assert.match(text(find('physical-workflow-repair-card')),/explicit GUI action\. Preparing this profile did not start EDA/);
assert.match(text(find('physical-workflow-repair-card')),/Physical execution is a separate explicit action/);
assert.doesNotMatch(text(find('physical-workflow-repair-card')),/No EDA has started/);
assert.equal(navigations.length,0);assert.match(toasts.at(-1),/No EDA was started/);
await flow.prepareFixedRepair(run);assert.equal(requests.length,1);
// Only a second, explicit Run action can request a physical execution.
responder=async()=>({...project.envelope,physical_workflow:{...flow.data,runs:[...flow.data.runs,{id:'software-qa-new-layout',execution_status:'Queued'}],latest_run_id:'software-qa-new-layout'}});
await flow.start();assert.equal(requests.length,2);assert.equal(requests[1].route,'physical-workflow/runs');
""")

    def test_only_exact_latest_current_first_profile_electrical_failure_is_eligible(self):
        self.run_client(r"""
for (const mutate of [r=>r.freshness='Stale',r=>r.execution_status='Failed',r=>r.validation_status='Passed',r=>r.revision_id='other',
  r=>r.error={code:'error'},r=>r.evidence_kind='trusted_saved_tool_revalidation',r=>r.software_qa_fixture=true,
  r=>r.runtime_configuration.profile.profile_version='other',r=>r.checks.origin='other',r=>r.checks.executed=false,r=>r.checks.exit_code=1,
  r=>r.checks.cleanup_unresolved=true,r=>r.checks.commands.pop(),r=>r.checks.commands[0].cleanup_unresolved=true,
  r=>r.checks.checks.timing.validation_status='Failed',r=>r.checks.checks.extra={validation_status:'Passed'},r=>r.diagnostics=[]]) {
  const run=failure();mutate(run);install(run);assert.equal(find('physical-workflow-repair-card').hidden,true);await flow.prepareFixedRepair(run);
}
const run=failure();install(run);flow.data.latest_run_id='other';flow.refresh();assert.equal(find('physical-workflow-repair-card').hidden,true);
assert.equal(requests.length,0);
""")

    def test_guards_and_pending_request_prevent_preparation_and_duplicates(self):
        self.run_client(r"""
const run=failure();install(run);
for (const [object,key,value] of [[project,'dirty',true],[project,'conflict','newer'],[project,'busy',true],[project,'readOnly',true],
  [flow,'busy',true],[flow,'pollError','lost'],[flow,'uncertainStart',true],[flow.data,'storage_error',{message:'store failure'}],
  [project.envelope,'workspace_identity',{read_only:true}],[project.envelope,'generation',{jobs:[{execution_status:'Running'}]}],
  [project.envelope,'repair_analysis',{jobs:[{execution_status:'Running'}]}],[project.envelope,'generation_batches',{batches:[{execution_status:'Queued'}]}],
  [project.envelope,'postlayout_workflow',{runs:[{checks:{cleanup_unresolved:true}}]}]]) {
  const old=object[key];object[key]=value;flow.refresh();assert.equal(find('physical-workflow-prepare-repair').disabled,true);await flow.prepareFixedRepair(run);object[key]=old;
}
assert.equal(requests.length,0);flow.refresh();
const pending=deferred();responder=async()=>pending.promise;const request=flow.prepareFixedRepair(run);
assert.equal(find('physical-workflow-prepare-repair').disabled,true);await flow.prepareFixedRepair(run);assert.equal(requests.length,1);
pending.resolve(project.envelope);await request;assert.equal(flow.busy,false);
""")

    def test_lost_response_requires_readonly_refresh_without_resending(self):
        self.run_client(r"""
const run=failure();install(run);responder=async()=>{throw new Error('SOFTWARE QA lost response');};
await flow.prepareFixedRepair(run);assert.equal(requests.length,1);assert.match(flow.pollError,/without resending/);
assert.equal(find('physical-workflow-prepare-repair').disabled,true);await flow.prepareFixedRepair(run);assert.equal(requests.length,1);
responder=async()=>project.envelope;await flow.refreshSaved();assert.equal(requests.length,2);assert.equal(requests.at(-1).route,'project');
assert.equal(requests.at(-1).body,undefined);assert.equal(flow.pollError,null);assert.equal(run.validation_status,'Failed');
""")

    def test_second_failure_prepares_third_version_without_replacing_ancestry_or_starting_tools(self):
        self.run_client(r"""
const run=failure();run.id='software-qa-second-failure';
run.runtime_configuration.profile.profile_version='hullcirq-sky130-route-repair-npu2v2';
run.checks.implementation_kind='resumed_post_GRT_route_repair';
project.envelope.physical_repair_session={configured:true,repair_generation:2,profile_version:'hullcirq-sky130-route-repair-npu2v2'};
install(run);const original=JSON.stringify(run);
assert.equal(find('physical-workflow-prepare-repair').disabled,false);
assert.equal(requests.length,0);
responder=async()=>({...project.envelope,physical_repair_session:{configured:true,repair_generation:3,profile_version:'hullcirq-sky130-route-repair-npu2v3'},
  physical_workflow:{...flow.data,runtime_configuration_sha256:'software-qa-v3',runs:[{...normalized(run),freshness:'Stale'}]}});
await find('physical-workflow-prepare-repair').click();
assert.deepEqual(normalized(requests),[{route:'physical-workflow/repair-profile',body:{failed_layout_id:run.id,revision_id:'software-qa-revision'}}]);
assert.equal(JSON.stringify(run),original);assert.equal(flow.data.runs.length,1);
assert.equal(find('physical-workflow-prepare-repair'),null);
assert.match(text(find('physical-workflow-repair-card')),/Preparing this profile did not start EDA/);
await flow.prepareFixedRepair(run);assert.equal(requests.length,1);
// A failed final profile has no unbounded automatic fourth-version preparation.
const final=failure();final.runtime_configuration.profile.profile_version='hullcirq-sky130-route-repair-npu2v3';
final.runtime_configuration.profile.implementation_kind='resume_second_NPU2_repair_post_timing_checkpoint_before_one_extra_standard_electrical_repair';
final.checks.implementation_kind='resumed_post_GRT_route_repair';install(final);
assert.match(text(find('physical-workflow-implementation')),/post-timing checkpoint.*all-nine-corner timing repair are reused/);
assert.equal(flow.fixedRepairEligible(final),false);await flow.prepareFixedRepair(final);assert.equal(requests.length,1);
""")

    def test_second_failure_retains_all_guards_and_requires_matching_host_generation(self):
        self.run_client(r"""
const run=failure();run.runtime_configuration.profile.profile_version='hullcirq-sky130-route-repair-npu2v2';
run.checks.implementation_kind='resumed_post_GRT_route_repair';
project.envelope.physical_repair_session={configured:true,repair_generation:2,profile_version:'hullcirq-sky130-route-repair-npu2v2'};
for (const mutate of [r=>r.freshness='Stale',r=>r.review_status='Accepted',r=>r.checks.implementation_kind='resumed_pre_CTS_route_repair',
  r=>r.checks.checks.timing.validation_status='Failed',r=>r.checks.commands[0].cleanup_unresolved=true]) {
  const bad=normalized(run);mutate(bad);install(bad);assert.equal(flow.fixedRepairEligible(bad),false);await flow.prepareFixedRepair(bad);
}
install(run);
for (const [object,key,value] of [[project,'dirty',true],[project,'conflict','newer'],[project,'busy',true],[project,'readOnly',true],
  [flow,'busy',true],[flow,'pollError','lost'],[flow,'uncertainStart',true],[flow.data,'storage_error',{message:'store failure'}],
  [project.envelope,'generation',{jobs:[{execution_status:'Running'}]}],[project.envelope,'postlayout_workflow',{runs:[{checks:{cleanup_unresolved:true}}]}]]) {
  const old=object[key];object[key]=value;flow.refresh();assert.equal(find('physical-workflow-prepare-repair').disabled,true);
  await flow.prepareFixedRepair(run);object[key]=old;
}
for (const status of [{configured:false},{configured:true,profile_version:'hullcirq-sky130-route-repair-npu2v1'},
  {configured:true,profile_version:'hullcirq-sky130-route-repair-npu2v3'},
  {configured:true,profile_version:'hullcirq-sky130-route-repair-npu2v2',error:{message:'corrupt bundle'}}]) {
  project.envelope.physical_repair_session=status;assert.ok(flow.fixedRepairGate(run));await flow.prepareFixedRepair(run);
}
assert.equal(requests.length,0);
""")


if __name__ == "__main__":
    unittest.main()
