"""Portable saved-data reader of adopted b1 and its matched adopted-a1 control."""
from dataclasses import asdict
from io import BytesIO
from itertools import product
import hashlib
import json
from pathlib import Path
import zipfile

import matplotlib.pyplot as plt
from matplotlib.collections import PatchCollection
from matplotlib.patches import Polygon
import numpy as np
import pandas as pd

from comparator_atlas.spice import Point, Trace, measure, validate_waveform
from entry_tools import digest, verify_files, artifact_path
import layout_evidence as physical
from single_row_a1_evidence import validate_observations

ROOT = Path(__file__).resolve().parent
FOLDER = ROOT / "layout_single_row" / "v2"
VERSION = "single-row-local-pitch-b1"
NOTICE = "Archived RC-deck outcomes; model physical fidelity not yet qualified"
GDS_SHA256 = "8766839b2ec991e152b8094cc75c7322f9c7e2de6cb317791eb1b6ce0c6bd4cd"
MAG_SHA256 = "a25f990d1ea2119a92f3f93a1af8d0e7e804567155037ddc3376f9065a5a0889"


def read_json(name):
    return json.loads(artifact_path(FOLDER, name).read_bytes())


def load():
    selector = json.loads((ROOT / "layout_single_row" / "current.json").read_bytes())
    metadata = json.loads((ROOT / "entry_metadata.json").read_bytes())["current_area_version"]
    if selector["schema_version"] != 2 or selector["adopted_version"] != VERSION \
            or selector["evidence_directory"] != FOLDER.relative_to(ROOT).as_posix() \
            or selector["matched_control"] != "single-row-a1" \
            or metadata["adopted_version"] != VERSION \
            or metadata["selector"] != "layout_single_row/current.json":
        raise ValueError("Current version selector and entry metadata disagree")
    verify_files(FOLDER, read_json("evidence-sha256.json"))
    verify_files(ROOT, read_json("historical-source-sha256.json"))
    if digest(FOLDER / "native/candidate/atlas.gds") != GDS_SHA256 \
            or digest(FOLDER / "native/candidate/atlas.mag") != MAG_SHA256:
        raise RuntimeError("The adopted b1 geometry changed")
    gates = read_json("native-b1/structural-receipt.json")
    if not gates["qualified"] or len(gates["checks"]) != 14 \
            or any(r["status"] != "PASS" for r in gates["checks"]) \
            or gates["native_drc_attempts"] != 1:
        raise RuntimeError("Historical b1 native proof is incomplete")
    analysis = read_json("analysis/full45-analysis.json")
    if analysis["status"] != "completed_private_full45_passed_not_adopted" \
            or analysis["charged_invocations"] != 1440 \
            or analysis["successful_transients"] != 1440 \
            or analysis["qualified_step_pairs"] != 720 or analysis["not_run"] != 0 \
            or analysis["pointwise_regression_rows"] != 0 \
            or not analysis["fresh_control_archived_a1_all_available_agree"]:
        raise RuntimeError("The immutable pre-adoption full45 experiment is incomplete")
    # Adoption is publication provenance, not a rewrite of private execution status.
    frame = pd.DataFrame(read_json("analysis/finest-point-measurements.json"))
    keys = ["layout", "mode", "corner", "vdd_v", "temperature_c", "signed_input_mv", "deadline_ns"]
    expected = set(product(("control", "candidate"), ("c", "rc"),
                           ("tt", "ss", "ff", "sf", "fs"), (1.62, 1.8, 1.95),
                           (-40, 27, 125), (-10, -3, 3, 10), (1, 2)))
    if len(frame) != 1440 or frame.duplicated(keys).any() \
            or set(frame[keys].itertuples(index=False, name=None)) != expected:
        raise ValueError("Finest observations do not close the exact b1/a1 grid")
    validate_observations(frame)
    if not frame.numerically_qualified.eq(True).all() or not frame.reset_ok.eq(True).all() \
            or not frame.finest_step_ps.eq(5).all():
        raise ValueError("Invalid b1 numerical/reset evidence")
    records = read_json("execution-index.json")
    planned = read_json("pre-data-deck-plan.json")
    plan = {(r["layout"], r["mode"], *r["condition"], r["signed_input_mv"], r["step_ps"]):
            r["deck_sha256"] for r in planned}
    run_keys = set()
    by_id = {}
    for r in records:
        p = r["point"]
        key = (r["layout"], r["mode"], p["corner"], p["vdd_v"], p["temperature_c"],
               p["differential_v"] * 1000, r["max_step_ps"])
        if key in run_keys or key not in plan or r["status"] != "PASS" \
                or r["returncode"] != 0 or r["geometry_count"] != 27 \
                or r["executed_deck_sha256"] != plan[key] \
                or r["log_classification"]["errors"] or r["log_classification"]["warnings"]:
            raise ValueError("Duplicate, changed or failed original execution")
        if r["run_id"] in by_id or p["pair_skew"] != 0 or p["trim_code"] != 0 or p["load_ff"] != 5:
            raise ValueError("Changed nominal experiment or run identity")
        run_keys.add(key)
        by_id[r["run_id"]] = r
    expected_runs = {(*key[:-1], step) for key in expected for step in (10, 5)}
    if len(plan) != 1440 or len(planned) != 1440 or len(records) != 1440 or run_keys != expected_runs:
        raise ValueError("Planned/executed transient closure differs")
    for row in frame.to_dict("records"):
        record = by_id[row["run_id"]]
        p = record["point"]
        if (record["layout"], record["mode"], p["corner"], p["vdd_v"], p["temperature_c"],
            p["differential_v"] * 1000, p["max_step_ps"]) != (
                row["layout"], row["mode"], row["corner"], row["vdd_v"], row["temperature_c"],
                row["signed_input_mv"], 5):
            raise ValueError("Finest measurement was reassigned")
        m = next(m for m in record["measurements"] if m["deadline_ns"] == row["deadline_ns"])
        if m["outcome"] != row["outcome"] or m["decision"] != row["decision"] \
                or not np.isclose(m["core_energy_fj"], row["core_energy_fj"], rtol=1e-12, atol=1e-12):
            raise ValueError("Displayed values differ from recorded data")
        actual = None if pd.isna(row["decision_time_ns"]) else row["decision_time_ns"]
        if actual != m["decision_time_ns"]:
            raise ValueError("Recorded null/latency changed")
    paired = []
    for r in read_json("keyed-layout-comparisons.json"):
        paired.append({"mode": r["mode"], "corner": r["condition"][0], "vdd_v": r["condition"][1],
                       "temperature_c": r["condition"][2], "signed_input_mv": r["signed_input_mv"],
                       "deadline_ns": r["deadline_ns"], "control_outcome": r["control"]["outcome"],
                       "candidate_outcome": r["candidate"]["outcome"],
                       "control_fullcycle_core_energy_fj": r["control"]["core_energy_fj"],
                       "candidate_energy_change_percent": r["energy_change_percent"],
                       "control_latency_ns": r["control"]["decision_time_ns"],
                       "candidate_latency_ns": r["candidate"]["decision_time_ns"],
                       "candidate_minus_control_latency_ns": r["latency_delta_ns"],
                       "observed_regression_gate": r["regression_gate"]})
    paired = pd.DataFrame(paired)
    pk = ["mode", "corner", "vdd_v", "temperature_c", "signed_input_mv", "deadline_ns"]
    if len(paired) != 720 or paired.duplicated(pk).any() or paired.observed_regression_gate.any() \
            or set(paired[pk].itertuples(index=False, name=None)) != {key[1:] for key in expected}:
        raise ValueError("Invalid matched comparison closure")
    provenance = read_json("publication-provenance.json")
    if provenance["version"] != VERSION or provenance["matched_control"] != "adopted-single-row-a1":
        raise ValueError("Wrong adopted/matched-control version")
    frozen = read_json("frozen-execution.json")
    if digest(ROOT / "comparator_atlas/spice.py") != frozen["sources"]["measurement"]:
        raise RuntimeError("Published measurement helper changed")
    return {"analysis": {**analysis, "area_reduction_percent": analysis["area_reduction_percent"]},
            "frame": frame, "paired": paired, "gates": gates, "provenance": provenance,
            "version": VERSION}


