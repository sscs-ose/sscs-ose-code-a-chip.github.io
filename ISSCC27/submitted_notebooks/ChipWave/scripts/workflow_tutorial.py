"""Run configuration lessons through TaskGraph using saved RTL and real checks, offline."""
from __future__ import annotations

import argparse
import difflib
import json
import shutil
import subprocess
import time
from pathlib import Path

import yaml

from chip_nebula.models.task_manifest import AgentResult
from chip_nebula.taskgraph.domain import TaskBrief
from chip_nebula.taskgraph.static_cli import load_compiled_recipe, run_workflow
from chip_nebula.taskgraph.static_store import StaticTaskGraphStore
from chip_nebula.taskgraph.ip_library import IPLibrary
from run_configuration_study import DESIGN, git, prepare
from study_protocol import digest, write_json

CASE = Path(__file__).resolve().parents[1]


class SavedDesignReplay:
    def __init__(self, selected):
        self.selected = selected
        self.calls = []

    def dispatch(self, task, workspace, **kwargs):
        started = time.monotonic()
        if task.assigned_agent == 'tutorial-designer':
            for source in self.selected.glob('rtl/**/*'):
                if source.is_file():
                    destination = workspace/source.relative_to(self.selected)
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, destination)
            payload = {'rtl': {'module': 'nebula_npu_dot4'}}
        else:
            output = workspace/'build/tutorial-review'
            output.mkdir(parents=True, exist_ok=True)
            sources = sorted(workspace.glob('rtl/**/*.sv'))+sorted(workspace.glob('ip/**/*.sv'))
            commands = [['iverilog', '-g2012', '-s', 'npu_smoke_tb', '-o', str(output/'sim'),
                         *map(str, sources), 'tb/npu_smoke_tb.sv'], ['vvp', str(output/'sim')]]
            text = ''; codes = []
            for command in commands:
                result = subprocess.run(command, cwd=workspace, capture_output=True, text=True, timeout=90)
                text += result.stdout+result.stderr; codes.append(result.returncode)
                if result.returncode:
                    break
            (output/'review.log').write_text(text)
            report = {'subject': 'saved-generated-rtl', 'verdict': 'passed' if codes == [0,0] and
                      'NPU_SMOKE_PASS' in text else 'failed', 'repair_summary': text[-6000:]}
            write_json(workspace/'reports/review.json', report)
            payload = {'report': report}
        self.calls.append({'role': task.assigned_agent, 'mode': 'saved RTL / real checker replay',
                           'seconds': time.monotonic()-started})
        return AgentResult(success=True, execution_log='NEBULA_OUTPUT: '+json.dumps(payload))

    def terminate(self, *args):
        pass


