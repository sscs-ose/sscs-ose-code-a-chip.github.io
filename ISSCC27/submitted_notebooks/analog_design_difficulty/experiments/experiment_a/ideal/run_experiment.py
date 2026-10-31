#!/usr/bin/env python3
"""Run the reduced-model study (REDUCED_MODEL_DEFINITION.md) and write its data, figure, and result note."""
from __future__ import annotations

import csv
import json
from pathlib import Path
import sys

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
RESULTS_DATA = REPO / "results" / "data"
RESULTS_FIG = REPO / "results" / "figures"
sys.path.insert(0, str(HERE))

from model import (  # noqa: E402
    SourceParams,
    characteristic_coefficients,
    command_initial_state,
    connected_initial_state,
    equilibrium,
    exact_constant_command,
    gcmd_polynomials,
    integrate_constant_command,
    matched_a3_command_start,
    poles_from_denominator,
    poles_from_state_matrix,
    state_matrix,
    with_updates,
    zout_polynomials,
)


P = SourceParams(
    A_e=9.0,
    tau_d=20e-9,
    Rout=2.0e3,
    Co=0.50e-12,
    Cs=1.00e-12,
    Vtarget=0.90,
)
EPSILON = 2.0e-3
TBLK = 80e-9
A0_START = 0.60
REP_TACQ = 30e-9
REP_DVPREV = 0.30
A3_TMAX = 80e-9
# reader-facing names of the cases in the data file
CASE_NAMES = {"A0": "input_step", "A1": "zero_charge_control", "A2": "connection", "A3": "matched_comparison",
              "A4": "acquisition_times"}


def ensure_dirs() -> None:
    RESULTS_DATA.mkdir(parents=True, exist_ok=True)
    RESULTS_FIG.mkdir(parents=True, exist_ok=True)


def state_at(t: float, x0: np.ndarray, vcmd: float, p: SourceParams = P) -> np.ndarray:
    return exact_constant_command([0.0, t], x0, vcmd, p)[-1]


def error_at(t: float, x0: np.ndarray, vcmd: float, p: SourceParams = P) -> float:
    return abs(state_at(t, x0, vcmd, p)[1] - vcmd)


def validate_model() -> dict:
    C = P.C_total
    A = state_matrix(P)
    xeq = equilibrium(P.Vtarget)
    dc_drive = np.array([(1 + P.A_e) * P.Vtarget / P.tau_d, 0.0])
    dc_residual = A @ xeq + dc_drive
    dc_scale = max(float(np.max(np.abs(A @ xeq))), float(np.max(np.abs(dc_drive))), 1.0)

    poles_poly = np.sort_complex(poles_from_denominator(P))
    poles_state = np.sort_complex(poles_from_state_matrix(P))

    g_num, den = gcmd_polynomials(P)
    z_num, z_den = zout_polynomials(P)

    t = np.linspace(0.0, 80e-9, 801)
    x0 = command_initial_state(A0_START)
    exact = exact_constant_command(t, x0, P.Vtarget, P)
    integ = integrate_constant_command(t, x0, P.Vtarget, P)
    cross_abs = float(np.max(np.abs(exact - integ)))
    cross_rel = float(cross_abs / max(1e-15, np.max(np.abs(exact - equilibrium(P.Vtarget)))))

    # Numeric transfer-function spot checks directly from state-space resolvent.
    freqs = np.array([1e5, 1e6, 1e7, 5e7])
    g_err = []
    z_err = []
    Bc = np.array([(1 + P.A_e) / P.tau_d, 0.0])
    Bi = np.array([0.0, -1.0 / C])
    Cout = np.array([0.0, 1.0])
    for f in freqs:
        s = 1j * 2 * np.pi * f
        Hc_ss = Cout @ np.linalg.solve(s * np.eye(2) - A, Bc)
        Hi_ss = Cout @ np.linalg.solve(s * np.eye(2) - A, Bi)
        D = (P.tau_d * s + 1) * (P.Rout * C * s + 1) + P.A_e
        Hc_an = (1 + P.A_e) / D
        # Hi_ss = Vout / Idist, while the analysis defines Zout_cl = -Vout / Idist.
        Hi_an = -P.Rout * (P.tau_d * s + 1) / D
        g_err.append(abs(Hc_ss - Hc_an))
        z_err.append(abs(Hi_ss - Hi_an))

    return {
        "dc_equilibrium": {
            "Vd_V": float(xeq[0]),
            "Vout_V": float(xeq[1]),
            "max_equation_residual_V_per_s": float(np.max(np.abs(dc_residual))),
            "max_relative_equation_residual": float(np.max(np.abs(dc_residual)) / dc_scale),
        },
        "characteristic_denominator": {
            "coefficients_descending": den.tolist(),
            "formula": "tau_d*Rout*C_T*s^2 + (tau_d + Rout*C_T)*s + (1 + A_e)",
        },
        "poles_rad_per_s": {
            "from_denominator": [[float(x.real), float(x.imag)] for x in poles_poly],
            "from_state_matrix": [[float(x.real), float(x.imag)] for x in poles_state],
            "max_abs_difference": float(np.max(np.abs(poles_poly - poles_state))),
        },
        "Gcmd": {
            "numerator": g_num.tolist(),
            "denominator": den.tolist(),
            "max_complex_spotcheck_error": float(max(g_err)),
        },
        "Zout_cl": {
            "numerator": z_num.tolist(),
            "denominator": z_den.tolist(),
            "definition": "-Vout/Idist",
            "max_complex_spotcheck_error_ohm": float(max(z_err)),
        },
        "exact_vs_solve_ivp": {
            "max_absolute_state_difference_V": cross_abs,
            "max_relative_difference": cross_rel,
        },
    }


