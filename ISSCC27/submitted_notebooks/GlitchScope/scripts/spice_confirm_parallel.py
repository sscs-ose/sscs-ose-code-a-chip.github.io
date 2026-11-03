"""Transistor-level confirmation of an automatic fix on a large design, in parallel.

Same measurement as ``spice_confirm_fix.py`` (every SKY130 cell and real dfxtp flip-flops
in ngspice, on exactly the stimulus GlitchScope measured), but the analysed clock cycles
are split into independent chunks that run as separate ngspice processes.  Each chunk
first replays the SKIP cycles before it so that every pipeline register holds the same
state as in one long run; only the chunk's own cycles are kept.  Because the original and
the fixed design see the same cycles, the saving gets a paired bootstrap confidence
interval over cycles.

    python scripts/spice_confirm_parallel.py run   <liberty> <case> [--cycles 48] [--chunk 4] [--jobs N]
                                                   [--tags original,timing_driven,best_cuts,best_milp]
    python scripts/spice_confirm_parallel.py merge <liberty> <case> [--cells pex]
        parts  -> data/glitchfix/<case>/spice_parts_<cells>/<tag>_<start>.json   (resumable: done parts are skipped)
        result -> data/glitchfix/<case>/spice_confirm_<cells>.json

--cells pex (default) simulates the parasitic-extracted cell netlists of scripts/extract_cells_pex.sh,
the same kind of netlist the Liberty tables were characterised on; --cells schematic uses the
PDK's schematic cell library (no diffusion or wiring capacitance).

The fixed design is the placement GlitchScope reports as its result for the case (``optimized.v``).  Peak memory is about one ngspice
process per job (supplies only are saved).
"""
import argparse
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from glitchscope.optimize import GlitchFix  # noqa: E402
from glitchscope.spice.netlist_sim import simulate_design  # noqa: E402

SKIP = 3            # cycles replayed before each chunk; must be >= the pipeline depth (2 here). A chunked
                    # run reproduces one long run to 0.01 % per cycle (mul8, checked)
PEX = "data/pdk/pex/sky130_fd_sc_hd_pex.spice"


def set_cells(cells):
    if cells == "pex":
        os.environ["GS_CELL_SPICE"] = str(ROOT / PEX)
    else:
        os.environ.pop("GS_CELL_SPICE", None)


def parts_dir(d, cells):
    return d / f"spice_parts_{cells}"


def designs(case):
    d = ROOT / "data/glitchfix" / case
    if (d / "designs.json").exists():               # explicit list: {"config": {...}, "designs": {tag: path}}
        spec = json.loads((d / "designs.json").read_text())
        return d, spec["config"], {t: ROOT / v for t, v in spec["designs"].items()}
    cfg = json.loads((d / "optimize.json").read_text())["config"]
    return d, cfg, {"original": ROOT / cfg["netlist"], "glitchscope": d / "optimized.v", "timing_driven": d / "timing_driven.v",
                    "best_cuts": d / "best_cuts.v", "best_milp": d / "best_milp.v"}


_FX = {}


def _fx(lib, path, n_vec, period):
    key = (str(path), n_vec)
    if key not in _FX:
        _FX[key] = GlitchFix(path, lib, random_vectors=n_vec, period_ps=period, sample=4, grid=2, log=lambda m: None)
    return _FX[key]


def run_chunk(lib, case, tag, start, length, n_vec, step_ps, cells):
    set_cells(cells)
    d, cfg, des = designs(case)
    fx = _fx(lib, des[tag], n_vec, cfg["period_ps"])
    a = start - SKIP                                    # first replayed cycle
    st = {pi: fx.init0[pi] for pi in fx.design.real_inputs}
    for cyc in fx.cycles0[:a]:                          # input values when cycle a starts
        for _, upd in cyc:
            for pi in st:
                if pi in upd:
                    st[pi] = upd[pi]
    t0 = time.time()
    rows = simulate_design(fx.design, fx.cycles0[a:start + length], fx.edges0, st, cfg["period_ps"],
                           step_ps=step_ps, save_nets=False)
    keep = rows[SKIP:]
    out = dict(tag=tag, start=start, cycles=list(range(start, start + length)),
               E_fJ=[r["E_fJ"] for r in keep], E_ff_fJ=[r["E_ff_fJ"] for r in keep],
               seconds=round(time.time() - t0, 1))
    p = parts_dir(d, cells) / f"{tag}_{start}.json"
    p.parent.mkdir(exist_ok=True)
    p.write_text(json.dumps(out))
    return tag, start, out["seconds"]


def cmd_run(a):
    d, cfg, des = designs(a.case)
    tags = a.tags.split(",")
    n_vec = SKIP + a.cycles + 3
    jobs = []
    for s in range(SKIP + 1, SKIP + 1 + a.cycles, a.chunk):
        for t in tags:
            n = min(a.chunk, SKIP + 1 + a.cycles - s)
            f = parts_dir(d, a.cells) / f"{t}_{s}.json"
            if not (f.exists() and len(json.loads(f.read_text())["cycles"]) == n):
                jobs.append((t, s, n))
    pd = parts_dir(d, a.cells)
    pd.mkdir(exist_ok=True)
    (pd / "plan.json").write_text(json.dumps(dict(cycles=a.cycles, chunk=a.chunk, tags=tags, cells=a.cells,
                                                  n_vec=n_vec, step_ps=a.step_ps)))
    print(f"{len(jobs)} chunks to run on {a.jobs} parallel jobs", flush=True)
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=a.jobs) as ex:
        futs = [ex.submit(run_chunk, a.lib, a.case, t, s, n, n_vec, a.step_ps, a.cells) for t, s, n in jobs]
        for i, f in enumerate(as_completed(futs), 1):
            try:
                t, s, sec = f.result()
                print(f"[{i}/{len(jobs)}] {t} cycles {s}.. done in {sec:.0f} s  "
                      f"(elapsed {(time.time() - t0) / 60:.0f} min)", flush=True)
            except Exception as e:  # noqa: BLE001
                print(f"[{i}/{len(jobs)}] FAILED: {str(e)[-500:]}", flush=True)


