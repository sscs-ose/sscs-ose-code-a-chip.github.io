"""Locked, durable attempt allocation; allocation failures cannot mint retries."""
from __future__ import annotations

import datetime
import fcntl
import json
from pathlib import Path

from capacity_protocol import PHYSICAL_LIMITS
from study_protocol import write_json


def reserve(root, category, trial, identity):
    root = Path(root)
    if category == "retained_invalid_pilot":
        raise ValueError("Historical failures are imported, never newly allocated")
    if category not in PHYSICAL_LIMITS or not all(
            isinstance(x, str) and x and x.isascii() and all(c.isalnum() or c in "-_" for c in x)
            for x in (trial, identity)):
        raise ValueError("Unknown category or unsafe trial/attempt identity")
    root.mkdir(parents=True, exist_ok=True)
    with (root / ".physical-budget.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        path = root / "physical-ledger.json"
        state = json.loads(path.read_text()) if path.exists() else dict(
            limits=PHYSICAL_LIMITS, absolute_total=194, attempts=[])
        if state["limits"] != PHYSICAL_LIMITS or state["absolute_total"] != 194:
            raise ValueError("Physical budget differs from approved protocol")
        rows = state["attempts"]
        if any(r["identity"] == identity for r in rows):
            raise ValueError("Existing attempt retained; no replacement")
        if len(rows) >= 194 or sum(r["category"] == category for r in rows) >= PHYSICAL_LIMITS[category]:
            raise ValueError("Physical category/global budget exhausted")
        if category in ("pilot", "formal"):
            if sum(r["trial"] == trial for r in rows) >= 2:
                raise ValueError("No third physical attempt")
            protocol = json.loads((root / "protocol.json").read_text())
            jobs = protocol["pilot_jobs" if category == "pilot" else "formal_jobs"]
            if trial not in {row["id"] for row in jobs}:
                raise ValueError("Trial is not preregistered")
            if category == "pilot" and not protocol.get("pilot_launch_allowed"):
                raise ValueError("Pilot prerequisites not qualified")
            if category == "formal" and not protocol.get("formal_launch_allowed"):
                raise ValueError("Formal prerequisites not qualified")
        if category == "preformal_calibration" and (root / "formal-freeze.json").exists():
            raise ValueError("Calibration cannot rescue a formal trial")
        row = dict(identity=identity, trial=trial, category=category, status="allocated",
                   allocated_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
        rows.append(row)
        write_json(path, state)
        return row


def finish(root, identity, status, evidence):
    if status not in ("passed", "failed", "timeout", "infrastructure_error"):
        raise ValueError("Physical attempt must have an explicit terminal class")
    root = Path(root)
    with (root / ".physical-budget.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        path = root / "physical-ledger.json"
        state = json.loads(path.read_text())
        row = next(r for r in state["attempts"] if r["identity"] == identity)
        if row["status"] != "allocated":
            raise ValueError("Terminal attempt cannot be overwritten")
        row.update(status=status, evidence=evidence)
        write_json(path, state)
