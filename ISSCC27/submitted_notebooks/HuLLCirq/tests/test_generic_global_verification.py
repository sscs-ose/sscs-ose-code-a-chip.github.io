"""Non-NPU source/prompt/command/proof fixtures; no model or EDA execution."""
import copy
from pathlib import Path
import sys
import threading
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from hullcirq import generic_global_verification as generic, global_generation as generation, global_workflow as workflow
from hullcirq import postroute_generic, postroute_tools
from hullcirq.domain import DomainError, revision_hashes, validate_shape
from hullcirq.context import node_fingerprint
from hullcirq.verification import content_hash, object_hash
from hullcirq.workspace import blank_design


def design_fixture():
    design = blank_design('project-software-generic', 'Software generic', 'system-software-generic', 'Software generic', 'byte_pipeline')
    # This fixture exercises the retained pre-external-I/O generic route.
    design.pop('external_io', None)
    design.update({'settings': {**design['settings'], 'top_module': 'byte_pipeline', 'clock_name': 'clock_i', 'reset_name': 'reset_i',
                        'clock_period_ns': 50, 'reset_active': 'low', 'reset_kind': 'synchronous', 'rtl_language': 'verilog_2005'},
            'nodes': [{'id': 'stage-a', 'module_name': 'byte_xor', 'ports': []},
                      {'id': 'stage-b', 'module_name': 'byte_rotate', 'ports': []}], 'edges': [],
            'global_integration': {'behavior': 'Connect the two adopted transform modules as a byte pipeline.',
                                   'public_ports': [{'name': 'data_i', 'direction': 'input', 'width': 8, 'signed': False},
                                                    {'name': 'data_o', 'direction': 'output', 'width': 8, 'signed': False}]},
            'global_verification': {'kind': 'generic_cycle_vectors', 'version': 1, 'cycles': [
                {'reset': 1, 'drive': {'data_i': 0}, 'expect': {'data_o': 0}},
                {'reset': 0, 'drive': {'data_i': 173}, 'expect': {'data_o': 42}}]}})
    for node in design['nodes']:
        node.update(name=node['id'], behavior='Independent SOFTWARE QA node specification.',
                    test_expectations='Independent SOFTWARE QA saved requirements.', parent_id=None,
                    constraints={'latency_cycles': 1, 'protocol': 'valid_ready'})
    return design


def manifest_fixture(design=None):
    design = design or design_fixture()
    nodes = []
    for node in design['nodes']:
        rtl = 'module ' + node['module_name'] + '; endmodule // SOFTWARE QA ONLY\n'
        nodes.append({'node_id': node['id'], 'module_name': node['module_name'], 'rtl': rtl,
                      'rtl_sha256': content_hash(rtl), 'public_interface': {'module_name': node['module_name'], 'ports': []}})
    return {'design': design, 'nodes': nodes}


def scope_fixture(manifest):
    tb = generation.build_global_plan(manifest['design'])['testbench_module']
    lines = [f'S_0 .scope module, "{tb}" "{tb}";',
             'S_1 .scope module, "dut" "byte_pipeline" S_0;']
    for index, node in enumerate(manifest['nodes'], 2):
        lines.append(f'S_{index} .scope module, "u{index}" "{node["module_name"]}" S_1;')
    return lines


def transcript(plan):
    lines = [f'HULLCIRQ_CYCLE cycle={i} signal={name} value={value & ((1 << next(p["width"] for p in plan["interface"]["ports"] if p["name"] == name))-1):x}'
             for i, row in enumerate(plan['contract']['cycles']) for name, value in row['expect'].items()]
    return '\n'.join(lines + [f'HULLCIRQ_PASS vectors={plan["vector_count"]} vector_hash={plan["vector_hash"]}'])