def cmd_merge(a):
    d, cfg, des = designs(a.case)
    pd = parts_dir(d, a.cells)
    plan = json.loads((pd / "plan.json").read_text())
    n_vec = plan["n_vec"]
    res = dict(case=a.case, cells=a.cells, period_ps=cfg["period_ps"], step_ps=plan["step_ps"], designs={})
    per_cycle = {}
    for tag in plan["tags"]:
        parts = sorted((json.loads(p.read_text()) for p in pd.glob(f"{tag}_*.json")),
                       key=lambda r: r["start"])
        if not parts:
            continue
        cyc = [c for p in parts for c in p["cycles"]]
        e = np.array([x for p in parts for x in p["E_fJ"]])
        eff = np.array([x for p in parts for x in p["E_ff_fJ"]])
        fx = GlitchFix(des[tag], a.lib, random_vectors=n_vec, period_ps=cfg["period_ps"], sample=len(cyc), grid=2,
                       log=lambda m: None)
        fx.sample_idx = cyc
        g = fx.original().energy                         # GlitchScope on exactly these cycles
        f0 = fx.design.flops[0]
        c_clk = fx.lib.cells[f0.libcell].pin_capacitance.get(f0.clk_pin, 0.0)
        e_clk = len(fx.design.flops) * (1 + fx.fe.k_tree) * c_clk * fx.fe.vdd ** 2
        gs_logic = g["functional"] + g["glitch"]
        gs_ff = g["flop_clock"] + g["flop_data"] - e_clk
        per_cycle[tag] = dict(zip(cyc, e + eff + e_clk))
        res["designs"][tag] = dict(
            file=str(des[tag].relative_to(ROOT)), flops=len(fx.design.flops), cycles=len(cyc),
            cpu_hours=round(sum(p["seconds"] for p in parts) / 3600, 2),
            spice=dict(logic=float(e.mean()), flops=float(eff.mean()), clock_network=e_clk,
                       total=float(e.mean() + eff.mean() + e_clk), logic_sd=float(e.std(ddof=1)) if len(e) > 1 else 0.0),
            glitchscope=dict(logic=gs_logic, glitch=g["glitch"], functional=g["functional"], flops=gs_ff,
                             clock_network=e_clk, total=gs_logic + gs_ff + e_clk))
    rng = np.random.default_rng(1)
    if "original" in per_cycle:
        o = res["designs"]["original"]
        for tag in per_cycle:
            if tag == "original":
                continue
            common = sorted(set(per_cycle[tag]) & set(per_cycle["original"]))
            x = np.array([per_cycle["original"][c] for c in common])
            y = np.array([per_cycle[tag][c] for c in common])
            boot = []
            for _ in range(5000):
                i = rng.integers(0, len(common), len(common))
                boot.append(1 - y[i].sum() / x[i].sum())
            r = res["designs"][tag]
            r["saving_spice"] = float(1 - y.sum() / x.sum())
            r["saving_spice_ci95"] = [float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))]
            r["saving_glitchscope"] = 1 - r["glitchscope"]["total"] / o["glitchscope"]["total"]
            r["logic_saving_spice"] = 1 - r["spice"]["logic"] / o["spice"]["logic"]
            r["logic_saving_glitchscope"] = 1 - r["glitchscope"]["logic"] / o["glitchscope"]["logic"]
            r["paired_cycles"] = len(common)
            print(f"{tag:14s} saving SPICE {100 * r['saving_spice']:+.1f} % "
                  f"[{100 * r['saving_spice_ci95'][0]:+.1f}, {100 * r['saving_spice_ci95'][1]:+.1f}]  "
                  f"GlitchScope {100 * r['saving_glitchscope']:+.1f} %   logic: SPICE "
                  f"{100 * r['logic_saving_spice']:+.1f} % / GlitchScope {100 * r['logic_saving_glitchscope']:+.1f} %  "
                  f"({len(common)} cycles)")
    for tag, r in res["designs"].items():
        s, g = r["spice"], r["glitchscope"]
        print(f"{tag:14s} flops {r['flops']:4d}  logic GS/SPICE {g['logic'] / s['logic']:.2f}  "
              f"flops GS/SPICE {g['flops'] / s['flops']:.2f}  total GS/SPICE {g['total'] / s['total']:.2f}")
    (d / f"spice_confirm_{a.cells}.json").write_text(json.dumps(res, indent=1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["run", "merge"])
    ap.add_argument("lib")
    ap.add_argument("case")
    ap.add_argument("--cycles", type=int, default=48)
    ap.add_argument("--chunk", type=int, default=4)
    ap.add_argument("--jobs", type=int, default=max(1, (os.cpu_count() or 2) // 2))
    ap.add_argument("--tags", default="original,timing_driven,best_cuts,best_milp")
    ap.add_argument("--step-ps", type=float, default=2.0)
    ap.add_argument("--cells", choices=["pex", "schematic"], default="pex")
    a = ap.parse_args()
    cmd_run(a) if a.mode == "run" else cmd_merge(a)


if __name__ == "__main__":
    main()
