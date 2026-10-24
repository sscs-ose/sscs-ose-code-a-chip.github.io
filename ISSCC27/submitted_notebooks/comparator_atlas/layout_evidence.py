"""Portable review of the actual layout addendum, including its failed 1 ns gate."""

from __future__ import annotations

from dataclasses import asdict
from itertools import product
import json
import math
from pathlib import Path
import re
import struct

import matplotlib.pyplot as plt
from matplotlib.collections import PatchCollection
from matplotlib.patches import Polygon
import numpy as np
import pandas as pd

from comparator_atlas.spice import Point, Trace, measure
from entry_tools import artifact_path, digest, verify_files

ROOT = Path(__file__).resolve().parent
LAYOUT = ROOT / "layout_compact_repair"
RECEIPT_SHA256 = "ca6042d02ae0d315caf9b5f8e1f7db0a0fdb29f5115fcb7832473a9dd488d490"
MODES = ("schematic", "lvs", "c", "rc")
LABELS = {"schematic": "Schematic", "lvs": "Connectivity only", "c": "C-only", "rc": "Distributed RC"}
PORTS = ("vinp", "vinn", "clk", "vdd", "vss", "qp", "qn",
         "tp0", "tp1", "tp2", "tp3", "tn0", "tn1", "tn2", "tn3")


def snapshot_hashes(text: str) -> dict[str, str]:
    hashes = {}
    for line in text.splitlines():
        matched = re.fullmatch(r"([a-f0-9]{64})  (.+)", line)
        if matched is None:
            raise ValueError("Malformed layout snapshot checksum record")
        expected, name = matched.groups()
        if name in hashes:
            raise ValueError("Duplicate layout snapshot checksum record")
        hashes[name] = expected
    return hashes


def circuit_guide_path() -> Path:
    directory = ROOT / "results" / "presentation"
    manifest = json.loads((directory / "circuit_guide_manifest.json").read_text())
    if manifest["source_sha256"] != digest(ROOT / "results" / "study" / "selected_circuit.spice"):
        raise RuntimeError("Circuit guide is based on a different electrical source")
    verify_files(directory, manifest["artifact_sha256"])
    if len(manifest["device_inventory"]) != 27:
        raise RuntimeError("Circuit guide has an incomplete device inventory")
    return directory / "circuit_guide.png"


def validate_measurements(frame: pd.DataFrame, receipt: dict) -> None:
    conditions = [tuple(condition) for condition in receipt["protocol"]["sampled_conditions"]]
    inputs = receipt["protocol"]["stimulus"]["differentials_mv"]
    keys = ["corner", "vdd_v", "temperature_c", "mode", "differential_mv"]
    expected = {(*condition, mode, value) for condition, mode, value in product(conditions, MODES, inputs)}
    if len(frame) != 80 or frame.duplicated(keys).any() or set(frame[keys].itertuples(index=False, name=None)) != expected:
        raise ValueError("Layout measurements do not cover exactly the declared 80-point four-mode grid")
    for field, required in (("pair_skew", 0), ("trim_code", 0), ("external_load_ff_each", 5), ("max_step_ps", 5)):
        if not (frame[field] == required).all():
            raise ValueError(f"A layout measurement changed the fixed experiment: {field}")
    for field in ("numerically_qualified", "reset_ok", "retained_10_to_5ps_agree_at_2ns"):
        if frame[field].isna().any() or not frame[field].eq(True).all():
            raise ValueError(f"Missing layout evidence qualification: {field}")
    if not np.isfinite(frame.core_energy_fj).all() or not (frame.core_energy_fj > 0).all():
        raise ValueError("Layout energy must be finite measured core-rail energy")
    if not frame.outcome_at_3_5ns.eq("not_evaluated").all():
        raise ValueError("This addendum does not contain a 3.5 ns characterization")
    for deadline in (1, 2):
        outcome = frame[f"outcome_at_{deadline}ns"]
        decisions = frame[f"decision_at_{deadline}ns"]
        latencies = frame[f"latency_at_{deadline}ns_ns"]
        if not outcome.isin(("correct", "wrong", "unresolved")).all():
            raise ValueError("Unknown layout outcome label")
        resolved = outcome != "unresolved"
        if decisions[~resolved].ne(0).any() or latencies[~resolved].notna().any():
            raise ValueError("Unresolved layout rows must not have an invented decision or latency")
        if not decisions[resolved].isin((-1, 1)).all() or latencies[resolved].isna().any():
            raise ValueError("Resolved layout rows require actual signed decisions and latencies")
        if not latencies[resolved].between(0, deadline + 1e-10).all():
            raise ValueError("Layout latency exceeds its own reporting window")
        expected_sign = np.sign(frame.differential_mv)
        if not ((decisions == expected_sign) == (outcome == "correct"))[resolved].all():
            raise ValueError("Layout correctness does not match the external differential input")


