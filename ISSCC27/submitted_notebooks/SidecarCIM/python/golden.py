"""Bit-exact golden model for SidecarCIM: dense unsigned DCIM core plus the sidecar (outlier) path.

Sidecar slot format, per array column j: k = spec outlier.budget_per_output slots, each slot is
(row index r in [0, n_inputs), signed value v with outlier.weight_bits bits, two's complement).
Unused slot: v = 0 (row index ignored). Arrays: idx (k, n_outputs), val (k, n_outputs).
"""
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
SPEC = yaml.safe_load((ROOT / "spec" / "spec.yaml").read_text())


def dcim_dot(w, x, wbits, abits):
    """Bit-serial DCIM dot product, exactly as hardware computes it.

    w: (n_inputs, n_outputs) unsigned ints, x: (n_inputs,) unsigned ints.
    """
    w = np.asarray(w, dtype=np.int64)
    x = np.asarray(x, dtype=np.int64)
    acc = np.zeros(w.shape[1], dtype=np.int64)
    for a in range(abits - 1, -1, -1):            # input bits, MSB first
        xb = (x >> a) & 1
        part = np.zeros(w.shape[1], dtype=np.int64)
        for b in range(wbits):                    # weight bits
            wb = (w >> b) & 1
            pop = (wb & xb[:, None]).sum(axis=0)  # AND + popcount
            part += pop << b                      # shift-add
        acc = (acc << 1) + part                   # shift-accumulate
    return acc


def sidecar_dot(idx, val, x, abits, vbits=None, T=None):
    """Sidecar dot: y[j] = sum_s val[s,j] * x[idx[s,j]], bit-serial over x (MSB first).

    idx: (k, n_outputs) row indices, val: (k, n_outputs) signed ints, x: (n_inputs,) unsigned.
    Each input bit cycle adds the signed slot value when that row's bit is 1, then shifts.
    T: optional sidecar-side shift per column (n_outputs,) >= 0: the finished sum is shifted
    left by T[j] (a second small barrel shifter after the sidecar accumulator). None = off.
    """
    if T is not None:
        T = np.asarray(T, dtype=np.int64)
        assert T.min() >= 0
        return sidecar_dot(idx, val, x, abits, vbits) << T
    vbits = SPEC["outlier"]["weight_bits"] if vbits is None else vbits
    idx = np.asarray(idx, dtype=np.int64)
    val = np.asarray(val, dtype=np.int64)
    x = np.asarray(x, dtype=np.int64)
    assert val.min() >= -(1 << (vbits - 1)) and val.max() < (1 << (vbits - 1))
    assert idx.min() >= 0 and idx.max() < x.shape[0]
    acc = np.zeros(val.shape[1], dtype=np.int64)
    for a in range(abits - 1, -1, -1):            # input bits, MSB first
        xb = (x[idx] >> a) & 1                    # gather slot rows
        acc = (acc << 1) + (val * xb).sum(axis=0)  # add selected values, shift-accumulate
    return acc


def s_max(vbits, sbits=None):
    """Largest shift S: vbits-1 (default), or 2^sbits - 1 for an sbits-wide S (rtl SBITS)."""
    return vbits - 1 if sbits is None else min(vbits - 1, (1 << sbits) - 1)


def merged_width(n_in, wbits, abits, vbits, k, sbits=None, tbits=None):
    """Signed bit width of the merged output (rtl/sidecarcim_top.v YTW).

    sbits: width of S (None = S up to vbits-1, the original formula).
    tbits: width of the sidecar-side shift T (None = no T, the original formula).
    """
    yw = int(np.ceil(np.log2(n_in * ((1 << wbits) - 1) * ((1 << abits) - 1) + 1)))
    scw = vbits + int(np.ceil(np.log2(k * ((1 << abits) - 1) + 1)))
    if tbits is not None:
        scw += (1 << tbits) - 1
    return max(yw + s_max(vbits, sbits) + 1, scw) + 1


