"""Trimmed Monte Carlo: per chip, measure VREF at code 16 (27 C, 2.5 V), pick the code that lands closest to
1.200 V (step measured per chip from codes 16 and 24), then check that code at -40 / 27 / 125 C and 1.8 / 3.3 V."""
import sys
from lib import *
n = int(sys.argv[1]) if len(sys.argv) > 1 else 100
def chip(seed):
    try:
        f = lambda code, T=27, v=2.5: bgr_tran(dict(BGR0, trim=code), v, "tt", T, mc=True, seed=seed,
                                               tag_extra=f"tm{code}_{T}_{v}")["vref"]
        v16, v24 = f(16), f(24)
        step = (v24 - v16) / 8
        code = int(np.clip(round(16 + (1.2 - v16) / step), 0, 31))
        return dict(seed=seed, untrim=v16, code=code, v27=f(code), vm40=f(code, -40), v125=f(code, 125),
                    v18=f(code, 27, 1.8), v33=f(code, 27, 3.3))
    except Exception as e:
        return dict(seed=seed, err=str(e).strip().splitlines()[-1][:160])
res = pd.DataFrame(pmap(chip, list(range(1, n + 1))))
bad = res[res.v27.isna()] if "v27" in res else res
for _, r in bad.iterrows():
    print(f"seed {int(r.seed)}: no result ({r.get('err', '')})")
df = res.dropna(subset=["v27", "vm40", "v125", "v18", "v33"]).drop(columns=["err"], errors="ignore")
df.to_csv("bgr_trim_mc.csv", index=False)
allv = df[["v27", "vm40", "v125", "v18", "v33"]].values.ravel()
print(f"chips {len(df)}/{n}; untrimmed sigma {df.untrim.std()/1.2*100:.2f} %; codes used {df.code.min()}..{df.code.max()}")
print(f"trimmed @27C: mean {df.v27.mean():.4f} sigma {df.v27.std()*1e3:.2f} mV; all T/V: {allv.min():.4f} .. {allv.max():.4f} V "
      f"(error {100*(allv.min()-1.2)/1.2:+.2f} % .. {100*(allv.max()-1.2)/1.2:+.2f} %)")
