"""Durable logical identity for explicitly submitted model/native executions.

Owners explicitly attach the nonce to NEW records before their existing atomic
persist. Reads never add defaults or rewrite historical records. The separate
submission mutex is never acquired by workers, preserving owner lock ordering.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
import threading

from .domain import DomainError

PROTOCOL_VERSION = "execution-submission-v1"
LEDGER = "execution_submissions"
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_MUTEX_GUARD = threading.Lock()
_POOLS = ("jobs", "runs", "batches")


def validate_submission_id(value):
    if type(value) is not str or not _ID.fullmatch(value):
        raise DomainError("invalid_submission_id", "Submission identity must be 1 to 128 identifier characters.")


def _hash(route, request):
    return hashlib.sha256(json.dumps({"route": route, "request": request}, sort_keys=True,
        ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def _records(state):
    return [record for pool in _POOLS for record in state.get(pool, []) if type(record) is dict]


def _durable(owner):
    committed = getattr(owner, "_committed", None)
    if type(committed) is not dict:
        raise DomainError("submission_owner_unsupported", "This execution manager has no durable submission snapshot.", 500)
    return committed


def validate_submissions(state):
    """Check additive receipt bindings without changing legacy state or records."""
    ledger = state.get(LEDGER, {})
    if type(ledger) is not dict:
        raise ValueError("Invalid execution submission ledger")
    pooled = _records(state)
    identifiers = [record.get("id") for record in pooled]
    if any(type(value) is not str or not value for value in identifiers) or len(set(identifiers)) != len(identifiers):
        raise ValueError("Execution records must have distinct nonempty identities across pools")
    records = {record["id"]: record for record in pooled}
    bound = set()
    for key, receipt in ledger.items():
        validate_submission_id(key)
        if (type(receipt) is not dict or set(receipt) != {"route", "request", "binding_hash", "record_id", "rejection"}
                or type(receipt["route"]) is not str or not receipt["route"]
                or type(receipt["request"]) is not dict or "submission_id" in receipt["request"]
                or receipt["binding_hash"] != _hash(receipt["route"], receipt["request"])):
            raise ValueError("Invalid frozen execution submission")
        identifier, rejection = receipt["record_id"], receipt["rejection"]
        if identifier is None:
            if (type(rejection) is not dict or set(rejection) != {"code", "message", "status"}
                    or type(rejection["code"]) is not str or type(rejection["message"]) is not str
                    or type(rejection["status"]) is not int or not 400 <= rejection["status"] < 500):
                raise ValueError("Invalid rejected execution submission")
        else:
            record = records.get(identifier) if type(identifier) is str else None
            if record is None or rejection is not None or identifier in bound or record.get("submission_id") != key:
                raise ValueError("Execution submission does not bind its unique record")
            bound.add(identifier)
    for record in records.values():
        if "submission_id" in record and record.get("id") not in bound:
            raise ValueError("Execution record lacks its submission receipt")


def submission_view(owner):
    """Return only committed receipts; no default field or new file is written."""
    with owner.lock:
        return copy.deepcopy(_durable(owner).get(LEDGER, {}))


def _reject(key, rejection):
    error = DomainError(rejection["code"], rejection["message"], rejection["status"])
    error.execution_start_rejected_before_creation = True
    error.submission_id = key
    raise error


def _existing(owner, key, route, request):
    receipt = _durable(owner).get(LEDGER, {}).get(key)
    if receipt is None:
        return None
    if receipt["route"] != route or receipt["request"] != request or receipt["binding_hash"] != _hash(route, request):
        raise DomainError("submission_conflict", "This submission identity already binds a different frozen execution request.", 409)
    if receipt["rejection"]:
        _reject(key, receipt["rejection"])
    if not any(record.get("id") == receipt["record_id"] and record.get("submission_id") == key for record in _records(_durable(owner))):
        raise DomainError("submission_record_missing", "The saved execution receipt cannot resolve its original record.", 500)
    return receipt


def _reply(result, key, receipt, replayed):
    result = result if type(result) is dict else {}
    result["execution_submission"] = {"version": PROTOCOL_VERSION, "submission_id": key,
        "record_id": receipt["record_id"], "replayed": replayed, "route": receipt["route"]}
    return result


class Submission:
    """A frozen intent passed explicitly to the owner's record construction."""
    def __init__(self, owner, key, route, request):
        self.owner, self.submission_id, self.route = owner, key, route
        self.request = copy.deepcopy(request)
        self.record_id = None

    def bind(self, record_id):
        # The owner must independently set NEW record['submission_id'] before
        # binding, append and its ordinary record-hash/persist operation.
        if type(record_id) is not str or not record_id or self.record_id is not None:
            raise DomainError("invalid_submission_record", "A submission must bind one new execution record.", 500)
        with self.owner.lock:
            self.owner._state.setdefault(LEDGER, {})[self.submission_id] = {
                "route": self.route, "request": copy.deepcopy(self.request),
                "binding_hash": _hash(self.route, self.request), "record_id": record_id, "rejection": None}
            self.record_id = record_id

    def discard_uncommitted(self):
        """Remove only this ticket's uncommitted additions, never stream data."""
        if _durable(self.owner).get(LEDGER, {}).get(self.submission_id) is not None or self.record_id is None:
            return
        for pool in _POOLS:
            if pool in self.owner._state:
                self.owner._state[pool] = [record for record in self.owner._state[pool]
                    if not (record.get("id") == self.record_id and record.get("submission_id") == self.submission_id)]
        ledger = self.owner._state.get(LEDGER, {})
        receipt = ledger.get(self.submission_id)
        if receipt and receipt.get("record_id") == self.record_id:
            del ledger[self.submission_id]
        if not ledger and LEDGER not in _durable(self.owner):
            self.owner._state.pop(LEDGER, None)


