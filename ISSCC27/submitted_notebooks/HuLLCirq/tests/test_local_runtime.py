"""Focused software lifecycle checks; no service, model inference, or EDA run."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from hullcirq.domain import DomainError
from hullcirq.local_runtime import LocalRuntimeController
import hullcirq.local_runtime as runtime


class SoftwareProcess:
    pid = 481516

    def __init__(self):
        self.returncode = None
        self.terminations = 0
        self.kills = 0
        self.timeout_once = False

    def poll(self):
        return self.returncode

    def terminate(self):
        self.terminations += 1
        if not self.timeout_once:
            self.returncode = 0

    def kill(self):
        self.kills += 1
        self.returncode = -9

    def wait(self, timeout):
        if self.timeout_once and self.kills == 0:
            raise subprocess.TimeoutExpired("software fixture", timeout)
        return self.returncode


class LocalRuntimeTests(unittest.TestCase):
    def setUp(self):
        (ROOT / ".work").mkdir(exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=ROOT / ".work")
        self.root = Path(self.temporary.name)
        self.exe = self.root / "software-ollama.exe"
        self.exe.write_bytes(b"SOFTWARE QA ONLY; NEVER EXECUTED")
        self.controller = LocalRuntimeController(self.root, self.exe)
        self.process = SoftwareProcess()
        self.closed = False

    def tearDown(self):
        if not self.closed:
            self.controller.close()
        self.temporary.cleanup()

    def settle(self):
        worker = self.controller._worker
        if worker:
            worker.join(2)
            self.assertFalse(worker.is_alive(), "Software lifecycle worker did not terminate")
        with self.controller._lock:
            return self.controller._snapshot()

    def prepared(self, model=runtime.MODEL):
        directory = self.controller.model_directory
        manifest_path = (directory / "manifests" / "registry.ollama.ai" / "library").joinpath(*runtime.PREPARED_MODELS[model]["manifest_path"])
        manifest_path.parent.mkdir(parents=True)
        blobs = directory / "blobs"
        blobs.mkdir(exist_ok=True)
        parts = []
        for content in (b"QA config", b"QA tiny model; not a model weight"):
            digest = hashlib.sha256(content).hexdigest()
            (blobs / f"sha256-{digest}").write_bytes(content)
            parts.append({"digest": f"sha256:{digest}", "size": len(content)})
        raw = json.dumps({"config": parts[0], "layers": [parts[1]]}).encode()
        manifest_path.write_bytes(raw)
        return manifest_path, hashlib.sha256(raw).hexdigest()

    def mocks(self, probe=None):
        patches = [patch.object(self.controller, "_probe", side_effect=probe or ["stopped", "ready"]),
                   patch.object(self.controller, "_port_occupied", return_value=False),
                   patch.object(self.controller, "_prepared_model"),
                   patch("hullcirq.local_runtime.subprocess.run", return_value=subprocess.CompletedProcess([], 0, "ollama version is 0.32.15\n", "")),
                   patch("hullcirq.local_runtime.subprocess.Popen", return_value=self.process)]
        values = [item.start() for item in patches]
        for item in patches:
            self.addCleanup(item.stop)
        return values

    def test_profile_support_is_specific_to_prepared_loopback_model(self):
        profile = {"execution_location": "Local", "api_type": "chat_completions",
                   "base_url": "http://localhost:11435/v1/", "model": "qwen3:8b"}
        self.assertTrue(LocalRuntimeController.supports_profile(profile))
        self.assertTrue(LocalRuntimeController.supports_profile(profile | {"model": "qwen2.5-coder:7b"}))
        for key, value in (("execution_location", "Network"), ("model", "different-model"),
                           ("base_url", "http://remote.example:11435/v1"),
                           ("base_url", "http://token@127.0.0.1:11435/v1"),
                           ("base_url", "http://127.0.0.1:11435/v1?secret=value")):
            with self.subTest(key=key, value=value):
                self.assertFalse(LocalRuntimeController.supports_profile(profile | {key: value}))
        with self.assertRaises(DomainError) as caught:
            self.controller.start(profile | {"model": "different-model"})
        self.assertEqual(caught.exception.status, 409)
        self.assertIsNone(self.controller._worker)

    def test_external_ready_endpoint_is_visible_but_never_owned_or_stopped(self):
        with patch.object(self.controller, "_probe", return_value="ready"), patch("hullcirq.local_runtime.subprocess.Popen") as spawn:
            result = self.controller.status()
            self.assertEqual(result["state"], "Running")
            self.assertFalse(result["owned"])
            self.assertFalse(result["can_stop"])
            self.assertIsNone(result["managed_environment"])
            self.assertIsNone(result["environment_source"])
            self.controller.start()
            self.assertEqual(self.settle()["state"], "Running")
            with self.assertRaises(DomainError) as caught:
                self.controller.stop()
            self.assertEqual(caught.exception.code, "local_runtime_external")
            self.controller.close()
            self.closed = True
            spawn.assert_not_called()

    def test_unrecognized_occupied_port_never_spawns_or_terminates_existing_process(self):
        with patch.object(self.controller, "_probe", return_value="occupied"), patch("hullcirq.local_runtime.subprocess.Popen") as spawn:
            self.controller.start()
            result = self.settle()
            self.assertEqual(result["state"], "Failed")
            self.assertFalse(result["owned"])
            with self.assertRaises(DomainError):
                self.controller.stop()
            spawn.assert_not_called()

    def test_start_launches_fixed_command_and_child_only_environment(self):
        mocks = self.mocks()
        previous_host = os.environ.get("OLLAMA_HOST")
        self.controller.start()
        result = self.settle()
        self.assertEqual(result["state"], "Running")
        self.assertTrue(result["owned"])
        self.assertEqual(result["pid"], self.process.pid)
        arguments, options = mocks[-1].call_args
        self.assertEqual(arguments[0], [str(self.exe), "serve"])
        self.assertFalse(options["shell"])
        self.assertEqual(options["env"]["OLLAMA_HOST"], "127.0.0.1:11435")
        self.assertEqual(options["env"]["OLLAMA_MODELS"], str(self.controller.model_directory))
        self.assertEqual(options["env"]["OLLAMA_NO_CLOUD"], "1")
        self.assertEqual(options["env"]["OLLAMA_API_KEY"], "")
        self.assertEqual(os.environ.get("OLLAMA_HOST"), previous_host)
        self.assertTrue(Path(result["log_path"]).is_file())
        self.controller.stop()
        self.assertEqual(self.settle()["state"], "Stopped")
        self.assertEqual(self.process.terminations, 1)

    def test_managed_cache_defaults_and_exact_launch_metadata(self):
        with patch.dict(os.environ, {}, clear=True):
            mocks = self.mocks()
            self.controller.start()
            result = self.settle()
            expected = {"OLLAMA_FLASH_ATTENTION": "1", "OLLAMA_KV_CACHE_TYPE": "q8_0", "OLLAMA_CONTEXT_LENGTH": "16384"}
            self.assertEqual(result["state"], "Running")
            self.assertEqual(result["managed_environment"], expected)
            self.assertEqual(result["environment_source"], "owned_child_launch_environment")
            self.assertEqual(result["context_length_source"], "default")
            child_environment = mocks[-1].call_args.kwargs["env"]
            self.assertEqual({key: child_environment[key] for key in expected}, expected)
            self.assertNotIn("OLLAMA_FLASH_ATTENTION", os.environ)
            self.assertNotIn("OLLAMA_KV_CACHE_TYPE", os.environ)
            # Returned JSON metadata cannot mutate the captured launch settings.
            result["managed_environment"]["OLLAMA_KV_CACHE_TYPE"] = "changed by viewer"
            self.assertEqual(self.controller.status()["managed_environment"], expected)
            self.controller.stop()
            stopped = self.settle()
            self.assertIsNone(stopped["managed_environment"])
            self.assertIsNone(stopped["environment_source"])
            self.assertIsNone(stopped["context_length_source"])

    def test_explicit_user_cache_and_flash_environment_values_are_preserved(self):
        inherited = {"OLLAMA_FLASH_ATTENTION": "0", "OLLAMA_KV_CACHE_TYPE": "f16"}
        with patch.dict(os.environ, inherited, clear=True):
            mocks = self.mocks()
            self.controller.start()
            result = self.settle()
            child_environment = mocks[-1].call_args.kwargs["env"]
            for key, value in inherited.items():
                self.assertEqual(child_environment[key], value)
                self.assertEqual(result["managed_environment"][key], value)
                self.assertEqual(os.environ[key], value)
            self.assertEqual(result["managed_environment"]["OLLAMA_CONTEXT_LENGTH"], runtime.MANAGED_CONTEXT_LENGTH)

    def test_partial_override_keeps_unset_cache_default(self):
        with patch.dict(os.environ, {"OLLAMA_FLASH_ATTENTION": "false"}, clear=True):
            self.mocks()
            self.controller.start()
            result = self.settle()
            self.assertEqual(result["managed_environment"], {
                "OLLAMA_FLASH_ATTENTION": "false", "OLLAMA_KV_CACHE_TYPE": "q8_0", "OLLAMA_CONTEXT_LENGTH": "16384"})

    def test_explicit_context_override_is_passed_unchanged_and_recorded_with_cache_defaults(self):
        with patch.dict(os.environ, {"OLLAMA_CONTEXT_LENGTH": "20480"}, clear=True):
            mocks = self.mocks()
            self.controller.start()
            result = self.settle()
            self.assertEqual(result["state"], "Running")
            self.assertEqual(result["managed_environment"], {
                "OLLAMA_FLASH_ATTENTION": "1", "OLLAMA_KV_CACHE_TYPE": "q8_0", "OLLAMA_CONTEXT_LENGTH": "20480"})
            self.assertEqual(mocks[-1].call_args.kwargs["env"]["OLLAMA_CONTEXT_LENGTH"], "20480")
            self.assertEqual(os.environ["OLLAMA_CONTEXT_LENGTH"], "20480")
            self.assertEqual(result["context_length_source"], "parent_environment")
            self.assertNotIn("OLLAMA_FLASH_ATTENTION", os.environ)
            self.assertNotIn("OLLAMA_KV_CACHE_TYPE", os.environ)

    def test_coder_cold_start_uses_selected_profile_context_and_records_source(self):
        profile = {"model": "qwen2.5-coder:7b", "execution_location": "Local", "api_type": "chat_completions",
                   "base_url": "http://127.0.0.1:11435/v1", "context_window": 32768}
        with patch.dict(os.environ, {}, clear=True):
            mocks = self.mocks()
            self.controller.start(profile)
            result = self.settle()
            self.assertEqual(result["state"], "Running")
            self.assertEqual(result["model"], profile["model"])
            self.assertEqual(result["managed_environment"]["OLLAMA_CONTEXT_LENGTH"], "32768")
            self.assertEqual(result["context_length_source"], "saved_provider_profile")
            self.assertEqual(mocks[-1].call_args.kwargs["env"]["OLLAMA_CONTEXT_LENGTH"], "32768")
            self.assertNotIn("OLLAMA_CONTEXT_LENGTH", os.environ)
            self.assertEqual(self.controller._launch_profile_context, {"context_window": 32768})
            # A later profile edit cannot alter an already owned launch.
            profile["context_window"] = 4096
            self.assertEqual(self.controller.start(profile)["managed_environment"]["OLLAMA_CONTEXT_LENGTH"], "32768")
            self.assertEqual(mocks[-1].call_count, 1)

    def test_explicit_context_override_wins_over_saved_profile_context(self):
        profile = {"model": "qwen2.5-coder:7b", "execution_location": "Local",
                   "base_url": "http://localhost:11435/v1", "context_window": 32768}
        with patch.dict(os.environ, {"OLLAMA_CONTEXT_LENGTH": "20480"}, clear=True):
            mocks = self.mocks()
            self.controller.start(profile)
            result = self.settle()
            self.assertEqual(result["managed_environment"]["OLLAMA_CONTEXT_LENGTH"], "20480")
            self.assertEqual(result["context_length_source"], "parent_environment")
            self.assertEqual(mocks[-1].call_args.kwargs["env"]["OLLAMA_CONTEXT_LENGTH"], "20480")
            self.assertEqual(profile["context_window"], 32768)

    def test_invalid_saved_profile_context_fails_closed_without_environment_override(self):
        for value in (None, True, "32768", 0, 1023, 131073):
            with self.subTest(value=value), patch.dict(os.environ, {}, clear=True):
                mocks = self.mocks(probe=["stopped"])
                profile = {"model": "qwen2.5-coder:7b", "execution_location": "Local",
                           "base_url": "http://localhost:11435/v1", "context_window": value}
                self.controller.start(profile)
                result = self.settle()
                self.assertEqual(result["state"], "Failed")
                self.assertFalse(result["owned"])
                self.assertIsNone(result["context_length_source"])
                mocks[-1].assert_not_called()

    def test_invalid_explicit_context_fails_closed_before_spawn_or_log_creation(self):
        for value in ("", "not-an-integer", "20480.0", " 20480", "+20480", "-1", "0", "1023", "131073", "99999999"):
            with self.subTest(value=value), patch.dict(os.environ, {"OLLAMA_CONTEXT_LENGTH": value}, clear=True):
                mocks = self.mocks(probe=["stopped"])
                self.controller.start()
                result = self.settle()
                self.assertEqual(result["state"], "Failed")
                self.assertFalse(result["owned"])
                self.assertIn("OLLAMA_CONTEXT_LENGTH", result["message"])
                self.assertIsNone(result["managed_environment"])
                self.assertFalse((self.root / ".work" / "local_runtime").exists())
                self.assertEqual(os.environ["OLLAMA_CONTEXT_LENGTH"], value)
                mocks[-1].assert_not_called()

    def test_explicit_empty_environment_values_are_not_replaced(self):
        inherited = {"OLLAMA_FLASH_ATTENTION": "", "OLLAMA_KV_CACHE_TYPE": ""}
        with patch.dict(os.environ, inherited, clear=True):
            self.mocks()
            self.controller.start()
            result = self.settle()
            for key, value in inherited.items():
                self.assertEqual(result["managed_environment"][key], value)
            self.assertEqual(result["environment_source"], "owned_child_launch_environment")

    def test_status_does_not_start_service_or_inference_to_apply_defaults(self):
        before = os.environ.copy()
        with patch.object(self.controller, "_probe", return_value="stopped"), \
                patch("hullcirq.local_runtime.subprocess.run") as run, \
                patch("hullcirq.local_runtime.subprocess.Popen") as spawn:
            result = self.controller.status()
            self.assertEqual(result["state"], "Stopped")
            self.assertIsNone(result["managed_environment"])
            self.assertIsNone(result["environment_source"])
            run.assert_not_called()
            spawn.assert_not_called()
        self.assertEqual(os.environ, before)

    def test_concurrent_start_is_idempotent_and_status_does_not_wait_for_preflight(self):
        mocks = self.mocks()
        entered, release = threading.Event(), threading.Event()

        def held_check():
            entered.set()
            release.wait(2)

        with patch.object(self.controller, "_check_executable", side_effect=held_check):
            self.assertEqual(self.controller.start()["state"], "Starting")
            self.assertTrue(entered.wait(1))
            worker = self.controller._worker
            before = time.monotonic()
            for _ in range(10):
                self.assertEqual(self.controller.start()["state"], "Starting")
                self.assertEqual(self.controller.status()["state"], "Starting")
            self.assertLess(time.monotonic() - before, .25)
            self.assertIs(self.controller._worker, worker)
            release.set()
            self.assertEqual(self.settle()["state"], "Running")
        self.assertEqual(mocks[-1].call_count, 1)

    def test_cancel_while_starting_does_not_launch_a_process(self):
        mocks = self.mocks()
        entered, release = threading.Event(), threading.Event()

        def held_check():
            entered.set()
            release.wait(2)

        with patch.object(self.controller, "_check_executable", side_effect=held_check):
            self.controller.start()
            self.assertTrue(entered.wait(1))
            self.assertEqual(self.controller.stop()["state"], "Stopping")
            release.set()
            self.assertEqual(self.settle()["state"], "Stopped")
        mocks[-1].assert_not_called()

    def test_missing_prepared_model_fails_without_download_or_spawn(self):
        mocks = self.mocks()
        mocks[2].side_effect = DomainError("local_runtime_model_missing", "Prepared model missing", 409)
        self.controller.start()
        result = self.settle()
        self.assertEqual(result["state"], "Unavailable")
        self.assertTrue(result["can_start"], "Preparation can be retried after the model has been installed")
        mocks[-1].assert_not_called()

    def test_cancelled_old_start_cannot_overwrite_a_new_start(self):
        mocks = self.mocks()
        old_probe, release_old = threading.Event(), threading.Event()
        new_check, release_new = threading.Event(), threading.Event()
        probes, checks = [], []
        second_process = SoftwareProcess()
        second_process.pid += 1

        def probe():
            probes.append(True)
            if len(probes) == 2:
                old_probe.set()
                release_old.wait(2)
                return "stopped"
            return "ready" if len(probes) == 4 else "stopped"

        def check():
            checks.append(True)
            if len(checks) == 2:
                new_check.set()
                release_new.wait(2)

        mocks[0].side_effect = probe
        mocks[-1].side_effect = [self.process, second_process]
        with patch.object(self.controller, "_check_executable", side_effect=check):
            self.controller.start()
            self.assertTrue(old_probe.wait(1))
            old_worker = self.controller._worker
            self.controller.stop()
            self.assertEqual(self.settle()["state"], "Stopped")
            self.controller.start()
            self.assertTrue(new_check.wait(1))
            release_old.set()
            old_worker.join(1)
            self.assertFalse(old_worker.is_alive())
            self.assertEqual(self.controller.status()["state"], "Starting")
            release_new.set()
            result = self.settle()
        self.assertEqual(result["state"], "Running")
        self.assertEqual(result["pid"], second_process.pid)
        self.assertIs(self.controller._process, second_process)
        self.assertEqual(second_process.terminations, 0)

    def test_manifest_and_blob_size_checked_without_hashing_model_blob(self):
        manifest, digest = self.prepared()
        fixture_spec = {**runtime.PREPARED_MODELS[runtime.MODEL], "manifest_sha256": digest}
        with patch.dict(runtime.PREPARED_MODELS, {runtime.MODEL: fixture_spec}):
            self.controller._prepared_model()
            blob = next((self.controller.model_directory / "blobs").iterdir())
            blob.write_bytes(b"wrong size")
            with self.assertRaises(DomainError):
                self.controller._prepared_model()
        manifest.write_bytes(manifest.read_bytes() + b" ")
        with patch.dict(runtime.PREPARED_MODELS, {runtime.MODEL: fixture_spec}), self.assertRaises(DomainError):
            self.controller._prepared_model()

    def test_coder_manifest_and_blob_checks_use_its_own_trusted_pin(self):
        model = "qwen2.5-coder:7b"
        self.controller._model = model
        manifest, digest = self.prepared(model)
        # A well-formed but untrusted manifest is not accepted or downloaded.
        with self.assertRaises(DomainError):
            self.controller._prepared_model()
        fixture_spec = {**runtime.PREPARED_MODELS[model], "manifest_sha256": digest}
        with patch.dict(runtime.PREPARED_MODELS, {model: fixture_spec}):
            self.controller._prepared_model()
            blob = next((self.controller.model_directory / "blobs").iterdir())
            blob.write_bytes(b"different size")
            with self.assertRaises(DomainError):
                self.controller._prepared_model()
        self.assertEqual(self.controller._model, model)

    def test_coder_missing_manifest_cannot_fall_back_to_qwen3_or_spawn(self):
        self.prepared()
        actual_check = self.controller._prepared_model
        mocks = self.mocks(probe=["stopped"])
        mocks[2].side_effect = actual_check
        self.controller.start({"model": "qwen2.5-coder:7b", "execution_location": "Local", "base_url": "http://127.0.0.1:11435/v1"})
        result = self.settle()
        self.assertEqual(result["state"], "Unavailable")
        self.assertIn("qwen2.5-coder:7b", result["message"])
        self.assertFalse(result["owned"])
        mocks[-1].assert_not_called()

    def test_model_probe_checks_selected_coder_and_does_not_accept_only_qwen3(self):
        self.controller._model = "qwen2.5-coder:7b"
        for listed, expected in (([runtime.MODEL], "missing_model"), (["qwen2.5-coder:7b"], "ready")):
            with self.subTest(listed=listed), patch.object(self.controller, "_http_json", side_effect=[{"version": runtime.VERSION}, {"data": [{"id": model} for model in listed]}]) as metadata:
                self.assertEqual(self.controller._probe(), expected)
                self.assertEqual([call.args[0] for call in metadata.call_args_list], ["/api/version", "/v1/models"])

    def test_wrong_binary_version_does_not_spawn(self):
        mocks = self.mocks()
        mocks[3].return_value = subprocess.CompletedProcess([], 0, "ollama version is 9.9.9", "")
        self.controller.start()
        result = self.settle()
        self.assertEqual(result["state"], "Failed")
        self.assertIn("0.32.15", result["error"])
        mocks[-1].assert_not_called()

    def test_binary_version_check_targets_managed_endpoint_without_mutating_parent(self):
        with patch.dict(os.environ, {"OLLAMA_HOST": "127.0.0.1:11434"}, clear=False):
            mocks = self.mocks()
            self.controller.start()
            self.assertEqual(self.settle()["state"], "Running")
            self.assertEqual(mocks[3].call_args.kwargs["env"]["OLLAMA_HOST"], "127.0.0.1:11435")
            self.assertEqual(os.environ["OLLAMA_HOST"], "127.0.0.1:11434")

    def test_owned_startup_exit_is_failed_and_not_reported_running(self):
        self.mocks()
        self.process.returncode = 7
        self.controller.start()
        result = self.settle()
        self.assertEqual(result["state"], "Failed")
        self.assertFalse(result["owned"])
        self.assertIn("7", result["error"])

    def test_owned_startup_timeout_cleans_up_process(self):
        self.mocks(probe=["stopped"])
        with patch.object(runtime, "STARTUP_TIMEOUT", 0):
            self.controller.start()
            result = self.settle()
        self.assertEqual(result["state"], "Failed")
        self.assertFalse(result["owned"])
        self.assertEqual(self.process.terminations, 1)

    def test_owned_running_exit_is_visible_and_restartable(self):
        self.mocks()
        self.controller.start()
        self.assertEqual(self.settle()["state"], "Running")
        self.process.returncode = 8
        result = self.controller.status()
        self.assertEqual(result["state"], "Failed")
        self.assertTrue(result["can_start"])
        self.assertFalse(result["owned"])

    def test_stop_escalates_only_the_owned_handle_after_bounded_wait(self):
        self.mocks()
        self.controller.start()
        self.settle()
        self.process.timeout_once = True
        self.controller.stop()
        result = self.settle()
        self.assertEqual(result["state"], "Stopped")
        self.assertEqual(self.process.terminations, 1)
        self.assertEqual(self.process.kills, 1)

    def test_close_cleans_owned_process_and_rejects_new_start(self):
        self.mocks()
        self.controller.start()
        self.settle()
        self.controller.close()
        self.closed = True
        self.assertEqual(self.process.terminations, 1)
        self.assertFalse(self.controller.status()["can_start"])
        with self.assertRaises(DomainError):
            self.controller.start()

    def test_probe_uses_metadata_gets_and_requires_version_and_model(self):
        with patch.object(self.controller, "_http_json", side_effect=[{"version": runtime.VERSION}, {"data": [{"id": runtime.MODEL}]}]) as metadata:
            self.assertEqual(self.controller._probe(), "ready")
            self.assertEqual([call.args[0] for call in metadata.call_args_list], ["/api/version", "/v1/models"])
        with patch.object(self.controller, "_http_json", return_value={"version": "9.9.9"}):
            self.assertEqual(self.controller._probe(), "incompatible")
        with patch.object(self.controller, "_http_json", side_effect=[{"version": runtime.VERSION}, {"data": []}]):
            self.assertEqual(self.controller._probe(), "missing_model")


if __name__ == "__main__":
    unittest.main()
