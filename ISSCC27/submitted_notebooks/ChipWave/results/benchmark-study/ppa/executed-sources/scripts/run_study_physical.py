"""One frozen physical implementation for the configurable-workflow study."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

import yaml

from chip_nebula.dashboard.workbench import WorkbenchProject
from chip_nebula.taskgraph.static_store import StaticTaskGraphStore
from collect_physical import collect
from freeze_tool_workflow import freeze
from run_frequency_search import collect_failed
from study_protocol import BASELINE, config_tuple, digest, write_json
from classify_study_failures import classify, read_reports

CASE = Path(__file__).resolve().parents[1]


def prepare(project, source, configuration, period_ps):
    config_tuple(configuration)
    if type(period_ps) is not int or period_ps <= 0 or period_ps % 2:
        raise ValueError('Positive even integer-picosecond clock period required')
    selected = json.loads((source / 'selected-delivery.json').read_text())
    sources = selected['exported_source_sha256']
    if not sources:
        raise ValueError('Empty source delivery')
    for relative, expected in sources.items():
        path = source / relative
        if path.is_symlink() or not path.resolve().is_relative_to((source / 'rtl').resolve()):
            raise ValueError('Unsafe source path: ' + relative)
        if digest(path) != expected:
            raise ValueError('Source delivery changed: ' + relative)
    if project.exists():
        raise ValueError('Existing project preserved: ' + str(project))
    shutil.copytree(CASE / 'released_design', project)
    shutil.rmtree(project / 'rtl')
    for relative in sources:
        destination = project / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / relative, destination)
    write_json(project / 'selected-delivery.json', selected)
    sdk = WorkbenchProject(project)
    cfg = yaml.safe_load((project / 'workbench.yaml').read_text())
    cfg.update(top_module='nebula_cpu_npu_top', design_files=sorted(sources))
    sdk.save_config(cfg)
    receipt = sdk.configure_physical_project(
        top_module='nebula_cpu_npu_top', clock_port='clk', clock_period_ns=period_ps / 1000,
        platform='sky130hd', simulation_command='python3 scripts/run_kernels.py --project . --output build/operators')
    if not receipt['environment']['ready']:
        raise RuntimeError('Physical environment not ready: ' + json.dumps(receipt))
    physical = project / 'physical/chip-nebula'
    write_json(physical / 'configuration-receipt.json', receipt)
    config = physical / 'config.mk'
    overrides = {'CORE_UTILIZATION': configuration['utilization'], 'PLACE_DENSITY': configuration['density'],
                 'ABC_AREA': configuration['abc_area'], 'CAP_MARGIN': configuration['repair_margin'],
                 'SLEW_MARGIN': configuration['repair_margin']}
    lines = [line for line in config.read_text().splitlines()
             if not any(line.startswith('export ' + key + ' =') for key in overrides)]
    lines.extend('export ' + key + ' = ' + str(value) for key, value in overrides.items())
    config.write_text('\n'.join(lines) + '\n')
    sdc = ('current_design nebula_cpu_npu_top\n'
           f'create_clock -name nebula_clock -period {period_ps / 1000:g} [get_ports {{clk}}]\n'
           'set_clock_uncertainty 0.1 [get_clocks nebula_clock]\n'
           'set_input_delay 0.5 -clock nebula_clock [get_ports {rst_n imem_rdata[*] dmem_req_ready dmem_rsp_valid dmem_rsp_rdata[*] dmem_rsp_err}]\n'
           'set_output_delay 0.5 -clock nebula_clock [all_outputs]\n')
    (physical / 'constraints.sdc').write_text(sdc)
    cfg = yaml.safe_load((project / 'workbench.yaml').read_text())
    cfg['physical']['timeout'] = 14400
    sdk.save_config(cfg)
    (project / 'scripts').mkdir(exist_ok=True)
    for name in ('run_physical.py', 'run_kernels.py', 'kernel_programs.py'):
        shutil.copy2(CASE / 'scripts' / name, project / 'scripts' / name)
    verification = project / 'verification'
    verification.mkdir(exist_ok=True)
    # Physical workload checks use this closure; the full independent CPU benchmark stays in the public package.
    for name in ('tb_cpu_npu.sv', 'sail_commit.py', 'LICENSE.benchmark'):
        shutil.copy2(CASE / 'verification' / name, verification / name)
    roles, recipes = project / '.chip_nebula/roles', project / '.chip_nebula/recipes'
    roles.mkdir(parents=True, exist_ok=True); recipes.mkdir(parents=True, exist_ok=True)
    shutil.copy2(CASE / 'workflows/case-physical-tool.yaml', roles / 'case-physical-tool.yaml')
    definition = yaml.safe_load((CASE / 'workflows/cpu-npu-physical.yaml').read_text())
    task = definition['tasks']['physical']
    task['max_attempts'] = 1
    task['execution']['timeout_seconds'] = 14520
    task['intent'] = f'One physical implementation at {period_ps} ps with explicit reset/IO constraints; no source or target changes.'
    recipe = recipes / 'cpu-npu-physical.yaml'
    recipe.write_text(yaml.safe_dump(definition, sort_keys=False))
    (project / '.gitignore').write_text('.chip_nebula/\nbuild/\n__pycache__/\n*.pyc\n')
    manifest = {'schema_version': 1, 'configuration': configuration, 'period_ps': period_ps,
                'rtl_sha256': sources, 'source_design_delivery': selected['id'],
                'sdc_sha256': digest(physical / 'constraints.sdc'), 'config_sha256': digest(config),
                'physical_timeout_seconds': 14400, 'threads': 2,
                'scope': 'One fixed-RTL physical implementation; historical records are unchanged'}
    write_json(project / 'study-candidate.json', manifest)
    for command in (['git', 'init', '-q'], ['git', 'config', 'user.name', 'ChipNebula study automation'],
                    ['git', 'config', 'user.email', 'automation@chipnebula.invalid'], ['git', 'add', '.'],
                    ['git', 'add', '-f', '.chip_nebula/roles', '.chip_nebula/recipes'],
                    ['git', 'commit', '-qm', 'Freeze study candidate before physical execution']):
        subprocess.run(command, cwd=project, check=True)
    freeze(project, recipe, 'study-physical', source_design_delivery=selected['id'])
    return manifest


def run(output, source, configuration, period_ps):
    if output.exists():
        raise ValueError('Existing run preserved: ' + str(output))
    os.environ.update(ORFS_ROOT=str(CASE / 'toolchain/orfs'), NUM_CORES='2')
    output.mkdir(parents=True)
    flow = json.loads((CASE / 'toolchain/orfs/source-manifest.json').read_text())['files']
    for item in flow:
        if digest(CASE / 'toolchain/orfs' / item['path']) != item['sha256']:
            raise ValueError('Pinned physical-flow source changed: ' + item['path'])
    project = output / 'project'
    manifest = prepare(project, source, configuration, period_ps)
    write_json(output / 'manifest.json', manifest)
    cmd = [sys.executable, '-m', 'chip_nebula.cli.commands', '--project-root', str(project),
           'run', str(project / '.chip_nebula/recipes/cpu-npu-physical.yaml'),
           '--workflow', 'study-physical', '--workers', '1', '--resume']
    start = time.monotonic()
    write_json(output / 'state.json', {'state': 'running', 'command': cmd, 'pid': os.getpid()})
    timed_out = False
    with (output / 'workflow.log').open('w') as log:
        proc = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            proc.wait(timeout=14640)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(proc.pid, signal.SIGTERM)
            try: proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL); proc.wait()
    row = {'physical_finished': True, 'exit_code': proc.returncode, 'timed_out': timed_out,
           'physical_wall_seconds': time.monotonic() - start, 'configuration': configuration,
           'physical_qualified': False, 'rank_eligible': False, 'failure_classes': [], 'manifest': manifest}
    with StaticTaskGraphStore(project / '.chip_nebula/shared/memory/taskgraph-v2.db') as store:
        task = 'study-physical:physical'
        attempts = store.list_attempts(task)
        row['task_state'] = store.task_state(task).value
        row['attempts'] = [{'id': a.id, 'status': a.status.value, 'failure': a.diagnostics.get('failure_reason', '')} for a in attempts]
        selected = store.deliveries(task).get('report')
        if selected and row['task_state'] == 'satisfied':
            collect(project, 'study-physical', output / 'evidence', include_operators=True)
        elif attempts:
            collect_failed(project, attempts[-1], output / 'evidence')
    raw, summary, report_errors = read_reports(output/'evidence')
    row['metrics'] = summary.get('metrics', {})
    row['electrical_violations'] = {k: raw.get('finish__timing__drv__' + k) for k in ('max_slew', 'max_cap', 'max_fanout')}
    row['failure_classes'].extend(report_errors)
    row['physical_qualified'] = (not timed_out and proc.returncode == 0 and row['task_state'] == 'satisfied'
                                 and summary.get('status') in ('passed', 'physical_passed'))
    row['frozen_inputs_unchanged'] = (digest(project / 'physical/chip-nebula/constraints.sdc') == manifest['sdc_sha256']
                                    and digest(project / 'physical/chip-nebula/config.mk') == manifest['config_sha256']
                                    and all(digest(project / p) == h for p, h in manifest['rtl_sha256'].items()))
    row['failure_classes'] = classify(row, raw, summary)
    row['physical_qualified'] &= row['frozen_inputs_unchanged'] and not row['failure_classes']
    write_json(output / 'summary.json', row)
    write_json(output / 'state.json', {'state': 'physical_finished', 'summary': 'summary.json'})
    print(json.dumps({'physical_finished': True, 'physical_qualified': row['physical_qualified'], 'output': str(output)}), flush=True)
    return row


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--source', type=Path, default=CASE / 'released_design')
    p.add_argument('--configuration', type=Path)
    p.add_argument('--period-ps', type=int, default=10526)
    a = p.parse_args()
    run(a.output.resolve(), a.source.resolve(), json.loads(a.configuration.read_text()) if a.configuration else BASELINE, a.period_ps)
