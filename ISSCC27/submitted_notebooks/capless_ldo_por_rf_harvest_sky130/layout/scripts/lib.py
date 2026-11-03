"""v3 design library: the notebook's v2 simulation helpers, plus a transistor-level nano-power bandgap
that replaces the ideal VREF and Iref sources.

Run inside the cac-eda container (sh run.sh python ...). All helpers from notebook cell 9 are loaded
unchanged; only `tb` is extended so P["ref"] == "bgr" swaps the ideal sources for the bandgap subcircuit.
"""
import os, math, re

exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "_nb_cell09_original.py"), encoding="utf-8").read())

_tb_ideal = tb
_ldo_ideal = ldo_subckt


def models(corner="tt", mc=False):
    """Notebook model subset, plus pfet_01v8 (the PNP model reads its junction parameters)."""
    fn = os.path.join(SIMDIR, f"models4_{corner}{'_mm' if mc else ''}.lib")
    if not os.path.exists(fn):
        with open(fn, "w") as f:
            f.write(f"* subset of sky130.lib.spice, corner {corner}\n"
                    f".param mc_mm_switch={1 if mc else 0}\n.param mc_pr_switch=0\n"
                    f".include \"{NGS}/corners/{corner}/nonfet.spice\"\n")
            for d in ("nfet_g5v0d10v5", "pfet_g5v0d10v5", "pfet_01v8", "nfet_05v0_nvt"):
                f.write(f".include \"{REF}/sky130_fd_pr__{d}__{corner}.corner.spice\"\n"
                        f".include \"{REF}/sky130_fd_pr__{d}__mismatch.corner.spice\"\n")
            f.write(f".include \"{NGS}/all.spice\"\n"
                    f".include \"{NGS}/r+c/res_typical__cap_typical.spice\"\n"
                    f".include \"{NGS}/r+c/res_typical__cap_typical__lin.spice\"\n")
    return f".include \"{fn}\"\n"

def fetm(name, d, g, s, b, model, W, L, nf=1, m=1):
    """Generic sky130 FET instance (any model name), same geometry rules as `fet`."""
    wf = W / nf
    ad = int((nf + 1) / 2) * wf * 0.29; as_ = int((nf + 2) / 2) * wf * 0.29
    pd_ = 2 * int((nf + 1) / 2) * (wf + 0.29); ps = 2 * int((nf + 2) / 2) * (wf + 0.29)
    return (f"X{name} {d} {g} {s} {b} sky130_fd_pr__{model} W={W} L={L} nf={nf} "
            f"ad={ad:.4g} as={as_:.4g} pd={pd_:.4g} ps={ps:.4g} nrd={0.29/W:.4g} nrs={0.29/W:.4g} "
            f"sa=0 sb=0 sd=0 mult={m} m={m}\n")

# --------------------------------------------------------------------------- bandgap reference
BGR0 = dict(
    ref="bgr",
    N=8,                        # Q2 : Q1 emitter ratio
    mq=1,                       # unit PNP multiplier (Q1, Q3, Q5 = mq; Q2 = N*mq)
    Rb1=640e3,                  # PTAT resistor: I = VT ln(N) / R1  (~100 nA incl. mirror offsets)
    Rb2=7.19e6,                 # output resistor: VREF = I*R2 + VBE(Q3), set for a flat TC at 1.20 V
    mpm=4, Wpm=20, Lpm=16,      # PMOS mirror unit (x mpm in parallel for matching) (thick oxide; wide -> moderate/weak inversion, long L -> rout)
    Wnn=1, Lnm=25, mn=6,        # native NMOS pair: mn x (W/L = 1/25); VGS stays > 0 up to 125 C in every corner
    kout=1,                     # output branch current = kout * I
    kib=4,                      # LDO Iref branch = kib/2 * I  (unit PMOS of half width)
    ls=1, mf=6, msk=2,          # level-shifted PMOS diode (native follower mf x 1/25, sink msk x 1/25)
    cas=1, Lcd=25,              # native cascode on MNB; its bias diode MNCD is a single 1/25 device (mn x denser)
    trim=None, nbits=5, lsb=25e3, Wsw=5,   # R2 trim (None = untrimmed R2); code 15/16 ~ nominal
    pcas=1, Lpc=2, ksc=4,       # PMOS self-cascode: bottom device W*ksc, L = Lpc (no extra bias needed)
    Wsu=0.42, Lsu=50, nsu=4,    # start-up pull-up: chain of nsu PMOS diodes VIN -> st (sub-nA when on)
    Wsn=1, Lsn=4,               # start-up release: thick NMOS, gate at VREF, source on a PNP
    Wst2=1, Lst2=1,             # start-up kick: thick NMOS that pulls pg low while st is high
    ncvr=4, Cvr_side=25, Rf=2e6,  # VREF ripple filter: Rf into 4 x (25 x 25 um) MIM ~ 5 pF to gnd
)

