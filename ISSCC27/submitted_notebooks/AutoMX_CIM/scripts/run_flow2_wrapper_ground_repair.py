#!/usr/bin/env python3
"""Bounded same-layer ground ECO on completed routing, without place/route."""
from pathlib import Path
import argparse
import json
import os
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import flow2_integration_common as common
from scripts import run_flow2_wrapper_postroute as post
from scripts import run_flow2_wrapper_transistor_lvs as lvs

TOP = post.TOP
PLAN = [
    {'instance': 'core_i', 'rect_um': [636.8, 213.52, 639.14, 214.12],
     'pin_um': [633.43, 213.52, 637.2, 214.12], 'stripe_um': [638.74, 144.72, 640.34, 1387.44]},
    {'instance': 'condition_i', 'rect_um': [1556.4, 53.52, 1560.74, 54.12],
     'pin_um': [1553.03, 53.52, 1556.8, 54.12], 'stripe_um': [1560.34, 10.64, 1561.94, 62.92]},
]


def cached_mag(source, destination):
    """Retain every routing/placement record; resolve children from verified LEFs."""
    count = 0
    with source.open() as src, destination.open('w') as out:
        for line in src:
            if line.startswith('use '):
                fields = line.split()
                if len(fields) < 3:
                    raise ValueError('invalid cached cell use')
                if len(fields) > 3:
                    line = ' '.join(fields[:3])+'\n'; count += 1
            out.write(line)
    return count


