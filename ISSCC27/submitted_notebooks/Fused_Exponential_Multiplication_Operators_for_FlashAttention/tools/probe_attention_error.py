"""Operator -> attention error transfer, both ExpMul variants (numpy probe)."""
import numpy as np
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "model"))
from expmul_ref import expmul_mi_fp32, expmul_fp32

rng = np.random.default_rng(0)

for d, N, scale in [(64, 128, 1.0), (64, 512, 1.0), (64, 128, 2.0)]:
    q = rng.standard_normal((N, d)) * scale
    k = rng.standard_normal((N, d))
    v = rng.standard_normal((N, d))
    s = (q @ k.T) / np.sqrt(d)
    m = s.max(-1, keepdims=True)
    x = (s - m).astype(np.float32)
    p = np.exp(s - m)
    ref = (p @ v) / p.sum(-1, keepdims=True)
    peak = (p.max(-1) / p.sum(-1)).mean()
    for name, fn in (("exponent-only", lambda a: expmul_fp32(a, np.ones_like(a)).astype(np.float64)),
                     ("mantissa-int", lambda a: expmul_mi_fp32(a, np.ones_like(a)).astype(np.float64))):
        w = fn(x)
        got = (w @ v) / w.sum(-1, keepdims=True)
        err = got - ref
        l2 = np.linalg.norm(err, axis=1) / (np.linalg.norm(ref, axis=1) + 1e-12)
        print(f"d={d:2d} N={N:3d} scale={scale} {name:13s}: "
              f"row-rel-L2 mean={l2.mean():.4f} p95={np.percentile(l2, 95):.4f} | peak w={peak:.3f}")
    print()
