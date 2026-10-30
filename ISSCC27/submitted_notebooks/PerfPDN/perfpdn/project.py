"""Read a design description and the shared SKY130 tool profile."""
import json
import os
import math
import re
from .metric_policy import validate_policy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PDK = Path(os.environ.get("PDK_ROOT", Path.home()/".local/share/perfpdn/pdks"))/"sky130A"
SIMULATOR = Path.home()/".local/share/perfpdn/tools/ngspice-47/bin/ngspice"


def load(path):
    path = Path(path).resolve()
    project = json.loads(path.read_text())
    if not re.fullmatch(r"[A-Za-z0-9_-]+",project["name"]):
        raise ValueError("Use letters, digits, underscores or hyphens for the project name.")
    if project["technology"] != "sky130A":
        raise ValueError("This release supports the SKY130A technology profile.")
    for key in ("testbench", "layout"):
        project[key] = str((path.parent/project[key]).resolve())
        if not Path(project[key]).is_file():
            raise ValueError(f"Missing {key}: {project[key]}")
    project["project_file"] = str(path)
    project.setdefault("mesh_step_um", .25)
    project.setdefault("frequency_range_Hz", [1e3, 1e11])
    project.setdefault("voltage_step_V", 1e-4)
    project.setdefault("verification_count", 1)
    project.setdefault("refine_count", 8)
    if project["mesh_step_um"] <= 0 or project["actions"]["budget_um2"] <= 0:
        raise ValueError("Mesh spacing and area budget must be positive.")
    for key in ("mesh_step_um","voltage_step_V"):
        if not math.isfinite(project[key]) or project[key]<=0:raise ValueError(f"Invalid {key}")
    lo,hi=project["frequency_range_Hz"]
    if not 0<lo<hi or not math.isfinite(hi):raise ValueError("Set an increasing positive frequency range.")
    for key in ("verification_count","refine_count"):
        value=project[key]
        if value is not None and (not isinstance(value,int) or value<1):raise ValueError(f"Invalid {key}")
    rules=project["actions"]
    if not rules["nets"] or not rules["layers"] or set(rules["layers"])-{"li","m1","m2","m3","m4","m5"}:
        raise ValueError("Choose editable nets and supported conductor layers.")
    if not rules["width_increments_um"] or any(not math.isfinite(v) or v<=0 for v in rules["width_increments_um"]):
        raise ValueError("Width increments must be positive finite values.")
    for key in ("budget_um2","end_clearance_um","minimum_length_um","minimum_aspect_ratio"):
        if key in rules and (not math.isfinite(rules[key]) or rules[key]<=0):raise ValueError(f"Invalid action rule: {key}")
    for pair in project["transfer"].values():
        if len(pair)!=2:raise ValueError("Define input and output as positive/reference node pairs.")
    for name, metric in project["metrics"].items():
        metric.setdefault("label",name)
        if metric["measurement"] not in ("gain_dB", "unity_Hz"):
            raise ValueError(f"Unsupported metric measurement: {name}")
        if metric["measurement"]=="gain_dB" and not 0<metric.get("frequency_Hz",0)<=hi:
            raise ValueError(f"Set a valid gain frequency for {name}.")
    validate_policy({"metrics":project["metrics"]})
    return project
