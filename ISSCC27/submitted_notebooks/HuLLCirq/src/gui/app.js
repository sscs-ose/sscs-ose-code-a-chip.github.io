import { element as el, field, badge, downloadJson } from './dom.js';
import { GraphEditor } from './graph.js';
import { arrayShape, instanceSuffix, endpointsFor, endpointValue, parseEndpoint, arrayResizeProblem } from './design_instances.js';
import { hasExternalIO, blankExternalIO, externalPorts, expandedExternalPorts, externalEndpointChoices, parseGraphEndpoint, externalBindingLabel, externalConnectionProblem, externalArrayResizeProblem, renderExternalInspector } from './external_io.js';
import { BlockFloorplan } from './block_floorplan.js';
import { SYSTEM_DRAFT_KEYS, structuredInput, evaluateStructuredDraft, nodePhysicalPorts, cycleTemplate, parseCycleInput, parseIntegrationInput } from './verification_inputs.js';
import { GenerationWorkspace } from './generation.js';
import { ExecutionSubmissions } from './execution_submissions.js';
import { GenerationBatchWorkspace } from './generation_batch.js';
import { AdoptionPolicy } from './policy.js';
import { ReviewOperator, reviewActorLabel, adoptionProvenance } from './review_operator.js';
import { LocalWorkflow } from './workflow.js';
import { NodeImplementationSpecs } from './implementation_specs.js';
import { GlobalGeneration } from './global_generation.js';
import { DependentStageRefresh } from './dependent_stage_refresh.js';
import { GlobalWorkflow } from './global_workflow.js';
import { PhysicalWorkflow } from './physical_workflow.js';
import { DRCWorkflow } from './drc_workflow.js';
import { LVSWorkflow } from './lvs_workflow.js';
import { PostlayoutWorkflow } from './postlayout_workflow.js';
import { PhysicalRecovery } from './physical_recovery.js';
import { WaveformViewer } from './waveform_viewer.js';
import { ProjectFiles } from './project_files.js';
import { WorkspaceManager } from './workspace.js';
import { sessionFetch, workspaceSession, setWorkspaceSession } from './workspace_transport.js';
import { resolveStageGuidance } from './flow_guidance.js';
import { stageIcon, statusIcon } from './icons.js';
import { connectionVisualState } from './visual_state.js';
import { stagePresentation, stageOverviewFacts, stageHasSavedEvidence } from './stage_visuals.js';
import { ConnectionMonitor } from './connection_monitor.js';
import { ExecutionStateTracker, executionAction } from './execution_state.js';
import { availabilityReason } from './availability.js';

const STAGES = [
  ['global_settings', 'Global Settings', 'Set the shared clock, reset, RTL, and technology contracts.'],
  ['graph_editor', 'Graph Editor', 'Arrange the design hierarchy, ports, and connections.'],
  ['specifications', 'Specifications', 'Describe what each node does and how data moves between nodes.'],
  ['local_rtl_generation', 'Local RTL Generation', 'Generate each node from its specification and connected edges.'],
  ['local_synthesis', 'Local Synthesis', 'Synthesize the reviewed RTL for each node.'],
  ['local_netlist_simulation', 'Local Netlist Simulation', 'Check actual synthesized node netlists against independent expectations.'],
  ['node_implementation_specs', 'Node Implementation Specs', 'Review evidence-backed behavior and the public node interfaces.'],
  ['global_rtl_generation', 'Global RTL Generation', 'Generate integration RTL from accepted node evidence and edge specifications.'],
  ['global_synthesis', 'Global Synthesis', 'Synthesize the reviewed complete design.'],
  ['global_netlist_simulation', 'Global Netlist Simulation', 'Verify the complete synthesized circuit.'],
  ['layout', 'Layout', 'Run placement and routing and inspect the physical results.'],
  ['drc', 'DRC', 'Inspect design-rule results for the actual layout.'],
  ['lvs', 'LVS', 'Compare extracted layout connectivity with the circuit netlist.'],
  ['post_layout_verification', 'Post-layout Verification', 'Inspect recorded functional and timing evidence, scope and limitations.'],
];
let DRAFT_KEY = 'hullcirq.m1.draft.v1';
let RECOVERY_KEY = 'hullcirq.m1.recovered-drafts.v1';
let workspaceEnabled = false;
let activeWorkspace = null;
let executionSubmissions = null;
const state = { envelope: null, design: null, saved: null, externalRevision: null, verificationDrafts: {}, stage: STAGES[0][0], selected: null, undo: [], redo: [], busy: false, graph: null, historyOpen: false, feedback: {}, returnTargets: {}, recovered: [], recoveredSelection: null, recoveryUnpersisted: false };
const reviewOperator = new ReviewOperator();
const executionState = new ExecutionStateTracker({
  readStorage: scope => { try { return JSON.parse(localStorage.getItem(`hullcirq.execution.v1:${scope}`) || 'null'); } catch { return null; } },
  writeStorage: (scope, value) => { try { localStorage.setItem(`hullcirq.execution.v1:${scope}`, JSON.stringify(value)); } catch { /* Saved execution evidence remains authoritative when browser storage is unavailable. */ } },
});
function executionScope(envelope = state.envelope) {
  return `${activeWorkspace?.project_id || envelope?.design?.project?.id || 'legacy'}:${activeWorkspace?.system_id || 'system'}:${envelope?.revision?.id || 'unopened'}`;
}
function receiveExecution(envelope = state.envelope) {
  if (!envelope?.revision?.id) return;
  executionState.setScope(executionScope(envelope));
  executionState.receive(envelope);
}
function stageVisual(id) {
  let overlay = executionState.overlay(id);
  const unsavedInput = !!stageInputDirty(id);
  if (unsavedInput && overlay?.status !== 'Running') overlay = null;
  // A completed action on one node cannot complete an entire multi-node stage.
  if (overlay?.status === 'Complete' && ['local_rtl_generation', 'local_synthesis', 'local_netlist_simulation', 'node_implementation_specs'].includes(id)) overlay = null;
  // The controller may still own a POST or reconcile a child after the last
  // envelope showed a terminal batch. Ordinary read polling is not execution.
  if (['local_synthesis', 'local_netlist_simulation'].includes(id) &&
      !overlay?.reconnectRequired && !localFlow.batchStartUncertain && !localFlow.batchPollError && !localFlow.pollError &&
      (localFlow.busy && (localFlow.busyStage || state.stage) === id ||
       localFlow.batches.some(batch => localFlow.batchStage(batch) === id && ['Queued', 'Running'].includes(batch.execution_status)) ||
       localFlow.runs.some(run => run.stage_id === id && ['Queued', 'Running'].includes(run.execution_status))))
    overlay = { status: 'Running', detail: 'The operation is running or its latest saved result is being reconciled.' };
  const visual = stagePresentation(state.envelope, id, { dirty: unsavedInput, overlay, design: state.design });
  if (id === 'drc' && drcFlow.pollError) visual.detail = `Saved DRC progress could not be observed. The displayed execution status is the last saved observation, not confirmation that tools are still running. ${drcFlow.pollError}`;
  if (visual.label === 'Not run' && !unsavedInput) {
    const facts = stageOverviewFacts(state.envelope, state.design, id);
    if (facts.blocked_reason) {
      const dataKey = {global_rtl_generation:'global_generation',global_synthesis:'global_workflow',global_netlist_simulation:'global_workflow',layout:'physical_workflow',drc:'drc_workflow',lvs:'lvs_workflow',post_layout_verification:'postlayout_workflow'}[id];
      const data = state.envelope?.[dataKey];
      const kind = facts.implemented === false ? 'implementation_required' : data?.ready !== false && data?.tool_ready === false ? 'configuration_required' : undefined;
      const reason = availabilityReason({kind,reason:facts.blocked_reason});
      const progress = overlay?.invalidated && facts.has_saved_evidence ? 'An earlier stage was restarted. ' : facts.required_node_count > 1 && facts.accepted_node_count < facts.required_node_count ? `${facts.accepted_node_count || 0}/${facts.required_node_count} nodes adopted. ` : '';
      visual.detail = `${progress}${reason.label}: ${reason.message}`;
    }
  }
  return visual;
}
const byId = id => document.getElementById(id);
const clone = value => structuredClone(value);
const equal = (left, right) => JSON.stringify(left) === JSON.stringify(right);
const invalidVerification = () => Object.entries(state.verificationDrafts).map(([id, draft]) => [id, verificationDraftState(id, draft)]).find(([, draft]) => draft?.error || draft?.pending);
function verificationDraftState(id, draft) {
  if (id === SYSTEM_DRAFT_KEYS[0]) return evaluateStructuredDraft(draft, state.design.global_integration, text => parseIntegrationInput(text, state.design.settings));
  if (id === SYSTEM_DRAFT_KEYS[1]) return evaluateStructuredDraft(draft, state.design.global_verification, text => parseCycleInput(text, state.design.global_integration?.public_ports || []));
  const node = state.design?.nodes.find(node => node.id === id);
  return node ? evaluateStructuredDraft(draft, node.verification, text => parseCycleInput(text, nodePhysicalPorts(node), { allowLegacy: true })) : null;
}
const adapterDraftDirty = () => postlayoutFlow.adapterBackupDirty?.() || false;
const dirty = () => state.design && (!equal(state.design, state.saved) || !!invalidVerification());
// Graph drawing coordinates and viewport are presentation state. Keep them
// saveable without making already accepted circuit evidence look unexecuted.
// Logical source identities exclude drawing state and physical-only constraints.
const executionInput = design => {
  if (!design || typeof design !== 'object') return design;
  const projected = { ...design };
  delete projected.layout;
  delete projected.physical_design;
  return projected;
};
const executionInputDirty = () => state.design && (!equal(executionInput(state.design), executionInput(state.saved)) || !!invalidVerification());
const physicalDraftDirty = () => state.design && !equal(state.design.physical_design, state.saved?.physical_design);
const physicalExecutionInputDirty = () => executionInputDirty() || physicalDraftDirty();
const stageInputDirty = (stage = state.stage) => ['layout', 'drc', 'lvs', 'post_layout_verification'].includes(stage) ? physicalExecutionInputDirty() : executionInputDirty();
const currentStage = () => STAGES.find(stage => stage[0] === state.stage);
const workflowStage = id => state.envelope?.workflow?.find(stage => stage.id === id);
const selectedNode = () => state.selected?.kind === 'node' ? state.design.nodes.find(node => node.id === state.selected.id) : null;
const newId = prefix => `${prefix}_${crypto.randomUUID().replaceAll('-', '').slice(0, 12)}`;
const postlayoutRunning = () => (state.envelope?.postlayout_workflow?.runs || []).some(run => ['Queued', 'Running'].includes(run.execution_status));
const generationBatches = new GenerationBatchWorkspace({
  project: () => ({ design: state.design, envelope: state.envelope, dirty: executionInputDirty(), conflict: state.externalRevision, readOnly: readOnly(), busy: state.busy || !!executionSubmissions?.blocked(), stage: state.stage, postlayoutRunning: postlayoutRunning(), lvsRunning: (state.envelope?.lvs_workflow?.runs || []).some(run => ['Queued', 'Running'].includes(run.execution_status)) }),
  request: api, envelope: mergeGenerationEnvelope, notify, toast, chrome: syncChrome, navigate: navigateNode, providerDirty: () => generation.profileDirty(), providerGate: () => executionSubmissions?.gate() || generation.providerRequestGate(),
  inspect: (jobId, nodeId) => { navigateNode('local_rtl_generation', nodeId); generation.selectedJobId = jobId; generation.renderResult(); syncChrome(); renderReview(); },
});
const generation = new GenerationWorkspace({
  batch: () => generationBatches,
  project: () => ({ design: state.design, envelope: state.envelope, dirty: executionInputDirty(), conflict: state.externalRevision, postlayoutRunning: postlayoutRunning(), lvsRunning: (state.envelope?.lvs_workflow?.runs || []).some(run => ['Queued', 'Running'].includes(run.execution_status)), busy: state.busy || !!executionSubmissions?.blocked(), stage: state.stage }),
  request: api, envelope: mergeGenerationEnvelope, notify, toast, navigate: navigateNode, chrome: syncChrome, providerStateChanged: () => { globalGeneration.refresh(); syncChrome(); },
  connection: (label, observation) => {
    if (observation?.checkedAt && (observation.runtime || observation.error) && connectionMonitor.eligible() && observation.checkedAt >= (connectionMonitor.checkedAt || 0)) {
      connectionMonitor.runtime = observation.runtime || null; connectionMonitor.error = observation.error;
      connectionMonitor.checkedAt = observation.checkedAt;
    }
    renderConnectionStatus();
  },
});
const connectionMonitor = new ConnectionMonitor({
  project: () => ({ envelope: state.envelope, readOnly: readOnly(), profileDirty: generation.profileDirty() }),
  request: api, changed: renderConnectionStatus, visible: () => document.visibilityState !== 'hidden',
});
const adoption = new AdoptionPolicy({ request: api, envelope: mergeGenerationEnvelope, notify, toast });
const localFlow = new LocalWorkflow({ project: () => ({ design: state.design, envelope: state.envelope, dirty: executionInputDirty(), conflict: state.externalRevision, readOnly: readOnly(), busy: state.busy || !!executionSubmissions?.blocked(), postlayoutRunning: postlayoutRunning(), lvsRunning: (state.envelope?.lvs_workflow?.runs || []).some(run => ['Queued', 'Running'].includes(run.execution_status)), stage: state.stage }), request: api, envelope: mergeGenerationEnvelope, notify, toast, navigate: navigateNode, prepareRepair: prepareWorkflowRepair, batch: () => generationBatches, chrome: syncChrome });
const implementationSpecs = new NodeImplementationSpecs({ project: () => ({ design: state.design, envelope: state.envelope, dirty: executionInputDirty(), conflict: state.externalRevision, readOnly: readOnly(), postlayoutRunning: postlayoutRunning(), lvsRunning: (state.envelope?.lvs_workflow?.runs || []).some(run => ['Queued', 'Running'].includes(run.execution_status)), busy: state.busy || !!executionSubmissions?.blocked(), stage: state.stage }), request: api, envelope: mergeGenerationEnvelope, notify, toast, navigate: navigateNode, chrome: syncChrome });
const dependentStageRefresh = new DependentStageRefresh({ scope: () => `${executionScope()}:${activeWorkspace?.session_id || 'local'}`, refresh: refreshDependentStageSnapshot, notify });
const globalGeneration = new GlobalGeneration({ project: () => ({ design: state.design, envelope: state.envelope, dirty: executionInputDirty(), conflict: state.externalRevision, postlayoutRunning: postlayoutRunning(), lvsRunning: (state.envelope?.lvs_workflow?.runs || []).some(run => ['Queued', 'Running'].includes(run.execution_status)), stage: state.stage }), request: api, envelope: mergeGenerationEnvelope, notify, resolveNotice, toast, navigate: navigateNode, chrome: syncChrome, providerGate: () => executionSubmissions?.gate() || generation.providerRequestGate(), dependencies: envelope => dependentStageRefresh.observe(envelope) });
const globalFlow = new GlobalWorkflow({ project: () => ({ design: state.design, envelope: state.envelope, dirty: executionInputDirty(), conflict: state.externalRevision, postlayoutRunning: postlayoutRunning(), lvsRunning: (state.envelope?.lvs_workflow?.runs || []).some(run => ['Queued', 'Running'].includes(run.execution_status)), busy: state.busy || !!executionSubmissions?.blocked(), stage: state.stage }), request: api, envelope: mergeGenerationEnvelope, workflow: mergeGlobalWorkflow, notify, toast, navigate: navigateNode, chrome: syncChrome });
const blockFloorplan = new BlockFloorplan({ project: () => ({ design: state.design, saved: state.saved, envelope: state.envelope, dirty: dirty(), conflict: state.externalRevision, readOnly: readOnly(), busy: state.busy || !!executionSubmissions?.blocked() }), mutate: change => { mutate(change, false); physicalFlow.refreshDraftActions(); }, save: saveDesign, notify });
const physicalFlow = new PhysicalWorkflow({ project: () => ({ design: state.design, envelope: state.envelope, dirty: physicalExecutionInputDirty(), conflict: state.externalRevision, postlayoutRunning: postlayoutRunning(), lvsRunning: (state.envelope?.lvs_workflow?.runs || []).some(run => ['Queued', 'Running'].includes(run.execution_status)), busy: state.busy || !!executionSubmissions?.blocked(), stage: state.stage }), request: api, envelope: mergeGenerationEnvelope, workflow: mergePhysicalWorkflow, notify, toast, navigate: navigateNode, chrome: syncChrome, renderBlockFloorplan: host => blockFloorplan.render(host) });
const lvsFlow = new LVSWorkflow({ project: () => ({ design: state.design, envelope: state.envelope, dirty: physicalExecutionInputDirty(), conflict: state.externalRevision, readOnly: readOnly(), busy: state.busy || !!executionSubmissions?.blocked(), stage: state.stage }), request: api, envelope: mergeGenerationEnvelope, workflow: mergeLVSWorkflow, notify, toast, navigate: navigateNode, chrome: syncChrome });
const drcFlow = new DRCWorkflow({ project: () => ({ design: state.design, envelope: state.envelope, dirty: physicalExecutionInputDirty(), conflict: state.externalRevision, postlayoutRunning: postlayoutRunning(), lvsRunning: (state.envelope?.lvs_workflow?.runs || []).some(run => ['Queued', 'Running'].includes(run.execution_status)), busy: state.busy || !!executionSubmissions?.blocked(), stage: state.stage }), request: api, envelope: mergeGenerationEnvelope, workflow: mergeDRCWorkflow, notify, toast, navigate: navigateNode, chrome: syncChrome });
const postlayoutFlow = new PostlayoutWorkflow({ project: () => ({ design: state.design, envelope: state.envelope, dirty: physicalExecutionInputDirty(), conflict: state.externalRevision, busy: state.busy || !!executionSubmissions?.blocked(), stage: state.stage }), request: api, envelope: mergeGenerationEnvelope, workflow: mergePostlayoutWorkflow, notify, toast, navigate: navigateNode, chrome: syncChrome, draftChanged: () => { autosave(); syncChrome(); } });
const waveFlows = {
  workflow: {flow:localFlow,stage:'local_netlist_simulation',host:'[data-testid="workflow-result"]'},
  'global-workflow': {flow:globalFlow,stage:'global_netlist_simulation',host:'[data-testid="global-workflow-result"]'},
  'postlayout-workflow': {flow:postlayoutFlow,stage:'post_layout_verification',host:'[data-testid="postlayout-workflow-result"]'},
};
const waveformViewer = new WaveformViewer({ request:api, identity:()=>[workspaceSession(),state.design?.id,state.envelope?.revision?.id],
  selected:group=>state.stage===waveFlows[group]?.stage?waveFlows[group].flow.selected():null,
  refresh:group=>waveFlows[group].flow.renderResult(),
});
for (const [group, view] of Object.entries(waveFlows)) {
  const original = view.flow.renderResult.bind(view.flow);
  view.flow.renderResult = (...args) => { original(...args); if(state.stage===view.stage)waveformViewer.mount(document.querySelector(view.host),group,view.flow.selected()); };
}
const projectFiles = new ProjectFiles({request:api,identity:()=>JSON.stringify([workspaceSession(),state.design?.id,state.envelope?.revision?.id])});
const recoveryFlows = { layout: physicalFlow, drc: drcFlow, lvs: lvsFlow, post_layout_verification: postlayoutFlow };
const physicalRecovery = new PhysicalRecovery({
  project: () => ({ design: state.design, envelope: state.envelope, stage: state.stage, dirty: physicalExecutionInputDirty(), conflict: state.externalRevision, busy: state.busy || !!executionSubmissions?.blocked(), readOnly: readOnly() }),
  selected: stage => recoveryFlows[stage]?.selected(), request: api, refresh: renderReview,
  open: async handoff => {
    if (handoff.target === 'node_rtl') {
      const scope = snapshotIdentity(), stage = state.stage;
      const job = await api(`generation/jobs/${encodeURIComponent(handoff.base_job.id)}`);
      if (scope !== snapshotIdentity() || stage !== state.stage) return;
      state.envelope.generation.jobs = state.envelope.generation.jobs.map(j => j.id === job.id ? job : j);
      generation.generation.jobs = state.envelope.generation.jobs;
      navigateNode('local_rtl_generation', handoff.node_id);
      generation.selectedJobId = job.id; generation.prepareRepair(job, handoff.instruction);
    } else if (handoff.target === 'global_rtl') {
      const scope = snapshotIdentity(), stage = state.stage;
      const job = await api(`global-generation/jobs/${encodeURIComponent(handoff.base_job.id)}`);
      if (scope !== snapshotIdentity() || stage !== state.stage) return;
      state.envelope.global_generation.jobs = state.envelope.global_generation.jobs.map(j => j.id === job.id ? job : j);
      globalGeneration.data.jobs = state.envelope.global_generation.jobs;
      navigateNode('global_rtl_generation');
      globalGeneration.selectedId = job.id;
      globalGeneration.operation = 'repair'; globalGeneration.baseId = handoff.base_job.id;
      globalGeneration.instruction = handoff.instruction; globalGeneration.preview = null;
      globalGeneration.render(globalGeneration.host);
    } else navigateNode(handoff.target_stage);
    syncChrome();
  },
});
for (const [stage, flow] of Object.entries(recoveryFlows)) {
  const original = flow.renderReview.bind(flow);
  flow.renderReview = host => { original(host); if (host && state.stage === stage) physicalRecovery.render(host, stage, flow.selected()); };
}
const workspace = new WorkspaceManager({ request: api, notify, toast, flush: flushActiveField,
  project: () => ({ design: state.design, envelope: state.envelope }),
  selection: () => state.selected?.kind === 'node' ? state.selected.ids || [state.selected.id] : [],
  beforeLeave: preserveBeforeContextChange,
  identityChanged: active => !!active && (active.project_id !== activeWorkspace?.project_id || active.system_id !== activeWorkspace?.system_id || active.session_id !== activeWorkspace?.session_id),
  activate: result => {
    autosave(); setWorkspaceSession(result.workspace?.active?.session_id);
    // Workspace commands reach activation only after their explicit draft
    // preservation choice. Do not ask a second native leave-page question.
    state.authorizedContextNavigation = true;
    location.reload();
  },
  updated: (envelope, action) => {
    if (['instantiate', 'rename-system', 'rename-project'].includes(action)) { state.undo = []; state.redo = []; state.selected = null; adopt(envelope); }
    else adopt(envelope, true);
  },
});
const readOnly = () => workspaceEnabled && activeWorkspace?.read_only === true;

