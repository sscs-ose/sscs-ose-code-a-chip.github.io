"""Is chip A really better than chip B on unseen users, or is the gap within user-to-user noise?

Uses results/final_test.csv (9 official test subjects x 5 hash seeds). The unit of replication is
the USER, so each user's score is first averaged over the 5 seeds and then compared in pairs.
Reports, for the paired differences over the 9 users:
  * the mean, a 95% bootstrap confidence interval (users resampled with replacement),
  * an exact two-sided Wilcoxon signed-rank test and a paired t-test,
  * the number of users where the first chip is better.

    python src/significance.py        # writes results/significance.json and results/per_user_final.csv
"""
import json
import pathlib

import numpy as np
import pandas as pd
from scipy import stats

ROOT = pathlib.Path(__file__).resolve().parents[1]
RES = ROOT / "results"
N_BOOT, SEED = 20000, 2027


def per_user(ft, chip, col):
    return ft[ft.chip == chip].groupby("subject")[col].mean().sort_index()


def paired(a, b, rng):
    d = (a - b).to_numpy()
    boot = np.array([rng.choice(d, len(d), replace=True).mean() for _ in range(N_BOOT)])
    w = stats.wilcoxon(d, alternative="two-sided", method="exact")
    t = stats.ttest_1samp(d, 0.0)
    return dict(mean_diff=float(d.mean()), ci95_low=float(np.percentile(boot, 2.5)), ci95_high=float(np.percentile(boot, 97.5)),
                n_users=int(len(d)), users_first_better=int((d > 0).sum()), wilcoxon_p=float(w.pvalue), ttest_p=float(t.pvalue),
                min_diff=float(d.min()), max_diff=float(d.max()))


def main():
    ft = pd.read_csv(RES / "final_test.csv")
    rng = np.random.default_rng(SEED)
    A_ad, B_ad = per_user(ft, "A", "adapted_holdout"), per_user(ft, "B", "adapted_holdout")
    A_fz, C_ad = per_user(ft, "A", "frozen_holdout"), per_user(ft, "C", "adapted_holdout")
    out = {"note": "per-user scores are averaged over 5 hash seeds first; the user is the unit of replication",
           "A_adapted_vs_B": paired(A_ad, B_ad, rng),
           "A_adapted_vs_A_frozen": paired(A_ad, A_fz, rng),
           "C_adapted_vs_B": paired(C_ad, B_ad, rng)}
    # robustness: the same comparison seed by seed (is the sign stable across random hypervector draws?)
    per_seed = []
    for sd in sorted(ft.seed.unique()):
        a = ft[(ft.chip == "A") & (ft.seed == sd)].adapted_holdout.to_numpy(); b = ft[(ft.chip == "B") & (ft.seed == sd)].adapted_holdout.to_numpy()
        per_seed.append(float((a - b).mean()))
    out["A_adapted_vs_B_by_seed_mean_diff"] = per_seed
    (RES / "significance.json").write_text(json.dumps(out, indent=2))
    table = pd.DataFrame({"B (inference-only)": B_ad, "A frozen": A_fz, "A adapted": A_ad, "A adapted - B": A_ad - B_ad, "A adapted - A frozen": A_ad - A_fz})
    table.index.name = "test subject"
    table.round(4).to_csv(RES / "per_user_final.csv")
    for k in ("A_adapted_vs_B", "A_adapted_vs_A_frozen", "C_adapted_vs_B"):
        r = out[k]
        print(f"{k:24s} mean diff {r['mean_diff']:+.3f}  95% CI [{r['ci95_low']:+.3f}, {r['ci95_high']:+.3f}]  "
              f"better in {r['users_first_better']}/{r['n_users']} users  Wilcoxon p={r['wilcoxon_p']:.3f}  t-test p={r['ttest_p']:.4f}")
    print("A - B by seed:", [round(v, 3) for v in per_seed])
    print(table.round(3).to_string())


if __name__ == "__main__":
    main()
