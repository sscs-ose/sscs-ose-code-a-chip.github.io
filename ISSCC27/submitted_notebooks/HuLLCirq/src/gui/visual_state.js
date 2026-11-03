/** Presentation only: these labels never grant execution or acceptance. */
const SYMBOLS = Object.freeze({ complete: 'check', working: 'progress', attention: 'alert', error: 'error', blocked: 'lock', pending: 'circle' });
const visual = (kind, label, detail = '') => ({ kind, label, detail, symbol: SYMBOLS[kind] });
const text = value => typeof value === 'string' ? value : '';

function reasonText(value) {
  if (typeof value === 'string') return value;
  return text(value?.message) || text(value?.summary) || text(value?.reason) || text(value?.title);
}

function nodeProgress(stage, partial) {
  const accepted = partial?.accepted ?? partial?.accepted_node_count ?? stage?.accepted_node_count;
  const total = partial?.total ?? partial?.required_node_count ?? stage?.required_node_count;
  if (Number.isInteger(total) && total > 0) {
    if (Number.isInteger(accepted) && accepted >= 0 && accepted < total)
      return `${accepted}/${total} nodes adopted`;
    if (accepted !== total) return `Current adoption count is unavailable (${total} nodes required)`;
  }
  return typeof partial === 'string' ? partial : partial === true ? 'Some nodes still need work' : '';
}

const USER_STATES = Object.freeze({
  'Not run': 'pending', Running: 'working', Complete: 'complete',
  'Review required': 'attention', Failed: 'error',
});
const primaryStatus = value => ({ 'Not Run': 'Not run', 'Not started': 'Not run',
  Queued: 'Running', Starting: 'Running', Stopping: 'Running', Cancelling: 'Running',
  Completed: 'Complete', 'Awaiting Review': 'Review required',
  Cancelled: 'Failed', Interrupted: 'Failed' }[value] || value);
const userVisual = (status, detail) => ({ ...visual(USER_STATES[status], status, detail), status });

/** Five user-facing states only. Raw tool and review fields remain in evidence. */
export function stageVisualState(stage, { blockedReason = '', dirty = false, partial = null, overlay = null } = {}) {
  const execution = stage?.execution_status;
  const validation = stage?.stage_validation?.validation_status || stage?.effective_validation_status || stage?.validation_status;
  const review = stage?.review_status;
  const freshness = stage?.freshness;
  const progress = nodeProgress(stage, partial);
  const blocker = reasonText(blockedReason) || reasonText(stage?.blocked_reason);
  const hasResult = !!stage && (['Completed', 'Failed', 'Cancelled', 'Interrupted'].includes(execution) || validation === 'Passed' || review === 'Accepted');
  const progressDetail = detail => [progress, detail].filter(Boolean).join('. ');
  const overlayStatus = primaryStatus(overlay?.status || overlay?.label);

  if (overlay?.invalidated) return userVisual('Not run', overlay.detail || 'Earlier evidence is retained. Rerun this stage after the new upstream result.');
  if (USER_STATES[overlayStatus]) return userVisual(overlayStatus, overlay.detail || (overlayStatus === 'Running' ? 'The requested operation is starting or running.' : 'Inspect this stage for the next action.'));
  if (['Running', 'Queued', 'Starting', 'Stopping', 'Cancelling'].includes(execution))
    return userVisual('Running', progressDetail('This stage has an active operation.'));
  if (dirty) return userVisual('Not run', 'Unsaved changes. Save the current design before running this stage. Earlier evidence is retained.');
  if (freshness === 'Stale' || stage?.invalidated)
    return userVisual('Not run', 'Earlier evidence is retained. This stage has not run for the current upstream result.');
  if (hasResult && freshness !== 'Current')
    return userVisual('Not run', 'Earlier evidence is retained. Current input has not been established for this recorded result.');
  if (['Failed', 'Declined'].includes(execution) || validation === 'Failed')
    return userVisual('Failed', progressDetail('Inspect the failed checks, then repair or rerun this stage.'));
  if (['Request Changes', 'Changes Requested', 'Rejected', 'Returned', 'Declined'].includes(review))
    return userVisual('Failed', progressDetail('Changes were requested. Read the review feedback before repairing or rerunning this stage.'));
  if (['Cancelled', 'Interrupted'].includes(execution))
    return userVisual('Failed', `${execution}. Inspect the saved attempt, then retry or reconnect explicitly.`);
  if (stage?.implemented === false)
    return userVisual('Not run', blocker || 'This stage is not implemented for the current flow.');
  if (validation === 'Unsupported')
    return userVisual(execution === 'Completed' ? 'Failed' : 'Not run', blocker || 'Required verification support is unavailable.');
  if (stage?.review_required === true && execution === 'Completed')
    return userVisual('Review required', progressDetail('Review the completed result to accept it or request changes.'));
  if (!progress && execution === 'Completed' && validation === 'Passed' && review === 'Accepted' && freshness === 'Current')
    return userVisual('Complete', 'Required checks passed and the result is adopted for the current input.');
  if (progress) return userVisual('Not run', progressDetail('Remaining nodes have not completed this stage.'));
  if (execution === 'Completed' && validation === 'Passed' && review === 'Awaiting Review')
    return userVisual('Review required', 'Checks passed. Review the completed result to accept it or request changes.');
  if (blocker) return userVisual('Not run', blocker);
  if (execution === 'Completed')
    return userVisual('Not run', 'Execution finished, but required checks have not completed. Inspect the saved attempt and next action.');
  if (stage?.ready === false)
    return userVisual('Not run', 'Complete the prerequisites shown in this stage.');
  return userVisual('Not run', 'This stage has not run. Inspect its inputs and next action.');
}

