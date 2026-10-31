"""Transistor-level transmitter core (full-chip step C1, see PLAN.md).

Signal path (all SKY130 devices except the stimulus and the ideal bias current):
  thermometer data bits -> I and Q unary current-steering DACs (31 cells each:
  current source W0.5/L1 as in design D1 + differential data-switch pair)
  -> the DAC's two output currents are the tails of a Gilbert switching quad
  driven by LO_I (or LO_Q) -> both quads share one differential load
  (I and Q sum at RF) -> differential-pair PA driver -> RF out.
LO path: external LO (sine) -> RC-CR (res_high_po_1p41 + cap_mim, v2 as laid out)
  -> AC-coupled self-biased inverter limiter + inverter chain -> LO and LOb.

Timing: LO 200 MHz, DAC update 25 MS/s (8 LO cycles per DAC sample).
"""
import sys
from pathlib import Path

import numpy as np

import bias_ref
import lo
from spice import PDK_LIB, mc_control, run_netlist

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "analysis"))

import os

N_UNITS = 31
# design variants (step 2d, PLAN.md): "base" = the laid-out core; "palin" = source-degenerated
# PA (split tail, R_DEG between the sources, loads x2); "bigdac" = DAC units 4x area, same W/L
VARIANT = os.environ.get("TX_VARIANT", "base")
N_DEG = int(os.environ.get("TX_NDEG", "2"))       # palin: degeneration = N_DEG x 311-ohm segments
W_U, L_U = (1.0, 2.0) if VARIANT == "bigdac" else (0.5, 1.0)   # DAC current source (design D1)
IREF = 10e-6
W_SW, L_SW = 1.0, 0.15           # DAC data switches
W_MX, L_MX = 4.0, 0.15           # mixer switching quad
R_LOAD, C_LOAD = 1500.0, 0.25e-12
W_PA, L_PA, I_PA, R_PA = 10.0, 0.15, 1e-3, 300.0
FLO, FS = 200e6, 25e6
# supply-drift runs: TX_VARIANT=vdd162 / vdd198 = the base circuit at 1.62 / 1.98 V (data-bit drive
# levels follow the supply); "more_a"/"more_b" = the base circuit, separate run directories
VDD = float(VARIANT[3] + "." + VARIANT[4:]) if VARIANT.startswith("vdd") else 1.8   # vdd1764 -> 1.764 V
# LDO variants (item 2c, full version): ldo330 / ldo297 ... = the core supplied by the on-chip LDO
# (sim/ldo.py, bandgap reference) from an external VIN of 3.30 / 2.97 ... V; data bits stay at 1.8 V
LDO = VARIANT.startswith("ldo")
VIN_EXT = float(VARIANT[3] + "." + VARIANT[4:]) if LDO else None
# mismatch sensitivity: scales the mismatch of every device model that uses SKY130's MC_MM_SWITCH:
# MOSFETs, poly resistors (xhigh_po, high_po) and MIM capacitors; not the generic n-diffusion resistor
MM_SCALE = float(os.environ.get("TX_MMSCALE", "1"))
T_RISE = 0.2e-9
NF, PF = "sky130_fd_pr__nfet_01v8", "sky130_fd_pr__pfet_01v8"


def thermometer(codes):
    """codes (n,) ints 0..31 -> bits (31, n) 0/1 (unit k on iff k < code)."""
    return (np.arange(N_UNITS)[:, None] < codes[None, :]).astype(int)


def pwl(name, node, bits):
    """PWL voltage source from a 0/1 sequence at FS with finite edges."""
    pts, ts = [], 1 / FS
    for i, b in enumerate(bits):
        v = VDD * b
        t0 = i * ts
        pts += [f"{t0 + (T_RISE if i else 0):.4e} {v}", f"{t0 + ts:.4e} {v}"]
    return f"V{name} {node} 0 PWL({' '.join(pts)})"


def inverter(name, a, y, wn=1.0, wp=2.0):
    return [f"X{name}n {y} {a} 0 0 {NF} W={wn} L=0.15", f"X{name}p {y} {a} vdd vdd {PF} W={wp} L=0.15"]


