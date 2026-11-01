"""Software-only repeated generic correction checks; no native tools/model."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from hullcirq import physical_repair_generic as old, physical_repair_generic_v2 as new
from hullcirq import generic_physical_retry_session as retry, physical_tools, physical_repair_session as session
from hullcirq.domain import DomainError
from hullcirq.verification import object_hash
from test_generic_physical_repair_session import source_fixture
from test_physical_repair_session import checksum
import test_generic_physical_repair_session as previous_tests

ROOT = Path(__file__).resolve().parents[1]


def failed_layout(runtime=None, identifier='layout-failed-generic'):
    layout, original_s14 = source_fixture()
    if runtime is None:
        runtime = old.prepare_configuration(layout, ROOT / '.work/software-fixture/generic-repair', original_s14)
    layout.update(id=identifier, stage_id='layout', execution_status='Completed', validation_status='Failed',
        review_status='Awaiting Review', error=None, runtime_configuration=copy.deepcopy(runtime),
        runtime_configuration_sha256=object_hash(runtime), diagnostics=[{'code': 'physical_checks_failed', 'severity': 'error'}])
    layout['checks'].update(status='Completed', origin='trusted_fixed_tool_adapter', validation_status='Failed',
        technology_mapping_executed=True, upstream_technology_mapping_reused=False,
        implementation_kind=new.IMPLEMENTATION_KIND, diagnostics=copy.deepcopy(layout['diagnostics']),
        checks={key: {'validation_status': 'Failed' if key == 'electrical' else 'Passed'}
                for key in ('source_identity', 'configuration', 'routing', 'timing', 'electrical')},
        commands=[{}, {}])
    return checksum(layout)


class RepeatedGenericBuilderTests(unittest.TestCase):
    def build(self, layout=None, attempt=1, previous='a'*64, density=30):
        layout = layout or failed_layout()
        return new.prepare_configuration(layout, layout, ROOT / f'.work/software-fixture/repeat-{attempt}',
                attempt=attempt, previous_bundle_sha256=previous, core_utilization=density)

    def test_repeated_attempts_keep_source_constraints_and_fresh_recipe(self):
        layout = failed_layout(); initial = copy.deepcopy(layout)
        first = self.build(layout)
        second_layout = failed_layout(first, 'layout-failed-generic-two')
        second = self.build(second_layout, 2, 'b'*64, 25)
        third_layout = failed_layout(second, 'layout-failed-generic-three')
        third = self.build(third_layout, 3, 'c'*64, 20)
        for runtime, source in ((first, layout), (second, second_layout), (third, third_layout)):
            self.assertTrue(old.is_generic(runtime)); self.assertTrue(new.is_generic(runtime))
            new.validate_source(runtime, source['global_rtl'], source['source_manifest'], source['settings'])
            projected = physical_tools.configuration_projection(source['settings'], runtime, source['source_manifest'])
            self.assertEqual(projected['FP_CORE_UTIL'], runtime['generic_retry_source_binding']['core_utilization'])
            self.assertEqual(projected['CLOCK_PERIOD'], source['settings']['clock_period_ns'])
            self.assertEqual(runtime['base_sdc_sha256'], source['runtime_configuration']['base_sdc_sha256'])
            self.assertEqual(projected['SIGNOFF_SDC_FILE'], 'dir::physical.sdc')
            self.assertNotIn('resume', runtime); self.assertNotIn('generic_repair_source_binding', runtime)
            self.assertEqual(physical_tools._closure_recipe(runtime)[0], new.LAUNCHER)
            self.assertEqual(len(projected['STA_CORNERS']), 9)
        self.assertEqual(layout, initial)

    def test_old_v1_is_still_exact_original_profile_and_launcher(self):
        layout = failed_layout(); runtime = layout['runtime_configuration']
        old.validate_source(runtime, layout['global_rtl'], layout['source_manifest'], layout['settings'])
        self.assertEqual(physical_tools._closure_recipe(runtime)[0], old.LAUNCHER)
        for module in (old, new):
            self.assertEqual(hashlib.sha256((ROOT/'configs'/module.PROFILE_FILE).read_bytes()).hexdigest(), module.PROFILE_SHA)
            self.assertEqual(hashlib.sha256((ROOT/'scripts'/module.LAUNCHER).read_bytes()).hexdigest(), module.LAUNCHER_SHA)

    def test_rehashed_binding_changes_and_unbounded_options_rejected(self):
        layout = failed_layout(); runtime = self.build(layout)
        for key, value in [('core_utilization', True), ('core_utilization', 0), ('core_utilization', 31),
                           ('attempt', True), ('attempt', -1), ('failed_stage', 'other'),
                           ('previous_bundle_sha256', 'missing'), ('failed_run_id', '../escape')]:
            changed = copy.deepcopy(runtime); changed['generic_retry_source_binding'][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(DomainError):
                new.validate_source(changed, layout['global_rtl'], layout['source_manifest'], layout['settings'])
        for key in ('resume', 'block_plan', 'generic_repair_source_binding'):
            changed = copy.deepcopy(runtime); changed[key] = {}
            with self.assertRaises(DomainError): new.validate_configuration(changed, layout['settings'], layout['source_manifest'])
        changed = copy.deepcopy(runtime); changed['generic_retry_source_binding']['settings_sha256'] = 'f'*64
        with self.assertRaises(DomainError): new.validate_source(changed, layout['global_rtl'], layout['source_manifest'], layout['settings'])
        with self.assertRaises(DomainError): new.validate_source(runtime, layout['global_rtl']+' altered', layout['source_manifest'], layout['settings'])

    def test_native_commands_fresh_mapping_not_resume(self):
        runtime = self.build(); runtime['pdk_root'] = str(ROOT / '.work/software-fixture/pdk')
        folder = Path(runtime['working_directory'])/'hullcirq-layout-software-only'
        commands = physical_tools.fixed_commands(runtime, folder)
        text = json.dumps(commands)
        self.assertIn(new.LAUNCHER, text); self.assertIn(new.FLOW, text)
        self.assertNotIn('--with-initial-state', text); self.assertNotIn('resume-state', text)

    def test_declared_attempt_limit_accepts_256_and_rejects_257_without_execution(self):
        layout = failed_layout()
        boundary = self.build(layout, attempt=256, density=10)
        new.validate_source(boundary, layout['global_rtl'], layout['source_manifest'], layout['settings'])
        self.assertEqual(boundary['generic_retry_source_binding']['attempt'], 256)
        with self.assertRaises(DomainError):
            self.build(layout, attempt=257, density=10)


class RepeatedGenericChainTests(unittest.TestCase):
    def test_publication_is_complete_and_never_overwrites_an_existing_attempt(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'attempt.json'
            retry._publish(path, {'value': 1})
            raw = path.read_bytes(); self.assertEqual(json.loads(raw), {'value': 1})
            with self.assertRaises(DomainError): retry._publish(path, {'value': 2})
            self.assertEqual(path.read_bytes(), raw)
            self.assertEqual([p.name for p in Path(directory).iterdir()], ['attempt.json'])

    def test_four_explicit_preparations_restore_and_preserve_prior_bundle_and_store_bytes(self):
        fixture = previous_tests.GenericRepairSessionTests('test_explicit_generic_prepare_and_reopen_preserve_history_and_start_no_work')
        fixture.setUp(); self.addCleanup(fixture.doCleanups); f = fixture.f
        f.prepare(); original_bundle = f.bundle_path.read_bytes()
        def derived(layout, failed, previous, base, raw_sha, attempt, directory):
            binding = {'attempt': attempt, 'core_utilization': 35-5*attempt, 'failed_stage': 'layout',
                'failed_run_id': failed['id'], 'previous_bundle_sha256': raw_sha,
                'layout_record_sha256': layout['record_hash']}
            return {'physical': {'profile': {'profile_version': new.PROFILE}, 'generic_retry_source_binding': binding},
                    'drc': {'attempt': attempt, 'physical_runtime': binding}, 'lvs': {'attempt': attempt, 'physical_runtime': binding}}
        with patch.object(retry, '_derive', side_effect=derived):
            for attempt in (1, 2, 3, 4):
                source = failed_layout(runtime=copy.deepcopy(f.server.physical_workflow.tool_configuration),
                                       identifier=f'layout-generic-repeat-{attempt}')
                source['revision_id'] = f.revision
                source['runtime_configuration'] = copy.deepcopy(f.server.physical_workflow.tool_configuration)
                source['runtime_configuration_sha256'] = object_hash(source['runtime_configuration']); checksum(source)
                f.save_layout_failure(source)
                before = {path: path.read_bytes() for path in (*f.directory.iterdir(), *f.store_path.iterdir())}
                status = session.prepare_retry(f.server, source['id'], f.revision)
                self.assertEqual(status['retry_attempt'], attempt); self.assertEqual(status['core_utilization'], 35-5*attempt)
                self.assertEqual({path: path.read_bytes() for path in before}, before)
                self.assertEqual(f.bundle_path.read_bytes(), original_bundle)
                restored, opened = session.load_repair_configurations(f.store, f.base, f.directory,
                                                        'software-qa-project', 'software-qa-system')
                self.assertTrue(opened['configured'], opened.get('error')); self.assertEqual(opened['retry_attempt'], attempt)
                self.assertEqual(restored[2], f.server.physical_workflow.tool_configuration)
                with self.assertRaises(DomainError): session.prepare_retry(f.server, source['id'], f.revision)
            f.server.workspace.identity['read_only'] = True
            with self.assertRaises(DomainError): session.prepare_retry(f.server, source['id'], f.revision)

    def test_failure_admission_requires_complete_native_electrical_only_evidence(self):
        source = failed_layout(); previous = [None]*6; previous[2] = copy.deepcopy(source['runtime_configuration'])
        with patch.object(session, '_saved', return_value={'runs': [source], 'reviews': []}), \
             patch('hullcirq.presentation_revision.same_source_design'), \
             patch('hullcirq.physical_workflow.validate_failed_physical_proof') as proof:
            run, layout = retry._record(None, 'layout', source['id'], source['revision_id'], previous, None)
            self.assertEqual(run, source); self.assertEqual(layout, source); proof.assert_called_once()
        mutations = [lambda r: r.update(execution_status='Failed'), lambda r: r.update(review_status='Accepted'),
            lambda r: r.update(software_qa_fixture=True), lambda r: r.update(error={'message': 'failed launch'}),
            lambda r: r['checks'].update(technology_mapping_executed=False),
            lambda r: r['checks'].update(upstream_technology_mapping_reused=True),
            lambda r: r['checks'].update(software_qa_fixture=True),
            lambda r: r['checks']['checks']['timing'].update(validation_status='Failed'),
            lambda r: r['checks']['checks'].update(routing=None),
            lambda r: r['checks'].update(commands=[])]
        for mutate in mutations:
            changed = copy.deepcopy(source); mutate(changed); checksum(changed)
            with patch.object(session, '_saved', return_value={'runs': [changed], 'reviews': []}), \
                 patch('hullcirq.presentation_revision.same_source_design'), \
                 patch('hullcirq.physical_workflow.validate_failed_physical_proof') as proof:
                with self.assertRaises(DomainError):
                    retry._record(None, 'layout', changed['id'], changed['revision_id'], previous, None)
                proof.assert_not_called()
        wrong = list(previous); wrong[2] = {'other': 'runtime'}
        with patch.object(session, '_saved', return_value={'runs': [source], 'reviews': []}), \
             patch('hullcirq.presentation_revision.same_source_design'), \
             patch('hullcirq.physical_workflow.validate_failed_physical_proof'):
            with self.assertRaises(DomainError): retry._record(None, 'layout', source['id'], source['revision_id'], wrong, None)

    def test_no_retry_files_preserve_legacy_status_and_require_no_store_access(self):
        with tempfile.TemporaryDirectory() as directory:
            base = (None,)*6; status = {'configured': False, 'bundle_present': False, 'error': None}
            self.assertEqual(retry.restore(None, base, directory, 'p', 's', base, status), (base, status))

    def test_missing_hole_or_unknown_retry_name_is_fail_closed_not_skipped(self):
        for name in ('generic_physical_retry_000002.json', 'generic_physical_retry_bad.json'):
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory)/name; path.write_bytes(b'{}'); before = path.read_bytes()
                base = (None,)*6
                result, status = retry.restore(None, base, directory, 'p', 's', base, {'configured': True})
                self.assertEqual(result, base); self.assertFalse(status['configured']); self.assertIsNotNone(status['error'])
                self.assertEqual(path.read_bytes(), before)

    def test_chain_reconstructs_two_preparations_and_rejects_rehashed_tampering(self):
        # File/session plumbing is exercised with explicit mocked native-proof
        # callbacks, never promoted to actual circuit evidence.
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            base = tuple({'slot': n} for n in range(6))
            prior = list(copy.deepcopy(base)); prior[2] = {'profile': {'profile_version': old.PROFILE}}
            first = {'physical': prior[2], 'drc': prior[3], 'lvs': prior[4]}
            original = directory/session.BUNDLE_NAME; original.write_bytes(b'{"retained":true}')
            raw = original.read_bytes(); rows = []
            for n in (1, 2):
                binding = {'attempt': n, 'failed_stage': 'layout', 'failed_run_id': f'failure-{n}'}
                derived = {'physical': {'profile': {'profile_version': new.PROFILE}, 'generic_retry_source_binding': binding},
                           'drc': {'attempt': n}, 'lvs': {'attempt': n}}
                bundle = checksum({'schema': retry.SCHEMA, 'project_id': 'project', 'system_id': 'system',
                    'revision_id': 'revision', 'base_configuration_sha256': session._base_hashes(base),
                    'previous_bundle_sha256': hashlib.sha256(raw).hexdigest(), 'source_identity': binding,
                    'configurations': derived, 'actor': 'explicit_GUI_action', 'created_at': 'software-fixture'})
                path = directory/f'{retry.PREFIX}{n:06d}.json'; path.write_text(json.dumps(bundle), encoding='utf-8')
                raw = path.read_bytes(); rows.append((path, derived))
            status = {'configured': True, 'session_schema': session.GENERIC_SCHEMA}
            def derive(layout, failed, previous, base_arg, sha, attempt, directory_arg):
                return copy.deepcopy(rows[attempt-1][1])
            with patch.object(session, '_bundle_path', return_value=original), patch.object(session, '_validate_bundle', return_value=first), \
                 patch.object(retry, '_record', return_value=({}, {})), patch.object(retry, '_derive', side_effect=derive), \
                 patch.object(retry, '_status', return_value={'configured': True, 'retry_attempt': 2}):
                restored, outcome = retry.restore(None, base, directory, 'project', 'system', tuple(prior), status)
                self.assertTrue(outcome['configured']); self.assertEqual(restored[2], rows[-1][1]['physical'])
                path = rows[1][0]; changed = json.loads(path.read_text()); changed['configurations']['drc']['attempt'] = 99
                checksum(changed); path.write_text(json.dumps(changed), encoding='utf-8'); before = path.read_bytes()
                restored, outcome = retry.restore(None, base, directory, 'project', 'system', tuple(prior), status)
                self.assertFalse(outcome['configured']); self.assertEqual(restored, base); self.assertEqual(path.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
