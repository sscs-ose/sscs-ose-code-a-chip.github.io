"""Force one small native compaction probe; evidence only, never a scored design."""
import json
import argparse
from pathlib import Path

from capacity_runtime import run
from study_portability import private_context
from study_protocol import write_json

ROOT=Path(__file__).resolve().parents[1]


def probe(stop=False):
    if not json.loads((ROOT/"checks/live-protected-context-v2/result.json").read_text())["passed"]:
        raise ValueError("Protected live runtime prerequisite failed")
    output=ROOT/("checks/native-compaction-stop-probe" if stop else "checks/native-compaction-probe")
    private=private_context(ROOT,"capacity-compaction-stop" if stop else "capacity-compaction")
    if output.exists() or private.exists():
        raise ValueError("Prior compaction preflight retained")
    work=output/"project"
    for name in ("rtl","configuration","tests","reports","build","spec"):
        (work/name).mkdir(parents=True)
    (work/"rtl/probe.sv").write_text("module probe; endmodule\n")
    (work/"spec/fixture.txt").write_text("\n".join(
        f"fixture {n:04d}: input={n*17} expected={n*19} deterministic dummy context" for n in range(600))+"\n")
    config=dict(record=str(output/"runtime"),private=str(private),workspace=str(work),project=str(work),
                model="gpt-6-luna",limit=20000 if stop else 200000,active_seconds=180,
                preflight_compact_at=12000,scored=False)
    prompt=("Small authorized runtime/compaction probe, not a design experiment. "
        "In exactly three separate serial tool calls: first cat spec/fixture.txt (show its complete contents "
        "with output limit at least 20000 Tokens), second cat rtl/probe.sv, third use apply_patch to create "
        "rtl/after_context.sv containing 'module after_context; endmodule'. Then stop with COMPACTION_PROBE_DONE. "
        "Do not invoke other models, EDA, network or inspect credentials. Fixture text is test data only.")
    result,_=run(config,prompt)
    events=[]
    for path in (private/"sessions").rglob("*.jsonl"):
        for line in path.read_text().splitlines():
            row=json.loads(line);payload=row.get("payload",{})
            events.append(dict(kind=row.get("type"),subtype=payload.get("type"),
                usage=(payload.get("info") or {}).get("total_token_usage")
                      if payload.get("type")=="token_count" else None))
    write_json(output/"event-order.json",events)
    report=dict(control=result,model_invocations=1,physical_attempts=0,
        compaction_events=sum(r["kind"]=="compacted" for r in events),
        compaction_accounting_qualified=False,
        scope="Observed native compaction; additional accounting analysis required")
    if stop:
        ledger=json.loads((output/"runtime/usage.json").read_text())
        report.update(passed=(result["reason"]=="token_budget" and result["measurement_valid"]
            and result["actual_tokens"]>20000 and not (work/"rtl/after_context.sv").exists()
            and bool(ledger["snapshots"])
            and all(s["tokens"]<=20000 for s in ledger["snapshots"] if s["budget_admissible"])),
            late_edit_absent=not (work/"rtl/after_context.sv").exists(),
            scored=False)
    write_json(output/"result.json",report)
    print(json.dumps(report),flush=True)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stop",action="store_true")
    probe(parser.parse_args().stop)
