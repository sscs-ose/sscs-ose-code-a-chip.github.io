import os, re, subprocess, shutil, hashlib, itertools, concurrent.futures as _futures
import numpy as np, pandas as pd
import matplotlib
import matplotlib.pyplot as plt
plt.rcParams.update({"figure.dpi": 90, "axes.titlesize": 11, "font.size": 9})

# ---------------------------------------------------------------- ngspice runner
PDK_ROOT = os.environ["PDK_ROOT"]
NGS = f"{PDK_ROOT}/sky130A/libs.tech/ngspice"
REF = f"{PDK_ROOT}/sky130A/libs.ref/sky130_fd_pr/spice"
SIMDIR = os.path.abspath("sim_work")
os.makedirs(SIMDIR, exist_ok=True)
with open(os.path.join(SIMDIR, ".spiceinit"), "w") as f:     # same settings as the PDK's spinit
    f.write("set ngbehavior=hsa\nset skywaterpdk\nset ng_nomodcheck\nset num_threads=1\n"
            "option noinit\noption klu\nset wr_singlescale\nset wr_vecnames\n")
_meas = re.compile(r"^\s*([A-Za-z_][^\s=]*)\s*=\s*([-+]?[0-9.]+(?:[eE][-+]?\d+)?)(?=\s|$)", re.M)

def spice(net, tag, timeout=900):
    """Write a netlist, run `ngspice -b`, return {name: value} of every printed/measured scalar."""
    path = os.path.join(SIMDIR, f"{tag}.spice")
    with open(path, "w") as f:
        f.write(net)
    r = subprocess.run(["ngspice", "-b", path], cwd=SIMDIR, capture_output=True, text=True, timeout=timeout)
    out = r.stdout + r.stderr
    with open(os.path.join(SIMDIR, f"{tag}.log"), "w") as f:
        f.write(out)
    if r.returncode != 0 or "fatal" in out.lower():
        raise RuntimeError(f"ngspice failed for {tag}:\n" + out[-3000:])
    return {k.lower(): float(v) for k, v in _meas.findall(out)}

def wrdata(tag):
    return pd.read_csv(os.path.join(SIMDIR, f"{tag}.dat"), sep=r"\s+")

def pmap(fn, items, workers=None):
    """Run independent simulations in parallel (each is its own ngspice process)."""
    with _futures.ThreadPoolExecutor(workers or max(2, os.cpu_count() or 2)) as ex:
        return list(ex.map(fn, items))

def models(corner="tt", mc=False):
    """Light-weight equivalent of `.lib sky130.lib.spice <corner>[_mm]` for the devices used here."""
    fn = os.path.join(SIMDIR, f"models_{corner}{'_mm' if mc else ''}.lib")
    if not os.path.exists(fn):
        with open(fn, "w") as f:
            f.write(f"* subset of sky130.lib.spice, corner {corner}\n"
                    f".param mc_mm_switch={1 if mc else 0}\n.param mc_pr_switch=0\n"
                    f".include \"{NGS}/corners/{corner}/nonfet.spice\"\n")
            for d in ("nfet_g5v0d10v5", "pfet_g5v0d10v5"):
                f.write(f".include \"{REF}/sky130_fd_pr__{d}__{corner}.corner.spice\"\n"
                        f".include \"{REF}/sky130_fd_pr__{d}__mismatch.corner.spice\"\n")
            f.write(f".include \"{NGS}/all.spice\"\n"
                    f".include \"{NGS}/r+c/res_typical__cap_typical.spice\"\n"
                    f".include \"{NGS}/r+c/res_typical__cap_typical__lin.spice\"\n")
    return f".include \"{fn}\"\n"

