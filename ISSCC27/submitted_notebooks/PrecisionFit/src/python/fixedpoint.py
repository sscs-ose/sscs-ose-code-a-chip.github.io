"""
Bit-accurate fixed-point FIR model -- the golden model.

Convention: Qm.f fixed point, two's complement, stored as Python ints
representing the raw bit pattern (so overflow/wraparound is explicit and
matches what hardware actually does -- no float shortcuts).

  Qm.f  -> m integer bits (including sign), f fractional bits
  value = raw_int / 2**f    (raw_int is a signed m+f-bit two's-complement int)

Two precision modes are supported:

  * uniform  -- every coefficient gets the same bit width
                (`fir_fixed_point`, `FixedPointConfig.coeff_frac_bits`)
  * per-tap  -- every (symmetric-folded) coefficient gets its own fractional
                bit count (`fir_fixed_point_per_tap`). Because the taps then
                have different binary points, each product is aligned to the
                *widest* tap's binary point before summing (hardware does the
                same thing with a free left-shift, i.e. padding zeros into the
                LSBs). `generate_rtl` emits exactly this structure.

`fir_fixed_point` (readable per-sample loop) is the audited golden model.
`fir_fixed_point_fast` is a vectorized re-implementation used only by the
sweeps; `sanity_check.py` asserts the two agree bit-for-bit so the fast path
can never silently drift.
"""
from dataclasses import dataclass
import numpy as np


def float_to_fixed(x: np.ndarray, frac_bits: int, total_bits: int,
                   mode: str = "round") -> np.ndarray:
    """
    Quantize float array to a signed total_bits-wide fixed-point integer array.
    mode: 'round' (round-to-nearest) or 'trunc' (floor).
    Returns int64 array of raw two's-complement values, NOT saturated yet.
    """
    scaled = x * (2 ** frac_bits)
    if mode == "round":
        q = np.round(scaled).astype(np.int64)
    elif mode == "trunc":
        q = np.floor(scaled).astype(np.int64)
    else:
        raise ValueError(mode)
    return q


def saturate(x: np.ndarray, total_bits: int) -> np.ndarray:
    """Clip to the representable range of a signed total_bits two's-complement value."""
    lo = -(2 ** (total_bits - 1))
    hi = (2 ** (total_bits - 1)) - 1
    return np.clip(x, lo, hi)


def wrap(x: np.ndarray, total_bits: int) -> np.ndarray:
    """Two's-complement wraparound (what happens with NO saturation logic)."""
    mask = (1 << total_bits) - 1
    x = x & mask
    sign_bit = 1 << (total_bits - 1)
    return np.where(x >= sign_bit, x - (1 << total_bits), x)


def fixed_to_float(x: np.ndarray, frac_bits: int) -> np.ndarray:
    return x.astype(np.float64) / (2 ** frac_bits)


@dataclass
class FixedPointConfig:
    coeff_int_bits: int       # coefficient integer bits (incl. sign)
    coeff_frac_bits: int      # coefficient fractional bits (uniform mode)
    input_int_bits: int       # input sample integer bits (incl. sign)
    input_frac_bits: int      # input sample fractional bits
    acc_guard_bits: int       # extra headroom bits beyond the theoretical max growth
    output_int_bits: int
    output_frac_bits: int
    rounding: str = "round"       # 'round' or 'trunc', applied at output requantization
    saturate_output: bool = True  # if False, output wraps (used for stress tests)

    @property
    def coeff_total_bits(self):
        return self.coeff_int_bits + self.coeff_frac_bits

    @property
    def input_total_bits(self):
        return self.input_int_bits + self.input_frac_bits

    @property
    def output_total_bits(self):
        return self.output_int_bits + self.output_frac_bits

    def acc_total_bits(self, n_taps: int) -> int:
        """
        Worst-case accumulator width for the symmetric-folded architecture.

        Derivation (see the implementation guide section 3.2 and this project's
        README for the bit-width argument):
          - a folded pre-adder is IN_WIDTH+1 bits wide;
          - its product with a COEFF_INT+F bit constant is (IN_WIDTH+1)+w bits;
          - after aligning the binary point, every term is IN_WIDTH+1+w bits;
          - summing n_terms = (n_taps+1)//2 of them costs ceil(log2(n_terms))
            growth bits; plus explicit guard bits.
        For uniform precision this reduces exactly to

            (coeff_total + input_total) + ceil(log2(n_taps)) + guard

        which is what the guide's formula gives, so the two agree.
        """
        return self.acc_total_bits_for_frac(self.coeff_frac_bits, n_taps)

    def acc_total_bits_for_frac(self, max_coeff_frac_bits: int, n_taps: int) -> int:
        """Accumulator width for a given (maximum) coefficient fractional width."""
        term_bits = self.input_total_bits + self.coeff_int_bits + max_coeff_frac_bits + 1
        n_terms = (n_taps + 1) // 2
        growth_bits = int(np.ceil(np.log2(max(n_terms, 2))))
        return term_bits + growth_bits + self.acc_guard_bits