function executionSubmissionScope(envelope = null) {
  const identity = envelope?.workspace_identity || activeWorkspace || state.envelope?.workspace_identity;
  if (identity?.project_id && identity?.system_id) return JSON.stringify([identity.project_id, identity.system_id]);
  const id = envelope?.design?.project?.id || envelope?.design?.id || state.design?.project?.id || state.design?.id;
  return id ? JSON.stringify(['legacy', id]) : null;
}
function applyExecutionSelection(receipt = null) {
  const resolution = executionSubmissions?.lastResolution;
  const outcome = resolution?.scope === executionSubmissionScope() ? resolution : null;
  const route = receipt?.route || outcome?.route;
  const controller = route?.startsWith('workflow/') ? localFlow : route === 'generation/batches/start' || route === 'repair-analysis/start' ? generationBatches : route === 'global-generation/start' ? globalGeneration : ({ 'global-workflow/runs': globalFlow, 'physical-workflow/runs': physicalFlow, 'drc-workflow/runs': drcFlow, 'lvs-workflow/runs': lvsFlow, 'postlayout-workflow/runs': postlayoutFlow })[route];
  // API errors reach the controller catch/finally after api() rejects. Keep the
  // exact outcome until that controller has finished setting its local flags.
  if (!receipt && outcome?.status === 'rejected' && controller?.busy) return;
  if (controller) {
    if (route === 'workflow/batches/start') { controller.batchStartUncertain = false; controller.batchPollError = null; controller.batchRequestId = null; }
    else if (route === 'generation/batches/start') { controller.startUncertain = false; controller.pollError = null; controller.requestId = null; }
    else if (route === 'repair-analysis/start') { controller.analysisStartUncertain = false; controller.analysisError = null; controller.analysisRequestId = null; }
    else { controller.uncertainStart = false; controller.pollError = null; }
  }
  if (!receipt && resolution?.scope === executionSubmissionScope() && resolution.status === 'started') receipt = { route: resolution.route, record_id: resolution.recordId };
  if (executionSubmissions) executionSubmissions.lastResolution = null;
  if (!receipt?.record_id) {
    // Consume the exact outcome before refreshing: refresh callbacks reenter
    // chrome, and must not reapply this already resolved request.
    controller?.refresh?.();
    return;
  }
  const id = receipt.record_id;
  if (receipt.route === 'workflow/start') { localFlow.runId = id; localFlow.runPinned = true; }
  else if (receipt.route === 'workflow/batches/start') localFlow.batchId = id;
  else if (receipt.route === 'generation/batches/start') generationBatches.batchId = id;
  else if (receipt.route === 'repair-analysis/start') generationBatches.analysisJobId = id;
  else if (receipt.route === 'global-generation/start') globalGeneration.selectedId = id;
  else {
    const flow = ({ 'global-workflow/runs': globalFlow, 'physical-workflow/runs': physicalFlow,
      'drc-workflow/runs': drcFlow, 'lvs-workflow/runs': lvsFlow, 'postlayout-workflow/runs': postlayoutFlow })[receipt.route];
    if (flow) flow.runId = id;
  }
}
async function publishExecutionOutcome(response) {
  const envelope = response.design ? response : await api('project');
  mergeGenerationEnvelope(envelope);
  applyExecutionSelection(response.execution_submission);
  localFlow.refresh(); globalGeneration.refresh(); globalFlow.refresh(); physicalFlow.refresh(); drcFlow.refresh(); lvsFlow.refresh(); postlayoutFlow.refresh();
  syncChrome();
}
executionSubmissions = new ExecutionSubmissions({
  context: () => ({ scope: executionSubmissionScope(), envelope: state.envelope, dirty: executionInputDirty(), conflict: state.externalRevision, readOnly: readOnly(), busy: state.busy }),
  foreignPending: () => !!generation.pendingStart(), read: () => api('project'), send: api,
  publish: publishExecutionOutcome, notify, toast, changed: () => { if (state.design) syncChrome(); },
});


// A preserved system opens from a small saved-record index. Expensive evidence
// is requested only for the stage or historical record the person selects.
const savedSnapshotStages = new Map();
const savedSnapshotRecords = new Map();
const compactSnapshot = () => readOnly() && state.envelope?.readonly_snapshot?.compact === true;
const snapshotIdentity = () => `${workspaceSession()}:${state.design?.id}:${state.envelope?.revision?.id}`;
const snapshotStageKey = id => `${snapshotIdentity()}:${id}`;
const evidenceViews = [
  { module: generation, stages: ['local_rtl_generation'], selected: () => generation.selectedJob(), path: ['generation', 'jobs'], route: 'generation/jobs', host: '#generation-result-content' },
  { module: localFlow, stages: ['local_synthesis', 'local_netlist_simulation'], selected: () => localFlow.selected(), path: ['workflow_runs'], route: 'workflow/runs', host: '[data-testid="workflow-result"]' },
  { module: implementationSpecs, stages: ['node_implementation_specs'], selected: () => implementationSpecs.selected(), path: ['implementation_specs'], route: 'implementation-specs', host: '[data-testid="implementation-result"]' },
  { module: globalGeneration, stages: ['global_rtl_generation'], selected: () => globalGeneration.selected(), path: ['global_generation', 'jobs'], route: 'global-generation/jobs', host: '[data-testid="global-result"]' },
  { module: globalFlow, stages: ['global_synthesis', 'global_netlist_simulation'], selected: () => globalFlow.selected(), path: ['global_workflow', 'runs'], route: 'global-workflow/runs', host: '[data-testid="global-workflow-result"]' },
  { module: physicalFlow, stages: ['layout'], selected: () => physicalFlow.selected(), path: ['physical_workflow', 'runs'], route: 'physical-workflow/runs', host: '[data-testid="physical-workflow-result"]' },
  { module: drcFlow, stages: ['drc'], selected: () => drcFlow.selected(), path: ['drc_workflow', 'runs'], route: 'drc-workflow/runs', host: '[data-testid="drc-workflow-result"]' },
  { module: lvsFlow, stages: ['lvs'], selected: () => lvsFlow.selected(), path: ['lvs_workflow', 'runs'], route: 'lvs-workflow/runs', host: '[data-testid="lvs-workflow-result"]' },
  { module: postlayoutFlow, stages: ['post_layout_verification'], selected: () => postlayoutFlow.selected(), path: ['postlayout_workflow', 'runs'], route: 'postlayout-workflow/runs', host: '[data-testid="postlayout-workflow-result"]' },
];

function recordsAt(envelope, path) { return path.reduce((value, key) => value?.[key], envelope) || []; }

function mergeSavedSnapshot(incoming) {
  // A later compact index must not discard already opened evidence. The session
  // and revision checks at each caller prevent reuse across projects/systems.
  const merged = { ...incoming };
  for (const { path } of evidenceViews) {
    const previous = new Map(recordsAt(state.envelope, path).filter(record => !record.summary_only).map(record => [record.id, record]));
    const records = recordsAt(incoming, path).map(record => record.summary_only && previous.has(record.id) ? previous.get(record.id) : record);
    if (path.length === 1) merged[path[0]] = records;
    else merged[path[0]] = { ...merged[path[0]], [path[1]]: records };
  }
  return merged;
}

function snapshotLoading(host, message, error, retry) {
  host.replaceChildren(el('section', { class: 'card', 'data-testid': 'saved-snapshot-loading' },
    el('h2', { text: error ? 'Saved evidence could not be loaded' : 'Opening saved evidence' }),
    el('p', { role: error ? 'alert' : 'status', text: error || message }),
    el('p', { class: 'scope-note', text: 'You can switch stages or projects while this saved result loads. No model or EDA tool is started.' }),
    error ? el('button', { type: 'button', text: 'Retry loading saved evidence', 'data-testid': 'saved-snapshot-retry', onclick: retry }) : null));
}

function loadSavedStage(id, retry = false) {
  const key = snapshotStageKey(id), identity = snapshotIdentity();
  if (retry) savedSnapshotStages.delete(key);
  if (savedSnapshotStages.has(key)) return;
  const request = { status: 'loading' };
  savedSnapshotStages.set(key, request);
  api(`workspace/stage/${encodeURIComponent(id)}`).then(response => {
    if (!compactSnapshot() || snapshotIdentity() !== identity || state.stage !== id) { savedSnapshotStages.delete(key); return; }
    const envelope = response.project || response;
    if (envelope.revision?.id !== state.envelope.revision.id || envelope.design?.id !== state.design.id) throw new Error('The saved evidence belongs to a different design revision. Open Projects to reconnect.');
    request.status = 'ready';
    adopt(mergeSavedSnapshot(envelope), true);
  }).catch(error => {
    if (snapshotIdentity() !== identity || state.stage !== id) { savedSnapshotStages.delete(key); return; }
    request.status = 'error'; request.error = error.message; render();
  });
}

function loadSavedRecord(view, record, retry = false) {
  const stage = state.stage, identity = snapshotIdentity(), key = `${identity}:${view.route}:${record.id}`;
  if (retry) savedSnapshotRecords.delete(key);
  if (savedSnapshotRecords.has(key)) return;
  const request = { status: 'loading' }; savedSnapshotRecords.set(key, request);
  api(`${view.route}/${encodeURIComponent(record.id)}`).then(full => {
    if (!compactSnapshot() || snapshotIdentity() !== identity || state.stage !== stage || view.selected()?.id !== record.id) { savedSnapshotRecords.delete(key); return; }
    if (full.id !== record.id || full.summary_only) throw new Error('The service did not return the selected saved evidence record.');
    const current = recordsAt(state.envelope, view.path), records = current.map(item => item.id === record.id ? full : item);
    const incoming = view.path.length === 1 ? { ...state.envelope, [view.path[0]]: records }
      : { ...state.envelope, [view.path[0]]: { ...state.envelope[view.path[0]], [view.path[1]]: records } };
    request.status = 'ready'; adopt(incoming, true);
  }).catch(error => {
    if (snapshotIdentity() !== identity || state.stage !== stage || view.selected()?.id !== record.id) { savedSnapshotRecords.delete(key); return; }
    request.status = 'error'; request.error = error.message; view.module.renderResult();
  });
}

function installSavedSnapshotViews() {
  for (const view of evidenceViews) {
    const original = view.module.renderResult;
    view.module.renderResult = function (...args) {
      const record = view.selected(), host = this.host?.querySelector(view.host);
      if (compactSnapshot() && view.stages.includes(state.stage) && record?.summary_only && host) {
        const key = `${snapshotIdentity()}:${view.route}:${record.id}`;
        loadSavedRecord(view, record);
        const request = savedSnapshotRecords.get(key);
        snapshotLoading(host, `Loading saved record ${record.id}…`, request?.error, () => { loadSavedRecord(view, record, true); this.renderResult(); });
        return;
      }
      return original.apply(this, args);
    };
    if (typeof view.module.renderReview === 'function') {
      const review = view.module.renderReview;
      view.module.renderReview = function (...args) {
        const result = review.apply(this, args);
        if (compactSnapshot()) applyReadOnly();
        return result;
      };
    }
    // A snapshot displays historical execution status. It must not poll a saved
    // Running label as though a live worker or policy adoption were in progress.
    const method = view.module.schedulePoll ? 'schedulePoll' : 'schedule';
    if (typeof view.module[method] === 'function') {
      const schedule = view.module[method];
      view.module[method] = function (...args) { if (!compactSnapshot()) return schedule.apply(this, args); };
    }
  }
}
installSavedSnapshotViews();

function navigateNode(stage, nodeId) {
  if (nodeId) {
    localFlow.setNode(nodeId);
    implementationSpecs.setNode(nodeId);
    generation.nodeId = nodeId;
    generation.selectedJobId = state.envelope.generation?.nodes?.find(node => node.node_id === nodeId)?.latest_job_id || null;
    if (['specifications', 'graph_editor'].includes(stage)) state.selected = { kind: 'node', id: nodeId, ids: [nodeId] };
  }
  setStage(stage);
  if (nodeId && stage === 'specifications') {
    const target = byId(`spec-node-behavior-${nodeId}`);
    target?.closest('.node-spec-card')?.scrollIntoView({block:'start',behavior:'smooth'});
    target?.focus({preventScroll:true});
  }
}

function prepareWorkflowRepair(candidate, instruction) {
  flushActiveField();
  const node = state.envelope?.generation?.nodes?.find(item => item.node_id === candidate?.node_id);
  const current = state.envelope?.generation?.jobs?.find(item => item.id === candidate?.id);
  if (readOnly() || executionInputDirty() || state.externalRevision || state.busy || generation.requestBusy || generation.activeJob() ||
      !current?.rtl || current.freshness !== 'Current' || current.review_status !== 'Accepted' ||
      node?.accepted_job_id !== current.id || node?.latest_job_id !== current.id) {
    toast('The current source or operation changed. Reopen the latest S05 or S06 result before preparing a repair.');
    return false;
  }
  navigateNode('local_rtl_generation', current.node_id);
  generation.selectedJobId = current.id;
  if (generation.prepareRepair(current, instruction) === false) return false;
  syncChrome();
  return true;
}

function mergeGenerationEnvelope(envelope) {
  flushActiveField();
  dependentStageRefresh.rememberFull(envelope);
  // Provider/job changes must never replace a user's in-progress circuit draft.
  if (state.envelope && envelope.revision.id !== state.envelope.revision.id) {
    // A poll or provider response may observe another window's source edit.
    // Keep the original save base so optimistic concurrency still rejects an
    // overwrite. Explicit Open saved is the only action adopting that source.
    const changed = state.externalRevision !== envelope.revision.id;
    state.externalRevision = envelope.revision.id;
    state.envelope = { ...envelope, design: state.envelope.design, revision: state.envelope.revision,
      workflow: state.envelope.workflow.map(stage => ['global_synthesis', 'global_netlist_simulation', 'layout', 'drc', 'lvs', 'post_layout_verification'].includes(stage.id)
        ? envelope.workflow.find(incoming => incoming.id === stage.id) || stage : stage) };
    if (changed) notify('The saved design changed in another window. Your source and save base were preserved. Export JSON to retain your draft, then use Open saved to load the newer design.', 'warning');
  } else {
    state.envelope = envelope;
    state.saved = clone(envelope.design);
  }
  receiveExecution(state.envelope);
  generationBatches.receive(envelope); generation.receive(envelope);
  adoption.receive(envelope);
  localFlow.receive(envelope);
  implementationSpecs.receive(envelope);
  globalGeneration.receive(envelope);
  globalFlow.receive(envelope);
  physicalFlow.receive(envelope);
  drcFlow.receive(envelope);
  lvsFlow.receive(envelope);
  postlayoutFlow.receive(envelope);
  applyExecutionSelection(envelope.execution_submission);
  autosave(); syncChrome(); renderReview();
}

async function refreshDependentStageSnapshot() {
  const scope = executionScope(), session = activeWorkspace?.session_id;
  const observed = state.envelope, executionSerial = executionState.serial;
  const envelope = await api('project'); // One read-only aggregate per new terminal/adoption stamp.
  if (scope !== executionScope() || session !== activeWorkspace?.session_id) return false;
  // A later Run or newer response owns the screen; a slow read must not replace it.
  if (observed !== state.envelope || executionSerial !== executionState.serial) return false;
  mergeGenerationEnvelope(envelope); // Preserve drafts and optimistic save bases through the normal merger.
  return true;
}

function mergeGlobalWorkflow(data) {
  // A tool-only poll must update its whole evidence snapshot together while
  // preserving the user's design, unsaved text, revision and optimistic base.
  if (!state.envelope || !data) return;
  const workflow = state.envelope.workflow.map(stage => {
    if (!['global_synthesis', 'global_netlist_simulation'].includes(stage.id)) return stage;
    const status = data.stages.find(item => item.stage_id === stage.id);
    const latest = data.runs.find(run => run.id === status?.latest_run_id);
    return { ...stage, implemented: data.implemented, latest_run_id: status?.latest_run_id || null,
      accepted_run_id: status?.accepted_run_id || null, execution_status: latest?.execution_status || 'Not Run',
      validation_status: latest?.validation_status || 'Not Checked', review_status: latest?.review_status || 'Awaiting Review',
      freshness: latest?.freshness || 'Current', ready: data.ready, blocked_reason: data.blocked_reason };
  });
  state.envelope = { ...state.envelope, global_workflow: data, workflow };
  receiveExecution();
  globalFlow.receive(state.envelope);
  physicalFlow.receive(state.envelope);
  drcFlow.receive(state.envelope); lvsFlow.receive(state.envelope);
  postlayoutFlow.receive(state.envelope);
  syncChrome(); renderReview();
  void dependentStageRefresh.observe({ global_workflow: data });
}

function mergePhysicalWorkflow(data) {
  // Keep the complete physical run/review snapshot atomic without adopting a
  // newer source revision, replacing the draft or moving its optimistic base.
  if (!state.envelope || !data) return;
  const latest = data.runs.find(run => run.id === data.latest_run_id);
  const workflow = state.envelope.workflow.map(stage => stage.id !== 'layout' ? stage : {
    ...stage, implemented: data.implemented, latest_run_id: data.latest_run_id || null,
    accepted_run_id: data.accepted_run_id || null, execution_status: latest?.execution_status || 'Not Run',
    validation_status: latest?.validation_status || 'Not Checked', review_status: latest?.review_status || 'Awaiting Review',
    freshness: latest?.freshness || 'Current', ready: data.ready, blocked_reason: data.blocked_reason,
  });
  state.envelope = { ...state.envelope, physical_workflow: data, workflow };
  receiveExecution();
  physicalFlow.receive(state.envelope);
  drcFlow.receive(state.envelope); lvsFlow.receive(state.envelope);
  globalFlow.receive(state.envelope);
  postlayoutFlow.receive(state.envelope);
  syncChrome(); renderReview();
  void dependentStageRefresh.observe({ physical_workflow: data });
}

function mergeDRCWorkflow(data) {
  // Keep tool status/reviews atomic while retaining source drafts and save base.
  if (!state.envelope || !data) return;
  const latest = data.runs.find(run => run.id === data.latest_run_id);
  const workflow = state.envelope.workflow.map(stage => stage.id !== 'drc' ? stage : {
    ...stage, implemented: data.implemented, latest_run_id: data.latest_run_id || null,
    accepted_run_id: data.accepted_run_id || null, execution_status: latest?.execution_status || 'Not Run',
    validation_status: latest?.validation_status || 'Not Checked', review_status: latest?.review_status || 'Awaiting Review',
    freshness: latest?.freshness || 'Current', ready: data.ready, blocked_reason: data.blocked_reason,
  });
  state.envelope = { ...state.envelope, drc_workflow: data, workflow };
  receiveExecution();
  drcFlow.receive(state.envelope); lvsFlow.receive(state.envelope); physicalFlow.receive(state.envelope);
  postlayoutFlow.receive(state.envelope);
  syncChrome(); renderReview();
  void dependentStageRefresh.observe({ drc_workflow: data });
}

