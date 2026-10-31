"""One consolidated frozen-checker regression, with evidence retained on failure."""
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import time

ROOT = Path.cwd()
FIXED = ROOT/'.nebula_inputs/authorized-common-verifier-resources/verification/fixed_common'
OUT = ROOT/'build/verify/regression'
manifest = json.loads((FIXED/'fixed-files.json').read_text())
assert all(hashlib.sha256((FIXED/p).read_bytes()).hexdigest() == h for p, h in manifest.items())
reports = ROOT/'reports/verification'
reports.mkdir(parents=True,exist_ok=True)
(reports/'fixed-before.json').write_text(json.dumps({'verdict':'passed','files':len(manifest),
    'manifest_sha256':hashlib.sha256((FIXED/'fixed-files.json').read_bytes()).hexdigest(),'mismatches':[]},indent=2)+'\n')
VIEW = ROOT/'build/verify/candidate'
paths = (ROOT/'integration/design.f').read_text().splitlines()
assert paths and len(paths) == len(set(paths))
integration_id = json.loads((ROOT/'.nebula_inputs/attempt-context.json').read_text())['input_deliveries']['integration']
integration_record = json.loads((ROOT/'.nebula_inputs'/integration_id/'artifact.json').read_text())
integration_commit = integration_record['content']['commit']
for name in paths:
    data = (ROOT/name).read_bytes()
    frozen = subprocess.check_output(['git', 'show', integration_commit+':'+name])
    assert data == frozen, name
    target = VIEW/name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
(reports/'candidate-view.json').write_text(json.dumps({'rtl_commit':integration_commit,
    'sources':[{'source':p,'sha256':hashlib.sha256((ROOT/p).read_bytes()).hexdigest(),'byte_equal':True} for p in paths]},indent=2)+'\n')
(VIEW/'rtl/files.f').write_text(''.join(str(Path(p).relative_to('rtl'))+'\n' for p in paths))
OUT.mkdir(parents=True, exist_ok=False)
EVAL = FIXED/'verification/benchmark/evaluator'
rows = []

def execute(name, command, config='base', timeout=2400):
    env = dict(os.environ, NEBULA_VERIFY_CONFIG=config)
    log = OUT/f'{name}.log'
    started = time.time()
    try:
        result = subprocess.run(list(map(str, command)), text=True, capture_output=True,
                                env=env, timeout=timeout)
        log.write_text(result.stdout+result.stderr)
        row = dict(name=name, command=shlex.join(list(map(str, command))), configuration=config,
                   returncode=result.returncode, log=str(log.relative_to(ROOT)),
                   elapsed_seconds=time.time()-started)
    except subprocess.TimeoutExpired as exc:
        log.write_bytes((exc.stdout or b'')+(exc.stderr or b''))
        row = dict(name=name, command=shlex.join(list(map(str, command))), configuration=config,
                   returncode=None, status='timeout', log=str(log.relative_to(ROOT)))
    rows.append(row)
    (OUT/'commands.json').write_text(json.dumps(rows, indent=2)+'\n')
    print(name, row['returncode'], flush=True)
    return row['returncode'] == 0

runtime = {'shell_pid': os.environ['NEBULA_VERIFY_SHELL_PID'], 'runner_pid': os.getpid(),
           'source_order': ['/tmp/chipnebula-pinned-tools/env.sh', '/opt/rh/gcc-toolset-13/enable'],
           'source_status': [int(os.environ['NEBULA_VERIFY_ENV1_STATUS']), int(os.environ['NEBULA_VERIFY_ENV2_STATUS'])],
           'verilator_path': shutil.which('verilator'),
           'verilator_version': subprocess.check_output(['verilator', '--version'], text=True).strip(),
           'python': sys.version, 'workflow_wall_time_available': False,
           'workflow_wall_time_reason': 'Captured input records provide no workflow launch/time accounting receipt; functional score only.'}
runtime['verilator_sha256'] = hashlib.sha256(Path(runtime['verilator_path']).read_bytes()).hexdigest()
assert runtime['source_status'] == [0, 0] and runtime['verilator_version'].startswith('Verilator 5.048 ')
(ROOT/'reports/verification/runtime.json').write_text(json.dumps(runtime, indent=2)+'\n')

