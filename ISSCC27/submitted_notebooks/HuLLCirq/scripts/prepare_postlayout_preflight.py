"""Prepare local readiness configuration; does not run or qualify a simulator."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from hullcirq.postlayout_tools import runtime_descriptor


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--physical-config', type=Path, default=ROOT / '.work/m2g/physical_runtime.json')
    parser.add_argument('--pdk-manifest', type=Path, default=ROOT / '.work/m2g/pdk-input-manifest.json')
    parser.add_argument('--output', type=Path, default=ROOT / '.work/m2j/postlayout_runtime.json')
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to((ROOT / '.work').resolve()):
        parser.error('Output must remain inside HuLLCirq/.work.')
    if output.exists():
        parser.error('Output already exists; retain the prior configuration and choose a new path.')
    manifest = json.loads(args.pdk_manifest.read_text(encoding='utf-8'))
    configuration = {'profile': json.loads((ROOT / 'configs/postlayout_preflight_sky130_v1.json').read_text(encoding='utf-8')),
        'physical_runtime': json.loads(args.physical_config.read_text(encoding='utf-8')),
        'pdk_manifest': str(args.pdk_manifest.resolve()), 'pdk_root': manifest['root'],
        'working_directory': str(ROOT / '.work/m2j/preflight'),
        'execution_scope': 'compatibility_preflight_only', 'verification_supported': False}
    capability = runtime_descriptor(configuration)
    if not capability['available']:
        parser.error(capability['reason'])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(configuration, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'configuration': str(output), 'capability': capability}, indent=2))


if __name__ == '__main__':
    main()
