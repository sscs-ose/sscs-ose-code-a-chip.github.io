/** Explicit S08 GUI actions. No model call occurs for preview/observe phases. */
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const assert = require('node:assert/strict');
const { chromium } = require(process.env.HULLCIRQ_PLAYWRIGHT_PATH || 'playwright');
const root = path.resolve(__dirname, '..');
const url = process.env.HULLCIRQ_NPU_URL || 'http://127.0.0.1:8768/';
const phase = process.argv[2];
const waitMs = Number(process.env.HULLCIRQ_GLOBAL_WAIT_MS || 720000);
assert.ok(Number.isFinite(waitMs) && waitMs > 0, 'HULLCIRQ_GLOBAL_WAIT_MS must be positive.');
assert.ok(['preview', 'generate', 'repair', 'observe', 'cancel'].includes(phase), 'Choose preview, generate, repair, observe or cancel.');
const output = path.join(path.resolve(root, process.env.HULLCIRQ_GUI_OUTPUT_ROOT || '.work/m2e/global-gui-operations'), new Date().toISOString().replace(/[:.]/g, '-') + '-global-' + phase);
fs.mkdirSync(output, { recursive: true });
const actions = [], errors = [], downloads = [];
let browser, checksView;
(async () => {
  browser = await chromium.launch({ channel: 'msedge', headless: true });
  const context = await browser.newContext({ viewport: { width: 1500, height: 1100 }, acceptDownloads: true });
  const page = await context.newPage(); page.setDefaultTimeout(Math.min(120000, waitMs));
  page.on('pageerror', e => errors.push(e.message));
  const test = id => page.getByTestId(id);
  const endpoint = route => new URL('/api/' + route, url).href;
  async function getExact(route, filename) {
    const response = await context.request.get(endpoint(route), { timeout: 120000 });
    assert.ok(response.ok(), 'Read failed: ' + route + ' ' + response.status());
    const raw = await response.body();
    if (filename) fs.writeFileSync(path.join(output, filename), raw);
    // Parsed numbers are used only for UI/status assertions, never to write
    // authoritative JSON snapshots. Originals are the response bytes above.
    return JSON.parse(raw.toString('utf8'));
  }
  async function action(id, route) {
    const [response] = await Promise.all([
      page.waitForResponse(r => r.url().endsWith('/api/' + route) && r.request().method() === 'POST'), test(id).click(),
    ]);
    const record = { actor: 'development_assistant_gui_automation', control: id, route, at: new Date().toISOString(), status: response.status() };
    actions.push(record);
    // Do not repeat a mutation after a response/body-cache error. The caller
    // can observe the already recorded attempt with the observe phase.
    if (!response.ok()) throw Error(route + ' failed: ' + response.status() + ' ' + await response.text().catch(() => 'Body unavailable; mutation was not retried.'));
  }
  async function download(id, kind) {
    const [item] = await Promise.all([page.waitForEvent('download'), test(id).click()]);
    const file = path.join(output, kind + (kind === 'top' ? '.v' : '.json'));
    await item.saveAs(file); assert.equal(await item.failure(), null);
    const raw = fs.readFileSync(file);
    downloads.push({ control: id, kind, filename: path.basename(file), bytes: raw.length, sha256: crypto.createHash('sha256').update(raw).digest('hex') });
  }
  await page.goto(url); await test('stage-global_rtl_generation').waitFor();
  await test('stage-global_rtl_generation').click();
  await test('global-context-preview').waitFor();
  let state = (await getExact('global-generation')).global_generation;
  if (['preview', 'generate', 'repair'].includes(phase)) {
    assert.equal(state.ready, true, state.blocked_reason || 'All six adopted sources are required.');
    assert.ok(!state.jobs.some(j => ['Queued', 'Running'].includes(j.execution_status)), 'A global request is already active.');
    if (phase === 'repair') {
      assert.ok(state.jobs.at(-1)?.rtl, 'An earlier global RTL is required for repair.');
      await test('global-operation').selectOption('repair');
      const chosen = process.env.HULLCIRQ_GLOBAL_BASE_JOB || state.jobs.at(-1).id;
      await test('global-base-job').selectOption(chosen);
      await test('global-instruction').fill(process.env.HULLCIRQ_GLOBAL_INSTRUCTION || 'Correct the recorded public-boundary or full-system failures. Preserve all adopted modules, ports, original job inputs and saved verification.');
    } else if (process.env.HULLCIRQ_GLOBAL_INSTRUCTION) {
      await test('global-instruction').fill(process.env.HULLCIRQ_GLOBAL_INSTRUCTION);
    }
    await action('global-context-preview', 'global-generation/context');
    await test('global-preview').waitFor();
    await download('global-download-preview', 'preview');
    // UI download is original backend response text, never JSON.stringify of
    // a browser-rounded 134-bit configuration word.
    const preview = JSON.parse(fs.readFileSync(path.join(output, 'preview.json'), 'utf8'));
    assert.equal(preview.source_manifest.nodes.length, 6);
    assert.equal(preview.source_manifest.internal_nets_used_as_API, false);
    const sourceIds = preview.source_manifest.nodes.map(n => ({ node_id: n.node_id, candidate_id: n.candidate_id, synthesis_run_id: n.synthesis_run_id, netlist_run_id: n.netlist_run_id, spec_id: n.spec_id }));
    actions.push({ actor: 'development_assistant_gui_automation', control: 'global-preview', action: 'inspected_complete_frozen_source_manifest_and_prompt', revision_id: preview.revision_id, context_id: preview.context_id, source_ids: sourceIds, vector_hash: preview.verification_plan.vector_hash, public_boundary_vector_hash: preview.verification_plan.public_boundary_vector_hash, at: new Date().toISOString() });
    await page.screenshot({ path: path.join(output, 'global-context-preview.png'), fullPage: true });
    if (phase !== 'preview') {
      await page.waitForFunction(() => !document.querySelector('[data-testid="global-generate"]')?.disabled);
      await action('global-generate', 'global-generation/start');
      state = (await getExact('global-generation')).global_generation;
      console.log(JSON.stringify({ event: 'global_local_model_started', id: state.jobs.at(-1)?.id, output }));
    }
  }
  if (phase === 'cancel') {
    assert.ok(state.jobs.some(j => ['Queued', 'Running'].includes(j.execution_status)), 'No active global request exists.');
    await action('global-cancel', 'global-generation/cancel');
  }
  if (phase !== 'preview') {
    state = (await getExact('global-generation')).global_generation;
    const tracked = state.jobs.at(-1); assert.ok(tracked, 'No global attempt exists to observe.');
    const deadline = Date.now() + waitMs;
    let completedJob;
    while (true) {
      const job = await getExact('global-generation/jobs/' + tracked.id);
      if (!['Queued', 'Running'].includes(job.execution_status) && job.finished_at) { completedJob = job; break; }
      assert.ok(Date.now() < deadline, 'Global attempt remains active after the bounded wait; partial evidence is retained.');
      await new Promise(resolve => setTimeout(resolve, 1500));
    }
    await test('global-refresh').click();
    // The same job ID is already visible while Running. Wait for the actual
    // terminal status after the asynchronous refresh before capturing the UI.
    await page.waitForFunction(expected => {
      const status = document.querySelector('[data-testid="global-job-status"]')?.textContent || '';
      return [expected.id, expected.execution_status, expected.validation_status, expected.review_status].every(value => status.includes(value));
    }, { id: tracked.id, execution_status: completedJob.execution_status, validation_status: completedJob.validation_status, review_status: completedJob.review_status });
    await test('global-tab-checks').click();
    const displayed = await test('global-result-content').evaluate(node => ({
      text: node.textContent, white_space: getComputedStyle(node).whiteSpace,
      overflow_wrap: getComputedStyle(node).overflowWrap,
    }));
    checksView = {
      rendered_characters: displayed.text.length,
      white_space: displayed.white_space,
      overflow_wrap: displayed.overflow_wrap,
      complete_display_record_present: displayed.text === JSON.stringify({
        checks: completedJob.checks, diagnostics: completedJob.diagnostics, error: completedJob.error,
      }, null, 2),
      display_integer_precision: 'Browser Number precision; exact JSON downloads retain original backend bytes.',
    };
    await page.screenshot({ path: path.join(output, 'global-executed-checks.png'), fullPage: true });
    for (const [id, kind] of [['global-download-job', 'job'], ['global-download-context', 'context'], ['global-download-source-manifest', 'source-manifest'], ['global-download-plan', 'verification-plan']]) await download(id, kind);
    const job = await getExact('global-generation/jobs/' + tracked.id, 'job-api-original.json');
    if (job.rtl) await download('global-download-rtl', 'top');
    console.log(JSON.stringify({ event: 'global_candidate_observed', id: job.id, revision_id: job.revision_id, execution_status: job.execution_status, validation_status: job.validation_status, review_status: job.review_status, freshness: job.freshness, original_output_count: job.checks?.actual_output_transfers?.length || 0, observed_pe_count: job.checks?.actual_pe_lane_transfers?.length || 0, output }));
  }
  assert.deepEqual(errors, []);
  fs.writeFileSync(path.join(output, 'gui-operation.json'), JSON.stringify({ actor: 'development_assistant_gui_automation', phase, url, actions, downloads, checks_view: checksView, page_errors: errors, scope: 'GUI actions and original backend text downloads; no manual human adoption was fabricated', finished_at: new Date().toISOString() }, null, 2) + '\n');
  console.log(JSON.stringify({ status: 'Passed', phase, output, downloads: downloads.length }));
  await browser.close();
})().catch(async error => {
  fs.writeFileSync(path.join(output, 'gui-operation-failure.json'), JSON.stringify({ actor: 'development_assistant_gui_automation', phase, actions, downloads, page_errors: errors, error: error.message, mutation_retry: false }, null, 2) + '\n');
  console.error(error.stack || error); if (browser) await browser.close(); process.exitCode = 1;
});
