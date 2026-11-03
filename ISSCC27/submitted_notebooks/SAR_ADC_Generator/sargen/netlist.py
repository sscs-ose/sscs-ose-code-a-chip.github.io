"""SPICE netlist generation for the SAR ADC and its building blocks (SKY130 + ngspice XSPICE).

Signal naming
-------------
top          CDAC top plate = comparator input (+)
vcm          common-mode reference = comparator input (-)
bot_<i>      bottom plate of bit-i capacitor group (i = 0 is the LSB); botd = dummy cap
phis/phisb   bottom-plate sampling phase (and complement)
phit/phitb   top-plate sampling phase; opens slightly before phis (bottom-plate sampling)
clk          comparator clock (high = evaluate)
qp           comparator output, high when top < vcm  -> bit decision "keep"
bo_<i>       analog copy of output bit i, for read-out
"""

from dataclasses import dataclass

from .pdk import L_MIN, MIM, NFET, NFET_LVT, PFET, PFET_LVT, STDCELL_SPICE, TG_FLAVORS, lib_line, mim, mos

TR = 50e-12  # edge time of ideal timing sources


# ---------------------------------------------------------------- building blocks
def strongarm_subckt(c: dict) -> str:
    """StrongARM latch with output inverters. Ports: inp inn clk qp qn vdd vss."""
    L = c["l"]
    lines = [
        ".subckt strongarm inp inn clk qp qn vdd vss",
        mos("Mt", "tail", "clk", "vss", "vss", NFET, c["w_tail"], L),
        mos("Mi1", "xp", "inp", "tail", "vss", NFET, c["w_in"], c["l_in"]),
        mos("Mi2", "xn", "inn", "tail", "vss", NFET, c["w_in"], c["l_in"]),
        mos("Mn1", "outn", "outp", "xp", "vss", NFET, c["w_ln"], L),
        mos("Mn2", "outp", "outn", "xn", "vss", NFET, c["w_ln"], L),
        mos("Mp1", "outn", "outp", "vdd", "vdd", PFET, c["w_lp"], L),
        mos("Mp2", "outp", "outn", "vdd", "vdd", PFET, c["w_lp"], L),
        mos("Mr1", "outn", "clk", "vdd", "vdd", PFET, c["w_rst"], L),
        mos("Mr2", "outp", "clk", "vdd", "vdd", PFET, c["w_rst"], L),
        mos("Mr3", "xp", "clk", "vdd", "vdd", PFET, c["w_rst"], L),
        mos("Mr4", "xn", "clk", "vdd", "vdd", PFET, c["w_rst"], L),
        # qp = NOT(outp): outp is pulled low when inp < inn
        mos("Mon1", "qp", "outp", "vss", "vss", NFET, c["w_inv_n"], L),
        mos("Mop1", "qp", "outp", "vdd", "vdd", PFET, c["w_inv_p"], L),
        mos("Mon2", "qn", "outn", "vss", "vss", NFET, c["w_inv_n"], L),
        mos("Mop2", "qn", "outn", "vdd", "vdd", PFET, c["w_inv_p"], L),
        ".ends strongarm",
    ]
    return "\n".join(lines)


def top_switch_lines(sw, fl):
    """Top-plate switch to vcm: a transmission gate, or with top_flavor "nlvt" one LVT NMOS of width top_wn (the plate
    only ever connects to the fixed vcm, so the PMOS - the hot-leakage path - is not needed)."""
    flavor = sw.get("top_flavor", fl)
    if flavor == "nlvt":
        return [mos("Mttn", "top", "phit", "vcm", "0", NFET_LVT, sw["top_wn"], L_MIN)]
    return tg_lines("Mtt", "top", "vcm", "phit", "phitb", sw["top_wn"], sw["top_wp"], flavor)


