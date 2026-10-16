"""Day-1 experiments: accuracy vs D, vs approximation level, vs samples learned,
and the equal-area 'smaller D' baseline.

All accuracies are on the VALIDATION subjects (design exploration). The official test
subjects are untouched here and are reserved for the final Pareto points.

    python exp_day1.py            # run everything (about 5-10 min on 16 cores), then plot
    python exp_day1.py --plot     # re-plot from results/*.csv only (REPLAYED)
"""
import argparse
import csv
import multiprocessing as mp
import os
import pathlib
import time

import numpy as np

import area_model as AM
import data
import hdc_model as H

ROOT = pathlib.Path(__file__).resolve().parents[1]
RES, FIGS = ROOT / "results", ROOT / "figs"
F, Q, C = 64, 16, 6
SEEDS = range(5)
DS = [256, 512, 1024, 2048, 4096]
APPROX = ([H.Similarity("trunc", k) for k in (1, 2, 3)]
          + [H.Similarity("satcomp", k) for k in (3, 2, 1)]
          + [H.Similarity("sampled", k) for k in (6, 4, 3, 2)])
EXACT = H.Similarity()
# recipe = (label, mode, w, k)
R_IDEAL = ("error-driven, w=16", "error", 16, 0)
E1_RECIPES = [("bundle-all, w=16", "bundle", 16, 0), R_IDEAL,
              ("error-driven, w=8", "error", 8, 0), ("error-driven, w=4", "error", 4, 0),
              ("error-driven, w=4, stochastic k=3", "error", 4, 3)]
E2_RECIPE = ("error-driven, w=8", "error", 8, 0)
E3_RECIPES = [("bundle-all, w=8", "bundle", 8, 0), ("error-driven, w=8", "error", 8, 0),
              ("error-driven, w=4", "error", 4, 0), ("error-driven, w=4, k=3", "error", 4, 3),
              ("error-driven, w=3, k=3", "error", 3, 3), ("error-driven, w=2, k=4", "error", 2, 4)]
CURVE_EVERY = 250

_G = {}   # per-process globals (filled before fork)


def _setup():
    d = data.load(F, Q)
    _G["y_tr"], _G["y_va"] = d["train"][1], d["val"][1]
    for s in SEEDS:
        im = H.item_memory(F, Q, s)
        _G[s] = (im, H.encode(d["train"][0], im), H.pack(H.encode(d["val"][0], im)))


