"""Representative real-waveform lessons; no new circuit simulations or performance claims."""

from __future__ import annotations

from dataclasses import asdict
import json
import math
from pathlib import Path
import re
import shutil

import matplotlib.pyplot as plt
import numpy as np

from comparator_atlas.spice import EVALUATION_START_S, Point, Trace, measure
import entry_tools as entry
import layout_evidence as physical

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / "evidence_traces" / "waveform_lab"
DEADLINES = (0.25, 0.35, 0.5, 0.75, 1.0, 2.0)
CALIBRATION_EXAMPLES = (
    ("schematic_untrimmed", "code_zero", "Wrong is not late: code zero"),
    ("schematic_calibrated", "local_boundary", "Same circuit and input: calibrated"),
)


def display_vectors(values: np.ndarray) -> dict[str, list[float]]:
    mask = (values[:, 0] >= EVALUATION_START_S - 0.2e-9) \
        & (values[:, 0] <= EVALUATION_START_S + 2.2e-9)
    selected = values[mask]
    if len(selected) < 10:
        raise ValueError("The retained waveform does not cover the teaching window")
    return {
        "time_ns": ((selected[:, 0] - EVALUATION_START_S) * 1e9).tolist(),
        "clock_v": selected[:, 1].tolist(),
        "qp_v": selected[:, 2].tolist(),
        "qn_v": selected[:, 3].tolist(),
    }


def make_sample(
    identifier: str, label: str, description: str, source_kind: str,
    path: Path, point: Point, run_id: str, provenance: dict,
) -> dict:
    with np.load(path, allow_pickle=False) as saved:
        values = saved["values"]
    trace = Trace(point, values, run_id, path.parent)
    observations = [asdict(measure(trace, deadline)) for deadline in DEADLINES]
    return {
        "id": identifier, "label": label, "description": description,
        "source_kind": source_kind, "point": asdict(point), "run_id": run_id,
        "waveform_path": path.relative_to(ROOT).as_posix(),
        "waveform_sha256": entry.digest(path),
        "provenance": provenance,
        "observations": observations,
        "plot": display_vectors(values),
    }


def verify_observation(actual: dict, recorded: dict) -> None:
    if actual.keys() != recorded.keys():
        raise RuntimeError("Teaching observation fields differ from the measurement contract")
    for key, expected in recorded.items():
        value = actual[key]
        if isinstance(expected, (float, int)) and not isinstance(expected, bool):
            if not isinstance(value, (float, int)) or not math.isclose(
                value, expected, rel_tol=1e-12, abs_tol=1e-12,
            ):
                raise RuntimeError(f"Teaching observation differs from the full waveform: {key}")
        elif value != expected:
            raise RuntimeError(f"Teaching observation differs from the full waveform: {key}")


