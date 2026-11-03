"""Draws the two structural figures of HSKEM-2 as SVG, from the RTL as it stands (no measured values):
figures/hskem2_datapath.svg (blocks, the 18 SRAM macros and the data buses) and
figures/hskem2_butterfly.svg (one word butterfly at operator level, from rtl/kyber/kyber_ntt_engine_packed2.sv).

usage: python make_arch_figures.py
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
INK, INK2, MUTED, SURF, BOX = "#0b0b0b", "#52514e", "#898781", "#fcfcfb", "#f6f3ee"
NTT, KEC, MEM, CTRL, HOST, KEM, SEC = "#2a78d6", "#eb6834", "#f2cc8f", "#898781", "#486886", "#1d7874", "#7b3f6e"


class Svg:
    def __init__(self, w: int, h: int, title: str, sub: str = ""):
        self.w, self.h, self.e = w, h, []
        self.text(16, 28, title, 19, INK, "bold")
        if sub:
            self.text(16, 49, sub, 12.5, INK2)

    def text(self, x, y, t, size=12, col=INK, weight="normal", anchor="start", style="normal"):
        t = t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        self.e.append(f'<text x="{x}" y="{y}" font-size="{size}" fill="{col}" font-weight="{weight}" '
                      f'font-style="{style}" text-anchor="{anchor}">{t}</text>')

    def box(self, x, y, w, h, title="", sub=(), fill=BOX, stroke=MUTED, sw=1.3, size=12.5, r=5, tc=INK):
        self.e.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')
        lines = 1 + len(sub)
        y0 = y + h / 2 - (lines - 1) * 7.5 + 4
        if title:
            self.text(x + w / 2, y0, title, size, tc, "bold", "middle")
        for i, s in enumerate(sub):
            self.text(x + w / 2, y0 + 15 * (i + 1), s, size - 2, INK2 if tc == INK else tc, "normal", "middle")

    def group(self, x, y, w, h, title, stroke=MUTED):
        self.e.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="7" fill="none" stroke="{stroke}" stroke-width="1.2" stroke-dasharray="6 4"/>')
        self.text(x + 9, y + 16, title, 12, stroke, "bold")

    def wire(self, pts, col=INK2, sw=1.6, arrow=True, dash=False):
        d = " ".join(f"{x},{y}" for x, y in pts)
        self.e.append(f'<polyline points="{d}" fill="none" stroke="{col}" stroke-width="{sw}"' + (' stroke-dasharray="5 4"' if dash else "") + "/>")
        if arrow:
            (x0, y0), (x1, y1) = pts[-2], pts[-1]
            dx, dy = (x1 > x0) - (x1 < x0), (y1 > y0) - (y1 < y0)
            s = 7
            self.e.append(f'<polygon points="{x1},{y1} {x1 - s * dx - s * .55 * dy},{y1 - s * dy - s * .55 * dx} '
                          f'{x1 - s * dx + s * .55 * dy},{y1 - s * dy + s * .55 * dx}" fill="{col}"/>')

    def op(self, x, y, sym, r=15, col=INK2):
        self.e.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{SURF}" stroke="{col}" stroke-width="1.5"/>')
        self.text(x, y + 5, sym, 14, INK, "bold", "middle")

    def mux(self, x, y, h=44, w=16, label=""):
        """A multiplexer: trapezoid, inputs on the left."""
        self.e.append(f'<polygon points="{x},{y} {x + w},{y + 8} {x + w},{y + h - 8} {x},{y + h}" fill="{SURF}" stroke="{INK2}" stroke-width="1.5"/>')
        if label:
            self.text(x + w / 2, y - 5, label, 9.5, INK2, "normal", "middle")

    def reg(self, x, y, h=52, w=13, label=""):
        self.e.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="#e3f4ec" stroke="#1baf7a" stroke-width="1.6"/>')
        if label:
            self.text(x + w / 2, y + h + 13, label, 9.5, "#12805a", "normal", "middle")

    def bits(self, x, y, n):
        self.e.append(f'<line x1="{x - 4}" y1="{y + 5}" x2="{x + 4}" y2="{y - 5}" stroke="{INK2}" stroke-width="1.2"/>')
        self.text(x + 5, y - 6, str(n), 9.5, INK2)

    def save(self, name):
        body = "\n".join(self.e)
        (ROOT / "figures" / name).write_text(
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}" width="{self.w}" height="{self.h}" '
            f'font-family="DejaVu Sans, Helvetica, Arial, sans-serif"><rect width="{self.w}" height="{self.h}" fill="{SURF}"/>\n{body}\n</svg>\n',
            encoding="utf-8")


def sram(s, x, y, name, shape, w=104, h=38):
    s.box(x, y, w, h, name, (shape,), fill=MEM, stroke="#b5833b", size=10.5, r=3)


def datapath():
    s = Svg(1120, 630, "HSKEM-2: blocks, the 18 SRAM macros and the data buses",
            "Every macro is single-port, bits × words. Blue carries coefficient pairs, orange the bytes of the shared sponge.")
    # host side
    s.group(16, 66, 188, 496, "Host interface and policy", HOST)
    s.box(32, 92, 156, 52, "SPI front end", ("framing, CRC-16",))
    s.box(32, 156, 156, 52, "Command bridge", ("opcodes, responses",))
    s.box(32, 220, 156, 66, "HSM policy shell", ("key slots, counters,", "session, lock"))
    s.box(32, 298, 156, 52, "HMAC-SHA-256", ("frames, vault",))
    s.box(32, 362, 156, 52, "SHAKE DRBG", ("coins from the TRNG",))
    s.box(32, 426, 156, 52, "PUF root, key vault", ("device root key",))
    sram(s, 32, 496, "public-key buffer", "24 × 256", w=156, h=46)
    s.wire([(110, 144), (110, 156)], HOST); s.wire([(110, 208), (110, 220)], HOST); s.wire([(110, 286), (110, 298)], HOST)
    # top sequencers
    s.group(222, 66, 882, 148, "Shared engines, requested by one controller at a time", MUTED)
    s.box(240, 94, 330, 106, "Keccak sponge", ("one round per clock, 24 cycles per permutation", "1600-bit state, byte stream in and out, SHA-3 and SHAKE"), stroke=KEC, sw=2.4, fill="#fdf0ea")
    s.box(590, 94, 330, 106, "Packed NTT engine", ("two butterfly lanes, two 16-word register banks", "seven layers fused into two passes"), stroke=NTT, sw=2.4, fill="#eaf2fb")
    sram(s, 948, 128, "NTT pairs", "24 × 128", w=136)
    s.wire([(920, 140), (948, 140)], NTT, 3.2); s.wire([(948, 156), (920, 156)], NTT, 3.2)
    s.text(934, 124, "24", 10, NTT, "bold", "middle")
    # three controllers
    y = 262
    s.group(222, y, 340, 300, "K-PKE and matrix: A, s, e, keys", KEM)
    for i, (n, sh) in enumerate([("matrix even", "12 × 512"), ("matrix odd", "12 × 512"), ("secret even", "12 × 256"), ("secret odd", "12 × 256"),
                                 ("error even", "12 × 256"), ("error odd", "12 × 256"), ("noise bytes", "8 × 768"), ("ek pairs", "24 × 256"), ("dk pairs", "24 × 256")]):
        sram(s, 236 + (i % 3) * 108, y + 150 + (i // 3) * 46, n, sh)
    s.box(236, y + 28, 312, 48, "KeyGen controller", ("SampleNTT, CBD samplers, matrix product",), stroke=KEM)
    s.box(236, y + 84, 312, 48, "Key encode and decode", ("12-bit coefficients to bytes and back",), stroke=KEM)
    s.group(576, y, 300, 300, "Encapsulation", KEM)
    s.box(590, y + 28, 272, 48, "Encrypt controller", ("noise streams into the NTT, u and v",), stroke=KEM)
    s.box(590, y + 84, 272, 48, "Ciphertext codec", ("compress, encode, decode",), stroke=KEM)
    for i, (n, sh) in enumerate([("noise even", "12 × 640"), ("noise odd", "12 × 640"), ("coefficients", "12 × 768"), ("decoded", "12 × 768"), ("ciphertext", "8 × 768")]):
        sram(s, 590 + (i % 2) * 140, y + 150 + (i // 2) * 46, n, sh, w=132)
    s.group(890, y, 214, 300, "Decapsulation", KEM)
    s.box(904, y + 28, 186, 48, "Decaps controller", ("decrypt, hashes",), stroke=KEM)
    s.box(904, y + 84, 186, 48, "Fused comparison", ("re-encryption vs c",), stroke=KEM)
    sram(s, 930, y + 150, "products", "24 × 128", w=134)
    sram(s, 930, y + 196, "ciphertext ref.", "8 × 768", w=134)
    # buses
    s.wire([(405, 200), (405, 222), (392, 222), (392, 262)], KEC, 2.6); s.wire([(405, 222), (726, 222), (726, 262)], KEC, 2.6); s.wire([(726, 222), (960, 222), (960, 262)], KEC, 2.6)
    s.text(415, 237, "8-bit byte stream", 10.5, KEC, "bold")
    s.wire([(755, 200), (755, 248), (440, 248), (440, 262)], NTT, 3.4); s.wire([(755, 248), (800, 248), (800, 262)], NTT, 3.4); s.wire([(755, 248), (1040, 248), (1040, 262)], NTT, 3.4)
    s.text(545, 243, "24-bit coefficient pairs, one per cycle", 10.5, NTT, "bold")
    s.wire([(204, 280), (222, 280)], HOST, 1.6, dash=True)
    s.wire([(240, 590), (290, 590)], NTT, 3.4); s.text(298, 594, "24-bit pair bus", 11, INK2)
    s.wire([(420, 590), (470, 590)], KEC, 2.6); s.text(478, 594, "8-bit sponge stream", 11, INK2)
    s.wire([(630, 590), (680, 590)], HOST, 1.6, dash=True); s.text(688, 594, "commands", 11, INK2)
    s.box(780, 576, 22, 26, fill=MEM, stroke="#b5833b", r=2); s.text(810, 594, "single-port OpenRAM macro (18 in all)", 11, INK2)
    s.save("hskem2_datapath.svg")


def lane(s, y0, name):
    """One butterfly lane, operator level; wires follow the g_lane block of kyber_ntt_engine_packed2.sv."""
    s.text(120, y0 - 4, name, 12, NTT, "bold")
    ya, yb = y0 + 40, y0 + 150
    # operands
    s.wire([(108, ya), (250, ya)], arrow=False); s.wire([(108, yb), (250, yb)], arrow=False)
    s.text(124, ya - 6, "a", 12, INK, "bold"); s.text(124, yb - 6, "b", 12, INK, "bold")
    s.bits(170, ya, 12); s.bits(170, yb, 12)
    # a + b, a - b with conditional subtraction
    s.wire([(200, ya), (200, ya + 34), (232, ya + 34)], arrow=True); s.wire([(216, yb), (216, ya + 46), (232, ya + 46)], arrow=False)
    s.box(232, ya + 22, 62, 34, "a + b", ("",), size=11, fill=SURF, stroke=INK2)
    s.wire([(216, yb), (216, yb - 24), (232, yb - 24)], arrow=True)
    s.box(232, yb - 42, 62, 34, "b − a", ("",), size=11, fill=SURF, stroke=INK2)
    s.wire([(200, ya + 34), (200, yb - 16), (232, yb - 16)], arrow=False)
    s.box(306, ya + 22, 54, 34, "− q", ("if ≥ q",), size=10, fill=SURF, stroke=INK2); s.wire([(294, ya + 39), (306, ya + 39)], arrow=True)
    s.box(306, yb - 42, 54, 34, "− q", ("if ≥ q",), size=10, fill=SURF, stroke=INK2); s.wire([(294, yb - 25), (306, yb - 25)], arrow=True)
    # x mux and multiplicand mux
    s.mux(392, ya - 12, 62, label="x"); s.wire([(250, ya), (392, ya)], arrow=True); s.wire([(360, ya + 39), (376, ya + 39), (376, ya + 30), (392, ya + 30)], arrow=True)
    s.mux(392, yb - 40, 72, label="m"); s.wire([(360, yb - 25), (392, yb - 25)], arrow=True); s.wire([(250, yb), (392, yb)], arrow=True)
    s.wire([(180, ya), (180, yb + 34), (384, yb + 34), (384, yb + 22), (392, yb + 22)], arrow=False, sw=1.2)
    # multiplier with the twiddle
    s.op(452, yb - 4, "×"); s.wire([(408, yb - 4), (437, yb - 4)], arrow=True)
    s.wire([(452, yb + 56), (452, yb + 11)], arrow=True); s.bits(452, yb + 40, 12); s.text(460, yb + 54, "ζ", 12, INK, "bold")
    # stage 1 registers
    s.reg(492, ya - 26, label="x₁"); s.wire([(408, ya + 19), (480, ya + 19), (480, ya), (492, ya)], arrow=True)
    s.reg(492, yb - 30, label="p"); s.wire([(467, yb - 4), (492, yb - 4)], arrow=True); s.bits(478, yb - 4, 24)
    # Barrett
    s.box(524, yb - 30, 66, 52, "× 5039", (">> 24",), size=11, fill="#fdeeee", stroke="#d03b3b"); s.wire([(505, yb - 4), (524, yb - 4)], arrow=True)
    s.box(602, yb - 30, 56, 52, "× q", ("t · q",), size=11, fill="#fdeeee", stroke="#d03b3b"); s.wire([(590, yb - 4), (602, yb - 4)], arrow=True)
    s.op(690, yb - 4, "−", col="#d03b3b"); s.wire([(658, yb - 4), (675, yb - 4)], arrow=True)
    s.wire([(515, yb - 4), (515, yb + 34), (690, yb + 34), (690, yb + 11)], arrow=True, sw=1.2)
    s.box(718, yb - 26, 56, 44, "− q", ("if ≥ q",), size=10, fill="#e3f4ec", stroke="#1baf7a"); s.wire([(705, yb - 4), (718, yb - 4)], arrow=True)
    s.text(746, yb + 32, "one subtraction", 9.5, "#12805a", "normal", "middle")
    # stage 2 registers
    s.reg(804, ya - 26, label="x₂"); s.wire([(505, ya), (804, ya)], arrow=True)
    s.reg(804, yb - 30, label="r"); s.wire([(774, yb - 4), (804, yb - 4)], arrow=True)
    # output add, subtract
    s.box(846, ya + 8, 66, 34, "x + r", ("",), size=11, fill=SURF, stroke=INK2)
    s.box(846, ya + 62, 66, 34, "x − r", ("",), size=11, fill=SURF, stroke=INK2)
    s.wire([(817, ya), (832, ya), (832, ya + 25), (846, ya + 25)], arrow=True); s.wire([(832, ya + 25), (832, ya + 79), (846, ya + 79)], arrow=True)
    s.wire([(817, yb - 4), (838, yb - 4), (838, ya + 87), (846, ya + 87)], arrow=True); s.wire([(838, ya + 87), (838, ya + 33), (846, ya + 33)], arrow=True)
    s.mux(944, ya - 8, 62, label="lo"); s.mux(944, yb - 44, 62, label="hi")
    s.wire([(832, ya), (936, ya), (936, ya + 8), (944, ya + 8)], arrow=True)        # inverse: lo takes x
    s.wire([(928, ya + 42), (944, ya + 42)], arrow=True); s.text(924, ya + 46, "r", 10.5, INK, "bold", "end")     # scaling step: lo takes r
    s.wire([(838, yb - 4), (838, yb + 8), (944, yb + 8)], arrow=True)                # inverse: hi takes r
    s.wire([(912, ya + 25), (944, ya + 25)], arrow=True); s.wire([(912, ya + 79), (928, ya + 79), (928, yb - 18), (944, yb - 18)], arrow=True)
    s.wire([(960, ya + 23), (1008, ya + 23)]); s.wire([(960, yb - 13), (1008, yb - 13)])
    s.text(1014, ya + 27, "a′", 12, INK, "bold"); s.text(1014, yb - 9, "b′", 12, INK, "bold")


def butterfly():
    s = Svg(1060, 590, "One butterfly lane of HSKEM-2, operator by operator",
            "Two identical lanes share one ζ, one per half of a word pair. Forward: a′ = a + ζb, b′ = a − ζb. Inverse: a′ = a + b, b′ = ζ(b − a).")
    s.box(16, 104, 92, 130, "Two banks", ("16 words,", "2 × 12 bit,", "ping-pong"), size=11, stroke=NTT, fill="#eaf2fb")
    s.box(16, 262, 92, 62, "SRAM", ("24 × 128,", "one port"), fill=MEM, stroke="#b5833b", size=11.5)
    s.wire([(62, 262), (62, 234)], NTT, 3); s.bits(62, 250, 24)
    s.box(16, 348, 92, 56, "ζ ROM", ("128 values",), size=11)
    lane(s, 84, "One of two lanes: the other takes the odd coefficient of each word")
    s.mux(372, 362, 44)
    s.wire([(108, 372), (372, 372)], arrow=True); s.wire([(300, 394), (372, 394)], arrow=True)
    s.wire([(388, 384), (452, 384), (452, 290)], arrow=False, sw=1.2)
    s.text(296, 398, "3303, 1652 (scaling)", 9.5, INK2, "normal", "end")
    y = 448
    s.reg(36, y, 34); s.text(58, y + 22, "pipeline register, three stages per butterfly", 11, INK2)
    s.box(36, y + 48, 16, 18, fill="#fdeeee", stroke="#d03b3b", r=1); s.text(58, y + 62, "Barrett reduction, a mod q for every 24-bit product", 11, INK2)
    s.mux(420, y, 34); s.text(444, y + 22, "selected by direction and by the scaling step", 11, INK2)
    s.box(420, y + 48, 16, 18, fill="#e3f4ec", stroke="#1baf7a", r=1); s.text(444, y + 62, "one conditional subtraction, proven for all 2²⁴ inputs (Section 4)", 11, INK2)
    s.text(36, y + 104, "From rtl/kyber/kyber_ntt_engine_packed2.sv and barrett_reduce_1c.v. Both lanes use the same bank words, so they need no extra SRAM port. 3303 and 1652 fold the scaling by 128⁻¹ into the last layer.", 11, MUTED)
    s.save("hskem2_butterfly.svg")


if __name__ == "__main__":
    datapath()
    butterfly()
