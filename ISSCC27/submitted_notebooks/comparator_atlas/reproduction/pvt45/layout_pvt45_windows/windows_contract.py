"""Versioned native-Windows identity and runtime gates; historical code is read-only."""

from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import sys

HERE = Path(__file__).resolve().parent
ENTRY = HERE.parent
sys.path.insert(0, str(ENTRY / "layout_pvt45"))
import phase

IntegrityError = phase.IntegrityError
require = phase.require
sha256 = phase.sha256
canonical_sha256 = phase.canonical_sha256
write_json = phase.write_json
STEPS = phase.STEPS
MODES = phase.MODES
DEADLINES = phase.DEADLINES
EXECUTION = json.loads((HERE / "execution-protocol.json").read_text())


def audit_sealed() -> dict:
    sealed = EXECUTION["sealed_inputs"]
    paths = {
        "feasibility_protocol_sha256": HERE / "protocol.json",
        "remote_protocol_sha256": ENTRY / "layout_pvt45" / "protocol.json",
        "matrix_sha256": ENTRY / "layout_pvt45" / "matrix.json",
        "runtime_pins_sha256": HERE / "evidence" / "runtime-pins.json",
        "raw_model_manifest_sha256": HERE / "evidence" / "model-raw-sha256.json",
        "static_deck_plan_sha256": HERE / "evidence" / "static-deck-plan.json",
    }
    for field, path in paths.items():
        require(sha256(path) == sealed[field], f"Sealed input changed: {path.name}")
    limits = EXECUTION["hard_limits"]
    require((limits["total_charged_attempts"], limits["initial_attempts_before_adaptive"],
             limits["additional_attempts"], limits["maximum_workers"], limits["ngspice_threads"],
             limits["maximum_execution_windows"], limits["window_seconds"]) ==
            (900, 720, 180, 2, 1, 2, 1800), "Released hard limits changed")
    require(EXECUTION["startup"]["first_scheduled_point_id"] == "c01-schematic-m10"
            and EXECUTION["startup"]["first_step_ps"] == 10,
            "First counted serial matrix trace changed")
    prior = phase.audit_inputs()
    return {"sealed_sha256": {name: sha256(path) for name, path in paths.items()},
            "historical_read_only_input_audit": prior}


def audit_executor_pins() -> dict:
    path = HERE / "executor-pins.json"
    require(path.is_file(), "Executor identities must be frozen before any data")
    pins = json.loads(path.read_text())
    for name, expected in pins["files"].items():
        require(sha256(HERE / name) == expected, f"Frozen Windows executor changed: {name}")
    for name, expected in pins["inherited_pure_helpers"].items():
        require(sha256(ENTRY / name) == expected, f"Sealed pure helper changed: {name}")
    return pins


def audit_runtime(executable: Path) -> dict:
    require(os.name == "nt", "This execution variant is native Windows only")
    require(sys.dont_write_bytecode and os.environ.get("PYTHONDONTWRITEBYTECODE") == "1",
            "Disable bytecode before importing parent-installed modules")
    import numpy as np
    pins = json.loads((HERE / "evidence" / "runtime-pins.json").read_text())
    require(platform.python_version() == pins["python_version"] == "3.12.10",
            "Unpinned native Python version")
    require(np.__version__ == pins["numpy_version"] == "2.2.6", "Unpinned NumPy version")
    require(sha256(Path(sys.executable).resolve()) == pins["python_launcher_sha256"],
            "Unpinned Python launcher")
    base = Path(sys._base_executable).resolve().parent
    for name, expected in pins["python_runtime_files"].items():
        require(sha256(base / name) == expected, f"Python runtime file changed: {name}")
    numpy_root = Path(np.__file__).resolve().parent
    require(sha256(Path(np.__file__)) == pins["numpy_init_sha256"], "NumPy initialization changed")
    for name, expected in pins["numpy_native_files"].items():
        require(sha256(numpy_root.parent / name) == expected, f"NumPy native component changed: {name}")
    require(executable.name.lower() == "ngspice_con.exe", "Wrong native console executable")
    for name, record in pins["ngspice_bin_files"].items():
        require(sha256(executable.parent / name) == record["sha256"], f"ngspice component changed: {name}")
    tool_root = executable.parent.parent
    require(sha256(tool_root / "share" / "ngspice" / "scripts" / "spinit")
            == pins["ngspice_global_startup_sha256"], "Installed startup resource changed")
    for name, record in pins["ngspice_global_codemodel_files"].items():
        require(sha256(tool_root / "lib" / "ngspice" / name) == record["sha256"],
                f"Installed codemodel changed: {name}")
    return {
        "python_version": platform.python_version(), "numpy_version": np.__version__,
        "runtime_pin_sha256": sha256(HERE / "evidence" / "runtime-pins.json"),
        "ngspice_console_sha256": sha256(executable),
        "all_installed_components_match_sealed_windows47_manifest": True,
        "bytecode_disabled": True, "no_absolute_parent_paths_recorded": True,
    }


