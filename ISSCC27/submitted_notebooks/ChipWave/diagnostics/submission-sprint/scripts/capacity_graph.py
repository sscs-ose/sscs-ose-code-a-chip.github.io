"""Freeze public Recipe/TaskGraph briefs without an unmetered planning agent."""
import json
import subprocess
from dataclasses import asdict
from pathlib import Path

from chip_nebula.taskgraph.domain import Artifact, ArtifactContent, ArtifactProducer, TaskBrief
from chip_nebula.taskgraph.static_cli import load_compiled_recipe
from chip_nebula.taskgraph.static_store import StaticTaskGraphStore
from capacity_tool_router import CLIENT
from study_protocol import digest, write_json
from write_capacity_workflows import write


def freeze(project,workflow,model,*,recipe=None):
    project=Path(project).resolve()
    recipe=write(project,workflow,model) if recipe is None else Path(recipe).resolve()
    if recipe is None:
        raise ValueError("C0 uses native execution, not TaskGraph")
    if not recipe.is_relative_to(project):
        raise ValueError("Workflow configuration must belong to the frozen project")
    for name in ("tools","rtl","configuration","tests","reports","build"):
        (project/name).mkdir(exist_ok=True)
    (project/"tools/capacity_bridge.py").write_text(CLIENT)
    (project/".gitignore").write_text(".chip_nebula/\ntools/.capacity-results/\nbuild/\n__pycache__/\n*.pyc\n")
    for args in (["init","-q"],["config","user.name","ChipNebula experiment"],
                 ["config","user.email","automation@chipnebula.invalid"],["add","."],
                 ["add","-f",".chip_nebula/roles",".chip_nebula/recipes"],
                 ["commit","-qm","Freeze task, roles and deterministic briefs"]):
        subprocess.run(["git",*args],cwd=project,check=True,capture_output=True)
    def git(*args):
        return subprocess.check_output(["git",*args],cwd=project,text=True).strip()
    commit,tree=git("rev-parse","HEAD"),git("rev-parse","HEAD^{tree}")
    compiled=load_compiled_recipe(recipe,workflow_id="capacity",goal="Execute the frozen workload-to-GDS protocol",
        parameters=dict(source="capacity-task"),baseline_commit=commit,workers=1)
    description=project/"spec/task.md"
    if not description.is_file():
        raise ValueError("A public task book is required")
    artifact=Artifact(id="capacity-task",type="specification.source",schema_version=1,
        producer=ArtifactProducer("external","capacity-protocol","frozen-input","experiment-author",1),
        content=ArtifactContent("git",commit,tree,("spec","tools")),
        payload=dict(source_name="Frozen workload task",media_type="text/markdown",
            content=description.read_text(),content_digest="sha256:"+digest(description),
            received_at="2026-10-21T00:00:00+00:00"))
    briefs={task.id:TaskBrief(objective=task.intent,
        deliverables=tuple(o.name+": "+o.artifact_type for o in task.outputs),
        responsibilities=("Follow the common resource and tool contract; use actual captured reports.",),
        exclusions=("Do not change hidden/frozen inputs or invoke other models.",),
        completion_criteria=("Submit declared artifacts with truthful evidence and failure reports.",),
        collaboration=tuple("task:"+other.id for other in compiled.tasks if other.id!=task.id)
                      or ("Work within this single role and the same controlled tool interface.",))
        for task in compiled.tasks}
    database=project/".chip_nebula/shared/memory/taskgraph-v2.db"
    with StaticTaskGraphStore(database) as store:
        store.create_workflow(compiled.workflow,compiled.roles,compiled.tasks,[artifact],
                              compiled.joint_analysis_groups,compiled.feedback_routes)
        store.freeze_briefs("capacity",briefs)
    git("update-ref","refs/chip-nebula/artifacts/capacity-task",commit)
    write_json(project/"frozen-capacity-workflow.json",dict(workflow=workflow,baseline=commit,
        planner="deterministic declared briefs; no model/planning invocation",
        briefs={key:asdict(value) for key,value in briefs.items()},input_artifact=artifact.document()))
    return database
