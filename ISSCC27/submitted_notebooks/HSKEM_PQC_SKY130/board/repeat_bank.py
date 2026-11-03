"""Repeat the complete bank attack/defense scenario ("bank run") N times.

Each run: fresh ML-KEM session, authentic withdrawal, 1-bit amount tamper
(must be AUTH_FAILED), replay (must be REPLAY_DETECTED), zeroize, resend
(must be AUTH_REQUIRED). One CSV row per run with every scenario marker.

usage: python repeat_bank.py COM3 N out.csv raw.log
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import csv
import re
import sys
import time

import serial

from esp32_console import read_until_quiet

MARKERS = ("BANK_SESSION_RESULT", "BANK_TX_PREPARED", "BANK_TAMPER_RESULT", "BANK_WITHDRAW_RESULT",
           "BANK_REPLAY_RESULT", "BANK_ZEROIZE_RESULT", "BANK_POST_ZEROIZE_RESULT", "BANK_DEMO_RESULT")


def main() -> None:
    port, n, out_csv, raw_log = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4]
    rows = []
    with serial.Serial(port, 115200, timeout=0.1) as ser, open(raw_log, "a", encoding="utf-8") as raw:
        for i in range(n):
            ser.reset_input_buffer()
            t0 = time.perf_counter()
            ser.write(b"bank run\n")
            out = read_until_quiet(ser, 6.0, 300.0)
            raw.write(f"### run {i}\n{out}\n")
            raw.flush()
            row = {"run": i, "host_wall_s": round(time.perf_counter() - t0 - 6.0, 3)}
            for mk in MARKERS:
                m = re.search(rf"{mk}: (PASS|FAIL)", out)
                row[mk.lower()] = m[1] if m else "MISSING"
            dd = re.search(r"duplicate_debit=(\d+)", out)
            row["duplicate_debit"] = int(dd[1]) if dd else None
            row["any_fail_text"] = int(bool(re.search(r"\bFAIL\b|failed|MISO_STUCK", out)))
            rows.append(row)
            print(i, row["bank_demo_result"], row["duplicate_debit"], row["any_fail_text"], flush=True)
    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main()