class GenericGlobalTests(unittest.TestCase):
    def test_blank_workspace_source_manifest_does_not_require_legacy_matrix_jobs(self):
        design = design_fixture(); validate_shape(design)
        revision = {'id': 'software-revision', **revision_hashes(design)}
        current = {'design': design, 'revision': revision}
        jobs, runs, specs, candidate_reviews, run_reviews, spec_reviews = [], [], [], [], [], []
        for node in design['nodes']:
            node_id = node['id']; common = {'node_id': node_id, 'revision_id': revision['id'],
                'input_hash': node_fingerprint(design, node_id), 'execution_status': 'Completed',
                'validation_status': 'Passed', 'review_status': 'Accepted', 'acceptance_epoch': 1}
            candidate = {**common, 'id': node_id+'-candidate', 'rtl': '// SOFTWARE QA ONLY', 'rtl_sha256': content_hash('// SOFTWARE QA ONLY')}
            synthesis = {**common, 'id': node_id+'-synthesis', 'stage_id': 'local_synthesis', 'candidate_id': candidate['id']}
            netlist = {**common, 'id': node_id+'-netlist', 'stage_id': 'local_netlist_simulation',
                       'candidate_id': candidate['id'], 'prior_run_id': synthesis['id']}
            candidate_review = {'job_id': candidate['id'], 'decision': 'accepted'}
            synthesis_review = {'run_id': synthesis['id'], 'decision': 'accepted'}
            netlist_review = {'run_id': netlist['id'], 'decision': 'accepted'}
            spec = {**common, 'id': node_id+'-spec', 'candidate_id': candidate['id'], 'source_run_id': netlist['id'],
                'design_hash': revision['semantic_hash'],
                'specification': {'lineage': {'synthesis_run_id': synthesis['id']}, 'original_requirements': {'verification_jobs': []}},
                'source_adoptions': [{'kind': kind, 'review': review} for kind, review in
                    [('candidate', candidate_review), ('synthesis', synthesis_review), ('netlist_simulation', netlist_review)]]}
            spec['specification_sha256'] = object_hash(spec['specification'])
            jobs.append(candidate); runs.extend([synthesis, netlist]); specs.append(spec)
            candidate_reviews.append(candidate_review); run_reviews.extend([synthesis_review, netlist_review])
            spec_reviews.append({'spec_id': spec['id'], 'decision': 'accepted'})
        epochs = {node['id']: 1 for node in design['nodes']}
        manager = generation.GlobalGenerationManager.__new__(generation.GlobalGenerationManager)
        manager.lock = threading.RLock(); manager._manifest_stamp = None; manager._manifest_cache = None
        manager.store = SimpleNamespace(snapshot=lambda identifier: copy.deepcopy(design))
        manager.generation = SimpleNamespace(_state={'jobs': jobs, 'node_epochs': epochs, 'reviews': candidate_reviews},
            _stored_job=lambda identifier: next(j for j in jobs if j['id'] == identifier))
        manager.workflow = SimpleNamespace(_state={'runs': runs, 'node_epochs': epochs, 'reviews': run_reviews},
            _run=lambda identifier: next(r for r in runs if r['id'] == identifier))
        manager.specifications = SimpleNamespace(_state={'specs': specs, 'node_epochs': epochs, 'reviews': spec_reviews})
        manifest = manager._source_manifest_locked(current, design, {s['node_id']: s for s in specs}, generation.required_node_ids(design))
        self.assertEqual(manifest['canonical_job_hash'], object_hash(design['global_verification']))
        self.assertNotIn('verification_jobs', manifest['design'])
        self.assertEqual([node['node_id'] for node in manifest['nodes']], ['stage-a', 'stage-b'])
        self.assertEqual(manifest['design'], design)

    def test_explicit_contract_uses_all_saved_node_ids_not_name_allowlist(self):
        design = design_fixture()
        self.assertEqual(generation.required_node_ids(design), ('stage-a', 'stage-b'))
        design['nodes'][0]['id'] = 'arbitrary_component_73'
        self.assertEqual(generation.required_node_ids(design)[0], 'arbitrary_component_73')
        design.pop('global_verification')
        with self.assertRaises(DomainError): generation.required_node_ids(design)

    def test_public_interface_clock_polarity_expected_values_and_plan_rebuild(self):
        design = design_fixture(); before = copy.deepcopy(design)
        plan = generation.build_global_plan(design)
        self.assertEqual(plan['kind'], 'generic_cycle_vectors')
        self.assertEqual(plan['interface']['reset']['active'], 'low')
        self.assertEqual(plan['interface']['clock'], {'port': 'clock_i', 'period_ns': 50})
        generation.validate_global_plan(design, plan)
        self.assertEqual(design, before)
        self.assertNotIn('verification_jobs', design)
        self.assertEqual(generation.canonical_job_hash(design), object_hash(design['global_verification']))
        changed = copy.deepcopy(plan); changed['contract']['cycles'][1]['expect']['data_o'] = 43
        with self.assertRaises(DomainError): generation.validate_global_plan(design, changed)

    def test_invalid_ports_missing_expected_values_and_array_shape_fail_closed(self):
        for mutate in [lambda d: d['global_integration']['public_ports'][0].update(name='clock_i'),
                       lambda d: d['global_verification']['cycles'][1]['expect'].clear(),
                       lambda d: d['nodes'][0].update(instance_array={'rows': True, 'columns': 2}),
                       lambda d: d['nodes'][0].update(id='../outside')]:
            design = design_fixture(); mutate(design)
            with self.assertRaises(DomainError): generation.build_global_plan(design)

    def test_generic_array_counts_come_from_saved_declaration(self):
        design = design_fixture(); design['nodes'][0]['instance_array'] = {'rows': 2, 'columns': 3}
        self.assertEqual(generation.expected_instance_counts(manifest_fixture(design)), {'stage-a': 6, 'stage-b': 1})

    def test_prompt_preserves_behavior_interfaces_edges_and_no_builtin_algorithm(self):
        manifest = manifest_fixture(); messages = generation.integration_messages(manifest, 'Keep every handshake.')
        self.assertEqual(generation.prompt_template(manifest['design']), generic.PROMPT)
        source = messages[-1]['content']
        self.assertIn('byte_pipeline', source); self.assertIn('byte_xor', source)
        self.assertIn('Connect the two adopted transform modules', source)
        self.assertIn('Keep every handshake.', source)
        self.assertNotIn('matrix', source); self.assertNotIn('configuration_word', source)
        self.assertNotIn('"expect"', source); self.assertNotIn('173', source)

    def test_source_bundle_and_commands_keep_all_original_sources_and_correct_tb(self):
        manifest = manifest_fixture(); top = 'module byte_pipeline; endmodule // SOFTWARE QA ONLY'
        bundle = workflow.source_bundle(top, manifest)
        self.assertEqual([entry['file'] for entry in bundle], ['candidate_top.v', 'stage-a.v', 'stage-b.v'])
        parent = ROOT / '.work/qa/generic-command-fixture'
        compiler = {'kind': 'native', 'executable': str(ROOT / '.work/qa/fixed-tools/iverilog.exe'), 'working_directory': str(parent)}
        commands = generation.fixed_global_commands(compiler, manifest, parent / 'hullcirq-global-fixture')
        plan = generation.build_global_plan(manifest['design'])
        self.assertIn(plan['testbench_module'], commands[1])
        netlist_commands = workflow.fixed_global_netlist_commands(compiler, parent / 'hullcirq-global-netlist-fixture', plan)
        self.assertIn(plan['testbench_module'], netlist_commands[1])
        self.assertNotIn('stage-a.v', ' '.join(netlist_commands[1]))

    def test_compiler_scope_text_ancestry_counts_and_external_only_instrumentation(self):
        manifest = manifest_fixture(); scope = scope_fixture(manifest)
        self.assertEqual(generation.compiler_public_hierarchy(scope, manifest), {'stage-a': ['dut.u2'], 'stage-b': ['dut.u3']})
        self.assertEqual(workflow.compiler_netlist_public_hierarchy(scope, manifest), {'stage-a': ['dut.u2'], 'stage-b': ['dut.u3']})
        with self.assertRaises(DomainError): generation.compiler_public_hierarchy(scope[:-1], manifest)
        with self.assertRaises(DomainError): generation.compiler_public_hierarchy([*scope, scope[-1]], manifest)
        plan = generation.build_global_plan(manifest['design'])
        tb, monitor = generation.instrument_public_testbench(plan, {})
        self.assertEqual(tb, plan['testbench']); self.assertIn('no internal behavioral coverage claim', monitor)

    def test_same_generic_runtime_records_fail_on_wrong_missing_or_unknown_output(self):
        plan = generation.build_global_plan(design_fixture()); source = transcript(plan)
        self.assertTrue(generation.parse_runtime_records(source, plan)[0])
        self.assertEqual(generation.public_transfer_counts(plan), {})
        self.assertEqual(generation.expected_pe_records(plan), [])
        for invalid in [source.replace('value=2a', 'value=2b'), source.replace('value=2a', 'value=x'),
                        source.replace('HULLCIRQ_CYCLE cycle=1 signal=data_o value=2a', ''), source+'\nHULLCIRQ_FAIL']:
            self.assertFalse(generation.parse_runtime_records(invalid, plan)[0])

    def test_s14_generic_plan_keeps_exact_original_tb_and_uses_common_parser(self):
        design = design_fixture(); plan = generation.build_global_plan(design); settings = design['settings']
        contract = postroute_generic.derive_contract(plan, settings)
        self.assertEqual(contract, {'version': postroute_generic.CYCLE_VERSION})
        binding = postroute_generic.binding(plan, settings, contract)
        configuration = {'profile_version': postroute_tools.PROFILE_V4, 'functional_adapter': binding}
        layout = {'verification_plan': plan, 'settings': settings}
        adapted = postroute_tools._testbench(layout, configuration)
        recording = adapted.index('  initial begin\n    $display("HULLCIRQ_ROUTED_FUNCTIONAL_NO_SDF")')
        restored = adapted[:recording] + adapted[adapted.index('endmodule', recording):]
        self.assertEqual(restored, plan['testbench'])
        self.assertIn(("'-s', '" + plan['testbench_module'] + "'").encode(), postroute_tools._launcher(configuration))
        source = 'HULLCIRQ_ROUTED_FUNCTIONAL_NO_SDF\n' + transcript(plan)
        self.assertEqual(postroute_tools._functional_report(source, layout, configuration)['validation_status'], 'Passed')
        self.assertEqual(postroute_tools._functional_report(transcript(plan), layout, configuration)['validation_status'], 'Failed')
        for diagnostic in ('ERROR: cell model', 'FATAL: simulator'):
            self.assertEqual(postroute_tools._functional_report(source+'\n'+diagnostic, layout, configuration)['validation_status'], 'Failed')
        self.assertEqual(postroute_tools._functional_report(source+'\nWARNING: software fixture', layout, configuration)['validation_status'], 'Passed')
        with self.assertRaises(DomainError): postroute_generic.validate_contract(plan, {**settings, 'clock_period_ns': 100}, contract)

    def test_generic_s08_strict_proof_rebuild_rejects_forged_source_command_sample_and_scope(self):
        manifest = manifest_fixture(); plan = generation.build_global_plan(manifest['design'])
        parent = ROOT / '.work/qa/generic-command-fixture'
        compiler = {'kind': 'native', 'executable': str(ROOT / '.work/qa/fixed-tools/iverilog.exe'), 'working_directory': str(parent)}
        folder = parent / 'hullcirq-global-fixture'
        source = transcript(plan)
        commands = [{'command': command, 'executed': True, 'status': 'Completed', 'exit_code': 0,
                     'stdout': source if i == 3 else '', 'stderr': ''}
                    for i, command in enumerate(generation.fixed_global_commands(compiler, manifest, folder))]
        scope = scope_fixture(manifest); locations = generation.compiler_public_hierarchy(scope, manifest)
        tb, monitor = generation.instrument_public_testbench(plan, locations)
        records = generation.parse_runtime_records(source, plan)[1]
        rtl = 'module byte_pipeline(input clock_i,input reset_i,input [7:0] data_i,output [7:0] data_o); endmodule // SOFTWARE QA ONLY'
        proof = {'validation_status': 'Passed', 'executed': True, 'exit_code': 0, 'commands': commands,
                 'tool_configuration': compiler, 'artifacts_directory': str(folder), 'stdout': source, 'stderr': '',
                 'rtl_sha256': content_hash(rtl), 'source_manifest_sha256': object_hash(manifest),
                 'verification_profile': generic.KIND, 'signal_sample_count': 2, 'expected_signal_samples': 2,
                 'vector_hash': plan['vector_hash'], 'testbench_sha256': plan['testbench_sha256'],
                 'public_boundary_vector_hash': plan['public_boundary_vector_hash'],
                 'public_port_hierarchy': locations, 'hierarchy_scope_lines': scope, 'hierarchy_scope_sha256': object_hash(scope),
                 'public_monitor_source': monitor, 'public_monitor_sha256': content_hash(monitor),
                 'instrumented_testbench_sha256': content_hash(tb), 'elaborated_instance_counts': {'stage-a': 1, 'stage-b': 1},
                 'actual_output_transfers': records, 'actual_public_stream_transfers': [], 'actual_pe_lane_transfers': [],
                 'checks': {key: {'validation_status': 'Passed'} for key in ('interface', 'elaboration', 'functional', 'public_boundary')}}
        job = {'rtl': rtl, 'context': {'source_manifest': manifest, 'verification_plan': plan, 'tool_configuration': compiler}, 'checks': proof}
        self.assertTrue(generation.GlobalGenerationManager._passed(job))
        for mutate in [lambda j: j['checks'].update(source_manifest_sha256='0'*64),
                       lambda j: j['checks']['commands'][3].update(stdout=source.replace('value=2a', 'value=2b')),
                       lambda j: j['checks']['commands'][1]['command'].append('unexpected.v'),
                       lambda j: j['checks'].update(stdout=source+'\nforged'),
                       lambda j: j['checks']['actual_output_transfers'][1].update(value=0),
                       lambda j: j['checks'].update(hierarchy_scope_lines=scope[:-1]),
                       lambda j: j['checks'].update(signal_sample_count=True)]:
            bad = copy.deepcopy(job); mutate(bad)
            self.assertFalse(generation.GlobalGenerationManager._passed(bad))


if __name__ == '__main__': unittest.main()
