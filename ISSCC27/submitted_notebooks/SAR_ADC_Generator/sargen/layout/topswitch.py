"""Top-plate sampling switch (transmission gate top <-> vcm) from SKY130 PDK FET PCells, in guard rings.

    vdd rail + n-tap (ring top)
    phitb comb (PMOS gates)                        gate contacts on the outer side of each row
    [vcm Mp top Mp vcm ...]                        PMOS fingers, the top node on inner shared bars
    n-tap ring segment                             | n-well
    vcm / top / vcm tracks (met2)                  NMOS vcm, shared top, PMOS vcm: drops never pass each other
    p-tap ring segment
    [vcm Mn top Mn vcm ...]                        NMOS fingers
    phit comb (NMOS gates)
    vss rail + p-tap (ring bottom)

The switch's diffusion is the floating top plate's only junction to the substrate, so the NMOS sits in a
closed p+ ring to vss and the PMOS in a closed n-tap ring to vdd (Hastings, guard rings; SKY130 latch-up
LU.2 / LU.3).  The top node goes up to met4, the CDAC top plate's layer (no met5: TinyTapeout grid).
"""

import math

from .cdac import M2_PAD, M3_PAD, MET2, MET3, MET4, VIA, VIA2, snap
from .cell import MET1, NWELL, VIA1, V1, Dev
from .strongarm import (RAIL_W, R_DIFF_TAP, TAP_H, M1_STUB, TRK, TRK_IN, WF_MAX, Row, _clusters, _fe_extra,
                        _row_draw, _tap_strip)
from .unitcell import LI, MC, MCON, NSDM, PSDM, R_M1_SP, R_M2_SP, V1_M1, V1_M2, _pin, _poly
from ..pdk import W_MIN

VIA3, M3_TOP = (70, 44), 0.50          # via3; met3 landing (met3.6 area 0.24 um^2)
EXIT = 0.8                              # vcm / phit / phitb leave the cell on met2 this far past its edge


def finger_count(wn, wp):
    """One finger count for both rows (the PMOS fingers are wider by wp / wn), so the two rows are equally long and
    the guard ring closes tightly around both; even where the finger width allows, so both row ends are vcm."""
    k = max(1, math.ceil(wn / WF_MAX - 1e-9), math.ceil(wp / (WF_MAX * max(1.0, wp / wn)) - 1e-9))
    if k % 2 and min(wn, wp) / (k + 1) >= W_MIN:
        k += 1
    return k


def _fingers(name, kind, w, l, flavor, gate, side, k, dummies=True):
    """Fingers of one device, the top node on inner shared bars: vcm top vcm ... , and a dummy finger at each end
    (gate on the row's gate net, both diffusions on vcm): every active finger sees a neighbouring gate on both
    sides, and the end fingers' diffusion runs one pitch further (length-of-diffusion stress, sargen.layout.lod).
    A dummy shares the end bar where that bar is vcm; next to a top bar (odd count) it stands alone, so the floating
    top plate gains no junction."""
    dv = Dev(name, kind, w / k, l, "", "", "", fingers=1, tie=False, flavor=flavor)
    nodes = ["vcm" if i % 2 == 0 else "top" for i in range(k + 1)]
    dmy = lambda i: (f"{name}d.{i}", dv, gate, side, "vcm", "vcm")
    act = [(f"{name}.{i}", dv, gate, side, nodes[i], nodes[i + 1]) for i in range(k)]
    return Row([dmy(0)] + act + [dmy(1)] if dummies else act, align="bot" if side == "bot" else "top")


def top_switch_rows(design, matched=True):
    """(NMOS row, PMOS row) of the top-plate switch, centred on x = 0.  matched=False: the earlier layout (each row
    in fingers no wider than WF_MAX, no dummies), kept for the matching study."""
    from ..pdk import NFET_LVT, PFET_LVT, TG_FLAVORS
    sw = design["sw"]
    nm, ln, pm, lp = TG_FLAVORS[sw.get("top_flavor", sw.get("flavor", "std"))]
    # threshold per device: a flavour may mix an LVT NMOS with a standard-Vt PMOS
    k = finger_count(sw["top_wn"], sw["top_wp"])
    kn, kp = (k, k) if matched else (max(1, math.ceil(sw[w] / WF_MAX - 1e-9)) for w in ("top_wn", "top_wp"))
    nrow = _fingers("Mttn", "n", sw["top_wn"], ln, "lvt" if nm == NFET_LVT else "std", "phit", "bot", kn, matched)
    prow = _fingers("Mttp", "p", sw["top_wp"], lp, "lvt" if pm == PFET_LVT else "std", "phitb", "top", kp, matched)
    nrow.center()
    prow.center()
    return nrow, prow


