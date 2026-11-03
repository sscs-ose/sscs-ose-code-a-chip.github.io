"""Post-layout loop gain of the LDO inside ldo_top (extracted netlist, real bandgap), over PVT, load and C_L.

The loop is broken at the gate of the error-amplifier input MN1 (a MOS gate, so a plain voltage injection is exact):
in a copy of the extracted netlist that gate gets its own port `fb`. Each point first runs the power-up transient
(fb tied to vout), takes every node voltage at the end as a .nodeset, so the operating point lands on the running
state of the bandgap, then runs op + ac with a 1 GH inductor vout -> fb and the AC source coupled into fb.
T = -v(vout) / v(fb).   usage: python pl_loop.py <view: pex|sch> [nproc | post]
"""
import sys, re
import postlayout as pl
from lib import *

VIEW = sys.argv[1] if len(sys.argv) > 1 else "pex"
SRC = pl.VIEWS[VIEW]
LOOP = SRC.replace(".spice", "_loop.spice")


def make_loop_netlist():
    s = open(SRC).read()
    head = re.search(r"^\.subckt ldo_top vin vout rstn gnd\s*$", s, re.M)
    s = s[:head.start()] + ".subckt ldo_top vin vout rstn gnd fb" + s[head.end():]
    if VIEW == "pex":
        old = "Xldo_MN1 gnd ldo_MP4/G ldo_MN2/S vout "
        assert s.count(old) == 1
        s = s.replace(old, "Xldo_MN1 gnd ldo_MP4/G ldo_MN2/S fb ")
    else:
        old = "Xldo_MN1 ldo_n1 vout ldo_tail gnd "
        assert s.count(old) == 1
        s = s.replace(old, "Xldo_MN1 ldo_n1 fb ldo_tail gnd ")
    open(LOOP, "w").write(s)


def read_raw_last(path):
    """last point of every voltage vector in an ngspice ASCII rawfile"""
    lines = open(path).read().split("\n")
    nv = int(next(l for l in lines if l.startswith("No. Variables:")).split(":")[1])
    iv = lines.index("Variables:")
    names = [lines[iv + 1 + k].split()[1] for k in range(nv)]
    ival = lines.index("Values:")
    vals = [l.split()[-1] for l in lines[ival + 1:] if l.strip()]
    last = vals[-nv:]
    return {n: float(x) for n, x in zip(names, last) if n.startswith("v(") or "(" not in n}


def loop(corner, temp, vin, il, cl):
    tag = f"loop_{VIEW}_{corner}_{temp}_{vin}_{il}_{cl:g}"
    head = (models(corner) + f".temp {temp}\n.option gmin=1e-14 reltol=1e-4 rshunt=1e13 method=gear\n"
            f".include \"{os.path.abspath(LOOP)}\"\n")
    # 1) power-up transient, loop closed
    tr = (f"* {tag} tran\n" + head + f"Vin vin 0 PWL(0 0 1m {vin})\nXtop vin vout rstn 0 fb ldo_top\nVfb vout fb 0\n"
          f"CL vout 0 {cl}\nIl vout 0 {il}\nCrst rstn 0 50f\n"
          f".control\nset filetype=ascii\ntran 20n 6m 5.99m 2u uic\nmeas tran vo find v(vout) at=5.995m\n"
          f"write {tag}_tr.raw\n.endc\n.end\n")          # only the last 10 us is stored
    vo = spice(tr, tag + "_tr", timeout=3600)["vo"]
    v = read_raw_last(os.path.join(SIMDIR, f"{tag}_tr.raw"))
    ns = "".join(f".nodeset {k}={x:.6g}\n" for k, x in v.items()
                 if k.startswith("v(") and k not in ("v(vin)",) and "#" not in k)
    # 2) op + ac, loop broken at the MN1 gate
    ac = (f"* {tag} ac\n" + head + f"Vin vin 0 {vin}\nXtop vin vout rstn 0 fb ldo_top\n"
          f"Lb vout fb 1G\nCb fb vac 1\nVac vac 0 0 AC 1\nCL vout 0 {cl}\nIl vout 0 {il}\nCrst rstn 0 50f\n" + ns +
          ".control\nop\nprint v(vout)\nac dec 40 1 1e9\nlet tre = real(-v(vout)/v(fb))\nlet tim = imag(-v(vout)/v(fb))\n"
          f"set wr_singlescale\nset wr_vecnames\nwrdata {tag}.dat tre tim\n.endc\n.end\n")
    r = spice(ac, tag + "_ac", timeout=3600)
    return dict(corner=corner, T=temp, vin=vin, il_mA=il * 1e3, cl_pF=cl * 1e12, vout_tran=vo,
                vout_op=r.get("v(vout)", np.nan), **margins(tag))