def char(kind, L, temp=27, corner="tt", vds=1.0, W=5):
    """DC sweep of one thick-oxide FET: returns |VGS|, |Id|, gm (numerical derivative)."""
    tag = f"char_{kind}_{W}_{L}_{temp}_{corner}".replace(".", "p").replace("-", "m")
    m = f"sky130_fd_pr__{kind}fet_g5v0d10v5"
    sgn = 1 if kind == "n" else -1
    net = (f"* char\n{models(corner)}.temp {temp}\nXM1 d g 0 0 {m} W={W} L={L} nf=1\n"
           f"Vd d 0 {sgn*vds}\nVg g 0 0\n.control\ndc Vg 0 {sgn*2.5} {sgn*0.005}\n"
           f"let id=abs(i(Vd))\nwrdata {tag}.dat id\n.endc\n.end\n")
    spice(net, tag); d = wrdata(tag)
    v = np.abs(d.iloc[:, 0].values); i = d["id"].values
    return v, i, np.gradient(i, v)

# ---------------------------------------------------------------- circuit generators
def fet(name, d, g, s, b, kind, W, L, nf=1, m=1):
    """sky130 thick-oxide (g5v0d10v5) FET instance with xschem-style diffusion geometry."""
    wf = W / nf
    ad = int((nf + 1) / 2) * wf * 0.29; as_ = int((nf + 2) / 2) * wf * 0.29
    pd_ = 2 * int((nf + 1) / 2) * (wf + 0.29); ps = 2 * int((nf + 2) / 2) * (wf + 0.29)
    return (f"X{name} {d} {g} {s} {b} sky130_fd_pr__{kind}fet_g5v0d10v5 W={W} L={L} nf={nf} "
            f"ad={ad:.4g} as={as_:.4g} pd={pd_:.4g} ps={ps:.4g} nrd={0.29/W:.4g} nrs={0.29/W:.4g} "
            f"sa=0 sb=0 sd=0 mult={m} m={m}\n")

def res(name, a, b, R):
    """xhigh_po poly resistor, W = 0.35 um (~2 kohm/sq); length computed from the target value."""
    L = R / 2000 * (0.35 - 0.056) + 0.0592
    return f"X{name} {a} {b} 0 sky130_fd_pr__res_xhigh_po_0p35 L={L:.4g} mult=1\n"

P0 = dict(
    Ib=250e-9,                  # reference current (ideal; from a nano-power reference in a full chip)
    Win=8, Lin=2,               # NMOS input pair (weak inversion)
    Wld=16, Lld=4,              # PMOS mirror load (v1: 4/4; wider in v2 for headroom at VIN = 1.8 V with the 1 uA tail)
    Wb=2, Lb=4,                 # bias diode / unit current-source device
    mt=4,                       # tail = 4 x Ib = 1 uA (v1: 0.5 uA)
    mbl=20,                     # bleeder = 20 x Ib = 5 uA (minimum load)
    Wp=400, Lp=0.5, nfp=40,     # pass PMOS
    Ws=0.84, Ls=0.5,            # adaptive-bias sense PMOS (1/476 of pass)
    Wa=1, La=4, ma=1,           # adaptive-bias NMOS mirror
    Cc_side=30, Cc_mf=1,        # direct Miller cap, 30 x 30 um MIM (~1.8 pF)
    # --- v2: class-AB common-gate current-buffer coupling (transient enhancement + Ahuja-type compensation)
    mx=3,                       # buffer bias Ix = mx * Ib = 0.75 uA (one stack VIN -> MPT -> MPX -> vg -> MNX -> MNS -> GND)
    Cf_side=55,                 # Cfp = Cfn = 55 x 55 um MIM (~6 pF each), VOUT -> buffer sources
    Wpb=4, Lpb=4,               # PMOS bias diode MPB2 / current source MPT / buffer MPX (unit; long L for output resistance)
    Wnx=4, Lnx=1,               # NMOS buffer MNX (unit), gate at VREF
    Rsh=1.4e6,                  # level shift: vbp = VIN - VSG - Ib*Rsh  -> tx ~ VIN - 0.35 V
    Cff_side=32,                # supply feed-forward VIN -> sx (~2 pF): injects C*dVIN/dt into vg (PSRR)
    Cbp_side=22,                # vbp filter cap (~1 pF): PMOS-buffer bias does not follow fast VIN ripple
    R1=1.9e6, R2=3.2e6, R3=1.28e6, Rpu=4e6,    # POR divider / pull-up
    Wd=0.7, Ld=20,              # POR detector (near-ZTC current density)
    Winv=0.42, Linv=4,          # POR inverters
)
# the first version of this design (before the transient-enhancement update), kept for before/after comparisons
P_V1 = dict(P0, mt=2, Wld=4, mbl=30, Cc_side=70, mx=0, Cff_side=0, Cbp_side=0)

