"""Build disjoint development/formal test-data packages with unchanged task contracts."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import capacity_dot
import capacity_memory
from attach_capacity_contracts import attach
from capacity_candidate import ALLOWED_CONFIG, DEFAULT_CONFIG, SYSTEM_FUNCTIONS
from capacity_integration_physical import ROOT, verified_integration
from check_capacity_progress import dot_bench, memory_bench
from qualify_capacity_tasks import simulate
from study_protocol import digest, write_json


def source_policy():
    return '''# Shared source and tool contract

Implement only the task module and its internal helpers in rtl/. The supplied
CPU, ISA, neighboring modules, firmware, interface and physical constraints are
read-only. Do not define replacements for frozen modules. Original source and
configuration bytes are captured at every admitted tool boundary.

The evaluator preprocesses Verilog/SystemVerilog in isolation, removes compiler
metacomments and uses that same canonical source for function and implementation.
Local .v/.sv compilation units and .vh/.svh headers are supported. Process/file
operations, DPI, external binds, unresolved black boxes and changed interfaces
are rejected. The side-effect-free system functions admitted are:

'''+', '.join('$'+name for name in sorted(SYSTEM_FUNCTIONS))+'''.

Only configuration/implementation.json may supply implementation knobs; omit it
to use the defaults. No clock, PDK, interface, checker or tool override is allowed.

Defaults: `'''+json.dumps(DEFAULT_CONFIG)+'''`

Allowed values: `'''+json.dumps(ALLOWED_CONFIG)+'''`

Use `python tools/check.py` for the public module smoke check. All executable
development commands, including self-written tests, share 20 check slots.
`capacity-check status` reads the shared Token/time/tool counters without spending
a check slot; its model invocation still consumes the ordinary shared Tokens.
`capacity-check integration` also consumes one of these slots; it runs the fixed
CPU workloads with public memory seed 17. `capacity-check synth` consumes one of
six generic full-integration synthesis slots; it is not a PPA/STA estimate.
Physical workload measurement uses the public, fixed response seed 20261021.
Additional final-check vectors and response schedules stay in the evaluator;
their final acceptance results are not returned through the tool interface.
`capacity-check physical` consumes one of two complete physical attempts, even
if source admission, tools or implementation fail. Failed slots are not refunded.
Full diagnostics appear in the producing role's reports/<stage>/eda/ directory.
These copies can be handed to other roles; protected originals remain authoritative.

All roles share one million logical input-plus-output Tokens (cached input
included), 90 minutes active time and the same serial tools. Physical waiting
is separately limited to four hours plus 30 minutes deterministic postprocessing
per attempt. No other model, remote service or full physical invocation is allowed.
Only an admitted source/configuration version with matching physical evidence
can receive a GDS score. The latest admitted attempt is retained even if it fails;
there is no automatic fallback to an earlier successful attempt. Editing RTL or
configuration after the last attempt can leave the final source without matching
GDS. Reports and comments must not invent a successful result.
'''


def build(variant,task):
    if variant not in ('pilot','formal') or task not in ('A1','A2','B1','B2'):
        raise ValueError('Unknown package')
    target=ROOT/'task-packages'/variant/task
    if target.exists():raise ValueError('Existing task package retained')
    public=target/'agent';grader=target/'grader'
    for folder in (public/'spec',public/'tb',public/'rtl',grader/'mutants'):
        folder.mkdir(parents=True)
    template=capacity_dot if task.startswith('A') else capacity_memory
    slots=1 if task.endswith('1') else 4
    original=ROOT/'tasks'/task
    meta=json.loads((original/'agent/spec/interface.json').read_text())
    write_json(public/'spec/interface.json',meta)
    contract=template.contract(slots).replace('With live-command capacity and no cancel',
        'With an unreserved command slot available and no cancel')
    (public/'spec/task.md').write_text('# '+task+' — '+variant+' test-data variant\n\n'+contract+
        '\nRead resource-contract.md, the read-only frozen integration, and scorecard.json.\n'
        'Deliver the assigned subsystem and its complete frozen CPU integration at 95 MHz.\n')
    if task.startswith('A'):
        final=template.checker(slots,True,seed=20261022 if variant=='pilot' else 20261021)
        development=template.checker(slots,False,seed=1978 if variant=='pilot' else 1977)
        progress=dot_bench(slots,data_offset=19 if variant=='pilot' else 0)
    else:
        final,development=template.checker(slots,True),template.checker(slots,False)
        if variant=='pilot':
            final=final.replace("32'h89abcdef","32'hb94ec712").replace("32'h12340000","32'h72ba0000")
            development=development.replace("32'h89abcdef","32'hb94ec712").replace("32'h12340000","32'h72ba0000")
        progress=memory_bench(data_offset=19 if variant=='pilot' else 0)
    (public/'tb/development_tb.sv').write_text(development)
    (grader/'final_tb.sv').write_text(final);(grader/'progress_tb.sv').write_text(progress)
    shutil.copy2(original/'grader/reference.sv',grader/'reference.sv')
    for path in (original/'grader/mutants').glob('*.sv'):shutil.copy2(path,grader/'mutants'/path.name)
    attach(target)
    (public/'spec/resource-contract.md').write_text(source_policy())
    source,frozen=verified_integration(task)
    for name in ('rtl','verification','workloads'):
        shutil.copytree(source/name,public/'spec/frozen'/name)
    shutil.rmtree(public/'spec/frozen/rtl/candidate')
    write_json(public/'spec/scorecard.json',dict(calibrated=False,period_ns=10.526,
        scoring='100 F G H min(1,0.5 cbrt(T/Tref Eref/E Aref/A))',
        constraints=dict(minimum_throughput_ratio=.8,maximum_latency_ratio=1.25,
                         maximum_cell_area_ratio=1.25,maximum_die_area_ratio=1.25,
                         maximum_power_ratio=1.25,maximum_energy_ratio=1.25),
        note='Not runnable until all reference integrations and scoring gates qualify'))
    task_json=public/'spec/task.json';data=json.loads(task_json.read_text());data.update(
        period_ps=10526,module_reference_period_ps=100000,variant=variant,
        scope='Assigned subsystem in a frozen CPU integration; reference calibration pending')
    write_json(task_json,data)
    rows=[]
    for name,bench in (('development',public/'tb/development_tb.sv'),('final',grader/'final_tb.sv'),('progress',grader/'progress_tb.sv')):
        rows.append(simulate(grader/'reference.sv',bench,target/'qualification'/name))
    faults=[]
    for path in (grader/'mutants').glob('*.sv'):
        checked=simulate(path,grader/'final_tb.sv',target/'qualification/mutants'/path.stem)
        checked.update(fault=path.stem,detected=checked['compiled'] and checked['exit_codes']==[0,1]);faults.append(checked)
    receipt=dict(task=task,variant=variant,passed=all(x['passed'] for x in rows) and all(x['detected'] for x in faults),
        reference_checks=rows,mutants=faults,csir_pass=True,calibrated=False,frozen=False,
        variant_scope='Different functional vectors and memory patterns; unchanged interface, difficulty, CPU workloads and physical constraints',
        integration_sha256=frozen['source_sha256'],source_sha256={str(p.relative_to(target)):digest(p)
        for base in (public,grader) for p in sorted(base.rglob('*')) if p.is_file()})
    write_json(target/'package.json',receipt)
    build_receipt=json.loads((target/'build.json').read_text())
    build_receipt.update(source_sha256=receipt['source_sha256'],
                         status='draft_task_package_checked_not_yet_calibrated_or_frozen')
    write_json(target/'build.json',build_receipt)
    print(json.dumps(dict(task=task,variant=variant,passed=receipt['passed'])),flush=True)
    return receipt


if __name__=='__main__':
    rows=[build(variant,task) for variant in ('pilot','formal') for task in ('A1','A2','B1','B2')]
    result=dict(passed=all(r['passed'] for r in rows),packages=8,model_calls=0,physical_runs=0,
                compiling_faults_rejected=sum(x['detected'] for r in rows for x in r['mutants']))
    write_json(ROOT/'checks/task-packages.json',result)
    raise SystemExit(0 if result['passed'] else 1)
