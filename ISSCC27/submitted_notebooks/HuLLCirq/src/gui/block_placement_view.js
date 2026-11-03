import { element as el, svgElement, badge } from './dom.js';
import { workspaceSession, sessionFetch } from './workspace_transport.js';

const hash = value => typeof value === 'string' && /^[0-9a-f]{64}$/i.test(value);
const rect = value => Array.isArray(value) && value.length === 4 && value.every(v => typeof v === 'number' && Number.isFinite(v)) && value[0] < value[2] && value[1] < value[3];
const contains = (outer, inner) => outer[0] <= inner[0] && outer[1] <= inner[1] && outer[2] >= inner[2] && outer[3] >= inner[3];
const integer = value => Number.isInteger(value) && value >= 0;
const targetLabel = target => `${target.node_id}${Array.isArray(target.instance_index) ? '[' + target.instance_index.join(',') + ']' : ''}`;
const color = index => `hsl(${(index * 71) % 360} 65% 37%)`;
const boundFiles = ['def', 'block-placement-proof', 'block-ownership'];
const artifacts = run => run?.artifacts || run?.checks?.artifacts || [];
const check = (condition, message) => { if (!condition) throw new Error(message); };
const readPlacement = async route => {
  // Deliberately bypass the execution API's read-failure/stage-state handling.
  // sessionFetch still enforces the per-page workspace capability and drops a
  // response if its session changed. All remaining errors stay in this view.
  const response = await sessionFetch('/api/' + route, { cache: 'no-store', credentials: 'same-origin' });
  let result;
  try { result = await response.json(); }
  catch { throw new Error('The read-only placement response could not be read as JSON. No layout or project state was changed.'); }
  if (!response.ok) {
    const raw = result?.error, error = new Error(typeof raw === 'string' ? raw : raw?.message || `Read-only placement lookup failed (${response.status}).`);
    error.status = response.status; error.code = typeof raw === 'object' && raw !== null ? raw.code : null; throw error;
  }
  return result;
};

/** Presentation binding checks supplement, never replace, the backend proof. */
export function validateBlockPlacementProjection(run, data) {
  check(data?.version === 'block-placement-view-v1' && data.validation_status === 'Passed' && data.run_id === run?.id
    && data.physical_run_id === run.id && data.record_hash === run.record_hash
    && data.revision_id === run.revision_id && data.physical_design_revision_id === (run.physical_design_revision_id || run.revision_id)
    && data.profile_version === run.runtime_configuration?.profile?.profile_version,
  'The saved placement projection does not belong to the selected physical run and execution profile.');
  const source = data.source;
  check(source && hash(source.source_manifest_sha256) && source.source_manifest_sha256 === run.source_manifest_sha256
    && hash(source.plan_sha256) && source.plan_sha256 === run.runtime_configuration?.block_plan_sha256
    && source.global_job_id === run.global_job_id && source.synthesis_run_id === run.synthesis_run_id && source.netlist_run_id === run.netlist_run_id,
  'The placement source manifest, plan or adopted source identity does not match this saved run.');
  for (const [id, key] of [['def', 'final_def_sha256'], ['block-placement-proof', 'proof_sha256'], ['block-ownership', 'ownership_sha256']]) {
    const saved = artifacts(run).find(item => item.id === id);
    check(saved && hash(source[key]) && saved.sha256 === source[key], 'The placement projection ' + id + ' artifact hash does not match this saved run.');
  }
  check(rect(data.core_um) && typeof data.scope === 'string' && Array.isArray(data.regions) && data.regions.length > 0
    && data.regions.length <= 128 && Array.isArray(data.cells) && data.cells.length > 0 && data.cells.length <= 200000,
  'The validated placement projection has missing or unsupported saved geometry.');
  const regions = new Map();
  for (const region of data.regions) {
    check(typeof region.id === 'string' && !regions.has(region.id) && rect(region.rect_um) && contains(data.core_um, region.rect_um)
      && Array.isArray(region.targets) && region.targets.length > 0 && region.targets.every(target => typeof target?.node_id === 'string'
        && (target.instance_index === undefined || Array.isArray(target.instance_index) && target.instance_index.length === 2 && target.instance_index.every(integer))),
    'The placement projection contains an invalid or duplicate saved region.');
    regions.set(region.id, region);
  }
  const names = new Set(), odbNames = new Set();
  for (const cell of data.cells) {
    check(typeof cell.name === 'string' && cell.name.length > 0 && !names.has(cell.name)
      && typeof cell.source_name === 'string' && typeof cell.odb_name === 'string' && !odbNames.has(cell.odb_name)
      && typeof cell.master === 'string' && regions.has(cell.region_id) && rect(cell.bbox_um)
      && contains(regions.get(cell.region_id).rect_um, cell.bbox_um),
    'The placement projection contains an invalid, duplicate or out-of-region mapped cell.');
    names.add(cell.name); odbNames.add(cell.odb_name);
  }
  check(data.counts?.original_owned_cells === data.cells.length && data.counts.regions === data.regions.length
    && integer(data.counts.unclaimed_final_cells) && integer(data.counts.original_mapped_ties)
    && data.counts.original_mapped_ties <= data.cells.length && integer(data.counts.final_DEF_components)
    && data.counts.original_owned_cells + data.counts.unclaimed_final_cells === data.counts.final_DEF_components,
  'The placement projection counts do not match its original mapped-cell geometry.');
}

