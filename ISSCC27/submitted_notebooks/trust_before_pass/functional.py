"""Sampled, first-startup response contract. Apache-2.0.

No dependency on CACE or scalar extraction. This is not a brownout monitor,
glitch filter, continuous-time proof, or reconstruction of the designer's spec.
"""
from dataclasses import dataclass, asdict
from numbers import Real
import numpy as np
from evidence import rising_crossings


@dataclass(frozen=True)
class FunctionalContract:
    supply_trigger_v: float = 3.0
    por_threshold_v: float = .9
    response_deadline_s: float = .002
    observation_start_s: float = 0.0
    max_sample_gap_s: float = 2e-6
    source: str = 'Teaching assumption T1; FUNCTIONAL_CONTRACT.md, not an upstream acceptance specification'

    def __post_init__(self):
        values = [v for k, v in asdict(self).items() if k != 'source']
        if (not all(isinstance(v, Real) and not isinstance(v, bool) and np.isfinite(v) for v in values) or self.supply_trigger_v <= 0
                or self.por_threshold_v <= 0 or self.response_deadline_s <= 0
                or self.observation_start_s < 0 or self.max_sample_gap_s <= 0
                or not isinstance(self.source, str) or not self.source.strip()):
            raise ValueError('Finite positive thresholds/deadline/gap and explicit source required')


def assess_function(t, avdd, por, contract):
    """First supply rising crossing -> NEW POR rise within inclusive deadline.

    AVDD must stay >= trigger until the witness or deadline. Partial history,
    ambiguous sampling and supply collapse return INSUFFICIENT_EVIDENCE.
    No observed trigger returns NOT_TRIGGERED, never vacuous PASS.
    The reported verdict applies only to this explicitly sourced contract.
    """
    c = contract
    out = dict(status='INSUFFICIENT_EVIDENCE', reason='', trigger_s=None,
               deadline_s=None, witness_s=None, contract=asdict(c))
    def done(status, reason):
        out.update(status=status, reason=reason)
        return out
    try:
        t, avdd, por = [np.asarray(x, dtype=float) for x in (t, avdd, por)]
        triggers = rising_crossings(t, avdd, c.supply_trigger_v)
        events = rising_crossings(t, por, c.por_threshold_v)
    except (ValueError, TypeError) as exc:
        return done('INSUFFICIENT_EVIDENCE', 'invalid_trace: '+str(exc))
    if t[0] > c.observation_start_s + 1e-12 or t[-1] < c.observation_start_s:
        return done('INSUFFICIENT_EVIDENCE', 'missing_initial_history')
    if np.interp(c.observation_start_s, t, avdd) >= c.supply_trigger_v:
        return done('INSUFFICIENT_EVIDENCE', 'supply_initially_high; rising trigger unobserved')
    triggers = triggers[triggers >= c.observation_start_s]
    trigger = float(triggers[0]) if len(triggers) else None
    if trigger is None:
        relevant = (t[1:] > c.observation_start_s)
        if np.any(np.diff(t)[relevant] > c.max_sample_gap_s*(1+1e-9)):
            return done('INSUFFICIENT_EVIDENCE', 'sampling_gap_before_trigger')
        return done('NOT_TRIGGERED', 'no_supply_trigger_observed; no functional PASS asserted')
    deadline = trigger + c.response_deadline_s
    out.update(trigger_s=trigger, deadline_s=deadline)
    timely = events[(events >= trigger) & (events <= deadline + 1e-12)]
    witness = float(timely[0]) if len(timely) else None
    end = witness if witness is not None else min(deadline, float(t[-1]))
    # Include segments intersecting the required interval; no unsupported
    # interpolation across missing observations is accepted.
    segments = (t[:-1] < end) & (t[1:] > c.observation_start_s)
    if np.any(np.diff(t)[segments] > c.max_sample_gap_s*(1+1e-9)):
        return done('INSUFFICIENT_EVIDENCE', 'sampling_gap_in_required_history')
    between = avdd[(t > trigger) & (t < end)]
    if np.any(between < c.supply_trigger_v) or np.interp(end,t,avdd) < c.supply_trigger_v-1e-12:
        return done('INSUFFICIENT_EVIDENCE', 'supply_dropped; recovery outside first-startup contract')
    if witness is not None:
        out['witness_s'] = witness
        return done('PASS', 'new_por_rise_observed_within_deadline')
    if t[-1] < deadline-1e-12:
        return done('INSUFFICIENT_EVIDENCE', 'deadline_not_observed')
    return done('FAIL', 'deadline_observed_without_new_por_rise; an earlier high level is not a new edge')