def quantize_coeffs(h_float: np.ndarray, cfg: FixedPointConfig) -> np.ndarray:
    """Quantize coefficients once (they're constants -> ROM/hardwired in RTL).
    Enforces symmetry after rounding so the model matches the RTL's folded
    architecture even if h_float has microscopic float asymmetry."""
    q = float_to_fixed(h_float, cfg.coeff_frac_bits, cfg.coeff_total_bits, mode="round")
    q = saturate(q, cfg.coeff_total_bits)
    # enforce symmetry: RTL uses q[i] for both taps i and N-1-i
    n_pairs = len(q) // 2
    q[len(q) - 1:n_pairs:-1] = q[:n_pairs]
    return q


def quantize_coeffs_per_tap(h_float: np.ndarray, cfg: FixedPointConfig,
                            coeff_frac_bits_per_tap: np.ndarray) -> np.ndarray:
    """
    Quantize each (symmetric-folded) coefficient with its own fractional width.
    `coeff_frac_bits_per_tap` is indexed by unique-coefficient position
    (0..n_pairs-1 for the folded pairs, n_pairs for the center tap).
    Returns raw ints at each tap's own scale.
    """
    frac = np.asarray(coeff_frac_bits_per_tap, dtype=int)
    n_pairs = (len(h_float) - 1) // 2
    pairs = frac[:n_pairs]
    # full-length view: pairs (taps 0..P-1), center tap, then the mirrored pairs
    widths = np.concatenate([pairs, [frac[n_pairs]], pairs[::-1]])
    assert len(widths) == len(h_float), "per-tap frac bits length mismatch"

    q = np.zeros(len(h_float), dtype=np.int64)
    for i, f in enumerate(widths):
        total_bits = cfg.coeff_int_bits + int(f)
        v = float_to_fixed(np.array([h_float[i]]), int(f), total_bits, mode="round")
        q[i] = saturate(v, total_bits)[0]
    # enforce symmetry: RTL uses q[i] for both taps i and N-1-i
    q[len(q) - 1:n_pairs:-1] = q[:n_pairs]
    return q


def _unique_view(h_fixed_taps: np.ndarray) -> np.ndarray:
    """Raw ints for the unique folded coefficients: [pair0..pair_{P-1}, center]."""
    n_taps = len(h_fixed_taps)
    n_pairs = n_taps // 2
    return np.array([int(h_fixed_taps[i]) for i in range(n_pairs)] +
                    [int(h_fixed_taps[n_pairs])], dtype=np.int64)


