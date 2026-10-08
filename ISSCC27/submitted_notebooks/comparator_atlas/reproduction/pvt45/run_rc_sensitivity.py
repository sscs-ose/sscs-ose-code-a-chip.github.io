"""Bounded exploratory RC-card scaling; separate from the sealed PVT study."""

import argparse
from dataclasses import asdict
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time


CASES = (
    ("original", Decimal("1"), Decimal("1")),
    ("c_low", Decimal("1"), Decimal("0.8")),
    ("c_high", Decimal("1"), Decimal("1.2")),
    ("r_low", Decimal("0.8"), Decimal("1")),
    ("r_high", Decimal("1.2"), Decimal("1")),
    ("both_low", Decimal("0.8"), Decimal("0.8")),
    ("both_high", Decimal("1.2"), Decimal("1.2")),
)
POINT_IDS = ("c01-rc-m10", "c37-rc-m03")
STEPS_PS = (10, 5)
CAP = re.compile(r"^(C[0-9]+) (\S+) (\S+) (\S+)(.*)$")
RES = re.compile(r"^(R[0-9]+) (\S+) (\S+) (\S+)(.*)$")


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, obj):
    path.write_text(
        json.dumps(
            obj,
            indent=2,
            allow_nan=False) +
        "\n",
        encoding="utf-8")


def scale_native_cards(deck, resistance, capacitance):
    lines, inside, nc, nr = [], False, 0, 0
    for line in deck.splitlines():
        if line.startswith(".subckt atlas "):
            require(not inside, "Multiple atlas subcircuits")
            inside = True
        elif line == ".ends" and inside:
            inside = False
        elif inside:
            capacitor = CAP.fullmatch(line)
            resistor = RES.fullmatch(line)
            if capacitor is not None:
                name, left, right, original, suffix = capacitor.groups()
                require(
                    original.endswith("f") or original == "0",
                    "Unsupported capacitor")
                fF = Decimal(
                    original[:-1] if original.endswith("f") else original)
                value = format(fF * capacitance, "f") + "f" if fF else "0"
                line = f"{name} {left} {right} {value}{suffix}"
                nc += 1
            elif resistor is not None:
                name, left, right, original, suffix = resistor.groups()
                value = format(Decimal(original) * resistance, "f")
                line = f"{name} {left} {right} {value}{suffix}"
                nr += 1
        lines.append(line)
    require(not inside and nc == 319 and nr ==
            675, "RC card count or subckt invalid")
    return "\n".join(lines) + "\n"


def public_baselines(entry):
    import csv
    path = entry.parents[1] / "results/study/postlayout_pvt45/measurements.csv"
    with path.open(encoding="utf-8", newline="") as handle:
        rows = {row["point_id"]: row for row in csv.DictReader(handle)}
    require(len(rows) == 360 and set(POINT_IDS) <=
            rows.keys(), "Published rows missing")
    return {p: rows[p] for p in POINT_IDS}, sha256(path.read_bytes())


def compare_public(fine, row):
    energy = fine["measurements"][-1]["core_energy_fj"]
    reference_energy = float(row["core_energy_fj"])
    require(abs(energy - reference_energy) <= reference_energy * .01,
            "New original scenario does not reproduce published energy")
    for deadline in (1, 2):
        result = next(m for m in fine["measurements"]
                      if m["deadline_ns"] == deadline)
        suffix = f"{deadline}ns"
        require(result["outcome"] == row["outcome_" + suffix]
                and result["decision"] == int(row["decision_" + suffix]),
                "New original scenario does not reproduce published decision")
        old = row["decision_time_ns_" + suffix]
        require((result["decision_time_ns"] is None and old == "")
                or (result["decision_time_ns"] is not None and old != ""
                    and abs(result["decision_time_ns"] - float(old)) <= .02),
                "New original scenario does not reproduce published latency")
    return {"archived_energy_fj": reference_energy,
            "fresh_energy_fj": energy, "qualified_at_1ns_and_2ns": True}


