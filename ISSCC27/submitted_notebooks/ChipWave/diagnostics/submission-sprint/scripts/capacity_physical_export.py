"""Retain terminal physical evidence and Git provenance without worktrees or caches."""
import gzip
import json
import shutil
import subprocess
import sys
from pathlib import Path

from capacity_integration_physical import CASE
from capacity_physical_evidence import checked_path
from study_protocol import digest,write_json

sys.path.append(str(CASE/'scripts'))
from export_study_results import copy_evidence

SUFFIXES={'.json','.log','.rpt','.txt','.csv','.xml','.lyrdb','.gds','.odb','.v','.sv',
          '.spef','.sdf','.lib','.vcd','.lvsdb','.cdl','.spice','.lef','.hex','.tcl','.py','.gz',
          '.sdc','.tsv','.jsonl','.S'}


def export(run,destination):
    run,destination=Path(run).resolve(),Path(destination).resolve()
    if destination.exists():raise ValueError('Preserve existing physical export')
    if run==destination or run.is_relative_to(destination) or destination.is_relative_to(run):
        raise ValueError('Physical export must be separate from its source')
    terminal=run/('qualification.json' if (run/'qualification.json').exists() else 'result.json')
    record=json.loads(terminal.read_text())
    if record.get('status') in (None,'allocated','running'):raise ValueError('Physical attempt has no terminal status')
    files=set(run.glob('*.json'))|set(run.glob('*.log'))
    for name in ('evidence','postroute','workloads'):
        files.update(p for p in (run/name).rglob('*') if p.is_file() and p.suffix in SUFFIXES
            and not any(part in ('obj','obj_dir','__pycache__') or part.startswith('obj-')
                        for part in p.relative_to(run).parts))
    for name,key in (('selected-delivery.json','collected_files'),('failed-attempt.json','files')):
        receipt=run/'evidence'/name
        if receipt.exists():
            files.update(checked_path(run/'evidence',item['path'])
                         for item in json.loads(receipt.read_text()).get(key,[]))
    manifest_path=run/'manifest.json'
    if manifest_path.exists():
        manifest=json.loads(manifest_path.read_text())
        for name in manifest.get('rtl_sha256',{}):files.add(checked_path(run/'project',name))
        for name in ('physical/chip-nebula/config.mk','physical/chip-nebula/constraints.sdc'):
            path=run/'project'/name
            if path.exists():files.add(path)
    destination.mkdir(parents=True)
    records=[]
    for path in sorted(files):
        relative=str(path.relative_to(run));checked_path(run,relative)
        stored=copy_evidence(path,destination/relative)
        if stored is None:raise ValueError('Missing selected evidence: '+relative)
        records.append(dict(path=relative,stored=str(stored.relative_to(destination)),
            encoding='gzip' if stored!=destination/relative else 'raw',
            bytes=path.stat().st_size,sha256=digest(path),stored_sha256=digest(stored)))
    bundle=None
    if (run/'project/.git').exists() and subprocess.check_output(
            ['git','for-each-ref','--format=%(refname)'],cwd=run/'project',timeout=30).strip():
        target=destination/'physical-project.bundle'
        subprocess.run(['git','bundle','create',str(target),'--all'],cwd=run/'project',check=True,
                       capture_output=True,timeout=300)
        bundle=dict(path=target.name,bytes=target.stat().st_size,sha256=digest(target))
    result=dict(schema_version=1,terminal=record['status'],files=records,bundle=bundle,
        decoded_file_bytes=sum(r['bytes'] for r in records),
        scope='Terminal physical data, required source/configuration and reachable Git provenance. No mutable worktrees, compiler caches or model homes.')
    write_json(destination/'physical-export.json',result)
    return result


def restore_file(source,destination,row):
    stored=checked_path(source,row['stored']);target=checked_path(destination,row['path'])
    target.parent.mkdir(parents=True,exist_ok=True)
    opener=gzip.open if row['encoding']=='gzip' else open
    with opener(stored,'rb') as src,target.open('xb') as dst:
        remaining=row['bytes']
        while remaining:
            block=src.read(min(1<<20,remaining))
            if not block:raise ValueError('Truncated stored evidence')
            dst.write(block);remaining-=len(block)
        if src.read(1):raise ValueError('Evidence exceeds its declared decoded size')
    if digest(target)!=row['sha256']:raise ValueError('Decoded evidence differs')
    if row['encoding']=='raw':
        target.chmod((target.stat().st_mode & 0o777) | (stored.stat().st_mode & 0o111))


def restore(source,destination):
    source,destination=Path(source).resolve(),Path(destination).resolve()
    if destination.exists():raise ValueError('Restore requires a fresh directory')
    receipt=json.loads((source/'physical-export.json').read_text())
    names=[r['path'] for r in receipt['files']]
    if len(names)!=len(set(names)):raise ValueError('Duplicate export paths')
    for row in receipt['files']:
        if checked_path(destination,row['path']).is_relative_to(destination/'project/.git'):
            raise ValueError('Export may not overwrite Git metadata')
        stored=checked_path(source,row['stored'])
        if digest(stored)!=row['stored_sha256']:raise ValueError('Stored evidence changed')
        if row['encoding'] not in ('raw','gzip') or type(row['bytes']) is not int or row['bytes']<0:
            raise ValueError('Malformed storage manifest')
    bundle=receipt.get('bundle')
    if bundle and digest(checked_path(source,bundle['path']))!=bundle['sha256']:
        raise ValueError('Git provenance bundle changed')
    destination.mkdir(parents=True)
    if bundle:
        subprocess.run(['git','clone','--no-checkout','--',str(source/bundle['path']),str(destination/'project')],
                       check=True,capture_output=True,timeout=300)
        # Removing the clone remote also deletes its branch refs; keep every bundled object reachable.
        heads=subprocess.check_output(['git','bundle','list-heads',str(source/bundle['path'])],
                                      text=True,timeout=30).splitlines()
        for index,line in enumerate(heads):
            subprocess.run(['git','update-ref',f'refs/capacity-provenance/{index}',line.split()[0]],
                           cwd=destination/'project',check=True,capture_output=True,timeout=30)
        subprocess.run(['git','remote','remove','origin'],cwd=destination/'project',check=True,capture_output=True)
    for row in receipt['files']:
        restore_file(source,destination,row)
    return dict(restored=True,files=len(receipt['files']),decoded_file_bytes=receipt['decoded_file_bytes'])
