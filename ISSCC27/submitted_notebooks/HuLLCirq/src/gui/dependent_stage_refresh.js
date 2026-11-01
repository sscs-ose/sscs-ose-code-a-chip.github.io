// A terminal/adoption observation needs one fresh dependency snapshot, not a
// request on every tab switch. This coordinator never starts or saves anything.
const TERMINAL = new Set(['Completed', 'Failed', 'Cancelled', 'Interrupted']);
const stamp = record => JSON.stringify([record.id, record.execution_status, record.validation_status,
  record.review_status, record.freshness, record.acceptance_epoch, record.source_key]);

export function terminalDependencyStamps(envelope) {
  const values = new Map();
  const add = (stage, record) => { if (record?.id && TERMINAL.has(record.execution_status)) values.set(stage, stamp(record)); };
  if (envelope.global_generation) add('global_rtl_generation', envelope.global_generation.jobs?.at(-1));
  if (envelope.global_workflow) for (const stage of envelope.global_workflow.stages || [])
    add(stage.stage_id, envelope.global_workflow.runs?.find(run => run.id === stage.latest_run_id));
  for (const [key, stage] of [['physical_workflow', 'layout'], ['drc_workflow', 'drc'], ['lvs_workflow', 'lvs']]) {
    const data = envelope[key];
    if (data) add(stage, data.runs?.find(run => run.id === data.latest_run_id));
  }
  return values;
}

export class DependentStageRefresh {
  constructor(callbacks) { this.callbacks = callbacks; this.scope = null; this.seen = new Map(); this.pending = null; }
  currentScope() {
    const scope = this.callbacks.scope();
    // A slow former project's read must not hold the new context's queue.
    if (scope !== this.scope) { this.scope = scope; this.seen = new Map(); this.pending = null; }
    return scope;
  }
  rememberFull(envelope) {
    this.currentScope();
    for (const [stage, value] of terminalDependencyStamps(envelope)) this.seen.set(stage, value);
  }
  observe(envelope) {
    const scope = this.currentScope();
    const changed = [...terminalDependencyStamps(envelope)].filter(([stage, value]) => this.seen.get(stage) !== value);
    if (!changed.length) return this.pending || Promise.resolve(false);
    for (const [stage, value] of changed) this.seen.set(stage, value);
    const clearAttempt = () => {
      if (this.currentScope() !== scope) return;
      for (const [stage, value] of changed) if (this.seen.get(stage) === value) this.seen.delete(stage);
    };
    const task = async () => {
      if (this.currentScope() !== scope) return false;
      try {
        if (await this.callbacks.refresh() === false) { clearAttempt(); return false; }
        return true;
      } catch (error) {
        clearAttempt();
        if (this.currentScope() === scope) this.callbacks.notify?.(
          `${error.message} Dependent-stage status was not refreshed. Use Refresh saved tool runs to read saved progress; no execution was resent.`, 'error');
        return false;
      }
    };
    const pending = (this.pending || Promise.resolve()).then(task);
    this.pending = pending;
    void pending.finally(() => { if (this.pending === pending) this.pending = null; });
    return pending;
  }
}
