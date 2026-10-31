"""Small deterministic scheduler for fixed Tasks and dynamic Attempts."""

from __future__ import annotations

from .domain import Attempt, TaskState
from .static_store import StateConflict, StaticTaskGraphStore


class AttemptScheduler:
    def __init__(
        self, store: StaticTaskGraphStore, workflow_id: str,
        *, max_parallel_tasks: int = 12, framework: str = "", model: str = "",
        reasoning_effort: str = "",
    ) -> None:
        self.store = store
        self.workflow_id = workflow_id
        self.max_parallel_tasks = max_parallel_tasks
        self.framework = framework
        self.model = model
        self.reasoning_effort = reasoning_effort

    def ready_task_ids(self) -> tuple[str, ...]:
        return tuple(
            task.id for task in self.store.list_tasks(self.workflow_id)
            if self.store.task_state(task.id) == TaskState.READY
        )

    def claim(self, limit: int = 1) -> list[Attempt]:
        if limit < 1:
            return []
        active = sum(
            self.store.active_attempt(task.id) is not None
            for task in self.store.list_tasks(self.workflow_id)
        )
        allowance = min(limit, max(0, self.max_parallel_tasks - active))
        claimed: list[Attempt] = []
        for task_id in self.ready_task_ids():
            if len(claimed) >= allowance:
                break
            try:
                claimed.append(self.store.claim_attempt(
                    task_id, framework=self.framework, model=self.model,
                    reasoning_effort=self.reasoning_effort,
                ))
            except StateConflict:
                # Another scheduler may have won the transactional claim.
                continue
        return claimed