# ---------------------------------------------------------------- layout-aware (LOD) netlists
def lod_lines(fingers, bulk=None, with_lod=True) -> list[str]:
    """Device cards of drawn fingers (sargen.layout.lod): one card per group of identical fingers, with each
    finger's sa / sb (with_lod=False writes the same fingers with sa = sb = 0, the model's no-stress default)."""
    from .pdk import DIFF_EXT
    bulk = bulk or {"n": "vss", "p": "vdd"}
    model = {("n", "std"): NFET, ("n", "lvt"): NFET_LVT, ("p", "std"): PFET, ("p", "lvt"): PFET_LVT}
    groups = {}
    for f in fingers:
        sa, sb = (f["sa"], f["sb"]) if with_lod else (0, 0)
        key = (f["dev"], f["kind"], f["flavor"], f["w"], f["l"], f["d"], f["g"], f["s"], sa, sb,
               f.get("shared_d", False), f.get("shared_s", False))
        groups[key] = groups.get(key, 0) + 1
    out, idx = [], {}
    for (dev, kind, fl, w, l, d, g, s_, sa, sb, shd, shs), m in groups.items():
        k = idx[dev] = idx.get(dev, -1) + 1
        # a contact bar shared with the neighbouring finger carries half its junction on each finger
        ad, pd = (0.5 if shd else 1) * w * DIFF_EXT, (0.5 if shd else 1) * 2 * (w + DIFF_EXT)
        as_, ps = (0.5 if shs else 1) * w * DIFF_EXT, (0.5 if shs else 1) * 2 * (w + DIFF_EXT)
        out.append(f"X{dev}_{k} {d} {g} {s_} {bulk[kind]} {model[kind, fl]} L={l:.3g} W={w:.4g} nf=1 "
                   f"ad={ad:.4g} as={as_:.4g} pd={pd:.4g} ps={ps:.4g} nrd={DIFF_EXT / w:.4g} nrs={DIFF_EXT / w:.4g} "
                   f"sa={sa:.4g} sb={sb:.4g} sd=0 mult={m} m={m}")
    return out


def strongarm_lod_subckt(fingers, with_lod=True) -> str:
    """The comparator as drawn: every finger and dummy of the layout, with its LOD."""
    return "\n".join([".subckt strongarm inp inn clk qp qn vdd vss"] + lod_lines(fingers, with_lod=with_lod)
                     + [".ends strongarm"])


def _unit_lod(line, unit):
    """sa / sb of the CDAC unit-cell devices (identical in every cell) into a schematic card."""
    name = line.split()[0]
    for prefix, dev in (("XMddn", "Mdn"), ("XMdp", "Mdp"), ("XMdn", "Mdn")):
        if name.startswith(prefix):
            break
    else:
        dev = "Msn" if name.endswith("n") else "Msp"
    sa, sb = unit[dev]
    return line.replace(" sa=0 sb=0 ", f" sa={sa:.4g} sb={sb:.4g} ")


def tg_lines(name, a, b, en, enb, wn, wp, flavor="std", m=1) -> list[str]:
    nm, ln, pm, lp = TG_FLAVORS[flavor]
    return [mos(f"{name}n", a, en, b, "0", nm, wn, ln, m),
            mos(f"{name}p", a, enb, b, "vdd", pm, wp, lp, m)]


# ---------------------------------------------------------------- SAR core
def wrap_extraction(path, name, pins) -> str:
    """Flat magic extraction (devices + parasitic C) wrapped as subcircuit `name` with `pins`.

    Layout pin labels carry the port names; unlabelled internal nets keep magic's names."""
    body = []
    for ln in open(path).read().splitlines():
        t = ln.split("**")[0].strip()          # drop magic's '**FLOATING' annotations
        if t and t[0] in "XCR":
            body.append(t)
    return "\n".join([f".subckt {name} {' '.join(pins)}"] + body + [f".ends {name}"])


def load_strongarm_extraction(path) -> str:
    return wrap_extraction(path, "strongarm", ["inp", "inn", "clk", "qp", "qn", "vdd", "vss"])


def switch_pins(bits):
    """Pin order of the `switches` layout cell (same as sargen.layout.cell.switch_devices)."""
    return ([f"bot_{i}" for i in range(bits)] + ["botd", "top", "vin", "vcm", "vref", "vdd", "vss",
            "phis", "phisb", "phig", "phigb", "phit", "phitb"] + [f"pg_{i}" for i in range(bits)]
            + [f"ng_{i}" for i in range(bits)])