NVT = "nfet_05v0_nvt"


def nnat(name, d, g, s_, p, nf=None, L=None, W=None):
    """native NMOS of the pair: W = Wnn, L = Lnm, m = mn parallel devices (model bins: W 1/10, L 0.9/2/4/8/25)"""
    return fetm(name, d, g, s_, "gnd", NVT, W or p['Wnn'], L or p['Lnm'], m=nf or p['mn'])


def bgr_subckt(p):
    """Self-biased PTAT current (native NMOS pair, PNP 1:N) + VBE output branch: no op-amp, ~0.6 uA total.
    pins: vin vref iref gnd   (iref sources the LDO bias current into its NMOS diode)"""
    pnp = "sky130_fd_pr__pnp_05v5_W3p40L3p40"
    s = ".subckt bgr vin vref iref gnd\n"
    # PMOS mirror (thick oxide): MPA diode in the R1 branch; MPB feeds the native diode MNA; MPO output; MPI Iref.
    # With pcas=1 every branch gets a wide-swing cascode (gate pc), so all mirror devices see the same small Vsd.
    pd = "pd" if p.get('ls', 0) else "pg"     # with ls=1 the R1-branch PMOS diode is level-shifted
    br = [("MPA", pd, p['Wpm'], 1), ("MPB", "ng", p['Wpm'], 1), ("MPO", "vref", p['Wpm'], p['kout']),
          ("MPI", "iref", p['Wpm'] / 2 * p['kib'], 1)]   # one wide unit per mpm (shorter layout rows)
    if p.get('cas', 1):
        br.append(("MPC", "ncas", p['Wpm'], 1))
    for name, out, w, m in br:
        m = m * p.get('mpm', 1)     # parallel unit devices (matching)
        if p.get('pcas', 1):
            # self-cascode: top device (W, Lpm) in near-triode, bottom device (ksc*W, Lpc) saturated; same gate
            mid = name.lower() + "_m"
            s += fet(name, mid, "pg", "vin", "vin", "p", w, p['Lpm'], nf=math.ceil(w / 20), m=m)
            s += fet(name + "C", out, "pg", mid, "vin", "p", w * p['ksc'], p['Lpc'], nf=math.ceil(w * p['ksc'] / 20), m=m)
        else:
            s += fet(name, out, "pg", "vin", "vin", "p", w, p['Lpm'], nf=math.ceil(w / 20), m=m)
    if p.get('ls', 0):
        # level shift: native follower MNF puts the mirror gate pg ~VGS(nat) below the diode drain pd, so the
        # R1 branch keeps ~0.25 V more headroom at low VIN / cold. Sink MNSK (native copy, own PNP) biases it.
        s += fetm("MNF", "vin", pd, "pg", "gnd", NVT, p['Wnn'], p['Lnm'], m=p['mf'])
        s += fetm("MNSK", "pg", "ng", "e8", "gnd", NVT, p['Wnn'], p['Lnm'], m=p['msk'])
        s += f"XQ8 gnd gnd e8 {pnp} m={p['mq']}\n"
    # native NMOS pair: equal VGS -> VEB(Q1) = VEB(Q2) + I*R1 -> I = VT ln(N) / R1
    s += nnat("MNA", "ng", "ng", "ea", p)
    if p.get('cas', 1):
        # native cascode MNBC holds MNB's drain at ~eb + 0.1 V, independent of VIN; bias ncas from a weak
        # native diode (W = 1 um) on its own PNP, fed by mirror copy MPC.
        s += nnat("MNB", "xb", "ng", "eb", p)
        s += nnat("MNBC", pd, "ncas", "xb", p)
        s += fetm("MNCD", "ncas", "ncas", "e5", "gnd", NVT, 1, p['Lcd'])
        s += f"XQ5 gnd gnd e5 {pnp} m={p['mq']}\n"
    else:
        s += nnat("MNB", pd, "ng", "eb", p)
    s += f"XQ1 gnd gnd ea {pnp} m={p['mq']}\n"
    s += res("R1", "eb", "e2", p['Rb1'])
    s += f"XQ2 gnd gnd e2 {pnp} m={p['N'] * p['mq']}\n"
    # output: VREF = I*R2 + VBE(Q3)
    if p.get('trim') is None:
        s += res("R2", "vref", "e3", p['Rb2'])
    else:
        # one-time trim: R2 = R2fix + sum over bits k of (1 - b_k) * 2^k * LSB. Segments sit at the bottom of R2
        # (node ~VBE) so the bypass NMOS (gate at VIN for b_k = 1, at GND for b_k = 0) has VGS >= 1.2 V.
        nb = p['nbits']; code = int(p['trim'])
        s += res("R2", "vref", "t0", p['Rb2'] - (2 ** nb - 1) * p['lsb'] / 2)
        for k in range(nb):
            a, b = f"t{k}", ("e3" if k == nb - 1 else f"t{k+1}")
            s += res(f"RT{k}", a, b, p['lsb'] * 2 ** k)
            s += fet(f"MT{k}", a, ("vin" if (code >> k) & 1 else "gnd"), b, "gnd", "n", p['Wsw'], 0.5)
    s += f"XQ3 gnd gnd e3 {pnp} m={p['mq']}\n"
    # start-up: weak PMOS-diode chain pulls st up; thick NMOS MSN pulls it down once the core runs.
    # Core off -> st high -> kick MS2 pulls pg low. Core on -> st ~ 0 -> MS2 off.
    nodes = ["vin"] + [f"su{k}" for k in range(1, p['nsu'])] + ["st"]
    for k in range(p['nsu']):
        s += fet(f"MSU{k}", nodes[k + 1], nodes[k + 1], nodes[k], "vin", "p", p['Wsu'], p['Lsu'])
    # MSN gate at VREF, source on a PNP (e7): VGS ~ 0 in the stuck states (VREF ~ 0 or ~VBE), VREF - VBE once running.
    # W/L = 1/4 keeps its 125 C leakage below the chain current (2/2 never starts at ss/125 C on a slow ramp). The cost:
    # at -40 C, VREF - VBE is only ~0.45 V, so st is released slowly (VREF settles in ~8 ms at fs/-40 C).
    # Tried and rejected: gate at pd (rises with the kick itself -> premature release, core stays off after layout),
    # source at gnd (releases in the cold low-current state VREF ~ VBE), a current-mirror release (cold start at 1.8-2.2 V),
    # a native MSN (125 C slow-ramp start up to 3.7 V).
    s += fet("MSN", "st", "vref", "e7", "gnd", "n", p['Wsn'], p['Lsn'])
    s += f"XQ7 gnd gnd e7 {pnp}\n"
    s += fet("MS2", "pg", "st", "gnd", "gnd", "n", p['Wst2'], p['Lst2'])
    if p.get('lay'):
        # layout dummies at both ends of the matched rows (layout.py MATCH): PNPs with E = B = C = gnd, and mirror
        # PMOS units with every terminal at vin (off)
        s += f"XQD0 gnd gnd gnd {pnp}\nXQD1 gnd gnd gnd {pnp}\n"
        for k in range(2):
            s += fet(f"MPD{k}", "vin", "vin", "vin", "vin", "p", p['Wpm'], p['Lpm'], nf=math.ceil(p['Wpm'] / 20))
    # supply-ripple filter outside the bandgap loop: core, output branch and start-up release (MSN gate) use the raw
    # node vr; the pin vref is vr through Rf into a MIM to gnd (the LDO gate draws no DC current, so no DC error).
    # A cap directly on vr slows the release and lets the kick overshoot VREF and collapse the core when cold.
    if p.get('ncvr', 0):
        head, body = s.split("\n", 1)
        s = head + "\n" + re.sub(r"(?<=\s)vref(?=\s)", "vr", body)
        s += res("Rf", "vr", "vref", p['Rf'])
        for k in range(p['ncvr']):
            s += f"XCvr{k} vref gnd sky130_fd_pr__cap_mim_m3_1 W={p['Cvr_side']} L={p['Cvr_side']} MF=1\n"
    return s + ".ends bgr\n"