def load_layout() -> dict:
    receipt_path = LAYOUT / "verification-receipt.json"
    if digest(receipt_path) != RECEIPT_SHA256:
        raise RuntimeError("The sealed layout receipt changed; review a new release explicitly")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    snapshot = artifact_path(LAYOUT, receipt["evidence"]["native_snapshot"])
    manifest = snapshot / "snapshot.sha256"
    if digest(manifest) != receipt["evidence"]["snapshot_manifest_sha256"]:
        raise RuntimeError("The layout snapshot manifest changed")
    hashes = snapshot_hashes(manifest.read_text(encoding="utf-8"))
    if len(hashes) != receipt["evidence"]["snapshot_files"]:
        raise RuntimeError("The layout snapshot is incomplete")
    verify_files(snapshot, hashes)
    verify_files(snapshot, receipt["evidence"]["native_sha256"])
    physical = receipt["physical"]
    if (physical["pass"], physical["fail"], physical["skip"]) != (17, 0, 0) \
            or physical["full_named_drc_errors"] != 0 or physical["positive_lvs"] != "pass":
        raise RuntimeError("The layout does not have the recorded DRC/LVS qualification")
    if physical["native_devices"] != 27 or tuple(receipt["protocol"]["ordered_ports"]) != PORTS:
        raise RuntimeError("The actual comparator device or port contract changed")
    if set(physical["negative_lvs"]) != {"connection", "bulk", "width", "SVT_for_LVT"}:
        raise RuntimeError("The independent LVS negative controls are incomplete")
    provenance = receipt["actual_tools_and_models"]["simulation_provenance"]
    if provenance["measurement_source_sha256"] != digest(ROOT / "comparator_atlas" / "spice.py"):
        raise RuntimeError("The published measurement code changed after this layout experiment")
    if receipt["qualification"]["original_five_condition_pilot_qualified"] is not False:
        raise RuntimeError("Do not relabel the original 1 ns pilot as a qualification pass")
    frame = pd.read_csv(snapshot / "matched-metrics.csv")
    validate_measurements(frame, receipt)
    primary = json.loads((snapshot / "matched-primary-results.json").read_text())
    windows = json.loads((snapshot / "retained-window-characterization.json").read_text())
    if len(primary) != 80 or len(windows["measurements"]) != 80:
        raise RuntimeError("The source measurements do not match the declared observation count")
    by_run = {row["run_id"]: row for row in primary}
    window_by_run = {row["run_id"]: row for row in windows["measurements"]}
    if len(by_run) != 80 or len(window_by_run) != 80:
        raise RuntimeError("Duplicate source observations would bias the layout evidence")
    for row in frame.itertuples():
        original = by_run[row.run_id]
        later = window_by_run[row.run_id]
        if original["outcome"] != row.outcome_at_1ns \
                or later["two_ns_measurement"]["outcome"] != row.outcome_at_2ns:
            raise RuntimeError("Layout table outcomes differ from the actual source measurements")
        if original["condition"] != [row.corner, row.vdd_v, row.temperature_c] or original["mode"] != row.mode:
            raise RuntimeError("A layout table row was assigned to the wrong physical point")
        for actual, expected in (
            (row.core_energy_fj, original["core_energy_fj"]),
            (row.latency_at_2ns_ns, later["two_ns_measurement"]["decision_time_ns"]),
        ):
            if not math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12):
                raise RuntimeError("Layout table values differ from measured waveform values")
    return {"receipt": receipt, "snapshot": snapshot, "frame": frame, "windows": windows, "hashes": hashes}


def deadline_summary(evidence: dict) -> pd.DataFrame:
    rows = []
    frame = evidence["frame"]
    for mode in MODES:
        selected = frame[frame["mode"] == mode]
        for deadline in (1, 2):
            outcomes = selected[f"outcome_at_{deadline}ns"]
            rows.append({
                "mode": LABELS[mode], "deadline_ns": deadline, "sampled_points": len(selected),
                "correct": int(outcomes.eq("correct").sum()),
                "wrong": int(outcomes.eq("wrong").sum()),
                "unresolved": int(outcomes.eq("unresolved").sum()),
                "scope": "original pilot" if deadline == 1 else "post-hoc retained-window characterization",
            })
    return pd.DataFrame(rows)


