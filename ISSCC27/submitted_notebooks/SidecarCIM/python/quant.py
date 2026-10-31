"""Uniform unsigned quantization with zero point, plus integer zero-point correction.

Real value ~= scale * (q - zp), q in [0, 2^bits - 1] (unsigned, as the dense core needs).
Choice: weights use per-output-channel scale/zp (min/max over the input axis of a
(n_inputs, n_outputs) matrix); activations use one per-tensor scale/zp (min/max over all values).
The signed integer dot product is recovered from the unsigned core result by:
    sum((w - zw)(x - zx)) = core_dot(w, x) - zx*sum(w) - zw*sum(x) + N*zw*zx
"""
import numpy as np

from golden import SPEC, dcim_dot, sidecar_dot


def qmax(bits):
    """Largest unsigned code for a bit width."""
    return (1 << bits) - 1


def range_params(lo, hi, bits):
    """Scale and zero point for a real range [lo, hi] (widened to contain 0)."""
    lo = np.minimum(np.asarray(lo, dtype=np.float64), 0.0)   # range must contain 0 so zp is exact
    hi = np.maximum(np.asarray(hi, dtype=np.float64), 0.0)
    scale = (hi - lo) / qmax(bits)
    scale = np.where(scale > 0, scale, 1.0)  # all-zero channel: any scale works
    zp = np.clip(np.round(-lo / scale), 0, qmax(bits)).astype(np.int64)
    return scale, zp


def quant_params(t, bits, axis=None):
    """Min/max scale and zero point. axis=None: per tensor; axis=0: per column of (in, out)."""
    t = np.asarray(t, dtype=np.float64)
    return range_params(t.min(axis=axis), t.max(axis=axis), bits)


def quantize_with(t, scale, zp, bits):
    """Quantize with given (broadcastable) params; clips out-of-range values."""
    q = np.round(np.asarray(t, dtype=np.float64) / scale) + zp
    return np.clip(q, 0, qmax(bits)).astype(np.int64)


def quantize(t, bits, axis=None):
    """Return (q, scale, zp); q is int64 in [0, 2^bits - 1]."""
    scale, zp = quant_params(t, bits, axis)
    s, z = (scale, zp) if axis is None else (np.expand_dims(scale, axis), np.expand_dims(zp, axis))
    q = np.clip(np.round(np.asarray(t, dtype=np.float64) / s) + z, 0, qmax(bits))
    return q.astype(np.int64), scale, zp


def dequantize(q, scale, zp):
    """Back to real values."""
    return scale * (np.asarray(q, dtype=np.int64) - zp)


def signed_dot(wq, xq, zw, zx, wbits, abits):
    """Signed integer dot sum((w-zw)(x-zx)) from the unsigned DCIM core plus corrections.

    wq: (n_in, n_out) codes, xq: (n_in,) codes, zw: scalar or (n_out,), zx: scalar. Integer only.
    """
    wq = np.asarray(wq, dtype=np.int64)
    xq = np.asarray(xq, dtype=np.int64)
    zw = np.asarray(zw, dtype=np.int64)
    zx = np.int64(zx)
    n = wq.shape[0]
    core = dcim_dot(wq, xq, wbits, abits)             # hardware part
    return core - zx * wq.sum(axis=0) - zw * xq.sum() + n * zw * zx


def sidecar_signed(idx, val, xq, zx, abits, vbits=None):
    """Signed sidecar term sum_s val*(x[idx]-zx) = sidecar_dot - zx*sum(val). Integer only.

    vbits: slot value width to enforce (default: spec outlier.weight_bits).
    """
    val = np.asarray(val, dtype=np.int64)
    return sidecar_dot(idx, val, xq, abits, vbits) - np.int64(zx) * val.sum(axis=0)


# ---------------- self-tests ----------------

def _test_qmax():
    assert qmax(4) == 15 and qmax(8) == 255
    print("  qmax ok")


def _test_quantize(bits, rng):
    t = rng.normal(0, 1, (SPEC["array"]["n_inputs"], SPEC["array"]["n_outputs"]))
    for axis in (None, 0):
        q, s, z = quantize(t, bits, axis)
        assert q.min() >= 0 and q.max() <= qmax(bits)
        err = np.abs(dequantize(q, s, z) - t)
        assert np.all(err <= s / 2 + 1e-12)          # half-step bound (no clipping by design)
    q, s, z = quantize(np.zeros(5), bits)            # degenerate input
    assert np.all(dequantize(q, s, z) == 0)
    print(f"  quantize/dequantize ok ({bits}b, per-tensor and per-channel)")


