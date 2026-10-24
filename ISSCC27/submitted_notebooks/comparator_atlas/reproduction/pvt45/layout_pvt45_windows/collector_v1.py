"""Exact console-notice correction with linked raw-evidence acceptance, not warning suppression."""

from __future__ import annotations

import copy
from dataclasses import asdict
import json
from pathlib import Path
import re
import sys

from windows_contract import (
    DEADLINES, ENTRY, HERE, audit_executor_pins, canonical_sha256,
    phase, require, runtime_markers, sha256,
)

DECLARATION = json.loads((HERE / "continuation-declaration.json").read_text())
NOTICE = "Comments and warnings go to log-file: ngspice.log"


def audit_correction_pins() -> dict:
    audit_executor_pins()
    pins = json.loads((HERE / "correction-pins.json").read_text())
    for name, expected in pins["files"].items():
        require(sha256(HERE / name) == expected, f"Frozen reporting correction changed: {name}")
    require(sha256(HERE / "execution-protocol.json")
            == DECLARATION["original_executor"]["execution_protocol_sha256"]
            and sha256(HERE / "executor-pins.json")
            == DECLARATION["original_executor"]["executor_pins_sha256"],
            "Reporting correction changed the frozen physical executor")
    return pins


def classify(log: str, console: str) -> dict:
    info = []
    warnings = []
    errors = []
    for source, text in (("ngspice.log", log), ("console.log", console)):
        for line in text.splitlines():
            if source == "console.log" and line == NOTICE:
                info.append({"source": source, "text": line})
                continue
            if "warning" in line.lower():
                warnings.append({"source": source, "text": line})
            if re.search(r"^\s*(?:error\b|fatal\b)|unknown parameter|unknown device|unknown subckt|"
                         r"no such vector|timestep too small|convergence failed|simulation interrupted",
                         line, re.I):
                errors.append({"source": source, "text": line})
    return {"information": info, "warnings": warnings, "errors": errors,
            "only_exact_console_notice_exempted": True}


def review(directory: Path, legacy: dict) -> dict:
    for name, expected in legacy["artifact_sha256"].items():
        require(sha256(directory / name) == expected, f"Retained evidence changed before review: {name}")
    metadata_path = directory / "metadata.json"
    require(json.loads(metadata_path.read_text()) == legacy, "Original collector metadata was modified")
    log = (directory / "ngspice.log").read_text(errors="replace") if (directory / "ngspice.log").exists() else ""
    console = (directory / "console.log").read_text(errors="replace")
    classification = classify(log, console)
    result = copy.deepcopy(legacy)
    result["legacy_collector_status"] = legacy["status"]
    result["legacy_collector_error_code"] = legacy.get("error_code")
    result["legacy_collected_warning_lines"] = legacy.get("warnings", [])
    result["original_metadata_sha256"] = sha256(metadata_path)
    result["reporting_correction"] = {
        "declaration_sha256": sha256(HERE / "continuation-declaration.json"),
        "correction_pins_sha256": sha256(HERE / "correction-pins.json"),
        "classification": classification, "new_transients_performed_by_review": 0,
        "original_record_kept_verbatim": True,
    }
    eligible = (legacy["status"] == "success" or (
        legacy["status"] == "measurement_error"
        and legacy.get("error_code") == "unreviewed_actual_simulator_warning"))
    if not eligible or classification["warnings"] or classification["errors"]:
        result["reporting_correction"]["accepted"] = False
        return result
    require(legacy.get("returncode") == 0
            and re.findall(r"^(NOMINAL27_TRANSIENT_COMPLETE)[ \t]*\r?$", log, re.M)
            == ["NOMINAL27_TRANSIENT_COMPLETE"],
            "Missing actual successful transient completion")
    markers = runtime_markers(log)
    require(markers == legacy.get("startup_markers"), "Actual startup proof differs from record")
    mode = legacy["mode"]
    target = phase.PROTOCOL["immutable_target"]
    devices = phase.historical.DEVICES if mode == "schematic" else phase.historical.read_spice(
        ENTRY / target["rc_path"])["devices"]
    geometry = phase.native_simulator.audit_geometry(log, devices)
    require(geometry["observed_device_count"] == legacy.get("geometry_device_count") == 27
            and geometry == json.loads((directory / "actual-geometry.json").read_text()),
            "Missing or changed actual 27-device SI geometry evidence")
    sys.path.insert(0, str(ENTRY))
    import numpy as np
    from comparator_atlas import spice
    with np.load(directory / "waveform.npz", allow_pickle=False) as data:
        require(data.files == ["values"], "Unexpected raw waveform payload")
        values = data["values"]
    spice.validate_waveform(values)
    point = spice.Point(**legacy["point"])
    trace = spice.Trace(point, values, legacy["attempt_id"], directory, ())
    measurements = [asdict(spice.measure(trace, deadline)) for deadline in DEADLINES]
    require(measurements == legacy["measurements"] and legacy.get("reset_ok") is True
            and legacy.get("waveform_validated") is True,
            "Reset/waveform/published measurement evidence did not pass unchanged")
    result["status"] = "success"
    result["warnings"] = []
    result.pop("error_code", None)
    result["reporting_correction"]["accepted"] = True
    result["report_acceptance_identity"] = canonical_sha256({
        "actual_physical_run_identity": legacy["run_identity"],
        "original_metadata_sha256": result["original_metadata_sha256"],
        "reporting_correction": result["reporting_correction"],
    })
    return result
