#!/usr/bin/env python3
"""Robustness sweeps of a sized design: python3 run_sweep.py {pvt|fin|fs|delay|all} --bits 4"""

import argparse
import json
from pathlib import Path

from sargen import SarSpec
from sargen import sweep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=["pvt", "fin", "fs", "delay", "mc", "all"])
    ap.add_argument("--bits", type=int, default=4)
    ap.add_argument("--fs", type=float, default=10e6)
    ap.add_argument("--hits", type=int, default=16)
    ap.add_argument("--fft-n", type=int, default=128)
    a = ap.parse_args()

    base = Path(f"build/{a.bits}bit")
    design = json.loads((base / "design.json").read_text())   # nominal design from run_flow.py
    spec = SarSpec(bits=a.bits, fs=a.fs)
    out = base / "sweeps"
    kw = dict(hits=a.hits, fft_n=a.fft_n)
    if a.what in ("delay", "all"):
        r = sweep.comparator_delay(spec, design, out)
        (out / f"cmp_delay_{a.bits}b.json").write_text(json.dumps(r, indent=1))
        print(f"comparator tau {r['tau'] * 1e12:.1f} ps, delay at LSB/2 {r['delay_half_lsb'] * 1e12:.0f} ps")
    if a.what in ("fin", "all"):
        sweep.fin_sweep(spec, design, out, fft_n=a.fft_n)
    if a.what in ("fs", "all"):
        sweep.fs_sweep(spec, design, out, **kw)
    if a.what in ("pvt", "all"):
        sweep.pvt(spec, design, out, **kw)
    if a.what == "mc":
        s_os = None
        summ = base / "summary.json"
        if summ.exists():
            s_os = json.loads(summ.read_text())["comparator_offset"]["sigma"]
        sweep.spice_mc(spec, design, out, seeds=4, hits=8, sigma_os=s_os)


if __name__ == "__main__":
    main()