def ldo_subckt(p):
    s = ".subckt ldo vin vout fb vref gnd\n"
    s += f"Bref vin nb I={p['Ib']}*(1-exp(-max(V(vin)-V(nb),0)/0.05))\n"   # ideal Iref with compliance
    s += fet("MNB", "nb", "nb", "gnd", "gnd", "n", p['Wb'], p['Lb'])
    s += fet("MN5", "tail", "nb", "gnd", "gnd", "n", p['Wb'], p['Lb'], m=p['mt'])
    s += fet("MN1", "n1", "fb", "tail", "gnd", "n", p['Win'], p['Lin'])
    s += fet("MN2", "vg", "vref", "tail", "gnd", "n", p['Win'], p['Lin'])
    s += fet("MP3", "n1", "n1", "vin", "vin", "p", p['Wld'], p['Lld'])
    s += fet("MP4", "vg", "n1", "vin", "vin", "p", p['Wld'], p['Lld'])
    s += fet("MPP", "vout", "vg", "vin", "vin", "p", p['Wp'], p['Lp'], nf=p['nfp'])
    s += fet("MPS", "na", "vg", "vin", "vin", "p", p['Ws'], p['Ls'])
    s += fet("MNA", "na", "na", "gnd", "gnd", "n", p['Wa'], p['La'])
    s += fet("MNA2", "tail", "na", "gnd", "gnd", "n", p['Wa'], p['La'], m=p['ma'])
    s += fet("MNBL", "vout", "nb", "gnd", "gnd", "n", p['Wb'], p['Lb'], m=p['mbl'])
    s += f"XCc vg vout sky130_fd_pr__cap_mim_m3_1 W={p['Cc_side']} L={p['Cc_side']} MF={p['Cc_mf']}\n"
    if p.get('mx', 0) > 0:
        # bias for the PMOS buffer gate: diode MPB2 (Ib) + level-shift resistor Rsh -> vbp, sink MNB3 (Ib)
        s += fet("MPB2", "pa", "pa", "vin", "vin", "p", p['Wpb'], p['Lpb'])
        s += f"XRsh pa vbp gnd sky130_fd_pr__res_xhigh_po_0p35 L={p['Rsh']/2000*(0.35-0.056)+0.0592:.4g} mult=1\n"
        s += fet("MNB3", "vbp", "nb", "gnd", "gnd", "n", p['Wb'], p['Lb'])
        # class-AB current-buffer stack (static current Ix cancels at vg)
        s += fet("MPT", "tx", "pa", "vin", "vin", "p", p['Wpb'], p['Lpb'], m=p['mx'])
        s += fet("MPX", "vg", "vbp", "tx", "vin", "p", p['Wpb'], p['Lpb'], m=p['mx'])
        s += fet("MNX", "vg", "vref", "sx", "gnd", "n", p['Wnx'], p['Lnx'], m=p['mx'])
        s += fet("MNS", "sx", "nb", "gnd", "gnd", "n", p['Wb'], p['Lb'], m=p['mx'])
        s += f"XCfp vout tx sky130_fd_pr__cap_mim_m3_1 W={p['Cf_side']} L={p['Cf_side']} MF=1\n"
        s += f"XCfn vout sx sky130_fd_pr__cap_mim_m3_1 W={p['Cf_side']} L={p['Cf_side']} MF=1\n"
        if p.get('Cff_side', 0) > 0:
            s += f"XCff vin sx sky130_fd_pr__cap_mim_m3_1 W={p['Cff_side']} L={p['Cff_side']} MF=1\n"
        if p.get('Cbp_side', 0) > 0:
            s += f"XCbp vbp gnd sky130_fd_pr__cap_mim_m3_1 W={p['Cbp_side']} L={p['Cbp_side']} MF=1\n"
    return s + ".ends ldo\n"

