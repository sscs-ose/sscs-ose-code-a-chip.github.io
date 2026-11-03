"""PDK characterization with ngspice: every number the sizing step needs comes from here.

* Pelgrom coefficient A_VT of nfet/pfet (many mismatch instances in one netlist)
* on-resistance x width of the transmission gate and of the DAC drivers
* MIM capacitance per area and per perimeter
* MIM matching coefficient (read from the PDK model card)
* comparator offset distribution (after sizing; many comparator instances)
"""

import json
from pathlib import Path

import numpy as np

from . import netlist as nl
from .pdk import NFET, PFET, TG_FLAVORS, lib_line, mim, mim_matching_pct_um, mos
from .spice import read_print, read_wrdata, run, run_many

AVT_GEOMS = [(2.0, 0.5), (4.0, 1.0)]   # (W, L) in um
# switches are sized for the worst on-resistance over these (corner, temp, vdd scale) conditions
RON_WORST_CASES = [("ss", -40.0, 1.0), ("ss", 125.0, 1.0), ("tt", 27.0, 0.9)]
N_MC = 200                              # instances per geometry
# off-state leakage of the switches that hold the floating top plate is worst at these hot, fast corners
LEAK_CASES = [("ff", 125.0, 1.0), ("fs", 125.0, 1.0)]
LEAK_STEPS = 10                         # plate offsets Vref / 2^(k+1) from Vcm, k = 0 .. LEAK_STEPS - 1


def _avt_netlist(corner, temp, vdd):
    lines = [f"* A_VT extraction", lib_line(corner, mismatch=True), f".temp {temp}",
             f"Vdd vdd 0 {vdd}"]
    for g, (w, l) in enumerate(AVT_GEOMS):
        i_bias = 1e-6 * w / l           # moderate inversion
        for k in range(N_MC):
            lines += [mos(f"N{g}_{k}", f"gn{g}_{k}", f"gn{g}_{k}", "0", "0", NFET, w, l),
                      f"In{g}_{k} vdd gn{g}_{k} {i_bias:.4g}",
                      mos(f"P{g}_{k}", f"gp{g}_{k}", f"gp{g}_{k}", "vdd", "vdd", PFET, w, l),
                      f"Ip{g}_{k} gp{g}_{k} 0 {i_bias:.4g}"]
    lines += [".control", "op", "print all > op.txt", "quit", ".endc", ".end"]
    return "\n".join(lines)


def _ron_netlist(corner, temp, vdd):
    """Small-signal on-resistance vs. signal level for Wn = 1 um devices (TG: Wp = 2 Wn)."""
    L = 0.15
    tgs = []
    for fl, (nm, ln, pm, lp) in TG_FLAVORS.items():
        tgs += [f"Vt_{fl} b_{fl} a 0.005", mos(f"Tn_{fl}", "a", "vdd", f"b_{fl}", "0", nm, 1, ln),
                mos(f"Tp_{fl}", "a", "0", f"b_{fl}", "vdd", pm, 2, lp)]
    return "\n".join([
        "* switch on-resistance", lib_line(corner), f".temp {temp}",
        f"Vdd vdd 0 {vdd}", "Vin a 0 0", *tgs,
        # NMOS driver (gate = vdd) and PMOS driver (gate = 0), source tied to rail
        "Vn bn 0 0.005", mos("Dn", "bn", "vdd", "0", "0", NFET, 1, L),
        "Vp bp vdd -0.005", mos("Dp", "bp", "0", "vdd", "vdd", PFET, 1, L),
        ".control", f"dc Vin 0 {vdd} 0.01", "set wr_singlescale", "set wr_vecnames",
        "wrdata ron.txt " + " ".join(f"i(Vt_{fl})" for fl in TG_FLAVORS) + " i(Vn) i(Vp)",
        "quit", ".endc", ".end"])


def _leak_netlist(corner, temp, vdd):
    """Off-state current out of a floating plate through each TG flavour (Wn = 1 um, Wp = 2 um): the plate is swept
    across the supply while the other side sits at Vcm; channel and plate-side junctions are both included."""
    tgs = []
    for fl, (nm, ln, pm, lp) in TG_FLAVORS.items():
        tgs += [f"Vm_{fl} x m_{fl} 0", mos(f"Tn_{fl}", "a", "0", f"m_{fl}", "0", nm, 1, ln),
                mos(f"Tp_{fl}", "a", "vdd", f"m_{fl}", "vdd", pm, 2, lp)]
    return "\n".join([
        "* switch off-state leakage", lib_line(corner), f".temp {temp}", f"Vdd vdd 0 {vdd}", f"Va a 0 {vdd / 2}",
        "Vx x 0 0", *tgs, ".control", f"dc Vx 0 {vdd} 0.005", "set wr_singlescale", "set wr_vecnames",
        "wrdata leak.txt " + " ".join(f"i(Vm_{fl})" for fl in TG_FLAVORS), "quit", ".endc", ".end"])


