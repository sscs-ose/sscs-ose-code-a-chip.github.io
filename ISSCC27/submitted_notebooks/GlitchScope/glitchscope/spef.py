"""Minimal SPEF reader: total parasitic (wire) capacitance per net.

Used to add post-layout wire capacitance to the net loads
(``PulseSimulator(..., wire_cap_ff_by_net=read_spef_caps(path))``).  Lumped
capacitance only: RC delay along the wire is not modelled.
"""
from __future__ import annotations

import re
from pathlib import Path

_UNIT = {"F": 1e15, "PF": 1e3, "FF": 1.0, "NF": 1e6, "UF": 1e9}


def _norm(name):
    return name.replace("\\", "")


def read_spef_caps(path):
    """{net name: total capacitance in fF} from the *D_NET headers of a SPEF file."""
    text = Path(path).read_text(errors="replace")
    cu = re.search(r"^\*C_UNIT\s+([\d.eE+-]+)\s+(\w+)", text, re.M)
    scale = float(cu.group(1)) * _UNIT[cu.group(2).upper()] if cu else 1.0
    names = {}
    nm = re.search(r"^\*NAME_MAP\s*$(.*?)^\*(?:PORTS|D_NET|POWER_NETS|GROUND_NETS)\b", text, re.M | re.S)
    if nm:
        for m in re.finditer(r"^(\*\d+)\s+(\S+)", nm.group(1), re.M):
            names[m.group(1)] = _norm(m.group(2))
    caps = {}
    for m in re.finditer(r"^\*D_NET\s+(\S+)\s+([\d.eE+-]+)", text, re.M):
        n = names.get(m.group(1), _norm(m.group(1)))
        caps[n] = float(m.group(2)) * scale
    return caps
