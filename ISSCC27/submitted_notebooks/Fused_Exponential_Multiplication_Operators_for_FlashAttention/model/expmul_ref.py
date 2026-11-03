#!/usr/bin/env python3
"""expmul_ref.py -- bit-exact NumPy model of the paper's ExpMul operator.

Implements Algorithm 3 of Alexandridis et al., arXiv:2505.14314:
    X_hat = Fixed(Clip(X,-15,0))        Q6.10
    S     = X_hat + (X_hat>>1) - (X_hat>>4)
    L     = round(-S/2^10)              (or ceil / trunc, see --mode)
    Out   = Float(S_V, E_V - L, M_V)

The model is used to cross-check the C++ model (src/expmul.hpp) and the RTL
(rtl/fa_expmul.v) bit for bit.

    python model/expmul_ref.py --check results/phase1/expmul_pairs.csv
"""
from __future__ import annotations

import argparse
import csv

import numpy as np

Q_FRAC = 10
Q_ONE = 1 << Q_FRAC
Q_MIN = -15 * Q_ONE


def to_q6_10(x: np.ndarray) -> np.ndarray:
    """Fixed(Clip(x,-15,0)) with round-half-up, in float32 like the hardware."""
    x = np.asarray(x, dtype=np.float32)
    xc = np.where(x <= np.float32(0), x, np.float32(0))       # NaN/positive -> 0
    xc = np.maximum(xc, np.float32(-15))
    s = (xc * np.float32(Q_ONE)).astype(np.float32)          # exact scaling
    r = np.floor(s + np.float32(0.5)).astype(np.int32)
    return np.clip(r, Q_MIN, 0)


