"""Closed loop, design note section 6.2 steps 1-7, on SKY130:

  1  xschem (live)   build a 50-ohm-terminated cascode driver whose output node
                     carries C_L at the T-coil tap; the coil is L1/L2 + series R + K + C_B
  2  ngspice         baseline (no coil) and an initial ideal T-coil
  3  optimizer       ideal symmetric T-coil: sweep L, k, C_B; widest f3dB with peaking <= limit
  4  KLayout (live)  place the VIADUCT_SKY130 T-coil; adjust `area` with FastHenry until the
                     series inductance matches the optimizer's target
  5  FastHenry       final EM run (L1, L2, R, Q, k); results written into the PCell with run ID
  6  back-annotate   extracted coil (both orientations, with and without a C_B) re-simulated
  7  report          runs/closedloop_<id>/report.md + report.json with every run ID

    python examples/tcoil_amp_closed_loop.py [--peaking-db 1.0] [--cl 150f]

Everything appears live in the xschem and KLayout windows on the noVNC desktop.
Models: SKY130 tt devices; the coil from FastHenry is quasi-static (no substrate,
no inter-winding capacitance), so the extracted case is an estimate, not signoff.
"""
import argparse
import json
import math
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from viaduct import Viaduct  # noqa: E402
from viaduct.schematic import Builder  # noqa: E402

SCH = "/foss/designs/viaduct/xschem/tcoil_amp.sch"
RT = 50.0
OFF = dict(LA="1e-15", LB="1e-15", KC="1e-6", CB="1e-18", RA="1e-3", RB="1e-3")   # "no coil"


def log(msg):
    print("[%s] %s" % (time.strftime("%H:%M:%S"), msg), flush=True)


def eng(x, unit=""):
    for f, p in ((1e9, "G"), (1e6, "M"), (1e3, "k"), (1, ""), (1e-3, "m"), (1e-6, "u"), (1e-9, "n"),
                 (1e-12, "p"), (1e-15, "f")):
        if abs(x) >= f:
            return "%.3g%s%s" % (x / f, p, unit)
    return "%.3g%s" % (x, unit)


# ---- 1: schematic -----------------------------------------------------------------------

