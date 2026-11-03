"""Bandgap Monte Carlo (local mismatch, tt, 27 C, VIN = 2.5 V), 200 seeds."""
import sys
from lib import *
n = int(sys.argv[1]) if len(sys.argv) > 1 else 200
def one(seed):
    try: return bgr_tran(dict(BGR0), 2.5, "tt", 27, mc=True, seed=seed)["vref"]
    except Exception: return np.nan
v = np.array(pmap(one, list(range(1, n + 1))))
np.savetxt("bgr_mc.txt", v)
ok = v[~np.isnan(v)]
print(f"MC n={len(ok)}/{n}: mean {ok.mean():.4f} V, sigma {ok.std()*1e3:.2f} mV ({100*ok.std()/ok.mean():.2f} %), "
      f"min {ok.min():.4f}, max {ok.max():.4f}, 3sigma +-{300*ok.std()/ok.mean():.2f} %")
