"""Post-layout Monte Carlo of ldo_top (LDO + POR + bandgap, extracted netlist): local mismatch on every device,
process corner + mismatch, power-up transient then the 0 -> 1 -> 0 mA load step.
usage: python pl_mc.py <view> [n] [temp] [vin] [corner]"""
import sys
import postlayout as pl
from lib import *
view = sys.argv[1]
n = int(sys.argv[2]) if len(sys.argv) > 2 else 100
T = float(sys.argv[3]) if len(sys.argv) > 3 else 27
v = float(sys.argv[4]) if len(sys.argv) > 4 else 2.5
C = sys.argv[5] if len(sys.argv) > 5 else "tt"
def one(seed):
    try: return dict(seed=seed, **pl.load_step(view, C, T, v, seed=seed))
    except Exception: return dict(seed=seed)
df = pd.DataFrame(pmap(one, list(range(1, n + 1))))
df.to_csv(f"postlayout_mc_{view}_{T:g}_{v:g}" + ("" if C == "tt" else f"_{C}") + ".csv", index=False)
ok = df.dropna(subset=["vout"])
print(f"{view} MC {C} {T:g} C {v:g} V: n={len(ok)}/{n}  VOUT mean {ok.vout.mean():.4f} V, sigma {ok.vout.std()*1e3:.2f} mV "
      f"({ok.vout.std()/1.2*100:.2f} %), min {ok.vout.min():.4f} max {ok.vout.max():.4f}; undershoot max {ok.under.max():.0f} mV, "
      f"overshoot max {ok.over.max():.0f} mV; Iq mean {ok.iq.mean():.2f} max {ok.iq.max():.2f} uA; RST_N high {int((ok.rstn > 0.6).sum())}/{len(ok)}")