def execute(working, point, scenario, factors, step,
            support, spice, np, executable, deadline):
    require(time.monotonic() < deadline,
            "Global 15-minute sensitivity window expired")
    directory = working / "data" / "transients" / \
        f"{point['condition_id']}-{scenario}-{int(step)}"
    directory.mkdir(parents=True, exist_ok=False)
    original = support.make_deck(point, step)
    perturbed = scale_native_cards(original, factors[0], factors[1])
    if scenario == "original":
        require(perturbed == original, "Nominal deck changed by scaling code")
    (directory / "circuit.cir").write_text(perturbed, encoding="utf-8", newline="\n")
    (directory / ".spiceinit").write_text(
        support.PROTOCOL["runtime"]["local_spiceinit"], encoding="utf-8", newline="\n")
    record = {"point_id": point["point_id"], "condition": point["condition"],
              "differential_mv": point["differential_mv"],
              "scenario": scenario, "r_factor": str(factors[0]), "c_factor": str(factors[1]),
              "step_ps": step, "base_deck_sha256": sha256(original.encode()),
              "executed_deck_sha256": sha256(perturbed.encode()),
              "status": "started"}
    write_json(directory / "record.json", record)
    environment = dict(os.environ, HOME=str(directory), USERPROFILE=str(directory),
                       TMP=str(directory), TEMP=str(directory), PYTHONDONTWRITEBYTECODE="1",
                       OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1")
    with (directory / "console.log").open("wb") as console:
        try:
            outcome = subprocess.run(
                [str(executable), "-b", "-o", "ngspice.log", "circuit.cir"],
                cwd=directory, env=environment, stdout=console, stderr=subprocess.STDOUT,
                timeout=120, check=False,
            )
        except subprocess.TimeoutExpired as error:
            record.update(status="timed_out", error=str(error))
            write_json(directory / "record.json", record)
            raise
    log = (directory / "ngspice.log").read_text(errors="replace")
    console = (directory / "console.log").read_text(errors="replace")
    diagnostics = support.classify(log, console)
    require(outcome.returncode == 0 and not diagnostics["errors"]
            and not diagnostics["warnings"]
            and log.splitlines().count("NOMINAL27_TRANSIENT_COMPLETE") == 1,
            f"Simulator error/warning for {directory.name}")
    startup = support.old_windows.runtime_markers(log)
    devices = support.devices()["rc"]
    geometry = support.phase.native_simulator.audit_geometry(log, devices)
    require(startup["qualified"] and geometry["observed_device_count"] == 27,
            "Runtime marker or 27-device geometry mismatch")
    values = np.loadtxt(directory / "waveform.tsv", skiprows=1, ndmin=2)
    require(values.shape[1] == 9, "Incomplete waveform")
    spice.validate_waveform(values)
    physical = spice.Point(**point["physical_point"], max_step_ps=step)
    trace = spice.Trace(physical, values, directory.name, directory)
    measurements = [asdict(spice.measure(trace, d)) for d in support.DEADLINES]
    record.update(status="success", runtime_markers=startup,
                  actual_mos_si_count=geometry["observed_device_count"],
                  waveform_rows=int(values.shape[0]), waveform_sha256=sha256(
                      (directory / "waveform.tsv").read_bytes()),
                  measurements=measurements)
    write_json(directory / "record.json", record)
    print(f"{directory.name}: 1ns={measurements[-2]['outcome']} "
          f"2ns={measurements[-1]['outcome']} energy={measurements[-1]['core_energy_fj']:.3f}fJ",
          flush=True)
    return record


def main():
    cli = argparse.ArgumentParser()
    for name in ("entry", "models", "ngspice", "out"):
        cli.add_argument("--" + name, type=Path, required=True)
    args = cli.parse_args()
    entry, models, executable, working = (
        args.entry.resolve(), args.models.resolve(), args.ngspice.resolve(), args.out.resolve())
    require(not working.exists() and len(str(working))
            < 90, "Fresh SHORT output path required")
    require(entry.is_dir() and models.is_dir()
            and executable.is_file(), "Pinned input missing")
    sys.path.insert(0, str(entry))
    import numpy as np
    from comparator_atlas import spice
    from pvt45_reproduce import support
    require(entry == support.ENTRY.resolve(), "Wrong comparator entry")
    audit = support.source_audit()
    require(spice.sha256(executable) == support.PROTOCOL["runtime"]["ngspice_console_sha256"],
            "Wrong ngspice executable")
    support.old_windows.audit_runtime(executable)
    model_pin = support.models_audit(models)
    expected, public_csv_sha = public_baselines(entry)
    plan = [p for p in support.points("full") if p["point_id"] in POINT_IDS]
    require(
        len(plan) == 2 and all(
            p["mode"] == "rc" for p in plan),
        "Point selection changed")
    require(all(expected[p["point_id"]]["finest_step_ps"] == "5" for p in plan),
            "Published baseline finest step changed")
    manifest = json.loads(
        (entry / support.PROTOCOL["runtime"]["exact_raw_models_manifest"]).read_text())
    working.mkdir()
    model_copy = working / "data" / "model-source"
    for relative in manifest["files"]:
        dest = model_copy / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(models / relative, dest)
    support.models_audit(model_copy)
    (working / "data" / "transients").mkdir()
    write_json(working / "plan.json", {
        "scope": "Two previously public RC points only, seven hypothetical R/C ratios x 10/5 ps",
        "no_physical_uncertainty_interval_or_full_grid_claim": True,
        "points": [{k: p[k] for k in ("point_id", "condition", "differential_mv")}
                   for p in plan],
        "scenarios": [{"name": name, "r_factor": str(r), "c_factor": str(c)}
                      for name, r, c in CASES],
        "expected_transients": len(plan) * len(CASES) * len(STEPS_PS),
        "submitted_rc_netlist_sha256": sha256(
            (entry / support.PROTOCOL["circuit"]["rc_path"]).read_bytes()),
        "public_results_csv_sha256": public_csv_sha,
        "fresh_source_audit_sha256": sha256(
            json.dumps(audit, sort_keys=True, default=str).encode()),
        "model_pin": model_pin,
    })
    start = time.monotonic()
    deadline = start + 900
    pairs = []
    for scenario, resistance, capacitance in CASES:
        for point in plan:
            pair = [execute(working, point, scenario, (resistance, capacitance), step,
                            support, spice, np, executable, deadline) for step in STEPS_PS]
            numerical = support.phase.historical.compare_measurements(
                pair[0]["measurements"], pair[1]["measurements"])
            require(
                numerical["passed"],
                f"Numerically unqualified pair {point['point_id']} {scenario}")
            baseline = compare_public(
                pair[1], expected[point["point_id"]]) if scenario == "original" else None
            pairs.append({
                "scenario": scenario, "point_id": point["point_id"],
                "numerical_comparison": numerical,
                "archived_baseline_comparison": baseline,
                "finest": pair[1],
            })
            write_json(working / "progress.json", {
                "completed_pairs": len(pairs), "completed_transients": 2 * len(pairs),
                "pair_ids": [(p["point_id"], p["scenario"]) for p in pairs],
            })
    write_json(working / "summary.json", {
        "scope": "Exploratory factors are hypothetical and not validated PDK error bounds",
        "maximum_elapsed_seconds": 900, "actual_elapsed_seconds": time.monotonic() - start,
        "actual_transients": len(pairs) * 2,
        "points": POINT_IDS,
        "numerical_pairs_qualified": len(pairs),
        "full_new_pvt_grid": False,
        "geometry_or_pex_physical_fidelity_certification": False,
        "pairs": pairs,
    })
    print("SENSITIVITY_COMPLETE pairs=14 transients=28", flush=True)


if __name__ == "__main__":
    main()
