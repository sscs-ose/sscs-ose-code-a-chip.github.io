"""Read-only cell footprints from the adopted SKY130 GDS and final DEF.

This deliberately small reader accepts the records needed by the retained GDS.
It uses the standard-cell boundary, not the bounding box of routing or labels.
It does not extract connectivity, assign circuit roles or alter any layout.
"""

from __future__ import annotations

from collections import Counter
import math
from pathlib import Path
import re
import struct


def gds_real(value: bytes) -> float:
    if len(value) != 8:
        raise ValueError("A GDS real must contain eight bytes")
    word = int.from_bytes(value, "big")
    return (-1 if word >> 63 else 1) * (word & ((1 << 56) - 1)) / (1 << 56) * 16 ** (((word >> 56) & 127) - 64)


def reference_bbox(boundary, origin, angle=0, reflected=False, magnification=1):
    """GDS reflection about X, followed by rotation and translation."""
    if not math.isclose(magnification, 1):
        raise ValueError("Scaled standard-cell instances are unsupported")
    if angle not in (0, 90, 180, 270, -90):
        raise ValueError("Non-orthogonal standard-cell instances are unsupported")
    sine, cosine = round(math.sin(math.radians(angle))), round(math.cos(math.radians(angle)))
    x0, y0, x1, y1 = boundary
    points = []
    for x, y in ((x0, y0), (x0, y1), (x1, y0), (x1, y1)):
        y = -y if reflected else y
        points.append((cosine * x - sine * y + origin[0], sine * x + cosine * y + origin[1]))
    return [min(p[0] for p in points), min(p[1] for p in points), max(p[0] for p in points), max(p[1] for p in points)]


