"""Post-route functional verification and independent extracted STA.

This method deliberately makes no dynamic SDF timing-check claim. It runs the
unchanged GUI workload on the routed netlist with original PDK functional
models, and evaluates delay/electrical constraints using extracted OpenSTA.
"""
from __future__ import annotations

import ast
import copy
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile

from .domain import DomainError
from . import physical_tools as physical
from . import lvs_tools
from . import postroute_sta
from .postlayout_execution import WORKER_V2_SHA256
from .verification import content_hash, object_hash, trusted_command, _wsl_path

ROOT = Path(__file__).resolve().parents[2]
SCOPE = 'post_route_functional_plus_sta'
METHOD = 'Routed-netlist functional simulation + extracted STA'
PROFILE_V1 = 'hullcirq-postroute-functional-sta-v1'
PROFILE_V2 = 'hullcirq-postroute-functional-sta-v2'
PROFILE_V3 = 'hullcirq-postroute-functional-sta-v3'
PROFILE_V4 = 'hullcirq-postroute-functional-sta-v4'
SUPPORTED_PLAN_KINDS = {'global-original-matrix-v1', 'npu2-global-original-matrix-v1'}
COMPILER_PACKAGE_NAME = 'iverilog_12.0-2build2_amd64.deb'
COMPILER_PACKAGE_SHA256 = 'f19394cee05ad526e0eb3873bc6c17a5828f56df17fbe2db40cb66513a2d4667'
COMPILER_PACKAGE_SOURCE = 'https://packages.ubuntu.com/noble/iverilog'
COMPILER_MANIFEST_SHA256 = 'c576dc2a63337955b56f380bd9ee075f48100de38088068190a6eb25797682f3'
require, sha, load = physical.require, physical.sha, physical.load
file_stat, file_exists = physical.file_stat, physical.file_exists
read_bytes, read_text, artifact_files = physical.read_bytes, physical.read_text, physical.artifact_files
MODEL_FILES = {'cell_models': 'libs.ref/sky130_fd_sc_hd/verilog/sky130_fd_sc_hd.v',
               'primitives': 'libs.ref/sky130_fd_sc_hd/verilog/primitives.v'}
TEXT = 'text/plain; charset=utf-8'


def _bytes(value):
    return (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode('utf-8')


def _save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(value if isinstance(value, bytes) else _bytes(value))


def _output_count(plan):
    recipe = plan.get('recipe') if type(plan) is dict else None
    expected = recipe.get('expected_outputs') if type(recipe) is dict else None
    count = plan.get('output_count') if type(plan) is dict else None
    require(type(count) is int and 0 < count <= 4096 and type(expected) is list and len(expected) == count,
            'postroute_testbench', 'The saved output count must match the complete expected-output list.')
    return count


def functional_testbench(plan, settings):
    """Scale the original cycle recipe; do not alter stimulus or assertions."""
    text = plan['testbench']
    period = Decimal(str(settings['clock_period_ns']))
    _output_count(plan)
    require(plan['kind'] in SUPPORTED_PLAN_KINDS and content_hash(text) == plan['testbench_sha256']
            and period.is_finite() and period > 0 and text.count('  always #5 clk=~clk;') == 1
            and text.count('  initial begin #200000;') == 1 and text.count('endmodule') == 1
            and '`timescale' not in text,
            'postroute_testbench', 'Require the exact saved GUI workload and supported single-clock recipe.')
    text = '`timescale 1ns/1ps\n' + text.replace('  always #5 clk=~clk;', f'  always #{period/2:f} clk=~clk;', 1)
    text = text.replace('  initial begin #200000;', f'  initial begin #{period*20000:f};', 1)
    text = text.replace('endmodule', '''  initial begin
    $display("HULLCIRQ_ROUTED_FUNCTIONAL_NO_SDF");
    $dumpfile("simulation.vcd");
    $dumpvars(0, clk, rst, config_data, config_data_valid, config_data_ready,
      load_data, load_data_valid, load_data_ready, output_data,
      output_data_valid, output_data_ready, busy, job_done);
  end
endmodule''', 1)
    return text


def runtime_pins():
    """Read the already pinned Icarus distribution without executing its worker."""
    path = ROOT / 'scripts/postlayout_worker_v2.py'
    # The published Windows setup may check Git text files out with CRLF.  Bind
    # to the exact repository text (LF) so transport newlines do not rewrite the
    # retained v1 pin table or its historical values.
    source = read_bytes(path).replace(b'\r\n', b'\n')
    require(b'\r' not in source and hashlib.sha256(source).hexdigest() == WORKER_V2_SHA256,
            'postroute_runtime', 'The retained Icarus runtime definition changed.')
    tree = ast.parse(source.decode('utf-8'))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'TOOL_SHA256' for t in node.targets):
            return ast.literal_eval(node.value)
    raise DomainError('postroute_runtime', 'Missing pinned Icarus runtime files.')


def _native_wsl_path(value):
    require(type(value) is str and not any(ord(char) < 32 for char in value),
            'postroute_runtime', 'Require an absolute WSL path from the configured compiler.')
    match = re.fullmatch(r'/mnt/([a-zA-Z])/([^\\]+)', value)
    require(match is not None and '..' not in Path(match[2]).parts,
            'postroute_runtime', 'Require an absolute WSL path from the configured compiler.')
    return Path(f'{match[1].upper()}:/{match[2]}').resolve()