def run_submission(owner, route, body, create, preflight=None):
    """Execute/recover one keyed logical request, or retain an unkeyed caller.

    `create(ticket)` uses the original owner start/source locking. It must stamp
    and bind a new record before persisting it and starting any worker.
    """
    key = body.get("submission_id")
    if key is None:
        if preflight is not None:
            preflight()
        return create(None)
    validate_submission_id(key)
    request = copy.deepcopy({name: value for name, value in body.items() if name != "submission_id"})
    _hash(route, request)  # Require a reproducible JSON wire request before work.
    with _MUTEX_GUARD:
        if not hasattr(owner, "_submission_mutex"):
            owner._submission_mutex = threading.RLock()
        mutex = owner._submission_mutex
    with mutex:
        with owner.lock:
            receipt = _existing(owner, key, route, request)
        if receipt is not None:
            return _reply(owner.envelope(), key, receipt, True)
        ticket = Submission(owner, key, route, request)
        try:
            if preflight is not None:
                preflight()
            result = create(ticket)
        except DomainError as error:
            with owner.lock:
                # A response/view exception after persistence never becomes
                # proof of rejection and never authorizes a second worker.
                if _durable(owner).get(LEDGER, {}).get(key) is not None:
                    raise
                ticket.discard_uncommitted()
                if 400 <= error.status < 500:
                    rejection = {"code": error.code, "message": error.message, "status": error.status}
                    owner._state.setdefault(LEDGER, {})[key] = {"route": route, "request": request,
                        "binding_hash": _hash(route, request), "record_id": None, "rejection": rejection}
                    owner._persist()
                    _reject(key, rejection)
            raise
        except Exception:
            with owner.lock:
                ticket.discard_uncommitted()
            raise
        with owner.lock:
            receipt = _existing(owner, key, route, request)
        if receipt is None or ticket.record_id != receipt["record_id"]:
            raise DomainError("submission_commit_missing", "The execution did not save its exact submission receipt.", 500)
        return _reply(result, key, receipt, False)
