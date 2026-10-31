"""Verify the exported study and restore raw evidence into a new local workspace."""
import argparse
import json
import shutil
from pathlib import Path

from capacity_physical_evidence import checked_path
from capacity_physical_export import restore as restore_physical,restore_file
from study_protocol import digest,write_json


def restore(source,destination):
    source,destination=Path(source).resolve(),Path(destination).resolve()
    if destination.exists():raise ValueError('Restore into a fresh workspace')
    manifest=json.loads((source/'export-manifest.json').read_text())
    files={row['path']:row for row in manifest['files']}
    if len(files)!=len(manifest['files']):raise ValueError('Duplicate export file')
    actual={str(p.relative_to(source)) for p in source.rglob('*') if p.is_file()}
    if actual!=set(files)|{'export-manifest.json'}:raise ValueError('Export file inventory differs')
    for name,row in files.items():
        path=checked_path(source,name)
        if path.stat().st_size!=row['bytes'] or digest(path)!=row['sha256']:
            raise ValueError('Changed export file: '+name)
        target=checked_path(destination,name)
        if '.git' in target.relative_to(destination).parts:raise ValueError('Unmanaged Git metadata in export')
    physical=[Path(r['path']) for r in manifest['physical']]
    if len(physical)!=len(set(physical)) or any(a.is_relative_to(b) for a in physical for b in physical if a!=b):
        raise ValueError('Overlapping physical exports')
    for path in physical:checked_path(destination,str(path))
    ordinary=manifest['ordinary_sources'];names=[r['path'] for r in ordinary]
    if len(names)!=len(set(names)):raise ValueError('Duplicate decoded path')
    for row in ordinary:
        target=checked_path(destination,row['path']);checked_path(source,row['stored'])
        if '.git' in target.relative_to(destination).parts or row['stored'] not in files:
            raise ValueError('Unmanaged decoded file')
        if any(Path(row['path']).is_relative_to(p) for p in physical):raise ValueError('Conflicting ordinary/physical source')
        if row['encoding'] not in ('raw','gzip') or type(row['bytes']) is not int or row['bytes']<0:
            raise ValueError('Invalid decoded storage')
        if files[row['stored']]['sha256']!=row['stored_sha256']:raise ValueError('Storage hash mismatch')
    destination.mkdir(parents=True)
    stores={r['stored'] for r in ordinary}
    for name in files:
        if name in stores or any(Path(name).is_relative_to(p) for p in physical):continue
        target=destination/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source/name,target)
    for row in ordinary:restore_file(source,destination,row)
    for path in physical:restore_physical(source/path,destination/path)
    shutil.copy2(source/'export-manifest.json',destination/'source-export-manifest.json')
    record=dict(restored=True,source_complete=manifest['complete'],source_manifest_sha256=digest(source/'export-manifest.json'),
        ordinary_files=len(ordinary),physical_attempts=len(physical),model_calls=0,physical_runs=0,
        scope='Byte/provenance restoration only. Reexecute accounting, function and physical audits separately.')
    write_json(destination/'restoration.json',record)
    return record


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',required=True,type=Path);parser.add_argument('--workspace',required=True,type=Path)
    args=parser.parse_args();print(json.dumps(restore(args.source,args.workspace)))
