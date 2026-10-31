"""Protected incremental native usage observer and shared-budget process stop."""
from __future__ import annotations

import hashlib
import json
import os
import signal
import subprocess
import time
from pathlib import Path

from capacity_meter import InvalidMeasurement, TokenLedger
from capacity_native_usage import NativeUsage
from study_protocol import write_json


class LiveUsage:
    """Raw native transcripts remain private; only accounting leaves this owner."""
    def __init__(self, private, record, model, *, limit=1_000_000):
        self.private, self.record, self.model = Path(private), Path(record), model
        self.ledger = TokenLedger(json.loads(self.record.read_text()) if self.record.exists() else None,
                                  limit=limit)
        if self.ledger.state["events"] and self.ledger.state.get("accounting_schema") != "native-response-v2":
            raise ValueError("Preserve the legacy ledger; replay raw transcripts into a new v2 ledger")
        self.ledger.state["accounting_schema"] = "native-response-v2"
        if self.ledger.state["limit"] != limit:
            raise ValueError("Existing shared Token ceiling differs")
        self.prefixes = {}
        self.sessions = {}
        self.contexts = set()
        self.awaiting_usage = set()
        self.native_usage = {}

    def poll(self):
        try:
            paths = sorted((self.private/"sessions").rglob("*.jsonl"))
            if set(self.prefixes)-set(paths):
                self.ledger.invalid("Previously observed transcript disappeared")
            recorded = self.ledger.state.setdefault("transcript_prefixes", {})
            if set(recorded)-{str(p.relative_to(self.private)) for p in paths}:
                self.ledger.invalid("Durably recorded transcript disappeared")
            for path in paths:
                if path.is_symlink() or not path.resolve().is_relative_to(self.private.resolve()):
                    self.ledger.invalid("Transcript escapes private accounting tree")
                data = path.read_bytes()
                key = str(path.relative_to(self.private))
                durable = recorded.get(key)
                if durable and (len(data) < durable["bytes"] or hashlib.sha256(
                        data[:durable["bytes"]]).hexdigest() != durable["sha256"]):
                    self.ledger.invalid("Durably recorded native prefix changed")
                previous = self.prefixes.get(path, b"")
                if not data.startswith(previous):
                    self.ledger.invalid("Transcript was truncated or previous bytes changed")
                complete = data[:data.rfind(b"\n")+1]
                accounting = self.native_usage.setdefault(path,NativeUsage())
                offset = len(previous)
                for line in complete[offset:].splitlines(keepends=True):
                    try:
                        event = json.loads(line)
                    except ValueError:
                        self.ledger.invalid("Malformed completed transcript event")
                    if not isinstance(event, dict) or not isinstance(event.get("payload", {}), dict):
                        self.ledger.invalid("Malformed native event structure")
                    kind, payload = event.get("type"), event.get("payload", {})
                    if kind == "session_meta":
                        session = payload.get("id")
                        if not isinstance(session, str) or not session:
                            self.ledger.invalid("Missing native session identity")
                        if path in self.sessions and self.sessions[path] != session:
                            self.ledger.invalid("Transcript changed its native session identity")
                        if session in self.sessions.values() and self.sessions.get(path) != session:
                            self.ledger.invalid("Native session duplicated across source files")
                        self.sessions[path] = session
                    if kind == "turn_context":
                        if payload.get("model") != self.model or payload.get("effort") != "high":
                            self.ledger.invalid("Actual native context differs from frozen model/effort")
                        if path not in self.sessions:
                            self.ledger.invalid("Context without source session")
                        self.contexts.add(self.sessions[path])
                        self.awaiting_usage.add(self.sessions[path])
                    try:
                        usage = accounting.observe(kind,payload)
                    except InvalidMeasurement as error:
                        self.ledger.invalid(str(error))
                    if usage is not None:
                        session = self.sessions.get(path)
                        if session not in self.contexts:
                            self.ledger.invalid("Usage without verified native context")
                        # Byte offsets survive reopening; existing ledger events are idempotent.
                        self.ledger.record(session, "byte-"+str(offset), usage)
                        self.awaiting_usage.discard(session)
                    offset += len(line)
                self.prefixes[path] = complete
                recorded[key] = dict(bytes=len(complete), sha256=hashlib.sha256(complete).hexdigest())
            return self.ledger.summary()
        finally:
            write_json(self.record, self.ledger.state)

    def finish(self):
        self.poll()
        try:
            for path, prefix in self.prefixes.items():
                if path.read_bytes() != prefix:
                    self.ledger.invalid("Terminal transcript has an incomplete final event")
            if not self.ledger.state["events"]:
                self.ledger.invalid("Native invocation ended without usage")
            if self.awaiting_usage:
                self.ledger.invalid("Native turn ended without its own usage event")
        finally:
            write_json(self.record, self.ledger.state)
        return self.ledger.summary()

    def admit(self, session, event_key):
        """A tool waits for its own response, never spends against an earlier counter."""
        if not self.ledger.state["valid"]:
            raise ValueError("Invalid shared usage measurement")
        entry = self.ledger.state["events"].get(session+":"+event_key)
        if entry is None:
            return None
        if entry["global_tokens"]>self.ledger.state["limit"]:
            raise ValueError("Response exceeds the Token ceiling")
        return dict(session=session,tokens=entry["global_tokens"],usage_sha256=entry["sha256"])

    def wait(self, process, *, active_seconds=5400, physical_wait_seconds=lambda: 0.0):
        """Caller launches a new process group; deterministic broker EDA is separate."""
        if os.getpgid(process.pid) != process.pid:
            raise ValueError("Cannot control an invocation sharing another process group")
        start, excluded_start = time.monotonic(), physical_wait_seconds()
        reason = None
        while process.poll() is None:
            try:
                summary = self.poll()
                if not summary["dispatch_allowed"]:
                    reason = "token_budget"
            except InvalidMeasurement:
                reason = "measurement_invalid"
            active = time.monotonic()-start-(physical_wait_seconds()-excluded_start)
            if active >= active_seconds:
                reason = reason or "active_time_budget"
            if reason:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
                break
            time.sleep(.1)
        # Account final in-flight usage as actual cost; never authorize its artifacts here.
        try:
            summary = self.finish()
        except InvalidMeasurement:
            reason = reason or "measurement_invalid"
            summary = self.ledger.summary()
        return dict(reason=reason or "native_exit", exit_code=process.returncode,
                    wall_seconds=time.monotonic()-start, **summary)
