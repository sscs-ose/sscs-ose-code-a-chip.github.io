"""Turns the key frames of render_zoom_frames.py into a smooth clip with a scale bar.
usage: python make_zoom_clip.py <key frame dir> <x_um> <y_um> <out.mp4>
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

N, KW, KH, DIE, END = 16, 2560, 1440, 3351.0, 14.0
W, H, FPS, SEC, HOLD = 1280, 720, 20, 10, 2
kdir, cx, cy, out = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), sys.argv[4]
span = DIE * 1.05


def view(l: float) -> tuple[float, float, float]:
    """Centre and height (µm) of the view at level l; level k equals key frame k."""
    h = span * (END / span) ** (l / (N - 1))
    return cx + (DIE / 2 - cx) * h / span, cy + (DIE / 2 - cy) * h / span, h


try:
    big, small = ImageFont.truetype("DejaVuSans-Bold.ttf", 30), ImageFont.truetype("DejaVuSans.ttf", 20)
except OSError:
    big, small = ImageFont.truetype("arialbd.ttf", 30), ImageFont.truetype("arial.ttf", 20)
keys = [Image.open(f"{kdir}/k{k:02d}.png").convert("RGB") for k in range(N)]
ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                       "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "27", "-movflags", "+faststart", "-an", out], stdin=subprocess.PIPE)
n = (SEC + HOLD) * FPS
for i in range(n):
    u = min(i / (SEC * FPS), 1.0)
    l = (N - 1) * (u * u * (3 - 2 * u))                # eased
    k = min(int(l), N - 2) if l < N - 1 else N - 1
    kx, ky, kh = view(k)
    vx, vy, vh = view(l)
    upp = kh / KH                                      # µm per key-frame pixel
    bw, bh = vh * W / H / upp, vh / upp
    x0 = KW / 2 + (vx - kx) / upp - bw / 2
    y0 = KH / 2 - (vy - ky) / upp - bh / 2
    im = keys[k].crop((round(x0), round(y0), round(x0 + bw), round(y0 + bh))).resize((W, H), Image.BILINEAR)
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, W, 66), fill=(16, 16, 20))
    d.text((24, 15), "From the whole die to the wiring of the NTT engine", font=big, fill="white")
    bar = next(b for b in (1000, 500, 200, 100, 50, 20, 10, 5, 2, 1) if b / vh * H < 260)
    px = bar / vh * H
    d.rectangle((W - 40 - px, H - 46, W - 40, H - 40), fill="white", outline="black")
    d.text((W - 40 - px, H - 74), f"{bar} µm", font=small, fill="white", stroke_width=2, stroke_fill="black")
    d.text((24, H - 40), "signed-off layout of HSKEM-2, SKY130 (not fabricated)", font=small, fill="white", stroke_width=2, stroke_fill="black")
    ff.stdin.write(im.tobytes())
ff.stdin.close(); ff.wait()
