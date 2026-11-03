"""Two-row analog cell generator with a deterministic channel router (gLayout devices, SKY130).

Floorplan, bottom to top:
    channel A  - NMOS gate and body (vss) connections
    NMOS row   - gLayout nfets, source/drain bars facing up
    channel Bn - NMOS source/drain connections
    channel Bp - PMOS source/drain connections (separate, so stubs of the two rows never overlap)
    PMOS row   - gLayout pfets rotated by 180 degrees (source/drain facing down)
    channel C  - PMOS gate and body (vdd) connections
Every terminal drops a met3 stub (via1 + via2 stack) to the met2 track of its net in the adjacent channel;
every net has its own track, so routing cannot short by construction.  Nets that appear in several channels
are joined by met3 trunks to the left of the rows.  Both rows are placed mirror-symmetrically by the caller.

Layer note: gLayout names metals one level higher than SKY130 (it counts li1 as met1); this module uses
SKY130 GDS numbers directly.
"""

from dataclasses import dataclass, field

from .cdac import M2_PAD, M3_PAD, PIN, LBL, MET2, MET3, VIA, VIA2, snap

MET1 = (68, 20)
VIA1 = (68, 44)
NWELL = (64, 20)
LVTN = (125, 44)
DIFF = (65, 20)
V1 = 0.15                 # via1 size
M1_PAD_X, M1_PAD_Y = V1 + 2 * 0.085, V1 + 2 * 0.06      # 0.32 x 0.27 fits the 0.29 um source/drain bars
M2_PAD1 = V1 + 2 * 0.085                                 # met2 around via1 (0.32)
TRACK_W = 0.30
TRACK_PITCH = 0.75
STUB_W = 0.36
ROW_GAP = 0.45            # gap between device tap rings in a row
CH_EDGE = 0.75            # channel edge clearance to a row
TRUNK_W = 0.50
TRUNK_PITCH = 1.10


@dataclass
class Dev:
    name: str
    kind: str             # "n" or "p"
    w: float              # total width [um]
    l: float
    d: str
    g: str
    s: str
    fingers: int = 0      # 0 = auto: 2 fingers if each can be >= 0.42 um wide, else 1
    flavor: str = "std"   # "std" or "lvt"
    tie: bool = True      # gLayout tap ring around the device (False: caller provides shared taps)
    ref: object = field(default=None, repr=False)


def model_name(dv):
    from ..pdk import TG_FLAVORS, NFET, PFET
    if dv.flavor == "lvt":
        nm, _, pm, _ = TG_FLAVORS["lvt"]
        return nm if dv.kind == "n" else pm
    return NFET if dv.kind == "n" else PFET


def reference_netlist(name, nrow, prow, pins, body=("vss", "vdd")):
    """LVS reference written from the same device list that was drawn."""
    from ..pdk import mos
    lines = [f".subckt {name} {' '.join(pins)}"]
    for dv in nrow + prow:
        b = body[0] if dv.kind == "n" else body[1]
        lines.append(mos(dv.name, dv.d, dv.g, dv.s, b, model_name(dv), dv.w, dv.l))
    lines.append(f".ends {name}")
    return "\n".join(lines) + "\n"


def _make_device(dv):
    from glayout import nmos, pmos, sky130
    fn = nmos if dv.kind == "n" else pmos
    kw = dict(with_dnwell=False) if dv.kind == "n" else {}
    if not dv.fingers:
        dv.fingers = 2 if dv.w / 2 >= 0.42 else 1
    comp = fn(sky130, width=snap(dv.w / dv.fingers), length=dv.l, fingers=dv.fingers, with_dummy=False,
              with_tie=dv.tie, with_substrate_tap=False, sd_route_topmet="met2", gate_route_topmet="met2", **kw)
    if dv.flavor == "lvt":
        # magic types a transistor inside the cell that holds its diffusion/poly, so the lvtn implant must be
        # in that same cell: flatten the device and add lvtn over its diffusion (+0.18 um enclosure)
        from gdsfactory.components import rectangle
        comp = comp.flatten()
        xs, ys = [], []
        for poly in comp.get_polygons(by_spec=DIFF):
            xs += [pt[0] for pt in poly]
            ys += [pt[1] for pt in poly]
        x0, y0, x1, y1 = min(xs) - 0.18, min(ys) - 0.18, max(xs) + 0.18, max(ys) + 0.18
        r = comp << rectangle(size=(snap(x1 - x0), snap(y1 - y0)), layer=LVTN)
        r.move((snap(x0), snap(y0)))
        comp = comp.flatten()
        comp.name = f"{dv.name}_lvt"
    return comp


