"""Compact CDAC with per-unit switches: identical square-ish tiles in a common-centroid array (SKY130).

Every tile = one MIM unit capacitor + its own bottom-plate switch (LVT input transmission gate, PMOS
driver to Vref, NMOS driver to ground).  Bit i is 2^i identical tiles, so each bit's R*C equals the unit
R*C and switches match as well as capacitors.  Tile cross-section (bottom to top):

    p-tap (vss) | n-tap (vdd)               body taps shared by the row
    supply rails  met2: vss vdd vin vref    run through the whole row
    [Mdn][Msn] | [Msp][Mdp]                 4 gLayout fets, rotated: gates up, inner bar = plate
    control rails met2: en enb pg ng ...    only the signals used in this row
    MIM unit cap (met3/met4)                stacked ON TOP of the control rails (different layers)

Wiring inside a tile is fixed: gate -> control rail (met1 stub + via1), outer bar -> supply rail
(met1 stub + via1), the four inner bars -> via1/via2 -> met3 bus -> met3 riser -> cap bottom plate.
Rails end on met3 trunks at the array edges.  Layer numbers are SKY130 GDS numbers.
"""

from .cdac import M2_PAD, M3_PAD, LBL, PIN, MET2, MET3, MET4, VIA, VIA2, centroid_grid, snap
from .cell import DIFF, LVTN, MET1, NWELL, VIA1, V1, Dev, _make_device

NSDM, PSDM = (93, 44), (94, 20)
RAIL_W = 0.23            # met2 rail width
RAIL_PITCH = 0.48
M1_STUB = 0.23           # met1 stub width
V1_PAD_M1 = (0.27, 0.32) # met1 around via1 (x, y): 0.06 / 0.085 enclosure
V1_PAD_M2 = (0.32, 0.27) # met2 around via1, long along the rail
DEV_GAP = 0.40           # between devices of the same type
NP_GAP = 1.00            # between the NMOS pair and the PMOS pair (nwell edge)
TILE_GAP = 1.00          # between tiles in a row
STRAP_W = 0.80


def tile_signals(g, bits):
    """Gate nets (en, enb, pg, ng) of the tile that belongs to group g."""
    if g == "d":                                   # termination unit: no Vref driver (gate tied off)
        return dict(en="phig", enb="phigb", pg="vdd", ng="phigb")
    en, enb = ("phis", "phisb") if g == bits - 1 else ("phig", "phigb")
    return dict(en=en, enb=enb, pg=f"pg_{g}", ng=f"ng_{g}")


def tile_devices(design, g, bits, tag):
    sw, drv = design["sw"], design["drv"]
    fl = sw.get("flavor", "lvt")
    from ..pdk import TG_FLAVORS
    ln, lp = TG_FLAVORS[fl][1], TG_FLAVORS[fl][3]
    s = tile_signals(g, bits)
    bot = f"p_{tag}"
    # inner bar (gLayout "source") = plate, outer bar ("drain") = supply
    return [Dev(f"Mdn_{tag}", "n", drv["wn"], 0.15, "vss", s["ng"], bot, fingers=1, tie=False),
            Dev(f"Msn_{tag}", "n", sw["in_wn"], ln, "vin", s["en"], bot, fingers=1, flavor=fl, tie=False),
            Dev(f"Msp_{tag}", "p", sw["in_wp"], lp, "vin", s["enb"], bot, fingers=1, flavor=fl, tie=False),
            Dev(f"Mdp_{tag}", "p", drv["wp"], 0.15, "vref", s["pg"], bot, fingers=1, tie=False)]


SUPPLY = ["vss", "vdd", "vin", "vref"]
CTRL_ORDER = ["phis", "phisb", "phig", "phigb", "vdd"]


