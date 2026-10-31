#!/usr/bin/env python3
"""Bounded TT schematic/RC pilot for the exact tap-repaired acquisition core."""
from pathlib import Path
import argparse
import json
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import flow2_integration_common as common
from scripts import flow2_live_spice as live
from scripts import flow2_waveforms as waves
from scripts import run_flow2_core_acquisition as core


def nominal_deck(model, netlist, variant, case):
    # This native PDK revision references an external mismatch-enable switch.
    # Nominal TT explicitly disables mismatch; it does not model offset/noise.
    text = core.pilot_deck(model, netlist, variant, case,
                           waveform=True, physical_bl_load=True)
    title, rest = text.split('\n', 1)
    return title+'\n.param mc_mm_switch=0\n'+rest


def source(root, source_tag):
    common.tag_ok(source_tag)
    receipt = root/common.BASE/source_tag/'tap_pex_summary.json'
    data = json.loads(receipt.read_text())
    if data.get('status') != 'CORE_TAP_DRC_LVS_RC_PEX_PASS':
        raise ValueError('tap-repaired full DRC/LVS/RC receipt required')
    views = {key: common._verified(root, data['views'][key])
             for key in ('gds', 'pex', 'schematic')}
    original = common._verified(root, data['source_gds'])
    if common._sha(original) != common._sha(views['gds']):
        raise ValueError('tap-repaired GDS identity differs')
    audit = core.acq._rc_audit(views['pex'])
    if not audit['nonzero_resistors'] or audit['unreferenced_capacitive_nodes']:
        raise ValueError('missing RC or unreferenced substrate')
    return receipt, data, views


def run(root, *, tag='core_tap_transient_srv_20261022_01',
        source_tag='core_tap_pex_srv_20261022_01', timeout_s=120, execute=False):
    root = Path(root).resolve()
    common.tag_ok(tag)
    if not 1 <= timeout_s <= 600:
        raise ValueError('per-job budget must be 1..600 seconds')
    receipt, extracted, views = source(root, source_tag)
    model = Path(extracted['pdk'])/'libs.tech/ngspice/sky130.lib.spice'
    simulator = shutil.which('ngspice')
    if not simulator or not model.is_file():
        raise FileNotFoundError('ngspice and matching native PDK models required')
    identity = {'sources': [common._item(root, p) for p in
        (receipt, *views.values(), Path(__file__), Path(core.__file__),
         Path(live.__file__), Path(waves.__file__))],
        'model': {'path': str(model), 'sha256': common._sha(model)},
        'simulator': {'path': simulator, 'sha256': common._sha(Path(simulator))},
        'timeout_s': timeout_s, 'physical_bl_load': True}
    report = {'format': 'automx-cim-core-tap-transient-v1', 'tag': tag,
        'source_tag': source_tag, 'status': 'PREPARED', 'qualification': 'NOT_QUALIFIED',
        'scope': 'TT core/acquisition pilot with physical MIM loads; no conditioner/ADC '
                 'or routed top loading, full transfer, noise, PVT or retention qualification',
        'inputs': identity, 'completed_sims': 0, 'jobs': [], 'new_ADC_conversions': 0}
    if not execute:
        return report
    store = common.Store(root, tag, identity)
    for case in ('zero', 'pair_a', 'pair_b'):
        for variant in ('schematic', 'pex'):
            name = 'tt_'+case+'_'+variant
            netlist = views['pex' if variant == 'pex' else 'schematic']
            deck = nominal_deck(model, netlist, variant, case)
            command = [simulator, '-b', 'pilot.spice']
            def simulate(work, content=deck):
                (work/'pilot.spice').write_text(content)
                return live.run(command, work, timeout_s)
            result, work = store.step(name, command, tcl=deck, executor=simulate)
            entry = {'case': case, 'variant': variant, 'returncode': result.returncode}
            report['jobs'].append(entry)
            try:
                if result.returncode:
                    raise RuntimeError('TIMEOUT' if result.returncode == 124 else 'simulator failed')
                entry.update(core.analyze(result.stdout, case))
                vectors = waves.read_raw(work/'core.raw')
                entry['scalar_waveform_agreement'] = core.scalar_waveform_agreement(
                    entry['raw_measurements'], vectors)
                entry['stage_diagnostic'] = core.analyze_waveform(vectors)
                entry['waveform'] = common._item(root, work/'core.raw')
                entry['status'] = 'MEASURED'
                report['completed_sims'] += 1
            except (ValueError, OSError, RuntimeError) as error:
                entry['status'], entry['reason'] = 'BLOCKED', str(error)
            report['status'] = 'RUNNING'
            common.save_summary(store.folder/'summary.json', report)
    complete = report['completed_sims'] == 6
    report['status'] = 'CORE_TAP_TT_PILOT_MEASURED' if complete else 'BLOCKED_CORE_TAP_TT_PILOT'
    pex = [j for j in report['jobs'] if j['variant'] == 'pex' and j['status'] == 'MEASURED']
    report['capture_budget_v'] = .0008
    report['all_rc_capture_budgets_met'] = (len(pex) == 3 and all(j['capture_budget_met'] for j in pex))
    if complete:
        report['maximum_schematic_pex_held_difference_v'] = max(
            abs(a-b) for i in range(0, 6, 2)
            for a, b in zip(report['jobs'][i]['differentials_v']['held'],
                            report['jobs'][i+1]['differentials_v']['held']))
    common.save_summary(store.folder/'summary.json', report)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--tag', default='core_tap_transient_srv_20261022_01')
    parser.add_argument('--source-tag', default='core_tap_pex_srv_20261022_01')
    parser.add_argument('--timeout-s', type=int, default=120)
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args()
    print(json.dumps(run(args.root, tag=args.tag, source_tag=args.source_tag,
                         timeout_s=args.timeout_s, execute=args.run), indent=2))
