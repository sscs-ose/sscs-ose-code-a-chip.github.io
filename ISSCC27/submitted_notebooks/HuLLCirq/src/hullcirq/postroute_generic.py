"""Versioned, source-bound external-port functional adapter (no tool calls).

Metadata describes an already adopted testbench; it cannot replace its workload,
expected values, clock constraint, assertions, or routed circuit. Unsupported
testbench constructs fail closed instead of being interpreted as a pass.
"""
from __future__ import annotations

import copy
from decimal import Decimal, InvalidOperation
import hashlib
from pathlib import Path
import re

from .domain import DomainError
from .verification import content_hash, object_hash

PROFILE = 'hullcirq-postroute-functional-sta-v4'
VERSION = 'external-port-functional-v1'
CYCLE_VERSION = 'generic-cycle-functional-v1'
FIELDS = ('version', 'testbench_module', 'dut_instance', 'clock_signal',
          'clock_statement', 'timeout_statement', 'output_prefix', 'pass_marker', 'failure_markers')
IDENTIFIER = r'[A-Za-z_][A-Za-z0-9_$]*'
NUMBER = r'(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)'


def require(condition, message):
    if not condition:
        raise DomainError('postroute_adapter_contract', message)


def module_sha256():
    return hashlib.sha256(Path(__file__).read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def _source(plan, settings):
    require(type(plan) is dict and type(settings) is dict, 'Retain a saved external-port verification plan and clock settings.')
    text = plan.get('testbench')
    require(type(text) is str and 0 < len(text.encode('utf-8')) <= 2_000_000
            and content_hash(text) == plan.get('testbench_sha256'), 'The original saved testbench hash changed.')
    recipe = plan.get('recipe')
    require(type(recipe) is dict, 'Retain the original saved finite verification recipe.')
    count = plan.get('output_count'); expected = recipe.get('expected_outputs')
    require(type(count) is int and 0 < count <= 4096 and type(expected) is list and len(expected) == count
            and all(type(value) is int for value in expected),
            'A saved finite integer-output workload with exact original expected values is required; S14 never learns golden values from the DUT.')
    require(type(plan.get('vector_hash')) is str and re.fullmatch(r'[0-9a-f]{64}', plan['vector_hash']),
            'Retain the original verification-vector hash.')
    require(type(settings.get('top_module')) is str and re.fullmatch(IDENTIFIER, settings['top_module'])
            and type(settings.get('clock_name')) is str and re.fullmatch(IDENTIFIER, settings['clock_name']),
            'The fixed adapter requires simple top-module and clock-port identifiers.')
    try:
        period = Decimal(str(settings['clock_period_ns']))
    except (KeyError, InvalidOperation, ValueError):
        raise DomainError('postroute_adapter_contract', 'Retain a finite positive original clock period.') from None
    require(period.is_finite() and period > 0, 'Retain a finite positive original clock period.')
    return text, expected, period


def _code(text):
    # Preserve quoted strings when excluding comments; comment punctuation in
    # a diagnostic string must not erase executable text from these checks.
    return re.sub(r'"(?:\\.|[^"\\])*"|//[^\n]*|/\*[\s\S]*?\*/',
                  lambda match: match[0] if match[0].startswith('"') else ' ' * len(match[0]), text)


def validate_contract(plan, settings, contract):
    if type(plan) is dict and plan.get('kind') == 'generic_cycle_vectors':
        from .generic_verification import validate_cycle_plan
        validate_cycle_plan(plan)
        require(contract == {'version': CYCLE_VERSION}, 'The self-describing generic cycle plan needs no editable adapter metadata.')
        interface = plan['interface']
        require(interface['module_name'] == settings.get('top_module')
                and interface['clock']['port'] == settings.get('clock_name')
                and Decimal(str(interface['clock']['period_ns'])) == Decimal(str(settings.get('clock_period_ns')))
                and interface['reset']['port'] == settings.get('reset_name')
                and interface['reset']['active'] == settings.get('reset_active')
                and interface['reset']['kind'] == settings.get('reset_kind'),
                'The generic cycle plan must retain the exact original top, clock period, reset name and polarity.')
        require(re.fullmatch(IDENTIFIER, plan.get('testbench_module', '')), 'Retain the exact declared generic testbench module.')
        return copy.deepcopy(contract)
    text, _, _ = _source(plan, settings)
    require(type(contract) is dict and set(contract) == set(FIELDS) and contract.get('version') == VERSION,
            'Use only the documented versioned adapter metadata fields; testbench, expected values and clock period cannot be overridden here.')
    for key in ('testbench_module', 'dut_instance', 'clock_signal'):
        require(type(contract.get(key)) is str and re.fullmatch(IDENTIFIER, contract[key]), 'Use one simple Verilog identifier for ' + key + '.')
    code = _code(text)
    modules = re.findall(r'\bmodule\s+(' + IDENTIFIER + r')\s*;', code)
    require(modules == [contract['testbench_module']] and len(re.findall(r'\bmodule\b', code)) == 1
            and len(re.findall(r'\bendmodule\b', code)) == 1,
            'The saved testbench must contain exactly one unambiguous no-port testbench module.')
    top = re.escape(settings['top_module']); dut = re.escape(contract['dut_instance'])
    require(len(re.findall(r'\b' + top + r'\s+' + dut + r'\s*\(', code)) == 1,
            'Select the exact adopted top-module instance in the saved testbench.')
    require(not re.search(r'\b' + dut + r'\s*\.', code),
            'The routed-netlist testbench must use external DUT ports, not flattened internal hierarchy.')
    signal = re.escape(contract['clock_signal'])
    require(len(re.findall(r'\.' + re.escape(settings['clock_name']) + r'\s*\(\s*' + signal + r'\s*\)', code)) == 1,
            'The saved testbench clock signal must connect to the original top-level clock port.')
    require(not re.search(r'`\s*include\b|\$(?:system|fopen|fclose|fwrite|fdisplay|fread|fscanf|fseek|readmem\w*|writemem\w*|sdf_annotate|dumpfile|dumpvars|stop)\b', code),
            'External files, shell tasks, SDF annotation and testbench-owned waveform paths are unsupported in this fixed functional adapter.')
    scales = re.findall(r'`timescale\s+([^\n]+)', code)
    require(not scales or scales == ['1ns/1ps'], 'Only an absent timescale or the explicit 1ns/1ps timescale is supported.')
    for key in ('clock_statement', 'timeout_statement'):
        require(type(contract.get(key)) is str and 0 < len(contract[key]) <= 1024 and text.count(contract[key]) == 1,
                'Select one exact, unique saved testbench statement for ' + key + '.')
    clock = re.fullmatch(r'\s*always\s+#(' + NUMBER + r')\s+' + signal + r'\s*=\s*~\s*' + signal + r'\s*;\s*', contract['clock_statement'])
    timeout = re.fullmatch(r'\s*initial\s+begin\s+#(' + NUMBER + r')\s*;\s*', contract['timeout_statement'])
    require(clock is not None and timeout is not None and Decimal(clock[1]) > 0 and Decimal(timeout[1]) > 0,
            'Select a simple saved always-delay clock and initial-delay watchdog; their original cycle relationship is preserved.')
    # Another generator on the same signal would make the declared clock
    # adaptation ambiguous, even if the selected anchor itself occurs once.
    require(len(re.findall(r'\balways\s+#' + NUMBER + r'\s+' + signal + r'\s*=', code)) == 1,
            'The selected testbench clock must have exactly one delay generator.')
    prefix = contract.get('output_prefix'); marker = contract.get('pass_marker')
    require(type(prefix) is str and re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.:-]{0,95}', prefix)
            and type(marker) is str and 0 < len(marker) <= 512 and not any(ord(c) < 32 for c in marker),
            'Declare a bounded output-record token and an exact single-line completion marker.')
    require(text.count('"' + marker + '"') == 1 and re.search(r'\$display\s*\(\s*"' + re.escape(marker) + r'"\s*\)\s*;', code),
            'The completion marker must already be emitted exactly once by the saved testbench; no new success condition is invented.')
    require('"' + prefix + ' index=%0d value=%0d cycle=%0d"' in code,
            'The saved testbench must emit indexed integer value/cycle records using the declared prefix.')
    failures = contract.get('failure_markers')
    require(type(failures) is list and 0 < len(failures) <= 16
            and all(type(v) is str and 0 < len(v) <= 128 and not any(ord(c) < 32 for c in v) for v in failures)
            and len(set(failures)) == len(failures),
            'Declare nonempty bounded failure markers; ERROR and FATAL are always checked additionally.')
    return copy.deepcopy(contract)


