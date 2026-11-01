"""Preserve an actual saved-input S14 replay after validating its result.

This copies existing evidence only. It neither runs EDA nor changes adoption.
"""
from __future__ import annotations

import argparse
import copy
import gzip
import hashlib
import json
from pathlib import Path

from replay_completion_proof import ROOT, load, require, save, verify
from hullcirq.postroute_tools import validate_postlayout_result
from hullcirq.verification import object_hash


def collect(archive: Path, replay: Path, output: Path) -> dict:
    archive, replay, output = archive.resolve(), replay.resolve(), output.resolve()
    require(replay.is_dir() and replay.is_relative_to((ROOT / '.work').resolve()),
            'Read an existing replay below HuLLCirq/.work.')
    require(not output.exists() and output.is_relative_to((ROOT / 'results').resolve()),
            'Use a fresh results directory; previous evidence is immutable.')
    records = verify(archive)['records']
    source, summary, result = (load(replay / name) for name in
                               ('replay-source.json', 'summary.json', 'result.json'))
    require(summary['status'] == 'Passed' and summary['kind'] == 'actual_saved_input_postroute_replay',
            'An actual replay must have completed successfully.')
    require(source['archive_manifest_sha256'] == hashlib.sha256((archive / 'manifest.json').read_bytes()).hexdigest()
            and source['original_record_sha256'] == object_hash(records['postlayout'])
            and source['original_run_id'] == summary['original_run_id'] == records['postlayout']['id'],
            'Replay evidence must refer to this exact completion archive.')
    original_configuration = records['postlayout']['runtime_configuration']
    expected_configuration = copy.deepcopy(original_configuration)
    expected_configuration['working_directory'] = str(replay / 'runs')
    require(source['original_configuration_sha256'] == object_hash(original_configuration)
            and source['configuration'] == expected_configuration,
            'Replay may change only the original configuration working directory.')
    artifacts_directory = Path(result['artifacts_directory']).resolve()
    require(artifacts_directory.is_dir() and artifacts_directory.is_relative_to(replay / 'runs'),
            'The actual replay artifacts must be inside its retained runs directory.')
    validate_postlayout_result(result, records['lvs'], records['drc'], records['physical'], source['configuration'])
    require(result['summary'] == summary['summary'] and source['live_store_modified'] is False
            and source['adopted'] is False and source['model_calls'] == 0
            and summary['verification_plan_sha256'] == records['postlayout']['verification_plan_sha256']
            and summary['live_store_modified'] is False and summary['adopted'] is False
            and summary['new_RTL_or_model_generation'] is False,
            'Replay summary or execution scope differs.')
    output.mkdir(parents=True)
    files = {}
    for path in sorted(replay.rglob('*')):
        if not path.is_file():
            continue
        require(path.resolve().is_relative_to(replay) and path.stat().st_size < 512 * 1024 * 1024,
                'Unexpected replay file path or size.')
        relative = path.relative_to(replay).as_posix()
        raw = path.read_bytes()
        compressed = len(raw) > 262144 and path.suffix not in ('.gz', '.png')
        destination = relative + ('.gz' if compressed else '')
        payload = gzip.compress(raw, mtime=0) if compressed else raw
        target = output / destination
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as stream:
            stream.write(payload)
        require(target.read_bytes() == payload, 'Saved replay bytes differ.')
        files[destination] = {'original_path': relative, 'bytes': len(payload),
                              'sha256': hashlib.sha256(payload).hexdigest(),
                              'raw_bytes': len(raw), 'raw_sha256': hashlib.sha256(raw).hexdigest(),
                              'compression': 'gzip' if compressed else None}
    copied = {entry['original_path']: entry for entry in files.values()}
    for artifact in result['artifacts']:
        original = (artifacts_directory / artifact['relative_path']).resolve()
        require(original.is_relative_to(artifacts_directory), 'A replay artifact escaped its execution directory.')
        entry = copied.get(original.relative_to(replay).as_posix())
        require(entry is not None and entry['raw_sha256'] == artifact['sha256']
                and entry['raw_bytes'] == artifact['bytes'],
                'A captured replay artifact differs from the validated execution.')
    for filename, value in (('replay-source.json', source), ('summary.json', summary), ('result.json', result)):
        require(load(replay / filename) == value, 'Replay metadata changed during collection.')
    manifest = {'schema': 'hullcirq-completion-replay-evidence-v1', 'status': 'Passed',
                'kind': summary['kind'], 'original_run_id': summary['original_run_id'],
                'archive_manifest_sha256': source['archive_manifest_sha256'],
                'summary': summary['summary'], 'files': files,
                'scope': 'Actual S14 compile, routed functional simulation and nine-corner extracted STA on the same prepared host. No new LLM generation, adoption or S01-S13 execution.',
                'dynamic_SDF_simulation_passed': False}
    save(output / 'manifest.json', manifest)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, default=ROOT / 'results/npu_completion_v1')
    parser.add_argument('--replay', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    manifest = collect(args.archive, args.replay, args.output)
    print(json.dumps({'status': manifest['status'], 'files': len(manifest['files']), 'output': str(args.output)}))


if __name__ == '__main__':
    main()
