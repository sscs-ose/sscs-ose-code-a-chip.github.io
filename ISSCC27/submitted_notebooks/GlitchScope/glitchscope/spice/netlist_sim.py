"""Transistor-level reference: simulate a mapped netlist in ngspice with SKY130 cells.

Applies a vector sequence (one vector per period, ramp inputs with the given
Liberty-style slew), then reports per-vector supply energy and per-net 50 %
crossing counts so GlitchScope M0/M1/M2 can be compared against SPICE.
"""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import numpy as np

from .pulse_sweep import _env, _cell_pins, cell_spice_lib, VDD, LIB_SLEW_FRAC


def _sp(n: str) -> str:
    return "n_" + n.replace("[", "_").replace("]", "_").replace("$", "_").replace(".", "_")


def build_deck(net, vectors, initial, period_ps, slew_ps, outfile, step_ps=1.0):
    pdk = Path(_env("GS_PDK_ROOT"))
    cell_lib = cell_spice_lib()
    model_lib = pdk / "libs.tech/ngspice/sky130.lib.spice"
    tr = slew_ps / LIB_SLEW_FRAC
    L = [".option scale=1e-6", f'.lib "{model_lib}" tt', f'.include "{cell_lib}"', ".temp 25",
         f"Vdd vpwr 0 {VDD}"]
    # primary inputs as PWL sources; vector k applied at t_k = (k+1)*period
    for pi in net.primary_inputs:
        v = initial[pi]
        pts = [(0.0, v)]
        for k, vec in enumerate(vectors):
            nv = vec.get(pi, v)
            if nv != v:
                t = (k + 1) * period_ps
                pts += [(t, v), (t + tr, nv)]
                v = nv
        s = " ".join(f"{t:.3f}p {val * VDD:.3f}" for t, val in pts)
        L.append(f"V_{_sp(pi)} {_sp(pi)} 0 PWL({s})")
    for c in net.cells:
        pins = _cell_pins(cell_lib, c.library_cell.split("__")[-1])
        conn = []
        for p in pins:
            if p in ("VGND", "VNB"):
                conn.append("0")
            elif p in ("VPWR", "VPB"):
                conn.append("vpwr")
            elif p == c.library_output_pin:
                conn.append(_sp(c.output))
            else:
                conn.append(_sp(c.inputs[p]))
        L.append(f"X_{_sp(c.name)} {' '.join(conn)} {c.library_cell}")
    nets = sorted({c.output for c in net.cells})
    tstop = (len(vectors) + 1) * period_ps
    L += [".control", "set wr_singlescale", "set wr_vecnames", "option numdgt=6",
          f"tran {step_ps}p {tstop}p 0 {step_ps}p",
          f"linearize",
          f"wrdata {outfile} i(Vdd) " + " ".join(f"v({_sp(n)})" for n in nets),
          "quit", ".endc", ".end"]
    return "\n".join(L) + "\n", nets


def simulate(net, vectors, initial, period_ps=3000.0, slew_ps=40.0, chunk=5):
    """Transistor-level reference, run in chunks of ``chunk`` vectors (each chunk starts
    from the settled state the previous vectors leave) to keep ngspice's waveform
    memory bounded on larger circuits (``GS_SPICE_CHUNK`` overrides it)."""
    import os
    chunk = int(os.environ.get("GS_SPICE_CHUNK", chunk))
    if chunk and len(vectors) > chunk:
        rows, state = [], dict(initial)
        for k in range(0, len(vectors), chunk):
            part = vectors[k:k + chunk]
            rows += _simulate(net, part, state, period_ps, slew_ps)
            for v in part:
                state.update(v)
        return rows
    return _simulate(net, vectors, initial, period_ps, slew_ps)


