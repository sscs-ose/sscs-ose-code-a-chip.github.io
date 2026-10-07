#!/usr/bin/env python3
"""Build and verify the portable Code-a-Chip candidate; never execute EDA.

The research branch exists only for a complete, accepted FINAL family.
Package verification replays Python models against captured RTL observations;
it does not describe that replay as a fresh RTL simulation or physical run.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib.util
from importlib.metadata import version
import json
import math
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = 'ISSCC27/submitted_notebooks/Model2GDS'
PACKAGE_ATTRIBUTES = '* -text\n'
ANALYSIS = 'results/processed/final_analysis.json'
FUNCTIONAL = 'results/processed/phase2_functional_verification.json'
PHASE0 = 'results/processed/phase0_metrics.json'
LICENSE_EVIDENCE = 'results/raw/phase2/sprint/SUBMISSION_LICENSE_001'
FULL_TITLE = 'Model2GDS: A Reproducible Decision-Fidelity Audit of GEMM Accelerator Models with Open-Source RTL-to-GDS Tools'
FALLBACK_TITLE = 'Model2GDS: An Auditable Model-to-RTL Workflow for Reproducible Systolic-Array Design'
OFFICIAL_COMMIT = 'a502a6ba01260d3492df9137dddae0bb5fabeb3c'
OFFICIAL_BASE = 'https://github.com/sscs-ose/sscs-ose-code-a-chip.github.io/blob/' + OFFICIAL_COMMIT + '/'
RULES = {
    'schema_version': 1, 'checked_date': '2026-10-07',
    'official_repository_commit': OFFICIAL_COMMIT,
    'official_commit_date': '2026-10-06T07:00:07Z',
    'sources': [
        {'url': OFFICIAL_BASE + 'README.md', 'bytes': 8004,
         'sha256': 'df0d6f0a00b9b45e53f90027b112e345bfcfbbbb2ec273f23c5a8963e21e10f3'},
        {'url': OFFICIAL_BASE + 'howtoapply.md', 'bytes': 1579,
         'sha256': '1c62abbb8b6527934a0b0fb4dc058dec0fce49096d26e14734c08f96c220f599'},
    ],
    'current_readme_deadline': '2026-10-31 11:59 AM Pacific Time',
    'internal_conservative_planning_deadline': '2026-10-09 11:59 AM Pacific Time',
    'year_specific_conflict': 'Pinned howtoapply.md still refers to ISSCC26 and November 27, 2025. The current README identifies the ISSCC27 directory. Historical project planning is not rewritten.',
    'deadline_issue': {'url': 'https://github.com/sscs-ose/sscs-ose-code-a-chip.github.io/issues/194',
                       'observed_state': 'OPEN', 'checked_date': '2026-10-07'},
    'requirements': [
        'Openly licensed Jupyter notebook about circuit design or an educational project using open-source tools and applicable open-source PDKs.',
        'Explain ideas, design decisions, methodology, results and reproduction.',
        'A final circuit layout is encouraged, not required by the current README.',
        'The local-OpenLane FAQ requests the resulting layout image, relevant output and an explanation of the flow.',
        'All project files, license and supporting files belong inside ISSCC27/submitted_notebooks/<project_name> in a fork and pull request.',
        'The application guide asks for team members at the notebook top, references for reused material, and recommended tool versions.',
        'A team designates a representative for the award and conference attendance.',
    ],
    'eligibility_or_acceptance_guaranteed': False,
    'submission_action': 'LOCAL_CANDIDATE_ONLY_NO_PULL_REQUEST',
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def canonical(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False, ensure_ascii=False) + '\n').encode('utf-8')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'),
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Nonfinite JSON: ' + value)))


def safe_path(root, relative):
    require(isinstance(relative, str) and relative and '\\' not in relative, 'Noncanonical package path')
    path = PurePosixPath(relative)
    require(not path.is_absolute() and ':' not in relative and '..' not in path.parts
            and path.as_posix() == relative, 'Unsafe package path: ' + relative)
    root = Path(root).resolve()
    full = root.joinpath(*path.parts)
    require(not any((root.joinpath(*path.parts[:i])).is_symlink() for i in range(1, len(path.parts)+1)),
            'Symlink in package path: ' + relative)
    require(full.resolve().is_relative_to(root), 'Path escaped package')
    return full


def descriptor(root, relative):
    path = safe_path(root, relative)
    require(path.is_file(), 'Missing package source: ' + relative)
    data = path.read_bytes()
    return {'path': relative, 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}


def verify_sources(root, sources):
    seen = {}
    for source in sources:
        actual = descriptor(root, source['path'])
        expected = {'path': source['path'], 'sha256': source['sha256'],
                    'bytes': source.get('bytes', source.get('size_bytes'))}
        require(type(expected['bytes']) is int and actual == expected, 'Source bytes differ: ' + source['path'])
        require(source['path'] not in seen or seen[source['path']] == expected, 'Conflicting source identity')
        seen[source['path']] = expected
    return sorted(seen.values(), key=lambda item: item['path'])


def load_module(root, relative, name):
    path = safe_path(root, relative)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(Path(root).resolve()))
    spec.loader.exec_module(module)
    return module


def validate_analysis(analysis, functional, frozen):
    require(analysis.get('schema_version') == 1 and analysis.get('status') == 'PASS', 'Analysis is not complete')
    require(functional.get('pass') is True and functional.get('status') == 'PASS'
            and functional.get('errors') == [], 'Functional evidence is not accepted')
    require(frozen.get('array_sizes') == [2, 4, 8], 'Configuration scope differs')
    configs = functional.get('configurations', [])
    require([c.get('array_size') for c in configs] == frozen['array_sizes'], 'Functional family differs')
    total = 0
    for cfg in configs:
        cases = cfg['cases']
        require(cases and len({c['case_id'] for c in cases}) == len(cases), 'Empty or duplicate functional cases')
        require(all(c.get('pass') is True and c.get('numerical_match') is True and c.get('cycle_match') is True
                    and c['model_cycles'] == c['rtl_cycles'] for c in cases), 'Functional comparison failed')
        computed = {'case_count': len(cases), 'passed': sum(c['pass'] for c in cases),
                    'numerical_passed': sum(c['numerical_match'] for c in cases),
                    'cycle_passed': sum(c['cycle_match'] for c in cases)}
        require(all(cfg['summary'].get(k) == v for k, v in computed.items()), 'Manually altered functional count')
        require(dict(Counter(c['category'] for c in cases)) == cfg['summary']['category_counts'], 'Category count differs')
        total += len(cases)
    require(analysis['functional']['total_case_executions'] == total, 'Analysis verification total differs')
    require(analysis.get('rejected_physical_performance_used') is False, 'Rejected physical performance was promoted')
    mode = analysis.get('analysis_mode')
    require(mode in ('PRIMARY_RESEARCH', 'EDUCATIONAL_FALLBACK'), 'Unknown submission branch')
    science = analysis.get('scientific_analysis')
    if mode == 'EDUCATIONAL_FALLBACK':
        require(science is None, 'Fallback must contain no scientific physical comparison')
    else:
        require(isinstance(science, dict) and science.get('status') == 'COMPUTED_FROM_ACCEPTED_FINAL_FAMILY',
                'Research branch lacks accepted-family analysis')
        rows = science['configurations']
        require([r['array_size'] for r in rows] == [2, 4, 8], 'Research family incomplete')
        require(all(re.fullmatch(r'FINAL_[A-Za-z0-9_]+', r['run_id']) for r in rows), 'Development/rejected run promoted')
        for key in ('freeze_commit', 'recipe_sha256', 'resolved_recipe_sha256'):
            require(len({r[key] for r in rows}) == 1 and all(r[key] for r in rows), 'Unmatched physical ' + key)
        require(len(science['workloads']) == len(frozen['workloads'])
                and science['pairwise']['total_decisions'] == len(frozen['workloads']) * 3,
                'Incomplete research decisions')
    return total


def verify_receipt(root, relative):
    receipt = read(safe_path(root, relative))
    require(type(receipt.get('returncode')) is int and receipt['returncode'] == 0, 'Failed accepted command: ' + relative)
    for stream in ('stdout', 'stderr'):
        if stream in receipt:
            require(descriptor(root, receipt[stream])['sha256'] == receipt[stream + '_sha256'], 'Changed command stream')
    if 'log' in receipt:
        require(descriptor(root, receipt['log'])['sha256'] == receipt['log_sha256'], 'Changed command log')
    return receipt


def replay_functional(root):
    """Recompute from preserved inputs, without launching compiled code or EDA."""
    root = Path(root).resolve()
    sys.path.insert(0, str(root))
    from model.golden import gemm
    from model.systolic_generic import simulate
    functional = read(root / FUNCTIONAL)
    verify_sources(root, functional['raw_sources'])
    run = 'results/raw/phase2/functional/' + functional['run_id']
    source_manifest = read(root / run / 'source_manifest.json')
    for source in source_manifest['files']:
        snapshot = descriptor(root, run + '/' + source['snapshot'])
        require(snapshot['sha256'] == source['sha256'] and snapshot['bytes'] == source['bytes'], 'Functional snapshot changed')
        # Original source copies are carried for all runnable model/RTL inputs.
        if source['path'].startswith(('model/', 'rtl/')):
            require(descriptor(root, source['path'])['sha256'] == source['sha256'], 'Model/RTL differs from captured source')
    vectors = read(root / run / 'phase1_oracles/vectors.json')['cases']
    require(len({v['case_id'] for v in vectors}) == len(vectors), 'Duplicate input cases')
    golden = {v['case_id']: gemm(v['A'], v['B']) for v in vectors}
    rows = []
    for cfg in functional['configurations']:
        size = cfg['array_size']
        prefix = run + '/S' + str(size)
        verify_receipt(root, prefix + '/compile.command.json')
        verify_receipt(root, prefix + '/execute.command.json')
        references = read(root / prefix / 'reference.json')['cases']
        observed = [json.loads(line) for line in (root / prefix / 'rtl_results.jsonl').read_text().splitlines() if line.strip()]
        ref = {c['case_id']: c for c in references}
        rtl = {c['case_id']: c for c in observed}
        processed = {c['case_id']: c for c in cfg['cases']}
        require(len(ref) == len(references) and len(rtl) == len(observed)
                and set(ref) == set(rtl) == set(golden) == set(processed), 'Case membership differs')
        for vector in vectors:
            case_id = vector['case_id']
            model = simulate(vector['A'], vector['B'], size)
            recorded = rtl[case_id]
            require(model == ref[case_id]['model'], 'Token model regeneration differs: ' + case_id)
            require(model['C'] == ref[case_id]['golden'] == recorded['C'] == golden[case_id], 'Numerical result differs: ' + case_id)
            require(recorded['array_size'] == size and recorded['cycles'] == model['cycles']
                    and recorded['tiles'] == model['tiles'], 'RTL cycle/tile observation differs: ' + case_id)
            require(processed[case_id]['rtl_cycles'] == recorded['cycles']
                    and processed[case_id]['model_cycles'] == model['cycles'], 'Processed cycles differ')
        rows.append({'array_size': size, 'cases': len(vectors), 'numerical_passed': len(vectors), 'cycle_passed': len(vectors)})
    return {'status': 'PASS', 'kind': 'OFFLINE_MODEL_REPLAY_AGAINST_CAPTURED_RTL',
            'fresh_rtl_simulation': False, 'configurations': rows, 'total_cases': sum(x['cases'] for x in rows)}


def reparse_primary_quantities(root, physical, parser=None):
    """Re-derive displayed quantities from full reports, not cached scalars.

