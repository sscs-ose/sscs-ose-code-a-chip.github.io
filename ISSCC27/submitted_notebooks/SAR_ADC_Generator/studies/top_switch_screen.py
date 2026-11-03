#!/usr/bin/env python3
"""Top-plate switch candidates screened by DC simulation (fast): on-resistance at Vcm at the cold / slow corners vs.
off-state leakage at the hot corners, for transmission gates of different threshold flavours and channel lengths
(PMOS twice as wide as NMOS, as in the generator).  With the switch sized to the on-resistance target, the predicted
top-plate droop over one conversion is  I_leak * W_n * T_hold / C_total,  reported in LSB.
Writes results/<N>bit/sweeps/top_switch_screen.md.  Run inside IIC-OSIC-TOOLS:  python3 studies/top_switch_screen.py 8
"""
import json, re, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sargen import SarSpec, spice
from sargen.pdk import NFET, NFET_LVT, PFET, PFET_LVT, lib_line, mos

N_OPT = [("SVT", NFET, 0.15), ("SVT", NFET, 0.30), ("LVT", NFET_LVT, 0.15), ("LVT", NFET_LVT, 0.30), ("LVT", NFET_LVT, 0.50)]
P_OPT = [("SVT", PFET, 0.15), ("SVT", PFET, 0.30), ("LVT", PFET_LVT, 0.35), ("LVT", PFET_LVT, 0.50), ("LVT", PFET_LVT, 0.70)]
COLD = [("ss", -40, 1.0), ("ss", 125, 1.0), ("tt", 27, 0.9)]      # the corners the sizing step uses (characterize.py)
HOT = [("ff", 125, 1.0), ("fs", 125, 1.0), ("sf", 125, 1.0)]
V_RES = 0.89             # top plate away from Vcm while the switch is off: a near-full-scale input on the first trial


def gates(on):
    """One TG per candidate pair (Wn = 1 um, Wp = 2 um), all between node a and its own b node."""
    lines = []
    for i, (_, nm, ln) in enumerate(N_OPT):
        for j, (_, pm, lp) in enumerate(P_OPT):
            k = f"{i}{j}"
            lines += [f"Vs{k} b{k} a 0", mos(f"N{k}", f"b{k}", "gn", "x" + k, "0", nm, 1.0, ln),
                      mos(f"P{k}", f"b{k}", "gp", "x" + k, "vdd", pm, 2.0, lp), f"Vx{k} x{k} 0 {{vx}}"]
    return lines


def run(corner, temp, scale, on, vx_offset, wd):
    vdd = 1.8 * scale; vcm = vdd / 2
    lines = ["* top switch screen", lib_line(corner), f".temp {temp}", f".param vx={vcm + vx_offset}", f"Vdd vdd 0 {vdd}",
             f"Va a 0 {vcm}", f"Vgn gn 0 {vdd if on else 0}", f"Vgp gp 0 {0 if on else vdd}"] + gates(on)
    # on: current through the gate (5 mV across it); off: everything that leaves the floating plate node, i.e. the
    # channel and the plate-side junctions to substrate / n-well
    names = [f"i(v{'s' if on else 'x'}{i}{j})" for i in range(len(N_OPT)) for j in range(len(P_OPT))]
    lines += [".control", "op", "print " + " ".join(names) + " > cur.txt", "quit", ".endc", ".end"]
    d = spice.run("\n".join(lines), Path(wd))
    txt = (d / "cur.txt").read_text()
    return {"i(vs" + n[4:]: abs(float(v)) for n, v in re.findall(r"(i\(v[sx]\d+\))\s*=\s*([-0-9.eE+]+)", txt)}


def main(bits=8):
    spec = SarSpec(bits=bits)
    design = json.loads(Path(f"build/{bits}bit/design.json").read_text())
    r_top = 0.0
    for e in design["log"]:
        if "R_top" in e["result"]:
            r_top = float(e["result"].split("R_top <=")[1].split("Ohm")[0])
    c_tot = design["cu"]["c_total"]
    t_hold = (spec.cycles - 1) * spec.tclk          # the top plate floats from the end of sampling to the last decision
    base = Path(f"build/{bits}bit/studies/top_switch_screen")
    ron = {}
    for c, t, s in COLD:                              # 5 mV across each on-gate -> R = 5 mV / I
        cur = run(c, t, s, True, 0.005, base / f"on_{c}_{t}_{s}")
        for k, i in cur.items():
            ron[k] = max(ron.get(k, 0), 0.005 / i)
    leak = {}
    for c, t, s in HOT:
        for sgn in (+1, -1):
            cur = run(c, t, s, False, sgn * V_RES, base / f"off_{c}_{t}_{s}_{'p' if sgn > 0 else 'n'}")
            for k, i in cur.items():
                leak[k] = max(leak.get(k, 0), i)
    rows = []
    for i, (nf, nm, ln) in enumerate(N_OPT):
        for j, (pf, pm, lp) in enumerate(P_OPT):
            k = f"i(vs{i}{j})"
            wn = max(ron[k] / r_top, 0.42)                     # sized like the generator: R_on * W / R_top
            droop = leak[k] * wn * t_hold / c_tot / spec.lsb
            rows.append(dict(n=f"{nf} N, L {ln}", p=f"{pf} P, L {lp}", ron_kohm_um=ron[k] / 1e3, leak_na_um=leak[k] * 1e9,
                             wn=wn, droop_lsb=droop))
    rows.sort(key=lambda r: r["droop_lsb"])
    md = [f"Top-plate switch candidates for the {bits}-bit design: R_top <= {r_top:.0f} Ohm, C_total {c_tot * 1e12:.2f} pF, "
          f"hold {t_hold * 1e9:.0f} ns, LSB {spec.lsb * 1e3:.2f} mV.", "",
          "| NMOS | PMOS | R_on*Wn, cold worst [kOhm um] | plate leakage per um Wn, hot worst [nA/um] | Wn needed [um] | droop per conversion [LSB] |",
          "|---|---|---|---|---|---|"]
    md += [f"| {r['n']} | {r['p']} | {r['ron_kohm_um']:.2f} | {r['leak_na_um']:.3g} | {r['wn']:.1f} | {r['droop_lsb']:.3f} |" for r in rows]
    md.append(f"\nCold: {', '.join(f'{c} {t:+d} C x{s}' for c, t, s in COLD)}; hot: {', '.join(f'{c} {t:+d} C' for c, t, s in HOT)}; "
              f"off-state with the plate {V_RES} V above or below Vcm (worst sign).")
    out = Path(f"results/{bits}bit/sweeps/top_switch_screen.md"); out.write_text("\n".join(md) + "\n")
    (base / "rows.json").write_text(json.dumps(rows, indent=1))
    print(out.read_text())


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 8)
