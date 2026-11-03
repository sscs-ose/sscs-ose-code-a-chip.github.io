"""Characterize the 5T OTA open in xschem (examples/ota5t_xschem.py) beyond its AC response:

    python examples/ota5t_characterize.py

  1. step response as a unity-gain buffer: slew rate (rise / fall), 1 % settling, overshoot
  2. CMRR: differential vs common-mode gain at 10 Hz
  3. input common-mode range: buffer DC sweep, where every OTA transistor stays saturated
  4. output swing: open-loop DC transfer, where the small-signal gain is >= half its peak

Each testbench is derived from the schematic's own netlist (OTA, bias mirror, supply and
models kept; sources, load and analyses replaced) and run through Viaduct's sim runner.
"""
import json
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from viaduct import Viaduct  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "container"))
import ngspice_runner as ng  # noqa: E402  (pure netlist helpers only)

RUNS = "/foss/designs/viaduct/runs"
VCM, STEP = 0.9, 0.3


def core(netlist):
    """The schematic netlist without its input sources, load and analyses."""
    keep = []
    for line in netlist.splitlines():
        if re.match(r"^(VINP|VINN|CL)\s", line) or line.strip().lower() in (".end", "**.ends"):
            continue
        keep.append(line)
    text = "\n".join(keep)
    return re.sub(r"^\.control\b.*?^\.endc[^\n]*\n?", "", text, flags=re.S | re.M | re.I)


def follower(text):
    """Unity-gain buffer: the inverting input (M2 gate) tied to OUT."""
    return re.sub(r"^(XM2 OUT )INN ", r"\1OUT ", text, flags=re.M)


def _sim(vd, name, text, nodes=("out",)):
    remote = "%s/ota5t_%s.spice" % (RUNS, name)
    Path(vd.transport.to_local(remote)).write_text(text + "\n.end\n", encoding="utf-8", newline="\n")
    r = vd.sim.run(remote, nodes=list(nodes)).check().result
    log = Path(vd.transport.to_local(r["run_dir"] + "/ngspice.log")).read_text(errors="replace")
    meas = {m.group(1).lower(): float(m.group(2))
            for m in re.finditer(r"^\s*(\w+)\s*=\s*([-+0-9.eE]+)", log, re.M)}
    return r, meas


def table(vd, r, name):
    d = np.loadtxt(vd.transport.to_local("%s/%s" % (r["run_dir"], name)))
    return d[:, 0], d[:, 1]


