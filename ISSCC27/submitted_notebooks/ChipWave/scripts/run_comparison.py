#!/usr/bin/env python3
"""Five paired, same-model NPU trials: direct Codex versus ChipWave.

This scoped pilot does not measure CPU design success or prove a general
platform advantage. All trials receive the same contract and public checker;
the same separately frozen final checker measures the resulting RTL.
"""
from __future__ import annotations
import concurrent.futures
import argparse
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path
import yaml
from chip_nebula.taskgraph.domain import Artifact, ArtifactContent, ArtifactProducer
from chip_nebula.taskgraph.static_store import StaticTaskGraphStore

ENTRY = Path(__file__).resolve().parents[1]
RUN_ROOT = ENTRY
MODEL, BUDGET = 'gpt-6.1-sol', 600
CONTRACT = '''Design fresh original synthesizable SystemVerilog for nebula_npu_dot4.
Ports: input clk,rst_n,req_valid; output req_ready; input [31:0] req_a,req_b;
output rsp_valid; input rsp_ready; output [31:0] rsp_data; input kill.
Compute the signed INT32 sum of four signed INT8 products, lane0 in bits7:0.
Widen products before reducing. Accept at edge n on req_valid&&req_ready,
assert result after edge n+2, hold valid/data until consumed. At most one
operation is outstanding. Reset and kill dominate all acceptance and output,
cancel pending work, and allow correct recovery. No hidden accumulator,
memory, saturation or rounding. Use four parallel multipliers.
'''
PROMPT = '''Implement spec/npu.md under rtl/ only. Develop and repair using
python3 tools/smoke.py; the checker is immutable. Write only rtl/** and build/**.
Do not read other trials, supplied implementations, evaluator references or
parent projects. Do not spawn agents or make subordinate model calls.
Use the installed Icarus/Verilator and Python. No external IP is permitted in
either treatment. The total trial budget, including planning and checking,
is 600 seconds. Finish with NEBULA_OUTPUT: {"rtl":{"module":"nebula_npu_dot4"}}.
'''


def command(args, cwd, timeout=30):
    return subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=True, timeout=timeout).stdout


