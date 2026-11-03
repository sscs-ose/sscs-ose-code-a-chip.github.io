import { element as el, field } from './dom.js';

/** Shared S11–S14 diagnostic routing. Preparing never requests a model/tool. */
export class PhysicalRecovery {
  constructor(callbacks) { this.callbacks = callbacks; this.drafts = new Map(); }
  key(stage, run) {
    const p = this.callbacks.project(), w = p.envelope.workspace_identity || {};
    return JSON.stringify([w.project_id, w.system_id, w.session_id, p.envelope.revision.id, stage, run?.id, run?.record_hash]);
  }
  render(host, stage, run) {
    if (!run) return;
    const p = this.callbacks.project(), key = this.key(stage, run);
    if (!this.drafts.has(key)) this.drafts.set(key, { target: 'environment', node: '', feedback: '', prepared: null, busy: false, error: '', history: [] });
    const d = this.drafts.get(key), panel = el('section', { class: 'card', 'data-testid': 'physical-recovery-card' });
    const blocked = p.readOnly || p.dirty || p.conflict || p.busy || d.busy || run.freshness !== 'Current' || ['Queued','Running'].includes(run.execution_status);
    const redraw = () => { panel.replaceChildren(); build(); };
    const invalidate = () => { d.prepared = null; d.error = ''; panel.querySelector('[data-testid="physical-recovery-prepared"]')?.remove(); };
    const stillCurrent = () => this.callbacks.project().stage === stage && this.key(stage, this.callbacks.selected(stage)) === key;
    const act = async kind => {
      if (blocked || d.busy || !stillCurrent()) return;
      const draftScope = JSON.stringify([d.target,d.node,d.feedback,d.prepared?.id]);
      d.busy = true; d.error = ''; redraw();
      try {
        const result = await this.callbacks.request(`physical-recovery/${kind}`, kind === 'history' ? {stage} : kind === 'prepare' ? {
          stage, run_id: run.id, revision_id: p.envelope.revision.id, target: d.target,
          node_id: d.target === 'node_rtl' ? d.node : null, feedback: d.feedback,
        } : { id: d.prepared.id });
        if (!stillCurrent() || draftScope !== JSON.stringify([d.target,d.node,d.feedback,d.prepared?.id])) return;
        if (kind === 'history') { d.history = result.records; return; }
        d.prepared = result;
        if (kind === 'open') await this.callbacks.open(result);
      } catch (error) { if (stillCurrent()) d.error = error.message; }
      finally { d.busy = false; if (stillCurrent()) { redraw(); this.callbacks.refresh?.(); } }
    };
    const build = () => {
      panel.append(...[el('h3', { text: 'Diagnose and return for correction' }),
        el('p', { text: 'Inspect required checks, diagnostics and raw reports above. Choose the cause hypothesis and correction target explicitly. Tool failures do not automatically prove that RTL is wrong.' }),
        el('p', { class: 'scope-note', text: 'Extraction/model recognition → S13 correction profile; placement/routing/electrical limits → S11; missing runtime/proof files → environment; node behavior → S04; top-level wiring → S08. An unsupported check remains unsupported.' }),
        el('p', { text: `Frozen source: ${stage} · ${run.id} · ${run.freshness}. Preparing a handoff saves diagnostic evidence only; it neither rejects nor accepts this run.` }),
        field('Cause hypothesis / correction target', d.target, value => { d.target = value; invalidate(); redraw(); }, {
          disabled: !!blocked || d.busy, 'data-testid': 'physical-recovery-target', choices: [
            ['environment','Environment / runtime / insufficient evidence'], ['extraction','S13 extraction / comparison setup'],
            ['physical','S11 physical implementation'], ['node_rtl','S04 node RTL'], ['global_rtl','S08 integration RTL'],
          ],
        }),
        d.target === 'node_rtl' ? field('RTL definition to repair', d.node, value => { d.node = value; invalidate(); redraw(); }, {
          disabled: !!blocked || d.busy, 'data-testid': 'physical-recovery-node', choices: [['','Select a definition'], ...p.design.nodes.map(n => [n.id, n.name || n.id])],
        }) : null,
        field('Evidence and requested correction', d.feedback, value => { d.feedback = value; invalidate(); }, { disabled: !!blocked || d.busy, multiline: true, 'data-testid': 'physical-recovery-feedback' }),
        el('button', { type: 'button', text: 'Prepare diagnostic handoff', disabled: !!blocked || d.busy,
          'data-testid': 'physical-recovery-prepare', onclick: () => act('prepare') }),
        el('button', { type: 'button', text: 'Load saved diagnostic handoffs', disabled: !!blocked || d.busy,
          'data-testid': 'physical-recovery-history', onclick: () => act('history') }),
        d.error ? el('p', { class: 'generation-error', role: 'alert', text: d.error }) : null].filter(Boolean));
      for (const saved of d.history) panel.append(el('details', {},
        el('summary', { text: `${saved.created_at} · ${saved.target_stage} · ${saved.run_id}` }),
        el('pre', { text: JSON.stringify(saved, null, 2) }),
        el('button', { type: 'button', text: 'Select saved handoff', disabled: !!blocked || saved.run_id !== run.id,
          onclick: () => { d.prepared = saved; d.target = saved.target; d.node = saved.node_id || ''; d.feedback = saved.feedback; redraw(); } })));
      if (d.prepared) panel.append(el('div', { 'data-testid': 'physical-recovery-prepared' },
        el('p', { text: d.prepared.certainty }),
        el('details', {}, el('summary', { text: 'Inspect exact saved repair instruction and source binding' }),
          el('pre', { text: JSON.stringify(d.prepared, null, 2) })),
        el('p', { text: 'Opening S04/S08 fills an unsent repair draft. Review Context Preview, then explicitly request the model. After repair, repeat affected synthesis, simulation, specifications and physical verification. Original results remain in history.' }),
        el('button', { type: 'button', text: 'Open correction target', disabled: !!blocked,
          'data-testid': 'physical-recovery-open', onclick: () => act('open') })));
    };
    build(); host.append(panel);
  }
}
