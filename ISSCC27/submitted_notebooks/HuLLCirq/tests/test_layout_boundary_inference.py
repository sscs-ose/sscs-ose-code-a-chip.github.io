"""Checked boundary graph fixtures, never circuit/model/native execution."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tests')]
from hullcirq import layout_roles as roles
from hullcirq.verification import content_hash
from test_external_io_generation import fixture, rtl_fixture


def graph_fixture():
    manifest = fixture(array=True)
    node = manifest['nodes'][0]
    def declaration(p):
        return p['direction'] + (f" [{p['width']-1}:0]" if p['width'] > 1 else '') + ' ' + p['name']
    node['rtl'] = 'module fixture_scalar(' + ','.join(declaration(p) for p in node['public_interface']['ports']) + '); endmodule\n'
    node['rtl_sha256'] = content_hash(node['rtl'])
    top = rtl_fixture(manifest, aliases=True)
    bundle = [{'file': 'candidate_top.v', 'module_name': 'fixture_top', 'sha256': content_hash(top)},
              {'file': node['node_id'] + '.v', 'module_name': node['module_name'], 'sha256': node['rtl_sha256']}]
    context = roles.generic_role_context('fixture_top', bundle, manifest, top)
    ports, nets, cells, bits = {}, {}, {}, 2
    for p in context['boundary_inference']['ports']:
        ids = list(range(bits, bits + p['width'])); bits += p['width']
        ports[p['name']] = {'direction': p['direction'], 'bits': ids, 'signed': int(p['signed'])}
        nets[p['name']] = {'bits': ids, 'hide_name': 0}
    source = next(p['name'] for p in context['boundary_inference']['ports'] if p['direction'] == 'input' and p['width'] > 1)
    for p in context['boundary_inference']['ports']:
        if p['direction'] != 'output': continue
        for bit in ports[p['name']]['bits']:
            name = 'anonymous_' + str(len(cells))
            cells[name] = {'type': 'sky130_fd_sc_hd__buf_1', 'connections': {'A': [ports[source]['bits'][0]], 'X': [bit]},
                           'port_directions': {'A': 'input', 'X': 'output'},
                           'attributes': {'src': node['node_id'] + '.v:1.1-1.100'}}
    module = {'ports': ports, 'netnames': nets, 'cells': cells}
    return manifest, top, bundle, context, module


def structural(module):
    _, labels = roles._json_graph(module)
    names = {bit: min(value) for bit, value in labels.items()}
    lines = ['module fixture_top(' + ','.join(module['ports']) + ');']
    for name, port in module['ports'].items():
        lines.append(port['direction'] + (f" [{len(port['bits'])-1}:0]" if len(port['bits']) > 1 else '') + ' ' + name + ';')
    for bit in {b[0] for c in module['cells'].values() for b in c['connections'].values()}:
        if bit not in names: names[bit] = 'internal_' + str(bit); lines.append('wire ' + names[bit] + ';')
    for name, cell in module['cells'].items():
        lines.append(cell['type'] + ' ' + name + '(' + ','.join('.'+p+'('+names[b[0]]+')' for p,b in cell['connections'].items()) + ');')
    return '\n'.join(lines + ['endmodule\n'])


class BoundaryInferenceTests(unittest.TestCase):
    def annotate(self, module, context, final=None):
        synthesis = roles.parse_structural_verilog(structural(module))
        final = final or synthesis
        return roles.annotate_cells(module, synthesis, final, {n: c['master'] for n,c in final['cells'].items()},
                                    roles.GENERIC_ROLE_PROFILE, 'changed_family_unknown_v1', context)

    def test_shared_definition_without_member_names_uses_checked_output_bits(self):
        _, _, _, context, module = graph_fixture()
        self.assertFalse(any(i['path'] in json.dumps(module) for i in context['instances']))
        cells, summary = self.annotate(module, context)
        self.assertEqual(summary['by_role'], {i['id']: 6 for i in context['instances']})
        self.assertEqual(summary['by_status'], {'source_and_connectivity': 12})
        self.assertTrue(all(any(e['kind'] == 'checked_external_output_dependency_anchor' for e in c['evidence']) for c in cells))
        self.assertFalse(any(c['status'] == 'source_confirmed' for c in cells))

    def test_old_context_keeps_exact_unknown_behavior(self):
        _, _, _, context, module = graph_fixture(); context.pop('boundary_inference')
        cells, summary = self.annotate(module, context)
        self.assertEqual(summary['by_role'], {'unknown': 12})
        self.assertNotIn('checked_boundary_inference', summary)

    def test_bad_source_wiring_or_definition_interface_never_creates_boundary_proof(self):
        manifest, top, bundle, _, _ = graph_fixture()
        for candidate in [top.replace('.clock_x(clock_x)', '.clock_x(reset_x)'), top.replace('endmodule', 'always @(*) begin end endmodule')]:
            self.assertNotIn('boundary_inference', roles.generic_role_context('fixture_top', bundle, manifest, candidate))
        manifest['nodes'][0]['public_interface']['ports'][0]['width'] = 2
        self.assertNotIn('boundary_inference', roles.generic_role_context('fixture_top', bundle, manifest, top))

    def test_mapped_port_type_and_bit_substitution_are_rejected(self):
        _, _, _, context, module = graph_fixture()
        name = next(p for p,v in module['ports'].items() if v['direction'] == 'output')
        for mutate in ['type', 'bits']:
            changed = copy.deepcopy(module)
            if mutate == 'type': changed['ports'][name]['direction'] = 'input'
            else: changed['ports'][name]['bits'] = [999] * len(changed['ports'][name]['bits'])
            with self.assertRaisesRegex(roles.LayoutRoleError, 'Mapped top port'):
                self.annotate(changed, context)

    def test_duplicate_driver_is_unknown_not_arbitrarily_selected(self):
        _, _, _, context, module = graph_fixture()
        module['cells']['second_driver'] = copy.deepcopy(module['cells']['anonymous_0'])
        cells, summary = self.annotate(module, context)
        self.assertEqual({c['id'] for c in cells if c['role'] == 'unknown'}, {'anonymous_0', 'second_driver'})
        self.assertEqual(summary['checked_boundary_inference']['withheld_output_bits_without_unique_eligible_driver'], 1)

    def test_shared_cone_is_shared_and_sequential_input_is_a_boundary(self):
        _, _, _, context, module = graph_fixture()
        for c in module['cells'].values(): c['attributes'] = {}
        first, last = module['cells']['anonymous_0'], module['cells']['anonymous_6']
        shared = 999; old_input = first['connections']['A'][0]
        first['connections']['A'] = [shared]; last['connections']['A'] = [shared]
        module['cells']['common'] = {'type':'sky130_fd_sc_hd__buf_1','connections':{'A':[old_input],'X':[shared]},'port_directions':{'A':'input','X':'output'}}
        cells, _ = self.annotate(module, context)
        self.assertEqual(next(c for c in cells if c['id']=='common')['role'], 'shared')
        module['cells']['common']['type'] = 'sky130_fd_sc_hd__dfxtp_1'
        cells, _ = self.annotate(module, context)
        self.assertEqual(next(c for c in cells if c['id']=='common')['role'], 'unknown')

    def test_changed_family_remains_unknown(self):
        _, _, _, context, module = graph_fixture()
        final = roles.parse_structural_verilog(structural(module))
        final['cells']['anonymous_0']['master'] = 'other_function_1'
        cells, _ = self.annotate(module, context, final)
        self.assertEqual(next(c for c in cells if c['id']=='anonymous_0')['role'], 'unknown')

    def test_malformed_or_relabelled_boundary_context_is_rejected(self):
        _, _, _, context, module = graph_fixture()
        for mode in ['hash', 'member', 'duplicate', 'width']:
            bad = copy.deepcopy(context); proof = bad['boundary_inference']
            if mode == 'hash': proof['wiring_proof_sha256'] = 'not-a-digest'
            elif mode == 'member': proof['connections'][0]['role'] = 'instance:unretained'
            elif mode == 'duplicate': proof['connections'].append(copy.deepcopy(proof['connections'][0]))
            else: proof['connections'][0]['width'] += 1
            with self.subTest(mode=mode), self.assertRaises(roles.LayoutRoleError):
                self.annotate(module, bad)

    def test_rehashed_archive_cannot_forge_source_bound_member_connections(self):
        manifest, top, bundle, context, module = graph_fixture()
        with tempfile.TemporaryDirectory(dir=ROOT/'.work/qa') as tmp:
            root = Path(tmp); archive = root/'results/boundary_fixture'; archive.mkdir(parents=True)
            layout_id = 'physical-workflow-' + '1'*32
            record = {'id':layout_id,'global_rtl':top,'source_manifest':manifest,'checks':{'source_bundle':bundle}}
            files = {'artifacts/candidate_top.v':top.encode(), 'artifacts/'+manifest['nodes'][0]['node_id']+'.v':manifest['nodes'][0]['rtl'].encode(),
                     'artifacts/synthesis.json':json.dumps({'modules':{'fixture_top':module}}).encode(),
                     'artifacts/synthesis.v':structural(module).encode(),'artifacts/final.v':structural(module).encode(),
                     'artifacts/final.def':('COMPONENTS 12 ;\n'+'\n'.join('- '+n+' '+c['type']+' ;' for n,c in module['cells'].items())+'\nEND COMPONENTS\n').encode(),
                     'layout_record.json':json.dumps(record).encode()}
            profile = {'source_root':'results/boundary_fixture','source_manifest_sha256':'0'*64,'layout_run_id':layout_id,
                       'inputs':{'synthesis_json':'artifacts/synthesis.json','synthesis_verilog':'artifacts/synthesis.v','final_verilog':'artifacts/final.v','final_def':'artifacts/final.def'},
                       'expected_final_cells':12,'expected_synthesis_cells':12,'gds_relative_path':'unused.gds','role_profile':roles.GENERIC_ROLE_PROFILE,
                       'annotation_policy':'changed_family_unknown_v1','role_context':context}
            def publish():
                files['source_binding.json'] = json.dumps({'role_context':context}).encode()
                for rel,raw in files.items():
                    p=archive/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
                raw=json.dumps({'validation_status':'Passed','layout_run_id':layout_id,'files':{k:{'sha256':hashlib.sha256(v).hexdigest(),'bytes':len(v)} for k,v in files.items()}}).encode()
                (archive/'manifest.json').write_bytes(raw);profile['source_manifest_sha256']=hashlib.sha256(raw).hexdigest()
            publish();result=roles.collect_layout_roles(root, profile)
            self.assertEqual(result['summary']['by_status'], {'source_and_connectivity':12})
            context['boundary_inference']['connections'][0]['role'] = context['instances'][-1]['id']
            publish()
            with self.assertRaisesRegex(roles.LayoutRoleError, 'exact retained source reconstruction'):
                roles.collect_layout_roles(root, profile)


if __name__ == '__main__': unittest.main()
