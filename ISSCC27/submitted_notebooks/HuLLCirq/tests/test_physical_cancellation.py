"""Mocked command-stop classification. Never native or live-project evidence."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import threading
import unittest
from contextlib import ExitStack
from unittest.mock import patch

ROOT = next(p for p in Path(__file__).resolve().parents if (p/'src/hullcirq').is_dir())
from hullcirq import physical_tools as physical, drc_tools as drc, lvs_tools as lvs, postroute_tools as postroute
from hullcirq import postlayout_tools, postlayout_diagnostic_tools, postlayout_event_diagnostic_tools
from hullcirq.domain import DomainError
from hullcirq.verification import object_hash


class PhysicalCancellationTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack(); self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(subprocess, 'Popen', side_effect=AssertionError('No native process permitted.')))
        self.stack.enter_context(patch.object(subprocess, 'run', side_effect=AssertionError('No native process permitted.')))
        qa_root=ROOT/'.work/qa';qa_root.mkdir(parents=True,exist_ok=True)
        self.stack.enter_context(patch.object(tempfile,'tempdir',str(qa_root)))
        self.temp = tempfile.TemporaryDirectory(dir=qa_root); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.image = self.root/'image'; self.image.write_bytes(b'SOFTWARE QA image, never executed')
        self.sdc = self.root/'source.sdc'; self.sdc.write_bytes(b'SOFTWARE QA unchanged timing')
        self.pdk = self.root/'pdks/pdk'; self.pdk.mkdir(parents=True)
        self.manifest = self.root/'pdk.json'
        self.manifest.write_text(json.dumps({'root':str(self.pdk),'ciel_revision':physical.PDK_REVISION,'files':{}}), encoding='utf-8')
        self.runtime = {'kind':'wsl','distribution':'Ubuntu','appimage_path':str(self.image),
            'executable':'/SOFTWARE_QA_DO_NOT_EXECUTE','base_sdc_path':str(self.sdc),
            'pdk_manifest_path':str(self.manifest),'pdk_manifest_sha256':physical.sha(self.manifest),
            'pdk_root':str(self.root/'pdks'),'working_directory':str(self.root/'runs'),
            'profile':{'deck_files':{}}}
        self.sources = self.root/'source'; self.sources.mkdir()
        self.inputs = {}
        for identifier in ('gds','def','netlist','powered_netlist','final-state'):
            p=self.sources/identifier; p.write_bytes(('SOFTWARE QA '+identifier+'\n').encode())
            self.inputs[identifier]={'id':identifier,'relative_path':identifier,'bytes':p.stat().st_size,'sha256':physical.sha(p)}
        self.settings={'top_module':'qa_top','clock_name':'clk','clock_period_ns':50}
        self.layout={'id':'qa-layout','settings':self.settings,'checks':{'artifacts_directory':str(self.sources),'artifacts':list(self.inputs.values())}}
        self.drc={'id':'qa-drc','layout_record_sha256':object_hash(self.layout)}
        self.lvs={'id':'qa-lvs','drc_record_sha256':object_hash(self.drc),
                  'source_inputs':self.inputs,'layout_record_sha256':object_hash(self.layout)}
        self.event = threading.Event(); self.event.set()

    @staticmethod
    def record(command, status='Completed', code=0, executed=True, unresolved=False):
        return {'command':copy.deepcopy(command),'status':status,'exit_code':code,'executed':executed,
                'cleanup_unresolved':unresolved,'stdout':'RAW cancelled word is not a status\n','stderr':'RAW stderr\n'}

    def run_native_adapter(self, stage, stop_index, status='Cancelled', code=-15, executed=True, unresolved=False, source_error=False):
        module={'physical':physical,'drc':drc,'lvs':lvs}[stage]
        commands=[['wsl.exe','--exec','SOFTWARE_QA_VERSION'],['wsl.exe','--exec','SOFTWARE_QA_WORKER']]
        records=[]
        def execute(command, configuration, folder, operation, cancel, timeout):
            index=len(records)
            if source_error and index==stop_index:
                raise DomainError('qa_source_changed','SOFTWARE QA source changed; not cancellation.')
            record=self.record(command, status if index==stop_index else 'Completed',
                code if index==stop_index else 0, executed if index==stop_index else True,
                unresolved if index==stop_index else False)
            logs=folder/operation;logs.mkdir()
            (logs/'stdout.log').write_text(record['stdout'],encoding='utf-8')
            (logs/'stderr.log').write_text(record['stderr'],encoding='utf-8')
            records.append(copy.deepcopy(record)); return record
        original_sha=physical.sha
        def sha(path):
            if Path(path)==self.image:return physical.IMAGE_SHA
            if Path(path)==self.sdc:return physical.SDC_SHA
            return original_sha(path)
        with ExitStack() as mocks:
            mocks.enter_context(patch.object(physical,'sha',side_effect=sha))
            if module is not physical:mocks.enter_context(patch.object(module,'sha',side_effect=sha))
            mocks.enter_context(patch.object(module,'configuration_projection',return_value={}))
            mocks.enter_context(patch.object(module,'fixed_commands',return_value=commands))
            mocks.enter_context(patch.object(physical,'_execute',side_effect=execute))
            if stage=='physical':
                mocks.enter_context(patch.object(physical,'source_bundle',return_value=[]))
                mocks.enter_context(patch.object(physical,'is_repair',return_value=False))
                mocks.enter_context(patch.object(physical,'is_block_configuration',return_value=False))
                mocks.enter_context(patch.object(physical,'_has_pnr_headroom',return_value=False))
                mocks.enter_context(patch.object(physical,'_closure_recipe',return_value=None))
                mocks.enter_context(patch.object(physical.generic_repair,'is_generic',return_value=False))
                result=physical.run_layout('module qa_top; endmodule\n',{'nodes':[]},self.settings,self.runtime,self.event)
            else:
                configuration={'physical_runtime':self.runtime,'working_directory':str(self.root/'runs'), 'profile':{'deck_files':{}}}
                if stage=='drc':result=drc.run_drc(self.layout,configuration,self.event)
                else:
                    mocks.enter_context(patch.object(lvs,'source_inputs',return_value=self.inputs))
                    mocks.enter_context(patch.object(lvs,'_variant_files',return_value={}))
                    result=lvs.run_lvs(self.drc,self.layout,configuration,self.event)
        self.assertEqual(result['commands'],records,'Every command and raw field must remain unchanged.')
        for record in records:
            self.assertIn(record['stdout'],result['stdout']);self.assertIn(record['stderr'],result['stderr'])
        return result

    def test_version_or_worker_cancel_is_not_failed_check_and_does_not_replay(self):
        for stage in ('physical','drc','lvs'):
            for stop_index,executed in ((0,False),(0,True),(1,False),(1,True)):
                with self.subTest(stage=stage,stop_index=stop_index,executed=executed):
                    result=self.run_native_adapter(stage,stop_index,executed=executed,code=-15 if executed else None)
                    self.assertEqual(result['status'],'Cancelled');self.assertEqual(result['validation_status'],'Not Checked')
                    self.assertEqual(len(result['commands']),stop_index+1)
                    self.assertFalse(result['cleanup_unresolved'])
                    self.assertEqual(result['diagnostics'][-1]['code'],stage+'_cancelled')
                    self.assertEqual(result['diagnostics'][-1]['severity'],'info')
                    self.assertFalse(any(d['severity']=='error' for d in result['diagnostics']))
                    self.assertNotEqual(result.get('validation_status'),'Passed')

    def test_real_failure_timeout_and_sigterm_exit_are_not_downgraded_even_with_cancel_event(self):
        for stage in ('physical','drc','lvs'):
            for status,code in (('Completed',7),('Completed',-15),('Failed',-15),('Timeout',-15),('TimedOut',124)):
                with self.subTest(stage=stage,status=status,code=code):
                    result=self.run_native_adapter(stage,1,status,code)
                    self.assertEqual(result['validation_status'],'Failed')
                    self.assertEqual(result['diagnostics'][-1]['code'],stage+'_tool_failed')
                    self.assertEqual(result['diagnostics'][-1]['severity'],'error')

    def test_trusted_cancelled_status_with_zero_exit_does_not_need_cancel_event_or_pass(self):
        self.event.clear()
        for stage in ('physical','drc','lvs'):
            with self.subTest(stage=stage):
                result=self.run_native_adapter(stage,1,code=0)
                self.assertEqual(result['status'],'Cancelled')
                self.assertEqual(result['validation_status'],'Not Checked')
                self.assertEqual(result['commands'][-1]['exit_code'],0)
                self.assertEqual(result['diagnostics'][-1]['severity'],'info')
        for phase in ('compile','simulate','sta'):
            with self.subTest(stage='postroute',phase=phase):
                result=self.run_s14(phase,code=0)
                self.assertEqual(result['status'],'Cancelled')
                self.assertEqual(result['validation_status'],'Not Checked')
                self.assertEqual(result['commands'][-1]['exit_code'],0)
                self.assertEqual(result['diagnostics'][-1]['severity'],'info')

    def test_cancel_with_unresolved_cleanup_stays_actionable_and_flagged(self):
        for stage in ('physical','drc','lvs'):
            with self.subTest(stage=stage):
                result=self.run_native_adapter(stage,1,unresolved=True)
                self.assertTrue(result['cleanup_unresolved']);self.assertEqual(result['validation_status'],'Not Checked')
                self.assertEqual(result['diagnostics'][-1]['code'],stage+'_cancel_cleanup_unresolved')
                self.assertEqual(result['diagnostics'][-1]['severity'],'error')

    def test_s11_aggregate_executed_retains_earlier_execution_at_worker_cancel_boundary(self):
        boundary=self.run_native_adapter('physical',1,code=None,executed=False)
        self.assertEqual([c['executed'] for c in boundary['commands']],[True,False])
        self.assertTrue(boundary['executed'])
        self.assertFalse(boundary['technology_mapping_executed'])
        not_started=self.run_native_adapter('physical',0,code=None,executed=False)
        self.assertEqual([c['executed'] for c in not_started['commands']],[False])
        self.assertFalse(not_started['executed'])
        self.assertFalse(not_started['technology_mapping_executed'])
        # A successful command sequence is a positive execution-metadata control.
        # Native completion/proof validation is separately covered by existing tests.
        with patch.object(physical,'_finish_layout_result') as finish:
            completed_commands=self.run_native_adapter('physical',2)
        finish.assert_called_once()
        self.assertEqual([c['executed'] for c in completed_commands['commands']],[True,True])
        self.assertEqual([c['status'] for c in completed_commands['commands']],['Completed','Completed'])
        self.assertTrue(completed_commands['executed'])
        self.assertFalse(completed_commands['technology_mapping_executed'])

    def test_source_error_after_cancel_event_is_still_error(self):
        for stage in ('physical','drc','lvs'):
            with self.subTest(stage=stage):
                result=self.run_native_adapter(stage,1,source_error=True)
                self.assertEqual(result['validation_status'],'Failed')
                self.assertEqual(result['diagnostics'][-1]['code'],'qa_source_changed')
                self.assertEqual(result['diagnostics'][-1]['severity'],'error')

    def run_s14(self, phase, status='Cancelled', code=-15, unresolved=False, wrong_command=False, unrelated=False):
        working=self.root/('postroute-'+str(len(list(self.root.glob('postroute-*')))))
        working.mkdir()
        def functional(layout, configuration, folder, cancel, commands, source_binding):
            for operation in ('compile','simulate'):
                command=['wsl.exe','--exec','SOFTWARE_QA_'+operation]
                stopped=phase==operation
                record=self.record(command,status if stopped else 'Completed',code if stopped else 0,True,unresolved if stopped else False)
                if stopped and wrong_command:record['command']=['WRONG_SOURCE_COMMAND']
                commands.append(record)
                if stopped:
                    if unrelated:raise DomainError('qa_source_changed','SOFTWARE QA source mismatch after stop.')
                    postroute._validate_execution(folder,operation,record,command)
            return {'software_qa_fixture':True}
        command=['wsl.exe','--exec','SOFTWARE_QA_STA']
        record=self.record(command,status,code,True,unresolved)
        prepared={'commands':[{'command':command,'operation':'sta-fixture','corner':'fixture','timeout':300}]}
        with patch.object(postroute,'_configuration',return_value=(self.runtime,None,None,working)), \
             patch.object(postroute,'source_inputs',return_value=self.inputs), \
             patch.object(postroute,'_bindings',return_value={}), \
             patch.object(postroute,'run_functional',side_effect=functional), \
             patch.object(postroute,'_annotation_policy',return_value=None), \
             patch.object(postroute.postroute_sta,'prepare_sta',return_value=prepared), \
             patch.object(physical,'_execute',return_value=record):
            result=postroute.run_postlayout(self.lvs,self.drc,self.layout,{},self.event)
        return result

    def test_s14_compile_simulate_or_sta_cancel_is_not_tool_failure(self):
        for phase in ('compile','simulate','sta'):
            with self.subTest(phase=phase):
                result=self.run_s14(phase)
                self.assertEqual(result['status'],'Cancelled');self.assertEqual(result['validation_status'],'Not Checked')
                self.assertEqual(result['diagnostics'][-1]['code'],'postroute_cancelled')
                self.assertEqual(result['diagnostics'][-1]['severity'],'info')
                self.assertEqual(len(result['commands']),{'compile':1,'simulate':2,'sta':3}[phase])
                self.assertEqual(result['commands'][-1]['exit_code'],-15)

    def test_s14_cancel_unresolved_cleanup_remains_error(self):
        result=self.run_s14('sta',unresolved=True)
        self.assertTrue(result['cleanup_unresolved']);self.assertEqual(result['validation_status'],'Not Checked')
        self.assertEqual(result['diagnostics'][-1]['code'],'postroute_cancel_cleanup_unresolved')
        self.assertEqual(result['diagnostics'][-1]['severity'],'error')

    def test_s14_true_errors_timeouts_and_bad_source_are_not_softened(self):
        for options in ({'status':'Timeout','code':124},{'status':'Completed','code':7},
                        {'status':'Failed','code':-15},{'wrong_command':True},{'unrelated':True}):
            with self.subTest(options=options):
                result=self.run_s14('compile',**options)
                self.assertEqual(result['diagnostics'][-1]['severity'],'error')
                self.assertNotEqual(result['diagnostics'][-1]['code'],'postroute_cancelled')

    def test_existing_legacy_saved_reviews_preserve_original_execution_and_add_cancel_info(self):
        from test_postlayout_diagnostic_tools import SavedDiagnosticTests
        from test_postlayout_event_diagnostic_tools import SavedEventDiagnosticTests
        for cls,module in ((SavedDiagnosticTests,postlayout_diagnostic_tools),(SavedEventDiagnosticTests,postlayout_event_diagnostic_tools)):
            with self.subTest(adapter=module.__name__):
                fixture=cls();fixture.setUp()
                try:
                    original=copy.deepcopy(fixture.evidence['frozen_result'])
                    with patch.object(postlayout_tools,'source_inputs',return_value=fixture.inputs):
                        result=module.run_postlayout(fixture.lvs,fixture.drc,fixture.layout,fixture.configuration,self.event)
                    self.assertEqual(result['status'],'Cancelled');self.assertEqual(result['validation_status'],'Not Checked')
                    self.assertFalse(result['execution_started_by_this_review'])
                    self.assertEqual(result['commands'],original['commands'])
                    self.assertEqual(result['diagnostics'][:-1],original['diagnostics'])
                    self.assertEqual(result['diagnostics'][-1]['severity'],'info')
                    self.assertEqual(fixture.evidence['frozen_result'],original)
                finally:fixture.tearDown()

    def test_legacy_readiness_cancel_adds_info_without_claiming_dynamic_support(self):
        for key in ('sdf',):
            p=self.sources/key;p.write_bytes(b'SOFTWARE QA unexecuted SDF')
            self.inputs[key]={'relative_path':key,'bytes':p.stat().st_size,'sha256':physical.sha(p)}
        for key,relative in postlayout_tools.MODEL_FILES.items():
            p=self.pdk/relative;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'// SOFTWARE QA model, never simulated\n')
            self.inputs[key]={'bytes':p.stat().st_size,'sha256':physical.sha(p)}
        plan={'output_count':4,'public_boundary_vectors':[], 'vector_hash':'qa-vector',
              'testbench_sha256':'qa-testbench','public_boundary_vector_hash':'qa-boundary'}
        self.layout.update(verification_plan=plan,verification_plan_sha256=object_hash(plan))
        drc_record={'id':'qa-drc','layout_record_sha256':object_hash(self.layout)}
        lvs_record={'id':'qa-lvs','layout_record_sha256':object_hash(self.layout),
                    'drc_record_sha256':object_hash(drc_record),'source_inputs':self.inputs}
        profile={'reason':'SOFTWARE QA dynamic support is unavailable','readiness_report_sha256':'qa'}
        report={'simulator':'SOFTWARE QA no simulator','annotation_coverage':{},'SDF_syntactic_construct_counts':{},'HOLD_values_ns':[]}
        with patch.object(postlayout_tools,'_configuration',return_value=(profile,report,None,self.pdk,self.root/'readiness')), \
             patch.object(postlayout_tools,'source_inputs',return_value=self.inputs), \
             patch.object(postlayout_tools,'timed_testbench',return_value=('module never_run; endmodule',{})):
            cancelled=postlayout_tools.run_postlayout(lvs_record,drc_record,self.layout,{},self.event)
            ordinary=postlayout_tools.run_postlayout(lvs_record,drc_record,self.layout,{})
        self.assertEqual(cancelled['status'],'Cancelled');self.assertEqual(cancelled['validation_status'],'Not Checked')
        self.assertEqual(cancelled['diagnostics'][-1]['code'],'postlayout_preflight_cancelled')
        self.assertEqual(cancelled['diagnostics'][-1]['severity'],'info')
        self.assertEqual(cancelled['commands'],[]);self.assertFalse(cancelled['executed']);self.assertFalse(cancelled['verification_supported'])
        self.assertEqual(ordinary['validation_status'],'Unsupported');self.assertEqual(ordinary['status'],'Completed')
        self.assertFalse(any(d['code']=='postlayout_preflight_cancelled' for d in ordinary['diagnostics']))


if __name__=='__main__':unittest.main()
