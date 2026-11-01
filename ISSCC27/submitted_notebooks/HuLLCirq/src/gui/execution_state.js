/** Presentation/reconnection ledger only. Never changes saved runs or authorizes work. */
export const STAGE_ORDER = Object.freeze([
  'global_settings', 'graph_editor', 'specifications', 'local_rtl_generation',
  'local_synthesis', 'local_netlist_simulation', 'node_implementation_specs',
  'global_rtl_generation', 'global_synthesis', 'global_netlist_simulation',
  'layout', 'drc', 'lvs', 'post_layout_verification',
]);

/** Only actual execution requests invalidate subsequent stage displays. */
export function executionAction(path, body) {
  if (!body || typeof body !== 'object') return null; // GETs never execute.
  const route = String(path).replace(/^\/api\//, '').replace(/^\//, '').replace(/\/+$/, '');
  let stageId;
  if (route === 'validate') stageId = body.stage_id;
  else if (['generation/start', 'generation/verify', 'generation/batches/start'].includes(route)) stageId = 'local_rtl_generation';
  else if (route === 'workflow/start') stageId = body.stage_id;
  else if (route === 'workflow/batches/start') stageId = body.stage_id || 'local_synthesis';
  else if (route === 'implementation-specs/start') stageId = 'node_implementation_specs';
  else if (route === 'global-generation/start') stageId = 'global_rtl_generation';
  else if (route === 'global-workflow/runs') stageId = body.stage;
  else if (route === 'physical-workflow/runs' || /^physical-workflow\/runs\/[^/]+\/revalidate$/.test(route)) stageId = 'layout';
  else if (route === 'drc-workflow/runs') stageId = 'drc';
  else if (route === 'lvs-workflow/runs') stageId = 'lvs';
  else if (route === 'postlayout-workflow/runs') stageId = 'post_layout_verification';
  if (!STAGE_ORDER.includes(stageId)) return null;
  return { stageId, kind: 'execute', ...(body.node_id ? { nodeId: body.node_id } : {}),
    ...(route === 'generation/verify' && body.job_id ? { recordId: body.job_id } : {}),
    ...(body.request_id ? { requestId: body.request_id } : {}) };
}

const ACTIVE = new Set(['Queued', 'Running', 'Starting', 'Stopping', 'Cancelling']);
const FAILED = new Set(['Failed', 'Cancelled', 'Canceled', 'Interrupted', 'Unsupported']);
const REVIEW_FAILED = new Set(['Request Changes', 'Changes Requested', 'Rejected', 'Returned']);
const clone = value => JSON.parse(JSON.stringify(value));
const idOf = record => record?.id || record?.run_id || record?.job_id || record?.spec_id;
const validation = record => record?.stage_validation?.validation_status || record?.effective_validation_status || record?.validation_status;
const stageOf = record => record?.stage_id || record?.stage;
const isActive = record => ACTIVE.has(record?.execution_status);
const isTerminal = record => record?.execution_status === 'Completed' || FAILED.has(record?.execution_status);

/** Collect real record identities, including aggregate batches; no synthetic success. */
function recordsFrom(envelope) {
  if (!envelope || typeof envelope !== 'object') return [];
  const records = [], add = (values, stage, batch = false) => {
    for (const record of Array.isArray(values) ? values : []) {
      const stageId = stage || stageOf(record);
      if (idOf(record) && STAGE_ORDER.includes(stageId)) records.push({ ...record, stage_id: stageId, _batch: batch });
    }
  };
  add(envelope.runs); add(envelope.workflow_runs);
  add(envelope.generation?.jobs, 'local_rtl_generation');
  add(envelope.implementation_specs, 'node_implementation_specs');
  add(envelope.global_generation?.jobs, 'global_rtl_generation');
  add(envelope.global_workflow?.runs);
  for (const [key, stage] of [['physical_workflow', 'layout'], ['drc_workflow', 'drc'], ['lvs_workflow', 'lvs'], ['postlayout_workflow', 'post_layout_verification']])
    add(envelope[key]?.runs, stage);
  add(Array.isArray(envelope.generation_batches) ? envelope.generation_batches : envelope.generation_batches?.batches, 'local_rtl_generation', true);
  add(envelope.workflow_batches?.map(record => ({ ...record, stage_id: record.stage_id || 'local_synthesis' })), null, true);
  // Polls may return a single record or a narrow {runs: [...]} workflow view.
  if (idOf(envelope) && stageOf(envelope)) add([envelope]);
  for (const stage of Array.isArray(envelope.workflow) ? envelope.workflow : []) {
    const id = stage.latest_run_id || stage.latest_job_id || stage.latest_spec_id;
    if (id && STAGE_ORDER.includes(stage.id) && !records.some(record => record.stage_id === stage.id && idOf(record) === id))
      add([{ ...stage, id }], stage.id);
  }
  const unique = new Map();
  for (const record of records) unique.set(`${record.stage_id}:${idOf(record)}`, record);
  const result = [...unique.values()];
  const reviews = [envelope.reviews, envelope.workflow_reviews, envelope.implementation_spec_reviews,
    ...['generation', 'global_generation', 'global_workflow', 'physical_workflow', 'drc_workflow', 'lvs_workflow', 'postlayout_workflow'].map(key => envelope[key]?.reviews)]
    .flatMap(values => Array.isArray(values) ? values : []);
  for (const record of result) {
    const review = reviews.findLast(item => [item.run_id, item.job_id, item.spec_id].includes(idOf(record)));
    if (review?.note) record._reviewNote = review.note;
  }
  for (const record of result.filter(record => record._batch)) {
    const items = record.items || [];
    record._adopted = items.length > 0 && items.every(item => {
      const sourceId = item.run_id || item.job_id;
      const source = result.find(candidate => idOf(candidate) === sourceId);
      return source?.review_status === 'Accepted' && validation(source) === 'Passed';
    });
  }
  return result;
}

function recordState(record) {
  if (isActive(record)) return { status: 'Running', detail: 'Execution is in progress.' };
  if (REVIEW_FAILED.has(record.review_status)) {
    const note = record._reviewNote || record.review_note || record.feedback || record.note;
    return { status: 'Failed', detail: `${record.review_status}.${typeof note === 'string' && note.trim() ? ` ${note.trim()}` : ' Inspect the saved feedback and correct the result before continuing.'}` };
  }
  if (FAILED.has(record.execution_status) || ['Failed', 'Unsupported'].includes(validation(record))) {
    const message = record.error?.message || record.error || record.diagnostics?.find(item => item.severity === 'error')?.message;
    return { status: 'Failed', detail: typeof message === 'string' ? message :
      ['Cancelled', 'Canceled', 'Interrupted'].includes(record.execution_status) ? `${record.execution_status}. Read saved progress before explicitly retrying.` : 'Inspect the saved failure and choose repair or retry.' };
  }
  if (record.execution_status === 'Completed') {
    if ((record.review_status === 'Accepted' || record._adopted) && validation(record) === 'Passed') return { status: 'Complete', detail: 'The saved result passed and was accepted.' };
    return { status: 'Review required', detail: 'Execution finished. Inspect its checks and review the result.' };
  }
  return null;
}

function overlayValue(entry) {
  if (!entry) return null;
  const status = entry.status;
  return {
    status, label: status, detail: entry.detail || '', token: entry.token,
    reconnectRequired: !!entry.reconnectRequired, invalidated: !!entry.invalidated,
    recordId: entry.recordId || null, nodeId: entry.nodeId || null,
    execution_status: status === 'Not run' ? 'Not Run' : status === 'Running' ? 'Running' : status === 'Failed' ? 'Failed' : 'Completed',
    validation_status: status === 'Not run' ? 'Not Checked' : entry.backendValidation || (status === 'Complete' ? 'Passed' : status === 'Failed' ? 'Failed' : 'Not Checked'),
    review_status: status === 'Not run' ? 'Awaiting Review' : entry.backendReview || (status === 'Complete' ? 'Accepted' : 'Awaiting Review'),
    freshness: 'Current',
  };
}

/**
 * Scoped local display state bridges the click-to-HTTP-response gap and reloads.
 * Storage contains only identities/statuses, never RTL, prompts, or saved evidence.
 * readStorage(scope) -> object/string; writeStorage(scope, object) -> void.
 */
export class ExecutionStateTracker {
  constructor({ readStorage = () => null, writeStorage = () => {} } = {}) {
    this.readStorage = readStorage; this.writeStorage = writeStorage;
    this.scopeKey = null; this.entries = {}; this.known = {}; this.serial = 0;
  }

  setScope(scopeKey) {
    if (scopeKey === this.scopeKey) return;
    this.scopeKey = scopeKey || null; this.entries = {}; this.known = {}; this.serial = 0;
    if (!this.scopeKey) return;
    try {
      let saved = this.readStorage(this.scopeKey);
      if (typeof saved === 'string') saved = JSON.parse(saved);
      if (saved?.version === 1) {
        this.serial = Number.isSafeInteger(saved.serial) ? saved.serial : 0;
        for (const stage of STAGE_ORDER) {
          this.known[stage] = Array.isArray(saved.known?.[stage]) ? saved.known[stage].filter(id => typeof id === 'string') : [];
          const entry = saved.entries?.[stage];
          if (!entry || !['Not run', 'Running', 'Complete', 'Review required', 'Failed'].includes(entry.status)) continue;
          this.entries[stage] = clone(entry);
          if (entry.status === 'Running') Object.assign(this.entries[stage], { status: 'Failed', pending: false, reconnectRequired: true,
            detail: 'Connection was interrupted. Reconnect to saved progress; execution is not sent again.' });
        }
      }
    } catch { /* Unavailable/corrupt browser storage cannot block the workspace. */ }
  }

  persist() {
    if (!this.scopeKey) return;
    try { this.writeStorage(this.scopeKey, clone({ version: 1, serial: this.serial, entries: this.entries, known: this.known })); }
    catch { /* The in-memory status remains usable when browser storage is full. */ }
  }

  begin(action, token) {
    if (!this.scopeKey || action?.kind !== 'execute' || !STAGE_ORDER.includes(action.stageId)) return null;
    token ||= `${this.scopeKey}:execution:${++this.serial}`;
    const stageIndex = STAGE_ORDER.indexOf(action.stageId);
    for (let index = stageIndex + 1; index < STAGE_ORDER.length; index++) {
      const stage = STAGE_ORDER[index];
      this.entries[stage] = { status: 'Not run', invalidated: true, baseline: [...(this.known[stage] || [])],
        detail: 'An earlier stage was started again. Previous evidence remains in saved history.', causeToken: token };
    }
    this.entries[action.stageId] = { status: 'Running', detail: 'Starting execution. Waiting for saved progress.', token,
      scopeKey: this.scopeKey, nodeId: action.nodeId || null, requestId: action.requestId || null,
      pending: true, baseline: [...(this.known[action.stageId] || [])], recordIds: action.recordId ? [action.recordId] : [] };
    this.persist();
    return { id: token, scopeKey: this.scopeKey, stageId: action.stageId };
  }

  own(token) {
    if (!token || token.scopeKey !== this.scopeKey) return null;
    const entry = this.entries[token.stageId];
    return entry?.token === token.id ? entry : null;
  }

  success(token, response) {
    const entry = this.own(token); if (!entry) return false;
    entry.pending = false;
    this.receive(response, token.scopeKey);
    if (entry.status === 'Running' && !(entry.recordIds || []).length) {
      Object.assign(entry, { status: 'Failed', reconnectRequired: true,
        detail: 'The response did not identify saved execution progress. Reconnect before retrying; no automatic resend occurs.' });
    }
    this.persist(); return true;
  }

  failure(token, error) {
    const entry = this.own(token); if (!entry) return false;
    const uncertain = !(Number.isInteger(error?.status) && error.status >= 400);
    Object.assign(entry, { status: 'Failed', pending: false, reconnectRequired: uncertain,
      detail: `${error?.message || 'Execution request failed.'}${uncertain ? ' Reconnect to saved progress before retrying; the request is not resent.' : ''}` });
    this.persist(); return true;
  }

  /** A failed progress read cannot leave the UI claiming live observation. */
  observeFailure(error, stageId = null) {
    let changed = false;
    for (const stage of stageId ? [stageId] : STAGE_ORDER) {
      const entry = this.entries[stage];
      if (entry?.status !== 'Running') continue;
      Object.assign(entry, { status: 'Failed', pending: false, reconnectRequired: true,
        detail: `${error?.message || 'Saved progress could not be read.'} Reconnect to saved progress; execution is not sent again.` });
      changed = true;
    }
    if (changed) this.persist();
    return changed;
  }

  receive(envelope, scopeKey = this.scopeKey) {
    if (!scopeKey || scopeKey !== this.scopeKey) return false;
    const records = recordsFrom(envelope);
    if (idOf(envelope) && !stageOf(envelope)) {
      const stage = STAGE_ORDER.find(stage => (this.entries[stage]?.recordIds || []).includes(idOf(envelope)));
      if (stage) records.push({ ...envelope, stage_id: stage });
    }
    for (const stage of STAGE_ORDER) {
      const allStageRecords = records.filter(record => record.stage_id === stage);
      const stageRecords = allStageRecords.filter(record => record.freshness !== 'Stale');
      let entry = this.entries[stage];
      const staleOwn = entry?.recordId && allStageRecords.find(record => idOf(record) === entry.recordId && record.freshness === 'Stale');
      if (staleOwn && !entry.pending && !entry.reconnectRequired && ['Complete', 'Review required', 'Failed'].includes(entry.status)) {
        Object.assign(entry, { status: 'Not run', invalidated: true, reconnectRequired: false,
          baseline: [...new Set([...(entry.baseline || []), ...(this.known[stage] || []), ...allStageRecords.map(idOf)])],
          detail: 'The saved result belongs to earlier input. Run this stage for the current input; earlier evidence remains in history.' });
      }
      // A different browser may have completed work after this invalidation.
      // Reconcile only a new current latest record after the adopted cause;
      // old/history/status-only evidence cannot advance an explicitly rerun flow.
      // A runtime correction may also replace this browser's own now-stale run.
      const staleReplacement = !!(entry?.invalidated && staleOwn && !entry.pending && !entry.reconnectRequired &&
        (entry.recordIds || []).includes(entry.recordId));
      if (entry?.invalidated && (entry.causeToken || staleReplacement) && Array.isArray(envelope.workflow)) {
        const prior = STAGE_ORDER.slice(0, STAGE_ORDER.indexOf(stage));
        const summary = envelope.workflow.find(item => item.id === stage);
        const accepted = item => item?.execution_status === 'Completed' && item.validation_status === 'Passed' && item.review_status === 'Accepted' && item.freshness === 'Current';
        const cause = prior.map(id => this.entries[id]).find(item => item?.token === entry.causeToken);
        const boundaryTime = staleReplacement ? Date.parse(staleOwn.finished_at || staleOwn.created_at) :
          Date.parse(records.find(record => idOf(record) === cause?.recordId)?.created_at);
        const prerequisites = prior.every(id => accepted(envelope.workflow.find(item => item.id === id)) &&
          !this.entries[id]?.pending && !this.entries[id]?.reconnectRequired && !this.entries[id]?.invalidated &&
          !['Running', 'Failed', 'Review required'].includes(this.entries[id]?.status));
        const latest = summary?.latest_job_id || summary?.latest_run_id || summary?.latest_spec_id;
        if ((staleReplacement || cause?.status === 'Complete') && prerequisites && Number.isFinite(boundaryTime) &&
            summary?.execution_status === 'Completed' && summary.validation_status === 'Passed' && summary.freshness === 'Current') {
          const fresh = stageRecords.find(record => !record._batch && idOf(record) === latest &&
            (staleReplacement ? !(entry.recordIds || []).includes(idOf(record)) : !(entry.baseline || []).includes(idOf(record))) &&
            record.freshness === 'Current' &&
            record.execution_status === 'Completed' && validation(record) === 'Passed' &&
            Date.parse(record.created_at) > boundaryTime &&
            (record.review_status === 'Awaiting Review' || record.review_status === 'Accepted' && accepted(summary)));
          if (fresh) Object.assign(entry, recordState(fresh), { recordId: idOf(fresh), recordIds: [idOf(fresh)],
            invalidated: false, pending: false, reconnectRequired: false, backendExecution: fresh.execution_status,
            backendValidation: validation(fresh), backendReview: fresh.review_status });
        }
      }
      if (!entry) {
        const running = stageRecords.filter(isActive).at(-1);
        if (running) entry = this.entries[stage] = { status: 'Running', baseline: stageRecords.filter(record => idOf(record) !== idOf(running)).map(idOf), recordIds: [idOf(running)], recordId: idOf(running), nodeId: running.node_id || null };
      }
      if (entry && !entry.invalidated) {
        // New IDs are evidence of an execution after this display's invalidation.
        // A status change on an old record cannot make a downstream stage current.
        const pinned = entry.recordIds || [];
        const eligible = stageRecords.filter(record => pinned.includes(idOf(record)) || (!pinned.length && !(entry.baseline || []).includes(idOf(record))))
          .filter(record => !entry.requestId || !record._batch || !record.request_id || record.request_id === entry.requestId)
          .filter(record => !entry.nodeId || record._batch || !record.node_id || record.node_id === entry.nodeId);
        const active = eligible.filter(isActive).at(-1);
        const batches = eligible.filter(record => record._batch);
        const chosen = active || batches.at(-1) || eligible.at(-1);
        if (chosen) {
          const next = recordState(chosen);
          // Delayed Running polls may not regress a completed exact record.
          const terminalAlready = ['Complete', 'Review required', 'Failed'].includes(entry.status) && !entry.reconnectRequired && entry.recordId === idOf(chosen);
          if (next && !(terminalAlready && isActive(chosen))) {
            Object.assign(entry, next, { recordId: idOf(chosen), recordIds: [...new Set([...(entry.recordIds || []), ...eligible.map(idOf)])],
              pending: false, reconnectRequired: false, invalidated: false, backendExecution: chosen.execution_status,
              backendValidation: validation(chosen), backendReview: chosen.review_status });
          }
        }
      }
      this.known[stage] = [...new Set([...(this.known[stage] || []), ...allStageRecords.map(idOf)])];
    }
    this.persist(); return true;
  }

  overlay(stageId) { return overlayValue(this.entries[stageId]); }

  /** Clear only this browser ledger; never deletes backend evidence. */
  reset() { this.entries = {}; this.known = {}; this.serial = 0; this.persist(); }
}
