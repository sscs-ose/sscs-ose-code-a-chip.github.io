/** DOM helpers. User input is always assigned as text or a property. */
import { sessionFetch, sessionURL } from './workspace_transport.js';

export function element(tag, attributes = {}, ...children) {
  const result = document.createElement(tag);
  for (const [key, value] of Object.entries(attributes)) {
    if (value === null || value === undefined || value === false) continue;
    if (key === 'class') result.className = value;
    else if (key === 'text') result.textContent = value;
    else if (key.startsWith('on') && typeof value === 'function') result.addEventListener(key.slice(2), value);
    else if ((key === 'href' || key === 'src') && typeof value === 'string' && value.startsWith('/api/')) result[key] = sessionURL(value);
    else if (key in result && !key.startsWith('aria-') && !key.startsWith('data-')) result[key] = value;
    else result.setAttribute(key, value === true ? '' : String(value));
  }
  for (const child of children.flat(Infinity)) {
    if (child === null || child === undefined || child === false) continue;
    result.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return result;
}

export function svgElement(tag, attributes = {}, ...children) {
  const result = document.createElementNS('http://www.w3.org/2000/svg', tag);
  for (const [key, value] of Object.entries(attributes)) {
    if (key === 'text') result.textContent = value;
    else if (key.startsWith('on') && typeof value === 'function') result.addEventListener(key.slice(2), value);
    else result.setAttribute(key, String(value));
  }
  for (const child of children.flat(Infinity)) if (child) result.append(child);
  return result;
}

export function field(label, value, onChange, options = {}) {
  const inputId = options.id || `field-${crypto.randomUUID()}`;
  const { hint, choices, multiline, ...attributes } = options;
  let control;
  if (choices) {
    control = element('select', { ...attributes, id: inputId });
    for (const choice of choices) {
      const [optionValue, optionLabel] = Array.isArray(choice) ? choice : [choice, choice];
      control.append(element('option', { value: optionValue, text: optionLabel }));
    }
    control.value = value ?? '';
  } else if (multiline) {
    control = element('textarea', { rows: 4, ...attributes, id: inputId, value: value ?? '' });
  } else {
    control = element('input', { type: 'text', ...attributes, id: inputId, value: value ?? '' });
  }
  control.addEventListener('change', () => onChange(control.type === 'checkbox' ? control.checked : control.value));
  // Text edits immediately become a draft, allowing Save to enable before blur.
  // Selects use their change event so rebuilding a related inspector never
  // interrupts keyboard navigation through the options.
  if (!choices) control.addEventListener('input', () => onChange(control.type === 'checkbox' ? control.checked : control.value));
  if (hint) control.setAttribute('aria-describedby', `${inputId}-hint`);
  return element('div', { class: `field${multiline ? ' wide' : ''}` },
    element('label', { htmlFor: inputId, text: label }), control,
    hint ? element('small', { id: `${inputId}-hint`, text: hint }) : null);
}

export function badge(text, tone = 'neutral') {
  // Old saved records retain their exact enum. It is not a sixth UI state.
  const label = typeof text === 'string' ? text.replace(/^Blocked(?=\s*(?:$|:))/i, 'Not run') : text;
  return element('span', { class: `badge ${tone}`, text: label });
}

export function downloadJson(value, filename) {
  const url = URL.createObjectURL(new Blob([`${JSON.stringify(value, null, 2)}\n`], { type: 'application/json' }));
  const link = element('a', { href: url, download: filename });
  document.body.append(link); link.click(); link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/** Keep authoritative JSON numbers as response text, without a JS Number round trip. */
export async function downloadJsonResponse(endpoint, filename, onError) {
  try {
    const response = await sessionFetch(endpoint, { cache: 'no-store', credentials: 'same-origin' });
    const source = await response.text();
    if (!response.ok) {
      let message = `Download failed (${response.status}).`;
      try { message = JSON.parse(source).error?.message || message; } catch { /* Use the status when an error body is not JSON. */ }
      throw new Error(message);
    }
    if (!response.headers.get('content-type')?.startsWith('application/json')) throw new Error('The download did not return JSON.');
    const url = URL.createObjectURL(new Blob([source], { type: 'application/json' }));
    const link = element('a', { href: url, download: filename });
    document.body.append(link); link.click(); link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  } catch (error) {
    if (onError) onError(error.message, 'error');
    else throw error;
  }
}