def derive_contract(plan, settings):
    """Infer metadata only from an unambiguous saved standard transcript TB.

    No circuit names, node count, array dimensions or NPU plan-kind allowlist.
    Other supported metadata can be supplied explicitly through the GUI.
    """
    if type(plan) is dict and plan.get('kind') == 'generic_cycle_vectors':
        return validate_contract(plan, settings, {'version': CYCLE_VERSION})
    text, expected, _ = _source(plan, settings); code = _code(text)
    modules = re.findall(r'\bmodule\s+(' + IDENTIFIER + r')\s*;', code)
    instances = re.findall(r'\b' + re.escape(settings['top_module']) + r'\s+(' + IDENTIFIER + r')\s*\(', code)
    signals = re.findall(r'\.' + re.escape(settings['clock_name']) + r'\s*\(\s*(' + IDENTIFIER + r')\s*\)', code)
    require(len(modules) == len(instances) == len(signals) == 1,
            'Describe the saved testbench module, DUT instance and clock connection in the GUI adapter metadata.')
    signal = re.escape(signals[0])
    clocks = re.findall(r'^[ \t]*always\s+#' + NUMBER + r'\s+' + signal + r'\s*=\s*~\s*' + signal + r'\s*;[ \t]*$', text, re.M)
    timeouts = re.findall(r'^[ \t]*initial\s+begin\s+#' + NUMBER + r'\s*;', text, re.M)
    prefixes = re.findall(r'\$display\s*\(\s*"([A-Za-z_][A-Za-z0-9_.:-]*) index=%0d value=%0d cycle=%0d"', code)
    marker = f"HULLCIRQ_GLOBAL_PASS outputs={len(expected)} vector_hash={plan['vector_hash']}"
    require(len(clocks) == len(timeouts) == len(prefixes) == 1 and '"' + marker + '"' in text,
            'Describe the exact saved clock/watchdog statements, output prefix and completion marker in GUI adapter metadata.')
    contract = dict(version=VERSION, testbench_module=modules[0], dut_instance=instances[0], clock_signal=signals[0],
                    clock_statement=clocks[0], timeout_statement=timeouts[0], output_prefix=prefixes[0],
                    pass_marker=marker, failure_markers=['HULLCIRQ_FAIL', 'ERROR', 'FATAL'])
    return validate_contract(plan, settings, contract)


