#!/usr/bin/env python3
"""Parse explicitly selected Phase 0 evidence, never manually entered metrics."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
RAW_PREFIX = Path('results/raw/phase0')


class EvidenceError(ValueError):
    """Selected evidence is missing, inconsistent, or insufficient."""


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b''):
            digest.update(chunk)
    return digest.hexdigest()


class Evidence:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.sources = {}
        self.commands = []

    def path(self, relative):
        if not isinstance(relative, str) or not relative:
            raise EvidenceError('Evidence path must be a nonempty string')
        candidate = Path(relative.replace('\\', '/'))
        if candidate.is_absolute() or re.match(r'^[A-Za-z]:', relative):
            raise EvidenceError(f'Evidence paths must be repository-relative: {relative}')
        path = (self.root / candidate).resolve()
        if not path.is_relative_to((self.root / RAW_PREFIX).resolve()):
            raise EvidenceError(f'Evidence path is outside {RAW_PREFIX.as_posix()}: {relative}')
        return path

    def relative(self, path):
        return Path(path).resolve().relative_to(self.root).as_posix()

    def source(self, path, nonempty=True):
        path = Path(path)
        if not path.is_file() or (nonempty and path.stat().st_size == 0):
            raise EvidenceError(f'Missing or empty evidence: {self.relative(path)}')
        item = {'path': self.relative(path), 'sha256': sha256(path),
                'size_bytes': path.stat().st_size}
        self.sources[item['path']] = item
        return item

    def json(self, path):
        self.source(path)
        try:
            return json.loads(Path(path).read_text(encoding='utf-8-sig'))
        except (ValueError, UnicodeError) as exc:
            raise EvidenceError(f'Invalid JSON: {self.relative(path)}: {exc}') from exc

    def command(self, relative):
        record_path = self.path(relative)
        record = self.json(record_path)
        if not isinstance(record, dict):
            raise EvidenceError(f'Command record must be an object: {relative}')
        argv = record.get('argv')
        if not isinstance(argv, list) or not argv or not all(isinstance(a, str) for a in argv):
            raise EvidenceError(f'Command argv is missing or malformed: {relative}')
        if type(record.get('returncode')) is not int or record['returncode'] != 0:
            raise EvidenceError(f'Command did not succeed: {relative}; returncode={record.get("returncode")}')
        log_path = self.path(record.get('log'))
        log_source = self.source(log_path, nonempty=False)
        if record.get('log_sha256') != log_source['sha256']:
            raise EvidenceError(f'Command log checksum mismatch: {self.relative(log_path)}')
        captured = {
            'record': self.relative(record_path), 'argv': argv,
            'returncode': record['returncode'], 'log': log_source,
            'started_at': record.get('started_at'), 'finished_at': record.get('finished_at'),
        }
        self.commands.append(captured)
        return log_path.read_text(encoding='utf-8', errors='replace'), captured


def numeric(value, source):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise EvidenceError(f'Non-finite or nonnumeric metric: {source}')
    return value


def parse_simulation(evidence, selection):
    _, compile_record = evidence.command(selection['compile_command'])
    text, run_record = evidence.command(selection['run_command'])
    if not re.search(r'^PHASE0_SIM_PASS\s*$', text, re.MULTILINE) or 'PHASE0_SIM_FAIL' in text:
        raise EvidenceError('Simulation lacks an unambiguous PHASE0_SIM_PASS result')
    return {'pass': True, 'compile': compile_record, 'execution': run_record}


def parse_synthesis(evidence, selection):
    text, command = evidence.command(selection['command'])
    if 'End of script' not in text or re.search(r'^\s*ERROR:', text, re.MULTILINE):
        raise EvidenceError('Yosys log lacks successful completion')
    netlist = evidence.path(selection['netlist'])
    netlist_source = evidence.source(netlist)
    if not re.search(r'\bmodule\s+\\?phase0_counter\b', netlist.read_text(errors='replace')):
        raise EvidenceError('Selected synthesis netlist does not contain phase0_counter')
    return {'pass': True, 'execution': command, 'netlist': netlist_source}


def selected_run_path(evidence, path, run_dir):
    candidate = evidence.path(path)
    if not candidate.is_relative_to(run_dir):
        raise EvidenceError(f'Artifact is outside selected physical run: {path}')
    return candidate


def resolve_view(evidence, value, run_dir):
    """Map OpenLane's absolute container paths to the selected local run only."""
    if not isinstance(value, str):
        raise EvidenceError('Final state GDS path must be a string')
    normalized = value.replace('\\', '/')
    marker = evidence.relative(run_dir) + '/'
    if marker in normalized:
        normalized = marker + normalized.split(marker, 1)[1]
    return selected_run_path(evidence, normalized, run_dir)