def ldo_subckt(p):
    s = _ldo_ideal(p)
    if p.get("ref") != "bgr":
        return s
    lines = [l for l in s.splitlines(keepends=True) if not l.startswith("Bref ")]
    lines[0] = ".subckt ldo vin vout fb vref gnd nb\n"
    if p.get("lay"):
        # layout view: the MIM generator allows at most 30 um per side -> split a W x W cap into k x k units
        out = []
        for l in lines:
            mm = re.match(r"(X\S+ \S+ \S+ sky130_fd_pr__cap_mim_m3_1) W=(\S+) L=(\S+) MF=(\S+)", l)
            if mm and float(mm.group(2)) > 30:
                w, k = float(mm.group(2)), math.ceil(float(mm.group(2)) / 30)
                l = f"{mm.group(1)} W={w/k:g} L={w/k:g} MF={int(mm.group(4))*k*k}\n"
            out.append(l)
        lines = out
    return "".join(lines)


def tb(P, body, control, corner="tt", temp=27, mc=False, seed=None, por=False):
    if P.get("ref") != "bgr":
        return _tb_ideal(P, body, control, corner, temp, mc, seed, por)
    body = body.replace(" 0 ldo\n", " 0 nbx ldo\n")
    s = "* testbench (bandgap reference)\n" + (f".option seed={seed}\n" if seed is not None else "")
    # gmin 1e-14 (not 1e-15): the last gmin step is singular at the nA-biased bandgap nodes; 1e-14 S x 1 V = 10 fA.
    # rshunt 1e13 ohm (0.1 pA/V on every node) lets Newton find the operating state without the transient-op fallback.
    s += models(corner, mc) + f".temp {temp}\n.option gmin=1e-14 reltol=1e-4 rshunt=1e13\n"
    s += ldo_subckt(P) + (por_subckt(P) if por else "") + bgr_subckt(P) + "Xbgr vin vref nbx 0 bgr\n" + body
    # DC analyses: steer the bandgap to its operating state. The node voltages come from a short power-up transient
    # of the bandgap alone at the same corner / temperature / VIN (cached), because they move a lot with T.
    m = re.search(r"^Vin vin 0 (?:dc )?([0-9.]+)", body, re.M)
    v = float(m.group(1)) if m else 2.5
    s += bgr_nodeset(P, corner, temp, v)
    return s + ".control\n" + control + "\n.endc\n.end\n"


