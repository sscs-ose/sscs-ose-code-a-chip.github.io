"""Browser regression QA using isolated software doubles, never circuit proof.

No live project, model, compiler or synthesizer is used. The double deliberately
separates tool completion from policy adoption to exercise the real GUI polling.
"""
from __future__ import annotations

import copy
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
from hullcirq.server import RequestHandler, make_server
from hullcirq.store import ProjectStore, utc_now
from hullcirq.verification import content_hash
from hullcirq.execution_submissions import validate_submissions


class InMemorySubmissionDouble:
    """Faithful atomic receipt owner for software fixtures; never writes files."""
    def _init_submission_memory(self, **pools):
        self.lock = getattr(self, "lock", threading.RLock())
        self._worker = None
        self._state = pools
        self._committed = copy.deepcopy(self._state)
        self.memory_persists = 0

    def _persist(self):
        with self.lock:
            for pool in ("jobs", "runs", "batches", "reviews"):
                if hasattr(self, pool):
                    self._state[pool] = getattr(self, pool)
            validate_submissions(self._state)
            self._committed = copy.deepcopy(self._state)
            self.memory_persists += 1


class GlobalGenerationDouble(InMemorySubmissionDouble):
    """A declared software fixture, not generated or verified RTL."""
    def __init__(self, revision):
        self.job = {"id": "software-qa-global", "revision_id": revision,
                    "execution_status": "Completed", "validation_status": "Passed",
                    "review_status": "Accepted", "freshness": "Current",
                    "rtl_sha256": content_hash("SOFTWARE QA ONLY"), "software_qa_fixture": True}
        self.jobs = [self.job]
        self._init_submission_memory(jobs=self.jobs)

    def envelope(self):
        return {"global_generation": {"implemented": True, "ready": True, "blocked_reason": None,
                "jobs": [copy.deepcopy(self.job)], "reviews": [], "latest_job_id": self.job["id"],
                "required_node_count": 6, "storage_error": None}}

    def is_active(self):
        return False

    def close(self):
        pass


class ControlledWorkflowDouble(InMemorySubmissionDouble):
    """Explicitly controlled fake status transitions; never runs tools."""
    def __init__(self, store):
        self.store = store
        self.lock = threading.RLock()
        self.runs = []
        self.reviews = []
        self.calls = []
        self.ready = True
        self._init_submission_memory(runs=self.runs, reviews=self.reviews)

    def envelope(self):
        with self.lock:
            stages = []
            for stage in ("global_synthesis", "global_netlist_simulation"):
                run = next((item for item in reversed(self.runs) if item["stage_id"] == stage), None)
                stages.append({"stage_id": stage, "latest_run_id": run["id"] if run else None,
                               "accepted_run_id": run["id"] if run and run["review_status"] == "Accepted" else None})
            return {"global_workflow": {"implemented": True, "ready": self.ready,
                    "blocked_reason": None if self.ready else "SOFTWARE QA external source changed",
                    "storage_error": None, "runs": copy.deepcopy(self.runs),
                    "reviews": copy.deepcopy(self.reviews), "stages": stages}}

    def is_active(self):
        with self.lock:
            return any(run["execution_status"] in ("Queued", "Running") for run in self.runs)

    def start(self, stage, job, prior, revision, *, _submission=None):
        with self.lock:
            self.calls.append(("start", stage, job, prior, revision))
            run = {"id": "software-qa-synthesis", "stage_id": stage, "global_job_id": job,
                              "revision_id": revision, "execution_status": "Running",
                              "validation_status": "Not Checked", "review_status": "Awaiting Review",
                              "freshness": "Current", "created_at": utc_now(), "finished_at": None,
                              "checks": {}, "diagnostics": [], "source_manifest": {"software_qa_fixture": True},
                              "verification_plan": {"software_qa_fixture": True}, "software_qa_fixture": True}
            if _submission is not None:
                run["submission_id"] = _submission.submission_id
                _submission.bind(run["id"])
            self.runs.append(run)
            self._persist()

    def transition(self, state):
        with self.lock:
            run = self.runs[-1]
            run.update(execution_status="Completed", validation_status="Passed", finished_at=utc_now())
            if state == "accepted":
                run.update(review_status="Accepted", netlist="// SOFTWARE QA ONLY; never compiled\n",
                           netlist_sha256=content_hash("// SOFTWARE QA ONLY; never compiled\n"))
                self.reviews.append({"id": "software-qa-policy-review", "run_id": run["id"],
                                     "decision": "accepted", "actor": "automation_policy",
                                     "provenance": {"policy_id": self.store.review_policy()["id"]},
                                     "note": "SOFTWARE QA controlled policy transition only"})
            elif state != "awaiting":
                raise ValueError("Unsupported software-only control")
            self._persist()

    def close(self):
        pass

    def external_source_changed(self):
        with self.lock:
            self.ready = False
            for run in self.runs:
                run.update(freshness="Stale", review_status="Awaiting Review")
            self._persist()


