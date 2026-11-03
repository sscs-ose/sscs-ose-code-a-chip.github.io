"""Preserve the real GUI scheduler and unchanged-PE continuation, read only.

All four durable histories are inspected on scratch copies. This never calls a
model/tool, reviews a result, modifies live data, or replaces existing evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tempfile

from node_spec_evidence import ROOT, load, sha, verify_files, write_json
from hullcirq.domain import revision_hashes
from hullcirq.implementation_specs import build_node_implementation_spec
from hullcirq.server import make_server, project_envelope
from hullcirq.store import ProjectStore
from hullcirq.verification import build_verification_plan, content_hash, object_hash, verification_template_version

HISTORIES = ('state.json', 'generation.json', 'workflow.json', 'implementation_specs.json')
NODE_IDS = ('node-scheduler', 'node-pe')
RECORD_KIND = 'actual_GUI_scheduler_and_PE_verification_contract_preserved_continuous_flow'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_histories(directory):
    return {name: (Path(directory) / name).read_bytes() for name in HISTORIES}


def inspect_histories(directory):
    """Strict load copied histories; allow manager housekeeping only on copies."""
    scratch = ROOT / '.work/m2d/evidence-checks'
    scratch.mkdir(parents=True, exist_ok=True)
    raw = read_histories(directory)
    with tempfile.TemporaryDirectory(prefix='scheduler-check-', dir=scratch) as temporary:
        copied = Path(temporary)
        for name, value in raw.items():
            (copied / name).write_bytes(value)
        server = make_server('127.0.0.1', 0, ProjectStore(copied), ROOT)
        try:
            envelope = project_envelope(server)
        finally:
            server.workflow.close()
            server.generation.close()
            server.server_close()
    require(read_histories(directory) == raw, 'Histories changed while being inspected; retry after execution finishes.')
    return envelope


def unique(records, identifier):
    matches = [record for record in records if record['id'] == identifier]
    require(len(matches) == 1, 'Missing or ambiguous preserved record: ' + identifier)
    return matches[0]


def latest_passed(records, node_id, stage_id=None):
    matches = [record for record in records if record['node_id'] == node_id
               and (stage_id is None or record['stage_id'] == stage_id)]
    require(bool(matches), 'No preserved latest result for ' + node_id + ' / ' + str(stage_id))
    result = matches[-1]
    require(all(result.get(key) == expected for key, expected in (
        ('execution_status', 'Completed'), ('validation_status', 'Passed'),
        ('review_status', 'Accepted'), ('freshness', 'Current'))),
        'Latest result needs Passed/Accepted/Current: ' + node_id + ' / ' + str(stage_id))
    return result


def validate_continuation(directory, baseline_directory):
    """Return immutable raw records only after authoritative effective checks."""
    directory, baseline_directory = Path(directory), Path(baseline_directory)
    histories = {name: load(directory / name) for name in HISTORIES}
    originals = {name: load(baseline_directory / name) for name in HISTORIES}
    state, generation, workflow, specifications = [histories[name] for name in HISTORIES]
    design = state['design']
    require(design['project']['id'] == originals['state.json']['design']['project']['id'] == 'hullcirq-npu-4x4-int8', 'Project identity differs from the original GUI project.')
    require(object_hash(design.get('verification_jobs')) == object_hash(originals['state.json']['design'].get('verification_jobs')), 'The original canonical NPU job was replaced or modified, including JSON numeric types.')
    original_pe = next(job for job in reversed(originals['generation.json']['jobs']) if job['node_id'] == 'node-pe' and job['validation_status'] == 'Passed')
    require(original_pe['verification_plan']['vector_count'] == 42, 'The original PE proof must have 42 GUI-saved cycles.')
    require(all(job['execution_status'] not in ('Queued', 'Running') for job in generation['jobs'])
            and all(run['execution_status'] not in ('Queued', 'Running') for run in workflow['runs']), 'Wait for all actual model and tool operations to reach terminal state.')
    envelope = inspect_histories(directory)
    require(envelope['design'] == design, 'Strict loaded design differs from the raw source.')
    for stage in envelope['workflow']:
        if stage['id'] in ('global_settings', 'graph_editor', 'specifications'):
            require(stage['validation_status'] == 'Passed' and stage['review_status'] == 'Accepted' and stage['freshness'] == 'Current', 'Current input checks must be Passed and adopted.')
    selected = {}
    for node_id in NODE_IDS:
        adopted = latest_passed(envelope['generation']['jobs'], node_id)
        synth = latest_passed(envelope['workflow_runs'], node_id, 'local_synthesis')
        simulation = latest_passed(envelope['workflow_runs'], node_id, 'local_netlist_simulation')
        spec = latest_passed(envelope['implementation_specs'], node_id)
        candidate = unique(generation['jobs'], adopted['id'])
        require(candidate['origin'] == 'local_llm' and candidate['profile']['execution_location'] == 'Local', 'Selected current RTL must be an actually completed local-model candidate: ' + node_id)
        synthesis = unique(workflow['runs'], synth['id'])
        netlist = unique(workflow['runs'], simulation['id'])
        specification = unique(specifications['specs'], spec['id'])
        source = state['snapshots'][candidate['revision_id']]
        require(revision_hashes(source)['semantic_hash'] == state['revision']['semantic_hash'], 'A selected node still uses a previous complete semantic design: ' + node_id)
        require(specification['candidate_id'] == candidate['id'] and specification['source_run_id'] == netlist['id'], 'Latest S07 was derived from different source results: ' + node_id)
        require(synthesis['candidate_id'] == netlist['candidate_id'] == candidate['id'] and netlist['prior_run_id'] == synthesis['id'], 'S04/S05/S06 lineage differs: ' + node_id)
        plan = candidate['verification_plan']
        require(plan == build_verification_plan(source, node_id, verification_template_version(plan)), 'Frozen plan differs from original GUI source: ' + node_id)
        require(plan == synthesis['verification_plan'] == netlist['verification_plan'], 'RTL and netlist use different plans: ' + node_id)
        require(content_hash(candidate['rtl']) == candidate['rtl_sha256'] == synthesis['rtl_sha256'] == netlist['rtl_sha256'], 'RTL hash lineage differs: ' + node_id)
        require(synthesis['netlist'] == netlist['netlist'] and content_hash(netlist['netlist']) == synthesis['netlist_sha256'] == netlist['netlist_sha256'], 'S06 did not verify the exact S05 netlist: ' + node_id)
        rebuilt = build_node_implementation_spec(source, candidate, synthesis, netlist)
        require(rebuilt == specification['specification'] and object_hash(rebuilt) == specification['specification_sha256'], 'S07 reconstruction differs: ' + node_id)
        if node_id == 'node-pe':
            require(object_hash(plan) == object_hash(original_pe['verification_plan']), 'PE verification plan changed; all original 42-cycle vectors/reference/TB and JSON types must remain identical.')
            require(candidate['id'] not in {job['id'] for job in originals['generation.json']['jobs']}, 'Current PE RTL must be regenerated by the local model for this current semantic design; the old adopted candidate is not reused as the new candidate.')
        else:
            require(plan['kind'] == 'npu_scheduler_stream', 'Scheduler needs its own original-job projection plan.')
            require(sum(object_hash(plan['contract']['source_job']) == object_hash(job) for job in design['verification_jobs']) == 1, 'Scheduler projection source is not exactly one canonical saved job, including JSON types.')
        selected[node_id] = {'candidate': candidate, 'synthesis': synthesis, 'netlist': netlist,
                             'spec_record': specification, 'specification': rebuilt,
                             'effective_spec': spec}
    return histories, selected


def node_manifest(node_id, records):
    candidate, synthesis, simulation, spec = [records[key] for key in ('candidate', 'synthesis', 'netlist', 'spec_record')]
    plan = candidate['verification_plan']
    return {'node_id': node_id, 'source_revision_id': candidate['revision_id'], 'candidate_id': candidate['id'],
            'synthesis_run_id': synthesis['id'], 'netlist_run_id': simulation['id'], 'spec_id': spec['id'],
            'rtl_sha256': candidate['rtl_sha256'], 'netlist_sha256': simulation['netlist_sha256'],
            'specification_sha256': spec['specification_sha256'], 'vector_hash': plan['vector_hash'],
            'reference_trace_hash': plan['reference_trace_hash'], 'testbench_sha256': plan['testbench_sha256'],
            'vector_count': plan['vector_count'], 'checked_assertion_count': records['specification']['observed_facts']['checked_assertion_count'],
            'public_port_count': len(records['specification']['public_interface']['ports'])}


def check_gui_operations(directory, selected):
    operations = []
    for folder in sorted(Path(directory).iterdir()):
        if not folder.is_dir() or not (folder / 'gui-actions.json').is_file():
            continue
        action = load(folder / 'gui-actions.json')
        require(action.get('record_kind') == 'actual_project_GUI_operations'
                and action.get('actor') == 'development_assistant_gui_automation'
                and action.get('page_errors') == [], 'Require truthful completed actual GUI actions: ' + folder.name)
        operations.append((folder, action))
    require(bool(operations), 'No completed actual scheduler GUI operation records.')
    require(any(action['phase'] == 'specify' for _, action in operations), 'The actual GUI source specification operation is missing.')
    for node_id, records in selected.items():
        matching = [(folder, action) for folder, action in operations if action.get('node_id') == node_id and action['phase'] in ('implementation-specs', 'observe-implementation-specs')]
        require(bool(matching), 'Actual current S07 GUI operation is missing: ' + node_id)
        folder, _ = matching[-1]
        require(object_hash(load(folder / 'actual-spec-record.json')) == object_hash(records['effective_spec']), 'Saved S07 GUI record differs from the current strict result, including JSON types: ' + node_id)
        require((folder / 'actual-node-implementation-specs.png').is_file(), 'Actual S07 screenshot is missing: ' + node_id)
    return operations


def _wide_integer_rounding_paths(expected, observed, path='$'):
    """Identify known browser precision loss without accepting it as proof."""
    if type(expected) is dict and type(observed) is dict and set(expected) == set(observed):
        paths = []
        for key in expected:
            found = _wide_integer_rounding_paths(expected[key], observed[key], path + '.' + key)
            if found is None:
                return None
            paths.extend(found)
        return paths
    if type(expected) is list and type(observed) is list and len(expected) == len(observed):
        paths = []
        for index, (left, right) in enumerate(zip(expected, observed, strict=True)):
            found = _wide_integer_rounding_paths(left, right, path + '[' + str(index) + ']')
            if found is None:
                return None
            paths.extend(found)
        return paths
    if type(expected) is int and type(observed) is float and abs(expected) > 2 ** 53 and observed == float(expected):
        return [path]
    return [] if type(expected) is type(observed) and expected == observed else None


def gui_snapshot_provenance(operations, selected):
    provenance = []
    latest = {node_id: next(folder for folder, action in reversed(operations)
                            if action.get('node_id') == node_id and action.get('phase') in ('implementation-specs', 'observe-implementation-specs'))
              for node_id in selected}
    for folder, action in operations:
        snapshot = folder / 'actual-spec-record.json'
        if not snapshot.is_file() or action.get('node_id') not in selected:
            continue
        node_id = action['node_id']
        observed, expected = load(snapshot), selected[node_id]['effective_spec']
        exact = object_hash(observed) == object_hash(expected)
        rounding_paths = _wide_integer_rounding_paths(expected, observed)
        require(folder != latest[node_id] or exact, 'Latest selected GUI specification snapshot must remain lossless and authoritative.')
        provenance.append({'file': 'gui_operations/' + folder.name + '/actual-spec-record.json',
                           'node_id': node_id, 'phase': action['phase'],
                           'selected_for_current_proof': folder == latest[node_id],
                           'matches_strict_current_specification_object_hash': exact,
                           'classification': 'lossless_authoritative_current_API_view' if exact else 'non_authoritative_historical_browser_snapshot',
                           'known_JSON_number_rounding': not exact and bool(rounding_paths),
                           'rounded_wide_integer_paths': rounding_paths or [],
                           'preserved_without_modification': True})
    return provenance


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path, default=ROOT / '.work/projects/npu')
    parser.add_argument('--baseline-dir', type=Path, default=ROOT / '.work/m2d/original_runtime')
    parser.add_argument('--gui-operations', type=Path, default=ROOT / '.work/m2d/gui-operations')
    parser.add_argument('--output', type=Path, default=ROOT / 'results/npu_scheduler_continuous_flow')
    args = parser.parse_args()
    if args.output.exists() and any(args.output.iterdir()):
        parser.error('Use a new empty output directory; preserved evidence is never replaced.')
    source_bytes, baseline_bytes = read_histories(args.data_dir), read_histories(args.baseline_dir)
    histories, selected = validate_continuation(args.data_dir, args.baseline_dir)
    operations = check_gui_operations(args.gui_operations, selected)
    snapshot_provenance = gui_snapshot_provenance(operations, selected)
    require(read_histories(args.data_dir) == source_bytes and read_histories(args.baseline_dir) == baseline_bytes, 'Source changed during collection; retry after execution finishes.')
    args.output.mkdir(parents=True, exist_ok=True)
    for name in HISTORIES:
        (args.output / name).write_bytes(source_bytes[name])
        (args.output / 'original_runtime').mkdir(exist_ok=True)
        (args.output / 'original_runtime' / name).write_bytes(baseline_bytes[name])
    write_json(args.output / 'design.json', histories['state.json']['design'])
    nodes = {}
    for node_id, records in selected.items():
        folder = args.output / 'nodes' / node_id
        folder.mkdir(parents=True)
        for key, filename in (('candidate', 'candidate_record.json'), ('synthesis', 'synthesis_record.json'),
                              ('netlist', 'netlist_record.json'), ('spec_record', 'implementation_spec_record.json'),
                              ('specification', 'node_implementation_spec.json')):
            write_json(folder / filename, records[key])
        plan = records['candidate']['verification_plan']
        vectors = plan['expanded_vectors'] if plan['kind'] == 'npu_scheduler_stream' else plan['contract']['vectors']
        for filename, value in (('verification_plan.json', plan), ('reference_trace.json', plan['reference_trace']),
                                ('vectors.json', vectors)):
            write_json(folder / filename, value)
        for filename, value in (('candidate.v', records['candidate']['rtl']), ('netlist.v', records['synthesis']['netlist']), ('contract_tb.v', plan['testbench'])):
            (folder / filename).write_text(value, encoding='utf-8', newline='\n')
        nodes[node_id] = node_manifest(node_id, records)
    copied = []
    for folder, _ in operations:
        destination = args.output / 'gui_operations' / folder.name
        destination.mkdir(parents=True)
        for path in sorted(folder.iterdir()):
            if path.is_file() and (path.suffix.lower() == '.png' or path.name in ('gui-actions.json', 'actual-spec-record.json', 'gui-saved-design.json')):
                shutil.copyfile(path, destination / path.name)
                copied.append((destination / path.name).relative_to(args.output).as_posix())
    files = {path.relative_to(args.output).as_posix(): {'sha256': sha(path), 'bytes': path.stat().st_size}
             for path in sorted(args.output.rglob('*')) if path.is_file()}
    generation, workflow = histories['generation.json'], histories['workflow.json']
    original_generation = load(args.baseline_dir / 'generation.json')
    pe_candidate = selected['node-pe']['candidate']
    over_budget = {name: record['bytes'] for name, record in files.items() if record['bytes'] > 10_000_000}
    manifest = {'record_kind': RECORD_KIND, 'scope': 'two_node_types_in_same_GUI_project_with_PE_verification_contract_preserved_and_PE_RTL_regenerated',
                'project_id': histories['state.json']['design']['project']['id'],
                'current_revision_id': histories['state.json']['revision']['id'],
                'current_design_semantic_hash': histories['state.json']['revision']['semantic_hash'],
                'canonical_job_hash': object_hash(histories['state.json']['design']['verification_jobs']),
                'nodes': nodes, 'historical_generation_attempts': len(generation['jobs']),
                'new_generation_attempts': len(generation['jobs']) - len(original_generation['jobs']),
                'attempts': [{key: job.get(key) for key in ('id', 'node_id', 'revision_id', 'operation', 'base_job_id', 'origin', 'execution_status', 'validation_status', 'review_status')} for job in generation['jobs']],
                'tool_runs': len(workflow['runs']), 'GUI_operator': 'development_assistant_under_explicit_user_instruction',
                'adoption_origin': 'automation_policy_user_preapproved_accept_on_pass',
                'manual_human_reviews': sum(review.get('actor') == 'human' for name, key in (('state.json', 'reviews'), ('generation.json', 'reviews'), ('workflow.json', 'reviews'), ('implementation_specs.json', 'reviews')) for review in histories[name][key]),
                'canonical_job_replaced': False, 'PE_original_42_cycle_plan_identical': True,
                'PE_preserved_scope': 'Original finite 42-cycle verification contract, reference and testbench only; the selected PE candidate is a new local-model result.',
                'PE_candidate_regeneration': {'candidate_id': pe_candidate['id'], 'origin': pe_candidate['origin'],
                                              'operation': pe_candidate['operation'], 'base_job_id': pe_candidate['base_job_id'],
                                              'model': pe_candidate['profile']['model'], 'new_since_baseline': True,
                                              'previous_RTL_used_as_model_repair_input': pe_candidate['operation'] == 'repair',
                                              'manual_RTL_edit': False, 'old_adopted_candidate_reused_as_current_candidate': False},
                'manual_RTL_modifications': [],
                'RTL_and_netlist_use_same_frozen_plan': True,
                'full_NPU_verified': False, 'PDK_mapping': False, 'timing_or_SDF': False,
                'original_runtime_files': {name: hashlib.sha256(value).hexdigest() for name, value in baseline_bytes.items()},
                'gui_operation_files': copied,
                'gui_snapshot_provenance': snapshot_provenance,
                'authoritative_evidence': 'Four raw backend histories, selected raw candidate/tool/spec records and exact lossless latest API observations. Historical rounded browser snapshots are retained but excluded from proof.',
                'file_budget': {'review_threshold_bytes': 10_000_000, 'largest_file_bytes': max(record['bytes'] for record in files.values()),
                                'files_above_review_threshold': over_budget, 'total_preserved_file_bytes': sum(record['bytes'] for record in files.values())},
                'files': files}
    write_json(args.output / 'manifest.json', manifest)
    print(json.dumps({'status': 'Passed', 'nodes': nodes, 'file_budget': manifest['file_budget'], 'output': str(args.output)}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
