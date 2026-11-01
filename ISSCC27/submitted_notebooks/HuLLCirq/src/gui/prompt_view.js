import { element as el } from './dom.js';

/** Readable, lossless presentation. Headers are UI labels, message text is untouched. */
export function promptTranscript(messages = []) {
  return messages.map((message, index) => `--- Message ${index + 1}: ${message.role || 'unknown'} ---\n${typeof message.content === 'string' ? message.content : JSON.stringify(message.content, null, 2)}`).join('\n\n');
}

export function instructionView(instruction, { prefix = 'prompt', title = 'Complete repair instruction' } = {}) {
  return el('section', { class: 'prompt-instruction' },
    el('h4', { text: title }),
    el('pre', { class: 'prompt-text', text: instruction || 'No additional instruction was recorded.', 'data-testid': `${prefix}-instruction`, tabindex: 0 }));
}

export function promptMessagesView(context, { prefix = 'prompt', title = 'Full request messages', description = '', open = true } = {}) {
  const messages = context?.messages || [];
  return el('details', { class: 'prompt-messages', open, 'data-testid': `${prefix}-messages` },
    el('summary', { text: `${title} · ${messages.length} message(s)` }),
    description ? el('p', { text: description }) : null,
    ...messages.map((message, index) => el('section', { class: 'prompt-message' },
      el('h4', { text: `${index + 1} · ${message.role || 'unknown'}` }),
      el('pre', { class: 'prompt-text', text: typeof message.content === 'string' ? message.content : JSON.stringify(message.content, null, 2), 'data-testid': `${prefix}-message-${index}`, tabindex: 0 }))),
    !messages.length ? el('p', { text: 'No request messages were saved in this record.' }) : null);
}

export function repairOutcomeLabel(value) {
  const outcome = typeof value === 'string' ? value : value?.outcome;
  return ({ unchanged: 'RTL unchanged', same_diagnostic: 'Same problem remains', new_diagnostic: 'Diagnostics changed · inspect remaining problems', passed: 'Synthesis passed · verify behavior in S06', no_baseline: 'First recorded attempt', not_comparable: 'Comparison unavailable' })[outcome] || 'Not compared yet';
}

/** Display-only compatibility for older previews. Never rewrites their prompt. */
export function repairProblemProjection(item) {
  if (item?.repair_explanation) return item.repair_explanation;
  const guidance = item?.repair_guidance || {}, evidence = guidance.evidence || {};
  const diagnostics = evidence.actionable_diagnostics || evidence.diagnostics || [];
  const used = new Set();
  const issues = diagnostics.map(diagnostic => {
    const target = (diagnostic.target || '').split('.').at(-1).replace(/^\\/, '');
    const matching = (guidance.changes || []).filter(change => (change.locations || []).some(location => {
      const direct = Number.isInteger(diagnostic.line) && location.line === diagnostic.line || diagnostic.source && location.source === diagnostic.source;
      const driver = change.rule_id === 'conflicting_driver_ownership' && /conflicting\s+drivers/i.test(diagnostic.raw_message || diagnostic.message || '') &&
        /^[A-Za-z_$][\w$]*$/.test(target) && new RegExp(`^\\s*(?:assign\\s+)?${target.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\s*(?:<=|=)`).test(location.source || '');
      return direct || driver;
    }));
    matching.forEach(change => used.add(change));
    return { ...diagnostic, raw_message: diagnostic.raw_message || diagnostic.message || 'Diagnostic text not recorded.',
      code_context: diagnostic.source ? [{ line: diagnostic.line, source: diagnostic.source, is_error_line: true }] : [],
      explanation: matching.flatMap(change => change.facts?.length ? change.facts : change.cause ? [`Model-proposed cause (not validated): ${change.cause}`] : []), actions: matching.flatMap(change => change.actions || []),
      preserve: matching.flatMap(change => change.preserve || []), assumptions: matching.flatMap(change => change.assumptions || []),
      expected_result: matching.flatMap(change => textValues(change.expected_result)), related_locations: matching.flatMap(change => change.locations || []),
      confidence: matching.length && matching.every(change => change.confidence === 'confirmed') ? 'confirmed' : 'unknown' };
  });
  return { version: 'legacy-guidance-display', source: guidance.source || {}, comparison: guidance.repeat_status || {},
    issues, unmatched_proposals: (guidance.changes || []).filter(change => !used.has(change)), previous_instruction: guidance.recent_attempts?.[0] || null,
    limits: 'Earlier preview: source excerpts and proposals come from its saved guidance. No new analysis or model request was performed.' };
}