def _mim_netlist(corner, temp):
    sides = [(5, 5), (20, 20), (5, 40)]
    lines = ["* MIM capacitance", lib_line(corner), f".temp {temp}"]
    for k, (w, l) in enumerate(sides):
        lines += [f"Vc{k} t{k} 0 DC 0 AC 1", mim(f"C{k}", f"t{k}", "0", w, l)]
    lines += [".control", "ac lin 1 1meg 1meg"]
    lines += [f"let c{k} = imag(-i(Vc{k}))/(2*pi*1e6)" for k in range(len(sides))]
    lines += ["print " + " ".join(f"c{k}" for k in range(len(sides))) + " > mim.txt",
              "quit", ".endc", ".end"]
    return "\n".join(lines), sides


def characterize_pdk(spec, workdir: Path, force=False) -> dict:
    """Run (or load cached) PDK characterization for this corner/temperature/supply."""
    workdir = Path(workdir)
    cache = workdir / f"pdk_char_{spec.corner}_{spec.temp:g}C_{spec.vdd:g}V.json"
    cached = json.loads(cache.read_text()) if cache.exists() else None
    if cached and not force and isinstance(cached.get("ron_tg_worst_ohm_um"), dict) and \
            set(cached.get("tg_leak_hot_a_per_um", {})) == set(TG_FLAVORS):
        return cached

    mim_txt, sides = _mim_netlist(spec.corner, spec.temp)
    worst_jobs = [dict(netlist=_ron_netlist(c, t, spec.vdd * k), workdir=workdir / f"ron_{c}_{t:g}C_{k:g}")
                  for c, t, k in RON_WORST_CASES]
    leak_jobs = [dict(netlist=_leak_netlist(c, t, spec.vdd * k), workdir=workdir / f"leak_{c}_{t:g}C_{k:g}")
                 for c, t, k in LEAK_CASES]
    d_avt, d_ron, d_mim, *d_rest = run_many([
        dict(netlist=_avt_netlist(spec.corner, spec.temp, spec.vdd), workdir=workdir / "avt", seed=1),
        dict(netlist=_ron_netlist(spec.corner, spec.temp, spec.vdd), workdir=workdir / "ron"),
        dict(netlist=mim_txt, workdir=workdir / "mim"),
    ] + worst_jobs + leak_jobs)
    d_worst, d_leak = d_rest[:len(worst_jobs)], d_rest[len(worst_jobs):]

    # --- A_VT: sigma(dVT) of a pair = sqrt(2) * sigma(single); A_VT = sigma(dVT) * sqrt(WL)
    op = read_print(d_avt / "op.txt")
    avt = {"nfet": [], "pfet": []}
    for g, (w, l) in enumerate(AVT_GEOMS):
        vn = np.array([op[f"gn{g}_{k}"] for k in range(N_MC)])
        vp = np.array([spec.vdd - op[f"gp{g}_{k}"] for k in range(N_MC)])
        avt["nfet"].append(np.sqrt(2) * vn.std(ddof=1) * np.sqrt(w * l) * 1e3)
        avt["pfet"].append(np.sqrt(2) * vp.std(ddof=1) * np.sqrt(w * l) * 1e3)

    # --- on-resistance (worst case over the signal range for the TG)
    r = read_wrdata(d_ron / "ron.txt")
    vin = r[list(r)[0]]
    r_tg = 0.005 / np.abs(r["i(vt_std)"])
    r_n = 0.005 / np.abs(r["i(vn)"][0])
    r_p = 0.005 / np.abs(r["i(vp)"][0])

    # --- worst-case on-resistance over corners / temperature / low supply
    worst = dict(n=r_n, p=r_p, where=dict(n="nominal", p="nominal"))
    at_vcm = {}                         # a switch that only ever passes Vcm (the top-plate switch): R_on at Vcm
    for fl in TG_FLAVORS:
        worst[f"tg_{fl}"] = float((0.005 / np.abs(r[f"i(vt_{fl})"])).max())
        worst["where"][f"tg_{fl}"] = "nominal"
        at_vcm[fl] = float(0.005 / np.abs(np.interp(spec.vcm, vin, r[f"i(vt_{fl})"])))
    for (c_, t_, k_), d in zip(RON_WORST_CASES, d_worst):
        rw = read_wrdata(d / "ron.txt")
        vin_w = rw[list(rw)[0]]
        vals = {f"tg_{fl}": (0.005 / np.abs(rw[f"i(vt_{fl})"]))[vin_w <= spec.vref * k_].max()
                for fl in TG_FLAVORS}
        vals.update(n=0.005 / abs(rw["i(vn)"][0]), p=0.005 / abs(rw["i(vp)"][0]))
        for fl in TG_FLAVORS:
            at_vcm[fl] = max(at_vcm[fl], float(0.005 / np.abs(np.interp(spec.vcm * k_, vin_w, rw[f"i(vt_{fl})"]))))
        for key, v in vals.items():
            if v > worst[key]:
                worst[key], worst["where"][key] = float(v), f"{c_} {t_:g}C {spec.vdd * k_:.2f}V"

    # --- hot off-state leakage per um of NMOS width, with the plate Vref/2^(k+1) above or below Vcm (worse sign)
    offsets = [spec.vref / 2 ** (k + 1) for k in range(LEAK_STEPS)]
    leak = {fl: [0.0] * LEAK_STEPS for fl in TG_FLAVORS}
    for d in d_leak:
        lw = read_wrdata(d / "leak.txt")
        vx = lw[list(lw)[0]]
        for fl in TG_FLAVORS:
            i_abs = np.abs(lw[f"i(vm_{fl})"])
            for k, dv in enumerate(offsets):
                v = max(np.interp(spec.vcm + dv, vx, i_abs), np.interp(spec.vcm - dv, vx, i_abs))
                leak[fl][k] = max(leak[fl][k], float(v))

    # --- MIM: C = ca*W*L + cp*2(W+L), least squares over the three geometries
    c = read_print(d_mim / "mim.txt")
    A = np.array([[w * l, 2 * (w + l)] for w, l in sides])
    y = np.array([c[f"c{k}"] for k in range(len(sides))])
    (ca, cperim), *_ = np.linalg.lstsq(A, y, rcond=None)

    res = dict(
        corner=spec.corner, temp=spec.temp, vdd=spec.vdd,
        avt_n_mVum=float(np.mean(avt["nfet"])), avt_p_mVum=float(np.mean(avt["pfet"])),
        avt_geoms=AVT_GEOMS, avt_n_each=avt["nfet"], avt_p_each=avt["pfet"],
        ron_tg_ohm_um=float(r_tg.max()), ron_tg_vin=vin.tolist(), ron_tg_curve=(r_tg).tolist(),
        ron_n_ohm_um=float(r_n), ron_p_ohm_um=float(r_p),
        ron_tg_worst_ohm_um={fl: float(worst[f"tg_{fl}"]) for fl in TG_FLAVORS},
        ron_n_worst_ohm_um=float(worst["n"]),
        ron_p_worst_ohm_um=float(worst["p"]), ron_worst_where=worst["where"],
        ron_tg_vcm_worst_ohm_um=at_vcm, tg_leak_hot_a_per_um=leak, tg_leak_offsets_v=offsets,
        tg_leak_where=", ".join(f"{c} {t:g}C" for c, t, _ in LEAK_CASES),
        mim_ca_fF_um2=float(ca * 1e15), mim_cp_fF_um=float(cperim * 1e15),
        mim_match_pct_um=mim_matching_pct_um(),
    )
    if cached and not force:
        # only the switch data was missing: keep the cached A_VT and MIM numbers, so adding a switch flavour does not
        # re-draw the A_VT Monte Carlo (and re-size the comparator)
        res.update({k: v for k, v in cached.items() if k.startswith(("avt_", "mim_"))})
    cache.write_text(json.dumps(res, indent=1))
    return res


