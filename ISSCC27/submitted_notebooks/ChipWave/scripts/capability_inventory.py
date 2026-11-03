"""Inventory the public built-in templates and the case-local configuration seams."""
from pathlib import Path
import argparse
import json
import yaml

from study_protocol import digest, write_json

CASE = Path(__file__).resolve().parents[1]


def inventory(output):
    configs=CASE/'runtime/src/chip_nebula/configs'
    roles=[]
    for path in sorted((configs/'roles').glob('*.yaml')):
        role=yaml.safe_load(path.read_text())
        roles.append({'name':role['name'],'version':role['version'],
            'accepted_types':role.get('accepted_types',[]),'produced_types':role.get('produced_types',[]),
            'skills':role.get('skills',[]),'path':str(path.relative_to(CASE)),'sha256':digest(path)})
    recipe=configs/'recipes/specification-to-gds.yaml'
    parsed=yaml.safe_load(recipe.read_text())
    assert len(parsed['tasks'])==20 and roles
    record={'public_runtime':'runtime/', 'browser_frontend_required':False,
        'builtin_roles':roles,'standard_recipe':{'name':parsed['name'],'path':str(recipe.relative_to(CASE)),
            'sha256':digest(recipe),'task_count':len(parsed['tasks']),'tasks':[
                {'name':name,'role':task['role'],'executor':task.get('execution',{}).get('executor','agent'),
                 'inputs':task.get('inputs',{}),'gates':[gate['name'] for gate in task.get('gates',[])]}
                for name,task in parsed['tasks'].items()]},
        'configuration_seams':[
            {'object':'Role','location':'.chip_nebula/roles/<name>.yaml',
             'fields':['name','version','system_prompt','accepted_types','produced_types','skills','framework','model']},
            {'object':'Task and dependencies','location':'.chip_nebula/recipes/<name>.yaml: tasks',
             'fields':['role','intent','inputs.*.from','inputs.*.release','outputs','execution','max_attempts']},
            {'object':'Task authorization','location':'recipe: tasks.<task>.permission',
             'fields':['read','write','tools']},
            {'object':'Feedback','location':'recipe: feedback',
             'fields':['source','verdict','target','kind','summary_field','propagate','when']},
            {'object':'Gate','location':'recipe: tasks.<task>.gates',
             'fields':['name','template','version','on_failure','parameters']},
            {'object':'Tool executor','location':'recipe: tasks.<task>.execution',
             'fields':['executor: tool','command','timeout_seconds']},
            {'object':'IP','location':'ip/model2gds-dot4/ and project-local immutable IP input',
             'fields':['source','license','ports','parameters','qualification','dependency lock']},
            {'object':'Skill','location':'runtime/src/chip_nebula/configs/skills/<name>/SKILL.md; project copies under .codex/skills/ or .claude/skills/',
             'fields':['Role.skills']}],
        'freeze_before_run':['source and IP bytes','roles and versions','recipe tasks/dependencies/feedback',
            'read/write/tool grants','model and reasoning level','tool/PDK versions and constraints',
            'budgets','development and final checkers','ranking and representative selection'],
        'case_additions':['dot4 single/multi-role recipes','shared 1200-second budget wrapper',
            'OS-isolated trial inputs and protected public-check receipts','PPA schemas and bounded tool evaluator',
            'candidate-bound activity/parasitic audit and scoring','offline tutorial artifact replay'],
        'limits':['The browser frontend is not part of this selected public distribution.',
            'The published example integrates soft RTL IP; hard-macro declarations do not constitute a supported automatic physical integration flow.',
            'The stock standard workflow may invoke its planner; formal configuration/PPA experiments freeze authored TaskBriefs and make zero planner calls.',
            'Templates supply reusable roles; adding roles alone does not prove better circuit quality.']}
    write_json(output,record)
    print(json.dumps({'builtin_roles':len(roles),'standard_tasks':20,'output':str(output)}))
    return record


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    inventory(parser.parse_args().output.resolve())
