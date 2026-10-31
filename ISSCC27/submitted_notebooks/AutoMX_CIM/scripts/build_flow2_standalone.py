"""Assemble an independent on-disk laboratory with source IP, PDK and tools."""
from pathlib import Path
from datetime import datetime,timezone
import ast,copy,json,os,shutil,sys,subprocess
import nbformat as nbf

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
DEST=Path('/media/nam/EDABK/AutoMX_CIM_standalone_20261024')
REVIEW=ROOT/'submission/ISSCC27/submitted_notebooks/automx_cim'

def copy_tree(source,target):
    print('COPY',source,'->',target,flush=True)
    shutil.copytree(source,target,symlinks=False,ignore=shutil.ignore_patterns('__pycache__','.git','.pytest_cache'),dirs_exist_ok=True)

def assemble(dest=DEST):
    dest=Path(dest);dest.mkdir(parents=True,exist_ok=True)
    if (dest/'runs').exists() and any((dest/'runs').iterdir()):
        raise FileExistsError('Preserve completed runs; do not rebuild an occupied standalone laboratory')
    for folder in ('scripts','automx_cim','rtl','configs','ip'):
        copy_tree(ROOT/folder,dest/folder)
    copy_tree(ROOT/'third_party/SKY130_SAR_ADC1/mixed_signal_partition',dest/'third_party/SKY130_SAR_ADC1/mixed_signal_partition')
    for name in ('LICENSE','NOTICE.md','TEAM.json','requirements.txt','environment.yml'):
        if (REVIEW/name).is_file():shutil.copyfile(REVIEW/name,dest/name)
    copy_tree(REVIEW/'licenses',dest/'licenses')
    copy_tree(Path('/home/nam/dependencies/openlane_src'),dest/'tools/openlane')
    analog=Path('/home/nam/.volare/volare/sky130/versions/bdc9412b3e468c102d01b7cf6337be06ec6e9c9a/sky130A')
    digital=Path('/home/nam/.volare_openlane_30ee138_nam/sky130A').resolve()
    copy_tree(analog,dest/'pdks/analog/sky130A')
    copy_tree(digital,dest/'pdks/digital/sky130A')
    lib=dest/'tools/ngspice/libngspice.so';lib.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile('/media/nam/EDABK/AutoMX_CIM_tools/ngspice_shared44/libngspice.so',lib)
    netgen=ROOT/'build/flow2_wrapper_integration/netgen_tool_srv_20261022_01/install'
    copy_tree(netgen,dest/'tools/netgen')
    shutil.copyfile(netgen.parent/'source/Copying',dest/'tools/netgen/Copying')
    script=dest/'tools/netgen/lib/netgen/tcl/netgen.tcl'
    script.write_text(script.read_text().replace('load '+str(netgen/'lib/netgen/tcl/tclnetgen.so'),
        'load [file join [file dirname [info script]] tclnetgen.so]'))
    launcher=dest/'tools/netgen/bin/netgen'
    launcher.write_text('#!/usr/bin/env bash\nset -euo pipefail\nexec tclsh "$(dirname -- "$0")/../lib/netgen/tcl/netgen.tcl" "$@"\n')
    launcher.chmod(0o755)
    ip=dest/'third_party/SKY130_SAR_ADC1';shutil.copyfile(ROOT/'third_party/SKY130_SAR_ADC1/LICENSE',ip/'LICENSE')
    design=ROOT/'build/flow2_wrapper_integration/mixed_wrapper_srv_20261022_04_impl_gds/design'
    config=json.loads((design/'config.json').read_text());assets=dest/'inputs';assets.mkdir(exist_ok=True)
    digital_library=ROOT/'physical/sky130/digital_blocks'
    if digital_library.is_dir():copy_tree(digital_library,assets/'digital_blocks')
    names=['core','conditioner','adc']
    for kind,key in [('gds','EXTRA_GDS_FILES'),('lef','EXTRA_LEFS')]:
        for name,p in zip(names,config[key]):shutil.copyfile(p,assets/(name+'.'+kind))
    for name in ('automx_cim_mixed_signal_proto.sv','wrapper_blackboxes.sv','macro_placement.cfg'):
        shutil.copyfile(design/name,assets/name)
    shutil.copyfile(ROOT/'ip/automx_mha/rtl/automx_cim_mixed_signal_proto.sv',assets/'automx_cim_mixed_signal_proto.sv')
    for name in ('pdn_mixed_wrapper.tcl','repair_wrapper_ground.tcl'):
        shutil.copyfile(ROOT/'physical/sky130/wrapper_prototype'/name,assets/name)
    from scripts.run_flow2_core_tap_transient import source
    from scripts import flow2_integration_common as common
    _,data,views=source(ROOT,'core_tap_pex_srv_20261022_01')
    shutil.copyfile(views['schematic'],assets/'core_acquisition.spice')
    shutil.copyfile(views['pex'],assets/'core_acquisition.pex.spice')
    condition=json.loads((ROOT/common.BASE/'mixed_wrapper_20261020_01_cond/summary.json').read_text())
    condition=condition.get('block',condition)
    shutil.copyfile(common._verified(ROOT,condition['views']['schematic']),assets/'conditioner.spice')
    pex=dest/'physical/sky130/macro';pex.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(ROOT/'physical/sky130/macro/automx_ternary_cim_4x4_core.pex.spice',pex/'automx_ternary_cim_4x4_core.pex.spice')
    generated=dest/'generated/sky130/spice';generated.mkdir(parents=True,exist_ok=True)
    (generated/'stage4_manifest.json').write_text(json.dumps({'model_library':str(dest/'pdks/analog/sky130A/libs.tech/ngspice/sky130.lib.spice')},indent=2)+'\n')
    # Stimuli and requested mappings only; no old codes, voltages, waves or top checkpoint.
    old=json.loads((REVIEW/'data/evidence.json').read_text())
    spec={'cases':[], 'calibration_ids':old['calibration_ids'],'mha':{k:v for k,v in old['mha'].items() if k!='recorded_output'}}
    for row in old['cases']:
        payload=json.loads((REVIEW/row['stimulus']).read_text())
        spec['cases'].append({'id':row['id'],'cohort':row['cohort'],'payload':payload})
    (assets/'experiment_spec.json').write_text(json.dumps(spec,indent=2)+'\n')
    config={k:v for k,v in config.items() if k not in ('VERILOG_FILES','VERILOG_FILES_BLACKBOX','EXTRA_LEFS','EXTRA_GDS_FILES','MACRO_PLACEMENT_CFG','FP_PDN_CFG')}
    config.update(CLOCK_PERIOD=40,PL_TARGET_DENSITY=0.45,RUN_FILL_INSERTION=0,RUN_MAGIC_DRC=0,RUN_KLAYOUT_DRC=0,RUN_LVS=0,
        DRT_OPT_ITERS=32,QUIT_ON_TR_DRC=0,RUN_HEURISTIC_DIODE_INSERTION=0,
        RUN_SPEF_EXTRACTION=0,STA_WRITE_LIB=0,RUN_IRDROP_REPORT=0,
        RUN_MAGIC=0,RUN_KLAYOUT=1,RUN_KLAYOUT_XOR=0,PRIMARY_SIGNOFF_TOOL='klayout',
        PL_RESIZER_DESIGN_OPTIMIZATIONS=0,PL_RESIZER_TIMING_OPTIMIZATIONS=0,
        GLB_RESIZER_DESIGN_OPTIMIZATIONS=0,GLB_RESIZER_TIMING_OPTIMIZATIONS=0,
        CTS_SINK_CLUSTERING_SIZE=25,MAX_FANOUT_CONSTRAINT=20)
    (assets/'openlane_config_template.json').write_text(json.dumps(config,indent=2)+'\n')
    manifest={'format':'automx-standalone-v1','created_utc':datetime.now(timezone.utc).isoformat(),
        'assembled_root':str(dest.resolve()),
        'openlane_image':'efabless/openlane:30ee1388932eb55a89ad84ee43997bfe3a386421-amd64',
        'old_checkout_required':False,'routed_top_checkpoint_included':False,
        'initial_measurements_included':False,'initial_top_gds_included':False,
        'hard_macro_ip':['inputs/core.gds','inputs/conditioner.gds','inputs/adc.gds'],
        'analogue_model':'pdks/analog/sky130A','digital_pdk':'pdks/digital/sky130A',
        'pnr_profile':'cold synthesis/floorplan/place/CTS/global+detailed route; no fill; independent bounded checks',
        'forbidden_roots':[str(ROOT),'/home/nam/dependencies/openlane_src','/home/nam/.volare','/home/nam/.volare_openlane_30ee138_nam']}
    if (assets/'digital_blocks/source_library.json').is_file():
        manifest['hard_macro_ip'] += ['inputs/digital_blocks/mha/automx_mha_ip.gds','inputs/digital_blocks/readout/automx_cim_readout_seq.gds']
    (dest/'standalone.json').write_text(json.dumps(manifest,indent=2)+'\n')
    # Local PDK configuration must not retain host installation prefixes.
    replacements={str(analog):str(dest/'pdks/analog/sky130A'),str(digital):str(dest/'pdks/digital/sky130A'),
        '/home/nam/.volare_openlane_30ee138_nam':str(dest/'pdks/digital'),
        '/home/nam/dependencies/openlane_src':str(dest/'tools/openlane')}
    changed=[]
    for directory in (dest/'pdks',dest/'inputs'):
        for p in directory.rglob('*'):
            if not p.is_file() or p.stat().st_size>25_000_000 or p.suffix in ('.gds','.gz','.so','.png'):continue
            try:text=p.read_text()
            except UnicodeError:continue
            original=text
            for before,after in replacements.items():text=text.replace(before,after)
            if text!=original:p.write_text(text);changed.append(str(p.relative_to(dest)))
    (dest/'relocated_configuration.json').write_text(json.dumps(changed,indent=2)+'\n')
    # Notebook adaptation is authored separately; keep a source copy for recovery.
    seed=nbf.read(REVIEW/'AutoMX_CIM_Code_a_Chip.ipynb',4)
    for cell in seed.cells:
        if cell.cell_type=='code':cell.outputs=[];cell.execution_count=None
    nbf.write(seed,dest/'source_notebook.ipynb')
    archive=dest/'tools/openlane-image.tar'
    if not archive.is_file():
        subprocess.run(['docker','image','save','-o',str(archive),manifest['openlane_image']],check=True)
    from scripts.adapt_flow2_standalone_notebook import adapt
    adapt(dest)
    from scripts.extend_mha_ip_notebook import extend
    extend(dest)
    from scripts.extend_block_floorplan_notebook import extend as extend_block_floorplan
    extend_block_floorplan(dest)
    catalog=ROOT/'data/notebook_english.json'
    if catalog.is_file():
        (dest/'data').mkdir(exist_ok=True)
        shutil.copyfile(catalog,dest/'data/notebook_english.json')
        for name in ('notebook_editorial_policy.json','notebook_references.md'):
            source=ROOT/'data'/name
            if source.is_file():shutil.copyfile(source,dest/'data'/name)
        from scripts.notebook_english import apply as apply_english
        apply_english(dest)
    shutil.copyfile(ROOT/'scripts/standalone_readme.md',dest/'README.md')
    print('STANDALONE_INPUTS_READY',dest,flush=True)
    return dest

if __name__=='__main__':assemble()
