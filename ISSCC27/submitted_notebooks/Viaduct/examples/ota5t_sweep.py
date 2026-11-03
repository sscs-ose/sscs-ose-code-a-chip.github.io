"""Sweep the channel lengths of the 5T OTA in one ngspice run: input pair (M1/M2) and
mirror load (M3/M4), keeping each W/L constant so the overdrive stays put.

    python examples/ota5t_sweep.py [--l 0.5 1 1.5 2]

Takes the netlist of the OTA open in xschem (examples/ota5t_xschem.py), turns the M1-M4
sizes into .params (diffusion areas/perimeters follow W), runs Viaduct's sim sweep over
every (L_in, L_load) pair and prints gain, f3dB, UGF and phase margin per point.
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from viaduct import Viaduct  # noqa: E402

GROUPS = {"XM1": ("LIN", "WIN"), "XM2": ("LIN", "WIN"), "XM3": ("LLD", "WLD"), "XM4": ("LLD", "WLD")}


def parameterize(netlist):
    """Replace the literal L/W (and the W-derived ad/as/pd/ps) of M1-M4 by .param expressions.
    Returns (text, defaults)."""
    out, defaults = [], {}
    for line in netlist.splitlines():
        inst = line.split(" ", 1)[0]
        if inst in GROUPS:
            ln, wn = GROUPS[inst]
            defaults[ln] = float(re.search(r"\bL=(\S+)", line).group(1))
            defaults[wn] = float(re.search(r"\bW=(\S+)", line).group(1))
            line = re.sub(r"\bL=\S+", "L={%s}" % ln, line)
            line = re.sub(r"\bW=\S+", "W={%s}" % wn, line)
            # nf=1 SKY130 symbol formulas: ad = as = 0.29*W, pd = ps = 2*(W+0.29)
            for k, expr in (("ad", "{0.29*%s}"), ("as", "{0.29*%s}"), ("pd", "{2*(%s+0.29)}"), ("ps", "{2*(%s+0.29)}")):
                line = re.sub(r"\b%s=\S+" % k, "%s=%s" % (k, expr % wn), line)
        out.append(line)
    params = ".param " + " ".join("%s=%g" % kv for kv in sorted(defaults.items()))
    text = "\n".join(out)
    text = text.replace("**** begin user architecture code", params + "\n**** begin user architecture code", 1)
    return text, defaults


def sweep(vd, lengths=(0.5, 1.0, 1.5, 2.0)):
    """Every (L_in, L_load) pair of `lengths` (um), W/L kept; returns the sweep result."""
    nl = vd.xschem.netlist().check().result
    text, d = parameterize(nl["netlist"])
    remote = "/foss/designs/viaduct/runs/ota5t_param.spice"
    Path(vd.transport.to_local(remote)).write_text(text + "\n", encoding="utf-8", newline="\n")
    ratio_in, ratio_ld = d["WIN"] / d["LIN"], d["WLD"] / d["LLD"]
    cases = [{"label": "Lin=%g Lload=%g" % (li, ll), "LIN": li, "WIN": round(ratio_in * li, 3),
              "LLD": ll, "WLD": round(ratio_ld * ll, 3)} for li in lengths for ll in lengths]
    return vd.sim.sweep(remote, cases=cases, node="out", ac="dec 20 1 1e10").check().result


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--l", type=float, nargs="+", default=[0.5, 1.0, 1.5, 2.0])
    a = p.parse_args()
    vd = Viaduct.from_env()
    r = sweep(vd, a.l)
    print("run %s, %d points in %.1f s (one ngspice process)" % (r["run_id"], r["count"], r["seconds"]))
    print("%-20s %8s %10s %10s %7s" % ("case", "gain_dB", "f3dB_kHz", "UGF_MHz", "PM_deg"))
    for pt in r["points"]:
        pm = 180 + pt["phase_at_ugf_deg"] if pt.get("phase_at_ugf_deg") is not None else float("nan")
        print("%-20s %8.2f %10.1f %10.2f %7.1f" % (pt["label"], pt["dc_gain_db"], pt["f3db_hz"] / 1e3,
                                                  (pt["ugf_hz"] or 0) / 1e6, pm))
    print(json.dumps({"points_csv": vd.transport.to_local(r["run_dir"] + "/points.csv")}))


if __name__ == "__main__":
    main()
