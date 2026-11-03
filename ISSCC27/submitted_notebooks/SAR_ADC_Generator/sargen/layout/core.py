"""SAR ADC core: the verified blocks (CDAC, comparator, top-plate switch, SAR logic) placed and routed.

    [CDAC (unit cells + dummy ring)]      ->  pg / ng channel  ->  [SAR logic (LibreLane)]
       top-plate met4 bar (bottom)
       | met4 spine                          (analog on the west, logic on the east)
    [top switch] - [comparator]
    ------------------------------------- met3 signal buses: qp, clk, vcm, phisb, phig
    ------------------------------------- met4 power buses: vss, vdd

The top-plate net is met4 only: the CDAC bar, a short spine down to the comparator input and a stub into the
top-plate switch, so it never runs along a dynamic line (the qp riser crosses the comparator's input lead
once, ~0.04 um^2).  Everything is placed from the blocks' own pin labels.
"""

from pathlib import Path

from .cdac import M2_PAD, M3_PAD, MET2, MET3, MET4, VIA, VIA2, snap
from .cell import MET1, VIA1, V1
from .unitcell import V1_M1, V1_M2, _pin, _poly

VIA3 = (70, 44)
M3_W, M4_W, M2_W = 0.30, 0.60, 0.20
BUS_P = 0.80                     # met3 / met4 bus pitch
PWR_W = 0.80
EXIT = 0.8                       # block pins leave their cells this far (strongarm.EXIT, topswitch.EXIT)


def _labels(gds):
    import gdstk
    c = gdstk.read_gds(str(gds)).top_level()[0]
    out = {}
    for l in c.labels:
        out.setdefault(l.text, (l.layer, l.origin[0], l.origin[1]))
    (x0, y0), (x1, y1) = c.bounding_box()
    return c.name, out, (x0, y0, x1, y1)


class Core:
    def __init__(self, name):
        from gdsfactory import Component
        self.c = Component(name)
        self.pins = {}

    def rect(self, xa, ya, xb, yb, lay):
        _poly(self.c, xa, ya, xb, yb, lay)

    def place(self, gds, dx, dy, mirror=False):
        import gdsfactory as gf
        name, pins, bb = _labels(gds)
        ref = self.c << gf.import_gds(gds, cellname=name)
        if mirror:
            ref.mirror((0, 0), (0, 1))
        ref.move((snap(dx), snap(dy)))
        sx = -1 if mirror else 1
        P = {k: (lay, snap(dx + sx * x), snap(dy + y)) for k, (lay, x, y) in pins.items()}
        xs = sorted((dx + sx * bb[0], dx + sx * bb[2]))
        return P, (xs[0], dy + bb[1], xs[1], dy + bb[3])

    # ---- wiring
    def via(self, x, y, lo, hi):
        """Via stack between metal levels lo..hi (1 = met1 ... 4 = met4) at (x, y)."""
        pads = {1: (MET1, max(V1_M1)), 2: (MET2, M2_PAD), 3: (MET3, 0.50), 4: (MET4, 0.60)}
        cuts = {1: (VIA1, V1), 2: (VIA2, VIA), 3: (VIA3, 0.20)}
        for k in range(lo, hi + 1):
            lay, w = pads[k]
            self.rect(x - w / 2, y - w / 2, x + w / 2, y + w / 2, lay)
        for k in range(lo, hi):
            lay, w = cuts[k]
            self.rect(x - w / 2, y - w / 2, x + w / 2, y + w / 2, lay)

    def h(self, y, xa, xb, lay, w):
        self.rect(min(xa, xb) - w / 2, y - w / 2, max(xa, xb) + w / 2, y + w / 2, lay)

    def v(self, x, ya, yb, lay, w):
        self.rect(x - w / 2, min(ya, yb) - w / 2, x + w / 2, max(ya, yb) + w / 2, lay)

    def pin(self, net, x, y, lay):
        _pin(self.c, net, x, y, lay)
        self.pins[net] = (lay, x, y)


