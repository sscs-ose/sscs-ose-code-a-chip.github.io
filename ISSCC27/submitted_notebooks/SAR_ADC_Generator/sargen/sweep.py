"""Robustness sweeps of one fixed (nominally sized) design: PVT, input frequency, sample rate,
plus the comparator delay vs. input characteristic (regeneration / metastability)."""

import dataclasses
import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from . import metrics
from . import netlist as nl
from .flow import _coprime_cycles, simulate_codes
from .pdk import lib_line
from .spice import read_wrdata, run_many


def evaluate(spec, design, out, *, hits=16, fft_n=128, fft_cycles=None, chunk=32, **tb_kw):
    """Ramp (DNL/INL/offset/gain) + coherent sine (ENOB) + power for a fixed design."""
    out = Path(out)
    n_ramp = hits * 2**spec.bits
    v0, v1 = -0.5 * spec.lsb, spec.vref + 0.5 * spec.lsb
    codes_r, vin_r, _ = simulate_codes(spec, design, "ramp", n_ramp, out / "ramp", chunk,
                                       ramp=(v0, (v1 - v0) / n_ramp), **tb_kw)
    hist = metrics.histogram_inl_dnl(codes_r, spec.bits)
    trans = metrics.transition_inl_dnl(metrics.transition_levels(vin_r, codes_r, spec.bits),
                                       spec.vref, spec.bits)
    fft_cycles = fft_cycles or _coprime_cycles(fft_n)
    f_in = metrics.coherent_tone(spec.fs, fft_n, fft_cycles)
    codes_s, _, pw = simulate_codes(spec, design, "sine", fft_n, out / "sine", chunk,
                                    sine=(spec.vref / 2 * 0.99, f_in), **tb_kw)
    fft = metrics.fft_metrics(codes_s, spec.bits, fft_cycles)
    return dict(enob=fft["enob"], sndr_db=fft["sndr_db"], sfdr_db=fft["sfdr_db"], f_in=f_in,
                dnl_max=hist["dnl_max"], inl_max=hist["inl_max"], missing=hist["missing_codes"],
                dnl_t=trans["dnl_max"], inl_t=trans["inl_max"],
                offset_lsb=trans["offset_lsb"], gain_lsb=trans["gain_error_lsb"],
                p_uw=pw["p_total"] * 1e6)


def _save(rows, out, name):
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{name}.json").write_text(json.dumps(rows, indent=1, default=float))
    keys = [k for k in rows[0] if k not in ("label",)]
    md = ["| " + " | ".join(["point"] + keys) + " |", "|" + "---|" * (len(keys) + 1)]
    for r in rows:
        md.append("| " + " | ".join([r["label"]] + [f"{r[k]:.3g}" if isinstance(r[k], float) else str(r[k])
                                                   for k in keys]) + " |")
    (out / f"{name}.md").write_text("\n".join(md) + "\n")
    return out / f"{name}.md"


def pvt(spec, design, out, corners=("tt", "ss", "ff", "sf", "fs"), temps=(-40, 27, 125),
        vdd_scale=(0.9, 1.1), **kw):
    """Fixed design across process corners x temperatures, plus +-10 % supply at tt/27 C."""
    out = Path(out)
    rows = []
    points = [(c, t, 1.0) for c in corners for t in temps] + [("tt", 27, s) for s in vdd_scale]
    for c, t, s in points:
        sp = dataclasses.replace(spec, corner=c, temp=float(t), vdd=spec.vdd * s, vref=spec.vref * s)
        label = f"{c} {t:+d}C {sp.vdd:.2f}V"
        r = evaluate(sp, design, out / "sim" / label.replace(" ", "_"), **kw)
        rows.append(dict(label=label, corner=c, temp=t, vdd=sp.vdd, **r))
        print(f"  PVT {label}: ENOB {r['enob']:.2f}, DNL {r['dnl_t']:.3f}, INL {r['inl_t']:.3f}, "
              f"offset {r['offset_lsb']:.2f} LSB, {r['p_uw']:.1f} uW", flush=True)
    md = _save(rows, out, f"pvt_{spec.bits}b")
    _plot_pvt(rows, spec, out / f"pvt_{spec.bits}b.png")
    return rows, md


