"""Read full local transients; export compact, preliminary review evidence."""
import hashlib
import difflib
import json
from pathlib import Path
import re
import shutil

import numpy as np

DEST = Path(__file__).resolve().parent
REPO = DEST.parents[3]
LOCAL = REPO / 'examples/microrobot/local_runs/clock_layout/contact_escape_v2'
CASES = ['schematic_50ns', 'schematic_25ns', 'extracted_50ns', 'extracted_25ns']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def crossing_times(t, x, threshold, rising=True):
    y = x - threshold
    indices = np.flatnonzero((y[:-1] < 0) & (y[1:] >= 0) if rising else
                             (y[:-1] >= 0) & (y[1:] < 0))
    return t[indices] - y[indices] * np.diff(t)[indices] / np.diff(y)[indices]


def frequency(edges):
    return float(1 / np.mean(np.diff(edges))) if len(edges) > 1 else None


def audit_case(name):
    src = LOCAL / name
    export = DEST / name
    export.mkdir(exist_ok=True)
    files = ['clock.spice', '.spiceinit', 'receiver_cells.spice', 'ngspice.log',
             'metrics.json', 'failure.json', 'execution.log', 'execution.json']
    for file in files:
        if (src / file).is_file():
            shutil.copy2(src / file, export / file)
    record = {'source': str(src.relative_to(REPO)), 'sha256': {
        p.name: sha(p) for p in src.iterdir() if p.is_file()}}
    if not (src / 'clock.dat').is_file():
        record['audit_failure'] = 'No full transient is available'
        return record
    data = np.loadtxt(src / 'clock.dat', skiprows=1)
    t, vdd, clk, bn, bp, analog, digital, q = data.T
    finite = bool(np.isfinite(data).all())
    record.update(rows=len(data), columns=data.shape[1], all_finite=finite,
                  first_time_s=float(t[0]), actual_stop_s=float(t[-1]),
                  requested_stop_s=.004,
                  nondecreasing_time=bool(np.all(np.diff(t) >= 0)),
                  max_observed_step_s=float(np.max(np.diff(t))),
                  full_completion=bool(finite and t[0] == 0 and
                      np.all(np.diff(t) >= 0) and
                      np.isclose(t[-1], .004, rtol=1e-8, atol=1e-12)))
    select = t > .0024
    # Exact boundary used by clock_case's reported metrics; no new simulation.
    record['steady_window_s'] = [float(t[select][0]), float(t[-1])]
    record['rail_V'] = {'minimum': float(vdd[select].min()),
                        'sample_mean': float(vdd[select].mean()),
                        'time_average': float(np.trapezoid(vdd[select], t[select]) / np.ptp(t[select])),
                        'maximum': float(vdd[select].max())}
    record['clock_range_V'] = [float(clk[select].min()), float(clk[select].max())]
    record['receiver_q_range_V'] = [float(q[select].min()), float(q[select].max())]
    record['power_W'] = {key: float(np.trapezoid((vdd * current)[select],
                       t[select]) / np.ptp(t[select])) for key, current in
                       [('whole_clock_and_first_ff', analog + digital),
                        ('analog_clock', analog), ('first_ff_and_feedback', digital)]}
    rise = crossing_times(t, clk, vdd / 2)
    qrise = crossing_times(t, q, vdd / 2)
    qfall = crossing_times(t, q, vdd / 2, False)
    # Startup crossings near zero supply are numerical/noise-sensitive. For an
    # offline sustained-edge audit use only >=0.4 ms, leaving startup visible.
    stable = rise[rise >= .0004]
    qr = qrise[qrise >= .0004]
    qf = qfall[qfall >= .0004]
    sr = rise[rise > t[select][0]]
    sqr = qrise[qrise > t[select][0]]
    sqf = qfall[qfall > t[select][0]]
    record['edges'] = {
        'method': 'Linear interpolation of signal minus instantaneous vdd/2',
        'all_clock_rises_s': rise.tolist(), 'all_q_rises_s': qrise.tolist(),
        'all_q_falls_s': qfall.tolist(),
        'sustained_audit_start_s': .0004,
        'sustained_clock_rises_s': stable.tolist(),
        'sustained_q_rises_s': qr.tolist(), 'sustained_q_falls_s': qf.tolist(),
        'steady_clock_rises_s': sr.tolist(), 'steady_q_rises_s': sqr.tolist(),
        'steady_q_falls_s': sqf.tolist(),
        'steady_clock_frequency_Hz': frequency(sr),
        'steady_q_frequency_from_one_or_more_periods_Hz': frequency(sqr),
        'sustained_clock_frequency_Hz': frequency(stable),
        'sustained_q_frequency_Hz': frequency(qr),
        'sustained_q_to_clock_frequency_ratio':
            frequency(qr) / frequency(stable) if len(qr) > 1 and len(stable) > 1 else None,
        'bench_q_requires_rise_count': 3,
        'steady_q_rise_count': len(sqr),
        'clock_edges_between_successive_q_rises':
            [int(np.sum((stable > a) & (stable <= b))) for a, b in zip(qr[:-1], qr[1:])],
        'startup_limitation': 'Near-zero-supply crossings are retained in all_* arrays and excluded from sustained audit',
    }
    qedges = np.sort(np.r_[qr, qf])
    if len(qedges) and len(stable):
        record['edges']['q_transition_nearest_clock_rise_offset_s'] = [
            float(edge - stable[np.argmin(abs(stable - edge))]) for edge in qedges]
        record['edges']['offset_limitation'] = ('Signed threshold-crossing offsets are not propagation-delay characterization; '
                                               'supply and slow input slew move thresholds')
    log = (src / 'ngspice.log').read_text()
    record['log_abort_markers'] = [s for s in ['simulation(s) aborted', 'doanalyses:',
                                  'timestep too small'] if s in log.lower()]
    record['log_warnings'] = sorted(set(s.strip() for s in log.splitlines()
                                      if 'warning' in s.lower()))
    record['bench_metrics'] = json.loads((src / 'metrics.json').read_text()) if (src / 'metrics.json').exists() else None
    return record


