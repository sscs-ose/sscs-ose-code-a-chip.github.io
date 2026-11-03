import { element as el, field, badge, downloadJsonResponse } from './dom.js';
import { adoptionProvenance } from './review_operator.js';
import { instructionView, promptMessagesView, promptTranscript, repairGuidanceView } from './prompt_view.js';

const PROFILE_DEFAULTS = {
  id: 'local_default', name: 'Local Ollama', api_type: 'chat_completions', execution_location: 'Local',
  base_url: 'http://127.0.0.1:11435/v1', model: 'qwen3:8b', credential_env: '', timeout_seconds: 180,
  context_window: 8192, max_output_tokens: 2048, temperature: 0.2, seed: 101,
  model_revision: 'unknown', quantization: 'unknown', runtime_version: 'unknown', reasoning_effort: null,
};
const PREPARED_RUNTIME_MODELS = new Set(['qwen3:8b', 'qwen2.5-coder:7b']);
const START_RECOVERY_KEY = 'hullcirq.node-start-recovery.v1';
const START_PROTOCOL = 'node-submission-v1';
const START_FIELDS = ['node_id', 'revision_id', 'context_id', 'profile_revision_id', 'operation', 'base_job_id', 'instruction', 'retry_of_job_id'];
const sameStart = (left, right) => !!left && !!right && START_FIELDS.every(key => (left[key] ?? ({ operation: 'generate', instruction: '', base_job_id: null, retry_of_job_id: null })[key]) === (right[key] ?? ({ operation: 'generate', instruction: '', base_job_id: null, retry_of_job_id: null })[key]));
const newSubmissionId = () => {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID();
  if (globalThis.crypto?.getRandomValues) return [...globalThis.crypto.getRandomValues(new Uint8Array(16))].map(value => value.toString(16).padStart(2, '0')).join('');
  return `node-${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}-${Math.random().toString(36).slice(2)}`;
};
const ACTIVE = new Set(['Queued', 'Running']);
const RECOVERABLE = new Set(['Failed', 'Cancelled', 'Interrupted']);
const inProgress = job => job && (ACTIVE.has(job.execution_status) || (job.execution_status === 'Completed' && !job.finished_at));
const PROFILE_KEYS = Object.keys(PROFILE_DEFAULTS);
const clone = value => structuredClone(value);
const same = (left, right) => JSON.stringify(left) === JSON.stringify(right);
const cleanProfile = value => Object.fromEntries(PROFILE_KEYS.map(key => [key, value?.[key] ?? PROFILE_DEFAULTS[key]]));
const date = value => value ? new Date(value).toLocaleString() : 'Not recorded';
const inputEstimate = context => context?.provider_input_estimated_tokens ?? context?.estimated_input_tokens;
const jobInputEstimate = job => job?.provider_input_estimated_tokens ?? inputEstimate(job?.context);
const validEstimate = value => typeof value === 'number' && Number.isFinite(value) && value >= 0;
const tokens = value => typeof value === 'number' && Number.isFinite(value) ? value.toLocaleString('en-US') : 'Unknown';

function card(title, description, content, className = '') {
  return el('section', { class: `card ${className}` }, el('div', { class: 'card-heading' }, el('h2', { text: title }), el('p', { text: description })), content);
}

