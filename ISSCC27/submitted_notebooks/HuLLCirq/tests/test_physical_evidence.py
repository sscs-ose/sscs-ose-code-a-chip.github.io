"""Isolated SOFTWARE QA for S11 collection; no actual physical proof or EDA.

All generated files and records below are disposable rejection/byte-copy
fixtures. They never substitute for the original GUI design or tool results.
"""
from __future__ import annotations

import copy
import gzip
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT / "scripts"))

from collect_physical_proof import (PHYSICAL_HISTORY, SOURCE_HISTORIES, copy_artifacts,
    copy_attempt, copy_legacy_execution_sources, copy_retained_files, decode_physical_history, digest, export_logs, inspect_attempt_files, latest_adopted,
    load_baseline, require_real_origin, require_source_bytes, retained_files,
    terminal_history, validate_lineage, validate_revalidation_binding, verify_attempt_copies, verify_prior_payloads)
from hullcirq.domain import DomainError
from hullcirq.global_generation import NODE_IDS
from hullcirq.global_workflow import source_bundle
from hullcirq.physical_tools import fixed_commands
from hullcirq.physical_workflow import REQUIRED_FILES
from hullcirq.verification import _wsl_path, content_hash, object_hash, trusted_command


def software_lineage():
    """Explicit software fixture, not an executed circuit or tool run."""
    settings = {"top_module": "software_qa", "clock_period_ns": 50}
    plan = {"vector_hash": "qa-vector", "testbench_sha256": "qa-tb", "public_boundary_vector_hash": "qa-public",
            "recipe": {"source_job": {"k": 4, "relu": False}}}
    manifest = {"nodes": [{"node_id": "qa-node", "rtl": "module qa; endmodule\n"}]}
    job = {"id": "qa-S08", "revision_id": "qa-revision", "context_id": "qa-context", "rtl": "module software_qa; endmodule\n",
           "context": {"source_manifest": manifest, "verification_plan": plan}}
    job["rtl_sha256"] = content_hash(job["rtl"])
    synthesis = {"id": "qa-S09", "global_job_id": job["id"]}
    simulation = {"id": "qa-S10", "global_job_id": job["id"], "prior_run_id": synthesis["id"]}
    configuration = {"origin": "SOFTWARE_QA_ONLY", "core_utilization_percent": 35}
    run = {"id": "qa-S11", "stage_id": "layout", "revision_id": job["revision_id"], "global_job_id": job["id"],
        "synthesis_run_id": synthesis["id"], "netlist_run_id": simulation["id"], "global_context_id": job["context_id"],
        "global_rtl": job["rtl"], "global_rtl_sha256": job["rtl_sha256"], "source_manifest": copy.deepcopy(manifest),
        "source_manifest_sha256": object_hash(manifest), "verification_plan": copy.deepcopy(plan), "verification_plan_sha256": object_hash(plan),
        **{key: plan[key] for key in ("vector_hash", "testbench_sha256", "public_boundary_vector_hash")},
        "settings": copy.deepcopy(settings), "settings_sha256": object_hash(settings), "runtime_configuration": configuration,
        "runtime_configuration_sha256": object_hash(configuration), "evidence_kind": "software_qa_fixture", "checks": {"software_qa_fixture": True}}
    baseline = {"revision_id": job["revision_id"], "original_settings": settings}
    return run, synthesis, simulation, job, baseline


def software_artifacts(folder):
    """Only checks collection mechanics, never layout semantics."""
    entries = []
    for identifier in sorted(REQUIRED_FILES):
        payload = b"SOFTWARE QA ONLY\r\n" + identifier.encode() + b"\x00\xff\n"
        path = Path(folder) / "fixtures" / identifier; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(payload)
        entries.append({"id": identifier, "kind": identifier, "relative_path": path.relative_to(folder).as_posix(),
            "sha256": digest(payload), "bytes": len(payload), "content_type": "application/octet-stream"})
    return {"software_qa_fixture": True, "artifacts_directory": str(Path(folder).resolve()), "artifacts": entries}


