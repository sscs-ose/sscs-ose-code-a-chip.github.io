"""SKY130 clock candidate: electrical validation before physical layout.

Uses installed ngspice/PDK only; transistor parameters come from SKY130.
PV data, geometry choices and circuit corner tests retain separate provenance.
"""
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

import numpy as np

from opentcad.device.compact import SingleDiodePV

HERE = Path(__file__).parent


def _actual_stop(data):
    if data is None or not np.size(data):
        return None
    value = data[-1, 0] if data.ndim == 2 else data[0] if data.ndim == 1 else np.nan
    return float(value) if np.isfinite(value) else None


def _clock_data_error(data, expected_columns, stop_s):
    """Only wrdata rounding (1e-8 relative/1ps) may separate final/requested time."""
    if data.ndim != 2 or len(data) < 2 or data.shape[1] != expected_columns:
        return f'invalid transient shape; expected at least 2 rows and {expected_columns} columns'
    if not np.isfinite(data).all():
        return 'nonfinite transient data'
    t = data[:, 0]
    if t[0] < 0 or not np.isclose(t[0], 0., rtol=0., atol=1e-12):
        return 'transient does not start at zero'
    if np.any(np.diff(t) < 0):
        return 'transient time decreases'
    if not np.isclose(t[-1], stop_s, rtol=1e-8, atol=1e-12):
        return f'transient stop {t[-1]:.12g} s does not match requested {stop_s:.12g} s'
    return None


def _clock_failure(dest, reason, corner, stop_s, data=None):
    actual = _actual_stop(data)
    if (data is None or data.ndim != 2) and (dest/'clock.dat').is_file():
        try:
            times = np.loadtxt(dest/'clock.dat', skiprows=1, usecols=0, ndmin=1)
            actual = float(times[-1]) if len(times) and np.isfinite(times[-1]) else None
        except (ValueError, OSError):
            actual = None
    info = {'passed': False, 'failure': reason, 'corner': corner,
            'stop_s': stop_s, 'requested_stop_s': stop_s, 'actual_stop_s': actual,
            'requested_stop_reached': bool(actual is not None and
                np.isclose(actual, stop_s, rtol=1e-8, atol=1e-12)),
            'scope': 'Rejected clock experiment; no new metrics or preview emitted'}
    (dest/'failure.json').write_text(json.dumps(info, indent=2)+'\n')
    return info, None


