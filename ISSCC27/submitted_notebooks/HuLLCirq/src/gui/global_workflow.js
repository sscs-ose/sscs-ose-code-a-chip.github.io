import { element as el, field, badge, downloadJsonResponse } from './dom.js';
import { adoptionProvenance } from './review_operator.js';

const STAGES = new Set(['global_synthesis', 'global_netlist_simulation']);
const ACTIVE = new Set(['Queued', 'Running']);
const active = run => !!run && ACTIVE.has(run.execution_status);
const safe = value => String(value).replace(/[^a-z0-9_.-]/gi, '_');
const card = (title, subtitle, ...children) => el('section', { class: 'card' }, el('div', { class: 'card-heading' }, el('h2', { text: title }), el('p', { text: subtitle })), ...children);
const details = (title, value, attributes = {}) => el('details', { class: 'raw-result', ...attributes }, el('summary', { text: title }), el('pre', { text: JSON.stringify(value ?? {}, null, 2) }));
const EARLIER_STAGES = [
  ['global_settings', 'Global Settings'], ['graph_editor', 'Graph Editor'], ['specifications', 'Specifications'],
  ['local_rtl_generation', 'Local RTL Generation'], ['local_synthesis', 'Local Synthesis'],
  ['local_netlist_simulation', 'Local Netlist Simulation'], ['node_implementation_specs', 'Node Implementation Specs'],
  ['global_rtl_generation', 'Global RTL Generation'], ['global_synthesis', 'Global Synthesis'],
];