def fir_fixed_point(x_float: np.ndarray, h_float: np.ndarray,
                    cfg: FixedPointConfig) -> dict:
    """
    Reference bit-accurate fixed-point FIR, direct form, matching the RTL's
    arithmetic step for step. This is what verify_rtl.py compares Verilator /
    Icarus output against.
    """
    n_taps = len(h_float)
    h_fixed = quantize_coeffs(h_float, cfg)

    x_fixed = float_to_fixed(x_float, cfg.input_frac_bits, cfg.input_total_bits,
                             mode="round")
    x_fixed = saturate(x_fixed, cfg.input_total_bits)

    n = len(x_fixed)
    acc_bits = cfg.acc_total_bits(n_taps)
    acc_lo = -(2 ** (acc_bits - 1))
    acc_hi = (2 ** (acc_bits - 1)) - 1

    y_raw = np.zeros(n, dtype=np.int64)
    overflow_events = 0
    clip_events = 0

    out_lo = -(2 ** (cfg.output_total_bits - 1))
    out_hi = (2 ** (cfg.output_total_bits - 1)) - 1

    padded = np.concatenate([np.zeros(n_taps - 1, dtype=np.int64), x_fixed])
    for i in range(n):
        window = padded[i:i + n_taps][::-1]
        # use Python int() to avoid int64 overflow for wide configs (N1 fix)
        products = [int(w) * int(c) for w, c in zip(window, h_fixed)]
        acc = sum(products)

        if acc > acc_hi or acc < acc_lo:
            overflow_events += 1
            if cfg.saturate_output:
                acc = max(acc_lo, min(acc_hi, acc))
            else:
                # W1 fix: hardware register wraps modulo 2**acc_bits before shift
                mask = (1 << acc_bits) - 1
                acc = acc & mask
                if acc >= (1 << (acc_bits - 1)):
                    acc -= (1 << acc_bits)

        acc_frac_bits = cfg.coeff_frac_bits + cfg.input_frac_bits
        shift = acc_frac_bits - cfg.output_frac_bits
        assert shift >= 0, "output_frac_bits must be <= accumulator fractional bits"

        if cfg.rounding == "round" and shift > 0:
            acc_shifted = (acc + (1 << (shift - 1))) >> shift
        else:
            acc_shifted = acc >> shift

        # W3 fix: track output clipping separately from accumulator overflow
        if acc_shifted > out_hi or acc_shifted < out_lo:
            clip_events += 1

        if not cfg.saturate_output:
            acc_shifted = wrap(np.array([acc_shifted]), cfg.output_total_bits)[0]
        else:
            acc_shifted = saturate(np.array([acc_shifted]), cfg.output_total_bits)[0]

        y_raw[i] = acc_shifted

    y_float = fixed_to_float(y_raw, cfg.output_frac_bits)
    return dict(y_float=y_float, y_raw=y_raw, overflow_events=overflow_events,
                clip_events=clip_events, h_fixed=h_fixed, x_fixed=x_fixed)


def fir_fixed_point_per_tap(x_float: np.ndarray, h_float: np.ndarray,
                            cfg: FixedPointConfig,
                            coeff_frac_bits_per_tap: np.ndarray) -> dict:
    """
    Bit-accurate fixed-point FIR with a *per-tap* coefficient fractional width.

    Products with different binary points cannot be added directly. Every tap's
    product is therefore left-shifted by (F - f_i), where F = max_i f_i, so all
    terms share the binary point at `input_frac + F` (equivalently: the low
    bits are zero-padded). This is a free wiring shift in hardware and it is
    exactly what the generated RTL does.
    """
    n_taps = len(h_float)
    frac = np.asarray(coeff_frac_bits_per_tap, dtype=int)
    n_pairs = n_taps // 2
    F = int(frac.max())

    h_fixed = quantize_coeffs_per_tap(h_float, cfg, frac)
    # align every tap to the common binary point F (per-tap view + full view)
    h_fixed_unique = _unique_view(h_fixed)
    pairs = frac[:n_pairs]
    h_unique_frac = np.concatenate([pairs, [frac[n_pairs]], pairs[::-1]])
    shift_up = F - h_unique_frac
    h_common = np.array([int(h_fixed[i]) << int(shift_up[i])
                         for i in range(n_taps)], dtype=object)

    x_fixed = float_to_fixed(x_float, cfg.input_frac_bits, cfg.input_total_bits,
                             mode="round")
    x_fixed = saturate(x_fixed, cfg.input_total_bits)

    n = len(x_fixed)
    acc_bits = cfg.acc_total_bits_for_frac(F, n_taps)
    acc_lo = -(2 ** (acc_bits - 1))
    acc_hi = (2 ** (acc_bits - 1)) - 1

    y_raw = np.zeros(n, dtype=np.int64)
    overflow_events = 0
    clip_events = 0
    acc_frac_bits = cfg.input_frac_bits + F
    shift = acc_frac_bits - cfg.output_frac_bits
    assert shift >= 0, "output_frac_bits must be <= accumulator fractional bits"

    out_lo = -(2 ** (cfg.output_total_bits - 1))
    out_hi = (2 ** (cfg.output_total_bits - 1)) - 1

    padded = np.concatenate([np.zeros(n_taps - 1, dtype=np.int64), x_fixed])
    for i in range(n):
        window = padded[i:i + n_taps][::-1]
        acc = int(sum(int(w) * int(c) for w, c in zip(window, h_common)))

        if acc > acc_hi or acc < acc_lo:
            overflow_events += 1
            if cfg.saturate_output:
                acc = max(acc_lo, min(acc_hi, acc))
            else:
                # W1 fix: hardware register wraps modulo 2**acc_bits before shift
                mask = (1 << acc_bits) - 1
                acc = acc & mask
                if acc >= (1 << (acc_bits - 1)):
                    acc -= (1 << acc_bits)

        if cfg.rounding == "round" and shift > 0:
            acc_shifted = (acc + (1 << (shift - 1))) >> shift
        else:
            acc_shifted = acc >> shift

        # W3 fix: track output clipping separately from accumulator overflow
        if acc_shifted > out_hi or acc_shifted < out_lo:
            clip_events += 1

        if not cfg.saturate_output:
            acc_shifted = wrap(np.array([acc_shifted]), cfg.output_total_bits)[0]
        else:
            acc_shifted = saturate(np.array([acc_shifted]), cfg.output_total_bits)[0]

        y_raw[i] = acc_shifted

    y_float = fixed_to_float(y_raw, cfg.output_frac_bits)
    return dict(y_float=y_float, y_raw=y_raw, overflow_events=overflow_events,
                clip_events=clip_events, h_fixed=h_fixed, h_fixed_unique=h_fixed_unique,
                h_common=h_common, x_fixed=x_fixed, coeff_frac_bits_max=F)