def _acc(L, s, D, sim):
    return float((L.predict(_G[s][2][:, :D // 8], sim) == _G["y_va"]).mean())


def run_task(t):
    exp, D, (label, mode, w, k), train_sim, s = t
    im, Qtr, _ = _G[s]
    rows, curve = [], []
    cb = None
    if exp == "E3":
        hits = []

        def cb(L, n, pred, y):
            hits.append(pred == y)
            if n % CURVE_EVERY == 0:
                curve.append((n, _acc(L, s, D, EXACT), float(np.mean(hits[-500:]))))
    L = H.train(Qtr, _G["y_tr"], D, w, mode, im.T, train_sim, k, s, callback=cb)
    evals = [train_sim] + (APPROX if (exp == "E1" and train_sim == EXACT) else [])
    for ev in evals:
        rows.append(dict(exp=exp, D=D, recipe=label, mode=mode, w=w, k=k,
                         train_sim=str(train_sim), eval_sim=str(ev), seed=s,
                         val_acc=round(_acc(L, s, D, ev), 5)))
    return rows, [dict(recipe=label, seed=s, n_seen=n, n_train=len(_G["y_tr"]),
                       val_acc=round(a, 5), preq_acc=round(p, 5))
                  for n, a, p in curve]


def tasks():
    for s in SEEDS:
        for D in DS:
            for r in E1_RECIPES:
                yield ("E1", D, r, EXACT, s)
        for D in (512, 1024, 2048):
            for sim in APPROX:
                yield ("E2", D, E2_RECIPE, sim, s)
        for r in E3_RECIPES:
            yield ("E3", 1024, r, EXACT, s)


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=list(rows[0]))
        wr.writeheader()
        wr.writerows(rows)


def read_csv(path):
    with path.open() as fh:
        return list(csv.DictReader(fh))


# ------------------------------------------------------------------------------ area
AREA_POINTS = []   # (P_label, D, P, learn, w, k, variant, knob)
for D in DS:
    for sim in [EXACT] + APPROX:
        AREA_POINTS.append(("P=64", D, 64, False, 8, 0, sim.variant, sim.knob))
        AREA_POINTS.append(("P=64", D, 64, True, 8, 0, sim.variant, sim.knob))
        if D <= 2048:
            AREA_POINTS.append(("P=D", D, D, False, 8, 0, sim.variant, sim.knob))
            AREA_POINTS.append(("P=D", D, D, True, 8, 0, sim.variant, sim.knob))
for P in (64, 1024):
    for w, k in ((4, 0), (4, 3)):
        AREA_POINTS.append((f"P={P}" if P == 64 else "P=D", 1024, P, True, w, k, "exact", 0))


def run_area():
    jobs = [j for (_, D, P, learn, w, k, v, kn) in AREA_POINTS
            for j in AM.design_jobs(D, P, F, Q, v, kn, learn, w, k)]
    cache = AM.ensure_blocks(jobs)
    rows = []
    for (pl, D, P, learn, w, k, v, kn) in AREA_POINTS:
        a = AM.design_area(D, P, F, Q, C, v, kn, learn, w, k, cache=cache)
        sim = str(H.Similarity(v, kn))
        rows.append(dict(arch=pl, D=D, P=P, learn=int(learn), w=w, k=k, sim=sim,
                         **{f"{b}_um2": round(a.get(b, 0.0), 1)
                            for b in ("enc", "sim", "upd", "mask", "store", "total")}))
    write_csv(RES / "day1_area.csv", rows)


# ----------------------------------------------------------------------------- plots
INK, INK2, GRID, SURF = "#1f1f1e", "#5c5b55", "#e4e3dc", "#fcfcfb"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]


def _style():
    import sys
    import matplotlib
    if "ipykernel" not in sys.modules:      # headless scripts: Agg; inside Jupyter keep the inline backend
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "figure.facecolor": SURF, "axes.facecolor": SURF, "savefig.facecolor": SURF,
        "axes.edgecolor": GRID, "axes.labelcolor": INK, "text.color": INK,
        "xtick.color": INK2, "ytick.color": INK2, "axes.grid": True, "grid.color": GRID,
        "grid.linewidth": 0.8, "axes.spines.top": False, "axes.spines.right": False,
        "lines.linewidth": 1.6, "lines.markersize": 6, "font.size": 10,
        "axes.titlesize": 11, "axes.titleweight": "bold", "legend.frameon": False,
        "figure.dpi": 130,
    })
    return plt


def _stats(rows, key, **match):
    sel = [r for r in rows if all(str(r[k]) == str(v) for k, v in match.items())]
    groups = {}
    for r in sel:
        groups.setdefault(r[key], []).append(float(r["val_acc"]))
    xs = sorted(groups, key=float)
    return (np.array([float(x) for x in xs]), np.array([np.mean(groups[x]) for x in xs]),
            np.array([np.std(groups[x]) for x in xs]))


def _tag(fig, live):
    fig.text(0.995, 0.005, "LIVE run" if live else "REPLAYED from results/*.csv",
             ha="right", va="bottom", fontsize=7, color=INK2)


