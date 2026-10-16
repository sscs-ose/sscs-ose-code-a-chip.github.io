"""Day-4 design-space search: surrogate fit, exhaustive enumeration, optimizer comparison.

1. accuracy table: validation accuracy of every distinct accuracy configuration (P never
   changes accuracy), from the bit-accurate model with the chip's own training recipe
2. surrogate: area / power fitted on the real LibreLane rows (results/flow_runs.csv),
   scored by leave-one-out MAPE; candidates use the Yosys block-model estimates as features
3. enumeration of the whole core space -> ground-truth Pareto front
4. random search vs NSGA-II vs Bayesian optimization (Optuna TPE) at equal evaluation
   budgets over several seeds, scored by hypervolume gap to the ground-truth front

    python exp_day4_search.py            # full run (accuracy table is cached)
    python exp_day4_search.py --plot     # re-plot from results/day4_*.csv (REPLAYED)
"""
import argparse
import copy
import csv
import itertools
import math
import multiprocessing as mp
import os
import time

import numpy as np

import area_model as AM
import data
import hdc_model as H
from exp_day4_model import split_subject
from exp_day1 import FIGS, INK2, RES, SERIES, SURF, _style, _tag, read_csv, write_csv

F, Q, C, CLOCK_NS = 64, 16, 6, 20.0
ACC_SEEDS = range(3)
OPT_SEEDS = range(10)
BUDGETS = [25, 50, 100, 150, 200, 300]
GENES = dict(D=[256, 512, 1024, 2048], P=[32, 64, 128],
             sim=[("exact", 0), ("trunc", 1), ("satcomp", 2), ("satcomp", 3), ("sampled", 4)],
             learn=[0, 1, 2], w=list(range(2, 9)), k=list(range(0, 5)))
# All minimized. Power is NOT an objective: vectorless STA power from the flow is not
# physically consistent across designs (default activities blow up through the XOR/hash
# logic), so it is reported but not optimized; final points get VCD-annotated power.
# err = 1 - accuracy on NEW users after the chip streams part of their data (test-then-
# train; frozen if learning is off): the reason on-chip learning exists. Static accuracy
# (offline training only) is kept as a column for comparison.
OBJ = ["err", "area_mm2", "latency_us"]


def space():
    """Every legal design point (learning-off designs have no counters: w, k fixed)."""
    pts = []
    for D, P, (v, kn), learn in itertools.product(GENES["D"], GENES["P"], GENES["sim"], GENES["learn"]):
        for w, k in (itertools.product(GENES["w"], GENES["k"]) if learn else [(8, 0)]):
            pts.append(dict(D=D, P=P, variant=v, knob=kn, learn=learn, w=w, k=k))
    return pts


def acc_key(p):
    return (p["D"], p["variant"], p["knob"], p["learn"], p["w"], p["k"])


# ------------------------------------------------------------------ 1. accuracy table
_G = {}


def _acc_setup():
    d = data.load(F, Q)
    _G["ytr"], _G["yva"] = d["train"][1], d["val"][1]
    sva = d["val"][2]
    _G["val_split"] = [tuple(np.flatnonzero(sva == s)[i] for i in split_subject(_G["yva"][sva == s]))
                       for s in sorted(set(sva.tolist()))]
    for s in ACC_SEEDS:
        im = H.item_memory(F, Q, s)
        Qv = H.encode(d["val"][0], im)
        _G[s] = (im, H.encode(d["train"][0], im), H.pack(Qv), Qv)


