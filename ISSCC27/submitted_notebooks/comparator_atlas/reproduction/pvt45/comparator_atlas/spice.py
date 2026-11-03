"""Pinned-device ngspice runner and explicit decision/energy measurements."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
from typing import Literal
import uuid

import numpy as np
from numpy.typing import NDArray

from .designs import circuit_text, controls, get_design

ROOT = Path(__file__).resolve().parents[1]
PDK_REVISION = "f62031a1be9aefe902d6d54cddd6f59b57627436"
CORNERS = ("tt", "ss", "ff", "sf", "fs")
EVALUATION_START_S = 22.025e-9
CYCLE_START_S = 20e-9
STOP_S = 30e-9
CALIBRATION_DEADLINE_NS = 3.5
COLUMNS = (
    "time_s", "clock_v", "qp_v", "qn_v", "xp_v", "xn_v", "ivdd_a", "vinp_v", "vinn_v",
)
SPICE_INIT = "set ngbehavior=hsa\nset noaskquit\nset num_threads=1\n"
FloatArray = NDArray[np.float64]


class SimulationError(RuntimeError):
    """A simulation or evidence-integrity failure, never a circuit timeout."""


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(path)


@dataclass(frozen=True)
class Point:
    corner: str = "tt"
    vdd_v: float = 1.8
    temperature_c: float = 27.0
    differential_v: float = 0.01
    common_mode_ratio: float = 0.5
    pair_skew: float = 0.04
    trim_code: int = 0
    load_ff: float = 5.0
    max_step_ps: float = 10.0
    design_name: str = "baseline"
    source_resistance_ohm: float = 0.0
    sample_cap_ff: float = 0.0
    previous_differential_v: float | None = None

    def __post_init__(self) -> None:
        if self.corner not in CORNERS:
            raise ValueError(f"Unsupported process corner: {self.corner}")
        values = (
            self.vdd_v, self.temperature_c, self.differential_v,
            self.common_mode_ratio, self.pair_skew, self.load_ff, self.max_step_ps,
            self.source_resistance_ohm, self.sample_cap_ff,
        )
        if not all(math.isfinite(value) for value in values):
            raise ValueError("All simulation parameters must be finite")
        if not 1.2 <= self.vdd_v <= 1.95:
            raise ValueError("DUT supply must be between 1.2 V and 1.95 V")
        if not -40 <= self.temperature_c <= 125:
            raise ValueError("Temperature must be between -40 C and 125 C")
        if not 0.35 <= self.common_mode_ratio <= 0.75:
            raise ValueError("Common-mode ratio must be between 0.35 and 0.75")
        if abs(self.pair_skew) > 0.2:
            raise ValueError("Deterministic width stress is limited to +/-20% per branch")
        design = get_design(self.design_name)
        if type(self.trim_code) is not int or abs(self.trim_code) > design.max_code:
            raise ValueError(f"Trim code must be an integer within +/-{design.max_code}")
        if not 0 < self.load_ff <= 100 or not 0 < self.max_step_ps <= 20:
            raise ValueError("Load must be in (0, 100] fF and timestep in (0, 20] ps")
        common_mode = self.common_mode_ratio * self.vdd_v
        if not 0 <= common_mode - abs(self.differential_v) / 2:
            raise ValueError("Input is below ground")
        if common_mode + abs(self.differential_v) / 2 > self.vdd_v:
            raise ValueError("Input exceeds the supply")
        if not 0 <= self.source_resistance_ohm <= 100000 or not 0 <= self.sample_cap_ff <= 1000:
            raise ValueError("Source resistance or sample capacitance is outside the declared domain")
        if self.previous_differential_v is not None:
            previous = self.previous_differential_v
            if not math.isfinite(previous):
                raise ValueError("Previous differential input must be finite")
            if common_mode - abs(previous) / 2 < 0 or common_mode + abs(previous) / 2 > self.vdd_v:
                raise ValueError("Previous input would exceed the supply rails")


@dataclass(frozen=True)
class Trace:
    point: Point
    values: FloatArray
    run_id: str
    directory: Path
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class Measurement:
    deadline_ns: float
    decision: int
    outcome: Literal["correct", "wrong", "unresolved", "reference"]
    decision_time_ns: float | None
    core_energy_fj: float
    reset_ok: bool
    qp_at_deadline_v: float
    qn_at_deadline_v: float


def rail_decision(qp: float, qn: float, vdd: float) -> int:
    if qp >= 0.8 * vdd and qn <= 0.2 * vdd:
        return 1
    if qn >= 0.8 * vdd and qp <= 0.2 * vdd:
        return -1
    return 0


def validate_waveform(values: FloatArray) -> None:
    if values.ndim != 2 or values.shape[1] not in (7, len(COLUMNS)) or len(values) < 10:
        raise SimulationError("Waveform must have seven legacy or nine current columns and at least ten samples")
    if not np.isfinite(values).all():
        raise SimulationError("Waveform contains non-finite values")
    if not np.all(np.diff(values[:, 0]) > 0):
        raise SimulationError("Waveform time is not strictly increasing")
    if values[0, 0] > CYCLE_START_S or values[-1, 0] < STOP_S - 1e-15:
        raise SimulationError("Simulation did not cover the complete measured cycle")


def measure(trace: Trace, deadline_ns: float) -> Measurement:
    if not math.isfinite(deadline_ns) or not 0 < deadline_ns <= CALIBRATION_DEADLINE_NS:
        raise ValueError("Decision deadline must be in (0, 3.5] ns after clock midpoint")
    values = trace.values
    validate_waveform(values)
    t = values[:, 0]
    point = trace.point
    stop = EVALUATION_START_S + deadline_ns * 1e-9
    qp = float(np.interp(stop, t, values[:, 2]))
    qn = float(np.interp(stop, t, values[:, 3]))
    decision = rail_decision(qp, qn, point.vdd_v)
    reset_time = EVALUATION_START_S - 100e-12
    reset_ok = all(
        np.interp(reset_time, t, values[:, column]) >= 0.9 * point.vdd_v
        for column in (2, 3, 4, 5)
    )
    if not reset_ok:
        raise SimulationError(f"Comparator did not reset before evaluation: {trace.run_id}")
    if not decision:
        outcome = "unresolved"
    elif point.differential_v == 0:
        outcome = "reference"
    else:
        expected = 1 if point.differential_v > 0 else -1
        outcome = "correct" if decision == expected else "wrong"

    decision_time = None
    if decision:
        # The last invalid sample prevents an early output glitch being called a decision.
        selection = (t >= EVALUATION_START_S) & (t < stop)
        times = np.concatenate(([EVALUATION_START_S], t[selection], [stop]))
        positive = np.interp(times, t, values[:, 2])
        negative = np.interp(times, t, values[:, 3])
        high, low = (positive, negative) if decision > 0 else (negative, positive)
        valid = (high >= 0.8 * point.vdd_v) & (low <= 0.2 * point.vdd_v)
        invalid = np.flatnonzero(~valid)
        index = int(invalid[-1] + 1) if len(invalid) else 0
        decision_time = float((times[index] - EVALUATION_START_S) * 1e9)

    cycle_mask = (t > CYCLE_START_S) & (t < STOP_S)
    energy_times = np.concatenate(([CYCLE_START_S], t[cycle_mask], [STOP_S]))
    current = np.interp(energy_times, t, values[:, 6])
    energy = float(-point.vdd_v * np.trapezoid(current, energy_times) * 1e15)
    if energy < -1e-3:
        raise SimulationError(f"Unexpected negative net rail energy: {trace.run_id}")
    return Measurement(
        deadline_ns, decision, outcome, decision_time, energy,
        bool(reset_ok), qp, qn,
    )


class Simulator:
    def __init__(self, output: Path, *, workers: int = 2) -> None:
        if type(workers) is not int or not 1 <= workers <= 4:
            raise ValueError("Simulator workers must be between one and four")
        self.workers = workers
        self.output = output.resolve()
        self.output.mkdir(parents=True, exist_ok=True)
        self.pdk = ROOT / ".deps" / "sky130_fd_pr"
        self.circuit = ROOT / "circuits" / "strongarm.spice"
        supplied = os.environ.get("NGSPICE_EXE")
        local = ROOT / ".tools" / "ngspice" / "Spice64" / "bin" / "ngspice_con.exe"
        executable = supplied or (str(local) if local.is_file() else shutil.which("ngspice"))
        if not executable:
            raise SimulationError("ngspice is missing; run node scripts\\setup.mjs or set NGSPICE_EXE")
        self.executable = Path(executable).resolve()
        if not self.executable.is_file():
            raise SimulationError(f"ngspice executable does not exist: {self.executable}")
        if not self.pdk.is_dir():
            raise SimulationError("Pinned SKY130 models are missing; run the setup script")
        revision = subprocess.run(
            ["git", "-C", str(self.pdk), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        if revision != PDK_REVISION:
            raise SimulationError(f"Unexpected PDK revision: {revision}; expected {PDK_REVISION}")
        dirty = subprocess.run(
            ["git", "-C", str(self.pdk), "status", "--porcelain", "--untracked-files=no"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        if dirty:
            raise SimulationError("The pinned PDK has modified tracked files; restore it separately")
        self.version = subprocess.run(
            [str(self.executable), "--version"], capture_output=True, text=True,
            check=True, timeout=30,
        ).stdout.strip()
        self.provenance = {
            "pdk_repository": "https://github.com/google/skywater-pdk-libs-sky130_fd_pr",
            "pdk_revision": PDK_REVISION,
            "ngspice_version": self.version,
            "ngspice_binary_sha256": sha256(self.executable),
            "baseline_circuit_sha256": sha256(self.circuit),
            "design_generator_sha256": sha256(Path(__file__).with_name("designs.py")),
            "measurement_source_sha256": sha256(Path(__file__)),
            "numpy_version": np.__version__,
        }
        self.model_hashes: dict[str, dict[str, str]] = {}
        for corner in CORNERS:
            files = [self.pdk / "models" / "parameters" / "lod.spice"]
            for device in ("nfet_01v8", "pfet_01v8", "nfet_01v8_lvt"):
                folder = self.pdk / "cells" / device
                stem = f"sky130_fd_pr__{device}"
                files.extend(folder / f"{stem}__{suffix}.spice" for suffix in (
                    "mismatch.corner", f"{corner}.corner", f"{corner}.pm3",
                ))
            self.model_hashes[corner] = {
                str(path.relative_to(self.pdk)): sha256(path) for path in files
            }
        self.executed = 0
        self.cached = 0
        self.processes = 0
        self._verified_batches: set[str] = set()

    def _header(self, point: Point) -> str:
        design = get_design(point.design_name)
        includes = [self.pdk / "models" / "parameters" / "lod.spice"]
        devices = ["nfet_01v8", "pfet_01v8"]
        if design.input_device not in devices:
            devices.append(design.input_device)
        for device in devices:
            stem = f"sky130_fd_pr__{device}"
            folder = self.pdk / "cells" / device
            includes.extend((
                folder / f"{stem}__mismatch.corner.spice",
                folder / f"{stem}__{point.corner}.corner.spice",
            ))
        include_text = "\n".join(f'.include "{path}"' for path in includes)
        common_mode = point.common_mode_ratio * point.vdd_v
        sources = []
        for label, sign in (("p", 1), ("n", -1)):
            voltage = common_mode + sign * point.differential_v / 2
            node = f"vin{label}" if point.source_resistance_ohm == 0 else f"source_{label}"
            value = f"{voltage:.12g}"
            if point.previous_differential_v is not None:
                previous = common_mode + sign * point.previous_differential_v / 2
                value = f"PWL(0 {previous:.12g} 18n {previous:.12g} 18.05n {voltage:.12g})"
            sources.append(f"Vin{label} {node} 0 {value}")
            if point.source_resistance_ohm > 0:
                sources.append(f"Rsource{label} {node} vin{label} {point.source_resistance_ohm:.12g}")
            if point.sample_cap_ff > 0:
                sources.append(f"Csample{label} vin{label} 0 {point.sample_cap_ff:.12g}f")
        trim_sources = []
        for side, enabled in (("p", point.trim_code > 0), ("n", point.trim_code < 0)):
            for bit in range(design.trim_bits):
                high = enabled and bool(abs(point.trim_code) & (1 << bit))
                trim_sources.append(f"Vt{side}{bit} t{side}{bit} 0 {point.vdd_v if high else 0:.12g}")
        return f"""Comparator Atlas - actual SKY130 models, deterministic width stress
