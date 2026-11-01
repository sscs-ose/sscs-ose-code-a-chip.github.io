"""Isolated SOFTWARE QA for S13 archival/rejection mechanics, with no EDA.

These disposable bytes are not layout or LVS evidence. No fixture is copied
into the original NPU store or any submitted actual-circuit proof archive.
"""
from __future__ import annotations

import copy
import gzip
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT / "scripts"))

from collect_lvs_proof import (LVS_HISTORY, SOURCE_HISTORIES, attempt_inventory, copy_attempt, declared_files, digest,
    load_baseline, normalized_history_hashes, require_real_origin, require_source_bytes, safe_relative, terminal_history,
    validate_history_selection, validate_lineage, validate_reviews, verify_default_histories, verify_prior_payloads)
from collect_global_proof import history_descriptor
from node_spec_evidence import write_json
from replay_lvs_proof import decode_history, verify_attempt
from hullcirq.domain import DomainError
from hullcirq.verification import object_hash


def signed(value):
    result = copy.deepcopy(value); result.pop("record_hash", None)
    result["record_hash"] = object_hash(result)
    return result


def software_source():
    """Pure snapshot fixture: no original design or executed physical tool."""
    descriptors = {key: {"id": key, "kind": "software_qa_only", "relative_path": "qa." + key,
        "sha256": letter * 64, "bytes": 3, "content_type": "application/octet-stream"}
        for key, letter in (("gds", "a"), ("def", "b"), ("netlist", "c"))}
    gds = descriptors["gds"]
    layout = signed({"id": "qa-layout", "revision_id": "qa-revision", "execution_status": "Completed", "validation_status": "Passed",
                     "review_status": "Accepted", "source_key": "qa-physical-source", "source_epoch_at_start": 1,
                     "acceptance_epoch": 1, "checks": {"artifacts": list(descriptors.values()), "software_qa_fixture": True}})
    review = {"id": "qa-layout-review", "run_id": layout["id"], "decision": "accepted", "source_key": layout["source_key"], "acceptance_epoch": 1}
    drc_configuration = {"origin": "SOFTWARE_QA_ONLY_DRC"}
    drc_identity = {"revision_id": layout["revision_id"], "layout_run_id": layout["id"], "layout_record_sha256": object_hash(layout),
        "physical_source_key": layout["source_key"], "physical_source_epoch": 1, "layout_adoption": review,
        "input_gds": gds, "configuration_sha256": object_hash(drc_configuration)}
    drc = signed({"id": "qa-drc", "revision_id": layout["revision_id"], "layout_run_id": layout["id"], "layout_snapshot": layout,
        "layout_record_sha256": object_hash(layout), "layout_adoption": review, "input_gds_sha256": gds["sha256"],
        "runtime_configuration": drc_configuration, "configuration_sha256": object_hash(drc_configuration),
        "source_identity": drc_identity, "source_key": object_hash(drc_identity), "source_epoch_at_start": 1, "acceptance_epoch": 1,
        "execution_status": "Completed", "validation_status": "Passed", "review_status": "Accepted", "checks": {"software_qa_fixture": True}})
    drc_review = {"id": "qa-drc-review", "run_id": drc["id"], "decision": "accepted", "source_key": drc["source_key"], "acceptance_epoch": 1}
    inputs = {**descriptors, "powered_netlist": {"id": "powered-netlist", "relative_path": "qa.pnl.v", "sha256": "d" * 64,
        "bytes": 3, "content_type": "text/plain", "origin": "original_S11_state_pointer_observed_at_S13_start",
        "binding": {"software_qa_fixture": True}}}
    configuration = {"origin": "SOFTWARE_QA_ONLY"}
    identity = {"revision_id": layout["revision_id"], "layout_run_id": layout["id"], "layout_record_sha256": object_hash(layout),
        "physical_source_key": layout["source_key"], "physical_source_epoch": 1, "layout_adoption": review,
        "drc_run_id": drc["id"], "drc_record_sha256": object_hash(drc), "drc_source_key": drc["source_key"],
        "drc_source_epoch": 1, "drc_adoption": drc_review, "source_inputs": inputs, "configuration_sha256": object_hash(configuration)}
    run = {"id": "qa-lvs", "stage_id": "lvs", "revision_id": layout["revision_id"], "layout_run_id": layout["id"],
        "layout_snapshot": layout, "layout_record_sha256": object_hash(layout), "layout_adoption": review,
        "drc_run_id": drc["id"], "drc_snapshot": drc, "drc_record_sha256": object_hash(drc), "drc_adoption": drc_review,
        "source_inputs": inputs, "input_netlist_sha256": inputs["netlist"]["sha256"], "input_powered_netlist_sha256": inputs["powered_netlist"]["sha256"],
        "input_gds_sha256": gds["sha256"], "runtime_configuration": configuration, "configuration_sha256": object_hash(configuration),
        "source_identity": identity, "source_key": object_hash(identity), "source_epoch_at_start": 1,
        "evidence_kind": "software_qa_fixture", "checks": {"software_qa_fixture": True}, "execution_status": "Completed",
        "validation_status": "Failed", "review_status": "Awaiting Review"}
    return signed(run), layout, drc, {"reviews": [review]}, {"reviews": [drc_review]}


