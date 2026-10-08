"""Single checkpoint writer: write once, retry only a transient Windows atomic rename."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import threading
import time
import uuid


class CheckpointWriter:
    def __init__(self, path: Path, guard, retry_seconds: float = 2.0):
        if not 0 < retry_seconds <= 2:
            raise ValueError("Checkpoint rename retry budget must be in (0,2] seconds")
        self.path, self.guard, self.retry_seconds = path, guard, retry_seconds
        self.lock = threading.Lock()

    def write(self, snapshot_supplier):
        self.guard.check("checkpoint_writer_wait")
        with self.lock:
            self.guard.check("checkpoint_writer_begin")
            token = uuid.uuid4().hex
            temporary = self.path.with_name(f".{self.path.name}.{token}.tmp")
            receipts = self.path.parent / "checkpoint-write-receipts"
            receipts.mkdir(exist_ok=True)
            # The caller's state is serialized exactly once. Rename retries cannot
            # invoke a reservation, snapshot supplier, counter update or process.
            data = (json.dumps(snapshot_supplier(), indent=2, allow_nan=False) + "\n").encode()
            with temporary.open("xb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            start_wall, start_mono = time.time(), time.monotonic()
            result = {
                "checkpoint": self.path.name, "unique_temporary": temporary.name,
                "intent_sha256": hashlib.sha256(data).hexdigest(), "intent_bytes": len(data),
                "snapshot_supplier_calls": 1, "temporary_write_count": 1,
                "retry_seconds_limit": self.retry_seconds, "rename_attempts": 0,
                "sharing_errors": [], "success": False,
            }
            try:
                while True:
                    self.guard.check("before_checkpoint_rename", write_id=token)
                    wall, mono = time.time() - start_wall, time.monotonic() - start_mono
                    if wall < 0 or mono < 0 or abs(wall - mono) > 0.5:
                        raise RuntimeError("Unverifiable time during checkpoint rename retry")
                    if result["rename_attempts"] and max(wall, mono) >= self.retry_seconds:
                        raise TimeoutError("Bounded checkpoint rename retry expired")
                    result["rename_attempts"] += 1
                    try:
                        os.replace(temporary, self.path)
                    except OSError as error:
                        code = getattr(error, "winerror", None)
                        if code not in (5, 32, 33):
                            result["unexpected_error_type"] = type(error).__name__
                            result["unexpected_winerror"] = code
                            raise
                        result["sharing_errors"].append({
                            "winerror": code, "rename_attempt": result["rename_attempts"],
                            "wall_elapsed_seconds": time.time() - start_wall,
                            "monotonic_elapsed_seconds": time.monotonic() - start_mono,
                        })
                        print(f"CHECKPOINT_RENAME_RETRY code={code} count={result['rename_attempts']}", flush=True)
                        remaining = self.retry_seconds - max(time.time() - start_wall, time.monotonic() - start_mono)
                        if remaining <= 0:
                            raise TimeoutError("Bounded checkpoint rename retry expired") from error
                        self.guard.check("checkpoint_rename_retry_wait", write_id=token)
                        time.sleep(min(0.05, remaining))
                    else:
                        result["success"] = True
                        self.guard.check("checkpoint_rename_complete", write_id=token)
                        return result
            finally:
                result["wall_elapsed_seconds"] = time.time() - start_wall
                result["monotonic_elapsed_seconds"] = time.monotonic() - start_mono
                result["failed_temporary_retained"] = temporary.exists()
                with (receipts / f"{token}.json").open("x", encoding="utf-8", newline="\n") as handle:
                    handle.write(json.dumps(result, indent=2, allow_nan=False) + "\n")
                    handle.flush()
                    os.fsync(handle.fileno())
