"""Verify the retained S14 readiness bytes and original-job lineage offline.

Does not launch a simulator, write a project or produce dynamic Passed evidence.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from hullcirq.postlayout_workflow import validate_source_snapshot
from hullcirq.verification import object_hash


def check_archive(folder):
    folder = Path(folder).resolve()
    manifest = json.loads((folder / 'manifest.json').read_text(encoding='utf-8'))
    decoded = {}
    for entry in manifest['files']:
        rel = PurePosixPath(entry['stored_path'])
        if rel.is_absolute() or any(p in ('..', '.') for p in rel.parts) or '\\' in str(rel) or ':' in str(rel):
            raise ValueError('Unsafe archive path')
        path = (folder / str(rel)).resolve()
        if not path.is_relative_to(folder): raise ValueError('Archive path escapes its directory')
        payload = path.read_bytes()
        if len(payload) != entry['bytes'] or hashlib.sha256(payload).hexdigest() != entry['sha256']:
            raise ValueError('Stored bytes changed: ' + str(rel))
        raw = gzip.decompress(payload) if entry.get('encoding') == 'gzip' else payload
        if len(raw) != entry['decoded_bytes'] or hashlib.sha256(raw).hexdigest() != entry['decoded_sha256']:
            raise ValueError('Decoded bytes changed: ' + str(rel))
        decoded[entry['role']] = raw
    run = json.loads(decoded['run-api'])
    validate_source_snapshot(run)
    if not (run['execution_scope'] == 'compatibility_preflight_only'
            and run['verification_supported'] is False and run['checks']['executed'] is False
            and run['checks']['commands'] == [] and run['validation_status'] == 'Unsupported'
            and run['review_status'] == 'Awaiting Review'):
        raise ValueError('Readiness cannot be represented as adopted dynamic evidence')
    for artifact in run['checks']['artifacts']:
        raw = decoded['artifact:' + artifact['id']]
        if len(raw) != artifact['bytes'] or hashlib.sha256(raw).hexdigest() != artifact['sha256']:
            raise ValueError('Artifact differs from exact run: ' + artifact['id'])
    plan = json.loads(decoded['artifact:frozen-verification-plan'])
    if object_hash(plan) != run['verification_plan_sha256'] or object_hash(plan) != object_hash(run['verification_plan']):
        raise ValueError('Original plan changed')
    models = json.loads(decoded['artifact:cell-models'])
    for name, model in models.items():
        raw = model['original_text'].encode('utf-8')
        if len(raw) != model['bytes'] or hashlib.sha256(raw).hexdigest() != model['sha256']:
            raise ValueError('Original PDK model bytes changed: ' + name)
    for key, artifact in (('gds', 'input-gds'), ('def', 'input-def'), ('netlist', 'input-netlist'),
                          ('powered_netlist', 'input-powered-netlist'), ('sdf', 'input-sdf')):
        if hashlib.sha256(decoded['artifact:' + artifact]).hexdigest() != run['source_inputs'][key]['sha256']:
            raise ValueError('Physical source binding changed: ' + key)
    return {'archive_integrity': 'Passed', 'run_id': run['id'], 'files_checked': len(manifest['files']),
            'verification_plan_sha256': run['verification_plan_sha256'],
            'original_expected_outputs': plan['output_count'], 'dynamic_simulator_started': False,
            'dynamic_validation': 'Unsupported', 'S14_accepted': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', nargs='?', type=Path, default=ROOT / 'results/npu_postlayout_readiness')
    args = parser.parse_args()
    print(json.dumps(check_archive(args.archive), indent=2))
