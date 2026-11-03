"""Explicit generic S08/S10 contract, independent of circuit family/names.

Uses the saved graph, public top interface and independent finite cycle vectors.
This module builds tests and checks evidence; it never supplies integration RTL.
"""
from __future__ import annotations

import copy
import re

from .domain import DomainError, VERILOG_IDENTIFIER, VERILOG_KEYWORDS
from .instance_arrays import array_shape, validate_design_arrays
from .verification import content_hash, object_hash

PROMPT = 'generic-public-contract-cycle-vectors-v6'
EXTERNAL_PROMPT = 'generic-explicit-external-io-cycle-vectors-v7'
EXTERNAL_PROMPT_V8 = 'generic-explicit-external-io-cycle-vectors-v8'
EXTERNAL_WIRING_VERSION = 'explicit-external-io-direct-wiring-v1'
KIND = 'generic_cycle_vectors'


def require(value, message):
    if not value:
        raise DomainError('generic_global_contract', message)


def handles(design):
    return type(design) is dict and type(design.get('global_verification')) is dict and design['global_verification'].get('kind') == KIND


def identifier(value):
    return type(value) is str and VERILOG_IDENTIFIER.fullmatch(value) is not None and value not in VERILOG_KEYWORDS


def required_node_ids(design):
    require(handles(design), 'Save an explicit generic cycle-vector system contract first.')
    validate_design_arrays(design)
    nodes = design.get('nodes')
    require(type(nodes) is list and 0 < len(nodes) <= 256
            and all(type(n.get('id')) is str and re.fullmatch(r'[A-Za-z0-9_-]{1,96}', n['id']) for n in nodes)
            and len({n['id'] for n in nodes}) == len(nodes),
            'Retain distinct saved source node IDs that are safe fixed artifact names.')
    require(all(identifier(n.get('module_name')) for n in nodes)
            and len({n['module_name'] for n in nodes}) == len(nodes), 'Every saved node definition needs a distinct plain Verilog module name.')
    return tuple(n['id'] for n in nodes)


def top_interface(design):
    required_node_ids(design)
    settings = design.get('settings') or {}; declaration = design.get('global_integration')
    require(type(declaration) is dict and type(declaration.get('public_ports')) is list
            and type(declaration.get('behavior')) is str and declaration['behavior'].strip(),
            'Declare the top public ports and complete integration behavior in the saved GUI design.')
    clock, reset, top = (settings.get(k) for k in ('clock_name', 'reset_name', 'top_module'))
    require(all(identifier(v) for v in (clock, reset, top)) and clock != reset
            and settings.get('rtl_language') == 'verilog_2005' and settings.get('reset_kind') == 'synchronous'
            and settings.get('reset_active') in ('high', 'low'),
            'Generic integration requires distinct plain clock/reset/top names, Verilog-2005 and one synchronous reset domain.')
    ports = [{'name': clock, 'direction': 'input', 'width': 1, 'signed': False},
             {'name': reset, 'direction': 'input', 'width': 1, 'signed': False}]
    for port in declaration['public_ports']:
        require(type(port) is dict and set(port) == {'name', 'direction', 'width', 'signed'}
                and identifier(port['name']) and port['direction'] in ('input', 'output')
                and type(port['width']) is int and 1 <= port['width'] <= 4096 and type(port['signed']) is bool,
                'Each top public port needs an exact name, direction, integer width and boolean signedness.')
        ports.append(copy.deepcopy(port))
    if 'external_io' in design:
        from .external_io import bindings, expanded_ports
        bindings(design)
        declared = {p['name']: p for p in ports[2:]}
        external = expanded_ports(design)
        require(len(declared) == len(ports) - 2 and declared == {p['name']: p for p in external},
                'Saved top public ports must exactly match the explicit external I/O blocks; update the declaration explicitly in the GUI.')
        ports = ports[:2] + copy.deepcopy(external)
    require(len({p['name'] for p in ports}) == len(ports) and any(p['direction'] == 'output' for p in ports)
            and top not in {n['module_name'] for n in design['nodes']},
            'Top public names must be unique (clock/reset are automatic), with an output and a distinct top module.')
    return {'module_name': top, 'ports': ports,
            'clock': {'port': clock, 'period_ns': settings.get('clock_period_ns')},
            'reset': {'port': reset, 'active': settings['reset_active'], 'kind': settings['reset_kind']}}


