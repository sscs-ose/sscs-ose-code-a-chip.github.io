"""
Per-coefficient sensitivity analysis for precision allocation.

Method: finite-difference perturbation. For each unique coefficient (after
symmetric folding), perturb by +/- eps, measure the resulting change in
frequency-response margin (distance from the spec's ripple/attenuation
limits). Coefficients whose perturbation causes large margin loss are
"high-sensitivity" -> allocate them more bits. Low-sensitivity coefficients
can be quantized more aggressively.

This is a numerical gradient estimate -- a standard, explainable technique
(finite-difference sensitivity analysis), not a novel algorithm. The
contribution is applying it to bit-width allocation and then *verifying the
resulting hardware*.
"""
import numpy as np

# np.trapezoid was introduced in NumPy 2.0; np.trapz was removed in NumPy 2.0.
# On NumPy 1.x (e.g. the Colab standard image) trapezoid does not exist yet,
# so alias it from trapz.  On NumPy 2.x both attributes are the same function
# and this branch is never taken.
if not hasattr(np, "trapezoid"):
    np.trapezoid = np.trapz  # type: ignore[attr-defined]  # NumPy 1.x only

from reference import FILTER_A_SPEC, design_filter, verify_spec


def unique_coeff_indices(n_taps: int) -> list:
    """
    Indices into the full coefficient array representing each unique
    (symmetric-folded) coefficient: one representative per folded pair, then
    the center tap. Length = n_taps // 2 + 1.
    """
    n_pairs = n_taps // 2
    return list(range(n_pairs)) + [n_pairs]


def perturb_and_measure(h: np.ndarray, idx: int, eps: float, spec: dict,
                        n_taps: int) -> dict:
    """
    Perturb coefficient at `idx` (and its symmetric partner, to keep the
    filter symmetric -- asymmetric perturbation would break the linear-phase
    property the whole architecture assumes) by +eps, and measure the margin
    change per unit perturbation.
    """
    h_pert = h.copy()
    partner = n_taps - 1 - idx
    h_pert[idx] += eps
    if partner != idx:
        h_pert[partner] += eps

    v_base = verify_spec(h, spec)
    v_pert = verify_spec(h_pert, spec)

    passband_margin_base = spec["passband_ripple_db"] - v_base["passband_ripple_db"]
    passband_margin_pert = spec["passband_ripple_db"] - v_pert["passband_ripple_db"]
    stopband_margin_base = v_base["stopband_atten_db"] - spec["stopband_atten_db"]
    stopband_margin_pert = v_pert["stopband_atten_db"] - spec["stopband_atten_db"]

    return dict(
        d_passband_margin=(passband_margin_pert - passband_margin_base) / eps,
        d_stopband_margin=(stopband_margin_pert - stopband_margin_base) / eps,
    )


def compute_sensitivities(h: np.ndarray, spec: dict, eps: float = 1e-4) -> np.ndarray:
    """
    Returns an array of sensitivity scores, one per unique coefficient
    (length = n_pairs + 1). Score = combined passband+stopband margin
    sensitivity magnitude -- higher means "more damaging to quantize
    aggressively".
    """
    n_taps = len(h)
    indices = unique_coeff_indices(n_taps)
    scores = np.zeros(len(indices))

    for k, idx in enumerate(indices):
        r = perturb_and_measure(h, idx, eps, spec, n_taps)
        scores[k] = max(abs(r["d_passband_margin"]), abs(r["d_stopband_margin"]))
    return scores


def basis_influence(h: np.ndarray, spec: dict, n_fft: int = 8192) -> tuple:
    """
    The exact per-tap basis function of the frequency response, on a grid.

    H(w) = sum_n h[n] e^{-jwn} is affine in every coefficient, so for a
    symmetric pair (taps i and N-1-i, shared value c_i) the derivative with
    respect to c_i has magnitude

        |dH/dc_i| = 2*|cos(w*(center - i))|      (folded pair)
        |dH/dc_c| = 1                             (center tap)

    Returns (w, influence) with influence[k] the grid of |dH/dc_k| for the k-th
    unique coefficient, plus the passband/stopband masks.
    """
    n_taps = len(h)
    n_pairs = n_taps // 2
    fs = spec["fs"]
    w = np.linspace(0.0, np.pi, n_fft)

    wp = 2 * np.pi * spec["passband_edge"] / fs
    ws = 2 * np.pi * spec["stopband_edge"] / fs
    pass_mask = w <= wp
    stop_mask = w >= ws

    influence = []
    for i in range(n_pairs):
        influence.append(2.0 * np.abs(np.cos(w * (n_pairs - i))))
    influence.append(np.ones_like(w))          # center tap
    return w, np.array(influence), pass_mask, stop_mask


