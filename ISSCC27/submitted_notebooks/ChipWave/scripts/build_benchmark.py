"""Build parameterized ChipWave benchmark tasks, never evaluate an agent here."""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import yaml

from benchmark_templates import checker, describe, mutants, reference
from chip_nebula.csir.parser import parse_file
from chip_nebula.csir.provenance import empty_sidecar
from chip_nebula.taskgraph.acceptance_plan import validate_acceptance_plan
from chip_nebula.taskgraph.specir import blocking_diagnostics, run_check
from study_protocol import digest, write_json
from run_benchmark_generation import write_configuration

CASE = Path(__file__).resolve().parents[1]
DEFAULT_TASKS = [dict(id='counter8', family='counter', width=8), dict(id='counter16', family='counter', width=16),
                 dict(id='fifo8x4', family='fifo', width=8, depth=4), dict(id='fifo16x8', family='fifo', width=16, depth=8),
                 dict(id='dot2', family='dot', lanes=2), dict(id='dot4', family='dot', lanes=4)]

CHECK_SCRIPT = '''"""Public development check, intentionally smaller than the independent grader."""
import json,subprocess
from pathlib import Path
root=Path.cwd();out=root/'build/smoke';out.mkdir(parents=True,exist_ok=True)
sources=sorted(root.glob('rtl/**/*.sv'))+sorted(root.glob('rtl/**/*.v'))
if not sources:raise ValueError('No RTL delivered')
for p in sources:
 if p.is_symlink() or not p.resolve().is_relative_to((root/'rtl').resolve()):raise ValueError('Unsafe RTL path')
commands=[['iverilog','-g2012','-s','benchmark_check_tb','-o',str(out/'sim'),*map(str,sources),'tb/development_tb.sv'],['vvp',str(out/'sim')]]
codes=[];text=''
for command in commands:
 r=subprocess.run(command,text=True,capture_output=True,timeout=90);codes.append(r.returncode);text+=r.stdout+r.stderr
 if r.returncode:break
(out/'smoke.log').write_text(text)
report=dict(subject='benchmark-rtl',verdict='passed' if codes==[0,0] and 'BENCHMARK_PASS' in text else 'failed',repair_summary=text[-10000:])
(out/'report.json').write_text(json.dumps(report,indent=2)+'\\n')
print('NEBULA_OUTPUT: '+json.dumps({'report':report}))
if report['verdict']!='passed':raise SystemExit(1)
'''


def validate(task):
    if not isinstance(task, dict) or task.get('family') not in ('counter', 'fifo', 'dot'):
        raise ValueError('Choose a supported parameterized family')
    if not isinstance(task.get('id'), str) or not task['id'].isascii() or not task['id'].isalnum():
        raise ValueError('Task id must be ASCII alphanumeric')
    expected = {'counter': {'id','family','width'}, 'fifo': {'id','family','width','depth'}, 'dot': {'id','family','lanes'}}[task['family']]
    if set(task) != expected:
        raise ValueError('Unexpected/missing task parameters')
    for key in expected - {'id', 'family'}:
        if type(task[key]) is not int:
            raise ValueError('Task dimensions must be integers')
    if task['family'] in ('counter', 'fifo') and task['width'] not in (8,16):
        raise ValueError('Qualified width template range is 8 or 16')
    if task['family'] == 'fifo' and task['depth'] not in (4,8):
        raise ValueError('Qualified FIFO depths are 4 or 8')
    if task['family'] == 'dot' and task['lanes'] not in (2,4):
        raise ValueError('Qualified dot lane counts are 2 or 4')


