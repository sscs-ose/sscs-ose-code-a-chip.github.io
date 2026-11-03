import { sessionFetch } from './workspace_transport.js';
import { element as el, field, badge, downloadJsonResponse } from './dom.js';

const active = run => !!run && ['Queued', 'Running'].includes(run.execution_status);
const current = run => run?.execution_status === 'Completed' && run.validation_status === 'Passed' && run.review_status === 'Accepted' && run.freshness === 'Current';
const safe = value => String(value).replace(/[^a-z0-9_.-]/gi, '_');
const card = (title, text, ...children) => el('section', { class: 'card' }, el('div', { class: 'card-heading' }, el('h2', { text: title }), el('p', { text })), ...children);
const details = (title, value, attrs = {}, state = {}) => {
  const source = JSON.stringify(value ?? {}, null, 2), size = 32768, count = Math.ceil(source.length / size);
  const host = el('details', { class: 'raw-result', ...attrs, open: state.open ?? attrs.open, ontoggle: () => { state.open = host.open; } }, el('summary', { text: title }));
  if (source.length <= size * 2) { host.append(el('pre', { text: source })); return host; }
  // Keep the complete string, while laying out only one bounded segment. Large
  // raw EDA records otherwise stall browser rendering when a detail is opened.
  state.page = Math.min(Math.max(state.page || 0, 0), count - 1);
  const prefix = attrs['data-testid'] || 'lvs-inspector-' + safe(title);
  const preview = el('pre', { 'data-testid': prefix + '-segment' }), range = el('p', { class: 'scope-note', 'data-testid': prefix + '-range' });
  const buttons = [
    ['first', 'First segment', () => 0], ['previous', 'Previous segment', () => state.page - 1],
    ['next', 'Next segment', () => state.page + 1], ['last', 'Last segment', () => count - 1],
  ].map(([id, label, destination]) => el('button', { type: 'button', text: label, 'data-testid': prefix + '-' + id, onclick: () => { state.page = destination(); display(); } }));
  const display = () => {
    const start = state.page * size, end = Math.min(start + size, source.length);
    preview.textContent = source.slice(start, end);
    range.textContent = `Segment ${state.page + 1} of ${count} · characters ${start + 1}–${end} of ${source.length}. All segments are available. Download the original JSON for the complete exact record; previews use browser number precision.`;
    buttons[0].disabled = buttons[1].disabled = state.page === 0;
    buttons[2].disabled = buttons[3].disabled = state.page === count - 1;
  };
  host.append(range, el('div', { class: 'provider-actions' }, buttons), preview); display(); return host;
};
const JSON_FIELDS = ['layout-record', 'drc-record', 'source-identity', 'runtime-configuration', 'artifact-manifest'];
const FILES = new Set(['input-gds', 'input-def', 'input-netlist', 'input-powered-netlist', 'config', 'initial-state', 'final-state', 'metrics', 'tool-versions', 'lvs-summary', 'extracted-spice', 'lvs-report', 'lvs-json', 'extraction-feedback', 'extraction-markers', 'lvs-script', 'extraction-model-proof', 'extraction-raw-spice', 'extraction-models', 'extraction-deck', 'extraction-inventory-pre-gds', 'extraction-inventory-post-gds', 'extraction-inventory-post-annotation']);
const EXTENSIONS = { 'input-gds': 'gds', 'input-def': 'def', 'input-netlist': 'v', 'input-powered-netlist': 'v', 'extracted-spice': 'spice', 'lvs-report': 'rpt', 'extraction-feedback': 'txt', 'extraction-markers': 'xml', 'lvs-script': 'lvs', 'extraction-model-proof': 'json', 'extraction-raw-spice': 'spice', 'extraction-models': 'spice', 'extraction-deck': 'tech', 'extraction-inventory-pre-gds': 'json', 'extraction-inventory-post-gds': 'json', 'extraction-inventory-post-annotation': 'json' };
const CORRECTED_EXTRACTION_PROFILE = 'hullcirq-sky130-lvs-v3';
const CORRECTED_EXTRACTION_PROFILE_V4 = 'hullcirq-sky130-lvs-v4';
const CORRECTED_EXTRACTION_PROFILE_V5 = 'hullcirq-sky130-lvs-v5';
const CORRECTED_EXTRACTION_PROFILE_V6 = 'hullcirq-sky130-lvs-v6';
const CORRECTED_EXTRACTION_PROFILE_V7 = 'hullcirq-sky130-lvs-v7';
const CORRECTED_EXTRACTION_LABELS = Object.freeze({ [CORRECTED_EXTRACTION_PROFILE]: 'v3', [CORRECTED_EXTRACTION_PROFILE_V4]: 'v4', [CORRECTED_EXTRACTION_PROFILE_V5]: 'v5', [CORRECTED_EXTRACTION_PROFILE_V6]: 'v6', [CORRECTED_EXTRACTION_PROFILE_V7]: 'v7' });
const EXTRACTION_UPGRADES = Object.freeze({
  upgrade_v4: Object.freeze({ previous: CORRECTED_EXTRACTION_PROFILE, target: CORRECTED_EXTRACTION_PROFILE_V4, intent: 'address loaded-definition inventory handling' }),
  upgrade_v5: Object.freeze({ previous: CORRECTED_EXTRACTION_PROFILE_V4, target: CORRECTED_EXTRACTION_PROFILE_V5, intent: 'establish explicit selected-cell extraction' }),
  upgrade_v6: Object.freeze({ previous: CORRECTED_EXTRACTION_PROFILE_V5, target: CORRECTED_EXTRACTION_PROFILE_V6, intent: 'correct native MOS-capacitor parameter recognition' }),
  upgrade_v7: Object.freeze({ previous: CORRECTED_EXTRACTION_PROFILE_V6, target: CORRECTED_EXTRACTION_PROFILE_V7, executionStatuses: Object.freeze(['Completed']), intent: 'preserve raw extracted parameters in an explicit three-to-four-pin comparison mapping' }),
});
const RETURNS = [['global_settings', 'Global Settings'], ['graph_editor', 'Graph Editor'], ['specifications', 'Specifications'], ['local_rtl_generation', 'Local RTL Generation'], ['local_synthesis', 'Local Synthesis'], ['local_netlist_simulation', 'Local Netlist Simulation'], ['node_implementation_specs', 'Node Implementation Specs'], ['global_rtl_generation', 'Global RTL Generation'], ['global_synthesis', 'Global Synthesis'], ['global_netlist_simulation', 'Global Netlist Simulation'], ['layout', 'Layout'], ['drc', 'DRC']];

