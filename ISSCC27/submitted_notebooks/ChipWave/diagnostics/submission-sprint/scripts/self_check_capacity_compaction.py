"""Reconcile a real compacted transcript without repeating any model calls."""
import json
import tempfile
from pathlib import Path

from capacity_live_usage import LiveUsage
from capacity_native_usage import NativeUsage
from capacity_meter import InvalidMeasurement
from capacity_snapshots import associate_captures
from study_portability import private_context
from study_protocol import write_json

ROOT=Path(__file__).resolve().parents[1]


def check():
    probe=ROOT/"checks/native-compaction-probe"
    private=private_context(ROOT,"capacity-compaction")
    rows=[]
    for path in (private/"sessions").rglob("*.jsonl"):
        rows += [json.loads(l) for l in path.read_text().splitlines()]
    requests={r["payload"]["response_id"]:r["payload"] for r in rows if r["type"]=="token_usage_record"}
    compact_ids={r["payload"]["compaction_response_id"] for r in rows if r["type"]=="compacted"}
    assert compact_ids and compact_ids <= requests.keys()
    expected=sum(r["usage"]["input_tokens"]+r["usage"]["output_tokens"] for r in requests.values())
    compact=sum(requests[k]["usage"]["total_tokens"] for k in compact_ids)
    for defect in ("missing_compaction_usage","changed_response_usage","duplicate_changed_identity"):
        altered=json.loads(json.dumps(rows))
        target=next(r for r in altered if r["type"]=="token_usage_record"
                    and r["payload"]["response_id"] in compact_ids)
        if defect=="missing_compaction_usage":
            altered.remove(target)
        elif defect=="changed_response_usage":
            target["payload"]["usage"]["input_tokens"]+=1
            target["payload"]["usage"]["total_tokens"]+=1
        else:
            duplicate=json.loads(json.dumps(target))
            duplicate["payload"]["usage"]["input_tokens"]+=1
            duplicate["payload"]["usage"]["total_tokens"]+=1
            altered.insert(altered.index(target)+1,duplicate)
        reader=NativeUsage()
        try:
            for row in altered:
                reader.observe(row["type"],row.get("payload",{}))
        except InvalidMeasurement:
            pass
        else:
            raise AssertionError("Damaged native response accounting accepted: "+defect)
    with tempfile.TemporaryDirectory() as temp:
        observer=LiveUsage(private,Path(temp)/"usage.json","gpt-6-luna",limit=50000)
        assert observer.finish()["actual_tokens"]==expected
        assert associate_captures(observer,probe/"runtime/tools/snapshots")>0
        snapshots=observer.ledger.state["snapshots"]
        tokens=[r["tokens"] for r in snapshots]
        assert tokens==sorted(tokens) and all(0<t<=expected for t in tokens)
        assert all(r["budget_admissible"]==(r["tokens"]<=50000) for r in snapshots)
        eligible=[r for r in snapshots if r["tokens"]<=50000]
        assert eligible and observer.ledger.at(50000)["id"]==eligible[-1]["id"]
        restarted=LiveUsage(private,Path(temp)/"usage.json","gpt-6-luna",limit=50000)
        assert restarted.finish()["actual_tokens"]==expected
    report=dict(passed=True,additional_model_calls=0,physical_runs=0,
        actual_logical_tokens=expected,compaction_tokens=compact,
        ui_token_counter=next((e.get("usage",{}).get("total_tokens") for e in reversed(json.loads((probe/"event-order.json").read_text())) if e.get("usage")),None),
        native_responses=len(requests),source_snapshot_tokens=tokens,overshoot_exclusion_observed=any(t>50000 for t in tokens),
        checks=["actual compaction included exactly once","sum of individual response usage reconciled",
                "50k latest eligible snapshot; each observed budget flag checked","durable reload",
                "missing/altered/duplicate-changed response usage rejected"],
        original_receipt_preserved=True,
        live_stop_with_compaction_qualified=False,
        scope="Offline replay of real protected compaction; live stopping under compaction still requires a probe")
    write_json(probe/"accounting-correction.json",report)
    return report


if __name__=="__main__":
    print(json.dumps(check()))