# SKY130 passives replacing the ideal ones (values calibrated in sim/test/rcal.sp)
def RES(name, a, b, kind):
    """SKY130 resistor(s) exactly as laid out (wide 1.41/5.73 um bodies; the
    0.35 um variants fail the RPM/URPM marker-width rule). Values calibrated in
    sim/test/rcal2.sp: load 1.55k, pa 311, 20k 20.2k, 50k 50.2k, 200k 200.9k."""
    model, length, segs = {"load": ("sky130_fd_pr__res_high_po_1p41", 5.6, 1),
                           "pa":   ("sky130_fd_pr__res_high_po_5p73", 4.3, 1),
                           "20k":  ("sky130_fd_pr__res_xhigh_po_1p41", 14.1, 1),
                           "50k":  ("sky130_fd_pr__res_xhigh_po_1p41", 35.25, 1),
                           "200k": ("sky130_fd_pr__res_xhigh_po_1p41", 35.25, 4)}[kind]
    nodes = [a] + [f"{name}_s{i}" for i in range(1, segs)] + [b]
    lines = [f"X{name}{'' if segs == 1 else f'_{i}'} {nodes[i]} {nodes[i + 1]} 0 {model} L={length} mult=1 m=1"
             for i in range(segs)]
    return "\n".join(lines)


def CAP(name, a, b, side):
    return f"X{name} {a} {b} sky130_fd_pr__cap_mim_m3_1 W={side} L={side} MF=1 m=1"


REAL = True     # False: the first (ideal-passive) version used in step C1/C2


STDCELLS = Path.home() / ".volare/sky130A/libs.ref/sky130_fd_sc_hd/spice/sky130_fd_sc_hd.spice"


def sc_inv(name, a, y, size):
    """SkyWater standard-cell inverter (same cell as in the layout)."""
    return f"X{name} {a} 0 0 vdd vdd {y} sky130_fd_sc_hd__inv_{size}"


def lo_limiter(tag, vin):
    """AC-coupled self-biased inverter + chain -> lo_<tag>, lob_<tag>."""
    if REAL:
        return [CAP(f"Cc_{tag}", vin, f"g_{tag}", 3), RES(f"Rfb_{tag}", f"g_{tag}", f"a1_{tag}", "200k"),
                sc_inv(f"L1{tag}", f"g_{tag}", f"a1_{tag}", 2), sc_inv(f"L2{tag}", f"a1_{tag}", f"a2_{tag}", 4),
                sc_inv(f"L3{tag}", f"a2_{tag}", f"lob_{tag}", 8), sc_inv(f"L4{tag}", f"lob_{tag}", f"lo_{tag}", 8)]
    head = [f"Cc_{tag} {vin} g_{tag} 20f", f"Rfb_{tag} g_{tag} a1_{tag} 1Meg"]
    return [*head,
            *inverter(f"L1{tag}", f"g_{tag}", f"a1_{tag}"),
            *inverter(f"L2{tag}", f"a1_{tag}", f"a2_{tag}", 2, 4),
            *inverter(f"L3{tag}", f"a2_{tag}", f"lob_{tag}", 4, 8),
            *inverter(f"L4{tag}", f"lob_{tag}", f"lo_{tag}", 4, 8)]


def dac_and_quad(ch, codes, lo, lob):
    """one channel: DAC cells feeding a switching quad onto outp/outn. With REAL the
    reference current comes from the on-chip bias reference (bias_ref.py), otherwise
    from an ideal source."""
    lines = ([] if REAL else [f"Iref_{ch} vdd g{ch} {IREF}"]) + [f"XREF{ch} g{ch} g{ch} 0 0 {NF} W={W_U} L={L_U}"]
    bits = thermometer(codes)
    for k in range(N_UNITS):
        lines += [f"XU{ch}{k} n{ch}{k} g{ch} 0 0 {NF} W={W_U} L={L_U}",
                  f"XSP{ch}{k} tp{ch} d{ch}{k} n{ch}{k} 0 {NF} W={W_SW} L={L_SW}",
                  f"XSN{ch}{k} tn{ch} db{ch}{k} n{ch}{k} 0 {NF} W={W_SW} L={L_SW}",
                  pwl(f"d{ch}{k}", f"d{ch}{k}", bits[k]),
                  pwl(f"db{ch}{k}", f"db{ch}{k}", 1 - bits[k])]
    lines += [f"XQ1{ch} outp {lo} tp{ch} 0 {NF} W={W_MX} L={L_MX}",
              f"XQ2{ch} outn {lob} tp{ch} 0 {NF} W={W_MX} L={L_MX}",
              f"XQ3{ch} outn {lo} tn{ch} 0 {NF} W={W_MX} L={L_MX}",
              f"XQ4{ch} outp {lob} tn{ch} 0 {NF} W={W_MX} L={L_MX}"]
    return lines


