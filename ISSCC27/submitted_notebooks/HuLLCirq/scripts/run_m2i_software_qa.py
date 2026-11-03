#!/usr/bin/env python3
"""Run one complete software suite and preserve its actual outcomes.

SOFTWARE QA ONLY: this does not generate RTL, establish circuit correctness,
run the actual project's EDA, or adopt/change its live review records.
Invoke only after source/test files are frozen and the physical run settles.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import traceback
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIRECTORIES = ("src", "scripts", "tests", "configs")
ORIGINAL_HISTORIES = {"state.json", "generation.json", "workflow.json", "implementation_specs.json",
                      "global_generation.json", "global_workflow.json", "physical_workflow.json", "drc_workflow.json"}
DEFAULT_HISTORIES = {"state.json", "generation.json", "workflow.json", "global_workflow.json", "physical_workflow.json", "drc_workflow.json"}
RECORD_KIND = "M2_I_full_unittest_software_QA_not_actual_NPU_layout_DRC_or_LVS_execution_proof"


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def file_record(path):
    path = Path(path)
    return {"sha256": sha(path), "bytes": path.stat().st_size}


def write_json(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, allow_nan=False, indent=2)
        stream.write("\n")


def strict_json(path):
    def pairs(values):
        result = {}
        for key, value in values:
            if key in result:
                raise ValueError("Duplicate JSON key: " + key)
            result[key] = value
        return result
    def invalid(value):
        raise ValueError("Nonfinite JSON constant: " + value)
    return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=pairs, parse_constant=invalid)


def label(path):
    path = Path(path).resolve()
    return path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else str(path)


def source_snapshot():
    """Every source/test/config file, excluding only generated Python caches."""
    files = {}
    for relative in SOURCE_DIRECTORIES:
        folder = ROOT / relative
        for path in sorted(folder.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts and path.suffix not in (".pyc", ".pyo"):
                files[path.relative_to(ROOT).as_posix()] = file_record(path)
    if not files:
        raise ValueError("No product/test source files were found.")
    return files


def valid_sha(value):
    return type(value) is str and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def protected_paths(baseline, data_directory, original_directory):
    if type(baseline) is not dict or type(baseline.get("preexisting_files")) is not dict:
        raise ValueError("The pre-S13 baseline must contain its prior-file hashes.")
    originals = baseline.get("original_NPU_histories"); defaults = baseline.get("default_histories")
    if type(originals) is not dict or type(defaults) is not dict:
        raise ValueError("The baseline must identify every original NPU and default history.")
    selected = {}
    for relative, expected in baseline["preexisting_files"].items():
        if type(relative) is not str or not valid_sha(expected):
            raise ValueError("Invalid prior-file baseline entry.")
        if relative.startswith("results/"):
            path = (ROOT / relative).resolve()
            if not path.is_relative_to(ROOT) or path.relative_to(ROOT).as_posix() != relative:
                raise ValueError("Unsafe baseline result path: " + relative)
            selected[path] = expected
    for kind, histories, required in (("npu", originals, ORIGINAL_HISTORIES), ("default", defaults, DEFAULT_HISTORIES)):
        names = set()
        for relative, expected in histories.items():
            name = Path(relative).name if type(relative) is str else None
            if not valid_sha(expected) or name not in required or relative != ".work/projects/" + kind + "/" + name or name in names:
                raise ValueError("Original history paths must be unique, canonical and baseline-hashed.")
            names.add(name)
            live = Path(data_directory).resolve() / name if kind == "npu" else ROOT / relative
            selected[live.resolve()] = expected
            selected[(Path(original_directory).resolve() / kind / name).resolve()] = expected
        if names != required:
            raise ValueError("The baseline is missing required " + kind + " source histories.")
    if not any(path.is_relative_to(ROOT / "results") for path in selected):
        raise ValueError("The baseline must protect the preexisting actual result payloads.")
    return selected


def preservation_snapshot(paths):
    files = {}; conflicts = []
    for path, expected in sorted(paths.items(), key=lambda item: str(item[0])):
        try:
            record = file_record(path)
            files[label(path)] = {**record, "expected_sha256": expected}
            if record["sha256"] != expected:
                conflicts.append({"path": label(path), "reason": "baseline_hash_mismatch"})
        except OSError as error:
            files[label(path)] = {"expected_sha256": expected, "error": str(error)}
            conflicts.append({"path": label(path), "reason": "missing_or_unreadable"})
    return {"validation_status": "Passed" if not conflicts else "Failed", "files": files, "conflicts": conflicts}


class RecordedResult(unittest.TextTestResult):
    """Keep standard unittest semantics plus structured full case outcomes."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cases = []; self._case = None; self._started = None

    def startTest(self, test):
        super().startTest(test)
        self._started = time.monotonic()
        self._case = {"id": test.id(), "description": self.getDescription(test), "status": "Running", "subtests": []}
        self.cases.append(self._case)

    def stopTest(self, test):
        if self._case is not None:
            self._case["elapsed_seconds"] = time.monotonic() - self._started
        super().stopTest(test)

    def case_for(self, test):
        # setUpClass/tearDownClass and module fixtures may report an error or
        # skip without startTest. Preserve those events instead of crashing.
        if self._case is None or self._case["id"] != test.id():
            self._case = {"id": test.id(), "description": self.getDescription(test), "status": "Running",
                          "subtests": [], "fixture_event_outside_test_start": True}
            self.cases.append(self._case)
        return self._case

    def addSuccess(self, test):
        super().addSuccess(test); self.case_for(test)["status"] = "Passed"

    def addFailure(self, test, error):
        super().addFailure(test, error)
        self.case_for(test).update(status="Failed", traceback=self._exc_info_to_string(error, test))

    def addError(self, test, error):
        super().addError(test, error)
        self.case_for(test).update(status="Error", traceback=self._exc_info_to_string(error, test))

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        parent = getattr(test, "test_case", None)
        if parent is not None:
            self.case_for(parent)["subtests"].append({"id": test.id(), "description": str(test), "status": "Skipped", "reason": reason})
        else:
            self.case_for(test).update(status="Skipped", reason=reason)

    def addExpectedFailure(self, test, error):
        super().addExpectedFailure(test, error)
        self.case_for(test).update(status="ExpectedFailure", traceback=self._exc_info_to_string(error, test))

    def addUnexpectedSuccess(self, test):
        super().addUnexpectedSuccess(test); self.case_for(test)["status"] = "UnexpectedSuccess"

    def addSubTest(self, test, subtest, error):
        super().addSubTest(test, subtest, error)
        case = self.case_for(test)
        outcome = {"id": subtest.id(), "description": str(subtest), "status": "Passed"}
        if error is not None:
            status = "Failed" if issubclass(error[0], test.failureException) else "Error"
            outcome.update(status=status, traceback=self._exc_info_to_string(error, test))
            if case["status"] != "Error": case["status"] = status
        case["subtests"].append(outcome)


