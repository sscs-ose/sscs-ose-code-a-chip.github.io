#!/usr/bin/env python3
"""Run a public TT FCT bench and print gain, SFDR, hold movement, and total power."""

import argparse
import cmath
import math
import re
import subprocess
from pathlib import Path


HERE = Path(__file__).resolve().parent
DEFAULT_DECK = "tb_dynamic_tt.spi"
DEFAULT_COUNT = 32
DEFAULT_TONE = 5
DEFAULT_INPUT_PEAK_V = 10e-3
MEASURE = re.compile(r"^\s*([a-z]\w*)\s*=\s*([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[-+]?\d+)?)", re.I)


parser = argparse.ArgumentParser()
parser.add_argument("--deck", default=DEFAULT_DECK, help="public deck under /app/testbench")
parser.add_argument("--tone-bin", type=int, default=DEFAULT_TONE)
parser.add_argument("--input-peak-v", type=float, default=DEFAULT_INPUT_PEAK_V)
args = parser.parse_args()

deck = (HERE / args.deck).resolve()
if HERE not in deck.parents:
    raise SystemExit("--deck must be a file under /app/testbench")
if args.tone_bin < 1 or args.tone_bin >= DEFAULT_COUNT // 2:
    raise SystemExit("--tone-bin must be between 1 and 15 for 32 samples")
if args.input_peak_v <= 0:
    raise SystemExit("--input-peak-v must be positive")

result = subprocess.run(
    ["ngspice", "-b", deck],
    cwd=HERE,
    text=True,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
)

COUNT = DEFAULT_COUNT
values = {}
for line in result.stdout.splitlines():
    if match := MEASURE.match(line):
        value = float(match.group(2))
        if math.isfinite(value):
            values[match.group(1).lower()] = value

required = [
    f"out{side}{suffix}_{index:03d}"
    for index in range(COUNT)
    for suffix in ("", "_early")
    for side in ("p", "n")
] + ["power_w"]
if result.returncode:
    raise SystemExit(f"ngspice exited {result.returncode} while running {deck.name}:\n{result.stdout}")
if any(name not in values for name in required):
    raise SystemExit(f"ngspice did not produce a complete finite sample set:\n{result.stdout}")

outp = [values[f"outp_{index:03d}"] for index in range(COUNT)]
outn = [values[f"outn_{index:03d}"] for index in range(COUNT)]
outp_early = [values[f"outp_early_{index:03d}"] for index in range(COUNT)]
outn_early = [values[f"outn_early_{index:03d}"] for index in range(COUNT)]
differential = [p - n for p, n in zip(outp, outn)]
differential_track = [p - n for p, n in zip(outp_early, outn_early)]
common_mode = [(p + n) / 2 for p, n in zip(outp, outn)]
mean = sum(differential) / COUNT
spectrum = [
    sum((value - mean) * cmath.exp(-2j * math.pi * k * n / COUNT) for n, value in enumerate(differential))
    for k in range(COUNT // 2 + 1)
]
fundamental = abs(spectrum[args.tone_bin])
spur = max(abs(value) for index, value in enumerate(spectrum[1:], 1) if index != args.tone_bin)
gain = 2 * fundamental / COUNT / args.input_peak_v
sfdr = 20 * math.log10(max(fundamental, 1e-30) / max(spur, 1e-30))
hold_movement = math.sqrt(
    sum((track - held) ** 2 for track, held in zip(differential_track, differential))
    / max(sum(held ** 2 for held in differential), 1e-30)
)
print(f"sampled_gain_vv = {gain:.6g}")
print(f"sfdr_db = {sfdr:.6g}")
print(f"mean_output_common_mode_v = {sum(common_mode)/COUNT:.6g}")
print(f"sampled_output_min_v = {min(outp+outn):.6g}")
print(f"sampled_output_max_v = {max(outp+outn):.6g}")
print(f"hold_transition_movement_ratio = {hold_movement:.6g}")
print(f"power_w = {values['power_w']:.6g}")
