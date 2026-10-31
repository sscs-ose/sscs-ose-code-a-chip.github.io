"""Explicit recovery reset preserves history/session and does not affect later checkpoints."""
import json
from types import SimpleNamespace
from unittest.mock import patch
from chip_nebula.taskgraph.domain import AttemptStatus
from chip_nebula.taskgraph.static_store import StaticTaskGraphStore

old = SimpleNamespace(id='old', status=AttemptStatus.SUCCEEDED, session_id='old-session',
    workspace_commit='old-checkpoint', diagnostics={'workspace_base_commit': 'old-base',
    'changed_paths': ['spec/requirements.ledger.json']})

def site(attempts):
    store = object.__new__(StaticTaskGraphStore)
    store.get_task = lambda task_id: object()
    rows = [{'document': json.dumps({'id': a.id})} for a in attempts]
    store._connection = SimpleNamespace(execute=lambda *args: SimpleNamespace(fetchall=lambda: rows))
    by_id = {a.id: a for a in attempts}
    with patch('chip_nebula.taskgraph.static_store._attempt_from', side_effect=lambda row: by_id[row['id']]):
        return store.recoverable_site('review')

for value in (None, True, 0, 'false'):
    failure = SimpleNamespace(id='failed', status=AttemptStatus.FAILED, session_id='',
        workspace_commit='', diagnostics={'restore_saved_wip': value})
    assert site([failure, old]).workspace_commit == 'old-checkpoint'
failure.diagnostics['restore_saved_wip'] = False
reset = site([failure, old])
assert reset.session_id == 'old-session' and reset.workspace_commit == ''
assert reset.base_commit == '' and reset.modified_paths == ()
assert old.workspace_commit == 'old-checkpoint' and old.diagnostics['changed_paths']
new = SimpleNamespace(id='new', status=AttemptStatus.SUCCEEDED, session_id='new-session',
    workspace_commit='new-checkpoint', diagnostics={'workspace_base_commit': 'new-base',
    'changed_paths': ['spec/requirements.review.json']})
assert site([new, failure, old]).workspace_commit == 'new-checkpoint'
print('RECOVERY_RESET_PASS: explicit boolean only, session/history retained, later checkpoint resumes normally')
