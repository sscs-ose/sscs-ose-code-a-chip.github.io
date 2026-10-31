#!/usr/bin/env python3
"""Evidence behind Table B.1 of the notebook (Appendix B; Table 3.4 in earlier versions) (driver responses compared with the bootstrapped switch).

    uv run python experiments/closure/table34_evidence.py

Reads only results that already exist in results/closure/ (screening runs made during the design study with this
folder's bench and metric code, at the supplies then declared, 1.62/1.80/1.98 V) and writes
results/closure/candidates/table34.json, the numbers quoted in Table B.1 with their source files. No simulation is run.
Noise figures marked "earlier method" were integrated from 1 kHz with the switch as modelled by SKY130 (about 0.8 kT/C),
before the method correction of Section 3.5; corrected figures differ by a few µV, which does not change any row.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
C = ROOT / "results" / "closure" / "candidates"
VLSB_MV = 0.6 / 1024 * 1e3


def load(name):
    return json.loads((C / name).read_text())


def maxr(rows):
    return max(r["max_abs_r_LSB"] for r in rows)


def main() -> None:
    f2 = json.loads((ROOT / "results" / "closure" / "screen" / "f2_screen.json").read_text())
    nf, nfs = load("nf16a_boot5_screen+hot.json"), load("nf16a_boot5_screen+hot_stress.json")
    gb, gbs = load("gbfc2_boot5_screen+hot.json"), load("gbfc2_boot5_screen+hot_stress.json")
    gbn = load("gbfc2_boot5_noise_earlier_method.json")
    drv_noise = load("driver_noise_tt.json")
    tt = lambda rows: [r for r in rows if r["tag"] == "tt_1.80V_+27C"][0]
    out = {
        "first_cut": {
            "current_uA_tt": tt(f2)["supply_current_uA"],
            "pre_opening_residual_max_mV": max(r["components_mV"]["rS"] for r in f2 if r["max_abs_r_LSB"] < 10),
            "noise_uV_tt_0p6V": drv_noise["f2_boot5"]["noise_uV_rms"], "noise_method": drv_noise["f2_boot5"]["method"],
            "sources": ["results/closure/screen/f2_screen.json (first-cut gate; conditions where the gate conducts)",
                        "results/closure/candidates/driver_noise_tt.json"]},
        "folded_cascode_native_pair": {
            "current_uA_tt": tt(nf)["supply_current_uA"],
            "pre_opening_residual_max_mV": max(r["components_mV"]["rS"] for r in nf + nfs),
            "screening_max_LSB_primary": maxr(nf), "screening_max_LSB_stress": maxr(nfs),
            "noise_uV_tt_0p6V": drv_noise["nf16a_boot5"]["noise_uV_rms"], "noise_method": drv_noise["nf16a_boot5"]["method"],
            "sources": ["results/closure/candidates/nf16a_boot5_screen+hot.json", "nf16a_boot5_screen+hot_stress.json",
                        "driver_noise_tt.json"]},
        "single_stage_load_compensated": {
            "current_uA_tt": tt(gb)["supply_current_uA"],
            "screening_max_LSB_primary": maxr(gb), "screening_max_LSB_stress": maxr(gbs),
            "noise_uV_range": [min(r["noise_uV_rms"] for r in gbn), max(r["noise_uV_rms"] for r in gbn)],
            "noise_uV_tt": [r["noise_uV_rms"] for r in gbn if r["tag"] == "tt_1.80V_+27C"],
            "noise_method": "earlier method",
            "sources": ["results/closure/candidates/gbfc2_boot5_screen+hot.json", "gbfc2_boot5_screen+hot_stress.json",
                        "gbfc2_boot5_noise_earlier_method.json"]},
    }
    (C / "table34.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