def sidecarcim_dot(w, x, idx, val, S, wbits, abits, vbits=None, sbits=None, T=None, tbits=None):
    """SidecarCIM macro output per column: Y = (dcim_dot << S) + (sidecar_dot << T) (raw).

    w: (n_inputs, n_outputs) unsigned, x: (n_inputs,) unsigned, idx/val: (k, n_outputs) slots,
    S: (n_outputs,) shift in [0, s_max(vbits, sbits)]. T: optional sidecar-side shift
    (n_outputs,) in [0, 2^tbits - 1] (None = off, the original macro). Result fits
    merged_width() bits signed.
    """
    vbits = SPEC["outlier"]["weight_bits"] if vbits is None else vbits
    S = np.asarray(S, dtype=np.int64)
    assert S.min() >= 0 and S.max() <= s_max(vbits, sbits)
    if T is not None:
        assert tbits is not None and np.asarray(T).max() <= (1 << tbits) - 1
    y = (dcim_dot(w, x, wbits, abits) << S) + sidecar_dot(idx, val, x, abits, vbits, T)
    yb = merged_width(np.asarray(w).shape[0], wbits, abits, vbits, np.asarray(val).shape[0],
                      sbits, tbits)
    assert y.min() >= -(1 << (yb - 1)) and y.max() < (1 << (yb - 1))
    return y


def _test_dcim(trials, rng):
    n, m = SPEC["array"]["n_inputs"], SPEC["array"]["n_outputs"]
    wb, ab = SPEC["dense"]["weight_bits"], SPEC["dense"]["act_bits"]
    for _ in range(trials):
        w = rng.integers(0, 2**wb, (n, m))
        x = rng.integers(0, 2**ab, n)
        assert np.array_equal(dcim_dot(w, x, wb, ab), x @ w)
    print(f"golden self-test passed ({trials} random cases, {n}x{m}, {wb}b x {ab}b)")


def _test_sidecar(trials, rng):
    n, m = SPEC["array"]["n_inputs"], SPEC["array"]["n_outputs"]
    ab, k = SPEC["dense"]["act_bits"], SPEC["outlier"]["budget_per_output"]
    vb = SPEC["outlier"]["weight_bits"]
    lo, hi = -(1 << (vb - 1)), (1 << (vb - 1)) - 1
    for t in range(trials):
        idx = rng.integers(0, n, (k, m))
        val = rng.integers(lo, hi + 1, (k, m))
        val[:, rng.random(m) < 0.3] = 0           # some unused slots
        if t == 0:
            val[:] = lo                           # extremes
        if t == 1:
            val[:] = hi
        x = rng.integers(0, 2**ab, n)
        if t < 2:
            x[:] = 2**ab - 1
        ref = np.array([sum(int(val[s, j]) * int(x[idx[s, j]]) for s in range(k)) for j in range(m)])
        assert np.array_equal(sidecar_dot(idx, val, x, ab), ref)
    print(f"sidecar self-test passed ({trials} random cases, k={k}, {vb}b values x {ab}b inputs)")


def _test_sidecarcim(trials, rng):
    n, m = SPEC["array"]["n_inputs"], SPEC["array"]["n_outputs"]
    wb, ab = SPEC["dense"]["weight_bits"], SPEC["dense"]["act_bits"]
    k, vb = SPEC["outlier"]["budget_per_output"], SPEC["outlier"]["weight_bits"]
    lo, hi = -(1 << (vb - 1)), (1 << (vb - 1)) - 1
    if (n, wb, ab, k) == (32, 4, 4, 2):           # rtl YTW: 30 b at VB16, 26 b at VB12
        assert merged_width(n, wb, ab, 16, k) == 30 and merged_width(n, wb, ab, 12, k) == 26
    for t in range(trials):
        w = rng.integers(0, 2**wb, (n, m))
        x = rng.integers(0, 2**ab, n)
        idx = rng.integers(0, n, (k, m))
        val = rng.integers(lo, hi + 1, (k, m))
        S = rng.integers(0, vb, m)
        if t < 2:                                 # extremes: dense max, S max, sidecar max/min
            w[:], x[:], S[:], val[:] = 2**wb - 1, 2**ab - 1, vb - 1, (hi if t == 0 else lo)
        ref = np.array([(int(x @ w[:, j]) << int(S[j])) +
                        sum(int(val[s, j]) * int(x[idx[s, j]]) for s in range(k)) for j in range(m)])
        assert np.array_equal(sidecarcim_dot(w, x, idx, val, S, wb, ab), ref)
    print(f"sidecarcim self-test passed ({trials} random cases incl. S={vb - 1} extremes, "
          f"{merged_width(n, wb, ab, vb, k)}-bit signed output)")


