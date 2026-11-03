"""Finite waveform contracts with an explicit prior-state coverage check.

SPDX-License-Identifier: Apache-2.0
No topology, SPICE executable or file-column order is assumed here.
"""
from dataclasses import dataclass
import math
import numpy as np


@dataclass(frozen=True)
class Band:
    signal: str
    lower: float | None = None
    upper: float | None = None


@dataclass(frozen=True)
class Window:
    name: str
    start_s: float
    ramp_end_s: float
    stop_s: float


def waveform(time_s, signals):
    t = np.asarray(time_s, dtype=float)
    if t.ndim != 1 or len(t) < 3 or not np.isfinite(t).all() or not np.all(np.diff(t) > 0):
        raise ValueError('Time must be finite, strictly increasing and contain at least three samples')
    values = {}
    for name, value in signals.items():
        value = np.asarray(value, dtype=float)
        if value.shape != t.shape or not np.isfinite(value).all():
            raise ValueError('Missing or nonfinite vector: ' + name)
        values[name] = value
    return t, values


def margins(signals, bands):
    if not bands:
        raise ValueError('An empty state contract cannot qualify a waveform')
    result = []
    for band in bands:
        if band.signal not in signals or (band.lower is None and band.upper is None):
            raise ValueError('Undeclared signal or empty band')
        if any(x is not None and (isinstance(x, bool) or not math.isfinite(x)) for x in (band.lower, band.upper)):
            raise ValueError('Band limits must be finite')
        if band.lower is not None and band.upper is not None and band.lower > band.upper:
            raise ValueError('Reversed band')
        if band.lower is not None:
            result.append(signals[band.signal] - band.lower)
        if band.upper is not None:
            result.append(band.upper - signals[band.signal])
    return result


def segment(t, values, start, stop):
    if not math.isfinite(start) or not math.isfinite(stop) or not t[0] <= start < stop <= t[-1]:
        raise ValueError('The requested observation interval is not covered')
    tw = np.unique(np.r_[start, t[(t > start) & (t < stop)], stop])
    return tw, {name: np.interp(tw, t, v) for name, v in values.items()}


def last_entry(t, margin):
    """Final entry into a closed band, using piecewise-linear interpolation."""
    if margin[-1] < 0:
        return None
    bad = np.flatnonzero(margin < 0)
    if not len(bad):
        return float(t[0])
    i = int(bad[-1])
    return float(t[i] + (t[i + 1] - t[i]) * (-margin[i]) / (margin[i + 1] - margin[i]))


def accepts(t, values, bands, deadline_s, hold_s):
    if not math.isfinite(deadline_s) or not math.isfinite(hold_s) or hold_s <= 0:
        raise ValueError('Finite deadline and positive hold required')
    if deadline_s < t[0] or deadline_s + hold_s > t[-1] + 1e-12:
        raise ValueError('The complete deadline and hold interval must be observed')
    # Find each bound crossing separately. Interpolating a sampled minimum can
    # move a crossing when the limiting bound changes between samples.
    entries = [last_entry(t, m) for m in margins(values, bands)]
    ready = None if any(x is None for x in entries) else max(entries)
    passed = ready is not None and ready <= deadline_s + 1e-12 and t[-1] - ready >= hold_s - 1e-12
    return dict(pass_contract=bool(passed), final_entry_s=ready)


def evaluate(time_s, signals, *, supply_points, windows, state_bands,
             release_bands, state_delay_s, release_delay_s, hold_s,
             precondition_interval=None, prior_bands=None, alternate_bands=None):
    t, values = waveform(time_s, signals)
    points = np.asarray(supply_points, dtype=float)
    if points.ndim != 2 or points.shape[1] != 2 or len(points) < 2 or not np.isfinite(points).all() or not np.all(np.diff(points[:, 0]) > 0):
        raise ValueError('Invalid declared supply history')
    if abs(t[0] - points[0, 0]) > 1e-12 or abs(t[-1] - points[-1, 0]) > 1e-10:
        raise ValueError('Incomplete transient')
    if 'vdd' not in values or np.max(abs(values['vdd'] - np.interp(t, points[:, 0], points[:, 1]))) > 1e-6:
        raise ValueError('Supply differs from the declared history')
    events = []
    if not windows or len({w.name for w in windows}) != len(windows):
        raise ValueError('Named observation windows required')
    for window in windows:
        if not window.start_s <= window.ramp_end_s < window.stop_s:
            raise ValueError('Invalid observation window')
        tw, v = segment(t, values, window.start_s, window.stop_s)
        state = accepts(tw, v, state_bands, window.ramp_end_s + state_delay_s, hold_s)
        release = accepts(tw, v, release_bands, window.ramp_end_s + release_delay_s, hold_s)
        events.append(dict(name=window.name, state=state, release=release,
                           pass_contract=state['pass_contract'] and release['pass_contract']))
    prior = alternate = None
    if precondition_interval is not None:
        _, before = segment(t, values, *precondition_interval)
        prior = bool(all(np.all(x >= 0) for x in margins(before, prior_bands)))
        alternate = bool(all(np.all(x >= 0) for x in margins(before, alternate_bands)))
    passed = all(event['pass_contract'] for event in events)
    return dict(status='measured', observed_pass=passed, events=events,
                declared_precondition_verified=prior, alternate_state_exercised=alternate,
                sampled_restoration_observed=bool(passed and prior and alternate),
                coverage='Finite samples with piecewise-linear interpolation; no exhaustive state or physical reliability claim.')


def source_work(time_s, sources):
    """Each named pair is source voltage and current into its positive terminal."""
    if not sources:
        raise ValueError('Declare every independent energy source')
    vectors = {name + suffix: vector for name, pair in sources.items()
               for suffix, vector in zip(('_v', '_i'), pair)}
    t, _ = waveform(time_s, vectors)
    rows = {}
    for name, (voltage, current) in sources.items():
        power = -np.asarray(voltage) * np.asarray(current)
        rows[name] = dict(delivered_J=float(np.trapezoid(np.maximum(power, 0), t)),
                          returned_J=float(np.trapezoid(np.maximum(-power, 0), t)),
                          net_J=float(np.trapezoid(power, t)))
    return dict(sources=rows, **{key: sum(row[key] for row in rows.values())
                                for key in ('delivered_J', 'returned_J', 'net_J')})