# The fixed evaluator supplies the base population. Equivalent enabled bindings
# repeat that same population, rather than adding invented CPU requirements.
started = time.time()
for config in ['base', 'enabled']:
    elapsed = time.time()-started
    execute(f't09-{config}', [sys.executable, EVAL/'t09_check.py', VIEW,
            '--elapsed-seconds', str(elapsed), '--output', OUT/f't09-{config}.json'], config)

execute('kernels', [sys.executable, FIXED/'scripts/run_kernels.py', '--project', VIEW,
                    '--output', ROOT/'build/perf/kernels'])
execute('custom-reset', [sys.executable, FIXED/'scripts/run_custom_reset.py', '--project', VIEW,
                         '--output', OUT/'custom-reset'])
sources = [VIEW/'rtl'/line for line in (VIEW/'rtl/files.f').read_text().splitlines()]
for top, parameter in [('custom_traps_tb', 0), ('custom_traps_tb', 1), ('precise_custom_tb', None)]:
    name = top + (f'-{parameter}' if parameter is not None else '')
    obj = OUT/name
    args = ['verilator', '--binary', '--timing', '--assert', '-Wno-fatal', '-j', '4',
            '--top-module', top, '--Mdir', obj, *sources, FIXED/f'verification/{top}.sv']
    if parameter is not None:
        args.append(f'-GENABLE={parameter}')
    if execute(name+'-compile', args):
        execute(name+'-run', [obj/f'V{top}'], timeout=180)

obj = OUT/'npu-sim'
if execute('npu-compile', ['iverilog', '-g2012', '-s', 'npu_acceptance_tb', '-o', obj,
                         VIEW/'rtl/nebula_npu_dot4.sv', FIXED/'verification/npu_acceptance_tb.sv']):
    execute('npu-run', ['vvp', obj], timeout=180)

execute('integration-smoke-compile', ['verilator', '--binary', '--timing', '--assert', '-Wno-fatal',
        '-j', '4', '--top-module', 'integration_smoke_tb', '--Mdir', OUT/'integration-smoke',
        *sources, ROOT/'integration/integration_smoke_tb.sv'])
if rows[-1]['returncode'] == 0:
    execute('integration-smoke-run', [OUT/'integration-smoke/Vintegration_smoke_tb'], timeout=180)
execute('pipeline-observer', [sys.executable, ROOT/'verification/run_pipeline.py'])
execute('structure', [sys.executable, ROOT/'verification/check_structure.py'])
if execute('npu-cancel-compile', ['iverilog','-g2012','-s','npu_cancellation_edges_tb',
        '-o',ROOT/'build/verify/npu-cancellation-edges',VIEW/'rtl/nebula_npu_dot4.sv',
        ROOT/'tb/npu_cancellation_edges_tb.sv']):
    execute('npu-cancel-run',['vvp',ROOT/'build/verify/npu-cancellation-edges'])
stale=[]
for enabled in [0,1]:
    obj=ROOT/f'build/verify/stale-fetch-{enabled}'
    if execute(f'stale-fetch-{enabled}-compile',['verilator','--binary','--timing','--assert','-Wno-fatal','-j','4',
            '--top-module','stale_fetch_tb',f'-GENABLE={enabled}','--Mdir',obj,*sources,ROOT/'tb/stale_fetch_tb.sv']):
        passed=execute(f'stale-fetch-{enabled}-run',[obj/'Vstale_fetch_tb'])
        shutil.copyfile(ROOT/rows[-1]['log'],reports/f'stale-fetch-{enabled}-run.log')
        stale.append({'enabled':enabled,'passed':passed,'cases':6})
(reports/'stale-fetch.json').write_text(json.dumps({'passed':len(stale)==2 and all(r['passed'] for r in stale),'rows':stale},indent=2)+'\n')

manifest = json.loads((FIXED/'fixed-files.json').read_text())
mismatches = [p for p, h in manifest.items() if hashlib.sha256((FIXED/p).read_bytes()).hexdigest() != h]
(ROOT/'reports/verification/fixed-after.json').write_text(json.dumps(
    {'verdict': 'failed' if mismatches else 'passed', 'files': len(manifest), 'mismatches': mismatches}, indent=2)+'\n')
assert not mismatches
print('REGRESSION_COMPLETED commands='+str(len(rows)), flush=True)
