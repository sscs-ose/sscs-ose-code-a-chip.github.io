"""Transistor-level SPICE of the *placed and routed* 16x16 multiplier: original, timing-driven retiming and
GlitchScope's placement, each as OpenROAD wrote it (resized cells, hold buffers, the real clock tree) with every
net's extracted wire capacitance (SPEF, lumped), all cells parasitic-extracted, real dfxtp flip-flops.

Nothing analytic remains: logic, flip-flops and clock tree are separate supplies in ngspice.  The stimulus is
exactly that of the pre-layout confirmation (scripts/spice_confirm_parallel.py, same cycles), applied at the
layouts' input delay (0.5 ns after the clock source edge, as constrained in bench/layout/orfs/constraint.sdc).

    python scripts/spice_confirm_postlayout.py run   <liberty> [--cycles 40] [--chunk 4] [--jobs N] [--tags ...]
    python scripts/spice_confirm_postlayout.py merge <liberty>
        parts  -> data/glitchfix/mul16_r/spice_parts_postlayout/<tag>_<start>.json
        result -> data/glitchfix/mul16_r/spice_postlayout.json
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
sys.path.insert(0, str(ROOT / "scripts"))
from glitchscope.liberty import parse_liberty_file  # noqa: E402
from glitchscope.optimize import GlitchFix  # noqa: E402
from glitchscope.spice.netlist_sim import simulate_design  # noqa: E402
from glitchscope.verilog import read_design  # noqa: E402
from spice_confirm_parallel import SKIP, set_cells  # noqa: E402

CASE = "mul16_r"
LAYOUTS = {"original": "v0", "timing_driven": "r_td", "glitchscope": "r_milp"}
INPUT_DELAY_PS = 500.0
OUT = ROOT / "data/glitchfix" / CASE


def stimulus(lib, n_vec):
    cfg = json.loads((OUT / "optimize.json").read_text())["config"]
    fx = GlitchFix(ROOT / cfg["netlist"], lib, random_vectors=n_vec, period_ps=cfg["period_ps"], sample=4, grid=2,
                   log=lambda m: None)
    return fx, cfg["period_ps"]


def run_chunk(lib, tag, start, length, n_vec, step_ps):
    set_cells("pex")
    fx, period = stimulus(lib, n_vec)
    lay = ROOT / "data/layout" / LAYOUTS[tag]
    design = read_design(lay / "6_final.v", parse_liberty_file(lib))
    caps = json.loads((lay / "wire_caps.json").read_text())
    a = start - SKIP
    st = {pi: fx.init0[pi] for pi in fx.design.real_inputs}
    for cyc in fx.cycles0[:a]:
        for _, upd in cyc:
            for pi in st:
                if pi in upd:
                    st[pi] = upd[pi]
    t0 = time.time()
    rows = simulate_design(design, fx.cycles0[a:start + length], fx.edges0, st, period, step_ps=step_ps,
                           save_nets=False, wire_caps=caps, clock_tree=True, input_delay_ps=INPUT_DELAY_PS)
    keep = rows[SKIP:]
    out = dict(tag=tag, start=start, cycles=list(range(start, start + length)),
               E_fJ=[r["E_fJ"] for r in keep], E_ff_fJ=[r["E_ff_fJ"] for r in keep],
               E_clk_fJ=[r["E_clk_fJ"] for r in keep], seconds=round(time.time() - t0, 1))
    p = OUT / "spice_parts_postlayout" / f"{tag}_{start}.json"
    p.parent.mkdir(exist_ok=True)
    p.write_text(json.dumps(out))
    return tag, start, out["seconds"]


def cmd_run(a):
    tags = a.tags.split(",")
    n_vec = SKIP + a.cycles + 3                       # identical to the pre-layout confirmation of this case
    pd = OUT / "spice_parts_postlayout"
    pd.mkdir(exist_ok=True)
    jobs = []
    for s in range(SKIP + 1, SKIP + 1 + a.cycles, a.chunk):
        for t in tags:
            n = min(a.chunk, SKIP + 1 + a.cycles - s)
            f = pd / f"{t}_{s}.json"
            if not (f.exists() and len(json.loads(f.read_text())["cycles"]) == n):
                jobs.append((t, s, n))
    (pd / "plan.json").write_text(json.dumps(dict(cycles=a.cycles, chunk=a.chunk, tags=tags, n_vec=n_vec,
                                                  step_ps=a.step_ps, input_delay_ps=INPUT_DELAY_PS)))
    print(f"{len(jobs)} chunks to run on {a.jobs} parallel jobs", flush=True)
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=a.jobs) as ex:
        futs = [ex.submit(run_chunk, a.lib, t, s, n, n_vec, a.step_ps) for t, s, n in jobs]
        for i, f in enumerate(as_completed(futs), 1):
            try:
                t, s, sec = f.result()
                print(f"[{i}/{len(jobs)}] {t} cycles {s}.. done in {sec:.0f} s  (elapsed {(time.time() - t0) / 60:.0f} min)",
                      flush=True)
            except Exception as e:  # noqa: BLE001
                print(f"[{i}/{len(jobs)}] FAILED: {str(e)[-500:]}", flush=True)


def cmd_merge(a):
    pd = OUT / "spice_parts_postlayout"
    plan = json.loads((pd / "plan.json").read_text())
    pre = json.loads((OUT / "spice_confirm_pex.json").read_text())["designs"]
    pre_key = {"original": "original", "timing_driven": "timing_driven", "glitchscope": "best_milp"}
    lay = json.loads((ROOT / "data/layout/summary.json").read_text())["variants"]
    res = dict(case=CASE, input_delay_ps=plan["input_delay_ps"], step_ps=plan["step_ps"], designs={})
    per = {}
    for tag in plan["tags"]:
        parts = sorted((json.loads(p.read_text()) for p in pd.glob(f"{tag}_*.json")), key=lambda r: r["start"])
        if not parts:
            continue
        cyc = [c for p in parts for c in p["cycles"]]
        lg, ff, ck = (np.array([x for p in parts for x in p[k]]) for k in ("E_fJ", "E_ff_fJ", "E_clk_fJ"))
        per[tag] = dict(zip(cyc, lg + ff + ck))
        sp = pre.get(pre_key[tag], {}).get("spice", {})
        res["designs"][tag] = dict(
            layout=LAYOUTS[tag], cycles=len(cyc), cpu_hours=round(sum(p["seconds"] for p in parts) / 3600, 2),
            logic=float(lg.mean()), flops=float(ff.mean()), clock_tree=float(ck.mean()), total=float((lg + ff + ck).mean()),
            prelayout_spice_total=sp.get("total"),
            opensta_mW=lay[LAYOUTS[tag]]["opensta_mW"]["Total"])
    rng = np.random.default_rng(1)
    if "original" in per:
        for tag in per:
            if tag == "original":
                continue
            common = sorted(set(per[tag]) & set(per["original"]))
            x = np.array([per["original"][c] for c in common]); y = np.array([per[tag][c] for c in common])
            boot = [1 - y[i].sum() / x[i].sum() for i in (rng.integers(0, len(common), len(common)) for _ in range(5000))]
            r = res["designs"][tag]
            r["saving"] = float(1 - y.sum() / x.sum())
            r["saving_ci95"] = [float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))]
            r["paired_cycles"] = len(common)
            r["saving_opensta"] = 1 - r["opensta_mW"] / res["designs"]["original"]["opensta_mW"]
    for tag, r in res["designs"].items():
        s = f"  saving {100 * r['saving']:+.1f} % [{100 * r['saving_ci95'][0]:+.1f}, {100 * r['saving_ci95'][1]:+.1f}]" if "saving" in r else ""
        print(f"{tag:14s} logic {r['logic'] / 1e3:6.2f}  flops {r['flops'] / 1e3:6.2f}  clock tree {r['clock_tree'] / 1e3:5.2f}  "
              f"total {r['total'] / 1e3:6.2f} pJ/cycle  (pre-layout SPICE {(r['prelayout_spice_total'] or 0) / 1e3:6.2f}; "
              f"OpenSTA {r['opensta_mW']:.2f} mW = {r['opensta_mW'] * 15:.1f} pJ){s}")
    (OUT / "spice_postlayout.json").write_text(json.dumps(res, indent=1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["run", "merge"])
    ap.add_argument("lib")
    ap.add_argument("--cycles", type=int, default=40)
    ap.add_argument("--chunk", type=int, default=4)
    ap.add_argument("--jobs", type=int, default=max(1, (os.cpu_count() or 2) // 2))
    ap.add_argument("--tags", default="original,timing_driven,glitchscope")
    ap.add_argument("--step-ps", type=float, default=2.0)
    a = ap.parse_args()
    cmd_run(a) if a.mode == "run" else cmd_merge(a)


if __name__ == "__main__":
    main()
