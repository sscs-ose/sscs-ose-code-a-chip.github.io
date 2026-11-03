#!/usr/bin/env python
# Author: Vrinda Pandey (layout generator and sign-off scripts for this submission)
# SPDX-License-Identifier: Apache-2.0
"""RC parasitic extraction (resistance + capacitance) for vga_core_12t.

Separate from verify12t.py on purpose: verify12t.py is the signed-off, hash-pinned checker and is not changed.

    python pex_rc.py [layout/vga_core_12t.gds] [layout/vga_core_12t.spice]
        -> verify_rc/vga_core_12t_pex_rc.spice   (.subckt vga_core_12t, same pins and order as the reference)
        -> verify_rc/rc_report.txt               (checks and per-net resistance)

Steps
  1. Magic: flatten, extract with resistance, extresist, ext2spice with R and C (thresholds 0).
  2. Rename the subcircuit and order its pins like the reference; drop Magic's "**FLOATING" markers (ngspice rejects them).
  3. Correct a double count: with extresist, Magic gives every resistor-network node a capacitor to ground equal to its
     TOTAL capacitance (coupling included) AND also writes the coupling capacitors. Each net's distributed ground
     capacitors are scaled so the net's ground total equals the capacitance-only extraction (verify12t.extract),
     keeping their distribution along the wire.
  4. Verify: every net-to-net capacitance total must equal the capacitance-only extraction.
  5. Report the effective resistance from each signal pin to its farthest transistor terminal, and the RC pole.
"""
import os, re, subprocess, sys
from collections import defaultdict
from pathlib import Path
import numpy as np
import verify12t   # unchanged; used only for the capacitance-only reference extraction

TOP = "vga_core_12t"
PDK_ROOT = Path(os.environ.get("PDK_ROOT", ""))
MAGICRC = PDK_ROOT / "sky130A/libs.tech/magic/sky130A.magicrc"
SIGNAL_NETS = ["v_out", "net4", "net2", "net3", "net5", "vin_p", "vin_n", "iref", "vctrl_p", "vctrl_n"]
SCALE = {"f": 1e-15, "p": 1e-12, "a": 1e-18, "n": 1e-9, "u": 1e-6, "m": 1e-3, "k": 1e3, "meg": 1e6, "g": 1e9, None: 1.0}


def num(s):
    m = re.match(r"^([0-9.eE+-]+)(meg|[fpanumkg])?", s.lower())
    return float(m.group(1)) * SCALE[m.group(2)]


def net(node):
    return node.split(".")[0]


def magic_rc(gds, outdir):
    raw = outdir / f"{TOP}_rc_raw.spice"; raw.unlink(missing_ok=True)
    script = f"""gds read {gds}
load {TOP}
flatten {TOP}_flat
load {TOP}_flat
select top cell
cd {outdir}
extract do resistance
extract all
ext2sim labels on
ext2sim
extresist tolerance 10
extresist all
ext2spice cthresh 0
ext2spice rthresh 0
ext2spice extresist on
ext2spice subcircuit top on
ext2spice -o {raw}
quit -noprompt
"""
    r = subprocess.run(["magic", "-dnull", "-noconsole", "-rcfile", str(MAGICRC)], input=script, text=True, capture_output=True)
    (outdir / "extract_rc_magic.log").write_text(r.stdout + r.stderr)
    if not raw.exists():
        raise SystemExit("Magic wrote no RC netlist; see verify_rc/extract_rc_magic.log")
    return raw.read_text()


def caps(text):
    """net-to-net capacitance totals (F), keyed by sorted net pair; nodes of one net are merged."""
    P = defaultdict(float)
    for l in text.splitlines():
        p = l.split()
        if len(p) >= 4 and p[0][:1] == "C":
            a, b = net(p[1]), net(p[2])
            if a != b:
                P[tuple(sorted((a, b)))] += num(p[3])
    return P


