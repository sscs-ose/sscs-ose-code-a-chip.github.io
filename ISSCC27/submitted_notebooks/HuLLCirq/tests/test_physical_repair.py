"""Software fixtures for bounded route repair; no EDA or live history writes."""
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
from hullcirq.physical_tools import metric_checks,configuration_projection,fixed_commands,sha
from hullcirq import physical_repair as repair
from hullcirq.verification import object_hash,content_hash,_wsl_path
from hullcirq.global_workflow import source_bundle
import test_physical_tools as original_qa


class RepairTests(unittest.TestCase):
    def setUp(self):
        base=original_qa.PhysicalToolTests();base.setUp()
        self.metrics=base.metrics;self.config=base.config;self.settings=base.settings
        self.config['profile']=json.loads((ROOT/'configs/physical_profile_sky130_repair_v2.json').read_text(encoding='utf-8'))
        self.config['pdk_root']=str(ROOT/'.work/fixture/pdks')
        self.config['resume']={'initial_state_path':str(ROOT/'.work/fixture/state.json'),'initial_state_sha256':repair.STATE_SHA,
            'source_input_manifest_path':str(ROOT/'.work/fixture/input-manifest.json'),'source_input_manifest_sha256':repair.INPUT_SHA,'from_step':repair.START_STEP}

    def test_new_profile_preserves_constraints_and_enables_standard_repair(self):
        old=json.loads((ROOT/'configs/physical_profile_sky130.json').read_text(encoding='utf-8'))['config']
        expected={**old,'RUN_POST_GRT_DESIGN_REPAIR':True,'RUN_POST_GRT_RESIZER_TIMING':True,'CTS_SINK_CLUSTERING_SIZE':8}
        self.assertEqual(self.config['profile']['config'],expected)
        output=configuration_projection(self.settings,self.config)
        self.assertEqual(output['CLOCK_PERIOD'],50)
        self.assertEqual(output['IO_DELAY_CONSTRAINT'],20.0)

    def test_resume_uses_new_folder_and_fixed_start(self):
        folder=Path(self.config['working_directory'])/'hullcirq-layout-fixture'
        command=fixed_commands(self.config,folder)[1]
        self.assertIn('--with-initial-state',command)
        self.assertIn(_wsl_path(folder/'resume-state.json'),command)
        self.assertEqual(command[command.index('--from')+1],'OpenROAD.CTS')
        self.assertNotIn('--overwrite',command)

    def test_v3_adds_only_fixed_clock_buffer_distance(self):
        config=copy.deepcopy(self.config)
        config['profile']=json.loads((ROOT/'configs/physical_profile_sky130_repair_v3.json').read_text(encoding='utf-8'))
        self.assertEqual(config['profile']['config'],{**self.config['profile']['config'],'CTS_DISTANCE_BETWEEN_BUFFERS':50})
        projected=configuration_projection(self.settings,config)
        self.assertEqual(projected['CTS_DISTANCE_BETWEEN_BUFFERS'],50)
        self.assertEqual(projected['CLOCK_PERIOD'],50)
        self.assertEqual(projected['CLOCK_UNCERTAINTY_CONSTRAINT'],.25)

    def test_v4_uses_stricter_pnr_target_and_unchanged_nine_corner_signoff(self):
        config=copy.deepcopy(self.config)
        config['profile']=json.loads((ROOT/'configs/physical_profile_sky130_repair_v4.json').read_text(encoding='utf-8'))
        projected=configuration_projection(self.settings,config)
        self.assertEqual(projected['PNR_CORNERS'],['max_ss_100C_1v60'])
        self.assertEqual(projected['RSZ_CORNERS'],['max_ss_100C_1v60'])
        self.assertEqual(projected['STA_CORNERS'],self.config['profile']['config']['STA_CORNERS'])
        self.assertEqual(projected['GRT_DESIGN_REPAIR_MAX_SLEW_PCT'],30)
        self.assertEqual(projected['GRT_DESIGN_REPAIR_MAX_CAP_PCT'],30)
        self.assertEqual(projected['PNR_SDC_FILE'],'dir::physical_pnr.sdc')
        self.assertEqual(projected['SIGNOFF_SDC_FILE'],'dir::physical.sdc')
        original=b'# SOFTWARE QA original SDC\nset_max_fanout 10 [current_design]\n'
        derived=repair.pnr_sdc(original)
        self.assertTrue(derived.startswith(original))
        self.assertTrue(derived.endswith(b'set_max_fanout 8 [current_design]\n'))
        self.assertEqual(projected['CLOCK_PERIOD'],50)
        self.assertEqual(projected['DEFAULT_CORNER'],'nom_tt_025C_1v80')

    def test_v5_repeats_repair_at_its_fixed_postgrt_checkpoint_only(self):
        config=copy.deepcopy(self.config)
        config['profile']=json.loads((ROOT/'configs/physical_profile_sky130_repair_v5.json').read_text(encoding='utf-8'))
        config['resume'].update(initial_state_sha256=repair.V5_STATE_SHA,
            source_input_manifest_sha256=repair.V5_INPUT_SHA,from_step='OpenROAD.RepairDesignPostGRT')
        projected=configuration_projection(self.settings,config)
        self.assertEqual(projected['PNR_SDC_FILE'],'dir::physical_pnr.sdc')
        self.assertEqual(projected['SIGNOFF_SDC_FILE'],'dir::physical.sdc')
        self.assertEqual(repair.implementation_kind(config),'resumed_post_GRT_route_repair')
        command=fixed_commands(config,Path(config['working_directory'])/'hullcirq-layout-fixture')[1]
        self.assertEqual(command[command.index('--from')+1],'OpenROAD.RepairDesignPostGRT')
        self.assertEqual(command[command.index('--flow')+1],'HuLLCirqRouteClosureV5')
        self.assertIn(_wsl_path(Path(config['working_directory'])/'hullcirq-layout-fixture/route_closure_v5.py'),command)
        self.assertEqual(sha(ROOT/'scripts/route_closure_v5.py'),repair.V5_LAUNCHER_SHA)
        config['resume']['initial_state_sha256']=repair.STATE_SHA
        with self.assertRaises(DomainError):configuration_projection(self.settings,config)

    def test_v6_adds_estimation_headroom_without_changing_signoff(self):
        config=copy.deepcopy(self.config)
        config['profile']=json.loads((ROOT/'configs/physical_profile_sky130_repair_v6.json').read_text(encoding='utf-8'))
        previous=json.loads((ROOT/'configs/physical_profile_sky130_repair_v5.json').read_text(encoding='utf-8'))
        self.assertEqual(config['profile']['config'],{**previous['config'],
            'GRT_DESIGN_REPAIR_MAX_SLEW_PCT':60,'GRT_RESIZER_HOLD_SLACK_MARGIN':.10})
        config['resume'].update(initial_state_sha256=repair.V6_STATE_SHA,
            source_input_manifest_sha256=repair.V6_INPUT_SHA,from_step='OpenROAD.RepairDesignPostGRT')
        projected=configuration_projection(self.settings,config)
        self.assertEqual(projected['SIGNOFF_SDC_FILE'],'dir::physical.sdc')
        self.assertEqual(projected['STA_CORNERS'],previous['config']['STA_CORNERS'])
        self.assertEqual(projected['CLOCK_PERIOD'],50)
        self.assertEqual(config['profile']['fixed_launcher_sha256'],repair.V5_LAUNCHER_SHA)
        self.assertEqual(repair.implementation_kind(config),'resumed_post_GRT_route_repair')
        config['resume']['initial_state_sha256']=repair.V5_STATE_SHA
        with self.assertRaises(DomainError):configuration_projection(self.settings,config)

    def test_unknown_checkpoint_or_start_cannot_be_substituted(self):
        for key,value in [('initial_state_sha256','0'*64),('source_input_manifest_sha256','0'*64),('from_step','KLayout.Render')]:
            changed=copy.deepcopy(self.config);changed['resume'][key]=value
            with self.subTest(key=key),self.assertRaises(DomainError):configuration_projection(self.settings,changed)

    def test_electrical_violations_block_new_profile_only(self):
        for field in ('design__max_slew_violation__count','design__max_cap_violation__count','design__max_fanout_violation__count'):
            values={**self.metrics,'design__max_slew_violation__count':0,'design__max_cap_violation__count':0,'design__max_fanout_violation__count':0,field:1}
            self.assertEqual(metric_checks(values,True)['electrical']['validation_status'],'Failed')
            self.assertNotIn('electrical',metric_checks(values))

    def test_missing_or_untyped_electrical_count_rejected(self):
        for value in (None,False,0.0,-1,'0'):
            values={**self.metrics,'design__max_slew_violation__count':value,'design__max_cap_violation__count':0}
            with self.subTest(value=value),self.assertRaises(DomainError):metric_checks(values,True)

    def test_checkpoint_copy_preserves_bytes_and_detects_edit(self):
        rtl='module fixture; endmodule\n';manifest={'nodes':[]}
        with tempfile.TemporaryDirectory() as temporary:
            base=Path(temporary);source=base/'source';source.mkdir();destination=base/'result';destination.mkdir()
            view=source/'design.odb';view.write_bytes(b'fixture checkpoint bytes')
            state=source/'state.json';state.write_text(json.dumps({'odb':_wsl_path(view),'metrics':{'tool_value':float('inf')}}),encoding='utf-8')
            inputs=source/'input-manifest.json';inputs.write_text(json.dumps({'settings':self.settings,'global_rtl_sha256':content_hash(rtl),
                'source_manifest_sha256':object_hash(manifest),'source_bundle':{'software_fixture':True}}),encoding='utf-8')
            config=copy.deepcopy(self.config);config['resume'].update(initial_state_path=str(state),initial_state_sha256=sha(state),
                source_input_manifest_path=str(inputs),source_input_manifest_sha256=sha(inputs))
            with patch.object(repair,'STATE_SHA',sha(state)),patch.object(repair,'INPUT_SHA',sha(inputs)),patch('hullcirq.global_workflow.source_bundle',return_value={'software_fixture':True}):
                repair.snapshot_resume(config,destination,rtl,manifest,self.settings)
                self.assertEqual(view.read_bytes(),(destination/'resume-files/design.odb').read_bytes())
                repair.validate_resume(config,destination,rtl,manifest,self.settings)
                (destination/'resume-files/design.odb').write_bytes(b'changed')
                with self.assertRaises(DomainError):repair.validate_resume(config,destination,rtl,manifest,self.settings)


if __name__=='__main__':unittest.main()