def capacitance_audit():
    # Collapse only explicit resistor-connected nodes for offline accounting.
    # This does not replace distributed RC with a different simulation circuit.
    text = (LOCAL / 'clock_rc.spice').read_text()
    parent = {}

    def find(a):
        parent.setdefault(a, a)
        if parent[a] != a:
            parent[a] = find(parent[a])
        return parent[a]

    for line in text.splitlines():
        fields = line.split()
        if fields and fields[0].startswith('R'):
            parent[find(fields[1])] = find(fields[2])
    labels = {'a': 'Xc1.C1', 'b': 'Xc2.C1', 'c': 'Xc3.C1',
              'd': 'Xc4.C1', 'raw': 'X1_Xpi.G', 'buffered': 'Xbp1.D',
              'clk': 'clk', 'bias_n': 'bias_n', 'bias_p': 'bias_p',
              'vdd': 'vdd', 'vss': 'vss'}
    # Roots are resistor components, linked to the cap-only netlist names.
    roots = {find(node): label for label, node in labels.items()}
    caps = []
    for line in text.splitlines():
        fields = line.split()
        if not fields or not fields[0].startswith('C'):
            continue
        value = fields[3]
        match = re.fullmatch(r'([0-9.eE+\-]+)([fpnu]?)', value)
        assert match, value
        scale = {'': 1., 'f': 1e-15, 'p': 1e-12, 'n': 1e-9, 'u': 1e-6}[match[2]]
        a, b = [roots.get(find(node), re.sub(r'\.[tn]\d+$', '', node)) for node in fields[1:3]]
        caps.append((fields[0], a, b, float(match[1]) * scale))
    result = {'method': 'Sum explicit extracted C incident on resistor-connected logical net',
              'limitations': [
                  'Incident capacitance is not effective switching capacitance; coupling depends on other-node motion',
                  'Explicit PDK MIM devices and transistor model capacitances are excluded from these parasitic C sums',
                  'Mappings follow extracted cap-only FET/MIM connectivity, not physical rerouting',
                  'No causal attribution of frequency loss from this accounting alone'],
              'resistor_count': sum(line.startswith('R') for line in text.splitlines()),
              'capacitor_count': len(caps), 'logical_nets': {}}
    for label, node in labels.items():
        incident = [(name, b if a == label else a, value) for name, a, b, value in caps
                    if a == label or b == label]
        by_other = {}
        for _, other, value in incident:
            by_other[other] = by_other.get(other, 0.) + value / 1e-15
        result['logical_nets'][label] = {
            'extracted_anchor': node,
            'total_incident_parasitic_fF': sum(v for _, _, v in incident) / 1e-15,
            'by_other_logical_net_fF': dict(sorted(by_other.items(), key=lambda p: -p[1]))}
    return result


