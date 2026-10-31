#!/usr/bin/env python3
"""Collect bounded prototype evidence after native routing, including failed runs.

Never resumes/edits a native run or converts its failed signoff into PASS.
KLayout, antenna and rendering are independent of a Magic DRC failure.
Transistor extraction here is diagnostic: no full-chip RC PEX is inferred.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import run_flow2_mixed_wrapper_gds as native
from scripts import run_flow2_wrapper_transistor_lvs as transistor
from scripts import flow2_integration_common as common

TOP = native.d.TOP


def magic_rules(text):
    """Retain original rule names and all boxes; never divide into fake counts."""
    result, rule = {}, None
    for line in text.splitlines()[1:]:
        if line.startswith(('---', '[INFO]')) or not line.strip():
            continue
        coordinates = re.fullmatch(r'\s*(-?[\d.]+)um\s+(-?[\d.]+)um\s+(-?[\d.]+)um\s+(-?[\d.]+)um\s*', line)
        if coordinates is None:
            rule = line.strip()
            result.setdefault(rule, [])
        elif rule:
            result[rule].append([float(v) for v in coordinates.groups()])
    return {name: {'box_count': len(boxes), 'boxes_um': boxes} for name, boxes in result.items()}


def clock_model(text, clock):
    """Annotate the measured ETM's clock using the native CLOCK_PORT contract."""
    if re.search(r'(?i)\b(?:nan|infinity)\b', text):
        raise ValueError('nonfinite native ETM')
    if not re.search(r'\bcell\s*\(\s*"?' + re.escape(TOP) + r'"?\s*\)', text):
        raise ValueError('ETM top differs')
    pattern = r'(\bpin\s*\(\s*"?' + re.escape(clock) + r'"?\s*\)\s*\{)([^{}]*)'
    matches = list(re.finditer(pattern, text))
    if len(matches) != 1 or not re.search(r'\bdirection\s*:\s*input\s*;', matches[0][2]):
        raise ValueError('one input clock pin required')
    if re.search(r'\bclock\s*:', matches[0][2]):
        if not re.search(r'\bclock\s*:\s*true\s*;', matches[0][2]):
            raise ValueError('ETM explicitly denies clock pin')
        return text
    return text[:matches[0].end(1)] + '\n      clock : true;' + text[matches[0].end(1):]


def container_command(root, program, args, name):
    nb = native.notebook
    cmd = nb.docker_command(root, name, nb.DEFAULT_SOURCE, nb.DEFAULT_PDK, nb.DEFAULT_IMAGE)
    end = cmd.index(nb.DEFAULT_IMAGE)
    cmd = cmd[:end + 1]
    cmd[cmd.index('--entrypoint') + 1] = program
    cmd[2:2] = ['--name', name]
    return [*cmd, *map(str, args)]


def source_views(source, stage):
    if stage == 'final':
        final = source/'results/final'
        return {kind: final/kind/(TOP+'.'+kind)
                for kind in ('gds', 'lef', 'lib', 'spef')}, []
    if stage != 'streamout':
        raise ValueError('source stage must be final or streamout')
    # Read completed streamout and nominal STA products only. LEF may still
    # be open for writing, so it is deliberately deferred to the native end.
    nominal = source/'results/routing/mca/process_corner_nom'
    return {'gds': source/'results/signoff'/(TOP+'.magic.gds'),
            'lib': nominal/(TOP+'.lib'), 'spef': nominal/(TOP+'.spef')}, ['lef']


