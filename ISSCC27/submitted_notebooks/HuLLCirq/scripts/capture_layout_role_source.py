#!/usr/bin/env python3
"""Freeze the current adopted S11 inputs for an offline Functional Map.

This command only reads an already completed physical-workflow result.  It
does not invoke EDA, regenerate RTL, review/adopt a run, or modify ``.work``.
The output is a new, immutable archive below ``results``; an existing output
path is always rejected.

The Yosys JSON is covered by the physical run's retained-file manifest.  The
matching structural Verilog is an existing sibling in the same frozen run
directory, but the current run did not list that sibling in its public
artifact manifest.  Its bytes and newly observed hash are therefore recorded
explicitly instead of being represented as an original saved declaration.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hullcirq.layout_roles import (  # noqa: E402
    LayoutRoleError,
    bridge_synthesis,
    parse_def_components,
    parse_structural_verilog,
)
from hullcirq.store import strict_loads  # noqa: E402
from hullcirq.verification import object_hash  # noqa: E402


DEFAULT_STORE = (
    ROOT
    / ".work/projects/npu_2x2_explicit/systems/system-7df07952c6b64696813d14ab19837af8"
    / "physical_workflow.json"
)
DEFAULT_RUN_ID = "physical-workflow-7490fdd470a941c9b097033613816d72"
EXPECTED_RUN_RECORD_HASH = (
    "cb67921cea5616107a93c9a20d05c8fd25b624d5e98adfd9069961de8b40c88f"
)
DEFAULT_OUTPUT = ROOT / "results/npu2_layout_role_source_20261020"
TOP = "hullcirq_npu2_top"

RTL_INPUTS = (
    ("candidate_top.v", "hullcirq_npu2_top", "rtl-top"),
    ("npu2-control.v", "hullcirq_npu2_control", "rtl-npu2-control"),
    ("npu2-buffer.v", "hullcirq_npu2_buffer", "rtl-npu2-buffer"),
    ("npu2-scheduler.v", "hullcirq_npu2_scheduler", "rtl-npu2-scheduler"),
    ("npu2-dispatcher.v", "hullcirq_npu2_dispatcher", "rtl-npu2-dispatcher"),
    ("npu2-pe00.v", "hullcirq_npu2_pe00", "rtl-npu2-pe00"),
    ("npu2-pe01.v", "hullcirq_npu2_pe01", "rtl-npu2-pe01"),
    ("npu2-pe10.v", "hullcirq_npu2_pe10", "rtl-npu2-pe10"),
    ("npu2-pe11.v", "hullcirq_npu2_pe11", "rtl-npu2-pe11"),
    ("npu2-collector.v", "hullcirq_npu2_collector", "rtl-npu2-collector"),
    ("npu2-post.v", "hullcirq_npu2_post", "rtl-npu2-post"),
    ("npu2-fifo.v", "hullcirq_npu2_fifo", "rtl-npu2-fifo"),
)

LAYOUT_INPUTS = (
    (
        "gds",
        "runs/physical/57-magic-streamout/hullcirq_npu2_top.gds",
        "artifacts/final.gds",
    ),
    (
        "def",
        "runs/physical/53-odb-cellfrequencytables/hullcirq_npu2_top.def",
        "artifacts/final.def",
    ),
    (
        "netlist",
        "runs/physical/52-openroad-fillinsertion/hullcirq_npu2_top.nl.v",
        "artifacts/final.nl.v",
    ),
)

SYNTHESIS_JSON = "runs/physical/06-yosys-synthesis/hullcirq_npu2_top.nl.v.json"
SYNTHESIS_VERILOG = "runs/physical/06-yosys-synthesis/hullcirq_npu2_top.nl.v"


class CaptureError(ValueError):
    """The selected stored result cannot be frozen without weakening binding."""


def _require(condition, message):
    if not condition:
        raise CaptureError(message)


def _record(raw):
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def _json_bytes(value):
    return (
        json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    ).encode("utf-8")


def _one(entries, key, value, description):
    matches = [entry for entry in entries if entry.get(key) == value]
    _require(len(matches) == 1, f"Require exactly one {description}: {value}")
    return matches[0]


def _checked_relative_path(root, relative):
    _require(type(relative) is str, "Recorded source path must be text")
    pure = PurePosixPath(relative)
    _require(
        not pure.is_absolute()
        and pure.parts
        and not any(part in ("", ".", "..") for part in pure.parts)
        and "\\" not in relative
        and ":" not in relative
        and not any(ord(character) < 32 for character in relative),
        "Recorded source path is unsafe: " + repr(relative),
    )
    path = (root / Path(*pure.parts)).resolve()
    _require(
        path.is_relative_to(root.resolve()) and path != root.resolve() and path.is_file(),
        "Recorded source file is missing or outside the adopted result: " + relative,
    )
    return path


def _declared_bytes(root, entry, expected_relative=None):
    _require(type(entry) is dict, "Invalid saved file declaration")
    relative = entry.get("relative_path")
    if expected_relative is not None:
        _require(relative == expected_relative, "Unexpected saved file path: " + str(relative))
    expected = {key: entry.get(key) for key in ("bytes", "sha256")}
    _require(
        type(expected["bytes"]) is int
        and expected["bytes"] > 0
        and type(expected["sha256"]) is str
        and re.fullmatch(r"[0-9a-f]{64}", expected["sha256"]) is not None,
        "Invalid saved file hash/length declaration",
    )
    raw = _checked_relative_path(root, relative).read_bytes()
    _require(_record(raw) == expected, "Saved source bytes do not match their declaration: " + relative)
    return raw


def _recorded_artifact_root(recorded):
    """Resolve the saved absolute path, including its exact WSL drive mount."""
    native = Path(recorded)
    if native.is_absolute():
        return native.resolve()
    windows = PureWindowsPath(recorded)
    drive_match = re.fullmatch(r"([A-Za-z]):", windows.drive)
    _require(
        sys.platform.startswith("linux")
        and windows.is_absolute()
        and drive_match is not None,
        "Require a native absolute result path or its exact Windows path in WSL",
    )
    return (
        Path("/mnt")
        / drive_match.group(1).lower()
        / Path(*windows.parts[1:])
    ).resolve()


def _resolve_artifact_root(recorded, working_root=None):
    saved = _recorded_artifact_root(recorded)
    candidate = saved if working_root is None else Path(working_root).resolve()
    expected_parent = (ROOT.resolve() / ".work/n2f/layout").resolve()
    _require(
        candidate == saved,
        "Working-root override must resolve to the exact saved result directory",
    )
    _require(
        candidate.parent == expected_parent
        and re.fullmatch(r"hullcirq-layout-[A-Za-z0-9_-]+", candidate.name)
        is not None
        and candidate.is_dir(),
        "Physical result directory must be the exact run directory below "
        "this HuLLCirq .work/n2f/layout tree",
    )
    return candidate


def _validate_store(store, run_id):
    _require(
        type(store) is dict
        and store.get("physical_workflow_store_version") == "0.1"
        and type(store.get("runs")) is list
        and store["runs"],
        "Require a non-empty physical-workflow v0.1 store",
    )
    _require(
        run_id == DEFAULT_RUN_ID,
        "This capture is pinned to the adopted 2026-10-20 physical run",
    )
    _require(
        re.fullmatch(r"physical-workflow-[0-9a-f]{32}", run_id) is not None,
        "Invalid physical run identifier",
    )
    run = _one(store["runs"], "id", run_id, "selected physical run")
    _require(store["runs"][-1].get("id") == run_id, "Require the latest physical run")
    _require(
        run.get("execution_status") == "Completed"
        and run.get("validation_status") == "Passed"
        and run.get("review_status") == "Accepted",
        "Require the latest Completed / Passed / Accepted physical run",
    )
    _require(
        run.get("record_hash") == EXPECTED_RUN_RECORD_HASH,
        "Unexpected physical run record hash for the pinned adopted run",
    )
    _require(
        run.get("record_hash")
        == object_hash({key: value for key, value in run.items() if key != "record_hash"}),
        "Physical run record hash mismatch",
    )
    _require(
        type(store.get("source_epoch")) is int
        and store.get("source_key") == run.get("source_key")
        and run.get("acceptance_epoch") == store.get("source_epoch"),
        "Require the adopted run for the current physical source epoch",
    )
    reviews = [review for review in store.get("reviews", []) if review.get("run_id") == run_id]
    _require(
        reviews
        and reviews[-1].get("decision") == "accepted"
        and reviews[-1].get("acceptance_epoch") == store.get("source_epoch"),
        "Require the saved acceptance review for the selected run",
    )
    checks = run.get("checks")
    _require(
        type(checks) is dict
        and checks.get("validation_status") == "Passed"
        and checks.get("executed") is True
        and checks.get("exit_code") == 0
        and checks.get("cleanup_unresolved") is False
        and checks.get("origin") == "trusted_fixed_tool_adapter"
        and run.get("evidence_kind") == "trusted_fixed_tool_execution",
        "Require the completed trusted physical execution with resolved cleanup",
    )
    return run


def _archive_readme(run_id):
    return (
        "# NPU 2x2 Functional Map source\n\n"
        f"This immutable, read-only bundle binds `{run_id}` to its exact twelve RTL "
        "inputs, synthesis graph, final mapped netlist, DEF and GDS. The synthesis "
        "Verilog was observed beside the manifest-pinned synthesis JSON in the same "
        "adopted result directory, so its observed byte hash is recorded explicitly. "
        "Capturing this bundle performs no RTL generation, model request, EDA run, "
        "review, adoption or mutation of the saved project.\n"
    ).encode("utf-8")


def capture(physical_store, output, run_id=DEFAULT_RUN_ID, working_root=None):
    """Create a new source archive and return a machine-readable capture summary."""
    root = ROOT.resolve()
    physical_store = Path(physical_store).resolve()
    output = Path(output).resolve()
    _require(
        physical_store.is_relative_to((root / ".work/projects").resolve())
        and physical_store.is_file(),
        "Physical store must be an existing project store below .work/projects",
    )
    _require(
        output.is_relative_to((root / "results").resolve())
        and output != (root / "results").resolve(),
        "Output must be a new directory below results",
    )
    _require(not output.exists(), "Output exists; prior evidence is never overwritten")

    store_raw = physical_store.read_bytes()
    try:
        store = strict_loads(store_raw.decode("utf-8"))
    except (UnicodeError, ValueError) as error:
        raise CaptureError("Physical store is not strict UTF-8 JSON") from error
    run = _validate_store(store, run_id)
    checks = run["checks"]
    artifact_root_text = checks.get("artifacts_directory")
    _require(type(artifact_root_text) is str, "Require the retained result directory")
    artifact_root = _resolve_artifact_root(artifact_root_text, working_root)
    artifacts = checks.get("artifacts")
    retained = checks.get("retained_files")
    source_bundle = checks.get("source_bundle")
    _require(
        type(artifacts) is list
        and type(retained) is list
        and type(source_bundle) is list,
        "Require physical artifact, retained-file and source-bundle manifests",
    )
    artifact_ids = [entry.get("id") for entry in artifacts]
    _require(len(artifact_ids) == len(set(artifact_ids)), "Duplicate physical artifact ID")
    retained_paths = [entry.get("relative_path") for entry in retained]
    _require(len(retained_paths) == len(set(retained_paths)), "Duplicate retained-file path")

    pending = {}
    rtl_binding = []
    _require(
        len(source_bundle) == len(RTL_INPUTS),
        "Require exactly the twelve source-bound NPU 2x2 RTL files",
    )
    for filename, module_name, artifact_id in RTL_INPUTS:
        source = _one(source_bundle, "file", filename, "source-bundle RTL")
        _require(
            source.get("module_name") == module_name
            and re.fullmatch(r"[0-9a-f]{64}", str(source.get("sha256"))) is not None,
            "Unexpected source-bundle module/hash: " + filename,
        )
        entry = _one(artifacts, "id", artifact_id, "physical RTL artifact")
        _require(
            entry.get("relative_path") == filename
            and entry.get("sha256") == source.get("sha256"),
            "RTL artifact and source bundle disagree: " + filename,
        )
        raw = _declared_bytes(artifact_root, entry, filename)
        target = "artifacts/" + filename
        pending[target] = raw
        rtl_binding.append(
            {
                "artifact_id": artifact_id,
                "source_relative_path": filename,
                "target": target,
                "module_name": module_name,
                **_record(raw),
            }
        )

    layout_binding = []
    for artifact_id, expected_relative, target in LAYOUT_INPUTS:
        entry = _one(artifacts, "id", artifact_id, "physical layout artifact")
        raw = _declared_bytes(artifact_root, entry, expected_relative)
        pending[target] = raw
        layout_binding.append(
            {
                "artifact_id": artifact_id,
                "source_relative_path": expected_relative,
                "target": target,
                **_record(raw),
            }
        )

    synthesis_json_entry = _one(
        retained, "relative_path", SYNTHESIS_JSON, "retained synthesis JSON"
    )
    synthesis_json_raw = _declared_bytes(
        artifact_root, synthesis_json_entry, SYNTHESIS_JSON
    )
    pending["artifacts/synthesis.json"] = synthesis_json_raw

    synthesis_verilog_path = _checked_relative_path(artifact_root, SYNTHESIS_VERILOG)
    synthesis_verilog_raw = synthesis_verilog_path.read_bytes()
    synthesis_verilog_record = _record(synthesis_verilog_raw)
    declared_synthesis_verilog = [
        entry for entry in retained if entry.get("relative_path") == SYNTHESIS_VERILOG
    ]
    _require(
        len(declared_synthesis_verilog) <= 1,
        "Duplicate retained synthesis Verilog declaration",
    )
    if declared_synthesis_verilog:
        _require(
            _record(_declared_bytes(artifact_root, declared_synthesis_verilog[0], SYNTHESIS_VERILOG))
            == synthesis_verilog_record,
            "Retained synthesis Verilog changed during capture",
        )
    pending["artifacts/synthesis.v"] = synthesis_verilog_raw

    try:
        synthesis_document = strict_loads(synthesis_json_raw.decode("utf-8"))
        _require(
            type(synthesis_document) is dict
            and type(synthesis_document.get("modules")) is dict
            and TOP in synthesis_document["modules"],
            "Synthesis JSON does not contain the expected top",
        )
        synthesis_graph = parse_structural_verilog(
            synthesis_verilog_raw.decode("utf-8")
        )
        _require(synthesis_graph["top"] == TOP, "Synthesis Verilog top mismatch")
        _, bridge = bridge_synthesis(
            synthesis_document["modules"][TOP], synthesis_graph
        )
        final_graph = parse_structural_verilog(
            pending["artifacts/final.nl.v"].decode("utf-8")
        )
        components = parse_def_components(
            pending["artifacts/final.def"].decode("utf-8")
        )
    except (UnicodeError, ValueError, KeyError, TypeError, LayoutRoleError) as error:
        raise CaptureError("Retained synthesis/final structural binding failed") from error
    _require(final_graph["top"] == TOP, "Final mapped netlist top mismatch")
    _require(
        set(final_graph["cells"]) == set(components)
        and all(
            final_graph["cells"][name]["master"] == master
            for name, master in components.items()
        ),
        "Final mapped netlist and DEF component inventory disagree",
    )

    # Re-read the source store and every captured input before creating output.
    # A concurrent source change fails closed and leaves no archive directory.
    _require(physical_store.read_bytes() == store_raw, "Physical store changed during capture")
    for relative, raw in pending.items():
        if relative.startswith("artifacts/"):
            if relative == "artifacts/synthesis.v":
                source_path = synthesis_verilog_path
            elif relative == "artifacts/synthesis.json":
                source_path = _checked_relative_path(artifact_root, SYNTHESIS_JSON)
            else:
                binding = next(
                    item
                    for item in rtl_binding + layout_binding
                    if item["target"] == relative
                )
                source_path = _checked_relative_path(
                    artifact_root, binding["source_relative_path"]
                )
            _require(source_path.read_bytes() == raw, "Source file changed during capture: " + relative)

    layout_record_raw = _json_bytes(run)
    pending["layout_record.json"] = layout_record_raw
    source_binding = {
        "schema_version": 1,
        "kind": "immutable_npu2_layout_role_source_binding",
        "layout_run_id": run_id,
        "revision_id": run.get("revision_id"),
        "source_key": run.get("source_key"),
        "source_epoch": store.get("source_epoch"),
        "record_hash": run.get("record_hash"),
        "lineage": {
            "global_job_id": run.get("global_job_id"),
            "synthesis_run_id": run.get("synthesis_run_id"),
            "netlist_run_id": run.get("netlist_run_id"),
            "global_context_id": run.get("global_context_id"),
            "global_rtl_sha256": run.get("global_rtl_sha256"),
            "source_manifest_sha256": run.get("source_manifest_sha256"),
            "verification_plan_sha256": run.get("verification_plan_sha256"),
            "vector_hash": run.get("vector_hash"),
            "testbench_sha256": run.get("testbench_sha256"),
            "public_boundary_vector_hash": run.get("public_boundary_vector_hash"),
        },
        "physical_store_snapshot": {
            "path": physical_store.relative_to(root).as_posix(),
            **_record(store_raw),
        },
        "layout_record": {"path": "layout_record.json", **_record(layout_record_raw)},
        "rtl_sources": rtl_binding,
        "layout_inputs": layout_binding,
        "synthesis_inputs": {
            "json": {
                "source_relative_path": SYNTHESIS_JSON,
                "target": "artifacts/synthesis.json",
                "binding": "original_checks.retained_files_declaration",
                **_record(synthesis_json_raw),
            },
            "verilog": {
                "source_relative_path": SYNTHESIS_VERILOG,
                "target": "artifacts/synthesis.v",
                "binding": (
                    "original_checks.retained_files_declaration"
                    if declared_synthesis_verilog
                    else "new_read_only_observation_of_exact_adopted_result_sibling"
                ),
                "declared_in_original_retained_files": bool(
                    declared_synthesis_verilog
                ),
                **synthesis_verilog_record,
            },
        },
        "structural_checks": {
            "top_module": TOP,
            "synthesis_cells": len(synthesis_graph["cells"]),
            "final_cells": len(final_graph["cells"]),
            "def_components": len(components),
            "synthesis_json_verilog_bridge": bridge,
            "final_netlist_def_exact_instance_master_match": True,
        },
        "derivation_activity": {
            "model_calls": 0,
            "rtl_generations": 0,
            "rtl_edits": 0,
            "eda_runs": 0,
            "review_or_adoption_actions": 0,
            "saved_project_mutations": 0,
        },
    }
    pending["source_binding.json"] = _json_bytes(source_binding)
    pending["README.md"] = _archive_readme(run_id)

    output.mkdir(parents=True)
    for relative, raw in pending.items():
        target = output / Path(*PurePosixPath(relative).parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as handle:
            handle.write(raw)
    manifest = {
        "schema_version": 1,
        "kind": "immutable_npu2_layout_role_source",
        "validation_status": "Passed",
        "validation_scope": "archive_integrity_and_exact_S11_binding_only",
        "layout_run_id": run_id,
        "files": {relative: _record(raw) for relative, raw in pending.items()},
    }
    manifest_raw = _json_bytes(manifest)
    with (output / "manifest.json").open("xb") as handle:
        handle.write(manifest_raw)

    return {
        "output": str(output),
        "layout_run_id": run_id,
        "files": len(pending) + 1,
        "archived_bytes": sum(len(raw) for raw in pending.values())
        + len(manifest_raw),
        "source_manifest_sha256": hashlib.sha256(manifest_raw).hexdigest(),
        "synthesis_cells": len(synthesis_graph["cells"]),
        "final_cells": len(final_graph["cells"]),
        "additional_eda_runs": 0,
        "saved_project_mutations": 0,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--physical-store", type=Path, default=DEFAULT_STORE)
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--working-root",
        type=Path,
        help=(
            "Exact saved run directory, for example its /mnt/c/... path in WSL; "
            "a different directory is rejected"
        ),
    )
    args = parser.parse_args()
    try:
        result = capture(
            args.physical_store,
            args.output,
            args.run_id,
            working_root=args.working_root,
        )
    except CaptureError as error:
        parser.error(str(error))
    print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
