"""Paired clocks and fail-closed worker admissions, with no subtraction of host gaps."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import threading
import time

from winjob import _winapi, open_identity


class WindowExpired(RuntimeError):
    pass


def clock_sample() -> dict:
    before = time.monotonic_ns()
    wall = time.time_ns()
    after = time.monotonic_ns()
    return {
        "utc": datetime.fromtimestamp(wall / 1e9, timezone.utc).isoformat(),
        "wall_ns": wall, "monotonic_ns": after,
        "paired_sampling_span_ns": after - before,
    }


def clock_state(start: dict, now: dict, limit_seconds: float) -> dict:
    wall = (now["wall_ns"] - start["wall_ns"]) / 1e9
    mono = (now["monotonic_ns"] - start["monotonic_ns"]) / 1e9
    reason = None
    if wall < 0 or mono < 0 or now["paired_sampling_span_ns"] > 100_000_000:
        reason = "unverifiable_clock_sample"
    elif wall >= limit_seconds or mono >= limit_seconds:
        reason = "deadline_elapsed"
    elif abs(wall - mono) > 0.5:
        reason = "wall_monotonic_disagreement"
    return {
        "allowed": reason is None, "reason": reason, "wall_elapsed_seconds": wall,
        "monotonic_elapsed_seconds": mono, "remaining_seconds": limit_seconds - max(wall, mono),
        "clock_difference_seconds": wall - mono,
    }


class WorkerGuard:
    def __init__(self, event_path: Path):
        self.context = json.loads(os.environ["PVT45_SUPERVISION_CONTEXT"])
        self.handle = open_identity(self.context["supervisor"]["pid"],
                                    self.context["supervisor"]["creation_filetime"])
        self.event_path = event_path
        self.lock = threading.Lock()
        self.check("worker_start")

    def state(self, now=None):
        result = clock_state(self.context["start"], now or clock_sample(),
                             self.context["limit_seconds"])
        if _winapi.WaitForSingleObject(self.handle, 0) != _winapi.WAIT_TIMEOUT:
            result.update(allowed=False, reason="supervisor_process_exited")
        return result

    def event(self, name: str, **fields):
        sample = clock_sample()
        record = {"event": name, "clock": sample, "deadline_state": self.state(sample), **fields}
        self.event_path.parent.mkdir(parents=True, exist_ok=True)
        with self.lock, self.event_path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(record, allow_nan=False) + "\n")
            handle.flush()
        return record

    def check(self, name: str, **fields):
        # If the event write stalls, the independent job owner still expires the worker.
        before = self.state()
        if not before["allowed"]:
            raise WindowExpired(before["reason"])
        record = self.event(name, **fields)
        after = self.state()
        if not after["allowed"]:
            raise WindowExpired(after["reason"])
        return record

    def remaining(self) -> float:
        state = self.state()
        if not state["allowed"]:
            raise WindowExpired(state["reason"])
        return state["remaining_seconds"]

    def close(self):
        _winapi.CloseHandle(self.handle)