def run_model(x_float: np.ndarray, h_float: np.ndarray, cfg: FixedPointConfig,
              bit_widths=None) -> dict:
    """
    Single entry point used by the search / verification / stress-test code:
    uniform precision when `bit_widths` is None, otherwise per-tap widths
    (total bits per unique coefficient: folded pairs first, center tap last).
    """
    if bit_widths is None:
        return fir_fixed_point(x_float, h_float, cfg)
    frac_bits = np.asarray(bit_widths, dtype=int) - cfg.coeff_int_bits
    return fir_fixed_point_per_tap(x_float, h_float, cfg, frac_bits)


def fir_fixed_point_fast(x_float: np.ndarray, h_float: np.ndarray,
                         cfg: FixedPointConfig) -> dict:
    """
    Vectorized equivalent of `fir_fixed_point` (uniform precision only).
    Used by the sweeps; asserted bit-identical to the golden loop in
    sanity_check.py. Kept separate so the golden model stays auditable.
    """
    n_taps = len(h_float)
    h_fixed = quantize_coeffs(h_float, cfg).astype(object)

    x_fixed = saturate(float_to_fixed(x_float, cfg.input_frac_bits,
                                      cfg.input_total_bits, mode="round"),
                       cfg.input_total_bits)

    acc_bits = cfg.acc_total_bits(n_taps)
    acc_lo = -(2 ** (acc_bits - 1))
    acc_hi = (2 ** (acc_bits - 1)) - 1

    padded = np.concatenate([np.zeros(n_taps - 1, dtype=np.int64), x_fixed])
    windows = np.lib.stride_tricks.sliding_window_view(padded, n_taps)[:, ::-1]

    # object dtype keeps the products exact for any swept bit width
    acc = (windows.astype(object) * h_fixed[None, :]).sum(axis=1).astype(object)
    acc = np.array([int(v) for v in acc], dtype=object)

    overflow_events = int(np.sum((acc > acc_hi) | (acc < acc_lo)))
    if cfg.saturate_output:
        acc = np.clip(acc, acc_lo, acc_hi)
    else:
        # W1 fix: hardware wraps at acc_bits before the shift
        overflow_mask = (acc > acc_hi) | (acc < acc_lo)
        if np.any(overflow_mask):
            mask_val = (1 << acc_bits) - 1
            sign_val = 1 << (acc_bits - 1)
            wrapped = acc & mask_val
            wrapped = np.where(wrapped >= sign_val, wrapped - (1 << acc_bits), wrapped)
            acc = np.where(overflow_mask, wrapped, acc)

    acc_frac_bits = cfg.coeff_frac_bits + cfg.input_frac_bits
    shift = acc_frac_bits - cfg.output_frac_bits
    assert shift >= 0, "output_frac_bits must be <= accumulator fractional bits"

    if cfg.rounding == "round" and shift > 0:
        shifted = (acc + (1 << (shift - 1))) >> shift        # floor, like Verilog >>>
    else:
        shifted = acc >> shift

    # W3 fix: track output clipping
    out_lo = -(2 ** (cfg.output_total_bits - 1))
    out_hi = (2 ** (cfg.output_total_bits - 1)) - 1
    clip_events = int(np.sum((shifted > out_hi) | (shifted < out_lo)))

    if not cfg.saturate_output:
        y_raw = wrap(np.array([int(v) for v in shifted]), cfg.output_total_bits)
    else:
        y_raw = np.clip(np.array([int(v) for v in shifted], dtype=object),
                        out_lo, out_hi)
    y_raw = np.array([int(v) for v in y_raw], dtype=np.int64)

    return dict(y_float=fixed_to_float(y_raw, cfg.output_frac_bits),
                y_raw=y_raw, overflow_events=overflow_events,
                clip_events=clip_events,
                h_fixed=quantize_coeffs(h_float, cfg), x_fixed=x_fixed)


