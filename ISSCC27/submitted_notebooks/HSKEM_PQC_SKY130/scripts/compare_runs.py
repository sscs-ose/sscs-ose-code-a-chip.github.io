"""Compare the final (6_report.json) metrics of two ORFS runs of the same design point.

Used to check that a re-run - for example with the relocated tool bundle of
scripts/make_orfs_bundle.sh, in a clean container or in Colab - reproduces the
committed layout. Warning counters are ignored; every other numeric finish metric
must match exactly.
usage: compare_runs.py <committed run> <re-run> [<label>]   (names under results/asic/)
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]


def report(run: str) -> dict:
    return json.loads(next((ROOT / "results/asic" / run / "logs").rglob("6_report.json")).read_text())


def compare(ref: str, new: str) -> dict:
    a, b = report(ref), report(new)
    keys = [k for k in a if k.startswith("finish__") and isinstance(a[k], (int, float)) and "warnings" not in k]
    diff = {k: [a[k], b.get(k)] for k in keys if a[k] != b.get(k)}
    return {"committed": ref, "rerun": new, "metrics_compared": len(keys), "identical": len(keys) - len(diff),
            "differences": diff}


if __name__ == "__main__":
    res = compare(sys.argv[1], sys.argv[2])
    if len(sys.argv) > 3:
        res["label"] = sys.argv[3]
    print(json.dumps(res, indent=2))
