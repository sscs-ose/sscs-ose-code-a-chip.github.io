"""Summarize tb/decaps_timeline.sv: keeps the first valid decapsulation of each chip (the run whose length equals the
latency that the testbench reports) and writes results/system_sim/decaps_timeline.json.

usage: collect_timeline.py <hskem1.tl> <hskem2.tl>
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]


def read(path: str) -> dict:
    text = pathlib.Path(path).read_text(errors="replace")
    assert "TB_TRUSTEDGE_SPI_RESULT: ALL PASS" in text
    cycles = int(re.search(r"U1 Decaps busy latency valid/implicit-rejection=(\d+)", text)[1])
    ends = {int(r): int(t) for r, t in re.findall(r"TIMELINE_END run=(\d+) t=(\d+)", text)}
    run = min(r for r, t in ends.items() if t == cycles)
    seg = [dict(t=int(t), ntt=int(n), inv=int(i), sponge=int(s), perm=int(p))
           for t, n, i, s, p in re.findall(rf"TIMELINE run={run} t=(\d+) ntt=(\d) inv=(\d) sponge=(\d) perm=(\d)", text)]
    return {"cycles": cycles, "segments": seg}


def main() -> None:
    out = {"source": "tb/decaps_timeline.sv in the full-system testbench", "hskem1": read(sys.argv[1]), "hskem2": read(sys.argv[2])}
    (ROOT / "results/system_sim/decaps_timeline.json").write_text(json.dumps(out, separators=(",", ":")) + "\n")
    print({k: (out[k]["cycles"], len(out[k]["segments"])) for k in ("hskem1", "hskem2")})


if __name__ == "__main__":
    main()
