"""Transistor drivers and a deliberately unaccepted brownout candidate.

Standalone interface benches; the complete divider/POR/clock is not simulated
as one transistor circuit. Driver ready/phase stimuli and logic rail are ideal.
"""

from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from opentcad.device.compact import SingleDiodePV

HERE = Path(__file__).parent


def run_deck(destination, deck, *, filename="bench.spice", timeout=180):
    """Run an installed ngspice; retain exact deck/log, fail on process errors."""
    executable = shutil.which("ngspice")
    if not executable:
        raise FileNotFoundError("Optional ngspice executable is not installed")
    dest = Path(destination).resolve()
    dest.mkdir(parents=True, exist_ok=True)
    (dest / ".spiceinit").write_text("set ngbehavior=hsa\nset num_threads=1\n")
    (dest / filename).write_text(deck)
    result = subprocess.run(
        [executable, "-b", filename], cwd=dest, capture_output=True, text=True, timeout=timeout
    )
    log = result.stdout + result.stderr
    (dest / "ngspice.log").write_text(log)
    if result.returncode or "simulation(s) aborted" in log or "doAnalyses:" in log:
        raise RuntimeError(f"ngspice failed; see {dest / 'ngspice.log'}")
    return dest


def header(corner="tt", temperature_C=26.85):
    if corner not in {"tt", "ss", "ff", "sf", "fs"}:
        raise ValueError("Unsupported deterministic process corner")
    pdk = Path(os.environ.get("PDK_ROOT", "/usr/local/share/pdk")) / "sky130A"
    library = pdk / "libs.tech/ngspice/sky130.lib.spice"
    if not library.is_file():
        raise FileNotFoundError(library)
    return (
        f"* OpenTCAD microrobot interface experiment\n.lib {library} {corner}\n"
        f".temp {temperature_C}\n"
    )


def mean_power(t, power, start=0.343333, stop=1.009999):
    """Integrate over two complete commanded gait cycles, including endpoints."""
    select = (t > start) & (t < stop)
    times = np.r_[start, t[select], stop]
    values = np.r_[np.interp(start, t, power), power[select], np.interp(stop, t, power)]
    return float(np.trapezoid(values, times) / (stop - start))