def clock_case(destination, *, corner="tt", voltage_V=1.8, temperature_C=26.85,
               ramp_s=100e-6, stop_s=0.004, timestep_s=50e-9, pv_model=None,
               output_load_F=0.0, pv_storage_F=2e-12, load_standard_cell=True,
               circuit_path=None, relative_tolerance=1e-4, measure_bias_current=True):
    """Simulate cold startup without initial-condition/UIC or electrical kick.

    The source starts at zero, then ramps; intentional 10/12 fF asymmetry is
    part of the design. Pass ``pv_model`` for an illuminated three-cell supply,
    using 150 um²/cell under an explicitly assumed identical-current-density
    scaling from the measured large cell. PV capacitance is not inferred;
    a chosen 2 pF storage capacitor is external to this clock macro. A real
    SKY130 DFF plus feedback inverter loads the clock by default; its supply
    current is measured separately from the analog clock. Set
    measure_bias_current=False for a supplied physical macro without internal
    Vbias; its separate bias power is unavailable, not zero. This option does
    not edit the supplied circuit. Whole-clock/receiver currents remain measured.
    """
    if corner not in {"tt", "ss", "ff", "sf", "fs"}:
        raise ValueError("Unknown process corner")
    if not 0 < relative_tolerance <= 1e-3:
        raise ValueError("Relative tolerance must be positive and at most 1e-3")
    if not 1.4 <= voltage_V <= 1.94 or not -40 <= temperature_C <= 125:
        raise ValueError("Outside this candidate's experiment envelope")
    executable = shutil.which("ngspice")
    if not executable:
        raise FileNotFoundError("ngspice is required for this optional experiment")
    pdk = Path(os.environ.get("PDK_ROOT", "/usr/local/share/pdk")) / "sky130A"
    library = pdk / "libs.tech/ngspice/sky130.lib.spice"
    if not library.is_file():
        raise FileNotFoundError(f"Missing installed PDK library: {library}")
    dest = Path(destination).resolve()
    dest.mkdir(parents=True, exist_ok=True)
    (dest / ".spiceinit").write_text("set ngbehavior=hsa\nset num_threads=1\n")
    circuit = Path(circuit_path or HERE / "circuits/starved_clock.spice").read_text()
    if pv_model is None:
        supply = f"VDD supply 0 PWL(0 0 1u 0 {ramp_s+1e-6:.12g} {voltage_V})\n"
        supply_kind = "ideal voltage ramp"
    else:
        cell = replace(pv_model, series_cells=1).scaled_current(150 / 540)
        a = cell.photocurrent_A
        n = cell.ideality
        supply = (f"Vlight illumination 0 PWL(0 0 1u 0 {ramp_s+1e-6:.12g} 1000)\n"
                  f".model fitted_pv D(IS={cell.saturation_A:.12g} N={n:.12g} "
                  f"TNOM={cell.temperature_K-273.15:.12g} EG=0 XTI=0)\n"
                  f"Bph1 0 pv1 I={{{a:.12g}*v(illumination)/1000}}\n"
                  f"Bph2 pv1 pv2 I={{{a:.12g}*v(illumination)/1000}}\n"
                  f"Bph3 pv2 supply I={{{a:.12g}*v(illumination)/1000}}\n"
                  "Dp1 pv1 0 fitted_pv\nDp2 pv2 pv1 fitted_pv\n"
                  f"Dp3 supply pv2 fitted_pv\nCstore supply 0 {pv_storage_F:.12g}\n")
        supply_kind = "three scaled S2E-fit cells, optical ramp, chosen storage capacitor"
    digital = "Vlogic supply digital_supply 0\n"
    source_cell_hash = None
    if load_standard_cell:
        cell_library = pdk / "libs.ref/sky130_fd_sc_hd/spice/sky130_fd_sc_hd.spice"
        cells = cell_library.read_text()
        selected = []
        for name in ("sky130_fd_sc_hd__dfxtp_1", "sky130_fd_sc_hd__inv_1"):
            match = re.search(r"(?ms)^\.subckt " + name + r"\b.*?^\.ends[^\n]*", cells)
            if match is None:
                raise ValueError(f"Installed standard-cell library lacks {name}")
            selected.append(match.group())
        first_cell = re.search(r"(?m)^\.subckt\b", cells)
        imported = cells[:first_cell.start()]+"\n".join(selected)+"\n"
        (dest / "receiver_cells.spice").write_text(imported)
        source_cell_hash = hashlib.sha256(imported.encode()).hexdigest()
        digital += ('.include "receiver_cells.spice"\n'
                    "Xff clk feedback 0 0 digital_supply digital_supply div2 sky130_fd_sc_hd__dfxtp_1\n"
                    "Xfeedback div2 0 0 digital_supply digital_supply feedback sky130_fd_sc_hd__inv_1\n")
    else:
        digital += "Runused digital_supply 0 1e20\nRprobe div2 0 1e20\n"
    bias_vector = " i(v.xclock.vbias)" if measure_bias_current else ""
    deck = (f"* Our low-power clock candidate; {supply_kind}\n"
            f'.lib "{library}" {corner}\n.temp {temperature_C:.12g}\n'
            + circuit + "\n" + supply
            + "Vsense supply vdd 0\nXclock clk vdd 0 bn bp microrobot_clock\n"
            + digital
            + f"Coutput clk 0 {output_load_F:.12g}\n"
            + f".options method=gear maxord=2 reltol={relative_tolerance:.12g} abstol=1e-15\n"
            + ".control\nset wr_vecnames\nset wr_singlescale\n"
            + f"tran {timestep_s:.12g} {stop_s:.12g} 0 {timestep_s:.12g}\n"
            + "wrdata clock.dat v(vdd) v(clk) v(bn) v(bp) i(Vsense) i(Vlogic) v(div2)"+bias_vector+"\n"
            + "quit\n.endc\n.end\n")
    (dest / "clock.spice").write_text(deck)
    try:
        result = subprocess.run([executable, "-b", "clock.spice"], cwd=dest,
                                capture_output=True, text=True, timeout=180)
    except subprocess.TimeoutExpired as exc:
        output = exc.stdout or ''
        error = exc.stderr or ''
        if isinstance(output, bytes):
            output = output.decode(errors='replace')
        if isinstance(error, bytes):
            error = error.decode(errors='replace')
        (dest / "ngspice.log").write_text(str(exc)+'\n'+output+error)
        return _clock_failure(dest, 'simulation timeout', corner, stop_s)
    log = result.stdout + result.stderr
    (dest / "ngspice.log").write_text(log)
    data = None
    load_error = None
    if (dest/'clock.dat').is_file():
        try:
            data = np.loadtxt(dest/'clock.dat', skiprows=1)
        except (ValueError, OSError) as exc:
            load_error = str(exc)
    if result.returncode:
        return _clock_failure(dest, 'simulator error', corner, stop_s, data)
    if any(marker in log.lower() for marker in
           ['simulation(s) aborted', 'doanalyses:', 'timestep too small']):
        return _clock_failure(dest, 'simulator aborted transient; see ngspice.log',
                              corner, stop_s, data)
    if data is None:
        return _clock_failure(dest, 'missing or malformed clock.dat'+
                              (': '+load_error if load_error else ''), corner, stop_s)
    invalid = _clock_data_error(data, 9 if measure_bias_current else 8, stop_s)
    if invalid:
        return _clock_failure(dest, invalid, corner, stop_s, data)
    t, vdd, clk, bn, bp, analog_current, digital_current, div2 = data[:, :8].T
    bias_current = data[:, 8] if measure_bias_current else None
    select = t > max(0.6 * stop_s, ramp_s * 1.2)
    if np.count_nonzero(select) < 2 or np.ptp(t[select]) <= 0:
        return _clock_failure(dest, 'insufficient steady-window samples', corner, stop_s, data)
    preview_step = max(1, len(data)//1200)
    preview_columns = ('time_s,supply_V,clock_V,bias_n_V,bias_p_V,analog_current_A,'
                       'first_ff_current_A,divide2_V')
    if measure_bias_current:
        preview_columns += ',reference_current_A'
    np.savetxt(dest/'waveform.csv.gz', data[::preview_step], delimiter=',', fmt='%.9e',
               header=preview_columns, comments='')
    current = analog_current + digital_current
    rail = float(np.mean(vdd[select]))
    threshold = vdd / 2
    crossings = np.flatnonzero((clk[:-1] < threshold[:-1]) & (clk[1:] >= threshold[1:]))
    crossings = crossings[t[crossings] > t[select][0]]
    times = t[crossings] + (threshold[crossings]-clk[crossings]) * (
        t[crossings+1]-t[crossings]) / (clk[crossings+1]-clk[crossings])
    frequency = float(1 / np.mean(np.diff(times))) if len(times) >= 5 else None
    divided_crossings = np.flatnonzero((div2[:-1] < threshold[:-1])
        & (div2[1:] >= threshold[1:]) & select[1:])
    divided_frequency = float(1 / np.mean(np.diff(t[divided_crossings]))) \
        if len(divided_crossings) >= 3 else None
    power = float(np.trapezoid((vdd * current)[select], t[select]) / np.ptp(t[select]))
    startup = np.flatnonzero((clk[:-1] < threshold[:-1]) & (clk[1:] >= threshold[1:])
                            & (vdd[1:] > rail*0.8))
    passed = bool(frequency and np.min(clk[select]) < 0.1*rail
                  and np.max(clk[select]) > 0.9*rail and power > 0)
    if load_standard_cell:
        passed = bool(passed and divided_frequency
                      and abs(divided_frequency/frequency - 0.5) < 0.025)
    info = {"passed": passed, "corner": corner, "voltage_V": voltage_V,
            "passed_meaning": "sustained clock, full output swing and first DFF divide-by-two; not a PV power-budget pass",
            "temperature_C": temperature_C, "ramp_s": ramp_s, "stop_s": stop_s,
            "requested_stop_s": stop_s, "actual_stop_s": float(t[-1]),
            "simulation_completed": True, "measure_bias_current": bool(measure_bias_current),
            "max_timestep_s": timestep_s, "relative_tolerance": relative_tolerance,
            "output_load_F": output_load_F,
            "supply": supply_kind, "steady_supply_V": rail, "frequency_Hz": frequency,
            "mean_power_W": power,
            "analog_clock_power_W": float(np.trapezoid((vdd*analog_current)[select],
                                                        t[select]) / np.ptp(t[select])),
            "bias_reference_power_W": (float(np.trapezoid((vdd*bias_current)[select],
                                                          t[select]) / np.ptp(t[select]))
                                       if measure_bias_current else None),
            "bias_reference_power_available": bool(measure_bias_current),
            "bias_reference_measurement": ('internal Vbias current' if measure_bias_current
                                           else 'unavailable: internal bias measurement not requested'),
            "first_divider_stage_power_W": float(np.trapezoid((vdd*digital_current)[select],
                                                               t[select]) / np.ptp(t[select])),
            "mean_current_A": float(np.trapezoid(current[select], t[select]) / np.ptp(t[select])),
            "pv_storage_F": pv_storage_F if pv_model else None,
            "standard_cell_receiver": load_standard_cell,
            "standard_cells_sha256": source_cell_hash,
            "first_divider_output_Hz": divided_frequency,
            "clock_min_V": float(np.min(clk[select])),
            "clock_max_V": float(np.max(clk[select])),
            "first_high_crossing_s": float(t[startup[0]]) if len(startup) else None,
            "bias_n_mean_V": float(np.mean(bn[select])),
            "bias_p_mean_V": float(np.mean(bp[select])),
            "netlist_sha256": hashlib.sha256(circuit.encode()).hexdigest(),
            "library_sha256": hashlib.sha256(library.read_bytes()).hexdigest(),
            "startup": "zero supply operating point, then ramp; no UIC or seeded node voltage",
            "waveform_csv": "Decimated for plots only; metrics use the full transient",
            "limitations": ["Supply/temperature dependent bias, not a PTAT reference",
                ("PDK MIM timing/bias capacitors; canonical schematic routing is not extracted"
                 if circuit_path is None else
                 "Extraction coverage follows supplied-netlist provenance; this bench does not extract or infer coverage from its filename"),
                "No statistical mismatch; remaining divider and drivers not in this bench"]}
    if not passed:
        info["failure"] = "clock swing, power or first-DFF divide-by-two check failed"
    (dest / "metrics.json").write_text(json.dumps(info, indent=2) + "\n")
    return info, data


def run_clock_matrix(destination, model: SingleDiodePV):
    dest = Path(destination)
    cases = [("tt", v, 26.85, 100e-6) for v in (1.6, 1.7, 1.8, 1.9, 1.94)]
    cases += [(corner, 1.8, 26.85, 100e-6) for corner in ("ss", "ff", "sf", "fs")]
    cases += [("tt", 1.8, temp, 100e-6) for temp in (0, 85)]
    cases += [("tt", 1.8, 26.85, 2e-3)]
    results = []
    for corner, v, temp, ramp in cases:
        name = f"{corner}_{v}_{temp}_{ramp}"
        result, _ = clock_case(dest / name, corner=corner, voltage_V=v,
                               temperature_C=temp, ramp_s=ramp,
                               stop_s=max(0.004, ramp*3), output_load_F=2e-15)
        results.append(result)
        print(name, result.get("frequency_Hz"), result.get("mean_power_W"),
              "PASS" if result["passed"] else "FAIL", flush=True)
    pv, data = clock_case(dest / "pv_startup", pv_model=model,
                          stop_s=0.004, timestep_s=50e-9, output_load_F=2e-15)
    results.append(pv)
    for corner in ("sf", "fs"):
        loaded, _ = clock_case(dest / f"pv_startup_{corner}", pv_model=model,
            corner=corner, stop_s=0.004, timestep_s=50e-9, output_load_F=2e-15)
        results.append(loaded)
    smaller_storage, _ = clock_case(dest / "pv_storage_1pf", pv_model=model,
        stop_s=0.004, timestep_s=50e-9, output_load_F=2e-15, pv_storage_F=1e-12)
    held_out, _ = clock_case(dest / "withheld_1v75", voltage_V=1.75,
                             output_load_F=2e-15)
    # Halve timestep at the nominal operating point and compare electrical metrics.
    finer, _ = clock_case(dest / "timestep_half", timestep_s=25e-9, output_load_F=2e-15)
    nominal = next(r for r in results if r.get("corner") == "tt"
                   and r.get("voltage_V") == 1.8 and r.get("temperature_C") == 26.85)
    convergence = {name: abs(finer[name]/nominal[name]-1)
                   for name in ("frequency_Hz", "mean_power_W")
                   if finer.get(name) and nominal.get(name)}
    array_max_W = model.maximum_power_point()[2]/2 * 3 * 150/540
    for record in results:
        record["logic_PV_array_max_W_at_1sun"] = array_max_W
        if record.get("mean_power_W"):
            record["within_nominal_PV_maximum_power"] = record["mean_power_W"] <= array_max_W
    summary = {"cases": results, "timestep_half": finer,
               "pv_storage_1pf": smaller_storage,
               "withheld_1v75": held_out,
               "timestep_relative_changes": convergence,
               "scope": "deterministic cases, not a complete combined PVT or mismatch signoff"}
    pdk = Path(os.environ.get("PDK_ROOT", "/usr/local/share/pdk")) / "sky130A"
    nodeinfo = pdk / ".config/nodeinfo.json"
    if nodeinfo.is_file():
        summary["pdk_nodeinfo"] = json.loads(nodeinfo.read_text())
    summary["ngspice_version"] = subprocess.run(["ngspice", "--version"],
                                                capture_output=True, text=True).stdout.strip()
    (dest / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary, data


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=HERE / "local_runs/clock_final")
    args = parser.parse_args()
    fit = json.loads((HERE / "results/published/pv_fit.json").read_text())
    run_clock_matrix(args.output, SingleDiodePV(**fit["fitted_terminal_model"]))
