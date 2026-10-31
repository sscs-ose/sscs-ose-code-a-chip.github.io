"""Compile once, run independent numerical/protocol checks; never edits RTL."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

from vectors import dot, generate, legal_maps


def run(cmd,log,timeout=180):
    start=time.monotonic()
    result=subprocess.run(cmd,capture_output=True,text=True,timeout=timeout)
    log.write_text(result.stdout+result.stderr)
    if result.returncode: raise RuntimeError(f'command failed: {log}')
    return result.stdout,time.monotonic()-start


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--quick',action='store_true')
    parser.add_argument('--output',type=Path,default=Path('build/verify'))
    parser.add_argument('--rtl',type=Path,default=Path('rtl/lb_feedback.sv'))
    args=parser.parse_args()
    out=args.output;out.mkdir(parents=True,exist_ok=True)
    frozen_files=[args.rtl,Path('spec/contract.md'),Path('scripts/verify.py'),Path('scripts/vectors.py'),Path('verif/tb_lb.sv')]
    input_hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in frozen_files}
    assert len(legal_maps())==73
    assert dot([-128]*4,[[127]*8 for _ in range(4)],4)==[-65024]*8
    tb=Path('verif/tb_lb.sv')
    compile_cmd=[os.environ.get('IVERILOG_EXE','iverilog'),'-g2012','-s','tb_lb','-o',str(out/'sim'),str(args.rtl),str(tb)]
    run(compile_cmd,out/'compile.log')
    cases=[];seeds=[11] if args.quick else [11,29,47,71,97]
    count=12 if args.quick else 1000
    def traffic(seed,count,mapping,name,extra=()):
        vector_file=out/f'vectors-{name}.txt';generate(vector_file,seed,count,first_k=64 if name=='reset' else None)
        rows=vector_file.read_text().splitlines()
        vector_file.write_text('\n'.join(' '.join([p[0],str(mapping),*p[2:]]) for p in (r.split() for r in rows))+'\n')
        text,seconds=run([os.environ.get('VVP_EXE','vvp'),str(out/'sim'),f'+vectors={vector_file}',f'+seed={seed}',f'+count={count}',*extra],out/f'{name}.log')
        if f'LB_TRAFFIC_PASS tasks={count}' not in text:raise RuntimeError('no traffic pass marker: '+name)
        return dict(name=name,seed=seed,tasks=count,mapping=mapping,seconds=seconds,
            latency_cycles=[int(x) for x in re.findall(r'LB_LATENCY job=\d+ cycles=(\d+)',text)],
            cycles=int(re.search(r'LB_TRAFFIC_PASS tasks=\d+ seed=\d+ cycles=(\d+)',text)[1]))
    for seed in seeds:
        mapping=legal_maps()[seed%73]
        cases.append(traffic(seed,count,mapping,f'traffic-{seed}'))
    if not args.quick:
        text,seconds=run([os.environ.get('VVP_EXE','vvp'),str(out/'sim'),'+config_only=1'],out/'configuration.log',timeout=600)
        if 'LB_CONFIG_PASS encodings=65536' not in text:raise RuntimeError('missing exhaustive config pass')
        if 'LB_CONFIG_BAD_PASS cases=730' not in text or 'LB_LOCK_PASS cases=73' not in text:
            raise RuntimeError('missing bad-target/lock checks')
        cases.append(dict(configuration_encodings=65536,bad_target_cases=730,locked_commit_cases=73,seconds=seconds))
        for index,mapping in enumerate(legal_maps()):
            cases.append(traffic(100+index,3,mapping,f'mapping-{index}'))
        cases.append(traffic(71,2,0,'overlap',['+overlap=1']))
        cases.append(traffic(71,2,0,'reset',['+reset_probe=1']))
        cases.append(traffic(47,30,0,'unloaded',['+unloaded=1']))
        negatives=[]
        for fault in ['fault_data','fault_swap','fault_drop']:
            log=out/(fault+'.log')
            cmd=[os.environ.get('VVP_EXE','vvp'),str(out/'sim'),f'+vectors={out}/vectors-traffic-11.txt','+seed=11',f'+count={count}','+'+fault+'=1']
            result=subprocess.run(cmd,capture_output=True,text=True,timeout=180)
            log.write_text(result.stdout+result.stderr)
            if result.returncode==0 or not any(marker in log.read_text() for marker in ['NUMERIC mismatch','result timeout']):
                raise RuntimeError('checker did not detect '+fault)
            negatives.append(dict(fault=fault,detected=True,returncode=result.returncode))
        cases.append(dict(checker_negative_controls=negatives))
    if input_hashes!={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in frozen_files}:
        raise RuntimeError('DUT or independent checker changed during execution; no qualified result')
    summary=dict(schema_version=1,verdict='passed',scope='quick diagnostic' if args.quick else 'pre-synthesis independent functional/protocol/performance checks; physical obligations remain separate',
        source_sha256=hashlib.sha256(args.rtl.read_bytes()).hexdigest(),cases=cases,
        input_hashes=input_hashes,
        tests_total=sum(x.get('tasks',x.get('configuration_encodings',0)) for x in cases),
        deferred=['all-legal-mapping traffic','ping-pong overlap','reset during traffic','fault-injection self-checks','unloaded throughput'] if args.quick else [],
        post_synthesis_obligations=['netlist consistency','physical implementation and GDS'])
    (out/'verification.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k not in {'cases','input_hashes'}}))


if __name__=='__main__': main()
