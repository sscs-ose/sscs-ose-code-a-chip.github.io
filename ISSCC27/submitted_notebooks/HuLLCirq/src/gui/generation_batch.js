import { element as el, field, badge } from './dom.js';
import { instructionView, promptMessagesView, repairGuidanceView, repairOutcomeLabel, repairProblemProjection, repairProblemsView } from './prompt_view.js';
import { availabilityReason } from './availability.js';

const active = value => value && ['Queued', 'Running'].includes(value.execution_status);
const batchSameRtlRecovery = run => {
  if (run?.stage_id !== 'local_synthesis') return '';
  if (run.error?.code === 'workflow_environment_error' && run.error.next_action === 'retry_same_RTL') return 'The tool execution environment failed. Fix setup and retry S05 using the same saved RTL; no RTL defect has been established.';
  if (run.execution_status === 'Failed' && run.validation_status === 'Not Checked' && run.error?.code === 'workflow_error'
      && run.checks && typeof run.checks === 'object' && !Array.isArray(run.checks) && Object.keys(run.checks).length === 0)
    return 'No tool checks were saved. The cause is not established. Inspect setup and the service, then retry S05 using the same saved RTL.';
  return '';
};
const card = (title, description, ...children) => el('section', { class: 'card generation-batch-card' },
  el('div', { class: 'card-heading' }, el('h2', { text: title }), el('p', { text: description })), ...children);
const number = value => Number.isFinite(value) ? value.toLocaleString('en-US') : 'Not recorded';
const repairMode = mode => ['synthesis_repair', 'netlist_repair'].includes(mode);
const repeatedGuidanceBlocked = guidance => !!guidance?.same_plan_repeated && !guidance.analysis_reviewed &&
  (Object.hasOwn(guidance, 'manual_correction_revised') ? !guidance.manual_correction_revised : !guidance.additional_instruction?.trim());