def read_gds_footprints(path: Path, top_name="hullcirq_npu"):
    data = path.read_bytes()
    offset = 0
    current = None
    element = None
    boundaries = {}
    references = []
    cell_names = set()
    dbu_um = None
    while offset < len(data):
        if offset + 4 > len(data):
            raise ValueError("Truncated GDS record header")
        length, kind, datatype = struct.unpack(">HBB", data[offset:offset + 4])
        if length < 4 or length % 2 or offset + length > len(data):
            raise ValueError("Invalid or truncated GDS record")
        value = data[offset + 4:offset + length]
        offset += length
        if kind == 3:
            if len(value) != 16:
                raise ValueError("Invalid GDS units")
            dbu_um = gds_real(value[8:]) * 1e6
        elif kind == 6:
            current = value.rstrip(b"\0").decode("ascii")
            if current in cell_names:
                raise ValueError("Duplicate GDS cell name")
            cell_names.add(current)
        elif kind in (8, 9, 10, 11, 12, 45):
            element = {"kind": kind, "cell": current, "props": {}, "angle": 0, "mag": 1, "reflected": False}
        elif element is not None:
            if kind in (13, 14):
                element["layer" if kind == 13 else "datatype"] = struct.unpack(">h", value)[0]
            elif kind == 16:
                if not value or len(value) % 8:
                    raise ValueError("Invalid GDS XY record")
                numbers = struct.unpack(">" + "i" * (len(value) // 4), value)
                element["xy"] = list(zip(numbers[::2], numbers[1::2]))
            elif kind == 18:
                element["master"] = value.rstrip(b"\0").decode("ascii")
            elif kind == 26:
                flags = struct.unpack(">H", value)[0]
                if flags & ~0x8000:
                    raise ValueError("Unsupported GDS reference transformation flags")
                element["reflected"] = bool(flags & 0x8000)
            elif kind in (27, 28):
                element["mag" if kind == 27 else "angle"] = gds_real(value)
            elif kind == 43:
                element["property"] = struct.unpack(">H", value)[0]
            elif kind == 44:
                attribute = element.get("property")
                if attribute is None or attribute in element["props"]:
                    raise ValueError("Missing or duplicate GDS property attribute")
                element["props"][attribute] = value.rstrip(b"\0").decode("ascii")
            elif kind == 17:
                if element["kind"] == 8 and (element.get("layer"), element.get("datatype")) == (81, 4):
                    # SKY130 prBoundary: the placed-cell footprint, in the actual GDS.
                    xy = element["xy"]
                    boundary = [min(p[0] for p in xy), min(p[1] for p in xy), max(p[0] for p in xy), max(p[1] for p in xy)]
                    if current in boundaries:
                        raise ValueError("Multiple standard-cell boundaries are unsupported")
                    boundaries[current] = boundary
                if current == top_name and element["kind"] in (10, 11):
                    if element["kind"] == 11:
                        raise ValueError("Array references are unsupported by this retained-layout reader")
                    references.append(element)
                elif current != top_name and element["kind"] in (10, 11):
                    raise ValueError("Nested standard-cell references require a general GDS reader")
                element = None
    if dbu_um is None or not math.isfinite(dbu_um) or dbu_um <= 0 or top_name not in cell_names:
        raise ValueError("Missing GDS top or valid units")
    result = {}
    for ref in references:
        name = ref["props"].get(61)
        if not name or name in result or len(ref.get("xy", [])) != 1:
            raise ValueError("Missing/duplicate instance name property 61 or invalid origin")
        master = ref["master"]
        if master not in boundaries:
            raise ValueError(f"Missing SKY130 cell boundary for {master}")
        bbox = reference_bbox(boundaries[master], ref["xy"][0], ref["angle"], ref["reflected"], ref["mag"])
        result[name] = {"master": master, "bbox": [round(v * dbu_um, 6) for v in bbox]}
    if not result:
        raise ValueError("No named placed GDS instances")
    return {"cells": result, "dbu_um": dbu_um, "structure_count": len(cell_names), "boundary_layer": [81, 4]}


def bind_def_geometry(path: Path, gds):
    """Require every final DEF instance/master/origin to match the actual GDS."""
    text = path.read_text(encoding="utf-8")
    units = re.search(r"UNITS\s+DISTANCE\s+MICRONS\s+(\d+)\s*;", text)
    die = re.search(r"DIEAREA\s*\(\s*(-?\d+)\s+(-?\d+)\s*\)\s*\(\s*(-?\d+)\s+(-?\d+)\s*\)\s*;", text)
    section = re.search(r"\bCOMPONENTS\s+(\d+)\s*;(.*?)\bEND\s+COMPONENTS", text, re.S)
    if not units or not die or not section:
        raise ValueError("Missing DEF units, die or components")
    scale = int(units[1])
    if scale <= 0:
        raise ValueError("Invalid DEF units")
    die_bbox = [int(v) / scale for v in die.groups()]
    components = {}
    orientations = Counter()
    for statement in section[2].split(";"):
        statement = statement.strip()
        if not statement:
            continue
        match = re.match(r"-\s+(\S+)\s+(\S+).*?\+\s+(?:PLACED|FIXED)\s*\(\s*(-?\d+)\s+(-?\d+)\s*\)\s+(N|S|E|W|FN|FS|FE|FW)\b", statement, re.S)
        if not match:
            raise ValueError("Unsupported or unplaced DEF component")
        name, master, x, y, orientation = match.groups()
        if name in components:
            raise ValueError("Duplicate DEF instance")
        components[name] = master
        orientations[orientation] += 1
        actual = gds["cells"].get(name)
        if actual is None or actual["master"] != master:
            raise ValueError(f"DEF/GDS instance or master mismatch: {name}")
        if not all(math.isclose(a, b, abs_tol=1e-6) for a, b in zip(actual["bbox"][:2], [int(x) / scale, int(y) / scale])):
            raise ValueError(f"DEF/GDS footprint origin mismatch: {name}")
        if any(actual["bbox"][i] < die_bbox[i] - 1e-6 for i in (0, 1)) or any(actual["bbox"][i] > die_bbox[i] + 1e-6 for i in (2, 3)):
            raise ValueError(f"Cell footprint extends outside DEF die: {name}")
    if len(components) != int(section[1]) or set(components) != set(gds["cells"]):
        raise ValueError("DEF/GDS component count or name set mismatch")
    return {"die": die_bbox, "component_count": len(components), "orientations": dict(orientations), "geometry_binding": "All GDS property-61 instances, masters and transformed cell-boundary lower-left coordinates match the final DEF."}