def run_cases() -> tuple[dict, dict[str, np.ndarray]]:
    # A0 representative block characterization: 0.60 -> 0.90 V.
    a0_x0 = command_initial_state(A0_START)
    a0_end = state_at(TBLK, a0_x0, P.Vtarget)
    e_cmd = abs(a0_end[1] - P.Vtarget)

    # A1: zero stored-charge difference.
    a1_x0 = connected_initial_state(P, 0.0)
    a1_end = state_at(REP_TACQ, a1_x0, P.Vtarget)
    e_a1 = abs(a1_end[1] - P.Vtarget)

    # A2: representative stored-charge disturbance.
    a2_x0 = connected_initial_state(P, REP_DVPREV)
    a2_end = state_at(REP_TACQ, a2_x0, P.Vtarget)
    e_a2 = abs(a2_end[1] - P.Vtarget)
    e0_a2 = abs(a2_x0[1] - P.Vtarget)

    # A3: exact matched initial output error and same time/capacitance.
    a3_start = matched_a3_command_start(P, REP_DVPREV)
    a3_a0_x0 = command_initial_state(a3_start)
    a3_a2_x0 = a2_x0.copy()
    e0_a0 = abs(a3_a0_x0[1] - P.Vtarget)
    t = np.linspace(0.0, A3_TMAX, 1201)
    a3_cmd = exact_constant_command(t, a3_a0_x0, P.Vtarget, P)
    a3_dist = exact_constant_command(t, a3_a2_x0, P.Vtarget, P)
    cmd_norm = (a3_cmd[:, 1] - P.Vtarget) / (a3_a0_x0[1] - P.Vtarget)
    dist_norm = (a3_dist[:, 1] - P.Vtarget) / (a3_a2_x0[1] - P.Vtarget)
    vd_cmd_norm = (a3_cmd[:, 0] - P.Vtarget) / (a3_a0_x0[1] - P.Vtarget)
    vd_dist_norm = (a3_dist[:, 0] - P.Vtarget) / (a3_a2_x0[1] - P.Vtarget)
    norm_diff = np.abs(cmd_norm - dist_norm)
    i_max = int(np.argmax(norm_diff))

    # A4: same representative disturbance with longer acquisition time.
    a4_times = np.array([REP_TACQ, 45e-9, 60e-9, 80e-9])
    a4_errors = np.array([error_at(ti, a2_x0, P.Vtarget) for ti in a4_times])

    cases = {
        "A0": {
            "command_start_V": A0_START,
            "Vtarget_V": P.Vtarget,
            "Tblk_ns": TBLK * 1e9,
            "Ecmd_mV": e_cmd * 1e3,
            "epsilon_mV": EPSILON * 1e3,
            "pass": bool(e_cmd < EPSILON),
        },
        "A1": {
            "DeltaVprev_V": 0.0,
            "Tacq_ns": REP_TACQ * 1e9,
            "Eacq_mV": e_a1 * 1e3,
            "pass": bool(e_a1 < EPSILON),
        },
        "A2": {
            "DeltaVprev_V": REP_DVPREV,
            "Vprev_V": P.Vtarget - REP_DVPREV,
            "Vout_0plus_V": float(a2_x0[1]),
            "initial_output_error_mV": e0_a2 * 1e3,
            "Tacq_ns": REP_TACQ * 1e9,
            "Eacq_mV": e_a2 * 1e3,
            "epsilon_mV": EPSILON * 1e3,
            "pass": bool(e_a2 < EPSILON),
        },
        "A3": {
            "DeltaVprev_V": REP_DVPREV,
            "matched_A0_command_start_V": a3_start,
            "matched_A0_command_amplitude_V": P.Vtarget - a3_start,
            "input_step_initial_output_error_mV": e0_a0 * 1e3,
            "connection_initial_output_error_mV": e0_a2 * 1e3,
            "initial_error_match_abs_uV": abs(e0_a0 - e0_a2) * 1e6,
            "same_Ctotal_pF": P.C_total * 1e12,
            "comparison_interval_ns": A3_TMAX * 1e9,
            "max_abs_normalized_Vout_difference": float(norm_diff[i_max]),
            "time_of_max_difference_ns": float(t[i_max] * 1e9),
            "normalized_Vout_at_30ns": {
                "command": float(np.interp(REP_TACQ, t, cmd_norm)),
                "disturbance": float(np.interp(REP_TACQ, t, dist_norm)),
                "abs_difference": float(abs(np.interp(REP_TACQ, t, cmd_norm) - np.interp(REP_TACQ, t, dist_norm))),
            },
        },
        "A4": {
            "DeltaVprev_V": REP_DVPREV,
            "Tacq_ns": (a4_times * 1e9).tolist(),
            "Eacq_mV": (a4_errors * 1e3).tolist(),
        },
    }

    arrays = {
        "t": t,
        "a3_cmd": a3_cmd,
        "a3_dist": a3_dist,
        "cmd_norm": cmd_norm,
        "dist_norm": dist_norm,
        "vd_cmd_norm": vd_cmd_norm,
        "vd_dist_norm": vd_dist_norm,
    }
    return cases, arrays


