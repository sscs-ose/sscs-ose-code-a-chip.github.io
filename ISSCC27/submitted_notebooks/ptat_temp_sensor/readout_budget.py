#!/usr/bin/env python3
"""Behavioral ADC/readout verification for retained or candidate PDK data."""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RELEASE = json.loads(
    (ROOT / "release_requirements.json").read_text(encoding="utf-8")
)
DESIGN = json.loads(
    (ROOT / "design_requirements.json").read_text(encoding="utf-8")
)
MANIFEST = json.loads(
    (ROOT / "results" / "sky130_ci_manifest.json").read_text(
        encoding="utf-8"
    )
)
ANCHORS = [
    float(x)
    for x in RELEASE["release_architecture"]["calibration_anchors_c"]
]
PROVENANCE_KEYS = (
    "ngspice",
    "ngspice_compatibility_mode",
    "pdk_revision",
    "model_sha256",
    "design_requirements_sha256",
)


def load(path: Path) -> tuple[list[float], list[float]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle, skipinitialspace=True))
    if not rows:
        raise ValueError(f"{path}: empty CSV")
    try:
        temps = [float(row["temp_c"]) for row in rows]
        dvgs = [float(row["dvgs_v"]) for row in rows]
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"{path}: invalid temperature/DVGS data") from exc
    if not all(math.isfinite(x) for x in temps + dvgs):
        raise ValueError(f"{path}: non-finite temperature/DVGS data")
    if any(b <= a for a, b in zip(temps, temps[1:])):
        raise ValueError(f"{path}: temperature grid must be strictly increasing")
    return temps, dvgs


def anchor_indices(
    temps: list[float], anchors: list[float]
) -> list[int]:
    indices: list[int] = []
    for anchor in anchors:
        hits = [
            index
            for index, temp in enumerate(temps)
            if abs(temp - anchor) < 1e-9
        ]
        if len(hits) != 1:
            raise ValueError(
                f"calibration anchor {anchor:g} C is missing or duplicated"
            )
        indices.append(hits[0])
    if indices != sorted(indices) or len(set(indices)) != len(indices):
        raise ValueError("calibration anchors must be unique and increasing")
    if indices[0] != 0 or indices[-1] != len(temps) - 1:
        raise ValueError(
            "calibration anchors must cover the full temperature grid"
        )
    return indices


def calibrate_pwl(
    temps: list[float],
    volts: list[float],
    anchors: list[float] | None = None,
) -> list[float]:
    use_anchors = ANCHORS if anchors is None else anchors
    indices = anchor_indices(temps, use_anchors)
    estimated = [math.nan] * len(temps)
    for ia, ib in zip(indices[:-1], indices[1:]):
        span = volts[ib] - volts[ia]
        if span == 0.0:
            raise ValueError("zero PWL voltage span")
        gain = (temps[ib] - temps[ia]) / span
        offset = temps[ia] - gain * volts[ia]
        for index in range(ia, ib + 1):
            estimated[index] = gain * volts[index] + offset
    if any(not math.isfinite(value) for value in estimated):
        raise ValueError("PWL calibration did not cover all samples")
    return estimated


def quantization_rms_from_anchors(
    temps: list[float],
    volts: list[float],
    anchors: list[float],
    adc_lsb_v: float,
    analog_gain: float,
) -> float:
    indices = anchor_indices(temps, anchors)
    values: list[float] = []
    for ia, ib in zip(indices[:-1], indices[1:]):
        delta_t = temps[ib] - temps[ia]
        slope = abs((volts[ib] - volts[ia]) / delta_t)
        if slope <= 0.0 or not math.isfinite(slope):
            raise ValueError("non-positive calibration voltage slope")
        values.append(adc_lsb_v / (analog_gain * slope * math.sqrt(12)))
    return max(values)


