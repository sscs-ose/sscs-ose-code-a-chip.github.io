"""Isolated supervisor QA using explicit fake /proc; no EDA/model/WSL calls."""
from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import signal
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("physical_worker_v2", ROOT / "scripts/physical_worker_v2.py")
worker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(worker)


class FakeClock:
    def __init__(self):
        self.now = 0.0
        self.hook = None

    def clock(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds
        if self.hook:
            self.hook()


class PhysicalWorkerV2Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="hullcirq-worker-v2-software-QA-")
        self.root = Path(self.temp.name)
        self.proc = self.root / "proc"
        (self.proc / "sys/kernel/random").mkdir(parents=True)
        (self.proc / "sys/kernel/random/boot_id").write_text("11111111-2222-3333-4444-555555555555", encoding="ascii")
        self.clock = FakeClock()
        self.signals = []
        self.request_path = self.root / "request.json"
        self.worker_path = self.root / "frozen-worker.py"
        self.worker_path.write_bytes(b"Explicit software QA source snapshot; not a tool execution.\n")
        self.worker_sha = worker.digest(self.worker_path.read_bytes())
        self.request = {"version": worker.VERSION, "argv": ["/software-QA/librelane-devshell-x86_64.AppImage", "python3", "software-QA.py"],
                        "cwd": "/software-QA/physical-run", "timeout_seconds": 2, "worker_sha256": self.worker_sha}
        self.save_request()

    def tearDown(self):
        self.temp.cleanup()

    def save_request(self):
        self.request_path.write_bytes(worker.canonical(self.request) + b"\n")
        self.request_sha = worker.digest(self.request_path.read_bytes())

    def process(self, pid, state="S", group=100, birth=500, session=100):
        directory = self.proc / str(pid)
        directory.mkdir(exist_ok=True)
        fields = [state, "1", str(group), str(session)] + ["0"] * 15 + [str(birth)]
        (directory / "stat").write_text(str(pid) + " (comm with ) parentheses) " + " ".join(fields), encoding="utf-8")

    def remove(self, pid):
        (self.proc / str(pid) / "stat").unlink(missing_ok=True)
        directory = self.proc / str(pid)
        if directory.exists():
            directory.rmdir()

    def sender(self, pgid, sig):
        self.signals.append((pgid, sig))
        if sig == signal.SIGTERM:
            self.remove(100)  # Leader exits immediately; child ignores TERM.
        if sig == worker.KILL_SIGNAL:
            self.process(101, state="Z", birth=501)  # Zombie is dead/nonlive.

    def terminate(self, sender=None):
        return worker.terminate_group(100, proc_root=self.proc, clock=self.clock.clock,
                                      sleeper=self.clock.sleep, sender=sender or self.sender)

    def freeze_start(self, include_child=True):
        binding = worker.identity_fields(self.request, self.request_sha, self.worker_sha)
        start = {**binding, "process_group": 100, "leader_starttime": 500,
                 "boot_id": worker.boot_identity(self.proc), "observed_child_cwd": self.request["cwd"]}
        worker.atomic_json(self.root / "process-start.json", start)
        worker.atomic_json(self.root / "process-group.json", {"version": worker.VERSION,
                            "process_start_sha256": worker.digest((self.root / "process-start.json").read_bytes()),
                            "members": worker.live_group_members(100, self.proc) if include_child else []})
        return binding

    def cleanup(self, binding):
        return worker.cleanup_saved_group(self.root, binding, proc_root=self.proc,
                                         clock=self.clock.clock, sleeper=self.clock.sleep, sender=self.sender)

    def test_stat_parser_handles_parentheses_and_zombies_are_not_live(self):
        self.process(100)
        self.process(101, state="Z", birth=501)
        self.process(102, state="X", birth=502)
        self.process(103, state="T", birth=503)
        self.assertEqual(worker.read_process(100, self.proc)["starttime"], 500)
        self.assertEqual([p["pid"] for p in worker.live_group_members(100, self.proc)], [100, 103])

    def test_kill_escalates_after_leader_exits_and_child_ignores_term(self):
        self.process(100)
        self.process(101, birth=501)
        result = self.terminate()
        self.assertEqual(result["signals"], ["SIGTERM", "SIGKILL"])
        self.assertTrue(result["verified_terminated"])
        self.assertEqual(result["after"], [])
        self.assertLessEqual(self.clock.now, worker.TERM_SECONDS + worker.KILL_SECONDS + .2)

    def test_unkillable_group_is_bounded_and_never_claims_terminated(self):
        self.process(100)
        def ignored(pgid, sig):
            self.signals.append((pgid, sig))
        result = self.terminate(ignored)
        self.assertFalse(result["verified_terminated"])
        self.assertEqual(result["after"][0]["pid"], 100)
        self.assertLessEqual(self.clock.now, worker.TERM_SECONDS + worker.KILL_SECONDS + .2)
        self.assertEqual(len(self.signals), 2)

    def test_inspection_failure_is_not_success(self):
        self.process(100)
        (self.proc / "100/stat").write_text("truncated", encoding="utf-8")
        result = self.terminate()
        self.assertFalse(result["verified_terminated"])
        self.assertIn("Invalid Linux process", result["inspection_error"])
        self.assertEqual(self.signals, [])

    def test_non_utf8_comm_bytes_do_not_break_numeric_process_identity(self):
        self.process(100)
        path = self.proc / "100/stat"
        path.write_bytes(path.read_bytes().replace(b"comm", b"\xff\xfecomm"))
        self.assertEqual(worker.read_process(100, self.proc)["starttime"], 500)

    def test_cleanup_leader_gone_requires_checkpoint_anchor_then_kills_child(self):
        self.process(100)
        self.process(101, birth=501)
        binding = self.freeze_start()
        self.remove(100)
        result = self.cleanup(binding)
        self.assertTrue(result["whole_process_group_terminated_on_cancel"])
        self.assertEqual(result["status"], "Cancelled")
        self.assertEqual(result["termination"]["signals"], ["SIGTERM", "SIGKILL"])

    def test_cleanup_refuses_pid_reuse_boot_change_and_unanchored_children(self):
        cases = ("pid-reused", "boot-changed", "unanchored", "start-mismatch", "old-checkpoint")
        for case in cases:
            with self.subTest(case=case):
                self.signals.clear()
                self.process(100)
                self.process(101, birth=501)
                binding = self.freeze_start(include_child=case != "unanchored")
                if case == "pid-reused": self.process(100, birth=900)
                elif case == "boot-changed":
                    (self.proc / "sys/kernel/random/boot_id").write_text("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee", encoding="ascii")
                elif case in ("unanchored", "old-checkpoint"):
                    self.remove(100)
                    if case == "old-checkpoint":
                        record = json.loads((self.root / "process-group.json").read_text())
                        record["process_start_sha256"] = "0" * 64
                        worker.atomic_json(self.root / "process-group.json", record)
                else:
                    binding = {**binding, "request_sha256": "0" * 64}
                result = self.cleanup(binding)
                self.assertFalse(result["executed"])
                self.assertFalse(result["whole_process_group_terminated_on_cancel"])
                self.assertEqual(self.signals, [])
                (self.proc / "sys/kernel/random/boot_id").write_text("11111111-2222-3333-4444-555555555555", encoding="ascii")

    def test_no_live_members_cleanup_is_verified_without_signalling_zombies(self):
        self.process(100, state="Z")
        binding = self.freeze_start()
        result = self.cleanup(binding)
        self.assertTrue(result["whole_process_group_terminated_on_cancel"])
        self.assertEqual(self.signals, [])

    def test_request_and_source_hashes_and_strict_schema_are_checked_before_launch(self):
        self.assertEqual(worker.frozen_request(self.request_path, self.request_sha, self.worker_sha, self.worker_path), self.request)
        for key, value in (("timeout_seconds", True), ("timeout_seconds", 7201), ("timeout_seconds", 0),
                           ("cwd", "/unsafe/../cwd"), ("argv", ["/bin/sh", "python3"]), ("extra", "ignored")):
            with self.subTest(key=key, value=value):
                original = copy.deepcopy(self.request)
                self.request[key] = value
                self.save_request()
                with self.assertRaises(worker.WorkerError):
                    worker.frozen_request(self.request_path, self.request_sha, self.worker_sha, self.worker_path)
                self.request = original
        self.save_request()
        with self.assertRaises(worker.WorkerError): worker.frozen_request(self.request_path, "0" * 64, self.worker_sha, self.worker_path)
        with self.assertRaises(worker.WorkerError): worker.frozen_request(self.request_path, self.request_sha, "0" * 64, self.worker_path)

    def test_duplicate_json_keys_and_nonfinite_values_rejected(self):
        for raw in (b'{"argv":[],"argv":[]}', b'{"timeout_seconds":NaN}'):
            with self.assertRaises(worker.WorkerError): worker.load_json(raw)

    def run_fake(self, *, cancel=False, source_change=False, normal_exit=False):
        outer = self
        class FakeProcess:
            pid = 100
            returncode = None
            def __init__(self, argv, **kwargs):
                outer.assertEqual(argv, outer.request["argv"])
                outer.assertEqual(kwargs["cwd"], outer.request["cwd"])
                outer.assertIs(kwargs["start_new_session"], True)
                outer.assertIs(kwargs["shell"], False)
                outer.process(100)
                outer.process(101, birth=501)
                kwargs["stdout"].write(b"explicit software QA stdout\n")
            def poll(self):
                if normal_exit:
                    outer.remove(100); outer.remove(101)
                    self.returncode = 0
                elif not worker.live_group_members(100, outer.proc): self.returncode = -9
                return self.returncode
            def wait(self, timeout):
                if self.poll() is None: raise subprocess.TimeoutExpired("software QA", timeout)
                return self.returncode
        if cancel: (self.root / "cancel.request").write_bytes(b"software QA cancel\n")
        if source_change:
            self.clock.hook = lambda: self.worker_path.write_bytes(b"changed software QA snapshot\n")
        return worker.run_request(self.request_path, self.request_sha, self.worker_sha,
                                  worker_source_path=self.worker_path, proc_root=self.proc,
                                  clock=self.clock.clock, sleeper=self.clock.sleep,
                                  popen_factory=FakeProcess, sender=self.sender)

    def test_cancel_records_actual_cwd_start_identity_and_verified_descendant_kill(self):
        result = self.run_fake(cancel=True)
        start = json.loads((self.root / "process-start.json").read_text())
        self.assertEqual(start["cwd"], self.request["cwd"])
        self.assertEqual(start["request_sha256"], self.request_sha)
        self.assertEqual(start["worker_sha256"], self.worker_sha)
        self.assertEqual(start["leader_starttime"], 500)
        self.assertEqual(result["status"], "Cancelled")
        self.assertTrue(result["whole_process_group_terminated_on_cancel"])
        self.assertTrue(result["request_unchanged_at_completion"])
        self.assertTrue(result["worker_unchanged_at_completion"])
        self.assertEqual((self.root / "stdout.log").read_bytes(), b"explicit software QA stdout\n")

    def test_timeout_cleans_whole_group_and_source_mutation_cannot_complete(self):
        result = self.run_fake(source_change=True)
        self.assertEqual(result["status"], "Failed")
        self.assertFalse(result["worker_unchanged_at_completion"])
        self.assertTrue(result["whole_process_group_terminated_on_cancel"])
        self.assertLessEqual(self.clock.now, 2 + worker.TERM_SECONDS + worker.KILL_SECONDS + .3)

    def test_fast_normal_exit_rechecks_group_after_reaping(self):
        result = self.run_fake(normal_exit=True)
        self.assertEqual(result["status"], "Completed")
        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(result["diagnostics"], [])
        self.assertEqual(self.signals, [])
        self.assertTrue(result["whole_process_group_terminated"])

    def test_prior_launch_evidence_is_never_overwritten_by_reexecution(self):
        self.run_fake(normal_exit=True)
        before = {name: (self.root / name).read_bytes() for name in ("process-start.json", "process-result.json", "stdout.log", "stderr.log")}
        with self.assertRaises(worker.WorkerError): self.run_fake(normal_exit=True)
        self.assertEqual(before, {name: (self.root / name).read_bytes() for name in before})


if __name__ == "__main__":
    unittest.main()