def _plot_pvt(rows, spec, path):
    labels = [r["label"] for r in rows]
    fig, ax = plt.subplots(4, 1, figsize=(10, 9), sharex=True)
    for a, key, name in zip(ax, ["enob", "dnl_t", "offset_lsb", "p_uw"],
                            ["ENOB [bit]", "max |DNL| [LSB]", "offset [LSB]", "power [uW]"]):
        a.bar(range(len(rows)), [r[key] for r in rows], color="#4C9BE8")
        a.set_ylabel(name)
        a.grid(alpha=0.3)
    ax[0].axhline(spec.bits, color="k", ls="--", lw=1)
    ax[-1].set_xticks(range(len(rows)))
    ax[-1].set_xticklabels(labels, rotation=60, ha="right", fontsize=8)
    fig.suptitle(f"{spec.bits}-bit SAR, one fixed design across PVT")
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def fin_sweep(spec, design, out, fft_n=128, cycles=None, **kw):
    """ENOB vs. input frequency (coherent tones up to ~fs/2)."""
    out = Path(out)
    cycles = cycles or [c for c in (3, 13, 31, 47, 59, 63) if c < fft_n // 2 and math.gcd(c, fft_n) == 1]
    rows = []
    for c in cycles:
        tim_codes, _, _ = simulate_codes(spec, design, "sine", fft_n, out / "sim" / f"fin_{c}", 32,
                                         sine=(spec.vref / 2 * 0.99, metrics.coherent_tone(spec.fs, fft_n, c)))
        f = metrics.fft_metrics(tim_codes, spec.bits, c)
        rows.append(dict(label=f"fin={c / fft_n:.3f} fs", f_in=c / fft_n * spec.fs, enob=f["enob"],
                         sndr_db=f["sndr_db"], sfdr_db=f["sfdr_db"]))
        print(f"  fin {c / fft_n:.3f} fs: ENOB {f['enob']:.2f}", flush=True)
    md = _save(rows, out, f"fin_{spec.bits}b")
    return rows, md


def fs_sweep(spec, design, out, rates=(10e6, 20e6, 40e6, 80e6, 160e6), **kw):
    """Same design clocked faster: where does it break (settling / comparator time)?"""
    out = Path(out)
    rows = []
    for fs in rates:
        sp = dataclasses.replace(spec, fs=fs)
        r = evaluate(sp, design, out / "sim" / f"fs_{fs / 1e6:g}M", **kw)
        rows.append(dict(label=f"{fs / 1e6:g} MS/s", fs=fs, **r))
        print(f"  fs {fs / 1e6:g} MS/s: ENOB {r['enob']:.2f}, DNL {r['dnl_t']:.3f}, {r['p_uw']:.1f} uW", flush=True)
    md = _save(rows, out, f"fs_{spec.bits}b")
    return rows, md


def comparator_delay(spec, design, out, dv=None, tclk=10e-9):
    """Clock-to-output delay vs. input difference (one transient, many comparators, no mismatch)."""
    out = Path(out)
    dv = np.asarray(dv if dv is not None else np.logspace(-6, -1, 16))
    inst = []
    for k, v in enumerate(dv):
        inst += [f"Vp{k} inp{k} 0 {spec.vcm + v / 2:.9g}", f"Vn{k} inn{k} 0 {spec.vcm - v / 2:.9g}",
                 f"Xc{k} inp{k} inn{k} clk qp{k} qn{k} vdd 0 strongarm"]
    saves = " ".join(f"v(qn{k})" for k in range(len(dv))) + " v(clk)"
    tb = f"""* comparator delay vs input
{lib_line(spec.corner)}
.temp {spec.temp}
{nl.strongarm_subckt(design['cmp'])}
Vdd vdd 0 {spec.vdd}
Vclk clk 0 PULSE(0 {spec.vdd} {0.5 * tclk:.6g} {nl.TR} {nl.TR} {0.45 * tclk:.6g} {tclk:.6g})
{chr(10).join(inst)}
.tran 2p {1.0 * tclk:.6g} 0 5p
.control
set wr_singlescale
set wr_vecnames
run
wrdata wave.txt {saves}
quit
.endc
.end
"""
    d = run_many([dict(netlist=tb, workdir=out / "cmp_delay")])[0]
    w = read_wrdata(d / "wave.txt")
    t = w["time"]
    t_clk = 0.5 * tclk + nl.TR / 2
    delays = []
    for k in range(len(dv)):
        q = w[f"qn{k}"]                                 # qn rises when inp > inn
        idx = np.nonzero((t > t_clk) & (q > spec.vdd / 2))[0]
        delays.append(float(t[idx[0]] - t_clk) if len(idx) else float("nan"))
    delays = np.array(delays)
    ok = np.isfinite(delays) & (dv < 1e-2)
    slope = np.polyfit(np.log(dv[ok]), delays[ok], 1)[0] if ok.sum() > 2 else float("nan")
    tau = -slope                                        # t_d = t0 + tau * ln(1/dv)
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.semilogx(dv * 1e3, delays * 1e12, "o-")
    ax.axvline(spec.lsb / 2 * 1e3, color="r", ls="--", label="LSB/2")
    ax.set_xlabel("input difference [mV]")
    ax.set_ylabel("clk -> output delay [ps]")
    ax.set_title(f"StrongARM regeneration: tau = {tau * 1e12:.1f} ps")
    ax.grid(alpha=0.3, which="both")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out / f"cmp_delay_{spec.bits}b.png", dpi=130)
    plt.close(fig)
    return dict(dv=dv.tolist(), delay=delays.tolist(), tau=float(tau),
                delay_half_lsb=float(np.interp(np.log(spec.lsb / 2), np.log(dv), delays)))