def write_a3_data(arrays: dict[str, np.ndarray]) -> None:
    path = RESULTS_DATA / "reduced_model_equal_time.csv"
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "time_ns",
            "Vout_command_V",
            "Vout_disturbance_V",
            "Vd_command_V",
            "Vd_disturbance_V",
            "normalized_Vout_error_command",
            "normalized_Vout_error_disturbance",
            "normalized_Vd_error_command",
            "normalized_Vd_error_disturbance",
        ])
        for i, ti in enumerate(arrays["t"]):
            w.writerow([
                ti * 1e9,
                arrays["a3_cmd"][i, 1],
                arrays["a3_dist"][i, 1],
                arrays["a3_cmd"][i, 0],
                arrays["a3_dist"][i, 0],
                arrays["cmd_norm"][i],
                arrays["dist_norm"][i],
                arrays["vd_cmd_norm"][i],
                arrays["vd_dist_norm"][i],
            ])


def make_figure_a(arrays: dict[str, np.ndarray]) -> None:
    t_ns = arrays["t"] * 1e9
    fig, axes = plt.subplots(2, 1, figsize=(7.2, 6.2), sharex=True, constrained_layout=True)
    ax = axes[0]
    ax.plot(t_ns, arrays["cmd_norm"], label="Input step (external input)")
    ax.plot(t_ns, arrays["dist_norm"], label="Output-port disturbance (charged Cs connected)")
    ax.axhline(0.0, linewidth=0.8)
    ax.set_ylabel("Normalized Vout error")
    ax.legend(loc="best")
    ax.grid(True, alpha=0.25)
    ax.set_title("Reduced model: input step versus output-port disturbance, matched in time")

    ax2 = axes[1]
    ax2.plot(t_ns, arrays["vd_cmd_norm"], label="Vd, input step")
    ax2.plot(t_ns, arrays["vd_dist_norm"], label="Vd, output-port disturbance")
    ax2.axhline(0.0, linewidth=0.8)
    ax2.set_xlabel("Elapsed time after event (ns)")
    ax2.set_ylabel("Vd error / initial Vout error")
    ax2.legend(loc="best")
    ax2.grid(True, alpha=0.25)

    note = (
        "Matched conditions: Ctotal = Co + Cs = 1.50 pF; initial |Vout−Vtarget| = 200 mV; "
        "same elapsed time. The input step starts with Vd displaced; the output-port disturbance starts with Vd already settled."
    )
    fig.text(0.5, -0.01, note, ha="center", va="top", fontsize=8, wrap=True)
    fig.savefig(RESULTS_FIG / "figure_reduced_model_input_step_vs_connection.png", dpi=180, bbox_inches="tight")
    fig.savefig(RESULTS_FIG / "figure_reduced_model_input_step_vs_connection.svg", bbox_inches="tight",
                metadata={"Date": None})
    plt.close(fig)