def quantity(value, units, source, key, corner=None):
    result = {'value': numeric(value, key), 'units': units,
              'source': source, 'source_key': key}
    if corner is not None:
        result['corner'] = corner
    return result


def parse_supplemental_r2r(evidence, relative, run_dir, sta_dir, physical_command, corners):
    text, command = evidence.command(relative)
    if not re.search(r'^PHASE0_R2R_STA_PASS\s*$', text, re.MULTILINE) or 'PHASE0_R2R_STA_FAIL' in text:
        raise EvidenceError('Supplemental R2R STA lacks an unambiguous PASS marker')
    corner_matches = re.findall(r'^PHASE0_SUPPLEMENTAL_CORNER\s+(\S+)\s*$', text, re.MULTILINE)
    values = re.findall(r'^PHASE0_R2R_SETUP_WS_NS\s+(\S+)\s*$', text, re.MULTILINE)
    if len(corner_matches) != 1 or len(values) != 1:
        raise EvidenceError('Supplemental R2R STA requires exactly one corner and slack marker')
    corner = corner_matches[0]
    if corner not in corners:
        raise EvidenceError('Supplemental R2R corner is not in the selected post-route evidence')
    try:
        value = numeric(float(values[0]), 'PHASE0_R2R_SETUP_WS_NS')
    except ValueError as exc:
        raise EvidenceError('Supplemental R2R setup slack is not finite numeric output') from exc
    environment_args = [arg.split('=', 1)[1] for arg in command['argv'] if arg.startswith('PHASE0_STA_ENV=')]
    if len(environment_args) != 1:
        raise EvidenceError('Supplemental R2R command lacks its selected saved STA environment')
    env_path = resolve_view(evidence, environment_args[0], run_dir)
    if env_path.parent != sta_dir / corner:
        raise EvidenceError('Supplemental R2R environment belongs to another stage or corner')
    image_args = {arg for arg in physical_command['argv'] if '@sha256:' in arg}
    if not image_args.intersection(command['argv']):
        raise EvidenceError('Supplemental R2R STA did not use the physical-flow image digest')
    return {
        'execution': command, 'saved_environment': evidence.source(env_path),
        'setup_worst_slack': quantity(value, 'ns', command['log']['path'], 'PHASE0_R2R_SETUP_WS_NS', corner),
        'semantics': 'Supplemental OpenSTA max-delay query from register clock pins to register data pins '
                     'using the saved post-route corner environment, libraries, netlist, SDC and SPEF; '
                     'kept separate from native OpenLane metrics. No frequency is derived.',
    }


