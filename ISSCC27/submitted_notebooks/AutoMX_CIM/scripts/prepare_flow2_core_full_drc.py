#!/usr/bin/env python3
"""Derive/check core taps and restrict macro access to real top-level metal.

The original macro/receipts stay immutable. New GDS requires full native-PDK
Magic DRC and transistor LVS. Added ground metal changes parasitics: previous
core RC/analog characterization does not qualify this derived prototype.
"""
from pathlib import Path
import argparse
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import flow2_integration_common as common
from scripts import flow2_wrapper_pdn as access
from scripts import run_flow2_mixed_wrapper_gds as native
from scripts import run_flow2_wrapper_transistor_lvs as lvs

RECIPE = Path('physical/sky130/wrapper_prototype/repair_core_taps.tcl')


def top_metal_access(text, extra_obs=()):
    hidden, ports = [], access.pins(text)
    if not ports: raise ValueError('macro has no ports')
    for name, block in ports.items():
        shapes = list(access.geometry(block))
        target = 'met2' if name.startswith(('WPOS_', 'WNEG_')) else 'met4'
        kept = [(layer, rect) for layer, rect in shapes if layer == target]
        if not kept: raise ValueError('no real '+target+' access for '+name)
        hidden.extend((layer, rect) for layer, rect in shapes if layer != target)
        header = block[:block.index('    PORT')]
        body = '    PORT\n'
        for layer, rect in kept:
            body += '      LAYER '+layer+' ;\n        RECT '+' '.join(f'{v:.3f}' for v in rect)+' ;\n'
        text = text.replace(block, header+body+'    END\n  END '+name, 1)
    obs = re.search(r'(?ms)^  OBS\s*\n(.*?)^  END\s*\n(?=END )', text)
    if not obs: raise ValueError('macro OBS missing')
    extra = ''.join('      LAYER '+layer+' ;\n        RECT '+' '.join(f'{v:.3f}' for v in rect)+' ;\n'
                    for layer, rect in [*hidden, *extra_obs])
    text = text[:obs.end(1)] + extra + text[obs.end(1):]
    return text, {'pins': len(ports), 'hidden_rectangles_preserved_as_OBS': len(hidden),
                  'policy': 'WPOS/WNEG met2, all other pins met4; original geometry only'}


def run(root, *, tag, source_gds_tag, execute=False):
    root = Path(root).resolve()
    common.tag_ok(tag); common.tag_ok(source_gds_tag)
    config = root/common.BUILD/source_gds_tag/'design/config.json'
    cfg = json.loads(config.read_text())
    gds, lef, cond_lef = map(Path, [cfg['EXTRA_GDS_FILES'][0], cfg['EXTRA_LEFS'][0], cfg['EXTRA_LEFS'][1]])
    ref = gds.with_name(native.d.core.CELL+'.reference.spice')
    pdk = native.notebook.DEFAULT_PDK/'sky130A'
    sources = [common._item(root, p) for p in (config, gds, lef, cond_lef, ref, root/RECIPE, Path(__file__))]
    report = {'status': 'PREPARED', 'tag': tag, 'source_gds_tag': source_gds_tag,
              'qualification': 'NOT_QUALIFIED', 'sources': sources,
              'scope': 'Derived prototype core taps and macro access; new core PEX/loaded analog still required'}
    if not execute: return report
    store = common.Store(root, tag, {'sources': sources, 'pdk': str(pdk), 'tech': common._sha(pdk/'libs.tech/magic/sky130A.tech')})
    try:
        tcl = 'set SOURCE_GDS {'+str(gds)+'}\n'+(root/RECIPE).read_text()
        result, work = store.step('layout', ['magic', str(pdk)], tcl=tcl,
            executor=lambda work: native.acq.stage5._magic(native.acq.stage5._find_tool('magic'),
                pdk/'libs.tech/magic/sky130A.tech', work, tcl, 120))
        if result.returncode or not re.search(r'(?m)^COUNT=0$', result.stdout):
            raise ValueError('derived core full DRC failed')
        netgen = store.build/'netgen.log'
        cmd = [native.acq.stage5._find_tool('netgen'), '-batch', 'lvs',
               str(work/'repaired.spice')+' '+native.d.core.CELL, str(ref)+' '+native.d.core.CELL,
               str(pdk/'libs.tech/netgen/sky130A_setup.tcl'), str(netgen)]
        result, _ = store.step('lvs', cmd, executor=lambda folder: native.acq.stage5._run(cmd, folder, 120))
        if result.returncode: raise ValueError('Netgen failed')
        lvs.validate_netgen(netgen.read_text()+'\n'+result.stdout+result.stderr)
        # GDS coordinates to original LEF coordinates; outline is unchanged.
        original = lef.read_text()
        ox, oy = map(float, re.search(r'ORIGIN\s+(-?[\d.]+)\s+(-?[\d.]+)', original).groups())
        obs = [('met1', (x1+ox, y1+oy, x2+ox, y2+oy)) for x1,y1,x2,y2 in
               ((18.5,148.1,19.1,190.7),(46.9,148.1,47.5,190.7),(18.5,148.1,47.5,148.7))]
        text, proof = top_metal_access(original, obs)
        core_lef = store.build/'core.access.lef'; core_lef.write_text(text)
        text, cond_proof = top_metal_access(cond_lef.read_text())
        conditioner_lef = store.build/'conditioner.access.lef'; conditioner_lef.write_text(text)
        report.update(status='CORE_FULL_DRC_LVS_ACCESS_READY', magic_full_drc=0,
                      transistor_lvs='MATCH_UNIQUELY', core_access=proof, conditioner_access=cond_proof,
                      views={key: common._item(root, p) for key,p in
                             (('gds',work/'repaired.gds'),('lef',core_lef),('conditioner_lef',conditioner_lef),('schematic',ref))},
                      lvs_report=common._item(root,netgen))
    except Exception as error:
        report.update(status='BLOCKED_CORE_FULL_DRC_REPAIR', error=f'{type(error).__name__}: {error}')
        raise
    finally:
        common.save_summary(store.folder/'summary.json', report)
    return report


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=ROOT)
    p.add_argument('--tag', required=True); p.add_argument('--source-gds-tag', required=True)
    p.add_argument('--run', action='store_true'); a=p.parse_args()
    print(json.dumps(run(a.root, tag=a.tag, source_gds_tag=a.source_gds_tag, execute=a.run),indent=2))
