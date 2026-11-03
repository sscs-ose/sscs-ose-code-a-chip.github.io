"""Read-only retry preparation and fixed launcher QA; no EDA or live history."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from hullcirq import physical_repair as repair
from hullcirq.domain import DomainError
from hullcirq.physical_tools import configuration_projection, fixed_commands, sha
from hullcirq.postlayout_cleanup import execution_hash
from hullcirq.verification import content_hash, object_hash, _wsl_path
import test_physical_repair_npu2 as original_npu2_qa


class Npu2RetryTests(unittest.TestCase):
    def setUp(self):
        original_npu2_qa.Npu2RepairTests.setUp(self)

    def failed_fixture(self, task_root):
        original, _, _, _, _ = original_npu2_qa.Npu2RepairTests.fixture(self, task_root)
        (task_root / 'configs/physical_profile_sky130_repair_npu2v2.json').write_bytes(
            (ROOT / 'configs/physical_profile_sky130_repair_npu2v2.json').read_bytes())
        source = task_root / '.work/first-repair/hullcirq-layout-failed'
        source.mkdir(parents=True)
        runtime = original_npu2_qa.Npu2RepairTests.npu2_config(self)
        runtime.update(appimage_path=original['runtime_configuration']['appimage_path'],
                       executable=original['runtime_configuration']['executable'],
                       working_directory=str(source.parent))
        inputs = source / 'input-manifest.json'
        inputs.write_text(json.dumps({'settings': self.settings, 'runtime_configuration': runtime,
                                     'global_rtl_sha256': original['global_rtl_sha256'],
                                     'source_manifest_sha256': object_hash(self.manifest),
                                     'source_bundle': {'software_fixture': True, 'node_count': 11}}), encoding='utf-8')
        view = source / 'after-CTS.odb'
        view.write_bytes(b'SOFTWARE QA completed new CTS checkpoint view')
        state = source / repair.NPU2_RETRY_CHECKPOINT
        state.parent.mkdir(parents=True)
        state.write_text(json.dumps({'odb': _wsl_path(view), 'metrics': {'raw_tool_value': float('inf')}}), encoding='utf-8')
        layout = copy.deepcopy(original)
        layout.update(id=repair.NPU2_RETRY_SOURCE_BINDING['layout_run_id'], validation_status='Failed',
                      review_status='Awaiting Review', runtime_configuration=runtime,
                      runtime_configuration_sha256=object_hash(runtime),
                      checks={'validation_status': 'Failed', 'executed': True, 'exit_code': 0,
                              'cleanup_unresolved': False, 'artifacts_directory': str(source),
                              'checks': {name: {'validation_status': 'Failed' if name == 'electrical' else 'Passed'}
                                         for name in ('configuration', 'source_identity', 'routing', 'timing', 'electrical')},
                              'commands': [{'executed': True, 'status': 'Completed', 'exit_code': 0} for _ in range(2)],
                              'diagnostics': [{'code': 'physical_checks_failed'}],
                              'artifacts': [{'id': 'input-manifest', 'relative_path': 'input-manifest.json',
                                             'sha256': sha(inputs), 'bytes': inputs.stat().st_size}],
                              'retained_files': [{'relative_path': repair.NPU2_RETRY_CHECKPOINT,
                                                  'sha256': sha(state), 'bytes': state.stat().st_size}]})
        layout.pop('record_hash')
        layout['record_hash'] = object_hash(layout)
        binding = copy.deepcopy(repair.NPU2_RETRY_SOURCE_BINDING)
        binding.update({key: layout[key] for key in ('revision_id', 'global_job_id', 'global_rtl_sha256',
                                                    'source_manifest_sha256', 'settings_sha256', 'verification_plan_sha256')})
        binding.update(layout_run_id=layout['id'], layout_record_sha256=layout['record_hash'],
                       layout_execution_sha256=execution_hash(layout),
                       original_runtime_configuration_sha256=object_hash(runtime))
        patch.object(repair, 'NPU2_RETRY_STATE_SHA', sha(state)).start()
        patch.object(repair, 'NPU2_RETRY_INPUT_SHA', sha(inputs)).start()
        patch.object(repair, 'NPU2_RETRY_SOURCE_BINDING', binding).start()
        inventory = {'schema': 'hullcirq-npu2-retry-checkpoint-inventory-v1',
                     'origin': repair.NPU2_RETRY_INVENTORY_ORIGIN,
                     'source_run_id': binding['layout_run_id'],
                     'source_execution_sha256': binding['layout_execution_sha256'],
                     'checkpoint_relative_path': repair.NPU2_RETRY_CHECKPOINT,
                     'checkpoint_sha256': sha(state), 'input_manifest_sha256': sha(inputs),
                     'files': [{'relative_path': view.relative_to(source).as_posix(),
                                'bytes': view.stat().st_size, 'sha256': sha(view)}]}
        inventory_path = task_root / 'configs/npu2_retry_checkpoint_inventory.json'
        inventory_path.write_text(json.dumps(inventory), encoding='utf-8')
        patch.object(repair, 'NPU2_RETRY_INVENTORY_SHA', sha(inventory_path)).start()
        return layout, source, state, inputs, view

    def test_retry_reuses_fixed_clocktree_and_changes_only_new_buffer_selection(self):
        with tempfile.TemporaryDirectory() as temporary:
            task_root = Path(temporary)
            layout, source, state, inputs, view = self.failed_fixture(task_root)
            before = copy.deepcopy(layout)
            originals = [path.read_bytes() for path in (state, inputs, view)]
            destination = task_root / '.work/managed/retry'
            runtime = repair.prepare_npu2_retry_configuration(layout, destination)
            self.assertEqual(layout, before)
            self.assertFalse(destination.exists())
            self.assertEqual([path.read_bytes() for path in (state, inputs, view)], originals)
            self.assertEqual(runtime['profile']['profile_version'], repair.PROFILE_NPU2_RETRY)
            self.assertEqual(runtime['profile']['config'], {
                **self.profile['config'], 'EXTRA_EXCLUDED_CELLS': ['sky130_fd_sc_hd__clkdlybuf*']})
            projected = configuration_projection(self.settings, runtime, self.manifest)
            self.assertEqual(projected['CLOCK_PERIOD'], 50)
            self.assertEqual(projected['SIGNOFF_SDC_FILE'], 'dir::physical.sdc')
            self.assertEqual(projected['STA_CORNERS'], self.profile['config']['STA_CORNERS'])
            self.assertEqual(runtime['resume']['initial_state_path'], str(state.resolve()))
            self.assertEqual(runtime['resume']['from_step'], 'OpenROAD.RepairDesignPostGRT')
            command = fixed_commands(runtime, destination / 'hullcirq-layout-fixture')[1]
            self.assertEqual(command[command.index('--flow') + 1], 'HuLLCirqNpu2RouteClosureV2')
            self.assertTrue(any(item.endswith('/route_closure_npu2_v2.py') for item in command))
            self.assertEqual(repair.implementation_kind(runtime), 'resumed_post_GRT_route_repair')
            copy_folder = task_root / '.work/copied-retry'
            copy_folder.mkdir()
            repair.snapshot_resume(runtime, copy_folder, layout['global_rtl'], self.manifest, self.settings)
            repair.validate_resume(runtime, copy_folder, layout['global_rtl'], self.manifest, self.settings)

    def test_review_only_update_keeps_same_retry_but_rehashed_execution_change_does_not(self):
        with tempfile.TemporaryDirectory() as temporary:
            task_root = Path(temporary)
            layout, *_ = self.failed_fixture(task_root)
            destination = task_root / '.work/managed/retry'
            first = repair.prepare_npu2_retry_configuration(layout, destination)
            layout['review_status'] = 'Changes Requested'
            layout['acceptance_epoch'] = 0
            layout['record_hash'] = object_hash({key: value for key, value in layout.items() if key != 'record_hash'})
            self.assertEqual(repair.prepare_npu2_retry_configuration(layout, destination), first)
            layout['global_rtl'] += '\n'
            layout['global_rtl_sha256'] = content_hash(layout['global_rtl'])
            layout['record_hash'] = object_hash({key: value for key, value in layout.items() if key != 'record_hash'})
            with self.assertRaises(DomainError):
                repair.prepare_npu2_retry_configuration(layout, destination)

    def test_retry_rejects_different_failure_unresolved_cleanup_or_bad_selfchecksum(self):
        with tempfile.TemporaryDirectory() as temporary:
            task_root = Path(temporary)
            layout, *_ = self.failed_fixture(task_root)
            for field, value in (('id', 'another-layout'), ('record_hash', '0' * 64),
                                 ('validation_status', 'Passed'), ('freshness', 'Stale')):
                changed = copy.deepcopy(layout)
                changed[field] = value
                with self.subTest(field=field), self.assertRaises(DomainError):
                    repair.prepare_npu2_retry_configuration(changed, task_root / '.work/managed/retry')
            layout['checks']['cleanup_unresolved'] = True
            layout['record_hash'] = object_hash({key: value for key, value in layout.items() if key != 'record_hash'})
            with self.assertRaises(DomainError):
                repair.prepare_npu2_retry_configuration(layout, task_root / '.work/managed/retry')

    def test_retry_checkpoint_corruption_or_original_run_destination_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            task_root = Path(temporary)
            layout, source, state, *_ = self.failed_fixture(task_root)
            with self.assertRaises(DomainError):
                repair.prepare_npu2_retry_configuration(layout, source / 'retry')
            state.write_bytes(state.read_bytes() + b'\n')
            with self.assertRaises(DomainError):
                repair.prepare_npu2_retry_configuration(layout, task_root / '.work/managed/retry')

    def test_changed_odb_is_rejected_before_prepare_and_between_prepare_and_snapshot(self):
        with tempfile.TemporaryDirectory() as temporary:
            task_root = Path(temporary)
            layout, _, _, _, view = self.failed_fixture(task_root)
            original = view.read_bytes()
            view.write_bytes(b'X' * len(original))
            with self.assertRaises(DomainError) as error:
                repair.prepare_npu2_retry_configuration(layout, task_root / '.work/managed/retry')
            self.assertEqual(error.exception.code, 'physical_resume_inventory')
            view.write_bytes(original)
            runtime = repair.prepare_npu2_retry_configuration(layout, task_root / '.work/managed/retry')
            view.write_bytes(b'X' * len(original))
            copy_folder = task_root / '.work/copied-retry'
            copy_folder.mkdir()
            with self.assertRaises(DomainError) as error:
                repair.snapshot_resume(runtime, copy_folder, layout['global_rtl'], self.manifest, self.settings)
            self.assertEqual(error.exception.code, 'physical_resume_inventory')
            self.assertEqual(list(copy_folder.iterdir()), [])

    def test_copied_odb_cannot_be_blessed_by_rehashing_its_copy_manifest(self):
        with tempfile.TemporaryDirectory() as temporary:
            task_root = Path(temporary)
            layout, _, _, _, _ = self.failed_fixture(task_root)
            runtime = repair.prepare_npu2_retry_configuration(layout, task_root / '.work/managed/retry')
            copy_folder = task_root / '.work/copied-retry'
            copy_folder.mkdir()
            repair.snapshot_resume(runtime, copy_folder, layout['global_rtl'], self.manifest, self.settings)
            copied = copy_folder / 'resume-files/after-CTS.odb'
            copied.write_bytes(b'X' * copied.stat().st_size)
            manifest_path = copy_folder / 'resume-manifest.json'
            manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
            manifest['files']['resume-files/after-CTS.odb']['sha256'] = sha(copied)
            manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
            with self.assertRaises(DomainError) as error:
                repair.validate_resume(runtime, copy_folder, layout['global_rtl'], self.manifest, self.settings)
            self.assertEqual(error.exception.code, 'physical_resume_inventory')

    def test_changed_fixed_inventory_is_rejected_before_prepare(self):
        with tempfile.TemporaryDirectory() as temporary:
            task_root = Path(temporary)
            layout, *_ = self.failed_fixture(task_root)
            path = task_root / 'configs/npu2_retry_checkpoint_inventory.json'
            path.write_bytes(path.read_bytes() + b'\n')
            with self.assertRaises(DomainError) as error:
                repair.prepare_npu2_retry_configuration(layout, task_root / '.work/managed/retry')
            self.assertEqual(error.exception.code, 'physical_resume_inventory')

    def test_launcher_checks_exclusion_and_keeps_standard_all_corner_timing(self):
        class Config(dict):
            def copy(self, **updates):
                return Config({**self, **updates})

        class Step:
            def __init__(self, config, *args, **kwargs):
                self.config = config

        flows = types.ModuleType('librelane.flows')
        flows.Flow = types.SimpleNamespace(factory=types.SimpleNamespace(register=lambda _name: lambda value: value))
        classic = types.ModuleType('librelane.flows.classic')
        classic.Classic = object
        steps = types.ModuleType('librelane.steps')
        steps.OpenROAD = types.SimpleNamespace(RepairDesignPostGRT=Step, ResizerTimingPostGRT=Step)
        module = types.ModuleType('hullcirq_retry_launcher_qa')
        script = ROOT / 'scripts/route_closure_npu2_v2.py'
        with patch.dict(sys.modules, {'librelane': types.ModuleType('librelane'), 'librelane.flows': flows,
                                     'librelane.flows.classic': classic, 'librelane.steps': steps}):
            spec = importlib.util.spec_from_file_location(module.__name__, script)
            spec.loader.exec_module(module)
        config = Config(STA_CORNERS=list(module.CORNERS), RSZ_CORNERS=['max_ss_100C_1v60'],
                        EXTRA_EXCLUDED_CELLS=['sky130_fd_sc_hd__clkdlybuf*'])
        self.assertIs(module.NonDelayBufferDesignRepair(config).config, config)
        timing = module.AllCornerTimingPostGRT(config)
        self.assertEqual(timing.config['RSZ_CORNERS'], module.CORNERS)
        self.assertEqual(config['RSZ_CORNERS'], ['max_ss_100C_1v60'])
        for changed in (config.copy(EXTRA_EXCLUDED_CELLS=[]), config.copy(STA_CORNERS=module.CORNERS[:-1])):
            with self.assertRaises(ValueError):
                module.NonDelayBufferDesignRepair(changed)
        self.assertEqual(sha(script), repair.NPU2_RETRY_LAUNCHER_SHA)
        self.assertEqual(repair.closure_launcher({'profile': {'profile_version': repair.PROFILE_NPU2}}),
                         ('route_closure_v5.py', 'HuLLCirqRouteClosureV5', repair.V5_LAUNCHER_SHA))


if __name__ == '__main__':
    unittest.main()
