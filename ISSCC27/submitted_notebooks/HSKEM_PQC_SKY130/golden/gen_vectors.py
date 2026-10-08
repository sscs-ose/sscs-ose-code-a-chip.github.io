"""Generate hex test vectors for the RTL testbenches from the golden model.

SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import argparse
import pathlib
import random

import mlkem_ref as ref


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="../vectors")
    ap.add_argument("--ntt", type=int, default=200, help="random NTT polynomials")
    ap.add_argument("--keccak", type=int, default=200, help="random Keccak states")
    ap.add_argument("--seed", type=int, default=2027)
    ap.add_argument("--more-corners", action="store_true",
                    help="also alternating 0 / q-1 patterns, every coefficient +-1, and the first and last coefficient set")
    args = ap.parse_args()

    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.seed)

    # Corner cases first, then uniform random coefficients in [0, q).
    polys = [[0] * 256, [ref.Q - 1] * 256, [1] + [0] * 255, list(range(256))]
    if args.more_corners:
        polys += [[0, ref.Q - 1] * 128, [ref.Q - 1, 0] * 128, [rng.choice((1, ref.Q - 1)) for _ in range(256)],
                  [ref.Q - 1] + [0] * 254 + [ref.Q - 1], [0] * 255 + [ref.Q - 1]]
    polys += [[rng.randrange(ref.Q) for _ in range(256)] for _ in range(args.ntt)]

    with open(out / "ntt_in.hex", "w") as fi, \
         open(out / "ntt_fwd.hex", "w") as ff, \
         open(out / "ntt_inv.hex", "w") as fv:
        for p in polys:
            for c in p:
                fi.write(f"{c:04x}\n")
            for c in ref.ntt(p):
                ff.write(f"{c:04x}\n")
            for c in ref.intt(p):
                fv.write(f"{c:04x}\n")

    states = [[0] * 25, [(1 << 64) - 1] * 25]
    states += [[rng.getrandbits(64) for _ in range(25)] for _ in range(args.keccak)]
    with open(out / "keccak_in.hex", "w") as fi, open(out / "keccak_out.hex", "w") as fo:
        for s in states:
            fi.write(f"{ref.lanes_to_int(s):0400x}\n")
            fo.write(f"{ref.lanes_to_int(ref.keccak_f1600(s)):0400x}\n")

    (out / "counts.vh").write_text(
        f"`define N_NTT {len(polys)}\n`define N_KECCAK {len(states)}\n")
    print(f"ntt={len(polys)} keccak={len(states)} -> {out.resolve()}")


if __name__ == "__main__":
    main()
