#!/usr/bin/env python3
"""Bounded RC extraction of the exact tap-repaired core/acquisition GDS.

Reuse the physical-block checks, keeping the original repair/source receipts
immutable. This closes a block extraction dependency, not wrapper/ADC signoff.
"""
from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import flow2_integration_common as common
from scripts import flow2_wrapper_physical as physical
from scripts import run_flow2_wrapper_transistor_lvs as transistor
from scripts import run_flow2_mixed_wrapper_gds as native


def run(root, *, repair_tag='core_full_drc_srv_20261022_02',
        tag='core_tap_pex_srv_20261022_01', timeout_s=180, execute=False):
    root = Path(root).resolve()
    common.tag_ok(tag); common.tag_ok(repair_tag)
    if not 1 <= timeout_s <= 600:
        raise ValueError('tool budget must be 1..600 seconds')
    receipt = root/common.BASE/repair_tag/'summary.json'
    repair = json.loads(receipt.read_text())
    if (repair.get('status') != 'CORE_FULL_DRC_LVS_ACCESS_READY'
            or repair.get('magic_full_drc') != 0 or repair.get('transistor_lvs') != 'MATCH_UNIQUELY'):
        raise ValueError('full-DRC/transistor-LVS repair receipt required')
    for item in repair['sources']:
        common._verified(root, item)
    gds = common._verified(root, repair['views']['gds'])
    schematic = common._verified(root, repair['views']['schematic'])
    cell = native.d.core.CELL
    reference = schematic.read_text()
    pins = transistor.port_order(transistor.definitions(reference)[cell.lower()])
    pdk = native.notebook.DEFAULT_PDK/'sky130A'
    report = {'format': 'automx-cim-core-tap-pex-v1', 'tag': tag, 'repair_tag': repair_tag,
              'status': 'PREPARED', 'qualification': 'NOT_QUALIFIED',
              'source_gds': common._item(root, gds), 'pdk': str(pdk),
              'scope': 'Exact repaired core/acquisition block DRC, transistor LVS and RC extraction; '
                       'no whole-wrapper/ADC, transfer, noise or PVT qualification'}
    if not execute:
        return report
    layout = (f'crashbackups stop\ndrc off\ngds read {{{gds}}}\nload {cell}\nselect top cell\n'
              'box -100um -100um 10000um 5000um\ndrc on\ndrc style drc(full)\ndrc check\ndrc catchup\n'
              'puts "AUTOMX_WRAPPER_DRC=[drc list count total]"\n'
              f'file copy -force {{{gds}}} {cell}.gds\nlef write {cell}.lef\n'
              'puts AUTOMX_WRAPPER_LAYOUT_DONE\nquit -noprompt\n')
    sources = [common._item(root, p) for p in
               (receipt, gds, schematic, Path(__file__), Path(physical.__file__))]
    # The outer native campaign owns export; no duplicate mirrors/ZIPs here.
    with common.export_mode('deferred'):
        block = physical.physical(root, pdk=pdk, tag=tag, cell=cell, pins=pins,
                                  layout_tcl=layout, reference=reference, sources=sources, timeout_s=timeout_s)
    report['block'] = block
    if block.get('status') == 'BLOCK_DRC_TRANSISTOR_LVS_RC_PEX_PASS':
        extracted_gds = common._verified(root, block['views']['gds'])
        if common._sha(extracted_gds) != common._sha(gds):
            raise ValueError('PEX layout differs from actual repaired GDS')
        pex = common._verified(root, block['views']['pex'])
        report['substrate_rc_audit'] = native.acq._rc_audit(pex)
        report['views'] = block['views']
        report['status'] = ('CORE_TAP_DRC_LVS_RC_PEX_PASS'
                            if not report['substrate_rc_audit']['unreferenced_capacitive_nodes']
                            else 'BLOCKED_CORE_TAP_SUBSTRATE_RC')
    else:
        report['status'] = 'BLOCKED_CORE_TAP_PEX'
    common.save_summary(root/common.BASE/tag/'tap_pex_summary.json', report)
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=ROOT)
    p.add_argument('--tag', default='core_tap_pex_srv_20261022_01')
    p.add_argument('--repair-tag', default='core_full_drc_srv_20261022_02')
    p.add_argument('--timeout-s', type=int, default=180)
    p.add_argument('--run', action='store_true')
    a = p.parse_args()
    print(json.dumps(run(a.root, tag=a.tag, repair_tag=a.repair_tag,
                         timeout_s=a.timeout_s, execute=a.run), indent=2))
