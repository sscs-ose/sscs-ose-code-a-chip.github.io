"""Read-only audit of one completed original-job experiment; no adoption."""
from pathlib import Path
import argparse
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from hullcirq import physical_tools as physical
from hullcirq.sdf_interconnect import interconnect_inventory
from hullcirq.sdf_timing_audit import audit_sdf_timing
from hullcirq.verification import object_hash


def write_new(path, value):
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, allow_nan=False, indent=2)
        stream.write('\n')


def audit(folder, destination):
    """Raw evidence and finite functional checks, never an S14 approval gate."""
    folder = Path(folder).resolve(); destination = Path(destination).resolve()
    if not folder.is_relative_to((ROOT / '.work/m2k/dynamic').resolve()):
        raise ValueError('Use a retained isolated original-job experiment.')
    destination.mkdir(exist_ok=False)
    binding = physical.load(folder / 'source-binding.json')
    plan = physical.load(folder / 'verification-plan.json')
    assert object_hash(plan) == binding['original_plan_sha256']
    for key, name in (('netlist','input.nl.v'), ('sdf','input.sdf'),
                      ('cell_models','original-cell-models.v'), ('primitives','primitives.v')):
        assert physical.sha(folder / name) == binding['source_inputs'][key]['sha256']
    compiled = physical.load(folder / 'compile-execution.json')
    simulated = physical.load(folder / 'simulation-execution.json')
    for result in (compiled, simulated):
        assert result['executed'] is True and result['status'] == 'Completed'
        assert result['exit_code'] == 0 and result['cleanup_unresolved'] is False
        assert result['whole_process_group_terminated'] is True
    log = (folder / 'simulate/stdout.log').read_text(encoding='utf-8')
    observed = [(int(i), int(value), int(cycle)) for i, value, cycle in
                re.findall(r'^HULLCIRQ_OUTPUT index=(\d+) value=(-?\d+) cycle=(\d+)$', log, re.M)]
    expected_hex = re.findall(r"expected\[(\d+)\] = 32'h([0-9a-f]{8});", plan['testbench'])
    assert [int(index) for index, _ in expected_hex] == list(range(16))
    expected = [int(value,16) - (1 << 32) if int(value,16) >= (1 << 31) else int(value,16)
                for _, value in expected_hex]
    marker = f'HULLCIRQ_GLOBAL_PASS outputs=16 vector_hash={plan["vector_hash"]}'
    functional = {'kind':'hullcirq-original-job-finite-top-output-audit-v1',
        'status': 'Passed' if ([index for index, _, _ in observed] == list(range(16))
            and [value for _, value, _ in observed] == expected and log.count(marker) == 1
            and 'HULLCIRQ_FAIL' not in log) else 'Failed',
        'expected': expected, 'observed': observed, 'vector_hash':plan['vector_hash'],
        'original_plan_sha256':object_hash(plan), 'base_testbench_sha256':plan['testbench_sha256'],
        'scope':'one inherited GUI job, external outputs/completion/assertions; not all former hierarchy monitors',
        'original_job_values_changed':False, 'S14_adopted':False}
    write_new(destination / 'functional-audit.json', functional)
    sdf = (folder / 'input.sdf').read_bytes().decode('utf-8')
    inventory = interconnect_inventory((folder / 'input.nl.v').read_bytes().decode('utf-8'), sdf,
                                     (folder / 'original-cell-models.v').read_bytes().decode('utf-8'))
    write_new(destination / 'interconnect-inventory.json', inventory)
    timing = audit_sdf_timing(sdf, folder / 'simulation.vcd', dut_scope='hullcirq_global_tb.dut', offset_ps=0)
    write_new(destination / 'timing-audit.json', timing)
    summary = {'kind':'hullcirq-postlayout-experiment-audit-v1',
        'experiment_directory':str(folder), 'source_binding_sha256':physical.sha(folder / 'source-binding.json'),
        'functional_status':functional['status'], 'timing_status':timing['status'],
        'timing_counts':timing['counts'], 'S14_adopted':False,
        'overall_S14_validation_status':'Unsupported',
        'reason':'Independent native delay readback and timed-testbench version qualification are separate mandatory checks.',
        'files':{path.name:{'sha256':physical.sha(path),'bytes':path.stat().st_size}
                 for path in destination.iterdir() if path.is_file()}}
    write_new(destination / 'report.json', summary)
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('experiment_directory')
    parser.add_argument('new_audit_directory')
    arguments = parser.parse_args()
    print(json.dumps(audit(arguments.experiment_directory, arguments.new_audit_directory), ensure_ascii=False), flush=True)
