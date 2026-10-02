"""Hash-bound, offline reader of the adopted single-row-a1 recorded experiment."""
from __future__ import annotations

from dataclasses import asdict
from io import BytesIO
from itertools import product
import json
from pathlib import Path
import zipfile

import matplotlib.pyplot as plt
from matplotlib.collections import PatchCollection
from matplotlib.patches import Polygon
import numpy as np
import pandas as pd

from comparator_atlas.spice import Point, Trace, measure
from entry_tools import digest, verify_files
import layout_evidence as physical

ROOT = Path(__file__).resolve().parent
FOLDER = ROOT / "layout_single_row" / "v1"
VERSION = "single-row-a1"
NOTICE = "Archived RC-deck outcomes; model physical fidelity not yet qualified"
GDS_SHA256 = "6e7cf5a7c3d61cd1298dc340999b01e84e5ff4ff39a6694d8070cdfeeb047fff"
MAG_SHA256 = "f05c4b0b2ce0d9747cde4d2eb84d2770e37190f3543358b3fcc8165a32b47896"


def read_json(name):
    return json.loads((FOLDER / name).read_bytes())


def validate_observations(frame):
    unresolved = frame.outcome.eq("unresolved")
    resolved = ~unresolved
    if not frame.outcome.isin(("correct", "wrong", "unresolved")).all() \
            or frame.loc[unresolved, "decision_time_ns"].notna().any() \
            or frame.loc[unresolved, "decision"].ne(0).any():
        raise ValueError("Unknown outcome or fabricated unresolved latency")
    latency = frame.loc[resolved, "decision_time_ns"]
    decisions = frame.loc[resolved, "decision"]
    if not np.isfinite(latency).all() or not decisions.isin((-1, 1)).all() \
            or not latency.ge(0).all() or not latency.le(frame.loc[resolved, "deadline_ns"]).all():
        raise ValueError("Resolved decisions require finite recorded times inside their own deadline")
    correct_sign = decisions.eq(np.sign(frame.loc[resolved, "signed_input_mv"]))
    if not correct_sign.eq(frame.loc[resolved, "outcome"].eq("correct")).all() \
            or not np.isfinite(frame.core_energy_fj).all() or not frame.core_energy_fj.gt(0).all():
        raise ValueError("Polarity classification or positive finite core energy is inconsistent")


