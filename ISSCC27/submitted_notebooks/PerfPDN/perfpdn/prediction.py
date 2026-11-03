"""Refine a candidate with its actual mesh and a common terminal circuit."""
import json
import numpy as np
from scipy.optimize import brentq
from .system import reduce_network
from .devices import device_matrices
from .native import read_scalar_raw


def predict(project,base,folder,network,system):
    folder.mkdir(parents=True,exist_ok=True)
    state=system["state"];ports=[p for p,t in state["ports"]];count=len(ports)
    reduced=reduce_network(network,state,project)
    S=reduced["S"];raw=read_scalar_raw(base/"op.raw")
    v0=np.array([state["node_voltages_V"][n] for n in reduced["names"]])
    i0=np.zeros(len(v0));i0[:count]=[raw[f"i(v_{p})"] for p in ports]
    Ydc=np.zeros_like(S);Ydc[:count,:count]=system["Ydc"]

    delta=np.linalg.solve(S+Ydc,reduced["dc_rhs"]-S@v0-i0)
    predicted=v0+delta
    gain_frequencies=[s["frequency_Hz"] for s in project["metrics"].values() if s["measurement"]=="gain_dB"]
    unity_names=[n for n,s in project["metrics"].items() if s["measurement"]=="unity_Hz"]
    low=min([project["frequency_range_Hz"][0],*gain_frequencies])
    anchor=system["baseline"]["metrics"][unity_names[0]] if unity_names else None
    queries=0;cache={};checks=None

    def query(frequencies):
        nonlocal queries,checks
        Y,_,checks=device_matrices(base,folder/f"device_query_{queries}",frequencies,
                                   step=None,dc_override=predicted[:count])
        queries+=1
        cache.update(zip(frequencies,Y))

    def transfer(f,y):
        A=S.astype(complex)+2j*np.pi*f*reduced["C"]
        A[:count,:count]+=y
        return reduced["c"]@np.linalg.solve(A,reduced["ac_rhs"])

    query(list(dict.fromkeys(gain_frequencies+([low,anchor] if unity_names else []))))
    crossing_error=None;unity=None;refreshes=0

    if unity_names:
        if anchor<=low:
            raise ValueError("The unity crossing must be above the lowest characterization frequency.")
        for iteration in range(3):
            def interpolated(f):
                y=cache[low]+(cache[anchor]-cache[low])*(f-low)/(anchor-low)
                return transfer(f,y)
            frequencies=np.geomspace(*project["frequency_range_Hz"],160)
            amplitude=np.log([abs(interpolated(f)) for f in frequencies])
            crossings=np.flatnonzero((amplitude[:-1]>=0)&(amplitude[1:]<0))
            if not len(crossings):
                raise ValueError("Predicted circuit has no descending unity crossing in the frequency range.")
            k=crossings[0]
            unity=float(np.exp(brentq(lambda logf:np.log(abs(interpolated(np.exp(logf)))),
                                     np.log(frequencies[k]),np.log(frequencies[k+1]),xtol=1e-11)))
            query([unity]);refreshes+=1
            crossing_error=float(abs(np.log(abs(transfer(unity,cache[unity])))))
            if crossing_error<1e-5:break
            anchor=unity
    currents=np.array(checks["dc_currents_A"]+[0.]*(len(v0)-count))
    residual=S@predicted+currents-reduced["dc_rhs"]
    relative=float(max(abs(residual))/max(max(abs(i0)),1e-12))
    values={name:float(20*np.log10(abs(transfer(spec["frequency_Hz"],cache[spec["frequency_Hz"]]))))
            if spec["measurement"]=="gain_dB" else unity for name,spec in project["metrics"].items()}
    issues=[]
    if relative>project.get("bias_residual_relative_limit",.05):
        issues.append("predicted bias current imbalance")
    if crossing_error is not None and crossing_error>=1e-5:
        issues.append("frequency response requires further native verification")
    record={"values":values,"predicted_terminal_voltages_V":dict(zip(ports,predicted[:count].tolist())),
            "current_residual_A":float(max(abs(residual))),"current_residual_relative":relative,
            "crossing_log_amplitude_error":crossing_error,"frequency_refreshes":refreshes,
            "device_queries":queries,"usable":not issues,"issues":issues,"retained_nodes":len(v0),
            "method":"candidate remesh; terminal reduction; one bias solve; native device refresh; AC solution"}
    (folder/"prediction.json").write_text(json.dumps(record,indent=2)+"\n")
    return record
