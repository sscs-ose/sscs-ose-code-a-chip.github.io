/** S11 GUI evidence recorder. Observation never starts or reviews execution. */
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const assert = require('node:assert/strict');
const { chromium } = require(process.env.HULLCIRQ_PLAYWRIGHT_PATH || 'playwright');
const sidebarStatus = require('./gui_recorder_status.cjs');

const root = path.resolve(__dirname, '..');
const url = process.env.HULLCIRQ_NPU_URL || 'http://127.0.0.1:8768/';
const phase = process.argv[2];
assert.ok(['layout', 'revalidate-layout', 'observe-layout'].includes(phase), 'Choose layout, revalidate-layout or observe-layout.');
const observe = phase === 'observe-layout';
const revalidate = phase === 'revalidate-layout';
const waitMs = Number(process.env.HULLCIRQ_LAYOUT_WAIT_MS || 7200000);
assert.ok(Number.isFinite(waitMs) && waitMs > 0, 'HULLCIRQ_LAYOUT_WAIT_MS must be a positive number of milliseconds.');
const output = path.join(path.resolve(root, process.env.HULLCIRQ_GUI_OUTPUT_ROOT || '.work/m2g/gui-operations'), new Date().toISOString().replace(/[:.]/g, '-') + '-' + phase + '-' + crypto.randomBytes(4).toString('hex'));
fs.mkdirSync(output, { recursive: true });
const JSON_FIELDS = ['source-manifest', 'verification-plan', 'settings', 'runtime-configuration', 'artifact-manifest'];
const FILE_IDS = new Set(['config', 'sdc', 'metrics', 'def', 'gds', 'png', 'netlist', 'final-state', 'tool-versions', 'input-manifest', 'rtl-top', ...['control', 'buffer', 'scheduler', 'pe', 'post', 'fifo'].map(id => 'rtl-node-' + id)]);
const BINARY = new Set(['def', 'gds', 'png']);
const extensions = { sdc: 'sdc', def: 'def', gds: 'gds', png: 'png', netlist: 'v', 'rtl-top': 'v' };
const actions = [], errors = [], downloads = [], captureErrors = [], requests = [];
const sha = raw => crypto.createHash('sha256').update(raw).digest('hex');
const active = run => ['Queued', 'Running'].includes(run.execution_status);
let browser, context, page, trackedId, priorRunId, beforeSources, completed, finalProject, allowedWrites = 0, lastObservedStatus;
let mutationPath = revalidate ? null : '/api/physical-workflow/runs';
const endpoint = route => new URL('/api/' + route, url).href;
const test = id => page.getByTestId(id);
const at = () => new Date().toISOString();
function event(kind, detail) { fs.appendFileSync(path.join(output, 'events.jsonl'), JSON.stringify({ at: at(), kind, ...detail }) + '\n'); }
function provenance(extra = {}) {
  return { actor: 'development_assistant_gui_automation', phase, stage: 'layout', url, run_id: trackedId,
    frozen_source_ids: beforeSources, actions, requests, downloads, page_errors: errors, capture_errors: captureErrors,
    model_calls: 0, allowed_mutation_requests: allowedWrites, mutation_retry: false,
    ...(revalidate ? { prior_run_id: priorRunId, operation_kind: 'saved_outputs_no_new_tool_start', new_eda_tool_starts: 0, new_model_calls: 0 } : {}),
    scope: 'GUI physical evidence and exact backend downloads. Revalidate-layout checks saved completed outputs without a new EDA/model start and preserves the failed original. Observe-layout performs read-only navigation/downloads only. Authorized policy adoption is not a manual human click. S11 does not imply S12 DRC, S13 LVS or S14 dynamic SDF verification.', ...extra };
}
function checkpoint() { fs.writeFileSync(path.join(output, 'gui-operation-progress.json'), JSON.stringify(provenance({ last_observed_status: lastObservedStatus, updated_at: at() }), null, 2) + '\n'); }
async function getExact(route, filename, binary = false) {
  const response = await context.request.get(endpoint(route), { timeout: 120000 });
  const raw = await response.body();
  if (filename) fs.writeFileSync(path.join(output, filename), raw);
  event('read_response', { route, status: response.status(), bytes: raw.length, sha256: sha(raw), filename });
  assert.ok(response.ok(), 'Read failed: ' + route + ' ' + response.status());
  // Parsed values serve status/identity assertions only. Authoritative JSON
  // evidence is the original response bytes, including integers above 53 bits.
  return { raw, value: binary ? undefined : JSON.parse(raw.toString('utf8')) };
}
function sources(saved) {
  const job = saved.global_generation?.jobs?.at(-1);
  const adopted = stage => saved.global_workflow?.runs?.find(run => run.id === saved.global_workflow.stages?.find(item => item.stage_id === stage)?.accepted_run_id);
  const synthesis = adopted('global_synthesis'), netlist = adopted('global_netlist_simulation');
  const current = run => run?.execution_status === 'Completed' && run.validation_status === 'Passed' && run.review_status === 'Accepted' && run.freshness === 'Current';
  if (!current(job) || !current(synthesis) || !current(netlist) || synthesis.global_job_id !== job.id || netlist.global_job_id !== job.id || (netlist.synthesis_run_id || netlist.prior_run_id) !== synthesis.id) return null;
  return { revision_id: saved.revision.id, global_job_id: job.id, synthesis_run_id: synthesis.id, netlist_run_id: netlist.id };
}
async function clickReadOnly(id, action) {
  const record = { control: id, action, at: at(), mutation: false };
  actions.push(record); event('gui_action', record); checkpoint();
  await test(id).click(); record.outcome = 'Completed';
}
async function waitSourcesInUI(saved, terminalRun) {
  const sourceIds = sources(saved);
  const stages = saved.workflow.map(stage => ({ id: stage.id, status: sidebarStatus(stage) }));
  await page.waitForFunction(expected => {
    const lineage = document.querySelector('[data-testid="physical-workflow-lineage"]')?.textContent || '';
    const sourceReady = expected.sources ? Object.values(expected.sources).every(value => lineage.includes(value)) : lineage.includes('Not available');
    const sidebarsReady = expected.stages.every(stage => document.querySelector(`[data-testid="stage-${stage.id}"]`)?.textContent.includes(stage.status));
    const evidence = document.querySelector('[data-testid="physical-workflow-status"]')?.textContent || '';
    return sourceReady && sidebarsReady && (!expected.run || [expected.run.id, expected.run.execution_status, expected.run.validation_status, expected.run.review_status, expected.run.freshness].every(value => evidence.includes(value)));
  }, { sources: sourceIds, stages, run: terminalRun ? { id: terminalRun.id, execution_status: terminalRun.execution_status, validation_status: terminalRun.validation_status, review_status: terminalRun.review_status, freshness: terminalRun.freshness } : null });
  const record = { action: 'inspected_current_source_ids_and_sidebar_status', source_ids: sourceIds, sidebar_stages: stages, terminal_run_id: terminalRun?.id, at: at(), mutation: false };
  actions.push(record); event('gui_inspection', record); checkpoint();
}
async function download(id, kind, extension, route, format, descriptor) {
  const originalFilename = kind + '-api-original.' + (format === 'raw' ? extension : 'json');
  const original = await getExact(route, originalFilename, format === 'raw');
  const expected = format === 'text' ? Buffer.from(original.value, 'utf8') : original.raw;
  if (format === 'text') assert.equal(typeof original.value, 'string', 'Text artifact must be a backend JSON string.');
  const record = { control: id, action: 'download_saved_artifact', kind, at: at(), mutation: false };
  actions.push(record); event('gui_action', record); checkpoint();
  const [item] = await Promise.all([page.waitForEvent('download'), test(id).click()]);
  const filename = kind + '.' + extension;
  await item.saveAs(path.join(output, filename));
  assert.equal(await item.failure(), null);
  const raw = fs.readFileSync(path.join(output, filename));
  assert.ok(raw.equals(expected), 'GUI download differs from exact backend bytes: ' + kind);
  if (descriptor) {
    assert.equal(raw.length, descriptor.bytes, 'Artifact size differs from saved manifest: ' + kind);
    assert.equal(sha(raw), descriptor.sha256, 'Artifact hash differs from saved manifest: ' + kind);
  }
  Object.assign(record, { outcome: 'Downloaded and byte-compared', filename });
  const result = { control: id, kind, filename, bytes: raw.length, sha256: sha(raw), exact_backend_match: true,
    response_format: format, backend_response_filename: originalFilename, backend_response_bytes: original.raw.length,
    backend_response_sha256: sha(original.raw), ...(descriptor ? { manifest_sha256: descriptor.sha256, manifest_bytes: descriptor.bytes, exact_manifest_match: true } : {}) };
  downloads.push(result); event('gui_download', result); checkpoint();
}
async function captureTerminal() {
  await page.waitForFunction(() => !document.querySelector('[data-testid="physical-workflow-refresh"]')?.disabled);
  await clickReadOnly('physical-workflow-refresh', 'read_saved_project_without_reexecuting');
  await test('physical-workflow-run-' + trackedId).waitFor();
  await clickReadOnly('physical-workflow-run-' + trackedId, 'select_recorded_run');
  await waitSourcesInUI(finalProject, completed);
  const png = completed.artifacts?.find(item => item.id === 'png');
  if (png) await page.waitForFunction(() => { const image = document.querySelector('[data-testid="physical-workflow-layout-image"]'); return image?.complete && image.naturalWidth > 0; });
  await page.screenshot({ path: path.join(output, 'physical-workflow-terminal.png'), fullPage: true });
  if (png) {
    await test('physical-workflow-preview').screenshot({ path: path.join(output, 'physical-layout-preview.png') });
    // Keyboard operations exercise the real zoom widget without changing any
    // circuit input, source, adoption record or execution configuration.
    await test('physical-workflow-zoom').focus(); await test('physical-workflow-zoom').press('Home');
    for (let i = 0; i < 7; i++) await test('physical-workflow-zoom').press('ArrowRight');
    assert.equal(await test('physical-workflow-zoom').inputValue(), '200');
    actions.push({ control: 'physical-workflow-zoom', action: 'preview_zoom_200_percent', at: at(), mutation: false });
    await test('physical-workflow-preview').screenshot({ path: path.join(output, 'physical-layout-zoom-200.png') });
    await clickReadOnly('physical-workflow-fit', 'restore_preview_fit_width');
    assert.equal(await test('physical-workflow-zoom').inputValue(), '100');
  }
  const prefix = 'artifacts/physical-workflow/' + encodeURIComponent(trackedId) + '/';
  const attempt = async work => { try { await work(); } catch (error) { captureErrors.push(error.message); event('capture_error', { message: error.message }); checkpoint(); } };
  await attempt(() => download('physical-workflow-download-run', 'run', 'json', 'physical-workflow/runs/' + encodeURIComponent(trackedId), 'json'));
  for (const id of JSON_FIELDS) await attempt(() => download('physical-workflow-download-' + id, id, 'json', prefix + id, 'json'));
  for (const item of completed.artifacts || []) {
    if (!FILE_IDS.has(item.id) || item.url !== '/api/' + prefix + item.id) { captureErrors.push('Artifact URL or ID is outside the fixed allowlist: ' + item.id); continue; }
    const extension = extensions[item.id] || (item.id.startsWith('rtl-') ? 'v' : 'json');
    await attempt(() => download('physical-workflow-download-' + item.id, item.id, extension, prefix + item.id, BINARY.has(item.id) ? 'raw' : 'text', item));
  }
}

