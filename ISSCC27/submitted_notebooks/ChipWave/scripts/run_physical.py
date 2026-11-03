#!/usr/bin/env python3
"""Deterministic TaskGraph tool task using the actual ChipWave EDA backend."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from chip_nebula.dashboard.workbench import WorkbenchProject
from chip_nebula.taskgraph.physical import PhysicalFlow
from chip_nebula.taskgraph.tool_executor import DeterministicToolExecutor, ToolCommand


def run(root, subject, mode):
    project = WorkbenchProject(root)
    config = project.config()
    flow = PhysicalFlow(root, config.physical)
    environment = flow.inspect_environment(config.top_parameters)
    if not environment.get('ready'):
        raise RuntimeError('physical preflight failed: ' + json.dumps(environment))
    command, _ = flow.execution_command(root, mode)
    result = DeterministicToolExecutor().execute(root, [ToolCommand('rtl-to-gds', command,
                         cwd=config.physical.workdir, timeout=config.physical.timeout)])
    out = root / config.physical.output_root
    out.mkdir(parents=True, exist_ok=True)
    (out / 'executor.log').write_text(result.log)
    summary = flow.read_summary(root)
    passed = (result.status == 'succeeded' and result.verdict == 'passed'
              and summary.get('status') in ('passed', 'physical_passed')
              and summary.get('detailed_routing_violations') == 0
              and summary.get('drc_violations') == 0 and summary.get('lvs') == 'matched'
              and summary.get('metrics', {}).get('setup_violations') == 0
              and summary.get('metrics', {}).get('hold_violations') == 0)
    report = dict(subject=subject, verdict='passed' if passed else 'failed',
                  design=config.top_module, platform=config.physical.platform,
                  stages=summary.get('stages', []), metrics=summary.get('metrics', {}),
                  artifacts=[item['path'] for item in flow.collect_artifacts(root)],
                  input_digests=['sha256:' + hashlib.sha256((root / 'physical/chip-nebula/flow-definition.json').read_bytes()).hexdigest()],
                  tool_versions={name: value.get('version', '') for name, value in environment.get('tools', {}).items()},
                  raw_flow_summary=summary)
    (out / 'physical-report.json').write_text(json.dumps(report, indent=2, default=str) + '\n')
    print('NEBULA_OUTPUT: ' + json.dumps({'report': report}))
    if not passed:
        raise RuntimeError('physical engineering acceptance failed; inspect preserved report and executor.log')
    print('PHYSICAL_ACCEPTANCE_PASS')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--subject', required=True)
    p.add_argument('--mode', choices=['all', 'physical'], default='all')
    a = p.parse_args()
    run(Path.cwd(), a.subject, a.mode)
