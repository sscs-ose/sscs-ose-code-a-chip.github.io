#!/usr/bin/env python3
"""Independent bounded DRC on an exact ODB, before antenna/wire ordering.

No routing or published view changes. Compare baseline and candidate with
the same pinned parser; DRT marker counts are not whole-GDS Magic signoff.
"""
from pathlib import Path
import argparse
from collections import Counter
import json
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import flow2_integration_common as common
from scripts import run_flow2_wrapper_postroute as post


def marker_counts(path):
    counts = Counter()
    with Path(path).open() as stream:
        for line in stream:
            match = re.match(r'^\s*violation type:\s*(\S.*?)\s*$', line)
            if match:
                counts[match[1]] += 1
    return dict(counts)


def run(root, *, source_tag, tag, timeout_s=90, execute=False, refresh_pin_access=False):
    root = Path(root).resolve()
    common.tag_ok(source_tag); common.tag_ok(tag)
    if not 1 <= timeout_s <= 180:
        raise ValueError('bounded independent DRC budget required')
    if (root/common.BASE/tag/'inputs.json').exists():
        raise FileExistsError('fresh diagnostic tag required')
    receipt = root/common.BASE/source_tag/'summary.json'
    data = json.loads(receipt.read_text())
    views = data.get('candidate_views', {})
    item = views.get('routed') or data.get('candidate_odb') or data.get('views', {}).get('odb')
    if not item:
        raise ValueError('completed routed ODB required')
    odb = common._verified(root, item)
    sources = [common._item(root, p) for p in (receipt, odb, Path(__file__))]
    report = {'format': 'automx-cim-independent-odb-drc-v1', 'tag': tag,
              'source_tag': source_tag, 'odb': common._item(root, odb),
              'status': 'PREPARED', 'qualification': 'NOT_QUALIFIED',
              'scope': 'Independent pinned DRT DRC on fresh ODB, before antenna/orderWires; '
                       'not GDS/Magic/transistor LVS/PEX or whole-system qualification.',
              'sources': sources, 'timeout_s': timeout_s, 'refresh_pin_access': refresh_pin_access}
    if not execute:
        return report
    store = common.Store(root, tag, {'sources': sources, 'timeout_s': timeout_s,
                                    'refresh_pin_access': refresh_pin_access,
                                    'image': post.native.notebook.DEFAULT_IMAGE})
    frozen = store.build/'executed_host_sources'; frozen.mkdir()
    (frozen/Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    output = store.build/'independent.drc'
    tcl = store.build/'check.tcl'
    access = ('set automx_block [ord::get_db_block]\n'
              'set automx_old_aps [$automx_block getAccessPoints]\n'
              'puts "AUTOMX_CLEAR_OLD_ACCESS_POINTS [llength $automx_old_aps]"\n'
              'foreach ap $automx_old_aps {odb::dbAccessPoint_destroy $ap}\n'
              'unset automx_old_aps\n'
              'pin_access -bottom_routing_layer met1 -top_routing_layer met5\n'
              'puts AUTOMX_ACCESS_REFRESH_DONE\n') if refresh_pin_access else ''
    tcl.write_text('read_db {'+str(odb)+'}\nset_thread_count 8\n'+access+
                   'drt::check_drc -output_file {'+str(output)+'}\n'
                   'puts AUTOMX_INDEPENDENT_DRC_DONE\nexit\n')
    cmd = post.container_command(root, 'openroad', ['-exit', tcl], 'automx-'+tag)
    cmd[cmd.index('-w')+1] = str(store.build)
    def invoke(work):
        try:
            return subprocess.run(cmd, cwd=store.build, text=True, capture_output=True, timeout=timeout_s)
        except subprocess.TimeoutExpired as error:
            subprocess.run(['docker', 'rm', '-f', 'automx-'+tag], capture_output=True, timeout=15)
            text = error.stdout or b''
            if isinstance(text, bytes): text = text.decode(errors='replace')
            return subprocess.CompletedProcess(cmd, 124, text, '\nBOUNDED_TIMEOUT\n')
    try:
        result, _ = store.step('drc', cmd, executor=invoke)
        report['returncode'] = result.returncode
        if result.returncode or 'AUTOMX_INDEPENDENT_DRC_DONE' not in result.stdout or not output.exists():
            raise ValueError('independent DRC did not complete')
        counts = marker_counts(output)
        if output.stat().st_size and not counts:
            raise ValueError('nonempty DRC report without recognized markers')
        report.update(marker_counts=counts, total_markers=sum(counts.values()),
                      drc_report=common._item(root, output),
                      status='INDEPENDENT_ODB_DRC_FAIL' if counts else 'INDEPENDENT_ODB_DRC_CLEAN')
        for source in sources: common._verified(root, source)
    except Exception as error:
        report.update(status='BLOCKED_INDEPENDENT_ODB_DRC', error=type(error).__name__+': '+str(error))
    finally:
        common.save_summary(store.folder/'summary.json', report)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--source-tag', required=True)
    parser.add_argument('--tag', required=True)
    parser.add_argument('--timeout-s', type=int, default=90)
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--refresh-pin-access', action='store_true',
                        help='regenerate only pin-access metadata in disposable memory before DRC')
    args = parser.parse_args()
    report = run(args.root, source_tag=args.source_tag, tag=args.tag,
                 timeout_s=args.timeout_s, execute=args.run, refresh_pin_access=args.refresh_pin_access)
    print(json.dumps(report, indent=2))
    if args.run and report['status'] != 'INDEPENDENT_ODB_DRC_CLEAN':
        raise SystemExit(1)
