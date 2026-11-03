#!/usr/bin/env python3
"""Command-line entry point: python3 run_flow.py --bits 4 [--fs 10e6] ..."""

import argparse

from sargen import SarSpec
from sargen.flow import run_flow


def main():
    ap = argparse.ArgumentParser(description="SKY130 SAR ADC generator flow")
    ap.add_argument("--bits", type=int, default=4)
    ap.add_argument("--fs", type=float, default=10e6, help="sample rate [S/s]")
    ap.add_argument("--vref", type=float, default=1.8)
    ap.add_argument("--corner", default="tt")
    ap.add_argument("--temp", type=float, default=27.0)
    ap.add_argument("--hits", type=int, default=32, help="ramp-test hits per code")
    ap.add_argument("--fft-n", type=int, default=128, help="FFT length (conversions)")
    ap.add_argument("--mc-runs", type=int, default=1000, help="behavioral mismatch MC runs")
    ap.add_argument("--spice-mc-seeds", type=int, default=0, help="extra full-SPICE mismatch ramps")
    ap.add_argument("--out", default=None)
    ap.add_argument("--no-anim", action="store_true")
    ap.add_argument("--force-char", action="store_true", help="re-run PDK characterization")
    a = ap.parse_args()

    spec = SarSpec(bits=a.bits, fs=a.fs, vref=a.vref, corner=a.corner, temp=a.temp)
    res = run_flow(spec, a.out, hits=a.hits, fft_n=a.fft_n, mc_runs=a.mc_runs,
                   spice_mc_seeds=a.spice_mc_seeds, animate=not a.no_anim, force_char=a.force_char)
    d, s = res["dynamic"], res["static"]
    print(f"\nENOB {d['enob']:.2f} bit | SNDR {d['sndr_db']:.2f} dB | DNL {s['dnl_max']:.3f} LSB | "
          f"INL {s['inl_max']:.3f} LSB | P {res['power']['p_total'] * 1e6:.1f} uW")


if __name__ == "__main__":
    main()