def build_cell(name, nrow, prow, pins, body=("vss", "vdd")):
    """nrow/prow: lists of Dev (left to right).  pins: nets that get pin labels.  Returns (Component, info)."""
    from gdsfactory import Component
    from gdsfactory.components import rectangle

    top = Component(name)

    def rect(x0, y0, x1, y1, layer):
        x0, y0, x1, y1 = (snap(v) for v in (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)))
        if x1 - x0 <= 0 or y1 - y0 <= 0:
            return None
        r = top << rectangle(size=(snap(x1 - x0), snap(y1 - y0)), layer=layer)
        r.move((x0, y0))
        return r

    def via12(x, y):          # met1 bar -> met3 stub
        rect(x - M1_PAD_X / 2, y - M1_PAD_Y / 2, x + M1_PAD_X / 2, y + M1_PAD_Y / 2, MET1)
        rect(x - V1 / 2, y - V1 / 2, x + V1 / 2, y + V1 / 2, VIA1)
        m2 = max(M2_PAD1, M2_PAD)
        rect(x - m2 / 2, y - m2 / 2, x + m2 / 2, y + m2 / 2, MET2)
        rect(x - VIA / 2, y - VIA / 2, x + VIA / 2, y + VIA / 2, VIA2)
        rect(x - M3_PAD / 2, y - M3_PAD / 2, x + M3_PAD / 2, y + M3_PAD / 2, MET3)

    def via2(x, y):           # met2 track <-> met3 stub / trunk
        rect(x - M2_PAD / 2, y - M2_PAD / 2, x + M2_PAD / 2, y + M2_PAD / 2, MET2)
        rect(x - VIA / 2, y - VIA / 2, x + VIA / 2, y + VIA / 2, VIA2)
        rect(x - M3_PAD / 2, y - M3_PAD / 2, x + M3_PAD / 2, y + M3_PAD / 2, MET3)

    # ---- devices and rows
    comps = {dv.name: _make_device(dv) for dv in nrow + prow}
    widths = {k: c.bbox[1][0] - c.bbox[0][0] for k, c in comps.items()}
    heights = {k: c.bbox[1][1] - c.bbox[0][1] for k, c in comps.items()}

    def row_width(row):
        return sum(widths[d.name] for d in row) + ROW_GAP * (len(row) - 1)

    W = max(row_width(nrow), row_width(prow))
    hn = max(heights[d.name] for d in nrow)
    hp = max(heights[d.name] for d in prow)

    # terminal list: (channel, x, y, net)
    terms = []

    def place(row, yc, rotate):
        x = -row_width(row) / 2
        for dv in row:
            ref = top << comps[dv.name]
            if rotate:
                ref.rotate(180)
            ref.move((snap(x + widths[dv.name] / 2), snap(yc)))
            dv.ref = ref
            x += widths[dv.name] + ROW_GAP
            p = ref.ports
            sx = sorted([p["multiplier_0_source_W"].center[0], p["multiplier_0_source_E"].center[0]])
            dxs = sorted([p["multiplier_0_drain_W"].center[0], p["multiplier_0_drain_E"].center[0]])
            gx = sorted([p["multiplier_0_gate_W"].center[0], p["multiplier_0_gate_E"].center[0]])
            ys, yd, yg = p["multiplier_0_source_W"].center[1], p["multiplier_0_drain_W"].center[1], p["multiplier_0_gate_W"].center[1]
            sd_ch, g_ch = ("Bn", "A") if dv.kind == "n" else ("Bp", "C")
            # source stub at the left end of its bar, drain stub at the right end; short (single-finger)
            # bars are extended in met1 (the tap ring sides are li1) so the two stubs stay >= 1 um apart
            xc = ref.center[0]
            if sx[0] > xc - 0.9:
                rect(xc - 0.9, ys - 0.145, sx[0] + 0.1, ys + 0.145, MET1)
                sx[0] = xc - 0.9
            if dxs[1] < xc + 0.9:
                rect(dxs[1] - 0.1, yd - 0.145, xc + 0.9, yd + 0.145, MET1)
                dxs[1] = xc + 0.9
            terms.append((sd_ch, snap(sx[0] + M1_PAD_X / 2 + 0.02), ys, dv.s, dv.name))
            terms.append((sd_ch, snap(dxs[1] - M1_PAD_X / 2 - 0.02), yd, dv.d, dv.name))
            terms.append((g_ch, snap((gx[0] + gx[1]) / 2), yg, dv.g, dv.name))
            # body: tap ring bar on the side facing the gate channel
            tie = p["tie_S_top_met_S"] if dv.kind == "n" else p["tie_S_top_met_S"]
            tx = snap(tie.center[0] + 1.0)
            ty = tie.center[1] + (0.205 if dv.kind == "n" else -0.205)
            terms.append((g_ch, tx, ty, body[0] if dv.kind == "n" else body[1], dv.name))

    # channel nets decide channel heights
    chan_nets = {"A": [], "Bn": [], "Bp": [], "C": []}
    for dv in nrow:
        for ch, n in (("Bn", dv.s), ("Bn", dv.d), ("A", dv.g), ("A", body[0])):
            if n not in chan_nets[ch]:
                chan_nets[ch].append(n)
    for dv in prow:
        for ch, n in (("Bp", dv.s), ("Bp", dv.d), ("C", dv.g), ("C", body[1])):
            if n not in chan_nets[ch]:
                chan_nets[ch].append(n)
    ch_h = {k: 2 * CH_EDGE + max(len(v) - 1, 0) * TRACK_PITCH + TRACK_W for k, v in chan_nets.items()}

    y_n = 0.0
    y_b_lo = y_n + hn / 2
    y_p = y_b_lo + ch_h["Bn"] + ch_h["Bp"] + hp / 2
    place(nrow, y_n, rotate=False)
    place(prow, y_p, rotate=True)
    # merged n-well over the PMOS row (all at vdd)
    rect(-W / 2 - 0.4, y_p - hp / 2 + 0.25, W / 2 + 0.4, y_p + hp / 2 - 0.25, NWELL)

    # track y positions
    track_y = {}
    ya_hi = y_n - hn / 2 - CH_EDGE
    for i, n in enumerate(chan_nets["A"]):
        track_y[("A", n)] = snap(ya_hi - TRACK_W / 2 - i * TRACK_PITCH)
    ybn_lo = y_b_lo + CH_EDGE                       # NMOS stubs come up from below
    for i, n in enumerate(chan_nets["Bn"]):
        track_y[("Bn", n)] = snap(ybn_lo + TRACK_W / 2 + i * TRACK_PITCH)
    ybp_hi = y_p - hp / 2 - CH_EDGE                 # PMOS stubs come down from above
    for i, n in enumerate(chan_nets["Bp"]):
        track_y[("Bp", n)] = snap(ybp_hi - TRACK_W / 2 - i * TRACK_PITCH)
    yc_lo = y_p + hp / 2 + CH_EDGE
    for i, n in enumerate(chan_nets["C"]):
        track_y[("C", n)] = snap(yc_lo + TRACK_W / 2 + i * TRACK_PITCH)

    # stubs
    span = {}
    for ch, x, y, net, _ in terms:
        yt = track_y[(ch, net)]
        via12(x, y)
        rect(x - STUB_W / 2, min(y, yt), x + STUB_W / 2, max(y, yt), MET3)
        via2(x, yt)
        lo, hi = span.get((ch, net), (x, x))
        span[(ch, net)] = (min(lo, x), max(hi, x))

    # nets in several channels -> trunks on the left
    multi = [n for n in dict.fromkeys(chan_nets["A"] + chan_nets["Bn"] + chan_nets["Bp"] + chan_nets["C"])
             if sum(n in v for v in chan_nets.values()) > 1 or n in pins]
    x_left = -W / 2 - 1.2
    trunk_x = {n: snap(x_left - i * TRUNK_PITCH) for i, n in enumerate(multi)}
    for (ch, net), (lo, hi) in span.items():
        if net in trunk_x:
            lo = trunk_x[net]
        yt = track_y[(ch, net)]
        rect(lo - M2_PAD / 2, yt - TRACK_W / 2, hi + M2_PAD / 2, yt + TRACK_W / 2, MET2)
    for net, xt in trunk_x.items():
        ys = [track_y[(ch, net)] for ch in ("A", "Bn", "Bp", "C") if (ch, net) in track_y]
        for yt in ys:
            via2(xt, yt)
        y0, y1 = min(ys) - M3_PAD / 2, max(ys) + M3_PAD / 2
        y1 = max(y1, y0 + 1.0)            # m3.6: met3 area >= 0.24 um^2 even for single-channel pins
        rect(xt - TRUNK_W / 2, y0, xt + TRUNK_W / 2, y1, MET3)
        if net in pins:
            rect(xt - TRUNK_W / 2, y1 - 0.5, xt + TRUNK_W / 2, y1, PIN[MET3])
            top.add_label(text=net, position=(xt, snap(y1 - 0.25)), layer=LBL[MET3])

    bb = top.bbox
    info = dict(name=name, width=float(bb[1][0] - bb[0][0]), height=float(bb[1][1] - bb[0][1]),
                channels={k: v for k, v in chan_nets.items()}, devices=[d.name for d in nrow + prow])
    return top, info