/** A single explicit start authorizes separate, sequential node requests. */
export class GenerationBatchWorkspace {
  constructor(callbacks) {
    this.callbacks = callbacks;
    this.batches = []; this.batchId = null; this.plan = null; this.selected = new Set(); this.repairSelected = new Set();
    this.previewSelection = null;
    this.generationDetailsIdentity = null; this.selectionOpen = null; this.nodeInstructionsOpen = false;
    this.instruction = ''; this.nodeInstructions = Object.create(null); this.synthesisNodeInstructions = Object.create(null); this.netlistNodeInstructions = Object.create(null); this.selectionEdited = false; this.repairSelectionEdited = false;
    this.busy = false; this.polling = false; this.pollTimer = null; this.pollError = null;
    this.startUncertain = false; this.requestId = null; this.token = 0; this.session = undefined;
    this.analysisJobs = []; this.analysisJobId = null; this.analysisPreview = null; this.analysisJobIds = {};
    this.analysisError = null; this.analysisStartUncertain = false; this.analysisRequestId = null;
    this.analysisPollTimer = null; this.analysisPolling = false;
  }
  project() { return this.callbacks.project(); }
  identity() { const p = this.project(); return JSON.stringify([p.envelope.workspace_identity?.session_id, p.design?.id]); }
  sourceIdentity() { const p = this.project(); return JSON.stringify([this.identity(), p.envelope.revision?.id, p.envelope.llm?.profile_revision_id]); }
  nodes() { return this.project().design.nodes || []; }
  nodeState(id) { return this.project().envelope.generation?.nodes?.find(node => node.node_id === id); }
  accepted(id) {
    const state = this.nodeState(id), job = this.project().envelope.generation?.jobs?.find(job => job.id === state?.accepted_job_id);
    return !!job && state.latest_job_id === job.id && job.freshness === 'Current' && job.review_status === 'Accepted';
  }
  synthesisAccepted(id) {
    const p = this.project(), state = this.nodeState(id);
    if (!this.accepted(id)) return false;
    const run = [...(p.envelope.workflow_runs || [])].reverse().find(item => item.node_id === id && item.stage_id === 'local_synthesis' && item.candidate_id === state.latest_job_id);
    return !!run && run.freshness === 'Current' && run.execution_status === 'Completed' && run.validation_status === 'Passed' && run.review_status === 'Accepted' && !!run.netlist;
  }
  failedSynthesis() {
    const p = this.project(), runs = p.envelope.workflow_runs || [], jobs = p.envelope.generation?.jobs || [];
    return this.nodes().flatMap(node => {
      const state = this.nodeState(node.id);
      // Only the backend may authorize using a pre-transport-failure candidate.
      // A failed request without RTL is not itself a new synthesis source.
      const recoverySource = (p.envelope.generation_batches?.repair_sources || []).find(source => source.node_id === node.id && source.latest_job_id === state?.latest_job_id && source.base_job_id === state?.accepted_job_id && source.recovery?.kind === 'no_rtl_transport_failure_v1');
      const candidate = jobs.find(job => job.id === (recoverySource?.base_job_id || state?.latest_job_id) && job.id === state?.accepted_job_id && job.freshness === 'Current' && (!recoverySource || job.rtl));
      const run = candidate && [...runs].reverse().find(run => run.node_id === node.id && run.stage_id === 'local_synthesis' && run.candidate_id === candidate.id && (!recoverySource || run.id === recoverySource.source_workflow_run_id));
      if (!run || run.freshness !== 'Current' || !run.finished_at || !['Completed', 'Failed'].includes(run.execution_status) || !(run.validation_status === 'Failed' || run.execution_status === 'Failed')) return [];
      const codes = [run.error?.code, ...(run.diagnostics || []).map(item => item.code)];
      const sameRtlRecovery = batchSameRtlRecovery(run);
      const setup = run.checks?.executed === false || codes.some(code => ['synthesizer_unavailable', 'invalid_synthesizer', 'unsupported_synthesizer'].includes(code));
      return [{ node, run, recovery: recoverySource?.recovery || null, sameRtlRecovery, blocked: sameRtlRecovery || (setup ? 'Correct the Yosys setup and rerun S05.' : '') }];
    });
  }
  failedNetlists() {
    return (this.project().envelope.generation_batches?.netlist_repair_sources || []).flatMap(source => {
      const node = this.nodes().find(node => node.id === source.node_id), state = this.nodeState(source.node_id);
      return node && state?.latest_job_id === source.latest_job_id && state?.accepted_job_id === source.base_job_id
        ? [{ node, source }] : [];
    });
  }
  receive(envelope) {
    const identity = this.identity(), switched = this.session !== undefined && this.session !== identity;
    if (switched) {
      this.token++; this.plan = null; this.batchId = null; this.selected.clear(); this.repairSelected.clear();
      this.previewSelection = null;
      this.generationDetailsIdentity = null; this.selectionOpen = null; this.nodeInstructionsOpen = false;
      this.selectionEdited = false; this.repairSelectionEdited = false; this.instruction = ''; this.nodeInstructions = Object.create(null); this.synthesisNodeInstructions = Object.create(null); this.netlistNodeInstructions = Object.create(null);
      this.busy = false; this.polling = false; this.pollError = null; this.startUncertain = false; this.requestId = null;
      this.analysisJobs = []; this.analysisJobId = null; this.analysisPreview = null; this.analysisJobIds = {};
      this.analysisError = null; this.analysisStartUncertain = false; this.analysisRequestId = null; this.analysisPolling = false;
      if (this.analysisPollTimer) clearTimeout(this.analysisPollTimer); this.analysisPollTimer = null;
      if (this.pollTimer) clearTimeout(this.pollTimer); this.pollTimer = null;
    }
    this.session = identity;
    this.batches = envelope.generation_batches?.batches || [];
    const savedAnalyses = envelope.repair_analysis?.jobs || [];
    this.analysisJobs = savedAnalyses.map(job => ({ ...this.analysisJobs.find(old => old.id === job.id), ...job }));
    if (!this.analysisPreview && (!this.analysisJobId || !this.analysisJobs.some(job => job.id === this.analysisJobId))) this.analysisJobId = envelope.repair_analysis?.active_job_id || this.analysisJobs.at(-1)?.id || null;
    if (!this.batchId || !this.batches.some(batch => batch.id === this.batchId)) this.batchId = envelope.generation_batches?.active_batch_id || envelope.generation_batches?.latest_batch_id || this.batches.at(-1)?.id || null;
    if (!this.selectionEdited) this.selected = new Set(this.nodes().filter(node => !this.accepted(node.id)).map(node => node.id));
    if (!this.repairSelectionEdited) this.repairSelected = new Set(this.failedSynthesis().filter(item => !item.blocked).map(item => item.node.id));
    this.selected = new Set([...this.selected].filter(id => this.nodes().some(node => node.id === id)));
    this.repairSelected = new Set([...this.repairSelected].filter(id => this.failedSynthesis().some(item => item.node.id === id && !item.blocked)));
    this.refresh(); this.schedule(); this.scheduleAnalysis();
  }
  selectedBatch() { return this.batches.find(batch => batch.id === this.batchId) || this.batches.at(-1); }
  activeBatch() { return this.batches.find(active); }
  unchangedRepair(item) {
    const envelope = this.project().envelope, jobs = envelope.generation?.jobs || [];
    const job = jobs.find(job => job.id === item.job_id), base = jobs.find(job => job.id === item.base_job_id);
    const source = (envelope.workflow_runs || []).find(run => run.id === item.source_workflow_run_id);
    if (item.operation !== 'repair' || !job || !base || job.operation !== 'repair' || job.base_job_id !== base.id ||
      job.node_id !== item.node_id || base.node_id !== item.node_id || job.execution_status !== 'Completed' || !job.finished_at ||
      typeof job.rtl_sha256 !== 'string' || !job.rtl_sha256 || job.rtl_sha256 !== base.rtl_sha256 ||
      source?.stage_id !== 'local_synthesis' || source.candidate_id !== base.id || source.validation_status !== 'Failed' || source.checks?.executed !== true) return null;
    return { job, base, source, current: job.freshness === 'Current' && this.nodeState(item.node_id)?.latest_job_id === job.id };
  }
  unchangedRepairs(batch) { return batch?.source_current === false ? [] : (batch?.items || []).filter(item => this.unchangedRepair(item)?.current && !this.synthesisAccepted(item.node_id)); }
  repairStatus(nodeId, run = null) {
    const state = this.project().envelope.workflow_nodes?.find(node => node.node_id === nodeId && (!node.stage_id || node.stage_id === 'local_synthesis'));
    const status = state?.repair_status, candidateId = this.nodeState(nodeId)?.latest_job_id;
    const current = run || this.failedSynthesis().find(item => item.node.id === nodeId)?.run;
    return status && status.candidate_id === candidateId && current?.id === status.run_id && current.freshness === 'Current' ? status : null;
  }
  repairOutcomeSummary() {
    const failures = this.failedSynthesis().filter(item => !item.blocked);
    const repeated = failures.map(item => ({ ...item, status: this.repairStatus(item.node.id, item.run) })).filter(item => item.status?.reconsideration_required);
    return { count: repeated.length, nodes: repeated.map(item => item.node.id), summary: repeated.map(item => `${item.node.name}: ${repairOutcomeLabel(item.status)} · ${this.failureExcerpt(item.run) || 'Diagnostic not recorded'}`).join('; ') };
  }
  gate() {
    const p = this.project(), envelope = p.envelope;
    if (p.readOnly || envelope.workspace_identity?.read_only) return 'This preserved system is read-only.';
    if (p.dirty || p.conflict) return 'Save or reopen the current design first.';
    if (envelope.generation?.storage_error || envelope.generation_batches?.storage_error || envelope.workflow_storage_error) return 'Resolve the saved-history storage error first.';
    if (this.startUncertain) return 'Reconnect to check whether the batch was saved. Do not start another request.';
    if (this.analysisStartUncertain) return 'Reconnect to check the saved guidance analysis. Do not resend it.';
    if (this.busy || p.busy || this.activeBatch() || p.postlayoutRunning || p.lvsRunning ||
      this.analysisJobs.some(active) ||
      (envelope.generation?.jobs || []).some(job => active(job) || job.execution_status === 'Completed' && !job.finished_at) ||
      [...(envelope.workflow_runs || []), ...(envelope.workflow_batches || [])].some(active) ||
      ['global_generation', 'global_workflow', 'physical_workflow', 'drc_workflow', 'lvs_workflow', 'postlayout_workflow'].some(key =>
        [...(envelope[key]?.runs || []), ...(envelope[key]?.jobs || [])].some(active))) return 'Wait for the active operation to finish, or cancel it.';
    if (!envelope.llm?.profile_revision_id) return 'Save an LLM provider profile in Global Settings.';
    if (this.callbacks.providerDirty?.()) return 'Save the edited provider settings in Global Settings first.';
    if (this.callbacks.providerGate?.()) return this.callbacks.providerGate();
    return '';
  }
  planCurrent() { return !!this.plan && this.planSource === this.sourceIdentity() && this.plan.revision_id === this.project().envelope.revision.id && this.plan.profile_revision_id === this.project().envelope.llm?.profile_revision_id && (this.plan.items || []).every(item => !Object.hasOwn(item, 'expected_latest_job_id') || (this.nodeState(item.node_id)?.latest_job_id || null) === item.expected_latest_job_id); }
  startGate() { return this.gate() || (!this.planCurrent() ? 'Preview this batch with the current saved design and provider.' : !this.plan.ready_to_start ? this.plan.gate_reason || 'Complete the requirements shown for each unsent request before starting.' : ''); }
  itemAvailability(item, reason = '') {
    return availabilityReason({ status: item?.status, code: item?.error?.code || item?.code,
      reason: reason || item?.reason || item?.error?.message, readiness: item?.readiness || item?.context?.readiness,
      kind: repeatedGuidanceBlocked(item?.repair_guidance) ? 'input_required' : item?.kind });
  }
  itemDisplayStatus(item) {
    // A preflight refusal has not executed. Keep a real saved failure distinct.
    if (['Blocked', 'Unsupported'].includes(item.status)) {
      const job = this.project().envelope.generation?.jobs?.find(job => job.id === item.job_id);
      if (job && (job.execution_status === 'Failed' || job.validation_status === 'Failed')) return 'Failed';
      return 'Not run';
    }
    return item.status;
  }
  itemReasonView(item, prefix) {
    if (!['Blocked', 'Unsupported'].includes(item.status)) return null;
    const reason = this.itemAvailability(item);
    return el('section', { 'data-testid': prefix, class: 'generation-availability' },
      badge(reason.label, 'orange'), el('small', { text: reason.message }),
      reason.actionLabel ? el('small', { text: `Next: ${reason.actionLabel}.` }) : null);
  }
  selectionChanged() { this.plan = null; this.previewSelection = null; this.token++; this.refresh(); this.callbacks.chrome?.(); }
  focus() { const host = this.project().stage === 'local_synthesis' ? this.repairHost : this.generationHost; host?.scrollIntoView?.({ behavior: 'smooth', block: 'start' }); }
  readPreviewInstructions() {
    const target = this.generationHost?.querySelector('[data-testid="generation-batch-readable-request"]');
    target?.scrollIntoView?.({ behavior: 'smooth', block: 'start' }); target?.focus?.({ preventScroll: true });
  }
  focusUnresolvedProblems() {
    const host = this.project().stage === 'local_synthesis' ? this.repairHost : this.generationHost;
    const target = host?.querySelector('[data-testid="repair-unresolved-problems"]');
    target?.scrollIntoView?.({ behavior: 'smooth', block: 'start' }); target?.focus?.({ preventScroll: true });
  }
  repairItemCurrent(item) {
    if (item.netlist_repair_evidence) return this.failedNetlists().some(({ source }) =>
      source.node_id === item.node_id && source.base_job_id === item.base_job_id && source.latest_job_id === item.expected_latest_job_id
      && source.source_workflow_run_id === item.source_workflow_run_id
      && source.netlist_repair_evidence?.frozen_plan?.sha256 === item.netlist_repair_evidence.frozen_plan?.sha256);
    const savedSource = item.display_source === 'authoritative_saved_source' && (this.project().envelope.generation_batches?.repair_sources || []).find(source =>
      source.node_id === item.node_id && source.base_job_id === item.base_job_id && source.latest_job_id === item.expected_latest_job_id && source.source_workflow_run_id === item.source_workflow_run_id && source.repair_explanation === item.repair_explanation);
    if (!savedSource && !this.planCurrent()) return false;
    const source = repairProblemProjection(item).source || {};
    const failed = this.failedSynthesis().find(failure => failure.node.id === item.node_id && failure.run.id === item.source_workflow_run_id && failure.run.candidate_id === item.base_job_id);
    const state = this.nodeState(item.node_id), revisionId = savedSource ? this.project().envelope.revision?.id : this.plan.revision_id;
    return !!failed && (!savedSource || state?.latest_job_id === item.expected_latest_job_id && state?.accepted_job_id === item.base_job_id) && (!source.node_id || source.node_id === item.node_id) &&
      (!source.candidate_id || source.candidate_id === item.base_job_id) && (!source.run_id || source.run_id === item.source_workflow_run_id) &&
      (!source.revision_id || source.revision_id === revisionId) &&
      (!source.rtl_sha256 || !failed.run.rtl_sha256 || source.rtl_sha256 === failed.run.rtl_sha256);
  }
  repairProblemSummary(items) {
    return items.map(item => {
      const projection = repairProblemProjection(item), issue = projection.issues?.[0], diagnostic = issue?.diagnostic || issue;
      return `${item.node_name || item.node_id}: ${diagnostic?.raw_message || diagnostic?.message || 'Inspect the saved S05 diagnostic'}`;
    }).join('; ');
  }
  superseded(batch) {
    const jobs = this.project().envelope.generation?.jobs || [];
    return (batch?.items || []).some(item => item.job_id && jobs.some(job => job.id === item.job_id && job.node_id === item.node_id) && this.nodeState(item.node_id)?.latest_job_id !== item.job_id && this.accepted(item.node_id));
  }
  discardPreview() {
    if (this.busy || this.activeBatch() || this.startUncertain) return false;
    this.plan = null; this.previewSelection = null; this.refresh(); this.callbacks.chrome?.();
    return true;
  }
  rebuildPlan() {
    const selection = this.plan ? { mode: this.plan.mode, nodeIds: (this.plan.items || []).map(item => item.node_id), retryBatchId: this.plan.retry_of_batch_id || null }
      : this.previewSelectionCurrent() ? this.previewSelection : null;
    if (!selection) { this.callbacks.toast?.('Prepare a preview for the selected nodes first.'); return; }
    return this.prepare(selection.mode, [...selection.nodeIds], false, selection.retryBatchId);
  }
  previewSelectionCurrent() { return !!this.previewSelection && this.previewSelection.identity === this.identity() && this.previewSelection.revisionId === this.project().envelope.revision?.id; }
  budgetForItem(item) {
    if (item?.context_budget) return item.context_budget;
    const plan = this.plan, context = (item === plan?.items?.[0] ? plan?.first_request_context : null) || item?.context || {}, profile = plan?.profile || {};
    // Old blocked previews sometimes retained only the un-packed base context.
    // Never advertise its subtraction as the complete request's output ceiling.
    if (item?.status === 'Blocked' && !context.batch_context) return { base_input_estimated_tokens: context.provider_input_estimated_tokens ?? context.estimated_input_tokens, max_output_tokens: profile.max_output_tokens, context_window: profile.context_window };
    const input = context.provider_input_estimated_tokens ?? context.estimated_input_tokens;
    return { provider_input_estimated_tokens: input, max_output_tokens: profile.max_output_tokens, context_window: profile.context_window, maximum_output_tokens: Number.isFinite(input) && Number.isFinite(profile.context_window) ? Math.max(0, profile.context_window - input) : null };
  }
  itemBudget(item) {
    if (item?.status === 'Blocked' && !item.context_budget && !item.context && repeatedGuidanceBlocked(item.repair_guidance)) return 'No request prepared: review unresolved problems and revise the repair guidance first.';
    const budget = this.budgetForItem(item), input = budget.provider_input_estimated_tokens;
    if (!Number.isFinite(input)) return `Saved base input ${number(budget.base_input_estimated_tokens)} · output limit ${number(budget.max_output_tokens)} · context ${number(budget.context_window)} tokens. Complete provider input including conversation was not recorded; rebuild the preview to calculate its limit.`;
    const total = Number.isFinite(budget.total_estimated_tokens) ? budget.total_estimated_tokens : Number.isFinite(budget.max_output_tokens) ? input + budget.max_output_tokens : null;
    const maximum = budget.maximum_output_tokens;
    if (budget.scope === 'base_contract') return `Base input ${number(input)} + output limit ${number(budget.max_output_tokens)} = ${number(total)} / context ${number(budget.context_window)} tokens. Later conversation is packed within the remaining budget when this node executes; its exact request is not prepared yet.`;
    return `Estimated provider input ${number(input)} + output limit ${number(budget.max_output_tokens)} = ${number(total)} / context ${number(budget.context_window)} tokens${Number.isFinite(maximum) ? ` · maximum output for this request ${number(maximum)}` : ''}${Number.isFinite(budget.ledger_input_estimated_tokens) ? ` · conversation references ${number(budget.ledger_input_estimated_tokens)} · retained turns ${number(budget.retained_history_input_estimated_tokens)}` : ''}.`;
  }
  planBudget() {
    const item = this.plan?.items?.find(item => item.status === 'Blocked') || this.plan?.items?.[0];
    return `${item?.node_name || item?.node_id ? `${item.node_name || item.node_id} · ` : ''}${this.itemBudget(item)}`;
  }
  guidance({ singleRequestPrepared = false } = {}) {
    const result = this.queueGuidance({ singleRequestPrepared });
    if (!result) return null;
    const batch = this.activeBatch() || this.batches.at(-1), failures = this.failedSynthesis();
    const nodes = this.plan?.items || (this.previewSelectionCurrent() ? this.previewSelection.nodeIds.map(id => ({ node_id: id, node_name: this.nodes().find(node => node.id === id)?.name || id }))
      : failures.length ? failures.map(item => ({ node_id: item.node.id, node_name: item.node.name })) : batch?.items || []);
    return { ...result, scope: result.scope || (nodes.length === 1 ? `Request queue: ${nodes[0].node_name || nodes[0].node_id}` : `Request queue: ${nodes.length} nodes`) };
  }
  queueGuidance({ singleRequestPrepared = false } = {}) {
    // History selection changes the inspected evidence, not the next action.
    const batch = this.activeBatch() || this.batches.at(-1);
    if (this.analysisStartUncertain || this.analysisError) return { tone: 'warning', title: 'Inspect the saved guidance analysis', summary: this.analysisError || 'The analysis start response was not confirmed. Reconnect without resending.', primary: { label: 'Reconnect analysis without resending', action: () => this.pollAnalysis(true) } };
    if (this.analysisJobs.some(active)) return { tone: 'neutral', title: 'Repair guidance is being analyzed', summary: 'One explicit analysis request is running. It proposes changes only; the RTL is unchanged.', primary: { label: 'View guidance analysis', action: () => this.focusAnalysis() } };
    if (this.analysisPreview && !this.analysisCurrent(this.analysisPreview)) {
      if (this.analysisSourceCurrent(this.analysisPreview)) return { tone: 'warning', title: 'Rebuild analysis with the saved LLM settings', summary: 'The provider settings changed. Rebuild the unsent preview to calculate its current input/output budget; no request is sent.', primary: { label: 'Rebuild analysis preview', disabled: !!this.gate(), action: () => this.rebuildAnalysisPreview() }, secondary: { label: 'Read earlier analysis request', action: () => this.focusAnalysis() } };
      return { tone: 'warning', title: 'Discard the earlier analysis preview', summary: 'Its source changed. Discard it, then preview analysis for the current failed candidate.', primary: { label: 'Discard stale analysis preview', action: () => { this.analysisPreview = null; this.refresh(); this.callbacks.chrome?.(); } }, secondary: { label: 'Read earlier analysis request', action: () => this.focusAnalysis() } };
    }
    if (this.analysisPreview && !this.analysisPreview.ready_to_start) return { tone: 'warning', title: 'Adjust the analysis context budget', summary: this.analysisPreview.gate_reason || 'The exact request does not fit the saved context window. Current source is complete; no model request was sent.', primary: { label: 'Open LLM settings', action: () => this.callbacks.navigate?.('global_settings') }, secondary: { label: 'Read analysis budget', action: () => this.focusAnalysis() } };
    if (this.analysisPreview) return { tone: 'neutral', title: 'Inspect the analysis request before sending', summary: this.analysisPreview.gate_reason || 'This separate request proposes a repair method. It does not change RTL.', primary: { label: 'Start guidance analysis', disabled: !!this.gate() || !this.analysisPreview.ready_to_start, action: () => this.startAnalysis() }, secondary: { label: 'Read analysis request', action: () => this.focusAnalysis() } };
    const analysis = this.selectedAnalysis();
    if (analysis?.execution_status === 'Completed' && analysis.proposal && this.analysisCurrent(analysis) && this.analysisJobIds[analysis.source.node_id] !== analysis.id) return { tone: 'neutral', title: 'Review the proposed repair guidance', summary: 'Inspect the saved proposal and raw answer below. Apply reviewed guidance to prepare a fresh RTL repair preview; no repair is sent by analysis.', primary: { label: 'Review proposed guidance', action: () => this.focusAnalysis() } };
    if (this.startUncertain || this.pollError) return { tone: 'warning', title: 'Reconnect to the saved generation batch', summary: this.pollError || 'The start response was not received. Check saved progress before another request.', primary: { label: 'Reconnect without resending', action: () => this.reconnect() } };
    if (active(batch)) return { tone: 'neutral', title: 'Sequential RTL requests are running', summary: `${batch.completed_count || 0}/${batch.required_node_count || batch.items?.length || 0} nodes processed. Inspect each result below; previous conversation is retained within the saved context budget.`, primary: { label: 'View generation batch', action: () => this.focus() } };
    if (!this.plan && this.previewSelectionCurrent()) return { tone: 'warning', title: 'Rebuild the edited request preview', summary: `The instruction changed. Rebuild the same ${this.previewSelection.nodeIds.length} selected node request(s), then inspect the new budget before sending.`, primary: { label: repairMode(this.previewSelection.mode) ? 'Rebuild repair preview' : 'Rebuild generation preview', disabled: !!this.gate(), action: () => this.rebuildPlan() } };
    if (this.plan && !this.planCurrent() && this.nodes().length && this.nodes().every(node => this.accepted(node.id))) {
      const synthesized = this.nodes().every(node => this.synthesisAccepted(node.id));
      return { tone: synthesized ? 'success' : 'neutral', title: synthesized ? 'S04 and S05 are complete for the current RTL' : 'Continue the current RTL to S05',
        summary: synthesized ? 'All current RTL and synthesis results are accepted. Continue to S06. The earlier unsent preview remains available for inspection or rebuilding.' : 'All current RTL is accepted. Open S05 to synthesize or inspect its current results. The earlier unsent preview remains available for inspection or rebuilding.',
        primary: { label: synthesized ? 'Continue to Netlist Simulation' : 'Open Local Synthesis', action: () => this.callbacks.navigate?.(synthesized ? 'local_netlist_simulation' : 'local_synthesis') },
        secondary: { label: 'Inspect saved preview', action: () => this.focus() } };
    }
    if (this.plan) {
      const gate = this.startGate(), repair = repairMode(this.plan.mode);
      const recoverable = repair && this.failedSynthesis().filter(item => item.recovery && !item.blocked);
      if (gate && recoverable?.length && !this.gate()) return { tone: 'warning', title: 'Rebuild the repair retries after connection failure', summary: `${recoverable.length} request(s) returned no RTL. Their original RTL and S05 diagnostics are preserved. Rebuild with the saved provider settings; inspect the new complete input budget before starting.`, primary: { label: `Preview all ${recoverable.length} repair retries`, action: () => this.prepare('synthesis_repair', this.failedSynthesis().filter(item => !item.blocked).map(item => item.node.id), false) }, secondary: { label: 'Open LLM settings', action: () => this.callbacks.navigate?.('global_settings') } };
      const repeated = repair && this.plan.items?.find(item => repeatedGuidanceBlocked(item.repair_guidance));
      if (gate && repeated && this.planCurrent() && !this.gate()) return { tone: 'warning', title: 'Inspect the problems left by the previous repair', summary: `${this.repairProblemSummary(this.plan.items.filter(item => item.operation === 'repair'))}. The request is paused because the same repair guidance was repeated; this is not a new synthesis error.`, primary: { label: 'Inspect unresolved problems', action: () => this.focusUnresolvedProblems() }, secondary: { label: 'Edit repair instruction', action: () => this.focusRepairInstruction() } };
      const unknown = repair && this.plan.items?.find(item => item.repair_guidance?.analysis_required && !item.repair_guidance.analysis_reviewed && !item.repair_guidance.additional_instruction?.trim());
      if (gate && unknown && this.planCurrent()) return { tone: 'warning', title: 'Prepare a concrete repair method', summary: 'No qualified rule matched this diagnostic. Add a correction instruction or preview a separate model analysis; RTL is unchanged.', primary: { label: 'Preview guidance analysis', disabled: !!this.gate(), action: () => this.previewAnalysis(unknown) }, secondary: { label: 'Read repair guidance', action: () => this.readPreviewInstructions() } };
      if (gate) {
        const item = this.plan.items?.find(item => ['Blocked', 'Unsupported'].includes(item.status)), reason = this.itemAvailability(item, item?.reason || gate);
        const implementation = reason.kind === 'implementation';
        const settings = ['configuration', 'connection'].includes(reason.kind);
        return { tone: 'warning', title: `${reason.label} · request not sent`, summary: `${reason.message}${implementation ? '' : ` ${this.planBudget()}`}`,
          primary: implementation ? { label: 'Inspect saved requirements', action: () => this.readPreviewInstructions() } :
            settings ? { label: 'Open LLM settings', action: () => this.callbacks.navigate?.('global_settings') } :
            { label: repair ? 'Rebuild repair preview' : 'Rebuild generation preview', disabled: !!this.gate(), action: () => this.rebuildPlan() },
          secondary: implementation ? undefined : { label: 'Read request instructions', action: () => this.readPreviewInstructions() } };
      }
      return { tone: 'neutral', title: repair ? 'Start the prepared repair batch' : 'Start the prepared generation batch', summary: 'One start sends one request per queued node, in order, with bounded conversation context retained between requests.', primary: { label: repair ? 'Start repair batch' : 'Start generation batch', action: () => this.start() }, secondary: { label: repair ? 'Read repair instructions' : 'Read request instructions', action: () => this.readPreviewInstructions() } };
    }
    if (singleRequestPrepared) return null;
    const failures = this.failedSynthesis(), repairable = failures.filter(item => !item.blocked);
    const recoverable = repairable.filter(item => item.recovery);
    if (recoverable.length) return { tone: 'warning', title: 'Retry repairs that returned no RTL', summary: `${recoverable.length} request(s) failed during connection or transport. No replacement RTL was produced; the original RTL and failed S05 sources remain available. Preview the repair retries, then start them explicitly.`, primary: { label: `Preview all ${repairable.length} repair retries`, disabled: !!this.gate(), action: () => this.prepare('synthesis_repair', repairable.map(item => item.node.id), false) }, secondary: { label: 'Open LLM settings', action: () => this.callbacks.navigate?.('global_settings') } };
    const repeat = this.repairOutcomeSummary();
    if (repeat.count) return { tone: 'warning', title: 'Reconsider the repeated repair', summary: `${repeat.summary}. Read the actual errors and source below before revising the correction.`, primary: { label: 'Inspect unresolved problems', action: () => this.focusUnresolvedProblems() }, secondary: { label: 'Inspect failed synthesis', action: () => this.callbacks.navigate?.('local_synthesis', repeat.nodes[0]) } };
    if (repairable.length) return { tone: 'warning', title: 'Repair the RTL that failed S05', summary: `${repairable.length} current failed node(s): ${repairable.map(item => item.node.name).join(', ')}. Preview their saved synthesis diagnostics, then start the repair requests.`, primary: { label: `Preview repairs for ${repairable.length} failed node${repairable.length === 1 ? '' : 's'}`, disabled: !!this.gate(), action: () => this.prepare('synthesis_repair', repairable.map(item => item.node.id), false) }, secondary: { label: 'Inspect failed synthesis', action: () => this.callbacks.navigate?.('local_synthesis', repairable[0].node.id) } };
    if (failures.length && failures.every(item => item.sameRtlRecovery)) return { tone: 'warning', title: 'Retry S05 using the same saved RTL', summary: failures[0].sameRtlRecovery, primary: { label: 'Open S05 · retry the same RTL', action: () => this.callbacks.navigate?.('local_synthesis', failures[0].node.id) } };
    if (failures.length) return { tone: 'warning', title: 'Correct the S05 tool setup', summary: failures[0].blocked, primary: { label: 'Inspect failed synthesis', action: () => this.callbacks.navigate?.('local_synthesis', failures[0].node.id) } };
    const repairedWithoutSynthesis = batch?.mode === 'netlist_repair' && batch.source_current !== false && batch.execution_status === 'Completed' && batch.validation_status === 'Passed'
      ? (batch.items || []).filter(item => item.job_id && item.job_id === this.nodeState(item.node_id)?.latest_job_id && this.accepted(item.node_id) && !this.synthesisAccepted(item.node_id)) : [];
    if (repairedWithoutSynthesis.length) return { tone: 'success', title: 'Continue the repaired RTL to S05', summary: `${repairedWithoutSynthesis.length} repaired candidate(s) are accepted in S04. S05 has no adopted result for these exact candidates yet; continue synthesis before rerunning their S06 checks.`, primary: { label: 'Open Local Synthesis', action: () => this.callbacks.navigate?.('local_synthesis', repairedWithoutSynthesis[0].node_id) }, secondary: { label: 'Inspect repair batch results', action: () => this.focus() } };
    const netlistFailures = this.failedNetlists();
    if (netlistFailures.length) return { tone: 'warning', scope: netlistFailures.length === 1 ? `Request queue: ${netlistFailures[0].node.name}` : `Request queue: ${netlistFailures.length} nodes`, title: 'Repair the RTL that failed S06', summary: `${netlistFailures.length} node(s) failed actual netlist checks. Preview one repair request per node with its exact S05 netlist and saved S06 failure.`, primary: { label: `Preview repairs for ${netlistFailures.length} failed netlists`, disabled: !!this.gate(), action: () => this.prepare('netlist_repair', netlistFailures.map(item => item.node.id), false) }, secondary: { label: 'Inspect netlist results', action: () => this.callbacks.navigate?.('local_netlist_simulation', netlistFailures[0].node.id) } };
    if (batch && batch.source_current !== false) {
      const pending = this.remaining(batch);
      if (pending.length && pending.every(item => ['Blocked', 'Unsupported'].includes(item.status) && this.itemAvailability(item).kind === 'implementation')) return {
        tone: 'warning', title: 'Not implemented · requests not sent',
        summary: pending.map(item => `${item.node_name || item.node_id}: ${this.itemAvailability(item).message}`).join(' '),
        primary: { label: 'Inspect saved request details', action: () => this.focus() } };
      if (pending.length) return { tone: 'warning', title: 'Some RTL requests need attention', summary: `${pending.length} node(s) remain unresolved. Inspect their saved results, then preview a new batch for those nodes. No request is automatically repeated.`, primary: { label: 'Preview remaining requests', disabled: !!this.gate(), action: () => this.prepareRemaining(batch) }, secondary: { label: 'Inspect batch results', action: () => this.focus() } };
      const unchanged = this.unchangedRepairs(batch);
      if (batch.execution_status === 'Completed' && unchanged.length) return { tone: 'warning', title: 'Some repairs returned unchanged RTL', summary: `${unchanged.length} repair(s) returned the same RTL as their failed ${batch.mode === 'netlist_repair' ? 'S06' : 'S05'} source. External-interface acceptance remains valid; the prior failure has not been corrected. Preview fresh generation for these nodes, or inspect their saved results.`, primary: { label: 'Preview fresh generation', disabled: !!this.gate(), action: () => this.prepare('generate', unchanged.map(item => item.node_id), false) }, secondary: { label: 'Open Local Synthesis', action: () => this.callbacks.navigate?.('local_synthesis') } };
      if (batch.execution_status === 'Completed' && this.nodes().length && this.nodes().every(node => this.accepted(node.id))) {
        if (this.nodes().every(node => this.synthesisAccepted(node.id))) return { tone: 'success', title: 'S04 and S05 are complete for the current RTL', summary: 'All current node RTL and synthesis results are accepted. Continue to S06 to verify the synthesized circuit behavior.', primary: { label: 'Continue to Netlist Simulation', action: () => this.callbacks.navigate?.('local_netlist_simulation') }, secondary: { label: 'Inspect synthesis results', action: () => this.callbacks.navigate?.('local_synthesis') } };
        return { tone: 'success', title: 'Continue the generated RTL to S05', summary: 'The queued S04 requests finished. Run synthesis to check the repaired or generated RTL; external-interface acceptance does not establish synthesis or circuit behavior.', primary: { label: 'Open Local Synthesis', action: () => this.callbacks.navigate?.('local_synthesis') }, secondary: { label: 'Inspect batch results', action: () => this.focus() } };
      }
    }
    return null;
  }
  focusRepairInstruction() {
    const host = this.project().stage === 'local_synthesis' ? this.repairHost : this.generationHost;
    const target = host?.querySelector('[data-testid="workflow-batch-repair-instruction"]') || host?.querySelector('[data-testid="generation-batch-instruction"]');
    target?.scrollIntoView?.({ behavior: 'smooth', block: 'center' }); target?.focus?.({ preventScroll: true });
  }
  focusAnalysis() {
    const target = this.generationHost?.querySelector('[data-testid="repair-analysis-panel"]');
    target?.scrollIntoView?.({ behavior: 'smooth', block: 'start' }); target?.focus?.({ preventScroll: true });
  }
  remaining(batch) { return (batch.items || []).filter(item => !['Accepted', 'Passed', 'Skipped'].includes(item.status) && !(item.job_id && this.nodeState(item.node_id)?.latest_job_id !== item.job_id && this.accepted(item.node_id))); }
  prepareRemaining(batch) { return this.prepare(batch.mode, this.remaining(batch).map(item => item.node_id), false, batch.id); }
  nodeInstructionDrafts(mode) {
    return mode === 'synthesis_repair' ? this.synthesisNodeInstructions : mode === 'netlist_repair' ? this.netlistNodeInstructions : this.nodeInstructions;
  }
  editNodeInstruction(mode, nodeId, value) {
    this.nodeInstructionDrafts(mode)[nodeId] = value;
    this.plan = null; this.token++; this.updateButtons(); this.callbacks.chrome?.();
  }
  async prepare(mode = 'generate', ids = null, navigate = true, retryBatchId = null) {
    if (this.gate()) return;
    const nodeIds = ids || (mode === 'netlist_repair' ? this.failedNetlists().map(item => item.node.id) : [...(mode === 'synthesis_repair' ? this.repairSelected : this.selected)]);
    if (!nodeIds.length) { this.callbacks.toast?.('Select at least one node.'); return; }
    const identity = this.sourceIdentity(), token = ++this.token;
    this.busy = true; this.refresh();
    try {
      const analysisIds = Object.fromEntries(nodeIds.filter(id => this.analysisJobIds[id] && this.analysisCurrent(this.analysisJobs.find(job => job.id === this.analysisJobIds[id]))).map(id => [id, this.analysisJobIds[id]]));
      const drafts = this.nodeInstructionDrafts(mode);
      const nodeInstructions = !retryBatchId ? Object.fromEntries(nodeIds.filter(id => drafts[id]?.trim()).map(id => [id, drafts[id]])) : {};
      const plan = await this.callbacks.request('generation/batches/preview', { revision_id: this.project().envelope.revision.id, mode, node_ids: nodeIds, instruction: this.instruction, ...(retryBatchId ? { retry_batch_id: retryBatchId } : {}), ...(repairMode(mode) && Object.keys(analysisIds).length ? { analysis_job_ids: analysisIds } : {}), ...(Object.keys(nodeInstructions).length ? { node_instructions: nodeInstructions } : {}) });
      if (identity !== this.sourceIdentity() || token !== this.token) return;
      this.plan = plan; this.planSource = identity; this.pollError = null;
      this.previewSelection = { mode, nodeIds: (plan.items || []).map(item => item.node_id), retryBatchId: retryBatchId || null, identity: this.identity(), revisionId: plan.revision_id };
      if (mode === 'netlist_repair') { this.analysisPreview = null; this.analysisError = null; }
      if (navigate && repairMode(mode)) this.callbacks.navigate?.('local_rtl_generation');
      const unavailable = !plan.ready_to_start && this.itemAvailability(plan.items?.find(item => ['Blocked', 'Unsupported'].includes(item.status)), plan.gate_reason);
      this.callbacks.toast?.(plan.ready_to_start ? 'Batch preview ready. Inspect the queue, then start once for all queued requests.' : `${unavailable.label}: ${unavailable.message} No model request was sent.`);
    } catch (error) { if (identity === this.sourceIdentity() && token === this.token) this.callbacks.notify?.(error.message, 'error'); }
    finally { if (token === this.token) { this.busy = false; this.refresh(); this.callbacks.chrome?.(); } }
  }
  analysisCurrent(job) {
    const source = job?.source, state = source && this.nodeState(source.node_id);
    const netlist = source?.stage_id === 'local_netlist_simulation' && this.failedNetlists().find(item =>
      item.node.id === source.node_id && item.source.source_workflow_run_id === source.run_id && item.source.base_job_id === source.candidate_id);
    const failed = netlist ? { recovery: netlist.source.recovery } : source?.stage_id === 'local_netlist_simulation' ? null : source && this.failedSynthesis().find(item => item.node.id === source.node_id && item.run.id === source.run_id && item.run.candidate_id === source.candidate_id);
    return !!source && source.candidate_id === state?.accepted_job_id &&
      (source.candidate_id === state?.latest_job_id || !!failed?.recovery) && !!failed &&
      (!job.profile_revision_id || job.profile_revision_id === this.project().envelope.llm?.profile_revision_id);
  }
  analysisSourceCurrent(value) { return !!value && this.analysisCurrent({ ...value, profile_revision_id: this.project().envelope.llm?.profile_revision_id }); }
  async rebuildAnalysisPreview() {
    const preview = this.analysisPreview;
    if (this.gate() || !this.analysisSourceCurrent(preview)) return;
    return this.previewAnalysisRun(preview.source.run_id);
  }
  selectedAnalysis() { return this.analysisJobs.find(job => job.id === this.analysisJobId); }
  saveAnalysis(job) {
    const index = this.analysisJobs.findIndex(saved => saved.id === job.id);
    if (index >= 0) this.analysisJobs[index] = { ...this.analysisJobs[index], ...job }; else this.analysisJobs.push(job);
    if (!this.analysisPreview || job.context_id === this.analysisPreview.context_id) this.analysisJobId = job.id;
  }
  publishAnalysis() {
    this.callbacks.envelope?.({ ...this.project().envelope, repair_analysis: { ...this.project().envelope.repair_analysis, jobs: this.analysisJobs, active_job_id: this.analysisJobs.find(active)?.id || null } });
  }
  async previewAnalysis(item) {
    if (this.gate() || !this.repairItemCurrent(item) || !item.source_workflow_run_id) return;
    return this.previewAnalysisRun(item.source_workflow_run_id);
  }
  async previewAnalysisRun(runId) {
    const identity = this.sourceIdentity(), token = ++this.token; this.busy = true; this.refresh();
    let prepared = null;
    try {
      const preview = await this.callbacks.request('repair-analysis/preview', { run_id: runId });
      if (identity !== this.sourceIdentity() || token !== this.token) return;
      this.analysisPreview = preview; this.analysisJobId = null; this.analysisError = null; this.analysisRequestId = null; prepared = preview;
      this.callbacks.toast?.(preview.ready_to_start ? 'Analysis preview ready. Inspect its request, then start analysis.' : `${preview.gate_reason || 'Analysis does not fit the saved context window.'} No model request was sent.`);
    } catch (error) { if (identity === this.sourceIdentity() && token === this.token) this.callbacks.notify?.(error.message, 'error'); }
    finally { if (identity === this.sourceIdentity() && token === this.token) { this.busy = false; this.refresh(); this.callbacks.chrome?.(); if (prepared && this.analysisPreview === prepared) this.focusAnalysis(); } }
  }
  async startAnalysis() {
    const preview = this.analysisPreview;
    if (this.gate() || !preview?.ready_to_start || !this.analysisCurrent(preview)) return;
    const identity = this.sourceIdentity(), token = ++this.token;
    this.analysisRequestId ||= crypto.randomUUID(); const requestId = this.analysisRequestId;
    this.busy = true; this.refresh();
    try {
      const job = await this.callbacks.request('repair-analysis/start', { context_id: preview.context_id, request_id: requestId });
      if (identity !== this.sourceIdentity() || token !== this.token) return;
      this.saveAnalysis(job); this.analysisPreview = null; this.analysisError = null; this.analysisStartUncertain = false; this.analysisRequestId = null;
      this.publishAnalysis();
      this.callbacks.toast?.('Guidance analysis started. It proposes changes and does not generate or replace RTL.');
    } catch (error) {
      if (identity !== this.sourceIdentity() || token !== this.token) return;
      this.analysisStartUncertain = !error.status || error.status >= 500;
      this.analysisError = this.analysisStartUncertain ? `${error.message} Reconnect before another request.` : error.message;
      this.callbacks.notify?.(error.message, 'error');
    } finally { if (identity === this.sourceIdentity() && token === this.token) { this.busy = false; this.refresh(); this.callbacks.chrome?.(); this.scheduleAnalysis(); } }
  }
  async pollAnalysis(reconnect = false) {
    if (this.analysisPolling) return;
    const identity = this.identity(), job = this.analysisJobs.find(active) || this.selectedAnalysis();
    if (!job && !reconnect) return;
    this.analysisPolling = true;
    try {
      if (job) {
        const updated = await this.callbacks.request(`repair-analysis/jobs/${encodeURIComponent(job.id)}`);
        if (identity !== this.identity()) return;
        this.saveAnalysis(updated);
        this.publishAnalysis();
      }
      if (reconnect || !active(this.selectedAnalysis())) {
        const envelope = await this.callbacks.request('project');
        if (identity !== this.identity()) return;
        const recovered = this.analysisRequestId && envelope.repair_analysis?.jobs?.find(saved => saved.request_id === this.analysisRequestId);
        if (recovered) { this.saveAnalysis(recovered); this.analysisPreview = null; this.analysisRequestId = null; }
        this.analysisStartUncertain = false; this.callbacks.envelope(envelope);
      }
      this.analysisError = null; this.refresh(); this.callbacks.chrome?.();
    } catch (error) { if (identity === this.identity()) { this.analysisError = `${error.message} Analysis was not resent.`; this.refresh(); } }
    finally { if (identity === this.identity()) { this.analysisPolling = false; this.scheduleAnalysis(); } }
  }
  scheduleAnalysis() {
    if (this.analysisPollTimer || this.analysisPolling || this.analysisError || !this.analysisJobs.some(active)) return;
    this.analysisPollTimer = setTimeout(() => { this.analysisPollTimer = null; this.pollAnalysis(); }, 1300);
  }
  async cancelAnalysis(job) {
    if (!active(job) || this.busy) return;
    const identity = this.identity(); this.busy = true; this.refresh();
    try { const updated = await this.callbacks.request('repair-analysis/cancel', { job_id: job.id }); if (identity === this.identity()) { this.saveAnalysis(updated); this.publishAnalysis(); } }
    catch (error) { if (identity === this.identity()) this.callbacks.notify?.(error.message, 'error'); }
    finally { if (identity === this.identity()) { this.busy = false; this.refresh(); this.callbacks.chrome?.(); this.scheduleAnalysis(); } }
  }
  async applyAnalysis(job) {
    if (this.gate() || job?.execution_status !== 'Completed' || !job.proposal || !this.analysisCurrent(job)) return;
    this.analysisJobIds[job.source.node_id] = job.id;
    const mode = job.source.stage_id === 'local_netlist_simulation' ? 'netlist_repair' : 'synthesis_repair';
    const ids = this.plan?.mode === mode ? this.plan.items.map(item => item.node_id) : [job.source.node_id];
    await this.prepare(mode, ids, false);
  }
  async start() {
    if (this.startGate()) return;
    const identity = this.sourceIdentity(), token = ++this.token, plan = this.plan;
    const requestId = this.requestId || crypto.randomUUID(); this.requestId = requestId;
    this.busy = true; this.refresh();
    try {
      const envelope = await this.callbacks.request('generation/batches/start', { plan_id: plan.plan_id, request_id: requestId });
      if (identity !== this.sourceIdentity() || token !== this.token) return;
      const records = envelope.generation_batches?.batches || [];
      this.batchId = records.find(batch => batch.request_id === requestId)?.id || envelope.generation_batches?.active_batch_id || envelope.generation_batches?.latest_batch_id;
      this.plan = null; this.previewSelection = null; this.startUncertain = false; this.pollError = null; this.requestId = null;
      this.callbacks.envelope(envelope); this.callbacks.toast?.('Batch started. Each queued node gets a separate request; results remain saved per node.');
    } catch (error) {
      if (identity !== this.sourceIdentity() || token !== this.token) return;
      if (!error.code || error.code === 'internal_error') { this.startUncertain = true; this.pollError = `${error.message} Reconnect to check saved progress. No request was resent.`; }
      else { this.requestId = null; this.callbacks.notify?.(error.message, 'error'); }
    } finally { if (token === this.token) { this.busy = false; this.refresh(); this.schedule(); this.callbacks.chrome?.(); } }
  }
  async reconnect() {
    if (this.polling) return;
    const identity = this.identity(), token = this.token; this.polling = true;
    try {
      const envelope = await this.callbacks.request('project');
      if (identity !== this.identity() || token !== this.token) return;
      const recovered = envelope.generation_batches?.batches?.find(batch => batch.request_id === this.requestId);
      if (recovered) { this.batchId = recovered.id; this.plan = null; }
      this.startUncertain = false; this.pollError = null; if (recovered) this.requestId = null;
      this.callbacks.envelope(envelope);
    } catch (error) { if (identity === this.identity() && token === this.token) this.pollError = `${error.message} No request was resent.`; }
    finally { if (identity === this.identity() && token === this.token) { this.polling = false; this.refresh(); this.schedule(); this.callbacks.chrome?.(); } }
  }
  async cancel() {
    const batch = this.activeBatch(); if (!batch || this.busy) return;
    const identity = this.identity(), token = this.token; this.busy = true; this.refresh();
    try {
      const envelope = await this.callbacks.request(`generation/batches/${encodeURIComponent(batch.id)}/cancel`, {});
      if (identity === this.identity() && token === this.token) this.callbacks.envelope(envelope);
    } catch (error) { if (identity === this.identity() && token === this.token) this.callbacks.notify?.(error.message, 'error'); }
    finally { if (identity === this.identity() && token === this.token) { this.busy = false; this.refresh(); this.schedule(); } }
  }
  schedule() { if (!this.pollTimer && !this.polling && !this.pollError && this.activeBatch()) this.pollTimer = setTimeout(() => { this.pollTimer = null; this.poll(); }, 1300); }
  async poll() {
    const batch = this.activeBatch(); if (!batch || this.polling) return;
    const identity = this.identity(), token = this.token; this.polling = true;
    try {
      const updated = await this.callbacks.request(`generation/batches/${encodeURIComponent(batch.id)}`);
      if (identity !== this.identity() || token !== this.token) return;
      const index = this.batches.findIndex(item => item.id === updated.id); if (index >= 0) this.batches[index] = updated;
      this.refresh();
      const envelope = await this.callbacks.request('project');
      if (identity === this.identity() && token === this.token) this.callbacks.envelope(envelope);
    } catch (error) { if (identity === this.identity() && token === this.token) this.pollError = `${error.message} No request was resent.`; }
    finally { if (identity === this.identity() && token === this.token) { this.polling = false; this.refresh(); this.schedule(); this.callbacks.chrome?.(); } }
  }
  refresh() { if (this.generationHost?.isConnected && this.project().stage === 'local_rtl_generation') this.renderGeneration(this.generationHost); if (this.repairHost?.isConnected && this.project().stage === 'local_synthesis') this.renderRepairs(this.repairHost); }
  renderRepairs(host, inGeneration = false) {
    if (!inGeneration) this.repairHost = host;
    const failed = this.failedSynthesis(), eligible = failed.filter(item => !item.blocked), gate = this.gate();
    if (failed.length && failed.every(item => item.sameRtlRecovery)) {
      host.replaceChildren(card('Retry synthesis without regenerating RTL',
        'These attempts have no saved failed RTL check. Inspect the recorded execution errors, correct the environment if needed, then retry S05 with the same accepted candidates.',
        el('div', { class: 'generation-batch-body', 'data-testid': 'workflow-same-rtl-recovery' },
          ...failed.map(item => el('p', {}, el('strong', { text: item.node.name + ': ' }), el('span', { text: item.sameRtlRecovery }))),
          el('p', { text: inGeneration ? 'Return to Local Synthesis and use Run synthesis for all nodes. No model request is needed.' : 'Use Retry synthesis for all nodes in Next step, or Run synthesis for all nodes above. Old attempts and the exact saved RTL are retained.' }),
          inGeneration ? el('button', { type: 'button', text: 'Open S05 · retry the same RTL', 'data-testid': 'generation-open-s05-same-rtl', onclick: () => this.callbacks.navigate?.('local_synthesis', failed[0].node.id) }) : null)));
      return;
    }
    host.replaceChildren(card(inGeneration ? 'Repair failed synthesis' : 'Repair failed synthesis together', inGeneration ? 'S05 found an issue in the current RTL. Prepare its diagnostics here; no need to generate every node again.' : 'Collect S05 diagnostics for several nodes, then start their separate S04 repair requests with one action.',
      el('div', { class: 'generation-batch-body' },
        el('p', { 'data-testid': 'workflow-batch-repair-status', text: eligible.length ? `${eligible.length} current failed node${eligible.length === 1 ? '' : 's'} can be prepared for RTL repair.` : 'No current failed RTL synthesis is ready for repair.' }),
        el('div', { class: 'generation-batch-selection' }, ...failed.map(item => el('section', { class: 'repair-selection-node' },
          el('label', {}, el('input', { type: 'checkbox', checked: this.repairSelected.has(item.node.id), disabled: !!gate || !!item.blocked, 'data-testid': `workflow-batch-repair-select-${item.node.id}`, onchange: event => { this.repairSelectionEdited = true; if (event.target.checked) this.repairSelected.add(item.node.id); else this.repairSelected.delete(item.node.id); this.selectionChanged(); } }), el('span', { text: item.node.name })),
          item.recovery ? el('small', { 'data-testid': `workflow-repair-transport-${item.node.id}`, text: 'Last request returned no RTL after a connection or transport failure. Retry uses the preserved original RTL and S05 diagnostics.' }) : null,
          item.blocked ? el('small', { text: item.blocked }) : el('small', { text: this.failureExcerpt(item.run) || item.run.id }),
          this.repairStatus(item.node.id, item.run) ? el('small', { 'data-testid': `workflow-repair-outcome-${item.node.id}`, text: `${repairOutcomeLabel(this.repairStatus(item.node.id, item.run))}${this.repairStatus(item.node.id, item.run).reconsideration_required ? ' · Reconsider guidance' : ''}` }) : null,
          field('Correction for this node', this.synthesisNodeInstructions[item.node.id] || '', value => this.editNodeInstruction('synthesis_repair', item.node.id, value), { 'data-testid': `synthesis-batch-node-instruction-${item.node.id}`, multiline: true, rows: 4, disabled: !!gate || !!item.blocked, placeholder: 'Describe the specific RTL correction for this node.', hint: 'Up to 8,192 UTF-8 bytes. Only this node receives this guidance with its actual S05 diagnostics. Preview again after editing.' }),
          inGeneration ? el('button', { type: 'button', text: 'Inspect S05', 'data-testid': `generation-synthesis-inspect-${item.node.id}`, onclick: event => { event?.preventDefault?.(); this.callbacks.navigate?.('local_synthesis', item.node.id); } }) : null))),
        this.renderUnresolvedProblems(),
        field('Additional instruction for these repairs', this.instruction, value => { this.instruction = value; this.plan = null; this.token++; this.updateButtons(); this.callbacks.chrome?.(); }, { id: 'workflow-batch-repair-instruction', 'data-testid': 'workflow-batch-repair-instruction', multiline: true, rows: 4, disabled: !!gate, placeholder: 'Optional correction applied to each selected repair.', hint: 'Saved S05 diagnostics are included for each node. After editing, prepare the repair preview again.' }),
        el('div', { class: 'provider-actions' },
          el('button', { type: 'button', class: 'primary', text: inGeneration ? 'Preview repairs for all failed nodes' : 'Prepare repairs for all failed nodes', 'data-testid': 'workflow-batch-repair-all', disabled: !!gate || !eligible.length, title: gate || 'Preview the failed nodes together; no LLM request is sent yet.', onclick: () => this.prepare('synthesis_repair', eligible.map(item => item.node.id), !inGeneration) }),
          el('button', { type: 'button', text: `Prepare selected repairs (${this.repairSelected.size})`, 'data-testid': 'workflow-batch-repair-selected', disabled: !!gate || !this.repairSelected.size, onclick: () => this.prepare('synthesis_repair') })),
        el('p', { class: 'generation-gate', text: gate || 'Next: inspect the S04 batch preview, then select Start repair batch. Original RTL and S05 evidence are retained.' }))));
  }
  renderUnresolvedProblems() {
    const sources = this.project().envelope.generation_batches?.repair_sources || [];
    const items = this.plan?.mode === 'synthesis_repair' ? (this.plan.items || []).filter(item => item.operation === 'repair' || item.repair_guidance || item.repair_explanation) : this.failedSynthesis().flatMap(failed => {
      const state = this.nodeState(failed.node.id), source = sources.find(source => source.node_id === failed.node.id && source.base_job_id === failed.run.candidate_id && source.latest_job_id === state?.latest_job_id && source.source_workflow_run_id === failed.run.id && source.repair_explanation);
      return source ? [{ node_id: failed.node.id, node_name: failed.node.name, base_job_id: source.base_job_id, expected_latest_job_id: source.latest_job_id, source_workflow_run_id: source.source_workflow_run_id, repair_explanation: source.repair_explanation, display_source: 'authoritative_saved_source' }] : [];
    });
    if (!items.length) return null;
    return el('section', { class: 'repair-unresolved-problems', 'data-testid': 'repair-unresolved-problems', tabindex: -1 },
      el('h3', { text: 'Unresolved synthesis problems' }),
      el('p', { class: 'scope-note', text: 'Read the actual error and source below, then choose a correction. Viewing these facts sends no model request.' }),
      ...items.map(item => repairProblemsView(item, { prefix: `repair-problem-${item.node_id}`, current: this.repairItemCurrent(item), disabled: !!this.gate(),
        onEdit: () => this.focusRepairInstruction(), onAnalyze: item.source_workflow_run_id ? () => this.previewAnalysis(item) : null,
        onInspect: this.callbacks.inspect, onReadGuidance: this.plan ? () => this.readPreviewInstructions() : null })));
  }
  failureExcerpt(run) {
    const lines = [run.checks?.stderr, run.checks?.stdout].filter(Boolean).join('\n').split(/\r?\n/).map(line => line.trim()).filter(Boolean);
    return ([...lines].reverse().find(line => /multiple conflicting drivers|no driver|syntax error|latch inferred/i.test(line)) || lines.find(line => /\b(error|fatal)\b/i.test(line)) || run.error?.message || '').slice(0, 300);
  }
  renderNetlistRepairs() {
    const failures = this.failedNetlists();
    if (!failures.length) return null;
    const gate = this.gate();
    return card('Repair failed netlist checks · S06', 'Each node keeps its complete saved specification and RTL. The repair request includes its actual first failure and immutable S05/S06 evidence references.',
      el('div', { class: 'generation-batch-body', 'data-testid': 'generation-netlist-recovery' },
        ...failures.map(({ node, source }) => el('section', {}, el('strong', { text: node.name }),
          el('pre', { class: 'prompt-text', text: source.netlist_repair_evidence?.first_failure || 'Inspect the recorded diagnostic.', tabindex: 0 }),
          this.planCurrent() && this.plan?.mode === 'netlist_repair' && this.plan.items.find(item => item.node_id === node.id)?.context_budget ? el('p', { class: 'scope-note', text: this.itemBudget(this.plan.items.find(item => item.node_id === node.id)) }) : null,
          field('Correction for this node', this.netlistNodeInstructions[node.id] || '', value => this.editNodeInstruction('netlist_repair', node.id, value), { 'data-testid': `netlist-batch-node-instruction-${node.id}`, multiline: true, rows: 4, disabled: !!gate, placeholder: 'Describe the RTL change needed for the saved netlist failure of this node.', hint: 'Up to 8,192 UTF-8 bytes. Only this node receives this guidance with its actual S05/S06 evidence. Preview again after editing.' }),
          el('button', { type: 'button', text: 'Preview repair analysis', 'data-testid': `netlist-repair-analyze-${node.id}`, disabled: !!gate, onclick: () => this.previewAnalysis({ node_id: node.id, base_job_id: source.base_job_id, expected_latest_job_id: source.latest_job_id, source_workflow_run_id: source.source_workflow_run_id, netlist_repair_evidence: source.netlist_repair_evidence }) }),
          el('button', { type: 'button', text: 'Inspect S06', onclick: () => this.callbacks.navigate?.('local_netlist_simulation', node.id) }))),
        field('Additional instruction for netlist repairs', this.instruction, value => { this.instruction = value; this.plan = null; this.token++; this.updateButtons(); this.callbacks.chrome?.(); }, { 'data-testid': 'netlist-batch-repair-instruction', multiline: true, rows: 3, disabled: !!gate, placeholder: 'Optional correction. Original specifications and saved diagnostics are included automatically.' }),
        el('button', { type: 'button', class: 'primary', text: `Preview repairs for all ${failures.length} failed netlists`, 'data-testid': 'netlist-batch-repair-all', disabled: !!gate, onclick: () => this.prepare('netlist_repair', failures.map(item => item.node.id), false) }),
        el('p', { class: 'scope-note', text: 'Preview → Start repair batch → S05 synthesis → S06 netlist checks. No model request is sent by preview.' })));
  }
  renderGeneration(host) {
    // Read the native state before replacing DOM, even when its toggle event
    // has not fired yet. Background polls and checkbox refreshes keep it open.
    const identity = this.identity();
    if (this.generationDetailsIdentity === identity) {
      const selection = this.generationHost?.querySelector('[data-testid="generation-batch-node-selection"]');
      const instructions = this.generationHost?.querySelector('[data-testid="generation-batch-node-instructions"]');
      if (selection) this.selectionOpen = selection.open === true;
      if (instructions) this.nodeInstructionsOpen = instructions.open === true;
    }
    this.generationDetailsIdentity = identity;
    this.generationHost = host; const gate = this.gate(), batch = this.selectedBatch(), accepted = this.nodes().filter(node => this.accepted(node.id)).length;
    const failed = this.failedSynthesis(), recovery = failed.length ? el('div', { 'data-testid': 'generation-synthesis-recovery' }) : null;
    const oldRecord = batch && !active(batch) && (this.plan || failed.length || this.superseded(batch));
    const locked = this.busy || !!this.activeBatch() || this.startUncertain;
    host.replaceChildren(...[recovery, this.renderNetlistRepairs(), card('Generate nodes in sequence', 'Choose nodes once. Each node gets a separate LLM request; saved conversation turns are retained within the context budget.',
      el('div', { class: 'generation-batch-body' },
        el('div', { class: 'generation-summary' }, badge(`${accepted}/${this.nodes().length} nodes adopted`, 'teal'), badge('One node per request'), badge('Bounded retained conversation')),
        el('details', { open: this.selectionOpen ?? (!this.plan && !failed.length && !active(batch)), 'data-testid': 'generation-batch-node-selection' }, el('summary', { text: `Select nodes (${this.selected.size})` }),
          el('div', { class: 'provider-actions' },
            el('button', { type: 'button', text: 'Select missing nodes', 'data-testid': 'generation-batch-select-missing', disabled: locked, onclick: () => { this.selectionEdited = true; this.selected = new Set(this.nodes().filter(node => !this.accepted(node.id)).map(node => node.id)); this.selectionChanged(); } }),
            el('button', { type: 'button', text: 'Select all nodes', 'data-testid': 'generation-batch-select-all', disabled: locked, onclick: () => { this.selectionEdited = true; this.selected = new Set(this.nodes().map(node => node.id)); this.selectionChanged(); } }),
            el('button', { type: 'button', text: 'Clear selection', disabled: locked, onclick: () => { this.selectionEdited = true; this.selected.clear(); this.selectionChanged(); } })),
          el('div', { class: 'generation-batch-selection' }, ...this.nodes().map(node => el('label', {}, el('input', { type: 'checkbox', checked: this.selected.has(node.id), disabled: locked, 'data-testid': `generation-batch-select-${node.id}`, onchange: event => { this.selectionEdited = true; if (event.target.checked) this.selected.add(node.id); else this.selected.delete(node.id); this.selectionChanged(); } }), el('span', { text: node.name }), badge(this.accepted(node.id) ? 'Accepted' : 'RTL required', this.accepted(node.id) ? 'teal' : 'neutral')))),
          field('Additional instruction for this batch', this.instruction, value => { this.instruction = value; this.plan = null; this.callbacks.chrome?.(); this.updateButtons(); }, { id: 'generation-batch-instruction', 'data-testid': 'generation-batch-instruction', multiline: true, disabled: locked, placeholder: 'Optional common instruction. Each node keeps its saved specification and connected-edge context.' }),
          el('details', { open: this.nodeInstructionsOpen, 'data-testid': 'generation-batch-node-instructions' },
            el('summary', { text: `Per-node instructions (${this.selected.size})` }),
            el('p', { class: 'scope-note', text: 'Optional natural-language guidance for each selected node. Its current request receives the common instruction and its own guidance; previous turns are retained only within the context budget. Preview shows the complete request before sending.' }),
            ...this.nodes().filter(node => this.selected.has(node.id)).map(node => field(`${node.name} · ${node.id}`, this.nodeInstructions[node.id] || '', value => { this.nodeInstructions[node.id] = value; this.plan = null; this.callbacks.chrome?.(); this.updateButtons(); }, { 'data-testid': `generation-batch-node-instruction-${node.id}`, multiline: true, rows: 4, disabled: locked, placeholder: 'Describe the implementation approach in natural language. The saved specification remains authoritative.', hint: 'Up to 8,192 UTF-8 bytes. Per-node guidance applies to fresh generation; retries retain the frozen original request.' }))),
          el('div', { class: 'provider-actions' }, el('button', { type: 'button', text: 'Preview selected generation', 'data-testid': 'generation-batch-preview', disabled: !!gate || !this.selected.size, title: gate, onclick: () => this.prepare('generate') }))),
        this.plan ? this.renderPlan() : null,
        this.renderAnalysis(),
        this.pollError ? el('div', { class: 'generation-error' }, el('p', { text: this.pollError }), el('button', { type: 'button', text: 'Reconnect without resending', 'data-testid': 'generation-batch-reconnect', onclick: () => this.reconnect() })) : null,
        batch ? oldRecord ? el('details', { 'data-testid': 'generation-batch-history-panel' }, el('summary', { text: `Previous generation batch · ${batch.execution_status}` }), this.renderRecord(batch)) : this.renderRecord(batch) : null,
        this.batches.length > 1 ? el('details', {}, el('summary', { text: 'Previous generation batches' }), el('div', { class: 'generation-job-list' }, ...[...this.batches].reverse().map(record => el('button', { type: 'button', class: `generation-job-button${record.id === batch?.id ? ' selected' : ''}`, 'data-testid': `generation-batch-history-${record.id}`, onclick: () => { this.batchId = record.id; this.refresh(); } }, badge(record.execution_status), badge(record.validation_status), el('code', { text: record.id }))))) : null,
        el('p', { class: 'generation-gate', 'data-testid': 'generation-batch-gate', text: gate || 'Preview, then Start. One start authorizes all queued requests. S04 checks external interfaces; S05 synthesis remains separate.' })))].filter(Boolean));
    if (recovery) this.renderRepairs(recovery, true);
  }
  updateButtons() { const start = this.generationHost?.querySelector('[data-testid="generation-batch-start"]'); if (start) start.disabled = !!this.startGate(); }
  renderPlan() {
    const plan = this.plan, context = plan.first_request_context || {}, startGate = this.startGate(), items = plan.items || [];
    const repeatedPlan = this.planCurrent() && items.some(item => repeatedGuidanceBlocked(item.repair_guidance));
    const unavailable = startGate ? this.itemAvailability(items.find(item => ['Blocked', 'Unsupported'].includes(item.status)), startGate) : null;
    const implementationRequired = unavailable?.kind === 'implementation';
    return el('section', { class: 'generation-batch-preview', 'data-testid': 'generation-batch-plan' },
      el('h3', { text: plan.mode === 'synthesis_repair' ? 'S05 repair queue' : plan.mode === 'netlist_repair' ? 'S06 netlist repair queue' : 'Generation queue' }),
      el('p', { text: `${items.filter(item => item.status === 'Queued').length} queued request(s) · source ${plan.revision_id} · profile ${plan.profile_revision_id}` }),
      plan.profile ? el('p', { text: `Provider: ${plan.profile.execution_location} · ${plan.profile.model} · ${plan.profile.base_url}. Output limit ${number(plan.profile.max_output_tokens)} / context ${number(plan.profile.context_window)} tokens.` }) : null,
      el('p', { 'data-testid': 'generation-batch-budget', text: this.planBudget() }),
      plan.profile?.execution_location === 'Network' ? el('p', { class: 'generation-network-notice', text: 'Starting sends these node specifications and retained conversation to the configured network endpoint.' }) : null,
      el('p', { text: 'Previous exact request/answer turns are retained where they fit. A saved ledger preserves turn identities when older turns leave the context. Later requests add only their target node and required adjacent interfaces.' }),
      el('div', { class: 'generation-batch-table-scroll' }, el('table', { class: 'generation-batch-table' }, el('thead', {}, el('tr', {}, ...['Order / node', 'Operation', 'Source / status'].map(text => el('th', { scope: 'col', text })))), el('tbody', {}, ...items.map((item, index) => el('tr', {}, el('th', { scope: 'row', text: `${index + 1}. ${item.node_name || item.node_id}` }), el('td', { text: item.operation }), el('td', {}, badge(this.itemDisplayStatus(item)), this.itemReasonView(item, `generation-batch-availability-${item.node_id}`), el('small', { text: ['Blocked', 'Unsupported'].includes(item.status) ? '' : item.reason || item.source_workflow_run_id || item.base_job_id || item.context?.context_id || '' }), item.context_budget ? el('small', { 'data-testid': `generation-batch-budget-${item.node_id}`, text: this.itemBudget(item) }) : null, item.source_recovery || item.recovery ? el('small', { text: 'Connection/transport retry · original RTL and S05 source retained' }) : null, el('details', {}, el('summary', { text: 'Node request and source' }), el('pre', { text: JSON.stringify(item, null, 2) })))))))),
      el('section', { class: 'prompt-panel', 'data-testid': 'generation-batch-readable-request', tabindex: -1 },
        el('h3', { text: 'Instructions for the next requests · not sent' }),
        el('p', { text: 'These are the complete instructions in this preview. To change them, edit Additional instruction for these repairs and preview again.' }),
        ...items.map(item => el('section', { class: 'prompt-node' },
          el('h4', { text: item.node_name || item.node_id }),
          el('p', { class: 'prompt-metadata', text: `Operation: ${item.operation} · base candidate: ${item.base_job_id || 'None'} · ${plan.mode === 'netlist_repair' ? 'S06' : 'S05'} run: ${item.source_workflow_run_id || 'None'}` }),
          item.repair_guidance ? repairGuidanceView(item.repair_guidance, { prefix: `generation-batch-guidance-${item.node_id}` }) : null,
          item.netlist_repair_evidence ? el('section', { 'data-testid': `netlist-repair-evidence-${item.node_id}` }, el('h4', { text: 'Actual S06 failure' }), el('pre', { class: 'prompt-text', text: JSON.stringify(item.netlist_repair_evidence, null, 2), tabindex: 0 })) : null,
          item.operation === 'repair' ? el('details', { 'data-testid': `generation-batch-source-rtl-${item.node_id}` }, el('summary', { text: `Current RTL used by the failed ${plan.mode === 'netlist_repair' ? 'S06' : 'S05'} run` }), el('pre', { class: 'prompt-text', text: this.project().envelope.generation?.jobs?.find(job => job.id === item.base_job_id)?.rtl || 'RTL is not included in this envelope. Inspect the saved source candidate.', tabindex: 0 }), el('button', { type: 'button', text: 'Inspect saved source candidate', 'data-testid': `generation-batch-source-inspect-${item.node_id}`, onclick: () => this.callbacks.inspect?.(item.base_job_id, item.node_id) })) : null,
          item.repair_guidance ? el('button', { type: 'button', text: 'Preview model-assisted guidance', 'data-testid': `generation-batch-analyze-${item.node_id}`, disabled: !!this.gate() || !this.planCurrent(), title: 'Preview a separate analysis request. It does not modify RTL or start repair.', onclick: () => this.previewAnalysis(item) }) : null,
          instructionView(item.instruction, { prefix: `generation-batch-instruction-${item.node_id}`, title: item.operation === 'repair' ? 'Complete repair instruction' : 'Complete additional instruction' }))),
        promptMessagesView(context, { prefix: 'generation-batch-request', title: 'Read the full first request', open: false, description: 'Preview only. Later node requests will add the bounded conversation available when they execute; each actual request is saved with its job.' })),
      el('details', {}, el('summary', { text: 'First exact provider request and context policy' }), el('p', { text: `First estimated input: ${number(context.provider_input_estimated_tokens ?? context.estimated_input_tokens)} tokens. This is the first request only. Later exact requests, including the retained conversation and ledger, are saved with each job.` }), el('pre', { 'data-testid': 'generation-batch-context', text: JSON.stringify({ first_request_context: context, context_policy: plan.context_policy }, null, 2) })),
      el('div', { class: 'provider-actions' }, el('button', { type: 'button', class: 'primary', text: repairMode(plan.mode) ? 'Start repair batch' : 'Start generation batch', 'data-testid': 'generation-batch-start', disabled: !!startGate, title: startGate || 'Authorize all queued node requests in this preview.', onclick: () => this.start() }),
        startGate && !implementationRequired ? el('button', { type: 'button', text: repairMode(plan.mode) ? 'Rebuild repair preview' : 'Rebuild generation preview', 'data-testid': 'generation-batch-rebuild', disabled: !!this.gate(), onclick: () => this.rebuildPlan() }) : null,
        startGate ? implementationRequired ? el('button', { type: 'button', text: 'Inspect saved requirements', 'data-testid': 'generation-batch-inspect-requirements', onclick: () => this.readPreviewInstructions() }) : repeatedPlan ? el('button', { type: 'button', text: 'Inspect unresolved problems', 'data-testid': 'generation-batch-inspect-problems', onclick: () => this.focusUnresolvedProblems() }) : el('button', { type: 'button', text: 'Open LLM settings', 'data-testid': 'generation-batch-provider-settings', onclick: () => this.callbacks.navigate?.('global_settings') }) : null,
        el('button', { type: 'button', text: 'Discard preview', 'data-testid': 'generation-batch-discard', disabled: this.busy || this.startUncertain, onclick: () => this.discardPreview() })),
      startGate ? el('p', { class: 'generation-gate', text: `${unavailable.label}: ${unavailable.message}` }) : null);
  }
  renderAnalysis() {
    const preview = this.analysisPreview, job = this.selectedAnalysis();
    if (!preview && !job && !this.analysisError && !this.analysisJobs.length) return null;
    const current = job && this.analysisCurrent(job), gate = this.gate();
    return el('section', { class: 'generation-recovery', 'data-testid': 'repair-analysis-panel', tabindex: -1 },
      el('h3', { text: 'Model-assisted repair guidance' }),
      el('p', { class: 'scope-note', text: 'Analysis suggests a repair method. Review it, apply it to a new repair preview, then explicitly start RTL repair. No RTL is changed by analysis.' }),
      preview ? el('section', { 'data-testid': 'repair-analysis-preview' },
        el('p', { text: `Unsent analysis · node ${preview.source?.node_id || 'Not recorded'} · ${preview.source?.stage_id === 'local_netlist_simulation' ? 'S06' : 'S05'} ${preview.source?.run_id || 'Not recorded'}` }),
        el('p', { 'data-testid': 'repair-analysis-budget', text: `Estimated input ${number(preview.estimated_input_tokens)} + output ${number(preview.parameters?.max_tokens)} = ${number(preview.context_budget?.total_estimated_tokens)} / context ${number(preview.profile?.context_window)} tokens${Number.isFinite(preview.context_budget?.maximum_output_tokens) ? ` · maximum output for this exact request ${number(preview.context_budget.maximum_output_tokens)}` : ''}. Conservative byte estimate; actual provider tokens are not measured.` }),
        preview.prompt_projection ? el('p', { class: 'scope-note', 'data-testid': 'repair-analysis-projection', text: 'Complete current requirements, RTL and diagnostics. Only prior repair instruction/diff excerpts are bounded; their full originals remain saved.' }) : null,
        promptMessagesView(preview, { prefix: 'repair-analysis-request', title: 'Full analysis request · not sent', open: false }),
        preview.source_evidence ? el('details', {}, el('summary', { text: 'Complete original evidence · saved, not all sent' }), el('pre', { class: 'prompt-text', text: JSON.stringify(preview.source_evidence, null, 2), tabindex: 0, 'data-testid': 'repair-analysis-source-evidence' })) : null,
        preview.profile?.execution_location === 'Network' ? el('p', { class: 'generation-network-notice', text: 'Starting analysis sends these saved requirements, RTL and diagnostics to the configured network endpoint.' }) : null,
        preview.gate_reason ? el('p', { class: 'generation-gate', text: preview.gate_reason }) : null,
        el('button', { type: 'button', class: 'primary', text: 'Start guidance analysis', 'data-testid': 'repair-analysis-start', disabled: !!gate || !preview.ready_to_start || !this.analysisCurrent(preview), title: !this.analysisCurrent(preview) ? 'Source or provider changed. Discard this preview and prepare a current one.' : gate || preview.gate_reason || 'Send one analysis request to the configured model. RTL is unchanged.', onclick: () => this.startAnalysis() }),
        !preview.ready_to_start ? el('button', { type: 'button', text: 'Open LLM settings', 'data-testid': 'repair-analysis-provider-settings', onclick: () => this.callbacks.navigate?.('global_settings') }) : null,
        el('button', { type: 'button', text: 'Rebuild analysis preview', 'data-testid': 'repair-analysis-rebuild', disabled: !!gate || !this.analysisSourceCurrent(preview), title: 'Use the current saved provider settings. Does not send a model request.', onclick: () => this.rebuildAnalysisPreview() }),
        el('button', { type: 'button', text: 'Discard analysis preview', 'data-testid': 'repair-analysis-discard', disabled: this.busy || this.analysisStartUncertain, onclick: () => { this.analysisPreview = null; this.refresh(); this.callbacks.chrome?.(); } })) : null,
      job ? el('section', { 'data-testid': 'repair-analysis-result' },
        el('div', { class: 'generation-summary' }, badge(job.execution_status), badge(current ? 'Current sources' : 'Earlier sources'), el('code', { text: job.id })),
        job.error ? el('p', { class: 'generation-error', text: `${job.error.code || 'Analysis error'} · ${job.error.message || ''}` }) : null,
        job.proposal ? el('section', {}, el('h4', { text: 'Proposed changes · hypotheses' }), el('pre', { class: 'prompt-text', text: JSON.stringify(job.proposal, null, 2), tabindex: 0, 'data-testid': 'repair-analysis-proposal' })) : null,
        el('details', {}, el('summary', { text: 'Complete saved analysis answer and request' }),
          el('pre', { class: 'prompt-text', text: job.raw_content ?? 'Load the full saved analysis to inspect its answer.', tabindex: 0, 'data-testid': 'repair-analysis-raw-answer' }),
          job.raw_reasoning ? el('pre', { class: 'prompt-text', text: job.raw_reasoning, tabindex: 0 }) : null,
          promptMessagesView(job.context || { messages: job.messages || [] }, { prefix: 'repair-analysis-saved', title: 'Saved analysis messages', open: false })),
        el('div', { class: 'provider-actions' },
          el('button', { type: 'button', text: 'Load full saved analysis', 'data-testid': 'repair-analysis-load', disabled: this.analysisPolling, onclick: () => this.pollAnalysis() }),
          active(job) ? el('button', { type: 'button', text: 'Cancel guidance analysis', 'data-testid': 'repair-analysis-cancel', disabled: this.busy, onclick: () => this.cancelAnalysis(job) }) : null,
          el('button', { type: 'button', class: 'primary', text: 'Apply reviewed guidance to repair preview', 'data-testid': 'repair-analysis-apply', disabled: !!gate || job.execution_status !== 'Completed' || !job.proposal || !current, title: current ? gate || 'Prepare a new repair preview; does not send an RTL-generation request.' : 'Analysis uses earlier sources. Preview analysis for the current failed candidate.', onclick: () => this.applyAnalysis(job) }))) : null,
      this.analysisError ? el('p', { class: 'generation-error', text: this.analysisError }) : null,
      this.analysisStartUncertain || this.analysisError ? el('button', { type: 'button', text: 'Reconnect analysis without resending', 'data-testid': 'repair-analysis-reconnect', disabled: this.analysisPolling, onclick: () => this.pollAnalysis(true) }) : null,
      this.analysisJobs.length > 1 || !job && this.analysisJobs.length ? el('details', {}, el('summary', { text: 'Earlier guidance analyses' }), ...[...this.analysisJobs].reverse().map(saved => el('button', { type: 'button', text: `${saved.execution_status} · ${saved.id}`, 'data-testid': `repair-analysis-history-${saved.id}`, onclick: () => { this.analysisJobId = saved.id; this.refresh(); } }))) : null);
  }
  renderRecord(batch) {
    const items = batch.items || [], pending = this.remaining(batch), unchanged = this.unchangedRepairs(batch);
    const implementationOnly = pending.length && pending.every(item => ['Blocked', 'Unsupported'].includes(item.status) && this.itemAvailability(item).kind === 'implementation');
    return el('section', { class: 'generation-batch-record', 'data-testid': 'generation-batch-result' },
      el('div', { class: 'generation-summary', 'data-testid': 'generation-batch-status' }, badge(batch.execution_status), badge(batch.validation_status), el('strong', { text: `${batch.completed_count || 0}/${batch.required_node_count || items.length} nodes processed` }), ...Object.entries(batch.counts || {}).filter(([, count]) => count > 0).map(([status, count]) => badge(`${['Blocked', 'Unsupported'].includes(status) ? 'Not run' : status}: ${count}`))),
      el('code', { text: batch.id }), batch.error ? el('p', { class: 'generation-error', text: `${batch.error.code || 'Batch error'} · ${batch.error.message || ''}` }) : null,
      batch.source_current === false ? el('p', { class: 'generation-error', text: 'The saved source changed. These results remain historical; preview the current source before another batch.' }) : null,
      el('div', { class: 'generation-batch-table-scroll' }, el('table', { class: 'generation-batch-table', 'data-testid': 'generation-batch-results' }, el('thead', {}, el('tr', {}, ...['Node', 'Request result', 'Evidence'].map(text => el('th', { scope: 'col', text })))), el('tbody', {}, ...items.map(item => {
        const same = this.unchangedRepair(item), historical = batch.source_current === false || !same?.current;
        return el('tr', { 'data-testid': `generation-batch-result-${item.node_id}` }, el('th', { scope: 'row', text: item.node_name || item.node_id }), el('td', {}, badge(this.itemDisplayStatus(item), ['Failed', 'Blocked', 'Unsupported'].includes(item.status) ? 'orange' : 'neutral'),
          this.itemReasonView(item, `generation-batch-result-availability-${item.node_id}`),
          same ? el('small', { 'data-testid': `generation-batch-unchanged-${item.node_id}`, text: historical ? 'Historical unchanged RTL; inspect later candidates for the current result.' : 'RTL unchanged; prior synthesis failure not corrected.' }) : null,
          !['Blocked', 'Unsupported'].includes(item.status) && (item.error || item.reason) ? el('small', { text: item.error?.message || item.reason }) : null), el('td', {}, item.job_id ? el('button', { type: 'button', text: 'Inspect RTL and checks', 'data-testid': `generation-batch-inspect-${item.node_id}`, onclick: () => this.callbacks.inspect?.(item.job_id, item.node_id) }) : null, el('small', { text: item.job_id || 'No request result' })));
      })))),
      active(batch) ? el('button', { type: 'button', text: 'Cancel remaining requests', 'data-testid': 'generation-batch-cancel', disabled: this.busy, onclick: () => this.cancel() }) :
        pending.length && !implementationOnly && batch.validation_status !== 'Passed' ? el('button', { type: 'button', text: 'Preview remaining requests', 'data-testid': 'generation-batch-remaining', disabled: !!this.gate(), onclick: () => this.prepareRemaining(batch) }) : null,
      !active(batch) && batch.execution_status === 'Completed' ? el('button', { type: 'button', text: 'Continue to Local Synthesis', 'data-testid': 'generation-batch-continue-synthesis', onclick: () => this.callbacks.navigate?.('local_synthesis') }) : null,
      !active(batch) && unchanged.length ? el('button', { type: 'button', class: 'primary', text: 'Preview fresh generation for unchanged repairs', 'data-testid': 'generation-batch-fresh-unchanged', disabled: !!this.gate(), onclick: () => this.prepare('generate', unchanged.map(item => item.node_id), false) }) : null,
      el('details', {}, el('summary', { text: 'Saved batch record' }), el('pre', { text: JSON.stringify(batch, null, 2) })));
  }
}
