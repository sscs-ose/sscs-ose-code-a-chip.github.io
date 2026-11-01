"""Isolated DRC parser/recipe QA; fabricated reports are never NPU evidence."""
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
from hullcirq import drc_tools as drc
import test_physical_tools as physical_fixtures

class DrcToolTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        prior=physical_fixtures.PhysicalToolTests();prior.setUp()
        prior.config['pdk_root']=str(self.root/'software-QA-PDK')
        self.layout={'id':'SOFTWARE-QA-layout','settings':prior.settings,'runtime_configuration':prior.config,
            'checks':{'artifacts':[{'id':'gds','sha256':'0'*64,'bytes':4,'relative_path':'original.gds'}]}}
        self.configuration={'physical_runtime':copy.deepcopy(prior.config),'working_directory':str(self.root),
            'profile':json.loads((ROOT/'configs/drc_profile_sky130.json').read_text())}

    def reports(self,magic=0,klayout=0):
        for key,count in [('magic-markers',magic),('klayout-report',klayout)]:
            p=self.root/drc.FIXED_FILES[key];p.parent.mkdir(parents=True,exist_ok=True)
            items=''.join("<item><cell>hullcirq_npu</cell><category>'rule.1'</category><values><value>polygon: (1,2;3,2;3,4;1,4)</value></values></item>" for _ in range(count))
            p.write_text('<report-database><categories><category><name>rule.1</name><description>SOFTWARE QA spacing</description></category></categories><items>'+items+'</items></report-database>')
        p=self.root/drc.FIXED_FILES['magic-report'];p.write_text(f'hullcirq_npu\n----------------------------------------\n[INFO] COUNT: {magic}\n[INFO] Should be divided by 3 or 4\n')
        p=self.root/drc.FIXED_FILES['klayout-violations'];p.write_text(json.dumps({'rule.1':klayout,'total':klayout}))
        self.metrics={'magic__drc_error__count':magic,'klayout__drc_error__count':klayout}
        p=self.root/drc.FIXED_FILES['metrics'];p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(self.metrics))

    def test_two_completed_zero_report_counts_are_required(self):
        self.reports();summary,metrics,checks=drc.summarize(self.root,self.layout)
        self.assertEqual(checks['drc']['validation_status'],'Passed')
        self.assertTrue(checks['drc']['completed']);self.assertEqual(summary['violations'],[])
        self.assertEqual(metrics,self.metrics)

    def test_finite_actual_violations_are_failed_with_complete_locations(self):
        self.reports(1,2);summary,_,checks=drc.summarize(self.root,self.layout)
        self.assertEqual(checks['drc']['validation_status'],'Failed');self.assertEqual(len(summary['violations']),3)
        self.assertEqual(summary['violations'][0]['geometry'],['polygon: (1,2;3,2;3,4;1,4)'])
        self.assertEqual(checks['drc']['waivers'],0)

    def test_missing_boolean_fraction_negative_or_nonfinite_count_rejected(self):
        self.reports()
        for value in (None,False,True,0.0,-1,float('nan'),float('inf'),'0'):
            with self.subTest(value=value):
                m=dict(self.metrics);m['magic__drc_error__count']=value
                (self.root/drc.FIXED_FILES['metrics']).write_text(json.dumps(m))
                with self.assertRaises((DomainError,ValueError)):drc.summarize(self.root,self.layout)

    def test_marker_metric_mismatch_is_rejected(self):
        self.reports(1,0);self.metrics['magic__drc_error__count']=0
        (self.root/drc.FIXED_FILES['metrics']).write_text(json.dumps(self.metrics))
        with self.assertRaises(DomainError):drc.summarize(self.root,self.layout)

    def test_magic_report_count_cannot_be_divided_to_make_pass(self):
        self.reports(3,0)
        p=self.root/drc.FIXED_FILES['magic-report'];p.write_text(p.read_text().replace('COUNT: 3','COUNT: 1'))
        with self.assertRaises(DomainError):drc.summarize(self.root,self.layout)

    def test_klayout_category_totals_must_match_markers(self):
        self.reports(0,1)
        (self.root/drc.FIXED_FILES['klayout-violations']).write_text('{"rule.1":0,"total":1}')
        with self.assertRaises(DomainError):drc.summarize(self.root,self.layout)

    def test_missing_complete_xml_is_not_a_zero_report(self):
        self.reports();p=self.root/drc.FIXED_FILES['magic-markers']
        for raw in ('<report-database/>','<empty/>','<!DOCTYPE x><report-database><categories/><items/></report-database>'):
            p.write_text(raw)
            with self.assertRaises(DomainError):drc.summarize(self.root,self.layout)

    def test_no_stage_can_be_skipped_or_magleft_blackboxed(self):
        original=copy.deepcopy(self.layout)
        cfg=drc.configuration_projection(self.layout,self.configuration)
        self.assertEqual(cfg['meta']['flow'],['Magic.DRC','KLayout.DRC'])
        self.assertTrue(cfg['MAGIC_DRC_USE_GDS']);self.assertIsNone(cfg['MAGIC_DRC_MAGLEFS'])
        self.assertNotIn('VERILOG_FILES',cfg);self.assertEqual(self.layout,original)
        for field,value in [('MAGIC_DRC_MAGLEFS',['fake.mag']),('KLAYOUT_DRC_THREADS',True)]:
            changed=copy.deepcopy(self.configuration);changed['profile']['config'][field]=value
            with self.assertRaises(DomainError):drc.configuration_projection(self.layout,changed)

    def test_s11_runtime_and_pdk_cannot_be_changed(self):
        changed=copy.deepcopy(self.configuration);changed['physical_runtime']['pdk_revision']='other'
        with self.assertRaises(DomainError):drc.configuration_projection(self.layout,changed)

    def test_fixed_command_only_versions_and_drc_from_frozen_gds(self):
        folder=self.root/'hullcirq-drc-software-qa';commands=drc.fixed_commands(self.configuration,folder)
        self.assertEqual(len(commands),2);self.assertIn('--with-initial-state',commands[1])
        self.assertNotIn('Classic',commands[1]);self.assertNotIn('--from',commands[1])
        with self.assertRaises(DomainError):drc.fixed_commands(self.configuration,self.root/'outside')

    def test_artifact_escape_and_alias_paths_are_rejected(self):
        (self.root/'a').write_text('SOFTWARE QA')
        for relative in ('../a','/a','C:/a','a\\b','a\x00'):
            with self.subTest(relative=relative),self.assertRaises(DomainError):drc._safe(self.root,relative)

    def test_unprepared_runtime_never_launches_tools(self):
        with patch.object(drc.physical,'_execute',side_effect=AssertionError('No actual EDA allowed')) as execute:
            result=drc.run_drc(self.layout,self.configuration)
        self.assertFalse(result['executed']);self.assertEqual(result['validation_status'],'Failed');execute.assert_not_called()

if __name__=='__main__':unittest.main()
