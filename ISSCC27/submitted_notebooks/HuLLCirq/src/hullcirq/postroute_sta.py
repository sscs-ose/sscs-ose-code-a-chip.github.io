"""Fresh nine-corner STA of a saved physical circuit, without SDF simulation.

The analysis uses the original Liberty, extracted SPEF and physical SDC. Setup /
hold, constraint coverage, parasitic coverage and electrical limits are reported
separately; electrical violations are failures, never implicit waivers.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import re

from . import physical_tools as physical
from .drc_tools import _safe
from .domain import VERILOG_IDENTIFIER, VERILOG_KEYWORDS
from .lvs_tools import _flat_netlist, _pointer_relative
from .verification import object_hash, trusted_command, _wsl_path

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = 'hullcirq-postroute-sta-v1'
ANNOTATION_V2 = 'unconnected-clock-load-output-v2'
LEGACY_TOP_MODULE = 'hullcirq_npu'
LEGACY_CLOCK_NAME = 'clk'
STA_BINARY_SHA256 = '81df2b09dfc05972a8982fe5ad092e045abe2ceaa15d3315d5364f7569715d22'
CORNERS = tuple(f'{rc}_{pvt}' for rc in ('nom', 'min', 'max')
                for pvt in ('tt_025C_1v80', 'ss_100C_1v60', 'ff_n40C_1v95'))
ENV_KEYS = ('CLOCK_PERIOD', 'CLOCK_PORT', 'MAX_FANOUT_CONSTRAINT',
            'MAX_TRANSITION_CONSTRAINT', 'MAX_CAPACITANCE_CONSTRAINT',
            'SYNTH_DRIVING_CELL', 'OUTPUT_CAP_LOAD', 'CLOCK_UNCERTAINTY_CONSTRAINT',
            'CLOCK_TRANSITION_CONSTRAINT', 'TIME_DERATING_CONSTRAINT', 'IO_DELAY_CONSTRAINT')
METRICS = ('setup_ws_ns', 'hold_ws_ns', 'setup_tns_ns', 'hold_tns_ns',
           'setup_violations', 'hold_violations', 'max_slew_violations',
           'max_cap_violations', 'max_fanout_violations', 'clock_count',
           'clock_period_ns', 'clock_propagated', 'clock_virtual', 'register_clock_pins')
require, sha, load = physical.require, physical.sha, physical.load


def _save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as handle:
        handle.write(data)


def _json(value):
    return (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode('utf-8')


def _quoted(path):
    value = _wsl_path(Path(path))
    require(not any(c in value for c in '{}\r\n'), 'postroute_sta_path', 'Unsupported Tcl filename.')
    return '{' + value + '}'


def _identifier(value, field):
    require(type(value) is str and VERILOG_IDENTIFIER.fullmatch(value) is not None
            and value not in VERILOG_KEYWORDS,
            'postroute_sta_identifier',
            'The saved ' + field + ' must be one plain non-keyword Verilog identifier.')
    return value


def _tcl_identifier(value):
    """Return one literal Tcl word while preserving the legacy common case."""
    return '{' + value + '}' if '$' in value else value


def _layout_identifiers(layout):
    settings = layout.get('settings') if type(layout) is dict else None
    require(type(settings) is dict, 'postroute_sta_identifier',
            'The selected layout must retain its saved design settings.')
    return (_identifier(settings.get('top_module'), 'DUT top module'),
            _identifier(settings.get('clock_name'), 'clock name'))


def _record_identifiers(record):
    """Resolve an explicit v1 binding or the one exact historical default."""
    require(type(record) is dict, 'postroute_sta_identifier', 'The STA binding record must be an object.')
    present = ('top_module' in record, 'clock_name' in record)
    require(present[0] == present[1], 'postroute_sta_identifier',
            'The STA top module and clock binding must be recorded together.')
    if not present[0]:
        return LEGACY_TOP_MODULE, LEGACY_CLOCK_NAME, False
    return (_identifier(record['top_module'], 'DUT top module'),
            _identifier(record['clock_name'], 'clock name'), True)


def _environment(text):
    values = {}
    for key in ENV_KEYS:
        found = re.findall(r'^set ::env\(' + re.escape(key) + r'\) ([A-Za-z0-9_./+-]+)$', text, re.M)
        require(len(found) == 1, 'postroute_sta_environment', 'Missing or ambiguous physical constraint: ' + key)
        values[key] = found[0]
    return values


def _script(corner, values, files, top_module=LEGACY_TOP_MODULE, clock_name=LEGACY_CLOCK_NAME):
    top_module = _identifier(top_module, 'DUT top module')
    clock_name = _identifier(clock_name, 'clock name')
    setup = '\n'.join(f'set ::env({key}) {{{value}}}' for key, value in values.items())
    return ('''# HuLLCirq fresh post-route STA; original constraints remain unchanged.
if {[catch {
set_cmd_units -time ns -capacitance pF -current mA -voltage V -resistance kOhm -distance um
set sta_report_default_digits 9
''' + setup + f'''
define_corners {corner}
read_liberty -corner {corner} {_quoted(files['liberty'])}
read_verilog {_quoted(files['netlist'])}
link_design {_tcl_identifier(top_module)}
read_sdc {_quoted(files['sdc'])}
read_spef -corner {corner} {_quoted(files['spef'])}
puts HULLCIRQ_BEGIN_SETUP
report_checks -path_delay max -sort_by_slack -group_path_count 10 -fields {{slew cap input net fanout}} -format full_clock_expanded -corner {corner}
puts HULLCIRQ_END_SETUP
puts HULLCIRQ_BEGIN_HOLD
report_checks -path_delay min -sort_by_slack -group_path_count 10 -fields {{slew cap input net fanout}} -format full_clock_expanded -corner {corner}
puts HULLCIRQ_END_HOLD
puts HULLCIRQ_BEGIN_COVERAGE
check_setup -verbose -unconstrained_endpoints -multiple_clock -no_clock -no_input_delay -loops -generated_clocks
puts HULLCIRQ_END_COVERAGE
puts HULLCIRQ_BEGIN_ANNOTATION
report_parasitic_annotation -report_unannotated
puts HULLCIRQ_END_ANNOTATION
puts HULLCIRQ_BEGIN_ELECTRICAL
report_check_types -max_slew -max_capacitance -max_fanout -violators -corner {corner}
puts HULLCIRQ_END_ELECTRICAL
puts HULLCIRQ_BEGIN_METRICS
puts "setup_ws_ns [worst_slack -corner {corner} -max]"
puts "hold_ws_ns [worst_slack -corner {corner} -min]"
puts "setup_tns_ns [total_negative_slack -corner {corner} -max]"
puts "hold_tns_ns [total_negative_slack -corner {corner} -min]"
foreach {{kind delay}} {{setup max hold min}} {{
    set count 0
    foreach path [find_timing_paths -unique_paths_to_endpoint -path_delay $delay -sort_by_slack -group_path_count 1000000 -slack_max 0 -corner {corner}] {{
        if {{[get_property $path slack] < 0}} {{incr count}}
    }}
    puts "${{kind}}_violations $count"
}}
puts "max_slew_violations [sta::max_slew_violation_count]"
puts "max_cap_violations [sta::max_capacitance_violation_count]"
puts "max_fanout_violations [sta::max_fanout_violation_count]"
puts "clock_count [llength [all_clocks]]"
set clock [get_clocks {_tcl_identifier(clock_name)}]
puts "clock_period_ns [get_property $clock period]"
puts "clock_propagated [get_property $clock is_propagated]"
puts "clock_virtual [get_property $clock is_virtual]"
puts "register_clock_pins [llength [all_registers -clock_pins]]"
puts HULLCIRQ_END_METRICS
puts HULLCIRQ_STA_COMPLETE_{corner}
''' + '''} failure]} {
    puts stderr "HULLCIRQ_STA_ERROR $failure"
    exit 1
}
exit 0
''').encode('utf-8')


LAUNCHER = '''"""Frozen bounded OpenSTA launcher, called inside the pinned AppImage."""
import hashlib, json, os, pathlib, shutil, subprocess, sys
root = pathlib.Path(__file__).resolve().parent
corner, expected = sys.argv[1:]
raw = (root / 'sta-inputs.json').read_bytes()
assert hashlib.sha256(raw).hexdigest() == expected, 'STA manifest changed'
manifest = json.loads(raw)
assert corner in manifest['corners'], 'Unknown corner'
for item in manifest['files']:
    path = root / item['relative_path']
    with path.open('rb') as handle:
        assert hashlib.file_digest(handle, 'sha256').hexdigest() == item['sha256'], str(path)
    assert path.stat().st_size == item['bytes']
sta = shutil.which('sta')
assert sta and sta.startswith('/nix/store/'), 'Require pinned AppImage OpenSTA'
version = subprocess.run([sta, '-version'], capture_output=True, timeout=20, check=True)
assert b'2.7.0' in version.stdout, 'Unexpected OpenSTA version'
runtime = {'executable': sta, 'version': version.stdout.decode(), 'pid': os.getpid(),
           'executable_sha256': hashlib.sha256(pathlib.Path(sta).read_bytes()).hexdigest()}
assert runtime['executable_sha256'] == manifest['sta_binary_sha256'], 'Pinned OpenSTA binary changed'
with (root / 'reports' / (corner + '.runtime.json')).open('x') as output:
    json.dump(runtime, output, indent=2)
with (root / 'reports' / (corner + '.log')).open('xb') as output:
    result = subprocess.run([sta, '-no_splash', '-exit', str(root / 'scripts' / (corner + '.tcl'))],
                            cwd=root, stdout=output, stderr=subprocess.STDOUT, timeout=240)
print('HULLCIRQ_STA_LAUNCH_COMPLETE', corner, result.returncode, flush=True)
sys.exit(result.returncode)
'''.encode('utf-8')


def source_inventory(layout, physical_config):
    """Observe exact STA sources derived from the selected layout and pinned PDK.

    This is also the freshness descriptor used before/after an S14 execution.
    No caller-supplied frozen-manifest source path is used for discovery.
    """
    require(object_hash(physical_config) == object_hash(layout['runtime_configuration']),
            'postroute_sta_source', 'Inherit the exact physical runtime of the selected layout.')
    top_module, clock_name = _layout_identifiers(layout)
    require(tuple(physical_config['profile']['config']['STA_CORNERS']) == CORNERS,
            'postroute_sta_corners', 'Retain all nine selected STA corners.')
    pdk_file = Path(physical_config['pdk_manifest_path'])
    require(sha(pdk_file) == physical_config['pdk_manifest_sha256'],
            'postroute_sta_pdk', 'The pinned PDK manifest changed.')
    pdk = load(pdk_file)
    folder = Path(layout['checks']['artifacts_directory']).resolve()
    artifacts = {item['id']: item for item in layout['checks']['artifacts']}
    for name in ('netlist', 'final-state', 'sdc'):
        entry = artifacts[name]
        path = _safe(folder, entry['relative_path'])
        require(sha(path) == entry['sha256'] and path.stat().st_size == entry['bytes'],
                'postroute_sta_source', 'Saved physical input changed: ' + name)
    state = physical.load_tool_json(_safe(folder, artifacts['final-state']['relative_path']))
    require(_pointer_relative(state['nl'], folder) == artifacts['netlist']['relative_path']
            and set(state['spef']) == {'nom_*', 'min_*', 'max_*'} and set(state['sdf']) == set(CORNERS),
            'postroute_sta_source', 'Final state must bind the selected netlist and all nine extracted corners.')
    files = []

    def observe(source, relative, origin):
        source = Path(source).resolve()
        item = {'relative_path': relative, 'source_path': str(source),
                'sha256': sha(source), 'bytes': source.stat().st_size, 'origin': origin}
        files.append(item)

    observe(folder / artifacts['netlist']['relative_path'], 'inputs/netlist.v', 'retained_S11_netlist')
    observe(folder / artifacts['sdc']['relative_path'], 'inputs/physical.sdc', 'retained_original_physical_SDC')
    observe(folder / artifacts['final-state']['relative_path'], 'inputs/physical-final-state.json', 'retained_S11_final_state')
    for rc in ('nom', 'min', 'max'):
        observe(_safe(folder, _pointer_relative(state['spef'][rc + '_*'], folder)),
                f'inputs/{rc}.spef', 'S11_final_state_pointer_observed_at_new_S14')
    for pvt in ('tt_025C_1v80', 'ss_100C_1v60', 'ff_n40C_1v95'):
        relative = f'libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__{pvt}.lib'
        source = _safe(Path(pdk['root']), relative)
        entry = pdk['files'][relative]
        require(sha(source) == entry['sha256'] and source.stat().st_size == entry['bytes'],
                'postroute_sta_pdk', 'Pinned Liberty changed: ' + pvt)
        observe(source, f'inputs/{pvt}.lib', 'pinned_original_PDK_Liberty')
    common_values = None
    for corner in CORNERS:
        source_dir = _safe(folder, _pointer_relative(state['sdf'][corner], folder)).parent
        candidates = list(source_dir.glob('_env*.tcl'))
        require(len(candidates) == 1, 'postroute_sta_environment', 'Require one original per-corner constraint environment.')
        observe(candidates[0], f'inputs/{corner}.env.tcl', 'original_physical_constraint_environment')
        values = _environment(candidates[0].read_text(encoding='utf-8'))
        require(values['CLOCK_PORT'] == clock_name
                and float(values['CLOCK_PERIOD']) == layout['settings']['clock_period_ns'],
                'postroute_sta_clock', 'STA must retain the original GUI clock constraint.')
        require(common_values is None or values == common_values,
                'postroute_sta_environment', 'The corner constraints differ.')
        common_values = values
    inventory = {'layout_run_id': layout['id'], 'layout_record_sha256': object_hash(layout),
                 'physical_runtime_sha256': object_hash(physical_config), 'corners': list(CORNERS),
                 'clock_period_ns': layout['settings']['clock_period_ns'], 'constraints': common_values,
                 'files': files}
    if (top_module, clock_name) != (LEGACY_TOP_MODULE, LEGACY_CLOCK_NAME):
        inventory.update(top_module=top_module, clock_name=clock_name)
    return inventory


def _validate_annotation_policy(annotation_policy):
    require(annotation_policy in (None, ANNOTATION_V2), 'postroute_sta_annotation_policy',
            'Use the recorded supported parasitic annotation policy.')


def _liberty_block(text, kind, name):
    """Read one exact balanced Liberty group, retaining nested model tables."""
    matches = list(re.finditer(r'\b' + re.escape(kind) + r'\s*\(\s*"' + re.escape(name) + r'"\s*\)\s*\{', text))
    require(len(matches) == 1, 'postroute_sta_annotation_model', 'Require one exact Liberty ' + kind + ': ' + name)
    start = matches[0].end()
    index, depth, quoted, escaped, line_comment, block_comment = start, 1, False, False, False, False
    while index < len(text):
        char = text[index]
        pair = text[index:index + 2]
        if line_comment:
            line_comment = char != '\n'
        elif block_comment:
            if pair == '*/':
                block_comment = False
                index += 1
        elif quoted:
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == '"':
                quoted = False
        elif pair in ('//', '/*'):
            line_comment, block_comment = pair == '//', pair == '/*'
            index += 1
        elif char == '"':
            quoted = True
        elif char == '{':
            depth += 1
        elif char == '}':
            depth -= 1
            if depth == 0:
                return text[start:index]
        index += 1
    require(False, 'postroute_sta_annotation_model', 'A required Liberty group is truncated: ' + name)


def _annotation_qualification(files, frozen_root=None):
    """Qualify the one new unused-output cell from every pinned PVT model.

    This does not exclude connected drivers. It establishes only inv_6's exact
    input/output semantics before the V2 parser can classify an omitted Y pin.
    """
    models = []
    for pvt in ('tt_025C_1v80', 'ss_100C_1v60', 'ff_n40C_1v95'):
        relative = 'inputs/' + pvt + '.lib'
        entries = [item for item in files if item.get('relative_path') == relative]
        require(len(entries) == 1, 'postroute_sta_annotation_model', 'Qualify every original PVT Liberty model.')
        entry = entries[0]
        path = Path(entry['source_path']) if frozen_root is None else _safe(frozen_root, relative)
        raw = path.read_bytes()
        require(len(raw) == entry['bytes'] and hashlib.sha256(raw).hexdigest() == entry['sha256'],
                'postroute_sta_annotation_model', 'The qualified Liberty must match the frozen pinned input.')
        cell = _liberty_block(raw.decode('utf-8'), 'cell', 'sky130_fd_sc_hd__inv_6')
        pins = re.findall(r'\bpin\s*\(\s*"([^"]+)"\s*\)\s*\{', cell)
        require(sorted(pins) == ['A', 'Y'], 'postroute_sta_annotation_model',
                'The qualified inverter must have only the original A and Y signal pins.')
        input_pin, output_pin = (_liberty_block(cell, 'pin', pin) for pin in ('A', 'Y'))
        input_direction = re.findall(r'^\s*direction\s*:\s*"?([A-Za-z_]+)"?\s*;', input_pin, re.M)
        output_direction = re.findall(r'^\s*direction\s*:\s*"?([A-Za-z_]+)"?\s*;', output_pin, re.M)
        functions = re.findall(r'^\s*function\s*:\s*"([^"]+)"\s*;', output_pin, re.M)
        require(input_direction == ['input'] and output_direction == ['output'] and len(functions) == 1
                and re.sub(r'\s+', '', functions[0]) in ('!A', '(!A)'),
                'postroute_sta_annotation_model', 'Require the pinned inv_6 A-input / Y-output inverter function.')
        models.append({'relative_path': relative, 'sha256': entry['sha256'], 'bytes': entry['bytes'],
                       'input_pin': 'A', 'input_direction': 'input', 'output_pin': 'Y',
                       'output_direction': 'output', 'output_function': '!A'})
    return {'cell': 'sky130_fd_sc_hd__inv_6', 'liberty_models': models,
            'classification_requires': ['clkload_numbered_instance', 'connected_A_input', 'omitted_or_empty_Y_output']}


def prepare_sta(layout, physical_config, output_dir, *, annotation_policy=None):
    """Freeze exact saved inputs; return nine supervised command specifications.

    ``output_dir`` must not exist. This prepares, but does not execute, tools.
    The caller must save each actual execution dictionary alongside its corner.
    """
    _validate_annotation_policy(annotation_policy)
    output = Path(output_dir).resolve()
    require(not output.exists(), 'postroute_sta_output', 'Use a fresh STA output directory.')
    require(physical_config['appimage_sha256'] == physical.IMAGE_SHA
            and sha(physical_config['appimage_path']) == physical.IMAGE_SHA
            and physical_config['executable'] == _wsl_path(Path(physical_config['appimage_path'])),
            'postroute_sta_runtime', 'The pinned physical runtime changed.')
    inventory = source_inventory(layout, physical_config)
    top_module, clock_name, explicit_binding = _record_identifiers(inventory)
    require((top_module, clock_name) == _layout_identifiers(layout),
            'postroute_sta_source', 'The STA inventory must bind the selected layout top and clock.')
    qualification = _annotation_qualification(inventory['files']) if annotation_policy == ANNOTATION_V2 else None
    output.mkdir(parents=True)
    (output / 'reports').mkdir()
    files = list(inventory['files'])
    for item in files:
        raw = Path(item['source_path']).read_bytes()
        require(len(raw) == item['bytes'] and hashlib.sha256(raw).hexdigest() == item['sha256'],
                'postroute_sta_source', 'An STA source changed during input freezing.')
        _save(output / item['relative_path'], raw)
    common_values = inventory['constraints']
    for corner in CORNERS:
        rc, pvt = corner.split('_', 1)
        values = _environment((output / 'inputs' / (corner + '.env.tcl')).read_text(encoding='utf-8'))
        require(values == common_values, 'postroute_sta_source', 'The frozen corner environment changed.')
        _save(output / 'scripts' / f'{corner}.tcl', _script(corner, values,
              {'netlist': output / 'inputs/netlist.v', 'sdc': output / 'inputs/physical.sdc',
               'spef': output / 'inputs' / (rc + '.spef'), 'liberty': output / 'inputs' / (pvt + '.lib')},
              top_module, clock_name))
    _save(output / 'run_sta.py', LAUNCHER)
    _save(output / 'layout-source.json', _json(layout))
    for source in [output / 'run_sta.py', output / 'layout-source.json', *sorted((output / 'scripts').glob('*.tcl'))]:
        files.append({'relative_path': source.relative_to(output).as_posix(), 'source_path': None,
                      'sha256': sha(source), 'bytes': source.stat().st_size, 'origin': 'development_assistant_STA_adapter'})
    manifest = {'schema': SCHEMA, 'corners': list(CORNERS), 'files': files, 'source_inventory_sha256': object_hash(inventory),
                'layout_run_id': layout['id'], 'layout_record_sha256': object_hash(layout),
                'physical_runtime_sha256': object_hash(physical_config), 'clock_period_ns': layout['settings']['clock_period_ns'],
                'constraints': common_values, 'appimage_sha256': physical.IMAGE_SHA,
                'appimage_executable': physical_config['executable'],
                'sta_binary_sha256': STA_BINARY_SHA256,
                'scope': 'fresh_extracted_STA_not_dynamic_SDF_simulation'}
    if explicit_binding:
        manifest.update(top_module=top_module, clock_name=clock_name)
    if annotation_policy == ANNOTATION_V2:
        manifest.update(annotation_policy=annotation_policy, annotation_policy_qualification=qualification)
    _save(output / 'sta-inputs.json', _json(manifest))
    manifest_hash = sha(output / 'sta-inputs.json')
    commands = [{'corner': corner, 'operation': 'sta-' + corner, 'timeout': 300,
                 'command': trusted_command(physical_config, physical_config['executable'],
                            ['python3', _wsl_path(output / 'run_sta.py'), corner, manifest_hash], output)}
                for corner in CORNERS]
    return {'manifest': manifest, 'manifest_sha256': manifest_hash, 'commands': commands,
            'output_directory': str(output)}


def _section(text, name):
    pattern = r'^HULLCIRQ_BEGIN_' + name + r'\r?\n(.*?)^HULLCIRQ_END_' + name + r'\r?$'
    found = re.findall(pattern, text, re.M | re.S)
    require(len(found) == 1, 'postroute_sta_report', 'Missing, duplicate or truncated report section: ' + name)
    return found[0]


def parse_corner(text, corner, netlist_text, clock_period_ns, *, annotation_policy=None):
    """Parse complete actual reports. Empty/missing/unknown data cannot pass."""
    _validate_annotation_policy(annotation_policy)
    require(corner in CORNERS and text.count('HULLCIRQ_STA_COMPLETE_' + corner) == 1
            and not re.search(r'(^Error:|HULLCIRQ_STA_ERROR)', text, re.M),
            'postroute_sta_report', 'The actual OpenSTA report did not complete successfully.')
    metrics = {}
    for line in _section(text, 'METRICS').splitlines():
        key, value = line.split()
        require(key in METRICS and key not in metrics, 'postroute_sta_report', 'Unexpected or duplicate STA metric.')
        parsed = float(value)
        require(math.isfinite(parsed), 'postroute_sta_report', 'Nonfinite STA metrics cannot pass.')
        metrics[key] = parsed
    require(set(metrics) == set(METRICS), 'postroute_sta_report', 'Missing required STA metrics.')
    for key in METRICS:
        if key.endswith('violations') or key.startswith('clock_') and key != 'clock_period_ns' or key == 'register_clock_pins':
            require(metrics[key] >= 0 and metrics[key].is_integer(), 'postroute_sta_report', 'Invalid metric count.')
            metrics[key] = int(metrics[key])
    coverage = _section(text, 'COVERAGE').strip()
    setup = _section(text, 'SETUP')
    hold = _section(text, 'HOLD')
    require('Startpoint:' in setup and 'Endpoint:' in setup and 'Startpoint:' in hold and 'Endpoint:' in hold,
            'postroute_sta_report', 'Require real setup and hold paths.')
    electrical = _section(text, 'ELECTRICAL')
    annotation = _section(text, 'ANNOTATION')
    complete = re.search(r'Found ([0-9]+) unannotated drivers\.\s*(.*?)Found ([0-9]+) partially unannotated drivers\.', annotation, re.S)
    require(complete is not None, 'postroute_sta_report', 'Missing parasitic annotation coverage.')
    names = complete[2].split()
    require(len(names) == int(complete[1]) and len(set(names)) == len(names),
            'postroute_sta_report', 'Incomplete unannotated-driver list.')
    logical = _flat_netlist(netlist_text)
    warnings = [line for line in text.splitlines() if line.startswith('Warning:')]
    unresolved_warnings = []
    for warning in warnings:
        missing = re.search(r'module (sky130_fd_sc_hd__(?:fill|decap|tapvpwrvgnd)_\d+) not found\. Creating black box for ([A-Za-z0-9_]+)\.', warning)
        instance = logical['instances'].get(missing[2]) if missing else None
        if not (missing and instance and instance['cell'] == missing[1] and not instance['pins']):
            unresolved_warnings.append(warning)
    dangling = []
    connected = []
    for name in names:
        instance, pin = name.rsplit('/', 1)
        cell = logical['instances'].get(instance)
        output_pin = ('X' if cell and re.fullmatch(r'sky130_fd_sc_hd__(?:clkbuf|buf)_\d+', cell['cell']) else
                      'Y' if cell and re.fullmatch(r'sky130_fd_sc_hd__(?:clkinv|clkinvlp|bufinv)_\d+', cell['cell']) else None)
        if annotation_policy == ANNOTATION_V2 and cell and cell['cell'] == 'sky130_fd_sc_hd__inv_6':
            output_pin = 'Y'
        if (cell is not None and re.fullmatch(r'clkload[0-9]+', instance) and pin == output_pin
                and cell['pins'].get(pin) in (None, '') and cell['pins'].get('A')):
            dangling.append({'pin': name, 'cell': cell['cell'], 'connection': cell['pins'].get(pin),
                             'reason': 'unconnected_clock_load_output_in_original_netlist',
                             'Verilog_representation': 'omitted_named_port' if pin not in cell['pins'] else 'empty_named_port'})
        else:
            connected.append(name)
    setup_hold_pass = all(metrics[key] >= 0 for key in ('setup_ws_ns', 'hold_ws_ns')) and all(
        metrics[key] == 0 for key in ('setup_tns_ns', 'hold_tns_ns', 'setup_violations', 'hold_violations'))
    electrical_pass = all(metrics[key] == 0 for key in ('max_slew_violations', 'max_cap_violations', 'max_fanout_violations'))
    require(electrical_pass == ('(VIOLATED)' not in electrical), 'postroute_sta_report', 'Electrical metrics and report disagree.')
    coverage_pass = not coverage and metrics['clock_count'] == 1 and metrics['clock_period_ns'] == clock_period_ns and metrics['clock_propagated'] == 1 and metrics['clock_virtual'] == 0 and metrics['register_clock_pins'] > 0
    annotation_pass = not connected and int(complete[3]) == 0
    report = {'corner': corner, 'validation_status': 'Passed' if all((setup_hold_pass, electrical_pass, coverage_pass, annotation_pass, not unresolved_warnings)) else 'Failed',
            'metrics': metrics, 'setup_hold_status': 'Passed' if setup_hold_pass else 'Failed',
            'electrical_status': 'Passed' if electrical_pass else 'Failed',
            'constraint_coverage_status': 'Passed' if coverage_pass else 'Failed', 'constraint_coverage_report': coverage,
            'annotation_status': 'Passed' if annotation_pass else 'Failed', 'unannotated_count': len(names),
            'partially_unannotated_count': int(complete[3]), 'unconnected_clock_load_outputs': dangling,
            'unresolved_unannotated_drivers': connected,
            'warnings': warnings, 'unresolved_warnings': unresolved_warnings,
            'timing_model_coverage_status': 'Passed' if not unresolved_warnings else 'Failed', 'waivers': []}
    if annotation_policy == ANNOTATION_V2:
        report['annotation_policy'] = annotation_policy
    return report


def collect_sta(output_dir, executions):
    """Collect nine actual supervised runs. ``executions`` maps corner to result."""
    output = Path(output_dir).resolve()
    manifest = load(output / 'sta-inputs.json')
    annotation_policy = manifest.get('annotation_policy')
    _validate_annotation_policy(annotation_policy)
    require('annotation_policy' not in manifest and 'annotation_policy_qualification' not in manifest
            or annotation_policy == ANNOTATION_V2,
            'postroute_sta_annotation_policy', 'A new annotation qualification must explicitly select its supported policy.')
    require(manifest.get('schema') == SCHEMA and tuple(manifest.get('corners', ())) == CORNERS
            and set(executions) == set(CORNERS), 'postroute_sta_report', 'Require exactly nine executed corners.')
    expected_files = {'inputs/netlist.v', 'inputs/physical.sdc', 'inputs/physical-final-state.json', 'run_sta.py', 'layout-source.json'}
    expected_files.update('inputs/' + rc + '.spef' for rc in ('nom', 'min', 'max'))
    expected_files.update('inputs/' + pvt + '.lib' for pvt in ('tt_025C_1v80', 'ss_100C_1v60', 'ff_n40C_1v95'))
    expected_files.update('inputs/' + c + '.env.tcl' for c in CORNERS)
    expected_files.update('scripts/' + c + '.tcl' for c in CORNERS)
    names = [item['relative_path'] for item in manifest['files']]
    require(set(names) == expected_files and len(names) == len(expected_files)
            and manifest['sta_binary_sha256'] == STA_BINARY_SHA256 and manifest['appimage_sha256'] == physical.IMAGE_SHA,
            'postroute_sta_source', 'Require the exact complete frozen STA input set and runtime.')
    for item in manifest['files']:
        path = _safe(output, item['relative_path'])
        require(sha(path) == item['sha256'] and path.stat().st_size == item['bytes'],
                'postroute_sta_source', 'A frozen STA input changed.')
        if item['source_path']:
            source = Path(item['source_path'])
            require(sha(source) == item['sha256'] and source.stat().st_size == item['bytes'],
                    'postroute_sta_source', 'An original STA input changed during execution.')
    if annotation_policy == ANNOTATION_V2:
        require(object_hash(manifest.get('annotation_policy_qualification')) == object_hash(_annotation_qualification(manifest['files'], output)),
                'postroute_sta_annotation_model', 'Retain the exact all-PVT Liberty qualification for the selected annotation policy.')
    require((output / 'run_sta.py').read_bytes() == LAUNCHER
            and sha(output / 'inputs/physical.sdc') == physical.SDC_SHA
            and object_hash(load(output / 'layout-source.json')) == manifest['layout_record_sha256'],
            'postroute_sta_source', 'Require the fixed launcher, original SDC and matching source layout.')
    source_layout = load(output / 'layout-source.json')
    inventory = source_inventory(source_layout, source_layout['runtime_configuration'])
    top_module, clock_name, manifest_explicit = _record_identifiers(manifest)
    inventory_top, inventory_clock, inventory_explicit = _record_identifiers(inventory)
    layout_top, layout_clock = _layout_identifiers(source_layout)
    observed = [item for item in manifest['files'] if item['source_path'] is not None]
    require(observed == inventory['files'] and manifest.get('source_inventory_sha256') == object_hash(inventory)
            and all(manifest[key] == inventory[key] for key in ('layout_run_id', 'layout_record_sha256',
                    'physical_runtime_sha256', 'corners', 'clock_period_ns', 'constraints'))
            and manifest_explicit == inventory_explicit
            and (top_module, clock_name) == (inventory_top, inventory_clock)
            and (top_module, clock_name) == (layout_top, layout_clock)
            and manifest['appimage_executable'] == source_layout['runtime_configuration']['executable'],
            'postroute_sta_source', 'Frozen STA sources differ from the selected layout pointers, pinned PDK or original constraints.')
    for corner in CORNERS:
        rc, pvt = corner.split('_', 1)
        values = _environment((output / 'inputs' / (corner + '.env.tcl')).read_text(encoding='utf-8'))
        expected_script = _script(corner, values, {'netlist': output / 'inputs/netlist.v', 'sdc': output / 'inputs/physical.sdc',
                                                 'spef': output / 'inputs' / (rc + '.spef'), 'liberty': output / 'inputs' / (pvt + '.lib')},
                                  top_module, clock_name)
        require(values == manifest['constraints'] and (output / 'scripts' / (corner + '.tcl')).read_bytes() == expected_script,
                'postroute_sta_source', 'The actual STA script must reproduce the fixed analysis recipe.')
    netlist = (output / 'inputs/netlist.v').read_text(encoding='utf-8')
    corners = []
    for corner in CORNERS:
        result = executions[corner]
        require(result.get('executed') is True and result.get('status') == 'Completed'
                and type(result.get('exit_code')) is int and result['exit_code'] == 0
                and result.get('whole_process_group_terminated') is True and result.get('cleanup_unresolved') is False,
                'postroute_sta_execution', 'Require actual completed execution and verified process cleanup.')
        expected = ['python3', _wsl_path(output / 'run_sta.py'), corner, sha(output / 'sta-inputs.json')]
        require(result.get('argv') == [manifest['appimage_executable'], *expected], 'postroute_sta_execution', 'Actual command does not bind the frozen corner.')
        logs = output / ('sta-' + corner)
        request = load(logs / 'request.json')
        require(sha(logs / 'request.json') == result['request_sha256']
                and sha(logs / 'worker.py') == physical.WORKER_V2_SHA,
                'postroute_sta_execution', 'The frozen supervisor/request changed.')
        physical.validate_worker_binding(request, result, load(logs / 'process-start.json'), output, physical.WORKER_V2_SHA)
        raw_exit = load(logs / 'process-result.json')
        require(all(object_hash(value) == object_hash(result.get(key)) for key, value in raw_exit.items())
                and (logs / 'stdout.log').read_text(encoding='utf-8', errors='replace') == result['stdout']
                and (logs / 'stderr.log').read_text(encoding='utf-8', errors='replace') == result['stderr']
                and result['stdout'].strip() == 'HULLCIRQ_STA_LAUNCH_COMPLETE ' + corner + ' 0'
                and not result['stderr'].strip(),
                'postroute_sta_execution', 'Captured stdout/stderr/exit records disagree with the actual execution.')
        runtime = load(output / 'reports' / (corner + '.runtime.json'))
        require(runtime['version'].strip() == '2.7.0' and runtime['executable_sha256'] == STA_BINARY_SHA256,
                'postroute_sta_runtime', 'Require actual fixed OpenSTA version and executable hash.')
        raw = output / 'reports' / (corner + '.log')
        entry = parse_corner(raw.read_text(encoding='utf-8'), corner, netlist, manifest['clock_period_ns'],
                             annotation_policy=annotation_policy)
        entry.update(report_sha256=sha(raw), report_bytes=raw.stat().st_size, execution=result, runtime=runtime)
        corners.append(entry)
    statuses = {key: 'Passed' if all(c[key] == 'Passed' for c in corners) else 'Failed'
                for key in ('setup_hold_status', 'electrical_status', 'constraint_coverage_status', 'annotation_status', 'timing_model_coverage_status')}
    report = {'schema': SCHEMA, 'scope': manifest['scope'], 'validation_status': 'Passed' if all(c['validation_status'] == 'Passed' for c in corners) else 'Failed',
              **statuses,
              'executed': True, 'corners': corners, 'layout_run_id': manifest['layout_run_id'],
              'layout_record_sha256': manifest['layout_record_sha256'], 'manifest_sha256': sha(output / 'sta-inputs.json'),
              'source_inventory_sha256': manifest['source_inventory_sha256'],
              'clock_period_ns': manifest['clock_period_ns'], 'waivers': [],
              'summary': {'setup_ws_ns': min(c['metrics']['setup_ws_ns'] for c in corners),
                          'hold_ws_ns': min(c['metrics']['hold_ws_ns'] for c in corners),
                          **{key: max(c['metrics'][key] for c in corners)
                             for key in ('setup_violations', 'hold_violations', 'max_slew_violations', 'max_cap_violations', 'max_fanout_violations')}},
              'limits': ['Static timing and electrical checks; not dynamic SDF simulation.', 'Original physical assumptions and all nine corners retained.']}
    if manifest_explicit:
        report.update(top_module=top_module, clock_name=clock_name)
    if annotation_policy == ANNOTATION_V2:
        report.update(annotation_policy=annotation_policy,
                      annotation_policy_qualification=manifest['annotation_policy_qualification'])
    return report
