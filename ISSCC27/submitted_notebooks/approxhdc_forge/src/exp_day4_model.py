"""Day-4 model experiments: user adaptation, approximation + learning recovery, bit flips.

Deployment story: prototypes are trained offline on the training subjects (software, exact
similarity, the chip's counter width), loaded into the chip, and the chip then meets a NEW
user (one of the 9 official test subjects) and keeps learning while it classifies.

Per test subject, each activity's windows are split in time order: the first 70% form the
stream (test-then-train, in recording order), the last 30% are held out and never learned.
A 2-window gap separates them because UCI-HAR windows overlap by 50%.

    python exp_day4_model.py          # run (a few minutes on 16 cores), then plot
    python exp_day4_model.py --plot   # re-plot from results/day4_*.csv (REPLAYED)
"""
import argparse
import copy
import multiprocessing as mp
import os
import time

import numpy as np

import data
import hdc_model as H
from exp_day1 import FIGS, INK2, RES, SERIES, SURF, _style, _tag, read_csv, write_csv

F, Q, C, D0 = 64, 16, 6, 1024
SEEDS = range(5)
DESIGNS = {"w=8": (8, 0), "w=4, k=3": (4, 3)}          # counter width, stochastic exponent
SIMS = [H.Similarity(), H.Similarity("trunc", 1), H.Similarity("satcomp", 2),
        H.Similarity("sampled", 4)]
FLIP_RATES = [0.0, 0.01, 0.02, 0.05, 0.1, 0.2, 0.3]
FLIP_DS = [256, 512, 1024, 2048]
EVAL_FRACS = np.linspace(0, 1, 11)    # held-out accuracy after 0%, 10%, ..., 100% of the stream
STREAM_FRAC, GAP = 0.7, 2

_G = {}


def split_subject(y):
    """Indices (in recording order) of the stream and held-out parts of one subject."""
    stream, hold = [], []
    for c in np.unique(y):
        idx = np.flatnonzero(y == c)
        cut = int(len(idx) * STREAM_FRAC)
        stream += idx[:cut].tolist()
        hold += idx[cut + GAP:].tolist()
    return np.sort(stream), np.sort(hold)


def _setup():
    d = data.load(F, Q)
    Xte, yte, ste = d["test"]
    _G["ytr"], _G["yte"] = d["train"][1], yte
    _G["subjects"] = sorted(set(ste.tolist()))
    _G["split"] = {s: tuple(np.flatnonzero(ste == s)[i] for i in split_subject(yte[ste == s]))
                   for s in _G["subjects"]}
    for seed in SEEDS:
        im = H.item_memory(F, Q, seed)
        Qtr = H.encode(d["train"][0], im)
        Qte = H.encode(Xte, im)
        offline = {}
        for name, (w, k) in DESIGNS.items():
            offline[name] = H.train(Qtr, _G["ytr"], D0, w, "error", im.T, H.Similarity(), k, seed)
        ideal = {D: H.train(Qtr, _G["ytr"], D, 16, "error", im.T, H.Similarity(), 0, seed)
                 for D in FLIP_DS}
        _G[seed] = dict(im=im, Qte=Qte, offline=offline, ideal=ideal)


def _holdout_acc(L, Qp, y, sim):
    return float((L.predict(Qp, sim) == y).mean())


def _stream(L, seed, subject, D, learn, eval_curve=True):
    """Test-then-train over one subject's stream; returns [(fraction_seen, holdout_acc)], preq acc."""
    g, (si, hi) = _G[seed], _G["split"][subject]
    Qd = g["Qte"][:, :D]
    Qp = H.pack(Qd)
    yte = _G["yte"]
    curve, hits = [(0.0, _holdout_acc(L, Qp[hi], yte[hi], L.sim))], 0
    marks = {int(round(f * len(si))): f for f in EVAL_FRACS[1:]}
    L.mode = "error"
    for n, i in enumerate(si, 1):
        if learn:
            pred = L.step(Qd[i], Qp[i], int(yte[i]))
        else:
            pred = int(L.predict(Qp[i]))
        hits += pred == yte[i]
        if eval_curve and n in marks:
            curve.append((marks[n], _holdout_acc(L, Qp[hi], yte[hi], L.sim)))
    if not eval_curve:
        curve.append((1.0, _holdout_acc(L, Qp[hi], yte[hi], L.sim)))
    return curve, hits / len(si)


def task_adapt(t):
    seed, design, sim, subject, learn = t
    L = copy.deepcopy(_G[seed]["offline"][design])
    L.sim = sim
    curve, preq = _stream(L, seed, subject, D0, learn)
    return [dict(exp="adapt", seed=seed, design=design, sim=str(sim), subject=subject,
                 learn=int(learn), frac_seen=round(f, 2), stream_len=len(_G["split"][subject][0]),
                 holdout_acc=round(a, 5), preq_acc=round(preq, 5))
            for f, a in curve]


