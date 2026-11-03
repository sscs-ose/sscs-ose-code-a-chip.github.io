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
  const prefix = attrs['data-testid'] || 'drc-inspector-' + safe(title);
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
const JSON_FIELDS = ['layout-record', 'source-identity', 'runtime-configuration', 'artifact-manifest'];
const FILES = new Set(['input-gds', 'config', 'initial-state', 'final-state', 'metrics', 'tool-versions', 'drc-summary', 'klayout-violations', 'magic-report', 'magic-markers', 'klayout-report']);
const EXTENSIONS = { 'input-gds': 'gds', 'magic-report': 'rpt', 'magic-markers': 'xml', 'klayout-report': 'lyrdb' };
const RETURNS = [['global_settings', 'Global Settings'], ['graph_editor', 'Graph Editor'], ['specifications', 'Specifications'], ['local_rtl_generation', 'Local RTL Generation'], ['local_synthesis', 'Local Synthesis'], ['local_netlist_simulation', 'Local Netlist Simulation'], ['node_implementation_specs', 'Node Implementation Specs'], ['global_rtl_generation', 'Global RTL Generation'], ['global_synthesis', 'Global Synthesis'], ['global_netlist_simulation', 'Global Netlist Simulation'], ['layout', 'Layout']];

/** S12 inspects the adopted S11 GDS; it never rewrites inputs or invokes a model. */
export class DRCWorkflow {
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
  source() {
    const e = this.project().envelope, upstream = e.physical_workflow;
    const run = upstream?.runs?.find(item => item.id === upstream.accepted_run_id);
    if (!current(run) || typeof run.revision_id !== 'string' || !run.revision_id || (upstream.latest_run_id && upstream.latest_run_id !== run.id)) return null;
    // The backend pins these source IDs after its live snapshot/proof guards.
    // A presentation-only saved revision need not be the evidence's revision.
    const linked = Object.hasOwn(this.data, 'layout_run_id')
      ? typeof this.data.layout_run_id === 'string' && this.data.layout_run_id === run.id
      : run.revision_id === e.revision.id; // Older same-revision service only.
    return linked ? run : null;
  }
  receive(envelope) { if (envelope.drc_workflow) this.data = envelope.drc_workflow; this.refresh(); this.schedule(); }
  pendingPolicy() {
    const policy = this.project().envelope.review_policy, run = this.data.runs.find(item => item.id === this.data.latest_run_id);
    return policy?.mode === 'accept_on_pass' && policy.user_authorized === true && !this.data.storage_error && run?.execution_status === 'Completed' && run.validation_status === 'Passed' && run.review_status === 'Awaiting Review' && run.freshness === 'Current' && !run.error && !(run.diagnostics || []).some(item => item.code === 'automatic_adoption_blocked');
  }
  anyActive() { const e = this.project().envelope; return [this.data.runs, e.postlayout_workflow?.runs || [], e.lvs_workflow?.runs || [], e.physical_workflow?.runs || [], e.global_workflow?.runs || [], e.workflow_runs || [], e.global_generation?.jobs || [], e.generation?.jobs || []].some(runs => runs.some(active)); }
  gate() {
    const p = this.project();
    if (!this.data.implemented || !p.envelope.workflow.find(stage => stage.id === 'drc')?.implemented) return 'DRC execution is not implemented by the connected service.';
    if (p.conflict) return 'A newer saved design was detected. Export your draft, then Open saved.';
    if (p.dirty) return 'Save the complete design before DRC execution.';
    if (p.busy) return 'Wait for the current project operation to finish.';
    if (this.data.storage_error) return this.data.storage_error.message || 'DRC execution history is unavailable.';
    if (this.uncertainStart || this.pollError) return this.pollError || 'The start outcome is unknown. Refresh saved runs; this request is not automatically resent.';
    if (this.anyActive()) return 'A model or tool run is active. Inspect or cancel it before starting another.';
    if (!this.data.ready || !this.source()) return this.data.blocked_reason || 'Current adopted S11 evidence for this exact saved revision is required.';
    if (!this.data.tool_ready) return this.data.tool_blocked_reason || 'The fixed DRC runtime and PDK are not ready.';
    return '';
  }
  render(host) {
    this.host = host;
    host.replaceChildren(
      el('div', { class: 'spec-intro' }, badge('S12 · Design rule checking'), badge('Exact adopted GDS'), el('p', { text: 'Run the recorded PDK checks on the GDS produced by the current adopted S11 layout. DRC reports geometry-rule results; LVS and S14 post-layout verification require separate evidence.' })),
      card('Frozen DRC execution', 'Inspect the S11 identity, GDS hash and pinned rule configuration before execution.', el('div', { class: 'provider-actions' }, el('button', { type: 'button', class: 'primary', text: 'Run DRC', 'data-testid': 'drc-workflow-run', onclick: () => this.start() }), el('button', { type: 'button', text: 'Inspect S11 layout', onclick: () => this.callbacks.navigate('layout') }), el('button', { type: 'button', text: 'Refresh saved DRC runs', 'data-testid': 'drc-workflow-refresh', onclick: () => this.refreshSaved() })), el('p', { class: 'generation-gate', 'data-testid': 'drc-workflow-gate' }), el('div', { class: 'workflow-lineage', 'data-testid': 'drc-workflow-lineage' }), el('div', { 'data-testid': 'drc-workflow-configuration' })),
      card('DRC verification evidence', 'Inspect rule counts, reported locations, complete diagnostics and raw reports before choosing the next action.', el('div', { 'data-testid': 'drc-workflow-result' })),
      card('Saved DRC attempts', 'Each execution is a separate record. Failed and stale results remain inspectable.', el('div', { class: 'generation-job-list', 'data-testid': 'drc-workflow-history' })));
    this.refresh(); this.schedule();
  }
  refresh() {
    if (!this.host?.isConnected || this.project().stage !== 'drc') return;
    const button = this.host.querySelector('[data-testid="drc-workflow-run"]'); if (!button) return;
    const gate = this.gate(), source = this.source(), gds = source?.artifacts?.find(item => item.id === 'gds');
    button.disabled = this.busy || !!gate; button.title = gate || 'Run the fixed DRC checks on the exact adopted S11 GDS.';
    this.host.querySelector('[data-testid="drc-workflow-refresh"]').disabled = this.busy || this.polling;
    this.host.querySelector('[data-testid="drc-workflow-gate"]').textContent = this.busy ? 'Contacting the local DRC execution service…' : gate || 'Ready. Required DRC checks and adoption use the saved policy.';
    this.host.querySelector('[data-testid="drc-workflow-lineage"]').replaceChildren(el('p', { text: `Saved revision ${this.project().envelope.revision.id}` }), el('p', { text: `Adopted S11 ${source?.id || 'Not available'}` }), el('p', { text: `Input GDS SHA-256 ${gds?.sha256 || 'Not available'}` }), el('p', { text: `DRC configuration SHA-256 ${this.data.configuration_sha256 || 'Not configured'}` }));
    this.host.querySelector('[data-testid="drc-workflow-configuration"]').replaceChildren(this.inspect('Recorded DRC runtime and rule configuration', this.data.runtime_configuration));
    this.renderResult(); this.renderHistory(); if (this.reviewHost?.isConnected) this.renderReview(this.reviewHost); this.callbacks.chrome?.();
  }
  artifactURL(run, id) { return `/api/artifacts/drc-workflow/${encodeURIComponent(run.id)}/${id}`; }
  artifacts(run) { return (run.artifacts || []).filter(item => FILES.has(item.id) && item.url === this.artifactURL(run, item.id)); }
  renderResult() {
    const host = this.host?.querySelector('[data-testid="drc-workflow-result"]'); if (!host) return;
    const run = this.selected();
    if (!run) { host.replaceChildren(...[el('p', { class: 'empty-small', text: 'No DRC execution evidence exists. The S11 routing checks do not establish an S12 result.' }), this.reconnect()].filter(Boolean)); return; }
    const checks = run.checks || {}, lineage = Object.fromEntries(['revision_id', 'layout_run_id', 'layout_record_sha256', 'input_gds_sha256', 'configuration_sha256', 'source_identity', 'source_key', 'source_epoch_at_start', 'acceptance_epoch'].filter(key => Object.hasOwn(run, key)).map(key => [key, run[key]]));
    host.replaceChildren(...[
      el('div', { class: 'generation-summary', 'data-testid': 'drc-workflow-status' }, badge(run.execution_status), badge(run.validation_status, run.validation_status === 'Passed' ? 'teal' : 'orange'), badge(run.review_status), badge(run.freshness), el('code', { text: run.id })),
      run.error ? el('div', { class: 'generation-error', text: `${run.error.code || 'Execution error'} · ${run.error.message || JSON.stringify(run.error)}` }) : null,
      active(run) ? el('div', { class: 'generation-progress' }, !this.pollError && !this.uncertainStart ? el('span', { class: 'generation-spinner', 'aria-hidden': true }) : null, el('span', { text: this.pollError || this.uncertainStart ? 'Last observed DRC execution was running; current progress is unknown.' : 'Actual DRC checks in progress' }), el('button', { type: 'button', text: 'Cancel DRC run', 'data-testid': 'drc-workflow-cancel', disabled: this.busy, onclick: () => this.cancel(run) })) : null,
      active(run) && this.pollError ? el('div', { class: 'generation-summary', 'data-testid': 'drc-workflow-observation-unavailable' }, badge('Observation unavailable'), el('span', { text: 'The displayed Running status is the last saved observation, not confirmation that DRC is still executing. This read failure does not establish a circuit pass or failure.' })) : null,
      el('p', { class: 'scope-note', 'data-testid': 'drc-workflow-scope', text: 'Results apply to this exact layout and recorded PDK rule decks. Missing reports or nonnumeric counts are not zero violations. A DRC pass does not establish LVS, electrical performance, fabrication approval or dynamic SDF verification.' }),
      (run.diagnostics || []).map(item => el('div', { class: `diagnostic ${item.severity || 'info'}` }, badge(item.severity || 'info'), el('code', { text: item.code || '' }), el('span', { text: item.message || JSON.stringify(item) }))),
      this.inspect('Required DRC verification checks', checks.checks || {}, { open: true, 'data-testid': 'drc-workflow-checks' }),
      this.inspect('Reported DRC counts and metrics', checks.metrics || {}, { open: true, 'data-testid': 'drc-workflow-metrics' }),
      this.inspect('Reported rules and violation locations', checks.summary || checks.report_summary || run.summary || { availability: 'No structured location summary was returned. Inspect the complete raw reports below.' }, { open: true, 'data-testid': 'drc-workflow-locations' }),
      this.inspect('All commands, raw logs, warnings, reports and output record', checks, { 'data-testid': 'drc-workflow-logs' }),
      this.inspect('Frozen S11, GDS, runtime and source lineage', lineage, { 'data-testid': 'drc-workflow-frozen-input' }),
      this.inspect('Exact adopted S11 snapshot', run.layout_snapshot), this.inspect('Recorded runtime configuration', run.runtime_configuration),
      el('p', { class: 'scope-note', text: 'JSON previews use browser number precision. JSON downloads preserve the exact backend response text. Raw artifact downloads verify the saved hash and byte count.' }),
      el('div', { class: 'generation-artifact-actions' }, el('button', { type: 'button', text: 'Download DRC run JSON', 'data-testid': 'drc-workflow-download-run', onclick: () => downloadJsonResponse(`/api/drc-workflow/runs/${encodeURIComponent(run.id)}`, `${safe(run.id)}.json`, this.callbacks.notify) }), JSON_FIELDS.map(id => el('button', { type: 'button', text: 'Download ' + id, 'data-testid': 'drc-workflow-download-' + id, onclick: () => downloadJsonResponse(this.artifactURL(run, id), `${safe(run.id)}-${id}.json`, this.callbacks.notify) })), this.artifacts(run).map(item => el('button', { type: 'button', text: `Download ${item.id.toUpperCase()} · ${item.bytes} bytes`, 'data-testid': 'drc-workflow-download-' + item.id, onclick: () => this.downloadFile(run, item) }))), this.reconnect(),
    ].filter(Boolean));
  }
  async downloadFile(run, item) {
    try {
      if (!FILES.has(item.id) || item.url !== this.artifactURL(run, item.id)) throw new Error('This artifact is outside the fixed DRC routes.');
      const response = await sessionFetch(this.artifactURL(run, item.id), { cache: 'no-store', credentials: 'same-origin' }); if (!response.ok) throw new Error(`Artifact download failed (${response.status}).`);
      const bytes = new Uint8Array(await response.arrayBuffer()), digest = Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', bytes))).map(value => value.toString(16).padStart(2, '0')).join('');
      if (digest !== item.sha256 || bytes.length !== item.bytes) throw new Error('Artifact bytes do not match the saved hash and size. The download was stopped.');
      const url = URL.createObjectURL(new Blob([bytes], { type: item.content_type || 'application/octet-stream' })); const link = el('a', { href: url, download: `${safe(run.id)}-${item.id}.${EXTENSIONS[item.id] || 'json'}` }); document.body.append(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (error) { this.callbacks.notify(error.message, 'error'); }
  }
  renderHistory() {
    const host = this.host?.querySelector('[data-testid="drc-workflow-history"]'); if (!host) return;
    host.replaceChildren(...(this.data.runs.length ? this.data.runs.toReversed().map(run => el('button', { type: 'button', class: `generation-job-button${run.id === this.selected()?.id ? ' selected' : ''}`, 'data-testid': 'drc-workflow-run-' + run.id, onclick: () => { this.runId = run.id; this.refresh(); } }, badge(run.execution_status), badge(run.validation_status), badge(run.review_status), badge(run.freshness), el('code', { text: run.id }), el('small', { text: `S11 ${run.layout_run_id} · ${run.created_at || ''}` }))) : [el('p', { class: 'empty-small', text: 'No recorded DRC attempts.' })]));
  }
  renderReview(host) {
    if (!host) return; this.reviewHost = host; const run = this.selected(); if (!run) { host.replaceChildren(el('p', { text: 'Run the fixed DRC checks to inspect evidence and adoption.' })); return; }
    const p = this.project(), reviewable = run.id === this.data.latest_run_id && !active(run) && !p.dirty && !p.conflict && !p.busy && !this.busy && !this.anyActive(), reviews = this.data.reviews.filter(item => item.run_id === run.id), decision = reviews.findLast(item => item.decision === 'accepted');
    const old = host.querySelector('[data-testid="drc-workflow-feedback"]'), focused = old === document.activeElement, selection = focused ? [old.selectionStart, old.selectionEnd] : null;
    const note = el('textarea', { rows: 3, value: this.notes.get(run.id) || '', 'aria-label': 'DRC feedback', 'data-testid': 'drc-workflow-feedback', placeholder: 'Describe the observed rule violation or requested correction.', oninput: event => this.notes.set(run.id, event.target.value) }), target = this.targets.get(run.id) || 'layout';
    host.replaceChildren(el('div', { class: 'generation-review-status' }, badge(run.review_status), badge(run.freshness), el('code', { text: run.id })), el('p', { class: 'scope-note', 'data-testid': 'drc-workflow-adoption-provenance', text: decision?.actor === 'automation_policy' ? `Recorded adoption by authorized policy ${decision.provenance?.policy_id || decision.policy_id || ''}; this is not a manual human click.` : run.review_status === 'Accepted' && decision ? 'Accepted by explicit review; its actor and provenance are recorded below.' : 'Required DRC checks for current sources must pass before adoption. Inspect failures and return for corrections as needed.' }), el('div', { class: 'field' }, el('label', { text: 'Review and debug feedback' }), note), field('Return destination', target, value => this.targets.set(run.id, value), { choices: RETURNS, 'data-testid': 'drc-workflow-return-target' }), el('div', { class: 'review-actions' }, el('button', { type: 'button', class: 'primary', text: run.review_status === 'Accepted' ? 'DRC accepted' : 'Accept verified DRC run', 'data-testid': 'drc-workflow-accept', disabled: !reviewable || run.freshness !== 'Current' || run.validation_status !== 'Passed' || run.review_status === 'Accepted', onclick: () => this.review(run, 'accepted', note.value) }), el('button', { type: 'button', text: 'Request Changes', 'data-testid': 'drc-workflow-request-changes', disabled: !reviewable, onclick: () => this.review(run, 'changes_requested', note.value) }), el('button', { type: 'button', text: 'Return to selected stage', 'data-testid': 'drc-workflow-return', disabled: !reviewable, onclick: () => this.review(run, 'return_to_stage', note.value, this.targets.get(run.id) || target) }), el('button', { type: 'button', text: p.envelope.workflow.find(stage => stage.id === 'lvs')?.implemented ? 'Continue to LVS' : 'S13 LVS · not implemented', 'data-testid': 'drc-workflow-continue', disabled: !p.envelope.workflow.find(stage => stage.id === 'lvs')?.implemented || !reviewable || run.freshness !== 'Current' || run.review_status !== 'Accepted', onclick: () => this.callbacks.navigate('lvs') })), this.inspect('Exact DRC adoption and feedback records', reviews));
    if (focused) { note.focus({ preventScroll: true }); note.setSelectionRange(...selection); }
  }
  reconnect() { return this.pollError || this.uncertainStart ? el('div', { class: 'generation-error' }, el('p', { text: this.pollError || 'The start outcome is unknown. Refresh saved history without resending.' }), el('button', { type: 'button', text: 'Reconnect without resending', 'data-testid': 'drc-workflow-reconnect', disabled: this.busy || this.polling, onclick: () => this.refreshSaved() })) : null; }
  async start() {
    if (this.busy || this.gate()) return; const p = this.project(), source = this.source(); this.busy = true; this.refresh();
    try { const response = await this.callbacks.request('drc-workflow/runs', { stage: 'drc', layout_run_id: source.id, revision_id: p.envelope.revision.id }); this.runId = response.drc_workflow?.latest_run_id; this.pollError = null; this.uncertainStart = false; this.callbacks.envelope(response); this.callbacks.toast('DRC started from the exact adopted S11 GDS and recorded rule configuration.'); }
    catch (error) { this.uncertainStart = true; this.pollError = `${error.message} Refresh saved runs; the request is not automatically resent.`; this.callbacks.notify(this.pollError, 'error'); }
    finally { this.busy = false; this.refresh(); this.schedule(); }
  }
  async cancel(run) { if (this.busy) return; this.busy = true; this.refresh(); try { this.callbacks.envelope(await this.callbacks.request(`drc-workflow/runs/${encodeURIComponent(run.id)}/cancel`, {})); } catch (error) { this.callbacks.notify(`${error.message} Refresh saved history to inspect cancellation.`, 'error'); } finally { this.busy = false; this.refresh(); this.schedule(); } }
  async review(run, decision, note, target) {
    if (this.busy) return; if (decision !== 'accepted' && !note.trim()) { this.callbacks.toast('Record the issue or return reason first.'); return; } this.busy = true; this.refresh();
    try { this.callbacks.envelope(await this.callbacks.request(`drc-workflow/runs/${encodeURIComponent(run.id)}/review`, { decision, note: note.trim(), ...(target ? { target_stage: target } : {}) })); if (target) this.callbacks.navigate(target); } catch (error) { this.callbacks.notify(error.message, 'error'); } finally { this.busy = false; this.refresh(); }
  }
  finishRead() {
    this.polling = false;
    try { this.refresh(); }
    catch (error) {
      this.pollError = `${error.message || 'The DRC view could not render.'} Saved results were not changed. Reconnect to read saved progress; no execution was resent.`;
      const button = this.host?.querySelector('[data-testid="drc-workflow-refresh"]'); if (button) button.disabled = this.busy;
      this.host?.querySelector('[data-testid="drc-workflow-result"]')?.append(this.reconnect());
      this.callbacks.notify?.(this.pollError, 'error');
    }
    this.schedule();
  }
  async refreshSaved() { if (this.busy || this.polling) return; this.polling = true; try { this.refresh(); this.callbacks.envelope(await this.callbacks.request('project')); this.pollError = null; this.uncertainStart = false; } catch (error) { this.pollError = `${error.message} The tool request is not resent.`; this.callbacks.notify(this.pollError, 'error'); } finally { this.finishRead(); } }
  schedule() { if (this.pollTimer || this.polling || this.pollError || (!this.data.runs.some(active) && !this.pendingPolicy())) return; this.pollTimer = setTimeout(() => { this.pollTimer = null; this.poll(); }, 1500); }
  async poll() { if (this.polling) return; this.polling = true; try { this.refresh(); const response = await this.callbacks.request('drc-workflow'); this.callbacks.workflow(response.drc_workflow); this.pollError = null; this.pollCount = (this.pollCount || 0) + 1; if (!this.data.runs.some(active) || this.pollCount % 3 === 0) this.callbacks.envelope(await this.callbacks.request('project')); } catch (error) { this.pollError = `${error.message} Reconnecting reads saved progress without resending execution.`; } finally { this.finishRead(); } }
}
