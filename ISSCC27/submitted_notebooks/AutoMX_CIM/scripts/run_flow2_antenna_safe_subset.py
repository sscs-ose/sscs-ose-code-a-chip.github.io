#!/usr/bin/env python3
"""Keep only antenna ECO nets without new native wire-ordering flags.

Restore flagged nets from the exact ground-closed source, remove only their
new diodes, then measure independent DRC/antenna and connectivity again.
Baseline wire islands remain explicit; this cannot qualify wrapper signoff.
"""
from pathlib import Path
import argparse
import json
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import flow2_integration_common as common
from scripts import run_flow2_wrapper_postroute as post
from scripts.run_flow2_wrapper_antenna_eco import fixed_net_def, check_disk_budget
from scripts.analyze_flow2_antenna import analyze


def connectivity_delta(source, candidate):
    before = {r['net'] for r in source['failures']}
    after = {r['net'] for r in candidate['failures']}
    return {'source_flagged_nets': len(before), 'candidate_flagged_nets': len(after),
            'new_flags': sorted(after-before), 'cleared_flags': sorted(before-after),
            'unmapped_candidate_iterms': sum(len(r['unmapped_iterms']) for r in candidate['records']),
            'scope': 'Native wire-ordering flags, not extracted LVS or proof of functional opens.'}


def drc_rollback_nets(text, targets):
    """Every marker must touch a measured ECO net; restore all such nets."""
    rollback = set()
    canonical = {name.replace('\\', ''): name for name in targets}
    if len(canonical) != len(set(targets)):
        raise ValueError('ambiguous escaped ECO net names')
    markers = re.split(r'(?m)^\s*violation type:', text)[1:]
    if not markers: raise ValueError('completed nonempty DRC markers required')
    for marker in markers:
        names = {name.replace('\\', '') for name in re.findall(r'net:(\S+)', marker)}
        affected = {canonical[name] for name in names if name in canonical}
        if not affected: raise ValueError('DRC marker has no ECO target; cannot safely plan rollback')
        rollback.update(affected)
    return sorted(rollback)


