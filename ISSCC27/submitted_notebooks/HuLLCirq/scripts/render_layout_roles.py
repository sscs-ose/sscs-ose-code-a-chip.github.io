#!/usr/bin/env python3
"""Derive a read-only functional cell view from an unchanged adopted layout.

No EDA, model, simulation or adoption action is executed. Existing output
directories are refused, so prior circuit evidence is never overwritten.
Pillow is used only for the static, exportable placement figure.
"""

from __future__ import annotations

import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import struct
import sys
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hullcirq.layout_geometry import bind_def_geometry, read_gds_footprints
from hullcirq.layout_roles import collect_layout_roles, source_profile_values


_ROLE_DESCRIPTION_FALLBACKS = {
    "control": "Job control and configuration/start/completion sequencing.",
    "buffer": "Operand storage and read interfaces for the matrix job.",
    "scheduler": "Serial row-major, time-multiplexed dispatch to the sixteen MAC lanes.",
    "dispatcher": "Distribution of each scheduled operand batch to the supplied explicit PE lanes.",
    "collector": "Collection of completed PE results in the recorded output order.",
    "post": "Bias and selectable ReLU processing; the recorded job disables ReLU.",
    "fifo": "Output buffering and ready/valid backpressure.",
    "integration": "Logic originating in the integration top, outside the node implementations.",
    "clock": "Clock-distribution cells identified by retained CTS instance names.",
    "physical": "Fill, decap, tap and antenna-diode support cells identified by cell master.",
    "shared": "A source-free combinational dependency reached from multiple functional anchors; inferred, not recovered hierarchy.",
    "unknown": "No unique supported role assignment from the retained metadata.",
}


def role_description(role):
    """Keep source-profile wording; provide legacy-compatible safe fallbacks."""
    supplied = role.get("description")
    if isinstance(supplied, str) and supplied.strip():
        return supplied
    identifier = str(role.get("id", ""))
    if identifier.startswith("pe:"):
        return "Signed INT8 multiply and INT32 accumulation lane. Row/column refer to the RTL lane index, not a physical floorplan region."
    return _ROLE_DESCRIPTION_FALLBACKS.get(identifier, "No role description supplied.")