def run(output, results):
    if output.exists():
        raise ValueError('Choose a new tutorial directory; old lessons are retained')
    output.mkdir(parents=True)
    builtin = CASE/'runtime/src/chip_nebula/configs/roles/rtl-designer.yaml'
    role = yaml.safe_load(builtin.read_text())
    role.update(name='tutorial-designer', system_prompt=DESIGN,
                accepted_types=['specification.source', 'verification.report'],
                produced_types=['rtl.snapshot'], framework='codex', model='gpt-6.1-sol')
    rows = []; previous = None
    for name, entry, roles in (('01-custom-role', 'fresh', 'single'),
                               ('02-add-reviewer', 'fresh', 'multi'),
                               ('03-check-before-review', 'fresh', 'multi'),
                               ('04-existing-ip', 'ip', 'multi')):
        lesson = output/name; root = lesson/'project'
        job = dict(input=entry, roles=roles, repetition=1, id=entry+'-'+roles+'-1')
        prepare(root, job)
        selected = results/'generation'/job['id']/'results/selected'
        final = json.loads((results/'generation'/job['id']/'results/result.json').read_text())['final_checker']
        for relative, expected in final['source_sha256'].items():
            if digest(selected/relative) != expected:
                raise ValueError('Saved design identity mismatch')
        (root/'.chip_nebula/roles/tutorial-designer.yaml').write_text(yaml.safe_dump(role, sort_keys=False))
        recipe = yaml.safe_load((root/'.chip_nebula/recipes/configuration.yaml').read_text())
        recipe['name'] = name
        recipe['tasks']['designer']['role'] = 'tutorial-designer'
        if roles == 'multi':
            reviewer = yaml.safe_load((root/'.chip_nebula/roles/study-verifier.yaml').read_text())
            reviewer['name'] = 'tutorial-reviewer'
            reviewer['accepted_types'].append('verification.report')
            (root/'.chip_nebula/roles/tutorial-reviewer.yaml').write_text(yaml.safe_dump(reviewer, sort_keys=False))
            recipe['tasks']['verifier']['role'] = 'tutorial-reviewer'
        if name in ('03-check-before-review', '04-existing-ip'):
            recipe['tasks']['audit']['inputs'] = {'rtl': {'type':'rtl.snapshot','from':'$tasks.designer.outputs.rtl'}}
            recipe['tasks']['verifier']['inputs']['smoke'] = {'type':'verification.report',
                'from':'$tasks.audit.outputs.report', 'release':{'field':'verdict','equals':'passed'}}
        path = root/'.chip_nebula/recipes/tutorial.yaml'
        path.write_text(yaml.safe_dump(recipe, sort_keys=False))
        git(root, 'add', '-f', '.chip_nebula/roles', str(path.relative_to(root)))
        git(root, 'commit', '-qm', 'Freeze this independent tutorial configuration')
        compiled = load_compiled_recipe(path, workflow_id='tutorial', goal='Learn one configuration change',
            parameters={'source':'common-source'}, baseline_commit=git(root,'rev-parse','HEAD'), workers=1)
        briefs = {task.id:TaskBrief(objective=task.intent,
            deliverables=tuple(out.name+': '+out.artifact_type for out in task.outputs),
            responsibilities=('Execute the frozen configuration with saved design deliveries and real checks.',),
            exclusions=('No model calls or claims of new generation.',),
            completion_criteria=('Publish the declared real check results.',),
            collaboration=tuple('task:'+other.id for other in compiled.tasks if other.id!=task.id)) for task in compiled.tasks}
        with StaticTaskGraphStore(root/'.chip_nebula/shared/memory/taskgraph-v2.db') as store:
            source = store.get_artifact('common-source')
            store.create_workflow(compiled.workflow, compiled.roles, compiled.tasks, [source], compiled.joint_analysis_groups, compiled.feedback_routes)
            store.freeze_briefs('tutorial', briefs)
        pool = SavedDesignReplay(selected)
        state = run_workflow(root, root/'.chip_nebula/shared/memory/taskgraph-v2.db', 'tutorial', pool, workers=1)
        with StaticTaskGraphStore(root/'.chip_nebula/shared/memory/taskgraph-v2.db') as store:
            tasks = [{'name':task.key, 'state':store.task_state(task.id).value,
                      'attempts':len(store.list_attempts(task.id))} for task in store.list_tasks('tutorial')]
        if state.value != 'complete' or any(task['state'] != 'satisfied' for task in tasks):
            raise RuntimeError('Tutorial check failed; inspect retained project')
        current = path.read_text()
        after = current if previous is not None else yaml.safe_dump(role, sort_keys=False)
        (lesson/'configuration.diff').write_text(''.join(difflib.unified_diff(
            (previous or builtin.read_text()).splitlines(True), after.splitlines(True),
            fromfile='previous configuration', tofile=name)))
        if entry == 'ip':
            (lesson/'configuration.diff').write_text((lesson/'configuration.diff').read_text()+
                '\n# Design entry changes to raw IP integration:\n'+(root/'spec/treatment.md').read_text())
        previous = current
        row = {'lesson':name, 'trial':job['id'], 'state':state.value, 'tasks':tasks,
               'calls':pool.calls, 'recipe_sha256':digest(path), 'model_calls':0,
               'source_sha256':final['source_sha256'],
               'dependencies': [{'from':item['from'].split('.')[1], 'to':name} for name,task in recipe['tasks'].items()
                                for item in task.get('inputs',{}).values() if item.get('from','').startswith('$tasks.')],
               'feedback':recipe['feedback']}
        write_json(lesson/'result.json', row); rows.append(row)
    library=IPLibrary(output/'ip-library-demo')
    package=library.import_package(CASE/'ip/model2gds-dot4')
    qualification=library.validate(package.package_id,package.version)
    if not qualification['records'] or any(row['verdict']!='passed' for row in qualification['records']):
        raise RuntimeError('Packaged-IP lesson failed; inspect retained qualification')
    write_json(output/'ip-library-qualification.json',qualification)
    write_json(output/'summary.json', {'passed':True, 'lessons':rows,
        'packaged_ip_demo':{'passed':True,'record':'ip-library-qualification.json',
            'scope':'Native IPLibrary import/qualification of the pre-existing full PE+adapter package. This package is never exposed to raw-IP generation trials.'},
        'scope':'Offline TaskGraph tutorial using actual independently checked trial deliveries. Configuration and checks execute now; AI generation is replayed from saved artifacts, not rerun.'})
    print('WORKFLOW_TUTORIAL_PASS: four frozen configurations; real Icarus checks; no model calls')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--results', type=Path, default=CASE/'results/configurable-study')
    args = parser.parse_args()
    run(args.output.resolve(), args.results.resolve())
