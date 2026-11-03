"""A routed netlist with the delays of its SDF, for a timed simulation with cell models that have no specify blocks.

The SKY130 cell models of open_pdks are functional only (no specify paths), so $sdf_annotate has nothing to annotate.
This script gives every standard-cell instance one inertial delay on each of its outputs instead: the output net is
renamed, and `assign #(d) net = net_pre;` reconnects it, where d is the mean of the instance's IOPATH delays in the SDF
(rise and fall, the typical value of each triple) plus the mean INTERCONNECT delay into the instance's loads is left out
(sub-picosecond to a few ps on these blocks). An inertial delay suppresses pulses shorter than itself, as a gate does, so
the simulation shows the glitches that the arrival-time differences of a routed block produce, which a zero-delay
simulation cannot. The approximation: one delay per output instead of one per arc, no slew dependence.

usage: sdf_inertial_netlist.py <6_final.v> <netlist.sdf> <liberty> <out.v> [<report.json>]
SPDX-License-Identifier: Apache-2.0
"""
import json
import re
import statistics
import sys


def output_pins(lib):
    """cell -> list of output pin names, from the Liberty."""
    text = open(lib).read()
    out = {}
    for cm in re.finditer(r"\bcell\s*\(\s*\"?([\w]+)\"?\s*\)\s*\{", text):
        name, i, depth = cm[1], cm.end(), 1
        start = i
        while depth:
            depth += {"{": 1, "}": -1}.get(text[i], 0); i += 1
        body = text[start:i]
        pins = re.findall(r"\bpin\s*\(\s*\"?(\w+)\"?\s*\)\s*\{[^{}]*?direction\s*:\s*\"?output", body, re.S)
        out[name] = pins
    return out


def sdf_delays(sdf):
    """instance -> mean IOPATH delay (ns)."""
    text = open(sdf).read()
    d = {}
    for cell in re.finditer(r"\(CELL\s*\(CELLTYPE\s*\"[^\"]*\"\)\s*\(INSTANCE\s*([^)]*)\)(.*?)(?=\(CELL\s*\(CELLTYPE|\Z)", text, re.S):
        inst = cell[1].strip().replace("\\", "")
        vals = []
        for m in re.finditer(r"\(IOPATH\s+\S+\s+\S+((?:\s*\([^()]*\))+)\)", cell[2]):
            for trip in re.findall(r"\(([^()]*)\)", m[1]):
                parts = [p for p in trip.split(":") if p.strip()]
                if parts:
                    vals.append(float(parts[1] if len(parts) == 3 else parts[0]))
        if inst and vals:
            d[inst] = statistics.mean(vals)
    return d


def main(netlist, sdf, lib, out, report=None):
    outs = output_pins(lib)
    dly = sdf_delays(sdf)
    text = open(netlist).read()
    assigns, n_inst, used = [], 0, []

    def fix(m):
        nonlocal n_inst
        cell, inst, conns = m[1], m[2], m[3]
        key = inst.strip().lstrip("\\")
        if cell not in outs or key not in dly:
            return m[0]
        d = dly[key]
        def rename(pm):
            pin, net = pm[1], pm[2].strip()
            if pin not in outs[cell] or not net:
                return pm[0]
            pre = f"_pre{len(assigns)}_"
            assigns.append((pre, net, d))
            return f".{pin}({pre})"
        new = re.sub(r"\.(\w+)\s*\(\s*((?:\\\S+\s)|[^()]*?)\s*\)", rename, conns)
        if new != conns:
            n_inst += 1; used.append(d)
        return f" {cell} {inst} ({new});"
    body = re.sub(r"\s(sky130_fd_sc_hd__\w+)\s+(\\\S+\s|\S+)\s*\(((?:[^;])*?)\)\s*;", fix, text, flags=re.S)
    decl = "".join(f"  wire {p};\n" for p, _, _ in assigns)
    asg = "".join(f"  assign #({d:.4f}) {n} = {p};\n" for p, n, d in assigns)
    body = re.sub(r"\n\s*endmodule\s*$", lambda m: "\n" + asg + "endmodule\n", body.rstrip() + "\n", count=1)
    body = body.replace(");\n", ");\n" + decl, 1) if decl else body      # after the port list
    open(out, "w").write("`timescale 1ns/1ps" + chr(10) + body)
    rep = {"instances_delayed": n_inst, "outputs": len(assigns), "sdf_instances": len(dly),
           "delay_ns": {"mean": round(statistics.mean(used), 4), "median": round(statistics.median(used), 4),
                        "max": round(max(used), 4)} if used else None}
    print(json.dumps(rep))
    if report:
        json.dump(rep, open(report, "w"), indent=1)


if __name__ == "__main__":
    main(*sys.argv[1:6])