def software_failed_attempt(root, recipe="v1"):
    """Make disposable old-worker/parser-failure bytes, without running tools."""
    root = Path(root); folder = root / "runs/hullcirq-layout-software-qa"; folder.mkdir(parents=True)
    run, *_ = software_lineage()
    settings = {"top_module": "software_qa", "clock_name": "clk", "clock_period_ns": 50,
        "reset_name": "rst", "reset_kind": "synchronous", "reset_active": "high", "rtl_language": "verilog_2005"}
    nodes = [{"node_id": identifier, "module_name": "qa_" + identifier.replace("-", "_"),
        "rtl": "// SOFTWARE QA ONLY\nmodule qa_" + identifier.replace("-", "_") + "; endmodule\n"} for identifier in NODE_IDS]
    for node in nodes: node["rtl_sha256"] = content_hash(node["rtl"])
    manifest = {"design": {"settings": settings, "nodes": [{"id": node["node_id"]} for node in nodes]}, "nodes": nodes}
    sdc = b"# SOFTWARE QA ONLY\r\n"; pdk = b'{"SOFTWARE_QA_ONLY":true}\r\n'
    configuration = {"kind": "wsl", "distribution": "Ubuntu", "origin": "SOFTWARE_QA_ONLY",
        "executable": _wsl_path(root / "librelane-devshell-x86_64.AppImage"), "working_directory": str(folder.parent),
        "pdk_root": str(root / "pdks"), "profile": {"config": {"FP_CORE_UTIL": 35, "SOFTWARE_QA_ONLY": True}},
        "base_sdc_sha256": digest(sdc), "pdk_manifest_sha256": digest(pdk)}
    run.update(settings=settings, settings_sha256=object_hash(settings), source_manifest=manifest, source_manifest_sha256=object_hash(manifest),
        runtime_configuration=configuration, runtime_configuration_sha256=object_hash(configuration),
        execution_status="Failed", validation_status="Failed", review_status="Awaiting Review")
    bundle = source_bundle(run["global_rtl"], manifest)
    (folder / "candidate_top.v").write_bytes(run["global_rtl"].encode())
    for node in nodes: (folder / (node["node_id"] + ".v")).write_bytes(node["rtl"].encode())
    (folder / "physical.sdc").write_bytes(sdc); (folder / "pdk-input-manifest.json").write_bytes(pdk)
    config = {**configuration["profile"]["config"], "DESIGN_NAME": settings["top_module"],
        "VERILOG_FILES": ["dir::" + item["file"] for item in bundle], "CLOCK_PORT": "clk", "CLOCK_PERIOD": 50,
        "PNR_SDC_FILE": "dir::physical.sdc", "SIGNOFF_SDC_FILE": "dir::physical.sdc"}
    inputs = {"settings": settings, "runtime_configuration": configuration, "source_bundle": bundle,
        "source_manifest_sha256": run["source_manifest_sha256"], "global_rtl_sha256": run["global_rtl_sha256"]}
    for name, value in (("config.json", config), ("input-manifest.json", inputs)):
        (folder / name).write_bytes((json.dumps(value, indent=2) + "\r\n").encode())
    commands = []
    for index, command in enumerate(fixed_commands(configuration, folder, recipe)):
        logs = folder / ("version", "layout")[index]; logs.mkdir()
        worker = logs / "worker.py" if recipe == "v2" else ROOT / "scripts/physical_worker.py"
        if recipe == "v2": worker.write_bytes(b"# SOFTWARE QA ONLY; never executed\n")
        worker_hash = digest(worker.read_bytes()); argv = command[command.index("--exec") + 1:]
        request = {"version": "hullcirq-physical-worker-" + recipe, "argv": argv, "timeout_seconds": 120 if index == 0 else 7200}
        if recipe == "v2": request.update(cwd=_wsl_path(folder), worker_sha256=worker_hash)
        (logs / "request.json").write_bytes((json.dumps(request) + "\r\n").encode())
        exit_record = {"status": "Completed", "executed": True, "exit_code": 0, "argv": argv, "elapsed_seconds": 0.1}
        (logs / "process-result.json").write_bytes((json.dumps(exit_record) + "\n").encode())
        raw_stdout = b"SOFTWARE QA ONLY\r\ninvalid UTF8 retained: \xff\n"
        (logs / "stdout.log").write_bytes(raw_stdout); (logs / "stderr.log").write_bytes(b"fixture diagnostic\r\n")
        supervisor_args = [_wsl_path(worker), _wsl_path(logs / "request.json")]
        if recipe == "v2": supervisor_args += ["--request-sha256", digest((logs / "request.json").read_bytes()), "--worker-sha256", worker_hash]
        commands.append({**exit_record, "command": command, "worker_sha256": worker_hash,
            "request_sha256": digest((logs / "request.json").read_bytes()),
            "supervisor_command": trusted_command(configuration, "/usr/bin/python3", supervisor_args, folder),
            "stdout": (logs / "stdout.log").read_text(encoding="utf-8", errors="replace"),
            "stderr": (logs / "stderr.log").read_text(encoding="utf-8", errors="replace")})
    (folder / "state_out.json").write_bytes(b'{"SOFTWARE_QA_ONLY":true,"unused_slack":Infinity}\r\n')
    (folder / "excluded.odb").write_bytes(b"SOFTWARE QA heavy format placeholder")
    run["checks"] = {"software_qa_fixture": True, "adapter_recipe": recipe, "artifacts_directory": str(folder),
        "artifacts": [], "retained_files": [], "commands": commands, "source_bundle": bundle,
        **{key: run[key] for key in ("global_rtl_sha256", "source_manifest_sha256", "settings_sha256", "runtime_configuration_sha256")},
        "stdout": "".join(c["stdout"] for c in commands), "stderr": "".join(c["stderr"] for c in commands)}
    return run, folder


