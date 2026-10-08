"""Fresh four-mode comparisons using the frozen simulator and monotone audit."""

from __future__ import annotations

import itertools
import json
from pathlib import Path
import subprocess
import sys
import traceback

from repair import FIXED_PROTOCOL, PROTOCOL, audit_inherited_inputs, require, write_json
from simulate import Experiment


def qualified_rows(experiment: Experiment, conditions: list[tuple]) -> list[dict]:
    rows = experiment.primary_rows(conditions)
    require(len(rows) == 16 * len(conditions) and all(r["numerically_audited"] for r in rows),
            "Every scored condition requires a completed monotone numerical audit")
    return rows


def main(out: Path, models: Path) -> int:
    report = {"qualified": False, "phase": "initialization", "expanded_45_pvt": False,
              "repair_phase": PROTOCOL["phase"], "revision": PROTOCOL["revision"],
              "fixed_testbench_and_numerical_tolerances_unchanged": True}
    experiment = None
    completed = []
    try:
        audit_inherited_inputs()
        structural = json.loads((out / "structural-handoff.json").read_text())
        require(structural["qualified"] and structural["checks"] == 17,
                "Repaired physical geometry did not qualify")
        checks = json.loads((out / "structural-results.json").read_text())
        require(len(checks) == 17 and all(row["status"] == "PASS" for row in checks),
                "Repaired physical checks contain a failure or unknown result")
        experiment = Experiment(out, models)

        def audit(condition: tuple) -> list[dict]:
            experiment.numerical_audit(condition)
            if condition not in completed:
                completed.append(condition)
            rows = qualified_rows(experiment, completed)
            write_json(out / "matched-primary-results.json", rows)
            print(f"COMPACT_REPAIR_AUDITED_CONDITION {condition}", flush=True)
            return rows

        first = tuple(FIXED_PROTOCOL["simulation"]["first_gate"])
        report["phase"] = "TT numerical and matched four-mode gate"
        rows = audit(first)
        require(all(row["outcome"] == "correct" for row in rows),
                "Finest audited code-zero TT failure; pilot is not run")
        print("COMPACT_REPAIR_TT_FUNCTIONAL_QUALIFIED 1", flush=True)
        pilot = [tuple(condition) for condition in FIXED_PROTOCOL["simulation"]["pilot"]]
        report["phase"] = "five-condition numerically audited pilot"
        for condition in pilot:
            audit(condition)
        rows = qualified_rows(experiment, pilot)
        report["pilot_primary_rows"] = len(rows)
        report["pilot_worst_rc_condition"] = list(experiment.worst_rc_condition(pilot))
        require(all(row["outcome"] == "correct" for row in rows),
                "Finest audited code-zero pilot failure; 45-PVT expansion is not run")
        print("COMPACT_REPAIR_PILOT_FUNCTIONAL_QUALIFIED 1", flush=True)
        expansion = FIXED_PROTOCOL["simulation"]["expand_only_after_credible_rc_pilot_and_numerics"]
        conditions = list(itertools.product(expansion["corners"], expansion["vdd_v"],
                                            expansion["temperature_c"]))
        require(len(conditions) == 45, "Changed PVT condition product")
        report.update(phase="conditional 45-PVT numerically audited sweep", expanded_45_pvt=True)
        for condition in conditions:
            audit(condition)
        rows = qualified_rows(experiment, conditions)
        write_json(out / "matched-primary-results.json", rows)
        report.update(primary_rows=len(rows),
                      final_worst_rc_condition=list(experiment.worst_rc_condition(conditions)))
        require(all(row["outcome"] == "correct" for row in rows),
                "Finest audited PVT failure is retained; no physical retuning")
        report.update(qualified=True, phase="complete")
    except (AssertionError, ValueError, OSError, RuntimeError, subprocess.SubprocessError) as error:
        report.update(error=str(error), traceback=traceback.format_exc())
        print(f"COMPACT_REPAIR_SIMULATION_ERROR: {error}", flush=True)
    finally:
        report["completed_numerically_audited_conditions"] = [list(c) for c in completed]
        if experiment is not None:
            report["actual_simulator_runs"] = len(experiment.records)
            report["successful_simulator_runs"] = sum(
                row["status"] == "PASS" for row in experiment.records.values())
            report["failed_simulator_runs"] = [row["run_id"] for row in experiment.records.values()
                                               if row["status"] != "PASS"]
            report["hash_verified_in_job_reuse"] = sorted(experiment.verified_reuse)
        write_json(out / "simulation-result.json", report)
    return 0 if report["qualified"] else 1


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()))
