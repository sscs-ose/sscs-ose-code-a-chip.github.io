#!/usr/bin/env python3
"""Inventory observed MHA stimuli without executing recipes or asserting freshness.

Sources are read-only JSON, SPICE decks, and literal Python seed declarations.
Every observed vector is conservatively reserved, including prepared stimuli.
Case names, generator-local ranks, seeds and exact vector identities remain
distinct. Only an explicit payload or a content-hash link establishes identity.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter, defaultdict
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
CASE = re.compile(r'^mha_(\d+)(?:_([ab]))?(?:_[A-Za-z0-9_]+)?$')
HASH = re.compile(r'^[a-fA-F0-9]{64}$')
DECK_SUFFIXES = {'.spice', '.cir', '.deck', '.sp', '.ckt'}
SEED_KEYS = {'seed', 'random_seed', 'rng_seed', 'mha_seed', 'dataset_seed'}
INDEX_KEYS = {'vector_index', 'sample_index', 'sample_id', 'mha_index', 'token_index'}
SKIP_DIRS = {'.git', '.agents', '.codex', '__pycache__', '.pytest_cache',
             'node_modules', 'issue_reproducible', 'tests', '.venv', 'venv'}


def digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                             allow_nan=False).encode()).hexdigest()


def vector_payload(node):
    """Do not infer a vector from a case name, deck name or integer sums."""
    if 'activation_x2' not in node or 'ternary_weights' not in node:
        return None
    acts, weights = node['activation_x2'], node['ternary_weights']
    if not isinstance(acts, list) or not acts or not isinstance(weights, list):
        raise ValueError('invalid activation/weight arrays')
    if len(weights) != len(acts) or not all(isinstance(row, list) and row for row in weights):
        raise ValueError('activation/weight dimensions differ')
    if len({len(row) for row in weights}) != 1:
        raise ValueError('nonrectangular weight matrix')

    def integer(x):
        if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) or int(x) != x:
            raise ValueError('nonintegral vector scalar')
        return int(x)

    acts = [integer(x) for x in acts]
    weights = [[integer(x) for x in row] for row in weights]
    if any(x not in (-1, 0, 1) for row in weights for x in row):
        raise ValueError('nonternary weights')
    return {'activation_x2': acts, 'ternary_weights': weights}


def candidate_status(payload, registry):
    vector = vector_payload(payload)
    fp = digest(vector) if vector is not None else None
    if fp is None:
        raise ValueError('candidate requires explicit activation_x2 and ternary_weights')
    return {'vector_sha256': fp, 'holdout_freshness_asserted': False,
            'status': ('PREVIOUSLY_OBSERVED_RESERVED' if fp in registry['vectors']
                       else 'NOT_OBSERVED_FRESHNESS_UNPROVEN')}


def pointer(parent, key):
    return parent+'/'+str(key).replace('~', '~0').replace('/', '~1')


def unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError('duplicate JSON key: '+key)
        value[key] = item
    return value


def seed_literals(text):
    """Static recipe observations only; never execute or bind a default to jobs."""
    tree = ast.parse(text)
    found = []

    def add(value, line, kind):
        try:
            literal = ast.literal_eval(value)
        except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
            literal = None
        if not isinstance(literal, (int, str)) or isinstance(literal, bool):
            literal = None
        found.append({'line': line, 'value': literal, 'kind': kind,
                      'expression': (ast.get_source_segment(text, value) or '')[:160],
                      'scope': 'recipe literal/expression; not proof that a job used this seed'})

    for node in ast.walk(tree):
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if node.target.id.lower() in SEED_KEYS and node.value is not None:
                add(node.value, node.lineno, 'annotated_seed')
        elif isinstance(node, ast.Assign):
            if any(isinstance(t, ast.Name) and t.id.lower() in SEED_KEYS for t in node.targets):
                add(node.value, node.lineno, 'assigned_seed')
        elif isinstance(node, ast.Call):
            for kw in node.keywords:
                if kw.arg and kw.arg.lower() in SEED_KEYS:
                    add(kw.value, node.lineno, 'seed_keyword')
            if isinstance(node.func, ast.Attribute) and node.func.attr in {'default_rng', 'seed'} and node.args:
                add(node.args[0], node.lineno, 'rng_call')
    return found


def build_registry(root, *, exclude=(), max_file_bytes=2*1024*1024):
    root = Path(root).resolve()
    excluded = {Path(p).resolve() for p in exclude}
    excluded.add(Path(__file__).resolve())
    sources, texts, skipped = {}, {}, []
    inventory = Counter()
    for base, dirs, files in os.walk(root, followlinks=False):
        for name in sorted(dirs):
            path = Path(base)/name
            if name in SKIP_DIRS or path.is_symlink() or path.relative_to(root).as_posix() == 'build/tools':
                dirs.remove(name)
                skipped.append({'path': path.relative_to(root).as_posix(), 'reason': 'excluded_directory'})
        dirs.sort()
        for name in sorted(files):
            path = Path(base)/name
            suffix = path.suffix.lower()
            if path.resolve() in excluded:
                continue
            if suffix not in {'.json', '.py', *DECK_SUFFIXES}:
                if suffix in {'.zip', '.npz', '.npy', '.ipynb'}:
                    inventory['unscanned'+suffix] += 1
                continue
            rel = path.relative_to(root).as_posix()
            try:
                if path.is_symlink():
                    skipped.append({'path': rel, 'reason': 'symlink_not_followed'})
                    continue
                size = path.stat().st_size
                if size > max_file_bytes:
                    skipped.append({'path': rel, 'reason': 'size_limit', 'bytes': size})
                    continue
                raw = path.read_bytes()
                if len(raw) > max_file_bytes:
                    raise ValueError('file grew beyond scan budget')
                fp = sha256(raw).hexdigest()
                inventory['files_read'] += 1
                kind = 'json' if suffix == '.json' else 'python' if suffix == '.py' else 'deck'
                source_id = kind+':'+fp
                if source_id in sources:
                    sources[source_id]['paths'].append(rel)
                    continue
                text = raw.decode('utf-8-sig', errors='strict')
                sources[source_id] = {'sha256': fp, 'kind': kind, 'bytes': len(raw), 'paths': [rel]}
                texts[source_id] = text
            except (OSError, UnicodeError, ValueError) as error:
                skipped.append({'path': rel, 'reason': type(error).__name__, 'error': str(error)[:200]})

    vectors = {}
    identifiers, indices, seeds, deck_refs, source_claims, errors = [], [], [], [], [], []

    def label(value, source_id, at, context, vector=None, relationship='case_reference'):
        match = CASE.fullmatch(value) if isinstance(value, str) else None
        if match:
            identifiers.append({'label': value, 'generator_local_rank': int(match[1]),
                'phase_label': match[2], 'source_id': source_id, 'pointer': at,
                'index_sha256': digest({'source_id': source_id, 'generator_local_label': value}),
                'index_namespace': 'source content only; generator/dataset namespace unproven',
                'vector_sha256': vector, 'declared_roles': context['roles'],
                'relationship': relationship})

    def walk(node, source_id, at='', context=None):
        context = context or {'seeds': [], 'roles': [], 'labels': [], 'status': None}
        if isinstance(node, list):
            for i, item in enumerate(node):
                walk(item, source_id, pointer(at, i), context)
            return
        if isinstance(node, str):
            label(node, source_id, at, context)
            return
        if not isinstance(node, dict):
            return
        ctx = {k: list(v) if isinstance(v, list) else v for k, v in context.items()}
        if isinstance(node.get('status'), str):
            ctx['status'] = node['status']
        for key, val in node.items():
            key_lower = str(key).lower()
            if key_lower in SEED_KEYS and isinstance(val, (int, str)) and not isinstance(val, bool):
                obs = {'source_id': source_id, 'pointer': pointer(at, key), 'key': key,
                       'value': val, 'seed_sha256': digest({'key': key_lower, 'value': val})}
                seeds.append(obs)
                ctx['seeds'].append(obs)
            if key_lower in {'role', 'purpose', 'split', 'group'} and isinstance(val, str):
                ctx['roles'].append({'pointer': pointer(at, key), 'value': val})
            if val is True and ('holdout' in key_lower and any(s in key_lower for s in ('select', 'reuse'))):
                source_claims.append({'source_id': source_id, 'pointer': pointer(at, key), 'value': True})
            if CASE.fullmatch(str(key)):
                label(str(key), source_id, pointer(at, key), ctx)
        direct_labels = {k: v for k, v in node.items() if isinstance(v, str) and CASE.fullmatch(v)}
        ctx['labels'] = sorted(set(ctx['labels']+list(direct_labels.values())))
        try:
            payload = vector_payload(node)
        except ValueError as error:
            errors.append({'source_id': source_id, 'pointer': at, 'reason': str(error)})
            payload = None
        vector = digest(payload) if payload is not None else None
        deck_hash = node.get('deck_sha256')
        if not isinstance(deck_hash, str) or not HASH.fullmatch(deck_hash):
            item = node.get('deck')
            deck_hash = item.get('sha256') if isinstance(item, dict) else None
        deck_hash = deck_hash.lower() if isinstance(deck_hash, str) and HASH.fullmatch(deck_hash) else None
        explicit_indices = {k: v for k, v in node.items() if str(k).lower() in INDEX_KEYS
                            and isinstance(v, (str, int)) and not isinstance(v, bool)}
        for key, value in explicit_indices.items():
            indices.append({'source_id': source_id, 'pointer': pointer(at, key),
                'key': key, 'value': value, 'vector_sha256': vector,
                'labels': ctx['labels'], 'seeds': ctx['seeds'],
                'index_sha256': digest({'key': key, 'value': value}),
                'scope': 'explicit declared index; dataset/generator namespace may be missing'})
        observation = {'source_id': source_id, 'pointer': at, 'labels': ctx['labels'],
            'declared_roles': ctx['roles'], 'seeds': ctx['seeds'], 'explicit_indices': explicit_indices,
            'context_status_claim': ctx['status'], 'deck_sha256': deck_hash}
        if vector is not None:
            entry = vectors.setdefault(vector, {'payload': payload, 'observations': [],
                'policy': 'reserved_by_observation_including_prepared_or_inspected_stimuli'})
            entry['observations'].append(observation)
        for key, value in direct_labels.items():
            parent_reference = str(key).lower().startswith('parent')
            label(value, source_id, pointer(at, key), ctx, None if parent_reference else vector,
                  'parent_reference' if parent_reference else 'case_reference')
        if deck_hash:
            deck_refs.append({**observation, 'vector_sha256': vector,
                'deck_path_claim': node.get('deck') if isinstance(node.get('deck'), str) else None})
        for key, val in node.items():
            if key in {'activation_x2', 'ternary_weights'} or key in direct_labels:
                continue
            child = {**ctx, 'roles': list(ctx['roles'])}
            if CASE.fullmatch(str(key)):
                child['labels'] = sorted(set(ctx['labels']+[str(key)]))
            if any(s in str(key).lower() for s in ('holdout', 'train', 'calibrat', 'selection')):
                child['roles'].append({'pointer': pointer(at, key), 'value': str(key), 'scope': 'JSON content key'})
            walk(val, source_id, pointer(at, key), child)

    for source_id, text in texts.items():
        kind = sources[source_id]['kind']
        try:
            if kind == 'json':
                node = json.loads(text, object_pairs_hook=unique_object)
                if isinstance(node, dict) and node.get('format') == 'automx-cim-global-consumed-mha-registry-v1':
                    sources[source_id]['scope'] = 'prior registry excluded from evidence traversal'
                else:
                    walk(node, source_id)
            elif kind == 'python':
                for obs in seed_literals(text):
                    seeds.append({'source_id': source_id, **obs,
                                  'seed_sha256': digest({'recipe_value': obs['value'], 'expression': obs['expression']})})
            else:
                for number, line in enumerate(text.splitlines(), 1):
                    if line.lower().startswith('.title'):
                        for value in re.findall(r'\bmha_\d+(?:_[A-Za-z0-9_]+)?\b', line):
                            label(value, source_id, 'line:'+str(number), {'roles': []})
        except (ValueError, SyntaxError, RecursionError) as error:
            errors.append({'source_id': source_id, 'reason': type(error).__name__, 'error': str(error)[:200]})

    deck_sources = {s['sha256']: source_id for source_id, s in sources.items() if s['kind'] == 'deck'}
    by_deck = defaultdict(set)
    for ref in deck_refs:
        if ref['vector_sha256']:
            by_deck[ref['deck_sha256']].add(ref['vector_sha256'])
    links = []
    mha_decks = set(by_deck)
    mha_decks.update(sources[i['source_id']]['sha256'] for i in identifiers
                     if sources[i['source_id']]['kind'] == 'deck')
    for ref in deck_refs:
        if not ref['vector_sha256'] and not ref['labels'] and ref['deck_sha256'] not in mha_decks:
            continue
        actual = deck_sources.get(ref['deck_sha256'])
        known = sorted(by_deck[ref['deck_sha256']])
        link = {**ref, 'matching_deck_source_id': actual, 'payloads_claiming_this_deck': known,
                'link_status': 'CONTENT_HASH_MATCH' if actual else 'DECK_CONTENT_NOT_SCANNED'}
        claim = ref['deck_path_claim']
        if claim:
            claimed = Path(claim)
            claimed = claimed if claimed.is_absolute() else root/claimed
            try:
                relative = claimed.resolve().relative_to(root).as_posix()
                link['claimed_path_status'] = ('VERIFIED' if actual and relative in sources[actual]['paths']
                                               else 'MISSING_OR_HASH_MISMATCH')
            except ValueError:
                link['claimed_path_status'] = 'OUTSIDE_ROOT_NOT_READ'
        links.append(link)
    # A label alone never inherits another record's payload or seed. A matched
    # deck hash can link an otherwise vectorless receipt to explicit payloads.
    for item in identifiers:
        if item['vector_sha256'] is None and sources[item['source_id']]['kind'] == 'deck':
            item['payloads_linked_by_deck_sha256'] = sorted(by_deck[sources[item['source_id']]['sha256']])
        elif item['vector_sha256'] is None and item['relationship'] != 'parent_reference':
            related = [ref for ref in links if ref['source_id'] == item['source_id'] and
                       (item['pointer'] == ref['pointer'] or item['pointer'].startswith(ref['pointer']+'/'))]
            item['payloads_linked_by_deck_sha256'] = sorted({fp for ref in related
                                                            for fp in ref['payloads_claiming_this_deck']})
    missing_seed = [fp for fp, v in vectors.items() if not any(o['seeds'] for o in v['observations'])]
    unresolved = sum(not i['vector_sha256'] and not i.get('payloads_linked_by_deck_sha256') for i in identifiers)
    conflicts = {k: sorted(v) for k, v in by_deck.items() if len(v) > 1}
    rank_values = sorted({i['generator_local_rank'] for i in identifiers})
    return {'format': 'automx-cim-global-consumed-mha-registry-v1',
        'scan_utc': datetime.now(timezone.utc).isoformat(),
        'scanner': {'path': 'scripts/'+Path(__file__).name,
                    'sha256': sha256(Path(__file__).read_bytes()).hexdigest()},
        'root': str(root), 'policy': {'holdout_freshness_asserted': False,
            'observed_vectors_reserved': True, 'filenames_used_to_infer_identity': False,
            'case_indices_are_generator_local_not_dataset_indices': True,
            'seed_defaults_not_bound_to_historical_jobs': True,
            'receipt_status_is_a_recorded_claim_not_raw_or_signoff_revalidation': True},
        'coverage': {'complete': False, 'status': 'INCOMPLETE_PROVENANCE_COVERAGE',
            'reasons': ['Archives, binary arrays, notebooks, logs and external/deleted sessions are not scanned.',
                'Excluded directories and oversized/unreadable sources are listed.',
                'Unresolved labels, missing per-vector seed provenance and missing/conflicting deck links remain conservative exclusions.',
                'Concurrent source reads are not an atomic snapshot; every observed content hash is retained.'],
            'max_file_bytes': max_file_bytes, 'inventory': dict(inventory), 'skipped': skipped,
            'unrelated_deck_reference_nodes_ignored': len(deck_refs)-len(links),
            'parse_or_payload_errors': errors, 'vectors_missing_explicit_seed_provenance': missing_seed,
            'identifier_observations_without_payload_link': unresolved,
            'deck_links_without_scanned_content': sum(x['matching_deck_source_id'] is None for x in links),
            'conflicting_deck_payloads': conflicts},
        'summary': {'unique_vectors': len(vectors), 'vector_observations': sum(len(v['observations']) for v in vectors.values()),
            'unique_source_contents': len(sources), 'identifier_observations': len(identifiers),
            'explicit_index_observations': len(indices),
            'generator_local_rank_values': rank_values, 'seed_observations': len(seeds),
            'explicit_holdout_reuse_or_selection_claims': len(source_claims)},
        'sources': sources, 'vectors': dict(sorted(vectors.items())), 'identifiers': identifiers,
        'explicit_index_observations': indices,
        'seed_observations': seeds, 'deck_receipt_links': links,
        'explicit_holdout_reuse_or_selection_claims': source_claims}


def markdown(report):
    s, c = report['summary'], report['coverage']
    ranks = s['generator_local_rank_values']
    rank_text = (f'{ranks[0]}–{ranks[-1]} ({len(ranks)} distinct ranks)'
                 if ranks and ranks == list(range(ranks[0], ranks[-1]+1)) else str(ranks))
    return '\n'.join([
        '# Global consumed MHA usage registry — source inventory', '',
        '**Coverage: INCOMPLETE. Holdout freshness is not asserted.**', '',
        f"Observed {s['unique_vectors']} exact activation/weight payloads in {s['vector_observations']} records; "
        f"{s['unique_source_contents']} distinct source contents scanned.", '',
        'Every observed vector is reserved conservatively, including prepared, inspected, training and holdout stimuli. '
        'An unseen fingerprint is only unobserved in this inventory, never certified fresh.', '',
        'Identity is SHA-256 of canonical activation_x2 plus ternary_weights JSON. '
        'Labels/ranks, explicit dataset indices, seeds, source hashes and JSON pointers remain separate. '
        'Local-index fingerprints include the source content hash; equal ranks in different artifacts are not assumed '
        'to identify the same dataset sample. Deck and vectorless receipt associations use exact deck hashes. '
        'Filenames establish no vector, rank, role or freshness.', '',
        f"Generator-local ranks observed: {rank_text}. These are not dataset indices.", '',
        f"Missing explicit per-vector seed provenance: {len(c['vectors_missing_explicit_seed_provenance'])}. "
        f"Identifier observations without a payload link: {c['identifier_observations_without_payload_link']}. "
        f"Deck references lacking scanned content: {c['deck_links_without_scanned_content']}. "
        f"Conflicting deck/payload associations: {len(c['conflicting_deck_payloads'])}.", '',
        f"Explicit JSON claims of old holdout reuse/selection: {s['explicit_holdout_reuse_or_selection_claims']}. "
        'These claims retain their source/pointer; an old holdout used for selection must not be reused as a fresh final holdout.', '',
        'Python seed literals are recipe observations only. The current config default does not prove that historical '
        'jobs used that seed. Receipt PASS/MEASURED statuses are recorded claims; this scan does not revalidate native raw.', '',
        'Coverage gaps, skipped sources, archive/array/notebook counts, parse failures and every source hash/path are in the JSON. '
        'Exports with identical contents share one source record and retain every observed path. '
        'No MHA generator, simulator, notebook, archive extraction or native physical flow is executed.', '',
        'Rebuild from the repository root:', '', '```bash',
        'PYTHONDONTWRITEBYTECODE=1 /home/nam/anaconda3/envs/env_mamba/bin/python \\',
        '  scripts/build_flow2_mha_usage_registry.py --root . \\',
        '  --output docs/flow2_mha_usage_registry_20261021.json \\',
        '  --markdown docs/flow2_mha_usage_registry_20261021.md', '```', '',
        'For a proposed vector, add `--candidate-json /path/to/vector.json`. The candidate must contain explicit '
        '`activation_x2` and `ternary_weights`; its file is excluded from the consumed-source scan. '
        'Known payloads return PREVIOUSLY_OBSERVED_RESERVED; unseen payloads return NOT_OBSERVED_FRESHNESS_UNPROVEN.', '',
        'Before a fresh holdout: resolve missing provenance, inventory prior design/decoder selection usage and external '
        'or archived sources, freeze training/calibration, then reserve the new candidate fingerprints before evaluation. '
        'Qualified Stage 6 and strict Stage 8 remain pending coupled ADC/readout and their separate qualification gates.', ''])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=ROOT)
    p.add_argument('--output', type=Path)
    p.add_argument('--markdown', type=Path)
    p.add_argument('--candidate-json', type=Path)
    p.add_argument('--max-file-bytes', type=int, default=2*1024*1024)
    a = p.parse_args()
    if a.max_file_bytes <= 0:
        p.error('positive file byte budget required')
    exclude = [x for x in (a.output, a.markdown, a.candidate_json) if x]
    # Also omit the owned registry outputs on read-only summary invocations.
    exclude += list(a.root.resolve().glob('docs/flow2_mha_usage_registry_*.json'))
    report = build_registry(a.root, exclude=exclude, max_file_bytes=a.max_file_bytes)
    if a.candidate_json:
        report['candidate_check'] = candidate_status(json.loads(a.candidate_json.read_text(), object_pairs_hook=unique_object), report)
    if a.output:
        a.output.write_text(json.dumps(report, sort_keys=True, indent=2)+'\n')
    if a.markdown:
        a.markdown.write_text(markdown(report))
    summary = dict(report['summary'])
    ranks = summary.pop('generator_local_rank_values')
    summary['generator_local_rank_range'] = [min(ranks), max(ranks)] if ranks else []
    summary['distinct_generator_local_ranks'] = len(ranks)
    print(json.dumps({**summary, 'coverage': report['coverage']['status'],
                      'holdout_freshness_asserted': False,
                      'candidate_check': report.get('candidate_check')}, sort_keys=True))


if __name__ == '__main__':
    main()
