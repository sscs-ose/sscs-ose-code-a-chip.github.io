/** Explicit review provenance. This declaration is not authentication. */
import { element as el, field } from './dom.js';

export const REVIEW_ACTOR_VERSION = 'hullcirq.review-actor.v1';
const namedRoutes = new Set(['review', 'generation/review', 'workflow/review', 'implementation-specs/review', 'global-generation/review']);
export const isReviewRoute = path => namedRoutes.has(path) || /^(?:global|physical|drc|lvs|postlayout)-workflow\/runs\/[^/]+\/review$/.test(path);

export function reviewActorLabel(record) {
  if (record?.actor === 'automation_policy') return 'authorized policy';
  if (record?.provenance?.version !== REVIEW_ACTOR_VERSION) return 'legacy operator label · actual operator unverified';
  return { human: 'human · self-declared', development_assistant: 'development assistant · self-declared', unspecified: 'operator not declared' }[record.actor] || 'operator unverified';
}

export function adoptionProvenance(record) {
  if (!record) return 'Inspect the exact saved adoption record for its origin.';
  if (record.actor === 'automation_policy') return `Accepted by authorized adoption policy ${record.provenance?.policy_id || record.policy_id || record.review_policy_id || ''}. This is a policy decision, not a manual human review.`;
  return `Accepted by explicit review · ${reviewActorLabel(record)}. Historical records are preserved without retrospectively asserting who operated the GUI.`;
}

export class ReviewOperator {
  constructor() { this.actor = ''; this.host = null; }
  reset() { this.actor = ''; if (this.host) this.render(this.host); }
  render(host) {
    this.host = host;
    host.replaceChildren(field('Review operator', this.actor, actor => { this.actor = actor; }, {
      id: 'review-operator', 'data-testid': 'review-operator',
      choices: [['', 'Select before recording a review'], ['human', 'Human'], ['development_assistant', 'Development assistant']],
      hint: 'Self-declared provenance for explicit review buttons only. No file or request is saved by changing this selection. Authorized automatic policy decisions remain separate.',
    }));
  }
  request(path, body, version) {
    if (body === undefined || !isReviewRoute(path)) return body;
    if (version !== REVIEW_ACTOR_VERSION) throw new Error('The service does not support accurate review-operator records. Restart the updated local service and reopen this system before reviewing.');
    if (!['human', 'development_assistant'].includes(this.actor)) throw new Error('Select Human or Development assistant in Review operator before recording this review. No review request was sent.');
    return { ...body, review_operator: { actor: this.actor } };
  }
}
