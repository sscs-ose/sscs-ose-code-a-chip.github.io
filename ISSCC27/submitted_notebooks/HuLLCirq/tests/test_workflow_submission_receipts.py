"""Common S05/S06/S09/S10 receipts with failed adapters; never native evidence."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from hullcirq.domain import DomainError, IMPLEMENTED_STAGES
from hullcirq.execution_submissions import run_submission
from hullcirq.observation import readonly_observation_scope
from hullcirq.store import ProjectStore, _io_path
from hullcirq.verification import object_hash
from hullcirq.workflow import WorkflowManager
from hullcirq.global_workflow import GlobalWorkflowManager
from hullcirq.physical_tools import artifact_files
from test_s05_batch import SoftwareCandidates
import test_s06_batch as s06_fixtures
import test_global_workflow as global_fixtures

ROOT = Path(__file__).resolve().parents[1]
FAILED = {'validation_status':'Failed','executed':False,'exit_code':1,'diagnostics':[{'code':'isolated_adapter_failure','message':'Software fixture; no process executed.'}],'netlist':None,'netlist_sha256':None,'scope':'software_fixture_no_native_or_simulation'}

class WorkflowSubmissionReceiptTests(unittest.TestCase):
    def setUp(self):
        qa=ROOT/'.work/qa';qa.mkdir(parents=True,exist_ok=True)
        self.temporary=tempfile.TemporaryDirectory(prefix='workflow-receipt-',dir=qa)
        self.root=Path(self.temporary.name);self.qa=qa;self.managers=[]
        self.addCleanup(self.cleanup)
        for target in ('subprocess.Popen','socket.socket.connect'):
            guard=patch(target,side_effect=AssertionError('No process/network permitted in receipt fixtures'));guard.start();self.addCleanup(guard.stop)
        defaults=patch.object(tempfile,'tempdir',str(self.root));defaults.start();self.addCleanup(defaults.stop)
        adapter=self.root/'fake-adapter';adapter.mkdir()
        allocation=patch('hullcirq.workflow.allocate_synthesis_directory',return_value=adapter);allocation.start();self.addCleanup(allocation.stop)

    def cleanup(self):
        for manager in self.managers:
            manager.close()
            for name in ('_worker','_batch_worker'):
                worker=getattr(manager,name,None)
                if worker is not None and worker.ident is not None:
                    worker.join(5);self.assertFalse(worker.is_alive())
        self.assertEqual(self.root.resolve().parent,self.qa.resolve());self.assertTrue(self.root.name.startswith('workflow-receipt-'));self.assertFalse(self.root.is_symlink())
        if _io_path(self.root).exists():
            list(artifact_files(self.root,reject_links=True));shutil.rmtree(_io_path(self.root))
        self.temporary.cleanup()

    def local(self, stage='local_synthesis', batch=False, deep=False):
        if stage=='local_netlist_simulation':
            base=s06_fixtures.S06BatchTests('runTest');base.setUp();self.addCleanup(base.doCleanups)
            store,candidates,manager=base.store,base.candidates,base.manager
        else:
            folder=self.root/'project'
            if deep:
                while len(str(folder/'workflow.json'))<330:folder/='保存先é_'+'x'*28
            store=ProjectStore(folder,ROOT/'examples/m1_two_nodes.json')
            for first in IMPLEMENTED_STAGES:
                record=store.validate(first,store.envelope()['revision']['id'])['runs'][-1];store.review(record['id'],'accepted','Isolated software fixture input.')
            candidates=SoftwareCandidates(store)
            manager=WorkflowManager(store,candidates,compiler={'kind':'native','executable':'not-invoked'},synthesizer={'kind':'native','executable':'not-invoked'})
        self.managers.append(manager)
        revision=store.envelope()['revision']['id'];node=store.envelope()['design']['nodes'][0]['id']
        if batch:body={'revision_id':revision,'request_id':'owned-request-'+stage,'stage_id':stage};route='workflow/batches/start'
        else:body={'stage_id':stage,'node_id':node,'candidate_id':candidates.selected[node],'revision_id':revision};route='workflow/start'
        return SimpleNamespace(manager=manager,store=store,candidates=candidates,body=body,route=route,batch=batch,global_case=False)

    def global_case(self,stage='global_synthesis'):
        base=global_fixtures.GlobalWorkflowTests('runTest');base.setUp();self.addCleanup(base.doCleanups)
        prior=base.run_stage() if stage=='global_netlist_simulation' else None
        self.managers.append(base.manager)
        return SimpleNamespace(manager=base.manager,store=base.store,base=base,body={'stage_id':stage,'global_job_id':base.job['id'],'synthesis_run_id':prior['id'] if prior else None,'revision_id':base.store.envelope()['revision']['id']},route='global-workflow/runs',batch=False,global_case=True)

    def submit(self,f,key='owned-execution-001',body=None):
        body=copy.deepcopy(f.body if body is None else body);body['submission_id']=key
        if f.global_case: create=lambda ticket:f.manager.start(body['stage_id'],body['global_job_id'],body.get('synthesis_run_id'),body.get('revision_id'),_submission=ticket)
        elif f.batch:create=lambda ticket:f.manager.start_batch(body['revision_id'],body['request_id'],body['stage_id'],_submission=ticket)
        else:create=lambda ticket:f.manager.start(body['stage_id'],body['node_id'],body['candidate_id'],body['revision_id'],_submission=ticket)
        return run_submission(f.manager,f.route,body,create)

    def settle(self,f):
        worker=f.manager._batch_worker if f.batch else f.manager._worker
        self.assertIsNotNone(worker);worker.join(10);self.assertFalse(worker.is_alive())

    def native_failures(self):
        class Stack:
            def __enter__(inner):
                inner.patches=[patch(name,return_value=copy.deepcopy(FAILED)) for name in ('hullcirq.workflow.synthesize_generic','hullcirq.workflow.verify_behavior','hullcirq.global_workflow.synthesize_global_generic','hullcirq.global_workflow.check_global_netlist')]
                inner.mocks=[p.start() for p in inner.patches];return inner.mocks
            def __exit__(inner,*args):
                for p in reversed(inner.patches):p.stop()
        return Stack()

    def durable(self,f):return _io_path(f.manager.path).read_bytes(),_io_path(f.manager.path).stat().st_mtime_ns

    def exercise(self,f):
        old={r['id']:copy.deepcopy(r) for pool in ('runs','batches') for r in f.manager._state.get(pool,[])}
        with self.native_failures() as mocks:
            first=self.submit(f);identifier=first['execution_submission']['record_id'];self.settle(f)
            record=next(r for pool in ('runs','batches') for r in f.manager._state.get(pool,[]) if r['id']==identifier)
            self.assertEqual(record['validation_status'],'Failed');self.assertEqual(record['submission_id'],'owned-execution-001')
            count=sum(x.call_count for x in mocks);self.assertGreater(count,0);before=self.durable(f)
            replay=self.submit(f)['execution_submission'];self.assertEqual(replay['record_id'],identifier);self.assertTrue(replay['replayed']);self.assertEqual(sum(x.call_count for x in mocks),count);self.assertEqual(self.durable(f),before)
            changed={**f.body,'revision_id':'different-frozen-revision'}
            with self.assertRaises(DomainError) as error:self.submit(f,body=changed)
            self.assertEqual(error.exception.code,'submission_conflict');self.assertFalse(getattr(error.exception,'execution_start_rejected_before_creation',False));self.assertEqual(self.durable(f),before)
        for pool in ('runs','batches'):
            for record in f.manager._state.get(pool,[]):
                if record['id'] in old:self.assertEqual(record,old[record['id']]);self.assertNotIn('submission_id',record)
        return identifier

    def test_s05_single_failed_replay_conflict_and_deep_history(self):
        f=self.local(deep=True);self.exercise(f);before=self.durable(f);f.manager.close();replacement=WorkflowManager(f.store,f.candidates,f.manager.compiler,f.manager.synthesizer);self.managers.append(replacement);f.manager=replacement;self.assertEqual(self.durable(f),before);self.assertTrue(self.submit(f)['execution_submission']['replayed']);self.assertEqual(self.durable(f),before)

    def test_s06_single_failed_replay_never_repeats_simulation(self):self.exercise(self.local('local_netlist_simulation'))
    def test_s05_batch_receipt_binds_only_new_batch(self):self.exercise(self.local(batch=True))
    def test_s06_batch_receipt_binds_only_new_batch(self):self.exercise(self.local('local_netlist_simulation',batch=True))
    def test_s09_failed_replay_conflict_keeps_original_source_plan(self):self.exercise(self.global_case())
    def test_s10_failed_replay_conflict_keeps_exact_adopted_prior(self):self.exercise(self.global_case('global_netlist_simulation'))

    def test_postpersist_4xx_is_not_proof_of_no_start(self):
        f=self.local()
        with self.native_failures() as mocks:
            with patch.object(f.manager,'_result_envelope',side_effect=DomainError('fixture_view_error','View failed after persistence.',409)):
                with self.assertRaises(DomainError) as caught:self.submit(f)
            self.assertFalse(getattr(caught.exception,'execution_start_rejected_before_creation',False));self.settle(f);self.assertEqual(len(f.manager._state['runs']),1)
            replay=self.submit(f)['execution_submission'];self.assertTrue(replay['replayed']);self.assertEqual(replay['record_id'],f.manager._state['runs'][0]['id']);self.assertEqual(sum(x.call_count for x in mocks),1)

    def test_postpersist_non_json_transport_error_retains_exact_receipt(self):
        f=self.local()
        with self.native_failures() as mocks:
            with patch.object(f.manager,'_result_envelope',side_effect=OSError('fixture lost response')):
                with self.assertRaises(OSError):self.submit(f)
            self.settle(f);self.assertTrue(self.submit(f)['execution_submission']['replayed']);self.assertEqual(len(f.manager._state['runs']),1);self.assertEqual(sum(x.call_count for x in mocks),1)

    def test_new_nonce_cannot_bind_legacy_batch_request_id(self):
        f=self.local(batch=True)
        with self.native_failures() as mocks:
            f.manager.start_batch(f.body['revision_id'],f.body['request_id'],f.body['stage_id']);self.settle(f);before=copy.deepcopy(f.manager._state['batches'][0]);count=sum(x.call_count for x in mocks)
            with self.assertRaises(DomainError) as caught:self.submit(f)
            self.assertEqual(caught.exception.code,'submission_conflict');self.assertTrue(caught.exception.execution_start_rejected_before_creation);self.assertEqual(f.manager._state['batches'][0],before);self.assertNotIn('submission_id',before);self.assertEqual(len(f.manager._state['batches']),1);self.assertEqual(sum(x.call_count for x in mocks),count)

    def test_terminal_reopen_and_view_do_not_migrate_legacy_bytes(self):
        f=self.local();before=self.durable(f);self.assertNotIn('execution_submissions',f.manager._state);f.manager.close();m=WorkflowManager(f.store,f.candidates,f.manager.compiler,f.manager.synthesizer);self.managers.append(m);m.envelope();self.assertEqual((_io_path(m.path).read_bytes(),_io_path(m.path).stat().st_mtime_ns),before);self.assertNotIn('execution_submissions',m._state)

    def test_tampered_tagged_record_is_rejected_without_rewriting(self):
        f=self.local()
        with self.native_failures():self.submit(f);self.settle(f)
        f.manager.close();value=json.loads(_io_path(f.manager.path).read_text(encoding='utf-8'));value['runs'][-1]['submission_id']='different-nonce';value['runs'][-1]['record_hash']=object_hash({k:v for k,v in value['runs'][-1].items() if k!='record_hash'});_io_path(f.manager.path).write_text(json.dumps(value),encoding='utf-8');before=self.durable(f)
        with self.assertRaises(DomainError):WorkflowManager(f.store,f.candidates,f.manager.compiler,f.manager.synthesizer)
        self.assertEqual(self.durable(f),before)

    def test_server_aggregate_uses_exact_route_without_cross_route_receipts(self):
        from hullcirq.server import execution_submission_metadata
        f=self.local(batch=True)
        with self.native_failures():self.submit(f);self.settle(f)
        names=('generation','generation_batches','repair_analysis','workflow','global_generation','global_workflow','physical_workflow','drc_workflow','lvs_workflow','postlayout_workflow')
        idle=SimpleNamespace(lock=threading.RLock(),_committed={})
        server=SimpleNamespace(**{name:idle for name in names});server.workflow=f.manager
        metadata=execution_submission_metadata(server)
        exact=metadata['execution_submission_receipts']['workflow/batches/start']
        self.assertIn('owned-execution-001',exact)
        self.assertEqual(metadata['execution_submission_receipts']['workflow/start'],{})
        self.assertEqual(exact['owned-execution-001']['record_id'],f.manager._state['batches'][-1]['id'])

    def test_empty_global_protocol_view_does_not_create_default_file_or_receipt(self):
        f=self.global_case();self.assertFalse(_io_path(f.manager.path).exists())
        # HTTP GETs use the existing ephemeral observation graph; direct
        # action-side observation intentionally keeps its legacy persistence.
        with readonly_observation_scope():
            first=f.manager.envelope();second=f.manager.envelope()
        self.assertEqual(first,second);self.assertFalse(_io_path(f.manager.path).exists());self.assertNotIn('execution_submissions',f.manager._state)

    def test_global_terminal_restart_replays_receipt_without_new_worker(self):
        f=self.global_case();identifier=self.exercise(f);before=self.durable(f);f.manager.close();f.manager=f.base.new_manager();self.managers.append(f.manager);self.assertEqual(self.durable(f),before);self.assertEqual(self.submit(f)['execution_submission']['record_id'],identifier);self.assertEqual(self.durable(f),before)

if __name__=='__main__':unittest.main()