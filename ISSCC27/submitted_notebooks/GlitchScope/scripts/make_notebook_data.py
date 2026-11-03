"""Precompute everything the notebook plots (light enough to rerun: ~10 min).
Heavy SPICE references (data/m2, data/bench/spice_ref_*) are produced by their own scripts."""
import sys, json, random, csv, statistics
from dataclasses import replace
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
import numpy as np
from glitchscope.verilog import read_verilog, read_design
from glitchscope.liberty import parse_liberty_file, LibertyDelayProvider
from glitchscope.model import ps_to_fs, Cell
from glitchscope.sim import PulseSimulator
from glitchscope.m2model import M2Model
from glitchscope.analyze import EnergyModel, analyze
from glitchscope.seq import read_vcd, read_clk_to_q, build_cycles
from glitchscope.test_support import lib_path_or_none
OUT = ROOT / "data/notebook"; OUT.mkdir(parents=True, exist_ok=True)
L = lib_path_or_none(); lib = parse_liberty_file(L); dp = LibertyDelayProvider(lib); m2 = M2Model()
mk = lambda net, m, **kw: PulseSimulator(net, dp, m, r_filter=m2, default_input_slew_fs=ps_to_fs(40), **kw)

# 1) benchmark energy split under M0/M1/M2 (SPICE-scaled energy), 300 random vectors
bench = {}
for b in ["rca8", "ks8", "cmp8", "mul4"]:
    net = read_verilog(ROOT / f"bench/netlists/{b}.v"); em = EnergyModel(L, net, spice_scale=True)
    rnd = random.Random(7); vecs = [{p: rnd.randint(0, 1) for p in net.primary_inputs} for _ in range(300)]
    bench[b] = {m: analyze(mk(net, m), em, vecs)["totals"] for m in ["M0", "M1", "M2"]}
    bench[b]["cells"] = len(net.cells)
(OUT / "bench_energy.json").write_text(json.dumps(bench, indent=1))
print("bench done")

# 2) MAC per-cycle energy: GlitchScope vs SPICE reference (15 cycles after 3 reset cycles)
design = read_design(ROOT / "bench/netlists/mac.v", lib); net = design.network
dcap = {f.d: lib.cells[f.libcell].pin_capacitance.get("D", 0.0) for f in design.flops}
waves, _ = read_vcd(ROOT / "bench/sim/mac.vcd")
init, cycles, edges = build_cycles(design, waves, lib, read_clk_to_q(L, {f.libcell for f in design.flops}),
                                   mk(net, "M1", primary_output_load_ff_by_net=dcap).loads)
st = dict(init)
for cyc in cycles[:3]:
    for _, u in cyc: st.update(u)
sel = cycles[3:18]
ref = json.loads((ROOT / "data/bench/spice_ref_mac_15.json").read_text())
mac = {"spice": [r["E_fJ"] for r in ref]}
pex = ROOT / "data/bench/spice_ref_mac_15_pex.json"          # parasitic-extracted cells (the reference)
if pex.exists():
    mac["spice_schematic"], mac["spice"] = mac["spice"], [r["E_fJ"] for r in json.loads(pex.read_text())]
for m, cal in [("M0", False), ("M2", True)]:
    a = analyze(mk(net, m, primary_output_load_ff_by_net=dcap), EnergyModel(L, net, spice_scale=cal), sel, initial=st)
    mac[f"{m}{'_CAL' if cal else ''}"] = [v["E_fun"] + v["E_glitch"] for v in a["per_vector"]]
(OUT / "mac_per_cycle.json").write_text(json.dumps(mac, indent=1))
print("mac per-cycle done")

# 3) buffer path-balancing sweep on tight-skew targets
def ins(net, target, pin, n):
    cells = [c for c in net.cells if c.name != target]; t = [c for c in net.cells if c.name == target][0]; src = t.inputs[pin]
    for i in range(n):
        o = f"{target}_b{i}"
        cells.append(Cell(f"{target}_B{i}", "BUF", {"A": src}, o, 1000, 1000, library_cell="sky130_fd_sc_hd__buf_1", library_output_pin="X")); src = o
    cells.append(replace(t, inputs={**t.inputs, pin: src})); return replace(net, cells=cells)
sweep = {}
for b, target in [("mul4", "_41_"), ("mul4", "_36_"), ("rca8", "_53_")]:
    net = read_verilog(ROOT / f"bench/netlists/{b}.v"); rnd = random.Random(7)
    vecs = [{p: rnd.randint(0, 1) for p in net.primary_inputs} for _ in range(300)]
    pin = statistics.mode(r["lead_pin"] for r in csv.DictReader(open(ROOT / f"data/bench/skew_{b}.csv")) if r["cell"] == target)
    T0 = analyze(mk(net, "M2"), EnergyModel(L, net, spice_scale=True), vecs)["totals"]
    rows = []
    for n in range(0, 9):
        nn = ins(net, target, pin, n) if n else net
        T = analyze(mk(nn, "M2"), EnergyModel(L, nn, spice_scale=True), vecs)["totals"]
        rows.append(dict(n_buf=n, d_glitch_pct=100 * (T["E_glitch_fJ"] - T0["E_glitch_fJ"]) / T0["E_glitch_fJ"],
                         d_total_pct=100 * (T["E_total_fJ"] - T0["E_total_fJ"]) / T0["E_total_fJ"]))
    sweep[f"{b}/{target}"] = dict(pin=pin, rows=rows)
(OUT / "balance_sweep.json").write_text(json.dumps(sweep, indent=1))
print("balance sweep done")
