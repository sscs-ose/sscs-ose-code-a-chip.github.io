"""Plot baseline, predictions and native measurements from one saved result schema."""
import csv
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def plot(folder):
    folder=Path(folder);record=json.loads((folder/"results.json").read_text())
    rows=record["candidates"];metrics=list(record["project"]["metrics"])
    fig,axes=plt.subplots(1,len(metrics),squeeze=False,figsize=(5.5*len(metrics),4),layout="constrained")
    axes=axes.ravel()
    for ax,name in zip(axes,metrics):
        scale=record["project"]["metrics"][name].get("display_scale",1)
        unit=record["project"]["metrics"][name].get("display_unit","")
        ax.axhline(record["baseline"]["metrics"][name]*scale,color="black",label="Baseline")
        for field,marker,label in (("first_order_values","x","First order"),("predicted_values","o","Refined prediction"),("measured_values","s","Ngspice")):
            available=[r for r in rows if field in r]
            ax.scatter([r["geometry"]["added_area_um2"] for r in available],
                       [r[field][name]*scale for r in available],marker=marker,label=label)
        ax.set(xlabel="Added area (µm²)",ylabel=f"{name} ({unit})");ax.legend(fontsize=8)
    fig.savefig(folder/"candidate_metrics.png",dpi=180);plt.close(fig)
    fig,ax=plt.subplots(figsize=(7,4),layout="constrained")

    curves=[("Baseline",folder/"calibration/measurement/sweep/bode.csv")]
    curves += [(r["id"],folder/"candidates"/r["id"]/"AC_measurement/sweep/bode.csv")
               for r in rows if "bode_file" in r]
    for label,path in curves:
        data=np.loadtxt(path,skiprows=1)
        ax.semilogx(data[:,0],20*np.log10(np.hypot(data[:,1],data[:,2])),label=label)
    ax.set(xlabel="Frequency (Hz)",ylabel="Voltage gain (dB)");ax.legend(fontsize=8)
    fig.savefig(folder/"bode.png",dpi=180);plt.close(fig)
    with (folder/"candidates.csv").open("w") as f:
        writer=csv.writer(f)
        writer.writerow(["id","net","layer","area_um2","status","predicted_benefit","measured_benefit",
                         *[f"{field}_{name}" for field in ("first_order","predicted","measured") for name in metrics]])
        for r in rows:
            writer.writerow([r["id"],r["geometry"]["net"],r["geometry"]["layer"],r["geometry"]["added_area_um2"],
                             r["status"],r.get("predicted_benefit"),r.get("measured_benefit"),
                             *[r.get(field+"_values",{}).get(name) for field in ("first_order","predicted","measured") for name in metrics]])