def log2exp(xh: np.ndarray, mode: str = "nearest") -> np.ndarray:
    """Integer exponent L with e^x ~ 2^-L."""
    xh = np.asarray(xh, dtype=np.int32)
    s = xh + (xh // 2) - (xh // 16)      # arithmetic >> is floor division
    p = -s                                # >= 0, Q6.10
    if mode == "nearest":
        return (p + Q_ONE // 2) >> Q_FRAC
    if mode == "ceil":
        return (p + Q_ONE - 1) >> Q_FRAC
    if mode == "trunc":
        return p >> Q_FRAC
    raise ValueError(mode)


def shift_fp32(L, vbits: np.ndarray) -> np.ndarray:
    """Float(S_V, E_V - L, M_V); underflow -> +0. Vectorised over L and V."""
    vb = np.asarray(vbits, dtype=np.uint32)
    L = np.asarray(L, dtype=np.int32)
    sign = vb & np.uint32(0x80000000)
    e = ((vb >> np.uint32(23)) & np.uint32(0xFF)).astype(np.int32)
    mant = vb & np.uint32(0x007FFFFF)
    ne = e - L
    under = (e == 0) | (ne <= 0)
    out = (sign | (ne.astype(np.uint32) << np.uint32(23)) | mant)
    out = np.where(under, np.uint32(0), out)
    out = np.where(e == 0xFF, vb, out)          # inf / NaN passthrough
    return out.astype(np.uint32)


def shift_fp32_mi(p, vbits: np.ndarray) -> np.ndarray:
    """Mantissa-interpolating variant: bits(V) - (-x*log2e)*2^23."""
    vb = np.asarray(vbits, dtype=np.uint32)
    D = (np.asarray(p, dtype=np.uint32) << np.uint32(23 - Q_FRAC))
    e = ((vb >> np.uint32(23)) & np.uint32(0xFF)).astype(np.int32)
    mag = vb & np.uint32(0x7FFFFFFF)
    rem = mag - D
    valid = (e != 0) & (e != 0xFF) & (D < mag) & ((rem >> np.uint32(23)) != 0)
    out = (vb & np.uint32(0x80000000)) | rem
    out = np.where(valid, out, np.where(e == 0xFF, vb, np.uint32(0)))
    return out.astype(np.uint32)


def q_residual(x) -> np.ndarray:
    """p = -x*log2e in Q6.10, >= 0."""
    xh = to_q6_10(x)
    return -(xh + (xh // 2) - (xh // 16))


def expmul_mi_fp32(x, v):
    out = shift_fp32_mi(q_residual(x), np.asarray(v, np.float32).view(np.uint32))
    return out.view(np.float32)


def shift_bf16(L, vbits: np.ndarray) -> np.ndarray:
    vb = np.asarray(vbits, dtype=np.uint32) & np.uint32(0xFFFF)
    L = np.asarray(L, dtype=np.int32)
    sign = vb & np.uint32(0x8000)
    e = ((vb >> np.uint32(7)) & np.uint32(0xFF)).astype(np.int32)
    mant = vb & np.uint32(0x007F)
    ne = e - L
    under = (e == 0) | (ne <= 0)
    out = sign | (ne.astype(np.uint32) << np.uint32(7)) | mant
    out = np.where(under, np.uint32(0), out)
    out = np.where(e == 0xFF, vb, out)
    return out.astype(np.uint32)


def expmul_fp32(x, v, mode: str = "nearest"):
    """e^x * v as float32, via the ExpMul datapath (returns float32 values)."""
    vb = np.asarray(v, dtype=np.float32).view(np.uint32)
    L = log2exp(to_q6_10(x), mode)
    out = shift_fp32(L, vb)
    return out.view(np.float32)


def weight_from_L(L) -> np.ndarray:
    L = np.asarray(L, dtype=np.int32)
    return np.ldexp(np.ones_like(L, dtype=np.float64), -L)


# --------------------------------------------------------------------------
#  verification against the C++ dump
# --------------------------------------------------------------------------
def check(pairs_csv: str) -> int:
    xs, vbits, on, oc, om, ln, lc = [], [], [], [], [], [], []
    with open(pairs_csv, newline="") as f:
        for row in csv.DictReader(f):
            xs.append(float(row["x"]))
            vbits.append(int(row["v_bits"], 16))
            on.append(int(row["out_bits_nearest"], 16))
            oc.append(int(row["out_bits_ceil"], 16))
            om.append(int(row["out_bits_mi"], 16))
            ln.append(int(row["L_nearest"]))
            lc.append(int(row["L_ceil"]))
    x = np.asarray(xs, dtype=np.float32)
    vb = np.asarray(vbits, dtype=np.uint32)
    xh = to_q6_10(x)
    ok = True
    for mode, L_ref, out_ref, tag in (
        ("nearest", np.asarray(ln), np.asarray(on), "exp_only_near"),
        ("ceil", np.asarray(lc), np.asarray(oc), "exp_only_ceil"),
    ):
        L = log2exp(xh, mode)
        out = shift_fp32(L, vb)
        nL = int(np.count_nonzero(L != L_ref))
        nO = int(np.count_nonzero(out != out_ref))
        print(f"[{tag:13s}] rows={len(x)}  L mismatches={nL}  out-bit mismatches={nO}")
        ok &= (nL == 0 and nO == 0)
    mi = shift_fp32_mi(q_residual(x), vb)
    nMI = int(np.count_nonzero(mi != np.asarray(om)))
    print(f"[mantissa_int ] rows={len(x)}  out-bit mismatches={nMI}")
    ok &= (nMI == 0)
    # scalar spot checks
    spot = [(0.0, 1.0), (-1.0, 2.5), (-15.0, 1.0), (-0.3, -1.0), (-7.77, 3.0)]
    for sx, sv in spot:
        xa = np.array([sx], dtype=np.float32)
        va = np.array([sv], dtype=np.float32)
        got = float(expmul_fp32(xa, va)[0])
        L = int(log2exp(to_q6_10(xa))[0])
        print(f"  x={sx:7.3f} v={sv:6.2f}  L={L:2d}  out={got:.9g}  "
              f"exact={np.exp(sx) * sv:.9g}  ratio={got / (np.exp(sx) * sv):.4f}")
    print("C++/Python bit-exact:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", metavar="PAIRS_CSV")
    a = ap.parse_args()
    if a.check:
        return check(a.check)
    # default: print the weight table that the RTL is verified against
    x = np.linspace(-15, 0, 31, dtype=np.float32)
    L = log2exp(to_q6_10(x))
    print("      x      x_hat   L   2^-L        e^x        ratio")
    for xi, Li in zip(x, L):
        print(f"{xi:8.3f} {int(to_q6_10(np.float32(xi))):7d} {int(Li):3d} "
              f"{2.0 ** (-int(Li)):10.3e} {np.exp(float(xi)):10.3e} "
              f"{2.0 ** (-int(Li)) / np.exp(float(xi)):8.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