/** Source-bound, browser-only snapshot. Reads only on explicit activation/retry. */
export class BlockPlacementView {
  constructor(callbacks) { this.callbacks = callbacks; this.request = callbacks.request || readPlacement; this.cache = new Map(); this.token = 0; this.state = null; }
  key() {
    const p = this.callbacks.project(), run = this.callbacks.run();
    return JSON.stringify([p.envelope?.workspace_identity, workspaceSession(), run?.id, run?.revision_id,
      run?.physical_design_revision_id, run?.global_job_id, run?.source_manifest_sha256,
      run?.runtime_configuration_sha256, run?.runtime_configuration?.block_plan_sha256,
      artifacts(run).filter(item => boundFiles.includes(item.id)).map(item => [item.id, item.sha256])]);
  }
  current(state) {
    return state === this.state && state.token === this.token && this.host?.isConnected && this.callbacks.active()
      && this.key() === state.key && this.callbacks.run()?.record_hash === state.recordHash;
  }
  clear() { this.token++; this.state = null; this.host?.replaceChildren(); }
  mount(host) {
    if (this.host !== host) { this.clear(); this.host = host; }
    this.sync();
  }
  sync() {
    if (!this.host?.isConnected || !this.callbacks.active()) return;
    const key = this.key(), run = this.callbacks.run();
    if (this.state?.key === key && this.state.recordHash === run?.record_hash) return;
    this.clear();
    const entry = this.cache.get(key);
    if (entry && run) { this.state = { key, token: this.token, recordHash: run.record_hash, entry }; this.render(this.state); return; }
    this.message('Not loaded', run ? 'Read the saved proof for this selected physical run. No other layout or generated geometry is substituted.' : 'Select a saved block-region physical run first.', !!run);
  }
  async activate(host) {
    this.mount(host);
    if (this.state) return;
    await this.load();
  }
  async load() {
    if (!this.host?.isConnected || !this.callbacks.active()) return;
    const run = this.callbacks.run();
    if (!run) { this.message('Not available', 'No saved physical run is selected.', false); return; }
    if (this.state?.loading && this.current(this.state)) return;
    this.clear();
    const state = { key: this.key(), token: this.token, recordHash: run.record_hash, loading: true };
    this.state = state; this.cache.delete(state.key);
    this.message('Loading', 'Reading and validating the selected run’s saved placement proof. No EDA, save or adoption is requested.', false);
    try {
      const data = await this.request(`physical-workflow/runs/${encodeURIComponent(run.id)}/block-placement`);
      if (!this.current(state)) return;
      validateBlockPlacementProjection(run, data);
      state.loading = false; state.entry = { data, visible: new Set(data.regions.map(region => region.id)), zoom: 100 };
      this.cache.set(state.key, state.entry); this.render(state);
    } catch (error) {
      if (!this.current(state)) return;
      state.loading = false;
      this.message(error.code === 'block_placement_view_unavailable' ? 'Not available' : 'Failed',
        error.message || 'The saved placement proof could not be read. No fallback geometry is shown.', true);
    }
  }
  message(status, text, retry) {
    this.host?.replaceChildren(el('div', { class: 'generation-summary', role: 'status', 'data-testid': 'block-placement-status' }, badge(status), el('span', { text })),
      ...(retry ? [el('button', { type: 'button', text: 'Read saved block placement (read-only)', 'data-testid': 'block-placement-retry', onclick: () => this.load() })] : []));
  }
  render(state) {
    if (!this.current(state) || !state.entry) return;
    const entry = state.entry, data = entry.data, core = data.core_um, width = core[2] - core[0], height = core[3] - core[1];
    const groups = new Map(), inputs = new Map();
    const regionCounts = new Map(data.regions.map(region => [region.id, 0]));
    for (const cell of data.cells) regionCounts.set(cell.region_id, regionCounts.get(cell.region_id) + 1);
    const svg = svgElement('svg', { viewBox: `0 0 ${width} ${height}`, role: 'img', 'aria-label': 'Saved original mapped-cell block placement; inserted support cells excluded', class: 'block-placement-svg', 'data-testid': 'block-placement-svg' },
      svgElement('rect', { x: 0, y: 0, width, height, fill: '#f7fafc' }));
    const converted = r => ({ x: r[0] - core[0], y: core[3] - r[3], width: r[2] - r[0], height: r[3] - r[1] });
    for (const [index, region] of data.regions.entries()) {
      const group = svgElement('g', { 'data-region-id': region.id, display: entry.visible.has(region.id) ? 'inline' : 'none' });
      for (const cell of data.cells.filter(cell => cell.region_id === region.id)) group.append(svgElement('rect', { ...converted(cell.bbox_um), fill: color(index), 'data-cell-name': cell.name },
        svgElement('title', { text: `${cell.source_name} · ${cell.master} · ${cell.bbox_um.join(', ')} µm` })));
      const geometry = converted(region.rect_um);
      group.append(svgElement('rect', { ...geometry, fill: 'none', stroke: color(index), 'stroke-width': width / 900, 'vector-effect': 'non-scaling-stroke' }),
        svgElement('text', { x: geometry.x + 3, y: geometry.y + Math.min(height / 50, geometry.height / 8), fill: color(index), 'font-size': Math.min(height / 60, geometry.height / 10), text: region.id }),
        svgElement('title', { text: `${region.id}: ${region.targets.map(targetLabel).join(', ')}` }));
      groups.set(region.id, group); svg.append(group);
    }
    const applyZoom = () => { svg.style.width = `${entry.zoom}%`; svg.style.maxWidth = 'none'; zoomLabel.textContent = `${entry.zoom}%`; };
    const zoomLabel = el('output', { 'data-testid': 'block-placement-zoom-value' });
    const zoom = el('input', { type: 'range', min: '25', max: '800', step: '25', value: entry.zoom, 'aria-label': 'Block placement zoom', 'data-testid': 'block-placement-zoom', oninput: event => {
      if (!this.current(state)) return;
      entry.zoom = Math.min(800, Math.max(25, Number(event.target.value))); applyZoom();
    } });
    const scroll = el('div', { class: 'block-placement-scroll', tabIndex: 0, 'aria-label': 'Scrollable saved placement view', 'data-testid': 'block-placement-scroll' }, svg);
    const visibility = (id, visible) => {
      if (!this.current(state)) return;
      if (visible) entry.visible.add(id); else entry.visible.delete(id);
      groups.get(id).setAttribute('display', visible ? 'inline' : 'none'); inputs.get(id).checked = visible;
      updateCount();
    };
    const count = el('span', { 'data-testid': 'block-placement-visible-count' });
    const updateCount = () => {
      const visibleCells = [...entry.visible].reduce((sum, id) => sum + regionCounts.get(id), 0);
      count.textContent = `${entry.visible.size} of ${data.regions.length} regions · ${visibleCells.toLocaleString()} / ${data.cells.length.toLocaleString()} original mapped cells visible`;
    };
    const legend = el('div', { class: 'block-placement-legend' }, ...data.regions.map((region, index) => {
      const input = el('input', { type: 'checkbox', checked: entry.visible.has(region.id), 'data-testid': 'block-placement-region-' + region.id,
        onchange: event => visibility(region.id, event.target.checked) }); inputs.set(region.id, input);
      return el('label', {}, input, el('span', { class: 'block-placement-swatch', style: `background:${color(index)}` }), el('span', { text: `${region.id} · ${region.targets.map(targetLabel).join(', ')}` }));
    }));
    this.host.replaceChildren(
      el('div', { class: 'generation-summary', role: 'status', 'data-testid': 'block-placement-status' }, badge('Saved snapshot · read-only'), el('span', { text: `${data.cells.length.toLocaleString()} original mapped cells · ${data.regions.length} regions · ${data.run_id}` })),
      el('p', { class: 'scope-note', 'data-testid': 'block-placement-scope', text: `Original mapped cells only. ${data.counts.unclaimed_final_cells.toLocaleString()} unclaimed final cells (inserted clock/support and other unowned cells) are excluded. This is placed-cell geometry, not full mask layout, Functional Map or DRC/LVS/S14 verification. The cached snapshot does not establish currentness or adoption.` }),
      el('div', { class: 'provider-actions' },
        el('button', { type: 'button', text: 'Show all regions', 'data-testid': 'block-placement-show-all', onclick: () => data.regions.forEach(region => visibility(region.id, true)) }),
        el('button', { type: 'button', text: 'Hide all regions', 'data-testid': 'block-placement-hide-all', onclick: () => data.regions.forEach(region => visibility(region.id, false)) }), count,
        el('label', {}, el('span', { text: 'Zoom ' }), zoom, zoomLabel),
        el('button', { type: 'button', text: 'Fit view', 'data-testid': 'block-placement-fit', onclick: () => { if (!this.current(state)) return; entry.zoom = 100; zoom.value = 100; applyZoom(); scroll.scrollLeft = 0; scroll.scrollTop = 0; } }),
        el('button', { type: 'button', text: 'Refresh read-only snapshot', 'data-testid': 'block-placement-retry', onclick: () => this.load() })),
      legend, scroll,
      el('details', { class: 'raw-result' }, el('summary', { text: 'Saved source binding and view limits' }), el('pre', { text: JSON.stringify({ run_id: data.run_id, revision_id: data.revision_id, profile_version: data.profile_version, source: data.source, counts: data.counts, scope: data.scope, status_at_lookup: data.status, historical_at_lookup: data.historical, limits: data.limits }, null, 2) })));
    updateCount(); applyZoom();
  }
}