def run(root, *, source_tag='mixed_wrapper_srv_20261022_04_impl_gds',
        tag='ground_repair_srv_20261022_01', timeout_s=600, execute=False):
    root = Path(root).resolve(); common.tag_ok(source_tag); common.tag_ok(tag)
    if not 1 <= timeout_s <= 600:
        raise ValueError('tool budget must be 1..600 seconds')
    if execute and (root/common.BASE/tag/'inputs.json').exists():
        raise FileExistsError('ground ECO already reserved; retain evidence and use a fresh tag')
    source = root/common.BUILD/source_tag/'design/runs'/source_tag
    summary = root/common.BASE/source_tag/'summary.json'
    data = json.loads(summary.read_text())
    if data.get('metrics', {}).get('tritonRoute_violations') != '0':
        raise ValueError('completed zero-DRC routing source required')
    gds = common._verified(root, data['views']['gds'])
    config = source.parent.parent/'config.json'; settings = json.loads(config.read_text())
    pdk = post.native.notebook.DEFAULT_PDK/'sky130A'
    odb = source/'results/routing'/(TOP+'.odb')
    mag = source/'results/signoff'/(TOP+'.mag')
    netlist = source/'tmp/signoff/19-automx_cim_mixed_signal_proto.pnl.v'
    recipe = root/'physical/sky130/wrapper_prototype/repair_wrapper_ground.tcl'
    worker = root/'scripts/flow2_ground_bridge_gds.py'
    lefs = [Path(p) for p in settings['EXTRA_LEFS']]
    report = {'format': 'automx-cim-ground-repair-v1', 'tag': tag, 'source_tag': source_tag,
              'status': 'PREPARED', 'qualification': 'NOT_QUALIFIED', 'plan': PLAN,
              'scope': 'Two measured M4 ground bridges; macro-connectivity LVS only. '
                       'No transistor LVS, full Magic DRC, new STA/RC characterization or ADC qualification.'}
    if not execute:
        return report
    items = [common._item(root, p) for p in
             (summary, config, odb, mag, gds, netlist, recipe, worker, Path(__file__), Path(lvs.__file__), *lefs)]
    store = common.Store(root, tag, {'sources': items, 'plan': PLAN, 'timeout_s': timeout_s,
                                    'pdk': str(pdk), 'image': post.native.notebook.DEFAULT_IMAGE})
    (store.build/'plan.json').write_text(json.dumps(PLAN, indent=2)+'\n')
    snapshot = store.build/'executed_host_sources'; snapshot.mkdir(exist_ok=True)
    for path in (Path(__file__), worker, recipe):
        (snapshot/path.name).write_bytes(path.read_bytes())
    report['sources'] = items

    def step(name, command, *, env=None, budget=180):
        def invoke(work):
            try:
                return subprocess.run(command, cwd=store.build, env=env, text=True,
                                      capture_output=True, timeout=budget)
            except subprocess.TimeoutExpired as error:
                if command[0] == 'docker':
                    subprocess.run(['docker', 'rm', '-f', command[command.index('--name')+1]],
                                   capture_output=True, timeout=15)
                output = error.stdout or b''
                if isinstance(output, bytes): output = output.decode(errors='replace')
                return subprocess.CompletedProcess(command, 124, output, '\nTIMEOUT\n')
        result, work = store.step(name, command, executor=invoke)
        if result.returncode:
            raise RuntimeError(name+' failed: '+str(result.returncode))
        return result

    def container(program, args, stage):
        command = post.container_command(root, program, args, 'automx-'+tag+'-'+stage)
        command[command.index('-w')+1] = str(store.build)
        return command

    try:
        env = os.environ.copy(); env.update(AUTOMX_PG_WORK=str(store.build), AUTOMX_PG_GDS=str(gds))
        step('gds', ['/usr/bin/klayout', '-b', '-r', str(worker)], env=env)
        report['geometry'] = json.loads((store.build/'geometry.json').read_text())
        tcl = store.build/'repair_odb.tcl'
        tcl.write_text(f'read_db {{{odb}}}\nsource {{{recipe}}}\nautomx_ground_bridges\n'
                       f'write_db {{{store.build/"ground_repaired.odb"}}}\n'
                       f'write_def {{{store.build/"ground_repaired.def"}}}\nexit\n')
        step('odb', container('openroad', ['-exit', tcl], 'odb'))

        # Native streamout MAG has the exact saved routing geometry (XOR=0).
        # Resolve child cells through the same LEF/maglef views as native LVS;
        # this avoids parsing 500k DEF components again.
        clean = store.build/(TOP+'.mag')
        report['removed_child_path_hints'] = cached_mag(mag, clean)
        rc = store.build/'magicrc'
        rc.write_text(f'set ::env(PDK_ROOT) {{{pdk.parent}}}\nset ::env(MAGTYPE) maglef\n'
                      f'source {{{pdk/"libs.tech/magic/sky130A.magicrc"}}}\n')
        tcl = store.build/'extract.tcl'
        lines = ['crashbackups stop', 'drc off',
                 f'lef read {{{pdk/"libs.ref/sky130_fd_sc_hd/techlef/sky130_fd_sc_hd__nom.tlef"}}}']
        lines += [f'lef read {{{p}}}' for p in lefs]
        lines += [f'load {{{clean}}}', 'select top cell']
        for item in PLAN:
            lines += ['box '+' '.join(str(v)+'um' for v in item['rect_um']), 'paint metal4']
        lines += ['extract do local', 'extract no capacitance', 'extract no coupling',
                  'extract no resistance', 'extract no adjust', 'extract unique', 'extract',
                  'ext2spice lvs', f'ext2spice -o {{{store.build/"ground_repaired.lef.spice"}}}',
                  'puts AUTOMX_GROUND_EXTRACT_DONE', 'quit -noprompt']
        tcl.write_text('\n'.join(lines)+'\n')
        result = step('extract', container('magic', ['-dnull', '-noconsole', '-rcfile', rc, tcl], 'extract'),
                      budget=timeout_s)
        if 'AUTOMX_GROUND_EXTRACT_DONE' not in result.stdout:
            raise ValueError('incomplete extraction')
        netgen_log = store.build/'netgen.log'
        result = step('lvs', container('netgen', ['-batch', 'lvs',
                    str(store.build/'ground_repaired.lef.spice')+' '+TOP, str(netlist)+' '+TOP,
                    pdk/'libs.tech/netgen/sky130A_setup.tcl', netgen_log], 'lvs'))
        lvs.validate_netgen(netgen_log.read_text()+'\n'+result.stdout+result.stderr)
        for item in items: common._verified(root, item)
        report.update(status='GROUND_BRIDGES_MACRO_LVS_MATCH', native_macro_LVS='MATCH_UNIQUELY',
                      views={key: common._item(root, store.build/name) for key, name in
                             [('gds', 'ground_repaired.gds'), ('odb', 'ground_repaired.odb'),
                              ('def', 'ground_repaired.def'), ('lef_spice', 'ground_repaired.lef.spice')]},
                      lvs_log=common._item(root, netgen_log))
    except Exception as error:
        report.update(status='BLOCKED_GROUND_REPAIR', error=type(error).__name__+': '+str(error))
        raise
    finally:
        common.save_summary(store.folder/'summary.json', report)
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=ROOT)
    p.add_argument('--tag', default='ground_repair_srv_20261022_01')
    p.add_argument('--source-tag', default='mixed_wrapper_srv_20261022_04_impl_gds')
    p.add_argument('--timeout-s', type=int, default=600)
    p.add_argument('--run', action='store_true')
    a = p.parse_args()
    print(json.dumps(run(a.root, tag=a.tag, source_tag=a.source_tag,
                         timeout_s=a.timeout_s, execute=a.run), indent=2))
