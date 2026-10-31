#!/usr/bin/env python3
"""Bounded full-hierarchy Magic DRC on a hash-verified mixed-signal GDS.

Reads all GDS geometry, without LEF abstracts or clipped context. No extraction,
rerouting, published writes or qualification inferred from missing output.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import flow2_integration_common as common
from scripts import run_flow2_wrapper_postroute as post


def drc_count(text):
    counts = re.findall(r'^AUTOMX_FULL_MAGIC_DRC=(\d+)\s*$', text, re.M)
    if len(counts) != 1 or 'AUTOMX_FULL_MAGIC_DONE' not in text:
        raise ValueError('completed whole-GDS DRC marker/count required')
    if re.search(r'(?im)^\s*(?:error:|fatal|could not open|cannot open|cell .* not found)', text):
        raise ValueError('Magic reported a load/check error')
    return int(counts[0])


def run(root, *, tag, source_tag='ground_repair_srv_20261022_02', timeout_s=180, execute=False):
    root = Path(root).resolve(); common.tag_ok(tag); common.tag_ok(source_tag)
    if not 1 <= timeout_s <= 300: raise ValueError('bounded full Magic budget required')
    if (root/common.BASE/tag/'inputs.json').exists(): raise FileExistsError('fresh full Magic tag required')
    receipt = root/common.BASE/source_tag/'summary.json'
    data = json.loads(receipt.read_text())
    if data['status'] not in ('GROUND_BRIDGES_MACRO_LVS_MATCH',
                             'GDS_PROTOTYPE_KLAYOUT_CLEAN_SIGNAL_LVS_ONLY'):
        raise ValueError('ground-closed baseline or audited prototype required')
    gds = common._verified(root, data['views']['gds'])
    pdk = post.native.notebook.DEFAULT_PDK/'sky130A'
    sources = [common._item(root, p) for p in (receipt, gds, Path(__file__))]
    identity = {'sources': sources, 'timeout_s': timeout_s, 'pdk': str(pdk),
                'technology_sha256': common._sha(pdk/'libs.tech/magic/sky130A.tech'),
                'image': post.native.notebook.DEFAULT_IMAGE}
    report = {'format': 'automx-cim-full-gds-magic-drc-v1', 'tag': tag, 'source_tag': source_tag,
              'status': 'PREPARED', 'qualification': 'NOT_QUALIFIED', 'inputs': identity,
              'scope': 'Full self-contained GDS hierarchy, native drc(full), no LEF/ROI; '
                       'not transistor LVS/PEX, antenna, timing or analog qualification.'}
    if not execute: return report
    store = common.Store(root, tag, identity)
    frozen = store.build/'executed_host_sources'; frozen.mkdir()
    (frozen/Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    rc = store.build/'magicrc'
    rc.write_text('set ::env(PDK_ROOT) {'+str(pdk.parent)+'}\nset ::env(MAGTYPE) mag\n'
                  'source {'+str(pdk/'libs.tech/magic/sky130A.magicrc')+'}\n')
    tcl = store.build/'check.tcl'
    tcl.write_text('crashbackups stop\ndrc off\ngds read {'+str(gds)+'}\n'
        'load '+post.TOP+'\nselect top cell\nbox -100um -100um 10000um 5000um\n'
        'puts AUTOMX_FULL_GDS_LOADED\ndrc on\ndrc style drc(full)\ndrc check\ndrc catchup\n'
        'set output [open {'+str(store.build/'full.drc')+'} w]\n'
        'puts $output [drc listall why]\nclose $output\n'
        'puts "AUTOMX_FULL_MAGIC_DRC=[drc listall count total]"\n'
        'puts AUTOMX_FULL_MAGIC_DONE\nquit -noprompt\n')
    cmd = post.container_command(root, 'magic', ['-dnull', '-noconsole', '-rcfile', rc, tcl], 'automx-'+tag)
    cmd[cmd.index('-w')+1] = str(store.build)
    def invoke(work):
        try: return subprocess.run(cmd, cwd=store.build, text=True, capture_output=True, timeout=timeout_s)
        except subprocess.TimeoutExpired as error:
            subprocess.run(['docker','rm','-f','automx-'+tag],capture_output=True,timeout=15)
            output = error.stdout or b''
            if isinstance(output, bytes): output = output.decode(errors='replace')
            return subprocess.CompletedProcess(cmd,124,output,'\nBOUNDED_TIMEOUT\n')
    try:
        result, _ = store.step('magic', cmd, executor=invoke)
        report['returncode'] = result.returncode
        report['gds_load_completed'] = 'AUTOMX_FULL_GDS_LOADED' in result.stdout
        if result.returncode: raise ValueError('full Magic did not complete: '+str(result.returncode))
        count = drc_count(result.stdout+result.stderr)
        report.update(violations=count, status='FULL_GDS_MAGIC_DRC_CLEAN' if count == 0 else 'FULL_GDS_MAGIC_DRC_FAIL',
                      report=common._item(root, store.build/'full.drc'))
        for item in sources: common._verified(root,item)
    except Exception as error:
        report.update(status='BLOCKED_FULL_GDS_MAGIC_DRC', error=type(error).__name__+': '+str(error))
    finally:
        common.save_summary(store.folder/'summary.json',report)
    return report


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=ROOT);p.add_argument('--tag',required=True)
    p.add_argument('--source-tag',default='ground_repair_srv_20261022_02')
    p.add_argument('--timeout-s',type=int,default=180);p.add_argument('--run',action='store_true')
    a=p.parse_args();r=run(a.root,tag=a.tag,source_tag=a.source_tag,timeout_s=a.timeout_s,execute=a.run)
    print(json.dumps(r,indent=2))
    if a.run and r['status']!='FULL_GDS_MAGIC_DRC_CLEAN': raise SystemExit(1)