def characterize(vd):
    """All four testbenches on the OTA open in xschem; returns the results dict."""
    nl = vd.xschem.netlist().check().result["netlist"]
    base = core(nl)
    cl = re.search(r"^CL OUT GND (\S+)", nl, re.M).group(1)
    out = {"cl": cl}

    # 1. step response, unity-gain buffer. Settling and overshoot are measured against the
    #    actual final value: with finite gain the buffer settles slightly below the input.
    lo, hi, t_up, t_dn = VCM, VCM + STEP, 20e-9, 220e-9
    tb = follower(base) + """
VINP INP GND pulse(%g %g %g 100p 100p 200n 400n)
CL OUT GND %s
.control
tran 20p 400n
wrdata ota5t_step.txt v(out)
write ota5t_step.raw
.endc""" % (lo, hi, t_up, cl)
    r, _ = _sim(vd, "step", tb, nodes=("out", "inp"))
    t, v = table(vd, r, "ota5t_step.txt")
    edges = {}
    for name, t0, t1 in (("rise", t_up, t_dn), ("fall", t_dn, t[-1])):
        w = (t >= t0) & (t < t1)
        tw, vw = t[w], v[w]
        v_start = float(np.interp(t0 - 1e-12, t, v))
        v_final = float(vw[-1])
        span = v_final - v_start
        frac = (vw - v_start) / span
        t10 = float(tw[np.argmax(frac >= 0.1)])
        t90 = float(tw[np.argmax(frac >= 0.9)])
        outside = np.flatnonzero(np.abs(vw - v_final) > 0.01 * abs(span))
        t_settle = float(tw[outside[-1] + 1]) if outside.size and outside[-1] + 1 < tw.size else float(tw[0])
        edges[name] = {"slew_v_per_us": round(0.8 * abs(span) / (t90 - t10) / 1e6, 2),
                       "settle_1pct_ns": round((t_settle - t0) * 1e9, 2),
                       "overshoot_pct": round(max(0.0, float(np.max(frac) - 1)) * 100, 2),
                       "final_v": round(v_final, 4), "static_error_mv": round(
                           (v_final - (hi if name == "rise" else lo)) * 1e3, 2)}
    out["step"] = {"run": r["run_id"], "step_v": STEP, **edges,
                   "plot": vd.transport.to_local(r["images"][0]) if r["images"] else None}

    # 2. CMRR at 10 Hz
    tb = base + """
VINP INP GND dc %g ac 1
VINN INN GND dc %g ac 0
CL OUT GND %s
.control
ac dec 20 1 1e9
meas ac adm find vdb(out) at=10
alter @vinn[acmag]=1
ac dec 20 1 1e9
meas ac acm find vdb(out) at=10
write ota5t_cmrr.raw
.endc""" % (VCM, VCM, cl)
    r, m = _sim(vd, "cmrr", tb)
    out["cmrr"] = {"run": r["run_id"], "adm_db": round(m["adm"], 2), "acm_db": round(m["acm"], 2),
                   "cmrr_db": round(m["adm"] - m["acm"], 2)}

    # 3. input common-mode range: buffer, VINP swept rail to rail. The range is where every
    #    transistor of the OTA stays saturated (|Vds| > Vdsat); output tracking alone is not
    #    enough, a dead amplifier near a rail can still sit within millivolts of its input.
    fets = [(n, path) for n, path, _ in ng.op_devices(base) if n in ("M1", "M2", "M3", "M4", "M5")]
    vecs = " ".join("%s[%s]" % (path, q) for _, path in fets for q in ("vds", "vdsat"))
    tb = follower(base) + """
VINP INP GND dc 0.9
CL OUT GND %s
.control
save v(out) %s
dc vinp 0 1.8 0.005
wrdata ota5t_icmr.txt v(out) %s
write ota5t_icmr.raw
.endc""" % (cl, vecs, vecs)
    r, _ = _sim(vd, "icmr", tb)
    d = np.loadtxt(vd.transport.to_local(r["run_dir"] + "/ota5t_icmr.txt"))
    vin, cols = d[:, 0], d[:, 1::2]                      # wrdata: (scale, value) per vector
    vout = cols[:, 0]
    margins = {n: np.abs(cols[:, 1 + 2 * i]) - np.abs(cols[:, 2 + 2 * i]) for i, (n, _) in enumerate(fets)}
    sat = np.all(np.vstack(list(margins.values())) > 0, axis=0)
    i0 = int(np.argmin(np.abs(vin - VCM)))
    lo_i = hi_i = i0
    while lo_i > 0 and sat[lo_i - 1]:
        lo_i -= 1
    while hi_i < len(vin) - 1 and sat[hi_i + 1]:
        hi_i += 1
    limiter = lambda i: min(margins, key=lambda n: margins[n][i])  # noqa: E731
    out["icmr"] = {"run": r["run_id"], "criterion": "every OTA transistor saturated, unity-gain buffer",
                   "low_v": round(float(vin[lo_i]), 3), "low_limited_by": limiter(max(lo_i - 1, 0)),
                   "high_v": round(float(vin[hi_i]), 3), "high_limited_by": limiter(min(hi_i + 1, len(vin) - 1)),
                   "offset_at_vcm_mv": round(float(np.interp(VCM, vin, vout) - VCM) * 1e3, 2),
                   "max_tracking_error_in_range_mv": round(float(np.max(np.abs(vout - vin)[lo_i:hi_i + 1])) * 1e3, 2)}

    # 4. output swing: open loop, INN at VCM, INP swept finely around it
    tb = base + """
VINP INP GND dc %g
VINN INN GND dc %g
CL OUT GND %s
.control
dc vinp %g %g 0.00002
wrdata ota5t_swing.txt v(out)
write ota5t_swing.raw
.endc""" % (VCM, VCM, cl, VCM - 0.03, VCM + 0.03)
    r, _ = _sim(vd, "swing", tb)
    vin, vout = table(vd, r, "ota5t_swing.txt")
    gain = np.gradient(vout, vin)
    good = np.flatnonzero(gain >= 0.5 * gain.max())
    out["swing"] = {"run": r["run_id"], "criterion": "open-loop gain >= 50 % of its peak",
                    "peak_gain_vv": round(float(gain.max()), 1),
                    "out_low_v": round(float(vout[good].min()), 3), "out_high_v": round(float(vout[good].max()), 3)}
    return out


def main():
    print(json.dumps(characterize(Viaduct.from_env()), indent=2))


if __name__ == "__main__":
    main()