def local_sensitivity() -> list[dict]:
    """Small post-baseline sanity check; not an Experiment-A sweep axis."""
    rows = []
    variations = [
        ("A_e", 0.8), ("A_e", 1.2),
        ("tau_d", 0.8), ("tau_d", 1.2),
        ("Rout", 0.8), ("Rout", 1.2),
        ("Co", 0.8), ("Co", 1.2),
    ]
    for name, factor in variations:
        p = with_updates(P, **{name: getattr(P, name) * factor})
        x2 = connected_initial_state(p, REP_DVPREV)
        ea2 = error_at(REP_TACQ, x2, p.Vtarget, p)
        # Matched A3 separation over the same early transient window.
        start = matched_a3_command_start(p, REP_DVPREV)
        xcmd = command_initial_state(start)
        ec0 = xcmd[1] - p.Vtarget
        ed0 = x2[1] - p.Vtarget
        ts = np.linspace(0.0, 40e-9, 401)
        xc = exact_constant_command(ts, xcmd, p.Vtarget, p)
        xd = exact_constant_command(ts, x2, p.Vtarget, p)
        ncmd = (xc[:, 1] - p.Vtarget) / ec0
        ndist = (xd[:, 1] - p.Vtarget) / ed0
        diff = np.abs(ncmd - ndist)
        imax = int(np.argmax(diff))
        rows.append({
            "parameter": name,
            "factor": factor,
            "value": getattr(p, name),
            "connection_error_at_30ns_mV": ea2 * 1e3,
            "matched_max_abs_normalized_difference_0_40ns": float(diff[imax]),
            "matched_time_of_max_difference_ns": float(ts[imax] * 1e9),
        })

    path = RESULTS_DATA / "reduced_model_local_sensitivity.csv"
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    return rows