def parse_physical(evidence, selection):
    text, command = evidence.command(selection['command'])
    plain = re.sub(r'\x1b\[[0-9;]*m', '', text)
    if not re.search(r'Flow (?:complete|completed)\b', plain, re.IGNORECASE):
        raise EvidenceError('OpenLane command lacks a completed-flow marker')
    run_dir = evidence.path(selection['run_dir'])
    if not run_dir.is_dir():
        raise EvidenceError('Selected physical run directory is missing')
    arguments = command['argv']
    tag_index = arguments.index('--run-tag') + 1 if '--run-tag' in arguments else len(arguments)
    if tag_index >= len(arguments) or arguments[tag_index] != run_dir.name:
        raise EvidenceError('Physical command does not identify the selected OpenLane run tag')
    final_path = selected_run_path(evidence, selection['final_state'], run_dir)
    final_state = evidence.json(final_path)
    config_path = selected_run_path(evidence, selection['resolved_config'], run_dir)
    config = evidence.json(config_path)
    if config.get('DESIGN_NAME') != 'phase0_counter':
        raise EvidenceError('Resolved physical configuration is not phase0_counter')
    if not all(isinstance(config.get(key), str) and config[key] for key in ('PDK', 'STD_CELL_LIBRARY')):
        raise EvidenceError('Resolved configuration lacks PDK/library identity')
    sta_dir = selected_run_path(evidence, selection['post_route_sta_dir'], run_dir)
    if not re.fullmatch(r'\d+-openroad-stapostpnr', sta_dir.name, re.IGNORECASE):
        raise EvidenceError('Timing evidence is not the OpenROAD.STAPostPNR stage')
    sta_state_path = sta_dir / 'state_out.json'
    sta_state = evidence.json(sta_state_path)
    metrics = sta_state.get('metrics')
    if not isinstance(metrics, dict):
        raise EvidenceError('Post-route STA state lacks metrics')
    timing = []
    unavailable = []
    for key, value in sorted(metrics.items()):
        match = re.fullmatch(r'timing__(setup|hold)__(ws|tns)(?:__corner:(.+))?', key)
        if match:
            timing.append(quantity(value, 'ns', evidence.relative(sta_state_path), key,
                                   match.group(3) or 'aggregate'))
        elif key.startswith('timing__') and isinstance(value, float) and not math.isfinite(value):
            unavailable.append({'value': None, 'status': 'UNAVAILABLE',
                                'raw_representation': str(value),
                                'reason': 'Non-finite tool output; no finite timing quantity can be reported',
                                'source': evidence.relative(sta_state_path), 'source_key': key})
    if not any(item['source_key'].startswith('timing__setup__ws') for item in timing):
        raise EvidenceError('Post-route STA lacks finite setup slack metrics')
    reports = []
    report_names = {'summary.rpt', 'max.rpt', 'min.rpt', 'ws.max.rpt', 'ws.min.rpt',
                    'tns.max.rpt', 'tns.min.rpt', 'clock.rpt', 'checks.rpt'}
    for path in sorted(sta_dir.rglob('*.rpt')):
        if path.name in report_names and path.is_file() and path.stat().st_size:
            reports.append(evidence.source(path))
    if not reports:
        raise EvidenceError('Post-route STA reports are missing')
    for item in timing:
        if item['source_key'].startswith('timing__setup__ws__corner:'):
            report_path = sta_dir / item['corner'] / 'ws.max.rpt'
            report = evidence.source(report_path)
            match = re.search(r'^' + re.escape(item['corner']) + r':\s*([-+\d.eE]+)\s*$',
                              report_path.read_text(errors='replace'), re.MULTILINE)
            if not match or not math.isclose(float(match.group(1)), item['value'], abs_tol=1e-10):
                raise EvidenceError('Post-route setup report disagrees with metrics: ' + item['corner'])
            item['report_source'] = report
    time_units = []
    for corner, view in sorted(sta_state.get('lib', {}).items()):
        lib_path = resolve_view(evidence, view, run_dir)
        lib_source = evidence.source(lib_path)
        if not re.search(r'time_unit\s*:\s*"1ns"\s*;', lib_path.read_text(errors='replace')):
            raise EvidenceError('Post-route extracted Liberty does not establish 1ns time units')
        time_units.append({'corner': corner, 'units': 'ns', 'source': lib_source, 'source_key': 'time_unit'})
    if not time_units:
        raise EvidenceError('Post-route extracted Liberty unit evidence is missing')
    area = []
    final_metrics = final_state.get('metrics', {})
    for key in ('design__instance__area', 'design__core__area', 'design__die__area'):
        if key in final_metrics:
            area.append(quantity(final_metrics[key], 'um^2', evidence.relative(final_path), key))
    gds_path = resolve_view(evidence, final_state.get('gds'), run_dir)
    if gds_path.suffix.lower() != '.gds':
        raise EvidenceError('Final state does not reference a GDS file')
    gds_view = evidence.source(gds_path)
    final_gds = evidence.source(run_dir / 'final/gds' / gds_path.name)
    if final_gds['sha256'] != gds_view['sha256']:
        raise EvidenceError('Exported final GDS differs from the completed final-state view')
    result = {
        'pass': True, 'run_id': run_dir.name, 'execution': command,
        'final_state': evidence.source(final_path), 'resolved_config': evidence.source(config_path),
        'pdk': config['PDK'], 'standard_cell_library': config['STD_CELL_LIBRARY'],
        'clock_period': quantity(config.get('CLOCK_PERIOD'), 'ns', evidence.relative(config_path), 'CLOCK_PERIOD'),
        'post_route_timing': {'stage': 'OpenROAD.STAPostPNR', 'quantities': timing, 'reports': reports,
                              'unit_evidence': time_units, 'unavailable': unavailable},
        'area': area, 'gds': final_gds, 'gds_source_view': gds_view,
    }
    if selection.get('supplemental_r2r_command'):
        result['supplemental_r2r_timing'] = parse_supplemental_r2r(
            evidence, selection['supplemental_r2r_command'], run_dir, sta_dir, command,
            {item['corner'] for item in timing if item.get('corner') != 'aggregate'},
        )
    return result


