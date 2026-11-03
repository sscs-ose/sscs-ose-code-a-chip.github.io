"""Real model/tool admission with a delayed deterministic fixture, no EDA run."""
import json
import argparse
import time
from pathlib import Path

from capacity_runtime import run
from study_portability import private_context
from study_protocol import write_json

ROOT=Path(__file__).resolve().parents[1]


def probe(physical=False):
    label="capacity-physical-wait" if physical else "capacity-eda-admission"
    output=ROOT/("checks/native-physical-wait" if physical else "checks/native-eda-admission")
    private=private_context(ROOT,label)
    if output.exists() or private.exists():
        raise ValueError("Previous qualification evidence retained")
    work=output/"project"
    for name in ("rtl","configuration","tests","reports","build","spec"):
        (work/name).mkdir(parents=True)
    (work/"rtl/probe.sv").write_text("module probe(input a,output y);assign y=a;endmodule\n")
    starts=[]
    def fixture(source,identity):
        capture=json.loads((source/"capture.json").read_text())
        admission=capture["response_admission"]
        assert admission["tokens"]<=200000 and admission["response_id"]
        starts.append(dict(identity=identity,source=str(source.relative_to(output)),
                           admission=admission,started=time.monotonic()))
        write_json(output/"fixture-starts.json",starts)
        time.sleep(.1)
        prefixes={p:p.read_bytes() for p in (private/"sessions").rglob("*.jsonl")}
        time.sleep(130)
        if physical:
            assert prefixes and all(p.read_bytes()==prefix for p,prefix in prefixes.items()), "Model ran during excluded EDA wait"
        write_json(output/"fixture-finished.json",dict(epoch=time.time()))
        return dict(status="passed",evidence="Delayed fixture only; no synthesis or physical implementation",
                    exit_code=0,output="DETERMINISTIC_FIXTURE_COMPLETE: no EDA was executed.\n")
    config=dict(record=str(output/"runtime"),private=str(private),workspace=str(work),project=str(work),
                model="gpt-6-luna",limit=200000,active_seconds=180,scored=False)
    command="physical" if physical else "synth"
    result,_=run(config,
        "This is a tiny authorized tool admission probe, not a design experiment. "
        f"Run exactly 'capacity-check {command}' once. This invokes a documented delayed fixture, not EDA. "
        "Wait until it finishes, then run exactly 'cat rtl/probe.sv' in a separate tool call and stop. "
        "Do not edit files, invoke other models, use network or inspect credentials.",
        handlers={"physical" if physical else "synthesis_sta":fixture})
    ledger=json.loads((output/"runtime/usage.json").read_text())
    report=dict(passed=result["passed"] and len(starts)==1
                and any(s["witness"].get("source_frozen_before_eda") for s in ledger["snapshots"]),
        control=result,model_invocations=1,physical_attempts=0,real_synthesis_runs=0,
        fixture_calls=len(starts),source_snapshots=len(ledger["snapshots"]),
        scope="Live native usage known before delayed deterministic fixture; no physical backend qualified")
    finished=json.loads((output/"fixture-finished.json").read_text())["epoch"] if (output/"fixture-finished.json").exists() else float("inf")
    reads=[]
    for request in (output/"runtime/tools").glob("*-request.json"):
        event=json.loads(request.read_text())
        if event.get("tool_input",{}).get("command","").strip()!="cat rtl/probe.sv":continue
        response=work/"tools/.capacity-results"/(request.name.removesuffix("-request.json")+".json")
        value=json.loads(response.read_text()) if response.exists() else {}
        reads.append(request.stat().st_mtime>=finished and value.get("exit_code")==0 and "module probe" in value.get("output",""))
    report["post_wait_read_passed"]=bool(reads) and all(reads)
    report["passed"] &= report["post_wait_read_passed"]
    report["scope"]="130-second live native fixture with tree-wide pause and successful post-wait read; no chip-design session or EDA run"
    if physical:
        report["passed"] &= result["physical_seconds"]>=130 and result["active_seconds"]<result["wall_seconds"]-125
        report["model_paused_during_excluded_wait"]=bool(report["passed"])
    write_json(output/"result.json",report)
    print(json.dumps(report),flush=True)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--physical",action="store_true")
    probe(parser.parse_args().physical)