function normalEndpoint(value) {
  try {
    const url = new URL(value);
    if (url.username || url.password || url.search || url.hash) return null;
    const host = ['localhost', '127.0.0.1'].includes(url.hostname) ? 'loopback' : url.hostname;
    return `${url.protocol}//${host}:${url.port || (url.protocol === 'https:' ? '443' : '80')}${url.pathname.replace(/\/+$/, '')}`;
  } catch { return null; }
}

function managedProfile(profile, runtime) {
  if (profile?.execution_location !== 'Local') return false;
  const endpoint = normalEndpoint(profile?.base_url);
  const managed = normalEndpoint(runtime?.endpoint || 'http://127.0.0.1:11435/v1');
  return !!endpoint && endpoint === managed;
}

/** Model-list connection evidence, distinct from local process and circuit status. */
export function connectionVisualState({ probe = null, profileRevisionId = null, profile = null, runtime = null, runtimeError = null, busy = false, readOnly = false, profileDirty = false } = {}) {
  if (readOnly) return visual('pending', 'Recorded only', 'This snapshot does not establish a live LLM connection.');
  if (!profileRevisionId || !profile) return visual('pending', 'Not configured', 'Save an LLM provider profile in Global Settings.');
  if (profileDirty) return visual('attention', 'Unsaved settings', 'Save the edited provider settings, then test the current profile.');
  if (busy || ['Checking', 'Running'].includes(probe?.status))
    return visual('working', 'Checking', 'Checking the saved provider connection.');

  if (managedProfile(profile, runtime)) {
    if (['Starting', 'Stopping', 'Checking'].includes(runtime?.state))
      return visual('working', runtime.state, 'The matching local server is changing state.');
    if (runtimeError || ['Failed', 'Unavailable'].includes(runtime?.state))
      return visual('error', 'Server unavailable', reasonText(runtimeError) || reasonText(runtime?.error) || 'Inspect the local server controls in Global Settings.');
    if (runtime?.state === 'Stopped')
      return visual('pending', 'Offline', 'Start the local LLM in Global Settings, then test its connection.');
  }

  if (!probe || probe.profile_revision_id !== profileRevisionId)
    return visual('attention', 'Not tested', probe ? 'The provider profile changed. Test the current saved profile.' : 'Test the saved provider connection in Global Settings.');
  if (probe.selected_model_available === false)
    return visual('error', 'Model unavailable', reasonText(probe.error) || 'The selected model was not returned by this provider.');
  if (probe.status === 'Connected' && probe.selected_model_available === true)
    return visual('complete', 'Connected', 'The current profile passed its model-list connection test. Generation and circuit checks are separate.');
  if (probe.status === 'Failed' || probe.connected === false)
    return visual('error', 'Not connected', reasonText(probe.error) || 'Connection test failed. Inspect provider settings and test again.');
  if (probe.status === 'Cancelled') return visual('attention', 'Not tested', 'The connection test was cancelled.');
  return visual('attention', 'Not tested', 'A successful model-list test is required for the current profile.');
}
