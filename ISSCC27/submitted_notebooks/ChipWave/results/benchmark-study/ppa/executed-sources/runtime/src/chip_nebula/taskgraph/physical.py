"""Deterministic RTL-to-GDS execution support for Task Graph clients.

The module owns physical-flow configuration, tool discovery and evidence
classification.  Dashboard code only schedules the deterministic command and
publishes its result as a Task Graph artifact.
"""

from __future__ import annotations

import json
import hashlib
import difflib
import os
import re
import shlex
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any, Mapping


class PhysicalFlowError(RuntimeError):
    """Raised when a physical flow cannot be configured or executed."""


def _ancestor_toolchain_candidates(origin: Path) -> list[Path]:
    """Find a development tool bundle adjacent to an unpacked desktop tree."""
    start = origin if origin.is_dir() else origin.parent
    candidates: list[Path] = []
    for parent in (start, *start.parents):
        candidate = parent / "build" / "rtl2gds-tools"
        if candidate not in candidates:
            candidates.append(candidate)
    return candidates


_DEFAULT_ARTIFACT_GLOBS = [
    "build/rtl-to-gds/run-summary.json",
    "build/rtl-to-gds/gds-summary.json",
    "build/rtl-to-gds/simulation/build/*.log",
    "build/rtl-to-gds/simulation/build/*.vcd",
    "build/rtl-to-gds/orfs-work/results/**/1_2_yosys.v",
    "build/rtl-to-gds/orfs-work/results/**/6_final.*",
    "build/rtl-to-gds/orfs-work/objects/**/6_final_concat.cdl",
    "build/rtl-to-gds/orfs-work/objects/**/6_final_concat_used.cdl",
    "build/rtl-to-gds/orfs-work/objects/**/6_final_concat_used.manifest.json",
    "build/rtl-to-gds/orfs-work/reports/**/*.rpt",
    "build/rtl-to-gds/orfs-work/logs/**/*.log",
    "build/rtl-to-gds/orfs-work/logs/**/6_report.json",
    "build/rtl-to-gds/orfs-work/logs/**/5_2_route.json",
]


@dataclass
class PhysicalFlowConfig:
    """Versionable project configuration for one deterministic physical flow."""

    enabled: bool = False
    command: str = ""
    workdir: str = "."
    timeout: int = 14_400
    platform: str = "sky130hd"
    design: str = ""
    flow_variant: str = "smoke"
    num_cores: int = 2
    output_root: str = "build/rtl-to-gds"
    summary_path: str = "build/rtl-to-gds/run-summary.json"
    input_globs: list[str] = field(default_factory=lambda: [
        "**/*.sdc", "**/*.tcl", "Makefile", "config.mk", "run.sh", "prepare_orfs.py",
        "inspect_gds.py", "filter_lvs_cdl.py", "klayout.sh", "tool-versions.env",
    ])
    # Broad input globs copy files when present; these paths must be present.
    required_inputs: list[str] = field(default_factory=list)
    artifact_globs: list[str] = field(
        default_factory=lambda: list(_DEFAULT_ARTIFACT_GLOBS)
    )
    toolchain_root: str = ""
    orfs_root: str = ""
    tool_versions_file: str = "tool-versions.env"

    @classmethod
    def from_document(cls, document: Any) -> "PhysicalFlowConfig":
        raw = document if isinstance(document, Mapping) else {}
        config = cls()
        for name in asdict(config):
            if name in raw:
                setattr(config, name, raw[name])
        config.enabled = bool(config.enabled)
        config.command = str(config.command).strip()
        config.platform = str(config.platform).strip() or "sky130hd"
        config.design = str(config.design).strip()
        config.flow_variant = str(config.flow_variant).strip() or "smoke"
        config.timeout = max(1, min(int(config.timeout), 86_400))
        config.num_cores = max(1, min(int(config.num_cores), 128))
        config.artifact_globs = _string_list(
            config.artifact_globs, "physical.artifact_globs"
        )
        config.input_globs = _string_list(
            config.input_globs, "physical.input_globs"
        )
        config.required_inputs = _string_list(
            config.required_inputs, "physical.required_inputs"
        )
        for name in (
            "workdir", "output_root", "summary_path", "tool_versions_file",
        ):
            setattr(config, name, _safe_relative(str(getattr(config, name)), name))
        for name, patterns in (
            ("artifact_globs", config.artifact_globs),
            ("input_globs", config.input_globs),
            ("required_inputs", config.required_inputs),
        ):
            for pattern in patterns:
                _safe_relative(pattern, f"physical.{name}")
        for name in ("toolchain_root", "orfs_root"):
            value = str(getattr(config, name) or "").strip()
            if value and "\x00" in value:
                raise PhysicalFlowError(f"physical.{name} contains an invalid byte")
            setattr(config, name, value)
        if config.enabled and not config.command:
            raise PhysicalFlowError("physical.command is required when the flow is enabled")
        return config


