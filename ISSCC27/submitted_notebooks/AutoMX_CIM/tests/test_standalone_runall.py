"""Cold-start and dependency-isolation contracts for the portable laboratory."""
from pathlib import Path
import json,subprocess,sys,types,time,io
import pytest
from scripts import standalone_runtime as runtime

def bundle(tmp_path):
    root=tmp_path/'bundle';(root/'inputs').mkdir(parents=True)
    (root/'inputs/openlane_config_template.json').write_text(json.dumps({'DESIGN_NAME':runtime.TOP}))
    (root/'inputs/pdn_mixed_wrapper.tcl').write_text('source [file join [file dirname [info script]] repair_wrapper_ground.tcl]\n')
    (root/'inputs/repair_wrapper_ground.tcl').write_text('odb::dbSBox_create [lindex $swires 0] $layer {*}$rectangle STRIPE\n')
    (root/'scripts').mkdir();(root/'scripts/flow2_chip_pg_check.py').write_text('# worker source\n')
    (root/'standalone.json').write_text(json.dumps({'openlane_image':'example/openlane:test'}))
    return root

def test_container_has_no_external_checkout_or_home_mount(tmp_path):
    root=bundle(tmp_path)
    command=runtime.container(root,'openroad',['-version'],'cold-test',root/'work')
    mounts=[command[i+1] for i,v in enumerate(command) if v=='-v']
    assert mounts==[str(root.resolve())+':'+str(root.resolve()),str(root.resolve()/'tools/openlane')+':/openlane']
    assert command[command.index('--network')+1]=='none'
    assert 'PWD='+str(root/'work') in command
    assert not any(str(Path.home())+':'+str(Path.home())==m for m in mounts)

def test_cold_preparation_preserves_prior_attempt_and_fixes_pdn_source(tmp_path):
    root=bundle(tmp_path);work=tmp_path/'new_run'
    first,config=runtime.prepare_pnr(root,work)
    marker=first/'native-result';marker.write_text('first attempt remains intact')
    second,again=runtime.prepare_pnr(root,work)
    assert second!=first and marker.read_text()=='first attempt remains intact'
    assert 'source {'+str(first/'repair_wrapper_ground.tcl')+'}' in Path(config['FP_PDN_CFG']).read_text()
    assert 'STRIPE 1' in (first/'repair_wrapper_ground.tcl').read_text()
    for values in [config['VERILOG_FILES'],config['EXTRA_LEFS'],config['EXTRA_GDS_FILES']]:
        assert all(Path(p).is_relative_to(root) for p in values)
    assert 'CURRENT_ODB' not in config and 'resume' not in json.dumps(config).lower()

def test_moved_bundle_rebases_pdk_configuration_and_model_path(tmp_path):
    root=bundle(tmp_path);target=root/'pdks/digital/sky130A/libs.tech/test.tcl';target.parent.mkdir(parents=True)
    target.write_text('source {/old/bundle/pdks/digital/sky130A/model.tcl}\n')
    (root/'relocated_configuration.json').write_text(json.dumps([str(target.relative_to(root))]))
    (root/'standalone.json').write_text(json.dumps({'assembled_root':'/old/bundle'}))
    runtime.relocate_bundle(root)
    assert '/old/bundle' not in target.read_text()
    model=json.loads((root/'generated/sky130/spice/stage4_manifest.json').read_text())['model_library']
    assert Path(model).is_relative_to(root)

def test_guard_rejects_actual_old_input_reads_without_rejecting_new_bundle(tmp_path):
    root=bundle(tmp_path);old=tmp_path/'old_checkout';old.mkdir();(old/'netlist').write_text('old')
    (root/'new_input').write_text('new')
    (root/'standalone.json').write_text(json.dumps({'forbidden_roots':[str(old)]}))
    script='from scripts.standalone_runtime import guard_old_checkout\nfrom pathlib import Path\nguard_old_checkout('+repr(str(root))+')\nassert Path('+repr(str(root/'new_input'))+').read_text()=="new"\ntry:Path('+repr(str(old/'netlist'))+').read_text()\nexcept PermissionError:print("BLOCKED_OLD_INPUT")\nelse:raise AssertionError("old data were readable")\n'
    result=subprocess.run([sys.executable,'-c',script],text=True,capture_output=True)
    assert result.returncode==0,result.stderr
    assert 'BLOCKED_OLD_INPUT' in result.stdout