def build_top_switch(design, name="topsw"):
    """Returns (Component, info, reference netlist).  Ports: top vcm phit phitb vdd vss."""
    from gdsfactory import Component
    from ..netlist import tg_lines
    from ..pdk import mos
    from .cell import model_name
    sw = design["sw"]
    fl = sw.get("top_flavor", sw.get("flavor", "std"))
    nrow, prow = top_switch_rows(design)
    for row in (nrow, prow):
        for f in row.f:
            _fe_extra(f["fe"])
    top = Component(name + "_hier")
    rect = lambda xa, ya, xb, yb, lay: _poly(top, xa, ya, xb, yb, lay)

    def box(x, y, w, h, lay):
        rect(x - w / 2, y - h / 2, x + w / 2, y + h / 2, lay)

    def v1(x, y, li=True):
        if li:
            box(x, y, MC, MC, MCON)
        box(x, y, *V1_M1, MET1)
        box(x, y, V1, V1, VIA1)
        box(x, y, *V1_M2, MET2)

    fN, fP = nrow.f[0], prow.f[0]
    # ---- vertical placement
    y_g0 = RAIL_W + R_M1_SP + V1_M1[1] / 2                         # NMOS gate comb
    yN = max(y_g0 - fN["fe"].pad_y - fN["dy"], RAIL_W / 2 + TAP_H / 2 + R_DIFF_TAP - nrow.span(0, "diff", 2))
    y_g0 = yN + fN["dy"] + fN["fe"].pad_y
    y_pseg = nrow.span(yN, "diff", 3) + R_DIFF_TAP + TAP_H / 2      # p-ring top segment (vcm track over it)
    nw0 = y_pseg + TAP_H / 2 + 0.13 + 0.05                          # n-well edge (p-tap to n-well)
    y_nseg = max(nw0 + 0.18 + TAP_H / 2, y_pseg + 2 * (V1_M1[1] + R_M1_SP))  # n-ring segment; tracks 0.46 apart
                                                                    # (via pads of drops at one x stay clear)
    nw0 = y_nseg - 0.18 - TAP_H / 2
    yP = y_nseg + TAP_H / 2 + R_DIFF_TAP - prow.span(0, "diff", 2)
    y_g1 = yP + fP["dy"] + fP["fe"].pad_y                           # PMOS gate comb
    y_vdd = max(y_g1 + V1_M1[1] / 2 + R_M1_SP, prow.span(yP, "diff", 3) + R_DIFF_TAP + TAP_H / 2 - RAIL_W / 2)
    H = y_vdd + RAIL_W
    _row_draw(top, nrow, yN)
    _row_draw(top, prow, yP)
    # ---- rings: x of the side stripes clear of every diffusion and implant
    xs = [f["x"] + f["fe"].diff[k] for row in (nrow, prow) for f in row.f for k in (0, 1)]
    xi = [f["x"] + f["fe"].imp[k] for row in (nrow, prow) for f in row.f for k in (0, 1)]
    xg = [x + s * 0.4 for row in (nrow, prow) for f in row.f for x, s in ((f["x"], -1), (f["x"], 1))]
    x_ring = max(max(abs(v) for v in xs) + R_DIFF_TAP, max(abs(v) for v in xi) + 0.13,
                 max(abs(v) for v in xg) + V1_M1[0] / 2 + 0.3) + TAP_H / 2
    X1 = x_ring + TAP_H / 2 + 0.18
    for yr, kind in ((0.0, "p"), (y_vdd, "n")):                    # outer strips under the rails
        rect(-X1, yr, X1, yr + RAIL_W, MET1)
        _tap_strip(top, -X1 + 0.2, X1 - 0.2, yr + RAIL_W / 2, kind)
    _tap_strip(top, -x_ring - TAP_H / 2, x_ring + TAP_H / 2, y_pseg, "p", mcon=False)   # inner segments
    _tap_strip(top, -x_ring - TAP_H / 2, x_ring + TAP_H / 2, y_nseg, "n", mcon=False)
    for x in (-x_ring, x_ring):
        _tap_strip(top, RAIL_W / 2, y_pseg, x, "p", vertical=True, margin=TAP_H)
        _tap_strip(top, y_nseg, y_vdd + RAIL_W / 2, x, "n", vertical=True, margin=TAP_H)
    rect(-X1, nw0, X1, H + 0.3, NWELL)
    # ---- source / drain: three tracks, vcm (NMOS) over the p-ring segment, top in the middle, vcm (PMOS) over
    # the n-ring segment: every drop reaches its track without passing a drop of the other net (any finger counts)
    y_vn, y_top, y_vp = y_pseg, (y_pseg + y_nseg) / 2, y_nseg
    y_vcm = y_vn
    drops = {}
    for row, y, up, yv in ((nrow, yN, True, y_vn), (prow, yP, False, y_vp)):
        for x, n, f in row.bars():
            yb = y + f["dy"] + f["fe"].bar_y[1 if up else 0]
            ym = yb - MC / 2 if up else yb + MC / 2
            box(x, ym, MC, MC, MCON)
            box(x, ym, M1_STUB, MC + 0.12, MET1)
            yt = yv if n == "vcm" else y_top
            rect(x - M1_STUB / 2, min(ym, yt), x + M1_STUB / 2, max(ym, yt), MET1)
            drops.setdefault((n, yt), []).append(x)
    for (n, yt), xs_ in drops.items():                              # (both rows share the top track)
        for cl in _clusters(xs_, V1_M1[0] + R_M1_SP):               # one via per group of nearby drops
            rect(cl[0] - M1_STUB / 2, yt - V1_M1[1] / 2, cl[-1] + M1_STUB / 2, yt + V1_M1[1] / 2, MET1)
            v1(snap(sum(cl) / len(cl)), yt, li=False)
    xs_all = [x for row in (nrow, prow) for x, n, f in row.bars()]
    xj = min(xs_all) - 0.6                                          # the two vcm tracks join on met3 here
    for net, y, xs_ in (("vcm", y_vn, [x for x, n, f in nrow.bars("vcm")]),
                        ("vcm", y_vp, [x for x, n, f in prow.bars("vcm")]),
                        ("top", y_top, [x for row in (nrow, prow) for x, n, f in row.bars("top")])):
        xa = min(xs_ + ([xj] if net == "vcm" else []))
        rect(xa - V1_M2[0] / 2, y - TRK / 2, max(xs_) + V1_M2[0] / 2, y + TRK / 2, MET2)
    for y in (y_vn, y_vp):
        box(xj, y, M2_PAD, M2_PAD, MET2)
        box(xj, y, VIA, VIA, VIA2)
        box(xj, y, M3_PAD, M3_PAD, MET3)
    rect(xj - M3_PAD / 2, y_vn - M3_PAD / 2, xj + M3_PAD / 2, y_vp + M3_PAD / 2, MET3)
    # top -> met4 (the CDAC top plate's layer) at the track's right end; vcm pin on met2 at the left end
    xt = max(x for row in (nrow, prow) for x, n, f in row.bars("top")) + 0.6
    rect(xt - 0.6, y_top - TRK / 2, xt, y_top + TRK / 2, MET2)
    box(xt, y_top, M2_PAD, M2_PAD, MET2)
    box(xt, y_top, VIA, VIA, VIA2)
    box(xt, y_top, M3_TOP, M3_TOP, MET3)
    box(xt, y_top, 0.2, 0.2, VIA3)
    box(xt, y_top, 0.6, 0.6, MET4)
    _pin(top, "top", xt, y_top, MET4)
    xv = min(x for row in (nrow, prow) for x, n, f in row.bars("vcm"))
    rect(-X1 - EXIT, y_vcm - TRK_IN / 2, xv, y_vcm + TRK_IN / 2, MET2)     # vcm leaves the cell to the left
    _pin(top, "vcm", -X1 - EXIT + 0.15, y_vcm, MET2)
    # ---- gates: combs -> via at the comb end -> pins on met2
    for row, y, net in ((nrow, y_g0, "phit"), (prow, y_g1, "phitb")):
        xa = min(f["x"] for f in row.f) - f["fe"].pad_poly[1]
        xb = max(f["x"] for f in row.f) + 0.4
        rect(xa, y - MC / 2, xb + MC / 2, y + MC / 2, LI)
        v1(xb, y)
        rect(xb, y - TRK_IN / 2, X1 + EXIT, y + TRK_IN / 2, MET2)         # gates leave the cell to the right
        _pin(top, net, X1 + EXIT - 0.15, y, MET2)
    _pin(top, "vss", 0.0, RAIL_W / 2, MET1)
    _pin(top, "vdd", 0.0, y_vdd + RAIL_W / 2, MET1)
    top = top.flatten()
    top.name = name
    bb = top.bbox
    lines = tg_lines("Mtt", "top", "vcm", "phit", "phitb", sw["top_wn"], sw["top_wp"], fl)
    lines = [ln.replace(" 0 ", " vss ", 1) if ln.startswith("XMttn") or ln.startswith("MMttn") else ln for ln in lines]
    for row, g, b in ((nrow, "phit", "vss"), (prow, "phitb", "vdd")):   # end dummies: both diffusions on vcm
        f = row.f[0]["dv"]
        lines.append(mos(f"{f.name}d", "vcm", g, "vcm", b, model_name(f), f.w, f.l, 2))
    pins = ["top", "vcm", "phit", "phitb", "vdd", "vss"]
    ref = "\n".join([f".subckt {name} {' '.join(pins)}"] + lines + [f".ends {name}"]) + "\n"
    info = dict(width=float(bb[1][0] - bb[0][0]), height=float(bb[1][1] - bb[0][1]), flavor=fl,
                fingers=dict(n=len(nrow.f) - 2, p=len(prow.f) - 2, dummies=4))
    return top, info, ref
