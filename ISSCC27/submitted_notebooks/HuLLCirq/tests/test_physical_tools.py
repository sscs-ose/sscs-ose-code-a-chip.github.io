"""Pure metric/recipe QA; no physical tools, models or live projects."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from hullcirq.domain import DomainError
from hullcirq.physical_tools import metric_checks,configuration_projection,IMAGE_SHA,PDK_REVISION,SDC_SHA,load_tool_json,run_layout,sha,validate_worker_binding,revalidate_layout,_finish_layout_result
from hullcirq.verification import _wsl_path

class PhysicalToolTests(unittest.TestCase):
    def setUp(self):
        self.metrics={name:0 for name in ('route__drc_errors','design__disconnected_pin__count','design__instance_unmapped__count','synthesis__check_error__count','timing__setup__wns','timing__hold__wns','timing__setup_vio__count','timing__hold_vio__count')}
        self.metrics.update({name:10 for name in ('design__core__area','design__die__area','design__instance__area','design__instance__count','route__wirelength')})
        self.settings={'top_module':'hullcirq_npu','clock_name':'clk','clock_period_ns':50,'reset_name':'rst','reset_kind':'synchronous','reset_active':'high','pdk':'sky130A','cell_library':'sky130_fd_sc_hd'}
        self.config={'kind':'wsl','distribution':'Ubuntu','release':'3.0.16','appimage_sha256':IMAGE_SHA,'pdk_revision':PDK_REVISION,'base_sdc_sha256':SDC_SHA,'origin':'software_qa_fixture',
                     'profile':json.loads((ROOT/'configs/physical_profile_sky130.json').read_text(encoding='utf-8')),
                     'appimage_path':str(ROOT/'.work/software-fixture/librelane-devshell-x86_64.AppImage'),
                     'executable':_wsl_path(ROOT/'.work/software-fixture/librelane-devshell-x86_64.AppImage'),'working_directory':str(ROOT/'.work/isolated-software-QA')}

    def test_complete_metrics_explicitly_separate_routing_and_STA(self):
        result=metric_checks(self.metrics)
        self.assertEqual(result['routing']['validation_status'],'Passed')
        self.assertTrue(result['routing']['routing_DRC_is_not_signoff_DRC'])
        self.assertEqual(result['timing']['scope'],'extracted_STA_not_dynamic_SDF_simulation')

    def test_missing_metrics_never_become_zero_violations(self):
        for name in self.metrics:
            with self.subTest(name=name):
                changed=dict(self.metrics);del changed[name]
                with self.assertRaises(DomainError):metric_checks(changed)

    def test_boolean_nan_infinity_strings_are_not_numeric_evidence(self):
        for value in (False,True,float('nan'),float('inf'),'0',None):
            changed=dict(self.metrics);changed['route__drc_errors']=value
            with self.subTest(value=value),self.assertRaises(DomainError):metric_checks(changed)

    def test_routing_unmapped_and_connectivity_errors_reject_adoption(self):
        for name in ('route__drc_errors','design__disconnected_pin__count','design__instance_unmapped__count','synthesis__check_error__count'):
            changed=dict(self.metrics);changed[name]=1
            self.assertEqual(metric_checks(changed)['routing']['validation_status'],'Failed')

    def test_negative_slack_or_nonzero_violation_count_rejects_timing(self):
        for name,value in (('timing__setup__wns',-.001),('timing__hold__wns',-.001),('timing__setup_vio__count',1),('timing__hold_vio__count',1)):
            changed=dict(self.metrics);changed[name]=value
            self.assertEqual(metric_checks(changed)['timing']['validation_status'],'Failed')

    def test_empty_placement_and_routing_is_not_a_layout_pass(self):
        for name in ('design__instance__count','route__wirelength','design__core__area'):
            changed=dict(self.metrics);changed[name]=0
            self.assertEqual(metric_checks(changed)['routing']['validation_status'],'Failed')

    def test_original_clock_and_full_seven_sources_are_preserved(self):
        original=copy.deepcopy(self.settings);profile=copy.deepcopy(self.config)
        result=configuration_projection(self.settings,self.config)
        self.assertEqual(result['CLOCK_PERIOD'],50)
        self.assertEqual(result['FP_CORE_UTIL'],35)
        self.assertEqual(len(result['VERILOG_FILES']),7)
        self.assertNotIn('FP_CORE_UTIL',self.settings)
        self.assertEqual(self.settings,original);self.assertEqual(self.config,profile)
        self.assertEqual(result['PNR_SDC_FILE'],result['SIGNOFF_SDC_FILE'])

    def test_explicit_2x2_manifest_projects_all_eleven_sources_deterministically(self):
        node_ids=('npu2-control','npu2-buffer','npu2-scheduler','npu2-dispatcher','npu2-pe00','npu2-pe01',
                  'npu2-pe10','npu2-pe11','npu2-collector','npu2-post','npu2-fifo')
        manifest={'nodes':[{'node_id':node_id} for node_id in node_ids]}
        settings={**self.settings,'top_module':'hullcirq_npu2_top'}
        result=configuration_projection(settings,self.config,manifest)
        self.assertEqual(result['DESIGN_NAME'],'hullcirq_npu2_top')
        self.assertEqual(result['VERILOG_FILES'],['dir::candidate_top.v',*(f'dir::{node_id}.v' for node_id in node_ids)])
        # The no-manifest compatibility path remains byte/ordering compatible
        # with the historical six-node physical configuration.
        self.assertEqual(configuration_projection(self.settings,self.config)['VERILOG_FILES'],[
            'dir::candidate_top.v','dir::node-control.v','dir::node-buffer.v','dir::node-scheduler.v',
            'dir::node-pe.v','dir::node-post.v','dir::node-fifo.v'])

    def test_physical_source_and_top_identifiers_reject_duplicates_and_paths(self):
        for top in ('../top','nested/top','nested\\top','1top','module',''):
            with self.subTest(top=top),self.assertRaises(DomainError):
                configuration_projection({**self.settings,'top_module':top},self.config,{'nodes':[{'node_id':'safe-node'}]})
        invalid_manifests=({'nodes':[{'node_id':'../escape'}]}, {'nodes':[{'node_id':'nested/path'}]},
                           {'nodes':[{'node_id':'nested\\path'}]}, {'nodes':[{'node_id':'node.ok'}]}, {'nodes':[{'node_id':'1node'}]},
                           {'nodes':[{'node_id':'same'},{'node_id':'same'}]},
                           {'nodes':[{'node_id':'same'},{'node_id':'SAME'}]},
                           {'nodes':[{'node_id':'candidate_top'}]}, {'nodes':[{'node_id':'top'}]}, {'nodes':[]})
        for manifest in invalid_manifests:
            with self.subTest(manifest=manifest),self.assertRaises(DomainError):
                configuration_projection({**self.settings,'top_module':'hullcirq_npu2_top'},self.config,manifest)

    def test_unpinned_runtime_or_unreviewed_profile_is_rejected(self):
        for field in ('release','appimage_sha256','pdk_revision','base_sdc_sha256'):
            changed=copy.deepcopy(self.config);changed[field]='different'
            with self.assertRaises(DomainError):configuration_projection(self.settings,changed)
        changed=copy.deepcopy(self.config);changed['profile']['config']['FP_CORE_UTIL']=99
        with self.assertRaises(DomainError):configuration_projection(self.settings,changed)

    def test_generic_saved_contract_uses_arbitrary_clock_reset_and_source_names(self):
        manifest={'design':{'global_verification':{'kind':'generic_cycle_vectors','version':1}},
                  'nodes':[{'node_id':'byte-transform'},{'node_id':'output-register'}]}
        settings={**self.settings,'top_module':'byte_pipeline','clock_name':'clock_i',
                  'reset_name':'reset_ni','reset_active':'low'}
        result=configuration_projection(settings,self.config,manifest)
        self.assertEqual(result['DESIGN_NAME'],'byte_pipeline')
        self.assertEqual(result['CLOCK_PORT'],'clock_i')
        self.assertEqual(result['VERILOG_FILES'],['dir::candidate_top.v','dir::byte-transform.v','dir::output-register.v'])
        self.assertEqual(result['CLOCK_PERIOD'],50)
        self.assertEqual(result['PNR_SDC_FILE'],result['SIGNOFF_SDC_FILE'])
        with self.assertRaises(DomainError):configuration_projection(settings,self.config)
        for key,value in (('clock_name','../clock'),('reset_name','module'),('reset_name','clock_i'),
                          ('reset_active','other'),('reset_kind','asynchronous')):
            with self.subTest(key=key,value=value),self.assertRaises(DomainError):
                configuration_projection({**settings,key:value},self.config,manifest)

    def test_unsupported_reset_or_typed_clock_is_rejected(self):
        for field,value in (('reset_kind','asynchronous'),('clock_period_ns',True),('clock_period_ns',0),('clock_period_ns',float('nan')),('pdk','other')):
            changed=dict(self.settings);changed[field]=value
            with self.assertRaises(DomainError):configuration_projection(changed,self.config)

    def test_profile_numeric_types_and_verified_executable_are_bound(self):
        for field,value in (('STA_THREADS',True),('FP_CORE_UTIL',35.0)):
            changed=copy.deepcopy(self.config);changed['profile']['config'][field]=value
            with self.subTest(field=field),self.assertRaises(DomainError):configuration_projection(self.settings,changed)
        changed=copy.deepcopy(self.config);changed['executable']='/different/librelane-devshell-x86_64.AppImage'
        with self.assertRaises(DomainError):configuration_projection(self.settings,changed)

    def test_tool_nonfinite_tokens_are_tagged_without_changing_raw_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/'metrics.json'
            raw=b'{"unused_path_slack": Infinity, "negative": -Infinity, "nan": NaN}'
            path.write_bytes(raw)
            parsed=load_tool_json(path)
            self.assertEqual(parsed['unused_path_slack'],{'librelane_nonfinite':'Infinity'})
            self.assertEqual(parsed['negative'],{'librelane_nonfinite':'-Infinity'})
            self.assertEqual(path.read_bytes(),raw)
            invalid=dict(self.metrics);invalid['timing__setup__wns']=parsed['unused_path_slack']
            with self.assertRaises(DomainError):metric_checks(invalid)
            path.write_text('{"same":0,"same":1}',encoding='utf-8')
            with self.assertRaises(DomainError):load_tool_json(path)

    def test_failed_tool_retains_inputs_raw_logs_and_original_exit(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);pdk=root/'pdks';pdk.mkdir()
            image=root/'librelane-devshell-x86_64.AppImage';image.write_bytes(b'software QA placeholder, never executed')
            sdc=root/'official.sdc';sdc.write_bytes(b'software QA SDC')
            pdk_manifest=root/'pdk.json';pdk_manifest.write_text(json.dumps({'root':str(pdk),'ciel_revision':PDK_REVISION,'files':{}}),encoding='utf-8')
            configuration=copy.deepcopy(self.config)
            configuration.update(appimage_path=str(image),executable=_wsl_path(image),base_sdc_path=str(sdc),
                                 pdk_root=str(pdk),pdk_manifest_path=str(pdk_manifest),pdk_manifest_sha256=sha(pdk_manifest),working_directory=str(root/'runs'))
            manifest={'nodes':[{'node_id':'node-pe','rtl':'module pe; endmodule\n','rtl_sha256':'not-used-in-this-isolated-failure-test'}]}
            # Source bundle expects the real source identity schema. Its finite
            # fixture is independent of the NPU and never reaches live history.
            with patch('hullcirq.physical_tools.source_bundle',return_value={'software_qa_fixture':True}):
                def hash_fixture(path):
                    return IMAGE_SHA if Path(path)==image else SDC_SHA if Path(path)==sdc else sha(path)
                def failed(command,config,folder,operation,cancel,timeout):
                    logs=folder/operation;logs.mkdir();(logs/'stdout.log').write_bytes(b'original failed tool stdout\n')
                    (logs/'stderr.log').write_bytes(b'original failed tool stderr\n')
                    return {'command':command,'executed':True,'exit_code':7,'status':'Completed','stdout':'original failed tool stdout\n','stderr':'original failed tool stderr\n'}
                with patch('hullcirq.physical_tools.sha',side_effect=hash_fixture),patch('hullcirq.physical_tools._execute',side_effect=failed):
                    result=run_layout('module hullcirq_npu; endmodule\n',manifest,self.settings,configuration)
            self.assertEqual(result['validation_status'],'Failed');self.assertEqual(result['exit_code'],7)
            self.assertFalse(result['technology_mapping_executed'])
            self.assertIn('config',{entry['id'] for entry in result['artifacts']})
            self.assertIn('rtl-top',{entry['id'] for entry in result['artifacts']})
            self.assertIn('version/stdout.log',{entry['relative_path'] for entry in result['retained_files']})
            self.assertEqual((Path(result['artifacts_directory'])/'version/stdout.log').read_bytes(),b'original failed tool stdout\n')

    def test_worker_birth_record_cannot_be_rehashed_to_another_process(self):
        folder=ROOT/'.work/isolated-software-QA/run'
        request={'argv':['fixed','tool']}
        record={'version':'hullcirq-physical-worker-v2','argv':request['argv'],'cwd':_wsl_path(folder),
                'request_sha256':'a'*64,'worker_sha256':'b'*64,'process_group':101,'leader_starttime':202,
                'observed_child_cwd':_wsl_path(folder),'whole_process_group_terminated':True,'cleanup_unresolved':False}
        start={k:v for k,v in record.items() if k not in ('whole_process_group_terminated','cleanup_unresolved')};start['boot_id']='isolated-software-fixture-boot'
        validate_worker_binding(request,record,start,folder,'b'*64)
        for key,value in (('argv',['other']),('cwd','/other'),('request_sha256','c'*64),('worker_sha256','d'*64),('process_group',102),('leader_starttime',True)):
            modified=copy.deepcopy(start);modified[key]=value
            with self.subTest(key=key),self.assertRaises(DomainError):validate_worker_binding(request,record,modified,folder,'b'*64)

    def test_saved_output_recheck_rejects_nonexecuted_and_unresolved_reports(self):
        original={'origin':'trusted_fixed_tool_adapter','executed':True,'exit_code':0,
                  'commands':[{'executed':True,'exit_code':0,'status':'Completed'}]*2}
        for key,value in (('executed',False),('exit_code',True),('cleanup_unresolved',True)):
            changed=copy.deepcopy(original);changed[key]=value
            with self.subTest(key=key),patch('hullcirq.physical_tools.subprocess.Popen') as launch,self.assertRaises(DomainError):
                revalidate_layout('rtl',{'nodes':[]},self.settings,self.config,changed,'prior')
            launch.assert_not_called()

    def test_metric_failure_keeps_real_terminal_output_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder=Path(temporary);terminal=folder/'runs/physical/60-klayout-render';terminal.mkdir(parents=True)
            final=folder/'runs/physical/final';final.mkdir()
            state={}
            for name,key in (('layout.def','def'),('layout.gds','gds'),('layout.png','render'),('mapped.v','nl')):
                path=folder/name;path.write_bytes(b'isolated failed-output placeholder');state[key]=_wsl_path(path)
            (terminal/'state_out.json').write_text(json.dumps(state),encoding='utf-8')
            (final/'metrics.json').write_text('{}',encoding='utf-8')
            result={'artifacts_directory':str(folder),'artifacts':[],'retained_files':[],'metrics':{},'checks':{},'diagnostics':[],'validation_status':'Failed'}
            with self.assertRaises(DomainError):_finish_layout_result(result,'rtl',{'nodes':[]},self.settings,self.config)
            self.assertTrue({'def','gds','png','netlist','metrics','final-state'}<={entry['id'] for entry in result['artifacts']})
            self.assertEqual(result['validation_status'],'Failed')

if __name__=='__main__':unittest.main()