def _flip_counters(cnt, w, rate, rng):
    u = (cnt.astype(np.int32) & ((1 << w) - 1))
    for b in range(w):
        u ^= (rng.random(cnt.shape) < rate).astype(np.int32) << b
    return np.where(u >= 1 << (w - 1), u - (1 << w), u).astype(np.int16)


def _set_counters(L, cnt):
    L.cnt[:] = cnt
    for c in range(L.C):
        p = (L.cnt[c] > 0) | ((L.cnt[c] == 0) & L.T)
        L.proto[c] = p
        L.protop[c] = H.pack(p.astype(np.uint8))


def task_flip(t):
    kind, seed, D, rate = t
    rng = np.random.default_rng(10_000 + seed * 100 + int(rate * 1000))
    g, yte = _G[seed], _G["yte"]
    rows = []
    if kind == "proto":      # inference-only chip: stored prototype bits flip
        L = copy.deepcopy(g["ideal"][D])
        flips = (rng.random(L.proto.shape) < rate).astype(np.uint8)
        L.protop[:] = H.pack(L.proto ^ flips)
        acc = _holdout_acc(L, H.pack(g["Qte"][:, :D]), yte, L.sim)
        rows.append(dict(exp="flip_proto", seed=seed, D=D, design="offline w=16", rate=rate,
                         learn=0, acc=round(acc, 5)))
    else:                    # learning chip: stored counter bits flip, then the user streams
        for design, (w, k) in DESIGNS.items():
            base = g["offline"][design]
            flipped = _flip_counters(base.cnt, w, rate, rng)
            for learn in (0, 1):
                accs = []
                for s in _G["subjects"]:
                    L = copy.deepcopy(base)
                    _set_counters(L, flipped)
                    curve, _ = _stream(L, seed, s, D0, learn, eval_curve=False)
                    accs.append(curve[-1][1])
                rows.append(dict(exp="flip_counter", seed=seed, D=D0, design=design, rate=rate,
                                 learn=learn, acc=round(float(np.mean(accs)), 5)))
    return rows


def tasks():
    for seed in SEEDS:
        for design in DESIGNS:
            for sim in SIMS:
                for s in _G["subjects"]:
                    for learn in (0, 1):
                        yield task_adapt, (seed, design, sim, s, learn)
        for rate in FLIP_RATES:
            for D in FLIP_DS:
                yield task_flip, ("proto", seed, D, rate)
            yield task_flip, ("counter", seed, D0, rate)


def _call(ft):
    f, t = ft
    return f.__name__, f(t)


