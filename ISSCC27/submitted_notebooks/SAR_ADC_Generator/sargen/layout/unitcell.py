"""CDAC unit cell: one MIM unit capacitor with its own bottom-plate switch, built for abutment (SKY130).

    y ^  ...........  MIM cap (PDK PCell): only met2 rails underneath (capm.10)  ......  | n-well column,
         drive rails pg_k / ng_k  met2, edge to edge, pass under the cap              | vref / vdd lines
         vin rail                 met2                                                | (met1), n-tap
         [Mdn][Msn] | [Msp][Mdp]  SKY130 PDK FET PCells (li only) + plate bus (met2) in the street between
         sample rails phi*        met2                          the caps of two rows (capm.11 spacing)
       x ->  vss line, p-tap and top-plate strap on the NMOS edge (x = 0);  vref, vdd lines on the PMOS edge

SKY130 rule capm.10 keeps nwell, diff, tap, poly, li and met1 out from under a MIM cap, so the four switch
transistors sit in the street that capm.11 (1.34 um from capm to an unrelated met3) leaves between the caps of
two rows, and under the PCell's capm-free bottom-plate overhang.  Gates that are not under the cap's x-range
(Mdn on the NMOS edge, Msp and Mdp beside the cap) reach any rail through li/met1 stubs beside the cap; Msn
(under the cap's x-range) reaches only the sample rails in the street.  The cap's met3 plate shields its top
plate from everything below; the top plate leaves the PCell's C1 contact on a met4 stub to a vertical met4
strap on the vss edge (no met5: TinyTapeout power grid).  Cells are mirrored left/right in an array: the vss
line, p-tap and strap are shared on the NMOS edge, the vdd line, n-tap and n-well column on the PMOS edge.
Rows abut vertically.  Only the via positions of the four gates differ between cells, so every unit is
geometrically identical.
"""

from .cdac import LBL, M2_PAD, M3_PAD, MET2, MET3, MET4, PIN, VIA, VIA2, snap
from .cell import DIFF, MET1, NWELL, VIA1, V1, Dev

CAPM = (89, 44)
LI, MCON, POLY, TAP = (67, 20), (67, 44), (66, 20), (65, 44)
NSDM, PSDM = (93, 44), (94, 20)
LVTN = (125, 44)
CAPM10 = [NWELL, DIFF, TAP, POLY, LI, MET1]   # capm.10: none of these under a MIM cap
CTRL_PITCH, CTRL_W = 0.34, 0.14       # control rails (met2, min width); via1 pads widen to 0.26 at the via
M1_LINE = 0.23                        # vertical supply line (met1): mcon + 0.03 enclosure
MC = 0.17                             # mcon
V1_M1 = (0.27, 0.32)                  # met1 pad around mcon + via1 (x, y)
V1_M2 = (0.32, 0.26)                  # met2 pad around via1 on a horizontal rail (x, y)
STRAP_W = 0.40                        # vertical top-plate strap (met4), centred on the vss edge (2 ohm per array)
TRUNK_STRAP = 0.40                    # trunks beside the array keep this far from the strap (top-plate coupling)
STUB_W = 0.60                         # met4 stub from the PCell top contact C1 to the strap
SUPPLY = ["vss", "vin", "vref", "vdd"]
LINES = ["vss", "vref", "vdd"]        # vertical met1 supply lines (vin is a met2 rail)
GATE_SIDE = ["top", "bot", "bot", "top"]   # Mdn, Msn, Msp, Mdp: drive gates up, sample gates down
# SKY130 rules used to pack the cell
R_DIFF_SP, R_LI_SP, R_POLY_SP, R_M1_SP, R_M2_SP = 0.27, 0.17, 0.21, 0.14, 0.14
R_NDIFF_NWELL, R_NWELL_PDIFF, R_LVT_GATE, R_LVTN_SP = 0.34, 0.18, 0.24, 0.38
R_IMP_SP = 0.38                       # nsdm / psdm spacing: closer same-type implants are merged
CAPM11 = 1.34                         # capm to unrelated met3
VIA2_CAPM = 0.20                      # via2 clearance from a capm edge (magic capm.8)
M3_SP, M3_SP_WIDE = 0.30, 0.40         # met3 spacing; to met3 wider than 3 um (m3.3d)
TOP_BAR_GAP = 0.40                    # met4 top-plate bar below an array / test block


def cell_devices(design, gates, tag="u"):
    """gates: dict en/enb/pg/ng -> net names.  d = supply (outer bar), s = plate (inner bar)."""
    from ..pdk import TG_FLAVORS
    sw, drv = design["sw"], design["drv"]
    fl = sw.get("flavor", "lvt")
    ln, lp = TG_FLAVORS[fl][1], TG_FLAVORS[fl][3]
    p = f"p_{tag}"
    kw = dict(fingers=1, tie=False)
    return [Dev(f"Mdn_{tag}", "n", drv["wn"], 0.15, "vss", gates["ng"], p, **kw),
            Dev(f"Msn_{tag}", "n", sw["in_wn"], ln, "vin", gates["en"], p, flavor=fl, **kw),
            Dev(f"Msp_{tag}", "p", sw["in_wp"], lp, "vin", gates["enb"], p, flavor=fl, **kw),
            Dev(f"Mdp_{tag}", "p", drv["wp"], 0.15, "vref", gates["pg"], p, **kw)]


def _ext(comp, layer):
    pts = [pt for poly in comp.get_polygons(by_spec=layer) for pt in poly]
    if not pts:
        return None
    return min(p[0] for p in pts), max(p[0] for p in pts), min(p[1] for p in pts), max(p[1] for p in pts)


def _ceil01(v):
    """Round a cell pitch up to 0.01 um, so every multiple and half of it stays on the 5 nm grid."""
    import math
    return round(math.ceil(round(v, 6) * 100 - 1e-6) / 100, 2)