def mim_area(p):
    """total MIM area of the LDO in um^2"""
    a = p['Cc_side']**2 * p['Cc_mf']
    if p.get('mx', 0) > 0:
        a += 2 * p['Cf_side']**2 + p.get('Cff_side', 0)**2 + p.get('Cbp_side', 0)**2
    return a

def por_subckt(p):
    s = ".subckt por vin vout rstn pg gnd\n"
    s += res("R1", "vin", "div", p['R1']) + res("R2", "div", "dm", p['R2']) + res("R3", "dm", "gnd", p['R3'])
    s += fet("MH", "dm", "pgb", "gnd", "gnd", "n", 1, 0.5)                 # hysteresis switch
    s += res("Rpu", "vin", "x", p['Rpu'])
    s += fet("MD", "x", "div", "gnd", "gnd", "n", p['Wd'], p['Ld'])         # threshold detector
    s += fet("MI1P", "pg", "x", "vin", "vin", "p", 2*p['Winv'], p['Linv'])  # INV1 (long L: low crowbar)
    s += fet("MI1N", "pg", "x", "gnd", "gnd", "n", p['Winv'], p['Linv'])
    s += fet("MI2P", "pgb", "pg", "vin", "vin", "p", 2*p['Winv'], 0.5)      # INV2
    s += fet("MI2N", "pgb", "pg", "gnd", "gnd", "n", p['Winv'], 0.5)
    s += fet("MI3P", "rstn", "pgb", "vout", "vout", "p", 2*p['Winv'], 0.5)  # INV3, VOUT domain
    s += fet("MI3N", "rstn", "pgb", "gnd", "gnd", "n", p['Winv'], 0.5)
    return s + ".ends por\n"

VREF_SRC = "Bvref vref 0 V=1.2/(1+exp(-(V(vin)-1.4)/0.04))\n"   # ideal 1.2 V reference, valid above ~1.5 V

def tb(P, body, control, corner="tt", temp=27, mc=False, seed=None, por=False):
    s = "* testbench\n" + (f".option seed={seed}\n" if seed is not None else "")
    s += models(corner, mc) + f".temp {temp}\n.option gmin=1e-15 reltol=1e-4\n"
    s += ldo_subckt(P) + (por_subckt(P) if por else "") + VREF_SRC + body
    return s + ".control\n" + control + "\n.endc\n.end\n"

# ---------------------------------------------------------------- analyses
def _t(P, *a):
    h = hashlib.md5(repr(sorted(P.items())).encode()).hexdigest()[:6]
    return (h + "_" + "_".join(str(x) for x in a)).replace("-", "m").replace(".", "p")

def op_point(P, vin=2.5, il=0.0, corner="tt", temp=27, mc=False, seed=None):
    tag = _t(P, "op", vin, il, corner, temp, seed)
    body = f"Vin vin 0 {vin}\nXldo vin vout vout vref 0 ldo\nCL vout 0 100p\nIl vout 0 {il}\n"
    ctl = "op\nlet iq=-i(Vin)-%g\nlet vout=v(vout)\nlet vg=v(xldo.vg)\nprint vout vg iq" % il
    r = spice(tb(P, body, ctl, corner, temp, mc, seed), tag)
    return dict(vout=r["vout"], vg=r["vg"], iq=r["iq"])

def dc_line(P, il=0.0, corner="tt", temp=27):
    """VIN sweep 1.2 -> 3.6 V with a resistive load drawing `il` at 1.2 V (well-defined in dropout)."""
    tag = _t(P, "line", il, corner, temp)
    rl = f"Rl vout 0 {1.2/il:.6g}\n" if il > 0 else ""
    body = f"Vin vin 0 2.5\nXldo vin vout vout vref 0 ldo\n{rl}"
    iload = f"-v(vout)/{1.2/il:.6g}" if il > 0 else ""
    ctl = f"dc Vin 1.2 3.6 0.005\nlet iq=-i(Vin){iload}\nwrdata {tag}.dat v(vout) iq"
    spice(tb(P, body, ctl, corner, temp), tag)
    d = wrdata(tag); d.columns = ["vin", "vout", "iq"]; return d

