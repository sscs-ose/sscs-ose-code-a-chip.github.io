#!/usr/bin/env python3
"""Render the exact four-branch, eight-NMOS ternary CIM leaf as an SVG."""

from __future__ import annotations

import argparse
from hashlib import sha256
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = Path("docs/figures/ternary_cell_schematic.svg")

BRANCHES = (
    (265, "BLP", "WPOS", "WLP", "NPP", "+W, +A", "XPP"),
    (450, "BLP", "WNEG", "WLN", "NPN", "-W, -A", "XPN"),
    (805, "BLN", "WNEG", "WLP", "NNP", "-W, +A", "XNP"),
    (990, "BLN", "WPOS", "WLN", "NNN", "+W, -A", "XNN"),
)


def _source(root: Path) -> Path:
    candidates = (
        root / "generated/sky130/spice/cell/ternary_cell.spice",
        root / "server_results/generated/sky130/spice/cell/ternary_cell.spice",
        root / "automx_cim/circuit/sky130.py",
    )
    return next((path for path in candidates if path.is_file()), candidates[-1])


def _verify(source: Path) -> str:
    content = source.read_text(encoding="utf-8")
    for _x, bitline, weight, wordline, node, _meaning, name in BRANCHES:
        for suffix, terminals in (
            ("W", f"{bitline} {weight} {node} VSUBS"),
            ("A", f"{node} {wordline} VGND VSUBS"),
        ):
            exact = (f"{name}_{suffix} {terminals} sky130_fd_pr__nfet_01v8 "
                     "W=0.84 L=0.15")
            if exact not in content:
                raise ValueError(f"netlist topology differs: {exact}")
    return sha256(source.read_bytes()).hexdigest()


def _text(x: float, y: float, value: str, size: int = 16, *,
          fill: str = "#1b2a41", anchor: str = "middle", weight: int = 400) -> str:
    return (f'<text x="{x}" y="{y}" text-anchor="{anchor}" '
            f'font-family="Arial, Segoe UI, sans-serif" font-size="{size}" '
            f'font-weight="{weight}" fill="{fill}">{escape(value)}</text>')


def _line(x1: float, y1: float, x2: float, y2: float, *,
          color: str = "#24334b", width: float = 3) -> str:
    return (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
            f'stroke="{color}" stroke-width="{width}" stroke-linecap="round"/>')


def _mos(x: int, y: int, gate: str, name: str, color: str) -> list[str]:
    # Conventional simplified planar NMOS glyph: channel vertical, gate left.
    return [
        _line(x, y - 18, x, y + 18, width=5),
        _line(x - 17, y - 18, x - 17, y + 18, color=color, width=4),
        _line(x - 48, y, x - 17, y, color=color, width=3),
        _text(x - 55, y + 5, gate, 15, fill=color, anchor="end", weight=700),
        _text(x + 17, y + 5, name, 11, fill="#64748b", anchor="start"),
    ]


def render(root: Path, output: Path) -> Path:
    source = _source(root)
    source_sha = _verify(source)
    output.parent.mkdir(parents=True, exist_ok=True)
    shapes = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="760" '
        'viewBox="0 0 1200 760" role="img" '
        'aria-label="Eight NMOS differential ternary CIM compute cell">',
        f'<desc>Source {escape(source.relative_to(root).as_posix())}; '
        f'SHA-256 {source_sha}. Four branches, two NMOS in series per branch. '
        'The weight controls are inputs, not SRAM storage.</desc>',
        '<rect width="1200" height="760" fill="#f8fafc"/>',
        '<rect x="48" y="36" width="1104" height="688" rx="24" '
        'fill="#ffffff" stroke="#d7e0ec" stroke-width="2"/>',
        _text(600, 86, "Ternary CIM compute cell", 32, weight=700),
        _text(600, 119, "4 discharge paths · 8 SKY130 NMOS · one cell of the 4×4 passive core",
              16, fill="#52657e"),
        '<rect x="83" y="148" width="485" height="427" rx="18" '
        'fill="#eff6ff" stroke="#b7d4f5" stroke-width="2"/>',
        '<rect x="632" y="148" width="485" height="427" rx="18" '
        'fill="#fff7ed" stroke="#f8cf9b" stroke-width="2"/>',
        _text(325, 177, "BLP discharge", 20, fill="#175a9b", weight=700),
        _text(875, 177, "BLN discharge", 20, fill="#a65b13", weight=700),
        _line(265, 214, 450, 214, color="#1d75bd", width=5),
        _line(805, 214, 990, 214, color="#d47b21", width=5),
        _text(357, 207, "BLP", 16, fill="#175a9b", weight=700),
        _text(897, 207, "BLN", 16, fill="#a65b13", weight=700),
    ]
    for x, bitline, weight, wordline, node, meaning, name in BRANCHES:
        rail_color = "#1d75bd" if bitline == "BLP" else "#d47b21"
        shapes += [
            _text(x, 247, meaning, 15, fill=rail_color, weight=700),
            _line(x, 214, x, 270, color=rail_color),
            *_mos(x, 292, weight, f"{name}_W", "#7c3fa0"),
            _line(x, 310, x, 413),
            '<circle cx="%d" cy="355" r="5" fill="#24334b"/>' % x,
            _text(x + 18, 358, node, 12, fill="#52657e", anchor="start"),
            *_mos(x, 431, wordline, f"{name}_A", "#008477"),
            _line(x, 449, x, 528),
        ]
    shapes += [
        _line(220, 528, 1035, 528, color="#24334b", width=5),
        _line(627, 528, 627, 551, color="#24334b", width=4),
        _line(606, 551, 648, 551, color="#24334b", width=4),
        _line(613, 558, 641, 558, color="#24334b", width=4),
        _line(619, 565, 635, 565, color="#24334b", width=4),
        _text(675, 557, "VGND", 15, anchor="start", weight=700),
        '<rect x="83" y="603" width="1034" height="87" rx="14" '
        'fill="#f1f5f9"/>',
        _text(103, 630, "Weight: WPOS/WNEG = 10 → +1, 01 → −1, 00 → 0",
              15, anchor="start", weight=700),
        _text(103, 654, "Activation: WLP/WLN choose sign; pulse width carries magnitude.",
              14, fill="#52657e", anchor="start"),
        _text(103, 677, "All NMOS bulks → VSUBS. No SRAM/RRAM bit or local weight latch in this leaf.",
              14, fill="#9d3d2f", anchor="start"),
        _text(1094, 630, "V(BLN) − V(BLP)", 15, fill="#24334b", anchor="end", weight=700),
        '</svg>',
    ]
    output.write_text("\n".join(shapes) + "\n", encoding="utf-8")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    root = args.root.resolve()
    output = args.output if args.output.is_absolute() else root / args.output
    print(render(root, output))