class _Fet:
    """A FET PCell and the geometry the cell is packed from: x from the gate centre, y from the diffusion
    centre (the PCell is symmetric in x, so it is never mirrored).  PMOS PCells lose their own n-well: the
    cell draws one n-well for the pair that stays out from under the cap."""

    def __init__(self, dv, gate):
        from .cell import model_name
        from .pcell import fet, import_pcell
        drop = ((235, 4), (67, 5), (68, 5), (71, 5)) + ((NWELL,) if dv.kind == "p" else ())
        self.comp = c = import_pcell(*fet(model_name(dv), dv.w, dv.l, gate), drop_layers=drop)
        d = _ext(c, DIFF)
        self.oy = -(d[2] + d[3]) / 2                       # PCell origin -> diffusion centre

        def rel(e):
            return e and (e[0], e[1], e[2] + self.oy, e[3] + self.oy)
        self.diff, self.poly, self.lvt = rel(d), rel(_ext(c, POLY)), rel(_ext(c, LVTN))
        self.imp = rel(_ext(c, NSDM) or _ext(c, PSDM))
        li = [rel((min(p[:, 0]), max(p[:, 0]), min(p[:, 1]), max(p[:, 1]))) for p in c.get_polygons(by_spec=LI)]
        bars = [b for b in li if b[2] < self.diff[3] and b[3] > self.diff[2]]
        pad = [b for b in li if b not in bars][0]
        self.sd = max(abs(b[0] + b[1]) / 2 for b in bars)                  # bar centre from the gate
        self.bar_y = (min(b[2] for b in bars), max(b[3] for b in bars))
        self.pad, self.pad_y = pad, (pad[2] + pad[3]) / 2
        # capm.10 layers of the PCell, for the street height
        self.restricted = [rel((min(p[:, 0]), max(p[:, 0]), min(p[:, 1]), max(p[:, 1])))
                           for lay in CAPM10 for p in c.get_polygons(by_spec=lay)]
        assert abs(self.diff[0] + self.diff[1]) < 1e-6, "FET PCell not symmetric in x"


