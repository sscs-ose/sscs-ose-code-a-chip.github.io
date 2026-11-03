"""Write S12 configuration referencing the same prepared S11 runtime; no tools run."""
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from hullcirq import physical_tools
from hullcirq.store import strict_loads
from hullcirq.verification import object_hash

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--physical-config',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    base=strict_loads(args.physical_config.read_text(encoding='utf-8-sig'))
    if not (base.get('kind')=='wsl' and base.get('release')==physical_tools.RELEASE
            and base.get('appimage_sha256')==physical_tools.IMAGE_SHA and base.get('pdk_revision')==physical_tools.PDK_REVISION
            and base.get('base_sdc_sha256')==physical_tools.SDC_SHA
            and object_hash(base.get('profile'))==object_hash(physical_tools.load(ROOT/'configs/physical_profile_sky130.json'))):
        parser.error('Use the unchanged prepared pinned S11 physical configuration.')
    output=args.output.resolve();path=output/'drc_runtime.json'
    value={'physical_runtime':base,'working_directory':str(output/'drc'),
        'profile':physical_tools.load(ROOT/'configs/drc_profile_sky130.json')}
    if path.exists():
        if object_hash(strict_loads(path.read_text(encoding='utf-8-sig')))!=object_hash(value):
            parser.error('Existing configuration differs; choose a new output directory. No file overwritten.')
        status='verified_existing_configuration_not_runtime_validation'
    else:
        output.mkdir(parents=True,exist_ok=True)
        with path.open('x',encoding='utf-8') as stream:stream.write(json.dumps(value,indent=2)+'\n')
        status='configuration_written_not_runtime_validation'
    print(json.dumps({'status':status,'path':str(path),'configuration_sha256':object_hash(value),
        'EDA_starts':0,'model_calls':0,'live_history_writes':0}))
    return 0

if __name__=='__main__':raise SystemExit(main())
