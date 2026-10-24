"""Portable review and reproduction helpers for the public Code-a-Chip entry."""

from dataclasses import asdict
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from comparator_atlas.designs import get_design
from comparator_atlas.spice import Point, Simulator, Trace, measure
from comparator_atlas.stress import apply_refinements

ROOT = Path(__file__).resolve().parent
STUDY = ROOT / "results" / "study"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def artifact_path(root: Path, name: str) -> Path:
    relative = PurePosixPath(name.replace("\\", "/"))
    if relative.is_absolute() or ".." in relative.parts or any(":" in part for part in relative.parts):
        raise ValueError(f"Artifact path must stay inside its declared root: {name}")
    resolved = root.joinpath(*relative.parts).resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise ValueError(f"Artifact path escapes its declared root: {name}")
    return resolved


def verify_files(root: Path, hashes: dict[str, str]) -> None:
    for name, expected in hashes.items():
        path = artifact_path(root, name)
        if not path.is_file() or digest(path) != expected:
            raise RuntimeError(f"Missing or changed evidence: {name}")


def verify_manifest(name: str, folder: Path = STUDY) -> dict:
    manifest = json.loads((folder / name).read_text(encoding="utf-8"))
    if manifest["status"] != "complete":
        raise RuntimeError(f"Evidence is not complete: {name}")
    verify_files(ROOT, manifest["source_hashes"])
    verify_files(folder, manifest["artifact_sha256"])
    if manifest["protocol_sha256"] != digest(folder / "protocol.json"):
        raise RuntimeError(f"The recorded protocol changed: {name}")
    return manifest


def load_evidence() -> dict:
    optimization = verify_manifest("optimization_manifest.json")
    validation = verify_manifest("validation_manifest.json")
    stress = verify_manifest("stress_manifest.json")
    if stress["stress_source_sha256"] != digest(ROOT / "comparator_atlas" / "stress.py"):
        raise RuntimeError("Numerical correction source changed after the recorded study")
    if not stress["numerical_passed"]:
        raise RuntimeError("The submitted study still has unresolved numerical sensitivity")
    if validation["selection_sha256"] != digest(STUDY / "selection.json"):
        raise RuntimeError("Circuit selection changed after validation")
    if stress["validation_measurements_sha256"] != digest(STUDY / "validation_measurements.csv"):
        raise RuntimeError("Numerical checks refer to different initial measurements")
    selection = json.loads((STUDY / "selection.json").read_text(encoding="utf-8"))
    initial = pd.read_csv(STUDY / "validation_measurements.csv")
    updates = pd.read_csv(STUDY / "measurement_refinements.csv")
    verified = pd.read_csv(STUDY / "verified_measurements.csv")
    computed = apply_refinements(initial, updates)
    columns = [
        "design_name", "case_id", "policy", "input_mv", "deadline_ns",
        "run_id", "outcome", "core_energy_fj", "decision_time_ns",
    ]
    pd.testing.assert_frame_equal(
        verified[columns], computed[columns], check_dtype=False,
        check_exact=False, rtol=1e-12, atol=1e-12,
    )
    if len(verified) != 30576 or len(verified) != validation["row_count"]:
        raise RuntimeError("The published two-circuit grid is incomplete")
    key = ["design_name", "case_id", "policy", "input_mv", "deadline_ns"]
    if verified.duplicated(key).any():
        raise RuntimeError("Duplicated rows would bias the experiment")
    control_dir = STUDY / "professional"
    control = verify_manifest("manifest.json", control_dir)
    if not control["numerically_stable"]:
        raise RuntimeError("The energy-efficient control is numerically unresolved")
    if control["reference_validation_artifact_sha256"] != validation["artifact_sha256"]:
        raise RuntimeError("The control comparison refers to a different original validation")
    efficient = pd.read_csv(control_dir / "measurements.csv")
    if len(efficient) != 49 * 2 * 13 * 6 or len(efficient) != control["row_count"]:
        raise RuntimeError("The energy-efficient control grid is incomplete")
    if efficient.duplicated(key).any():
        raise RuntimeError("The energy-efficient control contains duplicate observations")
    combined = pd.concat([verified, efficient], ignore_index=True)
    available = combined[combined.policy_available]
    unavailable = combined[~combined.policy_available]
    if available.reset_ok.isna().any() or not available.reset_ok.all() \
            or available.run_id.isna().any() or available.core_energy_fj.isna().any():
        raise RuntimeError("Executed observations are missing required evidence")
    if unavailable.run_id.notna().any() or unavailable.core_energy_fj.notna().any():
        raise RuntimeError("Unavailable calibration was replaced by invented results")
    metadata = json.loads((ROOT / "entry_metadata.json").read_text(encoding="utf-8"))
    return {
        "frame": combined, "selection": selection, "metadata": metadata,
        "validation": validation, "optimization": optimization, "stress": stress,
        "control": control,
        "calibration": json.loads((STUDY / "validation_calibration.json").read_text()),
        "control_calibration": json.loads((control_dir / "calibration.json").read_text()),
        "operating": pd.read_csv(STUDY / "operating_stress.csv"),
    }