This portable check supplements hash preservation; the complete historical
qualification (including pre-run Git state) is still the full-repository task.
"""
    if parser is None:
        parser = load_module(root, 'scripts/collect_phase2_physical.py', '_submission_physical_quantities')
    if (Path(root) / 'support/physical_evidence_inventory.json').is_file():
        inventory = read(Path(root) / 'support/physical_evidence_inventory.json')
        require(inventory == primary_payload(root, physical), 'Portable physical inventory does not reproduce')
        sources = {s['path']: s for s in physical['raw_sources']}
        included = inventory['included']
        require(all(s['path'] in sources and s['sha256'] == sources[s['path']]['sha256'] for s in included),
                'Physical evidence inventory differs from original collector provenance')
        verify_sources(root, included)
    else:
        verify_sources(root, physical['raw_sources'])
    for cfg in physical['configurations']:
        timing = cfg['timing']
        require(timing['corner'] == 'max_ss_100C_1v60', 'Unexpected primary timing corner')
        period_source = timing['constraint_period']
        config = json.loads(safe_path(root, period_source['source']).read_text(encoding='utf-8'))
        period = parser.finite(config[period_source['source_key']], 'constraint period')
        require(period_source['units'] == 'ns' and period == period_source['value'] == 20.0,
                'Timing constraint differs from source')
        slack_source = timing['setup_worst_slack']
        text = safe_path(root, slack_source['source']).read_text(encoding='utf-8')
        parsed = parser.parse_r2r_report(text, timing['corner'], period)
        require(slack_source['units'] == 'ns' and parsed['worst_slack_ns'] == slack_source['value']
                and parsed['path_count'] == timing['internal_path_count'], 'Derived setup quantity differs from full report')
        p, f = parser.derive_frequency(period, parsed['worst_slack_ns'])
        require(timing['sta_period']['units'] == 'ns' and timing['sta_period']['value'] == p
                and timing['sta_frequency']['units'] == 'MHz' and timing['sta_frequency']['value'] == f,
                'Derived period/frequency differs from raw timing')
        for group in ('area', 'signoff', 'post_route_hold'):
            for name, item in cfg[group].items():
                native = json.loads(safe_path(root, item['source']).read_text(encoding='utf-8'))
                value = parser.finite(native['metrics'][item['source_key']], name)
                require(value == item['value'], 'Processed quantity differs from raw source: ' + name)
                if group == 'area':
                    require(item['units'] == 'um^2' and value > 0, 'Invalid physical area')
                elif group == 'signoff' or 'vio__count' in name:
                    require(item['units'] == 'count' and value == 0, 'Physical signoff blocker remains')
                else:
                    require(item['units'] == 'ns' and value >= 0, 'Physical hold failure remains')
        require(set(parser.ZERO_KEYS) <= set(cfg['signoff']), 'Incomplete signoff provenance')
        require(cfg['post_route_hold'], 'Missing post-route hold provenance')
    return {'status': 'PASS', 'kind': 'RAW_REPORT_QUANTITY_REPARSE', 'fresh_physical_run': False}


def primary_payload(root, physical):
    """Select complete metric authorities, excluding bulk flow intermediates."""
    all_sources = {source['path']: source for source in physical['raw_sources']}
    required = set()
    for cfg in physical['configurations']:
        required.update(item['source'] for group in ('area', 'signoff', 'post_route_hold') for item in cfg[group].values())
        required.update(cfg['timing'][name]['source'] for name in ('setup_worst_slack', 'constraint_period'))
        for name in ('resolved_config', 'final_state', 'post_route_state', 'sta_environment', 'netlist', 'sdc',
                     'spef', 'r2r_report', 'structural_report', 'mapped_report'):
            require(name in cfg['artifacts'], 'Missing portable metric authority: ' + name)
            required.add(cfg['artifacts'][name]['path'])
        # The actual layout is required for portable figure regeneration.
        required.add(cfg['gds']['path'])
        required.add(cfg['source_manifest']['path'])
        manifest_path = cfg['run_path'] + '/manifest.json'
        require(manifest_path in all_sources, 'Missing original physical run manifest')
        required.add(manifest_path)
        manifest = read(safe_path(root, manifest_path))
        for command_path in manifest['commands'].values():
            require(command_path in all_sources, 'Command absent from collector provenance')
            required.add(command_path)
            receipt = read(safe_path(root, command_path))
            require(type(receipt.get('returncode')) is int and receipt['returncode'] == 0, 'Failed primary physical command')
            for stream in ('stdout', 'stderr'):
                require(receipt[stream] in all_sources, 'Command stream absent from physical provenance')
                required.add(receipt[stream])
        if isinstance(manifest.get('freeze'), dict):
            required.add(manifest['freeze']['path'])
        if manifest.get('outer_receipt'):
            required.add(manifest['outer_receipt'])
            outer = read(safe_path(root, manifest['outer_receipt']))
            require(type(outer.get('returncode')) is int and outer['returncode'] == 0, 'Failed outer physical command')
            required.update(outer[stream] for stream in ('stdout', 'stderr'))
        recipes = {path for path, source in all_sources.items() if source['sha256'] == cfg['recipe_sha256']}
        require(recipes, 'Original accepted recipe source missing')
        required.update(recipes)
    require(required <= set(all_sources), 'Portable authority absent from original physical provenance')
    included = verify_sources(root, [all_sources[path] for path in sorted(required)])
    omitted = [source for path, source in sorted(all_sources.items()) if path not in required]
    return {'schema_version': 1, 'included': included, 'not_bundled': omitted,
            'meaning': 'All displayed timing/area/signoff authorities and routed netlist/SPEF/SDC/environment are bundled. '
                       'All accepted final GDS files are bundled; bulk ODB/build/intermediate data remain in the author-held full archive. '
                       'Original processed provenance is unchanged; portable replay does not requalify historical Git state.'}


def electrical_warnings(root, physical):
    """Display informational native electrical counts without changing gates."""
    records = []
    for cfg in physical['configurations']:
        require(str(cfg['run_id']).startswith('FINAL_') and cfg.get('pass') is True,
                'Electrical disclosure requires accepted final data')
        source = cfg['artifacts']['final_state']
        verify_sources(root, [source])
        metrics = json.loads(safe_path(root, source['path']).read_text(encoding='utf-8'))['metrics']
        values = []
        for key, value in sorted(metrics.items()):
            if not re.fullmatch(r'design__max_(?:slew|fanout|cap)_violation__count(?:__corner:.+)?', key):
                continue
            require(type(value) in (int, float) and math.isfinite(value) and value >= 0 and int(value) == value,
                    'Malformed native electrical count: ' + key)
            values.append({'value': value, 'units': 'count', 'source': source['path'], 'source_key': key})
        records.append({'array_size': cfg['array_size'], 'run_id': cfg['run_id'], 'counts': values,
                        'nonzero_counts_present': any(item['value'] > 0 for item in values)})
    return {'schema_version': 1, 'qualification_gate_changed': False,
            'warnings_present': any(row['nonzero_counts_present'] for row in records), 'configurations': records,
            'meaning': 'Native slew/fanout/capacitance violations are informational under the frozen gate. '
                       'Accepted qualification does not mean that every electrical checker reports zero.'}


def attempt_history_projection(root, analysis, *, verify_original=False, recorded_outcomes=None):
    """Keep nonnumeric attempt history without bundling rejected performance."""
    history = analysis.get('physical_attempt_history')
    if history is None:
        return None
    require(set(history) <= {'family', 'purpose', 'status', 'pass', 'selection', 'supersedes_selection', 'correction'},
            'Attempt history contains unsupported fields')
    path = 'results/processed/final_physical_metrics.json'
    sources = [item for item in analysis['sources'] if item['path'] == path]
    require(len(sources) == 1, 'Attempt history lacks a unique processed-source identity')
    outcome_keys = ('array_size', 'run_id', 'status', 'pass', 'qualification', 'failure_classification', 'error')
    if verify_original:
        verify_sources(root, sources)
        analyzer = load_module(root, 'scripts/analyze_final_results.py', '_submission_history')
        physical = read(safe_path(root, path))
        require(analyzer.physical_attempt_history(physical) == history,
                'Attempt history differs from the original processed record')
        outcomes = [{key: row.get(key) for key in outcome_keys} for row in physical['configurations']]
        require(recorded_outcomes is None or recorded_outcomes == outcomes, 'Attempt outcomes differ from original processed record')
    else:
        outcomes = recorded_outcomes
    require(isinstance(outcomes, list) and sorted(row.get('array_size', 0) for row in outcomes) == [2, 4, 8]
            and all(set(row) == set(outcome_keys) and row['status'] in ('PASS', 'FAIL', 'NOT_RUN')
                    and type(row['pass']) is bool and row['run_id'] == history['family'] for row in outcomes),
            'Malformed nonnumeric attempt outcomes')
    return {'schema_version': 1, 'history': history, 'configurations': outcomes, 'source': sources[0],
            'source_bundled': analysis['analysis_mode'] == 'PRIMARY_RESEARCH',
            'meaning': 'Nonnumeric projection checked against the original processed record during package generation. '
                       'Rejected physical-performance records remain in the author-held archive and are not bundled in fallback mode.'}


def third_party_material(root):
    """Reproduce the small GDS attribution bundle from pinned upstream captures."""
    verify_receipt(root, LICENSE_EVIDENCE + '/query.command.json')
    proof = read(root / LICENSE_EVIDENCE / 'query.stdout.log')
    require(proof['status'] == 'PASS', 'Third-party licensing source capture failed')
    verify_sources(root, [{**item, 'path': LICENSE_EVIDENCE + '/' + item['path']} for item in proof['sources']])
    lock = read(root / 'environment/toolchain.lock.json')
    require(proof['open_pdks_revision'] == lock['environment']['pdk']['observed']['revision'],
            'Third-party licensing evidence belongs to another PDK revision')
    materials = {}
    for name in ('sky130_fd_sc_hd', 'open_pdks'):
        materials['third_party/' + name + '/LICENSE'] = (root / LICENSE_EVIDENCE / (name + '_LICENSE')).read_bytes()
    header = (root / LICENSE_EVIDENCE / 'sky130_fd_sc_hd_cells__and2__sky130_fd_sc_hd__and2_1.v').read_text()
    copyright_line = re.search(r'Copyright[^\r\n]+', header).group(0)
    notice = f'''Model2GDS third-party attribution

Bundled GDS files contain SKY130 standard-cell geometry, not just project RTL.
The routed designs combine those cells with generated placement, routing and
top-level geometry. These generated/composed layouts are not unmodified PDK
source distributions. Upstream cell material retains its original licensing.

sky130_fd_sc_hd — SkyWater high-density standard cells
{copyright_line}
Revision: {proof['scl_revision_from_installed_nodeinfo']}
Apache License 2.0: third_party/sky130_fd_sc_hd/LICENSE

open_pdks — PDK processing and supporting cell material
Sky130 setup by Tim Edwards, efabless corporation (upstream Makefile attribution).
Revision: {proof['open_pdks_revision']}
Apache License 2.0: third_party/open_pdks/LICENSE

Exact upstream license/source URLs, hashes and installed revision metadata are
preserved in {LICENSE_EVIDENCE}/query.stdout.log and its captured inputs.
Project additions use the root LICENSE. This notice does not alter upstream terms.
'''
    materials['NOTICE'] = notice.encode('utf-8')
    return materials


def verify_package(root, *, replay=True):
    root = Path(root).resolve()
    manifest = read(root / 'file_manifest.json')
    verify_sources(root, manifest['files'])
    included = {x['path'] for x in manifest['files']}
    actual = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()
              and not {'__pycache__', '.ipynb_checkpoints', '.venv'} & set(p.relative_to(root).parts)
              and p != root / 'file_manifest.json'}
    require(actual == included, 'Unexpected or missing package files')
    require(all(safe_path(root, name).read_bytes() == content for name, content in third_party_material(root).items()),
            'Third-party notices/licenses differ from pinned sources')
    analysis, functional, frozen = (read(root / p) for p in (ANALYSIS, FUNCTIONAL, 'PROJECT_FREEZE.json'))
    total = validate_analysis(analysis, functional, frozen)
    verify_sources(root, functional['raw_sources'])
    p0 = load_module(root, 'scripts/collect_phase0_metrics.py', '_submission_phase0')
    regenerated, lock = p0.collect(root / 'results/raw/phase0/selection.json', root=root)
    require(regenerated == read(root / PHASE0) and regenerated['pass'] is True, 'Counter raw-output parser reproduction failed')
    require(lock == read(root / 'environment/toolchain.lock.json'), 'Tool lock reproduction differs')
    analyzer = load_module(root, 'scripts/analyze_final_results.py', '_submission_analysis')
    view = analyzer.functional_view(functional, frozen)
    require(view == analysis['functional'], 'Functional analysis differs')
    physical = None
    if analysis['analysis_mode'] == 'PRIMARY_RESEARCH':
        physical = read(root / 'results/processed/final_physical_metrics.json')
        rows, reasons = analyzer.accepted_family(physical)
        require(rows is not None and not reasons, 'Physical family no longer qualifies')
        reparse_primary_quantities(root, physical)
        require(electrical_warnings(root, physical) == read(root / 'support/electrical_warnings.json'),
                'Electrical warning disclosure differs from native final states')
        require(analyzer.scientific_view(view, rows) == analysis['scientific_analysis'], 'Scientific decisions differ')
    require(analyzer.layout_sources(root, physical) == analysis.get('layout_sources'),
            'Layout illustration sources differ from accepted evidence')
    if analysis.get('physical_attempt_history') is not None:
        recorded_history = read(root / 'support/physical_attempt_history.json')
        history = attempt_history_projection(root, analysis, verify_original=physical is not None,
                                             recorded_outcomes=recorded_history.get('configurations'))
        require(history == recorded_history, 'Attempt-history projection differs')
    replay_result = replay_functional(root) if replay else {'status': 'NOT_RUN'}
    team = read(root / 'TEAM.json')
    require(team == read(root / 'docs/submission_authors.json') and team.get('status') == 'OWNER_CONFIRMED'
            and team.get('members') and team.get('representative'), 'Owner-confirmed team identity missing')
    return {'status': 'PASS', 'analysis_mode': analysis['analysis_mode'], 'files_verified': len(included),
            'functional_case_executions': total, 'counter_raw_parser': 'PASS', 'functional_replay': replay_result,
            'team_identity': 'OWNER_CONFIRMED', 'public_submission': 'NOT_SUBMITTED'}


def cell(kind, source):
    result = {'cell_type': kind, 'metadata': {}, 'source': source.strip() + '\n'}
    if kind == 'code':
        result.update(execution_count=None, outputs=[])
    return result


def notebook(analysis, team=None):
    primary = analysis['analysis_mode'] == 'PRIMARY_RESEARCH'
    title = FULL_TITLE if primary else FALLBACK_TITLE
    total = analysis['functional']['total_case_executions']
    author_line = ('owner-confirmed names, affiliations and representative are pending. No placeholder identity is presented as an author. See `TEAM.json` before any public submission.'
                   if team is None else '; '.join(
                       f"{p['name_romanized']} — {p['affiliation_en']} — {p['email']}"
                       if p.get('affiliation_en') else
                       f"{p['name']} ({p['name_romanized']}) — {p['affiliation']} — {p['email']}"
                       for p in team['members'])
                   + '. Representative: ' + team['representative'] + '.')
    cells = [cell('markdown', f'''# {title}

**Team:** {author_line}

**An executable design and reproducibility notebook · Apache-2.0 · Python + SystemVerilog**

Explore a parameterized **2×2 / 4×4 / 8×8 output-stationary systolic array** through independent numerical and token-cycle models, reusable RTL, and preserved verification evidence. The systolic architecture is established practice; this notebook makes its arithmetic, cycle semantics and reproducibility inspectable and executable.

The accepted functional corpus contains **{total} case/configuration executions**, with exact numerical and cycle agreement. Follow the chain **raw evidence → parser → structured result → figure**, then replay the checks from captured inputs and RTL outputs. A separate tiny-counter design demonstrates the open-source RTL-to-GDS toolchain. Notebook execution replays preserved evidence; it does not launch a new simulator or physical flow.'''),
        cell('markdown', '''## 1. Start here: a portable, offline experiment

Run cells in order using Python 3.12, the tested interpreter for the pinned notebook dependencies. The first cell locates the package, verifies every bundled file and loads only preserved data. No network access, proprietary tool, Docker daemon or PDK download is required for this notebook. `python scripts/build_submission.py --verify-package` performs the same data verification from a terminal.

Commands inside original raw receipts preserve the actual historical machines. They are evidence, not local path dependencies. Fresh RTL and physical reruns are separate operations described in `README.md`.'''),
        cell('code', '''from pathlib import Path
import json, sys
from html import escape
from IPython.display import display, Markdown, Image, HTML

def show_details(title, data):
    display(HTML('<details><summary>' + escape(title) + '</summary><pre>'
                 + escape(json.dumps(data, indent=2, ensure_ascii=False)) + '</pre></details>'))

start = Path.cwd().resolve()
base = next((p for p in (start, *start.parents) if (p / 'PROJECT_FREEZE.json').is_file()), None)
assert base is not None, 'Run inside the package or repository'
ROOT = base if (base / 'file_manifest.json').is_file() else base / 'ISSCC27/submitted_notebooks/Model2GDS'
assert (ROOT / 'file_manifest.json').is_file(), 'Build the verified portable candidate first'
sys.path.insert(0, str(ROOT))
from scripts.build_submission import verify_package, replay_functional
integrity = verify_package(ROOT, replay=False)
analysis = json.loads((ROOT / 'results/processed/final_analysis.json').read_text())
functional = json.loads((ROOT / 'results/processed/phase2_functional_verification.json').read_text())
frozen = json.loads((ROOT / 'PROJECT_FREEZE.json').read_text())
display(Markdown(f"**Package verification: {integrity['status']}.** Bundled source and evidence hashes were checked before loading the results."))
show_details('Package verification details', integrity)'''),
        cell('markdown', '''## 2. What the hardware computes

For `A[M,K]` and `B[K,N]`, the numerical reference computes `C=A×B`. Inputs are signed INT8; each PE sign-extends its product and accumulates in signed INT32 with modulo-2³² wrap. Reset and clear have explicit priority. This compute core deliberately omits SRAM, DMA, caches and an application processor.

One generic RTL module instantiates S×S real registered PEs, for S in {2,4,8}. A propagates right, B downward, and each accumulator remains stationary. The boundary injects lane `i`/`j` with the appropriate skew; valid/last flags travel with each token. All registers sample their old neighbors on each rising edge.

Every output tile begins with one counted clear edge. Completion comes from the active PEs' sticky result-valid flags, including the last MAC edge. Ragged tiles use an active mask. Tiles execute sequentially with no hidden inter-tile edge or overlap. The independent token model observes its own completion; a closed-form latency never tells RTL when to finish.'''),
        cell('code', '''workload_table = '| Workload | M | N | K |\\n|---|---:|---:|---:|\\n'
for index, (M, N, K) in enumerate(frozen['workloads'], start=1):
    workload_table += f'| {index} | {M} | {N} | {K} |\\n'
display(Markdown('**Pre-registered workloads.** The dimensions below are read directly from `PROJECT_FREEZE.json`; each shape is evaluated on every declared array size.'))
display(Markdown(workload_table))'''),
        cell('code', '''from model.golden import gemm
from model.systolic_generic import simulate
example = analysis['wavefront_example']
A, B, S = example['A'], example['B'], example['array_size']
golden = gemm(A, B)
observed_model = simulate(A, B, S, trace=True)
assert golden == observed_model['C'] == example['C']
assert observed_model['trace'] == example['trace']
print('Preserved directed case:', example['case_id'])
print('A =', A, '\\nB =', B, '\\nC =', golden)
print('Counted rising edges:', observed_model['cycles'])
display(Image(filename=str(ROOT / 'figures/final/token_wavefront.png'),
              alt='Registered A and B links between four PEs, alongside their clear, MAC and final-token events on counted rising edges.'))
display(Markdown('*Figure 1 — Token wavefront.* An accepted directed input illustrates registered neighbor propagation and final-token completion. The clear edge is included in the count.'))'''),
        cell('markdown', '''The trace above is regenerated from an accepted directed input. It shows token movement and completion, rather than adding a new benchmark. The executable sources are `model/golden.py`, `model/systolic_generic.py`, `rtl/gemm_pe.sv` and `rtl/systolic_array.sv`. The complete cycle and arithmetic contract is in `docs/PHASE2_FUNCTIONAL_CONTRACT.md` and `docs/PHASE1_MICROARCHITECTURE.md`.

## 3. Three independent checks of one computation

The numerical reference evaluates GEMM using explicit wrap. The token model advances PE state edge by edge. The C++/Verilator harness independently drives the RTL boundary and waits for actual RTL completion; it never receives a predicted cycle count. Deterministic randomized inputs, signed/extreme and ragged directed inputs, and the six frozen workload sanity cases are shared across configurations.

The next cell recomputes numerical outputs and the token model for every preserved case, checks the recorded RTL matrices and tile/workload counts, and validates the processed record. Captured compile/execute return codes and stream hashes must agree. A successful model replay alone is not described as a fresh simulator run.'''),
        cell('code', '''replay = replay_functional(ROOT)
assert replay['total_cases'] == analysis['functional']['total_case_executions']
display(Markdown(f"**Offline model replay: {replay['status']}.** All **{replay['total_cases']}** recorded case/configuration executions agree numerically and cycle by cycle."))
show_details('Model replay details', replay)
rows = analysis['functional']['coverage']
table = '| Array | Cases | Numerical pass | Cycle pass | Directed / Random / Workload |\\n|---|---:|---:|---:|---|\\n'
for row in rows:
    categories = row['category_counts']
    table += f"| {row['array_size']}×{row['array_size']} | {row['case_count']} | {row['numerical_passed']} | {row['cycle_passed']} | {categories['directed']} / {categories['randomized']} / {categories['frozen_workload_sanity']} |\\n"
display(Markdown(table))
display(Image(filename=str(ROOT / 'figures/final/functional_coverage.png'),
              alt='Directed, deterministic randomized and frozen-workload cases for each array size, with exact numerical and cycle matches.'))
display(Markdown('*Figure 2 — Functional coverage.* Each array uses the same preserved directed, randomized and workload-sanity corpus. Every accepted execution must agree both numerically and in cycle count.'))
display(Image(filename=str(ROOT / 'figures/final/cycle_agreement.png'),
              alt='Token-model cycles plotted against RTL-observed cycles; the accepted executions lie on the exact-agreement line.'))
display(Markdown('*Figure 3 — Cycle agreement.* Independent token-model counts match RTL-observed rising edges across the accepted corpus. Coincident points can overlap; this is a cycle-correctness check, not a frequency measurement.'))'''),
        cell('markdown', '''Each point is a case/configuration observation, not an independently sampled chip. Agreement covers the tested schedule and input corpus; it is not a formal proof of all possible inputs. Directed PE tests separately exercise wrap, reset, clear, bubbles and final-token behavior. The preserved simulator version and command records are bundled alongside the raw outputs.

## 4. A real open-source RTL-to-GDS toolchain

Before the accelerator work, a tiny counter proved the complete simulation → Yosys synthesis → OpenLane/OpenROAD implementation → post-route STA → GDS chain. It used the same pinned open-source technology stack. Its layout is a **counter layout**, never an accelerator result. The package includes the raw logs, selected reports, final GDS and the original parser; the integrity cell reruns that parser without invoking any EDA tool.'''),
        cell('code', '''counter = json.loads((ROOT / 'results/processed/phase0_metrics.json').read_text())
lock = json.loads((ROOT / 'environment/toolchain.lock.json').read_text())
assert counter['pass'] and counter['physical_flow']['post_route_timing']['stage'] == 'OpenROAD.STAPostPNR'
proof = {'design': counter['design'], 'run_id': counter['run_id'],
         'simulation': counter['simulation']['pass'], 'synthesis': counter['synthesis']['pass'],
         'physical_implementation': counter['physical_flow']['pass'],
         'post_route_stage': counter['physical_flow']['post_route_timing']['stage'],
         'gds': counter['physical_flow']['gds'],
         'pdk': lock['pdk']['name'], 'library': lock['standard_cell_library']['name']}
display(Markdown(f"**Tiny-counter toolchain: PASS.** `{proof['design']}` completed simulation, synthesis, physical implementation, post-route timing and GDS generation using `{proof['pdk']}` / `{proof['library']}`."))
show_details('Counter tools, run and artifact identities', proof)''')]
    if primary:
        cells += [cell('markdown', '''## 5. Matched post-route implementations and decision fidelity

Only the complete qualified FINAL 2×2/4×4/8×8 family enters this section. All configurations share one recipe, PDK/library, timing method and source freeze. Development attempts and historical rejected runs never supply comparative metrics.

The reported frequency is a **post-route fixed-layout STA-derived frequency estimate**, not measured silicon Fmax. At the frozen slow corner, the same final netlist, extracted SPEF, propagated-clock SDC and saved environment supply internal register-to-register setup slack. The parser derives `P_sta_est_ns = 20 − S_r2r_ns` and `F_sta_MHz = 1000/P_sta_est_ns`; implementation-aware latency is `C_rtl × 1000/F_sta_MHz` in ns. This does not re-optimize layout for a different clock.

The six workloads were fixed before these measurements. Positive values are tied using relative tolerance 1e-9 with zero absolute tolerance. Every tied minimum is retained; a workload with ties is indeterminate for unique top-1 agreement. Any pair tied in either layer is indeterminate. No reversal is presumed.'''),
            cell('code', '''import hashlib
recipe_path = ROOT / 'rebuild/common_recipe.json'
recipe_bytes = recipe_path.read_bytes()
assert hashlib.sha256(recipe_bytes).hexdigest() == analysis['scientific_analysis']['configurations'][0]['recipe_sha256']
recipe = json.loads(recipe_bytes)
backend_rows = [(label, recipe[key]) for label, key in (
    ('OpenLane version', 'openlane_version'), ('Flow', 'flow'), ('Container image', 'docker_image'),
    ('PDK', 'pdk'), ('PDK revision', 'pdk_revision'), ('Standard-cell library', 'standard_cell_library'))]
for key, unit in (('CLOCK_PERIOD', 'ns'), ('FP_CORE_UTIL', '%'), ('GRT_ANTENNA_ITERS', ''),
                  ('GRT_ANTENNA_MARGIN', '%'), ('RUN_ANTENNA_REPAIR', ''),
                  ('RUN_HEURISTIC_DIODE_INSERTION', ''), ('GPL_CELL_PADDING', ''), ('DPL_CELL_PADDING', '')):
    backend_rows.append((key, str(recipe['common_config'][key]) + (' ' + unit if unit else '')))
backend_table = '| Common setting | Frozen value |\\n|---|---|\\n'
for label, value in backend_rows:
    backend_table += f'| {label} | `{value}` |\\n'
display(Markdown(backend_table))
configured_gpl_padding = recipe['common_config']['GPL_CELL_PADDING']
effective_gpl_padding = configured_gpl_padding // 2
display(Markdown(f'These are configured values from the byte-matched common recipe. The pinned global-placement implementation uses floor(GPL_CELL_PADDING / 2) sites per side: configured {configured_gpl_padding} therefore gives {effective_gpl_padding} per side. The selected recipe is shared by every array.'))'''),
            cell('code', '''science = analysis['scientific_analysis']
assert analysis['analysis_mode'] == 'PRIMARY_RESEARCH'
show_details('Decision summary data', {'top1': science['top1'], 'pairwise': {k:v for k,v in science['pairwise'].items() if k != 'decisions'}})
for name in ('physical_scaling', 'cycles_and_latency', 'pairwise_decisions', 'margin_transformation'):
    display(Image(filename=str(ROOT / ('figures/final/' + name + '.png'))))'''),
            cell('code', '''warnings = json.loads((ROOT / 'support/electrical_warnings.json').read_text())
display(Markdown('**Electrical-check limitations.** ' + warnings['meaning']))
table = '| Array | Max slew count | Max fanout count | Max capacitance count |\\n|---|---:|---:|---:|\\n'
for cfg in warnings['configurations']:
    native = {item['source_key']: item['value'] for item in cfg['counts']}
    values = [native.get('design__max_' + kind + '_violation__count', 'UNAVAILABLE') for kind in ('slew', 'fanout', 'cap')]
    table += '| ' + str(cfg['array_size']) + '×' + str(cfg['array_size']) + ' | ' + ' | '.join(map(str, values)) + ' |\\n'
display(Markdown(table))
display(Markdown('All corner-specific counts, units and exact native source keys are retained in `support/electrical_warnings.json`. They are not silently converted into clean electrical signoff.'))'''),
            cell('code', '''summary = science['pairwise']
top = science['top1']
display(Markdown(f"Unique top-1 agreement is **{top['agreement_count']}/{top['total_workloads']}**, with **{top['tied_or_indeterminate_count']}** tied/indeterminate workloads. Across **{summary['total_decisions']}** pairs: **{summary['preserved']}** are preserved, **{summary['reversed']}** reversed and **{summary['tied_or_indeterminate']}** tied/indeterminate. These are observations in this fixed domain, not a universal statement about architecture-model reliability."))
display(Markdown('Margin transformations use natural-log ratios; every pair and its source configuration remain in `final_analysis.json`. A null result is retained without replacing workloads or changing the backend.'))''')]
    else:
        cells += [cell('markdown', '''## 5. What physical qualification taught us

The model-to-RTL workflow is verified, while accelerator physical qualification remains incomplete. A complete qualified set of implementations is needed to compare performance across array sizes. This notebook therefore makes no claim about whether cycle-based configuration choices survive post-route timing.

Completing a route or writing a GDS file is not enough. Mapped compute state must be retained, routing and enabled signoff checks must pass, and the timing query must refer to the same routed artifacts. Historical work exposed both evidence-tooling defects and antenna signoff failures. Those classes are kept separate: repairing a parser does not repair a circuit, and an unsuccessful recipe does not establish universal design infeasibility.

Rejected area, slack, frequency and GDS characteristics are excluded from scientific comparison. No accelerator scaling plot, hardware winner or ranking-disagreement claim is produced.'''),
            cell('code', '''assert analysis['analysis_mode'] != 'PRIMARY_RESEARCH'
assert analysis['scientific_analysis'] is None
assert analysis['rejected_physical_performance_used'] is False
show_details('Comparative-analysis eligibility record', analysis['scientific_analysis_unavailable_reasons'])''')]
    cells += [cell('code', '''history = analysis.get('physical_attempt_history')
if history is not None:
    heading = 'Physical qualification complete' if history['pass'] else 'Physical qualification incomplete'
    display(Markdown('**' + heading + '.**'))
    attempt_record = json.loads((ROOT / 'support/physical_attempt_history.json').read_text())
    attempt_table = '| Array | Physical qualification |\\n|---|---|\\n'
    for cfg in attempt_record['configurations']:
        if cfg['status'] == 'PASS':
            outcome = 'Final implementation qualified'
        elif cfg['status'] == 'NOT_RUN':
            outcome = 'Not run after the preceding qualification stop'
        elif 'antenna__violating' in (cfg['error'] or ''):
            outcome = 'Did not pass final antenna signoff'
        else:
            outcome = 'Not qualified for comparative analysis'
        attempt_table += f"| {cfg['array_size']}×{cfg['array_size']} | {outcome} |\\n"
    display(Markdown(attempt_table))
    if history['pass']:
        display(Markdown('Only the complete qualified family supplies the comparison. Earlier partial results are excluded.'))
    else:
        display(Markdown('Incomplete physical families are excluded from scientific comparison, including performance and ranking claims. Earlier partial results are excluded.'))
    show_details('Physical qualification provenance: raw outcomes, errors and selection history', attempt_record)
    display(Markdown('The underlying records are preserved in `support/physical_attempt_history.json`; no rejected physical performance is presented.'))''')]
    layout_scope = ('The overview below is drawn from the accepted FINAL 2×2/4×4/8×8 GDS files. '
                    'It contains no development or rejected-run geometry.' if primary else
                    'The overview below is drawn only from the accepted tiny-counter GDS. '
                    'It is a toolchain illustration, not an accelerator implementation result.')
    layout_alt = ('Selected routing geometry from the qualified array implementations, with source identities retained.' if primary else
                  'Selected routing geometry from the accepted tiny-counter GDS: an open-source RTL-to-GDS toolchain proof, not the GEMM accelerator layout.')
    layout_caption = ('*Figure 4 — Accepted implementation layouts.* Selected routing geometry from the qualified array implementations; artifact identities retain full provenance.' if primary else
                      '*Figure 4 — Tiny-counter toolchain proof.* This is the accepted counter GDS, not a GEMM accelerator layout. The selected routing view demonstrates the open-source RTL-to-GDS path; it adds no accelerator physical result.')
    cells += [cell('markdown', '### Actual layout illustration\n\n' + layout_scope + '''

This reproducible view selects top-cell polygons and paths on GDS layers 67–72, datatype 20, with micrometre coordinates. Reference-cell geometry and text labels are omitted; large boundary polygons are outlined. It is a selected routing overview, not a transistor-detail rendering or an additional signoff check. The same selection is used for every displayed array. Exact GDS identities follow the image.'''),
        cell('code', f'''display(Image(filename=str(ROOT / 'figures/final/layout_overview.png'), alt={layout_alt!r}))
display(Markdown({layout_caption!r}))
show_details('Layout file identities', analysis['layout_sources'])'''),
        cell('markdown', f'''## What this experiment establishes

### {total}/{total} exact agreement

Across 2×2, 4×4 and 8×8 configurations, the independent numerical model, token-cycle model and recorded RTL observations agree on every accepted case: exact numerical outputs and exact cycle counts.

### Cycle semantics are executable, not assumed

The harness observes completion from the RTL's result-valid behavior and counts simulated clock edges. A closed-form latency predictor does not supply the observed completion time.

### Evidence levels remain separate

Functional correctness, successful tool execution, generated physical artifacts and qualified physical evidence answer different questions. The accepted functional result stands on its own; the incomplete accelerator physical family supports no comparative performance or ranking claim.'''),
        cell('markdown', '''## 6. Reproduce and extend responsibly

1. Create a Python environment and install `requirements.txt`.
2. Run `python scripts/build_submission.py --verify-package` from this directory. This verifies bundled hashes, reparses the counter evidence, regenerates GEMM/token results and checks captured RTL observations.
3. Run `python scripts/reproduce_figures.py --root . --portable --check` to verify figure regeneration, then execute this notebook top to bottom.

The package supports offline replay of the recorded observations. Optional fresh tool runs are described in `REBUILD.md`; the development repository retains the complete run history and qualification records.

Boundaries: idealized streaming compute core; no external-memory system, application demonstration, power or energy estimate. Verification coverage is finite. A single PDK/library and fixed backend cannot establish behavior across technologies or process variation. Agent assistance was used for engineering, tests and explanation; humans remain responsible for claims, provenance, licensing and authorship.

## References and license

- [ISSCC 2027 Code-a-Chip official repository](''' + OFFICIAL_BASE + '''README.md): current notebook, license, project-directory and reproduction requirements. The package preserves dated rule metadata in `support/official_rules.json`; its linked older application guide is disclosed separately.
- [OpenLane 2 documentation](https://openlane2.readthedocs.io/en/stable/): reproducible RTL-to-GDS flow and Classic steps.
- [Yosys documentation](https://yosyshq.readthedocs.io/projects/yosys/en/latest/): RTL synthesis.
- [OpenROAD](https://github.com/The-OpenROAD-Project/OpenROAD) and [OpenSTA](https://github.com/The-OpenROAD-Project/OpenSTA): physical implementation and static timing.
- [SKY130 PDK documentation](https://skywater-pdk.readthedocs.io/en/main/): open technology and standard-cell context.
- [Verilator documentation](https://verilator.org/guide/latest/): compiled RTL simulation.

Project source is licensed under Apache-2.0; see `LICENSE`. Bundled GDS contains upstream standard-cell geometry; its attribution and license copies are in `NOTICE` and `third_party/`. Third-party tools/PDKs retain their own licenses. No external notebook was copied into this notebook. `REFERENCES.md` distinguishes external tools from original project material.''')]
    for index, item in enumerate(cells):
        item['id'] = 'model2gds-' + str(index).zfill(2)
    return {'nbformat': 4, 'nbformat_minor': 5, 'metadata': {'kernelspec': {'display_name': 'Python 3', 'language': 'python', 'name': 'python3'},
            'language_info': {'name': 'python', 'version': '3.12'},
            'model2gds': {'analysis_mode': analysis['analysis_mode'], 'evidence_replay': 'offline; no EDA invocation'}}, 'cells': cells}


def copy_inputs(root, destination, analysis):
    functional, counter = read(root / FUNCTIONAL), read(root / PHASE0)
    sources = functional['raw_sources'] + counter['raw_sources']
    verify_sources(root, sources)
    paths = {s['path'] for s in sources}
    paths.update([ANALYSIS, FUNCTIONAL, PHASE0, 'PROJECT_FREEZE.json', 'LICENSE', 'environment/toolchain.lock.json',
                  'results/raw/phase0/selection.json', 'results/raw/phase2/functional_selection.json',
                  'scripts/build_submission.py', 'scripts/analyze_final_results.py', 'scripts/reproduce_figures.py',
                  'scripts/collect_phase0_metrics.py', 'scripts/collect_phase2_functional.py',
                  'scripts/collect_phase1_verification.py', 'scripts/generate_phase2_wrappers.py', 'scripts/phase1_common.py',
                  'scripts/run_phase2_functional.py',
                  'docs/FINAL_SPRINT.md', 'docs/submission_authors.json', 'docs/PHASE1_MICROARCHITECTURE.md', 'docs/PHASE2_FUNCTIONAL_CONTRACT.md',
                  'docs/PHASE2_TIMING_METHODOLOGY.md', 'docs/EXPERIMENT_PROTOCOL.md', 'docs/RESEARCH_QUESTION.md',
                  'verification/phase2_sim_main.cpp', 'phase0/smoke/rtl/phase0_counter.v',
                  'phase0/smoke/tb/tb_phase0_counter.v', 'phase0/smoke/openlane/config.json'])
    paths.update(p.relative_to(root).as_posix() for folder, pattern in [('model', '*.py'), ('rtl', '*.sv')]
                 for p in (root / folder).glob(pattern))
    paths.update(p.relative_to(root).as_posix() for p in (root / 'figures/final').glob('*') if p.is_file())
    rules_directory = root / 'results/raw/phase2/sprint/SUBMISSION_RULES_001'
    require(rules_directory.is_dir(), 'Missing captured official-rule verification')
    paths.update(p.relative_to(root).as_posix() for p in rules_directory.iterdir() if p.is_file())
    license_directory = root / LICENSE_EVIDENCE
    require(license_directory.is_dir(), 'Missing pinned standard-cell licensing evidence')
    paths.update(p.relative_to(root).as_posix() for p in license_directory.iterdir() if p.is_file())
    history = attempt_history_projection(root, analysis, verify_original=True)
    if history is not None:
        write_asset(destination / 'support/physical_attempt_history.json', canonical(history))
    if analysis['analysis_mode'] == 'PRIMARY_RESEARCH':
        physical = read(root / 'results/processed/final_physical_metrics.json')
        paths.add('results/processed/final_physical_metrics.json')
        paths.update(('scripts/collect_phase2_physical.py', 'scripts/check_phase2_structure.py', 'scripts/phase2_r2r_sta.tcl'))
        inventory = primary_payload(root, physical)
        paths.update(source['path'] for source in inventory['included'])
        write_asset(destination / 'support/physical_evidence_inventory.json', canonical(inventory))
        write_asset(destination / 'support/electrical_warnings.json', canonical(electrical_warnings(root, physical)))
    for relative in sorted(paths):
        source, target = safe_path(root, relative), safe_path(destination, relative)
        require(source.is_file(), 'Required portable input is missing: ' + relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
    return sorted(paths)


def write_asset(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content.encode('utf-8') if isinstance(content, str) else content)


def seal_package(root):
    files = [descriptor(root, p.relative_to(root).as_posix()) for p in sorted(root.rglob('*')) if p.is_file()
             and '__pycache__' not in p.parts and '.ipynb_checkpoints' not in p.parts and p != root / 'file_manifest.json']
    manifest = {'schema_version': 1, 'algorithm': 'sha256', 'self_exclusion': 'file_manifest.json', 'files': files}
    write_asset(root / 'file_manifest.json', canonical(manifest))
    return manifest


def notebook_runtime():
    names = ('ipykernel', 'nbclient', 'nbformat', 'matplotlib', 'numpy', 'pillow', 'fonttools', 'gdstk')
    observed = {name: version(name) for name in names}
    return {'python': sys.version.split()[0], 'packages': observed,
            'source': 'importlib.metadata.version from the interpreter executing build_submission.py'}


def execute_notebook(root):
    """Execute in memory, leaving the distributed notebook/manifest unchanged."""
    import nbformat
    from nbclient import NotebookClient
    root = Path(root).resolve()
    verify_package(root, replay=False)
    node = nbformat.read(root / 'Model2GDS.ipynb', as_version=4)
    NotebookClient(node, timeout=900, kernel_name='python3', resources={'metadata': {'path': str(root)}}).execute()
    return {'status': 'PASS', 'executed_code_cells': sum(c.cell_type == 'code' for c in node.cells),
            'source_notebook_unchanged': True, 'fresh_eda_executed': False}


def rtl_rebuild_commands(root, work, size):
    """Construct fresh simulation commands; merely calling this never runs them."""
    require(type(size) is int and size in (2, 4, 8), 'RTL rebuild size must be 2, 4 or 8')
    root, work = Path(root).resolve(), Path(work).resolve()
    require(not work.is_relative_to(root), 'Fresh outputs must be outside the immutable package')
    functional = read(root / FUNCTIONAL)
    run = root / 'results/raw/phase2/functional' / functional['run_id']
    prefix = run / ('S' + str(size))
    compile_command = ['verilator', '--cc', '--exe', '--build', '-j', '2', '-Wall', '-Wno-PINCONNECTEMPTY',
        '--top-module', 'phase2_sim_top', '--Mdir', str(work / 'obj'), '-CFLAGS', f'-std=c++17 -DARRAY_SIZE={size}',
        str(root / 'rtl/gemm_pe.sv'), str(root / 'rtl/systolic_array.sv'), str(prefix / 'phase2_sim_top.sv'),
        str(root / 'verification/phase2_sim_main.cpp')]
    execute_command = [str(work / 'obj/Vphase2_sim_top'), str(run / 'phase1_oracles/vectors.txt'),
                       str(work / 'rtl_results.jsonl'), str(work / 'array_tests.json')]
    return {'compile': compile_command, 'execute': execute_command}


def rerun_rtl(root, work, size):
    """Explicit optional rebuild, with no Git access or physical-tool call."""
    root, work = Path(root).resolve(), Path(work).resolve()
    verify_package(root, replay=False)
    commands = rtl_rebuild_commands(root, work, size)
    work.mkdir(parents=True, exist_ok=False)
    (work / 'obj').mkdir()
    for name, argv in commands.items():
        stdout, stderr = work / (name + '.stdout.log'), work / (name + '.stderr.log')
        receipt_path = work / (name + '.command.json')
        started = datetime.now(timezone.utc).isoformat()
        code, launch_error = None, None
        with stdout.open('xb') as out, stderr.open('xb') as err:
            try:
                code = subprocess.run(argv, cwd=root, stdout=out, stderr=err).returncode
            except OSError as exc:
                launch_error = str(exc)
                err.write(launch_error.encode('utf-8'))
        receipt = {'argv': argv, 'cwd': str(root), 'returncode': code, 'launch_error': launch_error,
                   'started_at': started, 'finished_at': datetime.now(timezone.utc).isoformat(),
                   'stdout': stdout.name, 'stderr': stderr.name,
                   'stdout_sha256': hashlib.sha256(stdout.read_bytes()).hexdigest(),
                   'stderr_sha256': hashlib.sha256(stderr.read_bytes()).hexdigest()}
        write_asset(receipt_path, canonical(receipt))
        require(code == 0, 'Fresh ' + name + ' failed; inspect preserved logs in ' + str(work))
    functional = read(root / FUNCTIONAL)
    old = root / 'results/raw/phase2/functional' / functional['run_id'] / ('S' + str(size))
    expected = [json.loads(line) for line in (old / 'rtl_results.jsonl').read_text().splitlines() if line.strip()]
    observed = [json.loads(line) for line in (work / 'rtl_results.jsonl').read_text().splitlines() if line.strip()]
    require(observed == expected and read(work / 'array_tests.json') == read(old / 'array_tests.json'),
            'Fresh RTL results differ from accepted observations')
    result = {'status': 'PASS', 'array_size': size, 'case_count': len(observed),
              'meaning': 'Optional fresh RTL reproduction only; not a new research or physical qualification record.'}
    write_asset(work / 'comparison.json', canonical(result))
    return result


def write_rebuild_support(root, destination, analysis):
    """Make optional tool instructions independent of the forensic Git history."""
    lock = read(root / 'environment/toolchain.lock.json')
    image = lock['environment']['container_image']['repository_digests'][0]
    revision = lock['environment']['pdk']['observed']['revision']
    text = f'''# Optional fresh tool runs

The notebook and `--verify-package` need no EDA installation. These additional
commands run real tools and may take minutes to hours. They write to a fresh
directory outside the package and never replace bundled evidence. No historical
Git objects or repository remote are needed. A new output is a reproduction
attempt, not automatically an accepted new research result.

## RTL simulation

Use Linux/WSL with Verilator and a C++17 compiler. The captured accepted version
is recorded in the functional JSON and `environment/toolchain.lock.json`.

```bash
python scripts/build_submission.py --rerun-rtl --array-size 2 --work-dir /tmp/model2gds_rtl_s2_001
python scripts/build_submission.py --rerun-rtl --array-size 4 --work-dir /tmp/model2gds_rtl_s4_001
python scripts/build_submission.py --rerun-rtl --array-size 8 --work-dir /tmp/model2gds_rtl_s8_001
```

The helper compiles the bundled thin wrapper, PE/fabric and C++ harness, uses the
preserved text vectors, saves exact argv/stdout/stderr/return codes and compares
all new matrices, tile cycles and directed tests with the accepted observations.
Existing work directories are refused. The notebook never calls this option.

## Tiny-counter RTL-to-GDS

Install Docker and the open SKY130 PDK separately using the upstream supported
OpenLane/Volare setup. Required open_pdks revision: `{revision}`; PDK `sky130A`,
library `sky130_fd_sc_hd`. Set `MODEL2GDS_PDK_ROOT` to the directory containing
that `sky130A` installation. All source RTL/configuration is included here.

```bash
set -eu
MODEL2GDS_PACKAGE="$(pwd)"
MODEL2GDS_RUN=/tmp/model2gds_counter_001
mkdir "$MODEL2GDS_RUN"
cp phase0/smoke/openlane/config.json "$MODEL2GDS_RUN/config.json"
python -c 'import json,sys; p=sys.argv[1]; d=json.load(open(p)); d["VERILOG_FILES"]=["/work/phase0/smoke/rtl/phase0_counter.v"]; open(p,"w").write(json.dumps(d,indent=2)+"\\n")' "$MODEL2GDS_RUN/config.json"
docker run --rm --user "$(id -u):$(id -g)" --env HOME=/tmp --env PDK_ROOT=/pdk \\
  --volume "$MODEL2GDS_PACKAGE:/work:ro" --volume "$MODEL2GDS_PDK_ROOT:/pdk:ro" \\
  --volume "$MODEL2GDS_RUN:/out" --workdir /work \\
  {image} \\
  openlane --manual-pdk --pdk-root /pdk --pdk sky130A --scl sky130_fd_sc_hd \\
  --flow Classic --jobs 2 --run-tag REBUILD_001 --hide-progress-bar /out/config.json
```

The sole transformation above relocates the input path; it changes no RTL or
backend setting. OpenLane writes reports and the layout under the fresh output
mount. Preserve failures as well as successful outputs. These optional commands
are supplied for reproduction; they are not run by package generation.
'''
    if analysis['analysis_mode'] == 'PRIMARY_RESEARCH':
        physical = read(root / 'results/processed/final_physical_metrics.json')
        first = physical['configurations'][0]
        # Find the original explicit common recipe by its recorded SHA; do not
        # synthesize a recipe from observed timing or per-configuration values.
        matches = [s['path'] for s in physical['raw_sources'] if s['sha256'] == first['recipe_sha256']]
        require(matches, 'Accepted common recipe source is not bundled')
        recipe_path = matches[0]
        recipe = read(safe_path(root, recipe_path))
        write_asset(destination / 'rebuild/common_recipe.json', safe_path(root, recipe_path).read_bytes())
        for size in (2, 4, 8):
            identity = recipe['configurations'][str(size)]
            for native in identity['verilog_files']:
                require(native.startswith('/work/'), 'Unexpected portable wrapper source path')
                relative = native[len('/work/'):]
                write_asset(safe_path(destination, relative), safe_path(root, relative).read_bytes())
            config = {**recipe['common_config'], 'DESIGN_NAME': identity['design_name'], 'VERILOG_FILES': identity['verilog_files']}
            write_asset(destination / f'rebuild/s{size}/config.json', canonical(config))
        text += '''
## Accepted accelerator family

`rebuild/common_recipe.json` is the exact accepted explicit common recipe;
`rebuild/s2/config.json`, `rebuild/s4/config.json` and `rebuild/s8/config.json`
change only design identity and wrapper paths. The matching source wrappers are
bundled. Use the same Docker command above, a separate new output directory per
size, and copy the chosen accelerator config to its `/out/config.json` before
launching. Do not apply the counter-specific input-path rewrite. Reuse the exact
PDK/image and common recipe. Routing, signoff, compute retention and internal
post-route timing must be independently checked before treating a fresh run as
qualified; the original accepted measurements remain unchanged.
'''
    write_asset(destination / 'REBUILD.md', text)


def readme(analysis):
    """Render the reviewer overview from accepted structured functional data."""
    total = analysis['functional']['total_case_executions']
    numerical = sum(row['numerical_passed'] for row in analysis['functional']['coverage'])
    cycles = sum(row['cycle_passed'] for row in analysis['functional']['coverage'])
    title = FULL_TITLE if analysis['analysis_mode'] == 'PRIMARY_RESEARCH' else FALLBACK_TITLE
    return f'''# {title}

Explore a parameterized **2×2 / 4×4 / 8×8 output-stationary systolic array**
with an independent numerical model, an independent token-cycle model and
parameterized SystemVerilog RTL. Across
**{analysis['functional']['total_case_executions']} accepted case/configuration executions**,
the models and captured RTL agree exactly on numerical results and cycle counts.

**[Open the executable Jupyter notebook](Model2GDS.ipynb)** to inspect the design,
replay the verification, and follow the reproducible
**raw evidence → parser → structured result → figure** workflow.
A separate tiny-counter design proves the open-source RTL-to-GDS toolchain.

## Key results

| Result | Model2GDS |
|---|---|
| Array sizes | 2×2 / 4×4 / 8×8 |
| Accepted executions | **{total}** |
| Numerical agreement | **{numerical} / {total}** |
| Cycle agreement | **{cycles} / {total}** |
| Models | Independent numerical + token-cycle |
| RTL | Parameterized SystemVerilog |
| Reproduction | Executable notebook + offline replay |

![Independent token-model cycles and RTL-observed cycles coincide across all accepted 2×2, 4×4 and 8×8 executions.](figures/final/cycle_agreement.png)

*Exact cycle agreement across the accepted corpus. Coincident points can overlap;
this verifies cycle semantics and does not measure physical frequency.*

**Yixuan Zhuang — School of Microelectronics, Fudan University**  
Contact: yixuanzhuangfudan@gmail.com · [Team metadata](TEAM.json)

## Offline reproduction

Use Python 3.12 with the recorded dependency versions. From this directory:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/build_submission.py --verify-package
python scripts/reproduce_figures.py --root . --portable --check
python scripts/build_submission.py --execute-notebook
```

On Windows, activate `.venv/Scripts/Activate.ps1`.
JupyterLab can also open the notebook and run all cells. The offline verification
needs only Python's standard library; display/plot dependencies are listed above.
Nothing in this workflow invokes a simulator, synthesis, P&R, STA or Docker.
`--execute-notebook` runs cells in memory and preserves the bundled source bytes.
The exact observed notebook dependency versions are in `support/notebook_runtime.json`.

The replay recomputes GEMM/token results from preserved inputs and compares them
with the recorded RTL observations. It reparses the tiny-counter raw evidence and
regenerates analysis/figures, without running a simulator or physical flow.
Raw command records retain historical machine paths solely as provenance.

## What is included

- `Model2GDS.ipynb`: the narrative and executable checks.
- `model/`, `rtl/`, `verification/`: independent references and synthesizable fabric/harness.
- `results/processed/`: immutable accepted functional/counter data and final analysis.
- `results/raw/`: captured simulation and counter RTL-to-GDS sources for displayed claims.
- `figures/final/`: deterministic figures and their source manifest.
- `file_manifest.json`: exact SHA256 and byte size of every package file, excluding itself.
- `environment/toolchain.lock.json`: recorded tool, PDK and library versions.
- `docs/`: arithmetic, cycle, workload and final-analysis contracts.

[REBUILD.md](REBUILD.md) describes optional fresh Verilator and pinned OpenLane
runs from bundled sources, with outputs kept in a separate work directory.
The notebook and these rebuild demonstrations are self-contained. The complete
development history and qualification records are available from the author.

## Scope and submission

The tiny counter proves the ASIC toolchain; it is never an accelerator result.
Accelerator physical qualification is incomplete: the final 2×2 implementation
qualified, 4×4 did not pass final antenna signoff, and 8×8 was therefore not run.
Incomplete physical families and rejected physical metrics are excluded from
comparative performance and ranking claims. No silicon Fmax, power/energy or
process-variation result is claimed. The notebook retains the qualification
summary and expandable provenance.

Apache-2.0 project license: `LICENSE`. GDS cell attribution: `NOTICE` and
`third_party/`. Primary references: `REFERENCES.md`.
Official rule provenance: `support/official_rules.json`. Place this entire folder
under `ISSCC27/submitted_notebooks/Model2GDS/` in the official fork; change no other
project. Team and contact details are in `TEAM.json`.
'''


def build(root=ROOT, *, execute=False):
    root = Path(root).resolve()
    analysis, functional, frozen = (read(root / p) for p in (ANALYSIS, FUNCTIONAL, 'PROJECT_FREEZE.json'))
    validate_analysis(analysis, functional, frozen)
    verify_sources(root, analysis['sources'])
    destination = root / PACKAGE
    require(not destination.exists(), 'Refusing to overwrite candidate; use --check on existing output')
    destination.mkdir(parents=True)
    copied = copy_inputs(root, destination, analysis)
    team = read(root / 'docs/submission_authors.json')
    require(team.get('status') == 'OWNER_CONFIRMED' and team.get('members') and team.get('representative'),
            'Missing owner-confirmed author metadata')
    write_asset(destination / 'TEAM.json', canonical(team))
    write_asset(destination / 'support/official_rules.json', canonical(RULES))
    write_asset(destination / '.gitattributes', PACKAGE_ATTRIBUTES)
    runtime = notebook_runtime()
    write_asset(destination / 'support/notebook_runtime.json', canonical(runtime))
    write_asset(destination / 'requirements.txt', ''.join(name + '==' + number + '\n' for name, number in runtime['packages'].items()))
    write_rebuild_support(root, destination, analysis)
    for name, content in third_party_material(root).items():
        write_asset(destination / name, content)
    write_asset(destination / 'REFERENCES.md', '# References and provenance\n\n' + '\n'.join('- ' + s['url'] for s in RULES['sources']) + '''

The current official README permits circuit-design and educational notebooks; a
layout is encouraged rather than mandatory. Its October 31 deadline is recorded
at the pinned commit. The linked application guide still names the older contest
year. This package does not change the project's earlier October 9 planning bound.

OpenLane 2: https://openlane2.readthedocs.io/en/stable/
Yosys: https://yosyshq.readthedocs.io/projects/yosys/en/latest/
OpenROAD: https://github.com/The-OpenROAD-Project/OpenROAD
OpenSTA: https://github.com/The-OpenROAD-Project/OpenSTA
SKY130: https://skywater-pdk.readthedocs.io/en/main/
Verilator: https://verilator.org/guide/latest/

Tool sources are cited for implementation and semantics, not novelty claims.
This notebook is original project material; no third-party notebook was reused.
The project source uses the bundled Apache-2.0 license. Bundled GDS contains
upstream standard-cell geometry; `NOTICE` identifies its sources and `third_party/`
retains exact upstream license copies. Tools and PDK material retain their licenses.
''')
    write_asset(destination / 'README.md', readme(analysis))
    nb = notebook(analysis, team)
    write_asset(destination / 'Model2GDS.ipynb', canonical(nb))
    seal_package(destination)
    if execute:
        import nbformat
        from nbclient import NotebookClient
        node = nbformat.from_dict(nb)
        NotebookClient(node, timeout=900, kernel_name='python3', resources={'metadata': {'path': str(destination)}}).execute()
        for item in node.cells:
            item.metadata.pop('execution', None)
        nb = json.loads(nbformat.writes(node))
        write_asset(destination / 'Model2GDS.ipynb', canonical(nb))
        seal_package(destination)
    write_asset(root / 'notebooks/Model2GDS.ipynb', canonical(nb))
    result = verify_package(destination, replay=True)
    return {**result, 'package': PACKAGE, 'source_files_copied': len(copied),
            'notebook_executed': execute, 'notebook': 'notebooks/Model2GDS.ipynb'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--verify-package', action='store_true')
    parser.add_argument('--execute-notebook', action='store_true')
    parser.add_argument('--rerun-rtl', action='store_true', help='Explicit optional real Verilator compilation/simulation')
    parser.add_argument('--array-size', type=int, choices=(2, 4, 8))
    parser.add_argument('--work-dir', type=Path)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args(argv)
    root = args.root.resolve()
    if args.rerun_rtl:
        require(args.array_size is not None and args.work_dir is not None, 'RTL rebuild requires --array-size and --work-dir')
        target = root if (root / 'file_manifest.json').is_file() else root / PACKAGE
        result = rerun_rtl(target, args.work_dir, args.array_size)
    elif args.execute_notebook:
        target = root if (root / 'file_manifest.json').is_file() else root / PACKAGE
        result = execute_notebook(target)
    elif args.verify_package:
        target = root if (root / 'file_manifest.json').is_file() else root / PACKAGE
        result = verify_package(target)
    elif args.check:
        result = verify_package(root / PACKAGE)
        require((root / 'notebooks/Model2GDS.ipynb').read_bytes() == (root / PACKAGE / 'Model2GDS.ipynb').read_bytes(),
                'Repository/package notebooks differ')
    else:
        result = build(root, execute=args.execute)
    print(canonical(result).decode(), end='')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
