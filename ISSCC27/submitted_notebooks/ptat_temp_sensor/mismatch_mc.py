#!/usr/bin/env python3
"""Real SKY130 local-mismatch Monte Carlo for the mirror-biased PTAT core.

Uses the PDK's tt_mm library section and one ngspice process per mismatch sample.
The .option seed is parsed before the PDK model library, so each process has a
deterministic local-mismatch realization that remains fixed during its
temperature sweep.

The runner supports explicit calibration anchors and geometry scaling. Geometry
scales multiply W and L together, preserving W/L and the 8x sensor width ratio
while increasing device area for statistically stronger mismatch candidates.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from statistics import mean, pstdev

import run_sky130

ROOT = Path(__file__).resolve().parent
RELEASE = json.loads(
    (ROOT / "release_requirements.json").read_text(encoding="utf-8")
)
DESIGN = json.loads(
    (ROOT / "design_requirements.json").read_text(encoding="utf-8")
)
DEFAULT_ANCHORS = [
    float(x) for x in RELEASE["release_architecture"]["calibration_anchors_c"]
]
BRANCH_MISMATCH_TARGET = float(
    DESIGN["mirror_branch_mismatch_percent_max"]
)
PLACEHOLDER_RE = re.compile(r"__[A-Z][A-Z0-9_]*__")


def percentile(xs: list[float], q: float) -> float:
    ys = sorted(xs)
    if not ys:
        return math.nan
    pos = (len(ys) - 1) * q
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return ys[lo]
    return ys[lo] * (hi - pos) + ys[hi] * (pos - lo)


def parse_anchor_list(text: str) -> list[float]:
    anchors = [float(x.strip()) for x in text.split(",") if x.strip()]
    if len(anchors) < 2:
        raise ValueError("at least two calibration anchors are required")
    if not all(math.isfinite(x) for x in anchors):
        raise ValueError("calibration anchors must be finite")
    if anchors != sorted(set(anchors)):
        raise ValueError(
            "calibration anchors must be unique and strictly increasing"
        )
    return anchors


def branch_mismatch_percent(
    branch_small_a: float, branch_large_a: float
) -> float:
    small = abs(branch_small_a)
    large = abs(branch_large_a)
    denom = (small + large) / 2.0
    if denom <= 0.0:
        raise ValueError("branch currents must have a positive mean magnitude")
    return abs(small - large) / denom * 100.0


def read_rows(path: Path) -> list[dict[str, float]]:
    with path.open(newline="", encoding="utf-8") as handle:
        raw = list(csv.DictReader(handle, skipinitialspace=True))
    rows = [{k.strip(): float(v) for k, v in row.items()} for row in raw]
    if not rows or not all(
        all(math.isfinite(v) for v in row.values()) for row in rows
    ):
        raise ValueError(f"{path}: invalid data")
    return rows


def pwl_errors(
    rows: list[dict[str, float]],
    anchors: list[float] | None = None,
) -> list[float]:
    use_anchors = DEFAULT_ANCHORS if anchors is None else anchors
    temps = [row["temp_c"] for row in rows]
    volts = [row["dvgs_v"] for row in rows]
    idx = []
    for anchor in use_anchors:
        hit = [
            i for i, temp in enumerate(temps)
            if abs(temp - anchor) < 1e-9
        ]
        if not hit:
            raise ValueError(f"anchor {anchor} C missing")
        idx.append(hit[0])

    est = [math.nan] * len(temps)
    for ia, ib in zip(idx[:-1], idx[1:]):
        if volts[ib] == volts[ia]:
            raise ValueError("zero PWL voltage span")
        gain = (
            (temps[ib] - temps[ia])
            / (volts[ib] - volts[ia])
        )
        bias = temps[ia] - gain * volts[ia]
        for j in range(ia, ib + 1):
            est[j] = gain * volts[j] + bias

    if any(math.isnan(x) for x in est):
        raise ValueError(
            "temperature grid extends outside calibration-anchor coverage"
        )
    return [estimate - actual for estimate, actual in zip(est, temps)]


def render(
    seed: int,
    temps: list[float],
    output_rel: str,
    model_lib: Path,
    *,
    sensor_linear_scale: float = 1.0,
    mirror_linear_scale: float = 1.0,
    vdd_v: float | None = None,
    reference_current_a: float | None = None,
) -> str:
    if sensor_linear_scale <= 0.0 or mirror_linear_scale <= 0.0:
        raise ValueError("geometry linear scales must be positive")

    design = run_sky130.load_design()["nominal_characterization_seed"]
    vdd = float(design["vdd_v"] if vdd_v is None else vdd_v)
    iref = float(
        design["reference_current_a"]
        if reference_current_a is None
        else reference_current_a
    )
    if vdd <= 0.0 or iref <= 0.0:
        raise ValueError("VDD and reference current must be positive")
    sensor = design["sensor_nmos"]
    mirror = design["mirror_pmos"]
    text = (
        ROOT
        / "spice"
        / "ptat_sky130_mismatch.template.spice"
    ).read_text(encoding="utf-8")

    rep = {
        "__SEED__": str(seed),
        "__MODEL_LIB__": model_lib.as_posix(),
        "__VDDVAL__": str(vdd),
        "__IREF__": str(iref),
        "__LNS__": str(sensor["l_um"] * sensor_linear_scale),
        "__WNS1__": str(sensor["w_small_um"] * sensor_linear_scale),
        "__WNS2__": str(sensor["w_large_um"] * sensor_linear_scale),
        "__LPM__": str(mirror["l_um"] * mirror_linear_scale),
        "__WPM__": str(mirror["w_um"] * mirror_linear_scale),
        "__TEMPS__": " ".join(f"{x:g}" for x in temps),
        "__OUTPUT_CSV__": output_rel,
    }
    for before, after in rep.items():
        text = text.replace(before, after)

    leftovers = PLACEHOLDER_RE.findall(text)
    if leftovers:
        raise RuntimeError(
            f"mismatch template rendering incomplete: {leftovers}"
        )
    return text


def run_sample(
    seed: int,
    temps: list[float],
    out: Path,
    model_lib: Path,
    ngspice: str,
    *,
    sensor_linear_scale: float = 1.0,
    mirror_linear_scale: float = 1.0,
    vdd_v: float | None = None,
    reference_current_a: float | None = None,
) -> Path:
    out = out.resolve()
    results_root = (ROOT / "results").resolve()
    try:
        out.relative_to(results_root)
    except ValueError as exc:
        raise ValueError(
            "--output-dir must be inside the project results directory"
        ) from exc

    netdir = out / "netlists"
    logdir = out / "logs"
    netdir.mkdir(parents=True, exist_ok=True)
    logdir.mkdir(parents=True, exist_ok=True)

    csv_path = out / f"sample_{seed:05d}.csv"
    rel = csv_path.relative_to(results_root).as_posix()
    net = netdir / f"sample_{seed:05d}.spice"
    net.write_text(
        render(
            seed,
            temps,
            rel,
            model_lib,
            sensor_linear_scale=sensor_linear_scale,
            mirror_linear_scale=mirror_linear_scale,
            vdd_v=vdd_v,
            reference_current_a=reference_current_a,
        ),
        encoding="utf-8",
    )

    runtime_dir = out / "runtime" / f"sample_{seed:05d}"
    ngspice_env, _ = run_sky130.prepare_ngspice_environment(runtime_dir)
    proc = subprocess.run(
        [ngspice, "-b", str(net)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=300,
        env=ngspice_env,
    )
    (logdir / f"sample_{seed:05d}.log").write_text(
        proc.stdout + "\n--- STDERR ---\n" + proc.stderr,
        encoding="utf-8",
    )
    if proc.returncode != 0 or not csv_path.is_file():
        raise RuntimeError(f"sample {seed} failed; see {logdir}")
    return csv_path


def analyze(
    files: list[Path],
    temps: list[float],
    anchors: list[float] | None = None,
) -> dict:
    use_anchors = DEFAULT_ANCHORS if anchors is None else anchors
    samples = []
    dv25 = []
    target = float(
        RELEASE["release_targets"]["dense_grid_pwl_max_abs_error_c_max"]
    )

    for path in files:
        rows = read_rows(path)
        got = [row["temp_c"] for row in rows]
        if len(got) != len(temps) or any(
            abs(a - b) > 1e-8 for a, b in zip(got, temps)
        ):
            raise ValueError(f"{path}: temperature grid mismatch")

        errors = pwl_errors(rows, use_anchors)
        maxerr = max(abs(x) for x in errors)
        rms = math.sqrt(sum(x * x for x in errors) / len(errors))
        mismatch = max(
            branch_mismatch_percent(
                row["branch_small_a"],
                row["branch_large_a"],
            )
            for row in rows
        )
        power = max(row["power_w"] for row in rows) * 1e6
        near = min(rows, key=lambda row: abs(row["temp_c"] - 25))
        dv25.append(near["dvgs_v"])
        samples.append(
            {
                "file": path.name,
                "max_abs_error_c": maxerr,
                "rms_error_c": rms,
                "max_branch_mismatch_percent": mismatch,
                "max_power_uw": power,
                "pass_error_target": maxerr <= target,
                "pass_branch_mismatch_target": (
                    mismatch <= BRANCH_MISMATCH_TARGET
                ),
            }
        )

    if len(samples) > 1 and pstdev(dv25) < 1e-12:
        raise RuntimeError(
            "no measurable variation across seeds; mismatch model may be inactive"
        )

    errors = [x["max_abs_error_c"] for x in samples]
    yield_pct = (
        100
        * sum(x["pass_error_target"] for x in samples)
        / len(samples)
    )
    branch_yield_pct = (
        100
        * sum(x["pass_branch_mismatch_target"] for x in samples)
        / len(samples)
    )
    min_samples = int(
        RELEASE["release_targets"]["mismatch_min_samples"]
    )
    yield_target = float(
        RELEASE["release_targets"]["mismatch_target_yield_percent"]
    )
    complete = len(samples) >= min_samples
    error_yield_status = (
        "PASS" if complete and yield_pct >= yield_target else "FAIL"
    )
    branch_mismatch_yield_status = (
        "PASS" if complete and branch_yield_pct >= yield_target else "FAIL"
    )

    return {
        "status": (
            "PASS"
            if (
                error_yield_status == "PASS"
                and branch_mismatch_yield_status == "PASS"
            )
            else "FAIL"
        ),
        "error_yield_status": error_yield_status,
        "branch_mismatch_yield_status": branch_mismatch_yield_status,
        "evidence_class": (
            "SKY130/open_pdks local device mismatch via tt_mm; simulation only"
        ),
        "samples": len(samples),
        "minimum_samples_target": min_samples,
        "calibration": "per-sample fixed piecewise-linear calibration",
        "calibration_anchors_c": use_anchors,
        "temperature_c": temps,
        "yield_percent_error_le_target": yield_pct,
        "yield_percent_branch_mismatch_le_target": branch_yield_pct,
        "yield_target_percent": yield_target,
        "error_target_c": target,
        "branch_mismatch_target_percent": BRANCH_MISMATCH_TARGET,
        "max_abs_error_c": {
            "mean": mean(errors),
            "std": pstdev(errors) if len(errors) > 1 else 0.0,
            "p50": percentile(errors, 0.50),
            "p95": percentile(errors, 0.95),
            "p99": percentile(errors, 0.99),
            "worst": max(errors),
        },
        "dvgs_25c_std_v": (
            pstdev(dv25) if len(dv25) > 1 else 0.0
        ),
        "ngspice_compatibility_mode": "hsa",
        "per_sample": samples,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", type=int, default=100)
    parser.add_argument("--seed-start", type=int, default=1001)
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--temps", default="-40:125:5")
    parser.add_argument(
        "--vdd-v",
        type=float,
        help="override nominal supply voltage for this Monte Carlo run",
    )
    parser.add_argument(
        "--reference-current-a",
        type=float,
        help="override nominal PMOS reference current for this Monte Carlo run",
    )
    parser.add_argument(
        "--anchors",
        default=",".join(f"{x:g}" for x in DEFAULT_ANCHORS),
        help="comma-separated calibration temperatures in degC",
    )
    parser.add_argument(
        "--sensor-linear-scale",
        type=float,
        default=1.0,
        help=(
            "multiply sensor NMOS W and L together; "
            "area scales by factor^2"
        ),
    )
    parser.add_argument(
        "--mirror-linear-scale",
        type=float,
        default=1.0,
        help=(
            "multiply mirror PMOS W and L together; "
            "area scales by factor^2"
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "results" / "mismatch_mc",
    )
    parser.add_argument(
        "--allow-fail",
        action="store_true",
        help=(
            "return success after a valid simulation even when "
            "statistical release targets are not met"
        ),
    )
    args = parser.parse_args()

    if args.samples < 2:
        print("MISMATCH MC: FAIL: at least 2 samples required")
        return 2
    if args.jobs < 1:
        print("MISMATCH MC: FAIL: --jobs must be at least 1")
        return 2
    if (
        args.sensor_linear_scale <= 0.0
        or args.mirror_linear_scale <= 0.0
        or (args.vdd_v is not None and args.vdd_v <= 0.0)
        or (
            args.reference_current_a is not None
            and args.reference_current_a <= 0.0
        )
    ):
        print(
            "MISMATCH MC: FAIL: geometry scales and operating point "
            "overrides must be positive"
        )
        return 2

    try:
        temps = run_sky130.parse_temps(args.temps)
        anchors = parse_anchor_list(args.anchors)
        if anchors[0] < min(temps) or anchors[-1] > max(temps):
            raise ValueError(
                "calibration anchors must lie inside the temperature grid"
            )
        missing = [
            anchor
            for anchor in anchors
            if not any(abs(anchor - temp) < 1e-9 for temp in temps)
        ]
        if missing:
            raise ValueError(
                f"calibration anchors missing from temperature grid: {missing}"
            )
    except Exception as exc:
        print(f"MISMATCH MC: FAIL: {exc}", file=sys.stderr)
        return 2

    ngspice = shutil.which("ngspice")
    if not ngspice:
        print("MISMATCH MC: FAIL: ngspice not found")
        return 2

    try:
        model = run_sky130.discover_model_lib()
        revision = run_sky130.pdk_revision(model)
        if revision == "unknown":
            raise RuntimeError(
                "exact SKY130 revision unavailable; set SKY130_PDK_REVISION"
            )
        args.output_dir.mkdir(parents=True, exist_ok=True)
        seeds = [args.seed_start + i for i in range(args.samples)]

        if args.jobs == 1:
            files = [
                run_sample(
                    seed,
                    temps,
                    args.output_dir,
                    model,
                    ngspice,
                    sensor_linear_scale=args.sensor_linear_scale,
                    mirror_linear_scale=args.mirror_linear_scale,
                    vdd_v=args.vdd_v,
                    reference_current_a=args.reference_current_a,
                )
                for seed in seeds
            ]
        else:
            with ThreadPoolExecutor(max_workers=args.jobs) as pool:
                futures = [
                    pool.submit(
                        run_sample,
                        seed,
                        temps,
                        args.output_dir,
                        model,
                        ngspice,
                        sensor_linear_scale=args.sensor_linear_scale,
                        mirror_linear_scale=args.mirror_linear_scale,
                        vdd_v=args.vdd_v,
                        reference_current_a=args.reference_current_a,
                    )
                    for seed in seeds
                ]
                files = [
                    future.result()
                    for future in as_completed(futures)
                ]
            files.sort()

        result = analyze(files, temps, anchors)
        result["parallel_jobs"] = args.jobs
        result["geometry"] = {
            "sensor_linear_scale": args.sensor_linear_scale,
            "sensor_area_scale": args.sensor_linear_scale ** 2,
            "mirror_linear_scale": args.mirror_linear_scale,
            "mirror_area_scale": args.mirror_linear_scale ** 2,
            "ratio_preservation": (
                "W and L scaled together; nominal W/L and sensor width ratio "
                "are preserved"
            ),
        }
        nominal = run_sky130.load_design()["nominal_characterization_seed"]
        result["seed_start"] = args.seed_start
        result["seed_end"] = args.seed_start + args.samples - 1
        result["operating_point"] = {
            "vdd_v": (
                nominal["vdd_v"] if args.vdd_v is None else args.vdd_v
            ),
            "reference_current_a": (
                nominal["reference_current_a"]
                if args.reference_current_a is None
                else args.reference_current_a
            ),
        }
        result["provenance"] = {
            "ngspice": run_sky130.ngspice_version(ngspice),
            "ngspice_compatibility_mode": "hsa",
            "pdk_revision": revision,
            "model_library": str(model),
            "model_sha256": run_sky130.sha256_file(model),
            "design_requirements_sha256": run_sky130.sha256_file(
                ROOT / "design_requirements.json"
            ),
        }
    except Exception as exc:
        print(f"MISMATCH MC: FAIL: {exc}", file=sys.stderr)
        return 1

    (args.output_dir / "summary.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print("MISMATCH MC:", result["status"])
    print(
        "samples:",
        result["samples"],
        "error yield:",
        result["yield_percent_error_le_target"],
        "branch-mismatch yield:",
        result["yield_percent_branch_mismatch_le_target"],
    )
    print(
        "geometry linear scales:",
        args.sensor_linear_scale,
        args.mirror_linear_scale,
    )
    if result["status"] == "PASS" or args.allow_fail:
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
