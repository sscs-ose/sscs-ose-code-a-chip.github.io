"""Pure/mocked generic fresh-closure recipe tests; no model, EDA or live stores."""
import copy
from decimal import Decimal
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
from hullcirq import physical_repair_generic as generic
from hullcirq import physical_tools as tools
from hullcirq.domain import DomainError
from hullcirq.generic_global_verification import build_plan
from hullcirq.verification import content_hash, object_hash
import test_generic_global_verification as global_qa
import test_physical_tools as legacy_qa


class GenericClosureTests(unittest.TestCase):
    def setUp(self):
        old = legacy_qa.PhysicalToolTests()
        old.setUp()
        self.metrics = copy.deepcopy(old.metrics)
        self.configuration = copy.deepcopy(old.config)
        self.configuration['pdk_root'] = str(ROOT / '.work/software-fixture/pdks')
        self.manifest = global_qa.manifest_fixture()
        self.settings = self.manifest['design']['settings']
        self.rtl = 'module byte_pipeline; endmodule // SOFTWARE QA, never executed\n'
        self.configuration.update(origin=generic.ORIGIN,
            profile=json.loads((ROOT / 'configs' / generic.PROFILE_FILE).read_text(encoding='utf-8')))
        binding = {key: 'a' * 64 for key in generic.BINDING_FIELDS if key.endswith('_sha256')}
        binding.update(version=generic.BINDING_VERSION, failed_s14_id='postlayout-software',
            layout_run_id='layout-software', revision_id='revision-software', global_job_id='global-software',
            synthesis_run_id='synthesis-software', netlist_run_id='netlist-software',
            global_rtl_sha256=content_hash(self.rtl), source_manifest_sha256=object_hash(self.manifest),
            settings_sha256=object_hash(self.settings), verification_plan_sha256=object_hash(build_plan(self.manifest['design'])))
        self.configuration['generic_repair_source_binding'] = binding
        for name in ('design__max_slew_violation__count', 'design__max_cap_violation__count', 'design__max_fanout_violation__count'):
            self.metrics[name] = 0
            for corner in self.configuration['profile']['config']['STA_CORNERS']:
                self.metrics[name + '__corner:' + corner] = 0

    def test_fresh_full_flow_preserves_original_clock_and_signoff(self):
        before = copy.deepcopy((self.settings, self.manifest, self.configuration))
        config = tools.configuration_projection(self.settings, self.configuration, self.manifest)
        self.assertEqual(config['CLOCK_PERIOD'], 50)
        self.assertEqual(config['CLOCK_PORT'], 'clock_i')
        self.assertEqual(config['SIGNOFF_SDC_FILE'], 'dir::physical.sdc')
        self.assertEqual(config['PNR_SDC_FILE'], 'dir::physical_pnr.sdc')
        self.assertEqual(len(config['STA_CORNERS']), 9)
        self.assertEqual(config['VERILOG_FILES'], ['dir::candidate_top.v', 'dir::stage-a.v', 'dir::stage-b.v'])
        command = tools.fixed_commands(self.configuration, Path(self.configuration['working_directory']) / 'hullcirq-layout-fixture')[1]
        self.assertEqual(command[command.index('--flow') + 1], generic.FLOW)
        self.assertNotIn('--from', command)
        self.assertNotIn('--with-initial-state', command)
        self.assertTrue(any(token.endswith('/' + generic.LAUNCHER) for token in command))
        self.assertEqual(before, (self.settings, self.manifest, self.configuration))
        self.assertEqual(tools.sha(ROOT / 'scripts' / generic.LAUNCHER), generic.LAUNCHER_SHA)
        self.assertEqual(tools.sha(ROOT / 'configs' / generic.PROFILE_FILE), generic.PROFILE_SHA)

    def test_no_checkpoint_or_fences_can_be_silently_discarded(self):
        for field in ('resume', 'block_plan', 'block_plan_sha256', 'repair_source_binding'):
            changed = copy.deepcopy(self.configuration)
            changed[field] = {}
            with self.subTest(field=field), self.assertRaises(DomainError):
                tools.configuration_projection(self.settings, changed, self.manifest)

    def test_changed_independent_contract_settings_and_profile_reject(self):
        for target in ('contract', 'settings', 'profile'):
            manifest, settings, config = copy.deepcopy((self.manifest, self.settings, self.configuration))
            if target == 'contract':
                manifest['design']['global_verification']['cycles'][1]['expect']['data_o'] = 43
            elif target == 'settings':
                settings['clock_period_ns'] = 100
            else:
                config['profile']['config']['GRT_DESIGN_REPAIR_MAX_SLEW_PCT'] = 0
            with self.subTest(target=target), self.assertRaises(DomainError):
                tools.configuration_projection(settings, config, manifest)

    def test_changed_rtl_rejects_before_output_directory_or_process(self):
        with patch.object(tools.tempfile, 'mkdtemp') as create, patch.object(tools, '_execute') as execute:
            with self.assertRaises(DomainError):
                tools.run_layout(self.rtl + '// changed', self.manifest, self.settings, self.configuration)
        create.assert_not_called()
        execute.assert_not_called()

    def test_launcher_pin_rechecked_at_fixed_command_boundary(self):
        original = tools.sha
        def changed(path):
            return '0' * 64 if Path(path).name == generic.LAUNCHER else original(path)
        with patch.object(tools, 'sha', side_effect=changed), self.assertRaises(DomainError):
            tools.fixed_commands(self.configuration, Path(self.configuration['working_directory']) / 'hullcirq-layout-fixture')

    def test_all_nine_corner_electrical_counts_required(self):
        checks = tools._configuration_metric_checks(self.metrics, self.configuration)
        self.assertEqual(checks['electrical']['validation_status'], 'Passed')
        self.assertEqual(checks['electrical']['corner_count'], 9)
        key = 'design__max_slew_violation__count__corner:max_ss_100C_1v60'
        changed = dict(self.metrics)
        changed[key] = 1
        self.assertEqual(changed['design__max_slew_violation__count'], 0)
        self.assertEqual(tools._configuration_metric_checks(changed, self.configuration)['electrical']['validation_status'], 'Failed')
        for value in (None, True, '0', float('nan'), -1):
            changed = dict(self.metrics)
            if value is None:
                del changed[key]
            else:
                changed[key] = value
            with self.subTest(value=value), self.assertRaises(DomainError):
                tools._configuration_metric_checks(changed, self.configuration)

    def test_old_metric_projection_unchanged(self):
        old = legacy_qa.PhysicalToolTests()
        old.setUp()
        self.assertEqual(tools._configuration_metric_checks(old.metrics, old.config), tools.metric_checks(old.metrics))
        self.assertNotIn('electrical', tools._configuration_metric_checks(old.metrics, old.config))

    def test_fresh_mapping_evidence_and_no_reuse_required(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            result = {'implementation_kind': generic.IMPLEMENTATION_KIND,
                      'upstream_technology_mapping_reused': False, 'technology_mapping_executed': True}
            with self.assertRaises(DomainError):
                tools._validate_generic_fresh_mapping(result, folder, self.configuration)
            state = folder / 'runs/physical/01-yosys-synthesis/state_out.json'
            state.parent.mkdir(parents=True)
            state.write_text('{}', encoding='utf-8')
            tools._validate_generic_fresh_mapping(result, folder, self.configuration)
            for key, value in (('upstream_technology_mapping_reused', True), ('technology_mapping_executed', False)):
                changed = {**result, key: value}
                with self.subTest(key=key), self.assertRaises(DomainError):
                    tools._validate_generic_fresh_mapping(changed, folder, self.configuration)
            (folder / 'resume-state.json').write_text('{}', encoding='utf-8')
            with self.assertRaises(DomainError):
                tools._validate_generic_fresh_mapping(result, folder, self.configuration)

    def test_launcher_standard_steps_all_corners_no_custom_run(self):
        class Config(dict):
            def copy(self, **updates):
                return Config({**self, **updates})
        class StandardStep:
            def __init__(self, config, *args, **kwargs):
                self.config = config
        flows = types.ModuleType('librelane.flows')
        flows.Flow = types.SimpleNamespace(factory=types.SimpleNamespace(register=lambda name: lambda value: value))
        classic = types.ModuleType('librelane.flows.classic')
        classic.Classic = object
        steps = types.ModuleType('librelane.steps')
        steps.OpenROAD = types.SimpleNamespace(RepairDesignPostGRT=StandardStep, ResizerTimingPostGRT=StandardStep)
        with patch.dict(sys.modules, {'librelane': types.ModuleType('librelane'), 'librelane.flows': flows,
                                    'librelane.flows.classic': classic, 'librelane.steps': steps}):
            spec = importlib.util.spec_from_file_location('generic_closure_fixture', ROOT / 'scripts' / generic.LAUNCHER)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        config = Config(self.configuration['profile']['config'])
        config['GRT_RESIZER_HOLD_SLACK_MARGIN'] = Decimal('0.1')
        electrical = module.ElectricalRepairAfterTiming(config)
        self.assertIs(electrical.config, config)
        self.assertEqual(electrical.id, 'HuLLCirq.GenericRepairDesignAfterTimingV1')
        self.assertNotIn('run', module.ElectricalRepairAfterTiming.__dict__)
        self.assertNotIn('get_script_path', module.StandardElectricalRepair.__dict__)
        self.assertIs(module.GenericRouteClosureV1.Substitutions['+OpenROAD.ResizerTimingPostGRT'], module.ElectricalRepairAfterTiming)
        self.assertEqual(module.AllCornerTimingPostGRT(config).config['RSZ_CORNERS'], module.CORNERS)
        for updates in ({'EXTRA_EXCLUDED_CELLS': []}, {'STA_CORNERS': module.CORNERS[:-1]},
                        {'RUN_POST_GRT_DESIGN_REPAIR': False}, {'GRT_DESIGN_REPAIR_MAX_SLEW_PCT': 0}):
            with self.subTest(updates=updates), self.assertRaises(ValueError):
                module.StandardElectricalRepair(config.copy(**updates))


if __name__ == '__main__':
    unittest.main()
