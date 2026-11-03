"""Freeze current sources and reusable IP into an empty independent run tree."""
from pathlib import Path
import argparse,json,shutil


def stage(root,destination,qualified_prototype,candidate_hardening,candidate_parent_drive=False):
    root=Path(root).resolve();destination=Path(destination).resolve()
    qualified_prototype=Path(qualified_prototype).resolve()
    assert root!=destination and (destination/'validation_bundle.json').is_file()
    assert not list((destination/'runs').glob('fresh_*')),'Never change inputs of a running validation'
    proof=json.loads((qualified_prototype/'experiments/closure_20261028/release_validation.json').read_text())
    assert proof['status']=='VERIFIED_MEASURED_PROTOTYPE_RELEASE'
    assert proof['main_and_executed_notebook_identical']
    for source in (root/'scripts').glob('*.py'):shutil.copy2(source,destination/'scripts'/source.name)
    for name in ('execute_standalone.py','run_all.sh','run_notebook.sh'):
        shutil.copy2(root/name,destination/name)
    for name in ('CIM_SAR_MHA_OPERATING_CONTRACT.md','MEASUREMENT_TOOLCHAIN.md','AWARD_IMPROVEMENT_PLAN_20261028.md'):
        shutil.copy2(root/'docs'/name,destination/'docs'/name)
    for name in ('rtl/automx_cim_readout_seq.sv','ip/automx_mha/rtl/automx_cim_readout_seq.sv','inputs/digital_blocks/source_library.json'):
        shutil.copy2(qualified_prototype/name,destination/name)
    for source in (qualified_prototype/'inputs/digital_blocks/readout').iterdir():
        if source.is_file():shutil.copy2(source,destination/'inputs/digital_blocks/readout'/source.name)
    fixture=destination/'inputs/electrical_candidate/readout'
    if fixture.exists():
        from datetime import datetime,timezone
        saved=destination/'experiments/closure_20261028'/('prior_candidate_inputs_'+datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f'))
        fixture.rename(saved)
    fixture.mkdir(parents=True,exist_ok=False)
    block=json.loads(Path(candidate_hardening).read_text())
    assert block['status']=='PASS' and min(block['setup_slack_ns'],block['hold_slack_ns'])>=0
    for key in ('source','gds','lef','odb','lib','mapped_netlist','spef'):
        source=Path(block[key]);name='source.sv' if key=='source' else source.name
        shutil.copy2(source,fixture/name);block[key]=name
    block.pop('log',None)
    block['parent_wordline_drive_required']=bool(candidate_parent_drive)
    block['scope']='Declared source-matched routed child IP; candidate parent, waveforms and native responses are acquired fresh. Candidate adoption requires separate electrical acceptance.'
    (fixture/'hardening.json').write_text(json.dumps(block,indent=2)+'\n')
    index=json.loads((destination/'inputs/digital_blocks/source_library.json').read_text())
    for block in index['blocks']:
        source=destination/('rtl/automx_cim_readout_seq.sv' if block['name']=='readout' else 'ip/automx_mha/rtl/automx_mha_ip.sv')
        assert source.read_bytes()==(destination/'inputs/digital_blocks'/block['source']).read_bytes()
    print('FINAL_VALIDATION_SOURCES_STAGED',destination,'no run outputs copied',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    for name in ('destination','qualified-prototype','candidate-hardening'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--candidate-parent-drive',action='store_true')
    a=p.parse_args();stage(a.root,a.destination,a.qualified_prototype,a.candidate_hardening,a.candidate_parent_drive)