def digest(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def packed_payload(data):
    """Deduplicate strings in the offline HTML without dropping cell evidence."""
    strings = []
    lookup = {}

    def intern(value):
        if value not in lookup:
            lookup[value] = len(strings)
            strings.append(value)
        return lookup[value]

    rows = [[intern(c["id"]), intern(c["master"]), c["bbox"], intern(c["role"]), intern(c["status"]), [intern(e) for e in c["evidence"]]] for c in data["cells"]]
    return {**{k: v for k, v in data.items() if k != "cells"}, "cell_encoding": "string-table-v1", "strings": strings, "cell_rows": rows}


_BITMAP_FONT = {
    " ": ("00000",) * 7,
    "-": ("00000", "00000", "00000", "11111", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ",": ("00000", "00000", "00000", "00000", "01100", "01100", "01000"),
    ":": ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    "/": ("00001", "00010", "00100", "00100", "01000", "10000", "00000"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00010", "00100", "01000", "11111"),
    "3": ("11110", "00001", "00001", "01110", "00001", "00001", "11110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "10000", "11110", "00001", "00001", "11110"),
    "6": ("01110", "10000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00001", "01110"),
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01111", "10000", "10000", "10000", "10000", "10000", "01111"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01111", "10000", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "10010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
}


def _rgb(value):
    """Convert the profile's CSS hex colors into deterministic RGB triples."""
    if not isinstance(value, str) or not value.startswith("#"):
        raise ValueError(f"Unsupported role color: {value!r}")
    value = value[1:]
    if len(value) == 3:
        value = "".join(part * 2 for part in value)
    if len(value) != 6:
        raise ValueError(f"Unsupported role color: #{value}")
    try:
        return tuple(int(value[offset:offset + 2], 16) for offset in (0, 2, 4))
    except ValueError as exc:
        raise ValueError(f"Unsupported role color: #{value}") from exc


class _RgbCanvas:
    """Small dependency-free RGB raster used only when Pillow is unavailable."""

    def __init__(self, width, height, fill):
        self.width = width
        self.height = height
        self.pixels = bytearray(bytes(_rgb(fill)) * width * height)

    def rectangle(self, box, fill, outline=None, width=1):
        x0, y0, x1, y1 = (int(round(value)) for value in box)
        if x0 > x1:
            x0, x1 = x1, x0
        if y0 > y1:
            y0, y1 = y1, y0
        x0, y0 = max(0, x0), max(0, y0)
        x1, y1 = min(self.width - 1, x1), min(self.height - 1, y1)
        if x0 > x1 or y0 > y1:
            return
        color = bytes(_rgb(fill))
        row = color * (x1 - x0 + 1)
        for y in range(y0, y1 + 1):
            start = (y * self.width + x0) * 3
            self.pixels[start:start + len(row)] = row
        if outline:
            edge = _rgb(outline)
            for inset in range(max(1, int(width))):
                self.rectangle((x0 + inset, y0 + inset, x1 - inset, y0 + inset), "#%02x%02x%02x" % edge)
                self.rectangle((x0 + inset, y1 - inset, x1 - inset, y1 - inset), "#%02x%02x%02x" % edge)
                self.rectangle((x0 + inset, y0 + inset, x0 + inset, y1 - inset), "#%02x%02x%02x" % edge)
                self.rectangle((x1 - inset, y0 + inset, x1 - inset, y1 - inset), "#%02x%02x%02x" % edge)

    def text(self, position, value, fill="#213858", scale=2):
        x, y = (int(round(part)) for part in position)
        color = bytes(_rgb(fill))
        scale = max(1, int(scale))
        for character in str(value).upper():
            glyph = _BITMAP_FONT.get(character, _BITMAP_FONT[" "])
            for row_index, row in enumerate(glyph):
                for column_index, pixel in enumerate(row):
                    if pixel != "1":
                        continue
                    px = x + column_index * scale
                    py = y + row_index * scale
                    for sy in range(scale):
                        if py + sy < 0 or py + sy >= self.height:
                            continue
                        start_x = max(px, 0)
                        end_x = min(px + scale, self.width)
                        if start_x >= end_x:
                            continue
                        start = ((py + sy) * self.width + start_x) * 3
                        self.pixels[start:start + (end_x - start_x) * 3] = color * (end_x - start_x)
            x += 6 * scale

    def png_bytes(self, metadata):
        scanlines = bytearray()
        stride = self.width * 3
        for y in range(self.height):
            scanlines.append(0)
            start = y * stride
            scanlines.extend(self.pixels[start:start + stride])

        def chunk(kind, payload):
            return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)

        output = bytearray(b"\x89PNG\r\n\x1a\n")
        output.extend(chunk(b"IHDR", struct.pack(">IIBBBBB", self.width, self.height, 8, 2, 0, 0, 0)))
        for keyword, value in metadata:
            payload = keyword.encode("latin-1") + b"\0" + str(value).encode("latin-1", "replace")
            output.extend(chunk(b"tEXt", payload))
        output.extend(chunk(b"IDAT", zlib.compress(bytes(scanlines), level=9)))
        output.extend(chunk(b"IEND", b""))
        return bytes(output)


def _draw_figure_stdlib(data, path):
    """Render the same evidence categories without optional image packages."""
    canvas = _RgbCanvas(2300, 1800, "#f6f8fc")
    die = data["die"]
    die_width, die_height = die[2] - die[0], die[3] - die[1]
    if die_width <= 0 or die_height <= 0:
        raise ValueError("Die dimensions must be positive")
    canvas.text((65, 35), "HuLLCirq | Functional cell map", fill="#092149", scale=5)
    canvas.text((68, 99), f"Actual flattened placement - {die_width:.2f} x {die_height:.2f} um - {len(data['cells']):,} cells", fill="#42516b", scale=3)
    scale = min(1560 / die_width, 1550 / die_height)
    left, bottom = 68, 1735
    top, right = bottom - die_height * scale, left + die_width * scale
    canvas.rectangle((left, top, right, bottom), fill="#ffffff", outline="#213858", width=2)
    colors = {role["id"]: role["color"] for role in data["roles"]}
    for physical in (True, False):
        for cell in data["cells"]:
            if (cell["role"] == "physical") != physical:
                continue
            x0, y0, x1, y1 = cell["bbox"]
            rect = (
                left + (x0 - die[0]) * scale,
                bottom - (y1 - die[1]) * scale,
                left + (x1 - die[0]) * scale,
                bottom - (y0 - die[1]) * scale,
            )
            canvas.rectangle(rect, fill="#e6e9ef" if physical else colors.get(cell["role"], "#7a8494"))

    canvas.text((1700, 180), "Placed-cell roles", fill="#092149", scale=4)
    counts = Counter(cell["role"] for cell in data["cells"])
    y = 235
    count_metadata = []
    for role in data["roles"]:
        count = counts[role["id"]]
        if not count:
            continue
        role_color = "#e6e9ef" if role["id"] == "physical" else role["color"]
        canvas.rectangle((1700, y, 2190, y + 12), fill=role_color, outline="#213858")
        canvas.text((1700, y + 18), f"{role['label']}  {count:,}", fill="#213858", scale=2)
        count_metadata.append(f"{role['id']}={count}")
        y += 43
    y += 20
    canvas.text((1700, y), "Evidence, not block boundaries", fill="#092149", scale=3)
    y += 35
    for line in (
        "Colors are actual placed cells.",
        "Role evidence remains inspectable.",
        "Shared and unknown remain explicit.",
        "Physical support cells are gray.",
        "No remapping or placement was run.",
    ):
        canvas.text((1700, y), line, fill="#42516b", scale=2)
        y += 24

    metadata = (
        ("Title", "HuLLCirq functional cell map"),
        ("Renderer", "Python standard library deterministic fallback"),
        ("CellCount", len(data["cells"])),
        ("RoleCounts", ";".join(count_metadata)),
        ("DieMicrometres", f"{die[0]:.6f},{die[1]:.6f},{die[2]:.6f},{die[3]:.6f}"),
    )
    Path(path).write_bytes(canvas.png_bytes(metadata))


def _draw_figure_pillow(data, path):
    from PIL import Image, ImageDraw, ImageFont

    image = Image.new("RGB", (2300, 1800), "#f6f8fc")
    draw = ImageDraw.Draw(image)
    regular = Path("C:/Windows/Fonts/segoeui.ttf")
    bold = Path("C:/Windows/Fonts/segoeuib.ttf")

    def font(size, strong=False):
        return ImageFont.truetype(str(bold if strong else regular), size) if regular.exists() else ImageFont.load_default()

    draw.text((65, 35), "HuLLCirq | Functional cell map", font=font(46, True), fill="#092149")
    die = data["die"]
    draw.text((68, 99), f"Actual flattened placement · {die[2] - die[0]:.2f} × {die[3] - die[1]:.2f} µm · {len(data['cells']):,} cells", font=font(25), fill="#42516b")
    scale = min(1560 / (die[2] - die[0]), 1550 / (die[3] - die[1]))
    left, bottom = 68, 1735
    top, right = bottom - (die[3] - die[1]) * scale, left + (die[2] - die[0]) * scale
    draw.rectangle((left, top, right, bottom), fill="white", outline="#213858", width=2)
    colors = {r["id"]: r["color"] for r in data["roles"]}
    for physical in (True, False):
        for cell in data["cells"]:
            if (cell["role"] == "physical") != physical:
                continue
            x0, y0, x1, y1 = cell["bbox"]
            rect = (left + (x0 - die[0]) * scale, bottom - (y1 - die[1]) * scale,
                    left + (x1 - die[0]) * scale, bottom - (y0 - die[1]) * scale)
            draw.rectangle(rect, fill="#e6e9ef" if physical else colors.get(cell["role"], "#7a8494"))
    draw.text((1700, 180), "Placed-cell roles", font=font(30, True), fill="#092149")
    counts = Counter(c["role"] for c in data["cells"])
    y = 235
    for role in data["roles"]:
        count = counts[role["id"]]
        if not count:
            continue
        draw.rounded_rectangle((1700, y + 4, 1727, y + 31), radius=5, fill="#e6e9ef" if role["id"] == "physical" else role["color"])
        draw.text((1741, y), role["label"], font=font(22), fill="#213858")
        draw.text((2150, y), f"{count:,}", font=font(22), fill="#213858", anchor="ra")
        y += 40
    y += 25
    draw.text((1700, y), "Evidence, not block boundaries", font=font(24, True), fill="#092149")
    y += 44
    for text in ("Colors apply to actual placed cells.", "Source-confirmed and connectivity-", "inferred assignments are distinguished", "in the interactive cell inspector.", "Shared and unknown cells stay explicit.", "Fill / decap / tap cells are light gray.", "Routing wires are not segmented.", "No remapping or placement was run."):
        draw.text((1700, y), text, font=font(21), fill="#42516b")
        y += 32
    image.save(path, optimize=True)


def draw_figure(data, path):
    """Prefer Pillow, while keeping evidence export available without it."""
    try:
        import PIL  # noqa: F401 - availability guard for the existing renderer
    except ImportError:
        _draw_figure_stdlib(data, path)
        return
    _draw_figure_pillow(data, path)


def render_layout_roles(root, selected, output):
    """Derive one immutable view in-process; never execute EDA or overwrite files."""
    root = Path(root).resolve()
    output = Path(output).resolve()
    if not output.is_relative_to(root):
        raise ValueError("Output must remain inside HuLLCirq")
    if output.exists():
        raise ValueError("Output exists; choose a new directory to preserve prior evidence")
    profile = source_profile_values(selected)
    data = collect_layout_roles(root, selected)
    archive = root / profile['source_root']
    gds_path = (archive / profile['gds_relative_path']).resolve()
    def_path = (archive / profile['inputs']['final_def']).resolve()
    if not gds_path.is_relative_to(archive.resolve()) or not def_path.is_relative_to(archive.resolve()):
        raise ValueError('Layout geometry must remain in its pinned source archive')
    manifest = json.loads((archive / "manifest.json").read_text(encoding="utf-8"))
    for source in (gds_path, def_path):
        relative = source.relative_to(archive).as_posix()
        if manifest["files"].get(relative) != {"bytes": source.stat().st_size, "sha256": digest(source)}:
            raise ValueError(f"Original layout archive hash/size mismatch: {relative}")
    geometry = read_gds_footprints(gds_path, top_name=data["top_module"])
    binding = bind_def_geometry(def_path, geometry)
    mapped = {c["id"]: c for c in data["cells"]}
    if len(mapped) != len(data["cells"]) or set(mapped) != set(geometry["cells"]):
        raise ValueError("Role map and actual GDS instance sets differ")
    for name, cell in mapped.items():
        actual = geometry["cells"][name]
        if actual["master"] != cell["master"]:
            raise ValueError(f"Role map/GDS master mismatch: {name}")
        cell["bbox"] = actual["bbox"]
        # The inspector displays exact structured reasons as readable JSON lines.
        cell["evidence"] = [json.dumps(reason, ensure_ascii=False, sort_keys=True) if isinstance(reason, dict) else reason for reason in cell["evidence"]]
    data.update({"schema_version": "0.1", "title": "HuLLCirq functional cell map", "die": binding["die"]})
    for role in data["roles"]:
        role["description"] = role_description(role)
    data["summary"]["geometry"] = {**binding, "gds_dbu_um": geometry["dbu_um"], "gds_structures": geometry["structure_count"], "cell_boundary_layer": geometry["boundary_layer"]}
    data["notes"] += [
        "Every footprint comes from the unchanged adopted GDS SKY130 prBoundary (81/4), transformed by its actual placement. All names, masters and lower-left coordinates match the final DEF.",
        "This is a software-derived view of flattened standard cells. Colored footprints are not new placement regions, macros, a new GDS or additional circuit-verification evidence.",
        f"The accepted die is {data['die'][2]-data['die'][0]:.2f} × {data['die'][3]-data['die'][1]:.2f} µm."
    ]
    sources = [gds_path, def_path, root / "src/hullcirq/layout_geometry.py", root / "src/hullcirq/layout_roles.py", root / "scripts/render_layout_roles.py", root / "scripts/templates/layout_roles_viewer.html"]
    data["provenance"]["viewer_sources"] = [{"path": str(p.relative_to(root)).replace("\\", "/"), "bytes": p.stat().st_size, "sha256": digest(p)} for p in sources]
    data["provenance"]["additional_eda_model_or_simulation_runs"] = 0
    template = (root / "scripts/templates/layout_roles_viewer.html").read_text(encoding="utf-8")
    if template.count("__LAYOUT_DATA_JSON__") != 1:
        raise ValueError("Viewer template must have exactly one data placeholder")
    packed = json.dumps(packed_payload(data), ensure_ascii=False, separators=(",", ":"), allow_nan=False).replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    # Packing is lossless; the small loader expands strings before the viewer uses them.
    loader = "const unpackLayoutData=d=>{if(d.cell_encoding!=='string-table-v1')return d;const s=d.strings;d.cells=d.cell_rows.map(r=>({id:s[r[0]],master:s[r[1]],bbox:r[2],role:s[r[3]],status:s[r[4]],evidence:r[5].map(i=>s[i])}));delete d.strings;delete d.cell_rows;return d;};"
    html = template.replace("__LAYOUT_DATA_JSON__", packed)
    # The template uses this agreed entry point, accepting both plain and packed data.
    if "/*__LAYOUT_UNPACK__*/" not in html:
        raise ValueError("Missing viewer unpacking entry point")
    html = html.replace("/*__LAYOUT_UNPACK__*/", loader)
    raw = (json.dumps(data, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")
    output.mkdir(parents=True)
    (output / "layout_roles.html").write_text(html, encoding="utf-8", newline="\n")
    (output / "layout_roles.json.gz").write_bytes(gzip.compress(raw, mtime=0))
    draw_figure(data, output / "layout_roles.png")
    report = {"kind": "derived_read_only_visualization", "validation_status": "Passed", "summary": data["summary"], "provenance": data["provenance"], "notes": data["notes"], "raw_map_bytes": len(raw), "raw_map_sha256": hashlib.sha256(raw).hexdigest()}
    (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    files = {str(p.relative_to(output)): {"bytes": p.stat().st_size, "sha256": digest(p)} for p in output.iterdir() if p.is_file()}
    (output / "manifest.json").write_text(json.dumps({"kind": "derived_view_payload", "files": files}, indent=2) + "\n", encoding="utf-8")
    return {"output": str(output), "cells": len(data["cells"]), "bytes": sum(f["bytes"] for f in files.values()), "summary": data["summary"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "results/npu_layout_role_view")
    parser.add_argument("--source-profile", type=Path, help="Explicit immutable source bundle for a separately retained layout")
    args = parser.parse_args()
    selected = json.loads(args.source_profile.read_text(encoding='utf-8')) if args.source_profile else None
    try:
        result = render_layout_roles(ROOT, selected, args.output)
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
