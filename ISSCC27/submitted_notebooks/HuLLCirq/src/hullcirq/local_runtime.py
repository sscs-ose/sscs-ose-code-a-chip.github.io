"""Manage the prepared local Ollama service without model download or inference.

Only a process launched by this controller can be stopped by it. Endpoint
discovery never grants ownership of another process, including after restart.
"""

from __future__ import annotations

import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import threading
import time
from urllib.parse import urlsplit
import uuid

from .domain import DomainError

HOST = "127.0.0.1"
PORT = 11435
ENDPOINT = f"http://{HOST}:{PORT}/v1"
MODEL = "qwen3:8b"
VERSION = "0.32.15"
MANIFEST_SHA256 = "500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41"
PREPARED_MODELS = {
    MODEL: {"manifest_path": ("qwen3", "8b"), "manifest_sha256": MANIFEST_SHA256},
    "qwen2.5-coder:7b": {"manifest_path": ("qwen2.5-coder", "7b"),
                         "manifest_sha256": "dae161e27b0e90dd1856c8bb3209201fd6736d8eb66298e75ed87571486f4364"},
}
STARTUP_TIMEOUT = 120.0
HTTP_TIMEOUT = 0.5
MAX_METADATA_BYTES = 256 * 1024
MANAGED_CONTEXT_LENGTH = "16384"
MIN_MANAGED_CONTEXT_LENGTH = 1024
MAX_MANAGED_CONTEXT_LENGTH = 131072
DEFAULT_KV_CACHE_TYPE = "q8_0"
DEFAULT_FLASH_ATTENTION = "1"