def passives_ideal():
    return [f"RLp vdd outp {R_LOAD}", f"RLn vdd outn {R_LOAD}", f"CLp outp 0 {C_LOAD}", f"CLn outn 0 {C_LOAD}",
            "Ccp outp pg 2p", "Ccn outn ng 2p", "Rbp pg vb 20k", "Rbn ng vb 20k", "Vb vb 0 0.9",
            f"Itail ptail 0 {I_PA}", f"RPAp vdd rfp {R_PA}", f"RPAn vdd rfn {R_PA}"]


def passives_real():
    """mixer loads, PA coupling/bias/loads as SKY130 devices; PA tail = NMOS mirror
    (x10) from an external 100 uA reference pin; PA gate bias from a resistor divider."""
    return [RES("RLp", "vdd", "outp", "load"), RES("RLn", "vdd", "outn", "load"),
            CAP("CLp", "outp", "0", 11), CAP("CLn", "outn", "0", 11),
            CAP("Ccp", "outp", "pg", 30), CAP("Ccn", "outn", "ng", 30),   # 30 um: the MIM generator maximum (was 31 until 2026-10-25)
            RES("Rbp", "pg", "vb", "20k"), RES("Rbn", "ng", "vb", "20k"),
            RES("Rv1", "vdd", "vb", "50k"), RES("Rv2", "vb", "0", "50k"),
            *bias_ref.core(outs=(("gi", 1), ("gq", 1), ("pab", 10), ("lob_bias", 10), ("ob_bias", 10))),
            f"XPAB pab pab 0 0 {NF} W=1 L=0.5", *pa_tail_and_loads()]


def pa_tail_and_loads():
    if VARIANT != "palin":
        return [f"XPAT ptail pab 0 0 {NF} W=10 L=0.5", RES("RPAp", "vdd", "pdp", "pa"), RES("RPAn", "vdd", "pdn", "pa")]
    deg = [RES(f"RDEG{i}", "ptail" if i == 0 else f"dg{i}", "ptail2" if i == N_DEG - 1 else f"dg{i + 1}", "pa")
           for i in range(N_DEG)]
    return [f"XPAT1 ptail pab 0 0 {NF} W=5 L=0.5", f"XPAT2 ptail2 pab 0 0 {NF} W=5 L=0.5", *deg,
            RES("RPAp1", "vdd", "pl_p", "pa"), RES("RPAp2", "pl_p", "pdp", "pa"),
            RES("RPAn1", "vdd", "pl_n", "pa"), RES("RPAn2", "pl_n", "pdn", "pa")]


def lo_input_buffer():
    """external LO (50-ohm source, off chip) -> pad -> 2 pF MIM coupling -> NMOS source
    follower (gate biased at VDD/2 by a 50k/50k divider) -> RC-CR input node 'in'.
    Follower sink: 200 uA, mirrored from the bias reference (100 uA x 2)."""
    return ["Rsrc s lo_pad 50",                                        # off-chip source impedance
            CAP("Clo", "lo_pad", "lo_g", 30),
            RES("Rlo1", "vdd", "lo_g", "50k"), RES("Rlo2", "lo_g", "0", "50k"),
            f"XLOF vdd lo_g in 0 {NF} W=20 L=0.15 nf=2",
            f"XLOB lob_bias lob_bias 0 0 {NF} W=1 L=0.5",
            f"XLOS in lob_bias 0 0 {NF} W=2 L=0.5"]


def output_buffer():
    """PA drains (pdp/pdn) -> NMOS source followers -> rfp/rfn, each sinking 2 mA
    (100 uA from the bias reference x 20); off chip: 10 pF AC coupling into 50 ohm."""
    return [f"XOFP vdd pdp sfp 0 {NF} W=40 L=0.15 nf=4", f"XOFN vdd pdn sfn 0 {NF} W=40 L=0.15 nf=4",
            f"XOBB ob_bias ob_bias 0 0 {NF} W=1 L=0.5",
            f"XOSP sfp ob_bias 0 0 {NF} W=20 L=0.5 nf=2", f"XOSN sfn ob_bias 0 0 {NF} W=20 L=0.5 nf=2",
            "Cxp sfp rfp 10p", "Rxp rfp 0 50", "Cxn sfn rfn 10p", "Rxn rfn 0 50"]   # off chip