class UnitCellPlan:
    """Geometry shared by every cell of an array, packed from the PCells' real layer extents and SKY130 rules.

    n_bot sample rails below the device row (the n_street nearest ones reachable by Msn, so inside the street),
    n_top drive rails above the vin rail."""

    def __init__(self, design, n_bot, n_top, n_street=None):
        from glayout import sky130, via_stack
        from .pcell import import_pcell, mim_cap
        n_street = n_bot if n_street is None else n_street
        proto = cell_devices(design, dict(en="a", enb="b", pg="c", ng="d"), "proto")
        self.fets = f = [_Fet(d, s) for d, s in zip(proto, GATE_SIDE)]
        self.n_bot, self.n_top, self.n_street = n_bot, n_top, n_street

        # MIM unit cap = SKY130 PDK PCell (C1 top contact over the capm, C2 bottom-plate strip on the right).
        # capm.11 against the mirrored neighbour on the vss edge (capm sides face each other), met3 spacing
        # between the plates on the vdd edge (C2 sides face each other)
        side = design["cu"]["side"]
        self.unit = import_pcell(*mim_cap(side, side))
        ub = self.unit.bbox
        self.cap_x0, self.cap_x1, self.cap_y0, self.cap_y1 = ub[0][0], ub[1][0], ub[0][1], ub[1][1]
        cm = self.capm = _ext(self.unit, CAPM)
        c1 = [p for p in self.unit.get_polygons(by_spec=MET4) if min(p[:, 0]) < cm[1]][0]   # C2 is right of the capm
        self.c1_x0 = min(c1[:, 0])
        self.cap_cx = snap((CAPM11 - cm[0] - self.cap_x0) / 2 + 0.0025)
        cl, cr = self.cap_cx + cm[0], self.cap_cx + cm[1]                  # capm x-range in the cell
        self.capm_x = (cl, cr)
        # met3 spacing between the plates: 0.3 um, 0.4 um once a plate is wider than 3 um in both directions (m3.3d)
        self.m3_sp = M3_SP_WIDE if min(self.cap_x1 - self.cap_x0, self.cap_y1 - self.cap_y0) > 3.0 else M3_SP
        w_cap = self.cap_cx + self.cap_x1 + self.m3_sp / 2

        # x: Mdn | Msn | n-well: Msp | Mdp | vref line | vdd line.  Facing inner bars carry plate met1 pads
        cg = V1_M1[0] / 2 + R_M1_SP + M1_LINE / 2           # gate met1 pad centre -> supply line centre

        def same(a, b):
            d = max(f[a].diff[1] - f[b].diff[0] + R_DIFF_SP, f[a].sd + f[b].sd + V1_M1[0] + R_M1_SP)
            if f[b].lvt and not f[a].lvt:
                d = max(d, f[a].poly[1] - f[b].lvt[0] + R_LVT_GATE)
            if f[a].lvt and not f[b].lvt:
                d = max(d, f[a].lvt[1] + R_LVT_GATE - f[b].poly[0])
            return d

        def column(fe):                                     # half width of a gate column (pad, poly, via)
            return max(V1_M1[0] / 2, fe.pad[1], fe.poly[1], MC / 2)

        # NMOS edge: mirrored Mdn faces Mdn; its gate column clears the vss line and stays left of the capm
        xg0 = max(R_DIFF_SP / 2 - f[0].diff[0], R_POLY_SP / 2 - f[0].poly[0], R_LI_SP / 2 - f[0].pad[0], cg)
        assert xg0 + column(f[0]) <= cl, "Mdn gate column under the cap"
        xg1 = xg0 + same(0, 1)
        # n-diff -> n-well (0.34) -> p-diff (0.18); NMOS lvtn outside the well; Msp's gate column beside the capm
        np_d = f[1].diff[1] + R_NDIFF_NWELL + R_NWELL_PDIFF - f[2].diff[0]
        if f[1].lvt:
            np_d = max(np_d, f[1].lvt[1] + R_NWELL_PDIFF - f[2].diff[0])
            if f[2].lvt:
                np_d = max(np_d, f[1].lvt[1] + R_LVTN_SP - f[2].lvt[0])
        xg2 = max(xg1 + np_d, cr + column(f[2]))
        xg3 = xg2 + same(2, 3)
        self.xg = xg = [snap(v) for v in (xg0, xg1, xg2, xg3)]
        self.x_in = [xg[0] + f[0].sd, xg[1] - f[1].sd, xg[2] + f[2].sd, xg[3] - f[3].sd]   # plate bars
        self.x_out = [xg[0] - f[0].sd, xg[1] + f[1].sd, xg[2] - f[2].sd, xg[3] + f[3].sd]  # supply bars
        self.x_vin = snap((self.x_out[1] + self.x_out[2]) / 2)                            # vin via
        self.nx0 = snap(xg[2] + f[2].diff[0] - R_NWELL_PDIFF)
        self.sup_x = {"vss": 0.0, "vref": snap(xg[3] + cg)}
        w_dev = max(self.sup_x["vref"] + (V1_M1[0] + M1_LINE) / 2 + R_M1_SP,   # vdd line on the edge (room for a via pad)
                    xg[3] + f[3].diff[1] + R_DIFF_SP / 2, xg[3] + f[3].poly[1] + R_POLY_SP / 2,
                    xg[3] + f[3].pad[1] + R_LI_SP / 2)
        self.W = _ceil01(max(w_dev, w_cap))
        self.sup_x["vdd"] = self.W

        # y, relative to the plate bus (P = 0 here): sample rails below, vin + drive rails above
        t_min = V1_M1[1] + R_M1_SP                          # rail via pads clear the plate pads
        s_max = -(f[1].bar_y[0] + MC / 2)                   # Msn may move up while P stays on its bar
        b0 = max(t_min, -f[1].pad_y - s_max)
        self.shift = [0.0, max(0.0, -b0 - f[1].pad_y), 0.0, 0.0]   # Msn's gate contact meets the first rail
        self.vin_dy = max(V1_M2[1] / 2 + R_M2_SP + V1_M2[1] / 2, M2_PAD / 2 + R_M2_SP + CTRL_W / 2)
        bot = [-(b0 + k * CTRL_PITCH) for k in range(n_bot)]           # nearest first
        top = [self.vin_dy + (k + 1) * CTRL_PITCH for k in range(n_top)]
        for k in (0, 3):
            assert f[k].pad_y + self.shift[k] <= top[0], "drive gate contact above the first drive rail"
        # street: every capm.10 shape whose x-range meets the capm's must lie between two rows of caps
        boxes = []
        for k, fe in enumerate(f):
            boxes += [(xg[k] + b[0], xg[k] + b[1], self.shift[k] + b[2], self.shift[k] + b[3]) for b in fe.restricted]
        pw = [(fe.diff[2] + self.shift[k], fe.diff[3] + self.shift[k]) for k, fe in ((2, f[2]), (3, f[3]))]
        self.nw_y = (min(a for a, _ in pw) - R_NWELL_PDIFF, max(b for _, b in pw) + R_NWELL_PDIFF)
        boxes.append((self.nx0, self.W, *self.nw_y))
        hm = V1_M1[1] / 2
        boxes += [(x - V1_M1[0] / 2, x + V1_M1[0] / 2, -hm, hm) for x in self.x_in]          # plate pads
        boxes.append((xg[1] - V1_M1[0] / 2, xg[1] + V1_M1[0] / 2, bot[n_street - 1] - hm, hm))  # Msn gate stub
        boxes.append((self.x_vin - V1_M1[0] / 2, self.x_vin + V1_M1[0] / 2, -hm, self.vin_dy + hm))
        under = [b for b in boxes if b[1] > cl and b[0] < cr]
        lo, hi = min(b[2] for b in under), max(b[3] for b in under)
        cap_h = cm[3] - cm[2]
        h_cap = CAPM11 + max(self.cap_y1 - cm[2], cm[3] - self.cap_y0)            # capm.11 to the row above
        h_street = hi - lo + cap_h
        h_rails = top[-1] - bot[-1] + CTRL_PITCH
        self.H = _ceil01(max(h_cap, h_street, h_rails))
        self.P = P = snap(-bot[-1] + CTRL_PITCH / 2 + (self.H - h_rails) / 2)
        self.yc = [snap(P + s) for s in self.shift]                                # diffusion centres
        self.bot_y = [snap(P + y) for y in reversed(bot)]                          # bottom to top
        self.top_y = [snap(P + y) for y in top]
        self.vin_y = snap(P + self.vin_dy)
        self.ctrl_y = self.bot_y + self.top_y
        self.street = (P + lo, P + hi)
        # cap centred in the band between this street and the next row's
        self.cap_cy = snap(P + hi + (self.H - (hi - lo) - cap_h) / 2 - cm[2])
        self.nw_y = (P + self.nw_y[0], P + self.nw_y[1])
        # plate: via2 + met3 riser from the plate bus up into the plate, beside the capm, clear (capm.11) of the
        # capm of the row below
        dy = (P - M3_PAD / 2) - (self.cap_cy + cm[3] - self.H)
        dx = (CAPM11 ** 2 - dy ** 2) ** 0.5 if dy < CAPM11 else 0.0
        self.riser_x = snap(max(cr + VIA2_CAPM + VIA / 2, cr + dx + M3_PAD / 2) + 0.005)   # grid margin
        assert self.riser_x + M3_PAD / 2 <= self.cap_cx + self.cap_x1, "no room for the plate riser"
        assert (P - M3_PAD / 2) - (self.cap_cy + self.cap_y1 - self.H) >= self.m3_sp, "riser too close to the plate below"
        self.tap = via_stack(sky130, "active_tap", "met2")
        tb_ = self.tap.bbox
        self.tap_half = max(abs(v) for v in (tb_[0][0], tb_[1][0], tb_[0][1], tb_[1][1]))
        self.ptap_y = self.ntap_y = self.cap_cy                  # beside the cap, on the cell edges


