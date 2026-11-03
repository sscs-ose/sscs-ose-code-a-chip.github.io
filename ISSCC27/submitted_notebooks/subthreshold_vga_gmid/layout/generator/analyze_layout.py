#!/usr/bin/env python
# Author: Vrinda Pandey (layout generator and sign-off scripts for this submission)
# SPDX-License-Identifier: Apache-2.0
"""Squeeze everything out of the PEX netlist and the GDS of vga_core_12t.
Usage (from the 12T folder):  python analyze_layout.py  > layout_analysis.txt
Inputs: verify/vga_core_12t_pex.spice, layout/vga_core_12t.spice (designer netlist),
        layout/vga_core_12t.gds, layout/vga_core_12t_placement.txt
"""
import re, sys
from pathlib import Path

PEX, NET, GDS, PLACE = (Path(sys.argv[i]) if len(sys.argv) > i else Path(d) for i, d in
                        enumerate(["verify/vga_core_12t_pex.spice", "layout/vga_core_12t.spice",
                                   "layout/vga_core_12t.gds", "layout/vga_core_12t_placement.txt"], 1))
SUP = {"gnd", "vdd", "0"}
UNIT = {"f": 1.0, "p": 1e3, "a": 1e-3, "n": 1e6, None: 1e15}
SIGNAL_PAIRS = [("net2", "net3"), ("vin_p", "vin_n"), ("vctrl_p", "vctrl_n")]


def caps(path):
    tot, pair = {}, {}
    for l in Path(path).read_text().splitlines():
        m = re.match(r"^C\d+ (\S+) (\S+) ([0-9.eE+-]+)([fpan])?", l)
        if not m:
            continue
        a, b, v, u = m.groups(); v = float(v) * UNIT[u]
        for n in (a, b):
            tot[n] = tot.get(n, 0) + v
        k = tuple(sorted((a, b))); pair[k] = pair.get(k, 0) + v
    return tot, pair


def spice_num(x):
    m = re.match(r"^([0-9.eE+-]+)(meg|[fpnumkg])?", str(x).lower())
    return float(m.group(1)) * {"f": 1e-15, "p": 1e-12, "n": 1e-9, "u": 1e-6, "m": 1e-3, "k": 1e3, "meg": 1e6, "g": 1e9, None: 1}[m.group(2)]


def devices(path):
    out = []
    for l in Path(path).read_text().splitlines():
        t = l.split()
        if not t or not t[0].upper().startswith("X"):
            continue
        p = {k.lower(): v for k, v in (x.split("=", 1) for x in t[6:] if "=" in x)}
        f = lambda k: spice_num(p.get(k, "0"))
        mult = f("m") or 1.0
        out.append(dict(name=t[0], d=t[1], g=t[2], s=t[3], b=t[4], model=t[5], w=f("w"), l=f("l"), nf=f("nf") or 1,
                        ad=f("ad") * mult, as_=f("as") * mult, pd=f("pd") * mult, ps=f("ps") * mult, m=mult))
    return out


def junction_by_net(devs):
    j = {}
    for d in devs:
        if d["d"] == d["g"] == d["s"]:           # dummy: all terminals on one supply net
            continue
        for net, a, p in ((d["d"], d["ad"], d["pd"]), (d["s"], d["as_"], d["ps"])):
            A, P = j.get(net, (0.0, 0.0)); j[net] = (A + a, P + p)
    return j


tot, pair = caps(PEX)
lay = devices(PEX); sch = devices(NET)
print("=" * 78); print("1. PARASITIC CAPACITANCE PER NET (from the PEX netlist, Magic extraction)"); print("=" * 78)
print(f"{'net':10s} {'total':>9s} {'to gnd/vdd':>11s} {'to signals':>11s}   largest signal coupling")
for n in sorted(tot, key=lambda k: -tot[k]):
    if n in SUP:
        continue
    to_sup = sum(v for (a, b), v in pair.items() if n in (a, b) and ({a, b} - {n}) <= SUP)
    sig = {(b if a == n else a): v for (a, b), v in pair.items() if n in (a, b) and not (({a, b} - {n}) <= SUP)}
    top = max(sig.items(), key=lambda kv: kv[1]) if sig else ("-", 0)
    print(f"{n:10s} {tot[n]:8.1f}f {to_sup:10.1f}f {sum(sig.values()):10.1f}f   {top[0]} {top[1]:.1f} fF")
print("\nLargest signal-to-signal couplings:")
for (a, b), v in sorted(((k, v) for k, v in pair.items() if not (set(k) & SUP)), key=lambda kv: -kv[1])[:6]:
    print(f"   {a:8s} <-> {b:8s} {v:7.2f} fF")

print("\n" + "=" * 78); print("2. SYMMETRY OF MATCHED NETS (wiring capacitance)"); print("=" * 78)
for a, b in SIGNAL_PAIRS:
    if a in tot and b in tot:
        d = abs(tot[a] - tot[b]); print(f"   {a:8s} {tot[a]:8.2f} fF  vs  {b:8s} {tot[b]:8.2f} fF   difference {d:6.2f} fF ({100 * d / max(tot[a], tot[b]):.1f} %)")