def _simulate(net, vectors, initial, period_ps=3000.0, slew_ps=40.0):
    ng = _env("GS_NGSPICE")
    with tempfile.TemporaryDirectory(prefix="gs_net_") as td:
        td = Path(td)
        out = td / "wave.txt"
        deck, nets = build_deck(net, vectors, initial, period_ps, slew_ps, out)
        (td / "deck.sp").write_text(deck)
        (td / ".spiceinit").write_text("set ngbehavior=hsa\nset ng_nomodcheck\n")
        r = subprocess.run([ng, "-b", "deck.sp"], cwd=td, capture_output=True, text=True)
        if not out.exists():
            raise RuntimeError(r.stdout[-2000:] + r.stderr[-2000:])
        d = np.loadtxt(out, skiprows=1)
    t = d[:, 0] * 1e12
    p = -d[:, 1] * VDD
    leak = float(np.mean(p[t < 0.8 * period_ps]))
    rows = []
    for k in range(len(vectors)):
        a, b = (k + 1) * period_ps, (k + 2) * period_ps
        m = (t >= a) & (t < b)
        e = float(np.trapezoid(p[m] - leak, t[m] * 1e-12)) * 1e15
        cross = {}
        for j, n in enumerate(nets):
            v = d[m, 2 + j] - VDD / 2
            cross[n] = int(np.count_nonzero(np.diff(np.sign(v)) != 0))
        rows.append({"k": k + 1, "E_fJ": e, "crossings": cross})
    return rows


