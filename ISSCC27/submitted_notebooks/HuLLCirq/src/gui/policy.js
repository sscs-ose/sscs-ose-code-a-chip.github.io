import { element as el, field, badge } from './dom.js';

const defaults = { id: null, mode: 'manual', user_authorized: false, note: '', created_at: null };
const selection = policy => ({ mode: policy?.mode || 'manual', user_authorized: policy?.user_authorized === true, note: policy?.note || '' });
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);

/** Explicit authorization for adoption; never a fabricated human review. */
export class AdoptionPolicy {
  constructor(callbacks) { this.callbacks = callbacks; this.saved = { ...defaults }; this.draft = selection(this.saved); this.available = false; this.busy = false; }
  dirty() { return !same(this.draft, selection(this.saved)); }
  receive(envelope) {
    const dirty = this.dirty();
    this.available = !!envelope.review_policy;
    this.saved = envelope.review_policy || { ...defaults };
    if (!dirty) this.draft = selection(this.saved);
    this.history = envelope.policy_history || [];
    this.refresh();
  }
  automatic() { return this.saved.mode === 'accept_on_pass' && this.saved.user_authorized === true; }
  render(host) {
    this.host = host;
    const update = (key, value) => { this.draft[key] = value; this.refresh(); };
    host.replaceChildren(el('section', { class: 'card adoption-policy' },
      el('div', { class: 'card-heading' }, el('h2', { text: 'Adoption policy' }), el('p', { text: 'Choose the decision policy before running verification. Passing only the required implemented checks can authorize adoption; failed, unsupported or stale results are never accepted.' })),
      el('div', { class: 'form-grid single' },
        field('Adoption policy', this.draft.mode, value => { update('mode', value); if (value === 'manual') update('user_authorized', false); }, { id: 'adoption-policy-mode', 'data-testid': 'adoption-policy-mode', choices: [['manual', 'Manual review'], ['accept_on_pass', 'Accept after verification']] }),
        el('label', { class: 'policy-authorization' }, el('input', { type: 'checkbox', checked: this.draft.user_authorized, 'data-testid': 'adoption-policy-authorize', onchange: event => update('user_authorized', event.target.checked) }), el('span', { text: 'I authorize acceptance after all required verification passes for the current source and candidate. Record this as an adoption-policy decision, not a manual human review.' })),
        field('Authorization / policy note', this.draft.note, value => update('note', value), { id: 'adoption-policy-note', 'data-testid': 'adoption-policy-note', multiline: true, placeholder: 'Record the intended verification boundary or why manual review is required.' })),
      el('div', { class: 'provider-actions' }, el('button', { type: 'button', class: 'primary', text: 'Save adoption policy', 'data-testid': 'adoption-policy-save', onclick: () => this.save() }), el('span', { id: 'adoption-policy-draft-state', class: 'generation-connection-label' })),
      el('div', { class: 'provider-status', 'data-testid': 'adoption-policy-status' })));
    this.refresh();
  }
  refresh() {
    if (!this.host?.isConnected) return;
    const button = this.host.querySelector('[data-testid="adoption-policy-save"]');
    button.disabled = !this.available || this.busy || (this.draft.mode === 'accept_on_pass' && !this.draft.user_authorized) || (!this.dirty() && !!this.saved.id);
    button.title = !this.available ? 'Start the service with adoption-policy support.' : this.draft.mode === 'accept_on_pass' && !this.draft.user_authorized ? 'Explicitly authorize this policy before saving it.' : 'Persist the authorization before running verification.';
    this.host.querySelector('.policy-authorization').hidden = this.draft.mode !== 'accept_on_pass';
    this.host.querySelector('#adoption-policy-draft-state').textContent = this.busy ? 'Saving policy…' : this.dirty() ? 'Unsaved policy selection' : 'Saved policy';
    this.host.querySelector('[data-testid="adoption-policy-status"]').replaceChildren(
      el('div', { class: 'provider-identity' }, badge(this.automatic() ? 'Accept after verification' : 'Manual review', this.automatic() ? 'teal' : 'neutral'), el('code', { text: this.saved.id || 'Default policy · not explicitly configured' })),
      el('p', { text: this.automatic() ? 'Authorized policy decisions are recorded with actor automation_policy. Results, complete evidence, repair and retry remain available. Passing does not automatically navigate to the next stage.' : 'Each eligible result requires an explicit review decision. Select the actual review operator before using a review button. Changing the selection above does not take effect until saved.' }),
      el('details', { class: 'raw-result' }, el('summary', { text: 'Saved authorization and policy history' }), el('pre', { text: JSON.stringify({ policy: this.saved, history: this.history }, null, 2) })));
  }
  async save() {
    if (this.busy || !this.available || (this.draft.mode === 'accept_on_pass' && !this.draft.user_authorized)) return;
    const submitted = structuredClone(this.draft);
    this.busy = true; this.refresh();
    try {
      const envelope = await this.callbacks.request('review-policy', { ...submitted, expected_policy_id: this.saved.id });
      this.callbacks.envelope(envelope);
      if (same(submitted, this.draft)) this.draft = selection(envelope.review_policy);
      this.callbacks.toast('Adoption policy saved. Subsequent verification uses this recorded authorization.');
    } catch (error) { this.callbacks.notify(error.message, 'error'); }
    finally { this.busy = false; this.refresh(); }
  }
}