def draw_cell(top, plan, x0, y0, mirror, rails, gates, tag, design):
    """Draw one cell into component `top` at (x0, y0).  rails = (bottom rails, top rails), each listed bottom
    to top; the n_street bottom rails nearest the device row can serve Msn.  Returns reference-netlist lines."""

    from ..pdk import mos
    from .cell import model_name

    W, H, P, f = plan.W, plan.H, plan.P, plan.fets

    def X(x):                       # local x -> layout x (mirrored about the cell centre)
        return x0 + (W - x if mirror else x)

    def rect(xa, ya, xb, yb, layer):
        xa, xb = sorted((X(xa), X(xb)))
        ya, yb = y0 + min(ya, yb), y0 + max(ya, yb)
        _poly(top, xa, ya, xb, yb, layer)

    def box(x, y, w, h, layer):
        rect(x - w / 2, y - h / 2, x + w / 2, y + h / 2, layer)

    def mcon(x, y):
        box(x, y, MC, MC, MCON)
        box(x, y, V1_M1[0] - 0.04, V1_M1[1] - 0.04, MET1)        # 0.03 / 0.06 enclosure

    def via1(x, y):                 # li -> met2: mcon, met1 pad, via1, met2 pad
        box(x, y, MC, MC, MCON)
        box(x, y, *V1_M1, MET1)
        box(x, y, V1, V1, VIA1)
        box(x, y, *V1_M2, MET2)

    devs = cell_devices(design, gates, tag)
    bot, topr = rails
    rail_y = {"bot": dict(zip(bot, plan.bot_y)), "top": dict(zip(topr, plan.top_y))}   # a net may be on both sides
    lines = []
    for k, (dv, fe) in enumerate(zip(devs, f)):
        xg, yc = plan.xg[k], plan.yc[k]
        ref = top << fe.comp
        ref.move((snap(X(xg)), snap(y0 + yc + fe.oy)))
        # gate: li from the PCell gate contact out to its rail, via up to the met2 rail
        side = GATE_SIDE[k]
        y_pad = yc + fe.pad_y
        if dv.g == "vdd" and k == 3:            # Vref driver held off (termination unit): li to the n-tap
            rect(xg - MC / 2, y_pad, xg + MC / 2, plan.ntap_y + MC / 2, LI)
            rect(xg - MC / 2, plan.ntap_y - MC / 2, W, plan.ntap_y + MC / 2, LI)
        else:
            assert dv.g in (bot if side == "bot" else topr), f"{dv.g} is not a {side} rail"
            y_r = rail_y[side][dv.g]
            assert (y_r <= y_pad + 1e-6) if side == "bot" else (y_r >= y_pad - 1e-6), f"{dv.name}: rail {dv.g} unreachable"
            if k == 1:
                assert y_r >= plan.bot_y[plan.n_bot - plan.n_street] - 1e-6, f"{dv.g} is outside the street"
            rect(xg - MC / 2, min(y_pad, y_r) - MC / 2, xg + MC / 2, max(y_pad, y_r) + MC / 2, LI)
            via1(xg, y_r)
        # inner bar -> plate bus
        via1(plan.x_in[k], P)
        lines.append(mos(dv.name, dv.d, dv.g, dv.s, "vss" if dv.kind == "n" else "vdd", model_name(dv), dv.w, dv.l))
    # outer bars -> supplies (li stubs at the plate-bus height): vss / vref lines (met1), vin rail (met2)
    xo, sx = plan.x_out, plan.sup_x
    rect(sx["vss"] - MC / 2, P - MC / 2, xo[0], P + MC / 2, LI)
    rect(xo[1], P - MC / 2, xo[2], P + MC / 2, LI)
    rect(plan.x_vin - MC / 2, P, plan.x_vin + MC / 2, plan.vin_y + MC / 2, LI)
    via1(plan.x_vin, plan.vin_y)
    rect(xo[3], P - MC / 2, sx["vref"] + MC / 2, P + MC / 2, LI)
    for net in ("vss", "vref"):
        mcon(sx[net], P)
    for net, x in sx.items():
        rect(x - M1_LINE / 2, 0, x + M1_LINE / 2, H, MET1)
    # plate bus (met2) through the inner bars, via2 + met3 riser beside the capm into the PCell plate
    xs = plan.x_in + [plan.riser_x]
    rect(min(xs) - V1_M2[0] / 2, P - V1_M2[1] / 2, max(xs) + M2_PAD / 2, P + V1_M2[1] / 2, MET2)
    box(plan.riser_x, P, M2_PAD, M2_PAD, MET2)
    box(plan.riser_x, P, VIA, VIA, VIA2)
    rect(plan.riser_x - M3_PAD / 2, P - M3_PAD / 2, plan.riser_x + M3_PAD / 2, plan.cap_cy + plan.cap_y0 + 0.2, MET3)
    capref = top << plan.unit
    if mirror:                      # the PDK PCell is asymmetric (C1 left, C2 strip right): mirror it too
        capref.mirror((0, 0), (0, 1))
    capref.move((snap(X(plan.cap_cx)), snap(y0 + plan.cap_cy)))
    side = design["cu"]["side"]
    lines.append(f"XC_{tag} top p_{tag} sky130_fd_pr__cap_mim_m3_1 W={side} L={side} MF=1")
    # control rails and the vin rail, edge to edge
    for y in plan.ctrl_y:
        rect(0, y - CTRL_W / 2, W, y + CTRL_W / 2, MET2)
    rect(0, plan.vin_y - CTRL_W / 2, W, plan.vin_y + CTRL_W / 2, MET2)
    # top plate (met4 only): C1 -> stub -> vertical strap on the vss edge
    rect(-STRAP_W / 2, 0, STRAP_W / 2, H, MET4)
    rect(0, plan.cap_cy - STUB_W / 2, plan.cap_cx + plan.c1_x0 + 0.2, plan.cap_cy + STUB_W / 2, MET4)
    # body taps on the cell edges, beside the cap under their supply lines (shared with the mirrored neighbour)
    for tx, ty, imp in ((0.0, plan.ptap_y, PSDM), (W, plan.ntap_y, NSDM)):
        t = top << plan.tap
        t.move((snap(X(tx)), snap(y0 + ty)))
        box(tx, ty, 0.68, 0.68, imp)
    # n-well: the PMOS pair in the street, plus a column beside the cap (n-tap; continuous through the rows)
    ex = W + plan.tap_half + R_NWELL_PDIFF
    rect(plan.nx0, plan.nw_y[0], ex, plan.nw_y[1], NWELL)
    rect(plan.capm_x[1], plan.nw_y[0], ex, plan.nw_y[0] + H, NWELL)
    # implants: bridge same-type neighbours (and the mirrored neighbours on the edges) closer than 0.38 um
    imp = [(plan.xg[k] + fe.imp[0], plan.xg[k] + fe.imp[1], plan.yc[k] + fe.imp[2], plan.yc[k] + fe.imp[3])
           for k, fe in enumerate(f)]
    for a, b, lay in ((0, 1, NSDM), (2, 3, PSDM)):
        if 0 < imp[b][0] - imp[a][1] < R_IMP_SP:
            rect(imp[a][1] - 0.01, min(imp[a][2], imp[b][2]), imp[b][0] + 0.01, max(imp[a][3], imp[b][3]), lay)
    if 2 * imp[0][0] < R_IMP_SP:
        rect(-0.05, imp[0][2], imp[0][0] + 0.01, imp[0][3], NSDM)
    if 2 * (W - imp[3][1]) < R_IMP_SP:
        rect(imp[3][1] - 0.01, imp[3][2], W + 0.05, imp[3][3], PSDM)
    return lines


