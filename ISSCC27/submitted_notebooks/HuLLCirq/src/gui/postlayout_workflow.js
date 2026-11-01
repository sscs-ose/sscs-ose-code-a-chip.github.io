import { sessionFetch } from './workspace_transport.js';
import { element as el, field, badge, downloadJsonResponse } from './dom.js';

const active = run => !!run && ['Queued', 'Running'].includes(run.execution_status);
const current = run => run?.execution_status === 'Completed' && run.validation_status === 'Passed' && run.review_status === 'Accepted' && run.freshness === 'Current';
const safe = value => String(value).replace(/[^a-z0-9_.-]/gi, '_');
const adapterSignature = value => JSON.stringify(value && typeof value === 'object' && !Array.isArray(value) ? Object.fromEntries(Object.entries(value).sort(([a], [b]) => a.localeCompare(b))) : value);
const card = (title, text, ...children) => el('section', { class: 'card' }, el('div', { class: 'card-heading' }, el('h2', { text: title }), el('p', { text })), ...children);
const JSON_FIELDS = ['layout-record', 'drc-record', 'lvs-record', 'source-identity', 'runtime-configuration', 'verification-plan', 'artifact-manifest'];
// Fixed adapter IDs only: a saved record never supplies an arbitrary path or URL.
const FILES = new Set(['input-gds', 'input-def', 'input-netlist', 'input-powered-netlist', 'input-sdf', 'cell-models', 'timed-testbench', 'public-vectors', 'configuration', 'source-binding', 'tool-versions', 'annotation-report', 'timing-check-report', 'simulation-report', 'simulation-waveform', 'worker-request', 'worker-report', 'compile-stdout', 'compile-stderr', 'simulation-stdout', 'simulation-stderr', 'frozen-verification-plan', 'source-layout-state', 'simulation-plot', 'event-transcript', 'event-manifest', 'event-summary', 'event-audit-report', 'conditional-path-report', 'native-delay-readback', 'native-delay-manifest', 'functional-provenance', 'sta-report', 'sta-log', 'sta-input-manifest', 'sta-constraints', 'sta-parasitics', 'sta-liberty', 'completion-report', 'functional-testbench', 'functional-models', 'functional-report']);
const EXTENSIONS = { 'input-gds': 'gds', 'input-def': 'def', 'input-netlist': 'v', 'input-powered-netlist': 'v', 'input-sdf': 'sdf', 'cell-models': 'v', 'timed-testbench': 'v', 'public-vectors': 'json', 'compile-stdout': 'log', 'compile-stderr': 'log', 'simulation-stdout': 'log', 'simulation-stderr': 'log', 'simulation-waveform': 'vcd', 'simulation-plot': 'png', 'event-transcript': 'tsv', 'event-manifest': 'tsv', 'native-delay-readback': 'tsv', 'native-delay-manifest': 'tsv', 'sta-log': 'log', 'sta-constraints': 'sdc', 'sta-parasitics': 'spef', 'sta-liberty': 'lib', 'functional-testbench': 'v', 'functional-models': 'v' };
const POST_ROUTE_METHOD = 'Routed-netlist functional simulation + extracted STA';
const PHYSICAL_REPAIR_CHECKS = ['source_identity', 'configuration', 'functional', 'parasitics', 'constraints', 'setup_hold', 'electrical'];
const GENERIC_CLOSURE_V1 = 'hullcirq-sky130-generic-closure-v1';
const genericClosure = version => [GENERIC_CLOSURE_V1, 'hullcirq-sky130-generic-closure-v2'].includes(version);
const RETURNS = [['global_settings', 'Global Settings'], ['graph_editor', 'Graph Editor'], ['specifications', 'Specifications'], ['local_rtl_generation', 'Local RTL Generation'], ['local_synthesis', 'Local Synthesis'], ['local_netlist_simulation', 'Local Netlist Simulation'], ['node_implementation_specs', 'Node Implementation Specs'], ['global_rtl_generation', 'Global RTL Generation'], ['global_synthesis', 'Global Synthesis'], ['global_netlist_simulation', 'Global Netlist Simulation'], ['layout', 'Layout'], ['drc', 'DRC'], ['lvs', 'LVS']];