.option scale=1u reltol=1e-5 abstol=1e-13 vntol=1e-7
{include_text}
{circuit_text(design)}
.temp {point.temperature_c:.12g}
Vdd vdd 0 {point.vdd_v:.12g}
Vclk clk 0 PULSE(0 {point.vdd_v:.12g} 2n 50p 50p 4n 10n)
{chr(10).join(sources)}
{chr(10).join(trim_sources)}
Xdut vinp vinn clk vdd 0 qp qn {" ".join(controls(design))} atlas pair_skew={point.pair_skew:.12g}
Cqp qp 0 {point.load_ff:.12g}f
Cqn qn 0 {point.load_ff:.12g}f
.save v(clk) v(qp) v(qn) v(xdut.xp) v(xdut.xn) i(vdd) v(vinp) v(vinn)
"""

    @staticmethod
    def _analysis(point: Point, destination: str) -> str:
        return (
            f"tran {point.max_step_ps:.12g}p 30n 19n {point.max_step_ps:.12g}p\n"
            f"wrdata {destination} v(clk) v(qp) v(qn) v(xdut.xp) v(xdut.xn) i(vdd) v(vinp) v(vinn)\n"
            "destroy $curplot\n"
        )

    def deck(self, point: Point) -> str:
        return (
            self._header(point) + ".control\nset wr_singlescale\nset wr_vecnames\nset numdgt=15\n"
            + self._analysis(point, "waveform.tsv") + "quit 0\n.endc\n.end\n"
        )

    def identity(self, point: Point) -> dict:
        return {
            "schema": 2, "point": asdict(point),
            "reproduction_deck_sha256": hashlib.sha256(self.deck(point).encode()).hexdigest(),
            "ngspice_binary_sha256": self.provenance["ngspice_binary_sha256"],
            "spiceinit_sha256": hashlib.sha256(SPICE_INIT.encode()).hexdigest(),
            "models": self.model_hashes[point.corner],
        }

    def run_id(self, point: Point) -> str:
        identity = self.identity(point)
        key = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()[:24]
        return key

    def _cached_trace(self, point: Point, key: str) -> Trace | None:
        folder = self.output / key
        metadata_path = folder / "metadata.json"
        archive = folder / "waveform.npz"
        if not metadata_path.exists():
            return None
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if metadata["identity"] != self.identity(point):
            raise SimulationError(f"Run-identity mismatch in {folder}")
        if not archive.exists() or sha256(archive) != metadata["waveform_sha256"]:
            raise SimulationError(f"Cached waveform is missing or corrupted: {folder}")
        if sha256(folder / "circuit.cir") != metadata["reproduction_deck_sha256"]:
            raise SimulationError(f"Cached reproduction netlist was modified: {folder}")
        batch_id = metadata["batch_id"]
        if not re.fullmatch(r"[0-9a-f]{32}", batch_id):
            raise SimulationError("Invalid batch identity in cache metadata")
        batch = self.output / "_batches" / batch_id
        receipt = json.loads((batch / "receipt.json").read_text(encoding="utf-8"))
        if receipt["status"] != "complete" or key not in receipt["run_ids"]:
            raise SimulationError(f"Missing completed execution receipt for {key}")
        if batch_id not in self._verified_batches:
            for name, expected in receipt["artifact_sha256"].items():
                if name not in ("batch.cir", ".spiceinit", "ngspice.log"):
                    raise SimulationError("Unexpected batch evidence filename")
                if sha256(batch / name) != expected:
                    raise SimulationError(f"Executed batch evidence was modified: {batch}")
            self._verified_batches.add(batch_id)
        with np.load(archive, allow_pickle=False) as saved:
            values = saved["values"]
        validate_waveform(values)
        return Trace(point, values, key, folder, tuple(metadata["warnings"]))

    def _execute_batch(self, points: list[Point]) -> list[Trace]:
        batch_id = uuid.uuid4().hex
        batch = self.output / "_batches" / batch_id
        batch.mkdir(parents=True)
        lines = [self._header(points[0]), ".control", "set wr_singlescale", "set wr_vecnames", "set numdgt=15"]
        for index, point in enumerate(points):
            if point.previous_differential_v is None:
                common_mode = point.common_mode_ratio * point.vdd_v
                lines.extend((
                    f"alter Vinp {common_mode + point.differential_v / 2:.12g}",
                    f"alter Vinn {common_mode - point.differential_v / 2:.12g}",
                ))
                for side, enabled in (("p", point.trim_code > 0), ("n", point.trim_code < 0)):
                    for bit in range(get_design(point.design_name).trim_bits):
                        high = enabled and bool(abs(point.trim_code) & (1 << bit))
                        lines.append(f"alter Vt{side}{bit} {point.vdd_v if high else 0:.12g}")
            lines.append(self._analysis(point, f"point_{index}.tsv"))
        lines.extend(("quit 0", ".endc", ".end"))
        (batch / "batch.cir").write_text("\n".join(lines) + "\n", encoding="utf-8")
        (batch / ".spiceinit").write_text(SPICE_INIT, encoding="ascii")
        write_json(batch / "receipt.json", {"status": "running"})
        start = time.perf_counter()
        result = subprocess.run(
            [str(self.executable), "-b", "-o", "ngspice.log", "batch.cir"],
            cwd=batch, capture_output=True, text=True, timeout=max(120, 15 * len(points)),
        )
        elapsed = time.perf_counter() - start
        log_path = batch / "ngspice.log"
        log = log_path.read_text(encoding="utf-8", errors="replace") if log_path.exists() else ""
        (batch / "console.log").write_text(result.stdout + result.stderr, encoding="utf-8")
        failures = re.search(
            r"(?im)^\s*(?:error\b|fatal\b)|timestep too small|no such vector|simulation interrupted",
            log + result.stderr,
        )
        if result.returncode != 0 or failures:
            write_json(batch / "receipt.json", {"status": "failed", "exit_code": result.returncode})
            raise SimulationError(
                f"ngspice failed (exit {result.returncode}); see {log_path}\n"
                f"{(log + result.stderr)[-2500:]}"
            )
        waveforms = []
        for index in range(len(points)):
            raw = batch / f"point_{index}.tsv"
            if not raw.is_file():
                raise SimulationError(f"Missing waveform {raw}; see {log_path}")
            values = np.loadtxt(raw, skiprows=1, dtype=np.float64)
            if values.shape[1] != len(COLUMNS):
                raise SimulationError("Current simulator output is missing declared voltage columns")
            validate_waveform(values)
            waveforms.append(values)
        warnings = tuple(line.strip() for line in log.splitlines() if "warning" in line.lower())
        traces = []
        for index, (point, values) in enumerate(zip(points, waveforms)):
            key = self.run_id(point)
            folder = self.output / key
            folder.mkdir(parents=True, exist_ok=True)
            archive = folder / "waveform.npz"
            (folder / "circuit.cir").write_text(self.deck(point), encoding="utf-8")
            np.savez_compressed(archive, values=values)
            write_json(folder / "metadata.json", {
                "identity": self.identity(point),
                "created_utc": datetime.now(timezone.utc).isoformat(),
                "producer_provenance": self.provenance,
                "batch_id": batch_id, "batch_index": index,
                "waveform_sha256": sha256(archive),
                "reproduction_deck_sha256": sha256(folder / "circuit.cir"),
                "warnings": warnings,
            })
            traces.append(Trace(point, values, key, folder, warnings))
        write_json(batch / "receipt.json", {
            "status": "complete",
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "elapsed_seconds": elapsed,
            "run_ids": [trace.run_id for trace in traces],
            "provenance": self.provenance,
            "artifact_sha256": {
                name: sha256(batch / name) for name in ("batch.cir", ".spiceinit", "ngspice.log")
            },
        })
        for index in range(len(points)):
            (batch / f"point_{index}.tsv").unlink()
        return traces

    def run_many(self, points: list[Point]) -> list[Trace]:
        results: dict[str, Trace] = {}
        pending: dict[Point, list[Point]] = {}
        keys = [self.run_id(point) for point in points]
        unique = dict(zip(keys, points))
        for key, point in unique.items():
            trace = self._cached_trace(point, key)
            if trace is not None:
                results[key] = trace
                self.cached += 1
            else:
                group = point if point.previous_differential_v is not None else replace(
                    point, differential_v=0, trim_code=0,
                )
                pending.setdefault(group, []).append(point)
        batches = [
            group[index:index + 64]
            for group in pending.values() for index in range(0, len(group), 64)
        ]
        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            for traces in executor.map(self._execute_batch, batches):
                self.processes += 1
                self.executed += len(traces)
                results.update((trace.run_id, trace) for trace in traces)
        return [results[key] for key in keys]

    def run(self, point: Point) -> Trace:
        return self.run_many([point])[0]
