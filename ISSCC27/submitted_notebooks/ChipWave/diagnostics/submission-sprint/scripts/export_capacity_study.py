"""Export the used study closure and terminal evidence; private model homes stay local."""
import argparse
import json
import sys
from pathlib import Path

from capacity_integration_physical import ROOT,CASE
from capacity_physical_evidence import checked_path
from capacity_physical_export import export as export_physical
from capacity_results import analyze,read_trials
from study_protocol import digest,write_json

sys.path.append(str(CASE/'scripts'))
from export_study_results import copy_evidence,graph

SUFFIXES={'.py','.md','.json','.jsonl','.log','.txt','.rpt','.csv','.tsv','.yaml','.yml',
    '.sv','.v','.vh','.svh','.hex','.S','.tcl','.ys','.sdc','.mk','.specir','.svg','.png','.html'}
EXCLUDED={'.git','__pycache__','obj','obj_dir','build','adapter-bin','private','model-home','sessions'}


def export(source,destination,*,draft=False):
    source,destination=Path(source).resolve(),Path(destination).resolve()
    if destination.exists():raise ValueError('Export into a fresh directory; retain previous candidates')
    if source==destination or source.is_relative_to(destination):raise ValueError('Export cannot contain its source')
    analyses={category:analyze(source,category) for category in ('pilot','formal')}
    ledger=json.loads((source/'physical-ledger.json').read_text())
    calibration=source/'checks/reference-calibration.json'
    calibrated=calibration.exists() and json.loads(calibration.read_text()).get('passed') is True
    frozen=source/'campaign-freeze.json';decision=source/'pilot-decision.json'
    admitted=False
    if frozen.exists() and decision.exists():
        freeze=json.loads(frozen.read_text());gate=json.loads(decision.read_text())
        admitted=(freeze.get('qualified') is True and gate.get('formal_launch_allowed') is True
                  and gate.get('stop_rule_triggered') is False and gate.get('campaign_sha256')==digest(frozen))
    for category in analyses:
        for row in read_trials(source,category):
            if not row.get('terminal'):continue
            expected={r['identity'] for r in ledger['attempts'] if r['category']==category and r['trial']==row['job']['id']}
            if 'physical_attempts' in row and {r['identity'] for r in row['physical_attempts']}!=expected:
                raise ValueError('Trial/global physical ledger differs: '+row['job']['id'])
    complete=all(a['complete'] for a in analyses.values()) and calibrated and admitted and all(
        a['status']!='allocated' for a in ledger['attempts'])
    if not complete and not draft:raise ValueError('Final export requires complete trials, reference calibration and physical terminals')
    destination.mkdir(parents=True)
    records={};physical=[];omitted=[]
    def copy(path):
        relative=str(path.relative_to(source));checked_path(source,relative)
        if relative in records:return
        stored=copy_evidence(path,destination/relative)
        if stored is None:raise ValueError('Missing selected source: '+relative)
        records[relative]=dict(path=relative,stored=str(stored.relative_to(destination)),
            encoding='gzip' if stored!=destination/relative else 'raw',
            bytes=path.stat().st_size,sha256=digest(path),stored_sha256=digest(stored))
    def tree(folder,*,skip_physical=False):
        for path in sorted(folder.rglob('*')):
            relative=path.relative_to(folder)
            if any(p in EXCLUDED or p.startswith('obj-') for p in relative.parts):continue
            if skip_physical and any('-physical-' in p for p in relative.parts):continue
            if path.is_file() and (path.suffix in SUFFIXES or path.name in ('LICENSE','Makefile')):copy(path)
    for name in ('README.md','protocol.json','physical-ledger.json','campaign-freeze.json','formal-freeze.json','pilot-decision.json'):
        path=source/name
        if path.exists():copy(path)
    if json.loads((destination/'physical-ledger.json').read_text())!=ledger:
        raise ValueError('Physical ledger changed during capture; preserve this unfinished export')
    for name in ('scripts','tasks','integration','task-packages','workflow-templates','provenance'):
        tree(source/name)
    for path in (source/'checks').glob('*.json'):copy(path)
    # The freeze explicitly names its qualification receipts, including native probe results.
    if frozen.exists():
        for name,sha in json.loads(frozen.read_text())['files'].items():
            path=checked_path(source,name)
            if digest(path)!=sha:raise ValueError('Frozen campaign source changed before export: '+name)
            copy(path)
    for category,analysis in analyses.items():
        write_json(destination/'analysis'/(category+'-results.json'),analysis)
        rules=json.loads((source/'protocol.json').read_text())
        for job in rules[category+'_jobs']:
            trial=source/'trials'/category/job['id']
            terminal=trial/'result.json'
            if not terminal.exists():
                omitted.append(dict(trial=job['id'],reason='no_terminal_result'));continue
            for path in trial.glob('*.json'):copy(path)
            tree(trial/'runtime',skip_physical=True)
            tree(trial/'grading')
            for name in ('spec','tests','reports','.chip_nebula/roles','.chip_nebula/recipes'):
                tree(trial/'project'/name)
            for name in ('frozen-capacity-workflow.json','workflow-definition.json','expert-checklist.json','native-entry.json'):
                path=trial/'project'/name
                if path.exists():copy(path)
            database=trial/'project/.chip_nebula/shared/memory/taskgraph-v2.db'
            if database.exists():graph(trial/'project','capacity',destination/trial.relative_to(source)/'taskgraph.json')
    for attempt in ledger['attempts']:
        if attempt['status']=='allocated':
            omitted.append(dict(physical=attempt['identity'],reason='allocated_not_terminal'));continue
        path=Path(attempt['evidence'])
        path=path if path.is_absolute() else source/path
        relative=str(path.parent.relative_to(source));checked_path(source,relative)
        export_physical(path.parent,destination/relative)
        physical.append(dict(identity=attempt['identity'],path=relative,status=attempt['status']))
    tree(source/'publication/figures')
    write_json(destination/'export-status.json',dict(complete=complete,draft=not complete,
        omitted=omitted,model_calls=0,physical_runs=0,
        scope='Used experiment sources and terminal evidence. Install the accompanying public SDK/tool closure; this directory alone is not the full submission.'))
    files=[dict(path=str(p.relative_to(destination)),bytes=p.stat().st_size,sha256=digest(p))
        for p in sorted(destination.rglob('*')) if p.is_file()]
    manifest=dict(schema_version=1,complete=complete,files=files,ordinary_sources=list(records.values()),
        physical=physical,stored_bytes=sum(r['bytes'] for r in files),
        scope='Restore compressed evidence before running raw-file graders. Model authentication and private native contexts are excluded; filtered accounting and public role transcripts remain.')
    write_json(destination/'export-manifest.json',manifest)
    return dict(complete=complete,files=len(files),stored_bytes=manifest['stored_bytes'],physical=len(physical))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=ROOT)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--draft',action='store_true')
    args=parser.parse_args();print(json.dumps(export(args.source,args.output,draft=args.draft)))
