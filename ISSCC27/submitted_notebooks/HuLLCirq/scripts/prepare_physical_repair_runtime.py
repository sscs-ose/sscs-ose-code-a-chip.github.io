"""Prepare the fixed original-job route-repair profile; launch no EDA or models."""
from pathlib import Path
import argparse
import copy
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from hullcirq.physical_tools import load,require,sha
from hullcirq.physical_repair import checkpoint_identity,validate_configuration


def prepare(destination,version='v2'):
    destination=Path(destination).resolve()
    require(destination.is_relative_to(ROOT/'.work/m2m'),'physical_repair_destination','Use a new M2-M runtime file.')
    original=ROOT/'.work/m2g/layout/hullcirq-layout-pzxpzxpu'
    state=original/'runs/physical/34-openroad-detailedplacement/state_out.json'
    if version=='v5':
        original=ROOT/'.work/m2m/v4/physical/hullcirq-layout-fiu6unxz'
        state=original/'runs/physical/11-openroad-stamidpnr-3/state_out.json'
    if version=='v6':
        original=ROOT/'.work/m2m/v5/physical/hullcirq-layout-0ha1k_f3'
        state=original/'runs/physical/05-openroad-stamidpnr-3/state_out.json'
    inputs=original/'input-manifest.json'
    runtime=copy.deepcopy(load(ROOT/'.work/m2g/physical_runtime.json'))
    runtime['origin']='development_assistant_standard_route_repair_under_user_authorized_completion_original_GUI_job_unchanged'
    runtime['working_directory']=str(ROOT/(f'.work/m2m/{version}/physical' if version in ('v4','v5','v6') else '.work/m2m/physical'))
    require(version in ('v2','v3','v4','v5','v6'),'physical_repair_profile','Use one complete versioned physical repair profile.')
    runtime['profile']=load(ROOT/f'configs/physical_profile_sky130_repair_{version}.json')
    state_sha,input_sha,start_step=checkpoint_identity(runtime)
    require(sha(state)==state_sha and sha(inputs)==input_sha,'physical_repair_source','The original-job checkpoint/input identity changed.')
    runtime['resume']={'initial_state_path':str(state),'initial_state_sha256':state_sha,
        'source_input_manifest_path':str(inputs),'source_input_manifest_sha256':input_sha,'from_step':start_step}
    validate_configuration(runtime)
    destination.parent.mkdir(parents=True,exist_ok=True)
    with destination.open('x',encoding='utf-8') as handle:json.dump(runtime,handle,indent=2);handle.write('\n')
    print(json.dumps({'runtime_configuration':str(destination),'sha256':sha(destination),
        'original_job_changed':False,'constraints_relaxed':False,'model_calls':0,'EDA_starts':0,
        'next_operation':'Start one new S11 run through the normal workflow manager using this runtime.'},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination',type=Path)
    parser.add_argument('--profile-version',choices=('v2','v3','v4','v5','v6'),default='v2')
    args=parser.parse_args()
    prepare(args.destination,args.profile_version)
