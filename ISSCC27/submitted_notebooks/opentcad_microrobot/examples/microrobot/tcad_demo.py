"""TCAD PV → characterized schematic-clock lookup → behavioral actuator demo.

Fresh multi-second system runs reuse archived DD and native clock evidence.
This is not a coupled transistor transient, PV calibration or walking model.
"""

from dataclasses import replace, asdict
import hashlib
import json
from pathlib import Path
import time

import numpy as np

from .pv import PVTable
from .published import ClockLookup
from .system import Parameters, simulate

HERE = Path(__file__).resolve().parent
DEFAULT_PV = HERE / "results/pv.json"
CLOCK_SUMMARY = HERE / "results/clock_final/summary.json"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def json_value(value):
    """Convert NumPy scalar leaves; json traverses their containing dicts/lists."""
    if isinstance(value, np.generic):
        return value.item()
    raise TypeError(f"Unsupported JSON value: {type(value).__name__}")


def completion(out, duration_s):
    t = out["time_s"]
    finite = all(
        np.isfinite(value).all() for value in out.values() if isinstance(value, np.ndarray)
    )
    return {
        "requested_stop_s": duration_s,
        "start_s": float(t[0]),
        "actual_stop_s": float(t[-1]),
        "rows": len(t),
        "strictly_increasing": bool(np.all(np.diff(t) > 0)),
        "finite": finite,
        "complete": bool(
            t[0] == 0 and abs(t[-1] - duration_s) < 1e-12 and np.all(np.diff(t) > 0) and finite
        ),
    }


def inputs(pv_path=DEFAULT_PV):
    curves = json.loads(Path(pv_path).read_text())
    table = PVTable.from_results(curves["dark"], curves["light"])
    summary = json.loads(CLOCK_SUMMARY.read_text())
    lookup = ClockLookup.from_summary(summary)
    selected = (lookup.voltage >= 1.6) & (lookup.voltage <= 1.9)
    lookup = ClockLookup(
        *(
            getattr(lookup, name)[selected]
            for name in ["voltage", "frequency", "analog_A", "first_ff_A", "reference_A"]
        )
    )
    if not np.array_equal(lookup.voltage, [1.6, 1.7, 1.8, 1.9]):
        raise ValueError("Missing validated schematic clock envelope")
    source_hash = sha(HERE / "circuits/starved_clock.spice")
    if any(
        record.get("netlist_sha256") != source_hash
        for record in summary["cases"]
        if record.get("netlist_sha256")
    ):
        raise ValueError("Schematic clock archive/source hash mismatch")
    return table, lookup


def parameters():
    return replace(
        Parameters(),
        logic_series_cells=4,
        logic_cell_area_um2=1080,
        actuator_cell_area_um2=1080,
        actuator_series_cells_per_half=2,
        divider=8192,
        brownout_on_V=1.65,
        brownout_off_V=1.60,
        effective_switched_F=0.02e-12,
    )


def evaluate(table, lookup, p, *, dt_s=0.001, duration_s=6.0, light_scale=1.0):
    return simulate(
        table,
        p=p,
        dt_s=dt_s,
        duration_s=duration_s,
        light_scale=light_scale,
        clock_response=lookup.clock,
        analog_current_response=lookup.analog,
        extra_logic_current_response=lookup.first_ff,
    )