def compute_sensitivities_response(h: np.ndarray, spec: dict,
                                   n_fft: int = 8192) -> np.ndarray:
    """
    Sensitivity = how much *spec-weighted* frequency-response deviation one
    unit of coefficient error at this tap injects.

        S_k = sqrt(  (1/dp^2) * int_pass |dH/dc_k|^2 dw
                   + (1/ds^2) * int_stop |dH/dc_k|^2 dw  )

    where dp/ds are the linear passband-ripple and stopband-deviation budgets
    from the spec. This is the same intent as the finite-difference margin
    method above ("protect the taps whose error hurts the spec most"), but it
    is EXACT rather than a noisy finite difference of a scalar max/min -- see
    the notebook/markdown for the stability comparison that motivated it.
    """
    w, influence, pass_mask, stop_mask = basis_influence(h, spec, n_fft)

    ripple_lin = (10 ** (spec["passband_ripple_db"] / 20) - 1) / \
                 (10 ** (spec["passband_ripple_db"] / 20) + 1)
    delta_p = max(ripple_lin, 1e-12)
    delta_s = max(10 ** (-spec["stopband_atten_db"] / 20), 1e-12)

    weight = np.zeros_like(w)
    weight[pass_mask] += 1.0 / (delta_p ** 2)
    weight[stop_mask] += 1.0 / (delta_s ** 2)

    # trapezoidal integral over the frequency grid
    integrand = influence ** 2 * weight[None, :]
    return np.sqrt(np.trapezoid(integrand, w, axis=1))


def sensitivity_rank_stability(h: np.ndarray, spec: dict,
                               eps_values=(1e-2, 1e-3, 1e-4, 1e-5, 1e-6)) -> dict:
    """
    Run the analysis at several eps and report Spearman-like rank agreement
    between them. A ranking that flips with eps is not a usable ranking, and
    the guide explicitly asks for this to be checked (and reported as a
    limitation if it does not stabilise).
    """
    rankings = {}
    for eps in eps_values:
        scores = compute_sensitivities(h, spec, eps=eps)
        rankings[eps] = np.argsort(np.argsort(-scores))  # rank 0 = most sensitive

    base_eps = eps_values[len(eps_values) // 2]
    base = rankings[base_eps]
    agreement = {}
    for eps, ranks in rankings.items():
        # fraction of unique coefficients whose rank is identical to base
        agreement[eps] = float(np.mean(ranks == base))
    return dict(rankings=rankings, agreement=agreement, base_eps=base_eps)


def allocate_bits_by_sensitivity(scores: np.ndarray, min_bits: int, max_bits: int,
                                 n_levels: int = None) -> np.ndarray:
    """
    Map sensitivity scores to per-coefficient total bit widths.

    Simple, explainable allocation rule: rank coefficients by sensitivity and
    linearly interpolate the bit width between min_bits (least sensitive) and
    max_bits (most sensitive). `n_levels` quantizes the bit-width choices
    themselves to a small set (e.g. 4 discrete widths) since real hardware
    benefits from a few reused multiplier widths, not N arbitrary ones -- and
    it makes the RTL/report much more readable.
    """
    scores = np.asarray(scores, dtype=float)
    n = len(scores)
    if n_levels is None:
        n_levels = max_bits - min_bits + 1
    ranks = np.argsort(np.argsort(scores))          # rank 0 = least sensitive
    normalized_rank = ranks / max(n - 1, 1)
    levels = np.round(normalized_rank * (n_levels - 1)).astype(int)
    step = (max_bits - min_bits) / max(n_levels - 1, 1)
    bit_widths = min_bits + levels * step
    return np.round(bit_widths).astype(int)


def _print_ranking(title, scores, indices, h):
    order = np.argsort(-scores)
    print(f"\n{title}")
    print(f"{'tap idx':>8} {'coeff value':>12} {'sensitivity':>14} {'rank':>6}")
    for rank, k in enumerate(order):
        print(f"{indices[k]:>8} {h[indices[k]]:>12.5f} {scores[k]:>14.4e} {rank:>6}")
    return order


if __name__ == "__main__":
    h = design_filter(FILTER_A_SPEC)
    indices = unique_coeff_indices(len(h))

    fd_scores = compute_sensitivities(h, FILTER_A_SPEC)
    _print_ranking("Guide method: finite-difference of the scalar margins",
                   fd_scores, indices, h)

    print("\neps stability of the guide method (fraction of taps whose rank is "
          "unchanged relative to the middle eps):")
    stable = sensitivity_rank_stability(h, FILTER_A_SPEC)
    for eps, frac in stable["agreement"].items():
        print(f"  eps={eps:>8.0e}: {frac * 100:5.1f}% rank agreement vs eps="
              f"{stable['base_eps']:.0e}")

    resp_scores = compute_sensitivities_response(h, FILTER_A_SPEC)
    _print_ranking("Exact method used for allocation: spec-weighted response "
                   "influence", resp_scores, indices, h)

    bits = allocate_bits_by_sensitivity(resp_scores, min_bits=4, max_bits=12,
                                        n_levels=4)
    print("\nAllocated bit widths (4-12 range, 4 discrete levels):")
    for k, idx in enumerate(indices):
        print(f"  tap {idx:>2}: coeff={h[idx]:+.5f}, bits={bits[k]}")
