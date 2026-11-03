"""Published PV evidence + characterized clock + reduced electrochemical system.

The original conceptual TCAD experiment remains separate. This experiment
uses an effective terminal fit; it does not calibrate the conceptual geometry.
"""
from dataclasses import dataclass, replace
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import brentq

from opentcad.device.compact import SingleDiodePV
from .digitize import fit_digitized
from .pv import PVTable
from .system import Parameters, simulate

HERE = Path(__file__).parent


@dataclass
class ClockLookup:
    voltage: np.ndarray
    frequency: np.ndarray
    analog_A: np.ndarray
    first_ff_A: np.ndarray
    reference_A: np.ndarray

    @classmethod
    def from_summary(cls, summary):
        records = sorted([r for r in summary["cases"] if r.get("passed")
            and r["corner"] == "tt" and r["temperature_C"] == 26.85
            and r["ramp_s"] == 100e-6 and r["supply"] == "ideal voltage ramp"],
            key=lambda r: r["voltage_V"])
        if len(records) < 3:
            raise ValueError("Need at least three passing TT supply characterizations")
        if len({r["netlist_sha256"] for r in records}) != 1:
            raise ValueError("Clock records mix different circuit revisions")
        return cls(np.array([r["voltage_V"] for r in records]),
                   np.array([r["frequency_Hz"] for r in records]),
                   np.array([r["analog_clock_power_W"]/r["voltage_V"] for r in records]),
                   np.array([r["first_divider_stage_power_W"]/r["voltage_V"] for r in records]),
                   np.array([r["bias_reference_power_W"]/r["voltage_V"] for r in records]))

    def clock(self, voltage):
        if voltage < self.voltage[0]-1e-9 or voltage > self.voltage[-1]+1e-9:
            raise ValueError("Active clock voltage is outside the characterized envelope")
        return float(np.exp(np.interp(voltage, self.voltage, np.log(self.frequency))))

    def _current(self, voltage, values):
        # Below the characterized active region this is an explicitly
        # approximate startup load. Direct PV-powered SPICE is authoritative
        # for electrical startup. Endpoint clipping above the highest voltage
        # is only for root bracketing; accepted states are checked separately.
        if voltage < self.voltage[0]:
            return max(0.0, voltage) / self.voltage[0] * values[0]
        return float(np.exp(np.interp(voltage, self.voltage, np.log(values))))

    def analog(self, voltage):
        return self._current(voltage, self.analog_A)

    def first_ff(self, voltage):
        return self._current(voltage, self.first_ff_A)

    def reference(self, voltage):
        return self._current(voltage, self.reference_A)


def terminal_table(pair: SingleDiodePV):
    """Per-um² proxy for matched cells, assuming the measured 540 um² cell density."""
    cell = replace(pair, series_cells=1).scaled_current(1 / 540)
    voltage = np.linspace(0, 0.75, 751)
    dark = cell.current_A(voltage, 0)
    return PVTable(voltage, dark, cell.current_A(voltage, 1000)-dark, 1000)