def matched_tt_comparison(evidence: dict) -> pd.DataFrame:
    frame, receipt = evidence["frame"], evidence["receipt"]
    values = frame[(frame.corner == "tt") & (frame.vdd_v == 1.8) & (frame.temperature_c == 27)
                   & (frame.differential_mv.abs() == 3)]
    rows = []
    for mode in MODES:
        selected = values[values["mode"] == mode]
        if len(selected) != 2 or not selected.outcome_at_1ns.eq("correct").all():
            raise RuntimeError("The matched TT comparison requires both actual signed inputs")
        rows.append({
            "implementation": "Schematic" if mode == "schematic" else "Repaired " + LABELS[mode],
            "mean_delay_ns": float(selected.latency_at_1ns_ns.mean()),
            "mean_core_energy_fj": float(selected.core_energy_fj.mean()),
            "matched_signed_points": len(selected),
        })
    previous = [
        row for row in receipt["matched_old_legal_and_repaired_results"]
        if row["reference_layout"] == "balanced_legal_r1" and row["condition"] == ["tt", 1.8, 27]
        and row["mode"] == "rc" and abs(row["differential_mv"]) == 3
    ]
    if len(previous) != 2 or any(not row["same_timestep"] for row in previous):
        raise RuntimeError("The old-versus-new layout comparison is not timestep matched")
    rows.insert(-1, {
        "implementation": "Previous balanced RC",
        "mean_delay_ns": sum(row["reference_latency_ns"] for row in previous) / 2,
        "mean_core_energy_fj": sum(row["reference_energy_fj"] for row in previous) / 2,
        "matched_signed_points": 2,
    })
    return pd.DataFrame(rows)


def geometry_summary(evidence: dict) -> pd.DataFrame:
    return pd.DataFrame([{
        "layout": row["layout"],
        "bbox_area_um2": row["geometry"]["bbox"]["bbox_area_um2"],
        "m2_union_area_um2": row["geometry"]["measured_metal_union_area_um2"]["metal2"],
        "rc_resistors": row["passives"]["rc"]["resistors"]["count"],
        "rc_capacitors": row["passives"]["rc"]["capacitors"]["count"],
        "listed_rc_capacitance_ff": row["passives"]["rc"]["capacitors"]["sum"] * 1e15,
        "drc_errors": row["drc_errors"],
        "lvs_and_negative_controls": row["independent_lvs_and_four_negatives"],
    } for row in evidence["receipt"]["legal_layout_comparison"]])


def gds_real8(data: bytes) -> float:
    if len(data) != 8:
        raise ValueError("Invalid eight-byte GDS real")
    # The sealed extractor uses Python 3.12; review also supports Python 3.10.
    mantissa = int.from_bytes(data[1:], byteorder="big") / 2**56
    return (-1 if data[0] & 128 else 1) * 16.0 ** ((data[0] & 127) - 64) * mantissa


def gds_polygons(data: bytes) -> dict[tuple[int, int], list[list[tuple[float, float]]]]:
    layers = {}
    offset, scale, active, layer, datatype, points = 0, None, False, None, None, None
    while offset < len(data):
        if offset + 4 > len(data):
            raise ValueError("Truncated GDS record")
        size, kind, _ = struct.unpack_from(">HBB", data, offset)
        if size < 4 or offset + size > len(data):
            raise ValueError("Truncated GDS payload")
        payload = data[offset + 4:offset + size]
        if kind == 3:
            if len(payload) != 16 or scale is not None:
                raise ValueError("Ambiguous GDS units")
            scale = gds_real8(payload[8:16]) * 1e6
            if not math.isclose(scale, 0.001, rel_tol=0, abs_tol=1e-12):
                raise ValueError("Unexpected GDS database units")
        elif kind == 8:
            if active:
                raise ValueError("Nested GDS boundary")
            active, layer, datatype, points = True, None, None, None
        elif kind in (9, 10, 11):
            raise ValueError("This audited renderer accepts flat boundaries, not paths or hierarchy")
        elif kind == 12:
            active = False
        elif kind == 13 and active:
            layer = struct.unpack(">h", payload)[0]
        elif kind == 14 and active:
            datatype = struct.unpack(">h", payload)[0]
        elif kind == 16 and active:
            if scale is None or points is not None or len(payload) % 8:
                raise ValueError("Invalid or unscaled GDS boundary coordinates")
            points = [(x * scale, y * scale) for x, y in struct.iter_unpack(">ii", payload)]
        elif kind == 17 and active:
            if layer is None or datatype is None or points is None or len(points) < 4 or points[0] != points[-1]:
                raise ValueError("Incomplete or open GDS boundary")
            layers.setdefault((layer, datatype), []).append(points)
            active = False
        offset += size
    if active or scale is None or not {(65, 20), (66, 20), (68, 20), (69, 20), (70, 20), (125, 44)} <= layers.keys():
        raise ValueError("Required actual GDS layers are missing or incomplete")
    return layers


