#!/usr/bin/env python3
"""Plan, then optionally remove verified export copies and obsolete run temps.

Keeps original build/results/physical, all export ZIPs/manifests, and all
OpenLane results/reports/logs. Never deletes the server_results directory.
No EDA tools or model changes. Default is read-only.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
import shutil

ROOT=Path(__file__).resolve().parents[1]
RUNS=Path('openlane/automx_cim_core_bound_demo/runs')
# Only historical failed bring-up runs. Passed/reference and current runs
# are deliberately absent, including readout_progress_20261018_04_fanout.
OLD_FAILED=(
    'core_bound_20261007_01','core_bound_20261007_lvs01',
    'core_bound_20261007_lvs02','core_bound_20261007_lvs03',
    'core_bound_20261007_lvs04','core_bound_20261007_lvs05',
    'core_bound_20261007_lvs06','core_bound_20261007_lvs07',
    'core_bound_20261008_pdn01','physical_next_20261018_01_fanout',
    'dc_antenna_20261018_01_fanout')
COPY_ROOTS={'build','results','physical','openlane','rtl','scripts','tests',
            'third_party','generated','configs'}


def digest(path):
    h=sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(4*1024*1024),b''):h.update(block)
    return h.hexdigest()


def inside(path,root):
    path,root=Path(path),Path(root).resolve()
    # Reject symlinks at any level, including ones pointing back inside root.
    if path.is_symlink() or not path.resolve().is_relative_to(root):
        raise ValueError('unsafe cleanup path: '+str(path))
    for parent in path.parents:
        if parent==root:break
        if parent.is_symlink():raise ValueError('symlink in cleanup path: '+str(path))
    return path.resolve()


def tree_size(path):
    total=0
    for p in path.rglob('*'):
        if p.is_symlink() or not p.resolve().is_relative_to(path.resolve()):
            raise ValueError('symlink/junction in old run temp: '+str(p))
        if p.is_file():total+=p.stat().st_size
    return total


def plan(root):
    root=Path(root).resolve()
    if not (root/'scripts/run_flow2_wrapper_closure.py').is_file():
        raise ValueError('expected AutoMX-CIM checkout with wrapper closure runner')
    directories=[];copies=[];skipped=0;seen=set()
    for tag in OLD_FAILED:
        for sub in ('tmp','issue_reproducible'):
            path=root/RUNS/tag/sub
            if path.exists():
                path=inside(path,root/RUNS)
                if not path.is_dir():raise ValueError('expected old run directory')
                directories.append({'path':path.relative_to(root).as_posix(),'bytes':tree_size(path)})
    exports=root/'server_results/flow2_wrapper_integration'
    for index in sorted(exports.glob('*/export.json')):
        inside(index,root/'server_results')
        try:manifest=json.loads(index.read_text(encoding='utf-8'))
        except (OSError,ValueError):skipped+=1;continue
        if manifest.get('format')!='automx-cim-wrapper-integration-export-v1':continue
        for item in manifest.get('files',[]):
            rel=PurePosixPath(item.get('path',''))
            expected=item.get('sha256','')
            if (rel.is_absolute() or '..' in rel.parts or not rel.parts or
                rel.parts[0] not in COPY_ROOTS or len(expected)!=64):
                skipped+=1;continue
            source=root/rel.as_posix();copy=index.parent/rel.as_posix()
            if not copy.exists() or copy in seen:continue
            seen.add(copy)
            source=inside(source,root);copy=inside(copy,index.parent)
            if (source==copy or not source.is_file() or not copy.is_file() or
                source.stat().st_size!=copy.stat().st_size):skipped+=1;continue
            if digest(source)!=expected or digest(copy)!=expected:skipped+=1;continue
            copies.append({'path':copy.relative_to(root).as_posix(),
                           'source':source.relative_to(root).as_posix(),
                           'sha256':expected,'bytes':copy.stat().st_size})
    return {'root':str(root),'old_temp_directories':directories,'verified_export_copies':copies,
            'skipped_unverified_items':skipped,
            'estimated_reclaim_bytes':sum(i['bytes'] for i in directories+copies)}


def apply(root,proposal):
    root=Path(root).resolve()
    if proposal['root']!=str(root):raise ValueError('cleanup plan root differs')
    removed=0
    # Source originals stay intact. Recheck immediately before each unlink.
    for item in proposal['verified_export_copies']:
        source=inside(root/item['source'],root)
        copy=inside(root/item['path'],root/'server_results/flow2_wrapper_integration')
        if (source==copy or not source.is_file() or digest(source)!=item['sha256'] or
            not copy.is_file() or digest(copy)!=item['sha256']):
            raise ValueError('export/native bytes changed; cleanup stopped')
        copy.unlink();removed+=item['bytes']
    allowed={f'{RUNS.as_posix()}/{tag}/{sub}' for tag in OLD_FAILED for sub in ('tmp','issue_reproducible')}
    for item in proposal['old_temp_directories']:
        if item['path'] not in allowed:raise ValueError('non-allowlisted run directory')
        path=inside(root/item['path'],root/RUNS)
        tree_size(path)  # Recheck links before recursive deletion.
        shutil.rmtree(path);removed+=item['bytes']
    return removed


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=ROOT)
    p.add_argument('--apply',action='store_true',help='delete only the verified copies and allowlisted old temps')
    a=p.parse_args();proposal=plan(a.root)
    print('Old run tmp/issue_reproducible directories:')
    for d in proposal['old_temp_directories']:print(f"  {d['bytes']/1024**2:.1f} MiB  {d['path']}")
    print('Verified redundant export files:',len(proposal['verified_export_copies']))
    print('Skipped unverified items:',proposal['skipped_unverified_items'])
    print(f"Estimated reclaim: {proposal['estimated_reclaim_bytes']/1024**3:.2f} GiB")
    if a.apply:
        count=apply(a.root,proposal)
        print(f"Removed {count/1024**3:.2f} GiB of copies/old temps; originals and export ZIPs retained")
    else:print('PLAN ONLY; no files removed. Add --apply to perform this plan.')
