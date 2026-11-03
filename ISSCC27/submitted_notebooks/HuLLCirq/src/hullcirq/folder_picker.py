"""User-triggered native directory chooser, independent of the API request lock."""
from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import threading
import uuid
from pathlib import Path

from .domain import DomainError


class FolderPickerManager:
    def __init__(self, project_root, runner=None):
        self.project_root = Path(project_root)
        self.runner = runner or self._run_native
        self.lock = threading.RLock()
        self.records = {}
        self.processes = {}
        self.closed = False

    def _public(self, record):
        return {key: copy.deepcopy(value) for key, value in record.items() if key != "session_id"}

    def start(self, session_id, initial_directory=None):
        if initial_directory is not None:
            if type(initial_directory) is not str or not Path(initial_directory).is_absolute():
                raise DomainError("invalid_directory", "Initial directory must be an absolute local path.")
            if not Path(initial_directory).is_dir():
                raise DomainError("invalid_directory", "Initial directory does not exist.")
        with self.lock:
            if self.closed:
                raise DomainError("folder_picker_closed", "Directory chooser is unavailable.", 409)
            if any(r["status"] == "Pending" for r in self.records.values()):
                raise DomainError("folder_picker_busy", "A folder chooser is already open. Finish or cancel it first.", 409)
            if len(self.records) >= 32:
                self.records = {k: r for k, r in self.records.items() if r["status"] == "Pending"}
            identifier = uuid.uuid4().hex
            record = {"id": identifier, "session_id": session_id, "status": "Pending", "directory": None, "error": None}
            self.records[identifier] = record
            threading.Thread(target=self._worker, args=(identifier, initial_directory), daemon=True).start()
            return self._public(record)

    def _worker(self, identifier, initial_directory):
        try:
            result = self.runner(identifier, initial_directory)
            if type(result) is not dict or result.get("status") not in ("Completed", "Cancelled"):
                raise ValueError("The directory chooser returned an invalid result.")
            if result["status"] == "Completed":
                directory = result.get("directory")
                if type(directory) is not str or not Path(directory).is_absolute() or not Path(directory).is_dir():
                    raise ValueError("The selected folder is no longer available.")
            with self.lock:
                if self.records[identifier]["status"] == "Pending":
                    self.records[identifier].update(status=result["status"], directory=result.get("directory"))
        except Exception:
            with self.lock:
                if self.records[identifier]["status"] == "Pending":
                    self.records[identifier].update(status="Failed", error="The native folder chooser could not open. Enter an absolute folder path instead.")
        finally:
            with self.lock:
                self.processes.pop(identifier, None)

    def _run_native(self, identifier, initial_directory):
        command = [sys.executable, "-X", "utf8", str(self.project_root / "scripts" / "select_project_folder.py")]
        if initial_directory:
            command.extend(["--initial-directory", initial_directory])
        options = {"stdout": subprocess.PIPE, "stderr": subprocess.PIPE, "text": True, "encoding": "utf-8"}
        if os.name == "nt":
            options["creationflags"] = subprocess.CREATE_NO_WINDOW
        with self.lock:
            if self.closed or self.records[identifier]["status"] != "Pending":
                return {"status": "Cancelled"}
            process = subprocess.Popen(command, **options)
            self.processes[identifier] = process
        try:
            stdout, _ = process.communicate(timeout=300)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate()
            raise ValueError("The folder chooser timed out.")
        if process.returncode != 0:
            raise ValueError("The folder chooser failed.")
        return json.loads(stdout)

    def status(self, identifier, session_id):
        with self.lock:
            record = self.records.get(identifier)
            if record is None or record["session_id"] != session_id:
                raise DomainError("folder_picker_not_found", "This folder chooser does not belong to the current page.", 404)
            return self._public(record)

    def cancel(self, identifier, session_id):
        with self.lock:
            self.status(identifier, session_id)
            record = self.records[identifier]
            if record["status"] == "Pending":
                record["status"] = "Cancelled"
                process = self.processes.get(identifier)
                if process is not None and process.poll() is None:
                    process.terminate()
            return self._public(record)

    def close(self):
        with self.lock:
            self.closed = True
            for identifier, record in self.records.items():
                if record["status"] == "Pending":
                    self.cancel(identifier, record["session_id"])

    def cancel_session(self, session_id):
        with self.lock:
            for identifier, record in self.records.items():
                if record["session_id"] == session_id and record["status"] == "Pending":
                    self.cancel(identifier, session_id)
