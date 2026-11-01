"""Isolated client race checks; no browser, model, EDA or real project writes.

The DOM surface is a declared software double. Actual rendering and CSP behavior
require the separate real-browser observation; these checks are not circuit proof.
"""
from pathlib import Path
import json
import shutil
import subprocess
import unittest

PROJECT = Path(__file__).resolve().parents[1]

CLIENT_RACES = r"""
const fs = require('fs'), vm = require('vm'), assert = require('assert/strict');
const source = fs.readFileSync('src/gui/physical_workflow.js', 'utf8')
  .replace(/^import[^\n]*\n/gm, '').replace('export class PhysicalWorkflow', 'class PhysicalWorkflow');
class DOMDouble {
  constructor(tag = 'div', attrs = {}) { this.tag = tag; Object.assign(this, attrs); this.children = []; this.attributes = {}; }
  append(...children) { this.children.push(...children.map(x => x == null ? String(x) : x)); }
  replaceChildren(...children) { this.children = []; this.append(...children); }
  setAttribute(key, value) { this.attributes[key] = String(value); }
  focus() { this.focused = true; }
}
const el = (tag, attrs = {}, ...children) => { const node = new DOMDouble(tag, attrs); node.append(...children.flat(Infinity).filter(x => x != null)); return node; };
const fixtureHTML = '<!doctype html><html><body>SOFTWARE QA VIEW ONLY</body></html>';
const fetches = [], metadataRequests = [], messages = [];
let htmlStatus = 200, htmlGate = null;
const sandbox = { el, badge: text => el('span', {text}), field: () => el('div'), downloadJsonResponse() {},
  AbortController, TextEncoder, Blob, URL, console, setTimeout, clearTimeout,
  fetch: async (url, options) => {
    fetches.push({url, method: options.method || 'GET'});
    if (htmlGate) await htmlGate.promise;
    return {ok: htmlStatus === 200, status: htmlStatus, headers: {get: () => 'text/html; charset=utf-8'}, text: async () => fixtureHTML};
  }
};
sandbox.sessionFetch = (...args) => sandbox.fetch(...args);
vm.createContext(sandbox); vm.runInContext(source + '\nglobalThis.PhysicalWorkflow = PhysicalWorkflow;', sandbox);
const deferred = () => { let resolve, reject; const promise = new Promise((r, j) => {resolve = r; reject = j;}); return {promise, resolve, reject}; };
const tick = () => new Promise(resolve => setImmediate(resolve));
const hash = digit => digit.repeat(64);
const run = id => ({id, revision_id: 'revision-software-qa', source_manifest_sha256: hash('a'),
  execution_status: 'Completed', validation_status: 'Passed', review_status: 'Accepted', freshness: 'Current',
  source_key: hash('b'), source_epoch_at_start: 1, acceptance_epoch: 1,
  artifacts: ['gds', 'def', 'netlist'].map((id, i) => ({id, sha256: hash(String(i + 1))}))});
const metadata = (record, available = true) => ({available, run_id: record.id, historical: false,
  html_url: available ? `/api/artifacts/physical-workflow/${record.id}/functional-map-html` : null,
  png_url: null, report_url: null,
  reason: available ? null : {code: 'software_qa_unbound', message: 'No view is bound to this software QA run.'},
  status: {execution_status: record.execution_status, validation_status: record.validation_status,
    review_status: record.review_status, freshness: record.freshness}, status_scope: 'recorded_physical_workflow_state',
  source_binding: available ? {layout_run_id: record.id, revision_id: record.revision_id,
    source_manifest_sha256: record.source_manifest_sha256, archive_manifest_sha256: hash('c'), view_manifest_sha256: hash('d'),
    gds_sha256: hash('1'), def_sha256: hash('2'), netlist_sha256: hash('3')} : null});
const content = new DOMDouble(), tabs = {physical: new DOMDouble(), functional: new DOMDouble(), blocks: new DOMDouble(), placement: new DOMDouble()},
  panels = {physical: new DOMDouble(), functional: new DOMDouble(), blocks: new DOMDouble(), placement: new DOMDouble()};
const host = {isConnected: true, querySelector: selector => {
  if (selector === '[data-testid="functional-map-content"]') return content;
  return {'#physical-layout-tab': tabs.physical, '#functional-map-tab': tabs.functional, '#block-floorplan-tab': tabs.blocks, '#block-placement-tab': tabs.placement,
    '#physical-layout-panel': panels.physical, '#functional-map-panel': panels.functional, '#block-floorplan-panel': panels.blocks, '#block-placement-panel': panels.placement}[selector] || null;
}};
const first = run('software-qa-layout-accepted'), other = run('software-qa-layout-unbound');
let project = {stage: 'layout', design: {id: 'software-qa-project'}, envelope: {revision: {id: 'revision-software-qa'}}};
const queue = [];
const flow = new sandbox.PhysicalWorkflow({project: () => project, request: (route, body) => {
  assert.equal(body, undefined, 'A view lookup must never be a POST'); metadataRequests.push(route);
  assert.ok(queue.length, 'Unexpected metadata lookup'); return queue.shift().promise;
}});
flow.host = host; flow.data = {runs: [other, first], reviews: [], latest_run_id: first.id, accepted_run_id: first.id};
flow.runId = first.id;
flow.refresh = () => flow.renderFunctionalMap();
// Native replaceChildren stringifies null; only the production DOM helper skips it.
flow.renderFunctionalMapMessage('Loading', 'SOFTWARE QA loading');
assert.equal(content.children.some(node => typeof node === 'string'), false, 'Loading must not render null placeholders');
flow.renderFunctionalMapMessage('Available', 'SOFTWARE QA available', metadata(first));
assert.equal(content.children.some(node => typeof node === 'string'), false, 'Available must not render a null retry placeholder');
flow.renderFunctionalMapMessage = (status, message, data) => { content.replaceChildren(); messages.push({status, message, data}); };
const enqueue = () => { const pending = deferred(); queue.push(pending); return pending; };
const frames = () => content.children.filter(node => node.tag === 'iframe');
const lastStatus = () => messages.at(-1).status;

(async () => {
  assert.equal(flow.layoutView, 'physical');
  const pending = enqueue(); flow.setLayoutView('functional');
  assert.equal(lastStatus(), 'Loading'); assert.equal(tabs.functional.attributes['aria-selected'], 'true');
  assert.equal(panels.physical.hidden, true);
  pending.resolve(metadata(first)); await tick();
  assert.equal(lastStatus(), 'Available · read-only'); assert.equal(frames().length, 1);
  assert.equal(frames()[0].src, `/api/artifacts/physical-workflow/${first.id}/functional-map-html`);
  assert.equal(frames()[0].sandbox, 'allow-scripts'); assert.equal(frames()[0].srcdoc, undefined);

  // The same circuit hashes cannot authorize a view for a different run ID.
  const unbound = enqueue(); flow.selectRun(other.id);
  assert.equal(frames().length, 0, 'Old iframe must disappear synchronously');
  unbound.resolve(metadata(other, false)); await tick(); assert.equal(lastStatus(), 'Not available');
  assert.equal(frames().length, 0);

  // A late descriptor for a previous selection cannot install its iframe.
  const old = enqueue(); flow.selectRun(first.id);
  const newer = enqueue(); flow.selectRun(other.id);
  old.resolve(metadata(first)); await tick(); assert.equal(frames().length, 0);
  newer.resolve(metadata(other, false)); await tick(); assert.equal(lastStatus(), 'Not available');

  // The same selected run plus a new adopted history snapshot also invalidates.
  const beforeHistoryChange = enqueue(); flow.selectRun(first.id);
  const newRecord = run('software-qa-new-adopted-run');
  flow.data = {...flow.data, runs: [...flow.data.runs, newRecord], latest_run_id: newRecord.id, accepted_run_id: newRecord.id};
  const afterHistoryChange = enqueue(); flow.refresh();
  beforeHistoryChange.resolve(metadata(first)); await tick(); assert.equal(frames().length, 0);
  afterHistoryChange.resolve(metadata(first, false)); await tick(); assert.equal(lastStatus(), 'Not available');

  // A project replacement with identical IDs must not reuse an in-flight lookup.
  const oldProject = enqueue(); flow.selectRun(first.id);
  project = {...project, design: {id: 'different-software-qa-project'}};
  const newProject = enqueue(); flow.refresh();
  oldProject.resolve(metadata(first)); await tick(); assert.equal(frames().length, 0);
  newProject.resolve(metadata(first, false)); await tick(); assert.equal(lastStatus(), 'Not available');

  // Selected run/source identity and artifact-route mismatches fail closed.
  for (const alter of [m => m.run_id = other.id,
    m => m.source_binding.layout_run_id = other.id,
    m => m.source_binding.netlist_sha256 = hash('e'),
    m => m.html_url = 'https://invalid.example/view.html']) {
    const bad = enqueue(); flow.clearFunctionalMap(); flow.renderFunctionalMap();
    const value = metadata(first); alter(value); bad.resolve(value); await tick();
    assert.equal(lastStatus(), 'Failed'); assert.equal(frames().length, 0);
  }

  // Artifact failures are observed before navigation; no alternate HTML is used.
  htmlStatus = 409;
  const badHTML = enqueue(); flow.clearFunctionalMap(); flow.renderFunctionalMap();
  badHTML.resolve(metadata(first)); await tick(); assert.equal(lastStatus(), 'Failed'); assert.equal(frames().length, 0);
  htmlStatus = 200;

  const failedMetadata = enqueue(); flow.clearFunctionalMap(); flow.renderFunctionalMap();
  failedMetadata.reject(new Error('SOFTWARE QA metadata lookup failed (404).'));
  await tick(); assert.equal(lastStatus(), 'Failed'); assert.equal(frames().length, 0);

  // A late HTML read is also rejected after changing the selected run.
  htmlGate = deferred(); const htmlOld = enqueue(); flow.clearFunctionalMap(); flow.renderFunctionalMap();
  htmlOld.resolve(metadata(first)); await tick();
  const htmlNew = enqueue(); flow.selectRun(other.id);
  htmlGate.resolve(); await tick(); assert.equal(frames().length, 0);
  htmlGate = null; htmlNew.resolve(metadata(other, false)); await tick();

  // Arrow/Home/End selection is memory-only and preserves the selected run.
  const selectedID = flow.runId, beforeKeys = metadataRequests.length;
  let prevented = 0;
  flow.layoutViewKey({key: 'Home', preventDefault() {prevented++;}}, 'functional');
  assert.equal(flow.layoutView, 'physical'); assert.equal(tabs.physical.focused, true);
  assert.equal(tabs.physical.tabIndex, 0); assert.equal(tabs.functional.tabIndex, -1);
  assert.equal(metadataRequests.length, beforeKeys);
  flow.layoutViewKey({key: 'End', preventDefault() {prevented++;}}, 'physical');
  assert.equal(flow.layoutView, 'placement'); assert.equal(tabs.placement.focused, true);
  flow.layoutViewKey({key: 'ArrowLeft', preventDefault() {prevented++;}}, 'placement');
  assert.equal(flow.layoutView, 'blocks'); assert.equal(tabs.blocks.focused, true);
  assert.equal(metadataRequests.length, beforeKeys, 'Opening the planning tab must not request a map or mutate files');
  const keyboard = enqueue();
  flow.layoutViewKey({key: 'ArrowLeft', preventDefault() {prevented++;}}, 'blocks');
  keyboard.resolve(metadata(other, false)); await tick();
  assert.equal(flow.layoutView, 'functional'); assert.equal(tabs.functional.focused, true);
  flow.layoutViewKey({key: 'ArrowLeft', preventDefault() {prevented++;}}, 'functional');
  assert.equal(flow.layoutView, 'physical'); assert.equal(flow.runId, selectedID); assert.equal(prevented, 5);
  assert.equal(frames().length, 0);
  flow.data = {...flow.data, runs: [], latest_run_id: null, accepted_run_id: null};
  flow.setLayoutView('functional');
  assert.equal(lastStatus(), 'Not available'); assert.equal(frames().length, 0);
  assert.ok(fetches.every(request => request.method === 'GET'));
  assert.ok(metadataRequests.every(route => route.endsWith('/functional-map')));
  console.log(JSON.stringify({status: 'Passed', software_qa_fixture: true, mutation_requests: 0,
    model_calls: 0, eda_calls: 0, stale_descriptor_and_html_guard: true,
    same_hash_different_run_guard: true, same_selected_new_history_guard: true,
    project_identity_guard: true, fixed_artifact_routes: true, keyboard_memory_only: true}));
})().catch(error => {console.error(error.stack || error); process.exitCode = 1;});
"""