/** S14 distinguishes readiness, retained diagnostics and qualified execution. */
export class PostlayoutWorkflow {
  constructor(callbacks) {
    this.callbacks = callbacks; this.data = { runs: [], reviews: [], ready: false, tool_ready: false, profile_prepare_available: false, profile_update_available: false, profile_prepare_needed: false };
    this.runId = null; this.notes = new Map(); this.targets = new Map(); this.inspectors = new Map();
    this.busy = false; this.polling = false; this.pollTimer = null; this.pollError = null; this.uncertainStart = false;
    this.fileView = null; this.fileToken = 0;
    this.adapterDrafts = new Map();
  }
  project() { return this.callbacks.project(); }
  selected() { return this.data.runs.find(run => run.id === this.runId) || this.data.runs.at(-1); }
  scope(run) { return run?.execution_scope || run?.runtime_configuration?.execution_scope || run?.checks?.execution_scope || (run ? undefined : this.data.execution_scope); }
  postRoute(run) { return this.scope(run) === 'post_route_functional_plus_sta'; }
  eventDiagnostic(run) { return this.scope(run) === 'saved_event_diagnostic_review'; }
  diagnostic(run) { return ['saved_dynamic_diagnostic_review', 'saved_event_diagnostic_review'].includes(this.scope(run)); }
  nativeDiagnostics(run) {
    if (this.eventDiagnostic(run)) {
      const note = run.checks?.summary?.native_diagnostics_note;
      return typeof note === 'string' ? note : 'Inspect the saved annotation-report, conditional-path-report, native-delay-readback and event-audit-report for the exact native diagnostics, finite observation scope and remaining barriers. This saved review starts no new tool execution. S14 remains Unsupported.';
    }
    return 'The saved native annotation log retains two empty-typ metadata errors for VOLTAGE and TEMPERATURE; their missing values were not filled. It also reports 1,991 ignored TIMINGCHECK warnings. Independent finite trace audits do not establish native timing-check support. Inspect annotation-report for the exact source lines and warnings. S14 remains Unsupported.';
  }
  preflight(run) { const scope = this.scope(run), supported = run ? run.runtime_configuration?.verification_supported ?? run.verification_supported : this.data.verification_supported; return scope === 'compatibility_preflight_only' || (!scope && supported === false); }
  unsupported(run) { return this.preflight(run) || this.diagnostic(run) || (run ? run.runtime_configuration?.verification_supported ?? run.verification_supported : this.data.verification_supported) === false; }
  actionLabel() { return this.eventDiagnostic() ? 'Validate saved event diagnostic' : this.diagnostic() ? 'Validate saved timed diagnostic' : this.preflight() ? 'Check S14 readiness' : 'Run post-layout verification'; }
  fileExtension(run, item) { return (this.diagnostic(run) && item.id === 'cell-models' || this.postRoute(run)) && item.content_type?.startsWith('application/json') ? 'json' : EXTENSIONS[item.id] || 'json'; }
  fileContext(run) { const p = this.project(); return JSON.stringify([p.design?.id, p.envelope.revision.id, run?.id, run?.source_key, run?.source_epoch_at_start, run?.acceptance_epoch, run?.source_identity, (run?.artifacts || []).map(item => [item.id, item.sha256, item.bytes, item.url])]); }
  clearFile() { this.fileToken++; if (this.fileView?.imageURL) URL.revokeObjectURL(this.fileView.imageURL); this.fileView = null; }
  completionSummary(run) {
    const summary = run.checks?.summary || run.summary || {}, criteria = Array.isArray(summary.completion_criteria) ? summary.completion_criteria : [];
    const timing = summary.timing_summary || {}, value = key => Number.isFinite(timing[key]) ? String(timing[key]) : 'Not reported';
    return el('section', { class: 'inspector-section postlayout-completion', 'data-testid': 'postlayout-workflow-completion' },
      el('h3', { text: POST_ROUTE_METHOD }),
      el('p', { text: 'Completion requires the original job to pass on the adopted routed netlist, with its extracted parasitics, declared timing constraints and required STA checks. Inspect each recorded result below.' }),
      el('div', { class: 'generation-summary' }, badge(`Functional simulation: ${summary.functional_status || 'Not reported'}`), badge(`Extracted STA: ${summary.sta_status || 'Not reported'}`)),
      criteria.length ? el('table', { class: 'implementation-port-table', 'data-testid': 'postlayout-workflow-completion-criteria' },
        el('thead', {}, el('tr', {}, el('th', { scope: 'col', text: 'Completion requirement' }), el('th', { scope: 'col', text: 'Result' }), el('th', { scope: 'col', text: 'Evidence / remaining work' }))),
        el('tbody', {}, criteria.map(item => el('tr', {}, el('th', { scope: 'row', text: item.label || item.id || 'Unnamed requirement' }), el('td', { text: item.status || 'Not reported' }), el('td', { text: item.detail || 'Inspect the required checks and raw report.' }))))) : el('p', { text: active(run) ? 'Tools are running. Completion results will appear when recorded; no intermediate pass is inferred.' : 'Completion requirements have not been reported. Inspect the run error and required checks.' }),
      el('p', { 'data-testid': 'postlayout-workflow-timing-summary', text: `STA corners: ${value('corner_count')} · Clock period: ${value('clock_period_ns')} ns · Setup violations: ${value('setup_violations')} · Hold violations: ${value('hold_violations')} · Max slew: ${value('max_slew_violations')} · Max capacitance: ${value('max_cap_violations')} · Max fanout: ${value('max_fanout_violations')}` }),
      summary.reason ? el('p', { 'data-testid': 'postlayout-workflow-completion-reason', text: summary.reason }) : null);
  }
  inspect(title, value, attrs = {}) {
    const key = `${this.selected()?.id || 'configuration'}:${attrs['data-testid'] || title}`;
    if (!this.inspectors.has(key)) this.inspectors.set(key, {});
    const state = this.inspectors.get(key), source = typeof value === 'string' ? value : JSON.stringify(value ?? {}, null, 2), size = 32768, count = Math.max(1, Math.ceil(source.length / size));
    const host = el('details', { class: 'raw-result', ...attrs, open: state.open ?? attrs.open, ontoggle: () => { state.open = host.open; } }, el('summary', { text: title }));
    if (source.length <= size * 2) { host.append(el('pre', { text: source })); return host; }
    state.page = Math.min(Math.max(state.page || 0, 0), count - 1);
    const prefix = attrs['data-testid'] || 'postlayout-inspector-' + safe(title), preview = el('pre', { 'data-testid': prefix + '-segment' }), range = el('p', { class: 'scope-note', 'data-testid': prefix + '-range' });
    const buttons = [['first', 'First segment', () => 0], ['previous', 'Previous segment', () => state.page - 1], ['next', 'Next segment', () => state.page + 1], ['last', 'Last segment', () => count - 1]].map(([id, label, destination]) => el('button', { type: 'button', text: label, 'data-testid': prefix + '-' + id, onclick: () => { state.page = destination(); display(); } }));
    const display = () => { const start = state.page * size, end = Math.min(start + size, source.length); preview.textContent = source.slice(start, end); range.textContent = `Segment ${state.page + 1} of ${count} · characters ${start + 1}–${end} of ${source.length}. Every segment is available. Download the original for exact bytes and JSON number precision.`; buttons[0].disabled = buttons[1].disabled = state.page === 0; buttons[2].disabled = buttons[3].disabled = state.page === count - 1; };
    host.append(range, el('div', { class: 'provider-actions' }, buttons), preview); display(); return host;
  }
  adoptedSources() {
    const e = this.project().envelope;
    const layout = e.physical_workflow?.runs?.find(run => run.id === e.physical_workflow.accepted_run_id), drc = e.drc_workflow?.runs?.find(run => run.id === e.drc_workflow.accepted_run_id), lvs = e.lvs_workflow?.runs?.find(run => run.id === e.lvs_workflow.accepted_run_id);
    if (![layout, drc, lvs].every(current) || typeof layout.revision_id !== 'string' || !layout.revision_id
      || drc.revision_id !== layout.revision_id || lvs.revision_id !== layout.revision_id
      || drc.layout_run_id !== layout.id || lvs.layout_run_id !== layout.id || lvs.drc_run_id !== drc.id
      || (e.physical_workflow.latest_run_id && e.physical_workflow.latest_run_id !== layout.id)
      || (e.drc_workflow.latest_run_id && e.drc_workflow.latest_run_id !== drc.id)
      || (e.lvs_workflow.latest_run_id && e.lvs_workflow.latest_run_id !== lvs.id)) return null;
    const gds = layout.artifacts?.find(item => item.id === 'gds'), netlist = layout.artifacts?.find(item => item.id === 'netlist');
    if (!gds || !netlist || drc.input_gds_sha256 !== gds.sha256 || lvs.input_gds_sha256 !== gds.sha256 || lvs.input_netlist_sha256 !== netlist.sha256) return null;
    return { layout, drc, lvs, gds, netlist };
  }
  sources() {
    const source = this.adoptedSources(); if (!source) return null;
    const { layout, drc, lvs } = source, e = this.project().envelope;
    // Source IDs are pinned by the backend when its fixed profile is ready.
    // A missing profile can return all-null IDs: allow only preparation from
    // the backend's current adopted upstream chain, never an S14 run.
    const references = [['layout_run_id', layout.id], ['drc_run_id', drc.id], ['lvs_run_id', lvs.id]];
    const prepareOnly = this.data.profile_prepare_available === true && this.data.ready === false
      && this.data.tool_ready === false && references.every(([key]) => this.data[key] === null);
    if (references.some(([key]) => Object.hasOwn(this.data, key))
      ? !prepareOnly && references.some(([key, id]) => typeof this.data[key] !== 'string' || this.data[key] !== id)
      : layout.revision_id !== e.revision.id) return null;
    return source;
  }
  preparationSources() {
    const source = this.sources(); if (source) return source;
    const metadata = this.data.profile_preparation_sources, adopted = this.adoptedSources(), e = this.project().envelope;
    if (!adopted || this.data.profile_prepare_available !== true || metadata?.available !== true
      || metadata.scope !== 'adopted_source_chain_for_explicit_profile_preparation_only'
      || metadata.revision_id !== e.revision.id || metadata.source_revision_id !== adopted.layout.revision_id) return null;
    const fields = [['physical_runtime_sha256', adopted.layout.runtime_configuration_sha256],
      ['verification_plan_sha256', adopted.layout.verification_plan_sha256], ['settings_sha256', adopted.layout.settings_sha256]];
    for (const name of ['layout', 'drc', 'lvs']) {
      if (metadata[name + '_run_id'] !== adopted[name].id) return null;
      fields.push([name + '_record_hash', adopted[name].record_hash]);
    }
    if (fields.some(([key, value]) => typeof value !== 'string' || !/^[a-f0-9]{64}$/i.test(value) || metadata[key] !== value)) return null;
    // This status identifies an explicit profile/metadata preparation context,
    // not executable S14 sources. Run and physical correction use sources().
    return adopted;
  }
  receive(envelope) {
    if (envelope.postlayout_workflow) {
      this.data = envelope.postlayout_workflow;
      const key = this.adapterKey(), draft = this.adapterDrafts.get(key);
      if (draft && draft.baseHash !== this.data.adapter_contract_sha256) {
        try {
          const signature = adapterSignature(JSON.parse(draft.text));
          if (signature === draft.base || signature === adapterSignature(this.data.adapter_contract || null)) this.adapterDrafts.delete(key);
        } catch { /* Preserve an invalid or newer local adapter draft. */ }
      }
    }
    if (this.fileView && this.fileView.context !== this.fileContext(this.selected())) this.clearFile(); this.refresh(); this.schedule();
  }
  pendingPolicy() { const policy = this.project().envelope.review_policy, run = this.data.runs.find(item => item.id === this.data.latest_run_id); return !this.unsupported(run) && policy?.mode === 'accept_on_pass' && policy.user_authorized === true && !this.data.storage_error && run?.execution_status === 'Completed' && run.validation_status === 'Passed' && run.review_status === 'Awaiting Review' && run.freshness === 'Current' && !run.error && !(run.diagnostics || []).some(item => item.code === 'automatic_adoption_blocked'); }
  anyActive() { const e = this.project().envelope; return [this.data.runs, e.lvs_workflow?.runs || [], e.drc_workflow?.runs || [], e.physical_workflow?.runs || [], e.global_workflow?.runs || [], e.workflow_runs || [], e.global_generation?.jobs || [], e.generation?.jobs || []].some(runs => runs.some(active)); }
  physicalRepairEligible(run) {
    const checks = run?.checks;
    const sources = this.sources();
    const sourceRevisionMatches = run?.revision_id === this.project().envelope.revision.id ||
      (!!sources && run?.revision_id === sources.layout.revision_id && run.layout_run_id === sources.layout.id
        && run.drc_run_id === sources.drc.id && run.lvs_run_id === sources.lvs.id);
    return !!run && run.id === this.data.latest_run_id && sourceRevisionMatches
      && run.freshness === 'Current' && run.execution_status === 'Completed' && run.validation_status === 'Failed'
      && !run.error && run.evidence_kind === 'trusted_fixed_postlayout_execution' && run.verification_supported === true
      && this.postRoute(run) && checks?.origin === 'trusted_fixed_postlayout_adapter'
      && checks.execution_scope === 'post_route_functional_plus_sta' && checks.status === 'Completed'
      && checks.validation_status === 'Failed' && checks.executed === true && checks.exit_code === 0
      && checks.cleanup_unresolved !== true && checks.software_qa_fixture !== true
      && Array.isArray(checks.commands) && checks.commands.length === 11
      && checks.commands.every(command => command?.executed === true && command.status === 'Completed' && command.exit_code === 0 && command.cleanup_unresolved !== true)
      && Object.keys(checks.checks || {}).length === PHYSICAL_REPAIR_CHECKS.length
      && PHYSICAL_REPAIR_CHECKS.every(name => checks.checks?.[name]?.validation_status === (name === 'electrical' ? 'Failed' : 'Passed'));
  }
  physicalRepairGate(run) {
    const p = this.project(), status = p.envelope.physical_repair_session || {};
    if (p.readOnly || p.envelope.workspace_identity?.read_only) return 'This preserved system is read-only.';
    if (this.pollError || this.uncertainStart) return 'Refresh saved correction status without resending before preparing or executing another action.';
    const repeat = status.configured && genericClosure(status.profile_version) && this.physicalRepairEligible(run);
    if (status.configured && !repeat) return 'The fixed physical correction profile is already prepared.';
    if (status.error) return status.error.message || 'Refresh the saved correction status.';
    if (status.bundle_present && !repeat) return 'A saved physical correction profile already exists. Refresh its saved status.';
    if (p.conflict) return 'A newer saved design was detected. Open the saved design before preparing correction.';
    if (p.dirty) return 'Save the complete design before preparing physical correction.';
    if (p.busy || this.busy || this.anyActive()) return 'Wait for active project, model and tool work to finish.';
    if (this.data.storage_error) return this.data.storage_error.message || 'Saved S14 history is unavailable.';
    if (!this.physicalRepairEligible(run)) return 'Select the latest current completed S14 run with only electrical checks failed.';
    return '';
  }
  renderPhysicalRepair() {
    const host = this.host?.querySelector('[data-testid="postlayout-physical-repair-card"]'); if (!host) return;
    const status = this.project().envelope.physical_repair_session || {}, run = this.selected();
    host.hidden = !status.configured && !status.bundle_present && !this.physicalRepairEligible(run);
    if (host.hidden) { host.replaceChildren(); return; }
    const title = el('div', { class: 'card-heading' }, el('h2', { text: 'Fixed physical correction' }));
    const generic = genericClosure(status.profile_version) || this.sources()?.layout.verification_plan?.kind === 'generic_cycle_vectors';
    const clockDescription = generic ? 'original saved clock' : 'original 50 ns clock';
    if (status.configured && !(genericClosure(status.profile_version) && this.physicalRepairEligible(run))) {
      host.replaceChildren(...[title,
        el('p', { text: `The fixed physical correction profile was prepared by an explicit GUI action. The ${clockDescription}, SDC constraints, workload and expected values are preserved. Preparation starts no EDA; run and verify the new S11 → S12 → S13 → S14 chain.` }),
        generic ? el('p', { class: 'scope-note', text: 'Generic closure starts a fresh technology mapping, placement, CTS, routing and closure run only after Run physical layout. No previous physical checkpoint or accepted result is reused. Mixed placement only; block-region fences are not silently dropped. Preparation does not execute or adopt any stage.' }) : null,
        el('p', { text: `Source S14: ${status.source_identity?.failed_s14_id || 'Recorded in the saved correction profile'}` }),
        el('button', { type: 'button', text: 'Go to Layout', 'data-testid': 'postlayout-physical-repair-layout',
          disabled: this.busy || this.project().busy || !!this.project().conflict || this.project().dirty || this.anyActive(), onclick: () => this.callbacks.navigate('layout') })].filter(Boolean));
      return;
    }
    const gate = this.physicalRepairGate(run);
    host.replaceChildren(...[title,
      el('p', { text: `Prepare the fixed correction profile for this electrical-only failure. The ${clockDescription}, SDC constraints, workload and expected values remain unchanged. This starts no EDA; completion requires new S11 → S12 → S13 → S14 runs.` }),
      generic ? el('p', { class: 'scope-note', text: 'For the saved generic cycle-vector plan, preparation selects fresh mapping/placement/CTS/routing closure, not an NPU checkpoint retry. Only Mixed placement is supported; a saved block-region plan is rejected rather than discarded. Run physical layout remains a separate explicit action.' }) : null,
      status.error ? el('p', { class: 'generation-error', text: status.error.message }) : null,
      status.configured && generic ? el('p', { class: 'scope-note', text: 'Prepare another immutable fresh correction, with five percentage points lower core utilization (minimum 10%). Original expectations, RTL, clock and all signoff checks remain fixed. No automatic retry or guarantee of closure.' }) : null,
      el('button', { type: 'button', text: status.configured && generic ? 'Prepare next generic physical correction' : 'Prepare fixed physical correction', 'data-testid': 'postlayout-physical-repair-prepare', disabled: !!gate, title: gate || 'Validate the saved failed result and prepare its fixed physical runtime without starting EDA.', onclick: () => this.preparePhysicalRepair(run) })].filter(Boolean));
  }
  prepareGate() {
    const p = this.project();
    if (p.readOnly || p.envelope.workspace_identity?.read_only) return 'This preserved system is read-only.';
    if (this.pollError || this.uncertainStart) return 'Refresh saved status without resending before preparing another profile.';
    if (!this.data.profile_prepare_available) return 'GUI preparation is unavailable because this service uses an explicit profile or has no pinned compiler configuration.';
    if (p.conflict) return 'A newer saved design was detected. Export your draft, then Open saved.';
    if (p.dirty) return 'Save the complete design before preparing S14.';
    if (p.busy) return 'Wait for the current project operation to finish.';
    if (this.data.storage_error) return this.data.storage_error.message || 'Post-layout execution history is unavailable.';
    if (this.data.runs.some(run => run.checks?.cleanup_unresolved === true && !run.cleanup_resolution)) return 'Verify saved process termination before preparing the S14 profile.';
    if (this.anyActive()) return 'A model or tool run is active. Inspect or cancel it before preparing S14.';
    if (!this.preparationSources()) return this.data.profile_preparation_sources?.blocked_reason || 'Current adopted S11 layout, S12 DRC and S13 LVS for this exact saved revision are required.';
    if (this.adapterDirty()) return 'Save the project-specific adapter metadata before preparing S14.';
    if (this.data.adapter_contract_required) return this.data.adapter_contract_reason || 'Configure this project’s testbench adapter metadata before preparing S14.';
    return '';
  }
  blocker() {
    if (!this.preparationSources()) return null;
    if (this.data.adapter_contract_editable && (this.data.adapter_contract_required || this.adapterDirty())) return {
      kind: 'configuration_required', message: this.data.adapter_contract_reason || 'Review and save the adapter metadata for this project’s original testbench. The saved job, clock conditions and expected outputs are not edited here.',
      setup_action: { label: this.adapterDirty() && !this.adapterProblem() ? 'Save this project’s adapter metadata' : 'Configure this project’s adapter metadata', testId: this.adapterDirty() && !this.adapterProblem() ? 'postlayout-adapter-save' : 'postlayout-adapter-settings' },
    };
    if (this.data.profile_prepare_available === true && (this.data.profile_prepare_needed === true || this.data.profile_update_available === true || this.data.tool_ready !== true)) {
      return { kind: 'configuration_required', message: this.data.profile_configuration_error?.message || this.data.blocked_reason || 'Prepare the S14 execution profile from this project’s saved verification plan and current adopted source chain.',
        setup_action: { label: this.data.profile_update_available ? 'Update this project’s S14 profile' : 'Prepare this project’s S14 profile', testId: 'postlayout-workflow-prepare' } };
    }
    return null;
  }
  gate() {
    const p = this.project();
    if (!this.data.implemented || !p.envelope.workflow.find(stage => stage.id === 'post_layout_verification')?.implemented) return 'Post-layout verification is not implemented by the connected service.';
    if (p.conflict) return 'A newer saved design was detected. Export your draft, then Open saved.';
    if (p.dirty) return 'Save the complete design before post-layout verification.';
    if (p.busy) return 'Wait for the current project operation to finish.';
    if (this.data.storage_error) return this.data.storage_error.message || 'Post-layout execution history is unavailable.';
    if (this.uncertainStart || this.pollError) return 'The request outcome or saved status is uncertain. Refresh saved runs; no request is automatically resent.';
    if (this.anyActive()) return 'A model or tool run is active. Inspect or cancel it before starting another.';
    if (this.adapterDirty()) return 'Save the project-specific adapter metadata before post-layout verification.';
    if (!this.data.ready || !this.sources()) return this.data.blocked_reason || 'Current adopted S11 layout, S12 DRC and S13 LVS for this exact saved revision are required.';
    if (!this.data.tool_ready) return this.data.tool_blocked_reason || (this.postRoute() ? 'The pinned functional simulator, STA tools and extracted timing inputs are not ready.' : 'The pinned timing simulator, cell models and SDF configuration are not ready.');
    return '';
  }
  render(host) {
    this.host = host;
    host.replaceChildren(el('div', { class: 'spec-intro' }, badge('S14 · Post-layout verification'), badge('Original GUI job · adopted physical circuit'), el('p', { 'data-testid': 'postlayout-workflow-intro' })),
      card('Frozen S14 inputs and execution scope', 'Inspect the exact S11/S12/S13 source chain, original job and recorded verification method before execution.', el('div', { class: 'provider-actions' }, el('button', { type: 'button', class: 'primary', text: 'Prepare fixed S14 profile', 'data-testid': 'postlayout-workflow-prepare', onclick: () => this.prepare() }), el('button', { type: 'button', class: 'primary', text: this.actionLabel(), 'data-testid': 'postlayout-workflow-run', onclick: () => this.start() }), ...[['layout', 'Inspect S11 layout'], ['drc', 'Inspect S12 DRC'], ['lvs', 'Inspect S13 LVS']].map(([stage, label]) => el('button', { type: 'button', text: label, onclick: () => this.callbacks.navigate(stage) })), el('button', { type: 'button', text: 'Refresh saved post-layout runs', 'data-testid': 'postlayout-workflow-refresh', onclick: () => this.refreshSaved() })), el('p', { class: 'generation-gate', 'data-testid': 'postlayout-workflow-gate' }), el('div', { class: 'workflow-lineage', 'data-testid': 'postlayout-workflow-lineage' }), el('div', { 'data-testid': 'postlayout-workflow-configuration' })),
      el('section', { class: 'card', 'data-testid': 'postlayout-adapter-card' }),
      el('section', { class: 'card', 'data-testid': 'postlayout-physical-repair-card' }),
      card('Post-layout verification evidence', 'Inspect required checks, compatibility limits, available outputs, warnings and complete raw records before choosing the next action.', el('div', { 'data-testid': 'postlayout-workflow-result' })),
      card('Saved post-layout attempts', 'Failed, unsupported, cancelled and stale attempts remain recorded. A rerun creates a new record.', el('div', { class: 'generation-job-list', 'data-testid': 'postlayout-workflow-history' })));
    this.refresh(); this.schedule();
  }
  refresh() {
    if (!this.host?.isConnected || this.project().stage !== 'post_layout_verification') return;
    const button = this.host.querySelector('[data-testid="postlayout-workflow-run"]'), prepare = this.host.querySelector('[data-testid="postlayout-workflow-prepare"]'); if (!button || !prepare) return;
    const gate = this.gate(), prepareGate = this.prepareGate(), sources = this.preparationSources(), inputs = this.data.source_inputs || {}, preflight = this.preflight(), diagnostic = this.diagnostic(), postRoute = this.postRoute();
    const updating = this.data.profile_update_available === true;
    const preparingCurrentLayout = this.data.profile_prepare_needed === true;
    const prepareVisible = this.data.profile_prepare_available === true && (this.data.tool_ready !== true || updating || preparingCurrentLayout);
    prepare.hidden = !prepareVisible; prepare.disabled = this.busy || !!prepareGate;
    prepare.textContent = updating ? 'Prepare updated S14 profile' : 'Prepare fixed S14 profile';
    prepare.title = prepareGate || (updating ? 'Explicitly update the host-managed S14 profile after read-only input/runtime checks. Earlier attempts are preserved. This starts no EDA or model process and creates no S14 attempt.' : 'Derive and save the fixed S14 profile from the exact adopted S11 runtime and the server-pinned compiler. This starts no EDA or model process and creates no S14 attempt.');
    button.textContent = this.actionLabel(); button.disabled = this.busy || !!gate; button.title = gate || (diagnostic ? 'Recheck retained original timed-run bytes and source bindings. No new simulator process is started; S14 adoption stays disabled.' : preflight ? 'Check source and runtime compatibility without starting a simulator or permitting adoption.' : 'Verify the inherited job using the exact adopted physical circuit and recorded timing scope.');
    this.host.querySelector('[data-testid="postlayout-workflow-intro"]').textContent = postRoute ? 'Routed-netlist functional simulation + extracted STA. Execute the original GUI job on the adopted routed netlist; separately check setup, hold and electrical limits using extracted parasitics and declared constraints. SDF delay simulation is not part of this method.' : diagnostic ? 'An actual timed diagnostic of the original GUI job is retained. This action rechecks saved outputs, exact adopted S11/S12/S13 sources and process provenance; it starts no new simulator process. Unqualified timing semantics keep S14 Unsupported and prevent adoption.' : preflight ? 'Dynamic simulation is unsupported with this runtime; this check does not start a simulator or permit adoption. Freeze the original GUI job and adopted physical inputs, then inspect the recorded compatibility barriers.' : 'Execute the inherited verification plan on the adopted mapped circuit with recorded extracted timing and PDK cell models. Inspect annotation coverage, dynamic results and limitations separately from S11 static timing and S13 connectivity checks.';
    this.host.querySelector('[data-testid="postlayout-workflow-refresh"]').disabled = this.busy || this.polling;
    const prepareMessage = updating ? 'An updated S14 profile is available. The saved profile remains in use until you explicitly prepare the update. Preparation performs read-only input/runtime checks, preserves earlier attempts, starts no EDA or model process and creates no S14 attempt.' : preparingCurrentLayout ? 'The saved S14 profile belongs to an earlier physical runtime. Prepare it for the current adopted S11/S12/S13 chain. Preparation preserves earlier attempts, starts no EDA or model process and creates no S14 attempt.' : `The fixed S14 profile is not ready. Prepare it from the current adopted source chain; this performs read-only input/runtime checks and starts no EDA or model process.${this.data.profile_configuration_error?.message ? ' Saved profile issue: ' + this.data.profile_configuration_error.message : ''}`;
    this.host.querySelector('[data-testid="postlayout-workflow-gate"]').textContent = this.busy ? 'Contacting the local S14 service…' : prepareVisible && !prepareGate ? prepareMessage : gate || (postRoute ? 'Ready. Completion requires functional, parasitic, constraint, setup/hold and electrical checks to pass on the same saved source chain.' : diagnostic ? 'Ready to validate the saved timed diagnostic only. The retained tool run is not repeated and S14 cannot be adopted.' : preflight ? 'Ready for a compatibility check only. Dynamic simulation remains unsupported; this cannot produce an accepted S14 result.' : 'Ready. Required dynamic and timing-coverage checks use the saved adoption policy.');
    const plan = sources?.layout.verification_plan, job = plan?.recipe?.source_job;
    const generic = plan?.kind === 'generic_cycle_vectors';
    const jobSummary = generic ? ['Generic cycle vectors v1', ...(Number.isInteger(plan.vector_count) ? [`${plan.vector_count} saved cycles`] : []), ...(Number.isInteger(plan.coverage?.output_assertions) ? [`${plan.coverage.output_assertions} independent output-pin assertions`] : []), ...(Number.isFinite(plan.interface?.clock?.period_ns) ? [`${plan.interface.clock.period_ns} ns saved clock`] : [])].join(' · ') : job ? [job.id || 'Saved source job', ...(Number.isInteger(job.k) ? [`K=${job.k}`] : []), ...(typeof job.relu === 'boolean' ? [`ReLU ${job.relu ? 'enabled' : 'disabled'}`] : []), ...(Number.isInteger(plan.output_count) ? [`${plan.output_count} expected outputs`] : [])].join(' · ') : null;
    this.host.querySelector('[data-testid="postlayout-workflow-lineage"]').replaceChildren(...[['Saved revision', this.project().envelope.revision.id], ['Adopted S11', sources?.layout.id], ['Adopted S12', sources?.drc.id], ['Adopted S13', sources?.lvs.id], [generic ? 'Saved independent cycle contract' : 'Original GUI job', jobSummary], ['Inherited verification plan SHA-256', this.data.verification_plan_sha256], ['Input GDS SHA-256', sources?.gds.sha256], ['Mapped netlist SHA-256', sources?.netlist.sha256], ...(postRoute ? [['Verification method', POST_ROUTE_METHOD]] : [['SDF corner', inputs.sdf?.corner], ['SDF SHA-256', inputs.sdf?.sha256 || this.data.input_sdf_sha256]]), ['Runtime configuration SHA-256', this.data.configuration_sha256]].map(([label, value]) => el('p', { text: `${label}: ${value || 'Not available'}` })));
    this.host.querySelector('[data-testid="postlayout-workflow-configuration"]').replaceChildren(this.inspect(postRoute ? 'Recorded functional simulator, STA inputs and configuration' : 'Recorded simulator, timing corner, cell models and configuration', this.data.runtime_configuration, { 'data-testid': 'postlayout-workflow-runtime' }), this.inspect('Source inputs and original verification plan', { source_inputs: inputs, verification_plan: this.data.verification_plan, limits: this.data.limits }, { 'data-testid': 'postlayout-workflow-inputs' }));
    this.renderAdapterContract(); this.renderPhysicalRepair(); this.renderResult(); this.renderHistory(); if (this.reviewHost?.isConnected) this.renderReview(this.reviewHost); this.callbacks.chrome?.();
  }
  adapterKey() {
    const p = this.project(), s = this.preparationSources();
    return JSON.stringify([p.envelope.workspace_identity, p.envelope.revision.id, s?.layout.id, s?.drc.id, s?.lvs.id, s?.gds.sha256, s?.netlist.sha256]);
  }
  adapterContext() {
    const p = this.project(), identity = p.envelope.workspace_identity || {};
    return JSON.stringify([identity.project_id || p.design?.project?.id || p.design?.id || 'legacy', identity.system_id || 'system']);
  }
  adapterBackup() {
    const context = this.adapterContext(), records = [];
    for (const [key, draft] of this.adapterDrafts) {
      if (draft.context !== context) continue;
      try { if (adapterSignature(JSON.parse(draft.text)) === draft.base) continue; } catch { /* Preserve invalid text too. */ }
      records.push({ key, context, text: draft.text, base: draft.base, baseHash: draft.baseHash ?? null });
    }
    return records;
  }
  adapterBackupDirty() { return this.adapterBackup().length > 0; }
  restoreAdapterBackup(records) {
    if (!Array.isArray(records)) return;
    const context = this.adapterContext(), identity = this.project().envelope.workspace_identity;
    for (const record of records) {
      if (!record || record.context !== context || typeof record.key !== 'string' || typeof record.text !== 'string' || typeof record.base !== 'string' || !(record.baseHash == null || typeof record.baseHash === 'string')) continue;
      let parts;
      try { parts = JSON.parse(record.key); } catch { continue; }
      if (!Array.isArray(parts) || parts.length !== 7 || typeof parts[1] !== 'string' || parts.slice(2).some(part => part !== null && typeof part !== 'string')) continue;
      // A reload can create a new transport session, but never changes the
      // revision/source IDs/hashes to which the preserved text belongs.
      const key = JSON.stringify([identity, ...parts.slice(1)]);
      if (!this.adapterDrafts.has(key)) this.adapterDrafts.set(key, { text: record.text, base: record.base, baseHash: record.baseHash, context });
    }
  }
  adapterDraft() {
    const key = this.adapterKey();
    if (!this.adapterDrafts.has(key)) {
      const initial = this.data.adapter_contract || {
        version: 'external-port-functional-v1', testbench_module: '', dut_instance: '', clock_signal: '', clock_statement: '', timeout_statement: '', output_prefix: '', pass_marker: '', failure_markers: [],
      };
      this.adapterDrafts.set(key, { text: JSON.stringify(initial, null, 2), base: adapterSignature(initial), baseHash: this.data.adapter_contract_sha256, context: this.adapterContext() });
    }
    return this.adapterDrafts.get(key);
  }
  adapterParsed() { try { return JSON.parse(this.adapterDraft().text); } catch { return null; } }
  adapterDirty() {
    if (this.data.adapter_contract_editable !== true) return false;
    try { return adapterSignature(JSON.parse(this.adapterDraft().text)) !== this.adapterDraft().base; } catch { return true; }
  }
  adapterProblem() {
    const value = this.adapterParsed(), keys = this.data.adapter_contract_fields || ['version', 'testbench_module', 'dut_instance', 'clock_signal', 'clock_statement', 'timeout_statement', 'output_prefix', 'pass_marker', 'failure_markers'];
    if (!value || typeof value !== 'object' || Array.isArray(value) || Object.keys(value).length !== keys.length || Object.keys(value).some(key => !keys.includes(key))) return 'Use only the listed adapter metadata fields. Testbench text, job, clock period and expected outputs cannot be changed here.';
    if (value.version !== 'external-port-functional-v1' || keys.filter(key => key !== 'failure_markers').some(key => typeof value[key] !== 'string' || !value[key].trim()) || !Array.isArray(value.failure_markers) || !value.failure_markers.length || value.failure_markers.some(marker => typeof marker !== 'string' || !marker.trim())) return 'Complete every adapter metadata field and provide at least one failure marker. The backend checks these against the original saved testbench.';
    return '';
  }
  adapterSaveGate() {
    const p = this.project();
    if (!this.data.adapter_contract_editable) return 'This service does not expose project-specific adapter editing.';
    if (p.readOnly || p.envelope.workspace_identity?.read_only) return 'This preserved system is read-only.';
    if (p.conflict || p.dirty) return 'Resolve the design draft or saved-version conflict before saving adapter metadata.';
    if (p.busy || this.busy || this.anyActive()) return 'Wait for active project, model and tool operations to finish.';
    if (!this.preparationSources()) return this.data.profile_preparation_sources?.blocked_reason || 'Current adopted S11/S12/S13 sources are required.';
    if (this.adapterDraft().baseHash !== this.data.adapter_contract_sha256) return 'The saved adapter changed. Your local metadata draft is retained; refresh and compare the saved contract below before proceeding.';
    return this.adapterProblem() || (!this.adapterDirty() ? 'No adapter metadata changes to save.' : '');
  }
  updateAdapterActions() {
    const save = this.host?.querySelector('[data-testid="postlayout-adapter-save"]'), status = this.host?.querySelector('[data-testid="postlayout-adapter-status"]');
    if (!save || !status) return;
    const gate = this.adapterSaveGate(); save.disabled = !!gate; save.title = gate || 'Explicitly save adapter metadata without changing original verification inputs or starting tools.';
    status.textContent = this.adapterProblem() || (this.adapterDirty() ? gate || 'Unsaved browser-only adapter metadata. Save explicitly before preparation or execution.' : 'Adapter metadata matches its saved or derived source. Viewing and typing do not save or run anything.');
  }
  renderAdapterContract() {
    const host = this.host?.querySelector('[data-testid="postlayout-adapter-card"]'); if (!host) return;
    host.hidden = this.data.adapter_contract_editable !== true;
    if (host.hidden) { host.replaceChildren(); return; }
    const draft = this.adapterDraft(), p = this.project();
    const editor = el('textarea', { rows: 16, value: draft.text, disabled: p.readOnly || p.envelope.workspace_identity?.read_only || p.busy || this.busy || this.anyActive(), 'aria-label': 'Project verification adapter metadata', 'data-testid': 'postlayout-adapter-contract', oninput: event => {
      draft.text = event.target.value; this.updateAdapterActions(); this.callbacks.draftChanged?.(); this.callbacks.chrome?.();
    } });
    host.replaceChildren(el('div', { class: 'card-heading' }, el('h2', { text: 'This project’s verification adapter' }), el('p', { text: 'Use the original saved external-port testbench and expected results. Only exact adapter metadata is configurable here; no NPU-specific job or expected values are substituted.' })),
      this.inspect('Original verification inputs · read-only', this.data.adapter_contract_original, { 'data-testid': 'postlayout-adapter-original' }),
      this.inspect('Currently saved or derived adapter metadata', { source: this.data.adapter_contract_source, sha256: this.data.adapter_contract_sha256, contract: this.data.adapter_contract, required: this.data.adapter_contract_required, reason: this.data.adapter_contract_reason, fields: this.data.adapter_contract_fields }),
      el('p', { class: 'scope-note', text: 'Draft changes remain in this browser until Save adapter metadata. Saving does not alter the source testbench, GUI job, expected outputs or saved clock constraints, and starts no model, EDA or verification attempt.' }),
      el('button', { type: 'button', text: 'Review adapter metadata', 'data-testid': 'postlayout-adapter-settings', onclick: () => editor.focus() }), editor,
      el('p', { role: 'status', class: 'generation-gate', 'data-testid': 'postlayout-adapter-status' }),
      el('button', { type: 'button', text: 'Save adapter metadata', 'data-testid': 'postlayout-adapter-save', onclick: () => this.saveAdapterContract() }));
    this.updateAdapterActions();
  }
  async saveAdapterContract() {
    if (this.adapterSaveGate()) return;
    const key = this.adapterKey(), draft = this.adapterDraft(), submitted = draft.text, contract = this.adapterParsed(), p = this.project(), sources = this.preparationSources();
    this.busy = true; this.refresh();
    try {
      const response = await this.callbacks.request('postlayout-workflow/adapter-contract', { layout_run_id: sources.layout.id, drc_run_id: sources.drc.id, lvs_run_id: sources.lvs.id, revision_id: p.envelope.revision.id, contract });
      if (key !== this.adapterKey()) return;
      if (draft.text === submitted) this.adapterDrafts.delete(key);
      else { draft.base = adapterSignature(contract); draft.baseHash = response.postlayout_workflow?.adapter_contract_sha256; }
      this.callbacks.envelope(response); this.callbacks.toast('Saved project-specific adapter metadata. Original verification inputs and all earlier attempts were preserved; no tool or model was started.');
    } catch (error) { if (key === this.adapterKey()) this.callbacks.notify(`${error.message} Adapter draft retained. Refresh saved status before deciding whether to retry; no save request is automatically resent.`, 'error'); }
    finally { this.busy = false; this.callbacks.draftChanged?.(); this.refresh(); }
  }
  artifactURL(run, id) { return `/api/artifacts/postlayout-workflow/${encodeURIComponent(run.id)}/${encodeURIComponent(id)}`; }
  artifacts(run) { return (run.artifacts || []).filter(item => FILES.has(item.id) && item.url === this.artifactURL(run, item.id)); }
  renderResult() {
    const host = this.host?.querySelector('[data-testid="postlayout-workflow-result"]'); if (!host) return;
    const run = this.selected();
    if (!run) { host.replaceChildren(...[el('p', { class: 'empty-small', text: this.postRoute() ? 'No completed run exists for routed-netlist functional simulation + extracted STA. Start verification to obtain its recorded completion checks.' : this.diagnostic() ? 'The fixed original timed diagnostic is available for a saved-output integrity review. No review record has been created. S14 qualification remains Unsupported.' : 'No dynamic post-layout execution evidence exists. Routing, static timing, DRC and LVS do not establish SDF simulation behavior.' }), this.reconnect()].filter(Boolean)); return; }
    const checks = run.checks || {}, lineage = Object.fromEntries(['revision_id', 'layout_run_id', 'drc_run_id', 'lvs_run_id', 'layout_record_sha256', 'drc_record_sha256', 'lvs_record_sha256', 'input_gds_sha256', 'input_netlist_sha256', 'input_powered_netlist_sha256', 'input_sdf_sha256', 'source_inputs', 'configuration_sha256', 'source_identity', 'source_key', 'source_epoch_at_start', 'acceptance_epoch'].filter(key => Object.hasOwn(run, key)).map(key => [key, run[key]]));
    const files = this.artifacts(run);
    host.replaceChildren(...[
      el('div', { class: 'generation-summary', 'data-testid': 'postlayout-workflow-status' }, badge(run.execution_status), badge(run.validation_status, run.validation_status === 'Passed' ? 'teal' : 'orange'), badge(run.review_status), badge(run.freshness), el('code', { text: run.id })),
      run.error ? el('div', { class: 'generation-error', text: `${run.error.code || 'Execution error'} · ${run.error.message || JSON.stringify(run.error)}` }) : null,
      checks.cleanup_unresolved === true ? el('div', { class: 'generation-summary', 'data-testid': 'postlayout-workflow-cleanup' },
        el('p', { text: run.cleanup_resolution ? 'Saved whole process-group termination was verified. This attempt retains its original failure and verification status; a new run is required.' : 'Saved process termination is unresolved. Verify the original request, process birth and terminal evidence before starting another run.' }),
        !run.cleanup_resolution ? el('button', { type: 'button', text: 'Verify saved process termination', 'data-testid': 'postlayout-workflow-verify-termination',
          disabled: this.busy || this.anyActive() || this.project().busy || !!this.project().conflict || this.project().dirty || run.cleanup_resolution_available !== true,
          onclick: () => this.verifyTermination(run) }) : this.inspect('Saved termination audit', run.cleanup_resolution)) : null,
      active(run) ? el('div', { class: 'generation-progress' }, el('span', { class: 'generation-spinner', 'aria-hidden': true }), el('span', { text: this.postRoute(run) ? 'Running tools for routed-netlist functional simulation and extracted STA. Waiting for recorded results.' : this.diagnostic(run) ? 'Rechecking saved timed diagnostic bytes and process proofs; no new tool run' : this.preflight(run) ? 'Checking exact S14 inputs and runtime compatibility' : 'Actual dynamic post-layout verification in progress' }), el('button', { type: 'button', text: 'Cancel post-layout run', 'data-testid': 'postlayout-workflow-cancel', disabled: this.busy, onclick: () => this.cancel(run) })) : null,
      el('p', { class: 'scope-note', 'data-testid': 'postlayout-workflow-scope', text: this.postRoute(run) ? 'Functional simulation checks the inherited finite job on the routed netlist. Timing is checked separately by STA with extracted parasitics, cell libraries and declared constraints. This result does not claim SDF delay simulation or fabrication readiness.' : this.diagnostic(run) ? 'Saved timed diagnostic review. Actual tool execution occurred in the retained original run; this review starts no new simulator process. Finite output agreement, annotation evidence and timing limitations are reported separately. S14 remains Unsupported and cannot be adopted.' : this.preflight(run) ? 'Compatibility check only. The original job and physical inputs are retained; no dynamic simulator was started and no timing or functional pass is established. Unsupported required checks prevent adoption. Inspect the complete recorded barriers below.' : 'Results apply only to the retained original job, finite verification plan, simulator, timing corner and annotated SDF constructs. Missing or unsupported timing checks are not successful checks. Static timing and dynamic simulation are separate evidence; neither establishes fabrication readiness.' }),
      this.postRoute(run) ? this.completionSummary(run) : null,
      this.diagnostic(run) ? this.inspect('Retained execution and this review', { review_mode: checks.review_mode, retained_actual_tool_execution: checks.executed === true, execution_started_by_this_review: checks.execution_started_by_this_review, retained_execution_configuration_sha256: checks.retained_execution_configuration_sha256, review_configuration_sha256: checks.configuration_sha256, diagnostic_evidence_sha256: checks.diagnostic_evidence_sha256 }, { open: true, 'data-testid': 'postlayout-workflow-diagnostic-execution' }) : null,
      this.diagnostic(run) ? el('p', { class: 'scope-note', 'data-testid': 'postlayout-workflow-native-diagnostics', text: this.nativeDiagnostics(run) }) : null,
      ...(run.diagnostics || []).map(item => el('div', { class: `diagnostic ${item.severity || 'info'}`, 'data-testid': 'postlayout-workflow-diagnostic' }, badge(item.severity || 'info'), el('code', { text: item.code || '' }), el('span', { text: item.message || JSON.stringify(item) }))),
      this.inspect(this.postRoute(run) ? 'Recorded functional and extracted STA summary' : this.eventDiagnostic(run) ? 'Saved event observations, conditional paths and qualification limits' : this.diagnostic(run) ? 'Retained timed diagnostic and qualification limits' : this.preflight(run) ? 'Compatibility barriers and verification scope' : 'Dynamic verification and timing-annotation summary', checks.summary || run.summary || { availability: 'No structured summary was returned. Inspect all required checks and raw output below.' }, { open: !this.postRoute(run), 'data-testid': 'postlayout-workflow-summary' }),
      this.inspect(this.postRoute(run) ? 'Required source, functional, parasitic, constraint, setup/hold and electrical checks' : 'Required dynamic and timing-coverage checks', checks.checks || {}, { open: true, 'data-testid': 'postlayout-workflow-checks' }),
      this.inspect(this.postRoute(run) ? 'Reported functional and extracted STA metrics' : this.preflight(run) ? 'Recorded compatibility metrics' : 'Reported dynamic metrics and original-job results', checks.metrics || {}, { 'data-testid': 'postlayout-workflow-metrics' }),
      this.inspect('All commands, raw logs, warnings, coverage and output record', checks, { 'data-testid': 'postlayout-workflow-logs' }),
      this.inspect('Frozen source identities, timing inputs and original-job lineage', lineage, { 'data-testid': 'postlayout-workflow-frozen-input' }),
      this.inspect('Exact adopted S11 snapshot', run.layout_snapshot), this.inspect('Exact adopted S12 snapshot', run.drc_snapshot), this.inspect('Exact adopted S13 snapshot', run.lvs_snapshot), this.inspect('Original verification plan and timed adapter', run.verification_plan || run.plan), this.inspect('Recorded runtime configuration', run.runtime_configuration),
      el('p', { class: 'scope-note', text: 'JSON previews use browser number precision. JSON downloads preserve exact backend response text. Artifact views and downloads verify the saved hash and byte count.' }),
      el('div', { class: 'generation-artifact-actions' }, el('button', { type: 'button', text: 'Download post-layout run JSON', 'data-testid': 'postlayout-workflow-download-run', onclick: () => downloadJsonResponse(`/api/postlayout-workflow/runs/${encodeURIComponent(run.id)}`, `${safe(run.id)}.json`, this.callbacks.notify) }), JSON_FIELDS.map(id => el('button', { type: 'button', text: 'Download ' + id, 'data-testid': 'postlayout-workflow-download-' + id, onclick: () => downloadJsonResponse(this.artifactURL(run, id), `${safe(run.id)}-${id}.json`, this.callbacks.notify) })), files.map(item => el('button', { type: 'button', text: `Download ${item.id} · ${item.bytes} bytes`, 'data-testid': 'postlayout-workflow-download-' + item.id, onclick: () => this.downloadFile(run, item) }))),
      files.some(item => /^(text\/|application\/json|image\/png)/.test(item.content_type || '')) ? el('div', { class: 'generation-artifact-actions' }, files.filter(item => /^(text\/|application\/json|image\/png)/.test(item.content_type || '')).map(item => el('button', { type: 'button', text: 'View ' + item.id, 'data-testid': 'postlayout-workflow-view-' + item.id, onclick: () => this.viewFile(run, item) }))) : null,
      this.fileView?.context === this.fileContext(run) ? el('div', { 'data-testid': 'postlayout-workflow-file-view' }, this.fileView.imageURL ? el('figure', { class: 'postlayout-plot' }, el('img', { src: this.fileView.imageURL, alt: this.fileView.title }), el('figcaption', { text: this.fileView.title })) : this.inspect(this.fileView.title, this.fileView.text, { open: true, 'data-testid': 'postlayout-workflow-file-text' }), el('button', { type: 'button', text: 'Close artifact view', onclick: () => { this.clearFile(); this.renderResult(); } })) : null,
      this.reconnect(),
    ].filter(Boolean));
  }
  async verifiedFile(run, item) {
    if (!FILES.has(item.id) || item.url !== this.artifactURL(run, item.id)) throw new Error('This artifact is outside the fixed post-layout routes.');
    const response = await sessionFetch(this.artifactURL(run, item.id), { cache: 'no-store', credentials: 'same-origin' }); if (!response.ok) throw new Error(`Artifact download failed (${response.status}).`);
    const bytes = new Uint8Array(await response.arrayBuffer()), digest = Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', bytes))).map(value => value.toString(16).padStart(2, '0')).join('');
    if (digest !== item.sha256 || bytes.length !== item.bytes) throw new Error('Artifact bytes do not match the saved hash and size. The operation was stopped.');
    return bytes;
  }
  async downloadFile(run, item) {
    try { const bytes = await this.verifiedFile(run, item), url = URL.createObjectURL(new Blob([bytes], { type: item.content_type || 'application/octet-stream' })); const link = el('a', { href: url, download: `${safe(run.id)}-${item.id}.${this.fileExtension(run, item)}` }); document.body.append(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000); } catch (error) { this.callbacks.notify(error.message, 'error'); }
  }
  async viewFile(run, item) {
    this.clearFile(); const token = this.fileToken, context = this.fileContext(run);
    try { const bytes = await this.verifiedFile(run, item); if (token !== this.fileToken || context !== this.fileContext(this.selected()) || this.project().stage !== 'post_layout_verification') return; this.fileView = { runId: run.id, context, title: `Verified ${item.id} · ${item.sha256}`, ...(item.content_type === 'image/png' ? { imageURL: URL.createObjectURL(new Blob([bytes], { type: 'image/png' })) } : { text: new TextDecoder('utf-8', { fatal: true }).decode(bytes) }) }; this.renderResult(); } catch (error) { if (token === this.fileToken) this.callbacks.notify(error.message, 'error'); }
  }
  renderHistory() {
    const host = this.host?.querySelector('[data-testid="postlayout-workflow-history"]'); if (!host) return;
    host.replaceChildren(...(this.data.runs.length ? this.data.runs.toReversed().map(run => el('button', { type: 'button', class: `generation-job-button${run.id === this.selected()?.id ? ' selected' : ''}`, 'data-testid': 'postlayout-workflow-run-' + run.id, onclick: () => { this.runId = run.id; this.clearFile(); this.refresh(); } }, badge(run.execution_status), badge(run.validation_status), badge(run.review_status), badge(run.freshness), el('code', { text: run.id }), el('small', { text: `S11 ${run.layout_run_id} · S12 ${run.drc_run_id} · S13 ${run.lvs_run_id} · ${run.created_at || ''}${this.postRoute(run) ? ' · Functional + extracted STA' : this.diagnostic(run) ? ' · Saved diagnostic' : this.preflight(run) ? ' · Readiness' : ''}` }))) : [el('p', { class: 'empty-small', text: 'No recorded post-layout attempts.' })]));
  }
  renderReview(host) {
    if (!host) return; this.reviewHost = host; const run = this.selected(); if (!run) { host.replaceChildren(el('p', { text: 'Run the fixed post-layout checks to inspect evidence and adoption.' })); return; }
    const p = this.project(), reviewable = run.id === this.data.latest_run_id && !active(run) && !p.dirty && !p.conflict && !p.busy && !this.busy && !this.anyActive(), reviews = this.data.reviews.filter(item => item.run_id === run.id), decision = reviews.findLast(item => item.decision === 'accepted');
    const old = host.querySelector('[data-testid="postlayout-workflow-feedback"]'), focused = !!old && old === document.activeElement, selection = focused ? [old.selectionStart, old.selectionEnd] : null;
    const note = el('textarea', { rows: 3, value: this.notes.get(run.id) || '', 'aria-label': 'Post-layout feedback', 'data-testid': 'postlayout-workflow-feedback', placeholder: 'Describe the timing, functional or annotation issue and requested correction.', oninput: event => this.notes.set(run.id, event.target.value) }), target = this.targets.get(run.id) || 'layout';
    host.replaceChildren(el('div', { class: 'generation-review-status' }, badge(run.review_status), badge(run.freshness), el('code', { text: run.id })), el('p', { class: 'scope-note', 'data-testid': 'postlayout-workflow-adoption-provenance', text: decision?.actor === 'automation_policy' ? `Recorded adoption by authorized policy ${decision.provenance?.policy_id || decision.policy_id || ''}; this is not a manual human click.` : run.review_status === 'Accepted' && decision ? 'Accepted by explicit review; its actor and provenance are recorded below.' : this.postRoute(run) ? 'Adoption requires current-source functional simulation, extracted parasitics, constraints, setup/hold and electrical checks to pass. Unsupported or missing checks cannot be accepted.' : 'All mandatory current-source dynamic and timing-scope checks must pass before adoption. Unsupported or missing checks cannot be accepted.' }), el('div', { class: 'field' }, el('label', { text: 'Review and debug feedback' }), note), field('Return destination', target, value => this.targets.set(run.id, value), { choices: RETURNS, 'data-testid': 'postlayout-workflow-return-target' }), el('div', { class: 'review-actions' }, el('button', { type: 'button', class: 'primary', text: run.review_status === 'Accepted' ? 'Post-layout verification accepted' : 'Accept verified post-layout run', 'data-testid': 'postlayout-workflow-accept', disabled: !reviewable || this.unsupported(run) || run.freshness !== 'Current' || run.validation_status !== 'Passed' || run.review_status === 'Accepted', onclick: () => this.review(run, 'accepted', note.value) }), el('button', { type: 'button', text: 'Request Changes', 'data-testid': 'postlayout-workflow-request-changes', disabled: !reviewable, onclick: () => this.review(run, 'changes_requested', note.value) }), el('button', { type: 'button', text: 'Return to selected stage', 'data-testid': 'postlayout-workflow-return', disabled: !reviewable, onclick: () => this.review(run, 'return_to_stage', note.value, this.targets.get(run.id) || target) }), el('button', { type: 'button', text: this.diagnostic() ? 'Repeat saved diagnostic review' : this.preflight() ? 'Repeat S14 readiness check' : 'Rerun current adopted sources', 'data-testid': 'postlayout-workflow-retry', disabled: this.busy || !!this.gate(), onclick: () => this.start() })), this.inspect('Exact post-layout adoption and feedback records', reviews));
    if (focused) { note.focus({ preventScroll: true }); note.setSelectionRange(...selection); }
  }
  reconnect() { return this.pollError || this.uncertainStart ? el('div', { class: 'generation-error' }, el('p', { text: this.pollError || 'The start outcome is unknown. Refresh saved history without resending.' }), el('button', { type: 'button', text: 'Reconnect without resending', 'data-testid': 'postlayout-workflow-reconnect', disabled: this.busy || this.polling, onclick: () => this.refreshSaved() })) : null; }
  async prepare() {
    if (this.busy || this.prepareGate()) return; const p = this.project(), sources = this.preparationSources(), scope = this.adapterKey(), updating = this.data.profile_update_available === true; this.busy = true; this.refresh();
    try {
      const response = await this.callbacks.request('postlayout-workflow/profile', { layout_run_id: sources.layout.id, drc_run_id: sources.drc.id, lvs_run_id: sources.lvs.id, revision_id: p.envelope.revision.id });
      if (scope !== this.adapterKey()) return;
      this.clearFile(); this.pollError = null; this.callbacks.envelope(response);
      this.callbacks.toast(`${updating ? 'Updated' : 'Prepared'} the fixed S14 profile from the exact adopted S11/S12/S13 chain. Earlier attempts were preserved. No EDA, model or S14 verification attempt was started.`);
    } catch (error) { if (scope === this.adapterKey()) this.callbacks.notify(`${error.message} Refresh the saved project before retrying profile preparation.`, 'error'); }
    finally { this.busy = false; this.refresh(); }
  }
  async preparePhysicalRepair(run) {
    if (this.physicalRepairGate(run)) return;
    const revision = this.project().envelope.revision.id, scope = this.adapterKey();
    this.busy = true; this.refresh();
    try {
      const response = await this.callbacks.request('postlayout-workflow/physical-repair-profile', { failed_s14_id: run.id, revision_id: revision });
      if (scope !== this.adapterKey()) return;
      this.clearFile(); this.callbacks.envelope(response);
      this.callbacks.toast('Prepared fixed physical correction through the GUI. No EDA was started. Run the new S11, S12, S13 and S14 chain from Layout.');
      this.callbacks.navigate('layout');
    } catch (error) {
      if (scope === this.adapterKey()) {
        this.pollError = `${error.message} Refresh the saved correction status without resending the preparation request.`;
        this.callbacks.notify(this.pollError, 'error');
      }
    }
    finally { this.busy = false; this.refresh(); }
  }
  async start() {
    if (this.busy || this.gate()) return; const p = this.project(), sources = this.sources(); this.busy = true; this.refresh();
    try { const response = await this.callbacks.request('postlayout-workflow/runs', { stage: 'post_layout_verification', layout_run_id: sources.layout.id, drc_run_id: sources.drc.id, lvs_run_id: sources.lvs.id, revision_id: p.envelope.revision.id }); this.runId = response.postlayout_workflow?.latest_run_id; this.clearFile(); this.pollError = null; this.uncertainStart = false; this.callbacks.envelope(response); this.callbacks.toast(this.postRoute() ? 'Started routed-netlist functional simulation and extracted STA from the original GUI job and exact adopted S11/S12/S13 chain.' : this.diagnostic() ? 'Saved timed diagnostic review started. Retained outputs are rechecked; no new simulator process is launched and S14 remains Unsupported.' : this.preflight() ? 'S14 compatibility check started with the original job and adopted S11/S12/S13 inputs. Dynamic simulation remains unsupported.' : 'Post-layout verification started from the exact adopted S11/S12/S13 chain and inherited job.'); }
    catch (error) { this.uncertainStart = true; this.pollError = `${error.message} Refresh saved runs; the request is not automatically resent.`; this.callbacks.notify(this.pollError, 'error'); }
    finally { this.busy = false; this.refresh(); this.schedule(); }
  }
  async cancel(run) { if (this.busy) return; this.busy = true; this.refresh(); try { this.callbacks.envelope(await this.callbacks.request(`postlayout-workflow/runs/${encodeURIComponent(run.id)}/cancel`, {})); } catch (error) { this.callbacks.notify(`${error.message} Refresh saved history to inspect cancellation.`, 'error'); } finally { this.busy = false; this.refresh(); this.schedule(); } }
  async verifyTermination(run) {
    const p = this.project();
    if (this.busy || this.anyActive() || p.busy || p.conflict || p.dirty || run.cleanup_resolution_available !== true) return;
    this.busy = true; this.refresh();
    try {
      this.callbacks.envelope(await this.callbacks.request(`postlayout-workflow/runs/${encodeURIComponent(run.id)}/verify-termination`, {}));
      this.callbacks.toast('Verified saved process termination. The original failed attempt is preserved; no process or verification was started.');
    } catch (error) { this.callbacks.notify(`${error.message} Execution stays blocked until complete termination evidence is available.`, 'error'); }
    finally { this.busy = false; this.refresh(); }
  }
  async review(run, decision, note, target) {
    if (this.busy) return; if (decision === 'accepted' && this.unsupported(run)) { this.callbacks.toast(this.diagnostic(run) ? 'Saved timed diagnostics remain Unsupported and cannot be adopted as S14 verification.' : 'Compatibility checks cannot be adopted as dynamic post-layout verification.'); return; } if (decision !== 'accepted' && !note.trim()) { this.callbacks.toast('Record the issue or return reason first.'); return; } this.busy = true; this.refresh();
    try { this.callbacks.envelope(await this.callbacks.request(`postlayout-workflow/runs/${encodeURIComponent(run.id)}/review`, { decision, note: note.trim(), ...(target ? { target_stage: target } : {}) })); if (target) this.callbacks.navigate(target); } catch (error) { this.callbacks.notify(error.message, 'error'); } finally { this.busy = false; this.refresh(); }
  }
  async refreshSaved() { if (this.busy || this.polling) return; this.polling = true; this.refresh(); try { this.callbacks.envelope(await this.callbacks.request('project')); this.pollError = null; this.uncertainStart = false; } catch (error) { this.pollError = `${error.message} The tool request is not resent.`; this.callbacks.notify(this.pollError, 'error'); } finally { this.polling = false; this.refresh(); this.schedule(); } }
  schedule() { if (this.pollTimer || this.polling || this.pollError || (!this.data.runs.some(active) && !this.pendingPolicy())) return; this.pollTimer = setTimeout(() => { this.pollTimer = null; this.poll(); }, 1500); }
  async poll() { if (this.polling) return; this.polling = true; this.refresh(); try { const response = await this.callbacks.request('postlayout-workflow'); this.callbacks.workflow(response.postlayout_workflow); this.pollError = null; this.pollCount = (this.pollCount || 0) + 1; if (!this.data.runs.some(active) || this.pollCount % 3 === 0) this.callbacks.envelope(await this.callbacks.request('project')); } catch (error) { this.pollError = `${error.message} Reconnecting reads saved progress without resending execution.`; } finally { this.polling = false; this.refresh(); this.schedule(); } }
}
