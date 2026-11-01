"""Run and archive the milestone-1 experiments, with executable acceptance checks.

    python -m examples.microrobot.run
    python -m examples.microrobot.run --spice

No network access, layout claims, or measurement fitting is performed.
"""
import argparse
from dataclasses import replace
import importlib.metadata
import json
from pathlib import Path
import platform

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from .pv import PVTable, characterize
from .system import Parameters, simulate

DEFAULT_OUTPUT = Path(__file__).parent / "local_runs/conceptual"


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")


def plots(destination, pv_results, system, sensitivities):
    fig, ax = plt.subplots(1, 2, figsize=(10, 4), layout="constrained")
    for label in ("dark", "light", "half_light", "short_lifetime"):
        item = pv_results[label]
        v = np.asarray(item["voltage_V"])
        i = np.asarray(item["delivered_A_per_um2"]) * 1e9
        ax[0].plot(v, i, label=label.replace("_", " "))
    ax[0].set(xlabel="Cell voltage (V)", ylabel="Delivered current (nA/µm²)",
              ylim=(-0.1, 0.16), xlim=(0, 0.55), title="Conceptual PV: dark and illuminated IV")
    ax[0].axhline(0, lw=0.5, color="0.5")
    ax[0].legend(fontsize=8)
    nominal = pv_results["light"]["responsivity_A_W"]
    ax[1].bar(["Our conceptual\nDD model", "2022 reported\napproximation"], [nominal, 0.3],
              color=["#177d92", "#b1bbc5"])
    ax[1].set(ylabel="Responsivity (A/W)", ylim=(0, 0.36),
              title="Comparison only: no calibration claimed")
    ax[1].text(0.5, 0.33, "Conceptual structure; S2 trace fit is a separate experiment", ha="center", fontsize=8)
    fig.savefig(destination / "pv.png", dpi=170)
    plt.close(fig)

    t = system["time_s"]
    fig, ax = plt.subplots(4, 1, figsize=(10, 10), sharex=True, layout="constrained")
    ax[0].plot(t, system["logic_V"], label="4-cell logic stack")
    ax[0].plot(t, system["positive_V"], label="actuator upper rail")
    ax[0].plot(t, -system["negative_magnitude_V"], label="actuator lower rail")
    ax[0].set(ylabel="Voltage (V)", title="Exploratory system: behavioral controller, uncalibrated mechanics")
    ax[0].legend(ncol=3, fontsize=8)
    for i, leg in enumerate(("A", "B")):
        ax[1].plot(t, system[f"drive_{leg}_V"], label=f"terminal {leg}", alpha=0.8)
        ax[2].plot(t, system[f"eta_{leg}_V"], label=f"local interface {leg}")
        ax[3].plot(t, system[f"curvature_{leg}_m_inv"] * 1e-5,
                   label=f"hinge angle {leg}")
    ax[1].set(ylabel="Terminal V\nvs Pt return")
    ax[2].plot(t, system["electrolyte_bulk_V"], "--", label="bulk electrolyte")
    ax[2].set(ylabel="Electrochemical V\nunknown absolute offset")
    ax[3].set(ylabel="Predicted angle (rad)", xlabel="Time (s)")
    for axis in ax:
        axis.axvspan(3, 3.4, color="0.7", alpha=0.25)
        axis.legend(fontsize=8, loc="upper right")
        axis.grid(alpha=0.15)
    fig.savefig(destination / "system.png", dpi=170)
    plt.close(fig)

    fig, ax = plt.subplots(1, 2, figsize=(10, 4), layout="constrained")
    labels = [r["label"] for r in sensitivities]
    ax[0].bar(labels, [r["mean_gait_Hz"] for r in sensitivities], color="#177d92")
    ax[0].set(ylabel="Behavioral gait frequency (Hz)", title="Illumination / leakage exploration")
    ax[0].tick_params(axis="x", rotation=25)
    parts = ["bias", "logic", "driver", "electrolyte", "faradaic", "adsorption"]
    ax[1].bar(parts, [system["metrics"][f"{s}_J_per_cycle"] * 1e9 for s in parts],
              color="#6b7f9a")
    ax[1].set(ylabel="Electrical energy (nJ/cycle)", title="Adsorption includes reversible storage")
    ax[1].tick_params(axis="x", rotation=25)
    fig.savefig(destination / "sensitivity_energy.png", dpi=170)
    plt.close(fig)


