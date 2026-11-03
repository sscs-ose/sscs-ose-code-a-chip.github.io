"""Query device currents and AC terminal matrices at a specified bias."""
import json
import numpy as np
from .native import spice, complex_raw, read_scalar_raw


def device_matrices(base,folder,frequencies,step=1e-4,dc_override=None):
    folder.mkdir(parents=True)
    state=json.loads((base/"summary.json").read_text())
    ports=[p[0] for p in state["ports"]]
    saved=read_scalar_raw(base/"op.raw")
    dc=np.array([saved[f"v({p})"] for p in ports]) if dc_override is None else np.asarray(dc_override)
    deck=["Device terminal AC matrices at the complete circuit operating point"]
    deck += state["design"]["directives"] + state["device_lines"]
    deck += [f"vc_{p} {p} 0 DC {v:.17g} AC 0" for p,v in zip(ports,dc)]
    deck += [".save all",".control","set filetype=ascii","op","write clamped.raw all"]
    settings=[("base",None,0)]
    if step is not None:
        settings += [(f"{sign}_{k}",k,d) for k in range(len(ports))
                     for sign,d in (("plus",step),("minus",-step))]
    for label,k,shift in settings:
        if k is not None:deck.append(f"alter vc_{ports[k]} dc = {dc[k]+shift:.17g}")
        for col,p in enumerate(ports):
            deck.append(f"alter vc_{p} acmag = 1")
            for f_index,f in enumerate(frequencies):
                deck += [f"ac lin 1 {f:.17g} {f:.17g}",
                         f"write {label}_{col}_{f_index}.raw all"]
            deck.append(f"alter vc_{p} acmag = 0")
        if k is not None:deck.append(f"alter vc_{ports[k]} dc = {dc[k]:.17g}")
    spice([*deck,"quit",".endc",".end"],folder,"device.cir")
    clamped=read_scalar_raw(folder/"clamped.raw")
    mismatch=max(abs(-clamped[f"i(vc_{p})"]-saved[f"i(v_{p})"]) for p in ports)
    if dc_override is None and mismatch>1e-11:raise ValueError(f"Clamped device current mismatch: {mismatch}")
    def matrix(label):
        y=np.zeros((len(frequencies),len(ports),len(ports)),complex)
        for col in range(len(ports)):
            for f_index in range(len(frequencies)):
                result=complex_raw(folder/f"{label}_{col}_{f_index}.raw")
                y[f_index,:,col]=[-result[f"i(vc_{p})"] for p in ports]
        return y
    y=matrix("base")
    derivative=None if step is None else np.array(
        [(matrix(f"plus_{k}")-matrix(f"minus_{k}"))/(2*step) for k in range(len(ports))])
    conservation=max(np.max(abs(y.sum(axis=1))),np.max(abs(y.sum(axis=2))))
    if conservation>1e-8:raise ValueError(f"AC terminal conservation mismatch: {conservation}")
    arrays={"Y":y,"frequencies_Hz":frequencies,"ports":ports}
    if derivative is not None:arrays["dY_dV"]=derivative
    np.savez_compressed(folder/"admittance.npz",**arrays)
    return y,derivative,{"current_mismatch_A":mismatch if dc_override is None else None,
                         "dc_currents_A":[-clamped[f"i(vc_{p})"] for p in ports],"terminal_conservation_S":float(conservation),
                         "voltage_step_V":step}