def _poly(top, xa, ya, xb, yb, layer):
    """Exact rectangle on the 5 nm grid (gdsfactory's rectangle() rounds its size to 2 grid steps)."""
    xa, xb, ya, yb = snap(min(xa, xb)), snap(max(xa, xb)), snap(min(ya, yb)), snap(max(ya, yb))
    if xb > xa and yb > ya:
        top.add_polygon([(xa, ya), (xb, ya), (xb, yb), (xa, yb)], layer=layer)


def _pin(top, net, x, y, layer, size=(0.3, 0.16)):
    """Pin shape + label centred at (x, y)."""
    lbl, pin = (dict(LBL) | {MET1: (68, 5)})[layer], (dict(PIN) | {MET1: (68, 16)})[layer]
    _poly(top, x - size[0] / 2, y - size[1] / 2, x + size[0] / 2, y + size[1] / 2, pin)
    top.add_label(text=net, position=(snap(x), snap(y)), layer=lbl)


def _subckt(name, pins, lines):
    return "\n".join([f".subckt {name} {' '.join(pins)}"] + lines + [f".ends {name}"]) + "\n"


def _n_street(bot, gate_maps):
    """How many sample rails, counted from the device row, Msn must reach (they must lie in the street)."""
    return max([len(bot) - bot.index(g["en"]) for g in gate_maps if g["en"] in bot] or [1])


def build_unit_cell(design, rails, gates, name="cdac_unit"):
    """A single unit cell (flattened), its reference netlist and pins.  rails = (bottom, top) rail names."""
    from gdsfactory import Component
    plan = UnitCellPlan(design, len(rails[0]), len(rails[1]), _n_street(rails[0], [gates]))
    top = Component(name + "_hier")
    lines = draw_cell(top, plan, 0.0, 0.0, False, rails, gates, "u", design)
    for net, y in list(zip(rails[0] + rails[1], plan.ctrl_y)) + [("vin", plan.vin_y)]:
        _pin(top, net, 0.3, y, MET2, (0.3, CTRL_W))
    for net, x in plan.sup_x.items():
        _pin(top, net, x, plan.H - 0.3, MET1, (0.14, 0.3))
    _pin(top, "top", 0.0, plan.H - 0.3, MET4)
    top = top.flatten()
    top.name = name
    pins = ["top"] + SUPPLY + rails[0] + rails[1]
    return top, plan, _subckt(name, pins, lines)


def _tie_supplies(rect, plan, cols, rows, vin_x):
    """Test/array scaffolding: vertical supply lines -> met2 bars below the block; the rows' vin rails -> a
    met1 trunk at vin_x left of the block -> the vin bar.  Returns {net: (x, y)} pin positions."""
    W, H = plan.W, plan.H

    def via(x, y):
        rect(x - V1_M1[0] / 2, y - V1_M1[1] / 2, x + V1_M1[0] / 2, y + V1_M1[1] / 2, MET1)
        rect(x - V1 / 2, y - V1 / 2, x + V1 / 2, y + V1 / 2, VIA1)
        rect(x - V1_M2[0] / 2, y - V1_M2[1] / 2, x + V1_M2[0] / 2, y + V1_M2[1] / 2, MET2)

    pins = {}
    for i, net in enumerate(SUPPLY):
        yb = -0.6 - i * 0.8
        if net == "vin":
            xs = [vin_x]
            ys = [r * H + plan.vin_y for r in range(rows)]
            for y in ys:
                rect(vin_x, y - CTRL_W / 2, 0, y + CTRL_W / 2, MET2)
                via(vin_x, y)
            rect(vin_x - V1_M1[0] / 2, yb, vin_x + V1_M1[0] / 2, max(ys), MET1)
        else:
            xs = sorted({snap(c * W + (W - plan.sup_x[net] if c % 2 else plan.sup_x[net])) for c in range(cols)})
            for x in xs:
                rect(x - M1_LINE / 2, yb, x + M1_LINE / 2, 0, MET1)
        for x in xs:
            via(x, yb)
        rect(xs[0] - V1_M2[0] / 2, yb - 0.2, xs[-1] + V1_M2[0] / 2, yb + 0.2, MET2)
        pins[net] = (xs[0], yb)
    return pins


