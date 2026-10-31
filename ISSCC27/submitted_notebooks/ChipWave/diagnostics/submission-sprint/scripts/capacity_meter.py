"""Fail-closed shared usage accounting; the observer, not the model, owns state."""
from __future__ import annotations

import hashlib
import json

FIELDS = ("input_tokens", "cached_input_tokens", "output_tokens", "reasoning_output_tokens")


class InvalidMeasurement(ValueError):
    pass


class TokenLedger:
    """Consume cumulative events across serial roles and preserve state on resume."""

    def __init__(self, state=None, limit=1_000_000):
        self.state = state if state is not None else dict(
            limit=limit, valid=True, errors=[], sessions={}, events={}, actual_tokens=0,
            cached_input_tokens=0, output_tokens=0, snapshots=[])

    def invalid(self, reason):
        self.state["valid"] = False
        self.state["errors"].append(reason)
        raise InvalidMeasurement(reason)

    def record(self, session, event_key, usage):
        if not self.state["valid"]:
            raise InvalidMeasurement("Ledger was invalidated; original evidence must be retained")
        if not session or not event_key:
            self.invalid("Missing source session/event identity")
        if any(type(usage.get(k)) is not int or usage[k] < 0 for k in FIELDS):
            self.invalid("Missing, negative or non-integer cumulative usage")
        if (usage["cached_input_tokens"] > usage["input_tokens"]
                or usage["reasoning_output_tokens"] > usage["output_tokens"]
                or usage.get("total_tokens") != usage["input_tokens"] + usage["output_tokens"]):
            self.invalid("Inconsistent cumulative usage")
        key = session + ":" + event_key
        fingerprint = hashlib.sha256(json.dumps(usage, sort_keys=True).encode()).hexdigest()
        prior = self.state["events"].get(key)
        if prior:
            if prior["sha256"] != fingerprint:
                self.invalid("An existing event identity changed content")
            return prior
        previous = self.state["sessions"].get(session, {k: 0 for k in FIELDS})
        if any(usage[k] < previous[k] for k in FIELDS):
            self.invalid("Cumulative counter reset without a new source session")
        delta = {k: usage[k] - previous[k] for k in FIELDS}
        self.state["actual_tokens"] += delta["input_tokens"] + delta["output_tokens"]
        self.state["cached_input_tokens"] += delta["cached_input_tokens"]
        self.state["output_tokens"] += delta["output_tokens"]
        self.state["sessions"][session] = dict(usage)
        row = dict(sha256=fingerprint, cumulative=dict(usage), delta=delta,
                   global_tokens=self.state["actual_tokens"])
        self.state["events"][key] = row
        return row

    def snapshot(self, *, snapshot_id, source_sha256, session, event_key, witness):
        """Admit only externally captured, completed-tool or terminal snapshots.

        Live observer qualification remains separate: synthetic witnesses do not
        establish that a real CLI stream can produce these guarantees.
        """
        if not self.state["valid"]:
            raise InvalidMeasurement("Cannot score an invalid ledger")
        event = self.state["events"].get(session + ":" + event_key)
        if not event or not source_sha256:
            self.invalid("Snapshot missing usage or source evidence")
        required = ("source_immutable", "no_unaccounted_mutation", "source_session_matches")
        if any(witness.get(k) is not True for k in required):
            self.invalid("Unproven source/usage association")
        completed = witness.get("tool_completed") is True and witness.get("usage_after_capture") is True
        admitted = witness.get("source_frozen_before_eda") is True and witness.get("native_response_accounted") is True
        if not (completed or admitted):
            self.invalid("Neither completed-tool nor pre-EDA response admission is proven")
        if any(s["id"] == snapshot_id for s in self.state["snapshots"]):
            self.invalid("Snapshot identity reused")
        charged = event["global_tokens"]
        row = dict(id=snapshot_id, source_sha256=dict(source_sha256),
                   session=session, event_key=event_key, tokens=charged,
                   budget_admissible=charged <= self.state["limit"], witness=dict(witness))
        self.state["snapshots"].append(row)
        return row

    def at(self, budget):
        if not self.state["valid"]:
            return None
        eligible = [r for r in self.state["snapshots"]
                    if r["budget_admissible"] and r["tokens"] <= budget]
        # Observer append order is snapshot order; never inspect grader verdicts.
        return eligible[-1] if eligible else None

    def summary(self):
        total = self.state["actual_tokens"]
        return dict(actual_tokens=total, overshoot_tokens=max(0, total-self.state["limit"]),
                    logical_token_limit=self.state["limit"],
                    cached_input_tokens=self.state["cached_input_tokens"],
                    measurement_valid=self.state["valid"], errors=self.state["errors"],
                    dispatch_allowed=self.state["valid"] and total < self.state["limit"])
