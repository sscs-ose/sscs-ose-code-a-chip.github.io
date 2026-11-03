#!/usr/bin/env python3
"""Bounded DEF/LEF signal macro LVS on the routed antenna prototype.

No GDS/transistor/body/decap signoff inferred. PG-only cells omitted on both
sides for runtime; actual signal route geometry and all diodes are retained.
"""
from pathlib import Path
import argparse
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import flow2_integration_common as common
from scripts import run_flow2_wrapper_postroute as post
from scripts.run_flow2_wrapper_transistor_lvs import validate_netgen
from scripts.check_flow2_signal_lvs import signal_spice, signal_verilog


def candidate_source(data, diagnostic_only=False):
    if 'candidate_odb' in data:
        if (data.get('independent_drc_bytes') != 0 or
                data.get('preservation', {}).get('status') != 'PASS_PRESERVATION_ONLY' or
                (data.get('status') != 'ROUTED_PROTOTYPE_NO_NEW_CONNECTIVITY_FLAGS_ANTENNA_REMAINS'
                 and not (diagnostic_only and data.get('status') == 'BLOCKED_SAFE_SUBSET'
                          and data.get('connectivity_delta', {}).get('unmapped_candidate_iterms') == 0))):
            raise ValueError('independently clean preserved subset required')
        return data['candidate_odb'], data['ground_tag']
    if data.get('native_router_drc') != 0 or data.get('preservation_routed', {}).get('status') != 'PASS_PRESERVATION_ONLY':
        raise ValueError('measured zero-DRC preserved routed prototype required')
    return data['candidate_views']['routed'], data['source_tag']


