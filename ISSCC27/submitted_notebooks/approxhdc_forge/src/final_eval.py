"""Final numbers on the 9 official TEST subjects for the three chips that went through the flow.

These subjects were never used for any design decision (accuracy objectives in the search used
validation subjects only). Protocol per subject (same as the search): each activity's windows
split in time, first 70% = stream (test-then-train), last 30% held out, 2-window gap.

    python final_eval.py          # run (about 1-2 min), writes results/final_test*.csv, figs/final_test.png
    python final_eval.py --plot   # re-plot from CSV (REPLAYED)
"""
import argparse
import copy
import time

import numpy as np

import data
import hdc_model as H
from exp_day1 import FIGS, INK2, RES, SERIES, SURF, _style, _tag, read_csv, write_csv
from exp_day4_model import split_subject

F, Q, C = 64, 16, 6
SEEDS = range(5)          # item-memory seeds; the fabricated chips use seed 0
SIM = H.Similarity("satcomp", 2)
# name -> (D, learn, w, k): exactly the configurations run through the physical flow
CHIPS = {"A  D=512, bundle-all learning, w=2": (512, 1, 2, 0),
         "B  D=1024, inference-only": (1024, 0, 8, 0),
         "C  D=256, bundle-all learning, w=2": (256, 1, 2, 0)}
SHORT = {k: k[0] for k in CHIPS}


def run(live=True):
    d = data.load(F, Q)
    Xte, yte, ste = d["test"]
    ytr = d["train"][1]
    subjects = sorted(set(ste.tolist()))
    split = {s: tuple(np.flatnonzero(ste == s)[i] for i in split_subject(yte[ste == s])) for s in subjects}
    rows = []
    t0 = time.time()
    for seed in SEEDS:
        im = H.item_memory(F, Q, seed)
        Qtr, Qte = H.encode(d["train"][0], im), H.encode(Xte, im)
        for name, (D, learn, w, k) in CHIPS.items():
            if learn:   # chip trains with its own counters and approximate similarity in the loop
                L0 = H.train(Qtr, ytr, D, w, "bundle", im.T, SIM, k, seed)
            else:       # inference-only chip: ideal offline prototypes, approximate similarity at inference
                L0 = H.train(Qtr, ytr, D, 16, "error", im.T, H.Similarity(), 0, seed)
            L0.sim = SIM
            Qd = np.ascontiguousarray(Qte[:, :D])
            Qp = H.pack(Qd)
            for s in subjects:
                si, hi = split[s]
                ids = np.flatnonzero(ste == s)
                L = copy.deepcopy(L0)
                frozen_hold = float((L.predict(Qp[hi], SIM) == yte[hi]).mean())
                frozen_all = float((L.predict(Qp[ids], SIM) == yte[ids]).mean())
                hits = 0
                if learn:
                    L.mode = "bundle"
                    for i in si:
                        hits += L.step(Qd[i], Qp[i], int(yte[i])) == yte[i]
                    preq = hits / len(si)
                else:
                    preq = float((L.predict(Qp[si], SIM) == yte[si]).mean())
                adapted = float((L.predict(Qp[hi], SIM) == yte[hi]).mean())
                rows.append(dict(chip=name[0], seed=seed, subject=s, frozen_holdout=round(frozen_hold, 5),
                                 frozen_all=round(frozen_all, 5), adapted_holdout=round(adapted, 5),
                                 prequential=round(preq, 5), stream_len=len(si), holdout_len=len(hi)))
        print(f"seed {seed} done ({time.time() - t0:.0f}s)", flush=True)
    write_csv(RES / "final_test.csv", rows)

    # software reference on the same 64 quantized features (no hardware constraints)
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    sc = StandardScaler().fit(d["train"][0])
    lr = LogisticRegression(max_iter=2000).fit(sc.transform(d["train"][0]), ytr)
    pred = lr.predict(sc.transform(Xte))
    ref = [dict(model="logistic regression, 64 features (software)",
                test_all=round(float((pred == yte).mean()), 5),
                test_holdout=round(float(np.mean([(pred[split[s][1]] == yte[split[s][1]]).mean()
                                                  for s in subjects])), 5))]
    write_csv(RES / "final_test_reference.csv", ref)