def strongarm_devices(c):
    """Mirror-symmetric StrongARM placement (sizes from design['cmp'])."""
    L, Lin = c["l"], c["l_in"]
    nrow = [Dev("Mon1", "n", c["w_inv_n"], L, "qp", "outp", "vss"),
            Dev("Mn1", "n", c["w_ln"], L, "outn", "outp", "xp"),
            Dev("Mi1", "n", c["w_in"], Lin, "xp", "inp", "tail"),
            Dev("Mt", "n", c["w_tail"], L, "tail", "clk", "vss"),
            Dev("Mi2", "n", c["w_in"], Lin, "xn", "inn", "tail"),
            Dev("Mn2", "n", c["w_ln"], L, "outp", "outn", "xn"),
            Dev("Mon2", "n", c["w_inv_n"], L, "qn", "outn", "vss")]
    prow = [Dev("Mop1", "p", c["w_inv_p"], L, "qp", "outp", "vdd"),
            Dev("Mr3", "p", c["w_rst"], L, "xp", "clk", "vdd"),
            Dev("Mr1", "p", c["w_rst"], L, "outn", "clk", "vdd"),
            Dev("Mp1", "p", c["w_lp"], L, "outn", "outp", "vdd"),
            Dev("Mp2", "p", c["w_lp"], L, "outp", "outn", "vdd"),
            Dev("Mr2", "p", c["w_rst"], L, "outp", "clk", "vdd"),
            Dev("Mr4", "p", c["w_rst"], L, "xn", "clk", "vdd"),
            Dev("Mop2", "p", c["w_inv_p"], L, "qn", "outn", "vdd")]
    return nrow, prow


