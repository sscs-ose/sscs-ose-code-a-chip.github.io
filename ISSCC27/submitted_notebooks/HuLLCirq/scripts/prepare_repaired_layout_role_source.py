#!/usr/bin/env python3
"""Freeze a second read-only Functional Map source archive after S11 adoption.

The repaired layout must retain the exact original RTL/source manifest. The
original synthesis metadata is reused byte-for-byte and separately attributed;
all geometry comes from the newly selected S11 record. No EDA is invoked.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from hullcirq import layout_roles as roles
from hullcirq.physical_workflow import _artifact_path
from hullcirq.verification import object_hash


def record(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def json_bytes(value):
    return (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode('utf-8')


def prepare(layout, output, profile_output):
    output, profile_output = Path(output).resolve(), Path(profile_output).resolve()
    if (not output.is_relative_to(ROOT / 'results') or not profile_output.is_relative_to(ROOT)
            or output.exists() or profile_output.exists()):
        raise ValueError('Use new output paths inside HuLLCirq; existing evidence is never overwritten')
    if not (layout['execution_status'] == 'Completed' and layout['validation_status'] == 'Passed'
            and layout['review_status'] == 'Accepted' and layout['record_hash'] == object_hash({k: v for k, v in layout.items() if k != 'record_hash'})):
        raise ValueError('Require the raw complete adopted S11 record')
    old = ROOT / roles._BASE
    manifest_raw = (old / 'manifest.json').read_bytes()
    if hashlib.sha256(manifest_raw).hexdigest() != roles._ARCHIVE_MANIFEST_SHA256:
        raise ValueError('Original source archive changed')
    old_manifest = json.loads(manifest_raw)

    def old_bytes(relative):
        path = (old / relative).resolve()
        if not path.is_relative_to(old.resolve()):
            raise ValueError('Original source escapes archive')
        raw = path.read_bytes()
        if record(raw) != old_manifest['files'][relative]:
            raise ValueError('Original source file changed: ' + relative)
        return raw

    previous = json.loads(old_bytes('layout_record.json'))
    if layout['id'] == previous['id'] or any(layout[key] != previous[key] for key in (
            'revision_id', 'global_job_id', 'source_manifest_sha256', 'global_rtl_sha256',
            'verification_plan_sha256', 'vector_hash', 'testbench_sha256')):
        raise ValueError('A repaired view must retain the exact original GUI job and RTL lineage')
    entries = {item['id']: item for item in layout['checks']['artifacts']}
    pending = {'layout_record.json': json_bytes(layout)}
    lineage = {'previous_layout_id': previous['id'], 'layout_run_id': layout['id'],
               'original_source_manifest_sha256': layout['source_manifest_sha256'],
               'reused_synthesis_archive': {'path': roles._BASE + '/manifest.json', 'sha256': roles._ARCHIVE_MANIFEST_SHA256},
               'reused_files': [], 'new_geometry_files': [], 'additional_EDA_runs': 0}
    for name in ['candidate_top.v'] + [f'node-{n}.v' for n in ('control', 'buffer', 'scheduler', 'post', 'fifo', 'pe')]:
        identifier = 'rtl-top' if name == 'candidate_top.v' else 'rtl-' + name[:-2]
        raw = _artifact_path(layout['checks'], entries[identifier]).read_bytes()
        if raw != old_bytes('artifacts/' + name) or record(raw) != {k: entries[identifier][k] for k in ('bytes', 'sha256')}:
            raise ValueError('The new layout RTL differs from original synthesis source: ' + name)
        pending['artifacts/' + name] = raw
    for key, relative in (('synthesis_json', 'artifacts/synthesis.json'), ('synthesis_verilog', 'artifacts/synthesis.v')):
        source = roles._INPUTS[key]
        pending[relative] = old_bytes(source)
        lineage['reused_files'].append({'source': roles._BASE + '/' + source, 'target': relative, **record(pending[relative])})
    for identifier, relative in (('gds', 'artifacts/final.gds'), ('def', 'artifacts/final.def'), ('netlist', 'artifacts/final.nl.v')):
        raw = _artifact_path(layout['checks'], entries[identifier]).read_bytes()
        if record(raw) != {k: entries[identifier][k] for k in ('bytes', 'sha256')}:
            raise ValueError('The new layout artifact changed: ' + identifier)
        pending[relative] = raw
        lineage['new_geometry_files'].append({'artifact_id': identifier, 'target': relative, **record(raw)})
    pending['source_binding.json'] = json_bytes(lineage)
    pending['README.md'] = (f'# Repaired-layout Functional Map source\n\n'
        f'This read-only source bundle binds `{layout["id"]}` to its actual GDS, DEF and mapped netlist. '
        'The original GUI job, seven RTL sources and synthesis metadata are retained byte-for-byte. '
        'Source metadata is reused from the original mapping; geometry belongs to this new layout. '
        'Creating this visualization source bundle performs no EDA or adoption action.\n').encode('utf-8')
    output.mkdir(parents=True)
    for relative, raw in pending.items():
        path = output / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as handle:
            handle.write(raw)
    manifest = {'kind': 'immutable_repaired_layout_role_source', 'validation_status': 'Passed',
                'layout_run_id': layout['id'], 'files': {name: record(raw) for name, raw in pending.items()}}
    raw_manifest = json_bytes(manifest)
    (output / 'manifest.json').write_bytes(raw_manifest)
    profile = {'source_root': output.relative_to(ROOT).as_posix(),
               'source_manifest_sha256': hashlib.sha256(raw_manifest).hexdigest(), 'layout_run_id': layout['id'],
               'inputs': {'synthesis_json': 'artifacts/synthesis.json', 'synthesis_verilog': 'artifacts/synthesis.v',
                          'final_verilog': 'artifacts/final.nl.v', 'final_def': 'artifacts/final.def'},
               'expected_final_cells': len(roles.parse_def_components(pending['artifacts/final.def'].decode('utf-8'))),
               'expected_synthesis_cells': len(roles.parse_structural_verilog(pending['artifacts/synthesis.v'].decode('utf-8'))['cells']),
               'gds_relative_path': 'artifacts/final.gds'}
    profile_output.parent.mkdir(parents=True, exist_ok=True)
    with profile_output.open('xb') as handle:
        handle.write(json_bytes(profile))
    return profile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--layout-record', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=ROOT / 'results/npu_layout_repaired_source')
    parser.add_argument('--profile-output', type=Path, default=ROOT / 'configs/layout_roles_repaired_source.json')
    args = parser.parse_args()
    print(json.dumps(prepare(json.loads(args.layout_record.read_text(encoding='utf-8')), args.output, args.profile_output), indent=2))


if __name__ == '__main__':
    main()
