"""PRBS9 stimulus and bit windows for the local SerDes testbench.

silk generates the canonical PRBS sequence; this module chooses warmup,
measurement windows, phase offset and serializer word padding.
"""
from silk.sources import prbs_bits
from numbers import Integral
from math import isfinite
SERIALIZER_RATIO = 10

def prbs_stimulus(settings):
    """Generate continuous PRBS with warmup, measurement and word padding."""
    length = settings.get('run_length', 'quick')
    rate = settings.get('bit_rate_hz', 600e6)
    offset = settings.get('prbs_offset', 0)
    if length not in ('quick', 'full'):
        raise ValueError('run_length must be quick or full')
    if isinstance(rate, bool) or not isinstance(rate, (int, float)) or not isfinite(rate) or rate <= 0:
        raise ValueError('bit_rate_hz must be finite and positive')
    if isinstance(offset, bool) or not isinstance(offset, Integral) or not 0 <= offset < 511:
        raise ValueError('prbs_offset must be an integer from 0 through 510')
    # Demo policy: skip 64 startup bits; measure 128 bits or one 511-bit period.
    measured = 128 if length == 'quick' else 511
    stop = 64 + measured
    # Add at least 16 trailing bits and round up to complete serializer words.
    total = ((stop + 16 + SERIALIZER_RATIO - 1) // SERIALIZER_RATIO) * SERIALIZER_RATIO
    # Silk API: generate PRBS9; slicing only selects its starting phase.
    return {'bits': list(prbs_bits(9, total + offset)[offset:]),
            'measurement_bit_range': [64, stop],
            'measurement_duration_s': measured / rate,
            'stimulus_duration_s': total / rate}
