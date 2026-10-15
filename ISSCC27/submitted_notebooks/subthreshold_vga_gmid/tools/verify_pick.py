#!/usr/bin/env python3
"""Run the pick's long SPICE verifications outside the notebook and store them in the caches the notebook reads
(same functions, same cache names): DC match, Monte Carlo at the rule-chosen corners, the control port, PSRR/CMRR,
the stress corners and the bias tolerance. Use after `tools/run_flow.py` and before a tier-1 notebook run.

  python tools/verify_pick.py            # only what is missing
  python tools/verify_pick.py --rerun    # recompute all of it
SPDX-License-Identifier: Apache-2.0
"""
import sys, json, time, argparse
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import os; os.chdir(ROOT)
import vga_flow as vf, evaluator as ev, flow, run_flow as rf, verify as vfy, nbutil as nu

LUT = ROOT / "cache" / "lut_sky130.npz"


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--rerun", action="store_true"); ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--spec", default="wire", choices=list(rf.SPECS))
    a = ap.parse_args()
    nu.CAN_RUN = True
    SPEC, BASE = rf.SPECS[a.spec], dict(vf.BASELINE)
    sfx = "" if a.spec == "wire" else f"_{a.spec}"             # the final pick (wire-aware run) owns the plain cache names
    R12 = flow.run_flow(SPEC, "12T", LUT, BASE, spice=False, log=lambda *x: None)
    PV = R12["pick"]
    if PV is None:
        sys.exit("no pick in the cached flow run")
    PICK = ev.materialise(BASE, PV["point"])
    print("pick:", PV["point"], f"{1e6*PV['vrms']:.2f} uV")
    t = time.time()
    nu.cached("pick_bias_tolerance" + sfx, lambda: flow.bias_tolerance(PV["point"], SPEC, BASE, LUT), a.rerun)
    print(f"bias tolerance {time.time()-t:.0f} s", flush=True)
    t = time.time()
    VPK = 0.2e-3
    nu.cached("pick_control_port" + sfx, lambda: dict(
        feed=[vfy.control_step(PICK, x, y, CL=SPEC.CL + SPEC.c_wire) for x, y in ((0.3, 0.0), (0.0, -0.3), (-0.3, 0.3))],
        gain=[vfy.control_step(PICK, x, y, vin_pk=VPK, CL=SPEC.CL + SPEC.c_wire) for x, y in ((0.3, 0.0), (0.0, 0.3), (0.3, -0.1))],
        psrr=vfy.psrr(PICK), cmrr=vfy.cmrr(PICK), stress=vfy.stress(PICK, SPEC)), a.rerun)
    print(f"control port, PSRR/CMRR, stress {time.time()-t:.0f} s", flush=True)
    t = time.time()
    def nz_corners():
        out = {}
        for c, tt, v in [(c, tt, 1.8) for c, tt in SPEC.corners] + [("tt", 27, v) for v in SPEC.supplies] + list(SPEC.combos):
            r = vf.noise(dict(PICK, corner=c, temp=tt, vdd=v), 0.3, *SPEC.band)
            out[f"{c}/{tt:g}/{v:g}"] = dict(vrms=r["vrms"], vn_1k=r["vn_1k"])
        return out
    nu.cached("pick_noise_corners" + sfx, nz_corners, a.rerun)
    print(f"noise at every corner {time.time()-t:.0f} s", flush=True)
    # the per-pick verification cells of notebook §10.1-10.4, same calls as there
    t = time.time()
    band, cl_w = SPEC.band, SPEC.CL + SPEC.c_wire
    nu.cached("pick_temperature" + sfx, lambda: dict(plain=vfy.gain_vs_temperature(PICK), ptat=vfy.gain_vs_temperature(PICK, ptat=True)), a.rerun)
    nu.cached("pick_supply" + sfx, lambda: vfy.supply(PICK, spec=SPEC), a.rerun)
    nu.cached("pick_noise" + sfx, lambda: {f"{v:+.1f}": (lambda r: dict(f=r["f"], vn=r["vn"], vrms=r["vrms"], vn_1k=r["vn_1k"]))(vf.noise(PICK, v, *band))
                                           for v in (0.3, 0.0)}, a.rerun)
    nu.cached("pick_steps" + sfx, lambda: vfy.per_step(PICK, CL=cl_w, band=band), a.rerun)
    print(f"temperature, supply, noise spectra, every step {time.time()-t:.0f} s", flush=True)
    # Monte Carlo corners: tt, then the pick's critical corners (the notebook's rule, §10.6)
    def corner_of(r):
        p_ = r["corner"].split("/")
        return (p_[0], float(p_[1]), float(p_[2][:-1]) if len(p_) > 2 else 1.8)
    mcc = [("tt", 27.0, 1.8)]
    for r in (max(PV["corners"], key=lambda r: SPEC.i_eff(r["i_tot"], r.get("i_sig", 0.0))),
              min(PV["corners"], key=lambda r: r["vds_min"]), min(PV["corners"], key=lambda r: r["bw_min"])):
        k = corner_of(r)
        if k not in mcc:
            mcc.append(k)
    print("Monte Carlo corners:", mcc, flush=True)
    t = time.time()
    nu.cached("dc_match" + sfx, lambda: {"pick": vfy.dc_match(PICK), "baseline": vfy.dc_match(BASE)}, a.rerun)
    print(f"dc match {time.time()-t:.0f} s", flush=True)
    t = time.time()
    # one cache file per corner, so an interrupted run keeps the corners already finished
    parts = {f"{c}/{tt:g}/{v:g}": nu.cached(f"mc_part{sfx}_{c}_{tt:g}_{v:g}",
                                            lambda c=c, tt=tt, v=v: vfy.monte_carlo(dict(PICK, vdd=v), n=a.n, corner=c, temp=tt, spec=SPEC),
                                            a.rerun)
             for c, tt, v in mcc}
    nu.cached("monte_carlo" + sfx, lambda: parts, True)
    print(f"monte carlo {time.time()-t:.0f} s", flush=True)
    M = json.loads((ROOT / "cache" / f"monte_carlo{sfx}.json").read_text())
    for k, m in M.items():
        S = m["samples"]
        ok = sum(s["monotonic"] and s["range_db"] >= SPEC.range_min_db and s["bw_min"] >= SPEC.bw_min_hz
                 and s["i_tot"] <= SPEC.i_tot_max and s["vds_min"] >= SPEC.vds_min_v for s in S)
        ol = sum(s.get("vds_open_min", 0) >= SPEC.vds_min_v for s in S)
        print(f"MC {k}: {ok}/{len(S)} pass behind the servo; {ol}/{len(S)} keep headroom without it")


if __name__ == "__main__":
    main()
