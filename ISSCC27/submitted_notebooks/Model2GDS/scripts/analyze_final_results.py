#!/usr/bin/env python3
"""Derive final results from accepted evidence; incomplete physical families fall back.

No EDA is executed. Old processed files are never written. Positive quantities
use one preregistered relative tie tolerance; no tolerance depends on results.
"""
import argparse
from collections import Counter
import itertools
import json
import math
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.phase1_common import canonical_bytes, sha256
from model.systolic_generic import simulate

SIZES = (2, 4, 8)
WORKLOADS = ((4, 4, 4), (8, 8, 8), (16, 16, 16), (32, 32, 32), (32, 8, 32), (32, 32, 8))
FUNCTIONAL = 'results/processed/phase2_functional_verification.json'
FINAL_PHYSICAL = 'results/processed/final_physical_metrics.json'
FINAL_SELECTION = 'results/raw/phase2/sprint/final_selection.json'
OUTPUT = 'results/processed/final_analysis.json'
PROTOCOL = 'docs/FINAL_SPRINT.md'
RELATIVE_TIE_TOLERANCE = 1e-9
LOG_MARGIN_ABSOLUTE_TOLERANCE = 1e-9
TIE_POLICY = {
    'positive_quantity_comparison': 'math.isclose(a,b,rel_tol=1e-9,abs_tol=0.0)',
    'relative_tolerance': RELATIVE_TIE_TOLERANCE,
    'absolute_tolerance': 0.0,
    'cycles_unit': 'rising_clock_edges_including_tile_clear',
    'implementation_latency_unit': 'ns',
    'winner_set': 'Every configuration numerically tied with the minimum; sorted by array size.',
    'top1_agreement': 'Identical unique winners count toward agreement/6; any multiwinner set is explicitly indeterminate.',
    'pairwise': 'If either layer ties, tied_or_indeterminate; otherwise equal order is preserved and opposite order reversed.',
    'logarithm': 'natural',
    'margin_change_absolute_tolerance': LOG_MARGIN_ABSOLUTE_TOLERANCE,
    'margin_change_tolerance_unit': 'dimensionless natural-log ratio',
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def positive(value, label):
    require(type(value) in (int, float) and math.isfinite(value) and value > 0,
            'Expected a finite positive quantity: ' + label)
    return value


def source(root, relative):
    require(isinstance(relative, str) and not Path(relative).is_absolute()
            and '..' not in Path(relative).parts, 'Source must be repository-relative')
    path = Path(root) / relative
    require(path.is_file() and not path.is_symlink(), 'Missing/nonordinary source: ' + relative)
    return {'path': relative, 'sha256': sha256(path), 'bytes': path.stat().st_size}


def read(root, relative):
    def constant(value):
        raise ValueError('Nonfinite JSON literal: ' + value)
    return json.loads((Path(root) / relative).read_text(encoding='utf-8'), parse_constant=constant)


def collect_functional(root, run):
    # Pure analysis helpers can be imported by a portable package without the
    # full historical parser dependency graph or a Git checkout.
    from scripts.collect_phase2_functional import collect
    return collect(root, run)


def layout_sources(root, physical=None):
    """Bind layout illustrations to the same accepted GDS identities."""
    if physical is None:
        counter = read(root, 'results/processed/phase0_metrics.json')
        require(counter.get('pass') is True and counter['physical_flow']['pass'] is True,
                'Counter layout requires accepted toolchain evidence')
        records = [(None, 'TINY_COUNTER_TOOLCHAIN_PROOF', counter['physical_flow']['gds'])]
    else:
        rows, reasons = accepted_family(physical)
        require(rows is not None and not reasons, 'Layout illustration requires a complete accepted final family')
        records = [(row['array_size'], 'QUALIFIED_FINAL_ARRAY', row['gds'])
                   for row in sorted(physical['configurations'], key=lambda item: item['array_size'])]
    result = []
    for size, kind, recorded in records:
        actual = source(root, recorded['path'])
        require(actual['sha256'] == recorded['sha256']
                and actual['bytes'] == recorded.get('bytes', recorded.get('size_bytes')),
                'Layout GDS identity differs from accepted evidence')
        require(actual['bytes'] > 0, 'Layout GDS must be nonempty')
        result.append({**actual, 'top_cell': Path(recorded['path']).stem,
                       'array_size': size, 'kind': kind})
    return result


def compare(a, b):
    positive(a, 'comparison a')
    positive(b, 'comparison b')
    if math.isclose(a, b, rel_tol=RELATIVE_TIE_TOLERANCE, abs_tol=0.0):
        return 0
    return -1 if a < b else 1


def winner_set(values):
    require(set(values) == set(SIZES), 'Winner set requires exactly the three authorized configurations')
    minimum = min(positive(value, 'winner quantity') for value in values.values())
    return [size for size in SIZES if compare(values[size], minimum) == 0]


def pairwise_record(a, b, cycles, latencies):
    architecture_order = compare(cycles[a], cycles[b])
    implementation_order = compare(latencies[a], latencies[b])
    category = ('tied_or_indeterminate' if not architecture_order or not implementation_order
                else 'preserved' if architecture_order == implementation_order else 'reversed')
    m_arch = math.log(cycles[a] / cycles[b])
    m_impl = math.log(latencies[a] / latencies[b])
    absolute_change = abs(m_impl) - abs(m_arch)
    if category == 'reversed':
        transformation = 'reversed'
    elif category == 'tied_or_indeterminate':
        transformation = 'tied_or_indeterminate'
    elif abs(absolute_change) <= LOG_MARGIN_ABSOLUTE_TOLERANCE:
        transformation = 'unchanged_within_tolerance'
    else:
        transformation = 'widened' if absolute_change > 0 else 'narrowed'
    return {'array_i': a, 'array_j': b, 'architecture_order': architecture_order,
        'implementation_order': implementation_order, 'decision': category,
        'M_arch': m_arch, 'M_impl': m_impl, 'margin_delta': m_impl - m_arch,
        'absolute_margin_delta': absolute_change, 'margin_transformation': transformation,
        'margin_unit': 'dimensionless natural-log ratio'}


def functional_view(functional, freeze):
    require(functional.get('pass') is True and functional.get('status') == 'PASS'
            and functional.get('errors') == [], 'Functional qualification did not pass')
    require(freeze.get('array_sizes') == list(SIZES)
            and tuple(tuple(x) for x in freeze.get('workloads', [])) == WORKLOADS,
            'Frozen configuration/workload membership changed')
    configurations = functional.get('configurations', [])
    require(len(configurations) == 3 and sorted(x.get('array_size', 0) for x in configurations) == list(SIZES),
            'Functional family must contain exactly 2,4,8')
    points, coverage, workload_cases = [], [], []
    membership = None
    input_identity = {}
    for cfg in sorted(configurations, key=lambda item: item['array_size']):
        size, cases = cfg['array_size'], cfg.get('cases', [])
        ids = [row.get('case_id') for row in cases]
        require(len(cases) == 147 and len(set(ids)) == 147, 'Functional case plan must have 147 unique cases')
        require(membership is None or membership == set(ids), 'Different functional cases across configurations')
        membership = set(ids)
        counts = Counter(row.get('category') for row in cases)
        require(dict(counts) == {'directed': 13, 'randomized': 128, 'frozen_workload_sanity': 6},
                'Required functional category coverage differs')
        for row in cases:
            require(all(row.get(key) is True for key in ('pass', 'numerical_match', 'cycle_match')),
                    'Unqualified functional case: ' + str(row.get('case_id')))
            require(size != 2 or row.get('phase1_compatibility') is True,
                    'S2 no longer agrees with accepted Phase1 evidence')
            model, rtl = row.get('model_cycles'), row.get('rtl_cycles')
            require(type(model) is int and type(rtl) is int and model == rtl and model > 0,
                    'Functional cycle disagreement/invalid integer')
            require(row.get('array_size') == size, 'Case configuration mismatch')
            require(row.get('cycle_unit') == TIE_POLICY['cycles_unit'], 'Cycle convention changed')
            identity = (row.get('input_sha256'), row.get('M'), row.get('N'), row.get('K'))
            require(row['case_id'] not in input_identity or input_identity[row['case_id']] == identity,
                    'Functional input identity differs across array sizes')
            input_identity[row['case_id']] = identity
            point = {key: row[key] for key in ('case_id', 'category', 'M', 'N', 'K',
                'array_size', 'model_cycles', 'rtl_cycles', 'input_sha256', 'cycle_unit', 'raw_sources')}
            points.append(point)
            if row['category'] == 'frozen_workload_sanity':
                require(re.fullmatch(r'W[1-6]', row['case_id']) is not None, 'Unexpected research workload ID')
                index = int(row['case_id'][1:]) - 1
                require((row['M'], row['N'], row['K']) == WORKLOADS[index], 'Frozen workload dimensions changed')
                workload_cases.append(point)
        summary = cfg.get('summary', {})
        require(all(summary.get(key) == len(cases) for key in ('case_count', 'numerical_passed', 'cycle_passed', 'passed')),
                'Functional summary differs from case records')
        coverage.append({'array_size': size, 'case_count': len(cases), 'category_counts': dict(sorted(counts.items())),
            'numerical_passed': sum(row['numerical_match'] for row in cases),
            'cycle_passed': sum(row['cycle_match'] for row in cases),
            'phase1_compatibility_passed': sum(row['phase1_compatibility'] is True for row in cases) if size == 2 else None})
    require(len(workload_cases) == 18, 'Exactly six frozen workloads per configuration are required')
    return {'run_id': functional['run_id'], 'accepted_array_sizes': list(SIZES),
        'total_case_executions': len(points), 'coverage': coverage, 'cycle_points': points,
        'frozen_workload_cases': sorted(workload_cases, key=lambda row: (row['case_id'], row['array_size'])),
        'meaning': 'Functional verification observations; verification cases do not expand the six research workloads.'}


def accepted_family(physical):
    """Incomplete/rejected families expose no performance values to analysis."""
    if physical is None:
        return None, ['No final physical collector output is available']
    if physical.get('pass') is not True or physical.get('status') != 'PASS':
        return None, ['Final physical family is not qualified; individual or rejected results are excluded']
    if physical.get('purpose') != 'FINAL':
        return None, ['Development qualification is not final comparative evidence']
    require(physical.get('errors') == [], 'A PASS final family still contains parser errors')
    family = physical.get('family')
    require(family in ('FINAL_001', 'FINAL_002'), 'Unrecognized final family')
    rows = physical.get('configurations', [])
    require(len(rows) == 3 and sorted(row.get('array_size', 0) for row in rows) == list(SIZES),
            'PASS physical family has missing/duplicate/unauthorized configurations')
    for row in rows:
        require(row.get('pass') is True and row.get('status') == 'PASS', 'Unaccepted configuration in PASS family')
        require(row.get('run_id') == family, 'Mixed or nonfinal run IDs')
        require(row.get('qualification') == 'QUALIFIED_FINAL', 'Only explicitly qualified final runs may be analyzed')
        require(row.get('run_path') == f'results/raw/phase2/sprint/physical/cfg_{row["array_size"]}x{row["array_size"]}/{family}',
                'Run path does not identify the selected final family')
    expected_paths = [row['run_path'] for row in sorted(rows, key=lambda item: item['array_size'])]
    require(physical.get('accepted_physical_runs') == expected_paths, 'Accepted-run list differs from full final family')
    for key in ('freeze_commit', 'recipe_sha256', 'resolved_recipe_sha256'):
        values = {row.get(key) for row in rows}
        require(len(values) == 1 and None not in values and '' not in values, 'Physical family differs in ' + key)
    normalized = []
    for row in sorted(rows, key=lambda item: item['array_size']):
        timing, area = row['timing'], row['area']
        require(timing.get('corner') == 'max_ss_100C_1v60', 'Physical timing corner differs from frozen method')
        frequency, period = timing['sta_frequency'], timing['sta_period']
        require(frequency.get('term') == 'post-route fixed-layout STA-derived frequency estimate',
                'Physical frequency terminology/method differs')
        require(frequency['units'] == 'MHz' and period['units'] == 'ns', 'Timing units must be explicit MHz/ns')
        f = positive(frequency['value'], 'STA-derived frequency estimate')
        p = positive(period['value'], 'STA-derived period estimate')
        require(math.isclose(f * p, 1000.0, rel_tol=1e-12), 'Period/frequency derivation mismatch')
        cell, core = area['design__instance__area'], area['design__core__area']
        require(cell['units'] == core['units'] == 'um^2', 'Expected square-micrometre area units')
        normalized.append({'array_size': row['array_size'], 'run_id': row['run_id'],
            'freeze_commit': row['freeze_commit'], 'recipe_sha256': row['recipe_sha256'],
            'resolved_recipe_sha256': row['resolved_recipe_sha256'],
            'sta_frequency_MHz': f, 'sta_period_ns': p,
            'cell_area_um2': positive(cell['value'], 'cell area'), 'core_area_um2': positive(core['value'], 'core area'),
            'frequency_terminology': frequency['term'],
            'raw_provenance': {'timing': timing, 'cell_area': cell, 'core_area': core}})
    return normalized, []


def physical_attempt_history(physical):
    """Retain collector-derived attempt/correction identity, never performance."""
    if physical is None:
        return None
    result = {key: physical.get(key) for key in ('family', 'purpose', 'status', 'pass', 'selection')}
    if 'supersedes_selection' in physical:
        result['supersedes_selection'] = physical['supersedes_selection']
    if isinstance(physical.get('correction'), dict):
        result['correction'] = {key: physical['correction'].get(key) for key in ('reason', 'source')}
    return result


def scientific_view(functional, physical_rows):
    configurations = {row['array_size']: row for row in physical_rows}
    workloads, pairs = [], []
    for index, dimensions in enumerate(WORKLOADS, 1):
        wid = 'W' + str(index)
        selected = {row['array_size']: row for row in functional['frozen_workload_cases'] if row['case_id'] == wid}
        require(set(selected) == set(SIZES), 'Missing workload/configuration observations')
        cycles = {size: selected[size]['model_cycles'] for size in SIZES}
        latencies = {size: selected[size]['rtl_cycles'] * 1000.0 / configurations[size]['sta_frequency_MHz'] for size in SIZES}
        arch_winners, impl_winners = winner_set(cycles), winner_set(latencies)
        top1 = ('tied_or_indeterminate' if len(arch_winners) != 1 or len(impl_winners) != 1
                else 'agreement' if arch_winners == impl_winners else 'disagreement')
        workloads.append({'workload_id': wid, 'M': dimensions[0], 'N': dimensions[1], 'K': dimensions[2],
            'configurations': [{'array_size': size, 'model_cycles': cycles[size], 'rtl_cycles': selected[size]['rtl_cycles'],
                'implementation_latency_ns': latencies[size]} for size in SIZES],
            'architecture_winner_set': arch_winners, 'implementation_winner_set': impl_winners,
            'top1': top1, 'winner_set_exact_agreement': arch_winners == impl_winners})
        pairs.extend({'workload_id': wid, **pairwise_record(a, b, cycles, latencies)} for a, b in itertools.combinations(SIZES, 2))
    top_counts = Counter(row['top1'] for row in workloads)
    pair_counts = Counter(row['decision'] for row in pairs)
    return {'status': 'COMPUTED_FROM_ACCEPTED_FINAL_FAMILY', 'configurations': physical_rows,
        'latency_equation': 'T_impl_ns = C_rtl * 1000 / F_sta_MHz',
        'workloads': workloads, 'top1': {'agreement_count': top_counts['agreement'], 'total_workloads': len(workloads),
            'disagreement_count': top_counts['disagreement'], 'tied_or_indeterminate_count': top_counts['tied_or_indeterminate']},
        'pairwise': {'total_decisions': len(pairs), 'preserved': pair_counts['preserved'],
            'tied_or_indeterminate': pair_counts['tied_or_indeterminate'], 'reversed': pair_counts['reversed'], 'decisions': pairs},
        'limitations': ['Only the six frozen workloads and three configured arrays under one qualified recipe are evaluated.',
            'STA-derived frequency is a fixed-layout estimate, not measured silicon Fmax.',
            'No power/energy claim or process-variation inference is made.',
            'Zero observed reversals would not establish general architecture-model reliability.']}


def analyze(root=ROOT, *, physical_output=FINAL_PHYSICAL, selection_path=FINAL_SELECTION):
    root = Path(root).resolve()
    require((root / PROTOCOL).is_file(), 'The analysis/tie protocol must exist before final analysis')
    freeze = read(root, 'PROJECT_FREEZE.json')
    selected = read(root, 'results/raw/phase2/functional_selection.json')
    run_id = selected.get('run_id')
    require(isinstance(run_id, str) and re.fullmatch(r'[A-Za-z0-9_]+', run_id), 'Invalid functional selection')
    run = root / 'results/raw/phase2/functional' / run_id
    functional = collect_functional(root, run)
    require(canonical_bytes(functional) == (root / FUNCTIONAL).read_bytes(), 'Functional processed bytes do not reproduce')
    view = functional_view(functional, freeze)
    physical, physical_sources = None, []
    if (root / physical_output).exists():
        from scripts.collect_final_physical import collect
        require((root / selection_path).is_file(), 'Final metrics exist without their selection')
        physical = collect(root, selection_path)
        require(canonical_bytes(physical) == (root / physical_output).read_bytes(), 'Final physical processed bytes do not reproduce')
        physical_sources = [source(root, physical_output), source(root, selection_path), source(root, 'scripts/collect_final_physical.py')]
    rows, blocked = accepted_family(physical)
    layouts = layout_sources(root, physical if rows else None)
    vector_path = 'results/raw/phase2/functional/' + run_id + '/phase1_oracles/vectors.json'
    vectors = read(root, vector_path)['cases']
    example = next(row for row in vectors if row['case_id'] == 'D_POSITIVE')
    trace = simulate(example['A'], example['B'], 2, trace=True)
    reference_path = 'results/raw/phase2/functional/' + run_id + '/S2/reference.json'
    ref = next(row for row in read(root, reference_path)['cases'] if row['case_id'] == 'D_POSITIVE')
    require({key: value for key, value in trace.items() if key != 'trace'} == ref['model'] and trace['C'] == ref['golden'],
            'Illustrative trace differs from accepted model/golden evidence')
    sources = [source(root, relative) for relative in (FUNCTIONAL, 'PROJECT_FREEZE.json',
        'results/raw/phase2/functional_selection.json', PROTOCOL, 'docs/EXPERIMENT_PROTOCOL.md',
        'docs/PHASE2_TIMING_METHODOLOGY.md', 'docs/PHASE2_FUNCTIONAL_CONTRACT.md',
        'scripts/analyze_final_results.py', 'model/systolic_generic.py', vector_path, reference_path)]
    return {'schema_version': 1, 'status': 'PASS', 'analysis_mode': 'PRIMARY_RESEARCH' if rows else 'EDUCATIONAL_FALLBACK',
        'tie_policy': TIE_POLICY, 'functional': view,
        'wavefront_example': {'case_id': example['case_id'], 'source': vector_path,
            'meaning': 'Explanatory trace regenerated from accepted input and unchanged token model; not a new benchmark or physical result.',
            'A': example['A'], 'B': example['B'], **trace},
        'scientific_analysis': scientific_view(view, rows) if rows else None,
        'scientific_analysis_unavailable_reasons': blocked,
        'physical_attempt_history': physical_attempt_history(physical),
        'layout_sources': layouts,
        'rejected_physical_performance_used': False,
        'sources': sources + physical_sources + [
            {key: item[key] for key in ('path', 'sha256', 'bytes')} for item in layouts]
            + ([] if rows else [source(root, 'results/processed/phase0_metrics.json')])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--physical-output', default=FINAL_PHYSICAL)
    parser.add_argument('--selection', default=FINAL_SELECTION)
    parser.add_argument('--output', default=OUTPUT)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    root = args.root.resolve()
    require(args.output == OUTPUT, 'Only the new final-analysis output is writable')
    result = analyze(root, physical_output=args.physical_output, selection_path=args.selection)
    expected = canonical_bytes(result)
    path = root / args.output
    if args.check or path.exists():
        require(path.read_bytes() == expected, 'Final analysis bytes do not reproduce')
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(expected)
    print(canonical_bytes({'status': 'PASS', 'analysis_mode': result['analysis_mode'],
        'output': source(root, args.output), 'meaning': 'Analysis/byte reproduction; scientific results exist only in PRIMARY_RESEARCH mode'}).decode(), end='')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
