/* Optional M1 regression check against a fresh isolated service.
 * Set HULLCIRQ_TEST_URL and, if needed, HULLCIRQ_PLAYWRIGHT_PATH.
 * Requires Playwright and an installed Microsoft Edge; neither is a GUI dependency.
 */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require(process.env.HULLCIRQ_PLAYWRIGHT_PATH || 'playwright');
const root = path.resolve(__dirname, '..');
const url = process.env.HULLCIRQ_TEST_URL || 'http://127.0.0.1:8767/';
const output = path.resolve(process.env.HULLCIRQ_M1_GUI_OUTPUT || path.join(root, '.work', 'm1', 'browser-check', `run-${new Date().toISOString().replace(/[:.]/g, '-')}`));
fs.mkdirSync(output, { recursive: true });

(async () => {
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 1100 } });
  const page = await context.newPage();
  const errors = [], checks = [];
  page.on('pageerror', error => errors.push(error.message));
  const test = name => checks.push(name);
  const button = id => page.getByTestId(id);
  // Transfer JSON as text so the browser-automation serializer cannot interpret
  // an opaque '__proto__' key as an object prototype.
  const envelope = async () => JSON.parse(await page.evaluate(async () => (await fetch('/api/project')).text()));
  const stage = async id => { await button(`stage-${id}`).click(); };
  const save = async () => {
    await page.locator('#stage-title').click();
    if (await button('save-project').isEnabled()) {
      const response = page.waitForResponse(r => r.url().endsWith('/api/save'));
      await button('save-project').click();
      assert.equal((await response).status(), 200);
    }
    await page.waitForFunction(() => document.querySelector('#save-state').textContent.includes('Saved locally'));
  };
  const verify = async id => {
    const response = page.waitForResponse(r => r.url().endsWith('/api/validate'));
    await button('run-verification').click();
    assert.equal((await response).status(), 200);
    await button('accept-continue').waitFor();
    const state = await envelope();
    return state.runs.find(run => run.id === state.workflow.find(s => s.id === id).latest_run_id);
  };
  const accept = async next => {
    const response = page.waitForResponse(r => r.url().endsWith('/api/review'));
    await button('accept-continue').click();
    assert.equal((await response).status(), 200);
    await page.waitForFunction(id => document.querySelector(`[data-stage-id="${id}"]`).getAttribute('aria-current') === 'step', next);
  };
  const importJson = async design => {
    const response = page.waitForResponse(r => r.url().endsWith('/api/import'));
    await page.locator('#import-file').setInputFiles({ name: 'fixture.json', mimeType: 'application/json', buffer: Buffer.from(JSON.stringify(design)) });
    assert.equal((await response).status(), 200);
    await page.waitForFunction(() => document.querySelector('#save-state').textContent.includes('Saved locally'));
  };
  try {
    await page.goto(url);
    await button('stage-global_settings').waitFor();
    assert.equal((await envelope()).runs.length, 0, 'Use a fresh isolated --data-dir; never reuse a working project.');
    assert.equal(await page.locator('html').getAttribute('lang'), 'en');
    assert.equal(await page.locator('#stage-tabs button').count(), 14);
    assert.equal(await page.locator('.brand img').evaluate(img => img.complete && img.naturalWidth > 0), true);
    test('English 14-stage navigation and provided logo');

    const first = await verify('global_settings');
    assert.equal(first.validation_status, 'Passed');
    assert.equal(first.review_status, 'Awaiting Review');
    assert.equal(await page.locator('#stage-title').textContent(), 'Global Settings');
    await button('review-note').fill('Reviewed the M1 input settings. No circuit execution.');
    await accept('graph_editor');
    test('Pass waits for an explicit human acceptance');

    assert.equal(await page.locator('[data-node-id]').count(), 2);
    assert.equal(await page.locator('[data-edge-id]').count(), 1);
    const beforeDrag = await envelope();
    const box = await button('node-node-producer').boundingBox();
    await page.mouse.move(box.x + 90, box.y + 20);
    await page.mouse.down(); await page.mouse.move(box.x + 120, box.y + 45, { steps: 6 }); await page.mouse.up();
    await save();
    const moved = await envelope();
    assert.notDeepEqual(moved.design.layout.nodes, beforeDrag.design.layout.nodes);
    assert.equal(moved.revision.semantic_hash, beforeDrag.revision.semantic_hash);
    assert.equal(moved.workflow[0].review_status, 'Accepted');
    test('SVG drag saves layout without invalidating semantic approval');

    await button('tree-node-consumer').click();
    await button('port-width-port-consumer-data').fill('16');
    await save();
    const failed = await verify('graph_editor');
    assert.equal(failed.validation_status, 'Failed');
    assert(failed.diagnostics.some(d => d.code === 'edge_width_mismatch'));
    assert.equal(await button('accept-continue').isDisabled(), true);
    await page.locator('[data-diagnostic-code="edge_width_mismatch"]').click();
    await button('review-note').fill('Repair the consumer width to match the producer.');
    const requested = page.waitForResponse(r => r.url().endsWith('/api/review'));
    await button('request-changes').click(); assert.equal((await requested).status(), 200);
    await button('review-note').fill('Return to check the shared settings before repair.');
    const returned = page.waitForResponse(r => r.url().endsWith('/api/review'));
    await button('return-to-stage').click(); assert.equal((await returned).status(), 200);
    await page.waitForFunction(() => document.querySelector('#stage-title').textContent === 'Global Settings');
    await stage('graph_editor'); await button('tree-node-consumer').click();
    await button('port-width-port-consumer-data').fill('32'); await save();
    assert.equal((await verify('graph_editor')).validation_status, 'Passed');
    await accept('specifications');
    test('Width failure, linked diagnostic, feedback, return, repair and review');

    await button('node-behavior-node-consumer').fill('M1 edited input: retain signed values in order under valid/ready stalls; no RTL exists.');
    await save(); assert.equal((await verify('specifications')).validation_status, 'Passed');
    await accept('local_rtl_generation');
    assert.equal(await button('run-verification').isDisabled(), true);
    assert.equal(await button('generate-node').isDisabled(), true);
    assert.equal((await envelope()).implementation.llm_connected, false);
    await stage('local_synthesis');
    assert.match(await page.locator('#stage-content').textContent(), /current, verified and accepted RTL candidate|not implemented/i);
    assert.equal(await button('run-verification').isDisabled(), true);
    test('Specifications editable; generation gated without profile and node synthesis gated without an accepted verified candidate');

    await stage('graph_editor'); await button('tree-node-consumer').click();
    await button('node-name').fill('Consumer renamed');
    await button('parent-node').selectOption('node-producer'); await save();
    const hierarchy = await envelope();
    assert.equal(hierarchy.design.nodes[1].id, 'node-consumer');
    assert.equal(hierarchy.design.nodes[1].parent_id, 'node-producer');
    assert.equal(hierarchy.design.edges[0].target.node_id, 'node-consumer');
    test('Rename and hierarchy edits retain stable connection IDs');

    await button('add-node').click(); assert.equal(await page.locator('[data-node-id]').count(), 3);
    await button('duplicate-node').click(); assert.equal(await page.locator('[data-node-id]').count(), 4);
    await button('undo').click(); assert.equal(await page.locator('[data-node-id]').count(), 3);
    await button('redo').click(); assert.equal(await page.locator('[data-node-id]').count(), 4);
    page.once('dialog', dialog => dialog.accept()); await button('load-project').click();
    await page.waitForFunction(() => document.querySelectorAll('[data-node-id]').length === 2);
    test('Add/duplicate and undo/redo; explicit draft discard');

    await button('tree-node-consumer').click(); await button('node-name').fill('Unsaved retained draft');
    page.once('dialog', dialog => dialog.dismiss()); await button('load-project').click();
    assert.equal(await button('node-name').inputValue(), 'Unsaved retained draft');
    page.once('dialog', dialog => dialog.accept());
    await page.locator('#import-file').setInputFiles({ name: 'bad.json', mimeType: 'application/json', buffer: Buffer.from('{bad json') });
    await page.waitForFunction(() => document.querySelector('#message').textContent.includes('not valid JSON'));
    assert.equal(await button('node-name').inputValue(), 'Unsaved retained draft');
    await page.reload(); await button('stage-graph_editor').waitFor();
    assert.equal(await button('tree-node-consumer').textContent().then(v => v.includes('Unsaved retained draft')), true);
    page.once('dialog', dialog => dialog.accept()); await button('load-project').click();
    await page.waitForFunction(() => document.querySelector('#save-state').textContent.includes('Saved locally'));
    test('Cancel and invalid import preserve draft; reload restores browser draft');

    const downloadEvent = page.waitForEvent('download'); await button('export-project').click();
    const download = await downloadEvent; const exported = path.join(output, 'exported-design.json'); await download.saveAs(exported);
    const design = JSON.parse(fs.readFileSync(exported, 'utf8'));
    const historyCount = (await envelope()).reviews.length;
    await importJson(design); await page.reload(); await button('stage-global_settings').waitFor();
    const reopened = await envelope(); assert.deepEqual(reopened.design, design); assert.equal(reopened.reviews.length, historyCount);
    test('Export/import round trip and persisted human history');

    await stage('graph_editor'); await button('tree-node-consumer').click();
    await button('fit-graph').click(); await save();
    await page.locator('#toast').waitFor({ state: 'hidden' });
    await page.screenshot({ path: path.join(output, 'desktop.png'), fullPage: true });
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
    await page.setViewportSize({ width: 390, height: 844 });
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
    await page.screenshot({ path: path.join(output, 'mobile.png'), fullPage: true });
    test('Desktop/mobile layout without body overflow; actual workspace screenshots');

    await page.setViewportSize({ width: 1440, height: 1100 });
    const opaque = structuredClone(design);
    opaque.nodes[0].id = 'producer/opaque'; opaque.nodes[0].ports[0].id = 'out/opaque';
    opaque.nodes[1].id = '__proto__'; opaque.nodes[1].ports[0].id = 'in/opaque'; opaque.nodes[1].parent_id = 'producer/opaque';
    opaque.edges[0].source = { node_id: 'producer/opaque', port_id: 'out/opaque' };
    opaque.edges[0].target = { node_id: '__proto__', port_id: 'in/opaque' };
    opaque.layout.nodes = JSON.parse('{"producer/opaque":{"x":100,"y":140},"__proto__":{"x":460,"y":140}}');
    await importJson(opaque); await stage('specifications');
    await button('edge-source-edge-producer-consumer').selectOption(JSON.stringify(['producer/opaque', 'out/opaque']));
    await button('edge-target-edge-producer-consumer').selectOption(JSON.stringify(['__proto__', 'in/opaque']));
    await save(); assert.deepEqual((await envelope()).design.edges[0].target, opaque.edges[0].target);
    await stage('graph_editor'); await button('node-__proto__').click({ position: { x: 70, y: 25 } });
    const protoBox = await button('node-__proto__').boundingBox();
    await page.mouse.move(protoBox.x + 60, protoBox.y + 20); await page.mouse.down();
    await page.mouse.move(protoBox.x + 90, protoBox.y + 35, { steps: 5 }); await page.mouse.up(); await save();
    assert(Object.hasOwn((await envelope()).design.layout.nodes, '__proto__'));
    test('Opaque endpoint IDs and prototype-named layout keys survive edits');

    const recovered = structuredClone(design); recovered.project.name = 'Recovered older draft';
    await page.evaluate(raw => localStorage.setItem('hullcirq.m1.draft.v1', raw), JSON.stringify({ design: recovered, base_revision_id: 'older-test-revision', stage: 'graph_editor' }));
    await page.reload(); await button('export-recovered-draft').waitFor();
    await button('load-project').click();
    await stage('global_settings'); await button('project-name').fill('Current saved input after recovery');
    assert.equal(await button('save-project').isEnabled(), true, 'Typing enables Save without needing blur.');
    await save(); await page.reload(); await button('export-recovered-draft').waitFor();
    const recoveredDownload = page.waitForEvent('download'); await button('export-recovered-draft').click();
    const recoveredPath = path.join(output, 'recovered-design.json'); await (await recoveredDownload).saveAs(recoveredPath);
    assert.deepEqual(JSON.parse(fs.readFileSync(recoveredPath, 'utf8')), recovered);
    page.once('dialog', dialog => dialog.accept()); await button('discard-recovered-draft').click();
    assert.equal(await page.locator('#recovered-drafts').isHidden(), true);
    assert.equal((await envelope()).design.project.name, 'Current saved input after recovery');
    test('Older draft backup survives save/load/reload; export and explicit discard');
    assert.deepEqual(errors, []);
    fs.writeFileSync(path.join(output, 'report.json'), JSON.stringify({ timestamp: new Date().toISOString(), browser: browser.version(), node: process.version, url, checks, pageErrors: errors, scope: 'M1 GUI/input checks only; no LLM or EDA execution' }, null, 2));
    console.log(JSON.stringify({ passed: checks.length, checks, pageErrors: errors, browser: browser.version() }, null, 2));
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
