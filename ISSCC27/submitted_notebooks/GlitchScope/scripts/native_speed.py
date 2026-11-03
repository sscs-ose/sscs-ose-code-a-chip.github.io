"""Speed of the compiled core against the Python engine (M2, SKY130), and the end-to-end
effect on ``analyze`` (simulation + pulse extraction + lineage + energy).

    python scripts/native_speed.py <liberty> [out.json]
"""
import json
import random
import sys
import time
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from glitchscope.analyze import EnergyModel, analyze  # noqa: E402
from glitchscope.liberty import LibertyDelayProvider, parse_liberty_file  # noqa: E402
from glitchscope.m2model import M2Model  # noqa: E402
from glitchscope.model import StimulusEpoch, ps_to_fs  # noqa: E402
from glitchscope.sim import PulseSimulator  # noqa: E402
from glitchscope.verilog import read_design, read_verilog  # noqa: E402

BENCH = [("mul4", 200), ("mac", 200), ("arraymul16", 20)]


def main():
    lib_path = sys.argv[1]
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "data/bench/native_speed.json"
    lib = parse_liberty_file(lib_path)
    dp = LibertyDelayProvider(lib)
    rows = []
    for b, nv in BENCH:
        try:
            net = read_verilog(ROOT / f"bench/netlists/{b}.v")
        except ValueError:
            net = read_design(ROOT / f"bench/netlists/{b}.v", lib).network
        rnd = random.Random(1)
        vecs = [{p: rnd.randint(0, 1) for p in net.primary_inputs} for _ in range(nv)]
        init = {p: 0 for p in net.primary_inputs}
        em = EnergyModel(lib_path, net, spice_scale=True)
        row = dict(bench=b, cells=len(net.cells), vectors=nv)
        res = {}
        for eng in ("python", "native"):
            for model in ("M1", "M2"):
                sim = PulseSimulator(net, dp, model, r_filter=M2Model() if model == "M2" else None,
                                     default_input_slew_fs=ps_to_fs(40), engine=eng)
                sim.run([StimulusEpoch(100_000, vecs[0], 1)])          # warm-up (native: build tables)
                if eng == "native":
                    sim._core.core_seconds = 0.0
                prev, t_sim, n_ev = dict(init), 0.0, 0
                for k, v in enumerate(vecs, 1):
                    sim.network = replace(net, initial_inputs=dict(prev))
                    t = time.perf_counter()
                    r = sim.run([StimulusEpoch(100_000, v, k)])
                    t_sim += time.perf_counter() - t
                    n_ev += len(r["trace"])
                    prev = v
                row[f"{model}_{eng}_sim_s"] = round(t_sim, 3)
                if eng == "native":
                    row[f"{model}_native_kernel_s"] = round(sim._core.core_seconds, 3)
                row[f"{model}_events"] = n_ev
            sim = PulseSimulator(net, dp, "M2", r_filter=M2Model(), default_input_slew_fs=ps_to_fs(40), engine=eng)
            t = time.perf_counter()
            res[eng] = analyze(sim, em, vecs, initial=init)["totals"]
            row[f"analyze_{eng}_s"] = round(time.perf_counter() - t, 3)
        row["identical_totals"] = res["python"] == res["native"]
        for model in ("M1", "M2"):
            row[f"{model}_speedup"] = round(row[f"{model}_python_sim_s"] / max(1e-9, row[f"{model}_native_sim_s"]), 1)
            row[f"{model}_kernel_speedup"] = round(row[f"{model}_python_sim_s"] /
                                                   max(1e-9, row[f"{model}_native_kernel_s"]), 1)
        row["analyze_speedup"] = round(row["analyze_python_s"] / max(1e-9, row["analyze_native_s"]), 1)
        rows.append(row)
        print(json.dumps(row), flush=True)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(dict(library=lib.name, rows=rows), indent=1))
    print("wrote", out)


if __name__ == "__main__":
    main()
