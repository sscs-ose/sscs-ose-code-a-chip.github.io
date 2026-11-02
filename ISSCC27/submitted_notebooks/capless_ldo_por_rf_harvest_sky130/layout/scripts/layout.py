"""Scripted layout of the v3 chip (LDO + POR + bandgap) in SKY130, generated from the same subcircuits the
simulations use.  Flow:  python layout.py gen   -> device cells (Magic gencell)
                         python layout.py place -> top cell ldo_top.mag (placement + routing) + schematic.spice
Routing scheme (all scripted, no manual edits):
  * every device terminal gets a via stack at its label point (mcon if the terminal is li-only, via1, via2)
  * metal3 riser: source/drain/body/resistor/BJT/cap terminals go DOWN, gates go UP
  * between device rows: two sub-channels of horizontal metal4 tracks (one track per net per sub-channel)
  * left of the rows: one vertical metal3 trunk per net, via3 to each of its tracks
"""
import os, re, sys, math, json, subprocess
from lib import *

UM = 200                      # Magic units per um (magscale 1 2 -> 0.005 um)
HERE = os.path.dirname(os.path.abspath(__file__))
MAG = os.path.join(HERE, "mag")
TRIM_CODE = 16                # trim bits hard-wired in this layout (metal option; fuses in a product)

P = dict(P0, **BGR0)
P["trim"] = TRIM_CODE
P["lay"] = 1

TOP_PINS = ["vin", "vout", "rstn", "gnd"]


# --------------------------------------------------------------------------- netlist -> device list
def _parse_subckt(text, prefix, pinmap):
    lines = text.strip().splitlines()
    pins = lines[0].split()[2:]
    devs = []
    for ln in lines[1:]:
        if not ln.startswith("X"):
            continue
        t = ln.split()
        mi = next(i for i, x in enumerate(t) if x.startswith("sky130_fd_pr__"))
        nodes = []
        for n in t[1:mi]:
            if n in pins:
                nodes.append(pinmap[n])
            elif n in ("0", "gnd"):
                nodes.append("gnd")
            else:
                nodes.append(f"{prefix}_{n}")
        par = {}
        for kv in t[mi + 1:]:
            if "=" in kv:
                k, v = kv.split("=", 1)
                par[k.lower()] = v
        devs.append(dict(name=f"{prefix}_{t[0][1:]}", model=t[mi].replace("sky130_fd_pr__", ""), nodes=nodes, par=par))
    return devs


def flatten(P):
    blocks = [("ldo", ldo_subckt(P), dict(vin="vin", vout="vout", fb="vout", vref="vref", gnd="gnd", nb="nbx")),
              ("por", por_subckt(P), dict(vin="vin", vout="vout", rstn="rstn", pg="por_pg", gnd="gnd")),
              ("bgr", bgr_subckt(P), dict(vin="vin", vref="vref", iref="nbx", gnd="gnd"))]
    devs = []
    for pre, txt, pm in blocks:
        devs += _parse_subckt(txt, pre, pm)
    return devs


def f(x):
    return float(x)


# --------------------------------------------------------------------------- device -> layout plan
RES_SEG = 60.0          # max snake segment length (um)
RES_BEND = 0.73         # extra extracted length per snake bend (um), measured on the generator


def plan(d):
    """Decide the gencell parameters and the LVS view (model + params) of one schematic device."""
    m, p = d["model"], d["par"]
    if m in ("nfet_g5v0d10v5", "pfet_g5v0d10v5", "nfet_05v0_nvt"):
        W, L, nf, mm = f(p["w"]), f(p["l"]), int(f(p.get("nf", 1))), int(f(p.get("m", 1)))
        if mm > 1 and (L < 2 or mm > 4):   # short gates or many units: fingers instead of a tall stack
            nf, mm, W = nf * mm, 1, W * mm
        wf = W / nf
        while wf > 20:                # keep fingers <= 20 um
            nf *= 2; wf = W / nf
        gen = dict(w=round(wf, 3), l=L, m=mm, nf=nf, topc=1, botc=0, full_metal=1, guard=1)
        lvs = dict(W=round(W, 3), L=L, nf=nf, m=mm)
        return dict(kind="mos", gen=gen, lvs=lvs, ports=["D", "G", "S", "B"])
    if m == "res_xhigh_po_0p35":
        L = f(p["l"])
        nx = max(1, math.ceil(L / RES_SEG))
        lseg = round((L - (nx - 1) * RES_BEND) / nx / 0.02) * 0.02     # on a 0.02 um grid (off-grid lengths break DRC)
        lseg = round(lseg, 2)
        Lext = round(nx * lseg + (nx - 1) * RES_BEND, 3)
        return dict(kind="res", gen=dict(w=0.35, l=lseg, m=1, nx=nx, snake=1 if nx > 1 else 0, full_metal=1, guard=1),
                    lvs=dict(L=Lext), ports=["R2", "R1", "B"])
    if m == "cap_mim_m3_1":
        W, L, MF = f(p["w"]), f(p["l"]), int(f(p.get("mf", 1)))
        return dict(kind="cap", gen=dict(w=W, l=L, nx=1, ny=1), lvs=dict(W=W, L=L, MF=MF), ports=["C1", "C2"], mult=MF)
    if m == "pnp_05v5_W3p40L3p40":
        return dict(kind="pnp", gen={}, lvs=dict(m=int(f(p.get("m", 1)))), ports=["Collector", "Base", "Emitter"],
                    mult=int(f(p.get("m", 1))))
    raise ValueError(m)


