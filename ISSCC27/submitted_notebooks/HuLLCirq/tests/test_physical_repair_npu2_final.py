"""Fixed post-timing source reuse and one standard electrical pass; no EDA."""
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
from hullcirq.verification import object_hash, _wsl_path
import test_physical_repair_npu2_retry as retry_qa


class Npu2FinalTests(unittest.TestCase):
    def setUp(self):
        retry_qa.Npu2RetryTests.setUp(self)

    def fixture(self, root):
        layout, source, state, inputs, view = retry_qa.Npu2RetryTests.failed_fixture(self, root)
        profile = json.loads((ROOT / 'configs/physical_profile_sky130_repair_npu2v3.json').read_text(encoding='utf-8'))
        (root / 'configs/physical_profile_sky130_repair_npu2v3.json').write_text(json.dumps(profile), encoding='utf-8')
        runtime = copy.deepcopy(layout['runtime_configuration'])
        runtime['profile'] = json.loads((ROOT / 'configs/physical_profile_sky130_repair_npu2v2.json').read_text(encoding='utf-8'))
        runtime.update(repair_source_binding=copy.deepcopy(repair.NPU2_RETRY_SOURCE_BINDING),
                       repair_checkpoint_inventory=repair._retry_inventory_descriptor(),
                       resume={'initial_state_path': str(state.resolve()),
                               'initial_state_sha256': repair.NPU2_RETRY_STATE_SHA,
                               'source_input_manifest_path': str(inputs.resolve()),
                               'source_input_manifest_sha256': repair.NPU2_RETRY_INPUT_SHA,
                               'from_step': 'OpenROAD.RepairDesignPostGRT'})
        frozen = json.loads(inputs.read_text(encoding='utf-8'))
        frozen['runtime_configuration'] = runtime
        inputs.write_text(json.dumps(frozen), encoding='utf-8')
        final_state = source / repair.NPU2_FINAL_CHECKPOINT
        final_state.parent.mkdir(parents=True, exist_ok=True)
        final_state.write_bytes(state.read_bytes())
        layout.update(id=repair.NPU2_FINAL_SOURCE_BINDING['layout_run_id'],
                      runtime_configuration=runtime, runtime_configuration_sha256=object_hash(runtime))
        layout['checks']['artifacts'][0].update(sha256=sha(inputs), bytes=inputs.stat().st_size)
        layout['checks']['retained_files'] = [{'relative_path': repair.NPU2_FINAL_CHECKPOINT,
                                             'sha256': sha(final_state), 'bytes': final_state.stat().st_size}]
        layout['record_hash'] = object_hash({k: v for k, v in layout.items() if k != 'record_hash'})
        binding = copy.deepcopy(repair.NPU2_FINAL_SOURCE_BINDING)
        binding.update({k: layout[k] for k in ('revision_id', 'global_job_id', 'global_rtl_sha256',
                                              'source_manifest_sha256', 'settings_sha256', 'verification_plan_sha256')})
        binding.update(layout_run_id=layout['id'], layout_record_sha256=layout['record_hash'],
                       layout_execution_sha256=execution_hash(layout),
                       original_runtime_configuration_sha256=object_hash(runtime))
        patch.object(repair, 'NPU2_FINAL_STATE_SHA', sha(final_state)).start()
        patch.object(repair, 'NPU2_FINAL_INPUT_SHA', sha(inputs)).start()
        patch.object(repair, 'NPU2_FINAL_SOURCE_BINDING', binding).start()
        inventory = {'schema': 'hullcirq-npu2-final-checkpoint-inventory-v1',
                     'origin': repair.NPU2_FINAL_INVENTORY_ORIGIN, 'source_run_id': layout['id'],
                     'source_execution_sha256': execution_hash(layout),
                     'checkpoint_relative_path': repair.NPU2_FINAL_CHECKPOINT,
                     'checkpoint_sha256': sha(final_state), 'input_manifest_sha256': sha(inputs),
                     'files': [{'relative_path': view.relative_to(source).as_posix(),
                                'bytes': view.stat().st_size, 'sha256': sha(view)}]}
        inventory_path = root / 'configs/npu2_final_checkpoint_inventory.json'
        inventory_path.write_text(json.dumps(inventory), encoding='utf-8')
        patch.object(repair, 'NPU2_FINAL_INVENTORY_SHA', sha(inventory_path)).start()
        return layout, source, final_state, inputs, view

    def test_fixed_post_timing_source_one_extra_pass_and_original_constraints(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            layout, source, state, inputs, view = self.fixture(root)
            before = copy.deepcopy(layout)
            raw = [p.read_bytes() for p in (state, inputs, view)]
            destination = root / '.work/final'
            config = repair.prepare_npu2_final_configuration(layout, destination)
            self.assertEqual(layout, before)
            self.assertFalse(destination.exists())
            self.assertEqual(raw, [p.read_bytes() for p in (state, inputs, view)])
            self.assertEqual(config['profile']['profile_version'], repair.PROFILE_NPU2_FINAL)
            self.assertEqual(config['profile']['config'], layout['runtime_configuration']['profile']['config'])
            self.assertEqual(config['resume']['from_step'], repair.NPU2_FINAL_STEP)
            self.assertEqual(config['resume']['initial_state_path'], str(state.resolve()))
            projected = configuration_projection(self.settings, config, self.manifest)
            self.assertEqual(projected['CLOCK_PERIOD'], 50)
            self.assertEqual(projected['SIGNOFF_SDC_FILE'], 'dir::physical.sdc')
            self.assertEqual(projected['STA_CORNERS'], self.profile['config']['STA_CORNERS'])
            command = fixed_commands(config, destination / 'hullcirq-layout-fixture')[1]
            self.assertEqual(command[command.index('--from') + 1], repair.NPU2_FINAL_STEP)
            self.assertEqual(command[command.index('--flow') + 1], 'HuLLCirqNpu2RouteClosureV3')
            self.assertTrue(any(x.endswith('/route_closure_npu2_v3.py') for x in command))
            copied = root / '.work/copied-final'
            copied.mkdir()
            repair.snapshot_resume(config, copied, layout['global_rtl'], self.manifest, self.settings)
            repair.validate_resume(config, copied, layout['global_rtl'], self.manifest, self.settings)

    def test_review_metadata_allowed_but_different_executed_source_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            layout, *_ = self.fixture(root)
            config = repair.prepare_npu2_final_configuration(layout, root / '.work/final')
            layout.update(review_status='Changes Requested', acceptance_epoch=0)
            layout['record_hash'] = object_hash({k: v for k, v in layout.items() if k != 'record_hash'})
            self.assertEqual(config, repair.prepare_npu2_final_configuration(layout, root / '.work/final'))
            for field, value in (('id', 'different'), ('validation_status', 'Passed'),
                                 ('record_hash', '0' * 64), ('freshness', 'Stale')):
                changed = copy.deepcopy(layout)
                changed[field] = value
                with self.subTest(field=field), self.assertRaises(DomainError):
                    repair.prepare_npu2_final_configuration(changed, root / '.work/final')

    def test_view_mutation_rejected_before_prepare_and_before_copy(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            layout, _, _, _, view = self.fixture(root)
            original = view.read_bytes()
            view.write_bytes(b'X' * len(original))
            with self.assertRaises(DomainError):
                repair.prepare_npu2_final_configuration(layout, root / '.work/final')
            view.write_bytes(original)
            config = repair.prepare_npu2_final_configuration(layout, root / '.work/final')
            view.write_bytes(b'X' * len(original))
            copied = root / '.work/copied-final'
            copied.mkdir()
            with self.assertRaises(DomainError):
                repair.snapshot_resume(config, copied, layout['global_rtl'], self.manifest, self.settings)
            self.assertEqual(list(copied.iterdir()), [])

    def test_copied_view_cannot_be_blessed_by_rehashed_manifest(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            layout, *_ = self.fixture(root)
            config = repair.prepare_npu2_final_configuration(layout, root / '.work/final')
            copied = root / '.work/copied-final'
            copied.mkdir()
            repair.snapshot_resume(config, copied, layout['global_rtl'], self.manifest, self.settings)
            view = copied / 'resume-files/after-CTS.odb'
            view.write_bytes(b'X' * view.stat().st_size)
            path = copied / 'resume-manifest.json'
            manifest = json.loads(path.read_text(encoding='utf-8'))
            manifest['files']['resume-files/after-CTS.odb']['sha256'] = sha(view)
            path.write_text(json.dumps(manifest), encoding='utf-8')
            with self.assertRaises(DomainError):
                repair.validate_resume(config, copied, layout['global_rtl'], self.manifest, self.settings)

    def test_checkpoint_inventory_or_source_directory_changes_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            layout, source, state, *_ = self.fixture(root)
            with self.assertRaises(DomainError):
                repair.prepare_npu2_final_configuration(layout, source / 'overwrite')
            state.write_bytes(state.read_bytes() + b'\n')
            with self.assertRaises(DomainError):
                repair.prepare_npu2_final_configuration(layout, root / '.work/final')
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            layout, *_ = self.fixture(root)
            path = root / 'configs/npu2_final_checkpoint_inventory.json'
            path.write_bytes(path.read_bytes() + b'\n')
            with self.assertRaises(DomainError):
                repair.prepare_npu2_final_configuration(layout, root / '.work/final')

    def test_unique_added_step_keeps_standard_implementation_and_optimization(self):
        class Config(dict):
            def copy(self, **updates):
                return Config({**self, **updates})
        class Step:
            def __init__(self, config, *args, **kwargs):
                self.config = config
        flows = types.ModuleType('librelane.flows')
        flows.Flow = types.SimpleNamespace(factory=types.SimpleNamespace(register=lambda name: lambda value: value))
        classic = types.ModuleType('librelane.flows.classic')
        classic.Classic = object
        steps = types.ModuleType('librelane.steps')
        steps.OpenROAD = types.SimpleNamespace(RepairDesignPostGRT=Step, ResizerTimingPostGRT=Step)
        script = ROOT / 'scripts/route_closure_npu2_v3.py'
        with patch.dict(sys.modules, {'librelane': types.ModuleType('librelane'), 'librelane.flows': flows,
                                     'librelane.flows.classic': classic, 'librelane.steps': steps}):
            spec = importlib.util.spec_from_file_location('hullcirq_final_launcher_qa', script)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        config = Config(STA_CORNERS=list(module.CORNERS), RSZ_CORNERS=['max_ss_100C_1v60'],
                        EXTRA_EXCLUDED_CELLS=list(module.EXCLUDED_CELLS))
        step = module.ElectricalRepairAfterTiming(config)
        self.assertIs(step.config, config)
        self.assertEqual(step.id, repair.NPU2_FINAL_STEP)
        self.assertIsInstance(step, Step)
        self.assertNotIn('run', module.ElectricalRepairAfterTiming.__dict__)
        self.assertNotIn('get_script_path', module.ElectricalRepairAfterTiming.__dict__)
        self.assertIs(module.Npu2RouteClosureV3.Substitutions['+OpenROAD.ResizerTimingPostGRT'],
                      module.ElectricalRepairAfterTiming)
        self.assertEqual(module.AllCornerTimingPostGRT(config).config['RSZ_CORNERS'], module.CORNERS)
        self.assertEqual(sha(script), repair.NPU2_FINAL_LAUNCHER_SHA)
        with self.assertRaises(ValueError):
            module.ElectricalRepairAfterTiming(config.copy(EXTRA_EXCLUDED_CELLS=['sky130_fd_sc_hd__buf_1']))


if __name__ == '__main__':
    unittest.main()
