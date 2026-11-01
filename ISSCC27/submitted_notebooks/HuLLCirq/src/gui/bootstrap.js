/** Surface module-load/startup failures instead of leaving a silent loading page. */
function recovery(message, failed = false) {
  if (document.documentElement.dataset.hullcirqReady === 'true') return;
  const screen = document.getElementById('startup-screen');
  if (screen) {
    screen.dataset.state = failed ? 'error' : 'waiting';
    screen.setAttribute('aria-busy', String(!failed));
    document.getElementById('startup-title').textContent = failed ? 'The workspace could not open' : 'Still opening your workspace';
    document.getElementById('startup-detail').textContent = message;
    document.getElementById('startup-retry').hidden = false;
    return;
  }
  const host = document.getElementById('message');
  if (!host) return;
  const text = document.createElement('span');
  text.textContent = message;
  const retry = document.createElement('button');
  retry.type = 'button'; retry.textContent = 'Retry opening workspace';
  retry.addEventListener('click', () => location.reload());
  host.replaceChildren(text, retry); host.hidden = false; host.className = 'message warning';
}

const watchdog = setTimeout(() => recovery('The workspace is taking longer to open. Keep waiting or retry; saved projects and browser drafts remain intact.'), 30000);
import('./app.js').catch(error => {
  console.error('HuLLCirq workspace startup failed', error);
  clearTimeout(watchdog);
  recovery('The workspace interface could not load. Make sure the local service is running, then retry.', true);
});
