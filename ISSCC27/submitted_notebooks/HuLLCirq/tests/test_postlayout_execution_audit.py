"""Isolated software proof fixtures; no actual circuit/tool evidence created."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from hullcirq.domain import DomainError
from hullcirq import postlayout_execution_audit as audit
from hullcirq.postlayout_execution import fixed_worker_definition
from hullcirq.verification import object_hash


class PostlayoutExecutionAuditTests(unittest.TestCase):
    def setUp(self):
        private = ROOT / ".work/m2k/software_qa_tmp"
        private.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="execution-proof-SOFTWARE-QA-", dir=private)
        self.folder = Path(self.temp.name)
        self.logs = self.folder / "simulate"
        self.logs.mkdir()
        self.definition = fixed_worker_definition()
        self.cwd = self.definition["WORK_ROOT"] + "/original-job-SOFTWARE_QA"
        self.patch = patch.object(audit, "_wsl_path", return_value=self.cwd)
        self.patch.start()
        for name in self.definition["COMPILE_INPUTS"] + ("simulation.vvp",):
            (self.folder / name).write_bytes(b"SOFTWARE QA placeholder, not circuit input/output")
        worker_raw = self.definition["_worker_source"].read_bytes()
        (self.logs / "worker.py").write_bytes(worker_raw)
        self.request = {"version": self.definition["VERSION"], "argv": list(self.definition["SIMULATION_ARGV"]), "cwd": self.cwd,
                        "timeout_seconds": 10, "worker_sha256": hashlib.sha256(worker_raw).hexdigest(),
                        "configuration_sha256": object_hash(self.definition["CONFIGURATION"]),
                        "input_files": {name: hashlib.sha256((self.folder / name).read_bytes()).hexdigest() for name in self.definition["COMPILE_INPUTS"] + ("simulation.vvp",)}}
        self.save("request.json", self.request)
        binding = self.definition["identity_fields"](self.request, hashlib.sha256((self.logs / "request.json").read_bytes()).hexdigest(), self.request["worker_sha256"])
        self.start = {**binding, "process_group": 100, "leader_starttime": 500, "boot_id": "11111111-2222-3333-4444-555555555555", "observed_child_cwd": self.cwd}
        self.save("process-start.json", self.start)
        self.result = {**binding, "process_group": 100, "leader_starttime": 500, "observed_child_cwd": self.cwd,
                       "process_start_sha256": hashlib.sha256((self.logs / "process-start.json").read_bytes()).hexdigest(),
                       "exit_code": 0, "status": "Completed", "executed": True, "whole_process_group_terminated": True,
                       "request_unchanged_at_completion": True, "worker_unchanged_at_completion": True,
                       "inputs_unchanged_at_completion": True, "runtime_unchanged_at_completion": True, "elapsed_seconds": 1.0}
        self.save("process-result.json", self.result)

    def tearDown(self):
        self.patch.stop()
        self.temp.cleanup()

    def save(self, name, value):
        (self.logs / name).write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")

    def test_complete_software_proof_binds_without_evaluating_a_circuit(self):
        proof = audit.validate_completed_execution(self.folder, "simulate")
        self.assertTrue(proof["execution_binding_verified"])
        self.assertEqual(proof["circuit_validation_status"], "Not evaluated")
        self.assertFalse(proof["adoption_permitted"])

    def test_runtime_input_and_worker_bytes_cannot_be_rebound(self):
        for path in (self.folder / "input.nl.v", self.logs / "worker.py"):
            raw = path.read_bytes()
            path.write_bytes(raw + b"SOFTWARE QA mutation")
            with self.subTest(path=path), self.assertRaises(DomainError):
                audit.validate_completed_execution(self.folder, "simulate")
            path.write_bytes(raw)

    def test_changed_birth_or_request_snapshot_is_rejected(self):
        for name, base, key, changed in (("process-start.json", self.start, "process_group", 101),
                                         ("process-start.json", self.start, "boot_id", "invalid"),
                                         ("request.json", self.request, "configuration_sha256", "0" * 64)):
            self.save(name, {**base, key: changed})
            with self.subTest(key=key), self.assertRaises(DomainError):
                audit.validate_completed_execution(self.folder, "simulate")
            self.save(name, base)

    def test_unverified_or_wrong_terminal_types_never_count_as_completed(self):
        changes = {"whole_process_group_terminated": False, "runtime_unchanged_at_completion": False,
                   "inputs_unchanged_at_completion": False, "exit_code": False, "status": "Failed", "executed": False,
                   "process_start_sha256": "0" * 64}
        for key, changed in changes.items():
            self.save("process-result.json", {**self.result, key: changed})
            with self.subTest(key=key), self.assertRaises(DomainError):
                audit.validate_completed_execution(self.folder, "simulate")
        self.save("process-result.json", self.result)


if __name__ == "__main__":
    unittest.main()