def layout_figure(evidence: dict):
    path = evidence["snapshot"] / "atlas.gds"
    layers = gds_polygons(path.read_bytes())
    points = [point for polygons in layers.values() for polygon in polygons for point in polygon]
    bounds = [min(point[0] for point in points), min(point[1] for point in points),
              max(point[0] for point in points), max(point[1] for point in points)]
    if not np.allclose(bounds, evidence["receipt"]["geometry"]["bbox"]["bounds_um"], rtol=0, atol=1e-9):
        raise RuntimeError("Rendered geometry bounds differ from the audited GDS bounds")
    colors = {
        (64, 20): "#e7cce8", (65, 20): "#65b184", (65, 44): "#bb976b",
        (66, 20): "#e17177", (67, 20): "#f0cb65", (68, 20): "#a5afd4",
        (69, 20): "#41b3ca", (70, 20): "#248e86", (71, 20): "#db9f33",
        (125, 44): "#9251a2",
    }
    order = {64: 0, 65: 2, 66: 3, 67: 4, 68: 5, 69: 6, 70: 7, 71: 8, 125: 2.5}
    fig = plt.figure(figsize=(13, 5.0))
    overview = fig.add_axes([0.06, 0.61, 0.90, 0.30])
    core = fig.add_axes([0.06, 0.12, 0.57, 0.36])
    repair = fig.add_axes([0.71, 0.12, 0.25, 0.36])
    for ax in (overview, core, repair):
        for layer, polygons in sorted(layers.items(), key=lambda item: order.get(item[0][0], 1)):
            patches = [Polygon(points, closed=True) for points in polygons]
            ax.add_collection(PatchCollection(
                patches, facecolor=colors.get(layer, "#c7cbd0"), edgecolor="none",
                alpha=0.8 if layer[1] == 20 else 0.6,
            ))
        ax.set_aspect("equal")
        ax.tick_params(labelsize=8)
        ax.set_xlabel("x (um)", fontsize=9)
        ax.set_ylabel("y (um)", fontsize=9)
    overview.set(xlim=(bounds[0] - 1, bounds[2] + 1), ylim=(bounds[1] - 0.3, bounds[3] + 0.3))
    overview.set_title("Actual repaired GDS geometry | 129.6 x 17.03 um | full DRC 0, LVS + negative controls passed",
                       fontsize=12, weight="bold")
    core.set(xlim=(-10, 10), ylim=(-2.3, 4.2))
    core.set_title("Matched input / latch / tail region", fontsize=10)
    repair.set(xlim=(20.5, 21.9), ylim=(-2.2, 0.0))
    repair.set_title("One real PFET-body M2 bridge", fontsize=10)
    fig.text(0.06, 0.015,
             "Rendered from the hash-checked native layout, not an illustrative floorplan. "
             "Geometric checks do not imply 1 ns performance or foundry signoff.",
             fontsize=8, color="#63758b")
    return fig


def deadline_figure(evidence: dict):
    frame = evidence["frame"]
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.1), sharey=True)
    conditions = evidence["receipt"]["protocol"]["sampled_conditions"]
    labels = [f"{corner.upper()}\n{vdd:g} V / {temperature:g} C" for corner, vdd, temperature in conditions]
    for ax, deadline in zip(axes, (1, 2)):
        for index, mode in enumerate(MODES):
            percentages = []
            for corner, vdd, temperature in conditions:
                rows = frame[(frame.corner == corner) & (frame.vdd_v == vdd)
                             & (frame.temperature_c == temperature) & (frame["mode"] == mode)]
                percentages.append(100 * rows[f"outcome_at_{deadline}ns"].eq("correct").mean())
            ax.bar(np.arange(5) + (index - 1.5) * 0.18, percentages, width=0.18,
                   label=LABELS[mode], color=("#a0aec0", "#718096", "#e0ad54", "#009c8d")[index])
        ax.set_xticks(range(5), labels, fontsize=8)
        ax.set_ylim(0, 112)
        ax.set_title("Original 1 ns pilot: NOT fully qualified" if deadline == 1
                     else "Retained 2 ns characterization (post-hoc)", fontsize=11)
        ax.grid(axis="y", alpha=0.2)
    axes[0].set_ylabel("Correct signed sampled points (%)")
    axes[1].legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.20), ncol=2)
    fig.tight_layout()
    return fig


