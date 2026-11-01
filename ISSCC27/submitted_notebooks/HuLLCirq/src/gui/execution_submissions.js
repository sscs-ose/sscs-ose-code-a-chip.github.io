const VERSION = 'execution-submission-v1';
const KEY = 'hullcirq.execution-start-recovery.v1';
export const EXECUTION_START_ROUTES = new Set(['generation/batches/start', 'repair-analysis/start', 'workflow/start', 'workflow/batches/start', 'global-generation/start', 'global-workflow/runs', 'physical-workflow/runs', 'drc-workflow/runs', 'lvs-workflow/runs', 'postlayout-workflow/runs']);
const copy = value => JSON.parse(JSON.stringify(value));
const stable = value => JSON.stringify(value, (key, item) => item && typeof item === 'object' && !Array.isArray(item) ? Object.fromEntries(Object.keys(item).sort().map(name => [name, item[name]])) : item);
const semantic = body => Object.fromEntries(Object.entries(body).filter(([key]) => key !== 'submission_id'));
const identity = () => globalThis.crypto?.randomUUID ? globalThis.crypto.randomUUID() : `request-${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}-${Math.random().toString(36).slice(2)}`;
const notSent = message => Object.assign(new Error(message), { request_not_sent: true });
const nonempty = value => typeof value === 'string' && value.length > 0;
const rejection = value => value && typeof value === 'object' && !Array.isArray(value) && Number.isInteger(value.status) && value.status >= 400 && value.status < 500 && typeof value.code === 'string' && typeof value.message === 'string';
const boundReceipt = (value, route, body) => value && value.route === route && typeof value.binding_hash === 'string' && /^[a-f0-9]{64}$/.test(value.binding_hash) && stable(value.request) === stable(semantic(body));

