"""Pinned passive-model files and capacitor dimensions.
SPDX-License-Identifier: Apache-2.0
"""


import hashlib, json, math, re
from pilot import HERE
ROOT = HERE / "passives"


def verify():
    manifest=json.loads((ROOT/"source_manifest.json").read_text())
    for name,item in manifest["files"].items():
        b=(ROOT/"upstream"/name).read_bytes()
        assert len(b)==item["bytes"] and hashlib.sha256(b).hexdigest()==item["sha256"]
        assert hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()==item["git_blob"]
    return manifest


def params():
    verify()
    sources=[(ROOT/"upstream"/n).read_text() for n in ("models/r+c/res_typical__cap_typical.spice","models/r+c/res_typical__cap_typical__lin.spice","models/sky130_fd_pr__model__r+c.model.spice")]
    names=("m3_dw","tol_m3","rm3","rcvia3","tc1rm3","tc2rm3","tc1rvia3","tc2rvia3","camimc","cpmimc","crpf_precision","crpfsw_precision_1_1","sky130_fd_pr__res_high_po__var_mult")
    values={}
    for name in names:
        found=[m.group(1) for text in sources for m in re.finditer(r"(?<![\w])"+re.escape(name)+r"\s*=\s*([^\s$]+)",text)]
        if len(set(found))!=1:raise ValueError("Ambiguous pinned parameter: "+name+str(found))
        values[name]=found[0]
    return values


def includes():
    text="* Pinned typical passive parameters, selected without modifying device subcircuits\n"
    text+="\n".join(".param "+k+"="+v for k,v in params().items())+"\n"
    # Explicit deterministic mismatch settings. No stochastic or yield claim.
    text+=".param sky130_fd_pr__res_high_po__slope_spectre=0 sky130_fd_pr__res_high_po__con_slope_spectre=0\n"
    for name in ("cells/cap_mim_m3/sky130_fd_pr__cap_mim_m3_1.model.spice","cells/res_xhigh_po/sky130_fd_pr__res_xhigh_po__base.model.spice"):
        text+='.include "'+(ROOT/"upstream"/name).as_posix()+'"\n'
    return text


def bank(capacitance):
    p=params();a=float(p["camimc"]);b=4*float(p["cpmimc"])
    shift=-.025 # micrometres, exactly m3_dw=-0.025u and tol_m3=0 from pinned files.
    assert p["m3_dw"]=="-0.025u" and float(p["tol_m3"])==0
    unit=a*(20+shift)**2+b*(20+shift)
    n=math.ceil(capacitance/unit)
    effective=(-b+math.sqrt(b*b+4*a*capacitance/n))/(2*a)
    w=effective-shift
    assert 2<=w<=20
    return {"units":n,"width_um":w,"length_um":w,"nominal_capacitance_F":n*(a*effective**2+b*effective),
        "summed_plate_rectangle_um2":n*w*w,"scope":"Sum of model input rectangles, excluding routing, spacing and enclosure; not final layout area."}