def run_worker(report_path):
    """Child process only: normal discovery once, no project/EDA special cases."""
    started = now(); clock = time.monotonic(); result = None; error = None
    try:
        # Workspace-local test temporaries avoid the Windows sandbox's distinct
        # system-temp permissions. TemporaryDirectory cleanup stays scoped.
        temporary_root = ROOT / ".work/m2i/test-temp"
        temporary_root.mkdir(parents=True, exist_ok=True)
        tempfile.tempdir = str(temporary_root.resolve())
        suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
        result = unittest.TextTestRunner(verbosity=2, resultclass=RecordedResult).run(suite)
    except BaseException:
        error = traceback.format_exc(); sys.stderr.write(error)
    finished = now()
    successful = result is not None and result.testsRun > 0 and result.wasSuccessful() and all(case["status"] != "Running" for case in result.cases)
    report = {"record_kind": RECORD_KIND, "discovery": "complete unittest discovery of tests/ once",
        "started_at": started, "finished_at": finished, "elapsed_seconds": time.monotonic() - clock,
        "python_version": sys.version, "temporary_directory": str(tempfile.gettempdir()),
        "validation_status": "Passed" if successful and error is None else "Failed",
        "tests_run": result.testsRun if result else 0, "failures": len(result.failures) if result else 0,
        "errors": len(result.errors) if result else 0, "skipped": len(result.skipped) if result else 0,
        "expected_failures": len(result.expectedFailures) if result else 0,
        "unexpected_successes": len(result.unexpectedSuccesses) if result else 0,
        "case_outcomes": result.cases if result else [], "runner_error": error,
        "focused_test_counts_added": False, "software_fixtures_are_actual_physical_evidence": False}
    write_json(report_path, report)
    return 0 if report["validation_status"] == "Passed" else 1


