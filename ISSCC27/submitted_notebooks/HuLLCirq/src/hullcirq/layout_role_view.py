"""Read-only serving of registered immutable Functional Maps for exact S11 records."""
from __future__ import annotations

import copy
import base64
import gzip
import hashlib
from pathlib import Path, PurePosixPath
import re

from .domain import DomainError
from .physical_workflow import _artifact_path
from .store import strict_loads
from .verification import object_hash


RUN_ID = "physical-workflow-f678bc2dd59949219132a7de80eb12af"
VIEW_ROOT = "results/npu_layout_role_view"
SOURCE_ROOT = "results/npu_layout_continuous_flow"
VIEW_MANIFEST_SHA256 = "3675f7002c8f1a36c90b5a2d57750d3ca1787d5925641d1dbf141e5b6b947d8d"
SOURCE_MANIFEST_SHA256 = "bc8431548dffe08c4f5c898f89ac9c6aeac3693a3432a75cc8c1054782b7599a"
# Added only after each new archive/map is frozen and verified. No run fallback.
ADDITIONAL_BUNDLES = {
    'physical-workflow-4e818ce3905c4bd1ad0e9b50033271cb': {
        'view_root': 'results/npu2_layout_repaired_role_view_20261021',
        'source_root': 'results/npu2_layout_repaired_source_20261021',
        'view_manifest_sha256': 'b204f63cda99b25a9debec2fb81a2bc29361bfb4564ce4b433b42a22cfad808d',
        'source_manifest_sha256': '4972e07cc646150c6757c5bca7bc0a8881dee00156d65c9f808fde21d54b8ee8',
        'final_cells': 33681,
        'allow_registered_archive_artifact_fallback': True,
    },
    'physical-workflow-f3635d8c43824df08ab01a01d0ebce8c': {
        'view_root': 'results/npu_layout_repaired_role_view',
        'source_root': 'results/npu_layout_repaired_source',
        'view_manifest_sha256': '186a150cca9d23ca2a540931177b8c932b1fbb8e91d84fbdfbaa0f6655eb6f39',
        'source_manifest_sha256': 'd5688568e77b2e5a2f37fa18dce99a7176c724793bba08283622c84694c08b5b',
        'final_cells': 64964,
    },
    'physical-workflow-7490fdd470a941c9b097033613816d72': {
        'view_root': 'results/npu2_layout_role_view_20261020',
        'source_root': 'results/npu2_layout_role_source_20261020',
        'view_manifest_sha256': 'dd5ae348d9b12babb8bcd38addc4c6b54e345d8c2a8074742d0fd6cc43a6f069',
        'source_manifest_sha256': '585e3139b9f130b9db57d96e6635daee99d09b1a4c2524fa179bdabe6568d102',
        'final_cells': 35193,
        'allow_registered_archive_artifact_fallback': True,
    },
}
FILES = {
    "functional-map-html": ("layout_roles.html", "text/html; charset=utf-8", "inline"),
    "functional-map-png": ("layout_roles.png", "image/png", "inline"),
    "functional-map-report": ("report.json", "application/json; charset=utf-8", "attachment"),
    "functional-map-data": ("layout_roles.json.gz", "application/gzip", "attachment"),
    "functional-map-manifest": ("manifest.json", "application/json; charset=utf-8", "attachment"),
}
FILE_IDS = frozenset(FILES)
_MUTABLE_REVIEW_FIELDS = {"record_hash", "review_status", "acceptance_epoch"}


def _require(condition, code="functional_map_integrity_error"):
    if not condition:
        raise DomainError(code, "The saved Functional Map could not be verified for this selected layout run.", 409)


def _raw_record_projection(run):
    return {key: value for key, value in run.items() if key not in _MUTABLE_REVIEW_FIELDS}


def snapshot_selected_run(manager, identifier):
    """No observe_design/envelope call: these GETs never persist source epochs.

    The caller holds manager.lock through verification. Current-stage freshness
    remains the existing workflow's responsibility, not this derived view.
    """
    raw = copy.deepcopy(manager._run(identifier))
    decorated = manager._decorate(raw)
    latest = manager._state["runs"][-1] if manager._state["runs"] else None
    latest_view = manager._decorate(latest) if latest else None
    accepted_id = (latest_view["id"] if latest_view and latest_view["review_status"] == "Accepted"
                   and latest_view["freshness"] == "Current" else None)
    status = {key: decorated.get(key) for key in ("execution_status", "validation_status", "review_status", "freshness")}
    return raw, {"status": status, "historical": raw["id"] != (latest or {}).get("id") or raw["id"] != accepted_id
                 or status["freshness"] != "Current" or status["review_status"] != "Accepted"}


