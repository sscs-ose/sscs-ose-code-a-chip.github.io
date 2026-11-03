"""Associate protected tool captures with an already observed shared Token ledger."""
from __future__ import annotations

import json
import hashlib
from pathlib import Path

from capacity_meter import InvalidMeasurement
from capacity_native_usage import NativeUsage
from qualify_capacity_events import associate, associate_completed
from study_protocol import digest, write_json


def associate_captures(observer, capture_root, *, interrupted=False):
    observer.poll()
    existing = {row["id"]:row for row in observer.ledger.state["snapshots"]}
    captures = []
    for path in Path(capture_root).glob("*/capture.json"):
        row = json.loads(path.read_text())
        sources = {}
        for name, expected in row["source_sha256"].items():
            source = path.parent/name
            if Path(name).is_absolute() or ".." in Path(name).parts or source.is_symlink():
                raise InvalidMeasurement("Unsafe protected snapshot path")
            if digest(source) != expected:
                raise InvalidMeasurement("Protected source bytes changed")
            sources[name] = dict(sha256=expected, text=source.read_text())
        # Reads before the first RTL exists consume Tokens but submit no design.
        if not sources:
            continue
        if row["call_id"] in existing:
            previous = existing[row["call_id"]]
            if previous["session"] != row["session"] or previous["source_sha256"] != row["source_sha256"]:
                raise InvalidMeasurement("Previously scored capture changed identity/content")
            continue
        captures.append(dict(source_sha256=row["source_sha256"], completion_fence=row.get("completion_fence"), event="PostToolUse", call_id=row["call_id"], session=row["session"],
            sources=sources, capture_monotonic=row["capture_monotonic"],
            capture_phase=row.get("capture_phase"),response_admission=row.get("response_admission"),
            **{k:row.get(k) for k in ("parent_call_id","transcript_before","transcript_after")}))
    captures.sort(key=lambda row:row["capture_monotonic"])
    streams = {}
    for session in {row["session"] for row in captures}:
        paths = list((observer.private/"sessions").rglob("*-"+session+".jsonl"))
        if len(paths) != 1:
            raise InvalidMeasurement("No unique source transcript")
        events, offset = [], 0
        accounting = NativeUsage()
        for line in paths[0].read_bytes().splitlines(keepends=True):
            row = json.loads(line); payload = row.get("payload", {})
            usage = accounting.observe(row.get("type"),payload)
            if row.get("type") in ("response_item","event_msg"):
                events.append(dict(kind=row["type"], subtype=payload.get("type"),
                    call_id=payload.get("call_id"), event_key="byte-"+str(offset),
                    usage=usage if payload.get("type") == "token_count" else None))
            offset += len(line)
        streams[session] = events
    try:
        admitted = 0
        excluded = []
        for capture in captures:
            if capture.get("capture_phase")=="before_deterministic_tool":
                admission=capture.get("response_admission")
                if not admission or admission.get("parent_call_id")!=capture.get("parent_call_id"):
                    raise InvalidMeasurement("Frozen EDA source has no parent response admission")
                entry=observer.ledger.state["events"].get(capture["session"]+":"+admission["event_key"])
                if not entry or entry["sha256"]!=admission["usage_sha256"] or entry["global_tokens"]!=admission["tokens"]:
                    raise InvalidMeasurement("EDA admission differs from shared native usage")
                observer.ledger.snapshot(snapshot_id=capture["call_id"],
                    source_sha256={p:s["sha256"] for p,s in capture["sources"].items()},
                    session=capture["session"],event_key=admission["event_key"],
                    witness=dict(source_immutable=True,source_frozen_before_eda=True,
                        native_response_accounted=True,no_unaccounted_mutation=True,source_session_matches=True,
                        evidence="Protected immutable submission and response usage admitted before deterministic EDA"))
                admitted+=1
                continue
            events = streams[capture["session"]]
            if capture.get("capture_phase")=="after_controlled_tool":
                path = next((observer.private/"sessions").rglob("*-"+capture["session"]+".jsonl"))
                fence = capture["completion_fence"]
                prefix = path.read_bytes()[:fence["bytes"]]
                if len(prefix)!=fence["bytes"] or hashlib.sha256(prefix).hexdigest()!=fence["sha256"]:
                    raise InvalidMeasurement("Completed source transcript prefix changed")
                if associate_completed(events,capture,observer.ledger,interrupted=interrupted):
                    admitted += 1
                else:
                    excluded.append(dict(id=capture["call_id"],reason="interrupted before completion watermark"))
                continue
            parent = capture.get("parent_call_id") or capture["call_id"]
            outputs = [i for i,event in enumerate(events) if event.get("call_id")==parent
                       and event.get("subtype") in ("function_call_output","custom_tool_call_output")]
            if interrupted and (not outputs or not any(
                event.get("subtype")=="token_count" for event in events[outputs[-1]+1:])):
                excluded.append(dict(id=capture["call_id"],reason="interrupted before completed-response watermark"))
                continue
            associate(events, [capture], ledger=observer.ledger, interrupted=interrupted)
            admitted += 1
        if excluded:
            write_json(Path(capture_root).parent/"interrupted-captures.json",excluded)
    except InvalidMeasurement as error:
        observer.ledger.invalid(str(error))
    finally:
        write_json(observer.record, observer.ledger.state)
    return admitted
