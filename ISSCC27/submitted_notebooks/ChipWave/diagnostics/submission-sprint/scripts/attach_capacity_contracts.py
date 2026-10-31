"""Attach existing typed CSIR external contracts to locally checked task variants."""
import json
import shutil
from pathlib import Path

import yaml
from chip_nebula.csir.parser import parse_file
from chip_nebula.csir.provenance import empty_sidecar
from chip_nebula.taskgraph.acceptance_plan import validate_acceptance_plan
from chip_nebula.taskgraph.specir import blocking_diagnostics, run_check

from study_protocol import digest, write_json


def attach(task):
    public = task / "agent"
    spec = public / "spec"
    if (task/"build.json").exists():
        raise ValueError("Existing contract receipt preserved")
    meta = json.loads((spec/"interface.json").read_text())
    contract = (spec/"task.md").read_text()
    ports = [(p["direction"], p["name"], p["width"]) for p in meta["ports"]]
    lines = [f'module {meta["top"]} {{']
    lines += [f'  {"in" if d=="in" else "abstract out"} {n}: {"bit" if w==1 else "u"+str(w)}'
              for d, n, w in ports]
    lines += ["  apply behavior {", *[f"    {n}: {n}" for _, n, _ in ports], "  }", "}"]
    (spec/"draft.specir").write_text("\n".join(lines)+"\n")
    provenance = empty_sidecar(parse_file(spec/"draft.specir"))
    for node in provenance["nodes"]:
        node.update(requirements=["REQ-BEHAVIOR"], evidence=["task.md"], design_group="task.behavior")
    provenance["requirements"] = [dict(id="REQ-BEHAVIOR", classification="normative",
        status="mapped", mapping_kind="both", text=contract, evidence=["task.md"],
        mapped_nodes=[n["node_id"] for n in provenance["nodes"]], mapped_contracts=["behavior"])]
    write_json(spec/"provenance.json", provenance)
    write_json(spec/"contracts.json", dict(schema_version="0.1", contracts=[dict(
        id="behavior", requirements=["REQ-BEHAVIOR"], evidence=["task.md","../tb/development_tb.sv"],
        semantics=dict(language="English and executable interface scoreboard", body=contract),
        interface={n:dict(mode="observe" if d=="in" else "constrain",
                         type=dict(kind="bit") if w==1 else dict(kind="uint",width=w))
                   for d,n,w in ports},
        verification=dict(status="executable", backend="iverilog", adapter="../tools/check.py"))]))
    plan = dict(version=1,categories=[dict(key="functional", name="Public behavioral contract",
        cards=[dict(key="behavior",title="Independent final acceptance",
            items=[dict(id="behavior",title="Pass function and CPU integration",
                        detail=contract,requirement_ids=["REQ-BEHAVIOR"])])])],metrics=[])
    validate_acceptance_plan(plan)
    (spec/"acceptance.plan.yaml").write_text(yaml.safe_dump(plan,sort_keys=False))
    write_json(spec/"task.json",dict(id=task.name,top=meta["top"], task_validated=False,
        area_limit_um2=None,period_ps=100000,
        scope="Module reference qualification; integrated score calibration is separate"))
    (public/"tools").mkdir()
    (public/"tools/check.py").write_text('''import subprocess
from pathlib import Path
root=Path.cwd();out=root/'build/smoke';out.mkdir(parents=True,exist_ok=True)
sources=sorted(root.glob('rtl/**/*.sv'))+sorted(root.glob('rtl/**/*.v'))
if not sources or any(p.is_symlink() for p in sources):raise ValueError('Invalid sources')
subprocess.run(['iverilog','-g2012','-s','benchmark_check_tb','-o',str(out/'sim'),*map(str,sources),'tb/development_tb.sv'],check=True,timeout=60)
subprocess.run(['vvp',str(out/'sim')],check=True,timeout=60)
''')
    check = run_check(spec/"draft.specir")
    write_json(task/"csir-check.json", check)
    if not check["ok"] or blocking_diagnostics(check["diagnostics"]):
        raise ValueError("Typed CSIR check failed")
    (task/"grader/reference").mkdir()
    shutil.copy2(task/"grader/reference.sv",task/"grader/reference/design.sv")
    shutil.copy2(task/"grader/final_tb.sv",task/"grader/acceptance_tb.sv")
    write_json(task/"build.json",dict(task=dict(id=task.name),top=meta["top"],ports=ports,
        status="local_reference_and_typed_contract_checked_not_physical_or_integration_qualified",
        source_sha256={str(p.relative_to(task)):digest(p) for base in (public,task/"grader")
                       for p in sorted(base.rglob("*")) if p.is_file()}))
    return dict(task=task.name, csir_pass=True, behavioral_formal_proof=False,
                cpu_integration_pass=False, physical_pass=False)


if __name__ == "__main__":
    root=Path(__file__).resolve().parents[1]
    rows=[attach(root/"tasks"/name) for name in ("A1","A2","B1","B2")]
    write_json(root/"checks/task-contracts.json",dict(passed=True,rows=rows))
    print(json.dumps(rows))