def software_history(run=None):
    run = run or software_source()[0]
    return {"lvs_workflow_store_version": "0.1", "runs": [run], "reviews": [], "source_epoch": 1,
            "source_key": run["source_key"], "source_transitions": [{"epoch": 1, "source_key": run["source_key"]}]}


def software_files(root):
    run, *_ = software_source(); folder = Path(root) / "runs/hullcirq-lvs-software-qa"; folder.mkdir(parents=True)
    payloads = {"input.gds": b"SOFTWARE QA ONLY\x00\xff\r\n", "reports/markers.xml": b"SOFTWARE QA ONLY\r\n",
                "lvs/stdout.log": b"SOFTWARE QA ONLY\xff\r\n", "lvs/stderr.log": b"", "lvs/request.json": b'{"SOFTWARE_QA_ONLY":true}\r\n'}
    for relative, payload in payloads.items():
        path = folder / relative; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(payload)
    entries = [{"relative_path": relative, "sha256": digest(payload), "bytes": len(payload)} for relative, payload in payloads.items()]
    artifact = {**entries[0], "id": "input-gds", "kind": "software_qa_only", "content_type": "application/octet-stream"}
    stdout = (folder / "lvs/stdout.log").read_text(encoding="utf-8", errors="replace")
    command = {"executed": False, "status": "Failed", "exit_code": None, "stdout": stdout, "stderr": "", "command": ["SOFTWARE_QA_ONLY_NEVER_EXECUTED"]}
    run["runtime_configuration"]["working_directory"] = str(folder.parent)
    run["checks"].update(artifacts_directory=str(folder), artifacts=[artifact], retained_files=entries,
                         commands=[command], stdout=stdout, stderr="", checks={})
    return signed(run), folder, payloads


