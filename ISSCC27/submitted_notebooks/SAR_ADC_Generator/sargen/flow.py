"""End-to-end SAR ADC flow: characterize -> size -> netlist -> simulate -> measure -> report."""

import json
import math
import time
from pathlib import Path

import numpy as np

from . import metrics, plots
from . import netlist as nl
from .anim import animate_conversion
from .characterize import characterize_pdk, comparator_offset_mc
from .model import SarModel
from .sizing import size_sar, sizing_table_md
from .spice import read_print, read_wrdata, run, run_many


# ---------------------------------------------------------------- chunked SPICE runs
def _codes_from_wave(w, tim, n_conv, bits, vdd):
    t = w["time"]
    tr = (np.arange(1, n_conv + 1)) * tim.tconv + tim.t_read
    b = np.stack([np.interp(tr, t, w[f"bo_{i}"]) > vdd / 2 for i in range(bits)], axis=1)
    return (b * 2 ** np.arange(bits)).sum(1)


def simulate_codes(spec, design, kind, n_total, workdir, chunk=32, *, ramp=None, sine=None,
                   mismatch=False, seed=None, cp_top=0.0, **tb_kw):
    """Simulate `n_total` conversions split into parallel chunks.

    kind = "ramp": ramp=(v_start, dv)   -> sample g gets v_start + g*dv
    kind = "sine": sine=(amp, f_in)     -> sample g gets vcm + amp*sin(2 pi f_in g / fs)
    Returns codes, input samples, power info.
    """
    tim = nl.Timing(spec.bits, spec.tclk)
    tc, ts = tim.tconv, tim.t_top_open
    jobs, spans = [], []
    for j, k0 in enumerate(range(0, n_total, chunk)):
        n = min(chunk, n_total - k0)
        tstop = (n + 1) * tc
        if kind == "ramp":
            v0, dv = ramp
            a = v0 + (k0 - 1) * dv - dv * ts / tc
            line = f"Vin vin 0 PWL(0 {a:.9g} {tstop:.9g} {a + dv * tstop / tc:.9g})"
        elif kind == "sine":
            amp, f = sine
            ph = math.degrees(2 * math.pi * f * ((k0 - 1) * tc - ts)) % 360
            line = f"Vin vin 0 SIN({spec.vcm} {amp:.9g} {f:.9g} 0 0 {ph:.9g})"
        else:
            raise ValueError(kind)
        jobs.append(dict(netlist=nl.sar_testbench(spec, design, line, n, mismatch=mismatch, cp_top=cp_top, **tb_kw),
                         workdir=Path(workdir) / f"chunk_{j:03d}", seed=seed))
        spans.append((k0, n))
    dirs = run_many(jobs)
    codes, q_vdd, q_vref, q_vcm = [], 0.0, 0.0, 0.0
    for d, (k0, n) in zip(dirs, spans):
        codes.append(_codes_from_wave(read_wrdata(d / "wave.txt"), tim, n, spec.bits, spec.vdd))
        p = read_print(d / "power.txt")
        q_vdd += -p["q_vdd"]
        q_vref += -p["q_vref"]
        q_vcm += -p["q_vcm"]
    g = np.arange(n_total)
    vin = ramp[0] + g * ramp[1] if kind == "ramp" else spec.vcm + sine[0] * np.sin(2 * np.pi * sine[1] * g / spec.fs)
    t_total = n_total * tc
    power = dict(p_vdd=q_vdd * spec.vdd / t_total, p_vref=q_vref * spec.vref / t_total,
                 p_vcm=q_vcm * spec.vcm / t_total)
    power["p_total"] = power["p_vdd"] + power["p_vref"] + power["p_vcm"]
    return np.concatenate(codes), vin, power