def summary(evidence: dict, minimum_mv: float = 1.0, deadline_ns: float = 1.0) -> pd.DataFrame:
    frame = evidence["frame"]
    selected = frame[
        (frame.policy == "local_boundary") & (frame.deadline_ns == deadline_ns)
        & (frame.input_mv != 0) & (frame.input_mv.abs() >= minimum_mv)
    ].copy()
    if selected.empty:
        raise ValueError("The requested scoring band has no measured observations")
    selected["correct"] = selected.outcome == "correct"
    rows = []
    for name, part in selected.groupby("design_name", sort=False):
        per_case = part.groupby("case_id").correct.mean()
        rows.append({
            "design": name, "correct": int(part.correct.sum()), "points": len(part),
            "grid_coverage": float(part.correct.mean()),
            "fully_passing_conditions": int((per_case == 1).sum()),
            "conditions": len(per_case),
            "worst_condition_coverage": float(per_case.min()),
            "mean_core_energy_fj": float(part.core_energy_fj.mean()),
            "simulated_points": int(part.core_energy_fj.notna().sum()),
            "gate_area_proxy_um2": get_design(name).gate_area_um2,
        })
    return pd.DataFrame(rows).set_index("design")


def sampled_envelope(evidence: dict) -> pd.DataFrame:
    rows = []
    for minimum in (0.25, 0.5, 1.0, 3.0, 10.0, 30.0):
        table = summary(evidence, minimum)
        for name, values in table.iterrows():
            rows.append({
                "design": name, "minimum_abs_input_mv": minimum,
                "deadline_ns": 1.0, "correct": int(values.correct),
                "points": int(values.points),
                "all_sampled_conditions_pass": values.correct == values.points,
                "worst_condition_coverage": values.worst_condition_coverage,
            })
    return pd.DataFrame(rows)


def operating_summary(evidence: dict) -> pd.DataFrame:
    frame = evidence["operating"]
    selected = frame[frame.deadline_ns == 1.0].copy()
    selected["correct"] = selected.outcome == "correct"
    return selected.groupby(["design_name", "stress"], sort=False).agg(
        points=("correct", "size"), correct=("correct", "sum"),
        peak_differential_input_error_mv=("max_differential_input_error_mv", "max"),
    )


def calibration_workload(evidence: dict) -> pd.DataFrame:
    rows = []
    for report in evidence["calibration"]:
        calibration = report["local"]
        count = len(calibration["probe_run_ids"])
        rows.append({
            "design": report["design_name"], "case": report["case_id"],
            "distinct_probe_count": count,
            "simulated_transient_duration_ns": 30 * count,
        })
    for report in evidence["control_calibration"]:
        accounting = report["calibration_accounting"]
        rows.append({
            "design": report["point"]["design_name"], "case": report["case_id"],
            "distinct_probe_count": accounting["distinct_probe_count"],
            "simulated_transient_duration_ns": accounting["simulated_transient_duration_ns"],
        })
    frame = pd.DataFrame(rows)
    return frame.groupby("design", sort=False).agg(
        minimum_distinct_probes=("distinct_probe_count", "min"),
        maximum_distinct_probes=("distinct_probe_count", "max"),
        median_distinct_probes=("distinct_probe_count", "median"),
        maximum_offline_simulated_duration_ns=("simulated_transient_duration_ns", "max"),
    )


