"""Build a SKY130 resistor-loaded common-source amplifier testbench live in xschem,
then simulate it and show the waveforms on the schematic.

    python examples/cs_amp_xschem.py [--out /foss/designs/viaduct/xschem/cs_amp.sch] [--replace]

Every instance and wire appears in the xschem window on the noVNC desktop as the
script runs.
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from viaduct import Viaduct  # noqa: E402
from viaduct.schematic import Builder  # noqa: E402


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", default="/foss/designs/viaduct/xschem/cs_amp.sch")
    p.add_argument("--replace", action="store_true", help="overwrite --out if it exists")
    p.add_argument("--vin-dc", default="0.9")
    a = p.parse_args()
    t0 = time.time()
    vd = Viaduct.from_env()
    sb = Builder(vd)

    sb.new(a.out, a.replace)
    # Amplifier: M1 at the origin. nfet_01v8 pins: D(20,-30) G(-20,0) S(20,30) B(20,0)
    sb.place("sky130_fd_pr/nfet_01v8.sym", 0, 0, name="M1", W="2", L="0.15", nf="1")
    sb.place("res.sym", 20, -100, name="R1", value="2k")          # P(20,-130) M(20,-70)
    sb.place("capa.sym", 100, -20, name="CL", value="50f")        # p(100,-50) m(100,10)
    sb.wire(20, -70, 20, -50)
    sb.wire(20, -50, 20, -30)
    sb.wire(20, -50, 100, -50)
    sb.wire(100, -50, 140, -50)
    sb.label("OUT", 140, -50, rot=2)
    sb.wire(20, -130, 20, -160)
    sb.label("VDD", 20, -160)
    sb.wire(-20, 0, -80, 0)
    sb.label("IN", -80, 0)
    sb.wire(20, 30, 20, 60)
    sb.gnd(20, 60)
    sb.wire(20, 0, 50, 0, 50, 60)
    sb.gnd(50, 60)
    sb.wire(100, 10, 100, 60)
    sb.gnd(100, 60)
    # Sources
    sb.place("vsource.sym", -300, -100, name="VDD", value="1.8")
    sb.wire(-300, -130, -300, -160)
    sb.label("VDD", -300, -160)
    sb.wire(-300, -70, -300, -40)
    sb.gnd(-300, -40)
    sb.place("vsource.sym", -200, -100, name="VIN", value="dc %s ac 1" % a.vin_dc)
    sb.wire(-200, -130, -200, -160)
    sb.label("IN", -200, -160)
    sb.wire(-200, -70, -200, -40)
    sb.gnd(-200, -40)
    # Models and analysis
    sb.place("sky130_fd_pr/corner.sym", -300, 120, corner="tt")
    sb.code(100, 120, ".control\nsave all\nop\nac dec 20 1e5 1e11\nwrite cs_amp.raw\n.endc")

    nl = sb.finish()
    sim = vd.sim.xschem(nodes=["out"]).check().result
    out = sim["raw_files"][0]["plots"][0]["nodes"]["out"]
    shot = vd.xschem.screenshot().check().result
    print(json.dumps({"schematic": a.out, "netlist": nl["path"], "run_id": sim["run_id"],
                      "dc_gain_db": out["dc_gain_db"], "f3db_hz": out["f3db_hz"],
                      "bode": sim["local_images"], "screenshot": shot["local_path"],
                      "seconds": round(time.time() - t0, 1)}, indent=2))


if __name__ == "__main__":
    main()
