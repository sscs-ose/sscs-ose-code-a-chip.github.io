"""Compact StrongARM comparator from SKY130 PDK FET PCells, mirror-symmetric about x = 0.

    vdd rail + n-tap
    clk combs (reset gates) + clk track             clk risers (met3) on both edges
    [Mop1] [vdd Mp1 outn Mr1 vdd Mr3 xp] | mirror   PMOS: latch + reset share diffusion, output inverter outside
    outp / outn tracks, swapped on the axis         cross-coupling with equal parasitics on both outputs
    [Mon1] [dmy outn Mn1 xp]             | mirror   NMOS latch with an outer dummy, output inverter outside
    dmy tail A xp A tail B xn B tail dmy            input pair, clustered (each drain an inner diffusion), dummies
    inp / inn tracks                                inputs leave sideways, away from clk and the outputs
    vss tail vss                                    clocked tail on the symmetry axis
    clk comb + vss rail + p-tap

Layout rules followed (Razavi, SSC Magazine 2015 / 2020; Hastings, The Art of Analog Layout; Boser, EE240B;
Sharma et al., DATE 2021): mirror symmetry with the tail and the clock on the axis, so clock and tail charge
couple equally to both sides; identical drain geometry for the input pair (equal Cgd and node capacitance on
xp / xn: no dynamic offset), each device clustered rather than common-centroid at this size; all gates in one
direction; equal routing on the two outputs (the cross-coupling tracks swap on the axis, a met3 trim stub
balances the crossing); inputs routed apart from the clock and the outputs; dummy fingers (all terminals on
tail) at both ends of the input pair; p-tap guard stripes beside the NMOS rows and n-tap stripes beside the
PMOS row, closing guard rings with the tap strips under the rails.  All devices are standard-Vt (the PDK's LVT
matches ~1.6x worse).
"""

import math

from .cdac import M2_PAD, M3_PAD, MET2, MET3, VIA, VIA2, snap
from .cell import DIFF, MET1, NWELL, VIA1, V1, Dev
from .unitcell import (LI, MC, MCON, NSDM, POLY, PSDM, R_DIFF_SP, R_IMP_SP, R_LI_SP, R_M1_SP, R_M2_SP,
                       R_POLY_SP, TAP, V1_M1, V1_M2, _ext, _Fet, _pin, _poly)

NPC, LICON = (95, 20), (66, 44)
WF_IN_MAX = 2.5         # input pair: finger width limit
WF_MAX = 2.0            # other devices: fingers no wider than this
SPLIT = 0.34            # two contact bars instead of one shared bar (lets neighbouring gate pads sit on one side)
R_NPC_SP = 0.27
RAIL_W = 0.48           # vss / vdd rails (met1)
TAP_H, TAP_LI, LICON_P = 0.41, 0.33, 0.36   # tap strip under a rail: tap height, li height, licon / mcon pitch
R_DIFF_TAP = 0.27
R_NWELL_PTAP = 0.13 + TAP_H / 2
M1_STUB = 0.23          # met1 vertical stubs (mcon + 0.03)
TRK = 0.26              # met2 track width (= via1 pad height, so vias sit flush in a track)
TRK_IN = 0.14           # inp / inn / clk tracks
XJ = 0.46               # output tracks swap between x = -XJ and +XJ
IN_PITCH = 0.40         # common-centroid pair: inp / inn tracks below the comb level
BAND_DY = 0.42          # extra met2 tracks over a diffusion band (xp / xn), off its centre (slim via2 fits)
EXIT = 0.8              # inp / inn / clk / qp / qn leave the cell on met2 this far past its edge
AXIS_CLEAR = 1.2        # latch inner dummy only if its diffusion ends this far from the axis (output crossover, links)
TRIM_L0, TRIM_DL = 0.80, 0.05   # met3 trim stub on outn: 0.80 um + 0.05 um per extra latch finger, tuned on
                                 # extraction (outp / outn within 0.1 %: 1 finger 4 / 6 bit, 9 fingers 8 bit)


