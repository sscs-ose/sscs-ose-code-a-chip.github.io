"""Historical file-copy utilities for the saved PDN seed proofs.

These helpers do NOT implement native resume: OpenLane 30ee138 prep rejects
a prepopulated run directory before it reaches the patched CURRENT_STEP.
The production GDS runner now starts a fresh native flow with verified hard
macros. Keep these utilities only to inspect/reproduce historical seed files.
"""
from pathlib import Path
import json
import re
import shutil

from scripts import flow2_integration_common as common
from scripts import flow2_wrapper_pdn as pdn


def rebase(value,old,new):
    if isinstance(value,str):return value.replace(str(old),str(new))
    if isinstance(value,list):return [rebase(v,old,new) for v in value]
    if isinstance(value,dict):return {k:rebase(v,old,new) for k,v in value.items()}
    return value


def seed(root,source_tag,target_tag,target_design,target_config,*,openlane_pdk):
    root=Path(root).resolve();target_design=Path(target_design).resolve()
    common.tag_ok(source_tag);common.tag_ok(target_tag)
    if source_tag==target_tag:raise ValueError('PDN continuation requires a fresh tag')
    if not target_design.is_relative_to(root):raise ValueError('resume destination escapes checkout')
    source_build=root/common.BUILD/source_tag
    source_design=source_build/'design';source_run=source_design/'runs'/source_tag
    target_run=target_design/'runs'/target_tag
    source_inputs=root/common.BASE/source_tag/'inputs.json'
    frozen=json.loads(source_inputs.read_text(encoding='utf-8'))
    # Only the DEF guard/parser is repaired. All circuit, geometry, splitter,
    # published view and source-receipt fingerprints remain checked.
    for item in frozen['sources']:
        if item['path']!=pdn.RECIPE.as_posix():common._verified(root,item)
    if frozen.get('openlane_pdk')!=str(openlane_pdk):
        raise ValueError('PDN continuation requires the original OpenLane PDK')
    old_conf=json.loads((source_design/'config.json').read_text(encoding='utf-8'))
    if rebase(old_conf,source_design,target_design)!=target_config:
        raise ValueError('native wrapper configuration changed; full new flow required')
    # Generated files were not all listed individually in the old source
    # snapshot. Compare their exact bytes with the regenerated new design.
    for key in ('VERILOG_FILES','VERILOG_FILES_BLACKBOX','EXTRA_LEFS','EXTRA_GDS_FILES','MACRO_PLACEMENT_CFG'):
        a,b=old_conf[key],target_config[key]
        if isinstance(a,str):a,b=[a],[b]
        if len(a)!=len(b) or any(common._sha(Path(x))!=common._sha(Path(y)) for x,y in zip(a,b)):
            raise ValueError('physical input bytes changed: '+key)
    audit=pdn.audit_pdn(source_run)
    if audit['status']!='PASS_WRAPPER_PDN_CONNECTIVITY':
        raise ValueError('native VPWR/VGND connectivity and six macro ITerms required before continuation')
    config=source_run/'config.tcl';state=config.read_text(encoding='utf-8')
    def env(name):
        m=re.search(r'(?m)^set ::env\('+re.escape(name)+r'\) "([^"\n]*)"\s*$',state)
        if not m:raise ValueError('saved OpenLane state missing '+name)
        return m[1]
    if env('CURRENT_STEP')!='placement' or env('CURRENT_INDEX')!='7':
        raise ValueError('source must be the original post-PDN floorplan checkpoint')
    top=target_config['DESIGN_NAME']
    for key,relative in (('CURRENT_ODB',f'results/floorplan/{top}.odb'),
                         ('CURRENT_DEF',f'results/floorplan/{top}.def'),
                         ('CURRENT_NETLIST',f'results/synthesis/{top}.v'),
                         ('CURRENT_SDC','tmp/floorplan/3-initial_fp.sdc')):
        if Path(env(key))!=source_run/relative:
            raise ValueError('saved state does not use the post-PDN checkpoint: '+key)
    proof_files=[source_inputs,source_design/'config.json',source_build/'flow_wrapper.tcl',config,
                 source_run/f'results/floorplan/{top}.odb',source_run/f'results/floorplan/{top}.def',
                 source_run/f'results/synthesis/{top}.v',source_run/'tmp/floorplan/3-initial_fp.sdc',
                 *sorted((source_run/'logs/floorplan').glob('*-pdn.log'))]
    proof={'source_tag':source_tag,'target_tag':target_tag,'start_step':'placement',
           'source_files':[common._item(root,p) for p in proof_files],'source_PDN':audit}
    snapshot=target_design.parent/'pdn_seed.json'
    if target_run.exists():
        if not snapshot.is_file() or json.loads(snapshot.read_text(encoding='utf-8'))!=proof:
            raise FileExistsError('different native continuation already exists; use a fresh tag')
        return proof,False
    # No hard links: subsequent OpenLane writes must never modify source data.
    shutil.copytree(source_run,target_run,symlinks=False)
    rebased=state.replace(str(source_run),str(target_run)).replace(str(source_design),str(target_design))
    rebased=rebased.replace(f'set ::env(RUN_TAG) "{source_tag}"',f'set ::env(RUN_TAG) "{target_tag}"')
    (target_run/'config.tcl').write_text(rebased,encoding='utf-8')
    common._save(snapshot,proof)
    return proof,True


def driver(text,config):
    marker='    set ::env(CURRENT_STEP) "verilator_lint_check"'
    if text.count(marker)!=1:raise ValueError('unknown pinned OpenLane start-step assignment')
    config=Path(config).as_posix()
    if any(c in config for c in '{}\n\r'):raise ValueError('unsupported saved-state path')
    return text.replace(marker,f'    source {{{config}}}\n    set ::env(CURRENT_STEP) "placement"',1)