def load():
    verify_files(FOLDER, read_json("evidence-sha256.json"))
    verify_files(ROOT, read_json("original-public-control-sha256.json"))
    if digest(FOLDER / "native/candidate/atlas.gds") != GDS_SHA256 \
            or digest(FOLDER / "native/candidate/atlas.mag") != MAG_SHA256:
        raise RuntimeError("The adopted frozen candidate changed")
    gates = read_json("native-a1/structural-receipt.json")
    if not gates["qualified"] or len(gates["checks"]) != 14 \
            or any(row["status"] != "PASS" for row in gates["checks"]) \
            or gates["native_drc_attempts"] != 1:
        raise RuntimeError("The actual archived native gate proof is incomplete")
    analysis = read_json("analysis/full45-analysis.json")
    if analysis["successful_transients"] != 1440 or analysis["qualified_step_pairs"] != 720 \
            or not analysis["nonregression_qualified"] or analysis["not_run"] != 0:
        raise RuntimeError("The full paired experiment is not complete/nonregressing")
    frame = pd.read_csv(FOLDER / "analysis/finest-point-measurements.csv")
    keys = ["layout", "mode", "corner", "vdd_v", "temperature_c", "signed_input_mv", "deadline_ns"]
    expected = set(product(
        ("control", "candidate"), ("c", "rc"), ("tt", "ss", "ff", "sf", "fs"),
        (1.62, 1.8, 1.95), (-40, 27, 125), (-10, -3, 3, 10), (1, 2)))
    if len(frame) != 1440 or frame.duplicated(keys).any() \
            or set(frame[keys].itertuples(index=False, name=None)) != expected:
        raise ValueError("Finest observations do not close the exact180-key grid per mode/layout")
    if not frame.numerically_qualified.eq(True).all() or not frame.reset_ok.eq(True).all() \
            or not frame.finest_step_ps.eq(5).all() \
            or not np.isfinite(frame.core_energy_fj).all() \
            or not frame.core_energy_fj.gt(0).all():
        raise ValueError("A required recorded qualification/energy/reset is missing")
    validate_observations(frame)
    index = read_json("execution-index.json")
    if len(index) != 1440 or len({r["run_id"] for r in index}) != 1440 \
            or any(r["status"] != "PASS" or r["returncode"] != 0 for r in index):
        raise ValueError("Executed trace identities are incomplete")
    records = {r["run_id"]: r for r in index}
    plans = read_json("pre-data-deck-plan.json")
    plan = {(p["layout"], p["mode"], *p["condition"], p["differential_mv"], p["step_ps"]):
            p["deck_sha256"] for p in plans}
    expected_runs = {(*key[:-1], step) for key in expected for step in (10, 5)}
    if len(plans) != 1440 or len(plan) != 1440 or set(plan) != expected_runs:
        raise ValueError("The pre-data deck plan does not close the exact1440fixed-step grid")
    observed_keys = set()
    for r in index:
        p = r["point"]
        key = (r["layout"], r["mode"], p["corner"], p["vdd_v"], p["temperature_c"],
               p["differential_v"] * 1000, p["max_step_ps"])
        if key in observed_keys or key not in plan or r["executed_deck_sha256"] != plan[key]:
            raise ValueError("An executed deck differs from the unique frozen plan")
        observed_keys.add(key)
        if p["pair_skew"] != 0 or p["trim_code"] != 0 or p["load_ff"] != 5 \
                or r["geometry_count"] != 27 or r["log_classification"]["warnings"] \
                or r["log_classification"]["errors"]:
            raise ValueError("Actual execution changed a fixed setting or has warnings/errors")
    if observed_keys != expected_runs:
        raise ValueError("Planned and executed trace keys differ")
    for row in frame.itertuples():
        record = records[row.run_id]
        p = record["point"]
        if (record["layout"], record["mode"], p["corner"], p["vdd_v"], p["temperature_c"],
            p["differential_v"] * 1000, p["max_step_ps"]) != (
                row.layout, row.mode, row.corner, row.vdd_v, row.temperature_c, row.signed_input_mv, 5):
            raise ValueError("An observation was reassigned to a different executed deck")
        observed = next(m for m in record["measurements"] if m["deadline_ns"] == row.deadline_ns)
        if observed["outcome"] != row.outcome or not np.isclose(
                observed["core_energy_fj"], row.core_energy_fj, rtol=1e-12, atol=1e-12):
            raise ValueError("Displayed values differ from actual trace measurements")
    paired = pd.read_csv(FOLDER / "analysis/keyed-layout-comparisons.csv")
    if len(paired) != 720 or paired[["loss_of_correct_point", "new_wrong",
                                    "new_unresolved_at_primary", "observed_regression_gate"]].any().any():
        raise ValueError("The keyed nonregression table has a missing or failed point")
    frozen = read_json("frozen-execution.json")
    if digest(ROOT / "comparator_atlas/spice.py") != frozen["source_sha256"]["measurement"]:
        raise RuntimeError("The recorded measurement helper changed")
    return {"analysis": analysis, "frame": frame, "paired": paired, "gates": gates,
            "provenance": read_json("publication-provenance.json"), "version": VERSION}


def table(evidence):
    rows = []
    for (layout, mode), points in evidence["frame"].groupby(["layout", "mode"], sort=False):
        first, primary = points[points.deadline_ns == 1], points[points.deadline_ns == 2]
        rows.append({
            "version": VERSION if layout == "candidate" else "original compact control",
            "mode": mode.upper(), "points": len(primary),
            "1ns correct/wrong/unresolved": "/".join(
                str(int(first.outcome.eq(k).sum())) for k in ("correct", "wrong", "unresolved")),
            "2ns correct/wrong/unresolved": "/".join(
                str(int(primary.outcome.eq(k).sum())) for k in ("correct", "wrong", "unresolved")),
            "mean core fJ": float(primary.core_energy_fj.mean()),
            "max core fJ": float(primary.core_energy_fj.max()),
            "worst recorded ns": float(primary.decision_time_ns.max()),
            "minimum 2ns margin ps": float((2 - primary.decision_time_ns.max()) * 1000),
        })
    return pd.DataFrame(rows)