def driver_case(
    destination,
    *,
    corner="tt",
    temperature_C=26.85,
    timestep_s=50e-6,
    edge_s=10e-9,
    irradiance_W_m2=1000,
):
    fit = json.loads((HERE / "results/published/pv_fit.json").read_text())
    cell = replace(SingleDiodePV(**fit["fitted_terminal_model"]), series_cells=1)
    circuit = (HERE / "circuits/actuator_driver.spice").read_text()
    electrode = (HERE / "circuits/electrochemical.spice").read_text()
    deck = (
        header(corner, temperature_C)
        + circuit
        + "\n"
        + electrode
        + f"""
* PV model held at its fitted 300 K; electronics temperature is varied separately.
.model fitted_cell D(IS={cell.saturation_A:.12g} N={cell.ideality:.12g} TNOM=26.85 EG=0 XTI=0)
Vlight light 0 PWL(0 0 100u 0 1m {irradiance_W_m2})
Bphlo 0 celllo I={{{cell.photocurrent_A:.12g}*v(light)/1000}}
Dlo celllo 0 fitted_cell TEMP=26.85
Vpvlo celllo mid 0
Bphhi mid cellhi I={{{cell.photocurrent_A:.12g}*v(light)/1000}}
Dhi cellhi mid fitted_cell TEMP=26.85
Vpvhi cellhi act_raw 0
Vact act_raw act 0
Cstorelo mid 0 1p
Cstorehi act_raw mid 1p
Vlogic logic_raw 0 PWL(0 0 1m 0 2m 1.77 1.2 1.77 1.201 0 1.4 0 1.401 1.77)
Vlogicsense logic_raw logic 0
VcommandA cmdA 0 PULSE(0 1 10m {edge_s} {edge_s} 0.166666 0.333333)
VcommandB cmdB 0 PULSE(0 1 93.333m {edge_s} {edge_s} 0.166666 0.333333)
BphaseA phaseA_source 0 V={{v(cmdA)*v(logic)}}
BphaseB phaseB_source 0 V={{v(cmdB)*v(logic)}}
VphaseA phaseA_source pa 0
VphaseB phaseB_source pb 0
* Explicit external ready stimulus: this bench does not validate the detector.
Venable en 0 PWL(0 0 4m 0 4.001m 1 1.199 1 1.199001 0 1.403 0 1.403001 1)
Bready ready_source 0 V={{v(en)*v(act)}}
Vready ready_source ready 0
Xda pa ready ea logic act mid 0 microrobot_driver
Xdb pb ready eb logic act mid 0 microrobot_driver
Xea ea sa ta micro_electrode
Xeb eb sb tb micro_electrode
Xreturn mid sr tr micro_electrode cdl=400p qmax=2600p rf=1g
Rsa sa bulk 10meg
Rsb sb bulk 10meg
Rsr sr bulk 1meg
.options method=gear maxord=2 reltol=1e-4 abstol=1e-15
.control
set wr_vecnames
set wr_singlescale
tran {timestep_s} 2 0 {timestep_s}
wrdata driver.dat v(act) v(mid) v(logic) v(ready) v(pa) v(pb) v(ea) v(eb) v(sa) v(sb) v(bulk) v(ta) v(tb) i(Vact) i(Vlogicsense) i(Vpvlo) i(Vpvhi) i(VphaseA) i(VphaseB) i(Vready)
quit
.endc
.end
"""
    )
    dest = run_deck(destination, deck)
    data = np.loadtxt(dest / "driver.dat", skiprows=1)
    (
        t,
        act,
        mid,
        logic,
        ready,
        pa,
        pb,
        ea,
        eb,
        sa,
        sb,
        bulk,
        ta,
        tb,
        ia,
        il,
        iplo,
        iphi,
        ipa,
        ipb,
        ir,
    ) = data.T
    steady = (t > 0.1) & (t < 1.19)
    neutral = (t > 1.22) & (t < 1.39)
    # Check settled outputs, excluding a 2 ms interval around phase transitions.
    phases = np.mod(t - 0.01, 0.333333)
    phases_b = np.mod(t - 0.093333, 0.333333)
    quiet_a = (phases > 0.002) & (phases < 0.331333) & (abs(phases - 0.166666) > 0.002)
    quiet_b = (phases_b > 0.002) & (phases_b < 0.331333) & (abs(phases_b - 0.166666) > 0.002)
    # Either channel's edge couples through the shared electrolyte/midpoint.
    # Settled error excludes both channels' transitions; peak checks use ALL samples.
    valid_a = valid_b = steady & quiet_a & quiet_b
    error_a = abs(ea - np.where(pa > logic / 2, act, 0))
    error_b = abs(eb - np.where(pb > logic / 2, act, 0))
    pv_power = mid * iplo + (act - mid) * iphi
    metrics = dict(
        corner=corner,
        temperature_C=temperature_C,
        timestep_s=timestep_s,
        edge_s=edge_s,
        irradiance_W_m2=irradiance_W_m2,
        minimum_actuator_span_after_start_V=float(act[t > 0.01].min()),
        minimum_electrode_V=float(min(ea.min(), eb.min())),
        maximum_electrode_above_upper_rail_V=float(max((ea - act).max(), (eb - act).max())),
        settled_output_error_V=float(max(error_a[valid_a].max(), error_b[valid_b].max())),
        reset_clamp_error_after_20ms_V=float(
            max(abs(ea[neutral] - mid[neutral]).max(), abs(eb[neutral] - mid[neutral]).max())
        ),
        actuator_PV_mean_W=mean_power(t, pv_power),
        driver_logic_supply_mean_W=mean_power(t, logic * il),
        phase_input_stimulus_mean_W=mean_power(t, pa * ipa + pb * ipb),
        ready_input_stimulus_mean_W=mean_power(t, ready * ir),
        phase_A_eta_peak_to_peak_V=float(np.ptp((ea - sa)[steady])),
        circuit_sha256=hashlib.sha256(circuit.encode()).hexdigest(),
        electrode_sha256=hashlib.sha256(electrode.encode()).hexdigest(),
        scope="Finite actuator PV + two transistor drivers + reduced electrode interfaces; ideal logic/phase/ready sources",
    )
    metrics["passed"] = bool(
        metrics["minimum_electrode_V"] > -0.1
        and metrics["maximum_electrode_above_upper_rail_V"] < 0.1
        and metrics["settled_output_error_V"] < 0.02
        and metrics["reset_clamp_error_after_20ms_V"] < 0.05
    )
    metrics["acceptance"] = (
        "Own preliminary limits: excursions <100mV; settled error <20mV; clamp error <50mV after 20ms"
    )
    (dest / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")
    names = "time_s,act_V,mid_V,logic_V,ready_V,phase_A_V,phase_B_V,electrode_A_V,electrode_B_V,solution_A_V,solution_B_V,bulk_V,theta_A,theta_B,actuator_rail_A,logic_A,pv_lower_A,pv_upper_A,phase_A_A,phase_B_A,ready_A"
    np.savetxt(
        dest / "waveform.csv.gz",
        data[:: max(1, len(data) // 2000)],
        delimiter=",",
        header=names,
        comments="",
    )
    return metrics, data


def brownout_case(
    destination, *, corner="tt", temperature_C=26.85, actuator_V=1.245, timestep_s=20e-6,
    circuit_path=None,
):
    circuit = Path(circuit_path or HERE / "circuits/brownout_candidate.spice").read_text()
    deck = (
        header(corner, temperature_C)
        + circuit
        + f"""
Vact act 0 {actuator_V}
Vlogic logic 0 PWL(0 0 1m 0 21m 1.94 23m 1.94 43m 0)
* Exact unloaded NMOS stack from the existing clock generates bn.
Xb1 bn bn 0 0 sky130_fd_pr__nfet_01v8 w=0.5 l=8
Xb2 b2 b2 bn 0 sky130_fd_pr__nfet_01v8 w=0.5 l=8
Xb3 logic logic b2 0 sky130_fd_pr__nfet_01v8 w=0.5 l=8
Xd bn ready act 0 microrobot_brownout
Cload ready 0 30f
.options method=gear maxord=2 reltol=1e-4 abstol=1e-15
.control
set wr_vecnames
set wr_singlescale
tran {timestep_s} 44m 0 {timestep_s}
wrdata brownout.dat v(logic) v(bn) v(ready) v(xd.ref) v(xd.sense) i(Vact)
quit
.endc
.end
"""
    )
    dest = run_deck(destination, deck)
    data = np.loadtxt(dest / "brownout.dat", skiprows=1)
    t, vlogic, bn, ready, reference, sense, current = data.T

    def crossing(rising):
        mask = (
            ((ready[:-1] < actuator_V / 2) & (ready[1:] >= actuator_V / 2))
            if rising
            else ((ready[:-1] >= actuator_V / 2) & (ready[1:] < actuator_V / 2))
        )
        indices = np.flatnonzero(mask & ((t[:-1] < 0.021) if rising else (t[:-1] > 0.023)))
        if len(indices) != 1:
            return None
        i = indices[0]
        f = (actuator_V / 2 - ready[i]) / (ready[i + 1] - ready[i])
        return float(vlogic[i] + f * (vlogic[i + 1] - vlogic[i]))

    on, off = crossing(True), crossing(False)
    i = np.flatnonzero(t < 0.021)[np.argmin(abs(vlogic[t < 0.021] - 1.77))]
    result = dict(
        corner=corner,
        temperature_C=temperature_C,
        actuator_V=actuator_V,
        turn_on_V=on,
        turn_off_V=off,
        hysteresis_V=on - off if on and off else None,
        power_at_1v77_W=float(-current[i] * actuator_V),
        timestep_s=timestep_s,
        circuit_sha256=hashlib.sha256(circuit.encode()).hexdigest(),
        method="Slow supply ramp; DC sweep branch switching is not accepted as hysteresis evidence",
        status="development candidate; not accepted for complete corner envelope",
    )
    (dest / "metrics.json").write_text(json.dumps(result, indent=2) + "\n")
    np.savetxt(
        dest / "waveform.csv.gz",
        data[:: max(1, len(data) // 1500)],
        delimiter=",",
        header="time_s,logic_V,bias_n_V,ready_V,reference_V,sense_V,actuator_current_A",
        comments="",
    )
    return result, data


def run(destination=HERE / "local_runs/electrical_v2"):
    dest = Path(destination)
    drivers = []
    nominal = None
    for corner in ("tt", "ss", "ff", "sf", "fs"):
        result, data = driver_case(dest / f"driver_{corner}", corner=corner)
        drivers.append(result)
        if corner == "tt":
            nominal = data
        print("driver", corner, result["passed"], flush=True)
    fine, _ = driver_case(dest / "driver_timestep_half", timestep_s=25e-6)
    slow, _ = driver_case(dest / "driver_slow_inputs", edge_s=1e-6)
    hot, _ = driver_case(dest / "driver_hot", temperature_C=85)
    half, _ = driver_case(dest / "driver_half_light", irradiance_W_m2=500)
    reset = []
    cases = [(c, 26.85, 1.245) for c in ("tt", "ss", "ff", "sf", "fs")]
    cases += [("tt", t, 1.245) for t in (0, 85)] + [("tt", 26.85, v) for v in (1.20, 1.28)]
    for corner, temp, voltage in cases:
        result, _ = brownout_case(
            dest / f"reset_{corner}_{temp}_{voltage}",
            corner=corner,
            temperature_C=temp,
            actuator_V=voltage,
        )
        reset.append(result)
        print("reset", corner, temp, voltage, result["turn_on_V"], result["turn_off_V"], flush=True)
    convergence = {
        key: abs(drivers[0][key] / fine[key] - 1)
        for key in ("actuator_PV_mean_W", "phase_A_eta_peak_to_peak_V")
    }
    report = dict(
        drivers=drivers,
        driver_timestep_half=fine,
        driver_slow_inputs=slow,
        driver_hot=hot,
        driver_half_light=half,
        driver_timestep_relative_changes=convergence,
        brownout=reset,
        brownout_decision="Reject as complete PVT solution: FS turn-on exceeds measured FS PV-powered clock rail; hot behavior also needs redesign",
    )
    (dest / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
    render_driver(dest, nominal)
    return report


def render_driver(dest, nominal):
    """Render recorded voltages; do not recompute metrics from decimated data."""
    t = nominal[:, 0]
    fig, axes = plt.subplots(3, 1, figsize=(10, 8), sharex=True, layout="constrained")
    axes[0].plot(t, nominal[:, 1], label="actuator span")
    axes[0].plot(t, nominal[:, 2], label="Pt midpoint versus VSS")
    axes[0].plot(t, nominal[:, 3], label="ideal logic span")
    for index, name in ((7, "A"), (8, "B")):
        axes[1].plot(t, nominal[:, index] - nominal[:, 2], label=f"electrode {name} versus Pt")
        axes[2].plot(t, nominal[:, index] - nominal[:, index + 2], label=f"local interface {name}")
    for ax in axes:
        ax.legend(fontsize=8)
        ax.set(ylabel="Voltage (V)")
        ax.axvspan(1.199, 1.403, color="0.7", alpha=0.2)
    axes[0].set(title="Transistor drivers + finite actuator PV; external ready/phase stimuli")
    axes[2].set(xlabel="Time (s)")
    fig.savefig(dest / "drivers.png", dpi=170)
    plt.close(fig)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=HERE / "local_runs/electrical_v2")
    run(parser.parse_args().output)