def main(gds="layout/vga_core_12t.gds", ref="layout/vga_core_12t.spice"):
    gds, ref = Path(gds).resolve(), Path(ref).resolve()
    outdir = Path("verify_rc").resolve(); outdir.mkdir(exist_ok=True)
    name, pins = verify12t._ref_pins(ref)
    report = [f"RC extraction of {gds}", f"reference netlist: {ref}"]

    # capacitance-only reference, produced by the unchanged checker
    if not verify12t.extract(str(gds), str(ref), outdir=str(outdir / "c_only")):
        raise SystemExit("capacitance-only reference extraction failed")
    c_only = caps((outdir / "c_only" / f"{TOP}_pex.spice").read_text())

    txt = magic_rc(gds, outdir)
    lines = txt.splitlines()

    # 2. subcircuit name and pin order like the reference; strip FLOATING markers
    i = next(k for k, l in enumerate(lines) if l.startswith(f".subckt {TOP}_flat"))
    j = i + 1
    got = lines[i].split()[2:]
    while j < len(lines) and lines[j].startswith("+"):
        got += lines[j][1:].split(); j += 1
    if sorted(got) != sorted(pins):
        raise SystemExit(f"extracted pins {sorted(got)} differ from reference pins {sorted(pins)}")
    lines[i:j] = [f".subckt {TOP} {' '.join(pins)}"]
    lines = [re.sub(r"\s+\*\*FLOATING\s*$", "", l) for l in lines]

    # 3. correct the double-counted coupling: scale each net's capacitors to gnd to the C-only ground total
    g_rc = defaultdict(float)
    for l in lines:
        p = l.split()
        if len(p) >= 4 and p[0][:1] == "C" and "gnd" in (net(p[1]), net(p[2])) and net(p[1]) != net(p[2]):
            g_rc[net(p[2]) if net(p[1]) == "gnd" else net(p[1])] += num(p[3])
    k = {n: c_only.get(tuple(sorted((n, "gnd"))), 0.0) / v for n, v in g_rc.items() if v > 0}
    out = []
    for l in lines:
        p = l.split()
        if len(p) >= 4 and p[0][:1] == "C" and "gnd" in (net(p[1]), net(p[2])) and net(p[1]) != net(p[2]):
            n = net(p[2]) if net(p[1]) == "gnd" else net(p[1])
            p[3] = f"{num(p[3]) * k[n] * 1e15:.6g}f"
            l = " ".join(p)
        out.append(l)
    rc_file = outdir / f"{TOP}_pex_rc.spice"
    rc_file.write_text("\n".join(out) + "\n")
    rc_text = rc_file.read_text()

    # 4. verify capacitance against the C-only extraction
    rc_caps = caps(rc_text)
    worst = max(abs(rc_caps.get(key, 0) - c_only.get(key, 0)) for key in set(rc_caps) | set(c_only))
    n_r = len(re.findall(r"^R", rc_text, re.M)); n_c = len(re.findall(r"^C", rc_text, re.M)); n_x = len(re.findall(r"^X", rc_text, re.M))
    report += [f"subcircuit: .subckt {TOP} {' '.join(pins)}",
               f"elements: {n_x} transistors, {n_r} resistors, {n_c} capacitors",
               f"ngspice-ready (no **FLOATING markers): {'yes' if 'FLOATING' not in rc_text else 'NO'}",
               "ground-capacitance correction factors (C-only / raw RC): "
               + ", ".join(f"{n} {k[n]:.3f}" for n in sorted(k) if abs(k[n] - 1) > 1e-6),
               f"capacitance check vs capacitance-only extraction: largest net-pair difference {worst * 1e15:.3f} fF "
               + ("(MATCH)" if worst < 0.05e-15 else "(MISMATCH)")]

    # 5. effective resistance from each signal pin to its farthest transistor terminal
    R = defaultdict(list); term = defaultdict(set); Ctot = defaultdict(float)
    for (a, b), v in rc_caps.items():
        Ctot[a] += v; Ctot[b] += v
    for l in rc_text.splitlines():
        p = l.split()
        if len(p) >= 4 and p[0][:1] == "R" and net(p[1]) == net(p[2]):
            R[net(p[1])].append((p[1], p[2], num(p[3])))
        elif p and p[0][:1] == "X":
            for node in p[1:5]:
                term[net(node)].add(node)
    report += ["", f"{'net':8s} {'resistors':>9s} {'C total':>9s} {'R pin->farthest transistor':>27s} {'RC pole':>10s}"]
    for n in SIGNAL_NETS:
        rs = R.get(n, [])
        if not rs or n not in {x for a, b, _ in rs for x in (a, b)}:
            report.append(f"{n:8s} {len(rs):9d} {Ctot[n] * 1e15:8.1f}f {'below tolerance (~0 ohm)':>27s}")
            continue
        nodes = sorted({x for a, b, _ in rs for x in (a, b)}); idx = {x: q for q, x in enumerate(nodes)}
        L = np.zeros((len(nodes), len(nodes)))
        for a, b, v in rs:
            g = 1.0 / max(v, 1e-6); qa, qb = idx[a], idx[b]
            L[qa, qa] += g; L[qb, qb] += g; L[qa, qb] -= g; L[qb, qa] -= g
        keep = [q for q in range(len(nodes)) if q != idx[n]]
        Linv = np.linalg.pinv(L[np.ix_(keep, keep)]); pos = {q: r for r, q in enumerate(keep)}
        reff = max((Linv[pos[idx[x]], pos[idx[x]]] for x in term[n] if x in idx and x != n), default=0.0)
        f = 1 / (2 * np.pi * reff * Ctot[n]) if reff > 0 else float("inf")
        report.append(f"{n:8s} {len(rs):9d} {Ctot[n] * 1e15:8.1f}f {reff:23.1f} ohm {f / 1e9:7.2f} GHz")
    report += ["", f"netlist: {rc_file}"]
    (outdir / "rc_report.txt").write_text("\n".join(report) + "\n")
    print("\n".join(report))
    return worst < 0.05e-15


if __name__ == "__main__":
    sys.exit(0 if main(*sys.argv[1:3]) else 1)
