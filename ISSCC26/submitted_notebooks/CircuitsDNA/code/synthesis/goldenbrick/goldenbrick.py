#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
goldenbrick.py
Generate full truth table for N-bit multiplier (signed or unsigned).
Usage:
  python goldenbrick.py --width 8 --signed
  python goldenbrick.py --width 8 # unsigned
"""

import argparse

def to_bits(value: int, width: int) -> str:
    mask = (1 << width) - 1
    return f"{value & mask:0{width}b}"

def clamp_signed(value: int, width: int) -> int:
    mask = (1 << width) - 1
    v = value & mask
    sign_bit = 1 << (width - 1)
    return v - (1 << width) if (v & sign_bit) else v

def main():
    parser = argparse.ArgumentParser(description="Generate truth table for N-bit multiplier.")
    parser.add_argument("--width", type=int, default=8, help="Operand bit width (default 8).")
    parser.add_argument("--signed", action="store_true", help="Use two's complement signed interpretation.")
    args = parser.parse_args()

    N = args.width
    OUTW = N * 2

    if args.signed:
        A_range = range(- (1 << (N - 1)), (1 << (N - 1)))
        B_range = range(- (1 << (N - 1)), (1 << (N - 1)))
    else:
        A_range = range(0, 1 << N)
        B_range = range(0, 1 << N)

    for a in A_range:
        for b in B_range:
            if args.signed:
                prod = clamp_signed(a * b, OUTW)
            else:
                prod = (a * b) & ((1 << OUTW) - 1)
            a_bits = to_bits(a, N)
            b_bits = to_bits(b, N)
            r_bits = to_bits(prod, OUTW)
            print(f"A = {a_bits} B = {b_bits} RESULT = {r_bits}")

if __name__ == "__main__":
    main()
