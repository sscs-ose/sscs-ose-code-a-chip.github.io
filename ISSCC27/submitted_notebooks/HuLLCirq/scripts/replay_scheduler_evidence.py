"""Replay preserved scheduler/PE RTL and identical plans, then rebuild S07.

No model invocation and no replacement vectors. Generic Yosys/Icarus replay is
functional evidence only, without PDK mapping, delays or complete NPU execution.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from collect_scheduler_evidence import (HISTORIES, NODE_IDS, RECORD_KIND, ROOT,
                                        check_gui_operations, gui_snapshot_provenance, node_manifest, require, validate_continuation)
from node_spec_evidence import load, sha, verify_files, write_json
from hullcirq.context import physical_interface
from hullcirq.implementation_specs import build_node_implementation_spec
from hullcirq.rtl_checks import check_rtl
from hullcirq.store import strict_loads
from hullcirq.verification import object_hash, verify_behavior
from hullcirq.workflow import synthesize_generic


def load_runtime(path):
    # PowerShell-written private runtime configs may have a UTF-8 BOM. Evidence
    # JSON remains strict UTF-8 under the common saved-history loader.
    return strict_loads(Path(path).read_text(encoding='utf-8-sig'))


def inspect_evidence(directory):
    directory = Path(directory)
    manifest = load(directory / 'manifest.json')
    require(manifest.get('record_kind') == RECORD_KIND, 'Use the actual preserved scheduler/PE continuation manifest.')
    verify_files(directory, manifest['files'])
    mandatory = {'design.json', *(name for name in HISTORIES), *('original_runtime/' + name for name in HISTORIES)}
    mandatory |= {f'nodes/{node_id}/{filename}' for node_id in NODE_IDS for filename in (
        'candidate_record.json', 'synthesis_record.json', 'netlist_record.json', 'implementation_spec_record.json',
        'node_implementation_spec.json', 'verification_plan.json', 'reference_trace.json', 'vectors.json', 'candidate.v', 'netlist.v', 'contract_tb.v')}
    require(mandatory.issubset(manifest['files']), 'Manifest omitted a required history or selected proof artifact.')
    require(set(manifest['nodes']) == set(NODE_IDS), 'Both scheduler and unchanged PE must be represented.')
    histories, selected = validate_continuation(directory, directory / 'original_runtime')
    operations = check_gui_operations(directory / 'gui_operations', selected)
    require(object_hash(manifest['gui_snapshot_provenance']) == object_hash(gui_snapshot_provenance(operations, selected)), 'GUI snapshot authority/rounding provenance differs from strict reconstructed classification.')
    gui_files = {path.relative_to(directory).as_posix() for folder, _ in operations for path in folder.iterdir() if path.is_file()}
    require(gui_files == set(manifest['gui_operation_files']) and gui_files.issubset(manifest['files']), 'Actual GUI operation files differ from the preserved manifest.')
    state = histories['state.json']
    require(object_hash(load(directory / 'design.json')) == object_hash(state['design']), 'Saved design differs from the strict current GUI history, including JSON types.')
    require(manifest['project_id'] == state['design']['project']['id']
            and manifest['current_revision_id'] == state['revision']['id']
            and manifest['current_design_semantic_hash'] == state['revision']['semantic_hash']
            and manifest['canonical_job_hash'] == object_hash(state['design']['verification_jobs']), 'Manifest source identity differs from the actual saved project.')
    for name, checksum in manifest['original_runtime_files'].items():
        require(name in HISTORIES and sha(directory / 'original_runtime' / name) == checksum, 'Original baseline differs: ' + name)
    require(set(manifest['original_runtime_files']) == set(HISTORIES), 'Original baseline must contain all four histories.')
    for node_id, records in selected.items():
        require(manifest['nodes'][node_id] == node_manifest(node_id, records), 'Node manifest has mixed artifact identity: ' + node_id)
        folder = directory / 'nodes' / node_id
        for key, filename in (('candidate', 'candidate_record.json'), ('synthesis', 'synthesis_record.json'),
                              ('netlist', 'netlist_record.json'), ('spec_record', 'implementation_spec_record.json'),
                              ('specification', 'node_implementation_spec.json')):
            require(object_hash(load(folder / filename)) == object_hash(records[key]), 'Selected artifact differs from its strict full history, including JSON types: ' + node_id + '/' + filename)
        plan = records['candidate']['verification_plan']
        vectors = plan['expanded_vectors'] if plan['kind'] == 'npu_scheduler_stream' else plan['contract']['vectors']
        require(object_hash(load(folder / 'verification_plan.json')) == object_hash(plan)
                and object_hash(load(folder / 'reference_trace.json')) == object_hash(plan['reference_trace'])
                and object_hash(load(folder / 'vectors.json')) == object_hash(vectors), 'Exported frozen inputs differ, including JSON types: ' + node_id)
        for filename, expected in (('candidate.v', records['candidate']['rtl']), ('netlist.v', records['synthesis']['netlist']), ('contract_tb.v', plan['testbench'])):
            require((folder / filename).read_text(encoding='utf-8') == expected, 'Exported Verilog differs from source proof: ' + node_id + '/' + filename)
    return manifest, histories, selected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, default=ROOT / 'results/npu_scheduler_continuous_flow')
    parser.add_argument('--compiler-config', type=Path, default=ROOT / '.work/m2/compiler.json')
    parser.add_argument('--synthesizer-config', type=Path, default=ROOT / '.work/m2b/synthesizer.json')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() and any(args.output.iterdir()):
        parser.error('Use a new empty output directory to preserve previous replays.')
    manifest, histories, selected = inspect_evidence(args.evidence)
    compiler, synthesizer = load_runtime(args.compiler_config), load_runtime(args.synthesizer_config)
    args.output.mkdir(parents=True, exist_ok=True)
    results = {}
    passed = True
    for node_id, records in selected.items():
        candidate, synthesis_record, simulation_record = [records[key] for key in ('candidate', 'synthesis', 'netlist')]
        design = histories['state.json']['snapshots'][candidate['revision_id']]
        node = next(item for item in design['nodes'] if item['id'] == node_id)
        plan = candidate['verification_plan']
        folder = args.output / node_id
        folder.mkdir()
        candidate_checks = check_rtl(candidate['rtl'], physical_interface(design, node), node['module_name'], compiler)
        behavior = verify_behavior(candidate['rtl'], plan, compiler, folder / 'rtl')
        synthesis = synthesize_generic(candidate['rtl'], node['module_name'], synthesizer, folder / 'synthesis')
        netlist = verify_behavior(synthesis['netlist'], plan, compiler, folder / 'netlist') if synthesis.get('validation_status') == 'Passed' and synthesis.get('netlist') else None
        rebuilt_spec = build_node_implementation_spec(design, candidate, synthesis_record, simulation_record)
        identical_netlist = synthesis.get('netlist_sha256') == manifest['nodes'][node_id]['netlist_sha256']
        identical_spec = rebuilt_spec == records['specification'] and object_hash(rebuilt_spec) == manifest['nodes'][node_id]['specification_sha256']
        node_pass = candidate_checks['validation_status'] == 'Passed' and all(item and item.get('validation_status') == 'Passed' for item in (behavior, synthesis, netlist)) and identical_netlist and identical_spec
        passed = passed and node_pass
        write_json(folder / 'rebuilt_node_implementation_spec.json', rebuilt_spec)
        report = {'node_id': node_id, 'validation_status': 'Passed' if node_pass else 'Failed',
                  'source_revision_id': candidate['revision_id'], 'candidate_id': candidate['id'],
                  'vector_hash': plan['vector_hash'], 'reference_trace_hash': plan['reference_trace_hash'],
                  'testbench_sha256': plan['testbench_sha256'], 'vector_count': plan['vector_count'],
                  'candidate_checks': candidate_checks, 'RTL_behavior': behavior,
                  'generic_synthesis': synthesis, 'netlist_behavior': netlist,
                  'replayed_netlist_byte_identical': identical_netlist,
                  'S07_original_saved_evidence_reconstruction_identical': identical_spec,
                  'S07_new_tool_results_not_substituted_into_original_record': True,
                  'specification_sha256': object_hash(rebuilt_spec)}
        write_json(folder / 'report.json', report)
        results[node_id] = {key: report[key] for key in ('validation_status', 'vector_count', 'vector_hash', 'testbench_sha256', 'replayed_netlist_byte_identical', 'S07_original_saved_evidence_reconstruction_identical')}
    final = {'record_kind': 'actual_saved_scheduler_and_PE_artifact_replay', 'validation_status': 'Passed' if passed else 'Failed',
             'source_evidence_manifest_sha256': sha(args.evidence / 'manifest.json'),
             'source_revision_id': manifest['current_revision_id'], 'nodes': results,
             'LLM_calls': 0, 'replacement_vectors': False, 'manual_RTL_modifications': [],
             'PE_original_42_cycle_plan_identical': True, 'full_NPU_verified': False,
             'PDK_mapping': False, 'SDF': False}
    write_json(args.output / 'report.json', final)
    print(json.dumps({**final, 'report': str(args.output / 'report.json')}, ensure_ascii=False))
    return 0 if passed else 2


if __name__ == '__main__':
    raise SystemExit(main())