def command_json(evidence, relative):
    text, command = evidence.command(relative)
    try:
        return json.loads(text), command
    except ValueError as exc:
        raise EvidenceError(f'Command output is not JSON: {relative}') from exc


def parse_environment(evidence, selection):
    hosts = []
    tools = {}
    for relative in selection.get('doctors', []):
        doctor, command = command_json(evidence, relative)
        if not isinstance(doctor, dict) or not isinstance(doctor.get('tools'), dict):
            raise EvidenceError('Doctor output lacks machine-readable tools')
        hosts.append({'host': doctor.get('host', {}), 'tools': doctor['tools'], 'source': command['log']})
        for name, tool in doctor['tools'].items():
            if tool.get('available') and tool.get('returncode') == 0 and tool.get('output'):
                tools[name] = {'output': tool['output'], 'command': tool['command'],
                               'source': command['log'], 'source_key': 'tools.' + name}
    for name, relative in selection.get('version_commands', {}).items():
        output, command = evidence.command(relative)
        if not output.strip():
            raise EvidenceError(f'Empty version output for {name}')
        tools[name] = {'output': output.strip(), 'command': command['argv'], 'source': command['log']}
    if not hosts:
        raise EvidenceError('No successful doctor report was selected')
    for name in ('openlane', 'openroad', 'yosys'):
        if name not in tools:
            raise EvidenceError(f'Missing successful tool version evidence: {name}')
    if not {'iverilog', 'verilator'}.intersection(tools):
        raise EvidenceError('Missing simulator version evidence')
    if 'simulation_verilator' not in tools:
        raise EvidenceError('Missing explicit version evidence for the host simulation Verilator')
    pdk_output, pdk_command = evidence.command(selection['pdk_command'])
    revision_match = re.fullmatch(r'(?:open_pdks\s+)?([0-9a-fA-F]{40})', pdk_output.strip())
    if not revision_match:
        raise EvidenceError('PDK output lacks an unambiguous actual open_pdks revision')
    pdk = {'revision': revision_match.group(1), 'output': pdk_output.strip()}
    pdk_support = {}
    for name, relative in selection.get('pdk_support_commands', {}).items():
        output, command = evidence.command(relative)
        pdk_support[name] = {'output': output.strip(), 'source': command['log']}
    images, image_command = command_json(evidence, selection['image_command'])
    if not isinstance(images, list) or len(images) != 1 or not isinstance(images[0], dict):
        raise EvidenceError('Docker inspection must identify exactly one selected image')
    image = images[0]
    digests = image.get('RepoDigests')
    if not isinstance(digests, list) or not digests or not all(
            isinstance(value, str) and re.fullmatch(r'.+@sha256:[0-9a-f]{64}', value) for value in digests):
        raise EvidenceError('Docker image lacks immutable repository digest')
    return {'pass': True, 'environments': hosts, 'tools': tools,
            'pdk': {'observed': pdk, 'source': pdk_command['log'], 'supporting_evidence': pdk_support},
            'container_image': {'id': image.get('Id'), 'repository_digests': digests,
                                'source': image_command['log']}}