def build_core(bits, layout_dir, name=None):
    """Assemble the core from build/<N>bit/layout/{cdacu<N>b,strongarm,topsw,sar_logic}.gds.
    Returns (Component, info)."""
    L = Path(layout_dir)
    name = name or f"sar{bits}b_core"
    K = Core(name)
    # ---------------------------------------------------------------- placement
    cd, cbb = K.place(L / f"cdacu{bits}b.gds", 0.0, 0.0)
    top_y = cd["top"][2]                                       # CDAC top-plate bar (met4)
    bar_lo = top_y - 0.2
    _, sa_pins, sa_bb = _labels(L / "strongarm.gds")
    # spine near the bar's left end, far enough east that the top switch and its west supply drops clear the
    # CDAC's west trunks (phisb / phig run down from them to the buses)
    _, ts_pins, ts_bb = _labels(L / "topsw.gds")
    x_trunks = max(cd[n][1] for n in ("vin", "phis", "phisb", "phig", "phigb"))
    x_spine = snap(max(cd["top"][1] + 0.4, x_trunks + 0.16 + 0.5 + 1.4 + 0.5 + (ts_bb[2] - ts_bb[0]) + 0.8))
    # comparator below the CDAC, its inp exit just right of the spine
    sx_c = x_spine + 1.0 - sa_bb[0]
    sy_c = cbb[1] - 0.6 - sa_bb[3]
    cm, cmb = K.place(L / "strongarm.gds", sx_c, sy_c)
    # top-plate switch left of the spine, its met4 top pad at the comparator input height
    sx_t = x_spine - 0.8 - ts_bb[2]
    sy_t = cm["inp"][2] - ts_pins["top"][2]
    ts, tsb = K.place(L / "topsw.gds", sx_t, sy_t)
    # SAR logic east of the CDAC, beyond the pg / ng channel
    n_ch = 2 * bits
    x_ch0 = cbb[2] + 0.6                                      # first channel column
    lg_x = snap(x_ch0 + n_ch * 0.6 + 0.6)
    lg, lgb = K.place(L / "sar_logic.gds", lg_x, cbb[1])
    # ---------------------------------------------------------------- top plate (met4 only)
    y_in = cm["inp"][2]
    K.v(x_spine, bar_lo + 0.2, y_in, MET4, M4_W)
    K.h(y_in, x_spine, cm["inp"][1], MET2, 0.14)               # comparator input lead to the spine
    K.via(x_spine, y_in, 2, 4)
    K.h(ts["top"][2], ts["top"][1], x_spine, MET4, M4_W)        # stub into the top-plate switch
    # ---------------------------------------------------------------- pg / ng: logic west pins -> CDAC trunks
    import gdstk
    cdc = gdstk.read_gds(str(L / f"cdacu{bits}b.gds")).top_level()[0]
    m1 = [p.bounding_box() for p in cdc.polygons if (p.layer, p.datatype) == (68, 20)]
    m2 = [p.bounding_box() for p in cdc.polygons if (p.layer, p.datatype) == (69, 20)]
    used_y = []
    nets = [f"{p}_{i}" for i in range(bits) for p in ("ng", "pg")]
    for k, net in enumerate(sorted(nets, key=lambda n: lg[n][2])):
        _, xt, yt_lbl = cd[net]                                # trunk x (label on the trunk)
        _, xp, yp = lg[net]
        rails = [(b[0][1] + b[1][1]) / 2 for b in m2 if b[0][0] - 0.2 <= xt <= b[1][0] + 0.2 and b[1][1] - b[0][1] < 0.4]
        # a via spot on the trunk clear of the met2 rails crossing it and of the other nets' wires
        cands = [round(yt_lbl + s * 0.05, 3) for s in range(-400, 401)]
        ok = [y for y in cands if all(abs(y - r) >= 0.46 for r in rails) and all(abs(y - u) >= 0.8 for u in used_y)
              and all(abs(y - lg[n][2]) >= 0.8 for n in nets if n != net)
              and (abs(y - yp) < 1e-6 or abs(y - yp) >= 0.8)]          # channel vias coincide or stand apart
        yv = min(ok, key=lambda y: abs(y - yp))
        used_y.append(yv)
        tr = [b for b in m1 if b[0][0] - 0.01 <= xt <= b[1][0] + 0.01]
        lo = min([yv] + [b[0][1] for b in tr]); hi = max([yv] + [b[1][1] for b in tr])
        K.rect(xt - 0.16, lo, xt + 0.16, hi, MET1)             # trunk (met1) reaches the via spot
        K.via(xt, yv, 1, 3)
        xc = x_ch0 + k * 0.6                                   # channel column (met2)
        K.h(yv, xt, xc, MET3, M3_W)
        K.via(xc, yv, 2, 3)
        if abs(yv - yp) > 1e-6:
            K.v(xc, yv, yp, MET2, M2_W)
            K.via(xc, yp, 2, 3)
        K.h(yp, xc, xp, MET3, M3_W)
    # ---------------------------------------------------------------- signal buses (met3) below everything
    y_b = min(cmb[1], tsb[1]) - 1.0
    bus = {n: y_b - i * BUS_P for i, n in enumerate(["qp", "clk", "vcm", "phisb", "phig"])}
    xl = tsb[0] - 1.0                                          # west column for vcm / phases
    # qp: comparator left exit -> met3 riser down (crosses the input lead once) -> bus -> logic south pin
    _, xq, yq = cm["qp"]
    K.via(xq, yq, 2, 3)
    K.v(xq, yq, bus["qp"], MET3, M3_W)
    # clk: comparator left exit -> met2 down -> bus
    _, xk, yk = cm["clk"]
    K.v(xk - 0.3, yk, bus["clk"], MET2, M2_W)
    K.h(yk, xk - 0.3, xk, MET2, M2_W)
    K.via(xk - 0.3, bus["clk"], 2, 3)
    for net in ("qp", "clk"):
        x_src = xq if net == "qp" else xk - 0.3
        _, xp, yp = lg[net]
        K.h(bus[net], x_src, xp, MET3, M3_W)
        K.via(xp, bus[net], 2, 3)
        K.v(xp, bus[net], yp, MET2, M2_W)
    # vcm: top-switch west exit -> west column -> bus -> up to the comparator's east inn exit
    _, xv, yv = ts["vcm"]
    K.h(yv, xv, xl, MET2, M2_W)
    K.v(xl, yv, bus["vcm"], MET2, M2_W)
    K.via(xl, bus["vcm"], 2, 3)
    _, xi, yi = cm["inn"]
    x_e = cmb[2] + 0.8
    K.h(bus["vcm"], xl, x_e, MET3, M3_W)
    K.via(x_e, bus["vcm"], 2, 3)
    K.v(x_e, bus["vcm"], yi, MET2, M2_W)
    K.h(yi, xi, x_e, MET2, M2_W)
    K.pin("vcm", xl, bus["vcm"], MET3)
    # phisb / phig: logic south pins -> buses -> CDAC west trunks (met1 extended down)
    for i, net in enumerate(("phisb", "phig")):
        _, xp, yp = lg[net]
        K.v(xp, yp, bus[net], MET2, M2_W)
        K.via(xp, bus[net], 2, 3)
        _, xt, _ = cd[net]
        tr = [b for b in m1 if b[0][0] - 0.01 <= xt <= b[1][0] + 0.01]
        K.rect(xt - 0.16, bus[net], xt + 0.16, max(b[1][1] for b in tr), MET1)
        K.via(xt, bus[net], 1, 3)
        K.h(bus[net], xt, xp, MET3, M3_W)
    # ---------------------------------------------------------------- power (met4 buses + met4 drops)
    y_vss = bus["phig"] - 2.0                                  # vdd's met3 hop stays clear of the last bus
    y_vdd = y_vss - 1.4
    drops = {"vss": [], "vdd": []}

    def drop(net, x, y):                                       # met4 down to the bus; vdd changes to met3
        if net == "vss":                                       # above the vss bus and ends on its met3 bus
            K.v(x, y, y_vss, MET4, M4_W)
        else:
            K.v(x, y, y_vss + 1.1, MET4, M4_W)
            K.via(x, y_vss + 1.1, 3, 4)
            K.v(x, y_vss + 1.1, y_vdd, MET3, M4_W)
            K.via(x, y_vdd, 3, 3)
        drops[net].append(x)

    # comparator rails leave east, the top switch's west (its east side has the top-plate stub and spine)
    for blk, bb_, sgn in ((cm, sa_bb, 1), (ts, ts_bb, -1)):
        rail_end = blk["vss"][1] + sgn * ((bb_[2] - bb_[0]) / 2 - EXIT)   # rails end where the met2 exits start
        for net, dxo in (("vss", 0.5), ("vdd", 1.4)):          # rails extended out of the cell (met1)
            _, x, y = blk[net]
            xd = rail_end + sgn * dxo
            K.rect(min(rail_end - sgn * 0.2, xd + sgn * 0.35), y - 0.24, max(rail_end - sgn * 0.2, xd + sgn * 0.35),
                   y + 0.24, MET1)
            K.via(xd, y, 1, 4)
            drop(net, xd, y)
    for net, yb_lbl, xe in (("vss", cd["vss"][2], cbb[2] - 1.0), ("vdd", cd["vdd"][2], cbb[2] - 2.0)):
        # CDAC bars extended east past the top-plate bar, one drop per net
        K.h(yb_lbl, cd[net][1], xe, MET2, 0.40)
        K.via(xe, yb_lbl, 2, 4)
        drop(net, xe, yb_lbl)
    for net, lbl in (("vss", "VGND"), ("vdd", "VPWR")):         # logic power straps (met4)
        _, x, y = lg[lbl]
        K.v(x, lgb[1] + 3.0, lgb[1] - 0.4, MET4, 1.6)                # overlaps the strap (it starts ~2.5 um up)
        drop(net, x, lgb[1] - 0.4)
    x0 = min(min(v) for v in drops.values()) - 0.6
    x1 = max(max(v) for v in drops.values()) + 0.6
    K.h(y_vss, x0, x1, MET4, PWR_W)
    K.h(y_vdd, x0, x1, MET3, PWR_W)
    K.pin("vss", x0 + 0.3, y_vss, MET4)
    K.pin("vdd", x0 + 0.3, y_vdd, MET3)
    # ---------------------------------------------------------------- core pins on the blocks
    for net in ("vin", "phis", "phigb"):
        K.pin(net, *cd[net][1:], (MET1))
    K.pin("phisb", *cd["phisb"][1:], MET1)
    K.pin("phig", *cd["phig"][1:], MET1)
    K.pin("vref", *cd["vref"][1:], MET2)
    for net in ("phit", "phitb"):
        K.pin(net, *ts[net][1:], MET2)
    for net in ["clkt", "en"] + [f"trial_{i}" for i in range(bits)] + [f"latch_{i}" for i in range(bits)] + \
               [f"bo_{i}" for i in range(bits)]:
        K.pin(net, *lg[net][1:], {69: MET2, 70: MET3}[lg[net][0]])
    bb = K.c.bbox
    info = dict(width=float(bb[1][0] - bb[0][0]), height=float(bb[1][1] - bb[0][1]))
    return K.c, info


