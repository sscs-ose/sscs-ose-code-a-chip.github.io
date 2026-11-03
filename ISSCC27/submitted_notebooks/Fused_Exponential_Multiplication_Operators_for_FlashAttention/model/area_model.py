#!/usr/bin/env python3
"""Compose the block-level area from the synthesized primitive areas (nangate45).

Measured (Yosys + ABC, NangateOpenCellLibrary_typical, 45 nm):
    fp32_mul 4069.534   fp32_add 1519.658   exp_pwl 4320.904
    rcp_pwl  1668.352   expmul(MODE0) 699.580   expmul(MODE1) 855.988

Block model (paper Fig.1/Fig.2, one query, D lanes):
    dot      : D multipliers + (D-1) adders
    update   : baseline -> 2 exp units (shared) + D*(2 mul + 1 add)
               expmul   -> D*(2 expmul + 1 add)
    divide   : 1 rcp + D multipliers
"""
from __future__ import annotations

import csv
import os

A = dict(mul=4069.534, add=1519.658, exp=4320.904, rcp=1668.352,
         em0=699.580, em1=855.988)


def block(D: int, variant: str) -> dict:
    dot = D * A["mul"] + (D - 1) * A["add"]
    div = A["rcp"] + D * A["mul"]
    if variant == "baseline":
        upd = 2 * A["exp"] + D * (2 * A["mul"] + A["add"])
    else:
        upd = D * (2 * A["em1"] + A["add"])
    return dict(dot=dot, upd=upd, div=div, total=dot + upd + div)


def main() -> int:
    outdir = "results/phase4"
    os.makedirs(outdir, exist_ok=True)
    rows = []
    print(f"{'D':>3} {'variant':10} {'dot':>12} {'update':>12} {'div':>10} {'total':>12} {'saving':>8}")
    for D in (16, 32, 64, 256):
        b = block(D, "baseline")
        e = block(D, "expmul")
        sav = 1 - e["total"] / b["total"]
        for name, m in (("baseline", b), ("expmul", e)):
            rows.append(dict(d=D, variant=name, dot=round(m["dot"], 1),
                             update=round(m["upd"], 1), div=round(m["div"], 1),
                             total=round(m["total"], 1), saving=round(sav, 4)))
            print(f"{D:3d} {name:10} {m['dot']:12.1f} {m['upd']:12.1f} "
                  f"{m['div']:10.1f} {m['total']:12.1f} {sav*100:7.2f}%")
    with open(f"{outdir}/area_model.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"\nprimitive areas: {A}")
    print(f"wrote {outdir}/area_model.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
