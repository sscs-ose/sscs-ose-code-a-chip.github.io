"""Build a SKY130 two-stage Miller op amp live in xschem, check its connectivity, simulate it
and report the operating point of every transistor.

    python examples/opamp2s_xschem.py [--replace] [--cc-ff 1000 --rz-k 3 --w2 96 ...]

    stage 1  the five-transistor OTA of ota5t_xschem.py: M1/M2 NMOS pair, M3/M4 PMOS mirror,
             M5 NMOS tail; its output is node X. Stage 2 inverts, so INP drives M2 here
             (M1 in the OTA) and stays the non-inverting input of the op amp
    stage 2  M7 PMOS common source (gate on X), M8 NMOS current source, output OUT
    CC, RZ   Miller capacitor with a nulling resistor in series, from X to OUT
    M6 + IBIAS  bias mirror for M5 and M8 (testbench)
    VDD 1.8 V, INP at VCM with AC 1, CL on OUT, SKY130 tt corner.

The open-loop gain needs the output biased in the middle of its range, which an open loop with
~70 dB of gain cannot hold. The testbench closes the loop for DC only: OUT drives INN through a
1 GH inductor and INN is held at AC ground by 1 F, so the operating point is the one of a
unity-gain buffer while the AC response is the open-loop gain from INP to OUT.

M7 is sized for no systematic offset: (W/L)7 / (W/L)4 = 2 (W/L)8 / (W/L)5, so with the defaults
M8 carries 3 x the tail current and M7 is 6 x M4.

Everything is wired by instance and pin name (wire_pins / label_pin), so no pin
coordinates are computed here; `check` must report no floating pins before simulating.
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from viaduct import Viaduct, ViaductError  # noqa: E402

N, P = "sky130_fd_pr/nfet_01v8.sym", "sky130_fd_pr/pfet_01v8.sym"
CONTROL = """.control
save all
op
ac dec 20 1 1e10
write opamp2s.raw
.endc"""


def build(x, a):
    um = lambda v: "%g" % v  # noqa: E731
    with x.batch() as b:
        b.add("new_schematic", path=a.out, replace=a.replace)
        # stage 1, as in ota5t_xschem.py; its output (the M2/M4 drains) is X
        b.place(P, 0, -200, flip=1, name="M3", W=um(a.w_load), L=um(a.l_load), nf="1")
        b.place(P, 200, -200, name="M4", W=um(a.w_load), L=um(a.l_load), nf="1")
        b.place(N, -40, 0, name="M1", W=um(a.w_in), L=um(a.l_in), nf="1")
        b.place(N, 240, 0, flip=1, name="M2", W=um(a.w_in), L=um(a.l_in), nf="1")
        b.place(N, 80, 150, name="M5", W=um(a.w_tail), L=um(a.l_tail), nf="1")
        b.wire_pins("M3", "D", "M1", "D")
        b.wire_pins("M4", "D", "M2", "D")
        b.wire_pins("M3", "G", "M4", "G")
        b.wire_pins("M3", "D", "M3", "G")          # diode connection
        b.wire_pins("M1", "S", "M5", "D")          # tail node
        b.wire(220, 30, 100, 30)                   # M2 source onto the tail wire corner
        b.wire(220, -100, 300, -100)               # stage-1 output tap off the right drain wire
        b.place("lab_pin.sym", 300, -100, rot=2, lab="X")
        # stage 2: PMOS common source on X, NMOS current source mirrored from the bias
        b.place(P, 460, -200, name="M7", W=um(a.w2), L=um(a.l2), nf="1")
        b.place(N, 460, 150, name="M8", W=um(a.w8), L=um(a.l_tail), nf="1")
        b.wire_pins("M7", "D", "M8", "D")
        b.label_pin("M7", "G", "X")
        b.label_pin("M8", "G", "NB")
        b.label_pin("M7", "D", "OUT")
        # Miller compensation: X - RZ - Z - CC - OUT
        b.place("res.sym", 360, -40, name="RZ", value="%gk" % a.rz_k)
        b.place("capa.sym", 360, 80, name="CC", value="%gf" % a.cc_ff)
        b.label_pin("RZ", "P", "X")
        b.label_pin("RZ", "M", "Z")
        b.label_pin("CC", "p", "Z")
        b.label_pin("CC", "m", "OUT")
        for m in ("M3", "M4", "M7"):
            b.label_pin(m, "S", "VDD")
            b.label_pin(m, "B", "VDD")
        for m in ("M1", "M2", "M5", "M8"):
            b.label_pin(m, "B", "GND")
        b.label_pin("M5", "S", "GND")
        b.label_pin("M8", "S", "GND")
        # stage 2 inverts, so the pair's inputs swap against the OTA: INP stays the + input
        b.label_pin("M1", "G", "INN")
        b.label_pin("M2", "G", "INP")
        b.label_pin("M5", "G", "NB")
        # testbench: bias mirror, supply, input, DC feedback, load, models, analyses (DC feedback,
    # load and analyses below the circuit: sim.xschem puts its graphs at x >= 600, y < 240)
        b.place(N, -200, 150, name="M6", W=um(a.w_tail), L=um(a.l_tail), nf="1")
        b.place("isource.sym", -180, 40, name="IBIAS", value="%gu" % a.ibias_ua)
        b.wire_pins("IBIAS", "m", "M6", "D")
        b.wire_pins("M6", "D", "M6", "G")
        b.label_pin("M6", "G", "NB")
        b.label_pin("M6", "S", "GND")
        b.label_pin("M6", "B", "GND")
        b.label_pin("IBIAS", "p", "VDD")
        b.place("vsource.sym", -520, -100, name="VSUP", value="%g" % a.vdd)
        b.place("vsource.sym", -420, -100, name="VINP", value="dc %g ac 1" % a.vcm)
        b.place("ind.sym", 480, 400, name="LFB", value="1G")      # DC feedback OUT -> INN
        b.place("capa.sym", 580, 400, name="CFB", value="1")      # INN at AC ground
        b.place("capa.sym", 380, 400, name="CL", value="%gf" % a.cl_ff)
        for src, plus, minus in (("VSUP", "VDD", "GND"), ("VINP", "INP", "GND"), ("LFB", "OUT", "INN"),
                                 ("CFB", "INN", "GND"), ("CL", "OUT", "GND")):
            b.label_pin(src, "p", plus)
            b.label_pin(src, "m", minus)
        b.place("sky130_fd_pr/corner.sym", -520, 150, corner="tt")
        b.place("devices/code_shown.sym", 680, 330, name="NGSPICE", only_toplevel="true", value=CONTROL)
        b.add("zoom_fit")
        b.add("save")
    return b.result


def parse(argv=None):
    """Arguments (sizes in um, IBIAS in uA, capacitors in fF, RZ in kohm); parse([]) gives the defaults."""
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--out", default="/foss/designs/viaduct/xschem/opamp2s.sch")
    p.add_argument("--replace", action="store_true", help="overwrite --out if it exists")
    p.add_argument("--w-in", type=float, default=20.0)
    p.add_argument("--l-in", type=float, default=1.0)
    p.add_argument("--w-load", type=float, default=16.0)
    p.add_argument("--l-load", type=float, default=1.0)
    p.add_argument("--w-tail", type=float, default=16.0)
    p.add_argument("--l-tail", type=float, default=1.0)
    p.add_argument("--w2", type=float, default=96.0, help="M7 width")
    p.add_argument("--l2", type=float, default=1.0, help="M7 length")
    p.add_argument("--w8", type=float, default=48.0, help="M8 width (L as the tail)")
    p.add_argument("--cc-ff", type=float, default=1000.0)
    p.add_argument("--rz-k", type=float, default=3.0)
    p.add_argument("--ibias-ua", type=float, default=20.0)
    p.add_argument("--vdd", type=float, default=1.8)
    p.add_argument("--vcm", type=float, default=0.9)
    p.add_argument("--cl-ff", type=float, default=1000.0)
    return p.parse_args(argv)


def run(vd, a):
    """Build, check, simulate and bias-check the op amp; returns the report dict."""
    t0 = time.time()
    x = vd.xschem
    built = build(x, a)
    chk = x.check().check().result
    if not chk["ok"]:
        raise ViaductError("connectivity check failed: %s" % json.dumps(chk["warnings"]))
    sim = vd.sim.xschem(nodes=("out",)).check().result
    ac = sim["raw_files"][0]["plots"][-1]["nodes"]["out"]
    op = vd.sim.op().check().result
    shot = x.screenshot("/foss/designs/viaduct/runs/opamp2s.png").result
    supply_ua = op["devices"]["M5"]["id_ua"] + op["devices"]["M8"]["id_ua"] + a.ibias_ua
    report = {
        "schematic": a.out, "build_ops": built.result["done"], "check": "ok",
        "sim_run": sim["run_id"], "op_run": op["run_id"],
        "dc_gain_db": round(ac["dc_gain_db"], 2), "f3db_hz": round(ac["f3db_hz"]),
        "ugf_hz": round(ac["ugf_hz"]),
        # phase margin as a unity-gain buffer: there the loop gain is exactly this A(s)
        "phase_margin_unity_fb_deg": round(180 + ac["phase_at_ugf_deg"], 1),
        "tail_current_ua": op["devices"]["M5"]["id_ua"], "stage2_current_ua": op["devices"]["M8"]["id_ua"],
        "power_uw": round(supply_ua * a.vdd, 1),
        "x_dc_v": round(op["nodes"]["x"], 4), "out_dc_v": round(op["nodes"]["out"], 4),
        "devices": {k: {f: v[f] for f in ("id_ua", "vov", "vds_margin", "gm_us", "region")}
                    for k, v in op["devices"].items()},
        "bias_warnings": op["warnings"], "screenshot": shot["local_path"],
        "seconds": round(time.time() - t0, 1)}
    return report


def main():
    report = run(Viaduct.from_env(), parse())
    print(json.dumps(report, indent=2))
    return 0 if not report["bias_warnings"] else 2


if __name__ == "__main__":
    sys.exit(main())
