"""Synchronize mutable sources and adopt only the independently checked ICG IP."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,os,shutil

def prepare(root,destination):
    root=Path(root).resolve();destination=Path(destination).resolve()
    assert destination!=root and (destination/'validation_bundle.json').is_file()
    assert not list((destination/'runs').glob('fresh_*')),'Use an empty validation tree'
    def read(path):return json.loads(Path(path).read_text())
    work=root/'experiments/closure_20261028'
    hard=read(work/'gated_physical/readout/hardening.json')
    rtl=read(work/'gated_rtl/verification.json')
    power=read(work/'clock_aware_power/verification.json')
    native=read(work/'schematic_timing/verification.json')
    assert hard['status']=='PASS' and hard['routed_drc_violations']==0
    assert hard['setup_slack_ns']>=0 and hard['hold_slack_ns']>=0
    assert hard['power_rails']=={'VPWR':'PASS','VGND':'PASS'}
    assert rtl['status']=='PASS' and rtl['cases']==98304
    assert power['status']=='PASS' and power['gating_child_energy_reduction_percent']>15
    assert native['status']=='PASS' and native['logical_conversions']==384
    source=Path(hard['source'])
    assert source.read_bytes()==(root/'inputs/digital_benchmarks/calibration_gated/source.sv').read_bytes()
    original_manifest=read(destination/'standalone.json')
    mutable=('automx_cim','ip','inputs','configs','rtl','scripts','licenses','physical','generated','tests','docs')
    for name in mutable:
        target=destination/name
        if target.exists():shutil.rmtree(target)
        if (root/name).is_dir():shutil.copytree(root/name,target,symlinks=True,ignore=shutil.ignore_patterns('__pycache__'))
    for name in ('README.md','NOTICE.md','LICENSE','TEAM.json','standalone.json','relocated_configuration.json','requirements.txt','environment.yml','execute_standalone.py','run_all.sh','run_notebook.sh','spice_dependency_audit.json','AutoMX_CIM_Code_a_Chip.ipynb'):
        if (destination/name).is_symlink():(destination/name).unlink()
        shutil.copy2(root/name,destination/name)
    manifest=read(destination/'standalone.json')
    manifest['forbidden_roots']=list(dict.fromkeys([*original_manifest.get('forbidden_roots',[]),*manifest.get('forbidden_roots',[]),str(root)]))
    (destination/'standalone.json').write_text(json.dumps(manifest,indent=2)+'\n')
    for relative in read(destination/'relocated_configuration.json'):
        target=destination/relative;data=target.read_bytes();target.unlink();target.write_bytes(data)
    for name in (*mutable,'tools','pdks','third_party','data'):
        for p in (destination/name).rglob('*'):
            if p.is_symlink():
                target=os.readlink(p)
                if target.startswith(str(root)+'/'):
                    p.unlink();p.symlink_to(str(destination)+target[len(str(root)):])
    library=destination/'inputs/digital_blocks';view=dict(hard);view.pop('log',None)
    shutil.rmtree(library/'readout');(library/'readout').mkdir()
    for key in ('source','gds','lef','odb','lib','mapped_netlist','spef'):
        original=Path(hard[key]);name='source.sv' if key=='source' else original.name
        target=library/'readout'/name;shutil.copy2(original,target);view[key]=str(Path('readout')/name)
    view['layout_config']={'width':1250,'height':750,'density':.4}
    for name in ('rtl/automx_cim_readout_seq.sv','ip/automx_mha/rtl/automx_cim_readout_seq.sv'):shutil.copy2(source,destination/name)
    index=read(library/'source_library.json');index['created_utc']=datetime.now(timezone.utc).isoformat()
    index['blocks']=[view if b['name']=='readout' else b for b in index['blocks']]
    index['note']='Isolated calibration-data ICG; source-matched routed IP. Pulse delivery and ideal-stimulus native conversion are distinct measured profiles.'
    (library/'source_library.json').write_text(json.dumps(index,indent=2)+'\n')
    report=read(destination/'validation_bundle.json')
    report.update(candidate_views_installed=True,installed_variant='isolated calibration clock gating',existing_run_outputs_copied=False,
        qualification={'rtl_cases':98304,'routed_drc':0,'setup_ns':hard['setup_slack_ns'],'hold_ns':hard['hold_slack_ns'],
        'matched_child_energy_reduction_percent':power['gating_child_energy_reduction_percent'],
        'native_stimulus':native['contract']['stimulus'],'native_frames':6},
        publication_status='NOT_EXECUTED_NOT_PUBLISHED',electrical_profile='timing-aligned ideal-50-ps native partition; routed pulse measured separately')
    (destination/'validation_bundle.json').write_text(json.dumps(report,indent=2)+'\n')
    print('MEASURED_PROTOTYPE_VALIDATION_PREPARED',destination,flush=True)
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--destination',type=Path,required=True)
    a=p.parse_args();prepare(a.root,a.destination)