# ---------------------------------------------------------------- main flow
def run_flow(spec, out=None, *, hits=32, fft_n=128, fft_cycles=None, cmp_mc_inst=24, mc_runs=1000,
             chunk=32, spice_mc_seeds=0, animate=True, force_char=False, log=print) -> dict:
    t_start = time.time()
    out = Path(out or f"build/{spec.bits}bit")
    sim = out / "sim"
    out.mkdir(parents=True, exist_ok=True)
    res = dict(spec=spec.to_dict())
    step = lambda s: log(f"[{time.time() - t_start:6.1f}s] {s}")  # noqa: E731

    step("1/8 PDK characterization (A_VT, R_on, MIM)")
    char = characterize_pdk(spec, out.parent / "char", force=force_char)
    res["char"] = {k: v for k, v in char.items() if k not in ("ron_tg_vin", "ron_tg_curve")}

    step("2/8 sizing")
    design = size_sar(spec, char)
    (out / "design.json").write_text(json.dumps(design, indent=1))
    (out / "sizing.md").write_text(sizing_table_md(design))
    res["design"] = {k: v for k, v in design.items() if k != "log"}

    step("3/8 netlist + single-conversion transient")
    tim = nl.Timing(spec.bits, spec.tclk)
    vin_demo = round(0.6 * 2**spec.bits) * spec.lsb + 0.5 * spec.lsb
    save = ["v(top)", "v(clk)", "v(qp)", "v(phit)"] + \
           [f"v(bo_{i})" for i in range(spec.bits)] + [f"v(bot_{i})" for i in range(spec.bits)]
    tb = nl.sar_testbench(spec, design, f"Vin vin 0 {vin_demo}", 2, save=save)
    (out / f"sar_adc_{spec.bits}b_tb.spice").write_text(tb)
    w = read_wrdata(run(tb, sim / "single") / "wave.txt")
    plots.waveforms(w, tim, spec, out / "waveforms.png")
    code_demo = int(_codes_from_wave(w, tim, 2, spec.bits, spec.vdd)[-1])
    res["single"] = dict(vin=vin_demo, code=code_demo, ideal=int(vin_demo / spec.lsb))

    step(f"4/8 comparator offset Monte Carlo ({cmp_mc_inst} x 8 instances)")
    os_res = comparator_offset_mc(spec, design, sim / "cmp", n_inst=cmp_mc_inst)
    plots.offset_hist(os_res["offsets"], spec, out / "comparator_offset.png")
    res["comparator_offset"] = {k: v for k, v in os_res.items() if k != "offsets"}

    step(f"5/8 ramp test: {hits} hits/code, transistor level")
    n_ramp = hits * 2**spec.bits
    v0, v1 = -0.5 * spec.lsb, spec.vref + 0.5 * spec.lsb
    dv = (v1 - v0) / n_ramp
    codes_r, vin_r, power = simulate_codes(spec, design, "ramp", n_ramp, sim / "ramp", chunk, ramp=(v0, dv))
    hist = metrics.histogram_inl_dnl(codes_r, spec.bits)
    trans = metrics.transition_inl_dnl(metrics.transition_levels(vin_r, codes_r, spec.bits), spec.vref, spec.bits)
    plots.transfer(vin_r, codes_r, spec, out / "transfer.png")
    plots.inl_dnl(hist, spec, out / "inl_dnl_histogram.png")
    plots.transition_inl_dnl(trans, spec, out / "inl_dnl_transitions.png")
    res["static"] = dict(dnl_max=hist["dnl_max"], inl_max=hist["inl_max"], missing_codes=hist["missing_codes"],
                         dnl_t_max=trans["dnl_max"], inl_t_max=trans["inl_max"],
                         offset_lsb=trans["offset_lsb"], gain_error_lsb=trans["gain_error_lsb"],
                         dnl=hist["dnl"].tolist(), inl=hist["inl"].tolist(), hist=hist["hist"].tolist(),
                         transitions=trans["t"].tolist())
    np.savez(out / "ramp.npz", vin=vin_r, codes=codes_r)

    step(f"6/8 sine test: {fft_n}-point coherent FFT, transistor level")
    fft_cycles = fft_cycles or _coprime_cycles(fft_n)
    f_in = metrics.coherent_tone(spec.fs, fft_n, fft_cycles)
    amp = spec.vref / 2 * 0.99
    codes_s, vin_s, power_s = simulate_codes(spec, design, "sine", fft_n, sim / "sine", chunk, sine=(amp, f_in))
    fft = metrics.fft_metrics(codes_s, spec.bits, fft_cycles)
    plots.spectrum(fft, spec, out / "fft.png")
    plots.time_samples(vin_s, codes_s, spec, out / "sine_samples.png")
    ideal_fft = metrics.fft_metrics(SarModel(spec.bits, spec.vref).convert(vin_s), spec.bits, fft_cycles)
    p_avg = power_s["p_total"]
    res["dynamic"] = dict(f_in=f_in, amp=amp, sndr_db=fft["sndr_db"], sfdr_db=fft["sfdr_db"], thd_db=fft["thd_db"],
                          enob=fft["enob"], ideal_model_sndr_db=ideal_fft["sndr_db"], ideal_model_enob=ideal_fft["enob"])
    res["power"] = dict(**power_s, energy_per_conv=p_avg / spec.fs,
                        walden_fom_J=metrics.walden_fom(p_avg, fft["enob"], spec.fs),
                        note="comparator, CDAC, switches and SAR logic (sky130_fd_sc_hd cells); "
                             "clock/phase generation and references are ideal sources")
    np.savez(out / "sine.npz", vin=vin_s, codes=codes_s)

    step(f"7/8 mismatch Monte Carlo: behavioral model x {mc_runs} (+{spice_mc_seeds} SPICE seeds)")
    vin_fine = np.linspace(-0.5 * spec.lsb, spec.vref + 0.5 * spec.lsb, 2**spec.bits * 64)
    sig_os = os_res["sigma"]
    dnl_m, inl_m, rng = [], [], np.random.default_rng(1)
    for k in range(mc_runs):
        m = SarModel(spec.bits, spec.vref, cu_sigma=design["cu"]["sigma_u"], offset=rng.normal(0, sig_os),
                     noise_rms=design["noise"]["ktc_rms"], seed=k)
        tr = metrics.transition_inl_dnl(metrics.transition_levels(vin_fine, m.convert(vin_fine), spec.bits),
                                        spec.vref, spec.bits)
        dnl_m.append(tr["dnl_max"])
        inl_m.append(tr["inl_max"])
    plots.mc_linearity(np.array(dnl_m), np.array(inl_m), spec, out / "mc_linearity.png")
    res["mc"] = dict(runs=mc_runs, dnl_p99=float(np.percentile(dnl_m, 99)), inl_p99=float(np.percentile(inl_m, 99)),
                     yield_dnl_lt_0p5=float(np.mean(np.array(dnl_m) < 0.5)), sigma_u=design["cu"]["sigma_u"],
                     sigma_offset=sig_os)
    spice_mc = []
    for s in range(spice_mc_seeds):
        c, v, _ = simulate_codes(spec, design, "ramp", 8 * 2**spec.bits, sim / f"mc_seed{s}", chunk,
                                 ramp=(v0, (v1 - v0) / (8 * 2**spec.bits)), mismatch=True, seed=500 + s)
        h = metrics.histogram_inl_dnl(c, spec.bits)
        spice_mc.append(dict(seed=500 + s, dnl_max=h["dnl_max"], inl_max=h["inl_max"]))
    res["mc"]["spice_seeds"] = spice_mc

    step("8/8 animation + report")
    if animate:
        animate_conversion(SarModel(spec.bits, spec.vref), vin_demo, out / "sar_animation.gif")
    res["runtime_s"] = time.time() - t_start
    (out / "summary.json").write_text(json.dumps(res, indent=1, default=float))
    (out / "report.md").write_text(report_md(res, design))
    step(f"done -> {out}")
    return res


