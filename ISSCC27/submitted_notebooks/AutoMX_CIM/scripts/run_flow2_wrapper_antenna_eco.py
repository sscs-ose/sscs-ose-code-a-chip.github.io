#!/usr/bin/env python3
"""Bounded targeted diode/route experiment from the ground-closed wrapper ODB.

Never overwrites published GDS or upgrades wrapper signoff. Even antenna=0
requires routed connectivity, DRC, LVS and fresh STA before acceptance.
"""
from pathlib import Path
import argparse
import json
import re
import subprocess
import sys
import shutil

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import flow2_integration_common as common
from scripts import run_flow2_wrapper_postroute as post
from scripts.analyze_flow2_antenna import analyze
from scripts.flow2_antenna_guides import augment
from scripts.flow2_antenna_fixed_special import as_special, widths_from_tlef


def check_disk_budget(root):
    free = shutil.disk_usage(root).free
    if free < 512*1024**2:
        raise ValueError('at least 512 MiB free disk required before writing ECO databases; free='+str(free))


def fixed_net_def(source, destination, target_nets, include_nets=None):
    """Incremental routing-only DEF; preserve all connections and coordinates.

    FIXED is a DEF path property in this OpenDB, not a dbWire setter.
    Never export components, placement, special nets or the affected nets.
    """
    records, lines, active, name = [], [], False, None
    header = []
    for line in source.read_text().splitlines(keepends=True):
        if line.startswith(('VERSION ', 'DIVIDERCHAR ', 'BUSBITCHARS ', 'DESIGN ', 'UNITS ')):
            header.append(line)
        if line.startswith('NETS '):
            active = True
            continue
        if line.startswith('END NETS'):
            break
        if not active:
            continue
        if line.lstrip().startswith('- '):
            if lines:
                raise ValueError('unterminated DEF net')
            name = line.split()[1]
        lines.append(line)
        if line.rstrip().endswith(';'):
            text = ''.join(lines)
            if name not in target_nets and (include_nets is None or name in include_nets) and '+ ROUTED ' in text:
                records.append(text.replace('+ ROUTED ', '+ FIXED '))
            lines, name = [], None
    if lines or len(header) != 5 or not records:
        raise ValueError('incomplete routing DEF')
    destination.write_text(''.join(header)+f'NETS {len(records)} ;\n'+''.join(records)+'END NETS\nEND DESIGN\n')
    return len(records)


