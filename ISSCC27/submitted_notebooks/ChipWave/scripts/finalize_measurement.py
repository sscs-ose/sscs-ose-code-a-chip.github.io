#!/usr/bin/env python3
"""Verify preserved engineering evidence and publish a conforming new Delivery.

Original failed Attempts remain failed. This creates a distinct, frozen
publication workflow; it does not rerun EDA or rewrite historical status.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
import yaml
from chip_nebula.taskgraph.domain import Artifact,ArtifactContent,ArtifactProducer,TaskBrief
from chip_nebula.taskgraph.static_store import StaticTaskGraphStore
from chip_nebula.taskgraph.static_cli import load_compiled_recipe
from chip_nebula.taskgraph.artifacts import load_schema_registry


VALIDATOR='''from pathlib import Path
import json,hashlib
root=Path.cwd()
manifest=json.loads(Path('measurement-input.json').read_text())
for item in manifest['files']:
    assert hashlib.sha256(Path(item['path']).read_bytes()).hexdigest()==item['sha256'],item['path']
report=json.loads(Path('build/rtl-to-gds/physical-report.json').read_text())
raw=report.pop('result_summary',report.get('raw_flow_summary'))
assert raw['status'] in ('passed','physical_passed')
assert raw['detailed_routing_violations']==0 and raw['drc_violations']==0 and raw['lvs']=='matched'
assert raw['metrics']['setup_violations']==0 and raw['metrics']['hold_violations']==0
assert raw['metrics']['clock_period_ns']==100
gds=list(Path('build/rtl-to-gds').glob('orfs-work/results/**/6_final.gds'))
assert len(gds)==1 and hashlib.sha256(gds[0].read_bytes()).hexdigest()==raw['gds']['sha256']
report['raw_flow_summary']=raw
report['original_attempt']=manifest['original_attempt']
report['publication_scope']='validated preserved completed engineering evidence; original schema-failed attempt is not changed'
Path('build/rtl-to-gds/physical-report.json').write_text(json.dumps(report,indent=2)+'\\n')
print('NEBULA_OUTPUT: '+json.dumps({'report':report}))
print('VALIDATED_PHYSICAL_PUBLICATION_PASS')
'''


def prepare(original,original_workflow,commit,destination,workflow):
    if destination.exists():raise ValueError('existing publication project preserved')
    with StaticTaskGraphStore(original/'.chip_nebula/shared/memory/taskgraph-v2.db') as s:
        attempt=s.list_attempts(original_workflow+':physical')[0]
        assert attempt.status.value=='failed' and 'Artifact output contract Gate failed' in attempt.diagnostics.get('failure_reason','')
        assert any(g.get('passed') and g.get('name')=='independent-physical-verdict' for g in attempt.diagnostics.get('gate_reports',[]))
    names=subprocess.run(['git','ls-tree','-r','--name-only',commit],cwd=original,capture_output=True,text=True,check=True).stdout.splitlines()
    selected=[]
    for name in names:
        path=Path(name)
        if name.startswith(('rtl/','physical/','spec/')) or name in ('workbench.yaml','selected-delivery.json'):
            selected.append(name)
        elif name.startswith('build/rtl-to-gds/') and (path.suffix in ('.json','.log','.rpt','.lyrdb','.lvsdb') or
              (path.name.startswith('6_final') and path.suffix in ('.gds','.v','.spef','.sdc','.cdl'))):
            selected.append(name)
    assert 'build/rtl-to-gds/physical-report.json' in selected
    destination.mkdir(parents=True)
    files=[]
    for name in selected:
        data=subprocess.run(['git','show',f'{commit}:{name}'],cwd=original,capture_output=True,check=True).stdout
        path=destination/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
        files.append({'path':name,'sha256':hashlib.sha256(data).hexdigest()})
    raw_report=json.loads((destination/'build/rtl-to-gds/physical-report.json').read_text())
    raw=raw_report['result_summary']
    assert raw['status']=='passed' and raw['lvs']=='matched' and raw['drc_violations']==0 and raw['detailed_routing_violations']==0
    fixed=dict(raw_report);fixed['raw_flow_summary']=fixed.pop('result_summary')
    manifest={'original_project':str(original),'original_workflow':original_workflow,'original_attempt':attempt.id,
              'original_preserved_commit':commit,'original_failure_reason':attempt.diagnostics['failure_reason'],
              'scope':'engineering acceptance passed; only reserved report-field schema was wrong','files':files}
    (destination/'measurement-input.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (destination/'scripts').mkdir();(destination/'scripts/validate_and_publish.py').write_text(VALIDATOR)
    role={'name':'case-physical-publication','version':1,'system_prompt':'Validate immutable completed engineering evidence and publish a conforming physical report. No EDA rerun, RTL changes or historical state edits.','accepted_types':['physical.report'],'produced_types':['physical.report']}
    roles=destination/'.chip_nebula/roles';recipes=destination/'.chip_nebula/recipes';roles.mkdir(parents=True);recipes.mkdir(parents=True)
    (roles/'case-physical-publication.yaml').write_text(yaml.safe_dump(role,sort_keys=False))
    recipe={'name':'validated-physical-publication','version':2,'parameters':{'measurement':'physical.report'},'tasks':{'physical':{
       'role':role['name'],'intent':'Verify complete preserved passed engineering evidence, exact source/GDS hashes, nominal clock, zero timing/DRC violations and matched LVS; correct reserved-field payload formatting and publish actual evidence.',
       'permission':{'read':['rtl/**','spec/**','physical/**','build/**','scripts/**','measurement-input.json','workbench.yaml','selected-delivery.json'],'write':['build/**'],'tools':['python3']},
       'inputs':{'measurement':{'type':'physical.report','from':'$parameters.measurement'}},
       'outputs':{'report':{'type':'physical.report','paths':['build/rtl-to-gds/**']}},'max_attempts':1,
       'execution':{'executor':'tool','command':'python3 scripts/validate_and_publish.py','timeout_seconds':120},
       'gates':[{'name':'validated-publication-verdict','template':'script-check','version':1,'on_failure':'report',
          'parameters':{'script':'python3','arguments':['-c',"import json; r=json.load(open('build/rtl-to-gds/physical-report.json')); assert r['verdict']=='passed'; assert 'result_summary' not in r; print('PUBLICATION_REPORT_PASS')"],'expected':'PUBLICATION_REPORT_PASS','timeout':30,'level':'L1','error_class':'measurement_publication_failed'}}]}}}
    rp=recipes/'publication.yaml';rp.write_text(yaml.safe_dump(recipe,sort_keys=False))
    (destination/'.gitignore').write_text('.chip_nebula/\n__pycache__/\n*.pyc\n')
    for cmd in (['git','init','-q'],['git','config','user.name','Validated evidence publication'],['git','config','user.email','automation@chipwave.invalid'],['git','add','.'],['git','add','-f','.chip_nebula/roles','.chip_nebula/recipes'],['git','commit','-qm','Freeze preserved passed measurements and corrected publication contract']):
        subprocess.run(cmd,cwd=destination,check=True)
    head=subprocess.run(['git','rev-parse','HEAD'],cwd=destination,capture_output=True,text=True,check=True).stdout.strip()
    tree=subprocess.run(['git','rev-parse','HEAD^{tree}'],cwd=destination,capture_output=True,text=True,check=True).stdout.strip()
    artifact=Artifact(id='preserved-physical-evidence',type='physical.report',schema_version=1,
       producer=ArtifactProducer('external','engineering-evidence-import',attempt.id,'validated-measurement-import',1),
       content=ArtifactContent('git',head,tree,('rtl','spec','physical','build','measurement-input.json','workbench.yaml','selected-delivery.json')),
       payload=fixed,metadata={'original_schema_failed_attempt':attempt.id,'original_preserved_commit':commit})
    artifact.validate(load_schema_registry())
    compiled=load_compiled_recipe(rp,workflow_id=workflow,goal='Publish independently validated preserved engineering results',parameters={'measurement':artifact.id},baseline_commit=head,workers=1)
    task=compiled.tasks[0]
    brief=TaskBrief(objective=task.intent,deliverables=('Validated physical.report and exact preserved physical files.',),responsibilities=('Verify all immutable input hashes and required physical conclusions; correct report serialization.',),exclusions=('Do not rerun EDA, change RTL or overwrite historical outcomes.',),completion_criteria=('Pass validated-publication-verdict and artifact-output-contract using genuine measured evidence.',),collaboration=('No other Task collaborators; deliver qualified evidence for the notebook.',))
    with StaticTaskGraphStore(destination/'.chip_nebula/shared/memory/taskgraph-v2.db') as store:
        store.create_workflow(compiled.workflow,compiled.roles,compiled.tasks,[artifact],compiled.joint_analysis_groups,compiled.feedback_routes)
        store.freeze_briefs(workflow,{task.id:brief})
    subprocess.run(['git','update-ref','refs/chip-nebula/artifacts/'+artifact.id,head],cwd=destination,check=True)
    print(json.dumps({'workflow':workflow,'baseline':head,'source_attempt_retained_failed':attempt.id},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--original',type=Path,required=True);p.add_argument('--original-workflow',required=True)
    p.add_argument('--commit',required=True);p.add_argument('--destination',type=Path,required=True);p.add_argument('--workflow',required=True)
    a=p.parse_args();prepare(a.original.resolve(),a.original_workflow,a.commit,a.destination.resolve(),a.workflow)
