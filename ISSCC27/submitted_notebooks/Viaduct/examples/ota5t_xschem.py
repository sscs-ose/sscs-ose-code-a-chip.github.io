"""Build a SKY130 five-transistor OTA (NMOS input pair, PMOS mirror load) live in xschem,
check its connectivity, simulate it and report the operating point of every transistor.

    python examples/ota5t_xschem.py [--replace] [--l-in 0.5 --w-in 10 ...]

    M1/M2  NMOS input pair          M3/M4  PMOS current-mirror load (M3 diode-connected)
    M5     NMOS tail current source M6 + IBIAS  bias mirror (testbench, not one of the five)
    VDD 1.8 V, inputs at VCM (AC 1 on INP), CL on OUT, SKY130 tt corner.

Default sizes come from examples/ota5t_sweep.py: L = 1 um for the pair and the load
(41.9 dB, UGF 54 MHz, 73 deg phase margin in unity feedback); L = 0.5 um gives 36.7 dB, longer L buys < 1 dB more.

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
write ota5t.raw
.endc"""


def build(x, a):
    um = lambda v: "%g" % v  # noqa: E731
    with x.batch() as b:
        b.add("new_schematic", path=a.out, replace=a.replace)
        # PMOS mirror: gates face each other.  NMOS pair: gates face outward (the inputs).
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
        for m in ("M3", "M4"):
            b.label_pin(m, "S", "VDD")
            b.label_pin(m, "B", "VDD")
        for m in ("M1", "M2", "M5"):
            b.label_pin(m, "B", "GND")
        b.label_pin("M5", "S", "GND")
        b.label_pin("M1", "G", "INP")
        b.label_pin("M2", "G", "INN")
        b.label_pin("M5", "G", "NB")
        b.wire(220, -100, 300, -100)               # output tap off the right drain wire
        b.place("lab_pin.sym", 300, -100, rot=2, lab="OUT")
        # testbench: bias mirror, supply, inputs, load, models, analyses
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
        b.place("vsource.sym", -320, -100, name="VINN", value="dc %g" % a.vcm)
        b.place("capa.sym", 380, -70, name="CL", value="%gf" % a.cl_ff)
        for src, plus in (("VSUP", "VDD"), ("VINP", "INP"), ("VINN", "INN"), ("CL", "OUT")):
            b.label_pin(src, "p", plus)
            b.label_pin(src, "m", "GND")
        b.place("sky130_fd_pr/corner.sym", -520, 150, corner="tt")
        b.place("devices/code_shown.sym", 330, 120, name="NGSPICE", only_toplevel="true", value=CONTROL)
        b.add("zoom_fit")
        b.add("save")
    return b.result


def parse(argv=None):
    """Arguments (sizes in um, IBIAS in uA, CL in fF); parse([]) gives the defaults."""
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--out", default="/foss/designs/viaduct/xschem/ota5t.sch")
    p.add_argument("--replace", action="store_true", help="overwrite --out if it exists")
    p.add_argument("--w-in", type=float, default=20.0)
    p.add_argument("--l-in", type=float, default=1.0)
    p.add_argument("--w-load", type=float, default=16.0)
    p.add_argument("--l-load", type=float, default=1.0)
    p.add_argument("--w-tail", type=float, default=16.0)
    p.add_argument("--l-tail", type=float, default=1.0)
    p.add_argument("--ibias-ua", type=float, default=20.0)
    p.add_argument("--vdd", type=float, default=1.8)
    p.add_argument("--vcm", type=float, default=0.9)
    p.add_argument("--cl-ff", type=float, default=500.0)
    return p.parse_args(argv)


def run(vd, a):
    """Build, check, simulate and bias-check the OTA; returns the report dict."""
    t0 = time.time()
    x = vd.xschem
    built = build(x, a)
    chk = x.check().check().result
    if not chk["ok"]:
        raise ViaductError("connectivity check failed: %s" % json.dumps(chk["warnings"]))
    sim = vd.sim.xschem(nodes=("out",)).check().result
    ac = sim["raw_files"][0]["plots"][-1]["nodes"]["out"]
    op = vd.sim.op().check().result
    shot = x.screenshot("/foss/designs/viaduct/runs/ota5t.png").result
    report = {
        "schematic": a.out, "build_ops": built.result["done"], "check": "ok",
        "sim_run": sim["run_id"], "op_run": op["run_id"],
        "dc_gain_db": round(ac["dc_gain_db"], 2), "f3db_hz": round(ac["f3db_hz"]),
        "ugf_hz": round(ac["ugf_hz"]),
        # phase margin as a unity-gain buffer: there the loop gain is exactly this A(s)
        "phase_margin_unity_fb_deg": round(180 + ac["phase_at_ugf_deg"], 1),
        "tail_current_ua": op["devices"]["M5"]["id_ua"], "out_dc_v": round(op["nodes"]["out"], 4),
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