def external_instances(design):
    """Unambiguous ordinary names for direct instances, including arbitrary IDs.

    Hex encoding is reversible and collision-free; symbols are not DUT modules.
    """
    from .instance_arrays import instance_indices
    result = []
    for node in design['nodes']:
        base = 'u_' + node['id'].encode('utf-8').hex()
        for member in instance_indices(node):
            result.append({'node_id': node['id'], 'module_name': node['module_name'],
                           'instance_name': base + (f'_r{member[0]}_c{member[1]}' if member is not None else ''),
                           **({'instance_index': member} if member is not None else {})})
    return result


def check_external_wiring(rtl, manifest):
    """Conservative new-mode structural check, never a Verilog/formal proof.

    Only direct named instances, literal net declarations and identifier-to-
    identifier continuous aliases qualify. Unsupported syntax fails closed.
    """
    design = manifest['design']
    if 'external_io' not in design:
        return None
    from .external_io import bindings
    from .rtl_checks import _strip_comments, _parse_interface
    proof = {'version': EXTERNAL_WIRING_VERSION, 'validation_status': 'Failed',
             'scope': 'saved_external_pin_direct_named_wiring_and_aliases_not_formal_equivalence',
             'rtl_sha256': content_hash(rtl), 'diagnostics': []}
    try:
        saved = bindings(design); interface = top_interface(design)
        proof['bindings_sha256'] = object_hash(saved)
        expected_instances = external_instances(design)
        proof['instances'] = expected_instances
        source = _strip_comments(rtl)
        name, actual_ports, errors = _parse_interface(source)
        require(not errors and name == interface['module_name']
                and {p['name']: p for p in actual_ports} == {p['name']: p for p in interface['ports']},
                'Retain exactly the declared physical top interface.')
        body_match = re.fullmatch(r'\s*module\s+' + re.escape(name) + r'\s*\([^()]*\)\s*;([\s\S]*)\bendmodule\s*', source)
        require(body_match is not None and len(source) <= 512 * 1024,
                'External I/O wiring requires one fixed ordinary top module.')
        signals = {p['name']: (p['width'], p['signed']) for p in actual_ports}
        drivers = {p['name']: ('top', p['name']) for p in actual_ports if p['direction'] == 'input'}
        aliases, instances = {}, {}
        wanted = {i['instance_name']: i for i in expected_instances}
        modules = {n['node_id']: n for n in manifest['nodes']}
        input_uses = []
        def drive(signal, origin):
            require(signal in signals and signal not in drivers,
                    'Every used net must be declared and have one driver; multiple drivers are not accepted.')
            drivers[signal] = origin
        body = body_match[1]
        require(not body.strip() or body.rstrip().endswith(';'), 'Top statements must be explicit semicolon-terminated declarations, aliases or instances.')
        statements = body.split(';')
        # Declarations may follow instances in legal Verilog. Record them first.
        remaining = []
        declaration = re.compile(r'^(input|output|wire)\s+(?:wire\s+)?(?:(signed)\s+)?(?:\[\s*(\d+)\s*:\s*(\d+)\s*\]\s*)?(.+)$')
        for statement in statements:
            statement = statement.strip()
            if not statement: continue
            match = declaration.fullmatch(statement)
            if not match:
                remaining.append(statement); continue
            kind, signed, msb, lsb, names = match.groups()
            spec = (abs(int(msb) - int(lsb)) + 1 if msb is not None else 1, bool(signed))
            for signal in (part.strip() for part in names.split(',')):
                require(identifier(signal), 'Only plain literal-width net declarations qualify for external wiring.')
                if kind != 'wire':
                    require(any(p['name'] == signal and p['direction'] == kind for p in actual_ports), 'Body port declarations must match the top interface.')
                require(signal not in signals or signals[signal] == spec, 'A repeated net declaration changes its width or signedness.')
                signals[signal] = spec
        for statement in remaining:
            alias = re.fullmatch(r'assign\s+([A-Za-z_][A-Za-z0-9_$]*)\s*=\s*([A-Za-z_][A-Za-z0-9_$]*)', statement)
            if alias:
                target, source_signal = alias.groups()
                require(source_signal in signals and target in signals and signals[target] == signals[source_signal],
                        'Aliases must connect declared nets of identical width and signedness without conversion.')
                drive(target, ('alias', source_signal)); aliases[target] = source_signal
                continue
            instance = re.fullmatch(r'([A-Za-z_][A-Za-z0-9_$]*)\s+([A-Za-z_][A-Za-z0-9_$]*)\s*\(([\s\S]*)\)', statement)
            require(instance is not None, 'Only direct named instances and plain wire aliases qualify; behavioral logic, generate, expressions and parameter overrides are unsupported.')
            module, instance_name, arguments = instance.groups()
            require(instance_name in wanted and instance_name not in instances and module == wanted[instance_name]['module_name'],
                    'Instantiate each adopted node/member exactly once under its prescribed instance name.')
            entry = wanted[instance_name]; public = modules[entry['node_id']]['public_interface']['ports']
            pins = {}
            for argument in arguments.split(','):
                pin = re.fullmatch(r'\s*\.([A-Za-z_][A-Za-z0-9_$]*)\s*\(\s*([A-Za-z_][A-Za-z0-9_$]*)\s*\)\s*', argument)
                require(pin is not None and pin[1] not in pins, 'Every node pin must use one explicit named identifier connection.')
                pins[pin[1]] = pin[2]
            require(set(pins) == {p['name'] for p in public}, 'Connect every adopted physical node pin exactly once.')
            for port in public:
                signal = pins[port['name']]
                require(signal in signals and signals[signal] == (port['width'], port['signed']), 'Node pin net types must match the adopted public interface.')
                origin = ('node', instance_name, port['name'])
                if port['direction'] == 'output': drive(signal, origin)
                else: input_uses.append((entry, port['name'], signal))
            instances[instance_name] = pins
        require(set(instances) == set(wanted), 'All graph-declared node/member instances must be present.')
        def root(signal, seen=None):
            seen = set() if seen is None else seen
            require(signal not in seen and signal in drivers, 'A used net is undriven or an alias cycle exists.')
            seen.add(signal); origin = drivers[signal]
            return root(origin[1], seen) if origin[0] == 'alias' else origin
        for signal in aliases: root(signal)
        instance_by_endpoint = {(i['node_id'], tuple(i.get('instance_index', []))): i['instance_name'] for i in expected_instances}
        external_inputs = {}
        records = []
        for binding in saved:
            instance_name = instance_by_endpoint[(binding['node_id'], tuple(binding.get('instance_index', [])))]
            signal = instances[instance_name][binding['node_pin']]
            if binding['direction'] == 'input':
                require(root(signal) == ('top', binding['external_name']), 'A node input is not driven by its exact saved external input.')
                external_inputs[(instance_name, binding['node_pin'])] = binding['external_name']
            else:
                require(root(binding['external_name']) == ('node', instance_name, binding['node_pin']), 'An external output is not driven by its exact saved node output.')
            records.append({**copy.deepcopy(binding), 'instance_name': instance_name})
        controls = {design['settings'][key] for key in ('clock_name', 'reset_name')}
        for entry, pin, signal in input_uses:
            origin = root(signal)
            if pin in controls:
                require(origin == ('top', pin), 'Every node clock/reset must connect to the matching saved top control.')
            elif origin[0] == 'top':
                require(external_inputs.get((entry['instance_name'], pin)) == origin[1], 'No undeclared extra top-input fanout or bypass is accepted.')
        proof.update(validation_status='Passed', checked_signal_count=len(records), connections=records,
                     aliases=[{'target': k, 'source': aliases[k]} for k in sorted(aliases)])
    except (DomainError, KeyError, TypeError, ValueError, AttributeError) as error:
        proof['diagnostics'] = [{'code': 'external_io_wiring', 'severity': 'error', 'message': str(error)}]
    return proof


