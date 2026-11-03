"""New-plan grid admission and unchanged historical v1 reconstruction; no EDA."""
import copy
import hashlib
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tests')]
from hullcirq.block_layout import effective_configuration as historical_configuration
from hullcirq.domain import DomainError
from hullcirq.observation import readonly_observation_scope
from hullcirq.physical_tools import (BLOCK_FLOW_SHA,BLOCK_RUNTIME_SHA,configuration_projection,effective_configuration)
from hullcirq.verification import object_hash
import test_block_layout as block_fixtures
import test_physical_tools as tool_fixtures


class BlockGridPreflightTests(unittest.TestCase):
    def setUp(self):
        self.fixture=tool_fixtures.PhysicalToolTests(methodName='runTest'); self.fixture.setUp()
        self.plan={'version':'block-regions-v1','core_um':[10,10,110,110],
                   'regions':[{'id':'scalar','targets':[{'node_id':'scalar'}],'rect_um':[12,12,108,108]}]}
        self.design={'nodes':[{'id':'scalar','module_name':'scalar_rtl'}],'physical_design':self.plan}
        self.manifest={'nodes':[{'node_id':'scalar','module_name':'scalar_rtl'}]}

    def test_every_core_and_region_axis_rejects_off_grid_without_mutation(self):
        for container in ('core','region'):
            for axis in range(4):
                design=copy.deepcopy(self.design)
                rectangle=design['physical_design']['core_um'] if container=='core' else design['physical_design']['regions'][0]['rect_um']
                rectangle[axis]+=0.001
                before=copy.deepcopy(design)
                with self.subTest(container=container,axis=axis),self.assertRaises(DomainError) as caught:
                    effective_configuration(self.fixture.config,design,ROOT)
                self.assertEqual(caught.exception.code,'block_region_coordinate_grid')
                self.assertIn('0.005 um',caught.exception.message)
                self.assertIn('not rounded automatically',caught.exception.message)
                self.assertEqual(design,before)

    def test_grid_aligned_decimal_coordinates_preserve_exact_values_and_hash(self):
        self.plan['core_um']=[10.005,10.335,110.995,110.665]
        self.plan['regions'][0]['rect_um']=[12.005,12.335,108.995,108.665]
        original=copy.deepcopy(self.design)
        result=effective_configuration(self.fixture.config,self.design,ROOT)
        self.assertEqual(result['block_plan'],self.plan)
        self.assertEqual(result['block_plan_sha256'],object_hash(self.plan))
        self.assertEqual(self.design,original)
        self.assertEqual(configuration_projection(self.fixture.settings,result,self.manifest)['CORE_AREA'],self.plan['core_um'])

    def test_manual_float_boundary_matches_client_tolerance_without_rounding(self):
        for drift in (-1e-12,1e-12):
            design=copy.deepcopy(self.design)
            design['physical_design']['regions'][0]['rect_um'][0]+=drift
            original=copy.deepcopy(design)
            result=effective_configuration(self.fixture.config,design,ROOT)
            self.assertEqual(result['block_plan'],design['physical_design'])
            self.assertEqual(result['block_plan_sha256'],object_hash(design['physical_design']))
            self.assertEqual(design,original)
        for drift in (-1e-8,1e-8,5e-10):
            design=copy.deepcopy(self.design)
            design['physical_design']['regions'][0]['rect_um'][0]+=drift
            with self.subTest(drift=drift),self.assertRaises(DomainError) as caught:
                effective_configuration(self.fixture.config,design,ROOT)
            self.assertEqual(caught.exception.code,'block_region_coordinate_grid')

    def test_three_row_fraction_is_rejected_but_historical_projection_is_unchanged(self):
        self.plan['core_um']=[10,10,1010,1010]
        self.plan['regions'][0]['rect_um']=[22,22,988,22+976/3]
        old=historical_configuration(self.fixture.config,self.design,ROOT)
        before=copy.deepcopy(old)
        with self.assertRaises(DomainError) as caught: effective_configuration(self.fixture.config,self.design,ROOT)
        self.assertEqual(caught.exception.code,'block_region_coordinate_grid')
        projected=configuration_projection(self.fixture.settings,old,self.manifest)
        self.assertEqual(projected['CORE_AREA'],self.plan['core_um'])
        self.assertEqual(old,before)

    def test_default_and_explicit_mixed_configuration_remain_unchanged(self):
        for physical in (None,{'version':'mixed-v1'}):
            design=copy.deepcopy(self.design)
            if physical is None: design.pop('physical_design')
            else: design['physical_design']=physical
            self.assertEqual(effective_configuration(self.fixture.config,design,ROOT),historical_configuration(self.fixture.config,design,ROOT))

    def test_first_executed_v1_bytes_and_pins_are_immutable(self):
        expected={
            'src/hullcirq/block_layout.py':'cbf41fb6e4de3fc93a1076a258a309160da542f82f785b860a999c9702418208',
            'scripts/block_region_flow_v1.py':'b7685078c3860e3cbb160b43160f9268ef433959db0806e71a841123795d1c26',
            'configs/physical_profile_sky130_block_regions_v1.json':'58fe80733ebc552f56244f0e20e52c4ceef9e0118959d79c57913f630edcafed'}
        for relative,digest in expected.items():
            self.assertEqual(hashlib.sha256((ROOT/relative).read_bytes()).hexdigest(),digest)
        self.assertEqual(BLOCK_RUNTIME_SHA,expected['src/hullcirq/block_layout.py'])
        self.assertEqual(BLOCK_FLOW_SHA,expected['scripts/block_region_flow_v1.py'])


class BlockGridWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.fixture=block_fixtures.BlockLayoutSourceTests(methodName='runTest'); self.fixture.setUp(); self.addCleanup(self.fixture.doCleanups)
        self.owner=self.fixture.fixture
        self.design=self.fixture.physical_design()
        self.design['physical_design']['regions'][0]['rect_um'][0]+=0.001
        self.fixture.save(self.design)

    def test_new_non_grid_plan_is_blocked_before_a_run_or_worker_is_created(self):
        manager=self.fixture.manager
        key,source,error=manager._source_state()
        self.assertIsNone(source); self.assertEqual(error['code'],'block_region_coordinate_grid')
        with patch('threading.Thread.start') as start:
            with self.assertRaises(DomainError) as caught:
                manager.start('layout',self.owner.base.job['id'],self.owner.synthesis['id'],self.owner.simulation['id'],self.owner.store.envelope()['revision']['id'])
            start.assert_not_called()
        self.assertIn('0.005 um',caught.exception.message)
        self.assertEqual(manager._state['runs'],[])
        with readonly_observation_scope():
            envelope=manager.envelope()['physical_workflow']
            self.assertFalse(envelope['ready']); self.assertIn('not rounded automatically',envelope['blocked_reason'])

    def test_historical_non_grid_failed_attempt_reopens_and_is_readable_unchanged(self):
        manager=self.fixture.manager
        def old_grid_failure(*args,**kwargs):
            raise DomainError('block_region_database','SOFTWARE QA: old OpenDB grid rejection, no tool execution.')
        manager._runner=old_grid_failure
        # Only this copied fixture simulates admission under the old source code.
        with patch('hullcirq.physical_workflow.effective_configuration',historical_configuration):
            manager.start('layout',self.owner.base.job['id'],self.owner.synthesis['id'],self.owner.simulation['id'],self.owner.store.envelope()['revision']['id'])
            manager._worker.join(20)
        self.assertFalse(manager._worker.is_alive())
        original=copy.deepcopy(manager._state['runs'][-1]); raw=manager.path.read_bytes()
        self.assertEqual(original['execution_status'],'Failed')
        self.assertEqual(original['error']['code'],'block_region_database')
        reopened=self.owner.new_manager(); self.addCleanup(reopened.close)
        self.assertEqual(reopened._state['runs'][-1],original)
        self.assertEqual(original['record_hash'],object_hash({k:v for k,v in original.items() if k!='record_hash'}))
        with readonly_observation_scope():
            saved=reopened.run(original['id'])
            self.assertEqual(saved['error'],original['error'])
            self.assertEqual(saved['record_hash'],original['record_hash'])
            self.assertEqual(reopened.artifact(original['id'],'runtime-configuration'),original['runtime_configuration'])
            self.assertFalse(reopened.envelope()['physical_workflow']['ready'])
        self.assertEqual(manager.path.read_bytes(),raw)


if __name__=='__main__': unittest.main()
