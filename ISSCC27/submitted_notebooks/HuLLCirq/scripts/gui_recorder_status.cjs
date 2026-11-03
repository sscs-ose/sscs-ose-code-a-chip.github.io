/** Expected sidebar labels from the saved public five-state GUI contract.
 * This recorder helper grants no adoption and does not alter saved raw status.
 */
module.exports = function sidebarStatus(stage) {
  const execution = stage.execution_status;
  const validation = stage.stage_validation?.validation_status || stage.effective_validation_status || stage.validation_status;
  if (['Queued', 'Running', 'Starting', 'Stopping', 'Cancelling'].includes(execution)) return 'Running';
  const hasResult = ['Completed', 'Failed', 'Cancelled', 'Interrupted'].includes(execution) || validation === 'Passed' || stage.review_status === 'Accepted';
  if (stage.freshness === 'Stale' || stage.invalidated || (hasResult && stage.freshness !== 'Current')) return 'Not run';
  if (['Failed', 'Declined', 'Cancelled', 'Interrupted'].includes(execution) || validation === 'Failed'
      || ['Request Changes', 'Changes Requested', 'Rejected', 'Returned', 'Declined'].includes(stage.review_status)) return 'Failed';
  if (stage.implemented === false) return 'Not run';
  if (validation === 'Unsupported') return execution === 'Completed' ? 'Failed' : 'Not run';
  if (stage.review_required === true && execution === 'Completed') return 'Review required';
  if (Number.isInteger(stage.required_node_count) && stage.required_node_count > 0
      && stage.accepted_node_count !== stage.required_node_count) return 'Not run';
  const terminal = {
    'Completed|Passed|Accepted|Current': 'Complete',
    'Completed|Passed|Awaiting Review|Current': 'Review required',
  };
  return terminal[[execution, validation, stage.review_status, stage.freshness].join('|')] || 'Not run';
};
