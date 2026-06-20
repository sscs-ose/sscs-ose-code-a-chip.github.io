"""
Post-processing for AnalogAgent output.

Goals
-----
1. Remove comments / wrappers and parse MOS instances.
2. Support arbitrary MOS-only topologies.
3. Keep original sizing parameter names (for example L_diff/W_diff/NF_diff).
4. Rename devices to sequential XM1, XM2, ...
5. Append SKY130 geometry expressions to every MOS device.
6. Write a normalized .param line containing the original parameter names.
"""

from __future__ import annotations

import re
from collections import OrderedDict
from pathlib import Path

DEFAULT_EXTRA_PARAMS = OrderedDict([
    ("VCM", "0.9"),
    ("IB", "50u"),
    ("vi", "0.05"),
    ("fi", "100000"),
])

MOS_RE = re.compile(
    r"^(?P<name>X\S+)\s+"
    r"(?P<d>\S+)\s+(?P<g>\S+)\s+(?P<s>\S+)\s+(?P<b>\S+)\s+"
    r"(?P<model>sky130_fd_pr__(?:n|p)fet_01v8)\b(?P<rest>.*)$",
    flags=re.IGNORECASE,
)
PARAM_PAIR_RE = re.compile(r"(\w+)\s*=\s*([^\s]+)")


class PostprocessError(ValueError):
    """Raised when post-processing cannot be completed."""


def _parse_param_dict(raw_code: str) -> OrderedDict[str, str]:
    """Collect .param key=value pairs across multiple .param / continuation lines."""
    params: OrderedDict[str, str] = OrderedDict()
    collecting = False

    for line in raw_code.splitlines():
        stripped = line.strip()
        low = stripped.lower()
        if low.startswith(".param"):
            collecting = True
            content = stripped[len(".param"):].strip()
            for k, v in PARAM_PAIR_RE.findall(content):
                params[k] = v
            continue
        if collecting and stripped.startswith("+"):
            content = stripped[1:].strip()
            for k, v in PARAM_PAIR_RE.findall(content):
                params[k] = v
            continue
        collecting = False

    return params


def _parse_devices(raw_code: str) -> list[dict]:
    """Parse MOS devices from raw AnalogAgent output."""
    devices = []
    for line in raw_code.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("*"):
            continue
        if stripped.lower().startswith((".subckt", ".ends", ".param", "+")):
            continue

        match = MOS_RE.match(stripped)
        if not match:
            continue

        item = match.groupdict()
        dev_params = OrderedDict()
        for k, v in PARAM_PAIR_RE.findall(item["rest"]):
            dev_params[k.lower()] = v

        fields = {
            "name": item["name"],
            "d": item["d"],
            "g": item["g"],
            "s": item["s"],
            "b": item["b"],
            "model": item["model"],
            "params": dev_params,
            "raw": stripped,
        }
        devices.append(fields)

    return devices


def _format_device_line(dev: dict, index: int) -> str:
    l_name = dev["params"].get("l", "L")
    w_name = dev["params"].get("w", "W")
    nf_name = dev["params"].get("nf", "NF")

    first = (
        f"XM{index} {dev['d']} {dev['g']} {dev['s']} {dev['b']} {dev['model']} "
        f"L={l_name} W={w_name} nf={nf_name} "
        "ad='int((nf+1)/2) * W/nf * 0.29' as='int((nf+2)/2) * W/nf * 0.29' "
        "pd='2*int((nf+1)/2) * (W/nf + 0.29)'"
    )
    second = (
        "+ ps='2*int((nf+2)/2) * (W/nf + 0.29)' "
        "nrd='0.29 / W' nrs='0.29 / W' sa=0 sb=0 sd=0 mult=1 m=1"
    )
    return first + "\n" + second


def _format_param_line(param_dict: OrderedDict[str, str]) -> str:
    ordered = OrderedDict()

    # Keep VDD first if present.
    if "VDD" in param_dict:
        ordered["VDD"] = param_dict["VDD"]

    # Add standard extras only if missing.
    for k, v in DEFAULT_EXTRA_PARAMS.items():
        if k not in param_dict:
            ordered[k] = v

    # Then preserve all original params in original appearance order.
    for k, v in param_dict.items():
        if k not in ordered:
            ordered[k] = v

    return ".param " + " ".join(f"{k}={v}" for k, v in ordered.items())


def split_netlist_param(raw_code: str):
    """
    Convert raw AnalogAgent output into ckt_netlist / ckt_param content.

    Returns
    -------
    netlist_lines : list[str]
        Device lines with SKY130 geometry fields.
    param_line : str
        Normalized .param line while keeping original sizing parameter names.
    subckt_header : str
        Original .subckt line if present.
    """
    lines = raw_code.splitlines()
    subckt_header = next(
        (line.strip() for line in lines if line.strip().lower().startswith(".subckt")),
        "",
    )

    params = _parse_param_dict(raw_code)
    devices = _parse_devices(raw_code)
    if not devices:
        raise PostprocessError("No SKY130 MOS devices found in raw_code")

    netlist_lines = []
    for idx, dev in enumerate(devices, start=1):
        netlist_lines.extend(_format_device_line(dev, idx).splitlines())

    param_line = _format_param_line(params)
    return netlist_lines, param_line, subckt_header


def write_ckt_files(raw_code: str, netlist_path: str, param_path: str):
    """
    Post-process AnalogAgent output and write:
      - ckt_netlist.spice: device lines only
      - ckt_param.spice: single .param line
    """
    device_lines, param_line, _ = split_netlist_param(raw_code)

    Path(netlist_path).parent.mkdir(parents=True, exist_ok=True)
    with open(netlist_path, "w", encoding="utf-8") as f:
        f.write("\n".join(device_lines) + "\n")

    with open(param_path, "w", encoding="utf-8") as f:
        f.write(param_line + "\n")

    print(f"[PostProcess] Written: {netlist_path}")
    print(f"[PostProcess] Written: {param_path}")
    return netlist_path, param_path
