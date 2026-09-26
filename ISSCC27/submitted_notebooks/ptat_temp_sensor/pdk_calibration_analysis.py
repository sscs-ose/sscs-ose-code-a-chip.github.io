#!/usr/bin/env python3
"""Calibration post-processing of retained SKY130 run-221 CSV evidence.

This script performs no new transistor simulation. Reported errors are evaluated
only at the retained temperature samples.
"""
from __future__ import annotations
import argparse, csv, itertools, json, math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TEMPS = [-40.0, -20.0, 0.0, 25.0, 50.0, 75.0, 100.0, 125.0]
MODES = ("ideal", "mirror")
CORNERS = ("tt", "ff", "ss")
DEFAULT_OUT = ROOT / "results" / "pdk_calibration_analysis.json"

def read_xy(path: Path) -> tuple[list[float], list[float]]:
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f, skipinitialspace=True))
    t = [float(r["temp_c"]) for r in rows]
    v = [float(r["dvgs_v"]) for r in rows]
    if t != TEMPS or not all(math.isfinite(x) for x in t + v):
        raise ValueError(f"{path}: unexpected/non-finite data")
    return t, v

def rms(values: list[float]) -> float:
    return math.sqrt(sum(v*v for v in values)/len(values))

def two_point_errors(t: list[float], v: list[float]) -> list[float]:
    gain = (t[-1]-t[0])/(v[-1]-v[0])
    offset = t[0] - gain*v[0]
    return [gain*x + offset - y for x, y in zip(v, t)]

def pwl_errors(t: list[float], v: list[float], anchors: tuple[float, ...]) -> list[float]:
    idx = [t.index(a) for a in anchors]
    est = [math.nan]*len(t)
    for ia, ib in zip(idx[:-1], idx[1:]):
        gain = (t[ib]-t[ia])/(v[ib]-v[ia])
        offset = t[ia] - gain*v[ia]
        for j in range(ia, ib+1):
            est[j] = gain*v[j] + offset
    if not all(math.isfinite(x) for x in est):
        raise ValueError("PWL estimate left uncovered samples")
    return [a-b for a,b in zip(est,t)]

def metrics(errors: list[float]) -> dict[str, float]:
    return {
        "max_abs_error_c": max(abs(x) for x in errors),
        "rms_error_c": rms(errors),
    }

def analyze() -> dict:
    datasets = {}
    for mode in MODES:
        for corner in CORNERS:
            t, v = read_xy(ROOT/"results"/"sky130_ci"/f"ptat_{mode}_{corner}.csv")
            datasets[f"{mode}_{corner}"] = (t, v)

    two = {}
    for name, (t, v) in datasets.items():
        two[name] = metrics(two_point_errors(t, v))

    candidates = []
    for middle in itertools.combinations(TEMPS[1:-1], 3):
        anchors = (TEMPS[0], *middle, TEMPS[-1])
        per = {}
        worst_max = 0.0
        worst_rms = 0.0
        for name, (t, v) in datasets.items():
            m = metrics(pwl_errors(t, v, anchors))
            per[name] = m
            worst_max = max(worst_max, m["max_abs_error_c"])
            worst_rms = max(worst_rms, m["rms_error_c"])
        candidates.append((worst_max, worst_rms, anchors, per))
    worst_max, worst_rms, anchors, per = min(
        candidates, key=lambda x: (x[0], x[1], x[2])
    )

    return {
        "status": "PASS",
        "evidence_source": "retained SKY130/open_pdks ngspice CI run-221 CSVs",
        "evidence_boundary": (
            "Digital calibration post-processing only. Errors are evaluated at the "
            "eight retained temperature samples; no claim is made for silicon, "
            "statistical PDK mismatch, layout, or unsampled temperatures."
        ),
        "temperature_samples_c": TEMPS,
        "two_point_endpoint_calibration": {
            "anchors_c": [TEMPS[0], TEMPS[-1]],
            "per_dataset": two,
            "worst_max_abs_error_c": max(v["max_abs_error_c"] for v in two.values()),
            "worst_rms_error_c": max(v["rms_error_c"] for v in two.values()),
        },
        "five_point_pwl_grid_calibration": {
            "selection": (
                "Exhaustive choice of three interior anchors with -40 C and 125 C "
                "fixed; objective is minimum worst-case absolute error across all "
                "retained ideal/mirror TT/FF/SS datasets at retained samples."
            ),
            "anchors_c": list(anchors),
            "per_dataset": per,
            "worst_max_abs_error_c": worst_max,
            "worst_rms_error_c": worst_rms,
        },
    }

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    result = analyze()
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.check:
        if not args.output.is_file():
            print(f"CALIBRATION ANALYSIS: FAIL\nmissing {args.output}")
            return 1
        if args.output.read_text(encoding="utf-8") != rendered:
            print("CALIBRATION ANALYSIS: FAIL\nretained result is stale")
            return 1
        print("CALIBRATION ANALYSIS: PASS")
        print("best 5-point anchors:",
              result["five_point_pwl_grid_calibration"]["anchors_c"])
        print("worst sampled-point error:",
              result["five_point_pwl_grid_calibration"]["worst_max_abs_error_c"])
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print(f"wrote {args.output}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
