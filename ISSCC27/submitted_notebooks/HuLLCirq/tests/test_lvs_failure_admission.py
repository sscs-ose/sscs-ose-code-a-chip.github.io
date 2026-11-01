"""Pure admission/dispatch guards; not native extraction qualification."""
import copy
import unittest
from unittest.mock import patch

from hullcirq import lvs_tools as lvs
from hullcirq.domain import DomainError
from hullcirq.verification import object_hash
from test_lvs_terminal_recognition_adapter import TerminalRecognitionGateTests, profile
import test_lvs_terminal_recognition_adapter as source_guards


class DirectV7SourceTests(unittest.TestCase):
    def setUp(self):
        self.fixture=source_guards.TerminalSourceGuardTests();self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.configuration=self.fixture.fixture.config
        self.configuration['profile']['profile_version']='hullcirq-sky130-lvs-v7'
        self.configuration['repair_preparation_kind']='direct_v7'

    def test_direct_latest_recipe_preserves_original_binding_without_fake_failed_ancestors(self):
        before=copy.deepcopy(self.configuration)
        self.fixture.projection()
        self.assertEqual(before,self.configuration)
        self.assertNotIn('repair_upgrade_binding',self.configuration)

    def test_direct_mode_rejects_fabricated_upgrade_and_unknown_preparation_kinds(self):
        configuration=copy.deepcopy(self.configuration);configuration['repair_upgrade_binding']={}
        with self.assertRaises(DomainError):self.fixture.projection(configuration)
        for kind in ('direct_v6','unknown',True,None):
            configuration=copy.deepcopy(self.configuration);configuration['repair_preparation_kind']=kind
            with self.subTest(kind=kind),self.assertRaises(DomainError):self.fixture.projection(configuration)

    def test_direct_mode_still_requires_complete_exact_original_source_proof_binding(self):
        for key in ('layout_record_sha256','drc_record_sha256','source_inputs_sha256'):
            configuration=copy.deepcopy(self.configuration);configuration['repair_source_binding'][key]='invalid'
            with self.subTest(key=key),self.assertRaises(DomainError):self.fixture.projection(configuration)


class V4RecognitionGateTests(TerminalRecognitionGateTests):
    def summary(self):
        value=profile();value['profile_version']='hullcirq-sky130-lvs-v4'
        return lvs.summarize(self.fixture.folder,self.fixture.layout,value)

    def test_v3_artifacts_are_separate_and_legacy_mandatory_set_is_unchanged(self):
        super().test_v3_artifacts_are_separate_and_legacy_mandatory_set_is_unchanged()
        value=profile();value['profile_version']='hullcirq-sky130-lvs-v4'
        extra={'extraction-inventory-pre-gds','extraction-inventory-post-gds',
            'extraction-inventory-post-annotation'}
        self.assertEqual(set(lvs._file_types(value)),set(lvs._file_types(profile()))|extra)
        self.assertEqual(set(lvs._fixed_files(self.fixture.layout,value)),
            set(lvs._fixed_files(self.fixture.layout,profile()))|extra)


class V5RecognitionGateTests(V4RecognitionGateTests):
    def summary(self):
        value=profile();value['profile_version']='hullcirq-sky130-lvs-v5'
        return lvs.summarize(self.fixture.folder,self.fixture.layout,value)

    def test_v5_retains_the_same_strict_inventory_artifact_requirements(self):
        v4=profile();v4['profile_version']='hullcirq-sky130-lvs-v4'
        v5=copy.deepcopy(v4);v5['profile_version']='hullcirq-sky130-lvs-v5'
        self.assertEqual(lvs._file_types(v4),lvs._file_types(v5))
        self.assertEqual(lvs._fixed_files(self.fixture.layout,v4),lvs._fixed_files(self.fixture.layout,v5))

    def test_v6_retains_inventory_and_zero_feedback_gates_without_skipping_versions(self):
        v5=profile();v5['profile_version']='hullcirq-sky130-lvs-v5'
        v6=copy.deepcopy(v5);v6['profile_version']='hullcirq-sky130-lvs-v6'
        self.assertEqual(lvs._file_types(v5),lvs._file_types(v6))
        self.assertEqual(lvs._fixed_files(self.fixture.layout,v5),lvs._fixed_files(self.fixture.layout,v6))
        result=lvs.summarize(self.fixture.folder,self.fixture.layout,v6)
        self.assertEqual(result[2]['extraction']['validation_status'],'Passed')
        self.raw.write_text('SOFTWARE QA retained warning',encoding='utf-8')
        self.assertEqual(lvs.summarize(self.fixture.folder,self.fixture.layout,v6)[2]['extraction']['validation_status'],'Failed')
        self.assertEqual(lvs.UPGRADE_PREVIOUS,{'hullcirq-sky130-lvs-v4':'hullcirq-sky130-lvs-v3',
            'hullcirq-sky130-lvs-v5':'hullcirq-sky130-lvs-v4','hullcirq-sky130-lvs-v6':'hullcirq-sky130-lvs-v5',
            'hullcirq-sky130-lvs-v7':'hullcirq-sky130-lvs-v6'})


class FailedExecutionAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.layout={'id':'software-qa-layout'};self.drc={'id':'software-qa-drc'}
        self.inputs={k:{'sha256':'a'*64} for k in ('gds','def','netlist','powered_netlist')}
        self.configuration={'profile':profile(),'physical_runtime':{},
            'repair_source_binding':{'source_inputs_sha256':object_hash(self.inputs)}}
        self.result={'artifacts_directory':'.','source_inputs':copy.deepcopy(self.inputs),
            'origin':'trusted_fixed_lvs_adapter','scope':lvs.SCOPE,
            'layout_run_id':self.layout['id'],'layout_record_sha256':object_hash(self.layout),
            'drc_run_id':self.drc['id'],'drc_record_sha256':object_hash(self.drc),
            'configuration_sha256':object_hash(self.configuration),
            'input_gds_sha256':'a'*64,'input_netlist_sha256':'a'*64,
            'input_powered_netlist_sha256':'a'*64,'status':'Failed','validation_status':'Failed',
            'executed':True,'cleanup_unresolved':False,'exit_code':1,'commands':[{},{}]}
        first=patch.object(lvs,'configuration_projection',return_value={})
        first.start();self.addCleanup(first.stop)
        second=patch.object(lvs,'source_inputs',return_value=self.inputs)
        second.start();self.addCleanup(second.stop)

    def reject(self,result=None,configuration=None):
        with patch.object(lvs,'fixed_commands') as commands,patch.object(lvs,'load') as read:
            with self.assertRaises(DomainError):
                lvs.validate_failed_lvs_result(result or self.result,self.drc,self.layout,
                    configuration or self.configuration)
            commands.assert_not_called();read.assert_not_called()

    def test_failed_admission_cannot_certify_a_pass_or_unresolved_execution(self):
        for key,value in (('status','Completed'),('validation_status','Passed'),('executed',False),
                ('cleanup_unresolved',True),('exit_code',0),('exit_code',True),('commands',[{}])):
            result=copy.deepcopy(self.result);result[key]=value
            with self.subTest(key=key):self.reject(result)

    def test_foreign_source_chain_and_configuration_are_rejected_before_reads(self):
        for key,value in (('layout_run_id','foreign'),('layout_record_sha256','b'*64),
                ('drc_run_id','foreign'),('drc_record_sha256','b'*64),
                ('configuration_sha256','b'*64),('input_gds_sha256','b'*64),
                ('input_powered_netlist_sha256','b'*64),('origin','fixture')):
            result=copy.deepcopy(self.result);result[key]=value
            with self.subTest(key=key):self.reject(result)

    def test_only_frozen_failed_versions_can_authorize_their_fixed_next_preparation(self):
        for version in ('hullcirq-sky130-lvs-v2','hullcirq-sky130-lvs-v7','unknown'):
            configuration=copy.deepcopy(self.configuration)
            configuration['profile']['profile_version']=version
            with self.subTest(version=version):self.reject(configuration=configuration)

    def test_fixed_v3_recipe_pins_remain_historical(self):
        frozen=lvs.load(lvs.ROOT/'configs/lvs_profile_sky130_v3.json')
        self.assertEqual(frozen['extraction_variant']['script_sha256'],
            '34955dcd067a6e92a5d46623c6b90207b777425b7f6dfe619ed1d1d179f0c175')
        self.assertEqual(frozen['terminal_recognition_variant']['helper_sha256'],
            'e8b452fde6faadc21fa69afd8d5200656f08eb2df5798adecfae841782eb1b74')

    def test_v6_native_errors_are_rejected_even_if_feedback_would_be_empty(self):
        value={'profile_version':'hullcirq-sky130-lvs-v6'}
        lvs._validate_native_recognition_diagnostics(value,'Extraction complete','')
        for message in ('freeMagic called with NULL argument.',
                'Device parameters do not match any extraction model.','No cell selected'):
            for channel in (0,1):
                logs=['',''];logs[channel]=message
                with self.subTest(message=message,channel=channel),self.assertRaises(DomainError):
                    lvs._validate_native_recognition_diagnostics(value,*logs)
            lvs._validate_native_recognition_diagnostics({'profile_version':'hullcirq-sky130-lvs-v5'},message,'')


if __name__=='__main__':unittest.main()