/** S13 compares the adopted physical circuit; it never rewrites RTL or invokes a model. */
export class LVSWorkflow {
  constructor(callbacks) {
    this.callbacks = callbacks; this.data = { runs: [], reviews: [], ready: false, tool_ready: false };
    this.runId = null; this.notes = new Map(); this.targets = new Map(); this.inspectors = new Map();
    this.busy = false; this.polling = false; this.pollTimer = null; this.pollError = null; this.uncertainStart = false;
  }
  project() { return this.callbacks.project(); }
  inspect(title, value, attrs = {}) {
    const key = `${this.selected()?.id || 'configuration'}:${attrs['data-testid'] || title}`;
    if (!this.inspectors.has(key)) this.inspectors.set(key, {});
    return details(title, value, attrs, this.inspectors.get(key));
  }
  selected() { return this.data.runs.find(run => run.id === this.runId) || this.data.runs.at(-1); }
  sources() {
    const e = this.project().envelope;
    const layout = e.physical_workflow?.runs?.find(item => item.id === e.physical_workflow.accepted_run_id);
    const drc = e.drc_workflow?.runs?.find(item => item.id === e.drc_workflow.accepted_run_id);
    if (!current(layout) || !current(drc) || typeof layout.revision_id !== 'string' || !layout.revision_id
      || drc.revision_id !== layout.revision_id || drc.layout_run_id !== layout.id
      || (e.physical_workflow.latest_run_id && e.physical_workflow.latest_run_id !== layout.id)
      || (e.drc_workflow.latest_run_id && e.drc_workflow.latest_run_id !== drc.id)) return null;
    const references = [['layout_run_id', layout.id], ['drc_run_id', drc.id]];
    if (references.some(([key]) => Object.hasOwn(this.data, key))
      ? references.some(([key, id]) => typeof this.data[key] !== 'string' || this.data[key] !== id)
      : layout.revision_id !== e.revision.id) return null;
    const gds = layout.artifacts?.find(item => item.id === 'gds'), netlist = layout.artifacts?.find(item => item.id === 'netlist');
    return gds && netlist && drc.input_gds_sha256 === gds.sha256 ? { layout, drc, gds, netlist } : null;
  }
  receive(envelope) { if (envelope.lvs_workflow) this.data = envelope.lvs_workflow; this.refresh(); this.schedule(); }
  pendingPolicy() {
    const policy = this.project().envelope.review_policy, run = this.data.runs.find(item => item.id === this.data.latest_run_id);
    return policy?.mode === 'accept_on_pass' && policy.user_authorized === true && !this.data.storage_error && run?.execution_status === 'Completed' && run.validation_status === 'Passed' && run.review_status === 'Awaiting Review' && run.freshness === 'Current' && !run.error && !(run.diagnostics || []).some(item => item.code === 'automatic_adoption_blocked');
  }
  anyActive() { const e = this.project().envelope; return [this.data.runs, e.postlayout_workflow?.runs || [], e.drc_workflow?.runs || [], e.physical_workflow?.runs || [], e.global_workflow?.runs || [], e.workflow_runs || [], e.global_generation?.jobs || [], e.generation?.jobs || []].some(runs => runs.some(active)); }
  repairUpgrade() {
    const preparation = this.project().envelope.lvs_repair_preparation;
    const recipe = preparation && Object.hasOwn(EXTRACTION_UPGRADES, preparation.mode) ? EXTRACTION_UPGRADES[preparation.mode] : null;
    return recipe && preparation.profile_version === recipe.target ? recipe : null;
  }
  repairSource() {
    const p = this.project(), preparation = p.envelope.lvs_repair_preparation, source = preparation?.source, upstream = this.sources(), run = this.selected(), status = p.envelope.lvs_repair_session || {};
    const recipe = this.repairUpgrade(), upgrade = !!recipe;
    const initialV7 = preparation?.mode === 'initial_v7' && preparation.profile_version === CORRECTED_EXTRACTION_PROFILE_V7;
    const initial = preparation?.profile_version === CORRECTED_EXTRACTION_PROFILE && (!preparation.mode || preparation.mode === 'initial_v3')
      || initialV7 && !status.configured && !status.bundle_present && !status.error
      && run?.runtime_configuration?.profile?.profile_version === 'hullcirq-sky130-lvs-v2';
    const eligibleRun = upgrade ? (recipe.executionStatuses || ['Failed']).includes(run?.execution_status) && run.validation_status === 'Failed' && run.review_status === 'Awaiting Review' && run.freshness === 'Current'
      && run.runtime_configuration?.profile?.profile_version === recipe.previous
      : (current(run) && run.id === this.data.accepted_run_id) || (initialV7 && run?.execution_status === 'Completed'
        && run.validation_status === 'Passed' && run.review_status === 'Awaiting Review' && run.freshness === 'Current');
    if (preparation?.available !== true || preparation.eligible !== true || (!initial && !upgrade)
      || !source || !upstream || !eligibleRun || run.id !== this.data.latest_run_id
      || run.evidence_kind !== 'trusted_fixed_lvs_execution' || run.error || run.checks?.executed !== true
      || run.checks.cleanup_unresolved === true || run.checks.software_qa_fixture === true
      || source.revision_id !== p.envelope.revision.id || source.source_revision_id !== upstream.layout.revision_id
      || run.revision_id !== upstream.layout.revision_id || source.source_lvs_run_id !== run.id
      || source.layout_run_id !== upstream.layout.id || source.drc_run_id !== upstream.drc.id
      || run.layout_run_id !== upstream.layout.id || run.drc_run_id !== upstream.drc.id) return null;
    const hashes = [['layout_record_hash', upstream.layout.record_hash], ['drc_record_hash', upstream.drc.record_hash],
      ['source_lvs_record_hash', run.record_hash], ['input_gds_sha256', upstream.gds.sha256], ['input_netlist_sha256', upstream.netlist.sha256]];
    if (hashes.some(([key, value]) => typeof value !== 'string' || !/^[a-f0-9]{64}$/i.test(value) || source[key] !== value)
      || !/^[a-f0-9]{64}$/i.test(source.source_lvs_record_sha256 || '')
      || run.input_gds_sha256 !== upstream.gds.sha256 || run.input_netlist_sha256 !== upstream.netlist.sha256
      || run.layout_snapshot?.record_hash !== upstream.layout.record_hash || run.drc_snapshot?.record_hash !== upstream.drc.record_hash) return null;
    if (upgrade && (status.configured !== true || status.bundle_present !== true || status.error
      || status.profile_version !== recipe.previous || source.previous_profile_version !== recipe.previous
      || !/^[a-f0-9]{64}$/i.test(status.bundle_sha256 || '') || source.previous_bundle_sha256 !== status.bundle_sha256
      || typeof source.historical_lvs_run_id !== 'string' || !source.historical_lvs_run_id
      || source.historical_lvs_run_id !== status.source_identity?.historical_lvs_run_id
      || !/^[a-f0-9]{64}$/i.test(source.historical_lvs_record_sha256 || '')
      || source.historical_lvs_record_sha256 !== status.source_identity?.historical_lvs_record_sha256)) return null;
    return { ...upstream, run, source, upgrade };
  }
  repairScope() {
    const p = this.project(), sources = this.sources(), run = this.selected();
    return JSON.stringify([p.envelope.workspace_identity, p.envelope.revision.id, sources?.layout.id, sources?.layout.record_hash,
      sources?.drc.id, sources?.drc.record_hash, run?.id, run?.record_hash, this.data.latest_run_id,
      this.data.accepted_run_id, this.data.configuration_sha256, p.envelope.lvs_repair_preparation?.mode,
      p.envelope.lvs_repair_preparation?.profile_version, p.envelope.lvs_repair_preparation?.source,
      p.envelope.lvs_repair_session?.profile_version, p.envelope.lvs_repair_session?.bundle_sha256]);
  }
  repairGate() {
    const p = this.project(), status = p.envelope.lvs_repair_session || {}, preparation = p.envelope.lvs_repair_preparation;
    if (p.readOnly || p.envelope.workspace_identity?.read_only) return 'This preserved system is read-only.';
    const recipe = this.repairUpgrade(), upgrade = !!recipe && status.configured === true && status.profile_version === recipe.previous;
    if (status.configured && !upgrade) return 'The corrected LVS extraction profile is already prepared. Run LVS separately.';
    if (status.bundle_present && !upgrade) return status.error?.message || 'A saved LVS correction profile already exists. Refresh its status; it will not be overwritten.';
    if (p.conflict) return 'A newer saved design was detected. Export your draft, then Open saved.';
    if (p.dirty) return 'Save the complete design before preparing corrected extraction.';
    if (p.busy || this.busy || this.polling || this.anyActive()) return 'Wait for active project, model and tool operations to finish.';
    if (this.data.storage_error) return this.data.storage_error.message || 'Saved LVS history is unavailable.';
    if (this.uncertainStart || this.pollError) return this.pollError || 'Refresh saved results before preparing extraction; the previous outcome is unknown.';
    if (!preparation || preparation.available !== true || preparation.eligible !== true) return preparation?.blocked_reason || 'The connected service has not identified an eligible current extraction-warning source.';
    if (!this.repairSource()) return upgrade ? `Select the exact latest current failed ${CORRECTED_EXTRACTION_LABELS[recipe.previous]} LVS attempt and retain its prepared ${CORRECTED_EXTRACTION_LABELS[recipe.previous]} bundle, original warning source and adopted S11/S12 hashes.` : 'Select the exact latest current completed LVS warning record with its adopted S11/S12 sources and saved hashes. The warning result need not be adopted.';
    return '';
  }
  repairPreparation() {
    const preparation = this.project().envelope.lvs_repair_preparation, recipe = this.repairUpgrade(), gate = this.repairGate();
    const initialV7 = preparation?.mode === 'initial_v7' && preparation.profile_version === CORRECTED_EXTRACTION_PROFILE_V7;
    const target = recipe ? CORRECTED_EXTRACTION_LABELS[recipe.target] : initialV7 ? 'v7' : null, previous = recipe ? CORRECTED_EXTRACTION_LABELS[recipe.previous] : null;
    return el('div', { 'data-testid': 'lvs-repair-profile-preparation' },
      el('p', { text: recipe ? `Use the separately versioned ${target} profile to ${recipe.intent} after a retained failed ${previous} execution. Prepare it explicitly only when the service validates the failed attempt and its original source chain. The ${previous} bundle, failure and guard remain unchanged; ${target} preparation is not a retry, a tool run or proof of warning resolution.` : 'Explicitly prepare the fixed new extraction version for the recognized device-terminal feedback. The versioned correction concerns MOS-capacitor recognition and its pin adapter, retaining ordinary MOS checks and the original PDK. Actual new tool feedback and connectivity checks determine its effect. No warning is waived or declared resolved by preparation.' }),
      initialV7 ? el('p', { class: 'scope-note', text: 'Prepare the fixed latest v7 profile directly from the completed original v2 warning record. Its adoption is not required; preparation preserves its pending review. S11/S12 must remain adopted. No correction bundle may already exist; historical failed-version upgrades remain separately source-bound.' }) : null,
      el('p', { class: 'scope-note', text: 'Original RTL, GDS/DEF geometry, clock/SDC, independent expectations and earlier LVS records remain unchanged. Preparation performs source/proof checks and saves only its fixed profile. Run LVS, review and adoption remain separate explicit actions.' }),
      el('p', { class: 'generation-gate', 'data-testid': 'lvs-repair-profile-gate', text: gate || 'Eligible saved source identified. Explicit preparation starts no EDA or model process.' }),
      this.inspect('Read-only extraction correction eligibility and source identity', preparation, { 'data-testid': 'lvs-repair-profile-source' }),
      el('button', { type: 'button', text: target ? `Prepare corrected LVS extraction profile ${target}` : 'Prepare corrected LVS extraction profile', 'data-testid': 'lvs-repair-profile-prepare', disabled: !!gate, title: gate || 'Validate the original source and prepare only the fixed extraction profile; no EDA or adoption.', onclick: () => this.prepareRepairProfile() }));
  }
  renderRepairProfile() {
    const host = this.host?.querySelector('[data-testid="lvs-repair-profile-card"]'); if (!host) return;
    const p = this.project(), status = p.envelope.lvs_repair_session || {}, preparation = p.envelope.lvs_repair_preparation, recipe = this.repairUpgrade();
    host.hidden = !preparation && !status.configured && !status.bundle_present;
    if (host.hidden) { host.replaceChildren(); return; }
    const title = el('div', { class: 'card-heading' }, el('h2', { text: 'Corrected LVS extraction profile' }));
    if (status.configured && Object.hasOwn(CORRECTED_EXTRACTION_LABELS, status.profile_version)) {
      host.replaceChildren(...[title, badge(`Prepared ${CORRECTED_EXTRACTION_LABELS[status.profile_version]} · not a new LVS result`),
        el('p', { text: 'The separately versioned extraction profile is prepared for its saved source chain. Preparation starts no EDA, changes no RTL or geometry, and adopts nothing. Earlier warning records remain unchanged and inspectable.' }),
        el('p', { class: 'scope-note', text: 'Choose Run LVS separately, inspect the new extraction feedback and comparison, then review the new S13 result. A newly accepted S13 requires a new source-bound S14 run. Inspect S14 readiness; prepare its profile again only if requested. The prepared profile does not establish that any warning is resolved.' }),
        this.inspect('Saved corrected extraction profile and source binding', status, { 'data-testid': 'lvs-repair-profile-status' }),
        recipe && status.profile_version === recipe.previous ? this.repairPreparation() : null,
        el('button', { type: 'button', text: status.profile_version === CORRECTED_EXTRACTION_PROFILE ? 'Run LVS with prepared profile' : `Run LVS with prepared ${CORRECTED_EXTRACTION_LABELS[status.profile_version]} profile`, 'data-testid': 'lvs-repair-profile-run', disabled: this.busy || !!this.gate(), title: this.gate() || 'Explicitly start a new LVS extraction/comparison; preparation did not start it.', onclick: () => this.start() })].filter(Boolean));
      return;
    }
    host.replaceChildren(...[title,
      status.error ? el('p', { class: 'generation-error', text: status.error.message }) : null,
      this.repairPreparation()].filter(Boolean));
  }
  gate() {
    const p = this.project();
    if (p.readOnly || p.envelope.workspace_identity?.read_only) return 'This preserved system is read-only.';
    if (!this.data.implemented || !p.envelope.workflow.find(stage => stage.id === 'lvs')?.implemented) return 'LVS execution is not implemented by the connected service.';
    if (p.conflict) return 'A newer saved design was detected. Export your draft, then Open saved.';
    if (p.dirty) return 'Save the complete design before LVS execution.';
    if (p.busy) return 'Wait for the current project operation to finish.';
    if (this.data.storage_error) return this.data.storage_error.message || 'LVS execution history is unavailable.';
    if (this.uncertainStart || this.pollError) return this.pollError || 'The start outcome is unknown. Refresh saved runs; this request is not automatically resent.';
    if (this.anyActive()) return 'A model or tool run is active. Inspect or cancel it before starting another.';
    if (!this.data.ready || !this.sources()) return this.data.blocked_reason || 'Current adopted S11 layout and S12 DRC for this exact saved revision are required.';
    if (!this.data.tool_ready) return this.data.tool_blocked_reason || 'The fixed extraction/LVS runtime and PDK are not ready.';
    return '';
  }
  render(host) {
    this.host = host;
    host.replaceChildren(
      el('div', { class: 'spec-intro' }, badge('S13 · Layout versus schematic'), badge('Exact adopted physical circuit'), el('p', { text: 'Extract the circuit from the current adopted S11 GDS and compare it with the corresponding mapped netlist using recorded PDK rules. Current S12 DRC is required. Post-layout functional/timing verification remains a separate stage; this view does not establish dynamic SDF qualification.' })),
      card('Frozen LVS execution', 'Inspect the S11/S12 identities, exact GDS and mapped-netlist hashes, and pinned extraction/comparison configuration.', el('div', { class: 'provider-actions' }, el('button', { type: 'button', class: 'primary', text: 'Run LVS', 'data-testid': 'lvs-workflow-run', onclick: () => this.start() }), el('button', { type: 'button', text: 'Inspect S11 layout', onclick: () => this.callbacks.navigate('layout') }), el('button', { type: 'button', text: 'Inspect S12 DRC', onclick: () => this.callbacks.navigate('drc') }), el('button', { type: 'button', text: 'Refresh saved LVS runs', 'data-testid': 'lvs-workflow-refresh', onclick: () => this.refreshSaved() })), el('p', { class: 'generation-gate', 'data-testid': 'lvs-workflow-gate' }), el('div', { class: 'workflow-lineage', 'data-testid': 'lvs-workflow-lineage' }), el('p', { class: 'scope-note', text: 'S13 first records the powered-netlist hash from the original S11 output and requires structural correspondence with the retained mapped netlist and DEF before execution.' }), el('div', { 'data-testid': 'lvs-workflow-configuration' })),
      el('section', { class: 'card', 'data-testid': 'lvs-repair-profile-card' }),
      card('LVS verification evidence', 'Inspect connectivity/device comparisons, reported mismatches, complete diagnostics and raw extraction/LVS reports before choosing the next action.', el('div', { 'data-testid': 'lvs-workflow-result' })),
      card('Saved LVS attempts', 'Each execution is a separate record. Failed and stale results remain inspectable.', el('div', { class: 'generation-job-list', 'data-testid': 'lvs-workflow-history' })));
    this.refresh(); this.schedule();
  }
  refresh() {
    if (!this.host?.isConnected || this.project().stage !== 'lvs') return;
    const button = this.host.querySelector('[data-testid="lvs-workflow-run"]'); if (!button) return;
    const gate = this.gate(), sources = this.sources();
    button.disabled = this.busy || !!gate; button.title = gate || 'Extract the exact adopted S11 GDS and compare its circuit with the matching mapped netlist.';
    this.host.querySelector('[data-testid="lvs-workflow-refresh"]').disabled = this.busy || this.polling;
    this.host.querySelector('[data-testid="lvs-workflow-gate"]').textContent = this.busy ? 'Contacting the local LVS execution service…' : gate || 'Ready. Required LVS checks and adoption use the saved policy.';
    const poweredHash = this.data.source_inputs?.powered_netlist?.sha256 || this.data.input_powered_netlist_sha256 || this.data.runs.findLast(run => run.layout_run_id === sources?.layout.id && run.drc_run_id === sources?.drc.id)?.input_powered_netlist_sha256;
    this.host.querySelector('[data-testid="lvs-workflow-lineage"]').replaceChildren(el('p', { text: `Saved revision ${this.project().envelope.revision.id}` }), el('p', { text: `Adopted S11 ${sources?.layout.id || 'Not available'}` }), el('p', { text: `Adopted S12 ${sources?.drc.id || 'Not available'}` }), el('p', { text: `Input GDS SHA-256 ${sources?.gds.sha256 || 'Not available'}` }), el('p', { text: `Mapped netlist SHA-256 ${sources?.netlist.sha256 || 'Not available'}` }), el('p', { text: `Powered mapped netlist SHA-256 ${poweredHash || 'Recorded by the fixed S13 source check before execution'}` }), el('p', { text: `LVS configuration SHA-256 ${this.data.configuration_sha256 || 'Not configured'}` }));
    this.host.querySelector('[data-testid="lvs-workflow-configuration"]').replaceChildren(this.inspect('Recorded extraction/LVS runtime and PDK configuration', this.data.runtime_configuration));
    this.renderRepairProfile(); this.renderResult(); this.renderHistory(); if (this.reviewHost?.isConnected) this.renderReview(this.reviewHost); this.callbacks.chrome?.();
  }
  artifactURL(run, id) { return `/api/artifacts/lvs-workflow/${encodeURIComponent(run.id)}/${id}`; }
  artifacts(run) { return (run.artifacts || []).filter(item => FILES.has(item.id) && item.url === this.artifactURL(run, item.id)); }
  comparisonSummary(summary) {
    const rows = [
      ['Extraction illegal overlaps', summary?.extraction?.illegal_overlap_count],
      ['Extraction feedback items', summary?.extraction?.feedback_item_count],
      ['Non-overlap extraction feedback', summary?.extraction?.non_overlap_feedback_count],
      ['LVS match status', summary?.lvs?.match_status], ['Compared circuit pairs', summary?.lvs?.comparison_count],
      ['LVS errors', summary?.lvs?.error_count], ['Device count differences', summary?.lvs?.device_difference_count],
      ['Net count differences', summary?.lvs?.net_difference_count], ['Property failures', summary?.lvs?.property_fail_count],
      ['Unmatched devices', summary?.lvs?.unmatched_device_count], ['Unmatched nets', summary?.lvs?.unmatched_net_count],
      ['Unmatched pins', summary?.lvs?.unmatched_pin_count],
    ];
    const display = (label, value) => value === undefined || value === null ? 'Not reported' : label === 'LVS match status' ? String(value) : typeof value !== 'number' || !Number.isFinite(value) || !Number.isInteger(value) || value < 0 ? `Invalid count (${String(value)})` : String(value);
    return el('div', { class: 'workflow-lineage', 'data-testid': 'lvs-workflow-comparison-summary' }, rows.map(([label, value]) => el('p', { text: `${label}: ${display(label, value)}` })), summary?.extraction?.feedback_scope ? el('p', { class: 'scope-note', text: summary.extraction.feedback_scope }) : null);
  }
  renderResult() {
    const host = this.host?.querySelector('[data-testid="lvs-workflow-result"]'); if (!host) return;
    const run = this.selected();
    if (!run) { host.replaceChildren(...[el('p', { class: 'empty-small', text: 'No LVS execution evidence exists. S11 routing and S12 DRC do not establish connectivity equivalence.' }), this.reconnect()].filter(Boolean)); return; }
    const checks = run.checks || {}, lineage = Object.fromEntries(['revision_id', 'layout_run_id', 'drc_run_id', 'layout_record_sha256', 'drc_record_sha256', 'input_gds_sha256', 'input_netlist_sha256', 'input_powered_netlist_sha256', 'source_inputs', 'configuration_sha256', 'source_identity', 'source_key', 'source_epoch_at_start', 'acceptance_epoch'].filter(key => Object.hasOwn(run, key)).map(key => [key, run[key]]));
    host.replaceChildren(...[
      el('div', { class: 'generation-summary', 'data-testid': 'lvs-workflow-status' }, badge(run.execution_status), badge(run.validation_status, run.validation_status === 'Passed' ? 'teal' : 'orange'), badge(run.review_status), badge(run.freshness), el('code', { text: run.id })),
      run.error ? el('div', { class: 'generation-error', text: `${run.error.code || 'Execution error'} · ${run.error.message || JSON.stringify(run.error)}` }) : null,
      active(run) ? el('div', { class: 'generation-progress' }, el('span', { class: 'generation-spinner', 'aria-hidden': true }), el('span', { text: 'Actual layout extraction and LVS comparison in progress' }), el('button', { type: 'button', text: 'Cancel LVS run', 'data-testid': 'lvs-workflow-cancel', disabled: this.busy, onclick: () => this.cancel(run) })) : null,
      el('p', { class: 'scope-note', 'data-testid': 'lvs-workflow-scope', text: 'Results apply to the exact retained layout, mapped netlist and recorded PDK extraction/comparison rules. Missing reports or nonnumeric counts are not zero mismatches. LVS checks connectivity/device correspondence; it does not establish dynamic SDF behavior, electrical performance or fabrication readiness.' }),
      ...(run.diagnostics || []).map(item => el('div', { class: `diagnostic ${item.severity || 'info'}`, 'data-testid': 'lvs-workflow-diagnostic' }, badge(item.severity || 'info'), el('code', { text: item.code || '' }), el('span', { text: item.message || JSON.stringify(item) }))),
      this.comparisonSummary(checks.summary),
      checks.summary?.extraction?.recognition_proof ? this.inspect('Recorded extraction-model recognition proof · not a waiver', checks.summary.extraction.recognition_proof, { 'data-testid': 'lvs-workflow-recognition-proof' }) : null,
      this.inspect('Required LVS verification checks', checks.checks || {}, { open: true, 'data-testid': 'lvs-workflow-checks' }),
      this.inspect('Reported extraction/LVS counts and metrics', checks.metrics || {}, { open: true, 'data-testid': 'lvs-workflow-metrics' }),
      this.inspect('Reported mismatches and comparison summary', checks.summary || checks.report_summary || run.summary || { availability: 'No structured comparison summary was returned. Inspect the complete raw reports below.' }, { open: true, 'data-testid': 'lvs-workflow-mismatches' }),
      this.inspect('All commands, raw logs, warnings, reports and output record', checks, { 'data-testid': 'lvs-workflow-logs' }),
      this.inspect('Frozen S11/S12, GDS, mapped netlist, runtime and source lineage', lineage, { 'data-testid': 'lvs-workflow-frozen-input' }),
      this.inspect('Exact adopted S11 snapshot', run.layout_snapshot), this.inspect('Exact adopted S12 snapshot', run.drc_snapshot), this.inspect('Recorded runtime configuration', run.runtime_configuration),
      el('p', { class: 'scope-note', text: 'JSON previews use browser number precision. JSON downloads preserve the exact backend response text. Raw artifact downloads verify the saved hash and byte count.' }),
      el('div', { class: 'generation-artifact-actions' }, el('button', { type: 'button', text: 'Download LVS run JSON', 'data-testid': 'lvs-workflow-download-run', onclick: () => downloadJsonResponse(`/api/lvs-workflow/runs/${encodeURIComponent(run.id)}`, `${safe(run.id)}.json`, this.callbacks.notify) }), JSON_FIELDS.map(id => el('button', { type: 'button', text: 'Download ' + id, 'data-testid': 'lvs-workflow-download-' + id, onclick: () => downloadJsonResponse(this.artifactURL(run, id), `${safe(run.id)}-${id}.json`, this.callbacks.notify) })), this.artifacts(run).map(item => el('button', { type: 'button', text: `Download ${item.id.toUpperCase()} · ${item.bytes} bytes`, 'data-testid': 'lvs-workflow-download-' + item.id, onclick: () => this.downloadFile(run, item) }))), this.reconnect(),
    ].filter(Boolean));
  }
  async downloadFile(run, item) {
    try {
      if (!FILES.has(item.id) || item.url !== this.artifactURL(run, item.id)) throw new Error('This artifact is outside the fixed LVS routes.');
      const response = await sessionFetch(this.artifactURL(run, item.id), { cache: 'no-store', credentials: 'same-origin' }); if (!response.ok) throw new Error(`Artifact download failed (${response.status}).`);
      const bytes = new Uint8Array(await response.arrayBuffer()), digest = Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', bytes))).map(value => value.toString(16).padStart(2, '0')).join('');
      if (digest !== item.sha256 || bytes.length !== item.bytes) throw new Error('Artifact bytes do not match the saved hash and size. The download was stopped.');
      const url = URL.createObjectURL(new Blob([bytes], { type: item.content_type || 'application/octet-stream' })); const link = el('a', { href: url, download: `${safe(run.id)}-${item.id}.${EXTENSIONS[item.id] || 'json'}` }); document.body.append(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (error) { this.callbacks.notify(error.message, 'error'); }
  }
  renderHistory() {
    const host = this.host?.querySelector('[data-testid="lvs-workflow-history"]'); if (!host) return;
    host.replaceChildren(...(this.data.runs.length ? this.data.runs.toReversed().map(run => el('button', { type: 'button', class: `generation-job-button${run.id === this.selected()?.id ? ' selected' : ''}`, 'data-testid': 'lvs-workflow-run-' + run.id, onclick: () => { this.runId = run.id; this.refresh(); } }, badge(run.execution_status), badge(run.validation_status), badge(run.review_status), badge(run.freshness), el('code', { text: run.id }), el('small', { text: `S11 ${run.layout_run_id} · S12 ${run.drc_run_id} · ${run.created_at || ''}` }))) : [el('p', { class: 'empty-small', text: 'No recorded LVS attempts.' })]));
  }
  renderReview(host) {
    if (!host) return; this.reviewHost = host; const run = this.selected(); if (!run) { host.replaceChildren(el('p', { text: 'Run the fixed LVS checks to inspect evidence and adoption.' })); return; }
    const p = this.project(), reviewable = run.id === this.data.latest_run_id && !active(run) && !p.dirty && !p.conflict && !p.busy && !this.busy && !this.anyActive(), reviews = this.data.reviews.filter(item => item.run_id === run.id), decision = reviews.findLast(item => item.decision === 'accepted');
    const old = host.querySelector('[data-testid="lvs-workflow-feedback"]'), focused = old === document.activeElement, selection = focused ? [old.selectionStart, old.selectionEnd] : null;
    const note = el('textarea', { rows: 3, value: this.notes.get(run.id) || '', 'aria-label': 'LVS feedback', 'data-testid': 'lvs-workflow-feedback', placeholder: 'Describe the connectivity/device mismatch or requested correction.', oninput: event => this.notes.set(run.id, event.target.value) }), target = this.targets.get(run.id) || 'layout';
    host.replaceChildren(el('div', { class: 'generation-review-status' }, badge(run.review_status), badge(run.freshness), el('code', { text: run.id })), el('p', { class: 'scope-note', 'data-testid': 'lvs-workflow-adoption-provenance', text: decision?.actor === 'automation_policy' ? `Recorded adoption by authorized policy ${decision.provenance?.policy_id || decision.policy_id || ''}; this is not a manual human click.` : run.review_status === 'Accepted' && decision ? 'Accepted by explicit review; its actor and provenance are recorded below.' : 'Required LVS checks for current sources must pass before adoption. Inspect failures and return for corrections as needed.' }), el('div', { class: 'field' }, el('label', { text: 'Review and debug feedback' }), note), field('Return destination', target, value => this.targets.set(run.id, value), { choices: RETURNS, 'data-testid': 'lvs-workflow-return-target' }), el('div', { class: 'review-actions' }, el('button', { type: 'button', class: 'primary', text: run.review_status === 'Accepted' ? 'LVS accepted' : 'Accept verified LVS run', 'data-testid': 'lvs-workflow-accept', disabled: !reviewable || run.freshness !== 'Current' || run.validation_status !== 'Passed' || run.review_status === 'Accepted', onclick: () => this.review(run, 'accepted', note.value) }), el('button', { type: 'button', text: 'Request Changes', 'data-testid': 'lvs-workflow-request-changes', disabled: !reviewable, onclick: () => this.review(run, 'changes_requested', note.value) }), el('button', { type: 'button', text: 'Return to selected stage', 'data-testid': 'lvs-workflow-return', disabled: !reviewable, onclick: () => this.review(run, 'return_to_stage', note.value, this.targets.get(run.id) || target) }), el('button', { type: 'button', text: 'S14 Post-layout Verification', 'data-testid': 'lvs-workflow-continue', disabled: !reviewable || !current(run) || !p.envelope.workflow.find(stage => stage.id === 'post_layout_verification')?.implemented, onclick: () => this.callbacks.navigate('post_layout_verification') })), this.inspect('Exact LVS adoption and feedback records', reviews));
    if (focused) { note.focus({ preventScroll: true }); note.setSelectionRange(...selection); }
  }
  reconnect() { return this.pollError || this.uncertainStart ? el('div', { class: 'generation-error' }, el('p', { text: this.pollError || 'The start outcome is unknown. Refresh saved history without resending.' }), el('button', { type: 'button', text: 'Reconnect without resending', 'data-testid': 'lvs-workflow-reconnect', disabled: this.busy || this.polling, onclick: () => this.refreshSaved() })) : null; }
  async prepareRepairProfile() {
    if (this.repairGate()) return;
    const p = this.project(), source = this.repairSource(), scope = this.repairScope();
    const body = { layout_run_id: source.layout.id, drc_run_id: source.drc.id, source_lvs_run_id: source.run.id, revision_id: p.envelope.revision.id };
    this.busy = true; this.refresh();
    try {
      const response = await this.callbacks.request('lvs-workflow/repair-profile', body);
      if (scope !== this.repairScope()) return;
      this.callbacks.envelope(response);
      this.callbacks.toast('Prepared the corrected LVS extraction profile only. No EDA, model, geometry change or adoption was started. Run LVS separately and inspect the new evidence.');
    } catch (error) {
      if (scope === this.repairScope()) {
        this.pollError = `${error.message} Profile preparation may have completed. Refresh saved status without resending before deciding whether to retry.`;
        this.callbacks.notify(this.pollError, 'error');
      }
    } finally { this.busy = false; this.refresh(); }
  }
  async start() {
    if (this.busy || this.gate()) return; const p = this.project(), sources = this.sources(); this.busy = true; this.refresh();
    try { const response = await this.callbacks.request('lvs-workflow/runs', { stage: 'lvs', layout_run_id: sources.layout.id, drc_run_id: sources.drc.id, revision_id: p.envelope.revision.id }); this.runId = response.lvs_workflow?.latest_run_id; this.pollError = null; this.uncertainStart = false; this.callbacks.envelope(response); this.callbacks.toast('LVS started from the exact adopted S11 circuit and S12 DRC source chain.'); }
    catch (error) { this.uncertainStart = true; this.pollError = `${error.message} Refresh saved runs; the request is not automatically resent.`; this.callbacks.notify(this.pollError, 'error'); }
    finally { this.busy = false; this.refresh(); this.schedule(); }
  }
  async cancel(run) { if (this.busy) return; this.busy = true; this.refresh(); try { this.callbacks.envelope(await this.callbacks.request(`lvs-workflow/runs/${encodeURIComponent(run.id)}/cancel`, {})); } catch (error) { this.callbacks.notify(`${error.message} Refresh saved history to inspect cancellation.`, 'error'); } finally { this.busy = false; this.refresh(); this.schedule(); } }
  async review(run, decision, note, target) {
    if (this.busy) return; if (decision !== 'accepted' && !note.trim()) { this.callbacks.toast('Record the issue or return reason first.'); return; } this.busy = true; this.refresh();
    try { this.callbacks.envelope(await this.callbacks.request(`lvs-workflow/runs/${encodeURIComponent(run.id)}/review`, { decision, note: note.trim(), ...(target ? { target_stage: target } : {}) })); if (target) this.callbacks.navigate(target); } catch (error) { this.callbacks.notify(error.message, 'error'); } finally { this.busy = false; this.refresh(); }
  }
  async refreshSaved() { if (this.busy || this.polling) return; this.polling = true; this.refresh(); try { this.callbacks.envelope(await this.callbacks.request('project')); this.pollError = null; this.uncertainStart = false; } catch (error) { this.pollError = `${error.message} The tool request is not resent.`; this.callbacks.notify(this.pollError, 'error'); } finally { this.polling = false; this.refresh(); this.schedule(); } }
  schedule() { if (this.pollTimer || this.polling || this.pollError || (!this.data.runs.some(active) && !this.pendingPolicy())) return; this.pollTimer = setTimeout(() => { this.pollTimer = null; this.poll(); }, 1500); }
  async poll() { if (this.polling) return; this.polling = true; this.refresh(); try { const response = await this.callbacks.request('lvs-workflow'); this.callbacks.workflow(response.lvs_workflow); this.pollError = null; this.pollCount = (this.pollCount || 0) + 1; if (!this.data.runs.some(active) || this.pollCount % 3 === 0) this.callbacks.envelope(await this.callbacks.request('project')); } catch (error) { this.pollError = `${error.message} Reconnecting reads saved progress without resending execution.`; } finally { this.polling = false; this.refresh(); this.schedule(); } }
}
