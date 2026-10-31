"""Three small real public-adapter invocations, excluded from design experiments."""
import json
import argparse
import re
import subprocess
from pathlib import Path

from chip_nebula.models.task_manifest import TaskManifest
from capacity_context import ContextPool
from capacity_tool_router import CLIENT
from study_portability import private_context
from study_protocol import write_json

ROOT=Path(__file__).resolve().parents[1]


def run(revision=None):
    for check in ("runtime-boundaries","shared-source-association","tool-router"):
        if not json.loads((ROOT/"checks"/(check+".json")).read_text())["passed"]:
            raise ValueError("Runtime prerequisite failed")
    if revision and not re.fullmatch(r"[a-z0-9-]+",revision):
        raise ValueError("Unsafe explicit preflight revision")
    suffix="-"+revision if revision else ""
    output=ROOT/("checks/live-protected-context"+suffix)
    private=private_context(ROOT,"capacity-protected-context"+suffix)
    if output.exists() or private.exists():
        raise ValueError("Existing actual preflight retained")
    work=output/"project"
    for name in ("rtl","configuration","tests","reports","build","tools","spec"):
        (work/name).mkdir(parents=True)
    (work/"tools/capacity_bridge.py").write_text(CLIENT)
    (work/".gitignore").write_text("tools/.capacity-results/\nbuild/\n")
    (work/"spec/task.txt").write_text("Runtime probe only, no design experiment.\n")
    for args in (["init","-q"],["config","user.name","Runtime Fixture"],
                 ["config","user.email","runtime@invalid"],["add","."],["commit","-qm","Frozen probe"]):
        subprocess.run(["git",*args],cwd=work,check=True,capture_output=True)
    runtime=dict(record=str(output/"runtime"),limit=200000,active_seconds=180,scored=False)
    pool=ContextPool(private,output/"contexts.json","gpt-6-luna",runtime=runtime)
    descriptions=[
        ("implementer","implementation", ["rtl/**","configuration/**","tests/**","reports/**","build/**"],
         "Use one native apply_patch call to create rtl/probe.sv containing "
         "'module probe(input a, output y); assign y=a; endmodule'. "
         "Then stop. Tiny authorized runtime probe; no EDA, other agents, network or credential inspection."),
        ("reviewer","review",["tests/**","reports/**","build/**"],
         "Use a read tool once to inspect rtl/probe.sv, then apply_patch to write "
         "reports/review.txt containing 'Inspected combinational wire'. Do not edit RTL. "
         "Use separate serial calls, then stop. This is a tiny runtime probe; no EDA or other agents."),
        ("implementer","revision",["rtl/**","configuration/**","tests/**","reports/**","build/**"],
         "Continue your earlier probe context. Read reports/review.txt in one call, then "
         "apply_patch to create rtl/continuation.sv containing 'module continuation; endmodule'. "
         "Use separate serial calls, then stop. No EDA or other agents.")]
    rows=[]
    for role,stage,write_paths,prompt in descriptions:
        task=TaskManifest(task_id=stage,feature_id="capacity-runtime-probe",stage=stage,
            assigned_agent=role,description=prompt,prompt_override=prompt,model="gpt-6-luna",
            reasoning_effort="high",write_paths=write_paths,timeout=240,live_workspace=True)
        result=pool.dispatch(task,work,project_root=work)
        row=dict(role=role,stage=stage,success=result.success,session_id=result.session_id,
                 error=result.error,files_modified=result.files_modified)
        rows.append(row);write_json(output/"dispatches.json",rows)
        if not result.success:
            break
    ledger=json.loads((output/"runtime/usage.json").read_text())
    calls=list((output/"runtime/invocations").glob("*/result.json"))
    outcomes=[json.loads(p.read_text()) for p in calls]
    report=dict(passed=len(rows)==3 and all(r["success"] for r in rows)
        and rows[0]["session_id"]==rows[2]["session_id"]!=rows[1]["session_id"]
        and all(r["passed"] for r in outcomes),
        model_calls=len(calls),physical_attempts=0,actual_logical_tokens=ledger["actual_tokens"],
        roles=len({r["session_id"] for r in rows}),snapshots=len(ledger["snapshots"]),
        measurement_valid=ledger["valid"],formal_qualified=False,
        scope="Public adapter with protected tools/shared meter; no TaskGraph, compaction or EDA qualification")
    write_json(output/"result.json",report)
    print(json.dumps(report),flush=True)
    return report


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revision")
    raise SystemExit(0 if run(parser.parse_args().revision)["passed"] else 1)