class SoftwareControlHandler(RequestHandler):
    def do_POST(self):
        # This route exists only in this isolated test server, never production.
        if self.path == "/software-qa/external-source":
            self.rfile.read(int(self.headers["Content-Length"]))
            current = self.server.store.envelope()
            changed = copy.deepcopy(current["design"])
            changed["project"]["name"] = "SOFTWARE QA external saved source"
            self.server.store.save(changed, current["revision"]["id"])
            self.server.global_workflow.external_source_changed()
            self._json({"software_qa_fixture": True})
            return
        if self.path == "/software-qa/transition":
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            self.server.global_workflow.transition(body["state"])
            self._json({"software_qa_fixture": True})
            return
        super().do_POST()


BROWSER_TEST = r"""
const assert = require('node:assert/strict');
const { chromium } = require(process.env.HULLCIRQ_PLAYWRIGHT_PATH || 'playwright');
(async () => {
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  try {
    const context = await browser.newContext();
    const page = await context.newPage(); page.setDefaultTimeout(20000);
    const errors = [], writes = [];
    page.on('pageerror', error => errors.push(error.message));
    page.on('request', request => { if (request.method() === 'POST') writes.push(new URL(request.url()).pathname); });
    const test = id => page.getByTestId(id);
    const original = await (await context.request.get(process.env.HULLCIRQ_SOFTWARE_QA_URL + 'api/project')).json();
    await page.goto(process.env.HULLCIRQ_SOFTWARE_QA_URL);
    await test('stage-global_synthesis').click();
    await page.waitForFunction(() => !document.querySelector('[data-testid="global-workflow-run"]')?.disabled);
    await test('global-workflow-run').click();
    await page.waitForFunction(() => document.querySelector('[data-testid="stage-global_synthesis"]')?.textContent.includes('Running'));
    assert.ok((await test('global-workflow-status').innerText()).includes('Running'));

    // Create a real unsaved browser draft after execution starts. Polling must
    // update evidence without replacing this source or its optimistic base.
    await test('stage-global_settings').click();
    await test('project-name').fill('SOFTWARE QA unsaved source retained');
    await test('stage-global_synthesis').click();
    const awaitingProject = page.waitForResponse(response => response.url().endsWith('/api/project') && response.request().method() === 'GET');
    await context.request.post(process.env.HULLCIRQ_SOFTWARE_QA_URL + 'software-qa/transition', { data: { state: 'awaiting' } });
    await awaitingProject;
    // Finish the complete Awaiting Review poll before advancing the double.
    // This prevents the full-project response from accidentally observing
    // Accepted early and hiding a missing pending-policy follow-up poll.
    await page.waitForFunction(() => !document.querySelector('[data-testid="global-workflow-refresh"]')?.disabled);
    await page.waitForFunction(() => {
      const status = document.querySelector('[data-testid="global-workflow-status"]')?.textContent || '';
      return status.includes('Completed') && status.includes('Passed') && status.includes('Awaiting Review');
    });
    assert.ok(!(await test('stage-global_synthesis').innerText()).includes('Running'));
    await context.request.post(process.env.HULLCIRQ_SOFTWARE_QA_URL + 'software-qa/transition', { data: { state: 'accepted' } });
    // No reload or second start: pending-policy polling must discover adoption.
    await page.waitForFunction(() => document.querySelector('[data-testid="global-workflow-status"]')?.textContent.includes('Accepted'));
    assert.ok((await test('stage-global_synthesis').innerText()).includes('Not run'), 'unsaved source must not look complete');
    await page.waitForFunction(() => {
      const lineage = document.querySelector('[data-testid="global-workflow-lineage"]')?.textContent || '';
      const provenance = document.querySelector('[data-testid="global-workflow-adoption-provenance"]')?.textContent || '';
      return lineage.includes('Adopted S09 run software-qa-synthesis') && provenance.includes('authorized adoption policy');
    });
    assert.ok((await test('global-workflow-adoption-provenance').innerText()).includes(original.review_policy.id));
    assert.ok((await page.locator('#save-state').innerText()).includes('Unsaved design inputs'));
    assert.equal(await test('global-workflow-run').isDisabled(), true);
    assert.equal(await test('global-workflow-continue').isDisabled(), true);
    await test('stage-global_settings').click();
    assert.equal(await test('project-name').inputValue(), 'SOFTWARE QA unsaved source retained');
    assert.ok((await page.locator('#revision-label').innerText()).includes(original.revision.id));
    const saved = await (await context.request.get(process.env.HULLCIRQ_SOFTWARE_QA_URL + 'api/project')).json();
    assert.equal(saved.design.project.name, original.design.project.name);
    assert.equal(saved.revision.id, original.revision.id);

    // An external save changes the authoritative currentness. A full-project
    // refresh must retain our old source/save base and first eight stage rows,
    // while replacing S09/S10 status rows rather than resurrecting Accepted.
    await test('stage-global_synthesis').click();
    const earlierRows = await page.locator('#stage-tabs .stage-tab').evaluateAll(nodes => nodes.slice(0, 8).map(node => node.textContent));
    await context.request.post(process.env.HULLCIRQ_SOFTWARE_QA_URL + 'software-qa/external-source', { data: {} });
    await page.waitForFunction(() => !document.querySelector('[data-testid="global-workflow-refresh"]')?.disabled);
    await test('global-workflow-refresh').click();
    await page.waitForFunction(() => document.querySelector('[data-testid="global-workflow-status"]')?.textContent.includes('Stale'));
    assert.ok((await test('stage-global_synthesis').innerText()).includes('Not run'));
    assert.ok((await test('global-workflow-status').innerText()).includes('Stale'));
    assert.deepEqual(await page.locator('#stage-tabs .stage-tab').evaluateAll(nodes => nodes.slice(0, 8).map(node => node.textContent)), earlierRows);
    assert.ok((await page.locator('#save-state').innerText()).includes('Newer saved design'));
    assert.equal(await test('global-workflow-continue').isDisabled(), true);
    await test('stage-global_settings').click();
    assert.equal(await test('project-name').inputValue(), 'SOFTWARE QA unsaved source retained');
    assert.ok((await page.locator('#revision-label').innerText()).includes(original.revision.id));
    const retainedBase = await page.evaluate(() => JSON.parse(localStorage.getItem('hullcirq.m1.draft.v1')).base_revision_id);
    assert.equal(retainedBase, original.revision.id);
    const external = await (await context.request.get(process.env.HULLCIRQ_SOFTWARE_QA_URL + 'api/project')).json();
    assert.notEqual(external.revision.id, original.revision.id);
    assert.equal(external.design.project.name, 'SOFTWARE QA external saved source');
    assert.deepEqual(writes, ['/api/global-workflow/runs']);
    assert.deepEqual(errors, []);
    console.log(JSON.stringify({ status: 'Passed', software_qa_fixture: true, model_calls: 0, eda_calls: 0,
      observed: ['Running', 'Completed/Passed/Awaiting Review', 'Accepted with stage ID and policy provenance'],
      source_draft_preserved: true, external_revision_conflict_preserved: true,
      first_eight_stage_rows_preserved: true, authoritative_tool_staleness_displayed: true, start_requests: writes.length }));
  } finally { await browser.close(); }
})().catch(error => { console.error(error.stack || error); process.exitCode = 1; });
"""