def run(root, *, gds_tag, tag, timeout_s=180, execute=False, transistor_checks=False,
        source_stage='final'):
    root = Path(root).resolve()
    common.tag_ok(gds_tag)
    common.tag_ok(tag)
    source = root / common.BUILD / gds_tag / 'design/runs' / gds_tag
    config = source.parent.parent / 'config.json'
    settings = json.loads(config.read_text())
    views, deferred = source_views(source, source_stage)
    view_items = {kind: common._item(root, path) for kind, path in views.items()}
    if any(not path.stat().st_size for path in views.values()):
        raise ValueError('completed nonempty streamout/STA products required')
    sources = [common._item(root, config), *view_items.values()]
    metrics = source/'reports/metrics.csv'
    if source_stage == 'final' or metrics.is_file():
        sources.append(common._item(root, metrics))
    report = {'format': 'automx-cim-wrapper-postroute-v1', 'tag': tag, 'gds_tag': gds_tag,
              'timestamp_utc': datetime.now(timezone.utc).isoformat(),
              'qualification': 'NOT_QUALIFIED', 'status': 'PREPARED', 'views': view_items,
              'source_stage': source_stage, 'deferred_native_views': deferred,
              'native_audit': native.audit(source), 'checks': {},
              'scope': 'Prototype continuation on exact native '+source_stage+' GDS. Native failures retained; '
                       'digital ETM, routed SPEF and macro PEX do not establish full transistor RC PEX.'}
    drc = source/'reports/signoff/drc.rpt'
    if drc.is_file():
        report['magic_drc'] = {'source': common._item(root, drc), 'rules': magic_rules(drc.read_text())}
    if not execute:
        return report
    deck = Path(re.search(r'^set ::env\(KLAYOUT_DRC_TECH_SCRIPT\) "([^"]+)"',
                         (source/'config.tcl').read_text(), re.M)[1])
    store = common.Store(root, tag, {'sources': sources, 'runner': common._sha(Path(__file__)),
                                    'source_stage': source_stage,
                                    'timeout_s': timeout_s, 'transistor_checks': transistor_checks,
                                    'native_config_sha256': common._sha(source/'config.tcl'),
                                    'native_pdk_sources': (source/'PDK_SOURCES').read_text(),
                                    'klayout_deck_sha256': common._sha(deck),
                                    'image': native.notebook.DEFAULT_IMAGE})
    snapshot = store.build/'executed_host_sources'
    snapshot.mkdir(exist_ok=True)
    shutil.copy2(Path(__file__), snapshot/Path(__file__).name)

    def step(name, command, env=None):
        def execute(work):
            try:
                return subprocess.run(command, cwd=work, env=env, text=True, capture_output=True, timeout=timeout_s)
            except subprocess.TimeoutExpired as error:
                if command[0] == 'docker':
                    subprocess.run(['docker', 'rm', '-f', command[command.index('--name')+1]],
                                   capture_output=True, timeout=15)
                output = error.stdout or b''
                if isinstance(output, bytes): output = output.decode(errors='replace')
                return subprocess.CompletedProcess(command, 124, output, '\nTIMEOUT: bounded prototype budget\n')
        result, work = store.step(name, command, executor=execute)
        item = {'returncode': result.returncode, 'status': 'TIMEOUT' if result.returncode == 124 else 'FAIL',
                'log': common._item(root, store.folder/(name+'.log'))}
        report['checks'][name] = item
        common.save_summary(store.folder/'summary.json', report)
        return result, work, item

    try:
        # Same pinned native runset; count report items, never infer clean from exit=0.
        xml = store.build/'klayout.xml'
        cmd = container_command(root, 'klayout', ['-b', '-r', deck, '-rd', 'input='+str(views['gds']),
                     '-rd', 'report='+str(xml), '-rd', 'feol=true', '-rd', 'beol=true', '-rd', 'offgrid=true'], 'automx-post-'+tag+'-drc')
        result, _, item = step('klayout', cmd)
        if result.returncode == 0 and xml.is_file():
            tree = ET.parse(xml).getroot()
            if tree.tag != 'report-database': raise ValueError('invalid KLayout report')
            from scripts.flow2_klayout_checks import summarize
            summarize(xml)  # empty disabled-rule reports cannot pass
            items = list(tree.iter('item'))
            item.update(rule_groups={'feol':True,'beol':True,'offgrid':True}, violations=len(items), categories=dict(Counter(x.findtext('category') for x in items)),
                        report=common._item(root, xml), status='PASS' if not items else 'FAIL')

        odb = source/'results/routing'/f'{TOP}.odb'
        antenna = store.build/'antenna.tcl'
        antenna.write_text(f'read_db {{{odb}}}\ncheck_antennas -verbose\nputs AUTOMX_ANTENNA_DONE\n')
        result, _, item = step('antenna', container_command(root, 'openroad', ['-exit', antenna],
                                                          'automx-post-'+tag+'-ant'))
        text = result.stdout + result.stderr
        nets = re.findall(r'\[INFO ANT-0002\] Found (\d+) net violations', text)
        pins = re.findall(r'\[INFO ANT-0001\] Found (\d+) pin violations', text)
        if result.returncode == 0 and nets and pins and 'AUTOMX_ANTENNA_DONE' in text:
            item.update(net_violations=int(nets[-1]), pin_violations=int(pins[-1]),
                        status='PASS' if int(nets[-1])+int(pins[-1]) == 0 else 'FAIL')

        lib = store.build/(TOP+'.clock_annotated.lib')
        try:
            lib.write_text(clock_model(views['lib'].read_text(), settings['CLOCK_PORT']))
        except ValueError as error:
            report['checks']['liberty']={'status':'FAIL', 'error':str(error)}
        verify = store.build/'verify_lib.tcl'
        verify.write_text(f'if {{[catch {{read_liberty {{{lib}}}}} e]}} {{puts stderr $e; exit 1}}\n'
                          f'if {{[llength [get_lib_cells */{TOP}]] != 1}} {{exit 2}}\n'
                          'puts AUTOMX_LIB_READ_PASS\nexit\n')
        if lib.is_file():
            result, _, item = step('liberty', container_command(root, 'sta', ['-exit', verify],
                                                              'automx-post-'+tag+'-lib'))
            item.update(derived_lib=common._item(root, lib), source_lib=common._item(root, views['lib']),
                        scope='Native measured digital ETM plus CLOCK_PORT annotation; no analog timing characterization')
            if result.returncode == 0 and 'AUTOMX_LIB_READ_PASS' in result.stdout and not re.search(r'(?m)^Error:', result.stdout+result.stderr):
                item['status'] = 'PASS_DIGITAL_ETM_PARSE'

        png = store.folder/'top.png'
        env = os.environ.copy()
        env.update(QT_QPA_PLATFORM='offscreen', AUTOMX_GDS=str(views['gds']), AUTOMX_PNG=str(png), AUTOMX_TOP=TOP)
        result, _, item = step('render', [shutil.which('klayout') or 'klayout', '-z', '-x', '-r',
                                        str(root/'scripts/render_flow2_wrapper_gds.py')], env)
        if result.returncode == 0 and png.is_file() and png.read_bytes()[:8] == b'\x89PNG\r\n\x1a\n':
            item.update(status='PASS', png=common._item(root, png), gds=common._item(root, views['gds']))

        if transistor_checks:
            previous = json.loads((root/common.BASE/'readout_progress_20261018_04/summary.json').read_text())
            cv = native.core_views(root, previous)
            cond = json.loads((root/common.BASE/'mixed_wrapper_20261020_01_cond/summary.json').read_text())
            schematic = common._verified(root, cond['views']['schematic'])
            # Use the original analog extraction PDK for the macro references.
            from scripts.run_flow2_acquisition_transient_recovery import DEFAULT_PDK
            pdk = Path(DEFAULT_PDK)
            text, proof = transistor.reference(root, pdk, source, cv['schematic'], schematic)
            ref = store.build/'transistor_reference.spice'
            ref.write_text(text)
            report['reference_proof'] = proof
            tcl = ('crashbackups stop\ndrc off\n' + f'gds read {{{views["gds"]}}}\nload {TOP}\n'
                   'select top cell\nextract do local\nextract all\next2spice lvs\next2spice merge none\n'
                   f'ext2spice scale off\next2spice subcircuit top on\next2spice -o {TOP}.spice\n'
                   'puts AUTOMX_TRANSISTOR_EXTRACT_DONE\nquit -noprompt\n')
            script = store.build/'transistor_extract.tcl'
            script.write_text(tcl)
            env = os.environ.copy()
            env.update(PDK_ROOT=str(pdk.parent), PDK='sky130A')
            command = [native.acq.stage5._find_tool('magic'), '-dnull', '-noconsole', '-rcfile',
                       str(pdk/'libs.tech/magic/sky130A.magicrc'), str(script)]
            result, ework, item = step('transistor_extract', command, env)
            extracted = ework/f'{TOP}.spice'
            if result.returncode == 0 and 'AUTOMX_TRANSISTOR_EXTRACT_DONE' in result.stdout and extracted.is_file():
                item.update(status='EXTRACTED_DIAGNOSTIC', netlist=common._item(root, extracted))
                nlog = store.build/'netgen.log'
                cmd = [native.acq.stage5._find_tool('netgen'), '-batch', 'lvs', f'{extracted} {TOP}',
                       f'{ref} {TOP}', str(pdk/'libs.tech/netgen/sky130A_setup.tcl'), str(nlog)]
                result, _, item = step('transistor_lvs', cmd)
                if result.returncode == 0 and nlog.is_file():
                    item['report'] = common._item(root, nlog)
                    try:
                        transistor.validate_netgen(nlog.read_text()+'\n'+result.stdout+result.stderr)
                        item['status'] = 'MATCH_DIAGNOSTIC_DRC_STILL_SEPARATE'
                    except ValueError as error: item['error'] = str(error)
        for source_item in sources:
            common._verified(root, source_item)
        report['status'] = 'PROTOTYPE_EVIDENCE_COLLECTED'
    except Exception as error:
        report.update(status='BLOCKED_POSTROUTE_EVIDENCE', error=f'{type(error).__name__}: {error}')
        raise
    finally:
        common.save_summary(store.folder/'summary.json', report)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--gds-tag', required=True)
    parser.add_argument('--tag', required=True)
    parser.add_argument('--timeout-s', type=int, default=180)
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--transistor', action='store_true')
    parser.add_argument('--source-stage', choices=('final', 'streamout'), default='final',
                        help='streamout reads completed GDS/nominal STA while native final checks continue')
    args = parser.parse_args()
    if not 1 <= args.timeout_s <= 600: parser.error('budget must be 1..600 seconds per tool')
    result = run(args.root, gds_tag=args.gds_tag, tag=args.tag, timeout_s=args.timeout_s,
                 execute=args.run, transistor_checks=args.transistor, source_stage=args.source_stage)
    print(json.dumps(result, indent=2))