function mergeLVSWorkflow(data) {
  // Update complete LVS evidence without replacing a user's draft or save base.
  if (!state.envelope || !data) return;
  const latest = data.runs.find(run => run.id === data.latest_run_id);
  const workflow = state.envelope.workflow.map(stage => stage.id !== 'lvs' ? stage : {
    ...stage, implemented: data.implemented, latest_run_id: data.latest_run_id || null,
    accepted_run_id: data.accepted_run_id || null, execution_status: latest?.execution_status || 'Not Run',
    validation_status: latest?.validation_status || 'Not Checked', review_status: latest?.review_status || 'Awaiting Review',
    freshness: latest?.freshness || 'Current', ready: data.ready, blocked_reason: data.blocked_reason,
  });
  state.envelope = { ...state.envelope, lvs_workflow: data, workflow };
  receiveExecution();
  lvsFlow.receive(state.envelope); drcFlow.receive(state.envelope); physicalFlow.receive(state.envelope); globalFlow.receive(state.envelope);
  generationBatches.receive(state.envelope); generation.receive(state.envelope); localFlow.receive(state.envelope); implementationSpecs.receive(state.envelope); globalGeneration.receive(state.envelope);
  postlayoutFlow.receive(state.envelope);
  syncChrome(); renderReview();
  void dependentStageRefresh.observe({ lvs_workflow: data });
}

function mergePostlayoutWorkflow(data) {
  // Atomically refresh tool evidence, retaining source drafts and their save base.
  if (!state.envelope || !data) return;
  const latest = data.runs.find(run => run.id === data.latest_run_id);
  const workflow = state.envelope.workflow.map(stage => stage.id !== 'post_layout_verification' ? stage : {
    ...stage, implemented: data.implemented, latest_run_id: data.latest_run_id || null,
    accepted_run_id: data.accepted_run_id || null, execution_status: latest?.execution_status || 'Not Run',
    validation_status: latest?.validation_status || 'Not Checked', review_status: latest?.review_status || 'Awaiting Review',
    freshness: latest?.freshness || 'Current', ready: data.ready, blocked_reason: data.blocked_reason,
  });
  state.envelope = { ...state.envelope, postlayout_workflow: data, workflow };
  receiveExecution();
  postlayoutFlow.receive(state.envelope); lvsFlow.receive(state.envelope); drcFlow.receive(state.envelope);
  physicalFlow.receive(state.envelope); globalFlow.receive(state.envelope);
  generationBatches.receive(state.envelope); generation.receive(state.envelope); localFlow.receive(state.envelope);
  implementationSpecs.receive(state.envelope); globalGeneration.receive(state.envelope);
  syncChrome(); renderReview();
}

async function api(path, body) {
  body = reviewOperator.request(path, body, state.envelope?.review_operator_version);
  const capturedTransportSession = typeof workspaceSession === 'function' ? workspaceSession() : null;
  const submissionRequestScope = typeof executionSubmissions !== 'undefined' && executionSubmissions ? executionSubmissionScope() : null;
  if (typeof executionSubmissions !== 'undefined' && executionSubmissions && body !== undefined) body = executionSubmissions.prepare(path, body);
  const action = executionAction(path, body);
  const scope = executionScope();
  if (state.envelope?.revision?.id) executionState.setScope(scope);
  const token = action ? executionState.begin(action) : null;
  // Paint before the first await: previous results must never look current while
  // the newly requested operation is waiting for the local service.
  if (token && state.design) syncChrome();
  let response, result;
  try {
    const options = body === undefined ? { cache: 'no-store' } : { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) };
    // Bound observation, including catalog/bootstrap and JSON body reads.
    // An explicit Open POST retains its larger history-validation allowance;
    // execution POST deadlines and one-request-only behavior are unchanged.
    if (body === undefined || body?.submission_id) options.signal = AbortSignal.timeout(60000);
    else if (path.startsWith('workspace/')) options.signal = AbortSignal.timeout(path === 'workspace/open' ? 300000 : 60000);
    response = await sessionFetch(`/api/${path}`, options);
    try { result = await response.json(); }
    catch (error) {
      if (response.ok || ['TimeoutError', 'AbortError'].includes(error.name)) throw error;
      result = {}; // Preserve the HTTP error even when its body is not JSON.
    }
    if (typeof workspaceSession === 'function' && capturedTransportSession !== workspaceSession()) throw new Error('The project context changed while the response was being read. Its response was ignored.');
  } catch (error) {
    if (typeof executionSubmissions !== 'undefined' && executionSubmissions && body !== undefined) executionSubmissions.observeFailure(path, body, error, submissionRequestScope);
    if (body === undefined && ['TimeoutError', 'AbortError'].includes(error.name)) {
      const failure = new Error('Saved progress was not read within 60 seconds. The last observed status may be out of date; this is not a circuit verification failure. Refresh saved status or reconnect without resending execution. No tool or model request was repeated.');
      failure.code = 'read_timeout'; failure.read_only = true;
      throw failure;
    }
    if (token) { executionState.failure(token, error); if (state.design) syncChrome(); }
    else if (body === undefined) executionReadFailure(path, error);
    if (error.message?.includes('context changed')) throw error;
    if (error.name === 'TimeoutError' || error.name === 'AbortError') throw new Error('The local service did not respond in time. Your saved projects remain intact. Refresh Projects before retrying; the operation may already have completed.');
    if (response?.ok) throw new Error('The local service response could not be read. Your saved projects and browser edits remain intact. Refresh saved status before retrying; the operation may already have completed.');
    byId('service-state').textContent = 'Service unavailable';
    byId('service-dot').classList.add('offline');
    throw new Error('The local service is unavailable. Your edits remain in this browser. Reconnect and open the saved project when ready.');
  }
  if (!response.ok) {
    const raw = result.error;
    const message = typeof raw === 'string' ? raw : raw?.message || result.message || `Request failed (${response.status}).`;
    const code = typeof raw === 'object' && raw !== null ? raw.code : null;
    const workspaceConflict = response.status === 409 && ['workspace_session_changed', 'revision_conflict'].includes(code);
    const error = new Error(workspaceConflict ? `${message} Your draft was preserved. Open Projects to reconnect explicitly or export your draft.` : message);
    error.status = response.status; error.code = code;
    error.generationStartRejectedBeforeCreation = raw?.generation_start_rejected_before_creation === true;
    error.submissionId = raw?.submission_id;
    error.executionStartRejectedBeforeCreation = raw?.execution_start_rejected_before_creation === true;
    if (typeof executionSubmissions !== 'undefined' && executionSubmissions && body !== undefined) executionSubmissions.observeFailure(path, body, error, submissionRequestScope);
    if (token) { executionState.failure(token, error); if (state.design) syncChrome(); }
    else if (body === undefined) executionReadFailure(path, error);
    throw error;
  }
  if (body === undefined && scope === executionScope() && ['project', 'bootstrap'].includes(path)) {
    generation.observeSavedProgress(result);
    if (typeof executionSubmissions !== 'undefined' && executionSubmissions) executionSubmissions.observeRead(result, executionSubmissionScope(result));
  }
  if (typeof executionSubmissions !== 'undefined' && executionSubmissions && body !== undefined) {
    try {
      if (submissionRequestScope !== executionSubmissionScope() || scope !== executionScope()) throw new Error('The project or saved source changed while execution was starting. Refresh its exact saved receipt; no request was resent.');
      executionSubmissions.observeSuccess(path, body, result);
    } catch (error) {
      executionSubmissions.observeFailure(path, body, error, submissionRequestScope);
      if (token) { executionState.failure(token, error); if (state.design) syncChrome(); }
      throw error;
    }
  }
  byId('service-state').textContent = 'Local service';
  byId('service-dot').classList.remove('offline');
  if (token) executionState.success(token, result);
  // Inspection payloads carry source stage/run IDs, but are not execution or
  // review envelopes. They must not overwrite the browser's adoption ledger.
  else if (!path.startsWith('inspection/') && executionState.scopeKey === scope) executionState.receive(result, scope);
  if (token && state.design) syncChrome();
  return result;
}

function executionReadFailure(path, error) {
  const groups = [
    [/^generation(?:\/|$)/, ['local_rtl_generation']],
    [/^workflow(?:\/|$)/, ['local_synthesis', 'local_netlist_simulation']],
    [/^implementation-specs(?:\/|$)/, ['node_implementation_specs']],
    [/^global-generation(?:\/|$)/, ['global_rtl_generation']],
    [/^global-workflow(?:\/|$)/, ['global_synthesis', 'global_netlist_simulation']],
    [/^physical-workflow(?:\/|$)/, ['layout']], [/^drc-workflow(?:\/|$)/, ['drc']],
    [/^lvs-workflow(?:\/|$)/, ['lvs']], [/^postlayout-workflow(?:\/|$)/, ['post_layout_verification']],
  ];
  let changed = false;
  if (path === 'project' || path === 'bootstrap') changed = executionState.observeFailure(error);
  else for (const [pattern, stages] of groups) if (pattern.test(path)) {
    for (const id of stages) changed = executionState.observeFailure(error, id) || changed;
    break;
  }
  if (changed && state.design) syncChrome();
}

function notify(message, kind = 'info') {
  const notice = { message, kind };
  state.messageNotice = notice;
  const target = byId('message');
  target.className = `message ${kind}`;
  target.replaceChildren(el('span', { text: message }), el('button', { type: 'button', class: 'message-close', 'aria-label': 'Dismiss message', text: '×', onclick: () => { target.hidden = true; } }));
  target.hidden = false;
  return notice;
}

function resolveNotice(notice) {
  // Resolving an operation's former error must never dismiss a newer error
  // from another operation, even if its message text happens to be identical.
  if (!notice || notice.kind !== 'error' || state.messageNotice !== notice) return false;
  byId('message').hidden = true;
  state.messageNotice = null;
  return true;
}

function toast(message) {
  const target = byId('toast'); target.textContent = message; target.hidden = false;
  clearTimeout(state.toastTimer); state.toastTimer = setTimeout(() => { target.hidden = true; }, 3500);
}

function autosave() {
  // If backup persistence failed, do not overwrite the sole remaining older
  // draft. Explicit saving/exporting still protects the active project.
  if (state.recoveryUnpersisted || !state.envelope || !state.design) return;
  try {
    if (dirty() || adapterDraftDirty() || generation.profileDirty() || adoption.dirty()) localStorage.setItem(DRAFT_KEY, JSON.stringify({ design: state.design, verification_drafts: state.verificationDrafts, postlayout_adapter_drafts: postlayoutFlow.adapterBackup?.() || [], provider_draft: generation.profileDirty() ? generation.profileDraft : null, policy_draft: adoption.dirty() ? adoption.draft : null, workspace: activeWorkspace, base_revision_id: state.envelope.revision.id, stage: state.stage, saved_at: new Date().toISOString() }));
    else localStorage.removeItem(DRAFT_KEY);
  } catch { /* Explicit save remains available if browser draft storage is full or disabled. */ }
}

function loadRecoveredDrafts() {
  try {
    const records = JSON.parse(localStorage.getItem(RECOVERY_KEY) || '[]');
    if (Array.isArray(records)) state.recovered = records.filter(record => record?.id && record.design?.schema_version === '0.1');
  } catch { /* A malformed backup is not removed or overwritten on startup. */ }
  renderRecoveredDrafts();
}

function isolateRecoveredDraft(draft) {
  if (!state.recovered.some(record => record.base_revision_id === draft.base_revision_id && equal(record.design, draft.design) && equal(record.verification_drafts || {}, draft.verification_drafts || {}) && equal(record.postlayout_adapter_drafts || [], draft.postlayout_adapter_drafts || []))) {
    state.recovered.push({ id: newId('recovered'), design: clone(draft.design), verification_drafts: clone(draft.verification_drafts || {}), postlayout_adapter_drafts: clone(draft.postlayout_adapter_drafts || []), base_revision_id: draft.base_revision_id, saved_at: draft.saved_at || null, recovered_at: new Date().toISOString() });
  }
  try {
    // The separate backup is committed before removing the original draft key.
    // Ordinary save/load/import/edit operations never touch this backup key.
    localStorage.setItem(RECOVERY_KEY, JSON.stringify(state.recovered));
    localStorage.removeItem(DRAFT_KEY);
  } catch {
    state.recoveryUnpersisted = true;
    notify('Browser backup storage is unavailable. The older draft has been retained; export it before closing this page. New edits can still be saved explicitly.', 'warning');
  }
  state.recoveredSelection = state.recovered.at(-1)?.id;
  renderRecoveredDrafts();
}

function renderRecoveredDrafts() {
  const host = byId('recovered-drafts');
  host.hidden = !state.recovered.length;
  if (!state.recovered.length) { host.replaceChildren(); return; }
  let selected = state.recovered.find(record => record.id === state.recoveredSelection) || state.recovered.at(-1);
  state.recoveredSelection = selected.id;
  const select = el('select', { 'aria-label': 'Recovered draft to export or discard', 'data-testid': 'recovered-draft-select', value: selected.id, onchange: event => { state.recoveredSelection = event.target.value; renderRecoveredDrafts(); } },
    state.recovered.map(record => el('option', { value: record.id, text: `${record.design.project?.name || 'Design draft'} · ${formatDate(record.saved_at || record.recovered_at)}` })));
  select.value = selected.id;
  host.replaceChildren(el('div', { class: 'recovery-description' }, el('strong', { text: `${state.recovered.length} recovered draft backup(s)` }), el('span', { text: 'Older saved revision. Retained separately from the active design until you explicitly discard it.' })),
    select,
    el('button', { type: 'button', text: 'Export recovered draft', 'data-testid': 'export-recovered-draft', onclick: () => downloadJson(selected.design, `HuLLCirq-recovered-${selected.id}.json`) }),
    ...(Object.keys(selected.verification_drafts || {}).length || selected.postlayout_adapter_drafts?.length ? [el('button', { type: 'button', text: 'Export unfinished verification text', 'data-testid': 'export-recovered-verification', onclick: () => downloadJson({ project_id: selected.design.project?.id, base_revision_id: selected.base_revision_id, verification_drafts: selected.verification_drafts, postlayout_adapter_drafts: selected.postlayout_adapter_drafts || [] }, `HuLLCirq-recovered-${selected.id}-unfinished-verification.json`) })] : []),
    el('button', { type: 'button', class: 'danger', text: 'Discard backup', 'data-testid': 'discard-recovered-draft', onclick: () => {
      if (!confirm('Permanently discard this recovered browser draft backup? Export it first if you want to keep a copy. The active project will not change.')) return;
      const remaining = state.recovered.filter(record => record.id !== selected.id);
      try {
        if (remaining.length) localStorage.setItem(RECOVERY_KEY, JSON.stringify(remaining)); else localStorage.removeItem(RECOVERY_KEY);
        if (state.recoveryUnpersisted) localStorage.removeItem(DRAFT_KEY);
        state.recovered = remaining; state.recoveryUnpersisted = false;
        renderRecoveredDrafts(); autosave(); toast('Recovered backup discarded. The active project is unchanged.');
      } catch { notify('The backup could not be removed from browser storage. It remains available for export.', 'error'); }
    } }));
}

function adopt(envelope, preserveDraft = false) {
  // A response can arrive while a person is still typing. Commit that field before
  // rebuilding the view so the incoming result cannot discard their latest edit.
  if (preserveDraft) flushActiveField();
  if (preserveDraft && state.envelope && envelope.revision.id !== state.envelope.revision.id) {
    mergeGenerationEnvelope(envelope); render(); return;
  }
  if (compactSnapshot()) for (const { module } of evidenceViews) { module.host = null; module.reviewHost = null; }
  state.envelope = envelope;
  receiveExecution(envelope);
  state.externalRevision = null;
  state.saved = clone(envelope.design);
  if (!preserveDraft) { state.design = clone(envelope.design); state.verificationDrafts = {}; }
  generationBatches.receive(envelope); generation.receive(envelope);
  adoption.receive(envelope);
  localFlow.receive(envelope);
  implementationSpecs.receive(envelope);
  globalGeneration.receive(envelope);
  globalFlow.receive(envelope);
  physicalFlow.receive(envelope);
  drcFlow.receive(envelope);
  lvsFlow.receive(envelope);
  postlayoutFlow.receive(envelope);
  autosave(); render();
}

function mutate(change, renderContent = true) {
  if (readOnly()) { toast('This snapshot is read-only. Duplicate it from Projects to edit.'); return; }
  flushActiveField();
  const previous = clone(state.design);
  change(state.design);
  if (equal(previous, state.design)) return;
  state.undo.push(previous);
  if (state.undo.length > 80) state.undo.shift();
  state.redo.length = 0;
  autosave();
  if (renderContent) render();
  else { syncChrome(); state.graph?.update(state.design, state.selected); renderHierarchy(); refreshConnectionChoices(); renderReview(); }
}

function undo() {
  if (!state.undo.length || state.busy) return;
  state.redo.push(clone(state.design)); state.design = state.undo.pop();
  checkSelection(); autosave(); render();
}

function redo() {
  if (!state.redo.length || state.busy) return;
  state.undo.push(clone(state.design)); state.design = state.redo.pop();
  checkSelection(); autosave(); render();
}

function checkSelection() {
  if (!state.selected) return;
  if (state.selected.kind === 'external') { if (!hasExternalIO(state.design)) state.selected = null; return; }
  const items = state.selected.kind === 'node' ? state.design.nodes : state.selected.kind === 'external_binding' ? state.design.external_io?.connections || [] : state.design.edges;
  if (!items.some(item => item.id === state.selected.id)) state.selected = null;
}

function select(selection, additive = false) {
  flushActiveField();
  if (additive && selection?.kind === 'node' && state.selected?.kind === 'node') {
    const ids = new Set(state.selected.ids || [state.selected.id]);
    if (ids.has(selection.id)) ids.delete(selection.id); else ids.add(selection.id);
    state.selected = ids.size ? { ...selection, ids: [...ids] } : null;
  } else state.selected = selection ? { ...selection, ...(selection.kind === 'node' ? { ids: [selection.id] } : {}) } : null;
  state.graph?.update(state.design, state.selected); renderInspector(); renderHierarchy();
}

function setStage(id) {
  if (!STAGES.some(stage => stage[0] === id)) return;
  flushActiveField();
  const previousNode = state.stage === 'local_rtl_generation' ? generation.nodeId : state.stage === 'node_implementation_specs' ? implementationSpecs.nodeId : ['local_synthesis', 'local_netlist_simulation'].includes(state.stage) ? localFlow.nodeId : null;
  if (previousNode && ['local_rtl_generation', 'local_synthesis', 'local_netlist_simulation', 'node_implementation_specs'].includes(id)) {
    localFlow.setNode(previousNode); implementationSpecs.setNode(previousNode);
    if (generation.nodeId !== previousNode) { generation.nodeId = previousNode; generation.selectedJobId = state.envelope.generation?.nodes?.find(node => node.node_id === previousNode)?.latest_job_id || null; }
  }
  state.stage = id; autosave(); render();
  byId('stage-title').focus({ preventScroll: true });
}

