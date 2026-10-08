#!/usr/bin/env python3
"""12T screening study: 9T core + two keep-alive sinks (M10, M11) + reference-current bias (M12).

SPICE only - no lookup table yet. This answers one question before any flow work is built on the 12T:
does a design exist that passes the adoption gate at every corner?

Gate (all five corners tt/ss/ff at 27 C, tt at -20 C and 85 C, 1.8 V):
  * gain monotonic (flat top may droop <= 0.2 dB per step) over a window from Vctrl = +0.3 V that spans >= 30 dB, with
    f_-3dB >= 10 kHz (C_L = 1 pF) at every sampled gain step inside that window
  * total supply current <= 5 uA, reference branch included
  * min V_DS of M2, M5, M6, M9 >= 130 mV at both control endpoints
  * integrated input noise at maximum gain (tt, 20 Hz-20 kHz) <= 29.1 uV, the 9T baseline's value

Usage, from the submission folder inside the container:
  python tools/study_12t.py              # reference point and the passing candidate, five corners each
  python tools/study_12t.py --grid       # the sink x mirror x common-mode grid, then corner-check the passers
Results go to cache/study_12t.json. Nothing in the notebook reads this file yet.
"""
import sys, json, math, time, argparse, itertools
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import vga_flow as vf

CL = 1e-12
CORNERS = [("tt", 27), ("ss", 27), ("ff", 27), ("tt", -20), ("tt", 85)]
VGRID = np.round(np.arange(-0.35, 0.301, 0.05), 3)       # gain-curve grid, ends at +0.3 V
VSTEPS = [0.3, 0.1, -0.1, -0.2, -0.3]                      # where bandwidth is sampled
DEVS = ("m2", "m5", "m6", "m9")
NOISE_LIMIT = 29.1e-6                                      # 9T hand-sized baseline, max gain, tt
MONO_TOL_DB = 0.2     # "monotonic" allows the saturated top of the curve to droop by up to this much per step
OUT = ROOT / "cache" / "study_12t.json"


def design(W_in=20, L_in=1, W_k=1.0, L_k=1.0, i_tail=2.04e-6, ratio=1, W_mir=None, L_mir=None, vctrl_cm=None):
    """12T design point. The reference device M12 is the tail's size divided by `ratio`, fed with
    i_tail/ratio, so the tail carries about i_tail and the reference branch costs i_tail/ratio."""
    p = dict(vf.BASELINE, W_in=W_in, L_in=L_in, W_k=W_k, L_k=L_k)
    p["W_ref"], p["L_ref"] = p["W_tail"] / ratio, p["L_tail"]
    p["iref"] = i_tail / ratio
    for k, v in (("W_mir", W_mir), ("L_mir", L_mir), ("vctrl_cm", vctrl_cm)):
        if v is not None:
            p[k] = v
    return p


# The first design found to pass the gate at all five corners (8 Oct, three hand-chosen grids).
# Found by SPICE screening, not yet by the flow: the notebook must not present it as a flow result.
CANDIDATE = dict(W_in=80, L_in=2, W_k=4, L_k=4, i_tail=2.0e-6, ratio=4, W_mir=10, L_mir=1, vctrl_cm=1.10)


def check(p, corner="tt", temp=27):
    q = dict(p, corner=corner, temp=temp)
    g = 20 * np.log10(np.asarray(vf.gain_curve(q, VGRID)))
    bw = {v: vf.bandwidth(q, v, CL)["f3db"] for v in VSTEPS}
    ops = [vf.characterise(q, v) for v in (0.3, -0.3)]
    vds_min = min(o[f"{m}_vds"] for o in ops for m in DEVS)
    i_tot = max(o["i_tot"] for o in ops)
    lo = None                                  # lowest sampled Vctrl reached without bandwidth dropping below 10 kHz
    for v in VSTEPS:
        if bw[v] >= 10e3:
            lo = v
        else:
            break
    if lo is None:
        mono, rng = False, 0.0
    else:
        sel = VGRID >= lo - 1e-9
        mono = bool(np.all(np.diff(g[sel]) > -MONO_TOL_DB))
        rng = float(g[-1] - g[np.argmin(abs(VGRID - lo))])
    return dict(corner=f"{corner}/{temp}", gain_max_db=float(g[-1]), window_lo_v=lo, monotonic=mono,
                range_db=rng, bw_khz={f"{k:+.1f}": v / 1e3 for k, v in bw.items()},
                i_tot_ua=i_tot * 1e6, vds_min_mv=vds_min * 1e3,
                gain_curve_db=[float(x) for x in g])