VERSION_FIXTURE = CLIENT_RACES.split("\n(async () => {", 1)[0] + r"""
const publication = 'functional-map-' + '1'.repeat(32);
const otherPublication = 'functional-map-' + '2'.repeat(32);
const pinnedMetadata = () => {
  const value = metadata(first);
  value.source_binding.registration_job_id = publication;
  const route = `/api/artifacts/physical-workflow/${first.id}/functional-map-`;
  for (const kind of ['html', 'png', 'report']) value[kind + '_url'] = route + kind + '?map_generation=' + publication;
  return value;
};
"""

VERSION_CASES = {
    "saved_version_selection_reads_only_the_selected_publication_and_latest_is_explicit": r"""
  flow.layoutView = 'functional';
  flow.mapGeneration = {token: flow.mapGenerationToken, key: flow.mapGenerationKey(first), design: project.design,
    result: {jobs: [publication, otherPublication].map(id => ({id, status:'Completed', layout_run_id:first.id}))}};
  const before = JSON.stringify(flow.data);
  const older = enqueue(); flow.selectMapPublication(publication);
  assert.equal(flow.selectedMapPublication(), publication);
  assert.equal(metadataRequests.at(-1), `physical-workflow/runs/${first.id}/functional-map?map_generation=${publication}`);
  older.resolve(pinnedMetadata()); await tick();
  assert.equal(lastStatus(), 'Available · read-only');
  assert.ok(frames()[0].src.endsWith('?map_generation=' + publication));
  assert.equal(JSON.stringify(flow.data), before, 'Viewing a version must not change acceptance or latest run');
  const latest = enqueue(); flow.selectMapPublication(null);
  assert.equal(flow.selectedMapPublication(), null);
  assert.ok(metadataRequests.at(-1).endsWith('/functional-map'));
  const latestMetadata = pinnedMetadata();
  latestMetadata.source_binding.registration_job_id = otherPublication;
  for (const kind of ['html','png','report']) latestMetadata[kind + '_url'] = latestMetadata[kind + '_url'].replace(publication, otherPublication);
  latest.resolve(latestMetadata); await tick();
  assert.ok(frames()[0].src.endsWith('?map_generation=' + otherPublication));
  assert.equal(JSON.stringify(flow.data), before);
""",
    "foreign_or_unfinished_versions_are_rejected_and_late_versions_cannot_replace_selection": r"""
  flow.layoutView = 'functional';
  flow.mapGeneration = {token: flow.mapGenerationToken, key: flow.mapGenerationKey(first), design: project.design,
    result: {jobs: [{id:publication,status:'Completed',layout_run_id:other.id},
      {id:otherPublication,status:'Running',layout_run_id:first.id}]}};
  for (const id of [publication,otherPublication,'../invalid','functional-map-' + 'a'.repeat(32),42]) flow.selectMapPublication(id);
  assert.equal(metadataRequests.length, 0);
  assert.equal(flow.selectedMapPublication(), null);
  flow.mapGeneration.result.jobs = [{id:publication,status:'Completed',layout_run_id:first.id}];
  const older = enqueue(); flow.selectMapPublication(publication);
  const latest = enqueue(); flow.selectMapPublication(null);
  older.resolve(pinnedMetadata()); await tick();
  assert.equal(frames().length, 0, 'Late old-version metadata must be ignored');
  latest.resolve(metadata(first)); await tick();
  assert.equal(frames()[0].src, metadata(first).html_url);
  const incorrect = enqueue(); flow.selectMapPublication(publication);
  const before = fetches.length;
  incorrect.resolve(metadata(first)); await tick();
  assert.equal(lastStatus(), 'Failed');
  assert.equal(frames().length, 0);
  assert.equal(fetches.length, before, 'A different publication must be rejected before artifact retrieval');
  project = {...project,design:{id:'different-software-qa-project'}};
  assert.equal(flow.selectedMapPublication(), null, 'A different project must not inherit a selected version');
""",
    "pinned_descriptor_is_used_for_preflight_and_actual_iframe_navigation": r"""
  const observed = pinnedMetadata();
  flow.validateFunctionalMap(first, observed);
  htmlGate = deferred();
  const descriptor = enqueue(); flow.setLayoutView('functional');
  descriptor.resolve(observed); await tick();
  assert.equal(fetches.length, 1);
  assert.equal(fetches[0].url, observed.html_url);
  assert.equal(frames().length, 0, 'Artifact preflight must finish before iframe creation');
  htmlGate.resolve(); await tick(); htmlGate = null;
  assert.equal(lastStatus(), 'Available · read-only');
  assert.equal(frames().length, 1);
  assert.equal(frames()[0].src, observed.html_url);
  assert.ok(frames()[0].src.endsWith('?map_generation=' + publication));
  assert.equal(frames()[0].srcdoc, undefined);
  assert.equal(observed.png_url, `/api/artifacts/physical-workflow/${first.id}/functional-map-png?map_generation=${publication}`);
  assert.equal(observed.report_url, `/api/artifacts/physical-workflow/${first.id}/functional-map-report?map_generation=${publication}`);
  assert.ok(!frames()[0].src.includes(otherPublication));
  // Legacy descriptors remain valid only on their original unpinned routes.
  const legacy = metadata(first);
  legacy.png_url = `/api/artifacts/physical-workflow/${first.id}/functional-map-png`;
  legacy.report_url = `/api/artifacts/physical-workflow/${first.id}/functional-map-report`;
  flow.validateFunctionalMap(first, legacy);
  const legacyRead = enqueue(); flow.clearFunctionalMap(); flow.renderFunctionalMap();
  legacyRead.resolve(legacy); await tick();
  assert.equal(lastStatus(), 'Available · read-only');
  assert.equal(frames()[0].src, legacy.html_url);
  assert.ok(fetches.every(request => request.method === 'GET'));
""",
    "invalid_or_mixed_publication_identity_and_urls_fail_before_artifact_read": r"""
  const invalidIdentity = [null, false, 42, '', 'functional-map-' + 'a'.repeat(31),
    'functional-map-' + 'a'.repeat(33), 'functional-map-' + 'A'.repeat(32),
    'other-' + '1'.repeat(32), publication + '/foreign', publication + '?x=1',
    publication + '&map_generation=' + otherPublication, '../' + publication,
    '<script>software QA only</script>'];
  const invalid = invalidIdentity.map(value => m => { m.source_binding.registration_job_id = value; });
  invalid.push(
    m => { delete m.source_binding.registration_job_id; },
    m => { m.html_url = m.html_url.split('?')[0]; },
    m => { m.html_url = m.html_url.replace(publication, otherPublication); },
    m => { m.html_url += '&map_generation=' + otherPublication; },
    m => { m.html_url += '&map_generation=' + publication; },
    m => { m.html_url += '&unexpected=1'; },
    m => { m.html_url += '#different-version'; },
    m => { m.html_url = m.html_url.replace('map_generation=', 'map_generation%3D'); },
    m => { m.html_url = 'https://invalid.example/' + m.html_url; },
    m => { m.png_url = m.png_url.split('?')[0]; },
    m => { m.png_url = m.png_url.replace(publication, otherPublication); },
    m => { m.png_url += '&map_generation=' + publication; },
    m => { m.report_url = m.report_url.split('?')[0]; },
    m => { m.report_url = m.report_url.replace(publication, otherPublication); },
    m => { m.report_url += '&map_generation=' + publication; });
  flow.layoutView = 'functional';
  for (const alter of invalid) {
    const value = pinnedMetadata(); alter(value);
    assert.throws(() => flow.validateFunctionalMap(first, value), /publication|artifact routes/);
    const before = fetches.length;
    const descriptor = enqueue(); flow.clearFunctionalMap(); flow.renderFunctionalMap();
    descriptor.resolve(value); await tick();
    assert.equal(lastStatus(), 'Failed');
    assert.equal(frames().length, 0);
    assert.equal(fetches.length, before, 'Invalid publication must not initiate artifact preflight');
  }
  assert.ok(metadataRequests.every(route => route.endsWith('/functional-map')));
""",
}


class FunctionalMapClientTests(unittest.TestCase):
    def test_readonly_subtabs_and_async_source_binding_races(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node is required for the isolated client regression.")
        result = subprocess.run([node, "-e", CLIENT_RACES], cwd=PROJECT,
                                capture_output=True, text=True, encoding="utf-8", timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout.strip().splitlines()[-1])["mutation_requests"], 0)

    def run_version_case(self, name):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node is required for the isolated publication regression.")
        script = VERSION_FIXTURE + "\n(async () => {\n" + VERSION_CASES[name] + r"""
  console.log(JSON.stringify({status:'Passed', software_qa_fixture:true, mutation_requests:0, model_calls:0, eda_calls:0}));
})().catch(error => {console.error(error.stack || error); process.exitCode = 1;});
"""
        result = subprocess.run([node, "-e", script], cwd=PROJECT,
                                capture_output=True, text=True, encoding="utf-8", timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout.strip().splitlines()[-1])["status"], "Passed")


for _case in VERSION_CASES:
    setattr(FunctionalMapClientTests, "test_" + _case,
            lambda self, name=_case: self.run_version_case(name))


if __name__ == "__main__":
    unittest.main()