def dc_load(P, vin=2.5, corner="tt", temp=27, i1=1.5e-3):
    tag = _t(P, "load", vin, corner, temp)
    body = f"Vin vin 0 {vin}\nXldo vin vout vout vref 0 ldo\nIl vout 0 0\n"
    ctl = f"dc Il 0 {i1} {i1/300}\nwrdata {tag}.dat v(vout)"
    spice(tb(P, body, ctl, corner, temp), tag)
    d = wrdata(tag); d.columns = ["il", "vout"]; return d

def _pm(f, mag, ph):
    ph = np.unwrap(np.deg2rad(ph)) * 180 / np.pi
    ph = ph - 360 * np.round(ph[0] / 360)
    k = np.where(mag < 0)[0]
    if len(k) == 0 or k[0] == 0:
        return np.nan, np.nan, ph
    k = k[0]; lf = np.log10(f)
    fu = 10 ** np.interp(0, [mag[k], mag[k - 1]], [lf[k], lf[k - 1]])
    return fu, 180 + np.interp(np.log10(fu), lf[k - 1:k + 1], ph[k - 1:k + 1]), ph

def loop(P, vin=2.5, il=0.0, cl=100e-12, corner="tt", temp=27):
    """Loop gain T = -v(vout)/v(fb), loop opened at the error-amplifier gate (capacitive node):
    DC kept by unity buffer + 1e9 s low-pass, AC injected in series."""
    tag = _t(P, "lg", vin, il, cl, corner, temp)
    body = (f"Vin vin 0 {vin}\nXldo vin vout fb vref 0 ldo\nCL vout 0 {cl}\nIl vout 0 {il}\n"
            "Ebuf vb 0 vout 0 1\nRlp vb fbdc 1G\nClp fbdc 0 1\nVinj fb fbdc dc 0 ac 1\n")
    ctl = f"ac dec 40 0.1 1G\nlet t=-v(vout)/v(fb)\nlet mag=db(t)\nlet ph=180/pi*cph(t)\nwrdata {tag}.dat mag ph"
    spice(tb(P, body, ctl, corner, temp), tag)
    d = wrdata(tag); f = d.iloc[:, 0].values; mag = d["mag"].values
    fu, pm, ph = _pm(f, mag, d["ph"].values)
    return dict(f=f, mag=mag, ph=ph, a0=mag[0], fu=fu, pm=pm)

def psrr(P, vin=2.5, il=0.0, cl=100e-12, corner="tt", temp=27):
    tag = _t(P, "psrr", vin, il, cl, corner, temp)
    body = f"Vin vin 0 dc {vin} ac 1\nXldo vin vout vout vref 0 ldo\nCL vout 0 {cl}\nIl vout 0 {il}\n"
    ctl = f"ac dec 20 1 100Meg\nlet psrr=-db(v(vout))\nwrdata {tag}.dat psrr"
    spice(tb(P, body, ctl, corner, temp), tag)
    d = wrdata(tag); d.columns = ["f", "psrr"]; return d

def tran_load(P, vin=2.5, ilo=0.0, ihi=1e-3, tr=100e-9, cl=100e-12, corner="tt", temp=27,
              t1=20e-6, t2=60e-6, tstop=100e-6):
    tag = _t(P, "tload", vin, ilo, ihi, tr, cl, corner, temp)
    body = (f"Vin vin 0 {vin}\nXldo vin vout vout vref 0 ldo\nCL vout 0 {cl}\n"
            f"Il vout 0 PWL(0 {ilo} {t1} {ilo} {t1+tr} {ihi} {t2} {ihi} {t2+tr} {ilo})\n")
    ctl = (f"tran 5n {tstop} 0 20n\nmeas tran vmin min v(vout) from={t1} to={t2}\n"
           f"meas tran vmax max v(vout) from={t2} to={tstop}\nmeas tran vpre avg v(vout) from={t1-5e-6} to={t1}\n"
           f"linearize v(vout)\nwrdata {tag}.dat v(vout)")
    r = spice(tb(P, body, ctl, corner, temp), tag)
    d = wrdata(tag); d.columns = ["t", "vout"]; return d, r

