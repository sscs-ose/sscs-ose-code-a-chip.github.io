#!/usr/bin/env python3
"""Use the pinned ChipWave backend to freeze the case's physical recipe."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import yaml
from chip_nebula.dashboard.workbench import WorkbenchProject

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--top', default='nebula_cpu_npu_top')
    parser.add_argument('--simulation-command', required=True)
    args = parser.parse_args()
    project = WorkbenchProject(args.project.resolve())
    # Imported RTL snapshots carry no Workbench fileset selection yet.
    path = project.root / 'workbench.yaml'
    config = yaml.safe_load(path.read_text())
    config['top_module'] = args.top
    config['design_files'] = [str(p.relative_to(project.root)) for p in
                              sorted(project.root.glob('rtl/**/*.sv')) + sorted(project.root.glob('rtl/**/*.v'))]
    project.save_config(config)
    result = project.configure_physical_project(top_module=args.top, clock_port='clk',
              clock_period_ns=100.0, platform='sky130hd', simulation_command=args.simulation_command)
    path = project.root / 'physical/chip-nebula/configuration-receipt.json'
    path.write_text(json.dumps(result, indent=2, default=str) + '\n')
    print(json.dumps({'top': args.top, 'clock_period_ns': 100, 'platform': 'sky130hd',
                     'environment_ready': result['environment'].get('ready'), 'receipt': str(path)}, indent=2))
    if not result['environment'].get('ready'):
        raise RuntimeError('physical environment not ready; see configuration receipt')
