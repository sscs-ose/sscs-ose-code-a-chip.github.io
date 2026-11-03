"""Locate the SKY130 HD tt_025C_1v80 Liberty (tests and notebook skip what needs it when absent).

Search order: $GS_LIB, tools.env (GS_LIB=...), $PDK_ROOT/sky130A/..., $CONDA_PREFIX/share/pdk/sky130A/...
"""
import os
from pathlib import Path

REL = "libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib"


def lib_path_or_none():
    cands = [os.environ.get("GS_LIB")]
    env = Path(__file__).resolve().parents[1] / "tools.env"
    if env.exists():
        cands += [l.split("=", 1)[1].strip() for l in env.read_text().splitlines() if l.startswith("GS_LIB=")]
    for root in (os.environ.get("PDK_ROOT"), os.environ.get("CONDA_PREFIX") and os.environ["CONDA_PREFIX"] + "/share/pdk"):
        if root:
            cands.append(str(Path(root) / "sky130A" / REL))
    for p in cands:
        if p and Path(p).exists():
            return p
    return None
