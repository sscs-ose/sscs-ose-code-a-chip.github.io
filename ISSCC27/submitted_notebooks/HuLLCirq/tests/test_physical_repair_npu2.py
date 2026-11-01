"""Fixed NPU2 repair preparation QA; no live project or EDA is used."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from hullcirq import physical_repair as repair
from hullcirq.domain import DomainError
from hullcirq.physical_tools import configuration_projection, fixed_commands, sha
from hullcirq.verification import content_hash, object_hash, _wsl_path
import test_physical_tools as original_qa


class Npu2RepairTests(unittest.TestCase):
    def setUp(self):
        base = original_qa.PhysicalToolTests()
        base.setUp()
        self.config = base.config
        self.config['pdk_root'] = str(ROOT / '.work/software-fixture/pdks')
        self.settings = {**base.settings, 'top_module': 'hullcirq_npu2_top'}
        self.manifest = {'nodes': [{'node_id': 'npu2-' + name} for name in (
            'control', 'buffer', 'scheduler', 'dispatcher', 'pe00', 'pe01',
            'pe10', 'pe11', 'collector', 'post', 'fifo')]}
        self.profile = json.loads((ROOT / 'configs/physical_profile_sky130_repair_npu2v1.json').read_text(encoding='utf-8'))

    def npu2_config(self):
        value = copy.deepcopy(self.config)
        value.update(profile=self.profile, repair_source_binding=copy.deepcopy(repair.NPU2_SOURCE_BINDING),
                     resume={'initial_state_path': str(ROOT / '.work/fixture/state.json'),
                             'initial_state_sha256': repair.NPU2_STATE_SHA,
                             'source_input_manifest_path': str(ROOT / '.work/fixture/input-manifest.json'),
                             'source_input_manifest_sha256': repair.NPU2_INPUT_SHA,
                             'from_step': repair.START_STEP})
        return value

    def test_new_version_keeps_original_signoff_and_uses_new_CTS(self):
        old = json.loads((ROOT / 'configs/physical_profile_sky130_repair_v6.json').read_text(encoding='utf-8'))
        self.assertEqual(self.profile['config'], old['config'])
        config = self.npu2_config()
        projected = configuration_projection(self.settings, config, self.manifest)
        self.assertEqual(len(projected['VERILOG_FILES']), 12)
        self.assertEqual(projected['DESIGN_NAME'], 'hullcirq_npu2_top')
        self.assertEqual(projected['CLOCK_PERIOD'], 50)
        self.assertEqual(projected['STA_CORNERS'], self.config['profile']['config']['STA_CORNERS'])
        self.assertEqual(projected['SIGNOFF_SDC_FILE'], 'dir::physical.sdc')
        self.assertEqual(projected['PNR_SDC_FILE'], 'dir::physical_pnr.sdc')
        command = fixed_commands(config, Path(config['working_directory']) / 'hullcirq-layout-fixture')[1]
        self.assertEqual(command[command.index('--from') + 1], 'OpenROAD.CTS')
        self.assertEqual(command[command.index('--flow') + 1], 'HuLLCirqRouteClosureV5')
        self.assertEqual(repair.implementation_kind(config), 'resumed_pre_CTS_route_repair')
        self.assertEqual(sha(ROOT / 'scripts/route_closure_v5.py'), repair.V5_LAUNCHER_SHA)

    def test_old_checkpoint_or_changed_binding_cannot_enter_new_version(self):
        for field, value in (('initial_state_sha256', repair.STATE_SHA),
                             ('source_input_manifest_sha256', repair.INPUT_SHA),
                             ('from_step', 'OpenROAD.RepairDesignPostGRT')):
            config = self.npu2_config()
            config['resume'][field] = value
            with self.subTest(field=field), self.assertRaises(DomainError):
                configuration_projection(self.settings, config, self.manifest)
        config = self.npu2_config()
        config['repair_source_binding']['layout_run_id'] = 'another-layout'
        with self.assertRaises(DomainError):
            configuration_projection(self.settings, config, self.manifest)

    def fixture(self, task_root):
        from hullcirq import physical_tools
        config_dir = task_root / 'configs'
        config_dir.mkdir()
        for name in ('physical_profile_sky130.json', 'physical_profile_sky130_repair_npu2v1.json'):
            (config_dir / name).write_bytes((ROOT / 'configs' / name).read_bytes())
        source = task_root / '.work/original/hullcirq-layout-fixture'
        source.mkdir(parents=True)
        runtime = copy.deepcopy(self.config)
        runtime.update(appimage_path=str(task_root / '.work/runtime/librelane-devshell-x86_64.AppImage'),
                       executable=_wsl_path(task_root / '.work/runtime/librelane-devshell-x86_64.AppImage'),
                       working_directory=str(source.parent))
        rtl = 'module hullcirq_npu2_top; endmodule\n'
        bundle = {'software_fixture': True, 'node_count': 11}
        inputs = source / 'input-manifest.json'
        inputs.write_text(json.dumps({'settings': self.settings, 'runtime_configuration': runtime,
                                     'global_rtl_sha256': content_hash(rtl),
                                     'source_manifest_sha256': object_hash(self.manifest),
                                     'source_bundle': bundle}), encoding='utf-8')
        view = source / 'placement.odb'
        view.write_bytes(b'SOFTWARE QA checkpoint view, not a physical result')
        state = source / repair.NPU2_CHECKPOINT
        state.parent.mkdir(parents=True)
        state.write_text(json.dumps({'odb': _wsl_path(view), 'metrics': {'raw_tool_value': float('inf')}}), encoding='utf-8')
        layout = {'id': repair.NPU2_SOURCE_BINDING['layout_run_id'], 'stage_id': 'layout',
                  'execution_status': 'Completed', 'validation_status': 'Passed', 'review_status': 'Accepted',
                  'evidence_kind': 'trusted_fixed_tool_execution', 'revision_id': 'fixture-revision',
                  'global_job_id': 'fixture-job', 'global_rtl': rtl, 'global_rtl_sha256': content_hash(rtl),
                  'source_manifest': self.manifest, 'source_manifest_sha256': object_hash(self.manifest),
                  'settings': self.settings, 'settings_sha256': object_hash(self.settings),
                  'verification_plan_sha256': 'fixture-plan', 'runtime_configuration': runtime,
                  'runtime_configuration_sha256': object_hash(runtime),
                  'checks': {'artifacts_directory': str(source),
                             'artifacts': [{'id': 'input-manifest', 'relative_path': 'input-manifest.json',
                                            'sha256': sha(inputs), 'bytes': inputs.stat().st_size}],
                             'retained_files': [{'relative_path': repair.NPU2_CHECKPOINT,
                                                 'sha256': sha(state), 'bytes': state.stat().st_size}]}}
        layout['record_hash'] = object_hash(layout)
        binding = {key: layout[key] for key in ('revision_id', 'global_job_id', 'global_rtl_sha256',
                                                'source_manifest_sha256', 'settings_sha256', 'verification_plan_sha256')}
        binding.update(layout_run_id=layout['id'], layout_record_sha256=layout['record_hash'],
                       original_runtime_configuration_sha256=object_hash(runtime),
                       checkpoint_view_hash_origin=repair.NPU2_SOURCE_BINDING['checkpoint_view_hash_origin'])
        self.addCleanup(patch.stopall)
        patch.object(physical_tools, 'ROOT', task_root).start()
        patch.object(repair, 'NPU2_STATE_SHA', sha(state)).start()
        patch.object(repair, 'NPU2_INPUT_SHA', sha(inputs)).start()
        patch.object(repair, 'NPU2_SOURCE_BINDING', binding).start()
        patch('hullcirq.global_workflow.source_bundle', return_value=bundle).start()
        return layout, source, state, inputs, view

    def test_preparation_is_read_only_and_copy_is_relocation_only(self):
        with tempfile.TemporaryDirectory() as temporary:
            task_root = Path(temporary)
            layout, source, state, inputs, view = self.fixture(task_root)
            original = copy.deepcopy(layout)
            originals = [path.read_bytes() for path in (state, inputs, view)]
            destination = task_root / '.work/managed/repair'
            prepared = repair.prepare_npu2_configuration(layout, destination)
            self.assertFalse(destination.exists())
            self.assertEqual(layout, original)
            self.assertEqual([path.read_bytes() for path in (state, inputs, view)], originals)
            self.assertEqual(prepared['resume']['initial_state_path'], str(state.resolve()))
            self.assertEqual(prepared['repair_source_binding']['layout_record_sha256'], layout['record_hash'])
            self.assertEqual(prepared['repair_source_binding']['checkpoint_view_hash_origin'],
                             'observed_at_repair_snapshot_not_original_S11_retained_hash')
            copy_folder = task_root / '.work/copied-run'
            copy_folder.mkdir()
            repair.snapshot_resume(prepared, copy_folder, layout['global_rtl'], self.manifest, self.settings)
            self.assertEqual((copy_folder / 'resume-files/placement.odb').read_bytes(), originals[2])
            repair.validate_resume(prepared, copy_folder, layout['global_rtl'], self.manifest, self.settings)
            (copy_folder / 'resume-files/placement.odb').write_bytes(b'changed')
            with self.assertRaises(DomainError):
                repair.validate_resume(prepared, copy_folder, layout['global_rtl'], self.manifest, self.settings)

    def test_different_record_stale_source_and_unsafe_destination_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            task_root = Path(temporary)
            layout, source, *_ = self.fixture(task_root)
            destination = task_root / '.work/managed/repair'
            for field, value in (('id', 'another-layout'), ('freshness', 'Stale'),
                                 ('record_hash', '0' * 64), ('review_status', 'Changes Requested'),
                                 ('global_rtl', 'module changed; endmodule'),
                                 ('source_manifest_sha256', '0' * 64)):
                changed = copy.deepcopy(layout)
                changed[field] = value
                with self.subTest(field=field), self.assertRaises(DomainError):
                    repair.prepare_npu2_configuration(changed, destination)
            for invalid in (source, source / 'new-repair', task_root / 'outside-work', 'relative/path'):
                with self.subTest(destination=invalid), self.assertRaises(DomainError):
                    repair.prepare_npu2_configuration(layout, invalid)

    def test_changed_checkpoint_and_input_bytes_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            task_root = Path(temporary)
            layout, _, state, inputs, _ = self.fixture(task_root)
            for path in (state, inputs):
                raw = path.read_bytes()
                path.write_bytes(raw + b'\n')
                with self.subTest(path=path), self.assertRaises(DomainError):
                    repair.prepare_npu2_configuration(layout, task_root / '.work/managed/repair')
                path.write_bytes(raw)

    def test_missing_checkpoint_view_is_rejected_before_profile_selection(self):
        with tempfile.TemporaryDirectory() as temporary:
            task_root = Path(temporary)
            layout, _, _, _, view = self.fixture(task_root)
            view.unlink()
            with self.assertRaises(DomainError):
                repair.prepare_npu2_configuration(layout, task_root / '.work/managed/repair')


if __name__ == '__main__':
    unittest.main()
