"""Post-layout verification of ldo_top (LDO + POR + bandgap) from the extracted netlist, compared with the
pre-layout netlist (same devices, no parasitics). Everything is a power-up transient (VIN ramps from 0 V), so the
bandgap start-up and the POR are exercised exactly as on a harvested tag.

usage: python postlayout.py <view: pex|sch> [pvt|tt] [nproc]
"""
import sys, os, re, itertools
from lib import *

VIEWS = {"pex": "mag/pexrun/ldo_top_pexC.spice", "sch": "mag/schematic.spice"}


def top_tb(view, corner, temp, vin, body_extra, ctl, tstop, tag):
    net = (f"* post-layout tb ({view})\n" + models(corner) + f".temp {temp}\n"
           ".option gmin=1e-14 reltol=1e-4 rshunt=1e13 method=gear\n"
           f".include \"{os.path.abspath(VIEWS[view])}\"\n"
           f"Vin vin 0 PWL(0 0 1m {vin})\n"
           "Xtop vin vout rstn 0 ldo_top\nCL vout 0 100p\nCrst rstn 0 50f\n" + body_extra +
           f".control\ntran 20n {tstop} 0 2u uic\n{ctl}\n.endc\n.end\n")
    return spice(net, tag, timeout=3600)


T_ON = 4.0e-3          # power-up ramp 1 ms, then settle


def load_step(view, corner="tt", temp=27, vin=2.5, tr=100e-9):
    t1, t2, te = T_ON, T_ON + 40e-6, T_ON + 80e-6
    body = f"Il vout 0 PWL(0 0 {t1} 0 {t1+tr} 1m {t2} 1m {t2+tr} 0)\n"
    ctl = (f"meas tran vpre avg v(vout) from={t1-20e-6} to={t1}\n"
           f"meas tran vmin min v(vout) from={t1} to={t2}\n"
           f"meas tran vload avg v(vout) from={t2-10e-6} to={t2}\n"
           f"meas tran vmax max v(vout) from={t2} to={te}\n"
           f"meas tran iq avg i(Vin) from={t1-20e-6} to={t1}\n"
           f"meas tran rst find v(rstn) at={t1-1e-6}\n")
    r = top_tb(view, corner, temp, vin, body, ctl, te, f"pl_{view}_ls_{corner}_{temp}_{vin}")
    return dict(vout=r["vpre"], under=(r["vpre"] - r["vmin"]) * 1e3, over=(r["vmax"] - r["vpre"]) * 1e3,
                load_reg=(r["vpre"] - r["vload"]) * 1e3, iq=-r["iq"] * 1e6, rstn=r["rst"])


def small_step(view, corner="tt", temp=27, vin=2.5, il=0.0, di=10e-6):
    """small load step il -> il+di, overshoot of the recovery in % of the dip (2nd-order PM indicator)"""
    t1, te = T_ON, T_ON + 60e-6
    body = f"Il vout 0 PWL(0 {il} {t1} {il} {t1+100e-9} {il+di})\n"
    tag = f"pl_{view}_ss_{corner}_{temp}_{vin}_{il}"
    ctl = f"linearize v(vout)\nwrdata {tag}.dat v(vout)"
    top_tb(view, corner, temp, vin, body, ctl, te, tag)
    d = wrdata(tag); d.columns = ["t", "v"]
    a = d[d.t >= t1]
    vf = a.v[a.t > te - 10e-6].mean()
    k = a.v.idxmin(); dip = vf - a.v[k]
    after = a[a.t > a.t[k]]
    over = (after.v.max() - vf) if len(after) else 0.0
    return dict(dip_mV=dip * 1e3, overshoot_pct=100 * over / dip if dip > 0 else float("nan"))


def psrr_tran(view, f, corner="tt", temp=27, vin=2.5, amp=0.05, il=0.0):
    """ripple of `amp` V at f on VIN after power-up; PSRR = 20 log(amp / vout ripple amplitude).
    The amplitude is a least-squares fit of sin + cos + offset + linear drift over the last 4 cycles, so slow
    settling of the reference does not count as ripple."""
    t1 = T_ON
    ncyc = 20 if f >= 10e3 else 5
    te = t1 + ncyc / f
    body = f"Il vout 0 {il}\n"
    net_vin = f"Vin vinx 0 PWL(0 0 1m {vin})\nVr vin vinx SIN(0 {amp} {f} {t1})\n"
    tag = f"pl_{view}_ps_{f:g}_{corner}_{temp}"
    ctl = f"linearize v(vout)\nwrdata {tag}.dat v(vout)"
    net = (f"* psrr tb ({view})\n" + models(corner) + f".temp {temp}\n"
           ".option gmin=1e-14 reltol=1e-4 rshunt=1e13 method=gear\n"
           f".include \"{os.path.abspath(VIEWS[view])}\"\n" + net_vin +
           "Xtop vin vout rstn 0 ldo_top\nCL vout 0 100p\nCrst rstn 0 50f\n" + body +
           f".control\ntran {min(20e-9, 1/f/200)} {te} 0 {min(2e-6, 1/f/50)} uic\n{ctl}\n.endc\n.end\n")
    spice(net, tag, timeout=3600)
    d = wrdata(tag); d.columns = ["t", "v"]
    a = d[d.t >= te - 4 / f]
    w = 2 * np.pi * f * (a.t.values - t1)
    A = np.column_stack([np.sin(w), np.cos(w), np.ones_like(w), a.t.values - te])
    c = np.linalg.lstsq(A, a.v.values, rcond=None)[0]
    return 20 * np.log10(amp / np.hypot(c[0], c[1]))


if __name__ == "__main__":
    view = sys.argv[1]
    mode = sys.argv[2] if len(sys.argv) > 2 else "tt"
    if mode == "tt":
        print(view, "load step tt:", {k: round(v, 4) for k, v in load_step(view).items()}, flush=True)
        for il in (0.0, 1e-3):
            print(view, f"small step at {il*1e3:g} mA:", {k: round(v, 2) for k, v in small_step(view, il=il).items()}, flush=True)
        for f in (1e3, 1e5, 8.47e5):
            print(view, f"PSRR {f:g} Hz: {psrr_tran(view, f):.1f} dB", flush=True)
    else:
        pts = [(c, T, v) for c in ("tt", "ss", "ff", "sf", "fs") for T in (-40, 27, 125) for v in (1.8, 2.5, 3.3)]
        def one(a):
            c, T, v = a
            try:
                r = load_step(view, c, T, v)
                s = small_step(view, c, T, v, il=0.0)
                return dict(corner=c, T=T, vin=v, **r, ss_over=s["overshoot_pct"])
            except Exception as e:
                return dict(corner=c, T=T, vin=v, err=str(e)[-200:])
        df = pd.DataFrame(pmap(one, pts, workers=int(sys.argv[3]) if len(sys.argv) > 3 else None))
        df.to_csv(f"postlayout_pvt_{view}.csv", index=False)
        pd.set_option("display.width", 220)
        cols = [c for c in ["corner", "T", "vin", "vout", "under", "over", "load_reg", "iq", "rstn", "ss_over"] if c in df]
        print(df[cols].round(3).to_string(index=False))
        ok = df.dropna(subset=["under"])
        print(f"{view}: n={len(ok)}/{len(df)}  worst undershoot {ok.under.max():.0f} mV, overshoot {ok.over.max():.0f} mV, "
              f"VOUT {ok.vout.min():.4f}..{ok.vout.max():.4f}, Iq max {ok.iq.max():.2f} uA, small-step overshoot max {ok.ss_over.max():.1f} %")