def run(destination=DEFAULT_OUTPUT, *, with_spice=False):
    dest = Path(destination).resolve()
    dest.mkdir(parents=True, exist_ok=True)
    pv = {"dark": characterize(mesh_um=0.04, irradiance_W_m2=0),
          "light": characterize(mesh_um=0.04),
          "medium_mesh": characterize(mesh_um=0.08),
          "coarse_mesh": characterize(mesh_um=0.16),
          "half_light": characterize(mesh_um=0.04, irradiance_W_m2=500),
          "short_lifetime": characterize(mesh_um=0.04, lifetime_s=1e-8)}
    write_json(dest / "pv.json", pv)
    table = PVTable.from_results(pv["dark"], pv["light"])
    model = simulate(table)
    refined = simulate(table, dt_s=0.0005)
    sensitivity = [dict(label="nominal", **model["metrics"])]
    for label, scale, leakage in (("0.5× light", 0.5, 1), ("2× light", 2, 1),
                                  ("10× leakage", 1, 0.1)):
        sensitivity.append(dict(label=label, **simulate(
            table, light_scale=scale, faradaic_scale=leakage)["metrics"]))
    # Supporting-reference mechanical timescale is not a calibrated Ti/Pt leg value.
    slower = simulate(table, p=replace(Parameters(), mechanical_tau_s=0.1))
    sensitivity.append(dict(label="2× mech τ", **slower["metrics"]))
    write_json(dest / "system_metrics.json", model["metrics"])
    write_json(dest / "sensitivities.json", sensitivity)
    columns = [key for key, value in model.items() if isinstance(value, np.ndarray)]
    np.savetxt(dest / "system.csv.gz", np.column_stack([model[k][::5] for k in columns]),
               delimiter=",", header=",".join(columns), comments="")
    mesh_error = abs(pv["medium_mesh"]["isc_A_per_um2"]
                     / pv["light"]["isc_A_per_um2"] - 1)
    time_errors = {key: abs(model["metrics"][key] / refined["metrics"][key] - 1)
                   for key in ("mean_gait_Hz", "bending_peak_to_peak_rad", "bias_mean_W",
                               "driver_J_per_cycle", "adsorption_J_per_cycle")}
    estimate = table.current(0, 500, 1)
    superposition_error = abs(estimate / pv["half_light"]["isc_A_per_um2"] - 1)
    validation = {"medium_to_fine_Isc_relative_change": mesh_error,
                  "timestep_relative_changes": time_errors,
                  "half_light_Isc_superposition_relative_error": superposition_error,
                  "maximum_contact_current_imbalance": max(
                      item["contact_imbalance_relative"] for item in pv.values()),
                  "electrical_energy_balance_relative_residual": model["metrics"][
                      "electrical_energy_balance_relative_residual"],
                  "phase_B_lag_cycles": model["metrics"]["measured_phase_B_lag_cycles"],
                  "published_responsivity_A_W_approximate": 0.3,
                  "our_responsivity_A_W": pv["light"]["responsivity_A_W"],
                  "published_comparison_status": "conceptual DD uncalibrated; digitized S2 fit in separate published experiment",
                  "layout_DRC_LVS_PEX": "not executed; no layout produced in milestone 1"}
    write_json(dest / "validation.json", validation)
    assert mesh_error < 0.05, "PV mesh convergence unresolved"
    assert max(time_errors.values()) < 0.05, "System timestep convergence unresolved"
    assert superposition_error < 0.03, "Illumination superposition inaccurate at 500 W/m²"
    assert validation["maximum_contact_current_imbalance"] < 1e-5
    assert abs(validation["phase_B_lag_cycles"] - 0.25) < 0.01
    assert model["metrics"]["enable_transitions"] == 2, "Startup/recovery missing"
    assert abs(validation["electrical_energy_balance_relative_residual"]) < 0.03
    assert 0 < pv["light"]["isc_A_per_um2"] <= pv["light"]["absorbed_photon_limit_A_per_um2"]
    plots(dest, pv, model, sensitivity)
    def package_version(name):
        try:
            return importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            return None  # Process tools are optional for this device-only experiment.
    environment = {"python": platform.python_version(), "platform": platform.platform(),
                   "packages": {name: package_version(name) for name in (
                       "numpy", "scipy", "devsim", "gmsh", "pyvista", "matplotlib",
                       "pydantic", "PyYAML", "nbformat", "nbclient", "ipykernel", "ViennaLS")}}
    write_json(dest / "environment.json", environment)
    if with_spice:
        from .spice import run_ring
        corners = []
        for corner, voltage, temp in (("tt", 1.6, 27), ("ss", 1.6, 27),
                                      ("ff", 1.6, 27), ("tt", 1.8, 27), ("tt", 1.6, 85)):
            info, data = run_ring(dest / "spice" / f"{corner}_{voltage}_{temp}",
                                  corner=corner, supply_V=voltage, temperature_C=temp)
            corners.append(info)
            if len(corners) == 1:
                fig, axis = plt.subplots(figsize=(8, 3.5), layout="constrained")
                sel = (data[:, 0] > 1e-3) & (data[:, 0] < 1.5e-3)
                axis.plot(data[sel, 0] * 1e3, data[sel, 2], label="buffered clock")
                axis.plot(data[sel, 0] * 1e3, data[sel, 3], label="internal RC node")
                axis.set(xlabel="Time (ms)", ylabel="Voltage (V)",
                         title="SKY130 TT 1.6 V: seeded RC ring feasibility experiment")
                axis.legend()
                fig.savefig(dest / "spice_ring.png", dpi=170)
                plt.close(fig)
        write_json(dest / "spice_summary.json", corners)
        maximum_logic_PV_W = (pv["light"]["pmax_W_per_um2"]
                              * Parameters().logic_cell_area_um2
                              * Parameters().logic_series_cells)
        write_json(dest / "spice_budget.json", {
            "nominal_ring_W": corners[0]["mean_power_W"],
            "logic_array_maximum_PV_W": maximum_logic_PV_W,
            "ring_to_available_power_ratio": corners[0]["mean_power_W"] / maximum_logic_PV_W,
            "decision": "reject this ring for the proposed PV allocation; redesign reference/clock",
            "comparison": "ideal external 1.6 V SPICE supply vs conceptual TCAD array MPP",
            "not_tested": "PV-powered transistor startup, mismatch, layout or PEX"})
    print(json.dumps({"validation": validation, "system": model["metrics"]}, indent=2))
    return validation


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--spice", action="store_true")
    args = parser.parse_args()
    run(args.output, with_spice=args.spice)
