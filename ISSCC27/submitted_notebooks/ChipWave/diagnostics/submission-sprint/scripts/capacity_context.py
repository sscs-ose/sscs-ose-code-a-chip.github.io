"""Reuse the public Codex adapter while binding resumptions to isolated roles."""
from __future__ import annotations

import json
import os
import shlex
import sys
import threading
import time
from pathlib import Path

from chip_nebula.adapters.codex import CodexAdapter
from chip_nebula.adapters.pool_manager import AgentPoolManager
from capacity_protocol import MODELS
from study_protocol import write_json

_ENVIRONMENT_LOCK = threading.Lock()


class IsolatedCodexAdapter(CodexAdapter):
    def __init__(self, private):
        super().__init__()
        self.private = Path(private)

    def _session_file_path(self, session_id):
        if not session_id or any(c not in "0123456789abcdef-" for c in session_id):
            raise ValueError("Invalid native session identity")
        files = list((self.private/"sessions").glob(f"*/*/*/*-{session_id}.jsonl"))
        if len(files) != 1:
            raise ValueError("Expected isolated context is missing or ambiguous; no silent reset")
        return files[0]

    def _session_exists(self, session_id):
        self._session_file_path(session_id)
        return True

    @staticmethod
    def _append_session_message(session_id, text):
        # Raw transcripts are measurement evidence; never add synthetic events.
        return None


class ContextPool(AgentPoolManager):
    """Context binding only; the live metering/tool wrapper is a separate prerequisite."""
    def __init__(self, private, record, model, runtime=None):
        if model not in MODELS.values():
            raise ValueError("Unapproved model")
        super().__init__(default_framework="codex", force_framework=True)
        self.adapters["codex"] = (ControlledCodexAdapter(private,runtime) if runtime
                                  else IsolatedCodexAdapter(private))
        self.record, self.model = Path(record), model
        self.runtime = dict(runtime) if runtime else None
        self.contexts = json.loads(self.record.read_text()) if self.record.exists() else {}

    def dispatch(self, task, workspace, blocking=True, project_root=None):
        if task.model != self.model or task.reasoning_effort != "high":
            raise ValueError("Role cannot change the frozen model or reasoning effort")
        reason=self.stop_reason()
        if reason:
            self.stop_workflow(project_root,reason)
            from chip_nebula.models.task_manifest import AgentResult
            return AgentResult(success=False,execution_log='Shared trial stopped: '+reason)
        role = task.assigned_agent
        task.session_id = self.contexts.get(role, "")
        task.reuse_session = True
        previous = set((Path(self.runtime['record'])/'invocations').glob('*')) if self.runtime else set()
        result = super().dispatch(task, workspace, blocking=blocking, project_root=project_root)
        if result.session_id:
            if task.session_id and result.session_id != task.session_id:
                raise ValueError("Existing role unexpectedly switched native context")
            if any(other != role and session == result.session_id for other, session in self.contexts.items()):
                raise ValueError("Distinct roles cannot share a native context")
            self.contexts[role] = result.session_id
            write_json(self.record, self.contexts)
        reason=self.stop_reason(after_dispatch=True)
        if self.runtime and not (set((Path(self.runtime['record'])/'invocations').glob('*'))-previous):
            reason=reason or 'runtime_infrastructure_error'
        if reason:self.stop_workflow(project_root,reason)
        return result

    def stop_reason(self, *, after_dispatch=False):
        if not self.runtime:return None
        root=Path(self.runtime['record'])
        if (root/'usage.json').exists():
            usage=json.loads((root/'usage.json').read_text())
            if not usage['valid']:return 'measurement_invalid'
            if usage['actual_tokens']>=usage['limit']:return 'token_budget'
        if (root/'clock.json').exists():
            clock=json.loads((root/'clock.json').read_text())
            if time.monotonic()-clock['start']-clock['physical_seconds']>=clock['active_limit']:
                return 'active_time_budget'
        if after_dispatch:
            invocations=sorted((root/'invocations').glob('*'))
            if not invocations or not (invocations[-1]/'result.json').exists():
                return 'runtime_infrastructure_error'
            result=json.loads((invocations[-1]/'result.json').read_text())
            if result.get('reason')!='native_exit' or result.get('exit_code')!=0:
                return result.get('reason','runtime_infrastructure_error') if result.get('reason')!='native_exit' else 'runtime_infrastructure_error'
        return None

    def stop_workflow(self, project, reason):
        from chip_nebula.taskgraph.static_store import StaticTaskGraphStore
        database=Path(project)/'.chip_nebula/shared/memory/taskgraph-v2.db' if project is not None else None
        if database is not None and database.exists():
            with StaticTaskGraphStore(database) as store:
                # Let the active attempt finish its receipt before the runner becomes quiescent.
                for task in store.list_tasks('capacity'):
                    store.pause_task(task.id,'Shared trial termination: '+reason)
        write_json(Path(self.runtime['record'])/'trial-stop.json',dict(reason=reason,
            model_calls_after_stop=0,scope='Resource/infrastructure termination, not an operator pause'))


class ControlledCodexAdapter(IsolatedCodexAdapter):
    """Keep public prompt/session/result handling; replace only its executable."""
    def __init__(self, private, runtime):
        super().__init__(private)
        self.runtime = dict(runtime)

    def execute(self, task, workspace, project_root=None):
        from capacity_tool_router import WRITABLE
        root = Path(self.runtime["record"]).resolve()
        wrapper = root/"adapter-bin"
        wrapper.mkdir(parents=True,exist_ok=True)
        config_path = root/"adapter-invocation.json"
        writable = tuple(name for name in WRITABLE
                         if name+"/**" in task.write_paths or name in task.write_paths)
        if not writable:
            raise ValueError("Public task must declare its permitted write roots")
        config = dict(self.runtime,private=str(self.private.resolve()),workspace=str(Path(workspace).resolve()),
                      project=str(Path(project_root or workspace).resolve()),model=task.model,
                      writable=writable, stage=task.stage, role=task.assigned_agent)
        executable = wrapper/"codex"
        script = Path(__file__).with_name("capacity_runtime.py")
        executable.write_text("#!/bin/sh\nexec "+shlex.join([
            sys.executable,str(script),"--adapter-config",str(config_path)])+' "$@"\n')
        executable.chmod(0o700)
        if not _ENVIRONMENT_LOCK.acquire(blocking=False):
            raise ValueError("Capacity roles must execute serially")
        old_path = os.environ["PATH"]
        try:
            write_json(config_path,config)
            os.environ["PATH"] = str(wrapper)+os.pathsep+old_path
            return super().execute(task,workspace,project_root=project_root)
        finally:
            os.environ["PATH"] = old_path
            _ENVIRONMENT_LOCK.release()
