#!/usr/bin/env python3
"""Generate random FP32 operand vectors and check the RTL mul/add results."""
from __future__ import annotations

import subprocess
import sys

import numpy as np


def gen(n: int, seed: int = 20250520) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    # signs, exponents in a safe normal range, random mantissas
    ea = rng.integers(110, 145, n).astype(np.uint32)
    eb = rng.integers(110, 145, n).astype(np.uint32)
    ma = rng.integers(0, 1 << 23, n).astype(np.uint32)
    mb = rng.integers(0, 1 << 23, n).astype(np.uint32)
    sa = rng.integers(0, 2, n).astype(np.uint32)
    sb = rng.integers(0, 2, n).astype(np.uint32)
    a = (sa << 31) | (ea << 23) | ma
    b = (sb << 31) | (eb << 23) | mb
    return a, b


def ref(a: np.ndarray, b: np.ndarray):
    fa = a.view(np.float32)
    fb = b.view(np.float32)
    mul = (fa * fb).view(np.uint32)
    add = (fa + fb).view(np.uint32)
    return mul, add


def main() -> int:
    outdir = sys.argv[1] if len(sys.argv) > 1 else "."
    a, b = gen(4000)
    with open(f"{outdir}/vec_in.txt", "w") as f:
        for x, y in zip(a, b):
            f.write(f"{x:08x} {y:08x}\n")
    cmd = ["vvp", "sim", "+IN=vec_in.txt", "+OUT=vec_out.txt"]
    subprocess.run(cmd, check=True, cwd=outdir, capture_output=True)
    got = np.loadtxt(f"{outdir}/vec_out.txt", dtype=str)
    gm = np.array([int(x, 16) for x in got[:, 0]], dtype=np.uint32)
    ga = np.array([int(x, 16) for x in got[:, 1]], dtype=np.uint32)
    em, ea = ref(a, b)
    bad_m = int(np.count_nonzero(gm != em))
    bad_a = int(np.count_nonzero(ga != ea))
    print(f"mul: {bad_m}/{len(a)} mismatches   add: {bad_a}/{len(a)} mismatches")
    if bad_m:
        idx = np.nonzero(gm != em)[0][:5]
        for i in idx:
            print(f"  mul {a[i]:08x} * {b[i]:08x} -> {gm[i]:08x} (exp {em[i]:08x})")
    if bad_a:
        idx = np.nonzero(ga != ea)[0][:5]
        for i in idx:
            print(f"  add {a[i]:08x} + {b[i]:08x} -> {ga[i]:08x} (exp {ea[i]:08x})")
    return 0 if (bad_m == 0 and bad_a == 0) else 1


if __name__ == "__main__":
    raise SystemExit(main())
