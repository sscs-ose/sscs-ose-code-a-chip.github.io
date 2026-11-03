"""Export the benchmark/workflow campaign without model homes or rebuildable objects."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from export_study_results import copy_evidence,graph,physical,project_config,tree
from study_protocol import digest,write_json
from summarize_benchmark_study import summarize

CASE=Path(__file__).resolve().parents[1]


def benchmark_physical(source,destination):
    for suffix in ('*.json','*.log'):
        for path in source.glob(suffix):copy_evidence(path,destination/path.name)
    tree(source/'evidence',destination/'evidence')
    tree(source/'postroute',destination/'postroute')
    project_config(source/'project',destination/'configuration')
    for folder in ('rtl','physical'):
        tree(source/'project'/folder,destination/'configuration'/folder)
    db=source/'project/.chip_nebula/shared/memory/taskgraph-v2.db'
    if db.exists():graph(source/'project','benchmark-physical',destination/'taskgraph.json')


def export(source,destination,*,draft=False):
    source,destination=Path(source).resolve(),Path(destination).resolve()
    if destination==source or source.is_relative_to(destination):
        raise ValueError('Evidence export must not contain its source campaign')
    analysis=summarize(source)
    complete=(analysis['ppa_complete'] and analysis['benchmark']['qualified'] and
              all(r['terminal'] for r in analysis['demonstrations']) and analysis['high_frequency']['finished'] and
              analysis['physical_accounting']['terminal']==analysis['physical_accounting']['allocated'])
    if not complete and not draft:
        raise ValueError('Only --draft may export incomplete campaign evidence')
    destination.mkdir(parents=True,exist_ok=True)
    for name in ('PLAN.md','protocol.json','launch-ledger.json','analysis.json','experiments-terminal.json',
                 'budget-amendment.json'):
        copy_evidence(source/name,destination/name)
    # Reference answers and final checkers are public for replay, never agent-visible during scoring.
    tree(source/'benchmark/tasks',destination/'benchmark/tasks')
    tree(source/'benchmark/executed-construction',destination/'benchmark/executed-construction')
    copy_evidence(source/'benchmark/qualification.json',destination/'benchmark/qualification.json')
    for launch in analysis['physical_accounting']['launches']:
        if launch['category'] in ('reference','preformal_calibration','reference_supplement'):
            benchmark_physical(source/launch['output'],destination/launch['output'])
    for label in json.loads((source/'protocol.json').read_text())['demonstrations']:
        root=source/'benchmark/demonstrations'/label;out=destination/'benchmark/demonstrations'/label
        tree(root/'results',out/'results')
        project_config(root/'project',out/'configuration')
        db=root/'project/.chip_nebula/shared/memory/taskgraph-v2.db'
        if db.exists():graph(root/'project','benchmark-generation',out/'taskgraph.json')
        if (root/'physical/qualification.json').exists():benchmark_physical(root/'physical',out/'physical')
    if (source/'baseline/common/campaign-evaluation.json').exists():
        physical(source/'baseline/common',destination/'baseline/common')
    tree(source/'ppa/executed-sources',destination/'ppa/executed-sources')
    copy_evidence(source/'ppa/formal-freeze.json',destination/'ppa/formal-freeze.json')
    for job in json.loads((source/'protocol.json').read_text())['ppa_jobs']:
        root=source/'ppa'/job['id'];out=destination/'ppa'/job['id']
        # Never export an active SQLite graph or half-written model stream.
        if not next(r for r in analysis['rows'] if r['job']['id']==job['id'])['terminal']:continue
        tree(root/'results',out/'results')
        copy_evidence(root/'session.json',out/'session.json')
        project_config(root/'project',out/'configuration')
        graph(root/'project','workflow-ppa',out/'taskgraph.json')
        for slot in sorted((root/'candidates').glob('*')):
            for suffix in ('*.json','*.log'):
                for path in slot.glob(suffix):copy_evidence(path,out/'candidates'/slot.name/path.name)
            tree(slot/'source',out/'candidates'/slot.name/'source')
            if (slot/'physical').exists():physical(slot/'physical',out/'candidates'/slot.name/'physical')
    for path in (source/'high-frequency').glob('*.json'):
        copy_evidence(path,destination/'high-frequency'/path.name)
    for root in (source/'high-frequency').glob('high-frequency-*'):
        if (root/'campaign-evaluation.json').exists():physical(root,destination/'high-frequency'/root.name)
    # Deliberate whitelist: no model homes, authentication, sockets or coordinator env files.
    for name in ('rtl-actions','checker-revision-v2','model-readiness','model-readiness-02'):
        tree(source/'checks'/name,destination/'checks'/name)
    for path in (source/'checks').glob('*'):
        if path.is_file() and path.suffix in ('.json','.log','.py') and not any(
                word in path.name for word in ('draft','guard-process','coordinator','proxy')):
            copy_evidence(path,destination/'checks'/path.name)
    files=[dict(path=str(p.relative_to(destination)),bytes=p.stat().st_size,sha256=digest(p))
           for p in sorted(destination.rglob('*')) if p.is_file() and p.name not in ('export-manifest.json','export-status.json')]
    write_json(destination/'export-status.json',dict(complete=complete,draft=not complete,model_calls=0,physical_calls=0))
    files.append(dict(path='export-status.json',bytes=(destination/'export-status.json').stat().st_size,
                      sha256=digest(destination/'export-status.json')))
    write_json(destination/'export-manifest.json',dict(complete=complete,files=files,
        scope='Public used-component evidence; raw historical paths retained as provenance, resolved by replay from this export. Private model homes, authentication and rebuildable objects excluded.'))
    print(json.dumps(dict(complete=complete,files=len(files),output=str(destination)),indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--campaign',type=Path,required=True)
    parser.add_argument('--output',type=Path,default=CASE/'results/benchmark-study')
    parser.add_argument('--draft',action='store_true')
    args=parser.parse_args();export(args.campaign,args.output,draft=args.draft)