# ----------------------------------------------------------------------------- plots
def plot_all(live):
    plt = _style()
    adapt = read_csv(RES / "day4_adapt.csv")
    flips = read_csv(RES / "day4_flips.csv")

    def curve(design, sim, learn):
        sel = [r for r in adapt if r["design"] == design and r["sim"] == sim and r["learn"] == str(learn)]
        pts = []
        for f in sorted({float(r["frac_seen"]) for r in sel}):
            at = [r for r in sel if float(r["frac_seen"]) == f]
            per_seed = [np.mean([float(r["holdout_acc"]) for r in at if r["seed"] == str(s)]) for s in SEEDS]
            pts.append((f * 100, np.mean([float(r["holdout_acc"]) for r in at]), np.std(per_seed)))
        return np.array(pts)

    # --- Fig A: user adaptation (exact similarity)
    fig, axs = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
    for ax, design in zip(axs, DESIGNS):
        for learn, col, lab in ((1, SERIES[0], "learning ON (error-driven, test-then-train)"),
                                (0, SERIES[1], "learning OFF (frozen offline prototypes)")):
            c = curve(design, "exact", learn)
            ax.plot(c[:, 0], c[:, 1], color=col, label=lab)
            ax.fill_between(c[:, 0], c[:, 1] - c[:, 2], c[:, 1] + c[:, 2], color=col, alpha=0.12, lw=0)
        ax.set_title(f"D={D0}, counters {design}")
        ax.set_xlabel("Share of the new user's stream seen (%)")
    axs[0].set_ylabel("Accuracy on the user's held-out windows")
    axs[0].legend(loc="lower right", fontsize=8)
    fig.suptitle("Adapting to an unseen user on chip (mean over 9 test subjects × 5 seeds; band = seed std)",
                 fontsize=10)
    _tag(fig, live)
    fig.tight_layout()
    fig.savefig(FIGS / "day4_user_adaptation.png")

    # --- Fig B: approximation + learning recovery
    fig, axs = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
    sims = [str(s) for s in SIMS]
    for ax, design in zip(axs, DESIGNS):
        x = np.arange(len(sims))
        for j, (learn, col, lab) in enumerate(((0, SERIES[1], "before: frozen offline prototypes"),
                                               (1, SERIES[0], "after streaming with learning ON"))):
            m = []
            for sim in sims:
                c = curve(design, sim, learn)
                m.append(c[-1, 1] if learn else c[0, 1])
            ax.bar(x + (j - 0.5) * 0.36, m, width=0.34, color=col, edgecolor=SURF, linewidth=2, label=lab)
            for xi, v in zip(x, m):
                ax.text(xi + (j - 0.5) * 0.36, v + 0.005, f"{v:.2f}", ha="center", fontsize=7.5)
        ax.set_xticks(x, sims)
        ax.set_title(f"D={D0}, counters {design}")
        ax.set_ylim(0.3, 0.95)
        ax.grid(axis="x", visible=False)
    axs[0].set_ylabel("Held-out accuracy (new users)")
    axs[0].legend(loc="upper right", fontsize=8)
    fig.suptitle("Prototypes trained with exact similarity, deployed on an approximate similarity unit: "
                 "does on-chip learning recover?", fontsize=10)
    _tag(fig, live)
    fig.tight_layout()
    fig.savefig(FIGS / "day4_approx_recovery.png")

    # --- Fig C: bit flips
    fig, axs = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
    ax = axs[0]
    for i, D in enumerate(FLIP_DS):
        sel = [r for r in flips if r["exp"] == "flip_proto" and int(r["D"]) == D]
        xs = sorted({float(r["rate"]) for r in sel})
        m = [np.mean([float(r["acc"]) for r in sel if float(r["rate"]) == x]) for x in xs]
        ax.plot(xs, m, "-o", color=SERIES[i], label=f"D={D}")
    ax.set_title("Inference-only chip: prototype bit flips")
    ax.set_xlabel("Fraction of stored bits flipped")
    ax.set_ylabel("Test accuracy (all 9 test subjects)")
    ax.legend(fontsize=8, loc="lower left")
    ax = axs[1]
    for i, design in enumerate(DESIGNS):
        for learn, ls in ((0, "--"), (1, "-")):
            sel = [r for r in flips if r["exp"] == "flip_counter" and r["design"] == design
                   and r["learn"] == str(learn)]
            xs = sorted({float(r["rate"]) for r in sel})
            m = [np.mean([float(r["acc"]) for r in sel if float(r["rate"]) == x]) for x in xs]
            ax.plot(xs, m, ls, marker="o", color=SERIES[i],
                    label=f"{design}, {'after streaming, learning ON' if learn else 'frozen'}")
    ax.set_title(f"Learning chip (D={D0}): counter bit flips")
    ax.set_xlabel("Fraction of stored counter bits flipped")
    ax.legend(fontsize=8, loc="lower left")
    fig.suptitle("Bit-flip robustness (mean of 5 seeds)", fontsize=10)
    _tag(fig, live)
    fig.tight_layout()
    fig.savefig(FIGS / "day4_bitflips.png")
    plt.close("all")


def summarize():
    adapt = read_csv(RES / "day4_adapt.csv")
    print(f"\nUser adaptation at D={D0}: held-out accuracy before -> after streaming (mean over subjects, seeds)")
    for design in DESIGNS:
        for sim in [str(s) for s in SIMS]:
            out = []
            for learn in (0, 1):
                sel = [r for r in adapt if r["design"] == design and r["sim"] == sim and r["learn"] == str(learn)]
                first = [float(r["holdout_acc"]) for r in sel if float(r["frac_seen"]) == 0]
                last = [float(r["holdout_acc"]) for r in sel if float(r["frac_seen"]) == 1]
                out.append((np.mean(first), np.mean(last)))
            print(f"  {design:9s} {sim:12s} frozen {out[0][1]:.3f} | learning: {out[1][0]:.3f} -> {out[1][1]:.3f}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--plot", action="store_true")
    a = ap.parse_args()
    if not a.plot:
        t0 = time.time()
        _setup()
        print(f"setup {time.time() - t0:.0f}s", flush=True)
        adapt, flips = [], []
        with mp.get_context("fork").Pool(max(1, int(os.environ.get("NPROC", os.cpu_count() // 2)))) as pool:
            for name, rows in pool.imap_unordered(_call, list(tasks()), chunksize=2):
                (adapt if name == "task_adapt" else flips).extend(rows)
        write_csv(RES / "day4_adapt.csv", adapt)
        write_csv(RES / "day4_flips.csv", flips)
        print(f"done in {time.time() - t0:.0f}s", flush=True)
    plot_all(live=not a.plot)
    summarize()
