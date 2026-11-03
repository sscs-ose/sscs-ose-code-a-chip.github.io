"""Deterministic command execution shared by Task Graph and the desktop."""

from __future__ import annotations

import datetime as dt
import os
import re
import shlex
import signal
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Mapping

import psutil


@dataclass(frozen=True)
class ToolCommand:
    name: str
    command: str
    cwd: str = "."
    timeout: int = 900
    success_pattern: str = ""
    environment: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ToolCommandResult:
    name: str
    command: str
    status: str
    verdict: str
    returncode: int | None
    started_at: str
    finished_at: str
    duration_seconds: float
    log: str
    reason: str = ""
    resources: Mapping[str, int | float | None] = field(default_factory=dict)


@dataclass(frozen=True)
class ToolExecutionResult:
    status: str
    verdict: str
    commands: tuple[ToolCommandResult, ...]
    log: str
    tool_versions: dict[str, str] = field(default_factory=dict)


class DeterministicToolExecutor:
    """Run explicit shell commands and retain status separately from verdict."""

    def __init__(
        self,
        *,
        stop_event: threading.Event | None = None,
        process_callback: Callable[[subprocess.Popen[str] | None], None] | None = None,
        log_callback: Callable[[str], None] | None = None,
    ) -> None:
        self.stop_event = stop_event or threading.Event()
        self.process_callback = process_callback
        self.log_callback = log_callback

    def execute(self, root: Path, commands: Iterable[ToolCommand]) -> ToolExecutionResult:
        results: list[ToolCommandResult] = []
        versions: dict[str, str] = {}
        for command in commands:
            result = self._run(root, command)
            results.append(result)
            token = _command_token(command.command)
            if token and token not in versions:
                versions[token] = _tool_version(token, command.environment)
            if result.status != "succeeded" or result.verdict != "passed":
                break
        if not results:
            return ToolExecutionResult("not_started", "not_started", (), "", versions)
        last = results[-1]
        status = (
            "succeeded"
            if all(item.status == "succeeded" for item in results)
            else last.status
        )
        verdict = (
            "passed"
            if status == "succeeded" and all(item.verdict == "passed" for item in results)
            else last.verdict
        )
        log = "\n".join(
            f"$ [{item.name}] {item.command}\n{item.log}".rstrip()
            for item in results
        ) + "\n"
        return ToolExecutionResult(status, verdict, tuple(results), log, versions)

    def _run(self, root: Path, command: ToolCommand) -> ToolCommandResult:
        started_wall = dt.datetime.now(dt.timezone.utc)
        started = time.monotonic()
        workspace = (root / command.cwd).resolve()
        resolved_root = root.resolve()
        if workspace != resolved_root and resolved_root not in workspace.parents:
            return _immediate(
                command, started_wall, "launch_failed", "not_started",
                "cwd escapes workspace",
            )
        if not workspace.is_dir():
            return _immediate(
                command, started_wall, "launch_failed", "not_started",
                f"cwd does not exist: {command.cwd}",
            )
        try:
            environment = os.environ.copy()
            environment.update({
                str(key): str(value)
                for key, value in command.environment.items()
            })
            process = subprocess.Popen(
                ["/bin/bash", "-o", "pipefail", "-c", command.command],
                cwd=workspace,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                errors="replace",
                start_new_session=True,
                env=environment,
            )
        except OSError as exc:
            return _immediate(
                command, started_wall, "launch_failed", "not_started", str(exc)
            )
        if self.process_callback:
            self.process_callback(process)
        status = "succeeded"
        reason = ""
        chunks: list[str] = []
        peak_rss = peak_swap = 0
        cpu_seconds = 0.0

        def read_output() -> None:
            if process.stdout is None:
                return
            for chunk in process.stdout:
                chunks.append(chunk)
                if self.log_callback:
                    self.log_callback(chunk)

        reader = threading.Thread(target=read_output, daemon=True)
        reader.start()
        try:
            while True:
                peak_rss, peak_swap, cpu_seconds = _sample_tree_resources(
                    process.pid, peak_rss, peak_swap, cpu_seconds,
                )
                if process.poll() is not None:
                    break
                if self.stop_event.is_set():
                    _terminate_process_group(process)
                    status, reason = "stopped", "stopped by user"
                    break
                if command.timeout and time.monotonic() - started > command.timeout:
                    _terminate_process_group(process)
                    status, reason = "timeout", f"timed out after {command.timeout}s"
                    break
                time.sleep(0.1)
            process.wait()
            reader.join(timeout=5)
        finally:
            if self.process_callback:
                self.process_callback(None)
        output = "".join(chunks)
        verdict = "failed"
        if status == "succeeded":
            if process.returncode != 0:
                status, reason = "failed", f"command exited with {process.returncode}"
            elif command.success_pattern and not re.search(
                command.success_pattern, output, re.MULTILINE
            ):
                verdict, reason = "failed", "success pattern was not found"
            else:
                verdict = "passed"
        elif status in {"stopped", "timeout"}:
            verdict = status
        finished = dt.datetime.now(dt.timezone.utc)
        return ToolCommandResult(
            name=command.name,
            command=command.command,
            status=status,
            verdict=verdict,
            returncode=process.returncode,
            started_at=started_wall.isoformat(),
            finished_at=finished.isoformat(),
            duration_seconds=round(time.monotonic() - started, 6),
            log=output,
            reason=reason,
            resources={
                "wall_time_seconds": round(time.monotonic() - started, 6),
                "peak_rss_bytes": peak_rss,
                "peak_swap_bytes": peak_swap,
                "cpu_seconds": round(cpu_seconds, 6),
                "memory_limit_bytes": None,
            },
        )


