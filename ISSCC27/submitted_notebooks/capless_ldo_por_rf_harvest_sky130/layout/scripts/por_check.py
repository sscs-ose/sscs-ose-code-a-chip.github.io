"""POR thresholds of ldo_top (LDO + POR + bandgap) from the extracted (or schematic) netlist: VIN ramps 0 -> 3.3 V
in 10 ms and back to 0 in 10 ms. V_on = VIN where RSTN rises, V_off = VIN where it falls.

usage: python por_check.py <view: pex|sch> [nproc]
"""
import sys
from lib import *
from postlayout import VIEWS


def por(view, corner, temp):
    net = (f"* por tb ({view})\n" + models(corner) + f".temp {temp}\n"
           ".option gmin=1e-14 reltol=1e-4 rshunt=1e13 method=gear\n"
           f".include \"{os.path.abspath(VIEWS[view])}\"\n"
           "Vin vin 0 PWL(0 0 10m 3.3 20m 0)\n"
           "Xtop vin vout rstn 0 ldo_top\nCL vout 0 100p\nCrst rstn 0 50f\n"
           ".control\ntran 1u 20m 0 5u uic\n"
           "meas tran von find v(vin) when v(rstn)=0.6 rise=1\n"
           "meas tran voff find v(vin) when v(rstn)=0.6 fall=last\n"
           ".endc\n.end\n")
    r = spice(net, f"pl_{view}_por_{corner}_{temp}", timeout=3600)
    return dict(corner=corner, T=temp, von=r.get("von"), voff=r.get("voff"))


if __name__ == "__main__":
    view = sys.argv[1]
    pts = [(c, T) for c in ("tt", "ss", "ff", "sf", "fs") for T in (-40, 27, 125)]
    def one(a):
        try:
            return por(view, *a)
        except Exception as e:
            return dict(corner=a[0], T=a[1], err=str(e)[-200:])
    df = pd.DataFrame(pmap(one, pts, workers=int(sys.argv[2]) if len(sys.argv) > 2 else None))
    df["hyst_mV"] = (df.von - df.voff) * 1e3
    df.to_csv(f"postlayout_por_{view}.csv", index=False)
    print(df.round(3).to_string(index=False))
    print(f"{view}: V_on {df.von.min():.3f}..{df.von.max():.3f} V, hysteresis >= {df.hyst_mV.min():.0f} mV")