function syncChrome() {
  if (!state.design) return;
  renderRecoveredDrafts();
  byId('project-title').textContent = workspaceEnabled ? `${workspace.project()?.name || state.design.project.name} / ${workspace.system()?.name || state.design.project.name}` : state.design.project.name;
  const milestone = document.querySelector('.milestone');
  if (milestone) milestone.textContent = state.envelope.postlayout_workflow?.implemented ? (postlayoutFlow.eventDiagnostic() ? 'S01–S13 · Saved S14 event diagnostic' : postlayoutFlow.diagnostic() ? 'S01–S13 · Saved S14 timed diagnostic' : postlayoutFlow.preflight() ? 'S01–S13 · S14 readiness check' : 'S01–S14 · Design & post-layout verification') : state.envelope.lvs_workflow?.implemented ? 'S01–S13 · Layout, DRC & LVS' : state.envelope.drc_workflow?.implemented ? 'S01–S12 · Layout & DRC' : state.envelope.physical_workflow?.implemented ? 'S01–S11 · Physical layout' : state.envelope.global_workflow?.implemented ? 'S01–S10 · Whole-design netlist verification' : state.envelope.global_generation ? 'S01–S08 · Global RTL integration' : state.envelope.implementation?.milestone === 'M2-C' ? 'S01–S07 · Node evidence' : state.envelope.implementation?.milestone === 'M2-B' ? 'M2-B · Node RTL, synthesis & netlist' : 'M2-A · Node RTL candidates';
  const hasDraft = !!dirty() || adapterDraftDirty(), hasInputDraft = !!stageInputDirty();
  byId('save-state').className = `save-state${hasDraft ? ' unsaved' : ''}`;
  byId('save-state').textContent = state.busy ? 'Working with local service…' : state.externalRevision ? '● Newer saved design · source retained' : executionInputDirty() ? '● Unsaved design inputs · browser draft retained' : physicalDraftDirty() ? '● Unsaved physical constraints · S01–S10 evidence unchanged' : adapterDraftDirty() ? '● Unsaved S14 adapter text · source-bound browser backup retained' : hasDraft ? '● Unsaved canvas view · saved evidence unchanged' : '✓ Saved locally';
  byId('revision-label').textContent = `Revision ${state.envelope.revision.id}`;
  byId('save-project').disabled = readOnly() || state.busy || !dirty() || !!invalidVerification();
  byId('save-project').title = invalidVerification() ? 'Apply or discard pending verification text in Specifications before saving. Its draft remains in this browser.' : 'Save the current design input.';
  byId('undo').disabled = state.busy || !state.undo.length;
  byId('redo').disabled = state.busy || !state.redo.length;
  for (const id of ['load-project', 'import-project', 'export-project']) byId(id).disabled = state.busy;
  const workflow = workflowStage(state.stage);
  const implemented = workflow?.implemented ?? STAGES.findIndex(stage => stage[0] === state.stage) < 3;
  const candidateStage = ['local_rtl_generation', 'global_rtl_generation'].includes(state.stage);
  const toolStage = ['local_synthesis', 'local_netlist_simulation'].includes(state.stage);
  const globalToolStage = ['global_synthesis', 'global_netlist_simulation'].includes(state.stage);
  const physicalStage = state.stage === 'layout';
  const drcStage = state.stage === 'drc';
  const lvsStage = state.stage === 'lvs';
  const postlayoutStage = state.stage === 'post_layout_verification';
  const implementationStage = state.stage === 'node_implementation_specs';
  byId('run-verification').textContent = postlayoutStage ? postlayoutFlow.actionLabel() : lvsStage ? 'Run LVS' : drcStage ? 'Run DRC' : physicalStage ? 'Run physical layout' : candidateStage ? 'Checks run with generation' : state.stage === 'local_synthesis' ? 'Run synthesis for all nodes' : state.stage === 'local_netlist_simulation' ? 'Verify all node netlists' : state.stage === 'global_synthesis' ? 'Run synthesis' : ['local_netlist_simulation', 'global_netlist_simulation'].includes(state.stage) ? 'Run netlist verification' : implementationStage ? 'Derive and verify specification' : 'Run verification';
  byId('run-verification').disabled = state.busy || hasInputDraft || !!state.externalRevision || !implemented || candidateStage || (toolStage && (!!localFlow.batchGate() || localFlow.busy)) || (globalToolStage && (!!globalFlow.gate() || globalFlow.busy)) || (physicalStage && (!!physicalFlow.gate() || physicalFlow.busy)) || (drcStage && (!!drcFlow.gate() || drcFlow.busy)) || (lvsStage && (!!lvsFlow.gate() || lvsFlow.busy)) || (postlayoutStage && (!!postlayoutFlow.gate() || postlayoutFlow.busy)) || (implementationStage && (!!implementationSpecs.gate() || implementationSpecs.busy));
  byId('run-verification').title = state.externalRevision ? 'A newer saved design was detected. Export your draft, then Open saved.' : candidateStage ? 'Generate RTL from the inspected context. S04 checks the external interface; S05 synthesizes and S06 verifies circuit behavior.' : !implemented ? 'This execution stage is not implemented yet.' : hasInputDraft ? 'Save the current design inputs before running verification.' : postlayoutStage ? postlayoutFlow.gate() || (postlayoutFlow.eventDiagnostic() ? 'Validate saved event, conditional-path and original-job reports; no new simulator is started; dynamic verification is not implemented by this adapter and this result cannot be accepted.' : postlayoutFlow.diagnostic() ? 'Validate saved timed results and original source hashes; no new simulator is started; dynamic verification is not implemented by this adapter and this result cannot be accepted.' : postlayoutFlow.preflight() ? 'Check S14 compatibility only. This adapter does not implement dynamic verification, so this result cannot complete S14.' : 'Verify the original job with the adopted physical circuit and recorded timing scope.') : lvsStage ? lvsFlow.gate() || 'Extract the exact adopted GDS and compare it with its corresponding mapped netlist.' : drcStage ? drcFlow.gate() || 'Run the fixed DRC checks on the exact adopted S11 GDS.' : physicalStage ? physicalFlow.gate() || 'Run the recorded physical profile with exact adopted S08/S09/S10 sources.' : globalToolStage ? globalFlow.gate() || 'Run the trusted whole-design tool with the exact adopted sources and original-job plan.' : implementationStage ? implementationSpecs.gate() || 'Derive and verify this node specification from its adopted S06 evidence.' : state.stage === 'local_synthesis' ? localFlow.batchGate() || 'Synthesize pending node RTL separately in one sequential batch; retain accepted results.' : state.stage === 'local_netlist_simulation' ? localFlow.batchGate() || 'Verify remaining eligible nodes sequentially with their exact accepted S05 netlists and original saved inputs.' : 'Run deterministic input checks for this saved revision.';
  byId('run-verification').hidden = state.stage === 'local_rtl_generation';
  generation.refreshGenerationActions();
  if (['local_rtl_generation', 'local_synthesis', 'local_netlist_simulation', 'node_implementation_specs', 'global_synthesis', 'global_netlist_simulation', 'layout', 'drc', 'lvs', 'post_layout_verification'].includes(state.stage)) {
    const selected = postlayoutStage ? postlayoutFlow.selected() : lvsStage ? lvsFlow.selected() : drcStage ? drcFlow.selected() : physicalStage ? physicalFlow.selected() : globalToolStage ? globalFlow.selected() : state.stage === 'local_rtl_generation' ? generation.selectedJob() : implementationStage ? implementationSpecs.selected() : localFlow.selected();
    renderReviewState();
  }
  const toolState = byId('eda-connection-state');
  if (toolState) toolState.textContent = state.envelope.postlayout_workflow?.implemented ? (postlayoutFlow.eventDiagnostic() ? 'EDA · Saved S14 event diagnostic · dynamic verification not implemented' : postlayoutFlow.diagnostic() ? 'EDA · Saved S14 timed diagnostic · dynamic verification not implemented' : postlayoutFlow.preflight() ? 'EDA · S14 compatibility API · dynamic simulation unsupported' : 'EDA · Layout, DRC, LVS & post-layout verification API') : state.envelope.lvs_workflow?.implemented ? 'EDA · Node, whole-design, layout, DRC & LVS API' : state.envelope.drc_workflow?.implemented ? 'EDA · Node, whole-design, layout & DRC API' : state.envelope.physical_workflow?.implemented ? 'EDA · Node, whole-design & physical execution API' : state.envelope.global_workflow?.implemented ? 'EDA · Node & whole-design execution API' : state.envelope.workflow?.some(stage => ['local_synthesis', 'local_netlist_simulation'].includes(stage.id) && stage.implemented) ? 'EDA · Node execution API' : 'EDA · Not configured';
  connectionMonitor.receive(); renderConnectionStatus();
  renderTabs(); renderStageStatus();
  applyReadOnly();
  renderNextStep();
}

function guidanceContext() {
  const index = STAGES.findIndex(([id]) => id === state.stage);
  const definitions = {
    local_synthesis: [localFlow, 'local_rtl_generation', 'Run synthesis for all nodes', 'workflow-batch-run', 'workflow-continue'],
    local_netlist_simulation: [localFlow, 'local_synthesis', 'Verify all node netlists', 'workflow-batch-run', 'workflow-continue'],
    node_implementation_specs: [implementationSpecs, 'local_netlist_simulation', 'Derive and verify specification', 'implementation-spec-run', 'implementation-continue'],
    global_rtl_generation: [globalGeneration, 'node_implementation_specs', 'Context Preview', 'global-context-preview', 'global-continue'],
    global_synthesis: [globalFlow, 'global_rtl_generation', 'Run synthesis', 'global-workflow-run', 'global-workflow-continue'],
    global_netlist_simulation: [globalFlow, 'global_synthesis', 'Run netlist verification', 'global-workflow-run', 'global-workflow-continue'],
    layout: [physicalFlow, 'global_netlist_simulation', 'Run physical layout', 'physical-workflow-run', 'physical-workflow-continue'],
    drc: [drcFlow, 'layout', 'Run DRC', 'drc-workflow-run', 'drc-workflow-continue'],
    lvs: [lvsFlow, 'drc', 'Run LVS', 'lvs-workflow-run', 'lvs-workflow-continue'],
    post_layout_verification: [postlayoutFlow, 'lvs', postlayoutFlow.actionLabel(), 'postlayout-workflow-run', null],
  };
  const [module, prerequisite, runLabel, runTestId, continueTestId] = definitions[state.stage] || [];
  const nodeId = state.stage === 'local_rtl_generation' ? generation.nodeId : index >= 4 && index <= 6 ? module?.nodeId : null;
  const record = index < 3 ? stageRun() : state.stage === 'local_rtl_generation' ? generation.selectedJob() : module?.selected();
  const latest = typeof module?.currentRun === 'function' ? module.currentRun() : module?.relevant?.()[0] || (module?.data?.runs || module?.data?.jobs || []).filter(item => !item.stage_id || item.stage_id === state.stage).at(-1);
  const recordCurrent = record && typeof module?.runCurrent === 'function' ? module.runCurrent(record) : undefined;
  const activeRecord = [
    ...(state.envelope.repair_analysis?.jobs || []).map(r => ({ ...r, stage_id: 'local_rtl_generation' })),
    ...(state.envelope.generation?.jobs || []).map(r => ({ ...r, stage_id: 'local_rtl_generation' })), ...(state.envelope.workflow_runs || []),
    ...(state.envelope.global_generation?.jobs || []).map(r => ({ ...r, stage_id: 'global_rtl_generation' })),
    ...(state.envelope.global_workflow?.runs || []),
    ...['physical_workflow', 'drc_workflow', 'lvs_workflow', 'postlayout_workflow'].flatMap((key, i) => (state.envelope[key]?.runs || []).map(r => ({...r, stage_id: ['layout', 'drc', 'lvs', 'post_layout_verification'][i]}))),
  ].find(r => ['Queued', 'Running'].includes(r.execution_status));
  const nextButton = continueTestId && document.querySelector(`[data-testid="${continueTestId}"]`);
  const nextNode = implementationSpecs.nextNode();
  const reconnectId = state.stage === 'local_rtl_generation' ? 'reconnect-generation' : ['local_synthesis','local_netlist_simulation'].includes(state.stage) ? 'workflow-reconnect' : state.stage === 'global_rtl_generation' ? 'global-refresh' : runTestId?.replace(/-run$/, '-reconnect');
  const batchGuidance = state.stage === 'local_rtl_generation' ? generationBatches.guidance({ singleRequestPrepared: !!(generation.retryOfJobId || (generation.operation === 'repair' && generation.baseJobId) || (generation.preview && !generation.previewStale)) }) : null;
  return {
    stage: state.stage, readOnly: readOnly(), conflict: !!state.externalRevision, dirty: stageInputDirty(), busy: state.busy || !!module?.busy,
    executionOverlay: executionState.overlay(state.stage),
    hasSavedEvidence: !!record?.id || stageHasSavedEvidence(state.envelope, state.stage),
    executionUpstreamRunning: (() => { const stage = STAGES.slice(0, index).find(([id]) => executionState.overlay(id)?.status === 'Running')?.[0]; return stage ? { stage } : null; })(),
    executionReconnect: async () => {
      try { mergeGenerationEnvelope(await api('project')); toast('Saved results refreshed. No execution request was resent.'); }
      catch (error) { notify(error.message, 'error'); }
    },
    invalidInput: invalidVerification() ? 'Verification text is unapplied or invalid. Apply or discard it in Specifications before saving.' : null,
    activeOperation: activeRecord ? {stage: activeRecord.stage_id, nodeId: activeRecord.node_id} : generationBatches.activeBatch() ? {stage:'local_rtl_generation'} : localFlow.activeBatch() ? {stage:localFlow.batchStage(localFlow.activeBatch())} : null,
    nodeId, nodeName: state.design.nodes.find(node => node.id === nodeId)?.name,
    record, recordCurrent, historical: !!(record && (recordCurrent === false || latest && record.id !== latest.id)), implemented: workflowStage(state.stage)?.implemented,
    gate: state.stage === 'local_netlist_simulation' ? localFlow.batchGate() : module?.gate() || '', blocker: module?.blocker?.() || null, prerequisite, runLabel, runTestId, continueTestId,
    repairAvailable: ['local_synthesis','local_netlist_simulation'].includes(state.stage) && !localFlow.repairGate(record),
    failureExcerpt: state.stage === 'local_synthesis' ? localFlow.firstSynthesisFailure(record) : state.stage === 'local_netlist_simulation' ? localFlow.firstFailure(record) : null,
    synthesisSummary: state.stage === 'local_synthesis' ? localFlow.synthesisSummary() : null,
    netlistSummary: state.stage === 'local_netlist_simulation' ? localFlow.netlistSummary() : null,
    netlistBatchGate: state.stage === 'local_netlist_simulation' ? localFlow.batchGate() : '',
    netlistBlocker: state.stage === 'local_netlist_simulation' ? localFlow.netlistBlockerFor(localFlow.netlistSummary().firstBlocked?.id) : null,
    synthesisBatchGate: state.stage === 'local_synthesis' ? localFlow.batchGate() : '',
    synthesisBatch: state.stage === 'local_synthesis' ? localFlow.selectedBatch() : null,
    synthesisRepairCount: state.stage === 'local_synthesis' ? generationBatches.failedSynthesis().filter(item => !item.blocked).length : 0,
    synthesisRepairGate: state.stage === 'local_synthesis' ? generationBatches.gate() : '',
    synthesisRepairGuidance: generationBatches.repairOutcomeSummary?.() || null,
    integrationUnsupported: state.envelope.global_generation?.ready === false && /currently integrates|six declared|unsupported|not implemented/i.test(state.envelope.global_generation?.blocked_reason || '') ? state.envelope.global_generation.blocked_reason : null,
    sourceRevisionConflict: state.stage === 'global_rtl_generation' && state.envelope.global_generation?.blocked_code === 'global_revision_conflict',
    continueBlocked: nextButton?.disabled ? nextButton.title || 'The next stage needs additional current evidence or implementation support.' : null,
    configurationBlocked: module?.data?.tool_ready === false && module?.data?.ready === true,
    completionBlocked: state.stage === 'post_layout_verification' && (postlayoutFlow.preflight(record) || postlayoutFlow.diagnostic(record) || postlayoutFlow.eventDiagnostic(record)) ? 'This is a compatibility or saved-diagnostic result. It does not complete dynamic post-layout verification.' : null,
    reconnect: ['local_synthesis','local_netlist_simulation'].includes(state.stage) && (localFlow.batchStartUncertain || localFlow.batchPollError) ? 'workflow-batch-reconnect' : (module?.uncertainStart || module?.pollError || (state.stage === 'local_rtl_generation' && (generation.pollFailure || generation.pendingStart()))) ? reconnectId : null,
    emptyGraph: !state.design.nodes.length, nextNode,
    missingInputStage: index < 3 ? STAGES.slice(0,index).find(([id]) => workflowStage(id)?.review_status !== 'Accepted' || workflowStage(id)?.freshness !== 'Current')?.[0] : null,
    localGuidance: state.stage === 'local_rtl_generation' ? batchGuidance || generation.guidance?.() : null,
    generationBatchGuidance: batchGuidance,
    previewReady: !!globalGeneration.preview,
  };
}

function renderNextStep() {
  const host = byId('next-step');
  if (!host || !state.design) return;
  const recovery = typeof executionSubmissions !== 'undefined' && executionSubmissions ? executionSubmissions.presentation() : null;
  if (recovery) {
    host.className = 'next-step warning'; host.setAttribute('data-guidance-id', 'execution.submission-recovery');
    host.replaceChildren(el('div', { class: 'next-step-copy' }, el('span', { class: 'eyebrow', text: 'EXECUTION RECOVERY' }),
      el('h2', { text: recovery.title }), el('p', { text: recovery.label }), el('p', { text: recovery.summary })),
      el('div', { class: 'next-step-actions' },
        el('button', { type: 'button', class: 'primary', text: 'Refresh saved outcome', disabled: recovery.readDisabled, 'data-testid': 'execution-submission-refresh', onclick: () => executionSubmissions.refresh() }),
        el('button', { type: 'button', text: 'Retry same request', disabled: recovery.retryDisabled, title: recovery.retryReason, 'data-testid': 'execution-submission-retry', onclick: () => executionSubmissions.retry() })));
    return;
  }
  applyExecutionSelection();
  const context = guidanceContext(), guide = resolveStageGuidance(context);
  function perform(action) {
    if (action.disabled) return;
    if (typeof action.action === 'function') { action.action(); return; }
    if (action.kind === 'navigate') { navigateNode(action.stage, action.nodeId); return; }
    if (action.kind === 'latest') {
      const view = evidenceViews.find(view => view.stages.includes(state.stage)), module = view?.module;
      if (module) { module.runId = null; module.runPinned = false; module.specId = null; module.selectedId = null; module.refresh?.(); renderNextStep(); }
      return;
    }
    const target = action.kind === 'control' ? document.querySelector(`[data-testid="${action.testId}"]`) : byId(action.target);
    if (!target) { notify('The requested control is not currently available. Inspect this stage’s recorded results.', 'warning'); return; }
    if (action.kind === 'control' && !target.disabled) target.click();
    else { target.scrollIntoView({block:'center',behavior:'smooth'}); if (!target.hasAttribute('tabindex')) target.tabIndex = -1; target.focus({preventScroll:true}); if (target.disabled) toast(target.title || 'Complete the requirement shown beside this control.'); }
  }
  const button = (action, primary) => action ? el('button', {type:'button',class:primary ? 'primary' : '',text:action.label,disabled:!!action.disabled,'data-testid':primary ? 'next-step-primary' : 'next-step-secondary',onclick:()=>perform(action)}) : null;
  host.className = `next-step ${guide.tone || 'info'}`;
  host.setAttribute('data-guidance-id', guide.decisionId);
  host.replaceChildren(el('div',{class:'next-step-copy'},el('div',{class:'next-step-meta'},el('span',{class:'eyebrow',text:'NEXT STEP'}),el('span',{text:guide.phase}),el('span',{text:guide.scope})),el('h2',{text:guide.title}),el('p',{text:guide.summary}),guide.detail ? el('p',{class:'next-step-detail',text:guide.detail}) : null),el('div',{class:'next-step-actions'},button(guide.primary,true),button(guide.secondary,false)));
}

// S08 refreshes its preview locally, without an envelope update.
const refreshGlobalGuidance = globalGeneration.refresh.bind(globalGeneration);
globalGeneration.refresh = function (...args) { const value = refreshGlobalGuidance(...args); if (state.stage === 'global_rtl_generation') renderNextStep(); return value; };

