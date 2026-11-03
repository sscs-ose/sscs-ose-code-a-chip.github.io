import { element as el, field, badge, downloadJsonResponse } from './dom.js';
import { adoptionProvenance } from './review_operator.js';
import { repairOutcomeLabel } from './prompt_view.js';
import { availabilityReason } from './availability.js';

const STAGES = new Set(['local_synthesis', 'local_netlist_simulation']);
const active = run => run && ['Queued', 'Running'].includes(run.execution_status);
const workflowSameRtlRecovery = run => {
  if (run?.stage_id !== 'local_synthesis') return '';
  if (run.error?.code === 'workflow_environment_error' && run.error.next_action === 'retry_same_RTL') return 'The tool execution environment failed. Fix setup and retry S05 using the same saved RTL. This does not establish an RTL defect.';
  if (run.execution_status === 'Failed' && run.validation_status === 'Not Checked' && run.error?.code === 'workflow_error'
      && run.checks && typeof run.checks === 'object' && !Array.isArray(run.checks) && Object.keys(run.checks).length === 0)
    return 'Execution stopped without any saved tool checks. Its cause is not established. Inspect setup and the service, then retry S05 using the same saved RTL; do not infer an RTL defect.';
  return '';
};
const resultLabel = (run, accepted = false) => !run ? 'Not run' : active(run) ? 'Running' : ['Failed', 'Cancelled', 'Interrupted'].includes(run.execution_status) || ['Failed', 'Unsupported'].includes(run.validation_status) ? 'Failed' : accepted ? 'Complete' : run.execution_status === 'Completed' && run.validation_status === 'Passed' ? 'Review required' : 'Not run';
function textDownload(value, filename) {
  const url = URL.createObjectURL(new Blob([value], { type: 'text/plain' }));
  const link = el('a', { href: url, download: filename }); document.body.append(link); link.click(); link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
const safe = value => String(value).replace(/[^a-z0-9_.-]/gi, '_');
const card = (title, subtitle, ...children) => el('section', { class: 'card' }, el('div', { class: 'card-heading' }, el('h2', { text: title }), el('p', { text: subtitle })), ...children);

/** Render saved streams without excerpts or a fabricated stdout/stderr ordering. */
function toolConsoleEvidence(run) {
  const checks = run?.checks || {};
  const commands = Array.isArray(checks.commands) ? checks.commands : [];
  const output = { stdout: [], stderr: [] }, sections = [];
  const recorded = value => value === null || value === undefined ? '' : String(value);
  const commandText = command => Array.isArray(command) ? command.map(token => {
    const value = String(token);
    return /^[a-z0-9_./:=+@%,-]+$/i.test(value) ? value : JSON.stringify(value);
  }).join(' ') : recorded(command) || 'Command not recorded';
  commands.forEach((command, index) => {
    sections.push(`COMMAND ${index + 1}\n$ ${commandText(command.command)}\nStatus: ${command.status ?? 'Not recorded'} · exit code: ${command.exit_code ?? 'Not recorded'} · executed: ${command.executed ?? 'Not recorded'}`);
    if (command.elapsed_seconds !== undefined) sections.push(`Elapsed: ${command.elapsed_seconds} seconds`);
    if (command.error) sections.push(`Command error: ${typeof command.error === 'string' ? command.error : JSON.stringify(command.error, null, 2)}`);
    for (const stream of ['stdout', 'stderr']) {
      const value = recorded(command[stream]);
      output[stream].push(value);
      sections.push(`[${stream}]\n${value || '(No output recorded)'}`);
    }
  });
  for (const stream of ['stdout', 'stderr']) {
    const aggregate = recorded(checks[stream]);
    // Some historical runs record aggregate streams but no per-command output.
    // Keep any additional aggregate text; suppress only a copy already shown.
    if (aggregate && !output[stream].join('').includes(aggregate)) {
      output[stream].push(aggregate);
      sections.push(`[${commands.length ? 'Additional saved run ' : ''}${stream}]\n${aggregate}`);
    }
  }
  return {
    text: sections.length ? sections.join('\n\n') : 'No tool commands or output have been recorded for this run yet.',
    stdout: output.stdout.join(''), stderr: output.stderr.join(''),
  };
}

/** Persisted stage-scoped S05/S06 batches and individual debugging runs. */
export class LocalWorkflow {
  constructor(callbacks) { this.callbacks = callbacks; this.runs = []; this.nodes = []; this.reviews = []; this.batches = []; this.batchId = null; this.nodeId = null; this.runId = null; this.runPinned = false; this.feedback = new Map(); this.busy = false; this.polling = false; this.pollTimer = null; this.pollError = null; this.batchPollError = null; this.batchRequestId = null; this.batchStartUncertain = false; }
  project() { return this.callbacks.project(); }
  identity() { return this.project().envelope.workspace_identity?.session_id || null; }
  batchStage(batch) { return batch?.stage_id || 'local_synthesis'; }
  stageBatches(stage = this.project().stage) { return this.batches.filter(batch => this.batchStage(batch) === stage); }
  selectedBatch() { const batches = this.stageBatches(); return batches.find(batch => batch.id === this.batchId) || batches.at(-1); }
  activeBatch() { return this.batches.find(active); }
  candidateFor(nodeId) {
    const generation = this.project().envelope.generation || {};
    const state = generation.nodes?.find(node => node.node_id === nodeId);
    return generation.jobs?.find(job => job.id === state?.accepted_job_id && job.id === state?.latest_job_id && job.freshness === 'Current' && job.review_status === 'Accepted');
  }
  relevant() { return [...this.runs].filter(run => run.node_id === this.nodeId && run.stage_id === this.project().stage).reverse(); }
  selected() { return this.runs.find(run => run.id === this.runId && run.stage_id === this.project().stage && run.node_id === this.nodeId) || this.currentRun(); }
  // Freshness describes saved inputs; replacing the RTL or S05 netlist also
  // makes an earlier result ineligible to advance the current design.
  runCurrent(run) {
    const candidate = this.candidate(), project = this.project();
    if (!run || !candidate || run.node_id !== this.nodeId || run.stage_id !== project.stage || run.freshness !== 'Current' || run.candidate_id !== candidate.id) return false;
    const matches = (saved, current) => saved === undefined || saved === null || saved === current;
    // A graph-position-only save can change the project revision while the
    // backend's semantic freshness and exact candidate lineage remain valid.
    if (!matches(run.revision_id, candidate.revision_id) ||
        !matches(run.input_hash, candidate.input_hash) || !matches(run.rtl_sha256, candidate.rtl_sha256)) return false;
    if (run.stage_id === 'local_netlist_simulation') {
      const prior = this.prior();
      if (!prior || run.prior_run_id !== prior.id || run.netlist_sha256 !== prior.netlist_sha256) return false;
    }
    return true;
  }
  currentRun() { return this.relevant().find(run => this.runCurrent(run)); }
  latestForCurrentSource() { return this.currentRun(); }
  candidate() {
    return this.candidateFor(this.nodeId);
  }
  prior() {
    const candidate = this.candidate();
    if (!candidate) return undefined;
    const latest = [...this.runs].reverse().find(run => run.stage_id === 'local_synthesis' && run.node_id === this.nodeId && run.candidate_id === candidate.id);
    return latest?.execution_status === 'Completed' && latest.validation_status === 'Passed' && latest.review_status === 'Accepted' && latest.freshness === 'Current' && latest.netlist ? latest : undefined;
  }
  verificationReadiness() { return this.project().envelope.generation?.nodes?.find(node => node.node_id === this.nodeId)?.behavioral_verification || this.candidate()?.behavioral_verification; }
  setNode(id) { this.nodeId = id; this.runId = null; this.runPinned = false; }
  receive(envelope) {
    const identity = this.identity();
    if (this.sessionId !== undefined && this.sessionId !== identity) {
      if (this.pollTimer) clearTimeout(this.pollTimer);
      this.pollTimer = null; this.busy = false; this.busyStage = null; this.polling = false; this.batchId = null; this.runId = null; this.runPinned = false; this.batchRequestId = null; this.batchRequestStage = null; this.batchStartUncertain = false; this.batchPollError = null; this.pollError = null;
    }
    this.sessionId = identity;
    this.runs = envelope.workflow_runs || [];
    this.nodes = envelope.workflow_nodes || [];
    this.reviews = envelope.workflow_reviews || [];
    this.batches = envelope.workflow_batches || [];
    if (!this.runPinned || !this.runs.some(run => run.id === this.runId)) this.runId = null;
    this.storageError = envelope.workflow_storage_error;
    if (!this.project().design.nodes.some(node => node.id === this.nodeId)) this.nodeId = this.project().design.nodes[0]?.id || null;
    this.refresh(); this.schedule();
  }
  batchGate() {
    const project = this.project(), synthesis = project.stage !== 'local_netlist_simulation';
    const operation = synthesis ? 'synthesis' : 'netlist verification';
    if (project.envelope.repair_analysis?.active_job_id) return `Repair guidance analysis is active. Inspect or cancel it before running ${operation}.`;
    if (project.readOnly || project.envelope.workspace_identity?.read_only) return 'This preserved system is read-only.';
    if (!project.envelope.workflow.find(stage => stage.id === (synthesis ? 'local_synthesis' : 'local_netlist_simulation'))?.implemented) return `${synthesis ? 'S05 synthesis' : 'S06 netlist verification'} is not implemented by the connected service.`;
    if (!synthesis && !project.envelope.workflow_batch_stages?.includes('local_netlist_simulation')) return 'Update and restart the local GUI service to enable all-node S06 verification. Existing node results are retained.';
    if (this.storageError || project.envelope.generation?.storage_error) return `Resolve the saved-history storage error before running ${operation}.`;
    if (project.conflict) return 'A newer saved design was detected. Export your draft, then Open saved.';
    if (project.dirty) return `Save the current design before running ${operation}.`;
    if (this.batchStartUncertain) return 'Check the saved batch before sending another request.';
    if (this.busy || project.busy || project.postlayoutRunning || project.lvsRunning || this.callbacks.batch?.()?.activeBatch() || this.activeBatch() || this.runs.some(active) ||
        (project.envelope.generation?.jobs || []).some(job => active(job) || job.execution_status === 'Completed' && !job.finished_at) ||
        ['global_generation', 'global_workflow', 'physical_workflow', 'drc_workflow', 'lvs_workflow', 'postlayout_workflow'].some(key =>
          [...(project.envelope[key]?.runs || []), ...(project.envelope[key]?.jobs || [])].some(active))) return 'Wait for the active operation to finish, or inspect and cancel it.';
    if (!project.design.nodes?.length) return `Add nodes before running ${operation}.`;
    return '';
  }
  synthesisFor(nodeId) {
    const candidate = this.candidateFor(nodeId);
    return candidate && [...this.runs].reverse().find(run => run.stage_id === 'local_synthesis' && run.node_id === nodeId && run.candidate_id === candidate.id);
  }
  synthesisAccepted(run) { return !!run && run.execution_status === 'Completed' && run.validation_status === 'Passed' && run.review_status === 'Accepted' && run.freshness === 'Current' && !!run.netlist; }
  priorFor(nodeId) { const run = this.synthesisFor(nodeId); return this.synthesisAccepted(run) ? run : undefined; }
  netlistFor(nodeId) {
    const candidate = this.candidateFor(nodeId), prior = this.priorFor(nodeId);
    if (!candidate || !prior) return undefined;
    const matches = (saved, current) => saved === undefined || saved === null || saved === current;
    return [...this.runs].reverse().find(run => run.stage_id === 'local_netlist_simulation' && run.node_id === nodeId &&
      run.candidate_id === candidate.id && run.prior_run_id === prior.id && run.netlist_sha256 === prior.netlist_sha256 &&
      matches(run.revision_id, candidate.revision_id) && matches(run.input_hash, candidate.input_hash) && matches(run.rtl_sha256, candidate.rtl_sha256));
  }
  netlistAccepted(run) { return !!run && run.execution_status === 'Completed' && run.validation_status === 'Passed' && run.review_status === 'Accepted' && run.freshness === 'Current'; }
  readinessFor(nodeId) { return this.project().envelope.generation?.nodes?.find(node => node.node_id === nodeId)?.behavioral_verification || this.candidateFor(nodeId)?.behavioral_verification; }
  netlistBlockerFor(nodeId) {
    if (!this.candidateFor(nodeId)) return { kind: 'candidate_required', message: 'Current accepted S04 RTL is required.' };
    if (!this.priorFor(nodeId)) return { kind: 'synthesis_required', message: 'The same RTL needs a current accepted S05 netlist.' };
    const readiness = this.readinessFor(nodeId);
    if (readiness?.available === false) return { kind: readiness.status || 'verification_unavailable', code: readiness.code, readiness, message: readiness.message || 'Behavioral verification is unavailable for this specification.' };
    return null;
  }
  netlistSummary() {
    const nodes = this.project().design.nodes || [], pending = nodes.filter(node => !this.netlistAccepted(this.netlistFor(node.id)));
    const failed = pending.filter(node => { const run = this.netlistFor(node.id); return run?.freshness === 'Current' && (run.execution_status === 'Failed' || run.validation_status === 'Failed'); });
    const blocked = pending.filter(node => this.netlistBlockerFor(node.id));
    const review = pending.filter(node => { const run = this.netlistFor(node.id); return run?.freshness === 'Current' && run.execution_status === 'Completed' && run.validation_status === 'Passed'; });
    const repairable = failed.filter(node => !this.repairGate(this.netlistFor(node.id)) && !this.netlistSetupFailure(this.netlistFor(node.id)));
    const availabilityCounts = Object.values(blocked.reduce((counts, node) => { const reason = availabilityReason(this.netlistBlockerFor(node.id)); counts[reason.kind] ||= {kind:reason.kind,label:reason.label,count:0}; counts[reason.kind].count++; return counts; }, {}));
    return { total: nodes.length, accepted: nodes.length - pending.length, failed: failed.length, blocked: blocked.length,
      availabilityCounts,
      implementationRequired: blocked.filter(node => availabilityReason(this.netlistBlockerFor(node.id))?.kind === 'implementation').length,
      prerequisitesMissing: blocked.filter(node => availabilityReason(this.netlistBlockerFor(node.id))?.kind !== 'implementation').length,
      repairable: repairable.length, firstRepairable: repairable[0],
      runnable: pending.length - blocked.length, firstIncomplete: pending[0], firstFailed: failed[0], firstBlocked: blocked[0], firstReview: review[0] };
  }
  repairStatusFor(nodeId, run) {
    const status = this.project().envelope.workflow_nodes?.find(node => node.node_id === nodeId && (!node.stage_id || node.stage_id === 'local_synthesis'))?.repair_status;
    return status && run?.stage_id === 'local_synthesis' && run.freshness === 'Current' && status.run_id === run.id &&
      status.candidate_id === this.candidateFor(nodeId)?.id ? status : null;
  }
  synthesisProgress() { const nodes = this.project().design.nodes || []; return { total: nodes.length, accepted: nodes.filter(node => this.synthesisAccepted(this.synthesisFor(node.id))).length }; }
  synthesisSummary() {
    const nodes = this.project().design.nodes || [];
    const incomplete = nodes.filter(node => !this.synthesisAccepted(this.synthesisFor(node.id)));
    const failed = incomplete.filter(node => { const run = this.synthesisFor(node.id); return run?.freshness === 'Current' && (run.execution_status === 'Failed' || run.validation_status === 'Failed'); });
    const sameRtlRetry = failed.filter(node => !!workflowSameRtlRecovery(this.synthesisFor(node.id)));
    return { ...this.synthesisProgress(), failed: failed.length, missing: incomplete.filter(node => !this.synthesisFor(node.id)).length,
      blocked: incomplete.filter(node => !this.candidateFor(node.id)).length, firstIncomplete: incomplete[0], firstFailed: failed[0],
      sameRtlRetry: sameRtlRetry.length, firstSameRtlRetry: sameRtlRetry[0], sameRtlRetryMessage: sameRtlRetry[0] && workflowSameRtlRecovery(this.synthesisFor(sameRtlRetry[0].id)) };
  }
  blocker() {
    const project = this.project();
    const blocked = (kind, message, details = {}) => ({ kind, message, nodeId: this.nodeId, ...details });
    if (project.envelope.repair_analysis?.active_job_id) return blocked('active_operation', 'Repair guidance analysis is active. Inspect or cancel it before running tools.');
    if (!project.envelope.workflow.find(stage => stage.id === project.stage)?.implemented) return blocked('stage_unimplemented', 'This execution stage is not implemented by the connected service.');
    if (this.storageError) return blocked('storage_error', `Workflow storage error: ${this.storageError.message || this.storageError.code}.`);
    if (project.conflict) return blocked('conflict', 'A newer saved design was detected. Export your draft, then Open saved.');
    if (project.dirty) return blocked('unsaved', 'Save the current design before running this stage.');
    if (project.postlayoutRunning) return blocked('active_operation', 'A post-layout tool run is active. Inspect or cancel it before starting another operation.');
    if (project.lvsRunning) return blocked('active_operation', 'An LVS tool run is active. Inspect or cancel it before starting another.');
    if (this.callbacks.batch?.()?.activeBatch() || this.activeBatch() || this.runs.some(active)) return blocked('active_operation', 'A local tool run or generation/synthesis batch is active. Inspect its recorded progress or cancel it before starting another.');
    if (!this.candidate()) return blocked('candidate_required', 'This node needs a current RTL candidate with accepted interface checks. Return to Local RTL Generation.');
    if (project.stage === 'local_netlist_simulation' && !this.prior()) return blocked('synthesis_required', 'Generic synthesis of this same candidate must pass and be accepted before its netlist is verified.');
    if (project.stage === 'local_netlist_simulation') {
      const readiness = this.verificationReadiness();
      if (readiness?.available === false) return blocked(
        ['implementation_required', 'input_required', 'configuration_required'].includes(readiness.status) ? readiness.status : 'verification_unavailable',
        readiness.status === 'implementation_required' ? 'S05 synthesis is accepted. S06 needs a behavioral checker for this saved specification.' : `S06 netlist verification is unavailable: ${readiness.message}`,
        { code: readiness.code, readiness, candidateId: this.candidate().id, priorRunId: this.prior().id });
    }
    return null;
  }
  gate() { return this.blocker()?.message || ''; }
  repairGate(run = this.selected()) {
    const project = this.project(), nodeId = run?.node_id || this.nodeId, candidate = this.candidateFor(nodeId), prior = this.priorFor(nodeId);
    const latest = [...this.runs].reverse().find(item => item.node_id === nodeId && item.stage_id === project.stage);
    if (project.envelope.repair_analysis?.active_job_id) return 'Repair guidance analysis is active. Inspect or cancel it before preparing another repair.';
    if (project.readOnly || project.envelope.workspace_identity?.read_only) return 'This preserved system is read-only.';
    if (project.dirty || project.conflict) return 'Save or reopen the current design before preparing a repair.';
    if (this.batchStartUncertain || this.batchPollError || this.pollError) return 'Reconnect to confirm the saved execution result before preparing a repair.';
    if (this.busy || project.busy || project.postlayoutRunning || project.lvsRunning || this.callbacks.batch?.()?.activeBatch() || this.activeBatch?.() || this.runs.some(active) ||
        (project.envelope.generation?.jobs || []).some(job => active(job) || job.execution_status === 'Completed' && !job.finished_at) ||
        ['global_generation', 'global_workflow', 'physical_workflow', 'drc_workflow', 'lvs_workflow', 'postlayout_workflow'].some(key =>
          [...(project.envelope[key]?.runs || []), ...(project.envelope[key]?.jobs || [])].some(active))) return 'Wait for the active operation to finish.';
    if (this.storageError || project.envelope.generation?.storage_error) return 'Resolve the saved-history storage error first.';
    if (workflowSameRtlRecovery(run)) return workflowSameRtlRecovery(run);
    if (!this.callbacks.prepareRepair) return 'The RTL repair connection is unavailable.';
    if (project.stage === 'local_synthesis') {
      if (!run || run.stage_id !== 'local_synthesis' || latest?.id !== run.id ||
          run.freshness !== 'Current' || !run.finished_at || !['Completed', 'Failed'].includes(run.execution_status) ||
          !(['Failed', 'Unsupported'].includes(run.validation_status) || run.execution_status === 'Failed')) return 'Select the latest current failed S05 result.';
      if (!candidate?.rtl || candidate.execution_status !== 'Completed' || candidate.validation_status !== 'Passed' ||
          ![run.input_hash, run.rtl_sha256].every(hash => typeof hash === 'string' && hash.length > 0) ||
          run.candidate_id !== candidate.id || run.revision_id !== candidate.revision_id || run.input_hash !== candidate.input_hash ||
          run.rtl_sha256 !== candidate.rtl_sha256 || run.requested_revision_id !== project.envelope.revision.id) return 'The failed result must use this node’s current accepted RTL and saved specification.';
      if (this.synthesisSetupFailure(run)) return 'Correct the trusted Yosys setup, then rerun S05. No RTL defect has been established.';
      if (run.validation_status === 'Unsupported') return 'Inspect the unsupported synthesis result and tool configuration, then rerun S05.';
      return '';
    }
    if (project.stage !== 'local_netlist_simulation' || !run || run.stage_id !== 'local_netlist_simulation' ||
        latest?.id !== run.id || run.freshness !== 'Current' || !run.finished_at ||
        !['Completed', 'Failed'].includes(run.execution_status) || !(run.validation_status === 'Failed' || run.execution_status === 'Failed')) return 'Select the latest current failed S06 result.';
    if (!candidate?.rtl || candidate.execution_status !== 'Completed' || candidate.validation_status !== 'Passed' ||
        ![run.input_hash, run.rtl_sha256, run.netlist_sha256, run.vector_hash, run.testbench_sha256].every(hash => typeof hash === 'string' && hash.length > 0) ||
        run.candidate_id !== candidate.id || run.revision_id !== candidate.revision_id || run.input_hash !== candidate.input_hash ||
        run.rtl_sha256 !== candidate.rtl_sha256 || run.requested_revision_id !== project.envelope.revision.id) return 'The failed result must use this node’s current accepted RTL and saved specification.';
    if (!prior || run.prior_run_id !== prior.id || run.netlist_sha256 !== prior.netlist_sha256 ||
        prior.rtl_sha256 !== candidate.rtl_sha256 || prior.input_hash !== candidate.input_hash) return 'The failed result must use the exact current accepted S05 netlist.';
    if (this.netlistSetupFailure(run)) return 'Correct the simulator setup or timeout, then rerun S06. No RTL defect has been established.';
    return '';
  }
  netlistSetupFailure(run = this.selected()) {
    const codes = [run?.error?.code, ...(run?.diagnostics || []).map(item => item.code)];
    return run?.checks?.executed === false || codes.some(code => ['compiler_unavailable', 'invalid_compiler', 'simulator_unavailable', 'invalid_simulator', 'unsupported_compiler'].includes(code)) ||
      (run?.checks?.commands || []).some(command => command.status === 'Timeout');
  }
  firstFailure(run = this.selected()) {
    return (String(run?.checks?.stdout || '').split(/\r?\n/).find(line => line.includes('HULLCIRQ_FAIL')) || '').trim().slice(0, 1200);
  }
  firstSynthesisFailure(run = this.selected()) {
    const lines = [run?.checks?.stderr, run?.checks?.stdout].filter(Boolean).join('\n').split(/\r?\n/).map(line => line.trim()).filter(Boolean);
    return (lines.find(line => /\b(error|fatal)\b|assertion failed|syntax error/i.test(line)) || lines.slice(-6).join('\n') || String(run?.error?.message || '')).slice(0, 1200);
  }
  synthesisSetupFailure(run = this.selected()) {
    const codes = [run?.error?.code, ...(run?.diagnostics || []).map(item => item.code)];
    return !!workflowSameRtlRecovery(run) || run?.checks?.executed === false || codes.some(code => ['synthesizer_unavailable', 'invalid_synthesizer', 'unsupported_synthesizer'].includes(code));
  }
  synthesisRecoveryHint(run = this.selected()) {
    if (workflowSameRtlRecovery(run)) return workflowSameRtlRecovery(run);
    if (this.synthesisSetupFailure(run)) return 'Yosys did not execute or its setup was rejected. Correct the trusted tool configuration, then rerun S05.';
    if ((run?.checks?.commands || []).some(command => command.status === 'Timeout')) return 'The synthesis command timed out. Inspect the log and tool setup, then rerun; repair RTL only if the log identifies an RTL problem.';
    return 'Inspect the saved Yosys error. Rerun S05 for a tool issue, or prepare an S04 repair for an RTL issue; the error alone does not establish its cause.';
  }
  repairInstruction(run, note = '') {
    if (run.stage_id === 'local_synthesis') {
      const checks = run.checks || {};
      const diagnostics = (run.diagnostics || []).slice(0, 6).map(item => `${item.code || 'Check'}: ${item.message || ''}`.slice(0, 300));
      const commands = (checks.commands || []).map(command => ({ command: command.command, status: command.status, exit_code: command.exit_code, error: command.error }));
      return [
        'Repair this exact RTL candidate using the saved S05 synthesis evidence below. Preserve the saved specification and external interface. The failed tool result alone does not prove an RTL defect; do not change RTL to mask a tool configuration error or timeout.',
        `S05 run: ${run.id}; node: ${run.node_id}; candidate: ${run.candidate_id}`,
        `Source revision: ${run.revision_id}; requested revision: ${run.requested_revision_id}; input SHA-256: ${run.input_hash}; RTL SHA-256: ${run.rtl_sha256}`,
        `Tool version: ${String(checks.tool_version || 'Not recorded').slice(0, 200)}; executed: ${String(checks.executed)}; exit code: ${String(checks.exit_code)}`,
        `Saved tool configuration (excerpt): ${JSON.stringify(run.tool_configuration || {}).slice(0, 500)}`,
        `Saved commands and outcomes (excerpt): ${JSON.stringify(commands).slice(0, 700)}`,
        `First synthesis log excerpt: ${this.firstSynthesisFailure(run) || 'No log excerpt recorded.'}`,
        `S05 diagnostics (up to 6 excerpts):\n${diagnostics.join('\n') || 'No diagnostic message recorded.'}`,
        run.error ? `S05 execution error (excerpt): ${String(run.error.code || '')}: ${String(run.error.message || '').slice(0, 500)}` : '',
        `Saved stderr (excerpt):\n${String(checks.stderr || '').slice(0, 1000) || 'Empty'}`,
        `Saved stdout (excerpt):\n${String(checks.stdout || '').slice(-1000) || 'Empty'}`,
        note.trim() ? `Human correction request (excerpt): ${note.trim().slice(0, 800)}` : '',
        `These are bounded excerpts. Complete checks, commands, stdout, stderr and source lineage remain in saved S05 run ${run.id}; retain that run and its original RTL. Return a complete corrected Verilog-2005 module. Prepare Context Preview, then explicitly send Repair node RTL. The new candidate must pass S04 interface checks and S05 synthesis again; S06 verifies circuit behavior. This repair draft does not establish a pass.`,
      ].filter(Boolean).join('\n').slice(0, 7900);
    }
    const failure = this.firstFailure(run);
    const diagnostics = (run.diagnostics || []).slice(0, 8).map(item => `${item.code || 'Check'}: ${item.message || ''}`.slice(0, 400));
    const parts = [
      'Repair this exact RTL candidate using the failed S06 netlist verification evidence below. Preserve the saved specification, interface and original verification inputs; do not weaken the test or change its expectations.',
      `S06 run: ${run.id}; node: ${run.node_id}; candidate: ${run.candidate_id}`,
      `Source revision: ${run.revision_id}; requested revision: ${run.requested_revision_id}; input SHA-256: ${run.input_hash}; RTL SHA-256: ${run.rtl_sha256}`,
      `Accepted S05 run: ${run.prior_run_id}; netlist SHA-256: ${run.netlist_sha256}`,
      `Original vectors SHA-256: ${run.vector_hash}; testbench SHA-256: ${run.testbench_sha256}`,
      `Frozen verification plan: ${JSON.stringify(Object.fromEntries(['kind', 'version', 'testbench_template_version', 'contract_hash', 'source_job_hash', 'reference_trace_hash', 'plan_sha256'].filter(key => run.verification_plan?.[key] !== undefined).map(key => [key, run.verification_plan[key]])))}`,
      failure ? `First HULLCIRQ_FAIL line (excerpt): ${failure}` : 'No HULLCIRQ_FAIL line was recorded. Inspect the saved tool error before assuming a circuit behavior mismatch.',
      diagnostics.length ? `S06 diagnostics (up to 8 excerpts):\n${diagnostics.join('\n')}` : `S06 execution error: ${String(run.error?.message || 'No diagnostic message recorded.').slice(0, 800)}`,
      note.trim() ? `Human correction request (excerpt): ${note.trim().slice(0, 1200)}` : '',
      `These are bounded excerpts. Complete checks, commands, stdout, stderr and the frozen original-input plan remain in saved S06 run ${run.id}. Return a complete corrected Verilog-2005 module. S05 synthesis and S06 verification must be rerun for the new RTL; this repair draft does not establish a pass.`,
    ];
    // Fewer than 8,000 UTF-16 code units stay under the backend's 32 KiB UTF-8 instruction limit.
    return parts.filter(Boolean).join('\n').slice(0, 7900);
  }
  prepareRepair(run = this.selected(), note = '') {
    const gate = this.repairGate(run);
    if (gate) { this.callbacks.toast?.(gate); return false; }
    const batch = this.callbacks.batch?.();
    if (this.project().stage === 'local_synthesis' && batch?.prepare) {
      // One-node and all-node S05 recovery use the same evidence-budgeted preview.
      batch.instruction = note.trim();
      batch.prepare('synthesis_repair', [run.node_id]);
      return true;
    }
    return this.callbacks.prepareRepair(this.candidateFor(run.node_id), this.repairInstruction(run, note)) !== false;
  }
  prepareNetlistRepairs(failures) {
    const batch = this.callbacks.batch?.();
    const eligible = failures.filter(({ run }) => !this.repairGate(run) && !this.netlistSetupFailure(run));
    if (!batch?.prepare || !eligible.length) return false;
    // This explicit action creates a new S06 draft. Do not carry an unrelated
    // old S05 correction into the newly source-bound netlist repair queue.
    batch.instruction = eligible.map(({ node, run }) => {
      const note = (this.feedback.get(run.id) || '').trim();
      return note ? `${node.name}: ${note}` : '';
    }).filter(Boolean).join('\n');
    batch.prepare('netlist_repair', eligible.map(({ node }) => node.id));
    return true;
  }
  render(host) {
    this.host = host;
    const project = this.project();
    if (!project.design.nodes.some(node => node.id === this.nodeId)) this.nodeId = project.design.nodes[0]?.id || null;
    const synthesis = project.stage === 'local_synthesis';
    host.replaceChildren(...[el('div', { class: 'spec-intro' }, badge(synthesis ? 'All nodes · separate synthesis runs' : 'All nodes · separate netlist verification runs'), badge('Generic · no PDK mapping'), el('p', { text: synthesis ? 'Run synthesis for all nodes from the saved RTL candidates. Current accepted results are reused; failed or missing nodes are processed separately. Behavioral simulation belongs to S06.' : 'Verify each node’s exact accepted S05 netlist against its original saved specification and inputs. One batch runs nodes sequentially; nodes with missing prerequisites or unimplemented checkers are listed separately. No extracted delay or physical verification is performed.' })),
      card(synthesis ? 'Synthesize all nodes' : 'Verify all node netlists', 'A saved batch schedules one node at a time and retains each result. Other eligible nodes continue when a node cannot run or fails.', el('div', { 'data-testid': 'workflow-batch' })),
      synthesis ? el('div', { 'data-testid': 'workflow-repair-batch-workspace' }) : el('div', { 'data-testid': 'workflow-netlist-recovery' }),
      el('div', { class: 'local-workflow-workspace' },
        card('Inspect or debug one node', synthesis ? 'Synthesize the selected interface-accepted RTL candidate with trusted Yosys when debugging. Use the all-node action above for normal progress.' : 'Use the all-node action above for normal progress. For debugging, freeze the selected node’s original-input verification plan and simulate its exact accepted S05 netlist.',
          el('div', { class: 'form-grid single' }, field('Target node', this.nodeId || '', value => { this.setNode(value); this.render(this.host); this.renderReview(this.reviewHost); }, { id: 'workflow-node', 'data-testid': 'workflow-node', choices: project.design.nodes.map(node => [node.id, `${node.name} · ${node.module_name}`]) })),
          el('div', { class: 'provider-actions' }, el('button', { type: 'button', text: synthesis ? 'Run synthesis for selected node' : 'Verify selected node netlist', 'data-testid': 'workflow-run', onclick: () => this.start() }), el('button', { type: 'button', text: 'Inspect node RTL', onclick: () => this.callbacks.navigate('local_rtl_generation', this.nodeId) })),
          el('p', { class: 'generation-gate', 'data-testid': 'workflow-gate' }), el('div', { class: 'workflow-lineage', 'data-testid': 'workflow-lineage' })),
        card('Execution evidence', synthesis ? 'Commands and synthesized netlist remain tied to the saved source RTL. S05 does not establish behavioral correctness.' : 'Commands, tool output and behavioral results remain tied to the exact accepted S05 netlist and the S06 frozen original-input verification plan.', el('div', { class: 'workflow-result', 'data-testid': 'workflow-result' }))),
      card('Saved node runs', 'Old results remain inspectable. Retry creates a new run; records are not overwritten.', el('div', { class: 'generation-job-list', 'data-testid': 'workflow-history' }))].filter(Boolean));
    this.refresh();
  }
  inspectBatchNode(nodeId, runId = null) {
    this.setNode(nodeId); this.runId = runId; this.runPinned = !!runId;
    const select = this.host?.querySelector('[data-testid="workflow-node"]');
    if (select) select.value = nodeId;
    this.refresh();
    this.host?.querySelector('[data-testid="workflow-result"]')?.scrollIntoView?.({ block: 'nearest', behavior: 'smooth' });
  }
  renderBatch() {
    const host = this.host?.querySelector('[data-testid="workflow-batch"]');
    if (!host || !STAGES.has(this.project().stage)) return;
    const synthesis = this.project().stage === 'local_synthesis', stageBatches = this.stageBatches();
    const batch = this.selectedBatch(), gate = this.batchGate(), progress = synthesis ? this.synthesisProgress() : this.netlistSummary();
    const earlierBatch = this.busy && this.batchRequestId && this.batchRequestStage === this.project().stage && batch?.request_id !== this.batchRequestId;
    const terminalIssue = batch && !active(batch) && (batch.execution_status !== 'Completed' || batch.validation_status !== 'Passed');
    const title = earlierBatch ? `Starting ${synthesis ? 'synthesis' : 'netlist verification'} · earlier saved batch below` : active(batch) ? `${synthesis ? 'Synthesis' : 'Netlist verification'} batch ${batch.execution_status.toLowerCase()}` : terminalIssue ? 'Batch finished · inspect unresolved nodes' : batch ? 'Batch finished' : synthesis ? 'Ready to synthesize all nodes' : 'Ready to verify all node netlists';
    const rows = (this.project().design.nodes || []).map(node => {
      const current = synthesis ? this.synthesisFor(node.id) : this.netlistFor(node.id), accepted = synthesis ? this.synthesisAccepted(current) : this.netlistAccepted(current), candidate = this.candidateFor(node.id);
      const blocker = synthesis ? !candidate ? { kind: 'candidate_required', message: 'Current accepted S04 RTL is required. Generate and accept this node in Local RTL Generation.' } : null : this.netlistBlockerFor(node.id);
      const readiness = blocker ? availabilityReason(blocker) : null;
      const item = batch?.items?.find(item => item.node_id === node.id);
      const status = resultLabel(current, accepted);
      const savedIssue = item && ['Blocked', 'Unsupported'].includes(item.status) ? availabilityReason({ ...item, ...(blocker || {}), reason: item.reason, diagnostics: current?.diagnostics }) : null;
      const savedStatus = savedIssue ? 'Not run' : item?.status === 'Skipped' ? 'Complete' : ['Queued', 'Running'].includes(item?.status) ? 'Running' : ['Failed', 'Cancelled', 'Interrupted'].includes(item?.status) ? 'Failed' : ['Passed', 'Completed'].includes(item?.status) ? 'Complete' : 'Not run';
      // The main Inspect action follows current RTL, even when an earlier
      // saved batch is displayed. Its original child remains in run history.
      const inspect = current;
      const repair = synthesis ? this.repairStatusFor(node.id, current) : null;
      return el('tr', { 'data-testid': `workflow-batch-node-${node.id}` }, el('th', { scope: 'row', text: node.name }), el('td', {}, badge(status, status === 'Complete' ? 'teal' : status === 'Failed' ? 'orange' : 'neutral'), synthesis && readiness ? el('div', {}, badge(readiness.label, 'orange'), el('small', { text: readiness.message })) : null, repair ? el('small', { text: repairOutcomeLabel(repair), 'data-testid': `workflow-s05-outcome-${node.id}` }) : null),
        !synthesis ? el('td', { 'data-testid': `workflow-batch-readiness-${node.id}`, title: readiness?.message || '' }, badge(readiness?.label || (accepted ? 'Complete' : 'Ready'), readiness ? 'orange' : accepted ? 'teal' : 'neutral'), readiness ? el('small', { text: ` ${readiness.message}` }) : el('small', { text: ` S05 ${this.priorFor(node.id)?.id || 'Not available'}` })) : null,
        el('td', {}, badge(savedStatus, savedStatus === 'Failed' ? 'orange' : savedStatus === 'Complete' ? 'teal' : 'neutral'),
          savedIssue ? el('div', {}, badge(savedIssue.label, 'orange'), el('small', { text: savedIssue.message })) : item?.reason ? el('small', { text: ` ${item.reason}` }) : ''),
        el('td', {}, el('button', { type: 'button', text: 'Inspect', 'data-testid': `workflow-batch-inspect-${node.id}`, onclick: () => this.inspectBatchNode(node.id, inspect?.id) }),
          blocker ? el('button', { type: 'button', text: blocker.kind === 'candidate_required' ? 'Open S04' : blocker.kind === 'synthesis_required' ? 'Open S05' : blocker.kind === 'configuration_required' ? 'Open settings' : 'Inspect requirements', 'data-testid': `workflow-batch-prerequisite-${node.id}`, onclick: () => this.callbacks.navigate(blocker.kind === 'candidate_required' ? 'local_rtl_generation' : blocker.kind === 'synthesis_required' ? 'local_synthesis' : blocker.kind === 'configuration_required' ? 'global_settings' : 'specifications', node.id) }) : null,
          !synthesis && current && ['Failed'].includes(current.validation_status) ? el('button', { type: 'button', text: 'Prepare S04 repair', 'data-testid': `workflow-batch-repair-${node.id}`, disabled: !!this.repairGate(current), title: this.repairGate(current) || 'Prepare a repair draft from this exact failed S06 result; no model request is sent.', onclick: () => this.prepareRepair(current, this.feedback.get(current.id) || '') }) : null));
    });
    host.replaceChildren(...[el('div', { class: 'generation-summary', 'data-testid': 'workflow-batch-status' }, ...[el('strong', { text: title }), badge(`${progress.accepted}/${progress.total} nodes adopted`, 'teal'),
      batch ? badge(`${earlierBatch ? 'Earlier · ' : ''}${resultLabel(batch, batch.execution_status === 'Completed' && batch.validation_status === 'Passed')}`, batch.validation_status === 'Passed' ? 'teal' : 'orange') : null].filter(Boolean)),
      el('div', { class: 'provider-actions' }, el('button', { type: 'button', class: 'primary', text: synthesis ? 'Run synthesis for all nodes' : 'Verify all node netlists', disabled: !!gate, title: gate || (synthesis ? 'Skip current accepted synthesis; run missing and unsuccessful nodes.' : 'Reuse current accepted S06 results; verify each remaining eligible node with its own original-input plan.'), 'data-testid': 'workflow-batch-run', onclick: () => this.startBatch() }),
        active(batch) && batch === this.activeBatch() ? el('button', { type: 'button', text: synthesis ? 'Cancel remaining synthesis' : 'Cancel remaining verification', 'data-testid': 'workflow-batch-cancel', onclick: () => this.cancelBatch(batch) }) : null),
      el('p', { class: 'generation-gate', 'data-testid': 'workflow-batch-gate', text: gate || (synthesis ? 'Accepted current results are skipped. Each other node retains its own result; S06 is not run.' : 'Current accepted S06 results are reused. Missing S05 sources and unavailable checkers are listed per node; other eligible nodes continue. No new RTL is generated.') }),
      this.batchPollError ? el('div', { class: 'generation-error', 'data-testid': 'workflow-batch-error' }, el('p', { text: this.batchPollError }), el('button', { type: 'button', text: 'Reconnect without resending', 'data-testid': 'workflow-batch-reconnect', onclick: () => this.reconnectBatch() })) : null,
      batch?.error ? el('div', { class: 'generation-error', text: `${batch.error.code || 'Batch error'} · ${batch.error.message || ''}` }) : null,
      el('div', { class: 'workflow-batch-table-scroll' }, el('table', { class: 'workflow-batch-table', 'data-testid': 'workflow-batch-nodes' }, el('thead', {}, el('tr', {}, ...(synthesis ? ['Node', 'Current S05 result', 'Saved batch result', 'Evidence'] : ['Node', 'Current S06 result', 'Readiness / S05 source', 'Saved batch result', 'Evidence']).map(text => el('th', { scope: 'col', text })))), el('tbody', {}, ...rows))),
      batch ? el('details', {}, el('summary', { text: 'Saved batch record' }), el('pre', { text: JSON.stringify(batch, null, 2), 'data-testid': 'workflow-batch-record' })) : null,
      stageBatches.length > 1 ? el('div', { class: 'generation-job-list', 'data-testid': 'workflow-batch-history' }, ...[...stageBatches].reverse().map(record => el('button', { type: 'button', class: `generation-job-button${record.id === batch?.id ? ' selected' : ''}`, onclick: () => { this.batchId = record.id; this.renderBatch(); } }, badge(record.execution_status), badge(record.validation_status), el('code', { text: record.id })))) : null].filter(Boolean));
  }
  renderNetlistRecovery() {
    const host = this.host?.querySelector('[data-testid="workflow-netlist-recovery"]');
    if (!host || this.project().stage !== 'local_netlist_simulation') return;
    const nodes = this.project().design.nodes || [], summary = this.netlistSummary();
    const failures = nodes.flatMap(node => {
      const run = this.netlistFor(node.id);
      return run && run.freshness === 'Current' && !active(run) && (run.validation_status === 'Failed' || run.execution_status === 'Failed') ? [{ node, run }] : [];
    });
    const interrupted = ['Cancelled', 'Interrupted'].includes(this.selectedBatch()?.execution_status);
    if (!failures.length && !summary.blocked && !interrupted) { host.replaceChildren(); return; }
    host.replaceChildren(card('Resolve node verification results', 'A failed simulation needs a source correction or a tool retry. An unavailable checker is a separate implementation requirement.',
      el('div', { class: 'generation-batch-body' },
        failures.some(({ run }) => !this.repairGate(run) && !this.netlistSetupFailure(run)) && this.callbacks.batch?.()?.prepare
          ? el('div', { class: 'provider-actions' }, el('button', { type: 'button', class: 'primary', text: 'Preview repairs for failed node netlists',
            'data-testid': 'workflow-netlist-repair-all', disabled: !!this.batchGate(), title: 'Prepare a separate source-bound S04 repair for each failed S06 node. Review the queue before starting the local model requests.',
            onclick: () => this.prepareNetlistRepairs(failures) })) : null,
        ...failures.map(({ node, run }) => {
          const gate = this.repairGate(run), setup = this.netlistSetupFailure(run);
          return el('section', { class: 'generation-recovery', 'data-testid': `workflow-netlist-failure-${node.id}` },
            el('h3', { text: node.name }),
            el('p', { text: this.firstFailure(run) || run.error?.message || (run.diagnostics || []).find(item => item.severity === 'error')?.message || 'Inspect the full saved simulation console.' }),
            el('p', { class: 'scope-note', text: setup ? 'Fix the simulator setup or timeout, then retry S06. RTL is retained.' : 'Prepare an S04 repair from this exact RTL, S05 netlist and failed original-input check. After the corrected RTL is accepted, rerun S05 and S06.' }),
            el('div', { class: 'provider-actions' },
              el('button', { type: 'button', class: 'primary', text: 'Prepare S04 RTL repair', 'data-testid': `workflow-netlist-prepare-repair-${node.id}`, disabled: !!gate, title: gate || 'Open the S04 repair draft. Preview and explicitly start the model request there.', onclick: () => this.prepareRepair(run, this.feedback.get(run.id) || '') }),
              el('button', { type: 'button', text: 'Inspect full failure', 'data-testid': `workflow-netlist-inspect-${node.id}`, onclick: () => this.inspectBatchNode(node.id, run.id) }),
              setup ? el('button', { type: 'button', text: 'Inspect simulator settings', 'data-testid': `workflow-netlist-configure-${node.id}`, onclick: () => this.callbacks.navigate('global_settings', node.id) }) : null,
              setup ? el('button', { type: 'button', text: 'Retry this node', 'data-testid': `workflow-netlist-retry-${node.id}`, disabled: !!this.batchGate(), onclick: () => { this.inspectBatchNode(node.id, run.id); return this.start(); } }) : null),
            gate ? el('p', { class: 'generation-gate', text: gate }) : null);
        }),
        summary.firstRepairable ? el('button', { type: 'button', text: `Prepare repair for ${summary.firstRepairable.name}`, 'data-testid': 'workflow-netlist-repair-first', onclick: () => this.prepareRepair(this.netlistFor(summary.firstRepairable.id)) }) : null,
        summary.blocked ? el('details', { open: true, 'data-testid': 'workflow-netlist-unavailable' }, el('summary', { text: summary.availabilityCounts.map(reason => `${reason.count} ${reason.label}`).join(' · ') }),
          ...nodes.filter(node => this.netlistBlockerFor(node.id)).map(node => { const blocker = this.netlistBlockerFor(node.id), reason = availabilityReason(blocker); return el('section', {}, el('strong', { text: node.name }), badge(reason.label, 'orange'), el('p', { text: reason.message }), blocker.kind === 'implementation_required' ? el('p', { class: 'scope-note', text: 'The saved test requirements exist, but their executable checker is not implemented. HuLLCirq development is required; repeating RTL generation or synthesis will not add it.' }) : null, el('button', { type: 'button', text: blocker.kind === 'synthesis_required' ? 'Inspect S05 source' : blocker.kind === 'candidate_required' ? 'Inspect S04 RTL' : blocker.kind === 'configuration_required' ? 'Inspect simulator settings' : 'Inspect saved requirements', 'data-testid': `workflow-netlist-prerequisite-${node.id}`, onclick: () => this.callbacks.navigate(blocker.kind === 'synthesis_required' ? 'local_synthesis' : blocker.kind === 'candidate_required' ? 'local_rtl_generation' : blocker.kind === 'configuration_required' ? 'global_settings' : 'specifications', node.id) })); })) : null,
        interrupted ? el('section', { 'data-testid': 'workflow-netlist-interrupted' }, el('p', { text: 'The batch stopped. Finished node results are retained; retry verifies the remaining eligible nodes.' }), el('button', { type: 'button', text: 'Retry remaining node checks', disabled: !!this.batchGate(), 'data-testid': 'workflow-netlist-retry-remaining', onclick: () => this.startBatch() })) : null)));
  }
  refresh() {
    if (!this.host?.isConnected || !STAGES.has(this.project().stage)) return;
    const gate = this.gate();
    const button = this.host.querySelector('[data-testid="workflow-run"]');
    if (!button) return;
    button.disabled = this.busy || !!gate; button.title = gate || 'Execute this saved node candidate with the trusted tool configuration.';
    this.host.querySelector('[data-testid="workflow-gate"]').textContent = this.busy ? 'Contacting local execution service…' : gate || 'Ready. Tool verification and adoption follow the saved policy.';
    const candidate = this.candidate(), prior = this.prior(), plan = this.selected()?.verification_plan;
    this.host.querySelector('[data-testid="workflow-lineage"]').replaceChildren(...[el('p', { text: `Project ${this.project().design.project.name} · source revision ${this.project().envelope.revision.id}` }),
      el('p', { text: `Candidate ${candidate?.id || 'No eligible candidate'} · RTL SHA-256 ${candidate?.rtl_sha256 || 'Not available'}` }),
      prior ? el('p', { text: `Prior synthesis ${prior.id} · netlist SHA-256 ${prior.netlist_sha256 || 'Not available'}` }) : null,
      plan ? el('details', {}, el('summary', { text: 'Recorded original-input verification plan' }), el('pre', { text: JSON.stringify(plan, null, 2) })) : null].filter(Boolean));
    this.renderBatch(); this.renderNetlistRecovery(); this.renderResult(); this.renderHistory();
    const repairHost = this.host.querySelector('[data-testid="workflow-repair-batch-workspace"]');
    if (repairHost) this.callbacks.batch?.()?.renderRepairs(repairHost);
    if (this.reviewHost?.isConnected) this.renderReview(this.reviewHost);
    this.callbacks.chrome?.();
  }
  renderResult() {
    const host = this.host?.querySelector('[data-testid="workflow-result"]');
    if (!host) return;
    const run = this.selected();
    if (!run) { host.replaceChildren(el('p', { class: 'empty-small', text: 'No execution evidence for this node and stage. No tool pass or netlist is inferred.' })); return; }
    const netlist = run.checks?.synthesis?.netlist || run.netlist || '';
    const consoleEvidence = toolConsoleEvidence(run);
    const failure = run.stage_id === 'local_netlist_simulation' && run.validation_status === 'Failed' ? this.firstFailure(run) : '';
    const synthesisFailure = run.stage_id === 'local_synthesis' && !active(run) && (['Failed', 'Unsupported'].includes(run.validation_status) || run.execution_status === 'Failed');
    const sameRtlRecovery = synthesisFailure && workflowSameRtlRecovery(run);
    const repairNote = synthesisFailure && !sameRtlRecovery ? el('textarea', { rows: 2, 'aria-label': 'Optional synthesis repair instruction', 'data-testid': 'workflow-synthesis-repair-note', value: this.feedback.get(run.id) || '', placeholder: 'Optional correction instruction.', oninput: event => this.feedback.set(run.id, event.target.value) }) : null;
    const currentSource = this.runCurrent(run);
    const repairStatus = this.repairStatusFor(run.node_id, run);
    host.replaceChildren(...[el('div', { class: 'generation-summary', 'data-testid': 'workflow-run-status' }, badge(run.execution_status), badge(run.validation_status, run.validation_status === 'Passed' && currentSource ? 'teal' : 'orange'), badge(currentSource ? 'Current source' : 'Earlier source', currentSource ? 'neutral' : 'orange'), el('code', { text: run.id })),
      !currentSource ? el('p', { class: 'scope-note', 'data-testid': 'workflow-historical-source', text: 'This saved result belongs to earlier sources. Its original pass and acceptance remain in history; they do not advance the current RTL or netlist.' }) : null,
      repairStatus ? el('section', { class: 'generation-recovery', 'data-testid': 'workflow-repair-outcome' }, el('h3', { text: repairOutcomeLabel(repairStatus) }),
        el('p', { text: repairStatus.outcome === 'passed' ? 'S05 passed for this candidate. Continue to S06 to check circuit behavior.' : repairStatus.reconsideration_required ? 'The previous repair did not resolve this problem. Review the original requirements, RTL difference and guidance before another repair.' : 'Compare this attempt with its saved source before preparing the next correction.' }),
        el('details', {}, el('summary', { text: 'Exact attempt comparison' }), el('pre', { text: JSON.stringify(repairStatus, null, 2), tabindex: 0 }))) : null,
      run.error ? el('div', { class: 'generation-error', text: `${run.error.code || 'Execution error'} · ${run.error.message || JSON.stringify(run.error)}` }) : null,
      failure ? el('div', { class: 'generation-error', 'data-testid': 'workflow-first-failure' }, el('strong', { text: 'First recorded simulation failure' }), el('p', { text: failure })) : null,
      synthesisFailure ? el('section', { class: 'generation-recovery', 'data-testid': 'workflow-synthesis-recovery' },
        el('h3', { text: 'Recover synthesis' }), el('p', { text: this.synthesisRecoveryHint(run) }),
        el('pre', { text: this.firstSynthesisFailure(run) || 'No tool log was recorded; inspect the saved error and commands.', 'data-testid': 'workflow-synthesis-first-failure' }),
        repairNote,
        sameRtlRecovery ? el('button', { type: 'button', text: 'Retry synthesis for all nodes · same RTL', 'data-testid': 'workflow-retry-same-rtl', disabled: !!this.batchGate() || !currentSource, title: this.batchGate() || 'Retry pending S05 nodes with their existing accepted RTL; no model request.', onclick: () => this.startBatch() }) :
          el('button', { type: 'button', text: 'Prepare RTL repair', 'data-testid': 'workflow-prepare-repair', disabled: !!this.repairGate(run), title: this.repairGate(run) || 'Carry the exact failed S05 evidence into an S04 draft, then preview before sending.', onclick: () => this.prepareRepair(run, repairNote.value) }),
        el('p', { class: 'generation-gate', text: sameRtlRecovery || this.repairGate(run) || 'Opens the S04 repair preview with this saved error. Review the queue, then select Start repair batch. The failed run and original RTL are retained.' })) : null,
      this.storageError ? el('div', { class: 'generation-error', text: `Storage error: ${this.storageError.message || JSON.stringify(this.storageError)}` }) : null,
      active(run) ? el('div', { class: 'generation-progress' }, el('span', { class: 'generation-spinner', 'aria-hidden': true }), el('span', { text: `${run.execution_status} · actual tool execution` }), el('button', { type: 'button', text: 'Cancel run', 'data-testid': 'workflow-cancel', onclick: () => this.cancel(run) })) : null,
      el('div', { class: 'generation-artifact' },
        el('p', { class: 'scope-note', text: run.stage_id === 'local_synthesis' ? 'Generic technology-independent synthesis. No SKY130 cell mapping, placement, routing, timing or physical verification.' : 'Finite-cycle, zero-delay simulation of the actual generic netlist. The initial saved vectors and independent reference define the tested conditions. No SDF or post-layout verification.' }),
        (run.diagnostics || []).map(item => el('div', { class: `diagnostic ${item.severity || 'info'}` }, badge(item.severity || 'info'), el('code', { text: item.code || '' }), el('span', { text: item.message || JSON.stringify(item) }))),
        el('section', { class: 'tool-console', 'data-testid': 'workflow-console' },
          el('h3', { text: 'Full saved tool console' }),
          el('p', { class: 'scope-note', text: 'All recorded commands and output are shown without excerpts. stdout and stderr are separate streams; their interleaving was not recorded.' }),
          el('div', { class: 'tool-console-actions' },
            el('button', { type: 'button', text: 'Jump to start', 'data-testid': 'workflow-console-top', onclick: () => { const output = this.host?.querySelector('[data-testid="workflow-console-output"]'); if (output) { output.scrollTop = 0; output.focus?.(); } } }),
            el('button', { type: 'button', text: 'Jump to end', 'data-testid': 'workflow-console-bottom', onclick: () => { const output = this.host?.querySelector('[data-testid="workflow-console-output"]'); if (output) { output.scrollTop = output.scrollHeight; output.focus?.(); } } })),
          el('pre', { class: 'tool-console-output', text: consoleEvidence.text, tabindex: 0, role: 'region', 'aria-label': 'Full saved tool console', 'data-testid': 'workflow-console-output' }),
          el('div', { class: 'generation-artifact-actions tool-console-actions' },
            el('button', { type: 'button', text: 'Download full console', 'data-testid': 'workflow-download-console', onclick: () => textDownload(consoleEvidence.text, `${safe(run.id)}-console.txt`) }),
            el('button', { type: 'button', text: 'Download stdout', 'data-testid': 'workflow-download-stdout', disabled: !consoleEvidence.stdout, onclick: () => textDownload(consoleEvidence.stdout, `${safe(run.id)}-stdout.txt`) }),
            el('button', { type: 'button', text: 'Download stderr', 'data-testid': 'workflow-download-stderr', disabled: !consoleEvidence.stderr, onclick: () => textDownload(consoleEvidence.stderr, `${safe(run.id)}-stderr.txt`) }))),
        el('details', { open: run.stage_id !== 'local_synthesis' }, el('summary', { text: 'Actual checks, commands, logs and results' }), el('pre', { text: JSON.stringify(run.checks || {}, null, 2), 'data-testid': 'workflow-checks' })),
        el('details', {}, el('summary', { text: 'Frozen input and candidate lineage' }), el('pre', { text: JSON.stringify({ node_id: run.node_id, candidate_id: run.candidate_id, revision_id: run.revision_id, requested_revision_id: run.requested_revision_id, input_hash: run.input_hash, design_hash: run.design_hash, rtl_sha256: run.rtl_sha256, netlist_sha256: run.netlist_sha256, vector_hash: run.vector_hash, testbench_sha256: run.testbench_sha256, prior_run_id: run.prior_run_id, verification_plan: run.verification_plan }, null, 2), 'data-testid': 'workflow-frozen-input' })),
        netlist ? el('details', {}, el('summary', { text: 'Actual generated netlist' }), el('pre', { text: netlist, 'data-testid': 'workflow-netlist' })) : null,
        el('p', { class: 'scope-note', text: 'JSON previews use browser number precision. Downloads preserve the backend’s exact integers.' }),
        el('div', { class: 'generation-artifact-actions' }, el('button', { type: 'button', text: 'Download run JSON', 'data-testid': 'workflow-download-run', onclick: () => downloadJsonResponse(`/api/workflow/runs/${encodeURIComponent(run.id)}`, `${safe(run.id)}.json`, this.callbacks.notify) }),
          netlist ? el('button', { type: 'button', text: 'Download netlist', 'data-testid': 'workflow-download-netlist', onclick: () => textDownload(netlist, `${safe(run.id)}-netlist.v`) }) : null,
          run.verification_plan ? el('button', { type: 'button', text: 'Download initial verification plan', 'data-testid': 'workflow-download-plan', onclick: () => downloadJsonResponse(`/api/artifacts/workflow/${encodeURIComponent(run.id)}/verification-plan`, `${safe(run.id)}-verification-plan.json`, this.callbacks.notify) }) : null,
          el('button', { type: 'button', text: 'Rerun this node', 'data-testid': 'workflow-rerun', disabled: this.busy || !!this.gate(), onclick: () => this.start() })),
        this.pollError ? el('div', { class: 'generation-error' }, this.pollError, el('button', { type: 'button', text: 'Reconnect without resending', 'data-testid': 'workflow-reconnect', onclick: () => { this.pollError = null; this.poll(true); } })) : null)].filter(Boolean));
  }
  renderHistory() {
    const host = this.host?.querySelector('[data-testid="workflow-history"]');
    if (!host) return;
    host.replaceChildren(...(this.relevant().length ? this.relevant().map(run => el('button', { type: 'button', class: `generation-job-button${run.id === this.selected()?.id ? ' selected' : ''}`, 'data-testid': `workflow-history-${run.id}`, onclick: () => { this.runId = run.id; this.runPinned = true; this.refresh(); } }, badge(run.execution_status), badge(run.validation_status), badge(run.review_status), badge(this.runCurrent(run) ? 'Current source' : 'Earlier source'), el('code', { text: run.id }), el('small', { text: `Candidate ${run.candidate_id} · ${run.created_at}` }))) : [el('p', { class: 'empty-small', text: 'No recorded tool runs for this node.' })]));
  }
  renderReview(host) {
    if (!host) return;
    this.reviewHost = host;
    const run = this.selected();
    if (!run) { host.replaceChildren(el('p', { class: 'empty-small', text: 'Run this saved node to inspect actual results and its adoption decision.' })); return; }
    const project = this.project();
    const current = this.runCurrent(run);
    const latest = this.relevant()[0]?.id === run.id;
    const accepted = run.review_status === 'Accepted';
    const decision = [...this.reviews].reverse().find(item => item.run_id === run.id && item.decision === 'accepted');
    const eligible = !project.dirty && !project.conflict && !this.busy && current && latest && !active(run);
    const note = el('textarea', { rows: 3, 'aria-label': 'Tool run review note', 'data-testid': 'workflow-feedback', value: this.feedback.get(run.id) || '', oninput: event => this.feedback.set(run.id, event.target.value), placeholder: 'Record a concern, requested repair or manual adoption reason.' });
    const activeNote = host.contains(document.activeElement) && document.activeElement.dataset.testid === 'workflow-feedback' ? document.activeElement : null;
    const selection = activeNote ? [activeNote.selectionStart, activeNote.selectionEnd] : null;
    const next = project.stage === 'local_synthesis' ? 'local_netlist_simulation' : 'node_implementation_specs';
    const nextImplemented = project.envelope.workflow.find(stage => stage.id === next)?.implemented;
    host.replaceChildren(el('div', { class: 'generation-review-status' }, badge(run.review_status, accepted ? 'teal' : 'neutral'), badge(current ? 'Current' : 'Stale'), el('code', { text: run.id })),
      el('p', { class: 'scope-note', 'data-testid': 'workflow-adoption-provenance', text: accepted ? adoptionProvenance(decision) : 'The saved adoption policy determines eligibility after all required checks finish. Failed, stale and unsupported results remain unaccepted.' }),
      el('div', { class: 'field' }, el('label', { text: 'Review and debug feedback' }), note),
      el('div', { class: 'review-actions' },
        el('button', { type: 'button', class: 'primary', text: accepted ? 'Run accepted' : 'Accept verified run', 'data-testid': 'workflow-accept', disabled: !eligible || accepted || run.validation_status !== 'Passed', onclick: () => this.review(run, 'accepted', note.value) }),
        el('button', { type: 'button', text: 'Request Changes', 'data-testid': 'workflow-request-changes', disabled: !eligible, onclick: () => this.review(run, 'changes_requested', note.value) }),
        el('button', { type: 'button', text: 'Return to node RTL', 'data-testid': 'workflow-return-rtl', disabled: !eligible, onclick: () => this.review(run, 'return_to_stage', note.value, 'local_rtl_generation') }),
        workflowSameRtlRecovery(run) ? el('button', { type: 'button', text: 'Retry synthesis for all nodes · same RTL', 'data-testid': 'workflow-review-retry-same-rtl', disabled: !eligible || !!this.batchGate(), title: this.batchGate() || workflowSameRtlRecovery(run), onclick: () => this.startBatch() }) :
          el('button', { type: 'button', text: 'Prepare RTL repair', 'data-testid': project.stage === 'local_synthesis' ? 'workflow-review-prepare-repair' : 'workflow-prepare-repair', disabled: !!this.repairGate(run), title: this.repairGate(run) || `Carry this exact failed ${project.stage === 'local_synthesis' ? 'S05' : 'S06'} evidence into an S04 repair draft. Preview it before sending a model request.`, onclick: () => this.prepareRepair(run, note.value) }),
        el('button', { type: 'button', text: next === 'local_netlist_simulation' ? 'Continue selected node to Netlist Simulation' : nextImplemented ? 'Continue selected node to Implementation Specs' : 'Node Implementation Specs · not implemented', 'data-testid': 'workflow-continue', disabled: !eligible || !accepted || run.validation_status !== 'Passed' || !nextImplemented, onclick: () => this.callbacks.navigate(next, this.nodeId) })),
      el('details', { class: 'raw-result' }, el('summary', { text: 'Exact adoption and feedback records' }), el('pre', { text: JSON.stringify(this.reviews.filter(item => item.run_id === run.id), null, 2) })));
    if (activeNote) { note.focus({ preventScroll: true }); note.setSelectionRange(...selection); }
  }
  async startBatch() {
    if (this.batchGate()) return;
    const project = this.project(), identity = this.identity(), stage = project.stage;
    if (this.batchRequestStage && this.batchRequestStage !== stage) this.batchRequestId = null;
    this.batchRequestStage = stage;
    this.batchRequestId ||= globalThis.crypto?.randomUUID?.() || `${stage === 'local_netlist_simulation' ? 's06' : 's05'}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
    const requestId = this.batchRequestId;
    this.busyStage = stage;
    this.busy = true; this.refresh();
    try {
      const envelope = await this.callbacks.request('workflow/batches/start', { revision_id: project.envelope.revision.id, request_id: requestId, ...(stage === 'local_netlist_simulation' ? { stage_id: stage } : {}) });
      if (identity !== this.identity()) return;
      this.batchId = envelope.workflow_batches?.find(batch => batch.request_id === requestId && this.batchStage(batch) === stage)?.id;
      this.batchPollError = null; this.batchStartUncertain = false; this.batchRequestId = null;
      this.callbacks.envelope(envelope); this.callbacks.toast?.(stage === 'local_netlist_simulation' ? 'Netlist verification batch saved. Each eligible node uses its accepted S05 netlist and original inputs; missing prerequisites and unimplemented checkers are listed per node.' : 'Synthesis batch saved. Current accepted results are reused; each remaining node records its own synthesis result.');
    } catch (error) {
      if (identity !== this.identity()) return;
      // A lost response is ambiguous: inspect saved state before any explicit retry.
      this.batchStartUncertain = !error.status || error.status >= 500;
      this.batchPollError = this.batchStartUncertain ? `${error.message} The start request was not resent. Reconnect to check the saved batch.` : null;
      this.callbacks.notify?.(error.message, 'error');
    } finally { if (identity === this.identity()) { this.busy = false; this.busyStage = null; this.refresh(); this.schedule(); } }
  }
  async cancelBatch(batch = this.activeBatch()) {
    if (!active(batch) || this.busy) return;
    const identity = this.identity(); this.busyStage = this.batchStage(batch); this.busy = true; this.refresh();
    try {
      const envelope = await this.callbacks.request(`workflow/batches/${encodeURIComponent(batch.id)}/cancel`, {});
      if (identity === this.identity()) {
        this.batchPollError = null; this.batchStartUncertain = false; this.batchRequestId = null;
        this.callbacks.envelope(envelope);
      }
    } catch (error) { if (identity === this.identity()) this.callbacks.notify?.(error.message, 'error'); }
    finally { if (identity === this.identity()) { this.busy = false; this.busyStage = null; this.refresh(); this.schedule(); } }
  }
  async reconnectBatch() {
    if (this.polling) return;
    const identity = this.identity(); this.polling = true;
    try {
      const envelope = await this.callbacks.request('project');
      if (identity !== this.identity()) return;
      const recovered = envelope.workflow_batches?.find(batch => batch.request_id === this.batchRequestId && this.batchStage(batch) === (this.batchRequestStage || this.project().stage));
      if (recovered) { this.batchId = recovered.id; this.batchRequestId = null; }
      this.batchStartUncertain = false; this.batchPollError = null;
      this.callbacks.envelope(envelope);
    } catch (error) { if (identity === this.identity()) { this.batchPollError = `${error.message} The batch was not resent.`; this.refresh(); } }
    finally { if (identity === this.identity()) { this.polling = false; this.schedule(); } }
  }
  async start() {
    if (this.busy || this.gate()) return;
    const candidate = this.candidate(), project = this.project();
    this.busyStage = project.stage;
    this.busy = true; this.refresh();
    try {
      const envelope = await this.callbacks.request('workflow/start', { stage_id: project.stage, node_id: this.nodeId, candidate_id: candidate.id, revision_id: project.envelope.revision.id });
      this.runId = envelope.workflow_runs?.filter(run => run.node_id === this.nodeId && run.stage_id === project.stage).at(-1)?.id;
      this.pollError = null; this.callbacks.envelope(envelope); this.callbacks.toast(project.stage === 'local_synthesis' ? 'Synthesis started from the frozen interface-accepted RTL candidate.' : 'Netlist verification started from the accepted S05 netlist and the frozen original-input verification plan.');
    } catch (error) { this.callbacks.notify(error.message, 'error'); }
    finally { this.busy = false; this.busyStage = null; this.refresh(); this.schedule(); }
  }
  async cancel(run) { try { this.callbacks.envelope(await this.callbacks.request('workflow/cancel', { run_id: run.id })); } catch (error) { this.callbacks.notify(error.message, 'error'); } }
  async review(run, decision, note, target) {
    if (decision !== 'accepted' && !note.trim()) { this.callbacks.toast('Record a reason for requesting changes or returning to RTL.'); return; }
    this.busyStage = run.stage_id || this.project().stage;
    this.busy = true; this.refresh();
    try {
      this.callbacks.envelope(await this.callbacks.request('workflow/review', { run_id: run.id, decision, note: note.trim(), ...(target ? { target_stage: target } : {}) }));
      if (target) this.callbacks.navigate(target, this.nodeId);
    } catch (error) { this.callbacks.notify(error.message, 'error'); }
    finally { this.busy = false; this.busyStage = null; this.refresh(); }
  }
  schedule() { if (this.pollTimer || this.polling || !(this.activeBatch() && !this.batchPollError || this.runs.some(active) && !this.pollError && !this.batchPollError)) return; this.pollTimer = setTimeout(() => { this.pollTimer = null; this.poll(); }, 1300); }
  async poll(force = false) {
    if (this.polling) return;
    if (this.activeBatch() || force && this.selectedBatch()) { await this.pollBatch(force); return; }
    const run = this.runs.find(active) || (force ? this.selected() : null);
    if (!run) return;
    const identity = this.identity();
    this.polling = true;
    try {
      const updated = await this.callbacks.request(`workflow/runs/${encodeURIComponent(run.id)}`);
      if (identity !== this.identity()) return;
      const index = this.runs.findIndex(item => item.id === updated.id); if (index >= 0) this.runs[index] = updated; else this.runs.push(updated);
      this.pollError = null; this.refresh();
      this.pollCount = (this.pollCount || 0) + 1;
      if (!active(updated) || this.pollCount % 3 === 0) { const envelope = await this.callbacks.request('project'); if (identity === this.identity()) this.callbacks.envelope(envelope); }
    } catch (error) { if (identity === this.identity()) { this.pollError = `${error.message} The tool run is not resent.`; this.refresh(); } }
    finally { if (identity === this.identity()) { this.polling = false; this.schedule(); } }
  }
  async pollBatch(force = false) {
    if (this.polling) return;
    const batch = this.activeBatch() || (force ? this.selectedBatch() : null);
    if (!batch) return;
    const identity = this.identity(); this.polling = true;
    try {
      const updated = await this.callbacks.request(`workflow/batches/${encodeURIComponent(batch.id)}`);
      if (identity !== this.identity()) return;
      const index = this.batches.findIndex(item => item.id === updated.id); if (index >= 0) this.batches[index] = updated; else this.batches.push(updated);
      this.batchPollError = null; this.refresh();
      // A batch stays active between child runs; refresh runs and policy adoption every tick.
      const envelope = await this.callbacks.request('project');
      if (identity === this.identity()) this.callbacks.envelope(envelope);
    } catch (error) { if (identity === this.identity()) { this.batchPollError = `${error.message} The batch was not resent.`; this.refresh(); } }
    finally { if (identity === this.identity()) { this.polling = false; this.schedule(); } }
  }
}