/** One scoped, frozen identity before each model/native POST. No automatic POST. */
export class ExecutionSubmissions {
  constructor(callbacks) {
    this.callbacks = callbacks; this.entries = new Map(); this.storage = null;
    this.storageError = null; this.reading = false; this.replaying = false; this.lastResolution = null;
    try {
      this.storage = callbacks.storage ?? (typeof sessionStorage === 'undefined' ? null : sessionStorage);
      if (!this.storage) throw new Error('Session storage unavailable');
      const saved = JSON.parse(this.storage?.getItem(KEY) || '[]');
      if (!Array.isArray(saved) || saved.some(value => !value || typeof value.scope !== 'string' || !EXECUTION_START_ROUTES.has(value.route) || !value.body || typeof value.body.submission_id !== 'string' || !/^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/.test(value.body.submission_id))) throw new Error('Invalid saved execution request');
      for (const value of saved) {
        if (!nonempty(value.scope) || this.entries.has(value.scope)) throw new Error('Ambiguous saved execution scope');
        this.entries.set(value.scope, { ...value, sending: false });
      }
    } catch { this.storageError = 'The browser could not read saved execution recovery state. Restore session storage and reload before starting another execution.'; }
  }
  context() { return this.callbacks.context(); }
  pending() { return this.entries.get(this.context().scope); }
  persist() {
    try {
      if (this.storage) {
        if (this.entries.size) this.storage.setItem(KEY, JSON.stringify([...this.entries.values()]));
        else this.storage.removeItem(KEY);
      }
      this.storageError = null; return true;
    } catch { this.storageError = 'The browser could not retain the exact execution request. No new request can be sent until session storage works again.'; return false; }
  }
  protocolGate() {
    const context = this.context();
    if (context.readOnly) return 'This preserved system is read-only.';
    if (context.envelope?.execution_submission_protocol_version !== VERSION) return 'Restart the local workspace service to enable safe execution recovery.';
    return '';
  }
  blocked() { return !!(this.pending() || this.storageError || this.protocolGate()); }
  gate() { return this.storageError || (this.pending() ? 'Reconnect to the previous execution start before submitting another request.' : this.protocolGate()); }
  prepare(route, input) {
    // S04 has ONE qualified I16 owner. Never create a second marker or nonce.
    if (route === 'generation/start') {
      if (this.pending() || this.storageError) throw notSent(this.gate());
      return input;
    }
    if (!EXECUTION_START_ROUTES.has(route)) return input;
    const context = this.context(), current = this.pending();
    if (this.storageError || this.protocolGate()) throw notSent(this.gate());
    if (!nonempty(context.scope)) throw notSent('Open a saved project and system before starting execution.');
    if (current) {
      if (route !== current.route || input.submission_id !== current.body.submission_id || stable(input) !== stable(current.body)) throw notSent('The previous start is unresolved. Use Retry same request; a new request was not sent.');
      current.sending = true;
      if (!this.persist()) { current.sending = false; throw notSent(this.storageError); }
      return copy(current.body);
    }
    if (this.callbacks.foreignPending?.()) throw notSent('Reconnect to the saved RTL generation start before another model or tool request.');
    const body = copy(input);
    if (!Object.hasOwn(body, 'submission_id')) body.submission_id = identity();
    if (typeof body.submission_id !== 'string' || !/^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/.test(body.submission_id)) throw notSent('Invalid execution submission identity.');
    body.submission_configuration_fingerprint = context.envelope.execution_configuration_fingerprints?.[route];
    if (typeof body.submission_configuration_fingerprint !== 'string') throw notSent('The saved execution configuration could not be identified. Refresh saved status first.');
    const entry = { scope: context.scope, route, body, revisionId: context.envelope.revision?.id, sending: true };
    this.entries.set(entry.scope, entry);
    if (!this.persist()) { this.entries.delete(entry.scope); throw notSent(this.storageError); }
    this.callbacks.changed?.(); return copy(body);
  }
  matching(route, body) {
    const entry = this.pending();
    return entry && entry.route === route && entry.body.submission_id === body?.submission_id && stable(entry.body) === stable(body) ? entry : null;
  }
  finish(entry, outcome) {
    if (this.entries.get(entry.scope) !== entry) return;
    this.entries.delete(entry.scope); this.persist(); this.lastResolution = { scope: entry.scope, route: entry.route, body: copy(entry.body), ...outcome };
  }
  observeSuccess(route, body, response) {
    if (!EXECUTION_START_ROUTES.has(route)) return;
    const entry = this.matching(route, body);
    if (!entry) throw new Error('The execution response belongs to another request. Refresh saved status without sending a new identity.');
    const receipt = response.execution_submission;
    if (receipt?.version !== VERSION || receipt.route !== route || receipt.submission_id !== body.submission_id || !nonempty(receipt.record_id)) throw new Error('The execution response did not identify the exact saved request. Refresh or retry the same request.');
    const saved = response.execution_submission_receipts?.[route]?.[body.submission_id];
    const rawAnalysis = route === 'repair-analysis/start' && response.id === receipt.record_id && response.submission_id === body.submission_id && response.request_id === body.request_id && response.context_id === body.context_id;
    if (!rawAnalysis && (!boundReceipt(saved, route, body) || saved.record_id !== receipt.record_id || saved.rejection !== null)) throw new Error('The saved receipt does not bind this frozen execution request. Refresh or retry the same request.');
    this.finish(entry, { status: 'started', recordId: receipt.record_id });
  }
  observeFailure(route, body, error, requestedScope = this.context().scope) {
    const value = this.entries.get(requestedScope);
    const entry = value && value.route === route && value.body.submission_id === body?.submission_id && stable(value.body) === stable(body) ? value : null;
    if (entry) { entry.sending = false; this.persist(); }
    if (entry && error.executionStartRejectedBeforeCreation === true && error.submissionId === body.submission_id && Number.isInteger(error.status) && error.status >= 400 && error.status < 500) this.finish(entry, { status: 'rejected' });
  }
  observeRead(envelope, requestedScope) {
    const currentScope = this.context().scope, entry = this.entries.get(requestedScope);
    if (!nonempty(currentScope) || !entry || entry.sending || entry.scope !== requestedScope || entry.scope !== currentScope) return;
    const receipt = envelope.execution_submission_receipts?.[entry.route]?.[entry.body.submission_id];
    if (!boundReceipt(receipt, entry.route, entry.body)) return;
    if (receipt.record_id === null && rejection(receipt.rejection)) this.finish(entry, { status: 'rejected' });
    else if (nonempty(receipt.record_id) && receipt.rejection === null) this.finish(entry, { status: 'started', recordId: receipt.record_id });
  }
  retryGate() {
    const context = this.context();
    if (!this.pending()) return 'No unresolved request.';
    if (this.pending()?.sending || this.reading || this.replaying || context.busy) return 'Wait for the current request or saved-status read.';
    if (context.readOnly || context.dirty || context.conflict) return 'Save or reopen the same editable system before retrying its frozen request.';
    return this.storageError || this.protocolGate();
  }
  async refresh() {
    if (this.pending()?.sending || this.reading || this.replaying) return;
    const scope = this.context().scope; this.reading = true; this.callbacks.changed?.();
    try {
      const envelope = await this.callbacks.read();
      if (scope !== this.context().scope) return;
      this.observeRead(envelope, scope); this.callbacks.publish(envelope); this.callbacks.toast?.(this.pending() ? 'No exact outcome is available yet. Retry same request keeps its original identity.' : 'Saved execution outcome recovered. No execution was resent.');
    } catch (error) { if (scope === this.context().scope) this.callbacks.notify?.(error.message, 'error'); }
    finally { this.reading = false; this.callbacks.changed?.(); }
  }
  async retry() {
    if (this.retryGate()) return;
    const entry = this.pending(), scope = entry.scope; this.replaying = true; this.callbacks.changed?.();
    try {
      const response = await this.callbacks.send(entry.route, copy(entry.body));
      if (scope !== this.context().scope) return;
      await this.callbacks.publish(response); this.callbacks.toast?.('The same logical request was recovered. No second execution identity was created.');
    } catch (error) { if (scope === this.context().scope) this.callbacks.notify?.(error.message, 'error'); }
    finally { this.replaying = false; this.callbacks.changed?.(); }
  }
  presentation() {
    const pending = this.pending();
    const protocol = !this.context().readOnly && this.context().envelope ? this.protocolGate() : '';
    if (!pending && !this.storageError && !protocol) return null;
    const labels = { 'generation/batches/start': 'Node RTL batch', 'repair-analysis/start': 'Repair guidance analysis', 'workflow/start': 'Node tool execution', 'workflow/batches/start': 'All-node tool execution', 'global-generation/start': 'Global RTL generation', 'global-workflow/runs': 'Whole-design tool execution', 'physical-workflow/runs': 'Physical layout', 'drc-workflow/runs': 'DRC', 'lvs-workflow/runs': 'LVS', 'postlayout-workflow/runs': 'Post-layout verification' };
    return { title: 'Reconnect to the saved execution request', label: labels[pending?.route] || 'Execution recovery',
      summary: this.storageError || protocol || (pending?.sending ? 'Waiting for the start acknowledgement. The saved identity prevents a second execution when recovery is needed.' : 'The start outcome is uncertain. Refresh reads saved progress. Retry same request reuses the original identity and frozen inputs.'),
      readDisabled: !!pending?.sending || this.reading || this.replaying, retryDisabled: !!this.retryGate(), retryReason: this.retryGate() };
  }
}