def table():
    rows, ref = read_csv(RES / "final_test.csv"), read_csv(RES / "final_test_reference.csv")
    print("\nFINAL, 9 official test subjects (mean over subjects; ± std over 5 item-memory seeds; seed 0 in brackets)")
    print(f"{'chip':38s} {'static, all windows':>20s} {'held-out, frozen':>18s} {'held-out, adapted':>19s} {'prequential':>14s}")
    for name in CHIPS:
        c = name[0]
        vals = {}
        for key in ("frozen_all", "frozen_holdout", "adapted_holdout", "prequential"):
            per_seed = [np.mean([float(r[key]) for r in rows if r["chip"] == c and r["seed"] == str(s)]) for s in SEEDS]
            vals[key] = (np.mean(per_seed), np.std(per_seed), per_seed[0])
        f = lambda t: f"{t[0]:.3f}±{t[1]:.3f} [{t[2]:.3f}]"
        print(f"{name:38s} {f(vals['frozen_all']):>20s} {f(vals['frozen_holdout']):>18s} {f(vals['adapted_holdout']):>19s} {f(vals['prequential']):>14s}")
    print(f"\nsoftware reference ({ref[0]['model']}): all windows {float(ref[0]['test_all']):.3f}, held-out 30% {float(ref[0]['test_holdout']):.3f}")


def plot(live):
    plt = _style()
    rows = read_csv(RES / "final_test.csv")
    subjects = sorted({int(r["subject"]) for r in rows})
    fig, ax = plt.subplots(figsize=(8.4, 4.4))
    x = np.arange(len(CHIPS))
    for j, (key, lab, col) in enumerate((("frozen_holdout", "frozen (offline prototypes only)", SERIES[1]),
                                         ("adapted_holdout", "after streaming the user (learning ON)", SERIES[0]))):
        means, stds = [], []
        for name in CHIPS:
            ps = [np.mean([float(r[key]) for r in rows if r["chip"] == name[0] and r["seed"] == str(s)]) for s in SEEDS]
            means.append(np.mean(ps)); stds.append(np.std(ps))
        pos = x + (j - 0.5) * 0.36
        ax.bar(pos, means, width=0.34, color=col, edgecolor=SURF, linewidth=2, label=lab,
               yerr=stds, error_kw=dict(ecolor=INK2, lw=1, capsize=3))
        for xi, m in zip(pos, means):
            ax.text(xi, 0.325, f"{m:.2f}", ha="center", fontsize=10, fontweight="bold", color=SURF)
        # one dot per test subject (mean over seeds)
        for ci, name in enumerate(CHIPS):
            v = [np.mean([float(r[key]) for r in rows if r["chip"] == name[0] and r["subject"] == str(s)]) for s in subjects]
            ax.scatter(np.full(len(v), pos[ci]) + np.linspace(-0.06, 0.06, len(v)), v, s=9, color=INK2, alpha=0.55, zorder=3, lw=0)
    ax.set_xticks(x, [n.replace("  ", "\n") for n in CHIPS], fontsize=8.5)
    ax.set_ylabel("Accuracy on the user's held-out windows")
    ax.set_ylim(0.3, 1.0)
    ax.set_title("Final result on 9 unseen test subjects (bars: mean of 5 seeds; dots: individual subjects)", fontsize=10)
    ax.legend(loc="upper left", fontsize=8.5)
    ax.grid(axis="x", visible=False)
    _tag(fig, live)
    fig.tight_layout()
    fig.savefig(FIGS / "final_test.png")
    plt.close("all")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--plot", action="store_true")
    a = ap.parse_args()
    if not a.plot:
        run()
    plot(live=not a.plot)
    table()
