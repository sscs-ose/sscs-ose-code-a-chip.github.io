import { sessionFetch } from './workspace_transport.js';
import { element as el, field, badge, downloadJsonResponse } from './dom.js';
import { BlockPlacementView } from './block_placement_view.js';

const active = run => !!run && ['Queued', 'Running'].includes(run.execution_status);
const mapJobActive = job => !!job && ['Queued', 'Running'].includes(job.status);
const FIXED_REPAIR_V1 = 'hullcirq-sky130-route-repair-npu2v1';
const FIXED_REPAIR_V2 = 'hullcirq-sky130-route-repair-npu2v2';
const FIXED_REPAIR_V3 = 'hullcirq-sky130-route-repair-npu2v3';
const GENERIC_CLOSURE_V1 = 'hullcirq-sky130-generic-closure-v1';
const GENERIC_CLOSURE_V2 = 'hullcirq-sky130-generic-closure-v2';
const genericClosure = version => [GENERIC_CLOSURE_V1, GENERIC_CLOSURE_V2].includes(version);
const GENERIC_REPAIR_SESSION_V1 = 'hullcirq-gui-generic-physical-repair-session-v1';
const REPAIR_TARGETS = new Map([[FIXED_REPAIR_V1, FIXED_REPAIR_V2], [FIXED_REPAIR_V2, FIXED_REPAIR_V3]]);
const REPAIR_CHECKS = ['configuration', 'source_identity', 'routing', 'timing', 'electrical'];
const revalidated = run => run?.execution_kind === 'saved_outputs_no_new_tool_start';
const implementationScope = run => {
  const kind = run?.checks?.implementation_kind;
  const configured = run?.runtime_configuration?.profile?.implementation_kind || '';
  if (run?.runtime_configuration?.profile?.profile_version === GENERIC_CLOSURE_V1 || kind === 'fresh_generic_standard_electrical_closure') return 'Generic closure scope: fresh technology mapping, placement, clock-tree synthesis, routing and closure, not a resumed predecessor checkpoint. Inspect this run’s recorded commands for actual execution and results; no earlier physical pass is reused.';
  if (configured.includes('post_timing')) return 'Resumed from a recorded post-timing checkpoint. Earlier mapping, placement, CTS and all-nine-corner timing repair are reused; this run performs the additional standard electrical repair, routing, extraction and final checks.';
  if (kind === 'resumed_post_GRT_route_repair' || configured.includes('post_GRT')) return 'Resumed from a recorded post-global-route checkpoint. Earlier technology mapping, placement and CTS are reused; this run performs the recorded route repair and downstream steps.';
  if (kind === 'resumed_pre_CTS_route_repair' || configured.includes('pre_CTS')) return 'Resumed from a recorded pre-CTS checkpoint. Earlier technology mapping and placement are reused; this run performs the recorded CTS, routing and downstream steps.';
  if (run?.checks?.upstream_technology_mapping_reused === true) return 'This run reuses recorded technology mapping. Inspect its checkpoint and execution records for the exact resumed steps.';
  return run ? 'This selected run records its mapping, placement and routing steps. Inspect the execution profile and raw records for their actual scope.' : 'Select a physical run to inspect its recorded mapping, placement, routing or checkpoint-resume scope. S09/S10 remain its required functional baseline.';
};
const safe = value => String(value).replace(/[^a-z0-9_.-]/gi, '_');
const card = (title, text, ...children) => el('section', { class: 'card' }, el('div', { class: 'card-heading' }, el('h2', { text: title }), el('p', { text })), ...children);
const details = (title, value, attrs = {}) => el('details', { class: 'raw-result', ...attrs }, el('summary', { text: title }), el('pre', { text: JSON.stringify(value ?? {}, null, 2) }));
const JSON_FIELDS = ['source-manifest', 'verification-plan', 'settings', 'runtime-configuration', 'artifact-manifest'];
const BASE_FILES = new Set(['config', 'sdc', 'metrics', 'def', 'gds', 'png', 'netlist', 'final-state', 'tool-versions', 'input-manifest', 'rtl-top']);
const BLOCK_FILES = new Set(['block-input', 'block-plan', 'block-synthesis', 'block-ownership', 'block-capacity', 'block-placement-proof', 'block-flow', 'block-runtime']);
const LEGACY_RTL_FILES = ['control', 'buffer', 'scheduler', 'pe', 'post', 'fifo'].map(id => 'rtl-node-' + id);
const SAFE_NODE_ID = /^[A-Za-z_][A-Za-z0-9_-]*$/;
const sourceNodeIdsAreSafe = ids => {
  const filenames = new Set(['candidate_top.v']);
  const artifactIds = new Set(['rtl-top']);
  for (const id of ids) {
    if (typeof id !== 'string' || !SAFE_NODE_ID.test(id)) return false;
    const filename = (id + '.v').toLowerCase();
    const artifactId = ('rtl-' + id).toLowerCase();
    if (filenames.has(filename) || artifactIds.has(artifactId)) return false;
    filenames.add(filename); artifactIds.add(artifactId);
  }
  return true;
};
const filesFor = run => {
  const blockFiles = (run?.artifacts || []).filter(item => BLOCK_FILES.has(item.id)).map(item => item.id);
  const nodes = run?.source_manifest?.nodes;
  if (!Array.isArray(nodes) || !nodes.length) return new Set([...BASE_FILES, ...LEGACY_RTL_FILES, ...blockFiles]);
  const ids = nodes.map(node => node?.node_id);
  if (!sourceNodeIdsAreSafe(ids)) return new Set([...BASE_FILES, ...blockFiles]);
  return new Set([...BASE_FILES, ...ids.map(id => 'rtl-' + id), ...blockFiles]);
};
const RAW_FILES = new Set(['png', 'gds', 'def', ...BLOCK_FILES]);
const EXTENSIONS = { png: 'png', gds: 'gds', def: 'def', sdc: 'sdc', netlist: 'v', 'rtl-top': 'v', 'block-flow': 'py', 'block-runtime': 'py' };
const RETURNS = [['global_settings', 'Global Settings'], ['graph_editor', 'Graph Editor'], ['specifications', 'Specifications'], ['local_rtl_generation', 'Local RTL Generation'], ['local_synthesis', 'Local Synthesis'], ['local_netlist_simulation', 'Local Netlist Simulation'], ['node_implementation_specs', 'Node Implementation Specs'], ['global_rtl_generation', 'Global RTL Generation'], ['global_synthesis', 'Global Synthesis'], ['global_netlist_simulation', 'Global Netlist Simulation']];

