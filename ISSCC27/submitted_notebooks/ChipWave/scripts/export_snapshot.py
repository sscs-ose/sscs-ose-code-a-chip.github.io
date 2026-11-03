#!/usr/bin/env python3
"""Export selected Git-backed project sources, excluding transient build products."""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import subprocess
import tarfile
from dataclasses import asdict
from pathlib import Path
from chip_nebula.taskgraph.static_store import StaticTaskGraphStore


def export(project, workflow, task_name, slot, destination):
    if destination.exists():
        raise ValueError('destination must be new; existing experiment is preserved')
    with StaticTaskGraphStore(project / '.chip_nebula/shared/memory/taskgraph-v2.db') as store:
        task_id = f'{workflow}:{task_name}'
        state = store.task_state(task_id)
        if state.value != 'satisfied':
            raise ValueError(f'task has not satisfied its frozen contract: {state.value}')
        delivery = store.deliveries(task_id).get(slot)
        if not delivery:
            raise ValueError('no selected Delivery for this output slot')
        artifact = store.get_artifact(delivery.artifact_id)
        if artifact.content.kind != 'git' or not artifact.content.commit:
            raise ValueError('selected Artifact must contain an immutable Git snapshot')
        record = asdict(artifact)
    roots = subprocess.run(['git', '-C', str(project), 'ls-tree', '--name-only', artifact.content.commit],
                           capture_output=True, text=True, check=True).stdout.splitlines()
    sources_only = [name for name in roots if name != 'build']
    assert 'rtl' in sources_only
    archive = subprocess.run(['git', '-C', str(project), 'archive', '--format=tar', artifact.content.commit, '--', *sources_only],
                             capture_output=True, check=True).stdout
    destination.mkdir(parents=True)
    with tarfile.open(fileobj=io.BytesIO(archive)) as bundle:
        for member in bundle.getmembers():
            path = destination / member.name
            if not path.resolve().is_relative_to(destination.resolve()) or member.issym() or member.islnk():
                raise ValueError(f'unsafe snapshot archive entry: {member.name}')
            if member.isdir():
                path.mkdir(parents=True, exist_ok=True)
            elif member.isfile():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(bundle.extractfile(member).read())
    sources = sorted((destination / 'rtl').rglob('*.sv')) + sorted((destination / 'rtl').rglob('*.v'))
    if not sources:
        raise ValueError('Delivery has no RTL compilation units')
    (destination / 'rtl/files.f').write_text(''.join(str(p.relative_to(destination / 'rtl')) + '\n' for p in sources))
    record['exported_source_sha256'] = {str(p.relative_to(destination)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    record['export_scope'] = 'Tracked project sources/configuration; transient build/ outputs excluded; all remaining archive path/link checks retained'
    (destination / 'selected-delivery.json').write_text(json.dumps(record, indent=2, default=str) + '\n')
    print(json.dumps({'artifact': artifact.id, 'commit': artifact.content.commit, 'destination': str(destination)}, indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--project', type=Path, required=True)
    p.add_argument('--workflow', default='cpu-npu-ai-led')
    p.add_argument('--task', required=True)
    p.add_argument('--slot', required=True)
    p.add_argument('--destination', type=Path, required=True)
    a = p.parse_args()
    export(a.project.resolve(), a.workflow, a.task, a.slot, a.destination.resolve())