def _sample_tree_resources(
    pid: int, peak_rss: int, peak_swap: int, cpu_seconds: float,
) -> tuple[int, int, float]:
    try:
        root = psutil.Process(pid)
        processes = [root, *root.children(recursive=True)]
    except (psutil.Error, OSError):
        return peak_rss, peak_swap, cpu_seconds
    rss = swap = 0
    cpu = 0.0
    for item in processes:
        try:
            memory = item.memory_full_info()
            times = item.cpu_times()
        except (psutil.Error, OSError):
            continue
        rss += int(getattr(memory, "rss", 0))
        swap += int(getattr(memory, "swap", 0))
        cpu += float(times.user + times.system)
    return max(peak_rss, rss), max(peak_swap, swap), max(cpu_seconds, cpu)


def _immediate(
    command: ToolCommand,
    started: dt.datetime,
    status: str,
    verdict: str,
    reason: str,
) -> ToolCommandResult:
    return ToolCommandResult(
        command.name, command.command, status, verdict, None,
        started.isoformat(), dt.datetime.now(dt.timezone.utc).isoformat(),
        0.0, "", reason,
        resources={
            "wall_time_seconds": 0.0,
            "peak_rss_bytes": 0,
            "peak_swap_bytes": 0,
            "cpu_seconds": 0.0,
            "memory_limit_bytes": None,
        },
    )


def _terminate_process_group(
    process: subprocess.Popen[str], timeout: float = 2.0
) -> None:
    pid = getattr(process, "pid", None)
    if type(pid) is not int or pid <= 1:
        return
    try:
        pgid = os.getpgid(pid)
    except ProcessLookupError:
        return
    if pgid <= 1 or pgid != pid or pgid == os.getpgrp():
        return
    try:
        os.killpg(pgid, signal.SIGTERM)
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(pgid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    except ProcessLookupError:
        pass


def _command_token(command: str) -> str:
    try:
        words = shlex.split(command)
    except ValueError:
        return ""
    while words and (words[0] in {"env", "sudo"} or "=" in words[0]):
        words.pop(0)
    return Path(words[0]).name if words else ""


def _tool_version(token: str, environment: Mapping[str, str] | None = None) -> str:
    process_environment = os.environ.copy()
    process_environment.update({
        str(key): str(value) for key, value in (environment or {}).items()
    })
    try:
        executable = shutil.which(token, path=process_environment.get("PATH"))
    except TypeError:
        executable = shutil.which(token)
    if not executable:
        executable = token
    flags = ("-V", "--version") if token in {"iverilog", "vvp"} else ("--version", "-V")
    for flag in flags:
        try:
            result = subprocess.run(
                [executable, flag], capture_output=True, text=True, timeout=3,
                errors="replace", env=process_environment,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        if result.returncode != 0:
            continue
        lines = (result.stdout or result.stderr).strip().splitlines()
        if lines:
            return lines[0][:300]
    return "available"