def spice_mc(spec, design, out, seeds=4, hits=8, behavioral_runs=1000, sigma_os=None):
    """Transistor-level ramps with SKY130 mismatch (tt_mm) vs. the PDK-calibrated behavioral MC."""
    from .model import SarModel
    out = Path(out)
    n_ramp = hits * 2**spec.bits
    v0, v1 = -0.5 * spec.lsb, spec.vref + 0.5 * spec.lsb
    rows = []
    for s in range(seeds):
        c, v, _ = simulate_codes(spec, design, "ramp", n_ramp, out / "sim" / f"mc_seed{s}", 32,
                                 ramp=(v0, (v1 - v0) / n_ramp), mismatch=True, seed=1000 + s)
        tr = metrics.transition_inl_dnl(metrics.transition_levels(v, c, spec.bits), spec.vref, spec.bits)
        rows.append(dict(label=f"seed {1000 + s}", dnl=tr["dnl_max"], inl=tr["inl_max"], offset=tr["offset_lsb"]))
        print(f"  SPICE MC seed {1000 + s}: DNL {tr['dnl_max']:.3f}, INL {tr['inl_max']:.3f}, "
              f"offset {tr['offset_lsb']:.2f} LSB", flush=True)
    # behavioral distribution evaluated with the same ramp resolution as the SPICE runs
    rng = np.random.default_rng(7)
    sig_os = sigma_os if sigma_os is not None else design["cmp"]["sigma_os_est"]
    vin = v0 + (v1 - v0) * np.arange(n_ramp) / n_ramp
    beh = []
    for k in range(behavioral_runs):
        m = SarModel(spec.bits, spec.vref, cu_sigma=design["cu"]["sigma_u"], offset=rng.normal(0, sig_os), seed=k)
        tr = metrics.transition_inl_dnl(metrics.transition_levels(vin, m.convert(vin), spec.bits), spec.vref, spec.bits)
        beh.append((tr["dnl_max"], tr["inl_max"]))
    beh = np.array(beh)
    res = dict(spice=rows, beh_dnl_pct=np.percentile(beh[:, 0], [5, 50, 95]).tolist(),
               beh_inl_pct=np.percentile(beh[:, 1], [5, 50, 95]).tolist(), hits=hits)
    fig, ax = plt.subplots(1, 2, figsize=(10, 4))
    for a, j, name in ((ax[0], 0, "DNL"), (ax[1], 1, "INL")):
        a.hist(beh[:, j], bins=30, color="#cccccc", label=f"behavioral MC ({behavioral_runs})")
        for r in rows:
            a.axvline(r[name.lower()], color="#C62828", lw=2)
        a.axvline(np.nan, color="#C62828", lw=2, label=f"transistor-level MC ({seeds} seeds)")
        a.set_xlabel(f"max |{name}| [LSB]")
        a.legend(fontsize=8)
        a.grid(alpha=0.3)
    fig.suptitle(f"{spec.bits}-bit: transistor-level mismatch runs vs. behavioral model "
                 f"(ramp resolution 1/{hits} LSB)")
    fig.tight_layout()
    fig.savefig(out / f"spice_mc_{spec.bits}b.png", dpi=130)
    plt.close(fig)
    (out / f"spice_mc_{spec.bits}b.json").write_text(json.dumps(res, indent=1, default=float))
    return res
