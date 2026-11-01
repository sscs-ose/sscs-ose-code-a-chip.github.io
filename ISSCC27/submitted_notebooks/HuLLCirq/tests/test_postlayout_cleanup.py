"""Synthetic saved supervisor proofs; these tests run no EDA or process."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))
from hullcirq import postlayout_cleanup as cleanup
from hullcirq.domain import DomainError
from hullcirq.verification import object_hash, trusted_command, _wsl_path


class SavedTerminationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.patch_root = patch.object(cleanup, "ROOT", self.root)
        self.patch_root.start(); self.addCleanup(self.patch_root.stop)
        self.folder = self.root / ".work/runs/postroute-software-qa"
        self.folder.mkdir(parents=True)
        self.runtime = {"kind": "wsl", "distribution": "Ubuntu", "executable": "/mnt/c/SOFTWARE_QA/librelane-devshell-x86_64.AppImage"}
        self.write(self.folder / "functional-inputs.json", {"software_qa_inputs": True})
        self.write(self.folder / "functional-program.json", {"software_qa_program": True})
        self.write(self.folder / "sta/sta-inputs.json", {"software_qa_sta": True})
        records = []
        worker = (PROJECT / "scripts/physical_worker_v2.py").read_bytes()
        self.assertEqual(hashlib.sha256(worker).hexdigest(), cleanup.physical.WORKER_V2_SHA)
        for index, operation in enumerate(("compile", "simulate", "sta-" + cleanup.CORNERS[0])):
            folder = self.folder if index < 2 else self.folder / "sta"
            logs = folder / operation
            logs.mkdir(parents=True)
            (logs / "worker.py").write_bytes(worker)
            if index < 2:
                args = ["python3", _wsl_path(folder / "run_functional.py"), operation,
                        self.digest(self.folder / "functional-inputs.json")]
                if index == 1: args.append(self.digest(self.folder / "functional-program.json"))
            else:
                args = ["python3", _wsl_path(folder / "run_sta.py"), cleanup.CORNERS[0], self.digest(folder / "sta-inputs.json")]
            command = trusted_command(self.runtime, self.runtime["executable"], args, folder)
            request = {"version": "hullcirq-physical-worker-v2", "argv": command[command.index("--exec") + 1:],
                       "cwd": _wsl_path(folder), "timeout_seconds": 300, "worker_sha256": cleanup.physical.WORKER_V2_SHA}
            self.write(logs / "request.json", request)
            request_hash = self.digest(logs / "request.json")
            binding = {key: request[key] for key in ("version", "argv", "cwd", "worker_sha256")}
            binding["request_sha256"] = request_hash
            start = {**binding, "process_group": 123 + index, "leader_starttime": 456 + index,
                     "boot_id": "00000000-0000-0000-0000-000000000000", "observed_child_cwd": request["cwd"]}
            self.write(logs / "process-start.json", start)
            terminal = {**start, "executed": True, "status": "Completed", "exit_code": 0,
                        "whole_process_group_terminated": True, "request_unchanged_at_completion": True,
                        "worker_unchanged_at_completion": True, "process_start_sha256": self.digest(logs / "process-start.json")}
            self.write(logs / "process-result.json", terminal)
            supervisor = trusted_command(self.runtime, "/usr/bin/python3", [_wsl_path(logs / "worker.py"),
                _wsl_path(logs / "request.json"), "--request-sha256", request_hash,
                "--worker-sha256", cleanup.physical.WORKER_V2_SHA], folder)
            wrapper = {**terminal, "command": command, "supervisor_command": supervisor, "cleanup_unresolved": False}
            if index == 2:
                wrapper = {key: wrapper[key] for key in ("command", "supervisor_command", "request_sha256", "worker_sha256")}
                wrapper.update(executed=False, status="Failed", exit_code=None, cleanup_unresolved=True)
            records.append(wrapper)
        self.record = {"id": "SOFTWARE_QA_S14", "execution_status": "Failed", "validation_status": "Not Checked",
                    "review_status": "Awaiting Review", "evidence_kind": "trusted_fixed_postlayout_execution",
                    "execution_scope": "post_route_functional_plus_sta", "error": {"code": "SOFTWARE_QA_PATH_LIMIT"},
                    "runtime_configuration": {"physical_runtime": self.runtime, "working_directory": str(self.folder.parent)},
                    "checks": {"cleanup_unresolved": True, "artifacts_directory": str(self.folder), "commands": records}}
        self.rehash()

    @staticmethod
    def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
    @staticmethod
    def write(path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")
    def rehash(self): self.record["record_hash"] = object_hash({k: v for k, v in self.record.items() if k != "record_hash"})
    def resolution(self):
        value = {"id": "SOFTWARE_QA_RESOLUTION", "run_id": self.record["id"], "actor": "gui_operator", "created_at": "SOFTWARE_QA_TIME",
                 "provenance": {"interface": "GUI", "action": "verify_saved_process_termination"},
                 "original_run_record_sha256": self.record["record_hash"], "execution_sha256": cleanup.execution_hash(self.record),
                 "evidence": cleanup.termination_evidence(self.record)}
        value["record_hash"] = object_hash(value)
        return value

    def test_original_failed_wrapper_is_preserved_and_feedback_does_not_invalidate_proof(self):
        before = copy.deepcopy(self.record)
        resolution = self.resolution()
        cleanup.validate_resolution(self.record, resolution)
        self.assertEqual(self.record, before)
        self.assertEqual(len(resolution["evidence"]["commands"]), 3)
        self.record["review_status"] = "Changes Requested"; self.rehash()
        cleanup.validate_resolution(self.record, resolution)
        self.assertEqual(self.record["checks"], before["checks"])
        self.record["error"]["code"] = "ALTERED"; self.rehash()
        with self.assertRaises(DomainError): cleanup.validate_resolution(self.record, resolution)

    def test_missing_terminal_or_changed_raw_hash_cannot_resolve(self):
        terminal = self.folder / "sta" / ("sta-" + cleanup.CORNERS[0]) / "process-result.json"
        original = terminal.read_bytes()
        resolution = self.resolution()
        terminal.unlink()
        with self.assertRaises(DomainError): cleanup.termination_evidence(self.record)
        terminal.write_bytes(original + b" ")
        with self.assertRaises(DomainError): cleanup.validate_resolution(self.record, resolution)

    def test_unterminated_group_worker_tamper_birth_swap_and_extra_request_are_rejected(self):
        logs = self.folder / "compile"
        for filename, key, value in (("process-result.json", "whole_process_group_terminated", False),
                                     ("process-result.json", "request_unchanged_at_completion", False),
                                     ("process-start.json", "process_group", 999)):
            path = logs / filename; original = path.read_bytes(); changed = json.loads(original)
            changed[key] = value; self.write(path, changed)
            with self.subTest(field=key), self.assertRaises(DomainError): cleanup.termination_evidence(self.record)
            path.write_bytes(original)
        worker = logs / "worker.py"; original = worker.read_bytes(); worker.write_bytes(original + b"# changed")
        with self.assertRaises(DomainError): cleanup.termination_evidence(self.record)
        worker.write_bytes(original)
        self.write(self.folder / "unrecorded/request.json", {})
        with self.assertRaises(DomainError): cleanup.termination_evidence(self.record)


if __name__ == "__main__": unittest.main()
