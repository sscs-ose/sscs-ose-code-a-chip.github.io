/** Read-only health display for the prepared local server; never sends inference. */
export class ConnectionMonitor {
  constructor(callbacks) {
    this.callbacks = callbacks; this.identity = null; this.runtime = null; this.error = null;
    this.pending = false; this.timer = null; this.token = 0; this.checkedAt = null;
  }
  eligible() {
    const p = this.callbacks.project();
    if (p.readOnly || p.profileDirty || !p.envelope?.workspace_identity?.session_id) return false;
    const profile = p.envelope.llm?.profile;
    try {
      const url = new URL(profile?.base_url);
      return profile.execution_location === 'Local' && profile.model === 'qwen3:8b' && url.protocol === 'http:' && ['localhost', '127.0.0.1'].includes(url.hostname) && url.port === '11435' && url.pathname.replace(/\/+$/, '') === '/v1' && !url.username && !url.password && !url.search && !url.hash;
    } catch { return false; }
  }
  receive() {
    const p = this.callbacks.project(), llm = p.envelope?.llm;
    const identity = JSON.stringify([p.envelope?.workspace_identity?.session_id, llm?.profile_revision_id, p.readOnly]);
    if (identity !== this.identity) {
      this.identity = identity; this.token++; this.runtime = null; this.error = null; this.pending = false; this.checkedAt = null;
      if (this.timer) clearTimeout(this.timer); this.timer = null;
      if (this.eligible()) void this.refresh();
    } else if (!this.pending && !this.timer && this.eligible()) this.schedule();
  }
  schedule() {
    if (!this.timer && this.eligible()) this.timer = setTimeout(() => { this.timer = null; void this.refresh(); }, 15000);
  }
  async refresh() {
    if (this.pending || !this.eligible()) return;
    if (this.callbacks.visible?.() === false) { this.schedule(); return; }
    const token = this.token; this.pending = true;
    try {
      // The absent body selects GET. No model probe/history/RTL/tool action is submitted.
      const result = await this.callbacks.request('workspace/local-runtime');
      if (token !== this.token) return;
      if (!result?.runtime || typeof result.runtime.state !== 'string') throw new Error('Local server status is unavailable.');
      this.runtime = result.runtime; this.error = null; this.checkedAt = Date.now();
    } catch (error) {
      if (token === this.token) { this.error = error.message || 'Local server status is unavailable.'; this.checkedAt = Date.now(); }
    } finally {
      if (token === this.token) { this.pending = false; this.callbacks.changed?.(); this.schedule(); }
    }
  }
  stop() { this.token++; if (this.timer) clearTimeout(this.timer); this.timer = null; this.pending = false; }
}
