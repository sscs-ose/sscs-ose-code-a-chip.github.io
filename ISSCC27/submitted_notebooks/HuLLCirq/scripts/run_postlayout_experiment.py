"""Isolated original-job timed experiment; never changes adoption/history.

This development tool deliberately cannot produce an adopted S14 result. Its
complete raw command records and inputs qualify a future versioned adapter.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from hullcirq import physical_tools as physical
from hullcirq import postlayout_tools
from hullcirq.postlayout_testbench import timed_testbench, timed_testbench_v2
from hullcirq.verification import trusted_command, _wsl_path, object_hash


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + '\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--compiler-config', required=True)
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--testbench-version', choices=('1', '2'), default='2')
    parser.add_argument('--native-readback', action='store_true')
    parser.add_argument('--dump-all', action='store_true')
    args = parser.parse_args()
    compiler = physical.load(Path(args.compiler_config))
    config = physical.load(ROOT / '.work/m2j/postlayout_runtime.json')
    layout = physical.load(ROOT / 'results/npu_layout_continuous_flow/layout_record.json')
    inputs = postlayout_tools.source_inputs(layout, config)
    parent = ROOT / '.work/m2k/dynamic'; parent.mkdir(parents=True, exist_ok=True)
    folder = Path(tempfile.mkdtemp(prefix='original-job-', dir=parent))
    save(folder / 'source-binding.json', {'layout_id': layout['id'], 'revision_id': layout['revision_id'],
        'source_inputs': inputs, 'original_plan_sha256': object_hash(layout['verification_plan']),
        'purpose': 'finite original-job dynamic experiment; no adoption or automatic Passed',
        'original_job_changed': False})
    save(folder / 'verification-plan.json', layout['verification_plan'])
    save(folder / 'compiler-config.json', compiler)
    shutil.copyfile(Path(__file__), folder / 'orchestrator-source.py')
    shutil.copyfile(ROOT / 'src/hullcirq/postlayout_testbench.py', folder / 'testbench-source.py')
    base = Path(layout['checks']['artifacts_directory'])
    for key, name in (('netlist','input.nl.v'), ('sdf','input.sdf')):
        shutil.copyfile(base / inputs[key]['relative_path'], folder / name)
        assert physical.sha(folder / name) == inputs[key]['sha256']
    pdk = Path(config['pdk_root'])
    raw = (pdk / inputs['cell_models']['relative_path']).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == inputs['cell_models']['sha256']
    (folder / 'original-cell-models.v').write_bytes(raw)
    save(folder / 'native-capture-contract.json', {
        'kind': 'icarus13-native-zero-offset-delayed-inputs-finite-trace-v1',
        'original_models_changed': False, 'original_sdf_changed': False,
        'offset_ps': 0, 'general_negative_timing_model_equivalence': False,
        'native_timing_checks_supported': False,
        'qualification_required': 'independently audit every signed check and capture stability through raw clock edge',
        'violating_or_ambiguous_trace_adoptable': False})
    shutil.copyfile(pdk / inputs['primitives']['relative_path'], folder / 'primitives.v')
    assert physical.sha(folder / 'primitives.v') == inputs['primitives']['sha256']
    adapter = timed_testbench_v2 if args.testbench_version == '2' else timed_testbench
    tb, metadata = adapter(layout['verification_plan'], layout['settings'])
    sdf = (folder / 'input.sdf').read_text(encoding='utf-8')
    cells = re.findall(r'\(CELLTYPE "sky130_fd_sc_hd__dfxtp_2"\)\s*\(INSTANCE ([A-Za-z_][A-Za-z_0-9]*)\)', sdf)
    assert len(cells) == len(set(cells)) == 1991
    dumps = '    $dumpvars(0, dut);' if args.dump_all else '\n'.join(f'    $dumpvars(1, dut.{cell});' for cell in cells)
    needle = '    $dumpfile("simulation.vcd");'
    assert tb.count(needle) == 1
    tb = tb.replace(needle, needle + '\n' + dumps)
    (folder / 'timed-testbench.v').write_bytes(tb.encode('utf-8'))
    save(folder / 'testbench-adapter.json', {**metadata, 'original_candidate_sha256': metadata['timed_testbench_sha256'],
        'timing_pin_dump_cells': cells, 'timing_pin_dump_count': len(cells), 'dump_all_hierarchy': args.dump_all,
        'executed_testbench_raw_sha256': physical.sha(folder / 'timed-testbench.v')})
    if args.native_readback:
        plugin = ROOT / '.work/m2k/simulator_research/native_readback'
        for source, name in ((plugin/'hullcirq_readback.vpi','hullcirq_readback.vpi'),
                             (plugin/'hullcirq_readback.c','hullcirq_readback.c'),
                             (plugin/'original_iopath_inventory/sdf-readback-manifest.tsv','sdf-readback-manifest.tsv')):
            shutil.copyfile(source, folder / name)
    print(json.dumps({'folder': str(folder), 'prepared': True}), flush=True)
    if args.prepare_only:
        return
    binary = compiler['executable']
    command = trusted_command(compiler, binary,
        ['-B', compiler['base_directory'], '-g2005', '-gspecify', '-ginterconnect', '-Ttyp',
         '-s', 'hullcirq_global_tb', '-o', 'simulation.vvp', 'primitives.v',
         'original-cell-models.v', 'input.nl.v', 'timed-testbench.v'], folder)
    from hullcirq.postlayout_execution import execute
    worker_version = 'v2' if args.native_readback else 'v1'
    compiled = execute(command, compiler, folder, 'compile', None, 300, worker_version=worker_version)
    save(folder / 'compile-execution.json', compiled)
    if compiled.get('exit_code') != 0 or not (folder / 'simulation.vvp').is_file() or compiled.get('cleanup_unresolved'):
        print(json.dumps({'compile': compiled.get('status'), 'exit_code': compiled.get('exit_code'), 'folder': str(folder)}), flush=True)
        return
    vvp_args = (['-M', _wsl_path(folder), '-m', 'hullcirq_readback', 'simulation.vvp', '-sdf-verbose',
                 '+hullcirq_readback_manifest=sdf-readback-manifest.tsv'] if args.native_readback else
                ['-M', compiler['base_directory'], 'simulation.vvp', '-sdf-verbose'])
    command = trusted_command(compiler, str(Path(binary).with_name('vvp')).replace('\\','/'), vvp_args, folder)
    simulated = execute(command, compiler, folder, 'simulate', None, 900, worker_version=worker_version)
    save(folder / 'simulation-execution.json', simulated)
    print(json.dumps({'folder': str(folder), 'simulation_exit': simulated.get('exit_code'),
        'cleanup_unresolved': simulated.get('cleanup_unresolved'),
        'has_global_pass_marker': 'HULLCIRQ_GLOBAL_PASS outputs=16' in simulated.get('stdout',''),
        'S14_adopted': False, 'qualification': 'must independently audit annotation, signed timing and every observed capture'}), flush=True)


if __name__ == '__main__':
    main()
