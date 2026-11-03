"""Post-layout comparison of the AI-accelerator PE (4-lane int8 dot product), original vs
GlitchScope register placement, array and Booth multipliers -> data/layout/pe_summary.json.

    DESIGN=dot4_i8 PERIOD_PS=7500 scripts/layout_flow.sh pe_<arch>_<v0|ga>   (each variant), then
    python scripts/pe_layout_summary.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from layout_summary import power_groups  # noqa: E402

rows = {}
for arch in ("plain", "booth"):
    for v in ("v0", "ga"):
        name = f"pe_{arch}_{v}"
        d = ROOT / "data/layout" / name
        rp = ROOT / f"build_layout/logs/sky130hd/dot4_i8_{name}/base/6_report.json"
        rep = json.loads(rp.read_text()) if rp.exists() else json.loads((d / "6_report.json").read_text())
        (d / "6_report.json").write_text(json.dumps(rep, indent=1))
        s = json.loads((d / "glitchscope/summary.json").read_text())
        n, T = s["design"]["cycles"], s["totals"]
        rows[name] = dict(arch=arch, placement="original" if v == "v0" else "GlitchScope", flops=s["design"]["flops"],
                          E_glitch_pJ=T["E_glitch_fJ"] / n / 1e3, E_comb_pJ=T["E_total_fJ"] / n / 1e3,
                          opensta_mW=power_groups(d / "power.log"), area_um2=rep["finish__design__instance__area__stdcell"])
(ROOT / "data/layout/pe_summary.json").write_text(json.dumps(rows, indent=1))
for arch in ("plain", "booth"):
    o, g = rows[f"pe_{arch}_v0"], rows[f"pe_{arch}_ga"]
    for r in (o, g):
        print(f"{arch:6s} {r['placement']:12s} flops {r['flops']:3d}  glitch {r['E_glitch_pJ']:5.1f} pJ  logic {r['E_comb_pJ']:5.1f} pJ  "
              f"P {r['opensta_mW']['Total']:.3f} mW ({100 * (r['opensta_mW']['Total'] / o['opensta_mW']['Total'] - 1):+5.1f} %)  "
              f"area {r['area_um2']:7.0f} um2 ({100 * (r['area_um2'] / o['area_um2'] - 1):+5.1f} %)  slack {r['opensta_mW']['slack_ns']:.2f} ns")
