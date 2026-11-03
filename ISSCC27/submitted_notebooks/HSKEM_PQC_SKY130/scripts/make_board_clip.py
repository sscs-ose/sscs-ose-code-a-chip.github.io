"""The closing part of the tour video: the board photograph and the board runs, read from results/fpga/c3_repeat.csv.
usage: python make_board_clip.py <tour in.mp4> <tour out.mp4>     (needs ffmpeg; appends six seconds)
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import csv
import pathlib
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = pathlib.Path(__file__).resolve().parents[1]
W, H, FPS, SEC = 1280, 720, 20, 6
PW, PH = 700, 494                                      # the photograph on screen, in pixels
tour_in, tour_out = sys.argv[1], sys.argv[2]

with open(ROOT / "results/fpga/c3_repeat.csv", newline="") as f:
    runs = list(csv.DictReader(f))
passed = sum(r["result_pass"].strip().lower() in ("true", "1") for r in runs)
assert passed == len(runs) == 100

last = subprocess.run(["ffmpeg", "-v", "error", "-sseof", "-0.2", "-i", tour_in, "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                      stdout=subprocess.PIPE, check=True).stdout
BG = tuple(last[3 * (W * 20 + 20):3 * (W * 20 + 20) + 3])  # the background of the part before
INK, INK_2 = (28, 28, 30), (90, 90, 88)


def font(bold: bool, size: int) -> ImageFont.FreeTypeFont:
    for name in (("DejaVuSans-Bold.ttf", "arialbd.ttf") if bold else ("DejaVuSans.ttf", "arial.ttf")):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    raise OSError("no font")


photo = Image.open(ROOT / "results/fpga/board_setup.jpg").convert("RGB")
pw, ph = photo.size
base = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(base)
d.text((38, 40), "The same design on a real board", font=font(True, 30), fill=INK)
d.text((38, 88), "an Altera Agilex 5 FPGA, with an ESP32 as the untrusted host", font=font(False, 20), fill=INK_2)
x = 38 + PW + 44
d.text((x, 170), f"{passed} of {len(runs)}", font=font(True, 54), fill=INK)
d.text((x, 240), "complete ML-KEM exchanges\npassed on the board", font=font(False, 22), fill=INK_2, spacing=6)
d.text((x, 350), "50 MHz", font=font(True, 54), fill=INK)
d.text((x, 420), "driven over SPI by the ESP32", font=font(False, 22), fill=INK_2)
d.text((38, H - 40), "One FPGA plays both parties in turn, so this is not a test between two boards.", font=font(False, 18), fill=INK_2)

clip = pathlib.Path(tour_out).with_suffix(".board.mp4")
ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                       "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-an", str(clip)], stdin=subprocess.PIPE)
for i in range(SEC * FPS):
    s = 1 - 0.1 * i / (SEC * FPS - 1)                  # a slow push in
    cw, ch = pw * s, ph * s
    x0, y0 = (pw - cw) * 0.5, (ph - ch) * 0.45
    im = base.copy()
    im.paste(photo.crop((round(x0), round(y0), round(x0 + cw), round(y0 + ch))).resize((PW, PH), Image.BILINEAR), (38, 136))
    ff.stdin.write(im.tobytes())
ff.stdin.close(); ff.wait()
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", tour_in, "-i", str(clip), "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0[v]", "-map", "[v]",
                "-r", str(FPS), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "25", "-movflags", "+faststart", "-an", tour_out], check=True)
clip.unlink()