def execution_materials(output,task,ports):
    """Evaluator-side workload and physical contract; no new agent-visible answers."""
    development={'counter':8,'fifo':32,'dot':8}[task['family']]
    final={'counter':256,'fifo':2048,'dot':256}[task['family']]
    write_json(output/'workload.json',dict(family=task['family'],
        development=dict(seed=12345 if task['family']!='counter' else None,main_samples=development,
                         checker='agent/tb/development_tb.sv'),
        final=dict(seed=20261018 if task['family']!='counter' else None,main_samples=final,
                   checker='grader/acceptance_tb.sv'),
        scope='Deterministic functional transaction workloads plus directed boundary/reset/protocol cases; sample counts are not independent architectures or coverage percentages.'))
    write_json(output/'physical-contract.json',dict(platform='sky130hd',corner='TT',temperature_c=25,voltage_v=1.8,
        period_ps=100000,threads=2,clock_uncertainty_ns=.1,input_output_delay_ns=.5,include_reset=True,
        reference_configuration=dict(utilization=40,density=.55,abc_area=1,repair_margin=20),
        gates=['functional','setup','hold','slew','capacitance','fanout','declared DRC','LVS','routed-netlist function'],
        area_limit='1.25 * measured reference standard-cell area; calibration receipt required before evaluation',
        tool_sources='toolchain/orfs/source-manifest.json in the public distribution',
        physical_timeout_seconds=14400,postprocess_timeout_seconds=1800))
    inputs=[name+('[*]' if width>1 else '') for direction,name,width in ports if direction=='in' and name!='clk']
    top=describe(task)[0]
    (output/'constraints.sdc').write_text(f'current_design {top}\ncreate_clock -name benchmark_clock -period 100 [get_ports {{clk}}]\n'
        'set_clock_uncertainty 0.1 [get_clocks benchmark_clock]\nset_input_delay 0.5 -clock benchmark_clock [get_ports {'+' '.join(inputs)+'}]\n'
        'set_output_delay 0.5 -clock benchmark_clock [all_outputs]\n')
    write_json(output/'commands.json',dict(local='python scripts/qualify_benchmark.py --task TASK_DIRECTORY',
        reference='python scripts/benchmark_physical.py --campaign STUDY_DIRECTORY --task TASK_DIRECTORY --source TASK_DIRECTORY/grader/reference --output NEW_OUTPUT --category reference --identity UNIQUE_REFERENCE_ID',
        fresh_design='python scripts/run_benchmark_generation.py --campaign STUDY_DIRECTORY --task TASK_DIRECTORY',
        caution='Reference and fresh-design entrypoints spend the declared physical/model budget; fresh design requires reference calibration.'))


