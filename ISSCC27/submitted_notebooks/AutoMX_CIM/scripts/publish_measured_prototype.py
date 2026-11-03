"""Mirror a validated independent release into the user's original entry folder."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,shutil

def publish(verified,destination):
    verified=Path(verified).resolve();destination=Path(destination).resolve()
    assert verified!=destination
    report=json.loads((verified/'experiments/closure_20261028/release_validation.json').read_text())
    assert report['status'] in ('VERIFIED_MEASURED_PROTOTYPE_RELEASE','VERIFIED_ROUTED_PARTITION_RELEASE')
    assert report['main_and_executed_notebook_identical']
    assert (verified/'AutoMX_CIM_Code_a_Chip.ipynb').read_bytes()==(verified/'AutoMX_CIM_Code_a_Chip.executed.ipynb').read_bytes()
    # These files are independently bound evidence, not copied run outputs.
    names=['README.md','AutoMX_CIM_Code_a_Chip.ipynb','AutoMX_CIM_Code_a_Chip.executed.ipynb',
        'rtl/automx_cim_readout_seq.sv','ip/automx_mha/rtl/automx_cim_readout_seq.sv',
        'ip/automx_mha/README.md','inputs/digital_blocks/source_library.json',
        'docs/CIM_SAR_MHA_OPERATING_CONTRACT.md','docs/MEASUREMENT_TOOLCHAIN.md','docs/AWARD_IMPROVEMENT_PLAN_20261028.md','execute_standalone.py','run_all.sh','run_notebook.sh']
    if (verified/'inputs/wordline_routing_policy.json').is_file():names.append('inputs/wordline_routing_policy.json')
    if (verified/'data/intermediate_notebook_cell_ids.json').is_file():names.append('data/intermediate_notebook_cell_ids.json')
    if (verified/'docs/PRIORITY_CLOSURE_RESULTS_20261029.md').is_file():names.append('docs/PRIORITY_CLOSURE_RESULTS_20261029.md')
    names += [str(p.relative_to(verified)) for p in (verified/'inputs/digital_blocks/readout').rglob('*') if p.is_file()]
    names += [str(p.relative_to(verified)) for p in (verified/'scripts').glob('*.py')]
    if (verified/'inputs/electrical_candidate').exists():
        names += [str(p.relative_to(verified)) for p in (verified/'inputs/electrical_candidate').rglob('*') if p.is_file()]
    if (verified/'inputs/earlier_pulse_placement').exists():
        names += [str(p.relative_to(verified)) for p in (verified/'inputs/earlier_pulse_placement').rglob('*') if p.is_file()]
    names += [str(p.relative_to(verified)) for p in (verified/'exports').iterdir() if p.is_file()]
    stamp=datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    backup=destination/'experiments/closure_20261028'/('before_publication_'+stamp);backup.mkdir(parents=True,exist_ok=False)
    for name in names:
        old=destination/name
        if old.is_file():
            target=backup/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(old,target)
    copied=[]
    try:
        for name in sorted(set(names)):
            source=verified/name;target=destination/name;target.parent.mkdir(parents=True,exist_ok=True)
            temp=target.with_name(target.name+'.publication_tmp');shutil.copy2(source,temp);temp.replace(target)
            copied.append(name)
        assert all((verified/n).read_bytes()==(destination/n).read_bytes() for n in copied)
    except BaseException:
        for name in copied:
            old=backup/name;target=destination/name
            if old.is_file():shutil.copy2(old,target)
            else:target.unlink(missing_ok=True)
        raise
    receipt={'status':'VERIFIED_RELEASE_MIRROR','published_utc':datetime.now(timezone.utc).isoformat(),
        'execution_root':str(verified),'entry_root':str(destination),'notebook':str(destination/'AutoMX_CIM_Code_a_Chip.ipynb'),
        'execution_receipt':str(verified/'experiments/closure_20261028/release_validation.json'),
        'fresh_run':report['fresh_run'],'mirrored_files':sorted(set(copied)),
        'source_and_artifact_byte_comparison':True,'old_run_directories_copied':False,
        'scope':report['scope'],'backup':str(backup)}
    (destination/'CURRENT_RELEASE.json').write_text(json.dumps(receipt,indent=2)+'\n')
    (destination/'LATEST_RUN.json').write_text(json.dumps({'run':report['fresh_run'],'top_gds':str(destination/'exports/AutoMX_CIM_five_block_top.gds'),
        'execution_root':str(verified),'release_validation':receipt['execution_receipt'],
        'manifest':str(Path(report['fresh_run'])/'full_native/full_native/runall_manifest.json')},indent=2)+'\n')
    print('VERIFIED_RELEASE_PUBLISHED',destination,'cells',report['total_cells'],'code',report['code_cells'],flush=True)
    return receipt

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--verified',type=Path,required=True);p.add_argument('--destination',type=Path,required=True)
    a=p.parse_args();publish(a.verified,a.destination)