class LocalRuntimeController:
    """Server-wide service lifecycle, independent of the active circuit project."""

    def __init__(self, project_root: Path, ollama_path: Path | str | None = None):
        self.root = Path(project_root).resolve()
        self.model_directory = self.root / ".work" / "m2" / "ollama-models"
        self.executable = self._discover_executable(ollama_path)
        self._lock = threading.RLock()
        self._process = None
        self._worker = None
        self._cancel = threading.Event()
        self._closed = False
        self._external = False
        self._log_path = None
        self._managed_environment = None
        self._managed_context_source = None
        self._model = MODEL
        self._launch_profile_context = {}
        self._state = "Stopped" if self.executable else "Unavailable"
        self._message = "Local service is stopped." if self.executable else "Ollama is not installed. Prepare the local runtime before starting it."
        self._error = None
        self._probe_at = float("-inf")
        self._operation = 0
        self._probe_lock = threading.Lock()

    @staticmethod
    def _discover_executable(explicit):
        if explicit is not None:
            candidate = Path(explicit).expanduser()
            return candidate.resolve() if candidate.is_file() else None
        local = os.environ.get("LOCALAPPDATA")
        candidates = ([Path(local) / "Programs" / "Ollama" / "ollama.exe"] if local else [])
        candidates.append(Path.home() / "AppData" / "Local" / "Programs" / "Ollama" / "ollama.exe")
        discovered = shutil.which("ollama")
        if discovered:
            candidates.append(Path(discovered))
        return next((path.resolve() for path in candidates if path.is_file()), None)

    @staticmethod
    def supports_profile(profile: dict | None) -> bool:
        if not isinstance(profile, dict):
            return False
        try:
            parsed = urlsplit(profile.get("base_url", ""))
            return (profile.get("execution_location") == "Local"
                    and profile.get("api_type", "chat_completions") == "chat_completions"
                    and profile.get("model") in PREPARED_MODELS
                    and parsed.scheme == "http"
                    and parsed.hostname in (HOST, "localhost") and parsed.port == PORT
                    and parsed.path.rstrip("/") == "/v1"
                    and not parsed.username and not parsed.password
                    and not parsed.query and not parsed.fragment)
        except (TypeError, ValueError):
            return False

    def _snapshot(self):
        process = self._process
        owned = process is not None and process.poll() is None
        return {"state": self._state, "owned": owned,
                "pid": process.pid if owned else None,
                "endpoint": ENDPOINT, "model": self._model,
                "message": self._message, "error": self._error,
                "can_start": not self._closed and not owned and self.executable is not None and self._state in ("Stopped", "Failed", "Unavailable"),
                "can_stop": not self._closed and (owned or self._state == "Starting") and self._state != "Stopping",
                "log_path": str(self._log_path) if self._log_path else None,
                # Exact launch values, not an observation of allocated KV memory.
                # External services cannot inherit settings or ownership by discovery.
                "managed_environment": dict(self._managed_environment) if owned and self._managed_environment is not None else None,
                "environment_source": "owned_child_launch_environment" if owned and self._managed_environment is not None else None,
                "context_length_source": self._managed_context_source if owned else None}

    def _set(self, state, message, error=None):
        self._state, self._message, self._error = state, message, error

    @staticmethod
    def _http_json(path):
        connection = http.client.HTTPConnection(HOST, PORT, timeout=HTTP_TIMEOUT)
        try:
            connection.request("GET", path, headers={"Accept": "application/json"})
            response = connection.getresponse()
            if response.status != 200:
                return None
            raw = response.read(MAX_METADATA_BYTES + 1)
            if len(raw) > MAX_METADATA_BYTES:
                return None
            value = json.loads(raw)
            return value if isinstance(value, dict) else None
        except (OSError, ValueError, http.client.HTTPException):
            return None
        finally:
            connection.close()

    @staticmethod
    def _port_occupied():
        try:
            with socket.create_connection((HOST, PORT), timeout=HTTP_TIMEOUT):
                return True
        except OSError:
            return False

    def _probe(self):
        version = self._http_json("/api/version")
        if version is None:
            return "occupied" if self._port_occupied() else "stopped"
        if version.get("version") != VERSION:
            return "incompatible"
        models = self._http_json("/v1/models")
        if not models or not isinstance(models.get("data"), list):
            return "occupied"
        if any(isinstance(item, dict) and item.get("id") == self._model for item in models["data"]):
            return "ready"
        return "missing_model"

    def _apply_probe(self, probe):
        self._external = probe != "stopped"
        if probe == "ready":
            self._set("Running", "Local service is running outside HuLLCirq. Stop it in the application that started it.")
        elif probe == "stopped":
            self._set("Stopped" if self.executable else "Unavailable",
                      "Local service is stopped." if self.executable else "Ollama is not installed. Prepare the local runtime before starting it.")
        elif probe == "incompatible":
            self._set("Failed", "Port 11435 has a different runtime version. The existing service was left running.", "The prepared runtime requires Ollama 0.32.15.")
        elif probe == "missing_model":
            self._set("Failed", f"The existing local service does not expose {self._model}. No model was downloaded.", "Required model is unavailable at the endpoint.")
        else:
            self._set("Failed", "Port 11435 is occupied by an unrecognized or unready service. The existing process was left running.", "The prepared local endpoint could not be verified.")

    def status(self):
        """Inspect bounded metadata only; never send a prompt or mutate a project."""
        with self._lock:
            process = self._process
            if process is not None and process.poll() is not None and self._state == "Running":
                code = process.returncode
                self._process = None
                self._set("Failed", "The local service exited. Review its log before restarting.", f"Ollama exited with code {code}.")
                self._probe_at = time.monotonic()
            if self._closed or self._state in ("Starting", "Stopping") or self._process is not None:
                return self._snapshot()
            if time.monotonic() - self._probe_at < 1.0:
                return self._snapshot()
            operation = self._operation
        if not self._probe_lock.acquire(blocking=False):
            with self._lock:
                return self._snapshot()
        try:
            probe = self._probe()
            with self._lock:
                if not self._closed and operation == self._operation and self._process is None:
                    # Keep actionable local startup failures until an endpoint is found.
                    if probe != "stopped" or self._state not in ("Failed", "Unavailable"):
                        self._apply_probe(probe)
                    self._probe_at = time.monotonic()
                return self._snapshot()
        finally:
            self._probe_lock.release()

    def start(self, profile=None):
        if profile is not None and not self.supports_profile(profile):
            raise DomainError("local_runtime_profile_unsupported", "GUI startup supports prepared Local qwen3:8b or qwen2.5-coder:7b at http://127.0.0.1:11435/v1. Other models and endpoints remain externally managed.", 409)
        with self._lock:
            if self._closed:
                raise DomainError("local_runtime_closed", "The GUI service is shutting down.", 409)
            if self._state in ("Starting", "Stopping") or (self._process is not None and self._process.poll() is None):
                return self._snapshot()
            self._model = profile["model"] if profile is not None else MODEL
            self._launch_profile_context = {"context_window": profile["context_window"]} if profile is not None and "context_window" in profile else {}
            self._operation += 1
            self._cancel = threading.Event()
            self._external = False
            self._set("Starting", "Checking the prepared local runtime and endpoint.")
            self._worker = threading.Thread(target=self._start_worker, args=(self._operation, self._cancel), name="hullcirq-local-runtime-start", daemon=True)
            self._worker.start()
            return self._snapshot()

    def _prepared_model(self):
        prepared = PREPARED_MODELS[self._model]
        manifest = self.model_directory / "manifests" / "registry.ollama.ai" / "library"
        manifest = manifest.joinpath(*prepared["manifest_path"])
        try:
            if not manifest.is_file() or manifest.is_symlink() or manifest.stat().st_size > MAX_METADATA_BYTES:
                raise ValueError
            raw = manifest.read_bytes()
            if hashlib.sha256(raw).hexdigest() != prepared["manifest_sha256"]:
                raise ValueError
            value = json.loads(raw)
            parts = [value["config"], *value["layers"]]
            if not parts:
                raise ValueError
            for part in parts:
                digest, size = part["digest"], part["size"]
                if (not isinstance(digest, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", digest)
                        or type(size) is not int or size < 1):
                    raise ValueError
                blob = self.model_directory / "blobs" / digest.replace(":", "-")
                if (not blob.is_file() or blob.is_symlink() or blob.stat().st_size != size
                        or not blob.resolve().is_relative_to(self.model_directory.resolve())):
                    raise ValueError
        except (OSError, ValueError, TypeError, KeyError):
            raise DomainError("local_runtime_model_missing", f"The pinned {self._model} model is missing or its manifest/size differs. Prepare the recorded local runtime first; no model was downloaded.", 409) from None

    def _check_executable(self):
        if self.executable is None or not self.executable.is_file():
            raise DomainError("local_runtime_unavailable", "Ollama is not installed. Prepare the local runtime before starting it.", 409)
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        environment = os.environ.copy()
        # `ollama --version` also reports the server found through OLLAMA_HOST.
        # Point the preflight at HuLLCirq's managed endpoint so an unrelated
        # default service on port 11434 cannot make a pinned client look wrong.
        environment["OLLAMA_HOST"] = f"{HOST}:{PORT}"
        try:
            result = subprocess.run([str(self.executable), "--version"], stdin=subprocess.DEVNULL,
                                    capture_output=True, text=True, timeout=5, shell=False, creationflags=flags,
                                    env=environment)
            versions = re.findall(r"\bversion(?: is|:)?\s+(\d+\.\d+\.\d+)\b", result.stdout + "\n" + result.stderr)
            if result.returncode or not versions or any(version != VERSION for version in versions):
                raise DomainError("local_runtime_version", "The prepared runtime requires Ollama 0.32.15. No service was started.", 409)
        except (OSError, subprocess.TimeoutExpired):
            raise DomainError("local_runtime_unavailable", "Ollama version check failed or timed out. No service was started.", 409) from None

    def _spawn(self):
        context_source = "default"
        context_length = MANAGED_CONTEXT_LENGTH
        if "OLLAMA_CONTEXT_LENGTH" in os.environ:
            context_length = os.environ["OLLAMA_CONTEXT_LENGTH"]
            context_source = "parent_environment"
        elif "context_window" in self._launch_profile_context:
            value = self._launch_profile_context["context_window"]
            context_length = str(value) if type(value) is int else ""
            context_source = "saved_provider_profile"
        if (not re.fullmatch(r"[0-9]{1,7}", context_length)
                or not MIN_MANAGED_CONTEXT_LENGTH <= int(context_length) <= MAX_MANAGED_CONTEXT_LENGTH):
            raise DomainError("local_runtime_context_length", "OLLAMA_CONTEXT_LENGTH must be an integer from 1,024 to 131,072. No service was started.", 409)
        log_directory = self.root / ".work" / "local_runtime"
        log_directory.mkdir(parents=True, exist_ok=True)
        log_path = log_directory / f"ollama-{uuid.uuid4().hex}.log"
        environment = os.environ.copy()
        environment.update(OLLAMA_HOST=f"{HOST}:{PORT}", OLLAMA_MODELS=str(self.model_directory),
                           OLLAMA_NO_CLOUD="1", OLLAMA_CONTEXT_LENGTH=context_length,
                           OLLAMA_NUM_PARALLEL="1", OLLAMA_API_KEY="")
        # Prepared Qwen3 runtime defaults reduce KV memory; explicit user
        # environment values remain authoritative. Never mutate the parent env.
        environment.setdefault("OLLAMA_FLASH_ATTENTION", DEFAULT_FLASH_ATTENTION)
        environment.setdefault("OLLAMA_KV_CACHE_TYPE", DEFAULT_KV_CACHE_TYPE)
        managed_environment = {key: environment[key] for key in
                               ("OLLAMA_FLASH_ATTENTION", "OLLAMA_KV_CACHE_TYPE", "OLLAMA_CONTEXT_LENGTH")}
        flags = (subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP) if os.name == "nt" else 0
        with log_path.open("xb") as log:
            process = subprocess.Popen([str(self.executable), "serve"], cwd=str(self.root), env=environment,
                                       stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                                       shell=False, creationflags=flags)
        return process, log_path, managed_environment, context_source

    @staticmethod
    def _terminate(process):
        if process is None or process.poll() is not None:
            return
        try:
            process.terminate()
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=2)
        except ProcessLookupError:
            pass

    def _start_worker(self, operation, cancel):
        process = None
        try:
            probe = self._probe()
            if probe != "stopped":
                with self._lock:
                    if operation == self._operation and not cancel.is_set():
                        self._apply_probe(probe)
                return
            if cancel.is_set():
                return
            self._check_executable()
            self._prepared_model()
            if cancel.is_set():
                return
            # Check again after preparation; never stop or replace a competing service.
            if self._port_occupied():
                with self._lock:
                    if operation == self._operation and not cancel.is_set():
                        self._apply_probe("occupied")
                return
            process, log_path, managed_environment, context_source = self._spawn()
            with self._lock:
                if operation == self._operation and not self._closed and not cancel.is_set():
                    self._process, self._log_path = process, log_path
                    self._managed_environment = managed_environment
                    self._managed_context_source = context_source
                    self._set("Starting", f"Waiting for local Ollama and {self._model} metadata.")
                else:
                    cancel.set()
            deadline = time.monotonic() + STARTUP_TIMEOUT
            while not cancel.is_set() and time.monotonic() < deadline:
                if process.poll() is not None:
                    raise DomainError("local_runtime_exit", f"Ollama exited with code {process.returncode}. Review the service log.", 409)
                probe = self._probe()
                if probe == "ready":
                    with self._lock:
                        if operation == self._operation and not cancel.is_set() and not self._closed:
                            self._set("Running", "Local Ollama is running. No inference was requested.")
                            return
                    break
                if probe in ("incompatible", "missing_model"):
                    raise DomainError("local_runtime_startup", "The started endpoint does not match the prepared Ollama version and model. Review the service log.", 409)
                cancel.wait(0.2)
            if not cancel.is_set():
                seconds = int(STARTUP_TIMEOUT)
                raise DomainError("local_runtime_timeout", f"Local startup timed out after {seconds} seconds. Review the service log; no inference was requested.", 409)
        except DomainError as error:
            with self._lock:
                if operation == self._operation and not cancel.is_set():
                    unavailable = error.code in ("local_runtime_unavailable", "local_runtime_model_missing")
                    self._set("Unavailable" if unavailable else "Failed", error.message, error.message)
        except (OSError, subprocess.SubprocessError):
            with self._lock:
                if operation == self._operation and not cancel.is_set():
                    self._set("Failed", "Local service startup failed. Review the service log and installation.", "Ollama could not be started.")
        finally:
            with self._lock:
                keep = (operation == self._operation and self._process is process
                        and self._state == "Running" and not cancel.is_set() and not self._closed)
            if process is not None and not keep:
                try:
                    self._terminate(process)
                except (OSError, subprocess.SubprocessError):
                    with self._lock:
                        if operation == self._operation:
                            self._set("Failed", "The local process could not be stopped. Review the service log.", "Owned process cleanup did not complete.")
                with self._lock:
                    if process.poll() is not None and self._process is process:
                        self._process = None
            with self._lock:
                if operation == self._operation and cancel.is_set() and (self._process is None or self._process.poll() is not None):
                    self._set("Stopped", "Local service is stopped.")

    def stop(self):
        with self._lock:
            if self._state == "Stopping":
                return self._snapshot()
            process = self._process
            if process is None and self._state == "Starting":
                self._cancel.set()
                self._set("Stopping", "Cancelling local service startup.")
                return self._snapshot()
            if process is None or process.poll() is not None:
                if self._external:
                    raise DomainError("local_runtime_external", "This service was started outside HuLLCirq and cannot be stopped here.", 409)
                self._process = None
                self._set("Stopped", "Local service is stopped.")
                return self._snapshot()
            self._cancel.set()
            self._set("Stopping", "Stopping the local service started by HuLLCirq.")
            self._worker = threading.Thread(target=self._stop_worker, args=(process,), name="hullcirq-local-runtime-stop", daemon=True)
            self._worker.start()
            return self._snapshot()

    def _stop_worker(self, process):
        try:
            self._terminate(process)
            with self._lock:
                if self._process is process and process.poll() is not None:
                    self._process = None
                    self._set("Stopped", "Local service is stopped.")
                    self._probe_at = time.monotonic()
        except (OSError, subprocess.SubprocessError):
            with self._lock:
                self._set("Failed", "The local process could not be stopped. Review the service log.", "Owned process cleanup did not complete.")

    def close(self):
        """Only stop our own process; external services survive GUI shutdown."""
        deadline = time.monotonic() + 5
        with self._lock:
            self._closed = True
            self._cancel.set()
            process, worker = self._process, self._worker
        try:
            self._terminate(process)
        except (OSError, subprocess.SubprocessError):
            pass
        if worker is not None and worker is not threading.current_thread():
            worker.join(timeout=max(0, deadline - time.monotonic()))
        with self._lock:
            if self._process is None or self._process.poll() is not None:
                self._process = None
                self._set("Stopped", "Local service is stopped.")
