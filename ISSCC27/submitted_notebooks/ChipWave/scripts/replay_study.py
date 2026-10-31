"""Verify saved study files and rerun independent accelerator/counter checks offline."""
from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path

from audit_study_ip import audit
from study_protocol import digest, write_json

CASE=Path(__file__).resolve().parents[1]


def run(output,results):
    if output.exists():raise ValueError('Choose a new replay output; prior checks are retained')
    output.mkdir(parents=True)
    manifest=json.loads((results/'export-manifest.json').read_text())
    for item in manifest['files']:
        path=results/item['path']
        if not path.resolve().is_relative_to(results) or path.is_symlink() or digest(path)!=item['sha256']:
            raise ValueError('Saved evidence changed: '+item['path'])
    analysis=json.loads((results/'generation/analysis.json').read_text());rows=[]
    checker=CASE/'verification/npu_acceptance_tb.sv'
    for trial in analysis['rows']:
        name=trial['job']['id'];source=results/'generation'/name/'results/selected'
        original=json.loads((source.parent/'result.json').read_text())
        for relative,expected in original['final_checker']['source_sha256'].items():
            if digest(source/relative)!=expected:raise ValueError('Changed selected source')
        target=output/name;target.mkdir()
        paths=[str(source/relative) for relative in original['final_checker']['source_sha256'] if Path(relative).suffix in ('.sv','.v')]
        commands=[['iverilog','-g2012','-s','npu_acceptance_tb','-o',str(target/'sim'),*paths,str(checker)],
                  ['vvp',str(target/'sim')],
                  ['yosys','-Q','-T','-p','read_slang --top nebula_npu_dot4 '+' '.join(paths)+'; proc; opt; check -assert']]
        codes=[];started=time.monotonic()
        for label,command in zip(('compile','acceptance','synthesis'),commands):
            result=subprocess.run(command,capture_output=True,text=True,timeout=120)
            (target/(label+'.log')).write_text(result.stdout+result.stderr);codes.append(result.returncode)
            if result.returncode:break
        passed=codes==[0,0,0] and 'NPU_ACCEPTANCE_PASS cases=264202 cancellations=8' in (target/'acceptance.log').read_text()
        if trial['job']['input']=='ip':passed=passed and audit(source,target/'ip-audit')['passed']
        row={'trial':name,'passed':passed,'exit_codes':codes,'seconds':time.monotonic()-started}
        write_json(target/'result.json',row);rows.append(row)
    source=results/'transfer/counter/results'
    counter=json.loads((source/'result.json').read_text());target=output/'counter';target.mkdir()
    paths=[]
    for relative,expected in counter['source_sha256'].items():
        path=source/'selected'/relative
        if digest(path)!=expected:raise ValueError('Changed counter source')
        paths.append(str(path))
    checker=source/'counter_acceptance_tb.sv'
    if digest(checker)!=counter['final_checker_sha256']:raise ValueError('Counter checker changed')
    compile_result=subprocess.run(['iverilog','-g2012','-s','counter_check_tb','-o',str(target/'sim'),*paths,str(checker)],capture_output=True,text=True,timeout=120)
    (target/'compile.log').write_text(compile_result.stdout+compile_result.stderr)
    passed=False
    if compile_result.returncode==0:
        result=subprocess.run(['vvp',str(target/'sim')],capture_output=True,text=True,timeout=120)
        (target/'acceptance.log').write_text(result.stdout+result.stderr)
        passed=result.returncode==0 and 'COUNTER_CHECK_PASS checks=2051' in result.stdout
    rows.append({'trial':'counter-transfer','passed':passed})
    summary={'passed':all(row['passed'] for row in rows),'rows':rows,'model_calls':0,
        'physical_calls':0,'scope':'Saved-file hashes plus new independent Icarus/synthesis and original-IP data-cone checks; no AI/EDA-flow rerun'}
    write_json(output/'summary.json',summary)
    if not summary['passed']:raise RuntimeError('Offline replay failed; inspect retained results')
    print('OFFLINE_STUDY_REPLAY_PASS: twelve accelerator trials and fresh counter')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--results',type=Path,default=CASE/'results/configurable-study');args=parser.parse_args()
    run(args.output.resolve(),args.results.resolve())