def _acc_task(key):
    D, v, kn, learn, w, k = key
    sim, accs, adapt = H.Similarity(v, kn), [], []
    for s in ACC_SEEDS:
        im, Qtr, Qva, _ = _G[s]
        if learn == 0:   # inference-only chip: prototypes trained offline (ideal), approx at inference
            L = H.train(Qtr, _G["ytr"], D, 16, "error", im.T, H.Similarity(), 0, s)
        else:            # learning chip: its own recipe, counters and similarity in the loop
            L = H.train(Qtr, _G["ytr"], D, w, "error" if learn == 2 else "bundle", im.T, sim, k, s)
        accs.append(float((L.predict(Qva[:, :D // 8], sim) == _G["yva"]).mean()))
        # adaptation: each validation subject streams 70% of its windows test-then-train,
        # accuracy on that subject's held-out 30% (learning-off chips stay frozen)
        Qv = _G[s][3][:, :D]
        Qvp = H.pack(Qv)
        for si, hi in _G["val_split"]:
            La = copy.deepcopy(L)
            La.sim = sim
            if learn:
                La.mode = "error" if learn == 2 else "bundle"
                for i in si:
                    La.step(Qv[i], Qvp[i], int(_G["yva"][i]))
            adapt.append(float((La.predict(Qvp[hi], sim) == _G["yva"][hi]).mean()))
    return dict(D=D, variant=v, knob=kn, learn=learn, w=w, k=k,
                acc=round(float(np.mean(adapt)), 5), acc_static=round(float(np.mean(accs)), 5),
                acc_std=round(float(np.std(adapt)), 5))


def acc_table(nproc):
    path = RES / "day4_acc_table_v2.csv"
    if path.exists():
        return {acc_key({**r, **{c: int(r[c]) for c in ("D", "knob", "learn", "w", "k")}}): r
                for r in read_csv(path)}
    keys = sorted({acc_key(p) for p in space()})
    _acc_setup()
    t0 = time.time()
    with mp.get_context("fork").Pool(nproc) as pool:
        rows = list(pool.imap_unordered(_acc_task, keys, chunksize=4))
    write_csv(path, rows)
    print(f"accuracy table: {len(rows)} configs in {time.time() - t0:.0f}s", flush=True)
    return acc_table(nproc)


# --------------------------------------------------------------------- 2. surrogate
def block_features(p, cache):
    a = AM.design_area(p["D"], p["P"], F, Q, C, p["variant"], p["knob"], bool(p["learn"]),
                       p["w"], p["k"], cache=cache)
    return np.array([a["store"], a["enc"] + a["sim"] + a.get("upd", 0) + a.get("mask", 0)]) / 1e6


def gene_features(p):
    v = [p["variant"] == n for n in ("trunc", "satcomp", "sampled")]
    return np.array([p["D"] / 1024, p["P"] / 64, p["learn"] > 0, p["learn"] == 2,
                     (p["w"] if p["learn"] else 0) / 8, p["k"] / 4, *v], dtype=float)


def flow_rows():
    rows = []
    for r in read_csv(RES / "flow_runs.csv"):
        if not r["gds"] or r["clock_ns"] != "20.0":
            continue
        p = dict(D=int(r["D"]), P=int(r["P"]), variant=r["variant"], knob=int(r["knob"]),
                 learn=int(r["learn"]), w=int(r["w"]), k=int(r["k"]))
        rows.append((p, float(r["cell_area_um2"]) / 1e6, float(r["power_total_w"]) * 1e3))
    return rows


def _fit_predict(model, Xtr, ytr, Xte):
    from sklearn.ensemble import GradientBoostingRegressor
    from sklearn.linear_model import Ridge
    if model == "ridge-blocks":
        m = Ridge(alpha=1e-3, positive=True).fit(Xtr, ytr)
    else:
        m = GradientBoostingRegressor(n_estimators=150, max_depth=2, learning_rate=0.05,
                                      subsample=0.9, random_state=0).fit(Xtr, ytr)
    return m.predict(Xte), m


def fit_surrogates(cache):
    """Leave-one-out MAPE for each candidate; returns the chosen fitted models."""
    rows = flow_rows()
    Xb = np.array([block_features(p, cache) for p, _, _ in rows])
    Xg = np.array([gene_features(p) for p, _, _ in rows])
    out, chosen = [], {}
    for target, y in (("area_mm2", np.array([a for _, a, _ in rows])),
                      ("power_mw", np.array([pw for _, _, pw in rows]))):
        best = None
        for model, X in (("ridge-blocks", Xb), ("gbm-genes", Xg)):
            pred = np.array([_fit_predict(model, np.delete(X, i, 0), np.delete(y, i), X[i:i + 1])[0][0]
                             for i in range(len(y))])
            mape = float(np.mean(np.abs(pred - y) / y) * 100)
            for (p, _, _), yt, yp in zip(rows, y, pred):
                out.append(dict(target=target, model=model, **p, real=round(yt, 5),
                                loo_pred=round(float(yp), 5), loo_mape=round(mape, 2)))
            print(f"  surrogate {target:9s} {model:12s} LOO MAPE {mape:5.1f}%  (n={len(y)})", flush=True)
            if best is None or mape < best[1]:
                best = (model, mape)
        X = Xb if best[0] == "ridge-blocks" else Xg
        chosen[target] = (best[0], _fit_predict(best[0], X, y, X[:1])[1], best[1])
    write_csv(RES / "day4_surrogate_loo.csv", out)
    return chosen


def cycles_per_inference(p):
    S = p["D"] // p["P"]
    SC = p["D"] * p["knob"] // 8 // p["P"] if p["variant"] == "sampled" else S
    return SC * (F + 1) + (S - SC) + 3          # ENC+COMMIT per compared slice, SKIP, DECIDE, FIN


# ------------------------------------------------------------------- 3. enumeration
def enumerate_space(acc, surr, cache):
    rows = []
    for p in space():
        a = acc[acc_key(p)]
        feats = {"ridge-blocks": block_features(p, cache), "gbm-genes": gene_features(p)}
        area = float(surr["area_mm2"][1].predict(feats[surr["area_mm2"][0]][None])[0])
        power = float(surr["power_mw"][1].predict(feats[surr["power_mw"][0]][None])[0])
        cyc = cycles_per_inference(p)
        rows.append(dict(**p, acc=float(a["acc"]), acc_static=float(a["acc_static"]),
                         err=1 - float(a["acc"]), area_mm2=round(area, 5),
                         power_vectorless_mw=round(power, 4), cycles=cyc,
                         latency_us=round(cyc * CLOCK_NS * 1e-3, 4)))
    F_ = np.array([[r[o] for o in OBJ] for r in rows])
    nd = nondominated(F_)
    for i, r in enumerate(rows):
        r["pareto"] = int(i in nd)
    write_csv(RES / "day4_space.csv", rows)
    return rows


def nondominated(Fm):
    from pymoo.util.nds.non_dominated_sorting import NonDominatedSorting
    return set(NonDominatedSorting().do(Fm, only_non_dominated_front=True).tolist())


# ------------------------------------------------------------- 4. optimizer comparison
class Lookup:
    """Evaluation oracle over the enumerated table; counts distinct evaluations."""

    def __init__(self, rows):
        self.idx = {(r["D"], r["P"], r["variant"], r["knob"], r["learn"], r["w"], r["k"]): r for r in rows}
        Fm = np.array([[r[o] for o in OBJ] for r in rows])
        self.lo, self.hi = Fm.min(0), Fm.max(0)
        self.seen, self.order = {}, []

    def genes_to_point(self, g):
        D = GENES["D"][int(g[0])]
        P = GENES["P"][int(g[1])]
        v, kn = GENES["sim"][int(g[2])]
        learn = int(g[3])
        w, k = (GENES["w"][int(g[4])], GENES["k"][int(g[5])]) if learn else (8, 0)
        return (D, P, v, kn, learn, w, k)

    def __call__(self, g):
        key = self.genes_to_point(g)
        if key not in self.seen:
            r = self.idx[key]
            self.seen[key] = (np.array([r[o] for o in OBJ]) - self.lo) / (self.hi - self.lo)
            self.order.append(key)
        return self.seen[key]

    def front_after(self, n):
        Fm = np.array([self.seen[k] for k in self.order[:n]])
        return Fm[list(nondominated(Fm))]


NG = [len(GENES[g]) for g in ("D", "P", "sim", "learn", "w", "k")]
REF = np.full(3, 1.1)


def hv(front):
    from pymoo.indicators.hv import HV
    return float(HV(ref_point=REF)(front)) if len(front) else 0.0


def run_random(oracle, budget, seed):
    rng = np.random.default_rng(seed)
    keys = list(oracle.idx)
    for i in rng.permutation(len(keys)):
        if len(oracle.order) >= budget:
            break
        D, P, v, kn, learn, w, k = keys[i]
        oracle([GENES["D"].index(D), GENES["P"].index(P), GENES["sim"].index((v, kn)), learn,
                GENES["w"].index(w), GENES["k"].index(k)])


def run_nsga2_simple(oracle, budget, seed):
    """NSGA-II via pymoo's ask/tell loop, stopped at `budget` distinct evaluations."""
    from pymoo.algorithms.moo.nsga2 import NSGA2
    from pymoo.core.evaluator import Evaluator
    from pymoo.core.problem import Problem
    from pymoo.operators.crossover.sbx import SBX
    from pymoo.operators.mutation.pm import PM
    from pymoo.operators.repair.rounding import RoundingRepair
    from pymoo.operators.sampling.rnd import IntegerRandomSampling

    class Prob(Problem):
        def __init__(self):
            super().__init__(n_var=6, n_obj=3, xl=np.zeros(6), xu=np.array(NG) - 1, vtype=int)

        def _evaluate(self, X, out, *a, **kw):
            out["F"] = np.array([oracle(x) for x in X])

    prob = Prob()
    algo = NSGA2(pop_size=20, sampling=IntegerRandomSampling(),
                 crossover=SBX(prob=0.9, eta=3.0, vtype=float, repair=RoundingRepair()),
                 mutation=PM(eta=3.0, vtype=float, repair=RoundingRepair()),
                 eliminate_duplicates=True)
    algo.setup(prob, seed=seed, verbose=False)
    stall = 0
    while len(oracle.order) < budget and stall < 50:
        n0 = len(oracle.order)
        pop = algo.ask()
        Evaluator().eval(prob, pop)
        algo.tell(infills=pop)
        stall = stall + 1 if len(oracle.order) == n0 else 0


def run_tpe(oracle, budget, seed):
    import optuna
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    study = optuna.create_study(directions=["minimize"] * 3,
                                sampler=optuna.samplers.TPESampler(seed=seed, n_startup_trials=20,
                                                                   multivariate=True))
    for _ in range(budget * 4):
        if len(oracle.order) >= budget:
            break
        t = study.ask()
        g = [t.suggest_int(n, 0, m - 1) for n, m in zip(("D", "P", "sim", "learn", "w", "k"), NG)]
        study.tell(t, list(oracle(g)))


OPTIMIZERS = {"random": run_random, "NSGA-II": run_nsga2_simple, "BO (Optuna TPE)": run_tpe}


def _opt_task(args):
    name, seed = args
    rows = read_csv(RES / "day4_space.csv")
    for r in rows:
        for c in ("D", "P", "knob", "learn", "w", "k"):
            r[c] = int(r[c])
        for o in OBJ:
            r[o] = float(r[o])
    oracle = Lookup(rows)
    true_hv = hv(np.array([[(r[o] - oracle.lo[i]) / (oracle.hi[i] - oracle.lo[i])
                            for i, o in enumerate(OBJ)] for r in rows if r["pareto"] == "1"]))
    OPTIMIZERS[name](oracle, max(BUDGETS), seed)
    out = []
    for b in BUDGETS:
        n = min(b, len(oracle.order))
        gap = (true_hv - hv(oracle.front_after(n))) / true_hv * 100
        out.append(dict(optimizer=name, seed=seed, budget=b, evaluated=n, hv_gap_pct=round(gap, 3)))
    return out


def compare_optimizers(nproc):
    tasks = [(n, s) for n in OPTIMIZERS for s in OPT_SEEDS]
    with mp.get_context("fork").Pool(nproc) as pool:
        rows = sum(pool.map(_opt_task, tasks), [])
    write_csv(RES / "day4_optimizers.csv", rows)


# ---------------------------------------------------------------------------- plots
def plot_all(live):
    plt = _style()
    space_rows = read_csv(RES / "day4_space.csv")
    loo = read_csv(RES / "day4_surrogate_loo.csv")
    opt = read_csv(RES / "day4_optimizers.csv")

    # --- surrogate parity (LOO)
    fig, axs = plt.subplots(1, 2, figsize=(10, 4.2))
    for ax, (target, unit) in zip(axs, (("area_mm2", "mm²"), ("power_mw", "mW"))):
        for i, model in enumerate(("ridge-blocks", "gbm-genes")):
            sel = [r for r in loo if r["target"] == target and r["model"] == model]
            x = [float(r["real"]) for r in sel]
            y = [float(r["loo_pred"]) for r in sel]
            ax.scatter(x, y, s=34, color=SERIES[i], edgecolor=SURF, linewidth=1,
                       label=f"{model} (LOO MAPE {sel[0]['loo_mape']}%)", zorder=3)
        lim = [0, max(float(r["real"]) for r in loo if r["target"] == target) * 1.1]
        ax.plot(lim, lim, color=INK2, lw=1, ls="--")
        ax.set_xlabel(f"Real LibreLane {target.split('_')[0]} ({unit}"
                      f"{', vectorless' if target == 'power_mw' else ''})")
        ax.set_ylabel(f"Leave-one-out prediction ({unit})")
        ax.set_title(f"Surrogate: {target.split('_')[0]}")
        ax.legend(fontsize=8, loc="upper left")
    _tag(fig, live)
    fig.tight_layout()
    fig.savefig(FIGS / "day4_surrogate.png")

    # --- optimizer comparison
    fig, ax = plt.subplots(figsize=(7, 4.2))
    for i, name in enumerate(OPTIMIZERS):
        m, s = [], []
        for b in BUDGETS:
            v = [float(r["hv_gap_pct"]) for r in opt if r["optimizer"] == name and int(r["budget"]) == b]
            m.append(np.mean(v)); s.append(np.std(v))
        m, s = np.array(m), np.array(s)
        ax.plot(BUDGETS, m, "-o", color=SERIES[i], label=name)
        ax.fill_between(BUDGETS, np.maximum(m - s, 0), m + s, color=SERIES[i], alpha=0.12, lw=0)
    ax.set_xlabel("Design evaluations (distinct points)")
    ax.set_ylabel("Hypervolume gap to true front (%)")
    ax.set_title(f"Search efficiency over {len(space_rows)} designs ({len(OPT_SEEDS)} seeds)")
    ax.legend(fontsize=8)
    _tag(fig, live)
    fig.tight_layout()
    fig.savefig(FIGS / "day4_optimizers.png")

    # --- Pareto front: accuracy vs area, colored by learning mode
    fig, ax = plt.subplots(figsize=(8, 4.8))
    labels = {"0": "learning off", "1": "bundle-all learning", "2": "error-driven learning"}
    for i, learn in enumerate(("0", "1", "2")):
        sel = [r for r in space_rows if r["learn"] == learn]
        ax.scatter([float(r["area_mm2"]) for r in sel], [float(r["acc"]) for r in sel], s=6,
                   color=SERIES[i], alpha=0.25, lw=0)
        par = sorted([r for r in sel if r["pareto"] == "1"], key=lambda r: float(r["area_mm2"]))
        ax.scatter([float(r["area_mm2"]) for r in par], [float(r["acc"]) for r in par], s=34,
                   color=SERIES[i], edgecolor=SURF, linewidth=1, label=f"{labels[learn]} (Pareto)", zorder=3)
    ax.set_xscale("log")
    ax.set_xlabel("Std-cell area, mm² (surrogate fitted on real sky130 runs, log)")
    ax.set_ylabel("Accuracy on new users after streaming (val. subjects)")
    ax.set_title("Design space: adapted accuracy vs. area (Pareto over error, area, latency)")
    ax.legend(fontsize=8, loc="lower right")
    _tag(fig, live)
    fig.tight_layout()
    fig.savefig(FIGS / "day4_pareto.png")
    plt.close("all")


def summarize():
    opt = read_csv(RES / "day4_optimizers.csv")
    print("\nHypervolume gap to the true front (mean ± std over seeds):")
    for name in OPTIMIZERS:
        line = []
        for b in BUDGETS:
            v = [float(r["hv_gap_pct"]) for r in opt if r["optimizer"] == name and int(r["budget"]) == b]
            line.append(f"{b}: {np.mean(v):5.1f}±{np.std(v):4.1f}")
        print(f"  {name:16s} " + "  ".join(line))
    sp = read_csv(RES / "day4_space.csv")
    par = [r for r in sp if r["pareto"] == "1"]
    print(f"\n{len(sp)} designs, {len(par)} on the 3-objective front")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--plot", action="store_true")
    a = ap.parse_args()
    nproc = int(os.environ.get("NPROC", max(1, os.cpu_count() // 2)))
    if not a.plot:
        t0 = time.time()
        acc = acc_table(nproc)
        jobs = sum((AM.design_jobs(p["D"], p["P"], F, Q, p["variant"], p["knob"], bool(p["learn"]),
                                   p["w"], p["k"]) for p in space()), [])
        cache = AM.ensure_blocks(jobs, workers=nproc)
        print(f"block synthesis cache ready ({time.time() - t0:.0f}s)", flush=True)
        surr = fit_surrogates(cache)
        enumerate_space(acc, surr, cache)
        compare_optimizers(nproc)
        print(f"done in {time.time() - t0:.0f}s", flush=True)
    plot_all(live=not a.plot)
    summarize()