def _compiler_root(compiler):
    require(type(compiler) is dict
            and set(compiler) == {'kind', 'distribution', 'executable', 'base_directory', 'working_directory'}
            and compiler.get('kind') == 'wsl'
            and type(compiler.get('distribution')) is str
            and re.fullmatch(r'[A-Za-z0-9_.-]+', compiler['distribution']) is not None,
            'postroute_runtime', 'Require the configured isolated WSL Icarus compiler.')
    executable = compiler.get('executable')
    base = compiler.get('base_directory')
    suffix = '/usr/bin/iverilog'
    require(type(executable) is str and executable.endswith(suffix),
            'postroute_runtime', 'Require the configured isolated Icarus executable.')
    linux_root = executable[:-len(suffix)]
    require(base == linux_root + '/usr/lib/x86_64-linux-gnu/ivl',
            'postroute_runtime', 'Require the compiler and its fixed ivl base from one isolated runtime.')
    root = _native_wsl_path(linux_root)
    expected = (ROOT / '.work/m2/iverilog').resolve()
    fresh = (ROOT / '.work/fresh').resolve()
    fresh_scope = root.parent
    is_fresh = (root.name == 'iverilog' and fresh_scope.parent == fresh
                and re.fullmatch(r'[a-f0-9]{12}', fresh_scope.name) is not None)
    if is_fresh:
        expected = fresh_scope / 'iverilog'
        require(load(fresh_scope / 'compiler.json') == compiler,
                'postroute_runtime', 'Use the exact compiler configuration written by fresh public setup.')
    require(root == expected and _native_wsl_path(executable) == expected/'usr/bin/iverilog'
            and _native_wsl_path(base) == expected/'usr/lib/x86_64-linux-gnu/ivl',
            'postroute_runtime', 'Use the public setup compiler below HuLLCirq/.work/m2 or its host-bound .work/fresh scope.')
    syntax = Path(compiler['working_directory']).resolve()
    require(syntax == (fresh_scope/'syntax' if is_fresh else (ROOT/'.work/m2/syntax').resolve()),
            'postroute_runtime', 'Use the compiler working directory written by the public setup helper.')
    return root


def _compiler_inventory(root):
    root = Path(root).resolve()
    files = {}
    for path in sorted(artifact_files(root,reject_links=True), key=lambda item: item.as_posix()):
        require(not path.is_symlink() and not path.is_junction(),
                'postroute_runtime', 'The fixed compiler package contains no links or junctions.')
        if not file_exists(path):
            require(path.is_dir(), 'postroute_runtime', 'Compiler runtime entries must be ordinary files or directories.')
            continue
        resolved = path.resolve()
        require(not path.is_symlink() and resolved.is_relative_to(root),
                'postroute_runtime', 'Compiler runtime files must remain inside the isolated package root.')
        relative = resolved.relative_to(root).as_posix()
        files[relative] = {'sha256': sha(resolved), 'bytes': file_stat(resolved).st_size}
    require({'usr/bin/iverilog', 'usr/bin/vvp', 'usr/lib/x86_64-linux-gnu/ivl/ivl',
             'usr/lib/x86_64-linux-gnu/ivl/ivlpp', 'usr/lib/x86_64-linux-gnu/ivl/vvp.conf',
             'usr/lib/x86_64-linux-gnu/ivl/vvp.tgt'}.issubset(files),
            'postroute_runtime', 'The pinned package extraction is incomplete.')
    return files


def _compiler_package_manifest():
    """Read the source-pinned inventory derived from the verified .deb payload.

    The published package uses zstd, which the isolated Python 3.12 cannot
    decode. Its checked-in inventory was derived read-only with dpkg-deb and
    stdlib tarfile. GUI preparation invokes neither decoder nor package code.
    """
    manifest = load(ROOT / 'configs/iverilog_12_runtime_manifest.json')
    require(object_hash(manifest) == COMPILER_MANIFEST_SHA256
            and manifest.get('schema') == 'hullcirq-iverilog-package-inventory-v1'
            and manifest.get('package', {}).get('name') == COMPILER_PACKAGE_NAME
            and manifest['package'].get('sha256') == COMPILER_PACKAGE_SHA256
            and manifest['package'].get('source') == COMPILER_PACKAGE_SOURCE
            and type(manifest['package'].get('bytes')) is int and manifest['package']['bytes'] > 0
            and manifest.get('provenance', {}).get('links') == {}
            and type(manifest.get('files')) is dict,
            'postroute_runtime', 'The source-pinned Icarus package inventory changed.')
    return manifest


def _verified_compiler_inventory(root):
    manifest = _compiler_package_manifest()
    # Both public setup routes retain the same pinned package and full payload.
    # Fresh setup keeps downloaded archives separate from extracted runtimes.
    fresh = (ROOT / '.work/fresh').resolve()
    is_fresh = root.name == 'iverilog' and root.parent.parent == fresh and re.fullmatch(r'[a-f0-9]{12}', root.parent.name)
    package = root.parent / ('downloads' if is_fresh else '') / COMPILER_PACKAGE_NAME
    require(file_exists(package) and not package.is_symlink() and not package.is_junction()
            and file_stat(package).st_size == manifest['package']['bytes']
            and sha(package) == COMPILER_PACKAGE_SHA256,
            'postroute_runtime', 'Require the public checksum-pinned Ubuntu Icarus package.')
    inventory = _compiler_inventory(root)
    require(inventory == manifest['files'], 'postroute_runtime',
            'The extracted Icarus files differ from the checksum-pinned package payload. '
            'Preserve the files and repair the isolated runtime using the public setup guide.')
    return inventory, manifest['package']


