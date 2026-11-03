"""Fresh matched nominal simulations, retaining every finer numerical observation."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
import hashlib
import itertools
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import traceback
from typing import TYPE_CHECKING

from contract import (
    DEVICES, ENTRY, HERE, PORTS, PROTOCOL, audit_source, check_netlist,
    logical_lines, read_spice, refinement_state, require, sha256, write_json,
)

if TYPE_CHECKING:
    from comparator_atlas.spice import Point

MODES = ("schematic", "lvs", "c", "rc")
DEADLINES = PROTOCOL["numerics"]["reporting_deadlines_ns"]
SPICE_INIT = "set ngbehavior=hsa\nset noaskquit\nset num_threads=1\n"


def geometry_commands(devices: list[dict]) -> list[str]:
    lines = ["show all : w l"]
    for index, device in enumerate(devices):
        primitive = f'm.xdut.{device["name"].lower()}.m{device["model"]}'
        lines.extend([
            f"let audit_w{index} = @{primitive}[w]",
            f"let audit_l{index} = @{primitive}[l]",
            f'echo NOMINAL27_GEOMETRY {device["name"]} {device["model"]} '
            f"$&audit_w{index} $&audit_l{index}",
        ])
    return lines


def audit_geometry(text: str, devices: list[dict]) -> dict:
    rows = re.findall(r"^NOMINAL27_GEOMETRY (\S+) (\S+) (\S+) (\S+)\s*$", text, re.M)
    require(len(rows) == len(devices) == 27, "Missing actual ngspice 27-device W/L evidence")
    observed = []
    for (name, model, width, length), device in zip(rows, devices):
        require((name, model) == (device["name"], device["model"]),
                "Simulator geometry evidence has different instances/flavors")
        width, length = float(width), float(length)
        for actual, expected in ((width, device["w_um"]*1e-6),
                                 (length, device["l_um"]*1e-6)):
            require(math.isfinite(actual) and math.isclose(actual, expected, rel_tol=1e-6, abs_tol=1e-15),
                    f"Actual ngspice SI geometry disagrees with layout W/L: {name}: {actual} != {expected}")
        observed.append({"name": name, "model": model, "actual_w_m": width, "actual_l_m": length,
                         "expected_w_um": device["w_um"], "expected_l_um": device["l_um"]})
    return {"observed_device_count": len(observed), "scale_option": "1u",
            "actual_instance_parameters_in_metres": observed}


def make_deck(mode: str, point: Point, native: str, model_root: Path, devices: list[dict]) -> str:
    require(mode in MODES and point.pair_skew == 0 and point.trim_code == 0
            and point.design_name == "lvt_balanced_4b", "Wrong nominal simulation target")
    require(point.load_ff == 5 and point.common_mode_ratio == 0.5
            and point.source_resistance_ohm == 0 and point.sample_cap_ff == 0
            and point.previous_differential_v is None, "Physical experiment was retuned")
    require(not re.search(r"^\s*\.(?:opt\w*|control|end)\b", native, re.I | re.M),
            "Native DUT contains a testbench, scaling option, or control block")
    includes = [model_root / "models" / "parameters" / "lod.spice"]
    for flavor in ("nfet_01v8", "pfet_01v8", "nfet_01v8_lvt"):
        directory = model_root / "cells" / flavor
        includes.extend(directory / f"sky130_fd_pr__{flavor}__{suffix}.spice"
                        for suffix in ("mismatch.corner", point.corner+".corner"))
    common = point.vdd_v * point.common_mode_ratio
    pins = ["0" if name == "vss" else name for name in PORTS]
    lines = [
        "Comparator Atlas: nominal published 27-device matched layout experiment",
        ".option scale=1u reltol=1e-5 abstol=1e-13 vntol=1e-7",
        *(f'.include "{path.as_posix()}"' for path in includes),
        native.rstrip(), f".temp {point.temperature_c:.12g}",
        f"Vdd vdd 0 {point.vdd_v:.12g}",
        f"Vclk clk 0 PULSE(0 {point.vdd_v:.12g} 2n 50p 50p 4n 10n)",
        f"Vinp vinp 0 {common+point.differential_v/2:.12g}",
        f"Vinn vinn 0 {common-point.differential_v/2:.12g}",
        *(f"V{name} {name} 0 0" for name in PORTS[7:]),
        f'Xdut {" ".join(pins)} atlas' + (" pair_skew=0" if mode == "schematic" else ""),
        "Cqp qp 0 5f", "Cqn qn 0 5f",
        ".save v(clk) v(qp) v(qn) v(xdut.xp) v(xdut.xn) i(vdd) v(vinp) v(vinn)",
        ".control", "set wr_singlescale", "set wr_vecnames", "set numdgt=15",
        f"tran {point.max_step_ps:.12g}p 30n 19n {point.max_step_ps:.12g}p",
        "wrdata waveform.tsv v(clk) v(qp) v(qn) v(xdut.xp) v(xdut.xn) i(vdd) v(vinp) v(vinn)",
        *geometry_commands(devices),
        "echo NOMINAL27_TRANSIENT_COMPLETE", "quit 0", ".endc", ".end", "",
    ]
    return "\n".join(lines)


class Experiment:
    def __init__(self, out: Path, models: Path):
        sys.path.insert(0, str(ENTRY))
        import numpy as np
        from comparator_atlas import spice

        self.np, self.spice = np, spice
        self.out, self.models = out, models
        self.directory = out / "simulations"
        self.directory.mkdir()
        executable = shutil.which("ngspice")
        require(executable is not None, "ngspice is missing")
        self.executable = Path(executable).resolve()
        package = subprocess.check_output(
            ["dpkg-query", "-W", "-f=${Version}", "ngspice"], text=True).strip()
        require(package == PROTOCOL["tools"]["ngspice"]["package_version"], "Unpinned ngspice package")
        require(np.__version__ == PROTOCOL["tools"]["numpy"], "Unpinned NumPy")
        require(spice.SPICE_INIT == SPICE_INIT, "Published initialization contract differs")
        audit_source()
        original = ENTRY / "results" / "study" / "selected_circuit.spice"
        shutil.copyfile(original, out / "atlas.schematic.spice")
        self.paths = {mode: out / f"atlas.{mode}.spice" for mode in MODES}
        self.devices = {"schematic": DEVICES}
        for mode in MODES[1:]:
            parsed = read_spice(self.paths[mode])
            check_netlist(parsed, rc=mode == "rc")
            self.devices[mode] = parsed["devices"]
        model_record = json.loads((out / "model-evidence" / "models.json").read_text())
        require(model_record["revision"] == spice.PDK_REVISION, "Simulation model provenance changed")
        require(all(sha256(models / name) == expected for name, expected in model_record["files"].items()),
                "Model files changed after the exact-revision checkout")
        for model in PROTOCOL["source"]["model_counts"]:
            flavor = model.removeprefix("sky130_fd_pr__")
            for corner in ("tt", "ss", "ff", "sf", "fs"):
                text = (models / "cells" / flavor / f"{model}__{corner}.pm3.spice").read_text()
                transistors = [line.split()[0] for line in logical_lines(text)
                               if re.match(r"m\S+\s", line, re.I)]
                require(transistors == ["m"+model], f"Unexpected inner model device: {model}, {corner}")
        self.provenance = {
            "ngspice_package_version": package,
            "ngspice_executed_version": subprocess.check_output(
                [str(self.executable), "--version"], text=True).strip(),
            "ngspice_binary_sha256": sha256(self.executable),
            "numpy_version": np.__version__, "python_version": sys.version,
            "measurement_source_sha256": sha256(ENTRY / "comparator_atlas" / "spice.py"),
            "model_evidence_sha256": sha256(out / "model-evidence" / "models.json"),
            "model_revision": spice.PDK_REVISION,
            "spiceinit_sha256": hashlib.sha256(SPICE_INIT.encode()).hexdigest(),
            "netlist_sha256": {mode: sha256(path) for mode, path in self.paths.items()},
        }
        write_json(out / "simulation-provenance.json", self.provenance)
        self.records, self.audits = {}, {}
        self.verified_reuse = set()

    def point(self, condition: tuple, differential: float, step: float = 10):
        corner, vdd, temperature = condition
        return self.spice.Point(
            corner=corner, vdd_v=vdd, temperature_c=temperature, differential_v=differential,
            common_mode_ratio=0.5, pair_skew=0, trim_code=0, load_ff=5, max_step_ps=step,
            design_name="lvt_balanced_4b",
        )

    def identity(self, mode: str, point: Point) -> dict:
        physical = asdict(point)
        physical.pop("max_step_ps")
        return {"mode": mode, "point": physical,
                "netlist_sha256": self.provenance["netlist_sha256"][mode],
                "model_evidence_sha256": self.provenance["model_evidence_sha256"],
                "ngspice_binary_sha256": self.provenance["ngspice_binary_sha256"],
                "spiceinit_sha256": self.provenance["spiceinit_sha256"]}

    def key(self, mode: str, point: Point) -> str:
        value = {"physical_identity": self.identity(mode, point), "max_step_ps": point.max_step_ps}
        return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()[:24]

    def run(self, mode: str, point: Point) -> dict:
        key = self.key(mode, point)
        directory = self.directory / key
        directory.mkdir()
        record = {"run_id": key, "mode": mode, "point": asdict(point),
                  "physical_identity": self.identity(mode, point), "max_step_ps": point.max_step_ps,
                  "status": "FAIL", "measurements": []}
        try:
            deck = make_deck(mode, point, self.paths[mode].read_text(),
                             self.models, self.devices[mode])
            (directory / "circuit.cir").write_text(deck)
            (directory / ".spiceinit").write_text(SPICE_INIT)
            with (directory / "ngspice.log").open("w") as log:
                result = subprocess.run([str(self.executable), "-b", "circuit.cir"],
                                        cwd=directory, text=True, stdout=log, stderr=subprocess.STDOUT,
                                        env=dict(os.environ, HOME=str(directory)), timeout=120)
            text = (directory / "ngspice.log").read_text(errors="replace")
            require(result.returncode == 0 and "NOMINAL27_TRANSIENT_COMPLETE" in text,
                    f"ngspice did not complete the actual analysis: {key}")
            fatal = re.search(r"(^|\n)\s*(?:error|fatal)|timestep too small|no such vector|"
                              r"unknown parameter|unknown device|convergence failed", text, re.I)
            require(fatal is None, f"ngspice reported a substantive execution error: {key}")
            geometry = audit_geometry(text, self.devices[mode])
            write_json(directory / "actual-geometry.json", geometry)
            values = self.np.loadtxt(directory / "waveform.tsv", skiprows=1, ndmin=2)
            require(values.shape[1] == 9, f"Expected nine actual waveform columns: {values.shape}")
            self.spice.validate_waveform(values)
            warnings = tuple(line for line in text.splitlines() if "warning" in line.lower())
            trace = self.spice.Trace(point, values, key, directory, warnings)
            # Preserve a compact lossless array as well as the raw wrdata evidence.
            self.np.savez_compressed(directory / "waveform.npz", values=values)
            record["measurements"] = [asdict(self.spice.measure(trace, deadline)) for deadline in DEADLINES]
            record.update(status="PASS", warnings=list(warnings), waveform_shape=list(values.shape),
                          actual_geometry_sha256=sha256(directory / "actual-geometry.json"))
        except (AssertionError, ValueError, OSError, RuntimeError, subprocess.SubprocessError) as error:
            record.update(error=str(error), traceback=traceback.format_exc())
        finally:
            record["artifact_sha256"] = {
                path.name: sha256(path) for path in sorted(directory.iterdir()) if path.is_file()
            }
            write_json(directory / "metadata.json", record)
        return record

    def run_group(self, requests: list[tuple[str, Point]]) -> None:
        for mode, point in requests:
            key = self.key(mode, point)
            if key in self.records and key not in self.verified_reuse:
                record = self.records[key]
                directory = self.directory / key
                require(record["physical_identity"] == self.identity(mode, point),
                        "In-job reuse changed the physical experiment")
                require(json.loads((directory / "metadata.json").read_text()) == record,
                        "In-job execution receipt changed")
                require(all(sha256(directory / name) == expected
                            for name, expected in record["artifact_sha256"].items()),
                        "In-job executed evidence changed")
                self.verified_reuse.add(key)
        missing = {self.key(mode, point): (mode, point) for mode, point in requests
                   if self.key(mode, point) not in self.records}
        remaining = float(os.environ["NOMINAL27_STOP_EPOCH"]) - time.time()
        require(remaining > 150, "Bounded job time exhausted before another simulation group")
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(self.run, mode, point) for mode, point in missing.values()]
            for future in futures:
                row = future.result()
                self.records[row["run_id"]] = row
        write_json(self.out / "simulation-index.json", list(self.records.values()))
        failures = [self.records[self.key(mode, point)] for mode, point in requests
                    if self.records[self.key(mode, point)]["status"] != "PASS"]
        require(not failures, f'Actual simulator/measurement failure: {failures[0] if failures else ""}')

    def get(self, mode: str, point: Point) -> dict:
        return self.records[self.key(mode, point)]

    def numerical_audit(self, condition: tuple) -> list[dict]:
        existing = self.audits.get(json.dumps(condition))
        if existing is not None:
            require(all(row["qualified"] for row in existing),
                    "Existing finest contrary evidence cannot be replaced by a coarse restart")
            return existing
        histories = {(mode, differential): [] for mode in MODES
                     for differential in (-0.01, -0.003, 0.003, 0.01)}
        states = {}
        for step in [10, 5, *PROTOCOL["numerics"]["further_max_steps_ps"]]:
            pending = [key for key in histories if key not in states or not states[key]["qualified"]]
            if not pending:
                break
            self.run_group([(mode, self.point(condition, differential, step))
                            for mode, differential in pending])
            for mode, differential in pending:
                history = histories[(mode, differential)]
                history.append(self.get(mode, self.point(condition, differential, step)))
                if len(history) >= 2:
                    states[(mode, differential)] = refinement_state(history)
        output = [{
            "condition": list(condition), "mode": mode, "differential_v": differential,
            "history": history, **states[(mode, differential)],
        } for (mode, differential), history in histories.items()]
        self.audits[json.dumps(condition)] = output
        write_json(self.out / "numerical-audits.json", list(self.audits.values()))
        require(all(row["qualified"] for row in output), "Finest bounded numerical evidence remains sensitive")
        return output

    def primary_rows(self, conditions: list[tuple]) -> list[dict]:
        rows = []
        for condition in conditions:
            audits = self.audits.get(json.dumps(condition), [])
            for mode in MODES:
                for differential in (-0.01, -0.003, 0.003, 0.01):
                    audited = next((r for r in audits if r["mode"] == mode
                                    and r["differential_v"] == differential), None)
                    record = (self.records[audited["finest_run_id"]] if audited
                              else self.get(mode, self.point(condition, differential)))
                    measurement = next(m for m in record["measurements"] if m["deadline_ns"] == 1)
                    rows.append({"condition": list(condition), "mode": mode,
                                 "differential_v": differential, "run_id": record["run_id"],
                                 "max_step_ps": record["max_step_ps"],
                                 "numerically_audited": audited is not None, **measurement})
        return rows

    def worst_rc_condition(self, conditions: list[tuple]) -> tuple:
        rows = [row for row in self.primary_rows(conditions) if row["mode"] == "rc"]
        worst = max(rows, key=lambda row: (row["outcome"] != "correct",
                    row["decision_time_ns"] if row["decision_time_ns"] is not None else math.inf,
                    row["core_energy_fj"]))
        return tuple(worst["condition"])


def main(out: Path, models: Path) -> int:
    report = {"qualified": False, "phase": "initialization", "expanded_45_pvt": False}
    experiment = None
    try:
        structural = json.loads((out / "structural-results.json").read_text())
        require(all(row["status"] == "PASS" for row in structural), "Physical/tool contracts did not qualify")
        experiment = Experiment(out, models)
        first = tuple(PROTOCOL["simulation"]["first_gate"])
        report["phase"] = "TT numerical and matched four-mode gate"
        experiment.numerical_audit(first)
        rows = experiment.primary_rows([first])
        write_json(out / "matched-primary-results.json", rows)
        require(all(row["outcome"] == "correct" for row in rows),
                "Actual finest-evidence nominal TT decision failed; PVT expansion is stopped")
        pilot = [tuple(condition) for condition in PROTOCOL["simulation"]["pilot"]]
        report["phase"] = "five-condition pilot"
        for condition in pilot:
            experiment.run_group([(mode, experiment.point(condition, differential))
                                  for mode in MODES for differential in (-0.01, -0.003, 0.003, 0.01)])
        worst = experiment.worst_rc_condition(pilot)
        if worst != first:
            experiment.numerical_audit(worst)
        for condition in pilot:
            if any(row["outcome"] != "correct" for row in experiment.primary_rows([condition])):
                experiment.numerical_audit(condition)
        rows = experiment.primary_rows(pilot)
        write_json(out / "matched-primary-results.json", rows)
        report["pilot_worst_rc_condition"] = list(worst)
        require(all(row["outcome"] == "correct" for row in rows),
                "Actual nominal pilot decision failed; larger PVT sweep is stopped")
        expansion = PROTOCOL["simulation"]["expand_only_after_credible_rc_pilot_and_numerics"]
        conditions = list(itertools.product(expansion["corners"], expansion["vdd_v"],
                                            expansion["temperature_c"]))
        require(len(conditions) == 45, "Incorrect declared PVT product")
        report["phase"] = "conditional 45-PVT matched sweep"
        report["expanded_45_pvt"] = True
        for condition in conditions:
            experiment.run_group([(mode, experiment.point(condition, differential))
                                  for mode in MODES for differential in (-0.01, -0.003, 0.003, 0.01)])
            write_json(out / "matched-primary-results.json",
                       experiment.primary_rows(conditions[:conditions.index(condition)+1]))
        worst = experiment.worst_rc_condition(conditions)
        if json.dumps(worst) not in experiment.audits:
            experiment.numerical_audit(worst)
        for condition in conditions:
            if any(row["outcome"] != "correct" for row in experiment.primary_rows([condition])):
                experiment.numerical_audit(condition)
        rows = experiment.primary_rows(conditions)
        write_json(out / "matched-primary-results.json", rows)
        report.update(final_worst_rc_condition=list(worst), primary_rows=len(rows))
        require(all(row["outcome"] == "correct" for row in rows),
                "Actual nominal PVT decision failure is retained; no physical retuning")
        report.update(qualified=True, phase="complete")
    except (AssertionError, ValueError, OSError, RuntimeError, subprocess.SubprocessError) as error:
        report.update(error=str(error), traceback=traceback.format_exc())
        print(f"NOMINAL27_SIMULATION_ERROR: {error}", flush=True)
    finally:
        if experiment is not None:
            report["actual_simulator_runs"] = len(experiment.records)
            report["successful_simulator_runs"] = sum(row["status"] == "PASS"
                                                      for row in experiment.records.values())
            report["failed_simulator_runs"] = [row["run_id"] for row in experiment.records.values()
                                               if row["status"] != "PASS"]
            report["hash_verified_in_job_reuse"] = sorted(experiment.verified_reuse)
        write_json(out / "simulation-result.json", report)
    return 0 if report["qualified"] else 1


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()))