def _test_widths(trials, rng, widths=(8, 10, 12, 16)):
    """Sidecar and merged output exact at other slot widths (vbits arg); out-of-range rejected."""
    n, m = SPEC["array"]["n_inputs"], SPEC["array"]["n_outputs"]
    wb, ab = SPEC["dense"]["weight_bits"], SPEC["dense"]["act_bits"]
    k = SPEC["outlier"]["budget_per_output"]
    for vb in widths:
        lo, hi = -(1 << (vb - 1)), (1 << (vb - 1)) - 1
        for t in range(trials):
            w = rng.integers(0, 2**wb, (n, m))
            x = rng.integers(0, 2**ab, n)
            idx = rng.integers(0, n, (k, m))
            val = rng.integers(lo, hi + 1, (k, m))
            S = rng.integers(0, vb, m)
            if t < 2:                             # extremes
                w[:], x[:], S[:], val[:] = 2**wb - 1, 2**ab - 1, vb - 1, (hi if t == 0 else lo)
            ref_s = np.array([sum(int(val[s, j]) * int(x[idx[s, j]]) for s in range(k))
                              for j in range(m)])
            assert np.array_equal(sidecar_dot(idx, val, x, ab, vb), ref_s)
            ref = np.array([(int(x @ w[:, j]) << int(S[j])) + ref_s[j] for j in range(m)])
            assert np.array_equal(sidecarcim_dot(w, x, idx, val, S, wb, ab, vb), ref)
        bad = np.full((k, m), hi + 1)
        try:
            sidecar_dot(np.zeros((k, m), int), bad, np.zeros(n, int), ab, vb)
            raise RuntimeError("out-of-range value accepted")
        except AssertionError:
            pass
    print(f"sidecar width self-test passed (vbits {widths}, {trials} cases each, "
          f"merged {[merged_width(n, wb, ab, v, k) for v in widths]} bits)")


def _test_dense_widths(trials, rng, widths=((8, 4), (6, 4))):
    """Dense core at other (wbits, abits) via explicit args: random, all-max, single bit-planes."""
    n, m = SPEC["array"]["n_inputs"], SPEC["array"]["n_outputs"]
    for wb, ab in widths:
        wm, am = 2**wb - 1, 2**ab - 1
        for t in range(trials):
            w = rng.integers(0, wm + 1, (n, m))
            x = rng.integers(0, am + 1, n)
            if t == 0:
                w[:], x[:] = wm, am               # all max
            assert np.array_equal(dcim_dot(w, x, wb, ab), x @ w)
        y = dcim_dot(np.full((n, m), wm), np.full(n, am), wb, ab)
        assert np.all(y == n * wm * am) and int(y.max()).bit_length() <= wb + ab + 5
        for b in range(wb):                       # weight bit-plane b alone
            assert np.all(dcim_dot(np.full((n, m), 1 << b), np.full(n, am), wb, ab) == n * am << b)
        for a in range(ab):                       # input bit-plane a alone
            assert np.all(dcim_dot(np.full((n, m), wm), np.full(n, 1 << a), wb, ab) == n * wm << a)
        # a too-narrow wbits drops the top weight bit (widths really are used)
        assert not np.array_equal(dcim_dot(np.full((n, m), wm), np.full(n, am), wb - 1, ab),
                                  np.full(m, n * wm * am))
    print(f"dense width self-test passed ((wbits, abits) {list(widths)}, {trials} random cases each"
          f" + all-max + bit-planes)")