def _read_below(root, relative):
    relative = PurePosixPath(relative)
    _require(not relative.is_absolute() and ".." not in relative.parts and "\\" not in str(relative))
    path = (root / Path(*relative.parts)).resolve()
    _require(path.is_relative_to(root.resolve()) and path.is_file())
    return path.read_bytes()


def _record(raw):
    return {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}


def _verified_file(root, relative, record):
    raw = _read_below(root, relative)
    _require(_record(raw) == record)
    return raw


def _registration(identifier):
    if identifier == RUN_ID:
        return {'view_root': VIEW_ROOT, 'source_root': SOURCE_ROOT,
                'view_manifest_sha256': VIEW_MANIFEST_SHA256,
                'source_manifest_sha256': SOURCE_MANIFEST_SHA256, 'final_cells': 66315}
    _require(identifier in ADDITIONAL_BUNDLES, 'functional_map_not_available')
    return ADDITIONAL_BUNDLES[identifier]


def _verified_bundle(project_root, run, registration=None, generation_id=None):
    root = Path(project_root).resolve()
    run_id = run['id']
    if generation_id is not None:
        from .layout_map_generation import read_registration_version
        registration = read_registration_version(root, run, generation_id)
    elif registration is None:
        # Dynamic publication is separate derived state. An invalid publication
        # must not be hidden by falling back to an older static registration.
        from .layout_map_generation import read_registration
        registration = read_registration(root, run)
    registered = registration if registration is not None else _registration(run_id)
    view_relative, source_relative = registered['view_root'], registered['source_root']
    view_hash, source_hash = registered['view_manifest_sha256'], registered['source_manifest_sha256']
    view_root = root / view_relative
    source_root = root / source_relative
    view_manifest_raw = _read_below(view_root, "manifest.json")
    source_manifest_raw = _read_below(source_root, "manifest.json")
    _require(hashlib.sha256(view_manifest_raw).hexdigest() == view_hash
             and hashlib.sha256(source_manifest_raw).hexdigest() == source_hash)
    manifest = strict_loads(view_manifest_raw.decode("utf-8"))
    source_manifest = strict_loads(source_manifest_raw.decode("utf-8"))
    expected_files = {value[0] for key, value in FILES.items() if key != "functional-map-manifest"}
    _require(manifest["kind"] == "derived_view_payload" and set(manifest["files"]) == expected_files
             and source_manifest["validation_status"] == "Passed" and source_manifest["layout_run_id"] == run_id)
    payloads = {name: _verified_file(view_root, name, manifest["files"][name]) for name in expected_files}
    payloads["manifest.json"] = view_manifest_raw
    archived = strict_loads(_verified_file(source_root, "layout_record.json", source_manifest["files"]["layout_record.json"]).decode("utf-8"))
    _require(archived["id"] == run_id and archived["execution_status"] == "Completed"
             and archived["validation_status"] == "Passed" and archived["review_status"] == "Accepted")
    _require(run.get("record_hash") == object_hash({key: value for key, value in run.items() if key != "record_hash"})
             and object_hash(_raw_record_projection(run)) == object_hash(_raw_record_projection(archived)), "functional_map_binding_mismatch")
    report = strict_loads(payloads["report.json"].decode("utf-8"))
    raw_map = gzip.decompress(payloads["layout_roles.json.gz"])
    _require(len(raw_map) == report["raw_map_bytes"] and hashlib.sha256(raw_map).hexdigest() == report["raw_map_sha256"])
    mapping = strict_loads(raw_map.decode("utf-8"))
    provenance = report["provenance"]
    _require(report["kind"] == "derived_read_only_visualization" and report["validation_status"] == "Passed"
             and mapping["layout_run_id"] == run_id and len(mapping["cells"]) == report["summary"]["final_cells"] == registered['final_cells']
             and mapping["summary"] == report["summary"] and mapping["provenance"] == provenance
             and provenance["archive_manifest"] == {"path": source_relative + "/manifest.json", "sha256": source_hash})
    inputs = list(provenance["inputs"].values()) + list(provenance["source_rtl"].values())
    inputs += [entry for entry in provenance["viewer_sources"] if entry["path"].startswith(source_relative + "/")]
    for entry in inputs:
        prefix = source_relative + "/"
        _require(entry["path"].startswith(prefix))
        relative = entry["path"][len(prefix):]
        expected = {"bytes": entry["bytes"], "sha256": entry["sha256"]}
        _require(source_manifest["files"].get(relative) == expected)
        _verified_file(source_root, relative, expected)
    artifact_inputs = {
        "gds": next(entry for entry in provenance["viewer_sources"] if entry["path"].endswith(".gds")),
        "def": provenance["inputs"]["final_def"],
        "netlist": provenance["inputs"]["final_verilog"],
    }
    artifact_verification = "retained_result_files"
    for identifier, expected in artifact_inputs.items():
        entries = [entry for entry in run["checks"]["artifacts"] if entry["id"] == identifier]
        _require(len(entries) == 1 and entries[0]["sha256"] == expected["sha256"] and entries[0]["bytes"] == expected["bytes"],
                 "functional_map_binding_mismatch")
        # Also verify the original retained run files, not only its declarations.
        try:
            original = _artifact_path(run["checks"], entries[0]).read_bytes()
        except DomainError as error:
            if (error.code != "physical_artifact_missing"
                    or not registered.get("allow_registered_archive_artifact_fallback")):
                raise
            relative = expected["path"][len(source_relative) + 1:]
            original = _verified_file(source_root, relative,
                                      {"bytes": expected["bytes"], "sha256": expected["sha256"]})
            artifact_verification = "registered_source_archive_fallback"
        except OSError:
            if not registered.get("allow_registered_archive_artifact_fallback"):
                raise
            relative = expected["path"][len(source_relative) + 1:]
            original = _verified_file(source_root, relative,
                                      {"bytes": expected["bytes"], "sha256": expected["sha256"]})
            artifact_verification = "registered_source_archive_fallback"
        _require(_record(original) == {"bytes": expected["bytes"], "sha256": expected["sha256"]})
    binding = {"layout_run_id": run_id, "revision_id": run["revision_id"], "source_manifest_sha256": run["source_manifest_sha256"],
               "gds_sha256": artifact_inputs["gds"]["sha256"], "def_sha256": artifact_inputs["def"]["sha256"],
               "netlist_sha256": artifact_inputs["netlist"]["sha256"], "archive_manifest_sha256": source_hash,
               "view_manifest_sha256": view_hash, "artifact_verification": artifact_verification}
    if registered.get("job_id"):
        binding["registration_job_id"] = registered["job_id"]
    return payloads, binding


