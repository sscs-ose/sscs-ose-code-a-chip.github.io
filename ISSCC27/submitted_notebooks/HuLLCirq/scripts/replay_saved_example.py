#!/usr/bin/env python3
"""Inspect or re-simulate the exact saved P1 RTL and S10 generic netlist.

Default: read-only input validation. --run explicitly starts Icarus/vvp only.
All new execution output goes below ignored .work; no saved adoption is changed.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
from hullcirq.verification import validate_plan, trusted_command, execute_fixed, _wsl_path
from hullcirq.generic_verification import parse_cycle_runtime

CASE = ROOT / 'submission/reproduction/p1_counter'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load_inputs(case=CASE):
    provenance = json.loads((case / 'provenance.json').read_text(encoding='utf-8'))
    if set(provenance['files']) != {'release_counter.v','release_counter_top.v','global_netlist.v','contract_tb.v','verification-plan.json','public-vectors.json'}:
        raise ValueError('The fixed reproduction input set changed.')
    for name, pin in provenance['files'].items():
        if name in ('.', '..') or not re.fullmatch(r'[A-Za-z0-9_.-]+', name):
            raise ValueError('Unsafe reproduction filename.')
        if (case / name).is_symlink() or not (case / name).resolve().is_relative_to(case.resolve()):
            raise ValueError('Linked or escaping reproduction input.')
        data = (case / name).read_bytes()
        if len(data) != pin['bytes'] or sha(data) != pin['sha256']:
            raise ValueError('Saved reproduction input changed: ' + name)
    plan = json.loads((case / 'verification-plan.json').read_text(encoding='utf-8'))
    validate_plan(plan)
    if json.loads((case / 'public-vectors.json').read_text(encoding='utf-8')) != plan['public_boundary_vectors']:
        raise ValueError('Public vectors no longer match the original frozen plan.')
    if (case / 'contract_tb.v').read_bytes() != plan['testbench'].encode('utf-8'):
        raise ValueError('Testbench no longer matches the frozen independent plan.')
    if (plan['vector_count'] != 14 or len(plan['reference_trace']) != 14
            or len(plan['signal_checks']) != 3 or provenance['required_output_samples'] != 42
            or plan['vector_hash'] != provenance['vector_hash']
            or plan['interface']['clock']['period_ns'] != 50):
        raise ValueError('The original cycle/expectation/clock contract changed.')
    history_root = ROOT / 'submission/evidence/p1_counter/history'
    histories = {}
    if set(provenance['source_histories']) != {'global_generation.json.gz','global_workflow.json.gz'}:
        raise ValueError('The fixed published-history source set changed.')
    for name, expected in provenance['source_histories'].items():
        raw = (history_root / name).read_bytes()
        if sha(raw) != expected:
            raise ValueError('Published source history changed: ' + name)
        histories[name] = json.loads(gzip.decompress(raw))
    job = next(x for x in histories['global_generation.json.gz']['jobs']
               if x['id'] == provenance['source_global_job_id'])
    run = next(x for x in histories['global_workflow.json.gz']['runs']
               if x['id'] == provenance['source_netlist_simulation_run_id'])
    if not all(x['validation_status'] == 'Passed' and x['review_status'] == 'Accepted' for x in (job, run)):
        raise ValueError('The retained sources are not the declared adopted records.')
    if run['global_job_id'] != job['id'] or run['verification_plan'] != plan:
        raise ValueError('Frozen source and verification-plan lineage mismatch.')
    if (case / 'release_counter_top.v').read_bytes() != job['rtl'].encode('utf-8'):
        raise ValueError('Global RTL differs from the adopted proposal.')
    if (case / 'global_netlist.v').read_bytes() != run['netlist'].encode('utf-8'):
        raise ValueError('Netlist differs from the actual S10 source.')
    nodes = run['source_manifest']['nodes']
    if len(nodes) != 1 or (case / 'release_counter.v').read_bytes() != nodes[0]['rtl'].encode('utf-8'):
        raise ValueError('Node RTL differs from the frozen adopted source.')
    return provenance, plan


def compiler_configuration(args):
    if args.compiler_config:
        config = json.loads(args.compiler_config.read_text(encoding='utf-8-sig'))
    elif args.fresh_runtime:
        # Same checkout/distribution binding as the public preparation helper.
        from fresh_runtime import host_root
        path = host_root(ROOT, args.distribution) / 'compiler.json'
        if not path.is_file():
            raise ValueError('Complete the first-use runtime setup in this checkout before --fresh-runtime.')
        config = json.loads(path.read_text(encoding='utf-8-sig'))
    else:
        executable = args.iverilog or shutil.which('iverilog')
        if not executable:
            raise ValueError('Install Icarus or select --fresh-runtime / --compiler-config / --iverilog.')
        config = {'kind':'native', 'executable':str(Path(executable).resolve())}
        if args.base_directory:
            config['base_directory'] = str(args.base_directory.resolve())
    executable = config.get('executable')
    if not isinstance(executable, str) or executable.replace('\\', '/').split('/')[-1].lower() not in ('iverilog', 'iverilog.exe'):
        raise ValueError('Only a trusted installed Icarus executable and its sibling vvp are supported.')
    if config.get('kind') not in ('native', 'wsl'):
        raise ValueError('Only native or explicit WSL Icarus configurations are supported.')
    return config


def run_replay(config, provenance, plan):
    parent = ROOT / '.work/saved-rtl-replay'
    parent.mkdir(parents=True, exist_ok=True)
    output = Path(tempfile.mkdtemp(prefix='p1-', dir=parent))
    report = {'created_at':datetime.now(timezone.utc).isoformat(),
              'method':'new_finite_zero_delay_replay_of_saved_sources',
              'source_run':provenance['source_netlist_simulation_run_id'],
              'vector_hash':plan['vector_hash'], 'clock_period_ns':50,
              'model_requests':0, 'new_synthesis_or_physical_runs':0,
              'historical_adoption_modified':False, 'commands':[], 'results':[]}
    executable = config['executable']
    base = ['-B', config['base_directory']] if config.get('base_directory') else []
    def command(exe, arguments, cwd, timeout=30):
        result = execute_fixed(trusted_command(config, exe, arguments, cwd), cwd, timeout=timeout)
        report['commands'].append(result)
        return result
    try:
        version = command(executable, [*base, '-V'], output, 10)
        version_text = version['stdout'] + version['stderr']
        if version['status'] != 'Completed' or version['exit_code'] != 0:
            raise ValueError('The trusted Icarus version query failed; inspect the local tool log. No circuit result was produced.')
        if 'Icarus Verilog version 12.' not in version_text:
            raise ValueError('This replay is qualified with Icarus Verilog 12.x; inspect the local version log.')
        report['compiler_version'] = next(x for x in version_text.splitlines() if 'Icarus Verilog version' in x)
        runtime = executable.rsplit('/', 1)[0] + '/vvp' if config['kind'] == 'wsl' else str(Path(executable).with_name('vvp.exe' if executable.lower().endswith('.exe') else 'vvp'))
        for mode, sources in [('rtl', ['release_counter.v','release_counter_top.v']), ('generic_netlist', ['global_netlist.v'])]:
            directory = output / mode
            directory.mkdir()
            for name in [*sources, 'contract_tb.v']:
                (directory / name).write_bytes((CASE / name).read_bytes())
            paths = [directory / x for x in [*sources,'contract_tb.v']]
            target = directory / 'simulation.vvp'
            convert = _wsl_path if config['kind'] == 'wsl' else lambda p:str(p.resolve())
            compiled = command(executable, [*base,'-g2005','-s',plan['testbench_module'],'-o',convert(target),*[convert(p) for p in paths]], directory)
            if compiled['status'] != 'Completed' or compiled['exit_code'] != 0:
                raise ValueError(mode + ' compilation failed; inspect local logs.')
            runtime_base = ['-M',config['base_directory']] if config.get('base_directory') else []
            simulated = command(runtime, [*runtime_base,convert(target)], directory)
            checked = parse_cycle_runtime(simulated['stdout'], plan, simulated['stderr'])
            if simulated['status'] != 'Completed' or simulated['exit_code'] != 0 or checked['validation_status'] != 'Passed':
                raise ValueError(mode + ' finite simulation failed; inspect local logs.')
            report['results'].append({'mode':mode,'validation_status':'Passed',
                                      'checked_output_samples':checked['checked_output_samples'],
                                      'required_output_samples':checked['required_output_samples'],
                                      'vector_count':checked['vector_count'],
                                      'mismatches':0,'missing':0})
        report['validation_status'] = 'Passed'
    except Exception as error:
        report['validation_status'] = 'Failed'
        report['error'] = str(error)
        raise
    finally:
        # These local logs can contain trusted host paths. Never publish .work.
        (output / 'local-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true', help='Explicitly compile and simulate; otherwise inspect saved inputs only.')
    choice=parser.add_mutually_exclusive_group()
    choice.add_argument('--compiler-config', type=Path, help='Trusted local Icarus profile, not a file supplied by the evidence archive.')
    choice.add_argument('--fresh-runtime', action='store_true', help='Use this checkout\'s prepared first-use Icarus profile.')
    choice.add_argument('--iverilog', help='Trusted installed native Icarus executable.')
    parser.add_argument('--base-directory', type=Path, help='Native Icarus library directory, when needed.')
    parser.add_argument('--distribution', default='Ubuntu', help='Same WSL distribution selected during first-use preparation.')
    args=parser.parse_args()
    provenance,plan=load_inputs()
    if not args.run:
        print(json.dumps({'input_integrity':'Passed','vector_count':14,'required_output_samples':42,
                          'clock_period_ns':50,'model_requests':0,'simulator_started':False},indent=2))
        return 0
    report=run_replay(compiler_configuration(args),provenance,plan)
    print(json.dumps({k:v for k,v in report.items() if k not in ('commands','error')},indent=2))
    return 0


if __name__=='__main__':
    try:
        raise SystemExit(main())
    except (ValueError, OSError, KeyError, StopIteration) as error:
        print('Replay did not pass: ' + str(error),file=sys.stderr)
        raise SystemExit(1)