def external_wiring_proof_matches(job, manifest):
    if 'external_io' not in manifest['design']:
        return True
    expected = check_external_wiring(job['rtl'], manifest)
    return (job.get('context', {}).get('template_version') in (EXTERNAL_PROMPT, EXTERNAL_PROMPT_V8)
            and expected['validation_status'] == 'Passed'
            and object_hash(job.get('checks', {}).get('external_io_wiring_proof')) == object_hash(expected)
            and job.get('checks', {}).get('checks', {}).get('external_io_wiring', {}).get('validation_status') == 'Passed')


def build_plan(design):
    from .generic_verification import build_cycle_plan
    interface = top_interface(design)
    return build_cycle_plan(interface, design['global_verification'],
        reserved_module_names=[interface['module_name'], *(node['module_name'] for node in design['nodes'])])


def instance_counts(manifest):
    required_node_ids(manifest['design'])
    result = {}
    for node in manifest['design']['nodes']:
        shape = array_shape(node)
        result[node['id']] = shape[0] * shape[1] if shape else 1
    return result


def testbench_module(plan):
    name = plan.get('testbench_module')
    require(identifier(name), 'Retain the exact simple testbench module declared by the generic cycle plan.')
    return name


def hierarchy(scope_lines, manifest, *, netlist=False):
    plan = build_plan(manifest['design']); root = testbench_module(plan); dut = plan.get('dut_instance', 'dut')
    require(identifier(dut), 'Retain the declared testbench DUT instance.')
    scopes = {}
    for line in scope_lines:
        match = re.fullmatch(r'(S_[A-Za-z0-9_]+)\s+\.scope (\w+),\s*"([^"]+)"(?:\s+"([^"]+)")?(.*);', line)
        require(match is not None and match[1] not in scopes, 'Compiler scope records must be complete and unique.')
        key, kind, name, module, rest = match.groups(); parents = re.findall(r'\bS_[A-Za-z0-9_]+\b', rest)
        scopes[key] = (kind, name, module, parents[-1] if parents else None)
    def components(key, seen=None):
        seen = set() if seen is None else seen
        require(key in scopes and key not in seen, 'Compiler scope ancestry is incomplete or cyclic.')
        seen.add(key); kind, name, _, parent = scopes[key]
        require(re.fullmatch(r'[A-Za-z_][A-Za-z0-9_$]*(?:\[\d+\])?(?:\.[A-Za-z_][A-Za-z0-9_$]*(?:\[\d+\])?)*', name),
                'Compiler scope names require safe ordinary components or constant array indices.')
        selector = '\\' + name + ' ' if netlist and ('.' in name or (kind == 'module' and '[' in name)) else name
        return (components(parent, seen) if parent else []) + [(name, selector)]
    result = {}; counts = instance_counts(manifest)
    for entry in manifest['nodes']:
        locations = []
        for key, (kind, _, module, _) in scopes.items():
            if kind == 'module' and module == entry['module_name']:
                parts = components(key)
                require(len(parts) >= 3 and [p[0] for p in parts[:2]] == [root, dut],
                        'Every adopted module instance must remain under the exact compiled testbench DUT.')
                locations.append('.'.join(p[1] for p in parts[1:]))
        require(len(locations) == counts[entry['node_id']] and len(set(locations)) == len(locations),
                'Actual compiler elaboration must contain every graph-declared source instance exactly once.')
        result[entry['node_id']] = sorted(locations)
    return result


