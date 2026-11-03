#!/usr/bin/env python3
"""Bounded TT check: measured conditioner decks plus the routed wrapper load.

Reuses the four hash-verified TT PEX conditioner decks (column 0..3, -100/0/
+50/+100 mV) and adds, on AINP/AINN/BIAS_MON, the total OpenRCX SPEF net
capacitance (coupling grounded, wire R dropped) and the Liberty DIODE pin
capacitance of every routed antenna diode. The ideal 2-pF ADC stand-in loads
remain. This is a TT diagnostic, not coupled ADC/readout qualification.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shutil
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import flow2_integration_common as common
from scripts import flow2_live_spice as live
from scripts import flow2_waveforms as waves
from scripts import run_flow2_conditioner as conditioner
from scripts import flow2_adc_c_only as reduction

CONDITION = 'mixed_wrapper_20261020_01_cond'
CASES = ('tt_pex_0', 'tt_pex_1', 'tt_pex_2', 'tt_pex_3')
NETS = ('AINP', 'AINN', 'BIAS_MON')
LIBERTY = Path('/home/nam/.volare_openlane_30ee138_nam/sky130A/libs.ref/sky130_fd_sc_hd/lib/'
               'sky130_fd_sc_hd__tt_025C_1v80.lib')
SETTLE_BAND_V = 1e-4


def proof(root, path):
    return {'path': str(Path(path).resolve().relative_to(root)), 'sha256': common._sha(path)}


def diode_pin_capacitance_pf(liberty):
    text = liberty.read_text()
    unit = re.search(r'capacitive_load_unit\s*\(\s*([0-9.]+)\s*,\s*"pf"\s*\)', text)
    if not unit or float(unit[1]) != 1.0:
        raise ValueError('Liberty capacitance unit must be 1 pF')
    start = text.index('cell ("sky130_fd_sc_hd__diode_2")')
    pin = text.index('pin ("DIODE")', start)
    return float(re.search(r'\bcapacitance\s*:\s*([0-9.eE+-]+)\s*;', text[pin:pin + 2000])[1])


def spef_loads(path, nets=NETS):
    """Return total/ground/coupling C (pF), R (ohm) and attached cells per net."""
    wanted, ids, loads, current, section = set(nets), {}, {}, None, None
    with Path(path).open() as handle:
        for line in handle:
            if line.startswith('*C_UNIT') and line.split()[1:] != ['1', 'PF']:
                raise ValueError('SPEF capacitance unit must be 1 PF')
            if line.startswith('*D_NET'):
                _, name, total = line.split()[:3]
                net = ids.get(name, name if name in wanted else None)
                current = net
                if net:
                    loads[net] = {'total_pf': float(total), 'ground_pf': 0., 'coupling_pf': 0.,
                                  'resistance_ohm': 0., 'cells': {}}
                section = None
                continue
            if current is None:
                parts = line.split()
                if len(parts) == 2 and parts[0].startswith('*') and parts[1] in wanted:
                    ids[parts[0]] = parts[1]
                continue
            parts = line.split()
            if not parts:
                continue
            if parts[0] in ('*CONN', '*CAP', '*RES'):
                section = parts[0]
            elif parts[0] == '*END':
                current = None
            elif section == '*CONN' and parts[0] == '*I' and '*D' in parts:
                cell = parts[parts.index('*D') + 1]
                loads[current]['cells'][cell] = loads[current]['cells'].get(cell, 0) + 1
            elif section == '*CAP':
                key = 'ground_pf' if len(parts) == 3 else 'coupling_pf'
                loads[current][key] += float(parts[-1])
            elif section == '*RES':
                loads[current]['resistance_ohm'] += float(parts[-1])
    missing = wanted - set(loads)
    if missing:
        raise ValueError('SPEF lacks nets: ' + ', '.join(sorted(missing)))
    return loads


def loaded_deck(text, loads, diode_pf):
    anchor = 'CLOADN AINN 0 2p\n'
    if text.count(anchor) != 1:
        raise ValueError('unexpected conditioner bench load contract')
    lines = ['* Routed wrapper load: SPEF total C to ground, Liberty DIODE pin C per antenna diode.']
    for net in NETS:
        diodes = sum(n for cell, n in loads[net]['cells'].items() if cell.startswith('sky130_fd_sc_hd__diode'))
        lines.append(f'CWIRE_{net} {net} 0 {loads[net]["total_pf"]:.9g}p')
        if diodes:
            lines.append(f'CDIODE_{net} {net} 0 {diodes * diode_pf:.9g}p')
    return text.replace(anchor, anchor + '\n'.join(lines) + '\n', 1)


def settle_time_s(raw, band=SETTLE_BAND_V):
    v = waves.read_raw(raw)
    t = np.asarray(v['time'], float)
    diff = np.asarray(v['v(ainp)'], float) - np.asarray(v['v(ainn)'], float)
    final = waves.sample(v, 'v(AINP)', 450e-9) - waves.sample(v, 'v(AINN)', 450e-9)
    outside = np.flatnonzero((np.abs(diff - final) > band) & (t <= 450e-9))
    return float(t[outside[-1]]) if len(outside) else 0.


def c_only_network(text):
    """Contract wire R in the flat extracted block; keep its port adapter."""
    from scripts.run_flow2_wrapper_transistor_lvs import definitions
    blocks = definitions(text)
    raw = conditioner.design.COND.lower() + '_raw'
    reduced, proof = reduction.reduce_text(blocks.pop(raw))
    proof.pop('node_aliases', None)
    return reduced + '\n' + '\n'.join(blocks.values()) + '\n', proof


def run(root, *, gds_tag, spef, tag, execute=False, timeout_s=240, network_mode='rc-pex'):
    root = Path(root).resolve()
    common.tag_ok(tag)
    if network_mode not in ('rc-pex', 'c-only', 'schematic'):
        raise ValueError('unknown network mode')
    spef = Path(spef).resolve()
    if not spef.is_relative_to(root / common.BUILD / gds_tag):
        raise ValueError('SPEF must belong to the named GDS child run')
    loads = spef_loads(spef)
    diode_pf = diode_pin_capacitance_pf(LIBERTY)
    report = {'format': 'automx-cim-wrapper-loaded-conditioner-v1', 'tag': tag,
              'timestamp_utc': datetime.now(timezone.utc).isoformat(),
              'status': 'PREPARED', 'qualification': 'NOT_QUALIFIED', 'new_ADC_conversions': 0,
              'gds_tag': gds_tag, 'spef': proof(root, spef), 'net_loads_pf': loads,
              'network_mode': network_mode,
              'liberty': {'path': str(LIBERTY), 'sha256': common._sha(LIBERTY),
                          'diode_2_DIODE_pin_pf': diode_pf},
              'scope': 'TT 25 C 1.8 V, driven 1.7-V held inputs, original 2-pF ADC stand-ins kept; '
                       'routed C lumped to ground (coupling grounded, wire R dropped); '
                       'no ADC kickback, held-node routing load, noise or PVT',
              'cases': []}
    if not execute:
        return report
    work = root / common.BUILD / tag
    work.mkdir(parents=True, exist_ok=False)
    tool = shutil.which('ngspice')
    try:
        network = None
        if network_mode == 'c-only':
            source = root / common.PHYSICAL / CONDITION / (conditioner.design.COND + '.pex.spice')
            # Verify the network against the measured electrical receipt.
            saved = json.loads((root / common.BUILD / CONDITION / CASES[0] / 'receipt.json').read_text())
            if common._sha(source) != saved['inputs']['network']:
                raise ValueError('measured conditioner network changed')
            text, contraction = c_only_network(source.read_text())
            network = work / 'conditioner.c_only.spice'
            network.write_text(text)
            report['network_reduction'] = contraction
            report['derived_network'] = proof(root, network)
            report['scope'] += '; conditioner extracted wire R contracted, NOT distributed RC timing'
        elif network_mode == 'schematic':
            report['scope'] += '; schematic conditioner with routed interface C, NOT internal PEX timing'
        for name in CASES:
            if network_mode == 'schematic':
                name = name.replace('tt_pex_', 'tt_schematic_')
            base = root / common.BUILD / CONDITION / name
            saved = json.loads((base / 'receipt.json').read_text())
            if common._sha(base / 'bench.spice') != saved['inputs']['deck']:
                raise ValueError(name + ': measured deck changed')
            if tool is None or common._sha(Path(tool)) != saved['inputs']['tool_binary']:
                raise ValueError('same measured conditioner ngspice binary required')
            reference_raw = common._verified(root, saved['raw'])
            case = work / name
            case.mkdir()
            deck = case / 'bench.spice'
            text = (base / 'bench.spice').read_text()
            if network is not None:
                original = root / common.PHYSICAL / CONDITION / (conditioner.design.COND + '.pex.spice')
                if text.count(str(original)) != 1:
                    raise ValueError('conditioner include contract changed')
                text = text.replace(str(original), str(network))
            deck.write_text(loaded_deck(text, loads, diode_pf))
            begun = time.monotonic()
            result = live.run([tool, '-b', 'bench.spice'], case, timeout_s, poll_s=.5, heartbeat_s=30.)
            item = {'case': name, 'input_diff_v': saved['input_diff_v'],
                    'selected_column': saved['selected_column'], 'deck': proof(root, deck),
                    'source_deck': proof(root, base / 'bench.spice'), 'returncode': result.returncode,
                    'wall_s': time.monotonic() - begun, 'log': proof(root, case / 'ngspice.live.log'),
                    'status': 'INCOMPLETE_NATIVE_PROBE',
                    'unloaded': {k: saved[k] for k in ('output_diff_v', 'output_cm_v', 'supply_current_a')}}
            report['cases'].append(item)
            item['unloaded']['settle_100uV_s'] = settle_time_s(reference_raw)
            raw = case / 'conditioner.raw'
            if result.returncode == 0 and raw.is_file():
                item['raw'] = proof(root, raw)
                item['loaded'] = conditioner.analyze_point(raw)
                item['loaded']['settle_100uV_s'] = settle_time_s(raw)
                item['delta_output_diff_v'] = item['loaded']['output_diff_v'] - item['unloaded']['output_diff_v']
                item['delta_output_cm_v'] = item['loaded']['output_cm_v'] - item['unloaded']['output_cm_v']
                item['status'] = 'MEASURED_TT_ROUTED_LOAD_POINT'
            (case / 'receipt.json').write_text(json.dumps(item, indent=2) + '\n')
            print(name, item['status'], flush=True)
            if item['status'] != 'MEASURED_TT_ROUTED_LOAD_POINT':
                break
        done = [c for c in report['cases'] if c['status'] == 'MEASURED_TT_ROUTED_LOAD_POINT']
        if len(done) == len(CASES):
            by = {c['input_diff_v']: c for c in done}
            gain = lambda key: (by[.1][key]['output_diff_v'] - by[-.1][key]['output_diff_v']) / .2
            report['gain'] = {'unloaded': gain('unloaded'), 'loaded': gain('loaded')}
            report['max_abs_delta_output_diff_v'] = max(abs(c['delta_output_diff_v']) for c in done)
            report['status'] = 'MEASURED_TT_ROUTED_LOAD_DIAGNOSTIC'
        else:
            report['status'] = 'PENDING_NATIVE_PROBE_EVIDENCE'
    except Exception as error:
        report.update(status='BLOCKED_LOADED_CONDITIONER', error=f'{type(error).__name__}: {error}')
        raise
    finally:
        (work / 'summary.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=ROOT)
    p.add_argument('--gds-tag', required=True)
    p.add_argument('--spef', type=Path, required=True)
    p.add_argument('--tag', required=True)
    p.add_argument('--timeout-s', type=int, default=240)
    p.add_argument('--run', action='store_true')
    p.add_argument('--network-mode', choices=('rc-pex', 'c-only', 'schematic'), default='rc-pex')
    a = p.parse_args()
    if not 1 <= a.timeout_s <= 240:
        p.error('native budget must be between 1 and 240 seconds per case')
    report = run(a.root, gds_tag=a.gds_tag, spef=a.spef, tag=a.tag, execute=a.run,
                 timeout_s=a.timeout_s, network_mode=a.network_mode)
    print(json.dumps({k: report.get(k) for k in ('status', 'gain', 'max_abs_delta_output_diff_v',
                                                  'net_loads_pf', 'qualification')}, indent=2))


if __name__ == '__main__':
    main()