const textValues = values => Array.isArray(values) ? values : values ? [values] : [];

/** Compact actionable facts. All provider, RTL, and diagnostic text stays literal. */
export function repairProblemsView(item, { prefix = 'repair-problems', current = false, onEdit, onAnalyze, onInspect, onReadGuidance, disabled = false } = {}) {
  const projection = repairProblemProjection(item), source = projection.source || {}, comparison = projection.comparison || {};
  const previous = projection.previous_instruction || {}, issues = projection.issues || [];
  const list = (heading, values, suffix) => textValues(values).length ? el('section', {}, el('h5', { text: heading }),
    el('ul', { 'data-testid': `${prefix}-${suffix}` }, ...textValues(values).map(value => el('li', { text: typeof value === 'string' ? value : JSON.stringify(value) })))) : null;
  const outcome = comparison.outcome;
  const comparisonText = outcome === 'unchanged' ? 'Previous repair returned identical RTL. The requested changes were not applied.' :
    outcome === 'same_diagnostic' ? 'RTL changed, but the same source-backed diagnostic remains.' :
    comparison.explanation || repairOutcomeLabel(comparison);
  const nodeName = item.node_name || item.node_id || source.node_id;
  const previousId = previous.base_job_id || comparison.base_candidate_id || comparison.previous_candidate_id;
  const currentId = source.candidate_id || item.base_job_id;
  const safeLink = (url, label) => typeof url === 'string' && url.startsWith('/api/') && !url.includes('\\') && !/[\r\n]/.test(url) ? el('a', { href: url, text: label, target: '_blank', rel: 'noopener' }) : null;
  return el('section', { class: `repair-problem-node${current ? '' : ' earlier-source'}`, 'data-testid': prefix },
    el('h4', { text: nodeName }),
    !current ? el('p', { class: 'generation-gate', 'data-testid': `${prefix}-stale`, text: 'Earlier preview · source or provider changed. Rebuild to inspect current problems; these saved facts do not describe the current request.' }) : null,
    el('p', { class: 'repair-problem-comparison', 'data-testid': `${prefix}-comparison`, text: comparisonText }),
    el('p', { class: 'prompt-metadata', text: `Candidate ${currentId || 'Not recorded'} · S05 ${source.run_id || item.source_workflow_run_id || 'Not recorded'}` }),
    ...issues.map((issue, index) => {
      const diagnostic = issue.diagnostic || issue, line = diagnostic.line ?? issue.line, sourceText = diagnostic.source ?? issue.source;
      const context = issue.code_context || [];
      return el('section', { class: 'repair-problem-issue', 'data-testid': `${prefix}-issue-${index}` },
        el('h5', { text: `Unresolved problem ${index + 1}${Number.isInteger(line) ? ` · candidate.v:${line}` : ' · location not recorded'}` }),
        el('pre', { class: 'repair-problem-diagnostic', 'data-testid': `${prefix}-diagnostic-${index}`, text: diagnostic.raw_message || diagnostic.message || issue.raw_message || 'Diagnostic text not recorded.', tabindex: 0 }),
        context.length || sourceText ? el('pre', { class: 'prompt-text repair-problem-code', 'data-testid': `${prefix}-source-${index}`, tabindex: 0,
          text: context.length ? context.map(row => `${row.is_error_line || row.is_target || row.line === line ? '>' : ' '} ${Number.isInteger(row.line) ? row.line : '?'} | ${row.source ?? row.text ?? ''}`).join('\n') : `${Number.isInteger(line) ? line : '?'} | ${sourceText}` }) :
          el('p', { class: 'scope-note', text: 'No source location was recorded. Inspect the complete S05 log; no line or cause is inferred here.' }),
        list(issue.confidence === 'confirmed' ? 'Source-backed cause' : 'Proposed explanation · not proven', issue.explanation || issue.facts, `explanation-${index}`),
        list('Correction to request', issue.actions, `actions-${index}`),
        !textValues(issue.actions).length ? el('p', { class: 'generation-gate', text: 'No qualified correction is available for this diagnostic. Inspect the source and log, or preview model-assisted guidance.' }) : null,
        list('Keep unchanged', issue.preserve, `preserve-${index}`),
        list('Uncertainty', issue.assumptions, `assumptions-${index}`),
        list('Expected diagnostic change · proposed, not verified', issue.expected_result, `expected-${index}`),
        issue.related_locations?.length ? el('details', {}, el('summary', { text: 'Related source locations' }), el('pre', { class: 'prompt-text', text: issue.related_locations.map(row => `${row.line ?? '?'} | ${row.source ?? row.text ?? ''}`).join('\n'), tabindex: 0 })) : null);
    }),
    !issues.length ? el('p', { class: 'generation-gate', text: 'Diagnostic details are missing from this saved preview. Inspect the complete S05 record or rebuild the preview to identify the problem before editing the repair instruction.' }) : null,
    projection.unmatched_proposals?.length ? el('details', { 'data-testid': `${prefix}-unmatched-proposals` },
      el('summary', { text: 'Other saved proposals · diagnostic association not established' }),
      ...projection.unmatched_proposals.map((proposal, index) => el('section', {},
        proposal.cause ? el('p', { text: `Model-proposed cause (not validated): ${proposal.cause}` }) : null,
        list('Saved proposed changes', proposal.actions, `unmatched-actions-${index}`),
        list('Uncertainty', proposal.assumptions, `unmatched-uncertainty-${index}`),
        list('Expected diagnostic change · proposed, not verified', proposal.expected_result, `unmatched-expected-${index}`)))) : null,
    projection.diagnostic_comparison ? el('details', { 'data-testid': `${prefix}-diagnostic-comparison` },
      el('summary', { text: 'Previous vs current diagnostics' }),
      list('Still reported', projection.diagnostic_comparison.remaining || projection.diagnostic_comparison.unchanged, 'still-reported'),
      list('Newly reported', projection.diagnostic_comparison.newly_reported, 'newly-reported'),
      list('Not reported this time · does not prove resolution', projection.diagnostic_comparison.not_reported, 'not-reported'),
      projection.diagnostic_comparison.limits ? el('p', { class: 'scope-note', text: textValues(projection.diagnostic_comparison.limits).join(' ') }) : null) : null,
    el('div', { class: 'provider-actions' },
      onInspect && previousId ? el('button', { type: 'button', text: 'Inspect previous RTL', 'data-testid': `${prefix}-previous`, onclick: () => onInspect(previousId, item.node_id) }) : null,
      onInspect && currentId ? el('button', { type: 'button', text: 'Inspect current RTL', 'data-testid': `${prefix}-current`, onclick: () => onInspect(currentId, item.node_id) }) : null,
      safeLink(comparison.previous_rtl_url, 'Open previous saved record'), safeLink(comparison.current_rtl_url, 'Open current saved record'),
      safeLink(item.repair_guidance?.evidence?.full_record_url, 'Open complete S05 record')),
    Object.hasOwn(previous, 'diff') || previous.text || previous.instruction ? el('details', { 'data-testid': `${prefix}-previous-repair` },
      el('summary', { text: 'Previous instruction and full saved RTL diff' }),
      previous.text || previous.instruction ? el('pre', { class: 'prompt-text', text: previous.text || previous.instruction, tabindex: 0, 'data-testid': `${prefix}-previous-instruction` }) : null,
      Object.hasOwn(previous, 'diff') ? el('pre', { class: 'prompt-text', text: previous.diff || 'No differences · previous and current RTL are identical.', tabindex: 0, 'data-testid': `${prefix}-diff` }) : null) : null,
    el('div', { class: 'provider-actions repair-problem-actions' },
      onEdit ? el('button', { type: 'button', text: 'Edit repair instruction', 'data-testid': `${prefix}-edit`, disabled: disabled || !current, onclick: onEdit }) : null,
      onAnalyze ? el('button', { type: 'button', text: 'Preview model-assisted guidance', 'data-testid': `${prefix}-analyze`, disabled: disabled || !current, title: 'Preview only. Review the analysis request before explicitly starting it.', onclick: onAnalyze }) : null,
      onReadGuidance ? el('button', { type: 'button', text: 'Read repair guidance', 'data-testid': `${prefix}-read`, onclick: onReadGuidance }) : null),
    projection.limits ? el('p', { class: 'scope-note', text: textValues(projection.limits).join(' ') }) : null);
}

