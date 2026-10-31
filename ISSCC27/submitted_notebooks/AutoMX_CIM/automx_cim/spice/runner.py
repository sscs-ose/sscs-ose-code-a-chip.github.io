"""Parallel batch ngspice runner with receipt-backed electrical validation."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import subprocess
from typing import Iterable

from .parser import parse_measurements, validate_measurements

def _hash(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()

def _version(executable: str) -> str:
    result = subprocess.run([executable, "--version"], capture_output=True, text=True, timeout=15)
    lines = (result.stdout or result.stderr).strip().splitlines()
    return lines[0] if lines else "unknown"

def _run_job(executable: str, stage: str, job: dict[str, object], log_dir: Path, timeout_s: int):
    deck = Path(str(job["testbench"])); name = str(job["name"])
    if not deck.is_file(): raise FileNotFoundError(f"missing testbench for {stage}/{name}: {deck}")
    log_path = log_dir / f"{stage}_{name}.log"; command = [executable, "-b", "-o", str(log_path), str(deck)]
    try:
        completed = subprocess.run(command, cwd=deck.parent, capture_output=True, text=True, timeout=timeout_s)
    except subprocess.TimeoutExpired as error:
        raise RuntimeError(f"ngspice timed out for {stage}/{name} after {timeout_s}s; log: {log_path}") from error
    log = log_path.read_text(encoding="utf-8", errors="replace") if log_path.exists() else completed.stdout + completed.stderr
    if completed.returncode:
        raise RuntimeError(f"ngspice failed for {stage}/{name} ({completed.returncode}); inspect {log_path}")
    expected = [str(case["measurement"]) for case in job["cases"]]
    expected += [str(item) for item in job["delay_measurements"]]
    expected.append(str(job["energy_measurement"]))
    return {"name": name, "deck": deck, "log": log_path, "command": command,
            "measurements": parse_measurements(log, expected=expected)}

def run_stage4_manifest(manifest_path: str | Path, stages: Iterable[str] | None = None,
                        timeout_s: int = 900) -> list[dict[str, object]]:
    """Run levels in order; split decks within a level run concurrently."""
    manifest_file = Path(manifest_path).resolve(); manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    if manifest.get("format") != "automx-cim-stage4-spice-manifest-v1":
        raise ValueError(f"unsupported Stage-4 manifest: {manifest.get('format')}")
    selected = set(stages) if stages is not None else None; executable = shutil.which("ngspice")
    if not executable: raise RuntimeError("ngspice is not on PATH")
    receipts = []
    for artifact in manifest["artifacts"]:
        stage = artifact["stage"]
        if selected is not None and stage not in selected: continue
        netlist = Path(artifact["netlist"])
        if not netlist.is_file(): raise FileNotFoundError(f"missing generated netlist for {stage}: {netlist}")
        receipt_path = Path(artifact["receipt"])
        if receipt_path.exists():
            receipt_path.unlink()  # A rerun must not inherit stale PASS evidence.
        jobs = artifact.get("jobs") or [{"name": stage, "testbench": artifact["testbench"],
                                         "cases": artifact["cases"], "delay_measurements": artifact["delay_measurements"],
                                         "energy_measurement": artifact["energy_measurement"]}]
        log_dir = manifest_file.parent / "logs"; log_dir.mkdir(parents=True, exist_ok=True)
        requested_jobs = int(os.environ.get("AUTOMX_NGSPICE_JOBS", "4")); workers = max(1, min(len(jobs), requested_jobs))
        results = []
        if workers == 1:
            results = [_run_job(executable, stage, job, log_dir, timeout_s) for job in jobs]
        else:
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures = {pool.submit(_run_job, executable, stage, job, log_dir, timeout_s): job["name"] for job in jobs}
                for future in as_completed(futures): results.append(future.result())
        measurements: dict[str, float] = {}; energy_by_job: dict[str, float] = {}
        for result in results:
            for key, value in result["measurements"].items():
                if key == artifact["energy_measurement"].lower(): energy_by_job[result["name"]] = value
                elif key in measurements: raise RuntimeError(f"duplicate measurement {key} in split {stage} decks")
                else: measurements[key] = value
        measurements.update({f"{artifact['energy_measurement'].lower()}__{name}": value for name, value in energy_by_job.items()})
        measurements[artifact["energy_measurement"].lower()] = sum(energy_by_job.values()) / len(energy_by_job)
        metrics, failures = validate_measurements(artifact["cases"], artifact["delay_measurements"], measurements,
                                                  energy_name=artifact["energy_measurement"])
        metrics["energy_by_job_j"] = energy_by_job
        metrics["maximum_dynamic_energy_j"] = max(energy_by_job.values())
        if failures:
            detail = "\n  - ".join(failures[:20]); logs = ", ".join(str(r["log"]) for r in results)
            raise RuntimeError(f"electrical validation failed for {stage}:\n  - {detail}\nlogs: {logs}")
        receipt = {"format": "automx-cim-stage4-ngspice-receipt-v1", "status": "PASS", "stage": stage,
                   "level": artifact["level"], "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                   "config_sha256": manifest["config_sha256"], "pdk": manifest["pdk"], "corner": manifest["corner"],
                   "vdd": manifest["vdd"], "temperature_c": manifest["temperature_c"],
                   "activation_encoding": manifest["activation_encoding"],
                   "circuit_assumptions": manifest.get("circuit_assumptions", {}),
                   "model_library": manifest["model_library"],
                   "model_library_sha256": manifest["model_library_sha256"],
                   "ngspice": {"path": executable, "version": _version(executable), "parallel_jobs": workers,
                               "commands": [r["command"] for r in results]},
                   "inputs": {"netlist": str(netlist), "netlist_sha256": _hash(netlist),
                              "testbenches": [{"path": str(r["deck"]), "sha256": _hash(r["deck"])} for r in results]},
                   "logs": [str(r["log"]) for r in results], "metrics": metrics, "measurements": measurements}
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8"); receipts.append(receipt)
    if not receipts: raise ValueError("no Stage-4 artifacts selected")
    return receipts