def run(root, *, tag, candidate_tag, execute=False, signal_only=False, diagnostic_only=False):
    root = Path(root).resolve(); common.tag_ok(tag); common.tag_ok(candidate_tag)
    if (root/common.BASE/tag/'inputs.json').exists():
        raise FileExistsError('retain old evidence; use a fresh fast LVS tag')
    receipt = root/common.BASE/candidate_tag/'summary.json'
    data = json.loads(receipt.read_text())
    odb_item, ground_tag = candidate_source(data, diagnostic_only)
    odb = common._verified(root, odb_item)
    ground_path = root/common.BASE/ground_tag/'summary.json'
    ground = json.loads(ground_path.read_text()); native_tag = ground['source_tag']
    native = root/common.BUILD/native_tag/'design'
    config = native/'config.json'; settings = json.loads(config.read_text())
    pdk = post.native.notebook.DEFAULT_PDK/'sky130A'
    libs = [pdk/'libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib']
    libs += [Path(p) for p in settings.get('EXTRA_LIBS', [])]
    lefs = [Path(p) for p in settings['EXTRA_LEFS']]
    worker = root/'scripts/flow2_fast_macro_lvs_odb.py'
    normalizer = Path(signal_spice.__code__.co_filename)
    sources = [common._item(root, p) for p in (receipt, ground_path, odb, config, worker, Path(__file__), normalizer, *lefs)]
    report = {'format': 'automx-cim-fast-signal-macro-lvs-v1', 'tag': tag, 'candidate_tag': candidate_tag,
              'status': 'PREPARED', 'qualification': 'NOT_QUALIFIED', 'sources': sources, 'signal_only': signal_only,
              'diagnostic_only': diagnostic_only, 'candidate_acceptance_changed': False,
              'scope': 'DEF/LEF signal connectivity only, retaining all diodes; both sides omit PG-only instances. '
                       'No GDS binding, full transistor/body/tap/decap LVS or analog qualification.'}
    if signal_only:
        report['scope'] += ' Standard-cell formal PG/body ports omitted on BOTH sides; analog PG and rail-tied signal pins retained.'
    if not execute: return report
    store = common.Store(root, tag, {'sources': sources,
        'libs': [{'path': str(p), 'sha256': common._sha(p)} for p in libs],
        'image': post.native.notebook.DEFAULT_IMAGE})
    snapshot = store.build/'executed_host_sources'; snapshot.mkdir()
    for p in (worker, Path(__file__), normalizer):(snapshot/p.name).write_bytes(p.read_bytes())

    def step(name, program, args, budget):
        cmd = post.container_command(root, program, args, 'automx-'+tag+'-'+name)
        cmd[cmd.index('-w')+1] = str(store.build)
        def invoke(w):
            try: return subprocess.run(cmd, cwd=store.build, text=True, capture_output=True, timeout=budget)
            except subprocess.TimeoutExpired as error:
                subprocess.run(['docker', 'rm', '-f', cmd[cmd.index('--name')+1]], capture_output=True, timeout=15)
                text = error.stdout or b''
                if isinstance(text, bytes):text = text.decode(errors='replace')
                return subprocess.CompletedProcess(cmd, 124, text, '\nBOUNDED_TIMEOUT\n')
        result, _ = store.step(name, cmd, executor=invoke)
        report.setdefault('checks', {})[name] = {'returncode': result.returncode,
            'log': common._item(root, store.folder/(name+'.log'))}
        common.save_summary(store.folder/'summary.json', report)
        if result.returncode: raise RuntimeError(name+' failed: '+str(result.returncode))
        return result

    try:
        args = ['-exit', '-python', worker, '--odb', odb, '--work', store.build]
        for lib in libs:args += ['--lib', lib]
        result = step('export', 'openroad', args, 90)
        if 'AUTOMX_FAST_MACRO_EXPORT_DONE' not in result.stdout: raise ValueError('incomplete export')
        report['export'] = json.loads((store.build/'export.json').read_text())
        rc = store.build/'magicrc'
        rc.write_text(f'set ::env(PDK_ROOT) {{{pdk.parent}}}\nset ::env(MAGTYPE) maglef\n'
                      f'source {{{pdk/"libs.tech/magic/sky130A.magicrc"}}}\n')
        extract = store.build/'extract.tcl'
        lines = ['crashbackups stop', 'drc off',
                 f'lef read {{{pdk/"libs.ref/sky130_fd_sc_hd/techlef/sky130_fd_sc_hd__nom.tlef"}}}']
        lines += [f'lef read {{{p}}}' for p in lefs]
        lines += [f'def read {{{store.build/"signal_scope.def"}}} -noblockage -labels',
                  f'load {post.TOP}', 'select top cell', 'extract do local', 'extract no capacitance',
                  'extract no coupling', 'extract no resistance', 'extract no adjust', 'extract unique', 'extract',
                  'ext2spice lvs', f'ext2spice -o {{{store.build/"signal_scope.lef.spice"}}}',
                  'puts AUTOMX_FAST_MACRO_EXTRACT_DONE', 'quit -noprompt']
        extract.write_text('\n'.join(lines)+'\n')
        result = step('extract', 'magic', ['-dnull', '-noconsole', '-rcfile', rc, extract], 240)
        if 'AUTOMX_FAST_MACRO_EXTRACT_DONE' not in result.stdout: raise ValueError('incomplete physical extraction')
        physical, reference = store.build/'signal_scope.lef.spice', store.build/'signal_scope.v'
        if signal_only:
            ptext, scope = signal_spice(physical.read_text())
            vtext, count = signal_verilog(reference.read_text(), scope['removed_ports_by_master'])
            if not count or count != scope['standard_instances']:
                raise ValueError('all standard instances must survive normalization on both sides')
            physical, reference = store.build/'signal_only.spice', store.build/'signal_only.v'
            physical.write_text(ptext); reference.write_text(vtext)
            report['normalization'] = scope
        log = store.build/'netgen.log'
        result = step('lvs', 'netgen', ['-batch', 'lvs',
            str(physical)+' '+post.TOP, str(reference)+' '+post.TOP,
            pdk/'libs.tech/netgen/sky130A_setup.tcl', log], 120 if signal_only else 180)
        validate_netgen(log.read_text()+'\n'+result.stdout+result.stderr)
        report.update(status=('SIGNAL_ONLY_DEF_LEF_LVS_MATCH_NO_PG_BODY_QUALIFICATION' if signal_only
                              else 'SIGNAL_MACRO_LVS_MATCH_PG_ONLY_CELLS_OMITTED'),
                      physical_spice=common._item(root, physical), reference=common._item(root, reference),
                      lvs_log=common._item(root, log))
        for item in sources:common._verified(root, item)
    except Exception as error:
        report.update(status='BLOCKED_FAST_MACRO_LVS', error=type(error).__name__+': '+str(error))
    finally: common.save_summary(store.folder/'summary.json', report)
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=ROOT)
    p.add_argument('--tag', required=True)
    p.add_argument('--candidate-tag', default='antenna_eco_srv_20261022_08')
    p.add_argument('--run', action='store_true')
    p.add_argument('--signal-only', action='store_true')
    p.add_argument('--diagnostic-only', action='store_true', help='allow independently clean subset with unresolved ordering flags for measurement only')
    a = p.parse_args(); result = run(a.root, tag=a.tag, candidate_tag=a.candidate_tag,
                                    execute=a.run, signal_only=a.signal_only, diagnostic_only=a.diagnostic_only)
    print(json.dumps(result, indent=2))
    if a.run and result['status'].startswith('BLOCKED'): raise SystemExit(1)