def build_array(design, bits, name=None):
    """Common-centroid tile array; returns (Component, info, reference netlist)."""
    from gdsfactory import Component
    from gdsfactory.components import rectangle
    from glayout import mimcap, sky130, via_stack

    from ..pdk import mos
    from .cell import model_name

    grid = centroid_grid(bits)
    R, C = len(grid), len(grid[0])
    name = name or f"cdacsw{bits}b"
    top = Component(name + "_hier")

    def rect(x0, y0, x1, y1, layer):
        x0, y0, x1, y1 = (snap(v) for v in (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)))
        if x1 - x0 <= 0 or y1 - y0 <= 0:
            return
        r = top << rectangle(size=(snap(x1 - x0), snap(y1 - y0)), layer=layer)
        r.move((x0, y0))

    def v1(x, y, along_x=False):   # met1 <-> met2; along_x: pad elongated in x (on horizontal met1 bars)
        mx, my = (V1_PAD_M1[1], V1_PAD_M1[0]) if along_x else V1_PAD_M1
        rect(x - mx / 2, y - my / 2, x + mx / 2, y + my / 2, MET1)
        rect(x - V1 / 2, y - V1 / 2, x + V1 / 2, y + V1 / 2, VIA1)
        rect(x - V1_PAD_M2[0] / 2, y - V1_PAD_M2[1] / 2, x + V1_PAD_M2[0] / 2, y + V1_PAD_M2[1] / 2, MET2)

    def v2(x, y):            # met2 <-> met3
        rect(x - M2_PAD / 2, y - M2_PAD / 2, x + M2_PAD / 2, y + M2_PAD / 2, MET2)
        rect(x - VIA / 2, y - VIA / 2, x + VIA / 2, y + VIA / 2, VIA2)
        rect(x - M3_PAD / 2, y - M3_PAD / 2, x + M3_PAD / 2, y + M3_PAD / 2, MET3)

    # ---- per-row control signals (uniform tile height = max over rows)
    row_ctrl = []
    for r in range(R):
        sigs = set()
        for c in range(C):
            sigs |= set(tile_signals(grid[r][c], bits).values())
        order = [s for s in CTRL_ORDER if s in sigs] + sorted(s for s in sigs if s not in CTRL_ORDER)
        row_ctrl.append(order)
    n_ctrl = max(len(o) for o in row_ctrl)

    # ---- device templates (identical geometry in every tile; nets differ)
    proto = tile_devices(design, 0, bits, "proto")
    comps = [_make_device(d) for d in proto]
    bb = [(cp.bbox[1][0] - cp.bbox[0][0], cp.bbox[1][1] - cp.bbox[0][1]) for cp in comps]
    # inner-bar offset (after 180 rotation: y -> -y)
    inner = [-cp.ports["multiplier_0_source_W"].center[1] for cp in comps]
    widths = [w for w, _ in bb]
    xs, x = [], 0.0
    for k, w in enumerate(widths):
        xs.append(x + w / 2)
        x += w + (NP_GAP if k == 1 else DEV_GAP)
    tile_w = x - (DEV_GAP) + TILE_GAP

    # vertical plan inside a tile (y from the tile bottom)
    y_tap = 0.35
    y_rail0 = 1.05
    rail_y = {s: snap(y_rail0 + i * RAIL_PITCH) for i, s in enumerate(SUPPLY)}
    dev_bottom = rail_y["vref"] + RAIL_W / 2 + 0.55
    y_inner = snap(dev_bottom + max(h / 2 + off for (w, h), off in zip(bb, inner)))
    dev_cy = [snap(y_inner - off) for off in inner]              # device centres (inner bars aligned)
    dev_top = max(cy + h / 2 for cy, (w, h) in zip(dev_cy, bb))
    y_ctrl0 = snap(dev_top + 0.45)
    tile_h = snap(y_ctrl0 + (n_ctrl - 1) * RAIL_PITCH + RAIL_W / 2 + 0.6)

    unit = mimcap(sky130, (design["cu"]["side"], design["cu"]["side"]))
    ucx0, ucy0 = unit.bbox[0]
    ucx1, ucy1 = unit.bbox[1]
    cap_h = ucy1 - ucy0
    cap_cy = snap(tile_h - cap_h / 2 - 0.2)                       # cap sits over the control rails
    cap_cx = snap((tile_w - TILE_GAP) / 2)
    tap = via_stack(sky130, "active_tap", "met2")                  # gLayout met2 = sky130 met1

    ref_lines, plate_nets = [], []
    lvt_nwell = []
    for r in range(R):
        y0 = (R - 1 - r) * tile_h
        ctrl_y = {s: snap(y0 + y_ctrl0 + i * RAIL_PITCH) for i, s in enumerate(row_ctrl[r])}
        sup_y = {s: snap(y0 + v) for s, v in rail_y.items()}
        for c in range(C):
            g = grid[r][c]
            tag = f"{r}_{c}"
            x0 = c * tile_w
            devs = tile_devices(design, g, bits, tag)
            for k, (dv, cp) in enumerate(zip(devs, comps)):
                ref = top << cp
                ref.rotate(180)
                ref.move((snap(x0 + xs[k]), snap(y0 + dev_cy[k])))
                p = ref.ports
                gx = (p["multiplier_0_gate_W"].center[0] + p["multiplier_0_gate_E"].center[0]) / 2
                gy = p["multiplier_0_gate_W"].center[1]
                ix = (p["multiplier_0_source_W"].center[0] + p["multiplier_0_source_E"].center[0]) / 2
                iy = p["multiplier_0_source_W"].center[1]
                ox = (p["multiplier_0_drain_W"].center[0] + p["multiplier_0_drain_E"].center[0]) / 2
                oy = p["multiplier_0_drain_W"].center[1]
                # gate -> control rail
                yr = ctrl_y[dv.g]
                rect(gx - M1_STUB / 2, gy, gx + M1_STUB / 2, yr, MET1)
                v1(gx, yr)
                # outer bar -> supply rail (offset from the bar centre so it misses the inner-bar via)
                sx = snap(ox + 0.25) if k % 2 == 0 else snap(ox - 0.25)
                ys = sup_y[dv.d]
                rect(sx - M1_STUB / 2, ys, sx + M1_STUB / 2, oy, MET1)
                v1(sx, ys)
                # inner bar -> met3 plate bus
                v1(ix, iy, along_x=True)
                v2(ix, iy)
                ref_lines.append(mos(dv.name, dv.d, dv.g, dv.s, "vss" if dv.kind == "n" else "vdd",
                                     model_name(dv), dv.w, dv.l))
            # plate bus + riser into the cap bottom plate
            bus_y = snap(y0 + y_inner)
            ixs = [snap(x0 + xs[k]) for k in range(4)]
            rect(min(ixs) - M3_PAD / 2, bus_y - M3_PAD / 2, max(ixs) + M3_PAD / 2, bus_y + M3_PAD / 2, MET3)
            cx, cy = snap(x0 + cap_cx), snap(y0 + cap_cy)
            capref = top << unit
            capref.move((cx, cy))
            rect(cx - 0.25, bus_y - M3_PAD / 2, cx + 0.25, cy + ucy0 + 0.3, MET3)
            ref_lines.append(f"XC{tag} top p_{tag} sky130_fd_pr__cap_mim_m3_1 W={design['cu']['side']} "
                             f"L={design['cu']['side']} MF=1")
            # body taps: p-tap under the NMOS pair, n-tap under the PMOS pair
            for k_tap, (tx, net, imp) in enumerate(((x0 + xs[0] - 0.5, "vss", PSDM), (x0 + xs[3] + 0.5, "vdd", NSDM))):
                t = top << tap
                t.move((snap(tx), snap(y0 + y_tap)))
                rect(tx - 0.34, y0 + y_tap - 0.34, tx + 0.34, y0 + y_tap + 0.34, imp)
                rect(tx - M1_STUB / 2, y0 + y_tap, tx + M1_STUB / 2, sup_y[net], MET1)
                v1(snap(tx), sup_y[net])
            # n-well over the PMOS pair and its tap
            nx0 = x0 + xs[2] - widths[2] / 2 - 0.1
            nx1 = x0 + max(xs[3] + widths[3] / 2 + 0.1, xs[3] + 0.5 + 0.21 + 0.18)
            lvt_nwell.append((nx0, y0 + y_tap - 0.55, nx1, y0 + dev_top + 0.1))
        # rails through the row (extended to the trunks later)
        for s, yy in list(sup_y.items()) + list(ctrl_y.items()):
            plate_nets.append((s, yy))
    for nx0, ny0, nx1, ny1 in lvt_nwell:
        rect(nx0, ny0, nx1, ny1, NWELL)

    # ---- top plate: met4 strap per row through the cap centres + vertical spine
    W_arr = C * tile_w - TILE_GAP
    for r in range(R):
        yy = (R - 1 - r) * tile_h + cap_cy
        rect(cap_cx - STRAP_W / 2, yy - STRAP_W / 2, (C - 1) * tile_w + cap_cx + STRAP_W / 2, yy + STRAP_W / 2, MET4)
    xsp = (C // 2) * tile_w + cap_cx
    rect(xsp - STRAP_W / 2, cap_cy, xsp + STRAP_W / 2, (R - 1) * tile_h + cap_cy, MET4)
    rect(xsp - 0.3, (R - 1) * tile_h + cap_cy - 0.3, xsp + 0.3, (R - 1) * tile_h + cap_cy + 0.3, PIN[MET4])
    top.add_label(text="top", position=(xsp, (R - 1) * tile_h + cap_cy), layer=LBL[MET4])

    # ---- rails and edge trunks: supplies + phases on the left, bit controls on the right
    nets = sorted({s for s, _ in plate_nets}, key=lambda s: (SUPPLY + CTRL_ORDER + [s]).index(s))
    left = [s for s in nets if s in SUPPLY or s in CTRL_ORDER]
    right = [s for s in nets if s not in left]
    trunk_x = {s: snap(-1.6 - i * 0.9) for i, s in enumerate(left)}
    trunk_x.update({s: snap(W_arr + 1.6 + i * 0.9) for i, s in enumerate(right)})
    for s, yy in plate_nets:
        xa, xb = (trunk_x[s], W_arr) if s in left else (0.0, trunk_x[s])
        rect(xa - M2_PAD / 2, yy - RAIL_W / 2, xb + M2_PAD / 2, yy + RAIL_W / 2, MET2)
        v2(trunk_x[s], yy)
    for s in nets:
        ys = [yy for n, yy in plate_nets if n == s]
        y_lo, y_hi = min(ys) - M3_PAD / 2, max(max(ys) + M3_PAD / 2, min(ys) + 1.0)
        rect(trunk_x[s] - 0.25, y_lo, trunk_x[s] + 0.25, y_hi, MET3)
        rect(trunk_x[s] - 0.25, y_hi - 0.5, trunk_x[s] + 0.25, y_hi, PIN[MET3])
        top.add_label(text=s, position=(trunk_x[s], snap(y_hi - 0.25)), layer=LBL[MET3])

    # flatten: device n-wells, the row n-well and the taps must be one shape for magic (wells per cell)
    top = top.flatten()
    top.name = name
    pins = ["top"] + nets
    ref = "\n".join([f".subckt {top.name} {' '.join(pins)}"] + ref_lines + [f".ends {top.name}"]) + "\n"
    bbx = top.bbox
    info = dict(bits=bits, grid=grid, tile=(round(tile_w, 3), round(tile_h, 3)), ctrl_rails=n_ctrl,
                width=float(bbx[1][0] - bbx[0][0]), height=float(bbx[1][1] - bbx[0][1]), pins=pins)
    return top, info, ref