(async () => {
  browser = await chromium.launch({ channel: 'msedge', headless: true });
  context = await browser.newContext({ viewport: { width: 1500, height: 1100 }, acceptDownloads: true });
  // Enforce phase scope at the network boundary as well as in the UI helper.
  // Even an accidental click cannot issue a model/review/repeated-start POST.
  await context.route('**/api/**', async route => {
    const request = route.request(), pathname = new URL(request.url()).pathname;
    if (['GET', 'HEAD'].includes(request.method())) { await route.continue(); return; }
    const allowed = !observe && request.method() === 'POST' && pathname === mutationPath && allowedWrites === 0;
    const record = { method: request.method(), path: pathname, allowed, at: at(), original_request_body: request.postData() };
    requests.push(record); event('mutation_request', record);
    if (!allowed) { captureErrors.push('Blocked an unexpected mutation request: ' + request.method() + ' ' + pathname); await route.abort('blockedbyclient'); return; }
    allowedWrites += 1; fs.writeFileSync(path.join(output, (revalidate ? 'revalidation' : 'start') + '-request-body-original.json'), request.postData() || ''); checkpoint(); await route.continue();
  });
  page = await context.newPage(); page.setDefaultTimeout(Math.min(120000, waitMs));
  page.on('pageerror', error => { errors.push(error.message); event('page_error', { message: error.message }); });
  const original = (await getExact('project', 'project-before-api-original.json')).value;
  beforeSources = sources(original);
  const before = (await getExact('physical-workflow', 'physical-workflow-before-api-original.json')).value.physical_workflow;
  await page.goto(url); await test('stage-layout').waitFor();
  await clickReadOnly('stage-layout', 'open_layout_stage'); await test('physical-workflow-run').waitFor();
  await waitSourcesInUI(original);
  await page.screenshot({ path: path.join(output, 'physical-workflow-before.png'), fullPage: true });
  trackedId = process.env.HULLCIRQ_PHYSICAL_WORKFLOW_RUN_ID;
  if (!observe) {
    assert.equal(before.ready, true, before.blocked_reason || 'Exact current adopted S08/S09/S10 sources are required.');
    assert.equal(before.tool_ready, true, before.tool_blocked_reason || 'A pinned physical runtime is required.');
    assert.ok(beforeSources, 'A complete adopted source baseline is required.');
    assert.ok(!before.runs.some(active), 'A physical run is already active.');
    let control = 'physical-workflow-run';
    if (revalidate) {
      priorRunId = trackedId || before.latest_run_id;
      const previous = before.runs.find(run => run.id === priorRunId);
      assert.ok(previous && priorRunId === before.latest_run_id && previous.freshness === 'Current' && !active(previous) && (previous.execution_status === 'Failed' || previous.validation_status === 'Failed'), 'Choose the latest failed run for current sources.');
      assert.equal(previous.evidence_kind, 'trusted_fixed_tool_execution');
      assert.equal(previous.checks?.executed, true); assert.equal(previous.checks?.exit_code, 0);
      assert.notEqual(previous.checks?.cleanup_unresolved, true, 'Unverified termination blocks revalidation.');
      await getExact('physical-workflow/runs/' + encodeURIComponent(priorRunId), 'prior-run-api-original.json');
      await clickReadOnly('physical-workflow-run-' + priorRunId, 'select_original_failed_run_for_saved_output_recheck');
      control = 'physical-workflow-revalidate';
      mutationPath = '/api/physical-workflow/runs/' + encodeURIComponent(priorRunId) + '/revalidate';
    }
    await page.waitForFunction(id => !document.querySelector(`[data-testid="${id}"]`)?.disabled, control);
    const action = { control, action: revalidate ? 'recheck_saved_outputs_without_eda_or_model_start' : 'start_exactly_one_physical_execution', ...(revalidate ? { prior_run_id: priorRunId, new_eda_tool_starts: 0, new_model_calls: 0 } : {}), frozen_source_ids: beforeSources, at: at(), outcome: 'Unknown; mutation will not be retried' };
    actions.push(action); event('gui_action', action); checkpoint();
    const [response] = await Promise.all([page.waitForResponse(item => new URL(item.url()).pathname === mutationPath && item.request().method() === 'POST'), test(control).click()]);
    // The POST returns a full project envelope, which can exceed Chromium's
    // inspector response cache. Never read its network Response body: the
    // status/request identify the one mutation, and the APIRequestContext GET
    // below retains authoritative saved bytes without replaying that POST.
    const responseMetadata = { status: response.status(), url: response.url(), original_request_body: response.request().postData(), response_body_captured: false,
      reason: 'Full project responses may exceed the browser inspector cache; authoritative saved state is captured by the following read-only API request.' };
    const responseMetadataFilename = (revalidate ? 'revalidation' : 'start') + '-response-metadata.json';
    fs.writeFileSync(path.join(output, responseMetadataFilename), JSON.stringify(responseMetadata, null, 2) + '\n');
    Object.assign(action, { status: response.status(), outcome: response.ok() ? 'Response received' : 'Rejected response', response_body_captured: false, response_metadata_filename: responseMetadataFilename }); checkpoint();
    assert.ok(response.ok(), 'Physical operation was rejected (' + response.status() + '); the mutation is not retried.');
    const after = (await getExact('physical-workflow', 'physical-workflow-started-api-original.json')).value.physical_workflow;
    const started = after.runs.find(run => run.id === after.latest_run_id);
    assert.ok(started && !before.runs.some(run => run.id === started.id), 'No distinct recorded run was found. The start request is not retried.');
    trackedId = started.id;
    for (const [key, value] of Object.entries(beforeSources)) assert.equal(started[key], value, 'Started run changed frozen source: ' + key);
    if (revalidate) { assert.equal(started.prior_run_id, priorRunId); assert.equal(started.execution_kind, 'saved_outputs_no_new_tool_start'); }
    console.log(JSON.stringify({ event: revalidate ? 'physical_saved_outputs_revalidation_started' : 'physical_layout_run_started', id: trackedId, ...(revalidate ? { prior_run_id: priorRunId } : {}), frozen_source_ids: beforeSources, output }));
  } else {
    trackedId ||= before.latest_run_id;
    assert.ok(trackedId && before.runs.some(run => run.id === trackedId && run.stage_id === 'layout'), 'No matching recorded layout run exists to observe.');
  }
  const deadline = Date.now() + waitMs;
  while (true) {
    completed = (await getExact('physical-workflow/runs/' + encodeURIComponent(trackedId), 'last-run-api-original.json')).value;
    let terminal = !active(completed) && !!completed.finished_at, policyPending = false;
    if (terminal) {
      finalProject = (await getExact('project', 'project-terminal-api-original.json')).value;
      completed = finalProject.physical_workflow.runs.find(run => run.id === trackedId) || completed;
      terminal = !active(completed) && !!completed.finished_at;
      policyPending = finalProject.review_policy?.mode === 'accept_on_pass' && finalProject.review_policy?.user_authorized === true
        && !finalProject.physical_workflow.storage_error && completed.execution_status === 'Completed'
        && completed.validation_status === 'Passed' && completed.review_status === 'Awaiting Review' && completed.freshness === 'Current'
        && !completed.error && !(completed.diagnostics || []).some(item => item.code === 'automatic_adoption_blocked');
    }
    const status = { id: trackedId, execution_status: completed.execution_status, validation_status: completed.validation_status, review_status: completed.review_status, freshness: completed.freshness, policy_pending: policyPending };
    if (JSON.stringify(status) !== JSON.stringify(lastObservedStatus)) { lastObservedStatus = status; event('observed_status', status); checkpoint(); console.log(JSON.stringify({ event: 'physical_layout_progress', ...status })); }
    if (terminal && !policyPending) break;
    assert.ok(Date.now() < deadline, 'Physical execution or authorized adoption exceeded the bounded wait. Partial evidence is retained; execution is not restarted.');
    await new Promise(resolve => setTimeout(resolve, 1500));
  }
  await captureTerminal();
  const terminal = await getExact('physical-workflow/runs/' + encodeURIComponent(trackedId), 'run-api-original.json');
  completed = terminal.value;
  if (revalidate) {
    assert.equal(completed.prior_run_id, priorRunId); assert.equal(completed.execution_kind, 'saved_outputs_no_new_tool_start');
    assert.equal(completed.checks.execution_reused, true); assert.equal(completed.checks.revalidated_from_run_id, priorRunId);
    assert.equal(completed.checks.revalidation_tool_starts, 0); assert.equal(completed.checks.revalidation_model_calls, 0);
    assert.equal(completed.previous_result_sha256, completed.checks.previous_result_sha256);
    const beforeOriginal = fs.readFileSync(path.join(output, 'prior-run-api-original.json'));
    const afterOriginal = await getExact('physical-workflow/runs/' + encodeURIComponent(priorRunId), 'prior-run-after-api-original.json');
    assert.ok(beforeOriginal.equals(afterOriginal.raw), 'The original failed run was changed by revalidation.');
  }
  if (!observe) assert.deepEqual(sources(finalProject), beforeSources, 'The adopted source baseline changed during physical execution.');
  assert.equal(allowedWrites, observe ? 0 : 1, 'Unexpected number of mutation requests.');
  assert.deepEqual(errors, []); assert.deepEqual(captureErrors, []);
  const report = provenance({ capture_status: 'Passed', frozen_run_source_ids: Object.fromEntries(['revision_id', 'global_job_id', 'synthesis_run_id', 'netlist_run_id'].map(key => [key, completed[key]])), execution_status: completed.execution_status, validation_status: completed.validation_status, review_status: completed.review_status, freshness: completed.freshness, finished_at: at() });
  fs.writeFileSync(path.join(output, 'gui-operation.json'), JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify({ status: 'Captured', capture_status: 'Passed', phase, id: trackedId, execution_status: completed.execution_status, validation_status: completed.validation_status, review_status: completed.review_status, freshness: completed.freshness, output, downloads: downloads.length }));
  assert.ok(completed.execution_status === 'Completed' && completed.validation_status === 'Passed' && completed.freshness === 'Current', 'The physical run did not pass for current sources. Its failure, logs, artifacts and GUI evidence were retained; no restart was attempted.');
  if (finalProject.review_policy?.mode === 'accept_on_pass' && finalProject.review_policy?.user_authorized === true) assert.equal(completed.review_status, 'Accepted', 'Required policy adoption did not complete; no manual acceptance was fabricated.');
  await browser.close();
})().catch(async error => {
  event('recorder_failure', { message: error.message });
  if (context) {
    try { await getExact('project', 'project-failure-api-original.json'); } catch (captureError) { captureErrors.push(captureError.message); }
    if (trackedId) try { await getExact('physical-workflow/runs/' + encodeURIComponent(trackedId), 'run-failure-api-original.json'); } catch (captureError) { captureErrors.push(captureError.message); }
  }
  if (page) try { await page.screenshot({ path: path.join(output, 'physical-workflow-failure.png'), fullPage: true }); } catch (captureError) { captureErrors.push(captureError.message); }
  fs.writeFileSync(path.join(output, 'gui-operation-failure.json'), JSON.stringify(provenance({ error: error.message, last_observed_status: lastObservedStatus, finished_at: at() }), null, 2) + '\n');
  console.error(error.stack || error); console.error('Evidence retained: ' + output);
  if (browser) await browser.close(); process.exitCode = 1;
});