def prepare(root, mode):
    for name in ('spec', 'rtl', 'tb', 'tools'):
        (root / name).mkdir(parents=True, exist_ok=True)
    (root / 'spec/npu.md').write_text(CONTRACT)
    shutil.copy2(ENTRY / 'generation_seed/tb/npu_smoke_tb.sv', root / 'tb/npu_smoke_tb.sv')
    script = '''from pathlib import Path
import subprocess
root=Path.cwd();out=root/'build';out.mkdir(exist_ok=True)
sources=sorted((root/'rtl').glob('*.sv'))+sorted((root/'rtl').glob('*.v'))
if not sources:raise RuntimeError('missing RTL')
subprocess.run(['iverilog','-g2012','-s','npu_smoke_tb','-o',str(out/'smoke'),*map(str,sources),'tb/npu_smoke_tb.sv'],check=True)
r=subprocess.run(['vvp',str(out/'smoke')],text=True,capture_output=True,timeout=60)
(out/'smoke.log').write_text(r.stdout+r.stderr);print(r.stdout,end='')
if r.returncode or 'NPU_SMOKE_PASS' not in r.stdout:raise RuntimeError('public smoke failed')
'''
    (root / 'tools/smoke.py').write_text(script)
    (root / '.gitignore').write_text('.chip_nebula/\nbuild/\n__pycache__/\n*.pyc\n')
    command(['git', 'init', '-q'], root)
    command(['git', 'config', 'user.name', 'ChipWave comparison automation'], root)
    command(['git', 'config', 'user.email', 'automation@chipwave.invalid'], root)
    command(['git', 'add', '.'], root)
    command(['git', 'commit', '-qm', 'Freeze common NPU trial input'], root)
    if mode == 'platform':
        roles, recipes = root / '.chip_nebula/roles', root / '.chip_nebula/recipes'
        roles.mkdir(parents=True); recipes.mkdir(parents=True)
        role = dict(name='comparison-npu', version=1, system_prompt=PROMPT,
                    accepted_types=['specification.source'], produced_types=['rtl.snapshot'],
                    framework='codex', model=MODEL)
        tool_role = dict(name='comparison-public-auditor', version=1,
                        system_prompt='Replay the immutable public checker and retain its actual verdict.',
                        accepted_types=['rtl.snapshot'], produced_types=['verification.report'],
                        framework='codex', model=MODEL)
        (roles / 'comparison-npu.yaml').write_text(yaml.safe_dump(role, sort_keys=False))
        (roles / 'comparison-public-auditor.yaml').write_text(yaml.safe_dump(tool_role, sort_keys=False))
        audit = '''import subprocess,json
from pathlib import Path
r=subprocess.run(['python3','tools/smoke.py'],text=True,capture_output=True)
out=Path('build');out.mkdir(exist_ok=True);(out/'audit.log').write_text(r.stdout+r.stderr)
report={'subject':'generated-rtl','verdict':'passed' if r.returncode==0 else 'failed','log':'build/audit.log'}
(out/'audit.json').write_text(json.dumps(report,indent=2)+'\\n')
print('NEBULA_OUTPUT: '+json.dumps({'report':report}))
'''
        (root / 'tools/audit.py').write_text(audit)
        recipe = dict(name='controlled-npu-pilot', version=2, planner=dict(framework='codex', model=MODEL),
                      parameters={'source': 'specification.source'}, tasks={
            'design': dict(role='comparison-npu', intent=PROMPT,
                permission=dict(read=['spec/**','tb/**','tools/smoke.py','rtl/**','build/**'], write=['rtl/**','build/**'], tools=['python3','git','iverilog','vvp','verilator']),
                inputs={'source':dict(type='specification.source', **{'from':'$parameters.source'})},
                outputs={'rtl':dict(type='rtl.snapshot',paths=['rtl/**'])}, max_attempts=1,
                execution=dict(framework='codex',model=MODEL,reasoning_effort='high',timeout_seconds=BUDGET),
                gates=[dict(name='common-public-smoke',template='script-check',version=1,on_failure='report',parameters=dict(script='python3',arguments=['tools/smoke.py'],expected='NPU_SMOKE_PASS',timeout=120,level='L1',error_class='public_smoke_failed'))]),
            'audit': dict(role='comparison-public-auditor',intent='Independently replay public checks on the selected design Delivery. Report genuine passed or failed; no RTL/checker changes.',
                permission=dict(read=['rtl/**','tb/**','tools/**'],write=['build/**'],tools=['python3','iverilog','vvp']),
                inputs={'rtl':dict(type='rtl.snapshot',**{'from':'$tasks.design.outputs.rtl'})},
                outputs={'report':dict(type='verification.report',paths=['build/audit.json','build/audit.log'])},max_attempts=1,
                execution=dict(executor='tool',command='python3 tools/audit.py',timeout_seconds=120))})
        (recipes / 'comparison.yaml').write_text(yaml.safe_dump(recipe,sort_keys=False))
        command(['git','add','tools/audit.py'],root)
        command(['git','add','-f','.chip_nebula/roles','.chip_nebula/recipes'],root)
        command(['git','commit','-qm','Freeze platform treatment configuration'],root)
        commit = command(['git','rev-parse','HEAD'],root).strip()
        tree = command(['git','rev-parse','HEAD^{tree}'],root).strip()
        artifact = Artifact(id='comparison-source',type='specification.source',schema_version=1,
            producer=ArtifactProducer('external','common-input','common-input','comparison-author',1),
            content=ArtifactContent('git',commit,tree,('spec/npu.md',)),
            payload=dict(source_name='common NPU contract',media_type='text/markdown',
                         content_digest='sha256:'+hashlib.sha256(CONTRACT.encode()).hexdigest(),
                         content=CONTRACT,received_at='2026-10-12T12:00:00+00:00'))
        with StaticTaskGraphStore(root/'.chip_nebula/shared/memory/taskgraph-v2.db') as store:
            store.register_evidence_artifacts([artifact])
        command(['git','update-ref','refs/chip-nebula/artifacts/comparison-source',commit],root)
    return command(['git','rev-parse','HEAD'],root).strip()


