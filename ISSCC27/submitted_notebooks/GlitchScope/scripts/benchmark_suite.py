"""Glitch analysis of the standard benchmark suites (ISCAS'85, ISCAS'89, ITC'99, EPFL),
mapped to SKY130 HD by bench/fetch_benchmarks.py.

For every circuit: size, a clock period from GlitchScope's static timing (critical path
x 1.25), random stimulus (one random input vector per cycle; sequential circuits are
clocked), and the glitch share of dynamic energy under the three pulse models
(M0 transport, M1 inertial, M2 SPICE-calibrated), with simulation time per cycle.

    python scripts/benchmark_suite.py <liberty> [--cycles N] [--max-cells N] [name ...]

Writes data/benchmarks/suite.json (results only; the benchmark sources are not
redistributed).
"""
import argparse
import json
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from glitchscope.analyze import EnergyModel, analyze  # noqa: E402
from glitchscope.liberty import LibertyDelayProvider, parse_liberty_file  # noqa: E402
from glitchscope.m2model import M2Model, calibration_for  # noqa: E402
from glitchscope.model import ps_to_fs  # noqa: E402
from glitchscope.retime import Timing, build_rgraph  # noqa: E402
from glitchscope.seq import build_cycles, random_waves, read_clk_to_q  # noqa: E402
from glitchscope.sim import PulseSimulator  # noqa: E402
from glitchscope.verilog import read_design  # noqa: E402

NET = ROOT / "bench/external/netlists"


def study(lib_path, lib, name, n_cycles, seed=1):
    d = read_design(NET / f"{name}.v", lib)
    dp = LibertyDelayProvider(lib)
    cal = calibration_for(lib.name)
    cap = {}
    for f in d.flops:
        cap[f.d] = cap.get(f.d, 0.0) + lib.cells[f.libcell].pin_capacitance.get(f.d_pin, 0.0)
    base = PulseSimulator(d.network, dp, "M1", default_input_slew_fs=ps_to_fs(40),
                          primary_output_load_ff_by_net=cap, engine="python")
    rg = build_rgraph(d)
    c2q = read_clk_to_q(lib_path, {f.libcell for f in d.flops}) if d.flops else {}
    tm = Timing(rg, lib, dp, base.loads, clk_to_q_ps=300.0, input_delay_ps=100.0)
    _, _, crit = tm.analyze([e[3] for e in rg.edges])
    period = max(500.0, round(1.25 * crit / 100.0) * 100.0)
    waves, clock = random_waves(d, n_cycles, period, seed=seed, clock=d.clocks[0] if d.clocks else "clk")
    init, cycles, _ = build_cycles(d, waves, lib, c2q, base.loads, clock=clock, input_delay_ps=100.0)
    st = dict(init)
    for _, u in cycles[0]:                                # the first edge only loads the registers
        st.update(u)
    cycles = cycles[1:]
    em = EnergyModel(lib_path, d.network, m2_json=cal, spice_scale=True)
    row = dict(name=name, cells=len(d.network.cells), flops=len(d.flops), inputs=len(d.real_inputs),
               outputs=len(d.real_outputs), critical_path_ps=round(crit, 1), period_ps=period, cycles=len(cycles))
    for model in ("M0", "M1", "M2"):
        sim = PulseSimulator(d.network, dp, model, r_filter=M2Model(cal) if model == "M2" else None, max_reruns=5000,
                             default_input_slew_fs=ps_to_fs(40), primary_output_load_ff_by_net=cap)
        t = time.perf_counter()
        r = analyze(sim, em, cycles, initial=st)
        dt = time.perf_counter() - t
        T = r["totals"]
        row[model] = dict(glitch_share=T["glitch_fraction"], E_glitch_fJ=T["E_glitch_fJ"] / len(cycles),
                          E_functional_fJ=T["E_functional_fJ"] / len(cycles),
                          seconds_per_cycle=dt / len(cycles))
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("lib")
    ap.add_argument("names", nargs="*")
    ap.add_argument("--cycles", type=int, default=40)
    ap.add_argument("--max-cells", type=int, default=30000)
    a = ap.parse_args()
    lib = parse_liberty_file(a.lib)
    index = json.loads((NET / "index.json").read_text())
    out = ROOT / "data/benchmarks/suite.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    res = json.loads(out.read_text()) if out.exists() else {}
    names = a.names or [n for n in index if not n.endswith("_r")]
    for n in names:
        if n not in index or index[n]["cells"] == 0 or index[n]["cells"] > a.max_cells:
            continue
        try:
            row = study(a.lib, lib, n, a.cycles)
        except Exception as e:                       # noqa: BLE001
            print(f"{n:12s} FAILED {str(e)[:160]}", flush=True)
            continue
        row["suite"] = index[n]["suite"]
        res[n] = row
        out.write_text(json.dumps(res, indent=1))
        print(f"{row['suite']:8s} {n:12s} {row['cells']:6d} cells {row['flops']:5d} flops  "
              f"glitch share M0 {100 * row['M0']['glitch_share']:5.1f} %  M1 {100 * row['M1']['glitch_share']:5.1f} %  "
              f"M2 {100 * row['M2']['glitch_share']:5.1f} %   {row['M2']['seconds_per_cycle']:.2f} s/cycle", flush=True)


if __name__ == "__main__":
    main()