function renderTabs() {
  const nav = byId('stage-tabs');
  const visuals = STAGES.map(([id]) => stageVisual(id));
  const groups = [[0, 3, '01–03 · Define'], [3, 7, '04–07 · Build nodes'], [7, 10, '08–10 · Integrate'], [10, 14, '11–14 · Physical']];
  nav.replaceChildren(...groups.map(([from, to, title]) => el('section', { class: 'stage-group', 'aria-label': title },
    el('div', { class: 'stage-group-heading', text: title }),
    ...STAGES.slice(from, to).map(([id, label], offset) => {
      const index = from + offset, visual = visuals[index];
      return el('button', { type: 'button', class: `stage-tab state-${visual.kind}${id === state.stage ? ' active' : ''}`, title: `${label}: ${visual.label}. ${visual.detail}`, 'aria-current': id === state.stage ? 'step' : null, 'data-testid': `stage-${id}`, 'data-stage-id': id, 'data-state': visual.kind, onclick: () => setStage(id) },
        el('span', { class: 'stage-icon-wrap' }, stageIcon(id)),
        el('span', { class: 'stage-tab-text' }, el('span', { class: 'stage-step-label' }, el('span', { class: 'stage-number', text: String(index + 1).padStart(2, '0') }), label), el('small', { class: 'stage-state-label' }, statusIcon(visual.kind), visual.label)),
        el('span', { class: 'stage-chevron', 'aria-hidden': 'true', text: id === state.stage ? '›' : '' }));
    }))));
  const completed = visuals.filter(visual => visual.kind === 'complete').length;
  byId('workflow-progress')?.replaceChildren(el('div', { class: 'workflow-progress-label' }, el('strong', { text: `${completed} / 14 stages complete` }), el('span', { text: 'Current execution' })), el('progress', { value: completed, max: 14, 'aria-label': `${completed} of 14 stages complete for current inputs` }));
  byId('stage-legend')?.replaceChildren(...[['pending', 'Not run'], ['working', 'Running'], ['complete', 'Complete'], ['attention', 'Review required'], ['error', 'Failed']].map(([kind, label]) => el('span', { class: `stage-legend-item state-${kind}` }, statusIcon(kind), label)));
}

function renderConnectionStatus() {
  connectionMonitor.receive();
  const llm = generation.llm;
  const visual = connectionVisualState({ probe: llm.probe, profileRevisionId: llm.profile_revision_id, profile: llm.profile,
    runtime: connectionMonitor.runtime, runtimeError: connectionMonitor.error,
    busy: generation.profileBusy || (connectionMonitor.pending && !connectionMonitor.checkedAt), readOnly: readOnly(), profileDirty: generation.profileDirty() });
  const detail = `${visual.detail}${llm.probe?.created_at ? ` Model-list test: ${new Date(llm.probe.created_at).toLocaleString()}.` : ''}${connectionMonitor.checkedAt ? ` Local server checked ${new Date(connectionMonitor.checkedAt).toLocaleTimeString()}.` : ''}`;
  const header = byId('llm-header-status');
  if (header) {
    header.className = `llm-header-status connection-${visual.kind}`; header.title = `${detail} Open LLM settings.`;
    header.setAttribute('aria-label', `LLM ${visual.label}. Open LLM settings`);
    byId('llm-header-icon')?.replaceChildren(statusIcon(visual.kind));
    if (byId('llm-header-text')) byId('llm-header-text').textContent = `LLM · ${visual.label}`;
    header.onclick = () => { setStage('global_settings'); byId('provider-model')?.focus({ preventScroll: false }); };
  }
  const footer = byId('llm-status-pill');
  if (footer) { footer.className = `llm-status-pill connection-${visual.kind}`; footer.title = detail; }
  const dot = byId('llm-connection-dot');
  if (dot) { dot.className = 'status-dot'; dot.replaceChildren(statusIcon(visual.kind)); }
  if (byId('llm-connection-state')) byId('llm-connection-state').textContent = `LLM · ${visual.label}`;
  const providerBadge = document.querySelector('[data-testid="provider-connection-badge"]');
  if (providerBadge) { providerBadge.className = `badge ${ {complete: 'success', working: 'info', attention: 'warning', error: 'error', blocked: 'neutral', pending: 'neutral'}[visual.kind] }`; providerBadge.replaceChildren(statusIcon(visual.kind), visual.label); providerBadge.title = detail; }
}

function renderReviewState() {
  const visual = stageVisual(state.stage);
  const tone = { complete: 'success', working: 'info', attention: 'warning', error: 'error', pending: 'neutral' }[visual.kind];
  byId('review-state')?.replaceChildren(el('span', { class: `badge ${tone}`, title: visual.detail }, statusIcon(visual.kind), visual.label));
}

function renderStageStatus() {
  const selectedNodeJob = state.stage === 'local_rtl_generation' ? generation.selectedJob() : null;
  const localGenerationStatus = selectedNodeJob && selectedNodeJob.node_id === generation.nodeId ? selectedNodeJob : null;
  const stage = state.stage === 'post_layout_verification' ? postlayoutFlow.selected() || workflowStage(state.stage) : state.stage === 'lvs' ? lvsFlow.selected() || workflowStage(state.stage) : state.stage === 'drc' ? drcFlow.selected() || workflowStage(state.stage) : state.stage === 'layout' ? physicalFlow.selected() || workflowStage(state.stage) : ['global_synthesis', 'global_netlist_simulation'].includes(state.stage) ? globalFlow.selected() || workflowStage(state.stage) : state.stage === 'global_rtl_generation' ? globalGeneration.selected() || workflowStage(state.stage) : state.stage === 'local_rtl_generation' ? localGenerationStatus : state.stage === 'node_implementation_specs' ? implementationSpecs.selected() : ['local_synthesis', 'local_netlist_simulation'].includes(state.stage) ? localFlow.selected() : workflowStage(state.stage);
  const earlierSource = !!stage && (['local_synthesis', 'local_netlist_simulation'].includes(state.stage) ? !localFlow.runCurrent(stage) : state.stage === 'node_implementation_specs' ? !implementationSpecs.runCurrent(stage) : false);
  const host = byId('stage-status');
  const visual = stageVisual(state.stage);
  const overlay = executionState.overlay(state.stage);
  const cancelledGuide = visual.label === 'Failed' && stage?.execution_status === 'Cancelled' && stage.validation_status === 'Not Checked' && !overlay?.reconnectRequired ? resolveStageGuidance(guidanceContext()) : null;
  const displayCancelled = cancelledGuide?.decisionId === 'cancelled' && cancelledGuide.tone === 'info';
  const displayLabel = displayCancelled ? 'Cancelled' : visual.label;
  const displayDetail = displayCancelled ? 'Cancelled. Inspect retained progress before explicitly starting another attempt.' : visual.detail;
  host.className = `stage-status execution-summary state-${visual.kind}`;
  host.setAttribute('data-status', visual.label);
  host.setAttribute('aria-live', 'polite');
  host.replaceChildren(
    el('div', { class: 'execution-primary', 'data-testid': 'stage-execution-status' },
      el('span', { class: 'execution-state-name' }, statusIcon(visual.kind), displayLabel),
      el('p', { class: 'execution-state-detail', text: displayDetail })),
    el('details', { class: 'execution-details', 'data-testid': 'stage-execution-details' },
      el('summary', { text: overlay?.invalidated && stageHasSavedEvidence(state.envelope, state.stage) ? 'Earlier saved evidence' : 'Execution details' }),
      el('div', { class: 'execution-evidence-grid' },
        statusItem(['local_synthesis','local_netlist_simulation'].includes(state.stage) ? 'SELECTED NODE · EXECUTION' : 'EXECUTION', stage?.execution_status || 'Not Run'),
        statusItem('VALIDATION', state.stage === 'local_rtl_generation' && stage ? generation.validationLabel(stage) : stage?.validation_status || 'Not Checked'),
        statusItem('ADOPTION', stage?.execution_status && stage.execution_status !== 'Not Run' ? stage?.review_status || 'Not requested' : 'Not requested'),
        statusItem('INPUT', stageInputDirty() ? 'Unsaved design inputs' : physicalDraftDirty() ? 'Unsaved physical constraints (S11+)' : dirty() ? 'Unsaved canvas view' : earlierSource ? 'Earlier source' : stage?.freshness || 'Current'))));
}

function statusItem(label, value) {
  const kind = ['Passed', 'Accepted', 'Current'].includes(value) ? 'complete' : ['Running', 'Queued'].includes(value) ? 'working' : value === 'Failed' ? 'error' : ['Stale', 'Earlier source', 'Unsaved edits', 'Unsaved design inputs', 'Review required', 'Verification required', 'Awaiting Review', 'Changes Requested'].includes(value) ? 'attention' : value === 'Unsupported' ? 'blocked' : 'pending';
  const tone = { complete: 'success', working: 'info', attention: 'warning', error: 'error', blocked: 'neutral', pending: 'neutral' }[kind];
  return el('div', { class: 'status-item' }, el('span', { class: 'eyebrow', text: label }), el('span', { class: `badge ${tone}` }, statusIcon(kind), value));
}

function render() {
  if (!state.design) return;
  flushActiveField();
  state.graph?.destroy(); state.graph = null;
  const [id, label, description] = currentStage();
  const index = STAGES.findIndex(stage => stage[0] === id);
  byId('stage-count').textContent = `${String(index + 1).padStart(2, '0')} / 14`;
  byId('breadcrumbs').textContent = `HuLLCirq / Design stages / ${String(index + 1).padStart(2, '0')}`;
  byId('stage-title').replaceChildren(el('span', { class: 'stage-title-icon' }, stageIcon(id)), document.createTextNode(label));
  byId('stage-title').tabIndex = -1;
  byId('stage-description').textContent = description;
  const host = byId('stage-content'); host.replaceChildren();
  if (compactSnapshot() && index >= 3 && savedSnapshotStages.get(snapshotStageKey(id))?.status !== 'ready') {
    for (const { module } of evidenceViews) { module.host = null; module.reviewHost = null; }
    loadSavedStage(id);
    const request = savedSnapshotStages.get(snapshotStageKey(id));
    snapshotLoading(host, `Loading ${label} from the saved snapshot…`, request?.error, () => { loadSavedStage(id, true); render(); });
    syncChrome(); renderReview(); applyReadOnly(); return;
  }
  if (id === 'global_settings') renderSettings(host);
  else if (id === 'graph_editor') renderGraph(host);
  else if (id === 'specifications') renderSpecifications(host);
  else if (id === 'local_rtl_generation') generation.render(host);
  else if (['local_synthesis', 'local_netlist_simulation'].includes(id) && workflowStage(id)?.implemented) localFlow.render(host);
  else if (id === 'node_implementation_specs' && workflowStage(id)?.implemented) implementationSpecs.render(host);
  else if (id === 'global_rtl_generation') globalGeneration.render(host);
  else if (['global_synthesis', 'global_netlist_simulation'].includes(id) && workflowStage(id)?.implemented) globalFlow.render(host);
  else if (id === 'layout' && workflowStage(id)?.implemented) physicalFlow.render(host);
  else if (id === 'drc' && workflowStage(id)?.implemented) drcFlow.render(host);
  else if (id === 'lvs' && workflowStage(id)?.implemented) lvsFlow.render(host);
  else if (id === 'post_layout_verification' && workflowStage(id)?.implemented) postlayoutFlow.render(host);
  else renderFuture(host);
  syncChrome(); renderReview(); applyReadOnly(); renderNextStep();
}

function flushActiveField() {
  if (state.flushingField) return;
  const active = document.activeElement;
  if (active && ['INPUT', 'SELECT', 'TEXTAREA'].includes(active.tagName) && !['review-note', 'node-search', 'import-file'].includes(active.id)) {
    state.flushingField = true;
    try { active.dispatchEvent(new Event('change', { bubbles: true })); }
    finally { state.flushingField = false; }
  }
}

function section(title, description, children, className = '') {
  return el('section', { class: `card ${className}` }, el('div', { class: 'card-heading' }, el('h2', { text: title }), description ? el('p', { text: description }) : null), children);
}

function renderSettings(host) {
  const settings = state.design.settings;
  const postlayout = state.envelope.postlayout_workflow?.implemented ? {
    label: postlayoutFlow.postRoute?.() ? 'Layout, DRC, LVS & functional + STA verification API' : postlayoutFlow.eventDiagnostic() ? 'Layout, DRC, LVS & saved S14 event diagnostic API' : postlayoutFlow.diagnostic() ? 'Layout, DRC, LVS & saved S14 diagnostic API' : postlayoutFlow.preflight() ? 'Layout, DRC, LVS & S14 readiness API' : 'Layout, DRC, LVS & post-layout workflow API',
    description: postlayoutFlow.postRoute?.() ? 'S14 runs the original GUI job on the adopted routed netlist and checks timing separately with extracted parasitics and declared constraints. Inspect functional, setup/hold and electrical results, completion requirements and raw reports in Post-layout Verification. SDF delay simulation is outside this method. Adoption requires the recorded mandatory checks to pass.' : postlayoutFlow.eventDiagnostic() ? 'S14 can validate the retained event-recorded timed diagnostic against the original GUI job and exact adopted S11/S12/S13 inputs. This action starts no new simulator. Inspect the saved event, conditional-path, native-delay and functional provenance reports in Post-layout Verification for their exact results and finite observation limits. Dynamic S14 verification is not implemented by this adapter; this diagnostic cannot complete S14.' : postlayoutFlow.diagnostic() ? 'S14 can validate the retained timed diagnostic against the original GUI job and exact adopted S11/S12/S13 inputs. This action starts no new simulator. The original timed run matched all 16 expected outputs, but conditional SDF path binding and event-timing qualification remain unsupported. Inspect the reports in Post-layout Verification; This adapter does not implement qualified dynamic S14 verification, so this diagnostic cannot complete S14.' : postlayoutFlow.preflight() ? 'S14 workflow and readiness checks are implemented. Qualified dynamic post-layout simulation remains unsupported. The current readiness profile freezes the original GUI job and exact adopted S11/S12/S13 inputs without starting a simulator or permitting S14 adoption. Inspect the saved checks and compatibility barriers in Post-layout Verification.' : 'Trusted tools expose the post-layout workflow with exact adopted S11/S12/S13 inputs, recorded timing scope and independent history. Implementation, runtime availability and actual dynamic results are reported separately in Post-layout Verification.',
  } : null;
  const updateSetting = (key, value) => mutate(design => { design.settings[key] = value; }, false);
  const form = el('div', { class: 'settings-grid' },
    section(workspaceEnabled ? 'System design & RTL' : 'Project & RTL', workspaceEnabled ? 'Set this system’s design label and RTL contract. Manage project and system names from Projects.' : 'Shared names and the initial supported RTL contract.', el('div', { class: 'form-grid' },
      field(workspaceEnabled ? 'Design display name' : 'Project name', state.design.project.name, value => mutate(design => { design.project.name = value; }, false), { id: 'project-name', 'data-testid': 'project-name' }),
      field('Top module', settings.top_module, value => updateSetting('top_module', value), { id: 'top-module', 'data-testid': 'top-module', spellcheck: false }),
      field('RTL language', settings.rtl_language, value => updateSetting('rtl_language', value), { id: 'rtl-language', choices: [['verilog_2005', 'Verilog-2005']] }))),
    section('Clock & reset', 'M1 supports a single clock and synchronous reset.', el('div', { class: 'form-grid' },
      field('Clock name', settings.clock_name, value => updateSetting('clock_name', value), { id: 'clock-name', 'data-testid': 'clock-name', spellcheck: false }),
      field('Clock period (ns)', settings.clock_period_ns, value => updateSetting('clock_period_ns', Number(value)), { id: 'clock-period', type: 'number', step: 'any', 'data-testid': 'clock-period' }),
      field('Reset name', settings.reset_name, value => updateSetting('reset_name', value), { id: 'reset-name', 'data-testid': 'reset-name', spellcheck: false }),
      field('Reset active level', settings.reset_active, value => updateSetting('reset_active', value), { id: 'reset-active', choices: [['high', 'Active high'], ['low', 'Active low']] }),
      field('Reset kind', settings.reset_kind, value => updateSetting('reset_kind', value), { id: 'reset-kind', choices: [['synchronous', 'Synchronous']] }))),
    section('Technology target', 'These selections are design inputs; no PDK or EDA installation is verified here.', el('div', { class: 'form-grid' },
      field('PDK', settings.pdk, value => updateSetting('pdk', value), { id: 'pdk', 'data-testid': 'pdk', choices: [['sky130A', 'SKY130A']] }),
      field('Cell library', settings.cell_library, value => updateSetting('cell_library', value), { id: 'cell-library', choices: [['sky130_fd_sc_hd', 'sky130_fd_sc_hd']] }))),
    section('EDA environment', 'Model requests and circuit tools have separate execution boundaries.', el('div', { class: 'connection-cards' },
      el('div', { 'data-testid': 'eda-settings-environment' }, el('strong', { text: 'EDA environment' }), badge(postlayout?.label || (state.envelope.lvs_workflow?.implemented ? 'Node, whole-design, layout, DRC & LVS API' : state.envelope.drc_workflow?.implemented ? 'Node, whole-design, layout & DRC API' : state.envelope.physical_workflow?.implemented ? 'Node, whole-design & physical execution API' : state.envelope.global_workflow?.implemented ? 'Node & whole-design execution API' : state.envelope.workflow?.some(stage => stage.id === 'local_synthesis' && stage.implemented) ? 'Node execution API' : 'Not configured')), el('p', { text: postlayout?.description || (state.envelope.lvs_workflow?.implemented ? 'Trusted tools retain adopted RTL, generic verification, SKY130 layout and DRC evidence. S13 extracts the exact accepted GDS and compares it against its corresponding mapped circuit with recorded PDK rules, full reports and separate adoption. S14 dynamic post-layout verification remains unimplemented.' : state.envelope.drc_workflow?.implemented ? 'Trusted tools execute adopted RTL, generic netlist checks and recorded SKY130 layout. S12 uses the exact adopted S11 GDS and pinned PDK rule decks, with its own commands, reports, checks and adoption. S13 LVS and S14 dynamic post-layout verification remain separate, unimplemented stages.' : state.envelope.physical_workflow?.implemented ? 'Trusted tools execute adopted RTL and netlist checks. S11 separately maps the same accepted source modules using a recorded LibreLane / SKY130 physical profile and exposes its actual steps, metrics and layout artifacts. S12 DRC, S13 LVS and S14 dynamic post-layout verification remain separate, unimplemented stages.' : state.envelope.global_workflow?.implemented ? 'Configured trusted tools execute adopted node RTL and complete-design generic synthesis and netlist checks. Each run records its actual availability, commands, logs and verification scope. Generic synthesis does not map to SKY130; layout, DRC, LVS and post-layout verification remain unavailable.' : state.envelope.workflow?.some(stage => stage.id === 'local_synthesis' && stage.implemented) ? 'Configured trusted tools execute node RTL and generic netlist checks. Runtime availability and failures are recorded in each actual run. Generic synthesis does not map to SKY130; layout, DRC, LVS and post-layout verification remain unavailable.' : 'Input checks run in the local service. Later tool availability and executed evidence are shown separately by stage.') })))));
  const provider = el('div', { id: 'provider-settings-host' });
  const policy = el('div', { id: 'adoption-policy-host' });
  host.append(form, policy, provider, conceptCard());
  adoption.render(policy);
  generation.renderProvider(provider);
}

function conceptCard() {
  const details = el('details', { class: 'concept-card' }, el('summary', { text: 'About this workspace · HuLLCirq concept' }),
    el('div', { class: 'concept-content' }, el('p', { text: 'Human specification -> local-LLM proposal -> independent verification -> reviewed evidence.' }),
      el('p', { text: 'This submission uses text branding. Separate concept artwork is excluded; retained circuit results remain actual execution evidence.' }),
      el('p', { text: 'Human decisions connect each design stage. Input editing, saved revisions, scoped model requests, and candidate reviews remain distinct from later circuit and physical verification.' })));
  return details;
}

function renderGraph(host) {
  const hierarchy = el('aside', { class: 'hierarchy card' }, el('div', { class: 'card-heading' }, el('h2', { text: 'Hierarchy' }), el('p', { text: 'Stable IDs preserve connections when names change.' })),
    el('input', { type: 'search', placeholder: 'Find a node…', 'aria-label': 'Find a node', id: 'node-search', oninput: () => renderHierarchy() }), el('div', { id: 'hierarchy-tree', class: 'hierarchy-tree' }));
  const canvas = el('section', { class: 'graph-card card', 'aria-label': 'Graph editor' });
  const inspector = el('aside', { class: 'inspector card', id: 'inspector', 'aria-label': 'Selection inspector', 'data-testid': 'selection-inspector' });
  host.append(el('div', { class: 'graph-workspace' }, hierarchy, canvas, inspector));
  state.graph = new GraphEditor(canvas, {
    select, addNode, duplicateSelection, deleteSelection, addEdge, enableExternalIO, addExternalBinding,
    previewLayout: layout => { if (readOnly()) return; state.design.layout = layout; state.graph.update(state.design, state.selected); syncChrome(); },
    commitLayout: initial => {
      const after = clone(state.design.layout);
      state.design.layout = initial;
      mutate(design => { design.layout = after; }, false);
    },
    setLayout: layout => mutate(design => { design.layout = layout; }, false),
  });
  state.graph.update(state.design, state.selected); renderHierarchy(); renderInspector();
}