def tt_cost_figure(evidence: dict):
    table = matched_tt_comparison(evidence)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.0))
    names = ["Schematic", "LVS only", "C-only", "Balanced\nRC", "Repaired\nRC"]
    colors = ["#a0aec0", "#718096", "#e0ad54", "#c78346", "#009c8d"]
    axes[0].bar(names, table.mean_delay_ns, color=colors)
    axes[0].set_ylabel("Mean decision time (ns)")
    axes[0].axhline(1, color="#bc4b58", linestyle="--", linewidth=1)
    axes[1].bar(names, table.mean_core_energy_fj, color=colors)
    axes[1].set_ylabel("Mean core-VDD energy (fJ/cycle)")
    for ax in axes:
        ax.tick_params(axis="x", labelsize=8)
        ax.grid(axis="y", alpha=0.2)
    fig.suptitle("Matched TT / 1.8 V / 27 C, code zero, +/-3 mV | same 5 ps setting", fontsize=12)
    fig.tight_layout()
    return fig


def review_layout_waveforms(evidence: dict) -> tuple[pd.DataFrame, object]:
    folder = evidence["snapshot"] / "trace-examples"
    index = json.loads((folder / "index.json").read_text())
    examples = index["examples"]
    if len(examples) != 6:
        raise RuntimeError("The retained RC examples must cover both signs at TT and both SS conditions")
    fig, axes = plt.subplots(3, 2, figsize=(12, 7), sharex=True)
    results = []
    for ax, example in zip(axes.flat, examples):
        run_id = example["run_id"]
        if not re.fullmatch(r"[0-9a-f]{24}", run_id):
            raise RuntimeError("Invalid raw RC run identity")
        run = folder / run_id
        metadata = json.loads((run / "metadata.json").read_text())
        if metadata["run_id"] != run_id or metadata["mode"] != "rc" or metadata["status"] != "PASS":
            raise RuntimeError("The retained RC waveform did not pass simulator integrity checks")
        if digest(run / "waveform.npz") != metadata["artifact_sha256"]["waveform.npz"]:
            raise RuntimeError("Retained RC waveform hash mismatch")
        with np.load(run / "waveform.npz", allow_pickle=False) as saved:
            values = saved["values"]
        point = Point(**metadata["point"])
        trace = Trace(point, values, run_id, run)
        for deadline in (1, 2):
            measured = measure(trace, deadline)
            recorded = next(item for item in metadata["measurements"] if item["deadline_ns"] == deadline)
            for key, expected in recorded.items():
                actual = asdict(measured)[key]
                if isinstance(expected, (float, int)) and not isinstance(expected, bool):
                    if not math.isclose(actual, expected, rel_tol=1e-11, abs_tol=1e-11):
                        raise RuntimeError(f"Recomputed RC measurement differs: {run_id} / {key}")
                elif actual != expected:
                    raise RuntimeError(f"Recomputed RC measurement differs: {run_id} / {key}")
            results.append({"corner": point.corner, "vdd_v": point.vdd_v,
                            "temperature_c": point.temperature_c, "input_mv": 1000 * point.differential_v,
                            "run_id": run_id, **asdict(measured)})
        t = (values[:, 0] - 22.025e-9) * 1e9
        selected = (t >= -0.1) & (t <= 2.15)
        ax.plot(t[selected], values[selected, 2], color="#009c8d", label="Q+")
        ax.plot(t[selected], values[selected, 3], color="#cc5967", label="Q-")
        ax.axvline(1, color="#cc8e34", linestyle="--", linewidth=1, label="1 ns")
        ax.axvline(2, color="#687996", linestyle=":", linewidth=1, label="2 ns")
        ax.set_title(f"{point.corner.upper()} / {point.vdd_v:g} V / {point.temperature_c:g} C / "
                     f"{point.differential_v * 1000:+g} mV", fontsize=10)
        ax.set_ylabel("Voltage (V)", fontsize=9)
    axes[0, 0].legend(ncol=4, fontsize=8)
    for ax in axes[-1]:
        ax.set_xlabel("Time after evaluation clock midpoint (ns)")
    fig.tight_layout()
    return pd.DataFrame(results), fig