def _configuration() -> tuple[int, float, float, float, float, float]:
    adc = DESIGN["adc"]
    bits = int(adc["bits"])
    vref = float(adc["vref_v"])
    gain = float(RELEASE["release_architecture"]["analog_gain"])
    util_target = float(
        RELEASE["release_targets"]["adc_full_scale_utilization_max"]
    )
    qrms_target = float(
        RELEASE["release_targets"]["adc_quantization_rms_c_max"]
    )
    total_target = float(
        RELEASE["release_targets"][
            "quantized_sampled_grid_pwl_max_abs_error_c_max"
        ]
    )
    return bits, vref, gain, util_target, qrms_target, total_target


def analyze() -> dict:
    """Preserve the retained run-221 readout calculation exactly."""
    bits, vref, gain, util_target, qrms_target, total_target = (
        _configuration()
    )
    lsb = vref / (2**bits)
    per: dict[str, dict[str, float]] = {}
    worst_qrms = 0.0
    worst_total = 0.0
    max_input = 0.0
    for mode in ("ideal", "mirror"):
        for corner in ("tt", "ff", "ss"):
            temps, volts = load(
                ROOT
                / "results"
                / "sky130_ci"
                / f"ptat_{mode}_{corner}.csv"
            )
            adc_input = [gain * value for value in volts]
            codes = [
                min(2**bits - 1, max(0, round(value / lsb)))
                for value in adc_input
            ]
            quantized = [code * lsb / gain for code in codes]
            estimated = calibrate_pwl(temps, quantized)
            error = [
                estimate - actual
                for estimate, actual in zip(estimated, temps)
            ]
            slope = (
                float(
                    MANIFEST["summary"][mode][corner][
                        "ptat_slope_uv_per_k"
                    ]
                )
                * 1e-6
            )
            qrms = lsb / (gain * slope * math.sqrt(12))
            item = {
                "adc_input_min_v": min(adc_input),
                "adc_input_max_v": max(adc_input),
                "full_scale_utilization": max(adc_input) / vref,
                "quantization_rms_c": qrms,
                "quantized_pwl_max_abs_error_c": max(
                    abs(value) for value in error
                ),
            }
            per[f"{mode}_{corner}"] = item
            worst_qrms = max(worst_qrms, qrms)
            worst_total = max(
                worst_total, item["quantized_pwl_max_abs_error_c"]
            )
            max_input = max(max_input, max(adc_input))
    status = (
        worst_qrms <= qrms_target
        and max_input / vref <= util_target
        and worst_total <= total_target
    )
    return {
        "status": "PASS" if status else "FAIL",
        "evidence_boundary": (
            "Behavioral 12-bit ADC quantization applied to retained "
            "real-PDK voltages; no transistor-level ADC or ADC power claim."
        ),
        "bits": bits,
        "vref_v": vref,
        "analog_gain": gain,
        "lsb_v": lsb,
        "worst_quantization_rms_c": worst_qrms,
        "quantization_rms_target_c": qrms_target,
        "worst_full_scale_utilization": max_input / vref,
        "full_scale_utilization_target_max": util_target,
        "worst_quantized_pwl_sampled_error_c": worst_total,
        "quantized_sampled_grid_target_c": total_target,
        "per_dataset": per,
    }