# RC-CR v2 (2026-10-03, as laid out): wide 1p41 resistors (the 0p35 ones failed rpm.1), Cq top
# plate on vq; RCCR_LQ may be trimmed vs RCCR_LI to cancel the layout's quadrature error
RCCR_LI = float(os.environ.get("RCCR_LI", "25.6"))
RCCR_LQ = float(os.environ.get("RCCR_LQ", "20.3"))   # trimmed: post-layout quad error -27.7 -> -2.0 deg


def rccr_lines():
    return [f"XRi in vi 0 sky130_fd_pr__res_high_po_1p41 L={RCCR_LI} mult=1 m=1",
            f"XCi vi 0 sky130_fd_pr__cap_mim_m3_1 W={lo.C_W} L={lo.C_L} MF=1 m=1",
            f"XCq vq in sky130_fd_pr__cap_mim_m3_1 W={lo.C_W} L={lo.C_L} MF=1 m=1",
            f"XRq vq 0 0 sky130_fd_pr__res_high_po_1p41 L={RCCR_LQ} mult=1 m=1"]


def ldo_supply():
    """external VIN -> on-chip LDO -> core vdd; Vdd (0 V ammeter) keeps i(Vdd) = core current."""
    import ldo
    # nodeset: without it the operating-point search occasionally lands on a non-physical solution
    # (VOUT ~ -16 V) for some Monte Carlo chips; rshunt is a negligible 1e12-ohm convergence aid
    return [ldo.subckt(), f"Vin vin_ext 0 {VIN_EXT}", "XLDO vin_ext vdd_ldo 0 ldo", "Vdd vdd_ldo vdd 0",
            ".nodeset v(vdd)=1.8 v(xldo.ldo_vref)=1.2", ".option rshunt=1e12"]


def netlist(codes_i, codes_q, temp=27, corner="tt", n_chips=0, lo_amp=0.5, extra_save=""):
    n = len(codes_i)
    tstop = n / FS
    lines = [f"* transmitter core T={temp}", f'.lib "{PDK_LIB}" {corner}',
             *([f".param mc_mm_switch={MM_SCALE}"] if MM_SCALE != 1.0 and corner.endswith("_mm") else []),
             f".temp {temp}",
             *([f'.include "{STDCELLS}"'] if REAL else []),
             *([] if LDO else [f"Vdd vdd 0 {VDD}"]),
             # LO path: RC-CR exactly as in lo.py, then limiters
             f"Vlo s 0 dc 0 ac {lo_amp} sin(0 {lo_amp} {FLO})",
             *(lo_input_buffer() if REAL else ["Rs s in 50"]),
             *rccr_lines(),
             *lo_limiter("i", "vi"), *lo_limiter("q", "vq"),
             *dac_and_quad("i", codes_i, "lo_i", "lob_i"),
             *dac_and_quad("q", codes_q, "lo_q", "lob_q"),
             *(passives_real() if REAL else passives_ideal()),
             f"XPA1 {'pdn' if REAL else 'rfn'} pg ptail 0 {NF} W={W_PA} L={L_PA}",
             f"XPA2 {'pdp' if REAL else 'rfp'} ng {'ptail2' if REAL and VARIANT == 'palin' else 'ptail'} 0 {NF} W={W_PA} L={L_PA}",
             *(output_buffer() if REAL else []),
             # the LDO goes last so the core devices keep their Monte Carlo draws (same chips as before)
             *(ldo_supply() if LDO else [])]
    save = "  save v(rfp) v(rfn) v(outp) v(outn) v(lo_i) v(lo_q) v(vi) v(vq)" + extra_save + "\n"
    tran = f"  tran 20p {tstop:.4e} 0 20p\n  wrdata tx_out.txt v(rfp) v(rfn) v(outp) v(outn) v(lo_i) v(lo_q)\n"
    if n_chips:
        return "\n".join(lines) + mc_control(n_chips, save + tran.replace("tx_out.txt", "tx_out_$&seed.txt")) + ".end\n"
    return "\n".join(lines) + "\n.control\n" + save + tran + ".endc\n.end\n"


WORK = Path(__file__).resolve().parent / "work" / "tx"


def run(text, tag="tx", timeout=7200):
    """run in a persistent work dir; returns the work dir (waveforms stay there)."""
    import shutil
    import subprocess
    from spice import SPINIT
    d = WORK / tag
    d.mkdir(parents=True, exist_ok=True)
    shutil.copy(SPINIT, d / ".spiceinit")
    (d / "c.sp").write_text(text)
    r = subprocess.run(["ngspice", "-b", "c.sp"], cwd=d, capture_output=True, text=True, timeout=timeout)
    (d / "ngspice.log").write_text(r.stdout + r.stderr)
    return d


