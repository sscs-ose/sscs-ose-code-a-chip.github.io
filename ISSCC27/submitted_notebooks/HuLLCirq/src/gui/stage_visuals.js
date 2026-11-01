/** Read-only overview facts. Execution gates remain in their owning modules. */
import { stageVisualState } from './visual_state.js';

const adopted = stage => stage?.execution_status === 'Completed' && stage.validation_status === 'Passed' && stage.review_status === 'Accepted' && stage.freshness === 'Current' && !(stage.required_node_count > 0 && stage.accepted_node_count !== stage.required_node_count);
const DATA = { global_rtl_generation: 'global_generation', global_synthesis: 'global_workflow', global_netlist_simulation: 'global_workflow', layout: 'physical_workflow', drc: 'drc_workflow', lvs: 'lvs_workflow', post_layout_verification: 'postlayout_workflow' };
const PREVIOUS = { graph_editor: 'global_settings', specifications: 'graph_editor', local_rtl_generation: 'specifications', global_netlist_simulation: 'global_synthesis', layout: 'global_netlist_simulation', drc: 'layout', lvs: 'drc', post_layout_verification: 'lvs' };

const ACTIVE = new Set(['Queued', 'Running', 'Starting', 'Stopping', 'Cancelling']);
const effectiveValidation = record => record?.stage_validation?.validation_status || record?.effective_validation_status || record?.validation_status;

/** Historical evidence is separate from an empty downstream display overlay. */
export function stageHasSavedEvidence(envelope, id) {
  const stage = (envelope?.workflow || []).find(item => item.id === id);
  if (stage && (stage.latest_run_id || stage.latest_job_id || stage.latest_spec_id || stage.accepted_run_id ||
      ['Completed', 'Failed', 'Cancelled', 'Interrupted'].includes(stage.execution_status))) return true;
  const records = id === 'local_rtl_generation' ? envelope?.generation?.jobs :
    id === 'node_implementation_specs' ? envelope?.implementation_specs :
    ['local_synthesis', 'local_netlist_simulation'].includes(id) ? envelope?.workflow_runs :
    id === 'global_rtl_generation' ? envelope?.global_generation?.jobs :
    DATA[id] ? envelope?.[DATA[id]]?.runs : envelope?.runs;
  if ((records || []).some(record => record?.id && (!record.stage_id || record.stage_id === id))) return true;
  const batches = id === 'local_rtl_generation' ? envelope?.generation_batches?.batches :
    ['local_synthesis', 'local_netlist_simulation'].includes(id) ? envelope?.workflow_batches : [];
  return (batches || []).some(batch => batch?.id && (!batch.stage_id || batch.stage_id === id));
}

