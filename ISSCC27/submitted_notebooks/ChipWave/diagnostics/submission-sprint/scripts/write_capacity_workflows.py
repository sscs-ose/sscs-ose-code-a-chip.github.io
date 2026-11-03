"""Generate ordinary public Role/Recipe files; C0 has no platform recipe."""
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

import yaml
from chip_nebula.taskgraph.static_cli import load_compiled_recipe
from capacity_protocol import MODELS, WORKFLOWS
from capacity_workflows import CHECKLISTS, configuration
from study_protocol import write_json

BASE = """Read the frozen workload, interface, integration shell and resource contract.
Deliver a correct implementation and matching GDS within the shared Token, time,
tool-check and two-physical-attempt ceilings. You may plan, test and repair.
Only edit the designated RTL/configuration/tests/reports. Do not change inputs,
constraints, checkers, tool permissions, models or budgets, inspect reference/final
graders or other trials, invoke another model, or bypass the controlled tool entry.
All costs include coordination and failed attempts. A failed physical report is
evidence for revising the design, not permission for an extra attempt.
Use the same expert checklist supplied to every workflow."""

EXTRA = dict(
    architecture="Propose an implementable microarchitecture satisfying the same contract, with resource/latency risks. Write an actionable report; do not implement RTL.",
    timing="Use the available synthesis/physical reports to identify real timing and electrical causes, separating evidence from predictions. Give the RTL owner actionable findings.",
    power="Check activity/source alignment and power/energy implications in available reports. Recommend justified changes without fabricating measurements.",
    integration="Check the frozen CPU shell and workloads, execute available controlled physical checks when appropriate, and report actual results and remaining constraints.",
    autonomous="Autonomously plan, implement, verify, run physical implementation and repair as the resource ceilings permit.")


def write(project, workflow, model):
    project=Path(project)
    if model not in MODELS.values():
        raise ValueError("Unapproved model")
    cfg=configuration(workflow)
    write_json(project/"workflow-definition.json",cfg)
    (project/"expert-checklist.json").write_text(json.dumps(dict(CHECKLISTS,**EXTRA),indent=2)+"\n")
    if workflow=="C0":
        write_json(project/"native-entry.json",dict(model=model,reasoning="high",
            basic_prompt=BASE,orchestration="native Codex; common external tool/usage controls"))
        return None
    roles,recipes=project/".chip_nebula/roles",project/".chip_nebula/recipes"
    roles.mkdir(parents=True);recipes.mkdir(parents=True)
    for context in sorted({p["context"] for p in cfg["phases"]}):
        name="capacity-"+context
        role=dict(name=name,version=1,framework="codex",model=model,system_prompt=BASE,
                  accepted_types=["specification.source","rtl.snapshot","verification.report"],
                  produced_types=["rtl.snapshot","verification.report"])
        (roles/(name+".yaml")).write_text(yaml.safe_dump(role,sort_keys=False))
    tasks={};feedback=[];last_rtl=None;last_report=None
    implement="autonomous" if workflow=="C1" else "implementation"
    for item in cfg["phases"]:
        phase,context=item["phase"],item["context"]
        code=phase in ("implementation","revision","autonomous")
        intent=BASE+"\n"+CHECKLISTS.get(phase,EXTRA.get(phase,""))
        if code:
            intent+='\nReturn NEBULA_OUTPUT: {"rtl":{"module":"the exact task top module"}} and preserve the submitted source/configuration.'
        else:
            intent+=('\nSave a source-bound report under reports/'+phase+'/. Return NEBULA_OUTPUT: '
                     '{"report":{"subject":"the task design","verdict":"passed or failed",'
                     '"repair_summary":"specific observed defects or remaining constraints"}}. '
                     'Do not relabel a failed check as passing.')
        inputs=dict(source=dict(type="specification.source",**{"from":"$parameters.source"}))
        if last_rtl:
            inputs["rtl"]=dict(type="rtl.snapshot",**{"from":f"$tasks.{last_rtl}.outputs.rtl"})
        if last_report:
            inputs["review"]=dict(type="verification.report",**{"from":f"$tasks.{last_report}.outputs.report"})
        output = dict(rtl=dict(type="rtl.snapshot",paths=["rtl/**","configuration/**","reports/**"])) if code else dict(
            report=dict(type="verification.report",paths=[f"reports/{phase}/**","tests/**"]))
        writable=["tests/**","reports/**","build/**"]
        if code:writable+=["rtl/**","configuration/**"]
        tasks[phase]=dict(role="capacity-"+context,intent=intent,inputs=inputs,outputs=output,
            permission=dict(read=["spec/**","rtl/**","configuration/**","tools/**","tb/**","tests/**","reports/**","build/**",
                                  "expert-checklist.json","workflow-definition.json"],write=writable,tools=["python3","git"]),
            execution=dict(framework="codex",model=model,reasoning_effort="high",timeout_seconds=37800),
            max_attempts=1000)
        if code:
            last_rtl=phase
        else:
            last_report=phase
            if phase!="architecture":
                feedback.append(dict(source=phase,verdict="fail",target=implement,kind="feedback",
                    propagate=True,summary="Repair the concrete reported defect within unchanged shared budgets.",
                    summary_field="report.repair_summary"))
    path=recipes/"capacity.yaml"
    path.write_text(yaml.safe_dump(dict(name="capacity-"+workflow,version=2,
        parameters=dict(source="specification.source"),tasks=tasks,feedback=feedback),sort_keys=False))
    return path


def check():
    rows=[]
    with tempfile.TemporaryDirectory(prefix="capacity-recipes-") as tmp:
        for workflow in WORKFLOWS:
            root=Path(tmp)/workflow;root.mkdir()
            recipe=write(root,workflow,MODELS["luna"])
            if workflow=="C0":
                assert recipe is None and not (root/".chip_nebula").exists()
                rows.append(dict(workflow=workflow,native=True))
                continue
            for args in (["init","-q"],["config","user.name","Fixture"],
                         ["config","user.email","fixture@invalid"],["add","."],["commit","-qm","fixture"]):
                subprocess.run(["git",*args],cwd=root,check=True,capture_output=True)
            commit=subprocess.check_output(["git","rev-parse","HEAD"],cwd=root,text=True).strip()
            compiled=load_compiled_recipe(recipe,workflow_id="fixture",
                goal="Validate public workflow configuration",parameters=dict(source="task-input"),
                baseline_commit=commit,workers=1)
            assert len(compiled.tasks)==len(configuration(workflow)["phases"])
            rows.append(dict(workflow=workflow,tasks=len(compiled.tasks),roles=len(compiled.roles),
                             feedback_routes=len(compiled.feedback_routes)))
    return dict(passed=True,model_calls=0,rows=rows,
                scope="Native Recipe loader/compiler qualification; live TaskGraph dispatch remains separate")


if __name__=="__main__":
    result=check()
    root=Path(__file__).resolve().parents[1]
    write_json(root/"checks/public-recipe-compilation.json",result)
    for flow in WORKFLOWS:
        output=root/"workflow-templates"/flow
        if output.exists():raise ValueError("Existing template revision preserved")
        write(output,flow,MODELS["luna"])
    print(json.dumps(result))