def _top_bar(rect, plan, cols, y_top=0.0):
    """Top-plate straps -> met4 bar below the block (below y_top), where the nearest caps are > 1.5 um away;
    above the top row the bar would add ~0.2 fF of top-to-bottom-plate fringe to those units only."""
    W = plan.W
    xs = sorted({snap(c * W + (W if c % 2 else 0)) for c in range(cols)})
    yb = y_top - TOP_BAR_GAP - STRAP_W
    for x in xs:
        rect(x - STRAP_W / 2, yb, x + STRAP_W / 2, 0, MET4)
    rect(xs[0] - STRAP_W / 2, yb, xs[-1] + STRAP_W / 2, yb + STRAP_W, MET4)


def _draw_dummy(top, plan, x0, y0, mirror):
    """Dummy unit cap at a cell position: the PDK MIM PCell only, top and bottom plate shorted on met4 (C1 to
    the C2 strip).  Returns the plate (met3) box in layout coordinates."""
    W = plan.W
    X = lambda x: x0 + (W - x if mirror else x)
    capref = top << plan.unit
    if mirror:
        capref.mirror((0, 0), (0, 1))
    capref.move((snap(X(plan.cap_cx)), snap(y0 + plan.cap_cy)))
    m4 = _ext(plan.unit, MET4)
    xa, xb = sorted((X(plan.cap_cx + plan.c1_x0), X(plan.cap_cx + m4[1])))
    _poly(top, xa, y0 + plan.cap_cy - STUB_W / 2, xb, y0 + plan.cap_cy + STUB_W / 2, MET4)
    px = sorted((X(plan.cap_cx + plan.cap_x0), X(plan.cap_cx + plan.cap_x1)))
    return px[0], px[1], y0 + plan.cap_cy + plan.cap_y0, y0 + plan.cap_cy + plan.cap_y1


def build_abut_test(design, rails, gate_maps, cols=3, rows=2, name="cdac_unit_2x3"):
    """rows x cols abutted cells (mirrored alternate columns) to prove the cell tiles DRC/LVS-clean.

    Every row gets its own control-rail names; supplies are tied below the block and the top-plate straps
    above it by a met4 bar, so the whole block is one LVS-checkable circuit."""
    from gdsfactory import Component
    plan = UnitCellPlan(design, len(rails[0]), len(rails[1]), _n_street(rails[0], gate_maps))
    W, H = plan.W, plan.H
    top = Component(name + "_hier")

    def rect(xa, ya, xb, yb, layer):
        _poly(top, xa, ya, xb, yb, layer)

    lines, all_rails = [], []
    k = 0
    for r in range(rows):
        ren = (lambda n: n) if rows == 1 else (lambda n, r=r: f"{n}_r{r}")
        row_rails = ([ren(n) for n in rails[0]], [ren(n) for n in rails[1]])
        all_rails += row_rails[0] + row_rails[1]
        for c in range(cols):
            g = {key: ren(v) for key, v in gate_maps[k % len(gate_maps)].items()}
            lines += draw_cell(top, plan, c * W, r * H, c % 2 == 1, row_rails, g, f"{r}_{c}", design)
            k += 1
        for net, y in zip(row_rails[0] + row_rails[1], plan.ctrl_y):
            _pin(top, net, W - 0.3, r * H + y, MET2, (0.3, CTRL_W))
    for net, (x, y) in _tie_supplies(rect, plan, cols, rows, -(max(plan.tap_half + R_M1_SP, STRAP_W / 2 + TRUNK_STRAP) + V1_M1[0] / 2)).items():
        _pin(top, net, x, y, MET2)
    _top_bar(rect, plan, cols)
    _pin(top, "top", 0.0, -TOP_BAR_GAP - STRAP_W / 2, MET4)
    top = top.flatten()
    top.name = name
    pins = ["top"] + SUPPLY + all_rails
    return top, plan, _subckt(name, pins, lines)


MAX_GROUPS = 3          # bit groups per row: 2 drive rails each, 6 drive rails = the 8-track unit cell


def rowwise_grid(bits):
    """Common-centroid assignment for the fixed unit cell: few bits per row (few control rails).

    Rows are taken in pairs (r, R-1-r); a unit at (r, c) pairs with (R-1-r, C-1-c), so every bit made of such
    point-symmetric pairs has its centroid exactly at the array centre.  The MSB (sampled on phis, the others
    on phig) fills the outer row pairs; the other bits are packed into the inner row pairs with at most
    MAX_GROUPS bits per row (the LSB and the termination unit share one pair).  Both orientations of the
    array are tried; if neither packs, rows may carry more bits (taller cells)."""
    from .cdac import array_shape
    R0, C0 = array_shape(bits)
    for R, C, k in ((R0, C0, MAX_GROUPS), (C0, R0, MAX_GROUPS), (R0, C0, None)):
        grid = _pack_grid(bits, R, C, k)
        if grid:
            return grid
    raise ValueError(f"no row-wise grid for {bits} bits")


def _pack_grid(bits, R, C, max_groups):
    from itertools import combinations
    msb = 2 ** (bits - 2)                                  # MSB point-symmetric pairs
    if R % 2 or msb % C:
        return None
    n_msb, n_bins = msb // C, R // 2 - msb // C
    sizes = {g: 2 ** (g - 1) for g in range(bits - 2, 0, -1)}
    sizes["L"] = 1                                          # LSB + termination unit
    k_max = max_groups or len(sizes)

    def fill(i, rem):
        if i == n_bins:
            return [] if not any(rem.values()) else None
        names = [g for g in rem if rem[g]]
        for n in range(1, k_max + 1):
            for combo in combinations(names, n):
                for split in combo:                         # one group may be split over rows
                    alloc = {g: rem[g] for g in combo if g != split}
                    need = C - sum(alloc.values())
                    if not 0 < need <= rem[split]:
                        continue
                    alloc[split] = need
                    rest = fill(i + 1, {g: rem[g] - alloc.get(g, 0) for g in rem})
                    if rest is not None:
                        return [alloc] + rest
        return None

    bins = fill(0, sizes)
    if bins is None:
        return None
    grid = [[None] * C for _ in range(R)]
    rows = [[(bits - 1, C)]] * n_msb + [sorted(b.items(), key=lambda t: -sizes[t[0]]) for b in bins]
    for r, row in enumerate(rows):
        j = 0
        for g, n in row:
            for _ in range(n):
                a, b = (0, "d") if g == "L" else (g, g)
                grid[r][j], grid[R - 1 - r][C - 1 - j] = a, b
                j += 1
    return grid