def write_summary(validation: dict, cases: dict, sensitivity: list[dict]) -> None:
    payload = {
        "baseline": {
            "A_e": P.A_e,
            "tau_d_ns": P.tau_d * 1e9,
            "Rout_ohm": P.Rout,
            "Co_pF": P.Co * 1e12,
            "Cs_pF": P.Cs * 1e12,
            "Ctotal_pF": P.C_total * 1e12,
            "Vtarget_V": P.Vtarget,
            "epsilon_mV": EPSILON * 1e3,
            "Tblk_ns": TBLK * 1e9,
            "representative_Tacq_ns": REP_TACQ * 1e9,
            "representative_DeltaVprev_V": REP_DVPREV,
        },
        "validation": validation,
        "cases": {CASE_NAMES[k]: v for k, v in cases.items()},
        "local_sensitivity": sensitivity,
    }
    (RESULTS_DATA / "reduced_model_summary.json").write_text(json.dumps(payload, indent=2) + "\n")

    a0 = cases["A0"]
    a1 = cases["A1"]
    a2 = cases["A2"]
    a3 = cases["A3"]
    a4 = cases["A4"]
    poles = validation["poles_rad_per_s"]["from_denominator"]
    declared_fail_example_mV = error_at(15e-9, connected_initial_state(P, REP_DVPREV), P.Vtarget) * 1e3
    txt = f"""# Reduced-model study — result

Generated by `run_experiment.py`. Definition: `REDUCED_MODEL_DEFINITION.md`; analysis: `../REDUCED_MODEL_ANALYSIS.md`.

## Parameters

`Ae` = {P.A_e:g}, `τd` = {P.tau_d*1e9:.1f} ns, `Rout` = {P.Rout/1e3:.2f} kΩ, `Co` = {P.Co*1e12:.2f} pF, `Cs` = {P.Cs*1e12:.2f} pF, target {P.Vtarget:.2f} V, error limit {EPSILON*1e3:.1f} mV; input-step test read at {TBLK*1e9:.0f} ns; connection read at {REP_TACQ*1e9:.0f} ns with `Vprev` = target − {REP_DVPREV:.2f} V.

## Model checks

- DC equilibrium residual: {validation['dc_equilibrium']['max_equation_residual_V_per_s']:.3e} V/s (relative {validation['dc_equilibrium']['max_relative_equation_residual']:.3e}).
- Denominator coefficients: {validation['characteristic_denominator']['coefficients_descending']}.
- Poles from `D(s)`: {poles} rad/s; the state-matrix poles agree within {validation['poles_rad_per_s']['max_abs_difference']:.3e} rad/s.
- `Gin` (`Gcmd`) state-space against analytical spot check: largest complex error {validation['Gcmd']['max_complex_spotcheck_error']:.3e}.
- `Zout` state-space against analytical spot check: largest complex error {validation['Zout_cl']['max_complex_spotcheck_error_ohm']:.3e} Ω.
- Exact matrix-exponential solution against `solve_ivp`: largest state difference {validation['exact_vs_solve_ivp']['max_absolute_state_difference_V']:.3e} V.

## Cases

- **Input step**, error at {a0['Tblk_ns']:.0f} ns: {a0['Ecmd_mV']:.4f} mV, **{'PASS' if a0['pass'] else 'FAIL'}** against {EPSILON*1e3:.1f} mV.
- **Zero-charge control**, error at {a1['Tacq_ns']:.0f} ns: {a1['Eacq_mV']:.4f} mV, **{'PASS' if a1['pass'] else 'FAIL'}**.
- **Connection of a charged capacitor** (`Vprev` = target − {a2['DeltaVprev_V']:.2f} V): `Vout(0+)` = {a2['Vout_0plus_V']:.4f} V, initial output error {a2['initial_output_error_mV']:.1f} mV; error at {a2['Tacq_ns']:.0f} ns {a2['Eacq_mV']:.4f} mV, **{'PASS' if a2['pass'] else 'FAIL'}**.
- **Matched comparison**: initial output errors differ by {a3['initial_error_match_abs_uV']:.3e} µV; both use {a3['same_Ctotal_pF']:.2f} pF and the same time axis. The largest difference between the normalized output errors is **{a3['max_abs_normalized_Vout_difference']:.4f}** at {a3['time_of_max_difference_ns']:.2f} ns. At 30 ns the normalized errors are {a3['normalized_Vout_at_30ns']['command']:.4f} (input step) and {a3['normalized_Vout_at_30ns']['disturbance']:.4f} (connection).
- **Acquisition times** {a4['Tacq_ns']} ns for the connection: errors {[round(x, 5) for x in a4['Eacq_mV']]} mV.

## Reading

With the same output capacitance, the same initial output error, and the same time axis, the input step starts with both `Vd` and `Vout` displaced, while the connection starts with `Vd` settled. The output transients do not collapse onto one waveform, as the analysis predicts. Shorter acquisition intervals fail for the connection (for example {declared_fail_example_mV:.2f} mV at 15 ns); that is a timing-allocation effect and is not what establishes the port difference. The local ±20 % check is in `reduced_model_local_sensitivity.csv`. The model is a qualitative mechanism model, a counterexample: it shows that one additional internal state makes the two tests non-equivalent. It is not a quantitative macromodel of the SKY130 driver, and its values are not fitted to it.
"""
    (HERE / "REDUCED_MODEL_RESULT.md").write_text(txt)


def main() -> None:
    ensure_dirs()
    validation = validate_model()
    cases, arrays = run_cases()
    write_a3_data(arrays)
    make_figure_a(arrays)
    sensitivity = local_sensitivity()
    write_summary(validation, cases, sensitivity)
    print(json.dumps({"validation": validation, "cases": cases}, indent=2))


if __name__ == "__main__":
    main()