def binding(plan, settings, contract):
    contract = validate_contract(plan, settings, contract)
    return {'version': VERSION, 'module_sha256': module_sha256(), 'contract': contract,
            'contract_sha256': object_hash(contract), 'verification_plan_sha256': object_hash(plan),
            'settings_sha256': object_hash(settings), 'testbench_sha256': plan['testbench_sha256'],
            'testbench_module': plan['testbench_module'] if plan.get('kind') == 'generic_cycle_vectors' else contract['testbench_module']}


def validate_binding(plan, settings, descriptor):
    require(type(descriptor) is dict and descriptor == binding(plan, settings, descriptor.get('contract')),
            'Preserve the exact saved adapter implementation, metadata, original plan, testbench and clock settings.')
    return descriptor['contract']


def functional_testbench(plan, settings, contract):
    contract = validate_contract(plan, settings, contract)
    if plan.get('kind') == 'generic_cycle_vectors':
        # The common builder already uses the original declared clock period
        # and independent per-cycle assertions. Preserve every original byte
        # except inserting the fixed recording block before its final module.
        text = plan['testbench']
        recording = ('  initial begin\n    $display("HULLCIRQ_ROUTED_FUNCTIONAL_NO_SDF");\n'
                     '    $dumpfile("simulation.vcd");\n    $dumpvars(1, ' + plan['testbench_module'] + ');\n  end\n')
        end = re.search(r'\bendmodule\b', _code(text))
        require(end is not None and len(re.findall(r'\bendmodule\b', _code(text))) == 1,
                'Retain the single generated external-port cycle testbench module.')
        return text[:end.start()] + recording + text[end.start():]
    text, _, period = _source(plan, settings)
    clock = re.search(r'#(' + NUMBER + ')', contract['clock_statement'])
    timeout = re.search(r'#(' + NUMBER + ')', contract['timeout_statement'])
    half = Decimal(clock[1]); watchdog = Decimal(timeout[1]) * period / (2 * half)
    new_clock = contract['clock_statement'].replace('#' + clock[1], '#' + format(period / 2, 'f'), 1)
    new_timeout = contract['timeout_statement'].replace('#' + timeout[1], '#' + format(watchdog, 'f'), 1)
    text = text.replace(contract['clock_statement'], new_clock, 1).replace(contract['timeout_statement'], new_timeout, 1)
    if '`timescale' not in text:
        text = '`timescale 1ns/1ps\n' + text
    recording = ('  initial begin\n    $display("HULLCIRQ_ROUTED_FUNCTIONAL_NO_SDF");\n'
                 '    $dumpfile("simulation.vcd");\n    $dumpvars(1, ' + contract['testbench_module'] + ');\n  end\n')
    end = re.search(r'\bendmodule\b', _code(text))
    return text[:end.start()] + recording + text[end.start():]