class LvsEvidenceTests(unittest.TestCase):
    def test_all_eight_original_histories_are_byte_exact(self):
        original = {name: b'{"SOFTWARE_QA_ONLY":true}\r\n' for name in SOURCE_HISTORIES}
        require_source_bytes(copy.deepcopy(original), original)
        for name in SOURCE_HISTORIES:
            changed = dict(original); changed[name] += b" "
            with self.subTest(name=name), self.assertRaises(ValueError): require_source_bytes(changed, original)
        with self.assertRaises(ValueError): require_source_bytes({k: v for k, v in original.items() if k != "physical_workflow.json"}, original)

    def test_baseline_accepts_only_canonical_complete_unique_source_keys(self):
        hashes = {".work/projects/npu/" + name: "a" * 64 for name in SOURCE_HISTORIES}
        self.assertEqual(set(normalized_history_hashes({"original_NPU_histories": hashes})), set(SOURCE_HISTORIES))
        for mutate in (lambda v: v.pop(".work/projects/npu/physical_workflow.json"), lambda v: v.update({"state.json": "a" * 64}),
                       lambda v: v.update({"../state.json": "a" * 64}), lambda v: v.update({".work/projects/npu/state.json": "not-sha"})):
            value = dict(hashes); mutate(value)
            with self.subTest(mutation=mutate), self.assertRaises(ValueError): normalized_history_hashes({"original_NPU_histories": value})

    def test_original_baseline_copy_corruption_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="lvs-evidence-software-qa-") as name:
            root = Path(name); originals = root / "originals"; originals.mkdir()
            values = {file: b'{"SOFTWARE_QA_ONLY":true}\n' for file in SOURCE_HISTORIES}
            for file, raw in values.items(): (originals / file).write_bytes(raw)
            baseline = {"original_NPU_histories": {k: digest(v) for k, v in values.items()}, "preexisting_files": {}, "default_histories": {}, "layout_run_id": "qa-layout"}
            path = root / "baseline.json"; write_json(path, baseline)
            self.assertEqual(load_baseline(path, originals)[2], values)
            (originals / "physical_workflow.json").write_bytes(b"{}")
            with self.assertRaises(ValueError): load_baseline(path, originals)

    def test_prior_results_protected_while_source_can_change(self):
        with tempfile.TemporaryDirectory(prefix="lvs-evidence-software-qa-") as name:
            root = Path(name); path = root / "results/prior/raw.bin"; path.parent.mkdir(parents=True); path.write_bytes(b"SOFTWARE QA PRIOR")
            baseline = {"preexisting_files": {"results/prior/raw.bin": digest(path.read_bytes()), "src/evolving.py": "a" * 64}}
            self.assertEqual(len(verify_prior_payloads(baseline, root)), 1)
            path.write_bytes(b"changed")
            with self.assertRaises(ValueError): verify_prior_payloads(baseline, root)

    def test_existing_default_histories_protected_including_empty_histories(self):
        with tempfile.TemporaryDirectory(prefix="lvs-evidence-software-qa-") as name:
            root = Path(name); relative = ".work/projects/default/physical_workflow.json"; path = root / relative
            path.parent.mkdir(parents=True); path.write_bytes(b'{"SOFTWARE_QA_ONLY":"empty"}\r\n')
            baseline = {"default_histories": {relative: digest(path.read_bytes())}}
            verify_default_histories(baseline, root)
            path.write_bytes(path.read_bytes() + b" ")
            with self.assertRaises(ValueError): verify_default_histories(baseline, root)

    def test_terminal_history_keeps_failed_result_and_rejects_active_or_duplicate(self):
        history = software_history(); self.assertEqual(terminal_history(json.dumps(history).encode())["runs"][0]["validation_status"], "Failed")
        for status in ("Queued", "Running"):
            changed = copy.deepcopy(history); changed["runs"][0] = signed({**changed["runs"][0], "execution_status": status})
            with self.subTest(status=status), self.assertRaises(ValueError): terminal_history(json.dumps(changed).encode())
        changed = copy.deepcopy(history); changed["runs"] *= 2
        with self.assertRaises(ValueError): terminal_history(json.dumps(changed).encode())

    def test_record_hash_and_epoch_strict_integer_checks(self):
        history = software_history(); changed = copy.deepcopy(history); changed["runs"][0]["validation_status"] = "Passed"
        with self.assertRaises(ValueError): terminal_history(json.dumps(changed).encode())
        for epoch in (True, 1.0, -1):
            changed = copy.deepcopy(history); changed["source_epoch"] = epoch
            with self.subTest(epoch=epoch), self.assertRaises(ValueError): terminal_history(json.dumps(changed).encode())

    def test_latest_failure_never_falls_back_to_old_pass(self):
        history = software_history(); old = signed({**history["runs"][0], "id": "qa-old", "validation_status": "Passed"})
        history["runs"].insert(0, old)
        self.assertEqual(validate_history_selection(history)["validation_status"], "Failed")
        history["runs"][-1]["source_epoch_at_start"] = 0
        with self.assertRaises(ValueError): validate_history_selection(history)

    def test_failed_result_cannot_be_accepted(self):
        history = software_history(); history["runs"][0].update(review_status="Accepted", acceptance_epoch=1)
        with self.assertRaises(ValueError): validate_history_selection(history)

    def test_source_snapshot_detects_resigned_dual_sources_inputs_config_and_reviews(self):
        run, layout, drc, physical, drc_history = software_source()
        with patch("collect_lvs_proof.require_real_origin"):
            validate_lineage(run, layout, drc, physical, drc_history)
            for mutate in (lambda r: r.update(layout_run_id="another"), lambda r: r["layout_snapshot"].update(revision_id="other"),
                           lambda r: r.update(input_gds_sha256="b" * 64), lambda r: r["runtime_configuration"].update(extra=True),
                           lambda r: r["layout_adoption"].update(id="another-review"), lambda r: r["drc_snapshot"].update(validation_status="Failed"),
                           lambda r: r["drc_adoption"].update(id="another-drc-review"), lambda r: r.update(input_netlist_sha256="e" * 64),
                           lambda r: r["source_inputs"]["powered_netlist"].update(origin="falsely_claimed_previously_retained_S11_artifact")):
                changed = copy.deepcopy(run); mutate(changed)
                with self.subTest(mutation=mutate), self.assertRaises((DomainError, ValueError)):
                    validate_lineage(signed(changed), layout, drc, physical, drc_history)

    def test_software_fixture_and_unidentified_runtime_cannot_be_actual_evidence(self):
        run, *_ = software_source()
        with self.assertRaises(ValueError): require_real_origin(run)
        changed = copy.deepcopy(run); changed["evidence_kind"] = "trusted_fixed_lvs_execution"
        with self.assertRaises(ValueError): require_real_origin(changed)

    def test_nested_profile_origin_matches_actual_runtime_contract_without_invented_top_field(self):
        # Only provenance-shape admission is exercised here. These disposable
        # records do not satisfy the separate executed-tool/raw-output proof.
        run, *_ = software_source()
        run.update(evidence_kind="trusted_fixed_lvs_execution")
        run["checks"]["software_qa_fixture"] = False
        run["runtime_configuration"] = {"physical_runtime": {}, "working_directory": "SOFTWARE_QA_ONLY",
                                        "profile": {"origin": "SOFTWARE_QA_ONLY_profile_origin_shape"}}
        require_real_origin(run)
        for value in (None, "", " ", True):
            changed = copy.deepcopy(run); changed["runtime_configuration"]["profile"]["origin"] = value
            with self.subTest(origin=value), self.assertRaises(ValueError): require_real_origin(changed)
        changed = copy.deepcopy(run); changed["checks"]["software_qa_fixture"] = True
        with self.assertRaises(ValueError): require_real_origin(changed)
        changed["checks"]["software_qa_fixture"] = False; changed["runtime_configuration"]["origin"] = " "
        with self.assertRaises(ValueError): require_real_origin(changed)

    def test_automatic_review_without_original_policy_is_rejected(self):
        history = software_history(); run = history["runs"][0]
        history["reviews"] = [{"run_id": run["id"], "decision": "accepted", "actor": "automation_policy", "source_key": run["source_key"], "note": "SOFTWARE QA"}]
        run["review_status"] = "Accepted"
        with self.assertRaises(DomainError): validate_reviews(history, {})

    def test_review_status_cannot_hide_withdrawal(self):
        history = software_history(); run = history["runs"][0]
        history["reviews"] = [{"run_id": run["id"], "decision": "changes_requested", "actor": "human", "source_key": run["source_key"], "note": "SOFTWARE QA"}]
        with self.assertRaises(ValueError): validate_reviews(history, {})
        run["review_status"] = "Changes Requested"; validate_reviews(history, {})

    def test_safe_relative_rejects_traversal_noncanonical_and_windows_aliases(self):
        self.assertEqual(safe_relative("runs/lvs/raw.log").as_posix(), "runs/lvs/raw.log")
        for value in ("../raw", "./raw", "a//raw", "a/../raw", "/raw", "C:/raw", "a\\raw", "a\nraw", ""):
            with self.subTest(value=value), self.assertRaises(ValueError): safe_relative(value)

    def test_declared_files_reject_duplicate_id_path_bool_length_and_hash_conflict(self):
        with tempfile.TemporaryDirectory(prefix="lvs-evidence-software-qa-") as name:
            run, _, _ = software_files(name); result = run["checks"]; self.assertGreater(len(declared_files(result)), 1)
            for mutate in (lambda r: r["artifacts"].append(copy.deepcopy(r["artifacts"][0])),
                           lambda r: r["artifacts"][0].update(bytes=True), lambda r: r["artifacts"][0].update(id="arbitrary-file"),
                           lambda r: r["retained_files"][0].update(sha256="b" * 64)):
                changed = copy.deepcopy(result); mutate(changed)
                with self.subTest(mutation=mutate), self.assertRaises(ValueError): declared_files(changed)

    def test_raw_binary_and_invalid_utf8_logs_preserved_with_shared_exact_files(self):
        with tempfile.TemporaryDirectory(prefix="lvs-evidence-software-qa-") as name:
            root = Path(name); run, _, payloads = software_files(root); output = root / "archive"; shared = {}
            first = copy_attempt(run, [], output, shared)
            another = signed({**run, "id": "qa-second"}); second = copy_attempt(another, [], output, shared)
            self.assertEqual(len(shared), len(payloads))
            for entry in first["files"]:
                self.assertEqual((output / entry["export_path"]).read_bytes(), payloads[entry["relative_path"]])
            self.assertTrue(all(e["storage"] == "shared_exact_raw_file" for e in second["files"]))
            verify_attempt(output, first, run, [])

    def test_empty_extraction_feedback_is_preserved_without_allowing_other_empty_artifacts(self):
        with tempfile.TemporaryDirectory(prefix="lvs-evidence-software-qa-") as name:
            root = Path(name); run, folder, _ = software_files(root)
            relative = "reports/extraction-feedback.txt"; (folder / relative).write_bytes(b"")
            entry = {"relative_path": relative, "sha256": digest(b""), "bytes": 0}
            run["checks"]["artifacts"].append({**entry, "id": "extraction-feedback", "content_type": "text/plain; charset=utf-8"})
            run["checks"]["retained_files"].append(entry); run = signed(run)
            self.assertEqual(declared_files(run["checks"])[relative]["bytes"], 0)
            output = root / "archive"; archive = copy_attempt(run, [], output)
            saved = next(item for item in archive["files"] if item["relative_path"] == relative)
            self.assertEqual((output / saved["export_path"]).read_bytes(), b"")
            verify_attempt(output, archive, run, [])
            for artifact_id in ("input-gds", "extracted-spice", "lvs-report", "metrics"):
                changed = copy.deepcopy(run["checks"]); changed["artifacts"][-1]["id"] = artifact_id
                with self.subTest(artifact_id=artifact_id), self.assertRaises(ValueError): declared_files(changed)

    def test_attempt_missing_or_changed_declared_raw_file_rejected(self):
        with tempfile.TemporaryDirectory(prefix="lvs-evidence-software-qa-") as name:
            run, folder, _ = software_files(name); (folder / "input.gds").write_bytes(b"changed")
            with self.assertRaises(ValueError): attempt_inventory(run)
            (folder / "input.gds").unlink()
            with self.assertRaises(ValueError): attempt_inventory(run)

    def test_unexecuted_preparation_failure_can_preserve_record_without_output_dir(self):
        run, *_ = software_source()
        self.assertIsNone(attempt_inventory(run)["directory"])
        run["checks"]["executed"] = True
        with self.assertRaises(ValueError): attempt_inventory(run)

    def test_attempt_cannot_escape_configured_lvs_root(self):
        with tempfile.TemporaryDirectory(prefix="lvs-evidence-software-qa-") as name:
            run, _, _ = software_files(name); run["runtime_configuration"]["working_directory"] = str(Path(name) / "other")
            with self.assertRaises(ValueError): attempt_inventory(run)

    def test_portable_verification_rehydrates_exact_bytes_without_original_paths(self):
        with tempfile.TemporaryDirectory(prefix="lvs-evidence-software-qa-") as name:
            root = Path(name); run, folder, payloads = software_files(root)
            run["checks"]["checks"] = {"lvs": {"completed": True}}; run = signed(run)
            output = root / "archive"; entry = copy_attempt(run, [], output)
            def fixture_validator(result, drc_snapshot, layout_snapshot, configuration, artifact_root=None):
                self.assertTrue(result["software_qa_fixture"])
                self.assertNotEqual(Path(artifact_root), folder)
                for relative, payload in payloads.items(): self.assertEqual((Path(artifact_root) / relative).read_bytes(), payload)
            # Explicit software fixture: this only exercises override plumbing.
            # Actual archive admission uses the unmocked fixed validator.
            with patch("hullcirq.lvs_tools.validate_lvs_result", side_effect=fixture_validator) as validator:
                verify_attempt(output, entry, run, [])
                self.assertEqual(validator.call_count, 1)

    def test_portable_attempt_rejects_relabeled_record_and_raw_output(self):
        with tempfile.TemporaryDirectory(prefix="lvs-evidence-software-qa-") as name:
            root = Path(name); run, _, _ = software_files(root); output = root / "archive"; entry = copy_attempt(run, [], output)
            changed = copy.deepcopy(entry); changed["validation_status"] = "Passed"
            with self.assertRaises(ValueError): verify_attempt(output, changed, run, [])
            (output / entry["files"][0]["export_path"]).write_bytes(b"altered")
            with self.assertRaises(ValueError): verify_attempt(output, entry, run, [])

    def test_lossless_compressed_history_rejects_changed_bytes_length_and_name(self):
        with tempfile.TemporaryDirectory(prefix="lvs-evidence-software-qa-") as name:
            root = Path(name); raw = json.dumps(software_history()).encode(); path = root / (LVS_HISTORY + ".gz")
            path.write_bytes(gzip.compress(raw, mtime=0)); descriptor = history_descriptor(path, raw)
            self.assertEqual(decode_history(root, descriptor, path.name), raw)
            for mutate in (lambda d: d.update(decompressed_bytes=d["decompressed_bytes"] - 1), lambda d: d.update(decompressed_sha256="a" * 64),
                           lambda d: d.update(archive="../bad.gz"), lambda d: d.update(decompressed_bytes=True)):
                changed = dict(descriptor); mutate(changed)
                with self.subTest(mutation=mutate), self.assertRaises(ValueError): decode_history(root, changed, path.name)


if __name__ == "__main__":
    unittest.main()
