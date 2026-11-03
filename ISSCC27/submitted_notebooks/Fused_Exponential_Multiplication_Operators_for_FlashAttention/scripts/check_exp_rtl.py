#!/usr/bin/env python3
"""Check RTL expmul (both modes) and exp_pwl against the bit-exact Python model."""
from __future__ import annotations

import subprocess
import sys

import numpy as np

sys.path.insert(0, __file__.rsplit("scripts", 1)[0] + "model")
from expmul_ref import expmul_fp32, expmul_mi_fp32  # noqa: E402


def main() -> int:
    d = sys.argv[1] if len(sys.argv) > 1 else "."
    rng = np.random.default_rng(20250520)
    n = 5000
    x = (-15.0 * rng.random(n)).astype(np.float32)
    x[:50] = 0.0
    # random V with normal exponents
    e = rng.integers(90, 160, n).astype(np.uint32)
    m = rng.integers(0, 1 << 23, n).astype(np.uint32)
    s = rng.integers(0, 2, n).astype(np.uint32)
    vb = (s << 31) | (e << 23) | m
    with open(f"{d}/exp_in.txt", "w") as f:
        for xi, vi in zip(x.view(np.uint32), vb):
            f.write(f"{xi:08x} {vi:08x}\n")
    subprocess.run(["vvp", "simexp", "+IN=exp_in.txt", "+OUT=exp_out.txt"],
                   check=True, cwd=d, capture_output=True)
    got = np.loadtxt(f"{d}/exp_out.txt", dtype=str)
    g0 = np.array([int(t, 16) for t in got[:, 0]], dtype=np.uint32)
    g1 = np.array([int(t, 16) for t in got[:, 1]], dtype=np.uint32)
    gp = np.array([int(t, 16) for t in got[:, 2]], dtype=np.uint32).view(np.float32)

    e0 = expmul_fp32(x, vb.view(np.float32)).view(np.uint32)
    e1 = expmul_mi_fp32(x, vb.view(np.float32)).view(np.uint32)
    bad0 = int(np.count_nonzero(g0 != e0))
    bad1 = int(np.count_nonzero(g1 != e1))
    ref = np.exp(x.astype(np.float64))
    rel = np.abs(gp.astype(np.float64) - ref) / ref
    print(f"expmul MODE0: {bad0}/{n} mismatches")
    print(f"expmul MODE1: {bad1}/{n} mismatches")
    print(f"exp_pwl     : max rel err {rel.max()*100:.3f}%, mean {rel.mean()*100:.3f}%")
    if bad0:
        i = np.nonzero(g0 != e0)[0][0]
        print(f"  x={x[i]:.6f} xb={x[i].view(np.uint32) if hasattr(x[i],chr(39)+chr(118)+chr(105)+chr(101)+chr(119)+chr(39)) else 0:08x} v={vb[i]:08x} got={g0[i]:08x} exp={e0[i]:08x}")
    if bad1:
        i = np.nonzero(g1 != e1)[0][0]
        print(f"  x={x[i]:.6f} xb={int(x.view(np.uint32)[i]):08x} v={vb[i]:08x} got={g1[i]:08x} exp={e1[i]:08x}")
    return 0 if (bad0 == 0 and bad1 == 0 and rel.max() < 0.01) else 1


if __name__ == "__main__":
    raise SystemExit(main())
