"""Measure configured voltage-transfer metrics with native ngspice."""
import json
import numpy as np
from .native import spice, complex_raw


def voltage_expression(nodes):
    a,b=nodes
    return ("0" if a=="0" else f"v({a})")+"-"+("0" if b=="0" else f"v({b})")


def transfer_expression(project):
    return f'({voltage_expression(project["transfer"]["output"])})/({voltage_expression(project["transfer"]["input"])})'


def response(project, point):
    v=lambda n:0j if n=="0" else point[f"v({n})"]
    a,b=project["transfer"]["output"];c,d=project["transfer"]["input"]
    return (v(a)-v(b))/(v(c)-v(d))


def points(base,folder,frequencies):
    lines=(base/"base.cir").read_text().splitlines()

    spice(["PerfPDN AC points",*lines,".save all",".control","set filetype=ascii",
           *[s for k,f in enumerate(frequencies) for s in (f"ac lin 1 {f:.17g} {f:.17g}",f"write ac_{k}.raw all")],
           "quit",".endc",".end"],folder)
    return [complex_raw(folder/f"ac_{k}.raw") for k in range(len(frequencies))]


def measure(project,base,folder):
    folder.mkdir(parents=True,exist_ok=True)
    lines=(base/"base.cir").read_text().splitlines()
    start,stop=project["frequency_range_Hz"]
    save=" ".join(f"v({n})" for n in set(sum(project["transfer"].values(),[])) if n!="0")
    spice(["PerfPDN frequency sweep",*lines,f".save {save}",".control","set wr_singlescale",
           "set wr_vecnames",f"ac dec 50 {start} {stop}",f"let h={transfer_expression(project)}",
           "let hr=real(h)","let hi=imag(h)","wrdata bode.csv hr hi","quit",".endc",".end"],folder/"sweep")
    curve=np.loadtxt(folder/"sweep/bode.csv",skiprows=1)
    amplitude=np.log(np.abs(curve[:,1]+1j*curve[:,2]))
    slope=None;root=None
    if any(s["measurement"]=="unity_Hz" for s in project["metrics"].values()):
        crossing=np.flatnonzero((amplitude[:-1]>=0)&(amplitude[1:]<0))
        if not len(crossing):
            raise ValueError("No descending unity crossing in the configured frequency range.")
        k=crossing[0];root=np.exp(np.interp(0,amplitude[k:k+2][::-1],np.log(curve[k:k+2,0])[::-1]))

        for iteration in range(4):
            fs=[root*np.exp(-.001),root,root*np.exp(.001)]
            data=points(base,folder/f"crossing_{iteration}",fs)
            values=np.log([abs(response(project,p)) for p in data])
            slope=(values[2]-values[0])/.002
            if slope>=-.01:
                raise ValueError("The selected unity crossing is too flat for reliable sensitivity.")
            root*=np.exp(-values[1]/slope)
            if abs(values[1])<1e-7:
                break
        else:
            raise ValueError("Unity crossing did not resolve within four native refinements.")
    metrics={};frequencies={}
    for name,spec in project["metrics"].items():
        frequencies[name]=spec["frequency_Hz"] if spec["measurement"]=="gain_dB" else root
    unique=list(dict.fromkeys(frequencies.values()))
    native=points(base,folder/"metric_points",unique)
    by_frequency=dict(zip(unique,native))
    for name,spec in project["metrics"].items():
        metrics[name]=float(20*np.log10(abs(response(project,by_frequency[frequencies[name]])))) if spec["measurement"]=="gain_dB" else float(root)
    record={"metrics":metrics,"frequencies":frequencies,"crossing_log_slope":None if slope is None else float(slope),
            "bode_file":str(folder/"sweep/bode.csv")}
    (folder/"measurement.json").write_text(json.dumps(record,indent=2)+"\n")
    return record,{name:by_frequency[f] for name,f in frequencies.items()}