def _string_list(value: Any, name: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise PhysicalFlowError(f"{name} must be a list of strings")
    return [item.strip() for item in value if item.strip()]


def _safe_relative(value: str, name: str) -> str:
    value = value.strip() or "."
    path = PurePosixPath(value.replace("\\", "/"))
    if path.is_absolute() or ".." in path.parts or "\x00" in value:
        raise PhysicalFlowError(f"physical.{name} must stay inside the project")
    return path.as_posix()


class PhysicalFlow:
    """Inspect and prepare a configured RTL-to-GDS command."""

    def __init__(self, project_root: Path, config: PhysicalFlowConfig) -> None:
        self.project_root = project_root.resolve()
        self.config = config

    def inspect_environment(
        self, top_parameters: Mapping[str, int] | None = None,
        *,
        ignore_expected_versions: bool = False,
    ) -> dict[str, Any]:
        tool_root = self._toolchain_root()
        orfs_root = self._orfs_root(tool_root)
        flow_home = _orfs_flow_home(orfs_root)
        # Product setup regenerates its version file from the selected tools.
        # A stale manual-flow version pin must not block that preflight.
        expected = {} if ignore_expected_versions else self._expected_versions()
        candidates = self.selected_tool_paths(tool_root)
        version_flags = {
            "git": "--version", "make": "--version", "python": "--version",
            "verilator": "--version", "iverilog": "-V", "vvp": "-V", "yosys": "-V",
            "openroad": "-version", "klayout": "-v",
        }
        expected_keys = {
            "yosys": "YOSYS_VERSION", "openroad": "OPENROAD_VERSION",
            "klayout": "KLAYOUT_VERSION",
        }
        tools: dict[str, dict[str, Any]] = {}
        missing: list[str] = []
        mismatches: list[str] = []
        for name, path in candidates.items():
            version = _tool_version(path, version_flags[name]) if path else ""
            expected_version = expected.get(expected_keys.get(name, ""), "")
            matches = not expected_version or expected_version in version
            tools[name] = {
                "path": str(path) if path else "",
                "version": version,
                "expected": expected_version,
                "ready": bool(path) and matches,
                "version_match": matches,
                "source": self._tool_source(path, tool_root),
            }
            if not path:
                missing.append(name)
            elif not matches:
                mismatches.append(
                    f"{name}: expected {expected_version}, got {version or 'unknown'}"
                )

        platform_files: list[dict[str, Any]] = []
        if flow_home:
            platform_root = flow_home / "platforms" / self.config.platform
            required = [platform_root]
            if self.config.platform == "sky130hd":
                required = [
                    platform_root / "gds" / "sky130_fd_sc_hd.gds",
                    platform_root / "drc" / "sky130hd.lydrc",
                    platform_root / "lvs" / "sky130hd.lylvs",
                    platform_root / "cdl" / "sky130hd.cdl",
                ]
            for path in required:
                ready = path.is_dir() if path == platform_root else path.is_file() and path.stat().st_size > 0
                platform_files.append({"path": str(path), "ready": ready})
                if not ready:
                    missing.append(f"platform:{path.name}")
        else:
            missing.append("OpenROAD-flow-scripts")

        actual_orfs_commit = _git_commit(orfs_root) if orfs_root else ""
        expected_orfs_commit = expected.get("ORFS_COMMIT", "")
        orfs_matches = not expected_orfs_commit or actual_orfs_commit == expected_orfs_commit
        if actual_orfs_commit and not orfs_matches:
            mismatches.append(
                f"ORFS: expected {expected_orfs_commit}, got {actual_orfs_commit}"
            )
        input_audit = self.audit_inputs()
        project_issues = self._project_issues(top_parameters)
        project_issues.extend(item["message"] for item in input_audit["issues"])
        return {
            "configured": self.config.enabled and bool(self.config.command),
            "ready": (
                self.config.enabled and bool(self.config.command)
                and not missing and not mismatches and not project_issues
            ),
            "profile": asdict(self.config),
            "toolchain_root": str(tool_root) if tool_root else "",
            "orfs": {
                "root": str(orfs_root) if orfs_root else "",
                "flow_home": str(flow_home) if flow_home else "",
                "commit": actual_orfs_commit,
                "expected_commit": expected_orfs_commit,
                "version_match": orfs_matches,
            },
            "tools": tools,
            "platform_files": platform_files,
            "missing": missing,
            "mismatches": mismatches,
            "project_issues": list(dict.fromkeys(project_issues)),
            "input_audit": input_audit,
        }

    def audit_inputs(self, root: Path | None = None) -> dict[str, Any]:
        """Check required project inputs without running project commands."""
        root = (root or self.project_root).resolve()
        issues: list[dict[str, Any]] = []
        checked: list[str] = []
        script_references = self._literal_script_sdc_inputs(root)
        config_references = self._literal_config_sdc_inputs(root)
        references = [*script_references, *config_references]
        for pattern in dict.fromkeys([*self.config.required_inputs, *references]):
            matches = sorted(root.glob(pattern))
            valid = [
                path for path in matches
                if path.is_file() and root in path.resolve().parents
                and path.stat().st_size > 0
            ]
            checked.append(pattern)
            if valid:
                continue
            suffix = Path(pattern).suffix.lower()
            if pattern.startswith(("tb/", "tbench/")):
                category = "acceptance"
                action = "恢复或重新冻结独立验收输入"
            elif suffix in {".v", ".sv", ".vh", ".svh"} or pattern.startswith("rtl/"):
                category = "design"
                action = "根据冻结规格形成受控 RTL 补全方案"
            elif suffix == ".sdc" or pattern.endswith("config.mk"):
                category = "constraint"
                action = "核对并确认技术目标或约束；AI 不得自行猜测"
            else:
                category = "flow"
                action = "恢复已登记的构建脚本或流程资产"
            source = (
                "required_inputs" if pattern in self.config.required_inputs
                else "script_reference" if pattern in script_references
                else "config_reference"
            )
            prefix = {
                "required_inputs": "物理流程必需输入",
                "script_reference": "物理流程脚本引用的输入",
                "config_reference": "物理流程配置引用的输入",
            }[source]
            issue = {
                "code": "missing_required_input",
                "path": pattern,
                "category": category,
                "agent_candidate": category == "design",
                "source": source,
                "action": action,
                "message": f"{prefix}缺失或为空：{pattern}（{action}）",
            }
            possible_matches = self._possible_input_matches(root, pattern)
            if possible_matches:
                issue["possible_matches"] = possible_matches
            issues.append(issue)
        return {
            "ready": not issues, "manifest_declared": bool(self.config.required_inputs),
            "checked": checked, "issues": issues,
        }

    def _literal_script_sdc_inputs(self, root: Path) -> list[str]:
        """Catch direct SDC references missed by a project's declared manifest.

        Dynamic paths still belong in required_inputs. The bundled dual-layout
        wrapper chooses its SDC with a variable and declares both layouts
        separately, so its branches are not guessed here.
        """
        try:
            tokens = shlex.split(self.config.command.replace("{mode}", "all"))
        except ValueError:
            return []
        script: Path | None = None
        for token in tokens:
            candidate = PurePosixPath(token.replace("\\", "/"))
            if candidate.is_absolute() or ".." in candidate.parts:
                continue
            if candidate.suffix.lower() == ".sh":
                script = root / self.config.workdir / candidate
                break
        if script is None or not script.is_file():
            return []
        script = script.resolve()
        if root not in script.parents:
            return []
        source = script.read_text(encoding="utf-8", errors="replace")
        result: list[str] = []
        for line in source.splitlines():
            stripped = line.lstrip()
            if stripped.startswith("#") or stripped.startswith("constraint_file="):
                continue
            for match in re.finditer(
                r"\$(?:\{(case_dir|repo_root)\}|(case_dir|repo_root))/"
                r"([A-Za-z0-9_./-]+\.sdc)\b", line,
            ):
                base = script.parent if (match.group(1) or match.group(2)) == "case_dir" else root
                path = (base / match.group(3)).resolve()
                if root not in path.parents:
                    continue
                relative = path.relative_to(root).as_posix()
                if relative not in result:
                    result.append(relative)
        return result

    def _literal_config_sdc_inputs(self, root: Path) -> list[str]:
        """Audit SDC paths named by a local ORFS config without evaluating Make."""
        result: list[str] = []
        for relative in (
            PurePosixPath(self.config.workdir) / "config.mk",
            PurePosixPath("physical/chip-nebula/config.mk"),
        ):
            config = (root / relative).resolve()
            if root not in config.parents or not config.is_file():
                continue
            source = config.read_text(encoding="utf-8", errors="replace")
            for line in source.splitlines():
                if line.lstrip().startswith("#") or "SDC_FILE" not in line:
                    continue
                for match in re.finditer(
                    r"\$\((CASE_DIR|NEBULA_PROJECT_ROOT)\)/"
                    r"([A-Za-z0-9_./-]+\.sdc)\b", line,
                ):
                    base = config.parent if match.group(1) == "CASE_DIR" else root
                    path = (base / match.group(2)).resolve()
                    if root not in path.parents:
                        continue
                    path_string = path.relative_to(root).as_posix()
                    if path_string not in result:
                        result.append(path_string)
        return result

    def _possible_input_matches(self, root: Path, pattern: str) -> list[str]:
        """Suggest nearby existing names; never select or rewrite a constraint."""
        if any(char in pattern for char in "*?[]"):
            return []
        target = PurePosixPath(pattern)
        suffix = target.suffix.lower()
        if not suffix:
            return []
        candidates: set[str] = set()
        nearby = root / target.parent
        if nearby.is_dir():
            for path in nearby.glob(f"*{suffix}"):
                if path.is_file() and root in path.resolve().parents:
                    candidates.add(path.relative_to(root).as_posix())
        for declared in self.config.required_inputs:
            if any(char in declared for char in "*?[]"):
                continue
            path = (root / declared).resolve()
            if path.is_file() and root in path.parents and path.suffix.lower() == suffix:
                candidates.add(path.relative_to(root).as_posix())
        ranked = sorted(
            (candidate for candidate in candidates if candidate != pattern),
            key=lambda candidate: difflib.SequenceMatcher(
                None, target.name, PurePosixPath(candidate).name,
            ).ratio(),
            reverse=True,
        )
        return [
            candidate for candidate in ranked[:3]
            if difflib.SequenceMatcher(
                None, target.name, PurePosixPath(candidate).name,
            ).ratio() >= 0.7
        ]

    def selected_tool_paths(
        self, tool_root: Path | None = None,
    ) -> dict[str, Path | None]:
        """Resolve the exact executables shared by RTL and physical runs."""
        tool_root = tool_root if tool_root is not None else self._toolchain_root()

        def bundled(name: str) -> tuple[Path, ...]:
            if not tool_root:
                return ()
            return (
                tool_root / "bin" / name,
                tool_root / "oss-cad-suite" / "bin" / name,
            )

        return {
            "git": _which("GIT_EXE", (), "git"),
            "make": _which("MAKE_EXE", (), "make"),
            "python": _which("PYTHON_EXE", (), "python3"),
            "verilator": _which("VERILATOR_EXE", bundled("verilator"), "verilator"),
            "iverilog": _which("IVERILOG_EXE", bundled("iverilog"), "iverilog"),
            "vvp": _which("VVP_EXE", bundled("vvp"), "vvp"),
            "yosys": _which("YOSYS_EXE", bundled("yosys"), "yosys"),
            "openroad": _which("OPENROAD_EXE", bundled("openroad"), "openroad"),
            "klayout": _which("KLAYOUT_CMD", bundled("klayout"), "klayout"),
        }

    @staticmethod
    def _tool_source(path: Path | None, tool_root: Path | None) -> str:
        if not path:
            return "missing"
        if tool_root and (path == tool_root or tool_root in path.parents):
            return "bundled"
        return "system"

    def validation_environment(
        self, paths: Mapping[str, Path | None] | None = None,
    ) -> dict[str, str]:
        """Build the process environment for deterministic RTL validation."""
        selected = dict(paths or self.selected_tool_paths())
        executable_names = ("verilator", "iverilog", "vvp")
        directories = list(dict.fromkeys(
            str(selected[name].parent)
            for name in executable_names if selected.get(name)
        ))
        current_path = os.environ.get("PATH", "")
        environment = {
            "PATH": os.pathsep.join([*directories, current_path])
            if current_path else os.pathsep.join(directories),
        }
        variable_names = {
            "verilator": "VERILATOR_EXE",
            "iverilog": "IVERILOG_EXE",
            "vvp": "VVP_EXE",
        }
        for name, variable in variable_names.items():
            if selected.get(name):
                environment[variable] = str(selected[name])
        return environment

    def validation_tools(self) -> dict[str, dict[str, Any]]:
        """Return the selected RTL executables without probing full PDK state."""
        tool_root = self._toolchain_root()
        paths = self.selected_tool_paths(tool_root)
        return {
            name: {
                "path": str(paths[name]) if paths.get(name) else "",
                "ready": bool(paths.get(name)),
                "source": self._tool_source(paths.get(name), tool_root),
            }
            for name in ("verilator", "iverilog", "vvp")
        }

    def execution_command(
        self, workspace: Path, mode: str = "all"
    ) -> tuple[str, dict[str, Any]]:
        if mode not in {"all", "physical"}:
            raise PhysicalFlowError("physical mode must be all or physical")
        state = self.inspect_environment()
        if not state["ready"]:
            details = [
                *state["missing"], *state["mismatches"],
                *state.get("project_issues", []),
            ]
            raise PhysicalFlowError(
                "physical environment is not ready: " + "; ".join(details)
            )
        workspace = workspace.resolve()
        output_root = (workspace / self.config.output_root).resolve()
        if workspace not in output_root.parents:
            raise PhysicalFlowError("physical output root escapes the snapshot")
        paths = {name: item["path"] for name, item in state["tools"].items()}
        validation_environment = self.validation_environment({
            name: Path(path) if path else None for name, path in paths.items()
        })
        variables = {
            "CHIP_NEBULA_RTL2GDS_WORK_ROOT": str(output_root),
            "CHIP_NEBULA_RTL2GDS_TOOL_ROOT": state["toolchain_root"],
            "ORFS_ROOT": state["orfs"]["root"],
            "OPENROAD_EXE": paths["openroad"],
            "YOSYS_EXE": paths["yosys"],
            "KLAYOUT_CMD": paths["klayout"],
            "VERILATOR_EXE": paths["verilator"],
            "IVERILOG_EXE": paths["iverilog"],
            "VVP_EXE": paths["vvp"],
            "PYTHON_EXE": paths["python"],
            "PATH": validation_environment["PATH"],
            "FLOW_VARIANT": self.config.flow_variant,
            "NUM_CORES": str(self.config.num_cores),
        }
        prefix = shlex.join(["env", *[f"{key}={value}" for key, value in variables.items()]])
        command = self.config.command.replace("{mode}", mode)
        return f"{prefix} {command}", state

    def _project_issues(
        self, top_parameters: Mapping[str, int] | None = None,
    ) -> list[str]:
        """Check the project-side flow contract without executing project code."""
        if not self.config.enabled:
            return []
        issues: list[str] = []
        if not self.config.design:
            issues.append("physical design top is not configured")
        workdir = (self.project_root / self.config.workdir).resolve()
        if not workdir.is_dir() or (
            workdir != self.project_root and self.project_root not in workdir.parents
        ):
            issues.append(f"physical workdir does not exist: {self.config.workdir}")
            return issues
        command = self.config.command.replace("{mode}", "all")
        try:
            tokens = shlex.split(command)
        except ValueError as exc:
            return [f"physical command cannot be parsed: {exc}"]
        script: Path | None = None
        for token in tokens:
            candidate = PurePosixPath(token.replace("\\", "/"))
            if candidate.is_absolute() or ".." in candidate.parts:
                continue
            if candidate.suffix.lower() in {".sh", ".py"} or "/" in token:
                path = (workdir / candidate).resolve()
                if path == self.project_root or self.project_root in path.parents:
                    script = path
                    break
        if script is None:
            issues.append(
                "cannot verify which project script produces the physical summary"
            )
        elif not script.is_file():
            issues.append(
                f"physical command script does not exist: {script.relative_to(self.project_root)}"
            )
        else:
            text = script.read_text(encoding="utf-8", errors="replace")
            summary = self.config.summary_path
            if summary not in text and Path(summary).name not in text:
                issues.append(
                    f"physical command does not declare summary output: {summary}"
                )

        definition_path = self.project_root / "physical/chip-nebula/flow-definition.json"
        if definition_path.is_file():
            try:
                definition = json.loads(definition_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                issues.append(f"generated physical definition is invalid: {exc}")
                return issues
            if definition.get("top_module") != self.config.design:
                issues.append("generated physical top does not match configured design")
            sources = definition.get("sources", [])
            if not isinstance(sources, list) or not sources:
                issues.append("generated physical definition has no RTL sources")
            else:
                for relative in sources:
                    if not isinstance(relative, str) or not (self.project_root / relative).is_file():
                        issues.append(f"generated physical RTL source is missing: {relative}")
            if not (self.project_root / "physical/chip-nebula/constraints.sdc").is_file():
                issues.append("generated physical SDC is missing")
            if not (self.project_root / "physical/chip-nebula/config.mk").is_file():
                issues.append("generated ORFS config is missing")
            from chip_nebula.taskgraph.physical_project import PhysicalProjectWizard
            issues.extend(
                PhysicalProjectWizard(self.project_root).existing_flow_issues(
                    self.config.design, top_parameters
                )
            )
        return list(dict.fromkeys(issues))

    def read_summary(self, workspace: Path) -> dict[str, Any]:
        path = (workspace / self.config.summary_path).resolve()
        workspace = workspace.resolve()
        if workspace not in path.parents or not path.is_file():
            raise PhysicalFlowError(
                f"physical summary was not generated: {self.config.summary_path}"
            )
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise PhysicalFlowError(f"invalid physical summary: {exc}") from exc
        if not isinstance(document, dict):
            raise PhysicalFlowError("physical summary must be a JSON object")
        return document

    def collect_artifacts(self, workspace: Path) -> list[dict[str, Any]]:
        workspace = workspace.resolve()
        result: list[dict[str, Any]] = []
        seen: set[str] = set()
        for pattern in self.config.artifact_globs:
            for path in sorted(workspace.glob(pattern)):
                if not path.is_file():
                    continue
                resolved = path.resolve()
                if workspace not in resolved.parents:
                    continue
                relative = path.relative_to(workspace).as_posix()
                if relative in seen:
                    continue
                seen.add(relative)
                result.append({
                    "source": path,
                    "path": relative,
                    "kind": classify_artifact(relative),
                    "size": str(path.stat().st_size),
                    "sha256": _sha256_file(path),
                })
        return result

    def layout_launch(
        self, gds: Path
    ) -> tuple[list[str], dict[str, str]]:
        state = self.inspect_environment()
        if not state["tools"].get("klayout", {}).get("path"):
            raise PhysicalFlowError("KLayout is not available")
        tool_root = Path(state["toolchain_root"]) if state["toolchain_root"] else None
        executable = Path(state["tools"]["klayout"]["path"])
        env = os.environ.copy()
        for name in ("LD_PRELOAD", "QT_PLUGIN_PATH", "QT_QPA_PLATFORM_PLUGIN_PATH"):
            env.pop(name, None)
        if tool_root:
            bundled = tool_root / "klayout-root" / "usr" / "bin" / "klayout"
            deps = tool_root / "deps-root" / "usr" / "lib" / "x86_64-linux-gnu"
            if bundled.is_file():
                executable = bundled
                env["LD_LIBRARY_PATH"] = ":".join([
                    str(tool_root / "klayout-root" / "usr" / "lib" / "klayout"),
                    str(deps), str(deps / "pulseaudio"),
                ])
                env["RUBYLIB"] = ":".join([
                    str(tool_root / "deps-root" / "usr" / "lib" / "ruby" / "3.0.0"),
                    str(deps / "ruby" / "3.0.0"),
                ])
        if env.get("DISPLAY"):
            env["QT_QPA_PLATFORM"] = "xcb"
            system_plugins = Path("/usr/lib/x86_64-linux-gnu/qt5/plugins")
            if system_plugins.is_dir():
                env["QT_PLUGIN_PATH"] = str(system_plugins)
                env["QT_QPA_PLATFORM_PLUGIN_PATH"] = str(system_plugins / "platforms")
        args = [str(executable)]
        flow_home = Path(state["orfs"]["flow_home"]) if state["orfs"]["flow_home"] else None
        if flow_home:
            layers = flow_home / "platforms" / self.config.platform / f"{self.config.platform}.lyp"
            if layers.is_file():
                args.extend(["-l", str(layers)])
        args.append(str(gds.resolve()))
        return args, env

    def _toolchain_root(self) -> Path | None:
        candidates: list[Path] = []
        configured = self.config.toolchain_root or os.environ.get(
            "CHIP_NEBULA_RTL2GDS_TOOL_ROOT", ""
        )
        if configured:
            candidate = Path(configured).expanduser()
            candidates.append(
                candidate if candidate.is_absolute() else self.project_root / candidate
            )
        candidates.extend([
            self.project_root / "build" / "rtl2gds-tools",
            Path(__file__).resolve().parents[3] / "build" / "rtl2gds-tools",
            Path.home() / ".cache" / "chip-nebula" / "rtl2gds-tools",
        ])
        # Source checkouts and unpacked developer packages can sit below the
        # repository that owns the optional multi-gigabyte tool bundle.  The
        # packaged backend's ``__file__`` and ``sys.executable`` are both
        # stable anchors even when the selected RTL project is elsewhere.
        candidates.extend(_ancestor_toolchain_candidates(Path(__file__).resolve()))
        candidates.extend(_ancestor_toolchain_candidates(Path(sys.executable).resolve()))
        # AppImage extracts both Electron and the backend below a transient
        # /tmp/.mount_* directory.  APPIMAGE retains the original executable
        # path, which lets a development AppImage find the repository-adjacent
        # optional tool bundle just like the unpacked package does.
        appimage = os.environ.get("APPIMAGE", "").strip()
        if appimage:
            candidates.extend(
                _ancestor_toolchain_candidates(Path(appimage).expanduser().resolve())
            )
        for candidate in candidates:
            if candidate.is_dir():
                return candidate.resolve()
        return candidates[0].resolve() if candidates and configured else None

    def _orfs_root(self, tool_root: Path | None) -> Path | None:
        configured = self.config.orfs_root or os.environ.get("ORFS_ROOT", "")
        candidates: list[Path] = []
        if configured:
            candidate = Path(configured).expanduser()
            candidates.append(
                candidate if candidate.is_absolute() else self.project_root / candidate
            )
        if tool_root:
            candidates.append(tool_root / "OpenROAD-flow-scripts")
        for candidate in candidates:
            if _orfs_flow_home(candidate):
                return candidate.resolve()
        return candidates[0].resolve() if candidates and configured else None

    def _expected_versions(self) -> dict[str, str]:
        path = self.project_root / self.config.workdir / self.config.tool_versions_file
        if not path.is_file():
            return {}
        result: dict[str, str] = {}
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            match = re.fullmatch(r"([A-Z0-9_]+)=(.*)", line.strip())
            if match:
                result[match.group(1)] = match.group(2).strip().strip("'\"")
        return result


def classify_artifact(relative: str) -> str:
    path = Path(relative)
    suffix = path.suffix.lower()
    name = path.name.lower()
    if suffix == ".gds":
        return "layout"
    if suffix in {".v", ".sv"}:
        return "netlist"
    if suffix in {".vcd", ".fst"}:
        return "waveform"
    if name == "run-summary.json":
        return "physical_summary"
    if suffix in {".def", ".odb", ".spef", ".sdc", ".lvsdb", ".cdl"}:
        return "physical_database"
    return "report"


def _which(environment_name: str, candidates: tuple[Path, ...], command: str) -> Path | None:
    configured = os.environ.get(environment_name, "")
    if configured:
        path = Path(configured).expanduser()
        if path.is_file() and os.access(path, os.X_OK):
            return path.resolve()
    for path in candidates:
        if path.is_file() and os.access(path, os.X_OK):
            return path.resolve()
    found = shutil.which(command)
    return Path(found).resolve() if found else None


def _tool_version(path: Path, flag: str) -> str:
    try:
        result = subprocess.run(
            # Rootless container startup can exceed 10s on a shared host.
            [str(path), flag], capture_output=True, text=True, timeout=60,
            errors="replace",
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    output = (result.stdout or result.stderr).strip()
    return output.splitlines()[0][:500] if output else ""


def _orfs_flow_home(root: Path | None) -> Path | None:
    if not root:
        return None
    if (root / "flow" / "Makefile").is_file():
        return root / "flow"
    if (root / "Makefile").is_file() and root.name == "flow":
        return root
    return None


def _git_commit(root: Path | None) -> str:
    if not root:
        return ""
    if (root / ".git").exists():
        try:
            result = subprocess.run(
                ["git", "-C", str(root), "rev-parse", "HEAD"],
                capture_output=True, text=True, timeout=5,
            )
        except (OSError, subprocess.TimeoutExpired):
            result = None
        if result is not None and result.returncode == 0:
            return result.stdout.strip()
    try:
        revision = (root / "ORFS_REVISION").read_text(encoding="utf-8").strip()
    except OSError:
        return ""
    return revision if re.fullmatch(r"[0-9a-f]{40}", revision) else ""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()
