"""Process / voltage / temperature robustness of glitch energy and of the automatic fix.

For each SKY130 HD timing corner (Liberty from the PDK), the 16x16 multiplier of
section 10 is simulated in three versions -- the original register placement, the
timing-driven retiming and the placement GlitchScope returns, both chosen at the
typical corner (data/glitchfix/mul16_r) -- on the same random stimulus at a clock of
1.25x the original's critical path *at that corner*.  Reported per corner: energy per
cycle split into logic (functional / glitch) and flip-flops + clock tree, the critical
path, and the saving of each placement.

M2 pulse filtering uses the typical-corner SPICE calibration at every corner (its
rejection threshold is normalised to each gate's own delay, r = w / t_pd).

    python scripts/pvt_study.py <PDK lib dir> [corner ...]      -> data/pvt/pvt.json
    python scripts/pvt_study.py <PDK lib dir> --compare-calibration ss_n40C_1v28   -> data/pvt/corner_calibration.json
"""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from glitchscope.optimize import GlitchFix  # noqa: E402

CORNERS = ["tt_025C_1v80", "tt_100C_1v80", "ss_100C_1v60", "ff_n40C_1v95", "ff_100C_1v95",
           "ss_n40C_1v28", "ss_n40C_1v40", "ss_n40C_1v60", "ss_n40C_1v76",
           "ff_n40C_1v56", "ff_n40C_1v65", "ff_n40C_1v76"]
DESIGNS = {"original": ROOT / "bench/layout/mul16_v0.v",
           "timing_driven": ROOT / "data/glitchfix/mul16_r/timing_driven.v",
           "glitchscope": ROOT / "data/glitchfix/mul16_r/optimized.v"}
VECTORS, SAMPLE = 40, 16


def run_corner(libdir, corner):
    lib = Path(libdir) / f"sky130_fd_sc_hd__{corner}.lib"
    probe = GlitchFix(DESIGNS["original"], lib, random_vectors=VECTORS, period_ps=100000, sample=2, grid=2,
                      log=lambda m: None)
    crit = probe.timing.analyze([e[3] for e in probe.rg.edges])[2]
    period = round(1.25 * crit / 100.0) * 100.0
    row = dict(corner=corner, critical_path_ps=round(crit, 1), period_ps=period)
    for k, path in DESIGNS.items():
        fx = GlitchFix(path, lib, random_vectors=VECTORS, period_ps=period, sample=SAMPLE, grid=2, log=lambda m: None)
        c = fx.original()
        e = c.energy
        row[k] = dict(total=e["total"], glitch=e["glitch"], functional=e["functional"],
                      registers=e["flop_clock"] + e["flop_data"] + e.get("inputs", 0.0),
                      flops=c.n_flops, critical_path_ps=round(c.period_ps, 1))
    o = row["original"]["total"]
    for k in ("timing_driven", "glitchscope"):
        row[k]["saving"] = 1 - row[k]["total"] / o
    row["glitch_share_original"] = row["original"]["glitch"] / (row["original"]["glitch"] + row["original"]["functional"])
    return row


def calibration_compare(libdir, corner):
    """The same corner with its own SPICE pulse calibration and with the typical-corner one."""
    import os
    from glitchscope.m2model import DEFAULT
    out = dict(corner=corner, corner_calibration=run_corner(libdir, corner))
    os.environ["GS_M2_CAL"] = str(DEFAULT)
    try:
        out["typical_calibration"] = run_corner(libdir, corner)
    finally:
        os.environ.pop("GS_M2_CAL", None)
    (ROOT / "data/pvt/corner_calibration.json").write_text(json.dumps(out, indent=1))
    for k in ("typical_calibration", "corner_calibration"):
        r = out[k]
        print(f"{k:20s} E orig {r['original']['total'] / 1e3:6.1f} pJ  timing-driven {100 * r['timing_driven']['saving']:+5.1f} %  "
              f"GlitchScope {100 * r['glitchscope']['saving']:+5.1f} %")


def main():
    libdir = sys.argv[1]
    if len(sys.argv) > 3 and sys.argv[2] == "--compare-calibration":
        return calibration_compare(libdir, sys.argv[3])
    corners = sys.argv[2:] or CORNERS
    out = ROOT / "data/pvt/pvt.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    res = json.loads(out.read_text()) if out.exists() else {}
    for c in corners:
        t0 = time.time()
        try:
            row = run_corner(libdir, c)
        except Exception as e:  # noqa: BLE001
            print(f"{c:14s} FAILED {e}", flush=True)
            continue
        row["seconds"] = round(time.time() - t0, 1)
        res[c] = row
        out.write_text(json.dumps(res, indent=1))
        o, t, g = row["original"], row["timing_driven"], row["glitchscope"]
        print(f"{c:14s} crit {row['critical_path_ps'] / 1e3:6.2f} ns  glitch share {100 * row['glitch_share_original']:5.1f} %  "
              f"E orig {o['total'] / 1e3:6.1f} pJ  timing-driven {100 * t['saving']:+6.1f} %  "
              f"GlitchScope {100 * g['saving']:+6.1f} %  ({row['seconds']:.0f} s)", flush=True)


if __name__ == "__main__":
    main()