def _v2_compiler(configuration):
    compiler = configuration['compiler']
    root = _compiler_root(compiler)
    inventory, package = _verified_compiler_inventory(root)
    descriptor = configuration.get('compiler_package')
    require(type(descriptor) is dict and descriptor == package,
            'postroute_runtime', 'Require the public checksum-pinned Ubuntu Icarus package.')
    pins = configuration.get('compiler_runtime_pins')
    sizes = configuration.get('compiler_runtime_bytes')
    require(type(pins) is dict and type(sizes) is dict
            and set(pins) == set(sizes) == set(inventory)
            and all(type(pins[name]) is str and re.fullmatch(r'[0-9a-f]{64}', pins[name])
                    and type(sizes[name]) is int and sizes[name] >= 0
                    and pins[name] == inventory[name]['sha256'] and sizes[name] == inventory[name]['bytes']
                    for name in inventory),
            'postroute_runtime', 'The prepared compiler inventory no longer matches the isolated package extraction.')
    return pins


def _configuration_runtime_pins(configuration):
    if configuration.get('profile_version') in (PROFILE_V2, PROFILE_V3, PROFILE_V4):
        return configuration['compiler_runtime_pins']
    return runtime_pins()


def _annotation_policy(configuration):
    policy = configuration.get('sta_annotation_policy')
    expected = postroute_sta.ANNOTATION_V2 if configuration.get('profile_version') in (PROFILE_V3, PROFILE_V4) else None
    require(policy == expected, 'postroute_configuration',
            'The STA annotation policy must match its frozen functional-plus-STA profile version.')
    return policy


def _check_output_path_budget(working):
    # Check the longest fixed terminal-proof name before any tool is launched.
    # WSL can create this path even when ordinary Windows APIs cannot read it.
    terminal = working / 'postroute-xxxxxxxx' / 'sta' / 'sta-max_ss_100C_1v60' / 'process-result.json'
    require(os.name != 'nt' or len(str(terminal)) < 260,
            'postroute_path_length',
            'The S14 output path exceeds the Windows proof-file limit. Use a shorter checkout or workspace path, then prepare S14 again.')


def prepare_configuration(layout, compiler, working_directory, *, adapter_contract=None):
    """Build a fixed v3 profile from backend-owned layout and compiler state.

    No package, executable, PDK or model path is accepted separately: each is
    derived from the selected S11 record or the configured public compiler.
    """
    require(type(layout) is dict and type(layout.get('runtime_configuration')) is dict,
            'postroute_source', 'Prepare S14 only from a concrete selected layout record.')
    working = Path(working_directory).resolve()
    work_root = (ROOT / '.work').resolve()
    require(working != work_root and working.is_relative_to(work_root),
            'postroute_path', 'Use a backend-owned post-route directory below HuLLCirq/.work.')
    _check_output_path_budget(working)
    compiler = copy.deepcopy(compiler)
    root = _compiler_root(compiler)
    inventory, package = _verified_compiler_inventory(root)
    configuration = {
        'profile_version': PROFILE_V3,
        'sta_annotation_policy': postroute_sta.ANNOTATION_V2,
        'execution_scope': SCOPE,
        'verification_supported': True,
        'physical_runtime': copy.deepcopy(layout['runtime_configuration']),
        'compiler': compiler,
        'compiler_package': copy.deepcopy(package),
        'compiler_runtime_pins': {name: value['sha256'] for name, value in inventory.items()},
        'compiler_runtime_bytes': {name: value['bytes'] for name, value in inventory.items()},
        'working_directory': str(working),
    }
    if adapter_contract is not None:
        from . import postroute_generic
        configuration['profile_version'] = PROFILE_V4
        configuration['functional_adapter'] = postroute_generic.binding(
            layout['verification_plan'], layout['settings'], adapter_contract)
    _configuration(configuration)
    return configuration


def _configuration(configuration):
    require(type(configuration) is dict and configuration.get('execution_scope') == SCOPE
            and configuration.get('verification_supported') is True
            and configuration.get('profile_version') in (PROFILE_V1, PROFILE_V2, PROFILE_V3, PROFILE_V4),
            'postroute_configuration', 'Use the explicit functional plus STA profile.')
    _annotation_policy(configuration)
    if configuration['profile_version'] == PROFILE_V4:
        from . import postroute_generic
        descriptor = configuration.get('functional_adapter')
        require(type(descriptor) is dict and descriptor.get('version') == postroute_generic.VERSION
                and descriptor.get('module_sha256') == postroute_generic.module_sha256()
                and descriptor.get('contract_sha256') == object_hash(descriptor.get('contract')),
                'postroute_adapter_contract', 'The fixed generic adapter implementation or metadata changed; preserve the saved profile.')
    runtime = configuration['physical_runtime']
    require(runtime['kind'] == 'wsl' and runtime['appimage_sha256'] == physical.IMAGE_SHA
            and sha(runtime['appimage_path']) == physical.IMAGE_SHA,
            'postroute_runtime', 'Require the pinned LibreLane runtime.')
    compiler = configuration['compiler']
    if configuration['profile_version'] == PROFILE_V1:
        original = load(ROOT / '.work/m2k/compiler.json')
        require(object_hash(compiler) == object_hash(original), 'postroute_runtime', 'Require the retained Icarus 13 compiler.')
        runtime_pins()
    else:
        _v2_compiler(configuration)
    manifest = load(runtime['pdk_manifest_path'])
    require(sha(runtime['pdk_manifest_path']) == runtime['pdk_manifest_sha256'], 'postroute_pdk', 'PDK manifest changed.')
    for relative in MODEL_FILES.values():
        path = Path(manifest['root']) / relative
        require(sha(path) == manifest['files'][relative]['sha256'] and file_stat(path).st_size == manifest['files'][relative]['bytes'],
                'postroute_pdk', 'The original PDK functional model changed.')
    working = Path(configuration['working_directory']).resolve()
    require(working != (ROOT/'.work').resolve() and working.is_relative_to((ROOT/'.work').resolve()),
            'postroute_path', 'Use a separate local post-route work directory.')
    if configuration['profile_version'] in (PROFILE_V2, PROFILE_V3, PROFILE_V4):
        _check_output_path_budget(working)
    return runtime, compiler, manifest, working


