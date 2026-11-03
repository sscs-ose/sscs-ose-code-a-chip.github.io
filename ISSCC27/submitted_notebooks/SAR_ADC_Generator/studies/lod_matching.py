#!/usr/bin/env python3
"""Matching audit of the drawn devices and the length-of-diffusion (LOD) stress effect.

The extraction gives every finger sa = sb = 0 (stress off); SKY130's models do carry LOD.  From the generator's
finger placement (build/<N>bit/layout/lod.json, sargen.layout.lod) this study
  1. audits the matched pairs: same fingers, widths and diffusion lengths on both sides (an identical multiset
     of (w, l, sa, sb) means LOD cannot create a systematic offset);
  2. measures each device's LOD current factor: drawn fingers with sa / sb against sa = sb = 0
     (saturation, Vgs = Vds = 0.9 V, for the comparator; triode, Vgs = 1.8 V, Vds = 50 mV, for switches);
  3. simulates the comparator three ways (schematic / as drawn without LOD / as drawn with LOD, no mismatch):
     systematic offset and clock-to-output delay at 1 mV overdrive.
Writes results/<N>bit/layout/lod_matching.md.  Run inside IIC-OSIC-TOOLS:  python3 studies/lod_matching.py 8
"""
import json, sys
from collections import Counter
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sargen import SarSpec, netlist as nl
from sargen.pdk import lib_line
from sargen.spice import read_wrdata, run, run_many

PAIRS = [("Mi1", "Mi2"), ("Mn1", "Mn2"), ("Mp1", "Mp2"), ("Mr1", "Mr2"), ("Mr3", "Mr4"), ("Mon1", "Mon2"),
         ("Mop1", "Mop2"), ("Md1", "Md2"), ("Mdl1", "Mdl2")]
TCLK = 5e-9
# Tight tolerances: at ngspice's defaults the many-finger netlist resolves a regenerative latch with a numerical
# bias of ~1 mV (the same netlist reads +10 uV here, and so does the schematic).
TIGHT = ".option reltol=1e-5 abstol=1e-14 vntol=1e-8"
# the whole ADC (with its behavioural logic) does not converge at TIGHT; this is the tolerance it runs at
TIGHT_SYS = ".option reltol=1e-4"


def signature(fingers, dev):
    """Multiset of (w, l, shorter, longer diffusion length): LOD is symmetric in sa / sb."""
    return Counter((f["w"], f["l"], min(f["sa"], f["sb"]), max(f["sa"], f["sb"])) for f in fingers if f["dev"] == dev)


def current_factors(spec, blocks, out):
    """{(block, dev): (sat factor, triode factor)}: summed finger current with LOD / without."""
    cards, keys = [], []
    for blk, fingers in blocks.items():
        for dev in sorted({f["dev"] for f in fingers}):
            fs = [f for f in fingers if f["dev"] == dev]
            for mode, (vg, vd) in (("sat", (0.9, 0.9)), ("tri", (1.8, 0.05))):
                for lod in (True, False):
                    tag = f"{blk}_{dev}_{mode}_{int(lod)}"
                    p = fs[0]["kind"] == "p"
                    sgn = -1 if p else 1
                    node = lambda n: f"{n}_{tag}"
                    fix = [dict(f, d=node("d"), g=node("g"), s="vdd" if p else "0") for f in fs]
                    cards += lod_cards(fix, lod, tag)
                    cards += [f"Vd_{tag} {node('d')} {'vdd' if p else '0'} {sgn * vd}",
                              f"Vg_{tag} {node('g')} {'vdd' if p else '0'} {sgn * vg}"]
                    keys.append((blk, dev, mode, lod, tag))
    net = "\n".join(["* LOD current factors", lib_line(spec.corner, False), f".temp {spec.temp}",
                     f"Vdd vdd 0 {spec.vdd}"] + cards +
                    [".control", "op", "print " + " ".join(f"i(Vd_{k[4]})" for k in keys) + " > cur.txt", "quit",
                     ".endc", ".end"])
    d = run(net, out)
    vals = {}
    for ln in (d / "cur.txt").read_text().splitlines():
        if "=" in ln:
            k, v = ln.split("=")
            vals[k.strip().lower()] = abs(float(v))
    res = {}
    for blk, dev, mode, lod, tag in keys:
        res.setdefault((blk, dev), {}).setdefault(mode, {})[lod] = vals[f"i(vd_{tag})".lower()]
    return {k: (v["sat"][True] / v["sat"][False], v["tri"][True] / v["tri"][False]) for k, v in res.items()}


def lod_cards(fingers, with_lod, tag):
    """Device cards with instance names made unique per test."""
    return [ln.replace(" ", f"_{tag} ", 1) for ln in nl.lod_lines(fingers, {"n": "0", "p": "vdd"}, with_lod)]