def final_check(root, mode, workflow, out):
    if mode=='platform':
        from export_snapshot import export
        source=out/'selected'
        export(root,workflow,'design','rtl',source)
    else:
        source=root
    sources=sorted(source.glob('rtl/**/*.sv'))+sorted(source.glob('rtl/**/*.v'))
    if not sources: return {'passed':False,'reason':'no RTL'}
    compiled=subprocess.run(['iverilog','-g2012','-s','npu_acceptance_tb','-o',str(out/'acceptance'),*map(str,sources),str(ENTRY/'verification/npu_acceptance_tb.sv')],text=True,capture_output=True,timeout=60)
    (out/'final-compile.log').write_text(compiled.stdout+compiled.stderr)
    if compiled.returncode:return {'passed':False,'reason':'final checker compilation failed'}
    result=subprocess.run(['vvp',str(out/'acceptance')],text=True,capture_output=True,timeout=120)
    (out/'final-run.log').write_text(result.stdout+result.stderr)
    return dict(passed=result.returncode==0 and 'NPU_ACCEPTANCE_PASS cases=264202 cancellations=8' in result.stdout,
                source_sha256={str(p.relative_to(source)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources})


def trial(mode, number):
    root=RUN_ROOT/'comparison'/f'{mode}-{number}'
    if root.exists(): raise ValueError(f'existing trial preserved: {root}')
    root.mkdir(parents=True)
    baseline=prepare(root,mode)
    out=RUN_ROOT/'results/comparison'/f'{mode}-{number}';out.mkdir(parents=True)
    workflow=f'npu-pilot-{number}'
    if mode=='platform':
        args=[sys.executable,'-m','chip_nebula.cli.commands','--project-root',str(root),'run',str(root/'.chip_nebula/recipes/comparison.yaml'),
              '--workflow',workflow,'--baseline',baseline,'--param','source=comparison-source','--workers','1']
        input_text=None
    else:
        args=['codex','exec','--json','--dangerously-bypass-approvals-and-sandbox','-m',MODEL,
              '-c','model_reasoning_effort="high"','-C',str(root),'-']
        input_text=PROMPT
    frozen={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [root/'spec/npu.md',root/'tb/npu_smoke_tb.sv',root/'tools/smoke.py']}
    start=time.monotonic();deadline=False
    with (out/'agent.log').open('w') as log:
        proc=subprocess.Popen(args,stdin=subprocess.PIPE if input_text else subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,text=True)
        try:proc.communicate(input=input_text,timeout=BUDGET)
        except subprocess.TimeoutExpired:
            deadline=True
            if mode=='platform':
                with StaticTaskGraphStore(root/'.chip_nebula/shared/memory/taskgraph-v2.db') as store:
                    store.request_workflow_stop(workflow,'preregistered 600-second comparison deadline')
            proc.terminate()
            try:proc.wait(timeout=30)
            except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
    elapsed=time.monotonic()-start
    unchanged=all(hashlib.sha256((root/p).read_bytes()).hexdigest()==digest for p,digest in frozen.items())
    try:verdict=final_check(root,mode,workflow,out) if not deadline and unchanged else dict(passed=False,reason='deadline or frozen input change')
    except Exception as error:verdict=dict(passed=False,reason=f'{type(error).__name__}: {error}')
    row=dict(mode=mode,trial=number,model=MODEL,reasoning_effort='high',budget_seconds=BUDGET,
             elapsed_seconds=round(elapsed,3),deadline=deadline,returncode=proc.returncode,
             immutable_inputs_unchanged=unchanged,final_checker=verdict,
             input_sha256=frozen,passed=verdict['passed'],baseline=baseline)
    (out/'result.json').write_text(json.dumps(row,indent=2)+'\n')
    print(json.dumps({k:row[k] for k in ('mode','trial','passed','elapsed_seconds','deadline')}),flush=True)
    return row


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True,help='New directory for all fresh trials and results; preserves packaged measurements')
    RUN_ROOT=parser.parse_args().output.resolve()
    if RUN_ROOT.exists():raise ValueError('choose a new pilot output directory; existing work is preserved')
    RUN_ROOT.mkdir(parents=True)
    rows=[]
    # Paired alternating order; at most two trials run alongside the main EDA flow.
    jobs=[(mode,i) for i in range(1,6) for mode in (('direct','platform') if i%2 else ('platform','direct'))]
    preregistration=dict(scope='fresh NPU RTL only, not a CPU/GDS reliability comparison',
        trials_per_treatment=5,model=MODEL,reasoning_effort='high',total_trial_budget_seconds=BUDGET,
        contract=CONTRACT,prompt=PROMPT,external_ip=False,public_checker='64-vector development smoke',
        final_checker='264202 frozen cases and 8 cancellation checks',
        final_checker_sha256=hashlib.sha256((ENTRY/'verification/npu_acceptance_tb.sv').read_bytes()).hexdigest(),
        outcome='all scheduled trials retained, including failures and deadlines',jobs=jobs)
    folder=RUN_ROOT/'results/comparison';folder.mkdir(parents=True,exist_ok=True)
    (folder/'preregistration.json').write_text(json.dumps(preregistration,indent=2)+'\n')
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(trial,*job) for job in jobs]
        for future in concurrent.futures.as_completed(futures):
            rows.append(future.result())
            (folder/'summary.json').write_text(json.dumps({'complete':len(rows)==10,'rows':rows},indent=2)+'\n')