def runtime_descriptor(configuration):
    try:
        _configuration(configuration)
        return {'available': True, 'verification_supported': True, 'execution_scope': SCOPE,
                'reason': METHOD, 'method': METHOD}
    except (DomainError, OSError, ValueError, KeyError, TypeError) as error:
        return {'available': False, 'verification_supported': False, 'execution_scope': SCOPE,
                'reason': getattr(error, 'message', str(error))}


def source_inputs(layout, configuration):
    runtime, _, manifest, _ = _configuration(configuration)
    require(object_hash(runtime) == object_hash(layout['runtime_configuration']), 'postroute_source', 'Use the selected layout runtime.')
    inputs = lvs_tools.source_inputs(layout)
    models = {name: manifest['files'][relative] for name, relative in MODEL_FILES.items()}
    for key, raw in (('functional_models', _bytes(models)),
                     ('functional_testbench', _testbench(layout, configuration).encode('utf-8'))):
        inputs[key] = {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw), 'origin': SCOPE}
    inventory = postroute_sta.source_inventory(layout, runtime)
    canonical = json.dumps(inventory, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8')
    inputs['timing_sources'] = {'sha256': object_hash(inventory), 'bytes': len(canonical), 'origin': SCOPE}
    return inputs


LAUNCHER = b'''import hashlib, json, os, pathlib, subprocess, sys
root = pathlib.Path(__file__).resolve().parent
operation, expected = sys.argv[1:3]
assert operation in ('compile', 'simulate')
raw = (root/'functional-inputs.json').read_bytes()
assert hashlib.sha256(raw).hexdigest() == expected
manifest = json.loads(raw)
for item in manifest['files']:
    path = root/item['relative_path']
    assert path.stat().st_size == item['bytes']
    assert hashlib.sha256(path.read_bytes()).hexdigest() == item['sha256']
runtime = pathlib.Path(manifest['runtime_root'])
for relative, expected_sha in manifest['runtime_pins'].items():
    assert hashlib.sha256((runtime/relative).read_bytes()).hexdigest() == expected_sha
compiler = str(runtime/'usr/bin/iverilog')
base = str(runtime/'usr/lib/x86_64-linux-gnu/ivl')
if operation == 'compile':
    assert len(sys.argv) == 3
    version = subprocess.run([compiler, '-B', base, '-V'], capture_output=True, timeout=20)
    assert version.returncode == 0
    with (root/'functional-versions.json').open('x') as stream:
        json.dump({'stdout':version.stdout.decode(), 'stderr':version.stderr.decode(),
                   'compiler':compiler, 'runtime_pins':manifest['runtime_pins']},stream,indent=2)
    command = [compiler, '-B', base, '-g2005', '-DFUNCTIONAL', '-DUNIT_DELAY=', '-s', 'hullcirq_global_tb',
        '-o', 'simulation.vvp', 'primitives.v', 'cell_models.v', 'input.nl.v', 'functional-testbench.v']
    assert not (root/'simulation.vvp').exists()
    result = subprocess.run(command)
    if result.returncode != 0:
        sys.exit(result.returncode)
    program = root/'simulation.vvp'
    assert program.is_file() and program.stat().st_size > 0
    with (root/'functional-program.json').open('x') as stream:
        json.dump({'input_manifest_sha256':expected, 'command':command,
                   'version_report_sha256':hashlib.sha256((root/'functional-versions.json').read_bytes()).hexdigest(),
                   'program_sha256':hashlib.sha256(program.read_bytes()).hexdigest(),
                   'program_bytes':program.stat().st_size}, stream, indent=2)
    sys.exit(0)
else:
    assert len(sys.argv) == 4
    program_raw = (root/'functional-program.json').read_bytes()
    assert hashlib.sha256(program_raw).hexdigest() == sys.argv[3]
    program = json.loads(program_raw)
    assert program['input_manifest_sha256'] == expected
    assert hashlib.sha256((root/'functional-versions.json').read_bytes()).hexdigest() == program['version_report_sha256']
    assert (root/'simulation.vvp').stat().st_size == program['program_bytes']
    assert hashlib.sha256((root/'simulation.vvp').read_bytes()).hexdigest() == program['program_sha256']
    command = [str(runtime/'usr/bin/vvp'), '-M', base, 'simulation.vvp']
os.execv(command[0], command)
'''


def _testbench(layout, configuration):
    if configuration.get('profile_version') == PROFILE_V4:
        from . import postroute_generic
        contract = postroute_generic.validate_binding(layout['verification_plan'], layout['settings'], configuration.get('functional_adapter'))
        return postroute_generic.functional_testbench(layout['verification_plan'], layout['settings'], contract)
    return functional_testbench(layout['verification_plan'], layout['settings'])


def _testbench_module(configuration):
    if configuration.get('profile_version') == PROFILE_V4:
        from . import postroute_generic
        descriptor = configuration.get('functional_adapter', {})
        value = descriptor.get('testbench_module')
        require(type(value) is str and re.fullmatch(postroute_generic.IDENTIFIER, value),
                'postroute_adapter_contract', 'Use the exact simple testbench module from the fixed adapter metadata.')
        return value
    return 'hullcirq_global_tb'


def _launcher(configuration):
    if configuration.get('profile_version') == PROFILE_V4:
        old = b"'-s', 'hullcirq_global_tb'"
        require(LAUNCHER.count(old) == 1, 'postroute_adapter_contract', 'The retained compiler launcher changed.')
        return LAUNCHER.replace(old, ("'-s', '" + _testbench_module(configuration) + "'").encode(), 1)
    return LAUNCHER


def _functional_report(stdout, layout, configuration, stderr=''):
    if configuration.get('profile_version') == PROFILE_V4:
        from . import postroute_generic
        contract = postroute_generic.validate_binding(layout['verification_plan'], layout['settings'], configuration.get('functional_adapter'))
        return postroute_generic.parse_functional(stdout, layout['verification_plan'], layout['settings'], contract, stderr)
    return parse_functional(stdout, layout['verification_plan'])


def _functional_command(folder, configuration, operation):
    runtime = configuration['physical_runtime']
    require(operation in ('compile', 'simulate'), 'postroute_execution', 'Unknown functional operation.')
    arguments = ['python3', _wsl_path(folder/'run_functional.py'), operation, sha(folder/'functional-inputs.json')]
    if operation == 'simulate':
        arguments.append(sha(folder/'functional-program.json'))
    return trusted_command(runtime, runtime['executable'], arguments, folder)


def _functional_commands(folder, configuration):
    return [_functional_command(folder, configuration, operation) for operation in ('compile', 'simulate')]


def _validate_functional_program(folder, configuration):
    manifest, program = load(folder/'functional-inputs.json'), load(folder/'functional-program.json')
    native_root = configuration['compiler']['executable'].rsplit('/usr/bin/', 1)[0]
    base = native_root + '/usr/lib/x86_64-linux-gnu/ivl'
    pins = _configuration_runtime_pins(configuration)
    command = [native_root + '/usr/bin/iverilog', '-B', base, '-g2005', '-DFUNCTIONAL', '-DUNIT_DELAY=', '-s', _testbench_module(configuration),
               '-o', 'simulation.vvp', 'primitives.v', 'cell_models.v', 'input.nl.v', 'functional-testbench.v']
    versions = load(folder/'functional-versions.json')
    require(manifest.get('runtime_root') == native_root and manifest.get('runtime_pins') == pins
            and versions.get('runtime_pins') == pins and versions.get('compiler') == command[0]
            and program.get('command') == command and program.get('input_manifest_sha256') == sha(folder/'functional-inputs.json')
            and program.get('version_report_sha256') == sha(folder/'functional-versions.json')
            and type(program.get('program_bytes')) is int and program['program_bytes'] > 0
            and file_stat((folder/'simulation.vvp')).st_size == program['program_bytes']
            and sha(folder/'simulation.vvp') == program.get('program_sha256'),
            'postroute_program', 'The compiled functional program must remain bound to its frozen inputs, runtime and version proof.')


FUNCTIONAL_INPUT_FILES = {'configuration.json', 'source-binding.json', 'verification-plan.json', 'public-vectors.json',
                          'input.nl.v', 'functional-testbench.v', 'cell_models.v', 'primitives.v',
                          'functional-models.json', 'run_functional.py'}


def _validate_functional_inputs(folder, layout, configuration, pdk):
    manifest = load(folder/'functional-inputs.json')
    items = manifest.get('files', [])
    require(type(items) is list and len(items) == len(FUNCTIONAL_INPUT_FILES)
            and {item.get('relative_path') for item in items} == FUNCTIONAL_INPUT_FILES,
            'postroute_source', 'Freeze every fixed functional input exactly once.')
    for item in items:
        path = folder/item['relative_path']
        require(path.resolve().is_relative_to(folder.resolve()) and sha(path) == item.get('sha256')
                and file_stat(path).st_size == item.get('bytes'), 'postroute_source', 'A frozen functional input changed.')
    models = load(folder/'functional-models.json')
    for name, relative in MODEL_FILES.items():
        descriptor = pdk['files'][relative]
        path = folder/(name+'.v')
        require(models.get(name) == descriptor and sha(path) == descriptor['sha256']
                and file_stat(path).st_size == descriptor['bytes'], 'postroute_pdk', 'Use the unchanged original PDK functional models.')
    inputs = lvs_tools.source_inputs(layout)
    require(object_hash(load(folder/'configuration.json')) == object_hash(configuration)
            and object_hash(load(folder/'verification-plan.json')) == layout['verification_plan_sha256']
            and object_hash(load(folder/'public-vectors.json')) == object_hash(layout['verification_plan']['public_boundary_vectors'])
            and sha(folder/'input.nl.v') == inputs['netlist']['sha256']
            and file_stat((folder/'input.nl.v')).st_size == inputs['netlist']['bytes']
            and read_bytes((folder/'functional-testbench.v')) == _testbench(layout, configuration).encode('utf-8')
            and read_bytes((folder/'run_functional.py')) == _launcher(configuration),
            'postroute_source', 'Retain the original plan, mapped circuit and fixed functional launcher.')


def run_functional(layout, configuration, folder, cancel_event=None, commands=None, source_binding=None):
    """Execute only the original-job functional part in a fresh caller directory.

    Used by the full adapter and isolated integration checks. It never performs
    STA, adoption, layout generation or project-history writes.
    """
    runtime, compiler, pdk, _ = _configuration(configuration)
    folder = Path(folder).resolve()
    require(folder.is_relative_to((ROOT/'.work').resolve()), 'postroute_path', 'Functional execution stays below HuLLCirq/.work.')
    folder.mkdir(parents=True, exist_ok=True)
    require(not any(folder.iterdir()), 'postroute_path', 'Functional execution requires a fresh empty directory.')
    plan = layout['verification_plan']
    inputs = source_inputs(layout, configuration)
    binding = source_binding if source_binding is not None else {
        'scope': 'isolated_original_job_functional_integration_not_S14_adoption', 'layout_run_id': layout['id'],
        'layout_record_sha256': object_hash(layout), 'source_inputs': inputs}
    for name, value in (('configuration.json', configuration), ('source-binding.json', binding),
                        ('verification-plan.json', plan), ('public-vectors.json', plan['public_boundary_vectors'])):
        _save(folder/name, value)
    _save(folder/'input.nl.v', read_bytes(Path(layout['checks']['artifacts_directory'])/inputs['netlist']['relative_path']))
    _save(folder/'functional-testbench.v', _testbench(layout, configuration).encode('utf-8'))
    models = {}
    for name, relative in MODEL_FILES.items():
        _save(folder/(name+'.v'), read_bytes(Path(pdk['root'])/relative))
        models[name] = pdk['files'][relative]
    _save(folder/'functional-models.json', models)
    _save(folder/'run_functional.py', _launcher(configuration))
    frozen = [{'relative_path': name, 'sha256': sha(folder/name), 'bytes': file_stat((folder/name)).st_size}
              for name in sorted(FUNCTIONAL_INPUT_FILES)]
    native_root = compiler['executable'].rsplit('/usr/bin/', 1)[0]
    _save(folder/'functional-inputs.json', {'files': frozen, 'runtime_root': native_root,
                                            'runtime_pins': _configuration_runtime_pins(configuration)})
    _validate_functional_inputs(folder, layout, configuration, pdk)
    executions = commands if commands is not None else []
    for operation in ('compile', 'simulate'):
        command = _functional_command(folder, configuration, operation)
        execution = physical._execute(command, runtime, folder, operation, cancel_event, 300)
        executions.append(execution)
        _save(folder/(operation+'-execution.json'), execution)
        _validate_execution(folder, operation, execution, command)
        _validate_functional_program(folder, configuration)
    require(file_stat((folder/'simulation.vcd')).st_size > 0, 'postroute_waveform', 'Retain the actual functional waveform.')
    functional = _functional_report(executions[-1]['stdout'], layout, configuration, executions[-1].get('stderr', ''))
    _save(folder/'functional-report.json', functional)
    return functional


def _validate_execution(folder, operation, record, command):
    logs = folder / operation
    if record.get('command') == command and record.get('status') == 'Cancelled':
        raise DomainError('postroute_cancelled', 'The fixed execution was cancelled; required checks did not complete.')
    require(record.get('command') == command and record.get('status') == 'Completed' and record.get('executed') is True
            and type(record.get('exit_code')) is int and record['exit_code'] == 0,
            'postroute_execution', 'Require a successful actual fixed execution.')
    request, terminal = load(logs/'request.json'), load(logs/'process-result.json')
    require(sha(logs/'worker.py') == physical.WORKER_V2_SHA and sha(logs/'request.json') == record['request_sha256']
            and sha(logs/'process-start.json') == record['process_start_sha256']
            and record.get('request_unchanged_at_completion') is True and record.get('worker_unchanged_at_completion') is True
            and request['argv'] == command[command.index('--exec')+1:]
            and all(object_hash(record[k]) == object_hash(v) for k, v in terminal.items())
            and record['stdout'] == read_text((logs/'stdout.log'),encoding='utf-8', errors='replace')
            and record['stderr'] == read_text((logs/'stderr.log'),encoding='utf-8', errors='replace'),
            'postroute_execution', 'Retain unchanged request, birth, terminal record and raw tool logs.')
    physical.validate_worker_binding(request, record, load(logs/'process-start.json'), folder, physical.WORKER_V2_SHA)


def parse_functional(stdout, plan):
    count = _output_count(plan)
    outputs = [{'index': int(a), 'value': int(b), 'cycle': int(c)} for a, b, c in
               re.findall(r'^HULLCIRQ_OUTPUT index=(\d+) value=(-?\d+) cycle=(\d+)$', stdout, re.M)]
    passed = (stdout.splitlines().count('HULLCIRQ_ROUTED_FUNCTIONAL_NO_SDF') == 1
              and stdout.splitlines().count(f"HULLCIRQ_GLOBAL_PASS outputs={count} vector_hash={plan['vector_hash']}") == 1
              and len([line for line in stdout.splitlines() if line.startswith('HULLCIRQ_OUTPUT')]) == count
              and 'HULLCIRQ_FAIL' not in stdout and 'ERROR' not in stdout and 'FATAL' not in stdout
              and [o['index'] for o in outputs] == list(range(count))
              and [o['value'] for o in outputs] == plan['recipe']['expected_outputs']
              and all(o['cycle'] > 0 and (i == 0 or o['cycle'] > outputs[i-1]['cycle']) for i, o in enumerate(outputs)))
    return {'validation_status': 'Passed' if passed else 'Failed', 'outputs': outputs,
            'vector_hash': plan['vector_hash'], 'testbench_sha256': plan['testbench_sha256'],
            'scope': 'original_GUI_job_external_values_protocol_reset_backpressure_and_completion',
            'logic': 'four_state_original_PDK_FUNCTIONAL_models', 'SDF_annotated': False,
            'limits': ['Finite original job; no exhaustive equivalence or dynamic SDF timing assertion.',
                       'Flattened internal public boundaries are covered by retained S10, not re-instrumented here.']}


def _bindings(lvs, drc, layout, configuration):
    return {**{f'{name}_{key}': value for name, run in (('layout', layout), ('drc', drc), ('lvs', lvs))
               for key, value in (('run_id', run['id']), ('record_sha256', object_hash(run)))},
            'input_gds_sha256': lvs['input_gds_sha256'], 'input_netlist_sha256': lvs['input_netlist_sha256'],
            'configuration_sha256': object_hash(configuration),
            **{k: layout[k] for k in ('verification_plan_sha256', 'vector_hash', 'testbench_sha256', 'public_boundary_vector_hash')}}


def _assessment(functional, sta):
    corners = sta['corners']
    checks = {name: {'validation_status': 'Passed'} for name in ('source_identity', 'configuration')}
    checks['functional'] = {'validation_status': functional['validation_status']}
    for name, key in (('parasitics', 'annotation_status'), ('constraints', 'constraint_coverage_status'),
                      ('setup_hold', 'setup_hold_status'), ('electrical', 'electrical_status')):
        checks[name] = {'validation_status': 'Passed' if all(c[key] == 'Passed' and c['timing_model_coverage_status'] == 'Passed' for c in corners) else 'Failed'}
    passed = all(c['validation_status'] == 'Passed' for c in checks.values()) and sta['validation_status'] == 'Passed'
    timing = {'corner_count': len(corners), 'clock_period_ns': sta['clock_period_ns'],
              **{key: max(c['metrics'][key] for c in corners) for key in ('setup_violations', 'hold_violations',
                    'max_slew_violations', 'max_cap_violations', 'max_fanout_violations')},
              'worst_setup_slack_ns': min(c['metrics']['setup_ws_ns'] for c in corners),
              'worst_hold_slack_ns': min(c['metrics']['hold_ws_ns'] for c in corners)}
    summary = {'method': METHOD, 'scope': SCOPE, 'functional_status': functional['validation_status'],
               'sta_status': sta['validation_status'], 'timing_summary': timing,
               'completion_criteria': [{'id': key, 'label': key.replace('_', ' ').title(),
                    'status': value['validation_status'], 'detail': 'Original GUI source and recorded physical conditions.'} for key, value in checks.items()],
               'reason': 'Original job and all required extracted STA checks passed.' if passed else 'Inspect failed criteria before advancing.'}
    return checks, summary, passed


def _validate_sta_binding(folder, sta, layout, runtime, inputs, annotation_policy=None):
    manifest = load(folder/'sta/sta-inputs.json')
    require(sta.get('layout_run_id') == layout['id'] and sta.get('layout_record_sha256') == object_hash(layout)
            and manifest.get('physical_runtime_sha256') == object_hash(runtime)
            and manifest.get('appimage_executable') == runtime['executable']
            and sta.get('clock_period_ns') == layout['settings']['clock_period_ns']
            and manifest.get('source_inventory_sha256') == inputs['timing_sources']['sha256']
            and sta.get('source_inventory_sha256') == inputs['timing_sources']['sha256']
            and sha(folder/'sta/inputs/netlist.v') == inputs['netlist']['sha256'],
            'postroute_source', 'Functional and extracted STA evidence must describe the same adopted circuit and runtime.')
    require(manifest.get('annotation_policy') == annotation_policy
            and sta.get('annotation_policy') == annotation_policy,
            'postroute_source', 'The actual extracted STA annotation policy must match the frozen profile version.')


def _artifacts(folder):
    files = {'input-netlist': 'input.nl.v', 'functional-testbench': 'functional-testbench.v', 'functional-models': 'functional-models.json',
             'functional-report': 'functional-report.json', 'frozen-verification-plan': 'verification-plan.json',
             'public-vectors': 'public-vectors.json', 'configuration': 'configuration.json', 'source-binding': 'source-binding.json',
             'tool-versions': 'tool-versions.json', 'worker-request': 'worker-requests.json', 'worker-report': 'worker-reports.json',
             'compile-stdout': 'compile/stdout.log', 'compile-stderr': 'compile/stderr.log',
             'simulation-stdout': 'simulate/stdout.log', 'simulation-stderr': 'simulate/stderr.log', 'simulation-waveform': 'simulation.vcd',
             'sta-report': 'sta-report.json', 'sta-log': 'sta-log.txt', 'sta-input-manifest': 'sta/sta-inputs.json',
             'sta-constraints': 'sta/inputs/physical.sdc', 'sta-parasitics': 'sta-parasitics.json', 'sta-liberty': 'sta-liberty.json',
             'completion-report': 'completion-report.json'}
    return [{'id': key, 'relative_path': relative, 'sha256': sha(folder/relative), 'bytes': file_stat((folder/relative)).st_size,
             'content_type': 'application/json' if relative.endswith('.json') else TEXT}
            for key, relative in files.items() if file_exists((folder/relative))]


def run_postlayout(lvs, drc, layout, configuration, cancel_event=None):
    runtime, compiler, pdk, working = _configuration(configuration)
    inputs = source_inputs(layout, configuration)
    require(all(object_hash(inputs[k]) == object_hash(lvs['source_inputs'][k]) for k in ('gds', 'def', 'netlist', 'powered_netlist'))
            and lvs['drc_record_sha256'] == object_hash(drc) and drc['layout_record_sha256'] == object_hash(layout),
            'postroute_source', 'Require the adopted current physical, DRC and LVS chain.')
    working.mkdir(parents=True, exist_ok=True)
    folder = Path(tempfile.mkdtemp(prefix='postroute-', dir=working))
    result = {'origin': 'trusted_fixed_postlayout_adapter', 'execution_scope': SCOPE, 'verification_supported': True,
              'status': 'Completed', 'validation_status': 'Failed', 'executed': False, 'exit_code': None,
              'cleanup_unresolved': False, 'commands': [], 'diagnostics': [], 'metrics': {}, 'checks': {},
              'artifacts_directory': str(folder), **_bindings(lvs, drc, layout, configuration)}
    try:
        functional = run_functional(layout, configuration, folder, cancel_event, result['commands'],
            {**_bindings(lvs, drc, layout, configuration), 'source_inputs': inputs})
        result.update(executed=True, exit_code=0, cleanup_unresolved=False)
        policy = _annotation_policy(configuration)
        prepared = postroute_sta.prepare_sta(layout, runtime, folder/'sta', **({'annotation_policy': policy} if policy is not None else {}))
        executions = {}
        for spec in prepared['commands']:
            execution = physical._execute(spec['command'], runtime, folder/'sta', spec['operation'], cancel_event, spec['timeout'])
            executions[spec['corner']] = execution
            result['commands'].append(execution)
            result['cleanup_unresolved'] = execution.get('cleanup_unresolved') is True
            _validate_execution(folder/'sta', spec['operation'], execution, spec['command'])
        sta = postroute_sta.collect_sta(folder/'sta', executions)
        _save(folder/'sta-report.json', sta)
        _save(folder/'sta-log.txt', b'\n'.join(read_bytes((folder/'sta/reports'/f'{c}.log')) for c in postroute_sta.CORNERS))
        for key, suffix in (('sta-parasitics', '.spef'), ('sta-liberty', '.lib')):
            _save(folder/(key+'.json'), {'files': [f for f in prepared['manifest']['files'] if f['relative_path'].endswith(suffix)]})
        checks, summary, passed = _assessment(functional, sta)
        _save(folder/'completion-report.json', summary)
        _save(folder/'tool-versions.json', {'functional': load(folder/'functional-versions.json'), 'sta': [c['runtime'] for c in sta['corners']], 'appimage_sha256': runtime['appimage_sha256']})
        result.update(checks=checks, summary=summary, metrics=summary['timing_summary'], validation_status='Passed' if passed else 'Failed', exit_code=0)
    except (DomainError, OSError, ValueError, KeyError, TypeError) as error:
        if result['commands']:
            last = result['commands'][-1]
            result.update(executed=any(item.get('executed') is True for item in result['commands']),
                          exit_code=last.get('exit_code'), cleanup_unresolved=last.get('cleanup_unresolved') is True)
            if last.get('status') == 'Cancelled':
                result.update(status='Cancelled', validation_status='Not Checked')
        if not (getattr(error, 'code', None) == 'postroute_cancelled' and result['commands']
                and physical._record_cancelled_command(result, result['commands'][-1], 'postroute')):
            result['diagnostics'].append({'code': getattr(error, 'code', 'postroute_error'), 'severity': 'error', 'message': str(error)})
    finally:
        _save(folder/'worker-requests.json', {'requests': [load(path) for path in sorted(artifact_files(folder)) if path.name=='request.json']})
        _save(folder/'worker-reports.json', {'executions': result['commands']})
        result['artifacts'] = _artifacts(folder)
    return result


def _validate_complete_postlayout_result(result, lvs, drc, layout, configuration, expected_status):
    runtime, _, pdk, _ = _configuration(configuration)
    folder = Path(result['artifacts_directory']).resolve()
    require(result.get('origin') == 'trusted_fixed_postlayout_adapter' and result.get('execution_scope') == SCOPE
            and result.get('validation_status') == expected_status and len(result.get('commands', [])) == 11
            and all(result.get(k) == v for k, v in _bindings(lvs, drc, layout, configuration).items()),
            'postroute_proof', 'Require complete source-bound functional plus nine-corner STA evidence.')
    inputs = source_inputs(layout, configuration)
    require(object_hash(load(folder/'configuration.json')) == object_hash(configuration)
            and object_hash(load(folder/'source-binding.json')) == object_hash({**_bindings(lvs, drc, layout, configuration), 'source_inputs': inputs})
            and object_hash(load(folder/'verification-plan.json')) == layout['verification_plan_sha256']
            and sha(folder/'input.nl.v') == inputs['netlist']['sha256']
            and read_bytes((folder/'functional-testbench.v')) == _testbench(layout, configuration).encode('utf-8')
            and read_bytes((folder/'run_functional.py')) == _launcher(configuration),
            'postroute_source', 'Frozen inputs and original workload must remain unchanged.')
    _validate_functional_inputs(folder, layout, configuration, pdk)
    _validate_functional_program(folder, configuration)
    for operation, record, command in zip(('compile', 'simulate'), result['commands'], _functional_commands(folder, configuration)):
        _validate_execution(folder, operation, record, command)
    functional = _functional_report(result['commands'][1]['stdout'], layout, configuration, result['commands'][1].get('stderr', ''))
    sta = postroute_sta.collect_sta(folder/'sta', dict(zip(postroute_sta.CORNERS, result['commands'][2:])))
    _validate_sta_binding(folder, sta, layout, runtime, inputs, _annotation_policy(configuration))
    checks, summary, passed = _assessment(functional, sta)
    require(passed == (expected_status == 'Passed')
            and object_hash(checks) == object_hash(result['checks']) and object_hash(summary) == object_hash(result['summary'])
            and object_hash(functional) == object_hash(load(folder/'functional-report.json'))
            and object_hash(sta) == object_hash(load(folder/'sta-report.json'))
            and object_hash(summary) == object_hash(load(folder/'completion-report.json'))
            and object_hash(result['artifacts']) == object_hash(_artifacts(folder)),
            'postroute_proof', 'The reports must reproduce the functional transcript and actual extracted STA checks.')


def validate_postlayout_result(result, lvs, drc, layout, configuration):
    _validate_complete_postlayout_result(result, lvs, drc, layout, configuration, 'Passed')


def validate_failed_postlayout_result(result, lvs, drc, layout, configuration):
    """Verify complete failed evidence before preparing a physical correction.

    This performs the same source, process, frozen-file and report reproduction
    checks as the Passed validator, while requiring an actually Failed result.
    It does not adopt or rewrite that result.
    """
    _validate_complete_postlayout_result(result, lvs, drc, layout, configuration, 'Failed')