class Row:
    """Fingers of one device row, left to right, built from PCell fingers that share contact bars where the
    nodes and finger widths allow.  Each finger: (name, Dev, gate net, pad side 'top'/'bot', left, right).
    Fingers of different widths are aligned on `align` ('bot' or 'top': their gate contacts line up)."""

    def __init__(self, fingers, align="bot"):
        self.align = align
        self.f = [dict(name=n, dv=dv, g=g, side=s, left=a, right=b, fe=_Fet(dv, s)) for n, dv, g, s, a, b in fingers]
        if align == "bot":
            ref = min(f["fe"].diff[2] for f in self.f)
            for f in self.f:
                f["dy"] = ref - f["fe"].diff[2]
        else:
            ref = max(f["fe"].diff[3] for f in self.f)
            for f in self.f:
                f["dy"] = ref - f["fe"].diff[3]
        x, self.split = 0.0, set()
        self.f[0].update(x=0.0, shared=False)
        for a, b in zip(self.f, self.f[1:]):
            fa, fb = a["fe"], b["fe"]
            share = (a["right"] == b["left"] and a["dv"].w == b["dv"].w and a["dv"].kind == b["dv"].kind
                     and a["dv"].flavor == b["dv"].flavor)
            if share:
                d = fa.sd + fb.sd
                pa, pb = _fe_extra(fa).pad_poly, _fe_extra(fb).pad_poly
                if a["g"] != b["g"]:
                    if a["side"] == b["side"]:       # two gate contacts side by side
                        tight = d - pa[1] + pb[0] < max(R_POLY_SP, R_LI_SP)
                    else:                            # a gate contact next to the other gate's poly end
                        tight = min(d - pa[1] - b["dv"].l / 2, d + pb[0] - a["dv"].l / 2) < R_POLY_SP
                    if tight:
                        d += SPLIT
                        self.split.add(b["name"])
            else:
                d = fa.diff[1] + R_DIFF_SP - fb.diff[0]
            x += d
            b.update(x=x, shared=share)
        self.by = {f["name"]: f for f in self.f}

    def shift(self, dx):
        for f in self.f:
            f["x"] += dx

    def center(self):
        self.shift(-(self.f[0]["x"] + self.f[-1]["x"]) / 2)

    def anchor(self, name, part, x):
        f = self.by[name]
        self.shift(x - (f["x"] + {"L": -f["fe"].sd, "R": f["fe"].sd, "G": 0.0}[part]))

    def mirrored(self, rename):
        """Mirror image about x = 0 (left half -> right half), nets and device names renamed."""
        out = Row([(rename(f["name"]), f["dv"], rename(f["g"]), f["side"], rename(f["right"]), rename(f["left"]))
                   for f in reversed(self.f)], self.align)
        for fo, fi in zip(out.f, reversed(self.f)):     # exact mirror of the placed fingers
            fo["x"] = -fi["x"]
        return out

    def bars(self, net=None):
        """[(x, node, finger)] of the contact bars to route (a shared bar once; of a split pair, which shares
        one diffusion, only the one nearer the axis)."""
        out = []
        for i, f in enumerate(self.f):
            if i == 0 or not f["shared"]:
                out.append((f["x"] - f["fe"].sd, f["left"], f))
            elif f["name"] in self.split:
                left = (f["x"] - f["fe"].sd, f["left"], f)
                if abs(left[0]) < abs(out[-1][0]):
                    out[-1] = left
            out.append((f["x"] + f["fe"].sd, f["right"], f))
        return [b for b in out if net is None or b[1] == net]

    def gates(self, net=None, side=None):
        return [f for f in self.f if (net is None or f["g"] == net) and (side is None or f["side"] == side)]

    def span(self, y, attr, k):
        """Lowest (k = 2) / highest (k = 3) extent of a finger attribute over the row placed at y."""
        vals = [y + f["dy"] + getattr(f["fe"], attr)[k] for f in self.f]
        return min(vals) if k == 2 else max(vals)


def _clusters(xs, gap):
    """Sorted xs grouped where neighbours are closer than gap."""
    xs = sorted(xs)
    out = [[xs[0]]]
    for x in xs[1:]:
        (out[-1].append(x) if x - out[-1][-1] < gap else out.append([x]))
    return out


def _segments(row, net):
    """x-ranges (gate x) of the runs of neighbouring same-net gates in a row (one gate-contact comb each)."""
    out = []
    for f in row.f:
        if f["g"] != net:
            continue
        if out and f["shared"] and out[-1][2] == row.f.index(f) - 1:
            out[-1] = (out[-1][0], f["x"], row.f.index(f))
        else:
            out.append((f["x"], f["x"], row.f.index(f)))
    return [(a, b) for a, b, _ in out]


def _fe_extra(fe):
    """Poly pad and npc extents of a FET finger (relative to the diffusion centre)."""
    if not hasattr(fe, "pad_poly"):
        # the poly around the gate contact (li pad +- 0.08), from the poly shape that holds it (for long
        # channels the gate and its contact pad are one polygon)
        yc = fe.pad_y - fe.oy                                       # (PCell coordinates)
        pad = [p for p in fe.comp.get_polygons(by_spec=POLY) if min(p[:, 1]) <= yc <= max(p[:, 1])][0]
        fe.pad_poly = (min(pad[:, 0]), max(pad[:, 0]), max(min(pad[:, 1]) + fe.oy, fe.pad[2] - 0.08),
                       min(max(pad[:, 1]) + fe.oy, fe.pad[3] + 0.08))
        e = _ext(fe.comp, NPC)
        fe.npc = (e[0], e[1], e[2] + fe.oy, e[3] + fe.oy)
    return fe


def _row_draw(top, row, y):
    """Place the PCell fingers of a row (reference y), merge same-net gate contacts, split diffusions, npc and
    implants between neighbours."""
    rect = lambda xa, ya, xb, yb, lay: _poly(top, xa, ya, xb, yb, lay)
    for f in row.f:
        ref = top << f["fe"].comp
        ref.move((snap(f["x"]), snap(y + f["dy"] + f["fe"].oy)))
    for a, b in zip(row.f, row.f[1:]):
        fa, fb = _fe_extra(a["fe"]), _fe_extra(b["fe"])
        ya, yb = y + a["dy"], y + b["dy"]
        if b["shared"] and b["name"] in row.split:          # two bars: fill the diffusion between them
            rect(a["x"] + fa.diff[1] - 0.01, ya + fa.diff[2], b["x"] + fb.diff[0] + 0.01, ya + fa.diff[3], DIFF)
        if a["side"] == b["side"] and abs(ya + fa.pad_y - yb - fb.pad_y) < 1e-6:
            if a["g"] == b["g"] and b["x"] - a["x"] < 1.0:     # same gate net: one comb (poly + li)
                rect(a["x"] + fa.pad_poly[1] - 0.01, ya + fa.pad_poly[2], b["x"] + fb.pad_poly[0] + 0.01,
                     ya + fa.pad_poly[3], POLY)
                rect(a["x"] + fa.pad[1] - 0.01, ya + fa.pad[2], b["x"] + fb.pad[0] + 0.01, ya + fa.pad[3], LI)
            if b["x"] + fb.npc[0] - (a["x"] + fa.npc[1]) < R_NPC_SP:
                rect(a["x"] + fa.npc[1] - 0.01, ya + fa.npc[2], b["x"] + fb.npc[0] + 0.01, ya + fa.npc[3], NPC)
        ia, ib = fa.imp, fb.imp                              # same-type implants merged
        if 0 < (b["x"] + ib[0]) - (a["x"] + ia[1]) < R_IMP_SP:
            lay = NSDM if a["dv"].kind == "n" else PSDM
            rect(a["x"] + ia[1] - 0.01, max(ya + ia[2], yb + ib[2]), b["x"] + ib[0] + 0.01,
                 min(ya + ia[3], yb + ib[3]), lay)


