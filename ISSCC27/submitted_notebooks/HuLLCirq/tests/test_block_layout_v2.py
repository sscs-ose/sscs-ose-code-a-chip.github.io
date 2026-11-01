"""V2 codec and exact region proof in isolated Python/stub API; no EDA/model."""
import ast
import copy
import hashlib
import json
import os
from pathlib import Path
import runpy
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from hullcirq import block_layout_v2 as v2
from hullcirq.domain import DomainError


class Instance:
    def __init__(self,name,master,x=20,y=20):
        self.name,self.master,self.x,self.y=name,master,x,y
        self.protected=False;self.group=None;self.placed=True
    def getName(self): return self.name
    def getMaster(self): return types.SimpleNamespace(getName=lambda:self.master,getWidth=lambda:1000,getHeight=lambda:2000)
    def setDoNotTouch(self,value): self.protected=value
    def isDoNotTouch(self): return self.protected
    def getBBox(self): return Box(self.x*1000,self.y*1000,(self.x+1)*1000,(self.y+2)*1000)
    def getLocation(self): return [self.x*1000,self.y*1000]
    def getOrient(self): return 'R0'
    def isPlaced(self): return self.placed
    def getGroup(self): return self.group


class Box:
    def __init__(self,*coords): self.coords=coords
    def xMin(self): return self.coords[0]
    def yMin(self): return self.coords[1]
    def xMax(self): return self.coords[2]
    def yMax(self): return self.coords[3]


