"""Portable archive/replay guards with explicitly synthetic software fixtures.

Collector tool validators are mocked; no fixture is circuit evidence and no
EDA, user history or original artifact is modified by these tests.
"""
from contextlib import ExitStack
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
import collect_completion_proof as collector
import replay_completion_proof as replay
from hullcirq.verification import object_hash
from hullcirq.postlayout_workflow import POST_ROUTE_REQUIRED_FILES


def write(path, value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(value if isinstance(value,bytes) else (json.dumps(value,indent=2)+'\n').encode())


def seal(value):
    value.pop('record_hash',None)
    value['record_hash']=object_hash(value)
    return value


class CompletionArchiveTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name)
        self.data=self.root/'.work/project';self.before=self.root/'.work/before';self.output=self.root/'results/completion'
        self.plan={'software_qa_fixture':True,'scope':'SYNTHETIC ARCHIVE ONLY'}
        records={}
        for name in collector.STAGES:
            folder=self.root/'.work/tools'/name;folder.mkdir(parents=True)
            ids=POST_ROUTE_REQUIRED_FILES if name=='postlayout' else {'software-qa-report'}
            artifacts=[]
            for identifier in sorted(ids):
                raw=('SOFTWARE QA ONLY: '+identifier+'\n').encode()
                write(folder/identifier,raw)
                artifacts.append({'id':identifier,'relative_path':identifier,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'content_type':'text/plain'})
            run={'id':'SOFTWARE_QA_'+name,'revision_id':'SOFTWARE_QA_REVISION',
                 'execution_status':'Completed','validation_status':'Passed','review_status':'Accepted',
                 'source_key':'SOFTWARE_QA_SOURCE_'+name,'acceptance_epoch':1,
                 'checks':{'artifacts_directory':str(folder),'artifacts':artifacts}}
            if name in ('physical','postlayout'):
                run.update(verification_plan=self.plan,verification_plan_sha256=object_hash(self.plan),vector_hash='SOFTWARE_QA_VECTOR')
            if name=='physical':
                run.update(global_rtl_sha256='SOFTWARE_QA_RTL',source_manifest_sha256='SOFTWARE_QA_NODES',settings_sha256='SOFTWARE_QA_SETTINGS')
                run['runtime_configuration']={'profile':{'profile_version':'SOFTWARE_QA_PHYSICAL_PROFILE'}}
                run['checks']['implementation_kind']='resumed_post_GRT_route_repair'
            if name in ('drc','lvs'):
                run.update(layout_run_id=records['physical']['id'],layout_snapshot=copy.deepcopy(records['physical']),
                           layout_record_sha256=object_hash(records['physical']))
            if name=='lvs':
                run.update(drc_run_id=records['drc']['id'],drc_snapshot=copy.deepcopy(records['drc']),
                           drc_record_sha256=object_hash(records['drc']))
            if name=='postlayout':
                run.update(execution_scope='post_route_functional_plus_sta',verification_supported=True,
                           runtime_configuration={'execution_scope':'post_route_functional_plus_sta','working_directory':'SOFTWARE_QA_ONLY'})
                run['checks'].update(execution_scope=run['execution_scope'],origin='trusted_fixed_postlayout_adapter',executed=True,
                    summary={'functional_status':'Passed','sta_status':'Passed','software_qa_fixture':True},
                    checks={key:{'validation_status':'Passed'} for key in ('source_identity','configuration','functional','parasitics','constraints','setup_hold','electrical')})
                for short,stage in (('layout','physical'),('drc','drc'),('lvs','lvs')):
                    run[short+'_record_sha256']=object_hash(records[stage]);run[short+'_run_id']=records[stage]['id'];run[short+'_snapshot']=copy.deepcopy(records[stage])
            records[name]=seal(run)
        baseline=copy.deepcopy(records['physical']);baseline['id']='SOFTWARE_QA_PRIOR';seal(baseline)
        cancelled=copy.deepcopy(records['physical']);cancelled.update(id='SOFTWARE_QA_CANCELLED',execution_status='Cancelled',validation_status='Not Checked',review_status='Awaiting Review')
        folder=self.root/'.work/tools/cancelled';folder.mkdir(parents=True)
        write(folder/'stdout.log',b'SOFTWARE QA CANCELLED OUTPUT\n'*20000)
        write(folder/'partial.odb',b'SOFTWARE QA EXCLUDED INCOMPLETE BINARY')
        cancelled['checks']={'artifacts_directory':str(folder),'commands':[{'executed':False,'software_qa_fixture':True}]};seal(cancelled)
        for name,run in records.items():
            write(self.data/(name+'_workflow.json'),{'runs':([baseline,cancelled] if name=='physical' else [])+[run],
                'source_key':run['source_key'],'source_epoch':1,'reviews':[{'run_id':run['id'],'decision':'accepted','source_key':run['source_key'],'acceptance_epoch':1}]})
            write(self.before/(name+'_workflow.json'),{'runs':[baseline] if name=='physical' else []})
        for name in ('generation.json','global_generation.json'):
            write(self.data/name,{'jobs':[],'software_qa_fixture':True});write(self.before/name,{'jobs':[],'software_qa_fixture':True})
        write(self.data/'state.json',{'software_qa_fixture':True})
        self.records=records

    def collect_fixture(self):
        with ExitStack() as stack:
            stack.enter_context(patch.object(collector,'ROOT',self.root))
            for name in ('validate_physical_proof','validate_drc_proof','validate_lvs_proof','validate_postlayout_proof'):
                stack.enter_context(patch.object(collector,name,return_value=None))
            return collector.collect(self.data,self.output,self.before)

    def test_collect_and_portable_verify_include_cancelled_raw_logs_and_exact_source_history(self):
        manifest=self.collect_fixture()
        result=replay.verify(self.output)
        self.assertEqual(result['status'],'Passed')
        for stage in ('drc','lvs'):
            run=result['records'][stage]
            self.assertTrue({'verification_plan','verification_plan_sha256','vector_hash'}.isdisjoint(run))
            self.assertEqual(run['layout_snapshot'],result['records']['physical'])
        self.assertEqual(result['records']['lvs']['drc_snapshot'],result['records']['drc'])
        self.assertEqual(manifest['physical_implementation'],'resumed_post_GRT_route_repair')
        self.assertEqual(manifest['physical_profile_version'],'SOFTWARE_QA_PHYSICAL_PROFILE')
        self.assertEqual(len(manifest['new_attempts']),1)
        item=manifest['new_attempts'][0]
        self.assertEqual(item['execution_status'],'Cancelled')
        self.assertIn('attempts/physical/SOFTWARE_QA_CANCELLED/raw/stdout.log.gz',manifest['files'])
        self.assertFalse(any('partial.odb' in name for name in manifest['files']))
        with self.assertRaises(ValueError):self.collect_fixture()

    def test_hash_tamper_and_missing_bound_artifact_are_rejected(self):
        manifest=self.collect_fixture()
        target=self.output/'postlayout/functional-report'
        raw=target.read_bytes();target.write_bytes(b'TAMPERED SOFTWARE QA')
        with self.assertRaises(ValueError):replay.verify(self.output)
        target.write_bytes(raw)
        manifest['files'].pop('postlayout/functional-report')
        write(self.output/'manifest.json',manifest)
        with self.assertRaisesRegex(ValueError,'bound raw artifact'):replay.verify(self.output)

    def test_path_traversal_aliases_and_decompressed_size_limits_are_rejected(self):
        for module in (collector,replay):
            for path in ('../outside','C:/outside','/absolute','x\\y','x/../y','./name','x//name'):
                with self.subTest(module=module.__name__,path=path),self.assertRaises(ValueError):module.archive_path(self.root,path)
        manifest=self.collect_fixture()
        key=next(key for key in manifest['files'] if key.endswith('stdout.log.gz'))
        entry=copy.deepcopy(manifest['files'][key]);entry['raw_bytes']=replay.MAX_RAW_BYTES
        with self.assertRaises(ValueError):replay._read_entry(self.output,key,entry)

    def test_changed_generation_history_prevents_zero_new_calls_claim(self):
        write(self.data/'generation.json',{'jobs':[{'id':'SOFTWARE_QA_EXTRA_CALL'}]})
        with self.assertRaisesRegex(ValueError,'Model generation history changed'):self.collect_fixture()
        self.assertFalse(self.output.exists())

    def test_actual_replay_failure_is_retained_without_adoption_or_store_writes(self):
        self.collect_fixture()
        output=self.root/'.work/replay'
        with patch.object(replay,'ROOT',self.root),patch.object(replay,'run_postlayout',side_effect=ValueError('SOFTWARE QA unavailable tools')) as runner:
            with self.assertRaisesRegex(ValueError,'unavailable tools'):replay.replay(self.output,output)
            self.assertEqual(runner.call_count,1)
        summary=json.loads((output/'summary.json').read_text())
        self.assertEqual(summary['status'],'Failed');self.assertFalse(summary['adopted']);self.assertFalse(summary['live_store_modified'])
        source=json.loads((output/'replay-source.json').read_text())
        self.assertEqual(source['configuration']['working_directory'],str(output/'runs'))
        self.assertFalse((output/'result.json').exists())
        with patch.object(replay,'ROOT',self.root),patch.object(replay,'run_postlayout') as runner:
            with self.assertRaises(ValueError):replay.replay(self.output,output)
            runner.assert_not_called()


if __name__=='__main__':unittest.main()
