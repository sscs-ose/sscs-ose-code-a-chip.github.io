"""Frozen, shared rules for the configurable-workflow study."""
from __future__ import annotations

import hashlib
import itertools
import json
import math
import random
from pathlib import Path

MODEL = 'gpt-6.1-sol'
SEED = 20261016
KEYS = ('utilization', 'density', 'abc_area', 'repair_margin')
DOMAINS = ((30, 40, 50), (0.55, 0.65), (0, 1), (0, 10, 20))
BASELINE = dict(zip(KEYS, (40, 0.55, 0, 0)))
WORKLOADS = ('DOT64', 'GEMM8', 'CONV3')


def digest(path):
    with Path(path).open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n')
    temporary.replace(path)


def config_tuple(config):
    if set(config) != set(KEYS):
        raise ValueError('Candidate must contain exactly: ' + ', '.join(KEYS))
    for key, domain in zip(KEYS, DOMAINS):
        value = config[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError('Non-finite or non-numeric parameter: ' + key)
        if value not in domain:
            raise ValueError('Parameter outside frozen domain: ' + key)
        if key != 'density' and type(value) is not int:
            raise ValueError('Integer parameter required: ' + key)
    return tuple(config[key] for key in KEYS)


def score(area, energies, baseline_area, baseline_energies):
    if set(energies) != set(WORKLOADS) or set(baseline_energies) != set(WORKLOADS):
        raise ValueError('All three workload energies are required')
    values = [area, baseline_area, *energies.values(), *baseline_energies.values()]
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v <= 0 for v in values):
        raise ValueError('Area and energy measurements must be finite and positive')
    energy_ratio = math.exp(sum(math.log(energies[w] / baseline_energies[w]) for w in WORKLOADS) / 3)
    return {'score': area / baseline_area * energy_ratio, 'energy_ratio': energy_ratio,
            'area_ratio': area / baseline_area}


def ranking(row):
    return (row['score'], row['energy_ratio'], row['cell_area_um2'], row['candidate_index'])


def rule_candidate(history):
    """Transparent W0 heuristic; use only this session's frozen observations."""
    seen = {config_tuple(row['configuration']) for row in history}
    latest = history[-1]
    qualified = [row for row in history if row.get('rank_eligible')]
    current = latest if not latest.get('rank_eligible') else min(qualified, key=ranking)
    config = current['configuration']
    failures = set(current.get('failure_classes', []))
    if failures & {'routing', 'drc'}:
        moves = [('utilization', -1), ('density', -1)]
        reason = 'routing_or_drc_failure'
    elif 'timing' in failures:
        moves = [('abc_area', -1), ('utilization', -1), ('density', -1)]
        reason = 'timing_failure'
    elif 'electrical' in failures:
        moves = [('repair_margin', 1), ('utilization', -1), ('density', -1)]
        reason = 'electrical_failure'
    elif current.get('rank_eligible'):
        moves = [('abc_area', 1), ('utilization', 1), ('density', 1), ('repair_margin', -1)]
        reason = 'qualified_incumbent'
    else:
        moves = []
        reason = 'unclassified_failure'
    for key, direction in moves:
        domain = DOMAINS[KEYS.index(key)]
        index = domain.index(config[key]) + direction
        if 0 <= index < len(domain):
            candidate = dict(config, **{key: domain[index]})
            if config_tuple(candidate) not in seen:
                return candidate, {'rule': reason, 'changed_parameter': key}
    for values in itertools.product(*DOMAINS):
        if values not in seen:
            return dict(zip(KEYS, values)), {'rule': 'lexicographic_fallback', 'trigger': reason}
    raise ValueError('Search space exhausted')


def preregistration():
    rng = random.Random(SEED)
    generation = []
    for repetition in range(1, 4):
        cells = list(itertools.product(('fresh', 'ip'), ('single', 'multi')))
        rng.shuffle(cells)
        generation.extend({'input': entry, 'roles': roles, 'repetition': repetition,
                           'id': f'{entry}-{roles}-{repetition}'} for entry, roles in cells)
    sessions = [{'id': 'W0-1', 'workflow': 'W0', 'repetition': 1}]
    sessions += [{'id': f'{w}-{i}', 'workflow': w, 'repetition': i}
                 for w in ('W1', 'W2') for i in range(1, 4)]
    rng.shuffle(sessions)
    return {'schema_version': 1, 'seed': SEED, 'model': MODEL, 'reasoning_effort': 'high',
            'generation': {'jobs': generation, 'total_budget_seconds': 1200,
                           'final_evaluation_outside_budget': True},
            'ppa': {'sessions': sessions, 'new_candidates_per_session': 3,
                    'aggregate_agent_budget_seconds': 1200, 'physical_timeout_seconds': 14400,
                    'postprocess_timeout_seconds': 1800, 'period_ps': 10526,
                    'baseline_configuration': BASELINE, 'parameter_keys': KEYS,
                    'parameter_domains': DOMAINS, 'threads': 2, 'corner': 'Sky130HD TT25C1.8V',
                    'workloads': WORKLOADS, 'io_delay_ns': 0.5, 'clock_uncertainty_ns': 0.1,
                    'score': '(cell_area / baseline_cell_area) * geometric_mean(workload_energy / baseline_workload_energy)',
                    'tie_order': ['unrounded score', 'energy_ratio', 'cell_area_um2', 'candidate_index'],
                    'physical_launches_including_baseline_max': 22},
            'representatives': {'generation': 'lowest repetition index passing independent final checks in each cell',
                                'generation_period_ps': 100000, 'high_frequency_period_ps': 10000,
                                'ppa': 'best new rank-eligible candidate for each workflow; absent if none'},
            'reporting': 'All slots, failures, timeouts, interventions and preparation costs retained; no outcome replacement'}
