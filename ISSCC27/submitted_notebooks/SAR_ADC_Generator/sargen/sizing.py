"""Specification-driven sizing of the SAR ADC from characterized PDK data.

Every decision is logged as a (block, rule, numbers, result) row so the notebook
can show *why* each device has its size.
"""

import math

from .pdk import L_MIN, MIM_MIN_SIDE, W_MIN

TOP_DROOP_LSB = 0.25    # hot leakage of the top-plate switch may move the floating plate by at most this per conversion
TOP_W_CAP = 4.0         # top-plate switch flavours considered: at most this many times as wide as the narrowest

K_B = 1.380649e-23


def _ceil(x, grid=0.05):
    return round(math.ceil(x / grid - 1e-9) * grid, 3)


class Log(list):
    def add(self, block, rule, numbers, result):
        self.append(dict(block=block, rule=rule, numbers=numbers, result=result))


def size_sar(spec, char: dict) -> dict:
    N, lsb, T = spec.bits, spec.lsb, spec.tclk
    kT = K_B * (spec.temp + 273.15)
    log = Log()
    log.add("spec", "LSB = Vref / 2^N", f"{spec.vref} V / {2**N}", f"{lsb * 1e3:.2f} mV")
    log.add("timing", "Tclk = 1 / ((N + 2) * fs)", f"fs = {spec.fs / 1e6:g} MS/s, {N + 2} cycles",
            f"{T * 1e9:.2f} ns ({spec.fclk / 1e6:.1f} MHz)")

    # ---------------------------------------------------------------- unit capacitor
    ln_settle = math.log(2**N / spec.settle_lsb)       # time constants to settle to settle_lsb
    sig_u = spec.dnl_3sigma_lsb / (3 * math.sqrt(2**N - 1))
    a_c = char["mim_match_pct_um"] / 100
    side_match = a_c / sig_u
    log.add("CDAC", "sigma_DNL(mid-code) = sqrt(2^N - 1) * sigma_u <= DNL_3sigma / 3",
            f"sigma_u <= {sig_u * 100:.3f} %, A_C = {char['mim_match_pct_um']} %um",
            f"side >= {side_match:.2f} um (matching)")
    ca, cp = char["mim_ca_fF_um2"] * 1e-15, char["mim_cp_fF_um"] * 1e-15
    c_of = lambda s: ca * s * s + cp * 4 * s       # noqa: E731
    sig_ktc = spec.noise_lsb * lsb
    c_ktc = kT / sig_ktc**2
    # solve 2^N * (ca s^2 + 4 cp s) = C_kTC for s
    side_ktc = (-4 * cp + math.sqrt(16 * cp**2 + 4 * ca * c_ktc / 2**N)) / (2 * ca)
    log.add("CDAC", "kT/C: sqrt(kT / C_total) <= noise_lsb * LSB",
            f"C_total >= {c_ktc * 1e15:.3g} fF",
            f"side >= {side_ktc:.2f} um (noise)" if side_ktc >= 0.01 else "negligible at this resolution")
    side = _ceil(max(side_match, side_ktc, MIM_MIN_SIDE))
    cu = c_of(side)
    c_tot = 2**N * cu
    reason = max([("matching", side_match), ("kT/C", side_ktc), ("min. size", MIM_MIN_SIDE)],
                 key=lambda x: x[1])[0]
    log.add("CDAC", "Cu = Ca * s^2 + Cp * 4s (characterized MIM)",
            f"s = {side:.2f} um, limited by {reason}",
            f"Cu = {cu * 1e15:.2f} fF, C_total = {c_tot * 1e15:.1f} fF")

    # ---------------------------------------------------------------- comparator
    sig_os_t = spec.offset_3sigma_lsb * lsb / 3
    wl_in = (char["avt_n_mVum"] * 1e-3 / sig_os_t) ** 2
    l_in = 0.3
    w_in = _ceil(max(wl_in / l_in, 2.0), 0.1)
    sig_os_est = char["avt_n_mVum"] * 1e-3 / math.sqrt(w_in * l_in)
    log.add("comparator", "offset only shifts the transfer curve here (no DNL/INL): spec = offset error",
            f"3 sigma_os <= {spec.offset_3sigma_lsb} LSB", f"sigma_os <= {sig_os_t * 1e3:.2f} mV")
    log.add("comparator", "sigma_os ~ A_VT / sqrt(W L) <= offset_3sigma * LSB / 3",
            f"A_VT = {char['avt_n_mVum']:.2f} mVum, target {sig_os_t * 1e3:.2f} mV",
            f"W L >= {wl_in:.3f} um^2 -> W/L = {w_in:.1f}/{l_in} (est. {sig_os_est * 1e3:.2f} mV)")
    preamp = wl_in > 20.0
    log.add("comparator", "pre-amplifier needed if W L > 20 um^2 (input cap / kick-back)",
            f"W L = {wl_in:.2f} um^2", "YES - add preamp" if preamp else "no - StrongARM alone")
    cmp_ = dict(w_in=w_in, l_in=l_in, w_tail=_ceil(1.5 * w_in, 0.1), w_ln=_ceil(max(w_in / 2, 1.0), 0.1),
                w_lp=_ceil(max(w_in / 2, 1.0), 0.1), w_rst=1.0, w_inv_n=1.0, w_inv_p=2.0, l=L_MIN,
                sigma_os_target=sig_os_t, sigma_os_est=sig_os_est, preamp=preamp)
    log.add("comparator", "tail = 1.5 W_in, latch = W_in / 2, reset / inverters fixed",
            "", f"tail {cmp_['w_tail']}, nlatch {cmp_['w_ln']}, platch {cmp_['w_lp']} um")

    # ---------------------------------------------------------------- sampling switches
    t_track = 0.85 * T
    tau_s = t_track / ln_settle
    # the shared top-plate switch carries the charge of the whole array, so it gets 3/4 of the budget
    r_unit = tau_s / 4 / cu
    r_top = 3 * tau_s / 4 / c_tot
    # transmission-gate flavour with the lowest worst-case (corner / temperature / supply) R_on * W
    worst = char["ron_tg_worst_ohm_um"]
    flavor = min(worst, key=worst.get)
    rw_tg = worst[flavor]
    log.add("sampling", "TG device flavour = lowest worst-case R_on W (ss/-40C, ss/125C, tt/-10% supply)",
            ", ".join(f"{k}: {v / 1e3:.1f} kOhm um" for k, v in worst.items()), f"{flavor} transistors")
    in_wn = _ceil(max(rw_tg / r_unit, W_MIN))
    log.add("sampling", "tau = T_track / ln(2^N / settle_lsb); 1/4 bit switch, 3/4 top switch",
            f"T_track = {t_track * 1e9:.2f} ns, tau <= {tau_s * 1e12:.0f} ps",
            f"R_unit <= {r_unit / 1e3:.1f} kOhm, R_top <= {r_top:.0f} Ohm")
    log.add("sampling", "W_n = (R_on W)_TG,worst / R  (Wp = 2 Wn), bit-i switch = 2^i units",
            f"worst (R_on W) = {rw_tg / 1e3:.2f} kOhm um ({char['ron_worst_where'].get('tg_' + flavor, 'tt')})",
            f"unit TG {in_wn:.2f}/{2 * in_wn:.2f} um")
    # The top-plate switch only ever passes Vcm, so it is sized for its on-resistance at Vcm; but it alone holds the
    # floating top plate during the conversion, so it must not leak when hot. Worst case: a near-full-scale input
    # leaves the plate Vref / 2^(k+1) from Vcm while bit k is tried (one clock period each); the leaked charge over
    # C_total is estimated per flavour (pessimistic: the leakage falls as the plate drifts back). Among flavours at
    # most TOP_W_CAP x wider than the narrowest, the least leaky one is taken (verified at 4, 6 and 8 bit,
    # studies/top_switch_trials.py: hot and cold corners).
    leak = char["tg_leak_hot_a_per_um"]
    cand = []
    for fl, rw in char["ron_tg_vcm_worst_ohm_um"].items():
        wn = _ceil(max(rw / r_top, W_MIN))
        cand.append((fl, rw, wn, sum(leak[fl][:N]) * wn * T / c_tot / lsb))
    w_cap = TOP_W_CAP * min(c[2] for c in cand)
    top_flavor, rw_top, top_wn, droop = min((c for c in cand if c[2] <= w_cap), key=lambda c: c[3])
    log.add("sampling", f"top-plate switch: sized at Vcm; least hot-leakage flavour among those <= {TOP_W_CAP:g}x the "
                        f"narrowest (plate droop per conversion, {char.get('tg_leak_where', 'hot')}, plate Vref/2^(k+1) "
                        f"from Vcm while bit k is tried; budget {TOP_DROOP_LSB} LSB)",
            ", ".join(f"{f}: {w:.1f} um, {d:.2g} LSB" for f, _, w, d in cand),
            f"{top_flavor}: top TG {top_wn:.2f}/{2 * top_wn:.2f} um ({rw_top / 1e3:.2f} kOhm um at Vcm, {droop:.3f} LSB"
            f"{'' if droop <= TOP_DROOP_LSB else ' - OVER BUDGET'})")

    # ---------------------------------------------------------------- DAC drivers
    t_dac = 0.45 * T                          # DAC must settle before the comparator clock
    tau_d = t_dac / ln_settle
    r_drv = tau_d / cu / 2                    # driver + top-plate redistribution, 2x margin
    drv = dict(wn=_ceil(max(char.get("ron_n_worst_ohm_um", char["ron_n_ohm_um"]) / r_drv, W_MIN)),
               wp=_ceil(max(char.get("ron_p_worst_ohm_um", char["ron_p_ohm_um"]) / r_drv, W_MIN)))
    log.add("DAC driver", "tau = 0.45 Tclk / ln(2^N / settle_lsb), per unit cap (binary scaled)",
            f"tau <= {tau_d * 1e12:.0f} ps, R_unit <= {r_drv / 1e3:.1f} kOhm",
            f"unit NMOS {drv['wn']:.2f} um, unit PMOS {drv['wp']:.2f} um")

    design = dict(
        bits=N, cu=dict(side=side, c=cu, c_total=c_tot, sigma_u=a_c / side),
        cmp=cmp_, sw=dict(in_wn=in_wn, in_wp=2 * in_wn, top_wn=top_wn, top_wp=2 * top_wn, flavor=flavor,
                          top_flavor=top_flavor),
        drv=drv, l_sw=L_MIN,
        timing=dict(tclk=T, t_track=t_track, t_dac=t_dac),
        noise=dict(ktc_rms=math.sqrt(kT / c_tot)),
    )
    design["log"] = list(log)
    return design


def sizing_table_md(design: dict) -> str:
    rows = ["| block | rule | numbers | result |", "|---|---|---|---|"]
    rows += [f"| {r['block']} | {r['rule']} | {r['numbers']} | **{r['result']}** |" for r in design["log"]]
    return "\n".join(rows)
