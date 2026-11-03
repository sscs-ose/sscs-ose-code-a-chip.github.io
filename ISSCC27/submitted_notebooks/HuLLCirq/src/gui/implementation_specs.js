import { element as el, field, badge, downloadJsonResponse } from './dom.js';
import { adoptionProvenance } from './review_operator.js';

const STAGE = 'node_implementation_specs';
const active = record => record && ['Queued', 'Running', 'Starting', 'Stopping', 'Cancelling'].includes(record.execution_status);
const safe = value => String(value).replace(/[^a-z0-9_.-]/gi, '_');
const card = (title, description, ...children) => el('section', { class: 'card' }, el('div', { class: 'card-heading' }, el('h2', { text: title }), el('p', { text: description })), ...children);
const details = (title, value, testid, open = false) => el('details', { open }, el('summary', { text: title }), el('pre', { text: JSON.stringify(value ?? {}, null, 2), ...(testid ? { 'data-testid': testid } : {}) }));
const yesNo = value => value === true ? 'Yes' : value === false ? 'No' : 'Not stated';
function downloadText(value, filename) {
  const url = URL.createObjectURL(new Blob([value], { type: 'text/plain' }));
  const link = el('a', { href: url, download: filename }); document.body.append(link); link.click(); link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/** Deterministic evidence extraction. This view never invents new vectors or a model response. */
export class NodeImplementationSpecs {
  constructor(callbacks) { this.callbacks = callbacks; this.specs = []; this.nodes = []; this.reviews = []; this.nodeId = null; this.specId = null; this.busy = false; this.feedback = new Map(); this.returnTargets = new Map(); }
  project() { return this.callbacks.project(); }
  relevant() { return this.specs.filter(spec => spec.node_id === this.nodeId).toReversed(); }
  nodeState(nodeId) {
    const states = this.project().envelope.implementation_spec_nodes;
    return (Array.isArray(states) ? states : []).find(node => node.node_id === nodeId);
  }
  latestSpec(nodeId = this.nodeId) {
    const state = this.nodeState(nodeId);
    return state?.latest_spec_id ? this.specs.find(spec => spec.node_id === nodeId && spec.id === state.latest_spec_id) : undefined;
  }
  accepted(nodeId) {
    const state = this.nodeState(nodeId), spec = this.latestSpec(nodeId);
    return !!state?.latest_spec_id && state.latest_spec_id === state.accepted_spec_id && !!spec &&
      spec.execution_status === 'Completed' && spec.validation_status === 'Passed' && spec.review_status === 'Accepted' && this.runCurrent(spec);
  }
  nextNode() { return this.project().design.nodes.find(node => !this.accepted(node.id)); }
  selected() { return this.specs.find(spec => spec.id === this.specId && spec.node_id === this.nodeId) || this.currentRun(); }
  currentRun() { const spec = this.latestSpec(); return this.runCurrent(spec) ? spec : undefined; }
  runCurrent(spec) {
    const source = this.source(spec?.node_id);
    return !!spec && this.latestSpec(spec.node_id)?.id === spec.id && spec.node_id === source?.node_id && spec.freshness === 'Current' && !!source &&
      spec.source_run_id === source.id && spec.candidate_id === source.candidate_id;
  }
  setNode(id) { this.nodeId = id; this.specId = null; }
  source(nodeId = this.nodeId) {
    const envelope = this.project().envelope, generation = envelope.generation || {};
    const state = generation.nodes?.find(node => node.node_id === nodeId);
    const candidate = generation.jobs?.find(job => job.id === state?.latest_job_id && job.id === state?.accepted_job_id &&
      job.execution_status === 'Completed' && job.validation_status === 'Passed' && job.review_status === 'Accepted' && job.freshness === 'Current');
    if (!candidate) return undefined;
    const runs = envelope.workflow_runs || [], same = run => run.node_id === nodeId && run.candidate_id === candidate.id && run.freshness === 'Current' &&
      (!run.revision_id || run.revision_id === candidate.revision_id) && (!run.input_hash || run.input_hash === candidate.input_hash) &&
      (!run.rtl_sha256 || run.rtl_sha256 === candidate.rtl_sha256);
    const synthesis = [...runs].reverse().find(run => run.stage_id === 'local_synthesis' && same(run));
    const passed = run => run?.execution_status === 'Completed' && run.validation_status === 'Passed' && run.review_status === 'Accepted';
    if (!passed(synthesis) || !synthesis.netlist) return undefined;
    // Never reuse an older passing simulation after a newer failure or new netlist.
    const simulation = [...runs].reverse().find(run => run.stage_id === 'local_netlist_simulation' && same(run));
    if (!passed(simulation) || simulation.prior_run_id !== synthesis.id || simulation.netlist_sha256 !== synthesis.netlist_sha256) return undefined;
    return simulation;
  }
  receive(envelope) {
    this.specs = envelope.implementation_specs || [];
    this.nodes = envelope.implementation_spec_nodes || [];
    this.reviews = envelope.implementation_spec_reviews || [];
    this.storageError = envelope.implementation_specs_storage_error || envelope.implementation_spec_storage_error;
    if (!this.project().design.nodes.some(node => node.id === this.nodeId)) this.nodeId = this.project().design.nodes[0]?.id || null;
    this.refresh();
  }
  operationGate() {
    const project = this.project(), envelope = project.envelope;
    if (project.readOnly || envelope.workspace_identity?.read_only) return 'This preserved system is read-only. Open an editable system before deriving or reviewing specifications.';
    if (!project.envelope.workflow?.find(stage => stage.id === STAGE)?.implemented) return 'Evidence extraction is not implemented by the connected service.';
    if (this.storageError) return `Implementation-spec storage error: ${this.storageError.message || this.storageError.code}.`;
    if (project.conflict) return 'A newer saved design was detected. Export your draft, then Open saved.';
    if (project.dirty) return 'Save the complete design before deriving evidence-backed specifications.';
    if (project.busy) return 'Wait for the current project operation to finish.';
    if (project.postlayoutRunning) return 'A post-layout tool run is active. Inspect or cancel it before starting another operation.';
    if (project.lvsRunning) return 'An LVS tool run is active. Wait for its recorded result before deriving specifications.';
    if (envelope.repair_analysis?.active_job_id) return 'Repair analysis is active. Inspect or cancel it before deriving or reviewing specifications.';
    const records = [...(envelope.generation?.jobs || []), ...(envelope.generation_batches?.batches || []),
      ...(envelope.workflow_runs || []), ...(envelope.workflow_batches || []), ...(envelope.repair_analysis?.jobs || []),
      ...['global_generation', 'global_workflow', 'physical_workflow', 'drc_workflow', 'lvs_workflow', 'postlayout_workflow']
        .flatMap(key => [...(envelope[key]?.jobs || []), ...(envelope[key]?.runs || [])])];
    if (records.some(active)) return 'An operation is running. Wait for its saved result before deriving or reviewing specifications.';
    return '';
  }
  gate() {
    const project = this.project(), source = this.source(), common = this.operationGate();
    if (common) return common;
    if (!source || source.execution_status !== 'Completed' || source.validation_status !== 'Passed' || source.review_status !== 'Accepted' || source.freshness !== 'Current') return 'This node needs a current, Passed and accepted Local Netlist Simulation result.';
    const node = this.nodes.find(item => item.node_id === this.nodeId);
    if (node?.ready === false) return node.blocked_reason || 'The saved source evidence is not eligible for extraction.';
    return '';
  }
  render(host) {
    this.host = host;
    const project = this.project();
    host.replaceChildren(el('div', { class: 'spec-intro' }, badge('Selected node only'), badge('Evidence extraction · no LLM request'), el('p', { text: 'Derive this node’s interface and finite observed behavior from its accepted generic netlist result. Original requirements, finite checked facts and unverified conditions remain distinct. This does not establish whole-system behavior or physical timing.' })),
      el('div', { class: 'implementation-workspace' },
        card('Evidence source', 'Use the adopted S06 result and the same saved project, candidate and initial verification plan.',
          el('div', { class: 'form-grid single' }, field('Target node', this.nodeId || '', value => { this.setNode(value); this.render(this.host); this.renderReview(this.reviewHost); }, { id: 'implementation-spec-node', 'data-testid': 'implementation-spec-node', choices: project.design.nodes.map(node => [node.id, `${node.name} · ${node.module_name}`]) })),
          el('div', { class: 'provider-actions' }, el('button', { type: 'button', class: 'primary', text: 'Derive and verify node specification', 'data-testid': 'implementation-spec-run', onclick: () => this.start() }), el('button', { type: 'button', text: 'Inspect source netlist result', 'data-testid': 'implementation-source', onclick: () => this.callbacks.navigate('local_netlist_simulation', this.nodeId) })),
          el('p', { class: 'generation-gate', 'data-testid': 'implementation-gate' }), el('div', { class: 'workflow-lineage', 'data-testid': 'implementation-lineage' })),
        card('Node implementation specification', 'Public ports come from the actual synthesized boundary. Finite evidence is traceable to its original inputs.', el('div', { 'data-testid': 'implementation-result' }))),
      card('Saved specifications', 'Rerun appends a new result. Old and stale evidence remains available for inspection.', el('div', { class: 'generation-job-list', 'data-testid': 'implementation-history' })));
    this.refresh();
  }
  refresh() {
    if (!this.host?.isConnected || this.project().stage !== STAGE) return;
    const gate = this.gate(), source = this.source();
    const button = this.host.querySelector('[data-testid="implementation-spec-run"]');
    if (!button) return;
    const target = this.host.querySelector('[data-testid="implementation-spec-node"]');
    if (target) target.disabled = this.busy;
    button.disabled = this.busy || !!gate; button.title = gate || 'Derive this node specification from its saved, accepted S06 evidence.';
    this.host.querySelector('[data-testid="implementation-gate"]').textContent = this.busy ? 'Deriving and checking saved evidence…' : gate || 'Ready. Deterministic extraction checks run before adoption under the saved policy.';
    this.host.querySelector('[data-testid="implementation-lineage"]').replaceChildren(el('p', { text: `Project ${this.project().design.project.name} · saved revision ${this.project().envelope.revision.id}` }),
      el('p', { text: `S06 source ${source?.id || 'No eligible source'} · ${source?.validation_status || 'Not checked'} · ${source?.review_status || 'Not adopted'} · ${source?.freshness || 'Unavailable'}` }),
      el('p', { text: `Candidate ${source?.candidate_id || 'Not available'} · netlist SHA-256 ${source?.netlist_sha256 || 'Not available'}` }));
    this.renderResult(); this.renderHistory();
    if (this.reviewHost?.isConnected) this.renderReview(this.reviewHost);
    this.callbacks.chrome?.();
  }
  renderResult() {
    const host = this.host?.querySelector('[data-testid="implementation-result"]');
    if (!host) return;
    const spec = this.selected();
    if (!spec) { host.replaceChildren(el('p', { class: 'empty-small', text: 'No implementation specification has been derived for this node. No behavior or interface evidence is inferred.' })); return; }
    const document = spec.specification || spec.implementation_spec || spec.document || {};
    const ports = document.public_ports || document.public_interface?.ports || document.interface?.ports || [];
    const facts = document.observed_facts || document.observed_behavior || document.finite_observed_facts || {};
    const source = (this.project().envelope.workflow_runs || []).find(run => run.id === spec.source_run_id);
    const candidate = (this.project().envelope.generation?.jobs || []).find(job => job.id === spec.candidate_id);
    host.replaceChildren(el('div', { class: 'generation-summary', 'data-testid': 'implementation-status' }, badge(spec.execution_status), badge(spec.validation_status, spec.validation_status === 'Passed' ? 'teal' : 'orange'), badge(spec.review_status, spec.review_status === 'Accepted' ? 'teal' : 'neutral'), badge(spec.freshness || 'Current', spec.freshness === 'Stale' ? 'orange' : 'neutral'), el('code', { text: spec.id })),
      el('div', { class: 'generation-artifact implementation-artifact' },
        spec.error ? el('div', { class: 'generation-error', text: `${spec.error.code || 'Extraction error'} · ${spec.error.message || JSON.stringify(spec.error)}` }) : null,
        (spec.diagnostics || []).map(item => el('div', { class: `diagnostic ${item.severity || 'info'}` }, badge(item.severity || 'info'), el('code', { text: item.code || '' }), el('span', { text: item.message || JSON.stringify(item) }))),
        this.storageError ? el('div', { class: 'generation-error', text: this.storageError.message || JSON.stringify(this.storageError) }) : null,
        el('p', { class: 'scope-note', 'data-testid': 'implementation-scope', text: 'Finite-cycle, zero-delay generic-netlist evidence only. Requirements are design intent; observations describe tested conditions. No internal-net stability promise, whole-system behavior, PDK mapping, SDF or physical timing is inferred.' }),
        !spec.specification ? el('p', { class: 'generation-error', 'data-testid': 'implementation-document-unavailable', text: 'No verified specification document was produced. Inspect this saved extraction attempt’s diagnostics and checks; no interface or behavior is inferred.' }) : null,
        details('Original design requirements', document.requirements || document.original_requirements || {}, 'implementation-requirements', true),
        el('h3', { text: 'Finite behavior checked by assertions' }),
        el('p', { text: `${facts.vector_count ?? 'Unspecified'} ${facts.vector_unit === 'recipe_step' ? 'saved verification recipe steps' : 'original input cycles'}. These facts come from assertions against an independent reference; the reference trace is not a captured waveform.` }),
        details('Finite assertion summary', { ...facts, trace: undefined }, 'implementation-observations', true),
        facts.trace ? details('Original independent reference trace', facts.trace, 'implementation-reference-trace') : null,
        el('section', { class: 'implementation-port-section' }, el('h3', { text: 'Public module boundary' }), el('p', { text: 'Use these physical port names when integrating this node. Internal synthesized nets are not exposed as integration interfaces.' }),
          ports.length ? el('div', { class: 'implementation-table-wrap' }, el('table', { class: 'implementation-port-table', 'data-testid': 'implementation-ports' },
            el('thead', {}, el('tr', {}, ['Port name', 'Direction', 'Width / range', 'Semantic signed', 'RTL signed', 'Netlist signed', 'Role'].map(title => el('th', { scope: 'col', text: title })))),
            el('tbody', {}, ports.map(port => el('tr', {}, el('td', {}, el('code', { text: port.name || port.physical_name || '' })), el('td', { text: port.direction || '' }), el('td', { text: `${port.width ?? ''}${port.netlist_range ? ` · ${JSON.stringify(port.netlist_range)}` : ''}` }), el('td', { text: yesNo(port.semantic_signed) }), el('td', { text: yesNo(port.source_rtl_signed) }), el('td', { text: yesNo(port.netlist_declared_signed) }), el('td', { text: [port.role, port.logical_port_name || port.logical_port_id].filter(Boolean).join(' · ') })))))) : el('p', { class: 'empty-small', text: 'No verified public-port record is available.' }),
          el('p', { class: 'scope-note', text: 'Semantic signedness, source RTL declarations and netlist declarations are separate. A generic netlist may preserve bits while removing a signed declaration.' }),
          details('Exact public interface and integration artifact', document.public_interface || {}, 'implementation-interface')),
        details('Unverified conditions and limitations', document.unverified_limits || document.unverified_conditions || document.limitations || [], 'implementation-unverified', true),
        details('Extraction checks and exact source evidence', spec.checks || {}, 'implementation-checks'),
        details('Source lineage and input hashes', document.lineage || document.evidence || spec.lineage || { node_id: spec.node_id, source_run_id: spec.source_run_id, candidate_id: spec.candidate_id, revision_id: spec.revision_id, input_hash: spec.input_hash, netlist_sha256: spec.netlist_sha256, verification_plan_hash: spec.verification_plan_hash, vector_hash: spec.vector_hash, testbench_sha256: spec.testbench_sha256 }, 'implementation-frozen-input'),
        details('Complete specification document', document, 'implementation-document'),
        el('p', { class: 'scope-note', text: 'JSON previews use browser number precision. JSON downloads preserve the backend’s exact integers, including wide configuration words.' }),
        el('div', { class: 'generation-artifact-actions' }, el('button', { type: 'button', text: 'Download specification JSON', 'data-testid': 'implementation-download', disabled: !spec.specification, onclick: () => downloadJsonResponse(`/api/artifacts/implementation-specs/${encodeURIComponent(spec.id)}/specification`, `${safe(spec.id)}-specification.json`, this.callbacks.notify) }), el('button', { type: 'button', text: 'Download full evidence record', 'data-testid': 'implementation-download-record', onclick: () => downloadJsonResponse(`/api/implementation-specs/${encodeURIComponent(spec.id)}`, `${safe(spec.id)}.json`, this.callbacks.notify) }),
          source ? el('button', { type: 'button', text: 'Download exact S06 source record', 'data-testid': 'implementation-download-source', onclick: () => downloadJsonResponse(`/api/workflow/runs/${encodeURIComponent(source.id)}`, `${safe(source.id)}.json`, this.callbacks.notify) }) : null,
          source?.verification_plan ? el('button', { type: 'button', text: 'Download original verification plan', 'data-testid': 'implementation-download-plan', onclick: () => downloadJsonResponse(`/api/artifacts/workflow/${encodeURIComponent(source.id)}/verification-plan`, `${safe(source.id)}-verification-plan.json`, this.callbacks.notify) }) : null,
          candidate?.rtl ? el('button', { type: 'button', text: 'Download adopted source RTL', 'data-testid': 'implementation-download-rtl', onclick: () => downloadText(candidate.rtl, `${safe(candidate.id)}.v`) }) : null,
          el('button', { type: 'button', text: 'Rerun extraction', 'data-testid': 'implementation-rerun', disabled: this.busy || !!this.gate(), onclick: () => this.start() }), el('button', { type: 'button', text: 'Refresh saved evidence', 'data-testid': 'implementation-refresh', disabled: this.busy, onclick: () => this.refreshSaved() }))));
  }
  renderHistory() {
    const host = this.host?.querySelector('[data-testid="implementation-history"]');
    if (!host) return;
    host.replaceChildren(...(this.relevant().length ? this.relevant().map(spec => el('button', { type: 'button', class: `generation-job-button${spec.id === this.selected()?.id ? ' selected' : ''}`, onclick: () => { this.specId = spec.id; this.refresh(); } }, badge(spec.execution_status), badge(spec.validation_status), badge(spec.review_status), badge(spec.freshness || 'Current'), el('code', { text: spec.id }), el('small', { text: `Source S06 ${spec.source_run_id} · ${spec.created_at}` }))) : [el('p', { class: 'empty-small', text: 'No recorded specifications for this node.' })]));
  }
  renderReview(host) {
    if (!host) return;
    this.reviewHost = host;
    const spec = this.selected();
    if (!spec) { host.replaceChildren(el('p', { class: 'empty-small', text: 'Derive the node specification to inspect its validated evidence and adoption decision.' })); return; }
    const project = this.project(), accepted = spec.review_status === 'Accepted';
    const reviewable = !this.busy && !this.operationGate() && this.latestSpec(spec.node_id)?.id === spec.id && spec.execution_status === 'Completed';
    const eligible = reviewable && !project.dirty && !project.conflict && this.runCurrent(spec) && !this.gate();
    const decision = this.reviews.toReversed().find(item => item.spec_id === spec.id && item.decision === 'accepted');
    const note = el('textarea', { rows: 3, 'aria-label': 'Implementation specification review note', 'data-testid': 'implementation-feedback', value: this.feedback.get(spec.id) || '', oninput: event => this.feedback.set(spec.id, event.target.value), placeholder: 'Record a concern, requested correction or reason to return to an earlier stage.' });
    const activeNote = host.contains(document.activeElement) && document.activeElement.dataset.testid === 'implementation-feedback' ? document.activeElement : null;
    const selection = activeNote ? [activeNote.selectionStart, activeNote.selectionEnd] : null;
    const target = this.returnTargets.get(spec.id) || 'local_netlist_simulation';
    const choices = project.envelope.workflow.filter(stage => stage.implemented && stage.id !== STAGE).filter(stage => ['global_settings', 'graph_editor', 'specifications', 'local_rtl_generation', 'local_synthesis', 'local_netlist_simulation'].includes(stage.id)).map(stage => [stage.id, stage.name || stage.label || stage.id.replaceAll('_', ' ')]);
    host.replaceChildren(el('div', { class: 'generation-review-status' }, badge(spec.review_status, accepted ? 'teal' : 'neutral'), badge(spec.freshness || 'Current'), el('code', { text: spec.id })),
      el('p', { class: 'scope-note', 'data-testid': 'implementation-adoption-provenance', text: accepted ? adoptionProvenance(decision) : 'This specification is not currently accepted. The saved policy can adopt only current specifications whose required extraction checks pass; previous adoption records remain historical.' }),
      el('div', { class: 'feedback-row' }, el('div', { class: 'field feedback-field' }, el('label', { text: 'Review and debug feedback' }), note), field('Return destination', target, value => this.returnTargets.set(spec.id, value), { id: 'implementation-return-stage', 'data-testid': 'implementation-return-stage', choices })),
      el('div', { class: 'review-actions' }, el('button', { type: 'button', class: 'primary', text: accepted ? 'Specification accepted' : 'Accept verified specification', 'data-testid': 'implementation-accept', disabled: !eligible || accepted || spec.validation_status !== 'Passed', onclick: () => this.review(spec, 'accepted', note.value) }),
        el('button', { type: 'button', text: 'Request Changes', 'data-testid': 'implementation-request-changes', disabled: !reviewable, onclick: () => this.review(spec, 'changes_requested', note.value) }),
        el('button', { type: 'button', text: 'Return to Stage', 'data-testid': 'implementation-return', disabled: !reviewable || !choices.length, onclick: () => this.review(spec, 'return_to_stage', note.value, this.returnTargets.get(spec.id) || target) }),
        el('button', { type: 'button', text: 'Continue to Global RTL Generation', 'data-testid': 'implementation-continue', disabled: !eligible || !this.accepted(spec.node_id) || spec.validation_status !== 'Passed' || !project.envelope.global_generation?.ready, title: !this.runCurrent(spec) ? 'This specification does not use the current accepted node sources.' : project.envelope.global_generation?.blocked_reason || 'All current adopted node specifications are required.', onclick: () => this.callbacks.navigate('global_rtl_generation') })),
      details('Exact adoption and feedback records', this.reviews.filter(item => item.spec_id === spec.id), 'implementation-review-records'));
    if (activeNote) { note.focus({ preventScroll: true }); note.setSelectionRange(...selection); }
  }
  async start() {
    if (this.busy || this.gate()) return;
    const project = this.project(), source = this.source(), nodeId = this.nodeId;
    this.busy = true; this.refresh();
    try {
      const envelope = await this.callbacks.request('implementation-specs/start', { node_id: nodeId, revision_id: project.envelope.revision.id, source_run_id: source.id });
      const result = envelope.implementation_specs?.filter(spec => spec.node_id === nodeId).at(-1);
      if (this.nodeId === nodeId) this.specId = result?.id || null;
      this.callbacks.envelope(envelope);
      this.callbacks.toast(result?.validation_status === 'Passed' ? 'Node specification derived and verified from its saved S06 evidence.' : `Extraction attempt saved with ${result?.validation_status || 'unavailable'} checks. Inspect the recorded diagnostics and evidence.`);
    } catch (error) {
      const message = error.code === 'internal_error'
        ? `S07 extraction failed (internal_error). S06 result ${source.id} is preserved. Check saved specifications before retrying.`
        : error.message;
      this.callbacks.notify(message, 'error');
    }
    finally { this.busy = false; this.refresh(); }
  }
  async refreshSaved() {
    if (this.busy) return;
    this.busy = true; this.refresh();
    try { if (this.selected()) await this.callbacks.request(`implementation-specs/${encodeURIComponent(this.selected().id)}`); this.callbacks.envelope(await this.callbacks.request('project')); }
    catch (error) { this.callbacks.notify(`${error.message} No extraction request was resent.`, 'error'); }
    finally { this.busy = false; this.refresh(); }
  }
  async review(spec, decision, note, target) {
    if (this.busy || this.operationGate()) return;
    if (this.latestSpec(spec.node_id)?.id !== spec.id || decision === 'accepted' &&
        (spec.validation_status !== 'Passed' || !this.runCurrent(spec) || this.gate())) return;
    if (decision !== 'accepted' && !note.trim()) { this.callbacks.toast('Record a reason for requesting changes or returning to an earlier stage.'); return; }
    this.busy = true; this.refresh();
    try { this.callbacks.envelope(await this.callbacks.request('implementation-specs/review', { spec_id: spec.id, decision, note: note.trim(), ...(target ? { target_stage: target } : {}) })); if (target) this.callbacks.navigate(target, this.nodeId); }
    catch (error) { this.callbacks.notify(error.message, 'error'); }
    finally { this.busy = false; this.refresh(); }
  }
}