def analyze_directory(
    input_dir: Path,
    anchors: list[float] | None = None,
) -> dict:
    """Evaluate the release ADC/readout contract on a dense PDK candidate."""
    use_anchors = ANCHORS if anchors is None else [float(x) for x in anchors]
    bits, vref, gain, util_target, qrms_target, total_target = (
        _configuration()
    )
    lsb = vref / (2**bits)
    metadata_path = input_dir / "run_metadata.json"
    if not metadata_path.is_file():
        raise ValueError(f"missing candidate metadata: {metadata_path}")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    provenance = {
        key: metadata.get(key)
        for key in PROVENANCE_KEYS
    }
    if any(not value for value in provenance.values()):
        raise ValueError("candidate readout provenance is incomplete")

    per: dict[str, dict[str, float]] = {}
    worst_qrms = 0.0
    worst_total = 0.0
    max_input = 0.0
    min_input = math.inf
    reference_grid: list[float] | None = None

    for mode in ("ideal", "mirror"):
        for corner in ("tt", "ff", "ss"):
            path = input_dir / f"ptat_{mode}_{corner}.csv"
            temps, volts = load(path)
            if reference_grid is None:
                reference_grid = temps
            elif temps != reference_grid:
                raise ValueError(
                    f"{path}: temperature grid differs from other datasets"
                )

            adc_input = [gain * value for value in volts]
            codes = [
                min(2**bits - 1, max(0, round(value / lsb)))
                for value in adc_input
            ]
            quantized = [code * lsb / gain for code in codes]
            estimated = calibrate_pwl(temps, quantized, use_anchors)
            error = [
                estimate - actual
                for estimate, actual in zip(estimated, temps)
            ]
            qrms = quantization_rms_from_anchors(
                temps,
                volts,
                use_anchors,
                lsb,
                gain,
            )
            item = {
                "adc_input_min_v": min(adc_input),
                "adc_input_max_v": max(adc_input),
                "full_scale_utilization": max(adc_input) / vref,
                "quantization_rms_c": qrms,
                "quantized_pwl_max_abs_error_c": max(
                    abs(value) for value in error
                ),
            }
            per[f"{mode}_{corner}"] = item
            worst_qrms = max(worst_qrms, qrms)
            worst_total = max(
                worst_total, item["quantized_pwl_max_abs_error_c"]
            )
            max_input = max(max_input, max(adc_input))
            min_input = min(min_input, min(adc_input))

    full_scale = max_input / vref
    status = (
        min_input >= 0.0
        and worst_qrms <= qrms_target
        and full_scale <= util_target
        and worst_total <= total_target
    )
    return {
        "status": "PASS" if status else "FAIL",
        "evidence_boundary": (
            "Behavioral release ADC/readout contract applied to dense "
            "transistor-level candidate voltages; no transistor-level ADC "
            "or ADC power claim."
        ),
        "anchors_c": use_anchors,
        "temperature_c": reference_grid,
        "bits": bits,
        "vref_v": vref,
        "analog_gain": gain,
        "lsb_v": lsb,
        "worst_quantization_rms_c": worst_qrms,
        "quantization_rms_target_c": qrms_target,
        "worst_full_scale_utilization": full_scale,
        "full_scale_utilization_target_max": util_target,
        "worst_quantized_pwl_sampled_error_c": worst_total,
        "quantized_sampled_grid_target_c": total_target,
        "minimum_adc_input_v": min_input,
        "provenance": provenance,
        "operating_point": metadata.get("operating_point", {}),
        "geometry": {
            "sensor_linear_scale": metadata.get("sensor_linear_scale"),
            "mirror_linear_scale": metadata.get("mirror_linear_scale"),
            "mirror_length_multiplier": metadata.get("mirror_length_multiplier", 1.0),
        },
        "per_dataset": per,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "results" / "readout_budget.json",
    )
    parser.add_argument("--check", action="store_true")
    parser.add_argument(
        "--input-dir",
        type=Path,
        help="evaluate dense candidate CSVs instead of retained run-221 data",
    )
    parser.add_argument(
        "--allow-fail",
        action="store_true",
        help="write valid candidate evidence even when readout targets fail",
    )
    args = parser.parse_args()

    if args.check and args.input_dir is not None:
        print("READOUT BUDGET: FAIL: --check is only for retained evidence")
        return 2

    try:
        result = (
            analyze()
            if args.input_dir is None
            else analyze_directory(args.input_dir)
        )
    except Exception as exc:
        print(f"READOUT BUDGET: FAIL: {exc}")
        return 1

    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.check:
        if (
            not args.output.is_file()
            or args.output.read_text(encoding="utf-8") != rendered
        ):
            print("READOUT BUDGET: FAIL: retained result missing/stale")
            return 1
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")

    print("READOUT BUDGET:", result["status"])
    print(
        "worst quantization RMS C:",
        result["worst_quantization_rms_c"],
    )
    print(
        "worst full-scale utilization:",
        result["worst_full_scale_utilization"],
    )
    print(
        "worst quantized PWL sampled error C:",
        result["worst_quantized_pwl_sampled_error_c"],
    )
    if result["status"] == "PASS" or args.allow_fail:
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