def _bundle(project_root, run, generation_id=None):
    try:
        return _verified_bundle(project_root, run, generation_id=generation_id)
    except DomainError:
        raise
    except (OSError, ValueError, KeyError, TypeError, StopIteration) as error:
        raise DomainError("functional_map_integrity_error", "The saved Functional Map could not be verified for this selected layout run.", 409) from error


def verify_registration(project_root, run, registration):
    """Verify a candidate in full before publishing its separate registration."""
    try:
        _, binding = _verified_bundle(project_root, run, registration)
        return binding
    except DomainError:
        raise
    except (OSError, ValueError, KeyError, TypeError, StopIteration) as error:
        raise DomainError("functional_map_integrity_error", "The generated Functional Map failed its final source binding check.", 409) from error


def functional_map_metadata(project_root, run, display, generation_id=None):
    result = {"available": False, "run_id": run["id"], "html_url": None, "png_url": None, "report_url": None,
              "reason": None, "status": display["status"], "historical": display["historical"], "source_binding": None,
              "status_scope": "recorded_physical_workflow_state"}
    try:
        _, binding = _bundle(project_root, run, generation_id=generation_id)
    except DomainError as error:
        result["reason"] = {"code": error.code, "message": error.message}
        return result
    prefix = "/api/artifacts/physical-workflow/" + run["id"] + "/functional-map-"
    suffix = "?map_generation=" + binding["registration_job_id"] if binding.get("registration_job_id") else ""
    result.update(available=True, html_url=prefix + "html" + suffix, png_url=prefix + "png" + suffix,
                  report_url=prefix + "report" + suffix, source_binding=binding)
    return result


def functional_map_bytes(project_root, run, artifact_id, generation_id=None):
    if artifact_id not in FILE_IDS:
        raise DomainError("artifact_not_found", "This Functional Map artifact does not exist.", 404)
    payloads, _ = _bundle(project_root, run, generation_id)
    name, mime, disposition = FILES[artifact_id]
    return payloads[name], mime, disposition, name


def functional_map_csp(html):
    """Allow only this immutable page's exact inline code, with no connections."""
    scripts = re.findall(rb"<script\b([^>]*)>(.*?)</script\s*>", html, re.S | re.I)
    executable = [body for attributes, body in scripts if not re.search(rb"\btype\s*=", attributes, re.I)]
    _require(len(executable) == 1)
    digest = base64.b64encode(hashlib.sha256(executable[0]).digest()).decode("ascii")
    return ("default-src 'none'; script-src 'sha256-" + digest + "'; style-src 'unsafe-inline'; img-src data:; "
            "connect-src 'none'; frame-ancestors 'self'; base-uri 'none'; form-action 'none'; object-src 'none'")
