"""Reference-bit-aware measurements for the demo's receiver convention.

silk measures and centers the geometric eye. The local PRBS decoder chooses
latency/phase from training only and independently checks transmitted bits;
a clean geometric eye alone cannot prove that those bits are correct.
"""
from typing import NamedTuple
import numpy as np
from silk.exceptions import SimulationError
from silk.metrics import average_power, eye_diagram, sample
from characterization.stimulus import prbs_stimulus
from silk.signals import Signal, metric
from silk.signals.schema import Transient

PHASES = np.linspace(0.0, 1.0, 101)
MAX_LAG_UI = 6


def measure_reference(t, voltage, experiment, *, t0):
    """Select lag/phase on bits 32:64, then hold them fixed on measured bits."""
    t, voltage = np.asarray(t, float), np.asarray(voltage, float)
    record = prbs_stimulus(experiment)
    bits = np.asarray(record['bits'], int)
    first, stop = record['measurement_bit_range']
    ui = 1 / experiment['bit_rate_hz']
    if (t.ndim != 1 or voltage.shape != t.shape or len(t) < 2
            or not np.all(np.isfinite(t)) or not np.all(np.isfinite(voltage))
            or np.any(np.diff(t) <= 0)):
        raise SimulationError('Link measurements require finite, strictly increasing transient samples.')
    if t[0] > t0 or t[-1] < t0 + (stop + MAX_LAG_UI + 2) * ui:
        raise SimulationError('Transient waveform does not cover the full alignment and measurement window.')
    rx = Signal('rxp-rxn', 'tran', 'time', 'voltage', t, voltage)
    threshold = 0.0
    # This example illustrates composing silk native commands: sample the
    # analog Signal, then use a simple threshold comparison to decide each bit.
    # Training chooses alignment; the measured window does not change it.
    # These are separate windows of the same deterministic PRBS sequence.
    train = np.arange(first // 2, first)
    reference = bits[train]
    choices = []
    for lag in range(MAX_LAG_UI + 1):
        for phase in PHASES[5:96]:
            # Silk API: sample at candidate decision times; Python compares to 0 V.
            sampled = sample(rx, x_new=t0 + (train + lag + phase) * ui).y
            decoded = sampled > threshold
            errors = int(np.count_nonzero(decoded != reference))
            margin = float(np.min(np.where(reference, sampled, -sampled)))
            choices.append(((errors, -margin, abs(phase - .5), lag), lag, float(phase)))
    score, lag, phase = min(choices)
    indices = np.arange(first, stop)
    truth = bits[indices].astype(bool)
    if not truth.any() or truth.all():
        raise SimulationError('Eye measurement requires both high and low reference bits.')
    start = float(t0 + (first + lag + phase) * ui)
    end = float(t0 + (stop + lag + phase) * ui)
    values = sample(rx, x_new=t0 + (indices + lag + phase) * ui).y
    decoded = values > threshold
    return {
        'bit_errors': int(np.count_nonzero(decoded != truth)),
        'measured_bits': len(indices),
        'reference_margin_v': float(np.min(np.where(truth, values, -values))),
        'alignment_lag_ui': lag,
        'decision_phase_ui': phase,
        'training_bit_errors': score[0],
        'training_margin_v': -score[1],
        'training_bit_range': [int(train[0]), int(train[-1]+1)],
        'phase_resolution_ui': .01,
        'measurement_start_s': float(t0 + (first + lag + phase) * ui),
        'measurement_stop_s': float(t0 + (stop + lag + phase) * ui),
    }


def measure_link(t, voltage, experiment, *, t0):
    """Compose the example's reference check with one native eye calculation."""
    result = measure_reference(t, voltage, experiment, t0=t0)
    rx = Signal('rxp-rxn', 'tran', 'time', 'voltage', t, voltage).window(
        result['measurement_start_s'], result['measurement_stop_s'])
    ui = 1 / experiment['bit_rate_hz']
    # Silk API: measure geometric eye opening independently of bit correctness.
    eye = eye_diagram(rx, period=ui, auto_center=True, threshold=0.0)
    return result | {'eye_height_v': float(eye.height),
                     'eye_width_ui': float(eye.width/ui),
                     'eye_sampling_instant_s': float(eye.sampling_instant_s)}


class LinkMeasurements(NamedTuple):
    """Named scalar outputs; tuple storage supports native report JSON."""
    bit_errors: float
    eye_height_v: float
    eye_width_ui: float
    alignment_lag_ui: float
    decision_phase_ui: float
    training_bit_errors: float
    reference_margin_v: float
    eye_sampling_instant_s: float


# Silk API: @metric(outputs=...) exposes several named results from one
# calculation, so eye height and width do not require separate eye calculations.
# Registered as "link", these become link.eye_height_v, link.eye_width_ui, etc.
@metric(domain='tran', outputs={
    'bit_errors': '', 'eye_height_v': 'V', 'eye_width_ui': '',
    'alignment_lag_ui': '', 'decision_phase_ui': '', 'training_bit_errors': '',
    'reference_margin_v': 'V', 'eye_sampling_instant_s': 's'})
def serdes_link_measurements(sig: Transient, *, bit_rate_hz: float,
                             run_length: str = "quick", prbs_offset: int = 0) -> LinkMeasurements:
    """Example composition: silk publishes each field from one calculation.

    The trained window is local policy; eye_diagram supplies the eye result.
    Native multi-output registration computes these values once per evaluation.
    """
    experiment = dict(bit_rate_hz=bit_rate_hz, run_length=run_length, prbs_offset=prbs_offset)
    values = measure_link(sig.x, sig.y, experiment, t0=2/bit_rate_hz)
    return LinkMeasurements(**{name: float(values[name])
                               for name in LinkMeasurements.__annotations__})


def supply_power(voltage, current, start, stop):
    """Power delivered by the supply; SPICE current into its + terminal is negated."""
    t = np.asarray(voltage.x, float)
    ti = np.asarray(current.x, float)
    if max(t[0], ti[0]) > start or min(t[-1], ti[-1]) < stop:
        raise SimulationError('Supply waveforms do not cover the power measurement window.')
    # Include exact window boundaries before measuring average power.
    grid = np.unique(np.r_[start, t[(t > start) & (t < stop)], stop])
    v = voltage.interpolate(grid)
    i = -current.interpolate(grid)
    # Silk API: average delivered power on the aligned voltage/current grid.
    result = float(average_power(v, i))
    if not np.isfinite(result):
        raise SimulationError('Nonfinite supply power extracted from transient data.')
    return result