function renderHierarchy() {
  const host = byId('hierarchy-tree');
  if (!host || !state.design) return;
  const query = byId('node-search')?.value.trim().toLowerCase() || '';
  const nodes = state.design.nodes;
  const visited = new Set();
  const items = [];
  if (hasExternalIO(state.design)) {
    for (const direction of ['input', 'output']) items.push(el('button', { type: 'button', class: `tree-node external-tree-node${state.selected?.kind === 'external' && state.selected.direction === direction ? ' selected' : ''}`, 'data-testid': `tree-external-${direction}`, onclick: () => select({ kind: 'external', direction }) },
      el('span', { class: 'tree-icon', text: direction === 'input' ? '→' : '←' }), el('span', {}, el('strong', { text: direction === 'input' ? 'External inputs' : 'External outputs' }), el('small', { text: `${externalPorts(state.design, direction).length} terminals · top interface` }))));
  }
  function add(node, depth) {
    if (visited.has(node.id)) return;
    visited.add(node.id);
    if (!query || `${node.name} ${node.module_name}`.toLowerCase().includes(query)) {
      items.push(el('button', { type: 'button', class: `tree-node${state.selected?.kind === 'node' && (state.selected.ids || [state.selected.id]).includes(node.id) ? ' selected' : ''}`, style: `padding-left: ${12 + Math.min(depth, 5) * 12}px`, 'data-testid': `tree-${node.id}`, onclick: () => select({ kind: 'node', id: node.id }) },
      el('span', { class: 'tree-icon', text: '◇' }), el('span', {}, el('strong', { text: node.name }), el('small', { text: node.module_name + (arrayShape(node) ? ` · ${node.instance_array.rows} × ${node.instance_array.columns} array` : '') }))));
    }
    for (const child of nodes.filter(item => item.parent_id === node.id)) add(child, depth + 1);
  }
  for (const node of nodes.filter(item => !item.parent_id || !nodes.some(parent => parent.id === item.parent_id))) add(node, 0);
  // Invalid cycles remain visible so the user can repair them after validation.
  for (const node of nodes) if (!visited.has(node.id)) add(node, 0);
  host.replaceChildren(...(items.length ? items : [el('p', { class: 'empty-small', text: query ? 'No matching nodes.' : 'Add a node to begin.' })]));
}

function renderInspector() {
  const host = byId('inspector');
  if (!host) return;
  host.replaceChildren();
  if (state.selected?.kind === 'external') {
    renderExternalInspector(host, state.design, state.selected, {
      addPort: addExternalPort, addBinding: addExternalBinding, deletePort: deleteExternalPort, removeBinding: removeExternalBinding,
      changePort: (id, key, value) => mutate(design => { design.external_io.ports.find(port => port.id === id)[key] = value; }, false),
      message: message => notify(message, 'error'),
    });
    host.append(connectionBuilder()); return;
  }
  if (state.selected?.kind === 'external_binding') {
    const binding = state.design.external_io?.connections.find(item => item.id === state.selected.id);
    if (binding) host.append(el('div', { class: 'card-heading' }, el('span', { class: 'eyebrow', text: 'EXTERNAL CONNECTION' }), el('h2', { text: 'Top boundary binding' }), el('p', { text: externalBindingLabel(state.design, binding) })),
      el('p', { class: 'scope-note', text: 'This explicit binding is part of saved graph validation and RTL integration. Removing it changes only the browser draft until Save design.' }),
      el('button', { type: 'button', class: 'danger', text: 'Remove external connection', onclick: () => removeExternalBinding(binding.id) }));
    host.append(connectionBuilder()); return;
  }
  const node = selectedNode();
  if (node) {
    host.append(el('div', { class: 'card-heading' }, el('span', { class: 'eyebrow', text: 'NODE INSPECTOR' }), el('h2', { text: node.name }), el('p', { class: 'stable-id', text: node.id })), nodeFields(node));
    if (node.component_ref) host.append(el('div', { class: 'inspector-section component-provenance' }, el('h3', { text: 'Pinned component source' }), badge(`Version ${node.component_ref.version}`, 'neutral'),
        el('p', {}, el('code', { text: node.component_ref.component_id }), el('br'), el('small', { text: `Instance: ${node.component_ref.instance_id} · Original node: ${node.component_ref.source_node_id}` })),
        el('p', { text: 'Copied intent and interface provenance. Target integration has not inherited source acceptance.' })));
    host.append(el('div', { class: 'inspector-section' }, el('h3', { text: 'Ports' }), ...node.ports.map(port => portFields(node, port)),
        el('button', { type: 'button', text: '+ Add port', 'data-testid': 'add-port', onclick: () => mutate(design => { design.nodes.find(item => item.id === node.id).ports.push(makePort('input', `data_${node.ports.length}`)); }) })),
      el('details', { class: 'inspector-section' }, el('summary', { text: 'Behavior & test expectations' }), specificationFields(node)),
      el('div', { class: 'inspector-actions' }, el('button', { type: 'button', text: 'Duplicate node', onclick: duplicateSelection }), el('button', { type: 'button', class: 'danger', text: 'Delete node', onclick: deleteSelection })));
    if (state.selected?.portId) host.querySelector(`[data-port-fields="${CSS.escape(state.selected.portId)}"]`)?.classList.add('focused-port');
  } else if (state.selected?.kind === 'edge') {
    const edge = state.design.edges.find(item => item.id === state.selected.id);
    if (edge) host.append(el('div', { class: 'card-heading' }, el('span', { class: 'eyebrow', text: 'EDGE INSPECTOR' }), el('h2', { text: 'Data transfer' }), el('p', { class: 'stable-id', text: edge.id })), edgeFields(edge),
      el('button', { type: 'button', class: 'danger', text: 'Delete connection', 'data-testid': 'delete-edge', onclick: deleteSelection }));
  } else host.append(el('div', { class: 'inspector-empty' }, el('span', { class: 'large-symbol', text: '◇' }), el('h2', { text: 'Select a node or edge' }), el('p', { text: 'Edit its ports, hierarchy, and design intent here. Inputs are checked after saving.' })));
  host.append(connectionBuilder());
}

function nodeFields(node) {
  const change = (key, value) => mutate(design => { design.nodes.find(item => item.id === node.id)[key] = value; }, false);
  return el('div', { class: 'inspector-section form-grid single' },
    field('Node name', node.name, value => change('name', value), { id: 'node-name', 'data-testid': 'node-name' }),
    field('Module name', node.module_name, value => change('module_name', value), { id: 'module-name', 'data-testid': 'module-name', spellcheck: false }),
    field('Parent node', node.parent_id || '', value => change('parent_id', value || null), { id: 'parent-node', 'data-testid': 'parent-node', choices: [['', 'Top level'], ...state.design.nodes.filter(item => item.id !== node.id).map(item => [item.id, item.name])], hint: 'Hierarchy cycles are diagnosed by graph verification.' }),
    arrayFields(node));
}

function arrayFields(node) {
  let rows = node.instance_array?.rows || 2, columns = node.instance_array?.columns || 2;
  let mode = node.instance_array ? 'array' : 'scalar';
  const message = el('p', { class: 'scope-note', role: 'status', 'data-testid': 'array-shape-message' });
  return el('section', { class: 'instance-array-fields' }, el('h3', { text: 'Instance array' }),
    field('Definition mode', mode, value => { mode = value; }, { id: `array-mode-${node.id}`, 'data-testid': 'array-mode', choices: [['scalar', 'Single instance'], ['array', 'Shared definition · 2D instance array']] }),
    el('div', { class: 'form-grid' },
      field('Array rows', rows, value => { rows = Number(value); }, { type: 'number', min: 1, max: 16, step: 1, id: `array-rows-${node.id}`, 'data-testid': 'array-rows' }),
      field('Array columns', columns, value => { columns = Number(value); }, { type: 'number', min: 1, max: 16, step: 1, id: `array-columns-${node.id}`, 'data-testid': 'array-columns' })),
    el('p', { class: 'scope-note', 'data-testid': 'array-profile-help', text: 'One scalar port definition is shared by all indexed instances. ' + (state.design.global_verification?.kind === 'generic_cycle_vectors' ? 'The selected generic cycle-vector profile expands the saved 1–16 row/column shape; declare indexed member connections and independent system expectations.' : 'The historical NPU profile is limited to a 2 × 2 PE array. For other arrays, configure the generic cycle-vector system contract in Specifications; shapes can use 1–16 rows and columns with explicit indexed member connections.') + ' Apply only changes the browser draft; Save design records it. Existing connections are not silently converted or deleted. Array shape alone establishes no verification result.' }),
    el('button', { type: 'button', text: 'Apply instance shape to draft', 'data-testid': 'apply-instance-array', onclick: () => {
      const next = mode === 'array' ? { rows, columns } : null;
      const problem = arrayResizeProblem(state.design, node.id, next) || externalArrayResizeProblem(state.design, node.id, next);
      if (problem) { message.textContent = problem; return; }
      mutate(design => {
        const target = design.nodes.find(item => item.id === node.id);
        if (next) target.instance_array = next; else delete target.instance_array;
      });
    } }), message);
}

function makePort(direction, name) {
  return { id: newId('port'), name, direction, width: 32, signed: true, protocol: 'valid_ready', clock: state.design.settings.clock_name, reset: state.design.settings.reset_name };
}

function portFields(node, port) {
  const change = (key, value) => mutate(design => { design.nodes.find(item => item.id === node.id).ports.find(item => item.id === port.id)[key] = value; }, false);
  const changeSideband = (key, value) => mutate(design => {
    const target = design.nodes.find(item => item.id === node.id).ports.find(item => item.id === port.id);
    target.sideband = { ...target.sideband, [key]: value };
  }, false);
  const changeProtocol = value => {
    mutate(design => {
      const target = design.nodes.find(item => item.id === node.id).ports.find(item => item.id === port.id);
      target.protocol = value;
      if (value === 'raw' && !target.sideband) target.sideband = { kind: 'metadata', associated_port_id: node.ports.find(item => item.id !== port.id && item.protocol === 'valid_ready' && item.direction === port.direction)?.id ?? null };
    }, false);
    renderInspector();
  };
  const associations = [['', 'Independent pulse (no associated stream)'], ...node.ports.filter(item => item.id !== port.id && item.protocol === 'valid_ready').map(item => [item.id, `${item.name} · ${item.direction}`])];
  if (port.sideband?.associated_port_id && !associations.some(([id]) => id === port.sideband.associated_port_id)) associations.push([port.sideband.associated_port_id, `Missing stream (${port.sideband.associated_port_id})`]);
  return el('div', { class: 'port-fields', 'data-port-fields': port.id },
    el('div', { class: 'port-heading' }, badge(port.direction, port.direction === 'input' ? 'teal' : 'orange'), el('code', { text: port.id }), el('button', { type: 'button', class: 'icon-button danger', 'aria-label': `Delete port ${port.name}`, text: '×', onclick: () => {
      const edges = state.design.edges.filter(edge => edge.source.port_id === port.id || edge.target.port_id === port.id);
      if (edges.length && !confirm(`Delete ${port.name} and its ${edges.length} connected edge(s)?`)) return;
      mutate(design => { design.nodes.find(item => item.id === node.id).ports = node.ports.filter(item => item.id !== port.id); design.edges = design.edges.filter(edge => edge.source.port_id !== port.id && edge.target.port_id !== port.id); });
    } })),
    el('div', { class: 'form-grid' },
      field('Port name', port.name, value => change('name', value), { id: `port-name-${port.id}`, 'data-testid': `port-name-${port.id}`, spellcheck: false }),
      field('Direction', port.direction, value => { change('direction', value); renderInspector(); }, { id: `port-direction-${port.id}`, 'data-testid': `port-direction-${port.id}`, choices: ['input', 'output'] }),
      field('Width (bits)', port.width, value => change('width', Number(value)), { id: `port-width-${port.id}`, type: 'number', step: '1', 'data-testid': `port-width-${port.id}` }),
      field('Signedness', String(port.signed), value => change('signed', value === 'true'), { id: `port-signed-${port.id}`, choices: [['true', 'Signed'], ['false', 'Unsigned']] }),
      field('Protocol', port.protocol, changeProtocol, { id: `port-protocol-${port.id}`, 'data-testid': `port-protocol-${port.id}`, choices: [['valid_ready', 'valid / ready stream'], ['raw', 'Raw public control / sideband']] }),
      field('Clock', port.clock, value => change('clock', value), { id: `port-clock-${port.id}`, spellcheck: false }),
      field('Reset', port.reset, value => change('reset', value), { id: `port-reset-${port.id}`, spellcheck: false }),
      ...(port.protocol === 'raw' ? [
        field('Sideband kind', port.sideband?.kind, value => changeSideband('kind', value), { id: `port-sideband-kind-${port.id}`, 'data-testid': `port-sideband-kind-${port.id}`, choices: [['metadata', 'Stream metadata'], ['pulse', 'One-bit control pulse'], ['level', 'One-bit control level']] }),
        field('Associated stream', port.sideband?.associated_port_id ?? '', value => changeSideband('associated_port_id', value || null), { id: `port-sideband-association-${port.id}`, 'data-testid': `port-sideband-association-${port.id}`, choices: associations, hint: 'Metadata requires a same-node valid / ready stream with matching direction, clock and reset. Independent pulses or levels explicitly use no stream.' }),
        field('Sideband meaning', port.sideband?.meaning ?? '', value => changeSideband('meaning', value), { id: `port-sideband-meaning-${port.id}`, 'data-testid': `port-sideband-meaning-${port.id}`, multiline: true, hint: 'One exact physical signal; no implicit valid / ready. Imported extra sideband fields are preserved.' }),
      ] : [])));
}

function specificationFields(node, prefix = '') {
  const update = (key, value) => mutate(design => { design.nodes.find(item => item.id === node.id)[key] = value; }, false);
  return el('div', { class: 'form-grid single' },
    field('Required behavior', node.behavior, value => update('behavior', value), { id: `${prefix}node-behavior-${node.id}`, multiline: true, 'data-testid': `node-behavior-${node.id}`, placeholder: 'Describe numerical behavior, reset, ordering, and stall handling.' }),
    field('Test expectations', node.test_expectations, value => update('test_expectations', value), { id: `${prefix}node-tests-${node.id}`, multiline: true, 'data-testid': `node-tests-${node.id}`, placeholder: 'State independent expected values and boundary cases.' }),
    field('Latency (cycles)', node.constraints.latency_cycles, value => mutate(design => { design.nodes.find(item => item.id === node.id).constraints.latency_cycles = Number(value); }, false), { id: `${prefix}node-latency-${node.id}`, type: 'number', step: '1', 'data-testid': `node-latency-${node.id}` }),
    field('Node protocol', node.constraints.protocol, value => mutate(design => { design.nodes.find(item => item.id === node.id).constraints.protocol = value; }, false), { id: `${prefix}node-protocol-${node.id}`, choices: [['valid_ready', 'valid / ready']] }),
    verificationFields(node, prefix));
}

function verificationFields(node, prefix) {
  const readiness = state.envelope.generation?.nodes?.find(item => item.node_id === node.id)?.behavioral_verification;
  const id = `verification-json-${node.id}`;
  const editor = structuredInput({ key: node.id, id: `${prefix}${id}`, testId: id, title: 'Node cycle vectors / structured verification JSON', value: node.verification, drafts: state.verificationDrafts,
    parse: text => parseCycleInput(text, nodePhysicalPorts(state.design.nodes.find(item => item.id === node.id)), { allowLegacy: true }),
    apply: value => mutate(design => { const target = design.nodes.find(item => item.id === node.id); if (value) target.verification = value; else delete target.verification; }, false),
    changed: verificationTextChanged, gate: verificationEditGate, template: () => cycleTemplate(nodePhysicalPorts(state.design.nodes.find(item => item.id === node.id))),
    hint: 'Generic cycle vectors v1: independent expected values for EVERY physical output and drive values for EVERY non-clock/reset physical input, including stream valid/ready pins. First reset=1, then reset=0 with changed inputs. Reset means logical assertion and inherits polarity. Values are exact integers; quote wide decimal integers. Null template values must be filled. Apply changes the browser design draft only; Save freezes it for S06. Existing saved checker contracts remain supported.' });
  editor.append(el('p', { class: 'scope-note', text: readiness?.message || 'Finite saved-cycle checks are not formal proof or exhaustive protocol coverage. Expected values are supplied independently, never derived from generated RTL.' }));
  return editor;
}

function verificationTextChanged() { autosave(); syncChrome(); renderReview(); }
function verificationEditGate() {
  if (readOnly()) return 'This saved snapshot is read-only.';
  if (state.externalRevision) return 'A newer saved design was detected; preserve this browser draft before reconnecting.';
  if (state.busy || generation.requestBusy || generationBatches.busy || localFlow.busy || globalGeneration.busy || globalFlow.busy || physicalFlow.busy || drcFlow.busy || lvsFlow.busy || postlayoutFlow.busy) return 'Wait for the current project operation to finish.';
  const records = [...(state.envelope.generation?.jobs || []), ...(state.envelope.workflow_runs || []), ...(state.envelope.global_generation?.jobs || []), ...['global_workflow', 'physical_workflow', 'drc_workflow', 'lvs_workflow', 'postlayout_workflow'].flatMap(key => state.envelope[key]?.runs || [])];
  return records.some(record => ['Queued', 'Running'].includes(record.execution_status)) ? 'Inspect or cancel the active execution before applying verification inputs.' : '';
}

function systemVerificationFields() {
  const integration = structuredInput({ key: SYSTEM_DRAFT_KEYS[0], id: 'system-integration-json', title: 'Top public interface and integration behavior JSON', value: state.design.global_integration, drafts: state.verificationDrafts,
    parse: text => parseIntegrationInput(text, state.design.settings),
    apply: value => mutate(design => { if (value) design.global_integration = value; else delete design.global_integration; }, false), changed: verificationTextChanged, gate: verificationEditGate,
    template: () => ({ public_ports: hasExternalIO(state.design) ? expandedExternalPorts(state.design) : [{ name: 'input_data', direction: 'input', width: 8, signed: false }, { name: 'output_data', direction: 'output', width: 8, signed: false }], behavior: state.design.global_integration?.behavior || '' }),
    hint: 'Declare flat physical top pins as {name,direction,width,signed}, including any valid/ready controls. Clock/reset are automatic from Global Settings and must not appear here. Describe exact top connections, reset and behavior. This unfilled example is not a verified design. Apply the interface before editing its cycle vectors.' });
  const cycles = structuredInput({ key: SYSTEM_DRAFT_KEYS[1], id: 'system-verification-json', title: 'System cycle-vector verification JSON', value: state.design.global_verification, drafts: state.verificationDrafts,
    parse: text => parseCycleInput(text, state.design.global_integration?.public_ports || []),
    apply: value => mutate(design => { if (value) design.global_verification = value; else delete design.global_verification; }, false), changed: verificationTextChanged, gate: verificationEditGate,
    template: () => cycleTemplate(state.design.global_integration?.public_ports || []),
    hint: 'Generic S08–S10/S14 uses these SAME independent saved-cycle expectations. Every physical top input except clock/reset and every output must be present every cycle. First assert reset (logical 1), then exercise changed inputs with reset=0. Use quoted decimal strings for values outside the safe JSON integer range. A backend source check determines readiness; entering vectors does not create a pass.' });
  const boundary = hasExternalIO(state.design) ? el('div', { class: 'scope-note external-integration-note' }, el('p', { text: 'External I/O blocks define the top physical pins and exact node bindings. The interface template uses those pins. Changing a terminal never silently changes saved expectations or this declaration.' }),
    el('button', { type: 'button', text: 'Apply external I/O ports to top declaration', onclick: () => {
      if (verificationEditGate()) return notify(verificationEditGate(), 'error');
      if (state.verificationDrafts[SYSTEM_DRAFT_KEYS[0]]) return notify('Apply or discard the existing top-interface text draft first.', 'error');
      mutate(design => { design.global_integration = { ...(design.global_integration || {}), public_ports: expandedExternalPorts(design), behavior: design.global_integration?.behavior || '' }; });
    } })) : null;
  return section('Whole-system integration and verification', 'Choose the generic finite-cycle profile by explicitly applying generic_cycle_vectors v1 below. Leaving this contract absent preserves an existing supported project-specific profile; it does not select an NPU template. Typing and viewing never save or execute.', [boundary, integration, cycles]);
}

function endpointChoices(direction, includeExternal = false) {
  return [...endpointsFor(state.design, direction), ...(includeExternal ? externalEndpointChoices(state.design, direction) : [])];
}