def run(root, *, source_tag, tag, execute=False, prepared_tag=None, drc_tag=None, rollback_reports=(), rollback_graph=None):
    root = Path(root).resolve(); common.tag_ok(tag); common.tag_ok(source_tag)
    if (rollback_reports or rollback_graph) and not drc_tag:
        raise ValueError('rollback reports/graph require an independently measured drc_tag')
    if (root/common.BASE/tag/'inputs.json').exists():
        raise FileExistsError('retain old evidence and use a fresh subset tag')
    if execute:
        check_disk_budget(root)
    source_path = root/common.BASE/source_tag/'summary.json'
    source = json.loads(source_path.read_text())
    work = root/common.BUILD/source_tag
    ground_tag = source['source_tag']
    ground_path = root/common.BASE/ground_tag/'summary.json'
    ground = json.loads(ground_path.read_text())
    original_odb = common._verified(root, ground['views']['odb'])
    original_def = common._verified(root, ground['views']['def'])
    odb = common._verified(root, source['candidate_views']['routed'])
    targets = ground_path.parent/'antenna_targets.json'
    extra_sources = []
    if drc_tag:
        common.tag_ok(drc_tag)
        drc_receipt = root/common.BASE/drc_tag/'summary.json'
        measured = json.loads(drc_receipt.read_text())
        if measured['source_tag'] != source_tag or measured.get('status') != 'INDEPENDENT_ODB_DRC_FAIL':
            raise ValueError('completed independent DRC for this candidate required')
        if common._verified(root, measured['odb']) != odb:
            raise ValueError('independent DRC candidate differs')
        drc_report = common._verified(root, measured['drc_report'])
        names = drc_rollback_nets(drc_report.read_text(), {t['net'] for t in json.loads(targets.read_text())['eco_targets']})
        target_names = {t['net'] for t in json.loads(targets.read_text())['eco_targets']}
        if rollback_graph:
            common.tag_ok(rollback_graph)
            graph_path = root/common.BASE/rollback_graph/'summary.json'
            graph = json.loads(graph_path.read_text())
            if (graph['status'] != 'CONSERVATIVE_ROLLBACK_SELECTION_ONLY' or
                    graph['candidate_tag'] != source_tag or graph['ground_tag'] != ground_tag or
                    not set(graph['rollback_nets']) <= target_names):
                raise ValueError('conflict graph source/scope differs')
            for expected in (ground['views']['odb'], source['candidate_views']['routed']):
                if not any(item == expected for item in graph['sources']):
                    raise ValueError('conflict graph ODB binding differs')
            for item in graph['sources']:
                extra_sources.append(common._verified(root, item))
            names = sorted(set(names) | set(graph['rollback_nets']))
            extra_sources.append(graph_path)
        for previous_tag in rollback_reports:
            common.tag_ok(previous_tag)
            previous_path = root/common.BASE/previous_tag/'summary.json'
            previous = json.loads(previous_path.read_text())
            if (previous['source_tag'] != source_tag or previous['ground_tag'] != ground_tag
                    or previous.get('checks', {}).get('subset', {}).get('returncode') != 0
                    or not previous.get('independent_drc_bytes')):
                raise ValueError('completed DRC subset from the same routed source required')
            if not any(item['path'] == source['candidate_views']['routed']['path']
                       and item['sha256'] == common._sha(odb) for item in previous['sources']):
                raise ValueError('subset routed source hash differs')
            prior_drc = root/common.BUILD/previous_tag/'independent.drc'
            names = sorted(set(names) | set(previous['rollback_nets']) |
                           set(drc_rollback_nets(prior_drc.read_text(), target_names)))
            extra_sources += [previous_path, prior_drc]
        # Reuse the actual wire-ordering baseline measured on the same ground source.
        baseline_tag = 'antenna_eco_srv_20261022_08'
        baseline_receipt = root/common.BASE/baseline_tag/'summary.json'
        if json.loads(baseline_receipt.read_text())['source_tag'] != ground_tag:
            raise ValueError('connectivity baseline ground source differs')
        baseline_path = root/common.BUILD/baseline_tag/'connectivity_source.json'
        baseline = json.loads(baseline_path.read_text())
        delta = {'new_flags': names, 'selection': 'All target nets touching independently measured DRC markers'}
        extra_sources += [drc_receipt, drc_report, baseline_receipt]
        conn_path = None
    else:
        baseline_path, conn_path = work/'connectivity_source.json', work/'connectivity.json'
        baseline, conn = [json.loads(p.read_text()) for p in (baseline_path, conn_path)]
        delta = connectivity_delta(baseline, conn)
        if (source.get('native_router_drc') != 0
                or source['preservation_routed']['status'] != 'PASS_PRESERVATION_ONLY'
                or not delta['new_flags']):
            raise ValueError('measured zero-DRC preserved candidate with new flags required')
    report = {'format': 'automx-cim-antenna-safe-subset-v1', 'tag': tag,
              'source_tag': source_tag, 'ground_tag': ground_tag,
              'status': 'PREPARED', 'qualification': 'NOT_QUALIFIED',
              'rollback_nets': delta['new_flags'], 'original_delta': delta,
              'published_views_changed': False,
              'scope': 'ODB prototype only. Baseline connectivity flags retained; no GDS/LVS/STA/analog qualification.'}
    if not execute:
        return report
    checker = root/'scripts/check_flow2_antenna_odb.py'
    connectivity = root/'scripts/check_flow2_antenna_connectivity.py'
    code = [Path(__file__), Path(fixed_net_def.__code__.co_filename), Path(analyze.__code__.co_filename), checker, connectivity]
    sources = [common._item(root, p) for p in
               (source_path, ground_path, odb, original_odb, original_def, targets, baseline_path,
                *([conn_path] if conn_path else []), *extra_sources, *code)]
    prepared = None
    if prepared_tag:
        common.tag_ok(prepared_tag)
        prior_path = root/common.BASE/prepared_tag/'summary.json'
        prior = json.loads(prior_path.read_text())
        if prior['source_tag'] != source_tag or prior['rollback_nets'] != delta['new_flags']:
            raise ValueError('prepared subset has different routing or rollback plan')
        prepared = common._verified(root, prior['candidate_odb'])
        sources += [common._item(root, p) for p in (prior_path, prepared)]
    store = common.Store(root, tag, {'sources': sources, 'rollback_nets': delta['new_flags'],
                                    'image': post.native.notebook.DEFAULT_IMAGE})
    report['sources'] = sources
    frozen = store.build/'executed_host_sources'; frozen.mkdir()
    for p in code: (frozen/p.name).write_bytes(p.read_bytes())
    restore = store.build/'restore.def'
    count = fixed_net_def(original_def, restore, set(), include_nets=set(delta['new_flags']))
    if count != len(delta['new_flags']):
        raise ValueError('every rollback net must have original physical routing')
    report['checks'] = {}

    def step(name, program, args, budget):
        command = post.container_command(root, program, args, 'automx-'+tag+'-'+name)
        command[command.index('-w')+1] = str(store.build)
        def invoke(w):
            try:
                return subprocess.run(command, cwd=store.build, capture_output=True, text=True, timeout=budget)
            except subprocess.TimeoutExpired as error:
                subprocess.run(['docker', 'rm', '-f', command[command.index('--name')+1]], capture_output=True, timeout=15)
                text = error.stdout or b''
                if isinstance(text, bytes): text = text.decode(errors='replace')
                return subprocess.CompletedProcess(command, 124, text, '\nBOUNDED_TIMEOUT\n')
        result, _ = store.step(name, command, executor=invoke)
        report['checks'][name] = {'returncode': result.returncode,
                                  'log': common._item(root, store.folder/(name+'.log'))}
        common.save_summary(store.folder/'summary.json', report)
        return result

    candidate = store.build/'subset.odb'
    names = delta['new_flags']
    if any('{' in n or '}' in n or '\n' in n for n in names):
        raise ValueError('unsupported native net name')
    script = store.build/'subset.tcl'
    clear_access = ('set old_aps [$block getAccessPoints]\n'
                    'puts "AUTOMX_CLEAR_ACCESS_BEFORE_DELETE [llength $old_aps]"\n'
                    'foreach ap $old_aps {odb::dbAccessPoint_destroy $ap}\n'
                    'unset old_aps\n') if drc_tag else ''
    refresh = ('pin_access -bottom_routing_layer met1 -top_routing_layer met5\n'
               'puts AUTOMX_ACCESS_REFRESH_DONE\n') if drc_tag else ''
    script.write_text(f'read_db {{{odb}}}\nset block [ord::get_db_block]\n'+clear_access+
        'set targets [dict create '+' '.join('{'+n+'} 1' for n in names)+']\n'
        'set removed 0\nforeach inst [$block getInsts] {\n'
        '  if {![string match AUTOMX_AE_* [$inst getName]]} {continue}\n'
        '  set net [[$inst findITerm DIODE] getNet]\n'
        '  if {[dict exists $targets [$net getName]]} {odb::dbInst_destroy $inst; incr removed}\n}\n'
        'foreach name [dict keys $targets] {\n'
        '  set net [$block findNet $name]\n  set wire [$net getWire]\n'
        '  if {$wire != "NULL"} {odb::dbWire_destroy $wire}\n}\n'
        f'read_def -floorplan_initialize {{{restore}}}\nwrite_db {{{candidate}}}\n'
        'puts "AUTOMX_SUBSET_DIODES_REMOVED $removed"\n'
        'set_thread_count 8\n'+refresh+f'drt::check_drc -output_file {{{store.build/"independent.drc"}}}\n'
        'puts AUTOMX_SUBSET_DRC_DONE\ncheck_antennas -verbose\nputs AUTOMX_ANTENNA_DONE\nexit\n')
    if prepared:
        candidate = prepared
        report['prepared_tag'] = prepared_tag
        script.write_text(f'read_db {{{candidate}}}\n'
            'set_thread_count 8\n'+refresh+f'drt::check_drc -output_file {{{store.build/"independent.drc"}}}\n'
            'puts AUTOMX_SUBSET_DRC_DONE\ncheck_antennas -verbose\nputs AUTOMX_ANTENNA_DONE\nexit\n')
    try:
        result = step('subset', 'openroad', ['-exit', script], 180)
        text = result.stdout+result.stderr
        report['antenna'] = analyze(text)
        if result.returncode or 'AUTOMX_SUBSET_DRC_DONE' not in text:
            raise ValueError('independent DRC did not complete')
        report['independent_drc_bytes'] = (store.build/'independent.drc').stat().st_size
        if report['independent_drc_bytes']:
            raise ValueError('independent route DRC not zero; baseline requires a matching measurement')
        for name, worker, args in (
            ('preservation', checker, ['--source', original_odb, '--candidate', candidate,
                                      '--targets', targets, '--output', store.build/'preservation.json']),
            ('connectivity', connectivity, ['--odb', candidate, '--targets', targets,
                                            '--output', store.build/'connectivity.json'])):
            result = step(name, 'openroad', ['-exit', '-python', worker, *args], 180)
            path = store.build/(name+'.json')
            report[name] = json.loads(path.read_text())
            if name == 'preservation' and result.returncode:
                raise ValueError('preserved source geometry/connectivity changed')
        report['connectivity_delta'] = connectivity_delta(baseline, report['connectivity'])
        if report['connectivity_delta']['new_flags'] or report['connectivity_delta']['unmapped_candidate_iterms']:
            raise ValueError('subset still introduces connectivity flags or missing pins')
        report['status'] = 'ROUTED_PROTOTYPE_NO_NEW_CONNECTIVITY_FLAGS_ANTENNA_REMAINS'
        for item in sources: common._verified(root, item)
    except Exception as error:
        report.update(status='BLOCKED_SAFE_SUBSET', error=type(error).__name__+': '+str(error))
    finally:
        if candidate.exists(): report['candidate_odb'] = common._item(root, candidate)
        common.save_summary(store.folder/'summary.json', report)
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=ROOT)
    p.add_argument('--source-tag', default='antenna_eco_srv_20261022_08')
    p.add_argument('--tag', required=True)
    p.add_argument('--run', action='store_true')
    p.add_argument('--prepared-tag')
    p.add_argument('--drc-tag', help='rollback ECO nets touching independently measured DRC markers')
    p.add_argument('--rollback-report', action='append', default=[],
                   help='include rollback set and new conflicts measured by a prior subset of the same routed source')
    p.add_argument('--rollback-graph', help='conservative route-conflict closure tied to both exact ODBs')
    a = p.parse_args()
    result = run(a.root, source_tag=a.source_tag, tag=a.tag, execute=a.run,
                 prepared_tag=a.prepared_tag, drc_tag=a.drc_tag, rollback_reports=a.rollback_report,
                 rollback_graph=a.rollback_graph)
    print(json.dumps(result, indent=2))
    if a.run and result['status'].startswith('BLOCKED'):
        raise SystemExit(1)