def bgr_alone(p, vin=2.5, corner="tt", temp=27, mc=False, seed=None, ctl=None, tag_extra=""):
    """Bandgap with a dummy 1 V load on iref (stands in for the LDO's NMOS diode)."""
    tag = _t(p, "bgr", vin, corner, temp, seed, tag_extra)
    body = f"Vin vin 0 {vin}\nXbgr vin vref iref 0 bgr\nViref iref 0 1.0\n"
    ctl = ctl or ("op\nlet vref=v(vref)\nlet ibg=-i(Vin)\nlet iref=i(Viref)\nlet pg=v(xbgr.pg)\nlet ng=v(xbgr.ng)\n"
                  "print vref ibg iref pg ng")
    s = "* bgr\n" + (f".option seed={seed}\n" if seed is not None else "")
    s += models(corner, mc) + f".temp {temp}\n.option gmin=1e-15 reltol=1e-4\n" + bgr_subckt(p) + body
    s += ".control\n" + ctl + "\n.endc\n.end\n"
    return spice(s, tag)


def bgr_tran(p, vin=2.5, corner="tt", temp=27, mc=False, seed=None, t_ramp=1e-3, t_hold=6e-3, tag_extra=""):
    """Power-up transient (VIN 0 -> vin in t_ramp, hold): settled VREF, LDO Iref and supply current.
    The bandgap's high-impedance nodes make the transient (not a DC operating point) the trustworthy answer."""
    tag = _t(p, "bgrt", vin, corner, temp, seed, tag_extra)
    body = (f"Vin vin 0 PWL(0 0 {t_ramp} {vin})\nXbgr vin vref iref 0 bgr\n"
            "Vir iref ird 0\nXdio ird ird 0 0 sky130_fd_pr__nfet_g5v0d10v5 W=2 L=4 nf=1\n")   # LDO-like NMOS diode load
    te = t_ramp + t_hold
    ctl = (f"tran 2u {te} 0 5u\nmeas tran vref find v(vref) at={te*0.999}\n"
           f"meas tran iref find i(Vir) at={te*0.999}\nmeas tran itot find i(Vin) at={te*0.999}\n"
           f"meas tran vmid find v(vref) at={te*0.6:.6g}")
    s = "* bgr tran\n" + (f".option seed={seed}\n" if seed is not None else "")
    s += models(corner, mc) + f".temp {temp}\n.option gmin=1e-15 reltol=1e-4\n" + bgr_subckt(p) + body
    s += ".control\n" + ctl + "\n.endc\n.end\n"
    try:
        r = spice(s, tag)
    except RuntimeError:
        r = {}
    if "vref" not in r:
        # "Transient solution failed" at the very start (seen for a few cold Monte Carlo seeds): retry with the
        # gear integrator and a 10 TOhm shunt on every node, as the top-level post-layout runs use
        s = s.replace(".option gmin=1e-15 reltol=1e-4\n", ".option gmin=1e-15 reltol=1e-4 method=gear rshunt=1e13\n")
        r = spice(s, tag + "_g")
    return dict(vref=r["vref"], iref=r["iref"], itot=-r["itot"], drift=r["vref"] - r.get("vmid", r["vref"]))