def table(evidence):
    rows = []
    for (layout, mode), points in evidence["frame"].groupby(["layout", "mode"], sort=False):
        first, primary = points[points.deadline_ns == 1], points[points.deadline_ns == 2]
        rows.append({"version": VERSION if layout == "candidate" else "Matched adopted a1",
                     "mode": mode.upper(), "points": len(primary),
                     "1ns correct/wrong/unresolved": "/".join(
                         str(int(first.outcome.eq(k).sum())) for k in ("correct", "wrong", "unresolved")),
                     "2ns correct/wrong/unresolved": "/".join(
                         str(int(primary.outcome.eq(k).sum())) for k in ("correct", "wrong", "unresolved")),
                     "mean core fJ": float(primary.core_energy_fj.mean()),
                     "max core fJ": float(primary.core_energy_fj.max()),
                     "worst recorded ns": float(primary.decision_time_ns.max()),
                     "minimum 2ns margin ps": float((2 - primary.decision_time_ns.max()) * 1000)})
    return pd.DataFrame(rows)


def layout_figure(evidence):
    fig, axes = plt.subplots(2, 1, figsize=(12, 4.6))
    for ax, name, width in zip(axes, ("control", "candidate"), (121.8, 110)):
        layers = physical.gds_polygons((FOLDER / "native" / name / "atlas.gds").read_bytes())
        for i, polygons in enumerate(layers.values()):
            ax.add_collection(PatchCollection(
                [Polygon(p, closed=True) for p in polygons],
                facecolor="#365d7d" if i % 2 else "#b4bec7", edgecolor="none", alpha=.75))
        label = "Matched adopted a1" if name == "control" else "Adopted local-pitch b1"
        ax.set(xlim=(-60.9, 60.9), ylim=(-4.84, 12.19), aspect="equal",
               title=f"{label}: {width:g} x 17.03 um; all-material bbox {width*17.03:.3f} um2")
        ax.axis("off")
    fig.suptitle("b1: 9.688% incremental bbox reduction; archived GDS at identical scale")
    fig.tight_layout()
    return fig