def build_task(task, output):
    validate(task)
    output = Path(output).resolve()
    if output.exists():
        raise ValueError('An old task remains frozen; choose a new output')
    started = time.monotonic()
    top, ports, contract = describe(task)
    public, grader = output / 'agent', output / 'grader'
    for name in ('spec','rtl','tb','tools','reports','tests/designer','tests/reviewer'):
        (public / name).mkdir(parents=True)
    for name in ('reference','mutants'):
        (grader / name).mkdir(parents=True)
    (public / 'spec/task.md').write_text('# ' + task['id'] + '\n\n' + contract + '''

Use the fixed top-level port names and widths in interface.json. Develop with
`python3 tools/check.py`. Deliver synthesizable RTL under rtl/. Independent
final vectors/reference and scoring are outside your workspace. Do not alter
the task/checker, invoke extra models, or read other trials. The task's area
limit is installed after reference physical calibration, before evaluation.
''')
    write_json(public / 'spec/interface.json', dict(top=top, ports=[dict(direction=d,name=n,width=w) for d,n,w in ports]))
    write_json(public / 'spec/task.json', dict(task, top=top, period_ps=100000, seed=20261018,
              area_limit_um2=None, task_validated=False, checker_scope='public development subset; held-out final grader separate'))
    (public / 'tb/development_tb.sv').write_text(checker(task, False))
    (public / 'tools/check.py').write_text(CHECK_SCRIPT)
    (grader / 'reference/design.sv').write_text(reference(task))
    (grader / 'acceptance_tb.sv').write_text(checker(task, True))
    fault_names=[]
    for name, source in mutants(task).items():
        (grader / 'mutants' / (name+'.sv')).write_text(source)
        fault_names.append(name)

    # The CSIR contract is typed and externally checked, not a fabricated lowered model.
    lines=['module ' + top + ' {']
    for direction,name,width in ports:
        lines.append('  ' + ('in' if direction=='in' else 'abstract out') + ' ' + name + ': ' + ('bit' if width==1 else 'u'+str(width)))
    lines.append('  apply behavior {')
    lines.extend('    ' + name + ': ' + name for _,name,_ in ports)
    lines.extend(['  }','}'])
    (public / 'spec/draft.specir').write_text('\n'.join(lines)+'\n')
    provenance = empty_sidecar(parse_file(public / 'spec/draft.specir'))
    for node in provenance['nodes']:
        node.update(requirements=['REQ-BEHAVIOR'], evidence=['task.md'], design_group='task.behavior')
    provenance['requirements'] = [dict(id='REQ-BEHAVIOR', classification='normative', status='mapped', mapping_kind='both',
        text=contract, evidence=['task.md'], mapped_nodes=[node['node_id'] for node in provenance['nodes']], mapped_contracts=['behavior'])]
    write_json(public / 'spec/provenance.json', provenance)
    write_json(public / 'spec/contracts.json', dict(schema_version='0.1', contracts=[dict(id='behavior',requirements=['REQ-BEHAVIOR'],
        evidence=['task.md','../tb/development_tb.sv'],semantics=dict(language='English plus executable SystemVerilog scoreboard',body=contract),
        interface={name:dict(mode='observe' if direction=='in' else 'constrain',type=dict(kind='bit') if width==1 else dict(kind='uint',width=width)) for direction,name,width in ports},
        verification=dict(status='executable',backend='iverilog',adapter='../tools/check.py'))]))
    check = run_check(public / 'spec/draft.specir')
    write_json(output / 'csir-check.json', check)
    if not check['ok'] or blocking_diagnostics(check['diagnostics']):
        raise ValueError('Generated typed CSIR contract is invalid: ' + json.dumps(check))
    plan = dict(version=1,categories=[dict(key='functional',name='Behavioral acceptance',cards=[dict(key='contract',title='Fixed task contract',
        items=[dict(id='behavior',title='Pass independent final scoreboard',detail=contract,requirement_ids=['REQ-BEHAVIOR'])])])],metrics=[])
    validate_acceptance_plan(plan)
    (public / 'spec/acceptance.plan.yaml').write_text(yaml.safe_dump(plan,sort_keys=False))
    write_json(public / 'spec/freeze.json', dict(scope='Typed CSIR external behavioral contract, not RTL lowering or full behavioral formal proof',
               revision=check['revision_id'],contract_sha256=digest(public/'spec/contracts.json'),task_sha256=digest(public/'spec/task.md')))
    recipe=write_configuration(public)
    (public/'workflow.yaml').write_text(recipe.read_text())
    (output / 'README.md').write_text(f'''# {task['id']}

`agent/` is the only task material exposed to an evaluated agent. `grader/`
contains the independent reference, held-out vectors and deliberate mutants.
CSIR checks the typed interface/contract attachment. Actual behavior is checked
by the executable acceptance scoreboard; no complete CSIR-to-RTL lowering is claimed.

Build another task with:
`python scripts/build_benchmark.py --family {task['family']} --output NEW_DIRECTORY`.
Qualify this task with `python scripts/qualify_benchmark.py --task THIS_DIRECTORY`.
Physical qualification and area calibration are separate from these local checks.
''')
    execution_materials(output,task,ports)
    record = dict(schema_version=1,task=task,top=top,ports=ports,created_seconds=time.monotonic()-started,
        declared_faults=fault_names,model_calls=0,physical_calls=0,
        source_sha256={str(p.relative_to(output)):digest(p) for p in sorted(output.rglob('*')) if p.is_file()},
        status='built_not_yet_qualified',generator_sha256=digest(Path(__file__)),templates_sha256=digest(CASE/'scripts/benchmark_templates.py'))
    write_json(output / 'build.json', record)
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--suite',action='store_true')
    parser.add_argument('--family',choices=['counter','fifo','dot'],default='counter')
    parser.add_argument('--width',type=int,default=8)
    parser.add_argument('--depth',type=int,default=4)
    parser.add_argument('--lanes',type=int,default=2)
    args=parser.parse_args()
    if args.suite:
        if args.output.exists():raise ValueError('Existing suite preserved')
        args.output.mkdir(parents=True)
        rows=[build_task(task,args.output/task['id']) for task in DEFAULT_TASKS]
        write_json(args.output/'suite.json',dict(tasks=[row['task'] for row in rows],families=3,variants=6,qualified=False))
    else:
        task=dict(family=args.family,id=args.family+str(args.lanes if args.family=='dot' else args.width))
        task.update(dict(lanes=args.lanes) if args.family=='dot' else dict(width=args.width))
        if args.family=='fifo':task.update(depth=args.depth,id='fifo'+str(args.width)+'x'+str(args.depth))
        build_task(task,args.output)
    print('BENCHMARK_BUILT; qualification remains required',flush=True)


if __name__ == '__main__':main()