def core_pins(bits):
    return (["vin", "vref", "vcm", "vdd", "vss", "phis", "phisb", "phig", "phigb", "phit", "phitb", "clkt", "en"]
            + [f"trial_{i}" for i in range(bits)] + [f"latch_{i}" for i in range(bits)]
            + [f"bo_{i}" for i in range(bits)])


def extracted(bits, layout_dir):
    """evaluate() keyword for the extracted core (flat Magic PEX, ports from the pin labels), or None."""
    from .. import netlist as nl
    name = f"sar{bits}b_core"
    pex = Path(layout_dir) / "pex" / f"{name}_pex.spice"
    if not pex.exists():
        return None
    pins = core_pins(bits)
    return dict(core=(nl.wrap_extraction(pex, name, pins), pins, name))


def reference(bits, layout_dir, name=None):
    """LVS reference: the blocks' references and the core netlist that connects them."""
    L = Path(layout_dir)
    name = name or f"sar{bits}b_core"
    parts = [(L / f"cdacu{bits}b_ref.spice").read_text(), (L / "strongarm_ref.spice").read_text(),
             (L / "topsw_ref.spice").read_text(), (L / "sar_logic_ref.spice").read_text()]
    import re
    cpins = re.search(rf"^\.subckt cdacu{bits}b (.*)$", parts[0], re.M).group(1).split()
    lpins = re.search(r"^\.subckt sar_logic (.*)$", parts[3], re.M).group(1).split()
    conn = {"VPWR": "vdd", "VGND": "vss"}
    lines = [f".subckt {name} {' '.join(core_pins(bits))}",
             f"xcdac {' '.join(cpins)} cdacu{bits}b",
             "xcmp top vcm clk qp qn vdd vss strongarm",
             "xtsw top vcm phit phitb vdd vss topsw",
             f"xlog {' '.join(conn.get(p, p) for p in lpins)} sar_logic",
             f".ends {name}"]
    return "\n".join(parts + lines) + "\n"