def load_cdac_extraction(path, bits) -> list[str]:
    """Extracted CDAC (magic, with parasitics) mapped onto the testbench nets.

    Layout nets top/b<i>/bd/VSUBS become top/bot_<i>/botd/0; element names get an 'L' prefix."""
    nets = {f"b{i}": f"bot_{i}" for i in range(bits)}
    nets.update(bd="botd", VSUBS="0", top="top")
    out = []
    for ln in open(path).read().splitlines():
        t = ln.split()
        if not t or t[0][0] not in "XC":
            continue
        t[0] = t[0][0] + "L" + t[0][1:]
        t[1], t[2] = nets.get(t[1], t[1]), nets.get(t[2], t[2])
        out.append(" ".join(t))
    return out


def subckt_pins(path, name):
    """Port list of `.subckt name ...` in a SPICE file (handles '+' continuation lines)."""
    txt = open(path).read().replace("\n+", " ")
    for ln in txt.splitlines():
        t = ln.split()
        if len(t) > 1 and t[0].lower() == ".subckt" and t[1] == name:
            return t[2:]
    raise ValueError(f"subckt {name} not found in {path}")


def sar_core(design: dict, bits: int, cp_top: float = 0.0, cap_values=None, cdac_lines=None,
             sw_extracted=False, cdacsw_pins=None, lod=None) -> str:
    """CDAC + switches + comparator (transistor level).

    cap_values: optional list of 2^N ideal capacitances (bit-major, dummy last) replacing the MIM
    devices - used to separate capacitor mismatch from transistor mismatch in Monte-Carlo studies."""
    caps = iter(cap_values) if cap_values is not None else None
    def cap(name, top, bot):
        return f"C{name} {top} {bot} {next(caps):.6g}" if caps else mim(name, top, bot, cu["side"], cu["side"])
    cu, sw, drv, L = design["cu"], design["sw"], design["drv"], design["l_sw"]
    out = ["* ---- comparator", "Xcmp top vcm clk qp qn vdd 0 strongarm"]
    fl = sw.get("flavor", "std")
    if cdacsw_pins:          # compact CDAC: every unit cap with its own switch (layout extraction)
        out += ["* ---- top-plate sampling switch (to vcm)"]
        out += top_switch_lines(sw, fl)
        out += ["* ---- CDAC with per-unit switches from layout extraction",
                "Xcdacsw " + " ".join("0" if p == "vss" else p for p in cdacsw_pins) + " cdacsw"]
        if cp_top > 0:
            out.append(f"Cptop top 0 {cp_top:.4g}")
        return "\n".join(out)
    if sw_extracted:
        out += ["* ---- switch array from layout extraction",
                "Xsw " + " ".join("0" if p == "vss" else p for p in switch_pins(bits)) + " switches"]
    else:
        out.append("* ---- top-plate sampling switch (to vcm)")
        out += lod_lines(lod["topsw"], {"n": "0", "p": "vdd"}) if lod else top_switch_lines(sw, fl)
    n_head = len(out)
    for i in range(bits):
        m = 2**i
        out.append(f"* ---- bit {i}: {m} unit cap(s), binary-scaled switches")
        for u in range(m):
            if cdac_lines is None:
                out.append(cap(f"{i}_{u}", "top", f"bot_{i}"))
        # MSB stops tracking at phis and goes to Vref; the other plates keep tracking Vin until phig,
        # so the top plate moves to Vcm + (Vref - Vin)/2 first and never leaves [0, Vref]
        en, enb = ("phis", "phisb") if i == bits - 1 else ("phig", "phigb")
        if not sw_extracted:
            out += tg_lines(f"Ms{i}", f"bot_{i}", "vin", en, enb, sw["in_wn"], sw["in_wp"], fl, m)
            out.append(mos(f"Mdp{i}", f"bot_{i}", f"pg_{i}", "vref", "vdd", PFET, drv["wp"], L, m))
            out.append(mos(f"Mdn{i}", f"bot_{i}", f"ng_{i}", "0", "0", NFET, drv["wn"], L, m))
    out.append("* ---- dummy (termination) unit cap: samples vin, then grounded")
    if cdac_lines is None:
        out.append(cap("d", "top", "botd"))
    else:
        out.append("* ---- CDAC from layout extraction (MIM devices + parasitic C)")
        out += cdac_lines
    if not sw_extracted:
        out += tg_lines("Msd", "botd", "vin", "phig", "phigb", sw["in_wn"], sw["in_wp"], fl)
        out.append(mos("Mddn", "botd", "phigb", "0", "0", NFET, drv["wn"], L))
    if lod:
        out[n_head:] = [_unit_lod(ln, lod["unit"]) if ln.startswith("XM") else ln for ln in out[n_head:]]
    if cp_top > 0:
        out.append(f"Cptop top 0 {cp_top:.4g}")
    return "\n".join(out)