def instrument(plan, locations):
    from .generic_verification import validate_cycle_plan
    validate_cycle_plan(plan)
    # External assertions are already complete in this frozen testbench. Do
    # not invent internal-node reference traces or NPU participation monitors.
    monitor = '// generic-cycle-vectors-v1: exact external DUT-port assertions; no internal behavioral coverage claim\n'
    return plan['testbench'], monitor


def runtime_records(stdout, plan, stderr=''):
    from .generic_verification import parse_cycle_runtime
    report = parse_cycle_runtime(stdout, plan, stderr)
    return report.get('validation_status') == 'Passed', report.get('records', []), [], []


def passed_s08(job):
    """Reconstruct all trusted source/command/elaboration/finite-test evidence."""
    from . import global_generation as global_tools
    try:
        proof = job['checks']; context = job['context']; plan = context['verification_plan']; manifest = context['source_manifest']
        require(external_wiring_proof_matches(job, manifest), 'Retain the exact new-version source-bound external wiring proof.')
        global_tools.validate_global_plan(manifest['design'], plan)
        commands = proof['commands']
        expected_commands = global_tools.fixed_global_commands(context['tool_configuration'], manifest, proof['artifacts_directory'])
        require(type(commands) is list and len(commands) == 4 and all(type(c) is dict and c.get('executed') is True
                and c.get('status') == 'Completed' and type(c.get('exit_code')) is int and c['exit_code'] == 0 for c in commands),
                'Four exact successful fixed commands are required.')
        passed, records, streams, pes = runtime_records(commands[-1]['stdout'], plan, commands[-1].get('stderr', ''))
        locations = hierarchy(proof['hierarchy_scope_lines'], manifest); tb, monitor = instrument(plan, locations)
        interface = global_tools.top_interface(manifest['design'])
        interface_check = global_tools.check_rtl(job['rtl'], interface, interface['module_name'], None)
        return (passed and proof.get('validation_status') == 'Passed' and proof.get('executed') is True
            and interface_check['checks']['interface']['validation_status'] == 'Passed'
            and proof.get('stdout') == ''.join(c.get('stdout', '') for c in commands[1:])
            and proof.get('stderr') == ''.join(c.get('stderr', '') for c in commands[1:])
            and proof.get('verification_profile') == KIND and proof.get('signal_sample_count') == len(records)
            and proof.get('expected_signal_samples') == sum(len(row['expect']) for row in plan['contract']['cycles'])
            and type(proof.get('exit_code')) is int and proof['exit_code'] == 0
            and object_hash([c['command'] for c in commands]) == object_hash(expected_commands)
            and object_hash(proof.get('tool_configuration')) == object_hash(context['tool_configuration'])
            and proof.get('rtl_sha256') == content_hash(job['rtl']) and proof.get('source_manifest_sha256') == object_hash(manifest)
            and proof.get('vector_hash') == plan['vector_hash'] and proof.get('testbench_sha256') == plan['testbench_sha256']
            and proof.get('public_boundary_vector_hash') == plan['public_boundary_vector_hash']
            and object_hash(proof.get('public_port_hierarchy')) == object_hash(locations)
            and proof.get('hierarchy_scope_sha256') == object_hash(proof['hierarchy_scope_lines'])
            and proof.get('public_monitor_source') == monitor and proof.get('public_monitor_sha256') == content_hash(monitor)
            and proof.get('instrumented_testbench_sha256') == content_hash(tb)
            and object_hash(proof.get('elaborated_instance_counts')) == object_hash(instance_counts(manifest))
            and object_hash(proof.get('actual_output_transfers')) == object_hash(records)
            and proof.get('actual_public_stream_transfers') == streams and proof.get('actual_pe_lane_transfers') == pes
            and all(proof.get('checks', {}).get(key, {}).get('validation_status') == 'Passed'
                    for key in ('interface', 'elaboration', 'functional', 'public_boundary')))
    except (DomainError, KeyError, ValueError, TypeError, AttributeError):
        return False
