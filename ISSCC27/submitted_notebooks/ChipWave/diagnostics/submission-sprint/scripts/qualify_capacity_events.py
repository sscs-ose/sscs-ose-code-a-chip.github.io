"""Join captured post-tool snapshots to a subsequent cumulative usage watermark."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from capacity_meter import InvalidMeasurement, TokenLedger
from study_protocol import write_json

CALLS = ("function_call", "custom_tool_call")
OUTPUTS = ("function_call_output", "custom_tool_call_output")


def associate(events, hooks, limit=1_000_000, ledger=None, interrupted=False):
    sessions = {row["session"] for row in hooks if row.get("session")}
    if len(sessions) != 1:
        raise InvalidMeasurement("Exactly one source session is required per stream")
    session = sessions.pop()
    calls, outputs, usages = {}, {}, []
    for index, event in enumerate(events):
        subtype, call = event.get("subtype"), event.get("call_id")
        if event.get("kind") == "response_item" and subtype in CALLS:
            if not call or call in calls:
                raise InvalidMeasurement("Missing/duplicate tool call identity")
            calls[call] = index
        if event.get("kind") == "response_item" and subtype in OUTPUTS:
            if call not in calls or call in outputs:
                raise InvalidMeasurement("Unmatched/repeated tool output")
            outputs[call] = index
        if event.get("kind") == "event_msg" and subtype == "token_count":
            if event.get("usage") is None:
                raise InvalidMeasurement("Missing cumulative usage")
            usages.append(index)
    unfinished = set(calls)-set(outputs)
    trailing_only = (len(unfinished)==1 and
                     calls[next(iter(unfinished))]>max(outputs.values(),default=-1))
    if (unfinished and not (interrupted and trailing_only)) or not usages:
        raise InvalidMeasurement("Incomplete tool/usage stream")
    snapshots = {}
    for hook in hooks:
        if hook["event"] != "PostToolUse" or not hook["sources"]:
            continue
        call = hook.get("parent_call_id") or hook.get("call_id")
        if call is None:
            tail_calls = [row[2] for row in hook["sequence_tail"]
                          if row[0] == "response_item" and row[1] in CALLS]
            if not tail_calls:
                raise InvalidMeasurement("No call identity for captured snapshot")
            call = tail_calls[-1]
        if call not in outputs:
            raise InvalidMeasurement("Captured tool never completed")
        candidates = [index for index in usages if index > outputs[call]]
        if not candidates:
            raise InvalidMeasurement("Tool completed without following usage watermark")
        watermark = candidates[0]
        # Do not infer ownership when another mutation-capable call intervenes.
        if any(calls[call] < position < watermark for other, position in calls.items() if other != call):
            raise InvalidMeasurement("Overlapping calls require a stronger source observer")
        for path, source in hook["sources"].items():
            if Path(path).is_absolute() or ".." in Path(path).parts:
                raise InvalidMeasurement("Unsafe snapshot path")
            if hashlib.sha256(source["text"].encode()).hexdigest() != source["sha256"]:
                raise InvalidMeasurement("Captured bytes do not match their digest")
        snapshot_id = hook.get("call_id") or call
        if snapshot_id in snapshots:
            raise InvalidMeasurement("Repeated post-tool snapshot")
        if hook.get("parent_call_id"):
            before, after = hook.get("transcript_before"), hook.get("transcript_after")
            if not before or not after or any(w.get("parent_call_id") != call for w in (before, after)):
                raise InvalidMeasurement("Missing protected parent-call witnesses")
        snapshots[snapshot_id] = dict(watermark=watermark, hook=hook)
    meter = ledger if ledger is not None else TokenLedger(limit=limit)
    for index in usages:
        event_key = events[index].get("event_key", str(index))
        if ledger is not None and session+":"+event_key not in meter.state["events"]:
            raise InvalidMeasurement("Shared observer has not accounted for this watermark")
        meter.record(session, event_key, events[index]["usage"])
        for call, item in snapshots.items():
            if item["watermark"] != index:
                continue
            meter.snapshot(snapshot_id=call,
                source_sha256={p: source["sha256"] for p, source in item["hook"]["sources"].items()},
                session=session, event_key=event_key,
                witness=dict(source_immutable=True, tool_completed=True,
                             usage_after_capture=True, no_unaccounted_mutation=True,
                             source_session_matches=True,
                             evidence="serial post-tool capture and next cumulative usage watermark"))
    if not snapshots:
        raise InvalidMeasurement("No captured source snapshot")
    return meter


def associate_completed(events, capture, ledger, *, interrupted=False):
    """Charge a completed controlled tool to the first usage event after its sealed source."""
    session = capture["session"]
    admission = capture.get("response_admission") or {}
    origin = capture.get("parent_call_id")
    entry = ledger.state["events"].get(session+":"+admission.get("event_key",""))
    fence = capture.get("completion_fence") or {}
    if (not entry or admission.get("parent_call_id")!=origin
            or entry["sha256"]!=admission.get("usage_sha256")
            or entry["global_tokens"]!=admission.get("tokens")
            or type(fence.get("bytes")) is not int or fence["bytes"]<=0
            or not isinstance(fence.get("sha256"),str) or len(fence["sha256"])!=64):
        raise InvalidMeasurement("Completed tool lacks immutable response admission/fence")
    if not any(e.get("call_id")==origin and e.get("subtype") in CALLS for e in events):
        raise InvalidMeasurement("Completed tool has no originating model call")
    watermarks = [e for e in events if e.get("subtype")=="token_count"
                  and int(e["event_key"].removeprefix("byte-"))>=fence["bytes"]]
    if not watermarks:
        if interrupted:return False
        raise InvalidMeasurement("No usage watermark after completed source capture")
    key = watermarks[0]["event_key"]
    if session+":"+key not in ledger.state["events"]:
        raise InvalidMeasurement("Completion usage has not been accounted")
    ledger.snapshot(snapshot_id=capture["call_id"],source_sha256=capture["source_sha256"],
        session=session,event_key=key,witness=dict(source_immutable=True,tool_completed=True,
            response_admitted_before_execution=True,completion_prefix_bound=True,
            usage_after_capture=True,no_unaccounted_mutation=True,source_session_matches=True,
            evidence="Protected tool completion and first subsequent native usage watermark"))
    return True


def check(campaign):
    rows = []
    for folder in sorted((campaign / "checks").glob("connectivity-*")):
        events = json.loads((folder / "event-order.json").read_text())
        hooks = json.loads((folder / "hook-observations.json").read_text())
        meter = associate(events, hooks)
        result = json.loads((folder / "result.json").read_text())
        assert meter.summary()["actual_tokens"] == result["actual_usage"]["total_tokens"]
        assert meter.state["snapshots"][-1]["source_sha256"]["rtl/probe.sv"] == result["source_sha256"]
        for broken in ("missing_usage", "truncated", "modified_bytes", "missing_output"):
            e, h = json.loads(json.dumps(events)), json.loads(json.dumps(hooks))
            if broken == "missing_usage":
                e = [r for r in e if r["subtype"] != "token_count"]
            elif broken == "truncated":
                last_output = max(i for i, r in enumerate(e) if r["subtype"] in OUTPUTS)
                e = e[:last_output+1]
            elif broken == "modified_bytes":
                next(r for r in h if r["event"] == "PostToolUse" and r["sources"])["sources"]["rtl/probe.sv"]["text"] += "x"
            else:
                e = [r for r in e if r["subtype"] not in OUTPUTS]
            try:
                associate(e, h)
            except InvalidMeasurement:
                pass
            else:
                raise AssertionError("Damaged event stream accepted: " + broken)
        # Replay a tighter ceiling against the same real stream; no model rerun.
        boundary = meter.state["snapshots"][0]["tokens"]
        tight = associate(events, hooks, limit=boundary-1)
        assert tight.at(boundary-1) is None
        assert tight.summary()["overshoot_tokens"] > 0
        write_json(folder / "associated-usage.json", meter.state)
        rows.append(dict(model=result["model"], snapshots=len(meter.state["snapshots"]),
                         actual_tokens=meter.summary()["actual_tokens"],
                         first_snapshot_tokens=boundary, damaged_streams_rejected=4))
    assert len(rows) == 2
    report = dict(passed=True, probes=rows, additional_model_calls=0, physical_runs=0,
                  scope="serial two-tool probe streams only; no concurrent/background/compaction qualification",
                  formal_meter_qualified=False)
    write_json(campaign / "checks/live-event-association.json", report)
    return report


if __name__ == "__main__":
    print(json.dumps(check(Path(__file__).resolve().parents[1])))