def plot_all(live):
    plt = _style()
    FIGS.mkdir(parents=True, exist_ok=True)
    acc, curves = read_csv(RES / "day1_acc.csv"), read_csv(RES / "day1_curves.csv")
    area = read_csv(RES / "day1_area.csv")

    # --- Fig 1: accuracy vs D
    fig, ax = plt.subplots(figsize=(7, 4.2))
    for i, (label, *_r) in enumerate(E1_RECIPES):
        x, m, s = _stats(acc, "D", exp="E1", recipe=label, eval_sim="exact")
        ax.plot(x, m, "-o", color=SERIES[i], label=label)
        ax.fill_between(x, m - s, m + s, color=SERIES[i], alpha=0.12, lw=0)
    ax.set_xscale("log", base=2)
    ax.set_xticks(DS, [str(d) for d in DS])
    ax.set_xlabel("Hypervector dimension D")
    ax.set_ylabel("Validation accuracy")
    ax.set_title("Accuracy vs. D (exact similarity, F=64, Q=16; mean ± std over 5 seeds)")
    ax.legend(loc="lower right", fontsize=8)
    _tag(fig, live)
    fig.tight_layout()
    fig.savefig(FIGS / "day1_acc_vs_D.png")

    # --- Fig 2: accuracy vs approximation level (D=1024), in-loop vs inference-only
    fams = [("trunc", "LSBs dropped per 8-bit group count", [0, 1, 2, 3]),
            ("satcomp", "Saturating compressor output bits", [4, 3, 2, 1]),
            ("sampled", "Fraction of dimensions compared", [8, 6, 4, 3, 2])]
    fig, axs = plt.subplots(1, 3, figsize=(11, 3.8), sharey=True)
    D0 = 1024
    ex_loop = _stats(acc, "D", exp="E1", recipe=E2_RECIPE[0], eval_sim="exact")
    ref = ex_loop[1][list(ex_loop[0]).index(D0)]
    for ax, (fam, xlabel, knobs) in zip(axs, fams):
        def sim_name(kn):
            return "exact" if (fam == "trunc" and kn == 0) or (fam == "satcomp" and kn == 4) \
                or (fam == "sampled" and kn == 8) else f"{fam}({kn})"
        for j, (lab, ex, col) in enumerate([("approx. in the learning loop", "E2", SERIES[0]),
                                            ("approx. at inference only", "E1", SERIES[1])]):
            m, s = [], []
            for kn in knobs:
                nm = sim_name(kn)
                if ex == "E2" and nm != "exact":
                    sel = [float(r["val_acc"]) for r in acc if r["exp"] == "E2" and
                           int(r["D"]) == D0 and r["train_sim"] == nm]
                else:
                    sel = [float(r["val_acc"]) for r in acc if r["exp"] == "E1" and
                           int(r["D"]) == D0 and r["recipe"] == E2_RECIPE[0] and r["eval_sim"] == nm]
                m.append(np.mean(sel)); s.append(np.std(sel))
            xpos = np.arange(len(knobs))
            m, s = np.array(m), np.array(s)
            ax.plot(xpos, m, "-o", color=col, label=lab)
            ax.fill_between(xpos, m - s, m + s, color=col, alpha=0.12, lw=0)
        ax.axhline(ref, color=INK2, lw=1, ls="--")
        ax.set_xticks(np.arange(len(knobs)),
                      [f"{kn / 8:.3g}" if fam == "sampled" else str(kn) for kn in knobs])
        ax.set_xlabel(xlabel)
        ax.set_title(fam)
    axs[0].set_ylabel("Validation accuracy")
    axs[0].legend(loc="lower left", fontsize=8)
    fig.suptitle(f"Approximate similarity at D={D0} (error-driven, w=8; exact first, "
                 "more approximate to the right; dashed = exact)", fontsize=10)
    _tag(fig, live)
    fig.tight_layout()
    fig.savefig(FIGS / "day1_acc_vs_approx.png")

    # --- Fig 3: accuracy vs samples learned
    fig, axs = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
    for i, (label, *_r) in enumerate(E3_RECIPES):
        sel = [r for r in curves if r["recipe"] == label]
        ns = sorted({int(r["n_seen"]) for r in sel})
        bundle = label.startswith("bundle")   # identical to every recipe's warm-up pass
        for ax, key in zip(axs, ("val_acc", "preq_acc")):
            m = [np.mean([float(r[key]) for r in sel if int(r["n_seen"]) == n]) for n in ns]
            ax.plot(ns, m, color=SERIES[i], lw=3 if bundle else 1.6, zorder=4 if bundle else 2,
                    ls="--" if bundle else "-",
                    label=label + (" (one pass = everyone's warm-up)" if bundle else ""))
    ntr = int(curves[0]["n_train"])
    for ax, t in zip(axs, ("Held-out validation accuracy", "Test-then-train (prequential, last 500)")):
        for e in range(1, 4):
            ax.axvline(e * ntr, color=GRID, lw=1.2, ls=":")
        ax.set_xlabel("Training samples learned (stream; dotted = pass boundary)")
        ax.set_title(t)
    axs[0].set_ylabel("Accuracy")
    for ax in axs:
        ax.text(ntr * 0.5, 0.905, "bundle-all warm-up", ha="center", color=INK2, fontsize=8)
        ax.text(ntr * 2.5, 0.905, "error-driven passes", ha="center", color=INK2, fontsize=8)
        ax.set_ylim(0.38, 0.93)
    h, l = axs[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=3, fontsize=8)
    fig.suptitle("Online learning at D=1024 (mean of 5 seeds)", fontsize=10)
    _tag(fig, live)
    fig.tight_layout(rect=(0, 0.1, 1, 1))
    fig.savefig(FIGS / "day1_acc_vs_samples.png")

    # --- Fig 4: equal-area baseline
    def acc_for(D, sim, learn):
        if learn:   # chip learns with approximate similarity in the loop
            if sim == "exact":
                sel = [r for r in acc if r["exp"] == "E1" and int(r["D"]) == D and
                       r["recipe"] == E2_RECIPE[0] and r["eval_sim"] == "exact"]
            else:
                sel = [r for r in acc if r["exp"] == "E2" and int(r["D"]) == D and r["train_sim"] == sim]
        else:       # prototypes trained offline (ideal), chip only infers
            sel = [r for r in acc if r["exp"] == "E1" and int(r["D"]) == D and
                   r["recipe"] == R_IDEAL[0] and r["eval_sim"] == sim]
        return np.mean([float(r["val_acc"]) for r in sel]) if sel else None

    fig, axs = plt.subplots(2, 2, figsize=(11, 7.5))
    fam_col = {"trunc": SERIES[1], "satcomp": SERIES[2], "sampled": SERIES[3]}
    for r_i, learn in enumerate((0, 1)):
        for c_i, arch in enumerate(("P=64", "P=D")):
            ax = axs[r_i, c_i]
            pts = [a for a in area if a["arch"] == arch and int(a["learn"]) == learn
                   and int(a["w"]) == 8 and int(a["k"]) == 0]
            base = sorted((int(a["D"]), float(a["total_um2"]) / 1e6, acc_for(int(a["D"]), "exact", learn))
                          for a in pts if a["sim"] == "exact")
            base = [b for b in base if b[2] is not None]
            ax.plot([b[1] for b in base], [b[2] for b in base], "-o", color=SERIES[0],
                    label="exact popcount, D swept (baseline)")
            for b in base:
                ax.annotate(f"D={b[0]}", (b[1], b[2]), textcoords="offset points",
                            xytext=(5, -10), fontsize=7, color=INK2)
            for fam, col in fam_col.items():
                xs, ys = [], []
                for a in pts:
                    if a["sim"].startswith(fam):
                        y = acc_for(int(a["D"]), a["sim"], learn)
                        if y is not None:
                            xs.append(float(a["total_um2"]) / 1e6); ys.append(y)
                ax.scatter(xs, ys, s=28, color=col, edgecolor=SURF, linewidth=1, label=fam, zorder=3)
            ax.set_xscale("log")
            ax.set_title(f"{'learning ON (approx. in loop), w=8' if learn else 'learning OFF (offline prototypes)'}"
                         f" · {'slice-serial P=64' if arch == 'P=64' else 'fully parallel P=D'}", fontsize=9.5)
            ax.set_xlabel("Estimated cell area, mm² (pre-layout, log)")
            ax.set_ylabel("Validation accuracy")
    axs[0, 0].legend(loc="lower right", fontsize=8)
    fig.suptitle("Equal-area check: does approximate similarity beat simply using a smaller D?",
                 fontsize=11)
    _tag(fig, live)
    fig.tight_layout()
    fig.savefig(FIGS / "day1_equal_area.png")

    # --- Fig 5: area breakdown, learning off vs on
    picks = [("P=64", 0, 8, 0, "off"), ("P=64", 1, 8, 0, "on, w=8"), ("P=64", 1, 4, 3, "on, w=4 k=3"),
             ("P=D", 0, 8, 0, "off"), ("P=D", 1, 8, 0, "on, w=8"), ("P=D", 1, 4, 3, "on, w=4 k=3")]
    blocks = [("enc", "encoder + hashes"), ("sim", "similarity (6 classes)"),
              ("upd", "counter update"), ("mask", "stochastic mask"), ("store", "prototype / counter storage")]
    fig, ax = plt.subplots(figsize=(8, 4.2))
    labels, bottoms = [], None
    for i, (arch, learn, w, k, lab) in enumerate(picks):
        a = next(a for a in area if a["arch"] == arch and int(a["D"]) == 1024 and int(a["learn"]) == learn
                 and int(a["w"]) == w and int(a["k"]) == k and a["sim"] == "exact")
        labels.append(f"{'P=64' if arch == 'P=64' else 'P=1024'}\nlearning {lab}")
        b = 0.0
        for j, (blk, name) in enumerate(blocks):
            v = float(a[f"{blk}_um2"]) / 1e6
            ax.bar(i, v, bottom=b, color=SERIES[j], edgecolor=SURF, linewidth=2, width=0.6,
                   label=name if i == 0 else None)
            b += v
        ax.text(i, b, f"{b:.2f}", ha="center", va="bottom", fontsize=8, color=INK)
    ax.set_xticks(range(len(picks)), labels, fontsize=8)
    ax.set_ylabel("Estimated cell area, mm²")
    ax.set_title("What online learning costs (D=1024, 6 classes, exact similarity)")
    ax.legend(fontsize=8, loc="upper left")
    ax.grid(axis="x", visible=False)
    _tag(fig, live)
    fig.tight_layout()
    fig.savefig(FIGS / "day1_area_breakdown.png")
    plt.close("all")


