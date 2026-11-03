"""Arrival-skew records of every two-pin hazard (glitchscope/skew.py) for the section 8 plots.

    python scripts/skew_study.py <liberty> [bench ...] [--vectors N]   -> data/bench/skew_<bench>.csv
"""
import argparse
import csv
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from glitchscope.liberty import LibertyDelayProvider, parse_liberty_file  # noqa: E402
from glitchscope.m2model import M2Model  # noqa: E402
from glitchscope.model import ps_to_fs  # noqa: E402
from glitchscope.sim import PulseSimulator  # noqa: E402
from glitchscope.skew import collect_skew  # noqa: E402
from glitchscope.verilog import read_verilog  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("lib")
    ap.add_argument("benches", nargs="*", default=["mul4", "rca8"])
    ap.add_argument("--vectors", type=int, default=300)
    a = ap.parse_args()
    dp = LibertyDelayProvider(parse_liberty_file(a.lib))
    for b in a.benches:
        net = read_verilog(ROOT / f"bench/netlists/{b}.v")
        rnd = random.Random(7)
        vecs = [{p: rnd.randint(0, 1) for p in net.primary_inputs} for _ in range(a.vectors)]
        sim = PulseSimulator(net, dp, "M2", r_filter=M2Model(), default_input_slew_fs=ps_to_fs(40), engine="python")
        rows = collect_skew(sim, vecs, dict(net.initial_inputs))
        out = ROOT / f"data/bench/skew_{b}.csv"
        with open(out, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
        print(b, len(rows), "hazard records ->", out.relative_to(ROOT))


if __name__ == "__main__":
    main()