def _test_sbits(trials, rng):
    """3-bit S (rtl SBITS=3): S in 0..7, merged width 22 b at 32x8, W4A4, VB12, K=2."""
    n, m = SPEC["array"]["n_inputs"], SPEC["array"]["n_outputs"]
    wb, ab, k, vb = 4, 4, 2, 12
    for v in (8, 10, 12, 16):                     # sbits=None keeps the original formula
        yw = int(np.ceil(np.log2(n * 15 * 15 + 1)))
        scw = v + int(np.ceil(np.log2(k * 15 + 1)))
        assert merged_width(n, wb, ab, v, k) == max(yw + v, scw) + 1
        assert merged_width(n, wb, ab, v, k, 4) >= merged_width(n, wb, ab, v, k, 3)
    assert merged_width(n, wb, ab, vb, k) == 26 and merged_width(n, wb, ab, vb, k, 3) == 22
    assert s_max(vb, 3) == 7 and s_max(vb) == 11 and s_max(vb, 4) == 11
    lo, hi = -(1 << (vb - 1)), (1 << (vb - 1)) - 1
    for t in range(trials):
        w = rng.integers(0, 16, (n, m))
        x = rng.integers(0, 16, n)
        idx = rng.integers(0, n, (k, m))
        val = rng.integers(lo, hi + 1, (k, m))
        S = rng.integers(0, 8, m)
        if t < 2:                                 # extremes: max y = (7200 << 7) + 2*2047*15
            w[:], x[:], S[:], val[:] = 15, 15, 7, (hi if t == 0 else lo)
        y = sidecarcim_dot(w, x, idx, val, S, wb, ab, vb, sbits=3)
        ref = np.array([(int(x @ w[:, j]) << int(S[j])) +
                        sum(int(val[s, j]) * int(x[idx[s, j]]) for s in range(k))
                        for j in range(m)])
        assert np.array_equal(y, ref)
        if t == 0:
            assert np.all(y == 983010) and int(y.max()).bit_length() + 1 <= 22
        if t == 1:
            assert np.all(y == (7200 << 7) + 2 * lo * 15)
    try:                                          # S = 8 is out of range for 3 bits
        sidecarcim_dot(np.zeros((n, m), int), np.zeros(n, int), np.zeros((k, m), int),
                       np.zeros((k, m), int), np.full(m, 8), wb, ab, vb, sbits=3)
        raise RuntimeError("S=8 accepted with sbits=3")
    except AssertionError:
        pass
    print(f"sbits self-test passed (SBITS=3: S 0..7, merged width 22 b, max y 983010, "
          f"{trials} random cases)")


def _test_tshift(trials, rng):
    """Sidecar-side shift T (3 bits): Y = (D << S) + (C << T) exact; T=None = original."""
    n, m = SPEC["array"]["n_inputs"], SPEC["array"]["n_outputs"]
    wb, ab, k, vb, tb = 4, 4, 2, 12, 3
    lo, hi = -(1 << (vb - 1)), (1 << (vb - 1)) - 1
    assert merged_width(n, wb, ab, vb, k) == 26 and merged_width(n, wb, ab, vb, k, tbits=0) == 26
    assert merged_width(n, wb, ab, vb, k, tbits=tb) == 26          # 17 + 7 = 24 < 25
    assert merged_width(n, wb, ab, vb, k, sbits=3, tbits=tb) == 25  # max(21, 24) + 1
    for t in range(trials):
        w = rng.integers(0, 16, (n, m))
        x = rng.integers(0, 16, n)
        idx = rng.integers(0, n, (k, m))
        val = rng.integers(lo, hi + 1, (k, m))
        S = rng.integers(0, 8, m)
        T = rng.integers(0, 1 << tb, m)
        if t < 2:                                 # extremes: T 7, slots at the limits
            w[:], x[:], S[:], T[:], val[:] = 15, 15, 7, 7, (hi if t == 0 else lo)
        y = sidecarcim_dot(w, x, idx, val, S, wb, ab, vb, sbits=3, T=T, tbits=tb)
        ref = np.array([(int(x @ w[:, j]) << int(S[j])) +
                        (sum(int(val[s, j]) * int(x[idx[s, j]]) for s in range(k)) << int(T[j]))
                        for j in range(m)])
        assert np.array_equal(y, ref)
        assert np.array_equal(sidecarcim_dot(w, x, idx, val, S, wb, ab, vb, sbits=3,
                                             T=np.zeros(m, int), tbits=tb),
                              sidecarcim_dot(w, x, idx, val, S, wb, ab, vb, sbits=3))
        if t == 0:
            assert np.all(y == (7200 << 7) + ((2 * hi * 15) << 7))
    print(f"tshift self-test passed (T 0..7: {trials} random cases, extremes, T=0 == original; "
          f"merged width {merged_width(n, wb, ab, vb, k, sbits=3, tbits=tb)} b with SBITS=3)")


def _selftest(trials=200):
    rng = np.random.default_rng(0)
    _test_dcim(trials, rng)
    _test_sidecar(trials, rng)
    _test_sidecarcim(trials, rng)
    _test_widths(60, rng)
    _test_dense_widths(trials, rng)
    _test_sbits(trials, rng)
    _test_dense_widths(trials, rng, widths=((7, 4), (4, 8)))   # W7A4, W4A8 (review Oct 15)
    _test_tshift(trials, rng)


if __name__ == "__main__":
    _selftest()