/** Read-only aggregate facts for both the tab and the stage header. */
export function stageOverviewFacts(envelope, design, id) {
  const stages = envelope?.workflow || [];
  const original = stages.find(item => item.id === id);
  const stage = { ...original, id };
  stage.has_saved_evidence = stageHasSavedEvidence(envelope, id);
  const data = envelope?.[DATA[id]];
  const generationNodes = envelope?.generation?.nodes || [];
  const currentCandidate = nodeId => {
    const node = generationNodes.find(item => item.node_id === nodeId);
    return node?.latest_job_id && node.latest_job_id === node.accepted_job_id ? node.latest_job_id : null;
  };
  let records = [];
  if (id === 'local_rtl_generation') {
    const ids = new Set(generationNodes.map(node => node.latest_job_id));
    records = (envelope?.generation?.jobs || []).filter(job => ids.has(job.id));
  } else if (['local_synthesis', 'local_netlist_simulation'].includes(id)) {
    const ids = new Set((envelope?.workflow_nodes || []).filter(node => node.stage_id === id).map(node => node.latest_run_id));
    records = (envelope?.workflow_runs || []).filter(run => {
      if (!ids.has(run.id) || run.stage_id !== id || run.candidate_id !== currentCandidate(run.node_id)) return false;
      if (id !== 'local_netlist_simulation') return true;
      const source = (envelope?.workflow_nodes || []).find(node => node.node_id === run.node_id && node.stage_id === 'local_synthesis');
      const synthesis = (envelope?.workflow_runs || []).find(item => item.id === source?.accepted_run_id);
      return synthesis?.candidate_id === run.candidate_id && run.prior_run_id === synthesis.id &&
        run.netlist_sha256 === synthesis.netlist_sha256;
    });
  } else if (id === 'node_implementation_specs') {
    const ids = new Set((envelope?.implementation_spec_nodes || []).map(node => node.latest_spec_id));
    records = (envelope?.implementation_specs || []).filter(spec => {
      const node = (envelope?.implementation_spec_nodes || []).find(item => item.node_id === spec.node_id);
      return ids.has(spec.id) && (!spec.source_run_id || spec.source_run_id === node?.source_run_id);
    });
  } else if (data) {
    if (id === 'global_rtl_generation') records = (data.jobs || []).slice(-1);
    else records = (data.runs || []).filter(run => !run.stage_id || run.stage_id === id).slice(-1);
  }
  // An unfinished/failing current node must not be hidden by another node's pass.
  const active = records.find(record => ACTIVE.has(record.execution_status));
  const failed = records.find(record => record.freshness === 'Current' && (
    ['Failed', 'Cancelled', 'Interrupted', 'Declined'].includes(record.execution_status) ||
    ['Rejected', 'Returned', 'Request Changes', 'Changes Requested', 'Declined'].includes(record.review_status) ||
    (id === 'local_rtl_generation' ? effectiveValidation(record) : record.validation_status) === 'Failed' ||
    record.execution_status === 'Completed' && record.validation_status === 'Unsupported'));
  if (active) stage.execution_status = active.execution_status;
  else if (failed) { stage.execution_status = failed.execution_status; stage.validation_status = 'Failed'; stage.freshness = 'Current'; }
  const review = records.some(record => record.freshness === 'Current' && record.execution_status === 'Completed' &&
    (id === 'local_rtl_generation' ? effectiveValidation(record) : record.validation_status) === 'Passed' && record.review_status === 'Awaiting Review');
  if (review && !active && !failed) { stage.review_required = true; stage.execution_status = 'Completed'; }
  if (id === 'local_rtl_generation' && (envelope?.generation_batches?.batches || []).some(batch => ACTIVE.has(batch.execution_status))) stage.execution_status = 'Running';
  if (['local_synthesis', 'local_netlist_simulation'].includes(id) && (envelope?.workflow_batches || []).some(batch =>
    (batch.stage_id || 'local_synthesis') === id && ACTIVE.has(batch.execution_status))) stage.execution_status = 'Running';

  let blockedReason = stage.blocked_reason || '';
  if (data?.ready === false) blockedReason ||= data.blocked_reason || 'The required accepted sources are not ready.';
  if (data?.tool_ready === false) blockedReason ||= data.tool_blocked_reason || 'Configure the tool for this stage.';
  if (id === 'post_layout_verification' && data?.verification_supported === false) {
    stage.validation_status = 'Unsupported';
    blockedReason ||= 'The configured adapter does not support the required post-layout verification.';
  }
  if (stage.implemented === undefined) stage.implemented = ['global_settings', 'graph_editor', 'specifications'].includes(id);

  if (!adopted(original)) {
    const previous = PREVIOUS[id];
    if (previous && !adopted(stages.find(item => item.id === previous))) blockedReason ||= `Waiting for current accepted ${stages.find(item => item.id === previous)?.label || previous.replaceAll('_', ' ')} results.`;
    if (id === 'local_rtl_generation' && !envelope?.llm?.profile_revision_id) blockedReason ||= 'Save an LLM provider profile in Global Settings.';
    if (id === 'local_synthesis' && !generationNodes.some(node => currentCandidate(node.node_id))) blockedReason ||= 'Accept a current node RTL candidate in Local RTL Generation.';
    if (id === 'local_netlist_simulation') {
      const sources = (envelope?.workflow_nodes || []).filter(node => node.stage_id === 'local_synthesis' && node.accepted_run_id);
      if (!sources.length) blockedReason ||= 'Accept a current synthesized node in Local Synthesis.';
      else if (!generationNodes.some(node => node.behavioral_verification?.available === true && sources.some(source => source.node_id === node.node_id))) blockedReason ||= 'Behavioral verification support is required for the remaining node specifications.';
    }
    if (id === 'node_implementation_specs' && !(envelope?.implementation_spec_nodes || []).some(node => node.ready)) blockedReason ||= 'Accept node netlist verification results before deriving implementation specifications.';
  }
  stage.blocked_reason = blockedReason;
  return stage;
}

export function stagePresentation(envelope, id, { dirty = false, overlay = null, design = null } = {}) {
  const stage = stageOverviewFacts(envelope, design, id);
  if (overlay?.invalidated && !stage.has_saved_evidence)
    overlay = { ...overlay, detail: 'This stage has not run yet. Inspect its prerequisites and next action.' };
  // A child result can update the browser ledger before the aggregate poll.
  // Keep the actual same-stage batch running until it reaches a terminal state.
  const activeBatch = ['local_synthesis', 'local_netlist_simulation'].includes(id) &&
    (envelope?.workflow_batches || []).some(batch => (batch.stage_id || 'local_synthesis') === id &&
      batch.freshness !== 'Stale' && ACTIVE.has(batch.execution_status));
  if (activeBatch && !overlay?.reconnectRequired) overlay = null;
  return stageVisualState(stage, { blockedReason: stage.blocked_reason, dirty, overlay });
}
