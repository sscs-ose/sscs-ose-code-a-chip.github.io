"""Isolated terminal-correction setup QA. No EDA, SDK, model or browser."""
import copy
from contextlib import ExitStack, nullcontext
import io
import json
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from hullcirq import lvs_repair_session as session
from hullcirq.domain import DomainError
from hullcirq.verification import object_hash
from hullcirq.workspace_server import _postlayout_profile_directory
from hullcirq.workspace import blank_design
from hullcirq.server import RequestHandler
from hullcirq.workspace_server import WorkspaceRuntime
from hullcirq import workspace_server

ROOT = Path(__file__).resolve().parents[1]


def checksum(value):
    value['record_hash'] = object_hash({k: v for k, v in value.items() if k != 'record_hash'})
    return value


class Manager:
    def __init__(self, configuration=None):
        self.tool_configuration = copy.deepcopy(configuration); self.lock = threading.RLock()
        self._worker = None; self._storage_error = None; self.active = False; self.current = True
        self._state = {'runs': []}; self.observations = 0
    def is_active(self): return self.active
    def _source_locks(self): return nullcontext()
    def observe_design(self): self.observations += 1
    def _decorate(self, run): return {**run, 'freshness': 'Current' if self.current else 'Stale'}


class LvsRepairSessionTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(dir=ROOT / '.work/qa'); self.addCleanup(temp.cleanup)
        self.root = Path(temp.name); self.directory = self.root / 'runtime_profiles/systemscope'
        self.system = self.root / 'system'; self.system.mkdir()
        self.revision = 'revision-software-independent'
        self.design = blank_design('project-software', 'Software QA', 'system-software', 'Software QA', 'independent_top')
        physical = {'profile': 'SOFTWARE_QA_PHYSICAL', 'working_directory': str(self.root / 'old-physical')}
        original = {'physical_runtime': physical, 'profile': {'profile_version': 'SOFTWARE_QA_OLD_LVS'}, 'working_directory': str(self.root / 'old-lvs')}
        self.base = (None, None, physical, {'physical_runtime': physical}, original, None)
        common = {'revision_id': self.revision, 'execution_status': 'Completed', 'validation_status': 'Passed',
                  'review_status': 'Accepted', 'source_key': 'SOFTWARE_QA_KEY', 'acceptance_epoch': 1, 'checks': {}, 'error': None}
        layout = checksum({**copy.deepcopy(common), 'id': 'physical-software', 'evidence_kind': 'trusted_fixed_tool_execution', 'runtime_configuration': physical})
        drc = checksum({**copy.deepcopy(common), 'id': 'drc-software', 'evidence_kind': 'trusted_fixed_drc_execution', 'layout_snapshot': layout})
        feedback = [{'description': 'device missing 1 terminal;\n connecting remainder to node '+supply, 'geometry': ['SOFTWARE_QA_ONLY']}
                    for supply in ('VGND', 'VPWR')]
        lvs = checksum({**copy.deepcopy(common), 'id': 'lvs-software', 'evidence_kind': 'trusted_fixed_lvs_execution',
            'layout_snapshot': layout, 'drc_snapshot': drc, 'runtime_configuration': original,
            'source_inputs': {'SOFTWARE_QA_ONLY': True}, 'input_gds_sha256': 'a'*64, 'input_netlist_sha256': 'b'*64,
            'checks': {'summary': {'extraction': {'feedback': feedback}}}})
        self.records = {'physical': layout, 'drc': drc, 'lvs': lvs}
        self.histories = {name: {'runs': [record], 'reviews': [{'run_id': record['id'], 'decision': 'accepted',
            'source_key': record['source_key'], 'acceptance_epoch': record['acceptance_epoch']}]} for name, record in self.records.items()}
        self.write_histories()
        self.store = SimpleNamespace(state_path=self.system/'state.json',
            envelope=lambda: {'revision': {'id': self.revision}, 'design': copy.deepcopy(self.design)},
            snapshot=lambda identifier: copy.deepcopy(self.design))
        self.server = SimpleNamespace(execution_lock=threading.RLock(), store=self.store)
        for name in session.MANAGERS: setattr(self.server, name, Manager())
        manager = self.server.lvs_workflow; manager._state['runs'] = [copy.deepcopy(lvs)]
        manager.tool_configuration = copy.deepcopy(original)
        manager._source_state = lambda: ('SOFTWARE_QA_KEY', {'layout': self.records['physical'], 'drc': self.records['drc']}, None)
        self.server.workspace = SimpleNamespace(context=SimpleNamespace(), configurations=copy.deepcopy(self.base),
            registry=SimpleNamespace(root=self.root), identity={'project_id': 'project-software', 'system_id': 'system-software', 'read_only': False})
        self.directory = _postlayout_profile_directory(self.root, 'project-software', 'system-software')
        self.path = self.directory/session.BUNDLE_NAME
        (self.root/'configs').mkdir(); (self.root/'configs/lvs_profile_sky130_v3.json').write_text(json.dumps({'profile_version': session.PROFILE}), encoding='utf-8')
        self.stack = ExitStack(); self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(session, 'ROOT', self.root))
        self.proofs = [self.stack.enter_context(patch(name)) for name in (
            'hullcirq.physical_workflow.validate_physical_proof', 'hullcirq.drc_workflow.validate_drc_proof',
            'hullcirq.lvs_workflow.validate_source_snapshot', 'hullcirq.lvs_workflow.validate_lvs_proof')]
        self.stack.enter_context(patch('hullcirq.lvs_tools.configuration_projection'))
        self.stack.enter_context(patch('hullcirq.physical_repair_session.load_repair_configurations', return_value=(self.base, {'error': None})))
        self.stack.enter_context(patch('hullcirq.lvs_tools._fixed_profile', side_effect=lambda p: p))
        self.stack.enter_context(patch('hullcirq.lvs_tools.lvs_capability', return_value={'available': True}))

    def write_histories(self):
        for name, state in self.histories.items():
            (self.system/(name+'_workflow.json')).write_text(json.dumps(state), encoding='utf-8')

    def prepare(self):
        # Preserve the historical v3 session fixture. New GUI initial actions
        # use the latest fixed direct recipe, qualified in separate tests.
        return session._prepare_v3(self.server, 'physical-software', 'drc-software', 'lvs-software', self.revision)

    def restore(self):
        return session.load_repair_configuration(self.store, self.base, self.directory, 'project-software', 'system-software')

    def test_prepare_restores_after_physical_profile_and_preserves_sources_without_tools(self):
        before = {path: path.read_bytes() for path in self.system.iterdir()}
        status = self.prepare(); self.assertTrue(status['configured'])
        self.assertEqual(status['profile_version'], session.PROFILE)
        configuration = self.server.lvs_workflow.tool_configuration
        self.assertEqual(configuration['physical_runtime'], self.base[2])
        self.assertEqual(configuration['repair_source_binding'], session._identity(self.records))
        self.assertEqual(before, {path: path.read_bytes() for path in before})
        raw = self.path.read_bytes(); restored, status = self.restore()
        self.assertTrue(status['configured'], status['error']); self.assertEqual(restored[4], configuration)
        self.assertEqual(restored[:4], self.base[:4]); self.assertEqual(restored[5], self.base[5])
        self.assertEqual(self.path.read_bytes(), raw)
        self.assertTrue(all(proof.call_count >= 2 for proof in self.proofs))

    def test_same_preparation_is_idempotent_without_overwrite(self):
        self.prepare(); raw = self.path.read_bytes(); mtime = self.path.stat().st_mtime_ns
        self.server.lvs_workflow.current = False  # Original record becomes stale after explicit preparation.
        self.assertTrue(self.prepare()['configured'])
        self.assertEqual(self.path.read_bytes(), raw); self.assertEqual(self.path.stat().st_mtime_ns, mtime)
        with self.assertRaises(DomainError):
            session.prepare_repair(self.server, 'physical-software', 'drc-software', 'different-lvs', self.revision)
        self.assertEqual(self.path.read_bytes(), raw)

    def test_changed_bundle_runtime_source_or_system_does_not_restore_or_overwrite(self):
        self.prepare(); raw = self.path.read_bytes()
        for mutate in (lambda b: b['configuration'].update(working_directory='arbitrary'),
                       lambda b: b.update(project_id='other-project'),
                       lambda b: b['source_identity'].update(historical_lvs_execution_sha256='0'*64)):
            changed = json.loads(raw); mutate(changed); checksum(changed)
            self.path.write_text(json.dumps(changed), encoding='utf-8'); payload = self.path.read_bytes()
            restored, status = self.restore()
            self.assertFalse(status['configured']); self.assertEqual(restored, self.base)
            self.assertEqual(self.path.read_bytes(), payload)

    def test_busy_readonly_stale_revision_cleanup_and_upstream_mismatch_create_no_bundle(self):
        for target, attr, value in ((self.server.generation, 'active', True), (self.server.lvs_workflow, 'current', False),
                                    (self.server.drc_workflow, '_storage_error', {'code': 'error'})):
            original = getattr(target, attr); setattr(target, attr, value)
            with self.assertRaises(DomainError): self.prepare()
            setattr(target, attr, original); self.assertFalse(self.path.exists())
        self.server.workspace.identity['read_only'] = True
        with self.assertRaises(DomainError): self.prepare()
        self.server.workspace.identity['read_only'] = False
        with self.assertRaises(DomainError): session.prepare_repair(self.server, 'physical-software', 'drc-software', 'lvs-software', 'stale-revision')
        with self.assertRaises(DomainError): session.prepare_repair(self.server, 'wrong-layout', 'drc-software', 'lvs-software', self.revision)
        self.assertFalse(self.path.exists())

    def test_proof_warning_or_durable_adoption_changes_fail_closed(self):
        original = copy.deepcopy(self.histories)
        for label in ('warning', 'adoption', 'proof'):
            with self.subTest(label=label):
                self.histories = copy.deepcopy(original)
                self.records = {name: state['runs'][0] for name, state in self.histories.items()}
                self.server.lvs_workflow._state['runs'] = [copy.deepcopy(self.records['lvs'])]
                if label == 'warning':
                    self.records['lvs']['checks']['summary']['extraction']['feedback'][0]['description'] = 'Unknown warning'
                    checksum(self.records['lvs'])
                elif label == 'adoption':
                    self.histories['lvs']['reviews'][-1]['decision'] = 'changes_requested'
                else:
                    self.proofs[-1].side_effect = DomainError('bad-proof', 'bad-proof')
                self.write_histories()
                with self.assertRaises(DomainError): self.prepare()
                self.assertFalse(self.path.exists())

    def test_restore_does_not_require_original_lvs_to_remain_latest(self):
        self.prepare(); self.histories['lvs']['runs'].append({'id': 'later-versioned-run'})
        self.write_histories(); restored, status = self.restore()
        self.assertTrue(status['configured'], status['error']); self.assertEqual(restored[4]['profile']['profile_version'], session.PROFILE)

    def test_eligibility_is_readonly_authoritative_and_unrelated_warnings_do_not_qualify(self):
        before = copy.deepcopy(self.server.lvs_workflow._state)
        meta = session._initial_eligibility(self.server)
        self.assertTrue(meta['available']); self.assertTrue(meta['eligible'], meta['blocked_reason'])
        self.assertEqual(meta['source']['source_lvs_record_hash'], self.records['lvs']['record_hash'])
        self.assertEqual(self.server.lvs_workflow._state, before); self.assertFalse(self.path.exists())
        self.server.lvs_workflow._state['runs'][-1]['checks']['summary']['extraction']['feedback'] = []
        checksum(self.server.lvs_workflow._state['runs'][-1])
        self.assertFalse(session._initial_eligibility(self.server)['eligible'])
        self.server.workspace.identity['read_only'] = True
        self.assertFalse(session._initial_eligibility(self.server)['available'])


