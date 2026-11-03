"""Evidence gates for POR startup measurements. Apache-2.0.

The monitor is independent of SPICE .meas arithmetic. It does not diagnose
transistor defects or claim that a valid numerical result is physically true.
All times and voltages are SI. A missing event is never replaced by zero.
"""
from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib
import itertools
import json
import re
import numpy as np


@dataclass(frozen=True)
class Contract:
    window_start_s: float = 1.5e-3
    stop_s: float = 4e-3
    crossing_v: float = 0.9
    startup_min_s: float = 0.5e-3
    startup_max_s: float = 2e-3
    scalar_abs_tolerance_s: float = 1e-7

    def __post_init__(self):
        if not all(np.isfinite(v) for v in asdict(self).values()):
            raise ValueError('Contract must be finite')
        if not (0 <= self.window_start_s < self.stop_s and
                0 <= self.startup_min_s <= self.startup_max_s and
                self.scalar_abs_tolerance_s >= 0):
            raise ValueError('Invalid contract bounds')


def rising_crossings(t, v, level):
    """Linear interpolation of strict-below to at-or-above transitions.

    A trace starting above threshold has no observed rising event at t=0.
    This is a sampled-waveform oracle, not an analog noise/glitch filter.
    """
    t, v = np.asarray(t, dtype=float), np.asarray(v, dtype=float)
    if t.ndim != 1 or v.shape != t.shape or len(t) < 2:
        raise ValueError('Need matching one-dimensional traces')
    if not np.isfinite(t).all() or not np.isfinite(v).all():
        raise ValueError('Non-finite trace')
    if not np.all(np.diff(t) > 0):
        raise ValueError('Time must be strictly increasing')
    i = np.flatnonzero((v[:-1] < level) & (v[1:] >= level))
    return t[i] + (level-v[i]) * (t[i+1]-t[i]) / (v[i+1]-v[i])


def _assess_run(folder, contract=None):
    """Retain independent execution, measurement and specification states."""
    folder = Path(folder)
    resources = json.loads((folder/'resources.json').read_text())
    prov = json.loads((folder/'provenance.json').read_text())
    contract = contract if contract is not None else Contract(**prov.get('measurement_contract',{}))
    result = dict(run_id=folder.name, conditions=prov['conditions'],
                  model_family=prov.get('model_family', 'raw'),
                  cell_family=prov.get('cell_family','google'),
                  scenario=prov.get('scenario', 'original'),
                  execution='COMPLETE', measurement='UNASSESSED',
                  verdict='NOT_EVALUATED', reasons=[],
                  wall_s=resources['wall_seconds'],
                  peak_rss_mib=resources['peak_windows_wset']/2**20,
                  startup_s=None, exported_startup_s=None,
                  por_rises_s=[], osc_first_rise_in_window_s=None)
    if resources.get('termination_reason'):
        result.update(execution='INCOMPLETE', measurement='UNAVAILABLE')
        result['reasons'].append(resources['termination_reason'])
        return result
    if resources['exit_code'] != 0:
        result.update(execution='ERROR', measurement='UNAVAILABLE')
        result['reasons'].append('nonzero_exit_code')
        return result
    log = (folder/'stdout.log').read_text(errors='replace')
    if re.search(r'timestep too small|transient analysis aborted|simulation interrupted', log, re.I):
        result.update(execution='INCOMPLETE', measurement='UNAVAILABLE')
        result['reasons'].append('transient_aborted_in_log')
        return result
    if not (folder/'wave.tsv').exists():
        result.update(measurement='INVALID')
        result['reasons'].append('missing_waveform')
        return result
    try:
        a = np.loadtxt(folder/'wave.tsv', skiprows=1, ndmin=2)
        if a.shape[1] != 6 or not np.isfinite(a).all():
            raise ValueError('Expected six finite waveform columns')
        t = a[:, 0]
        osc = rising_crossings(t, a[:, 2], contract.crossing_v)
        por = rising_crossings(t, a[:, 3], contract.crossing_v)
    except (ValueError, OSError) as exc:
        result.update(measurement='INVALID')
        result['reasons'].append('malformed_waveform: '+str(exc))
        return result
    # SPICE can start output at a small positive time, but it must include
    # the start of the declared measurement window and reach analysis stop.
    if t[0] > contract.window_start_s or t[-1] < contract.stop_s-1e-12:
        result.update(execution='INCOMPLETE', measurement='UNAVAILABLE')
        result['reasons'].append('incomplete_time_coverage')
        return result
    result['por_rises_s'] = por.tolist()
    ow = osc[(osc >= contract.window_start_s) & (osc <= contract.stop_s)]
    pw = por[(por >= contract.window_start_s) & (por <= contract.stop_s)]
    if len(ow):
        result['osc_first_rise_in_window_s'] = float(ow[0])
    if not len(ow):
        result['reasons'].append('missing_osc_event_in_window')
    if not len(pw):
        result['reasons'].append('missing_por_event_in_window')
    if re.search(r'Error:\s+measure\s+(?:por_start|osc_start)\b', log, re.I):
        result['reasons'].append('required_measurement_error_in_log')
    try:
        if not (folder/'response_0.data').read_text().strip():
            raise ValueError('Empty scalar artifact')
        vals = np.loadtxt(folder/'response_0.data', ndmin=1).reshape(-1)
        if len(vals) != 2 or not np.isfinite(vals).all():
            raise ValueError('Expected two finite scalars')
        result['exported_startup_s'] = float(vals[1])
    except (ValueError, OSError):
        result['reasons'].append('invalid_scalar_artifact')
    if result['reasons']:
        result['measurement'] = 'INVALID'
        return result
    startup = float(pw[0]-ow[0])
    result['startup_s'] = startup
    if startup < 0:
        result['reasons'].append('por_precedes_osc_in_window')
    if abs(startup-result['exported_startup_s']) > contract.scalar_abs_tolerance_s:
        result['reasons'].append('scalar_waveform_disagreement')
    if result['reasons']:
        result['measurement'] = 'INVALID'
        return result
    result['measurement'] = 'VALID'
    result['verdict'] = ('PASS' if contract.startup_min_s <= startup <= contract.startup_max_s
                         else 'FAIL')
    return result


