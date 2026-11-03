#!/usr/bin/env python3
"""Collect post-P&R area/timing/power of the fa_lane designs from ORFS reports."""
from __future__ import annotations

import glob
import json
import os
import re

ROOT = os.path.expanduser("~/orfs-src/flow/reports/nangate45/fa_lane_top")
OUT = os.path.expanduser("~/flashattn_expmul/results/phase4/power_compare.json")


def parse(tag: str) -> dict:
    d = os.path.join(ROOT, tag)
    res = {}
    files = glob.glob(os.path.join(d, "*.rpt")) + glob.glob(os.path.join(d, "*.txt"))
    for f in files:
        try:
            txt = open(f, errors="ignore").read()
        except OSError:
            continue
        m = re.search(r"Total\s+([0-9.]+)\s*[eE]?([-+]?\d*)\s*mW", txt)
        if m:
            val = float(m.group(1)) * (10 ** int(m.group(2) or 0))
            res.setdefault("power_mw", val)
        for key, pat in (("area_um2", r"Design area\s+([0-9.]+)\s*um\^2"),
                         ("wns_ns", r"worst slack\s+(-?[0-9.]+)"),
                         ("cells", r"Number of instances:\s+(\d+)")):
            mm = re.search(pat, txt)
            if mm:
                res.setdefault(key, float(mm.group(1)))
    res["files"] = [os.path.basename(f) for f in files]
    return res


def main() -> int:
    out = {}
    for tag in ("base", "exp"):
        out[tag] = parse(tag)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(out, open(OUT, "w"), indent=2)
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