def _coprime_cycles(n):
    """Odd, prime-ish number of input cycles close to n/10 (coherent, no repeated codes)."""
    c = max(3, int(n / 10)) | 1
    while math.gcd(c, n) != 1:
        c += 2
    return c


def report_md(res, design) -> str:
    s, st, dy, pw, mc = res["spec"], res["static"], res["dynamic"], res["power"], res["mc"]
    co = res["comparator_offset"]
    return f"""# {s['bits']}-bit SAR ADC - generated report

**Spec:** {s['bits']} bit, {s['fs'] / 1e6:g} MS/s, Vref = {s['vref']} V, LSB = {s['lsb'] * 1e3:.2f} mV, SKY130 {s['corner']}, {s['temp']} C

## Sizing
{sizing_table_md(design)}

## Results (transistor level, pre-layout)
| metric | value |
|---|---|
| ENOB (FFT, {dy['f_in'] / 1e6:.3f} MHz) | **{dy['enob']:.2f} bit** (ideal quantizer: {dy['ideal_model_enob']:.2f}) |
| SNDR / SFDR / THD | {dy['sndr_db']:.2f} dB / {dy['sfdr_db']:.1f} dB / {dy['thd_db']:.1f} dB |
| max DNL / INL (histogram) | {st['dnl_max']:.3f} / {st['inl_max']:.3f} LSB |
| max DNL / INL (transition levels) | {st['dnl_t_max']:.3f} / {st['inl_t_max']:.3f} LSB |
| missing codes | {st['missing_codes']} |
| offset / gain error | {st['offset_lsb']:.3f} / {st['gain_error_lsb']:.3f} LSB |
| comparator offset sigma (MC, n={co['n']}) | {co['sigma'] * 1e3:.2f} mV ({co['sigma'] / s['lsb']:.3f} LSB) |
| power (comparator + CDAC + switches + SAR logic cells) | {pw['p_total'] * 1e6:.2f} uW |
| energy / conversion | {pw['energy_per_conv'] * 1e12:.3f} pJ |
| Walden FoM | {pw['walden_fom_J'] * 1e15:.1f} fJ/conv-step |
| MC ({mc['runs']} runs) 99th-pct DNL / INL | {mc['dnl_p99']:.3f} / {mc['inl_p99']:.3f} LSB |
| MC yield (max DNL < 0.5 LSB) | {mc['yield_dnl_lt_0p5'] * 100:.1f} % |

Runtime: {res['runtime_s']:.0f} s
"""