def plot_clock_validation(summary, clock_directory, destination):
    folder = Path(clock_directory)
    preview = folder / "pv_startup/waveform.csv.gz"
    if not preview.is_file():
        raise FileNotFoundError("Clock waveform preview missing; rerun the SPICE characterization")
    data = np.loadtxt(preview, delimiter=",", skiprows=1)
    t, voltage, clock = data[:, :3].T
    fig, axes = plt.subplots(2, 2, figsize=(11, 7), layout="constrained")
    startup = t < 0.0006
    axes[0, 0].plot(t[startup]*1e6, voltage[startup], label="PV-powered logic rail")
    axes[0, 0].plot(t[startup]*1e6, clock[startup], label="clock", alpha=0.7)
    axes[0, 0].set(xlabel="Time (µs)", ylabel="Voltage (V)",
                    title="Cold startup: three fitted cells + chosen 2 pF")
    axes[0, 0].legend(fontsize=8)
    steady = t > t[-1]-0.00025
    axes[0, 1].plot(t[steady]*1e3, clock[steady], label="clock")
    axes[0, 1].plot(t[steady]*1e3, data[steady, 7], label="real DFF divide-by-two")
    axes[0, 1].set(xlabel="Time (ms)", ylabel="Voltage (V)", title="Foundry-cell input and output")
    axes[0, 1].legend(fontsize=8)
    cases = [next(r for r in summary["cases"] if r.get("passed") and r["corner"] == c
        and r["voltage_V"] == 1.8 and r["temperature_C"] == 26.85
        and r["ramp_s"] == 100e-6 and r["supply"] == "ideal voltage ramp")
        for c in ("tt", "ss", "ff", "sf", "fs")]
    labels = [r["corner"].upper() for r in cases]
    axes[1, 0].bar(labels, [r["frequency_Hz"]*1e-3 for r in cases], color="#24788d")
    axes[1, 0].set(ylabel="Clock frequency (kHz)", title="Deterministic corners at fixed 1.8 V")
    reference = np.array([r["bias_reference_power_W"] for r in cases])*1e9
    core = np.array([r["analog_clock_power_W"] for r in cases])*1e9-reference
    logic = np.array([r["first_divider_stage_power_W"] for r in cases])*1e9
    axes[1, 1].bar(labels, reference, label="bias reference")
    axes[1, 1].bar(labels, core, bottom=reference, label="oscillator + buffers")
    axes[1, 1].bar(labels, logic, bottom=reference+core, label="first DFF")
    maximum = cases[0]["logic_PV_array_max_W_at_1sun"]*1e9
    axes[1, 1].axhline(maximum, ls="--", color="0.3", label="assumed logic PV maximum")
    axes[1, 1].set(ylabel="Power (nW)", title="Oscillation and power-budget passes differ")
    axes[1, 1].legend(fontsize=7)
    fig.savefig(Path(destination) / "clock_validation.png", dpi=170)
    plt.close(fig)