def tradeoff_figure(evidence: dict):
    colors = {"baseline": "#778ba4", "lvt_base_3b": "#e4a338", "lvt_balanced_4b": "#009e91"}
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    for minimum, marker in ((1.0, "o"), (3.0, "s")):
        table = summary(evidence, minimum)
        for name, row in table.iterrows():
            axes[0].scatter(row.mean_core_energy_fj, 100 * row.grid_coverage, s=100,
                            marker=marker, color=colors[name],
                            label=f"{name}; min input {minimum:g} mV")
    frame = sampled_envelope(evidence)
    for name, part in frame.groupby("design", sort=False):
        axes[1].plot(part.minimum_abs_input_mv, 100 * part.correct / part.points,
                     "o-", label=name, color=colors[name])
    axes[0].set(xlabel="Mean core-VDD energy (fJ/cycle)", ylabel="Correct grid points (%)",
                title="Same local policy and 1 ns deadline")
    axes[1].set(xlabel="Minimum absolute sampled input (mV)", ylabel="Correct grid points (%)",
                title="Sampled operating envelope, not a continuous guarantee")
    axes[1].set_xscale("log")
    for ax in axes:
        ax.grid(alpha=0.2)
        ax.legend(fontsize=7)
    fig.tight_layout()
    return fig


def review_waveforms() -> tuple[pd.DataFrame, object]:
    folder = ROOT / "evidence_traces"
    manifest = json.loads((folder / "manifest.json").read_text())
    verify_files(folder, manifest["artifact_sha256"])
    records = manifest["traces"]
    if not records:
        raise RuntimeError("The entry has no actual waveform evidence")
    fig, axes = plt.subplots(len(records), 1, figsize=(10, 2.3 * len(records)), squeeze=False)
    metrics = []
    for ax, record in zip(axes[:, 0], records):
        with np.load(folder / record["file"], allow_pickle=False) as saved:
            values = saved["values"]
        point = Point(**record["point"])
        trace = Trace(point, values, record["run_id"], folder)
        measured = measure(trace, 1.0)
        metrics.append({"design": point.design_name, "input_mv": point.differential_v * 1000,
                        "run_id": trace.run_id, **asdict(measured)})
        relative_time = (values[:, 0] - 22.025e-9) * 1e9
        mask = (relative_time >= -0.1) & (relative_time <= 1.5)
        ax.plot(relative_time[mask], values[mask, 2], label="Q+", color="#009e91")
        ax.plot(relative_time[mask], values[mask, 3], label="Q-", color="#dd5266")
        ax.axvline(1, color="#e4a338", linestyle="--")
        ax.set(title=f"{point.design_name}: SS / 1.62 V / -40 C / {point.differential_v * 1000:g} mV",
               ylabel="Voltage (V)")
        ax.legend(fontsize=8)
    axes[-1, 0].set_xlabel("Time after evaluation clock midpoint (ns)")
    fig.tight_layout()
    return pd.DataFrame(metrics), fig


def live_spice_smoke() -> pd.DataFrame:
    subprocess.run([sys.executable, str(ROOT / "scripts" / "setup_models.py")], check=True)
    simulator = Simulator(ROOT / ".cache" / "review_smoke", workers=1)
    records = json.loads((ROOT / "evidence_traces" / "manifest.json").read_text())["traces"]
    rows = []
    for record in records:
        point = Point(**record["point"])
        trace = simulator.run(point)
        measured = measure(trace, 1.0)
        rows.append({
            "design": point.design_name, "input_mv": point.differential_v * 1000,
            "simulator_version": simulator.version, **asdict(measured),
        })
    return pd.DataFrame(rows)


def full_reproduction() -> None:
    # Full simulation requires the documented toolchain; review mode needs no simulator.
    for stage in ("optimize", "study", "stress"):
        subprocess.run([sys.executable, "-m", "comparator_atlas", stage], cwd=ROOT, check=True)
    subprocess.run([sys.executable, "-m", "comparator_atlas.professional_audit"], cwd=ROOT, check=True)
    subprocess.run([sys.executable, "-m", "presentation.waveform_lab"], cwd=ROOT, check=True)