def simulate_design(design, cycles, edges, warmup_inputs, period_ps, slew_ps=40.0,
                    clk_slew_ps=40.0, n_warmup=2, step_ps=1.0, save_nets=True, wire_caps=None,
                    clock_tree=False, input_delay_ps=None):
    """Transistor-level run of a sequential design (real dfxtp flops in SPICE).

    Combinational cells sit on supply ``vcomb`` and flops on ``vff`` so the
    combinational energy per cycle can be compared with GlitchScope.  The
    circuit first runs ``n_warmup`` cycles with ``warmup_inputs`` so all flops
    settle to the GlitchScope initial state; cycle k of ``cycles`` then starts
    at warm-up end + k*period.  Returns per-cycle combinational energy and
    per-net 50 % crossings (combinational nets only).

    Post-layout options: ``wire_caps`` {net: fF} adds each net's extracted (lumped) wire capacitance;
    ``clock_tree=True`` instantiates the design's clock-tree cells (``design.clock_tree``) on their own
    supply ``vclk`` between the ideal clock source and the flip-flops (``E_clk_fJ`` per cycle);
    ``input_delay_ps`` applies every input change that long after the clock source edge."""
    ng = _env("GS_NGSPICE")
    pdk = Path(_env("GS_PDK_ROOT"))
    cell_lib = cell_spice_lib()
    model_lib = pdk / "libs.tech/ngspice/sky130.lib.spice"
    net = design.network
    tr = slew_ps / LIB_SLEW_FRAC
    t0 = n_warmup * period_ps                      # time of first analysed edge
    L = [".option scale=1e-6", f'.lib "{model_lib}" tt', f'.include "{cell_lib}"', ".temp 25",
         f"Vcomb vcomb 0 {VDD}", f"Vff vff 0 {VDD}", f"Vclk vclk 0 {VDD}"]
    tcl = clk_slew_ps / LIB_SLEW_FRAC
    clk = "PULSE(0 {v} {d}p {r}p {r}p {w}p {p}p)".format(v=VDD, d=period_ps / 2 - tcl / 2, r=tcl,
                                                       w=period_ps / 2 - tcl, p=period_ps)
    # rising edges at period/2 + k*period  -> shift so analysed edge k is at t0 + period/2 + k*period
    for c in design.clocks:
        L.append(f"V_{_sp(c)} {_sp(c)} 0 {clk}")
    first_edge = period_ps / 2 + t0
    for pi in design.real_inputs:
        v = warmup_inputs.get(pi, 0)
        pw = [(0.0, v)]
        for k, cyc in enumerate(cycles):
            for off_fs, upd in cyc:
                if pi in upd and upd[pi] != v:
                    t = first_edge + k * period_ps + (off_fs / 1000.0 if input_delay_ps is None else input_delay_ps)
                    pw += [(t, v), (t + tr, upd[pi])]
                    v = upd[pi]
        L.append(f"V_{_sp(pi)} {_sp(pi)} 0 PWL({' '.join(f'{t:.3f}p {x * VDD:.3f}' for t, x in pw)})")
    for f in design.flops:
        pins = _cell_pins(cell_lib, f.libcell.split("__")[-1])
        m = {"CLK": _sp(f.clk), "D": _sp(f.d), "Q": _sp(f.q), "VGND": "0", "VNB": "0", "VPWR": "vff", "VPB": "vff"}
        L.append(f"X_{_sp(f.name)} {' '.join(m[p] for p in pins)} {f.libcell}")
    for c in net.cells:
        pins = _cell_pins(cell_lib, c.library_cell.split("__")[-1])
        conn = []
        for p in pins:
            if p in ("VGND", "VNB"):
                conn.append("0")
            elif p in ("VPWR", "VPB"):
                conn.append("vcomb")
            elif p == c.library_output_pin:
                conn.append(_sp(c.output))
            else:
                conn.append(_sp(c.inputs[p]))
        L.append(f"X_{_sp(c.name)} {' '.join(conn)} {c.library_cell}")
    for c in (getattr(design, "clock_tree", []) if clock_tree else []):
        pins = _cell_pins(cell_lib, c.library_cell.split("__")[-1])
        conn = ["0" if p in ("VGND", "VNB") else "vclk" if p in ("VPWR", "VPB") else
                _sp(c.output) if p == c.library_output_pin else _sp(c.inputs[p]) for p in pins]
        L.append(f"X_{_sp(c.name)} {' '.join(conn)} {c.library_cell}")
    if wire_caps:
        used = {_sp(n) for n in list(design.real_inputs) + list(design.clocks)} | {_sp(c.output) for c in net.cells}
        used |= {_sp(x) for c in net.cells for x in c.inputs.values()}
        used |= {_sp(x) for f in design.flops for x in (f.clk, f.d, f.q)}
        if clock_tree:
            used |= {_sp(c.output) for c in getattr(design, "clock_tree", [])}
        for i, (n, cf) in enumerate(sorted((_sp(k), v) for k, v in wire_caps.items())):
            if n in used and cf > 0:
                L.append(f"Cw{i} {n} 0 {cf:.5f}f")
    nets = sorted({c.output for c in net.cells}) if save_nets else []    # supplies only: far less memory
    tstop = first_edge + len(cycles) * period_ps
    with tempfile.TemporaryDirectory(prefix="gs_seq_") as td:
        td = Path(td); out = td / "wave.txt"
        L += [".control", "set wr_singlescale", "set wr_vecnames", "option numdgt=6"]
        if not save_nets:
            L.append("save vcomb#branch vff#branch vclk#branch")
        L += [f"tran {step_ps}p {tstop}p 0 {step_ps}p", "linearize",
              f"wrdata {out} i(Vcomb) i(Vff) i(Vclk) " + " ".join(f"v({_sp(n)})" for n in nets), "quit", ".endc", ".end"]
        (td / "deck.sp").write_text("\n".join(L) + "\n")
        (td / ".spiceinit").write_text("set ngbehavior=hsa\nset ng_nomodcheck\n")
        r = subprocess.run([ng, "-b", "deck.sp"], cwd=td, capture_output=True, text=True)
        if not out.exists():
            raise RuntimeError(r.stdout[-2000:] + r.stderr[-2000:])
        d = np.loadtxt(out, skiprows=1)
    t = d[:, 0] * 1e12
    p = -d[:, 1] * VDD
    pff = -d[:, 2] * VDD                  # flip-flop supply (clock pins: ideal source, or the clock tree)
    pclk = -d[:, 3] * VDD                 # clock-tree cells (zero unless clock_tree=True)
    rows = []
    for k in range(len(cycles)):
        a, b = first_edge + k * period_ps, first_edge + (k + 1) * period_ps
        m = (t >= a) & (t < b)
        e = float(np.trapezoid(p[m], t[m] * 1e-12)) * 1e15
        eff = float(np.trapezoid(pff[m], t[m] * 1e-12)) * 1e15
        eclk = float(np.trapezoid(pclk[m], t[m] * 1e-12)) * 1e15
        cross = {n: int(np.count_nonzero(np.diff(np.sign(d[m, 4 + j] - VDD / 2)) != 0)) for j, n in enumerate(nets)}
        rows.append({"k": k + 1, "E_fJ": e, "E_ff_fJ": eff, "E_clk_fJ": eclk, "crossings": cross})
    return rows