def collect(selection_path, root=ROOT):
    evidence = Evidence(root)
    selection_path = Path(selection_path).resolve()
    if not selection_path.is_relative_to((evidence.root / RAW_PREFIX).resolve()):
        raise EvidenceError('Selection must live under results/raw/phase0')
    selection = evidence.json(selection_path)
    if not isinstance(selection, dict) or selection.get('schema_version') != 1:
        raise EvidenceError('Unsupported selection schema')
    data = {'schema_version': 2, 'run_id': selection.get('run_id'),
            'design': 'phase0_counter', 'selection': evidence.source(selection_path),
            'parser': {'path': 'scripts/collect_phase0_metrics.py', 'sha256': sha256(Path(__file__))},
            'errors': []}
    for name, parser in (('simulation', parse_simulation), ('synthesis', parse_synthesis),
                         ('physical_flow', parse_physical), ('environment', parse_environment)):
        try:
            data[name] = parser(evidence, selection[name])
        except (EvidenceError, KeyError, TypeError, AttributeError, OSError) as exc:
            data[name] = {'pass': False, 'error': str(exc)}
            data['errors'].append({'stage': name, 'message': str(exc),
                                   'failure_classification': 'UNKNOWN_FAILURE'})
    if data['simulation']['pass'] and data['environment']['pass']:
        data['simulation']['tool_version'] = data['environment']['tools']['simulation_verilator']
    if data['environment']['pass']:
        digests = data['environment']['container_image']['repository_digests']
        for stage in ('synthesis', 'physical_flow'):
            if data[stage]['pass']:
                used = [digest for digest in digests if digest in data[stage]['execution']['argv']]
                if not used:
                    message = 'Selected image digest is not present in the captured stage command'
                    data[stage]['pass'] = False
                    data[stage]['error'] = message
                    data['errors'].append({'stage': stage, 'message': message,
                                           'failure_classification': 'UNKNOWN_FAILURE'})
                else:
                    data[stage]['container_image_digest'] = used[0]
    data['pass'] = all(data[name]['pass'] for name in ('simulation', 'synthesis', 'physical_flow', 'environment'))
    data['raw_sources'] = sorted(evidence.sources.values(), key=lambda item: item['path'])
    times = [command['finished_at'] for command in evidence.commands if command['finished_at']]
    data['evidence_recorded_through'] = max(times) if times else None
    lock = {'schema_version': 2, 'status': 'VERIFIED' if data['environment']['pass'] else 'INCOMPLETE',
            'recorded_at': data['evidence_recorded_through'], 'selection': data['selection'],
            'parser': data['parser'], 'environment': data['environment']}
    if data['physical_flow']['pass']:
        physical = data['physical_flow']
        lock['pdk'] = {'name': physical['pdk'], 'source': physical['resolved_config'], 'source_key': 'PDK'}
        lock['standard_cell_library'] = {'name': physical['standard_cell_library'],
                                         'source': physical['resolved_config'], 'source_key': 'STD_CELL_LIBRARY'}
    return data, lock


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--selection', type=Path, default=ROOT / RAW_PREFIX / 'selection.json')
    parser.add_argument('--output', type=Path, default=ROOT / 'results/processed/phase0_metrics.json')
    parser.add_argument('--lock-output', type=Path, default=ROOT / 'environment/toolchain.lock.json')
    args = parser.parse_args(argv)
    try:
        data, lock = collect(args.selection)
    except (EvidenceError, OSError) as exc:
        print(f'PHASE0_EVIDENCE_FAIL: {exc}', file=sys.stderr)
        return 2
    for path, value in ((args.output, data), (args.lock_output, lock)):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n', encoding='utf-8', newline='\n')
    print('PHASE0_EVIDENCE_PASS' if data['pass'] else 'PHASE0_EVIDENCE_FAIL')
    return 0 if data['pass'] else 1


if __name__ == '__main__':
    sys.exit(main())
