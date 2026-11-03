"""A study-specific cumulative agent budget around the existing dispatcher."""
from __future__ import annotations

import math
import os
import time
from pathlib import Path

from chip_nebula.adapters.pool_manager import AgentPoolManager
from chip_nebula.models.task_manifest import AgentResult
from chip_nebula.taskgraph_run_controls import initialize_timeout_control
from study_protocol import write_json
from study_checks import DevelopmentChecks


class BudgetPool(AgentPoolManager):
    def __init__(self, record, seconds=1200, *, total_deadline=None, check_ledger=None):
        super().__init__(default_framework='codex', force_framework=True)
        self.record = Path(record)
        self.limit = seconds
        self.deadline = total_deadline
        self.used = 0.0
        self.dispatches = []
        self.check_ledger = check_ledger

    def dispatch(self, task, workspace, blocking=True, project_root=None):
        remaining = self.limit - self.used
        if self.deadline is not None:
            remaining = min(remaining, self.deadline - time.monotonic())
        if remaining < 1:
            return AgentResult(success=False, error='Frozen cumulative study budget exhausted',
                               execution_log='Error-Class: study_budget_exhausted')
        task.timeout = max(1, math.floor(remaining))
        initialize_timeout_control(Path(task.timeout_control_path), run_id=task.run_id, base_timeout=task.timeout)
        started = time.monotonic()
        try:
            os.environ['CHIP_STUDY_READONLY'] = '["rtl", "tb"]' if 'verifier' in task.assigned_agent else '["tb"]'
            if self.check_ledger:
                with DevelopmentChecks(workspace, self.check_ledger, task.run_id) as checks:
                    os.environ['CHIP_STUDY_CHECK_SOCKET'] = str(checks.socket)
                    return super().dispatch(task, workspace, blocking=blocking, project_root=project_root)
            return super().dispatch(task, workspace, blocking=blocking, project_root=project_root)
        finally:
            os.environ.pop('CHIP_STUDY_CHECK_SOCKET', None)
            elapsed = time.monotonic() - started
            self.used += elapsed
            self.dispatches.append({'attempt': task.run_id, 'role': task.assigned_agent,
                                    'allocated_seconds': task.timeout, 'elapsed_seconds': elapsed})
            write_json(self.record, {'limit_seconds': self.limit, 'used_agent_seconds': self.used,
                                     'dispatches': self.dispatches, 'extensions_allowed': False})