def _odd(n):
    n = max(1, int(n))
    return n if n % 2 else n + 1


def input_pattern(m):
    """Finger order of the input pair, as pairs of fingers sharing a drain (A = Mi1 / inp, B = Mi2 / inn):
    clustered and mirror-symmetric at every size, A ... A | B ... B, each drain an inner diffusion.

    Clustered beats common centroid for StrongARM latches (Sharma et al., DATE 2021: common centroid adds
    X / Y capacitance mismatch), and the mirror keeps xp and xn exact images (equal capacitance, equal
    coupling to the inputs, no crossings).  Gradients stay negligible over the pair's width next to the
    random mismatch the sizing allows (Pelgrom: the distance term is small over tens of um)."""
    return ["A"] * (m // 2) + ["B"] * (m // 2)


def strongarm_rows(c, end_dummies=True, compact=True):
    """Device rows of the StrongARM (left halves mirrored where the circuit is left/right symmetric).

    One architecture for every resolution: the sizing (design['cmp']) sets the widths, this sets the
    fingers: input pair in an even number of fingers <= WF_IN_MAX per device (clustered, mirror-symmetric);
    the tail gets as many fingers as the pair (tail node on the axis); latch NMOS / PMOS odd finger counts
    no wider than WF_MAX, so the xp / output bars keep their places."""
    L, Lin = c["l"], c["l_in"]
    swap = {"inp": "inn", "xp": "xn", "outp": "outn", "qp": "qn", "Mon1": "Mon2", "Mn1": "Mn2", "Mop1": "Mop2",
            "Mp1": "Mp2", "Mr1": "Mr2", "Mr3": "Mr4", "Mdl1": "Mdl2", "d_outn": "d_outp",
            "Mdx1": "Mdx2", "Mdp1": "Mdp2", "Mdq1": "Mdq2"}
    swap.update({v: k for k, v in list(swap.items())})

    def sw(n):
        base, dot, idx = n.partition(".")
        return swap.get(base, base) + dot + idx

    def dev(name, kind, w, l):
        return Dev(name, kind, w, l, "", "", "", fingers=1, tie=False)

    for w in (c["w_inv_n"], c["w_rst"]):
        if w > WF_MAX + 1e-9:
            raise NotImplementedError(f"compact StrongARM: reset / inverter NMOS wider than {WF_MAX} um")
    # input pair
    m = 2 * math.ceil(c["w_in"] / (2 * WF_IN_MAX) - 1e-9)        # even fingers per device, each <= WF_IN_MAX
    wi = c["w_in"] / m
    seq = []
    for d in input_pattern(m):
        x = "xp" if d == "A" else "xn"
        name, g = ("Mi1", "inp") if d == "A" else ("Mi2", "inn")
        seq += [(name, g, "tail", x), (name, g, x, "tail")]
    cnt = {}
    fingers = []
    for name, g, a, b in seq:
        k = cnt[name] = cnt.get(name, -1) + 1
        fingers.append((f"{name}.{k}", dev(name, "n", wi, Lin), g, "bot", a, b))
    dmy = lambda n: (n, dev("Md", "n", wi, Lin), "tail", "bot", "tail", "tail")   # dummy: all terminals on tail
    inp = Row([dmy("Md1")] + fingers + [dmy("Md2")])
    inp.center()
    # tail: as many fingers as the pair (even count of pairs: the tail node sits on the axis)
    kt = max(2, 2 * round(m / 2))
    nodes = ["tail" if i % 2 == 0 else "vss" for i in range(2 * kt + 1)]
    tail = Row([(f"Mt.{i}", dev("Mt", "n", c["w_tail"] / (2 * kt), L), "clk", "bot", nodes[i], nodes[i + 1])
                for i in range(2 * kt)])
    tail.center()
    x_xp = min(x for x, n, _ in inp.bars("xp"))                   # outermost xp bar of the pair
    # NMOS latch (left): output-inverter NMOS outside, outer dummy finger (gate on Mn1's gate net, both
    # diffusions on outn), Mn1 in an odd number of fingers outn xp outn ... xp, its inner xp bar above the pair's
    kn = _odd(math.ceil(c["w_ln"] / WF_MAX - 1e-9))
    wn = c["w_ln"] / kn
    mn = [(f"Mn1.{i}", dev("Mn1", "n", wn, L), "outp", "top", ("outn", "xp")[i % 2], ("xp", "outn")[i % 2])
          for i in range(kn)]
    # a dummy finger at both ends of the latch device (outer: Mdl1 on outn; inner: Mdx1 on xp, gate on Mn1's gate
    # net): every Mn1 finger has a gate on either side and the end fingers' diffusion runs one pitch further
    # (end_dummies=False: the earlier layout, outer dummy only - kept for the matching study)
    nl = Row([("Mon1", dev("Mon1", "n", c["w_inv_n"], L), "outp", "top", "qp", "vss"),
              ("Mdl1", dev("Mdl", "n", wn, L), "outp", "top", "d_outn", "outn")] + mn +
             ([("Mdx1", dev("Mdx", "n", wn, L), "outp", "top", "xp", "xp")] if end_dummies else []), align="top")
    nl.anchor(f"Mn1.{kn - 1}", "R", x_xp)
    dx_ = nl.by.get("Mdx1")
    if dx_ and abs(dx_["x"] + dx_["fe"].diff[1]) < AXIS_CLEAR:   # small latch next to the axis: no room for the inner dummy
        nl = Row([(f["name"], f["dv"], f["g"], f["side"], f["left"], f["right"]) for f in nl.f if f["name"] != "Mdx1"],
                 align="top")
        nl.anchor(f"Mn1.{kn - 1}", "R", x_xp)
    # matched devices close together: where the pair is wider than the latch, the latch halves move in to the axis
    # clearance instead of sitting over the pair's outer drains (the xp / xn link then runs on the met2 band
    # tracks and a met3 jumper, identical on both sides)
    end = nl.f[-1]
    gap = -AXIS_CLEAR - (end["x"] + end["fe"].diff[1])
    if compact and gap > 1e-6:
        nl.shift(gap)
    x_lat = nl.by[f"Mn1.{kn - 1}"]["x"] + nl.by[f"Mn1.{kn - 1}"]["fe"].sd     # Mn1's inner xp bar
    # PMOS (left): output-inverter PMOS outside; latch Mp1 (odd fingers vdd outn ... outn) + reset Mr1 (outn)
    # + reset Mr3 (xp).  The inverter PMOS is folded to the latch finger width when it is a multiple of it
    # (shares a vdd bar with Mp1, keeps the row one finger tall), else into fingers no wider than WF_MAX / 2
    kp = _odd(math.ceil(c["w_lp"] / WF_MAX - 1e-9))
    wp = c["w_lp"] / kp
    k = round(c["w_inv_p"] / wp)
    k = k if k >= 1 and abs(k * wp - c["w_inv_p"]) < 1e-6 else math.ceil(c["w_inv_p"] / (WF_MAX / 2))
    mop = [(f"Mop1.{i}", dev("Mop1", "p", c["w_inv_p"] / k, L), "outp", "bot", ("vdd", "qp")[(k - i) % 2],
            ("qp", "vdd")[(k - i) % 2]) for i in range(k)]
    mp = [(f"Mp1.{i}", dev("Mp1", "p", wp, L), "outp", "bot", ("vdd", "outn")[i % 2], ("outn", "vdd")[i % 2])
          for i in range(kp)]
    # latch PMOS between two dummy fingers (gate on Mp1's gate net; outer on vdd, inner on outn)
    dp = [("Mdp1", dev("Mdp", "p", wp, L), "outp", "bot", "vdd", "vdd")] if end_dummies else []
    dq = [("Mdq1", dev("Mdq", "p", wp, L), "outp", "bot", "outn", "outn")] if end_dummies else []
    pl = Row(mop + dp + mp + dq + [
              ("Mr1", dev("Mr1", "p", c["w_rst"], L), "clk", "top", "outn", "vdd"),
              ("Mr3", dev("Mr3", "p", c["w_rst"], L), "clk", "top", "vdd", "xp")], align="bot")
    pl.anchor("Mr3", "R", x_lat)                                   # the reset of xp over the latch's xp bar
    # output inverter as a column: Mon1's qp bar under Mop1's qp bar (qp is one met1 drop, no track).  The
    # inverter NMOS moves out to its PMOS; if the PMOS is the inner one (it is free when it shares no bar
    # with Mp1), the PMOS moves out instead
    x_q = max(x for x, n, f in pl.bars("qp"))
    mon = nl.by["Mon1"]
    if x_q + mon["fe"].sd <= mon["x"] + 1e-6:
        mon["x"] = x_q + mon["fe"].sd
    else:
        assert not any(f["shared"] for f in pl.f if f["name"].startswith("Mp1.0")), \
            "output inverter: PMOS shares a bar with the latch and the NMOS cannot move under it"
        dx = (mon["x"] - mon["fe"].sd) - x_q
        for f in pl.f:
            if f["name"].startswith("Mop1"):
                f["x"] += dx
    if compact and gap > 1e-6:
        # the output inverter stays outboard of the pair and the tail: its vss drop runs down the side
        x_rows = min(f["x"] + f["fe"].diff[0] for row in (inp, tail) for f in row.f) - 0.6
        dx = min(0.0, x_rows - (mon["x"] + mon["fe"].sd))
        mop_f = [f for f in pl.f if f["name"].startswith("Mop1")]
        nxt = pl.f[len(mop_f)]
        if dx < 0 and (nxt["shared"] or any(f["name"] in pl.split for f in mop_f[1:] + [nxt])):
            return strongarm_rows(c, end_dummies, compact=False)     # inverter PMOS folded into the latch row
        for f in mop_f + [mon]:
            f["x"] += dx
    dummies = [("Md1", "tail", "tail", "tail", wi, Lin, "n"), ("Md2", "tail", "tail", "tail", wi, Lin, "n"),
               ("Mdl1", "outn", "outp", "outn", wn, L, "n"), ("Mdl2", "outp", "outn", "outp", wn, L, "n"),
               *([("Mdx1", "xp", "outp", "xp", wn, L, "n"), ("Mdx2", "xn", "outn", "xn", wn, L, "n")]
                 if "Mdx1" in nl.by else []),
               *([("Mdp1", "vdd", "outp", "vdd", wp, L, "p"), ("Mdp2", "vdd", "outn", "vdd", wp, L, "p"),
                  ("Mdq1", "outn", "outp", "outn", wp, L, "p"), ("Mdq2", "outp", "outn", "outp", wp, L, "p")]
                 if end_dummies else [])]
    return dict(tail=tail, inp=inp, nl=nl, nr=nl.mirrored(sw), pl=pl, pr=pl.mirrored(sw), sw=sw, dummies=dummies,
                fingers=dict(inp=m, tail=2 * kt, latch_n=kn, latch_p=kp, inv_p=k))


def build_strongarm(c, name="strongarm"):
    """Compact StrongARM layout; returns (Component, info).  Ports: inp inn clk qp qn vdd vss."""
    from gdsfactory import Component
    R = strongarm_rows(c)
    tail, inp, nl, nr, pl, pr = (R[k] for k in ("tail", "inp", "nl", "nr", "pl", "pr"))
    top = Component(name + "_hier")
    rect = lambda xa, ya, xb, yb, lay: _poly(top, xa, ya, xb, yb, lay)

    def box(x, y, w, h, lay):
        rect(x - w / 2, y - h / 2, x + w / 2, y + h / 2, lay)

    def mcon(x, y):                                   # li -> met1
        box(x, y, MC, MC, MCON)
        box(x, y, M1_STUB, MC + 0.12, MET1)

    def v1(x, y, li=True):                            # (li ->) met1 -> met2
        if li:
            box(x, y, MC, MC, MCON)
        box(x, y, *V1_M1, MET1)
        box(x, y, V1, V1, VIA1)
        box(x, y, *V1_M2, MET2)

    def v2(x, y):                                     # met2 -> met3
        box(x, y, M2_PAD, M2_PAD, MET2)
        box(x, y, VIA, VIA, VIA2)
        box(x, y, M3_PAD, M3_PAD, MET3)

    def vline(x, ya, yb, lay, w):
        rect(x - w / 2, ya, x + w / 2, yb, lay)

    def hline(y, xa, xb, lay, w):
        rect(xa, y - w / 2, xb, y + w / 2, lay)

    def bar_y(f, y, k):                               # bar li bottom (0) / top (1) of finger f in a row at y
        return y + f["dy"] + f["fe"].bar_y[k]

    for row in (tail, inp, nl, pl):
        for f in row.f:
            _fe_extra(f["fe"])
    fT, fI = tail.f[0], inp.f[0]
    fN, fP, fR = nl.by["Mn1.0"], pl.by["Mp1.0"], pl.by["Mr1"]

    # ---------------------------------------------------------------- vertical placement
    y_clk0 = RAIL_W + R_M1_SP + V1_M1[1] / 2                       # tail gate comb + clk track
    yT = y_clk0 - fT["fe"].pad_y - fT["dy"]
    yT = max(yT, RAIL_W / 2 + TAP_H / 2 + R_DIFF_TAP - tail.span(0, "diff", 2))
    y_clk0 = yT + fT["dy"] + fT["fe"].pad_y
    yI = max(tail.span(yT, "poly", 3) + R_POLY_SP - fI["fe"].pad_poly[2],
             tail.span(yT, "bar_y", 1) + R_LI_SP - fI["fe"].pad[2]) - fI["dy"]
    segs = {net: _segments(inp, net) for net in ("inp", "inn")}
    cc = any(len(v) > 1 for v in segs.values())                    # common-centroid pair: inputs on two tracks
    y_Tt = yT + fT["dy"]                                            # tail track over the tail row
    if cc:                                                          # inp / inn tracks between the tail and the pair
        yI = max(yI, y_Tt + TRK / 2 + R_M2_SP + 2 * IN_PITCH + TRK / 2 - fI["dy"] - fI["fe"].pad_y)
    y_in = yI + fI["dy"] + fI["fe"].pad_y                           # input combs + inp / inn tracks
    yN = max(inp.span(yI, "diff", 3) + R_DIFF_SP - nl.span(0, "diff", 2),
             inp.span(yI, "bar_y", 1) + R_LI_SP - nl.span(0, "bar_y", 0),
             inp.span(yI, "poly", 3) + R_POLY_SP - nl.span(0, "poly", 2))
    y_lo = yN + fN["dy"] + fN["fe"].pad_y                           # N gate level, drain / output track
    y_hi = y_lo + max(fN["fe"].npc[3] - fN["fe"].pad_y + R_NPC_SP - (fP["fe"].npc[2] - fP["fe"].pad_y),
                      TRK + R_M2_SP)                                # P gate level, gate cross track
    yP = y_hi - fP["fe"].pad_y - fP["dy"]
    y_clk1 = yP + fR["dy"] + fR["fe"].pad_y                         # reset gate combs + clk track
    y_vdd = max(y_clk1 + V1_M1[1] / 2 + R_M1_SP,                    # vdd rail bottom
                pl.span(yP, "diff", 3) + R_DIFF_TAP + TAP_H / 2 - RAIL_W / 2)
    H = y_vdd + RAIL_W

    for row, y in ((tail, yT), (inp, yI), (nl, yN), (nr, yN), (pl, yP), (pr, yP)):
        _row_draw(top, row, y)
    # implants: one nsdm rectangle over the NMOS rows, one psdm rectangle over the PMOS row (no slivers)
    for rows_, lay in (((tail, yT), (inp, yI), (nl, yN), (nr, yN)), NSDM), (((pl, yP), (pr, yP)), PSDM):
        fs = [(f, y) for row, y in rows_ for f in row.f]
        rect(min(f["x"] + f["fe"].imp[0] for f, y in fs), min(y + f["dy"] + f["fe"].imp[2] for f, y in fs),
             max(f["x"] + f["fe"].imp[1] for f, y in fs), max(y + f["dy"] + f["fe"].imp[3] for f, y in fs), lay)

    xs = [f["x"] + f["fe"].diff[k] for row in (tail, inp, nl, nr, pl, pr) for f in row.f for k in (0, 1)]
    x_dev = max(abs(v) for v in xs)
    x_imp = max(abs(f["x"] + f["fe"].imp[k]) for row in (tail, inp, nl, nr, pl, pr) for f in row.f for k in (0, 1))
    x_ring = max(x_dev + R_DIFF_TAP, x_imp + 0.13) + TAP_H / 2      # guard stripes clear of diffusion and implant
    x_edge = x_ring + TAP_H / 2 + 0.18                              # n-well encloses the n-tap stripes by 0.18
    xr = x_dev - M3_PAD / 2                                         # clk risers (met3), over the outermost devices
    X0, X1 = -x_edge, x_edge

    # ---------------------------------------------------------------- rails, taps, n-well
    for yr, kind in ((0.0, "p"), (y_vdd, "n")):
        hline(yr + RAIL_W / 2, X0, X1, MET1, RAIL_W)
        _tap_strip(top, X0 + 0.2, X1 - 0.2, yr + RAIL_W / 2, kind)
    nw0 = pl.span(yP, "diff", 2) - 0.18
    rect(X0, nw0, X1, H + 0.3, NWELL)
    # guard rings: p-tap stripes beside the NMOS rows up to the n-well, n-tap stripes beside the PMOS row;
    # with the tap strips under the rails they ring the NMOS and the PMOS devices
    for x in (-x_ring, x_ring):
        p_top = min(nw0 - R_NWELL_PTAP, pl.span(yP, "imp", 2) - R_IMP_SP - 0.13)
        _tap_strip(top, RAIL_W / 2, p_top, x, "p", vertical=True, margin=TAP_H)
        _tap_strip(top, nw0 + 0.18, y_vdd + RAIL_W / 2, x, "n", vertical=True, margin=TAP_H)

    # ---------------------------------------------------------------- tail: vss down, tail up, clk comb
    for x, n, f in tail.bars("vss"):
        mcon(x, bar_y(f, yT, 0) + MC / 2)
        vline(x, RAIL_W / 2, bar_y(f, yT, 0) + MC, MET1, M1_STUB)
    # clk comb via: right of the tail's gates, clear of the met1 drops to the vss rail
    drops = [x for x, n, f in tail.bars("vss")] + [x for x, n, f in nr.bars("vss")]
    x_g = max(f["x"] for f in tail.f) + fT["fe"].pad_poly[1]
    cand = [x_g + i * 0.005 for i in range(200)]
    xc0 = snap(min(c_ for c_ in cand if min(abs(c_ - d) for d in drops) >= V1_M1[0] / 2 + R_M1_SP + M1_STUB / 2))
    hline(y_clk0, -xc0 - MC / 2, xc0 + MC / 2, LI, MC)
    for x in (-xc0, xc0):
        v1(x, y_clk0)
    # tail node: a met2 track through the tail bars of each row, joined by one met1 link on the axis (both
    # rows have their tail node there)
    y_tt = yI + fI["dy"]
    ib, tb = inp.bars("tail"), tail.bars("tail")
    for x, n, f in ib:
        v1(x, y_tt)
    hline(y_tt, min(b[0] for b in ib), max(b[0] for b in ib), MET2, TRK)
    for x, n, f in tb:
        v1(x, y_Tt)
    hline(y_Tt, min(b[0] for b in tb), max(b[0] for b in tb), MET2, TRK)
    assert any(abs(b[0]) < 1e-6 for b in ib) and any(abs(b[0]) < 1e-6 for b in tb), "tail node not on the axis"
    vline(0.0, y_Tt, y_tt, MET1, M1_STUB)
    for g in inp.gates("tail"):                                     # input-pair dummies: gate -> tail
        mcon(g["x"], y_in)
        vline(g["x"], y_in, y_tt, MET1, M1_STUB)
        hline(y_tt, g["x"] - g["fe"].sd, g["x"] + g["fe"].sd, MET1, V1_M1[1])

    # ---------------------------------------------------------------- inputs: combs -> sideways tracks
    # inputs: one via per comb segment (clear of the tail link on the axis); a clustered pair has one segment
    # per input and leaves sideways on the comb level, a common-centroid pair joins its segments on a track
    for k, (net, sgn) in enumerate((("inp", -1), ("inn", 1))):
        y_net = y_in - (k + 1) * IN_PITCH if cc else y_in
        xvs = []
        for g_lo, g_hi in segs[net]:
            cand = [g_lo + i * 0.005 for i in range(int((g_hi - g_lo) / 0.005) + 1)]
            xv = snap(max(cand, key=lambda x: abs(x)))
            assert abs(xv) >= V1_M1[0] / 2 + R_M1_SP + M1_STUB / 2, "no room for the input via"
            box(xv, y_in, MC, MC, MCON)
            box(xv, y_in, *V1_M1, MET1)
            vline(xv, y_net, y_in, MET1, V1_M1[0])
            v1(xv, y_net, li=False)
            xvs.append(xv)
        xe = sgn * (x_edge + EXIT)
        hline(y_net, min(xvs + [xe]), max(xvs + [xe]), MET2, TRK_IN)   # inputs leave the cell sideways
        _pin(top, net, sgn * (x_edge + EXIT - 0.15), y_net, MET2)

    # ---------------------------------------------------------------- xp / xn: pair -> latch (li) -> reset (met1)
    for k, (net, nrow, prow) in enumerate((("xp", nl, pl), ("xn", nr, pr))):
        # several drains of the pair / the latch NMOS: met2 tracks over their diffusion bands
        tr = {}
        for key, row, y, dyk in (("i", inp, yI, 1), ("n", nrow, yN, -1)):      # mirror: same height both sides
            bs = row.bars(net)
            if len(bs) > 1:
                yb = tr[key] = y + bs[0][2]["dy"] + dyk * BAND_DY
                for x, n, f in bs:
                    v1(x, yb)
                hline(yb, min(b[0] for b in bs), max(b[0] for b in bs), MET2, TRK)
        # bars touched by a real finger (a dummy's outer bar only rides the track; in the mirrored row a shared
        # bar is listed under the dummy's name, so test positions)
        edges = [f["x"] + k * f["fe"].sd for f in nrow.f if not f["name"].startswith("Md") for k in (-1, 1)]
        real = [b for b in nrow.bars(net) if min(abs(b[0] - e) for e in edges) < 1e-6]
        aligned = any(abs(b[0] - min(real, key=lambda q: abs(q[0]))[0]) < 1e-6 for b in inp.bars(net))
        if len(tr) == 2 and not aligned:                  # pair track -> latch track on met3
            ib_ = [b[0] for b in inp.bars(net)]
            xl = min((x for x, n, f in real if abs(abs(x) - xr) >= 0.7), key=abs)
            hline(tr["i"], min(ib_ + [xl]), max(ib_ + [xl]), MET2, TRK)    # (pair track reaches the link)
            for yv in tr.values():
                box(xl, yv, M2_PAD, VIA + 0.08, MET2)
                box(xl, yv, VIA, VIA, VIA2)
                box(xl, yv, M3_PAD, M3_PAD, MET3)
            vline(xl, min(tr.values()) - M3_PAD / 2, max(tr.values()) + M3_PAD / 2, MET3, M3_PAD)
        xn_, _, fn_ = min(real, key=lambda b: abs(b[0]))               # the latch drain above the pair's
        x_xn_col = xn_
        xp_, _, fp_ = prow.bars(net)[0]
        for x, n, f in inp.bars(net):
            if abs(x - xn_) < 1e-6:
                vline(x, bar_y(f, yI, 1) - 0.01, bar_y(fn_, yN, 0) + 0.01, LI, MC)
        mcon(xn_, bar_y(fn_, yN, 0) + MC / 2 + 0.05)
        mcon(xp_, bar_y(fp_, yP, 0) + MC / 2 + 0.05)
        vline(xn_, bar_y(fn_, yN, 0) + 0.05, bar_y(fp_, yP, 0) + MC + 0.05, MET1, M1_STUB)

    # ---------------------------------------------------------------- cross-coupled outputs
    # each side: its gates (one li net over the N and P gate levels, one via) and the other net's drains.
    # Left: outp gates -> y_hi, outn drains -> y_lo; right: mirror.  The tracks swap between -XJ and +XJ.
    for sgn, net_g, net_d, nrow, prow in ((-1, "outp", "outn", nl, pl), (1, "outn", "outp", nr, pr)):
        ng, pg = nrow.gates(net_g, "top"), prow.gates(net_g, "bot")
        hline(y_lo, min(g["x"] for g in ng) - MC / 2, max(g["x"] for g in ng) + MC / 2, LI, MC)
        xo = max(ng, key=lambda g: abs(g["x"]))["x"]                # li link between the gate levels
        hline(y_hi, min([g["x"] for g in pg] + [xo]) - MC / 2, max([g["x"] for g in pg] + [xo]) + MC / 2, LI, MC)
        vline(xo, y_lo, y_hi, LI, MC)
        # gate via on the P gate level, as far as possible from the met1 drops crossing the channel
        drops = [x for net in (net_d, "qp" if sgn < 0 else "qn", "xp" if sgn < 0 else "xn")
                 for x, n, f in prow.bars(net)]
        g_lo = min([g["x"] for g in pg] + [xo])
        g_hi = max([g["x"] for g in pg] + [xo])
        cand = [g_lo + i * 0.005 for i in range(int((g_hi - g_lo) / 0.005) + 1)]
        xgv = snap(max(cand, key=lambda x: min(abs(x - d) for d in drops)))
        assert min(abs(xgv - d) for d in drops) >= V1_M1[0] / 2 + R_M1_SP + M1_STUB / 2, "no room for the gate via"
        v1(xgv, y_hi)
        hline(y_hi, xgv, -XJ if sgn < 0 else 0.0, MET2, TRK)     # left: to outp's via2; right: from the jog
        dx = []
        for x, n, f in nrow.bars(net_d):
            mcon(x, bar_y(f, yN, 1) - MC / 2)
            vline(x, bar_y(f, yN, 1) - MC, y_lo, MET1, M1_STUB)
            dx.append(x)
        for x, n, f in prow.bars(net_d):
            mcon(x, bar_y(f, yP, 0) + MC / 2)
            vline(x, y_lo, bar_y(f, yP, 0) + MC, MET1, M1_STUB)
            dx.append(x)
        for cl in _clusters(dx, V1_M1[0] + R_M1_SP):     # one via per group of nearby drops
            hline(y_lo, cl[0] - M1_STUB / 2, cl[-1] + M1_STUB / 2, MET1, V1_M1[1])
            v1(snap(sum(cl) / len(cl)), y_lo, li=False)
        hline(y_lo, max(dx, key=abs), 0.0 if sgn < 0 else XJ, MET2, TRK)   # left: to the jog; right: outp's via2
    # the swap: outp y_hi (left) -> met3 -> y_lo (right); outn y_lo (left) -> met2 jog on the axis -> y_hi (right)
    v2(-XJ, y_hi)
    v2(XJ, y_lo)
    vline(-XJ, y_lo - M3_PAD / 2, y_hi + M3_PAD / 2, MET3, M3_PAD)
    hline(y_lo, -XJ - M3_PAD / 2, XJ + M3_PAD / 2, MET3, M3_PAD)
    vline(0.0, y_lo - TRK / 2, y_hi + TRK / 2, MET2, TRK)          # outn: y_lo (left) -> y_hi (right) on the axis
    # the crossing puts outp on met3 (and outn on met2) between -XJ and +XJ: a met3 trim stub on outn's
    # right track balances the two output capacitances (tuned on the extracted layout)
    trim = TRIM_L0 + TRIM_DL * (R["fingers"]["latch_n"] - 1)
    if trim > 0:                                      # (start clear of the xn met1 column)
        xs0 = max(XJ + M2_PAD + R_M2_SP, x_xn_col + 0.6)
        v2(xs0, y_hi)
        hline(y_hi, xs0 - M3_PAD / 2, xs0 + trim, MET3, M3_PAD)
    assert XJ - M2_PAD / 2 - TRK / 2 >= R_M2_SP

    # ---------------------------------------------------------------- output inverters: qp / qn met1 columns
    for net, nrow, prow in (("qp", nl, pl), ("qn", nr, pr)):
        (xn_, _, fn_), = nrow.bars(net)
        for x, n, f in prow.bars(net):
            assert abs(x - xn_) < 1e-6
            mcon(x, bar_y(f, yP, 0) + MC / 2)
        mcon(xn_, bar_y(fn_, yN, 1) - MC / 2)
        vline(xn_, bar_y(fn_, yN, 1) - MC, max(bar_y(f, yP, 0) for x, n, f in prow.bars(net)) + MC, MET1, M1_STUB)
        # output exit: via onto met2 between the two output tracks, out past the cell edge (no track there)
        sgn = -1 if net == "qp" else 1
        v1(xn_, (y_lo + y_hi) / 2, li=False)
        hline((y_lo + y_hi) / 2, xn_, sgn * (x_edge + EXIT), MET2, TRK_IN)
        _pin(top, net, sgn * (x_edge + EXIT - 0.15), (y_lo + y_hi) / 2, MET2)
    # latch-NMOS dummies: outer bar tied to the shared output bar (met1 across the band)
    for nrow, d_net, o_net in ((nl, "d_outn", "outn"), (nr, "d_outp", "outp")):
        (xd, _, fd), = nrow.bars(d_net)
        xo = min((x for x, n, f in nrow.bars(o_net)), key=lambda x: abs(x - xd))
        yb = yN + fd["dy"] + (fd["fe"].bar_y[0] + fd["fe"].bar_y[1]) / 2
        for x in (xd, xo):
            mcon(x, yb)
        hline(yb, min(xd, xo), max(xd, xo), MET1, M1_STUB)
    # inverter NMOS sources -> vss rail (met1 down the side)
    for nrow in (nl, nr):
        for x, n, f in nrow.bars("vss"):
            mcon(x, bar_y(f, yN, 0) + MC / 2)
            vline(x, RAIL_W / 2, bar_y(f, yN, 0) + MC, MET1, M1_STUB)

    # ---------------------------------------------------------------- PMOS sources -> vdd rail, reset clk
    for prow in (pl, pr):
        for x, n, f in prow.bars("vdd"):
            mcon(x, bar_y(f, yP, 1) - MC / 2)
            vline(x, bar_y(f, yP, 1) - MC, y_vdd + RAIL_W / 2, MET1, M1_STUB)
        gs = prow.gates("clk", "top")
        x_out = prow.bars("xp" if prow is pl else "xn")[0][0]
        xa = min([g["x"] for g in gs] + [x_out]) - MC / 2
        hline(y_clk1, xa, max([g["x"] for g in gs] + [x_out]) + MC / 2, LI, MC)
        v1(x_out, y_clk1)
    hline(y_clk1, -xr, xr, MET2, TRK_IN)
    hline(y_clk0, -(x_edge + EXIT), xr, MET2, TRK_IN)
    for x in (-xr, xr):
        v2(x, y_clk0)
        v2(x, y_clk1)
        vline(x, y_clk0, y_clk1, MET3, M3_PAD)
    _pin(top, "clk", -(x_edge + EXIT - 0.15), y_clk0, MET2)
    _pin(top, "vss", 0.0, RAIL_W / 2, MET1)
    _pin(top, "vdd", 0.0, y_vdd + RAIL_W / 2, MET1)

    top = top.flatten()
    top.name = name
    bb = top.bbox
    info = dict(width=float(bb[1][0] - bb[0][0]), height=float(bb[1][1] - bb[0][1]),
                fingers=R["fingers"], dummies=R["dummies"])
    return top, info


def _tap_strip(top, xa, xb, yc, kind, vertical=False, margin=0.0, mcon=None):
    """Substrate (p) or n-well (n) tap strip: tap, licons, li, implant (+ mcons to a met1 rail above it).
    Horizontal from xa to xb at height yc, or vertical (vertical=True) from y = xa to xb at x = yc."""
    def rect(a0, b0, a1, b1, lay):                  # (along, across) -> layout
        if vertical:
            _poly(top, b0, a0, b1, a1, lay)
        else:
            _poly(top, a0, b0, a1, b1, lay)
    xa, xb = min(xa, xb), max(xa, xb)
    rect(xa, yc - TAP_H / 2, xb, yc + TAP_H / 2, TAP)
    rect(xa - 0.13, yc - TAP_H / 2 - 0.13, xb + 0.13, yc + TAP_H / 2 + 0.13, PSDM if kind == "p" else NSDM)
    rect(xa + 0.04, yc - TAP_LI / 2, xb - 0.04, yc + TAP_LI / 2, LI)
    n = int((xb - xa - 2 * margin - 0.24 - MC) / LICON_P) + 1     # no contacts within margin of the ends
    x0 = snap((xa + xb) / 2 - (n - 1) * LICON_P / 2)              # contacts on the 5 nm grid
    for i in range(n):
        x = x0 + i * LICON_P
        rect(x - MC / 2, yc - MC / 2, x + MC / 2, yc + MC / 2, LICON)
        if (not vertical) if mcon is None else mcon:
            rect(x - MC / 2, yc - MC / 2, x + MC / 2, yc + MC / 2, MCON)
