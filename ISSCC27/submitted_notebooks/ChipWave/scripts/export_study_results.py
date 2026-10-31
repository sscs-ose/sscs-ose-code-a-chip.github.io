"""Export used experiment evidence, excluding private contexts and rebuildable objects."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import gzip
import json
from pathlib import Path
import shutil

from chip_nebula.taskgraph.static_store import StaticTaskGraphStore
from package_submission import SECRET, gzip_info
from study_protocol import digest, write_json

CASE=Path(__file__).resolve().parents[1]
EXCLUDED={'.git','__pycache__','obj','obj_dir'}
DRAFT_CHECK_PREFIXES=('notebook-draft-','foundation-export-','build-notebook-draft-','preview-')


def copy_evidence(source,destination):
    if source.is_symlink():raise ValueError('Unexpected evidence symlink: '+str(source))
    if not source.is_file():return
    if source.stat().st_size<10_000_000 and SECRET.search(source.read_bytes()):
        raise ValueError('Potential credential in selected evidence: '+str(source))
    destination.parent.mkdir(parents=True,exist_ok=True)
    compressed=source.suffix in ('.vcd','.lvsdb') or source.stat().st_size>90_000_000
    target=destination.with_name(destination.name+'.gz') if compressed else destination
    if compressed:
        if target.exists():
            if gzip_info(target)!=(source.stat().st_size,digest(source)):
                raise ValueError('Existing compressed evidence differs: '+str(target))
        else:
            with source.open('rb') as src,target.open('wb') as raw,gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0) as dst:
                shutil.copyfileobj(src,dst)
    elif not target.exists() or digest(target)!=digest(source):
        shutil.copy2(source,target)
    return target


def tree(source,destination):
    if not source.exists():return
    for path in sorted(source.rglob('*')):
        relative=path.relative_to(source)
        if any(part in EXCLUDED or part.startswith('obj-') for part in relative.parts):continue
        if path.suffix in ('.pyc','.o','.a','.so') or path.name in ('acceptance','sim','npu_compile'):continue
        copy_evidence(path,destination/relative)


def graph(project,workflow,target):
    with StaticTaskGraphStore(project/'.chip_nebula/shared/memory/taskgraph-v2.db') as store:
        tasks=store.list_tasks(workflow)
        attempts=[attempt for task in tasks for attempt in store.list_attempts(task.id)]
        work_ids={identity for attempt in attempts for identity in attempt.work_item_ids}
        work_ids.update(item.id for task in tasks for item in store.pending_work(task.id))
        work_items=store.work_items(sorted(work_ids))
        artifacts=store.list_artifacts()
        deliveries={task.id:store.deliveries(task.id) for task in tasks}
        if {item.id for item in work_items}!=work_ids:
            raise ValueError('Captured or pending workflow work record is missing')
        references={identity for attempt in attempts for identity in attempt.input_deliveries.values()}
        references.update(identity for item in work_items for identity in item.evidence_artifact_ids)
        references.update(delivery.artifact_id for outputs in deliveries.values() for delivery in outputs.values())
        if not references.issubset({artifact.id for artifact in artifacts}):
            raise ValueError('Workflow input or feedback evidence artifact is missing')
        record={'workflow':asdict(store.get_workflow(workflow)),
            'tasks':[dict(asdict(task),engineering_state=store.task_state(task.id).value) for task in tasks],
            'roles':[asdict(store.get_role(name,version)) for name,version in sorted({(task.role,task.role_version) for task in tasks})],
            'feedback':[asdict(route) for route in store.feedback_routes(workflow)],
            'attempts':[asdict(attempt) for attempt in attempts],
            'work_items':[asdict(item) for item in work_items],
            'deliveries':{task_id:{name:asdict(delivery) for name,delivery in outputs.items()}
                          for task_id,outputs in deliveries.items()},
            'artifacts':[artifact.document() for artifact in artifacts],
            'scope':'Frozen contracts, attempt decisions, engineering states, deliveries and captured/pending feedback evidence. WorkItem states are their exported final states. Private model-home and credentials excluded.'}
    write_json(target,record)


def project_config(project,destination):
    for folder in ('spec','context','tb','tools','reports','.chip_nebula/roles','.chip_nebula/recipes','.chip_nebula/schemas'):
        tree(project/folder,destination/folder)
    for name in ('trial-inputs.json','frozen-tool-workflow.json','study-candidate.json','workbench.yaml'):
        copy_evidence(project/name,destination/name)


def physical(source,destination):
    for path in source.glob('*.json'):copy_evidence(path,destination/path.name)
    for path in source.glob('*.log'):copy_evidence(path,destination/path.name)
    tree(source/'evidence',destination/'evidence')
    project_config(source/'project',destination/'configuration')
    if (source/'project/.chip_nebula/shared/memory/taskgraph-v2.db').exists():
        graph(source/'project','study-physical',destination/'taskgraph.json')
    for workloads in source.glob('workloads*'):
        if not workloads.is_dir():continue
        tree(workloads,destination/workloads.name)
        storage={}
        for vcd in workloads.glob('*/*.vcd'):
            stored=destination/workloads.name/vcd.relative_to(workloads)
            storage[str(vcd.relative_to(workloads))]={'encoding':'gzip','path':str(stored.relative_to(destination/workloads.name))+'.gz',
                'decoded_sha256':digest(vcd),'decoded_bytes':vcd.stat().st_size}
        if storage:write_json(destination/workloads.name/'experiment-manifest.json',{'vcd_storage':storage})


def ppa_provenance(source,destination):
    for pattern in ('source-bindings*.json','measurement-source-correction.json'):
        for path in (source/'ppa').glob(pattern):
            copy_evidence(path,destination/'ppa'/path.name)
    for archive in (source/'ppa').glob('executed-helpers-*'):
        if archive.is_dir():tree(archive,destination/'ppa'/archive.name)
    tree(source/'source-correction',destination/'source-correction')
    tree(source/'release-hardening',destination/'release-hardening')
    copy_evidence(source/'freeze_measurement_correction.py',destination/'source-correction/freeze_measurement_correction.py')


def export(source,destination,foundations=False):
    source=source.resolve();destination=destination.resolve();destination.mkdir(parents=True,exist_ok=True)
    for name in ('protocol.json','source-bindings.json','capabilities.json','measurement-corrections.json'):
        copy_evidence(source/name,destination/name)
    for name in ('analysis.json','summary.json'):
        copy_evidence(source/'generation'/name,destination/'generation'/name)
    for path in (source/'generation').glob('analysis-*.json'):
        copy_evidence(path,destination/'generation'/path.name)
    tree(source/'generation/executed-helpers-v1',destination/'generation/executed-helpers-v1')
    plan=json.loads((source/'protocol.json').read_text())
    for job in plan['generation']['jobs']:
        trial=source/'generation'/job['id'];out=destination/'generation'/job['id']
        tree(trial/'results',out/'results');project_config(trial/'project',out/'configuration')
        graph(trial/'project','configuration-study',out/'taskgraph.json')
    tree(source/'transfer/counter/results',destination/'transfer/counter/results')
    project_config(source/'transfer/counter/project',destination/'transfer/counter/configuration')
    graph(source/'transfer/counter/project','counter-transfer',destination/'transfer/counter/taskgraph.json')
    tree(source/'tutorial',destination/'tutorial')
    # Tutorial .git/SQLite workspaces are rebuildable; retain configs/results only.
    for project in (destination/'tutorial').glob('*/project'):
        transient=project/'.chip_nebula/taskgraph-v2'
        if transient.exists():shutil.rmtree(transient)
        transient=project/'.chip_nebula/shared'
        if transient.exists():shutil.rmtree(transient)
    for pattern in ('*.json','*.log'):
        for path in (source/'checks').glob(pattern):
            if not path.name.startswith(DRAFT_CHECK_PREFIXES):
                copy_evidence(path,destination/'checks'/path.name)
    ppa_provenance(source,destination)
    copy_evidence(source/'ppa/analysis.json',destination/'ppa/analysis.json')
    for path in (source/'infrastructure-failures').glob('*.json'):
        copy_evidence(path,destination/'infrastructure-failures'/path.name)
    for failure in (source/'infrastructure-failures').glob('*'):
        if not failure.is_dir():continue
        out=destination/'infrastructure-failures'/failure.name
        for path in failure.glob('*.json'):copy_evidence(path,out/path.name)
        tree(failure/'results',out/'results');project_config(failure/'project',out/'configuration')
        graph(failure/'project','ppa-search',out/'taskgraph.json')
    if not foundations:
        physical(source/'baseline/mhz95-run03',destination/'baseline/mhz95-run03')
    else:
        # Drafts retain completed decision traces; full physical evidence follows at final export.
        copy_evidence(source/'baseline/mhz95-run03/evaluation-v4.json',destination/'baseline/mhz95-run03/evaluation-v4.json')
    for job in plan['ppa']['sessions']:
        session=source/'ppa'/job['id'];out=destination/'ppa'/job['id']
        if foundations and not (session/'results/search-summary.json').exists():continue
        tree(session/'results',out/'results');copy_evidence(session/'session.json',out/'session.json')
        copy_evidence(session/'executed-source-binding.json',out/'executed-source-binding.json')
        graph(session/'project','ppa-search',out/'taskgraph.json')
        if not foundations:project_config(session/'project',out/'configuration')
        for slot in sorted((session/'candidates').glob('*')):
            for path in slot.glob('*.json'):copy_evidence(path,out/'candidates'/slot.name/path.name)
            if not foundations:physical(slot/'physical',out/'candidates'/slot.name/'physical')
    for group in ('representatives','high-frequency'):
        for path in (source/group).glob('*.json'):copy_evidence(path,destination/group/path.name)
        if not foundations:
            for item in (source/group).glob('*'):
                if item.is_dir():
                    tree(item/'source',destination/group/item.name/'source')
                    if (item/'physical').exists():physical(item/'physical',destination/group/item.name/'physical')
    files=[{'path':str(path.relative_to(destination)),'bytes':path.stat().st_size,'sha256':digest(path)}
           for path in sorted(destination.rglob('*')) if path.is_file() and path.name!='export-manifest.json']
    write_json(destination/'export-manifest.json',{'complete':not foundations,'files':files,
        'scope':'Used public evidence only. Private model sessions and authentication excluded; source experiment remains unchanged.'})
    print(json.dumps({'complete':not foundations,'exported_files':len(files),'destination':str(destination)}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--experiment',type=Path,required=True)
    parser.add_argument('--output',type=Path,default=CASE/'results/configurable-study');parser.add_argument('--foundations',action='store_true')
    args=parser.parse_args();export(args.experiment,args.output,args.foundations)