def audit_raw_models(directory: Path) -> dict:
    manifest = json.loads((HERE / "evidence" / "model-raw-sha256.json").read_text())
    require(len(manifest["files"]) == 400, "Wrong pinned model/license count")
    for name, record in manifest["files"].items():
        require(sha256(directory / name) == record["actual_parent_sha256"],
                f"Raw Windows model snapshot mismatch: {name}")
    return {
        "revision": manifest["model_revision"], "files": 400,
        "raw_manifest_sha256": sha256(HERE / "evidence" / "model-raw-sha256.json"),
        "raw_bytes_not_normalized": True,
        "canonical_git_identities_retained_in_sealed_manifest": True,
    }


def make_deck(definition: dict, step: float) -> str:
    sys.path.insert(0, str(ENTRY))
    from comparator_atlas.spice import Point
    mode = definition["mode"]
    point = Point(**definition["physical_point"], max_step_ps=step)
    target = phase.PROTOCOL["immutable_target"]
    path = ENTRY / target[f"{mode}_path"]
    require(sha256(path) == target[f"{mode}_sha256"], "Native schematic/RC changed")
    devices = (phase.historical.DEVICES if mode == "schematic"
               else phase.historical.read_spice(path)["devices"])
    original = phase.native_simulator.make_deck(
        mode, point, path.read_text(), Path("../../model-source"), devices)
    command = f"tran {step:.12g}p 30n 19n {step:.12g}p\n"
    require(original.count(command) == 1, "Ambiguous inherited transient command")
    controls = "\n".join(EXECUTION["child_execution"]["control_only_lines_before_tran"]) + "\n"
    deck = original.replace(command, controls + command, 1)
    require(deck.count("scale=1u") == 1 and path.read_text().rstrip() in deck,
            "Native passives or single geometry scaling changed")
    plan = json.loads((HERE / "evidence" / "static-deck-plan.json").read_text())
    require(hashlib.sha256(deck.encode()).hexdigest()
            == plan["points"][definition["point_id"]][str(step)]["unexecuted_deck_sha256"],
            "Executed deck differs from prospectively assessed deck")
    return deck


def deck_identity(runtime_identity: dict, definition: dict, step: float, deck: str) -> str:
    return canonical_sha256({
        "variant": EXECUTION["execution_variant"], "runtime_identity": runtime_identity,
        "physical_point": definition, "max_step_ps": step,
        "executed_deck_sha256": hashlib.sha256(deck.encode()).hexdigest(),
        "startup_sha256": hashlib.sha256(EXECUTION["child_execution"]["local_spiceinit"].encode()).hexdigest(),
        "numerical_policy": phase.PROTOCOL["numerics"],
    })


def runtime_markers(text: str) -> dict:
    observed = {}
    for name, expected in (("PVT45W47_NUM_THREADS", "1"), ("PVT45W47_COMPAT", "hsa")):
        matches = re.findall(r"^" + name + r"\s+(\S+)\s*$", text, re.M)
        require(matches == [expected], f"Missing, repeated or incorrect actual startup marker: {name}")
        observed[name] = matches[0]
    return {"qualified": True, "actual_markers": observed, "requires_si_geometry_and_reset_too": True}


def serial_gate(record: dict) -> bool:
    return (record["status"] == "success" and record.get("startup_markers", {}).get("qualified") is True
            and record.get("geometry_device_count") == 27 and record.get("reset_ok") is True
            and record.get("waveform_validated") is True)


def check_reservation(attempts: list[dict], point_id: str, step: float) -> None:
    require(len(attempts) < 900, "900 total charged-attempt cap reached")
    require(not any(a["point_id"] == point_id and a["max_step_ps"] == step for a in attempts),
            "Duplicate attempted endpoint is not permitted")
    previous = [a["max_step_ps"] for a in attempts if a["point_id"] == point_id]
    require(len(previous) < len(STEPS) and previous == STEPS[:len(previous)]
            and step == STEPS[len(previous)], "Numerical endpoint restarted or skipped")
    if step not in STEPS[:2]:
        require(sum(a["max_step_ps"] in STEPS[:2] for a in attempts) == 720,
                "All 720 initial attempts must precede optional refinements")
        require(sum(a["max_step_ps"] not in STEPS[:2] for a in attempts) < 180,
                "180 additional-attempt cap reached")


def verify_record(out: Path, attempt: dict) -> dict:
    directory = out / "transients" / attempt["attempt_id"]
    require(sha256(directory / "metadata.json") == attempt["metadata_sha256"],
            "Changed actual attempt receipt")
    record = json.loads((directory / "metadata.json").read_text())
    for key in ("attempt_id", "run_identity", "point_id", "max_step_ps"):
        require(record[key] == attempt[key], f"Attempt identity changed: {key}")
    for name, expected in record["artifact_sha256"].items():
        require(sha256(directory / name) == expected, f"Raw attempt evidence changed: {name}")
    return record


def private_error(directory: Path, error: BaseException) -> dict:
    import traceback
    path = directory / "private-error.txt"
    path.write_text(traceback.format_exc(), encoding="utf-8", newline="\n")
    return {"error_type": type(error).__name__, "private_error_sha256": sha256(path),
            "private_error_retained": True,
            "message": "Exact diagnostics retained privately; no path-bearing text substituted as raw evidence."}