class GlobalWorkflowGUIRegressionTests(unittest.TestCase):
    def test_policy_settle_poll_updates_stage_source_and_provenance_without_losing_draft(self):
        executable = shutil.which("node")
        if not executable:
            self.skipTest("Node and Playwright are required for browser software QA.")
        with tempfile.TemporaryDirectory(prefix="hullcirq-global-gui-software-qa-") as directory:
            store = ProjectStore(Path(directory) / "project", PROJECT / "examples/npu_all_nodes_project.json")
            store.set_review_policy("accept_on_pass", True, "SOFTWARE QA only; no circuit proof")
            server = make_server("127.0.0.1", 0, store, PROJECT)
            server.global_workflow.close()
            server.global_generation.close()
            server.global_workflow = double = ControlledWorkflowDouble(store)
            server.global_generation = GlobalGenerationDouble(store.envelope()["revision"]["id"])
            server.RequestHandlerClass = SoftwareControlHandler
            thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": .02}, daemon=True)
            thread.start()
            try:
                environment = browser_environment()
                environment["HULLCIRQ_SOFTWARE_QA_URL"] = f"http://127.0.0.1:{server.server_address[1]}/"
                result = subprocess.run([executable, "-e", BROWSER_TEST], env=environment, cwd=PROJECT,
                                        text=True, encoding="utf-8", capture_output=True, timeout=80)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(len(double.calls), 1)
                self.assertEqual(double.calls[0][0], "start")
                self.assertTrue(json.loads(result.stdout.strip().splitlines()[-1])["source_draft_preserved"])
            finally:
                server.shutdown(); server.server_close(); server.workflow.close(); server.generation.close()
                thread.join(2)


if __name__ == "__main__":
    unittest.main()