def margins(tag):
    """DC gain, UGF, phase and gain margin from the stored AC sweep of T"""
    d = wrdata(tag)
    f = d.iloc[:, 0].values
    T = d.tre.values + 1j * d.tim.values
    mag = 20 * np.log10(np.abs(T))
    ph = np.unwrap(np.angle(T)) * 180 / np.pi           # 0 deg at DC for negative feedback
    ugf = pm = gm = np.nan
    k = np.where((mag[:-1] > 0) & (mag[1:] <= 0))[0]
    ku = len(ph) - 1
    if len(k):
        ku = k = k[0]; a = mag[k] / (mag[k] - mag[k + 1])
        ugf = f[k] * (f[k + 1] / f[k]) ** a
        pm = (180 + ph[k] + a * (ph[k + 1] - ph[k]) + 180) % 360 - 180      # modulo 360 (see `doublet`)
    # a sharp low-frequency pole-zero doublet turns the unwrapped phase by +360 deg below the UGF at a few cold, 1 mA
    # points; the Bode margins are then not a clean stability measure there (step response instead: pl_ss_cold.py)
    doublet = bool(np.max(ph[: ku + 1]) > 180)
    phm = ph - 360 if doublet else ph
    j = np.where((phm[:-1] > -180) & (phm[1:] <= -180))[0]
    if len(j):
        j = j[0]; gm = -(mag[j] + (mag[j + 1] - mag[j]) * (-180 - phm[j]) / (phm[j + 1] - phm[j]))
    return dict(a0_dB=mag[0], ugf_kHz=ugf / 1e3, pm_deg=pm, gm_dB=gm, doublet=doublet)


if __name__ == "__main__" and len(sys.argv) > 2 and sys.argv[2] == "post":
    # recompute the margins from the stored AC sweeps (no new simulation)
    df = pd.read_csv(f"postlayout_loop_{VIEW}.csv")
    for i, r in df.iterrows():
        m = margins(f"loop_{VIEW}_{r.corner}_{r['T']}_{r.vin}_{r.il_mA / 1e3}_{r.cl_pF * 1e-12:g}")
        for key, val in m.items():
            df.loc[i, key] = val
    df.to_csv(f"postlayout_loop_{VIEW}.csv", index=False)
    print(df.round(3).to_string(index=False))
elif __name__ == "__main__":
    make_loop_netlist()
    pts = [(c, T, 2.5, il, cl) for c in ("tt", "ss", "ff", "sf", "fs") for T in (-40, 27, 125)
           for il in (0.0, 1e-3) for cl in (10e-12, 100e-12)]
    pts += [(c, T, 1.8, il, 100e-12) for c in ("tt", "ss", "sf") for T in (-40, 125) for il in (0.0, 1e-3)]
    def one(a):
        try:
            return loop(*a)
        except Exception as e:
            c, T, v, il, cl = a
            return dict(corner=c, T=T, vin=v, il_mA=il * 1e3, cl_pF=cl * 1e12, err=str(e).strip().splitlines()[-1][:150])
    df = pd.DataFrame(pmap(one, pts, workers=int(sys.argv[2]) if len(sys.argv) > 2 else None))
    df.to_csv(f"postlayout_loop_{VIEW}.csv", index=False)
    pd.set_option("display.width", 220)
    print(df.round(3).to_string(index=False))
