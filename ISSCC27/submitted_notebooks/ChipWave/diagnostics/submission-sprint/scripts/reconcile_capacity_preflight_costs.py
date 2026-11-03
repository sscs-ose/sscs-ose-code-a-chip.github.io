"""Recompute actual preflight cost from immutable native response records."""
import json
from pathlib import Path

from capacity_native_usage import NativeUsage
from study_portability import private_context
from study_protocol import write_json

ROOT=Path(__file__).resolve().parents[1]


def reconcile():
    locations=[
        ("connectivity-luna",private_context(ROOT,"capacity-connectivity","gpt-6-luna")),
        ("connectivity-sol",private_context(ROOT,"capacity-connectivity","gpt-6-1-sol")),
        ("router-v4",private_context(ROOT,"capacity-router-probe-v4")),
        ("protected-context-v2",private_context(ROOT,"capacity-protected-context-v2")),
        ("compaction",private_context(ROOT,"capacity-compaction")),
        ("compaction-stop",private_context(ROOT,"capacity-compaction-stop")),
        ("eda-admission",private_context(ROOT,"capacity-eda-admission")),
        ("physical-wait",private_context(ROOT,"capacity-physical-wait")),
        ("taskgraph-v2",private_context(ROOT,"capacity-live-taskgraph-v2")),
        ("taskgraph-c2-v1",private_context(ROOT,"capacity-live-taskgraph-c2-v1")),
        ("taskgraph-c3-v1-failed",private_context(ROOT,"capacity-live-taskgraph-c3-v1")),
        ("taskgraph-c3-v2",private_context(ROOT,"capacity-live-taskgraph-c3-v2"))]
    summaries=[]
    for label,private in locations:
        records={}
        sessions=list((private/"sessions").rglob("*.jsonl"))
        assert sessions,label+" has no retained transcript"
        for path in sessions:
            reader=NativeUsage()
            for line in path.read_text().splitlines():
                row=json.loads(line)
                reader.observe(row["type"],row.get("payload",{}))
                if row["type"]=="token_usage_record":
                    payload=row["payload"]
                    key=payload["session_id"]+":"+payload["response_id"]
                    if key in records:
                        assert records[key]==payload
                    records[key]=payload
        total=sum(p["usage"]["input_tokens"]+p["usage"]["output_tokens"] for p in records.values())
        summaries.append(dict(probe=label,logical_tokens=total,native_responses=len(records)))
    result=dict(passed=True,logical_tokens=sum(r["logical_tokens"] for r in summaries),probes=summaries,
                native_responses=sum(r["native_responses"] for r in summaries),
                additional_model_calls=0,physical_runs=0,
                scope="Preparation costs only; unique response IDs include compaction, cache input counted")
    assert all(r["native_responses"]>0 and r["logical_tokens"]>0 for r in summaries),result
    write_json(ROOT/"checks/preflight-cost-reconciliation.json",result)
    print(json.dumps(result),flush=True)


if __name__=="__main__":
    reconcile()