function edgeFields(edge, prefix = '') {
  const update = (key, value) => mutate(design => { design.edges.find(item => item.id === edge.id)[key] = value; }, false);
  return el('div', { class: 'form-grid single inspector-section' },
    field('Source output', endpointValue(edge.source.node_id, edge.source.port_id, edge.source.instance_index), value => update('source', parseEndpoint(value)), { id: `${prefix}edge-source-${edge.id}`, choices: endpointChoices('output'), 'data-testid': `edge-source-${edge.id}` }),
    field('Target input', endpointValue(edge.target.node_id, edge.target.port_id, edge.target.instance_index), value => update('target', parseEndpoint(value)), { id: `${prefix}edge-target-${edge.id}`, choices: endpointChoices('input'), 'data-testid': `edge-target-${edge.id}` }),
    field('Transfer behavior', edge.behavior, value => update('behavior', value), { id: `${prefix}edge-behavior-${edge.id}`, multiline: true, 'data-testid': `edge-behavior-${edge.id}`, placeholder: 'Describe valid / ready, ordering, and backpressure.' }),
    field('Edge protocol', edge.protocol, value => update('protocol', value), { id: `${prefix}edge-protocol-${edge.id}`, choices: [['valid_ready', 'valid / ready'], ['raw', 'Raw control / sideband']] }));
}

function connectionBuilder() {
  const outputs = endpointChoices('output', true), inputs = endpointChoices('input', true);
  let sourceValue = outputs[0]?.[0] || '', targetValue = inputs[0]?.[0] || '';
  return el('section', { class: 'inspector-section connection-builder' }, el('h3', { text: 'New connection' }),
    field('From output', sourceValue, value => { sourceValue = value; }, { id: 'new-edge-source', 'data-testid': 'new-edge-source', choices: outputs, disabled: !outputs.length }),
    field('To input', targetValue, value => { targetValue = value; }, { id: 'new-edge-target', 'data-testid': 'new-edge-target', choices: inputs, disabled: !inputs.length }),
    el('button', { type: 'button', text: '+ Connect ports', 'data-testid': 'add-edge', disabled: !outputs.length || !inputs.length, onclick: () => addEdge(parseGraphEndpoint(byId('new-edge-source')?.value || sourceValue), parseGraphEndpoint(byId('new-edge-target')?.value || targetValue)) }),
    el('small', { text: 'You can also select an output port, then an input port on the canvas.' }));
}

function refreshConnectionChoices() {
  const source = byId('new-edge-source'), target = byId('new-edge-target');
  if (!source || !target) return;
  const choices = { output: endpointChoices('output', true), input: endpointChoices('input', true) };
  for (const [control, direction] of [[source, 'output'], [target, 'input']]) {
    const options = choices[direction], previous = control.value;
    const existing = Array.from(control.options || control.children);
    if (!equal(existing.map(option => [option.value, option.textContent]), options)) {
      const retained = new Map(existing.map(option => [option.value, option]));
      control.replaceChildren(...options.map(([value, text]) => {
        const option = retained.get(value) || el('option', { value });
        if (option.textContent !== text) option.textContent = text;
        return option;
      }));
    }
    const next = options.some(([value]) => value === previous) ? previous : options[0]?.[0] || '';
    if (control.value !== next) control.value = next;
    control.disabled = !options.length;
  }
  const connect = document.querySelector('[data-testid="add-edge"]');
  if (connect) connect.disabled = !choices.output.length || !choices.input.length;
}

function setNodePosition(layout, id, at) {
  Object.defineProperty(layout.nodes, id, { value: at, enumerable: true, configurable: true, writable: true });
}

function enableExternalIO() {
  if (hasExternalIO(state.design)) return;
  state.selected = { kind: 'external', direction: 'input' };
  mutate(design => { design.external_io = blankExternalIO(); });
  state.graph?.fit();
}

function addExternalPort(direction) {
  let count = 1, name = direction === 'input' ? 'input_data' : 'output_data';
  const taken = new Set(externalPorts(state.design).map(port => port.name));
  while (taken.has(name)) name = `${direction === 'input' ? 'input' : 'output'}_data_${count++}`;
  state.selected = { kind: 'external', direction };
  mutate(design => { design.external_io.ports.push({ id: newId('external'), name, direction, width: 8, signed: false, protocol: 'valid_ready' }); });
}

function deleteExternalPort(id) {
  const port = externalPorts(state.design).find(item => item.id === id);
  const count = state.design.external_io.connections.filter(item => item.external_port_id === id).length;
  if (!port || !confirm(`Delete external port ${port.name} and its ${count} explicit connection(s)? Undo can restore this draft edit. Saved expectations and top declarations are not changed automatically.`)) return;
  mutate(design => {
    design.external_io.ports = design.external_io.ports.filter(item => item.id !== id);
    design.external_io.connections = design.external_io.connections.filter(item => item.external_port_id !== id);
  });
}

function addExternalBinding(externalId, endpoint) {
  const problem = externalConnectionProblem(state.design, externalId, endpoint);
  if (problem) return notify(problem, 'error');
  const id = newId('external_connection');
  state.selected = { kind: 'external_binding', id };
  mutate(design => { design.external_io.connections.push({ id, external_port_id: externalId, ...endpoint }); });
}

function removeExternalBinding(id) {
  const binding = state.design.external_io?.connections.find(item => item.id === id);
  if (!binding) return;
  const port = externalPorts(state.design).find(item => item.id === binding.external_port_id);
  state.selected = { kind: 'external', direction: port?.direction || 'input' };
  mutate(design => { design.external_io.connections = design.external_io.connections.filter(item => item.id !== id); });
}

function addNode() {
  let count = state.design.nodes.length + 1;
  while (state.design.nodes.some(node => node.module_name === `block_${count}`)) count++;
  const id = newId('node');
  const node = { id, name: `Block ${count}`, module_name: `block_${count}`, parent_id: null, behavior: '', test_expectations: '', constraints: { latency_cycles: 1, protocol: 'valid_ready' }, ports: [makePort('input', 'data_in'), makePort('output', 'data_out')] };
  state.selected = { kind: 'node', id, ids: [id] };
  mutate(design => { design.nodes.push(node); setNodePosition(design.layout, id, { x: (hasExternalIO(design) ? 330 : 80) + (count % 3) * 90, y: 70 + (count % 4) * 70 }); });
}

function addEdge(source, target) {
  if (source.external_port_id || target.external_port_id) {
    if (source.external_port_id && target.external_port_id) return notify('Connect each external terminal to a node port, not to another external terminal.', 'error');
    return addExternalBinding(source.external_port_id || target.external_port_id, source.external_port_id ? target : source);
  }
  if (!source.node_id || !source.port_id || !target.node_id || !target.port_id) { notify('Select an output and an input port first.', 'error'); return; }
  if (state.design.edges.some(edge => equal(edge.source, source) && equal(edge.target, target))) { notify('This connection already exists. Select the existing edge to edit it.', 'warning'); return; }
  const id = newId('edge'); state.selected = { kind: 'edge', id };
  const sourcePort = state.design.nodes.find(node => node.id === source.node_id)?.ports.find(port => port.id === source.port_id);
  mutate(design => { design.edges.push({ id, source, target, behavior: '', protocol: sourcePort?.protocol || 'valid_ready' }); });
}

function duplicateSelection() {
  if (state.selected?.kind !== 'node') { toast('Select a node to duplicate it.'); return; }
  const selectedIds = state.selected.ids || [state.selected.id];
  const mapping = new Map(), ports = new Map();
  const copies = state.design.nodes.filter(node => selectedIds.includes(node.id)).map(node => {
    const copy = clone(node); copy.id = newId('node'); mapping.set(node.id, copy.id);
    copy.name = `${node.name} copy`; copy.module_name = `${node.module_name}_copy`;
    let suffix = 2;
    while (state.design.nodes.some(item => item.module_name === copy.module_name)) copy.module_name = `${node.module_name}_copy${suffix++}`;
    for (const port of copy.ports) { const original = port.id; port.id = newId('port'); ports.set(original, port.id); }
    return copy;
  });
  state.selected = { kind: 'node', id: copies[0].id, ids: copies.map(node => node.id) };
  mutate(design => {
    const edges = design.edges.filter(edge => mapping.has(edge.source.node_id) && mapping.has(edge.target.node_id)).map(edge => ({ ...clone(edge), id: newId('edge'), source: { ...clone(edge.source), node_id: mapping.get(edge.source.node_id), port_id: ports.get(edge.source.port_id) }, target: { ...clone(edge.target), node_id: mapping.get(edge.target.node_id), port_id: ports.get(edge.target.port_id) } }));
    for (const node of copies) {
      for (const port of node.ports) if (port.sideband?.associated_port_id && ports.has(port.sideband.associated_port_id)) port.sideband.associated_port_id = ports.get(port.sideband.associated_port_id);
      const originalId = [...mapping].find(([, copyId]) => copyId === node.id)[0];
      const at = Object.hasOwn(design.layout.nodes, originalId) ? design.layout.nodes[originalId] : { x: 80, y: 80 };
      node.parent_id = mapping.get(node.parent_id) || node.parent_id;
      setNodePosition(design.layout, node.id, { x: at.x + 40, y: at.y + 45 });
    }
    design.nodes.push(...copies); design.edges.push(...edges);
  });
}

function deleteSelection() {
  if (!state.selected) { toast('Select a node or connection first.'); return; }
  const selection = clone(state.selected);
  if (selection.kind === 'external') return toast('Use the external terminal controls to edit this permanent top-interface block.');
  if (selection.kind === 'external_binding') return removeExternalBinding(selection.id);
  const ids = selection.ids || [selection.id];
  if (selection.kind === 'node') {
    const edges = state.design.edges.filter(edge => ids.includes(edge.source.node_id) || ids.includes(edge.target.node_id));
    if (!confirm(`Delete ${ids.length} selected node(s) and ${edges.length} connected edge(s)? Child nodes will remain at the top level. Undo can restore this edit.`)) return;
  }
  state.selected = null;
  mutate(design => {
    if (selection.kind === 'edge') design.edges = design.edges.filter(edge => edge.id !== selection.id);
    else {
      design.nodes = design.nodes.filter(node => !ids.includes(node.id));
      for (const node of design.nodes) if (ids.includes(node.parent_id)) node.parent_id = null;
      design.edges = design.edges.filter(edge => !ids.includes(edge.source.node_id) && !ids.includes(edge.target.node_id));
      for (const id of ids) delete design.layout.nodes[id];
    }
  });
}

function renderSpecifications(host) {
  host.append(el('div', { class: 'spec-intro' }, badge(`${state.design.nodes.length} nodes`), badge(`${state.design.edges.length} connections`), el('p', { text: 'Required behavior remains separate from future verified implementation specifications. Input validation checks completeness and structured contracts, not the truth of natural-language behavior.' })));
  if (!state.design.nodes.length) host.append(section('No nodes yet', 'Create the circuit structure before writing node specifications.', el('button', { type: 'button', text: 'Open Graph Editor', onclick: () => setStage('graph_editor') })));
  const cards = state.design.nodes.map(node => section(node.name, `Module ${node.module_name} · ${node.id}`, specificationFields(node, 'spec-'), 'node-spec-card'));
  host.append(el('div', { class: 'spec-cards' }, cards));
  host.append(systemVerificationFields());
  if (state.design.edges.length) host.append(section('Edge transfer contracts', 'Explain the order and timing of data movement, including valid / ready and stalls.',
    el('div', { class: 'edge-specs' }, state.design.edges.map(edge => el('details', { class: 'edge-spec', open: true }, el('summary', { text: edgeLabel(edge) }), edgeFields(edge, 'spec-'))))));
}

function edgeLabel(edge) {
  const name = endpoint => {
    const node = state.design.nodes.find(item => item.id === endpoint.node_id);
    const port = node?.ports.find(item => item.id === endpoint.port_id);
    return node && port ? `${node.name}${instanceSuffix(endpoint.instance_index)}.${port.name}` : `Missing endpoint (${endpoint.node_id}/${endpoint.port_id})`;
  };
  return `${name(edge.source)} → ${name(edge.target)}`;
}

function renderFuture(host) {
  const index = STAGES.findIndex(stage => stage[0] === state.stage);
  host.append(section('This stage is not implemented yet', 'The 14-stage workflow keeps each future result tied to its own stage. Input editing and node candidate generation are separate from synthesis and circuit verification.',
    el('div', { class: 'future-content' }, el('div', { class: 'future-icon', text: String(index + 1).padStart(2, '0') }),
      el('div', {}, badge('Not implemented'), el('h3', { text: currentStage()[1] }), el('p', { text: currentStage()[2] }),
        el('p', { text: 'This stage has no executed synthesis, circuit simulation, layout, DRC, LVS, or post-layout evidence. Node RTL candidates, when available, belong to Local RTL Generation.' }),
        el('button', { type: 'button', disabled: true, text: 'Execution not implemented yet' }))), 'future-card'));
  host.append(section('Required before execution', 'Current stage evidence and the saved adoption policy will gate progression.',
    el('ol', { class: 'prerequisites' }, STAGES.slice(Math.max(0, index - 2), index).map(([id, label]) => el('li', {}, el('button', { type: 'button', class: 'link-button', text: label, onclick: () => setStage(id) }), badge(workflowStage(id)?.review_status || 'Awaiting Review'))))));
}

function stageRun() {
  const stage = workflowStage(state.stage);
  return state.envelope.runs.find(run => run.id === stage?.latest_run_id) || [...state.envelope.runs].reverse().find(run => run.stage_id === state.stage);
}

function renderReview() {
  const host = byId('review-content');
  if (compactSnapshot() && STAGES.findIndex(([id]) => id === state.stage) >= 3 && savedSnapshotStages.get(snapshotStageKey(state.stage))?.status !== 'ready') {
    host.replaceChildren(el('p', { class: 'scope-note', text: 'Saved adoption decisions will appear with this stage’s evidence. Opening a snapshot does not create a new decision or run.' }));
    return;
  }
  if (state.stage === 'post_layout_verification' && workflowStage(state.stage)?.implemented) {
    const run = postlayoutFlow.selected();
    renderReviewState();
    postlayoutFlow.renderReview(host); return;
  }
  if (state.stage === 'lvs' && workflowStage(state.stage)?.implemented) {
    const run = lvsFlow.selected();
    renderReviewState();
    lvsFlow.renderReview(host); return;
  }
  if (state.stage === 'drc' && workflowStage(state.stage)?.implemented) {
    const run = drcFlow.selected();
    renderReviewState();
    drcFlow.renderReview(host); return;
  }
  if (state.stage === 'layout' && workflowStage(state.stage)?.implemented) {
    const run = physicalFlow.selected();
    renderReviewState();
    physicalFlow.renderReview(host); return;
  }
  if (['global_synthesis', 'global_netlist_simulation'].includes(state.stage) && workflowStage(state.stage)?.implemented) {
    const run = globalFlow.selected();
    renderReviewState();
    globalFlow.renderReview(host); return;
  }
  if (state.stage === 'global_rtl_generation') {
    const job = globalGeneration.selected();
    renderReviewState();
    globalGeneration.renderReview(host); return;
  }
  if (state.stage === 'node_implementation_specs' && workflowStage(state.stage)?.implemented) {
    const spec = implementationSpecs.selected();
    renderReviewState();
    implementationSpecs.renderReview(host); return;
  }
  if (['local_synthesis', 'local_netlist_simulation'].includes(state.stage) && workflowStage(state.stage)?.implemented) {
    const run = localFlow.selected();
    renderReviewState();
    localFlow.renderReview(host); return;
  }
  if (state.stage === 'local_rtl_generation') {
    const job = generation.selectedJob();
    renderReviewState();
    generation.renderReview(host);
    return;
  }
  const run = stageRun();
  const stage = workflowStage(state.stage);
  const implemented = stage?.implemented ?? STAGES.findIndex(item => item[0] === state.stage) < 3;
  renderReviewState();
  host.replaceChildren();
  if (!run) {
    host.append(el('div', { class: 'review-empty' }, el('div', { class: 'review-empty-symbol', text: '◎' }), el('div', {}, el('h3', { text: implemented ? 'No verification run for this stage' : 'No execution evidence' }), el('p', { text: implemented ? executionInputDirty() ? 'Save the edited design inputs, then run verification. Adoption follows the saved policy.' : 'Run verification to see the saved input checks, diagnostics, and decision actions here.' : 'This stage has no execution evidence. No pass or acceptance is inferred.' }))));
    if (implemented && executionInputDirty()) host.append(el('button', { type: 'button', text: 'Save before verification', onclick: saveDesign }));
  } else {
    // The service fingerprints each stage's actual dependencies. A global semantic
    // hash comparison would incorrectly invalidate settings after behavior edits.
    const isCurrent = run.freshness === 'Current';
    const previous = STAGES.slice(0, STAGES.findIndex(item => item[0] === state.stage)).filter(([id]) => workflowStage(id)?.implemented);
    const missing = previous.filter(([id]) => workflowStage(id)?.review_status !== 'Accepted' || workflowStage(id)?.freshness === 'Stale');
    const canAccept = !state.busy && !executionInputDirty() && !state.externalRevision && isCurrent && run.validation_status === 'Passed' && !missing.length;
    const accepted = run.review_status === 'Accepted';
    const decision = [...state.envelope.reviews].reverse().find(review => review.run_id === run.id && review.decision === 'accepted');
    const summary = typeof run.summary === 'string' ? run.summary : JSON.stringify(run.summary, null, 2);
    const identity = el('div', { class: 'run-identity' }, badge(run.validation_status, run.validation_status === 'Passed' ? 'teal' : 'orange'), badge(isCurrent ? 'Current input' : 'Stale input', isCurrent ? 'neutral' : 'orange'), el('code', { text: run.id }), el('span', { text: `Input ${run.revision_id}` }), el('time', { dateTime: run.created_at, text: formatDate(run.created_at) }));
    host.append(identity, el('p', { class: 'run-summary', text: summary }),
      el('p', { class: 'scope-note', text: 'M1 verifies structured design inputs. It does not validate circuit functionality, generated RTL, technology installation, or timing.' }));
    if (accepted && decision) host.append(el('p', { class: 'scope-note', 'data-testid': 'adoption-provenance', text: adoptionProvenance(decision) }));
    const diagnostics = run.diagnostics || [];
    if (diagnostics.length) host.append(el('div', { class: 'diagnostics', 'data-testid': 'diagnostics' }, diagnostics.map(item => el('button', { type: 'button', class: `diagnostic ${item.severity || 'info'}`, onclick: () => focusDiagnostic(item), 'data-diagnostic-code': item.code }, badge(item.severity || 'info', item.severity === 'error' ? 'orange' : 'neutral'), el('code', { text: item.code }), el('span', { text: item.message }), el('span', { class: 'diagnostic-target', text: item.node_id || item.edge_id || '' })))));
    else host.append(el('p', { class: 'no-diagnostics', text: 'No diagnostics reported by the implemented checks.' }));
    const feedback = el('textarea', { id: 'review-note', rows: 2, value: state.feedback[run.id] || '', placeholder: 'Record your conclusion, requested correction, or reason for returning.', 'aria-label': 'Review note', 'data-testid': 'review-note', oninput: event => { state.feedback[run.id] = event.target.value; } });
    let targetStage = state.returnTargets[run.id] || previous[previous.length - 1]?.[0] || STAGES[0][0];
    const returnChoices = STAGES.slice(0, STAGES.findIndex(item => item[0] === state.stage)).map(([id, label]) => [id, label]);
    const returnSelect = field('Return destination', targetStage, value => { targetStage = value; state.returnTargets[run.id] = value; }, { id: 'return-stage', choices: returnChoices, disabled: !returnChoices.length, 'data-testid': 'return-stage' });
    const actions = el('div', { class: 'review-actions' },
      el('button', { type: 'button', class: 'primary', text: accepted ? 'Continue to next stage' : 'Accept & Continue', 'data-testid': 'accept-continue', disabled: !canAccept, title: !isCurrent ? 'This result is stale; verify the current saved input.' : executionInputDirty() ? 'Save and verify your design-input edits first.' : run.validation_status !== 'Passed' ? 'Required input checks must pass first.' : missing.length ? `Accept the current results of ${missing.map(([, label]) => label).join(', ')} first.` : accepted ? 'Open the next stage without fabricating another review decision.' : 'Record your explicit acceptance and open the next stage.', onclick: () => accepted ? setStage(STAGES[STAGES.findIndex(item => item[0] === state.stage) + 1]?.[0]) : review(run, 'accepted', feedback.value) }),
      el('button', { type: 'button', text: 'Request Changes', 'data-testid': 'request-changes', disabled: state.busy || executionInputDirty() || !isCurrent, onclick: () => review(run, 'changes_requested', feedback.value) }),
      el('button', { type: 'button', text: 'Rerun', 'data-testid': 'rerun', disabled: state.busy || executionInputDirty() || !implemented, onclick: validate }),
      el('button', { type: 'button', text: 'Return to Stage', 'data-testid': 'return-to-stage', disabled: state.busy || executionInputDirty() || !isCurrent || !returnChoices.length, onclick: () => review(run, 'return_to_stage', feedback.value, targetStage) }));
    host.append(el('div', { class: 'feedback-row' }, el('div', { class: 'field feedback-field' }, el('label', { htmlFor: 'review-note', text: 'Human feedback' }), feedback), returnSelect), actions);
    if (!canAccept) host.append(el('p', { class: 'gate-reason', text: executionInputDirty() ? 'Save and verify the current design-input edits before accepting.' : !isCurrent ? 'This run belongs to older input. Verify the saved design to obtain a current result.' : run.validation_status !== 'Passed' ? 'Resolve the required-check failures before acceptance.' : missing.length ? `Previous stages need current acceptance: ${missing.map(([, label]) => label).join(', ')}.` : state.busy ? 'Wait for the local service operation to finish.' : '' }));
    host.append(el('details', { class: 'raw-result' }, el('summary', { text: 'Full run record & input hash' }), el('pre', { text: JSON.stringify(run, null, 2) }),
      el('button', { type: 'button', text: 'Download run JSON', onclick: () => downloadJson(run, `${run.id}.json`) })));
    if (run.artifacts?.length) host.append(el('details', { class: 'raw-result' }, el('summary', { text: `Input evidence & artifacts · ${run.artifacts.length}` }),
      el('div', { class: 'artifact-list' }, run.artifacts.map(artifact => el('div', { class: 'artifact-item' }, el('code', { text: artifact.kind }),
        el('span', { text: artifact.revision_id || '' }),
        el('button', { type: 'button', class: 'link-button', text: 'Download input snapshot', onclick: async () => {
          try {
            // Only the service's snapshot route is used; model text cannot choose
            // a new remote endpoint or an arbitrary filesystem path.
            const snapshot = await api(`snapshots/${encodeURIComponent(artifact.revision_id)}`);
            downloadJson(snapshot, `${artifact.revision_id}-input.json`);
          } catch (error) { notify(error.message, 'error'); }
        } }))))));
  }
  renderHistory(host);
}

