"""Simulate the published dot2 reference and reject its cancellation mutant; no AI or P&R."""
import argparse
import csv
import json
import shutil
from pathlib import Path

from qualify_benchmark import simulate
from study_protocol import digest, write_json

CASE=Path(__file__).resolve().parents[1]


def run(output):
    output=output.resolve()
    if output.exists():raise ValueError('Previous lesson is preserved; choose a new output directory')
    for tool in ('iverilog','vvp'):
        if not shutil.which(tool):raise RuntimeError('Install Icarus Verilog and put '+tool+' on PATH')
    task=CASE/'results/benchmark-study/benchmark/tasks/dot2'
    checker=CASE/'verification/handshake_lesson_tb.sv'
    sources={'reference':task/'grader/reference/design.sv',
             'cancel_ignored':task/'grader/mutants/cancel_ignored.sv'}
    results={name:simulate([source],checker,output/name,period_ps=10000)
             for name,source in sources.items()}
    assert results['reference']['passed'], 'Published reference failed the lesson'
    faulty=results['cancel_ignored']
    assert faulty['compiled'] and not faulty['passed'] and not faulty['timed_out'] and faulty['exit_codes'][-1]!=0
    with (output/'reference/trace.csv').open() as handle:trace=list(csv.DictReader(handle))
    assert len(trace)==17
    delivered=[int(r['cycle']) for r in trace if r['rsp_valid']==r['rsp_ready']=='1']
    assert delivered==[6], 'Cancelled commands must not be delivered'
    record=dict(passed=True,scope='Local teaching simulation of the published dot2 reference; not a new design or PPA experiment',
        expression='2 * 4 + (-3) * 5 = -7',sample='Settled signals immediately before each rising edge',
        delivered_cycles=delivered,trace=trace,mutant_rejected=True,
        inputs={str(p.relative_to(CASE)):digest(p) for p in [checker,*sources.values()]},
        tools={name:dict(path=shutil.which(name),sha256=digest(Path(shutil.which(name)).resolve())) for name in ('iverilog','vvp')},
        actual_model_calls=0,actual_physical_calls=0)
    write_json(output/'lesson.json',record)
    print(json.dumps(dict(passed=True,output=str(output),delivered_cycles=delivered,mutant_rejected=True)))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    run(parser.parse_args().output)