def fir_fixed_point_per_tap_fast(x_float: np.ndarray, h_float: np.ndarray,
                                 cfg: FixedPointConfig,
                                 coeff_frac_bits_per_tap: np.ndarray) -> dict:
    """
    Vectorized equivalent of `fir_fixed_point_per_tap`. The total number of
    input samples here is small (2048-4096) and the sweep runs a few hundred
    configs, so the plain loop is already vectorized enough: it is implemented
    with numpy windowing and object-dtype arithmetic, matching the golden loop
    exactly.
    """
    n_taps = len(h_float)
    frac = np.asarray(coeff_frac_bits_per_tap, dtype=int)
    n_pairs = n_taps // 2
    F = int(frac.max())

    h_fixed = quantize_coeffs_per_tap(h_float, cfg, frac)
    pairs = frac[:n_pairs]
    h_unique_frac = np.concatenate([pairs, [frac[n_pairs]], pairs[::-1]])
    shift_up = F - h_unique_frac
    h_common = np.array([int(h_fixed[i]) << int(shift_up[i])
                         for i in range(n_taps)], dtype=object)

    x_fixed = saturate(float_to_fixed(x_float, cfg.input_frac_bits,
                                      cfg.input_total_bits, mode="round"),
                       cfg.input_total_bits)

    acc_bits = cfg.acc_total_bits_for_frac(F, n_taps)
    acc_lo = -(2 ** (acc_bits - 1))
    acc_hi = (2 ** (acc_bits - 1)) - 1

    padded = np.concatenate([np.zeros(n_taps - 1, dtype=np.int64), x_fixed])
    windows = np.lib.stride_tricks.sliding_window_view(padded, n_taps)[:, ::-1]
    # W5 fix: fully vectorized (was a Python list comprehension per sample)
    acc = (windows.astype(object) * h_common[None, :]).sum(axis=1)
    acc = np.array([int(v) for v in acc], dtype=object)

    overflow_events = int(np.sum((acc > acc_hi) | (acc < acc_lo)))
    if cfg.saturate_output:
        acc = np.clip(acc, acc_lo, acc_hi)
    else:
        # W1 fix: hardware wraps at acc_bits before the shift
        overflow_mask = (acc > acc_hi) | (acc < acc_lo)
        if np.any(overflow_mask):
            mask_val = (1 << acc_bits) - 1
            sign_val = 1 << (acc_bits - 1)
            wrapped = acc & mask_val
            wrapped = np.where(wrapped >= sign_val, wrapped - (1 << acc_bits), wrapped)
            acc = np.where(overflow_mask, wrapped, acc)

    acc_frac_bits = cfg.input_frac_bits + F
    shift = acc_frac_bits - cfg.output_frac_bits
    assert shift >= 0, "output_frac_bits must be <= accumulator fractional bits"

    if cfg.rounding == "round" and shift > 0:
        shifted = (acc + (1 << (shift - 1))) >> shift
    else:
        shifted = acc >> shift

    # W3 fix: track output clipping
    out_lo = -(2 ** (cfg.output_total_bits - 1))
    out_hi = (2 ** (cfg.output_total_bits - 1)) - 1
    clip_events = int(np.sum((shifted > out_hi) | (shifted < out_lo)))

    if not cfg.saturate_output:
        y_raw = wrap(np.array([int(v) for v in shifted]), cfg.output_total_bits)
    else:
        y_raw = np.clip(np.array([int(v) for v in shifted], dtype=object),
                        out_lo, out_hi)
    y_raw = np.array([int(v) for v in y_raw], dtype=np.int64)

    return dict(y_float=fixed_to_float(y_raw, cfg.output_frac_bits),
                y_raw=y_raw, overflow_events=overflow_events,
                clip_events=clip_events,
                h_fixed=h_fixed, x_fixed=x_fixed, coeff_frac_bits_max=F)
