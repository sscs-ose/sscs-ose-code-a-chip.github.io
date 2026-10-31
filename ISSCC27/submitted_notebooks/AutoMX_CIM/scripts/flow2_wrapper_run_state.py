"""Read-only wrapper/native state inspection; completion is not a signoff PASS.

Lock files are probed in place and never created, truncated or removed. A native
run is complete only with its own terminal metrics and nonempty final views.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

from scripts import flow2_integration_common as common

ACTIVE = 'ACTIVE'
COMPLETED = 'COMPLETED'
FAILED_INCOMPLETE = 'FAILED_INCOMPLETE'
EMPTY = 'EMPTY'
METADATA_CONFLICT = 'METADATA_CONFLICT'
TOP = 'automx_cim_mixed_signal_proto'
SUFFIXES = ('', '_impl', '_impl_gds', '_impl_gds_dev', '_impl_rtl',
            '_impl_lint', '_impl_cond', '_impl_adc')


def read_json(path):
    """Missing or malformed receipts are evidence, never a successful cache hit."""
    try:
        value = Path(path).read_text(encoding='utf-8')
        data = json.loads(value)
        return data if isinstance(data, dict) else None
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None


def active_locks(paths):
    import fcntl
    active = []
    for path in dict.fromkeys(map(Path, paths)):
        try:
            stream = path.open('r')
        except FileNotFoundError:
            continue
        with stream:
            try:
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                active.append(str(path))
            else:
                fcntl.flock(stream, fcntl.LOCK_UN)
    return active


def classify_native_run(run_dir, *, result_dir=None, identity=None, lock_paths=()):
    """Classify raw native artifacts without running tools or writing receipts.

    result_dir identifies the GDS child's results directory, when available.
    Supplying identity checks its inputs.json; otherwise metrics still must
    belong to run_dir.name. COMPLETED says nothing about DRC/STA acceptance.
    """
    run_dir = Path(run_dir)
    result_dir = Path(result_dir) if result_dir is not None else None
    locks = [*lock_paths, run_dir/'runner.lock']
    if result_dir is not None:
        locks.append(result_dir/'runner.lock')
    active = active_locks(locks)
    out = {'state': EMPTY, 'reasons': [], 'run_dir': str(run_dir),
           'occupied': run_dir.exists(), 'active_locks': active, 'metrics': {}}
    if active:
        return {**out, 'state': ACTIVE, 'reasons': ['runner lock is held']}
    if identity is not None:
        if result_dir is None:
            raise ValueError('result_dir is required to compare native inputs')
        snapshot = result_dir/'inputs.json'
        if snapshot.exists() and read_json(snapshot) != identity:
            return {**out, 'state': METADATA_CONFLICT, 'reasons': ['native inputs differ or are malformed']}
        if run_dir.exists() and not snapshot.exists():
            return {**out, 'state': METADATA_CONFLICT, 'reasons': ['occupied native run has no input identity']}
    if not run_dir.exists():
        return out
    if not run_dir.is_dir():
        return {**out, 'state': FAILED_INCOMPLETE, 'reasons': ['native path is not a directory']}
    if not any(p.name != 'runner.lock' for p in run_dir.iterdir()):
        return {**out, 'reasons': ['native directory is empty; no measurements']}
    metrics_path = run_dir/'reports/metrics.csv'
    try:
        with metrics_path.open(encoding='utf-8', newline='') as stream:
            rows = list(csv.DictReader(stream))
        metrics = rows[0] if len(rows) == 1 else {}
    except (OSError, UnicodeError, csv.Error):
        metrics = {}
    out['metrics'] = metrics
    if metrics.get('config') not in (None, '', run_dir.name):
        return {**out, 'state': METADATA_CONFLICT, 'reasons': ['metrics belong to another run: '+str(metrics['config'])]}
    reasons = []
    if metrics.get('flow_status') != 'flow completed':
        reasons.append('native flow did not complete' if metrics else 'native metrics missing or malformed')
    for kind in ('gds', 'lef', 'lib'):
        path = run_dir/f'results/final/{kind}/{TOP}.{kind}'
        if not path.is_file() or not path.stat().st_size:
            reasons.append('missing or empty final '+kind.upper())
    spefs = (run_dir/'results/final/spef').rglob('*.spef*')
    if not any(p.is_file() and p.stat().st_size for p in spefs):
        reasons.append('missing or empty extracted SPEF')
    return {**out, 'state': FAILED_INCOMPLETE if reasons else COMPLETED, 'reasons': reasons}


def namespace_paths(root, tag):
    common.tag_ok(tag)
    bases = (common.BASE, common.BUILD, common.PHYSICAL,
             Path('server_results/flow2_wrapper_integration'))
    return [Path(root)/base/(tag+suffix) for base in bases for suffix in SUFFIXES]


def classify_parent_run(root, tag, identity=None, *, held_locks=()):
    """An occupied child reserves the entire parent namespace, even if empty."""
    root = Path(root).resolve()
    paths = namespace_paths(root, tag)
    held_locks = set(map(Path, held_locks))
    active = active_locks(path/'runner.lock' for path in paths if path/'runner.lock' not in held_locks)
    out = {'state': EMPTY, 'tag': tag, 'reasons': [], 'active_locks': active,
           'occupied_paths': [str(p) for p in paths if p.exists()]}
    if active:
        return {**out, 'state': ACTIVE, 'reasons': ['parent or child runner lock is held']}
    folder = root/common.BASE/tag
    snapshot = folder/'inputs.json'
    saved = read_json(snapshot)
    if snapshot.exists() and (saved is None or (identity is not None and saved != identity)):
        return {**out, 'state': METADATA_CONFLICT, 'reasons': ['parent inputs differ or are malformed']}
    native = classify_native_run(root/common.BUILD/(tag+'_impl_gds')/'design/runs'/(tag+'_impl_gds'),
                                 result_dir=root/common.BASE/(tag+'_impl_gds'))
    out['native'] = native
    evidence = [p for p in paths if p.exists() and p != folder]
    if folder.is_dir():
        evidence.extend(p for p in folder.iterdir() if p.name not in ('inputs.json', 'runner.lock'))
    elif folder.exists():
        evidence.append(folder)
    if evidence and saved is None:
        return {**out, 'state': METADATA_CONFLICT, 'reasons': ['occupied namespace has no parent input identity']}
    if native['state'] in (ACTIVE, METADATA_CONFLICT):
        return {**out, 'state': native['state'], 'reasons': native['reasons']}
    if native['state'] == COMPLETED:
        return {**out, 'state': COMPLETED, 'reasons': ['terminal native metrics and final views present']}
    if evidence:
        return {**out, 'state': FAILED_INCOMPLETE,
                'reasons': native['reasons'] or ['parent or child output namespace is already occupied']}
    return out
