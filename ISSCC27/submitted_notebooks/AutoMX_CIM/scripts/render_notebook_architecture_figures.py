#!/usr/bin/env python3
"""Generate architecture diagrams for the AutoMX-CIM SKY130 notebook.

The drawings describe the checked-in circuit and RTL boundaries. They are
schematics, not replacement evidence for a measured waveform or GDS render.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
OUT = Path("docs/figures")

NAVY = "#172b4d"
INK = "#26364d"
MUTED = "#5b6d83"
BLUE = "#dceafb"
BLUE_EDGE = "#4f80bd"
TEAL = "#dcf4ed"
TEAL_EDGE = "#21866f"
AMBER = "#fff0d0"
AMBER_EDGE = "#d79224"
GREY = "#edf0f4"
GREY_EDGE = "#8491a2"
WHITE = "#ffffff"
BG = "#f8fafc"


class Drawing:
    def __init__(self, width: int, height: int, title: str, subtitle: str = ""):
        self.width, self.height = width, height
        self.elements = []
        self.rect(0, 0, width, height, BG, BG, 0)
        self.text(42, 54, title, 30, NAVY, 700, "start")
        if subtitle:
            self.text(42, 86, subtitle, 16, MUTED, 400, "start")
        self.line(42, 105, width - 42, 105, "#d5dfe9", 2)

    def rect(self, x, y, w, h, fill=WHITE, stroke="#d5dfe9", sw=2):
        self.elements.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')

    def line(self, x1, y1, x2, y2, color=INK, sw=2):
        self.elements.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
            f'stroke="{color}" stroke-width="{sw}" stroke-linecap="round"/>')

    def circle(self, x, y, r, fill):
        self.elements.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}"/>')

    def text(self, x, y, value, size=17, color=INK, weight=400, anchor="middle"):
        self.elements.append(
            f'<text x="{x}" y="{y}" text-anchor="{anchor}" '
            f'font-family="Arial, Segoe UI, sans-serif" font-size="{size}" '
            f'font-weight="{weight}" fill="{color}">{escape(str(value))}</text>')

    def arrow(self, x1, y1, x2, y2, color=INK, sw=3):
        self.line(x1, y1, x2, y2, color, sw)
        if abs(x2 - x1) >= abs(y2 - y1):
            sign = 1 if x2 > x1 else -1
            self.line(x2 - sign * 10, y2 - 6, x2, y2, color, sw)
            self.line(x2 - sign * 10, y2 + 6, x2, y2, color, sw)
        else:
            sign = 1 if y2 > y1 else -1
            self.line(x2 - 6, y2 - sign * 10, x2, y2, color, sw)
            self.line(x2 + 6, y2 - sign * 10, x2, y2, color, sw)

    def card(self, x, y, w, h, heading, body, fill=WHITE, edge="#d5dfe9"):
        self.rect(x, y, w, h, fill, edge, 2)
        cx = x + w / 2
        self.text(cx, y + 38, heading, 20, NAVY, 700)
        for index, item in enumerate(body):
            self.text(cx, y + 77 + 27 * index, item, 16, INK)

    def save(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.width}" '
               f'height="{self.height}" viewBox="0 0 {self.width} {self.height}">\n'
               + "\n".join(self.elements) + "\n</svg>\n")
        path.write_text(svg, encoding="utf-8")


def workflow() -> Drawing:
    d = Drawing(1200, 580, "AutoMX-CIM co-design workflow",
                "One traceable path from numerical reference to the rendered physical demonstrator")
    cards = [
        ("MHA reference", ["Tiny MHA + MXFP4", "QTEA vectors", "software oracle"], BLUE, BLUE_EDGE),
        ("CIM circuit", ["8-NMOS ternary cell", "4x4 differential", "SPICE validation"], TEAL, TEAL_EDGE),
        ("Physical core", ["SKY130 GDS + LEF", "DRC / LVS / PEX", "post-layout checks"], TEAL, TEAL_EDGE),
        ("RTL protocol", ["32x8 logical tile", "2+2 controller", "Verilator regression"], BLUE, BLUE_EDGE),
        ("Core-bound top", ["OpenLane routing", "top DRC / macro LVS", "real GDS + PNG"], BLUE, BLUE_EDGE),
    ]
    for i, (heading, body, fill, edge) in enumerate(cards):
        x = 34 + i * 234
        d.card(x, 160, 204, 225, heading, body, fill, edge)
        if i < 4:
            d.arrow(x + 207, 272, x + 229, 272, NAVY)
    d.rect(34, 430, 1132, 100, AMBER, AMBER_EDGE)
    d.text(55, 466, "Separate unfinished branch: on-chip phase engine, sample/hold, ADC and clocked wrapper", 18, NAVY, 700, "start")
    d.text(55, 500, "Requires physical views plus transfer, PVT, full-chip LVS/PEX and timing evidence.", 17, INK, 400, "start")
    return d


def computing_boundary() -> Drawing:
    d = Drawing(1200, 640, "What the CIM demonstrator actually computes",
                "The full MHA equation is a numerical reference; silicon evidence covers a smaller base operation")
    d.card(45, 150, 330, 165, "Software MHA reference",
           ["Q = X WQ, K = X WK, V = X WV", "O = softmax(QK^T / sqrt(d)) V"], BLUE, BLUE_EDGE)
    d.card(435, 150, 330, 165, "Candidate reusable tile",
           ["Q / K / V / WO projections", "logical 32x8 schedule", "mapped to repeated 4x4 reads"], TEAL, TEAL_EDGE)
    d.card(825, 150, 330, 165, "Measured passive core",
           ["4x4 ternary base sum", "differential BLP / BLN", "no on-chip sensing"], TEAL, TEAL_EDGE)
    d.arrow(379, 232, 429, 232, NAVY)
    d.arrow(769, 232, 819, 232, NAVY)
    d.rect(100, 365, 1000, 190, WHITE, "#d5dfe9")
    d.text(600, 404, "For a column c, the physical base mode represents", 20, NAVY, 700)
    d.text(600, 452, "s[c] = sum_r ACT_X2[r] * (WPOS[r,c] - WNEG[r,c])", 23, TEAL_EDGE, 700)
    d.text(600, 497, "E8M0 scaling, QTEA correction, QK^T, softmax and A@V remain digital.", 17, INK)
    d.text(600, 525, "The rendered top does not contain a complete MHA datapath or analog ADC.", 16, MUTED)
    return d


def core_array() -> Drawing:
    d = Drawing(1200, 710, "Physical passive CIM core: 4 rows x 4 columns",
                "Each square is one 8-NMOS differential ternary cell; WPOS/WNEG encode the weight")
    left, top, cell_w, cell_h, gap_x, gap_y = 215, 215, 125, 78, 18, 17
    for c in range(4):
        cx = left + c * (cell_w + gap_x) + cell_w / 2
        d.rect(cx - 51, 144, 102, 43, BLUE, BLUE_EDGE)
        d.text(cx, 171, f"BLP{c} / BLN{c}", 14, NAVY, 700)
        d.line(cx, 188, cx, top - 10, BLUE_EDGE, 2)
    for r in range(4):
        y = top + r * (cell_h + gap_y)
        d.rect(35, y + 16, 143, 44, BLUE, BLUE_EDGE)
        d.text(106, y + 44, f"WLP{r} / WLN{r}", 15, NAVY, 700)
        d.line(179, y + 38, left - 8, y + 38, BLUE_EDGE, 2)
        for c in range(4):
            x = left + c * (cell_w + gap_x)
            d.rect(x, y, cell_w, cell_h, TEAL, TEAL_EDGE)
            d.text(x + cell_w / 2, y + 32, f"T[{r},{c}]", 18, NAVY, 700)
            d.text(x + cell_w / 2, y + 57, "8 NMOS", 14, MUTED)
    d.rect(842, 194, 320, 292, AMBER, AMBER_EDGE)
    d.text(1002, 230, "EXTERNAL ANALOG", 19, NAVY, 700)
    d.text(1002, 280, "Precharge and pulse timing", 17, INK)
    d.text(1002, 316, "Sample/hold and sensing", 17, INK)
    d.text(1002, 352, "ADC conversion", 17, INK)
    d.line(858, 379, 1145, 379, AMBER_EDGE, 2)
    d.text(1002, 413, "No physical wrapper views", 16, MUTED)
    d.text(1002, 442, "for these blocks yet", 16, MUTED)
    d.arrow(784, 337, 836, 337, AMBER_EDGE)
    d.rect(35, 610, 1127, 64, WHITE, "#d5dfe9")
    d.text(598, 637, "Pins: 8 bitline + 8 wordline + 32 weight + VGND + VSUBS = 50", 17, NAVY, 700)
    d.text(598, 660, "Ternary value is applied on weight-control rails; this passive cell contains no SRAM latch.", 15, MUTED)
    return d


def phase_protocol() -> Drawing:
    d = Drawing(1200, 590, "2+2 row-pair read protocol",
                "Logical sequence checked in RTL; analog aperture, ADC conversion and PVT still need physical evidence")
    segments = [
        ("Precharge A", "external", AMBER, AMBER_EDGE),
        ("Pulse A", "rows 0-1", TEAL, TEAL_EDGE),
        ("Sample / ADC A", "external", AMBER, AMBER_EDGE),
        ("Precharge B", "external", AMBER, AMBER_EDGE),
        ("Pulse B", "rows 2-3", TEAL, TEAL_EDGE),
        ("Sample / ADC B", "external", AMBER, AMBER_EDGE),
    ]
    x0, w, gap = 33, 173, 22
    for i, (title, sub, fill, edge) in enumerate(segments):
        x = x0 + i * (w + gap)
        d.rect(x, 180, w, 105, fill, edge)
        d.text(x + w / 2, 221, title, 17, NAVY, 700)
        d.text(x + w / 2, 252, sub, 15, MUTED)
        if i < len(segments) - 1:
            d.arrow(x + w + 2, 232, x + w + gap - 3, 232)
    d.text(33, 343, "phase_b", 17, NAVY, 700, "start")
    d.line(145, 338, 618, 338, BLUE_EDGE, 4)
    d.line(618, 338, 618, 313, BLUE_EDGE, 4)
    d.line(618, 313, 1161, 313, BLUE_EDGE, 4)
    d.text(363, 376, "A: row pair 0/1", 17, INK)
    d.text(884, 376, "B: row pair 2/3", 17, INK)
    d.rect(175, 425, 850, 100, BLUE, BLUE_EDGE)
    d.text(600, 463, "Digital accumulation after both partial ADC results", 20, NAVY, 700)
    d.text(600, 498, "s[c] = sA[c] + sB[c]", 23, BLUE_EDGE, 700)
    return d


def top_boundary() -> Drawing:
    d = Drawing(1200, 675, "Implemented core-bound top and its analog boundary",
                "RTL and passive-core GDS are in the routed top; orange functions terminate at top-level ports")
    d.rect(145, 145, 750, 433, WHITE, BLUE_EDGE, 3)
    d.text(178, 175, "ON-CHIP CORE-BOUND GDS", 17, BLUE_EDGE, 700, "start")
    d.card(178, 215, 305, 260, "2+2 digital controller",
           ["weight registers", "phase / ADC handshake", "signed partial accumulator", "result ready / valid"], BLUE, BLUE_EDGE)
    d.card(565, 215, 295, 260, "Passive CIM core 4x4",
           ["16 ternary cells", "WPOS / WNEG weight pins", "WLP / WLN pulse pins", "BLP / BLN analog pairs"], TEAL, TEAL_EDGE)
    d.card(930, 215, 235, 260, "External analog",
           ["phase pulse engine", "precharge + S/H", "sense / ADC", "not in GDS"], AMBER, AMBER_EDGE)
    d.arrow(485, 300, 557, 300, BLUE_EDGE)
    d.text(521, 286, "WPOS/NEG", 13, BLUE_EDGE, 700)
    d.arrow(862, 344, 923, 344, TEAL_EDGE)
    d.text(895, 331, "BLP/N", 13, TEAL_EDGE, 700)
    d.arrow(925, 402, 864, 402, AMBER_EDGE)
    d.text(895, 432, "WLP/N", 13, AMBER_EDGE, 700)
    d.line(952, 483, 952, 526, AMBER_EDGE, 3)
    d.line(952, 526, 323, 526, AMBER_EDGE, 3)
    d.arrow(323, 526, 323, 480, AMBER_EDGE)
    d.text(640, 516, "ADC partials / phase_done", 15, AMBER_EDGE, 700)
    d.rect(32, 253, 93, 180, GREY, GREY_EDGE)
    d.text(78, 294, "Host", 17, NAVY, 700)
    d.text(78, 324, "config", 15, INK)
    d.text(78, 354, "input", 15, INK)
    d.text(78, 384, "result", 15, INK)
    d.arrow(128, 342, 169, 342, NAVY)
    d.text(600, 625, "OpenLane top LVS checks macro connectivity through LEF; composite device LVS is outstanding.", 16, MUTED)
    return d


def evidence() -> Drawing:
    d = Drawing(1200, 570, "Evidence boundary for the rendered GDS",
                "A layout image is one artifact in the chain, not proof that the complete analog wrapper is ready")
    d.card(47, 165, 336, 250, "Passive 4x4 macro",
           ["GDS / LEF / extracted SPICE", "core DRC + Netgen LVS", "post-layout diagnostics", "recorded Stage-5 receipts"], TEAL, TEAL_EDGE)
    d.card(432, 165, 336, 250, "Core-bound top",
           ["digital control + passive core", "routed GDS + PNG", "top DRC + LEF macro LVS", "STA from selected run tag"], BLUE, BLUE_EDGE)
    d.card(817, 165, 336, 250, "Clocked mixed-signal top",
           ["on-chip analog front end", "wrapper GDS / LEF / LIB / SPEF", "device LVS / PEX + ADC PVT", "physical sign-off pending"], AMBER, AMBER_EDGE)
    d.arrow(388, 290, 427, 290, NAVY)
    d.arrow(773, 290, 812, 290, NAVY)
    d.rect(47, 460, 1106, 64, WHITE, "#d5dfe9")
    d.text(600, 491, "The actual GDS render and current timing metrics are generated by notebook cells 5.1f-5.1g.", 17, NAVY, 700)
    return d


FIGURES = {
    "automx_workflow": workflow,
    "automx_compute_boundary": computing_boundary,
    "automx_core_array": core_array,
    "automx_2p2_protocol": phase_protocol,
    "automx_core_bound_top": top_boundary,
    "automx_evidence_boundary": evidence,
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    for name, build in FIGURES.items():
        path = args.root / OUT / f"{name}.svg"
        build().save(path)
        print(path)


if __name__ == "__main__":
    main()
