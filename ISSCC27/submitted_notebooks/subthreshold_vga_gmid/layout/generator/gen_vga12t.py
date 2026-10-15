#!/usr/bin/env python
# Author: Vrinda Pandey (layout generator and sign-off scripts for this submission)
# SPDX-License-Identifier: Apache-2.0
"""Parametric layout generator for the 12T VGA core (SKY130, gLayout).

Inputs : layout/vga_core_12t_sizes.json  (sizes: type, nf, L_um, m per device; 5 um fingers)
         layout/vga_core_12t.spice       (connectivity: D G S B of every device, pin order)
Outputs: layout/vga_core_12t.gds         (top cell vga_core_12t)
         layout/vga_core_12t_ref.spice   (LVS reference = connectivity + JSON sizes)
         layout/vga_core_12t_placement.txt (unit placement + centroid errors per block)

Layout rules implemented
  * every device is built from identical unit transistors of nf_u fingers (5 um each)
  * M2/M3 : one 2-D array, common-centroid, dummies at the row ends
  * M1/M4 : one array, interdigitated (and common-centroid), n-well + n-tap ring tied to vdd
  * M6-M9 : one matched array of four devices with a common centroid
  * M5/M10/M11/M12 : one array of unit devices, centroids as close as the counts allow,
                     M10 and M11 forced to the same centroid (their mismatch sets the output DC level)
  * text labels net2..net5 (and every pin) on the routing
Routing
  * inside an array: each terminal of each unit drops a met1->met2 via on its own finger strip
    (or on the gate bar) and runs vertically on met2 to a met3 bus above (top half of the rows)
    or below (bottom half). Rows that share a column use different strips, so tracks never touch.
  * between arrays: every net has one vertical met4 trunk; each array's bus for that net runs
    on met3 to the trunk.
"""
import argparse, json, math, random, re
from functools import lru_cache
from pathlib import Path

from gdsfactory import Component
from glayout import sky130, nmos, pmos, via_stack
from glayout.primitives.guardring import tapring

GL = {"li": "met1", "m1": "met2", "m2": "met3", "m3": "met4", "m4": "met5"}   # gLayout names of real layers
LAY = {k: tuple(sky130.get_glayer(v)) for k, v in GL.items()}
PIN = {"m3": ((70, 16), (70, 5)), "m4": ((71, 16), (71, 5))}                  # (pin, label) datatypes
VIA2 = (69, 44)
GAPX, GAPY, RING_MARGIN = 1.0, 2.0, 1.0
TRACK_SEP = 0.4            # min centre spacing: 0.14 um track vs 0.32 um via1 pad + 0.14 um space
BUS_W, BUS_PITCH = 0.40, 1.0
TRUNK_W, TRUNK_PITCH = 0.40, 1.6
BLOCK_GAP = 4.0
SENSITIVE = "v_out"        # designer: v_out wiring <= ~300 fF, keep it short and away from net4
AVOID = "net4"
SUPPLIES = ("gnd", "vdd")
QUIET_GAP = 1.0            # extra space on both sides of the sensitive bus / trunk


def net_order(nets):
    """Sensitive net first (nearest the array / blocks), supplies next as shields, the net to avoid last."""
    rank = lambda n: (0 if n == SENSITIVE else 1 if n in SUPPLIES else 3 if n == AVOID else 2, n)
    return sorted(nets, key=rank)


def offsets(nets, pitch):
    """Positions along a stack of parallel wires, with extra space around the sensitive net."""
    pos, x = {}, 0.0
    for i, n in enumerate(nets):
        if i and (n == SENSITIVE or nets[i - 1] == SENSITIVE):
            x += QUIET_GAP
        pos[n] = x; x += pitch
    return pos

BLOCKS = [  # name, devices, centroid-matching groups
    ("mirror", ["M1", "M4"], [["M1", "M4"]]),
    ("gain", ["M6", "M7", "M8", "M9"], [["M6", "M7", "M8", "M9"]]),
    ("bias", ["M5", "M10", "M11", "M12"], [["M10", "M11"]]),
    ("diff", ["M2", "M3"], [["M2", "M3"]]),
]