class BlockLayoutV2Tests(unittest.TestCase):
    def setUp(self):
        self.design={'nodes':[{'id':'npu2-pe','module_name':'pe','instance_array':{'rows':2,'columns':2}}]}
        self.plan={'version':'block-regions-v1','core_um':[10,10,210,210],'regions':[
            {'id':'pe'+str(r)+str(c),'targets':[{'node_id':'npu2-pe','instance_index':[r,c]}],
             'rect_um':[20+c*90,20+r*90,100+c*90,100+r*90]} for r in range(2) for c in range(2)]}
        self.inputs={'version':v2.VERSION,'execution_profile':v2.PROFILE_VERSION,'name_codec':v2.NAME_CODEC,
            'top_module':'top','design':self.design,'plan':self.plan,'plan_sha256':v2.object_hash(self.plan),'source_manifest_sha256':'a'*64}
        self.synthesis={'modules':{'top':{'cells':{'pe'+str(r)+str(c):{'type':'pe'} for r in range(2) for c in range(2)}},
            'pe':{'cells':{'sum_reg[0]':{'type':'sky130_fd_sc_hd__dfxtp_1'},
                           'tie_constant[0]':{'type':v2.MAPPED_TIE_MASTER},'plain_gate':{'type':'sky130_fd_sc_hd__and2_1'}}}}}
        self.ownership=v2.build_ownership(self.synthesis,self.inputs)

    def instances(self):
        return {cell['odb_name']:Instance(cell['odb_name'],cell['master'],*region['rect_um'][:2])
                for region in self.ownership['regions'] for cell in region['cells']}

    def proof(self):
        cells=[]
        for region in self.ownership['regions']:
            x,y=region['rect_um'][:2]
            for source in region['cells']:
                cells.append({k:source[k] for k in ('name','source_name','odb_name','master')})
                cells[-1].update(region_id=region['id'],placed=True,group_member=True,bbox_um=[x,y,x+1,y+2],
                                 origin_dbu=[x*1000,y*1000],orient='R0')
                if source['master']==v2.MAPPED_TIE_MASTER:cells[-1]['mapped_tie_protected']=True
        return {'version':v2.VERSION,'execution_profile':v2.PROFILE_VERSION,'name_codec':v2.NAME_CODEC,
                'ownership_sha256':v2.object_hash(self.ownership),'database_units_per_micron':1000,'cells':cells,'validation_status':'Passed'}

    def def_text(self,proof,units=1000):
        return 'UNITS DISTANCE MICRONS '+str(units)+' ;\nCOMPONENTS '+str(len(proof['cells']))+' ;\n'+'\n'.join(
            ' - '+cell['odb_name']+' '+cell['master']+' + PLACED ( '+str(cell['origin_dbu'][0]*units//1000)+' '
            +str(cell['origin_dbu'][1]*units//1000)+' ) N ;' for cell in proof['cells'])+'\nEND COMPONENTS\n'

    def test_codec_roundtrip_is_exact_for_current_lane_names_and_not_blanket_unescape(self):
        for source in ('control/count[0]_sky130_fd_sc_hd__dfxtp_2_Q','pe00/sum_reg[0]','bank_a[0][1]/$logic.foo[-1]','plain/leaf'):
            encoded=v2.source_to_odb_name(source)
            self.assertEqual(v2.odb_to_source_name(encoded),source)
            self.assertEqual(encoded,source.replace('[','\\[').replace(']','\\]'))
        for source in ('', '/leading','trailing/','double//segment','bad\\escape','white space/cell','control\n/cell'):
            with self.subTest(source=source),self.assertRaises(DomainError):v2.source_to_odb_name(source)
        for encoded in ('pe00/sum[0]','pe00/unknown\\x','pe00/trailing\\','pe00/slash\\/cell','pe00/escaped\\\\name'):
            with self.subTest(encoded=encoded),self.assertRaises(DomainError):v2.odb_to_source_name(encoded)

    def test_ownership_retains_every_source_and_exact_encoded_name(self):
        bindings=v2.ownership_name_bindings(self.ownership)
        self.assertEqual(len(bindings),12)
        for name,cell in bindings.items():
            self.assertEqual(cell['source_name'],name);self.assertEqual(v2.odb_to_source_name(cell['odb_name']),name)
        self.assertEqual(self.ownership['name_codec'],v2.NAME_CODEC)
        self.assertEqual(self.ownership['execution_profile'],v2.PROFILE_VERSION)

    def test_unknown_codec_wrong_profile_ambiguous_alias_and_duplicate_mapping_reject(self):
        changes=(lambda o:o.update(name_codec='unknown'),lambda o:o.update(execution_profile='v1'),
                 lambda o:o['regions'][0]['cells'][0].update(source_name='other'),
                 lambda o:o['regions'][0]['cells'][0].update(odb_name='other'),
                 lambda o:o['regions'][0]['cells'].append(copy.deepcopy(o['regions'][0]['cells'][0])))
        for change in changes:
            bad=copy.deepcopy(self.ownership);change(bad)
            with self.subTest(change=change),self.assertRaises(DomainError):v2.ownership_name_bindings(bad)

    def test_apply_exact_bijection_rejects_missing_unencoded_alias_and_wrong_master(self):
        instances=self.instances();bound=v2.bind_mapped_instances(self.ownership,instances)
        self.assertEqual(len(bound),12)
        for kind in ('missing','unencoded_alias','wrong_master'):
            bad=self.instances();cell=next(c for r in self.ownership['regions'] for c in r['cells'] if '[' in c['name'])
            inst=bad.pop(cell['odb_name'])
            if kind=='unencoded_alias':inst.name=cell['name'];bad[cell['name']]=inst
            if kind=='wrong_master':inst.master='sky130_fd_sc_hd__dfxtp_2';bad[cell['odb_name']]=inst
            with self.subTest(kind=kind),self.assertRaises(DomainError):v2.bind_mapped_instances(self.ownership,bad)

    def test_encoded_tie_protection_retains_source_list_and_never_touches_support(self):
        instances=self.instances();instances['inserted_support']=Instance('inserted_support',v2.MAPPED_TIE_MASTER)
        names=v2.protect_mapped_ties(self.ownership,instances)
        self.assertEqual(names,v2.mapped_tie_names(self.ownership));self.assertEqual(len(names),4)
        self.assertEqual(sum(inst.protected for inst in instances.values()),4)
        self.assertFalse(instances['inserted_support'].protected)

    def test_proof_requires_exact_bijection_membership_containment_and_ties(self):
        proof=self.proof();v2.validate_placement(self.ownership,proof)
        changes=(lambda p:p['cells'].pop(),lambda p:p['cells'][0].update(source_name='wrong'),
                 lambda p:p['cells'][0].update(odb_name='wrong'),lambda p:p['cells'][0].update(group_member=False),
                 lambda p:p['cells'][0].update(bbox_um=[0,0,1,2]),lambda p:p.update(name_codec='old'),
                 lambda p:next(c for c in p['cells'] if c['master']==v2.MAPPED_TIE_MASTER).update(mapped_tie_protected=False),
                 lambda p:next(c for c in p['cells'] if c['master']==v2.MAPPED_TIE_MASTER).update(master='sky130_fd_sc_hd__buf_1'))
        for change in changes:
            bad=copy.deepcopy(proof);change(bad)
            with self.subTest(change=change),self.assertRaises(DomainError):v2.validate_placement(self.ownership,bad)

    def test_final_resized_master_is_allowed_but_must_match_actual_final_def(self):
        proof=self.proof();cell=next(c for c in proof['cells'] if c['master']=='sky130_fd_sc_hd__dfxtp_1')
        cell['master']='sky130_fd_sc_hd__dfxtp_2'
        v2.validate_def_binding(self.def_text(proof),self.ownership,proof)
        with self.assertRaises(DomainError):v2.validate_def_binding(self.def_text(proof).replace('dfxtp_2','dfxtp_1'),self.ownership,proof)

    def test_def_uses_exact_raw_odb_names_units_and_unique_components(self):
        proof=self.proof();text=self.def_text(proof)
        v2.validate_def_binding(text,self.ownership,proof)
        v2.validate_def_binding(self.def_text(proof,100),self.ownership,proof)
        for bad in (text.replace('\\[','[').replace('\\]',']'),text.replace('MICRONS 1000','MICRONS 2000'),
                    text.replace('20000 20000','20001 20000'),text.replace('END COMPONENTS',' - '+proof['cells'][0]['odb_name']+' sky130_fd_sc_hd__and2_1 ;\nEND COMPONENTS')):
            with self.subTest(bad=bad[:40]),self.assertRaises(DomainError):v2.validate_def_binding(bad,self.ownership,proof)

    def test_capacity_keeps_exact_tie_list_and_v2_identity(self):
        cap={'version':v2.VERSION,'execution_profile':v2.PROFILE_VERSION,'name_codec':v2.NAME_CODEC,
             'ownership_sha256':v2.object_hash(self.ownership),'protected_mapped_ties':v2.mapped_tie_names(self.ownership),
             'regions':[{'id':r['id'],'cell_area_um2':70,'row_area_um2':100,'maximum_utilization':.7} for r in self.ownership['regions']]}
        v2.validate_capacity(self.ownership,cap)
        for change in (lambda c:c['protected_mapped_ties'].pop(),lambda c:c.update(name_codec='wrong'),
                       lambda c:c['regions'][0].update(cell_area_um2=71)):
            bad=copy.deepcopy(cap);change(bad)
            with self.assertRaises(DomainError):v2.validate_capacity(self.ownership,bad)

    def test_plan_schema_stays_v1_but_fresh_profile_and_inputs_are_v2(self):
        design={**self.design,'physical_design':self.plan}
        config=v2.effective_configuration({'working_directory':'unchanged','resume':{'old':True}},design,ROOT)
        self.assertEqual(config['profile']['profile_version'],'hullcirq-sky130-block-regions-v2')
        self.assertNotIn('resume',config)
        manifest={'nodes':[{'node_id':'npu2-pe','module_name':'pe'}]}
        inputs=v2.source_input(config,manifest,'top')
        self.assertEqual(inputs['plan'],self.plan);self.assertEqual(inputs['version'],'block-regions-v1')
        self.assertEqual(inputs['execution_profile'],v2.PROFILE_VERSION)
        config['profile']['profile_version']='hullcirq-sky130-block-regions-v1'
        with self.assertRaises(DomainError):v2.source_input(config,manifest,'top')

    def test_frozen_v1_bytes_unchanged_and_v2_standalone_syntax(self):
        expected={'src/hullcirq/block_layout.py':'cbf41fb6e4de3fc93a1076a258a309160da542f82f785b860a999c9702418208',
                  'scripts/block_region_flow_v1.py':'b7685078c3860e3cbb160b43160f9268ef433959db0806e71a841123795d1c26',
                  'configs/physical_profile_sky130_block_regions_v1.json':'58fe80733ebc552f56244f0e20e52c4ceef9e0118959d79c57913f630edcafed'}
        for path,digest in expected.items():self.assertEqual(hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),digest)
        for path in ('src/hullcirq/block_layout_v2.py','scripts/block_region_flow_v2.py'):ast.parse((ROOT/path).read_text())
        standalone=runpy.run_path(str(ROOT/'src/hullcirq/block_layout_v2.py'))
        self.assertEqual(standalone['odb_to_source_name']('pe00/reg\\[0\\]'),'pe00/reg[0]')


class BlockFlowV2StubTests(unittest.TestCase):
    # These methods exercise the actual new flow body against an explicit API
    # double. They do not start OpenROAD or count as actual database evidence.
    instances=BlockLayoutV2Tests.instances
    def_text=BlockLayoutV2Tests.def_text
    def setUp(self):
        BlockLayoutV2Tests.setUp(self)
        self.temp=tempfile.TemporaryDirectory(prefix='block-v2-stub-');self.addCleanup(self.temp.cleanup)
        self.folder=Path(self.temp.name)
        for filename,value in (('block-input.json',self.inputs),('block-ownership.json',self.ownership)):
            (self.folder/filename).write_text(json.dumps(value))
        self.inst=self.instances();self.inst['inserted_support']=Instance('inserted_support','sky130_fd_sc_hd__buf_1')
        self.regions=[];self.writes=[]
        block=types.SimpleNamespace(getDbUnitsPerMicron=lambda:1000,getInsts=lambda:list(self.inst.values()),getRegions=lambda:self.regions,
            getCoreArea=lambda:Box(10000,10000,210000,210000),getRows=lambda:[types.SimpleNamespace(getBBox=lambda:Box(10000,10000,210000,210000))])
        db=types.SimpleNamespace(getChip=lambda:types.SimpleNamespace(getBlock=lambda:block))
        def region_create(block,name):
            result=types.SimpleNamespace(getName=lambda:name,setRegionType=lambda value:None)
            self.regions.append(result);return result
        def group_create(region,name):
            result=types.SimpleNamespace(getName=lambda:name,getRegion=lambda:region)
            result.addInst=lambda inst:setattr(inst,'group',result)
            return result
        self.odb=types.SimpleNamespace(dbDatabase=types.SimpleNamespace(create=lambda:db),read_db=lambda *args:None,
            write_db=lambda *args:self.writes.append(('ODB',args[1])),write_def=lambda *args:self.writes.append(('DEF',args[1])),
            dbRegion_create=region_create,dbBox_create=lambda *args:None,dbGroup_create=group_create)
        with patch.dict(sys.modules,{'block_layout_runtime':v2}):self.flow=runpy.run_path(str(ROOT/'scripts/block_region_flow_v2.py'))

    def operation(self,mode):
        env={'HULLCIRQ_BLOCK_ROOT':str(self.folder),'HULLCIRQ_BLOCK_OPERATION':mode,'HULLCIRQ_BLOCK_ODB_IN':'stub-input.odb',
             'HULLCIRQ_BLOCK_ODB_OUT':'stub-output.odb','HULLCIRQ_BLOCK_DEF_OUT':'stub-output.def'}
        with patch.dict(sys.modules,{'odb':self.odb}),patch.dict(os.environ,env):self.flow['odb_operation']()

    def test_actual_flow_body_apply_verify_uses_same_exact_name_pairs(self):
        self.operation('apply')
        cap=json.loads((self.folder/'block-region-capacity.json').read_text());v2.validate_capacity(self.ownership,cap)
        self.operation('verify')
        proof=json.loads((self.folder/'block-placement-proof.json').read_text());v2.validate_placement(self.ownership,proof)
        v2.validate_def_binding(self.def_text(proof),self.ownership,proof)
        self.assertEqual(proof['unclaimed_final_cells'],['inserted_support'])
        self.assertEqual(len(proof['cells']),12);self.assertEqual(len(self.writes),4)
        self.assertTrue(all(c['odb_name']==v2.source_to_odb_name(c['source_name']) for c in proof['cells']))

    def test_flow_missing_original_leaf_never_falls_back_or_invents_ownership(self):
        self.operation('apply');name=next(n for n in self.inst if '\\[' in n);self.inst.pop(name)
        with self.assertRaises(DomainError):self.operation('verify')
        self.assertFalse((self.folder/'block-placement-proof.json').exists())

    def test_flow_wrong_region_object_or_tie_flag_is_not_a_pass(self):
        self.operation('apply');inst=next(iter(self.inst.values()))
        inst.group=types.SimpleNamespace(getName=lambda:'hullcirq_pe00',getRegion=lambda:types.SimpleNamespace(getName=lambda:'wrong_region'))
        with self.assertRaises(DomainError):self.operation('verify')
        self.assertFalse((self.folder/'block-placement-proof.json').exists())


if __name__=='__main__':unittest.main()
