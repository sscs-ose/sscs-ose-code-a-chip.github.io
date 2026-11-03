#!/usr/bin/env python3
"""Bounded clock-edge experiment on the verified tap-repaired RC core.

Changes only the testbench TRACK falling edge. Stops on the first failed
capture budget; no full ADC, calibration or physical qualification inferred.
"""
from pathlib import Path
import argparse
import json
import math
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import flow2_integration_common as common
from scripts import flow2_live_spice as live
from scripts import flow2_waveforms as waves
from scripts import run_flow2_core_tap_transient as pilot


def clock_deck(model, network, case, fall_ns):
    if not math.isfinite(fall_ns) or not .05 <= fall_ns <= 2:
        raise ValueError('TRACK fall must be 0.05..2ns, off before the 12ns sample')
    text = pilot.nominal_deck(model, network, 'pex', case)
    anchor = 'VTRACK TRACK 0 PWL(0 1.8 8n 1.8 8.05n 0 16n 0)'
    if text.count(anchor) != 1:
        raise ValueError('TRACK deck contract changed')
    return text.replace(anchor, 'VTRACK TRACK 0 PWL(0 1.8 8n 1.8 '+format(8+fall_ns, '.12g')+'n 0 16n 0)')


def run(root, *, tag, fall_ns=.5, timeout_s=120, execute=False):
    root = Path(root).resolve(); common.tag_ok(tag)
    if not 1 <= timeout_s <= 180:
        raise ValueError('bounded simulation budget required')
    if (root/common.BASE/tag/'inputs.json').exists():
        raise FileExistsError('fresh clock experiment tag required')
    receipt, data, views = pilot.source(root, 'core_tap_pex_srv_20261022_01')
    model = Path(data['pdk'])/'libs.tech/ngspice/sky130.lib.spice'
    simulator = shutil.which('ngspice')
    if not simulator: raise FileNotFoundError('ngspice required')
    # Validate the stimulus before launching anything.
    clock_deck(model, views['pex'], 'zero', fall_ns)
    identity = {'sources': [common._item(root, p) for p in
        (receipt, *views.values(), Path(__file__), Path(pilot.__file__),
         Path(pilot.core.__file__), Path(live.__file__), Path(waves.__file__))],
        'model': {'path': str(model), 'sha256': common._sha(model)},
        'simulator': {'path': simulator, 'sha256': common._sha(Path(simulator))},
        'fall_ns': fall_ns, 'timeout_s': timeout_s}
    report = {'format': 'automx-cim-core-clock-probe-v1', 'tag': tag, 'inputs': identity,
              'status': 'PREPARED', 'qualification': 'NOT_QUALIFIED', 'jobs': [],
              'capture_budget_v': .0008, 'new_ADC_conversions': 0,
              'scope': 'Exact tap-repaired RC core, TT, physical MIM loads, TRACK fall sweep; '
                       'no conditioner/ADC/routed-top load, holdout, noise or PVT qualification.'}
    if not execute: return report
    store = common.Store(root, tag, identity)
    frozen = store.build/'executed_host_sources'; frozen.mkdir()
    for p in (Path(__file__), Path(pilot.__file__), Path(pilot.core.__file__)):
        (frozen/p.name).write_bytes(p.read_bytes())
    try:
        for case in ('zero', 'pair_a', 'pair_b'):
            deck = clock_deck(model, views['pex'], case, fall_ns)
            command = [simulator, '-b', 'pilot.spice']
            def simulate(work):
                (work/'pilot.spice').write_text(deck)
                return live.run(command, work, timeout_s)
            result, work = store.step(case, command, tcl=deck, executor=simulate)
            entry = {'case': case, 'returncode': result.returncode}
            report['jobs'].append(entry)
            if result.returncode: raise ValueError('bounded simulation failed: '+str(result.returncode))
            entry.update(pilot.core.analyze(result.stdout, case))
            raw = waves.read_raw(work/'core.raw')
            entry['scalar_waveform_agreement'] = pilot.core.scalar_waveform_agreement(entry['raw_measurements'], raw)
            entry['waveform'] = common._item(root, work/'core.raw')
            entry['status'] = 'MEASURED'
            common.save_summary(store.folder/'summary.json', report)
            if not entry['capture_budget_met']:
                report['status'] = 'CLOCK_PROBE_CAPTURE_BUDGET_FAIL'
                break
        else:
            report['status'] = 'CLOCK_PROBE_THREE_RC_CAPTURE_CASES_PASS_NO_SYSTEM_QUALIFICATION'
        for item in identity['sources']: common._verified(root, item)
    except Exception as error:
        report.update(status='BLOCKED_CLOCK_PROBE', error=type(error).__name__+': '+str(error))
    finally:
        common.save_summary(store.folder/'summary.json', report)
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=ROOT)
    p.add_argument('--tag', required=True)
    p.add_argument('--fall-ns', type=float, default=.5)
    p.add_argument('--timeout-s', type=int, default=120)
    p.add_argument('--run', action='store_true')
    a = p.parse_args(); result = run(a.root, tag=a.tag, fall_ns=a.fall_ns,
                                    timeout_s=a.timeout_s, execute=a.run)
    print(json.dumps(result, indent=2))
    if a.run and result['status'] != 'CLOCK_PROBE_THREE_RC_CAPTURE_CASES_PASS_NO_SYSTEM_QUALIFICATION':
        raise SystemExit(1)