def build_schematic(vd, a):
    sb = Builder(vd)
    sb.new(SCH, replace=True)
    # Cascode driver. The cascode M2 keeps M1's Cgd feed-through (gate -> output) off the
    # output node; without it, for gm*R ~ 1, the feed-through zero sits inside the band and
    # the -3 dB point is not a bandwidth. M2 D(20,170) G(-20,200) S(20,230) B(20,200)
    sb.place("sky130_fd_pr/nfet_01v8.sym", 0, 200, name="M2", W=a.w, L="0.15", nf=a.nf)
    sb.wire(20, 170, 20, 140)
    sb.wire(-20, 200, -80, 200)
    sb.label("VB", -80, 200)
    sb.wire(20, 200, 50, 200, 50, 240)
    sb.gnd(50, 240)
    sb.wire(20, 230, 20, 270)
    # Input device: M1 D(20,270) G(-20,300) S(20,330) B(20,300)
    sb.place("sky130_fd_pr/nfet_01v8.sym", 0, 300, name="M1", W=a.w, L="0.15", nf=a.nf)
    # Coil chain from the drain X up to the termination: RA, L1, tap T, L2, RB, Y, RT, VDD
    sb.place("res.sym", 20, 110, name="RA", value="{RA}")          # P(20,80)  M(20,140)
    sb.wire(20, 80, 20, 60)
    sb.place("ind.sym", 20, 30, name="LCA", value="{LA}")           # p(20,0)   m(20,60)
    sb.wire(20, 0, 20, -20)
    sb.wire(20, -20, 20, -40)
    sb.place("ind.sym", 20, -70, name="LCB", value="{LB}")          # p(20,-100) m(20,-40)
    sb.wire(20, -100, 20, -120)
    sb.place("res.sym", 20, -150, name="RB", value="{RB}")         # P(20,-180) M(20,-120)
    sb.wire(20, -180, 20, -200)
    sb.place("res.sym", 20, -230, name="RT", value="{RT}")         # P(20,-260) M(20,-200)
    sb.wire(20, -260, 20, -280)
    sb.label("VDD", 20, -280)
    # Tap load and output
    sb.wire(20, -20, 120, -20)
    sb.place("capa.sym", 120, 10, name="CL", value="{CL}")         # p(120,-20) m(120,40)
    sb.wire(120, 40, 120, 60)
    sb.gnd(120, 60)
    sb.wire(120, -20, 170, -20)
    sb.label("OUT", 170, -20, rot=2)
    # Bridging capacitor X..Y
    sb.place("capa.sym", -100, -30, name="CB", value="{CB}")       # p(-100,-60) m(-100,0)
    sb.wire(-100, -60, -100, -200, 20, -200)
    sb.wire(-100, 0, -100, 140, 20, 140)
    sb.label("Y", -100, -200)
    sb.label("X", -100, 140)
    # Coil parasitics to substrate at X and Y (FasterCap pi split; tap share goes into CL)
    sb.place("capa.sym", -250, 200, name="CPX", value="{CPX}")    # p(-250,170) m(-250,230)
    sb.wire(-250, 170, -250, 150)
    sb.label("X", -250, 150)
    sb.wire(-250, 230, -250, 250)
    sb.gnd(-250, 250)
    sb.place("capa.sym", -250, -150, name="CPY", value="{CPY}")   # p(-250,-180) m(-250,-120)
    sb.wire(-250, -180, -250, -200)
    sb.label("Y", -250, -200)
    sb.wire(-250, -120, -250, -100)
    sb.gnd(-250, -100)
    # M1 source/bulk, gate
    sb.wire(20, 330, 20, 360)
    sb.gnd(20, 360)
    sb.wire(20, 300, 50, 300, 50, 360)
    sb.gnd(50, 360)
    sb.wire(-20, 300, -80, 300)
    sb.label("IN", -80, 300)
    # Supplies
    sb.place("vsource.sym", -300, 0, name="VDD", value="1.8")
    sb.wire(-300, -30, -300, -60)
    sb.label("VDD", -300, -60)
    sb.wire(-300, 30, -300, 60)
    sb.gnd(-300, 60)
    sb.place("vsource.sym", -200, 0, name="VIN", value="dc %s ac 1" % a.vin)
    sb.wire(-200, -30, -200, -60)
    sb.label("IN", -200, -60)
    sb.wire(-200, 30, -200, 60)
    sb.gnd(-200, 60)
    sb.place("vsource.sym", -400, 0, name="VB", value=a.vb)
    sb.wire(-400, -30, -400, -60)
    sb.label("VB", -400, -60)
    sb.wire(-400, 30, -400, 60)
    sb.gnd(-400, 60)
    sb.place("sky130_fd_pr/corner.sym", -300, 430, corner="tt")
    sb.code(200, 120, "\n".join([
        ".param LA=%s LB=%s KC=%s CB=%s RA=%s RB=%s" % tuple(OFF[k] for k in ("LA", "LB", "KC", "CB", "RA", "RB")),
        ".param CL=%s RT=%g CPX=1e-18 CPY=1e-18" % (a.cl, RT),
        "KCOIL LCA LCB {KC}",
        ".control", "save all", "op", "ac dec 40 1e8 2e11", "write tcoil_amp.raw", ".endc"]))
    return sb.finish()


# ---- helpers ------------------------------------------------------------------------------

def sweep(vd, netlist, **kw):
    r = vd.sim.sweep(netlist, node="out", ac="dec 40 1e8 2e11", **kw).check().result
    if r["status"] != "COMPLETE":
        raise SystemExit("sweep failed: %s" % r["errors"])
    return r


def coil_case(label, em, orientation="A", cb="1e-18"):
    m = em["spice_model"]
    la, ra, lb, rb = (m["L1_H"], m["R1_ohm"], m["L2_H"], m["R2_ohm"]) if orientation == "A" else \
                     (m["L2_H"], m["R2_ohm"], m["L1_H"], m["R1_ohm"])
    return {"label": label, "LA": "%.6g" % la, "LB": "%.6g" % lb, "RA": "%.6g" % ra, "RB": "%.6g" % rb,
            "KC": "%.6g" % m["K"], "CB": cb}


