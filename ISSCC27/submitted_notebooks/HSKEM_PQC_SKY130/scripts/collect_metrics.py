"""Collect ORFS metrics for every design-space point into one CSV.

Cycle counts come from the RTL simulations (results/sim/*.log), so the
derived latency numbers combine measured post-route timing with
simulation-measured cycles per operation.

SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import csv
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
ASIC = ROOT / "results" / "asic"
SIM = ROOT / "results" / "sim"


def sim_cycles() -> dict:
    cyc = {}
    for name, key in (("ntt_dualport", "ntt_dp"), ("ntt_singleport", "ntt_sp")):
        m = re.search(r"cycles_fwd=(\d+) cycles_inv=(\d+)", (SIM / f"{name}.log").read_text())
        cyc[key] = {"op": "NTT forward", "cycles": int(m[1]), "cycles_inv": int(m[2])}
    for name, key in (("keccak_round", "keccak_r1"), ("keccak_serial", "keccak_s7")):
        m = re.search(r"cycles=(\d+)", (SIM / f"{name}.log").read_text())
        cyc[key] = {"op": "Keccak-f[1600]", "cycles": int(m[1])}
    # the macro-store NTT runs the same controller as the single-port model (one-cycle synchronous read)
    cyc["ntt_macro"] = dict(cyc["ntt_sp"])
    # design-iteration variants (Section 7), simulated by scripts/run_sim_opt.sh
    for name, key in (("opt_b1_w12", "ntt_opt_b1_w12"), ("opt_pipe_w12", "ntt_opt_pipe_w12")):
        log = ROOT / "results" / "sim_opt" / f"{name}.log"
        if log.exists():
            m = re.search(r"cycles_fwd=(\d+) cycles_inv=(\d+)", log.read_text())
            cyc[key] = {"op": "NTT forward", "cycles": int(m[1]), "cycles_inv": int(m[2])}
    if "ntt_opt_pipe_w12" in cyc:     # same controller, macro store
        cyc["ntt_opt_pipe_macro"] = dict(cyc["ntt_opt_pipe_w12"])
    return cyc


def reg2reg_slack(run: pathlib.Path) -> float | None:
    """Worst register-to-register setup slack from 6_finish.rpt.

    The design-level WNS can be set by the I/O budget assumed in the SDC
    (e.g. the Keccak wrapper's combinational lane_idx -> lane_rdata path), so
    the core's own speed is compared on reg-to-reg paths only.
    """
    hits = list(run.glob("reports/**/6_finish.rpt"))
    if not hits:
        return None
    txt = hits[0].read_text()
    sec = txt.split("report_checks -path_delay max reg to reg", 1)
    if len(sec) < 2:
        return None
    m = re.search(r"(-?[\d.]+)\s+slack \((?:MET|VIOLATED)\)", sec[1])
    return float(m[1]) if m else None


def load_report(run: pathlib.Path) -> dict:
    d = {}
    # 5_2_route.json holds one block per detailed-route pass (ORFS reroutes
    # after antenna repair); json.loads keeps the last value = final pass.
    for name in ("5_2_route.json", "6_report.json"):
        hits = list(run.glob(f"logs/**/{name}"))
        if hits:
            d.update(json.loads(hits[0].read_text()))
    return d


def main() -> None:
    cyc = sim_cycles()
    rows = []
    for run in sorted(p for p in ASIC.iterdir() if p.is_dir()):
        # exact names only: suffixed experiment dirs (e.g. *_ant10) are reviewed separately
        m = re.fullmatch(r"(ntt_dp|ntt_sp|ntt_macro|keccak_r1|keccak_s7|ntt_opt_b1_w12|ntt_opt_pipe_w12|ntt_opt_pipe_macro)_(\d+(?:p\d+)?)ns",
                         run.name)
        if not m:
            continue
        variant, clk = m[1], float(m[2].replace("p", "."))
        # skip runs still in progress (no status) or without a finished layout
        if not (run / "status.txt").exists() or not list(run.glob("logs/**/6_report.json")):
            continue
        rc, secs = (run / "status.txt").read_text().split()
        r = load_report(run)
        g = lambda k: r.get(k)  # noqa: E731
        fmax = g("finish__timing__fmax")
        r2r = reg2reg_slack(run)
        row = {
            "variant": variant, "clk_target_ns": clk, "flow_rc": int(rc), "runtime_s": int(secs),
            "die_area_um2": g("finish__design__die__area"),
            "cell_area_um2": g("finish__design__instance__area__stdcell"),
            "seq_area_um2": g("finish__design__instance__area__class:sequential_cell"),
            "cells": g("finish__design__instance__count__stdcell"),
            "flops": g("finish__design__instance__count__class:sequential_cell"),
            "util": g("finish__design__instance__utilization"),
            "wns_ns": g("finish__timing__setup__ws"),
            "tns_ns": g("finish__timing__setup__tns"),
            "hold_wns_ns": g("finish__timing__hold__ws"),
            "fmax_design_mhz": fmax / 1e6 if fmax else None,
            "reg2reg_slack_ns": r2r,
            # core speed: period minus worst reg-to-reg slack
            "fmax_mhz": 1e3 / (clk - r2r) if r2r is not None else (fmax / 1e6 if fmax else None),
            # vectorless OpenSTA estimate at the target clock (default activity)
            "power_mw_vectorless": (g("finish__power__total") or 0) * 1e3 or None,
            "drc_errors": g("detailedroute__route__drc_errors"),
            "antenna_violating_nets": g("detailedroute__antenna__violating__nets"),
            **{k: v for k, v in cyc[variant].items()},
        }
        if row["fmax_mhz"]:
            row["latency_us_at_fmax"] = row["cycles"] / row["fmax_mhz"]
            if row["cell_area_um2"]:
                # area-time product (mm^2 * us): lower is better
                row["at_product"] = row["cell_area_um2"] / 1e6 * row["latency_us_at_fmax"]
        rows.append(row)

    out = ROOT / "results" / "dse_metrics.csv"
    keys = sorted({k for r in rows for k in r}, key=lambda k: list(rows[0]).index(k) if k in rows[0] else 99)
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)
    for r in rows:
        print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()})
    print("->", out)


if __name__ == "__main__":
    main()