def _test_quant_params(bits):
    s, z = quant_params(np.array([-1.0, 3.0]), bits)
    assert np.isclose(s, 4.0 / qmax(bits)) and z == round(1.0 / s)
    s, z = quant_params(np.array([2.0, 5.0]), bits)   # positive only -> zp 0
    assert z == 0
    print(f"  quant_params ok ({bits}b)")


def _test_signed_dot(wbits, abits, rng, trials=500):
    n, m = SPEC["array"]["n_inputs"], SPEC["array"]["n_outputs"]
    for _ in range(trials):
        wq = rng.integers(0, qmax(wbits) + 1, (n, m))
        xq = rng.integers(0, qmax(abits) + 1, n)
        zw = rng.integers(0, qmax(wbits) + 1, m)
        zx = rng.integers(0, qmax(abits) + 1)
        ref = (xq - zx) @ (wq - zw[None, :])
        assert np.array_equal(signed_dot(wq, xq, zw, zx, wbits, abits), ref)
    print(f"  signed_dot identity exact ({trials} cases, {n}x{m}, {wbits}b x {abits}b)")


def _test_end_to_end(bits, rng, trials=200):
    """Quantized float matmul equals scale * signed_dot (float rounding only)."""
    n, m = SPEC["array"]["n_inputs"], SPEC["array"]["n_outputs"]
    for _ in range(trials):
        w = rng.normal(0, 1, (n, m))
        x = rng.normal(0.5, 1, n)
        wq, sw, zw = quantize(w, bits, axis=0)
        xq, sx, zx = quantize(x, bits)
        y_int = sw * sx * signed_dot(wq, xq, zw, zx, bits, bits)
        y_flt = dequantize(xq, sx, zx) @ dequantize(wq, sw, zw)
        assert np.allclose(y_int, y_flt, rtol=1e-9, atol=1e-9)
    print(f"  end-to-end dequant match ok ({trials} cases, {bits}b)")


def _test_range_and_with(bits, rng):
    t = rng.normal(0, 1, (6, 4))
    q, s, z = quantize(t, bits, axis=0)
    assert np.array_equal(quantize_with(t, s, z, bits), q)
    s2, z2 = range_params(0.5 * t.min(axis=0), 0.5 * t.max(axis=0), bits)   # clipped range
    q2 = quantize_with(t, s2, z2, bits)
    assert q2.min() >= 0 and q2.max() <= qmax(bits) and np.all(s2 < s)
    print(f"  range_params / quantize_with ok ({bits}b)")


def _test_sidecar_signed(abits, rng, trials=200):
    n, m = SPEC["array"]["n_inputs"], SPEC["array"]["n_outputs"]
    k, vb = SPEC["outlier"]["budget_per_output"], SPEC["outlier"]["weight_bits"]
    for _ in range(trials):
        idx = rng.integers(0, n, (k, m))
        val = rng.integers(-(1 << (vb - 1)), 1 << (vb - 1), (k, m))
        xq = rng.integers(0, qmax(abits) + 1, n)
        zx = rng.integers(0, qmax(abits) + 1)
        ref = ((xq[idx] - zx) * val).sum(axis=0)
        assert np.array_equal(sidecar_signed(idx, val, xq, zx, abits), ref)
        v8 = np.clip(val, -128, 127)                  # narrower slots, enforced width
        ref8 = ((xq[idx] - zx) * v8).sum(axis=0)
        assert np.array_equal(sidecar_signed(idx, v8, xq, zx, abits, 8), ref8)
    print(f"  sidecar_signed exact ({trials} cases, k={k}, also vbits=8)")


def _selftest():
    rng = np.random.default_rng(1)
    wb, ab = SPEC["dense"]["weight_bits"], SPEC["dense"]["act_bits"]
    hi = 2 * max(wb, ab)                              # wider mode (uniform 8-bit)
    _test_qmax()
    for bits in (wb, hi):
        _test_quant_params(bits)
        _test_quantize(bits, rng)
        _test_end_to_end(bits, rng)
    _test_signed_dot(wb, ab, rng)
    _test_signed_dot(hi, hi, rng)
    _test_range_and_with(wb, rng)
    _test_sidecar_signed(ab, rng)
    print("quant self-test passed")


if __name__ == "__main__":
    _selftest()