def coil_lc_case(label, em, cap, cl, orientation="A", cb_extra=0.0):
    """FastHenry L/R/K plus FasterCap parasitics; X = drain side."""
    c = coil_case(label, em, orientation)
    p = cap["spice_parasitics"]
    cx, cy = (p["C_X_F"], p["C_Y_F"]) if orientation == "A" else (p["C_Y_F"], p["C_X_F"])
    c.update(CB="%.6g" % (p["CB_par_F"] + cb_extra), CPX="%.6g" % cx, CPY="%.6g" % cy,
             CL="%.6g" % (cl + p["C_T_F"]))
    return c


def series_l(em):
    return em["reference"]["L_series_P1_P2_nH"] * 1e-9


# ---- main ---------------------------------------------------------------------------------

DEFAULTS = dict(cl="150f", w="40", nf="8", vin="0.9", vb="1.8", peaking_db=1.0,
                areas="4000,5000,6400,8000,10000")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--cl", default=DEFAULTS["cl"], help="load capacitance at the tap")
    p.add_argument("--w", default=DEFAULTS["w"], help="driver width (um)")
    p.add_argument("--nf", default=DEFAULTS["nf"])
    p.add_argument("--vin", default=DEFAULTS["vin"], help="gate DC bias (V)")
    p.add_argument("--vb", default=DEFAULTS["vb"], help="cascode gate bias (V)")
    p.add_argument("--peaking-db", type=float, default=DEFAULTS["peaking_db"], help="maximum allowed peaking")
    p.add_argument("--areas", default=DEFAULTS["areas"], help="T-coil area values tried in step 4")
    p.add_argument("--mode", choices=("live", "headless"), default="live")
    a = p.parse_args()
    vd = Viaduct.from_env(mode=a.mode)
    _, rdir = run(vd, **{k: v for k, v in vars(a).items() if k in DEFAULTS})
    print(str(rdir))


