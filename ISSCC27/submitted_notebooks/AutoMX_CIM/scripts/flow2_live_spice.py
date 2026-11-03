"""Run a host simulator with direct logs and bounded process-group cleanup."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
import shutil
import signal
import subprocess
import time


def _usage(pid):
    """Best-effort Linux observations; absent metrics are never reported as zero."""
    result = {}
    try:
        for line in Path(f"/proc/{pid}/status").read_text().splitlines():
            key, _, value = line.partition(":")
            if key in ("State", "VmRSS", "VmHWM", "VmSwap", "Threads"):
                result[key] = value.strip()
        stat = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
        result["cpu_seconds"] = (int(stat[11])+int(stat[12]))/os.sysconf("SC_CLK_TCK")
    except (OSError, ValueError, IndexError, AttributeError):
        pass
    return result


def run(command, work: Path, timeout_s: float, *, poll_s=2., line_buffer=True, heartbeat_s=30.):
    work = Path(work)
    if timeout_s <= 0 or poll_s <= 0 or heartbeat_s <= 0:
        raise ValueError("positive timeout/poll interval required")
    work.mkdir(parents=True, exist_ok=True)
    raw, resource = work / "ngspice.live.log", work / "process.jsonl"
    actual = list(command)
    stdbuf = shutil.which("stdbuf") if line_buffer and os.name == "posix" else None
    if stdbuf:
        actual = [stdbuf, "-oL", "-eL", *actual]
    started, process, timed_out = time.monotonic(), None, False
    last_heartbeat = 0.

    def stop():
        if process is None or process.poll() is not None:
            return
        if os.name == "posix":
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        else:
            process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            if os.name == "posix":
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            else:
                process.kill()
            process.wait()

    with raw.open("w", encoding="utf-8") as output, resource.open("w", encoding="utf-8") as samples:
        try:
            process = subprocess.Popen(actual, cwd=work, stdout=output, stderr=subprocess.STDOUT,
                                       start_new_session=os.name == "posix")
            print(f"Simulator PID={process.pid}; live log: {raw}; resources: {resource}", flush=True)
            while True:
                elapsed = time.monotonic()-started
                sample = {"elapsed_s": round(elapsed, 3), "pid": process.pid,
                          "log_bytes": raw.stat().st_size, **_usage(process.pid)}
                if elapsed-last_heartbeat >= heartbeat_s:
                    with raw.open("rb") as tail:
                        tail.seek(max(0, raw.stat().st_size-65536))
                        recent = tail.read().decode("utf-8", errors="replace")
                    references = re.findall(r"Reference value\s*:\s*([+\-\d.eE]+)", recent)
                    if references:
                        sample["transient_reference_s"] = float(references[-1])
                    print(f"SPICE {work.name}: {elapsed:.0f}s; log={sample['log_bytes']} bytes; "
                          f"RSS={sample.get('VmRSS', 'unavailable')}; CPU={sample.get('cpu_seconds', 'unavailable')}s; "
                          f"transient={sample.get('transient_reference_s', 'not reported')}s", flush=True)
                    last_heartbeat = elapsed
                samples.write(json.dumps(sample)+"\n")
                samples.flush()
                if process.poll() is not None:
                    break
                if elapsed >= timeout_s:
                    timed_out = True
                    stop()
                    break
                time.sleep(min(poll_s, timeout_s-elapsed))
        finally:
            stop()
    text = raw.read_text(encoding="utf-8", errors="replace")
    code = 124 if timed_out else process.returncode
    if timed_out:
        text += f"\nTIMEOUT after {timeout_s:g}s; direct log and process observations retained\n"
    return subprocess.CompletedProcess(actual, code, text, "")
