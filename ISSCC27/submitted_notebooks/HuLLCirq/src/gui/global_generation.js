import { element as el, field, badge, downloadJsonResponse } from './dom.js';

const ACTIVE = new Set(['Queued', 'Running']);
const safe = value => String(value).replace(/[^a-z0-9_.-]/gi, '_');
const card = (title, subtitle, ...children) => el('section', { class: 'card' }, el('div', { class: 'card-heading' }, el('h2', { text: title }), el('p', { text: subtitle })), ...children);
const details = (title, value) => el('details', { class: 'raw-result' }, el('summary', { text: title }), el('pre', { text: JSON.stringify(value ?? {}, null, 2) }));
function textDownload(value, filename) {
  const url = URL.createObjectURL(new Blob([value], { type: 'text/plain' }));
  const a = el('a', { href: url, download: filename }); document.body.append(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/** S08 uses adopted public boundaries; generation and checks are server records. */
export class GlobalGeneration {
  constructor(callbacks) {
    this.callbacks = callbacks; this.data = { jobs: [], reviews: [], ready: false }; this.selectedId = null;
    this.operation = 'generate'; this.baseId = null; this.instruction = ''; this.preview = null;
    this.busy = false; this.polling = false; this.pollTimer = null; this.pollError = null; this.uncertainStart = false;
    this.tab = 'rtl'; this.note = '';
    this.previewBudgetNotice = null;
  }
  project() { return this.callbacks.project(); }
  generic(job = null) { return (job ? job.context?.verification_plan?.kind : this.project().design?.global_verification?.kind) === 'generic_cycle_vectors'; }
  blocker() {
    return !this.data.ready && ['generic_global_contract', 'invalid_generic_cycle_contract', 'global_nodes_unsupported', 'unsupported_global_settings', 'npu2_global_integration_unsupported'].includes(this.data.blocked_code)
      ? { kind: 'input_required', message: this.data.blocked_reason, setup_action: { label: 'Configure system interface and cycle vectors', testId: 'global-verification-settings' } } : null;
  }
  selected() { return this.data.jobs.find(j => j.id === this.selectedId) || this.data.jobs.at(-1); }
  gate() {
    const p = this.project();
    if (p.conflict) return 'A newer saved design was detected. Open saved before global generation.';
    if (p.dirty) return 'Save the complete design before global generation.';
    if (this.callbacks.providerGate?.()) return this.callbacks.providerGate();
    if (p.postlayoutRunning) return 'A post-layout tool run is active. Inspect or cancel it before starting another operation.';
    if (p.lvsRunning) return 'An LVS tool run is active. Inspect or cancel it before requesting generation.';
    if (this.data.storage_error) return this.data.storage_error.message;
    if (this.uncertainStart || this.pollError) return this.pollError || 'The last start response was interrupted. Refresh saved global jobs before trying again; the request is not automatically resent.';
    if (!this.data.ready) return this.data.blocked_reason || 'All required node specifications must be current and adopted; this design must also be supported by the integration checker.';
    if (this.data.jobs.some(j => ACTIVE.has(j.execution_status))) return 'A global model request is active.';
    return '';
  }
  receive(envelope) {
    if (envelope.global_generation) this.data = envelope.global_generation;
    this.refresh(); this.schedule();
  }
  render(host) {
    this.host = host;
    host.replaceChildren(
      el('div', { class: 'spec-intro' }, badge(`${this.project().design.nodes.length} design nodes`), badge('Adopted node evidence required'),
        el('p', { text: this.generic() ? 'Generate integration through the saved local model. Compile the exact adopted modules and check this project’s independently declared cycle vectors at every public output. S09 and physical design remain separate.' : 'Generate the top through the saved local model. Verification compiles the exact adopted modules and checks the same original matrix job at the external ports. S09 and physical design remain separate.' })),
      card('Frozen global request', 'Public ports, saved edges and integration rules enter the prompt. Full source RTL and node specifications remain in the source manifest.',
        el('p', { 'data-testid': 'global-verification-profile', text: this.generic() ? 'Verification profile: Generic finite cycle vectors v1 · selected by the saved global_verification contract.' : 'Verification profile: Existing saved project-specific contract. To choose generic cycle vectors explicitly, configure it in Specifications; this never substitutes an NPU example.' }),
        el('button', { type: 'button', text: 'Configure system interface and cycle vectors', 'data-testid': 'global-verification-settings', onclick: () => this.callbacks.navigate('specifications') }),
        el('div', { class: 'form-grid' },
          field('Operation', this.operation, value => { this.operation = value; this.preview = null; this.baseId = this.selected()?.rtl ? this.selected().id : this.data.jobs.findLast(j => j.rtl)?.id; this.render(this.host); }, { 'data-testid': 'global-operation', choices: [['generate', 'Generate integration RTL'], ['repair', 'Repair global candidate']] }),
          this.operation === 'repair' ? field('Candidate to repair', this.baseId || '', value => { this.baseId = value; this.preview = null; this.refresh(); }, { 'data-testid': 'global-base-job', choices: this.data.jobs.filter(j => j.rtl).map(j => [j.id, j.id]) }) : null,
          field(this.operation === 'repair' ? 'Required correction' : 'Additional integration instruction', this.instruction, value => { this.instruction = value; this.preview = null; this.refresh(); }, { multiline: true, 'data-testid': 'global-instruction' })),
        el('div', { class: 'provider-actions' },
          el('button', { type: 'button', text: 'Context Preview', 'data-testid': 'global-context-preview', onclick: () => this.prepare() }),
          el('button', { type: 'button', class: 'primary', text: this.operation === 'repair' ? 'Repair global RTL' : 'Generate global RTL', 'data-testid': 'global-generate', onclick: () => this.start() }),
          el('button', { type: 'button', text: 'Refresh saved global jobs', 'data-testid': 'global-refresh', onclick: () => this.refreshSaved() })),
        el('p', { class: 'generation-gate', 'data-testid': 'global-gate' }),
        el('p', { class: 'generation-error', 'data-testid': 'global-reconnect', hidden: true }),
        el('div', { class: 'generation-preview', 'data-testid': 'global-preview' })),
      card('Global RTL evidence', 'Inspect the generated top, original-job results, failures and events before returning or proceeding.', el('div', { class: 'generation-artifact', 'data-testid': 'global-result' })),
      card('Saved global attempts', 'Retries append new records. Reconnecting never resends a model request.', el('div', { 'data-testid': 'global-history' })));
    this.refresh(); this.renderPreview(); this.schedule();
  }
  refresh() {
    if (!this.host?.isConnected || this.project().stage !== 'global_rtl_generation') return;
    const gate = this.gate();
    this.host.querySelector('[data-testid="global-gate"]').textContent = this.busy ? 'Working with the saved global request…' : gate || 'All required sources are ready. Preview the complete request before generation.';
    this.host.querySelector('[data-testid="global-context-preview"]').disabled = this.busy || !!gate;
    this.host.querySelector('[data-testid="global-generate"]').disabled = this.busy || !!gate || !this.preview;
    this.host.querySelector('[data-testid="global-refresh"]').disabled = this.busy;
    const reconnect = this.host.querySelector('[data-testid="global-reconnect"]');
    reconnect.hidden = !(this.uncertainStart || this.pollError);
    reconnect.textContent = this.pollError || 'The last start response was interrupted. Use Refresh saved global jobs to read durable progress before deciding whether to retry. No model request is resent.';
    this.renderResult(); this.renderHistory(); this.renderPreview();
    if (this.reviewHost?.isConnected) this.renderReview(this.reviewHost);
  }
  payload() {
    return { revision_id: this.project().envelope.revision.id, operation: this.operation, instruction: this.instruction,
      ...(this.operation === 'repair' ? { base_job_id: this.baseId } : {}) };
  }
  previewNoticeScope() {
    const p = this.project(), identity = p.envelope.workspace_identity || {};
    return JSON.stringify([p.design?.project?.id, identity.project_id, identity.system_id, identity.session_id,
      p.envelope.revision.id, this.operation, this.operation === 'repair' ? this.baseId : null]);
  }
  async prepare() {
    if (this.busy || this.gate()) return;
    const scope = this.previewNoticeScope();
    this.busy = true; this.refresh();
    try {
      this.preview = await this.callbacks.request('global-generation/context', this.payload());
      if (this.previewBudgetNotice?.scope === scope && this.previewNoticeScope() === scope) {
        this.callbacks.resolveNotice?.(this.previewBudgetNotice.notice);
        this.previewBudgetNotice = null;
      }
      this.callbacks.toast('Global preview prepared. No model request was made.');
    } catch (e) {
      this.preview = null;
      const notice = this.callbacks.notify(e.message, 'error');
      if (e.code === 'global_context_budget') this.previewBudgetNotice = { scope, notice };
    }
    finally { this.busy = false; this.refresh(); }
  }
  renderPreview() {
    const host = this.host?.querySelector('[data-testid="global-preview"]'); if (!host) return;
    const p = this.preview;
    if (!p) { host.replaceChildren(el('p', { text: 'No current global request preview. Current adopted node evidence and support for this integration contract are required.' })); return; }
    host.replaceChildren(el('p', { text: 'Source revision ' + p.revision_id + (p.requested_revision_id && p.requested_revision_id !== p.revision_id ? ' · saved request revision ' + p.requested_revision_id + ' (presentation-only changes)' : '') + ' · profile ' + p.profile_revision_id + ' · ' + p.estimated_input_tokens + ' conservative input tokens' }),
      el('p', { text: 'Full artifacts retain exact backend integers. Pretty-printed browser JSON can use limited number precision.' }),
      el('details', { open: true }, el('summary', { text: 'Exact compact model prompt' }), el('pre', { 'data-testid': 'global-context-prompt', text: p.messages.map(m => m.role + ':\n' + m.content).join('\n\n') })),
      details('Adopted source identities', p.source_manifest.nodes.map(n => ({ node_id: n.node_id, candidate_id: n.candidate_id, spec_id: n.spec_id, rtl_sha256: n.rtl_sha256 }))),
      el('button', { type: 'button', text: 'Download exact preview and source manifest', 'data-testid': 'global-download-preview',
        onclick: () => downloadJsonResponse('/api/artifacts/global-preview/' + encodeURIComponent(p.context_id) + '/context', 'global-preview.json', this.callbacks.notify) }));
  }
  async start() {
    if (this.busy || this.gate() || !this.preview) return;
    this.busy = true; this.refresh();
    try {
      const response = await this.callbacks.request('global-generation/start', { ...this.payload(), context_id: this.preview.context_id, profile_revision_id: this.preview.profile_revision_id });
      this.selectedId = response.global_generation.latest_job_id; this.preview = null;
      this.pollError = null; this.uncertainStart = false;
      this.callbacks.envelope(response); this.callbacks.toast('Global local-model request started. Its exact sources and original-job plan are frozen.');
    } catch (e) {
      this.uncertainStart = true;
      this.pollError = `${e.message} Refresh saved global jobs before trying again. No request is automatically resent.`;
      this.callbacks.notify(this.pollError, 'error');
    }
    finally { this.busy = false; this.refresh(); this.schedule(); }
  }
  renderHistory() {
    const host = this.host?.querySelector('[data-testid="global-history"]'); if (!host) return;
    host.replaceChildren(...this.data.jobs.toReversed().map(j => el('button', { type: 'button', class: 'generation-job-entry',
      'data-testid': 'global-job-' + j.id, onclick: () => { this.selectedId = j.id; this.refresh(); this.callbacks.chrome(); } },
      el('code', { text: j.id }), badge(j.execution_status), badge(j.validation_status), badge(j.review_status), badge(j.freshness))));
  }
  renderResult() {
    const host = this.host?.querySelector('[data-testid="global-result"]'); if (!host) return;
    const j = this.selected(); if (!j) { host.replaceChildren(el('p', { text: 'No global candidate or execution evidence exists.' })); return; }
    const tabs = el('div', { class: 'generation-result-tabs' }, ['rtl', 'checks', 'raw', 'events'].map(id => el('button', { type: 'button', text: id === 'rtl' ? 'Candidate top RTL' : id === 'checks' ? 'Checks' : id === 'raw' ? 'Raw answer' : 'Events & record',
      'data-testid': 'global-tab-' + id, onclick: () => { this.tab = id; this.renderResult(); } })));
    const body = this.tab === 'rtl' ? j.rtl || 'No top RTL extracted.' : this.tab === 'raw' ? j.raw_content || 'No answer recorded.'
      : JSON.stringify(this.tab === 'checks' ? { checks: j.checks, diagnostics: j.diagnostics, error: j.error } : { events: j.events, usage: j.usage, finish_reason: j.finish_reason }, null, 2);
    host.replaceChildren(...[el('div', { class: 'provider-identity', 'data-testid': 'global-job-status' }, badge(j.execution_status), badge(j.validation_status), badge(j.review_status), badge(j.freshness), el('code', { text: j.id })),
      el('p', { text: this.generic(j) ? 'Local-model origin · independently saved finite cycle vectors · zero-delay RTL execution only. Per-cycle signal samples are not a count of stream transfers. S09 and physical verification have no inferred result.' : 'Local-model origin · one original matrix job · zero-delay RTL execution only. S09 synthesis and physical verification have no inferred result.' }),
      ACTIVE.has(j.execution_status) ? el('button', { type: 'button', text: 'Cancel global request', 'data-testid': 'global-cancel', onclick: () => this.cancel(j) }) : null,
      tabs, el('pre', { 'data-testid': 'global-result-content', text: body, style: 'white-space:pre;overflow-wrap:normal;' }),
      el('div', { class: 'generation-artifact-actions' },
        ...[['job', 'Download global job JSON', '/api/global-generation/jobs/' + encodeURIComponent(j.id)],
          ['context', 'Download exact context', '/api/artifacts/global-generation/' + encodeURIComponent(j.id) + '/context'],
          ['source-manifest', 'Download adopted source manifest', '/api/artifacts/global-generation/' + encodeURIComponent(j.id) + '/source-manifest'],
          ['plan', 'Download original-job verification plan', '/api/artifacts/global-generation/' + encodeURIComponent(j.id) + '/verification-plan']].map(([kind, text, endpoint]) =>
            el('button', { type: 'button', text, 'data-testid': 'global-download-' + kind, onclick: () => downloadJsonResponse(endpoint, safe(j.id) + '-' + kind + '.json', this.callbacks.notify) })),
        j.rtl ? el('button', { type: 'button', text: 'Download top RTL', 'data-testid': 'global-download-rtl', onclick: () => textDownload(j.rtl, safe(j.id) + '.v') }) : null)].filter(Boolean));
  }
  renderReview(host) {
    this.reviewHost = host; const j = this.selected();
    if (!j) { host.replaceChildren(el('p', { text: 'No global result to review. Prepare a request after all required node specifications are adopted.' })); return; }
    const reviewable = !ACTIVE.has(j.execution_status) && !this.project().dirty && !this.project().conflict && j.id === this.data.jobs.at(-1)?.id;
    const current = j.freshness === 'Current' && reviewable;
    host.replaceChildren(el('p', { text: j.review_status === 'Accepted' ? (this.generic(j) ? 'The saved independent cycle-vector verification passed. Adoption follows the recorded user policy or explicit review; finite checks are not exhaustive proof.' : 'The original whole-matrix verification passed. Adoption follows the recorded user policy or explicit review; inspect its actual provenance below.') : 'Inspect failures, request a repair, or return to the node specifications. No acceptance is inferred.' }),
      field('Review or repair feedback', this.note, value => { this.note = value; }, { multiline: true, 'data-testid': 'global-review-note' }),
      el('div', { class: 'decision-actions' },
        el('button', { type: 'button', text: j.review_status === 'Accepted' ? 'Global RTL accepted' : 'Accept verified global RTL', 'data-testid': 'global-accept', disabled: !current || j.validation_status !== 'Passed' || j.review_status === 'Accepted', onclick: () => this.review(j, 'accepted') }),
        el('button', { type: 'button', text: 'Request Changes', 'data-testid': 'global-request-changes', disabled: !reviewable, onclick: () => this.review(j, 'changes_requested') }),
        el('button', { type: 'button', text: 'Return to Node Specifications', 'data-testid': 'global-return', disabled: !reviewable, onclick: () => this.review(j, 'return_to_stage') }),
        el('button', { type: 'button', text: 'Use feedback for repair', 'data-testid': 'global-prepare-repair', disabled: !j.rtl || ACTIVE.has(j.execution_status), onclick: () => { this.operation = 'repair'; this.baseId = j.id; this.instruction = this.note; this.preview = null; this.render(this.host); } }),
        el('button', { type: 'button', text: this.project().envelope.workflow.find(stage => stage.id === 'global_synthesis')?.implemented ? 'Continue to Global Synthesis' : 'Global Synthesis · not implemented', 'data-testid': 'global-continue', disabled: !current || j.validation_status !== 'Passed' || j.review_status !== 'Accepted' || !this.project().envelope.workflow.find(stage => stage.id === 'global_synthesis')?.implemented, onclick: () => this.callbacks.navigate('global_synthesis') })),
      details('Exact global adoption records', this.data.reviews.filter(r => r.job_id === j.id)));
  }
  async review(job, decision) {
    if (this.busy) return;
    if (decision === 'accepted' && this.data.jobs.find(item => item.id === job.id)?.review_status === 'Accepted') return;
    if (decision !== 'accepted' && !this.note.trim()) {
      this.callbacks.toast('Enter the change or return reason in Review or repair feedback.');
      const input = this.reviewHost?.querySelector('[data-testid="global-review-note"]');
      input?.scrollIntoView?.({ behavior: 'smooth', block: 'center' }); input?.focus?.({ preventScroll: true });
      return;
    }
    this.busy = true;
    try {
      const response = await this.callbacks.request('global-generation/review', { job_id: job.id, decision, note: this.note, ...(decision === 'return_to_stage' ? { target_stage: 'node_implementation_specs' } : {}) });
      this.callbacks.envelope(response); this.callbacks.toast('Global review recorded.');
      if (decision === 'return_to_stage') this.callbacks.navigate('node_implementation_specs');
    } catch (e) { this.callbacks.notify(e.message, 'error'); }
    finally { this.busy = false; this.refresh(); }
  }
  async cancel(job) {
    try { this.callbacks.envelope(await this.callbacks.request('global-generation/cancel', { job_id: job.id })); }
    catch (e) { this.callbacks.notify(e.message, 'error'); }
  }
  async refreshSaved() {
    try {
      const response = await this.callbacks.request('global-generation');
      this.data = response.global_generation; this.project().envelope.global_generation = this.data;
      const stage = this.project().envelope.workflow.find(s => s.id === 'global_rtl_generation'), j = this.data.jobs.at(-1);
      Object.assign(stage, { execution_status: j?.execution_status || 'Not Run', validation_status: j?.validation_status || 'Not Checked', review_status: j?.review_status || 'Awaiting Review', freshness: j?.freshness || 'Current', ready: this.data.ready, blocked_reason: this.data.blocked_reason });
      this.pollError = null; this.uncertainStart = false;
      this.refresh(); this.callbacks.chrome();
      // The compact S08 poll does not contain refreshed S09/physical gates.
      // Reconcile dependencies once at a new terminal/adoption observation.
      await this.callbacks.dependencies?.(response);
    } catch (e) {
      this.pollError = `${e.message} Saved progress was not confirmed. Refresh saved global jobs before trying again; no model request is resent.`;
      this.callbacks.notify(this.pollError, 'error');
    }
  }
  schedule() {
    if (this.pollTimer || this.polling || this.pollError || !this.data.jobs.some(j => ACTIVE.has(j.execution_status))) return;
    this.pollTimer = setTimeout(async () => {
      this.pollTimer = null; this.polling = true;
      try { await this.refreshSaved(); }
      finally { this.polling = false; this.schedule(); }
    }, 1500);
  }
}