def gen_key(d, pl):
    return d["model"] + "|" + json.dumps(pl["gen"], sort_keys=True)


# --------------------------------------------------------------------------- pass 1: device cells
def cmd_gen():
    devs = flatten(P)
    keys = {}
    for d in devs:
        pl = plan(d)
        if pl["kind"] == "pnp":
            continue
        keys.setdefault(gen_key(d, pl), (d["model"], pl["gen"]))
    tcl = [f"cd /w/mag", "load gencells -force"]
    for i, (k, (model, g)) in enumerate(sorted(keys.items())):
        args = " ".join(f"{a} {b}" for a, b in g.items())
        tcl += [f"box {i*300}um 0 {i*300}um 0", f"magic::gencell sky130::sky130_fd_pr__{model} c{i} {args}"]
    tcl += ["writeall force", "quit -noprompt"]
    with open(os.path.join(MAG, "gencells.tcl"), "w") as fh:
        fh.write("\n".join(tcl) + "\n")
    with open(os.path.join(MAG, "gencells_keys.json"), "w") as fh:
        json.dump({f"c{i}": k for i, (k, _) in enumerate(sorted(keys.items()))}, fh, indent=0)
    print(len(keys), "unique device cells")


def read_mag(path):
    rects, labels, cur = {}, [], None
    scale = 1
    for ln in open(path):
        t = ln.split()
        if not t:
            continue
        if t[0] == "magscale":
            scale = int(t[2]) / int(t[1])
        elif t[0] == "<<":
            cur = t[1]
        elif t[0] == "rect" and cur not in ("checkpaint", "labels", "properties"):
            rects.setdefault(cur, []).append(tuple(int(x) for x in t[1:5]))
        elif t[0] in ("rlabel", "flabel"):
            if t[0] == "rlabel":
                lay, x1, y1, x2, y2, name = t[1], *map(int, t[2:6]), t[-1]
            else:
                lay, x1, y1, x2, y2, name = t[1], *map(int, t[3:7]), t[-1]
            labels.append(dict(layer=lay, x=(x1 + x2) / 2, y=(y1 + y2) / 2, name=name))
    k = 2 / scale        # convert to magscale-2 units
    rects = {l: [tuple(v * k for v in r) for r in rs] for l, rs in rects.items()}
    for lb in labels:
        lb["x"] *= k; lb["y"] *= k
    allr = [r for rs in rects.values() for r in rs]
    bbox = (min(r[0] for r in allr), min(r[1] for r in allr), max(r[2] for r in allr), max(r[3] for r in allr))
    return dict(rects=rects, labels=labels, bbox=bbox)


def load_cells():
    keys = json.load(open(os.path.join(MAG, "gencells_keys.json")))
    uses = {}
    for ln in open(os.path.join(MAG, "gencells.mag")):
        t = ln.split()
        if t and t[0] == "use":
            uses[t[2]] = t[1]
    cells = {}
    for inst, key in keys.items():
        cname = uses[inst]
        cells[key] = dict(name=cname, **read_mag(os.path.join(MAG, cname + ".mag")))
    pnp_path = "/opt/pdk/sky130A/libs.ref/sky130_fd_pr/mag/sky130_fd_pr__rf_pnp_05v5_W3p40L3p40.mag"
    cells["pnp"] = dict(name="sky130_fd_pr__rf_pnp_05v5_W3p40L3p40", lib=True, **read_mag(pnp_path))
    return cells


