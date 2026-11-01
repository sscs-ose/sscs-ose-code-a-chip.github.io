/** S12 GUI recorder: one explicitly requested DRC start or read-only observation. */
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const assert = require('node:assert/strict');
const { chromium } = require(process.env.HULLCIRQ_PLAYWRIGHT_PATH || 'playwright');
const sidebarStatus = require('./gui_recorder_status.cjs');

const root = path.resolve(__dirname, '..'), phase = process.argv[2];
assert.ok(['drc', 'observe-drc'].includes(phase), 'Choose drc or observe-drc.');
const observe = phase === 'observe-drc', url = process.env.HULLCIRQ_NPU_URL || 'http://127.0.0.1:8768/';
const waitMs = Number(process.env.HULLCIRQ_DRC_WAIT_MS || 7200000);
assert.ok(Number.isFinite(waitMs) && waitMs > 0, 'HULLCIRQ_DRC_WAIT_MS must be positive.');
const output = path.join(path.resolve(root, process.env.HULLCIRQ_GUI_OUTPUT_ROOT || '.work/m2h/gui-operations'), new Date().toISOString().replace(/[:.]/g, '-') + '-' + phase + '-' + crypto.randomBytes(4).toString('hex'));
fs.mkdirSync(output, { recursive: true });
const JSON_FIELDS = ['layout-record', 'source-identity', 'runtime-configuration', 'artifact-manifest'];
const FILE_IDS = new Set(['input-gds', 'config', 'initial-state', 'final-state', 'metrics', 'tool-versions', 'drc-summary', 'klayout-violations', 'magic-report', 'magic-markers', 'klayout-report']);
const extensions = { 'input-gds': 'gds', 'magic-report': 'rpt', 'magic-markers': 'xml', 'klayout-report': 'lyrdb' };
const actions = [], errors = [], downloads = [], captureErrors = [], requests = [];
const sha = raw => crypto.createHash('sha256').update(raw).digest('hex'), at = () => new Date().toISOString();
const active = run => ['Queued', 'Running'].includes(run.execution_status);
let browser, context, page, trackedId, beforeSources, completed, finalProject, allowedWrites = 0, lastObservedStatus;
const endpoint = route => new URL('/api/' + route, url).href, test = id => page.getByTestId(id);
function event(kind, detail) { fs.appendFileSync(path.join(output, 'events.jsonl'), JSON.stringify({ at: at(), kind, ...detail }) + '\n'); }
function provenance(extra = {}) { return { actor: 'development_assistant_gui_automation', phase, stage: 'drc', url, run_id: trackedId, frozen_source_ids: beforeSources, actions, requests, downloads, page_errors: errors, capture_errors: captureErrors, model_calls: 0, allowed_mutation_requests: allowedWrites, mutation_retry: false, scope: 'Exact adopted S11 GDS and pinned PDK DRC checks. Observe-drc is read-only. Policy adoption is not a manual human click. DRC does not establish LVS or dynamic post-layout verification.', ...extra }; }
function checkpoint() { fs.writeFileSync(path.join(output, 'gui-operation-progress.json'), JSON.stringify(provenance({ last_observed_status: lastObservedStatus, updated_at: at() }), null, 2) + '\n'); }
async function getExact(route, filename, binary = false) {
  const response = await context.request.get(endpoint(route), { timeout: 120000 }), raw = await response.body();
  if (filename) fs.writeFileSync(path.join(output, filename), raw);
  event('read_response', { route, status: response.status(), bytes: raw.length, sha256: sha(raw), filename });
  assert.ok(response.ok(), 'Read failed: ' + route + ' ' + response.status());
  // Parsed numbers are for UI assertions only. Saved original bytes remain authoritative.
  return { raw, value: binary ? undefined : JSON.parse(raw.toString('utf8')) };
}
function sources(saved) {
  const layout = saved.physical_workflow?.runs?.find(run => run.id === saved.physical_workflow.accepted_run_id);
  const gds = layout?.artifacts?.find(item => item.id === 'gds');
  if (!layout || layout.execution_status !== 'Completed' || layout.validation_status !== 'Passed' || layout.review_status !== 'Accepted' || layout.freshness !== 'Current' || layout.revision_id !== saved.revision.id || !gds?.sha256) return null;
  return { revision_id: saved.revision.id, layout_run_id: layout.id, input_gds_sha256: gds.sha256 };
}
async function clickReadOnly(id, action) { const record = { control: id, action, at: at(), mutation: false }; actions.push(record); event('gui_action', record); checkpoint(); await test(id).click(); record.outcome = 'Completed'; }
async function waitUI(saved, run) {
  await page.waitForFunction(expected => {
    const lineage = document.querySelector('[data-testid="drc-workflow-lineage"]')?.textContent || '', status = document.querySelector('[data-testid="drc-workflow-status"]')?.textContent || '';
    return (expected.sources ? Object.values(expected.sources).every(value => lineage.includes(value)) : lineage.includes('Not available')) && expected.stages.every(stage => document.querySelector(`[data-testid="stage-${stage.id}"]`)?.textContent.includes(stage.status)) && (!expected.run || Object.values(expected.run).every(value => status.includes(value)));
  }, { sources: sources(saved), stages: saved.workflow.map(stage => ({ id: stage.id, status: sidebarStatus(stage) })), run: run ? Object.fromEntries(['id', 'execution_status', 'validation_status', 'review_status', 'freshness'].map(key => [key, run[key]])) : null });
  actions.push({ action: 'inspected_source_identity_status_and_ordered_stages', frozen_source_ids: sources(saved), run_id: run?.id, at: at(), mutation: false }); checkpoint();
}
async function download(id, kind, extension, route, rawFile = false, descriptor) {
  const originalFilename = kind + '-api-original.' + (rawFile ? extension : 'json'), original = await getExact(route, originalFilename, rawFile);
  const record = { control: id, action: 'download_saved_artifact', kind, at: at(), mutation: false }; actions.push(record); event('gui_action', record); checkpoint();
  const [item] = await Promise.all([page.waitForEvent('download'), test(id).click()]), filename = kind + '.' + extension;
  await item.saveAs(path.join(output, filename)); assert.equal(await item.failure(), null);
  const raw = fs.readFileSync(path.join(output, filename)); assert.ok(raw.equals(original.raw), 'GUI download differs from original backend bytes: ' + kind);
  if (descriptor) { assert.equal(raw.length, descriptor.bytes); assert.equal(sha(raw), descriptor.sha256); }
  Object.assign(record, { outcome: 'Downloaded and byte-compared', filename });
  const result = { control: id, kind, filename, bytes: raw.length, sha256: sha(raw), exact_backend_match: true, response_format: rawFile ? 'raw' : 'json', backend_response_filename: originalFilename, backend_response_sha256: sha(original.raw), backend_response_bytes: original.raw.length, ...(descriptor ? { exact_manifest_match: true, manifest_sha256: descriptor.sha256, manifest_bytes: descriptor.bytes } : {}) };
  downloads.push(result); event('gui_download', result); checkpoint();
}
(async () => {
  browser = await chromium.launch({ channel: 'msedge', headless: true }); context = await browser.newContext({ viewport: { width: 1500, height: 1100 }, acceptDownloads: true });
  // At most one explicit start; no accidental review, model, retry or mutation.
  await context.route('**/api/**', async route => {
    const request = route.request(), pathname = new URL(request.url()).pathname;
    if (['GET', 'HEAD'].includes(request.method())) { await route.continue(); return; }
    const allowed = !observe && request.method() === 'POST' && pathname === '/api/drc-workflow/runs' && allowedWrites === 0;
    const record = { method: request.method(), path: pathname, allowed, at: at(), original_request_body: request.postData() }; requests.push(record); event('mutation_request', record);
    if (!allowed) { captureErrors.push('Blocked unexpected mutation: ' + request.method() + ' ' + pathname); await route.abort('blockedbyclient'); return; }
    allowedWrites += 1; fs.writeFileSync(path.join(output, 'start-request-body-original.json'), request.postData() || ''); checkpoint(); await route.continue();
  });
  page = await context.newPage(); page.setDefaultTimeout(Math.min(120000, waitMs)); page.on('pageerror', error => { errors.push(error.message); event('page_error', { message: error.message }); });
  const original = (await getExact('project', 'project-before-api-original.json')).value; beforeSources = sources(original);
  const before = (await getExact('drc-workflow', 'drc-workflow-before-api-original.json')).value.drc_workflow;
  await page.goto(url); await test('stage-drc').waitFor(); await clickReadOnly('stage-drc', 'open_drc_stage'); await test('drc-workflow-run').waitFor(); await waitUI(original);
  await page.screenshot({ path: path.join(output, 'drc-workflow-before.png'), fullPage: true }); trackedId = process.env.HULLCIRQ_DRC_WORKFLOW_RUN_ID;
  if (!observe) {
    assert.equal(before.ready, true, before.blocked_reason || 'Exact adopted S11 evidence is required.'); assert.equal(before.tool_ready, true, before.tool_blocked_reason || 'Pinned DRC runtime is required.'); assert.ok(beforeSources); assert.ok(!before.runs.some(active));
    await page.waitForFunction(() => !document.querySelector('[data-testid="drc-workflow-run"]')?.disabled);
    const action = { control: 'drc-workflow-run', action: 'start_exactly_one_drc_execution', frozen_source_ids: beforeSources, at: at(), outcome: 'Unknown; mutation will not be retried' }; actions.push(action); event('gui_action', action); checkpoint();
    const [response] = await Promise.all([page.waitForResponse(item => new URL(item.url()).pathname === '/api/drc-workflow/runs' && item.request().method() === 'POST'), test('drc-workflow-run').click()]);
    // Full POST envelopes can exceed inspector cache. Keep metadata and use a read-only authoritative GET.
    const metadata = { status: response.status(), url: response.url(), original_request_body: response.request().postData(), response_body_captured: false, reason: 'Authoritative saved bytes are retained by the subsequent GET; no POST retry.' }; fs.writeFileSync(path.join(output, 'start-response-metadata.json'), JSON.stringify(metadata, null, 2) + '\n'); Object.assign(action, metadata); checkpoint(); assert.ok(response.ok(), 'Start was rejected; no retry.');
    const after = (await getExact('drc-workflow', 'drc-workflow-started-api-original.json')).value.drc_workflow, started = after.runs.find(run => run.id === after.latest_run_id);
    assert.ok(started && !before.runs.some(run => run.id === started.id), 'No distinct new run found; request will not be retried.'); trackedId = started.id;
    for (const [key, value] of Object.entries(beforeSources)) assert.equal(started[key], value, 'Started run changed source ' + key);
    console.log(JSON.stringify({ event: 'drc_run_started', id: trackedId, frozen_source_ids: beforeSources, output }));
  } else { trackedId ||= before.latest_run_id; assert.ok(trackedId && before.runs.some(run => run.id === trackedId && run.stage_id === 'drc'), 'No matching recorded DRC run to observe.'); }
  const deadline = Date.now() + waitMs;
  while (true) {
    completed = (await getExact('drc-workflow/runs/' + encodeURIComponent(trackedId), 'last-run-api-original.json')).value;
    let terminal = !active(completed) && !!completed.finished_at, pending = false;
    if (terminal) { finalProject = (await getExact('project', 'project-terminal-api-original.json')).value; completed = finalProject.drc_workflow.runs.find(run => run.id === trackedId) || completed; terminal = !active(completed) && !!completed.finished_at; pending = finalProject.review_policy?.mode === 'accept_on_pass' && finalProject.review_policy?.user_authorized === true && !finalProject.drc_workflow.storage_error && completed.execution_status === 'Completed' && completed.validation_status === 'Passed' && completed.review_status === 'Awaiting Review' && completed.freshness === 'Current' && !completed.error && !(completed.diagnostics || []).some(item => item.code === 'automatic_adoption_blocked'); }
    const status = Object.fromEntries(['id', 'execution_status', 'validation_status', 'review_status', 'freshness'].map(key => [key, completed[key]])); status.policy_pending = pending;
    if (JSON.stringify(status) !== JSON.stringify(lastObservedStatus)) { lastObservedStatus = status; event('observed_status', status); checkpoint(); console.log(JSON.stringify({ event: 'drc_progress', ...status })); }
    if (terminal && !pending) break; assert.ok(Date.now() < deadline, 'Bounded wait exceeded. Partial evidence retained; execution is not restarted.'); await new Promise(resolve => setTimeout(resolve, 1500));
  }
  await page.waitForFunction(() => !document.querySelector('[data-testid="drc-workflow-refresh"]')?.disabled); await clickReadOnly('drc-workflow-refresh', 'read_saved_project_without_reexecuting'); await test('drc-workflow-run-' + trackedId).waitFor(); await clickReadOnly('drc-workflow-run-' + trackedId, 'select_recorded_run'); await waitUI(finalProject, completed);
  await page.screenshot({ path: path.join(output, 'drc-workflow-terminal.png'), fullPage: true });
  for (const id of ['drc-workflow-logs', 'drc-workflow-frozen-input']) await test(id).evaluate(node => { node.open = true; });
  await page.screenshot({ path: path.join(output, 'drc-workflow-expanded-evidence.png'), fullPage: true });
  const prefix = 'artifacts/drc-workflow/' + encodeURIComponent(trackedId) + '/';
  const attempt = async work => { try { await work(); } catch (error) { captureErrors.push(error.message); event('capture_error', { message: error.message }); checkpoint(); } };
  await attempt(() => download('drc-workflow-download-run', 'run', 'json', 'drc-workflow/runs/' + encodeURIComponent(trackedId)));
  for (const id of JSON_FIELDS) await attempt(() => download('drc-workflow-download-' + id, id, 'json', prefix + id));
  for (const item of completed.artifacts || []) { if (!FILE_IDS.has(item.id) || item.url !== '/api/' + prefix + item.id) { captureErrors.push('Artifact outside fixed allowlist: ' + item.id); continue; } await attempt(() => download('drc-workflow-download-' + item.id, item.id, extensions[item.id] || 'json', prefix + item.id, true, item)); }
  completed = (await getExact('drc-workflow/runs/' + encodeURIComponent(trackedId), 'run-api-original.json')).value;
  if (!observe) assert.deepEqual(sources(finalProject), beforeSources, 'S11 source changed during DRC.'); assert.equal(allowedWrites, observe ? 0 : 1); assert.deepEqual(errors, []); assert.deepEqual(captureErrors, []);
  fs.writeFileSync(path.join(output, 'gui-operation.json'), JSON.stringify(provenance({ capture_status: 'Passed', execution_status: completed.execution_status, validation_status: completed.validation_status, review_status: completed.review_status, freshness: completed.freshness, finished_at: at() }), null, 2) + '\n');
  console.log(JSON.stringify({ status: 'Captured', capture_status: 'Passed', phase, id: trackedId, execution_status: completed.execution_status, validation_status: completed.validation_status, review_status: completed.review_status, freshness: completed.freshness, output, downloads: downloads.length }));
  assert.ok(completed.execution_status === 'Completed' && completed.validation_status === 'Passed' && completed.freshness === 'Current', 'DRC did not pass for current sources. Failed evidence retained; no restart.'); if (finalProject.review_policy?.mode === 'accept_on_pass' && finalProject.review_policy?.user_authorized === true) assert.equal(completed.review_status, 'Accepted', 'Policy adoption incomplete; no manual acceptance fabricated.');
  await browser.close();
})().catch(async error => {
  event('recorder_failure', { message: error.message });
  if (context) { try { await getExact('project', 'project-failure-api-original.json'); } catch (failure) { captureErrors.push(failure.message); } if (trackedId) try { await getExact('drc-workflow/runs/' + encodeURIComponent(trackedId), 'run-failure-api-original.json'); } catch (failure) { captureErrors.push(failure.message); } }
  if (page) try { await page.screenshot({ path: path.join(output, 'drc-workflow-failure.png'), fullPage: true }); } catch (failure) { captureErrors.push(failure.message); }
  fs.writeFileSync(path.join(output, 'gui-operation-failure.json'), JSON.stringify(provenance({ error: error.message, last_observed_status: lastObservedStatus, finished_at: at() }), null, 2) + '\n'); console.error(error.stack || error); console.error('Evidence retained: ' + output); if (browser) await browser.close(); process.exitCode = 1;
});
