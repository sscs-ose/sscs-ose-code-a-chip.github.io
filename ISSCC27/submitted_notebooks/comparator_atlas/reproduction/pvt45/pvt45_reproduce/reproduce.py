"""Clean-start Windows reproduction. Explicit --smoke or --full; no historical checkpoint input."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import time
import traceback
import csv

from support import (
    DEADLINES, ENTRY, HERE, PROTOCOL, STEPS, CheckpointWriter, IntegrityError,
    OwnedProcess, WindowExpired, WorkerGuard, canonical_sha256, cap, check_charge,
    classify, compare_reference, devices, initial_order, make_deck, models_audit,
    old_windows, phase, points, require, sha256, source_audit, write_json,
)


class FreshStudy:
    def __init__(self, mode: str, root: Path, executable: Path, models: Path, guard: WorkerGuard):
        self.mode, self.root, self.exe, self.guard = mode, root, executable, guard
        self.out = root / "data"
        require(not self.out.exists(), "Fresh output data already exist; no reuse or budget reset")
        require(not root.is_relative_to(models) and not root.is_relative_to(executable.parent.parent),
                "Choose a new owned output outside the read-only model/tool installations")
        guard.check("fresh_source_checks_begin")
        audit = source_audit()
        runtime = old_windows.audit_runtime(executable)
        model_identity = models_audit(models, guard)
        self.definitions = points(mode)
        self.by_id = {p["point_id"]: p for p in self.definitions}
        self.device_table = devices()
        sys.path.insert(0, str(ENTRY))
        import numpy as np
        from comparator_atlas import spice
        self.np, self.spice = np, spice
        self.out.mkdir()
        model_manifest = json.loads((ENTRY / PROTOCOL["runtime"]["exact_raw_models_manifest"]).read_text())
        for name, record in model_manifest["files"].items():
            guard.check("copy_unchanged_model", component=name)
            target = self.out / "model-source" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(models / name, target)
            require(sha256(target) == record["actual_parent_sha256"], "Owned snapshot changed raw model bytes")
        models_audit(self.out / "model-source", guard)
        self.identity = {
            "variant": PROTOCOL["variant"], "selection": mode,
            "source_pins_sha256": audit["fresh_source_pins_sha256"],
            "protocol_sha256": audit["fresh_protocol_sha256"],
            "executed_source_sha256": audit["source_sha256"],
            "runtime": runtime, "raw_models": model_identity,
            "native_netlist_sha256": audit["native_sha256"],
            "scientific_contract": PROTOCOL["scientific_contract"],
            "startup_sha256": hashlib.sha256(PROTOCOL["runtime"]["local_spiceinit"].encode()).hexdigest(),
            "no_old_record_or_checkpoint_import": True,
        }
        permitted = STEPS if mode == "full" else [10, 5]
        self.plan = {
            p["point_id"]: {
                str(step): hashlib.sha256(make_deck(p, step).encode()).hexdigest()
                for step in permitted
            } for p in self.definitions
        }
        self.identity["all_permitted_deck_hashes_sha256"] = canonical_sha256(self.plan)
        self.checkpoint = {
            "variant": PROTOCOL["variant"], "selection": mode, "runtime_identity": self.identity,
            "attempt_cap": cap(mode), "attempts": [], "charged_attempts": 0,
            "startup_gate": None, "global_error": None, "old_study_counts_changed": False,
        }
        self.records = {}
        self.stop_reason = None
        self.writer = CheckpointWriter(self.out / "checkpoint.json", guard)
        (self.out / "transients").mkdir()
        for name, digest in audit["source_sha256"].items():
            source = ENTRY / name
            require(sha256(source) == digest, "Source changed during fresh preparation")
            destination = self.out / "source" / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
        shutil.copyfile(HERE / "source-pins.json", self.out / "source-pins.json")
        write_json(self.out / "matrix.json", self.definitions)
        write_json(self.out / "deck-plan.json", self.plan)
        write_json(self.out / "prepared-before-data.json", {
            "identity": self.identity, "input_audit": audit,
            "model_raw_and_canonical_identity": model_identity,
            "new_actual_transients_at_preparation": 0,
            "supervisor_start": guard.context["start"],
            "both_modes_same_new_runtime": True,
        })
        self.persist()
        guard.check("fresh_preparation_complete")
        print(f"FRESH_PREPARED selection={mode} points={len(self.definitions)} "
              f"initial_attempts={len(initial_order(mode))} charged=0", flush=True)

    def persist(self):
        def snapshot():
            self.checkpoint["charged_attempts"] = len(self.checkpoint["attempts"])
            return self.checkpoint
        self.writer.write(snapshot)

    def reserve(self, point_id: str, step: float) -> dict:
        self.guard.check("reserve_begin", point_id=point_id, step_ps=step)
        check_charge(self.mode, self.checkpoint["attempts"], point_id, step)
        definition = self.by_id[point_id]
        deck = make_deck(definition, step)
        require(hashlib.sha256(deck.encode()).hexdigest() == self.plan[point_id][str(step)],
                "Pre-data deck identity changed")
        physical = {
            "point_id": point_id, "mode": definition["mode"], "point": definition["physical_point"],
            "fresh_runtime_identity_sha256": canonical_sha256(self.identity),
            "native_netlist_sha256": self.identity["native_netlist_sha256"][definition["mode"]],
        }
        run_id = canonical_sha256({
            "physical_identity": physical, "step_ps": step,
            "deck_sha256": self.plan[point_id][str(step)],
            "numerical_settings": PROTOCOL["scientific_contract"],
        })
        attempt = {
            "attempt_id": f'a{len(self.checkpoint["attempts"]) + 1:04d}-{run_id[:24]}',
            "run_identity": run_id, "point_id": point_id, "mode": definition["mode"],
            "max_step_ps": step, "physical_identity": physical,
            "status": "reserved", "reservation_clock": self.guard.event("reserve_identity")["clock"],
        }
        self.checkpoint["attempts"].append(attempt)
        self.persist()
        directory = self.out / "transients" / attempt["attempt_id"]
        directory.mkdir()
        (directory / "circuit.cir").write_text(deck, encoding="utf-8", newline="\n")
        (directory / ".spiceinit").write_text(PROTOCOL["runtime"]["local_spiceinit"],
                                             encoding="utf-8", newline="\n")
        write_json(directory / "reservation.json", attempt)
        self.guard.check("reserve_durable", attempt_id=attempt["attempt_id"])
        return attempt

    def execute(self, attempt: dict) -> dict:
        directory = self.out / "transients" / attempt["attempt_id"]
        definition = self.by_id[attempt["point_id"]]
        record = {
            **attempt, "status": "simulator_error", "launch_confirmed": False,
            "point": {**definition["physical_point"], "max_step_ps": attempt["max_step_ps"]},
            "measurements": [], "reset_ok": False,
        }
        child = None
        started = time.monotonic()
        try:
            self.guard.check("spawn_prepare", attempt_id=attempt["attempt_id"])
            environment = dict(os.environ, HOME=str(directory), USERPROFILE=str(directory),
                               TMP=str(directory), TEMP=str(directory), PYTHONDONTWRITEBYTECODE="1",
                               OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1")
            with (directory / "console.log").open("wb") as console:
                child = OwnedProcess.suspended(
                    [str(self.exe), "-b", "-o", "ngspice.log", "circuit.cir"],
                    str(directory), environment, console)
                self.guard.check("before_resume", attempt_id=attempt["attempt_id"], child=child.identity)
                child.resume()
                record["launch_confirmed"] = True
                write_json(directory / "launch.json", {
                    "attempt_id": attempt["attempt_id"], "child_identity": child.identity,
                    "executable_component": "ngspice_con.exe", "executable_sha256": sha256(self.exe),
                    "argument_list": ["-b", "-o", "ngspice.log", "circuit.cir"],
                    "clock": self.guard.event("actual_spawn", attempt_id=attempt["attempt_id"])["clock"],
                })
                while child.poll() is None:
                    self.guard.remaining()
                    if time.monotonic() - started >= 120:
                        child.terminate(124)
                        child.wait(5)
                        record["error_code"] = "bounded_process_timeout"
                        return record
                    child.wait(0.05)
            record["returncode"] = child.poll()
            self.guard.check("actual_process_finished", attempt_id=attempt["attempt_id"],
                             returncode=record["returncode"])
            log = (directory / "ngspice.log").read_text(errors="replace") if (directory / "ngspice.log").exists() else ""
            console = (directory / "console.log").read_text(errors="replace")
            diagnostics = classify(log, console)
            record["diagnostics"] = diagnostics
            if diagnostics["errors"]:
                record.update(status="integrity_error", error_code="actual_spice_error")
                return record
            require(record["returncode"] == 0
                    and log.splitlines().count("NOMINAL27_TRANSIENT_COMPLETE") == 1,
                    "Missing successful actual transient completion")
            record["startup_markers"] = old_windows.runtime_markers(log)
            geometry = phase.native_simulator.audit_geometry(log, self.device_table[definition["mode"]])
            write_json(directory / "actual-geometry.json", geometry)
            record["geometry_device_count"] = geometry["observed_device_count"]
            self.guard.check("waveform_review_begin", attempt_id=attempt["attempt_id"])
            values = self.np.loadtxt(directory / "waveform.tsv", skiprows=1, ndmin=2)
            require(values.shape[1] == 9, "Unexpected waveform columns")
            self.spice.validate_waveform(values)
            record["waveform_validated"] = True
            self.np.savez_compressed(directory / "waveform.npz", values=values)
            reset_at = self.spice.EVALUATION_START_S - 100e-12
            reset = {name: float(self.np.interp(reset_at, values[:, 0], values[:, col]))
                     for col, name in ((2, "qp"), (3, "qn"), (4, "xp"), (5, "xn"))}
            record["reset_values_v"] = reset
            record["reset_ok"] = all(v >= 0.9 * definition["physical_point"]["vdd_v"] for v in reset.values())
            if not record["reset_ok"]:
                record.update(status="reset_failure", error_code="actual_reset_rail_failure")
                return record
            trace = self.spice.Trace(self.spice.Point(**record["point"]), values,
                                     attempt["attempt_id"], directory,
                                     tuple(d["text"] for d in diagnostics["warnings"]))
            record["measurements"] = [asdict(self.spice.measure(trace, d)) for d in DEADLINES]
            if diagnostics["warnings"]:
                record.update(status="measurement_error", error_code="actual_unreviewed_warning")
            else:
                record["status"] = "success"
            if record["status"] == "success" and self.mode == "smoke":
                record["same_point_reference_comparison"] = compare_reference(record)
            self.guard.check("waveform_review_end", attempt_id=attempt["attempt_id"])
        except WindowExpired:
            record.update(status="interrupted", error_code="whole_window_expired")
        except (IntegrityError, AssertionError) as error:
            record.update(status="integrity_error", error_code="runtime_or_identity_guard_failure")
            (directory / "private-error.txt").write_text(traceback.format_exc(), encoding="utf-8", newline="\n")
        except self.spice.SimulationError as error:
            record.update(status="measurement_error", error_code="published_measurement_error")
            (directory / "private-error.txt").write_text(traceback.format_exc(), encoding="utf-8", newline="\n")
        except (OSError, ValueError) as error:
            record.update(status="simulator_error", error_code="owned_process_or_output_error")
            (directory / "private-error.txt").write_text(traceback.format_exc(), encoding="utf-8", newline="\n")
        finally:
            if child is not None:
                if child.poll() is None:
                    child.terminate(125)
                    child.wait(5)
                child.close()
            record["elapsed_seconds"] = time.monotonic() - started
            record["artifact_sha256"] = {
                p.name: sha256(p) for p in sorted(directory.iterdir())
                if p.is_file() and p.name != "metadata.json"}
            write_json(directory / "metadata.json", record)
        return record

    def retain(self, attempt, record):
        self.records[attempt["attempt_id"]] = record
        attempt["status"] = record["status"]
        attempt["metadata_sha256"] = sha256(
            self.out / "transients" / attempt["attempt_id"] / "metadata.json")
        if record["status"] == "integrity_error":
            self.checkpoint["global_error"] = {"attempt_id": attempt["attempt_id"],
                                               "error_code": record["error_code"]}
        self.persist()

    def histories(self, point_id):
        return [self.records.get(a["attempt_id"], {
            **a, "status": "interrupted", "measurements": [],
        }) for a in self.checkpoint["attempts"] if a["point_id"] == point_id]

    def batch(self, requests):
        for offset in range(0, len(requests), 2):
            if self.checkpoint["global_error"] is not None:
                self.stop_reason = "global_integrity_failure"
                return False
            if self.guard.remaining() < PROTOCOL["runtime"]["admission_reserve_seconds"]:
                self.stop_reason = "whole_window_admission_reserve"
                return False
            remaining = cap(self.mode) - len(self.checkpoint["attempts"])
            if remaining <= 0:
                self.stop_reason = "charged_attempt_cap"
                return False
            candidates = requests[offset:offset + 2]
            attempts = [self.reserve(p, s) for p, s in candidates[:remaining]]
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = {pool.submit(self.execute, a): a for a in attempts}
                for future in as_completed(futures):
                    self.guard.check("future_completed")
                    self.retain(futures[future], future.result())
            if len(attempts) < len(candidates):
                self.stop_reason = "charged_attempt_cap"
                return False
        return self.checkpoint["global_error"] is None

    def run(self):
        schedule = initial_order(self.mode)
        first = self.reserve(*schedule[0])
        record = self.execute(first)
        self.retain(first, record)
        gate = old_windows.serial_gate(record)
        self.checkpoint["startup_gate"] = {
            "qualified": gate, "serial_counted_attempt": first["attempt_id"],
            "actual_mos_si_count": record.get("geometry_device_count"),
            "startup_markers": record.get("startup_markers"), "reset_ok": record.get("reset_ok"),
        }
        self.persist()
        print(f"FRESH_FIRST_COUNTED_GATE qualified={int(gate)} attempt={first['attempt_id']}", flush=True)
        if not gate:
            self.stop_reason = "first_serial_runtime_gate_failed"
            return
        for condition in dict.fromkeys(p["condition_id"] for p in self.definitions):
            requests = [(p, s) for p, s in schedule[1:] if self.by_id[p]["condition_id"] == condition]
            if requests and not self.batch(requests):
                return
            self.report()
            print(f"FRESH_INITIAL_CONDITION_COMPLETE {condition}", flush=True)
        if self.mode == "full":
            for step in STEPS[2:]:
                pending = []
                for point in self.definitions:
                    history = self.histories(point["point_id"])
                    if history and all(r["status"] == "success" for r in history):
                        state = phase.history_state(history)
                        if not state["qualified"] and len(history) < len(STEPS) and STEPS[len(history)] == step:
                            pending.append((point["point_id"], step))
                if pending and not self.batch(pending):
                    return
                self.report()
        self.stop_reason = "fresh_requested_schedule_complete"

    def report(self):
        rows, audits = [], []
        for point in self.definitions:
            history = self.histories(point["point_id"])
            state = phase.history_state(history) if history else {
                "qualified": False, "state": "UNKNOWN", "reason": "No observation"}
            last = history[-1] if history else None
            measurements = {m["deadline_ns"]: m for m in last.get("measurements", [])} if last else {}
            row = {
                "point_id": point["point_id"], "mode": point["mode"],
                "corner": point["condition"][0], "vdd_v": point["condition"][1],
                "temperature_c": point["condition"][2], "differential_mv": point["differential_mv"],
                "trim_code": 0, "pair_skew": 0, "common_mode_ratio": 0.5, "load_ff_each": 5,
                "finest_attempt_id": last["attempt_id"] if last else None,
                "finest_step_ps": last["max_step_ps"] if last else None,
                "execution_status": last["status"] if last else "not_run",
                "numerically_qualified": state["qualified"],
                "core_energy_fj": measurements.get(2.0, {}).get("core_energy_fj"),
            }
            for deadline in (1, 2):
                for name in ("outcome", "decision", "decision_time_ns", "qp_at_deadline_v", "qn_at_deadline_v", "reset_ok"):
                    row[f"{name}_{deadline}ns"] = measurements.get(deadline, {}).get(name)
            rows.append(row)
            audits.append({"point_id": point["point_id"], **state})
        coverage = {}
        for mode in ("schematic", "rc"):
            group = [r for r in rows if r["mode"] == mode]
            coverage[mode] = {"denominator": len(group)}
            for deadline in (1, 2):
                counts = {n: 0 for n in (
                    "correct", "wrong", "unresolved", "not_run", "numerical_unknown",
                    "reset_failure", "simulator_error", "measurement_error", "integrity_error", "interrupted")}
                for row in group:
                    category = (row["execution_status"] if row["execution_status"] != "success"
                                else "numerical_unknown" if not row["numerically_qualified"]
                                else row[f"outcome_{deadline}ns"])
                    counts[category] += 1
                coverage[mode][f"{deadline}ns"] = counts
        numeric = all(r["numerically_qualified"] for r in rows)
        actual = all(r["execution_status"] == "success" for r in rows)
        primary = all(r["outcome_2ns"] == "correct" for r in rows)
        refs = [r.get("same_point_reference_comparison") for r in self.records.values()]
        reference_pass = self.mode != "smoke" or (
            len(refs) == 4 and all(r is not None and r["passed"] for r in refs))
        result = {
            "variant": PROTOCOL["variant"], "selection": self.mode,
            "qualified_before_independent_owner_stop": numeric and actual and primary and reference_pass,
            "full_new_rerun_performed": self.mode == "full",
            "full_original_study_result_is_separate": True,
            "coverage": coverage, "point_rows": len(rows),
            "charged_attempts": len(self.checkpoint["attempts"]),
            "actual_launched_attempts": sum(r.get("launch_confirmed") is True for r in self.records.values()),
            "attempt_cap": cap(self.mode), "numerical_pairs_qualified": sum(r["numerically_qualified"] for r in rows),
            "same_point_smoke_reference_comparison_passed": reference_pass if self.mode == "smoke" else None,
            "smoke_reference_comparisons": refs if self.mode == "smoke" else [],
            "startup_gate": self.checkpoint["startup_gate"],
            "global_error": self.checkpoint["global_error"], "stop_reason": self.stop_reason,
            "old_study720transients722charges_not_modified_or_extended": True,
            "fresh_DRC_or_layout_execution": False,
        }
        write_json(self.out / "finest-measurements.json", rows)
        with (self.out / "finest-measurements.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        write_json(self.out / "numerical-audits.json", audits)
        write_json(self.out / "summary.json", result)
        return result


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    mode = result.add_mutually_exclusive_group()
    mode.add_argument("--smoke", action="store_true", help="Exactly SC/RC TT1.8V27C-10mV at10/5ps; four transients maximum")
    mode.add_argument("--full", action="store_true", help="Explicit fresh45PVT full study;720initial and at most900total")
    result.add_argument("--ngspice", type=Path, help="User-supplied existing pinned ngspice_con.exe")
    result.add_argument("--models", type=Path, help="User-supplied read-only raw Windows f62031 model directory")
    result.add_argument("--out", type=Path, help="Fresh owned output directory; must not exist")
    result.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    return result


def main():
    cli = parser()
    args = cli.parse_args()
    if not args.smoke and not args.full:
        cli.print_help()
        return 0
    if any(value is None for value in (args.ngspice, args.models, args.out)):
        cli.error("explicit mode also requires --ngspice, --models and --out")
    mode = "smoke" if args.smoke else "full"
    root, executable, models = args.out.resolve(), args.ngspice.resolve(), args.models.resolve()
    if not args.worker:
        require(not root.exists(), "Fresh --out already exists; cannot silently resume or rerun")
        from supervisor import supervise
        command = [sys.executable, "-B", str(Path(__file__).resolve()), f"--{mode}",
                   "--ngspice", str(executable), "--models", str(models), "--out", str(root), "--worker"]
        result = supervise(command, str(HERE), root / "supervisor", 1800)
        summary_path = root / "data" / "summary.json"
        summary = json.loads(summary_path.read_text()) if summary_path.exists() else {}
        final = {
            "variant": PROTOCOL["variant"], "selection": mode,
            "qualified": result["new_window_time_conformance"] and result["worker_exit_code"] == 0
            and summary.get("qualified_before_independent_owner_stop") is True,
            "time_conformance": result["new_window_time_conformance"],
            "all_owned_processes_stopped": result["all_owned_processes_stopped"],
            "supervisor_result_sha256": sha256(root / "supervisor" / "supervisor-result.json"),
            "summary_sha256": sha256(summary_path) if summary_path.exists() else None,
            "fresh_full_rerun_performed": mode == "full",
            "current_smoke_does_not_revalidate_full_grid": mode == "smoke",
        }
        write_json(root / "result.json", final)
        print(json.dumps(final, indent=2))
        return 0 if final["qualified"] else 1
    guard = WorkerGuard(root / "worker-events.jsonl")
    study = None
    code = 1
    try:
        study = FreshStudy(mode, root, executable, models, guard)
        study.run()
        code = 0 if study.report()["qualified_before_independent_owner_stop"] else 1
    except WindowExpired:
        if study is not None:
            study.stop_reason = "independent_window_expired"
        code = 124
    except (IntegrityError, AssertionError, OSError, ValueError, RuntimeError) as error:
        root.mkdir(parents=True, exist_ok=True)
        (root / "private-error.txt").write_text(traceback.format_exc(), encoding="utf-8", newline="\n")
        write_json(root / "worker-error.json", {"error_type": type(error).__name__,
                   "private_diagnostic_sha256": sha256(root / "private-error.txt")})
        if study is not None:
            study.stop_reason = "global_integrity_or_execution_error"
            study.checkpoint["global_error"] = {"error_type": type(error).__name__}
        print("FRESH_EXECUTION_BLOCKED: retained exact private diagnostic; no automatic retry", flush=True)
    finally:
        if study is not None and guard.state()["allowed"]:
            study.persist()
            study.report()
            guard.check("worker_stop")
        guard.close()
    return code


if __name__ == "__main__":
    sys.exit(main())