def main():
    records = {name: audit_case(name) for name in CASES}
    convergence = {}
    for kind in ['schematic', 'extracted']:
        coarse, fine = [records[f'{kind}_{step}ns'] for step in [50, 25]]
        comparison = {}
        for key in ['frequency_Hz', 'mean_power_W', 'analog_clock_power_W',
                    'first_divider_stage_power_W', 'steady_supply_V']:
            a, b = [r['bench_metrics'][key] for r in [coarse, fine]]
            comparison[key] = {'50ns': a, '25ns': b,
                               'relative_change_vs_25ns': abs(a-b)/abs(b),
                               'below_1_percent': bool(abs(a-b)/abs(b) < .01)}
        # Comments and transient line are the only allowed deck differences.
        normalize = lambda name: '\n'.join(line for line in (LOCAL/name/'clock.spice').read_text().splitlines()
                                             if not line.startswith('*') and not line.startswith('tran '))
        comparison['decks_identical_except_comments_and_tran'] = normalize(kind+'_50ns') == normalize(kind+'_25ns')
        decks = [(LOCAL/f'{kind}_{step}ns'/'clock.spice').read_text().splitlines()
                 for step in [50,25]]
        tran = [[line for line in deck if line.startswith('tran ')] for deck in decks]
        comparison['tran_commands_50ns_25ns'] = tran
        comparison['tran_stop_and_start_identical'] = tran[0][0].split()[2:4] == tran[1][0].split()[2:4]
        comparison['deck_diff'] = list(difflib.unified_diff(*decks, fromfile=f'{kind}_50ns/clock.spice',
                                                         tofile=f'{kind}_25ns/clock.spice', lineterm=''))
        comparison['primary_frequency_and_whole_power_below_1_percent'] = all(
            comparison[k]['below_1_percent'] for k in ['frequency_Hz', 'mean_power_W'])
        convergence[kind] = comparison
    provenance = DEST / 'provenance'
    provenance.mkdir(exist_ok=True)
    files = ['physical_clock.spice', 'clock_rc.spice', 'clock_capacitance.spice', 'report.json',
             'drc.txt', 'placement_drc.txt', 'lvs.json', 'lvs.txt', 'lvs.log',
             'negative_control_lvs.json', 'negative_control_lvs.txt', 'extract_rc.log',
             'extract_rc.tcl', 'microrobot_clock.mag', 'gds_roundtrip/drc.txt',
             'gds_roundtrip/lvs.json', 'gds_roundtrip/lvs.txt']
    for file in files:
        source = LOCAL / file
        if source.is_file():
            target = provenance / file
            target.parent.mkdir(exist_ok=True, parents=True)
            shutil.copy2(source, target)
    for source in [REPO/'examples/microrobot/circuits/starved_clock.spice',
                   REPO/'examples/microrobot/results/published/pv_fit.json',
                   REPO/'examples/microrobot/local_runs/clock_layout/run_electrical.py']:
        shutil.copy2(source, provenance / source.name)
    report = {'status': 'PRELIMINARY ELECTRICAL EVIDENCE; NOT ACCEPTED; awaiting Astra review',
              'scope': 'Unchanged canonical 29-FET/7-MIM prototype, matched finite-PV cold startup at 4ms',
              'cases': records, 'timestep_comparison': convergence,
              'capacitance': capacitance_audit(),
              'limitations': [
                  '50ns bench pass is false for extracted case because only 2 Q rises fall in the fixed steady window; this alone does not show physical divider failure',
                  'PV model assumes identical current density scaled from measured cell to 150um^2 per cell, three series cells; chosen 2pF storage and 2fF output load',
                  'Only tt/26.85C; no PVT, mismatch, whole divider, POR, driver or footprint closure',
                  'Separate bias current was not measured; whole macro and first-FF/feedback power were measured',
                  'Existing physical report electrical_executed=false is a historical pre-electrical report, preserved unchanged',
                  'No fabrication/submission/publish authorization or electrical acceptance is implied'],
              'raw_data_policy': 'Full clock.dat remains local only; report contains hashes, decks, logs and compact metrics; no PDF or raw transient export'}
    (DEST/'review_metrics.json').write_text(json.dumps(report, indent=2)+'\n')
    manifest = {str(p.relative_to(DEST)): sha(p) for p in sorted(DEST.rglob('*'))
                if p.is_file() and p.name != 'sha256.json' and '__pycache__' not in p.parts}
    (DEST/'sha256.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(json.dumps({'completion': {k: v['full_completion'] for k,v in records.items()},
                      'comparison': convergence,
                      'capacitance_fF': {k: v['total_incident_parasitic_fF']
                                         for k,v in report['capacitance']['logical_nets'].items()}}, indent=2))


if __name__ == '__main__':
    main()
