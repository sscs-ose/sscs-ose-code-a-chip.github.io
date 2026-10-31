"""Replay the public fixture with independent stage/RF observations."""
import json
from pathlib import Path
import os
import subprocess

ROOT = Path.cwd()
FIXED = ROOT/'.nebula_inputs/authorized-common-verifier-resources/verification/fixed_common'
rows = []
for config in ['base', 'enabled']:
    out = ROOT/f'build/verify/pipeline-{config}'
    out.mkdir(exist_ok=False)
    env = dict(os.environ, NEBULA_VERIFY_CONFIG=config)
    sources = (ROOT/'verification/design.f').read_text().splitlines()
    cmd = ['verilator','--binary','--timing','--assert','-Wno-fatal','-j','4',
           '--top-module','tb_T09','--Mdir',str(out/'obj'),
           *[str(ROOT/p) for p in sources],
           str(FIXED/'verification/benchmark/evaluator/public/tb_T09.sv'),
           '-I'+str(FIXED/'verification/benchmark'),str(ROOT/'tb/pipeline_observer.sv')]
    compiled = subprocess.run(cmd, env=env, text=True, capture_output=True)
    (out/'compile.log').write_text(compiled.stdout+compiled.stderr)
    assert compiled.returncode == 0, compiled.stderr
    executed = subprocess.run([str(out/'obj/Vtb_T09')], cwd=out, env=env, text=True, capture_output=True)
    (out/'run.log').write_text(executed.stdout+executed.stderr)
    assert executed.returncode == 0 and 'PUBLIC_PASS T09 retired=64' in executed.stdout
    trace = [json.loads(line) for line in (out/'pipeline.jsonl').read_text().splitlines()]
    commits = [r for r in trace if r['commit_valid']]
    assert len(commits) == 64 and all(r['rf_write'] for r in commits)
    rows.append({'configuration':config,'passed':True,'retirements':len(commits),
                 'actual_stage_and_rf_alignment':'asserted at every rising edge after NBA',
                 'trace':str((out/'pipeline.jsonl').relative_to(ROOT))})
(ROOT/'reports/verification/pipeline.json').write_text(json.dumps({'passed':True,'rows':rows},indent=2)+'\n')
print('PIPELINE_OBSERVER_PASS configurations=2 retirements=128')