def build() -> Path:
    schematic = entry.load_evidence()
    layout = physical.load_layout()
    frame = schematic["frame"]
    FOLDER.mkdir(parents=True, exist_ok=True)
    samples = []
    for identifier, policy, label in CALIBRATION_EXAMPLES:
        rows = frame[
            (frame.design_name == "baseline") & (frame.corner == "tt")
            & (frame.vdd_v == 1.8) & (frame.temperature_c == 27)
            & (frame.pair_skew == 0.04) & (frame.input_mv == -1)
            & (frame.deadline_ns == 1) & (frame.policy == policy)
        ]
        if len(rows) != 1:
            raise RuntimeError("A calibration teaching point is missing or duplicated")
        row = rows.iloc[0]
        if not re.fullmatch(r"[a-f0-9]{24}", row.run_id):
            raise RuntimeError("Invalid retained schematic run identity")
        source = ROOT / ".cache" / "spice" / row.run_id
        metadata = json.loads((source / "metadata.json").read_text())
        if entry.digest(source / "waveform.npz") != metadata["waveform_sha256"] \
                or entry.digest(source / "circuit.cir") != metadata["reproduction_deck_sha256"]:
            raise RuntimeError("Retained teaching-point waveform or netlist was changed")
        point = Point(**metadata["identity"]["point"])
        if point.design_name != row.design_name or point.trim_code != int(row.trim_code):
            raise RuntimeError("Retained waveform belongs to a different circuit/code")
        target = FOLDER / f"{identifier}-{row.run_id}.npz"
        if target.exists() and entry.digest(target) != metadata["waveform_sha256"]:
            raise RuntimeError("An existing teaching waveform differs; it was not overwritten")
        if not target.exists():
            shutil.copyfile(source / "waveform.npz", target)
        sample = make_sample(
            identifier, label,
            "The original 23-device schematic at TT / 1.8 V / 27 C, -1 mV input and deterministic "
            "+4%/-4% main-pair width stress. Only the physical trim code differs between the two "
            "calibration examples. This is not a foundry mismatch or layout result.",
            "schematic", target, point, row.run_id,
            {
                "reproduction_deck_sha256": metadata["reproduction_deck_sha256"],
                "ngspice_binary_sha256": metadata["identity"]["ngspice_binary_sha256"],
                "measurement_source_sha256": metadata["producer_provenance"]["measurement_source_sha256"],
                "pdk_revision": metadata["producer_provenance"]["pdk_revision"],
            },
        )
        selected = next(item for item in sample["observations"] if item["deadline_ns"] == 1)
        if selected["outcome"] != row.outcome \
                or not math.isclose(selected["core_energy_fj"], row.core_energy_fj, rel_tol=1e-12):
            raise RuntimeError("Teaching metrics disagree with the corrected published table")
        samples.append(sample)

    examples_folder = layout["snapshot"] / "trace-examples"
    examples = json.loads((examples_folder / "index.json").read_text())["examples"]
    for item in examples:
        run = examples_folder / item["run_id"]
        metadata = json.loads((run / "metadata.json").read_text())
        if metadata["mode"] != "rc" or metadata["status"] != "PASS":
            raise RuntimeError("A layout teaching trace lacks simulator integrity qualification")
        path = run / "waveform.npz"
        if entry.digest(path) != metadata["artifact_sha256"]["waveform.npz"]:
            raise RuntimeError("Layout teaching waveform changed")
        point = Point(**metadata["point"])
        condition = "tt" if point.corner == "tt" else "ss_cold" if point.temperature_c == -40 else "ss_hot"
        sign = "negative" if point.differential_v < 0 else "positive"
        sample = make_sample(
            f"layout_{condition}_{sign}",
            f"Extracted RC: {point.corner.upper()} / {point.temperature_c:g} C / "
            f"{1000 * point.differential_v:+g} mV",
            "The repaired 27-device extracted RC layout with nominal matched geometry, code zero, "
            "5 fF output loads and a 10 ns clock. The original 1 ns pilot remains not fully qualified; "
            "2 ns is post-hoc characterization of retained data, not a changed qualification.",
            "layout_rc", path, point, item["run_id"],
            {
                "netlist_sha256": metadata["physical_identity"]["netlist_sha256"],
                "ngspice_binary_sha256": metadata["physical_identity"]["ngspice_binary_sha256"],
                "layout_receipt_sha256": physical.RECEIPT_SHA256,
            },
        )
        if len(sample["observations"]) != len(metadata["measurements"]):
            raise RuntimeError("The physical teaching point lacks the original complete reporting windows")
        for observed, saved in zip(sample["observations"], metadata["measurements"]):
            verify_observation(observed, saved)
        samples.append(sample)
    if len(samples) != 8 or len({sample["id"] for sample in samples}) != 8:
        raise RuntimeError("The representative teaching set must contain exactly eight declared examples")
    data = {
        "schema": 1,
        "purpose": "Eight post-hoc educational examples from existing verified SPICE data, not a new benchmark.",
        "deadlines_ns": list(DEADLINES),
        "plot_window_ns": [-0.15, 2.15],
        "rail_thresholds_vdd": {"high": 0.8, "low": 0.2},
        "clock_period_ns": 10,
        "energy_window_ns": [20, 30],
        "sample_count": len(samples),
        "samples": samples,
        "new_physical_simulations": 0,
        "limitations": [
            "This teaching set does not contain every waveform in the full decision atlas.",
            "Example selection is illustrative and post-hoc; no new validation coverage is claimed.",
            "Changing the displayed deadline does not rerun SPICE or change the physical circuit.",
            "Core energy covers the entire recorded cycle, not only time before the selected deadline.",
            "Schematic width-stress calibration and nominal extracted-layout examples are different experiments.",
        ],
    }
    data_path = FOLDER / "waveform_lab.json"
    data_path.write_text(json.dumps(data, separators=(",", ":"), allow_nan=False) + "\n", encoding="utf-8")
    manifest = {
        "status": "verified_retained_waveform_teaching_set",
        "generator_sha256": entry.digest(Path(__file__)),
        "measurement_source_sha256": entry.digest(ROOT / "comparator_atlas" / "spice.py"),
        "source_selection_sha256": entry.digest(entry.STUDY / "verified_measurements.csv"),
        "layout_receipt_sha256": physical.RECEIPT_SHA256,
        "source_waveform_sha256": {
            sample["waveform_path"]: sample["waveform_sha256"] for sample in samples
        },
        "data_sha256": entry.digest(data_path),
        "new_physical_simulations": 0,
        "posthoc_educational_selection": True,
    }
    (FOLDER / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Prepared eight exact saved-waveform lessons, {sum(len(s['plot']['time_ns']) for s in samples)} displayed samples; no SPICE executed.")
    return data_path


def load_lab() -> dict:
    manifest = json.loads((FOLDER / "manifest.json").read_text(encoding="utf-8"))
    if manifest["generator_sha256"] != entry.digest(Path(__file__)):
        raise RuntimeError("Waveform-lab source changed; regenerate the presentation from the same raw evidence")
    if manifest["measurement_source_sha256"] != entry.digest(ROOT / "comparator_atlas" / "spice.py"):
        raise RuntimeError("The waveform lab uses a different measurement contract")
    if manifest["source_selection_sha256"] != entry.digest(entry.STUDY / "verified_measurements.csv"):
        raise RuntimeError("The published schematic table changed after selecting the teaching examples")
    if manifest["layout_receipt_sha256"] != physical.RECEIPT_SHA256:
        raise RuntimeError("The physical evidence reference changed")
    path = FOLDER / "waveform_lab.json"
    if entry.digest(path) != manifest["data_sha256"]:
        raise RuntimeError("The waveform teaching data changed")
    entry.verify_files(ROOT, manifest["source_waveform_sha256"])
    data = json.loads(path.read_text(encoding="utf-8"))
    if data["sample_count"] != 8 or len(data["samples"]) != 8 or data["deadlines_ns"] != list(DEADLINES):
        raise RuntimeError("Waveform lab shape or reporting windows are not the declared set")
    for sample in data["samples"]:
        raw = entry.artifact_path(ROOT, sample["waveform_path"])
        with np.load(raw, allow_pickle=False) as saved:
            values = saved["values"]
        trace = Trace(Point(**sample["point"]), values, sample["run_id"], raw.parent)
        recomputed = [asdict(measure(trace, deadline)) for deadline in DEADLINES]
        if len(recomputed) != len(sample["observations"]):
            raise RuntimeError("Teaching data lost a declared deadline observation")
        for actual, expected in zip(recomputed, sample["observations"]):
            verify_observation(actual, expected)
        if display_vectors(values) != sample["plot"]:
            raise RuntimeError("The displayed waveform disagrees with the original full trace")
    return data


def inspect_sample(data: dict, identifier: str, deadline_ns: float) -> tuple[dict, dict]:
    if deadline_ns not in data["deadlines_ns"]:
        raise ValueError("Select one of the six already reported decision deadlines")
    matches = [sample for sample in data["samples"] if sample["id"] == identifier]
    if len(matches) != 1:
        raise ValueError("Unknown or ambiguous waveform teaching example")
    sample = matches[0]
    reading = next(item for item in sample["observations"] if item["deadline_ns"] == deadline_ns)
    return sample, reading


def figure(data: dict, identifier: str, deadline_ns: float):
    sample, reading = inspect_sample(data, identifier, deadline_ns)
    plot = sample["plot"]
    point = sample["point"]
    vdd = point["vdd_v"]
    fig, ax = plt.subplots(figsize=(10, 4.3))
    ax.plot(plot["time_ns"], plot["qp_v"], label="Q+", color="#009c8d")
    ax.plot(plot["time_ns"], plot["qn_v"], label="Q-", color="#cc5967")
    ax.plot(plot["time_ns"], plot["clock_v"], label="Clock", color="#9aaabd", alpha=0.6)
    for fraction in (0.2, 0.8):
        ax.axhline(fraction * vdd, color="#6d7d92", linestyle=":", linewidth=1)
    ax.axvline(deadline_ns, color="#c58b25", linestyle="--", label=f"Deadline {deadline_ns:g} ns")
    ax.plot(deadline_ns, reading["qp_at_deadline_v"], "o", color="#009c8d")
    ax.plot(deadline_ns, reading["qn_at_deadline_v"], "o", color="#cc5967")
    ax.set(xlim=data["plot_window_ns"], xlabel="Time after evaluation clock midpoint (ns)",
           ylabel="Voltage (V)",
           title=f"{sample['label']} | {reading['outcome'].upper()} at {deadline_ns:g} ns")
    ax.legend(ncol=4, fontsize=8, loc="upper right")
    ax.grid(alpha=0.15)
    fig.tight_layout()
    return fig, {
        "outcome": reading["outcome"],
        "deadline_ns": deadline_ns,
        "expected_positive": point["differential_v"] > 0,
        "Q+_at_deadline_V": reading["qp_at_deadline_v"],
        "Q-_at_deadline_V": reading["qn_at_deadline_v"],
        "high_threshold_V": 0.8 * vdd,
        "low_threshold_V": 0.2 * vdd,
        "sampled_decision_time_ns": reading["decision_time_ns"],
        "full_cycle_core_energy_fJ": reading["core_energy_fj"],
        "source_kind": sample["source_kind"],
        "run_id": sample["run_id"],
    }


if __name__ == "__main__":
    build()