def stub_support(monkeypatch):
    package=types.ModuleType('automx_nb_inline_v1');package.__path__=[]
    support=types.ModuleType('automx_nb_inline_v1.support')
    support.item=lambda p:{'path':str(p)}
    monkeypatch.setitem(sys.modules,'automx_nb_inline_v1',package)
    monkeypatch.setitem(sys.modules,'automx_nb_inline_v1.support',support)

def test_printed_psm_error_cannot_become_pass_even_with_success_markers(tmp_path,monkeypatch):
    stub_support(monkeypatch);root=bundle(tmp_path);work=tmp_path/'active';work.mkdir()
    log=work/'power.native.log'
    log.write_text('[ERROR PSM-0069] Check connectivity failed.\nSTANDALONE_VPWR_CONNECTED\nSTANDALONE_VGND_CONNECTED\n')
    monkeypatch.setattr(runtime,'inputs',lambda flow:({}, {'odb':work/'new.odb'},None,None,None,root/'pdks/digital/sky130A'))
    class Flow:
        def run(self,*args,**kwargs):return {'returncode':0,'log':{'path':str(log)}}
    flow=Flow();flow.work=work;flow.root=root;flow.outputs={}
    with pytest.raises(ValueError,match='Actual supply connectivity failed'):runtime.power(flow)
    assert 'power' not in flow.outputs

def test_partial_top_after_failed_pnr_is_not_accepted(tmp_path,monkeypatch):
    stub_support(monkeypatch);root=bundle(tmp_path);work=tmp_path/'active';work.mkdir()
    design=work/'cold/design';design.mkdir(parents=True);log=design.parent/'native.log';log.write_text('Flow failed; partial views saved\n')
    class Failed:
        returncode=1
        def poll(self):return 1
    monkeypatch.setattr(runtime,'PNR',{'process':Failed(),'stream':io.BytesIO(),'log':log,'started':time.monotonic(),
         'command':['docker','run'],'design':design,'name':'test-failed'})
    monkeypatch.setattr(runtime,'WORK',work)
    class Flow:receipts={};outputs={}
    flow=Flow()
    with pytest.raises(RuntimeError,match='Cold OpenLane failed'):runtime.wait_pnr(flow)
    assert json.loads((design.parent/'step.json').read_text())['returncode']==1
    assert 'mapped_synthesis' not in flow.outputs

def test_only_unused_duplicate_pg_labels_are_removed():
    text=f'.subckt {runtime.TOP} VPWR VGND signal VPWR_uq0 VGND_uq0\nXcore signal VPWR VGND macro\n.ends\n'
    normalized,removed=runtime.remove_dangling_power_ports(text)
    assert removed==['VPWR_uq0','VGND_uq0']
    assert 'Xcore signal VPWR VGND macro' in normalized
    assert ' signal ' in normalized and '_uq' not in normalized
    connected=text.replace('Xcore signal VPWR VGND','Xcore signal VPWR_uq0 VGND')
    with pytest.raises(ValueError,match='Duplicated PG port is connected'):
        runtime.remove_dangling_power_ports(connected)

def test_power_label_normalization_does_not_erase_a_signal_short():
    text=f'.subckt {runtime.TOP} VPWR VGND signal VPWR_uq0 VGND_uq0\nXbad VGND output buffer\nXload VGND input flop\n.ends\n'
    normalized,_=runtime.remove_dangling_power_ports(text)
    assert 'Xbad VGND output buffer' in normalized and 'Xload VGND input flop' in normalized
