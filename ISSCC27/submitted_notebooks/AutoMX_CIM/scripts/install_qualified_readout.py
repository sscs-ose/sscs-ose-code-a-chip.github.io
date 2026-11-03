"""Install electrically qualified source/IP views into an isolated validation tree."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,shutil

def install(root,destination,hardening,pwm,electrical,rtl_checks):
    root=Path(root).resolve();destination=Path(destination).resolve()
    assert destination!=root,'Validate separately before replacing the verified release'
    def read(path):return json.loads(Path(path).read_text())
    block=read(hardening);pulse=read(pwm);native=read(electrical);rtl=read(rtl_checks)
    assert block['status']=='PASS' and block['setup_slack_ns']>=0 and block['hold_slack_ns']>=0
    assert block['routed_drc_violations']==0 and block['power_rails']=={'VPWR':'PASS','VGND':'PASS'}
    assert rtl['status']=='PASS' and rtl['cases']==98304
    assert len(pulse['measurements'])==64
    for check in ('zero_code_ok','nonzero_full_swing','single_pulse_ok','unselected_lines_quiet','strict_width_order','strict_bitline_order','bitline_polarity_ok'):
        assert pulse[check],('Pulse contract failed',check)
    assert native['status']=='PASS' and native['logical_conversions']==384 and len(native['frames'])==6
    assert native['partial_decode_mismatches']==native['nominal_matched_sum_wrong']==0
    assert all(f['output_mismatches']==0 for f in native['frames'])
    assert native['contract']['stimulus']=='routed measured PWM'
    for label,key in [('readout.v','mapped_netlist'),('child.spef','spef')]:
        assert (Path(pwm).parent/'declared_inputs'/label).read_bytes()==Path(block[key]).read_bytes(),('Pulse source/view mismatch',label)
    assert Path(block['source']).read_bytes()==(Path(rtl_checks).parent/rtl['readout_source_snapshot']).read_bytes()
    assert (destination/'validation_bundle.json').is_file()
    backup=destination/'experiments/closure_20261028/preinstall';backup.mkdir(parents=True,exist_ok=False)
    for name in ('rtl/automx_cim_readout_seq.sv','ip/automx_mha/rtl/automx_cim_readout_seq.sv','inputs/digital_blocks/source_library.json'):
        path=backup/name;path.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(destination/name,path)
    shutil.copytree(destination/'inputs/digital_blocks/readout',backup/'readout')
    library=destination/'inputs/digital_blocks';view=dict(block)
    view.pop('log',None)
    for key in ('source','gds','lef','odb','lib','mapped_netlist','spef'):
        source=Path(block[key]);name='source.sv' if key=='source' else source.name
        target=library/'readout'/name;shutil.copy2(source,target);view[key]=str(Path('readout')/name)
    import re
    config=Path(block['source']).parent/'design/runs/hard/config.tcl'
    match=re.search(r'^set ::env\(CURRENT_SDC\) "([^\n]*)"$',config.read_text(),re.M)
    assert match,'The actual child CTS constraints are required for the ICG timing audit'
    shutil.copy2(Path(match[1]),library/'readout/child.sdc')
    view['cts_constraints']='readout/child.sdc'
    view['layout_config']={'width':1250,'height':750,'density':.4}
    for name in ('rtl/automx_cim_readout_seq.sv','ip/automx_mha/rtl/automx_cim_readout_seq.sv'):
        shutil.copy2(Path(block['source']),destination/name)
    index=read(library/'source_library.json');index['created_utc']=datetime.now(timezone.utc).isoformat()
    index['blocks']=[view if b['name']=='readout' else b for b in index['blocks']]
    index['note']='Electrically qualified routed pulse construction and calibration ICG; source-matched physical IP. Fresh parent pulse qualification is repeated by Full Run All.'
    (library/'source_library.json').write_text(json.dumps(index,indent=2)+'\n')
    for b in index['blocks']:
        assert (library/b['source']).read_bytes()==(destination/('rtl/automx_cim_readout_seq.sv' if b['name']=='readout' else 'ip/automx_mha/rtl/automx_mha_ip.sv')).read_bytes()
        for key in ('source','gds','lef','odb','lib','mapped_netlist','spef'):
            assert not Path(b[key]).is_absolute() and (library/b[key]).is_file()
    manifest=read(destination/'validation_bundle.json');manifest.update(candidate_views_installed=True,existing_run_outputs_copied=False,declared_reference_fixtures_included=True)
    manifest.pop('existing_measurement_outputs_copied',None)
    (destination/'validation_bundle.json').write_text(json.dumps(manifest,indent=2)+'\n')
    receipt={'status':'INSTALLED_FOR_FRESH_VALIDATION','installed_utc':datetime.now(timezone.utc).isoformat(),
        'root':str(destination),'canonical_release_changed':False,'qualification':{k:str(Path(v).resolve()) for k,v in [('hardening',hardening),('pulse',pwm),('native',electrical),('rtl',rtl_checks)]},
        'scope':'Source-matched reusable child IP installed after nominal electrical checks; a fresh complete notebook/parent route is still required before publication.'}
    (destination/'experiments/closure_20261028/installation.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print('READOUT_INSTALLED_FOR_VALIDATION',destination,flush=True);return receipt

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    for name in ('destination','hardening','pwm','electrical','rtl-checks'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();install(args.root,args.destination,args.hardening,args.pwm,args.electrical,args.rtl_checks)