def inspect(out, table, p):
    t = out["time_s"]
    enabled = out["enabled"] > 0.5
    on = t[np.flatnonzero(np.diff(np.r_[False, enabled].astype(int)) > 0)]
    off = t[np.flatnonzero(np.diff(np.r_[False, enabled].astype(int)) < 0)]
    cells = np.array([out["logic_V"] / 4, out["positive_V"] / 2, out["negative_magnitude_V"] / 2])
    theta = np.array([out["theta_A"], out["theta_B"], out["theta_return"]])
    metrics = dict(out["metrics"])
    metrics.update(
        enable_rises_s=on.tolist(),
        enable_falls_s=off.tolist(),
        active_logic_min_max_V=[
            float(out["logic_V"][enabled].min()),
            float(out["logic_V"][enabled].max()),
        ]
        if enabled.any()
        else None,
        PV_cell_min_max_V=[float(cells.min()), float(cells.max())],
        theta_min_max=[float(theta.min()), float(theta.max())],
        electrolyte_KCL_peak_A=float(abs(out["electrolyte_KCL_A"]).max()),
        recovered_bending_peak_to_peak_rad=float(
            np.ptp(out["curvature_A_m_inv"][t > 4]) * p.hinge_length_um * 1e-6
        ),
        finite=all(
            np.isfinite(value).all() for value in out.values() if isinstance(value, np.ndarray)
        ),
    )
    metrics["gates"] = {
        "finite": metrics["finite"],
        "startup": len(on) >= 1 and on[0] < 3,
        "shutdown": len(off) >= 1 and 3 <= off[0] < 3.4,
        "recovery": len(on) >= 2 and on[1] >= 3.4,
        "phase_quarter_cycle": metrics["measured_phase_B_lag_cycles"] is not None
        and abs(metrics["measured_phase_B_lag_cycles"] - 0.25) < 0.01,
        "predicted_bend_nonzero": metrics["bending_peak_to_peak_rad"] > 1e-4
        and metrics["recovered_bending_peak_to_peak_rad"] > 1e-4,
        "bounded_coverage": bool(theta.min() >= -1e-9 and theta.max() <= 1 + 1e-9),
        "PV_domain": bool(cells.min() >= -1e-9 and cells.max() <= table.voltage_V[-1] + 1e-9),
        "active_clock_envelope": bool(
            enabled.any()
            and out["logic_V"][enabled].min() >= 1.6
            and out["logic_V"][enabled].max() <= 1.9
        ),
        "KCL": metrics["electrolyte_KCL_peak_A"] < 1e-18,
        "energy_residual_3percent": abs(metrics["electrical_energy_balance_relative_residual"])
        < 0.03,
    }
    return metrics