def run(vd, **options):
    """Steps 1-7 on a started Viaduct session; returns (report dict, report directory)."""
    a = argparse.Namespace(**dict(DEFAULTS, **options))
    t_start = time.time()
    report = {"inputs": vars(a), "mode": vd.mode, "runs": {}}

    log("1 xschem: building %s live" % SCH)
    nl = build_schematic(vd, a)
    netlist = nl["path"]
    report["schematic"] = SCH
    report["netlist"] = netlist
    report["runs"]["schematic_screenshot"] = vd.xschem.screenshot().check().result["local_path"]

    log("2 ngspice: baseline (no coil)")
    base = sweep(vd, netlist, cases=[dict(OFF, label="baseline: no T-coil")])
    b = base["points"][0]
    report["runs"]["baseline"] = base["run_id"]
    log("   baseline: gain %.2f dB, f3dB %s" % (b["dc_gain_db"], eng(b["f3db_hz"], "Hz")))

    log("3 optimizer: ideal symmetric T-coil (L1=L2, k, C_B), peaking <= %.2f dB" % a.peaking_db)
    cl = float(a.cl.rstrip("f")) * 1e-15
    l_ref = RT ** 2 * cl                 # constant-resistance T-coil: L1+L2+2M ~ R^2 C
    ls = [round(l_ref * f / 1e-12, 1) * 1e-12 for f in (0.15, 0.2, 0.25, 0.3, 0.35, 0.45)]
    grid = {"LA": ls, "KC": [0.2, 0.3, 0.4, 0.5, 0.6], "CB": [1e-18, 2e-15, 5e-15, 10e-15, 20e-15]}
    cases = [dict(label="ideal", LA="%.4g" % l, LB="%.4g" % l, KC=str(k), CB="%.4g" % c, RA="1e-3", RB="1e-3")
             for l in grid["LA"] for k in grid["KC"] for c in grid["CB"]]
    opt = sweep(vd, netlist, cases=cases)
    report["runs"]["optimizer"] = opt["run_id"]
    ok = [q for q in opt["points"] if q.get("f3db_hz") and q["peaking_db"] <= a.peaking_db]
    best = max(ok, key=lambda q: q["f3db_hz"])
    l_ideal, k_ideal = float(best["LA"]), float(best["KC"])
    target = 2 * l_ideal * (1 + k_ideal)       # series inductance P1->P2 of the ideal coil
    report["ideal"] = {k: best[k] for k in ("LA", "LB", "KC", "CB", "dc_gain_db", "f3db_hz", "peaking_db")}
    report["ideal"]["L_series_target_nH"] = target * 1e9
    log("   %d points in %.0fs; best: L1=L2=%s k=%s C_B=%s -> f3dB %s (peaking %.2f dB); series L target %s"
        % (len(cases), opt["seconds"], eng(l_ideal, "H"), k_ideal, eng(float(best["CB"]), "F"),
           eng(best["f3db_hz"], "Hz"), best["peaking_db"], eng(target, "H")))

    log("4 KLayout + FastHenry: size the T-coil to the series-L target")
    vd.klayout.new_layout("TCOIL_AMP").check()
    vd.klayout.place_tcoil("DUT", params={"metalWidth": 4.0, "area": 6400.0}).check()
    tried = []
    for area in [float(x) for x in a.areas.split(",")]:
        r = vd.klayout.set_pcell_params("DUT", area=area)
        if not r.ok:
            tried.append({"area": area, "error": r.error})
            continue
        em = vd.em.fasthenry({"metalWidth": 4.0, "area": area}, freqs_hz=[10e9]).check().result
        tried.append({"area": area, "L_series_nH": series_l(em) * 1e9, "L1_nH": em["reference"]["L1_nH"],
                      "L2_nH": em["reference"]["L2_nH"], "K1": em["reference"]["K1"], "run_id": em["run_id"]})
        log("   area %g um^2: L_series %.3f nH (L1 %.3f, L2 %.3f, K1 %.3f)  run %s" % (
            area, tried[-1]["L_series_nH"], tried[-1]["L1_nH"], tried[-1]["L2_nH"], tried[-1]["K1"], em["run_id"]))
    good = [t for t in tried if "L_series_nH" in t]
    pick = min(good, key=lambda t: abs(t["L_series_nH"] * 1e-9 - target))
    report["sizing"] = {"target_nH": target * 1e9, "tried": tried, "picked_area": pick["area"]}
    vd.klayout.set_pcell_params("DUT", area=pick["area"]).check()
    log("   picked area %g um^2 (L_series %.3f nH vs target %.3f nH)" % (pick["area"], pick["L_series_nH"], target * 1e9))

    log("5 FastHenry: final EM run, results into the PCell")
    em = vd.em.fasthenry({"metalWidth": 4.0, "area": pick["area"]}, freqs_hz=[1e9, 5e9, 10e9, 20e9]).check().result
    report["runs"]["em_final"] = em["run_id"]
    report["em"] = {"reference": em["reference"], "results": em["results"], "limits": em["limits"]}
    vd.klayout.annotate("DUT", em["annotation"], "FASTHENRY %s" % em["run_id"]).check()
    log("5b FasterCap: parasitic capacitance of the same coil")
    cap = vd.em.fastercap({"metalWidth": 4.0, "area": pick["area"]}).check().result
    report["runs"]["cap_final"] = cap["run_id"]
    report["cap"] = {k: cap[k] for k in ("C_AB_fF", "C_A_gnd_fF", "C_B_gnd_fF", "dielectric_er", "limits")}
    log("   C between halves %.1f fF, half P1-P3 to substrate %.1f fF, half P3-P2 %.1f fF  run %s" % (
        cap["C_AB_fF"], cap["C_A_gnd_fF"], cap["C_B_gnd_fF"], cap["run_id"]))
    report["runs"]["layout_screenshot"] = vd.klayout.screenshot().check().result["local_path"]
    desc = vd.klayout.describe("DUT").check().result
    report["layout"] = {"bbox_um": desc["bbox_um"], "params": desc["params"]}

    log("6 back-annotate the extracted coil and re-simulate")
    cb_best = best["CB"]
    cases = [dict(OFF, label="baseline: no T-coil"),
             dict({k: best[k] for k in ("LA", "LB", "KC", "CB", "RA", "RB")}, label="ideal T-coil (optimizer)"),
             coil_case("extracted, P1 at drain", em, "A"),
             coil_case("extracted, P2 at drain", em, "B")]
    first = sweep(vd, netlist, cases=cases)
    ext = {c["label"]: c for c in first["points"][2:]}
    orient = "A" if ext["extracted, P1 at drain"]["f3db_hz"] >= ext["extracted, P2 at drain"]["f3db_hz"] else "B"
    cbs = ["1e-18", "2e-15", "5e-15", "10e-15", "20e-15", "30e-15"]
    cbsweep = sweep(vd, netlist, cases=[coil_case("C_B=%s" % cb, em, orient, cb) for cb in cbs])
    okcb = [q for q in cbsweep["points"] if q.get("f3db_hz") and q["peaking_db"] <= a.peaking_db]
    best_cb = max(okcb, key=lambda q: q["f3db_hz"]) if okcb else None
    final_cases = cases + ([dict(coil_case("extracted + C_B=%s" % eng(float(best_cb["CB"]), "F"), em, orient,
                                           best_cb["CB"]))] if best_cb else [])
    # L from FastHenry + C from FasterCap, both orientations, then the best extra explicit C_B
    lc = [coil_lc_case("L+C extracted, P1 at drain", em, cap, cl, "A"),
          coil_lc_case("L+C extracted, P2 at drain", em, cap, cl, "B")]
    lc_first = sweep(vd, netlist, cases=lc)
    lc_orient = "A" if lc_first["points"][0]["f3db_hz"] >= lc_first["points"][1]["f3db_hz"] else "B"
    extras = [0.0, 2e-15, 5e-15, 10e-15, 20e-15]
    lc_cb = sweep(vd, netlist, cases=[coil_lc_case("+%g" % e, em, cap, cl, lc_orient, e) for e in extras])
    ok_lc = [(e, q) for e, q in zip(extras, lc_cb["points"]) if q.get("f3db_hz") and q["peaking_db"] <= a.peaking_db]
    report["runs"]["lc_cb_sweep"] = lc_cb["run_id"]
    final_cases += lc
    if ok_lc:
        e_best = max(ok_lc, key=lambda eq: eq[1]["f3db_hz"])[0]
        if e_best > 0:
            final_cases.append(coil_lc_case("L+C extracted + C_B extra %s" % eng(e_best, "F"), em, cap, cl,
                                            lc_orient, e_best))
    final = sweep(vd, netlist, cases=final_cases)
    report["runs"]["compare"] = final["run_id"]
    report["runs"]["cb_sweep"] = cbsweep["run_id"]
    report["compare"] = [{k: q.get(k) for k in ("label", "dc_gain_db", "f3db_hz", "peaking_db", "LA", "LB",
                                                 "KC", "CB", "RA", "RB", "CPX", "CPY", "CL")} for q in final["points"]]
    report["compare_plot"] = final["local_images"]
    # Plausibility: an ideal T-coil extends an RC pole by about 2.83x at most.
    report["checks"] = []
    for q in final["points"]:
        x = q["f3db_hz"] / b["f3db_hz"]
        if x > 3.1:
            report["checks"].append("%s: %.2fx exceeds the ~2.83x T-coil limit; check the testbench" % (q["label"], x))
    for q in final["points"]:
        log("   %-34s gain %6.2f dB  f3dB %9s  peaking %.2f dB  (x%.2f)" % (
            q["label"], q["dc_gain_db"], eng(q["f3db_hz"], "Hz"), q["peaking_db"], q["f3db_hz"] / b["f3db_hz"]))

    # Show the chosen extracted case live: set the schematic's .param line, simulate, graphs on it.
    chosen = final["points"][-1]
    code = "\n".join([
        ".param LA=%s LB=%s KC=%s CB=%s RA=%s RB=%s" % tuple(chosen[k] for k in ("LA", "LB", "KC", "CB", "RA", "RB")),
        ".param CL=%s RT=%g CPX=%s CPY=%s" % (chosen.get("CL", a.cl), RT, chosen.get("CPX", "1e-18"),
                                              chosen.get("CPY", "1e-18")), "KCOIL LCA LCB {KC}",
        ".control", "save all", "op", "ac dec 40 1e8 2e11", "write tcoil_amp.raw", ".endc"])
    vd.xschem.set_props("NGSPICE", {"value": code}).check()
    vd.xschem.save().check()
    live = vd.sim.xschem(["out"]).check().result
    report["runs"]["live_sim"] = live["run_id"]
    report["runs"]["schematic_with_graphs"] = vd.xschem.screenshot().check().result["local_path"]

    log("7 report")
    rdir = Path(vd.transport.to_local(vd.cfg.remote_dir + "/runs/closedloop_" + time.strftime("%Y%m%d_%H%M%S")))
    rdir.mkdir(parents=True, exist_ok=True)
    report["seconds"] = round(time.time() - t_start, 1)
    (rdir / "report.json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    lines = ["# T-coil bandwidth extension, SKY130 (Viaduct closed loop)", "",
             "Driver: cascode nfet_01v8 W=%sum nf=%s L=0.15um each, VIN dc %s V, VB %s V; termination %g ohm; "
             "C_L=%s at the tap; tt." % (a.w, a.nf, a.vin, a.vb, RT, a.cl), "",
             "| case | gain (dB) | f3dB | x baseline | peaking (dB) |", "|---|---|---|---|---|"]
    for q in final["points"]:
        lines.append("| %s | %.2f | %s | %.2f | %.2f |" % (q["label"], q["dc_gain_db"], eng(q["f3db_hz"], "Hz"),
                                                           q["f3db_hz"] / b["f3db_hz"], q["peaking_db"]))
    r10 = em["reference"]
    lines += ["", "Coil: VIADUCT_SKY130 TCoil W=4 um, area=%g um^2, FastHenry run %s at %.3g GHz: L1=%.4f nH, "
              "L2=%.4f nH, K1=%.4f, Q1=%.2f, Q2=%.2f (quasi-static: no substrate, no inter-winding C)." % (
                  pick["area"], em["run_id"], r10["frequency_hz"] / 1e9, r10["L1_nH"], r10["L2_nH"], r10["K1"],
                  r10["Q1"], r10["Q2"]),
              "FasterCap run %s: C between halves %.1f fF, to substrate %.1f fF (P1-P3 half) and %.1f fF "
              "(P3-P2 half); homogeneous er=%g, substrate as ground plane." % (
                  cap["run_id"], cap["C_AB_fF"], cap["C_A_gnd_fF"], cap["C_B_gnd_fF"], cap["dielectric_er"]),
              "Ideal optimum (peaking <= %.2f dB): L1=L2=%s, k=%s, C_B=%s; series-L target %.3f nH." % (
                  a.peaking_db, eng(l_ideal, "H"), k_ideal, eng(float(best["CB"]), "F"), target * 1e9), "",
              "Runs: " + ", ".join("%s=%s" % kv for kv in report["runs"].items() if "screenshot" not in kv[0])]
    lines += ["", "Checks: " + ("; ".join(report["checks"]) if report["checks"]
                                else "all extensions within the T-coil limit")]
    lines += ["", "Notes:",
              "- The extracted coil is a lumped L/R/K model from quasi-static FastHenry at the reference "
              "frequency: no inter-winding capacitance, no self-resonance, no substrate loss. Treat the extracted "
              "rows as estimates; the response far above the -3 dB points (bumps near 100 GHz) is not meaningful. "
              "A full-wave cross-check (openEMS) of one point is the next step.",
              "- Grid-edge results (an optimum C_B at the largest value tried) mean a wider grid may do better.",
              "- The coil's tap is off-centre (L1 ~ 1.8 x L2), so the symmetric ideal optimum cannot be matched "
              "exactly; the better orientation puts the shorter half (P2) at the drain.",
              "- Gain is below 0 dB: a 50-ohm-terminated driver with gm*R < 1; the study is about bandwidth."]
    (rdir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    log("done in %.0fs -> %s" % (report["seconds"], rdir))
    report["report_dir"] = str(rdir)
    return report, rdir


if __name__ == "__main__":
    main()
