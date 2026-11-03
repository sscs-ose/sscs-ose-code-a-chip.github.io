import { element as el, field } from './dom.js';

export const SYSTEM_DRAFT_KEYS = ['@global-integration', '@global-verification'];
const object = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const sameKeys = (value, keys) => object(value) && Object.keys(value).sort().join('\0') === [...keys].sort().join('\0');
const identifier = value => typeof value === 'string' && /^[A-Za-z_][A-Za-z0-9_$]*$/.test(value);

/** Reject rounded JSON integers before they can become a design input. */
export function parseExactJson(text) {
  for (const token of text.matchAll(/"(?:\\.|[^"\\])*"|(-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)/g)) {
    if (!token[1]) continue;
    const number = Number(token[1]);
    if (!Number.isFinite(number) || (Number.isInteger(number) && (!Number.isSafeInteger(number) || !/^-?\d+$/.test(token[1]))))
      throw new Error('Use plain safe JSON integers, or quoted decimal strings for wide values. Numeric values must not be rounded or silently rewritten.');
  }
  return JSON.parse(text);
}

export function nodePhysicalPorts(node) {
  return (node.ports || []).flatMap(port => {
    const base = { name: port.name, direction: port.direction, width: port.width, signed: port.signed };
    return port.protocol === 'valid_ready' ? [base,
      { name: `${port.name}_valid`, direction: port.direction, width: 1, signed: false },
      { name: `${port.name}_ready`, direction: port.direction === 'input' ? 'output' : 'input', width: 1, signed: false }] : [base];
  });
}

export function cycleTemplate(ports) {
  const values = direction => Object.fromEntries(ports.filter(port => port.direction === direction).map(port => [port.name, null]));
  return { kind: 'generic_cycle_vectors', version: 1, cycles: [
    { reset: 1, drive: values('input'), expect: values('output') },
    { reset: 0, drive: values('input'), expect: values('output') }] };
}

export function parseCycleInput(text, ports, { allowLegacy = false } = {}) {
  if (!text.trim()) return null;
  const value = parseExactJson(text);
  if (!object(value)) throw new Error('Expected a JSON object.');
  if (allowLegacy && value.kind !== 'generic_cycle_vectors') return value;
  if (!sameKeys(value, ['kind', 'version', 'cycles']) || value.kind !== 'generic_cycle_vectors' || value.version !== 1)
    throw new Error('Use only kind="generic_cycle_vectors", version=1 and cycles.');
  if (!Array.isArray(value.cycles) || value.cycles.length < 2 || value.cycles.length > 10000)
    throw new Error('Provide 2–10000 complete cycle rows.');
  const inputs = ports.filter(port => port.direction === 'input'), outputs = ports.filter(port => port.direction === 'output');
  if (!outputs.length) throw new Error('Declare at least one observable output first.');
  for (const [index, row] of value.cycles.entries()) {
    if (!sameKeys(row, ['reset', 'drive', 'expect']) || ![0, 1].includes(row.reset)) throw new Error(`Cycle ${index}: reset must be logical 0 or 1, with drive and expect objects.`);
    for (const [key, expected] of [['drive', inputs], ['expect', outputs]]) {
      if (!sameKeys(row[key], expected.map(port => port.name))) throw new Error(`Cycle ${index}: ${key} must name every declared physical ${key === 'drive' ? 'input' : 'output'}, and no others.`);
      for (const port of expected) {
        const number = row[key][port.name];
        if (!Number.isSafeInteger(port.width) || port.width < 1 || port.width > 4096 || typeof port.signed !== 'boolean') throw new Error('Declare valid port widths and signedness first.');
        const exact = Number.isSafeInteger(number) || typeof number === 'string' && /^(?:0|-?[1-9]\d*)$/.test(number);
        const integer = exact ? BigInt(number) : null;
        const low = port.signed ? -(1n << BigInt(port.width - 1)) : 0n, high = (1n << BigInt(port.width - (port.signed ? 1 : 0))) - 1n;
        if (!exact || integer < low || integer > high) throw new Error(`Cycle ${index}: ${port.name} needs an exact integer or quoted decimal integer within its declared ${port.signed ? 'signed' : 'unsigned'} ${port.width}-bit range. No null, X/Z or don't-care values.`);
      }
    }
  }
  if (value.cycles[0].reset !== 1 || !value.cycles.some(row => row.reset === 0)) throw new Error('Assert reset in the first cycle and provide non-reset operation.');
  if (inputs.length && !value.cycles.slice(1).some(row => inputs.some(port => BigInt(row.drive[port.name]) !== BigInt(value.cycles[0].drive[port.name]))))
    throw new Error('Change at least one physical input after the first reset cycle.');
  return value;
}