class LvsRepairRequestTests(unittest.TestCase):
    """Exercise the real dispatch/admission methods without an HTTP socket."""
    body = {'layout_run_id': 'physical-software', 'drc_run_id': 'drc-software',
            'source_lvs_run_id': 'lvs-software', 'revision_id': 'revision-software'}

    def handler(self, body=None, *, token='session-software', read_only=False, origin='http://127.0.0.1:8772'):
        raw = json.dumps(self.body if body is None else body).encode('utf-8')
        workspace = SimpleNamespace(identity={'session_id': 'session-software', 'read_only': read_only}, context=object())
        workspace.require_session = lambda handler, mutation=False: WorkspaceRuntime.require_session(workspace, handler, mutation)
        handler = SimpleNamespace(path='/api/lvs-workflow/repair-profile',
            server=SimpleNamespace(server_address=('127.0.0.1', 8772), store=object(),
                                   execution_lock=threading.RLock(), workspace=workspace),
            headers={'Host': '127.0.0.1:8772', 'Origin': origin, 'X-HuLLCirq-Session': token,
                     'Content-Type': 'application/json', 'Content-Length': str(len(raw))},
            connection=SimpleNamespace(settimeout=Mock()), rfile=io.BytesIO(raw),
            _require_global_workflow_idle=Mock(), _require_other_execution_idle=Mock(),
            _json=Mock(), _error=Mock(), _discard_rejected_body=Mock(), log_error=Mock())
        handler._check_host = lambda: RequestHandler._check_host(handler)
        handler._read_body = lambda: RequestHandler._read_body(handler)
        return handler

    def test_exact_route_only_prepares_and_returns_observation(self):
        handler = self.handler()
        with patch.object(session, 'prepare_repair') as prepare, \
                patch('hullcirq.server.project_envelope', return_value={'SOFTWARE_QA_ONLY': True}) as envelope:
            RequestHandler._do_POST(handler)
        handler._error.assert_not_called(); prepare.assert_called_once_with(handler.server,
            self.body['layout_run_id'], self.body['drc_run_id'], self.body['source_lvs_run_id'], self.body['revision_id'])
        handler._require_global_workflow_idle.assert_called_once(); handler._require_other_execution_idle.assert_called_once()
        envelope.assert_called_once_with(handler.server); handler._json.assert_called_once_with({'SOFTWARE_QA_ONLY': True})

    def test_extra_profile_path_expected_values_and_missing_ids_are_rejected(self):
        for changed in ({**self.body, 'profile': {}}, {**self.body, 'path': 'arbitrary'},
                        {**self.body, 'expected_outputs': []}, {k: v for k, v in self.body.items() if k != 'revision_id'}):
            with self.subTest(keys=sorted(changed)):
                handler = self.handler(changed)
                with patch.object(session, 'prepare_repair') as prepare:
                    RequestHandler._do_POST(handler)
                prepare.assert_not_called(); self.assertEqual(handler._error.call_args.args[0].code, 'lvs_repair_request_invalid')

    def test_foreign_stale_session_readonly_and_cross_origin_never_prepare(self):
        for options, code in (({'token': 'old-session'}, 'workspace_session_changed'),
                              ({'read_only': True}, 'read_only_system'),
                              ({'origin': 'http://foreign.invalid'}, 'invalid_origin')):
            with self.subTest(code=code):
                handler = self.handler(**options)
                with patch.object(session, 'prepare_repair') as prepare:
                    RequestHandler._do_POST(handler)
                prepare.assert_not_called(); self.assertEqual(handler._error.call_args.args[0].code, code)

    def test_busy_admission_never_prepares_or_retries(self):
        handler = self.handler()
        handler._require_other_execution_idle.side_effect = DomainError('busy-software', 'Software QA busy', 409)
        with patch.object(session, 'prepare_repair') as prepare:
            RequestHandler._do_POST(handler)
        prepare.assert_not_called(); self.assertEqual(handler._error.call_args.args[0].code, 'busy-software')