/** S11: recorded physical execution; no LLM request or inferred signoff pass. */
export class PhysicalWorkflow {
  constructor(callbacks) {
    this.callbacks = callbacks; this.data = { runs: [], reviews: [], ready: false, tool_ready: false };
    this.runId = null; this.notes = new Map(); this.targets = new Map(); this.zooms = new Map();
    this.busy = false; this.polling = false; this.pollTimer = null; this.pollError = null; this.uncertainStart = false;
    this.layoutView = 'physical'; this.functionalMap = null; this.functionalMapToken = 0; this.functionalMapAbort = null;
    this.mapGeneration = null; this.mapGenerationToken = 0; this.mapGenerationTimer = null;
    this.mapPublication = null;
    this.blockPlacement = null;
  }
  project() { return this.callbacks.project(); }
  selected() { return this.data.runs.find(run => run.id === this.runId) || this.data.runs.at(-1); }
  sources() {
    const e = this.project().envelope;
    const job = e.global_generation?.jobs?.at(-1);
    const current = run => run?.execution_status === 'Completed' && run.validation_status === 'Passed' && run.review_status === 'Accepted' && run.freshness === 'Current';
    const adopted = stage => e.global_workflow?.runs?.find(run => run.id === e.global_workflow.stages?.find(item => item.stage_id === stage)?.accepted_run_id);
    const synthesis = adopted('global_synthesis'), netlist = adopted('global_netlist_simulation');
    return e.global_generation?.ready === true && current(job) && current(synthesis) && current(netlist)
      && typeof job.revision_id === 'string' && !!job.revision_id && synthesis.revision_id === job.revision_id && netlist.revision_id === job.revision_id
      && (!e.global_generation.latest_job_id || e.global_generation.latest_job_id === job.id)
      && synthesis.global_job_id === job.id && netlist.global_job_id === job.id && (netlist.synthesis_run_id || netlist.prior_run_id) === synthesis.id ? { job, synthesis, netlist } : null;
  }
  receive(envelope) { if (envelope.physical_workflow) this.data = envelope.physical_workflow; this.refresh(); this.schedule(); }
  pendingPolicy() {
    const policy = this.project().envelope.review_policy, run = this.data.runs.find(item => item.id === this.data.latest_run_id);
    return policy?.mode === 'accept_on_pass' && policy.user_authorized === true && !this.data.storage_error && run?.execution_status === 'Completed' && run.validation_status === 'Passed' && run.review_status === 'Awaiting Review' && run.freshness === 'Current' && !run.error && !(run.diagnostics || []).some(item => item.code === 'automatic_adoption_blocked');
  }
  anyActive() {
    const e = this.project().envelope;
    return [this.data.runs, e.postlayout_workflow?.runs || [], e.drc_workflow?.runs || [], e.lvs_workflow?.runs || [], e.global_workflow?.runs || [], e.workflow_runs || [], e.global_generation?.jobs || [], e.generation?.jobs || [], e.repair_analysis?.jobs || [], e.generation_batches?.batches || []].some(runs => runs.some(active));
  }
  genericRepairEligible(run) {
    const checks = run?.checks, sources = this.sources();
    const revisionMatches = run?.revision_id === this.project().envelope.revision.id ||
      (!!sources && run?.revision_id === sources.job.revision_id && run.global_job_id === sources.job.id
        && run.synthesis_run_id === sources.synthesis.id && run.netlist_run_id === sources.netlist.id);
    return !!run && genericClosure(run.runtime_configuration?.profile?.profile_version)
      && run.id === this.data.latest_run_id && revisionMatches && run.freshness === 'Current'
      && run.execution_status === 'Completed' && run.validation_status === 'Failed' && run.review_status !== 'Accepted'
      && !run.error && run.evidence_kind === 'trusted_fixed_tool_execution' && checks?.software_qa_fixture !== true
      && checks?.origin === 'trusted_fixed_tool_adapter' && checks.status === 'Completed' && checks.validation_status === 'Failed'
      && checks.executed === true && checks.exit_code === 0 && checks.cleanup_unresolved === false
      && checks.technology_mapping_executed === true && checks.upstream_technology_mapping_reused === false
      && checks.implementation_kind === 'fresh_generic_standard_electrical_closure'
      && Array.isArray(checks.commands) && checks.commands.length === 2
      && checks.commands.every(command => command?.executed === true && command.status === 'Completed' && command.exit_code === 0 && command.cleanup_unresolved !== true)
      && Object.keys(checks.checks || {}).length === REPAIR_CHECKS.length
      && REPAIR_CHECKS.every(name => checks.checks?.[name]?.validation_status === (name === 'electrical' ? 'Failed' : 'Passed'));
  }
  fixedRepairEligible(run) {
    if (genericClosure(run?.runtime_configuration?.profile?.profile_version)) return this.genericRepairEligible(run);
    const checks = run?.checks;
    const version = run?.runtime_configuration?.profile?.profile_version;
    const sources = this.sources();
    const sourceRevisionMatches = run?.revision_id === this.project().envelope.revision.id ||
      (!!sources && run?.revision_id === sources.job.revision_id && run.global_job_id === sources.job.id
        && run.synthesis_run_id === sources.synthesis.id && run.netlist_run_id === sources.netlist.id);
    return !!run && run.id === this.data.latest_run_id && sourceRevisionMatches
      && run.freshness === 'Current' && run.execution_status === 'Completed' && run.validation_status === 'Failed'
      && run.review_status !== 'Accepted'
      && !run.error && run.evidence_kind === 'trusted_fixed_tool_execution' && run.software_qa_fixture !== true
      && REPAIR_TARGETS.has(version)
      && checks?.origin === 'trusted_fixed_tool_adapter' && checks.validation_status === 'Failed'
      && checks.executed === true && checks.exit_code === 0 && checks.cleanup_unresolved === false
      && checks.software_qa_fixture !== true && checks.technology_mapping_executed === false
      && checks.upstream_technology_mapping_reused === true
      && checks.implementation_kind === (version === FIXED_REPAIR_V1 ? 'resumed_pre_CTS_route_repair' : 'resumed_post_GRT_route_repair')
      && Array.isArray(checks.commands) && checks.commands.length === 2
      && checks.commands.every(command => command?.executed === true && command.status === 'Completed' && command.exit_code === 0 && command.cleanup_unresolved !== true)
      && (run.diagnostics || []).some(item => item.code === 'physical_checks_failed' && item.severity === 'error')
      && Object.keys(checks.checks || {}).length === REPAIR_CHECKS.length
      && REPAIR_CHECKS.every(name => checks.checks?.[name]?.validation_status === (name === 'electrical' ? 'Failed' : 'Passed'));
  }
  fixedRepairGate(run) {
    const p = this.project(), status = p.envelope.physical_repair_session || {};
    const version = run?.runtime_configuration?.profile?.profile_version;
    if (p.readOnly || p.envelope.workspace_identity?.read_only) return 'This preserved system is read-only.';
    if (status.configured && (status.profile_version === REPAIR_TARGETS.get(version) || status.profile_version === FIXED_REPAIR_V3)) return 'The next fixed correction is already prepared.';
    if (status.error) return status.error.message || 'Refresh the saved correction profile status.';
    if (p.conflict) return 'Open the newer saved design before preparing another correction.';
    if (p.dirty) return 'Save the complete design before preparing another physical correction.';
    if (p.busy || this.busy || this.anyActive()) return 'Wait for active project, model and tool work to finish.';
    if (this.pollError || this.uncertainStart) return 'Refresh saved runs and correction status before another request.';
    if (this.data.storage_error) return this.data.storage_error.message || 'Saved physical history is unavailable.';
    const runs = [this.data.runs, p.envelope.postlayout_workflow?.runs || [], p.envelope.drc_workflow?.runs || [], p.envelope.lvs_workflow?.runs || []].flat();
    if (runs.some(item => item.checks?.cleanup_unresolved === true && !item.cleanup_resolution)) return 'Verify unresolved process cleanup before preparing another correction.';
    if (!this.fixedRepairEligible(run)) return 'Select the latest current electrical-only failure from a supported fixed correction.';
    if (!status.configured || status.profile_version !== version) return 'Reload the source-bound correction profile before preparing another version.';
    return '';
  }
  renderFixedRepair() {
    const host = this.host?.querySelector('[data-testid="physical-workflow-repair-card"]'); if (!host) return;
    const run = this.selected(), status = this.project().envelope.physical_repair_session || {};
    if (status.configured === true && genericClosure(status.profile_version)
        && [GENERIC_REPAIR_SESSION_V1, 'hullcirq-gui-generic-physical-retry-session-v2'].includes(status.session_schema)) {
      host.hidden = false;
      host.replaceChildren(el('div', { class: 'card-heading' }, el('h2', { text: 'Prepared generic physical closure' })),
        el('p', { text: 'This source-bound generic closure profile was prepared explicitly. Preparation started no EDA and did not adopt a result. Use Run physical layout above to start a separate fresh technology mapping, placement, CTS, routing and closure run. Older physical mapping and checkpoints are not reused.' }),
        el('p', { text: 'Saved source RTL, independent finite-cycle expectations, clock/reset and SDC constraints are preserved. Mixed placement only; block-region fences are not silently removed. Completion requires a new S11 → S12 → S13 → S14 chain with its own checks and explicit review or previously authorized policy.' }),
        details('Prepared generic closure source', { session_schema: status.session_schema, profile_version: status.profile_version, implementation_kind: status.implementation_kind, technology_mapping_reused: status.technology_mapping_reused, repair_generation: status.repair_generation, core_utilization: status.core_utilization, source_identity: status.source_identity }),
        ...(this.genericRepairEligible(run) ? [
          el('p', { class: 'scope-note', text: 'This complete current attempt failed only electrical checks. Prepare another fresh correction with five percentage points less core utilization (minimum 10%). This changes a recorded placement assumption, not the clock, expected values or signoff limits. It does not guarantee closure and never retries automatically.' }),
          el('button', { type: 'button', text: 'Prepare next generic physical correction', 'data-testid': 'physical-workflow-prepare-repair', disabled: !!this.fixedRepairGate(run), title: this.fixedRepairGate(run) || 'Validate the complete failure and prepare another immutable fresh-mapping profile; start no EDA.', onclick: () => this.prepareFixedRepair(run) })
        ] : []));
      return;
    }
    const prepared = status.configured === true && [FIXED_REPAIR_V2, FIXED_REPAIR_V3].includes(status.profile_version)
      && !(status.profile_version === FIXED_REPAIR_V2 && this.fixedRepairEligible(run)
        && run.runtime_configuration.profile.profile_version === FIXED_REPAIR_V2);
    host.hidden = !prepared && !this.fixedRepairEligible(run);
    if (host.hidden) { host.replaceChildren(); return; }
    const title = el('div', { class: 'card-heading' }, el('h2', { text: 'Next fixed physical correction' }));
    if (prepared) {
      host.replaceChildren(title, el('p', { text: 'The next fixed correction profile was prepared by an explicit GUI action. Preparing this profile did not start EDA. Physical execution is a separate explicit action; inspect its current status and verify the new S11 → S12 → S13 → S14 chain. The original 50 ns clock, SDC constraints, workload and expected values are preserved; earlier failures remain saved.' }));
      return;
    }
    const gate = this.fixedRepairGate(run);
    host.replaceChildren(title,
      el('p', { text: 'Prepare the next fixed correction for this electrical-only failure. This starts no EDA and preserves the original 50 ns clock, SDC constraints, workload and expected values. Completion requires a new S11 → S12 → S13 → S14 chain. Run physical layout remains a separate explicit action.' }),
      el('button', { type: 'button', text: 'Prepare next fixed physical correction', 'data-testid': 'physical-workflow-prepare-repair',
        disabled: !!gate, title: gate || 'Validate the saved failed S11 and prepare the next fixed profile without starting tools.', onclick: () => this.prepareFixedRepair(run) }));
  }
  gate() {
    const p = this.project();
    if (!this.data.implemented || !p.envelope.workflow.find(stage => stage.id === 'layout')?.implemented) return 'Layout execution is not implemented by the connected service.';
    if (p.conflict) return 'A newer saved design was detected. Export your draft, then Open saved.';
    if (p.dirty) return 'Save the complete design before physical execution.';
    if (p.busy) return 'Wait for the current project operation to finish.';
    if (this.data.storage_error) return this.data.storage_error.message || 'Physical execution history is unavailable.';
    if (this.uncertainStart || this.pollError) return this.pollError || 'The start response was interrupted. Refresh saved runs before trying again; the request is not automatically resent.';
    if (this.anyActive()) return 'A model or tool run is active. Inspect its progress or cancel it before starting another.';
    if (!this.data.ready || !this.sources()) return this.data.blocked_reason || 'Current adopted S08, S09 and S10 evidence with the same source lineage is required.';
    if (!this.data.tool_ready) return this.data.tool_blocked_reason || 'The fixed LibreLane / PDK runtime is not ready.';
    return '';
  }
  revalidationGate(run) {
    const gate = this.gate(); if (gate) return gate;
    if (!run || run.id !== this.data.latest_run_id || run.freshness !== 'Current' || active(run) || !(run.execution_status === 'Failed' || run.validation_status === 'Failed')) return 'Select the latest failed physical result for the current sources.';
    if (run.evidence_kind !== 'trusted_fixed_tool_execution' || revalidated(run)) return 'Recheck the original recorded physical execution, rather than a previous revalidation.';
    if (run.checks?.cleanup_unresolved === true) return 'Process cleanup must be verified before saved outputs can be checked.';
    if (run.checks?.executed !== true || run.checks?.exit_code !== 0) return 'Saved-output rechecking requires a recorded physical execution that exited successfully.';
    return '';
  }
  render(host) {
    this.clearFunctionalMap();
    this.clearMapGeneration();
    this.blockPlacement?.clear();
    this.host = host;
    const physicalPanel = el('div', { id: 'physical-layout-panel', class: 'layout-view-panel', role: 'tabpanel', 'aria-labelledby': 'physical-layout-tab', 'data-testid': 'physical-layout-panel' },
      card('Frozen physical execution', 'Review the saved clock, reset and technology settings together with the separately recorded physical execution profile.',
        el('div', { class: 'provider-actions' }, el('button', { type: 'button', class: 'primary', text: 'Run physical layout', 'data-testid': 'physical-workflow-run', onclick: () => this.start() }), el('button', { type: 'button', text: 'Inspect S10 functional evidence', onclick: () => this.callbacks.navigate('global_netlist_simulation') }), el('button', { type: 'button', text: 'Refresh saved layout runs', 'data-testid': 'physical-workflow-refresh', onclick: () => this.refreshSaved() })),
        el('p', { class: 'generation-gate', 'data-testid': 'physical-workflow-gate' }), el('div', { class: 'workflow-lineage', 'data-testid': 'physical-workflow-lineage' }), el('div', { 'data-testid': 'physical-workflow-configuration' })),
      el('section', { class: 'card', 'data-testid': 'physical-workflow-repair-card' }),
      card('Physical execution evidence', 'Actual flow steps, warnings, logs, metrics and immutable artifacts remain tied to this run and its adopted sources.', el('div', { 'data-testid': 'physical-workflow-result' })),
      card('Recorded layout view', 'Preview the saved physical artifact. Zooming and downloads do not execute EDA tools.', el('div', { 'data-testid': 'physical-workflow-preview' })));
    const functionalPanel = el('div', { id: 'functional-map-panel', class: 'layout-view-panel', role: 'tabpanel', 'aria-labelledby': 'functional-map-tab', 'data-testid': 'functional-map-panel' },
      card('Functional Map', 'Inspect a saved, source-bound role overlay on the existing placed-cell footprints. This is a read-only view, not another placement method.',
        el('p', { class: 'scope-note', text: 'Some cell-to-function assignments are inferred. Inspect each cell’s status and evidence; inferred correspondence is not formal block ownership. The separate Block Floorplan tab edits physical region constraints; this map does not prove region containment. S14 verification is a separate stage and is not established by this view.' }),
        el('div', { 'data-testid': 'functional-map-generation' }),
        el('div', { 'data-testid': 'functional-map-content' })));
    const blockPanel = el('div', { id: 'block-floorplan-panel', class: 'layout-view-panel', role: 'tabpanel', 'aria-labelledby': 'block-floorplan-tab', 'data-testid': 'block-floorplan-panel' });
    const placementPanel = el('div', { id: 'block-placement-panel', class: 'layout-view-panel', role: 'tabpanel', 'aria-labelledby': 'block-placement-tab', 'data-testid': 'block-placement-panel' },
      card('Block Placement', 'Inspect original mapped-cell bounding boxes from this saved S11 region-containment proof, independently of its PNG preview. Viewing never starts EDA or changes adoption.', el('div', { 'data-testid': 'block-placement-content' })));
    this.callbacks.renderBlockFloorplan?.(blockPanel);
    const viewTabs = el('div', { class: 'layout-view-tabs', role: 'tablist', 'aria-label': 'Layout views' },
      ...[['physical', 'Physical Layout', 'physical-layout'], ['functional', 'Functional Map', 'functional-map'], ['blocks', 'Block Floorplan', 'block-floorplan'], ['placement', 'Block Placement', 'block-placement']].map(([view, label, id]) => el('button', {
        type: 'button', id: id + '-tab', role: 'tab', 'aria-controls': id + '-panel', 'data-testid': id + '-tab',
        text: label, onclick: () => this.setLayoutView(view), onkeydown: event => this.layoutViewKey(event, view)
      })));
    host.replaceChildren(
      el('div', { class: 'spec-intro' }, badge('S11 · Physical layout'), badge('Exact adopted sources'), el('p', { 'data-testid': 'physical-workflow-implementation', text: implementationScope(this.selected()) })),
      card('Selected physical run', 'Physical Layout, Functional Map and Block Placement refer to this selected S11 record. Block Floorplan edits the current design draft separately. Changing a view or selected record does not run tools or change adoption.', el('div', { 'data-testid': 'physical-workflow-selected-run' })),
      viewTabs, physicalPanel, functionalPanel, blockPanel, placementPanel,
      card('Saved layout attempts', 'Retries create new records. Old failures and stale layouts remain inspectable.', el('div', { class: 'generation-job-list', 'data-testid': 'physical-workflow-history' })));
    this.syncLayoutView();
    this.refresh(); this.schedule();
  }
  refresh() {
    if (!this.host?.isConnected || this.project().stage !== 'layout') return;
    const button = this.host.querySelector('[data-testid="physical-workflow-run"]'); if (!button) return;
    const gate = this.gate(), sources = this.sources();
    button.disabled = this.busy || !!gate; button.title = gate || 'Execute the exact fixed physical source and configuration.';
    this.host.querySelector('[data-testid="physical-workflow-refresh"]').disabled = this.busy || this.polling;
    this.host.querySelector('[data-testid="physical-workflow-gate"]').textContent = this.busy ? 'Contacting the local physical execution service…' : gate || 'Ready. Physical checks and adoption use the saved policy.';
    this.host.querySelector('[data-testid="physical-workflow-implementation"]').textContent = implementationScope(this.selected());
    this.host.querySelector('[data-testid="physical-workflow-lineage"]').replaceChildren(
      el('p', { text: `Saved revision ${this.project().envelope.revision.id}` }),
      el('p', { text: `Adopted S08 ${sources?.job.id || 'Not available'} · S09 ${sources?.synthesis.id || 'Not available'} · S10 ${sources?.netlist.id || 'Not available'}` }),
      el('p', { text: `Runtime configuration SHA-256 ${this.data.runtime_configuration_sha256 || 'Not configured'}` }));
    this.host.querySelector('[data-testid="physical-workflow-configuration"]').replaceChildren(...[
      el('p', { 'data-testid': 'physical-placement-mode', text: `Saved placement mode: ${this.data.placement_mode === 'block_regions' ? 'Block regions (same chip)' : 'Mixed placement'}` }),
      this.data.physical_design ? details('Saved block region constraints (not placement proof)', { placement_plan_sha256: this.data.placement_plan_sha256, physical_design: this.data.physical_design }) : null,
      details('Saved settings projected to physical constraints', this.data.settings_projection), el('p', { class: 'scope-note', text: 'Die sizing, utilization and process corners in the physical execution profile are recorded execution choices. They are not retroactively added to the original GUI job or its functional verification plan.' })].filter(Boolean));
    this.renderSelectedRun(); this.renderFixedRepair(); this.renderResult(); this.renderPreview(); this.renderHistory(); this.renderFunctionalMap(); this.renderMapGeneration();
    this.renderBlockPlacement();
    if (this.reviewHost?.isConnected) this.renderReview(this.reviewHost);
    this.callbacks.chrome?.();
  }
  refreshDraftActions() {
    // A coordinate keystroke changes only draft gates, not the saved evidence
    // DOM, map descriptors, network state or any project file.
    if (!this.host?.isConnected || this.project().stage !== 'layout') return;
    const button = this.host.querySelector('[data-testid="physical-workflow-run"]');
    if (!button) return;
    const gate = this.gate();
    button.disabled = this.busy || !!gate; button.title = gate || 'Execute the exact fixed physical source and configuration.';
    this.host.querySelector('[data-testid="physical-workflow-gate"]').textContent = this.busy ? 'Contacting the local physical execution service…' : gate || 'Ready. Physical checks and adoption use the saved policy.';
  }
  renderSelectedRun() {
    const host = this.host?.querySelector('[data-testid="physical-workflow-selected-run"]'); if (!host) return;
    const run = this.selected();
    const selector = el('select', { 'aria-label': 'Selected physical run', 'data-testid': 'physical-workflow-run-selector', disabled: !this.data.runs.length, onchange: event => this.selectRun(event.target.value) },
      ...(this.data.runs.length ? this.data.runs.toReversed().map(item => el('option', { value: item.id, text: `${item.id} · ${item.execution_status} / ${item.validation_status} / ${item.review_status} / ${item.freshness}` })) : [el('option', { value: '', text: 'No saved physical run' })]));
    selector.value = run?.id || '';
    host.replaceChildren(el('div', { class: 'layout-run-selector' }, selector),
      el('div', { class: 'generation-summary', 'data-testid': 'physical-workflow-selected-run-status' },
        ...(run ? [badge(run.execution_status), badge(run.validation_status, run.validation_status === 'Passed' ? 'teal' : 'orange'), badge(run.review_status), badge(run.freshness), el('code', { text: run.id })] : [badge('Not Run'), el('span', { text: 'Select a saved physical run when one exists.' })])));
  }
  selectRun(id) {
    if (!this.data.runs.some(run => run.id === id)) return;
    this.clearFunctionalMap(); this.clearMapGeneration(); this.blockPlacement?.clear(); this.runId = id; this.refresh();
  }
  syncLayoutView() {
    for (const [view, id] of [['physical', 'physical-layout'], ['functional', 'functional-map'], ['blocks', 'block-floorplan'], ['placement', 'block-placement']]) {
      const tab = this.host?.querySelector('#' + id + '-tab'), panel = this.host?.querySelector('#' + id + '-panel');
      if (!tab || !panel) continue;
      const selected = this.layoutView === view;
      tab.setAttribute('aria-selected', String(selected)); tab.tabIndex = selected ? 0 : -1;
      panel.hidden = !selected;
    }
  }
  setLayoutView(view, focus = false) {
    if (!['physical', 'functional', 'blocks', 'placement'].includes(view)) return;
    if (view !== this.layoutView) { this.clearFunctionalMap(); this.clearMapGeneration(); this.blockPlacement?.clear(); this.layoutView = view; }
    this.syncLayoutView();
    if (focus) this.host?.querySelector({ physical: '#physical-layout-tab', functional: '#functional-map-tab', blocks: '#block-floorplan-tab', placement: '#block-placement-tab' }[view])?.focus();
    if (view === 'functional') { this.renderFunctionalMap(); this.renderMapGeneration(); }
    if (view === 'placement') this.renderBlockPlacement(true);
  }
  layoutViewKey(event, view) {
    let next;
    const views = ['physical', 'functional', 'blocks', 'placement'];
    if (event.key === 'Home') next = 'physical';
    else if (event.key === 'End') next = 'placement';
    else if (['ArrowLeft', 'ArrowRight'].includes(event.key)) next = views[(views.indexOf(view) + (event.key === 'ArrowRight' ? 1 : views.length - 1)) % views.length];
    if (!next) return;
    event.preventDefault(); this.setLayoutView(next, true);
  }
  renderBlockPlacement(explicit = false) {
    if (this.layoutView !== 'placement' || !this.host?.isConnected || this.project().stage !== 'layout') return;
    const host = this.host.querySelector('[data-testid="block-placement-content"]'); if (!host) return;
    if (!this.blockPlacement) this.blockPlacement = new BlockPlacementView({
      project: () => this.project(), run: () => this.selected(), request: this.callbacks.blockPlacementRequest,
      active: () => this.layoutView === 'placement' && this.host?.isConnected && this.project().stage === 'layout',
    });
    if (explicit) this.blockPlacement.activate(host); else this.blockPlacement.mount(host);
  }
  clearFunctionalMap() {
    this.functionalMapToken++; this.functionalMapAbort?.abort(); this.functionalMapAbort = null; this.functionalMap = null;
    this.host?.querySelector('[data-testid="functional-map-content"]')?.replaceChildren();
  }
  clearMapGeneration() {
    this.mapGenerationToken++;
    if (this.mapGenerationTimer) clearTimeout(this.mapGenerationTimer);
    this.mapGenerationTimer = null; this.mapGeneration = null;
    this.host?.querySelector('[data-testid="functional-map-generation"]')?.replaceChildren();
  }
  mapGenerationKey(run) {
    const p = this.project();
    return JSON.stringify([p.envelope.workspace_identity, p.envelope.revision.id, run?.id, run?.revision_id, run?.record_hash,
      run?.execution_status, run?.validation_status, run?.review_status, run?.freshness]);
  }
  mapGenerationCurrent(state) {
    return state === this.mapGeneration && state.token === this.mapGenerationToken &&
      this.layoutView === 'functional' && this.host?.isConnected && this.project().stage === 'layout' &&
      this.project().design === state.design && this.mapGenerationKey(this.selected()) === state.key;
  }
  selectedMapPublication(run = this.selected()) {
    const selection = this.mapPublication;
    return selection && selection.design === this.project().design && selection.key === this.mapGenerationKey(run) ? selection.id : null;
  }
  selectMapPublication(id) {
    const state = this.mapGeneration, run = this.selected();
    if (!state || !this.mapGenerationCurrent(state)) return;
    if (id !== null && (typeof id !== 'string' || !/^functional-map-[0-9a-f]{32}$/.test(id) ||
        !(state.result?.jobs || []).some(job => job.id === id && job.status === 'Completed' && job.layout_run_id === run.id))) return;
    this.mapPublication = id === null ? null : { id, key: state.key, design: state.design };
    this.clearFunctionalMap(); this.renderFunctionalMap(); this.renderMapGeneration();
  }
  mapGenerationGate(run, state = this.mapGeneration) {
    const p = this.project();
    if (p.readOnly || p.envelope.workspace_identity?.read_only) return 'This preserved system is read-only. Existing maps remain viewable.';
    if (p.conflict) return 'Open the newer saved design before generating a map.';
    if (p.dirty) return 'Save the complete design before generating a map.';
    if (p.busy || this.busy || this.anyActive()) return 'Wait for active project, model and tool work to finish.';
    if (!run || typeof run.revision_id !== 'string' || !run.revision_id || run.execution_status !== 'Completed' ||
        run.validation_status !== 'Passed' || run.review_status !== 'Accepted' || run.freshness !== 'Current') return 'Select a current, passed and accepted S11 result for this saved revision.';
    if (run.id !== this.data.latest_run_id || run.id !== this.data.accepted_run_id) return 'Select the latest current adopted S11 result before generating a map.';
    if (!/^[0-9a-f]{64}$/i.test(run.record_hash || '')) return 'Refresh the saved S11 record before generating a map.';
    if (!state?.result) return 'Read generation availability before starting.';
    if (state.key !== this.mapGenerationKey(run)) return 'Refresh generation availability for the current selected source binding.';
    if (state.result.run_id !== run.id) return 'Refresh generation availability for the selected S11 result.';
    if (state.busy) return 'Reading saved generation status…';
    if (state.uncertain || state.error) return 'Refresh generation status without resending before another request.';
    if ((state.result.jobs || []).some(mapJobActive)) return 'Functional Map generation is already in progress. No EDA tools are running for this view.';
    if (state.result.can_generate !== true) return state.result.blocked_reason || 'The connected service cannot generate a map from this saved result.';
    return '';
  }
  renderMapGeneration() {
    const host = this.host?.querySelector('[data-testid="functional-map-generation"]');
    if (!host || this.layoutView !== 'functional' || !this.host?.isConnected || this.project().stage !== 'layout') return;
    const run = this.selected(), key = this.mapGenerationKey(run), design = this.project().design;
    if (!this.mapGeneration || this.mapGeneration.key !== key || this.mapGeneration.design !== design) {
      this.clearMapGeneration();
      if (!run) return;
      this.mapGeneration = { key, design, token: this.mapGenerationToken, runId: run.id, result: null, busy: false, error: null, uncertain: false, completed: null };
      this.readMapGeneration(this.mapGeneration);
    }
    const state = this.mapGeneration;
    if (!state) return;
    const result = state.result, latest = result?.latest_job, gate = this.mapGenerationGate(run, state);
    const hasMap = result?.registered === true || !!this.host.querySelector('[data-testid="functional-map-frame"]');
    const label = latest && ['Failed', 'Interrupted'].includes(latest.status) ? 'Retry Functional Map generation as a new attempt' :
      hasMap ? 'Generate new Functional Map (preserve current)' : 'Generate Functional Map';
    const completion = latest?.status === 'Completed' ?
      `Generated and registered${Number.isInteger(latest.registration?.final_cells) ? ' · ' + latest.registration.final_cells.toLocaleString('en-US') + ' cells' : ''}. Inspect the saved source binding below.` :
      latest ? (latest.message || `${latest.phase || latest.status} · Existing maps are preserved.`) : 'No saved generation attempt for this selected S11 result.';
    host.replaceChildren(
      el('h3', { text: 'Generate and register Functional Map' }),
      el('p', { class: 'scope-note', text: 'Explicitly derive a source-bound viewer from this saved S11 result. This does not run EDA or models, change placement, or change circuit-stage completion and adoption. Existing maps and earlier attempts are preserved.' }),
      el('div', { class: 'provider-actions' },
        el('button', { type: 'button', text: label, 'data-testid': 'functional-map-generate', disabled: !!gate, title: gate || 'Create one new derived-view attempt from this exact S11 record.', onclick: () => this.startMapGeneration() }),
        el('button', { type: 'button', text: 'Refresh generation status', 'data-testid': 'functional-map-generation-refresh', disabled: state.busy, onclick: () => this.readMapGeneration(state) })),
      el('p', { class: 'generation-gate', 'data-testid': 'functional-map-generation-gate', text: state.error || gate || 'Ready. Generation and registration are separate from circuit verification.' }),
      details('Source-bound Functional Map capability', { capability: result?.capability || null, can_generate: result?.can_generate ?? false, blocked_reason: result?.blocked_reason || null, run_id: result?.run_id || run?.id,
        scope: 'The backend validates this selected run and its saved sources. Role and instance controls come from that saved viewer, not a fixed project name, node count or four-PE template.' }, { 'data-testid': 'functional-map-generation-capability' }),
      el('div', { class: 'generation-summary', role: 'status', 'data-testid': 'functional-map-generation-status' },
        badge(latest?.status || (state.busy ? 'Loading' : 'Not run')), el('span', { text: completion })),
      ...(latest ? [el('div', { class: 'workflow-lineage', 'data-testid': 'functional-map-generation-attempt' },
        el('code', { text: latest.id }),
        el('p', { text: `Started: ${latest.started_at || latest.created_at} · Finished: ${latest.finished_at || 'Not finished'}` }))] : []),
      ...(latest?.error ? [el('p', { class: 'generation-error', 'data-testid': 'functional-map-generation-error', text: `${latest.error.code || 'Generation error'} · ${latest.error.message || 'Inspect the saved attempt.'}` })] : []),
      el('div', { class: 'saved-map-versions', 'data-testid': 'functional-map-versions' },
        el('h3', { text: 'Saved map versions' }),
        el('p', { class: 'scope-note', text: 'Open a completed version for this exact S11 result. Selecting a version only changes this view; the registered latest map and circuit adoption stay unchanged.' }),
        el('div', { class: 'provider-actions' },
          el('button', { type: 'button', text: 'View latest registered map', 'data-testid': 'functional-map-latest',
            'aria-pressed': String(!this.selectedMapPublication(run)), onclick: () => this.selectMapPublication(null) }),
          ...(result?.jobs || []).filter(job => job.status === 'Completed' && job.layout_run_id === run.id).toReversed().map(job => el('button', {
            type: 'button', text: `Open saved map · ${job.finished_at || job.created_at || 'Recorded time unavailable'} · ${job.id}`,
            'data-testid': 'functional-map-version', 'data-map-publication': job.id,
            'aria-pressed': String(this.selectedMapPublication(run) === job.id), onclick: () => this.selectMapPublication(job.id) })))),
      details('Saved Functional Map generation attempts (not EDA runs)', result?.jobs || [], { 'data-testid': 'functional-map-generation-history' }));
  }
  validateMapGeneration(state, result) {
    if (!result || !Array.isArray(result.jobs) || typeof result.can_generate !== 'boolean' ||
        result.run_id !== state.runId ||
        (result.latest_job != null && !result.jobs.some(job => job.id === result.latest_job.id))) throw new Error('Generation status does not match the selected S11 result.');
    const statuses = ['Queued', 'Running', 'Completed', 'Failed', 'Interrupted'];
    for (const job of [...result.jobs, ...(result.latest_job ? [result.latest_job] : [])]) {
      if (!job || typeof job.id !== 'string' || !statuses.includes(job.status) ||
          job.layout_run_id !== state.runId ||
          (job.run_id !== undefined && job.run_id !== state.runId)) throw new Error('A saved generation attempt does not match the selected S11 result.');
    }
  }
  applyMapGeneration(state, result) {
    this.validateMapGeneration(state, result);
    state.result = result; state.error = null; state.uncertain = false;
    const completed = result.latest_job?.status === 'Completed' ? result.latest_job.id : null;
    if (completed && state.completed !== completed) {
      state.completed = completed;
      this.clearFunctionalMap(); this.renderFunctionalMap();
    }
  }
  async readMapGeneration(state = this.mapGeneration) {
    if (!state || state.busy || !this.mapGenerationCurrent(state)) return;
    if (this.mapGenerationTimer) clearTimeout(this.mapGenerationTimer);
    this.mapGenerationTimer = null; state.busy = true; this.renderMapGeneration();
    try {
      const result = await this.callbacks.request(`physical-workflow/runs/${encodeURIComponent(state.runId)}/functional-map-generation`);
      if (!this.mapGenerationCurrent(state)) return;
      this.applyMapGeneration(state, result);
    } catch (error) {
      if (!this.mapGenerationCurrent(state)) return;
      state.error = `${error.message || 'Generation status could not be read.'} Refresh generation status; no request is automatically resent.`;
    } finally {
      state.busy = false;
      if (this.mapGenerationCurrent(state)) { this.renderMapGeneration(); this.scheduleMapGeneration(state); }
    }
  }
  scheduleMapGeneration(state) {
    if (!this.mapGenerationCurrent(state) || state.error || state.busy || this.mapGenerationTimer || !(state.result?.jobs || []).some(mapJobActive)) return;
    this.mapGenerationTimer = setTimeout(() => {
      this.mapGenerationTimer = null;
      if (this.mapGenerationCurrent(state)) this.readMapGeneration(state);
    }, 2000);
  }
  async startMapGeneration() {
    const state = this.mapGeneration, run = this.selected();
    if (!state || !this.mapGenerationCurrent(state) || this.mapGenerationGate(run, state)) return;
    this.mapPublication = null;
    state.busy = true; this.renderMapGeneration();
    try {
      const result = await this.callbacks.request(`physical-workflow/runs/${encodeURIComponent(run.id)}/functional-map-generation`,
        { revision_id: run.revision_id, record_hash: run.record_hash });
      if (!this.mapGenerationCurrent(state)) return;
      this.applyMapGeneration(state, result);
      this.callbacks.toast?.('Functional Map generation requested. This derives a saved viewer only; it does not start EDA or change circuit adoption.');
    } catch (error) {
      if (!this.mapGenerationCurrent(state)) return;
      state.uncertain = true;
      state.error = `${error.message || 'The generation response was interrupted.'} The start outcome may be unknown. Refresh generation status without resending.`;
      this.callbacks.notify?.(state.error, 'error');
    } finally {
      state.busy = false;
      if (this.mapGenerationCurrent(state)) { this.renderMapGeneration(); this.scheduleMapGeneration(state); }
    }
  }
  functionalMapKey(run) {
    const project = this.project();
    return JSON.stringify([project.envelope.revision.id, this.data.latest_run_id, this.data.accepted_run_id, this.data.runtime_configuration_sha256,
      this.data.runs.map(item => [item.id, item.review_status, item.freshness, item.source_key, item.source_epoch_at_start, item.acceptance_epoch, item.record_hash]),
      this.data.reviews.map(item => [item.run_id, item.decision, item.acceptance_epoch, item.created_at]),
      run?.id, run?.revision_id, run?.source_manifest_sha256, run?.source_key, run?.source_epoch_at_start, run?.acceptance_epoch, run?.record_hash,
      run?.execution_status, run?.validation_status, run?.review_status, run?.freshness, this.selectedMapPublication(run),
      (run?.artifacts || run?.checks?.artifacts || []).filter(item => ['gds', 'def', 'netlist'].includes(item.id)).map(item => [item.id, item.sha256])]);
  }
  renderFunctionalMap() {
    if (this.layoutView !== 'functional' || !this.host?.isConnected || this.project().stage !== 'layout') return;
    const run = this.selected(), key = this.functionalMapKey(run), projectDesign = this.project().design;
    if (this.functionalMap && this.functionalMap.key === key && this.functionalMap.projectDesign === projectDesign) return;
    this.clearFunctionalMap();
    if (!run) { this.renderFunctionalMapMessage('Not available', 'No saved physical run is selected. A functional map is never borrowed from another project or run.'); return; }
    const token = this.functionalMapToken;
    this.functionalMap = { key, projectDesign, runId: run.id, token };
    this.renderFunctionalMapMessage('Loading', 'Checking the saved functional map and its binding to the selected physical run…');
    this.loadFunctionalMap(run, key, projectDesign, token);
  }
  functionalMapCurrent(run, key, projectDesign, token) {
    return this.layoutView === 'functional' && this.host?.isConnected && this.project().stage === 'layout' &&
      this.functionalMapToken === token && this.project().design === projectDesign && this.selected()?.id === run.id && this.functionalMapKey(this.selected()) === key;
  }
  renderFunctionalMapMessage(status, message, metadata = null, retry = false) {
    const host = this.host?.querySelector('[data-testid="functional-map-content"]'); if (!host) return;
    host.replaceChildren(...[
      el('div', { class: 'generation-summary', 'data-testid': 'functional-map-status', role: 'status' }, badge(status), el('span', { text: message })),
      metadata?.source_binding ? details('Exact saved functional-map source binding', metadata.source_binding, { 'data-testid': 'functional-map-binding' }) : null,
      metadata?.status ? details('Recorded physical status at the read-only lookup', { ...metadata.status, status_scope: metadata.status_scope, historical: metadata.historical }) : null,
      retry ? el('div', { class: 'provider-actions' }, el('button', { type: 'button', text: 'Retry read-only view', 'data-testid': 'functional-map-retry', onclick: () => { this.clearFunctionalMap(); this.renderFunctionalMap(); } })) : null
    ].filter(Boolean));
  }
  validateFunctionalMap(run, metadata) {
    if (!metadata || metadata.run_id !== run.id || typeof metadata.available !== 'boolean') throw new Error('The functional-map response does not belong to the selected physical run.');
    if (!metadata.available) return;
    const source = metadata.source_binding, artifacts = run.artifacts || run.checks?.artifacts || [], hash = value => typeof value === 'string' && /^[0-9a-f]{64}$/i.test(value);
    if (!source || source.layout_run_id !== run.id || source.revision_id !== run.revision_id || source.source_manifest_sha256 !== run.source_manifest_sha256 ||
        !hash(source.source_manifest_sha256) || !hash(source.archive_manifest_sha256) || !hash(source.view_manifest_sha256)) throw new Error('The saved map source binding does not match the selected physical run.');
    for (const id of ['gds', 'def', 'netlist']) {
      const artifact = artifacts.find(item => item.id === id);
      if (!artifact || !hash(source[id + '_sha256']) || artifact.sha256 !== source[id + '_sha256']) throw new Error(`The saved map ${id.toUpperCase()} hash does not match the selected physical run.`);
    }
    const route = `/api/artifacts/physical-workflow/${encodeURIComponent(run.id)}/functional-map-`;
    const publication = source.registration_job_id;
    if (publication !== undefined && (typeof publication !== 'string' || !/^functional-map-[0-9a-f]{32}$/.test(publication))) throw new Error('The functional map publication identity is invalid.');
    const suffix = publication === undefined ? '' : `?map_generation=${publication}`;
    if (metadata.html_url !== route + 'html' + suffix || (metadata.png_url && metadata.png_url !== route + 'png' + suffix) || (metadata.report_url && metadata.report_url !== route + 'report' + suffix)) throw new Error('The functional map is outside the fixed read-only artifact routes or publication.');
  }
  async loadFunctionalMap(run, key, projectDesign, token) {
    const current = () => this.functionalMapCurrent(run, key, projectDesign, token);
    try {
      const publication = this.selectedMapPublication(run);
      const metadata = await this.callbacks.request(`physical-workflow/runs/${encodeURIComponent(run.id)}/functional-map` +
        (publication ? `?map_generation=${encodeURIComponent(publication)}` : ''));
      if (!current()) return;
      this.validateFunctionalMap(run, metadata);
      if (metadata.available && publication && metadata.source_binding.registration_job_id !== publication) throw new Error('The saved map response does not match the selected version.');
      if (!metadata.available) {
        this.renderFunctionalMapMessage('Not available', metadata.reason?.message || 'No saved functional map is bound to this physical run. No fallback view is shown.', metadata, true); return;
      }
      this.renderFunctionalMapMessage('Loading', 'Source binding matched. Reading the saved, self-contained viewer…', metadata);
      const controller = new AbortController(); this.functionalMapAbort = controller;
      const response = await sessionFetch(metadata.html_url, { cache: 'no-store', credentials: 'same-origin', signal: controller.signal });
      if (!current()) return;
      if (!response.ok) throw new Error(`The saved functional-map HTML could not be read (${response.status}). No other view was substituted.`);
      if (!response.headers.get('content-type')?.startsWith('text/html')) throw new Error('The functional-map artifact did not return HTML.');
      const html = await response.text();
      if (!current()) return;
      if (!html.trim()) throw new Error('The saved functional-map HTML is empty.');
      this.functionalMapAbort = null;
      this.renderFunctionalMapMessage('Available · read-only', metadata.historical ? 'Historical map bound to this selected run. Its availability does not establish currentness or adoption; inspect the selected physical status above.' : 'Saved map bound to this selected physical run. Viewing it does not run tools, change placement or adopt a result.', metadata);
      // A real artifact navigation uses its narrowly scoped CSP. srcdoc would
      // inherit the parent GUI policy and block this saved viewer's inline JS.
      const frame = el('iframe', { class: 'functional-map-frame', title: `Saved functional map for ${run.id}`, sandbox: 'allow-scripts', referrerPolicy: 'no-referrer', src: metadata.html_url, 'data-testid': 'functional-map-frame',
        onerror: () => { if (current()) this.renderFunctionalMapMessage('Failed', 'The saved functional-map frame could not load. No fallback view is shown.', metadata, true); } });
      this.host.querySelector('[data-testid="functional-map-content"]').append(frame);
    } catch (error) {
      if (!current()) return;
      this.functionalMapAbort = null;
      this.renderFunctionalMapMessage('Failed', error.message || 'The saved functional map could not be read. No fallback view is shown.', null, true);
    }
  }
  artifactURL(run, id) { return `/api/artifacts/physical-workflow/${encodeURIComponent(run.id)}/${id}`; }
  artifacts(run) { const files = filesFor(run); return (run.artifacts || []).filter(item => files.has(item.id) && item.url === this.artifactURL(run, item.id)); }
  renderResult() {
    const host = this.host?.querySelector('[data-testid="physical-workflow-result"]'); if (!host) return;
    const run = this.selected();
    if (!run) { host.replaceChildren(...[el('p', { class: 'empty-small', text: 'No physical execution evidence exists. No layout, timing or signoff result is inferred.' }), this.reconnect()].filter(Boolean)); return; }
    const checks = run.checks || {};
    const lineage = Object.fromEntries(['revision_id', 'global_job_id', 'synthesis_run_id', 'netlist_run_id', 'global_context_id', 'global_rtl_sha256', 'source_manifest_sha256', 'verification_plan_sha256', 'vector_hash', 'testbench_sha256', 'public_boundary_vector_hash', 'settings_sha256', 'runtime_configuration_sha256', 'source_identity', 'source_key', 'source_epoch_at_start', 'acceptance_epoch'].filter(key => Object.hasOwn(run, key)).map(key => [key, run[key]]));
    host.replaceChildren(...[
      el('div', { class: 'generation-summary', 'data-testid': 'physical-workflow-status' }, badge(run.execution_status), badge(run.validation_status, run.validation_status === 'Passed' ? 'teal' : 'orange'), badge(run.review_status), badge(run.freshness), el('code', { text: run.id })),
      run.error ? el('div', { class: 'generation-error', text: `${run.error.code || 'Execution error'} · ${run.error.message || JSON.stringify(run.error)}` }) : null,
      active(run) ? el('div', { class: 'generation-progress' }, el('span', { class: 'generation-spinner', 'aria-hidden': true }), el('span', { text: revalidated(run) ? 'Checking saved physical outputs; EDA tools are not rerun' : 'Actual physical flow in progress' }), el('button', { type: 'button', text: revalidated(run) ? 'Cancel output recheck' : 'Cancel layout run', 'data-testid': 'physical-workflow-cancel', disabled: this.busy, onclick: () => this.cancel(run) })) : null,
      !active(run) && (run.execution_status === 'Failed' || run.validation_status === 'Failed') ? el('div', { class: 'provider-actions' }, el('button', { type: 'button', text: 'Recheck saved outputs (no EDA rerun)', 'data-testid': 'physical-workflow-revalidate', disabled: this.busy || !!this.revalidationGate(run), title: this.revalidationGate(run) || 'Create a new validation record from the exact retained outputs; preserve the failed attempt.', onclick: () => this.revalidate(run) }), el('p', { class: 'scope-note', text: 'This checks the retained files and original completed command evidence. It creates a separate record and keeps the original failure; no EDA or model execution is requested.' })) : null,
      revalidated(run) ? details('Saved-output revalidation provenance (no EDA rerun)', Object.fromEntries(['evidence_kind', 'execution_kind', 'prior_run_id', 'previous_result_sha256', 'prior_record_sha256'].map(key => [key, run[key]]).concat(['execution_reused', 'revalidated_from_run_id', 'previous_result_sha256', 'revalidation_tool_starts', 'revalidation_model_calls'].map(key => [key, checks[key]]))), { open: true, 'data-testid': 'physical-workflow-revalidation-provenance' }) : null,
      el('p', { class: 'scope-note', 'data-testid': 'physical-workflow-scope', text: `${implementationScope(run)} Routing-rule counts, extracted parasitics and static timing are reported within their actual scope. S12 DRC, S13 LVS and S14 post-layout verification are separate and have no inferred pass.` }),
      ...(run.diagnostics || []).map(item => el('div', { class: `diagnostic ${item.severity || 'info'}` }, badge(item.severity || 'info'), el('code', { text: item.code || '' }), el('span', { text: item.message || JSON.stringify(item) }))),
      details('Actual physical checks', checks.checks || {}, { open: true, 'data-testid': 'physical-workflow-checks' }),
      details('Actual physical metrics', checks.metrics || {}, { 'data-testid': 'physical-workflow-metrics' }),
      details('All steps, complete commands, logs, warnings and output record', checks, { 'data-testid': 'physical-workflow-logs' }),
      details('Frozen source, settings, runtime and verification lineage', lineage, { 'data-testid': 'physical-workflow-frozen-input' }),
      details('Recorded physical settings', run.settings), details('Recorded runtime configuration', run.runtime_configuration),
      el('p', { class: 'scope-note', text: 'JSON previews use browser number precision. JSON downloads save the exact backend response text; output files are downloaded only through fixed artifact IDs.' }),
      el('div', { class: 'generation-artifact-actions' }, el('button', { type: 'button', text: 'Download physical run JSON', 'data-testid': 'physical-workflow-download-run', onclick: () => downloadJsonResponse(`/api/physical-workflow/runs/${encodeURIComponent(run.id)}`, `${safe(run.id)}.json`, this.callbacks.notify) }),
        JSON_FIELDS.map(id => el('button', { type: 'button', text: 'Download ' + id, 'data-testid': 'physical-workflow-download-' + id, onclick: () => downloadJsonResponse(this.artifactURL(run, id), `${safe(run.id)}-${id}.json`, this.callbacks.notify) })),
        this.artifacts(run).map(item => el('button', { type: 'button', text: `Download ${item.id.toUpperCase()} · ${item.bytes} bytes`, 'data-testid': 'physical-workflow-download-' + item.id, onclick: () => this.downloadFile(run, item) }))),
      this.reconnect(),
    ].filter(Boolean));
  }
  renderPreview() {
    const host = this.host?.querySelector('[data-testid="physical-workflow-preview"]'); if (!host) return;
    const run = this.selected(), png = run && this.artifacts(run).find(item => item.id === 'png');
    if (!png) { host.replaceChildren(el('p', { class: 'empty-small', text: 'No saved physical PNG preview is available for this run.' })); return; }
    const zoom = this.zooms.get(run.id) || 100, image = el('img', { src: this.artifactURL(run, 'png'), alt: `Recorded physical layout for ${run.id}`, 'data-testid': 'physical-workflow-layout-image', style: `width:${zoom}%;max-width:none;display:block;`, onerror: () => this.callbacks.notify('The recorded layout preview could not be loaded. Inspect the saved run and artifact manifest.', 'error') });
    const label = el('output', { text: `${zoom}%` });
    const slider = el('input', { type: 'range', min: 25, max: 400, step: 25, value: zoom, 'aria-label': 'Layout preview zoom', 'data-testid': 'physical-workflow-zoom', oninput: event => { const value = Number(event.target.value); this.zooms.set(run.id, value); image.style.width = `${value}%`; label.textContent = `${value}%`; } });
    host.replaceChildren(el('p', { text: `Artifact ${png.id} · ${png.bytes} bytes · SHA-256 ${png.sha256}` }), el('div', { class: 'provider-actions' }, el('label', { text: 'Zoom' }), slider, label, el('button', { type: 'button', text: 'Fit width', 'data-testid': 'physical-workflow-fit', onclick: () => { slider.value = 100; slider.dispatchEvent(new Event('input')); } })), el('div', { style: 'overflow:auto;max-height:520px;border:1px solid #c7d7e2;border-radius:8px;background:#fff;', 'data-testid': 'physical-workflow-layout-viewport' }, image));
  }
  async downloadFile(run, item) {
    try {
      if (!filesFor(run).has(item.id) || item.url !== this.artifactURL(run, item.id)) throw new Error('This artifact URL is outside the saved physical artifact routes.');
      let bytes;
      if (RAW_FILES.has(item.id)) {
        const response = await sessionFetch(this.artifactURL(run, item.id), { cache: 'no-store', credentials: 'same-origin' });
        if (!response.ok) throw new Error(`Artifact download failed (${response.status}).`);
        bytes = new Uint8Array(await response.arrayBuffer());
      } else {
        const source = await this.callbacks.request(`artifacts/physical-workflow/${encodeURIComponent(run.id)}/${item.id}`);
        if (typeof source !== 'string') throw new Error('The saved physical text artifact did not return text.');
        bytes = new TextEncoder().encode(source);
      }
      const digest = Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', bytes))).map(value => value.toString(16).padStart(2, '0')).join('');
      if (digest !== item.sha256 || bytes.length !== item.bytes) throw new Error('Artifact bytes do not match the saved hash and size. The download was stopped.');
      const url = URL.createObjectURL(new Blob([bytes], { type: item.content_type || 'application/octet-stream' }));
      const extension = EXTENSIONS[item.id] || (item.id.startsWith('rtl-') ? 'v' : 'json');
      const link = el('a', { href: url, download: `${safe(run.id)}-${item.id}.${extension}` }); document.body.append(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (error) { this.callbacks.notify(error.message, 'error'); }
  }
  renderHistory() {
    const host = this.host?.querySelector('[data-testid="physical-workflow-history"]'); if (!host) return;
    host.replaceChildren(...(this.data.runs.length ? this.data.runs.toReversed().map(run => el('button', { type: 'button', class: `generation-job-button${run.id === this.selected()?.id ? ' selected' : ''}`, 'data-testid': 'physical-workflow-run-' + run.id, onclick: () => this.selectRun(run.id) }, badge(run.execution_status), badge(run.validation_status), badge(run.review_status), badge(run.freshness), el('code', { text: run.id }), el('small', { text: `S10 ${run.netlist_run_id} · ${run.created_at || ''}` }))) : [el('p', { class: 'empty-small', text: 'No recorded layout attempts.' })]));
  }
  renderReview(host) {
    if (!host) return; this.reviewHost = host;
    const run = this.selected(); if (!run) { host.replaceChildren(el('p', { text: 'Run the fixed physical flow to inspect actual evidence and its adoption decision.' })); return; }
    const p = this.project(), reviewable = run.id === this.data.latest_run_id && !active(run) && !p.dirty && !p.conflict && !p.busy && !this.busy && !this.anyActive(), current = run.freshness === 'Current';
    const reviews = this.data.reviews.filter(item => item.run_id === run.id), decision = reviews.findLast(item => item.decision === 'accepted');
    const old = host.querySelector('[data-testid="physical-workflow-feedback"]'), focused = old === document.activeElement, selection = focused ? [old.selectionStart, old.selectionEnd] : null;
    const note = el('textarea', { rows: 3, value: this.notes.get(run.id) || '', 'aria-label': 'Physical run feedback', 'data-testid': 'physical-workflow-feedback', placeholder: 'Record the observed issue or requested correction.', oninput: event => this.notes.set(run.id, event.target.value) });
    const target = this.targets.get(run.id) || 'global_netlist_simulation';
    host.replaceChildren(el('div', { class: 'generation-review-status' }, badge(run.review_status), badge(run.freshness), el('code', { text: run.id })), el('p', { class: 'scope-note', 'data-testid': 'physical-workflow-adoption-provenance', text: decision?.actor === 'automation_policy' ? `Recorded adoption by authorized policy ${decision.provenance?.policy_id || decision.policy_id || ''}; this is not a manual human click. Inspect currentness and the exact record below.` : run.review_status === 'Accepted' && decision ? 'Accepted by explicit review. Its actor and provenance are recorded below.' : 'Only required physical checks for current sources can permit S11 adoption. This decision does not adopt DRC, LVS or post-layout verification.' }),
      el('div', { class: 'field' }, el('label', { text: 'Review and debug feedback' }), note), field('Return destination', target, value => this.targets.set(run.id, value), { choices: RETURNS, 'data-testid': 'physical-workflow-return-target' }),
      el('div', { class: 'review-actions' }, el('button', { type: 'button', class: 'primary', text: run.review_status === 'Accepted' ? 'Layout accepted' : 'Accept verified layout run', 'data-testid': 'physical-workflow-accept', disabled: !reviewable || !current || run.validation_status !== 'Passed' || run.review_status === 'Accepted', onclick: () => this.review(run, 'accepted', note.value) }), el('button', { type: 'button', text: 'Request Changes', 'data-testid': 'physical-workflow-request-changes', disabled: !reviewable, onclick: () => this.review(run, 'changes_requested', note.value) }), el('button', { type: 'button', text: 'Return to selected stage', 'data-testid': 'physical-workflow-return', disabled: !reviewable, onclick: () => this.review(run, 'return_to_stage', note.value, this.targets.get(run.id) || target) }), el('button', { type: 'button', text: p.envelope.workflow.find(stage => stage.id === 'drc')?.implemented ? 'Continue to DRC' : 'S12 DRC · not implemented', 'data-testid': 'physical-workflow-continue', disabled: !p.envelope.workflow.find(stage => stage.id === 'drc')?.implemented || !reviewable || !current || run.review_status !== 'Accepted', onclick: () => this.callbacks.navigate('drc') })), details('Exact physical adoption and feedback records', reviews));
    if (focused) { note.focus({ preventScroll: true }); note.setSelectionRange(...selection); }
  }
  reconnect() { return this.pollError || this.uncertainStart ? el('div', { class: 'generation-error' }, el('p', { text: this.pollError || 'The start outcome is unknown. Refresh saved history without resending the request.' }), el('button', { type: 'button', text: 'Reconnect without resending', 'data-testid': 'physical-workflow-reconnect', disabled: this.busy || this.polling, onclick: () => this.refreshSaved() })) : null; }
  async start() {
    if (this.busy || this.gate()) return; const p = this.project(), sources = this.sources(); this.busy = true; this.refresh();
    try { const response = await this.callbacks.request('physical-workflow/runs', { stage: 'layout', revision_id: p.envelope.revision.id, global_job_id: sources.job.id, synthesis_run_id: sources.synthesis.id, netlist_run_id: sources.netlist.id }); this.runId = response.physical_workflow?.latest_run_id; this.pollError = null; this.uncertainStart = false; this.callbacks.envelope(response); this.callbacks.toast('Physical execution started from the exact adopted sources and recorded configuration.'); }
    catch (error) { this.uncertainStart = true; this.pollError = `${error.message} Refresh saved runs; no request is automatically resent.`; this.callbacks.notify(this.pollError, 'error'); }
    finally { this.busy = false; this.refresh(); this.schedule(); }
  }
  async revalidate(run) {
    if (this.busy || this.revalidationGate(run)) return; this.busy = true; this.refresh();
    try { const response = await this.callbacks.request(`physical-workflow/runs/${encodeURIComponent(run.id)}/revalidate`, {}); this.runId = response.physical_workflow?.latest_run_id; this.pollError = null; this.uncertainStart = false; this.callbacks.envelope(response); this.callbacks.toast('Saved-output recheck recorded separately. The original physical attempt is preserved; EDA tools are not rerun.'); }
    catch (error) { this.uncertainStart = true; this.pollError = `${error.message} Refresh saved runs; the recheck request is not automatically resent.`; this.callbacks.notify(this.pollError, 'error'); }
    finally { this.busy = false; this.refresh(); this.schedule(); }
  }
  async prepareFixedRepair(run) {
    if (this.fixedRepairGate(run)) return;
    const revision = this.project().envelope.revision.id;
    this.busy = true; this.refresh();
    try {
      const response = await this.callbacks.request('physical-workflow/repair-profile', { failed_layout_id: run.id, revision_id: revision });
      this.clearFunctionalMap(); this.callbacks.envelope(response);
      this.callbacks.toast('Prepared the next fixed physical correction through the GUI. No EDA was started. Run physical layout explicitly, then verify the new S11, S12, S13 and S14 chain.');
    } catch (error) {
      this.pollError = `${error.message} Refresh saved correction status without resending the preparation request.`;
      this.callbacks.notify(this.pollError, 'error');
    } finally { this.busy = false; this.refresh(); }
  }
  async cancel(run) { if (this.busy) return; this.busy = true; this.refresh(); try { this.callbacks.envelope(await this.callbacks.request(`physical-workflow/runs/${encodeURIComponent(run.id)}/cancel`, {})); } catch (error) { this.callbacks.notify(`${error.message} Refresh saved history to inspect the cancellation outcome.`, 'error'); } finally { this.busy = false; this.refresh(); this.schedule(); } }
  async review(run, decision, note, target) {
    if (this.busy) return; if (decision !== 'accepted' && !note.trim()) { this.callbacks.toast('Record the issue or return reason first.'); return; } this.busy = true; this.refresh();
    try { this.callbacks.envelope(await this.callbacks.request(`physical-workflow/runs/${encodeURIComponent(run.id)}/review`, { decision, note: note.trim(), ...(target ? { target_stage: target } : {}) })); if (target) this.callbacks.navigate(target); }
    catch (error) { this.callbacks.notify(error.message, 'error'); } finally { this.busy = false; this.refresh(); }
  }
  async refreshSaved() { if (this.busy || this.polling) return; this.polling = true; this.refresh(); try { this.callbacks.envelope(await this.callbacks.request('project')); this.pollError = null; this.uncertainStart = false; } catch (error) { this.pollError = `${error.message} The tool request is not resent.`; this.callbacks.notify(this.pollError, 'error'); } finally { this.polling = false; this.refresh(); this.schedule(); } }
  schedule() { if (this.pollTimer || this.polling || this.pollError || (!this.data.runs.some(active) && !this.pendingPolicy())) return; this.pollTimer = setTimeout(() => { this.pollTimer = null; this.poll(); }, 2000); }
  async poll() { if (this.polling) return; this.polling = true; this.refresh(); try { const response = await this.callbacks.request('physical-workflow'); this.callbacks.workflow(response.physical_workflow); this.pollError = null; this.pollCount = (this.pollCount || 0) + 1; if (!this.data.runs.some(active) || this.pollCount % 3 === 0) this.callbacks.envelope(await this.callbacks.request('project')); } catch (error) { this.pollError = `${error.message} Reconnecting reads saved progress without resending execution.`; } finally { this.polling = false; this.refresh(); this.schedule(); } }
}
