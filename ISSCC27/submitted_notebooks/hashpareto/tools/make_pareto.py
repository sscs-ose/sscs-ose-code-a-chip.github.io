#!/usr/bin/env python3
"""Rebuild results/pareto.csv from measured metrics + measured cycles.

A1 fix: throughput and energy/hash are derived from *measured* cycles per block
(data/cycles.csv), not the closed-form 64/UNROLL. The vectorless STA power is
kept but labelled as a relative estimate.

Columns
  unroll, clock_period_ns, area_um2, cells, power_W,
  cycles_per_block,
  throughput_Mhash_s,            # f / cycles_per_block, at the run's own clock
  energy_per_hash_nJ,            # power_W * cycles_per_block / f
  model_cycles_per_block,        # legacy 64/U, kept for comparison only
  model_throughput_Mhash_s,
  model_energy_per_hash_nJ,
  fmax_est_worst_mhz, fmax_est_tt_mhz,
  setup_ws_worst_ns, setup_ws_worst_corner

Usage: python3 tools/make_pareto.py [pareto.csv]
"""
import csv
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(path):
    with open(path) as f:
        return {int(r["unroll"]): r for r in csv.DictReader(f)}


def main():
    met = load(os.path.join(ROOT, "results", "metrics.csv"))
    cyc = load(os.path.join(ROOT, "results", "cycles.csv"))
    rows = []
    for u in sorted(met):
        m = met[u]
        c = cyc.get(u, {})
        period = float(m["clock_period_ns"])          # ns
        freq = 1e9 / period                            # Hz
        pwr = float(m["power_W"])
        cpb = float(c["cycles_per_block"])
        model_cpb = 64.0 / u
        row = {
            "unroll": u,
            "clock_period_ns": period,
            "area_um2": float(m["area_stdcell_um2"]),
            "cells": int(m["cells_stdcell"]),
            "power_W": pwr,
            "cycles_per_block": cpb,
            "throughput_Mhash_s": freq / cpb / 1e6,
            "energy_per_hash_nJ": pwr * cpb / freq * 1e9,
            "model_cycles_per_block": model_cpb,
            "model_throughput_Mhash_s": freq / model_cpb / 1e6,
            "model_energy_per_hash_nJ": pwr * model_cpb / freq * 1e9,
            "fmax_est_worst_mhz": m.get("fmax_est_worst_mhz", ""),
            "fmax_est_tt_mhz": m.get("fmax_est_tt_mhz", ""),
            "setup_ws_worst_ns": m.get("setup_ws_worst_ns", ""),
            "setup_ws_worst_corner": m.get("setup_ws_worst_corner", ""),
        }
        rows.append(row)
    rows.sort(key=lambda r: r["unroll"])

    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        ROOT, "results", "pareto.csv")
    cols = list(rows[0].keys())
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    for r in rows:
        print("U{unroll:<2d} clk={clock_period_ns:>5}ns cpb={cycles_per_block:>5} "
              "thr={throughput_Mhash_s:6.3f}M/s en={energy_per_hash_nJ:6.3f}nJ "
              "(model thr={model_throughput_Mhash_s:6.3f} en={model_energy_per_hash_nJ:6.3f})"
              .format(**r))
    print("wrote", out)


if __name__ == "__main__":
    main()
