"""Desktop RTL workbench services.

The workbench deliberately keeps user source in the primary checkout.  Every
operation is bracketed by private Git snapshots created with a temporary index,
so neither the current branch nor the user's staging area is modified.
"""

from __future__ import annotations

import datetime as dt
import fcntl
import glob
import hashlib
import json
import math
import os
import posixpath
import re
import shlex
import shutil
import subprocess
import tempfile
import threading
import time
import uuid
import zipfile
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path, PurePosixPath
from typing import Any

import psutil
import yaml

from chip_nebula.adapters.pool_manager import AgentPoolManager
from chip_nebula.adapters.scope_check import detect_changed_paths, violations
from chip_nebula.dashboard.process import RunManager
from chip_nebula.gates.error_parser import parse_errors
from chip_nebula.models.task_manifest import (
    FileTarget, TaskContext, TaskError, TaskManifest,
)
from chip_nebula.project import ensure_project_definition, project_definition_files
from chip_nebula.taskgraph.generic_acceptance import (
    GenericAcceptanceError, GenericAcceptanceWorkspace, checker_contract,
    validation_command, verify_checker, verify_assembly_source_hashes,
)
from chip_nebula.taskgraph.existing_checker_review import preview_existing_checker
from chip_nebula.taskgraph.input_remediation import propose_input_remediation
from chip_nebula.taskgraph.implementation_constraints import (
    ImplementationConstraintsError,
    project_constraint_category,
    render_sdc,
    unavailable_constraint_categories,
    validate_constraint_questions,
    validate_implementation_constraints,
)
from chip_nebula.taskgraph.generic_rtl import (
    GenericRTLContractError, ast_artifact_path, elaboration_command,
    generation_target, generation_include_files, inspect_elaboration, verilator_ast_format,
    verify_generated_rtl, xml_artifact_path,
)
from chip_nebula.taskgraph.domain import Role, path_scope_covers
from chip_nebula.taskgraph.optimization import (
    EquivalenceConfig, FormalEquivalenceRunner, OptimizationError,
)
from chip_nebula.taskgraph.physical import (
    PhysicalFlow, PhysicalFlowConfig, PhysicalFlowError,
)
from chip_nebula.taskgraph.physical_project import (
    PhysicalProjectError, PhysicalProjectSelection, PhysicalProjectWizard,
    normalize_top_parameters,
)
from chip_nebula.taskgraph.static_recipe import load_project_static_roles
from chip_nebula.taskgraph.specs import SpecificationError, SpecificationWorkspace
from chip_nebula.taskgraph.acceptance_plan import validate_acceptance_plan
from chip_nebula.taskgraph.specir import specir_revision_id
from chip_nebula.taskgraph.spec_catalog import specification_catalog_context
from chip_nebula.taskgraph.stage_skills import load_stage_skill, verify_stage_skill
from chip_nebula.taskgraph.generated_submodule import (
    GeneratedSubmoduleError, generated_submodules, submodule_contract,
    verify_submodule,
)
from chip_nebula.taskgraph.tool_executor import DeterministicToolExecutor, ToolCommand
from chip_nebula.taskgraph.yasimulator import RegressionCommand, YASimulator


_SOURCE_SUFFIXES = {".v", ".sv", ".vh", ".svh"}
_IMPORT_TEXT_SUFFIXES = _SOURCE_SUFFIXES | {
    ".hex", ".mem", ".txt", ".dat", ".f", ".flist",
}
_TEXT_SUFFIXES = _IMPORT_TEXT_SUFFIXES | {
    ".c", ".cc", ".cpp", ".h", ".hpp", ".py", ".tcl", ".sdc",
    ".mk", ".sh", ".bash", ".cfg", ".toml", ".xml",
    ".md", ".json", ".yaml", ".yml", ".cnprj", "",
}
_SKIP_DIRS = {
    ".git", ".chip_nebula", ".claude", ".codex", ".omo", ".opencode",
    "node_modules", "__pycache__",
}
_RUN_ID_RE = re.compile(r"^[A-Za-z0-9_.:-]+$")


def _intersect_path_scopes(
    ceilings: tuple[str, ...], grants: tuple[str, ...],
) -> tuple[str, ...]:
    """Return the narrowest provable overlap of two structured path grants."""
    result: list[str] = []
    for ceiling in ceilings:
        for grant in grants:
            overlap = (
                grant if path_scope_covers(ceiling, grant)
                else ceiling if path_scope_covers(grant, ceiling)
                else ""
            )
            if overlap and overlap not in result:
                result.append(overlap)
    return tuple(result)
_ARTIFACT_TEXT_PREVIEW_LIMIT = 8 * 1024 * 1024
_ASSISTANT_WORKSPACES = {
    "project-manager", "requirements", "ip-integration", "rtl-analysis",
    "simulation", "synthesis", "implementation", "signoff", "complete-flow",
}
_ASSISTANT_MODES = {"ask", "plan"}


def _process_start_token(pid: int) -> str:
    """Return a stable process start token used to reject PID reuse."""
    if type(pid) is not int or pid <= 1:
        return ""
    try:
        stat = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8")
    except OSError:
        try:
            # psutil uses the native process API on macOS and other systems
            # without /proc.  Creation time changes when a PID is reused.
            started = psutil.Process(pid).create_time()
        except (psutil.Error, OSError, ValueError):
            return ""
        return f"psutil:{started:.6f}"
    _prefix, separator, suffix = stat.rpartition(")")
    fields = suffix.strip().split() if separator else []
    # The suffix starts at field 3 (state); starttime is field 22.
    # Keep the historical Linux token format so a rolling backend update does
    # not mistake an older live owner for stale state.
    return fields[19] if len(fields) > 19 else ""


class WorkbenchError(RuntimeError):
    pass


class WorkbenchConflict(WorkbenchError):
    def __init__(self, message: str, paths: list[str] | None = None) -> None:
        super().__init__(message)
        self.paths = paths or []


@dataclass
class WorkbenchConfig:
    top_module: str = ""
    top_parameters: dict[str, int] = field(default_factory=dict)
    source_globs: list[str] = field(
        default_factory=lambda: ["**/*.sv", "**/*.v", "**/*.svh", "**/*.vh"]
    )
    validation_mode: str = "commands"
    design_files: list[str] = field(default_factory=list)
    testbench_files: list[str] = field(default_factory=list)
    simulation_assets: list[str] = field(default_factory=list)
    include_dirs: list[str] = field(default_factory=list)
    defines: list[str] = field(default_factory=list)
    filelists: list[str] = field(default_factory=list)
    simulation_top: str = ""
    write_paths: list[str] = field(default_factory=lambda: ["rtl/**", "src/**"])
    lint_command: str = ""
    simulation_command: str = ""
    workdir: str = "."
    timeout: int = 900
    agent_timeout: int = 3600
    success_pattern: str = ""
    success_evidence: dict[str, Any] = field(default_factory=dict)
    report_globs: list[str] = field(default_factory=list)
    waveform_globs: list[str] = field(default_factory=lambda: ["**/*.vcd", "**/*.fst"])
    physical: PhysicalFlowConfig = field(default_factory=PhysicalFlowConfig)

    @classmethod
    def from_document(cls, document: Any) -> "WorkbenchConfig":
        raw = document if isinstance(document, dict) else {}
        config = cls()
        for name in asdict(config):
            if name in raw:
                if name == "physical":
                    config.physical = PhysicalFlowConfig.from_document(raw[name])
                else:
                    setattr(config, name, raw[name])
        config.source_globs = _string_list(config.source_globs, "source_globs")
        try:
            config.top_parameters = normalize_top_parameters(config.top_parameters)
        except PhysicalProjectError as exc:
            raise WorkbenchError(str(exc)) from exc
        config.validation_mode = str(config.validation_mode).strip() or "commands"
        if config.validation_mode not in {"commands", "fileset"}:
            raise WorkbenchError("validation_mode must be commands or fileset")
        config.design_files = _relative_file_list(
            config.design_files, "design_files", {".v", ".sv"}
        )
        config.testbench_files = _relative_file_list(
            config.testbench_files, "testbench_files", {".v", ".sv"}
        )
        config.simulation_assets = _relative_asset_list(
            config.simulation_assets, "simulation_assets"
        )
        config.filelists = _relative_file_list(
            config.filelists, "filelists", {".f", ".flist"}
        )
        config.include_dirs = _relative_directory_list(
            config.include_dirs, "include_dirs"
        )
        config.defines = _define_list(config.defines)
        config.simulation_top = str(config.simulation_top).strip()
        if config.simulation_top and not re.fullmatch(
            r"[A-Za-z_][A-Za-z0-9_$]*", config.simulation_top
        ):
            raise WorkbenchError("simulation_top must be a Verilog identifier")
        config.write_paths = _string_list(config.write_paths, "write_paths")
        config.report_globs = _string_list(config.report_globs, "report_globs")
        config.waveform_globs = _string_list(config.waveform_globs, "waveform_globs")
        config.success_evidence = _success_evidence(config.success_evidence)
        evidence_path = config.success_evidence.get("path", "")
        if evidence_path and evidence_path not in config.report_globs:
            config.report_globs.append(evidence_path)
        config.timeout = max(1, min(int(config.timeout), 86_400))
        config.agent_timeout = max(1, min(int(config.agent_timeout), 86_400))
        if config.physical.enabled and not config.physical.design:
            config.physical.design = str(config.top_module).strip()
        raw_workdir = str(config.workdir).strip().replace("\\", "/") or "."
        workdir = PurePosixPath(raw_workdir)
        if (
            workdir.is_absolute() or ".." in workdir.parts
            or any(character in raw_workdir for character in "*?[\x00\n\r")
        ):
            raise WorkbenchError("workdir must stay inside the project")
        config.workdir = workdir.as_posix()
        return config