def run(destination=HERE / "local_runs/published_system", *, with_spice=False):
    dest = Path(destination)
    dest.mkdir(parents=True, exist_ok=True)
    pv_dest = dest / "pv_fit"
    pair, fit = fit_digitized(HERE / "data/s2e_digitized.csv", pv_dest)
    clock_dest = dest / "clock" if with_spice else HERE / "results/clock_final"
    if with_spice:
        from .clock import run_clock_matrix
        summary, _ = run_clock_matrix(clock_dest, pair)
    else:
        summary = json.loads((clock_dest / "summary.json").read_text())
    source_hash = hashlib.sha256((HERE / "circuits/starved_clock.spice").read_bytes()).hexdigest()
    if any(r.get("netlist_sha256") != source_hash for r in summary["cases"]
           if r.get("netlist_sha256")):
        raise ValueError("Cached clock data are stale; rerun with --spice")
    lookup = ClockLookup.from_summary(summary)
    held = summary["withheld_1v75"]
    interpolation_errors = {
        "frequency_relative": abs(lookup.clock(1.75)/held["frequency_Hz"]-1),
        "analog_current_relative": abs(lookup.analog(1.75)
            /(held["analog_clock_power_W"]/1.75)-1)}
    cell = replace(pair, series_cells=1).scaled_current(150/540)
    proxy_voltage = brentq(lambda v: cell.current_A(v/3)-lookup.analog(v)-lookup.first_ff(v),
                           lookup.voltage[0], lookup.voltage[-1])
    direct_pv = next(r for r in summary["cases"] if r["supply"] != "ideal voltage ramp")
    proxy_check = {
        "supply_voltage_relative_error": proxy_voltage/direct_pv["steady_supply_V"]-1,
        "frequency_relative_error": lookup.clock(proxy_voltage)/direct_pv["frequency_Hz"]-1,
        "power_relative_error": proxy_voltage*(lookup.analog(proxy_voltage)
            + lookup.first_ff(proxy_voltage))/direct_pv["mean_power_W"]-1,
        "scope": "Quasi-static clock+first-FF proxy vs direct PV-powered SPICE; supply ripple absent in proxy"}
    p = replace(Parameters(), logic_series_cells=3, actuator_cell_area_um2=540,
                divider=8192, brownout_on_V=1.65, brownout_off_V=1.60,
                effective_switched_F=0.02e-12, logic_storage_F=2e-12,
                actuator_storage_each_F=1e-12)
    # Remaining divider power is an assumption, in addition to the first
    # divider cell's measured SPICE current. Driver model remains behavioral.
    def system(model=pair, *, dt=0.001, light=1):
        return simulate(terminal_table(model), p=p, dt_s=dt, light_scale=light,
                        clock_response=lookup.clock, analog_current_response=lookup.analog,
                        extra_logic_current_response=lookup.first_ff)
    nominal = system()
    fine = system(dt=0.0005)
    trials = np.loadtxt(pv_dest / "pv_sensitivity_samples.csv", delimiter=",", skiprows=1)
    extreme = []
    for index in (np.argmin(trials[:, 4]), np.argmax(trials[:, 4])):
        row = trials[index]
        model = SingleDiodePV(*row[:3], series_cells=2, temperature_K=300)
        extreme.append(system(model)["metrics"])
    light_results = [dict(light_scale=s, **system(light=s)["metrics"]) for s in (0.5, 1, 2)]
    m = nominal["metrics"]
    t = nominal["time_s"]
    steady = (t > 1) & (t < 2.5)
    voltage = nominal["logic_V"][steady]
    reference_W = float(np.mean([v*lookup.reference(v) for v in voltage]))
    analog_W = m["bias_mean_W"]
    first_ff_W = float(np.mean([v*lookup.first_ff(v) for v in voltage]))
    budget = {"reference_bias_mean_W": reference_W,
              "oscillator_and_buffers_mean_W": analog_W-reference_W,
              "first_divider_stage_mean_W": first_ff_W,
              "remaining_logic_estimate_mean_W": m["logic_mean_W"]-first_ff_W,
              "driver_mean_W": m["driver_mean_W"],
              "electrolyte_mean_W": m["electrolyte_mean_W"],
              "faradaic_mean_W": m["faradaic_mean_W"],
              "adsorption_electrical_work_mean_W": m["adsorption_mean_W"]}
    for key, power in list(budget.items()):
        budget[key.replace("mean_W", "J_per_cycle")] = power/m["mean_gait_Hz"]
    voltage_check = [{"series_cells": n, "irradiance_W_m2": e,
                      "no_load_Voc_V": replace(pair, series_cells=n).open_circuit_V(e),
                      "exceeds_1v95": replace(pair, series_cells=n).open_circuit_V(e) > 1.95}
                     for n in (2, 3, 4) for e in (500, 1000, 2000, 5000)]
    convergence = {key: abs(m[key]/fine["metrics"][key]-1)
                   for key in ("mean_gait_Hz", "bending_peak_to_peak_rad",
                               "bias_mean_W", "driver_J_per_cycle")}
    validations = {"clock_interpolation_withheld_1v75": interpolation_errors,
                   "direct_PV_SPICE_comparison": proxy_check,
                   "timestep_relative_changes": convergence,
                   "active_logic_voltage_min_V": float(nominal["logic_V"][nominal["enabled"] > 0].min()),
                   "active_logic_voltage_max_V": float(nominal["logic_V"][nominal["enabled"] > 0].max()),
                   "phase_B_lag_cycles": m["measured_phase_B_lag_cycles"],
                   "electrical_energy_balance_relative_residual": m["electrical_energy_balance_relative_residual"],
                   "scope": "Fitted terminal PV, characterized TT clock; drivers/mechanics remain reduced models"}
    report = {"parameters": nominal["parameters"], "metrics": m, "energy": budget,
              "validation": validations, "illumination_sensitivity": light_results,
              "PV_digitization_extremes": extreme, "no_load_voltage_check": voltage_check,
              "logic_PV_array_max_W": pair.maximum_power_point()[2]/2 * 3 * 150/540,
              "provenance": {"PV": "fit to digitized Fig S2E; large actuator PV pair",
                  "logic_PV": "same cell current density assumed at 150 um²; not measured small IC PV",
                  "clock": "SKY130 TT supply lookup; held-out voltage checked",
                  "remaining_divider": "RTL verified; extra 20 fF switched capacitance and leakage assumed",
                  "electrode_and_mechanics": "uncalibrated reduced model",
                  "storage": "Chosen 2 pF logic and 1 pF per actuator rail; junction capacitance not measured",
                  "startup": "Direct clock SPICE is authoritative; reduced model subthreshold startup load is approximate"}}
    (dest / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    np.savetxt(dest / "waveforms.csv.gz", np.column_stack([nominal[k][::5] for k in (
        "time_s", "logic_V", "positive_V", "negative_magnitude_V", "drive_A_V", "drive_B_V",
        "eta_A_V", "eta_B_V", "electrolyte_bulk_V", "curvature_A_m_inv", "curvature_B_m_inv")]),
        delimiter=",", header="time_s,logic_V,positive_V,negative_magnitude_V,drive_A_V,drive_B_V,"
        "eta_A_V,eta_B_V,electrolyte_bulk_V,curvature_A_m_inv,curvature_B_m_inv", comments="")
    fig, axes = plt.subplots(4, 1, figsize=(10, 10), sharex=True, layout="constrained")
    axes[0].plot(t, nominal["logic_V"], label="3-cell logic adaptation")
    axes[0].plot(t, nominal["positive_V"], label="actuator upper rail")
    axes[0].plot(t, -nominal["negative_magnitude_V"], label="actuator lower rail")
    axes[0].set(ylabel="Voltage (V)", title="Published PV fit + characterized clock; reduced driver/mechanics")
    for leg in ("A", "B"):
        axes[1].plot(t, nominal[f"drive_{leg}_V"], label=f"terminal {leg}")
        axes[2].plot(t, nominal[f"eta_{leg}_V"], label=f"local interface {leg}")
        axes[3].plot(t, nominal[f"curvature_{leg}_m_inv"]*p.hinge_length_um*1e-6,
                     label=f"hinge angle {leg}")
    axes[2].plot(t, nominal["electrolyte_bulk_V"], "--", label="bulk electrolyte")
    axes[1].set(ylabel="Terminal V vs Pt metal")
    axes[2].set(ylabel="Local potential (V)")
    axes[3].set(ylabel="Predicted angle (rad)", xlabel="Time (s)")
    for ax in axes:
        ax.axvspan(3, 3.4, color="0.7", alpha=0.2)
        ax.legend(loc="upper right", fontsize=8)
    fig.savefig(dest / "system.png", dpi=170)
    plt.close(fig)
    plot_clock_validation(summary, clock_dest, dest)
    assert max(interpolation_errors.values()) < 0.05, "Refine clock voltage characterization"
    assert max(convergence.values()) < 0.05
    assert validations["active_logic_voltage_min_V"] >= lookup.voltage[0]
    assert validations["active_logic_voltage_max_V"] <= lookup.voltage[-1]
    assert abs(m["measured_phase_B_lag_cycles"]-0.25) < 0.01
    assert abs(m["electrical_energy_balance_relative_residual"]) < 0.03
    print(json.dumps({"metrics": m, "validation": validations, "energy": budget}, indent=2))
    return report


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=HERE / "local_runs/published_system")
    parser.add_argument("--spice", action="store_true")
    args = parser.parse_args()
    run(args.output, with_spice=args.spice)
