"""Reparse the 20 ns historical evidence; no simulator, EDA or third-party imports.

The integrity index is not a digital signature. Full GDS/SPEF/netlist archives
are identified but not bundled, so this is an included-record audit, not signoff.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
import re

FREEZE = '5239290e91f789d68fd8e4b282b54fdb086f6285'
CORNER = 'max_ss_100C_1v60'
CORNERS = {f'{rc}_{pvt}' for rc in ('min', 'nom', 'max')
           for pvt in ('ff_n40C_1v95', 'tt_025C_1v80', 'ss_100C_1v60')}
CHECKS = ('antenna__violating__nets', 'antenna__violating__pins',
          'route__antenna_violation__count', 'route__drc_errors',
          'magic__drc_error__count', 'klayout__drc_error__count',
          'design__lvs_error__count', 'design__lvs_device_difference__count',
          'design__lvs_net_difference__count', 'design__lvs_property_fail__count',
          'design__lvs_unmatched_device__count', 'design__lvs_unmatched_net__count',
          'design__lvs_unmatched_pin__count', 'design__disconnected_pin__count',
          'design__critical_disconnected_pin__count', 'design__instance_unmapped__count',
          'design__xor_difference__count', 'magic__illegal_overlap__count',
          'timing__hold_vio__count')


def canonical(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def finite(value):
    require(type(value) in (int, float) and math.isfinite(value), 'Nonfinite or invalid metric')
    return value


def derive(root=None):
    root = Path(root or Path(__file__).parent).resolve()

    def safe(name):
        path = (root / name).resolve()
        require(path.is_relative_to(root), 'Evidence path escapes supplement root: ' + name)
        return path

    def read(name):
        return json.loads(safe(name).read_text(encoding='utf-8'))

    provenance = read('provenance.json')
    require(provenance['physical_freeze_commit'] == FREEZE, 'Wrong physical freeze')
    files = {}
    for entry in provenance['files']:
        name = entry['path']
        require(name not in files, 'Duplicate source entry: ' + name)
        data = safe(name).read_bytes()
        expected = entry['source']
        require(len(data) == expected['bytes'] and hashlib.sha256(data).hexdigest() == expected['sha256'],
                'Changed or mismatched evidence: ' + name)
        files[name] = expected
    required = {'raw/final_002_freeze.json', 'raw/family_qualification.json',
                'raw/recipe.json', 'raw/protocol.md', 'raw/timing_methodology.md',
                'raw/dac27_post_drt.tcl', 'raw/dac27_openlane.py', 'raw/phase2_r2r_sta.tcl',
                'raw/layout_manifest.json', 'raw/render_layouts_original.py',
                'raw/tool_versions.json', 'raw/cfg_8x8_repair_summary.tsv'}
    for size in (2, 4):
        required.update(f'raw/cfg_{size}x{size}/{name}' for name in (
            'run_manifest.json', 'final_state.json', 'post_route_state.json',
            'r2r.stdout.log', 'config.json', 'mapped_report.json', 'repair_summary.tsv', 'manufacturability.rpt'))
        required.add(f'layouts/cfg_{size}x{size}.png')
    require(set(files) == required, 'Unexpected or missing source-index entries')
    actual = {p.relative_to(root).as_posix() for folder in ('raw', 'layouts')
              for p in (root / folder).rglob('*') if p.is_file()}
    require(actual == required, 'Unindexed or missing raw/layout file')

    def bind(bundle_path, original):
        require(all(files[bundle_path][k] == original[k] for k in ('path', 'bytes', 'sha256')),
                'Source/run binding differs: ' + bundle_path)

    freeze = read('raw/final_002_freeze.json')
    recipe = read('raw/recipe.json')
    qualification = read('raw/family_qualification.json')
    require(freeze['freeze_commit'] == qualification['freeze_commit'] == FREEZE, 'Freeze mismatch')
    require(freeze['family'] == qualification['family'] == 'FINAL_002', 'Mixed physical families')
    require(qualification['status'] == 'FAIL' and qualification['pass'] is False
            and qualification['accepted_physical_runs'] == [], 'Incomplete family was relabeled')
    require([row['array_size'] for row in qualification['configurations']] == [2, 4, 8], 'Family membership changed')
    excluded = qualification['configurations'][2]
    require(excluded['pass'] is False and excluded['status'] == 'FAIL'
            and excluded.get('timing') is None and excluded.get('area') is None, '8x8 must remain unqualified')
    bind('raw/recipe.json', freeze['recipe'])
    frozen = {x['path']: x for x in freeze['sources']}
    for name in ('recipe.json', 'protocol.md', 'timing_methodology.md',
                 'dac27_post_drt.tcl', 'dac27_openlane.py', 'phase2_r2r_sta.tcl'):
        entry = files['raw/' + name]
        bind('raw/' + name, frozen[entry['path']])
    require(recipe['array_sizes'] == [2, 4, 8] and recipe['flow'] == 'DAC27Classic', 'Wrong recipe')
    require(recipe['common_config']['CLOCK_PERIOD'] == recipe['timing']['constraint_period_ns'] == 20.0,
            'This supplement permits only 20 ns experiments')
    require(recipe['timing']['corner'] == CORNER and recipe['post_drt_repair']['max_passes'] == 2,
            'Timing or repair protocol changed')
    require(recipe['common_config']['DRT_THREADS'] == 2, 'DRT thread setting changed')
    layouts = read('raw/layout_manifest.json')
    require(layouts['original_three_configuration_family_status'] == 'FAIL'
            and layouts['new_physical_signoff'] is False, 'Layout scope changed')
    images = {x['array_size']: x for x in layouts['images']}
    require(set(images) == {2, 4}, 'Unexpected layout membership')
    rows = []
    for historical in qualification['configurations'][:2]:
        size = historical['array_size']
        tag = f'raw/cfg_{size}x{size}'
        run = f'results/raw/phase2/dac27/round2/physical/cfg_{size}x{size}/FINAL_002'
        design = f'phase2_core_{size}'
        manifest = read(tag + '/run_manifest.json')
        config = read(tag + '/config.json')
        require(manifest['array_size'] == size and manifest['design_name'] == design
                and manifest['freeze_commit'] == FREEZE and manifest['dac_family'] == 'FINAL_002',
                'Run identity mismatch')
        require(historical['pass'] is True and historical['qualification'] == 'QUALIFIED_FINAL'
                and historical['run_path'] == run and historical['freeze_commit'] == FREEZE,
                'Historical member lacks qualification')
        require(manifest['recipe_sha256'] == files['raw/recipe.json']['sha256'] == historical['recipe_sha256'],
                'Different backend recipes were mixed')
        require(config['DESIGN_NAME'] == design, 'Wrong design in config')
        require(all(config.get(k) == v for k, v in recipe['common_config'].items()), 'Common config differs')
        require(config['VERILOG_FILES'] == recipe['configurations'][str(size)]['verilog_files'], 'RTL config differs')
        for artifact, local in (('final_state', 'final_state.json'), ('post_route_state', 'post_route_state.json'),
                                ('r2r_report', 'r2r.stdout.log'), ('input_config', 'config.json'),
                                ('mapped_report', 'mapped_report.json')):
            bind(tag + '/' + local, manifest['artifacts'][artifact])
            require(manifest['artifacts'][artifact]['sha256'] == historical['artifacts'][artifact]['sha256'],
                    'Qualification and native manifest differ')
        final = read(tag + '/final_state.json')
        post = read(tag + '/post_route_state.json')
        for state in (final, post):
            for key in ('nl', 'sdc', 'odb'):
                require(state[key].startswith('/work/' + run + '/runs/FINAL_002/'), 'Mixed state paths')
            require(all(path.startswith('/work/' + run + '/runs/FINAL_002/55-openroad-rcx/')
                        for path in state['spef'].values()), 'Extraction is from a different run')
        for key, artifact in (('nl', 'netlist'), ('sdc', 'sdc')):
            require(final[key] == '/work/' + manifest['artifacts'][artifact]['path'], 'Final view mismatch')
        require(final['spef']['max_*'] == '/work/' + manifest['artifacts']['spef']['path'], 'Maximum SPEF mismatch')
        state = final['metrics']; hold = post['metrics']
        checks = {key: finite(state[key]) for key in CHECKS}
        require(all(value == 0 for value in checks.values()), 'Historical physical check is nonzero')
        report_summary = safe(tag + '/manufacturability.rpt').read_text(encoding='utf-8')
        require(all(re.search(r'\* ' + section + r'\s+Passed', report_summary)
                    for section in ('Antenna', 'LVS', 'DRC')), 'Native manufacturability summary failed')
        require(set(historical['signoff']) == set(CHECKS), 'Historical check scope differs')
        for key, value in checks.items():
            require(value == historical['signoff'][key]['value'], 'Native/parsed check mismatch')
        hold_corners = {key.split('__corner:', 1)[1]: {'worst_slack_ns': finite(value),
                         'violations': finite(hold['timing__hold_vio__count__corner:' + key.split('__corner:', 1)[1]])}
                        for key, value in hold.items() if key.startswith('timing__hold__ws__corner:')}
        require(set(hold_corners) == CORNERS, 'Missing or unexpected hold corner')
        require(all(x['worst_slack_ns'] >= 0 and x['violations'] == 0 for x in hold_corners.values()),
                'Historical all-corner hold check failed')
        worst_hold = min(x['worst_slack_ns'] for x in hold_corners.values())
        require(worst_hold == hold['timing__hold__ws'] == state['timing__hold__ws'], 'Hold aggregate differs')
        for key, evidence in historical['post_route_hold'].items():
            require(hold[key] == evidence['value'], 'Historical hold parser mismatch')
        report = safe(tag + '/r2r.stdout.log').read_text(encoding='utf-8')

        def token(name):
            matches = re.findall(r'^' + re.escape(name) + r' (.+)$', report, re.M)
            require(len(matches) == 1, 'Missing or duplicate R2R token: ' + name)
            return matches[0].strip()

        require(token('PHASE2_STA_DESIGN') == design and token('PHASE2_R2R_CORNER') == CORNER,
                'R2R report identity differs')
        for token_name, artifact in (('PHASE2_STA_ENV', 'sta_environment'), ('PHASE2_STA_NETLIST', 'netlist'),
                                     ('PHASE2_STA_SPEF', 'spef'), ('PHASE2_STA_SDC', 'sdc')):
            require(token(token_name) == '/work/' + manifest['artifacts'][artifact]['path'], 'R2R artifact mismatch')
        require(len(re.findall(r'^PHASE2_R2R_STA_PASS$', report, re.M)) == 1, 'R2R query did not pass')
        constraint = finite(float(token('PHASE2_R2R_CLOCK_PERIOD_NS')))
        slack = finite(float(token('PHASE2_R2R_SETUP_WS_NS')))
        path_count = int(token('PHASE2_R2R_PATH_COUNT'))
        require(constraint == config['CLOCK_PERIOD'] == 20.0 and path_count > 0, 'Wrong R2R constraint or empty paths')
        path_slacks = re.findall(r'^\s*([-+0-9.eE]+)\s+slack \((MET|VIOLATED)\)\s*$', report, re.M)
        require(len(path_slacks) == path_count, 'Detailed R2R path count differs from scalar report')
        parsed_slacks = [finite(float(value)) for value, _ in path_slacks]
        require(min(parsed_slacks) == slack, 'Detailed R2R worst slack differs from scalar report')
        require(all((value >= 0) == (label == 'MET')
                    for value, (_, label) in zip(parsed_slacks, path_slacks)), 'R2R slack label disagrees with value')
        period = constraint - slack
        require(period > 0 and historical['timing']['sta_period']['value'] == period
                and historical['timing']['setup_worst_slack']['value'] == slack, 'R2R arithmetic differs')
        receipt = provenance['historical_commands'][str(size)]['r2r']['record']
        require(receipt['returncode'] == 0 and receipt['capture_complete']
                and receipt['stdout_sha256'] == files[tag + '/r2r.stdout.log']['sha256'], 'R2R command failed or differs')
        repair = [line.split('\t') for line in safe(tag + '/repair_summary.tsv').read_text().splitlines()]
        require(repair[0][0] == 'baseline' and repair[-1][0] == 'final', 'Incomplete repair log')
        repair_counts = [int(repair[0][1])] + [int(x[2]) for x in repair if x[0] == 'pass']
        require(int(repair[-1][2]) == repair_counts[-1] == 0 and len(repair_counts) <= 3,
                'Repair exceeded bound or left antenna violations')
        require(all(int(x[3]) == 0 for x in repair if x[0] in ('pass', 'final')), 'Repair routing DRC failed')
        mapped = read(tag + '/mapped_report.json')
        require(mapped['pass'] is True and mapped['array_size'] == size and mapped['design_name'] == design,
                'Mapped compute retention failed')
        require(mapped['mapped_arithmetic_cone_count'] == size * size and mapped['accumulator_bits'] == 32 * size * size,
                'Mapped arithmetic retention incomplete')
        for key in ('design__core__area', 'design__instance__area'):
            require(finite(state[key]) > 0 and state[key] == historical['area'][key]['value'], 'Area parser mismatch')
        image = images[size]
        layout = f'layouts/cfg_{size}x{size}.png'
        bind(layout, image)
        require(image['source_gds']['sha256'] == manifest['artifacts']['gds']['sha256']
                and image['source_gds']['path'] == manifest['artifacts']['gds']['path'], 'Layout is from a different GDS')
        rows.append({'array_size': size, 'run_id': 'FINAL_002', 'freeze_commit': FREEZE,
                     'historical_qualification': 'QUALIFIED_FINAL', 'core_area_um2': state['design__core__area'],
                     'cell_area_um2': state['design__instance__area'], 'constraint_period_ns': constraint,
                     'r2r_corner': CORNER, 'r2r_setup_slack_ns': slack, 'r2r_path_count': path_count,
                     'sta_period_ns': period, 'sta_frequency_mhz': 1000.0 / period,
                     'physical_checks': checks, 'hold_corners': hold_corners, 'worst_hold_slack_ns': worst_hold,
                     'setup_all_worst_slack_ns': finite(state['timing__setup__ws']),
                     'setup_all_violations': finite(state['timing__setup_vio__count']),
                     'max_slew_violations': finite(state['design__max_slew_violation__count']),
                     'max_capacitance_violations': finite(state['design__max_cap_violation__count']),
                     'repair_antenna_counts': repair_counts, 'layout': layout})
    failed = [line.split('\t') for line in safe('raw/cfg_8x8_repair_summary.tsv').read_text().splitlines()]
    require(failed[-1][0] == 'final' and int(failed[-1][2]) > 0, 'Missing 8x8 failure evidence')
    return {'schema_version': 1, 'status': 'PASS', 'scope': 'Included-record audit and arithmetic replay; no new RTL or EDA',
            'family_status': 'FAIL', 'physical_freeze_commit': FREEZE, 'configurations': rows,
            'excluded_8x8': {'status': 'FAILED_ANTENNA', 'physical_metrics': None,
                            'remaining_antenna_nets': int(failed[-1][2]), 'downstream_qualification': 'NOT RUN'},
            'limitations': ['Two engineering-qualified members of an unsuccessful three-size family; no new preregistered two-size study.',
                            'Positive internal R2R timing is a fixed-layout STA estimate, not measured silicon Fmax or system latency.',
                            'Nonzero native slew/cap diagnostics remain; no claim of all electrical rules passing or tapeout readiness.',
                            'Large GDS, SPEF and netlist artifacts are indexed but omitted; portable audit cannot repeat physical signoff.',
                            'Original submission failures remain unchanged; recipe and DRT thread changes confound a single-cause repair claim.']}


def verify(root=None):
    root = Path(root or Path(__file__).parent).resolve()
    metrics = derive(root)
    require((root / 'metrics.json').read_bytes() == canonical(metrics), 'metrics.json is stale or changed; review before --write')
    return metrics


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--write', action='store_true', help='Recalculate only metrics.json from unchanged included evidence')
    mode.add_argument('--check', action='store_true', help='Require byte-identical regenerated metrics (default)')
    parser.add_argument('--root', type=Path, default=Path(__file__).parent)
    args = parser.parse_args()
    if args.write:
        metrics = derive(args.root)
        (args.root / 'metrics.json').write_bytes(canonical(metrics))
    else:
        metrics = verify(args.root)
    print(json.dumps(metrics, indent=2, sort_keys=True, allow_nan=False))


if __name__ == '__main__':
    main()