function renderHistory(host) {
  const runs = state.envelope.runs.filter(run => run.stage_id === state.stage);
  const reviews = state.envelope.reviews.filter(review => runs.some(run => run.id === review.run_id));
  const history = el('details', { class: 'history', open: state.historyOpen }, el('summary', { text: `Stage history · ${runs.length} run(s), ${reviews.length} decision(s)` }));
  history.addEventListener('toggle', () => { state.historyOpen = history.open; });
  if (!runs.length) history.append(el('p', { class: 'empty-small', text: 'No recorded runs or adoption decisions.' }));
  else history.append(el('div', { class: 'history-list' }, [...runs].reverse().map(run => el('div', { class: 'history-entry' },
    el('div', {}, el('code', { text: run.id }), badge(run.validation_status, run.validation_status === 'Passed' ? 'teal' : 'orange'), badge(run.freshness || 'Current')), el('small', { text: `Input ${run.revision_id} · ${formatDate(run.created_at)}` }),
    reviews.filter(review => review.run_id === run.id).map(review => el('p', {}, el('strong', { text: `${humanDecision(review.decision)} · ${reviewActorLabel(review)} · ` }), review.note || 'No note recorded.', review.target_stage ? ` → ${STAGES.find(item => item[0] === review.target_stage)?.[1] || review.target_stage}` : '')),
    el('button', { type: 'button', class: 'link-button', text: 'Download evidence', onclick: () => downloadJson({ run, reviews: reviews.filter(review => review.run_id === run.id) }, `${run.id}-review.json`) })))));
  host.append(history);
}

function humanDecision(value) { return { accepted: 'Accepted', changes_requested: 'Changes requested', return_to_stage: 'Returned to stage' }[value] || value; }
function formatDate(value) { const date = new Date(value); return Number.isNaN(date.getTime()) ? value || '' : date.toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' }); }

function focusDiagnostic(item) {
  if (item.external_connection_id || item.connection_id) state.selected = { kind: 'external_binding', id: item.external_connection_id || item.connection_id };
  else if (item.external_port_id) state.selected = { kind: 'external', direction: externalPorts(state.design).find(port => port.id === item.external_port_id)?.direction || 'input', portId: item.external_port_id };
  else if (item.edge_id) state.selected = { kind: 'edge', id: item.edge_id };
  else if (item.node_id) state.selected = { kind: 'node', id: item.node_id, ids: [item.node_id], portId: item.port_id };
  if (item.node_id || item.edge_id || item.external_port_id || item.external_connection_id || item.connection_id) { state.stage = 'graph_editor'; render(); byId('inspector')?.scrollIntoView({ block: 'nearest', behavior: 'smooth' }); }
  else if (item.stage_id && STAGES.some(([id]) => id === item.stage_id)) setStage(item.stage_id);
}

async function saveDesign() {
  flushActiveField();
  if (readOnly() || state.busy || !dirty() || invalidVerification()) return;
  const submitted = clone(state.design);
  state.busy = true; syncChrome();
  try {
    const response = await api('save', { design: submitted, expected_revision_id: state.envelope.revision.id });
    const stillMatches = equal(submitted, state.design);
    state.envelope = response; state.saved = clone(response.design); state.externalRevision = null;
    if (stillMatches) state.design = clone(response.design);
    generationBatches.receive(response); generation.receive(response);
    adoption.receive(response);
    localFlow.receive(response);
    implementationSpecs.receive(response);
    globalGeneration.receive(response);
    globalFlow.receive(response);
    physicalFlow.receive(response);
    drcFlow.receive(response);
    lvsFlow.receive(response);
    postlayoutFlow.receive(response);
    autosave(); toast(stillMatches ? 'Design saved. Input checks are ready to run.' : 'Submitted revision saved; newer edits remain unsaved.');
  } catch (error) { notify(error.message, 'error'); }
  finally {
    state.busy = false;
    physicalFlow.refreshDraftActions();
    if (blockFloorplan.host?.isConnected) blockFloorplan.preview();
    syncChrome(); renderReview();
  }
}

async function loadDesign() {
  if (state.busy) return;
  if (!(await preserveBeforeContextChange())) return;
  state.busy = true; syncChrome();
  try { const response = await api('project'); state.undo = []; state.redo = []; state.selected = null; adopt(response); toast('Saved project and review history restored.'); }
  catch (error) { notify(error.message, 'error'); }
  finally { state.busy = false; syncChrome(); renderReview(); }
}

async function importDesign(file) {
  if (!file || state.busy || readOnly()) return;
  if (!(await preserveBeforeContextChange())) return;
  state.busy = true; syncChrome();
  try {
    let design;
    try { design = JSON.parse(await file.text()); } catch { throw new Error('This file is not valid JSON. The current project has not changed.'); }
    const response = await api('import', { design, expected_revision_id: state.envelope.revision.id });
    state.undo = []; state.redo = []; state.selected = null; adopt(response); toast('Design imported and saved. Review prior input checks before continuing.');
  } catch (error) { notify(error.message, 'error'); }
  finally { state.busy = false; byId('import-file').value = ''; syncChrome(); renderReview(); }
}

async function validate() {
  flushActiveField();
  if (state.stage === 'local_rtl_generation') return;
  if (state.stage === 'post_layout_verification') { await postlayoutFlow.start(); return; }
  if (state.stage === 'lvs') { await lvsFlow.start(); return; }
  if (state.stage === 'drc') { await drcFlow.start(); return; }
  if (state.stage === 'layout') { await physicalFlow.start(); return; }
  if (['global_synthesis', 'global_netlist_simulation'].includes(state.stage)) { await globalFlow.start(); return; }
  if (state.stage === 'local_synthesis') { await localFlow.startBatch(); return; }
  if (state.stage === 'local_netlist_simulation') { await localFlow.startBatch(); return; }
  if (state.stage === 'node_implementation_specs') { await implementationSpecs.start(); return; }
  if (state.busy || executionInputDirty() || !workflowStage(state.stage)?.implemented) return;
  state.busy = true; syncChrome();
  try { adopt(await api('validate', { stage_id: state.stage, revision_id: state.envelope.revision.id }), true); toast('Verification finished. Review the actual checks before deciding.'); }
  catch (error) { notify(error.message, 'error'); }
  finally { state.busy = false; syncChrome(); renderReview(); }
}

async function review(run, decision, note, targetStage) {
  flushActiveField();
  if (state.busy || executionInputDirty()) return;
  if ((decision === 'changes_requested' || decision === 'return_to_stage') && !note.trim()) { toast('Add a feedback note so the requested change or return has a recorded reason.'); byId('review-note').focus(); return; }
  state.busy = true; syncChrome();
  try {
    const payload = { run_id: run.id, decision, note: note.trim(), ...(targetStage ? { target_stage: targetStage } : {}) };
    const response = await api('review', payload);
    delete state.feedback[run.id];
    adopt(response, true);
    if (decision === 'accepted') {
      const next = STAGES[STAGES.findIndex(item => item[0] === state.stage) + 1];
      if (next) setStage(next[0]);
      toast('Your acceptance was recorded.');
    } else if (decision === 'return_to_stage') { setStage(targetStage); toast('Return recorded with your feedback.'); }
    else toast('Change request recorded. Edit the input, save, and verify again.');
  } catch (error) { notify(error.message, 'error'); }
  finally { state.busy = false; syncChrome(); renderReview(); }
}

function attachCommands() {
  reviewOperator.render(byId('review-operator-host'));
  byId('undo').addEventListener('click', undo); byId('redo').addEventListener('click', redo);
  byId('save-project').addEventListener('click', saveDesign);
  const filesButton = el('button',{type:'button',id:'project-files-button','data-testid':'project-files-button',text:'Files & history',onclick:()=>projectFiles.open()});
  byId('workspace-library').after(filesButton);
  byId('load-project').addEventListener('click', loadDesign);
  byId('run-verification').addEventListener('click', validate);
  byId('import-project').addEventListener('click', () => byId('import-file').click());
  byId('import-file').dataset.testid = 'import-file';
  byId('import-file').addEventListener('change', event => importDesign(event.target.files[0]));
  byId('export-project').addEventListener('click', () => {
    if (adapterDraftDirty()) {
      downloadJson({ schema_version: 'hullcirq.browser-draft.v1', workspace: activeWorkspace, base_revision_id: state.envelope.revision.id, design: state.design, verification_drafts: state.verificationDrafts, postlayout_adapter_drafts: postlayoutFlow.adapterBackup() }, `${state.design.project.name.replace(/[^a-z0-9_-]/gi, '_')}-browser-draft.json`);
      toast('Complete browser draft exported, including source-bound unfinished S14 metadata. It is not a saved design revision.');
    } else {
      downloadJson(state.design, `${state.design.project.name.replace(/[^a-z0-9_-]/gi, '_')}${dirty() ? '-draft' : ''}.json`);
      toast(dirty() ? 'Unsaved draft exported. It is not a saved or verified revision.' : 'Current design exported. Server-side run history remains local.');
    }
  });
  window.addEventListener('beforeunload', event => {
    flushActiveField();
    if (state.authorizedContextNavigation) { state.authorizedContextNavigation = false; autosave(); return; }
    if (dirty() || adapterDraftDirty() || generation.profileDirty() || adoption.dirty()) { autosave(); event.preventDefault(); event.returnValue = ''; }
  });
  document.addEventListener('keydown', event => {
    if (!(event.ctrlKey || event.metaKey)) return;
    const key = event.key.toLowerCase();
    if (key === 's') { event.preventDefault(); document.activeElement?.blur(); saveDesign(); }
    else if (key === 'z' && !isTextEditing()) { event.preventDefault(); event.shiftKey ? redo() : undo(); }
    else if (key === 'y' && !isTextEditing()) { event.preventDefault(); redo(); }
  });
}

function isTextEditing() { return ['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement?.tagName); }

function applyReadOnly() {
  byId('workspace-readonly').hidden = !readOnly();
  if (!readOnly()) return;
  if (compactSnapshot()) byId('workspace-readonly').textContent = 'Saved read-only snapshot. Results and adoption labels describe recorded evidence; this view starts no new execution and does not requalify the current tools or environment. Open Projects and duplicate it to create an editable design.';
  for (const id of ['save-project', 'import-project', 'run-verification', 'undo', 'redo']) byId(id).disabled = true;
  for (const input of document.querySelectorAll('#stage-content input, #stage-content textarea, #stage-content select, .review-panel input, .review-panel textarea, .review-panel select')) {
    if (input.type === 'search' || ['generation-node', 'workflow-node', 'implementation-spec-node', 'physical-workflow-run-selector'].includes(input.dataset.testid)) continue;
    input.disabled = true;
  }
  for (const button of document.querySelectorAll('#stage-content button, .review-panel button')) {
    if (/^(save |generate|repair|run |rerun|repeat |start |accept|request changes|return to |delete|duplicate|\+ add|test connection|probe connection|cancel (job|run)|preview context)/i.test(button.textContent.trim())) button.disabled = true;
  }
}

async function preserveBeforeContextChange() {
  flushActiveField();
  if (!state.design) return true;
  if (state.busy || generation.profileBusy || generation.requestBusy || adoption.busy || [localFlow, globalGeneration, globalFlow, physicalFlow, drcFlow, lvsFlow, postlayoutFlow].some(module => module.busy)) {
    notify('Wait for the current request to finish before changing projects or systems.', 'warning'); return false;
  }
  if (!dirty() && !adapterDraftDirty() && !generation.profileDirty() && !adoption.dirty()) return true;
  autosave();
  const decision = await new Promise(resolve => {
    const dialog = el('dialog', { class: 'workspace-form-dialog', 'aria-label': 'Preserve unsaved changes' });
    dialog.append(el('h2', { text: 'Preserve unsaved changes' }), el('p', { text: 'This system has unsaved changes. Save them, or export the complete browser draft before continuing. S14 adapter text must be saved in its own source-bound panel, or exported here; it is never silently saved with a design. A browser backup remains scoped to this project and system.' }),
      el('div', { class: 'workspace-actions' },
        el('button', { type: 'button', text: 'Cancel', onclick: () => dialog.close('cancel') }),
        el('button', { type: 'button', text: 'Export draft and continue', 'data-testid': 'workspace-export-and-continue', onclick: () => dialog.close('export') }),
        el('button', { type: 'button', class: 'primary', text: 'Save and continue', disabled: readOnly() || !!invalidVerification() || adapterDraftDirty(), 'data-testid': 'workspace-save-and-continue', onclick: () => dialog.close('save') })));
    dialog.addEventListener('close', () => { const value = dialog.returnValue; dialog.remove(); resolve(value); }, { once: true });
    document.body.append(dialog); dialog.showModal();
  });
  if (decision === 'export') {
    downloadJson({ schema_version: 'hullcirq.browser-draft.v1', workspace: activeWorkspace, base_revision_id: state.envelope.revision.id, design: state.design, verification_drafts: state.verificationDrafts, postlayout_adapter_drafts: postlayoutFlow.adapterBackup?.() || [], provider_draft: generation.profileDraft, policy_draft: adoption.draft }, `${state.design.project.name.replace(/[^a-z0-9_-]/gi, '_')}-browser-draft.json`);
    return true;
  }
  if (decision !== 'save') return false;
  if (dirty()) await saveDesign();
  if (generation.profileDirty()) await generation.saveProfile();
  if (adoption.dirty()) await adoption.save();
  autosave();
  return !dirty() && !adapterDraftDirty() && !generation.profileDirty() && !adoption.dirty();
}

function configureBrowserScope(active) {
  reviewOperator.reset();
  savedSnapshotStages.clear(); savedSnapshotRecords.clear();
  activeWorkspace = active;
  const prefix = `hullcirq.workspace.v1:${encodeURIComponent(active.project_id)}:${encodeURIComponent(active.system_id)}:`;
  DRAFT_KEY = `${prefix}draft:${encodeURIComponent(active.session_id)}`;
  RECOVERY_KEY = `${prefix}recovered:${encodeURIComponent(active.session_id)}`;
  state.draftPrefix = `${prefix}draft:`;
}

function restoreBrowserDraft(envelope) {
  let draft;
  try {
    if (workspaceEnabled) {
      const candidates = [];
      for (let index = 0; index < localStorage.length; index++) {
        const key = localStorage.key(index);
        if (!key?.startsWith(state.draftPrefix)) continue;
        try { const candidate = JSON.parse(localStorage.getItem(key)); if (candidate?.design) candidates.push(candidate); } catch { /* Preserve unreadable backup bytes. */ }
      }
      candidates.sort((a, b) => String(b.saved_at || '').localeCompare(String(a.saved_at || '')));
      draft = candidates[0];
    } else draft = JSON.parse(localStorage.getItem(DRAFT_KEY) || 'null');
  } catch { /* Keep browser data isolated when storage is unavailable. */ }
  if (!draft?.design || draft.design.schema_version !== '0.1') return;
  if (draft.base_revision_id === envelope.revision.id && !readOnly()) {
    state.design = draft.design;
    if (draft.verification_drafts && typeof draft.verification_drafts === 'object' && !Array.isArray(draft.verification_drafts)) state.verificationDrafts = draft.verification_drafts;
    postlayoutFlow.restoreAdapterBackup?.(draft.postlayout_adapter_drafts);
    if (draft.provider_draft) generation.profileDraft = draft.provider_draft;
    if (draft.policy_draft) adoption.draft = draft.policy_draft;
    if (STAGES.some(([id]) => id === draft.stage)) state.stage = draft.stage;
    notify('Your unsaved browser draft was restored for this system. It is separate from the saved revision and its checks.', 'info');
  } else {
    isolateRecoveredDraft(draft);
    if (!state.recoveryUnpersisted) notify('An older-revision draft was preserved in a separate browser backup. Export or explicitly discard it using the recovery bar.', 'warning');
  }
}

async function start() {
  attachCommands();
  try {
    byId('startup-detail').textContent = 'Loading your project list…';
    const catalog = await workspace.initialize();
    workspaceEnabled = !!catalog;
    if (workspaceEnabled) {
      activeWorkspace = catalog.active;
      if (!catalog.active?.project_id) {
        byId('project-title').textContent = 'No project open';
        byId('save-state').textContent = 'Create or open a project';
        document.querySelector('.workspace').hidden = true;
        for (const id of ['undo', 'redo', 'load-project', 'import-project', 'export-project', 'save-project']) byId(id).disabled = true;
        byId('startup-screen').hidden = true; document.body.classList.remove('is-opening');
        return;
      }
      configureBrowserScope(catalog.active);
    }
    loadRecoveredDrafts();
    byId('startup-detail').textContent = 'Opening saved system records and checking their source links…';
    const envelope = await api('bootstrap');
    state.envelope = envelope; state.design = clone(envelope.design); state.saved = clone(envelope.design);
    executionSubmissions.observeRead(envelope, executionSubmissionScope(envelope));
    receiveExecution(envelope);
    generationBatches.receive(envelope); generation.receive(envelope);
    adoption.receive(envelope);
    localFlow.receive(envelope);
    implementationSpecs.receive(envelope);
    globalGeneration.receive(envelope);
    globalFlow.receive(envelope);
    physicalFlow.receive(envelope);
    drcFlow.receive(envelope);
    lvsFlow.receive(envelope);
    postlayoutFlow.receive(envelope);
    restoreBrowserDraft(envelope);
    render();
    byId('startup-screen').hidden = true; document.body.classList.remove('is-opening');
  } catch (error) {
    const screen = byId('startup-screen');
    screen.dataset.state = 'error'; screen.setAttribute('aria-busy', 'false');
    byId('startup-title').textContent = 'The workspace could not open';
    byId('startup-detail').textContent = error.message || 'The local service did not respond. Check that it is running, then retry.';
    byId('startup-retry').hidden = false;
    notify(error.message, 'error'); byId('stage-content').append(section('Local service not available', 'Start the HuLLCirq launcher, then retry this page. Browser drafts are retained.', el('button', { type: 'button', text: 'Retry connection', onclick: () => location.reload() })));
  }
  finally { document.documentElement.dataset.hullcirqReady = 'true'; }
}

start();
