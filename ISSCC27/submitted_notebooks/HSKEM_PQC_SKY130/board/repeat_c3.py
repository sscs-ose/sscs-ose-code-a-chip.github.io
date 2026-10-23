"""Repeat the C3 two-role ML-KEM flow on the DE25-Nano and tabulate the
FPGA cycle counters and host-side latencies.

usage: python repeat_c3.py COM3 N out.csv raw.log
Cycle counters are 16-bit and saturate at 65535; saturated values are kept
as-is and flagged, never extrapolated.

SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import csv
import re
import sys
import time

import serial

from esp32_console import read_until_quiet

PHASES = ("KEYGEN", "ENCAPS", "CIPHERTEXT_FINAL", "DECAPS")


def main() -> None:
    port, n, out_csv, raw_log = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4]
    rows = []
    with serial.Serial(port, 115200, timeout=0.1) as ser, open(raw_log, "a", encoding="utf-8") as raw:
        for i in range(n):
            ser.reset_input_buffer()
            t0 = time.perf_counter()
            ser.write(b"c3\n")
            out = read_until_quiet(ser, 4.0, 120.0)
            wall = time.perf_counter() - t0 - 4.0
            raw.write(f"### run {i} host_wall_s={wall:.3f}\n{out}\n")
            raw.flush()
            row = {"run": i, "host_wall_s": round(wall, 3),
                   "result_pass": int("C3_TWO_ROLE_RESULT: PASS" in out)}
            for ph in PHASES:
                m = re.search(rf"C3_{ph}: (PASS|FAIL) .*?cycles=(\d+)", out)
                row[f"{ph.lower()}_pass"] = int(bool(m) and m[1] == "PASS")
                row[f"{ph.lower()}_cycles"] = int(m[2]) if m else None
            m = re.search(r"C3_TWO_ROLE latency=(\d+) us", out)
            row["esp32_latency_us"] = int(m[1]) if m else None
            rows.append(row)
            print(i, row["result_pass"], row["keygen_cycles"], row["encaps_cycles"],
                  row["decaps_cycles"], row["esp32_latency_us"], flush=True)
    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main()
