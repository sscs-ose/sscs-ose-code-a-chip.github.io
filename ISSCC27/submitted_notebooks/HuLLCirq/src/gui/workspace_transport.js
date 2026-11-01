/** Per-page workspace capability. Never share it through origin-wide cookies. */
let session = null;

export function setWorkspaceSession(value) { session = value || null; }
export function workspaceSession() { return session; }

export function sessionURL(input) {
  const url = new URL(input, location.href);
  if (url.origin !== location.origin) return input;
  if (url.origin === location.origin && url.pathname.startsWith('/api/') && session) url.searchParams.set('session_id', session);
  return `${url.pathname}${url.search}${url.hash}`;
}

export async function sessionFetch(input, init = {}) {
  const captured = session;
  const url = new URL(input, location.href);
  const headers = new Headers(init.headers || {});
  if (url.origin === location.origin && url.pathname.startsWith('/api/') && captured) headers.set('X-HuLLCirq-Session', captured);
  const response = await fetch(input, { ...init, headers });
  if (captured !== session) throw new Error('The project context changed while this request was running. Its response was ignored.');
  return response;
}
