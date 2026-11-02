"""VREF / Iref / supply current of the bandgap over 5 corners x 3 temperatures x 3 supplies (power-up transient)."""
from lib import *
jobs = [(c, T, v) for c in ("tt", "ss", "ff", "sf", "fs") for T in (-40, 27, 125) for v in (1.8, 2.5, 3.3)]
def one(a):
    c, T, v = a
    try:
        return (c, T, v, *bgr_tran(dict(BGR0), v, c, T).values())
    except Exception:
        return (c, T, v, np.nan, np.nan, np.nan, np.nan)
df = pd.DataFrame(pmap(one, jobs), columns=["corner", "T", "vin", "vref", "iref", "itot", "drift"])
df.to_csv("bgr_pvt.csv", index=False)
pd.set_option("display.width", 200)
print(df.pivot_table(index=["corner", "vin"], columns="T", values="vref").round(4))
print("VREF: %.4f .. %.4f V (%.2f %% of 1.2 V)" % (df.vref.min(), df.vref.max(), 100 * (df.vref.max() - df.vref.min()) / 2 / 1.2))
print("Iref: %.0f .. %.0f nA ; Itot: %.0f .. %.0f nA" % (df.iref.min()*1e9, df.iref.max()*1e9, df.itot.min()*1e9, df.itot.max()*1e9))
