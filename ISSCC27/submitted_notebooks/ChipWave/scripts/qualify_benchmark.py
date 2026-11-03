"""Independent reference, development/final checker and mutant qualification."""
from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path

from study_protocol import digest, write_json


def simulate(sources, checker, output, *, period_ps=100000, libraries=(), defines=()):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    commands = [['iverilog','-g2012','-s','benchmark_check_tb',f'-DCLOCK_PERIOD_PS={period_ps}',
                 *['-D'+name for name in defines],'-o',str(output/'sim'),*map(str,libraries),*map(str,sources),str(checker)],
                ['vvp',str(output/'sim')]]
    codes=[];started=time.monotonic();timed_out=False
    for name,command in zip(('compile','acceptance'),commands):
        try:
            result=subprocess.run(command,cwd=output,text=True,capture_output=True,timeout=120)
            text=result.stdout+result.stderr;codes.append(result.returncode)
        except subprocess.TimeoutExpired as error:
            timed_out=True;text=str(error);codes.append(124)
        (output/(name+'.log')).write_text(text)
        if codes[-1]:break
    record=dict(compiled=bool(codes) and codes[0]==0,passed=codes==[0,0] and 'BENCHMARK_PASS' in text,
                timed_out=timed_out,exit_codes=codes,commands=commands,seconds=time.monotonic()-started,
                checker_sha256=digest(checker),source_sha256={str(p):digest(p) for p in sources},
                period_ps=period_ps, libraries={str(p):digest(p) for p in libraries})
    write_json(output/'result.json',record)
    return record


def qualify(task, output):
    task,output=Path(task).resolve(),Path(output).resolve()
    if output.exists():raise ValueError('Previous qualification is preserved')
    output.mkdir(parents=True)
    meta=json.loads((task/'build.json').read_text())
    for relative,expected in meta['source_sha256'].items():
        if relative=='agent/spec/task.json' and (task/'calibration.json').exists():
            calibration=json.loads((task/'calibration.json').read_text())
            if json.loads((task/relative).read_text())!=calibration['after']:
                raise ValueError('Calibrated task parameters have changed')
            continue
        if digest(task/relative)!=expected:raise ValueError('Built task has changed: '+relative)
    source=task/'grader/reference/design.sv'
    final=simulate([source],task/'grader/acceptance_tb.sv',output/'reference-final')
    development=simulate([source],task/'agent/tb/development_tb.sv',output/'reference-development')
    faults={}
    for name in meta['declared_faults']:
        row=simulate([task/'grader/mutants'/(name+'.sv')],task/'grader/acceptance_tb.sv',output/'mutants'/name)
        row['detected']=row['compiled'] and not row['passed'] and not row['timed_out'] and row['exit_codes'][-1]!=0
        faults[name]=row
    script=f'read_slang --top {meta["top"]} {source}; proc; memory_map; opt; check -assert; write_json {output}/synthesis.json'
    result=subprocess.run(['yosys','-Q','-T','-p',script],text=True,capture_output=True,timeout=120)
    (output/'synthesis.log').write_text(result.stdout+result.stderr)
    record=dict(task=meta['task'],top=meta['top'],reference_final=final,reference_development=development,mutants=faults,
        synthesis_exit_code=result.returncode,local_qualified=final['passed'] and development['passed'] and
        len(faults)>=3 and all(row['detected'] for row in faults.values()) and result.returncode==0,
        physical_qualified=False,scope='Local reference/checker qualification; physical calibration still required')
    write_json(output/'qualification.json',record)
    print(json.dumps(dict(task=meta['task']['id'],local_qualified=record['local_qualified'],
                         mutants_detected=sum(row['detected'] for row in faults.values())),indent=2),flush=True)
    return record


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--task',type=Path,required=True)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    record=qualify(args.task,args.output or args.task/'qualification')
    if not record['local_qualified']:raise SystemExit(1)
