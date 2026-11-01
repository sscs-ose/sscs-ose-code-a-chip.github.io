"""Capture immutable Functional Map inputs without starting EDA or editing RTL.

Historical role profiles remain immutable; new source vocabularies are derived
from the saved bundle rather than circuit names or node counts. A capture establishes
byte correspondence, not a fresh physical verification or recovered ownership.
The caller owns the current-project/session guard and chooses the new output ID.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path, PurePosixPath
import re

from .domain import DomainError
from .global_workflow import source_bundle
from .layout_roles import (GENERIC_ROLE_PROFILE, LayoutRoleError, bridge_synthesis, generic_role_context,
                           parse_def_components, parse_structural_verilog, source_profile_values)
from .physical_workflow import _artifact_path
from .store import strict_loads
from .verification import content_hash, object_hash


TOP = "hullcirq_npu2_top"
ROLES = ("control", "buffer", "scheduler", "dispatcher", "pe00", "pe01", "pe10", "pe11", "collector", "post", "fifo")
RTL_INPUTS = (("candidate_top.v", TOP, "rtl-top"),) + tuple(
    ("npu2-" + role + ".v", "hullcirq_npu2_" + role, "rtl-npu2-" + role) for role in ROLES)
_SHA = re.compile(r"[0-9a-f]{64}")
_MUTABLE_REVIEW_FIELDS = {"record_hash", "review_status", "acceptance_epoch"}


def _require(condition, message, *, unsupported=False):
    if not condition:
        raise DomainError("functional_map_source_unsupported" if unsupported else "functional_map_source_integrity_error",
                          message, 409)


def _record(raw):
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def _json_bytes(value):
    return (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def _projection(run):
    return {key: value for key, value in run.items() if key not in _MUTABLE_REVIEW_FIELDS}


def _checksum(run):
    _require(type(run) is dict and run.get("record_hash") == object_hash(
        {key: value for key, value in run.items() if key != "record_hash"}), "Saved layout record checksum does not match.")


def _relative(relative):
    _require(type(relative) is str and relative and "\\" not in relative and ":" not in relative
             and not any(ord(c) < 32 for c in relative), "Source file path is not a safe relative path.")
    pure = PurePosixPath(relative)
    _require(not pure.is_absolute() and all(p not in ("", ".", "..") for p in relative.split("/")),
             "Source file path escapes its retained directory.")
    return Path(*pure.parts)


def _path_below(root, relative):
    path = (root / _relative(relative)).resolve()
    _require(path.is_relative_to(root.resolve()) and path != root.resolve(), "Source file path escapes its retained directory.")
    return path


def _declaration(entry):
    _require(type(entry) is dict and type(entry.get("bytes")) is int and entry["bytes"] > 0
             and type(entry.get("sha256")) is str and _SHA.fullmatch(entry["sha256"]) is not None,
             "Source file requires a positive byte count and exact saved SHA-256.")
    return {key: entry[key] for key in ("bytes", "sha256")}


def _one(entries, key, value):
    selected = [entry for entry in entries if type(entry) is dict and entry.get(key) == value]
    _require(len(selected) == 1, "Require one exact retained input: " + value)
    return selected[0]


def _expected_source_bundle(run):
    """Validate saved provenance, independently of S08's finite circuit checker.

    Functional annotation does not qualify a design for S08 execution. Reusing
    that execution adapter here would unnecessarily restrict valid saved S11s
    to the adapter's historical example circuits.
    """
    manifest = run["source_manifest"]
    nodes = manifest.get("nodes")
    design = manifest.get("design")
    _require(type(nodes) is list and type(design) is dict and type(design.get("nodes")) is list,
             "Preserve the complete saved graph and adopted source definitions.")
    node_ids = [node.get("node_id") for node in nodes if type(node) is dict]
    design_ids = [node.get("id") for node in design["nodes"] if type(node) is dict]
    _require(len(node_ids) == len(nodes) and len(design_ids) == len(design["nodes"])
             and len(set(node_ids)) == len(node_ids) and len(set(design_ids)) == len(design_ids)
             and set(node_ids) == set(design_ids), "The source manifest must retain every saved graph definition exactly once.")
    top_text = re.sub(r"/\*.*?\*/|//[^\n]*", " ", run["global_rtl"], flags=re.S)
    declarations = re.findall(r"\bmodule\s+([A-Za-z_][A-Za-z0-9_$]*)\b", top_text)
    _require(len(declarations) == 1, "Preserve one saved integration top module.")
    result = [{"file": "candidate_top.v", "module_name": declarations[0], "sha256": run["global_rtl_sha256"]}]
    for node in nodes:
        filename = node["node_id"] + ".v"
        _relative(filename)
        _require(type(node.get("rtl")) is str and node.get("rtl_sha256") == content_hash(node["rtl"])
                 and type(node.get("module_name")) is str and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_$]*", node["module_name"]),
                 "Every saved node requires exact RTL and a public module identifier.")
        design_node = next(item for item in design["nodes"] if item["id"] == node["node_id"])
        _require(design_node.get("module_name") == node["module_name"], "Saved graph and source definition module names disagree.")
        result.append({"file": filename, "module_name": node["module_name"], "sha256": node["rtl_sha256"]})
    _require(len({entry["module_name"] for entry in result}) == len(result)
             and len({entry["file"] for entry in result}) == len(result), "Saved source files and module definitions must be unique.")
    return result


def _check_run(run):
    _checksum(run)
    _require(re.fullmatch(r"physical-workflow-[0-9a-f]{32}", run.get("id", "")) is not None,
             "Require a saved physical-workflow run identifier.")
    checks = run.get("checks")
    _require(run.get("execution_status") == "Completed" and run.get("validation_status") == "Passed"
             and run.get("review_status") == "Accepted" and run.get("error") is None
             and run.get("evidence_kind") in ("trusted_fixed_tool_execution", "trusted_saved_tool_revalidation")
             and type(checks) is dict and checks.get("origin") == "trusted_fixed_tool_adapter"
             and checks.get("validation_status") == "Passed" and checks.get("executed") is True
             and type(checks.get("exit_code")) is int and checks["exit_code"] == 0
             and checks.get("cleanup_unresolved") is False and checks.get("software_qa_fixture") is not True,
             "Generate a map only from a Completed / Passed / Accepted trusted layout with resolved process cleanup.")
    _require(type(run.get("global_rtl")) is str and content_hash(run["global_rtl"]) == run.get("global_rtl_sha256")
             and type(run.get("source_manifest")) is dict
             and object_hash(run["source_manifest"]) == run.get("source_manifest_sha256"),
             "Saved RTL or source-manifest hash changed.")
    bundle = checks.get("source_bundle")
    _require(type(bundle) is list and bundle, "A Functional Map requires the saved source bundle.")
    _require(object_hash(bundle) == object_hash(_expected_source_bundle(run)),
             "Physical source bundle no longer matches the saved top and adopted nodes.")
    if run["evidence_kind"] == "trusted_saved_tool_revalidation":
        _require(run.get("execution_kind") == "saved_outputs_no_new_tool_start"
                 and type(run.get("prior_run_id")) is str and checks.get("execution_reused") is True
                 and checks.get("revalidated_from_run_id") == run["prior_run_id"]
                 and type(checks.get("revalidation_tool_starts")) is int and checks["revalidation_tool_starts"] == 0
                 and type(checks.get("revalidation_model_calls")) is int and checks["revalidation_model_calls"] == 0,
                 "Saved-output revalidation must retain its no-new-tool provenance.")
    return checks


def _rtl_inputs(run):
    """Exact app source-bundle filenames; no circuit-specific vocabulary gate."""
    return tuple((entry["file"], entry["module_name"], "rtl-top" if index == 0 else "rtl-" + entry["file"][:-2])
                 for index, entry in enumerate(run["checks"]["source_bundle"]))


def _legacy_bundle(run):
    return _rtl_inputs(run) == RTL_INPUTS


def eligibility(run):
    """Pure eligibility explanation; the caller additionally checks Current."""
    try:
        _check_run(run)
    except DomainError as error:
        return {"supported": False, "reason": {"code": error.code, "message": error.message}}
    except (KeyError, TypeError, ValueError) as error:
        return {"supported": False, "reason": {"code": "functional_map_source_integrity_error", "message": str(error)}}
    return {"supported": True, "reason": None,
            "source_profile": "npu2_explicit_2x2_v1" if _legacy_bundle(run) else GENERIC_ROLE_PROFILE,
            "scope": "saved_S11_artifact_bound_annotation_not_circuit_qualification"}


def _registrations():
    # Lazy import: serving may import the capture service.  These are server
    # constants, never browser-provided archive paths or manifest hashes.
    from . import layout_role_view
    return {layout_role_view.RUN_ID: layout_role_view._registration(layout_role_view.RUN_ID),
            **layout_role_view.ADDITIONAL_BUNDLES}


def _archive(root, identifier, registration, observations):
    relative = registration.get("source_root")
    _require(type(relative) is str and re.fullmatch(r"results/[A-Za-z0-9_-]+", relative) is not None,
             "Registered source archive path is invalid.")
    folder = _path_below(root, relative)
    manifest_path = _path_below(folder, "manifest.json")
    manifest_raw = manifest_path.read_bytes()
    _require(hashlib.sha256(manifest_raw).hexdigest() == registration.get("source_manifest_sha256"),
             "Registered source archive manifest changed.")
    manifest = strict_loads(manifest_raw.decode("utf-8"))
    _require(type(manifest) is dict and manifest.get("validation_status") == "Passed"
             and manifest.get("layout_run_id") == identifier and type(manifest.get("files")) is dict,
             "Registered archive does not bind its exact physical run.")
    observations[manifest_path] = manifest_raw

    def read(relative):
        path = _path_below(folder, relative)
        expected = _declaration(manifest["files"].get(relative))
        raw = path.read_bytes()
        _require(_record(raw) == expected, "Registered source archive input changed: " + relative)
        observations[path] = raw
        return raw

    archived = strict_loads(read("layout_record.json").decode("utf-8"))
    _checksum(archived)
    _require(archived.get("id") == identifier and archived.get("execution_status") == "Completed"
             and archived.get("validation_status") == "Passed" and archived.get("review_status") == "Accepted",
             "Registered source record is not the exact adopted layout.")
    return read, archived, {"source_root": relative, "manifest_sha256": hashlib.sha256(manifest_raw).hexdigest(),
                            "layout_run_id": identifier, "layout_record_sha256": archived["record_hash"]}


def _artifact_bytes(root, run, entry, fallback, observations):
    """Do not read external paths; never hide a readable hash mismatch."""
    expected = _declaration(entry)
    relative = entry.get("relative_path")
    _relative(relative)
    checks = run["checks"]
    recorded = checks.get("artifacts_directory")
    _require(type(recorded) is str and Path(recorded).is_absolute(), "Require the saved absolute physical result directory.")
    result_root = Path(recorded).resolve()
    _path_below(result_root, relative)
    # Missing migrated host paths may use only an already pinned archive of the
    # SAME raw run.  A current readable source always wins and must hash exactly.
    work_root = (root / ".work").resolve()
    _require(work_root.is_relative_to(root), "The workspace .work directory cannot redirect outside the project.")
    if result_root.is_relative_to(work_root):
        try:
            path = _artifact_path(checks, entry)
            raw = path.read_bytes()
        except DomainError as error:
            if error.code != "physical_artifact_missing":
                raise
        except FileNotFoundError:
            pass
        else:
            _require(_record(raw) == expected, "Retained physical bytes changed: " + relative)
            observations[path] = raw
            return raw, "retained_result_file"
    _require(fallback is not None, "The exact retained layout input is missing; no pinned same-run archive is available.")
    target = ("artifacts/" + entry["relative_path"] if entry["id"].startswith("rtl-") else
              {"gds": "artifacts/final.gds", "def": "artifacts/final.def", "netlist": "artifacts/final.nl.v"}[entry["id"]])
    raw = fallback(target)
    _require(_record(raw) == expected, "Pinned same-run archive differs from the selected retained artifact.")
    return raw, "registered_same_run_source_archive"


def _synthesis(root, run, rtl, same_archive, registrations, observations, *, generic=False):
    checks = run["checks"]
    retained = checks.get("retained_files")
    _require(type(retained) is list and all(type(entry) is dict and type(entry.get("relative_path")) is str
             for entry in retained), "Require a retained synthesis-file manifest.")
    paths = [entry.get("relative_path") for entry in retained]
    _require(len(paths) == len(set(paths)), "Duplicate retained synthesis-file paths.")
    matches = [entry for entry in retained if type(entry.get("relative_path")) is str
               and re.fullmatch(r"runs/physical/[0-9]+-yosys-synthesis/" + re.escape(checks["source_bundle"][0]["module_name"]) + r"\.nl\.v\.json", entry["relative_path"])]
    _require(len(matches) <= 1, "Ambiguous retained technology-mapped synthesis JSON.")
    if matches:
        result_root = Path(checks["artifacts_directory"]).resolve()
        entry = matches[0]
        path = _path_below(result_root, entry["relative_path"])
        # A missing retained path can use same-run immutable bytes below; a
        # readable mismatch is an integrity failure, never an archive fallback.
        if result_root.is_relative_to((root / ".work").resolve()) and path.is_file():
            raw_json = path.read_bytes()
            _require(_record(raw_json) == _declaration(entry), "Retained synthesis JSON bytes changed.")
            observations[path] = raw_json
            verilog_relative = entry["relative_path"][:-5]
            path_v = _path_below(result_root, verilog_relative)
            raw_v = path_v.read_bytes()
            declared_v = [item for item in retained if item.get("relative_path") == verilog_relative]
            if declared_v:
                _require(_record(raw_v) == _declaration(declared_v[0]), "Retained synthesis Verilog bytes changed.")
            observations[path_v] = raw_v
            return raw_json, raw_v, {"method": "retained_synthesis_json_and_same_directory_verilog",
                "json": {"source_relative_path": entry["relative_path"], "binding": "original_retained_declaration", **_record(raw_json)},
                "verilog": {"source_relative_path": verilog_relative, "binding": "original_retained_declaration" if declared_v else
                    "new_read_only_observation_not_originally_retained", "declared_in_original_retained_files": bool(declared_v), **_record(raw_v)}}
    candidates = []
    if same_archive is not None:
        candidates.append(same_archive)
    if checks.get("upstream_technology_mapping_reused") is True and checks.get("technology_mapping_executed") is False:
        for identifier, registered in registrations.items():
            if identifier == run["id"]:
                continue
            # A broken unrelated registered bundle does not make it a candidate;
            # matching source checks below must still pass before reuse.
            try:
                candidates.append(_archive(root, identifier, registered, observations))
            except (DomainError, OSError, ValueError, KeyError, TypeError):
                continue
    for read, archived, provenance in candidates:
        if any(archived.get(key) != run.get(key) for key in ("global_rtl_sha256", "source_manifest_sha256")):
            continue
        if any(read("artifacts/" + filename) != rtl["artifacts/" + filename] for filename, _, _ in _rtl_inputs(run)):
            continue
        return read("artifacts/synthesis.json"), read("artifacts/synthesis.v"), {
            "method": "checksum_pinned_source_archive_synthesis_reuse_no_fresh_mapping", **provenance,
            **({"all_source_rtl_bytes_equal": True, "source_rtl_count": len(_rtl_inputs(run))} if generic else {"all_twelve_source_rtl_bytes_equal": True}),
            "global_rtl_sha256": run["global_rtl_sha256"], "source_manifest_sha256": run["source_manifest_sha256"]}
    if generic:
        return None, None, {"method": "no_retained_synthesis_graph_attribution_withheld", "model_calls": 0, "eda_runs": 0}
    _require(False, "No retained synthesis graph or source-identical pinned synthesis archive is available.", unsupported=True)


def capture_source(root: Path, run: dict, output: Path) -> dict:
    """Freeze a server-selected new archive and return its renderer profile.

    All inputs are checked and re-read before creating output.  Existing archive
    directories are rejected.  Only the returned derived directory is written;
    source files, reviews, project stores and original archives are never edited.
    """
    root = Path(root).resolve()
    requested = Path(output)
    output = requested.resolve()
    _require(output.is_relative_to(root) and output.parent == (root / "results").resolve()
             and re.fullmatch(r"fm-source-[0-9a-f]{32}", output.name) is not None
             and not requested.is_symlink() and not getattr(requested, "is_junction", lambda: False)()
             and not output.exists(), "Use a new server-selected fm-source identifier directly below results.")
    selected = copy.deepcopy(run)
    checks = _check_run(selected)
    rtl_inputs = _rtl_inputs(selected)
    generic = not _legacy_bundle(selected)
    top_module = checks["source_bundle"][0]["module_name"]
    context = generic_role_context(top_module, checks["source_bundle"], selected["source_manifest"], selected["global_rtl"]) if generic else None
    registrations = _registrations()
    # A previously GUI-published source has the same immutable binding contract
    # as the shipped historical bundles. This enables regeneration after moving
    # a host without adding another source-code registration for the run.
    from .layout_map_generation import read_registration
    dynamic = read_registration(root, selected)
    if dynamic is not None:
        registrations = {**registrations, selected["id"]: dynamic}
    observations = {}
    same_archive = None
    registered = registrations.get(selected["id"])
    if registered is not None and registered.get("allow_registered_archive_artifact_fallback") is True:
        same_archive = _archive(root, selected["id"], registered, observations)
        _require(object_hash(_projection(same_archive[1])) == object_hash(_projection(selected)),
                 "Pinned same-run archive differs from the exact selected physical record.")
    artifacts = checks.get("artifacts")
    _require(type(artifacts) is list and all(type(entry) is dict for entry in artifacts)
             and len({entry.get("id") for entry in artifacts}) == len(artifacts), "Require unique retained physical artifact identifiers.")
    pending, bindings = {}, []
    source_texts = {"candidate_top.v": selected["global_rtl"], **{
        entry["node_id"] + ".v": entry["rtl"] for entry in selected["source_manifest"]["nodes"]}}
    fallback = same_archive[0] if same_archive is not None else None
    for filename, module_name, identifier in rtl_inputs:
        entry = _one(artifacts, "id", identifier)
        _require(entry.get("relative_path") == filename, "Source RTL artifact path changed.")
        bundle = _one(checks["source_bundle"], "file", filename)
        _require(entry.get("sha256") == bundle.get("sha256"), "Retained RTL and source-bundle hashes disagree.")
        raw, method = _artifact_bytes(root, selected, entry, fallback, observations)
        _require(raw == source_texts[filename].encode("utf-8"), "Retained RTL bytes differ from saved original source: " + filename)
        _require(re.search(r"\bmodule\s+" + re.escape(module_name) + r"(?=\s|[;(])", raw.decode("utf-8")) is not None,
                 "Retained RTL does not declare its saved public module: " + filename)
        target = "artifacts/" + filename
        pending[target] = raw
        bindings.append({"artifact_id": identifier, "target": target, "source_relative_path": filename, "method": method, **_record(raw)})
    for identifier, target in (("gds", "artifacts/final.gds"), ("def", "artifacts/final.def"), ("netlist", "artifacts/final.nl.v")):
        entry = _one(artifacts, "id", identifier)
        raw, method = _artifact_bytes(root, selected, entry, fallback, observations)
        pending[target] = raw
        bindings.append({"artifact_id": identifier, "target": target, "source_relative_path": entry["relative_path"], "method": method, **_record(raw)})
    raw_json, raw_v, synthesis_provenance = _synthesis(root, selected, pending, same_archive, registrations, observations, generic=generic)
    if raw_json is not None:
        pending["artifacts/synthesis.json"], pending["artifacts/synthesis.v"] = raw_json, raw_v
    try:
        final = parse_structural_verilog(pending["artifacts/final.nl.v"].decode("utf-8"))
        components = parse_def_components(pending["artifacts/final.def"].decode("utf-8"))
        _require(final["top"] == top_module, "Final mapped netlist must contain the saved source top.")
        synthesis = None
        bridge = {"method": "unavailable_no_attribution_claimed"}
        if raw_json is not None:
            document = strict_loads(raw_json.decode("utf-8"))
            _require(type(document) is dict and type(document.get("modules")) is dict and top_module in document["modules"],
                     "Mapped synthesis must contain the saved top.")
            flat = all(name == top_module or int(module.get("attributes", {}).get("blackbox", "0"), 2) == 1
                       for name, module in document["modules"].items())
            if generic and not flat:
                # A retained hierarchical graph is valid physical input, but
                # this flat graph bridge cannot prove its source attribution.
                # Preserve the raw synthesis bytes and show final geometry as
                # unknown rather than guessing a flattened hierarchy.
                bridge = {"method": "hierarchical_synthesis_attribution_withheld"}
            else:
                _require(flat, "Synthesis JSON must contain one mapped top and only blackbox cell libraries.")
                synthesis = parse_structural_verilog(raw_v.decode("utf-8"))
                _require(synthesis["top"] == top_module, "Mapped synthesis and final netlists must contain the saved top.")
                _, bridge = bridge_synthesis(document["modules"][top_module], synthesis)
        _require(set(final["cells"]) == set(components) and all(
            final["cells"][name]["master"] == master for name, master in components.items()),
            "Final DEF and mapped netlist instance/master inventories differ.")
    except (LayoutRoleError, UnicodeError, ValueError, KeyError, TypeError) as error:
        raise DomainError("functional_map_source_integrity_error", "Saved structural source correspondence failed: " + str(error), 409) from error
    pending["layout_record.json"] = _json_bytes(selected)
    pending["source_binding.json"] = _json_bytes({"schema_version": 1, "kind": "gui_functional_map_source_binding",
        "layout_run_id": selected["id"], "layout_record_sha256": selected["record_hash"],
        "global_rtl_sha256": selected["global_rtl_sha256"], "source_manifest_sha256": selected["source_manifest_sha256"],
        "artifact_bindings": bindings, "synthesis_inputs": synthesis_provenance,
        **({"role_context": context} if generic else {}),
        "structural_checks": {"top_module": top_module, "synthesis_cells": len(synthesis["cells"]) if synthesis else 0, "final_cells": len(final["cells"]),
            "def_components": len(components), "synthesis_json_verilog_bridge": bridge, "final_netlist_def_exact_instance_master_match": True},
        "derivation_activity": {"model_calls": 0, "rtl_generations": 0, "rtl_edits": 0, "eda_runs": 0,
            "review_or_adoption_actions": 0, "saved_project_mutations": 0}})
    pending["README.md"] = ("# GUI-generated Functional Map source\n\n"
        "Immutable presentation inputs for `" + selected["id"] + "`. All " + str(len(rtl_inputs)) + " original RTL files, final GDS, DEF and mapped "
        "netlist are byte-bound to the selected accepted layout. Synthesis provenance distinguishes retained inputs, fresh read-only "
        "observations and checksum-pinned reuse. Capture runs no EDA or model, edits no RTL and changes no circuit adoption. "
        "Functional annotations are not formal equivalence, recovered module ownership or new physical verification.\n").encode("utf-8")
    manifest_raw = _json_bytes({"schema_version": 1, "kind": "immutable_gui_functional_map_source", "validation_status": "Passed",
        "validation_scope": "archive_integrity_and_exact_selected_S11_binding_only", "layout_run_id": selected["id"],
        "files": {relative: _record(raw) for relative, raw in pending.items()}})
    profile = {"source_root": output.relative_to(root).as_posix(), "source_manifest_sha256": hashlib.sha256(manifest_raw).hexdigest(),
        "layout_run_id": selected["id"], "inputs": {"synthesis_json": "artifacts/synthesis.json", "synthesis_verilog": "artifacts/synthesis.v",
            "final_verilog": "artifacts/final.nl.v", "final_def": "artifacts/final.def"},
        "expected_final_cells": len(final["cells"]), "expected_synthesis_cells": len(synthesis["cells"]) if synthesis else 0,
        "gds_relative_path": "artifacts/final.gds", "role_profile": GENERIC_ROLE_PROFILE if generic else "npu2_explicit_2x2_v1", "annotation_policy": "changed_family_unknown_v1",
        **({"role_context": context} if generic else {})}
    if synthesis is None:
        profile["inputs"] = {key: profile["inputs"][key] for key in ("final_verilog", "final_def")}
    source_profile_values(profile)
    _require(run == selected, "Selected layout record changed during source capture.")
    for path, raw in observations.items():
        _require(path.read_bytes() == raw, "A retained input changed during source capture.")
    output.mkdir(parents=False)
    for relative, raw in {**pending, "manifest.json": manifest_raw}.items():
        target = output / _relative(relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(raw)
    return profile