def comparison_figure(evidence):
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    for mode, color in (("c", "#778ba4"), ("rc", "#365d7d")):
        p = evidence["paired"]
        p = p[(p["mode"] == mode) & (p.deadline_ns == 2)]
        axes[0].scatter(p.control_fullcycle_core_energy_fj, p.candidate_energy_change_percent,
                        s=14, label=mode.upper(), color=color)
        axes[1].scatter(p.control_latency_ns, 1000 * p.candidate_minus_control_latency_ns,
                        s=14, label=mode.upper(), color=color)
    axes[0].set(xlabel="Matched a1 core energy (fJ)", ylabel="b1 relative change (%)",
                title="180 keys per mode; finite-grid observations")
    axes[1].set(xlabel="Matched a1 recorded latency (ns)", ylabel="b1 minus a1 (ps)",
                title="2 ns primary; not timing signoff")
    for ax in axes:
        ax.axhline(0, color="#505963", linewidth=.8)
        ax.legend()
        ax.grid(alpha=.15)
    fig.tight_layout()
    return fig


def raw_bytes(evidence, identity):
    row = evidence["provenance"]["raw_members"][identity]
    with zipfile.ZipFile(artifact_path(FOLDER, row["archive"])) as archive:
        data = archive.read(row["member"])
    if hashlib.sha256(data).hexdigest() != row["sha256"]:
        raise RuntimeError(f"Changed raw member: {identity}")
    return data