def unit_gates(g, bits):
    if g == "d":                        # termination unit: Vref driver held off, ground driver on phigb
        return dict(en="phig", enb="phigb", pg="vdd", ng="phigb")
    en, enb = ("phis", "phisb") if g == bits - 1 else ("phig", "phigb")
    return dict(en=en, enb=enb, pg=f"pg_{g}", ng=f"ng_{g}")


PHASES = ["phis", "phisb", "phig", "phigb"]
TRUNK_W, TRUNK_PITCH = 0.32, 0.50       # met1 control trunks beside the array (via1 pads fit inside)
ANT_DIFF, ANT_STAGGER = 0.42, 0.80       # antenna-diode diffusion; vertical offset of every other diode
LICON = (66, 44)
SUP_BAR_W, SUP_BAR_PITCH = 0.40, 0.80   # met2 supply bars below the array


def build_unit_array(design, bits, name=None, grid=None):
    """CDAC with per-unit switches: abutted unit cells (alternate columns mirrored) on the row-wise
    common-centroid grid.  Each row carries only its own rails: the sample phase pair below the devices,
    its bits' pg/ng above (unused tracks are tied to vss).  Rails run out to met1 trunks, phases on the
    left and bit controls on the right; the vertical supply lines are tied by met2 bars below the array
    and the top-plate straps by a met4 bar below it.  A ring of dummy unit caps (on vss) surrounds the array.
    Returns (Component, info, reference netlist)."""
    from gdsfactory import Component

    # the unit cap is the sized one (sizing.py: matching / kT/C / PDK minimum), as in the schematic
    grid = grid or rowwise_grid(bits)
    R, C = len(grid), len(grid[0])
    gates = [[unit_gates(g, bits) for g in row] for row in grid]
    bot_rows, top_rows = [], []
    for row in gates:                         # bottom to top: complements first, Msn's phase next to the devices
        bot_rows.append([n for n in ("phisb", "phigb", "phis", "phig") if any(n in (g["en"], g["enb"]) for g in row)])
        tops = dict.fromkeys(n for g in row for n in (g["ng"], g["pg"]) if n not in SUPPLY)
        top_rows.append(sorted(tops, key=lambda n: (n not in PHASES, n.split("_")[-1], n)))
    n_bot, n_top = max(map(len, bot_rows)), max(map(len, top_rows))
    n_street = max(_n_street(b, row) for b, row in zip(bot_rows, gates))
    plan = UnitCellPlan(design, n_bot, n_top, n_street)
    W, H = plan.W, plan.H
    Wa = C * W
    name = name or f"cdacu{bits}b"
    top = Component(name + "_hier")

    def rect(xa, ya, xb, yb, layer):
        _poly(top, xa, ya, xb, yb, layer)

    def via1(x, y):
        rect(x - V1_M1[0] / 2, y - V1_M1[1] / 2, x + V1_M1[0] / 2, y + V1_M1[1] / 2, MET1)
        rect(x - V1 / 2, y - V1 / 2, x + V1 / 2, y + V1 / 2, VIA1)
        rect(x - V1_M2[0] / 2, y - V1_M2[1] / 2, x + V1_M2[0] / 2, y + V1_M2[1] / 2, MET2)

    lines, rail_pos = [], []                      # rail_pos: (net, y) of every used rail
    for r in range(R):
        y0 = (R - 1 - r) * H
        bot = [None] * (n_bot - len(bot_rows[r])) + bot_rows[r]
        tops = top_rows[r] + [None] * (n_top - len(top_rows[r]))
        names = [n or f"_nc{r}_{i}" for i, n in enumerate(bot + tops)]
        for c in range(C):
            lines += draw_cell(top, plan, c * W, y0, c % 2 == 1, (names[:n_bot], names[n_bot:]), gates[r][c],
                               f"{r}_{c}", design)
        unused = []
        for n, y in zip(bot + tops, plan.ctrl_y):
            if n:
                rail_pos.append((n, y0 + y))
            else:                                 # unused track: tied to the vss line on the array edge
                unused.append(y0 + y)
                via1(0.0, y0 + y)
        if unused:                                # one met1 / met2 bar over the tie vias (pads too close otherwise)
            lo, hi = min(unused) - V1_M1[1] / 2, max(unused) + V1_M1[1] / 2
            rect(-V1_M2[0] / 2, min(unused) - V1_M2[1] / 2, V1_M2[0] / 2, max(unused) + V1_M2[1] / 2, MET2)
            for ty in [(rr * H + plan.ptap_y) for rr in range(R)]:       # p-taps (vss) on the same edge
                if ty - plan.tap_half - hi < R_M1_SP and lo - (ty + plan.tap_half) < R_M1_SP:   # near or overlapping
                    lo, hi = min(lo, ty), max(hi, ty)
            rect(-V1_M1[0] / 2, lo, V1_M1[0] / 2, hi, MET1)

    rail_pos += [("vin", (R - 1 - r) * H + plan.vin_y) for r in range(R)]
    # trunks (met1): vin and phases on the left, bit controls on the right
    nets = list(dict.fromkeys(n for n, _ in rail_pos))
    left = ["vin"] + [n for n in PHASES if n in nets]
    right = sorted((n for n in nets if n not in left), key=lambda n: (n.split("_")[-1], n))
    edge = W + 0.4 + TRUNK_W / 2                  # outside the dummy-cap columns (0.4: wide-met3 spacing to the
                                                  # channel pads on the trunks, m3.3d)
    tx = {n: snap(-edge - i * TRUNK_PITCH) for i, n in enumerate(left)}
    tx.update({n: snap(Wa + edge + i * TRUNK_PITCH) for i, n in enumerate(right)})
    for n, y in rail_pos:
        xa, xb = (tx[n], 0.0) if n in left else (Wa, tx[n])
        rect(xa - V1_M2[0] / 2, y - CTRL_W / 2, xb + V1_M2[0] / 2, y + CTRL_W / 2, MET2)
        via1(tx[n], y)
    for n in nets:
        ys = [y for m, y in rail_pos if m == n]
        lo, hi = min(ys) - V1_M1[1] / 2, max(ys) + V1_M1[1] / 2
        rect(tx[n] - TRUNK_W / 2, lo, tx[n] + TRUNK_W / 2, hi, MET1)
        _pin(top, n, tx[n], hi - 0.2, MET1, (0.14, 0.3))
    # antenna diodes: a bit-control rail reaches the SAR logic (a driver's diffusion) only through a met3 hop in the
    # core's channel, so while met1 / met2 are etched it hangs on a few switch gates (Magic antennacheck: met2 ratio
    # > 400 at 6 and 8 bit). An n+ diffusion under each control trunk discharges it from met1 on. One row above the
    # highest rail, staggered by trunk parity (diffusion spacing), under one shared n+ implant.
    if right:
        y_d = snap(max(y for _, y in rail_pos) + V1_M1[1] / 2 + 0.55)
        for k, n in enumerate(right):
            x, yd = tx[n], y_d + (k % 2) * ANT_STAGGER
            rect(x - TRUNK_W / 2, max(y for m, y in rail_pos if m == n), x + TRUNK_W / 2, yd + 0.2, MET1)
            for lay, w in ((DIFF, ANT_DIFF), (LICON, 0.17), (LI, 0.33), (MCON, 0.17)):
                rect(x - w / 2, yd - w / 2, x + w / 2, yd + w / 2, lay)
        xs_r = [tx[n] for n in right]
        e = ANT_DIFF / 2 + 0.125
        rect(min(xs_r) - e, y_d - e, max(xs_r) + e, y_d + ANT_STAGGER + e, NSDM)
    # dummy-cap ring: one ring of unit-cell-pitch MIM caps (plates shorted, on vss) around the array, mirrored
    # like the real columns, so every real unit sees real-unit neighbours (edge etch / density) on all sides
    side = design["cu"]["side"]
    ring = [(r, c) for r in (-1, R) for c in range(-1, C + 1)] + [(r, c) for r in range(R) for c in (-1, C)]
    plates = {}
    for k, (r, c) in enumerate(ring):
        plates[(r, c)] = _draw_dummy(top, plan, c * W, (R - 1 - r) * H, c % 2 == 1)
        lines.append(f"XCD_{k} vss vss sky130_fd_pr__cap_mim_m3_1 W={side} L={side} MF=1")
    # met3 ring through the dummy plates: each gap filled along the whole facing edge (a narrow link would leave
    # notches, and plates over 3 um count as wide met3 whose notches need 0.4 um, m3.3c/d)
    for (r, c), (x0_, x1_, y0_, y1_) in plates.items():
        if (r, c + 1) in plates and r in (-1, R):
            n = plates[(r, c + 1)]
            rect(x1_ - 0.1, max(y0_, n[2]), n[0] + 0.1, min(y1_, n[3]), MET3)
        if (r + 1, c) in plates and c in (-1, C):
            n = plates[(r + 1, c)]
            rect(max(x0_, n[0]), n[3] - 0.1, min(x1_, n[1]), y0_ + 0.1, MET3)
    # vertical supply lines -> met2 bars below the dummy row; the dummy ring drops onto the vss bar
    yb0 = -H - 0.6
    for i, net in enumerate(LINES):
        yb = yb0 - i * SUP_BAR_PITCH
        xs = sorted({snap(c * W + (W - plan.sup_x[net] if c % 2 else plan.sup_x[net])) for c in range(C)})
        for x in xs:
            rect(x - M1_LINE / 2, yb, x + M1_LINE / 2, 0, MET1)
            via1(x, yb)
        if net == "vss":
            x0_, x1_, y0_, y1_ = plates[(R, -1)]
            xd = snap((x0_ + x1_) / 2)
            rect(xd - M3_PAD / 2, yb - M3_PAD / 2, xd + M3_PAD / 2, y0_ + 0.1, MET3)
            rect(xd - M2_PAD / 2, yb - M2_PAD / 2, xd + M2_PAD / 2, yb + M2_PAD / 2, MET2)
            rect(xd - VIA / 2, yb - VIA / 2, xd + VIA / 2, yb + VIA / 2, VIA2)
            xs = [xd] + xs
        rect(xs[0] - V1_M2[0] / 2, yb - SUP_BAR_W / 2, xs[-1] + V1_M2[0] / 2, yb + SUP_BAR_W / 2, MET2)
        _pin(top, net, xs[0] + 0.2, yb, MET2)
    _top_bar(rect, plan, C, y_top=-H)
    _pin(top, "top", 0.0, -H - TOP_BAR_GAP - STRAP_W / 2, MET4)

    top = top.flatten()
    top.name = name
    pins = ["top"] + LINES + left + right
    bb = top.bbox
    info = dict(bits=bits, grid=grid, cell=(W, H), rails_bot=bot_rows, rails_top=top_rows, dummies=len(ring),
                ctrl_rails=n_bot + n_top, width=float(bb[1][0] - bb[0][0]), height=float(bb[1][1] - bb[0][1]),
                pins=pins)
    return top, info, _subckt(name, pins, lines)
