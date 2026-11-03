"""Minimal reader for Liberty output-pin internal_power tables (rise/fall energy, pJ)."""
from __future__ import annotations
import re
from pathlib import Path
from .liberty import _strip_comments, _blocks, _table, bilinear, read_liberty_text, load_templates


def read_internal_power(path, cells):
    text = _strip_comments(read_liberty_text(path))
    load_templates(text)
    out = {}
    for name in cells:
        m = re.search(r'cell\s*\(\s*"?' + re.escape(name) + r'"?\s*\)\s*\{', text)
        if not m:
            continue
        depth, j = 0, m.end() - 1
        while True:
            ch = text[j]
            depth += ch == "{"
            depth -= ch == "}"
            if depth == 0:
                break
            j += 1
        body = text[m.end():j]
        for pin_name, pbody in _blocks(body, "pin"):
            if "direction" not in pbody or not re.search(r'direction\s*:\s*"?output', pbody):
                continue
            for _, ip in _blocks(pbody, "internal_power"):
                rp = re.search(r'related_pin\s*:\s*"?(\w+)"?', ip)
                tabs = {}
                for kind in ("rise_power", "fall_power"):
                    blk = list(_blocks(ip, kind))
                    if blk:
                        tabs[kind] = _table(blk[0][1], blk[0][0])
                out.setdefault(name, {})[(pin_name.strip('"'), rp.group(1) if rp else None)] = tabs
    return out


def internal_energy_pj(tabs, rise, slew_ns, load_pf):
    t = tabs["rise_power" if rise else "fall_power"]
    return bilinear(t, slew_ns, load_pf)


def liberty_units(path):
    """Library-wide units from the Liberty header: time unit (ps), capacitance unit (fF),
    voltage unit (V), nominal voltage (V) and the internal-energy unit (fJ) =
    capacitive_load_unit x voltage_unit^2 (Liberty convention for internal_power tables)."""
    head = read_liberty_text(path)[:400_000]
    head = _strip_comments(head)
    tu = re.search(r'\btime_unit\s*:\s*"?\s*([0-9.]*)\s*(fs|ps|ns|us)\s*"?\s*;', head)
    tps = float(tu.group(1) or 1) * {"fs": 1e-3, "ps": 1.0, "ns": 1e3, "us": 1e6}[tu.group(2)] if tu else 1000.0
    cu = re.search(r'\bcapacitive_load_unit\s*\(\s*([0-9.eE+-]+)\s*,\s*"?([a-zA-Z]+)"?\s*\)', head)
    cff = float(cu.group(1)) * {"ff": 1.0, "pf": 1e3}[cu.group(2).lower()] if cu else 1e3
    vu = re.search(r'\bvoltage_unit\s*:\s*"?\s*([0-9.eE+-]*)\s*(m?V)\s*"?\s*;', head)
    vv = (float(vu.group(1) or 1) * (1e-3 if vu.group(2) == "mV" else 1.0)) if vu else 1.0
    nv = re.search(r'\bnom_voltage\s*:\s*([0-9.eE+-]+)\s*;', head)
    name = re.search(r'\blibrary\s*\(\s*"?([^")]+)"?\s*\)', head)
    return dict(time_ps=tps, cap_ff=cff, volt_v=vv, vdd=float(nv.group(1)) * vv if nv else 1.8,
                energy_fj=cff * vv * vv, name=name.group(1).strip() if name else "")