def worst_figure(evidence):
    fig, ax = plt.subplots(figsize=(8, 2.6))
    for layout, linestyle in (("control", "--"), ("candidate", "-")):
        record = next(
            r for r in read_json("execution-index.json") if r["layout"] == layout
            and r["mode"] == "rc" and r["point"]["corner"] == "fs" and r["point"]["vdd_v"] == 1.62
            and r["point"]["temperature_c"] == -40 and r["point"]["differential_v"] == -.003
            and r["max_step_ps"] == 5)
        with np.load(BytesIO(raw_bytes(evidence, "full45/raw/" + record["directory"] + "/waveform.npz")),
                     allow_pickle=False) as saved:
            values = saved["values"]
        time = (values[:, 0] - 22.025e-9) * 1e9
        selected = (time >= -.05) & (time <= 2.05)
        for column, signal, color in ((2, "Q+", "#365d7d"), (3, "Q-", "#778ba4")):
            label = "Matched a1" if layout == "control" else "Adopted b1"
            ax.plot(time[selected], values[selected, column], linestyle, color=color, label=f"{label} {signal}")
    ax.axvline(1, color="#505963", linestyle=":")
    ax.axvline(2, color="#505963", linestyle=":")
    ax.set(xlabel="Time after evaluation midpoint (ns)", ylabel="Output (V)",
           title="Recorded RC: FS / 1.62 V / -40 C / -3 mV; both unresolved at 1 ns")
    ax.legend(fontsize=8, ncol=2)
    fig.tight_layout()
    return fig


def audit_raw():
    """Read every public part/member and remeasure all1504 actual saved waves; no new SPICE."""
    evidence = load()
    records = {"full45": {r["directory"]: r for r in read_json("execution-index.json")},
               "bounded64": None}
    diagnostic_index = raw_bytes(evidence, "bounded64/diagnostic-raw/execution-index.json")
    records["bounded64"] = {r["directory"]: r for r in json.loads(diagnostic_index)}
    count = {"full45": 0, "bounded64": 0}
    observed = set()
    for part in evidence["provenance"]["raw_parts"]:
        with zipfile.ZipFile(FOLDER / part["path"]) as archive:
            if archive.testzip() is not None or len(archive.namelist()) != len(set(archive.namelist())):
                raise RuntimeError("Raw CRC or duplicate-member failure")
            for name in archive.namelist():
                identity = part["source"] + "/" + name
                ref = evidence["provenance"]["raw_members"][identity]
                if identity in observed or ref["archive"] != part["path"] \
                        or hashlib.sha256(archive.read(name)).hexdigest() != ref["sha256"]:
                    raise RuntimeError(f"Changed/repeated raw member: {identity}")
                observed.add(identity)
                prefix = "raw/" if part["source"] == "full45" else "diagnostic-raw/"
                if not name.startswith(prefix + "simulations/") or not name.endswith("/waveform.npz"):
                    continue
                directory = name[len(prefix):].rsplit("/", 1)[0]
                record = records[part["source"]][directory]
                with np.load(BytesIO(archive.read(name)), allow_pickle=False) as saved:
                    values = saved["values"]
                tsv = np.loadtxt(BytesIO(raw_bytes(
                    evidence, part["source"] + "/" + prefix + directory + "/waveform.tsv")),
                    skiprows=1, ndmin=2)
                if not np.array_equal(values, tsv):
                    raise RuntimeError("TSV/NPZ differs")
                validate_waveform(values)
                trace = Trace(Point(**record["point"]), values, record["run_id"], FOLDER)
                for expected in record["measurements"]:
                    if asdict(measure(trace, expected["deadline_ns"])) != expected:
                        raise RuntimeError(f"Raw remeasurement differs: {record['run_id']}")
                count[part["source"]] += 1
    if observed != set(evidence["provenance"]["raw_members"]) or count != {"full45": 1440, "bounded64": 64}:
        raise RuntimeError("Incomplete exact public raw closure")
    return {"status": "passed", "raw_traces_remeasured": count, "new_simulations": 0}


if __name__ == "__main__":
    print(json.dumps(audit_raw(), indent=2))
