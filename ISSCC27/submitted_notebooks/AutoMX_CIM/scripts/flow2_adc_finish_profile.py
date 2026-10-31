"""Measured-reset-track input loading and fresh-completion conversion probes."""
from pathlib import Path
import re

import numpy as np

from scripts import flow2_adc_native_sessions as sessions
from scripts import flow2_waveforms as waves
from scripts import run_flow2_adc_waveform as adc

PROFILE = {"name": "OBSERVED_RESET_TRACK_EARLY_COMPLETION_V7", "ramp_s": .5e-9,
    "load": {"step_start_s": 5e-9, "step_end_s": 7e-9, "integrate_s": [4.9e-9,11e-9],
             "gate_window_s": [5e-9,9e-9], "stop_s": 12e-9, "reset": "HELD_LOW", "step_v": .01},
    "conversion": {"reset_release_s": 10e-9, "start_s": 20e-9, "maximum_stop_s": 3e-6,
                   "finish_policy": "fresh completion plus 40 ns, then validate all raw bit/clock gates"},
    "not_signoff": "standalone ideal-source ADC; new reset-track protocol, not loaded readout or full transfer/PVT"}


def deck(model, net, pins, probes, *, task, cm=.9, diff=.1):
    text = adc.deck(Path(model), Path(net), pins, probes, task=task, cm=cm, diff=diff)
    text = re.sub(r"(?ms)^\.control\s*$.*?^\.endc\s*$", "", text)
    lines = [l for l in text.splitlines() if not l.startswith(".measure ")]
    stop = "12n" if task == "load" else "3u"
    for i, line in enumerate(lines):
        if line.startswith(".option "):
            lines[i] = ".option klu method=gear reltol=1e-4 abstol=1e-13"
        elif line.startswith("VVDD "):
            lines[i] = f"VVDD VPWR 0 PWL(0 0 .5n 1.8 {stop} 1.8)"
        elif line.startswith("VVCM "):
            lines[i] = f"VVCM VCM 0 PWL(0 0 .5n .9 {stop} .9)"
        elif line.startswith("VRST "):
            lines[i] = "VRST RST_N 0 0" if task == "load" else "VRST RST_N 0 PWL(0 0 10n 0 10.1n 1.8 3u 1.8)"
        elif line.startswith("VSTART "):
            lines[i] = "VSTART START 0 0" if task == "load" else "VSTART START 0 PWL(0 0 20n 0 20.1n 1.8 30n 1.8 30.1n 0 3u 0)"
        elif line.startswith(("VINP ","VINN ")):
            pol = "P" if line.startswith("VINP ") else "N"
            sign = 1 if pol == "P" else -1
            value = cm-sign*.001 if task == "load" else cm+sign*diff/2
            lines[i] = (f"VIN{pol} AIN{pol} 0 PWL(0 0 .5n {value:.12g} 5n {value:.12g} 7n {value+.01:.12g} 12n {value+.01:.12g})"
                if task == "load" else f"VIN{pol} AIN{pol} 0 PWL(0 0 .5n {value:.12g} 3u {value:.12g})")
        elif line.startswith(".tran "):
            lines[i] = ".tran 100p 12n 0 100p" if task == "load" else ".tran 1n 3u 0 1n"
    saved = next(i for i,l in enumerate(lines) if l.startswith(".save "))
    names = list(dict.fromkeys(lines[saved].split()[1:]+["v(VPWR)","v(VCM)","v(RST_N)","v(START)"]))
    if task == "conversion":
        names += ["i(VINP)","i(VINN)","i(VVDD)"]
    lines[saved] = ".save "+" ".join(names)
    if any(l.startswith((".control", ".ic", "BSTATE")) or re.search(r"(?i)\buic\b|\brshunt\b", l) for l in lines):
        raise ValueError("bare physical ADC circuit required")
    return "\n".join(lines)+"\n", names


def validate_sources(vectors, task, cm, diff):
    for name in ("v(vpwr)","v(vcm)","v(ainp)","v(ainn)","v(rst_n)","v(start)"):
        if abs(waves.sample(vectors,name,0.)) > 1e-7:
            raise ValueError("independent source was not initially zero: "+name)
    for name, value in (("v(vpwr)",1.8),("v(vcm)",.9)):
        if abs(waves.sample(vectors,name,4e-9)-value) > 1e-5:
            raise ValueError("power/reference not settled")
    if task == "load":
        if vectors["time"][-1] < 12e-9*(1-1e-8):
            raise ValueError("incomplete reset-track load waveform")
        if np.max(np.abs(vectors["v(rst_n)"])) > .18 or np.max(np.abs(vectors["v(start)"])) > .18:
            raise ValueError("load must remain in reset-track")
        for side, sign in (("p",-1),("n",1)):
            for t, extra in ((4.9e-9,0.),(11e-9,.01)):
                if abs(waves.sample(vectors,"v(ain"+side+")",t)-(cm+sign*.001+extra)) > 1e-5:
                    raise ValueError("reset-track input step changed")


def analyze(vectors, probes, *, task, cm=.9, diff=.1):
    validate_sources(vectors,task,cm,diff)
    if task == "conversion":
        result = adc.analyze_conversion(vectors,diff,minimum_stop_s=0.,input_sample_s=15e-9,
            reset_sample_s=15e-9,start_sample_s=25e-9,before_start_s=18e-9,
            start_s=20e-9,complete_after_s=22e-9,cm=cm)
        end = result["conversion_finished_time_s"]+30e-9
        result["conversion_input_charge_c"] = {s:sessions.integrate(vectors,"i(vin"+s+")",20e-9,end) for s in ("p","n")}
        mask = (vectors["time"]>=20e-9)&(vectors["time"]<=end)
        result["peak_input_current_abs_a"] = {s:float(np.max(np.abs(vectors["i(vin"+s+")"][mask]))) for s in ("p","n")}
        return result
    witness = waves.sampling_witness(vectors,probes,start_s=5e-9,stop_s=9e-9)
    if not witness["sampling_command_on_witnessed"]:
        raise ValueError("reset-track input switch gates were not simultaneously ON")
    q = {s:sessions.integrate(vectors,"i(vin"+s+")",4.9e-9,11e-9) for s in ("p","n")}
    return {"gate_witness":witness,"charge_per_input_c":q,
        "apparent_charge_over_step_ff":{s:abs(q[s])/.01*1e15 for s in q},
        "measurement": "quadrature of original native current samples, endpoint-interpolated only",
        "input_common_mode_v":cm,
        "scope": "reset-track driven-input charge including kickback; not deembedded capacitance or held-node droop"}


def points(task):
    if task == "load":
        return [.5e-9,5e-9,9e-9,12e-9]
    return [.5e-9,5e-9,12e-9,20e-9]+[n*1e-9 for n in range(40,1001,40)]+[1.2e-6,1.5e-6,2e-6,2.5e-6,3e-6]