def comparator(spec, sub, out, vspan=2e-3, n_steps=400):
    """Systematic offset (no mismatch) and clock-to-output delay at +-1 mV for one strongarm subcircuit."""
    sub = sub + "\n" + TIGHT
    tb = nl.comparator_mc_testbench(spec, {"cmp": {}}, 1, vspan, n_steps, TCLK, sub)
    tb = tb.replace(lib_line(spec.corner, mismatch=True), lib_line(spec.corner, mismatch=False))
    w = read_wrdata(run(tb, out / "offset") / "wave.txt")
    t = w[list(w)[0]]
    slope = 2 * vspan / (n_steps * TCLK)
    t_dec = (np.arange(n_steps) + 0.9) * TCLK
    q = np.interp(t_dec, t, w["qp0"]) > spec.vdd / 2
    flip = np.nonzero(~q)[0]
    offset = spec.vcm - vspan + slope * (t_dec[flip[0]] - 0.4 * TCLK) - spec.vcm if len(flip) else float("nan")
    delays = []
    o = 0.0 if np.isnan(offset) else offset
    for dv in (o + 1e-3, o - 1e-3):              # 1 mV either side of this comparator's own offset
        net = f"""* comparator delay
{lib_line(spec.corner, False)}
.temp {spec.temp}
{sub}
Vdd vdd 0 {spec.vdd}
Vcm vcm 0 {spec.vcm}
Vinp inp 0 {spec.vcm + dv}
Vclk clk 0 PULSE(0 {spec.vdd} {0.5 * TCLK:.6g} 50p 50p {0.45 * TCLK:.6g} {TCLK:.6g})
X1 inp vcm clk qp qn vdd 0 strongarm
.tran 1p {1.5 * TCLK:.6g}
.control
run
meas tran td when v({'qn' if dv > o else 'qp'})={spec.vdd / 2} rise=1 from={0.5 * TCLK:.6g}
print td > td.txt
quit
.endc
.end
"""
        d = run(net, out / f"delay_{'p' if dv > o else 'n'}")
        txt = (d / "td.txt").read_text()
        try:
            delays.append(float(txt.split("=")[1]) - 0.5 * TCLK - 25e-12)
        except (IndexError, ValueError):
            delays.append(float("nan"))
    return offset, delays


def main(bits=8):
    spec = SarSpec(bits=bits)
    base = Path(f"build/{bits}bit")
    design = json.loads((base / "design.json").read_text())
    var = {"before": json.loads((base / "layout" / "lod_before.json").read_text()),     # earlier layout
           "after": json.loads((base / "layout" / "lod.json").read_text())}            # end dummies, matched switch
    out = base / "studies" / "lod_matching"
    md = [f"### {bits}-bit: matched devices as drawn, before / after the end dummies", "",
          "| pair | fingers | shortest diffusion, before -> after [um] | longest [um] | identical on both sides |",
          "|---|---|---|---|---|"]
    for a, b in PAIRS:
        sig = {v: (signature(d["strongarm"], a), signature(d["strongarm"], b)) for v, d in var.items()}
        if not sig["before"][0]:
            continue
        ends = {v: [x for f in d["strongarm"] if f["dev"] == a for x in (f["sa"], f["sb"])] for v, d in var.items()}
        same = "yes" if all(x == y for x, y in sig.values()) else "**no**"
        md.append(f"| {a} / {b} | {sum(sig['after'][0].values())} | {min(ends['before']):.2f} -> {min(ends['after']):.2f} "
                  f"| {max(ends['after']):.2f} | {same} |")
    for dev in ("Mttn", "Mttp"):
        n = {v: [x for f in d["topsw"] if f["dev"] == dev for x in (f["sa"], f["sb"])] for v, d in var.items()}
        k = {v: sum(1 for f in d["topsw"] if f["dev"] == dev) for v, d in var.items()}
        md.append(f"| top switch {dev} | {k['before']} -> {k['after']} | {min(n['before']):.2f} -> {min(n['after']):.2f} "
                  f"| {max(n['after']):.2f} | - |")
    md += ["", "### Current with the drawn diffusion lengths / with the stress off (sa = sb = 0)", "",
           "| block | device | saturation, before | after | triode (switch on), before | after |", "|---|---|---|---|---|---|"]
    fac = {v: current_factors(spec, {"strongarm": d["strongarm"], "topsw": d["topsw"]}, out / f"factors_{v}")
           for v, d in var.items()}
    for key in fac["before"]:
        (sb_, tb_), (sa_, ta_) = fac["before"][key], fac["after"][key]
        md.append(f"| {key[0]} | {key[1]} | {sb_:.3f} | {sa_:.3f} | {tb_:.3f} | {ta_:.3f} |")
    sa, sb = var["after"]["unit"]["Msn"]
    md.append(f"\nCDAC unit-cell switches: stand-alone fingers, sa = sb = {sa:.2f} um in every cell (unchanged).")
    rows = []
    for name, sub in (("schematic", nl.strongarm_subckt(design["cmp"])),
                      ("before, stress off", nl.strongarm_lod_subckt(var["before"]["strongarm"], with_lod=False)),
                      ("before, with LOD", nl.strongarm_lod_subckt(var["before"]["strongarm"], with_lod=True)),
                      ("after, stress off", nl.strongarm_lod_subckt(var["after"]["strongarm"], with_lod=False)),
                      ("after, with LOD", nl.strongarm_lod_subckt(var["after"]["strongarm"], with_lod=True))):
        off, dl = comparator(spec, sub, out / name.replace(" ", "_").replace(",", ""))
        rows.append((name, off, dl))
        print(name, off, dl, flush=True)
    res = 2 * 2e-3 / 400
    md += ["", f"### Comparator as drawn, no mismatch (offset resolution {res * 1e6:.0f} uV)", "",
           "| netlist | systematic offset [uV] | delay at offset +1 mV [ps] | at offset -1 mV [ps] |", "|---|---|---|---|"]
    md += [f"| {n} | {o * 1e6:+.0f} | {d[0] * 1e12:.0f} | {d[1] * 1e12:.0f} |" for n, o, d in rows]
    dst = Path(f"results/{bits}bit/layout/lod_matching.md")
    dst.write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 8)
