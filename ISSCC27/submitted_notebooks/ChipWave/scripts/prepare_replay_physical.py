#!/usr/bin/env python3
"""Prepare the same qualified physical configuration before freezing replay."""
from __future__ import annotations
import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from freeze_tool_workflow import freeze

ROOT=Path(__file__).resolve().parents[1]


def candidate_updates(core_utilization, place_density, cap_margin=None, slew_margin=None):
    if core_utilization is not None and (type(core_utilization) is not int or not 5 <= core_utilization <= 70):
        raise ValueError('core utilization must be an integer in 5..70')
    if place_density is not None and (type(place_density) not in (int, float) or not 0.30 <= place_density <= 0.80):
        raise ValueError('place density must be in 0.30..0.80')
    updates={}
    if core_utilization is not None: updates['CORE_UTILIZATION']=str(core_utilization)
    if place_density is not None: updates['PLACE_DENSITY']=f'{place_density:.2f}'
    for key,value in (('CAP_MARGIN',cap_margin),('SLEW_MARGIN',slew_margin)):
        if value is not None:
            if type(value) is not int or not 0<=value<=50:raise ValueError('repair margin must be an integer in 0..50')
            updates[key]=str(value)
    return updates


def render_configuration(original, core_utilization=None, place_density=None, cap_margin=None, slew_margin=None):
    text=original
    for key,value in candidate_updates(core_utilization,place_density,cap_margin,slew_margin).items():
        text,count=re.subn(r'^export '+key+r' = .+$','export '+key+' = '+value,text,flags=re.M)
        if count==0 and key in ('CAP_MARGIN','SLEW_MARGIN'):
            text=text.rstrip('\n')+'\nexport '+key+' = '+value+'\n';count=1
        if count!=1:raise ValueError('Expected exactly one definition of '+key)
    return text


def prepare(project, core_utilization=None, place_density=None, cap_margin=None, slew_margin=None):
    updates=candidate_updates(core_utilization,place_density,cap_margin,slew_margin)
    evidence=json.loads((ROOT/'results/physical.json').read_text())
    assert evidence['passed'] and evidence['clock_period_ns']==100 and evidence['platform']=='sky130hd'
    padding=evidence['placement_padding_sites']
    assert isinstance(padding,int) and 0<=padding<=8
    simulation='python3 scripts/run_kernels.py --project . --output build/operators'
    if not updates:simulation+=' --seeds 20260925'
    subprocess.run([sys.executable,str(ROOT/'scripts/configure_physical.py'),'--project',str(project),
        '--simulation-command',simulation],check=True)
    config=project/'physical/chip-nebula/config.mk'
    original=config.read_text()
    if updates:
        config.write_text(render_configuration(original,core_utilization,place_density,cap_margin,slew_margin))
        (project/'physical/chip-nebula/implementation-variant.json').write_text(json.dumps({
            'overrides':updates,'original_generated_config':original,
            'scope':'ORFS implementation parameters changed before workflow freeze; RTL and SDC unchanged'},indent=2)+'\n')
    if padding:
        with config.open('a') as handle:
            handle.write(f'\nexport CELL_PAD_IN_SITES_GLOBAL_PLACEMENT = {padding}\nexport CELL_PAD_IN_SITES_DETAIL_PLACEMENT = {padding}\n')
    scripts=project/'scripts';scripts.mkdir(exist_ok=True)
    for name in ('run_physical.py','run_kernels.py','kernel_programs.py'):
        shutil.copy2(ROOT/'scripts'/name,scripts/name)
    if not (project/'verification').exists():shutil.copytree(ROOT/'verification',project/'verification')
    for folder,name in [('roles','case-physical-tool.yaml'),('recipes','cpu-npu-physical.yaml')]:
        destination=project/'.chip_nebula'/folder/name;destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(ROOT/'workflows'/name,destination)
    (project/'.gitignore').write_text('.chip_nebula/\nbuild/\n__pycache__/\n*.pyc\n')
    for command in (['git','init','-q'],['git','config','user.name','Independent case reproduction'],
                    ['git','config','user.email','automation@chipwave.invalid'],['git','add','.'],
                    ['git','add','-f','.chip_nebula/roles/case-physical-tool.yaml','.chip_nebula/recipes/cpu-npu-physical.yaml'],
                    ['git','commit','-qm','Freeze qualified design and independent physical replay']):
        subprocess.run(command,cwd=project,check=True)
    freeze(project,project/'.chip_nebula/recipes/cpu-npu-physical.yaml','independent-replay')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project',type=Path,required=True)
    parser.add_argument('--core-utilization',type=int)
    parser.add_argument('--place-density',type=float)
    parser.add_argument('--cap-margin',type=int)
    parser.add_argument('--slew-margin',type=int)
    args=parser.parse_args();prepare(args.project.resolve(),args.core_utilization,args.place_density,args.cap_margin,args.slew_margin)
