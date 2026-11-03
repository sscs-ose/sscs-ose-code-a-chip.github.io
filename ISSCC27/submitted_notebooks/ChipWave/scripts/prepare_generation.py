#!/usr/bin/env python3
"""Prepare original generation inputs in a new project, without model calls."""
import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from chip_nebula.taskgraph.domain import Artifact, ArtifactContent, ArtifactProducer
from chip_nebula.taskgraph.artifacts import load_schema_registry
from chip_nebula.taskgraph.static_store import StaticTaskGraphStore

ROOT = Path(__file__).resolve().parents[1]


def prepare(output):
    if output.exists():
        raise ValueError('Choose a new project directory; previous work is preserved.')
    record = json.loads((ROOT/'results/generation.json').read_text())
    seed = ROOT/'generation_seed'
    for item in record['seed_files']:
        assert hashlib.sha256((seed/item['path']).read_bytes()).hexdigest() == item['sha256']
    assert not list(seed.glob('rtl/**/*.sv')), 'Generation input must not contain delivered RTL.'
    shutil.copytree(seed, output)
    for command in (['git','init','-q'], ['git','config','user.name','Case regeneration'],
                    ['git','config','user.email','automation@chipwave.invalid'],
                    ['git','add','.'], ['git','add','-f','.chip_nebula/roles','.chip_nebula/recipes'],
                    ['git','commit','-qm','Freeze original CPU/NPU generation inputs']):
        subprocess.run(command, cwd=output, check=True)
    def git(expression):
        return subprocess.run(['git','rev-parse',expression], cwd=output, capture_output=True,
                              text=True, check=True).stdout.strip()
    original = record['input']
    artifact = Artifact(id=original['id'], type=original['type'], schema_version=1,
        producer=ArtifactProducer('external','case-source','case-source','case-regeneration-input',1),
        content=ArtifactContent('git',git('HEAD'),git('HEAD^{tree}'),tuple(original['content']['paths'])),
        payload=original['payload'], metadata={'original_source_digest':record['input_digest']})
    artifact.validate(load_schema_registry())
    with StaticTaskGraphStore(output/'.chip_nebula/shared/memory/taskgraph-v2.db') as store:
        store.register_evidence_artifacts([artifact])
    subprocess.run(['git','update-ref','refs/chip-nebula/artifacts/'+artifact.id,git('HEAD')],
                   cwd=output, check=True)
    print('GENERATION_INPUT_READY; no model calls made')
    print('Run the project-local cpu-npu-generate.yaml recipe with --param source='+artifact.id)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    prepare(parser.parse_args().output.resolve())
