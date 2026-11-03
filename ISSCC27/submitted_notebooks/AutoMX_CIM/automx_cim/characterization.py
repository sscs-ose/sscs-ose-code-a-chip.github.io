"""Receipt-backed, TT-only architectural model for the passive SKY130 4x4 core.

The analog-to-digital transfer below is an explicitly assumed linear decoder,
not a measured sense amplifier.  This module must not be used as a PVT or
clocked-wrapper sign-off model.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import math
from pathlib import Path
import re
from typing import Any

import numpy as np

from .attention import Stage1Result, error_metrics, mha_from_projections
from .circuit.sky130 import _patterns
from .config import Sky130MHAConfig
from .fixed_point import AutoMXFixedConfig, fixed_mxfp4_qtea_projection
from .mxfp4 import encode_mxfp4
from .projection import QTEAProjection


CORE = "automx_ternary_cim_4x4_core"
STAGES = ("cell", "column4", "column8", "macro4x4")
PHYSICAL_RECEIPTS = ("preflight.json", "layout.json", "magic_drc.json",
                     "klayout_drc.json", "netgen_lvs.json", "pex.json",
                     "post_layout.json", "pre_post_comparison.json")


def _digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def _finite(value: Any, label: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"non-finite {label}")
    return result


def build_characterization(root: str | Path, config: Sky130MHAConfig) -> dict[str, Any]:
    """Verify current receipt chain and tabulate measured electrical samples."""
    if (config.physical_mode, config.physical_rows, config.physical_cols,
        config.logical_rows, config.logical_cols) != ("ternary_base_only", 4, 4, 32, 8):
        raise ValueError("Stage 6 currently supports only base-only physical 4x4 / logical 32x8")
    root = Path(root).resolve()
    manifest_path = root / "generated/sky130/spice/stage4_manifest.json"
    manifest = _json(manifest_path)
    if manifest.get("format") != "automx-cim-stage4-spice-manifest-v1" or manifest.get("config_sha256") != config.sha256:
        raise ValueError("Stage-4 manifest/config mismatch; rerun Stage 4")
    if (manifest.get("corner"), manifest.get("vdd"), manifest.get("temperature_c")) != ("tt", config.vdd, config.temperature_c):
        raise ValueError("Stage-4 PVT differs from the configured TT point")
    if _digest(Path(manifest["model_library"])) != manifest.get("model_library_sha256"):
        raise ValueError("Stage-4 PDK model library changed after simulation")
    artifacts = {item["stage"]: item for item in manifest["artifacts"]}
    if set(artifacts) != set(STAGES):
        raise ValueError("Stage 6 requires all four Stage-4 artifacts")
    stage4: dict[str, Any] = {}
    stage4_hashes: dict[str, str] = {}
    for stage in STAGES:
        artifact = artifacts[stage]
        receipt_path = Path(artifact["receipt"])
        receipt = _json(receipt_path)
        if (receipt.get("format"), receipt.get("status"), receipt.get("stage"), receipt.get("config_sha256")) != (
            "automx-cim-stage4-ngspice-receipt-v1", "PASS", stage, config.sha256
        ):
            raise ValueError(f"Stage-4 {stage} receipt is stale or not PASS")
        if (receipt.get("corner"), receipt.get("vdd"), receipt.get("temperature_c")) != ("tt", config.vdd, config.temperature_c):
            raise ValueError(f"Stage-4 {stage} PVT mismatch")
        if receipt.get("inputs", {}).get("netlist_sha256") != _digest(Path(artifact["netlist"])):
            raise ValueError(f"Stage-4 {stage} netlist changed after simulation")
        if receipt.get("model_library_sha256") != manifest["model_library_sha256"]:
            raise ValueError(f"Stage-4 {stage} model library hash mismatch")
        jobs = artifact.get("jobs") or [{"testbench": artifact["testbench"]}]
        deck_hashes = {str(Path(item["path"]).resolve()): item["sha256"]
                       for item in receipt.get("inputs", {}).get("testbenches", [])}
        if len(deck_hashes) != len(jobs) or any(
            deck_hashes.get(str(Path(job["testbench"]).resolve())) != _digest(Path(job["testbench"]))
            for job in jobs
        ):
            raise ValueError(f"Stage-4 {stage} testbench changed after simulation")
        measurements = receipt["measurements"]
        job_for_case = {case["measurement"]: job["name"]
                        for job in artifact.get("jobs", []) for case in job["cases"]}
        samples = []
        for case in artifact["cases"]:
            key = case["measurement"]
            sample = {"name": key, "integer_sum": int(case["expected"]),
                      "swing_v": _finite(measurements[key], key),
                      "delay_s": (_finite(measurements[key.replace("_diff", "_delay")], key + " delay")
                                  if key.replace("_diff", "_delay") in artifact["delay_measurements"] else None),
                      "energy_j": (_finite(measurements[f"energy_j__{job_for_case[key]}"], key + " energy")
                                   if key in job_for_case else None)}
            if stage == "cell":
                match = re.fullmatch(r"cell_w(n1|z0|p1)_a(\d+)_diff", key)
                if not match:
                    raise ValueError(f"unknown cell stimulus: {key}")
                sample.update({"ternary_weight": {"n1": -1, "z0": 0, "p1": 1}[match.group(1)],
                               "e2m1_code_x2": int(match.group(2)), "active_rows": int(match.group(1) != "z0")})
            elif stage in {"column4", "column8"}:
                match = re.fullmatch(r"column_\d+_(pos|neg)_n(\d+)_diff", key)
                if not match:
                    raise ValueError(f"unknown column stimulus: {key}")
                sample.update({"active_rows": int(match.group(2)), "ternary_nonzero": int(match.group(2)),
                               "e2m1_code_x2": 4})
            samples.append(sample)
        delays = {key: _finite(measurements[key], key) for key in artifact["delay_measurements"]}
        energies = {key.removeprefix("energy_j__"): _finite(value, key)
                    for key, value in measurements.items() if key.startswith("energy_j__")}
        stage4[stage] = {"samples": samples, "delays_s": delays,
                         "energy_j_sweep_average": _finite(measurements["energy_j"], f"{stage} average energy"),
                         "energy_by_job_j": energies, "receipt_sha256": _digest(receipt_path)}
        stage4_hashes[stage] = _digest(receipt_path)

    receipt_dir = root / "results/receipts/physical"
    summary_path = receipt_dir / "stage5_summary.json"
    summary = _json(summary_path)
    if (summary.get("format"), summary.get("status"), summary.get("macro"), summary.get("config_sha256")) != (
        "automx-cim-stage5-summary-v1", "PASS", CORE, config.sha256
    ):
        raise ValueError("Stage-5 summary is stale or not PASS")
    for name in PHYSICAL_RECEIPTS:
        path = receipt_dir / name
        if summary.get("receipts", {}).get(name) != _digest(path) or _json(path).get("status") != "PASS":
            raise ValueError(f"Stage-5 {name} changed or is not PASS")
    for name, view in summary.get("views", {}).items():
        if _digest(Path(view["path"])) != view["sha256"]:
            raise ValueError(f"Stage-5 {name} view changed after sign-off")
    pex_receipt = _json(receipt_dir / "pex.json")
    if pex_receipt.get("sha256") != _digest(Path(pex_receipt["extracted_spice"])):
        raise ValueError("PEX netlist changed after Stage 5")
    post = _json(receipt_dir / "post_layout.json")
    if post.get("pex_sha256") != pex_receipt["sha256"]:
        raise ValueError("post-layout simulation does not match the PEX netlist")
    macro = artifacts["macro4x4"]
    comparison = _json(receipt_dir / "pre_post_comparison.json")
    macro_pre = _json(Path(macro["receipt"]))["measurements"]
    for case in macro["cases"]:
        key = case["measurement"]
        item = comparison.get("measurements", {}).get(key, {})
        if item.get("pre") != macro_pre.get(key):
            raise ValueError(f"Stage-5 comparison is not linked to current Stage-4 sample {key}")
    if Path(comparison.get("pre_layout_receipt", "")).resolve() != Path(macro["receipt"]).resolve():
        raise ValueError("Stage-5 comparison points to a different Stage-4 receipt")
    patterns = {name: (acts, weights) for name, acts, weights in _patterns(4, 4)}
    physical_samples = []
    delay_values = []
    energies = []
    pattern_summaries = []
    for job in macro["jobs"]:
        name = job["name"]
        if name not in patterns or name not in post["jobs"]:
            raise ValueError(f"missing post-layout pattern: {name}")
        acts, weights = patterns[name]
        measurements = post["jobs"][name]
        energy = _finite(measurements["energy_j"], f"{name} energy")
        energies.append(energy)
        job_delays = [_finite(measurements[key], key) for key in job["delay_measurements"]]
        pattern_summaries.append({"name": name, "energy_j": energy,
                                  "max_delay_s": max(job_delays) if job_delays else None,
                                  "activation_x2": list(acts),
                                  "ternary_nonzero_by_column": [sum(weights[row][col] != 0 for row in range(4))
                                                                 for col in range(4)]})
        for col in range(4):
            case = next(item for item in job["cases"] if item["measurement"] == f"macro_{name}_c{col}_diff")
            key = case["measurement"]
            expected = sum(acts[row] * weights[row][col] for row in range(4))
            if expected != case["expected"]:
                raise ValueError(f"pattern/case mismatch: {key}")
            if comparison["measurements"][key].get("post") != measurements.get(key):
                raise ValueError(f"Stage-5 comparison/post-layout mismatch: {key}")
            physical_samples.append({"pattern": name, "column": col, "integer_sum": expected,
                                     "active_rows": sum(weights[row][col] != 0 and acts[row] != 0 for row in range(4)),
                                     "ternary_nonzero": sum(weights[row][col] != 0 for row in range(4)),
                                     "activation_x2": list(acts), "swing_v": _finite(measurements[key], key),
                                     "energy_j_for_pattern": energy,
                                     "delay_s": (_finite(measurements[key.replace("_diff", "_delay")], key + " delay")
                                                 if key.replace("_diff", "_delay") in job["delay_measurements"] else None)})
        for key in job["delay_measurements"]:
            delay_values.append(_finite(measurements[key], key))
    if len(physical_samples) != 16 or min(energies) < 0 or min(delay_values) < 0:
        raise ValueError("physical sample cardinality or energy/delay invalid")

    # One voltage-per-integer calibration, plus column-specific offsets/slopes.
    # This is a descriptive fit over four measured patterns, not a PVT fit.
    x = np.array([item["integer_sum"] for item in physical_samples], dtype=float)
    y = np.array([item["swing_v"] for item in physical_samples], dtype=float)
    global_gain = float(np.dot(x, y) / np.dot(x, x))
    if not 0 < global_gain < config.vdd:
        raise ValueError("invalid physical voltage-to-integer calibration")
    columns = []
    for col in range(4):
        subset = [item for item in physical_samples if item["column"] == col]
        cx = np.array([item["integer_sum"] for item in subset], dtype=float)
        cy = np.array([item["swing_v"] for item in subset], dtype=float)
        slope, intercept = np.linalg.lstsq(np.stack([cx, np.ones_like(cx)], axis=1), cy, rcond=None)[0]
        if slope <= 0:
            raise ValueError(f"nonmonotonic physical column {col}")
        columns.append({"column": col, "gain_v_per_integer": float(slope),
                        "offset_v": float(intercept), "fit_rmse_v": float(np.sqrt(np.mean((cy - slope * cx - intercept) ** 2))),
                        "measured_min_sum": int(min(cx)), "measured_max_sum": int(max(cx))})
    zero_swings = [abs(item["swing_v"]) for item in physical_samples if item["integer_sum"] == 0]
    nonzero_swings = [abs(item["swing_v"]) for item in physical_samples if item["integer_sum"] != 0]
    margin = min(nonzero_swings) - max(zero_swings)
    if margin <= 0:
        raise ValueError("measured zero/nonzero voltage margin is not positive")
    return {
        "format": "automx-cim-stage6-characterization-v1", "status": "PASS_TT_MODEL",
        "macro": CORE, "config_sha256": config.sha256,
        "pvt": {"corner": "tt", "vdd_v": config.vdd, "temperature_c": config.temperature_c,
                "coverage": "one measured point; other corners/voltages/temperatures uncharacterized"},
        "scope": "architectural TT-only estimate; passive core, no sense ADC or wrapper",
        "source_sha256": {"stage4_manifest": _digest(manifest_path), "stage4_receipts": stage4_hashes,
                          "stage5_summary": _digest(summary_path), "pex": pex_receipt["sha256"]},
        "stage4": stage4,
        "physical": {"samples": physical_samples, "patterns": pattern_summaries,
                     "global_gain_v_per_integer": global_gain,
                     "measured_activation_abs_x2_max": max(abs(a) for sample in physical_samples for a in sample["activation_x2"]),
                     "columns": columns, "energy_j_per_macro_job": dict(zip((j["name"] for j in macro["jobs"]), energies)),
                     "delay_s_max_measured": max(delay_values),
                     "energy_j_max_measured": max(energies),
                     "zero_nonzero_margin_v": margin,
                     "error_model": {"type": "per-column affine TT fit with global-gain linear decoder",
                                     "max_fit_rmse_v": max(item["fit_rmse_v"] for item in columns),
                                     "measured_patterns_per_column": 4}},
        "model_assumptions": ["linear fit of four measured macro patterns per column",
                              "voltage divided by measured global gain; ideal unquantized sense decoder",
                              "fit extrapolates outside measured integer-sum/code ranges and flags every such call",
                              "macro energy/latency upper estimates reuse maximum measured pattern; no wrapper cost"],
        "logical_tile": {"rows": 32, "cols": 8, "physical_rows": 4, "physical_cols": 4,
                         "macro_count": 16, "schedule": "eight row groups by two column groups"},
    }


@dataclass
class CIMMacroModel:
    """Apply TT fit to 4x4 base sums; retain the fixed-point oracle elsewhere."""

    characterization: dict[str, Any]
    extrapolated_columns: int = 0
    evaluated_columns: int = 0
    extrapolated_macro_codes: int = 0
    sum_outside_columns: int = 0
    code_outside_columns: int = 0
    max_abs_code_seen: int = 0

    def __post_init__(self) -> None:
        if self.characterization.get("format") != "automx-cim-stage6-characterization-v1" or self.characterization.get("status") != "PASS_TT_MODEL":
            raise ValueError("validated TT characterization required")

    def tile(self, act_x2: np.ndarray, ternary: np.ndarray) -> np.ndarray:
        act = np.asarray(act_x2, dtype=np.int64)
        weights = np.asarray(ternary, dtype=np.int64)
        if act.shape != (32,) or weights.shape != (32, 8) or not np.isin(weights, (-1, 0, 1)).all():
            raise ValueError("logical tile requires 32 signed E2M1 values and 32x8 ternary weights")
        if not np.isin(np.abs(act), (0, 1, 2, 3, 4, 6, 8, 12)).all():
            raise ValueError("activation is not signed E2M1 x2")
        output = np.zeros(8, dtype=float)
        gain = self.characterization["physical"]["global_gain_v_per_integer"]
        for row in range(0, 32, 4):
            for col in range(0, 8, 4):
                ideal = act[row:row+4] @ weights[row:row+4, col:col+4]
                self.max_abs_code_seen = max(self.max_abs_code_seen, int(np.max(np.abs(act[row:row+4]))))
                code_outside = np.any(np.abs(act[row:row+4]) > self.characterization["physical"]["measured_activation_abs_x2_max"])
                if code_outside:
                    self.extrapolated_macro_codes += 1
                for lane, value in enumerate(ideal):
                    fit = self.characterization["physical"]["columns"][lane]
                    self.evaluated_columns += 1
                    sum_outside = value < fit["measured_min_sum"] or value > fit["measured_max_sum"]
                    self.code_outside_columns += int(code_outside)
                    self.sum_outside_columns += int(sum_outside)
                    if code_outside or sum_outside:
                        self.extrapolated_columns += 1
                    voltage = fit["gain_v_per_integer"] * value + fit["offset_v"]
                    output[col+lane] += voltage / gain
        return output

    def project(self, token: np.ndarray, payload: QTEAProjection) -> np.ndarray:
        if payload.shape[0] != 32 or payload.shape[1] % 8 or payload.residual is not None or np.any(payload.beta) or not np.all(payload.col_v == 1):
            raise ValueError("Stage-6 physical model supports base-only, K=32, columns divisible by 8")
        activation = encode_mxfp4(token)
        oracle = fixed_mxfp4_qtea_projection(activation, payload).output.copy()
        act = activation.signed_magnitude_x2().reshape(32)
        scale = float(np.exp2(activation.scale_e8m0.astype(np.int16)[0] - 128))
        alpha_q = AutoMXFixedConfig().alpha.quantize(payload.alpha)[:, 0] / (1 << 12)
        for col in range(0, payload.shape[1], 8):
            weights = np.asarray(payload.ternary)[:, col:col+8]
            ideal = act @ weights
            modeled = self.tile(act, weights)
            oracle[col:col+8] += (modeled - ideal) * alpha_q[col:col+8] * scale
        return oracle


def evaluate_mha(stage1: Stage1Result, model: CIMMacroModel) -> dict[str, Any]:
    """Compare FP32, fixed-point ternary oracle, and TT macro surrogate."""
    payloads = stage1.payloads
    x = stage1.input_x
    q, k, v = (np.stack([model.project(token, payloads[name]) for token in x])
               for name in ("WQ", "WK", "WV"))
    provisional = mha_from_projections(q, k, v, np.eye(q.shape[1]), stage1.config.n_heads)
    output = np.stack([model.project(token, payloads["WO"]) for token in provisional.context])
    macro_count = (stage1.config.d_model // 8) * 16
    total_invocations = model.evaluated_columns // 4
    physical = model.characterization["physical"]
    return {
        "format": "automx-cim-stage6-mha-v1", "status": "PASS_TT_MODEL",
        "quantization_vs_fp32": error_metrics(stage1.fp32.output, stage1.quantized.output),
        "macro_model_vs_quantized": error_metrics(stage1.quantized.output, output),
        "macro_model_vs_fp32": error_metrics(stage1.fp32.output, output),
        "projection_metrics_vs_quantized": {name: error_metrics(getattr(stage1.quantized, name.lower()), value)
                                            for name, value in (("Q", q), ("K", k), ("V", v))},
        "macro_count_per_32x8_tile": 16,
        "macro_count_per_projection": macro_count,
        "evaluated_macro_invocations": total_invocations,
        "extrapolated_output_fraction": model.extrapolated_columns / max(1, model.evaluated_columns),
        "evaluated_output_columns": model.evaluated_columns,
        "extrapolated_output_columns": model.extrapolated_columns,
        "columns_with_unmeasured_e2m1_code": model.code_outside_columns,
        "columns_with_sum_outside_measured_range": model.sum_outside_columns,
        "maximum_absolute_e2m1_code_seen": model.max_abs_code_seen,
        "maximum_absolute_e2m1_code_measured_post_layout": physical["measured_activation_abs_x2_max"],
        "macro_invocations_with_unmeasured_code": model.extrapolated_macro_codes,
        "mha_coverage_status": "EXTRAPOLATED" if model.extrapolated_columns else "WITHIN_MEASURED_SUM_AND_CODE_RANGES",
        "energy_j_upper_proxy": total_invocations * physical["energy_j_max_measured"],
        "latency_s_serial_proxy_per_projection": 8 * physical["delay_s_max_measured"],
        "limitations": "TT-only passive-core architectural estimate; no ADC/wrapper/PVT validation",
    }


def write_stage6(root: str | Path, config: Sky130MHAConfig, stage1: Stage1Result) -> tuple[dict[str, Any], dict[str, Any]]:
    root = Path(root).resolve()
    characterization = build_characterization(root, config)
    model = CIMMacroModel(characterization)
    comparison = evaluate_mha(stage1, model)
    result_dir = root / "results/sky130"
    result_dir.mkdir(parents=True, exist_ok=True)
    char_path = result_dir / f"{CORE}_characterization.json"
    mha_path = result_dir / "stage6_mha_comparison.json"
    char_path.write_text(json.dumps(characterization, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    mha_path.write_text(json.dumps(comparison, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return characterization, comparison