def run(destination=HERE / "results/tcad_demo", *, dt_s=0.001, duration_s=6.0, pv_path=DEFAULT_PV):
    """Run nominal, half-step refinement and all-dark control; return summary dict."""
    destination = Path(destination)
    if destination.exists() and any(destination.iterdir()):
        raise FileExistsError("Demo output must be fresh")
    destination.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    table, lookup = inputs(pv_path)
    p = parameters()
    nominal = evaluate(table, lookup, p, dt_s=dt_s, duration_s=duration_s)
    fine = evaluate(table, lookup, p, dt_s=dt_s / 2, duration_s=duration_s)
    dark = evaluate(table, lookup, p, dt_s=dt_s, duration_s=duration_s, light_scale=0)
    nm = inspect(nominal, table, p)
    fm = inspect(fine, table, p)
    keys = [
        "mean_gait_Hz",
        "bending_peak_to_peak_rad",
        "bias_mean_W",
        "driver_J_per_cycle",
        "recovered_bending_peak_to_peak_rad",
    ]
    changes = {key: float(abs(nm[key] - fm[key]) / max(abs(fm[key]), 1e-30)) for key in keys}
    dark_max = {
        name: float(abs(dark[name]).max())
        for name in [
            "logic_V",
            "positive_V",
            "negative_magnitude_V",
            "phase_cycles",
            "drive_A_V",
            "drive_B_V",
            "curvature_A_m_inv",
            "curvature_B_m_inv",
            "storage_J",
            "enabled",
        ]
    }
    gates = {
        **nm["gates"],
        "fine_run": all(fm["gates"].values()),
        "timestep_principals_5percent": max(changes.values()) < 0.05,
        "all_dark_no_power_phase_or_bend": max(dark_max.values()) < 1e-20,
    }
    completions = {
        name: completion(out, duration_s)
        for name, out in [("nominal", nominal), ("fine", fine), ("all_dark", dark)]
    }
    gates["all_three_runs_complete"] = all(value["complete"] for value in completions.values())
    source_path = Path(pv_path).resolve()
    try:
        source_label = str(source_path.relative_to(HERE.parents[1]))
    except ValueError:
        source_label = source_path.name
    report = {
        "scope": __doc__,
        "all_gates_pass": all(gates.values()),
        "gates": gates,
        "nominal": nm,
        "fine": fm,
        "timestep_relative_changes": changes,
        "all_dark_max_abs": dark_max,
        "parameters": asdict(p),
        "design": {
            "logic_series_cells": 4,
            "actuator_series_cells_per_half": 2,
            "cell_area_um2": 1080,
            "total_PV_area_um2": 8640,
            "storage": "50pF logic/200pF per actuator half; assumed design choices",
        },
        "model_limits": {
            "PV": "Archived actual DD dark/light table, linear irradiance superposition; no measured-PV calibration",
            "clock": "Native schematic TT clock+DFF frequency/current lookup,1.6–1.9V; extracted-clock evidence is separate",
            "controller": "Behavioral phase accumulator, /8192 functional divider and1.65/1.60V supervisor; not full transistor startup",
            "remaining_digital": "Assumed20fF switched capacitance plus0.2nA leakage, beyond measured firstFF",
            "driver": "Finite100MΩ behavioral drive, NOT a native MOS transient; native MOS evidence remains separate",
            "electrochemistry": "Nonlinear adsorption, Cdl/Faradaic, finite Pt return/electrolyte; uncalibrated",
            "mechanics": "Assumed50ms relaxation/curvature scale, predicted bending only; no contact/force/walking",
        },
        "provenance": {
            "PV_path": source_label,
            "PV_sha256": sha(pv_path),
            "clock_summary_sha256": sha(CLOCK_SUMMARY),
            "schematic_clock_sha256": sha(HERE / "circuits/starved_clock.spice"),
        },
        "execution": {
            "system_simulations": 3,
            "SPICE": 0,
            "DD": 0,
            "layout": 0,
            "dt_s": dt_s,
            "fine_dt_s": dt_s / 2,
            "duration_s": duration_s,
            "seconds": time.monotonic() - started,
        },
    }
    columns = [
        "time_s",
        "irradiance_W_m2",
        "logic_V",
        "positive_V",
        "negative_magnitude_V",
        "enabled",
        "phase_cycles",
        "phase_Hz",
        "drive_A_V",
        "drive_B_V",
        "eta_A_V",
        "eta_B_V",
        "eta_return_V",
        "electrolyte_bulk_V",
        "theta_A",
        "theta_B",
        "theta_return",
        "curvature_A_m_inv",
        "curvature_B_m_inv",
        "current_A_A",
        "current_B_A",
        "current_return_A",
        "electrolyte_KCL_A",
        "storage_J",
    ]
    np.savetxt(
        destination / "waveforms.csv.gz",
        np.column_stack([nominal[key] for key in columns]),
        delimiter=",",
        header=",".join(columns),
        comments="",
    )
    plot(nominal, p, destination / "system.png")
    report["completion"] = completions
    report["execution"]["seconds"] = time.monotonic() - started
    report = json.loads(json.dumps(report, default=json_value, allow_nan=False))
    (destination / "summary.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    return report


def plot(out, p, destination):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    t = out["time_s"]
    fig, axes = plt.subplots(4, 1, figsize=(10, 10), sharex=True, layout="constrained")
    for key, label in [
        ("logic_V", "logic"),
        ("positive_V", "upper half"),
        ("negative_magnitude_V", "lower-half magnitude"),
    ]:
        axes[0].plot(t, out[key], label=label)
    for leg in ["A", "B"]:
        axes[1].plot(t, out[f"drive_{leg}_V"], label="phase " + leg)
        axes[2].plot(t, out[f"eta_{leg}_V"], label="local eta " + leg)
        axes[3].plot(
            t,
            out[f"curvature_{leg}_m_inv"] * p.hinge_length_um * 1e-6,
            label="predicted angle " + leg,
        )
    for ax, label in zip(axes, ["Supply V", "Drive V vs Pt", "Interface V", "Predicted bend rad"]):
        ax.set_ylabel(label)
        ax.legend(loc="upper right")
        ax.axvspan(3, 3.4, color="0.7", alpha=0.25)
    axes[-1].set_xlabel("Time (s)")
    fig.suptitle(
        "TCAD PV + native schematic-clock lookup + behavioral driver/nonlinear electrode/bending model"
    )
    fig.savefig(destination, dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=HERE / "results/tcad_demo")
    parser.add_argument("--pv-file", type=Path, default=DEFAULT_PV)
    args = parser.parse_args()
    result = run(args.output, pv_path=args.pv_file)
    print(
        json.dumps(
            {
                "all_gates_pass": result["all_gates_pass"],
                "gates": result["gates"],
                "execution": result["execution"],
            },
            indent=2,
        )
    )
