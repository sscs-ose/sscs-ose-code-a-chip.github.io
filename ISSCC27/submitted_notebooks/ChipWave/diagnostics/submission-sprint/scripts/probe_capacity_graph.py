"""One real native role through the public Recipe/TaskGraph and protected runner."""
import json
import argparse
import re
from pathlib import Path

import yaml
from chip_nebula.taskgraph.static_cli import run_workflow
from chip_nebula.taskgraph.static_store import StaticTaskGraphStore
from capacity_context import ContextPool
from capacity_graph import freeze
from study_portability import private_context
from study_protocol import write_json
from write_capacity_workflows import write

ROOT=Path(__file__).resolve().parents[1]


def probe(revision=None, workflow="C1"):
    if revision and not re.fullmatch(r"[a-z0-9-]+",revision):
        raise ValueError("Unsafe preflight revision")
    suffix=("-"+workflow.lower() if workflow!="C1" else "")+("-"+revision if revision else "")
    output=ROOT/("checks/live-taskgraph"+suffix)
    private=private_context(ROOT,"capacity-live-taskgraph"+suffix)
    if output.exists() or private.exists():
        raise ValueError("Previous live graph probe retained")
    project=output/"project";(project/"spec").mkdir(parents=True)
    prompt=("Authorized runtime preflight, not a chip-design experiment. Use one native apply_patch to "
            "write rtl/fixture.sv containing 'module capacity_fixture(input a,output y);assign y=a;endmodule'. "
            "Then return NEBULA_OUTPUT: {\"rtl\":{\"module\":\"capacity_fixture\"}}. "
            "No EDA, extra models, network, credential inspection or other changes.")
    (project/"spec/task.md").write_text(prompt+"\n")
    recipe=write(project,workflow,"gpt-6-luna")
    definition=yaml.safe_load(recipe.read_text())
    for phase, task in definition["tasks"].items():
        if phase in ("autonomous", "implementation"):
            instruction=prompt
        elif phase=="revision":
            instruction=("Runtime fixture continuation. Read rtl/fixture.sv and inherited reports. "
                "Use apply_patch to add a comment '// reviewed' to rtl/fixture.sv, preserving the module. "
                'Return NEBULA_OUTPUT: {"rtl":{"module":"capacity_fixture"}}. No extra tools or EDA.')
        else:
            instruction=("Runtime fixture review, not a chip experiment. Read rtl/fixture.sv, confirm y=a, "
                f"then use apply_patch to write reports/{phase}/report.json with "
                '{"subject":"capacity_fixture","verdict":"passed","repair_summary":"Identity wire observed"}. '
                'Return NEBULA_OUTPUT: {"report":{"subject":"capacity_fixture","verdict":"passed",'
                '"repair_summary":"Identity wire observed"}}. Do not edit RTL or invoke EDA.')
        task["intent"]=instruction
        task["max_attempts"]=1
        task["execution"]["timeout_seconds"]=240
    recipe.write_text(yaml.safe_dump(definition,sort_keys=False))
    for role in (project/".chip_nebula/roles").glob("*.yaml"):
        fields=yaml.safe_load(role.read_text());fields["system_prompt"]=(
            "This is a tiny runtime qualification fixture. Follow this task's stage instruction. "
            "No extra models, network, credentials or EDA. Use only scoped native reads and apply_patch.")
        role.write_text(yaml.safe_dump(fields,sort_keys=False))
    database=freeze(project,workflow,"gpt-6-luna",recipe=recipe)
    pool=ContextPool(private,output/"contexts.json","gpt-6-luna",
                     runtime=dict(record=str(output/"runtime"),limit=300000,active_seconds=600,scored=False))
    status=run_workflow(project,database,"capacity",pool,workers=1)
    with StaticTaskGraphStore(database) as store:
        snapshot=store.graph_snapshot("capacity")
        attempts=[attempt for task in store.list_tasks("capacity") for attempt in store.list_attempts(task.id)]
    write_json(output/"graph.json",snapshot)
    usage_path=output/"runtime/usage.json"
    usage=json.loads(usage_path.read_text()) if usage_path.exists() else {}
    contexts=json.loads((output/"contexts.json").read_text()) if (output/"contexts.json").exists() else {}
    expected_contexts=3 if workflow=="C3" else 1
    report=dict(passed=status.value=="complete" and bool(usage.get("valid"))
                and bool(usage.get("snapshots")) and len(set(contexts.values()))==expected_contexts,
                workflow=workflow, contexts=len(contexts), status=status.value,attempts=len(attempts),
                actual_logical_tokens=usage.get("actual_tokens",0),physical_attempts=0,
                model_invocations=len(list((output/"runtime/invocations").glob("*/result.json"))),
                scope="Real native TaskGraph with explicit tiny fixture recipe; not a formal design sample")
    write_json(output/"result.json",report)
    print(json.dumps(report),flush=True)
    return report


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revision")
    parser.add_argument("--workflow", choices=("C1", "C2", "C3"), default="C1")
    args=parser.parse_args()
    raise SystemExit(0 if probe(args.revision, args.workflow)["passed"] else 1)
