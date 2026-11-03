"""Frozen zero-delay waveform recording, reusing S14's recording insertion.

The saved original verification plan/testbench is never edited. Only the
execution copy gains a recording block; original assertions/timing stay exact.
This version is retained for historical proof reconstruction.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import stat

from .domain import DomainError
from . import postroute_generic as routed
from .physical_tools import io_path, read_bytes
from .verification import content_hash, object_hash

VERSION = 'hullcirq-zero-delay-waveform-v1'
MARKER = 'HULLCIRQ_ZERO_DELAY_WAVEFORM'
ROOT = Path(__file__).resolve().parents[2]
FILES = {
    'simulation-waveform': 'simulation.vcd',
    'original-testbench': 'original_job_tb.v',
    'recorded-testbench': 'recorded_job_tb.v',
    'simulation-input-netlist': 'candidate.v',
    'global-input-netlist': 'netlist.v',
    'simulation-stdout': 'simulation-stdout.log',
    'simulation-stderr': 'simulation-stderr.log',
    'waveform-recording-manifest': 'waveform-recording.json',
}


def require(value, message):
    if not value:
        raise DomainError('simulation_waveform_proof', message, 409)


def module_sha256():
    return hashlib.sha256(Path(__file__).read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def instrument(plan, base_testbench, testbench_module):
    """Return a new executable copy; generic projects use S14's exact builder."""
    require(type(base_testbench) is str and type(testbench_module) is str
            and re.fullmatch(r'[A-Za-z_][A-Za-z0-9_$]*', testbench_module),
            'Retain the declared fixed testbench module.')
    if plan.get('kind') == 'generic_cycle_vectors':
        require(base_testbench == plan['testbench'] and testbench_module == plan['testbench_module'],
                'Generic recording must retain the exact frozen cycle testbench.')
        interface = plan['interface']
        settings = {'top_module': interface['module_name'], 'clock_name': interface['clock']['port'],
                    'clock_period_ns': interface['clock']['period_ns'],
                    'reset_name': interface['reset']['port'], 'reset_active': interface['reset']['active'],
                    'reset_kind': interface['reset']['kind']}
        text = routed.functional_testbench(plan, settings, {'version': routed.CYCLE_VERSION})
        # This is a zero-delay node/global run, never a routed/SDF claim.
        return text.replace('    $display("HULLCIRQ_ROUTED_FUNCTIONAL_NO_SDF");\n',
                            '    $display("' + MARKER + '");\n')
    code = routed._code(base_testbench)
    endings = list(re.finditer(r'\bendmodule\b', code))
    require(len(endings) == 1 and re.search(r'\bmodule\s+' + re.escape(testbench_module) + r'\s*;', code),
            'Recording requires one declared trusted testbench module.')
    end = endings[0].start()
    recording = ('  initial begin\n    $display("' + MARKER + '");\n'
                 '    $dumpfile("simulation.vcd");\n    $dumpvars(1, ' + testbench_module + ');\n  end\n')
    return base_testbench[:end] + recording + base_testbench[end:]


def descriptor(plan, base_testbench, recorded_testbench, testbench_module):
    return {'version': VERSION, 'module_sha256': module_sha256(),
            's14_recording_module_sha256': routed.module_sha256(),
            'verification_plan_sha256': object_hash(plan),
            'original_testbench_sha256': plan['testbench_sha256'],
            'base_testbench_sha256': content_hash(base_testbench),
            'recorded_testbench_sha256': content_hash(recorded_testbench),
            'testbench_module': testbench_module, 'runtime_cwd': 'isolated_run_directory',
            'waveform_file': 'simulation.vcd', 'logic': 'zero_delay_no_PDK_no_SDF'}


def prepare(folder, plan, base_testbench, testbench_module):
    artifacts(folder)  # Validate location and directory ancestry before writing.
    text = instrument(plan, base_testbench, testbench_module)
    binding = descriptor(plan, base_testbench, text, testbench_module)
    io_path(folder/'original_job_tb.v').write_text(plan['testbench'], encoding='utf-8', newline='\n')
    io_path(folder/'recorded_job_tb.v').write_text(text, encoding='utf-8', newline='\n')
    io_path(folder/'waveform-recording.json').write_text(json.dumps(binding, sort_keys=True, indent=2)+'\n', encoding='utf-8', newline='\n')
    return text, binding


def artifacts(folder):
    folder = Path(os.path.abspath(folder))
    require(folder.is_relative_to(ROOT), 'New saved simulation artifacts must remain inside this HuLLCirq checkout.')
    for part in [ROOT, *reversed([p for p in folder.parents if p != ROOT and p.is_relative_to(ROOT)]), folder]:
        info = io_path(part).lstat()
        require(stat.S_ISDIR(info.st_mode) and not io_path(part).is_symlink()
                and not (getattr(info, 'st_file_attributes', 0) & 0x400),
                'Simulation artifact directories cannot contain links or reparse points.')
    items = []
    for identifier, name in FILES.items():
        path = io_path(folder/name)
        if not path.exists():
            continue
        info = path.lstat()
        require(stat.S_ISREG(info.st_mode) and not path.is_symlink()
                and not (getattr(info, 'st_file_attributes', 0) & 0x400),
                'Retained simulation artifacts cannot be links or special files.')
        raw = path.read_bytes()
        items.append({'id': identifier, 'relative_path': name, 'bytes': len(raw),
                      'sha256': hashlib.sha256(raw).hexdigest(), 'mime_type': 'text/plain; charset=utf-8'})
    return items


def finish(folder, result):
    """Retain evidence even when compilation/simulation reports failure."""
    for name, key in [('simulation-stdout.log', 'stdout'), ('simulation-stderr.log', 'stderr')]:
        io_path(folder/name).write_text(result.get(key, ''), encoding='utf-8')
    result['artifacts'] = artifacts(folder)
    if result.get('waveform_recording') and result.get('validation_status') == 'Passed':
        wave = next((a for a in result['artifacts'] if a['id'] == 'simulation-waveform'), None)
        if wave is None or wave['bytes'] == 0:
            result['validation_status'] = 'Failed'
            result['diagnostics'].append({'code': 'simulation_waveform_missing', 'severity': 'error',
                                          'message': 'Simulation completed without its required retained waveform. Inspect the saved logs.'})
    return result


def validate(proof, plan, base_testbench, testbench_module):
    binding = proof.get('waveform_recording')
    expected_text = instrument(plan, base_testbench, testbench_module)
    require(binding == descriptor(plan, base_testbench, expected_text, testbench_module),
            'Retain the exact versioned recording implementation and unchanged original plan.')
    folder = Path(proof['artifacts_directory'])
    actual = artifacts(folder)  # Validate ancestry before following any file.
    require(read_bytes(folder/'original_job_tb.v').decode('utf-8') == plan['testbench']
            and read_bytes(folder/'recorded_job_tb.v').decode('utf-8') == expected_text,
            'The saved original or executable recording testbench changed.')
    require(proof.get('artifacts') == actual and any(a['id'] == 'simulation-waveform' and a['bytes'] > 0 for a in actual),
            'Retain the hash-bound actual waveform, source files and raw simulation logs.')
    require(json.loads(read_bytes(folder/'waveform-recording.json')) == binding,
            'The retained waveform recording manifest changed.')