def layout_figure(evidence):
    fig, axes = plt.subplots(2, 1, figsize=(12, 4.6))
    for ax, name, width in zip(axes, ("control", "candidate"), (129.6, 121.8)):
        layers = physical.gds_polygons((FOLDER / "native" / name / "atlas.gds").read_bytes())
        for i, polygons in enumerate(layers.values()):
            ax.add_collection(PatchCollection(
                [Polygon(p, closed=True) for p in polygons],
                facecolor="#365d7d" if i % 2 else "#b4bec7", edgecolor="none", alpha=.75))
        ax.set(xlim=(-64.8, 64.8), ylim=(-4.84, 12.19), aspect="equal",
               title=f"{name}: {width:g} x17.03 um; all-material bbox {width * 17.03:.3f} um2")
        ax.axis("off")
    fig.suptitle("single-row-a1: 6.01852% less area; exact archived GDS, identical plot scale")
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
    axes[0].set(xlabel="Control core energy (fJ)", ylabel="Candidate paired change (%)",
                title="180 keys per mode; small energy changes")
    axes[1].set(xlabel="Control recorded latency (ns)", ylabel="Candidate paired change (ps)",
                title="2ns primary; not timing signoff")
    for ax in axes:
        ax.axhline(0, color="#505963", linewidth=.8)
        ax.legend()
        ax.grid(alpha=.15)
    fig.tight_layout()
    return fig


def worst_figure(evidence):
    fig, ax = plt.subplots(figsize=(8, 2.6))
    records = read_json("execution-index.json")
    for layout, linestyle in (("control", "--"), ("candidate", "-")):
        record = next(r for r in records if r["layout"] == layout and r["mode"] == "rc"
                      and r["point"]["corner"] == "fs" and r["point"]["vdd_v"] == 1.62
                      and r["point"]["temperature_c"] == -40
                      and r["point"]["differential_v"] == -.003
                      and r["point"]["max_step_ps"] == 5)
        name = record["directory"] + "/waveform.npz"
        part = evidence["provenance"]["raw_members"][name]["archive"]
        with zipfile.ZipFile(FOLDER / part) as archive:
            with np.load(BytesIO(archive.read(name)), allow_pickle=False) as saved:
                values = saved["values"]
        time = (values[:, 0] - 22.025e-9) * 1e9
        selected = (time >= -.05) & (time <= 2.05)
        for column, signal, color in ((2, "Q+", "#365d7d"), (3, "Q-", "#778ba4")):
            ax.plot(time[selected], values[selected, column], linestyle, color=color,
                    label=f"{layout} {signal}")
    ax.axvline(1, color="#505963", linestyle=":")
    ax.axvline(2, color="#505963", linestyle=":")
    ax.set(xlabel="Time after evaluation midpoint (ns)", ylabel="Output (V)",
           title="Actual saved RC: FS /1.62V /-40C /-3mV; both late at1ns")
    ax.legend(fontsize=8, ncol=2)
    fig.tight_layout()
    return fig


def audit_raw():
    """Recheck every original raw member and remeasure all1440saved waves, without SPICE."""
    evidence = load()
    records = {r["directory"]: r for r in read_json("execution-index.json")}
    count = 0
    for part in evidence["provenance"]["raw_parts"]:
        with zipfile.ZipFile(FOLDER / part["path"]) as archive:
            if archive.testzip() is not None:
                raise RuntimeError("Raw evidence CRC failure")
            for name in archive.namelist():
                reference = evidence["provenance"]["raw_members"][name]
                import hashlib
                if hashlib.sha256(archive.read(name)).hexdigest() != reference["sha256"]:
                    raise RuntimeError(f"Changed original raw member: {name}")
            for name in (n for n in archive.namelist() if n.endswith("/waveform.npz")):
                record = records[name.rsplit("/", 1)[0]]
                with np.load(BytesIO(archive.read(name)), allow_pickle=False) as saved:
                    trace = Trace(Point(**record["point"]), saved["values"], record["run_id"], FOLDER)
                for observed in record["measurements"]:
                    actual = asdict(measure(trace, observed["deadline_ns"]))
                    for key, expected in observed.items():
                        value = actual[key]
                        if isinstance(expected, float):
                            if value is None or not np.isclose(value, expected, rtol=1e-12, atol=1e-12):
                                raise RuntimeError(f"Raw remeasurement differs: {record['run_id']} {key}")
                        elif value != expected:
                            raise RuntimeError(f"Raw classification/null differs: {record['run_id']} {key}")
                count += 1
    if count != 1440:
        raise RuntimeError("Raw trace coverage incomplete")
    return {"status": "passed", "raw_traces_remeasured": count, "new_simulations": 0}


if __name__ == "__main__":
    print(json.dumps(audit_raw(), indent=2))