def run(output, baseline_path, data_directory, original_directory):
    output = Path(output).resolve()
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise ValueError("Use a new empty QA directory; previous runs are immutable.")
    if any(output.is_relative_to(ROOT / folder) for folder in SOURCE_DIRECTORIES) or output.is_relative_to(Path(data_directory).resolve()):
        raise ValueError("QA output must be separate from product/test source and live project data.")
    output.mkdir(parents=True, exist_ok=True)
    started = now(); clock = time.monotonic(); baseline_raw = Path(baseline_path).read_bytes()
    baseline = strict_json(baseline_path); protected = protected_paths(baseline, data_directory, original_directory)
    before = source_snapshot(); preservation_before = preservation_snapshot(protected)
    # The new LVS history is frozen only for this suite. Original S01-S12
    # histories and their original copies are protected from the baseline.
    lvs_path = Path(data_directory).resolve() / "lvs_workflow.json"
    if not lvs_path.is_file():
        raise ValueError("Run the complete suite after the actual S13 history exists and settles.")
    lvs_history = strict_json(lvs_path)
    if type(lvs_history) is not dict or lvs_history.get("lvs_workflow_store_version") != "0.1" or not lvs_history.get("runs") or any(
            run.get("execution_status") not in ("Completed", "Failed", "Cancelled", "Interrupted") for run in lvs_history["runs"]):
        raise ValueError("Wait for the actual S13 attempt to settle before complete-suite execution.")
    lvs_before = file_record(lvs_path)
    write_json(output / "source_before.json", before); write_json(output / "preservation_before.json", preservation_before)
    (output / "source_baseline.json").write_bytes(baseline_raw)
    command = [sys.executable, "-X", "utf8", str(Path(__file__).resolve()), "--worker", "--worker-report", str(output / "case_outcomes.json")]
    write_json(output / "command.json", {"command": command, "working_directory": str(ROOT),
        "environment_overrides": {"PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}, "scope": RECORD_KIND})
    exit_code = None; runner_error = None
    if preservation_before["validation_status"] == "Passed":
        environment = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
        try:
            with (output / "stdout.txt").open("xb") as stdout, (output / "stderr.txt").open("xb") as stderr:
                completed = subprocess.run(command, cwd=ROOT, env=environment, stdout=stdout, stderr=stderr, check=False)
            exit_code = completed.returncode
        except BaseException:
            runner_error = traceback.format_exc()
    else:
        (output / "stdout.txt").write_bytes(b"")
        (output / "stderr.txt").write_bytes(b"The pre-run preservation guard failed; tests were not started.\n")
    after = source_snapshot(); preservation_after = preservation_snapshot(protected)
    lvs_after = file_record(lvs_path)
    write_json(output / "source_after.json", after); write_json(output / "preservation_after.json", preservation_after)
    outcomes = None
    if (output / "case_outcomes.json").exists():
        try: outcomes = strict_json(output / "case_outcomes.json")
        except (OSError, ValueError): runner_error = (runner_error or "") + traceback.format_exc()
    unchanged_sources = before == after
    unchanged_baseline = Path(baseline_path).read_bytes() == baseline_raw
    unchanged_proof = preservation_before == preservation_after and preservation_after["validation_status"] == "Passed"
    success = exit_code == 0 and outcomes is not None and outcomes.get("validation_status") == "Passed" and unchanged_sources and unchanged_baseline and unchanged_proof and lvs_before == lvs_after and runner_error is None
    report = {"record_kind": RECORD_KIND, "validation_status": "Passed" if success else "Failed", "started_at": started,
        "finished_at": now(), "elapsed_seconds": time.monotonic() - clock, "exit_code": exit_code,
        "executed": exit_code is not None, "python_version": sys.version, "working_directory": str(ROOT), "command": command,
        "baseline_sha256": hashlib.sha256(baseline_raw).hexdigest(), "source_files_before": len(before), "source_files_after": len(after),
        "source_and_test_files_unchanged": unchanged_sources, "baseline_file_unchanged": unchanged_baseline,
        "original_histories_and_prior_result_payloads_unchanged": unchanged_proof,
        "protected_file_count": len(protected), "original_NPU_history_count": len(baseline["original_NPU_histories"]),
        "default_history_count": len(baseline["default_histories"]),
        "original_history_copy_count": len(baseline["original_NPU_histories"]) + len(baseline["default_histories"]),
        "prior_result_file_count": sum(relative.startswith("results/") for relative in baseline["preexisting_files"]),
        "default_histories": sorted(baseline["default_histories"]), "documentation_changes_allowed": True,
        "physical_workflow_history_frozen_by_this_runner": True,
        "lvs_workflow_history_unchanged": lvs_before == lvs_after, "lvs_workflow_before": lvs_before, "lvs_workflow_after": lvs_after,
        "all_case_outcomes": "case_outcomes.json" if outcomes else None,
        "tests_run": outcomes.get("tests_run") if outcomes else None, "failures": outcomes.get("failures") if outcomes else None,
        "errors": outcomes.get("errors") if outcomes else None, "skipped": outcomes.get("skipped") if outcomes else None,
        "expected_failures": outcomes.get("expected_failures") if outcomes else None,
        "unexpected_successes": outcomes.get("unexpected_successes") if outcomes else None,
        "runner_error": runner_error, "focused_test_counts_added": False,
        "software_fixtures_are_actual_physical_evidence": False, "model_or_live_EDA_started_by_wrapper": False,
        "live_review_writes_by_wrapper": False}
    write_json(output / "report.json", report)
    files = {path.relative_to(output).as_posix(): file_record(path) for path in sorted(output.rglob("*")) if path.is_file()}
    write_json(output / "manifest.json", {"record_kind": RECORD_KIND, "validation_status": report["validation_status"],
        "files": files, "report": "report.json", "baseline_sha256": report["baseline_sha256"]})
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--baseline", type=Path, default=ROOT / ".work/m2i/baseline.json")
    parser.add_argument("--data-dir", type=Path, default=ROOT / ".work/projects/npu")
    parser.add_argument("--original-runtime", type=Path, default=ROOT / ".work/m2i/original_runtime")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--worker-report", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        if args.worker_report is None: parser.error("Internal worker requires its fresh report path.")
        return run_worker(args.worker_report)
    if args.output is None: parser.error("--output must identify a new QA run directory.")
    report = run(args.output, args.baseline, args.data_dir, args.original_runtime)
    print(json.dumps({key: report[key] for key in ("validation_status", "tests_run", "failures", "errors", "skipped", "exit_code", "elapsed_seconds")}))
    return 0 if report["validation_status"] == "Passed" else 1


if __name__ == "__main__": raise SystemExit(main())
