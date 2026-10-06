#!/usr/bin/env python3
"""Two-stage SKY130 mismatch sizing study for the PTAT core.

Stage 1 screens device-size candidates using a shared discovery seed set
(common-random-number comparison). Stage 2 validates exactly one selected
candidate on a disjoint seed set. No validation seeds are used for selection.

This script does not alter the release architecture automatically. It produces
evidence for a later engineering decision.
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import mismatch_mc
import run_sky130

ROOT = Path(__file__).resolve().parent
DEFAULT_CANDIDATES = (
    (1.0, 1.0),
    (2.0, 4.0),
    (2.0, 8.0),
    (4.0, 4.0),
    (4.0, 8.0),
    (4.0, 16.0),
    (4.0, 32.0),
    (8.0, 8.0),
    (8.0, 16.0),
    (8.0, 32.0),
    (16.0, 16.0),
    (16.0, 32.0),
)


def scaled_design(base: dict, sensor_scale: float, mirror_scale: float) -> dict:
    if sensor_scale < 1.0 or mirror_scale < 1.0:
        raise ValueError("linear size scales must be >= 1")
    design = copy.deepcopy(base)
    seed = design["nominal_characterization_seed"]
    sensor = seed["sensor_nmos"]
    mirror = seed["mirror_pmos"]

    sensor["l_um"] *= sensor_scale
    sensor["w_small_um"] *= sensor_scale
    sensor["w_large_um"] *= sensor_scale
    mirror["l_um"] *= mirror_scale
    mirror["w_um"] *= mirror_scale
    return design


def active_device_area_um2(design: dict) -> float:
    seed = design["nominal_characterization_seed"]
    sensor = seed["sensor_nmos"]
    mirror = seed["mirror_pmos"]
    sensor_area = sensor["l_um"] * (
        sensor["w_small_um"] + sensor["w_large_um"]
    )
    mirror_area = (
        mirror["l_um"]
        * mirror["w_um"]
        * (1 + int(mirror["equal_output_devices"]))
    )
    return float(sensor_area + mirror_area)


def wilson_interval(successes: int, total: int, z: float = 1.959963984540054) -> list[float]:
    if total <= 0:
        return [math.nan, math.nan]
    p = successes / total
    denom = 1.0 + z * z / total
    center = (p + z * z / (2.0 * total)) / denom
    radius = z * math.sqrt(
        p * (1.0 - p) / total + z * z / (4.0 * total * total)
    ) / denom
    return [100.0 * (center - radius), 100.0 * (center + radius)]


def enrich_yield_intervals(summary: dict) -> None:
    n = int(summary["samples"])
    error_success = sum(
        bool(x["pass_error_target"]) for x in summary["per_sample"]
    )
    branch_success = sum(
        bool(x["pass_branch_mismatch_target"]) for x in summary["per_sample"]
    )
    summary["error_yield_wilson_95_percent"] = wilson_interval(error_success, n)
    summary["branch_yield_wilson_95_percent"] = wilson_interval(branch_success, n)


def candidate_score(summary: dict, area_um2: float) -> tuple[float, float, float, float]:
    target = float(summary["yield_target_percent"])
    error_yield = float(summary["yield_percent_error_le_target"])
    branch_yield = float(summary["yield_percent_branch_mismatch_le_target"])
    error_deficit = max(0.0, target - error_yield)
    branch_deficit = max(0.0, target - branch_yield)
    p95_error = float(summary["max_abs_error_c"]["p95"])
    return (
        error_deficit + branch_deficit,
        max(error_deficit, branch_deficit),
        area_um2,
        p95_error,
    )


def parse_candidates(spec: str | None) -> list[tuple[float, float]]:
    if not spec:
        return list(DEFAULT_CANDIDATES)
    out = []
    for token in spec.split(","):
        sensor_text, mirror_text = token.strip().lower().split("x", 1)
        pair = (float(sensor_text), float(mirror_text))
        if pair[0] < 1.0 or pair[1] < 1.0:
            raise ValueError("candidate scales must be >= 1")
        out.append(pair)
    if not out:
        raise ValueError("at least one candidate is required")
    return out


def candidate_tag(sensor_scale: float, mirror_scale: float) -> str:
    def fmt(value: float) -> str:
        return f"{value:g}".replace(".", "p")
    return f"sensor_{fmt(sensor_scale)}__mirror_{fmt(mirror_scale)}"


def run_candidate(
    *,
    base_design: dict,
    sensor_scale: float,
    mirror_scale: float,
    samples: int,
    seed_start: int,
    jobs: int,
    temps: list[float],
    output_dir: Path,
    model_lib: Path,
    ngspice: str,
) -> dict:
    design = scaled_design(base_design, sensor_scale, mirror_scale)
    original_loader = run_sky130.load_design
    run_sky130.load_design = lambda: design
    try:
        seeds = [seed_start + i for i in range(samples)]
        if jobs == 1:
            files = [
                mismatch_mc.run_sample(
                    seed, temps, output_dir, model_lib, ngspice
                )
                for seed in seeds
            ]
        else:
            with ThreadPoolExecutor(max_workers=jobs) as pool:
                futures = [
                    pool.submit(
                        mismatch_mc.run_sample,
                        seed,
                        temps,
                        output_dir,
                        model_lib,
                        ngspice,
                    )
                    for seed in seeds
                ]
                files = [future.result() for future in as_completed(futures)]
            files.sort()
    finally:
        run_sky130.load_design = original_loader

    summary = mismatch_mc.analyze(files, temps)
    enrich_yield_intervals(summary)
    summary["sizing"] = {
        "sensor_linear_scale": sensor_scale,
        "mirror_linear_scale": mirror_scale,
        "effective_sensor_nmos": design["nominal_characterization_seed"]["sensor_nmos"],
        "effective_mirror_pmos": design["nominal_characterization_seed"]["mirror_pmos"],
        "active_device_area_um2_approx": active_device_area_um2(design),
    }
    summary["seed_start"] = seed_start
    summary["seed_stop_inclusive"] = seed_start + samples - 1
    summary["provenance"] = {
        "ngspice": run_sky130.ngspice_version(ngspice),
        "ngspice_compatibility_mode": "hsa",
        "pdk_revision": run_sky130.pdk_revision(model_lib),
        "model_library": str(model_lib),
        "model_sha256": run_sky130.sha256_file(model_lib),
        "base_design_requirements_sha256": run_sky130.sha256_file(
            ROOT / "design_requirements.json"
        ),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return summary


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--screen-samples", type=int, default=16)
    ap.add_argument("--validation-samples", type=int, default=100)
    ap.add_argument("--screen-seed-start", type=int, default=2001)
    ap.add_argument("--validation-seed-start", type=int, default=5001)
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--temps", default="-40:125:5")
    ap.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "results" / "mismatch_sizing_study",
    )
    ap.add_argument(
        "--candidates",
        help="comma-separated sensorScale x mirrorScale pairs, e.g. 1x1,4x16",
    )
    args = ap.parse_args()

    if args.screen_samples < 2 or args.validation_samples < 2:
        print("SIZING STUDY: FAIL: sample counts must be >= 2", file=sys.stderr)
        return 2
    if args.jobs < 1:
        print("SIZING STUDY: FAIL: --jobs must be >= 1", file=sys.stderr)
        return 2

    screen_end = args.screen_seed_start + args.screen_samples - 1
    validation_end = args.validation_seed_start + args.validation_samples - 1
    if not (
        screen_end < args.validation_seed_start
        or validation_end < args.screen_seed_start
    ):
        print(
            "SIZING STUDY: FAIL: screening and validation seed sets overlap",
            file=sys.stderr,
        )
        return 2

    try:
        candidates = parse_candidates(args.candidates)
        temps = run_sky130.parse_temps(args.temps)
        ngspice = shutil.which("ngspice")
        if not ngspice:
            raise RuntimeError("ngspice not found")
        model_lib = run_sky130.discover_model_lib()
        revision = run_sky130.pdk_revision(model_lib)
        if revision == "unknown":
            raise RuntimeError(
                "exact SKY130 revision unavailable; set SKY130_PDK_REVISION"
            )
        base_design = run_sky130.load_design()

        screen_results = []
        for sensor_scale, mirror_scale in candidates:
            tag = candidate_tag(sensor_scale, mirror_scale)
            summary = run_candidate(
                base_design=base_design,
                sensor_scale=sensor_scale,
                mirror_scale=mirror_scale,
                samples=args.screen_samples,
                seed_start=args.screen_seed_start,
                jobs=args.jobs,
                temps=temps,
                output_dir=args.output_dir / "screen" / tag,
                model_lib=model_lib,
                ngspice=ngspice,
            )
            area = float(summary["sizing"]["active_device_area_um2_approx"])
            screen_results.append(
                {
                    "tag": tag,
                    "sensor_linear_scale": sensor_scale,
                    "mirror_linear_scale": mirror_scale,
                    "area_um2_approx": area,
                    "score": list(candidate_score(summary, area)),
                    "summary": summary,
                }
            )
            print(
                "SCREEN",
                tag,
                "error_yield=",
                summary["yield_percent_error_le_target"],
                "branch_yield=",
                summary["yield_percent_branch_mismatch_le_target"],
            )

        selected = min(screen_results, key=lambda item: tuple(item["score"]))
        validation = run_candidate(
            base_design=base_design,
            sensor_scale=float(selected["sensor_linear_scale"]),
            mirror_scale=float(selected["mirror_linear_scale"]),
            samples=args.validation_samples,
            seed_start=args.validation_seed_start,
            jobs=args.jobs,
            temps=temps,
            output_dir=args.output_dir / "validation" / selected["tag"],
            model_lib=model_lib,
            ngspice=ngspice,
        )

        result = {
            "method": {
                "selection": (
                    "screen on shared discovery seeds; rank by empirical yield "
                    "deficit, then approximate active device area and p95 error"
                ),
                "screen_seed_range": [
                    args.screen_seed_start,
                    screen_end,
                ],
                "validation_seed_range": [
                    args.validation_seed_start,
                    validation_end,
                ],
                "seed_sets_disjoint": True,
                "screen_samples_per_candidate": args.screen_samples,
                "validation_samples": args.validation_samples,
                "temperature_c": temps,
                "candidate_count": len(screen_results),
            },
            "selected_candidate": {
                key: selected[key]
                for key in (
                    "tag",
                    "sensor_linear_scale",
                    "mirror_linear_scale",
                    "area_um2_approx",
                    "score",
                )
            },
            "screening": [
                {
                    "tag": item["tag"],
                    "sensor_linear_scale": item["sensor_linear_scale"],
                    "mirror_linear_scale": item["mirror_linear_scale"],
                    "area_um2_approx": item["area_um2_approx"],
                    "score": item["score"],
                    "status": item["summary"]["status"],
                    "error_yield_percent": item["summary"][
                        "yield_percent_error_le_target"
                    ],
                    "branch_yield_percent": item["summary"][
                        "yield_percent_branch_mismatch_le_target"
                    ],
                    "p95_max_abs_error_c": item["summary"]["max_abs_error_c"]["p95"],
                }
                for item in screen_results
            ],
            "validation": validation,
            "qualification_status": validation["status"],
            "release_architecture_changed": False,
        }
        args.output_dir.mkdir(parents=True, exist_ok=True)
        (args.output_dir / "study_summary.json").write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except Exception as exc:
        print(f"SIZING STUDY: FAIL: {exc}", file=sys.stderr)
        return 1

    print("SELECTED:", result["selected_candidate"]["tag"])
    print(
        "VALIDATION:",
        result["qualification_status"],
        "error_yield=",
        validation["yield_percent_error_le_target"],
        "branch_yield=",
        validation["yield_percent_branch_mismatch_le_target"],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