class PhysicalEvidenceTests(unittest.TestCase):
    def test_all_six_original_histories_are_exact_including_whitespace(self):
        original = {name: b'{"software_qa":"original"}\r\n' for name in SOURCE_HISTORIES}
        require_source_bytes(copy.deepcopy(original), original)
        for name in SOURCE_HISTORIES:
            changed = dict(original); changed[name] += b" "
            with self.subTest(name=name), self.assertRaises(ValueError): require_source_bytes(changed, original)
        with self.assertRaises(ValueError): require_source_bytes({k: v for k, v in original.items() if k != SOURCE_HISTORIES[-1]}, original)

    def test_baseline_rejects_modified_original_copy(self):
        with tempfile.TemporaryDirectory(prefix="physical-evidence-software-qa-") as name:
            folder = Path(name); originals = folder / "originals"; originals.mkdir()
            values = {file: b'{"SOFTWARE_QA_ONLY":true}\n' for file in SOURCE_HISTORIES}
            for file, raw in values.items(): (originals / file).write_bytes(raw)
            baseline = {"original_NPU_histories": {k: digest(v) for k, v in values.items()}, "preexisting_files": {},
                "revision_id": "qa-revision", "original_settings": {"clock_period_ns": 50}}
            path = folder / "baseline.json"; path.write_text(json.dumps(baseline), encoding="utf-8")
            self.assertEqual(load_baseline(path, originals)[2], values)
            (originals / SOURCE_HISTORIES[-1]).write_bytes(b"{}")
            with self.assertRaises(ValueError): load_baseline(path, originals)

    def test_prior_results_are_immutable_while_product_changes_are_allowed(self):
        with tempfile.TemporaryDirectory(prefix="physical-evidence-software-qa-") as name:
            root = Path(name); path = root / "results/prior/data.bin"; path.parent.mkdir(parents=True); path.write_bytes(b"SOFTWARE QA prior")
            baseline = {"preexisting_files": {"results/prior/data.bin": digest(path.read_bytes()), "src/evolving.py": "0" * 64}}
            self.assertEqual(len(verify_prior_payloads(baseline, root)), 1)
            path.write_bytes(b"modified")
            with self.assertRaises(ValueError): verify_prior_payloads(baseline, root)

    def test_latest_failed_stale_unadopted_run_cannot_fallback_to_old_pass(self):
        accepted = {"id": "qa-old", "stage_id": "layout", "execution_status": "Completed", "validation_status": "Passed",
                    "review_status": "Accepted", "freshness": "Current"}
        self.assertEqual(latest_adopted([accepted])["id"], "qa-old")
        for change in ({"freshness": "Stale"}, {"validation_status": "Failed"}, {"review_status": "Awaiting Review"}, {"execution_status": "Cancelled"}):
            with self.subTest(change=change), self.assertRaises(ValueError): latest_adopted([accepted, {**accepted, "id": "qa-latest", **change}])

    def test_active_or_empty_history_cannot_be_collected(self):
        for runs in ([], [{"execution_status": "Running"}], [{"execution_status": "Queued"}]):
            history = {"physical_workflow_store_version": "0.1", "runs": runs, "reviews": []}
            with self.subTest(runs=runs), self.assertRaises(ValueError): terminal_history(json.dumps(history).encode())

    def test_resigned_source_settings_plan_and_previous_id_substitutions_fail(self):
        run, synthesis, simulation, job, baseline = software_lineage(); validate_lineage(run, synthesis, simulation, job, baseline)
        mutations = (lambda r: r.update(synthesis_run_id="another-S09"), lambda r: r.update(netlist_run_id="another-S10"),
            lambda r: r["source_manifest"]["nodes"][0].update(rtl="module replacement; endmodule\n"),
            lambda r: r["verification_plan"]["recipe"]["source_job"].update(k=4.0), lambda r: r["settings"].update(clock_period_ns=50.0))
        for mutation in mutations:
            changed = copy.deepcopy(run); mutation(changed)
            for value, checksum in (("source_manifest", "source_manifest_sha256"), ("verification_plan", "verification_plan_sha256"), ("settings", "settings_sha256")):
                changed[checksum] = object_hash(changed[value])
            with self.subTest(mutation=mutation), self.assertRaises(ValueError): validate_lineage(changed, synthesis, simulation, job, baseline)

    def test_runtime_configuration_change_requires_its_exact_hash(self):
        run, synthesis, simulation, job, baseline = software_lineage(); run["runtime_configuration"]["core_utilization_percent"] = 40
        with self.assertRaises(ValueError): validate_lineage(run, synthesis, simulation, job, baseline)

    def test_software_QA_and_missing_profile_origin_are_never_actual_proof(self):
        run, *_ = software_lineage()
        with self.assertRaises(ValueError): require_real_origin(run)
        run["evidence_kind"] = "trusted_fixed_tool_execution"
        with self.assertRaises(ValueError): require_real_origin(run)
        run["checks"] = {}; run["runtime_configuration"].pop("origin")
        with self.assertRaises(ValueError): require_real_origin(run)

    def test_lossless_gzip_has_typed_bounds_and_exact_original_bytes(self):
        with tempfile.TemporaryDirectory(prefix="physical-evidence-software-qa-") as name:
            folder = Path(name); raw = b'{"SOFTWARE_QA_ONLY":true}\r\n'; compressed = gzip.compress(raw, mtime=0)
            path = folder / (PHYSICAL_HISTORY + ".gz"); path.write_bytes(compressed)
            meta = {"archive": path.name, "compression": "gzip", "archive_sha256": digest(compressed), "archive_bytes": len(compressed),
                "decompressed_sha256": digest(raw), "decompressed_bytes": len(raw)}
            self.assertEqual(decode_physical_history(folder, meta), raw)
            for fields in ({"archive_bytes": True}, {"decompressed_bytes": True}, {"decompressed_bytes": len(raw) - 1},
                    {"decompressed_sha256": "0" * 64}, {"archive": "../physical_workflow.json.gz"}):
                with self.subTest(fields=fields), self.assertRaises(ValueError): decode_physical_history(folder, {**meta, **fields})

    def test_binary_and_CRLF_artifacts_preserve_raw_bytes_and_original_paths(self):
        with tempfile.TemporaryDirectory(prefix="physical-evidence-software-qa-") as name:
            folder = Path(name); result = software_artifacts(folder / "original"); output = folder / "collected"
            exported = copy_artifacts(result, output)
            for identifier, entry in exported.items():
                self.assertEqual(Path(entry["source_path"]).read_bytes(), (output / entry["export_path"]).read_bytes())
                self.assertIn(b"\r\n", (output / entry["export_path"]).read_bytes())
            aliased = copy.deepcopy(result); aliased["artifacts"][0]["relative_path"] = aliased["artifacts"][0]["relative_path"].replace("fixtures/", "fixtures/./")
            with self.assertRaises(ValueError): copy_artifacts(aliased, folder / "aliased")
            source = Path(exported["gds"]["source_path"]); source.write_bytes(source.read_bytes() + b"altered")
            with self.assertRaises(DomainError): copy_artifacts(result, folder / "rejected")

    def test_retained_logs_reject_escape_duplicate_boolean_size_and_changed_raw_bytes(self):
        with tempfile.TemporaryDirectory(prefix="physical-evidence-software-qa-") as name:
            root = Path(name); path = root / "worker.log"; path.write_bytes(b"SOFTWARE QA\r\n")
            entry = {"relative_path": "worker.log", "sha256": digest(path.read_bytes()), "bytes": path.stat().st_size}
            result = {"artifacts_directory": str(root), "retained_files": [entry]}
            self.assertEqual(len(retained_files(result)), 1)
            for fields in ({"relative_path": "../outside"}, {"relative_path": "C:/outside"}, {"relative_path": "./worker.log"},
                    {"bytes": True}, {"sha256": "0" * 64}):
                with self.subTest(fields=fields), self.assertRaises(ValueError): retained_files({**result, "retained_files": [{**entry, **fields}]})
            with self.assertRaises(ValueError): retained_files({**result, "retained_files": [entry, entry]})
            output = root / "export"; copied = copy_retained_files(result, output)
            self.assertEqual((output / copied[0]["export_path"]).read_bytes(), path.read_bytes())
            path.write_bytes(b"resigned")
            with self.assertRaises(ValueError): retained_files(result)

    def test_full_retained_stdout_stderr_strings_have_no_newline_conversion(self):
        with tempfile.TemporaryDirectory(prefix="physical-evidence-software-qa-") as name:
            result = {"stdout": "SOFTWARE QA\r\n", "stderr": "", "commands": [{"stdout": "command\r\n", "stderr": "error\n"}]}
            export_logs(result, name)
            self.assertEqual((Path(name) / "logs/adapter_stdout.txt").read_bytes(), b"SOFTWARE QA\r\n")
            self.assertEqual((Path(name) / "logs/command_00_stdout.txt").read_bytes(), b"command\r\n")

    def test_failed_legacy_attempt_keeps_raw_inputs_worker_exit_logs_and_nonstandard_tool_JSON(self):
        with tempfile.TemporaryDirectory(prefix="physical-attempt-software-qa-") as name:
            root = Path(name); run, folder = software_failed_attempt(root); original = copy.deepcopy(run)
            output = root / "collected"; report = copy_attempt(run, output)
            self.assertEqual(run, original)
            self.assertEqual(report["execution_status"], "Failed"); self.assertEqual(report["review_status"], "Awaiting Review")
            self.assertEqual(report["scope"], "diagnostic_preservation_only_no_rerun_or_new_adoption")
            self.assertEqual(report["record_object_sha256"], object_hash(original))
            self.assertEqual(json.loads((output / "attempts/qa-S11/run_record.json").read_text(encoding="utf-8")), original)
            copied = {entry["relative_path"]: entry for entry in report["files"]}
            for required in ("candidate_top.v", "node-buffer.v", "config.json", "physical.sdc", "input-manifest.json",
                    "layout/request.json", "layout/process-result.json", "layout/stdout.log", "layout/stderr.log", "state_out.json"):
                entry = copied[required]; self.assertEqual(entry["origin_run_id"], run["id"])
                self.assertEqual((output / entry["export_path"]).read_bytes(), (folder / required).read_bytes())
            self.assertIn(b"\r\n", (output / copied["layout/stdout.log"]["export_path"]).read_bytes())
            self.assertIn(b"\xff", (output / copied["layout/stdout.log"]["export_path"]).read_bytes())
            self.assertIn(b"Infinity", (output / copied["state_out.json"]["export_path"]).read_bytes())
            self.assertNotIn("excluded.odb", copied)
            self.assertEqual(report["external_sources"][0]["origin_run_id"], run["id"])
            verify_attempt_copies([report])
            (folder / "state_out.json").write_bytes(b"modified after inventory")
            with self.assertRaises(ValueError): verify_attempt_copies([report])

    def test_historical_inputs_requests_exit_and_raw_log_mismatches_are_rejected(self):
        for relative, mutation in (("candidate_top.v", b"replacement RTL"), ("config.json", b"{}"),
                ("physical.sdc", b"replacement SDC"), ("layout/request.json", b"{}"),
                ("layout/process-result.json", b'{"exit_code":19}'), ("layout/stdout.log", b"replacement log")):
            with self.subTest(relative=relative), tempfile.TemporaryDirectory(prefix="physical-attempt-software-qa-") as name:
                run, folder = software_failed_attempt(name); (folder / relative).write_bytes(mutation)
                with self.assertRaises((ValueError, DomainError)): inspect_attempt_files(run)

    def test_old_profile_is_preserved_and_v2_frozen_supervisor_is_bound_without_execution(self):
        with tempfile.TemporaryDirectory(prefix="physical-attempt-software-qa-") as name:
            run, folder = software_failed_attempt(name, "v2")
            # This old software profile deliberately differs from today's real profile.
            inventory = inspect_attempt_files(run)
            copied = {entry["relative_path"]: entry for entry in inventory["files"]}
            self.assertEqual(copied["layout/worker.py"]["original_recorded_raw_sha256"], run["checks"]["commands"][1]["worker_sha256"])
            self.assertFalse(inventory["external_sources"])
            (folder / "layout/worker.py").write_bytes(b"replacement worker")
            with self.assertRaises(ValueError): inspect_attempt_files(run)

    def test_shared_original_layout_bytes_and_legacy_sources_have_explicit_collection_origins(self):
        with tempfile.TemporaryDirectory(prefix="physical-attempt-software-qa-") as name:
            root = Path(name); run, folder = software_failed_attempt(root); output = root / "collected"
            payload = b"SOFTWARE QA binary sharing only\x00\xff"
            source = folder / "partial.gds"; source.write_bytes(payload)
            shared = output / "artifacts/original.gds"; shared.parent.mkdir(parents=True); shared.write_bytes(payload)
            entries = [{"source_path": str(source), "sha256": digest(payload), "bytes": len(payload), "export_path": "artifacts/original.gds"}]
            entries += copy_legacy_execution_sources(run, output)
            report = copy_attempt(run, output, shared_files=entries)
            partial = next(e for e in report["files"] if e["relative_path"] == "partial.gds")
            self.assertEqual(partial["export_path"], "artifacts/original.gds")
            self.assertEqual(partial["origin_run_id"], run["id"])
            self.assertFalse((output / "attempts/qa-S11/working_files/partial.gds").exists())
            self.assertTrue(all(e["copy_origin"] == "collection_time_copy_of_immutable_legacy_source" and e["pre_execution_snapshot"] is False for e in entries[1:]))
            self.assertEqual(report["external_sources"][0]["export_path"], "execution_sources/physical_worker.py")

    def test_attempt_paths_missing_directories_and_required_byte_bounds_reject_silent_loss(self):
        with tempfile.TemporaryDirectory(prefix="physical-attempt-software-qa-") as name:
            run, folder = software_failed_attempt(name)
            escaped = copy.deepcopy(run); escaped["checks"]["artifacts_directory"] = str(folder.parent.parent)
            with self.assertRaises(ValueError): inspect_attempt_files(escaped)
            with patch("collect_physical_proof.ATTEMPT_FILE_BYTES", 8), self.assertRaises(ValueError): inspect_attempt_files(run)
            (folder / "config.json").unlink()
            with self.assertRaises(ValueError): inspect_attempt_files(run)
        run, *_ = software_lineage()
        run.update(execution_status="Cancelled", validation_status="Not Checked", review_status="Awaiting Review")
        run["checks"] = {}
        self.assertIsNotNone(inspect_attempt_files(run)["unavailable_reason"])
        run["checks"]["executed"] = True
        with self.assertRaises(ValueError): inspect_attempt_files(run)

    def test_saved_output_revalidation_binds_original_failed_record_and_never_counts_new_tool_starts(self):
        with tempfile.TemporaryDirectory(prefix="physical-attempt-software-qa-") as name:
            # Pure contract fixture: no actual proof/adapter or tool is invoked.
            prior, _ = software_failed_attempt(name)
            prior["evidence_kind"] = "trusted_fixed_tool_execution"
            prior["checks"].pop("software_qa_fixture")
            prior["checks"].update(executed=True, exit_code=0)
            prior["record_hash"] = object_hash(prior)
            run = copy.deepcopy(prior)
            run.update(id="qa-S11-revalidation", execution_status="Completed", validation_status="Passed", review_status="Accepted",
                evidence_kind="trusted_saved_tool_revalidation", execution_kind="saved_outputs_no_new_tool_start", prior_run_id=prior["id"],
                previous_result_sha256=object_hash(prior["checks"]), prior_record_sha256=object_hash(prior))
            run["checks"].update(execution_reused=True, revalidated_from_run_id=prior["id"],
                previous_result_sha256=object_hash(prior["checks"]), revalidation_tool_starts=0, revalidation_model_calls=0)
            original = copy.deepcopy(prior)
            self.assertIs(validate_revalidation_binding(run, [prior, run]), prior)
            self.assertEqual(prior, original); self.assertEqual(prior["execution_status"], "Failed")
            mutations = (lambda r: r.update(prior_record_sha256="0" * 64),
                lambda r: r.update(previous_result_sha256="0" * 64),
                lambda r: r["checks"].update(revalidation_tool_starts=False),
                lambda r: r["checks"].update(revalidation_model_calls=1),
                lambda r: r["checks"].update(stdout="changed original log"),
                lambda r: r["checks"]["commands"][1].update(exit_code=1),
                lambda r: r.update(source_epoch_at_start=3))
            for mutation in mutations:
                changed = copy.deepcopy(run); mutation(changed)
                with self.subTest(mutation=mutation), self.assertRaises(ValueError): validate_revalidation_binding(changed, [prior, changed])
            with self.assertRaises(ValueError): validate_revalidation_binding(run, [run, prior])
            altered_prior = copy.deepcopy(prior); altered_prior["checks"]["diagnostics"] = [{"rewritten": True}]
            with self.assertRaises(ValueError): validate_revalidation_binding(run, [altered_prior, run])


if __name__ == "__main__": unittest.main()
