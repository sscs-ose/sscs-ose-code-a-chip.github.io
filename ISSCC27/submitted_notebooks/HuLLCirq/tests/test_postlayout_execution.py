"""Fixed execution guard QA, with fake /proc and no simulator/WSL execution."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from hullcirq.domain import DomainError
from hullcirq import postlayout_execution as host
from hullcirq.verification import object_hash

SPEC = importlib.util.spec_from_file_location("postlayout_worker_qa", ROOT / "scripts/postlayout_worker_v1.py")
worker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(worker)
SPEC_V2 = importlib.util.spec_from_file_location("postlayout_worker_v2_qa", ROOT / "scripts/postlayout_worker_v2.py")
worker_v2 = importlib.util.module_from_spec(SPEC_V2)
SPEC_V2.loader.exec_module(worker_v2)


class PostlayoutExecutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qa_temp = ROOT / ".work/m2k/software_qa_tmp"
        cls.qa_temp.mkdir(parents=True, exist_ok=True)

    def test_source_and_config_are_exactly_pinned(self):
        self.assertEqual(host.sha(host.WORKER_SOURCE), host.WORKER_SHA256)
        self.assertEqual(worker.digest(worker.canonical(worker.CONFIGURATION)), object_hash(worker.CONFIGURATION))
        self.assertEqual(len(worker.TOOL_SHA256), 39)
        self.assertEqual(worker.TOOL_SHA256["usr/bin/iverilog"], "e29c891c741689c5d06791dc57f12e3a6df2eeac010a3913f7be57e9ef493bb3")
        self.assertEqual(host.sha(ROOT / "scripts/physical_worker_v2.py"), "589b6b2841f1e31b8fde26f9b9fd8f872b2c9de0e396fb99bdb5a920b1a2220f")

    def test_only_original_job_exact_compiler_and_simulator_argv_allowed(self):
        cwd = worker.WORK_ROOT + "/original-job-SOFTWARE_QA"
        self.assertEqual(worker.validate_operation(list(worker.COMPILE_ARGV), cwd), worker.COMPILE_INPUTS)
        self.assertEqual(worker.validate_operation(list(worker.SIMULATION_ARGV), cwd), worker.COMPILE_INPUTS + ("simulation.vvp",))
        bad = [list(worker.COMPILE_ARGV) + ["extra.v"], ["/bin/sh", "-c", "echo arbitrary"],
               list(worker.COMPILE_ARGV[:-1]) + ["unbound.v"], list(worker.SIMULATION_ARGV) + ["-m", "arbitrary"],
               [worker.RUNTIME_ROOT + "/usr/bin/vvp", "-M", worker.BASE_DIRECTORY, "-sdf-verbose", "simulation.vvp"]]
        for argv in bad:
            with self.subTest(argv=argv), self.assertRaises(worker.WorkerError):
                worker.validate_operation(argv, cwd)
        for bad_cwd in (worker.WORK_ROOT, worker.WORK_ROOT + "/original-job-X/child", worker.WORK_ROOT + "/original-job-X/../Y", "/tmp/original-job-SOFTWARE_QA"):
            with self.subTest(cwd=bad_cwd), self.assertRaises(worker.WorkerError):
                worker.validate_operation(list(worker.COMPILE_ARGV), bad_cwd)

    def test_host_refuses_unbound_commands_before_starting_a_process(self):
        with patch.object(host.subprocess, "Popen") as popen:
            for config in ({}, {**worker.CONFIGURATION, "extra": True}, {**worker.CONFIGURATION, "distribution": "other"}):
                with self.subTest(config=config), self.assertRaises(DomainError):
                    host.execute(["untrusted"], config, ROOT / ".work/m2k/dynamic/original-job-SOFTWARE_QA", "compile", None, 10)
            with self.assertRaises(DomainError):
                host.execute(["untrusted"], worker.CONFIGURATION, ROOT / ".work/m2k/dynamic/original-job-SOFTWARE_QA", "compile", None, 10)
            popen.assert_not_called()

    def test_frozen_request_rejects_changed_hash_schema_configuration_and_time(self):
        with tempfile.TemporaryDirectory(prefix="postlayout-guard-SOFTWARE-QA-", dir=self.qa_temp) as temp:
            folder = Path(temp)
            source = folder / "source.py"
            source.write_bytes(b"SOFTWARE QA worker snapshot, never executed")
            source_sha = worker.digest(source.read_bytes())
            request = {"version": worker.VERSION, "argv": list(worker.COMPILE_ARGV), "cwd": worker.WORK_ROOT + "/original-job-SOFTWARE_QA",
                       "timeout_seconds": 10, "worker_sha256": source_sha, "input_files": {name: "a" * 64 for name in worker.COMPILE_INPUTS},
                       "configuration_sha256": object_hash(worker.CONFIGURATION)}
            path = folder / "request.json"
            def load(value, *, request_hash=None):
                path.write_bytes(worker.canonical(value))
                return worker.frozen_request(path, request_hash or worker.digest(path.read_bytes()), source_sha, source)
            # Only filesystem byte checks are stubbed here; argv/cwd have their
            # own direct validation test above. This fixture launches nothing.
            with patch.object(worker, "validate_inputs"), patch.object(worker, "validate_tool_files"):
                self.assertEqual(load(request), request)
                mutations = [{**request, "extra": "ignored"}, {**request, "configuration_sha256": "0" * 64},
                             {**request, "timeout_seconds": True}, {**request, "timeout_seconds": 7201},
                             {**request, "worker_sha256": "0" * 64}]
                for changed in mutations:
                    with self.subTest(changed=changed), self.assertRaises(worker.WorkerError):
                        load(changed)
                with self.assertRaises(worker.WorkerError):
                    load(request, request_hash="0" * 64)

    def test_group_cleanup_does_not_equate_leader_exit_with_child_termination(self):
        with tempfile.TemporaryDirectory(prefix="postlayout-proc-SOFTWARE-QA-", dir=self.qa_temp) as temp:
            proc = Path(temp)
            now, signals = [0.0], []
            def process(pid, state="S", birth=500):
                folder = proc / str(pid)
                folder.mkdir(exist_ok=True)
                fields = [state, "1", "100", "100"] + ["0"] * 15 + [str(birth)]
                (folder / "stat").write_text(str(pid) + " (QA name with ) parenthesis) " + " ".join(fields))
            process(100)
            process(101, birth=501)
            def sender(group, signal):
                signals.append((group, signal))
                if signal == worker.TERM_SIGNAL:
                    (proc / "100/stat").unlink()
                    (proc / "100").rmdir()
                elif signal == worker.KILL_SIGNAL:
                    process(101, state="Z", birth=501)
            result = worker.terminate_group(100, proc_root=proc, clock=lambda: now[0], sleeper=lambda seconds: now.__setitem__(0, now[0] + seconds), sender=sender)
            self.assertEqual(signals, [(100, worker.TERM_SIGNAL), (100, worker.KILL_SIGNAL)])
            self.assertTrue(result["verified_terminated"])
            self.assertEqual(result["after"], [])

    def test_process_birth_binding_includes_input_and_configuration(self):
        request = {"argv": list(worker.COMPILE_ARGV), "cwd": worker.WORK_ROOT + "/original-job-SOFTWARE_QA",
                   "input_files": {"input.nl.v": "a" * 64}, "configuration_sha256": object_hash(worker.CONFIGURATION)}
        binding = worker.identity_fields(request, "b" * 64, "c" * 64)
        self.assertEqual(binding["input_files"], request["input_files"])
        self.assertEqual(binding["configuration_sha256"], request["configuration_sha256"])
        self.assertEqual(binding["version"], worker.VERSION)

    def test_v2_adds_only_exact_byte_pinned_readonly_iopath_plugin(self):
        self.assertEqual(host.sha(host.WORKER_V2_SOURCE), host.WORKER_V2_SHA256)
        cwd = worker_v2.WORK_ROOT + "/original-job-SOFTWARE_QA"
        argv = list(worker_v2.simulation_argv(cwd))
        self.assertEqual(argv, [worker_v2.RUNTIME_ROOT + "/usr/bin/vvp", "-M", cwd, "-m", "hullcirq_readback", "simulation.vvp", "-sdf-verbose",
                                "+hullcirq_readback_manifest=sdf-readback-manifest.tsv"])
        self.assertEqual(worker_v2.validate_operation(argv, cwd), worker_v2.COMPILE_INPUTS + ("simulation.vvp", *worker_v2.PLUGIN_SHA256))
        self.assertEqual(worker_v2.PLUGIN_SHA256["hullcirq_readback.vpi"], "3a5c10e7bcfc12e98cd37a2c16a74ffd2503385f7cb8851d8d2aea712bbe97e3")
        self.assertEqual(worker_v2.PLUGIN_SHA256["sdf-readback-manifest.tsv"], "cf5d42a93b750a3cc2339c574d36db88fa58931279b95ca86a9904fd7da964da")
        self.assertEqual(worker_v2.COMPILE_ARGV, worker.COMPILE_ARGV)
        self.assertEqual(host.fixed_worker_definition("v2")["VERSION"], worker_v2.VERSION)
        for altered in (argv + ["-m", "arbitrary"], [value.replace("hullcirq_readback", "unknown") for value in argv],
                        [value.replace("sdf-readback-manifest.tsv", "unbound.tsv") for value in argv]):
            with self.subTest(argv=altered), self.assertRaises(worker_v2.WorkerError):
                worker_v2.validate_operation(altered, cwd)
        with self.assertRaises(DomainError):
            host.fixed_worker_definition("arbitrary")


if __name__ == "__main__":
    unittest.main()