# --------------------------------------------------------------------------- geometry helpers (um)
class Geo:
    SPACE = {"metal1": 0.14, "metal2": 0.14, "metal3": 0.30, "metal4": 0.30, "via3": 0.20, "locali": 0.17}

    def __init__(self):
        self.r = {}                      # layer -> list of (x1, y1, x2, y2, net) in um
        self.labels = []                 # (layer, x, y, name, port index)

    def rect(self, layer, x1, y1, x2, y2, net=None):
        self.r.setdefault(layer, []).append((min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2), net))

    def box(self, layer, x, y, ax, ay, net=None):
        self.rect(layer, x - ax / 2, y - ay / 2, x + ax / 2, y + ay / 2, net)

    def stack(self, x, y, start, net, narrow=False):
        """via stack at (x, y) from `start` ('locali' or 'metal1') up to metal3. narrow: 0.26-wide m1/m2 pads
        (gate contacts squeezed between source/drain strips)."""
        a = 0.26 if narrow else 0.40
        if start == "locali":
            self.box("locali", x, y, 0.17, 0.17, net); self.box("viali", x, y, 0.17, 0.17, net)
        self.box("metal1", x, y, a, 0.40, net); self.box("via1", x, y, 0.26, 0.26, net)
        self.box("metal2", x, y, 0.40, 0.40, net); self.box("via2", x, y, 0.28, 0.28, net)
        self.box("metal3", x, y, 0.44, 0.60, net)          # 0.44 x 0.60 > metal3 min area 0.24 um^2

    def v3(self, x, y, net):
        self.box("metal3", x, y, 0.44, 0.60, net); self.box("via3", x, y, 0.32, 0.32, net)
        self.box("metal4", x, y, 0.60, 0.46, net)          # elongated along the track (min area)

    def check(self):
        """net-aware spacing check of the routing geometry (different nets closer than the metal rule)"""
        bad = []
        for layer, rule in self.SPACE.items():
            rs = [r for r in self.r.get(layer, []) if r[4] is not None]
            grid = {}
            for i, r in enumerate(rs):
                for gx in range(int(r[0] // 5), int(r[2] // 5) + 1):
                    for gy in range(int(r[1] // 5), int(r[3] // 5) + 1):
                        grid.setdefault((gx, gy), []).append(i)
            seen = set()
            for ids in grid.values():
                for a in range(len(ids)):
                    for b in range(a + 1, len(ids)):
                        i, j = ids[a], ids[b]
                        if (i, j) in seen:
                            continue
                        seen.add((i, j))
                        p, q = rs[i], rs[j]
                        if p[4] == q[4]:
                            continue
                        dx = max(q[0] - p[2], p[0] - q[2]); dy = max(q[1] - p[3], p[1] - q[3])
                        if max(dx, dy) < rule:
                            bad.append((layer, p[4], q[4], [round(v, 2) for v in p[:4]], [round(v, 2) for v in q[:4]]))
        return bad


PWR = {"vin": 3.0, "vout": 3.0, "gnd": 3.0}   # wide tracks / trunks for the supply and output nets


def tw(n):
    return PWR.get(n, 0.46)


def alloc(nets, start, sign=-1):
    """stack tracks (or trunks) of per-net width, 0.5 um apart; returns centre per net and the total extent"""
    pos, cur = {}, start
    for n in nets:
        w = tw(n)
        pos[n] = cur + sign * (0.5 + w / 2)
        cur = pos[n] + sign * (w / 2)
    return pos, abs(cur - start) + 0.5


W3, W4 = 0.44, 0.46          # riser / trunk (metal3) and track (metal4) widths
TPITCH = 0.90                # track pitch inside a channel
RPITCH = 0.85                # minimum centre distance between risers of different nets
GAP = 3.0                    # spacing between device cells
ROWW = 300.0                 # max row width (um)

PNP_PORTS = {"Emitter": (3.39, 3.39, "metal1"), "Base": (1.20, 1.125, "locali"), "Collector": (5.60, 0.38, "locali")}


def device_terms(d, pl, cell):
    """Terminals of one placed device cell (cell coordinates, um): list of dicts(net, x, y, start, dir, kind)."""
    nodes = d["nodes"]
    out = []
    if pl["kind"] == "pnp":
        idx = {"Collector": 0, "Base": 1, "Emitter": 2}
        for nm, (x, y, st) in PNP_PORTS.items():
            out.append(dict(net=nodes[idx[nm]], x=x, y=y, start=st, dir=-1, kind=nm))
        return out
    R = cell["rects"]

    def has(layer, x, y):
        X, Y = x * UM, y * UM
        return any(r[0] <= X <= r[2] and r[1] <= Y <= r[3] for r in R.get(layer, []))

    for lb in cell["labels"]:
        nm = lb["name"][0] if pl["kind"] == "mos" else lb["name"]     # MOS labels: D0, G1, D0_3 ...
        x, y = lb["x"] / UM, lb["y"] / UM
        if pl["kind"] == "mos":
            net = nodes[{"D": 0, "G": 1, "S": 2, "B": 3}[nm]]
            dirn = +1 if nm == "G" else -1
        elif pl["kind"] == "res":
            net = nodes[{"R2": 0, "R1": 1, "B": 2}[nm]]
            dirn = -1
        elif pl["kind"] == "cap":
            net = nodes[{"C1": 0, "C2": 1}[nm]]
            dirn = -1
        start = "metal1" if has("metal1", x, y) else ("locali" if has("locali", x, y) else None)
        if pl["kind"] == "cap":
            start = "cap"
        if pl["kind"] == "res" or (pl["kind"] == "mos" and nm in ("D", "S", "G")):
            start = "metal1"        # contacts (viali) imply metal1 here; never add li on a device terminal
        out.append(dict(net=net, x=x, y=y, start=start, dir=dirn, kind=nm, layer=lb["layer"]))
    # multi-finger MOS: the generator leaves the last source/drain strip of each unit unlabeled -> find every
    # diffusion-contact strip and give unlabeled ones the type implied by the D/S alternation along the unit
    if pl["kind"] == "mos":
        strips = [r for l in ("mvpdiffc", "mvndiffc", "pdiffc", "ndiffc") for r in R.get(l, [])]
        sd = [o for o in out if o["kind"] in ("D", "S")]
        for r in strips:
            cx, cy = (r[0] + r[2]) / 2 / UM, (r[1] + r[3]) / 2 / UM
            if any(abs(o["x"] - cx) < 0.05 and r[1] / UM - 0.01 <= o["y"] <= r[3] / UM + 0.01 for o in sd):
                continue
            row = sorted([o for o in sd if r[1] / UM - 0.01 <= o["y"] <= r[3] / UM + 0.01], key=lambda o: abs(o["x"] - cx))
            if not row:
                continue
            nb = row[0]
            steps = round(abs(nb["x"] - cx) / max(0.01, abs(row[1]["x"] - row[0]["x"]) if len(row) > 1 else 1))
            kind = nb["kind"] if steps % 2 == 0 else ("S" if nb["kind"] == "D" else "D")
            out.append(dict(net=nodes[{"D": 0, "S": 2}[kind]], x=cx, y=nb["y"], start="metal1", dir=-1, kind=kind))
            sd.append(out[-1])
    # body / guard-ring ties: contact the ring at its bottom-left corner (mcon) and leave the cell with a metal1
    # stub, so the body riser runs in the gap between cells, clear of every source/drain riser
    li = R.get("locali", [])
    if pl["kind"] == "res":
        # resistor guard ring = p-substrate tap: it is the substrate (= gnd through the NMOS taps) already, and a
        # metal tie on it disturbs the generated RPM implant (rpm.1) -> no explicit tie
        out = [o for o in out if o["kind"] != "B"]
    for t in [o for o in out if o["kind"] == "B" and li]:
        xl = min(r[0] for r in li) / UM            # outer edge of the ring
        xr = min(r[2] for r in li if r[0] / UM <= xl + 0.01) / UM
        xc = (xl + xr) / 2                         # centre of the left ring strip
        t.update(x=xc, corner=True, xout=cell["bbox"][0] / UM - 1.0)
    # a down-riser that would run over another net's terminal below it goes up instead (straight resistors)
    for t in out:
        if pl["kind"] == "res" and t["dir"] == -1 and not t.get("corner") and any(
                o is not t and o["net"] != t["net"] and o["dir"] == -1 and not o["kind"] == "B"
                and abs(o["x"] - t["x"]) < RPITCH
                and o["y"] < t["y"] - 0.5 for o in out):
            t["dir"] = +1
    # drop duplicate body labels (one tie per cell is enough)
    seen, uniq = set(), []
    for o in out:
        if o.get("corner"):
            if o["net"] in seen:
                continue
            seen.add(o["net"])
        uniq.append(o)
    return uniq


def cmd_place():
    cells = load_cells()
    devs = flatten(P)
    units = []        # one entry per placed cell
    for d in devs:
        pl = plan(d)
        key = "pnp" if pl["kind"] == "pnp" else gen_key(d, pl)
        for k in range(pl.get("mult", 1)):
            units.append(dict(dev=d, pl=pl, cell=cells[key], uname=f"{d['name']}_{k}" if pl.get("mult", 1) > 1 else d["name"]))
    # order: by block, big items first inside each block, caps last
    order = {"ldo": 0, "bgr": 1, "por": 2}
    units.sort(key=lambda u: (u["pl"]["kind"] == "cap", order[u["dev"]["name"].split("_")[0]],
                              -(u["cell"]["bbox"][3] - u["cell"]["bbox"][1])))
    # rows
    rows, cur, w = [], [], 0.0
    for u in units:
        bw = (u["cell"]["bbox"][2] - u["cell"]["bbox"][0]) / UM + GAP + (3.0 if u["pl"]["kind"] in ("cap", "res") else 0)
        if cur and (w + bw > ROWW or (u["pl"]["kind"] == "cap") != (cur[-1]["pl"]["kind"] == "cap")):
            rows.append(cur); cur, w = [], 0.0
        cur.append(u); w += bw
    rows.append(cur)
    # terminals per unit (cell coordinates)
    for u in units:
        u["terms"] = device_terms(u["dev"], u["pl"], u["cell"])
    # x placement inside rows; nets per channel
    nets_all = sorted({t["net"] for u in units for t in u["terms"]})
    tx, tw_all = alloc(nets_all, 1.5, sign=+1)       # trunk x per net
    XT0 = 1.5 + tw_all + 3.0                          # rows start right of the trunk region
    for row in rows:
        x = XT0
        prev = None
        for u in row:
            bb = [v / UM for v in u["cell"]["bbox"]]
            if u["pl"]["kind"] in ("cap", "res") or (prev is not None and prev["pl"]["kind"] == "res"):
                x += 3.0                                # resistors: keep the RPM implants well apart
            u["ox"] = x - bb[0]
            x += bb[2] - bb[0] + GAP
            prev = u
    # vertical layout: [up-channel] [row] [down-channel] per row, top to bottom
    g = Geo()
    y = 0.0
    chan_tracks = []          # (channel id, net, y, xmin, xmax)
    uses = []
    for ri, row in enumerate(rows):
        up_nets = sorted({t["net"] for u in row for t in u["terms"] if t["dir"] == +1})
        dn_nets = sorted({t["net"] for u in row for t in u["terms"] if t["dir"] == -1})
        up_y, h_up = alloc(up_nets, y - 0.3)
        h_up += 0.3
        y -= h_up
        top = y
        hmax = max((u["cell"]["bbox"][3] - u["cell"]["bbox"][1]) / UM for u in row)
        for u in row:
            bb = [v / UM for v in u["cell"]["bbox"]]
            u["oy"] = top - 1.5 - bb[3]               # align cell tops 1.5 um below the up-channel
        y = top - 1.5 - hmax - 1.5
        dn_y, h_dn = alloc(dn_nets, y - 0.3)
        y -= h_dn + 0.3
        # routing for this row
        span = {}
        for u in row:
            uses.append(u)
            for t in u["terms"]:
                net = t["net"]
                X, Y = u["ox"] + t["x"], u["oy"] + t["y"]
                ty = up_y[net] if t["dir"] == +1 else dn_y[net]
                if t["start"] == "cap":
                    if t["kind"] == "C2":                       # bottom plate: the cell already has m3 here
                        rx = X                                  # (no via: it would overlap the child via3)
                    else:
                        # top plate: m4 stub to the left, outside the bottom plate; it stops 0.3 um before the
                        # mimcap contact so parent paint never overlaps the child's cap layers
                        R = u["cell"]["rects"]
                        xl = min(r[0] for r in R.get("metal3", [])) / UM + u["ox"] - 1.6
                        xc = min(r[0] for r in R.get("mimcapcontact", [(t["x"] * UM,) * 4])) / UM + u["ox"]
                        g.rect("metal4", xl - 0.3, Y - 0.23, xc, Y + 0.23, net)
                        g.v3(xl, Y, net)
                        rx = xl
                    g.rect("metal3", rx - W3 / 2, min(Y, ty), rx + W3 / 2, max(Y, ty), net)
                    g.v3(rx, ty, net)
                    span.setdefault(("dn", net), []).append(rx)
                    continue
                if t["kind"] == "G":
                    # gate: narrow m1 bridge 0.45 um up, away from the source/drain strips, then the stack
                    g.rect("metal1", X - 0.13, Y, X + 0.13, Y + 0.45, net)
                    Y += 0.45
                    g.stack(X, Y, "metal1", net, narrow=True)
                elif t.get("corner"):
                    # body: mcon on the ring corner, metal1 stub out of the cell, stack + riser outside
                    g.box("locali", X, Y, 0.17, 0.17, net); g.box("viali", X, Y, 0.17, 0.17, net)
                    g.box("metal1", X, Y, 0.29, 0.29, net)
                    Xo = u["ox"] + t["xout"]
                    g.rect("metal1", Xo, Y - 0.145, X + 0.145, Y + 0.145, net)
                    X = Xo
                    g.stack(X, Y, "metal1", net)
                else:
                    g.stack(X, Y, t["start"] or "metal1", net)
                g.rect("metal3", X - W3 / 2, min(Y, ty), X + W3 / 2, max(Y, ty), net)
                g.v3(X, ty, net)
                span.setdefault(("up" if t["dir"] == +1 else "dn", net), []).append(X)
        for (side, n), xs in span.items():
            ty = up_y[n] if side == "up" else dn_y[n]
            chan_tracks.append((ri, side, n, ty, max(xs)))
    ybot = y
    # trunks + tracks
    ys = {}
    for ri, side, n, ty, xmax in chan_tracks:
        g.rect("metal4", tx[n] - max(0.3, tw(n) / 2), ty - tw(n) / 2, xmax + 0.3, ty + tw(n) / 2, n)
        g.v3(tx[n], ty, n)
        ys.setdefault(n, []).append(ty)
    for n, yy in ys.items():
        top = 0.5 if n in TOP_PINS else max(max(yy), min(yy) + 0.8)      # >= 0.8 um long (metal3 min area)
        g.rect("metal3", tx[n] - max(W3, tw(n)) / 2, min(yy) - tw(n) / 2, tx[n] + max(W3, tw(n)) / 2, top, n)
    bad = g.check()
    print(f"routing self-check: {len(bad)} spacing conflicts", bad[:12])
    for i, n in enumerate(TOP_PINS):
        g.labels.append(("metal3", tx[n], 0.3, n, i + 1))
    write_top(g, uses, (0, ybot - 1, max(u["ox"] for u in uses) + 50, 1.5))
    with open(os.path.join(MAG, "placement.json"), "w") as fh:
        json.dump([dict(uname=u["uname"], cell=u["cell"]["name"], kind=u["pl"]["kind"], ox=u["ox"], oy=u["oy"],
                        bbox=[v / UM for v in u["cell"]["bbox"]],
                        terms=[dict(net=t["net"], x=t["x"], y=t["y"], kind=t["kind"], dir=t["dir"]) for t in u["terms"]])
                   for u in uses], fh)
    write_schematic(devs)
    print(f"rows {len(rows)}, cells {len(uses)}, nets {len(nets_all)}, size {max(u['ox'] for u in uses)+40:.0f} x {-ybot:.0f} um")


def write_top(g, uses, bbox):
    def I(v):
        return int(round(v * UM))
    lines = ["magic", "tech sky130A", "magscale 1 2", "timestamp 0"]
    for u in uses:
        c = u["cell"]
        lines.append(f"use {c['name']}  {u['uname']}" + (" $PDKPATH/libs.ref/sky130_fd_pr/mag" if c.get("lib") else ""))
        lines.append(f"transform 1 0 {I(u['ox'])} 0 1 {I(u['oy'])}")
        b = c["bbox"]
        lines.append(f"box {int(b[0])} {int(b[1])} {int(b[2])} {int(b[3])}")
    for layer in ("locali", "viali", "metal1", "via1", "metal2", "via2", "metal3", "via3", "metal4"):
        rs = g.r.get(layer, [])
        if rs:
            lines.append(f"<< {layer} >>")
            lines += [f"rect {I(r[0])} {I(r[1])} {I(r[2])} {I(r[3])}" for r in rs]
    lines.append("<< labels >>")
    for layer, x, y, name, port in g.labels:
        lines.append(f"flabel {layer} {I(x)-10} {I(y)-10} {I(x)+10} {I(y)+10} 0 FreeSans 400 0 0 0 {name}")
        lines.append(f"port {port} nsew")
    lines.append("<< properties >>")
    lines.append(f"string FIXED_BBOX {I(bbox[0])} {I(bbox[1])} {I(bbox[2])} {I(bbox[3])}")
    # URPM mask hints: the PDK's generated URPM around a 0.35 um poly resistor is only 0.75 um wide (urpm.1a needs
    # 1.27 um). Cover every resistor with one rectangle: poly-res + 0.2 um, notches filled, >= 1.27 um wide.
    hints = []
    for u in uses:
        if u["pl"]["kind"] != "res":
            continue
        R = u["cell"]["rects"]
        rr = R.get("xpolyres", []) + R.get("xpolycontact", [])
        x1, y1 = min(r[0] for r in rr) / UM - 0.2, min(r[1] for r in rr) / UM - 0.2
        x2, y2 = max(r[2] for r in rr) / UM + 0.2, max(r[3] for r in rr) / UM + 0.2
        if x2 - x1 < 1.27:
            cx = (x1 + x2) / 2; x1, x2 = cx - 0.64, cx + 0.64
        hints += [I(u["ox"] + x1), I(u["oy"] + y1), I(u["ox"] + x2), I(u["oy"] + y2)]
    if hints:
        lines.append("string MASKHINTS_URPM " + " ".join(map(str, hints)))
    # the same hint, in local coordinates, inside each resistor cell (Magic's hierarchical DRC reads the cell's own)
    done = set()
    for u in uses:
        c = u["cell"]
        if u["pl"]["kind"] != "res" or c["name"] in done:
            continue
        done.add(c["name"])
        R = c["rects"]; rr = R.get("xpolyres", []) + R.get("xpolycontact", [])
        x1, y1 = min(r[0] for r in rr) / UM - 0.2, min(r[1] for r in rr) / UM - 0.2
        x2, y2 = max(r[2] for r in rr) / UM + 0.2, max(r[3] for r in rr) / UM + 0.2
        if x2 - x1 < 1.27:
            cx = (x1 + x2) / 2; x1, x2 = cx - 0.64, cx + 0.64
        path = os.path.join(MAG, c["name"] + ".mag")
        txt = [l for l in open(path).read().splitlines() if not l.startswith("string MASKHINTS_URPM")]
        k = txt.index("<< properties >>") + 1
        txt.insert(k, f"string MASKHINTS_URPM {I(x1)} {I(y1)} {I(x2)} {I(y2)}")
        open(path, "w").write("\n".join(txt) + "\n")
    lines.append("<< end >>")
    with open(os.path.join(MAG, "ldo_top.mag"), "w") as fh:
        fh.write("\n".join(lines) + "\n")


def write_schematic(devs):
    """Schematic netlist in the layout's device view (same fingers / units), for LVS."""
    s = [".subckt ldo_top " + " ".join(TOP_PINS)]
    for d in devs:
        pl = plan(d); n = d["nodes"]; v = pl["lvs"]
        if pl["kind"] == "mos":
            s.append(f"X{d['name']} {' '.join(n)} sky130_fd_pr__{d['model']} W={v['W']} L={v['L']} nf={v['nf']} m={v['m']}")
        elif pl["kind"] == "res":
            s.append(f"X{d['name']} {n[0]} {n[1]} {n[2]} sky130_fd_pr__res_xhigh_po_0p35 L={v['L']}")
        elif pl["kind"] == "cap":
            for k in range(v["MF"]):
                s.append(f"X{d['name']}_{k} {n[0]} {n[1]} sky130_fd_pr__cap_mim_m3_1 W={v['W']} L={v['L']}")
        elif pl["kind"] == "pnp":
            for k in range(v["m"]):
                s.append(f"X{d['name']}_{k} {n[0]} {n[1]} {n[2]} sky130_fd_pr__pnp_05v5_W3p40L3p40")
    s.append(".ends ldo_top")
    with open(os.path.join(MAG, "schematic.spice"), "w") as fh:
        fh.write("\n".join(s) + "\n")


if __name__ == "__main__":
    {"gen": cmd_gen, "place": cmd_place}[sys.argv[1]]()
