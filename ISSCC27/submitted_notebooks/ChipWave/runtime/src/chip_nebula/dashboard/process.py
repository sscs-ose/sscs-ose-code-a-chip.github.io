from __future__ import annotations

import datetime
import json
import os
import signal
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Optional

from chip_nebula.project import get_chip_nebula_dir


def _cli_command() -> list[str]:
    """Return the CLI launcher for source and PyInstaller runtimes."""
    if getattr(sys, "frozen", False):
        return [sys.executable, "--cli"]
    return [sys.executable, "-m", "chip_nebula.cli.commands"]


class RunManager:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self._processes: dict[str, subprocess.Popen] = {}
        # A second dashboard/API process may attach to live runners recorded
        # by another process.  Attached runners are observable and explicitly
        # stoppable, but this manager must not kill them merely because its own
        # lifespan ends (for example a TestClient or a second Electron window).
        self._owned_run_ids: set[str] = set()
        self._features: dict[str, str] = {}
        self._frameworks: dict[str, Optional[str]] = {}
        self._exit_codes: dict[str, int] = {}
        self._active_runs_file = (
            get_chip_nebula_dir(project_root)
            / "shared"
            / "memory"
            / "dashboard"
            / "active_runs.json"
        )
        self._active_runs_file.parent.mkdir(parents=True, exist_ok=True)
        self._load_active_runs()

    def _load_active_runs(self) -> None:
        if not self._active_runs_file.exists():
            return
        try:
            data = json.loads(self._active_runs_file.read_text())
        except (json.JSONDecodeError, OSError):
            return
        if not isinstance(data, dict):
            return
        to_remove: list[str] = []
        for run_id, info in data.items():
            pid = info.get("pid")
            if not self._pid_exists(pid):
                to_remove.append(run_id)
                continue
            self._processes[run_id] = _PlaceholderPopen(pid)
            self._features[run_id] = info.get("feature", "")
            self._frameworks[run_id] = info.get("framework") or None
        for run_id in to_remove:
            data.pop(run_id, None)
        self._save_active_runs(data)

    def _save_active_runs(self, data: Optional[dict] = None) -> None:
        data = data if data is not None else self._active_runs_dict()
        try:
            self._active_runs_file.write_text(json.dumps(data, indent=2, default=str))
        except OSError:
            pass

    def _active_runs_dict(self) -> dict:
        result: dict = {}
        for run_id in self._processes:
            proc = self._processes[run_id]
            pid = getattr(proc, "pid", None)
            if pid is None:
                continue
            result[run_id] = {
                "pid": pid,
                "feature": self._features.get(run_id, ""),
                "framework": self._frameworks.get(run_id, ""),
                "started_at": datetime.datetime.now().isoformat(),
            }
        return result

    @staticmethod
    def _pid_exists(pid: Optional[int]) -> bool:
        if pid is None:
            return False
        try:
            os.kill(pid, 0)
        except (OSError, ProcessLookupError):
            return False
        # ``kill(pid, 0)`` also succeeds for an unreaped zombie. Treating that
        # shell as a live workflow owner leaves its Attempt permanently stuck
        # in running after a hard stop.
        try:
            status = subprocess.run(
                ["ps", "-o", "stat=", "-p", str(pid)],
                capture_output=True, text=True, check=False, timeout=2,
            ).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            return True
        if status.startswith("Z"):
            return False
        return True

    def start(
        self,
        pipeline: str,
        feature: str,
        framework: Optional[str],
        workers: int,
        run_id: Optional[str] = None,
        resume: bool = False,
        preserve_stopped: bool = False,
    ) -> str:
        run_id = run_id or self._new_run_id()
        log_dir = get_chip_nebula_dir(self.project_root) / "shared" / "memory" / "dashboard"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"{run_id}.log"

        cmd = [
            *_cli_command(),
            "legacy-run",
            str(pipeline),
            "--feature",
            feature,
            "--workers",
            str(workers),
            "--run-id",
            run_id,
            "--reuse-sessions",
        ]
        if framework:
            cmd.extend(["--framework", framework])
        if resume:
            cmd.append("--resume")
        if preserve_stopped:
            cmd.append("--preserve-stopped")

        with open(log_file, "a") as stdout:
            stdout.write(f"\n[{datetime.datetime.now().isoformat()}] {' '.join(cmd)}\n")
            stdout.flush()
            proc = subprocess.Popen(
                cmd,
                cwd=str(self.project_root),
                stdout=stdout,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )

        self._processes[run_id] = proc
        self._owned_run_ids.add(run_id)
        self._features[run_id] = feature
        self._frameworks[run_id] = framework
        self._save_active_runs()
        return run_id

    def start_taskgraph(
        self,
        recipe: str,
        workflow: str,
        framework: Optional[str],
        model: Optional[str],
        workers: int,
        *,
        baseline: str = "HEAD",
        resume: bool = False,
        parameters: Optional[dict[str, str]] = None,
    ) -> str:
        existing = self.active_run_for(f"taskgraph:{workflow}")
        if existing:
            raise RuntimeError(
                f"workflow {workflow} is already running as {existing}"
            )
        run_id = self._new_run_id()
        log_dir = get_chip_nebula_dir(self.project_root) / "shared" / "memory" / "dashboard"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"{run_id}.log"
        cmd = [
            *_cli_command(),
            "run", str(recipe), "--workflow", workflow,
            "--baseline", baseline, "--workers", str(workers),
        ]
        if framework:
            cmd.extend(["--framework", framework])
        if model:
            cmd.extend(["--model", model])
        if resume:
            cmd.append("--resume")
        for name, artifact_id in sorted((parameters or {}).items()):
            cmd.extend(["--param", f"{name}={artifact_id}"])
        with open(log_file, "a") as stdout:
            stdout.write(f"\n[{datetime.datetime.now().isoformat()}] {' '.join(cmd)}\n")
            stdout.flush()
            proc = subprocess.Popen(
                cmd, cwd=str(self.project_root), stdout=stdout,
                stderr=subprocess.STDOUT, start_new_session=True,
            )
        self._processes[run_id] = proc
        self._owned_run_ids.add(run_id)
        self._features[run_id] = f"taskgraph:{workflow}"
        self._frameworks[run_id] = framework
        self._save_active_runs()
        return run_id

    def stop(self, run_id: str) -> bool:
        proc = self._processes.get(run_id)
        if proc is None or proc.poll() is not None:
            self._reap(run_id, proc)
            return False
        self._kill_process_group(proc)
        self._reap(run_id, proc)
        return True

    def stop_all(self) -> None:
        """Explicitly stop every tracked process, including attached ones."""
        for run_id in list(self._processes):
            self.stop(run_id)

    def active_taskgraph_runs(self) -> list[dict[str, str]]:
        # Planning also owns a live runner before its frozen Workflow exists.
        return [
            {"id": run_id, "workflow_id": feature.removeprefix("taskgraph:")}
            for run_id, feature in list(self._features.items())
            if feature.startswith("taskgraph:") and self.is_active(run_id)
        ]

    def stop_owned(self) -> None:
        """Stop only processes launched by this manager instance.

        Persisted runners loaded from ``active_runs.json`` belong to another
        dashboard instance.  Lifespan teardown must leave those processes
        alone; an explicit user Stop/reset still calls :meth:`stop_all`.
        """
        for run_id in list(self._owned_run_ids):
            self.stop(run_id)

    @staticmethod
    def _kill_process_group(
        proc: subprocess.Popen, timeout: float = 5
    ) -> None:
        """Signal the whole process group (SIGTERM then SIGKILL), not just the runner PID."""
        pid = getattr(proc, "pid", None)
        # Reject mocks and special PIDs before Python coerces them via __index__.
        if type(pid) is not int or pid <= 1:
            return
        try:
            pgid = os.getpgid(pid)
        except ProcessLookupError:
            return
        # Our runners use start_new_session=True, so each owns its process group.
        # In particular, killpg(1, sig) becomes kill(-1, sig) on Linux.
        if pgid <= 1 or pgid != pid or pgid == os.getpgrp():
            return
        try:
            os.killpg(pgid, signal.SIGTERM)
        except (ProcessLookupError, PermissionError):
            return
        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            pass
        # The runner exiting on SIGTERM says nothing about its children (agent
        # CLIs may ignore SIGTERM). SIGKILL the group whenever ANY member is
        # still alive, not only when the runner itself is.
        try:
            os.killpg(pgid, 0)
        except ProcessLookupError:
            return
        try:
            os.killpg(pgid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            return
        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            pass

    def _reap(self, run_id: str, proc) -> None:
        """Drop a run, recording its exit code so the UI can show why it ended."""
        if proc is not None:
            code = proc.poll()
            if code is not None:
                self._exit_codes[run_id] = code
        self._drop_run(run_id)

    def _drop_run(self, run_id: str) -> None:
        self._processes.pop(run_id, None)
        self._owned_run_ids.discard(run_id)
        self._features.pop(run_id, None)
        self._frameworks.pop(run_id, None)
        self._save_active_runs()

    def is_active(self, run_id: str) -> bool:
        proc = self._processes.get(run_id)
        if proc is None:
            return False
        if proc.poll() is not None:
            self._reap(run_id, proc)
            return False
        return True

    def returncode_for(self, run_id: str) -> Optional[int]:
        proc = self._processes.get(run_id)
        if proc is not None:
            code = proc.poll()
            if code is not None:
                self._exit_codes[run_id] = code
            return code
        return self._exit_codes.get(run_id)

    def feature_for(self, run_id: str) -> Optional[str]:
        return self._features.get(run_id)

    def framework_for(self, run_id: str) -> Optional[str]:
        return self._frameworks.get(run_id)

    def active_run_for(self, feature_id: str) -> Optional[str]:
        self.prune_finished()
        for run_id, feat in self._features.items():
            if feat == feature_id and self.is_active(run_id):
                return run_id
        return None

    def prune_finished(self) -> None:
        finished = [
            rid for rid, proc in self._processes.items() if proc.poll() is not None
        ]
        for rid in finished:
            code = self._processes[rid].poll()
            if code is not None:
                self._exit_codes[rid] = code
            self._processes.pop(rid, None)
            self._owned_run_ids.discard(rid)
            self._features.pop(rid, None)
            self._frameworks.pop(rid, None)
        if finished:
            self._save_active_runs()

    @staticmethod
    def _new_run_id() -> str:
        return (
            datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
            + "-"
            + uuid.uuid4().hex[:6]
        )


class _PlaceholderPopen:
    """Minimal Popen stand-in for processes discovered from disk on startup."""

    def __init__(self, pid: int):
        self.pid = pid

    def poll(self) -> Optional[int]:
        return None if RunManager._pid_exists(self.pid) else -1

    def send_signal(self, sig: int) -> None:
        try:
            os.kill(self.pid, sig)
        except ProcessLookupError:
            pass

    def kill(self) -> None:
        self.send_signal(signal.SIGKILL)

    def wait(self, timeout: Optional[float] = None) -> int:
        import time
        deadline = time.time() + (timeout or 5)
        while time.time() < deadline:
            if self.poll() is not None:
                return 0
            time.sleep(0.1)
        raise subprocess.TimeoutExpired(cmd=[], timeout=timeout)