/** Facts and hypotheses remain distinct; source text is never interpreted as HTML. */
export function repairGuidanceView(guidance, { prefix = 'repair-guidance', title = 'Repair guidance' } = {}) {
  if (!guidance) return null;
  const source = guidance.source || {}, status = guidance.repeat_status || {}, changes = guidance.changes || [];
  const list = (heading, values) => values?.length ? el('section', {}, el('h5', { text: heading }), el('ul', {}, ...values.map(value => el('li', { text: typeof value === 'string' ? value : JSON.stringify(value) })))) : null;
  return el('section', { class: 'generation-recovery repair-guidance', 'data-testid': prefix },
    el('h4', { text: title }),
    el('p', { class: 'generation-gate', 'data-testid': `${prefix}-outcome`, text: `${repairOutcomeLabel(status)}${status.reconsideration_required ? ' · Reconsider the guidance before another repair.' : ''}` }),
    el('p', { class: 'prompt-metadata', text: `Candidate ${source.candidate_id || 'Not recorded'} · ${source.stage_id === 'local_netlist_simulation' ? 'S06' : 'S05'} ${source.run_id || 'Not recorded'} · guidance ${guidance.guidance_sha256 || 'Not recorded'}` }),
    guidance.analysis_required && !guidance.analysis_reviewed ? el('p', { text: 'No qualified repair rule matched. Add a concrete correction, or explicitly request model-assisted guidance below. No analysis request has been sent by preparing this preview.' }) : null,
    ...changes.map((change, index) => el('section', { class: 'prompt-node', 'data-testid': `${prefix}-change-${index}` },
      el('h5', { text: `${index + 1}. ${change.rule_id || change.cause || 'Suggested correction'} · ${change.confidence === 'confirmed' ? 'Rule-backed facts' : 'Hypothesis · requires tool checks'}` }),
      list('Observed facts', change.facts), list('Source locations', change.locations), list('Required changes', change.actions), list('Preserve', change.preserve), list('Assumptions / uncertainty', change.assumptions),
      change.expected_result ? el('p', { text: `Expected diagnostic change: ${change.expected_result}` }) : null)),
    el('details', { 'data-testid': `${prefix}-requirements` }, el('summary', { text: '1 · Original saved requirements and connected edges' }), el('pre', { class: 'prompt-text', text: JSON.stringify(guidance.original_requirements || {}, null, 2), tabindex: 0 })),
    el('details', { 'data-testid': `${prefix}-evidence` }, el('summary', { text: '2 · Actual diagnostic and source evidence' }), el('pre', { class: 'prompt-text', text: JSON.stringify({ source, evidence: guidance.evidence || {} }, null, 2), tabindex: 0 })),
    el('details', { 'data-testid': `${prefix}-attempts` }, el('summary', { text: `3 · Recent repair attempts (${guidance.recent_attempts?.length || 0})` }),
      ...(guidance.recent_attempts || []).map((attempt, index) => el('section', { class: 'prompt-node' }, el('h5', { text: `${index + 1}. ${attempt.job_id || 'Attempt'} · ${repairOutcomeLabel(attempt.outcome)}` }), el('pre', { class: 'prompt-text', text: JSON.stringify(attempt, null, 2), tabindex: 0 }))),
      !guidance.recent_attempts?.length ? el('p', { text: 'No comparable earlier repair was recorded.' }) : null),
    guidance.prompt_projection ? el('p', { class: 'scope-note', text: `Prompt history: ${guidance.prompt_projection.mode}. History excerpts fit the context budget; complete saved attempts remain available above. The current contract and RTL are retained.` }) : null,
    el('p', { class: 'scope-note', text: 'The current RTL and complete repair instruction are shown separately below. Guidance proposes changes; S05 synthesis and S06 behavior checks determine their result.' }));
}