def run(root, *, tag, source_tag='ground_repair_srv_20261022_02',
        route_timeout_s=600, copies=3, execute=False, prepared_tag=None):
    root = Path(root).resolve()
    common.tag_ok(tag); common.tag_ok(source_tag)
    if tag == source_tag or not 1 <= route_timeout_s <= 600 or copies not in (1, 2, 3):
        raise ValueError('fresh tag, bounded budget and 1..3 diodes required')
    if (root/common.BASE/tag/'inputs.json').exists():
        raise FileExistsError('retain old evidence; use a fresh antenna ECO tag')
    if execute:
        check_disk_budget(root)
    receipt = root/common.BASE/source_tag/'summary.json'
    source = json.loads(receipt.read_text())
    if source['status'] != 'GROUND_BRIDGES_MACRO_LVS_MATCH':
        raise ValueError('ground-closed macro-LVS source required')
    odb = common._verified(root, source['views']['odb'])
    source_def = common._verified(root, source['views']['def'])
    targets = receipt.parent/'antenna_targets.json'
    target_data = json.loads(targets.read_text())
    # Targets must describe this exact repaired database, not the native open-ground ODB.
    if target_data['odb']['sha256'] != common._sha(odb):
        raise ValueError('measured antenna target ODB differs')
    report = {'format': 'automx-cim-targeted-antenna-eco-v1', 'tag': tag,
              'source_tag': source_tag, 'status': 'PREPARED', 'qualification': 'NOT_QUALIFIED',
              'published_views_changed': False, 'route_timeout_s': route_timeout_s,
              'source_antenna': {k: target_data[k] for k in ('net_violations', 'pin_violations')},
              'scope': 'Candidate only; diode logical connectivity and antenna counts alone do not prove routed connectivity.'}
    if not execute:
        return report
    native_tag = source['source_tag']
    native = root/common.BUILD/native_tag/'design/runs'/native_tag
    guide = native/'tmp/routing/2-global.guide'
    worker = root/'scripts/flow2_targeted_antenna_odb.py'
    guide_worker = root/'scripts/flow2_antenna_guides.py'
    checker = root/'scripts/check_flow2_antenna_odb.py'
    connectivity_worker = root/'scripts/check_flow2_antenna_connectivity.py'
    analyzer = Path(analyze.__code__.co_filename)
    obstacle_worker = Path(as_special.__code__.co_filename)
    sources = [common._item(root, p) for p in (receipt, odb, source_def, targets, guide, worker, guide_worker, checker, connectivity_worker, analyzer, obstacle_worker, Path(__file__))]
    prior = None
    if prepared_tag:
        common.tag_ok(prepared_tag)
        prior_path = root/common.BASE/prepared_tag/'summary.json'
        prior = json.loads(prior_path.read_text())
        if (prior['source_tag'] != source_tag or prior['checks']['legalize']['returncode'] != 0
                or not any(i['path'] == source['views']['odb']['path'] and i['sha256'] == common._sha(odb)
                           for i in prior['sources'])):
            raise ValueError('prepared candidate is not from this ground-closed source')
        reused = common._verified(root, prior['candidate_views']['legalized'])
        sources += [common._item(root, p) for p in (prior_path, reused)]
    store = common.Store(root, tag, {'sources': sources, 'copies': copies,
                                    'route_timeout_s': route_timeout_s,
                                    'image': post.native.notebook.DEFAULT_IMAGE})
    report['sources'] = sources
    frozen = store.build/'executed_host_sources'; frozen.mkdir()
    for p in (worker, guide_worker, checker, connectivity_worker, analyzer, obstacle_worker, Path(__file__)):
        (frozen/p.name).write_bytes(p.read_bytes())
    report['checks'] = {}

    def step(name, program, args, budget):
        command = post.container_command(root, program, args, 'automx-'+tag+'-'+name)
        command[command.index('-w')+1] = str(store.build)
        def invoke(work):
            try:
                return subprocess.run(command, cwd=store.build, text=True, capture_output=True, timeout=budget)
            except subprocess.TimeoutExpired as error:
                subprocess.run(['docker', 'rm', '-f', command[command.index('--name')+1]],
                               capture_output=True, timeout=15)
                output = error.stdout or b''
                if isinstance(output, bytes): output = output.decode(errors='replace')
                return subprocess.CompletedProcess(command, 124, output, '\nBOUNDED_TIMEOUT\n')
        result, _ = store.step(name, command, executor=invoke)
        report['checks'][name] = {'returncode': result.returncode,
                                  'log': common._item(root, store.folder/(name+'.log'))}
        common.save_summary(store.folder/'summary.json', report)
        if result.returncode:
            raise RuntimeError(name+' failed: '+str(result.returncode))
        return result.stdout+result.stderr

    candidate = store.build/'diodes_unrouted.odb'
    legalized = store.build/'diodes_legalized.odb'
    routed = store.build/'diodes_routed.odb'
    try:
        if prior:
            candidate = reused
            report.update(insertion=prior['insertion'], prepared_tag=prepared_tag,
                          fixed_net_count=prior['fixed_net_count'])
        else:
            step('insert', 'openroad', ['-exit', '-python', worker, '--input', odb,
                 '--output', candidate, '--targets', targets, '--report', store.build/'insertion.json',
                 '--copies', str(copies)], 180)
            report['insertion'] = json.loads((store.build/'insertion.json').read_text())
            report['status'] = 'UNROUTED_DIODE_CANDIDATE'
        if prior and prior.get('preservation', {}).get('status') == 'PASS_PRESERVATION_ONLY':
            # Never import over existing native wires: this pinned reader can
            # segfault. The reused ODB is already hash-verified and legalized.
            legalized = reused
            report['preservation'] = prior['preservation']
            report['checks']['legalize'] = {'returncode': 0, 'reused_from': prepared_tag}
        else:
            if prior and prior['insertion'].get('unaffected_wires_pending_fixed_import') != prior['fixed_net_count']:
                raise ValueError('unsafe prepared candidate; fixed import requires absent old wires')
            fixed = store.build/'unaffected_fixed.def'
            report['fixed_net_count'] = fixed_net_def(source_def, fixed, {t['net'] for t in target_data['eco_targets']})
            dpl = store.build/'legalize.tcl'
            dpl.write_text(f'read_db {{{candidate}}}\nread_def -floorplan_initialize {{{fixed}}}\nset_thread_count 8\n'
                           'detailed_placement -max_displacement {100 100}\ncheck_placement -verbose\n'
                           f'write_db {{{legalized}}}\nputs AUTOMX_DIODE_LEGALIZED\nexit\n')
            text = step('legalize', 'openroad', ['-exit', dpl], 180)
            if 'AUTOMX_DIODE_LEGALIZED' not in text:
                raise ValueError('incomplete legalization')
            preservation = store.build/'preservation_legalized.json'
            step('preservation', 'openroad', ['-exit', '-python', checker, '--source', odb,
                 '--candidate', legalized, '--targets', targets, '--output', preservation], 180)
            report['preservation'] = json.loads(preservation.read_text())
            if report['preservation']['status'] != 'PASS_PRESERVATION_ONLY':
                raise ValueError('candidate changed preserved source geometry/connectivity')
        report['status'] = 'LEGALIZED_DIODE_CANDIDATE'
        locations = store.build/'diode_locations.json'
        step('locations', 'openroad', ['-exit', '-python', guide_worker, '--odb', legalized,
             '--output', locations], 60)
        patched, patches = augment(guide.read_text(), json.loads(locations.read_text()), targets_only=True)
        patched_guide = store.build/'diodes.guide'; patched_guide.write_text(patched)
        report['guide_patches'] = patches
        drt = store.build/'route.tcl'
        names = sorted({t['net'] for t in target_data['eco_targets']})
        if any('{' in name or '}' in name or '\n' in name for name in names):
            raise ValueError('unsupported measured net name in native Tcl')
        clear = ('set automx_block [ord::get_db_block]\nforeach name {'+' '.join('{'+n+'}' for n in names)+'} {\n'
                 '  set net [$automx_block findNet $name]\n'
                 '  if {$net == "NULL"} {error "missing measured route target: $name"}\n'
                 '  set wire [$net getWire]\n'
                 '  if {$wire != "NULL"} {odb::dbWire_destroy $wire}\n}\n')
        guard = ('set automx_block [ord::get_db_block]\n'
                 'foreach net [$automx_block getNets] {\n'
                 '  if {[$net isSpecial] && [$net getName] ni {VPWR VGND}} {\n'
                 '    error "unexpected source special net: [$net getName]"\n  }\n}\n')
        # Source ODB contains pin-access caches from a different routing scope.
        # Converting those nets to special changes PA generation. Clear stale
        # cache objects so the pinned writer never reuses dangling preferences.
        clear_access = ('set automx_old_aps [$automx_block getAccessPoints]\n'
                        'puts "AUTOMX_CLEAR_OLD_ACCESS_POINTS [llength $automx_old_aps]"\n'
                        'foreach ap $automx_old_aps {odb::dbAccessPoint_destroy $ap}\n'
                        'unset automx_old_aps\n')
        tlef = post.native.notebook.DEFAULT_PDK/'sky130A/libs.ref/sky130_fd_sc_hd/techlef/sky130_fd_sc_hd__nom.tlef'
        fixed = store.build/'obstacle_regular.def'
        fixed_net_def(source_def, fixed, set(names))
        special = store.build/'obstacle_special.def'
        special.write_text(as_special(fixed.read_text(), widths_from_tlef(tlef.read_text())))
        # Only imported non-supply special nets are temporary; the native two
        # PG nets stay untouched. Original regular wires remain in the DB.
        cleanup = ('foreach net [$automx_block getNets] {\n'
                   '  if {[$net getName] in {VPWR VGND}} {continue}\n'
                   '  if {[$net isSpecial]} {\n'
                   '    foreach swire [$net getSWires] {odb::dbSWire_destroy $swire}\n'
                   '    $net clearSpecial\n  }\n}\n')
        drt.write_text(f'read_db {{{legalized}}}\nset_thread_count 8\n'+guard+clear_access+clear+
                       f'read_def -floorplan_initialize {{{special}}}\nread_guides {{{patched_guide}}}\n'
                       'detailed_route -bottom_routing_layer met1 -top_routing_layer met5 '
                       '-droute_end_iter 6 -or_seed 42 -verbose 1 '
                       f'-output_drc {{{store.build/"route.drc"}}}\n'
                       +cleanup+
                       f'write_db {{{routed}}}\n'
                       f'write_def {{{store.build/"diodes_routed.def"}}}\n'
                       'check_antennas -verbose\nputs AUTOMX_ANTENNA_DONE\nexit\n')
        text = step('route', 'openroad', ['-exit', drt], route_timeout_s)
        report['antenna'] = analyze(text)
        counts = re.findall(r'\[INFO DRT-0199\]\s+Number of violations = (\d+)\.', text)
        if not counts or 'Complete detail routing.' not in text:
            raise ValueError('completed native routing DRC report required')
        report['native_router_drc'] = int(counts[-1])
        if int(counts[-1]) or (store.build/'route.drc').stat().st_size:
            raise ValueError('routing DRC is not zero')
        preservation = store.build/'preservation_routed.json'
        step('preservation_routed', 'openroad', ['-exit', '-python', checker, '--source', odb,
             '--candidate', routed, '--targets', targets, '--output', preservation], 180)
        report['preservation_routed'] = json.loads(preservation.read_text())
        connectivity = store.build/'connectivity.json'
        step('connectivity', 'openroad', ['-exit', '-python', connectivity_worker, '--odb', routed,
             '--targets', targets, '--output', connectivity], 120)
        report['connectivity'] = json.loads(connectivity.read_text())
        if report['connectivity']['status'] != 'PASS_NATIVE_ROUTED_CONNECTIVITY':
            raise ValueError('routed diode connectivity failed')
        report.update(status=('ROUTED_DIODE_ECO_WITH_RESIDUAL_ANTENNA' if report['antenna']['net_violations']
                              else 'ANTENNA_CLOSED_ODB_PENDING_GDS_LVS_STA'), candidate_odb=common._item(root, routed))
        for item in sources: common._verified(root, item)
    except Exception as error:
        report.update(status='BLOCKED_ANTENNA_ECO', error=type(error).__name__+': '+str(error))
    finally:
        for key, path in (('unrouted', candidate), ('legalized', legalized), ('routed', routed)):
            if path.exists(): report.setdefault('candidate_views', {})[key] = common._item(root, path)
        common.save_summary(store.folder/'summary.json', report)
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=ROOT)
    p.add_argument('--tag', required=True)
    p.add_argument('--source-tag', default='ground_repair_srv_20261022_02')
    p.add_argument('--route-timeout-s', type=int, default=600)
    p.add_argument('--copies', type=int, default=3)
    p.add_argument('--prepared-tag')
    p.add_argument('--run', action='store_true')
    a = p.parse_args()
    result = run(a.root, tag=a.tag, source_tag=a.source_tag, route_timeout_s=a.route_timeout_s,
                 copies=a.copies, execute=a.run, prepared_tag=a.prepared_tag)
    print(json.dumps(result, indent=2))
    if a.run and result['status'].startswith('BLOCKED'):
        raise SystemExit(1)