function textDownload(source, filename) {
  const url = URL.createObjectURL(new Blob([source], { type: 'text/plain;charset=utf-8' }));
  const link = el('a', { href: url, download: filename }); document.body.append(link); link.click(); link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/** S09/S10 execute persisted whole-design evidence without a new model request. */
export class GlobalWorkflow {
  constructor(callbacks) {
    this.callbacks = callbacks; this.data = { runs: [], reviews: [], stages: [], ready: false };
    this.runId = null; this.notes = new Map(); this.targets = new Map(); this.busy = false;
    this.polling = false; this.pollTimer = null; this.pollError = null; this.uncertainStart = false;
  }
  project() { return this.callbacks.project(); }
  relevant() { return this.data.runs.filter(run => run.stage_id === this.project().stage).toReversed(); }
  selected() { return this.relevant().find(run => run.id === this.runId) || this.relevant()[0]; }
  stageState(id = this.project().stage) { return this.data.stages?.find(stage => stage.stage_id === id); }
  candidate() {
    const data = this.project().envelope.global_generation;
    const job = data?.jobs?.find(item => item.id === data.accepted_job_id) || data?.jobs?.at(-1);
    return job?.execution_status === 'Completed' && job.validation_status === 'Passed' && job.review_status === 'Accepted' && job.freshness === 'Current' ? job : null;
  }
  prior() {
    const id = this.stageState('global_synthesis')?.accepted_run_id;
    return this.data.runs.find(run => run.id === id && run.stage_id === 'global_synthesis' && run.global_job_id === this.candidate()?.id && run.execution_status === 'Completed' && run.validation_status === 'Passed' && run.review_status === 'Accepted' && run.freshness === 'Current') || null;
  }
  receive(envelope) {
    if (envelope.global_workflow) this.data = envelope.global_workflow;
    this.refresh(); this.schedule();
  }
  pendingPolicyRuns() {
    const policy = this.project().envelope.review_policy;
    if (policy?.mode !== 'accept_on_pass' || policy.user_authorized !== true || this.data.storage_error) return [];
    const latest = new Set((this.data.stages || []).map(stage => stage.latest_run_id));
    return this.data.runs.filter(run => latest.has(run.id) && run.execution_status === 'Completed' && run.validation_status === 'Passed'
      && run.review_status === 'Awaiting Review' && run.freshness === 'Current' && !run.error
      && !(run.diagnostics || []).some(item => item.code === 'automatic_adoption_blocked'));
  }
  anyActive() {
    const e = this.project().envelope;
    return this.data.runs.some(active) || (e.postlayout_workflow?.runs || []).some(active) || (e.lvs_workflow?.runs || []).some(active) || (e.drc_workflow?.runs || []).some(active) || (e.physical_workflow?.runs || []).some(active) || (e.workflow_runs || []).some(active) || (e.generation?.jobs || []).some(active) || (e.global_generation?.jobs || []).some(active);
  }
  gate() {
    const p = this.project();
    if (!p.envelope.workflow.find(stage => stage.id === p.stage)?.implemented || !this.data.implemented) return 'This whole-design execution stage is not implemented by the connected service.';
    if (this.data.storage_error) return `Global tool history is unavailable: ${this.data.storage_error.message || this.data.storage_error.code}.`;
    if (p.conflict) return 'A newer saved design was detected. Export your draft, then Open saved.';
    if (p.dirty) return 'Save the complete design before executing whole-design tools.';
    if (p.busy) return 'Wait for the current project operation to finish.';
    if (this.uncertainStart || this.pollError) return this.pollError || 'The last start response was interrupted. Refresh saved runs before trying again; the request is not automatically resent.';
    if (this.anyActive()) return 'A model or tool run is active. Inspect its saved progress or cancel it before starting another.';
    if (!this.data.ready) return this.data.blocked_reason || 'S08 and all required adopted node sources must be current.';
    if (!this.candidate()) return 'A current, verified and adopted S08 global RTL candidate is required.';
    if (p.stage === 'global_netlist_simulation' && !this.prior()) return 'S09 must pass and be adopted for this exact S08 candidate before its complete netlist is verified.';
    return '';
  }
  render(host) {
    this.host = host;
    const synthesis = this.project().stage === 'global_synthesis';
    host.replaceChildren(
      el('div', { class: 'spec-intro' }, badge('Complete saved design'), badge('Generic · no PDK mapping'),
        el('p', { text: 'The adopted S08 top and every required adopted module remain bound to the original GUI input and verification plan. These stages do not perform SKY130 mapping, layout, timing, DRC, LVS or post-layout verification.' })),
      card(synthesis ? 'Frozen whole-design synthesis' : 'Frozen whole-netlist verification', synthesis ? 'Synthesize the exact adopted top and modules with the trusted Yosys configuration. Preserve public module boundaries without flattening.' : this.project().design?.global_verification?.kind === 'generic_cycle_vectors' ? 'Compile only the adopted S09 netlist and check the SAME saved independent cycle vectors and every physical public output. Signal samples are not stream-transfer counts. Source RTL is not linked as a substitute.' : 'Compile only the adopted S09 netlist and check the same original matrix job, every expected output and all public transfers. The adopted source RTL is not linked as a substitute.',
        el('div', { class: 'provider-actions' },
          el('button', { type: 'button', class: 'primary', text: synthesis ? 'Run global generic synthesis' : 'Run global netlist verification', 'data-testid': 'global-workflow-run', onclick: () => this.start() }),
          el('button', { type: 'button', text: 'Inspect S08 global RTL', 'data-testid': 'global-workflow-source', onclick: () => this.callbacks.navigate('global_rtl_generation') }),
          el('button', { type: 'button', text: 'Refresh saved tool runs', 'data-testid': 'global-workflow-refresh', onclick: () => this.refreshSaved() })),
        el('p', { class: 'generation-gate', 'data-testid': 'global-workflow-gate' }),
        el('div', { class: 'workflow-lineage', 'data-testid': 'global-workflow-lineage' })),
      card('Whole-design execution evidence', 'Actual tool commands, logs, public-boundary checks and immutable source identities are recorded separately for each attempt.', el('div', { class: 'workflow-result', 'data-testid': 'global-workflow-result' })),
      card('Saved whole-design runs', 'Old failures and stale results remain inspectable. Rerunning appends a new record.', el('div', { class: 'generation-job-list', 'data-testid': 'global-workflow-history' })));
    this.refresh(); this.schedule();
  }
  refresh() {
    if (!this.host?.isConnected || !STAGES.has(this.project().stage)) return;
    const gate = this.gate();
    const start = this.host.querySelector('[data-testid="global-workflow-run"]');
    if (!start) return;
    start.disabled = this.busy || !!gate; start.title = gate || 'Execute the exact current adopted sources with the trusted tool configuration.';
    this.host.querySelector('[data-testid="global-workflow-refresh"]').disabled = this.busy || this.polling;
    this.host.querySelector('[data-testid="global-workflow-gate"]').textContent = this.busy ? 'Contacting the local execution service…' : gate || 'Ready. Required checks and adoption use the saved policy.';
    const job = this.candidate(), prior = this.prior();
    this.host.querySelector('[data-testid="global-workflow-lineage"]').replaceChildren(
      el('p', { text: `Saved project revision ${this.project().envelope.revision.id}` }),
      el('p', { text: `Adopted S08 candidate ${job?.id || 'Not available'} · top RTL SHA-256 ${job?.rtl_sha256 || 'Not available'}` }),
      el('p', { text: `Adopted S09 run ${prior?.id || 'Not available'} · netlist SHA-256 ${prior?.netlist_sha256 || 'Not available'}` }));
    this.renderResult(); this.renderHistory();
    if (this.reviewHost?.isConnected) this.renderReview(this.reviewHost);
    this.callbacks.chrome?.();
  }
  lineage(run) {
    return Object.fromEntries([
      'stage_id', 'global_job_id', 'revision_id', 'requested_revision_id', 'global_context_id',
      'input_hash', 'design_hash', 'source_manifest_sha256', 'verification_plan_sha256',
      'global_rtl_sha256', 'vector_hash', 'testbench_sha256', 'public_boundary_vector_hash',
      'synthesis_run_id', 'prior_run_id', 'netlist_sha256', 'public_monitor_sha256',
      'instrumented_testbench_sha256', 'adoption_epoch', 'global_adoption_epoch',
      'source_identity', 'source_key', 'source_epoch_at_start', 'acceptance_epoch', 'synthesis_adoption',
    ].filter(key => Object.hasOwn(run, key)).map(key => [key, run[key]]));
  }
  checkSummary(run) {
    const checks = run.checks || {};
    const summary = Object.fromEntries(['scope', 'validation_status', 'executed', 'exit_code', 'source_rtl_linked', 'compiled_design_sources', 'elaborated_instance_counts', 'checks'].filter(key => Object.hasOwn(checks, key)).map(key => [key, checks[key]]));
    if (checks.commands) summary.commands = checks.commands.map(command => ({ command: command.command, status: command.status, executed: command.executed, exit_code: command.exit_code }));
    if (run.verification_plan?.kind === 'generic_cycle_vectors') {
      summary.verification_profile = 'generic_cycle_vectors v1';
      if (Number.isSafeInteger(checks.signal_sample_count)) summary.observed_signal_sample_count = checks.signal_sample_count;
      else if (Array.isArray(checks.actual_output_transfers)) summary.observed_signal_sample_count = checks.actual_output_transfers.length;
      if (Number.isSafeInteger(checks.expected_signal_samples)) summary.expected_signal_sample_count = checks.expected_signal_samples;
      summary.scope_note = 'Per-cycle output-pin samples, not stream transfers or PE participation.';
    } else for (const [key, count] of [['actual_output_transfers', 'observed_output_count'], ['actual_pe_lane_transfers', 'observed_pe_count'], ['actual_public_stream_transfers', 'observed_public_stream_count']]) if (Array.isArray(checks[key])) summary[count] = checks[key].length;
    return summary;
  }
  renderResult() {
    const host = this.host?.querySelector('[data-testid="global-workflow-result"]'); if (!host) return;
    const run = this.selected();
    if (!run) {
      host.replaceChildren(...[el('p', { class: 'empty-small', text: 'No tool run has been recorded for this stage. No netlist or verification result is inferred.' }), this.reconnectControl()].filter(Boolean));
      return;
    }
    const netlist = run.netlist || run.checks?.synthesis?.netlist;
    host.replaceChildren(...[
      el('div', { class: 'generation-summary', 'data-testid': 'global-workflow-status' }, badge(run.execution_status), badge(run.validation_status, run.validation_status === 'Passed' ? 'teal' : 'orange'), badge(run.review_status, run.review_status === 'Accepted' ? 'teal' : 'neutral'), badge(run.freshness, run.freshness === 'Stale' ? 'orange' : 'neutral'), el('code', { text: run.id })),
      run.summary ? el('p', { text: typeof run.summary === 'string' ? run.summary : JSON.stringify(run.summary) }) : null,
      run.error ? el('div', { class: 'generation-error', text: `${run.error.code || 'Execution error'} · ${run.error.message || JSON.stringify(run.error)}` }) : null,
      this.data.storage_error ? el('div', { class: 'generation-error', text: this.data.storage_error.message || JSON.stringify(this.data.storage_error) }) : null,
      active(run) ? el('div', { class: 'generation-progress' }, el('span', { class: 'generation-spinner', 'aria-hidden': true }), el('span', { text: `${run.execution_status} · actual whole-design tool execution` }), el('button', { type: 'button', text: 'Cancel whole-design run', 'data-testid': 'global-workflow-cancel', disabled: this.busy, onclick: () => this.cancel(run) })) : null,
      el('p', { class: 'scope-note', text: run.stage_id === 'global_synthesis' ? 'Technology-independent synthesis with public module boundaries preserved. A synthesis pass is not a circuit simulation, formal equivalence proof or physical result.' : 'Finite, zero-delay verification of the actual complete generic netlist. External stimulus and expected values inherit the original S08 plan. Public-port paths are rediscovered after synthesis; a changed monitor or instrumented testbench hash is recorded as a new artifact.' }),
      (run.diagnostics || []).map(item => el('div', { class: `diagnostic ${item.severity || 'info'}` }, badge(item.severity || 'info'), el('code', { text: item.code || '' }), el('span', { text: item.message || JSON.stringify(item) }))),
      details('Actual execution summary', this.checkSummary(run), { open: true, 'data-testid': 'global-workflow-check-summary' }),
      details('All checks, complete commands, raw logs and public-boundary results', run.checks, { 'data-testid': 'global-workflow-checks' }),
      details('Frozen source IDs and plan / netlist hashes', this.lineage(run), { 'data-testid': 'global-workflow-frozen-input' }),
      details('Exact adopted source manifest', run.source_manifest),
      details('Inherited original-job verification plan', run.verification_plan),
      details('Execution events', run.events || []),
      netlist ? el('details', {}, el('summary', { text: 'Actual complete synthesized netlist' }), el('pre', { text: netlist, 'data-testid': 'global-workflow-netlist' })) : null,
      el('p', { class: 'scope-note', text: 'JSON previews use browser number precision. JSON downloads save the backend response text without converting its integers through JavaScript numbers.' }),
      el('div', { class: 'generation-artifact-actions' },
        el('button', { type: 'button', text: 'Download run JSON', 'data-testid': 'global-workflow-download-run', onclick: () => downloadJsonResponse(`/api/global-workflow/runs/${encodeURIComponent(run.id)}`, `${safe(run.id)}.json`, this.callbacks.notify) }),
        ...[['verification-plan', 'Download inherited verification plan'], ['source-manifest', 'Download exact adopted source manifest']].map(([kind, text]) => el('button', { type: 'button', text, 'data-testid': `global-workflow-download-${kind}`, onclick: () => this.downloadJsonArtifact(run, kind) })),
        netlist ? el('button', { type: 'button', text: 'Download complete netlist', 'data-testid': 'global-workflow-download-netlist', onclick: () => textDownload(netlist, `${safe(run.id)}-netlist.v`) }) : null,
        run.checks?.synthesis_script ? el('button', { type: 'button', text: 'Download executed synthesis script', 'data-testid': 'global-workflow-download-synthesis-script', onclick: () => this.downloadTextArtifact(run, 'synthesis-script', 'ys') }) : null,
        run.checks?.public_monitor_source ? el('button', { type: 'button', text: 'Download public-port monitor', 'data-testid': 'global-workflow-download-public-monitor', onclick: () => this.downloadTextArtifact(run, 'public-monitor', 'v') }) : null,
        run.checks?.public_port_hierarchy ? el('button', { type: 'button', text: 'Download instrumented netlist testbench', 'data-testid': 'global-workflow-download-instrumented-testbench', onclick: () => this.downloadTextArtifact(run, 'instrumented-testbench', 'v') }) : null,
        el('button', { type: 'button', text: 'Rerun current whole-design sources', 'data-testid': 'global-workflow-rerun', disabled: this.busy || !!this.gate(), onclick: () => this.start() })),
      this.reconnectControl(),
    ].filter(Boolean));
  }
  reconnectControl() {
    if (!this.pollError && !this.uncertainStart) return null;
    return el('div', { class: 'generation-error' }, el('p', { text: this.pollError || 'The last start response was interrupted. Read the saved history to determine whether it started.' }),
      el('button', { type: 'button', text: 'Reconnect without resending', 'data-testid': 'global-workflow-reconnect', disabled: this.busy || this.polling, onclick: () => this.refreshSaved() }));
  }
  downloadJsonArtifact(run, kind) {
    return downloadJsonResponse(`/api/artifacts/global-workflow/${encodeURIComponent(run.id)}/${kind}`, `${safe(run.id)}-${kind}.json`, this.callbacks.notify);
  }
  async downloadTextArtifact(run, kind, extension) {
    try {
      const source = await this.callbacks.request(`artifacts/global-workflow/${encodeURIComponent(run.id)}/${kind}`);
      if (typeof source !== 'string') throw new Error('The saved artifact did not return the expected text.');
      textDownload(source, `${safe(run.id)}-${kind}.${extension}`);
    } catch (error) { this.callbacks.notify(error.message, 'error'); }
  }
  renderHistory() {
    const host = this.host?.querySelector('[data-testid="global-workflow-history"]'); if (!host) return;
    host.replaceChildren(...(this.relevant().length ? this.relevant().map(run => el('button', { type: 'button', class: `generation-job-button${run.id === this.selected()?.id ? ' selected' : ''}`, 'data-testid': `global-workflow-run-${run.id}`, onclick: () => { this.runId = run.id; this.refresh(); } }, badge(run.execution_status), badge(run.validation_status), badge(run.review_status), badge(run.freshness), el('code', { text: run.id }), el('small', { text: `S08 ${run.global_job_id} · ${run.created_at || ''}` }))) : [el('p', { class: 'empty-small', text: 'No recorded whole-design tool runs for this stage.' })]));
  }
  renderReview(host) {
    if (!host) return;
    this.reviewHost = host;
    const run = this.selected();
    if (!run) { host.replaceChildren(el('p', { class: 'empty-small', text: 'Run the current adopted sources to inspect this stage’s actual results and adoption decision.' })); return; }
    const p = this.project(), current = run.freshness === 'Current', latest = this.relevant()[0]?.id === run.id;
    const reviewable = latest && !active(run) && !p.dirty && !p.conflict && !p.busy && !this.busy && !this.anyActive();
    const eligible = current && reviewable;
    const accepted = run.review_status === 'Accepted';
    const reviews = this.data.reviews.filter(item => item.run_id === run.id);
    const decision = reviews.findLast(item => item.decision === 'accepted');
    const oldNote = host.querySelector('[data-testid="global-workflow-feedback"]');
    const focused = oldNote === document.activeElement;
    const selection = focused ? [oldNote.selectionStart, oldNote.selectionEnd] : null;
    const note = el('textarea', { rows: 3, value: this.notes.get(run.id) || '', 'aria-label': 'Whole-design run feedback', 'data-testid': 'global-workflow-feedback', placeholder: 'Record the observed issue, requested correction or manual adoption reason.', oninput: event => this.notes.set(run.id, event.target.value) });
    const target = this.targets.get(run.id) || (run.stage_id === 'global_synthesis' ? 'global_rtl_generation' : 'global_synthesis');
    const returnChoices = EARLIER_STAGES.slice(0, run.stage_id === 'global_synthesis' ? 8 : 9);
    const next = run.stage_id === 'global_synthesis' ? 'global_netlist_simulation' : 'layout';
    const nextImplemented = !!p.envelope.workflow.find(stage => stage.id === next)?.implemented;
    host.replaceChildren(
      el('div', { class: 'generation-review-status' }, badge(run.review_status, accepted ? 'teal' : 'neutral'), badge(run.freshness), el('code', { text: run.id })),
      el('p', { class: 'scope-note', 'data-testid': 'global-workflow-adoption-provenance', text: accepted ? adoptionProvenance(decision) : 'Only required checks for current sources can permit adoption. Failed, unsupported and stale runs remain inspectable.' }),
      el('div', { class: 'field' }, el('label', { text: 'Review and debug feedback' }), note),
      field('Return destination', target, value => this.targets.set(run.id, value), { choices: returnChoices, 'data-testid': 'global-workflow-return-target' }),
      el('div', { class: 'review-actions' },
        el('button', { type: 'button', class: 'primary', text: accepted ? 'Run accepted' : 'Accept verified run', 'data-testid': 'global-workflow-accept', disabled: !eligible || accepted || run.validation_status !== 'Passed', onclick: () => this.review(run, 'accepted', note.value) }),
        el('button', { type: 'button', text: 'Request Changes', 'data-testid': 'global-workflow-request-changes', disabled: !reviewable, onclick: () => this.review(run, 'changes_requested', note.value) }),
        el('button', { type: 'button', text: 'Return to selected stage', 'data-testid': 'global-workflow-return', disabled: !reviewable, onclick: () => this.review(run, 'return_to_stage', note.value, this.targets.get(run.id) || target) }),
        el('button', { type: 'button', text: nextImplemented ? next === 'layout' ? 'Continue to Layout' : 'Continue to Global Netlist Simulation' : 'Layout · not implemented', 'data-testid': 'global-workflow-continue', disabled: !eligible || !accepted || run.validation_status !== 'Passed' || !nextImplemented, onclick: () => this.callbacks.navigate(next) })),
      details('Exact adoption and feedback records', reviews));
    if (focused) { note.focus({ preventScroll: true }); note.setSelectionRange(...selection); }
  }
  async start() {
    if (this.busy || this.gate()) return;
    const project = this.project(), candidate = this.candidate(), prior = this.prior();
    this.busy = true; this.refresh();
    try {
      const response = await this.callbacks.request('global-workflow/runs', { stage: project.stage, global_job_id: candidate.id, revision_id: project.envelope.revision.id, ...(project.stage === 'global_netlist_simulation' ? { synthesis_run_id: prior.id } : {}) });
      this.runId = response.global_workflow?.runs?.filter(run => run.stage_id === project.stage).at(-1)?.id || null;
      this.pollError = null; this.uncertainStart = false; this.callbacks.envelope(response);
      this.callbacks.toast('Whole-design tool run started from the exact adopted sources and original-job plan.');
    } catch (error) {
      this.uncertainStart = true; this.pollError = `${error.message} Refresh saved runs before trying again. No request is automatically resent.`;
      this.callbacks.notify(this.pollError, 'error');
    } finally { this.busy = false; this.refresh(); this.schedule(); }
  }
  async cancel(run) {
    if (this.busy) return;
    this.busy = true; this.refresh();
    try { this.callbacks.envelope(await this.callbacks.request(`global-workflow/runs/${encodeURIComponent(run.id)}/cancel`, {})); }
    catch (error) { this.callbacks.notify(`${error.message} Refresh saved runs to inspect the cancellation outcome.`, 'error'); }
    finally { this.busy = false; this.refresh(); this.schedule(); }
  }
  async review(run, decision, note, target) {
    if (this.busy) return;
    if (decision !== 'accepted' && !note.trim()) { this.callbacks.toast('Record the issue or reason for returning before saving this decision.'); return; }
    this.busy = true; this.refresh();
    try {
      this.callbacks.envelope(await this.callbacks.request(`global-workflow/runs/${encodeURIComponent(run.id)}/review`, { decision, note: note.trim(), ...(target ? { target_stage: target } : {}) }));
      this.callbacks.toast('Whole-design tool decision recorded.');
      if (target) this.callbacks.navigate(target);
    } catch (error) { this.callbacks.notify(error.message, 'error'); }
    finally { this.busy = false; this.refresh(); }
  }
  async refreshSaved() {
    if (this.busy || this.polling) return;
    this.polling = true; this.refresh();
    try {
      this.callbacks.envelope(await this.callbacks.request('project'));
      this.pollError = null; this.uncertainStart = false;
    } catch (error) { this.pollError = `${error.message} The tool request is not resent.`; this.callbacks.notify(this.pollError, 'error'); }
    finally { this.polling = false; this.refresh(); this.schedule(); }
  }
  schedule() {
    if (this.pollTimer || this.polling || this.pollError || (!this.data.runs.some(active) && !this.pendingPolicyRuns().length)) return;
    this.pollTimer = setTimeout(() => { this.pollTimer = null; this.poll(); }, 1500);
  }
  async poll() {
    if (this.polling) return;
    const run = this.data.runs.find(active) || this.pendingPolicyRuns()[0]; if (!run) return;
    this.polling = true; this.refresh();
    try {
      // Run status, stage adoption IDs and review provenance form one snapshot.
      // Updating only a run would expose Accepted beside stale Running tabs.
      const response = await this.callbacks.request('global-workflow');
      this.callbacks.workflow(response.global_workflow);
      const updated = response.global_workflow.runs.find(item => item.id === run.id);
      this.pollError = null; this.pollCount = (this.pollCount || 0) + 1;
      if (!active(updated) || this.pollCount % 3 === 0) this.callbacks.envelope(await this.callbacks.request('project'));
    } catch (error) { this.pollError = `${error.message} Reconnecting reads saved progress and does not resend the tool request.`; }
    finally { this.polling = false; this.refresh(); this.schedule(); }
  }
}