STRONGARM_PINS = ["inp", "inn", "clk", "qp", "qn", "vdd", "vss"]


def switch_devices(design, bits):
    """Bottom-plate switches of every bit (LVT input TG + binary-scaled Vref/GND drivers), the termination-cap
    switches and the top-plate TG.  Bit i uses 2^i times the unit sizes; MSB samples on phis, others on phig."""
    sw, drv, fl = design["sw"], design["drv"], design["sw"].get("flavor", "std")
    from ..pdk import TG_FLAVORS
    ln, lp = TG_FLAVORS[fl][1], TG_FLAVORS[fl][3]
    L = 0.15
    nrow, prow = [], []
    for i in reversed(range(bits)):                 # MSB on the left
        m = 2**i
        en, enb = ("phis", "phisb") if i == bits - 1 else ("phig", "phigb")
        nrow += [Dev(f"Msn{i}", "n", sw["in_wn"] * m, ln, f"bot_{i}", en, "vin", flavor=fl),
                 Dev(f"Mdn{i}", "n", drv["wn"] * m, L, f"bot_{i}", f"ng_{i}", "vss")]
        prow += [Dev(f"Msp{i}", "p", sw["in_wp"] * m, lp, f"bot_{i}", enb, "vin", flavor=fl),
                 Dev(f"Mdp{i}", "p", drv["wp"] * m, L, f"bot_{i}", f"pg_{i}", "vref")]
    nrow += [Dev("Msnd", "n", sw["in_wn"], ln, "botd", "phig", "vin", flavor=fl),
             Dev("Mddn", "n", drv["wn"], L, "botd", "phigb", "vss"),
             Dev("Mttn", "n", sw["top_wn"], ln, "top", "phit", "vcm", flavor=fl)]
    prow += [Dev("Mspd", "p", sw["in_wp"], lp, "botd", "phigb", "vin", flavor=fl),
             Dev("Mttp", "p", sw["top_wp"], lp, "top", "phitb", "vcm", flavor=fl)]
    from ..netlist import switch_pins
    return nrow, prow, switch_pins(bits)
