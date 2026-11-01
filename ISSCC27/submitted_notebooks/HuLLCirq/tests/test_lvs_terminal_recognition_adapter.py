"""Pure adapter guards, not physical MOSCAP/extractor qualification evidence."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import test_lvs_tools as fixtures
from hullcirq import lvs_tools as lvs
from hullcirq import lvs_workflow
from hullcirq.domain import DomainError
from hullcirq.verification import object_hash


def profile():
    return {'profile_version':lvs.RECOGNITION_PROFILE,'limits':['SOFTWARE QA ONLY'],
        'flow':['Magic.SpiceExtraction','Netgen.LVS'],'config':{},
        'force_full_extraction':True,'extraction_variant':{},
        'terminal_recognition_variant':{'comparison_spice':'extraction-comparison.spice',
            'raw_spice':'extraction-raw.spice','proof':'extraction-model-proof.json',
            'wrapper_path':'scripts/lvs_moscap_models_v3.spice',
            'derived_tech':'derived-sky130A-moscap-v3.tech'}}


class TerminalRecognitionGateTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.LvsReportTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.write()
        self.raw=self.fixture.folder/lvs.FIXED_FILES['extraction-feedback']
        self.raw.write_text('',encoding='utf-8')
        self.proof=Mock(return_value={'validation_status':'Passed','origin':'software_qa_only'})
        self.patch=patch.object(lvs,'_validate_recognition_model_proof',self.proof)
        self.patch.start();self.addCleanup(self.patch.stop)

    def summary(self):
        return lvs.summarize(self.fixture.folder,self.fixture.layout,profile())

    def marker(self):
        return ('<report-database><categories><category><name>SOFTWARE_QA_ONLY</name>'
            '<description>device missing 1 terminal; connecting remainder to node VGND</description>'
            '</category></categories><items><item><category>SOFTWARE_QA_ONLY</category>'
            '<cell>software_qa_top</cell><values><value>fixture, not GDS</value></values>'
            '</item></items></report-database>')

    def test_zero_both_feedback_formats_and_positive_model_proof_are_required(self):
        summary,_,checks=self.summary()
        self.assertEqual(checks['extraction']['validation_status'],'Passed')
        self.assertEqual(summary['extraction']['missing_device_terminal_count'],0)
        self.assertIs(summary['extraction']['zero_feedback_required'],True)
        self.proof.assert_called_once()

    def test_same_warning_still_fails_new_profile_without_reinterpreting_old_gate(self):
        self.fixture.write(markers=self.marker())
        self.raw.write_text('SOFTWARE QA feedback: device missing 1 terminal',encoding='utf-8')
        new,_,checks=self.summary()
        self.assertEqual(checks['extraction']['validation_status'],'Failed')
        self.assertEqual(new['extraction']['missing_device_terminal_count'],1)
        old,_,old_checks=lvs.summarize(self.fixture.folder,self.fixture.layout)
        self.assertEqual(old_checks['extraction']['validation_status'],'Passed')
        self.assertEqual(old['extraction']['feedback'],new['extraction']['feedback'])
        self.assertNotIn('recognition_proof',old['extraction'])

    def test_xml_only_or_raw_only_warning_cannot_pass(self):
        self.fixture.write(markers=self.marker())
        self.assertEqual(self.summary()[2]['extraction']['validation_status'],'Failed')
        self.fixture.write()
        self.raw.write_text('unparsed retained raw warning',encoding='utf-8')
        self.assertEqual(self.summary()[2]['extraction']['validation_status'],'Failed')

    def test_unrelated_non_overlap_feedback_also_fails_new_recipe(self):
        self.fixture.write(markers=self.marker().replace('device missing 1 terminal','another warning'))
        self.assertEqual(self.summary()[2]['extraction']['validation_status'],'Failed')

    def test_missing_feedback_or_failed_model_proof_is_not_empty_success(self):
        self.raw.unlink()
        with self.assertRaises(DomainError):self.summary()
        self.raw.write_text('',encoding='utf-8')
        self.proof.side_effect=DomainError('software_qa_unproven','Unproven fixture',409)
        with self.assertRaises(DomainError):self.summary()

    def test_v3_artifacts_are_separate_and_legacy_mandatory_set_is_unchanged(self):
        legacy=lvs._fixed_files(self.fixture.layout)
        fresh=lvs._fixed_files(self.fixture.layout,profile())
        extra={'extraction-model-proof','extraction-raw-spice','extraction-models','extraction-deck'}
        self.assertEqual(set(fresh),set(legacy)|extra)
        self.assertEqual(set(lvs._file_types()),set(lvs.FILE_TYPES))
        self.assertEqual(set(lvs._file_types(profile())),set(lvs.FILE_TYPES)|extra)
        self.assertEqual(lvs_workflow.REQUIRED_FILES,set(lvs.FILE_TYPES))
        self.assertTrue(extra<=lvs_workflow.FILE_IDS)
        self.assertEqual(fresh['extracted-spice'],'extraction-comparison.spice')
        self.assertNotEqual(legacy['extracted-spice'],fresh['extracted-spice'])


class TerminalSourceGuardTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.LvsRecipeTests();self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.drc['id']='software-qa-drc'
        self.fixture.config['profile']=profile()
        self.fixture.config['repair_source_binding']={
            'schema':'hullcirq-lvs-terminal-repair-source-v1',
            'historical_lvs_run_id':'software-qa-original-lvs',
            'historical_lvs_record_sha256':'a'*64,'historical_lvs_execution_sha256':'b'*64,
            'layout_run_id':self.fixture.layout['id'],
            'layout_record_sha256':object_hash(self.fixture.layout),
            'drc_run_id':self.fixture.drc['id'],'drc_record_sha256':object_hash(self.fixture.drc),
            'source_inputs_sha256':object_hash({'software_qa_inputs':True})}
        self.patch=patch.object(lvs,'_fixed_profile',side_effect=lambda value:value)
        self.patch.start();self.addCleanup(self.patch.stop)

    def projection(self,configuration=None):
        return lvs.configuration_projection(self.fixture.drc,self.fixture.layout,
            configuration or self.fixture.config)

    def test_exact_original_source_binding_is_accepted_without_mutation(self):
        before=copy.deepcopy(self.fixture.config)
        self.projection()
        self.assertEqual(before,self.fixture.config)

    def test_foreign_ids_changed_record_hash_extra_fields_and_bad_sha_are_rejected(self):
        variants=[('schema','wrong'),('layout_run_id','other'),('drc_run_id','other'),
            ('layout_record_sha256','0'*64),('drc_record_sha256','0'*64),
            ('source_inputs_sha256','invalid'),('historical_lvs_record_sha256',True),
            ('historical_lvs_execution_sha256',None),('historical_lvs_run_id','')]
        for key,value in variants:
            config=copy.deepcopy(self.fixture.config);config['repair_source_binding'][key]=value
            with self.subTest(key=key),self.assertRaises(DomainError):self.projection(config)
        config=copy.deepcopy(self.fixture.config);config['repair_source_binding']['path']='forbidden'
        with self.assertRaises(DomainError):self.projection(config)

    def test_changed_input_binding_is_rejected_before_directory_or_command_execution(self):
        with patch.object(lvs,'source_inputs',return_value={'changed_fixture':True}),\
                patch.object(lvs.physical,'_execute') as execute,patch.object(lvs.tempfile,'mkdtemp') as directory:
            with self.assertRaises(DomainError):
                lvs.run_lvs(self.fixture.drc,self.fixture.layout,self.fixture.config)
            execute.assert_not_called();directory.assert_not_called()

    def test_wrong_helper_hash_is_rejected_before_its_code_can_execute(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);raw=b'raise RuntimeError("must not execute unpinned fixture")\n'
            (root/'fixture_helper.py').write_bytes(raw)
            fake=profile();fake['terminal_recognition_variant'].update(
                helper_path='scripts/fixture_helper.py',helper_sha256='0'*64)
            with self.assertRaises(DomainError) as caught:lvs._recognition_helper(root,fake)
            self.assertEqual(caught.exception.code,'lvs_recognition_source_changed')


if __name__=='__main__':unittest.main()