def corner_ok(r):
    return r["monotonic"] and r["range_db"] >= 30 and r["i_tot_ua"] <= 5.0 and r["vds_min_mv"] >= 130


def full(p, label):
    t = time.time()
    rows = [check(p, c, tc) for c, tc in CORNERS]
    nz = vf.noise(dict(p), 0.3, 20.0, 20e3)
    res = dict(label=label, params={k: p[k] for k in ("W_in", "L_in", "W_k", "L_k", "W_ref", "iref",
                                                     "W_mir", "L_mir", "W_st", "L_st", "vctrl_cm")},
               corners=rows, noise_max_gain_uv=nz["vrms"] * 1e6, noise_1k_nv=nz["vn_1k"] * 1e9)
    res["gate"] = bool(all(corner_ok(r) for r in rows) and nz["vrms"] <= NOISE_LIMIT)
    print(f"\n{label}   ({time.time() - t:.0f} s)   noise at max gain {res['noise_max_gain_uv']:.1f} uV"
          f"   GATE {'PASS' if res['gate'] else 'FAIL'}")
    print(f"  {'corner':8s} {'Amax dB':>7s} {'range dB':>8s} {'window to':>9s} {'mono':>5s} "
          f"{'BW min kHz':>10s} {'I uA':>5s} {'Vds mV':>6s}")
    for r in rows:
        bwmin = min(r["bw_khz"].values())
        print(f"  {r['corner']:8s} {r['gain_max_db']:7.1f} {r['range_db']:8.1f} {str(r['window_lo_v']):>9s} "
              f"{str(r['monotonic']):>5s} {bwmin:10.1f} {r['i_tot_ua']:5.2f} {r['vds_min_mv']:6.0f}"
              f"  {'ok' if corner_ok(r) else 'FAIL'}")
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--grid", action="store_true")
    a = ap.parse_args()
    out = {"reference": full(design(), "reference: baseline sizes, sinks 1/1, i_tail 2.04 uA, ratio 1")}
    out["candidate"] = full(design(**CANDIDATE), "candidate: in 80/2, sinks 4/4, mirror 10/1, cm 1.10 V, "
                                                 "i_tail 2.0 uA, reference device 1/4 of the tail")
    if a.grid:
        # Third and most informative of the 8 Oct grids: sink size x PMOS mirror size x steering common mode.
        # Mirror size was the noise lever; lowering the steering common mode fixed headroom.
        grid = list(itertools.product(((4, 4), (6, 8)), ((5, 1), (10, 1), (10, 2), (20, 2)), (1.05, 1.10, 1.15)))
        screened, passers = [], []
        for (W_k, L_k), (Wm, Lm), cm in grid:
            p = design(80, 2, W_k, L_k, 2.0e-6, ratio=4, W_mir=Wm, L_mir=Lm, vctrl_cm=cm)
            r = check(p)
            nz = vf.noise(dict(p), 0.3, 20.0, 20e3)["vrms"]
            ok = corner_ok(r) and r["vds_min_mv"] >= 150 and nz <= NOISE_LIMIT   # 20 mV extra margin at tt
            screened.append(dict(params=dict(W_k=W_k, L_k=L_k, W_mir=Wm, L_mir=Lm, vctrl_cm=cm),
                                 tt=r, noise_uv=nz * 1e6, tt_pass=ok))
            print(f"tt screen sink {W_k}/{L_k} mirror {Wm}/{Lm} cm {cm:.2f}: range {r['range_db']:5.1f} dB"
                  f"  BWmin {min(r['bw_khz'].values()):5.1f} kHz  I {r['i_tot_ua']:.2f} uA  Vds {r['vds_min_mv']:.0f} mV"
                  f"  noise {nz * 1e6:5.1f} uV  {'PASS' if ok else '-'}")
            if ok:
                passers.append(p)
        out["screen"] = screened
        out["corner_checked"] = [full(p, f"sink {p['W_k']}/{p['L_k']} mirror {p['W_mir']}/{p['L_mir']} "
                                         f"cm {p['vctrl_cm']:.2f}") for p in passers]
        print(f"\n{len(passers)} of {len(grid)} pass at tt; "
              f"{sum(r['gate'] for r in out['corner_checked'])} pass the full gate")
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
