"""Collect the post-layout comparison of the multiplier variants into data/layout/summary.json.

    python scripts/layout_summary.py [--pre]   (after scripts/layout_flow.sh v0 / v1 / v2; --pre: recompute the
                                                pre-layout reference, data/layout/prelayout.json)
"""
import json
import os, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
VARIANTS = {"v0": "no pipeline stage", "v1": "pipeline after row 3 (trace-and-sum)",
            "v2": "pipeline after row 9 (GlitchScope)",
            "r_td": "v0 retimed for minimum clock period (timing-driven, automatic)",
            "r_ga": "v0 retimed by GlitchScope (glitch-aware, arrival-time cuts, automatic)",
            "r_milp": "v0 retimed by GlitchScope (glitch-aware, calibrated MILP, automatic)"}
LATENCY = {"v0": 2, "v1": 3, "v2": 3, "r_td": 2, "r_ga": 2, "r_milp": 2}
PRE = ROOT / "data/layout/prelayout.json"


def power_groups(log):
    text = log.read_text()
    part = text.split("===== with GlitchScope SAIF", 1)[1]
    out = {}
    for g in ("Sequential", "Combinational", "Clock", "Total"):
        m = re.search(rf"^{g}\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)", part, re.M)
        out[g] = float(m.group(4)) * 1e3            # mW
    m = re.search(r"([-\d.]+)\s+slack \((MET|VIOLATED)\)", part)
    out["slack_ns"] = float(m.group(1))
    out["annotated_pins"] = int(re.search(r"Annotated (\d+) pin", text).group(1))
    return out


if "--pre" in sys.argv:          # pre-layout reference: the same analysis on the netlists before place & route
    import subprocess
    import tempfile
    pre = {}
    for v in ("v0", "v1", "v2"):
        with tempfile.TemporaryDirectory() as td:
            subprocess.run([sys.executable, "-m", "glitchscope.flow", "--netlist", str(ROOT / f"bench/layout/mul16_{v}.v"),
                            "--lib", os.environ["GS_LIB"], "--random-vectors", "40", "--period-ps", "15000", "--seed", "3",
                            "--no-attribution", "--out", td], check=True, capture_output=True)
            s0 = json.loads((Path(td) / "summary.json").read_text())
        n, T = s0["design"]["cycles"], s0["totals"]
        pre[v] = dict(E_glitch_pJ=T["E_glitch_fJ"] / n / 1e3, E_comb_pJ=T["E_total_fJ"] / n / 1e3, period_ns=15.0,
                      cycles=n, note="pre-layout netlist, pin capacitance only, 40 random cycles (seed 3)")
    PRE.write_text(json.dumps(pre, indent=1))

rows = {}
for v, desc in VARIANTS.items():
    d = ROOT / "data/layout" / v
    if not (d / "power.log").exists():
        continue
    s = json.loads((d / "glitchscope/summary.json").read_text())
    rep = json.loads((ROOT / f"build_layout/logs/sky130hd/mul16_{v}/base/6_report.json").read_text()) \
        if (ROOT / f"build_layout/logs/sky130hd/mul16_{v}/base/6_report.json").exists() else \
        json.loads((d / "6_report.json").read_text())
    (d / "6_report.json").write_text(json.dumps(rep, indent=1))
    n = s["design"]["cycles"]
    T = s["totals"]
    rows[v] = dict(
        description=desc, flops=s["design"]["flops"], cells=s["design"]["cells"],
        parasitics=s["design"].get("parasitics"),
        glitchscope=dict(E_functional_pJ=T["E_functional_fJ"] / n / 1e3, E_glitch_pJ=T["E_glitch_fJ"] / n / 1e3,
                         E_comb_pJ=T["E_total_fJ"] / n / 1e3, glitch_fraction=T["glitch_fraction"]),
        opensta_mW=power_groups(d / "power.log"),
        area_um2=rep["finish__design__instance__area__stdcell"], die_um2=rep["finish__design__die__area"],
        utilization=rep["finish__design__instance__utilization"],
        clock_period_ns=15.0, latency_cycles=LATENCY[v])
out = dict(variants=rows, prelayout=json.loads(PRE.read_text()) if PRE.exists() else None)
(ROOT / "data/layout/summary.json").write_text(json.dumps(out, indent=1))
b = rows["v0"]
print(f"{'variant':7s} {'E_glitch pJ':>11s} {'E_comb pJ':>10s} {'P_total mW':>10s} {'d P':>7s} {'area um2':>9s} {'d area':>7s} {'slack ns':>8s}")
for v, r in rows.items():
    print(f"{v:7s} {r['glitchscope']['E_glitch_pJ']:11.1f} {r['glitchscope']['E_comb_pJ']:10.1f} "
          f"{r['opensta_mW']['Total']:10.2f} {100 * (r['opensta_mW']['Total'] / b['opensta_mW']['Total'] - 1):+6.1f}% "
          f"{r['area_um2']:9.0f} {100 * (r['area_um2'] / b['area_um2'] - 1):+6.1f}% {r['opensta_mW']['slack_ns']:8.2f}")