def assess_run(folder, contract=None, functional_contract=None):
    """Four dimensions. Legacy verdict aliases scalar_spec, never function.

    A functional contract must be supplied explicitly. Missing/failed execution
    evidence cannot be upgraded to functional PASS by a plausible saved trace.
    """
    result = _assess_run(folder, contract)
    result['scalar_spec'] = result['verdict']
    result['functional'] = dict(status='NOT_EVALUATED', reason='no_functional_contract_supplied')
    if functional_contract is not None:
        from functional import assess_function
        if result['execution'] != 'COMPLETE':
            result['functional'] = dict(status='INSUFFICIENT_EVIDENCE', reason='execution_not_complete')
        else:
            try:
                a = np.loadtxt(Path(folder)/'wave.tsv', skiprows=1, ndmin=2)
                if a.shape[1] != 6:
                    raise ValueError('Expected six columns')
                result['functional'] = assess_function(a[:,0], a[:,1], a[:,3], functional_contract)
            except (ValueError, OSError) as exc:
                result['functional'] = dict(status='INSUFFICIENT_EVIDENCE', reason=str(exc))
    return result


def coverage(rows, corners=('ff','tt','ss'), temperatures=('-40','27','85')):
    """Coverage is separate from passing available measurements."""
    expected = set(itertools.product(corners, temperatures))
    observed = {(r['conditions']['corner'], str(r['conditions']['temperature'])) for r in rows}
    return {'expected': len(expected), 'observed_expected': len(expected & observed),
            'missing': sorted(expected-observed), 'unexpected': sorted(observed-expected)}


def verify_manifest(root):
    root = Path(root).resolve()
    entries = json.loads((root/'MANIFEST.json').read_text())
    for relative, expected in entries.items():
        p = (root/relative).resolve()
        if not p.is_relative_to(root):
            raise ValueError('Manifest path outside project')
        actual = hashlib.sha256(p.read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError('Evidence hash mismatch: '+relative)
    return len(entries)
