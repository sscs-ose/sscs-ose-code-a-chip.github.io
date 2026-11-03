#!/usr/bin/env python3
"""Rebuild the released case in a new directory; no model account is needed."""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def checked(command,log,cwd,timeout):
    log.parent.mkdir(parents=True,exist_ok=True)
    with log.open('w') as handle:
        result=subprocess.run(command,cwd=cwd,stdout=handle,stderr=subprocess.STDOUT,timeout=timeout)
    if result.returncode:
        raise RuntimeError(f'reproduction command failed; see {log}')
    print('Passed:',log.name,flush=True)


def simulate_tb(project,output,tb,top,parameters=()):
    obj=output/top
    sources=sorted(project.glob('rtl/**/*.sv'))+sorted(project.glob('rtl/**/*.v'))
    checked(['verilator','--binary','--timing','--assert','-Wno-fatal','-j','4','--top-module',top,
             *parameters,'--Mdir',str(obj),*map(str,sources),str(ROOT/'verification'/tb)],
            output/f'{top}-compile.log',ROOT,600)
    checked([str(obj/f'V{top}')],output/f'{top}-run.log',ROOT,120)


def reproduce(output,physical,source=None,elapsed_seconds=None):
    default_source=source is None
    source=ROOT/'released_design' if default_source else source.resolve()
    if elapsed_seconds is None:
        if not default_source:raise ValueError('A new selected design requires its recorded --elapsed-seconds')
        elapsed_seconds=2123.6762506961823
    if type(elapsed_seconds) not in (int,float) or not math.isfinite(elapsed_seconds) or elapsed_seconds<0:
        raise ValueError('Engineering wall time must be finite and nonnegative')
    if not source.is_dir():raise ValueError('selected design is not packaged yet')
    if output.exists():raise ValueError('choose a new output directory; previous runs are preserved')
    record=json.loads((source/'selected-delivery.json').read_text())
    for relative,digest in record['exported_source_sha256'].items():
        if not (source/relative).resolve().is_relative_to(source.resolve()):raise ValueError('Source hash path escapes selected design')
        assert hashlib.sha256((source/relative).read_bytes()).hexdigest()==digest,relative
    output.mkdir(parents=True)
    project=output/'design';shutil.copytree(source,project)
    reports=output/'results';reports.mkdir()
    # Run the common CPU scorer first so partial coverage survives a later extension failure.
    checked([sys.executable,str(ROOT/'verification/benchmark/evaluator/t09_check.py'),str(project),
             '--elapsed-seconds',str(elapsed_seconds),'--output',str(reports/'t09.json')],reports/'t09.log',ROOT,2400)
    t09=json.loads((reports/'t09.json').read_text())
    assert t09.get('score',{}).get('full_functional_pass'), 'T09 semantic/timing acceptance failed'
    checked([sys.executable,str(ROOT/'scripts/run_kernels.py'),'--project',str(project),'--output',str(reports/'operators')],
            reports/'operators.log',ROOT,1200)
    checked([sys.executable,str(ROOT/'scripts/run_custom_reset.py'),'--project',str(project),'--output',str(reports/'custom-reset')],
            reports/'custom-reset.log',ROOT,900)
    simulate_tb(project,reports,'custom_traps_tb.sv','custom_traps_tb',('-GENABLE=1',))
    simulate_tb(project,reports/'base-custom-traps','custom_traps_tb.sv','custom_traps_tb',('-GENABLE=0',))
    simulate_tb(project,reports,'precise_custom_tb.sv','precise_custom_tb')
    npu=reports/'npu';npu.mkdir()
    sources=sorted(project.glob('rtl/**/nebula_npu_dot4.sv'))
    assert len(sources)==1, 'Exactly one fixed-interface NPU module is required'
    checked(['iverilog','-g2012','-s','npu_acceptance_tb','-o',str(npu/'sim'),*map(str,sources),str(ROOT/'verification/npu_acceptance_tb.sv')],
            npu/'compile.log',ROOT,120)
    checked(['vvp',str(npu/'sim')],npu/'run.log',ROOT,180)
    assert 'NPU_ACCEPTANCE_PASS cases=264202 cancellations=8' in (npu/'run.log').read_text()
    # The recorded engineering time is replay metadata, not a new timed design run.
    summary=dict(passed=True,physical_requested=physical,physical_passed=None,
                 source_artifact=record['id'],source_commit=record['content']['commit'],
                 source_sha256=record['exported_source_sha256'],
                 recorded_engineering_wall_seconds=elapsed_seconds,
                 functional_reports='results/',model_calls=0)
    if physical:
        checked([sys.executable,str(ROOT/'scripts/prepare_replay_physical.py'),'--project',str(project)],
                reports/'physical-preparation.log',ROOT,600)
        checked([sys.executable,'-m','chip_nebula.cli.commands','--project-root',str(project),'run',
                 str(project/'.chip_nebula/recipes/cpu-npu-physical.yaml'),'--workflow','independent-replay',
                 '--param','rtl=imported-main-rtl','--workers','1','--resume'],reports/'physical.log',ROOT,20000)
        from chip_nebula.taskgraph.static_store import StaticTaskGraphStore
        with StaticTaskGraphStore(project/'.chip_nebula/shared/memory/taskgraph-v2.db') as store:
            delivery=store.deliveries('independent-replay:physical').get('report')
            assert delivery and store.task_state('independent-replay:physical').value=='satisfied'
            artifact=store.get_artifact(delivery.artifact_id)
            assert artifact.payload['verdict']=='passed'
            summary['physical_passed']=True
            summary['physical_artifact']=artifact.document()
    (output/'reproduction.json').write_text(json.dumps(summary,indent=2)+'\n')
    print('INDEPENDENT_REPRODUCTION_PASS',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--source',type=Path,help='Another exported selected Delivery with selected-delivery.json')
    parser.add_argument('--elapsed-seconds',type=float,help='Recorded engineering wall time for the selected design; not replay time')
    parser.add_argument('--physical',action='store_true',help='Also run the complete frozen RTL-to-GDS flow')
    args=parser.parse_args();reproduce(args.output.resolve(),args.physical,args.source,args.elapsed_seconds)
