"""Isolated view/HTTP fixtures only; no actual layout, SDK, model or EDA starts."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import threading
import types
import unittest
from unittest.mock import Mock, patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tests')]
from hullcirq import block_layout_v2 as v2
from hullcirq import block_layout as v1
from hullcirq.block_placement_view import block_placement_projection
from hullcirq.domain import DomainError
from hullcirq.observation import readonly_observation_scope
from hullcirq.physical_tools import configuration_projection
from hullcirq.physical_workflow import PhysicalWorkflowManager
import test_block_layout_v2 as geometry_fixtures
import test_physical_tools as tool_fixtures
import test_physical_workflow_http as http_fixtures


class ViewFixture:
    """Synthetic retained geometry plus an explicit complete-proof test double.

    The production route always supplies the real physical-proof validator;
    this fixture does not create actual physical execution evidence.
    """
    def __init__(self,case):
        self.temp=tempfile.TemporaryDirectory(prefix='block-view-fixture-');case.addCleanup(self.temp.cleanup)
        self.folder=Path(self.temp.name)
        self.geometry=geometry_fixtures.BlockLayoutV2Tests('runTest');self.geometry.setUp()
        tools=tool_fixtures.PhysicalToolTests('runTest');tools.setUp()
        self.configuration=v2.effective_configuration(tools.config,{**self.geometry.design,'physical_design':self.geometry.plan},ROOT)
        self.settings={**tools.settings,'top_module':'top'}
        self.manifest={'nodes':[{'node_id':'npu2-pe','module_name':'pe'}]}
        self.inputs=v2.source_input(self.configuration,self.manifest,'top')
        self.ownership=v2.build_ownership(self.geometry.synthesis,self.inputs)
        self.geometry.ownership=self.ownership
        self.proof=self.geometry.proof();self.proof['unclaimed_final_cells']=['support_clock']
        self.capacity={'version':v2.VERSION,'execution_profile':v2.PROFILE_VERSION,'name_codec':v2.NAME_CODEC,
            'ownership_sha256':v2.object_hash(self.ownership),'protected_mapped_ties':v2.mapped_tie_names(self.ownership),
            'regions':[{'id':r['id'],'cell_area_um2':70,'row_area_um2':100,'maximum_utilization':.7} for r in self.ownership['regions']]}
        final_def=self.geometry.def_text(self.proof).replace('COMPONENTS 12 ;','COMPONENTS 13 ;').replace('END COMPONENTS',' - support_clock sky130_fd_sc_hd__clkbuf_16 + PLACED ( 200000 200000 ) N ;\nEND COMPONENTS')
        files={'block-input':self.inputs,'block-plan':self.geometry.plan,'block-synthesis':self.geometry.synthesis,
            'block-ownership':self.ownership,'block-capacity':self.capacity,'block-placement-proof':self.proof,
            'config':configuration_projection(self.settings,self.configuration,self.manifest),'def':final_def,
            'block-runtime':(ROOT/'src/hullcirq/block_layout_v2.py').read_bytes(),
            'block-flow':(ROOT/'scripts/block_region_flow_v2.py').read_bytes()}
        entries=[]
        for identifier,value in files.items():
            data=value if isinstance(value,bytes) else value.encode() if isinstance(value,str) else json.dumps(value).encode()
            (self.folder/identifier).write_bytes(data)
            entries.append({'id':identifier,'relative_path':identifier,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'content_type':'application/json' if isinstance(value,dict) else 'text/plain; charset=utf-8'})
        self.run={'id':'software-block-view','revision_id':'software-revision','physical_design_revision_id':'software-physical-revision',
            'execution_status':'Completed','validation_status':'Passed','review_status':'Accepted','evidence_kind':'trusted_fixed_tool_execution',
            'global_job_id':'software-global','synthesis_run_id':'software-synthesis','netlist_run_id':'software-simulation',
            'source_manifest_sha256':v2.object_hash(self.manifest),'source_manifest':self.manifest,'settings':self.settings,'runtime_configuration':self.configuration,
            'checks':{'artifacts':entries,'artifacts_directory':str(self.folder),'placement_mode':v2.VERSION},'record_hash':'f'*64,
            'software_qa_view_fixture_not_hardware_evidence':True}
        self.validate=Mock(return_value=None)

    def projection(self,run=None):return block_placement_projection(self.run if run is None else run,self.validate)
    def replace(self,identifier,value):
        raw=value if isinstance(value,bytes) else value.encode() if isinstance(value,str) else json.dumps(value).encode()
        (self.folder/identifier).write_bytes(raw)
        entry=next(e for e in self.run['checks']['artifacts'] if e['id']==identifier)
        entry.update(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


class BlockPlacementProjectionTests(unittest.TestCase):
    def setUp(self):self.f=ViewFixture(self)

    def test_exact_validated_geometry_is_compact_original_owned_only_and_read_only(self):
        before=copy.deepcopy(self.f.run);files={p.name:p.read_bytes() for p in self.f.folder.iterdir()}
        value=self.f.projection();self.f.validate.assert_called_once_with(self.f.run)
        self.assertEqual(value['counts'],{'original_owned_cells':12,'regions':4,'unclaimed_final_cells':1,'final_DEF_components':13,'original_mapped_ties':4})
        self.assertEqual(len(value['cells']),12);self.assertNotIn('support_clock',{c['name'] for c in value['cells']})
        self.assertEqual(value['source']['plan_sha256'],self.f.configuration['block_plan_sha256'])
        for field,identifier in [('proof_sha256','block-placement-proof'),('ownership_sha256','block-ownership'),('final_def_sha256','def')]:
            self.assertEqual(value['source'][field],next(e['sha256'] for e in self.f.run['checks']['artifacts'] if e['id']==identifier))
        self.assertNotIn(str(self.f.folder),json.dumps(value))
        self.assertEqual(self.f.run,before);self.assertEqual({p.name:p.read_bytes() for p in self.f.folder.iterdir()},files)

    def test_failed_mixed_unexecuted_missing_proof_and_injected_fixtures_are_unavailable(self):
        for change in (lambda r:r.update(execution_status='Failed'),lambda r:r.update(validation_status='Failed'),
                       lambda r:r.update(execution_status='Running'),lambda r:r['runtime_configuration'].update(profile={'profile_version':'hullcirq-sky130-layout-v1'}),
                       lambda r:r.update(evidence_kind='software_qa_fixture'),lambda r:r['checks']['artifacts'].pop(5)):
            run=copy.deepcopy(self.f.run);change(run)
            with self.subTest(change=change),self.assertRaises(DomainError) as caught:self.f.projection(run)
            self.assertEqual(caught.exception.code,'block_placement_view_unavailable')
        self.f.validate.assert_not_called()

    def test_full_proof_failure_is_not_silently_ignored(self):
        self.f.validate.side_effect=DomainError('physical_proof_conflict','SOFTWARE QA sentinel rejection')
        with self.assertRaises(DomainError) as caught:self.f.projection()
        self.assertEqual(caught.exception.code,'physical_proof_conflict')

    def test_tampered_artifact_frozen_runtime_and_arbitrary_paths_fail_closed(self):
        (self.f.folder/'block-placement-proof').write_bytes(b'changed')
        with self.assertRaises(DomainError):self.f.projection()
        self.f.replace('block-placement-proof',self.f.proof)
        self.f.replace('block-runtime',b'not the immutable runtime')
        with self.assertRaises(DomainError):self.f.projection()
        self.f.replace('block-runtime',(ROOT/'src/hullcirq/block_layout_v2.py').read_bytes())
        next(e for e in self.f.run['checks']['artifacts'] if e['id']=='block-input')['relative_path']='../outside'
        with self.assertRaises(DomainError):self.f.projection()

    def test_rehashed_changed_ownership_plan_capacity_proof_and_def_are_rejected(self):
        changes={'block-input':lambda d:d.update(source_manifest_sha256='0'*64),
            'block-plan':lambda d:d['core_um'].__setitem__(2,999),
            'block-ownership':lambda d:d['regions'][0]['cells'].pop(),
            'block-capacity':lambda d:d['regions'][0].update(cell_area_um2=71),
            'block-placement-proof':lambda d:d['cells'][0].update(bbox_um=[0,0,1,2])}
        for identifier,change in changes.items():
            old=(self.f.folder/identifier).read_bytes();value=json.loads(old);change(value);self.f.replace(identifier,value)
            with self.subTest(identifier=identifier),self.assertRaises(DomainError):self.f.projection()
            self.f.replace(identifier,old)
        old=(self.f.folder/'def').read_bytes();self.f.replace('def',old.replace(b'\\[',b'['))
        with self.assertRaises(DomainError):self.f.projection()

    def test_unclaimed_set_is_checked_not_merely_counted(self):
        proof=copy.deepcopy(self.f.proof);proof['unclaimed_final_cells']=['fabricated_support'];self.f.replace('block-placement-proof',proof)
        with self.assertRaises(DomainError) as caught:self.f.projection()
        self.assertEqual(caught.exception.code,'block_placement_view_integrity')

    def test_actual_manager_method_does_not_observe_persist_or_change_epochs(self):
        record=copy.deepcopy(self.f.run)
        manager=types.SimpleNamespace(lock=threading.RLock(),_state={'runs':[record],'source_epoch':4},_committed={'epoch':4},
            _run=lambda identifier:record,_decorate=lambda run:{**run,'freshness':'Stale','review_status':'Awaiting Review'},
            _adapter=lambda:(Mock(side_effect=AssertionError('No tool run')),Mock()),
            observe_design=Mock(side_effect=AssertionError('No source observation')), _persist=Mock(side_effect=AssertionError('No writes')))
        before=copy.deepcopy((manager._state,manager._committed))
        with patch('hullcirq.physical_workflow.validate_physical_proof',side_effect=lambda run,validator:self.f.validate(run)),readonly_observation_scope():
            value=PhysicalWorkflowManager.block_placement(manager,record['id'])
        self.assertTrue(value['historical']);self.assertEqual(value['status']['freshness'],'Stale')
        self.assertEqual((manager._state,manager._committed),before);manager.observe_design.assert_not_called();manager._persist.assert_not_called()

    def test_historical_passed_v1_proof_uses_its_own_runtime_without_relabeling(self):
        synthesis=copy.deepcopy(self.f.geometry.synthesis)
        synthesis['modules']['pe']['cells']={'plain_reg':{'type':'sky130_fd_sc_hd__dfxtp_1'},'tie_constant':{'type':v1.MAPPED_TIE_MASTER}}
        config=v1.effective_configuration(self.f.configuration,{**self.f.geometry.design,'physical_design':self.f.geometry.plan},ROOT)
        inputs=v1.source_input(config,self.f.manifest,'top');owner=v1.build_ownership(synthesis,inputs)
        cells=[]
        for region in owner['regions']:
            x,y=region['rect_um'][:2]
            for source in region['cells']:
                cell={'name':source['name'],'master':source['master'],'region_id':region['id'],'placed':True,'group_member':True,
                      'bbox_um':[x,y,x+1,y+2],'origin_dbu':[x*1000,y*1000],'orient':'R0'}
                if source['master']==v1.MAPPED_TIE_MASTER:cell['mapped_tie_protected']=True
                cells.append(cell)
        proof={'version':v1.VERSION,'ownership_sha256':v1.object_hash(owner),'cells':cells,'database_units_per_micron':1000,
               'validation_status':'Passed','unclaimed_final_cells':[]}
        capacity={'version':v1.VERSION,'ownership_sha256':v1.object_hash(owner),'protected_mapped_ties':v1.mapped_tie_names(owner),
                  'regions':[{'id':r['id'],'cell_area_um2':70,'row_area_um2':100,'maximum_utilization':.7} for r in owner['regions']]}
        text='UNITS DISTANCE MICRONS 1000 ;\nCOMPONENTS 8 ;\n'+'\n'.join(
            ' - '+c['name']+' '+c['master']+' + PLACED ( '+str(c['origin_dbu'][0])+' '+str(c['origin_dbu'][1])+' ) N ;' for c in cells)+'\nEND COMPONENTS\n'
        self.f.run['runtime_configuration']=config
        for identifier,value in {'block-input':inputs,'block-plan':self.f.geometry.plan,'block-synthesis':synthesis,'block-ownership':owner,
            'block-placement-proof':proof,'block-capacity':capacity,'config':configuration_projection(self.f.settings,config,self.f.manifest),'def':text,
            'block-runtime':(ROOT/'src/hullcirq/block_layout.py').read_bytes(),'block-flow':(ROOT/'scripts/block_region_flow_v1.py').read_bytes()}.items():self.f.replace(identifier,value)
        value=self.f.projection()
        self.assertEqual(value['profile_version'],'hullcirq-sky130-block-regions-v1')
        self.assertEqual(value['counts']['original_owned_cells'],8)
        self.assertTrue(all(c['source_name']==c['name']==c['odb_name'] for c in value['cells']))


class BlockPlacementHTTPTests(unittest.TestCase):
    def setUp(self):
        self.http=http_fixtures.PhysicalWorkflowHTTPTests('runTest');self.http.setUp();self.addCleanup(self.http.doCleanups)
        self.f=ViewFixture(self);self.calls=[]
        def inspect(identifier):
            if identifier!=self.f.run['id']:raise DomainError('physical_run_not_found','SOFTWARE QA missing layout',404)
            self.calls.append(identifier);return self.f.projection()
        self.http.double.block_placement=inspect

    def test_get_is_read_only_repeatable_and_does_not_start_save_or_adopt(self):
        before=copy.deepcopy(self.http.double.record);state=copy.deepcopy(self.http.original_physical._state)
        committed=copy.deepcopy(self.http.original_physical._committed);directory=self.http.qa.store.path
        files={p.name:(p.read_bytes(),p.stat().st_mtime_ns) for p in directory.glob('*.json')}
        for _ in range(2):
            status,raw,value,headers=self.http.json_request('/api/physical-workflow/runs/software-block-view/block-placement')
            self.assertEqual(status,200);self.assertEqual(value['counts']['original_owned_cells'],12)
            self.assertEqual(headers['Cache-Control'],'no-store');self.assertEqual(headers['X-Content-Type-Options'],'nosniff')
        self.assertEqual(self.calls,['software-block-view']*2);self.assertEqual(self.http.double.calls,[])
        self.assertEqual(self.http.double.record,before);self.assertEqual(self.http.original_physical._state,state)
        self.assertEqual(self.http.original_physical._committed,committed)
        self.assertEqual({p.name:(p.read_bytes(),p.stat().st_mtime_ns) for p in directory.glob('*.json')},files)

    def test_failed_missing_and_arbitrary_route_components_do_not_expose_geometry(self):
        self.f.run['execution_status']='Failed'
        status,_,value,_=self.http.json_request('/api/physical-workflow/runs/software-block-view/block-placement')
        self.assertEqual(status,409);self.assertEqual(value['error']['code'],'block_placement_view_unavailable')
        for path in ('/api/physical-workflow/runs/missing/block-placement','/api/physical-workflow/runs/../block-placement',
                     '/api/physical-workflow/runs/software%5Cblock/block-placement','/api/physical-workflow/runs/software-block-view/block-placement/extra'):
            self.assertEqual(self.http.json_request(path)[0],404)
        self.assertEqual(self.http.double.calls,[])

    def test_workspace_session_conflict_is_rejected_before_view_reads(self):
        runtime=types.SimpleNamespace(require_session=Mock(side_effect=DomainError('workspace_session_changed','SOFTWARE QA session changed',409)))
        self.http.server.workspace=runtime
        try:
            status,_,value,_=self.http.json_request('/api/physical-workflow/runs/software-block-view/block-placement')
            self.assertEqual(status,409);self.assertEqual(value['error']['code'],'workspace_session_changed');self.assertEqual(self.calls,[])
        finally:self.http.server.workspace=None


if __name__=='__main__':unittest.main()