def tran_line(P, v0=2.0, v1=3.0, tr=1e-6, il=0.5e-3, cl=100e-12, corner="tt", temp=27,
              t1=20e-6, t2=60e-6, tstop=100e-6):
    tag = _t(P, "tline", v0, v1, tr, il, cl, corner, temp)
    body = (f"Vin vin 0 PWL(0 {v0} {t1} {v0} {t1+tr} {v1} {t2} {v1} {t2+tr} {v0})\n"
            f"Xldo vin vout vout vref 0 ldo\nCL vout 0 {cl}\nIl vout 0 {il}\n")
    ctl = (f"tran 5n {tstop} 0 20n\nmeas tran vmax max v(vout) from={t1} to={t2}\n"
           f"meas tran vmin min v(vout) from={t2} to={tstop}\nmeas tran vpre avg v(vout) from={t1-5e-6} to={t1}\n"
           f"linearize v(vin) v(vout)\nwrdata {tag}.dat v(vin) v(vout)")
    r = spice(tb(P, body, ctl, corner, temp), tag)
    d = wrdata(tag); d.columns = ["t", "vin", "vout"]; return d, r

def por_sweep(P, corner="tt", temp=27, mc=False, seed=None, vpk=3.3, tramp=2e-3):
    """Slow triangular VIN ramp 0 -> vpk -> 0. V_on / V_off = VIN where RST_N toggles."""
    tag = _t(P, "por", corner, temp, seed, tramp)
    body = (f"Vin vin 0 PWL(0 0 {tramp} {vpk} {2*tramp} 0)\nXldo vin vout vout vref 0 ldo\nCL vout 0 100p\n"
            "Vam vin vinp 0\nXpor vinp vout rstn pg 0 por\nCrst rstn 0 50f\n")
    ctl = (f"tran {tramp/4000:.4g} {2*tramp} 0 {tramp/4000:.4g}\nlet iin=i(Vam)\n"
           f"linearize v(vin) v(vout) v(pg) v(rstn) iin\nwrdata {tag}.dat v(vin) v(vout) v(pg) v(rstn) iin")
    r = spice(tb(P, body, ctl, corner, temp, mc, seed, por=True), tag)
    d = wrdata(tag); d.columns = ["t", "vin", "vout", "pg", "rstn", "iin"]
    up = (d.t < tramp) & (d.vin > 1.2); dn = d.t > tramp
    good = d.rstn > np.maximum(0.5 * d.vout, 0.3)      # RST_N high (and not just numerical noise near 0 V)
    k1 = np.where(up & good)[0]; k2 = np.where(dn & ~good)[0]
    r["von"] = d.vin[k1[0]] if len(k1) else np.nan
    r["voff"] = d.vin[k2[0]] if len(k2) else np.nan
    return d, r

def system_startup(P, iharv=300e-6, cst=47e-9, iload=1e-3, corner="tt", temp=27, tstop=1.6e-3):
    """Harvester (current source) -> C_st with 3.3 V soft clamp -> LDO + POR -> 1 mA core enabled by RST_N
    (1 us RC on the enable models the clock start-up)."""
    tag = _t(P, "sys", iharv, cst, iload, corner, temp)
    body = (f"Ih 0 vin {iharv}\nCst vin 0 {cst}\nBclamp vin 0 I=1e-3*ln(1+exp((V(vin)-3.3)/0.02))\n"
            "Xldo vin vout vout vref 0 ldo\nCL vout 0 100p\nXpor vin vout rstn pg 0 por\n"
            "Ren rstn en 1Meg\nCen en 0 1p\n"
            f"Bcore vout 0 I={iload}*0.5*(1+tanh((V(en)-0.6)/0.03))*(1-exp(-max(V(vout),0)/0.1))\n"
            ".ic v(vin)=0 v(vout)=0\n")
    ctl = f"tran 20n {tstop} 0 50n uic\nlinearize v(vin) v(vout) v(rstn) v(en)\nwrdata {tag}.dat v(vin) v(vout) v(rstn) v(en)"
    r = spice(tb(P, body, ctl, corner, temp, por=True), tag)
    d = wrdata(tag); d.columns = ["t", "vin", "vout", "rstn", "en"]
    d["iload"] = iload * 0.5 * (1 + np.tanh((d.en - 0.6) / 0.03)) * (1 - np.exp(-np.maximum(d.vout, 0) / 0.1))
    return d, r

