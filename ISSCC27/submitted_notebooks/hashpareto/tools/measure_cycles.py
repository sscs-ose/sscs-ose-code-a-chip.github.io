#!/usr/bin/env python3
"""A1: measure cycles-per-block for every UNROLL by RTL simulation.

Compiles verif/cycles/tb_cycles.sv against each variant's baked sources with
Icarus, runs two message lengths, and derives steady-state cycles/block from the
slope. Also cross-checks the U1 digest against Python's hashlib.

Outputs data/cycles.csv (and results/cycles.csv for the dev tree).
"""
import csv
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from hashlib import sha256

ROOT = Path(__file__).resolve().parent.parent
UNROLLS = (1, 2, 4, 8, 16)
NBYTES = (640, 3200)   # 11 and 51 blocks (incl. padding) -> 40-block difference


def build_and_run(u, nbytes, workdir):
    vvp = workdir / f"t_u{u}_{nbytes}.vvp"
    srcs = sorted((ROOT / f"flow/variants/u{u}/src").glob("*.sv"))
    cmd = [
        "iverilog", "-g2012", "-o", str(vvp),
        f"-Ptb.U={u}", f"-Ptb.NBYTES={nbytes}",
        str(ROOT / "verif/cycles/tb_cycles.sv"),
        *[str(p) for p in srcs],
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    out = subprocess.run(["vvp", str(vvp)], capture_output=True, text=True).stdout
    m = re.search(r"total_cycles=(\d+)\s+digest=([0-9a-fA-F]+)", out)
    if not m:
        raise RuntimeError(f"no RESULT for U{u} N={nbytes}:\n{out[-500:]}")
    return int(m.group(1)), m.group(2).lower()


def expected_digest(nbytes):
    """Word i = i*0x01010101 + 0x03020100, big-endian bytes, per the testbench."""
    msg = bytearray()
    for i in range(nbytes // 4):
        w = (i * 0x01010101 + 0x03020100) & 0xFFFFFFFF
        msg += w.to_bytes(4, "big")
    return sha256(bytes(msg)).hexdigest()


def main():
    work = Path(os.environ.get("TMPDIR", "/tmp")) / "hashpareto_cycles"
    work.mkdir(parents=True, exist_ok=True)
    rows = []
    for u in UNROLLS:
        cyc = {}
        dig = {}
        for n in NBYTES:
            c, d = build_and_run(u, n, work)
            cyc[n], dig[n] = c, d
        # blocks per message = ceil((nbytes + 8 + 1) / 64) ; 640->11, 3200->51
        blocks = {n: (n + 9 + 63) // 64 for n in NBYTES}
        cpb = (cyc[NBYTES[1]] - cyc[NBYTES[0]]) / (blocks[NBYTES[1]] - blocks[NBYTES[0]])
        rows.append({
            "unroll": u,
            "cycles_per_block": round(cpb, 4),
            "lat_total_cycles_640B": cyc[640],
            "lat_total_cycles_3200B": cyc[3200],
            "lat_cycles_64B": "",
            "digest_640B": dig[640],
        })
        print(f"U{u:2d}: total {cyc[640]}/{cyc[3200]} -> {cpb:.2f} cycles/block")

    # hashlib cross-check (U1, 640 B)
    exp = expected_digest(640)
    got = rows[0]["digest_640B"]
    ok = exp == got
    print(f"hashlib cross-check U1 640B: {'OK' if ok else 'MISMATCH'}")
    print(f"  expected {exp}\n  got      {got}")

    for out in (ROOT / "data/cycles.csv", ROOT / "results/cycles.csv"):
        out.parent.mkdir(parents=True, exist_ok=True)
        cols = list(rows[0].keys())
        with open(out, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            w.writerows(rows)
        print("wrote", out)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
