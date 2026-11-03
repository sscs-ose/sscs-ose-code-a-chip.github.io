"""GUI-triggered, append-only generation of derived Functional Map views.

This service never starts EDA or a model and never writes a project store.  A
worker captures already retained inputs, renders an isolated view and publishes
its immutable registration only after the server rechecks its exact S11 source.
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import os
from pathlib import Path, PurePosixPath
import re
import tempfile
import threading
import uuid

from .domain import DomainError
from .store import strict_loads, utc_now
from .verification import object_hash


_MUTABLE = frozenset(("record_hash", "review_status", "acceptance_epoch"))
_ACTIVE = frozenset(("Queued", "Running"))
_TERMINAL = frozenset(("Completed", "Failed", "Interrupted"))
_HEX = re.compile(r"[0-9a-f]{64}\Z")
_JOB = re.compile(r"functional-map-[0-9a-f]{32}\Z")
_SCOPE = frozenset(("project_id", "system_id"))


def _require(condition, message, code="functional_map_generation_integrity_error"):
    if not condition:
        raise DomainError(code, message, 409)


def immutable_projection(run):
    """The same immutable physical record projection as the read-only viewer."""
    return {key: value for key, value in run.items() if key not in _MUTABLE}


def projection_hash(run):
    return object_hash(immutable_projection(run))


def _checked_run(run):
    _require(type(run) is dict and type(run.get("id")) is str and bool(run["id"])
             and type(run.get("revision_id")) is str and bool(run["revision_id"])
             and type(run.get("source_manifest_sha256")) is str
             and bool(_HEX.fullmatch(run["source_manifest_sha256"])),
             "The selected layout record is malformed.")
    _require(run.get("record_hash") == object_hash({key: value for key, value in run.items() if key != "record_hash"}),
             "The selected layout record checksum is invalid.")


def _scope(value):
    _require(type(value) is dict and set(value) == _SCOPE
             and all(type(item) is str and bool(item.strip()) for item in value.values()),
             "A Functional Map job requires an exact project and system identity.")
    return copy.deepcopy(value)


def _binding(run):
    return {"layout_run_id": run["id"], "revision_id": run["revision_id"],
            "physical_source_manifest_sha256": run["source_manifest_sha256"],
            "physical_record_projection_sha256": projection_hash(run)}


def _sealed(value):
    result = copy.deepcopy(value)
    result["record_hash"] = object_hash(result)
    return result


def _validated_record(raw):
    value = strict_loads(raw.decode("utf-8"))
    _require(type(value) is dict and value.get("record_hash") == object_hash(
        {key: item for key, item in value.items() if key != "record_hash"}),
        "A saved Functional Map record has an invalid checksum.")
    return value


def _below(root, relative):
    _require(type(relative) is str, "A Functional Map path is malformed.")
    path = PurePosixPath(relative)
    _require(not path.is_absolute() and bool(path.parts) and ".." not in path.parts
             and "\\" not in relative and ":" not in relative,
             "Functional Map files must remain inside HuLLCirq.")
    resolved = (root / Path(*path.parts)).resolve()
    _require(resolved.is_relative_to(root.resolve()), "Functional Map files must remain inside HuLLCirq.")
    return resolved


def _storage(root):
    return _below(root, ".work/functional_maps")


def _read_saved(root, path):
    _require(path.resolve().is_relative_to(root.resolve()) and path.is_file(),
             "A saved Functional Map file is missing or outside HuLLCirq.")
    return path.read_bytes()


def _write_json(root, path, value, *, pointer=False):
    """Publish complete JSON atomically; only the derived pointer is replaceable."""
    import json

    _require(not path.is_symlink(), "A Functional Map output cannot replace a symbolic link.")
    path = path.parent.resolve() / path.name
    _require(path.is_relative_to(root.resolve()), "Functional Map files must remain inside HuLLCirq.")
    path.parent.mkdir(parents=True, exist_ok=True)
    _require(path.parent.resolve().is_relative_to(root.resolve()), "Unsafe Functional Map directory.")
    raw = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")
    descriptor, temporary_name = tempfile.mkstemp(prefix=".functional-map-", suffix=".tmp", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        # Unlike replace/rename, link has an atomic, no-overwrite contract on
        # both Windows NTFS and POSIX. The temporary inode is fully written.
        if pointer:
            os.replace(temporary, path)
        else:
            os.link(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _write_new(root, path, value):
    _write_json(root, path, value)


def _registration_path(root, run):
    return _storage(root) / "registrations" / (projection_hash(run) + ".json")


def _validate_registration(root, run, registration):
    _checked_run(run)
    _require(registration.get("kind") == "functional_map_registration"
             and registration.get("schema_version") == "1"
             and registration.get("binding") == _binding(run),
             "The generated Functional Map registration belongs to a different layout.",
             "functional_map_binding_mismatch")
    _scope(registration.get("scope_identity"))
    _require(type(registration.get("job_id")) is str and bool(_JOB.fullmatch(registration["job_id"]))
             and type(registration.get("registered_at")) is str
             and type(registration.get("final_cells")) is int and registration["final_cells"] > 0
             and registration.get("allow_registered_archive_artifact_fallback") is True,
             "The generated Functional Map registration is malformed.")
    suffix = registration["job_id"].removeprefix("functional-map-")
    _require(registration.get("source_root") == "results/fm-source-" + suffix
             and registration.get("view_root") == "results/fm-view-" + suffix,
             "Generated Functional Map output does not match its recorded job.")
    for key in ("view_root", "source_root"):
        path = _below(root, registration.get(key))
        _require(path.parent == (root / "results").resolve(), "Generated Functional Map output is outside results.")
    for key in ("view_manifest_sha256", "source_manifest_sha256"):
        _require(type(registration.get(key)) is str and bool(_HEX.fullmatch(registration[key])),
                 "A generated Functional Map manifest checksum is malformed.")
    _require(registration.get("record_hash") == object_hash(
        {key: value for key, value in registration.items() if key != "record_hash"}),
        "The generated Functional Map registration checksum is invalid.")
    return registration


def read_registration(root, run):
    """Read the exact dynamic registration; corrupt files fail closed.

    Absence alone returns None. Callers must not fall back to another run or a
    static registration after a present but invalid dynamic registration.
    Full source/view payload verification remains the viewer's responsibility.
    """
    root = Path(root).resolve()
    _require(type(run) is dict, "The selected layout record is malformed.")
    path = _registration_path(root, run)
    if not path.exists() and not path.is_symlink():
        return None
    try:
        pointer_raw = _read_saved(root, path)
        registration = _validate_registration(root, run, _validated_record(pointer_raw))
        version = path.parent / projection_hash(run) / (registration["job_id"] + ".json")
        _require(_read_saved(root, version) == pointer_raw, "The Functional Map pointer differs from its immutable registration version.")
        return registration
    except DomainError:
        raise
    except (OSError, ValueError, TypeError, KeyError) as error:
        raise DomainError("functional_map_generation_integrity_error",
                          "The generated Functional Map registration could not be verified.", 409) from error


def read_registration_version(root, run, job_id):
    """Read an immutable publication without consulting the mutable pointer.

    The metadata and all artifact requests can pin this job ID, so a later GUI
    generation cannot replace the bytes behind an already displayed binding.
    Unknown or invalid versions never fall back to the current or static map.
    """
    root = Path(root).resolve()
    _checked_run(run)
    _require(type(job_id) is str and bool(_JOB.fullmatch(job_id)),
             "The Functional Map publication ID is invalid.")
    path = _storage(root) / "registrations" / projection_hash(run) / (job_id + ".json")
    if not path.exists() and not path.is_symlink():
        raise DomainError("functional_map_not_available",
                          "No Functional Map publication is bound to this selected layout and generation ID.", 409)
    try:
        registration = _validate_registration(root, run, _validated_record(_read_saved(root, path)))
        _require(registration["job_id"] == job_id,
                 "The Functional Map publication does not match the requested generation ID.",
                 "functional_map_binding_mismatch")
        return registration
    except DomainError:
        raise
    except (OSError, ValueError, TypeError, KeyError) as error:
        raise DomainError("functional_map_generation_integrity_error",
                          "The immutable Functional Map publication could not be verified.", 409) from error


class FunctionalMapGeneration:
    """One explicitly started derived job at a time, across all GUI contexts.

    recheck is a server-owned, read-only source/context check. It is mandatory:
    a raw request snapshot alone cannot establish that a project stayed active.
    verify(root, run, candidate) must validate the complete source/view bundle.
    Dependencies are injectable solely for isolated software QA.
    """

    def __init__(self, root, *, capture=None, render=None, verify=None, recheck=None):
        if recheck is None:
            raise ValueError("Functional Map generation requires a server source recheck")
        self.root = Path(root).resolve()
        self.lock = threading.RLock()
        self._capture = capture
        self._render = render
        self._verify = verify
        self._recheck = recheck
        self._jobs = {}
        self._active_id = None
        self._thread = None
        self._closing = threading.Event()
        self._load_jobs()

    def _load_jobs(self):
        directory = _storage(self.root) / "jobs"
        if not directory.exists():
            return
        for path in sorted(directory.glob("*.json")):
            _require(bool(_JOB.fullmatch(path.stem)), "An unexpected Functional Map job record was found.")
            record = _validated_record(_read_saved(self.root, path))
            self._validate_job(record, path.stem, 0, None)
            event_directory = directory / path.stem
            if event_directory.exists():
                events = sorted(event_directory.glob("*.json"))
                for index, event in enumerate(events, 1):
                    _require(event.name == f"{index:06d}.json", "Functional Map job event history has a gap.")
                    following = _validated_record(_read_saved(self.root, event))
                    self._validate_job(following, path.stem, index, record)
                    record = following
            self._jobs[record["id"]] = record
    def _record_interruptions(self):
        """Called only by explicit start, never constructor/GET observation."""
        for record in list(self._jobs.values()):
            if record["status"] in _ACTIVE:
                self._append(record["id"], status="Interrupted", phase="Interrupted", finished_at=utc_now(),
                             error={"code": "functional_map_service_restarted",
                                    "message": "The GUI service restarted before this view job completed. Retry explicitly; no EDA or model was started."})

    @staticmethod
    def _validate_job(record, identifier, index, previous):
        _require(record.get("kind") == "functional_map_generation_job" and record.get("schema_version") == "1"
                 and record.get("id") == identifier and type(record.get("event_index")) is int and record["event_index"] == index
                 and record.get("status") in _ACTIVE | _TERMINAL
                 and type(record.get("binding")) is dict and type(record.get("created_at")) is str,
                 "A saved Functional Map job is malformed.")
        binding = record["binding"]
        suffix = identifier.removeprefix("functional-map-")
        _require(set(binding) == {"layout_run_id", "revision_id", "physical_source_manifest_sha256", "physical_record_projection_sha256"}
                 and record.get("layout_run_id") == binding["layout_run_id"]
                 and all(type(binding.get(key)) is str and bool(binding[key]) for key in binding)
                 and all(bool(_HEX.fullmatch(binding[key])) for key in
                         ("physical_source_manifest_sha256", "physical_record_projection_sha256"))
                 and type(record.get("expected_record_hash")) is str and bool(_HEX.fullmatch(record["expected_record_hash"]))
                 and record.get("source_root") == "results/fm-source-" + suffix
                 and record.get("view_root") == "results/fm-view-" + suffix,
                 "A saved Functional Map job has an invalid source binding.")
        _scope(record.get("scope_identity"))
        if previous is None:
            _require(record.get("previous_record_hash") is None and record["status"] == "Queued",
                     "The initial Functional Map job record is malformed.")
        else:
            _require(previous["status"] not in _TERMINAL
                     and record.get("previous_record_hash") == previous["record_hash"]
                     and all(record.get(key) == previous.get(key) for key in
                             ("id", "layout_run_id", "binding", "scope_identity", "created_at", "expected_record_hash", "source_root", "view_root")),
                     "A saved Functional Map job event changed its immutable source or completed history.")

    def _append(self, identifier, **changes):
        previous = self._jobs[identifier]
        _require(previous["status"] in _ACTIVE, "A completed Functional Map job cannot be changed.")
        following = {key: value for key, value in previous.items() if key != "record_hash"}
        following.update(changes, event_index=previous["event_index"] + 1,
                         previous_record_hash=previous["record_hash"], updated_at=utc_now())
        following = _sealed(following)
        self._validate_job(following, identifier, following["event_index"], previous)
        path = _storage(self.root) / "jobs" / identifier / f"{following['event_index']:06d}.json"
        _write_new(self.root, path, following)
        self._jobs[identifier] = following
        return copy.deepcopy(following)

    def is_active(self):
        with self.lock:
            return self._active_id is not None

    def close(self):
        """Stop at the next pure-software phase boundary; never publish on exit."""
        with self.lock:
            self._closing.set()
            thread = self._thread
        if thread is not None and thread is not threading.current_thread() and thread.is_alive():
            thread.join(1)

    def _ensure_open(self):
        _require(not self._closing.is_set(), "The GUI service closed before this derived view completed. Retry explicitly.",
                 "functional_map_service_closed")

    def start(self, run, expected_record_hash, scope_identity):
        run = copy.deepcopy(run)
        _checked_run(run)
        scope_identity = _scope(scope_identity)
        _require(expected_record_hash == run["record_hash"],
                 "The selected layout changed. Refresh it before generating a Functional Map.", "functional_map_source_changed")
        _require(run.get("execution_status") == "Completed" and run.get("validation_status") == "Passed"
                 and run.get("review_status") == "Accepted",
                 "Generate a Functional Map only from a completed, passed and accepted layout.", "functional_map_source_not_eligible")
        with self.lock:
            self._ensure_open()
            _require(self._active_id is None, "A Functional Map view job is already running. Wait for its saved result.",
                     "functional_map_generation_active")
            _require(self._recheck(run, scope_identity) is True,
                     "The active project or selected layout changed. Refresh before retrying.", "functional_map_source_changed")
            self._record_interruptions()
            identifier = "functional-map-" + uuid.uuid4().hex
            now = utc_now()
            suffix = identifier.removeprefix("functional-map-")
            job = _sealed({"kind": "functional_map_generation_job", "schema_version": "1", "id": identifier,
                           "layout_run_id": run["id"],
                           "event_index": 0, "previous_record_hash": None,
                           "scope_identity": scope_identity, "binding": _binding(run),
                           "expected_record_hash": expected_record_hash,
                           "status": "Queued", "phase": "Queued", "created_at": now, "updated_at": now,
                           "started_at": None, "finished_at": None, "error": None, "registration": None,
                           "source_root": "results/fm-source-" + suffix,
                           "view_root": "results/fm-view-" + suffix,
                           "additional_eda_model_or_simulation_runs": 0})
            _write_new(self.root, _storage(self.root) / "jobs" / (identifier + ".json"), job)
            self._jobs[identifier] = job
            self._active_id = identifier
            self._thread = threading.Thread(target=self._work, args=(identifier, run), daemon=True,
                                            name=identifier)
            try:
                self._thread.start()
            except Exception:
                self._append(identifier, status="Failed", phase="Failed", finished_at=utc_now(),
                             error={"code": "functional_map_worker_unavailable", "message": "The derived view worker could not start. Retry explicitly."})
                self._active_id = None
                raise
            return copy.deepcopy(job)

    def status(self, run, scope_identity=None):
        _checked_run(run)
        scope = _scope(scope_identity) if scope_identity is not None else None
        binding = _binding(run)
        with self.lock:
            jobs = [self._job_view(job) for job in self._jobs.values()
                    if job["binding"] == binding and (scope is None or job["scope_identity"] == scope)]
            jobs.sort(key=lambda job: (job["created_at"], job["id"]))
        registration = read_registration(self.root, run)
        if registration is not None and scope is not None:
            _require(registration["scope_identity"] == scope,
                     "The generated Functional Map belongs to a different project or system.", "functional_map_binding_mismatch")
        return {"jobs": jobs, "latest_job": jobs[-1] if jobs else None, "registration": registration,
                "additional_eda_model_or_simulation_runs": 0}

    def _job_view(self, record):
        result = copy.deepcopy(record)
        if record["status"] in _ACTIVE and record["id"] != self._active_id:
            # An unowned persisted attempt cannot resume from a GET or silently
            # rerun. This is a display projection, not a rewritten raw record.
            result.update(status="Interrupted", phase="Interrupted", recorded_status=record["status"],
                          recovery_required=True, status_scope="recovered_service_view",
                          persisted_record_hash=result.pop("record_hash"),
                          error={"code": "functional_map_service_restarted",
                                 "message": "The GUI service restarted before this view job completed. Retry explicitly; no EDA or model was started."})
        return result

    def _capture_source(self, run, output):
        if self._capture is not None:
            return self._capture(self.root, run, output)
        from .layout_map_source import capture_source
        return capture_source(self.root, run, output)

    def _render_view(self, selected, output):
        if self._render is not None:
            return self._render(self.root, selected, output)
        path = self.root / "scripts/render_layout_roles.py"
        spec = importlib.util.spec_from_file_location("hullcirq_gui_map_renderer", path)
        _require(spec is not None and spec.loader is not None, "The Functional Map renderer is unavailable.")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.render_layout_roles(self.root, selected, output)

    def _verify_bundle(self, run, registration):
        if self._verify is not None:
            _require(self._verify(self.root, run, registration) is not False,
                     "The generated Functional Map bundle failed verification.")
        else:
            from .layout_role_view import verify_registration
            verify_registration(self.root, run, registration)

    def _work(self, identifier, run):
        try:
            self._ensure_open()
            with self.lock:
                job = self._append(identifier, status="Running", phase="Capture", started_at=utc_now())
            source = _below(self.root, job["source_root"])
            view = _below(self.root, job["view_root"])
            _require(not source.exists() and not view.exists(), "This derived output already exists; preserve it and start a separate attempt.")
            selected = self._capture_source(run, source)
            self._ensure_open()
            with self.lock:
                context = selected.get("role_context")
                metadata = ({"source_profile": selected["role_profile"],
                             "definition_count": len(context["definitions"]),
                             "instance_role_count": len(context["instances"]),
                             "annotation_scope": "saved_artifact_bound_not_circuit_qualification"}
                            if type(context) is dict else {})
                self._append(identifier, phase="Render", **metadata)
            self._render_view(selected, view)
            self._ensure_open()
            with self.lock:
                self._append(identifier, phase="Register")
            source_manifest = (source / "manifest.json").read_bytes()
            view_manifest = (view / "manifest.json").read_bytes()
            report = strict_loads((view / "report.json").read_text(encoding="utf-8"))
            registration = _sealed({"kind": "functional_map_registration", "schema_version": "1",
                                    "job_id": identifier, "scope_identity": job["scope_identity"],
                                    "binding": job["binding"], "registered_at": utc_now(),
                                    "source_root": job["source_root"], "view_root": job["view_root"],
                                    "source_manifest_sha256": hashlib.sha256(source_manifest).hexdigest(),
                                    "view_manifest_sha256": hashlib.sha256(view_manifest).hexdigest(),
                                    "final_cells": report["summary"]["final_cells"],
                                    "allow_registered_archive_artifact_fallback": True})
            _validate_registration(self.root, run, registration)
            self._verify_bundle(run, registration)
            self._ensure_open()
            _require(self._recheck(run, job["scope_identity"]) is True,
                     "The project or source changed while the view was being generated. The derived files were retained but not registered.",
                     "functional_map_source_changed")
            with self.lock:
                self._ensure_open()
                previous = read_registration(self.root, run)
                if previous is not None:
                    _require(previous["scope_identity"] == job["scope_identity"], "A registration belongs to another project or system.")
                    self._verify_bundle(run, previous)
                # Every generated registration has an immutable version. Only
                # the derived current pointer changes; successful job events
                # also retain the complete version they published.
                version = _storage(self.root) / "registrations" / projection_hash(run) / (identifier + ".json")
                _write_new(self.root, version, registration)
                _write_json(self.root, _registration_path(self.root, run), registration, pointer=True)
                published = read_registration(self.root, run)
                self._append(identifier, status="Completed", phase="Completed", finished_at=utc_now(),
                             registration=published, error=None)
        except Exception as error:
            code = error.code if isinstance(error, DomainError) else "functional_map_generation_failed"
            message = error.message if isinstance(error, DomainError) else str(error)
            with self.lock:
                current = self._jobs.get(identifier)
                if current is not None and current["status"] in _ACTIVE:
                    terminal = "Interrupted" if code == "functional_map_service_closed" else "Failed"
                    self._append(identifier, status=terminal, phase=terminal, finished_at=utc_now(),
                                 error={"code": code, "message": message or "The derived view could not be generated. Prior results were preserved."})
        finally:
            with self.lock:
                if self._active_id == identifier:
                    self._active_id = None