def stress_check(P, conditions=((3.6, 0.0), (3.6, 1e-3), (1.9, 0.0), (1.0, 0.0))):
    """Operating-point voltage stress on every FET of the LDO + POR."""
    sub = {"ldo": (ldo_subckt(P), {"vin": "vin", "vout": "vout", "fb": "vout", "vref": "vref", "gnd": "0"}),
           "por": (por_subckt(P), {"vin": "vin", "vout": "vout", "rstn": "rstn", "pg": "pg", "gnd": "0"})}
    rows = {}
    for vin, il in conditions:
        tag = _t(P, "stress", vin, il)
        body = (f"Vin vin 0 {vin}\nXldo vin vout vout vref 0 ldo\nCL vout 0 100p\nIl vout 0 {il}\n"
                "Xpor vin vout rstn pg 0 por\n")
        r = spice(tb(P, body, "op\nprint all", por=True), tag)
        V = lambda inst, net: 0.0 if sub[inst][1].get(net, net) == "0" else \
            r.get(sub[inst][1][net] if net in sub[inst][1] else f"x{inst}.{net}", np.nan)
        for inst, (txt, _) in sub.items():
            for line in txt.splitlines():
                if not line.startswith("XM"):
                    continue
                t = line.split(); dev, (d, g, s, b), model = t[0][1:], t[1:5], t[5]
                vd, vg, vs, vb = (V(inst, n) for n in (d, g, s, b))
                w = max(abs(vg - vs), abs(vd - vs), abs(vg - vd), abs(vg - vb))   # oxide + channel stress
                key = (inst, dev)
                if key not in rows or w > rows[key]["worst_V"]:
                    rows[key] = dict(block=inst, device=dev, model=model.replace("sky130_fd_pr__", ""),
                                     worst_V=w, at=f"VIN={vin} V, IL={il*1e3:g} mA",
                                     VGS=abs(vg - vs), VDS=abs(vd - vs))
    return pd.DataFrame(rows.values())

def small_step(P, il=0.0, di=None, cl=100e-12, vin=2.5, corner="tt", temp=27):
    """Small load step il -> il+di (100 ns edge). Returns waveform and overshoot of the recovery in % of the
    initial deviation (a second-order loop with PM 45/60/75 deg rings by roughly 25/10/2 %)."""
    di = di if di is not None else max(0.1 * il, 2e-6)
    tag = _t(P, "sstep", il, di, cl, vin, corner, temp)
    body = (f"Vin vin 0 {vin}\nXldo vin vout vout vref 0 ldo\nCL vout 0 {cl}\n"
            f"Il vout 0 PWL(0 {il} 20u {il} 20.1u {il+di})\n")
    ctl = f"tran 2n 60u 0 10n\nlinearize v(vout)\nwrdata {tag}.dat v(vout)"
    spice(tb(P, body, ctl, corner, temp), tag)
    d = wrdata(tag); d.columns = ["t", "vout"]
    v0 = d.vout[(d.t > 15e-6) & (d.t < 20e-6)].mean(); vf = d.vout[d.t > 55e-6].mean()
    a = d[d.t > 20e-6]; kmin = a.vout.idxmin(); dip = vf - a.vout[kmin]
    after = a[a.t > a.t[kmin]]; over = after.vout.max() - vf
    return d, dict(dip_mV=dip * 1e3, overshoot_pct=100 * over / dip if dip > 0 else np.nan)

def psrr_band(P, il=0.0, f1=1e5, f2=1e6, corner="tt", temp=27, vin=2.5):
    d = psrr(P, vin, il, corner=corner, temp=temp); m = (d.f >= f1) & (d.f <= f2)
    return d.psrr[m].min()