def _tstop(d):
    """longest transient stop time requested by the netlists (*.sp) in run directory d, or None."""
    import re
    stops = [float(m.group(1)) for sp in Path(d).glob("*.sp")
             for m in re.finditer(r"^\s*tran\s+\S+\s+(\S+)", sp.read_text(errors="replace"), re.M)]
    return max(stops) if stops else None


def load_wr(path, names=("rfp", "rfn", "outp", "outn", "lo_i", "lo_q")):
    """read an ngspice wrdata file; refuses missing, empty or truncated waveforms (a waveform must reach the
    transient stop time of the netlist that produced it, read from the *.sp files in the same directory)."""
    path = Path(path)
    if not path.exists() or path.stat().st_size == 0:
        raise ValueError(f"{path}: waveform missing or empty")
    a = np.loadtxt(path)
    if a.ndim != 2 or len(a) < 2:
        raise ValueError(f"{path}: waveform has no data rows")
    tstop = _tstop(path.parent)
    if tstop is not None and a[-1, 0] < tstop * 0.9999:
        raise ValueError(f"{path}: waveform ends at {a[-1, 0]:.4g} s but the simulation asked for {tstop:.4g} s")
    return a[:, 0], {n: a[:, 2 * i + 1] for i, n in enumerate(names)}


def qpsk_codes(n_samples, seed=0):
    """QPSK, RRC shaped (txmodel), quantized to 0..31 DAC codes; also returns x."""
    from txmodel import H_RRC, SPS
    rng = np.random.default_rng(seed)
    sym = np.exp(1j * np.pi / 4 * (2 * rng.integers(0, 4, n_samples // SPS + 2) + 1))
    up = np.zeros(len(sym) * SPS, complex)
    up[::SPS] = sym
    x = np.convolve(up, H_RRC, "same")[:n_samples]
    x /= np.abs(x).max()
    ci = np.clip(np.round((x.real + 1) / 2 * N_UNITS), 0, N_UNITS).astype(int)
    cq = np.clip(np.round((x.imag + 1) / 2 * N_UNITS), 0, N_UNITS).astype(int)
    # Preserve the actual study stimulus across platforms. Sample 44 has Q ~= 0,
    # so roundoff around code 15.5 otherwise changes Q=15 to Q=16 on Windows.
    if n_samples == 128 and seed == 1:
        words = np.loadtxt(Path(__file__).with_name("frame128_seed1.hex"), dtype=str)
        words = np.array([int(word, 16) for word in words])
        ci, cq = words >> 5, words & 31
    return ci, cq, x


def downconvert(t, v, n_samples):
    """ideal I/Q downconversion of v(t) at FLO, averaged over each DAC sample
    (skipping the first 2 LO cycles of each sample for settling)."""
    bb = v * np.exp(-2j * np.pi * FLO * t)
    out = np.empty(n_samples, complex)
    for k in range(n_samples):
        m = (t >= k / FS + 2 / FLO) & (t < (k + 1) / FS)
        out[k] = 2 * np.trapezoid(bb[m], t[m]) / (t[m][-1] - t[m][0])
    return out


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 32
    ci, cq, x = qpsk_codes(n)
    d = run(netlist(ci, cq), "nominal")
    print(open(d / "ngspice.log").read()[-600:] if not (d / "tx_out.txt").exists() else "sim ok")
    t, w = load_wr(d / "tx_out.txt")
    rf = w["rfp"] - w["rfn"]
    print(f"RF diff p-p {np.ptp(rf):.3f} V   mixer out CM {np.mean((w['outp'] + w['outn']) / 2):.3f} V   "
          f"LO_I swing {w['lo_i'].min():.2f}..{w['lo_i'].max():.2f} V")
    y = downconvert(t, rf, n)
    ideal = (2 * ci / N_UNITS - 1) + 1j * (2 * cq / N_UNITS - 1)
    h = (y @ ideal.conj()) / (ideal @ ideal.conj())          # complex gain (rotation, scale)
    err = y / h - ideal
    print(f"complex gain |h|={abs(h):.4f} V/FS  angle {np.degrees(np.angle(h)):.1f} deg")
    print(f"EVM vs ideal DAC codes: {100 * np.sqrt(np.mean(abs(err) ** 2) / np.mean(abs(ideal) ** 2)):.2f} %")
    np.savez(d / "result.npz", t=t, rf=rf, y=y, ci=ci, cq=cq)