# ---------------------------------------------------------------- input files
def load_design(json_path, spice_path):
    spec = json.loads(Path(json_path).read_text())
    fw = float(spec["finger_width_um"])
    subckt, pins, devs = None, None, {}
    for raw in Path(spice_path).read_text().splitlines():
        t = raw.split()
        if not t or t[0].startswith("*"):
            continue
        if t[0].lower() == ".subckt":
            subckt, pins = t[1], t[2:]
        elif t[0].upper().startswith("XM"):
            devs[t[0][1:]] = dict(D=t[1], G=t[2], S=t[3], B=t[4], model=t[5])
    if set(devs) != set(spec["devices"]):
        raise SystemExit(f"device mismatch: spice {sorted(devs)} vs json {sorted(spec['devices'])}")
    if [p for p in pins] != spec["pins"]:
        print(f"note: pin order taken from the spice file: {pins}")
    for n, d in devs.items():
        js = spec["devices"][n]
        typ = "pfet" if "pfet" in js["type"] else "nfet"
        if typ not in d["model"]:
            raise SystemExit(f"{n}: json type {js['type']} but spice model {d['model']}")
        d.update(type=typ, nf=int(js["nf"]), L=float(js["L_um"]), m=int(js["m"]))
        if d["nf"] < 1 or d["m"] < 1:
            raise SystemExit(f"{n}: nf and m must be >= 1")
    return spec, fw, subckt, pins, devs


def write_reference(path, subckt, pins, devs, fw):
    lines = [f"* LVS reference: connectivity from the spice file, sizes from the json (finger width {fw} um)",
             f".subckt {subckt} {' '.join(pins)}"]
    for n, d in devs.items():
        m = f" m={d['m']}" if d["m"] != 1 else ""
        lines.append(f"X{n} {d['D']} {d['G']} {d['S']} {d['B']} {d['model']} "
                     f"L={d['L']:g} W={d['nf'] * fw:g} nf={d['nf']}{m}")
    lines.append(".ends")
    Path(path).write_text("\n".join(lines) + "\n")

# ---------------------------------------------------------------- unit cells
@lru_cache(maxsize=None)
def unit(typ, nf, L, fw):
    f = nmos if typ == "nfet" else pmos
    kw = dict(width=fw, length=L, fingers=nf, with_dummy=(False, False), with_tie=False, with_substrate_tap=False)
    if typ == "nfet":
        kw["with_dnwell"] = False
    c = f(sky130, **kw)
    strips, gates = {}, []
    for p in c.get_polygons(by_spec=True).get(LAY["m1"], []):
        x0, x1, y0, y1 = p[:, 0].min(), p[:, 0].max(), p[:, 1].min(), p[:, 1].max()
        if x1 - x0 > 0.5:
            continue
        xc = round(float((x0 + x1) / 2), 3)
        if y1 < -2.9:                                  # small squares on the gate bar
            gates.append((xc, float((y0 + y1) / 2)))
        else:
            lo, hi = strips.get(xc, (1e9, -1e9)); strips[xc] = (min(lo, y0), max(hi, y1))
    tops = sorted({round(hi, 2) for _, (lo, hi) in strips.items()})
    if len(tops) != 2:
        raise SystemExit(f"unexpected strip geometry for {typ} nf={nf} L={L}: {strips}")
    d_strips = sorted(x for x, (lo, hi) in strips.items() if round(hi, 2) == tops[1])
    s_strips = sorted(x for x, (lo, hi) in strips.items() if round(hi, 2) == tops[0])
    gate_y = sum(g[1] for g in gates) / len(gates)
    gate_x = sorted({g[0] for g in gates})
    return dict(comp=c, xmin=c.xmin, xmax=c.xmax, ymin=c.ymin, ymax=c.ymax, w=c.xmax - c.xmin, h=c.ymax - c.ymin,
                D=d_strips, S=s_strips, G=gate_x, gate_y=gate_y, sd_y=0.0)