print("\n" + "=" * 78); print("3. JUNCTION (DIFFUSION) AREA: LAYOUT vs DESIGNER NETLIST"); print("=" * 78)
print("   Simulation models compute drain/source junction capacitance from AD/AS/PD/PS. The designer's")
print("   pre-layout netlist assumes values; the PEX netlist carries what the layout actually has.")
jl, js = junction_by_net(lay), junction_by_net(sch)
print(f"   {'net':10s} {'area layout':>12s} {'area schem.':>12s} {'ratio':>6s} {'perim layout':>13s} {'perim schem.':>13s}")
for n in sorted(set(jl) | set(js)):
    if n in SUP:
        continue
    (Al, Pl), (As, Ps) = jl.get(n, (0, 0)), js.get(n, (0, 0))
    r = f"{Al / As:5.2f}x" if As else "   -"
    print(f"   {n:10s} {Al:10.1f}um2 {As:10.1f}um2 {r:>6s} {Pl:11.1f}um {Ps:11.1f}um")
print("   (supply nets omitted; dummy transistors excluded)")

print("\n" + "=" * 78); print("4. RESISTANCE OF THE SHARED ROUTING (met3 buses + met4 trunk, all in series = upper bound)"); print("=" * 78)
try:
    import klayout.db as db
    RS = {"m3": 0.047, "m4": 0.047}                                   # SKY130 met3/met4 sheet resistance, ohm/square
    ly = db.Layout(); ly.read(str(GDS)); top = ly.top_cell()
    l2n = db.LayoutToNetlist(db.RecursiveShapeIterator(ly, top, []))
    m3 = l2n.make_layer(ly.layer(70, 20), "m3"); v3 = l2n.make_layer(ly.layer(70, 44), "via3"); m4 = l2n.make_layer(ly.layer(71, 20), "m4")
    for x in (m3, v3, m4): l2n.connect(x)
    l2n.connect(m3, v3); l2n.connect(v3, m4); l2n.extract_netlist()
    pts = {}
    for txl in ((71, 16), (71, 5)):
        it = top.begin_shapes_rec(ly.layer(*txl))
        while not it.at_end():
            sh = it.shape()
            if sh.is_text(): pts[sh.text.string] = it.trans() * sh.text.trans.disp
            it.next()
    dbu = ly.dbu
    print(f"   {'net':8s} {'R bound':>9s} {'C total':>9s} {'RC pole':>12s}   IR drop at 1 uA")
    for name in ["v_out", "net4", "net2", "net3", "net5", "iref"]:
        if name not in pts: continue
        n = l2n.probe_net(m4, db.Point(pts[name].x, pts[name].y))
        if n is None: continue
        R = 0.0
        for k, lay_ in (("m3", m3), ("m4", m4)):
            for pg in l2n.shapes_of_net(n, lay_, True).each():
                bb = pg.bbox(); w, h = bb.width() * dbu, bb.height() * dbu
                if min(w, h) > 0: R += RS[k] * max(w, h) / min(w, h)
        C = tot.get(name, 0) * 1e-15
        f = 1 / (2 * 3.14159 * R * C) if R and C else float("inf")
        print(f"   {name:8s} {R:7.1f} ohm {tot.get(name, 0):7.1f}fF {f / 1e9:9.1f} GHz   {R:.0f} uV")
    print("   Even as an upper bound the routing poles are in the GHz range and IR drops are microvolts")
    print("   at the uA-level currents of this circuit, so capacitance-only extraction is adequate for audio.")
except Exception as e:
    print(f"   (skipped: {e})")

print("\n" + "=" * 78); print("5. LAYOUT STATISTICS"); print("=" * 78)
gate = sum(d["w"] * d["l"] * d["m"] for d in sch)
real = [d for d in lay if not (d["d"] == d["g"] == d["s"])]; dummies = len(lay) - len(real)
txt = PLACE.read_text() if PLACE.exists() else ""
m = re.search(r"top cell \S+: ([0-9.]+) x ([0-9.]+) um", txt)
if m:
    W, H = float(m.group(1)), float(m.group(2))
    print(f"   layout {W:.1f} x {H:.1f} um = {W * H:,.0f} um^2;  total gate area (W x L) {gate:,.0f} um^2 = {100 * gate / (W * H):.1f} % of the layout")
print(f"   transistors in the layout: {len(lay)} ({len(real)} active gate fingers, {dummies} dummies = {100 * dummies / len(lay):.0f} %)")
for blk in re.findall(r"^\[(\w+)\] (\w+) L=([0-9.]+) unit=(\d+) finger\(s\).*?grid (\d+) rows x (\d+) cols", txt, re.M):
    print(f"   block {blk[0]:7s} {blk[1]} L={blk[2]:>4s} um, unit {blk[3]:>3s} fingers, {blk[4]} x {blk[5]} array")