class LvsRepairWorkspaceTests(unittest.TestCase):
    def test_open_restores_physical_then_lvs_before_building_any_manager(self):
        temp = tempfile.TemporaryDirectory(dir=ROOT / '.work/qa'); self.addCleanup(temp.cleanup)
        root = Path(temp.name); events = []
        original = ('compiler', 'synth', 'old-physical', 'old-drc', 'old-lvs', 'old-postlayout')
        physical = ('compiler', 'synth', 'fixed-physical', 'fixed-drc', 'physical-fixed-lvs', 'fixed-postlayout')
        corrected = (*physical[:4], 'terminal-corrected-lvs', physical[5])
        runtime = WorkspaceRuntime.__new__(WorkspaceRuntime)
        runtime.server = SimpleNamespace(generation_previews={}); runtime.configurations = original; runtime.context = None
        runtime.folder_picker = SimpleNamespace(cancel_session=Mock()); runtime.identity = {'session_id': 'previous-software'}
        runtime.registry = SimpleNamespace(root=root, resolve_system=lambda *args: {'path': root/'independent-system', 'read_only': False})
        store = object(); context = SimpleNamespace(store=store)
        for name in workspace_server.MANAGERS: setattr(context, name, SimpleNamespace())
        def physical_load(actual_store, configurations, *args):
            self.assertIs(actual_store, store); self.assertEqual(configurations, original); events.append('physical')
            return physical, {'configured': True, 'error': None}
        def lvs_load(actual_store, configurations, *args):
            self.assertIs(actual_store, store); self.assertEqual(configurations, physical); events.append('lvs')
            return corrected, {'configured': True, 'bundle_present': True, 'error': None, 'profile_version': session.PROFILE}
        def build(actual_store, configurations, **kwargs):
            self.assertIs(actual_store, store); self.assertEqual(configurations, corrected); events.append('managers')
            return context
        with patch.object(workspace_server, 'ProjectStore', return_value=store), \
                patch('hullcirq.physical_repair_session.load_repair_configurations', side_effect=physical_load), \
                patch.object(session, 'load_repair_configuration', side_effect=lvs_load), \
                patch.object(workspace_server, 'build_context', side_effect=build):
            runtime.open('project-software', 'system-software')
        self.assertEqual(events, ['physical', 'lvs', 'managers'])
        self.assertEqual(runtime.server.lvs_repair_session['profile_version'], session.PROFILE)
        self.assertIs(runtime.context, context); self.assertFalse(runtime.identity['read_only'])
        runtime.close(); self.assertFalse(hasattr(runtime.server, 'lvs_repair_session'))


if __name__ == '__main__': unittest.main()
