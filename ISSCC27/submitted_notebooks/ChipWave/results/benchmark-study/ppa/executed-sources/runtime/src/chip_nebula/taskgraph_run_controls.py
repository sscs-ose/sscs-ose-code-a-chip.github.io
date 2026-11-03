"""Cross-process controls for a running Task Graph Run.

Kept outside the ``taskgraph`` package only to avoid importing its public
facade (and therefore adapters) while an adapter module itself is loading.
"""

from __future__ import annotations

import json
import os
import signal
import time
from pathlib import Path

import psutil


def timeout_control_path(chip_nebula_dir: Path, run_id: str) -> Path:
    return chip_nebula_dir / "shared" / "memory" / "run_controls" / f"{run_id}.json"


def initialize_timeout_control(path: Path, *, run_id: str, base_timeout: int) -> dict:
    now = time.time()
    document = {
        "version": 1,
        "run_id": run_id,
        "base_timeout_seconds": int(base_timeout),
        "extension_seconds": 0,
        "started_at_epoch": now,
        "updated_at_epoch": now,
    }
    _write_atomic(path, document)
    return document


def read_timeout_control(path: str | Path | None) -> dict:
    if not path:
        return {}
    try:
        document = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {}
    return document if isinstance(document, dict) else {}


def extend_timeout_control(path: Path, seconds: int) -> dict:
    if seconds <= 0:
        raise ValueError("timeout extension must be positive")
    document = read_timeout_control(path)
    if not document:
        raise FileNotFoundError(f"Run timeout control does not exist: {path}")
    document["extension_seconds"] = int(document.get("extension_seconds", 0)) + int(seconds)
    document["updated_at_epoch"] = time.time()
    _write_atomic(path, document)
    return document


def effective_timeout_seconds(path: str | Path | None, fallback: int) -> int:
    document = read_timeout_control(path)
    base = int(document.get("base_timeout_seconds", fallback) or fallback)
    extension = max(0, int(document.get("extension_seconds", 0) or 0))
    return base + extension


def record_run_process(path: str | Path | None, pid: int) -> None:
    """Persist the adapter process identity for crash recovery.

    The process creation time prevents a later runner from killing an
    unrelated process if the operating system has reused the numeric PID.
    """
    if not path or pid <= 0:
        return
    document = read_timeout_control(path)
    if not document:
        return
    try:
        process = psutil.Process(pid)
        created = process.create_time()
        process_group = os.getpgid(pid) if os.name == "posix" else 0
    except (psutil.Error, ProcessLookupError, PermissionError):
        return
    document["adapter_process"] = {
        "pid": pid,
        "created_at_epoch": created,
        "process_group": process_group,
    }
    document["updated_at_epoch"] = time.time()
    _write_atomic(Path(path), document)


def clear_run_process(path: str | Path | None, pid: int) -> None:
    if not path:
        return
    document = read_timeout_control(path)
    recorded = document.get("adapter_process")
    if not isinstance(recorded, dict) or int(recorded.get("pid", 0) or 0) != pid:
        return
    document.pop("adapter_process", None)
    document["updated_at_epoch"] = time.time()
    _write_atomic(Path(path), document)


def terminate_recorded_run_process(
    path: str | Path | None, *, timeout: float = 5.0,
) -> bool:
    """Terminate the exact recorded adapter process tree, if it is still live."""
    document = read_timeout_control(path)
    recorded = document.get("adapter_process")
    if not isinstance(recorded, dict):
        return True
    try:
        pid = int(recorded["pid"])
        expected_created = float(recorded["created_at_epoch"])
        process = psutil.Process(pid)
        if abs(process.create_time() - expected_created) > 0.01:
            return True
    except (KeyError, TypeError, ValueError, psutil.NoSuchProcess, ProcessLookupError):
        clear_run_process(path, int(recorded.get("pid", 0) or 0))
        return True
    except (psutil.Error, PermissionError):
        return False

    descendants = process.children(recursive=True)
    process_group = int(recorded.get("process_group", 0) or 0)
    try:
        if process_group and os.name == "posix":
            os.killpg(process_group, signal.SIGTERM)
        else:
            for child in reversed(descendants):
                child.terminate()
            process.terminate()
    except (ProcessLookupError, psutil.NoSuchProcess):
        pass
    except (PermissionError, psutil.AccessDenied):
        return False
    _, alive = psutil.wait_procs([process, *descendants], timeout=timeout)
    if alive:
        try:
            if process_group and os.name == "posix":
                os.killpg(process_group, signal.SIGKILL)
            else:
                for item in alive:
                    item.kill()
        except (ProcessLookupError, psutil.NoSuchProcess):
            pass
        except (PermissionError, psutil.AccessDenied):
            return False
        _, alive = psutil.wait_procs(alive, timeout=timeout)
    clear_run_process(path, pid)
    return not alive


def _write_atomic(path: Path, document: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    os.replace(temporary, path)