def sar_logic(bits: int, vdd: float) -> str:
    """Synchronous SAR logic in XSPICE digital models (idealised, zero power)."""
    dig_in = ["phis", "phig", "clkt", "en"] + [f"trial_{i}" for i in range(bits)] + \
             [f"latch_{i}" for i in range(bits)] + ["qp"]
    ana_in = " ".join(dig_in)
    dig = " ".join(f"d_{n}" for n in dig_in)
    lines = [
        "* ---- SAR logic (XSPICE)",
        f"abr_in [{ana_in}] [{dig}] adc_b",
        "aphisb d_phis d_phisb inv_d",
        "aclk [d_clkt d_en] d_clk and_d",
    ]
    outs_d, outs_a = ["d_clk"], ["clk"]
    for i in range(bits):
        lines += [
            f"aff{i} d_qp d_latch_{i} NULL d_phis d_b{i} d_b{i}n dff_d",
            f"aor{i} [d_trial_{i} d_b{i}] d_ctrl{i} or_d",
            f"apg{i} [d_ctrl{i} d_phisb] d_pg{i} nand_d",
            f"ang{i} [d_ctrl{i} d_phig] d_ng{i} nor_d",
        ]
        outs_d += [f"d_pg{i}", f"d_ng{i}", f"d_b{i}"]
        outs_a += [f"pg_{i}", f"ng_{i}", f"bo_{i}"]
    lines += [
        f"abr_out [{' '.join(outs_d)}] [{' '.join(outs_a)}] dac_b",
        ".model adc_b adc_bridge(in_low=0.7 in_high=1.1 rise_delay=1e-11 fall_delay=1e-11)",
        f".model dac_b dac_bridge(out_low=0 out_high={vdd} out_undef={vdd / 2} t_rise={TR} t_fall={TR})",
        ".model inv_d d_inverter(rise_delay=2e-11 fall_delay=2e-11)",
        ".model and_d d_and(rise_delay=2e-11 fall_delay=2e-11)",
        ".model or_d d_or(rise_delay=2e-11 fall_delay=2e-11)",
        ".model nand_d d_nand(rise_delay=2e-11 fall_delay=2e-11)",
        ".model nor_d d_nor(rise_delay=2e-11 fall_delay=2e-11)",
        ".model dff_d d_dff(clk_delay=3e-11 reset_delay=3e-11 rise_delay=2e-11 fall_delay=2e-11)",
    ]
    return "\n".join(lines)


def _cell(kind, m):
    """Drive strength for a gate that drives switches of multiplicity m."""
    size = 1 if m < 8 else 2 if m < 32 else 4 if m < 128 else 8
    return f"sky130_fd_sc_hd__{kind}_{size}"


def sar_logic_cells(bits: int) -> str:
    """Synchronous SAR logic built from SKY130 standard cells (sky130_fd_sc_hd), powered from vdd.

    Same function as sar_logic(): b_i = DFF(D = qp, CLK = latch_i, reset while sampling),
    ctrl_i = trial_i | b_i, pg_i = NAND(ctrl_i, phisb), ng_i = NOR(ctrl_i, phig).
    """
    p = "0 0 vdd vdd"                                   # VGND VNB VPB VPWR
    lines = ["* ---- SAR logic (sky130_fd_sc_hd standard cells)",
             f"Xclk clkt en {p} clk sky130_fd_sc_hd__and2_4"]
    for i in range(bits):
        m = 2**i
        lines += [
            f"Xff{i} latch_{i} qp phisb {p} bo_{i} sky130_fd_sc_hd__dfrtp_1",
            f"Xor{i} trial_{i} bo_{i} {p} ctrl_{i} sky130_fd_sc_hd__or2_1",
            f"Xpg{i} ctrl_{i} phisb {p} pg_{i} {_cell('nand2', m)}",
            f"Xng{i} ctrl_{i} phig {p} ng_{i} {_cell('nor2', m)}",
        ]
    return "\n".join(lines)