function downloadText(text, filename, type = 'text/plain') {
  const url = URL.createObjectURL(new Blob([text], { type }));
  const link = el('a', { href: url, download: filename });
  document.body.append(link); link.click(); link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function filename(value) { return String(value).replace(/[^a-z0-9_.-]/gi, '_'); }

/** UI state for explicit provider requests and evidence-backed candidate review. */
export class GenerationWorkspace {
  constructor(callbacks) {
    this.callbacks = callbacks;
    this.llm = { profile: null, profile_revision_id: null, probe: null, capabilities: {} };
    this.generation = { implemented: false, jobs: [], nodes: [], all_nodes_accepted: false };
    this.profileDraft = cleanProfile(null);
    this.profileBusy = false;
    this.runtimeStatus = null;
    this.runtimeCheckedAt = null;
    this.runtimeBusy = false;
    this.runtimeError = null;
    this.runtimeTimer = null;
    this.runtimeMount = 0;
    this.runtimePending = null;
    this.requestBusy = false;
    this.nodeId = null;
    this.operation = 'generate';
    this.baseJobId = null;
    this.instruction = '';
    this.retryOfJobId = null;
    this.recoveryDrafts = new Map();
    this.lastRequestIdentity = null;
    this.profileRequestToken = 0;
    this.requestToken = 0;
    this.submittedRequest = null;
    this.preview = null;
    this.previewStale = true;
    this.selectedJobId = null;
    this.artifactTab = 'rtl';
    this.feedback = new Map();
    this.returnTargets = new Map();
    this.pollTimer = null;
    this.polling = false;
    this.pollToken = 0;
    this.pollFailure = null;
    this.pendingStarts = new Map();
    this.startRecoveryStorage = null; this.startRecoveryStorageError = null;
    this.reconnectingStart = false;
    try {
      if (typeof sessionStorage !== 'undefined') {
        this.startRecoveryStorage = sessionStorage;
        const saved = JSON.parse(sessionStorage.getItem(START_RECOVERY_KEY) || '[]');
        if (!Array.isArray(saved) || saved.some(value => !value || !['scope', 'contextId', 'nodeId', 'revisionId', 'profileRevisionId', 'operation'].every(key => typeof value[key] === 'string') || !Array.isArray(value.knownJobIds) || value.knownJobIds.some(id => typeof id !== 'string'))) throw new Error('Invalid saved start recovery state');
        for (const value of saved) {
          if (value.submissionId !== undefined && (typeof value.submissionId !== 'string' || !/^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/.test(value.submissionId) || !value.request || value.request.submission_id !== value.submissionId || !sameStart(value.request, { node_id: value.nodeId, revision_id: value.revisionId, context_id: value.contextId, profile_revision_id: value.profileRevisionId, operation: value.operation, base_job_id: value.baseJobId, retry_of_job_id: value.retryOfJobId, instruction: value.request.instruction }) || typeof value.request.instruction !== 'string')) throw new Error('Invalid saved frozen submission');
          this.pendingStarts.set(value.scope, value);
        }
      }
    } catch { this.startRecoveryStorageError = 'The browser could not read saved generation-start recovery state. New model requests are blocked until session storage is available and the workspace is reloaded.'; }
  }

  receive(envelope) {
    const identity = JSON.stringify([this.runtimeIdentity(), this.project().design?.id]);
    const switched = this.lastRequestIdentity !== null && this.lastRequestIdentity !== identity;
    this.lastRequestIdentity = identity;
    if (switched) {
      this.retryOfJobId = null; this.preview = null; this.previewStale = true;
      this.operation = 'generate'; this.baseJobId = null; this.instruction = ''; this.selectedJobId = null;
      this.submittedRequest = null;
      this.recoveryDrafts.clear(); this.profileBusy = false; this.requestBusy = false;
      this.profileRequestToken++; this.requestToken++;
      if (this.pollTimer) clearTimeout(this.pollTimer);
      this.pollTimer = null; this.polling = false; this.pollFailure = null; this.pollToken++;
      this.runtimeStatus = null; this.runtimeError = null; this.runtimeCheckedAt = null;
    }
    const wasDirty = !switched && this.profileDirty();
    if (envelope.llm) {
      const previousRevision = this.llm.profile_revision_id;
      this.llm = envelope.llm;
      if (!wasDirty) this.profileDraft = cleanProfile(this.llm.profile);
      if (previousRevision !== this.llm.profile_revision_id) this.previewStale = true;
    }
    if (envelope.generation) this.generation = envelope.generation;
    const project = this.project();
    if (!project.design.nodes.some(node => node.id === this.nodeId)) this.nodeId = project.design.nodes[0]?.id || null;
    if (!this.selectedJob() || this.selectedJob()?.node_id !== this.nodeId) this.selectedJobId = this.nodeState()?.latest_job_id || this.nodeJobs()[0]?.id || null;
    if (this.preview && this.preview.revision_id !== project.envelope.revision.id) this.previewStale = true;
    this.refreshStatus();
    this.schedulePoll();
  }

  project() { return this.callbacks.project(); }
  requestIdentity() {
    const project = this.project();
    return JSON.stringify([this.runtimeIdentity(), project.design?.id, project.envelope?.revision?.id]);
  }
  startScope(envelope = this.project().envelope) {
    const identity = envelope?.workspace_identity;
    return identity?.project_id && identity?.system_id ? JSON.stringify([identity.project_id, identity.system_id]) : JSON.stringify(['standalone', envelope?.design?.id || this.project().design?.id]);
  }
  pendingStart() { return this.pendingStarts.get(this.startScope()); }
  startRecoveryGate() {
    if (this.startRecoveryStorageError) return this.startRecoveryStorageError;
    return this.pendingStart() ? 'The previous generation start has not been reconciled. Refresh saved jobs, or explicitly retry the same keyed request. Other single, batch, repair and integration model requests remain blocked.' : '';
  }
  persistStartRecovery() {
    if (!this.startRecoveryStorage) return true;
    try {
      if (this.pendingStarts.size) this.startRecoveryStorage.setItem(START_RECOVERY_KEY, JSON.stringify([...this.pendingStarts.values()]));
      else this.startRecoveryStorage.removeItem(START_RECOVERY_KEY);
      this.startRecoveryStorageError = null;
      return true;
    } catch {
      this.startRecoveryStorageError = 'The browser could not retain generation-start recovery state. New model requests are blocked; restore session storage and reload before sending another request.';
      return false;
    }
  }
  finishStartRecovery(scope, jobId = null) {
    this.pendingStarts.delete(scope); this.persistStartRecovery();
    if (scope === this.startScope()) {
      if (jobId) this.selectedJobId = jobId;
      this.preview = null; this.previewStale = true; this.submittedRequest = null; this.pollFailure = null;
    }
  }
  matchingStartJobs(pending, jobs) {
    return jobs.filter(job => typeof job.id === 'string' && (pending.submissionId ? job.submission_id === pending.submissionId && sameStart(job, pending.request) :
      !pending.knownJobIds.includes(job.id) && job.context_id === pending.contextId && job.node_id === pending.nodeId && job.revision_id === pending.revisionId &&
      job.profile_revision_id === pending.profileRevisionId && job.operation === pending.operation &&
      (job.base_job_id || null) === (pending.baseJobId || null) && (job.retry_of_job_id || null) === (pending.retryOfJobId || null)));
  }
  observeSavedProgress(envelope) {
    // Only successful scope-checked GET project/bootstrap responses reach here.
    const scope = this.startScope(envelope), pending = this.pendingStarts.get(scope);
    if (!pending || !Array.isArray(envelope.generation?.jobs)) return false;
    let receipt;
    if (pending.submissionId) {
      const receipts = envelope.generation.submissions || {};
      receipt = Object.hasOwn(receipts, pending.submissionId) ? receipts[pending.submissionId] : null;
      if (!receipt || !sameStart(receipt.request, pending.request)) { pending.matchCount = 0; this.persistStartRecovery(); return false; }
      if (receipt.job_id === null && receipt.rejection && Number.isInteger(receipt.rejection.status) && receipt.rejection.status >= 400 && receipt.rejection.status < 500) {
        this.finishStartRecovery(scope); return true;
      }
    }
    const matches = this.matchingStartJobs(pending, envelope.generation.jobs);
    if (matches.length !== 1 || receipt && (receipt.rejection !== null || receipt.job_id !== matches[0].id)) { pending.matchCount = matches.length; this.persistStartRecovery(); return false; }
    this.finishStartRecovery(scope, matches[0].id); return true;
  }
  retryStartGate() {
    const pending = this.pendingStart(), project = this.project();
    if (!pending?.submissionId || !pending.request) return 'This earlier unkeyed attempt can only be inspected; it cannot be safely replayed.';
    if (this.requestBusy || this.reconnectingStart || project.busy) return 'Wait for the current request or saved-status read.';
    if (this.runtimeReadOnly()) return 'This preserved system is read-only.';
    if (project.dirty || project.conflict) return 'Save or reopen the design before explicitly replaying the frozen request.';
    return this.providerRequestGate(true);
  }
  async retrySameStart() {
    if (this.retryStartGate()) return;
    await this.sendStart(this.pendingStart(), true);
  }
  async reconnectStart() {
    if (this.reconnectingStart || !this.pendingStart()) return;
    const scope = this.startScope(), identity = this.requestIdentity();
    this.reconnectingStart = true; this.renderResult();
    try {
      const envelope = await this.callbacks.request('project');
      if (scope !== this.startScope() || identity !== this.requestIdentity() || this.startScope(envelope) !== scope) return;
      this.observeSavedProgress(envelope);
      this.callbacks.envelope(envelope);
      this.callbacks.toast(this.pendingStart() ? 'The submission remains unresolved. Inspect saved progress or explicitly retry the same keyed request; no new identity is created.' : 'The saved submission outcome was recovered. No model request was resent.');
    } catch (error) { if (scope === this.startScope() && identity === this.requestIdentity()) this.callbacks.notify(error.message, 'error'); }
    finally { this.reconnectingStart = false; if (scope === this.startScope() && identity === this.requestIdentity()) this.refreshStatus(); }
  }
  renderStartRecovery() {
    if (!this.pendingStart()) return null;
    return el('div', { class: 'generation-error', 'data-testid': 'generation-start-uncertain' },
      el('p', { text: this.startRecoveryGate() }),
      el('button', { type: 'button', text: 'Refresh saved jobs without resending', disabled: this.reconnectingStart, 'data-testid': 'reconnect-generation', onclick: () => this.reconnectStart() }),
      el('button', { type: 'button', text: 'Retry same request', disabled: !!this.retryStartGate(), title: this.retryStartGate() || 'Reuse the exact saved request and submission identity. The server creates at most one job.', 'data-testid': 'generation-retry-same-start', onclick: () => this.retrySameStart() }));
  }
  profileDirty() { return !same(this.profileDraft, cleanProfile(this.llm.profile)); }
  providerRequestGate(ignorePendingStart = false) {
    if (this.startRecoveryStorageError || !ignorePendingStart && this.startRecoveryGate()) return this.startRecoveryGate();
    if (this.generation.implemented && this.generation.submission_protocol_version !== START_PROTOCOL) return 'Restart the local workspace service to enable safe submission recovery before sending model requests.';
    const batch = this.callbacks.batch?.();
    if (batch?.startUncertain || batch?.analysisStartUncertain) return 'Reconnect to the saved generation batch or guidance analysis before sending another model request.';
    if (this.profileBusy) return 'Wait for the current provider request or connection test to finish.';
    const probe = this.llm.probe;
    if (this.llm.profile_revision_id && probe?.profile_revision_id === this.llm.profile_revision_id && probe.selected_model_available === false)
      return 'The selected model is unavailable for this saved provider profile. Choose an available model or correct the provider setup, then explicitly Test Connection again. No additional model request will be sent while this gate is active.';
    // An absent or earlier-profile probe is not a new testing prerequisite.
    return '';
  }
  nodeState() { return this.generation.nodes.find(node => node.node_id === this.nodeId); }
  nodeJobs() { return [...this.generation.jobs].filter(job => job.node_id === this.nodeId).reverse(); }
  selectedJob() { return this.generation.jobs.find(job => job.id === this.selectedJobId); }
  validationLabel(job) {
    if (!job) return 'Not Checked';
    if (job.stage_validation) return job.stage_validation.validation_status;
    if (job.effective_validation_status) return job.effective_validation_status;
    // Historical reports retain their original checks; S04 evaluates only the external interface.
    if (job.execution_status === 'Completed' && job.rtl) return job.checks?.interface?.validation_status || 'Not Checked';
    return 'Not Checked';
  }
  activeJob() { return this.generation.jobs.find(inProgress); }
  verificationReadiness(job = this.selectedJob()) {
    return this.nodeState()?.behavioral_verification || job?.behavioral_verification || null;
  }
  readinessLabel(readiness) {
    return ({ ready: 'Behavior checks available', implementation_required: 'Checker implementation needed', input_required: 'Specification input needed', configuration_required: 'Verification setup needed' })[readiness?.status] || 'Verification support not reported';
  }
  inspectRequirements() { this.callbacks.navigate?.('specifications', this.nodeId); }
  showNodeReadiness() {
    const target = this.host?.querySelector('#generation-node-progress');
    target?.scrollIntoView?.({ behavior: 'smooth', block: 'center' }); target?.focus?.({ preventScroll: true });
  }
  showChecks() { this.artifactTab = 'checks'; this.renderResult(); this.host?.querySelector('[data-testid="generation-diagnostics"]')?.scrollIntoView?.({ behavior: 'smooth', block: 'center' }); }
  nextUnfinishedNode() {
    return this.project().design.nodes.find(node => node.id !== this.nodeId && !this.generation.nodes.some(item => item.node_id === node.id && item.review_status === 'Accepted' && item.freshness === 'Current' &&
      (!Object.hasOwn(item, 'accepted_job_id') || !!item.latest_job_id && item.latest_job_id === item.accepted_job_id)));
  }
  consumeCompletedRequest() {
    const submitted = this.submittedRequest;
    if (!submitted || submitted.identity !== this.requestIdentity()) return false;
    const job = this.generation.jobs.find(item => item.id === submitted.jobId);
    if (!job || inProgress(job)) return false;
    this.submittedRequest = null;
    // Consume only the exact submitted draft. Later edits and new requests remain intact.
    const payload = { node_id: job.node_id, revision_id: job.revision_id, operation: job.operation, instruction: job.instruction,
      ...(job.operation === 'repair' && job.base_job_id ? { base_job_id: job.base_job_id } : {}),
      ...(job.retry_of_job_id ? { retry_of_job_id: job.retry_of_job_id } : {}) };
    if (job.execution_status !== 'Completed' || !job.finished_at || !job.rtl || this.validationLabel(job) !== 'Passed'
        || job.freshness !== 'Current' || job.context_id !== submitted.contextId || job.profile_revision_id !== submitted.profileRevisionId
        || this.generation.nodes.find(item => item.node_id === job.node_id)?.latest_job_id !== job.id
        || !same(payload, submitted.payload) || !same(this.requestPayload(), submitted.payload)
        || this.preview !== submitted.preview || this.previewStale || this.preview?.context_id !== submitted.contextId
        || this.llm.profile_revision_id !== submitted.profileRevisionId || this.profileDirty()) return false;
    this.operation = 'generate'; this.baseJobId = null; this.retryOfJobId = null; this.instruction = '';
    this.preview = null; this.previewStale = true;
    return true;
  }
  // Read-only decision for the shared stage guide. Actions remain explicit user gestures.
  guidance() {
    const job = this.selectedJob(), project = this.project();
    const inspect = { label: 'Inspect saved requirements', action: () => this.inspectRequirements() };
    const progress = { label: 'View node progress', action: () => this.showNodeReadiness() };
    const checks = { label: 'View checks', action: () => this.showChecks() };
    const active = this.activeJob();
    if (this.pendingStart()) return { tone: 'warning', title: 'Reconnect to the saved generation attempt', summary: this.startRecoveryGate(), primary: { label: 'Refresh saved jobs without resending', disabled: this.reconnectingStart, action: () => this.reconnectStart() }, secondary: { label: 'Retry same request', disabled: !!this.retryStartGate(), action: () => this.retrySameStart() } };
    if (active) return { tone: 'neutral', title: 'Wait for the recorded result', summary: 'An RTL request is active. Its external-interface check and adoption decision will appear when it finishes.', primary: { label: 'View active request', action: () => this.selectNode(active.node_id) } };
    if (!this.nodeId) return { tone: 'neutral', title: 'Add a circuit node', summary: 'Local RTL is generated separately for each node.', primary: { label: 'Open Graph Editor', action: () => this.callbacks.navigate?.('graph_editor') } };
    if (this.runtimeReadOnly()) return { tone: 'neutral', title: 'Inspect preserved evidence', summary: 'This system is read-only. Saved results can be inspected here; open an editable system for new work.', primary: job ? checks : progress };
    const prerequisite = ['global_settings', 'graph_editor', 'specifications'].map(id => this.prerequisiteStages().find(stage => stage.id === id)).find(stage => stage && (stage.review_status !== 'Accepted' || stage.freshness !== 'Current'));
    if (prerequisite) {
      const label = ({ global_settings: 'Global Settings', graph_editor: 'Graph Editor', specifications: 'Specifications' })[prerequisite.id];
      return { tone: 'warning', title: `Complete ${label} first`, summary: `The current ${label} input checks must pass and be accepted before this node can proceed.`, primary: { label: `Open ${label}`, action: () => this.callbacks.navigate?.(prerequisite.id, this.nodeId) }, secondary: progress };
    }
    if (job && (job.freshness !== 'Current' || job.revision_id !== project.envelope.revision.id)) {
      const current = this.nodeJobs().find(item => item.freshness === 'Current' && item.revision_id === project.envelope.revision.id);
      return { tone: 'warning', title: 'This candidate uses an older specification', summary: 'Its saved results do not verify the current source. Select a current candidate or prepare a new request.', primary: current ? { label: 'View current node candidate', action: () => { this.selectedJobId = current.id; this.render(this.host); this.renderReview(this.reviewHost); } } : { label: 'Prepare current-source request', action: () => { this.selectedJobId = null; this.operation = 'generate'; this.baseJobId = null; this.retryOfJobId = null; this.preview = null; this.previewStale = true; this.instruction = ''; this.render(this.host); this.renderReview(this.reviewHost); } }, secondary: inspect };
    }
    const preparing = this.retryOfJobId || (this.operation === 'repair' && this.baseJobId);
    if ((preparing || !job?.rtl) && (!this.llm.profile_revision_id || this.profileDirty())) return { tone: 'warning', title: this.llm.profile_revision_id ? 'Save the edited provider settings' : 'Configure the RTL generation provider', summary: this.llm.profile_revision_id ? 'The provider has unsaved edits. Review and save them in Global Settings before preparing this model request.' : 'Save an LLM provider profile in Global Settings before previewing or generating RTL.', primary: { label: 'Open LLM provider settings', action: () => this.callbacks.navigate?.('global_settings') }, secondary: inspect };
    if (preparing) {
      if (!this.retryOfJobId && !this.instruction.trim()) return { tone: 'warning', title: 'Add the required correction', summary: 'Enter your correction in the Required correction field, then preview the repair request.', primary: { label: 'Edit required correction', action: () => {
        const input = this.host?.querySelector('#generation-instruction');
        input?.scrollIntoView?.({ behavior: 'smooth', block: 'center' }); input?.focus?.({ preventScroll: true });
      } } };
      const gate = this.generationGate();
      const previewReady = !this.previewGate();
      return { tone: 'neutral', title: this.retryOfJobId ? (previewReady ? 'Retry the saved request' : 'Preview the retry') : 'Review the repair request', summary: gate || (previewReady ? 'The inspected request is ready. Starting it sends one new request to the saved provider.' : this.retryOfJobId ? 'Preview the saved request before retrying.' : 'Review the correction and preview the exact request before sending it to the model.'), primary: { label: previewReady ? (this.retryOfJobId ? 'Retry node RTL' : 'Repair node RTL') : 'Context Preview', action: () => previewReady ? this.startGeneration() : this.previewContext(), disabled: this.requestBusy || !!gate } };
    }
    const latestId = this.nodeState()?.latest_job_id;
    if (job && latestId && latestId !== job.id) return { tone: 'neutral', title: 'You are viewing an earlier RTL request', summary: 'Use the latest node request to decide the next step. This saved request remains available for comparison.', primary: { label: 'Show latest node request', action: () => { this.selectedJobId = latestId; this.renderJobList(); this.renderResult(); this.renderReview(this.reviewHost); this.callbacks.chrome?.(); } }, secondary: checks };
    const accepted = job?.review_status === 'Accepted' && job.execution_status === 'Completed' && this.validationLabel(job) === 'Passed' && this.nodeState()?.latest_job_id === job.id &&
      (!Object.hasOwn(this.nodeState(), 'accepted_job_id') || this.nodeState().accepted_job_id === job.id);
    if (accepted) {
      const next = this.nextUnfinishedNode();
      const synthesis = { label: 'Continue this node to S05', action: () => this.callbacks.navigate?.('local_synthesis', this.nodeId), disabled: project.dirty || !!project.conflict };
      return { tone: 'success', title: 'This node’s RTL is accepted for synthesis', summary: next ? 'The S04 external-interface check passed. Generate the remaining node RTL, or continue this accepted node to S05. Circuit behavior is checked in S06.' : 'All node RTL is accepted in S04. Continue to S05 synthesis; circuit behavior is checked on the synthesized netlist in S06.', primary: next ? { label: `Next unfinished node: ${next.name}`, action: () => this.selectNode(next.id) } : synthesis, ...(next ? { secondary: synthesis } : {}) };
    }
    if (job?.rtl && job.checks?.interface?.validation_status === 'Failed') return { tone: 'warning', title: 'Correct the external interface', summary: 'The generated module or its external ports do not match the saved interface. Review the diagnostic, then prepare a correction using the same source specification.', primary: { label: 'View failed checks', action: () => this.showChecks() }, secondary: { label: 'Prepare repair context', action: () => this.prepareRepair(job, this.feedback.get(job.id) || (job.checks.interface.diagnostics || []).map(item => `${item.code || 'Check'}: ${item.message || ''}`).join('\n')), disabled: this.requestBusy } };
    if (job?.rtl && this.validationLabel(job) !== 'Passed') {
      return { tone: 'warning', title: 'Inspect the generation result', summary: 'S04 needs a complete RTL candidate with a matching external interface. Inspect the saved result before preparing a corrected request.', primary: checks, secondary: inspect };
    }
    if (job?.rtl && this.validationLabel(job) === 'Passed') return { tone: 'neutral', title: 'Review the RTL for synthesis', summary: job.review_status === 'Changes Requested' ? 'A changes request is recorded. Review that feedback before preparing a repair.' : 'The S04 external-interface check passed. Accept this RTL to continue to S05; behavioral verification belongs to S06.', primary: { label: 'Open candidate review', action: () => this.reviewHost?.scrollIntoView?.({ behavior: 'smooth', block: 'start' }) }, secondary: checks };
    if (job && RECOVERABLE.has(job.execution_status)) return { tone: 'warning', title: 'Recover the unsuccessful request', summary: this.recoveryAdvice(job), primary: { label: 'Open request recovery', action: () => this.host?.querySelector('[data-testid="generation-recovery"]')?.scrollIntoView?.({ behavior: 'smooth', block: 'center' }) }, secondary: inspect };
    const gate = this.generationGate(), ready = !this.previewGate();
    return { tone: 'neutral', title: ready ? 'Generate this node’s RTL' : 'Preview the scoped generation request', summary: gate || (ready ? 'The exact context has been inspected. Generate a candidate and check its external interface. Synthesis and circuit behavior are checked in S05 and S06.' : 'Inspect the saved node, connected edges and exact model request before generating RTL.'), primary: { label: ready ? 'Generate node RTL' : 'Context Preview', action: () => ready ? this.startGeneration() : this.previewContext(), disabled: this.requestBusy || !!gate }, secondary: inspect };
  }
  renderReadiness() {
    const host = this.host?.querySelector('#generation-readiness');
    if (!host) return;
    host.replaceChildren(badge('S04 · RTL & external interface'),
      el('p', { text: 'Check the generated module name and external port names, directions and widths. S05 runs synthesis; S06 verifies the synthesized circuit behavior.' }));
  }
  prerequisiteStages() {
    return this.project().envelope.workflow.filter(stage => ['global_settings', 'graph_editor', 'specifications'].includes(stage.id));
  }

  generationGate(checkRequest = true) {
    if (this.callbacks.batch?.()?.activeBatch()) return 'A sequential generation batch is active. Inspect or cancel it before another request.';
    const project = this.project();
    if (this.runtimeReadOnly()) return 'This preserved snapshot is read-only. Open an editable system to generate RTL.';
    if (this.providerRequestGate()) return this.providerRequestGate();
    if (project.busy) return 'Wait for the current project operation to finish.';
    if (!this.generation.implemented) return 'Generation service is not available. Start the M2-A local service.';
    if (this.generation.storage_error) return `Generation history storage error: ${this.generation.storage_error.message || this.generation.storage_error.code}. Resolve storage before starting another request.`;
    if (project.conflict) return 'The saved design changed in another window. Export your draft, then Open saved before requesting more generation.';
    if (project.dirty) return 'Save the edited design before previewing or generating from its input snapshot.';
    if (project.postlayoutRunning) return 'A post-layout tool run is active. Inspect or cancel it before starting another operation.';
    if (project.envelope.repair_analysis?.active_job_id) return 'Repair guidance analysis is active. Inspect or cancel it before starting RTL generation.';
    if (project.lvsRunning) return 'An LVS tool run is active. Inspect or cancel it before requesting generation.';
    if (!this.llm.profile_revision_id) return 'Save a provider profile in Global Settings first.';
    if (this.profileDirty()) return 'Save the edited provider profile before making a request.';
    if (!this.nodeId) return 'Add a node in the Graph Editor first.';
    const missing = this.prerequisiteStages().filter(stage => stage.review_status !== 'Accepted' || stage.freshness !== 'Current');
    if (missing.length) return `Review and accept current input checks first: ${missing.map(stage => stage.label).join(', ')}.`;
    if (this.activeJob()) {
      const active = this.activeJob();
      const node = project.design.nodes.find(item => item.id === active.node_id);
      return active.execution_status === 'Completed' ? `Candidate checks are still in progress for ${node?.name || active.node_id}. Wait for the complete recorded result.` : `A generation job is ${active.execution_status.toLowerCase()} for ${node?.name || active.node_id}. Open that node in Node progress to inspect or cancel it.`;
    }
    if (checkRequest && this.operation === 'repair' && !this.baseJobId) return 'Select an earlier RTL candidate to repair.';
    if (checkRequest && this.operation === 'repair' && !this.instruction.trim()) return 'Describe the required correction before previewing a repair.';
    if (checkRequest && this.retryOfJobId) {
      const parent = this.generation.jobs.find(job => job.id === this.retryOfJobId);
      if (!parent || !RECOVERABLE.has(parent.execution_status) || parent.freshness !== 'Current' || parent.revision_id !== project.envelope.revision.id || parent.node_id !== this.nodeId)
        return 'The retry source changed. Start a new request from the current saved design.';
      if (parent.operation !== this.operation || (parent.base_job_id || null) !== (this.baseJobId || null) || parent.instruction !== this.instruction)
        return 'The retry request changed. Start a new request before changing its operation or instructions.';
    }
    return '';
  }

  verificationGate(job) {
    if (this.startRecoveryGate()) return this.startRecoveryGate();
    const project = this.project();
    if (this.runtimeReadOnly()) return 'This preserved snapshot is read-only. Open an editable system to verify saved RTL.';
    if (this.requestBusy || project.busy) return 'Wait for the current project operation to finish.';
    if (!this.generation.implemented) return 'The local verification service is unavailable. Start the project service.';
    if (this.generation.storage_error) return `Resolve the generation history storage error first: ${this.generation.storage_error.message || this.generation.storage_error.code}.`;
    if (project.conflict) return 'The saved design changed in another window. Reopen the saved system before verification.';
    if (project.dirty) return 'Save the edited design before verifying its RTL.';
    if (project.postlayoutRunning || project.lvsRunning) return 'Wait for the active tool run to finish.';
    if (this.activeJob() || this.callbacks.batch?.()?.activeBatch()) return 'Wait for the current generation or verification job to finish.';
    if (!job?.rtl) return 'Generate a complete RTL candidate before running verification.';
    if (job.freshness !== 'Current' || job.revision_id !== project.envelope.revision.id) return 'This RTL belongs to an older source snapshot. Select a candidate for the current saved specification.';
    const missing = this.prerequisiteStages().filter(stage => stage.review_status !== 'Accepted' || stage.freshness !== 'Current');
    if (missing.length) return `Complete the current input checks first: ${missing.map(stage => stage.label).join(', ')}.`;
    if (job.saved_rtl_verification?.available !== true) return this.verificationReadiness(job)?.message || job.saved_rtl_verification?.message || 'Behavioral verification is not implemented for this node specification. A specification-based verification adapter must be added before this node can proceed.';
    return '';
  }

  async verifySavedRTL(job) {
    if (this.verificationGate(job)) return;
    const identity = this.requestIdentity(), token = ++this.requestToken;
    this.requestBusy = true; this.refreshStatus();
    try {
      const response = await this.callbacks.request('generation/verify', { job_id: job.id, revision_id: this.project().envelope.revision.id });
      if (identity !== this.requestIdentity() || token !== this.requestToken) return;
      this.selectedJobId = response.generation.latest_job_id;
      this.artifactTab = 'checks'; this.pollFailure = null;
      this.callbacks.envelope(response);
      this.callbacks.toast('Saved RTL verification started. The RTL is unchanged; no model request was sent.');
    } catch (error) { if (identity === this.requestIdentity() && token === this.requestToken) this.callbacks.notify(error.message, 'error'); }
    finally { if (token === this.requestToken) { this.requestBusy = false; if (identity === this.requestIdentity()) { this.refreshStatus(); this.schedulePoll(); } } }
  }

  prepareRepair(job, instruction = '') {
    if (!job?.rtl || inProgress(job) || this.requestBusy || this.runtimeReadOnly()) return;
    // An explicit single-node repair replaces only an unsent batch preview.
    if (this.callbacks.batch?.()?.discardPreview?.() === false) {
      this.callbacks.toast('Wait for the active batch, or reconnect to its saved result before preparing another request.');
      return false;
    }
    this.retryOfJobId = null; this.operation = 'repair'; this.baseJobId = job.id;
    this.instruction = instruction; this.preview = null; this.previewStale = true;
    this.render(this.host); this.renderReview(this.reviewHost);
    this.callbacks.toast('Repair prepared. Review the correction and Context Preview before requesting revised RTL.');
  }

  renderVerification(job) {
    if (!job.rtl) return null;
    return el('section', { class: 'generation-recovery', 'data-testid': 'generation-stage-scope' },
      el('h3', { text: 'S04 external-interface check' }),
      el('p', { text: 'S04 checks the generated RTL external interface. After acceptance, S05 checks whether it can be synthesized. S06 simulates the synthesized netlist against the saved specification and original verification inputs.' }),
      el('p', { class: 'scope-note', text: 'Earlier syntax and behavioral reports remain in Checks and Events & record as historical evidence. They do not add a behavioral requirement to S04.' }));
  }

  refreshVerificationActions() {
    // S04 exposes no circuit-behavior execution control; use S06 after synthesis.
  }

  previewGate() {
    const gate = this.generationGate();
    if (gate) return gate;
    if (!this.preview || this.previewStale) return 'Preview the exact context and prompt before starting this request.';
    if (this.preview.profile_revision_id !== this.llm.profile_revision_id) return 'The provider profile changed. Preview this request again.';
    const estimated = inputEstimate(this.preview);
    if (typeof estimated === 'number' && estimated + this.llm.profile.max_output_tokens > this.llm.profile.context_window) return 'Estimated input plus the output limit exceeds the configured context window. Adjust the profile or input; nothing is silently truncated.';
    return '';
  }

  connectionLabel() {
    const probe = this.llm.probe;
    if (!this.llm.profile_revision_id) return 'Not configured';
    if (!probe) return 'Not tested';
    if (probe.profile_revision_id && probe.profile_revision_id !== this.llm.profile_revision_id) return 'Profile changed · not tested';
    return probe.status || (probe.connected === true ? 'Connected' : 'Not connected');
  }

  renderProvider(host) {
    this.providerHost = host;
    const runtimeMount = ++this.runtimeMount;
    if (this.runtimeTimer) clearTimeout(this.runtimeTimer);
    this.runtimeTimer = null;
    this.runtimeStatus = null;
    this.runtimeCheckedAt = null;
    this.runtimeError = null;
    this.runtimeBusy = false;
    const edit = (key, value) => {
      this.profileDraft[key] = value;
      this.previewStale = true;
      this.refreshProviderActions(); this.refreshGenerationActions(); this.callbacks.chrome?.();
    };
    const form = el('div', { class: 'form-grid provider-form' },
      field('Profile name', this.profileDraft.name, value => edit('name', value), { id: 'provider-name', 'data-testid': 'provider-name' }),
      field('API type', this.profileDraft.api_type, value => edit('api_type', value), { id: 'provider-api-type', choices: [['chat_completions', 'Compatible Chat Completions']], 'data-testid': 'provider-api-type' }),
      field('Execution location', this.profileDraft.execution_location, value => edit('execution_location', value), { id: 'provider-location', choices: ['Local', 'Network'], 'data-testid': 'provider-location' }),
      field('Endpoint base URL', this.profileDraft.base_url, value => edit('base_url', value), { id: 'provider-base-url', type: 'url', spellcheck: false, 'data-testid': 'provider-base-url', hint: 'The service appends /models and /chat/completions. No automatic fallback.' }),
      field('Model', this.profileDraft.model, value => edit('model', value), { id: 'provider-model', spellcheck: false, 'data-testid': 'provider-model' }),
      field('Thinking control', this.profileDraft.reasoning_effort ?? '', value => edit('reasoning_effort', value || null), { id: 'provider-thinking-control', choices: [['', 'Provider default'], ['none', 'Disable thinking']], 'data-testid': 'provider-thinking-control', hint: 'Model-dependent API option. Support is verified for the configured Ollama/Qwen setup only.' }),
      field('Credential environment variable', this.profileDraft.credential_env, value => edit('credential_env', value), { id: 'provider-credential-env', spellcheck: false, placeholder: 'HULLCIRQ_API_KEY', 'data-testid': 'provider-credential-env', hint: 'Variable name only. Its secret value stays in the service environment.' }),
      field('Timeout (seconds)', this.profileDraft.timeout_seconds, value => edit('timeout_seconds', Number(value)), { id: 'provider-timeout', type: 'number', step: 'any', 'data-testid': 'provider-timeout' }),
      field('Context window (token budget)', this.profileDraft.context_window, value => edit('context_window', Number(value)), { id: 'provider-context-window', type: 'number', step: '1', 'data-testid': 'provider-context-window' }),
      field('Output limit (tokens)', this.profileDraft.max_output_tokens, value => edit('max_output_tokens', Number(value)), { id: 'provider-max-output', type: 'number', step: '1', 'data-testid': 'provider-max-output' }),
      field('Temperature', this.profileDraft.temperature, value => edit('temperature', Number(value)), { id: 'provider-temperature', type: 'number', step: 'any', 'data-testid': 'provider-temperature' }),
      field('Seed', this.profileDraft.seed, value => edit('seed', Number(value)), { id: 'provider-seed', type: 'number', step: '1', 'data-testid': 'provider-seed' }));
    const actions = el('div', { class: 'provider-actions' },
      el('button', { type: 'button', class: 'primary', text: 'Save provider profile', 'data-testid': 'provider-save', onclick: () => this.saveProfile() }),
      el('button', { type: 'button', text: 'Test Connection', 'data-testid': 'provider-test', onclick: () => this.probe() }),
      el('span', { id: 'provider-draft-status', class: 'generation-connection-label' }));
    const metadata = el('details', { class: 'generation-preview' }, el('summary', { text: 'Recorded model & runtime details' }),
      el('div', { class: 'form-grid provider-form' },
        ...['model_revision', 'quantization', 'runtime_version'].map(key => field({ model_revision: 'Model revision', quantization: 'Quantization', runtime_version: 'Runtime version' }[key], this.profileDraft[key], value => edit(key, value), { id: `provider-${key}`, hint: 'Keep unknown when it has not been independently checked.' }))));
    const runtime = this.runtimeIdentity() && !this.runtimeReadOnly() ? el('section', { class: 'provider-status', 'data-testid': 'local-runtime-panel' },
      el('h3', { text: 'Local LLM server' }),
      el('p', { text: 'GUI startup supports the qwen3:8b and qwen2.5-coder:7b model names in the saved profile; this does not establish that either model is installed. No model is downloaded. Test Connection checks the selected provider’s actual model list. The saved context window is used unless an explicit server environment override exists.' }),
      el('div', { class: 'provider-actions' },
        el('button', { type: 'button', text: 'Start local LLM', 'data-testid': 'local-runtime-start', onclick: () => this.requestRuntime('start') }),
        el('button', { type: 'button', text: 'Refresh server status', 'data-testid': 'local-runtime-refresh', onclick: () => this.requestRuntime() }),
        el('button', { type: 'button', text: 'Stop local LLM', 'data-testid': 'local-runtime-stop', onclick: () => this.requestRuntime('stop') })),
      el('div', { 'data-testid': 'local-runtime-status' }),
      el('p', { class: 'gate-reason', 'data-testid': 'local-runtime-gate' })) : null;
    host.replaceChildren(card('LLM provider', 'Select an API profile independently of node or global RTL generation. Connection testing does not generate RTL.', [form, actions, runtime, metadata, el('div', { class: 'provider-status', id: 'provider-connection-result' })], 'provider-settings'));
    this.refreshProviderActions(); this.renderConnectionResult();
    if (runtime && this.runtimeMount === runtimeMount) this.requestRuntime();
  }

  runtimeIdentity() {
    const identity = this.project().envelope?.workspace_identity;
    return identity ? `${identity.session_id}:${identity.project_id}:${identity.system_id}` : null;
  }

  runtimeReadOnly() { return this.project().envelope?.workspace_identity?.read_only === true; }

  runtimeStartGate() {
    if (!this.runtimeIdentity()) return 'Local server controls are available in the project workspace.';
    if (this.runtimeReadOnly()) return 'This preserved snapshot is read-only. Open an editable system to control the local server.';
    if (this.profileBusy) return 'Wait for the current provider request to finish.';
    if (!this.llm.profile_revision_id || this.profileDirty()) return 'Save the provider profile before starting its local server.';
    const profile = this.llm.profile;
    let supportedEndpoint = false;
    try {
      const endpoint = new URL(profile?.base_url);
      supportedEndpoint = endpoint.protocol === 'http:' && ['127.0.0.1', 'localhost'].includes(endpoint.hostname) && endpoint.port === '11435' && endpoint.pathname.replace(/\/+$/, '') === '/v1' && !endpoint.username && !endpoint.password && !endpoint.search && !endpoint.hash;
    } catch { /* Invalid or remote endpoints cannot select a local process. */ }
    if (profile?.execution_location !== 'Local' || profile?.api_type !== 'chat_completions' || !supportedEndpoint || !PREPARED_RUNTIME_MODELS.has(profile?.model))
      return 'GUI startup supports Local qwen3:8b or qwen2.5-coder:7b at http://127.0.0.1:11435/v1 (or localhost). These supported names do not guarantee installation; Test Connection checks model availability. Other API profiles remain available for connection testing and generation.';
    return '';
  }

  runtimeCurrent(identity, mount, host) {
    return this.runtimeIdentity() === identity && this.runtimeMount === mount && this.providerHost === host && host?.isConnected;
  }

  renderRuntimeStatus() {
    const panel = this.providerHost?.querySelector('[data-testid="local-runtime-panel"]');
    if (!panel || !this.providerHost?.isConnected) return;
    const status = this.runtimeStatus;
    const gate = this.runtimeStartGate();
    const start = panel.querySelector('[data-testid="local-runtime-start"]');
    const refresh = panel.querySelector('[data-testid="local-runtime-refresh"]');
    const stop = panel.querySelector('[data-testid="local-runtime-stop"]');
    start.disabled = this.runtimeBusy || !!gate || status?.can_start !== true;
    start.title = gate || (status?.can_start ? 'Start the prepared local service; no inference request.' : 'Refresh the server status before starting.');
    refresh.disabled = this.runtimeBusy;
    stop.disabled = this.runtimeBusy || this.runtimeReadOnly() || status?.owned !== true || status?.can_stop !== true;
    stop.title = this.runtimeReadOnly() ? 'Preserved read-only snapshot. Duplicate the design to start new work.' : status?.owned === false && status?.state === 'Running' ? 'This server was started outside HuLLCirq. Stop it from its original launcher.' : status?.can_stop !== true ? 'No running local server is owned by this HuLLCirq service.' : 'Stop only the local server process started by this HuLLCirq service.';
    panel.querySelector('[data-testid="local-runtime-gate"]').textContent = gate;
    const state = status?.state || (this.runtimeBusy ? 'Checking' : 'Not checked');
    const content = panel.querySelector('[data-testid="local-runtime-status"]');
    content.replaceChildren(el('div', { class: 'provider-identity' }, badge(state, state === 'Running' ? 'teal' : ['Failed', 'Unavailable'].includes(state) ? 'orange' : 'neutral'),
      el('code', { text: status?.endpoint || PROFILE_DEFAULTS.base_url }), el('code', { text: status?.model || PROFILE_DEFAULTS.model })),
      el('p', { text: status?.owned === true ? `Managed by this HuLLCirq service${status.pid ? ` · PID ${status.pid}` : ''}.` : status?.state === 'Running' ? 'Already running outside HuLLCirq. Its process will not be stopped by these controls.' : 'No server process is owned by this HuLLCirq service.' }));
    if (this.runtimeBusy) content.append(el('p', { text: 'Updating local server status…' }));
    if (status?.message) content.append(el('p', { text: status.message }));
    if (status?.owned && status.managed_environment?.OLLAMA_CONTEXT_LENGTH) {
      const source = ({ saved_provider_profile: 'Saved provider profile', parent_environment: 'Server environment override', default: 'Default' })[status.context_length_source] || 'Recorded launch setting';
      content.append(el('p', { 'data-testid': 'local-runtime-context', text: `Launch context: ${tokens(Number(status.managed_environment.OLLAMA_CONTEXT_LENGTH))} tokens · ${source}. Restart the local server to apply later changes.` }));
    }
    const error = this.runtimeError || status?.error;
    if (error) content.append(el('p', { class: 'gate-reason', 'data-testid': 'local-runtime-error', text: typeof error === 'string' ? error : error.summary || error.message || JSON.stringify(error) }));
    if (status?.log_path) content.append(el('p', {}, 'Server log: ', el('code', { text: status.log_path })));
    if (state === 'Stopped') content.append(el('p', { text: 'Start local LLM here, wait for Running, then select Test Connection to check the saved profile.' }));
    else if (state === 'Running') content.append(el('p', { text: 'Select Test Connection to check model discovery for the saved profile. Running is server availability, not circuit verification.' }));
  }

  requestRuntime(action = 'status') {
    const identity = this.runtimeIdentity(), mount = this.runtimeMount, host = this.providerHost;
    if (!identity || !host?.isConnected) return Promise.resolve();
    if (this.runtimePending?.identity === identity && this.runtimePending?.mount === mount) return this.runtimePending.promise;
    if (action === 'start' && (this.runtimeStartGate() || this.runtimeStatus?.can_start !== true)) return Promise.resolve();
    if (action === 'stop' && (this.runtimeReadOnly() || this.runtimeStatus?.owned !== true || this.runtimeStatus?.can_stop !== true)) return Promise.resolve();
    if (!['status', 'start', 'stop'].includes(action)) return Promise.resolve();
    if (this.runtimeTimer) clearTimeout(this.runtimeTimer);
    this.runtimeTimer = null;
    this.runtimeBusy = true; this.runtimeError = null; this.renderRuntimeStatus();
    const pending = { identity, mount, promise: null };
    this.runtimePending = pending;
    pending.promise = (async () => {
      try {
        const result = action === 'status' ? await this.callbacks.request('workspace/local-runtime') : await this.callbacks.request(`workspace/local-runtime/${action}`, {});
        if (!this.runtimeCurrent(identity, mount, host)) return;
        if (!result?.runtime || typeof result.runtime.state !== 'string') throw new Error('The local server status response is incomplete. Refresh to try again.');
        this.runtimeStatus = result.runtime;
        this.runtimeCheckedAt = Date.now();
      } catch (error) {
        if (this.runtimeCurrent(identity, mount, host)) {
          this.runtimeError = error.summary || error.message || String(error);
          this.runtimeCheckedAt = Date.now();
        }
      } finally {
        if (this.runtimePending === pending) this.runtimePending = null;
        if (this.runtimeCurrent(identity, mount, host)) {
          this.runtimeBusy = false; this.renderRuntimeStatus(); this.renderConnectionResult();
          if (!this.runtimeError && ['Starting', 'Stopping'].includes(this.runtimeStatus?.state)) this.runtimeTimer = setTimeout(() => {
            this.runtimeTimer = null;
            if (this.runtimeCurrent(identity, mount, host)) this.requestRuntime();
          }, 1200);
        }
      }
    })();
    return pending.promise;
  }

  refreshProviderActions() {
    const host = this.providerHost;
    if (!host?.isConnected) return;
    const save = host.querySelector('[data-testid="provider-save"]');
    const test = host.querySelector('[data-testid="provider-test"]');
    save.disabled = this.profileBusy || (!this.profileDirty() && !!this.llm.profile_revision_id);
    test.disabled = this.profileBusy || this.profileDirty() || !this.llm.profile_revision_id;
    test.title = this.profileDirty() ? 'Save this profile before testing its exact version.' : 'Fetch model information; no inference request.';
    host.querySelector('#provider-draft-status').textContent = this.profileBusy ? 'Contacting local service…' : this.profileDirty() || !this.llm.profile_revision_id ? 'Unsaved provider settings' : `Saved profile ${this.llm.profile_revision_id}`;
    this.renderRuntimeStatus();
  }

  renderConnectionResult() {
    const host = this.providerHost?.querySelector('#provider-connection-result');
    if (!host) return;
    const profile = this.llm.profile;
    const probe = this.llm.probe;
    const connectionBadge = badge(this.connectionLabel(), this.connectionLabel() === 'Connected' ? 'teal' : 'neutral');
    connectionBadge.setAttribute('data-testid', 'provider-connection-badge');
    host.replaceChildren(el('div', { class: 'provider-identity' }, connectionBadge,
      el('code', { text: profile ? `${profile.base_url.replace(/\/$/, '')}/chat/completions` : 'No saved endpoint' }),
      el('code', { text: this.llm.profile_revision_id || 'No saved profile version' })),
      el('p', { text: 'Test Connection uses the /models endpoint. Connected is a transport/model-discovery result; it is not an RTL or circuit verification result.' }));
    if (probe) host.append(el('details', { class: 'raw-result' }, el('summary', { text: 'Exact connection test, model list & capabilities' }), el('pre', { text: JSON.stringify({ profile_revision_id: this.llm.profile_revision_id, probe, capabilities: this.llm.capabilities }, null, 2) })));
    else host.append(el('p', { text: 'No connection test is recorded for the saved profile.' }));
    if (this.runtimeIdentity() && !this.runtimeReadOnly() && this.runtimeStatus?.state === 'Stopped') host.append(el('p', { text: 'The local server is stopped. Use Start local LLM above, wait for Running, then try Test Connection again.' }));
    this.callbacks.connection?.(this.connectionLabel(), { runtime: this.runtimeStatus, checkedAt: this.runtimeCheckedAt, error: this.runtimeError });
  }

  async saveProfile() {
    if (this.profileBusy) return;
    const submitted = clone(this.profileDraft);
    const identity = this.requestIdentity(), token = ++this.profileRequestToken;
    this.profileBusy = true; this.refreshProviderActions();
    try {
      const response = await this.callbacks.request('llm/profile', { profile: submitted, expected_profile_revision_id: this.llm.profile_revision_id });
      if (identity !== this.requestIdentity() || token !== this.profileRequestToken) return;
      const unchanged = same(submitted, this.profileDraft);
      this.callbacks.envelope(response);
      if (unchanged) this.profileDraft = cleanProfile(response.llm.profile);
      this.callbacks.toast('Provider profile saved. Test this version before relying on connection information.');
    } catch (error) { if (identity === this.requestIdentity() && token === this.profileRequestToken) this.callbacks.notify(error.message, 'error'); }
    finally { if (token === this.profileRequestToken) { this.profileBusy = false; if (identity === this.requestIdentity()) this.refreshStatus(); } }
  }

  async probe() {
    if (this.profileBusy || this.profileDirty() || !this.llm.profile_revision_id) return;
    const identity = this.requestIdentity(), revision = this.llm.profile_revision_id, token = ++this.profileRequestToken;
    this.profileBusy = true; this.refreshStatus();
    try {
      const response = await this.callbacks.request('llm/probe', { profile_revision_id: revision });
      if (identity !== this.requestIdentity() || token !== this.profileRequestToken || revision !== this.llm.profile_revision_id) return;
      this.callbacks.envelope(response);
      this.callbacks.toast('Connection test recorded. No generation request was made.');
    } catch (error) { if (identity === this.requestIdentity() && token === this.profileRequestToken && revision === this.llm.profile_revision_id) this.callbacks.notify(error.message, 'error'); }
    finally { if (token === this.profileRequestToken) { this.profileBusy = false; if (identity === this.requestIdentity()) this.refreshStatus(); } }
  }

  render(host) {
    this.host = host;
    const project = this.project();
    if (!project.design.nodes.some(node => node.id === this.nodeId)) this.nodeId = project.design.nodes[0]?.id || null;
    const targetFields = el('div', { class: 'form-grid generation-target-form' },
      field('Target node', this.nodeId || '', value => this.selectNode(value), { id: 'generation-node', 'data-testid': 'generation-node', choices: project.design.nodes.map(node => [node.id, `${node.name} · ${node.module_name}`]) }),
      field('Operation', this.operation, value => {
        this.operation = value;
        this.retryOfJobId = null;
        if (value === 'repair' && !this.baseJobId) this.baseJobId = this.nodeJobs().find(job => job.rtl)?.id || null;
        this.previewStale = true; this.render(this.host); this.renderReview(this.reviewHost);
      }, { id: 'generation-operation', 'data-testid': 'generation-operation', choices: [['generate', 'Generate node RTL'], ['repair', 'Repair previous candidate']] }),
      this.operation === 'repair' ? field('Candidate to repair', this.baseJobId || '', value => { this.baseJobId = value || null; this.retryOfJobId = null; this.previewStale = true; this.refreshGenerationActions(); this.callbacks.chrome?.(); }, { id: 'repair-base-job', 'data-testid': 'repair-base-job', choices: this.nodeJobs().filter(job => job.rtl).map(job => [job.id, `${job.id} · ${this.validationLabel(job)}`]) }) : null,
      field(this.operation === 'repair' ? 'Required correction' : 'Additional generation instruction', this.instruction, value => { this.instruction = value; this.retryOfJobId = null; this.previewStale = true; this.refreshGenerationActions(); this.callbacks.chrome?.(); }, { id: 'generation-instruction', 'data-testid': 'generation-instruction', multiline: true, placeholder: this.operation === 'repair' ? 'Describe the mismatch and the intended correction.' : 'Optional instructions; the saved node and connected-edge requirements remain the source contract.' }));
    const calls = el('div', { class: 'generation-call-actions' },
      el('button', { type: 'button', text: 'Context Preview', 'data-testid': 'context-preview-button', onclick: () => this.previewContext() }),
      el('button', { type: 'button', class: 'primary', text: this.retryOfJobId ? 'Retry node RTL' : this.operation === 'repair' ? 'Repair node RTL' : 'Generate node RTL', 'data-testid': 'generate-node', onclick: () => this.startGeneration() }),
      this.retryOfJobId ? el('button', { type: 'button', text: 'Start new request', 'data-testid': 'start-new-generation-request', onclick: () => this.clearRetry() }) : null);
    const source = el('div', { class: 'provider-status', id: 'generation-source' });
    const inputs = el('div', { class: 'generation-inputs' },
      card('Scoped generation request', 'Only this node, its incident edges, required adjacent interfaces, and shared constraints enter the context.', [targetFields, el('div', { class: 'scope-note', id: 'generation-readiness', 'data-testid': 'generation-readiness' }), calls, el('p', { class: 'generation-gate', id: 'generation-gate' }), source]),
      card('Context Preview', 'Inspect the exact prompt and profile version before submitting a request.', el('div', { class: 'generation-preview', id: 'generation-context-content' })),
      card('Node progress', 'S04 acceptance covers the external interface of each generated RTL candidate. S05 and S06 have their own synthesis and circuit results.', el('div', { class: 'generation-node-progress', id: 'generation-node-progress', tabindex: '-1' })));
    const results = el('div', { class: 'generation-results' }, card('Generation evidence', 'Actual server events, raw answer, candidate RTL, and checks remain tied to the source snapshot.', el('div', { id: 'generation-result-content' })),
      card('Saved generation jobs', 'Reconnect to these records without automatically resending a request.', el('div', { class: 'generation-job-list', id: 'generation-job-list' }), 'generation-history-card'));
    const batchHost = el('div', { 'data-testid': 'generation-batch-workspace' });
    host.replaceChildren(batchHost, el('div', { class: 'generation-workspace' }, inputs, results));
    this.callbacks.batch?.()?.renderGeneration(batchHost);
    this.refreshGenerationActions(); this.renderPreview(); this.renderProgress(); this.renderJobList(); this.renderResult();
  }

  selectNode(id) {
    this.nodeId = id;
    this.selectedJobId = this.nodeState()?.latest_job_id || this.nodeJobs()[0]?.id || null;
    this.baseJobId = null;
    this.retryOfJobId = null;
    this.instruction = '';
    this.preview = null; this.previewStale = true;
    this.render(this.host); this.renderReview(this.reviewHost);
  }

  refreshGenerationActions() {
    if (!this.host?.isConnected || this.project().stage !== 'local_rtl_generation') return;
    const gate = this.generationGate();
    const previewGate = this.previewGate();
    const preview = this.host.querySelector('[data-testid="context-preview-button"]');
    const generate = this.host.querySelector('[data-testid="generate-node"]');
    if (!preview || !generate) return;
    preview.disabled = this.requestBusy || !!gate;
    preview.title = gate || 'Build a scoped request preview without calling the model.';
    generate.disabled = this.requestBusy || !!previewGate;
    generate.textContent = this.retryOfJobId ? 'Retry node RTL' : this.operation === 'repair' ? 'Repair node RTL' : 'Generate node RTL';
    const newRequest = this.host.querySelector('[data-testid="start-new-generation-request"]');
    if (newRequest) newRequest.hidden = !this.retryOfJobId;
    generate.title = previewGate || 'Send the inspected request to the saved provider profile.';
    this.host.querySelector('#generation-gate').textContent = this.requestBusy ? 'Working with the local service…' : gate || previewGate || (this.retryOfJobId ? `Ready to retry ${this.retryOfJobId} as a new saved job. Completion still requires candidate checks.` : 'Ready to submit the inspected request. Completion will still require your review.');
    const profile = this.llm.profile;
    const identity = this.host.querySelector('#generation-source');
    identity.replaceChildren(el('div', { class: 'provider-identity' }, badge(profile?.execution_location || 'Not configured'), el('code', { text: profile?.model || 'No model' }), el('code', { text: this.llm.profile_revision_id || 'No profile version' })),
      el('p', { text: `Source revision ${this.project().envelope.revision.id}` }),
      el('p', { text: profile ? `${profile.base_url.replace(/\/$/, '')}/chat/completions` : 'Save the provider profile in Global Settings.' }));
    if (profile?.execution_location === 'Network') identity.append(el('p', { class: 'generation-network-notice', text: 'This configured endpoint is on the network. The inspected context is sent there when you explicitly start generation; no local-to-network fallback occurs.' }));
    this.renderReadiness();
    this.refreshRecoveryActions();
    this.refreshVerificationActions();
  }

  recoveryDraft(job) {
    if (!this.recoveryDrafts.has(job.id)) {
      this.recoveryDrafts.set(job.id, {
        max_output_tokens: this.llm.profile?.max_output_tokens ?? PROFILE_DEFAULTS.max_output_tokens,
        reasoning_effort: this.llm.profile?.reasoning_effort ?? null,
        timeout_seconds: this.llm.profile?.timeout_seconds ?? PROFILE_DEFAULTS.timeout_seconds,
      });
    }
    return this.recoveryDrafts.get(job.id);
  }

  recoverySettingsDirty(job) {
    const draft = this.recoveryDraft(job), profile = this.llm.profile;
    return draft.max_output_tokens !== profile?.max_output_tokens || draft.reasoning_effort !== (profile?.reasoning_effort ?? null) || draft.timeout_seconds !== profile?.timeout_seconds;
  }

  recoveryBudget(job) {
    let estimate = jobInputEstimate(job);
    if (!validEstimate(estimate) && this.retryOfJobId === job.id && !this.previewStale && this.preview?.profile_revision_id === this.llm.profile_revision_id)
      estimate = inputEstimate(this.preview);
    const contextWindow = this.llm.profile?.context_window;
    const known = validEstimate(estimate);
    const configuredCap = Number.isInteger(contextWindow) && contextWindow > 1 ? Math.min(65536, contextWindow - 1) : null;
    const maxOutput = configuredCap === null ? null : known ? Math.max(0, Math.min(configuredCap, Math.floor(contextWindow - estimate))) : null;
    return { estimate: known ? estimate : null, contextWindow, configuredCap, maxOutput };
  }

  recoveryRecommendation(job) {
    if ((job.error?.category || job.error?.code) !== 'output_truncated') return null;
    const budget = this.recoveryBudget(job), profile = this.llm.profile;
    if (budget.maxOutput === null || budget.maxOutput < 1 || !profile) return null;
    const priorLimit = job.parameters?.max_tokens ?? job.profile?.max_output_tokens;
    const changes = {};
    const larger = Math.min(budget.maxOutput, Math.max(4096, profile.max_output_tokens * 2, Number.isInteger(priorLimit) ? priorLimit * 2 : 0));
    if (larger > profile.max_output_tokens && (!Number.isInteger(priorLimit) || larger > priorLimit)) changes.max_output_tokens = larger;
    if (!job.raw_content && job.raw_reasoning && profile.reasoning_effort !== 'none') changes.reasoning_effort = 'none';
    return Object.keys(changes).length ? changes : null;
  }

  recoveryAdvice(job) {
    const category = job.error?.category || job.error?.code;
    if (category === 'connection_error') return 'The provider connection failed. No RTL candidate was produced. Check the saved LLM endpoint, then preview an explicit retry; changing the output limit alone does not fix a connection failure.';
    if (category === 'stream_incomplete') return 'No normal finish received. Retry with the same settings.';
    if (category === 'timeout') return `The request timed out after ${tokens(job.profile?.timeout_seconds)} s. Inspect the partial answer; increase timeout only if it was still making progress.`;
    if (category === 'output_truncated') {
      const suggestion = this.recoveryRecommendation(job);
      if (suggestion?.max_output_tokens) return `Output limit reached. Try ${tokens(suggestion.max_output_tokens)} output tokens${suggestion.reasoning_effort === 'none' ? ' with thinking disabled' : ''}, then save and prepare the retry.`;
      if (suggestion?.reasoning_effort === 'none') return 'Output limit reached while returning reasoning. Try disabling thinking; the output budget cannot be raised further.';
      return this.recoveryBudget(job).maxOutput === null ? 'Output limit reached. Prepare a retry and preview the input budget before changing the output limit.' : 'Output limit reached. No larger output limit fits this request; start a new request with a shorter scope or instructions.';
    }
    return 'The request did not complete. Inspect its error, then prepare a retry with the saved settings.';
  }

  applyRecoveryRecommendation(job) {
    if (this.recoveryGate(job, true)) return;
    const suggestion = this.recoveryRecommendation(job);
    if (!suggestion) return;
    Object.assign(this.recoveryDraft(job), suggestion);
    this.renderResult();
  }

  recoveryGate(job, settings = false) {
    if (job?.operation === 'verify') return 'This is a saved RTL verification. Run its checks again or prepare a repair; it is not a model request to retry.';
    if (this.requestBusy) return 'Wait for the current generation request to finish.';
    const gate = this.generationGate(false);
    if (gate) return gate;
    if (!job || !RECOVERABLE.has(job.execution_status)) return 'Select a failed, cancelled or interrupted request to retry.';
    if (job.freshness !== 'Current' || job.node_id !== this.nodeId || job.revision_id !== this.project().envelope.revision.id)
      return 'This job belongs to an older source snapshot. Start a new request from the current saved design.';
    if (this.nodeState()?.latest_job_id && this.nodeState().latest_job_id !== job.id)
      return 'A newer request exists for this node. Open its result before preparing another retry.';
    const draft = this.recoveryDraft(job);
    if (!Number.isInteger(draft.max_output_tokens) || draft.max_output_tokens < 1 || draft.max_output_tokens > 65536)
      return 'Output limit must be an integer from 1 to 65,536.';
    if (![null, 'none'].includes(draft.reasoning_effort)) return 'Choose Provider default or Disable thinking.';
    if (!Number.isFinite(draft.timeout_seconds) || draft.timeout_seconds < 0.05 || draft.timeout_seconds > 3600)
      return 'Timeout must be a finite number from 0.05 to 3,600 seconds.';
    const budget = this.recoveryBudget(job);
    if (budget.configuredCap === null) return 'Save a valid context window in Global Settings first.';
    if (budget.maxOutput === 0) return 'No output budget remains. Start a new request with a shorter scope or instructions.';
    const cap = budget.maxOutput ?? budget.configuredCap;
    if (draft.max_output_tokens > cap)
      return `Output limit must be 1–${tokens(cap)} tokens for this request; the proposed limit exceeds the saved context window.`;
    if (settings && this.recoverySettingsDirty(job) && budget.maxOutput === null)
      return 'Input budget unknown. Prepare a retry with saved settings, then use Context Preview before editing these settings.';
    if (!settings && this.recoverySettingsDirty(job)) return 'Save recovery settings before preparing this retry.';
    return '';
  }

  refreshRecoveryActions() {
    const panel = this.host?.querySelector('[data-testid="generation-recovery"]');
    const job = this.selectedJob();
    if (!panel || !job) return;
    const settingsGate = this.recoveryGate(job, true), retryGate = this.recoveryGate(job);
    panel.querySelector('[data-testid="save-recovery-settings"]').disabled = !!settingsGate || !this.recoverySettingsDirty(job);
    panel.querySelector('[data-testid="reset-recovery-settings"]').disabled = !this.recoverySettingsDirty(job) || this.profileBusy || this.requestBusy || this.runtimeReadOnly();
    const prepare = panel.querySelector('[data-testid="prepare-retry"]');
    prepare.disabled = !!retryGate;
    prepare.textContent = this.recoverySettingsDirty(job) ? 'Prepare retry after saving' : 'Prepare retry with saved settings';
    const retryPrepared = this.retryOfJobId === job.id;
    const nextAction = retryPrepared ? (!this.previewGate() ? 'Next: Retry node RTL.' : 'Next: Context Preview.') : 'Next: Prepare retry with saved settings.';
    panel.querySelector('[data-testid="recovery-gate"]').textContent = settingsGate || retryGate || nextAction;
    const budget = this.recoveryBudget(job);
    panel.querySelector('[data-testid="recovery-budget"]').textContent = `Context ${tokens(budget.contextWindow)} · input estimate ${tokens(budget.estimate)} · max output ${tokens(budget.maxOutput)} tokens.`;
    const output = panel.querySelector('[data-testid="recovery-max-output"]');
    output.max = budget.maxOutput ?? budget.configuredCap ?? 65536;
    const hint = panel.querySelector('#recovery-max-output-hint');
    if (hint) hint.textContent = budget.maxOutput === null ? `Configured ceiling: ${tokens(budget.configuredCap)}; request budget unknown. Prepare retry → Context Preview.` : budget.maxOutput ? `Allowed: 1–${tokens(budget.maxOutput)} tokens for this request.` : 'No output budget remains; shorten the request.';
    const recommendation = panel.querySelector('[data-testid="apply-recovery-suggestion"]');
    if (recommendation) recommendation.disabled = !!settingsGate;
    for (const id of ['recovery-max-output', 'recovery-thinking-control', 'recovery-timeout']) panel.querySelector(`[data-testid="${id}"]`).disabled = this.profileBusy || this.requestBusy || this.runtimeReadOnly();
  }

  async saveRecoverySettings(job) {
    if (this.recoveryGate(job, true) || !this.recoverySettingsDirty(job)) return;
    const draft = clone(this.recoveryDraft(job));
    const submitted = { ...clone(this.llm.profile), ...draft };
    const identity = this.requestIdentity(), token = ++this.profileRequestToken;
    const originalDraft = clone(this.profileDraft);
    const revision = this.llm.profile_revision_id;
    this.profileBusy = true; this.refreshGenerationActions(); this.refreshProviderActions();
    try {
      const response = await this.callbacks.request('llm/profile', { profile: submitted, expected_profile_revision_id: revision });
      if (identity !== this.requestIdentity() || token !== this.profileRequestToken || this.llm.profile_revision_id !== revision) return;
      const draftUnchanged = same(originalDraft, this.profileDraft);
      this.callbacks.envelope(response);
      if (draftUnchanged) this.profileDraft = cleanProfile(response.llm.profile);
      this.preview = null; this.previewStale = true;
      this.callbacks.toast('Recovery settings saved as a new provider profile. The failed job is preserved. No generation was started.');
    } catch (error) { if (identity === this.requestIdentity() && token === this.profileRequestToken) this.callbacks.notify(error.message, 'error'); }
    finally { if (token === this.profileRequestToken) { this.profileBusy = false; if (identity === this.requestIdentity()) this.refreshStatus(); } }
  }

  prepareRetry(job) {
    if (this.recoveryGate(job)) return;
    this.operation = job.operation; this.baseJobId = job.base_job_id || null;
    this.instruction = job.instruction; this.retryOfJobId = job.id;
    this.preview = null; this.previewStale = true;
    this.render(this.host); this.renderReview(this.reviewHost);
    this.callbacks.toast('Retry prepared from the original saved request. Preview it, then explicitly start a new job.');
  }

  clearRetry() {
    this.retryOfJobId = null; this.preview = null; this.previewStale = true;
    this.render(this.host);
  }

  renderRecovery(job) {
    if (job.operation === 'verify' || !RECOVERABLE.has(job.execution_status)) return null;
    const draft = this.recoveryDraft(job);
    const edit = (key, value) => { draft[key] = value; this.refreshRecoveryActions(); };
    const completion = job.usage?.completion_tokens;
    const limit = job.parameters?.max_tokens ?? job.profile?.max_output_tokens;
    const timeout = (job.error?.category || job.error?.code) === 'timeout';
    const budget = this.recoveryBudget(job), suggestion = this.recoveryRecommendation(job);
    const suggestedText = suggestion ? [suggestion.max_output_tokens ? `${tokens(suggestion.max_output_tokens)} output tokens` : null, suggestion.reasoning_effort === 'none' ? 'thinking off' : null].filter(Boolean).join(' + ') : '';
    return el('section', { class: 'generation-recovery', 'data-testid': 'generation-recovery' },
      el('h3', { text: 'Recover this request' }),
      el('p', { 'data-testid': 'recovery-advice', text: this.recoveryAdvice(job) }),
      el('p', { 'data-testid': 'recovery-budget' }),
      el('small', { text: 'HuLLCirq request budget, based on the conservative input estimate; provider/model maximum is not verified.' }),
      suggestion ? el('button', { type: 'button', text: `Use ${suggestedText}`, 'data-testid': 'apply-recovery-suggestion', onclick: () => this.applyRecoveryRecommendation(job) }) : null,
      el('div', { class: 'form-grid provider-form' },
        field('Retry output limit (tokens)', draft.max_output_tokens, value => edit('max_output_tokens', Number(value)), { id: 'recovery-max-output', type: 'number', min: 1, max: budget.maxOutput ?? budget.configuredCap ?? 65536, step: 1, 'data-testid': 'recovery-max-output', hint: budget.maxOutput === null ? 'Input budget unknown; prepare retry and preview first.' : `Allowed: 1–${tokens(budget.maxOutput)} tokens for this request.` }),
        field('Thinking control', draft.reasoning_effort ?? '', value => edit('reasoning_effort', value || null), { id: 'recovery-thinking-control', choices: [['', 'Provider default'], ['none', 'Disable thinking']], 'data-testid': 'recovery-thinking-control', hint: 'Thinking off is supported by this Ollama/Qwen setup.' }),
        field('Retry timeout (seconds)', draft.timeout_seconds, value => edit('timeout_seconds', Number(value)), { id: 'recovery-timeout', type: 'number', min: 0.05, max: 3600, step: 'any', 'data-testid': 'recovery-timeout', hint: 'Allowed: 0.05–3,600 s. A longer wait does not fix repetition.' })),
      el('div', { class: 'provider-actions' },
        el('button', { type: 'button', text: 'Save recovery settings', 'data-testid': 'save-recovery-settings', onclick: () => this.saveRecoverySettings(job) }),
        el('button', { type: 'button', text: 'Prepare retry with saved settings', 'data-testid': 'prepare-retry', onclick: () => this.prepareRetry(job) }),
        el('button', { type: 'button', text: 'Reset to saved settings', 'data-testid': 'reset-recovery-settings', onclick: () => { this.recoveryDrafts.delete(job.id); this.renderResult(); } })),
      el('p', { class: 'generation-gate', 'data-testid': 'recovery-gate' }),
      el('details', { 'data-testid': 'recovery-details' },
        el('summary', { text: 'Request details' }),
        el('p', { 'data-testid': 'recovery-stats', text: `Recorded completion tokens: ${completion ?? 'Unknown'} · output limit: ${limit ?? 'Unknown'} · answer characters: ${Array.from(job.raw_content || '').length} · reasoning characters: ${Array.from(job.raw_reasoning || '').length} · finish reason: ${job.finish_reason || 'Not received'}` }),
        timeout ? el('p', { 'data-testid': 'recovery-timeout-explanation', text: `The request timed out after ${job.profile?.timeout_seconds ?? 'an unknown number of'} seconds. This does not establish that the output limit or the model's capacity was reached.` }) : null,
        (job.error?.category || job.error?.code) === 'stream_incomplete' ? el('p', { text: 'No normal stop finish reason was received. The saved response does not establish that the output limit or request timeout was reached.' }) : null,
        el('p', { text: 'The failed record and source are preserved. Retrying creates a separate job from the same request; partial output is not used as repair RTL. Changed instructions require a new request. No automatic retry or provider fallback occurs.' })));
  }

  requestPayload() {
    return { node_id: this.nodeId, revision_id: this.project().envelope.revision.id, operation: this.operation, instruction: this.instruction,
      ...(this.operation === 'repair' && this.baseJobId ? { base_job_id: this.baseJobId } : {}),
      ...(this.retryOfJobId ? { retry_of_job_id: this.retryOfJobId } : {}) };
  }

  async previewContext() {
    if (this.requestBusy || this.generationGate()) return;
    const identity = this.requestIdentity(), token = ++this.requestToken;
    this.requestBusy = true; this.refreshGenerationActions(); this.callbacks.chrome?.();
    const payload = this.requestPayload();
    try {
      const response = await this.callbacks.request('generation/context', payload);
      if (identity !== this.requestIdentity() || token !== this.requestToken) return;
      this.preview = response;
      this.previewStale = !same(payload, this.requestPayload());
      this.renderPreview();
      this.callbacks.toast('Context preview prepared. Inspect the exact prompt before starting generation.');
    } catch (error) { if (identity === this.requestIdentity() && token === this.requestToken) { this.previewStale = true; this.callbacks.notify(error.message, 'error'); } }
    finally { if (token === this.requestToken) { this.requestBusy = false; if (identity === this.requestIdentity()) { this.refreshGenerationActions(); this.callbacks.chrome?.(); } } }
  }

  renderPreview() {
    const host = this.host?.querySelector('#generation-context-content');
    if (!host) return;
    if (!this.preview) { host.replaceChildren(el('p', { text: 'No preview is prepared. Choose a node and use Context Preview. No model is called by this action.' })); return; }
    const preview = this.preview;
    host.replaceChildren(el('div', { class: 'provider-identity' }, badge(this.previewStale ? 'Preview out of date' : 'Frozen request preview', this.previewStale ? 'orange' : 'teal'), el('code', { text: preview.context_id })),
      el('p', { text: `${preview.estimated_input_tokens} estimated input tokens · ${preview.token_estimate_method}. This is an estimate, not provider usage.` }),
      el('p', { 'data-testid': 'generation-context-budget', text: `Budgeted input ${inputEstimate(preview)} + output limit ${this.llm.profile?.max_output_tokens} = ${inputEstimate(preview) + this.llm.profile?.max_output_tokens}; saved context window ${this.llm.profile?.context_window}. The input budget includes serialized message framing when recorded by the service.` }),
      el('p', { text: `Profile ${preview.profile_revision_id} · input hash ${preview.node_input_hash}` }),
      el('details', { open: true }, el('summary', { text: 'Exact prompt sent to the provider' }), el('pre', { text: preview.prompt_text, 'data-testid': 'context-prompt' })),
      el('details', {}, el('summary', { text: 'Scoped input, physical interface & complete request metadata' }), el('pre', { text: JSON.stringify(preview, null, 2) })),
      el('p', { class: 'scope-note', text: 'JSON previews use browser number precision. Downloads preserve the backend’s exact integers.' }),
      el('button', { type: 'button', text: 'Download context JSON', 'data-testid': 'download-context', onclick: () => downloadJsonResponse(`/api/artifacts/generation-preview/${encodeURIComponent(preview.context_id)}/context`, `${filename(preview.node_id)}-context.json`, this.callbacks.notify) }));
  }

  async startGeneration() {
    if (this.requestBusy || this.previewGate()) return;
    const payload = clone(this.requestPayload()), preview = this.preview, submissionId = newSubmissionId();
    const pending = { scope: this.startScope(), contextId: preview.context_id, profileRevisionId: preview.profile_revision_id,
      nodeId: payload.node_id, revisionId: payload.revision_id, operation: payload.operation,
      baseJobId: payload.base_job_id || null, retryOfJobId: payload.retry_of_job_id || null,
      knownJobIds: this.generation.jobs.map(job => job.id), submissionId,
      request: { ...payload, context_id: preview.context_id, profile_revision_id: preview.profile_revision_id, submission_id: submissionId } };
    this.pendingStarts.set(pending.scope, pending);
    // Retain the identity AND exact frozen request before the first POST.
    if (!this.persistStartRecovery()) { this.pendingStarts.delete(pending.scope); this.callbacks.notify(this.startRecoveryGate(), 'error'); this.refreshStatus(); return; }
    await this.sendStart(pending, false);
  }

  async sendStart(pending, recovery) {
    const identity = this.requestIdentity(), token = ++this.requestToken, scope = pending.scope;
    const payload = Object.fromEntries(Object.entries(pending.request).filter(([key]) => !['context_id', 'profile_revision_id', 'submission_id'].includes(key)));
    const submitted = { identity, payload, preview: this.preview, contextId: pending.contextId, profileRevisionId: pending.profileRevisionId };
    this.requestBusy = true; this.refreshGenerationActions();
    try {
      const response = await this.callbacks.request('generation/start', clone(pending.request));
      if (identity !== this.requestIdentity() || token !== this.requestToken) return;
      const receipt = response.generation_submission;
      const matches = this.matchingStartJobs(pending, response.generation?.jobs || []);
      if (receipt?.version !== START_PROTOCOL || receipt.submission_id !== pending.submissionId || matches.length !== 1 || receipt.job_id !== matches[0].id) throw new Error('The start response did not identify this exact keyed submission. Refresh saved jobs or retry the same request; no new identity is created.');
      if (this.pendingStarts.get(scope) === pending) this.pendingStarts.delete(scope);
      this.persistStartRecovery(); this.selectedJobId = receipt.job_id;
      this.submittedRequest = recovery ? null : { ...submitted, jobId: receipt.job_id };
      if (recovery) { this.preview = null; this.previewStale = true; }
      this.pollFailure = null; this.callbacks.envelope(response);
      this.callbacks.toast(receipt.replayed ? 'The same saved submission was recovered. No second job was created.' : 'Generation job started. Required candidate checks and the saved adoption policy determine eligibility.');
    } catch (error) {
      // Only a durable, server-issued rejection for THIS identity releases it.
      if (error.generationStartRejectedBeforeCreation === true && error.submissionId === pending.submissionId && Number.isInteger(error.status) && error.status >= 400 && error.status < 500) {
        if (this.pendingStarts.get(scope) === pending) this.finishStartRecovery(scope);
      }
      if (identity === this.requestIdentity() && token === this.requestToken) this.callbacks.notify(error.message, 'error');
    }
    finally { if (token === this.requestToken) { this.requestBusy = false; if (identity === this.requestIdentity()) { this.refreshStatus(); this.schedulePoll(); } } }
  }

  renderProgress() {
    const host = this.host?.querySelector('#generation-node-progress');
    if (!host) return;
    host.replaceChildren(...this.project().design.nodes.map(node => {
      const evidence = this.generation.nodes.find(item => item.node_id === node.id);
      const accepted = evidence?.review_status === 'Accepted' && evidence?.freshness === 'Current';
      const job = this.generation.jobs.find(item => item.id === evidence?.latest_job_id);
      return el('div', { 'data-testid': `generation-progress-${node.id}` }, el('button', { type: 'button', class: 'link-button', text: node.name, onclick: () => this.selectNode(node.id) }),
        el('span', { class: 'generation-node-badges' }, job && ACTIVE.has(job.execution_status) ? badge(job.execution_status) : null,
          badge(accepted ? 'RTL accepted for synthesis' : evidence?.freshness === 'Stale' ? 'Stale' : evidence?.review_status || 'Not generated', accepted ? 'teal' : 'neutral')));
    }));
  }

  renderJobList() {
    const host = this.host?.querySelector('#generation-job-list');
    if (!host) return;
    const jobs = this.nodeJobs();
    host.replaceChildren(...(jobs.length ? jobs.map(job => el('button', { type: 'button', class: `generation-job-button${job.id === this.selectedJobId ? ' selected' : ''}`, 'data-testid': `generation-job-${job.id}`, onclick: () => { this.selectedJobId = job.id; this.renderJobList(); this.renderResult(); this.renderReview(this.reviewHost); } },
      badge(job.execution_status), badge(this.validationLabel(job), this.validationLabel(job) === 'Passed' ? 'teal' : 'neutral'), badge(job.freshness || 'Current', job.freshness === 'Stale' ? 'orange' : 'neutral'), el('code', { text: job.id }), el('small', { text: `${job.operation === 'verify' ? 'Saved RTL verification · no model request' : job.operation} · ${date(job.created_at)}` }))) : [el('p', { class: 'empty-small', text: 'No generation job for this node.' })]));
  }

  renderResult() {
    const host = this.host?.querySelector('#generation-result-content');
    if (!host) return;
    const job = this.selectedJob();
    const storageError = this.generation.storage_error;
    if (!job) {
      host.replaceChildren(el('div', { class: 'generation-result-empty' }, el('span', { class: 'large-symbol', text: '⌘' }), el('h3', { text: 'No generated candidate' }), el('p', { text: 'Preview the scoped request, then explicitly generate it. No example RTL or fabricated response is displayed here.' })));
      if (storageError) host.prepend(el('div', { class: 'generation-error', 'data-testid': 'generation-storage-error' }, el('strong', { text: `${storageError.code || 'Storage error'} · ` }), storageError.message || JSON.stringify(storageError)));
      const recovery = this.renderStartRecovery(); if (recovery) host.prepend(recovery);
      this.callbacks.chrome?.();
      return;
    }
    const current = job.freshness === 'Current';
    const busy = inProgress(job);
    const status = el('div', { class: 'generation-summary', 'data-testid': 'generation-job-status' }, badge(job.execution_status, job.execution_status === 'Completed' ? 'teal' : busy ? 'neutral' : 'orange'), badge(this.validationLabel(job), this.validationLabel(job) === 'Passed' ? 'teal' : 'neutral'), badge(current ? 'Current input' : 'Stale input', current ? 'neutral' : 'orange'), el('code', { text: job.id }));
    status.dataset.testid = 'generation-job-status';
    const progress = busy ? el('div', { class: 'generation-progress' }, el('span', { class: 'generation-spinner', 'aria-hidden': 'true' }), el('span', { text: `${job.execution_status === 'Completed' ? 'Candidate checks in progress' : job.execution_status} · ${job.events?.length || 0} actual event(s) recorded` }), ACTIVE.has(job.execution_status) ? el('button', { type: 'button', text: 'Cancel request', 'data-testid': 'cancel-generation', onclick: () => this.cancel(job) }) : null) : null;
    const error = job.error && this.validationLabel(job) !== 'Passed' ? el('div', { class: 'generation-error' }, el('strong', { text: `${job.error.category || job.error.code || job.error.type || 'Request error'} · ` }), job.error.message || JSON.stringify(job.error)) : null;
    const tabs = el('div', { class: 'generation-result-tabs', role: 'tablist', 'aria-label': 'Generation evidence views' },
      [['rtl', 'Candidate RTL'], ['request', 'LLM request'], ['diff', 'Diff'], ['raw', job.operation === 'verify' ? 'Original answer' : 'Raw answer'], ['checks', 'Checks'], ['events', 'Events & record']].map(([id, label]) => el('button', { type: 'button', role: 'tab', 'aria-selected': String(this.artifactTab === id), class: this.artifactTab === id ? 'active' : '', 'data-testid': `generation-tab-${id}`, text: label, onclick: () => { this.artifactTab = id; this.renderResult(); } })));
    const recovery = this.renderRecovery(job);
    const verification = this.renderVerification(job);
    const check = job.checks?.interface;
    const value = check?.validation_status || 'Not Checked';
    const checkSummary = el('div', { class: 'generation-summary', 'data-testid': 'generation-check-summary' },
      badge(`External interface: ${value}`, value === 'Passed' ? 'teal' : value === 'Failed' ? 'orange' : 'neutral'),
      badge('Synthesis: S05'), badge('Circuit behavior: S06'));
    const latestId = this.nodeState()?.latest_job_id;
    const requestAccess = el('div', { class: 'generation-request-access' },
      el('button', { type: 'button', text: 'Read this job’s LLM request', 'data-testid': 'generation-read-request', onclick: () => { this.artifactTab = 'request'; this.renderResult(); this.host?.querySelector('[data-testid="generation-saved-request"]')?.scrollIntoView?.({ behavior: 'smooth', block: 'start' }); } }),
      latestId && latestId !== job.id ? el('button', { type: 'button', text: 'Show latest node request', 'data-testid': 'generation-latest-request', onclick: () => { this.selectedJobId = latestId; this.artifactTab = 'request'; this.renderJobList(); this.renderResult(); this.renderReview(this.reviewHost); } }) : null,
      latestId && latestId !== job.id ? el('span', { text: 'Viewing an earlier job for this node.' }) : null);
    host.replaceChildren(status, checkSummary, requestAccess, ...(progress ? [progress] : []), ...(error ? [error] : []), ...(recovery ? [recovery] : []),
      ...(job.operation === 'verify' ? [el('p', { class: 'scope-note', 'data-testid': 'generation-verification-lineage', text: `Saved RTL verification of ${job.verification_of_job_id}. No model request was made; the RTL and original model-answer provenance are preserved.` })] : []),
      ...(job.retry_of_job_id ? [el('p', { class: 'scope-note', 'data-testid': 'generation-retry-lineage', text: `Retry of ${job.retry_of_job_id}. The original request and failure remain saved as a separate job.` })] : []),
      ...(verification ? [verification] : []),
      el('p', { class: 'scope-note generation-result-scope', text: `Origin ${job.origin} · source ${job.revision_id} · profile ${job.profile_revision_id}. S04 acceptance covers the generated external interface; circuit behavior is verified in S06.` }),
      el('p', { class: 'scope-note', text: 'JSON previews use browser number precision. Downloads preserve the backend’s exact integers.' }), tabs, this.artifactView(job));
    if (storageError) host.prepend(el('div', { class: 'generation-error', 'data-testid': 'generation-storage-error' }, el('strong', { text: `${storageError.code || 'Storage error'} · ` }), storageError.message || JSON.stringify(storageError)));
    const startRecovery = this.renderStartRecovery();
    if (startRecovery) host.prepend(startRecovery);
    else if (this.pollFailure) host.append(el('div', { class: 'generation-error' }, el('p', { text: this.pollFailure }), el('button', { type: 'button', text: 'Reconnect to job', 'data-testid': 'reconnect-generation', onclick: () => { this.pollFailure = null; this.pollJob(true); } })));
    this.refreshRecoveryActions();
    this.callbacks.chrome?.();
  }

  artifactView(job) {
    const actions = el('div', { class: 'generation-artifact-actions' },
      job.rtl ? el('button', { type: 'button', text: 'Download RTL', 'data-testid': 'download-rtl', onclick: () => downloadText(job.rtl, `${filename(job.context?.interface?.module_name || job.node_id)}-${filename(job.id)}.v`) }) : null,
      el('button', { type: 'button', text: 'Download raw answer', 'data-testid': 'download-raw-answer', onclick: () => downloadText(job.raw_content || '', `${filename(job.id)}-answer.txt`) }),
      el('button', { type: 'button', text: 'Download job JSON', 'data-testid': 'download-generation-job', onclick: () => downloadJsonResponse(`/api/generation/jobs/${encodeURIComponent(job.id)}`, `${filename(job.id)}.json`, this.callbacks.notify) }),
      el('button', { type: 'button', text: 'Download saved context JSON', 'data-testid': 'download-generation-context', onclick: () => downloadJsonResponse(`/api/artifacts/generation/${encodeURIComponent(job.id)}/context`, `${filename(job.id)}-context.json`, this.callbacks.notify) }));
    let content;
    if (this.artifactTab === 'rtl') content = el('div', {}, el('p', { text: job.rtl ? 'Extracted candidate Verilog. Check its external interface, then continue through S05 synthesis and S06 netlist behavioral verification.' : 'No candidate RTL was extracted. Partial raw output, errors, and events remain available.' }), el('pre', { text: job.rtl || 'No candidate RTL', 'data-testid': 'candidate-rtl' }));
    else if (this.artifactTab === 'request') content = el('section', { class: 'prompt-panel', 'data-testid': 'generation-saved-request' },
      el('h3', { text: 'Saved LLM request' }),
      el('p', { class: 'prompt-metadata', text: `Job: ${job.id} · operation: ${job.operation} · base candidate: ${job.base_job_id || 'None'} · context: ${job.context_id || 'Not recorded'} · status: ${job.execution_status}` }),
      el('p', { text: job.operation === 'verify' || job.provider_request_executed === false ? 'This verification-only record sent no model request. Its preserved original context is shown below.' : 'These are the frozen instructions and complete request messages saved for this job. Reading or downloading them does not submit a request.' }),
      job.context?.batch_context?.repair_guidance ? repairGuidanceView(job.context.batch_context.repair_guidance, { prefix: 'generation-saved-guidance', title: 'Repair guidance frozen with this request' }) : null,
      instructionView(job.instruction, { prefix: 'generation-saved-request', title: job.operation === 'repair' ? 'Complete repair instruction saved for this job' : 'Complete additional instruction saved for this job' }),
      promptMessagesView(job.context, { prefix: 'generation-saved-request', title: 'Full saved messages', open: true }),
      el('button', { type: 'button', text: 'Download request text', 'data-testid': 'download-generation-request-text', onclick: () => downloadText(promptTranscript(job.context?.messages || []), `${filename(job.id)}-request.txt`) }));
    else if (this.artifactTab === 'diff') content = el('div', {}, el('p', { text: job.base_job_id ? `Compared with ${job.base_job_id}.` : 'Initial candidate; no previous RTL candidate was selected.' }), el('pre', { text: job.diff || 'No RTL difference is recorded.', 'data-testid': 'rtl-diff' }));
    else if (this.artifactTab === 'raw') content = el('div', {}, el('p', { text: `${job.operation === 'verify' ? 'Preserved original model answer; this verification sent no model request. ' : ''}Finish reason: ${job.finish_reason || 'Not received'} · usage: ${job.usage ? JSON.stringify(job.usage) : 'Unknown'}. Partial output is not an accepted implementation.` }), el('pre', { text: job.raw_content || 'No answer text received.', 'data-testid': 'raw-answer' }),
      job.raw_reasoning ? el('details', {}, el('summary', { text: 'Separate provider reasoning output' }), el('p', { text: 'Text returned by the configured provider. This is not circuit verification evidence.' }), el('pre', { text: job.raw_reasoning, 'data-testid': 'raw-provider-reasoning' })) : null);
    else if (this.artifactTab === 'checks') content = el('div', {}, el('p', { text: 'S04 requires the external-interface check. The complete original check record is retained below, including any historical syntax or behavioral reports. These historical reports are not S04 acceptance requirements; current synthesis and netlist verification belong to S05 and S06.' }),
      el('div', { class: 'diagnostics', 'data-testid': 'generation-diagnostics' }, (job.diagnostics || []).map(item => el('div', { class: `diagnostic ${item.severity || 'info'}` }, badge(item.severity || 'info', item.severity === 'error' ? 'orange' : 'neutral'), el('code', { text: item.code || '' }), el('span', { text: item.message || JSON.stringify(item) })))), el('pre', { text: JSON.stringify(job.checks || {}, null, 2), 'data-testid': 'candidate-checks' }));
    else content = el('div', {}, el('p', { text: 'Persisted events can be revisited after reconnecting. Cancel disconnects the client; server-side inference halt is not guaranteed.' }),
      el('details', { open: true }, el('summary', { text: `${job.events?.length || 0} actual event(s)` }), el('pre', { text: JSON.stringify(job.events || [], null, 2), 'data-testid': 'generation-events' })),
      el('details', {}, el('summary', { text: 'Complete source, profile, context, parameters & result record' }), el('pre', { text: JSON.stringify(job, null, 2) })));
    return el('div', { class: 'generation-artifact' }, content, actions);
  }

  renderReview(host) {
    if (!host) return;
    this.reviewHost = host;
    const job = this.selectedJob();
    const project = this.project();
    if (!job) { host.replaceChildren(el('div', { class: 'review-empty' }, el('div', { class: 'review-empty-symbol', text: '◎' }), el('div', {}, el('h3', { text: 'No node candidate to review' }), el('p', { text: 'Actual generated RTL and its checks will appear here. A model answer alone is not verification evidence.' })))); return; }
    const previous = this.prerequisiteStages();
    const latest = this.nodeState()?.latest_job_id === job.id;
    const current = job.freshness === 'Current';
    const acceptanceRecord = [...(this.generation.reviews || [])].reverse().find(review => review.job_id === job.id && review.decision === 'accepted');
    const interfacePassed = !!job.rtl && job.checks?.interface?.validation_status === 'Passed' && this.validationLabel(job) === 'Passed';
    const checkReason = !interfacePassed ? 'A complete RTL candidate with a matching external interface is required before S04 acceptance.' : '';
    const canAccept = !this.runtimeReadOnly() && !project.dirty && !project.conflict && !this.requestBusy && current && latest && !inProgress(job) && job.execution_status === 'Completed' && !checkReason && previous.every(stage => stage.review_status === 'Accepted' && stage.freshness === 'Current');
    const canDecide = !this.runtimeReadOnly() && !project.dirty && !project.conflict && !this.requestBusy && current && !inProgress(job);
    const note = el('textarea', { id: 'generation-feedback', rows: 3, value: this.feedback.get(job.id) || '', placeholder: 'Record your review conclusion or the required correction.', 'aria-label': 'Node candidate review note', 'data-testid': 'generation-feedback', oninput: event => { this.feedback.set(job.id, event.target.value); } });
    let target = this.returnTargets.get(job.id) || 'specifications';
    const returnTarget = field('Return destination', target, value => { target = value; this.returnTargets.set(job.id, value); }, { id: 'generation-return-stage', 'data-testid': 'generation-return-stage', choices: [['global_settings', 'Global Settings'], ['graph_editor', 'Graph Editor'], ['specifications', 'Specifications']] });
    const reason = project.conflict ? 'A newer saved source was detected. Export your draft, then Open saved before reviewing this candidate.' : project.dirty ? 'Save the current design first. Existing candidates retain their original source snapshot.' : !current ? 'This candidate belongs to stale source input. Generate or repair from the current snapshot.' : !latest ? 'This is an older candidate. Review the latest candidate for acceptance.' : job.execution_status !== 'Completed' ? `The request is ${job.execution_status}; its output cannot be accepted.` : this.validationLabel(job) !== 'Passed' ? `The S04 external-interface check is ${this.validationLabel(job)}. Resolve it before accepting.` : checkReason || (previous.some(stage => stage.review_status !== 'Accepted' || stage.freshness !== 'Current') ? 'Current input-stage acceptance is required before candidate acceptance.' : '');
    const acceptance = el('button', { type: 'button', class: 'primary', text: job.review_status === 'Accepted' ? 'Candidate accepted' : 'Accept node candidate', 'data-testid': 'accept-candidate', disabled: !canAccept || job.review_status === 'Accepted', title: reason || 'Record your explicit acceptance. Remain at Local RTL Generation.', onclick: () => this.reviewJob(job, 'accepted', note.value) });
    // Preserve the active note while refreshing policy adoption and next actions.
    const activeNote = host.contains(document.activeElement) && document.activeElement.id === 'generation-feedback' ? document.activeElement : null;
    const selection = activeNote ? [activeNote.selectionStart, activeNote.selectionEnd] : null;
    host.replaceChildren(el('div', { class: 'generation-review-status' }, badge(job.review_status, job.review_status === 'Accepted' ? 'teal' : 'neutral'), badge(current ? 'Current' : 'Stale', current ? 'neutral' : 'orange'), el('code', { text: `Node ${job.node_id} · ${job.id}` })),
      el('p', { class: 'scope-note', 'data-testid': 'candidate-adoption-provenance', text: job.review_status === 'Accepted' ? adoptionProvenance(acceptanceRecord) : 'Review the generated external interface and accept this RTL for synthesis, or request a correction. S04 acceptance does not verify circuit behavior; S06 does that after S05 synthesis.' }),
      el('div', { class: 'feedback-row' }, el('div', { class: 'field feedback-field' }, el('label', { htmlFor: 'generation-feedback', text: 'Human feedback' }), note), returnTarget),
      el('div', { class: 'review-actions' }, acceptance,
        el('button', { type: 'button', text: 'Request Changes', 'data-testid': 'request-candidate-changes', disabled: !canDecide, onclick: () => this.reviewJob(job, 'changes_requested', note.value) }),
        el('button', { type: 'button', text: 'Prepare repair context', 'data-testid': 'prepare-repair', disabled: !job.rtl || inProgress(job) || this.requestBusy || this.runtimeReadOnly(), onclick: () => this.prepareRepair(job, note.value) }),
        el('button', { type: 'button', text: 'Return to Stage', 'data-testid': 'return-candidate-stage', disabled: !canDecide, onclick: () => this.reviewJob(job, 'return_to_stage', note.value, target) })),
      el('p', { class: 'gate-reason', 'data-testid': 'generation-review-reason', text: reason }),
      el('div', { class: 'generation-review-status' }, badge(this.generation.all_nodes_accepted ? 'All current node candidates accepted' : 'Other project nodes remain incomplete', this.generation.all_nodes_accepted ? 'teal' : 'neutral'),
        el('button', { type: 'button', text: 'Continue selected node to Local Synthesis', 'data-testid': 'continue-local-synthesis', disabled: job.review_status !== 'Accepted' || !current || !latest || project.dirty || !!project.conflict, title: 'Continue this accepted node. Completion of other nodes and the full project is independent.', onclick: () => this.callbacks.navigate('local_synthesis', job.node_id) })),
      el('details', { class: 'raw-result' }, el('summary', { text: 'Review provenance & checks' }), el('pre', { text: JSON.stringify({ job_id: job.id, node_id: job.node_id, revision_id: job.revision_id, input_hash: job.input_hash, profile_revision_id: job.profile_revision_id, context_id: job.context_id, execution_status: job.execution_status, validation_status: job.validation_status, review_status: job.review_status, checks: job.checks }, null, 2) })));
    if (activeNote) { note.focus({ preventScroll: true }); note.setSelectionRange(...selection); }
  }

  async reviewJob(job, decision, note, targetStage) {
    if (this.requestBusy || this.project().dirty) return;
    if (decision !== 'accepted' && !note.trim()) { this.callbacks.toast('Add a note explaining the requested change or return.'); this.reviewHost?.querySelector('#generation-feedback')?.focus(); return; }
    this.requestBusy = true; this.refreshGenerationActions();
    try {
      const response = await this.callbacks.request('generation/review', { job_id: job.id, decision, note: note.trim(), ...(targetStage ? { target_stage: targetStage } : {}) });
      this.callbacks.envelope(response);
      if (decision === 'return_to_stage') this.callbacks.navigate(targetStage);
      this.callbacks.toast(decision === 'accepted' ? 'Node candidate acceptance recorded. Review the remaining nodes before continuing.' : 'Your feedback was recorded against this source and candidate.');
    } catch (error) { this.callbacks.notify(error.message, 'error'); }
    finally { this.requestBusy = false; this.refreshStatus(); }
  }

  async cancel(job) {
    if (!ACTIVE.has(job.execution_status)) return;
    try { this.callbacks.envelope(await this.callbacks.request('generation/cancel', { job_id: job.id })); this.callbacks.toast('Cancellation requested. Client disconnect does not guarantee server-side inference halt.'); }
    catch (error) { this.callbacks.notify(error.message, 'error'); }
  }

  refreshStatus() {
    if (this.consumeCompletedRequest() && this.host?.isConnected && this.project().stage === 'local_rtl_generation') this.render(this.host);
    this.refreshProviderActions(); this.renderConnectionResult();
    this.refreshGenerationActions(); this.renderPreview(); this.renderProgress(); this.renderJobList(); this.renderResult();
    this.callbacks.batch?.()?.refresh();
    if (this.reviewHost?.isConnected && this.project().stage === 'local_rtl_generation') this.renderReview(this.reviewHost);
    this.callbacks.connection?.(this.connectionLabel());
    this.callbacks.providerStateChanged?.();
  }

  schedulePoll() {
    if (this.pollTimer || this.polling || this.pollFailure || !this.activeJob()) return;
    this.pollTimer = setTimeout(() => { this.pollTimer = null; this.pollJob(); }, 1300);
  }

  async pollJob(force = false) {
    if (this.polling) return;
    const job = this.activeJob() || (force ? this.selectedJob() : null);
    if (!job) return;
    const identity = this.requestIdentity(), token = ++this.pollToken;
    this.polling = true;
    try {
      const updated = await this.callbacks.request(`generation/jobs/${encodeURIComponent(job.id)}`);
      if (identity !== this.requestIdentity() || token !== this.pollToken) return;
      const index = this.generation.jobs.findIndex(item => item.id === updated.id);
      if (index >= 0) this.generation.jobs[index] = updated;
      else this.generation.jobs.push(updated);
      this.pollFailure = null;
      this.refreshStatus();
      this.pollCount = (this.pollCount || 0) + 1;
      if (!inProgress(updated) || this.pollCount % 3 === 0) {
        const response = await this.callbacks.request('project');
        if (identity === this.requestIdentity() && token === this.pollToken) this.callbacks.envelope(response);
      }
    } catch (error) { if (identity === this.requestIdentity() && token === this.pollToken) { this.pollFailure = `${error.message} The job is not resent. Use Reconnect to retrieve its saved result.`; this.renderResult(); } }
    finally { if (token === this.pollToken) { this.polling = false; if (identity === this.requestIdentity()) this.schedulePoll(); } }
  }
}