export function parseIntegrationInput(text, settings) {
  if (!text.trim()) return null;
  const value = parseExactJson(text);
  if (!object(value) || !Array.isArray(value.public_ports) || typeof value.behavior !== 'string' || !value.behavior.trim())
    throw new Error('Provide public_ports and nonempty behavior. Clock/reset come from Global Settings.');
  const names = new Set([settings.clock_name, settings.reset_name]);
  for (const port of value.public_ports) {
    if (!sameKeys(port, ['name', 'direction', 'width', 'signed']) || !identifier(port.name) || !['input', 'output'].includes(port.direction) || !Number.isSafeInteger(port.width) || port.width < 1 || port.width > 4096 || typeof port.signed !== 'boolean')
      throw new Error('Each physical public port needs name, input/output direction, integer width 1–4096 and boolean signed.');
    if (names.has(port.name)) throw new Error('Public names must be unique; do not repeat the automatic clock/reset.');
    names.add(port.name);
  }
  if (!value.public_ports.some(port => port.direction === 'output')) throw new Error('Declare at least one public output.');
  return value;
}

/** Only explicit Apply mutates the design; typing retains text in browser drafts. */
export function evaluateStructuredDraft(draft, value, parse) {
  if (!draft) return null;
  let parsed = null, error = '';
  try { parsed = parse(draft.text); } catch (reason) { error = `${reason.message} Text retained; no design input was changed.`; }
  return { text: draft.text, error, pending: !!error || JSON.stringify(parsed) !== JSON.stringify(value ?? null) };
}

export function structuredInput({ key, id, testId = id, title, value, drafts, parse, apply, changed, gate = () => '', template, hint }) {
  const savedText = value == null ? '' : JSON.stringify(value, null, 2);
  const status = el('p', { class: 'verification-json-status', 'data-testid': `${testId}-status` });
  let control, applyButton, resetButton;
  const current = () => Object.hasOwn(drafts, key) ? drafts[key] : null;
  const evaluated = () => evaluateStructuredDraft(current(), value, parse);
  const update = () => {
    const draft = evaluated(), blocked = gate();
    status.textContent = draft?.error || (draft?.pending ? 'Browser text draft retained. Apply explicitly, then Save design to freeze this input.' : value == null ? 'No saved structured contract. Select a template or enter independent requirements.' : 'Applied design input. Save design before execution; saved results remain bound to their original inputs.');
    applyButton.disabled = !!blocked || !draft?.pending || !!draft.error;
    applyButton.title = blocked || draft?.error || 'Apply this text to the design draft. This does not save or run tools.';
    resetButton.disabled = !!blocked || !draft;
    control.disabled = !!blocked;
  };
  const edit = text => {
    if (current()?.text === text) return;
    const draft = evaluateStructuredDraft({ text }, value, parse);
    Object.defineProperty(drafts, key, { value: draft, enumerable: true, configurable: true, writable: true });
    update(); changed();
  };
  const input = field(title, current()?.text ?? savedText, edit, { id, 'data-testid': testId, multiline: true, rows: 14, spellcheck: false, hint });
  control = input.querySelector('textarea');
  applyButton = el('button', { type: 'button', text: 'Apply verification input', 'data-testid': `${testId}-apply`, onclick: () => {
    const draft = evaluated(); if (gate() || !draft?.pending || draft.error) return;
    let parsed;
    try { parsed = parse(draft.text); } catch (reason) { draft.error = `${reason.message} Text retained; no design input was changed.`; update(); changed(); return; }
    apply(parsed); value = parsed; delete drafts[key]; update(); changed();
  } });
  resetButton = el('button', { type: 'button', text: 'Discard unapplied text', 'data-testid': `${testId}-discard`, onclick: () => {
    if (gate()) return; delete drafts[key]; control.value = value == null ? '' : JSON.stringify(value, null, 2); update(); changed();
  } });
  const example = template ? el('button', { type: 'button', text: 'Load unfilled generic template', 'data-testid': `${testId}-template`, disabled: !!gate(), onclick: () => {
    if (gate()) return; const text = JSON.stringify(template(), null, 2); control.value = text; edit(text);
  } }) : null;
  update();
  return el('div', { class: 'verification-json wide' }, input, el('div', { class: 'provider-actions' }, applyButton, resetButton, example), status);
}
