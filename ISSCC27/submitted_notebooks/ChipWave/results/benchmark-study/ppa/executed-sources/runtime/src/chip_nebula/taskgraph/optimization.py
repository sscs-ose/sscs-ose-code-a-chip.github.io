"""Deterministic formal-equivalence and PPA-candidate primitives.

The desktop and CLI can share this module without teaching either UI how to
interpret tool logs.  A successful process is deliberately kept separate
from a proof verdict: only EQY's final PASS marker, backed by PASS for every
generated partition, is classified as a proof.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Mapping, Sequence

import psutil


class OptimizationError(RuntimeError):
    """Raised when an optimization or equivalence request is invalid."""


_SV_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_$]*$")
_DEFINE = re.compile(r"^[A-Za-z_][A-Za-z0-9_$]*(?:=[^\n\r\x00]+)?$")
_PROOF_VERDICTS = {
    "proved", "counterexample", "inconclusive", "timeout",
    "resource_exhausted", "unsupported",
}


@dataclass(frozen=True)
class EquivalenceConfig:
    """Frozen contract for one gold-versus-candidate EQY proof."""

    top_module: str
    source_files: tuple[str, ...]
    include_dirs: tuple[str, ...] = ()
    defines: tuple[str, ...] = ()
    parameters: Mapping[str, int] = field(default_factory=dict)
    clock_port: str = ""
    reset_port: str = ""
    reset_active: str = ""
    timeout_seconds: int = 600
    jobs: int = 1

    def __post_init__(self) -> None:
        if not _SV_IDENTIFIER.fullmatch(self.top_module):
            raise OptimizationError("top_module must be a SystemVerilog identifier")
        if not self.source_files:
            raise OptimizationError("formal equivalence requires source_files")
        for name, values in (
            ("source_files", self.source_files),
            ("include_dirs", self.include_dirs),
        ):
            for value in values:
                _safe_relative(value, name)
        for define in self.defines:
            if not _DEFINE.fullmatch(define):
                raise OptimizationError(f"invalid SystemVerilog define: {define}")
        for name, value in self.parameters.items():
            if not _SV_IDENTIFIER.fullmatch(str(name)) or type(value) is not int:
                raise OptimizationError("formal parameters must map identifiers to integers")
        if self.reset_port:
            if not _SV_IDENTIFIER.fullmatch(self.reset_port):
                raise OptimizationError("reset_port must be a SystemVerilog identifier")
            if not _SV_IDENTIFIER.fullmatch(self.clock_port):
                raise OptimizationError("reset proof requires a clock_port identifier")
            if self.clock_port == self.reset_port:
                raise OptimizationError("clock_port and reset_port must differ")
            if self.reset_active not in {"high", "low"}:
                raise OptimizationError("reset_active must be high or low")
        elif self.reset_active:
            raise OptimizationError("reset_active requires reset_port")
        elif self.clock_port:
            raise OptimizationError("clock_port requires reset_port")
        if not 1 <= self.timeout_seconds <= 86_400:
            raise OptimizationError("equivalence timeout must be within 1..86400 seconds")
        if not 1 <= self.jobs <= 128:
            raise OptimizationError("equivalence jobs must be within 1..128")

    def contract(self) -> dict[str, Any]:
        return {
            "top_module": self.top_module,
            "source_files": list(self.source_files),
            "include_dirs": list(self.include_dirs),
            "defines": list(self.defines),
            "parameters": dict(sorted(self.parameters.items())),
            "observable_behavior": "ports-and-cycle-boundaries",
            "reset": {
                "clock_port": self.clock_port,
                "port": self.reset_port,
                "active": self.reset_active,
                "checked_separately": bool(self.reset_port),
                "covered_by_sequential_proof": bool(self.reset_port),
            },
            "proof_method": "eqy-partitioned-sby-abc-pdr",
            "reset_proof_method": (
                "eqy-reset-initialized-sby-abc-pdr" if self.reset_port else ""
            ),
            "finite_bmc_is_proof": False,
            "unknown_value_policy": "preserve",
        }


@dataclass(frozen=True)
class EquivalenceResult:
    verdict: str
    returncode: int | None
    reason: str
    partitions: tuple[dict[str, str], ...]
    contract: Mapping[str, Any]
    tool_versions: Mapping[str, str]
    input_digests: tuple[str, ...]
    resources: Mapping[str, Any]
    artifacts: tuple[dict[str, Any], ...]
    command: tuple[str, ...]
    reset_proof: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.verdict not in _PROOF_VERDICTS:
            raise OptimizationError(f"invalid equivalence verdict: {self.verdict}")

    @property
    def proved(self) -> bool:
        return self.verdict == "proved"

    def to_dict(self) -> dict[str, Any]:
        document = asdict(self)
        document["partitions"] = [dict(item) for item in self.partitions]
        document["artifacts"] = [dict(item) for item in self.artifacts]
        document["command"] = list(self.command)
        return document


class FormalEquivalenceRunner:
    """Run an unbounded EQY proof and preserve the exact evidence directory."""

    def __init__(self, toolchain_root: Path | None = None) -> None:
        self.toolchain_root = toolchain_root.resolve() if toolchain_root else None

    def inspect_environment(self) -> dict[str, Any]:
        bin_dir = self._bin_dir()
        commands = {
            "eqy": self._resolve_tool("EQY_EXE", "eqy", bin_dir),
            "yosys": self._resolve_tool("YOSYS_EXE", "yosys", bin_dir),
            "sby": self._resolve_tool("SBY_EXE", "sby", bin_dir),
            "abc": self._resolve_tool("ABC_EXE", "yosys-abc", bin_dir),
        }
        # ABC PDR is the proof engine.  z3 is recorded as an available
        # diagnostic solver but is not required by this strategy.
        commands["z3"] = self._resolve_tool("Z3_EXE", "z3", bin_dir)
        versions = {
            name: _tool_version(path, "--version" if name != "yosys" else "-V")
            for name, path in commands.items() if path is not None
        }
        required = ("eqy", "yosys", "sby", "abc")
        missing = [name for name in required if commands[name] is None]
        return {
            "ready": not missing,
            "toolchain_root": str(self._toolchain_root() or ""),
            "tools": {
                name: {
                    "path": str(path or ""),
                    "version": versions.get(name, ""),
                    "ready": path is not None,
                }
                for name, path in commands.items()
            },
            "missing": missing,
            "proof_method": "eqy-partitioned-sby-abc-pdr",
            "memory_limit_bytes": None,
        }

    def run(
        self,
        gold_root: Path,
        candidate_root: Path,
        evidence_dir: Path,
        config: EquivalenceConfig,
        *,
        process_callback: Callable[[subprocess.Popen[str] | None], None] | None = None,
        log_callback: Callable[[str], None] | None = None,
    ) -> EquivalenceResult:
        environment = self.inspect_environment()
        if not environment["ready"]:
            return EquivalenceResult(
                verdict="unsupported", returncode=None,
                reason="missing formal tools: " + ", ".join(environment["missing"]),
                partitions=(), contract=config.contract(),
                tool_versions=_environment_versions(environment),
                input_digests=(), resources=_empty_resources(), artifacts=(), command=(),
            )
        gold_root = gold_root.resolve()
        candidate_root = candidate_root.resolve()
        if not gold_root.is_dir() or not candidate_root.is_dir():
            raise OptimizationError("gold and candidate roots must be directories")
        evidence_dir = evidence_dir.resolve()
        if evidence_dir in {gold_root, candidate_root}:
            raise OptimizationError("evidence directory must be separate from proof inputs")
        if evidence_dir.exists():
            raise OptimizationError("formal evidence directory already exists")
        evidence_dir.mkdir(parents=True)
        inputs = evidence_dir / "inputs"
        gold_copy = inputs / "gold"
        candidate_copy = inputs / "candidate"
        input_digests = (
            self._copy_inputs(gold_root, gold_copy, config),
            self._copy_inputs(candidate_root, candidate_copy, config),
        )
        eqy_path = Path(environment["tools"]["eqy"]["path"])
        deadline = time.monotonic() + config.timeout_seconds
        config_path = evidence_dir / "equivalence.eqy"
        config_path.write_text(
            self._render_config(config, evidence_dir), encoding="utf-8"
        )
        sequential = self._run_one(
            eqy_path, config_path, evidence_dir / "eqy-work",
            evidence_dir / "equivalence.log", config.jobs, deadline,
            process_callback, log_callback,
        )
        verdict = sequential["verdict"]
        reason = sequential["reason"]
        returncode = sequential["returncode"]
        command = sequential["command"]
        partitions = tuple(sequential["partitions"])
        resources = dict(sequential["resources"])
        reset_proof: dict[str, Any] = {}
        if config.reset_port:
            reset_proof = {"verdict": "not_run", "reason": "sequential proof did not pass"}
            if verdict == "proved":
                reset_path = evidence_dir / "reset-start.eqy"
                reset_path.write_text(
                    self._render_config(config, evidence_dir, reset_start=True),
                    encoding="utf-8",
                )
                reset_run = self._run_one(
                    eqy_path, reset_path, evidence_dir / "reset-start-work",
                    evidence_dir / "reset-start.log", config.jobs, deadline,
                    process_callback, log_callback,
                )
                reset_proof = {
                    key: value for key, value in reset_run.items()
                    if key != "log"
                }
                partitions = (*partitions, *(
                    {**item, "name": "reset-start:" + item["name"],
                     "phase": "reset-start"}
                    for item in reset_run["partitions"]
                ))
                resources = {
                    "wall_time_seconds": round(
                        resources["wall_time_seconds"]
                        + reset_run["resources"]["wall_time_seconds"], 6,
                    ),
                    "peak_rss_bytes": max(
                        resources["peak_rss_bytes"],
                        reset_run["resources"]["peak_rss_bytes"],
                    ),
                    "peak_swap_bytes": max(
                        resources["peak_swap_bytes"],
                        reset_run["resources"]["peak_swap_bytes"],
                    ),
                    "cpu_seconds": round(
                        resources["cpu_seconds"]
                        + reset_run["resources"]["cpu_seconds"], 6,
                    ),
                    "memory_limit_bytes": None,
                }
                returncode = reset_run["returncode"]
                if reset_run["verdict"] != "proved":
                    verdict = reset_run["verdict"]
                    reason = "reset-start proof: " + reset_run["reason"]
                else:
                    reason = (
                        "sequential and reset-start partitions completed "
                        "unbounded PDR proofs"
                    )
        summary = {
            "verdict": verdict,
            "reason": reason,
            "returncode": returncode,
            "partitions": list(partitions),
            "contract": config.contract(),
            "tool_versions": _environment_versions(environment),
            "input_digests": list(input_digests),
            "resources": resources,
            "command": list(command),
            "reset_proof": reset_proof,
        }
        summary_path = evidence_dir / "equivalence-report.json"
        summary_path.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        artifacts = tuple(_collect_evidence(evidence_dir))
        return EquivalenceResult(
            verdict=verdict, returncode=returncode, reason=reason,
            partitions=partitions, contract=config.contract(),
            tool_versions=_environment_versions(environment),
            input_digests=input_digests, resources=resources,
            artifacts=artifacts, command=command, reset_proof=reset_proof,
        )

    def _run_one(
        self,
        eqy_path: Path,
        config_path: Path,
        workdir: Path,
        log_path: Path,
        jobs: int,
        deadline: float,
        process_callback: Callable[[subprocess.Popen[str] | None], None] | None,
        log_callback: Callable[[str], None] | None,
    ) -> dict[str, Any]:
        command = (
            str(eqy_path), "-f", "-j", str(jobs),
            "-d", str(workdir), str(config_path),
        )
        environment = os.environ.copy()
        environment["PATH"] = os.pathsep.join([
            str(eqy_path.parent), environment.get("PATH", ""),
        ])
        started = time.monotonic()
        timed_out = started >= deadline
        returncode: int | None = None
        peak_rss = peak_swap = 0
        cpu_seconds = 0.0
        read_offset = 0
        try:
            if timed_out:
                log_path.write_text(
                    "EQY proof exceeded the shared equivalence deadline\n",
                    encoding="utf-8",
                )
            else:
                with log_path.open("w", encoding="utf-8") as log_handle:
                    process = subprocess.Popen(
                        command, cwd=log_path.parent, env=environment,
                        stdin=subprocess.DEVNULL, stdout=log_handle,
                        stderr=subprocess.STDOUT, text=True, start_new_session=True,
                    )
                    if process_callback:
                        process_callback(process)
                    while process.poll() is None:
                        peak_rss, peak_swap, cpu_seconds = _sample_process_tree(
                            process.pid, peak_rss, peak_swap, cpu_seconds,
                        )
                        read_offset = _forward_log(log_path, read_offset, log_callback)
                        if time.monotonic() >= deadline:
                            timed_out = True
                            _terminate_process_group(process)
                            break
                        time.sleep(0.1)
                    try:
                        returncode = process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        _terminate_process_group(process, force=True)
                        returncode = process.wait(timeout=5)
        except OSError as exc:
            log_path.write_text(f"Unable to start EQY: {exc}\n", encoding="utf-8")
        finally:
            if process_callback:
                process_callback(None)
        _forward_log(log_path, read_offset, log_callback)
        partitions = tuple(self._partition_results(workdir))
        verdict, reason = self._classify(
            workdir, log_path.read_text(encoding="utf-8", errors="replace"),
            returncode, timed_out, partitions,
        )
        return {
            "verdict": verdict, "reason": reason, "returncode": returncode,
            "partitions": partitions, "command": command,
            "resources": {
                "wall_time_seconds": round(time.monotonic() - started, 6),
                "peak_rss_bytes": peak_rss,
                "peak_swap_bytes": peak_swap,
                "cpu_seconds": round(cpu_seconds, 6),
                "memory_limit_bytes": None,
            },
        }

    @staticmethod
    def _render_config(
        config: EquivalenceConfig, evidence_dir: Path, *, reset_start: bool = False,
    ) -> str:
        def side(name: str) -> list[str]:
            root = evidence_dir / "inputs" / name
            options = ["-formal", "-sv"]
            options.extend(f"-I{_yosys_quote(str(root / path))}" for path in config.include_dirs)
            options.extend(f"-D{define}" for define in config.defines)
            files = " ".join(
                _yosys_quote(str(root / relative)) for relative in config.source_files
            )
            lines = ["read_verilog " + " ".join([*options, files])]
            for parameter, value in sorted(config.parameters.items()):
                lines.append(
                    f"chparam -set {parameter} {value} {config.top_module}"
                )
            lines.extend([
                f"hierarchy -check -top {config.top_module}",
                f"prep -top {config.top_module}",
                "memory_map",
            ])
            if reset_start:
                # Keep reset asserted across a clock edge.  With Yosys sim,
                # rstlen=1 releases it before the first edge and can write
                # unconstrained input-driven state into the initial register.
                reset_option = "-reset" if config.reset_active == "high" else "-resetn"
                lines.append(
                    f"sim -clock {config.clock_port} {reset_option} "
                    f"{config.reset_port} -rstlen 2 -n 1 -w"
                )
            return lines

        return "\n".join([
            "# Generated by Chip Nebula. Unknown values are preserved.",
            "# PASS requires every EQY partition to complete an unbounded PDR proof.",
            "[gold]", *side("gold"), "", "[gate]", *side("candidate"), "",
            "[strategy pdr]", "use sby", "engine abc pdr -rfi", "xprop on", "",
        ])

    @staticmethod
    def _copy_inputs(root: Path, destination: Path, config: EquivalenceConfig) -> str:
        relative_files = set(config.source_files)
        for include in config.include_dirs:
            include_path = _resolved_inside(root, include)
            if not include_path.is_dir():
                raise OptimizationError(f"include directory does not exist: {include}")
            for path in include_path.rglob("*"):
                if path.is_file() and not path.is_symlink():
                    relative_files.add(path.relative_to(root).as_posix())
        digest = hashlib.sha256()
        for relative in sorted(relative_files):
            source = _resolved_inside(root, relative)
            if not source.is_file() or (root / relative).is_symlink():
                raise OptimizationError(f"formal input is missing or symbolic: {relative}")
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            content = source.read_bytes()
            digest.update(relative.encode("utf-8") + b"\0")
            digest.update(hashlib.sha256(content).digest())
        return "sha256:" + digest.hexdigest()

    @staticmethod
    def _partition_results(workdir: Path) -> list[dict[str, str]]:
        partitions: list[dict[str, str]] = []
        strategy_root = workdir / "strategies"
        if not strategy_root.is_dir():
            return partitions
        for status_path in sorted(strategy_root.glob("*/pdr/status")):
            status = status_path.read_text(encoding="utf-8", errors="replace").strip()
            partitions.append({
                "name": status_path.parent.parent.name,
                "strategy": "pdr",
                "status": status.split()[0].lower() if status else "error",
                "evidence": status_path.relative_to(workdir.parent).as_posix(),
            })
        return partitions

    @staticmethod
    def _classify(
        workdir: Path, log: str, returncode: int | None, timed_out: bool,
        partitions: Sequence[Mapping[str, str]],
    ) -> tuple[str, str]:
        lowered = log.lower()
        if timed_out or (workdir / "TIMEOUT").exists():
            return "timeout", "EQY proof exceeded the configured timeout"
        explicit_oom = any(marker in lowered for marker in (
            "out of memory", "oom-kill", "oom_kill", "cannot allocate memory",
        ))
        if explicit_oom:
            return "resource_exhausted", "formal tool reported memory exhaustion"
        if returncode in {-9, 137}:
            return "resource_exhausted", (
                "formal process was killed (possible exit 137); the host did not provide "
                "an explicit OOM marker"
            )
        statuses = {str(item.get("status", "")) for item in partitions}
        if (
            returncode == 0 and (workdir / "PASS").exists() and partitions
            and statuses == {"pass"}
            and "successfully proved designs equivalent" in lowered
        ):
            return "proved", "all EQY partitions completed an unbounded PDR proof"
        if (workdir / "FAIL").exists() or "partitions not equivalent" in lowered:
            return "counterexample", "EQY found a non-equivalent partition or counterexample"
        if (workdir / "UNKNOWN").exists() or "equivalence unknown" in lowered:
            return "inconclusive", "EQY could not complete the proof"
        if not partitions and returncode == 0:
            return "inconclusive", "EQY produced no independently checkable partition results"
        return "unsupported", "formal tool failed before producing a valid proof verdict"

    def _bin_dir(self) -> Path | None:
        root = self._toolchain_root()
        if not root:
            return None
        for candidate in (root / "oss-cad-suite" / "bin", root / "bin"):
            if candidate.is_dir() and (candidate / "eqy").is_file():
                return candidate
        for candidate in (root / "oss-cad-suite" / "bin", root / "bin"):
            if candidate.is_dir():
                return candidate
        return None

    def _toolchain_root(self) -> Path | None:
        if self.toolchain_root:
            return self.toolchain_root
        configured = os.environ.get("CHIP_NEBULA_RTL2GDS_TOOL_ROOT", "").strip()
        candidates: list[Path] = []
        if configured:
            candidates.append(Path(configured).expanduser())
        source = Path(__file__).resolve()
        executable = Path(sys.executable).resolve()
        for anchor in (source, executable):
            for parent in (anchor.parent, *anchor.parents):
                candidates.append(parent / "build" / "rtl2gds-tools")
        candidates.append(Path.home() / ".cache" / "chip-nebula" / "rtl2gds-tools")
        for candidate in candidates:
            if candidate.is_dir():
                return candidate.resolve()
        return None

    @staticmethod
    def _resolve_tool(environment: str, name: str, bin_dir: Path | None) -> Path | None:
        configured = os.environ.get(environment, "").strip()
        candidates = [Path(configured).expanduser()] if configured else []
        if bin_dir:
            candidates.append(bin_dir / name)
        found = shutil.which(name)
        if found:
            candidates.append(Path(found))
        for candidate in candidates:
            if candidate.is_file() and os.access(candidate, os.X_OK):
                return candidate.resolve()
        return None


def pareto_frontier(
    reports: Sequence[Mapping[str, Any]],
    *, reference_conditions: Mapping[str, Any] | None = None,
    require_reset_proof: bool = True,
) -> list[dict[str, Any]]:
    """Return deterministic, mutually comparable area/timing/power candidates.

    Reports with different implementation conditions or measurement levels are
    excluded from the same comparison.  Lower area and power are better;
    higher estimated Fmax is better.  Missing metrics never dominate a fully
    measured candidate.
    """
    cohorts: dict[str, list[dict[str, Any]]] = {}
    reference_signature = (
        _condition_signature(reference_conditions)
        if reference_conditions is not None else None
    )
    for report in reports:
        gates = report.get("gates")
        metrics = report.get("metrics")
        conditions = report.get("conditions")
        if not isinstance(gates, Mapping) or not all(
            gates.get(name) is True for name in ("regression", "equivalence", "sta", "drc", "lvs")
        ):
            continue
        if require_reset_proof and gates.get("reset_start") is not True:
            continue
        if not isinstance(metrics, Mapping) or not isinstance(conditions, Mapping):
            continue
        if report.get("measurement_level") != "full-physical":
            continue
        required_conditions = (
            "platform", "pvt", "clock_period_ns", "constraints_digest",
            "library_digest",
        )
        if any(not conditions.get(name) for name in required_conditions):
            continue
        if (
            type(conditions["clock_period_ns"]) not in {int, float}
            or not math.isfinite(conditions["clock_period_ns"])
            or conditions["clock_period_ns"] <= 0
        ):
            continue
        area = _metric(metrics, ("area_um2", "core_area_um2", "die_area_um2"), float("inf"))
        power = _metric(metrics, ("power_w", "total_power_w", "estimated_total_power_w"), float("inf"))
        fmax = _metric(metrics, ("estimated_fmax_hz", "fmax_hz"), float("-inf"))
        if not all(math.isfinite(value) for value in (area, power, fmax)):
            continue
        if area <= 0 or power < 0 or fmax <= 0:
            continue
        current_signature = _condition_signature(conditions)
        if reference_signature is not None and current_signature != reference_signature:
            continue
        normalized = dict(report)
        normalized["_objectives"] = (area, power, -fmax)
        cohorts.setdefault(current_signature, []).append(normalized)
    if not cohorts:
        return []
    if reference_signature is not None:
        eligible = cohorts.get(reference_signature, [])
    else:
        largest = max(len(group) for group in cohorts.values())
        leaders = [group for group in cohorts.values() if len(group) == largest]
        if len(leaders) != 1:
            raise OptimizationError(
                "PPA reports have ambiguous implementation conditions; "
                "supply frozen reference_conditions"
            )
        eligible = leaders[0]
    result: list[dict[str, Any]] = []
    for candidate in eligible:
        objectives = candidate["_objectives"]
        dominated = any(
            other is not candidate
            and all(left <= right for left, right in zip(other["_objectives"], objectives))
            and any(left < right for left, right in zip(other["_objectives"], objectives))
            for other in eligible
        )
        if not dominated:
            item = {key: value for key, value in candidate.items() if key != "_objectives"}
            result.append(item)
    return sorted(result, key=lambda item: str(item.get("candidate_artifact_id", "")))


def _condition_signature(conditions: Mapping[str, Any]) -> str:
    try:
        serialized = json.dumps(
            dict(conditions), sort_keys=True, separators=(",", ":"),
            ensure_ascii=False, allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise OptimizationError("PPA conditions must be finite JSON values") from exc
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _safe_relative(value: str, field_name: str) -> str:
    path = PurePosixPath(str(value).replace("\\", "/"))
    if (
        path.is_absolute() or path.as_posix() in {"", "."} or ".." in path.parts
        or any(character in str(value) for character in "\x00\n\r")
    ):
        raise OptimizationError(f"{field_name} must stay inside the project")
    return path.as_posix()


def _resolved_inside(root: Path, relative: str) -> Path:
    relative = _safe_relative(relative, "formal input")
    path = (root / relative).resolve()
    if root != path and root not in path.parents:
        raise OptimizationError(f"formal input escapes the project: {relative}")
    return path


def _yosys_quote(value: str) -> str:
    if "\n" in value or "\r" in value or "\x00" in value:
        raise OptimizationError("formal path contains an invalid character")
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _tool_version(path: Path, flag: str) -> str:
    try:
        result = subprocess.run(
            [str(path), flag], capture_output=True, text=True,
            timeout=10, errors="replace",
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    output = (result.stdout or result.stderr).strip()
    return output.splitlines()[0][:500] if output else ""


def _environment_versions(environment: Mapping[str, Any]) -> dict[str, str]:
    return {
        name: str(item.get("version", ""))
        for name, item in environment.get("tools", {}).items()
        if isinstance(item, Mapping) and item.get("version")
    }


def _sample_process_tree(
    pid: int, peak_rss: int, peak_swap: int, cpu_seconds: float,
) -> tuple[int, int, float]:
    try:
        root = psutil.Process(pid)
        processes = [root, *root.children(recursive=True)]
    except (psutil.Error, OSError):
        return peak_rss, peak_swap, cpu_seconds
    rss = 0
    swap = 0
    cpu = 0.0
    for process in processes:
        try:
            memory = process.memory_full_info()
            times = process.cpu_times()
        except (psutil.Error, OSError):
            continue
        rss += int(getattr(memory, "rss", 0))
        swap += int(getattr(memory, "swap", 0))
        cpu += float(times.user + times.system)
    return max(peak_rss, rss), max(peak_swap, swap), max(cpu_seconds, cpu)


def _forward_log(
    path: Path, offset: int, callback: Callable[[str], None] | None,
) -> int:
    if not path.is_file():
        return offset
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        handle.seek(offset)
        chunk = handle.read()
        new_offset = handle.tell()
    if chunk and callback:
        callback(chunk)
    return new_offset


def _terminate_process_group(process: subprocess.Popen[str], force: bool = False) -> None:
    """Signal only the private session owned by this EQY process.

    A runner can exit while a proof child survives.  Check the process group
    again after SIGTERM instead of assuming a reaped parent means completion.
    """
    pid = getattr(process, "pid", None)
    if type(pid) is not int or pid <= 1:
        return
    try:
        pgid = os.getpgid(pid)
    except ProcessLookupError:
        return
    if pgid <= 1 or pgid != pid or pgid == os.getpgrp():
        return
    try:
        os.killpg(pgid, signal.SIGKILL if force else signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        return
    if force:
        return
    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return
    try:
        os.killpg(pgid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        return
    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        pass


def _collect_evidence(root: Path) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        relative = path.relative_to(root).as_posix()
        # Source inputs are identified by the aggregate input digest and are
        # already carried by the immutable RTL artifacts.  Do not duplicate
        # them in the formal evidence catalog.
        if relative.startswith("inputs/"):
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        result.append({
            "path": relative,
            "size": path.stat().st_size,
            "sha256": "sha256:" + digest,
            "kind": "counterexample" if path.suffix.lower() in {".vcd", ".yw"} else "report",
        })
    return result


def _empty_resources() -> dict[str, Any]:
    return {
        "wall_time_seconds": 0.0, "peak_rss_bytes": 0,
        "peak_swap_bytes": 0, "cpu_seconds": 0.0,
        "memory_limit_bytes": None,
    }


def _metric(metrics: Mapping[str, Any], names: Sequence[str], default: float) -> float:
    for name in names:
        value = metrics.get(name)
        if type(value) in {int, float} and math.isfinite(value):
            return float(value)
    return default
