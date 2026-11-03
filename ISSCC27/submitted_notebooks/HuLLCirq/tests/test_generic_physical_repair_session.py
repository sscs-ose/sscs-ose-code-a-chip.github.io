"""Generic correction prepare/restore and source guards; no model or EDA."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from hullcirq import physical_repair_generic as generic, physical_repair_session as session
from hullcirq.domain import DomainError
from hullcirq.generic_global_verification import build_plan
from hullcirq.physical_tools import IMAGE_SHA, PDK_REVISION, SDC_SHA
from hullcirq.verification import _wsl_path, content_hash, object_hash
from test_generic_global_verification import manifest_fixture
import test_physical_repair_session as legacy
from test_physical_repair_session import checksum

ROOT = Path(__file__).resolve().parents[1]


def source_fixture():
    manifest = manifest_fixture()  # Starts from workspace.blank_design, not an NPU design.
    settings = manifest['design']['settings']
    runtime = {'kind': 'wsl', 'distribution': 'Ubuntu', 'release': '3.0.16',
        'appimage_sha256': IMAGE_SHA, 'pdk_revision': PDK_REVISION, 'base_sdc_sha256': SDC_SHA,
        'origin': 'SOFTWARE_QA_ONLY',
        'profile': json.loads((ROOT / 'configs/physical_profile_sky130.json').read_text(encoding='utf-8')),
        'appimage_path': str(ROOT / '.work/software-fixture/librelane-devshell-x86_64.AppImage'),
        'executable': _wsl_path(ROOT / '.work/software-fixture/librelane-devshell-x86_64.AppImage'),
        'working_directory': str(ROOT / '.work/software-fixture/original')}
    rtl = 'module byte_pipeline; endmodule // SOFTWARE QA ONLY'
    plan = build_plan(manifest['design'])
    layout = checksum({'id': 'physical-software-generic', 'revision_id': 'revision-software-generic',
        'global_job_id': 'global-software-generic', 'synthesis_run_id': 'synthesis-software-generic',
        'netlist_run_id': 'netlist-software-generic', 'execution_status': 'Completed',
        'validation_status': 'Passed', 'review_status': 'Accepted',
        'evidence_kind': 'trusted_fixed_tool_execution', 'global_rtl': rtl,
        'global_rtl_sha256': content_hash(rtl), 'source_manifest': manifest,
        'source_manifest_sha256': object_hash(manifest), 'settings': settings,
        'settings_sha256': object_hash(settings), 'verification_plan': plan,
        'verification_plan_sha256': object_hash(plan), 'runtime_configuration': runtime,
        'runtime_configuration_sha256': object_hash(runtime),
        'checks': {'artifacts_directory': str(ROOT / '.work/software-fixture/original/hullcirq-layout-original')}})
    failed = {'id': 'postlayout-software-generic', 'layout_run_id': layout['id'],
        'layout_snapshot': copy.deepcopy(layout),
        'runtime_configuration': {'profile_version': 'hullcirq-postroute-functional-sta-v4'}}
    return layout, failed


class GenericRepairBindingTests(unittest.TestCase):
    def prepare(self, layout=None, failed=None):
        if layout is None:
            layout, failed = source_fixture()
        return generic.prepare_configuration(layout, ROOT / '.work/software-fixture/generic-repair', failed)

    def test_blank_non_npu_design_fresh_recipe_binds_original_inputs_without_mutation(self):
        layout, failed = source_fixture(); before = copy.deepcopy((layout, failed))
        runtime = self.prepare(layout, failed)
        self.assertTrue(generic.is_generic(runtime)); self.assertNotIn('resume', runtime)
        self.assertEqual(runtime['profile']['profile_version'], generic.PROFILE)
        self.assertEqual(runtime['generic_repair_source_binding']['layout_record_sha256'], layout['record_hash'])
        self.assertEqual(runtime['generic_repair_source_binding']['verification_plan_sha256'], layout['verification_plan_sha256'])
        self.assertEqual(runtime['generic_repair_source_binding']['settings_sha256'], layout['settings_sha256'])
        generic.validate_source(runtime, layout['global_rtl'], layout['source_manifest'], layout['settings'])
        self.assertEqual((layout, failed), before)

    def test_changed_rtl_contract_settings_or_unpinned_recipe_fail_closed(self):
        layout, failed = source_fixture(); runtime = self.prepare(layout, failed)
        with self.assertRaises(DomainError):
            generic.validate_source(runtime, layout['global_rtl']+' altered', layout['source_manifest'], layout['settings'])
        changed = copy.deepcopy(layout['source_manifest'])
        changed['design']['global_verification']['cycles'][1]['expect']['data_o'] = 43
        with self.assertRaises(DomainError):
            generic.validate_source(runtime, layout['global_rtl'], changed, layout['settings'])
        changed_settings = {**layout['settings'], 'clock_period_ns': 51}
        with self.assertRaises(DomainError):
            generic.validate_configuration(runtime, changed_settings, layout['source_manifest'])
        for field in ('PROFILE_SHA', 'LAUNCHER_SHA'):
            with patch.object(generic, field, '0'*64), self.assertRaises(DomainError):
                generic.validate_configuration(runtime, layout['settings'], layout['source_manifest'])

    def test_legacy_or_block_or_already_corrected_source_never_silently_falls_back(self):
        for mutate in (lambda l, f: l['verification_plan'].update(kind='not-generic'),
                       lambda l, f: l['runtime_configuration'].update(resume={}),
                       lambda l, f: l['runtime_configuration'].update(block_plan={}),
                       lambda l, f: f['runtime_configuration'].update(profile_version='hullcirq-postroute-functional-sta-v3'),
                       lambda l, f: f.update(layout_run_id='another-layout')):
            layout, failed = source_fixture(); mutate(layout, failed)
            checksum(layout); failed['layout_snapshot'] = copy.deepcopy(layout)
            with self.assertRaises(DomainError): self.prepare(layout, failed)

    def test_source_binding_rejects_missing_extra_path_boolean_and_invalid_hash_fields(self):
        layout, failed = source_fixture(); runtime = self.prepare(layout, failed)
        for mutate in (lambda b: b.pop('failed_s14_id'), lambda b: b.update(waive=True),
                       lambda b: b.update(layout_run_id='../another'),
                       lambda b: b.update(settings_sha256=True),
                       lambda b: b.update(global_rtl_sha256='not-a-hash')):
            changed = copy.deepcopy(runtime); mutate(changed['generic_repair_source_binding'])
            with self.assertRaises(DomainError):
                generic.validate_configuration(changed, layout['settings'], layout['source_manifest'])

    def test_builder_rejects_original_record_and_destination_substitution(self):
        layout, failed = source_fixture(); changed = copy.deepcopy(layout); changed['global_job_id'] = 'other-job'
        with self.assertRaises(DomainError): self.prepare(changed, failed)
        for destination in (ROOT / '.work', Path(layout['checks']['artifacts_directory']) / 'new', ROOT.parent / 'outside'):
            with self.assertRaises(DomainError): generic.prepare_configuration(layout, destination, failed)


class GenericRepairSessionTests(unittest.TestCase):
    def setUp(self):
        fixture = legacy.PhysicalRepairSessionTests('test_explicit_prepare_preserves_histories_and_restores_exact_fixed_configs')
        fixture.setUp(); self.addCleanup(fixture.doCleanups); self.f = fixture
        # Independent blank-workspace generic contract supplies this new branch.
        layout, _ = source_fixture()
        fixture.design = copy.deepcopy(layout['source_manifest']['design'])
        fixture.snapshots[fixture.revision] = copy.deepcopy(fixture.design)
        fixture.records['layout']['verification_plan'] = copy.deepcopy(layout['verification_plan'])
        fixture.records['layout']['source_manifest'] = copy.deepcopy(layout['source_manifest'])
        checksum(fixture.records['layout'])
        fixture.failure['layout_snapshot'] = copy.deepcopy(fixture.records['layout'])
        checksum(fixture.failure)
        fixture.server.postlayout_workflow._state['runs'] = [copy.deepcopy(fixture.failure)]
        fixture.save_histories()
        self.builder = fixture.stack.enter_context(patch.object(generic, 'prepare_configuration', side_effect=self.builder_result))

    def builder_result(self, layout, work, failed):
        self.assertEqual(failed, self.f.failure)
        return {**copy.deepcopy(layout['runtime_configuration']), 'working_directory': str(work),
            'profile': {'profile_version': generic.PROFILE},
            'generic_repair_source_binding': {'failed_s14_id': failed['id'], 'layout_record_sha256': layout['record_hash']}}

    def restore(self):
        f = self.f
        return session.load_repair_configurations(f.store, f.base, f.directory, 'software-qa-project', 'software-qa-system')

    def test_explicit_generic_prepare_and_reopen_preserve_history_and_start_no_work(self):
        f = self.f; before = {p: p.read_bytes() for p in f.store_path.iterdir()}
        status = f.prepare()
        self.assertEqual(status['session_schema'], session.GENERIC_SCHEMA)
        self.assertEqual(status['profile_version'], generic.PROFILE)
        self.assertFalse(status['technology_mapping_reused'])
        self.assertEqual(status['implementation_kind'], generic.IMPLEMENTATION_KIND)
        self.assertEqual(self.builder.call_args.args[1], f.root / '.work/generic_repair_v1/p')
        f.builder.assert_not_called()
        raw = f.bundle_path.read_bytes(); bundle = json.loads(raw)
        self.assertEqual(bundle['schema'], session.GENERIC_SCHEMA)
        restored, reopened = self.restore()
        self.assertTrue(reopened['configured'], reopened['error'])
        self.assertEqual(reopened['session_schema'], session.GENERIC_SCHEMA)
        self.assertEqual(restored[2], f.server.physical_workflow.tool_configuration)
        self.assertEqual(before, {p: p.read_bytes() for p in before})
        self.assertEqual(f.bundle_path.read_bytes(), raw)
        self.assertGreaterEqual(f.failed_validator.call_count, 2)

    def test_generic_bundle_rehashed_runtime_or_schema_tampering_stays_unapplied(self):
        f = self.f; f.prepare(); raw = f.bundle_path.read_bytes()
        for mutate in (lambda b: b.update(schema=session.SCHEMA),
                       lambda b: b['configurations']['physical'].update(working_directory='another-path')):
            bundle = json.loads(raw); mutate(bundle); checksum(bundle)
            f.bundle_path.write_text(json.dumps(bundle), encoding='utf-8'); changed = f.bundle_path.read_bytes()
            restored, status = self.restore()
            self.assertFalse(status['configured']); self.assertEqual(restored, f.base)
            self.assertEqual(f.bundle_path.read_bytes(), changed)

    def test_generic_source_currentness_worker_readonly_and_electrical_only_guards_remain(self):
        f = self.f
        for target, attr, value in ((f.server.postlayout_workflow, 'current', False),
                                    (f.server.generation, 'active', True)):
            original = getattr(target, attr); setattr(target, attr, value)
            with self.assertRaises(DomainError): f.prepare()
            setattr(target, attr, original); self.assertFalse(f.bundle_path.exists())
        f.server.workspace.identity['read_only'] = True
        with self.assertRaises(DomainError): f.prepare()
        f.server.workspace.identity['read_only'] = False
        f.failure['checks']['checks']['functional']['validation_status'] = 'Failed'
        checksum(f.failure); f.save_histories(); f.server.postlayout_workflow._state['runs'] = [copy.deepcopy(f.failure)]
        with self.assertRaises(DomainError): f.prepare()
        self.assertFalse(f.bundle_path.exists())

    def test_generic_restore_revalidates_proof_and_rejects_old_checkpoint_retry_bundles(self):
        f = self.f; f.prepare(); raw = f.bundle_path.read_bytes()
        with patch.object(session, '_failure', side_effect=DomainError('changed-proof', 'changed-proof')):
            restored, status = self.restore()
        self.assertFalse(status['configured']); self.assertEqual(restored, f.base)
        retry = f.directory / session.RETRY_BUNDLE_NAME
        retry.write_text('{}', encoding='utf-8')
        restored, status = self.restore()
        self.assertFalse(status['configured']); self.assertEqual(restored, f.base)
        self.assertEqual(f.bundle_path.read_bytes(), raw)
        self.assertEqual(retry.read_text(encoding='utf-8'), '{}')
