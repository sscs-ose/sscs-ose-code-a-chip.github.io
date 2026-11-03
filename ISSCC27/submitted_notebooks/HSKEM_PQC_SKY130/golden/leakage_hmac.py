"""Fixed-vs-random TVLA on simulated leakage of the session HMAC (tb/tb_hmac_leak.sv).

Step 1 (`gen`): write hmac_in.hex -- one fixed 256-bit key or a fresh random key per trace, interleaved at random,
each with a fresh random 28-byte message (the frame message D||E||C||P, which an attacker can observe or choose),
plus the class labels. Step 2 (`analyze`): check every digest of the simulation against Python's hmac module, then
run the same noise model, Welch's t-test and negative control as golden/leakage.py.

The traces are a register-transition *model* from RTL simulation, not measured power.

SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import pathlib
import random

import leakage


def gen(out: pathlib.Path, n: int, seed: int) -> None:
    rng = random.Random(seed)
    fixed = rng.getrandbits(256)
    labels = [rng.randrange(2) for _ in range(n)]  # 0 = fixed key, 1 = random key
    with open(out / "hmac_in.hex", "w") as f:
        for lab in labels:
            key = fixed if lab == 0 else rng.getrandbits(256)
            msg = rng.getrandbits(224) << 32          # 28 message bytes, left-aligned in the 256-bit port
            f.write(f"{key:064x}\n{msg:064x}\n")
    (out / "leak_labels.json").write_text(json.dumps({"labels": labels, "runs_per_trace": 1}))
    (out / "hmac_counts.vh").write_text(f"`define N_HMAC {n}\n")


def check_digests(out: pathlib.Path) -> int:
    v = [int(x, 16) for x in (out / "hmac_in.hex").read_text().split()]
    d = (out / "hmac_digests.txt").read_text().split()
    assert len(d) * 2 == len(v), "digest count mismatch"
    for i, dig in enumerate(d):
        key = v[2 * i].to_bytes(32, "big")
        msg = v[2 * i + 1].to_bytes(32, "big")[:28]
        ref = hmac.new(key, msg, hashlib.sha256).hexdigest()
        assert dig.lower() == ref, f"trace {i}: RTL digest differs from Python's hmac"
    return len(d)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["gen", "analyze"])
    ap.add_argument("--out", default="../results/leakage_hmac")
    ap.add_argument("-n", type=int, default=2000)
    ap.add_argument("--sigma", type=float, default=4.0)
    ap.add_argument("--seed", type=int, default=11)
    a = ap.parse_args()
    o = pathlib.Path(a.out); o.mkdir(parents=True, exist_ok=True)
    if a.step == "gen":
        gen(o, a.n, a.seed)
    else:
        k = check_digests(o)
        res = leakage.analyze(o, a.sigma, a.seed)
        res["digests_checked_against_python_hmac"] = k
        (o / "tvla_summary.json").write_text(json.dumps(res, indent=2))
        print(res)