_NS = {}
_NS_NODES = ["vref", "xbgr.pg", "xbgr.pd", "xbgr.ng", "xbgr.ea", "xbgr.eb", "xbgr.xb", "xbgr.ncas", "xbgr.st", "xbgr.e3"]


def bgr_nodeset(P, corner, temp, vin):
    """.nodeset line for the bandgap nodes, from a short power-up transient of the bandgap alone (cached)."""
    key = (repr(sorted((k, v) for k, v in P.items() if k in BGR0)), corner, temp, round(vin, 3))
    if key not in _NS:
        p = {k: P[k] for k in BGR0}
        body = (f"Vin vin 0 PWL(0 0 1m {vin})\nXbgr vin vref iref 0 bgr\nVir iref ird 0\n"
                "Xdio ird ird 0 0 sky130_fd_pr__nfet_g5v0d10v5 W=2 L=4 nf=1\n")
        ctl = "tran 2u 4m 0 5u\n" + "".join(f"meas tran n{k} find v({n}) at=3.99m\n" for k, n in enumerate(_NS_NODES))
        net = ("* ns\n" + models(corner) + f".temp {temp}\n.option gmin=1e-15 reltol=1e-4\n" + bgr_subckt(p) + body +
               ".control\n" + ctl + "\n.endc\n.end\n")
        r = spice(net, _t(p, "ns", corner, temp, vin))
        _NS[key] = ".nodeset " + " ".join(f"v({n})={r[f'n{k}']:.4f}" for k, n in enumerate(_NS_NODES)) + "\n"
    return _NS[key]