def comparator_offset_mc(spec, design, workdir: Path, n_inst=24, n_jobs=8, vspan=None,
                         n_steps=120, cmp_subckt=None) -> dict:
    """Offset distribution of the sized comparator (or of `cmp_subckt`, e.g. its layout extraction);
    returns offsets [V] for every instance."""
    tclk = 5e-9
    vspan = vspan or float(np.clip(6 * design["cmp"]["sigma_os_est"], 0.015, 0.2))
    jobs = [dict(netlist=nl.comparator_mc_testbench(spec, design, n_inst, vspan, n_steps, tclk, cmp_subckt),
                 workdir=Path(workdir) / f"cmp_mc_{j}", seed=100 + j) for j in range(n_jobs)]
    offsets = []
    slope = 2 * vspan / (n_steps * tclk)
    for d in run_many(jobs):
        w = read_wrdata(d / "wave.txt")
        t = w[list(w)[0]]
        t_dec = (np.arange(n_steps) + 0.9) * tclk          # read-out instants (clk still high)
        vin_dec = spec.vcm - vspan + slope * (t_dec - 0.4 * tclk)  # input at the rising clk edge
        for k in range(n_inst):
            q = np.interp(t_dec, t, w[f"qp{k}"]) > spec.vdd / 2  # high while inp < vcm
            flip = np.nonzero(~q)[0]
            if len(flip):
                offsets.append(vin_dec[flip[0]] - spec.vcm)
    offsets = np.array(offsets)
    return dict(offsets=offsets.tolist(), sigma=float(offsets.std(ddof=1)),
                mean=float(offsets.mean()), n=len(offsets), vspan=vspan)