def summarize():
    acc = read_csv(RES / "day1_acc.csv")
    print("\nValidation accuracy, exact similarity (mean ± std over seeds):")
    for label, *_ in E1_RECIPES:
        x, m, s = _stats(acc, "D", exp="E1", recipe=label, eval_sim="exact")
        print(f"  {label:36s}" + "  ".join(f"D={int(d)}: {a:.3f}±{e:.3f}" for d, a, e in zip(x, m, s)))
    print(f"\nApproximation at D=1024 ({E2_RECIPE[0]}): in-loop | inference-only")
    for sim in APPROX:
        il = [float(r["val_acc"]) for r in acc if r["exp"] == "E2" and r["D"] == "1024" and r["train_sim"] == str(sim)]
        io = [float(r["val_acc"]) for r in acc if r["exp"] == "E1" and r["D"] == "1024"
              and r["recipe"] == E2_RECIPE[0] and r["eval_sim"] == str(sim)]
        print(f"  {str(sim):12s} {np.mean(il):.3f} | {np.mean(io):.3f}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--plot", action="store_true", help="only re-plot from CSV")
    args = ap.parse_args()
    if not args.plot:
        t0 = time.time()
        _setup()
        acc_rows, curve_rows = [], []
        with mp.get_context("fork").Pool(max(1, os.cpu_count() - 2)) as pool:
            for r, c in pool.imap_unordered(run_task, list(tasks()), chunksize=1):
                acc_rows += r
                curve_rows += c
        write_csv(RES / "day1_acc.csv", acc_rows)
        write_csv(RES / "day1_curves.csv", curve_rows)
        print(f"accuracy runs done in {time.time() - t0:.0f}s")
        run_area()
        print(f"area synthesis done in {time.time() - t0:.0f}s")
    plot_all(live=not args.plot)
    summarize()