@dataclass
class Timing:
    """Phase plan of one conversion (all times relative to the conversion start)."""
    bits: int
    tclk: float

    @property
    def tconv(self):
        return (self.bits + 2) * self.tclk

    @property
    def t_top_open(self):          # sampling instant (top plate opens first)
        return 0.85 * self.tclk

    @property
    def t_bot_open(self):
        return 0.90 * self.tclk

    @property
    def t_gnd_on(self):            # non-MSB plates are grounded only after the MSB reached Vref
        return self.t_bot_open + 0.04 * self.tclk

    @property
    def t_read(self):              # all bits final, read-out instant
        return (self.bits + 1.5) * self.tclk

    def sources(self, vdd: float) -> str:
        T, Tc, N = self.tclk, self.tconv, self.bits
        p = lambda name, td, pw, per, inv=False: (  # noqa: E731
            f"V{name} {name} 0 PULSE({vdd if inv else 0} {0 if inv else vdd} "
            f"{td:.6g} {TR} {TR} {pw - TR:.6g} {per:.6g})")
        lines = ["* ---- timing (ideal sources)",
                 p("phis", 0, self.t_bot_open, Tc), p("phisb", 0, self.t_bot_open, Tc, True),
                 p("phit", 0, self.t_top_open, Tc), p("phitb", 0, self.t_top_open, Tc, True),
                 # non-MSB plates track Vin until phig, then go to ground (after the MSB is at Vref)
                 p("phig", 0, self.t_gnd_on, Tc), p("phigb", 0, self.t_gnd_on, Tc, True),
                 p("clkt", 0.5 * T, 0.45 * T, T),          # comparator clock template
                 p("en", T, N * T, Tc)]                    # enable during bit trials
        # The decision is latched at 0.80 T and the trial window ends at 0.92 T, so a rejected plate
        # returns to ground before the next plate is set (release-before-set): no top-plate glitch.
        for i in range(N):
            k = N - i                                      # bit i is tried in cycle k (MSB first)
            if i == N - 1:
                # MSB is set the moment sampling ends, so the top plate stays within
                # [Vcm - Vref/2, Vcm + Vref/2] and never forward-biases the switch junctions
                lines.append(p(f"trial_{i}", self.t_bot_open, T + 0.92 * T - self.t_bot_open, Tc))
            else:
                lines.append(p(f"trial_{i}", k * T, 0.92 * T, Tc))
            lines.append(p(f"latch_{i}", k * T + 0.80 * T, 0.04 * T, Tc))
        return "\n".join(lines)


