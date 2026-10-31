"""Requalify the common RTL-action library without model calls or PPA prescreening."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

from benchmark_rtl_actions import qualify as formal_qualify
from study_protocol import digest,write_json

CASE=Path(__file__).resolve().parents[1]


def qualify(output):
    output=Path(output).resolve();started=time.monotonic()
    formal_qualify(output)
    qualification=json.loads((output/'qualification.json').read_text());rows=[]
    checker=CASE/'verification/npu_acceptance_tb.sv'
    for combination in qualification['combinations']:
        label=Path(combination['source']).parts[0];source=output/combination['source']
        integration=output/label/'integration'
        with (output/label/'integration-driver.log').open('w') as log:
            subprocess.run([sys.executable,str(CASE/'scripts/run_kernels.py'),'--project',str(source),
                            '--output',str(integration)],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=1200)
        summary=json.loads((integration/'summary.json').read_text())
        assert summary['passed'] and len(summary['rows'])==21
        protocol=output/label/'protocol';protocol.mkdir();npu=source/'rtl/npu/nebula_npu_dot4.sv'
        now=time.monotonic()
        for name,command in [('compile',['iverilog','-g2012','-s','npu_acceptance_tb','-o',str(protocol/'sim'),str(npu),str(checker)]),
                             ('acceptance',['vvp',str(protocol/'sim')])]:
            result=subprocess.run(command,text=True,capture_output=True,timeout=180)
            (protocol/(name+'.log')).write_text(result.stdout+result.stderr)
            if result.returncode:raise RuntimeError('Action protocol failed: '+label+'/'+name)
        assert 'NPU_ACCEPTANCE_PASS cases=264202 cancellations=8' in (protocol/'acceptance.log').read_text()
        record=dict(passed=True,actions=combination['actions'],seconds=time.monotonic()-now,
                    source_sha256=digest(npu),checker_sha256=digest(checker))
        write_json(protocol/'qualification.json',record)
        rows.append(dict(actions=label,integration_passed=True,integration_cases=21,protocol=record))
    write_json(output/'integration-qualification.json',dict(passed=True,rows=rows))
    write_json(output/'protocol-qualification.json',dict(passed=True,rows=[r['protocol'] for r in rows]))
    evidence={}
    for p in sorted(output.rglob('*')):
        if p.is_file() and (p.name in ('qualification.json','summary.json','proof.json','selected-delivery.json') or p.name=='expected_outputs.json'):
            evidence[str(p.relative_to(output))]=digest(p)
    admission=dict(admitted=True,all_three_nontrivial_combinations=True,files=evidence,
        preparation_seconds=time.monotonic()-started,model_calls=0,physical_calls=0,
        selection='Correctness only: temporal induction, CPU integration and concrete reset/cancel/backpressure. No physical screening.')
    write_json(output/'admission.json',admission)
    print('SHARED_RTL_ACTIONS_ADMITTED',flush=True)
    return admission


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    qualify(parser.parse_args().output)
