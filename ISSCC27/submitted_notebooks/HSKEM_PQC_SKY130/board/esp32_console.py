"""Minimal logging console for the HSKEM ESP32 host (115200 8N1).

usage: python esp32_console.py COM3 [--boot-wait 8] [--log file] [cmd ...]
Each command is sent as one line; output is captured until the port has been
quiet for --quiet seconds (or --timeout). Everything is appended to --log with
host timestamps so a session can be audited later.

SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import argparse
import datetime as dt
import sys
import time

import serial  # pyserial


def read_until_quiet(ser: serial.Serial, quiet: float, timeout: float) -> str:
    buf, last, start = bytearray(), time.monotonic(), time.monotonic()
    while True:
        n = ser.in_waiting
        if n:
            buf += ser.read(n)
            last = time.monotonic()
        elif time.monotonic() - last > quiet or time.monotonic() - start > timeout:
            return buf.decode("utf-8", "replace")
        else:
            time.sleep(0.01)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("port")
    ap.add_argument("cmds", nargs="*")
    ap.add_argument("--boot-wait", type=float, default=0.0, help="seconds to capture boot banner")
    ap.add_argument("--quiet", type=float, default=1.5)
    ap.add_argument("--timeout", type=float, default=120.0)
    ap.add_argument("--log", default=None)
    a = ap.parse_args()

    log = open(a.log, "a", encoding="utf-8") if a.log else None

    def emit(tag: str, text: str) -> None:
        stamp = dt.datetime.now().isoformat(timespec="milliseconds")
        block = f"### {stamp} {tag}\n{text}\n"
        sys.stdout.write(block)
        if log:
            log.write(block)
            log.flush()

    with serial.Serial(a.port, 115200, timeout=0.1) as ser:
        if a.boot_wait:
            emit("BOOT", read_until_quiet(ser, a.boot_wait, a.boot_wait + 30))
        for c in a.cmds:
            ser.reset_input_buffer()
            t0 = time.perf_counter()
            ser.write((c + "\n").encode())
            out = read_until_quiet(ser, a.quiet, a.timeout)
            emit(f"CMD {c!r} host_elapsed_s={time.perf_counter() - t0 - a.quiet:.3f}", out)


if __name__ == "__main__":
    main()
