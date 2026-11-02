"""VREF vs temperature (power-up transient) for several R2, tt, VIN = 2.5 V."""
import sys
from lib import *
R1 = float(sys.argv[1]) if len(sys.argv) > 1 else 640e3
R2s = [float(x) for x in sys.argv[2:]] or [6.4e6, 7.0e6, 7.6e6, 8.2e6]
Ts = (-40, 0, 27, 60, 90, 125)
jobs = [(R2, T) for R2 in R2s for T in Ts]
def one(a):
    R2, T = a
    try:
        return (R2, T, *bgr_tran(dict(BGR0, Rb1=R1, Rb2=R2), 2.5, "tt", T).values())
    except Exception as e:
        return (R2, T, np.nan, np.nan, np.nan, np.nan)
df = pd.DataFrame(pmap(one, jobs), columns=["R2", "T", "vref", "iref", "itot", "drift"])
pd.set_option("display.width", 200)
print(df.pivot(index="R2", columns="T", values="vref").round(4))
print(df.pivot(index="R2", columns="T", values="iref").mul(1e9).round(1))
print("itot nA at 27C:", (df[df["T"] == 27].itot * 1e9).round(0).tolist(), " max |drift| mV:", round(df.drift.abs().max()*1e3, 3))