def parse_functional(stdout, plan, settings, contract, stderr=''):
    contract = validate_contract(plan, settings, contract)
    if plan.get('kind') == 'generic_cycle_vectors':
        from .generic_verification import parse_cycle_runtime
        report = parse_cycle_runtime(stdout, plan, stderr)
        passed = (report['validation_status'] == 'Passed'
                  and stdout.splitlines().count('HULLCIRQ_ROUTED_FUNCTIONAL_NO_SDF') == 1
                  and 'ERROR' not in stdout + stderr and 'FATAL' not in stdout + stderr)
        return {**report, 'validation_status': 'Passed' if passed else 'Failed', 'SDF_annotated': False,
                'adapter_contract_sha256': object_hash(contract), 'logic': 'four_state_original_PDK_FUNCTIONAL_models',
                'limits': ['Exact saved finite external-port cycle assertions; no dynamic SDF delay simulation or exhaustive equivalence.']}
    _, expected, _ = _source(plan, settings)
    prefix = contract['output_prefix']
    outputs = [{'index': int(a), 'value': int(b), 'cycle': int(c)} for a, b, c in re.findall(
        r'^' + re.escape(prefix) + r' index=(\d+) value=(-?\d+) cycle=(\d+)$', stdout, re.M)]
    lines = stdout.splitlines()
    passed = (lines.count('HULLCIRQ_ROUTED_FUNCTIONAL_NO_SDF') == 1 and lines.count(contract['pass_marker']) == 1
              and len([line for line in lines if line.startswith(prefix)]) == len(expected)
              and not any(marker in stdout + stderr for marker in set(contract['failure_markers']) | {'ERROR', 'FATAL'})
              and [o['index'] for o in outputs] == list(range(len(expected)))
              and [o['value'] for o in outputs] == expected
              and all(o['cycle'] > 0 and (i == 0 or o['cycle'] > outputs[i-1]['cycle']) for i, o in enumerate(outputs)))
    return {'validation_status': 'Passed' if passed else 'Failed', 'outputs': outputs,
            'vector_hash': plan['vector_hash'], 'testbench_sha256': plan['testbench_sha256'],
            'adapter_contract_sha256': object_hash(contract), 'scope': 'saved_original_external_port_integer_job',
            'logic': 'four_state_original_PDK_FUNCTIONAL_models', 'SDF_annotated': False,
            'limits': ['Finite saved original workload, not exhaustive equivalence or dynamic SDF timing simulation.',
                       'Only external DUT ports are used; no original internal hierarchy is inferred after flattening.']}