def sar_testbench(spec, design: dict, vin_line: str, n_conv: int, *, mismatch=False,
                  cp_top=0.0, save=None, power=True, logic="cells", cap_values=None, cdac_lines=None,
                  cmp_subckt=None, sw_subckt=None, cdacsw=None, core=None, ext=None, lod=None, options="") -> str:
    """Full transient testbench with `n_conv` conversions (+1 leading dummy conversion).

    core = (netlist text, port list, subckt name): an extracted SAR core (CDAC, comparator, top-plate
    switch and SAR logic, from layout) replaces the schematic core and logic.
    ext = {"vref" | "vcm" | "vin": (R, C)}: a source reaches its node through R, with C from the node to
    ground (an on-chip decap, or a pad path); sources not named stay ideal.
    lod = sargen.layout.lod data: comparator, top-plate switch and unit-cell switches as drawn, with each
    finger's length of diffusion (the stress effect the models carry and the extraction does not write).
    options: extra simulator options (e.g. tighter tolerances)."""
    ext = ext or {}
    def src(name, line):
        if name not in ext:
            return line
        r, c = ext[name]
        return (line.replace(f" {name} 0 ", f" {name}_src 0 ", 1) +
                f"\nR{name}_ext {name}_src {name} {r:.6g}\nC{name}_ext {name} 0 {c:.6g}")
    tim = Timing(spec.bits, spec.tclk)
    tstop = (n_conv + 1) * tim.tconv
    save = save or [f"v(bo_{i})" for i in range(spec.bits)]
    meas = ""
    if power:
        t0 = tim.tconv
        meas = (f"meas tran q_vdd integ i(vdd) from={t0:.6g} to={tstop:.6g}\n"
                f"meas tran q_vref integ i(vref) from={t0:.6g} to={tstop:.6g}\n"
                f"meas tran q_vcm integ i(vcm) from={t0:.6g} to={tstop:.6g}\n"
                "print q_vdd q_vref q_vcm > power.txt\n")
    return f"""* SAR ADC {spec.bits}-bit testbench (generated by sargen)
{lib_line(spec.corner, mismatch)}
{f".include {STDCELL_SPICE}" if logic == "cells" and not core else ""}
.temp {spec.temp}
.option method=gear
{options}
{core[0] if core else (cmp_subckt or (strongarm_lod_subckt(lod["strongarm"]) if lod else strongarm_subckt(design['cmp'])))}
{sw_subckt or ''}
{cdacsw[0] if cdacsw else ''}
Vdd vdd 0 {spec.vdd}
{src("vref", f"Vref vref 0 {spec.vref}")}
{src("vcm", f"Vcm vcm 0 {spec.vcm}")}
{src("vin", vin_line)}
{tim.sources(spec.vdd)}
{_core_instance(core) if core else sar_core(design, spec.bits, cp_top, cap_values, cdac_lines,
                                          sw_extracted=bool(sw_subckt), cdacsw_pins=cdacsw[1] if cdacsw else None,
                                          lod=lod)}
{"" if core else (sar_logic_cells(spec.bits) if logic == "cells" else sar_logic(spec.bits, spec.vdd))}
.save {' '.join(save)} i(vdd) i(vref) i(vcm)
.tran {spec.tclk / 100:.4g} {tstop:.6g} 0 {spec.tclk / 25:.4g}
.control
set wr_singlescale
set wr_vecnames
option numdgt=8
run
wrdata wave.txt {' '.join(save)}
{meas}quit
.endc
.end
"""


def _core_instance(core):
    _, pins, name = core
    return "* ---- SAR core from layout extraction\nXcore " + " ".join("0" if p == "vss" else p for p in pins) + f" {name}"


def comparator_mc_testbench(spec, design: dict, n_inst: int, vspan: float, n_steps: int,
                            tclk: float, cmp_subckt=None) -> str:
    """`n_inst` comparators with independent mismatch, inp ramped across vcm +- vspan.
    cmp_subckt: an extracted `strongarm` subcircuit in place of the schematic one."""
    tstop = (n_steps + 1) * tclk
    inst = "\n".join(f"Xc{k} inp vcm clk qp{k} qn{k} vdd 0 strongarm" for k in range(n_inst))
    saves = " ".join(f"v(qp{k})" for k in range(n_inst))
    return f"""* comparator offset Monte Carlo (generated by sargen)
{lib_line(spec.corner, mismatch=True)}
.temp {spec.temp}
{cmp_subckt or strongarm_subckt(design['cmp'])}
Vdd vdd 0 {spec.vdd}
Vcm vcm 0 {spec.vcm}
Vinp inp 0 PWL(0 {spec.vcm - vspan} {tstop:.6g} {spec.vcm - vspan + 2 * vspan * (n_steps + 1) / n_steps})
Vclk clk 0 PULSE(0 {spec.vdd} {0.5 * tclk:.6g} {TR} {TR} {0.45 * tclk - TR:.6g} {tclk:.6g})
{inst}
.save {saves}
.tran {tclk / 100:.4g} {tstop:.6g} 0 {tclk / 25:.4g}
.control
set wr_singlescale
set wr_vecnames
run
wrdata wave.txt {saves}
quit
.endc
.end
"""


def unit_cells() -> dict:
    """Names of the primitive devices (for reporting)."""
    return dict(nfet=NFET, pfet=PFET, mim=MIM)
