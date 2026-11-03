"""Pure/stub-only qualified MOSCAP recipe tests. Never starts an EDA process."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import struct
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / filename)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def record(kind, value=b'', datatype=0):
    value += b'\0' if len(value) % 2 else b''
    return struct.pack('>HBB', len(value) + 4, kind, datatype) + value


def shape(points, layer=1):
    return (record(8) + record(13, struct.pack('>h', layer), 2)
            + record(14, b'\0\0', 2)
            + record(16, struct.pack('>' + 'i' * (len(points) * 2), *(v for p in points for v in p)), 3)
            + record(17))


def text(label='VGND', point=(0, 0)):
    return (record(12) + record(13, b'\0\1', 2) + record(22, b'\0\0', 2)
            + record(16, struct.pack('>ii', *point), 3) + record(25, label.encode(), 6) + record(17))


def reference(name):
    return record(10) + record(18, name.encode(), 6) + record(16, struct.pack('>ii', 0, 0), 3) + record(17)


def gds(cells, unit=bytes.fromhex('3944b82fa09b5a54')):
    return (record(0, b'\0\x03', 2) + record(1, bytes(24), 2) + record(2, b'fixture', 6)
            + record(3, bytes.fromhex('3e4189374bc6a7f0') + unit, 5)
            + b''.join(record(5, bytes(24), 2) + record(6, name.encode(), 6) + body + record(7)
                       for name, body in cells) + record(4))


CAP_SHAPE = shape([(0, 0), (20, 0), (20, 30), (0, 30), (0, 0)]) + text()
REFERENCE_SPICE = b'''.subckt sky130_fd_sc_hd__decap_3 VGND VNB VPB VPWR
X0 VPWR VGND VPWR VPB sky130_fd_pr__pfet_01v8_hvt w=870000u l=590000u
X1 VGND VPWR VGND VNB sky130_fd_pr__nfet_01v8 w=550000u l=590000u
.ends sky130_fd_sc_hd__decap_3
'''
RAW_SPICE = b'''.subckt sky130_fd_sc_hd__decap_3 VGND VNB VPB VPWR
X0 VPWR VGND VPB hullcirq_moscap_pfet_v5 w=0.87 l=0.59
X1 VGND VPWR VNB hullcirq_moscap_nfet_v5 w=0.55 l=0.59
.ends sky130_fd_sc_hd__decap_3
'''
BASE_TECH = b'''tech
 sky130A
end
extract
 style ngspice variants (),(orig),(si),(hrhc),(lrhc),(hrlc),(lrlc)
device msubcircuit sky130_fd_pr__nfet_01v8 nfet,scnfet \\
\t*ndiff,ndiffres *ndiff,ndiffres
device msubcircuit sky130_fd_pr__pfet_01v8_hvt pfethvt,scpfethvt \\
\t*pdiff,pdiffres *pdiff,pdiffres
end
'''


class MoscapRecipeTests(unittest.TestCase):
    def setUp(self):
        self.helper = module('moscap_qa_helper', 'lvs_moscap_v5.py')
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / 'execution'
        self.root.mkdir()
        self.vendor = gds([(self.helper.CELL, CAP_SHAPE)])
        self.input = gds([(self.helper.CELL, CAP_SHAPE), ('ordinary', shape([(0, 0), (3, 0), (3, 3), (0, 0)])),
                          ('arbitrary_top', reference(self.helper.CELL) + reference('ordinary'))])
        for key, raw in [('BASE_TECH_SHA', BASE_TECH), ('LIBRARY_GDS_SHA', self.vendor), ('LIBRARY_SPICE_SHA', REFERENCE_SPICE)]:
            self.addCleanup(patch.stopall)
            patch.object(self.helper, key, self.helper.digest(raw)).start()
        self.profile = json.loads((ROOT / 'configs/lvs_profile_sky130_v5.json').read_text())

    def write(self, relative, raw):
        target = self.root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)

    def complete_fixture(self):
        h = self.helper
        self.write('input.gds', self.input)
        self.write('config.json', h.json_bytes({'DESIGN_NAME': 'arbitrary_top'}))
        self.write('input-manifest.json', h.json_bytes({'configuration': {'profile': self.profile}}))
        for key, raw in [('base_tech', BASE_TECH), ('reference_gds', self.vendor), ('reference_spice', REFERENCE_SPICE),
                         ('derived_tech', h.derived_tech(BASE_TECH)), ('wrappers', (ROOT / 'scripts/lvs_moscap_models_v5.spice').read_bytes())]:
            self.write(h.FILES[key], raw)
        self.plan = h.make_plan(self.input, self.vendor, REFERENCE_SPICE, 'arbitrary_top')
        self.write(h.FILES['plan'], h.json_bytes(self.plan))
        self.write(h.FILES['plan_tcl'], h._plan_tcl(self.plan))
        baseline = self.inventory('pre_gds', source=False)
        after = self.inventory('post_gds')
        annotated = self.inventory('post_annotation')
        for value in (baseline, after, annotated):
            self.write(h._inventory_path(self.root, value['phase']).name, h.json_bytes(value))
        args = []
        for row in self.plan['cells']:
            args.extend([row['name'], row['style'], row['name'], '0', '0'])
            self.write('runs/lvs/1-magic-spiceextraction/extraction/' + row['name'] + '.ext',
                       ('timestamp 1\nstyle ' + row['style'] + '\n').encode())
        h.record_execution(self.root, args)
        self.write(h.FILES['raw_spice'], RAW_SPICE)
        h.finalize(self.root)
        self.layout = {'checks': {'artifacts': [{'id': 'gds', 'sha256': h.digest(self.input), 'bytes': len(self.input)}]}}

    def inventory(self, phase, source=True):
        h = self.helper
        plan = h.make_plan(self.input, self.vendor, REFERENCE_SPICE, 'arbitrary_top')
        rows = [{'name': '(UNNAMED)', 'flags': ['available'], 'children': [],
                 'paint_type_count': 0, 'label_count': 0, 'selected_instance_count': 0}]
        if source:
            rows += [{'name': row['name'], 'flags': ['available', 'modified'],
                      'children': plan['source_children'][row['name']],
                      'paint_type_count': -1, 'label_count': -1, 'selected_instance_count': -1}
                     for row in plan['cells']]
        return {'schema': h.INVENTORY_SCHEMA, 'phase': phase, 'cells': sorted(rows, key=lambda row: row['name'])}

    def test_inventory_keeps_empty_initial_definition_without_waiving_source_or_unknown_geometry(self):
        h = self.helper
        plan = h.make_plan(self.input, self.vendor, REFERENCE_SPICE, 'arbitrary_top')
        baseline, after = self.inventory('pre_gds', False), self.inventory('post_gds')
        self.assertEqual(h.validate_inventory(baseline, plan)['preexisting_empty_definition_count'], 1)
        self.assertEqual(h.validate_inventory(after, plan, baseline)['source_definition_count'], 3)
        self.assertEqual(h.validate_inventory(self.inventory('post_annotation'), plan, baseline, after)['definition_count'], 4)
        # No cell name is privileged: a painted initial (UNNAMED) is rejected.
        for count_key in ('paint_type_count', 'label_count', 'selected_instance_count'):
            changed = json.loads(json.dumps(after))
            changed['cells'][0][count_key] = 1
            with self.subTest(count_key=count_key), self.assertRaisesRegex(ValueError, 'actual geometry'):
                h.validate_inventory(changed, plan, baseline)

    def test_inventory_missing_source_unknown_definition_changed_graph_and_annotation_changes_fail(self):
        h = self.helper
        plan = h.make_plan(self.input, self.vendor, REFERENCE_SPICE, 'arbitrary_top')
        baseline, after = self.inventory('pre_gds', False), self.inventory('post_gds')
        mutations = []
        missing = json.loads(json.dumps(after)); missing['cells'].pop(); mutations.append(missing)
        unexpected = json.loads(json.dumps(after))
        unexpected['cells'].append({**unexpected['cells'][0], 'name': 'unplanned_pdk_cell'})
        unexpected['cells'].sort(key=lambda row: row['name']); mutations.append(unexpected)
        graph = json.loads(json.dumps(after))
        next(row for row in graph['cells'] if row['name'] == 'arbitrary_top')['children'] = []
        mutations.append(graph)
        duplicate = json.loads(json.dumps(after)); duplicate['cells'].insert(0, duplicate['cells'][0]); mutations.append(duplicate)
        for changed in mutations:
            with self.assertRaises(ValueError):
                h.validate_inventory(changed, plan, baseline)
        altered = self.inventory('post_annotation'); altered['cells'].pop(0)
        with self.assertRaisesRegex(ValueError, 'annotation changed'):
            h.validate_inventory(altered, plan, baseline, after)

    def test_inventory_records_failure_observations_before_fail_closed(self):
        h = self.helper
        plan = h.make_plan(self.input, self.vendor, REFERENCE_SPICE, 'arbitrary_top')
        self.write(h.FILES['plan'], h.json_bytes(plan))
        args = ['(UNNAMED)', '1', 'available', '0', '1', '0', '0']
        with self.assertRaisesRegex(ValueError, 'actual geometry'):
            h.record_inventory(self.root, 'pre_gds', args)
        retained = h.load(h._inventory_path(self.root, 'pre_gds'))
        self.assertEqual(retained['cells'][0]['paint_type_count'], 1)

    def test_all_three_inventory_hashes_are_reconstructed_and_relocated_without_writes(self):
        self.complete_fixture()
        result = self.helper.validate_retained_model_proof(self.root, self.layout, self.profile)
        self.assertEqual([row['phase'] for row in result['native_source_inventory']], list(self.helper.INVENTORY_PHASES))
        for phase in self.helper.INVENTORY_PHASES:
            path = self.helper._inventory_path(self.root, phase)
            original = path.read_bytes()
            value = self.helper.load(path)
            value['cells'][0]['label_count'] = 1
            path.write_bytes(self.helper.json_bytes(value))
            with self.subTest(phase=phase), self.assertRaises(ValueError):
                self.helper.validate_retained_model_proof(self.root, self.layout, self.profile)
            path.write_bytes(original)

    def test_inventory_filename_phase_binding_rejects_swapped_and_empty_post_documents(self):
        self.complete_fixture()
        h = self.helper
        for phase in ('post_gds', 'post_annotation'):
            path = h._inventory_path(self.root, phase)
            original = path.read_bytes()
            for crafted in ({'schema': h.INVENTORY_SCHEMA, 'phase': 'pre_gds', 'cells': []},
                            self.inventory('pre_gds', source=False)):
                path.write_bytes(h.json_bytes(crafted))
                with self.subTest(phase=phase), self.assertRaisesRegex(ValueError, 'filename/phase'):
                    h._proof(self.root, self.layout, self.profile)
            path.write_bytes(original)
        before = h._inventory_path(self.root, 'pre_gds')
        before.write_bytes(h.json_bytes(self.inventory('post_gds')))
        with self.assertRaisesRegex(ValueError, 'filename/phase'):
            h._proof(self.root, self.layout, self.profile)

    def test_exact_rational_unit_never_rounds_subpicometre_changes(self):
        h = self.helper
        raw = bytes.fromhex('3944b82fa09b5a54')
        self.assertNotEqual(h._unit_picometres(raw), 1000)
        changed_unit = (int.from_bytes(raw, 'big') + 1).to_bytes(8, 'big')
        first = h.gds_cells(self.vendor)[h.CELL]['geometry_sha256']
        changed = h.gds_cells(gds([(h.CELL, CAP_SHAPE)], changed_unit))[h.CELL]['geometry_sha256']
        self.assertNotEqual(first, changed)

    def test_full_geometry_canonicalization_accepts_ring_rotation_not_contact_or_label_mutation(self):
        h = self.helper
        rotated = shape([(20, 30), (20, 0), (0, 0), (0, 30), (20, 30)]) + text()
        self.assertEqual(h.gds_cells(self.vendor)[h.CELL]['geometry_sha256'],
                         h.gds_cells(gds([(h.CELL, rotated)]))[h.CELL]['geometry_sha256'])
        for geometry in (CAP_SHAPE + shape([(1, 1), (2, 1), (2, 2), (1, 1)], layer=7),
                         CAP_SHAPE.replace(b'VGND', b'VPWR')):
            changed = gds([(h.CELL, geometry), ('arbitrary_top', reference(h.CELL))])
            with self.assertRaisesRegex(ValueError, 'full geometry/labels'):
                h.make_plan(changed, self.vendor, REFERENCE_SPICE, 'arbitrary_top')

    def test_discovery_is_children_first_complete_and_arbitrary_top_not_project_specific(self):
        plan = self.helper.make_plan(self.input, self.vendor, REFERENCE_SPICE, 'arbitrary_top')
        self.assertEqual(plan['definition_count'], 3)
        self.assertEqual(plan['qualified_instance_uses'], 1)
        self.assertEqual(plan['cells'][-1]['name'], 'arbitrary_top')
        self.assertEqual(sum(r['style'] != 'ngspice()' for r in plan['cells']), 1)
        for altered in (gds([(self.helper.CELL, CAP_SHAPE), ('arbitrary_top', reference('missing'))]),
                        self.input[:-4] + record(5, bytes(24), 2) + record(6, b'unreachable', 6) + CAP_SHAPE + record(7) + record(4)):
            with self.assertRaises(ValueError):
                self.helper.make_plan(altered, self.vendor, REFERENCE_SPICE, 'arbitrary_top')

    def test_derived_style_preserves_every_original_byte_and_only_two_qualified_rules_change(self):
        h = self.helper
        derived = h.derived_tech(BASE_TECH)
        inserted = derived[len(BASE_TECH) - len(b'end\n'):]
        self.assertTrue(derived.startswith(BASE_TECH[:-len(b'end\n')]))
        self.assertEqual(derived.count(b'device msubcircuit sky130_fd_pr__nfet_01v8 '), 1)
        self.assertEqual(derived.count(b'device msubcircuit hullcirq_moscap_nfet_v5 '), 1)
        self.assertIn(b'nfet,scnfet 1 \\\n\t*ndiff,ndiffres', inserted)
        self.assertNotIn(b'*ndiff,ndiffres *ndiff,ndiffres', inserted)
        with self.assertRaisesRegex(ValueError, 'base PDK'):
            h.derived_tech(BASE_TECH + b'\n')

    def test_exact_original_devices_model_graph_width_length_and_numeric_encoding(self):
        h = self.helper
        self.assertEqual(h.cap_devices(REFERENCE_SPICE.decode()), h.cap_devices(RAW_SPICE.decode(), True))
        for changed in (RAW_SPICE.replace(b'w=0.55', b'w=0.56'), RAW_SPICE.replace(b'VPB hullcirq', b'VNB hullcirq'),
                        RAW_SPICE.replace(b'w=0.55', b'w={0.55}'), RAW_SPICE.replace(b'l=0.59', b'l=0'),
                        RAW_SPICE + RAW_SPICE):
            with self.assertRaises(ValueError):
                if h.cap_devices(changed.decode(), True) != h.cap_devices(REFERENCE_SPICE.decode()):
                    raise ValueError('model graph changed')

    def test_wrapper_keeps_original_four_terminal_model_and_all_extracted_parameters(self):
        text_value = (ROOT / 'scripts/lvs_moscap_models_v5.spice').read_text()
        for alias, model_name in self.helper.MODELS.items():
            self.assertIn('.subckt ' + alias + ' SD G B w=0 l=0 as=0 ps=0 ad=0 pd=0', text_value)
            self.assertIn('X0 SD G SD B ' + model_name + ' w={w} l={l} as={as} ps={ps} ad={ad} pd={pd}', text_value)
        self.assertNotIn('.include', text_value)

    def test_retained_complete_proof_is_pure_and_returns_integration_status(self):
        self.complete_fixture()
        before = {p.relative_to(self.root): (p.read_bytes(), p.stat().st_mtime_ns) for p in self.root.rglob('*') if p.is_file()}
        result = self.helper.validate_retained_model_proof(self.root, self.layout, self.profile)
        self.assertEqual(result['validation_status'], 'Passed')
        self.assertEqual(result['definition_count'], 3)
        self.assertEqual(before, {p.relative_to(self.root): (p.read_bytes(), p.stat().st_mtime_ns) for p in self.root.rglob('*') if p.is_file()})

    def test_archival_read_root_keeps_original_logical_include_and_rejects_arbitrary_include(self):
        self.complete_fixture()
        copy = self.root.parent / 'archived_copy'
        shutil.copytree(self.root, copy)
        self.assertEqual(self.helper.validate_retained_model_proof(copy, self.layout, self.profile, logical_root=self.root)['validation_status'], 'Passed')
        with self.assertRaisesRegex(ValueError, 'include-plus-raw'):
            self.helper.validate_retained_model_proof(copy, self.layout, self.profile)
        path = copy / self.helper.FILES['comparison_spice']
        path.write_bytes(path.read_bytes().replace(b'.include', b'.incLude', 1))
        with self.assertRaises(ValueError):
            self.helper.validate_retained_model_proof(copy, self.layout, self.profile, logical_root=self.root)

    def test_alias_leakage_ordinary_style_incomplete_ext_feedback_and_model_tampering_fail(self):
        self.complete_fixture()
        cases = [
            ('runs/lvs/1-magic-spiceextraction/extraction/ordinary.ext', b'\nstyle ngspice()\nhullcirq_moscap_nfet_v5\n'),
            ('runs/lvs/1-magic-spiceextraction/extraction/ordinary.ext', b'\nstyle hullcirq_moscap_v5()\n'),
            (self.helper.FILES['raw_spice'], RAW_SPICE.replace(b'w=0.55', b'w=0.56')),
            (self.helper.FILES['wrappers'], b'* discarded all devices\n'),
            (self.helper.FILES['derived_tech'], BASE_TECH),
        ]
        for relative, changed in cases:
            path = self.root / relative
            original = path.read_bytes()
            path.write_bytes(changed)
            with self.subTest(relative=relative), self.assertRaises(ValueError):
                self.helper.validate_retained_model_proof(self.root, self.layout, self.profile)
            path.write_bytes(original)
        path = self.root / 'runs/lvs/1-magic-spiceextraction/extraction/ordinary.ext'
        path.unlink()
        with self.assertRaises(ValueError):
            self.helper.validate_retained_model_proof(self.root, self.layout, self.profile)

    def test_feedback_monotonic_and_exact_plan_execution_never_clears_warnings(self):
        h = self.helper
        plan = h.make_plan(self.input, self.vendor, REFERENCE_SPICE, 'arbitrary_top')
        self.write(h.FILES['plan'], h.json_bytes(plan))
        args = [v for row in plan['cells'] for v in (row['name'], row['style'], row['name'], '0', '0')]
        for changed in (args[:-5], args[:-1] + ['-1'], args[:3] + ['1'] + args[4:],
                        args[:4] + ['2'] + args[5:], args[:2] + ['wrong_selected_cell'] + args[3:]):
            with self.assertRaises(ValueError):
                h.record_execution(self.root, changed)
        self.assertFalse((self.root / h.FILES['execution_log']).exists())

    def test_retained_selection_identity_cannot_be_missing_or_point_at_another_cell(self):
        self.complete_fixture()
        h = self.helper
        path = self.root / h.FILES['execution_log']
        original = path.read_bytes()
        for selected in (None, 'different_definition'):
            value = h.load(path)
            value['cells'][0]['selected_cell'] = selected
            path.write_bytes(h.json_bytes(value))
            with self.assertRaisesRegex(ValueError, 'cell execution/style/feedback'):
                h._proof(self.root, self.layout, self.profile)
            path.write_bytes(original)

    def test_prepare_copies_only_hash_pinned_vendor_inputs_into_separate_run(self):
        h = self.helper
        pdk = self.root.parent / 'pdk'
        sources = {'libs.tech/magic/sky130A.tech': BASE_TECH, h.LIBRARY_GDS: self.vendor, h.LIBRARY_SPICE: REFERENCE_SPICE}
        for relative, raw in sources.items():
            target = pdk / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        self.write('input.gds', self.input)
        self.write('config.json', h.json_bytes({'DESIGN_NAME': 'arbitrary_top'}))
        self.write('input-manifest.json', h.json_bytes({'configuration': {'profile': self.profile}}))
        self.write('pdk-input-manifest.json', h.json_bytes({'root': str(pdk), 'files': {k: {'sha256': h.digest(v)} for k, v in sources.items()}}))
        before = {p.relative_to(pdk): (p.read_bytes(), p.stat().st_mtime_ns) for p in pdk.rglob('*') if p.is_file()}
        self.assertEqual(h.prepare(self.root)['definition_count'], 3)
        self.assertEqual(before, {p.relative_to(pdk): (p.read_bytes(), p.stat().st_mtime_ns) for p in pdk.rglob('*') if p.is_file()})
        with self.assertRaises(FileExistsError):
            h.prepare(self.root)

    def test_tcl_requires_fixed_loaded_cells_original_normal_style_no_feedback_suppression(self):
        source = (ROOT / 'scripts/extract_spice_moscap_v5.tcl').read_text()
        self.assertLess(source.index('tech load'), source.index('gds read'))
        self.assertIn('extract cell $hullcirq_cell', source)
        iteration = source.split('foreach hullcirq_row $hullcirq_cell_plan {', 1)[1]
        self.assertLess(iteration.index('load $hullcirq_cell'), iteration.index('extract style $hullcirq_style'))
        self.assertLess(iteration.index('extract style $hullcirq_style'), iteration.index('select top cell'))
        self.assertLess(iteration.index('select top cell'), iteration.index('set hullcirq_selected [cellname list self]'))
        self.assertLess(iteration.index('set hullcirq_selected [cellname list self]'), iteration.index('extract cell $hullcirq_cell'))
        self.assertIn('[cellname list allcells]', source)
        self.assertIn('extract style $hullcirq_style', source)
        self.assertIn('extract style ngspice()', source)
        self.assertIn('feedback save', source)
        self.assertIn('select do labels', source)
        self.assertLess(source.index('hullcirq_record_inventory pre_gds'), source.index('gds read'))
        self.assertLess(source.index('gds read'), source.index('hullcirq_record_inventory post_gds'))
        self.assertLess(source.index('read_pdk_spice'), source.index('hullcirq_record_inventory post_annotation'))
        for forbidden in ('feedback clear', 'extract warn no', 'flatten ', 'save ', 'writeall'):
            if forbidden == 'save ':
                continue
            self.assertNotIn(forbidden, source)

    def test_profile_source_pins_and_old_recipe_bytes_are_not_rewritten(self):
        profile = self.profile
        self.assertEqual(profile['profile_version'], 'hullcirq-sky130-lvs-v5')
        variant, recognition = profile['extraction_variant'], profile['terminal_recognition_variant']
        for key, declaration in [('script', variant), ('launcher', variant), ('helper', recognition), ('wrapper', recognition)]:
            self.assertEqual(self.helper.digest((ROOT / declaration[key + '_path']).read_bytes()), declaration[key + '_sha256'])
        old = json.loads((ROOT / 'configs/lvs_profile_sky130_v2.json').read_text())
        self.assertEqual(profile['config'], old['config'])
        self.assertEqual(variant['upstream_sha256'], old['extraction_variant']['upstream_sha256'])
        self.assertNotEqual(variant['script_path'], old['extraction_variant']['script_path'])


class MoscapLauncherTests(unittest.TestCase):
    def setUp(self):
        self.launcher = module('moscap_qa_launcher', 'run_moscap_lvs_v5.py')
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.profile = json.loads((ROOT / 'configs/lvs_profile_sky130_v5.json').read_text())
        for declaration, names in [(self.profile['extraction_variant'], ['script', 'launcher']),
                                   (self.profile['terminal_recognition_variant'], ['helper', 'wrapper'])]:
            for name in names:
                source = ROOT / declaration[name + '_path']
                (self.root / source.name).write_bytes(source.read_bytes())
        # Test the fixed launcher with a harmless mock helper; never call prepare on real inputs.
        helper = self.root / 'lvs_moscap_v5.py'
        helper.write_bytes(b'def prepare(root):\n    return None\n')
        import hashlib
        self.profile['terminal_recognition_variant']['helper_sha256'] = hashlib.sha256(helper.read_bytes()).hexdigest()
        (self.root / 'input-manifest.json').write_text(json.dumps({'configuration': {'profile': self.profile}}), encoding='utf-8')
        upstream = (ROOT / 'scripts/extract_spice_full.tcl').read_bytes().replace(b'\nextract all\n', b'\nextract\n', 1)
        self.upstream = self.root / 'upstream.tcl'
        self.upstream.write_bytes(upstream)
        upstream_path = self.upstream
        class Extraction:
            id = 'Magic.SpiceExtraction'
            def get_script_path(self):
                return str(upstream_path)
        self.extraction = Extraction
        self.original = Extraction.get_script_path
        self.cli = Mock(return_value=7)
        magic, entry = types.ModuleType('librelane.steps.magic'), types.ModuleType('librelane.__main__')
        magic.SpiceExtraction, entry.cli = Extraction, self.cli
        self.addCleanup(patch.stopall)
        patch.dict(sys.modules, {'librelane.steps.magic': magic, 'librelane.__main__': entry}).start()
        patch.object(self.launcher.importlib.metadata, 'version', return_value='3.0.16').start()
        patch.object(self.launcher, '__file__', str(self.root / 'run_moscap_lvs_v5.py')).start()

    def test_banner_fixed_args_exit_and_method_restore(self):
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(self.launcher.main(['--run-tag', 'lvs']), 7)
        self.cli.assert_called_once_with(args=['--run-tag', 'lvs'])
        self.assertIs(self.extraction.get_script_path, self.original)
        value = json.loads(output.getvalue().split('HuLLCirq MOSCAP extraction launcher: ', 1)[1])
        self.assertEqual(set(value), {'librelane', 'entrypoint', 'step', 'profile_version', 'upstream_script_sha256',
                                     'script', 'script_sha256', 'helper_sha256', 'wrapper_sha256', 'qualified_cell',
                                     'added_abstract_cells', 'added_ignore_rules'})
        self.assertEqual(value['added_ignore_rules'], 0)
        self.assertEqual(value['added_abstract_cells'], 0)

    def test_changed_upstream_staged_inputs_or_runtime_fail_before_cli(self):
        for filename in ('upstream.tcl', 'extract_spice_moscap_v5.tcl', 'lvs_moscap_v5.py', 'lvs_moscap_models_v5.spice'):
            target = self.root / filename
            original = target.read_bytes()
            target.write_bytes(original + b'changed')
            with self.subTest(filename=filename), self.assertRaises(RuntimeError):
                self.launcher.main([])
            target.write_bytes(original)
        with patch.object(self.launcher.importlib.metadata, 'version', return_value='other'):
            with self.assertRaises(RuntimeError):
                self.launcher.main([])
        self.cli.assert_not_called()
        self.assertIs(self.extraction.get_script_path, self.original)


if __name__ == '__main__':
    unittest.main()
