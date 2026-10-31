"""One budgeted generic benchmark implementation through ChipWave's public backend."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from dataclasses import asdict
from pathlib import Path

import yaml

from campaign_budget import finish, reserve
from chip_nebula.dashboard.workbench import WorkbenchProject
from chip_nebula.taskgraph.static_store import StaticTaskGraphStore
from classify_study_failures import classify, read_reports
from collect_physical import collect
from freeze_tool_workflow import freeze
from qualify_benchmark import simulate
from run_frequency_search import collect_failed
from study_protocol import digest, write_json

CASE = Path(__file__).resolve().parents[1]


def prepare(project, task, source, *, period_ps=100000):
    meta = json.loads((task/'build.json').read_text())
    shutil.copytree(task/'agent',project)
    shutil.copytree(source,project/'rtl',dirs_exist_ok=True)
    sources=sorted(project.glob('rtl/**/*.sv'))+sorted(project.glob('rtl/**/*.v'))
    if not sources or any(p.is_symlink() or not p.resolve().is_relative_to(project/'rtl') for p in sources):
        raise ValueError('Unsafe or empty candidate sources')
    initial=dict(top_module=meta['top'],design_files=[str(p.relative_to(project)) for p in sources],
                 validation_mode='fileset',simulation_top='benchmark_check_tb',testbench_files=['tb/development_tb.sv'])
    (project/'workbench.yaml').write_text(yaml.safe_dump(initial,sort_keys=False))
    sdk=WorkbenchProject(project)
    sdk.save_config(initial)
    receipt=sdk.configure_physical_project(top_module=meta['top'],clock_port='clk',clock_period_ns=period_ps/1000,
                  platform='sky130hd',simulation_command='python3 tools/check.py')
    write_json(project/'configuration-receipt.json',receipt)
    if not receipt['environment']['ready']:
        raise RuntimeError('Benchmark physical environment not ready')
    physical=project/'physical/chip-nebula'
    config=physical/'config.mk'
    overrides=dict(CORE_UTILIZATION=40,PLACE_DENSITY=.55,ABC_AREA=1,CAP_MARGIN=20,SLEW_MARGIN=20)
    lines=[line for line in config.read_text().splitlines() if not any(line.startswith('export '+key+' =') for key in overrides)]
    config.write_text('\n'.join([*lines,*['export '+k+' = '+str(v) for k,v in overrides.items()]])+'\n')
    input_names=[name+('[*]' if width>1 else '') for direction,name,width in meta['ports'] if direction=='in' and name!='clk']
    (physical/'constraints.sdc').write_text(f'current_design {meta["top"]}\ncreate_clock -name benchmark_clock -period {period_ps/1000:g} [get_ports {{clk}}]\n'
        'set_clock_uncertainty 0.1 [get_clocks benchmark_clock]\nset_input_delay 0.5 -clock benchmark_clock [get_ports {'+' '.join(input_names)+'}]\n'
        'set_output_delay 0.5 -clock benchmark_clock [all_outputs]\n')
    cfg=asdict(sdk.config());cfg['physical']['timeout']=14400;sdk.save_config(cfg)
    # TaskGraph worktrees read the tracked template; SDK state is project-local.
    (project/'workbench.yaml').write_text(yaml.safe_dump(cfg,sort_keys=False))
    (project/'scripts').mkdir(exist_ok=True)
    shutil.copy2(CASE/'scripts/run_physical.py',project/'scripts/run_physical.py')
    roles,recipes=project/'.chip_nebula/roles',project/'.chip_nebula/recipes'
    roles.mkdir(parents=True,exist_ok=True);recipes.mkdir(parents=True,exist_ok=True)
    shutil.copy2(CASE/'workflows/case-physical-tool.yaml',roles/'case-physical-tool.yaml')
    definition=yaml.safe_load((CASE/'workflows/cpu-npu-physical.yaml').read_text())
    node=definition['tasks']['physical'];node['max_attempts']=1;node['execution']['timeout_seconds']=14520
    node['permission']['read']+=['tools/**','tb/**','configuration-receipt.json']
    node['intent']='One independent generic benchmark implementation; preserve source, interface, clock and gates.'
    path=recipes/'benchmark-physical.yaml';path.write_text(yaml.safe_dump(definition,sort_keys=False))
    manifest=dict(task=meta['task'],top=meta['top'],period_ps=period_ps,threads=2,configuration=overrides,
        rtl_sha256={str(p.relative_to(project)):digest(p) for p in sources},
        sdc_sha256=digest(physical/'constraints.sdc'),config_sha256=digest(config),
        final_checker_sha256=digest(task/'grader/acceptance_tb.sv'),budget_seconds=14400)
    write_json(project/'selected-delivery.json',dict(id='benchmark-'+meta['task']['id'],exported_source_sha256=manifest['rtl_sha256']))
    write_json(project/'benchmark-candidate.json',manifest)
    (project/'.gitignore').write_text('.chip_nebula/\nbuild/\n__pycache__/\n*.pyc\n')
    for arguments in (['init','-q'],['config','user.name','ChipWave benchmark automation'],
                      ['config','user.email','automation@chipwave.invalid'],['add','.'],
                      ['add','-f','.chip_nebula/roles','.chip_nebula/recipes'],['commit','-qm','Freeze benchmark physical candidate']):
        subprocess.run(['git',*arguments],cwd=project,check=True)
    freeze(project,path,'benchmark-physical',source_design_delivery='benchmark-'+meta['task']['id'])
    return manifest


def postroute(task, evidence, output):
    selected=json.loads((evidence/'selected-delivery.json').read_text())
    matches=[row for row in selected['collected_files'] if Path(row['path']).name=='6_final.v']
    if len(matches)!=1:raise ValueError('Expected exact final candidate netlist')
    netlist=evidence/matches[0]['path']
    if digest(netlist)!=matches[0]['sha256']:raise ValueError('Candidate netlist changed')
    output.mkdir(parents=True)
    library=CASE/'toolchain/orfs/flow/platforms/sky130hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib'
    models=output/'cell_models.v'
    result=subprocess.run(['yosys','-Q','-T','-p',f'read_liberty -ignore_miss_func {library}; write_verilog -noattr {models}'],
                          text=True,capture_output=True,timeout=120)
    (output/'models.log').write_text(result.stdout+result.stderr)
    if result.returncode:raise RuntimeError('Liberty model extraction failed')
    record=simulate([netlist],task/'grader/acceptance_tb.sv',output/'final-netlist',libraries=[models])
    record.update(netlist_sha256=digest(netlist),cell_models_sha256=digest(models),liberty_sha256=digest(library),
                  source_delivery=selected['id'],scope='Final routed netlist, zero-delay Liberty cell models; no SDF claim')
    write_json(output/'qualification.json',record)
    return record


def run(campaign,task,source,output,*,category,identity):
    campaign,task,source,output=(Path(p).resolve() for p in (campaign,task,source,output))
    reserve(campaign,category,identity,output)
    output.mkdir(parents=True)
    start=time.monotonic();row=dict(identity=identity,category=category,qualified=False)
    os.environ.update(ORFS_ROOT=str(CASE/'toolchain/orfs'),NUM_CORES='2')
    try:
        manifest=prepare(output/'project',task,source)
        write_json(output/'manifest.json',manifest)
        cmd=[sys.executable,'-m','chip_nebula.cli.commands','--project-root',str(output/'project'),'run',
             str(output/'project/.chip_nebula/recipes/benchmark-physical.yaml'),'--workflow','benchmark-physical','--workers','1','--resume']
        with (output/'workflow.log').open('w') as log:
            process=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            try:process.wait(timeout=14640)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid,signal.SIGTERM)
                try:process.wait(timeout=15)
                except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait()
                row['timed_out']=True
        with StaticTaskGraphStore(output/'project/.chip_nebula/shared/memory/taskgraph-v2.db') as store:
            state=store.task_state('benchmark-physical:physical').value
            attempts=store.list_attempts('benchmark-physical:physical')
            if state=='satisfied':collect(output/'project','benchmark-physical',output/'evidence')
            elif attempts:collect_failed(output/'project',attempts[-1],output/'evidence')
        raw,native,errors=read_reports(output/'evidence')
        unchanged=(digest(output/'project/physical/chip-nebula/constraints.sdc')==manifest['sdc_sha256'] and
                   digest(output/'project/physical/chip-nebula/config.mk')==manifest['config_sha256'] and
                   all(digest(output/'project'/p)==h for p,h in manifest['rtl_sha256'].items()))
        physical=dict(physical_qualified=process.returncode==0 and state=='satisfied',task_state=state,
                      frozen_inputs_unchanged=unchanged,failure_classes=errors)
        failures=classify(physical,raw,native)
        gate=None
        if physical['physical_qualified'] and not failures:
            gate=postroute(task,output/'evidence',output/'postroute')
        area=raw.get('finish__design__instance__area__stdcell')
        limit=json.loads((task/'agent/spec/task.json').read_text()).get('area_limit_um2')
        row.update(qualified=physical['physical_qualified'] and not failures and gate is not None and gate['passed'] and
                   (category in ('reference','preformal_calibration','reference_supplement') or limit is not None and area<=limit),
                   physical=physical,failure_classes=failures,native_summary=native,raw_metrics=raw,
                   postroute=gate,cell_area_um2=area,area_limit_um2=limit,exit_code=process.returncode)
        if category in ('reference','preformal_calibration','reference_supplement') and row['qualified']:
            before=json.loads((task/'agent/spec/task.json').read_text())
            after=dict(before,task_validated=True,area_limit_um2=1.25*area,reference_cell_area_um2=area)
            write_json(task/'calibration.json',dict(before=before,after=after,reference_output=str(output.relative_to(campaign)),
                reference_gds_sha256=next(v['sha256'] for v in json.loads((output/'evidence/selected-delivery.json').read_text())['collected_files'] if v['path'].endswith('6_final.gds')),
                calibration_rule='1.25 * reference standard-cell area; freeze before agent evaluation'))
            write_json(task/'agent/spec/task.json',after)
    except Exception as error:
        import traceback
        (output/'error.log').write_text(traceback.format_exc())
        row.update(error_class=type(error).__name__,error=str(error))
    row['total_seconds']=time.monotonic()-start
    write_json(output/'qualification.json',row)
    finish(campaign,identity,status='qualified' if row['qualified'] else 'failed',evidence=str((output/'qualification.json').relative_to(campaign)))
    print(json.dumps(dict(identity=identity,qualified=row['qualified'],output=str(output)),indent=2),flush=True)
    return row


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('campaign','task','source','output'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--category',choices=['reference','demonstration','preformal_calibration','reference_supplement'],required=True)
    parser.add_argument('--identity',required=True)
    a=parser.parse_args();run(a.campaign,a.task,a.source,a.output,category=a.category,identity=a.identity)