def _string_list(value: Any, name: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise WorkbenchError(f"{name} must be a list of strings")
    return [item.strip() for item in value if item.strip()]


def _relative_file_list(
    value: Any, name: str, suffixes: set[str],
) -> list[str]:
    result: list[str] = []
    for item in _string_list(value, name):
        path = PurePosixPath(item.replace("\\", "/"))
        if (
            path.is_absolute() or ".." in path.parts or path.as_posix() in {"", "."}
            or any(character in item for character in "*?[\x00\n\r")
            or path.suffix.lower() not in suffixes
        ):
            raise WorkbenchError(f"{name} must contain project-relative files")
        if path.as_posix() not in result:
            result.append(path.as_posix())
    return result


def _relative_directory_list(value: Any, name: str) -> list[str]:
    result: list[str] = []
    for item in _string_list(value, name):
        path = PurePosixPath(item.replace("\\", "/"))
        if (
            path.is_absolute() or ".." in path.parts
            or any(character in item for character in "*?[\x00\n\r")
        ):
            raise WorkbenchError(f"{name} must contain project-relative directories")
        normalized = path.as_posix()
        if normalized not in result:
            result.append(normalized)
    return result


def _relative_asset_list(value: Any, name: str) -> list[str]:
    result: list[str] = []
    for item in _string_list(value, name):
        path = PurePosixPath(item.replace("\\", "/"))
        if (
            path.is_absolute() or ".." in path.parts
            or path.as_posix() in {"", "."}
            or any(character in item for character in "*?[\x00\n\r")
        ):
            raise WorkbenchError(f"{name} must contain project-relative files")
        if path.as_posix() not in result:
            result.append(path.as_posix())
    return result


def _path_from_workdir(relative: str, workdir: str) -> str:
    """Express a project-relative path from a configured project workdir."""
    return PurePosixPath(posixpath.relpath(relative, start=workdir or ".")).as_posix()


def _command_from_project_root(command: str, workdir: str) -> str:
    if not command or workdir in {"", "."}:
        return command
    return f"cd {shlex.quote(workdir)} && {command}"


def _define_list(value: Any) -> list[str]:
    result: list[str] = []
    for item in _string_list(value, "defines"):
        if (
            not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*(?:=[^\s\x00]+)?", item)
            or "\n" in item or "\r" in item
        ):
            raise WorkbenchError("defines must use NAME or NAME=value")
        if item not in result:
            result.append(item)
    return result


def _success_evidence(value: Any) -> dict[str, Any]:
    """Validate a deterministic, project-relative validation success criterion."""
    if value in (None, {}):
        return {}
    if not isinstance(value, dict):
        raise WorkbenchError("success_evidence must be an object")
    kind = value.get("type")
    if kind not in {"file_regex", "json_value"}:
        raise WorkbenchError(
            "success_evidence.type must be file_regex or json_value"
        )
    raw_path = value.get("path")
    if not isinstance(raw_path, str) or not raw_path.strip() or "\x00" in raw_path:
        raise WorkbenchError("success_evidence.path must be a project-relative file")
    normalized = raw_path.strip().replace("\\", "/")
    path = PurePosixPath(normalized)
    if path.is_absolute() or ".." in path.parts or normalized in {"", "."}:
        raise WorkbenchError("success_evidence.path must stay inside the project")
    if any(character in normalized for character in "*?["):
        raise WorkbenchError("success_evidence.path must name one file, not a glob")
    result: dict[str, Any] = {"type": kind, "path": path.as_posix()}
    if kind == "file_regex":
        pattern = value.get("pattern")
        if not isinstance(pattern, str) or not pattern:
            raise WorkbenchError("success_evidence.pattern cannot be empty")
        try:
            re.compile(pattern)
        except re.error as exc:
            raise WorkbenchError(f"success_evidence.pattern is invalid: {exc}") from exc
        result["pattern"] = pattern
        return result
    pointer = value.get("pointer", "")
    if not isinstance(pointer, str) or (pointer and not pointer.startswith("/")):
        raise WorkbenchError("success_evidence.pointer must be empty or start with /")
    if "equals" not in value:
        raise WorkbenchError("success_evidence.equals is required for json_value")
    result.update({"pointer": pointer, "equals": value["equals"]})
    return result


def _literal_glob_root(pattern: str) -> PurePosixPath | None:
    """Find the non-wildcard directory prefix of an artifact glob."""
    normalized = pattern.replace("\\", "/").strip().lstrip("./")
    candidate = PurePosixPath(normalized)
    if not normalized or candidate.is_absolute() or ".." in candidate.parts:
        return None
    literal: list[str] = []
    wildcard_found = False
    for part in candidate.parts:
        if any(character in part for character in "*?["):
            wildcard_found = True
            break
        literal.append(part)
    if not wildcard_found and literal:
        literal.pop()
    if not literal:
        return None
    return PurePosixPath(*literal)


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def _normalize_task_error_paths(
    errors: list[TaskError], workspace: Path, cwd: str,
) -> list[TaskError]:
    """Map tool locations back to paths that the project editor can open."""
    root = workspace.resolve()
    command_root = (root / cwd).resolve()
    for error in errors:
        raw = error.file.strip()
        if not raw:
            continue
        candidate = Path(raw)
        resolved = candidate.resolve() if candidate.is_absolute() else (
            command_root / candidate
        ).resolve()
        try:
            relative = resolved.relative_to(root)
        except ValueError:
            continue
        if resolved.is_file():
            error.file = relative.as_posix()
    return errors


class WorkbenchProject:
    def __init__(self, root: Path, project_file: Path | None = None) -> None:
        self.root = root.resolve()
        self.project_file = project_file.resolve() if project_file else None
        if self.project_file is not None and (
            self.project_file.suffix.lower() != ".cnprj"
            or self.project_file.parent != self.root
        ):
            raise WorkbenchError("明确选择的 .cnprj 必须位于工程根目录")
        self.nebula = self.root / ".chip_nebula"
        self.state_root = self.nebula / "workbench"
        self.config_path = self.nebula / "workbench.yaml"
        self.operations_dir = self.state_root / "operations"
        self.runs_dir = self.state_root / "runs"
        self.workspaces_dir = self.state_root / "workspaces"
        self.assistant_dir = self.state_root / "assistant"
        self.execution_plans_dir = self.state_root / "execution-plans"

    def is_git_repository(self) -> bool:
        return self._git("rev-parse", "--is-inside-work-tree", check=False).returncode == 0

    def config(self) -> WorkbenchConfig:
        target, template = self._config_locations()
        source = target if target.is_file() else template
        if not source.is_file():
            return WorkbenchConfig()
        try:
            return WorkbenchConfig.from_document(
                yaml.safe_load(source.read_text(encoding="utf-8"))
            )
        except (OSError, yaml.YAMLError, PhysicalFlowError, TypeError, ValueError) as exc:
            raise WorkbenchError(f"invalid workbench config: {exc}") from exc

    def save_config(self, document: dict[str, Any]) -> WorkbenchConfig:
        try:
            config = WorkbenchConfig.from_document(document)
        except (PhysicalFlowError, TypeError, ValueError) as exc:
            raise WorkbenchError(f"invalid workbench config: {exc}") from exc
        target, _template = self._config_locations()
        target.parent.mkdir(parents=True, exist_ok=True)
        probe = target.with_name(target.name + ".tmp")
        probe.write_text(
            yaml.safe_dump(asdict(config), allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        probe.replace(target)
        return config

    @staticmethod
    def _remove_reset_target(path: Path) -> bool:
        """Remove one explicitly selected reset target without following links."""
        if path.is_symlink() or path.is_file():
            path.unlink()
            return True
        if path.is_dir():
            shutil.rmtree(path)
            return True
        return False

    def reset_state(self) -> dict[str, Any]:
        """Clear runtime state, generated specifications and project constraints.

        Source files, the Git checkout, the workbench configuration, staged
        skills, IP packages and platform metadata are deliberately preserved.
        Everything else under ``.chip_nebula`` is runtime state owned by the
        dashboard and may be recreated on demand.
        """
        if self.nebula.is_symlink():
            raise WorkbenchError(".chip_nebula 不能是符号链接，拒绝清理")
        physical_root = self.root / "physical"
        constraints_root = physical_root / "chip-nebula"
        for parent in (physical_root, constraints_root):
            if parent.is_symlink():
                raise WorkbenchError(f"{parent.relative_to(self.root)} 不能是符号链接，拒绝清理")

        removed: list[str] = []
        preserved = [
            ".chip_nebula/workbench.yaml",
            ".chip_nebula/platform_version",
            ".chip_nebula/shared/skills",
            ".chip_nebula/ip-library",
            ".git",
        ]

        # ``spec/`` is a platform-generated bundle (design document, CSIR,
        # diagnostics, decisions and acceptance plan), not user RTL input.
        # Remove it as one unit so no stale revision can leak into a fresh run.
        # Only these platform-generated constraint files belong to reset. Other
        # physical inputs, scripts, PDK views and flow definitions are preserved.
        candidates: list[Path] = [
            self.root / "spec",
            constraints_root / "implementation.constraints.json",
            constraints_root / "constraints.sdc",
        ]
        if self.nebula.exists():
            for child in self.nebula.iterdir():
                relative = child.relative_to(self.nebula)
                if relative.as_posix() in {"workbench.yaml", "platform_version", "ip-library"}:
                    continue
                if relative.parts == ("shared",):
                    # Keep the staged skills subtree but clear all shared
                    # memory/session databases and other runtime directories.
                    if child.is_dir() and not child.is_symlink():
                        candidates.extend(
                            nested for nested in child.iterdir()
                            if nested.name != "skills"
                        )
                    continue
                candidates.append(child)

        for target in candidates:
            # Refuse an unexpected symlink target, but unlink the symlink itself
            # when it is one of the generated/runtime entries.
            if target.is_symlink():
                target.unlink()
                removed.append(target.relative_to(self.root).as_posix())
                continue
            if not target.exists():
                continue
            self._remove_reset_target(target)
            removed.append(target.relative_to(self.root).as_posix())

        for directory in (constraints_root, physical_root):
            if directory.is_dir() and not any(directory.iterdir()):
                directory.rmdir()

        # The currently running desktop backend keeps a WorkbenchProject
        # instance alive.  Recreate its empty state root immediately so the
        # next Agent can acquire agent.lock without requiring an app restart.
        self.state_root.mkdir(parents=True, exist_ok=True)

        return {
            "reset": True,
            "removed": sorted(removed),
            "preserved": preserved,
            "message": "已清理可重建的工程运行态、spec 产物和生成的项目约束；源码、Git、配置、技能包与 IP 库保留",
        }

    def _config_locations(self) -> tuple[Path, Path]:
        definition = self.project_definition()
        if definition:
            workbench = definition["workbench"]
            return (
                self.root / str(workbench["config"]),
                self.root / str(workbench["template"]),
            )
        return self.config_path, self.root / "workbench.yaml"

    def fileset_issues(self, config: WorkbenchConfig | None = None) -> list[str]:
        config = config or self.config()
        if config.validation_mode != "fileset":
            return []
        issues: list[str] = []
        if not (self.root / config.workdir).is_dir():
            issues.append(f"Fileset 工作目录不存在：{config.workdir}")
        if not config.design_files and not config.filelists:
            issues.append("Fileset 至少需要一个设计文件或 filelist")
        for relative in [
            *config.design_files, *config.testbench_files,
            *config.simulation_assets, *config.filelists,
        ]:
            path = self.root / relative
            if not path.is_file():
                issues.append(f"Fileset 文件不存在：{relative}")
            elif self.root != path.resolve() and self.root not in path.resolve().parents:
                issues.append(f"Fileset 文件通过符号链接指向工程外部：{relative}")
        wizard = PhysicalProjectWizard(self.root)
        configured_defines = {item.split("=", 1)[0]: item for item in config.defines}
        for relative in config.filelists:
            filelist = self.root / relative
            if not filelist.is_file():
                continue
            if filelist.is_symlink() or not filelist.resolve().is_relative_to(self.root):
                issues.append(f"Fileset filelist 缺失、越界或经过符号链接：{relative}")
                continue
            diagnostics: list[dict[str, str]] = []
            wizard._filelist_sources(filelist, diagnostics)
            filelist_includes, filelist_defines = wizard._filelist_compile_options(
                filelist, diagnostics,
            )
            for include in filelist_includes:
                tool_path = self.root / config.workdir / include
                if tool_path.resolve() != (self.root / include).resolve():
                    issues.append(
                        f"filelist 的 +incdir+{include} 会从工作目录 {config.workdir} "
                        "解析到不同位置；请改用工程根工作目录或修正 filelist"
                    )
            for raw in filelist.read_text(encoding="utf-8", errors="replace").splitlines():
                line = raw.strip()
                if not line or line.startswith(("#", "//", "+", "-")):
                    continue
                candidate = Path(line)
                tool_path = candidate if candidate.is_absolute() else self.root / config.workdir / candidate
                if not tool_path.is_file() or not tool_path.resolve().is_relative_to(self.root):
                    issues.append(
                        f"filelist 源码 {line} 无法从工作目录 {config.workdir} 解析；"
                        "请改用工程根工作目录或修正 filelist"
                    )
            issues.extend(item["message"] for item in diagnostics
                          if item.get("code", "").startswith("FILELIST_")
                          and item.get("severity") == "error")
            for value in filelist_defines:
                name = value.split("=", 1)[0]
                if name in configured_defines and configured_defines[name] != value:
                    issues.append(
                        f"宏 {name} 在 Project Settings 或多个 filelist 中有不同取值，"
                        "请先确定一个版本"
                    )
                configured_defines[name] = value
        for relative in config.include_dirs:
            path = self.root / relative
            if not path.is_dir():
                issues.append(f"Fileset include 目录不存在：{relative}")
            elif self.root != path.resolve() and self.root not in path.resolve().parents:
                issues.append(f"Fileset include 目录通过符号链接指向工程外部：{relative}")
        if config.testbench_files and not config.simulation_top:
            issues.append("Fileset 包含测试文件时必须填写仿真顶层")
        return list(dict.fromkeys(issues))

    def validation_commands(
        self, config: WorkbenchConfig | None = None, kind: str = "all",
    ) -> list[tuple[str, str]]:
        config = config or self.config()
        if config.validation_mode == "commands":
            commands: list[tuple[str, str]] = []
            if kind in {"all", "lint"} and config.lint_command:
                commands.append(("lint", config.lint_command))
            if kind in {"all", "simulation"} and config.simulation_command:
                commands.append(("simulation", config.simulation_command))
            return commands
        issues = self.fileset_issues(config)
        if issues:
            raise WorkbenchError("；".join(issues))
        from_workdir = lambda relative: _path_from_workdir(relative, config.workdir)
        common = [
            *[f"-I{from_workdir(relative)}" for relative in config.include_dirs],
            *[f"-D{define}" for define in config.defines],
            *[
                value
                for relative in config.filelists
                for value in ("-f", from_workdir(relative))
            ],
        ]
        commands = []
        if kind in {"all", "lint"}:
            log_dir = from_workdir("build/chip-nebula-validation")
            args = ["verilator", "--lint-only", "--sv", "-Wall", "-Wno-fatal"]
            if config.top_module:
                args.extend(["--top-module", config.top_module])
            args.extend(
                f"-G{name}={value}"
                for name, value in config.top_parameters.items()
            )
            args.extend([*common, *map(from_workdir, config.design_files)])
            commands.append((
                "lint",
                f"mkdir -p {log_dir} && "
                + shlex.join(args)
                + f" 2>&1 | tee {log_dir}/lint.log",
            ))
        if kind in {"all", "simulation"} and config.testbench_files:
            log_dir = from_workdir("build/chip-nebula-validation")
            output = f"{log_dir}/simulation.vvp"
            args = ["iverilog", "-g2012"]
            if config.simulation_top:
                args.extend(["-s", config.simulation_top])
            args.extend([
                "-o", output, *common, *map(from_workdir, config.design_files),
                *map(from_workdir, config.testbench_files),
            ])
            command = (
                f"mkdir -p {log_dir} && "
                + shlex.join(args)
                + f" 2>&1 | tee {log_dir}/compile.log && "
                # Desktop runs have no interactive simulator console.  ``-n``
                # makes a testbench's normal ``$stop`` behave like ``$finish``
                # instead of waiting forever for user input.
                + shlex.join(["vvp", "-n", output])
                + f" 2>&1 | tee {log_dir}/simulation.log"
            )
            commands.append(("simulation", command))
        return commands

    def _fileset_design_sources(self, config: WorkbenchConfig) -> list[str]:
        sources = list(config.design_files)
        for relative in config.filelists:
            filelist = self.root / relative
            if not filelist.is_file():
                continue
            base = filelist.parent
            for raw in filelist.read_text(encoding="utf-8", errors="replace").splitlines():
                line = raw.strip()
                if not line or line.startswith(("#", "//", "-", "+")):
                    continue
                candidate = Path(line)
                if candidate.is_absolute():
                    path = candidate
                else:
                    # Verilator/Icarus resolve -f entries from the tool workdir.
                    # Older local lists may use the list's own directory, so
                    # retain that form as an explicit fallback.
                    from_workdir = self.root / config.workdir / candidate
                    from_filelist = base / candidate
                    path = from_workdir if from_workdir.is_file() else from_filelist
                try:
                    project_relative = path.resolve().relative_to(self.root).as_posix()
                except ValueError:
                    continue
                if path.is_file() and path.suffix.lower() in _SOURCE_SUFFIXES:
                    sources.append(project_relative)
        return list(dict.fromkeys(sources))

    def design_source_files(self, config: WorkbenchConfig | None = None) -> list[str]:
        """Return registered design RTL, without checker or runtime inputs."""
        config = config or self.config()
        candidates = (
            self._fileset_design_sources(config)
            if config.design_files or config.filelists
            else self._matching_files(config.source_globs)
        )
        testbenches = set(config.testbench_files)
        return list(dict.fromkeys(
            relative for relative in candidates
            if relative not in testbenches
            and PurePosixPath(relative).suffix.lower() in _SOURCE_SUFFIXES
        ))

    def _fileset_input_paths(self, config: WorkbenchConfig) -> set[str]:
        paths = set([
            *self._fileset_design_sources(config), *config.testbench_files,
            *config.simulation_assets, *config.filelists,
        ])
        for relative in config.include_dirs:
            paths.update(self._matching_files([f"{relative.rstrip('/')}/**"]))
        return paths

    def detect_physical_project(self) -> dict[str, Any]:
        config = self.config()
        try:
            generic = self.frozen_generic_physical_contract()
        except WorkbenchConflict:
            generic = None
        commands = {} if generic else dict(self.validation_commands(config))
        detection = PhysicalProjectWizard(self.root).detect(
            configured_top=generic["top_module"] if generic else config.top_module,
            configured_top_parameters=config.top_parameters,
            simulation_command=(
                generic["simulation_command"] if generic
                else _command_from_project_root(
                    commands.get("simulation", config.simulation_command), config.workdir,
                )
            ),
            declared_sources=(
                generic["sources"] if generic
                else self._fileset_design_sources(config)
                if config.validation_mode == "fileset" else None
            ),
            declared_include_dirs=(
                generic["include_dirs"] if generic
                else config.include_dirs if config.validation_mode == "fileset" else None
            ),
            declared_defines=(
                generic["defines"] if generic
                else config.defines if config.validation_mode == "fileset" else None
            ),
            declared_filelists=(
                [] if generic else config.filelists
                if config.validation_mode == "fileset" else None
            ),
        )
        if generic:
            detection["suggested_clock"] = generic["clock_port"]
            detection["suggested_clock_period_ns"] = generic["clock_period_ns"]
            detection["frozen_spec_digest"] = generic["spec_digest"]
            detection["source_authority"] = (
                "frozen generic IP lock" if generic["filelist"] else "frozen generic CSIR"
            )
        return detection

    def _infer_testbench_success_pattern(
        self, testbench_text: str,
    ) -> tuple[str, list[str]]:
        """Infer only PASS markers proven by both tests and project scripts.

        Corpus testbenches are sometimes minified onto one line and their
        wrapper passes an unquoted ``FOO_PASS`` argument.  Treat underscores
        as marker separators and do not rely on line or ``\b`` boundaries.
        If no wrapper names a marker, accept only one unambiguous PASS string
        emitted directly by a SystemVerilog display task.
        """
        token_pattern = re.compile(
            r"(?:^|[^A-Za-z0-9])PASS(?:ED)?(?:$|[^A-Za-z0-9])",
            re.IGNORECASE,
        )

        def usable(value: str) -> bool:
            value = value.strip()
            return bool(
                len(value) >= 8
                and value.casefold() not in {"pass", "passed"}
                and "FAIL" not in value.upper()
                and token_pattern.search(value)
                and value in testbench_text
            )

        script_markers: list[str] = []
        script_paths = sorted(self.root.glob("scripts/**/*.sh"))
        makefile = self.root / "Makefile"
        if makefile.is_file():
            script_paths.append(makefile)
        for script_path in script_paths:
            script_text = script_path.read_text(
                encoding="utf-8", errors="replace"
            )[:2_000_000]
            values = [
                *re.findall(r'''["']([^"'\r\n]*PASS(?:ED)?[^"'\r\n]*)["']''',
                            script_text, re.IGNORECASE),
                *re.findall(r"[A-Za-z0-9_.:-]+", script_text),
            ]
            for value in values:
                value = value.strip()
                if usable(value) and value not in script_markers:
                    script_markers.append(value)
        if script_markers:
            pattern = (
                re.escape(script_markers[0]) if len(script_markers) == 1
                else "(?s)" + "".join(
                    f"(?=.*{re.escape(value)})" for value in script_markers
                )
            )
            return pattern, script_markers

        display_markers: list[str] = []
        for value in re.findall(
            r'''\$(?:display|write|strobe)\s*\(\s*"((?:\\.|[^"\\])*)"''',
            testbench_text, re.IGNORECASE,
        ):
            value = value.strip()
            if "%" in value:
                stable_tokens = [
                    token for token in re.findall(r"[A-Za-z0-9_.:-]+", value)
                    if usable(token)
                ]
                value = max(stable_tokens, key=len) if stable_tokens else ""
            if usable(value) and value not in display_markers:
                display_markers.append(value)
        if len(display_markers) == 1:
            return re.escape(display_markers[0]), display_markers
        return "", []

    def _suggest_simulation_runtime(
        self, testbench_files: list[str], current_workdir: str,
    ) -> tuple[str, list[str], list[dict[str, str]]]:
        """Find literal simulator inputs and a cwd where those names resolve.

        Testbenches frequently load vectors with a bare ``$readmemh`` name or
        open a golden file relative to their own directory.  The files must be
        versioned validation inputs, and generated commands must run from the
        same directory instead of silently assuming the project root.
        """
        literals: list[str] = []
        for relative in testbench_files:
            path = self.root / relative
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8", errors="replace")[:2_000_000]
            values = re.findall(
                r'''\$(?:readmemh|readmemb)\s*\(\s*["']([^"']+)["']''',
                text, re.IGNORECASE,
            )
            for filename, mode in re.findall(
                r'''\$fopen\s*\(\s*["']([^"']+)["'](?:\s*,\s*["']([^"']*)["'])?''',
                text, re.IGNORECASE,
            ):
                # The one-argument Verilog form opens an output descriptor.
                # Only an explicit read mode is a reproducibility input.
                if mode.lower().startswith("r"):
                    values.append(filename)
            for value in values:
                candidate = PurePosixPath(value.replace("\\", "/"))
                if (
                    candidate.is_absolute() or ".." in candidate.parts
                    or candidate.as_posix() in {"", "."}
                ):
                    continue
                if candidate.as_posix() not in literals:
                    literals.append(candidate.as_posix())
        if not literals:
            return current_workdir, [], []

        directories_by_literal: dict[str, set[str]] = {}
        for literal in literals:
            literal_path = PurePosixPath(literal)
            candidates: set[str] = set()
            for match in self.root.rglob(literal_path.name):
                if not match.is_file():
                    continue
                relative = PurePosixPath(match.relative_to(self.root).as_posix())
                if any(part in _SKIP_DIRS for part in relative.parts):
                    continue
                if relative.parts[:2] == ("validation", "work") or (
                    relative.parts and relative.parts[0] == "build"
                ):
                    continue
                if len(relative.parts) < len(literal_path.parts):
                    continue
                if relative.parts[-len(literal_path.parts):] != literal_path.parts:
                    continue
                prefix = relative.parts[:-len(literal_path.parts)]
                candidates.add(PurePosixPath(*prefix).as_posix() if prefix else ".")
            directories_by_literal[literal] = candidates

        missing = [name for name, values in directories_by_literal.items() if not values]
        diagnostics: list[dict[str, str]] = []
        if missing:
            diagnostics.append({
                "severity": "warning",
                "code": "SIMULATION_RUNTIME_INPUT_MISSING",
                "message": (
                    "Testbench 引用了尚未在工程中找到的运行时文件："
                    + "、".join(missing)
                    + "。文件可能由仿真生成；若它们是输入，请先加入工程。"
                ),
            })

        available = [values for values in directories_by_literal.values() if values]
        common = set.intersection(*available) if available else set()
        preferred = [
            current_workdir,
            *[PurePosixPath(path).parent.as_posix() for path in testbench_files],
            ".",
        ]
        workdir = next((item for item in preferred if item in common), "")
        if not workdir and common:
            workdir = sorted(common, key=lambda item: (len(PurePosixPath(item).parts), item))[0]
        if not workdir:
            diagnostics.append({
                "severity": "warning",
                "code": "SIMULATION_WORKDIR_REVIEW_REQUIRED",
                "message": (
                    "Testbench 的运行时输入不能从同一工作目录解析，请保留已有工程命令，"
                    "或人工整理运行时文件。"
                ),
            })
            return current_workdir, [], diagnostics

        assets = [
            PurePosixPath(workdir, literal).as_posix()
            if workdir != "." else literal
            for literal in literals
            if (self.root / workdir / literal).is_file()
        ]
        if assets:
            diagnostics.append({
                "severity": "warning",
                "code": "SIMULATION_RUNTIME_DETECTED",
                "message": (
                    f"已识别 {len(assets)} 个 Testbench 运行时输入并采用工作目录 "
                    f"{workdir}：" + "、".join(assets)
                ),
            })
        return workdir, assets, diagnostics

    def suggest_fileset(self) -> dict[str, Any]:
        """Build a reviewable fileset proposal without executing project code."""
        current = self.config()
        wizard = PhysicalProjectWizard(self.root)
        detection = wizard.detect(
            configured_top=current.top_module,
            simulation_command=current.simulation_command,
            configured_top_parameters=current.top_parameters,
            declared_include_dirs=current.include_dirs,
            declared_defines=current.defines,
        )
        reviewed_include_dirs = {
            *current.include_dirs,
            *detection.get("filelist_include_dirs", []),
            *(str(PurePosixPath(path).parent) for path in detection.get("included_headers", [])),
        }
        suggested_include_dirs = [
            value for value in detection.get("include_dirs", [])
            if value in reviewed_include_dirs
        ]
        design_files = [
            path for path in detection.get("sources", [])
            if Path(path).suffix.lower() in {".v", ".sv"}
        ]
        ordered_design_files = wizard.order_compilation_units(design_files)
        if ordered_design_files != design_files:
            detection["diagnostics"].append({
                "severity": "warning", "code": "SOURCE_ORDER_NORMALIZED",
                "message": (
                    "工程描述中的源码顺序不是依赖顺序；已在建议中将被例化模块放到父模块之前，"
                    "请结合原工程脚本复核。"
                ),
            })
            design_files = ordered_design_files
        testbench_files = self._matching_files([
            "tb/**/*.sv", "tb/**/*.v", "tbench/**/*.sv", "tbench/**/*.v",
            "testbench/**/*.sv", "testbench/**/*.v", "sim/**/*.sv", "sim/**/*.v",
            "tests/**/*.sv", "tests/**/*.v",
        ])
        design_set = set(design_files)
        testbench_files = [
            path for path in testbench_files if path not in design_set
        ]
        tb_modules, tb_instantiated = wizard._scan_modules(testbench_files)
        tb_tops = sorted(set(tb_modules) - tb_instantiated)
        suggested_design_top = current.top_module or detection.get("suggested_top", "")
        if not suggested_design_top:
            physical_candidates = {
                str(item.get("name", ""))
                for item in detection.get("top_candidates", [])
                if isinstance(item, dict) and item.get("name")
            }
            exercised_tops = sorted(physical_candidates & set(tb_instantiated))
            if len(exercised_tops) == 1:
                suggested_design_top = exercised_tops[0]
                detection["diagnostics"] = [
                    item for item in detection.get("diagnostics", [])
                    if item.get("code") != "TOP_REVIEW_REQUIRED"
                ]
                detection["diagnostics"].append({
                    "severity": "warning",
                    "code": "TOP_INFERRED_FROM_TESTBENCH",
                    "message": (
                        "已根据验收 Testbench 的唯一被测实例确定设计顶层："
                        + suggested_design_top
                    ),
                })
        preferred_tb = [
            name for name in tb_tops
            if re.search(r"(?:^|_)(?:tb|testbench)(?:_|$)", name, re.IGNORECASE)
            or name.lower().startswith("tst_bench")
        ]
        simulation_top = current.simulation_top
        if not simulation_top:
            candidates = preferred_tb or tb_tops
            if len(candidates) == 1:
                simulation_top = candidates[0]
            elif testbench_files:
                detection["diagnostics"].append({
                    "severity": "warning", "code": "SIMULATION_TOP_REVIEW_REQUIRED",
                    "message": (
                        "检测到多个或无法确定唯一仿真顶层，请在文件集配置中人工选择："
                        + ("、".join(candidates) if candidates else "未解析到候选模块")
                    ),
                })
        testbench_text = "\n".join(
            (self.root / relative).read_text(
                encoding="utf-8", errors="replace"
            )[:2_000_000]
            for relative in testbench_files
            if (self.root / relative).is_file()
        )
        workdir, detected_assets, runtime_diagnostics = (
            self._suggest_simulation_runtime(testbench_files, current.workdir)
        )
        detection["diagnostics"].extend(runtime_diagnostics)
        simulation_assets = detected_assets or list(current.simulation_assets)
        success_pattern = current.success_pattern
        if success_pattern:
            try:
                pattern_is_produced = bool(re.search(
                    success_pattern, testbench_text, re.MULTILINE,
                ))
            except re.error:
                pattern_is_produced = False
            if not pattern_is_produced:
                detection["diagnostics"].append({
                    "severity": "warning",
                    "code": "SUCCESS_PATTERN_RESET",
                    "message": (
                        "现有成功判据不能由所选 testbench 输出证明；自动文件集不会执行原包装脚本，"
                        "已清除此判据并重新检查 metadata。"
                    ),
                })
                success_pattern = ""
        metadata_path = self.root / "metadata.json"
        metadata_marker_seen = False
        if not success_pattern and metadata_path.is_file():
            try:
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                metadata = {}
            marker = metadata.get("simulation_marker") if isinstance(metadata, dict) else None
            if isinstance(marker, str) and marker.strip():
                metadata_marker_seen = True
                literal = marker.strip()
                if literal in testbench_text:
                    # Corpus metadata normally defines one literal stdout
                    # marker. Escaping preserves that meaning in the regex
                    # based workbench criterion.
                    success_pattern = re.escape(literal)
                else:
                    # A metadata summary may contain a concrete value for a
                    # testbench format conversion, for example ``checks=11``
                    # while the source contains ``checks=%0d``.  In that case
                    # retain a distinctive PASS-bearing identifier that the
                    # selected testbench demonstrably emits.  Never collapse
                    # the criterion to a generic word such as ``pass``.
                    marker_tokens = re.findall(r"[A-Za-z0-9_.:-]+", literal)
                    stable_markers = [
                        value for value in marker_tokens
                        if len(value) >= 8
                        and value.casefold() not in {"pass", "passed"}
                        and re.search(
                            r"(?:^|[_:.-])PASS(?:ED)?(?:$|[_:.-])", value,
                        )
                        and value in testbench_text
                    ]
                    if stable_markers:
                        stable_marker = max(stable_markers, key=len)
                        success_pattern = re.escape(stable_marker)
                        detection["diagnostics"].append({
                            "severity": "warning",
                            "code": "SIMULATION_MARKER_NORMALIZED",
                            "message": (
                                "metadata.json 的仿真摘要含运行时格式化字段；已采用 testbench "
                                f"中可核实的稳定输出标记：{stable_marker}"
                            ),
                        })

                    # Some corpus metadata uses a human summary such as
                    # ``ECB/CBC/CTR TEST PASSED`` while the checked script
                    # requires several independent markers. Read quoted PASS
                    # literals from scripts, retain only strings produced by
                    # the selected testbench, and require all of them in any
                    # order. Project scripts are inspected but never run.
                    if not success_pattern:
                        script_paths = sorted(self.root.glob("scripts/**/*.sh"))
                        makefile = self.root / "Makefile"
                        if makefile.is_file():
                            script_paths.append(makefile)
                        candidates: list[str] = []
                        for script_path in script_paths:
                            script_text = script_path.read_text(
                                encoding="utf-8", errors="replace"
                            )[:2_000_000]
                            for value in re.findall(
                                r'''["']([^"'\r\n]*\b(?:PASSED|PASS)\b[^"'\r\n]*)["']''',
                                script_text,
                            ):
                                value = value.strip()
                                if (
                                    len(value) >= 8
                                    and value.casefold() not in {"pass", "passed"}
                                    and "FAIL" not in value.upper()
                                    and value in testbench_text
                                    and value not in candidates
                                ):
                                    candidates.append(value)
                        if candidates:
                            success_pattern = (
                                "(?s)" + "".join(
                                    f"(?=.*{re.escape(value)})" for value in candidates
                                )
                            )
                            detection["diagnostics"].append({
                                "severity": "warning",
                                "code": "SIMULATION_MARKER_EXPANDED",
                                "message": (
                                    "metadata.json 的仿真摘要不是逐字输出；已根据验收脚本和 testbench "
                                    "展开为必须全部出现的标记：" + "、".join(candidates)
                                ),
                            })
        if not success_pattern:
            inferred_pattern, inferred_markers = (
                self._infer_testbench_success_pattern(testbench_text)
            )
            if inferred_pattern:
                success_pattern = inferred_pattern
                detection["diagnostics"].append({
                    "severity": "warning",
                    "code": "SIMULATION_MARKER_INFERRED",
                    "message": (
                        "已从只读 testbench 与工程验收脚本核实仿真成功标记："
                        + "、".join(inferred_markers)
                    ),
                })
            elif metadata_marker_seen:
                detection["diagnostics"].append({
                    "severity": "warning",
                    "code": "SIMULATION_MARKER_UNVERIFIED",
                    "message": (
                        "metadata.json 的 simulation_marker 未在所选 testbench 中找到，"
                        "为避免伪失败，未自动设置成功判据，请人工确认。"
                    ),
                })
        authority = str(detection.get("source_authority", ""))
        filelists = list(current.filelists)
        if Path(authority).suffix.lower() in {".f", ".flist"}:
            if not filelists:
                filelists = [authority]
            if authority in filelists:
                # The filelist already supplies these compilation units.
                # Repeating them as explicit sources can create duplicate modules.
                design_files = [
                    value for value in current.design_files
                    if value not in detection.get("sources", [])
                ]
        success_evidence = (
            dict(current.success_evidence)
            if current.validation_mode == "fileset" else {}
        )
        if current.validation_mode != "fileset" and current.success_evidence:
            detection["diagnostics"].append({
                "severity": "warning",
                "code": "SUCCESS_EVIDENCE_RESET",
                "message": (
                    "已有工程命令的报告判据不会自动套用到生成的文件集命令；已清除该判据，"
                    "如 testbench 仍会生成同一报告，请在保存前重新配置。"
                ),
            })
        suggestion = {
            "validation_mode": "fileset",
            "top_module": suggested_design_top,
            "top_parameters": (
                dict(current.top_parameters)
                or dict(detection.get("suggested_top_parameters", {}))
            ),
            "design_files": design_files,
            "testbench_files": testbench_files,
            "simulation_assets": simulation_assets,
            "include_dirs": suggested_include_dirs,
            "defines": detection.get("defines", []),
            "filelists": filelists,
            "simulation_top": simulation_top,
            "workdir": workdir,
            "success_pattern": success_pattern,
            "success_evidence": success_evidence,
            "source_authority": authority,
            "diagnostics": detection.get("diagnostics", []),
            "top_candidates": detection.get("top_candidates", []),
            "simulation_candidates": detection.get("simulation_candidates", []),
        }
        candidate_document = asdict(current)
        candidate_document.update({
            key: suggestion[key] for key in (
                "validation_mode", "top_module", "design_files",
                "top_parameters",
                "testbench_files", "simulation_assets", "include_dirs",
                "defines", "filelists", "simulation_top", "workdir",
                "success_pattern", "success_evidence",
            )
        })
        candidate = WorkbenchConfig.from_document(candidate_document)
        issues = self.fileset_issues(candidate)
        issues.extend(item["message"] for item in detection.get("input_issues", []))
        issues = list(dict.fromkeys(issues))
        suggestion["issues"] = issues
        suggestion["effective_validation_commands"] = (
            dict(self.validation_commands(candidate)) if not issues else {}
        )
        return suggestion

    def frozen_soc_specification(self) -> dict[str, Any] | None:
        """Return a valid frozen SoC contract; reject draft or tampered contracts."""
        try:
            state = SpecificationWorkspace(self.root).state()
        except SpecificationError as exc:
            raise WorkbenchError(f"SoC 规格无法读取：{exc}") from exc
        document = state.get("document", {})
        if document.get("design_kind") != "single_clock_soc":
            return None
        if not state.get("configured") or not state.get("frozen") or not state.get("valid"):
            raise WorkbenchConflict("单时钟 SoC 规格尚未有效冻结，不能启动物理实现")
        return document

    def assert_frozen_soc_physical_target(
        self, *, top_module: str, clock_port: str,
        clock_period_ns: float, platform: str, allow_draft: bool = False,
    ) -> None:
        # Permit a valid draft to configure its physical target before freeze.
        # The workbench configuration is captured with each physical run, while
        # checker inputs freeze separately. Execution still requires both.
        if allow_draft:
            try:
                state = SpecificationWorkspace(self.root).state()
            except SpecificationError as exc:
                raise WorkbenchError(f"SoC 规格无法读取：{exc}") from exc
            document = state.get("document", {})
            if document.get("design_kind") != "single_clock_soc":
                return
            if not state.get("configured") or not state.get("valid"):
                raise WorkbenchConflict("单时钟 SoC 草稿存在阻断问题，不能生成物理流程")
        else:
            document = self.frozen_soc_specification()
            if document is None:
                return
        target = document["technical_target"]
        expected_clock = document["clocks"][0]["name"]
        period = float(clock_period_ns)
        if (
            top_module != document["name"]
            or clock_port != expected_clock
            or platform != target["platform"]
            or not math.isfinite(period)
            or abs(period - float(target["clock_period_ns"])) > 1e-9
        ):
            raise WorkbenchConflict(
                "物理顶层、时钟端口、平台或周期与 SoC 技术目标不一致；"
                "请重新生成与冻结规格一致的物理流程"
            )

    def frozen_generic_physical_contract(self) -> dict[str, Any] | None:
        """Bind generic physical setup to a frozen single-clock CSIR and checker."""
        state = SpecificationWorkspace(self.root).state()
        document = state.get("document", {})
        if document.get("design_kind") != "generic_module" or document.get("status") != "frozen":
            return None
        if not state.get("valid") or not state.get("frozen"):
            raise WorkbenchConflict("通用模块冻结规格已失效；请创建并审核新修订")
        target = document.get("technical_target")
        clocks = document.get("clocks", [])
        if (
            not isinstance(target, dict)
            or target.get("platform") != "sky130hd"
            or target.get("pvt") != "tt"
            or type(target.get("clock_period_ns")) not in {int, float}
            or not math.isfinite(float(target["clock_period_ns"]))
            or not 0.01 <= float(target["clock_period_ns"]) <= 1_000_000
            or not isinstance(clocks, list) or len(clocks) != 1
        ):
            raise WorkbenchConflict(
                "通用模块完整物理流程需要冻结的单时钟 Sky130HD TT 目标、周期和端口"
            )
        try:
            contract = checker_contract(state, self.root)
            acceptance = GenericAcceptanceWorkspace(self.root).state(state)
        except (GenericAcceptanceError, GenericRTLContractError) as exc:
            raise WorkbenchConflict(str(exc)) from exc
        if not acceptance.get("valid"):
            raise WorkbenchConflict(
                "通用模块独立 checker 未冻结或已失效；请在 Simulation 阶段重新审核"
            )
        filelist = str(contract.get("filelist", ""))
        filelist_lines = (
            (self.root / filelist).read_text(encoding="utf-8").splitlines()
            if filelist else []
        )
        sources = [line for line in filelist_lines if line and not line.startswith(("+", "-"))]
        if not filelist:
            sources = list(contract.get("sources") or [contract["rtl"]])
        include_dirs = ([line.removeprefix("+incdir+") for line in filelist_lines
                         if line.startswith("+incdir+")] if filelist
                        else list(contract.get("include_dirs", [])))
        defines = ([line.removeprefix("+define+") for line in filelist_lines
                    if line.startswith("+define+")] if filelist
                   else list(contract.get("defines", [])))
        return {
            "spec_digest": state["spec_digest"],
            "top_module": str(document["name"]),
            "clock_port": str(clocks[0]["name"]),
            "clock_period_ns": float(target["clock_period_ns"]),
            "platform": str(target["platform"]),
            "pvt": str(target["pvt"]),
            "rtl": contract["rtl"],
            "filelist": filelist,
            "sources": sources or [contract["rtl"]],
            "include_dirs": include_dirs,
            "defines": defines,
            "source_hashes": dict(contract.get("source_hashes", {})),
            "lock_digest": str(contract.get("lock_digest", "")),
            "assembly_digest": str(contract.get("assembly_digest", "")),
            "testbench": contract["testbench"],
            "acceptance_contract": acceptance["path"],
            "acceptance_contract_digest": acceptance["contract_digest"],
            "simulation_command": validation_command(contract),
        }

    def assert_frozen_generic_physical_target(
        self, *, top_module: str, clock_port: str,
        clock_period_ns: float, platform: str,
    ) -> dict[str, Any] | None:
        contract = self.frozen_generic_physical_contract()
        if contract is None:
            return None
        if (
            top_module != contract["top_module"]
            or clock_port != contract["clock_port"]
            or platform != contract["platform"]
            or not math.isfinite(float(clock_period_ns))
            or abs(float(clock_period_ns) - contract["clock_period_ns"]) > 1e-9
        ):
            raise WorkbenchConflict(
                "物理顶层、时钟端口、平台或周期与冻结通用 CSIR 不一致"
            )
        return contract

    def configure_physical_project(
        self, *, top_module: str, clock_port: str, clock_period_ns: float,
        platform: str, simulation_command: str,
        top_parameters: dict[str, int] | None = None,
    ) -> dict[str, Any]:
        self.assert_frozen_soc_physical_target(
            top_module=top_module.strip(), clock_port=clock_port.strip(),
            clock_period_ns=clock_period_ns, platform=platform.strip(),
            allow_draft=True,
        )
        generic_contract = self.assert_frozen_generic_physical_target(
            top_module=top_module.strip(), clock_port=clock_port.strip(),
            clock_period_ns=clock_period_ns, platform=platform.strip(),
        )
        if generic_contract is not None:
            simulation_command = generic_contract["simulation_command"]
        current = self.config()
        current_commands = (
            {} if generic_contract is not None
            else dict(self.validation_commands(current))
        )
        selected_parameters = normalize_top_parameters(
            top_parameters if top_parameters is not None
            else current.top_parameters
        )
        if (
            top_module.strip() == current.top_module
            and current.top_parameters
            and selected_parameters != current.top_parameters
        ):
            raise WorkbenchError(
                "物理顶层参数必须与已验证的工程配置一致；"
                "请恢复参数 "
                + "、".join(
                    f"{name}={value}"
                    for name, value in current.top_parameters.items()
                )
                + "，或先在验证配置中修改参数并重新运行 RTL 验证"
            )
        environment = PhysicalFlow(
            self.root, current.physical
        ).inspect_environment(current.top_parameters)
        try:
            generated = PhysicalProjectWizard(self.root).configure(
                PhysicalProjectSelection(
                    top_module=top_module.strip(),
                    clock_port=clock_port.strip(),
                    clock_period_ns=float(clock_period_ns),
                    platform=platform.strip(),
                    simulation_command=simulation_command.strip(),
                    top_parameters=selected_parameters,
                ),
                configured_top=current.top_module,
                configured_top_parameters=current.top_parameters,
                current_simulation_command=_command_from_project_root(
                    current_commands.get("simulation", current.simulation_command),
                    current.workdir,
                ),
                declared_sources=(
                    generic_contract["sources"] if generic_contract is not None
                    else self._fileset_design_sources(current)
                    if current.validation_mode == "fileset" else None
                ),
                declared_include_dirs=(
                    generic_contract["include_dirs"] if generic_contract is not None
                    else current.include_dirs if current.validation_mode == "fileset" else None
                ),
                declared_defines=(
                    generic_contract["defines"] if generic_contract is not None
                    else current.defines if current.validation_mode == "fileset" else None
                ),
                declared_filelists=(
                    [] if generic_contract is not None else current.filelists
                    if current.validation_mode == "fileset" else None
                ),
                environment=environment,
            )
        except PhysicalProjectError as exc:
            raise WorkbenchError(str(exc)) from exc
        if generic_contract is not None:
            definition = generated["definition"]
            definition["frozen_spec_digest"] = generic_contract["spec_digest"]
            definition["acceptance_contract_digest"] = generic_contract[
                "acceptance_contract_digest"
            ]
            definition["lock_digest"] = generic_contract["lock_digest"]
            definition["assembly_digest"] = generic_contract["assembly_digest"]
            definition["clock"]["constraint_status"] = "frozen CSIR technical target"
            definition_path = self.root / "physical/chip-nebula/flow-definition.json"
            definition_path.write_text(
                json.dumps(definition, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        document = asdict(current)
        patch = generated["config_patch"]
        for key in (
            "top_module", "top_parameters", "lint_command", "simulation_command",
        ):
            document[key] = patch[key]
        # Keep the exact, reviewed synthesis inputs available to every UI and
        # downstream consumer even when validation continues to use an
        # existing project command instead of generated fileset commands.
        definition = generated["definition"]
        document["design_files"] = definition["compilation_units"]
        document["include_dirs"] = definition["include_dirs"]
        document["defines"] = definition["defines"]
        document["source_globs"] = list(dict.fromkeys([
            *current.source_globs, *patch["source_globs"],
        ]))
        physical = asdict(current.physical)
        physical.update(patch["physical"])
        if generic_contract is not None:
            for key in ("input_globs", "required_inputs"):
                physical[key] = list(dict.fromkeys([
                    *physical[key],
                    generic_contract["testbench"],
                    generic_contract["acceptance_contract"],
                    "spec/design.csir.yaml",
                    *generic_contract["source_hashes"],
                ]))
        document["physical"] = physical
        config = self.save_config(document)
        return {
            **generated,
            "config": asdict(config),
            "environment": PhysicalFlow(
                self.root, config.physical
            ).inspect_environment(config.top_parameters),
        }

    def inspect(self) -> dict[str, Any]:
        config = self.config()
        design_source_files = self.design_source_files(config)
        source_files = sorted(set([
            *self._matching_files(config.source_globs),
            *self._fileset_input_paths(config),
        ]))
        # A cheap UI invalidation hint. Execution still rechecks exact content
        # digests, while this lets an open preview react to same-path RTL edits.
        source_revision = hashlib.sha256()
        for relative in source_files:
            source_revision.update(relative.encode("utf-8") + b"\0")
            try:
                stat = (self.root / relative).stat()
            except OSError:
                source_revision.update(b"missing\0")
            else:
                source_revision.update(
                    f"{stat.st_size}:{stat.st_mtime_ns}:{stat.st_ctime_ns}".encode("ascii")
                    + b"\0"
                )
        fileset_issues = self.fileset_issues(config)
        try:
            effective_commands = dict(self.validation_commands(config))
        except WorkbenchError:
            effective_commands = {}
        git_root = self._git_toplevel()
        project_definition = self.project_definition()
        configuration_file = self.configuration_file_state(project_definition)
        physical_flow = PhysicalFlow(self.root, config.physical)
        validation_tools = physical_flow.validation_tools()
        tools = {
            name: shutil.which(name) or ""
            for name in (
                "git", "verilator", "iverilog", "gtkwave", "make", "yosys",
                "openroad", "klayout", "codex", "opencode", "claude", "qodercli",
            )
        }
        tools.update({
            name: item["path"] for name, item in validation_tools.items()
        })
        return {
            "root": str(self.root),
            "name": (
                str(project_definition.get("name", "")).strip()
                if project_definition else self.root.name
            ) or self.root.name,
            "project_file": project_definition or {},
            "configuration_file": configuration_file,
            "project_issues": (
                [{
                    "code": "PROJECT_CONFIG_MISSING",
                    "severity": "warning",
                    "message": (
                        "工程配置文件不存在；当前显示的是空白默认配置。"
                        "请打开验证配置并保存，以创建版本化配置文件。"
                    ),
                    "path": configuration_file["path"],
                }]
                if project_definition and configuration_file["status"] == "missing"
                else []
            ),
            "git": self.is_git_repository(),
            "git_root": str(git_root) if git_root else "",
            "git_subdirectory": (
                self.root.relative_to(git_root).as_posix()
                if git_root and self.root != git_root else ""
            ),
            "head": self._head(),
            "source_count": len(source_files),
            "source_files": source_files[:200],
            "design_source_files": design_source_files[:200],
            "source_revision": source_revision.hexdigest(),
            "makefiles": [
                str(path.relative_to(self.root))
                for path in sorted(self.root.glob("**/Makefile"))
                if not self._skipped(path)
            ][:50],
            "filelists": self._matching_files(["**/*.f", "**/*.flist"])[:50],
            "tools": tools,
            "validation_tools": validation_tools,
            "config": asdict(config),
            "effective_validation_commands": effective_commands,
            "fileset_issues": fileset_issues,
            "configured": bool(effective_commands) and not fileset_issues,
            "physical_configured": bool(
                config.physical.enabled and config.physical.command
            ),
            "initialization_preview": self.initialization_preview(),
        }

    def initialization_preview(self) -> dict[str, Any]:
        recommended = [
            ".chip_nebula/", "build/", "validation/", "*.vvp", "*.vcd",
            "*.fst", "__pycache__/", "*.py[cod]",
        ]
        excluded: list[str] = []
        for path in self.root.rglob("*"):
            if not path.is_file():
                continue
            relative = path.relative_to(self.root)
            parts = set(relative.parts)
            if (
                ".chip_nebula" not in parts
                and (
                    "build" in parts or "validation" in parts or "__pycache__" in parts
                or path.suffix.lower() in {".vvp", ".vcd", ".fst", ".pyc", ".pyo"}
                )
            ):
                excluded.append(relative.as_posix())
        return {
            "recommended_ignores": recommended,
            "excluded_existing": sorted(excluded)[:200],
            "excluded_count": len(excluded),
        }

    def initialize_git(self) -> dict[str, Any]:
        if self.is_git_repository():
            return self.inspect()
        self.create_project_definition()
        ignore_file = self.root / ".gitignore"
        ignored = ignore_file.read_text(encoding="utf-8") if ignore_file.is_file() else ""
        for entry in self.initialization_preview()["recommended_ignores"]:
            if entry not in ignored.splitlines():
                ignored += ("" if not ignored or ignored.endswith("\n") else "\n") + entry + "\n"
        ignore_file.write_text(ignored, encoding="utf-8")
        self._git("init", "-b", "main")
        self._git("add", ".")
        commit_env = os.environ.copy()
        commit_env.update({
            "GIT_AUTHOR_NAME": "Chip Nebula", "GIT_AUTHOR_EMAIL": "nebula@localhost",
            "GIT_COMMITTER_NAME": "Chip Nebula", "GIT_COMMITTER_EMAIL": "nebula@localhost",
        })
        self._git("commit", "-m", "initial Chip Nebula project baseline", env=commit_env)
        return self.inspect()

    def project_definition(self) -> dict[str, Any] | None:
        manifests = (
            [self.project_file]
            if self.project_file is not None else project_definition_files(self.root)
        )
        if not manifests:
            return None
        if len(manifests) > 1:
            raise WorkbenchError(
                "工程根目录包含多个 .cnprj 文件："
                + "、".join(path.name for path in manifests)
                + "。请明确选择其中一个工程文件，或只保留一个工程入口"
            )
        path = manifests[0]
        if not path.is_file():
            raise WorkbenchError(f"工程文件不存在：{path}")
        if path.is_symlink():
            raise WorkbenchError("工程文件不能是符号链接；请在工程根目录保存真实的 .cnprj 文件")
        try:
            document = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, yaml.YAMLError) as exc:
            raise WorkbenchError(f"工程文件无法读取：{exc}") from exc
        if not isinstance(document, dict):
            raise WorkbenchError("工程文件必须是 YAML 对象")
        if document.get("format") != "chip-nebula-project" or document.get("format_version") != 1:
            raise WorkbenchError("工程文件格式不受支持，需要 chip-nebula-project v1")
        project_id = document.get("project_id")
        if not isinstance(project_id, str) or not re.fullmatch(r"cnprj-[A-Za-z0-9._-]+", project_id):
            raise WorkbenchError("工程文件 project_id 必须是稳定的 cnprj-* 标识")
        if not isinstance(document.get("name"), str) or not document["name"].strip():
            raise WorkbenchError("工程文件 name 不能为空")
        if document.get("root", ".") != ".":
            raise WorkbenchError("工程文件 root 必须为当前目录（.）")
        workbench = document.get("workbench")
        if not isinstance(workbench, dict):
            raise WorkbenchError("工程文件 workbench 必须是对象")
        for field_name in ("config", "template"):
            value = workbench.get(field_name)
            if not isinstance(value, str) or not value.strip():
                raise WorkbenchError(f"工程文件 workbench.{field_name} 不能为空")
            candidate = PurePosixPath(value.replace("\\", "/"))
            if (
                candidate.is_absolute() or ".." in candidate.parts
                or candidate.as_posix() in {"", "."}
            ):
                raise WorkbenchError(
                    f"工程文件 workbench.{field_name} 必须是工程内相对路径"
                )
            candidate_path = (self.root / candidate.as_posix()).resolve()
            if self.root != candidate_path and self.root not in candidate_path.parents:
                raise WorkbenchError(
                    f"工程文件 workbench.{field_name} 不能通过符号链接指向工程外部"
                )
        return {**document, "path": path.name}

    def configuration_file_state(
        self, definition: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Describe which versioned workbench file currently supplies config."""
        definition = definition if definition is not None else self.project_definition()
        target, template = self._config_locations()
        if target.is_file():
            source = target
            status = "saved"
        elif template.is_file():
            source = template
            status = "template"
        else:
            source = None
            status = "missing" if definition else "default"

        def relative(path: Path) -> str:
            try:
                return path.relative_to(self.root).as_posix()
            except ValueError:
                return ""

        return {
            "path": relative(target),
            "template_path": relative(template),
            "source_path": relative(source) if source else "",
            "status": status,
        }

    def create_project_definition(self, name: str = "") -> dict[str, Any]:
        existing = self.project_definition()
        if existing:
            return existing
        try:
            ensure_project_definition(self.root, name)
        except (OSError, ValueError) as exc:
            raise WorkbenchError(f"无法创建工程文件：{exc}") from exc
        return self.project_definition() or {}

    def file_tree(self) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        runtime_assets = set(self.config().simulation_assets)
        for path in sorted(self.root.rglob("*")):
            if len(result) >= 5000 or not path.is_file() or self._skipped(path):
                continue
            relative = path.relative_to(self.root).as_posix()
            if (
                path.suffix.lower() not in _TEXT_SUFFIXES
                and path.name not in {"Makefile"}
                and relative not in runtime_assets
            ):
                continue
            result.append({
                "path": relative,
                "size": path.stat().st_size,
                "source": path.suffix.lower() in _SOURCE_SUFFIXES,
                "runtime_asset": relative in runtime_assets,
            })
        return result

    def source_model(self) -> dict[str, Any]:
        """Return the hierarchy projected from the live project fileset."""
        config = self.config()
        source_files = self.design_source_files(config)
        compilation_units = [
            relative for relative in source_files
            if PurePosixPath(relative).suffix.lower() in {".v", ".sv"}
            and (self.root / relative).is_file()
        ]
        testbench_files = [
            relative for relative in config.testbench_files
            if PurePosixPath(relative).suffix.lower() in {".v", ".sv"}
            and (self.root / relative).is_file()
        ]
        documents = {
            relative: (self.root / relative).read_text(
                encoding="utf-8", errors="replace",
            )
            for relative in dict.fromkeys([*compilation_units, *testbench_files])
        }
        model = self._source_model_from_documents(
            documents,
            design_files=compilation_units,
            testbench_files=testbench_files,
            top_module=config.top_module,
            simulation_top=config.simulation_top,
            source={"kind": "live_project"},
        )
        try:
            compile_order = PhysicalProjectWizard(self.root).order_compilation_units(
                compilation_units,
            )
        except (OSError, UnicodeError):
            compile_order = compilation_units
        if config.design_files:
            compile_order = [
                item for item in config.design_files
                if PurePosixPath(item).suffix.lower() in {".v", ".sv"}
            ]
        return model | {
            "compile_order": compile_order,
            "constraint_files": [
                item["path"] for item in self.file_tree()
                if PurePosixPath(item["path"]).suffix.lower() == ".sdc"
            ],
            "note": "层次来自当前工程源码结构；正式编译与工具展开结果是最终依据。",
        }

    def source_model_from_git_snapshot(
        self, *, commit: str, paths: list[str] | tuple[str, ...], artifact_id: str,
    ) -> dict[str, Any]:
        """Project hierarchy from an immutable Task Graph RTL Artifact."""
        return self.source_model_from_git_snapshots(
            design_snapshots=[{
                "artifact_id": artifact_id, "commit": commit,
                "paths": list(paths),
            }],
            testbench_snapshots=[],
        )

    def source_model_from_git_snapshots(
        self, *, design_snapshots: list[dict[str, Any]],
        testbench_snapshots: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Assemble hierarchy from immutable design and verification inputs."""
        from chip_nebula.taskgraph.hierarchy_dependencies import (
            HierarchyDependencyError, locked_rtl_sources, read_locked_rtl,
        )

        def is_testbench(path: str) -> bool:
            pure = PurePosixPath(path)
            stem = pure.stem.lower()
            return "tb" in pure.parts or stem.endswith("_tb") or stem.endswith("testbench")

        design_files: list[str] = []
        testbench_files: list[str] = []
        documents: dict[str, str] = {}
        document_sources: dict[str, dict[str, str]] = {}
        dependency_warnings: list[str] = []
        selected_top = ""

        def read_snapshot(snapshot: dict[str, Any], selected: list[str]) -> None:
            commit = str(snapshot.get("commit") or "")
            artifact_id = str(snapshot.get("artifact_id") or "")
            if not commit:
                return
            for relative in selected:
                if relative in documents:
                    continue
                result = subprocess.run(
                    ["git", "show", f"{commit}:{relative}"],
                    cwd=self.root, capture_output=True, text=True,
                )
                if result.returncode == 0:
                    documents[relative] = result.stdout
                    document_sources[relative] = {
                        "artifact_id": artifact_id, "commit": commit,
                    }

        fallback_testbenches: list[tuple[dict[str, Any], list[str]]] = []
        for snapshot in design_snapshots:
            rtl_paths = [
                str(path) for path in snapshot.get("paths", [])
                if PurePosixPath(str(path)).suffix.lower() in {".v", ".sv"}
            ]
            snapshot_testbenches = [path for path in rtl_paths if is_testbench(path)]
            snapshot_design = [
                path for path in rtl_paths
                if path not in snapshot_testbenches
                and not path.startswith("build/")
                and ".nebula_inputs" not in PurePosixPath(path).parts
            ]
            if not snapshot_design:
                snapshot_design = [
                    path for path in rtl_paths if path not in snapshot_testbenches
                ]
            design_files.extend(snapshot_design)
            read_snapshot(snapshot, snapshot_design)
            fallback_testbenches.append((snapshot, [
                path for path in snapshot_testbenches
                if "vendor" not in PurePosixPath(path).parts
                and ".nebula_inputs" not in PurePosixPath(path).parts
                and not path.startswith("build/rtl/")
            ]))

        # Project snapshots take precedence over external dependency definitions.
        # Only the archived lock authorizes local IP/macro reads, never a directory scan.
        for snapshot in design_snapshots:
            try:
                records, locked_top = locked_rtl_sources(self.root, snapshot)
            except HierarchyDependencyError as exc:
                dependency_warnings.append(str(exc))
                continue
            selected_top = selected_top or locked_top
            for record in records:
                relative = record["path"]
                if relative in documents:
                    continue
                try:
                    dependency = read_locked_rtl(self.root, record)
                except HierarchyDependencyError as exc:
                    dependency_warnings.append(str(exc))
                    continue
                documents[relative] = dependency["content"]
                design_files.append(relative)
                document_sources[relative] = {
                    "artifact_id": str(snapshot.get("artifact_id") or ""),
                    "commit": str(snapshot.get("commit") or ""),
                    "dependency_source": True,
                    "dependency_sha256": dependency["version"],
                    "package": record.get("package", ""),
                    "package_version": record.get("package_version", ""),
                }

        if testbench_snapshots:
            for snapshot in testbench_snapshots:
                selected = [
                    str(path) for path in snapshot.get("paths", [])
                    if PurePosixPath(str(path)).suffix.lower() in {".v", ".sv"}
                    and is_testbench(str(path))
                ]
                testbench_files.extend(selected)
                read_snapshot(snapshot, selected)
        else:
            for snapshot, selected in fallback_testbenches:
                testbench_files.extend(selected)
                read_snapshot(snapshot, selected)

        design_files = list(dict.fromkeys(design_files))
        testbench_files = list(dict.fromkeys(testbench_files))
        primary = design_snapshots[0] if design_snapshots else {}
        model = self._source_model_from_documents(
            documents,
            design_files=[path for path in design_files if path in documents],
            testbench_files=[path for path in testbench_files if path in documents],
            top_module=selected_top,
            source={
                "kind": "taskgraph_artifact",
                "artifact_id": str(primary.get("artifact_id") or ""),
                "commit": str(primary.get("commit") or ""),
                "artifacts": [
                    {
                        "artifact_id": str(snapshot.get("artifact_id") or ""),
                        "commit": str(snapshot.get("commit") or ""),
                    }
                    for snapshot in [*design_snapshots, *testbench_snapshots]
                    if snapshot.get("artifact_id") and snapshot.get("commit")
                ],
            },
            document_sources=document_sources,
        )
        return model | {
            "compile_order": [path for path in design_files if path in documents],
            "constraint_files": [],
            "dependency_warnings": list(dict.fromkeys(dependency_warnings)),
            "note": (
                "层次来自不可变 RTL/集成 Artifact、摘要校验后的外部依赖与其验证环境；仅把实例化设计顶层的验证模块"
                "作为主 Testbench。若 Artifact 提供工具 elaboration 报告，应以工具结果为最终依据。"
            ),
        }

    @staticmethod
    def _source_model_from_documents(
        documents: dict[str, str], *, design_files: list[str],
        testbench_files: list[str], top_module: str = "",
        simulation_top: str = "", source: dict[str, Any] | None = None,
        document_sources: dict[str, dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        """Build separate design and simulation instance trees."""
        module_pattern = re.compile(
            r"\bmodule\s+([A-Za-z_][A-Za-z0-9_$]*)\b(.*?)\bendmodule\b",
            re.DOTALL,
        )
        instance_pattern = re.compile(
            r"(?:^|[;])\s*([A-Za-z_][A-Za-z0-9_$]*)\b"
            r"(?:\s*#\s*\([^;]*?\)\s*|\s+)"
            r"([A-Za-z_][A-Za-z0-9_$]*)\s*\(",
            re.MULTILINE | re.DOTALL,
        )
        modules: dict[str, dict[str, Any]] = {}
        bodies: dict[str, str] = {}
        origins: dict[str, str] = {}
        design_set = set(design_files)
        testbench_set = set(testbench_files)
        for relative, raw_text in documents.items():
            text = raw_text
            # Comments can contain examples which look like declarations.
            text = re.sub(r"/\*.*?\*/", " ", text, flags=re.DOTALL)
            text = re.sub(r"//[^\n]*", " ", text)
            for match in module_pattern.finditer(text):
                name = match.group(1)
                origin = "testbench" if relative in testbench_set else "design"
                modules[name] = {
                    "name": name, "file": relative, "origin": origin,
                    "instances": [],
                }
                if document_sources and relative in document_sources:
                    modules[name].update(document_sources[relative])
                bodies[name] = match.group(2)
                origins[name] = origin

        instantiated: set[str] = set()
        design_instantiated: set[str] = set()
        non_instance_keywords = {
            "module", "function", "task", "if", "else", "for", "foreach", "while",
            "case", "casex", "casez", "always", "always_comb", "always_ff",
            "always_latch", "initial", "assign", "assert", "assume", "cover",
            "logic", "wire", "reg", "bit", "int", "integer", "return",
            "input", "output", "inout", "parameter", "localparam", "typedef",
            "begin", "end", "endcase", "endfunction", "endtask", "generate",
            "endgenerate", "unique", "unique0", "priority", "repeat", "wait",
        }
        for name, item in list(modules.items()):
            children = []
            for match in instance_pattern.finditer(bodies.get(name, "")):
                module_name, instance_name = match.group(1), match.group(2)
                if module_name in non_instance_keywords:
                    continue
                if module_name not in modules:
                    modules[module_name] = {
                        "name": module_name, "file": "", "origin": "design",
                        "instances": [], "unresolved": True,
                    }
                children.append({
                    "name": instance_name,
                    "module": module_name,
                    "file": modules[module_name]["file"],
                })
                instantiated.add(module_name)
                if origins.get(name) == "design" and origins.get(module_name) == "design":
                    design_instantiated.add(module_name)
            item["instances"] = children

        design_modules = {name for name, origin in origins.items() if origin == "design"}
        testbench_modules = {name for name, origin in origins.items() if origin == "testbench"}
        design_roots: list[str] = []
        if top_module in design_modules:
            design_roots.append(top_module)
        design_roots.extend(
            name for name in sorted(design_modules - design_instantiated)
            if name not in design_roots
        )
        if not design_roots:
            design_roots = sorted(design_modules)
        simulation_roots: list[str] = []
        if simulation_top in testbench_modules:
            simulation_roots.append(simulation_top)
        else:
            simulation_roots.extend(sorted(testbench_modules - instantiated))
            selected_design_top = (
                top_module if top_module in design_modules
                else design_roots[0] if len(design_roots) == 1 else ""
            )

            def reaches(module_name: str, target: str, seen: set[str]) -> bool:
                if module_name == target:
                    return True
                if module_name in seen:
                    return False
                return any(
                    reaches(child["module"], target, {*seen, module_name})
                    for child in modules[module_name]["instances"]
                )

            matching_roots = [
                name for name in simulation_roots
                if selected_design_top and reaches(name, selected_design_top, set())
            ]
            if matching_roots:
                simulation_roots = matching_roots
        if not simulation_roots:
            simulation_roots = sorted(testbench_modules)

        def node(
            module_name: str, instance_name: str, stack: tuple[str, ...],
            parent_path: str = "",
        ) -> dict[str, Any]:
            cycle = module_name in stack
            entry = modules[module_name]
            instance_path = f"{parent_path}.{instance_name}" if parent_path else instance_name
            result = {
                "name": instance_name,
                "module": module_name,
                "file": entry["file"],
                "origin": entry["origin"],
                "path": instance_path,
                "cycle": cycle,
                "children": [] if cycle else [
                    node(
                        child["module"], child["name"], (*stack, module_name),
                        instance_path,
                    )
                    for child in entry["instances"]
                ],
            }
            if entry.get("artifact_id"):
                result["artifact_id"] = entry["artifact_id"]
            if entry.get("commit"):
                result["commit"] = entry["commit"]
            for field in ("dependency_source", "dependency_sha256", "package", "package_version", "unresolved"):
                if entry.get(field):
                    result[field] = entry[field]
            return result
        return {
            "top_module": top_module or (design_roots[0] if len(design_roots) == 1 else ""),
            "simulation_top": simulation_top or (
                simulation_roots[0] if len(simulation_roots) == 1 else ""
            ),
            "roots": [node(name, name, ()) for name in design_roots],
            "simulation_roots": [node(name, name, ()) for name in simulation_roots],
            "modules": [modules[name] for name in sorted(modules)],
            "design_files": list(design_files),
            "testbench_files": list(testbench_files),
            "source": source or {"kind": "unknown"},
        }

    def read_file(self, relative: str) -> dict[str, Any]:
        path = self._safe_file(relative)
        data = path.read_bytes()
        if len(data) > 2_000_000:
            raise WorkbenchError("file is larger than 2 MB")
        return {
            "path": relative,
            "content": data.decode("utf-8", errors="replace"),
            "version": hashlib.sha256(data).hexdigest(),
            "read_only": path.suffix.lower() == ".cnprj",
        }

    def save_file(self, relative: str, content: str, version: str) -> dict[str, Any]:
        path = self._safe_path(relative)
        if path.suffix.lower() == ".cnprj":
            raise WorkbenchError(
                "工程入口文件由 Chip Nebula 管理；请通过工程设置修改配置"
            )
        current = path.read_bytes() if path.is_file() else b""
        digest = hashlib.sha256(current).hexdigest()
        if version != digest:
            raise WorkbenchConflict("文件已在磁盘上变化，请重新载入后再保存", [relative])
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix.lower() in _SOURCE_SUFFIXES and content and not content.endswith("\n"):
            content += "\n"
        path.write_text(content, encoding="utf-8")
        self._mark_validation_stale()
        return self.read_file(relative)

    def create_file(self, relative: str, content: str = "") -> dict[str, Any]:
        normalized = PurePosixPath(str(relative).replace("\\", "/")).as_posix()
        if PurePosixPath(normalized).suffix.lower() not in _SOURCE_SUFFIXES:
            raise WorkbenchError("新建源码文件必须使用 .v、.sv、.vh 或 .svh 扩展名")
        path = self._safe_path(normalized)
        if path.exists():
            raise WorkbenchConflict("文件已经存在", [normalized])
        path.parent.mkdir(parents=True, exist_ok=True)
        if content and not content.endswith("\n"):
            content += "\n"
        path.write_text(content, encoding="utf-8")
        self._mark_validation_stale()
        return self.read_file(normalized)

    def import_files(self, files: list[dict[str, str]]) -> dict[str, Any]:
        """Atomically import selected RTL and text validation inputs."""
        if not files:
            raise WorkbenchError("没有选择可导入的工程文件")
        if len(files) > 500:
            raise WorkbenchError("一次最多导入 500 个工程文件")
        prepared: list[tuple[str, Path, str]] = []
        seen: set[str] = set()
        total_size = 0
        conflicts: list[str] = []
        for item in files:
            if not isinstance(item, dict):
                raise WorkbenchError("导入文件格式无效")
            raw_path = str(item.get("path", "")).strip().replace("\\", "/")
            relative = PurePosixPath(raw_path)
            normalized = relative.as_posix()
            if (
                relative.is_absolute() or ".." in relative.parts
                or normalized in {"", "."}
                or any(character in raw_path for character in "*?[\x00\n\r")
                or relative.suffix.lower() not in _IMPORT_TEXT_SUFFIXES
            ):
                raise WorkbenchError(f"无效的工程文件导入路径：{raw_path}")
            if normalized in seen:
                conflicts.append(normalized)
                continue
            content = item.get("content", "")
            if (
                not isinstance(content, str)
                or "\x00" in content or "\ufffd" in content
            ):
                raise WorkbenchError(f"导入文件必须是 UTF-8 文本：{normalized}")
            size = len(content.encode("utf-8"))
            if size > 2_000_000:
                raise WorkbenchError(f"导入文件超过 2 MB：{normalized}")
            total_size += size
            if total_size > 50_000_000:
                raise WorkbenchError("一次导入的文本总量不能超过 50 MB")
            target = self._safe_path(normalized)
            if target.exists():
                conflicts.append(normalized)
            seen.add(normalized)
            prepared.append((normalized, target, content))
        if conflicts:
            raise WorkbenchConflict(
                "导入目标已经存在或重复；未写入任何文件",
                sorted(set(conflicts)),
            )
        for normalized, target, content in prepared:
            target.parent.mkdir(parents=True, exist_ok=True)
            if (
                PurePosixPath(normalized).suffix.lower() in _SOURCE_SUFFIXES
                and content and not content.endswith("\n")
            ):
                content += "\n"
            target.write_text(content, encoding="utf-8")
        self._mark_validation_stale()
        return {
            "imported": [normalized for normalized, _, _ in prepared],
            "count": len(prepared),
        }

    def capture_snapshot(
        self, label: str, *, include_tool_outputs: bool = False,
    ) -> dict[str, str]:
        if not self.is_git_repository():
            raise WorkbenchError("project must be a Git repository before creating snapshots")
        snapshot_id = f"snap-{dt.datetime.now().strftime('%Y%m%dT%H%M%S')}-{uuid.uuid4().hex[:8]}"
        head = self._head()
        descriptor, index_name = tempfile.mkstemp(prefix="chip-nebula-index-")
        os.close(descriptor)
        Path(index_name).unlink()
        try:
            env = os.environ.copy()
            env["GIT_INDEX_FILE"] = index_name
            # Build a project-rooted tree from the live filesystem.  A project
            # may be a nested directory of a larger Git worktree, including a
            # deliberately ignored corpus checkout.  Reading HEAD would make
            # snapshot paths relative to that outer repository and validation
            # would subsequently run from the wrong directory.
            self._git("read-tree", "--empty", env=env)
            exclusions = [
                f":(exclude){directory}/**" for directory in sorted(_SKIP_DIRS)
            ]
            if not include_tool_outputs:
                config = self.config()
                output_roots = {
                    root.as_posix()
                    for pattern in [*config.report_globs, *config.waveform_globs]
                    if (root := _literal_glob_root(pattern)) is not None
                }
                if config.physical.output_root not in {"", "."}:
                    output_roots.add(config.physical.output_root)
                if config.validation_mode == "fileset":
                    output_roots.add("build/chip-nebula-validation")
                exclusions.extend(
                    f":(exclude){root.rstrip('/')}/**" for root in sorted(output_roots)
                )
            self._git(
                "add", "-f", "-A", "--", ".", *exclusions,
                env=env,
            )
            repository_tree = self._git("write-tree", env=env).stdout.strip()
            prefix = self._git("rev-parse", "--show-prefix").stdout.strip()
            tree = (
                self._git("rev-parse", f"{repository_tree}:./").stdout.strip()
                if prefix else repository_tree
            )
        finally:
            Path(index_name).unlink(missing_ok=True)
        commit_args = ["commit-tree", tree, "-m", f"Chip Nebula snapshot: {label}"]
        commit_env = os.environ.copy()
        commit_env.update({
            "GIT_AUTHOR_NAME": "Chip Nebula", "GIT_AUTHOR_EMAIL": "nebula@localhost",
            "GIT_COMMITTER_NAME": "Chip Nebula", "GIT_COMMITTER_EMAIL": "nebula@localhost",
        })
        commit = self._git(*commit_args, env=commit_env).stdout.strip()
        self._git("update-ref", f"refs/chip-nebula/workbench/snapshots/{snapshot_id}", commit)
        return {
            "id": snapshot_id, "commit": commit, "tree": tree, "label": label,
            "source_head": head,
        }

    def create_operation(
        self, instruction: str, write_paths: list[str], *, stage: str = "rtl",
    ) -> dict[str, Any]:
        before = self.capture_snapshot(
            "before AI operation", include_tool_outputs=True,
        )
        operation = {
            "id": f"op-{uuid.uuid4().hex[:10]}",
            "instruction": instruction,
            "stage": stage,
            "write_paths": write_paths,
            "before": before,
            "after": None,
            "status": "running",
            "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        }
        self._write_operation(operation)
        return operation

    def finish_operation(self, operation_id: str, *, status: str, summary: str = "") -> dict[str, Any]:
        operation = self.operation(operation_id)
        candidate = self.capture_snapshot(
            "raw AI operation result", include_tool_outputs=True,
        )
        before_commit = operation["before"]["commit"]
        candidate_changed = self.changed_files(before_commit, candidate["commit"])
        current_generated = [
            path for path in candidate_changed if self._is_tool_output(path)
        ]
        source_changes = [
            path for path in candidate_changed if path not in current_generated
        ]
        bad = violations(source_changes, operation.get("write_paths", []))
        after = candidate
        cleanup = list(dict.fromkeys([*bad, *current_generated]))
        if cleanup:
            # Live checkout rollback must be relative to our operation snapshot.
            # Using git checkout here would erase user edits that existed before
            # the Agent started and would also rewrite index semantics.
            self._restore_paths(before_commit, cleanup)
            after = self.capture_snapshot(
                "after output cleanup", include_tool_outputs=True,
            )
        generated = list(dict.fromkeys([
            *operation.get("discarded_tool_outputs", []), *current_generated,
        ]))
        if generated:
            note = "已清理 Agent 自检产生的临时工具输出：" + ", ".join(generated)
            summary = f"{summary}\n\n{note}".strip()
        if bad:
            status = "failed"
            summary = (
                f"AI 修改了授权范围之外的文件：{', '.join(bad)}。"
                "这些文件已从操作前快照恢复，原始结果仍保留在内部记录中。"
            )
        changed = self.changed_files(before_commit, after["commit"])
        operation.update({
            "after": after, "status": status, "summary": summary,
            "changed_files": changed, "scope_violations": bad,
            "discarded_tool_outputs": generated,
        })
        if cleanup:
            operation["raw_after"] = candidate
        self._write_operation(operation)
        self._mark_validation_stale()
        return operation

    def recover_declared_tool_output_scope_failure(
        self, operation_id: str, error: str | None,
    ) -> list[str]:
        """Clean declared self-check outputs after an adapter scope failure.

        Adapters correctly treat every write outside the Task's RTL scope as a
        failure. In live-workspace mode, however, lint and simulation may write
        reports, waveforms, and binaries under a configured output directory.
        The desktop runtime removes those files relative to its private before
        snapshot. It may continue only when no other out-of-scope source change
        exists; the Task's source write grant itself is never widened.
        """
        if not error or not error.startswith("Scope violation:"):
            return []
        operation = self.operation(operation_id)
        candidate = self.capture_snapshot(
            "raw Agent self-check result", include_tool_outputs=True,
        )
        before_commit = operation["before"]["commit"]
        changed = self.changed_files(before_commit, candidate["commit"])
        generated = [path for path in changed if self._is_tool_output(path)]
        source_changes = [path for path in changed if path not in generated]
        bad = violations(source_changes, operation.get("write_paths", []))
        if not generated or bad:
            return []
        self._restore_paths(before_commit, generated)
        operation["raw_after"] = candidate
        operation["discarded_tool_outputs"] = list(dict.fromkeys([
            *operation.get("discarded_tool_outputs", []), *generated,
        ]))
        self._write_operation(operation)
        return generated

    def _is_tool_output(self, relative: str) -> bool:
        """Return whether a changed path is inside a declared output tree.

        A broad pattern such as ``**/*.vcd`` has no literal root and grants
        nothing; ``build/*.log`` grants only the ``build/`` tree. These files
        are restored before formal snapshot validation and never widen Agent
        source permissions.
        """
        path = PurePosixPath(relative)
        config = self.config()
        if (
            config.validation_mode == "fileset"
            and (
                path == PurePosixPath("build/chip-nebula-validation")
                or PurePosixPath("build/chip-nebula-validation") in path.parents
            )
        ):
            return True
        for pattern in [*config.report_globs, *config.waveform_globs]:
            root = _literal_glob_root(pattern)
            if root and (path == root or root in path.parents):
                return True
        return False

    def operation(self, operation_id: str) -> dict[str, Any]:
        if not re.fullmatch(r"op-[a-f0-9]+", operation_id):
            raise WorkbenchError("invalid operation id")
        path = self.operations_dir / f"{operation_id}.json"
        if not path.is_file():
            raise WorkbenchError("operation not found")
        return json.loads(path.read_text(encoding="utf-8"))

    def list_operations(self) -> list[dict[str, Any]]:
        result = []
        for path in self.operations_dir.glob("op-*.json"):
            try:
                result.append(json.loads(path.read_text(encoding="utf-8")))
            except (OSError, json.JSONDecodeError):
                continue
        result.sort(
            key=lambda item: (str(item.get("created_at", "")), str(item.get("id", ""))),
            reverse=True,
        )
        return result

    def operation_diff(self, operation_id: str) -> dict[str, Any]:
        operation = self.operation(operation_id)
        if not operation.get("after"):
            return {"operation": operation, "files": [], "diff": ""}
        before = operation["before"]["commit"]
        after = operation["after"]["commit"]
        file_diffs = []
        for path in self.changed_files(before, after):
            old = self._commit_bytes(before, path)
            new = self._commit_bytes(after, path)
            if max(len(old or b""), len(new or b"")) > 2_000_000:
                continue
            file_diffs.append({
                "path": path,
                "before": (old or b"").decode("utf-8", errors="replace"),
                "after": (new or b"").decode("utf-8", errors="replace"),
            })
        return {
            "operation": operation,
            "files": self.changed_files(before, after),
            "diff": self._git("diff", "--no-ext-diff", "--unified=3", before, after).stdout,
            "file_diffs": file_diffs,
        }

    def undo_operation(self, operation_id: str) -> dict[str, Any]:
        operation = self.operation(operation_id)
        if not operation.get("after"):
            raise WorkbenchError("operation has no completed snapshot")
        before = operation["before"]["commit"]
        after = operation["after"]["commit"]
        changed = self.changed_files(before, after)
        conflicts = [path for path in changed if self._working_bytes(path) != self._commit_bytes(after, path)]
        if conflicts:
            raise WorkbenchConflict(
                "检测到操作完成后的编辑，为避免覆盖，未执行撤销", conflicts,
            )
        self._restore_paths(before, changed)
        operation["status"] = "undone"
        operation["undone_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
        self._write_operation(operation)
        self._mark_validation_stale()
        return operation

    def changed_files(self, older: str, newer: str) -> list[str]:
        result = self._git("diff", "--name-only", "-z", older, newer).stdout
        return [item for item in result.split("\0") if item]

    def fingerprint(self) -> str:
        """Legacy aggregate fingerprint retained for reading older run records."""
        digest = hashlib.sha256()
        config = self.config()
        tracked = set(self._matching_files(config.source_globs))
        tracked.update(self._fileset_input_paths(config))
        if config.physical.enabled:
            tracked.update(self._matching_files(config.physical.input_globs))
        tracked.update(
            relative for relative in (
                "spec/design.csir.yaml", "ip/nebula.lock.json",
                "integration/nebula-assembly.json", "workbench.yaml",
            )
            if (self.root / relative).is_file()
        )
        config_path, _template = self._config_locations()
        if config_path.is_file():
            data = config_path.read_bytes()
            relative = config_path.relative_to(self.root).as_posix()
            digest.update(relative.encode("utf-8") + b"\0" + hashlib.sha256(data).digest())
        for relative in sorted(tracked):
            data = (self.root / relative).read_bytes()
            digest.update(relative.encode("utf-8") + b"\0" + hashlib.sha256(data).digest())
        return digest.hexdigest()

    def validation_fingerprint(self, config: WorkbenchConfig | None = None) -> str:
        config = config or self.config()
        paths = self.validation_input_paths(config)
        if config.validation_mode == "fileset":
            # In fileset mode these inputs generate the effective commands.
            # Compatibility command fields and broad source globs may be
            # updated by the physical wizard, but are not executed by RTL
            # validation and therefore must not invalidate its evidence.
            document = {
                "top_module": config.top_module,
                "top_parameters": config.top_parameters,
                "validation_mode": config.validation_mode,
                "design_files": config.design_files,
                "testbench_files": config.testbench_files,
                "simulation_assets": config.simulation_assets,
                "include_dirs": config.include_dirs,
                "defines": config.defines,
                "filelists": config.filelists,
                "simulation_top": config.simulation_top,
            }
        else:
            document = {
                "top_module": config.top_module,
                "top_parameters": config.top_parameters,
                "source_globs": config.source_globs,
                "validation_mode": config.validation_mode,
                "lint_command": config.lint_command,
                "simulation_command": config.simulation_command,
            }
        document.update({
            "workdir": config.workdir,
            "timeout": config.timeout,
            "success_pattern": config.success_pattern,
            "success_evidence": config.success_evidence,
            "report_globs": config.report_globs,
            "waveform_globs": config.waveform_globs,
        })
        return self._input_fingerprint(paths, document)

    def generic_acceptance_fingerprint(
        self, config: WorkbenchConfig | None = None,
    ) -> str:
        """Bind generic verification to its real inputs, not physical-wizard fields."""
        config = config or self.config()
        try:
            spec = SpecificationWorkspace(self.root).state()
            acceptance = GenericAcceptanceWorkspace(self.root).state(spec)
            contract = checker_contract(spec, self.root)
            headers = generation_include_files(self.root, spec) if contract.get("include_dirs") else []
        except (SpecificationError, GenericAcceptanceError, GenericRTLContractError):
            return "invalid-generic-acceptance"
        if not (spec.get("frozen") and spec.get("valid") and acceptance.get("valid")):
            return "invalid-generic-acceptance"
        paths = {
            "spec/design.csir.yaml", contract["rtl"], contract["testbench"],
            acceptance["path"], *contract.get("sources", []), *headers,
            *contract.get("source_hashes", {}),
        }
        document = {
            "fingerprint_kind": "generic_acceptance_v1",
            "spec_digest": spec["spec_digest"],
            "acceptance_contract_digest": acceptance["contract_digest"],
            "runner": acceptance["runner"],
            "top_parameters": config.top_parameters,
            "workdir": config.workdir,
            "timeout": config.timeout,
            "success_pattern": config.success_pattern,
            "success_evidence": config.success_evidence,
        }
        return self._input_fingerprint(paths, document)

    def physical_fingerprint(self, *, legacy_empty_required_inputs: bool = False) -> str:
        config = self.config()
        paths = self.physical_input_paths(config)
        physical = asdict(config.physical)
        # Older run records predate required_inputs. An empty new default must
        # not make unchanged historical design inputs appear stale.
        if legacy_empty_required_inputs and not config.physical.required_inputs:
            physical.pop("required_inputs", None)
        document = {
            "top_module": config.top_module,
            "top_parameters": config.top_parameters,
            "validation_mode": config.validation_mode,
            "design_files": config.design_files,
            "simulation_assets": config.simulation_assets,
            "include_dirs": config.include_dirs,
            "defines": config.defines,
            "filelists": config.filelists,
            "simulation_command": config.simulation_command,
            "physical": physical,
        }
        return self._input_fingerprint(paths, document)

    def validation_input_paths(
        self, config: WorkbenchConfig | None = None, *,
        include_project_metadata: bool = False,
    ) -> set[str]:
        config = config or self.config()
        if config.validation_mode == "fileset":
            paths = self._fileset_input_paths(config)
        else:
            paths = set(self._matching_files(config.source_globs))
            paths.update(self._matching_files([
                "tb/**", "tbench/**", "scripts/**", "Makefile", "**/*.f",
                "**/*.flist", "**/*.svh", "**/*.vh",
            ]))
        paths.update(self._design_contract_paths())
        spec_path = self.root / "spec/design.csir.yaml"
        if spec_path.is_file():
            try:
                spec = SpecificationWorkspace(self.root).state()
                if (
                    spec.get("frozen") and spec.get("valid")
                    and spec.get("document", {}).get("design_kind") == "generic_module"
                ):
                    contract = checker_contract(spec, self.root)
                    # A checker candidate also runs in a fixed snapshot, before
                    # its acceptance contract has been approved and frozen.
                    paths.update({contract["rtl"], *contract.get("sources", [])})
                    if contract.get("include_dirs"):
                        paths.update(generation_include_files(self.root, spec))
                    if GenericAcceptanceWorkspace(self.root).state(spec).get("valid"):
                        paths.update({
                            contract["testbench"],
                            f"tb/{contract['top_module']}.acceptance.json",
                            *contract.get("source_hashes", {}),
                        })
            except (SpecificationError, GenericAcceptanceError, GenericRTLContractError):
                pass
        if include_project_metadata:
            paths.update(self._versioned_project_paths())
        return paths

    def physical_input_paths(
        self, config: WorkbenchConfig | None = None, *,
        include_project_metadata: bool = False,
    ) -> set[str]:
        config = config or self.config()
        paths = set(self._matching_files(config.source_globs))
        paths.update(self._fileset_input_paths(config))
        paths.update(self._matching_files(config.physical.input_globs))
        paths.update(self._matching_files(config.physical.required_inputs))
        paths.update(self._design_contract_paths())
        spec_path = self.root / "spec/design.csir.yaml"
        if spec_path.is_file():
            try:
                spec = SpecificationWorkspace(self.root).state()
                if (
                    spec.get("frozen") and spec.get("valid")
                    and spec.get("document", {}).get("design_kind") == "generic_module"
                ):
                    contract = checker_contract(spec, self.root)
                    paths.update({contract["rtl"], *contract.get("sources", [])})
                    if contract.get("include_dirs"):
                        paths.update(generation_include_files(self.root, spec))
            except (SpecificationError, GenericAcceptanceError, GenericRTLContractError):
                pass
        if include_project_metadata:
            paths.update(self._versioned_project_paths())
            # The physical "all" command runs the project's independent
            # acceptance script before synthesis. Its firmware and checker
            # inputs are frozen in CSIR, even when they do not match a source
            # or physical input glob.
            spec_path = self.root / "spec/design.csir.yaml"
            if spec_path.is_file():
                spec = SpecificationWorkspace(self.root).read()
                if spec.get("status") == "frozen":
                    sources = spec.get("acceptance_sources", [])
                    if not isinstance(sources, list) or not all(
                        isinstance(item, str) for item in sources
                    ):
                        raise WorkbenchError("冻结规格的验收输入清单无效")
                    paths.update(sources)
        return paths

    def _versioned_project_paths(self) -> set[str]:
        paths: set[str] = set()
        definition = self.project_definition()
        if definition:
            paths.add(str(definition["path"]))
        target, template = self._config_locations()
        config_path = target if target.is_file() else template
        if config_path.is_file() and not self._skipped(config_path):
            try:
                paths.add(config_path.relative_to(self.root).as_posix())
            except ValueError:
                pass
        return paths

    def _design_contract_paths(self) -> set[str]:
        return {
            relative for relative in (
                "metadata.json",
                "spec/design.csir.yaml", "ip/nebula.lock.json",
                "integration/nebula-assembly.json",
            )
            if (self.root / relative).is_file()
        }

    def _input_fingerprint(
        self, paths: set[str], document: dict[str, Any],
    ) -> str:
        digest = hashlib.sha256()
        digest.update(json.dumps(
            document, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        ).encode("utf-8"))
        for relative in sorted(paths):
            path = self.root / relative
            if not path.is_file():
                continue
            data = path.read_bytes()
            digest.update(relative.encode("utf-8") + b"\0" + hashlib.sha256(data).digest())
        return digest.hexdigest()

    def _write_operation(self, operation: dict[str, Any]) -> None:
        self.operations_dir.mkdir(parents=True, exist_ok=True)
        path = self.operations_dir / f"{operation['id']}.json"
        temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        try:
            temporary.write_text(
                json.dumps(operation, ensure_ascii=False, indent=2), encoding="utf-8",
            )
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)

    def _mark_validation_stale(self) -> None:
        self.state_root.mkdir(parents=True, exist_ok=True)
        marker = self.state_root / "validation-state.json"
        state = json.loads(marker.read_text()) if marker.is_file() else {}
        state["stale"] = True
        marker.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    def _restore_paths(self, commit: str, paths: list[str]) -> None:
        for relative in paths:
            target = self._safe_path(relative)
            data = self._commit_bytes(commit, relative)
            if data is None:
                if target.is_file() or target.is_symlink():
                    target.unlink()
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)

    def _working_bytes(self, relative: str) -> bytes | None:
        path = self._safe_path(relative)
        return path.read_bytes() if path.is_file() else None

    def _commit_bytes(self, commit: str, relative: str) -> bytes | None:
        result = subprocess.run(
            ["git", "show", f"{commit}:{relative}"], cwd=self.root, capture_output=True,
        )
        return result.stdout if result.returncode == 0 else None

    def _head(self) -> str:
        result = self._git("rev-parse", "HEAD", check=False)
        return result.stdout.strip() if result.returncode == 0 else ""

    def _git_toplevel(self) -> Path | None:
        result = self._git("rev-parse", "--show-toplevel", check=False)
        return Path(result.stdout.strip()).resolve() if result.returncode == 0 else None

    def _git(self, *args: str, check: bool = True, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            ["git", *args], cwd=self.root, env=env, capture_output=True, text=True,
        )
        if check and result.returncode != 0:
            raise WorkbenchError(result.stderr.strip() or result.stdout.strip())
        return result

    def _safe_path(self, relative: str) -> Path:
        candidate = (self.root / relative).resolve()
        if candidate == self.root or self.root not in candidate.parents:
            raise WorkbenchError("路径超出工程目录")
        if any(part in _SKIP_DIRS for part in PurePosixPath(relative).parts):
            raise WorkbenchError("path is managed by Chip Nebula")
        return candidate

    def _safe_file(self, relative: str) -> Path:
        path = self._safe_path(relative)
        if not path.is_file():
            raise WorkbenchError("文件不存在")
        return path

    def _skipped(self, path: Path) -> bool:
        try:
            parts = path.relative_to(self.root).parts
        except ValueError:
            return True
        return path.name == ".gitkeep" or any(part in _SKIP_DIRS for part in parts)

    def _matching_files(self, patterns: list[str]) -> list[str]:
        matches: set[str] = set()
        for pattern in patterns:
            for value in glob.glob(str(self.root / pattern), recursive=True):
                path = Path(value)
                if path.is_file() and not self._skipped(path):
                    matches.add(path.relative_to(self.root).as_posix())
        return sorted(matches)


class WorkbenchRunManager:
    """Run deterministic checks and direct-edit Agent operations."""

    def __init__(self, project: WorkbenchProject) -> None:
        self.project = project
        self.project.state_root.mkdir(parents=True, exist_ok=True)
        self._processes: dict[str, subprocess.Popen[Any]] = {}
        self._resource_samples: dict[str, tuple[float, float]] = {}
        self._viewer_processes: dict[int, subprocess.Popen[Any]] = {}
        self._threads: dict[str, threading.Thread] = {}
        self._stop_requests: set[str] = set()
        self._agent_pool: AgentPoolManager | None = None
        self._assistant_pools: dict[str, AgentPoolManager] = {}
        self._agent_operation = ""
        self._agent_stop_events: dict[str, threading.Event] = {}
        self._checker_review_stop_events: dict[str, threading.Event] = {}
        self._agent_validation_runs: dict[str, str] = {}
        self._agent_lock_handle: Any | None = None
        self._lock = threading.Lock()
        self._backend_pid = os.getpid()
        self._backend_start_token = _process_start_token(self._backend_pid)
        self._recover_interrupted()

    def _owned_record_fields(self) -> dict[str, Any]:
        return {
            "backend_pid": self._backend_pid,
            "backend_start_token": self._backend_start_token,
        }

    def project_constraints_author_resume_point(
        self, spec_revision_id: str,
    ) -> dict[str, str]:
        """Return the latest compatible Author session for one spec revision.

        Project-constraint decisions are consolidated by a separate read-only
        Role.  Finalization must therefore resume the Author that produced the
        candidate questions, never whichever implementation-constraints
        operation happened to run most recently.  The finalization itself is
        still a new Task/Run with its own write grant and audit trail.
        """
        if not spec_revision_id:
            return {}
        for operation in self.project.list_operations():
            if (
                operation.get("stage") != "impl_constraints"
                or operation.get("action_kind") != "constraints_questions_generate"
                or operation.get("status") != "succeeded"
                or operation.get("spec_revision_id") != spec_revision_id
            ):
                continue
            session_id = str(operation.get("session_id", "")).strip()
            framework = str(operation.get("framework", "")).strip()
            if not session_id or framework not in {
                "codex", "opencode", "claude-code", "qodercli",
            }:
                continue
            return {
                "operation_id": str(operation.get("id", "")),
                "session_id": session_id,
                "framework": framework,
                "model": str(operation.get("model", "")).strip(),
            }
        return {}

    @staticmethod
    def _record_owner_alive(record: dict[str, Any]) -> bool:
        pid = record.get("backend_pid")
        token = record.get("backend_start_token")
        if type(pid) is not int or pid <= 1 or not isinstance(token, str) or not token:
            return False
        return _process_start_token(pid) == token

    def _snapshot_existing_paths(
        self, commit: str, candidates: set[str],
    ) -> list[str]:
        result = self.project._git(
            "-c", "core.quotePath=false", "ls-tree", "-r", "-z",
            "--name-only", commit, check=False,
        )
        if result.returncode != 0:
            raise WorkbenchError("无法读取固定快照输入清单")
        available = {path for path in result.stdout.split("\0") if path}
        return sorted(path for path in candidates if path in available)

    def generic_acceptance_state(self) -> dict[str, Any]:
        spec = SpecificationWorkspace(self.project.root).state()
        try:
            return GenericAcceptanceWorkspace(self.project.root).state(spec)
        except (GenericAcceptanceError, GenericRTLContractError) as exc:
            raise WorkbenchError(str(exc)) from exc

    def preview_existing_checker_review(self) -> dict[str, Any]:
        """Review exact imported RTL/checker bytes without executing project code."""
        return preview_existing_checker(
            self.project.root, SpecificationWorkspace(self.project.root).state(),
            git_repository=self.project.is_git_repository(),
        )

    def start_existing_checker_review(self, plan_digest: str) -> dict[str, Any]:
        """Run an existing checker in a fixed snapshot as a tool-only Task Graph task."""
        with self._lock:
            plan = self.preview_existing_checker_review()
            if plan["plan_digest"] != plan_digest:
                raise WorkbenchConflict("RTL、checker 或规格已变化；请重新检查现有验收输入")
            if not plan["ready"]:
                raise WorkbenchConflict("现有 checker 自检受阻：" + "；".join(plan["blockers"]))
            if self._agent_operation:
                raise WorkbenchConflict("AI 正在修改源码；完成后再自检当前 checker")
            if any(
                item.get("kind") == "checker_review"
                and item.get("status") in {"starting", "running"}
                for item in self.list_runs()
            ):
                raise WorkbenchConflict("当前工程已有 checker 自检正在运行")
            snapshot = self.project.capture_snapshot("existing checker review")
            run_id = f"checker-review-{uuid.uuid4().hex[:10]}"
            config = self.project.config()
            snapshot_paths = self._snapshot_existing_paths(
                snapshot["commit"], set(plan["input_hashes"]) | {"spec/design.csir.yaml"},
            )
            run = {
                "id": run_id, "kind": "checker_review", "status": "starting",
                "verdict": "not_started", "engineering_verdict": "not_checked",
                **self._owned_record_fields(),
                "snapshot": snapshot, "snapshot_paths": snapshot_paths,
                "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                "source_fingerprint": self.project.fingerprint(),
                "input_fingerprint": self.project.fingerprint(),
                "fingerprint_kind": "project",
                "spec_digest": plan["spec_digest"], "spec_qualified": False,
                "rtl": plan["rtl"], "checker": plan["checker"],
                "input_hashes": plan["input_hashes"], "plan_digest": plan_digest,
                "commands": ["checker_selftest"], "tool_versions": {},
                "input_digests": [f"git:{snapshot['commit']}", plan["spec_digest"],
                                  *plan["input_hashes"].values()],
                "artifacts": [], "errors": [],
            }
            self._write_run(run)
            stop_event = threading.Event()
            self._checker_review_stop_events[run_id] = stop_event
            worker = threading.Thread(
                target=self._execute_existing_checker_review,
                args=(run_id, stop_event), daemon=True,
                name=f"checker-review-{run_id}",
            )
            self._threads[run_id] = worker
            try:
                worker.start()
            except Exception:
                run.update({"status": "launch_failed", "verdict": "launch_failed",
                            "error": "无法启动 checker 自检工作线程"})
                self._write_run(run)
                self._checker_review_stop_events.pop(run_id, None)
                raise
            return run

    def existing_checker_review_evidence(self, run_id: str) -> dict[str, Any]:
        run = self.get_run(run_id)
        if run.get("kind") != "checker_review":
            raise WorkbenchError("所选运行不是现有 checker 自检")
        directory = self.project.runs_dir / run_id
        try:
            log = (directory / "run.log").read_text(encoding="utf-8", errors="replace")
            report_path = directory / "report.json"
            report = (
                json.loads(report_path.read_text(encoding="utf-8"))
                if report_path.is_file() else {
                    "verdict": run.get("verdict", "failed"),
                    "diagnostics": [run.get("error", "自检未产生完整报告")],
                }
            )
        except (OSError, json.JSONDecodeError) as exc:
            raise WorkbenchError("checker 自检证据尚未归档") from exc
        return {"run_id": run_id, "report": report, "log": log}

    def freeze_existing_checker_review(
        self, run_id: str, *, confirmed: bool = False,
    ) -> dict[str, Any]:
        if not confirmed:
            raise WorkbenchError("请先审阅现有 checker、需求覆盖和缺陷注入证据，再确认冻结")
        with self._lock:
            run = self.get_run(run_id)
            if (
                run.get("kind") != "checker_review" or run.get("status") != "finished"
                or run.get("verdict") != "passed"
                or run.get("engineering_verdict") != "candidate_review_required"
            ):
                raise WorkbenchConflict("当前运行不是可审核冻结的 checker 自检候选")
            spec = SpecificationWorkspace(self.project.root).state()
            if not spec.get("frozen") or not spec.get("valid") or spec.get("spec_digest") != run.get("spec_digest"):
                raise WorkbenchConflict("冻结规格在自检后变化，请重新运行现有 checker 自检")
            try:
                report = json.loads(
                    (self.project.runs_dir / run_id / "report.json").read_text(encoding="utf-8")
                )
                frozen = GenericAcceptanceWorkspace(self.project.root).freeze(
                    spec, report, snapshot_commit=str(run["snapshot"]["commit"]),
                )
            except (OSError, json.JSONDecodeError, GenericAcceptanceError) as exc:
                raise WorkbenchConflict(str(exc)) from exc
            snapshot = self.project.capture_snapshot("existing checker acceptance freeze")
            return {**frozen, "snapshot": snapshot}

    def _execute_existing_checker_review(
        self, run_id: str, stop_event: threading.Event,
    ) -> None:
        directory = self.project.runs_dir / run_id
        with self._lock:
            run = self.get_run(run_id)
            if run["status"] == "stopped" or stop_event.is_set():
                run["status"] = run["verdict"] = "stopped"
                self._write_run(run)
                self._checker_review_stop_events.pop(run_id, None)
                return
            run["status"] = "running"
            self._write_run(run)
        try:
            spec = SpecificationWorkspace(self.project.root).state()
            if spec.get("spec_digest") != run["spec_digest"]:
                raise WorkbenchConflict("checker 自检启动前规格已变化")
            contract = checker_contract(spec, self.project.root)
            report = self._verify_checker_snapshot(
                run["snapshot"], spec, contract, directory, stop_event,
            )
            verdict = str(report.get("verdict", "failed"))
            run["status"] = (
                "finished" if report.get("status") not in {"stopped", "timeout", "launch_failed"}
                else report["status"]
            )
            run["verdict"] = (
                "passed" if verdict == "passed" else
                report.get("status") if report.get("status") in {"stopped", "timeout", "launch_failed"}
                else "failed"
            )
            run["engineering_verdict"] = (
                "candidate_review_required" if run["verdict"] == "passed" else "failed"
            )
            run["tool_versions"] = report.get("tool_versions", {})
            run["command_evidence"] = report.get("command_evidence", [])
            run["errors"] = [
                {"severity": "ERROR", "code": "CHECKER_SELFTEST", "message": item}
                for item in report.get("diagnostics", [])
            ]
            run["artifacts"] = [
                {"path": item, "kind": "report" if item == "report.json" else "log" if item == "run.log" else "source",
                 "size": (directory / item).stat().st_size,
                 "sha256": _file_sha256(directory / item)}
                for item in ("report.json", "run.log", "mutant.sv")
                if (directory / item).is_file()
            ]
            run["evidence_digest"] = "sha256:" + hashlib.sha256(
                json.dumps(
                    {item["path"]: item["sha256"] for item in run["artifacts"]},
                    sort_keys=True, separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest()
        except Exception as exc:
            run["status"] = "failed"
            run["verdict"] = "failed"
            run["engineering_verdict"] = "failed"
            run["error"] = str(exc)
            (directory / "run.log").write_text(str(exc) + "\n", encoding="utf-8")
            run["artifacts"] = [{
                "path": "run.log", "kind": "log",
                "size": (directory / "run.log").stat().st_size,
                "sha256": _file_sha256(directory / "run.log"),
            }]
        finally:
            with self._lock:
                if stop_event.is_set() or self.get_run(run_id)["status"] == "stopped":
                    run["status"] = run["verdict"] = "stopped"
                    run["engineering_verdict"] = "failed"
                run["finished_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
                self._write_run(run)
                self._checker_review_stop_events.pop(run_id, None)

    def acceptance_candidate_evidence(self, operation_id: str) -> dict[str, Any]:
        """Read only the archived checker self-test belonging to this operation."""
        operation = self.project.operation(operation_id)
        if operation.get("stage") != "acceptance_generation":
            raise WorkbenchError("operation is not an acceptance candidate")
        checks = operation.get("acceptance_checks", [])
        if not checks:
            raise WorkbenchError("acceptance self-test evidence is not available")
        check = checks[-1]
        if not isinstance(check, dict):
            raise WorkbenchError("invalid acceptance evidence record")
        attempt = check.get("attempt")
        if type(attempt) is not int or attempt < 1:
            raise WorkbenchError("invalid acceptance evidence attempt")
        evidence_dir = (self.project.root / str(check.get("evidence_dir", ""))).resolve()
        expected = (self.project.operations_dir / f"{operation_id}-acceptance-{attempt}").resolve()
        if not expected.is_relative_to(self.project.operations_dir.resolve()) or evidence_dir != expected:
            raise WorkbenchError("invalid acceptance evidence location")
        try:
            report_path = evidence_dir / "report.json"
            log_path = evidence_dir / "run.log"
            if report_path.stat().st_size > 2 * 1024 * 1024 or log_path.stat().st_size > 4 * 1024 * 1024:
                raise WorkbenchError("acceptance evidence exceeds preview limit")
            report = json.loads(report_path.read_text(encoding="utf-8"))
            log = log_path.read_text(encoding="utf-8", errors="replace")
        except (OSError, json.JSONDecodeError) as exc:
            raise WorkbenchError("acceptance self-test evidence cannot be read") from exc
        return {"operation_id": operation_id, "attempt": attempt, "report": report, "log": log}

    def freeze_generic_acceptance(
        self, operation_id: str, *, confirmed: bool = False,
    ) -> dict[str, Any]:
        """Human approval of a self-tested checker; never auto-freeze an Agent output."""
        if not confirmed:
            raise WorkbenchError("请先审阅 checker、需求覆盖和缺陷注入证据，再确认冻结")
        with self._lock:
            if self._agent_operation:
                raise WorkbenchConflict("AI 任务仍在运行，不能冻结验收环境")
            operation = self.project.operation(operation_id)
            if (
                operation.get("stage") != "acceptance_generation"
                or operation.get("status") != "succeeded"
                or operation.get("engineering_verdict") != "candidate_review_required"
            ):
                raise WorkbenchConflict("当前操作不是已通过自检的独立验收候选")
            spec = SpecificationWorkspace(self.project.root).state()
            try:
                contract = checker_contract(spec, self.project.root)
            except (GenericAcceptanceError, GenericRTLContractError) as exc:
                raise WorkbenchConflict(str(exc)) from exc
            if spec["spec_digest"] != operation.get("spec_digest"):
                raise WorkbenchConflict("冻结规格已变化，需重新生成 checker")
            checks = operation.get("acceptance_checks", [])
            if not checks or checks[-1].get("verdict") != "passed":
                raise WorkbenchConflict("独立 checker 自检证据缺失")
            report_path = self.project.root / str(checks[-1]["evidence_dir"]) / "report.json"
            try:
                report = json.loads(report_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise WorkbenchConflict("独立 checker 自检报告不可读取") from exc
            rtl = self.project.root / contract["rtl"]
            if not rtl.is_file() or report.get("rtl_sha256") != _file_sha256(rtl):
                raise WorkbenchConflict("RTL 在 checker 自检后变化，请重新生成并自检")
            try:
                frozen = GenericAcceptanceWorkspace(self.project.root).freeze(
                    spec, report,
                    snapshot_commit=str(report.get("snapshot", {}).get("commit", "")),
                )
            except GenericAcceptanceError as exc:
                raise WorkbenchConflict(str(exc)) from exc
            snapshot = self.project.capture_snapshot("generic acceptance freeze")
            return {**frozen, "snapshot": snapshot}

    def start_validation(
        self, kind: str = "all", *, config_override: WorkbenchConfig | None = None,
        workflow_id: str = "",
    ) -> dict[str, Any]:
        config = config_override or self.project.config()
        validation_flow = PhysicalFlow(self.project.root, config.physical)
        validation_tools = validation_flow.validation_tools()
        ast_format = ""
        commands: list[tuple[str, str]] = []
        spec = SpecificationWorkspace(self.project.root).state()
        acceptance_contract_state: dict[str, Any] = {}
        if (
            spec.get("frozen") and spec.get("valid")
            and spec.get("document", {}).get("design_kind") == "generic_module"
        ):
            try:
                acceptance_contract_state = GenericAcceptanceWorkspace(
                    self.project.root
                ).state(spec)
            except (GenericAcceptanceError, GenericRTLContractError) as exc:
                acceptance_contract_state = {"valid": False, "reason": str(exc)}
            if acceptance_contract_state.get("valid") and kind in {"all", "simulation"}:
                if config.workdir != ".":
                    raise WorkbenchError(
                        "通用独立验收需要工程根目录作为工作目录，请检查验证配置"
                    )
                if spec["document"].get("instances"):
                    top = str(spec["document"]["name"])
                    commands = [
                        ("elaboration", "verilator --lint-only --sv -Wall "
                         f"-Wno-fatal -Werror-PINMISSING --top-module {top} "
                         "-f integration/nebula.f"),
                        ("simulation", acceptance_contract_state["runner"]),
                    ]
                else:
                    ast_format = verilator_ast_format(
                        validation_tools.get("verilator", {}).get("path") or None
                    )
                    commands = [
                        ("elaboration", elaboration_command(
                            spec, parameters=config.top_parameters,
                            ast_format=ast_format,
                        )),
                        ("simulation", acceptance_contract_state["runner"]),
                    ]
        if not commands:
            commands = self.project.validation_commands(config, kind)
        if not commands:
            raise WorkbenchError("no validation command is configured")
        validation_environment = validation_flow.validation_environment()
        tool_versions = self._tool_versions(validation_environment)
        if spec.get("document", {}).get("status") == "frozen" and not (
            spec.get("frozen") and spec.get("valid")
        ):
            raise WorkbenchConflict("冻结规格或验收输入已改变；请创建新修订并重新冻结")
        snapshot = self.project.capture_snapshot("validation input")
        snapshot_paths = self._snapshot_existing_paths(
            snapshot["commit"],
            self.project.validation_input_paths(
                config, include_project_metadata=True,
            ),
        )
        run_id = f"validation-{uuid.uuid4().hex[:10]}"
        if spec.get("frozen") and spec.get("valid"):
            acceptance_plan = spec["acceptance_plan"]
            if acceptance_contract_state.get("valid") and kind in {"all", "simulation"}:
                acceptance_plan = {
                    **acceptance_plan,
                    "checks": [
                        {
                            **item, "status": "implemented",
                            "evidence_marker_required": item.get("kind") == "simulation",
                        }
                        if item.get("id") in acceptance_contract_state.get("check_ids", [])
                        else item
                        for item in acceptance_plan.get("checks", [])
                    ],
                    "acceptance_contract_digest": acceptance_contract_state["contract_digest"],
                }
            spec_digest = spec["spec_digest"]
            spec_qualified = (
                bool(acceptance_contract_state.get("valid"))
                and any(name == "simulation" for name, _command in commands)
                if spec["document"].get("design_kind") == "generic_module"
                else True
            )
        else:
            acceptance_plan = self._compatibility_acceptance_plan(
                snapshot["commit"], snapshot["tree"], commands,
            )
            spec_digest = acceptance_plan["spec_digest"]
            spec_qualified = False
        lock = {}
        lock_path = self.project.root / "ip" / "nebula.lock.json"
        if lock_path.is_file():
            try:
                lock = json.loads(lock_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                lock = {}
        environment_digest = "sha256:" + hashlib.sha256(json.dumps({
            "commands": commands, "workdir": config.workdir,
            "timeout": config.timeout, "success_pattern": config.success_pattern,
            "success_evidence": config.success_evidence,
            "tools": validation_tools, "tool_versions": tool_versions,
        }, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
        acceptance_sources_digest = (
            str(acceptance_contract_state.get("contract_digest", ""))
            if spec.get("document", {}).get("design_kind") == "generic_module"
            else str(spec.get("acceptance_sources_digest", ""))
        )
        input_digests = [
            f"git:{snapshot['commit']}", spec_digest,
            acceptance_sources_digest,
            str(lock.get("lock_digest", "")), environment_digest,
        ]
        run = {
            "id": run_id, "kind": "validation", "status": "starting", "verdict": "not_started",
            **self._owned_record_fields(),
            "snapshot": snapshot, "commands": [name for name, _ in commands],
            "snapshot_paths": snapshot_paths,
            "reproduction_commands": [
                {"name": name, "command": command} for name, command in commands
            ],
            "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "source_fingerprint": self.project.fingerprint(),
            "input_fingerprint": (
                self.project.generic_acceptance_fingerprint(config)
                if acceptance_contract_state.get("valid")
                and spec.get("document", {}).get("design_kind") == "generic_module"
                and kind in {"all", "simulation"}
                else self.project.validation_fingerprint(config)
            ),
            "fingerprint_kind": (
                "generic_acceptance_v1"
                if acceptance_contract_state.get("valid")
                and spec.get("document", {}).get("design_kind") == "generic_module"
                and kind in {"all", "simulation"}
                else "validation"
            ), "artifacts": [], "errors": [],
            **({"validation_config": asdict(config)} if config_override else {}),
            "tool_versions": tool_versions,
            "tool_paths": {
                name: item.get("path", "")
                for name, item in validation_tools.items()
            },
            "spec_digest": spec_digest, "spec_qualified": spec_qualified,
            "acceptance_sources_digest": acceptance_sources_digest,
            "acceptance_contract": acceptance_contract_state,
            "elaboration_ast_format": ast_format,
            "qualification_blocker": (
                str(acceptance_contract_state.get("reason", ""))
                if spec.get("document", {}).get("design_kind") == "generic_module"
                and not spec_qualified else ""
            ),
            "acceptance_plan": acceptance_plan,
            "input_digests": [item for item in input_digests if item],
        }
        self._write_run(run)
        thread = threading.Thread(
            target=self._execute_validation,
            args=(
                run_id, snapshot["commit"], commands, config,
                validation_environment,
            ), daemon=True,
        )
        self._threads[run_id] = thread
        thread.start()
        return run

    def _compatibility_acceptance_plan(
        self, snapshot_commit: str, snapshot_tree: str,
        commands: list[tuple[str, str]],
    ) -> dict[str, Any]:
        """Expose corpus verification intent without treating it as frozen CSIR.

        Corpus projects often carry a small ``metadata.json`` with independent
        behaviors covered by one aggregate testbench.  Preserve those items in
        the evidence matrix and bind each one to the actual simulation command.
        They remain compatibility evidence (``spec_qualified`` stays false),
        so this cannot accidentally satisfy the formal delivery gate.
        """
        fallback = {
            "spec_digest": f"legacy:{snapshot_tree}",
            "requirement_ids": ["legacy.validation"],
            "checks": [
                {
                    "id": f"legacy.{name}", "kind": name,
                    "requirement_ids": ["legacy.validation"],
                }
                for name, _command in commands
            ],
        }
        try:
            archived = self.project._git(
                "show", f"{snapshot_commit}:metadata.json", check=False,
            )
            if archived.returncode != 0 or len(archived.stdout.encode("utf-8")) > 1_000_000:
                return fallback
            metadata = json.loads(archived.stdout)
        except (UnicodeError, json.JSONDecodeError):
            return fallback
        raw_checks = metadata.get("verification_checks") if isinstance(metadata, dict) else None
        if not isinstance(raw_checks, list):
            return fallback
        descriptions: list[str] = []
        for value in raw_checks[:100]:
            if not isinstance(value, str):
                continue
            description = value.strip()
            if description and description not in descriptions:
                descriptions.append(description[:500])
        if not descriptions:
            return fallback
        command_names = [name for name, _command in commands]
        check_kind = "simulation" if "simulation" in command_names else command_names[-1]
        requirement_ids = [
            f"legacy.metadata.{index:02d}"
            for index in range(1, len(descriptions) + 1)
        ]
        return {
            "spec_digest": f"legacy:{snapshot_tree}",
            "source": "metadata.json",
            "requirement_ids": requirement_ids,
            "requirement_descriptions": dict(zip(requirement_ids, descriptions)),
            "checks": [
                {
                    "id": f"legacy.metadata-check.{index:02d}",
                    "kind": check_kind,
                    "description": description,
                    "requirement_ids": [requirement_id],
                }
                for index, (requirement_id, description) in enumerate(
                    zip(requirement_ids, descriptions), start=1,
                )
            ],
        }

    def physical_environment(self, *, platform: str = "") -> dict[str, Any]:
        config = self.project.config()
        if platform and platform != "sky130hd":
            raise WorkbenchError("首期物理环境检查仅支持 sky130hd")
        # The product flow configures its own workspace from the frozen target.
        # Inspect that target without changing the project's manual-flow setup.
        physical = replace(config.physical, platform=platform) if platform else config.physical
        environment = PhysicalFlow(
            self.project.root, physical
        ).inspect_environment(
            config.top_parameters, ignore_expected_versions=bool(platform),
        )
        # An unconfigured flow already reports that its generated files are
        # missing.  Also expose the read-only project discovery result so the
        # physical page can explain *why* the wizard cannot generate them
        # without making the user open the modal first (for example, a
        # multi-clock top that the current single-clock flow cannot constrain).
        if not (config.physical.enabled and config.physical.command):
            try:
                detection = self.project.detect_physical_project()
            except WorkbenchError as exc:
                environment["setup_diagnostics"] = [{
                    "severity": "error",
                    "code": "PHYSICAL_SETUP_DETECTION_FAILED",
                    "message": str(exc),
                }]
            else:
                environment["setup_diagnostics"] = list(
                    detection.get("diagnostics", [])
                )
                environment["setup_top"] = detection.get("suggested_top", "")
                selected = next((
                    item for item in detection.get("top_candidates", [])
                    if item.get("name") == detection.get("suggested_top")
                ), None)
                environment["setup_clock_candidates"] = list(
                    selected.get("clock_candidates", []) if selected else []
                )
        return environment

    def start_physical(self, mode: str = "all", *, workflow_id: str = "") -> dict[str, Any]:
        if mode not in {"all", "physical"}:
            raise WorkbenchError("physical mode must be all or physical")
        if any(
            item.get("kind") in {"physical", "formal"}
            and item.get("status") in {"starting", "running"}
            for item in self.list_runs()
        ):
            raise WorkbenchConflict("another RTL-to-GDS run is already active")
        config = self.project.config()
        soc = self.project.frozen_soc_specification()
        if soc is not None:
            definition_path = self.project.root / "physical/chip-nebula/flow-definition.json"
            try:
                definition = json.loads(definition_path.read_text(encoding="utf-8"))
                clock = definition["clock"]
                if (
                    definition.get("platform") != config.physical.platform
                    or config.top_module != soc["name"]
                    or config.physical.design != soc["name"]
                ):
                    raise WorkbenchConflict(
                        "物理流程平台或顶层与冻结 SoC 规格不一致"
                    )
                self.project.assert_frozen_soc_physical_target(
                    top_module=str(definition["top_module"]),
                    clock_port=str(clock["port"]),
                    clock_period_ns=float(clock["period_ns"]),
                    platform=config.physical.platform,
                )
            except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
                raise WorkbenchConflict(
                    "冻结 SoC 缺少可核对的物理流程定义；请先生成物理流程"
                ) from exc
            from chip_nebula.taskgraph.assembly import AssemblyError, AssemblyService
            from chip_nebula.taskgraph.ip_library import IPLibrary, IPLibraryError

            library = IPLibrary(self.project.root)
            try:
                assembly_service = AssemblyService(self.project.root, library)
                spec_state = SpecificationWorkspace(self.project.root).state()
                assembly_service.verify_current(spec_state, library.read_lock())
                assembly_service.verify_acceptance_contract(spec_state)
            except (AssemblyError, IPLibraryError, SpecificationError) as exc:
                raise WorkbenchConflict(
                    f"冻结 SoC 装配或锁定依赖已变化：{exc}"
                ) from exc
        generic = self.project.frozen_generic_physical_contract()
        if generic is not None:
            if mode != "all":
                raise WorkbenchConflict(
                    "通用模块物理签核须先在同一固定快照运行独立功能验收"
                )
            definition_path = self.project.root / "physical/chip-nebula/flow-definition.json"
            try:
                definition = json.loads(definition_path.read_text(encoding="utf-8"))
                clock = definition["clock"]
                self.project.assert_frozen_generic_physical_target(
                    top_module=str(definition["top_module"]),
                    clock_port=str(clock["port"]),
                    clock_period_ns=float(clock["period_ns"]),
                    platform=str(definition["platform"]),
                )
                if (
                    config.top_module != generic["top_module"]
                    or config.physical.design != generic["top_module"]
                    or config.physical.platform != generic["platform"]
                    or definition.get("frozen_spec_digest") != generic["spec_digest"]
                    or definition.get("acceptance_contract_digest")
                    != generic["acceptance_contract_digest"]
                    or definition.get("simulation_command") != generic["simulation_command"]
                    or definition.get("sources") != generic["sources"]
                    or definition.get("lock_digest", "") != generic["lock_digest"]
                    or definition.get("assembly_digest", "") != generic["assembly_digest"]
                ):
                    raise WorkbenchConflict(
                        "通用物理流程与冻结规格、RTL 或独立验收版本不一致"
                    )
            except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
                raise WorkbenchConflict(
                    "通用模块缺少可核对的物理流程定义；请重新生成流程"
                ) from exc
        physical = PhysicalFlow(self.project.root, config.physical)
        environment = physical.inspect_environment(config.top_parameters)
        if not environment.get("ready"):
            if not environment.get("configured"):
                raise WorkbenchError(
                    "当前工程尚未配置 RTL→GDS 物理流程；请在 Implementation "
                    "或 Complete Flow 页面点击“探测并生成流程”，确认顶层、时钟、周期和平台"
                )
            details = [
                *environment.get("missing", []),
                *environment.get("mismatches", []),
                *environment.get("project_issues", []),
            ]
            raise WorkbenchError(
                "物理流程环境未就绪：" + (
                    "; ".join(details) if details else "请重新检查工具、PDK 和工程约束"
                )
            )
        snapshot = self.project.capture_snapshot("RTL-to-GDS input")
        snapshot_paths = self._snapshot_existing_paths(
            snapshot["commit"],
            self.project.physical_input_paths(
                config, include_project_metadata=True,
            ),
        )
        run_id = f"physical-{uuid.uuid4().hex[:10]}"
        profile_document = {
            **asdict(config.physical),
            "top_parameters": dict(config.top_parameters),
        }
        profile_digest = "sha256:" + hashlib.sha256(
            json.dumps(
                profile_document, ensure_ascii=False, sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        tool_versions = {
            name: item.get("version", "")
            for name, item in environment.get("tools", {}).items()
            if item.get("version")
        }
        if environment.get("orfs", {}).get("commit"):
            tool_versions["orfs"] = environment["orfs"]["commit"]
        platform_inputs: dict[str, str] = {}
        for item in environment.get("platform_files", []):
            path = Path(str(item.get("path", "")))
            if item.get("ready") and path.is_file():
                digest = hashlib.sha256()
                with path.open("rb") as handle:
                    for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                        digest.update(chunk)
                platform_inputs[path.name] = "sha256:" + digest.hexdigest()
        environment_digest = "sha256:" + hashlib.sha256(
            json.dumps({
                "tools": tool_versions,
                "orfs_commit": environment.get("orfs", {}).get("commit", ""),
                "platform": config.physical.platform,
                "platform_inputs": platform_inputs,
            }, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        input_digests = [
            f"git:{snapshot['commit']}", profile_digest,
            environment_digest,
        ]
        run = {
            "id": run_id, "kind": "physical", "mode": mode,
            "status": "starting", "verdict": "not_started",
            **self._owned_record_fields(),
            "snapshot": snapshot,
            "snapshot_paths": snapshot_paths,
            "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "source_fingerprint": self.project.fingerprint(),
            "input_fingerprint": self.project.physical_fingerprint(),
            "fingerprint_kind": "physical",
            "artifacts": [], "errors": [], "summary": {},
            "physical_profile": profile_document,
            "physical_stages": self._physical_stages(),
            "current_stage": "environment",
            "tool_versions": tool_versions,
            "platform_inputs": platform_inputs,
            "input_digests": input_digests,
            "input_audit": environment["input_audit"],
        }
        self._write_run(run)
        thread = threading.Thread(
            target=self._execute_physical,
            args=(run_id, snapshot["commit"], mode, config),
            daemon=True,
        )
        self._threads[run_id] = thread
        thread.start()
        return run

    def formal_environment(self) -> dict[str, Any]:
        """Report the selected proof tools without running project code."""
        tool_root = PhysicalFlow(
            self.project.root, self.project.config().physical
        )._toolchain_root()
        return FormalEquivalenceRunner(tool_root).inspect_environment()

    def start_equivalence(
        self, operation_id: str, *, timeout_seconds: int = 600,
        clock_port: str = "", reset_port: str = "", reset_active: str = "",
    ) -> dict[str, Any]:
        """Compare a completed RTL operation's fixed before/after snapshots."""
        operation = self.project.operation(operation_id)
        if operation.get("status") != "succeeded" or not operation.get("after"):
            raise WorkbenchError("只能对已完成的 RTL 操作执行等价证明")
        if operation.get("stage", "rtl") != "rtl":
            raise WorkbenchError("规格修改不能作为 RTL 等价优化候选")
        config = self.project.config()
        sources = list(config.design_files) if config.design_files else [
            path for path in self.project._matching_files(config.source_globs)
            if Path(path).suffix.lower() in {".v", ".sv"}
            and not any(part.lower() in {"tb", "testbench", "sim", "simulation"}
                        for part in PurePosixPath(path).parts[:-1])
        ]
        sources = list(dict.fromkeys(sources))
        if not config.top_module or not sources:
            raise WorkbenchError("请在工程配置中指定设计顶层和 RTL 设计文件")
        if config.filelists and not config.design_files:
            raise WorkbenchError("等价证明需要明确的设计文件顺序；请先配置 Design Sources")
        try:
            proof_config = EquivalenceConfig(
                top_module=config.top_module,
                source_files=tuple(sources),
                include_dirs=tuple(config.include_dirs),
                defines=tuple(config.defines),
                parameters=dict(config.top_parameters),
                clock_port=clock_port, reset_port=reset_port,
                reset_active=reset_active,
                timeout_seconds=timeout_seconds,
                jobs=1,
            )
        except OptimizationError as exc:
            raise WorkbenchError(str(exc)) from exc
        environment = self.formal_environment()
        if not environment["ready"]:
            raise WorkbenchError(
                "形式验证工具缺失：" + ", ".join(environment["missing"])
            )
        for snapshot in (operation["before"], operation["after"]):
            for source in sources:
                result = self.project._git(
                    "cat-file", "-e", f"{snapshot['commit']}:{source}", check=False,
                )
                if result.returncode != 0:
                    raise WorkbenchError(f"固定快照缺少设计源：{source}")
        with self._lock:
            if any(
                item.get("kind") in {"formal", "physical"}
                and item.get("status") in {"starting", "running"}
                for item in self.list_runs()
            ):
                raise WorkbenchConflict("已有高负载形式或物理任务运行中")
            run_id = f"formal-{uuid.uuid4().hex[:10]}"
            snapshot_paths = self._snapshot_existing_paths(
                operation["after"]["commit"],
                self.project.validation_input_paths(
                    config, include_project_metadata=True,
                ),
            )
            formal_config = proof_config.contract() | {
                "timeout_seconds": proof_config.timeout_seconds,
                "jobs": proof_config.jobs,
            }
            run = {
                "id": run_id, "kind": "formal", "status": "starting",
                "verdict": "not_started", **self._owned_record_fields(),
                "operation_id": operation_id,
                "snapshot": operation["after"],
                "baseline_snapshot": operation["before"],
                "snapshot_paths": snapshot_paths,
                "formal_config": formal_config,
                "source_fingerprint": self.project.fingerprint(),
                "input_fingerprint": self.project.fingerprint(),
                "fingerprint_kind": "formal",
                "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                "artifacts": [], "partitions": [], "resources": {},
                "tool_versions": {
                    name: item.get("version", "")
                    for name, item in environment["tools"].items()
                    if item.get("version")
                },
                "input_digests": [
                    f"git:{operation['before']['commit']}",
                    f"git:{operation['after']['commit']}",
                ],
            }
            self._write_run(run)
            thread = threading.Thread(
                target=self._execute_equivalence,
                args=(run_id, proof_config), daemon=True,
            )
            self._threads[run_id] = thread
            thread.start()
        return run

    def _execute_equivalence(
        self, run_id: str, proof_config: EquivalenceConfig,
    ) -> None:
        run_dir = self.project.runs_dir / run_id
        gold_workspace = self.project.workspaces_dir / f"{run_id}-gold"
        candidate_workspace = self.project.workspaces_dir / f"{run_id}-candidate"
        run = self.get_run(run_id)
        run.update({
            "status": "running", "verdict": "running",
            "started_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        })
        self._write_run(run)
        try:
            self.project._git(
                "worktree", "add", "--detach", str(gold_workspace),
                run["baseline_snapshot"]["commit"],
            )
            self.project._git(
                "worktree", "add", "--detach", str(candidate_workspace),
                run["snapshot"]["commit"],
            )
            runner = FormalEquivalenceRunner(
                PhysicalFlow(
                    self.project.root, self.project.config().physical
                )._toolchain_root()
            )

            def process_changed(process: subprocess.Popen[str] | None) -> None:
                with self._lock:
                    if process is None:
                        self._processes.pop(run_id, None)
                    else:
                        self._processes[run_id] = process

            with (run_dir / "run.log").open("w", encoding="utf-8") as live_log:
                def log_changed(chunk: str) -> None:
                    live_log.write(chunk)
                    live_log.flush()

                result = runner.run(
                    gold_workspace, candidate_workspace,
                    run_dir / "artifacts" / "formal", proof_config,
                    process_callback=process_changed,
                    log_callback=log_changed,
                )
            if not (run_dir / "run.log").stat().st_size:
                (run_dir / "run.log").write_text(
                    result.reason + "\n", encoding="utf-8",
                )
            run.update({
                "status": "finished", "verdict": result.verdict,
                "reason": result.reason, "returncode": result.returncode,
                "partitions": list(result.partitions),
                "reset_proof": dict(result.reset_proof),
                "resources": dict(result.resources),
                "tool_versions": dict(result.tool_versions),
                "input_digests": [
                    *run["input_digests"], *result.input_digests,
                ],
                "command_evidence": [{
                    "command": list(result.command),
                    "returncode": result.returncode,
                }],
                "artifacts": [
                    {**item, "path": "formal/" + item["path"]}
                    for item in result.artifacts
                ],
                "finished_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            })
        except Exception as exc:
            run.update({
                "status": "failed_to_start", "verdict": "unsupported",
                "reason": str(exc),
                "finished_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            })
            (run_dir / "run.log").write_text(
                str(exc) + "\n", encoding="utf-8",
            )
        finally:
            self._processes.pop(run_id, None)
            for workspace in (gold_workspace, candidate_workspace):
                if workspace.exists():
                    self.project._git(
                        "worktree", "remove", "--force", str(workspace),
                        check=False,
                    )
            self.project._git("worktree", "prune", check=False)
            persisted = run_dir / "run.json"
            if persisted.is_file():
                current = json.loads(persisted.read_text(encoding="utf-8"))
                if current.get("status") == "stopped":
                    run.update({
                        "status": "stopped", "verdict": "stopped",
                        "finished_at": current.get("finished_at")
                        or dt.datetime.now(dt.timezone.utc).isoformat(),
                    })
            self._write_run(run)

    @staticmethod
    def stage_skill(workspace: str) -> dict[str, str]:
        if workspace not in _ASSISTANT_WORKSPACES:
            raise WorkbenchError("unsupported assistant workspace")
        skill = load_stage_skill(workspace)
        return {
            "id": skill.id, "version": skill.version,
            "workspace": skill.workspace, "digest": skill.digest,
        }

    def start_assistant(
        self, instruction: str, framework: str, *, workspace: str,
        mode: str = "ask",
    ) -> dict[str, Any]:
        """Run a stage assistant against an immutable project snapshot.

        Assistant questions and plan drafts never enter the live checkout and
        never claim the single-writer lock.  Framework state and any attempted
        edits are confined to a disposable detached worktree.
        """
        instruction = instruction.strip()
        if not instruction:
            raise WorkbenchError("assistant question is required")
        if workspace not in _ASSISTANT_WORKSPACES:
            raise WorkbenchError("unsupported assistant workspace")
        if mode not in _ASSISTANT_MODES:
            raise WorkbenchError("assistant mode must be ask or plan")
        if framework == "mock":
            raise WorkbenchError("mock cannot be used for a real assistant answer")
        executable = {
            "codex": "codex", "opencode": "opencode",
            "claude-code": "claude", "qodercli": "qodercli",
        }.get(framework)
        if not executable or not shutil.which(executable):
            raise WorkbenchError(f"agent framework is unavailable: {framework}")
        skill = load_stage_skill(workspace)
        snapshot = self.project.capture_snapshot(
            f"{workspace} assistant context", include_tool_outputs=False,
        )
        assistant_id = f"assistant-{uuid.uuid4().hex[:10]}"
        record = {
            "id": assistant_id,
            "workspace": workspace,
            "mode": mode,
            "instruction": instruction,
            "framework": framework,
            "status": "starting",
            "response": "",
            "snapshot": snapshot,
            "context_digest": f"git-tree:{snapshot['tree']}",
            "stage_skill": skill.as_record(),
            "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            **self._owned_record_fields(),
        }
        self._write_assistant(record)
        thread = threading.Thread(
            target=self._execute_assistant,
            args=(assistant_id,), daemon=True,
        )
        self._threads[assistant_id] = thread
        thread.start()
        return record

    def create_execution_plan(
        self, instruction: str, framework: str, *, workspace: str,
        write_paths: list[str] | None = None,
        clarifications: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Compile a reviewable live-edit plan without invoking an Agent."""
        instruction = instruction.strip()
        if not instruction:
            raise WorkbenchError("execution plan instruction is required")
        if workspace not in _ASSISTANT_WORKSPACES:
            raise WorkbenchError("unsupported assistant workspace")
        config = self.project.config()
        spec = SpecificationWorkspace(self.project.root).state()
        stage = "specification" if workspace == "requirements" else "rtl"
        ip_catalog = (
            specification_catalog_context(self.project.root)
            if stage == "specification" else {}
        )
        generation_path = ""
        generation_blocker = ""
        acceptance_path = ""
        acceptance_blocker = ""
        if (
            workspace == "rtl-analysis"
            and spec.get("configured")
            and spec.get("document", {}).get("design_kind") in {
                "generic_module", "single_clock_soc",
            }
        ):
            if spec.get("document", {}).get("instances"):
                if spec.get("valid") and spec.get("frozen"):
                    try:
                        missing_children = [
                            item for item in generated_submodules(spec)
                            if not (self.project.root / item["source"]).is_file()
                        ]
                    except GeneratedSubmoduleError as exc:
                        generation_blocker = str(exc)
                        missing_children = []
                    if missing_children:
                        stage = "rtl_generation"
                        generation_path = missing_children[0]["source"]
            else:
                name = str(spec["document"].get("name", ""))
                if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_$]*", name):
                    try:
                        candidate = generation_target(spec)
                    except GenericRTLContractError as exc:
                        generation_blocker = str(exc)
                        candidate = ""
                    if candidate and not (self.project.root / candidate).is_file():
                        stage = "rtl_generation"
                        generation_path = candidate
                    elif candidate and GenericAcceptanceWorkspace(self.project.root).revisable_prior(spec):
                        stage = "rtl_repair"
                        generation_path = candidate
                    if generation_path:
                        try:
                            generation_target(spec)
                        except GenericRTLContractError as exc:
                            generation_blocker = str(exc)
        if (
            workspace == "simulation" and spec.get("configured")
            and spec.get("document", {}).get("design_kind") == "generic_module"
        ):
            try:
                contract = checker_contract(spec, self.project.root)
                acceptance_path = contract["testbench"]
                acceptance_state = GenericAcceptanceWorkspace(self.project.root).state(spec)
                if not acceptance_state["frozen"]:
                    stage = "acceptance_generation"
                    if not (self.project.root / contract["rtl"]).is_file():
                        acceptance_blocker = "先根据冻结 CSIR 生成 RTL，再准备独立 checker"
                    # A stale contract remains as evidence. A new self-tested
                    # candidate may supersede it after explicit human review.
            except (GenericAcceptanceError, GenericRTLContractError) as exc:
                stage = "acceptance_generation"
                acceptance_blocker = str(exc)
        answers: dict[str, str] = {}
        if clarifications:
            if stage != "specification":
                raise WorkbenchError("澄清回答只能用于需求规格阶段")
            if not isinstance(clarifications, dict):
                raise WorkbenchError("澄清回答必须按问题 ID 提交")
            questions = {
                str(item.get("id", index)): item
                for index, item in enumerate(spec["document"].get("open_questions", []))
                if isinstance(item, dict) and item.get("status") != "resolved"
            }
            for question_id, answer in clarifications.items():
                if question_id not in questions or not isinstance(answer, str) or not answer.strip():
                    raise WorkbenchError(f"澄清问题无效或回答为空：{question_id}")
                answers[question_id] = answer.strip()
            instruction += "\n\n以下为用户针对现有待确认事项的回答。仅可解决已回答的问题；其余问题保持原样、不得推断：\n"
            instruction += "\n".join(
                f"{question_id}：{questions[question_id].get('question', '')}\n用户回答：{answer}"
                for question_id, answer in answers.items()
            )
        if workspace == "requirements":
            role_scope = ("spec/design.csir.yaml",)
            gates = ["CSIR deterministic compile", "human specification freeze"]
        elif stage in {"rtl_generation", "rtl_repair"}:
            role_scope = (
                (generation_path,)
                if not violations([generation_path], config.write_paths) else ()
            )
            gates = [
                "frozen CSIR", "exact RTL write scope", "Verilator elaboration",
                "independent acceptance pending",
            ]
        elif stage == "acceptance_generation":
            role_scope = (acceptance_path,) if acceptance_path else ()
            gates = [
                "frozen CSIR", "separate checker write scope",
                "real Icarus simulation", "zero-output mutant rejected",
                "human acceptance freeze",
            ]
        elif workspace in {"rtl-analysis", "simulation", "ip-integration"}:
            role_scope = tuple(config.write_paths)
            gates = ["write scope", "lint", "frozen acceptance regression"]
        else:
            role_scope = ()
            gates = ["read-only review"]
        requested = tuple(write_paths or role_scope)
        effective = list(_intersect_path_scopes(role_scope, requested))
        blockers: list[str] = []
        if generation_blocker:
            blockers.append(generation_blocker)
        if acceptance_blocker:
            blockers.append(acceptance_blocker)
        if not self.project.is_git_repository():
            blockers.append("工程尚未建立 Git 基线")
        if not role_scope:
            blockers.append("当前阶段只支持问答和方案分析，不能直接写入工程")
        if role_scope and not effective:
            blockers.append("请求的写入范围不在当前阶段授权范围内")
        if stage == "rtl" and spec.get("frozen") and spec.get("valid") and (
            spec.get("document", {}).get("design_kind") == "generic_module"
        ):
            try:
                protected = checker_contract(spec, self.project.root)["testbench"]
                if (self.project.root / protected).exists() and not violations(
                    [protected], effective
                ):
                    blockers.append("设计 Agent 的写范围覆盖独立 checker；请收窄到 RTL/集成逻辑")
            except (GenericAcceptanceError, GenericRTLContractError):
                pass
        if stage == "specification" and spec.get("frozen"):
            blockers.append("规格已经冻结，必须先创建新修订")
        lock_digest = ""
        lock_path = self.project.root / "ip" / "nebula.lock.json"
        if lock_path.is_file():
            try:
                lock_digest = str(
                    json.loads(lock_path.read_text(encoding="utf-8"))
                    .get("lock_digest", "")
                )
            except (OSError, json.JSONDecodeError):
                blockers.append("IP 依赖锁无法读取")
        current_runs = [
            item for item in self.list_runs()
            if item.get("verdict") in {"passed", "failed"}
        ]
        plan_id = f"plan-{uuid.uuid4().hex[:10]}"
        plan = {
            "id": plan_id,
            "workspace": workspace,
            "stage": stage,
            "instruction": instruction,
            "framework": framework,
            "status": "draft",
            "clarifications": answers,
            "ip_catalog": ip_catalog,
            "write_paths": effective,
            "inputs": {
                "project_fingerprint": self.project.fingerprint(),
                "validation_fingerprint": self.project.validation_fingerprint(),
                "spec_digest": str(spec.get("spec_digest", "")),
                "spec_frozen": bool(spec.get("frozen")),
                "ip_lock_digest": lock_digest,
                "ip_catalog_digest": ip_catalog.get("digest", ""),
                "latest_evidence_run_id": current_runs[0]["id"] if current_runs else "",
            },
            "tasks": [
                {"id": "agent-edit", "executor": "agent", "stage": stage},
                {"id": "deterministic-check", "executor": "tool", "depends_on": ["agent-edit"]},
                {"id": "repair", "executor": "agent", "depends_on": ["deterministic-check"], "conditional": True},
            ],
            "gates": gates,
            "budgets": {
                "max_repairs": 3,
                "max_candidates": 6,
                "max_physical_candidates": 2,
                "wall_time_seconds": 21_600,
                "memory_limit_bytes": None,
            },
            "blockers": blockers,
            "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        }
        self._write_execution_plan(plan)
        return plan

    def create_input_remediation_plan(
        self, path: str, framework: str = "codex",
    ) -> dict[str, Any]:
        """Turn one current physical input issue into a reviewed RTL-only plan."""
        config = self.project.config()
        if not config.physical.enabled or not config.physical.command:
            raise WorkbenchConflict("物理流程尚未配置；请先检查工程输入或生成物理流程")
        audit = PhysicalFlow(self.project.root, config.physical).audit_inputs()
        issue = next(
            (item for item in audit["issues"] if item["path"] == path), None,
        )
        if issue is None:
            raise WorkbenchConflict("所选缺项已不存在或未被当前物理输入清单登记；请重新检查环境")
        specification = SpecificationWorkspace(self.project.root).state()
        proposal = propose_input_remediation(issue, specification)
        if not proposal["eligible"]:
            raise WorkbenchConflict("不能由设计 Agent 补全：" + "；".join(proposal["blockers"]))
        if violations(proposal["write_paths"], config.write_paths):
            raise WorkbenchConflict("缺失 RTL 不在本工程授权的 AI 写入范围")
        plan = self.create_execution_plan(
            proposal["instruction"], framework,
            workspace=proposal["workspace"],
            write_paths=proposal["write_paths"],
        )
        if (
            plan["stage"] != proposal["stage"]
            or plan["write_paths"] != proposal["write_paths"]
        ):
            raise WorkbenchConflict("输入补全方案的实际写权限与冻结规格不一致")
        plan["origin"] = "physical_input_audit"
        plan["input_issue"] = dict(issue)
        plan["input_spec_digest"] = proposal["spec_digest"]
        self._write_execution_plan(plan)
        return plan

    def execution_plan(self, plan_id: str) -> dict[str, Any]:
        if not _RUN_ID_RE.fullmatch(plan_id):
            raise WorkbenchError("invalid execution plan id")
        path = self.project.execution_plans_dir / f"{plan_id}.json"
        if not path.is_file():
            raise WorkbenchError("execution plan not found")
        try:
            plan = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise WorkbenchError("execution plan is unreadable") from exc
        return self._with_generation_freshness(plan)

    def _with_generation_freshness(self, plan: dict[str, Any]) -> dict[str, Any]:
        if plan.get("stage") != "rtl_generation" or plan.get("status") != "succeeded":
            return plan
        result = dict(plan)
        result["generation_current_verdict"] = "stale"
        operation_id = str(plan.get("operation_id", ""))
        try:
            operation = self.project.operation(operation_id)
            spec = SpecificationWorkspace(self.project.root).state()
            relative = str(operation["generation_path"])
            after = str(operation["after"]["commit"])
            source_current = (
                self.project._working_bytes(relative)
                == self.project._commit_bytes(after, relative)
            )
            spec_current = bool(
                spec.get("valid") and spec.get("frozen")
                and spec.get("spec_digest") == operation.get("spec_digest")
            )
            if source_current and spec_current:
                result["generation_current_verdict"] = "generated_unverified"
            else:
                result["generation_stale_reason"] = (
                    "RTL 或冻结 CSIR 已变化；原展开报告只适用于旧快照"
                )
        except (WorkbenchError, KeyError, TypeError, SpecificationError):
            result["generation_stale_reason"] = "无法核对生成快照或冻结规格"
        return result

    def list_execution_plans(self) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        if not self.project.execution_plans_dir.is_dir():
            return result
        for path in self.project.execution_plans_dir.glob("plan-*.json"):
            try:
                result.append(self._with_generation_freshness(
                    json.loads(path.read_text(encoding="utf-8"))
                ))
            except (OSError, json.JSONDecodeError):
                continue
        result.sort(key=lambda item: str(item.get("created_at", "")), reverse=True)
        return result

    def start_execution_plan(self, plan_id: str) -> dict[str, Any]:
        with self._lock:
            plan = self.execution_plan(plan_id)
            if plan.get("status") != "draft":
                raise WorkbenchConflict("execution plan has already been started")
            if plan.get("blockers"):
                raise WorkbenchConflict(
                    "execution plan is blocked", list(plan.get("blockers", [])),
                )
            inputs = plan.get("inputs", {})
            current_spec = SpecificationWorkspace(self.project.root).state()
            if plan.get("origin") == "physical_input_audit":
                config = self.project.config()
                if not config.physical.enabled or not config.physical.command:
                    raise WorkbenchConflict(
                        "物理流程配置已变化；请重新审查输入并形成补全方案"
                    )
                current_audit = PhysicalFlow(
                    self.project.root, config.physical,
                ).audit_inputs()
                issue_path = str(plan.get("input_issue", {}).get("path", ""))
                issue = next(
                    (item for item in current_audit["issues"] if item["path"] == issue_path),
                    None,
                )
                proposal = propose_input_remediation(issue or {}, current_spec)
                if (
                    not issue or not proposal["eligible"]
                    or proposal["write_paths"] != plan.get("write_paths")
                    or proposal["spec_digest"] != plan.get("input_spec_digest")
                ):
                    raise WorkbenchConflict(
                        "物理输入缺项、冻结规格或补全权限已变化；请重新审查并形成方案"
                    )
            if (
                inputs.get("project_fingerprint") != self.project.fingerprint()
                or (
                    inputs.get("validation_fingerprint")
                    and inputs["validation_fingerprint"] != self.project.validation_fingerprint()
                )
                or inputs.get("spec_digest") != current_spec.get("spec_digest")
                or inputs.get("spec_frozen") != bool(current_spec.get("frozen"))
                or (
                    plan.get("stage") == "specification"
                    and inputs.get("ip_catalog_digest")
                    != specification_catalog_context(self.project.root)["digest"]
                )
            ):
                raise WorkbenchConflict(
                    "工程输入在方案生成后发生变化，请重新生成执行方案",
                )
            plan["status"] = "starting"
            self._write_execution_plan(plan)
        try:
            operation = self.start_agent(
                str(plan["instruction"]), str(plan["framework"]),
                list(plan.get("write_paths", [])), stage=str(plan["stage"]),
                max_repairs=int(plan.get("budgets", {}).get("max_repairs", 3)),
                execution_plan_id=plan_id,
                clarifications=dict(plan.get("clarifications", {})),
            )
        except Exception:
            with self._lock:
                latest = self.execution_plan(plan_id)
                if latest.get("status") == "starting":
                    latest["status"] = "draft"
                    self._write_execution_plan(latest)
            raise
        with self._lock:
            plan = self.execution_plan(plan_id)
            if plan["status"] == "starting":
                plan.update({
                    "status": "running", "operation_id": operation["id"],
                    "started_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                })
                self._write_execution_plan(plan)
        return {"plan": plan, "operation": self.project.operation(operation["id"])}

    def _agent_workflow_paused(self, operation_id: str) -> bool:
        try:
            operation = self.project.operation(operation_id)
        except WorkbenchError:
            return False
        plan_id = str(operation.get("execution_plan_id", ""))
        if not plan_id:
            return False
        return self.execution_plan(plan_id).get("status") in {
            "pause_requested", "paused",
        }

    def pause_execution_plan(self, plan_id: str) -> dict[str, Any]:
        with self._lock:
            plan = self.execution_plan(plan_id)
            operation_id = str(plan.get("operation_id", ""))
            if plan.get("status") not in {"running", "pause_requested", "paused"}:
                raise WorkbenchConflict("only a running execution plan can be paused")
            if operation_id != self._agent_operation:
                raise WorkbenchConflict("execution plan is no longer active")
            if plan["status"] != "paused":
                plan["status"] = "pause_requested"
                self._write_execution_plan(plan)
        return plan

    def resume_execution_plan(self, plan_id: str) -> dict[str, Any]:
        with self._lock:
            plan = self.execution_plan(plan_id)
            operation_id = str(plan.get("operation_id", ""))
            if plan.get("status") not in {"pause_requested", "paused"}:
                raise WorkbenchConflict("execution plan is not paused")
            if operation_id != self._agent_operation:
                raise WorkbenchConflict("execution plan is no longer active")
            fingerprint = plan.get("pause_fingerprint")
            if fingerprint and fingerprint != self.project.validation_fingerprint():
                raise WorkbenchConflict(
                    "工程输入在暂停期间发生变化，请停止当前操作并重新生成执行方案"
                )
            plan["status"] = "running"
            plan.pop("pause_fingerprint", None)
            self._write_execution_plan(plan)
        return plan

    def _await_agent_resume(
        self, operation_id: str, stop_event: threading.Event,
    ) -> bool:
        """Wait at an execution boundary, never suspending an active tool."""
        while not stop_event.is_set():
            if not self._agent_workflow_paused(operation_id):
                return True
            operation = self.project.operation(operation_id)
            plan_id = str(operation.get("execution_plan_id", ""))
            if plan_id:
                with self._lock:
                    plan = self.execution_plan(plan_id)
                    if plan.get("status") == "pause_requested":
                        plan["status"] = "paused"
                        plan["pause_fingerprint"] = self.project.validation_fingerprint()
                        self._write_execution_plan(plan)
            stop_event.wait(0.2)
        return False

    def _write_execution_plan(self, plan: dict[str, Any]) -> None:
        self.project.execution_plans_dir.mkdir(parents=True, exist_ok=True)
        path = self.project.execution_plans_dir / f"{plan['id']}.json"
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8",
        )
        temporary.replace(path)

    def assistant_session(self, assistant_id: str) -> dict[str, Any]:
        if not _RUN_ID_RE.fullmatch(assistant_id):
            raise WorkbenchError("invalid assistant session id")
        path = self.project.assistant_dir / f"{assistant_id}.json"
        if not path.is_file():
            raise WorkbenchError("assistant session not found")
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise WorkbenchError("assistant session is unreadable") from exc

    def list_assistant_sessions(self, workspace: str = "") -> list[dict[str, Any]]:
        if workspace and workspace not in _ASSISTANT_WORKSPACES:
            raise WorkbenchError("unsupported assistant workspace")
        result: list[dict[str, Any]] = []
        if not self.project.assistant_dir.is_dir():
            return result
        for path in self.project.assistant_dir.glob("assistant-*.json"):
            try:
                item = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if not workspace or item.get("workspace") == workspace:
                result.append(item)
        result.sort(
            key=lambda item: (str(item.get("created_at", "")), str(item.get("id", ""))),
        )
        return result

    def _execute_assistant(self, assistant_id: str) -> None:
        record = self.assistant_session(assistant_id)
        workspace = self.project.workspaces_dir / assistant_id
        stage = f"assistant-{record['workspace']}"
        pool = AgentPoolManager(
            default_framework=record["framework"], force_framework=True,
        )
        with self._lock:
            self._assistant_pools[assistant_id] = pool
        try:
            record.update({
                "status": "running",
                "started_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            })
            self._write_assistant(record)
            self.project.workspaces_dir.mkdir(parents=True, exist_ok=True)
            self.project._git(
                "worktree", "add", "--detach", str(workspace),
                str(record["snapshot"]["commit"]),
            )
            skill = dict(record.get("stage_skill") or {})
            verify_stage_skill(skill)
            if skill["workspace"] != record["workspace"]:
                raise ValueError("recorded stage skill belongs to another workspace")
            purpose = (
                "回答用户问题"
                if record["mode"] == "ask"
                else "形成一份可执行方案，但不要执行或修改文件"
            )
            prompt = (
                f"你是 Chip Nebula 的 {record['workspace']} 阶段工程顾问。"
                f"请基于当前固定工程快照{purpose}。不得修改、创建或删除任何文件，"
                "不得执行破坏性 Git 操作，不得声称没有真实报告支持的工具结论。"
                "请用简体中文回答，并在结论后列出所依据的工程文件或报告；代码、"
                "标识符、命令和原始日志保持原样。\n\n"
                f"阶段技能 {skill['id']}@{skill['version']} "
                f"({skill['digest']})：\n{skill['instructions']}\n\n"
                f"用户请求：\n{record['instruction']}"
            )
            task = TaskManifest(
                task_id=assistant_id,
                feature_id=assistant_id,
                stage=stage,
                assigned_agent=f"{record['workspace']}-advisor",
                context=TaskContext(top_module=self.project.config().top_module),
                target=[], write_paths=[],
                timeout=self.project.config().agent_timeout,
                run_id=assistant_id,
                max_iterations=1,
                live_workspace=False,
                prompt_override=prompt,
            )
            result = pool.dispatch(
                task, workspace, project_root=self.project.root,
            )
            attempted_writes = violations(detect_changed_paths(workspace), [])
            succeeded = bool(result.success and not attempted_writes)
            response = result.execution_log[-100_000:]
            if attempted_writes:
                response = (
                    response
                    + "\n\n只读助手尝试写入隔离工作区，回答已拒绝："
                    + "、".join(attempted_writes)
                )
            record.update({
                "status": "succeeded" if succeeded else "failed",
                "response": response,
                "agent_session_id": result.session_id or "",
                "attempted_writes": attempted_writes,
                "error": "" if succeeded else (
                    result.error or "read-only assistant attempted to modify files"
                ),
                "finished_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            })
        except Exception as exc:
            record.update({
                "status": "failed", "error": str(exc),
                "finished_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            })
        finally:
            if workspace.exists():
                self.project._git(
                    "worktree", "remove", "--force", str(workspace), check=False,
                )
            self.project._git("worktree", "prune", check=False)
            with self._lock:
                self._assistant_pools.pop(assistant_id, None)
            self._write_assistant(record)

    def stop_assistant(self, assistant_id: str) -> bool:
        record = self.assistant_session(assistant_id)
        if record.get("status") not in {"starting", "running"}:
            return False
        with self._lock:
            pool = self._assistant_pools.get(assistant_id)
        if pool is None:
            return False
        from chip_nebula.adapters.base import session_registry
        session_id = session_registry.get(
            assistant_id, f"assistant-{record['workspace']}",
        ) or ""
        if not session_id:
            return False
        pool.terminate(session_id)
        return True

    def _write_assistant(self, record: dict[str, Any]) -> None:
        self.project.assistant_dir.mkdir(parents=True, exist_ok=True)
        path = self.project.assistant_dir / f"{record['id']}.json"
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8",
        )
        temporary.replace(path)

    def start_agent(
        self, instruction: str, framework: str, write_paths: list[str], *,
        stage: str = "rtl", max_repairs: int = 3,
        execution_plan_id: str = "",
        clarifications: dict[str, str] | None = None,
        model: str = "",
        resume_session_id: str = "",
        action_kind: str = "",
        operation_metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if type(max_repairs) is not int or not 0 <= max_repairs <= 3:
            raise WorkbenchError("automatic repair budget must be within 0..3")
        if framework == "mock":
            raise WorkbenchError("mock cannot be used for a real RTL edit")
        executable = {"codex": "codex", "opencode": "opencode", "claude-code": "claude", "qodercli": "qodercli"}.get(framework)
        if not executable or not shutil.which(executable):
            raise WorkbenchError(f"agent framework is unavailable: {framework}")
        if stage not in {
            "rtl", "rtl_generation", "rtl_repair", "acceptance_generation",
            "specification", "advisory", "specir", "impl_constraints",
        }:
            raise WorkbenchError("unsupported desktop Agent stage")
        if stage == "specir" and not action_kind:
            action_kind = "spec_generate"
        if stage == "specir" and action_kind in {"spec_generate", "spec_repair", "decision_apply"}:
            raise WorkbenchError("规格生成和返工必须由内置 specification-baseline-preparation recipe 调度")
        if stage == "specir" and action_kind not in {
            "spec_generate", "spec_repair", "decision_apply", "acceptance_propose",
            "spec_diagnostics_decide",
        }:
            raise WorkbenchError("specir operation requires a supported action kind")
        if stage == "impl_constraints" and action_kind not in {
            "constraints_questions_generate", "project_decisions_consolidate",
            "constraints_finalize",
        }:
            raise WorkbenchError(
                "implementation-constraints operation requires a supported action kind"
            )
        if stage == "advisory":
            return self.start_assistant(
                instruction, framework, workspace="project-manager", mode="ask",
            )
        config = self.project.config()
        specification = None
        target_path = ""
        if stage in {"specification", "rtl_generation", "rtl_repair", "acceptance_generation"}:
            try:
                specification = SpecificationWorkspace(self.project.root).state()
            except SpecificationError as exc:
                raise WorkbenchError(f"现有规格无法读取：{exc}") from exc
            if stage == "specification" and specification.get("frozen"):
                raise WorkbenchError("规格已经冻结；请先创建新修订，不能由 AI 直接改写冻结规格")
            if stage == "rtl_repair" and (
                not specification.get("valid")
                or not specification.get("frozen")
                or not (
                    specification.get("acceptance_sources_digest")
                    or GenericAcceptanceWorkspace(self.project.root).revisable_prior(specification)
                )
            ):
                raise WorkbenchConflict("RTL 修订需要有效的冻结规格与独立验收；同名通用模块还需可核对的旧版记录")
            generation_instance = ""
            if stage in {"rtl_generation", "rtl_repair"}:
                if specification["document"].get("instances"):
                    try:
                        targets = [
                            item for item in generated_submodules(specification)
                            if item["source"] in write_paths
                        ]
                    except GeneratedSubmoduleError as exc:
                        raise WorkbenchError(str(exc)) from exc
                    if len(targets) != 1 or write_paths != [targets[0]["source"]]:
                        raise WorkbenchConflict(
                            "生成子模块只能授权冻结规格中的一个精确 RTL 文件"
                        )
                    target_path = targets[0]["source"]
                    generation_instance = targets[0]["instance"]
                elif stage == "rtl_generation" or (
                    stage == "rtl_repair"
                    and GenericAcceptanceWorkspace(self.project.root).revisable_prior(specification)
                ):
                    try:
                        target_path = generation_target(specification)
                    except GenericRTLContractError as exc:
                        raise WorkbenchError(str(exc)) from exc
                else:
                    raise WorkbenchConflict("RTL 修订需要冻结规格中的授权模块或旧版验收记录")
                target = self.project.root / target_path
                if stage == "rtl_generation" and target.exists():
                    raise WorkbenchConflict(f"目标 RTL 已存在，请使用 RTL 修改流程：{target_path}")
                if stage == "rtl_repair" and (target.is_symlink() or not target.is_file()):
                    raise WorkbenchConflict(f"授权修复的 RTL 缺失或不是普通文件：{target_path}")
                if violations([target_path], config.write_paths):
                    raise WorkbenchConflict(f"目标 RTL 不在工程授权写入范围：{target_path}")
            if stage == "acceptance_generation":
                try:
                    contract = checker_contract(specification, self.project.root)
                    target_path = contract["testbench"]
                    acceptance_state = GenericAcceptanceWorkspace(self.project.root).state(specification)
                except (GenericAcceptanceError, GenericRTLContractError) as exc:
                    raise WorkbenchError(str(exc)) from exc
                if not (self.project.root / contract["rtl"]).is_file():
                    raise WorkbenchConflict("目标 RTL 尚未生成，不能准备独立验收")
                if (self.project.root / acceptance_state["path"]).exists() and not (
                    GenericAcceptanceWorkspace(self.project.root).revisable_prior(specification)
                ):
                    raise WorkbenchConflict("验收契约无法核对旧版 checker；请人工审核后创建新版本")
        decision_consolidation_action = action_kind in {
            "spec_diagnostics_decide", "project_decisions_consolidate",
        }
        if decision_consolidation_action:
            raise WorkbenchError(
                "规格诊断与决策归并已迁移到静态 PREPARE Recipe；"
                "桌面 Agent 不能绕过固定 Task/WorkItem 发布决策"
            )
        role_paths = (
            ("spec/design.csir.yaml",) if stage == "specification"
            else (target_path,) if stage in {"rtl_generation", "rtl_repair", "acceptance_generation"}
            else tuple(write_paths) if stage == "specir"
            else tuple(write_paths) if stage == "impl_constraints"
            else tuple(config.write_paths)
        )
        role_name = (
            "project-constraints-author" if stage == "impl_constraints"
            else "project-verification-architect" if action_kind == "acceptance_propose"
            else ""
        )
        role = load_project_static_roles(self.project.root).get(role_name) if role_name else None
        if role_name and role is None:
            raise WorkbenchError(f"missing built-in role: {role_name}")
        role = role or Role(
            name=(
                "desktop-requirements-engineer" if stage == "specification"
                else "desktop-acceptance-engineer" if stage == "acceptance_generation"
                else "desktop-rtl-designer"
            ),
            version=1,
            instruction=(
                "在当前桌面工程中编写可检查的 CSIR 规格，并使用简体中文汇报需求缺项；"
                if stage == "specification" else
                "只根据冻结规格编写独立验收 checker，不得修改 RTL；"
                if stage == "acceptance_generation" else
                "在 spec/ 内生成、修订并检查 Compact SpecIR 规格产物；不得修改 RTL 或测试；"
                if stage == "specir" else
                "根据签署规格与平台库存生成项目实现约束；不得修改 RTL 或测试；"
                if stage == "impl_constraints" else
                "在当前桌面工程中修改 RTL，并使用简体中文汇报修改和验证结果；"
            ) + "代码、标识符、命令和原始日志保持原样。",
        )
        effective_paths = list(_intersect_path_scopes(
            role_paths, tuple(write_paths),
        ))
        if not effective_paths and not decision_consolidation_action:
            raise WorkbenchError("requested write paths do not overlap the project AI write scope")
        if stage == "rtl":
            protected_spec = SpecificationWorkspace(self.project.root).state()
            if protected_spec.get("frozen") and protected_spec.get("valid") and (
                protected_spec.get("document", {}).get("design_kind") == "generic_module"
            ):
                try:
                    protected = checker_contract(protected_spec, self.project.root)["testbench"]
                    if (self.project.root / protected).exists() and not violations(
                        [protected], effective_paths
                    ):
                        raise WorkbenchConflict(
                            "设计 Agent 的写范围覆盖独立 checker；请收窄到 RTL/集成逻辑"
                        )
                except (GenericAcceptanceError, GenericRTLContractError):
                    pass
        with self._lock:
            if self._agent_operation:
                raise WorkbenchConflict("another AI edit is already running")
            self._claim_agent_lock()
            try:
                catalog = {}
                if stage == "specification":
                    catalog = specification_catalog_context(self.project.root)
                    if execution_plan_id:
                        expected = self.execution_plan(execution_plan_id).get("inputs", {}).get(
                            "ip_catalog_digest", ""
                        )
                        if expected != catalog["digest"]:
                            raise WorkbenchConflict(
                                "IP 目录在方案形成后变化；请重新生成需求规格方案"
                            )
                operation = self.project.create_operation(
                    instruction, effective_paths, stage=stage,
                )
                operation.update(self._owned_record_fields())
                operation["max_repairs"] = max_repairs
                operation["framework"] = framework
                if action_kind:
                    operation["action_kind"] = action_kind
                if stage == "impl_constraints" or action_kind == "acceptance_propose":
                    operation["role_system_prompt"] = role.instruction
                if operation_metadata:
                    operation.update(operation_metadata)
                if model:
                    operation["model"] = model
                if stage in {"rtl_generation", "rtl_repair"}:
                    operation["spec_digest"] = specification["spec_digest"]
                    operation["generation_path"] = target_path
                    operation["generation_instance"] = generation_instance
                    operation["engineering_verdict"] = "not_checked"
                if stage == "acceptance_generation":
                    operation["spec_digest"] = specification["spec_digest"]
                    operation["acceptance_path"] = target_path
                    operation["engineering_verdict"] = "not_checked"
                if stage == "specification":
                    operation["ip_catalog"] = catalog
                    operation["clarifications"] = dict(clarifications or {})
                    operation["open_questions_before"] = [
                        {
                            "key": str(item.get("id", index)),
                            "question": str(item.get("question", "")),
                        }
                        for index, item in enumerate(
                            specification["document"].get("open_questions", [])
                        )
                        if isinstance(item, dict) and item.get("status") != "resolved"
                    ]
                if execution_plan_id:
                    operation["execution_plan_id"] = execution_plan_id
                self.project._write_operation(operation)
                self._agent_operation = operation["id"]
                self._agent_stop_events[operation["id"]] = threading.Event()
            except Exception:
                self._release_agent_lock()
                raise
        thread = threading.Thread(
            target=self._execute_agent,
            args=(
                operation["id"], instruction, framework, effective_paths, stage,
                resume_session_id,
            ),
            daemon=True,
        )
        self._threads[operation["id"]] = thread
        try:
            thread.start()
        except Exception:
            with self._lock:
                self._agent_operation = ""
                self._agent_stop_events.pop(operation["id"], None)
                self._release_agent_lock()
            self.project.finish_operation(
                operation["id"], status="failed",
                summary="桌面后端无法启动 Agent 工作线程。",
            )
            raise
        return operation

    def get_run(self, run_id: str) -> dict[str, Any]:
        if not _RUN_ID_RE.fullmatch(run_id):
            raise WorkbenchError("invalid run id")
        path = self.project.runs_dir / run_id / "run.json"
        if not path.is_file():
            raise WorkbenchError("run not found")
        run = json.loads(path.read_text(encoding="utf-8"))
        if run.get("verdict") in {
            "passed", "failed", "proved", "counterexample",
            "inconclusive", "timeout", "resource_exhausted", "unsupported",
        }:
            kind = run.get("fingerprint_kind")
            validation_config = (
                WorkbenchConfig.from_document(run["validation_config"])
                if kind == "validation" and isinstance(run.get("validation_config"), dict)
                else None
            )
            current = (
                self.project.validation_fingerprint(validation_config) if kind == "validation"
                else self.project.generic_acceptance_fingerprint(validation_config)
                if kind == "generic_acceptance_v1"
                else self.project.physical_fingerprint() if kind == "physical"
                else self.project.fingerprint()
            )
            stored = run.get("input_fingerprint", run.get("source_fingerprint"))
            if (
                stored != current and kind == "physical"
                and not self.project.config().physical.required_inputs
            ):
                legacy = self.project.physical_fingerprint(
                    legacy_empty_required_inputs=True,
                )
                if stored == legacy:
                    current = legacy
            if stored != current:
                run["historical_verdict"] = run["verdict"]
                run["verdict"] = "stale"
                run["stale_reason"] = "current_project_inputs_changed"
        if run.get("status") in {"starting", "running"}:
            run["runtime_health"] = self._runtime_health(run_id, run)
        return run

    def _runtime_health(
        self, run_id: str, run: dict[str, Any],
    ) -> dict[str, Any]:
        """Return live, non-persistent liveness data for an active desktop run."""
        now = dt.datetime.now(dt.timezone.utc)

        def age_seconds(value: Any) -> float | None:
            if not isinstance(value, str) or not value:
                return None
            try:
                parsed = dt.datetime.fromisoformat(value)
            except ValueError:
                return None
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=dt.timezone.utc)
            return max(0.0, (now - parsed).total_seconds())

        process = self._processes.get(run_id)
        process_alive = process is not None and process.poll() is None
        resources = self._live_process_resources(run_id, process)
        log_path = self.project.runs_dir / run_id / "run.log"
        log_bytes = 0
        last_output_at = ""
        last_output_age_seconds: float | None = None
        try:
            stat = log_path.stat()
            log_bytes = stat.st_size
            modified = dt.datetime.fromtimestamp(stat.st_mtime, dt.timezone.utc)
            last_output_at = modified.isoformat()
            last_output_age_seconds = max(0.0, (now - modified).total_seconds())
        except OSError:
            pass
        started_age = age_seconds(run.get("started_at") or run.get("created_at"))
        stage_age = age_seconds(
            run.get("stage_started_at") or run.get("started_at")
            or run.get("created_at")
        )
        return {
            "process_alive": process_alive,
            "elapsed_seconds": round(started_age or 0.0, 1),
            "stage_elapsed_seconds": round(stage_age or 0.0, 1),
            "log_bytes": log_bytes,
            "last_output_at": last_output_at,
            "last_output_age_seconds": (
                round(last_output_age_seconds, 1)
                if last_output_age_seconds is not None else None
            ),
            **resources,
        }

    def _live_process_resources(
        self, run_id: str, process: subprocess.Popen[Any] | None,
    ) -> dict[str, Any]:
        """Sample the owned tool process tree without blocking dashboard polls."""
        empty = {"cpu_percent": 0.0, "rss_bytes": 0, "process_count": 0}
        pid = getattr(process, "pid", None)
        if type(pid) is not int or pid <= 1 or process.poll() is not None:
            self._resource_samples.pop(run_id, None)
            return empty
        try:
            parent = psutil.Process(pid)
            processes = [parent, *parent.children(recursive=True)]
            cpu_seconds = 0.0
            rss_bytes = 0
            count = 0
            for owned in processes:
                try:
                    times = owned.cpu_times()
                    cpu_seconds += float(times.user) + float(times.system)
                    rss_bytes += int(owned.memory_info().rss)
                    count += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            self._resource_samples.pop(run_id, None)
            return empty
        sampled_at = time.monotonic()
        previous = self._resource_samples.get(run_id)
        self._resource_samples[run_id] = (sampled_at, cpu_seconds)
        cpu_percent = 0.0
        if previous is not None and sampled_at > previous[0]:
            cpu_percent = max(
                0.0,
                100.0 * (cpu_seconds - previous[1]) / (sampled_at - previous[0]),
            )
        return {
            "cpu_percent": round(cpu_percent, 1),
            "rss_bytes": rss_bytes,
            "process_count": count,
        }

    def list_runs(self) -> list[dict[str, Any]]:
        runs = []
        for path in self.project.runs_dir.glob("*/run.json"):
            try:
                run = self.get_run(path.parent.name)
                # Full deterministic command evidence includes the complete
                # tool log.  The workbench polls this list every two seconds,
                # so returning it here made one physical run add hundreds of
                # kilobytes to every refresh.  Logs remain available through
                # /log, and the full record remains available through /runs/id
                # and the evidence bundle.
                run.pop("command_evidence", None)
                runs.append(run)
            except WorkbenchError:
                continue
        runs.sort(
            key=lambda item: (str(item.get("created_at", "")), str(item.get("id", ""))),
            reverse=True,
        )
        return runs

    def run_log(self, run_id: str) -> str:
        self.get_run(run_id)
        path = self.project.runs_dir / run_id / "run.log"
        return path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""

    def _evidence_snapshot_paths(
        self, run: dict[str, Any], commit: str,
    ) -> tuple[list[str], str]:
        declared = run.get("snapshot_paths")
        authority = "run-record"
        if not isinstance(declared, list) or not all(
            isinstance(path, str) for path in declared
        ):
            declared = []
            authority = "unavailable"

        tree = self.project._git(
            "-c", "core.quotePath=false", "ls-tree", "-r", "-z",
            "--name-only", commit, check=False,
        )
        if tree.returncode != 0:
            raise WorkbenchError("固定快照已不可读取，无法导出输入证据")
        available = {path for path in tree.stdout.split("\0") if path}
        if run.get("kind") == "physical" and "spec/design.csir.yaml" in available:
            spec_bytes = self.project._commit_bytes(commit, "spec/design.csir.yaml")
            try:
                spec = yaml.safe_load(spec_bytes) if spec_bytes is not None else None
            except yaml.YAMLError as exc:
                raise WorkbenchError("固定快照的规格无法读取，不能导出完整物理输入") from exc
            if isinstance(spec, dict) and spec.get("status") == "frozen":
                sources = spec.get("acceptance_sources", [])
                if not isinstance(sources, list) or not all(
                    isinstance(path, str) for path in sources
                ):
                    raise WorkbenchError("固定快照的验收输入清单无效")
                missing = sorted(set(sources) - available)
                if missing:
                    raise WorkbenchError(
                        "固定快照缺少冻结验收输入：" + "、".join(missing[:5])
                    )
                declared = [*declared, *sources]
        metadata = {
            path for path in available
            if (
                ("/" not in path and path.endswith(".cnprj"))
                or path == "workbench.yaml"
                or path in {
                    "spec/design.csir.yaml", "ip/nebula.lock.json",
                    "integration/nebula-assembly.json",
                }
            )
        }
        paths = sorted(set(declared) | metadata)
        safe: list[str] = []
        for relative in paths:
            candidate = PurePosixPath(relative.replace("\\", "/"))
            if (
                candidate.is_absolute() or ".." in candidate.parts
                or candidate.as_posix() in {"", "."}
            ):
                raise WorkbenchError(f"固定快照输入路径不安全：{relative}")
            if candidate.as_posix() in available:
                safe.append(candidate.as_posix())
        return safe, authority

    @staticmethod
    def _evidence_reproduction_files(
        run: dict[str, Any], input_complete: bool,
    ) -> tuple[bytes, bytes | None, list[str]]:
        commands: list[str] = []
        workdir = "."
        if run.get("kind") == "physical":
            profile = run.get("physical_profile") or {}
            command = str(profile.get("command", "")).replace(
                "{mode}", str(run.get("mode") or "all")
            ).strip()
            workdir = str(profile.get("workdir", ".") or ".")
            if command:
                commands.append(command)
        else:
            for item in run.get("reproduction_commands") or []:
                if isinstance(item, dict) and str(item.get("command", "")).strip():
                    commands.append(str(item["command"]).strip())

        work_path = PurePosixPath(workdir.replace("\\", "/"))
        if work_path.is_absolute() or ".." in work_path.parts:
            commands = []
        script: bytes | None = None
        if input_complete and commands:
            directory = (
                '"$project_root"' if work_path.as_posix() in {"", "."}
                else '"$project_root"/' + shlex.quote(work_path.as_posix())
            )
            environment_check = ""
            if run.get("kind") == "physical":
                profile = run.get("physical_profile") or {}
                output_root = PurePosixPath(
                    str(profile.get("output_root", "build/rtl-to-gds"))
                    .replace("\\", "/")
                )
                if (
                    output_root.is_absolute() or ".." in output_root.parts
                    or output_root.as_posix() in {"", "."}
                ):
                    commands = []
                    output_expression = '"$project_root"/build/rtl-to-gds'
                else:
                    output_expression = (
                        '"$project_root"/' + shlex.quote(output_root.as_posix())
                    )
                flow_variant = str(profile.get("flow_variant", "nebula") or "nebula")
                try:
                    num_cores = max(1, int(profile.get("num_cores", 2)))
                except (TypeError, ValueError):
                    num_cores = 2
                environment_check = (
                    ': "${CHIP_NEBULA_RTL2GDS_TOOL_ROOT:?请设置已安装工具链目录 '
                    '(包含 bin/ 与 OpenROAD-flow-scripts/)}"\n'
                    ': "${ORFS_ROOT:?请设置固定版本的 OpenROAD-flow-scripts 目录}"\n'
                    'export CHIP_NEBULA_RTL2GDS_TOOL_ROOT ORFS_ROOT\n'
                    f"export CHIP_NEBULA_RTL2GDS_WORK_ROOT={output_expression}\n"
                    f"export FLOW_VARIANT={shlex.quote(flow_variant)}\n"
                    f"export NUM_CORES={num_cores}\n"
                )
            script = (
                "#!/usr/bin/env bash\n"
                "set -euo pipefail\n"
                'bundle_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"\n'
                'project_root="$bundle_root/inputs"\n'
                + environment_check
                + f"cd -- {directory}\n"
                + "\n".join(commands) + "\n"
            ).encode("utf-8")

        versions = json.dumps(
            run.get("tool_versions", {}), ensure_ascii=False,
            indent=2, sort_keys=True,
        )
        platform_inputs = json.dumps(
            run.get("platform_inputs", {}), ensure_ascii=False,
            indent=2, sort_keys=True,
        )
        command_text = "\n".join(f"- `{command}`" for command in commands) or "- 无可移植命令记录"
        physical_environment = ""
        if run.get("kind") == "physical":
            physical_environment = (
                "## 外部物理工具\n\n"
                "证据包包含全部工程输入，但不复制 EDA 工具和 PDK。请先安装清单中"
                "记录的版本，并显式指定以下两个目录：\n\n"
                "```bash\n"
                "export CHIP_NEBULA_RTL2GDS_TOOL_ROOT=/path/to/rtl2gds-tools\n"
                "export ORFS_ROOT=/path/to/OpenROAD-flow-scripts\n"
                "bash reproduce.sh\n"
                "```\n\n"
                "`reproduce.sh` 会在执行工程脚本前检查这两个变量；工程根固定为"
                "证据包内的 `inputs/`。\n\n"
            )
        readme = (
            "# Chip Nebula 运行复现\n\n"
            "固定快照的构建输入位于 `inputs/`，每个文件的大小和 SHA-256 "
            "记录在 `evidence-manifest.json`。\n\n"
            f"输入清单完整：`{'是' if input_complete else '否'}`\n\n"
            "安装清单中记录的工具版本和对应平台/PDK 文件后，在本目录执行 "
            "`bash reproduce.sh`。外部工具和 PDK 不复制进证据包。\n\n"
            f"{physical_environment}"
            "## 运行命令\n\n"
            f"{command_text}\n\n"
            "## 工具版本\n\n```json\n"
            f"{versions}\n```\n\n"
            "## 平台输入摘要\n\n```json\n"
            f"{platform_inputs}\n```\n"
        ).encode("utf-8")
        return readme, script, commands

    def evidence_bundle(self, run_id: str) -> Path:
        """Build a portable, deterministic archive for one completed run."""
        current_view = self.get_run(run_id)
        if current_view.get("status") in {"starting", "running"}:
            raise WorkbenchConflict("运行尚未结束，不能导出不完整的证据包")

        run_dir = (self.project.runs_dir / run_id).resolve()
        run_record = run_dir / "run.json"
        if not run_record.is_file():
            raise WorkbenchError("run record is missing")
        # Evidence describes what actually happened for the archived input,
        # so keep the persisted verdict even when the current project view
        # marks that result stale after source or constraint changes.
        run = json.loads(run_record.read_text(encoding="utf-8"))

        snapshot = run.get("snapshot") or {}
        snapshot_commit = str(snapshot.get("commit", ""))
        snapshot_paths: list[str] = []
        snapshot_authority = "unavailable"
        if snapshot_commit:
            snapshot_paths, snapshot_authority = self._evidence_snapshot_paths(
                run, snapshot_commit,
            )
        input_complete = bool(snapshot_commit and snapshot_paths) and (
            snapshot_authority != "unavailable"
        )
        reproduce_readme, reproduce_script, reproduce_commands = (
            self._evidence_reproduction_files(run, input_complete)
        )

        payloads: list[tuple[str, Path | None, bytes | None, str]] = [
            ("REPRODUCE.md", None, reproduce_readme, ""),
            ("run.json", run_record, None, ""),
            (
                "run.log",
                run_dir / "run.log" if (run_dir / "run.log").is_file() else None,
                None, "",
            ),
        ]
        if reproduce_script is not None:
            payloads.append(("reproduce.sh", None, reproduce_script, ""))
        for relative in snapshot_paths:
            data = self.project._commit_bytes(snapshot_commit, relative)
            if data is None:
                raise WorkbenchError(f"固定快照缺少已登记输入：{relative}")
            payloads.append((f"inputs/{relative}", None, data, relative))
        artifacts_dir = run_dir / "artifacts"
        if artifacts_dir.is_dir():
            resolved_artifacts = artifacts_dir.resolve()
            for path in sorted(artifacts_dir.rglob("*")):
                if path.is_symlink() or not path.is_file():
                    continue
                resolved = path.resolve()
                if resolved_artifacts not in resolved.parents:
                    raise WorkbenchError("artifact path escapes the run archive")
                relative = path.relative_to(run_dir).as_posix()
                payloads.append((relative, path, None, ""))

        destination = run_dir / f"{run_id}-evidence.zip"
        temporary = run_dir / f".{run_id}-evidence-{uuid.uuid4().hex}.tmp"
        try:
            with zipfile.ZipFile(
                temporary, "w", compression=zipfile.ZIP_DEFLATED,
                compresslevel=6, allowZip64=True,
            ) as archive:
                files: list[dict[str, Any]] = []
                snapshot_inputs: list[dict[str, Any]] = []
                for name, source, data, source_path in sorted(payloads):
                    item = self._write_evidence_member(
                        archive, name, source, data=data,
                    )
                    files.append(item)
                    if source_path:
                        snapshot_inputs.append({
                            "path": source_path,
                            "archive_path": item["path"],
                            "size": item["size"],
                            "sha256": item["sha256"],
                        })
                manifest = {
                    "format": "chip-nebula-run-evidence",
                    "format_version": 2,
                    "run": {
                        "id": run.get("id", run_id),
                        "kind": run.get("kind", ""),
                        "status": run.get("status", ""),
                        "verdict": run.get("verdict", ""),
                        "created_at": run.get("created_at", ""),
                        "started_at": run.get("started_at", ""),
                        "finished_at": run.get("finished_at", ""),
                    },
                    "snapshot": {
                        **snapshot,
                        "input_authority": snapshot_authority,
                        "inputs_complete": input_complete,
                        "inputs": snapshot_inputs,
                    },
                    "input_fingerprint": run.get("input_fingerprint", ""),
                    "input_digests": run.get("input_digests", []),
                    "tool_versions": run.get("tool_versions", {}),
                    "evidence_digest": run.get("evidence_digest", ""),
                    "reproduction": {
                        "available": reproduce_script is not None,
                        "entrypoint": "bash reproduce.sh" if reproduce_script else "",
                        "commands": reproduce_commands,
                        "external_tools_included": False,
                        "platform_inputs": run.get("platform_inputs", {}),
                    },
                    "files": files,
                }
                manifest_bytes = (
                    json.dumps(
                        manifest, ensure_ascii=False, indent=2, sort_keys=True,
                    ) + "\n"
                ).encode("utf-8")
                self._write_evidence_member(
                    archive, "evidence-manifest.json", None,
                    data=manifest_bytes,
                )
            temporary.replace(destination)
        finally:
            temporary.unlink(missing_ok=True)
        return destination

    @staticmethod
    def _write_evidence_member(
        archive: zipfile.ZipFile, name: str, source: Path | None,
        *, data: bytes | None = None,
    ) -> dict[str, Any]:
        """Stream one member into a ZIP while calculating its content identity."""
        info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.create_system = 3
        info.external_attr = 0o100644 << 16
        digest = hashlib.sha256()
        size = 0
        with archive.open(info, "w", force_zip64=True) as target:
            if data is not None:
                target.write(data)
                digest.update(data)
                size = len(data)
            elif source is not None:
                with source.open("rb") as handle:
                    for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                        target.write(chunk)
                        digest.update(chunk)
                        size += len(chunk)
        return {"path": name, "size": size, "sha256": digest.hexdigest()}

    def stop(self, run_id: str) -> bool:
        with self._lock:
            proc = self._processes.get(run_id)
            run = self.get_run(run_id)
            physical_starting = (
                run.get("kind") == "physical"
                and run.get("status") in {"starting", "running"}
            )
            checker_starting = (
                run.get("kind") == "checker_review"
                and run.get("status") in {"starting", "running"}
            )
            if not physical_starting and not checker_starting and (proc is None or proc.poll() is not None):
                return False
            if physical_starting:
                self._stop_requests.add(run_id)
            if checker_starting:
                self._checker_review_stop_events.get(run_id, threading.Event()).set()
            run.update({
                "status": "stopped", "verdict": "stopped",
                "finished_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            })
            self._write_run(run)
        if proc is not None and proc.poll() is None:
            RunManager._kill_process_group(proc)
        # The physical worker archives partial evidence after the tool exits.
        # Let it finish before a short-lived caller can exit with the only
        # copy still in the temporary worktree.
        worker = self._threads.get(run_id)
        if (
            run.get("kind") in {"physical", "checker_review"} and worker is not None
            and worker is not threading.current_thread()
        ):
            worker.join(timeout=30)
        return True

    def stop_agent(self, operation_id: str) -> bool:
        with self._lock:
            if operation_id != self._agent_operation:
                return False
            stop_event = self._agent_stop_events.get(operation_id)
            if stop_event is not None:
                stop_event.set()
            pool = self._agent_pool
            validation_run = self._agent_validation_runs.get(operation_id, "")
        operation = self.project.operation(operation_id)
        from chip_nebula.adapters.base import session_registry
        stage = (
            "specification" if operation.get("stage") == "specification"
            else "rtl-generation" if operation.get("stage") == "rtl_generation"
            else "rtl-repair" if operation.get("stage") == "rtl_repair"
            else "acceptance-generation" if operation.get("stage") == "acceptance_generation"
            else "rtl-edit"
        )
        session_id = session_registry.get("workbench", stage) or ""
        if pool is not None and session_id:
            pool.terminate(session_id)
        if validation_run:
            self.stop(validation_run)
        return True

    def stop_all(self) -> None:
        """Stop live tool and Agent work before the desktop backend exits."""
        run_ids = set(self._processes) | {
            identifier for identifier in self._threads
            if (self.project.runs_dir / identifier / "run.json").is_file()
        }
        for run_id in run_ids:
            self.stop(run_id)
        self.stop_viewers()
        with self._lock:
            operation_id = self._agent_operation
        if operation_id:
            self.stop_agent(operation_id)
        for record in self.list_assistant_sessions():
            if record.get("status") in {"starting", "running"}:
                self.stop_assistant(str(record["id"]))
        for thread in list(self._threads.values()):
            if thread.is_alive():
                thread.join(timeout=5)

    def _register_viewer(self, process: subprocess.Popen[Any]) -> None:
        """Track a native viewer owned by this desktop backend."""
        pid = getattr(process, "pid", None)
        if type(pid) is not int or pid <= 1 or process.poll() is not None:
            return
        with self._lock:
            self._viewer_processes = {
                viewer_pid: viewer
                for viewer_pid, viewer in self._viewer_processes.items()
                if viewer.poll() is None
            }
            self._viewer_processes[pid] = process

    def stop_viewers(self) -> None:
        """Stop GTKWave/KLayout processes launched by this desktop session."""
        with self._lock:
            viewers = list(self._viewer_processes.values())
            self._viewer_processes.clear()
        for process in viewers:
            if process.poll() is None:
                RunManager._kill_process_group(process)

    def viewer_status(self, viewer_id: int) -> dict[str, Any]:
        """Report whether a native viewer survived its asynchronous startup."""
        with self._lock:
            process = self._viewer_processes.get(viewer_id)
        if process is None:
            raise WorkbenchError("viewer is not owned by this desktop session")
        returncode = process.poll()
        if returncode is None:
            return {"viewer_id": viewer_id, "status": "running"}
        try:
            _, stderr = process.communicate(timeout=0.25)
        except (OSError, subprocess.TimeoutExpired):
            stderr = ""
        with self._lock:
            if self._viewer_processes.get(viewer_id) is process:
                self._viewer_processes.pop(viewer_id, None)
        lines = (stderr or "").strip().splitlines()
        return {
            "viewer_id": viewer_id,
            "status": "exited",
            "returncode": returncode,
            "detail": lines[-1] if lines else "没有诊断输出",
        }

    def file_locked(self, relative: str) -> bool:
        """Whether the active live Agent owns this path's editor lock."""
        with self._lock:
            operation_id = self._agent_operation
        if not operation_id:
            return False
        operation = self.project.operation(operation_id)
        return not violations([relative], operation.get("write_paths", []))

    def launch_waveform(self, run_id: str, relative: str) -> None:
        run = self.get_run(run_id)
        artifact = next((item for item in run.get("artifacts", []) if item.get("path") == relative and item.get("kind") == "waveform"), None)
        if artifact is None:
            raise WorkbenchError("waveform is not registered for this run")
        viewer = shutil.which("gtkwave")
        if not viewer:
            raise WorkbenchError("GTKWave is not installed")
        path = (self.project.runs_dir / run_id / "artifacts" / relative).resolve()
        process = subprocess.Popen(
            [viewer, str(path)], stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        self._register_viewer(process)

    def read_artifact(self, run_id: str, relative: str) -> dict[str, Any]:
        run = self.get_run(run_id)
        artifact = next(
            (item for item in run.get("artifacts", []) if item.get("path") == relative),
            None,
        )
        if artifact is None:
            raise WorkbenchError("artifact is not registered for this run")
        base = (self.project.runs_dir / run_id / "artifacts").resolve()
        path = (base / relative).resolve()
        if base not in path.parents or not path.is_file():
            raise WorkbenchError("artifact not found")
        if path.stat().st_size > _ARTIFACT_TEXT_PREVIEW_LIMIT:
            raise WorkbenchError(
                "文本产物超过 8 MiB，无法在工作台中安全预览；"
                "请下载后使用本地编辑器查看"
            )
        if path.suffix.lower() not in {
            ".v", ".sv", ".vh", ".svh", ".sdc", ".def", ".spef",
            ".rpt", ".log", ".json", ".txt", ".tcl", ".mk", ".eqy",
        }:
            raise WorkbenchError("artifact is not a text document")
        return {
            "path": relative,
            "content": path.read_text(encoding="utf-8", errors="replace"),
            "version": hashlib.sha256(path.read_bytes()).hexdigest(),
            "read_only": True,
            "run_id": run_id,
            "kind": artifact.get("kind", "report"),
        }

    def launch_layout(self, run_id: str, relative: str) -> dict[str, Any]:
        run = self.get_run(run_id)
        artifact = next(
            (
                item for item in run.get("artifacts", [])
                if item.get("path") == relative and item.get("kind") == "layout"
            ),
            None,
        )
        if artifact is None:
            raise WorkbenchError("GDSII is not registered for this run")
        base = (self.project.runs_dir / run_id / "artifacts").resolve()
        path = (base / relative).resolve()
        if base not in path.parents or not path.is_file():
            raise WorkbenchError("GDSII artifact not found")
        try:
            config = PhysicalFlowConfig.from_document(
                run.get("physical_profile", {})
            )
            args, environment = PhysicalFlow(
                self.project.root, config
            ).layout_launch(path)
            process = subprocess.Popen(
                args, env=environment, stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                text=True, start_new_session=True,
            )
            deadline = time.monotonic() + 0.75
            while time.monotonic() < deadline:
                returncode = process.poll()
                if isinstance(returncode, int):
                    _, stderr = process.communicate(timeout=0.25)
                    detail = (stderr or "没有诊断输出").strip().splitlines()[-1]
                    raise WorkbenchError(
                        f"KLayout 未能保持运行（退出码 {returncode}）：{detail}"
                    )
                time.sleep(0.05)
            self._register_viewer(process)
            pid = getattr(process, "pid", None)
            return {
                "viewer_id": pid if type(pid) is int and pid > 1 else None,
                "status": "running",
            }
        except (OSError, PhysicalFlowError) as exc:
            raise WorkbenchError(f"failed to launch KLayout: {exc}") from exc

    def _execute_validation(
        self, run_id: str, commit: str, commands: list[tuple[str, str]],
        config: WorkbenchConfig, environment: dict[str, str],
    ) -> None:
        run_dir = self.project.runs_dir / run_id
        workspace = self.project.workspaces_dir / run_id
        log_path = run_dir / "run.log"
        run = self.get_run(run_id)
        log_handle: Any | None = None
        run.update({"status": "running", "verdict": "running", "started_at": dt.datetime.now(dt.timezone.utc).isoformat()})
        self._write_run(run)
        try:
            self.project._git("worktree", "add", "--detach", str(workspace), commit)
            self._prepare_validation_output_directories(workspace, config)
            if run.get("acceptance_contract", {}).get("valid"):
                frozen_contract = run["acceptance_contract"].get("contract", {})
                verify_assembly_source_hashes(workspace, frozen_contract)
                if run.get("elaboration_ast_format"):
                    (workspace / Path(ast_artifact_path(run["elaboration_ast_format"])).parent).mkdir(
                        parents=True, exist_ok=True,
                    )
            acceptance = run.get("acceptance_plan", {})
            check_ids_by_kind: dict[str, list[str]] = {}
            for check in acceptance.get("checks", []):
                if isinstance(check, dict) and check.get("status") != "planned":
                    check_ids_by_kind.setdefault(str(check.get("kind", "")), []).append(str(check.get("id", "")))
            regression_commands = []
            for name, command in commands:
                ids = check_ids_by_kind.get(name, [])
                if name == "simulation":
                    ids = list(dict.fromkeys([
                        *ids,
                        *check_ids_by_kind.get("elaboration", []),
                    ]))
                regression_commands.append(RegressionCommand(
                    name=name,
                    command=command,
                    acceptance_ids=tuple(item for item in ids if item),
                    cwd=config.workdir,
                    timeout=config.timeout,
                    success_pattern=config.success_pattern if name == "simulation" else "",
                    success_evidence=(
                        config.success_evidence if name == "simulation" else {}
                    ),
                    environment=environment,
                ))

            def process_changed(process: subprocess.Popen[str] | None) -> None:
                with self._lock:
                    if process is None:
                        self._processes.pop(run_id, None)
                        self._resource_samples.pop(run_id, None)
                    else:
                        self._processes[run_id] = process

            log_path.parent.mkdir(parents=True, exist_ok=True)
            log_handle = log_path.open("w", encoding="utf-8")
            for name, command in commands:
                log_handle.write(f"$ [{name}] {command}\n")
            log_handle.flush()

            def log_changed(chunk: str) -> None:
                if log_handle is not None:
                    log_handle.write(chunk)
                    log_handle.flush()

            evidence = YASimulator().run(
                workspace,
                regression_commands,
                spec_digest=str(run["spec_digest"]),
                acceptance_plan=acceptance,
                input_digests=run.get("input_digests", []),
                process_callback=process_changed,
                log_callback=log_changed,
            )
            log_handle.close()
            log_handle = None
            log_path.write_text(evidence.pop("log"), encoding="utf-8")
            if run.get("acceptance_contract", {}).get("valid") and run.get("elaboration_ast_format"):
                frozen_spec = SpecificationWorkspace(workspace).state()
                port_contract = inspect_elaboration(
                    workspace / ast_artifact_path(run["elaboration_ast_format"]), frozen_spec,
                    parameters=config.top_parameters,
                )
                run["port_contract"] = port_contract
                if (
                    port_contract["verdict"] != "passed"
                    and evidence["status"] not in {"stopped", "timeout", "launch_failed"}
                ):
                    evidence["verdict"] = "failed"
                    for check in evidence.get("checks", []):
                        if check["id"] in run["acceptance_contract"].get("elaboration_ids", []):
                            check["verdict"] = "failed"
                            check["evidence"] = "；".join(port_contract["diagnostics"])
                    evidence["requirements"] = YASimulator._requirements(
                        acceptance, evidence.get("checks", []),
                    )
                evidence["evidence_digest"] = "sha256:" + hashlib.sha256(
                    json.dumps({
                        "regression": evidence["evidence_digest"],
                        "port_contract": port_contract,
                    }, ensure_ascii=False, sort_keys=True).encode("utf-8")
                ).hexdigest()
            artifacts = self._archive_outputs(workspace, run_dir / "artifacts", config)
            ast_relative = ast_artifact_path(run.get("elaboration_ast_format", ""))
            ast = workspace / ast_relative
            if ast.is_file() and run.get("acceptance_contract", {}).get("valid"):
                target = run_dir / "artifacts" / ast_relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ast, target)
                artifacts.append({
                    "path": ast_relative, "kind": "report",
                    "size": target.stat().st_size,
                    "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                })
            output = self._diagnostic_text(run_dir, artifacts)
            returncode = (
                evidence["commands"][-1].get("returncode")
                if evidence.get("commands") else None
            )
            run.update({
                "status": (
                    "finished" if evidence["status"] in {"succeeded", "failed"}
                    else evidence["status"]
                ),
                "verdict": evidence["verdict"], "returncode": returncode,
                "artifacts": artifacts,
                "errors": [
                    asdict(item) for item in _normalize_task_error_paths(
                        parse_errors(output), workspace, config.workdir,
                    )
                ],
                "tool_versions": {
                    **run.get("tool_versions", {}),
                    **evidence["tool_versions"],
                },
                "checks": evidence["checks"],
                "requirements": evidence["requirements"],
                "evidence_digest": evidence["evidence_digest"],
                "command_evidence": evidence["commands"],
                "finished_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            })
        except Exception as exc:
            run.update({"status": "failed_to_start", "verdict": "not_started", "error": str(exc)})
        finally:
            if log_handle is not None:
                log_handle.close()
            self._processes.pop(run_id, None)
            self._resource_samples.pop(run_id, None)
            if workspace.exists():
                self.project._git("worktree", "remove", "--force", str(workspace), check=False)
                self.project._git("worktree", "prune", check=False)
            existing_path = run_dir / "run.json"
            if existing_path.is_file():
                existing = json.loads(existing_path.read_text(encoding="utf-8"))
                if existing.get("status") == "stopped":
                    run.update({
                        "status": "stopped", "verdict": "stopped",
                        "finished_at": existing.get("finished_at")
                        or dt.datetime.now(dt.timezone.utc).isoformat(),
                    })
            self._write_run(run)

    @staticmethod
    def _prepare_validation_output_directories(
        workspace: Path, config: WorkbenchConfig,
    ) -> None:
        """Create declared artifact roots omitted from immutable snapshots."""
        resolved_workspace = workspace.resolve()
        roots = {
            root
            for pattern in [*config.report_globs, *config.waveform_globs]
            if (root := _literal_glob_root(pattern)) is not None
        }
        for relative in sorted(roots, key=lambda item: item.as_posix()):
            target = (workspace / relative).resolve()
            if target != resolved_workspace and resolved_workspace not in target.parents:
                raise WorkbenchError(f"artifact output path escapes workspace: {relative}")
            target.mkdir(parents=True, exist_ok=True)

    def _execute_physical(
        self, run_id: str, commit: str, mode: str,
        workbench_config: WorkbenchConfig,
    ) -> None:
        config = workbench_config.physical
        run_dir = self.project.runs_dir / run_id
        workspace = self.project.workspaces_dir / run_id
        log_path = run_dir / "run.log"
        with self._lock:
            run = self.get_run(run_id)
            if run_id not in self._stop_requests:
                started_at = dt.datetime.now(dt.timezone.utc).isoformat()
                run.update({
                    "status": "running", "verdict": "running",
                    "started_at": started_at, "stage_started_at": started_at,
                })
                run["physical_stages"][0]["status"] = (
                    "running" if mode == "all" else "skipped"
                )
                run["current_stage"] = "simulation" if mode == "all" else "synthesis"
                self._write_run(run)
        flow = PhysicalFlow(self.project.root, config)
        log_handle: Any | None = None
        try:
            self.project._git("worktree", "add", "--detach", str(workspace), commit)
            # The physical wrapper runs the project's functional validation
            # first.  Its declared reports and waveforms may live below build
            # directories that are intentionally absent from the immutable
            # Git snapshot, so create the same safe output roots used by a
            # standalone validation run before invoking the wrapper.
            self._prepare_validation_output_directories(
                workspace, workbench_config,
            )
            snapshot_audit = flow.audit_inputs(workspace)
            with self._lock:
                run = self.get_run(run_id)
                run["snapshot_input_audit"] = snapshot_audit
                self._write_run(run)
            if not snapshot_audit["ready"]:
                raise WorkbenchError(
                    "固定快照输入不完整：" + "；".join(
                        item["message"] for item in snapshot_audit["issues"]
                    )
                )
            command, environment = flow.execution_command(workspace, mode)
            with self._lock:
                if run_id in self._stop_requests:
                    raise WorkbenchError("physical run stopped before tool launch")
            log_path.parent.mkdir(parents=True, exist_ok=True)
            log_handle = log_path.open("w", encoding="utf-8")
            log_handle.write(f"$ [rtl-to-gds] {command}\n")
            log_handle.flush()

            def process_changed(process: subprocess.Popen[str] | None) -> None:
                with self._lock:
                    if process is None:
                        self._processes.pop(run_id, None)
                        self._resource_samples.pop(run_id, None)
                    else:
                        self._processes[run_id] = process
                    stopping = run_id in self._stop_requests
                if process is not None and stopping and process.poll() is None:
                    RunManager._kill_process_group(process)

            def log_changed(chunk: str) -> None:
                if log_handle is not None:
                    log_handle.write(chunk)
                    log_handle.flush()
                self._advance_physical_progress(run_id, chunk)

            result = DeterministicToolExecutor(
                process_callback=process_changed, log_callback=log_changed,
            ).execute(
                workspace,
                [ToolCommand(
                    "rtl-to-gds", command, cwd=config.workdir,
                    timeout=config.timeout,
                )],
            )
            if log_handle is not None:
                log_handle.close()
                log_handle = None
            # Replace the incremental log with the canonical executor evidence.
            log_path.write_text(result.log, encoding="utf-8")
            artifacts = self._archive_physical_outputs(
                flow, workspace, run_dir / "artifacts"
            )
            validation_artifacts = self._archive_outputs(
                workspace, run_dir / "artifacts", workbench_config,
            )
            known_artifacts = {item["path"] for item in artifacts}
            artifacts.extend(
                item for item in validation_artifacts
                if item["path"] not in known_artifacts
            )
            summary: dict[str, Any] = {}
            summary_error = ""
            try:
                summary = flow.read_summary(workspace)
            except PhysicalFlowError as exc:
                summary_error = str(exc)
            layout = next(
                (item for item in artifacts if item.get("kind") == "layout"), None
            )
            if layout and isinstance(summary.get("gds"), dict):
                summary["gds"]["path"] = layout["path"]
                summary["gds"]["artifact_path"] = layout["path"]
                self._canonicalize_archived_physical_summary(
                    artifacts,
                    run_dir / "artifacts",
                    config.summary_path,
                    summary,
                )
            physical_passed = (
                result.status == "succeeded"
                and result.verdict == "passed"
                and summary.get("status") in {"passed", "physical_passed"}
                and summary.get("detailed_routing_violations") == 0
                and summary.get("drc_violations") == 0
                and summary.get("lvs") == "matched"
                and summary.get("metrics", {}).get("setup_violations") == 0
                and summary.get("metrics", {}).get("hold_violations") == 0
                and layout is not None
                and (mode != "all" or summary.get("functional_simulation") == "passed")
            )
            verdict = "passed" if physical_passed else "failed"
            progress_run = self.get_run(run_id)
            if result.verdict != "passed":
                failure_stage = str(progress_run.get("current_stage", ""))
            elif summary_error:
                failure_stage = "evidence"
            elif mode == "all" and summary.get("functional_simulation") != "passed":
                failure_stage = "simulation"
            else:
                failure_stage = str(summary.get("failed_stage", ""))
            stages = self._completed_physical_stages(
                progress_run.get("physical_stages", []), summary, verdict, mode,
                failure_stage,
            )
            command_result = result.commands[-1] if result.commands else None
            evidence_document = {
                "summary": summary,
                "artifacts": [
                    {key: value for key, value in item.items() if key != "source"}
                    for item in artifacts
                ],
                "inputs": run.get("input_digests", []),
            }
            evidence_digest = "sha256:" + hashlib.sha256(
                json.dumps(
                    evidence_document, ensure_ascii=False, sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest()
            output = self._diagnostic_text(run_dir, artifacts)
            parsed_errors = _normalize_task_error_paths(
                parse_errors(output), workspace, config.workdir,
            )
            if (
                command_result and command_result.returncode not in {None, 0}
                and not any(
                    item.severity.upper() in {"ERROR", "FATAL"}
                    for item in parsed_errors
                )
            ):
                tool_errors = [
                    line.split("ERROR:", 1)[1].strip()
                    for line in command_result.log.splitlines()
                    if "ERROR:" in line and line.split("ERROR:", 1)[1].strip()
                ]
                if tool_errors:
                    parsed_errors.append(TaskError(
                        file="", line=0, code="PHYSICAL_TOOL_ERROR",
                        severity="ERROR", message=tool_errors[-1],
                    ))
            resource_failure = self._physical_resource_failure(command_result)
            if resource_failure and not any(
                item.code == "PHYSICAL_RESOURCE_EXHAUSTED"
                for item in parsed_errors
            ):
                parsed_errors.append(TaskError(
                    file="", line=0, code="PHYSICAL_RESOURCE_EXHAUSTED",
                    severity="ERROR", message=resource_failure["message"],
                ))
            primary_error = (
                resource_failure["message"] if resource_failure
                else self._physical_failure_reason(
                    summary, summary_error, command_result, parsed_errors,
                )
            )
            run.update({
                "status": (
                    "finished" if result.status in {"succeeded", "failed"}
                    else result.status
                ),
                "verdict": verdict if result.status in {"succeeded", "failed"}
                else result.verdict,
                "returncode": command_result.returncode if command_result else None,
                "artifacts": artifacts,
                "summary": summary,
                "error": primary_error,
                "failure_class": (
                    resource_failure["failure_class"] if resource_failure else ""
                ),
                "errors": [asdict(item) for item in parsed_errors],
                "physical_stages": stages,
                "current_stage": "complete" if physical_passed else (
                    failure_stage or "failed"
                ),
                "tool_versions": {
                    **run.get("tool_versions", {}),
                    **{
                        name: item.get("version", "")
                        for name, item in environment.get("tools", {}).items()
                        if item.get("version")
                    },
                },
                "command_evidence": [asdict(item) for item in result.commands],
                "evidence_digest": evidence_digest,
                "finished_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            })
        except Exception as exc:
            run.update({
                "status": "failed_to_start", "verdict": "not_started",
                "error": str(exc), "current_stage": "failed",
                "finished_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            })
        finally:
            if log_handle is not None:
                log_handle.close()
            self._processes.pop(run_id, None)
            self._resource_samples.pop(run_id, None)
            with self._lock:
                self._stop_requests.discard(run_id)
            if workspace.exists():
                self.project._git(
                    "worktree", "remove", "--force", str(workspace), check=False
                )
                self.project._git("worktree", "prune", check=False)
            existing_path = run_dir / "run.json"
            if existing_path.is_file():
                existing = json.loads(existing_path.read_text(encoding="utf-8"))
                if existing.get("status") == "stopped":
                    stopped_stages = [
                        dict(item) for item in existing.get(
                            "physical_stages", run.get("physical_stages", [])
                        )
                    ]
                    for item in stopped_stages:
                        if item.get("status") == "running":
                            item["status"] = "stopped"
                    run.update({
                        "status": "stopped", "verdict": "stopped",
                        "current_stage": "stopped",
                        "physical_stages": stopped_stages,
                        "finished_at": existing.get("finished_at")
                        or dt.datetime.now(dt.timezone.utc).isoformat(),
                    })
            self._write_run(run)

    @staticmethod
    def _physical_resource_failure(command_result: Any | None) -> dict[str, str] | None:
        """Recognize a nested EDA process killed because resources ran out.

        Make-based flows commonly return ``2`` even when the actual DRC or LVS
        child was killed with status 137.  Keep that distinction visible so a
        missing summary cannot hide an incomplete signoff as an evidence-file
        problem.
        """
        if command_result is None:
            return None
        log = str(getattr(command_result, "log", ""))
        lowered = log.lower()
        explicit_oom = any(marker in lowered for marker in (
            "out of memory", "oom-kill", "oom_kill", "cannot allocate memory",
        ))
        killed_137 = (
            "killed" in lowered
            and re.search(r"(?:error|exit(?:ed)?(?:\s+with)?|status)\s*137\b", lowered)
            is not None
        )
        if not explicit_oom and not killed_137:
            return None

        if re.search(r"(?:6_drc\.log|\.lydrc\b|drc[^\n]*klayout|klayout[^\n]*drc)", log, re.I):
            step = "KLayout DRC"
            incomplete = "DRC 未完成，LVS 未执行"
        elif re.search(r"(?:6_lvs\.log|lvs[^\n]*klayout|klayout[^\n]*lvs)", log, re.I):
            step = "KLayout LVS"
            incomplete = "LVS 未完成"
        else:
            step = "物理实现工具"
            incomplete = "当前阶段未完成"

        memory = re.findall(
            r"Peak memory:\s*([0-9]+(?:\.[0-9]+)?)\s*(KB|MB|GB)\b",
            log, re.I,
        )
        memory_detail = ""
        if memory:
            value, unit = memory[-1]
            amount = float(value)
            multiplier = {"KB": 1 / (1024 * 1024), "MB": 1 / 1024, "GB": 1}[unit.upper()]
            memory_detail = f"，峰值内存约 {amount * multiplier:.2f} GiB"
        cause = "检测到内存耗尽" if explicit_oom else "通常表示可用内存不足"
        return {
            "failure_class": "resource_exhausted",
            "message": (
                f"{step} 被系统终止（子进程状态 137{memory_detail}，{cause}）；"
                f"{incomplete}。请释放内存或为该流程提高内存上限后重试"
            ),
        }

    @staticmethod
    def _physical_failure_reason(
        summary: dict[str, Any], summary_error: str,
        command_result: Any | None, parsed_errors: list[Any],
    ) -> str:
        """Prefer actionable signoff evidence over a generic exit status."""
        problems: list[str] = []
        route = summary.get("detailed_routing_violations")
        drc = summary.get("drc_violations")
        lvs = summary.get("lvs")
        metrics = summary.get("metrics", {})
        metrics = metrics if isinstance(metrics, dict) else {}
        setup = metrics.get("setup_violations")
        hold = metrics.get("hold_violations")
        if isinstance(route, (int, float)) and route != 0:
            problems.append(f"详细布线违规 {route:g} 项")
        if isinstance(drc, (int, float)) and drc != 0:
            problems.append(f"DRC 违规 {drc:g} 项")
        if lvs and lvs != "matched":
            problems.append("LVS 网表不匹配")
        if (
            isinstance(setup, (int, float)) and setup != 0
            or isinstance(hold, (int, float)) and hold != 0
        ):
            timing = f"时序未收敛：setup 违例 {setup}，hold 违例 {hold}"
            setup_slack = metrics.get("setup_slack_ns")
            hold_slack = metrics.get("hold_slack_ns")
            fmax = metrics.get("estimated_fmax_hz")
            details: list[str] = []
            if isinstance(setup_slack, (int, float)):
                details.append(f"setup slack {setup_slack:g} ns")
            if isinstance(hold_slack, (int, float)):
                details.append(f"hold slack {hold_slack:g} ns")
            if isinstance(fmax, (int, float)):
                details.append(f"估算 Fmax {fmax / 1_000_000:g} MHz")
            problems.append(timing + ("（" + "，".join(details) + "）" if details else ""))
        if problems:
            return "；".join(problems)

        structured = summary.get("failure_reason")
        if isinstance(structured, str) and structured.strip():
            return structured.strip()
        if command_result and command_result.returncode not in {None, 0}:
            first_error = next(
                (
                    item for item in parsed_errors
                    if str(getattr(item, "severity", "")).upper() == "ERROR"
                ),
                None,
            )
            if first_error is not None:
                location = str(getattr(first_error, "file", "")).strip()
                line = getattr(first_error, "line", 0)
                if location and line:
                    location += f":{line}"
                message = str(getattr(first_error, "message", "")).strip()
                return f"{location}: {message}" if location else message
            command_log = str(getattr(command_result, "log", ""))
            tool_errors = [
                line.split("ERROR:", 1)[1].strip()
                for line in command_log.splitlines()
                if "ERROR:" in line and line.split("ERROR:", 1)[1].strip()
            ]
            if tool_errors:
                return tool_errors[-1]
        if summary_error:
            return summary_error
        return str(getattr(command_result, "reason", "") or "")

    @staticmethod
    def _physical_stages() -> list[dict[str, str]]:
        return [
            {"id": "simulation", "label": "功能仿真", "status": "pending"},
            {"id": "synthesis", "label": "逻辑综合", "status": "pending"},
            {"id": "floorplan", "label": "布局规划与 PDN", "status": "pending"},
            {"id": "placement", "label": "单元放置", "status": "pending"},
            {"id": "cts", "label": "时钟树综合", "status": "pending"},
            {"id": "routing", "label": "全局与详细布线", "status": "pending"},
            {"id": "signoff", "label": "STA / DRC / LVS / GDS", "status": "pending"},
            {"id": "evidence", "label": "摘要与证据归档", "status": "pending"},
        ]

    def _advance_physical_progress(self, run_id: str, chunk: str) -> None:
        probes = [
            ("simulation", ("CHIP_NEBULA_STAGE simulation", "functional simulation")),
            ("synthesis", (
                "CHIP_NEBULA_STAGE synthesis", "1_2_yosys",
                "Running synthesis", "synth.tcl",
            )),
            ("floorplan", ("2_1_floorplan", "floorplan.tcl", "pdn.tcl")),
            ("placement", ("3_1_place", "3_3_place", "global_place")),
            ("cts", ("4_1_cts", "cts.tcl", "clock tree")),
            ("routing", ("5_1_grt", "5_2_route", "detailed_route")),
            ("signoff", ("6_1_merge", "6_drc", "6_lvs", "RTL-to-GDS flow completed")),
        ]
        matched = ""
        lowered = chunk.lower()
        signoff_phase = ""
        if "6_lvs.log" in lowered or "writing lvs database" in lowered:
            signoff_phase = "lvs"
        elif "6_drc.log" in lowered or "drc section" in lowered:
            signoff_phase = "drc"
        elif "6_1_merge" in lowered:
            signoff_phase = "gds_merge"
        for stage, needles in probes:
            if any(needle.lower() in lowered for needle in needles):
                matched = stage
        iteration = re.search(
            r"Start\s+(\d+)(?:st|nd|rd|th)?\s+optimization iteration",
            chunk, re.IGNORECASE,
        )
        completion = re.search(
            r"Completing\s+(\d+)%\s+with\s+(\d+)\s+violations",
            chunk, re.IGNORECASE,
        )
        violation_total = re.search(
            r"Number of violations\s*=\s*(\d+)", chunk, re.IGNORECASE,
        )
        if not matched and any((iteration, completion, violation_total)):
            matched = "routing"
        if not matched and not any((iteration, completion, violation_total)):
            return
        with self._lock:
            try:
                path = self.project.runs_dir / run_id / "run.json"
                run = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                return
            stages = run.get("physical_stages", [])
            changed = False
            if matched:
                target = next(
                    (
                        index for index, item in enumerate(stages)
                        if item.get("id") == matched
                    ),
                    -1,
                )
                if target >= 0 and run.get("current_stage") != matched:
                    for index, item in enumerate(stages):
                        if item.get("status") == "skipped":
                            continue
                        if index < target:
                            item["status"] = "passed"
                        elif index == target:
                            item["status"] = "running"
                    run["current_stage"] = matched
                    run["stage_started_at"] = dt.datetime.now(
                        dt.timezone.utc
                    ).isoformat()
                    changed = True
            if any((iteration, completion, violation_total)):
                progress = dict(run.get("routing_progress") or {})
                if iteration:
                    progress.update({
                        "iteration": int(iteration.group(1)), "percent": 0,
                    })
                if completion:
                    progress.update({
                        "percent": int(completion.group(1)),
                        "violations": int(completion.group(2)),
                    })
                if violation_total:
                    progress.update({
                        "percent": 100,
                        "violations": int(violation_total.group(1)),
                    })
                run["routing_progress"] = progress
                changed = True
            if signoff_phase:
                labels = {
                    "gds_merge": "GDS 合并与最终报告",
                    "drc": "KLayout DRC 规则检查",
                    "lvs": "KLayout LVS 版图与网表匹配",
                }
                progress = {
                    "phase": signoff_phase,
                    "label": labels[signoff_phase],
                }
                if run.get("signoff_progress") != progress:
                    run["signoff_progress"] = progress
                    changed = True
            if not changed:
                return
            self._write_run(run)

    @staticmethod
    def _completed_physical_stages(
        stages: list[dict[str, str]], summary: dict[str, Any], verdict: str,
        mode: str, failure_stage: str = "",
    ) -> list[dict[str, str]]:
        completed = [dict(item) for item in stages]
        for item in completed:
            if item["id"] == "simulation" and mode == "physical":
                item["status"] = "skipped"
            elif verdict == "passed":
                item["status"] = "passed"
            elif item["id"] == failure_stage:
                item["status"] = "failed"
            elif item["status"] == "running":
                item["status"] = "pending"
        if mode == "all" and summary.get("functional_simulation") != "passed":
            simulation = next(
                (item for item in completed if item["id"] == "simulation"), None
            )
            if simulation is not None and failure_stage == "simulation":
                simulation["status"] = "failed"
        return completed

    @staticmethod
    def _archive_physical_outputs(
        flow: PhysicalFlow, workspace: Path, destination: Path,
    ) -> list[dict[str, str]]:
        destination.mkdir(parents=True, exist_ok=True)
        archived: list[dict[str, str]] = []
        for item in flow.collect_artifacts(workspace):
            source = item["source"]
            target = destination / item["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            archived.append({
                "path": item["path"], "kind": item["kind"],
                "size": item["size"], "sha256": item["sha256"],
            })
        return archived

    @staticmethod
    def _canonicalize_archived_physical_summary(
        artifacts: list[dict[str, str]], destination: Path,
        summary_path: str, summary: dict[str, Any],
    ) -> None:
        """Publish a portable summary while retaining the exact tool output."""
        item = next(
            (
                artifact for artifact in artifacts
                if artifact.get("path") == summary_path
                and artifact.get("kind") == "physical_summary"
            ),
            None,
        )
        if item is None:
            return
        target = destination / summary_path
        if not target.is_file():
            return
        relative = Path(summary_path)
        raw_relative = relative.with_name(
            f"{relative.stem}.tool{relative.suffix}"
        )
        raw_target = destination / raw_relative
        raw_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(target, raw_target)
        artifacts.append({
            "path": raw_relative.as_posix(), "kind": "report",
            "size": str(raw_target.stat().st_size),
            "sha256": _file_sha256(raw_target),
        })
        target.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        item["size"] = str(target.stat().st_size)
        item["sha256"] = _file_sha256(target)

    @staticmethod
    def _unanswered_spec_questions_removed(
        operation: dict[str, Any], spec_state: dict[str, Any],
    ) -> list[str]:
        """Reject Agent resolution of questions without a recorded user answer."""
        answered = set(operation.get("clarifications", {}))
        current = {
            str(item.get("id", index)): item
            for index, item in enumerate(
                spec_state.get("document", {}).get("open_questions", [])
            )
            if isinstance(item, dict)
        }
        return [
            str(previous["key"])
            for previous in operation.get("open_questions_before", [])
            if previous["key"] not in answered
            and (
                previous["key"] not in current
                or current[previous["key"]].get("status") == "resolved"
                or str(current[previous["key"]].get("question", ""))
                != previous["question"]
            )
        ]

    def _check_generic_acceptance(
        self, operation_id: str, attempt: int, stop_event: threading.Event,
    ) -> dict[str, Any]:
        """Self-test a separately authored checker in a fixed Git snapshot."""
        operation = self.project.operation(operation_id)
        spec = SpecificationWorkspace(self.project.root).state()
        try:
            contract = checker_contract(spec, self.project.root)
        except (GenericAcceptanceError, GenericRTLContractError) as exc:
            raise WorkbenchConflict(str(exc)) from exc
        if (
            spec.get("spec_digest") != operation.get("spec_digest")
            or contract["testbench"] != operation.get("acceptance_path")
        ):
            raise WorkbenchConflict("独立 checker 生成期间冻结 CSIR 已改变")
        snapshot = self.project.capture_snapshot(
            f"generic acceptance candidate attempt {attempt}",
        )
        evidence_dir = self.project.operations_dir / (
            f"{operation_id}-acceptance-{attempt}"
        )
        return self._verify_checker_snapshot(
            snapshot, spec, contract, evidence_dir, stop_event,
        )

    def _verify_checker_snapshot(
        self, snapshot: dict[str, str], spec: dict[str, Any],
        contract: dict[str, Any], evidence_dir: Path,
        stop_event: threading.Event,
    ) -> dict[str, Any]:
        """Archive real and mutant Icarus evidence before removing the worktree."""
        workspace = self.project.workspaces_dir / evidence_dir.name
        evidence_dir.mkdir(parents=True, exist_ok=True)
        report: dict[str, Any] = {}
        try:
            self.project._git(
                "worktree", "add", "--detach", str(workspace), snapshot["commit"],
            )
            report = verify_checker(
                workspace, spec, timeout=self.project.config().timeout,
                stop_event=stop_event, contract=contract,
            )
            mutant = workspace / "build/chip-nebula-acceptance/mutant.sv"
            if mutant.is_file():
                target = evidence_dir / "mutant.sv"
                shutil.copy2(mutant, target)
                report["mutant_sha256"] = _file_sha256(target)
        finally:
            if workspace.is_dir():
                self.project._git(
                    "worktree", "remove", "--force", str(workspace), check=False,
                )
        log = str(report.pop("log", ""))
        (evidence_dir / "run.log").write_text(log, encoding="utf-8")
        report.update({
            "snapshot": snapshot,
            "spec_digest": spec["spec_digest"],
            "evidence_dir": evidence_dir.relative_to(self.project.root).as_posix(),
        })
        (evidence_dir / "report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return report

    def _check_generic_generation(
        self, operation_id: str, attempt: int, stop_event: threading.Event,
    ) -> dict[str, Any]:
        """Elaborate one generated RTL candidate in its immutable Git snapshot."""
        operation = self.project.operation(operation_id)
        spec = SpecificationWorkspace(self.project.root).state()
        instance = str(operation.get("generation_instance", ""))
        try:
            expected_path = (
                submodule_contract(spec, instance)["source"]
                if instance else generation_target(spec)
            )
        except (GeneratedSubmoduleError, GenericRTLContractError) as exc:
            raise WorkbenchConflict(str(exc)) from exc
        if (
            not spec.get("valid") or not spec.get("frozen")
            or spec.get("spec_digest") != operation.get("spec_digest")
            or expected_path != operation.get("generation_path")
        ):
            raise WorkbenchConflict(
                "生成期间冻结 CSIR 已改变；停止本轮并重新形成方案"
            )
        snapshot = self.project.capture_snapshot(
            f"generic RTL candidate attempt {attempt}",
        )
        workspace = self.project.workspaces_dir / (
            f"{operation_id}-generation-{attempt}"
        )
        evidence_dir = self.project.operations_dir / (
            f"{operation_id}-generation-{attempt}"
        )
        evidence_dir.mkdir(parents=True, exist_ok=True)
        report: dict[str, Any] = {}
        try:
            self.project._git(
                "worktree", "add", "--detach", str(workspace), snapshot["commit"],
            )
            report = (
                verify_submodule(
                    workspace, spec, instance,
                    timeout=self.project.config().timeout, stop_event=stop_event,
                ) if instance else verify_generated_rtl(
                    workspace, spec, parameters=self.project.config().top_parameters,
                    timeout=self.project.config().timeout, stop_event=stop_event,
                )
            )
            ast_relative = report.get("ast_path", xml_artifact_path())
            ast = workspace / ast_relative
            if ast.is_file():
                target = evidence_dir / Path(ast_relative).name
                shutil.copy2(ast, target)
                report["ast_sha256"] = _file_sha256(target)
        finally:
            if workspace.is_dir():
                self.project._git(
                    "worktree", "remove", "--force", str(workspace), check=False,
                )
        log = str(report.pop("log", ""))
        (evidence_dir / "run.log").write_text(log, encoding="utf-8")
        report.update({
            "snapshot": snapshot,
            "spec_digest": spec["spec_digest"],
            "source": operation["generation_path"],
            "evidence_dir": evidence_dir.relative_to(self.project.root).as_posix(),
        })
        (evidence_dir / "report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return report

    def _validate_specir_questions(self) -> list[dict[str, Any]]:
        path = self.project.root / "spec" / "questions.json"
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise WorkbenchError("规格生成缺少 spec/questions.json") from exc
        except (OSError, json.JSONDecodeError) as exc:
            raise WorkbenchError(f"spec/questions.json 无法解析：{exc}") from exc
        if not isinstance(document, list):
            raise WorkbenchError("spec/questions.json 必须是 JSON 数组")
        seen: set[str] = set()
        normalized: list[dict[str, Any]] = []
        for index, value in enumerate(document):
            if not isinstance(value, dict):
                raise WorkbenchError(f"questions[{index}] 必须是对象")
            question_id = str(value.get("id") or "").strip()
            title = str(value.get("title") or "").strip()
            status = str(value.get("status") or "open").strip()
            options = value.get("options", [])
            if not question_id or question_id in seen:
                raise WorkbenchError(f"questions[{index}] 缺少唯一 id")
            if not title or status not in {"open", "resolved"}:
                raise WorkbenchError(f"questions[{index}] 缺少 title 或 status 无效")
            if status == "open" and (
                not isinstance(options, list) or len(options) < 2
                or any(not isinstance(item, dict) or not item.get("key") or not item.get("label") for item in options)
            ):
                raise WorkbenchError(f"questions[{index}] 的 open 决策至少需要两个有效 options")
            seen.add(question_id)
            normalized.append(value)
        return normalized

    def _validate_specir_operation_outputs(
        self, operation: dict[str, Any], action_kind: str,
    ) -> str:
        spec_dir = self.project.root / "spec"
        source = spec_dir / "draft.specir"
        provenance = spec_dir / "provenance.json"
        if action_kind != "acceptance_propose":
            if not (spec_dir / "design_doc.md").is_file():
                raise WorkbenchError("规格操作缺少 spec/design_doc.md")
            if not source.is_file() or not provenance.is_file():
                raise WorkbenchError("规格操作没有产出 draft.specir 与 provenance.json")
            questions = self._validate_specir_questions()
            try:
                provenance_doc = json.loads(provenance.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise WorkbenchError(f"spec/provenance.json 无法解析：{exc}") from exc
            if not isinstance(provenance_doc, dict):
                raise WorkbenchError("spec/provenance.json 必须是 JSON 对象")
            provenance_question_ids = {
                str(item.get("id", ""))
                for item in provenance_doc.get("requirements", [])
                if isinstance(item, dict) and item.get("status") == "question" and item.get("id")
            }
            open_question_ids = {
                str(item["id"]) for item in questions
                if item.get("status", "open") == "open"
            }
            missing_questions = sorted(provenance_question_ids - open_question_ids)
            if missing_questions:
                raise WorkbenchError(
                    "provenance 中的未决需求缺少结构化决策问题："
                    + ", ".join(missing_questions)
                )
            return specir_revision_id(source)

        plan_path = spec_dir / "acceptance.plan.yaml"
        if not plan_path.is_file():
            raise WorkbenchError("项目验收计划操作没有产出 acceptance.plan.yaml")
        try:
            plan = yaml.safe_load(plan_path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            raise WorkbenchError(f"项目验收计划无法解析：{exc}") from exc
        known_requirement_ids: set[str] = set()
        required_requirement_ids: set[str] = set()
        known_design_groups: set[str] = set()
        try:
            provenance_doc = json.loads(provenance.read_text(encoding="utf-8"))
            known_requirement_ids = {
                str(item.get("id", "")).strip()
                for item in provenance_doc.get("requirements", [])
                if isinstance(item, dict)
                and str(item.get("id", "")).startswith("REQ-")
            }
            required_requirement_ids = {
                str(item.get("id", "")).strip()
                for item in provenance_doc.get("requirements", [])
                if isinstance(item, dict)
                and str(item.get("id", "")).startswith("REQ-")
                and str(item.get("classification", "normative")) == "normative"
            }
            known_design_groups = {
                str(item.get("design_group", "")).strip()
                for item in provenance_doc.get("nodes", [])
                if isinstance(item, dict) and item.get("design_group")
            }
        except (OSError, json.JSONDecodeError, AttributeError) as exc:
            raise WorkbenchError(f"无法核对项目验收计划的 SpecIR node：{exc}") from exc
        revision_id = specir_revision_id(source)
        try:
            normalized = validate_acceptance_plan(
                plan,
                known_requirement_ids=known_requirement_ids,
                known_design_groups=known_design_groups,
                required_requirement_ids=required_requirement_ids,
                require_complete=True,
            )
        except ValueError as exc:
            raise WorkbenchError(f"项目验收计划门禁失败：{exc}") from exc
        normalized.update({
            "scope": "project", "confirmed": False,
        })
        plan_path.write_text(
            yaml.safe_dump(normalized, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        return revision_id

    def _validate_constraint_question_output(
        self, operation: dict[str, Any],
    ) -> list[dict[str, Any]]:
        path = self.project.root / "spec/project_constraints.questions.json"
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
            normalized = validate_constraint_questions(
                document,
                spec_revision_id=str(operation.get("spec_revision_id", "")),
            )
            previous = operation.get("previous_constraints")
            if isinstance(previous, dict):
                required = unavailable_constraint_categories(
                    previous,
                    available_platforms=frozenset(
                        str(item) for item in operation.get("available_platforms", [])
                    ),
                    available_corners={
                        str(platform): frozenset(str(item) for item in corners)
                        for platform, corners in operation.get("available_corners", {}).items()
                    },
                    available_memory_macros=frozenset(
                        str(item) for item in operation.get("available_memory_macros", [])
                    ),
                    available_memory_macro_views={
                        str(macro): {
                            str(name): str(path) for name, path in views.items()
                        }
                        for macro, views in operation.get(
                            "available_memory_macro_views", {}
                        ).items()
                    },
                )
                represented = {
                    project_constraint_category(
                        item.get("id"), item.get("title"), item.get("context"),
                    )
                    for item in normalized
                }
                missing = sorted(required - represented)
                if missing:
                    raise WorkbenchError(
                        "project constraint questions omitted unavailable inherited choices: "
                        + ", ".join(missing)
                    )
        except FileNotFoundError as exc:
            raise WorkbenchError(
                "project constraints Role did not produce spec/project_constraints.questions.json"
            ) from exc
        except (OSError, json.JSONDecodeError, ImplementationConstraintsError) as exc:
            raise WorkbenchError(f"project constraint questions failed validation: {exc}") from exc
        path.write_text(
            json.dumps(normalized, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return normalized

    def _validate_implementation_constraints_draft(
        self, operation: dict[str, Any],
    ) -> dict[str, Any]:
        constraint_path = (
            self.project.root / "physical/chip-nebula/implementation.constraints.json"
        )
        try:
            document = json.loads(constraint_path.read_text(encoding="utf-8"))
            options = dict(
                spec_revision_id=str(operation.get("spec_revision_id", "")),
                available_platforms=frozenset(
                    str(item) for item in operation.get("available_platforms", [])
                ),
                available_corners={
                    str(platform): frozenset(str(item) for item in corners)
                    for platform, corners in operation.get("available_corners", {}).items()
                },
                available_memory_macros=frozenset(
                    str(item) for item in operation.get("available_memory_macros", [])
                ),
                available_memory_macro_views={
                    str(macro): {
                        str(name): str(path) for name, path in views.items()
                    }
                    for macro, views in operation.get(
                        "available_memory_macro_views", {}
                    ).items()
                },
                available_platform_details={
                    str(platform): dict(details)
                    for platform, details in operation.get(
                        "available_platform_details", {}
                    ).items()
                },
                required_decision_ids=frozenset(
                    str(item) for item in operation.get("decision_artifact_ids", [])
                ),
                require_frozen=False,
            )
            from chip_nebula.taskgraph.implementation_constraints import missing_implementation_parameters
            normalized = validate_implementation_constraints({**document, "status": "draft"}, **options, allow_incomplete=True)
            valid_sdc = True
            try:
                normalized = validate_implementation_constraints(normalized, **options)
                valid_sdc = not missing_implementation_parameters(normalized)
            except ImplementationConstraintsError:
                valid_sdc = False
        except FileNotFoundError as exc:
            raise WorkbenchError("project constraints Role did not produce the final JSON") from exc
        except (OSError, json.JSONDecodeError, ImplementationConstraintsError) as exc:
            raise WorkbenchError(f"implementation constraints failed validation: {exc}") from exc
        if not valid_sdc and "sdc_sha256" in document:
            raise WorkbenchError("Author constraints require a regenerated, verified author SDC")
        sdc_path = constraint_path.with_name("constraints.sdc")
        sdc = None
        if valid_sdc:
            try:
                original = validate_implementation_constraints(document, **options)
                sdc = render_sdc(
                    normalized, authored_document=original,
                    authored_sdc=sdc_path.read_bytes() if "sdc_sha256" in original else None,
                )
            except (ImplementationConstraintsError, OSError, UnicodeError) as exc:
                raise WorkbenchError(str(exc)) from exc
        constraint_path.parent.mkdir(parents=True, exist_ok=True)
        constraint_path.write_text(
            json.dumps(normalized, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        if valid_sdc:
            sdc_path.write_text(sdc, encoding="utf-8")
        else:
            sdc_path.unlink(missing_ok=True)
        return normalized

    def _execute_agent(
        self, operation_id: str, instruction: str, framework: str,
        write_paths: list[str], stage: str = "rtl", resume_session_id: str = "",
    ) -> None:
        summaries: list[str] = []
        status = "failed"
        session_id = resume_session_id
        try:
            pool = AgentPoolManager(default_framework=framework, force_framework=True)
            self._agent_pool = pool
            operation = self.project.operation(operation_id)
            action_kind = str(operation.get("action_kind", ""))
            specir_task_stage = {
                "spec_generate": "spec-generate",
                "spec_repair": "spec-repair",
                "decision_apply": "spec-decision-apply",
                "spec_diagnostics_decide": "spec-diagnostics-decide",
                "acceptance_propose": "project-acceptance-propose",
                "constraints_questions_generate": "project-constraints-questions",
                "project_decisions_consolidate": "project-decisions-consolidate",
                "constraints_finalize": "project-constraints-finalize",
            }.get(action_kind, "spec-generate")
            task_stage = specir_task_stage if stage in {"specir", "impl_constraints"} else {
                "specification": "specification",
                "rtl_generation": "rtl-generation",
                "rtl_repair": "rtl-repair",
                "acceptance_generation": "acceptance-generation",
                "advisory": "advisory",
            }.get(stage, "rtl-edit")
            assigned_agent = (
                "project-verification-architect"
                if stage == "specir" and action_kind == "acceptance_propose"
                else "project-decision-consolidator"
                if action_kind in {"spec_diagnostics_decide", "project_decisions_consolidate"}
                else "project-constraints-author"
                if stage == "impl_constraints"
                else "specification-engineer" if stage == "specir"
                else {
                    "specification": "requirements-engineer",
                    "rtl_generation": "rtl-generator",
                    "rtl_repair": "rtl-repairer",
                    "acceptance_generation": "acceptance-engineer",
                    "advisory": "stage-advisor",
                }.get(stage, "rtl-designer")
            )
            task = TaskManifest(
                task_id=operation_id, feature_id="workbench",
                stage=task_stage,
                assigned_agent=assigned_agent,
                context=TaskContext(top_module=self.project.config().top_module),
                target=[FileTarget(path=item, status="modify") for item in write_paths],
                write_paths=write_paths, timeout=self.project.config().agent_timeout,
                run_id=operation_id,
                max_iterations=3,
                max_turns_per_session=(60 if stage == "specir" else 30),
                live_workspace=True,
                prompt_override=(
                    (
                        "你是需求规格阶段的工程师。根据用户的中文需求创建或完善 "
                        "spec/design.csir.yaml，只能修改该文件，不得修改 RTL、测试或工程配置。"
                        "使用 CSIR schema_version: 1；保留稳定 spec_id、name、revision、demand，"
                        "并明确 parameters、clocks、resets、ports、requirements、acceptance 和 "
                        "open_questions。根据实际需求选择 design_kind：通用组合或单时钟模块用 "
                        "generic_module；有 APB 寄存器契约的外设用 register_peripheral；"
                        "固定受限系统用 single_clock_soc。用户没有要求 APB 时，不得添加 APB "
                        "接口、GPIO 寄存器或示例 IP。"
                        "generic_module 的 interfaces、registers、address_windows、behaviors "
                        "仅在有已支持契约时填写。generic_module 复用普通引脚 IP 时，"
                        "只选择具备 generic-named-port-v1 契约的包，并明确每个引脚绑定；"
                        "IP 之间的直接连线须在 internal_signals 声明名称和位宽，"
                        "每条信号恰好一个输出驱动且至少一个输入接收端。"
                        "single_clock_soc 使用其专用 PicoRV32-native/APB4 能力与装配契约，"
                        "不要求普通引脚 generic-named-port-v1 标签；来源已审核但资格 pending "
                        "的真实包可以列为草稿候选，后续产品准备阶段再执行配置资格验证。"
                        "不得暗中推断协议适配或地址译码。不要凭空捏造 IP 身份；"
                        "没有可用包时写入待确认事项。"
                        "其端口、可观察行为、"
                        "时钟复位、边界和验收要求"
                        "应写入 ports、requirements 与 acceptance。组合模块 clocks/resets 为空；"
                        "时序模块首期只支持一个上升沿时钟和至多一个明确复位，并须声明对应输入端口。"
                        "CSIR 字段格式必须严格符合编译器契约：复位对象用 "
                        "{name: rst_n, active: low, kind: async, clock: clk}，"
                        "不要用 active_level 或 asynchronous；每条需求用 "
                        "{id: REQ-001, text: 需求正文, source: 用户需求原文, status: confirmed}，"
                        "只将用户已经明确提出的行为标为 confirmed；每条验收用 "
                        "{id: ACC-001, kind: simulation, requirement_ids: [REQ-001], "
                        "status: planned, description: 独立检查内容}，kind 只支持 "
                        "simulation、lint、elaboration；通用模块的独立验收只能用 "
                        "simulation/elaboration，且至少一项 simulation；Lint 是另行执行的"
                        "设计检查，不能用来代替功能或物理目标验收；未决问题用 "
                        "{id: Q-001, question: 待用户回答的具体问题, status: open}，"
                        "没有真实待确认语义时用 open_questions: []。"
                        "不要把人工审核、尚未执行验收或可在物理阶段配置的条件当作"
                        "缺失的功能语义问题。用户提出的‘审核前不冻结’和‘未运行不报通过’"
                        "属于平台门禁，只体现在草稿状态与 planned 验收，不应写成 RTL 的"
                        "需求或假装可由 elaboration 证明的验收项。Sky130HD、PVT、周期等"
                        "物理意图放入 technical_target；Lint、仿真或展开不能证明 STA、"
                        "DRC、LVS 或物理时序通过。所有已确认设计需求都须有独立验收项覆盖。"
                        "验收项只能标为 planned，除非工程里已有独立实现且可核对；"
                        "不得把规格编译通过冒充 RTL 或测试通过。"
                        "不要自行冻结规格；无法从用户输入确定的必要设计语义写入 open_questions。"
                        "下面是平台只读核验的内置与工程 IP 目录。bundled 表示可导入的内置包，"
                        "imported 表示已导入本工程；source review approved 只代表来源审核，"
                        "qualification pending 不能写成已经通过配置验证。"
                        "只能引用目录中实际存在、integrity valid 且来源已审核的精确包版本；"
                        "参数必须在声明范围内。目录能力不满足需求时明确标为待处理，"
                        "不能悄悄禁用中断、放宽功能或伪造另一版本。"
                        "\n\n平台 IP 目录快照：\n"
                        + json.dumps(
                            operation.get("ip_catalog", {}), ensure_ascii=False,
                            sort_keys=True,
                        )
                        + "\n\n"
                        "请用简体中文总结规格与待确认项。\n\n"
                        if stage == "specification" else
                        "你是当前芯片设计阶段的只读工程顾问。请检查工程内已有规格、"
                        "IP 锁、RTL、运行记录和报告来回答用户问题。不得修改、创建或删除"
                        "任何文件；不得声称未运行的工具已经通过。请用简体中文给出依据和"
                        "下一步建议。\n\n"
                        if stage == "advisory" else
                        (
                            ("你是 RTL 修复工程师。只能根据下列已冻结 CSIR 修复 "
                             if stage == "rtl_repair" else
                             "你是 RTL 生成工程师。只能根据下列已冻结 CSIR 为该工程生成 ")
                            + f"{operation['generation_path']}，不得修改或创建规格、验收用例、"
                            "参考模型、工程配置、约束或 IP 库文件。实现全部已确认的可观察"
                            "需求，不得使用空壳模块、常量输出或硬编码示例冒充功能。"
                            "你可以在脑中检查设计，但正式 Verilator 展开和端口契约由平台"
                            "在操作后的固定快照中执行；编译通过不代表功能验收通过。"
                            "代码标识符保持英文，说明使用简体中文。"
                            + (
                                "\n\n本次只处理以下父设计中的生成子模块；"
                                "必须使用指定模块名、完整端口和需求行为，"
                                "不得重写确定性装配顶层或已有 IP。\n"
                                + json.dumps(
                                    submodule_contract(
                                        SpecificationWorkspace(self.project.root).state(),
                                        operation["generation_instance"],
                                    ),
                                    ensure_ascii=False, indent=2,
                                )
                                if operation.get("generation_instance") else ""
                            )
                            + "\n\n冻结 CSIR：\n"
                            + json.dumps(
                                SpecificationWorkspace(self.project.root).state()["document"],
                                ensure_ascii=False, indent=2,
                            )
                            + "\n\n"
                        )
                        if stage in {"rtl_generation", "rtl_repair"} else
                        (
                            "你是独立验收工程师。只根据下列已冻结 CSIR 编写 "
                            f"{operation['acceptance_path']}，不得修改 RTL、规格、约束、"
                            "工程配置或 IP 库。验收期望来自规格，不得从当前 RTL 推断；"
                            "checker 只能驱动和观察被测顶层的公开端口，不得用 dut. 内部层次"
                            "引用依赖内部信号、实例名或库实现。结构、IP 锁和连接由平台单独检查；"
                            "内部状态需求须用公开输出上的后续可观察效果检验。"
                            "为每个 simulation 验收 ID 构造能区分正确和错误行为的检查，"
                            "真实成功后逐行打印 NEBULA_CHECK <验收 ID> PASS。"
                            "失败必须以 $fatal(1, ...) 结束；若用其他非零退出方式，"
                            "须先打印 NEBULA_CHECK <验收 ID> FAIL。"
                            "避免无界等待，为所有时钟过程设置合理超时。"
                            "平台会在固定快照独立运行真实 RTL 与零输出缺陷版本，"
                            "仅当真实版本通过而缺陷版本被明确拒绝时才形成待审核候选；"
                            "这仍需人工审阅冻结，不代表功能已获交付资格。"
                            + (
                                "当前顶层是已锁定 IP 的装配。真实编译应使用 integration/nebula.f，"
                                "其中包含只读 vendor 源码和 integration/nebula_assembly.sv；"
                                "不得改写装配或库文件，也不要把包装顶层单文件编译当作真实验收。"
                                if SpecificationWorkspace(self.project.root).state()["document"].get("instances")
                                else ""
                            )
                            + "\n\n冻结 CSIR：\n"
                            + json.dumps(
                                SpecificationWorkspace(self.project.root).state()["document"],
                                ensure_ascii=False, indent=2,
                            )
                            + "\n\n"
                        )
                        if stage == "acceptance_generation" else
                        (
                            str(operation.get("role_system_prompt", "")) + "\n"
                            if action_kind == "acceptance_propose"
                            or stage == "impl_constraints"
                            else "你正在直接编辑一个 Verilog/SystemVerilog 工程。"
                        )
                        + (
                            "只能修改授权路径，不得运行破坏性的 Git 命令。"
                        )
                        + "请使用简体中文说明修改内容和验证结果；"
                        + "代码、标识符、命令和原始日志保持原样。\n\n"
                    )
                    + f"授权路径：{write_paths}\n\n用户需求：\n{instruction}"
                ),
            )
            max_repairs = int(operation.get("max_repairs", 2))
            stop_event = self._agent_stop_events[operation_id]
            for attempt in range(1, max_repairs + 2):
                while True:
                    if not self._await_agent_resume(operation_id, stop_event):
                        status = "stopped"
                        summaries.append("用户已停止此操作；未领取下一轮任务。")
                        break
                    break
                if status == "stopped":
                    break
                task.iteration = attempt
                task.session_id = session_id
                # Every desktop Agent run is a resumable conversation from its
                # first dispatch.  SDK adapters that support caller-provided
                # IDs (Claude Code/Qoder) allocate one when it is empty;
                # CLI adapters that allocate IDs themselves capture the emitted
                # ID.  Later repair/decision work therefore resumes by default.
                task.reuse_session = True
                result = pool.dispatch(task, self.project.root, project_root=self.project.root)
                recovered_outputs = self.project.recover_declared_tool_output_scope_failure(
                    operation_id, result.error,
                )
                if recovered_outputs:
                    result.success = True
                    result.error = None
                    result.execution_log += (
                        "\n\n工作台已清理仅位于已登记报告/波形目录的 Agent 自检输出，"
                        "未扩大 RTL 写权限，继续执行正式验证。"
                    )
                session_id = result.session_id or session_id
                error_note = f"\nAgent 错误：{result.error}" if result.error else ""
                summaries.append(
                    f"Agent 第 {attempt} 次执行：\n"
                    f"{result.execution_log[-20_000:]}{error_note}"
                )
                operation = self.project.operation(operation_id)
                operation.update({"repair_attempt": attempt, "session_id": session_id})
                self.project._write_operation(operation)
                if stage == "specification":
                    try:
                        current_spec = SpecificationWorkspace(self.project.root).state()
                    except (SpecificationError, OSError, UnicodeError):
                        current_spec = None
                    unauthorized = (
                        self._unanswered_spec_questions_removed(operation, current_spec)
                        if current_spec is not None else []
                    )
                    if unauthorized:
                        raw = self.project.capture_snapshot(
                            "unauthorized CSIR clarification", include_tool_outputs=True,
                        )
                        self.project._restore_paths(
                            operation.get("question_restore_commit")
                            or operation["before"]["commit"],
                            ["spec/design.csir.yaml"],
                        )
                        operation["raw_after"] = raw
                        operation["unauthorized_question_resolutions"] = unauthorized
                        self.project._write_operation(operation)
                        status = "failed"
                        summaries.append(
                            "Agent 删除或解决了未经用户回答的待确认事项："
                            + "、".join(unauthorized)
                            + "。规格已从最近一次保留待确认事项的快照恢复，原始输出保留供审查。"
                        )
                        break
                if stop_event.is_set():
                    status = "stopped"
                    summaries.append("用户已停止此操作；不再启动验证或修复。")
                    break
                if not result.success:
                    break
                if not self._await_agent_resume(operation_id, stop_event):
                    status = "stopped"
                    summaries.append("用户已停止此操作；不再启动验证或修复。")
                    break
                if stage == "advisory":
                    status = "succeeded"
                    summaries.append("只读阶段答复完成；工程文件未授权写入。")
                    break
                if stage == "impl_constraints":
                    if action_kind == "constraints_questions_generate":
                        questions = self._validate_constraint_question_output(operation)
                        verdict = "questions_ready"
                        summaries.append(
                            f"project constraints Role produced {len(questions)} audited candidates."
                        )
                        diagnostics = {"question_count": len(questions)}
                    elif action_kind == "constraints_finalize":
                        document = self._validate_implementation_constraints_draft(operation)
                        verdict = "constraints_draft_ready"
                        summaries.append(
                            "project constraints draft is ready for human editing and freeze confirmation."
                        )
                        diagnostics = {
                            "implementation_constraints_status": document["status"],
                        }
                    else:
                        raise WorkbenchError(f"unsupported constraints action: {action_kind}")
                    status = "succeeded"
                    operation = self.project.operation(operation_id)
                    operation["spec_revision_id"] = str(operation.get("spec_revision_id", ""))
                    operation["engineering_verdict"] = verdict
                    operation.update(diagnostics)
                    self.project._write_operation(operation)
                    break
                if stage == "specir":
                    # specir 阶段的工程判定属于 Spec Compiler 确定性检查
                    # （前端在操作结束后自动执行），Agent 写出 spec/ 产物即完成；
                    # 不得落入 RTL 正式验证分支。
                    try:
                        revision_id = self._validate_specir_operation_outputs(
                            operation, action_kind,
                        )
                    except WorkbenchError as exc:
                        # An acceptance plan is a generated structured
                        # artifact.  Treat a YAML/schema gate rejection like
                        # any other repairable Agent output, not as a reason
                        # to leave a broken plan for the user to fix by hand.
                        if action_kind != "acceptance_propose" or attempt > max_repairs:
                            raise
                        feedback = str(exc)
                        summaries.append(f"项目验收计划门禁未通过：{feedback}")
                        task.prompt_override = (
                            "上一轮项目验收计划未通过平台解析/结构门禁。以下反馈是平台对整份"
                            "计划的一次性扫描结果，不要只修第一项。只可修改 "
                            "spec/acceptance.plan.yaml，不得修改 CSIR、provenance、questions、"
                            "RTL、测试或工程配置。重新阅读当前 spec/design_doc.md、"
                            "spec/draft.specir、spec/provenance.json 与冻结的 "
                            "physical/chip-nebula/implementation.constraints.json；旧计划只可作为"
                            "验收意图参考，必须整体刷新容量、地址范围、宏数量、PPA 指标、"
                            "标题与 detail。删除全部 spec_nodes；每个 item 改用当前 "
                            "provenance.json 中真实存在的 requirement_ids（REQ-*）和 "
                            "design_groups，并覆盖全部 normative requirements。"
                            "文件必须是可被 PyYAML safe_load 解析的 YAML；含冒号、#、引号"
                            "或换行的中文说明必须使用 YAML 引号或块标量。完成前请用 "
                            "yaml.safe_load 验证语法，并程序化扫描整份计划的 requirement_ids、"
                            "design_groups 和 normative requirement 覆盖，然后只回复一句确认。"
                            "\n\n门禁反馈：\n"
                            + feedback
                        )
                        continue
                    status = "succeeded"
                    summaries.append(
                        "spec 产物已写入并通过输出契约；工程判定以 Spec Compiler "
                        "确定性检查和规格就绪门禁为准。"
                    )
                    operation = self.project.operation(operation_id)
                    operation["spec_revision_id"] = revision_id
                    operation["engineering_verdict"] = "artifacts_written"
                    self.project._write_operation(operation)
                    break
                if stage == "acceptance_generation":
                    report = self._check_generic_acceptance(
                        operation_id, attempt, stop_event,
                    )
                    verdict = report.get("verdict", "failed")
                    operation = self.project.operation(operation_id)
                    operation.setdefault("acceptance_checks", []).append({
                        "attempt": attempt,
                        "verdict": verdict,
                        "snapshot": report.get("snapshot", {}),
                        "evidence_dir": report.get("evidence_dir", ""),
                        "diagnostics": report.get("diagnostics", []),
                    })
                    operation["engineering_verdict"] = (
                        "candidate_review_required" if verdict == "passed" else verdict
                    )
                    self.project._write_operation(operation)
                    if verdict == "passed":
                        status = "succeeded"
                        summaries.append(
                            "独立 checker 在真实 RTL 上通过并拒绝零输出缺陷。"
                            "这是待审核候选，必须由用户审阅并冻结才能用于正式验收。"
                        )
                        break
                    if verdict == "stopped" or stop_event.is_set():
                        status = "stopped"
                        summaries.append("用户已停止独立 checker 生成或自检。")
                        break
                    feedback = "\n".join(report.get("diagnostics", [])) or "checker 自检失败"
                    summaries.append(f"独立 checker 自检未通过：\n{feedback}")
                    if attempt <= max_repairs:
                        task.prompt_override = (
                            "上一轮独立 checker 未通过固定快照自检。只能修改 "
                            f"{operation['acceptance_path']}，不得修改 RTL、规格或验收门禁。"
                            f"\n诊断：\n{feedback}\n详细日志：\n"
                            + (self.project.root / report["evidence_dir"] / "run.log")
                            .read_text(encoding="utf-8", errors="replace")[-10_000:]
                        )
                    continue
                if stage in {"rtl_generation", "rtl_repair"}:
                    report = self._check_generic_generation(
                        operation_id, attempt, stop_event,
                    )
                    verdict = report.get("verdict", "failed")
                    operation = self.project.operation(operation_id)
                    operation.setdefault("generation_checks", []).append({
                        "attempt": attempt,
                        "verdict": verdict,
                        "snapshot": report.get("snapshot", {}),
                        "evidence_dir": report.get("evidence_dir", ""),
                        "diagnostics": report.get("diagnostics", []),
                    })
                    operation["engineering_verdict"] = (
                        ("repaired_unverified" if stage == "rtl_repair" else "generated_unverified")
                        if verdict == "passed" else verdict
                    )
                    self.project._write_operation(operation)
                    if verdict == "passed":
                        status = "succeeded"
                        summaries.append(
                            "RTL 已按冻结 CSIR 生成或修复；固定快照中的 Verilator 展开与端口"
                            "契约检查通过。独立功能验收尚未运行，不能视为交付通过。"
                        )
                        break
                    if verdict == "stopped" or stop_event.is_set():
                        status = "stopped"
                        summaries.append("用户已停止 RTL 生成或工具展开。")
                        break
                    feedback = "\n".join(report.get("diagnostics", [])) or (
                        "Verilator 展开失败；查看生成检查日志"
                    )
                    summaries.append(f"RTL 生成检查未通过：\n{feedback}")
                    if attempt <= max_repairs:
                        task.prompt_override = (
                            "上一轮生成的 RTL 未通过固定快照中的展开或端口契约检查。"
                            f"只能修改 {operation['generation_path']}，不得改写规格、"
                            "验收、约束、工程配置和 IP 库。"
                            "\n\n冻结规格与原始需求仍然有效。"
                            f"\n\n检查诊断：\n{feedback}"
                            f"\n\n详细日志：\n"
                            + (self.project.root / report["evidence_dir"] / "run.log")
                            .read_text(encoding="utf-8", errors="replace")[-10_000:]
                        )
                    continue
                if stage == "specification":
                    try:
                        spec_state = SpecificationWorkspace(self.project.root).state()
                        diagnostics = spec_state.get("diagnostics", [])
                    except (SpecificationError, OSError, UnicodeError) as exc:
                        spec_state = {"configured": False, "valid": False}
                        diagnostics = [{"code": "CSIR_READ", "message": str(exc)}]
                    question_diagnostics = [
                        item for item in diagnostics
                        if item.get("code") == "CSIR_OPEN_QUESTION"
                    ]
                    other_diagnostics = [
                        item for item in diagnostics
                        if item.get("code") != "CSIR_OPEN_QUESTION"
                    ]
                    verdict = (
                        "passed" if spec_state.get("configured") and spec_state.get("valid")
                        else "needs_clarification" if spec_state.get("configured")
                        and question_diagnostics and not other_diagnostics
                        else "failed"
                    )
                    if verdict == "passed":
                        status = "succeeded"
                        summaries.append(
                            "CSIR 确定性编译通过；规格仍为草稿，需由用户检查并冻结。"
                        )
                        break
                    feedback = "\n".join(
                        f"{item.get('code', 'CSIR')}: {item.get('path', '')} "
                        f"{item.get('message', '')}" for item in diagnostics
                    )
                    summaries.append(f"CSIR 编译未通过：\n{feedback}")
                    if verdict == "needs_clarification":
                        # Repair schema errors before asking the user, but do
                        # not spend repair budget guessing missing decisions.
                        status = "succeeded"
                        summaries.append(
                            "CSIR 草稿已保留；待确认事项需要用户澄清，"
                            "AI 不会自行删除、标记解决或冻结这些问题。"
                        )
                        break
                    if attempt <= max_repairs:
                        if question_diagnostics:
                            # Newly generated questions must survive schema
                            # repair as strictly as questions from the input.
                            operation = self.project.operation(operation_id)
                            previous_keys = {
                                item["key"] for item in operation.get("open_questions_before", [])
                            }
                            pending = {
                                item["key"]: item
                                for item in operation.get("open_questions_before", [])
                            }
                            for index, item in enumerate(
                                spec_state.get("document", {}).get("open_questions", [])
                            ):
                                if not isinstance(item, dict) or item.get("status") == "resolved":
                                    continue
                                key = str(item.get("id", index))
                                question = str(item.get("question") or item.get("description") or "")
                                if key not in pending:
                                    pending[key] = {"key": key, "question": question}
                            if set(pending) - previous_keys:
                                operation["open_questions_before"] = list(pending.values())
                                operation["question_restore_commit"] = self.project.capture_snapshot(
                                    "CSIR unresolved questions before schema repair",
                                )["commit"]
                                self.project._write_operation(operation)
                        task.prompt_override = (
                            "CSIR 确定性编译仍有阻断问题。只能修复 spec/design.csir.yaml，"
                            "不得修改 RTL、测试、工程配置，也不要冻结规格。"
                            "只修复下面列出的非待确认编译错误；已经记录的待确认问题"
                            "必须保持原 id、question 和 open 状态，不得自行删除或解决。"
                            "requirements 使用 text/source/status: confirmed，"
                            "acceptance 使用 kind: simulation/lint/elaboration，"
                            "resets 使用 active/kind，open_questions 使用 question/status。\n\n"
                            f"原始需求：\n{instruction}\n\n编译诊断：\n"
                            + "\n".join(
                                f"{item.get('code', 'CSIR')}: {item.get('path', '')} "
                                f"{item.get('message', '')}" for item in other_diagnostics
                            )
                        )
                    continue
                try:
                    validation = self.start_validation()
                except WorkbenchError as exc:
                    summaries.append(f"正式验证无法启动：{exc}")
                    break
                with self._lock:
                    self._agent_validation_runs[operation_id] = validation["id"]
                try:
                    validation_thread = self._threads[validation["id"]]
                    while validation_thread.is_alive():
                        if stop_event.is_set():
                            self.stop(validation["id"])
                        validation_thread.join(timeout=0.2)
                finally:
                    with self._lock:
                        self._agent_validation_runs.pop(operation_id, None)
                checked = self.get_run(validation["id"])
                operation = self.project.operation(operation_id)
                operation.setdefault("validation_run_ids", []).append(validation["id"])
                self.project._write_operation(operation)
                if stop_event.is_set():
                    status = "stopped"
                    summaries.append("用户已停止此操作；不再启动下一轮任务。")
                    break
                if checked.get("verdict") == "passed":
                    status = "succeeded"
                    summaries.append(f"正式验证通过：{validation['id']}")
                    break
                summaries.append(
                    f"正式验证 {validation['id']} 的结果为 {checked.get('verdict')}。"
                )
                if attempt <= max_repairs:
                    feedback = self.run_log(validation["id"])[-12_000:]
                    task.prompt_override = (
                        "固定快照中的 RTL 验证仍然失败。请分析日志，并且只修复"
                        f"授权路径 {write_paths}，不要修改 testbench 或验证脚本。"
                        "请使用简体中文说明修复内容和验证结果；代码、标识符、命令和原始日志保持原样。\n\n"
                        f"原始需求：\n{instruction}\n\n验证日志：\n{feedback}"
                    )
        except Exception as exc:
            summaries.append(str(exc))
        finally:
            try:
                completed = self.project.finish_operation(
                    operation_id, status=status, summary="\n\n".join(summaries)[-60_000:],
                )
                plan_id = str(completed.get("execution_plan_id", ""))
                if plan_id:
                    with self._lock:
                        try:
                            plan = self.execution_plan(plan_id)
                            plan.update({
                                "status": completed.get("status", "failed"),
                                "finished_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                                "operation_id": operation_id,
                            })
                            plan.pop("pause_fingerprint", None)
                            self._write_execution_plan(plan)
                        except WorkbenchError:
                            pass
            finally:
                with self._lock:
                    self._agent_operation = ""
                    self._agent_stop_events.pop(operation_id, None)
                    self._agent_validation_runs.pop(operation_id, None)
                    self._release_agent_lock()
                self._agent_pool = None

    def _claim_agent_lock(self) -> None:
        """Hold the project-wide live-edit lock until the Agent thread exits."""
        if self._agent_lock_handle is not None:
            raise WorkbenchConflict("another AI edit is already running")
        path = self.project.state_root / "agent.lock"
        handle = path.open("a+", encoding="utf-8")
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            handle.close()
            raise WorkbenchConflict(
                "another desktop process is already editing this project"
            ) from exc
        handle.seek(0)
        handle.truncate()
        handle.write(json.dumps({"pid": os.getpid(), "started_at": dt.datetime.now(dt.timezone.utc).isoformat()}))
        handle.flush()
        self._agent_lock_handle = handle

    def _release_agent_lock(self) -> None:
        handle = self._agent_lock_handle
        self._agent_lock_handle = None
        if handle is None:
            return
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()

    def _archive_outputs(self, workspace: Path, destination: Path, config: WorkbenchConfig) -> list[dict[str, str]]:
        result: list[dict[str, str]] = []
        destination.mkdir(parents=True, exist_ok=True)
        patterns = [(pattern, "report") for pattern in config.report_globs]
        if config.validation_mode == "fileset":
            patterns.append(("build/chip-nebula-validation/*.log", "report"))
        patterns += [(pattern, "waveform") for pattern in config.waveform_globs]
        seen: set[str] = set()
        for pattern, kind in patterns:
            for value in glob.glob(str(workspace / pattern), recursive=True):
                source = Path(value)
                if not source.is_file() or workspace not in source.resolve().parents:
                    continue
                relative = source.relative_to(workspace).as_posix()
                if relative in seen:
                    continue
                seen.add(relative)
                target = destination / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
                result.append({
                    "path": relative, "kind": kind,
                    "size": str(source.stat().st_size),
                    "sha256": _file_sha256(source),
                })
        return result

    @staticmethod
    def _diagnostic_text(
        run_dir: Path, artifacts: list[dict[str, Any]],
    ) -> str:
        """Collect bounded textual evidence for source-linked error parsing."""
        pieces: list[str] = []
        log_path = run_dir / "run.log"
        if log_path.is_file():
            pieces.append(log_path.read_text(encoding="utf-8", errors="replace"))
        artifact_root = (run_dir / "artifacts").resolve()
        remaining = 10_000_000
        text_suffixes = {".log", ".rpt", ".txt", ".out", ".err"}
        for item in artifacts:
            if remaining <= 0:
                break
            if item.get("kind") != "report":
                continue
            relative = str(item.get("path", ""))
            path = (artifact_root / relative).resolve()
            if (
                artifact_root not in path.parents or not path.is_file()
                or path.suffix.lower() not in text_suffixes
            ):
                continue
            size = min(path.stat().st_size, remaining)
            if size <= 0:
                continue
            with path.open("rb") as handle:
                content = handle.read(size).decode("utf-8", errors="replace")
            pieces.append(f"\n$ [artifact] {relative}\n{content}")
            remaining -= size
        return "".join(pieces)

    def _write_run(self, run: dict[str, Any]) -> None:
        directory = self.project.runs_dir / run["id"]
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / "run.json"
        temporary = directory / "run.json.tmp"
        temporary.write_text(
            json.dumps(run, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        temporary.replace(path)

    @staticmethod
    def _tool_versions(environment: dict[str, str] | None = None) -> dict[str, str]:
        process_environment = os.environ.copy()
        process_environment.update(environment or {})
        versions: dict[str, str] = {}
        for name in ("git", "make", "verilator", "iverilog", "vvp"):
            try:
                executable = shutil.which(
                    name, path=process_environment.get("PATH")
                )
            except TypeError:
                # Some embedders and tests provide the one-argument ``which``
                # contract. The selected command PATH still applies at run
                # time; this fallback only affects the initial version label.
                executable = shutil.which(name)
            if not executable:
                continue
            try:
                flag = "-V" if name in {"iverilog", "vvp"} else "--version"
                result = subprocess.run(
                    [executable, flag], capture_output=True, text=True, timeout=3,
                    env=process_environment,
                )
                output = result.stdout.strip() or result.stderr.strip()
                versions[name] = output.splitlines()[0][:300] if output else executable
            except (OSError, subprocess.TimeoutExpired):
                versions[name] = executable
        return versions

    def _recover_interrupted(self) -> None:
        lock_path = self.project.state_root / "agent.lock"
        recovery_lock = lock_path.open("a+", encoding="utf-8")
        try:
            try:
                fcntl.flock(
                    recovery_lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB
                )
            except BlockingIOError:
                # Another backend still owns this project.  Its running records
                # must not be mistaken for crash leftovers.
                return
            for path in self.project.runs_dir.glob("*/run.json"):
                try:
                    run = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    continue
                if run.get("status") in {"starting", "running"}:
                    if self._record_owner_alive(run):
                        continue
                    run.update({"status": "interrupted", "verdict": "stopped"})
                    self._write_run(run)
                if (
                    run.get("kind") == "physical"
                    and run.get("status") in {"stopped", "interrupted"}
                    and not self._record_owner_alive(run)
                ):
                    self._recover_physical_evidence(run)
            for path in self.project.operations_dir.glob("op-*.json"):
                try:
                    operation = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    continue
                if operation.get("status") == "running":
                    if self._record_owner_alive(operation):
                        continue
                    operation.update({
                        "status": "interrupted",
                        "summary": "Agent 操作尚未完成时桌面后端发生了重启。",
                    })
                    self.project._write_operation(operation)
                    plan_id = str(operation.get("execution_plan_id", ""))
                    if plan_id:
                        try:
                            plan = self.execution_plan(plan_id)
                            plan.update({
                                "status": "interrupted",
                                "finished_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                            })
                            plan.pop("pause_fingerprint", None)
                            self._write_execution_plan(plan)
                        except WorkbenchError:
                            pass
            for plan in self.list_execution_plans():
                if plan.get("status") not in {
                    "starting", "running", "pause_requested", "paused",
                }:
                    continue
                operation_id = str(plan.get("operation_id", ""))
                try:
                    operation = self.project.operation(operation_id) if operation_id else None
                except WorkbenchError:
                    operation = None
                if operation is not None and self._record_owner_alive(operation):
                    continue
                final_status = (
                    operation.get("status")
                    if operation is not None and operation.get("status")
                    not in {"starting", "running"}
                    else "interrupted"
                )
                plan.update({
                    "status": final_status,
                    "finished_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                })
                plan.pop("pause_fingerprint", None)
                self._write_execution_plan(plan)
            for path in self.project.assistant_dir.glob("assistant-*.json"):
                try:
                    record = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    continue
                if record.get("status") in {"starting", "running"}:
                    if self._record_owner_alive(record):
                        continue
                    record.update({
                        "status": "interrupted",
                        "error": "阶段助手运行期间桌面后端发生了重启。",
                        "finished_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                    })
                    self._write_assistant(record)
        finally:
            try:
                fcntl.flock(recovery_lock.fileno(), fcntl.LOCK_UN)
            finally:
                recovery_lock.close()

    def _recover_physical_evidence(self, run: dict[str, Any]) -> None:
        """Archive partial physical results when a worker died before cleanup."""
        run_id = str(run["id"])
        workspace = self.project.workspaces_dir / run_id
        if not workspace.is_dir():
            return
        run_dir = self.project.runs_dir / run_id
        try:
            flow = PhysicalFlow(
                self.project.root,
                PhysicalFlowConfig.from_document(run.get("physical_profile")),
            )
            artifacts = self._archive_physical_outputs(
                flow, workspace, run_dir / "artifacts"
            )
            extra = self._archive_outputs(
                workspace, run_dir / "artifacts", self.project.config(),
            )
            known = {item["path"] for item in artifacts}
            artifacts.extend(item for item in extra if item["path"] not in known)
            for item in artifacts:
                target = run_dir / "artifacts" / item["path"]
                if _file_sha256(target) != item["sha256"]:
                    raise WorkbenchError(f"recovered artifact checksum mismatch: {item['path']}")
            summary: dict[str, Any] = {}
            try:
                summary = flow.read_summary(workspace)
            except PhysicalFlowError:
                pass
            run["artifacts"] = artifacts
            run["summary"] = summary
            run["evidence_digest"] = "sha256:" + hashlib.sha256(
                json.dumps({
                    "summary": summary,
                    "artifacts": artifacts,
                    "inputs": run.get("input_digests", []),
                }, ensure_ascii=False, sort_keys=True, separators=(",", ":")
                ).encode("utf-8")
            ).hexdigest()
            run["evidence_recovery"] = {
                "status": "archived", "artifact_count": len(artifacts),
                "recovered_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            }
            self._write_run(run)
            self.project._git(
                "worktree", "remove", "--force", str(workspace), check=False
            )
            self.project._git("worktree", "prune", check=False)
        except (OSError, ValueError, PhysicalFlowError, WorkbenchError) as exc:
            # Leave the workspace in place so a later launch can retry.
            run["evidence_recovery"] = {"status": "pending", "error": str(exc)}
            self._write_run(run)
