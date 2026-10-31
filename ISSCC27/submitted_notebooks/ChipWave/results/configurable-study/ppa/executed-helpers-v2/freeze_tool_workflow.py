#!/usr/bin/env python3
"""Freeze a declared deterministic physical task through public backend APIs.

No model planning is needed for this fixed tool command. The CPU/NPU design
workflow retains its original model-planned tasks and all historical evidence.
"""
from __future__ import annotations
import argparse
import json
import subprocess
from dataclasses import asdict
from pathlib import Path
from chip_nebula.taskgraph.domain import Artifact, ArtifactContent, ArtifactProducer, TaskBrief, path_scope_covers
from chip_nebula.taskgraph.static_cli import load_compiled_recipe
from chip_nebula.taskgraph.static_store import StaticTaskGraphStore


def freeze(root, recipe, workflow, source_design_delivery='artifact-e628d2d80e2f49ce9cca5c228f9925b5'):
    commit = subprocess.run(['git','rev-parse','HEAD'],cwd=root,text=True,capture_output=True,check=True).stdout.strip()
    tree = subprocess.run(['git','rev-parse','HEAD^{tree}'],cwd=root,text=True,capture_output=True,check=True).stdout.strip()
    compiled = load_compiled_recipe(recipe,workflow_id=workflow,goal='Physical acceptance of the frozen verified design',
                                   parameters={'rtl':'imported-main-rtl'},baseline_commit=commit,workers=1)
    assert len(compiled.tasks)==1 and compiled.tasks[0].executor.value=='tool'
    task=compiled.tasks[0]
    paths = tuple(p for p in ('rtl','spec','scripts','verification','physical','workbench.yaml','selected-delivery.json','tools','tb')
                  if (root/p).exists() and any(path_scope_covers(grant,p) for grant in task.permission.read_paths))
    assert 'rtl' in paths and 'physical' in paths
    artifact = Artifact(id='imported-main-rtl',type='rtl.snapshot',schema_version=1,
        producer=ArtifactProducer('external','verified-rtl-import','verified-rtl-import','case-evidence-import',1),
        content=ArtifactContent('git',commit,tree,paths),
        payload=dict(module=json.loads((root/'physical/chip-nebula/flow-definition.json').read_text())['top_module'],commit=commit,paths=list(paths)),
        metadata={'source_design_delivery':source_design_delivery,'planning':'deterministic frozen tool task'})
    brief=TaskBrief(objective=task.intent,deliverables=('Produce the declared physical report and complete raw EDA evidence.',),
        responsibilities=('Run only the declared deterministic command on immutable source and constraints.',),
        exclusions=('Do not modify RTL, tests or physical targets; do not fabricate passed results.',),
        completion_criteria=tuple('Pass '+g.name+' using the exact frozen gate parameters.' for g in task.hard_gates),
        collaboration=('No upstream or downstream Task collaborators; publish genuine evidence for workflow consumers.',))
    with StaticTaskGraphStore(root/'.chip_nebula/shared/memory/taskgraph-v2.db') as store:
        store.create_workflow(compiled.workflow,compiled.roles,compiled.tasks,[artifact],compiled.joint_analysis_groups,compiled.feedback_routes)
        store.freeze_briefs(workflow,{task.id:brief})
    subprocess.run(['git','update-ref','refs/chip-nebula/artifacts/'+artifact.id,commit],cwd=root,check=True)
    record=dict(workflow=workflow,baseline=commit,input_artifact=artifact.document(),brief=asdict(brief),planner='deterministic code, not human review')
    (root/'frozen-tool-workflow.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps({'workflow':workflow,'baseline':commit,'status':'ready'},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project',type=Path,required=True)
    parser.add_argument('--recipe',type=Path,required=True)
    parser.add_argument('--workflow',required=True)
    args=parser.parse_args()
    freeze(args.project.resolve(),args.recipe.resolve(),args.workflow)