# ---------------------------------------------------------------- placement
def divisors(n):
    return [d for d in range(1, n + 1) if n % d == 0]


def plan_block(names, devs, fw):
    typs = {devs[n]["type"] for n in names}; Ls = {devs[n]["L"] for n in names}
    if len(typs) != 1 or len(Ls) != 1:
        raise SystemExit(f"devices {names} must share type and L to be matched ({typs}, {Ls})")
    typ, L = typs.pop(), Ls.pop()
    g = math.gcd(*[devs[n]["nf"] for n in names])
    est_w = lambda nf: nf * (L + 0.33) + 1.07          # measured gLayout unit width (5 um fingers), exact for nf 1..8
    est_h = 7.37
    best = None
    for nfu in [d for d in divisors(g) if d <= 32]:
        kmax = (nfu + 1) // 2                          # drain strips = ceil(nf/2) <= source strips
        counts = {n: devs[n]["m"] * devs[n]["nf"] // nfu for n in names}
        U = sum(counts.values())
        for R in range(2, 2 * kmax + 1, 2):
            C = math.ceil(U / R); fill = R * C - U
            if C < 2:                                  # must be a 2-D array
                continue
            W = C * (est_w(nfu) + GAPX) + 2 * (est_w(1) + GAPX); H = R * (est_h + GAPY)
            odd = sum(1 for v in counts.values() if v % 2) if len(counts) > 1 else 0
            single = sum(1 for v in counts.values() if v == 1) if len(counts) > 1 else 0
            score = max(W, H) / min(W, H) + 10.0 * fill / U + 6.0 * odd + 20.0 * single
            if best is None or score < best[0]:
                best = (score, nfu, R, C, fill, counts)
    _, nfu, R, C, fill, counts = best
    return dict(typ=typ, L=L, nfu=nfu, R=R, C=C, fill=fill, counts=counts)


def assign(plan, groups, seed=1):
    """Assign units to grid cells: every device's centroid at the array centre where the counts allow,
    devices of a matching group at the same centroid, neighbours preferably different (interdigitation)."""
    R, C, counts = plan["R"], plan["C"], dict(plan["counts"])
    if plan["fill"]:
        counts["FILL"] = plan["fill"]
    cells = [(r, c) for r in range(R) for c in range(C)]
    rot = lambda rc: (R - 1 - rc[0], C - 1 - rc[1])
    pairs, seen = [], set()
    for rc in sorted(cells, key=lambda rc: (abs(rc[0] - (R - 1) / 2) + abs(rc[1] - (C - 1) / 2))):
        if rc not in seen:
            seen |= {rc, rot(rc)}; pairs.append((rc, rot(rc)))
    grid, left = {}, dict(counts)
    order = sorted(left, key=lambda n: -left[n])
    i = 0
    for a, b in pairs:                                   # symmetric start: give whole pairs round-robin
        for _ in range(len(order)):
            n = order[i % len(order)]; i += 1
            if left[n] >= 2:
                grid[a] = grid[b] = n; left[n] -= 2; break
    for rc in cells:                                     # odd leftovers
        if rc not in grid:
            n = next(k for k in order if left[k] > 0); grid[rc] = n; left[n] -= 1
    cx, cy = (C - 1) / 2, (R - 1) / 2
    names = list(counts)                 # fillers included: they must sit symmetrically too

    def cost(gd):
        pos = {n: [] for n in counts}
        for (r, c), n in gd.items():
            pos[n].append((c, r))
        cen = {n: (sum(p[0] for p in v) / len(v), sum(p[1] for p in v) / len(v)) for n, v in pos.items()}
        J = sum((cen[n][0] - cx) ** 2 + (cen[n][1] - cy) ** 2 for n in names)
        for grp in groups:
            for a in grp:
                for b in grp:
                    if a < b:
                        J += 50 * ((cen[a][0] - cen[b][0]) ** 2 + (cen[a][1] - cen[b][1]) ** 2)
        J += 0.05 * sum(1 for (r, c), n in gd.items() if n != "FILL" and ((c + 1 < C and gd[(r, c + 1)] == n) or (r + 1 < R and gd[(r + 1, c)] == n)))
        return J

    real = [n for n in counts if n != "FILL"]
    if len(real) == 2 and "FILL" not in counts and counts[real[0]] == counts[real[1]] and (R + C) % 2 == 0:
        # two equal devices: an exact checkerboard is both fully interdigitated and exactly common-centroid
        return {(r, c): real[(r + c) % 2] for r in range(R) for c in range(C)}
    rnd = random.Random(seed)
    cur = cost(grid); best = (cur, dict(grid))
    T = 1.0
    for it in range(30000):
        a, b = rnd.sample(cells, 2)
        if grid[a] == grid[b]:
            continue
        grid[a], grid[b] = grid[b], grid[a]
        new = cost(grid)
        if new <= cur or rnd.random() < math.exp((cur - new) / max(T, 1e-6)):
            cur = new
            if cur < best[0]:
                best = (cur, dict(grid))
        else:
            grid[a], grid[b] = grid[b], grid[a]
        T *= 0.9997
    return best[1]

# ---------------------------------------------------------------- geometry helpers
def rect(c, x0, y0, x1, y1, layer):
    c.add_polygon([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], layer=layer)


def via(c, x, y, a, b):
    order = ["li", "m1", "m2", "m3", "m4"]
    lo, hi = sorted([a, b], key=order.index)
    v = c << via_stack(sky130, GL[lo], GL[hi], centered=True); v.move((x, y))


def via1_small(c, x, y):
    """met1 -> met2 via with 0.32 um pads (0.085 um enclosure on all sides), fits L = 0.5 um finger pitch."""
    rect(c, x - 0.075, y - 0.075, x + 0.075, y + 0.075, (68, 44))
    rect(c, x - 0.16, y - 0.16, x + 0.16, y + 0.16, LAY["m1"])
    rect(c, x - 0.16, y - 0.16, x + 0.16, y + 0.16, LAY["m2"])


def via2_small(c, x, y):
    """met2 -> met3 via with tight pads (the gLayout stack puts a 1.5 um pad on met3)."""
    rect(c, x - 0.1, y - 0.1, x + 0.1, y + 0.1, VIA2)
    rect(c, x - 0.185, y - 0.185, x + 0.185, y + 0.185, LAY["m2"])
    rect(c, x - 0.2, y - 0.2, x + 0.2, y + 0.2, LAY["m3"])

# ---------------------------------------------------------------- one matched array
def build_block(bname, names, groups, devs, fw, log):
    plan = plan_block(names, devs, fw)
    grid = assign(plan, groups)
    typ, L, nfu, R, C = plan["typ"], plan["L"], plan["nfu"], plan["R"], plan["C"]
    ug, dg = unit(typ, nfu, L, fw), unit(typ, 1, L, fw)
    body = devs[names[0]]["B"]
    term_net = {n: {"D": devs[n]["D"], "G": devs[n]["G"], "S": devs[n]["S"]} for n in names}
    term_net["FILL"] = {"D": body, "G": body, "S": body}
    c = Component(bname)
    pitch_x, pitch_y = ug["w"] + GAPX, ug["h"] + GAPY
    x0 = dg["w"] + GAPX                                  # first unit column starts after the left dummy
    col_x = [x0 + i * pitch_x - ug["xmin"] for i in range(C)]
    row_y = [-(r * pitch_y) - ug["ymax"] for r in range(R)]   # row 0 on top
    for (r, k), n in grid.items():
        ref = c << ug["comp"]; ref.move((col_x[k], row_y[r]))
    # end-of-row dummies: one finger each, all terminals shorted with met1, tied to the ring below
    dummy_x = [-dg["xmin"], x0 + C * pitch_x - GAPX + GAPX - dg["xmin"]]
    for r in range(R):
        for dx in dummy_x:
            ref = c << dg["comp"]; ref.move((dx, row_y[r]))
    ux0, ux1 = min(c.xmin, 0), c.xmax
    uy0, uy1 = c.ymin, c.ymax
    # tap ring around everything
    ew, eh = ux1 - ux0 + 2 * RING_MARGIN, uy1 - uy0 + 2 * RING_MARGIN
    ring = tapring(sky130, enclosed_rectangle=(ew, eh), sdlayer="p+s/d" if typ == "nfet" else "n+s/d",
                   horizontal_glayer="met2", vertical_glayer="met1")
    rr = c << ring; rr.move(((ux0 + ux1) / 2, (uy0 + uy1) / 2))
    ring_m1 = [p for p in rr.get_polygons(by_spec=True).get(LAY["m1"], [])]
    ring_top = max(ring_m1, key=lambda p: p[:, 1].max())
    ring_bot = min(ring_m1, key=lambda p: p[:, 1].min())
    ring_li = [p for p in rr.get_polygons(by_spec=True).get(LAY["li"], []) if (p[:, 1].max() - p[:, 1].min()) > 3]
    li_left = min(ring_li, key=lambda p: p[:, 0].min()); li_right = max(ring_li, key=lambda p: p[:, 0].max())
    xl = float((li_left[:, 0].min() + li_left[:, 0].max()) / 2); xr = float((li_right[:, 0].min() + li_right[:, 0].max()) / 2)
    for r in range(R):              # dummies: narrow met1 straps (no >3 um plate) short S, D, G and tie them to the ring
        yc = row_y[r] + dg["sd_y"]
        sd = dg["S"] + dg["D"]
        for dx, xe in ((dummy_x[0], xl), (dummy_x[1], xr)):
            xa, xb = sorted([dx + min(sd) - 0.2, xe]) if xe < dx else sorted([dx + max(sd) + 0.2, xe])
            xa, xb = min(xa, dx + min(sd) - 0.2), max(xb, dx + max(sd) + 0.2)
            rect(c, xa, yc - 0.3, xb, yc + 0.3, LAY["m1"])                                # across both strips to the ring
            rect(c, dx - 0.07, row_y[r] + dg["gate_y"] - 0.07, dx + 0.07, yc, LAY["m1"])  # 0.14 um drop to the gate bar (fits L=0.5)
            via(c, xe, yc, "li", "m1")
    imp = (94, 20) if typ == "nfet" else (93, 44)        # p+ taps in NMOS arrays, n+ taps in the PMOS array
    for r in range(R - 1):                               # latch-up: a tap strip between every pair of rows
        yg = row_y[r] + ug["ymin"] - GAPY / 2
        xa, xb = xl, xr
        rect(c, xa, yg - 0.205, xb, yg + 0.205, (65, 44))                      # tap diffusion
        rect(c, xa, yg - 0.33, xb, yg + 0.33, imp)                             # implant (0.125 enclosure)
        rect(c, xa, yg - 0.165, xb, yg + 0.165, LAY["li"])                     # li (merges with the ring li)
        n_ct = int((xb - xa - 0.6) // 0.34)
        x_c0 = (xa + xb) / 2 - (n_ct - 1) * 0.34 / 2
        for i in range(n_ct):
            xc = x_c0 + i * 0.34
            rect(c, xc - 0.085, yg - 0.085, xc + 0.085, yg + 0.085, (66, 44))  # licon
    if typ == "pfet":                                    # one n-well over the whole array and its n-tap ring
        rect(c, rr.xmin - 0.4, rr.ymin - 0.4, rr.xmax + 0.4, rr.ymax + 0.4, (64, 20))
    # ---- per-unit terminal tracks
    half = R // 2
    tracks = {"top": {}, "bot": {}}                     # net -> list of x
    for k in range(C):
        for side, rows in (("top", list(range(half))), ("bot", list(range(R - 1, half - 1, -1)))):
            K = len(rows)
            choices = [{"D": ug["D"][kk], "S": ug["S"][kk]} for kk in range(K)]   # all strips first
            used = [ch[t] for ch in choices for t in ("D", "S")]
            for ch in choices:                                                  # then gates around them
                gx = max(ug["G"], key=lambda x: min(abs(x - u) for u in used))
                if min(abs(gx - u) for u in used) < TRACK_SEP:
                    raise SystemExit(f"{bname}: no free gate track (nf_u={nfu}, L={L}, used={sorted(used)})")
                used.append(gx); ch["G"] = gx
            srt = sorted(used)
            if any(b2 - a2 < TRACK_SEP for a2, b2 in zip(srt, srt[1:])):
                raise SystemExit(f"{bname}: tracks too close in column {k}: {srt}")
            for kk, r in enumerate(rows):                # kk = 0 is the row next to the bus
                n = grid[(r, k)]
                for t in ("D", "S", "G"):
                    xs = col_x[k] + choices[kk][t]
                    ys = row_y[r] + (ug["gate_y"] if t == "G" else ug["sd_y"])
                    via1_small(c, xs, ys)
                    tracks[side].setdefault(term_net[n][t], []).append((xs, ys))
    # ---- buses (met3) above and below; ring tie to the body net on the top side
    tracks["top"].setdefault(body, [])
    ring_tie_x = float(ring_top[:, 0].min()) + 0.6
    ring_tie_y = float((ring_top[:, 1].min() + ring_top[:, 1].max()) / 2)
    via(c, ring_tie_x, ring_tie_y, "m1", "m2")
    tracks["top"][body].append((ring_tie_x, ring_tie_y))
    x_right = rr.xmax + 1.0
    bus_y = {}
    for side, sign, yref in (("top", 1, rr.ymax), ("bot", -1, rr.ymin)):
        order = net_order(tracks[side]); off = offsets(order, BUS_PITCH)
        for net in order:
            yb = yref + sign * (1.2 + off[net])
            bus_y[(side, net)] = yb
            for xs, ys in tracks[side][net]:
                rect(c, xs - 0.07, min(ys, yb), xs + 0.07, max(ys, yb), LAY["m2"]); via2_small(c, xs, yb)
    nets = sorted({n for s in tracks for n in tracks[s]})
    joins = net_order([n for n in nets if ("top", n) in bus_y and ("bot", n) in bus_y])
    joff = offsets(joins, 0.8)
    x_end = x_right + (max(joff.values()) + 0.8 if joins else 0) + 0.6
    xmin_bus = rr.xmin
    for (side, net), yb in bus_y.items():
        xs = [x for x, _ in tracks[side][net]]
        rect(c, min(xs) - 0.2, yb - BUS_W / 2, x_end, yb + BUS_W / 2, LAY["m3"])     # only from the first tap
    for net in joins:                                    # tie the top and bottom bus of a net together
        xj = x_right + joff[net]
        yt, yb = bus_y[("top", net)], bus_y[("bot", net)]
        rect(c, xj - 0.07, yb, xj + 0.07, yt, LAY["m2"]); via2_small(c, xj, yt); via2_small(c, xj, yb)
    exports = {net: (x_end, bus_y[("top", net)] if ("top", net) in bus_y else bus_y[("bot", net)]) for net in nets}
    # ---- report
    pos = {}
    for (r, k), n in grid.items():
        pos.setdefault(n, []).append((col_x[k] + (ug["xmin"] + ug["xmax"]) / 2, row_y[r] + (ug["ymin"] + ug["ymax"]) / 2))
    allp = [p for v in pos.values() for p in v]
    ctr = (sum(p[0] for p in allp) / len(allp), sum(p[1] for p in allp) / len(allp))
    log.append(f"[{bname}] {typ} L={L} unit={nfu} finger(s) x {fw} um, grid {R} rows x {C} cols (+2 dummy cols), fill dummies {plan['fill']}")
    for r in range(R):
        log.append("    " + " ".join(f"{grid[(r, k)]:>4s}" for k in range(C)))
    for n in names:
        cx = sum(p[0] for p in pos[n]) / len(pos[n]); cy = sum(p[1] for p in pos[n]) / len(pos[n])
        log.append(f"    {n:4s} units {len(pos[n]):3d}  centroid offset from array centre: dx={cx - ctr[0]:+.3f} um dy={cy - ctr[1]:+.3f} um")
    for grp in groups:
        cs = {n: (sum(p[0] for p in pos[n]) / len(pos[n]), sum(p[1] for p in pos[n]) / len(pos[n])) for n in grp}
        spread = max(math.dist(cs[a], cs[b]) for a in grp for b in grp)
        log.append(f"    matched group {'/'.join(grp)}: max centroid distance {spread:.3f} um")
    return c, exports

# ---------------------------------------------------------------- top level
def build(json_path, spice_path, out_gds, out_ref, out_log):
    spec, fw, subckt, pins, devs = load_design(json_path, spice_path)
    write_reference(out_ref, subckt, pins, devs, fw)
    top = Component(subckt)
    log, refs, y = [], [], 0.0
    for bname, names, groups in BLOCKS:
        blk, exports = build_block(bname, names, groups, devs, fw, log)
        dx, dy = -blk.xmax, y - blk.ymax                # right-aligned: every export lands next to the trunks
        ref = top << blk
        ref.move((dx, dy))
        y = ref.ymin - BLOCK_GAP
        refs.append((ref, {n: (x + dx, yy + dy) for n, (x, yy) in exports.items()}))
    # one vertical met4 trunk per net, to the right of all blocks
    xr = max(r.xmax for r, _ in refs) + 2.0
    all_nets = net_order({n for _, ex in refs for n in ex})
    toff = offsets(all_nets, TRUNK_PITCH)
    trunk_x = {n: xr + toff[n] for n in all_nets}
    span = {}
    for ref, ex in refs:
        for net, (x, yb) in ex.items():
            x_abs = x
            rect(top, x_abs - 0.2, yb - BUS_W / 2, trunk_x[net] + 0.2, yb + BUS_W / 2, LAY["m3"])
            via(top, trunk_x[net], yb, "m3", "m4")
            lo, hi = span.get(net, (yb, yb)); span[net] = (min(lo, yb), max(hi, yb))
    for net, (lo, hi) in span.items():
        xt = trunk_x[net]
        hi2 = hi + 2.0
        rect(top, xt - TRUNK_W / 2, lo - 0.3, xt + TRUNK_W / 2, hi2, LAY["m4"])
        pin_lay, lab_lay = PIN["m4"]
        if net in pins:
            rect(top, xt - 0.1, hi2 - 0.6, xt + 0.1, hi2 - 0.4, pin_lay)
            top.add_label(text=net, position=(xt, hi2 - 0.5), layer=pin_lay)
        elif net in spec.get("internal_net_labels", []):
            top.add_label(text=net, position=(xt, hi2 - 0.5), layer=lab_lay)
    missing = [p for p in pins if p not in span]
    if missing:
        raise SystemExit(f"pins with no connection in the layout: {missing}")
    top.write_gds(str(out_gds))
    bb = top.bbox
    log.append(f"top cell {subckt}: {bb[1][0] - bb[0][0]:.1f} x {bb[1][1] - bb[0][1]:.1f} um = "
               f"{(bb[1][0] - bb[0][0]) * (bb[1][1] - bb[0][1]):.0f} um^2")
    Path(out_log).write_text("\n".join(log) + "\n")
    print("\n".join(log))
    print(f"GDS written: {Path(out_gds).resolve()}\nLVS reference: {Path(out_ref).resolve()}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="layout/vga_core_12t_sizes.json")
    ap.add_argument("--spice", default="layout/vga_core_12t.spice")
    ap.add_argument("--out", default="layout/vga_core_12t.gds")
    a = ap.parse_args()
    out = Path(a.out)
    build(a.json, a.spice, out, out.with_name(out.stem + "_ref.spice"), out.with_name(out.stem + "_placement.txt"))
