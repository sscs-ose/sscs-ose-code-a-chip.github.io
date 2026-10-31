import threading
from pathlib import Path
from typing import Dict, Optional

from chip_nebula.models.task_manifest import TaskManifest, AgentResult
from chip_nebula.adapters.base import AgentFrameworkAdapter, MockAgentFrameworkAdapter
from chip_nebula.adapters.opencode import OpenCodeAdapter
from chip_nebula.adapters.claude_code import ClaudeCodeAdapter
from chip_nebula.adapters.qoder_cli import QoderCLIAdapter
from chip_nebula.adapters.codex import CodexAdapter


_DEFAULT_LIMITS = {
    "rtl-designer": 4,
    "lint-checker": 3,
    "ut-verifier": 3,
    "bes-analyzer": 2,
    "testbench-generator": 3,
    "integrator": 2,
    "design-reviewer": 5,
    "verif-reviewer": 5,
    "architect": 2,
    "st-env-owner": 2,
    "st-functional-verifier": 3,
    "st-performance-verifier": 2,
}


class AgentPoolManager:
    def __init__(self, default_framework: str = "opencode", *, force_framework: bool = False):
        self.default_framework = default_framework
        self.force_framework = force_framework
        self.adapters: Dict[str, AgentFrameworkAdapter] = {
            "opencode": OpenCodeAdapter(),
            "claude-code": ClaudeCodeAdapter(),
            "claudecode": ClaudeCodeAdapter(),
            "qoder-cli": QoderCLIAdapter(),
            "qodercli": QoderCLIAdapter(),
            "codex": CodexAdapter(),
            "mock": MockAgentFrameworkAdapter(),
        }
        self.max_concurrent = dict(_DEFAULT_LIMITS)
        # One semaphore per agent type; counting semaphores bound concurrency
        # without the race conditions of defaultdict+int increments.
        self._semaphores: Dict[str, threading.Semaphore] = {
            agent: threading.Semaphore(slots)
            for agent, slots in self.max_concurrent.items()
        }
        self._sem_lock = threading.Lock()
        self._session_lock = threading.Lock()
        self._active_sessions: Dict[str, str] = {}

    def _sem_for(self, agent_type: str) -> threading.Semaphore:
        with self._sem_lock:
            sem = self._semaphores.get(agent_type)
            if sem is None:
                slots = self.max_concurrent.get(agent_type, 1)
                sem = threading.Semaphore(slots)
                self._semaphores[agent_type] = sem
            return sem

    def dispatch(
        self, task: TaskManifest, workspace: Path,
        blocking: bool = True, project_root: Optional[Path] = None,
    ) -> AgentResult:
        framework = self.default_framework if self.force_framework else (
            task.framework if task.framework in self.adapters else self.default_framework
        )
        adapter = self.adapters[framework]
        agent_type = task.assigned_agent

        sem = self._sem_for(agent_type)
        if not sem.acquire(blocking=blocking):
            raise RuntimeError(
                f"Agent pool saturated for '{agent_type}' and non-blocking dispatch requested"
            )
        session_id = task.session_id or ""
        if session_id:
            with self._session_lock:
                self._active_sessions[session_id] = framework
        try:
            return adapter.execute(task, workspace, project_root=project_root)
        finally:
            sem.release()
            if session_id:
                with self._session_lock:
                    self._active_sessions.pop(session_id, None)

    def terminate(self, session_id: str) -> None:
        """Route a termination request to the adapter that owns ``session_id``.

        Broadcast to every adapter — each one internally checks whether it
        actually holds this session and is a no-op otherwise. This avoids
        the _active_sessions tracking gap when the adapter generates a new
        session ID after dispatch has already been called.
        """
        if not session_id:
            return None
        for adapter in self.adapters.values():
            adapter.terminate(session_id)
        return None
