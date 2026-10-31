"""Deterministic project discovery and a versionable ORFS flow scaffold."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import math
from pathlib import Path, PurePosixPath
import re
import shlex
import subprocess
from typing import Any, Mapping

import yaml

from chip_nebula.project import project_definition_files


class PhysicalProjectError(RuntimeError):
    """Raised when a project cannot be turned into a reviewed physical flow."""


_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_$]*$")
_CLOCK_NAME = re.compile(r"(^|_)(p?clk|clock)(_|$)", re.IGNORECASE)
_EXCLUDED_PARTS = {
    ".git", ".chip_nebula", "build", "validation", "node_modules",
    "tb", "tbench", "test", "tests", "sim", "simulation",
}


@dataclass(frozen=True)
class PhysicalProjectSelection:
    top_module: str
    clock_port: str
    clock_period_ns: float
    platform: str
    simulation_command: str
    top_parameters: dict[str, int] = field(default_factory=dict)


def normalize_top_parameters(value: Any) -> dict[str, int]:
    """Validate the supported, deterministic subset of top-level parameters."""
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise PhysicalProjectError("顶层参数必须是名称到整数值的对象")
    result: dict[str, int] = {}
    for raw_name, raw_value in value.items():
        name = str(raw_name).strip()
        if not _IDENTIFIER.fullmatch(name):
            raise PhysicalProjectError(f"顶层参数名不是合法的 Verilog 标识符：{name}")
        if isinstance(raw_value, bool) or not isinstance(raw_value, int):
            raise PhysicalProjectError(f"顶层参数 {name} 当前只支持整数值")
        if not -(2**63) <= raw_value < 2**63:
            raise PhysicalProjectError(f"顶层参数 {name} 超出 64 位整数范围")
        result[name] = raw_value
    return dict(sorted(result.items()))


class PhysicalProjectWizard:
    """Inspect files without running project code, then generate a reviewed flow."""

    def __init__(self, project_root: Path) -> None:
        self.root = project_root.resolve()

    def detect(
        self, *, configured_top: str = "", simulation_command: str = "",
        declared_sources: list[str] | None = None,
        declared_include_dirs: list[str] | None = None,
        declared_defines: list[str] | None = None,
        declared_filelists: list[str] | None = None,
        configured_top_parameters: Mapping[str, int] | None = None,
    ) -> dict[str, Any]:
        diagnostics: list[dict[str, str]] = []
        graph = self._read_json_with_diagnostics(
            "graph/source.json", diagnostics, "GRAPH_SOURCE_INVALID"
        )
        sources, source_authority = self._declared_sources(
            diagnostics, declared_sources, graph
        )
        filelist_includes: list[str] = []
        filelist_defines: list[str] = []
        filelists = (
            declared_filelists if declared_filelists is not None
            else [source_authority] if source_authority.endswith((".f", ".flist"))
            else []
        )
        for relative in filelists:
            filelist = self.root / relative
            if declared_filelists is not None:
                self._filelist_sources(filelist, diagnostics)
            includes, defines = self._filelist_compile_options(filelist, diagnostics)
            filelist_includes.extend(includes)
            filelist_defines.extend(defines)
            if includes or defines:
                diagnostics.append({
                    "severity": "warning", "code": "FILELIST_OPTIONS_DETECTED",
                    "message": (
                        f"从 {relative} 读取 {len(includes)} 个 Include 目录、"
                        f"{len(defines)} 个宏定义；请在 Project Settings 核对后保存"
                    ),
                })
        include_dirs = self._include_dirs(
            sources, [*(declared_include_dirs or []), *filelist_includes], diagnostics,
        )
        effective_defines = list(dict.fromkeys([
            *(declared_defines or []), *filelist_defines,
        ]))
        define_values: dict[str, str] = {}
        for value in effective_defines:
            name = value.split("=", 1)[0]
            if name in define_values and define_values[name] != value:
                diagnostics.append({
                    "severity": "error", "code": "FILELIST_DEFINE_CONFLICT",
                    "message": f"宏 {name} 在 Project Settings 与 filelist 中有不同取值，请先确定一个版本",
                })
            define_values[name] = value
        included_headers = self._included_headers(
            [item for item in sources if Path(item).suffix.lower() in {".v", ".sv"}],
            include_dirs, diagnostics,
        )
        source_prefix = {
            "workbench fileset": "WORKBENCH_FILESET",
            "graph/source.json": "GRAPH_SOURCE",
            "metadata.json": "METADATA_RTL",
        }.get(source_authority, "")
        input_issues = [
            item for item in diagnostics
            if item.get("code", "").startswith("INCLUDE_")
            or (source_prefix and item.get("code", "").startswith(source_prefix)
                and item.get("code", "").endswith((
                    "_FILE_MISSING", "_UNSAFE_PATH", "_INVALID_ENTRY",
                )))
            or ((source_authority.endswith((".f", ".flist")) or filelists)
                and item.get("code", "").startswith("FILELIST_")
                and item.get("severity") == "error")
        ]
        for item in input_issues:
            item["severity"] = "error"
        modules, instantiated = self._scan_modules(sources)
        graph_tops = self._graph_tops(graph, diagnostics)
        top_names = [name for name in graph_tops if name in modules]
        if not top_names:
            top_names = sorted(set(modules) - instantiated) or sorted(modules)
        if configured_top and configured_top in modules:
            top_names = [configured_top, *[name for name in top_names if name != configured_top]]
        configured_parameters = normalize_top_parameters(configured_top_parameters or {})
        top_candidates = []
        for name in top_names:
            inputs = modules.get(name, {}).get("inputs", [])
            clocks = [port for port in inputs if _CLOCK_NAME.search(port)]
            top_candidates.append({
                "name": name,
                "source": modules.get(name, {}).get("source", ""),
                "input_ports": inputs,
                "vector_input_ports": modules.get(name, {}).get(
                    "vector_inputs", []
                ),
                "clock_candidates": clocks,
                "detected_parameters": self._top_parameters_from_scripts(name),
            })
        suggested_top = configured_top if configured_top in top_names else (
            top_names[0] if len(top_names) == 1 else ""
        )
        selected = next(
            (item for item in top_candidates if item["name"] == suggested_top), None
        )
        suggested_top_parameters = (
            configured_parameters
            if configured_parameters
            else dict(selected.get("detected_parameters", {})) if selected else {}
        )
        if suggested_top_parameters and not configured_parameters:
            diagnostics.append({
                "severity": "warning", "code": "TOP_PARAMETERS_DETECTED",
                "message": (
                    "已从只读工程脚本识别顶层参数，请确认后保存："
                    + "、".join(
                        f"{name}={value}"
                        for name, value in suggested_top_parameters.items()
                    )
                ),
            })
        memory_images = self._memory_image_parameters(selected, diagnostics)
        suggested_clock = ""
        if selected and len(selected["clock_candidates"]) == 1:
            suggested_clock = selected["clock_candidates"][0]
        simulation_candidates = self._simulation_candidates(simulation_command)
        if not sources:
            diagnostics.append({
                "severity": "error", "code": "NO_RTL_SOURCES",
                "message": "没有找到可用于综合的 Verilog/SystemVerilog 源文件。",
            })
        if len(top_names) != 1 and not configured_top:
            diagnostics.append({
                "severity": "warning", "code": "TOP_REVIEW_REQUIRED",
                "message": (
                    f"检测到 {len(top_names)} 个候选顶层，请人工选择："
                    + "、".join(top_names)
                ),
            })
        if suggested_top and selected and len(selected["clock_candidates"]) > 1:
            diagnostics.append({
                "severity": "error", "code": "MULTIPLE_CLOCKS_UNSUPPORTED",
                "message": (
                    "检测到多个时钟端口："
                    + "、".join(selected["clock_candidates"])
                    + "。当前物理向导只支持单时钟设计，已阻止生成错误约束。"
                ),
            })
        elif suggested_top and selected and not selected["clock_candidates"]:
            diagnostics.append({
                "severity": "warning", "code": "CLOCK_REVIEW_REQUIRED",
                "message": "未识别出时钟端口，请人工选择并确认周期。",
            })
        suggested_clock_period_ns = 10.0
        existing_definition = self._read_json_with_diagnostics(
            "physical/chip-nebula/flow-definition.json", diagnostics,
            "FLOW_DEFINITION_INVALID",
        )
        if existing_definition:
            existing_clock = existing_definition.get("clock")
            try:
                existing_period = float(existing_clock.get("period_ns"))
            except (AttributeError, TypeError, ValueError):
                existing_period = 0.0
            if (
                existing_definition.get("top_module") == suggested_top
                and isinstance(existing_clock, dict)
                and existing_clock.get("port") == suggested_clock
                and 0.01 <= existing_period <= 1_000_000
            ):
                suggested_clock_period_ns = existing_period
        return {
            "schema_version": 1,
            "source_authority": source_authority,
            "sources": sources,
            "include_dirs": include_dirs,
            "filelist_include_dirs": list(dict.fromkeys(filelist_includes)),
            "included_headers": included_headers,
            "input_issues": input_issues,
            "defines": effective_defines,
            "top_candidates": top_candidates,
            "suggested_top": suggested_top,
            "suggested_clock": suggested_clock,
            "suggested_clock_period_ns": suggested_clock_period_ns,
            "suggested_top_parameters": suggested_top_parameters,
            "memory_images": memory_images,
            "simulation_candidates": simulation_candidates,
            "suggested_simulation_command": (
                simulation_command or (simulation_candidates[0] if simulation_candidates else "")
            ),
            "platforms": ["sky130hd"],
            "diagnostics": diagnostics,
            "ready_for_review": bool(
                sources and top_names and not input_issues
                and not (selected and len(selected["clock_candidates"]) > 1)
            ),
        }

    def configure(
        self,
        selection: PhysicalProjectSelection,
        *,
        configured_top: str = "",
        current_simulation_command: str = "",
        declared_sources: list[str] | None = None,
        declared_include_dirs: list[str] | None = None,
        declared_defines: list[str] | None = None,
        declared_filelists: list[str] | None = None,
        configured_top_parameters: Mapping[str, int] | None = None,
        environment: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        detection = self.detect(
            configured_top=configured_top,
            simulation_command=current_simulation_command,
            declared_sources=declared_sources,
            declared_include_dirs=declared_include_dirs,
            declared_defines=declared_defines,
            declared_filelists=declared_filelists,
            configured_top_parameters=(
                selection.top_parameters or configured_top_parameters or {}
            ),
        )
        top_parameters = normalize_top_parameters(selection.top_parameters)
        if detection["input_issues"]:
            raise PhysicalProjectError(
                "物理输入清单不完整：" + "；".join(
                    item["message"] for item in detection["input_issues"]
                )
            )
        candidates = {
            item["name"]: item for item in detection["top_candidates"]
        }
        if selection.top_module not in candidates:
            raise PhysicalProjectError("所选顶层不在当前 RTL 候选列表中")
        if not _IDENTIFIER.fullmatch(selection.clock_port):
            raise PhysicalProjectError("时钟端口必须是合法的 Verilog 标识符")
        candidate = candidates[selection.top_module]
        input_ports = candidate["input_ports"]
        if input_ports and selection.clock_port not in input_ports:
            raise PhysicalProjectError("所选时钟不是该顶层的输入端口")
        clock_candidates = candidate["clock_candidates"]
        if len(clock_candidates) > 1:
            raise PhysicalProjectError(
                "当前物理向导只支持单时钟设计；检测到多个时钟端口："
                + "、".join(clock_candidates)
                + "。请等待多时钟约束支持或提供已审核的自定义物理流程。"
            )
        if len(clock_candidates) == 1 and selection.clock_port != clock_candidates[0]:
            raise PhysicalProjectError(
                f"检测到的唯一时钟端口为 {clock_candidates[0]}，不能将其他输入作为时钟"
            )
        if not (0.01 <= float(selection.clock_period_ns) <= 1_000_000):
            raise PhysicalProjectError("时钟周期必须位于 0.01 ns 到 1 ms 之间")
        if selection.platform != "sky130hd":
            raise PhysicalProjectError("当前向导只支持已验证的 sky130hd 平台")
        if not selection.simulation_command.strip():
            raise PhysicalProjectError("完整流程需要选择或填写功能仿真命令")

        if any(item.get("severity") == "error" and item.get("code") == "MEMORY_IMAGE_INVALID"
               for item in detection["diagnostics"]):
            raise PhysicalProjectError("ROM 初始化文件缺失或路径无效；请修复后重新探测")
        synthesis_preflight = self._synthesis_preflight(
            selection.top_module, top_parameters, detection, environment or {},
        )
        relative_root = Path("physical") / "chip-nebula"
        output = self.root / relative_root
        output.mkdir(parents=True, exist_ok=True)
        sources = list(detection["sources"])
        include_dirs = list(detection["include_dirs"])
        defines = list(detection["defines"])
        compilation_units = [
            path for path in sources
            if Path(path).suffix.lower() in {".v", ".sv"}
        ]
        headers = list(dict.fromkeys([
            path for path in sources
            if Path(path).suffix.lower() in {".vh", ".svh"}
        ] + detection["included_headers"]))
        definition = {
            "schema_version": 1,
            "generator": "chip-nebula-physical-project-v1",
            "source_authority": detection["source_authority"],
            "top_module": selection.top_module,
            "top_parameters": top_parameters,
            "memory_images": detection["memory_images"],
            "sources": sources,
            "compilation_units": compilation_units,
            "headers": headers,
            "include_dirs": include_dirs,
            "defines": defines,
            "clock": {
                "port": selection.clock_port,
                "period_ns": float(selection.clock_period_ns),
                "constraint_status": "user-confirmed exploratory constraint",
            },
            "platform": selection.platform,
            "synthesis_frontend": synthesis_preflight["frontend"],
            "synthesis_preflight": {
                key: synthesis_preflight[key]
                for key in ("status", "frontend", "tool_version", "reason")
                if synthesis_preflight.get(key)
            },
            "simulation_command": selection.simulation_command.strip(),
        }
        self._write_json(output / "flow-definition.json", definition)
        (output / "constraints.sdc").write_text(
            _render_sdc(
                selection.top_module, selection.clock_port,
                float(selection.clock_period_ns),
                input_ports,
                candidates[selection.top_module].get("vector_input_ports", []),
            ),
            encoding="utf-8",
        )
        (output / "config.mk").write_text(
            _render_config_mk(
                selection.top_module, compilation_units, include_dirs, defines,
                selection.platform, top_parameters, detection["memory_images"],
            ),
            encoding="utf-8",
        )
        runner = output / "run.sh"
        runner.write_text(
            _render_runner(selection.top_module, selection.simulation_command),
            encoding="utf-8",
        )
        runner.chmod(0o755)
        template_root = Path(__file__).resolve().parents[1] / "configs" / "examples" / "rtl-to-gds-counter"
        for name in ("prepare_orfs.py", "inspect_gds.py", "filter_lvs_cdl.py", "klayout.sh"):
            source = template_root / name
            if not source.is_file():
                raise PhysicalProjectError(f"安装包缺少物理流程模板：{name}")
            (output / name).write_bytes(source.read_bytes())
            if name == "klayout.sh":
                (output / name).chmod(0o755)
        (output / "tool-versions.env").write_text(
            _render_tool_versions(environment or {}), encoding="utf-8"
        )
        (output / "README.md").write_text(
            _render_readme(definition), encoding="utf-8"
        )
        generated_files = [
            (relative_root / name).as_posix()
            for name in (
                "flow-definition.json", "constraints.sdc", "config.mk", "run.sh",
                "prepare_orfs.py", "inspect_gds.py", "filter_lvs_cdl.py",
                "klayout.sh", "tool-versions.env", "README.md",
            )
        ]
        input_globs = list(dict.fromkeys([
            *sources, *headers, *detection["memory_images"].values(),
            "physical/chip-nebula/**", "Makefile", "tb/**", "tbench/**",
            "scripts/**", "graph/source.json", "metadata.json", "**/*.f",
            "**/*.flist", "ip/nebula.lock.json", "spec/design.csir.yaml",
        ]))
        return {
            "detection": detection,
            "synthesis_preflight": synthesis_preflight,
            "definition": definition,
            "generated_files": generated_files,
            "config_patch": {
                "top_module": selection.top_module,
                "top_parameters": top_parameters,
                "source_globs": sources,
                "simulation_command": selection.simulation_command.strip(),
                "lint_command": _lint_command(
                    selection.top_module, compilation_units, include_dirs, defines,
                    top_parameters,
                ),
                "physical": {
                    "enabled": True,
                    "command": "bash physical/chip-nebula/run.sh {mode}",
                    "workdir": ".",
                    "timeout": 14_400,
                    "platform": selection.platform,
                    "design": selection.top_module,
                    "flow_variant": "nebula",
                    "num_cores": 2,
                    "output_root": "build/rtl-to-gds",
                    "summary_path": "build/rtl-to-gds/run-summary.json",
                    "input_globs": input_globs,
                    "required_inputs": list(dict.fromkeys([
                        *sources, *headers, *detection["memory_images"].values(),
                        *generated_files[:9],
                    ])),
                    "tool_versions_file": "physical/chip-nebula/tool-versions.env",
                },
            },
        }

    def _memory_image_parameters(
        self, candidate: Mapping[str, Any] | None,
        diagnostics: list[dict[str, str]],
    ) -> dict[str, str]:
        """Bind top-level readmemh filename parameters to snapshotted project files.

        ORFS invokes Yosys from its own flow directory. A relative ROM filename
        that works in simulation otherwise fails during synthesis elaboration.
        Only a literal project-relative default tied to a named readmemh
        parameter is supported; dynamic paths need an explicit future contract.
        """
        if not candidate:
            return {}
        source = self.root / str(candidate.get("source", ""))
        try:
            text = _without_comments(source.read_text(encoding="utf-8"))
        except OSError:
            return {}
        module = re.search(
            rf"\bmodule\s+{re.escape(str(candidate['name']))}\b(.*?)\bendmodule\b",
            text, re.DOTALL,
        )
        if not module:
            return {}
        body = module.group(1)
        result: dict[str, str] = {}
        for match in re.finditer(
            r'\bparameter\s+(?:string\s+)?([A-Za-z_][A-Za-z0-9_$]*)\s*=\s*"([^"\n]+)"',
            body,
        ):
            name, relative = match.groups()
            if not re.search(rf"\$readmemh\s*\(\s*{re.escape(name)}\s*,", body):
                continue
            path = PurePosixPath(relative)
            if (
                path.is_absolute() or ".." in path.parts
                or not re.fullmatch(r"[A-Za-z0-9_./-]+", relative)
                or not (self.root / path).is_file()
                or (self.root / path).resolve() != self.root / path
            ):
                diagnostics.append({
                    "severity": "error", "code": "MEMORY_IMAGE_INVALID",
                    "message": f"ROM 初始化参数 {name} 的工程文件无效：{relative}",
                })
                continue
            result[name] = path.as_posix()
        return dict(sorted(result.items()))

    def _synthesis_preflight(
        self, top_module: str, top_parameters: Mapping[str, int],
        detection: Mapping[str, Any],
        environment: Mapping[str, Any],
    ) -> dict[str, str]:
        """Read and elaborate the selected design with the configured frontend."""
        sources = [
            str(value) for value in detection.get("sources", [])
            if Path(str(value)).suffix.lower() in {".v", ".sv"}
        ]
        frontend = (
            "slang" if detection.get("memory_images")
            or any(Path(value).suffix.lower() == ".sv" for value in sources)
            else "read_verilog"
        )
        tool = environment.get("tools", {}).get("yosys", {})
        executable = str(tool.get("path", "")) if isinstance(tool, Mapping) else ""
        version = str(tool.get("version", "")) if isinstance(tool, Mapping) else ""
        if not executable or not Path(executable).is_file():
            return {
                "status": "skipped", "frontend": frontend,
                "tool_version": version,
                "reason": "Yosys 尚未安装，保存流程后需在运行前完成环境检查",
            }

        include_dirs = [str(value) for value in detection.get("include_dirs", [])]
        defines = [str(value) for value in detection.get("defines", [])]
        if frontend == "slang":
            image_parameters = {
                name: f'"{self.root / relative}"'
                for name, relative in detection.get("memory_images", {}).items()
            }
            words = [
                "read_slang", "--ignore-assertions", "--top", top_module,
                *[
                    value for name, parameter in {**top_parameters, **image_parameters}.items()
                    for value in ("-G", f"{name}={parameter}")
                ],
                *[value for directory in include_dirs for value in ("-I", directory)],
                *[value for define in defines for value in ("-D", define)],
                *sources,
            ]
        else:
            words = [
                "read_verilog", "-sv", "-defer",
                *[value for directory in include_dirs for value in ("-I", directory)],
                *[value for define in defines for value in ("-D", define)],
                *sources,
            ]
        if any(
            not re.fullmatch(r'[A-Za-z0-9_.$/+=:@,"-]+', value)
            for value in words
        ):
            return {
                "status": "skipped", "frontend": frontend,
                "tool_version": version,
                "reason": (
                    "源码路径或宏包含 Yosys 预检脚本无法安全转义的字符；"
                    "正式运行仍会使用生成的版本化流程"
                ),
            }
        script = " ".join(words)
        if frontend != "slang":
            for name, value in top_parameters.items():
                script += f"; chparam -set {name} {value} {top_module}"
        script += "; hierarchy -check -top " + top_module
        try:
            result = subprocess.run(
                [executable, "-Q", "-p", script], cwd=self.root,
                capture_output=True, text=True, errors="replace", timeout=90,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise PhysicalProjectError(f"综合前端预检无法完成：{exc}") from exc
        output = "\n".join(
            value.strip() for value in (result.stdout, result.stderr) if value.strip()
        )
        if result.returncode != 0:
            tail = "\n".join(output.splitlines()[-20:])[-4_000:]
            raise PhysicalProjectError(
                f"综合前端预检失败（{frontend}，顶层 {top_module}）：\n{tail}"
            )
        return {
            "status": "passed", "frontend": frontend,
            "tool_version": version,
            "reason": "精确源码集合与顶层已通过只读展开检查",
            "log_tail": "\n".join(output.splitlines()[-10:])[-2_000:],
        }

    def existing_flow_issues(
        self, configured_top: str,
        configured_top_parameters: Mapping[str, int] | None = None,
    ) -> list[str]:
        """Reject stale v1 generated constraints before they can be executed."""
        definition = self._read_json("physical/chip-nebula/flow-definition.json")
        if not definition or definition.get("generator") != "chip-nebula-physical-project-v1":
            return []
        configured_sources: list[str] | None = None
        configured_include_dirs: list[str] | None = None
        configured_defines: list[str] | None = None
        if definition.get("source_authority") == "workbench fileset":
            configured = self._configured_fileset()
            if configured is None:
                return ["已生成的物理流程依赖结构化 Fileset，但当前工程配置已缺失"]
            configured_sources, configured_include_dirs, configured_defines = configured
        detection = self.detect(
            configured_top=configured_top,
            declared_sources=configured_sources,
            declared_include_dirs=configured_include_dirs,
            declared_defines=configured_defines,
        )
        if detection["input_issues"]:
            return list(dict.fromkeys(
                item["message"] for item in detection["input_issues"]
            ))
        top = str(definition.get("top_module", ""))
        candidate = next(
            (item for item in detection["top_candidates"] if item["name"] == top),
            None,
        )
        if candidate is None:
            return ["已生成的物理流程与当前 RTL 顶层不兼容，请重新探测并生成流程"]

        issues: list[str] = []
        generated_parameters = definition.get("top_parameters", {})
        try:
            generated_parameters = normalize_top_parameters(generated_parameters)
        except PhysicalProjectError:
            issues.append("已生成的物理流程顶层参数无效，请重新探测并生成流程")
            generated_parameters = {}
        if configured_top_parameters is not None:
            current_parameters = normalize_top_parameters(configured_top_parameters)
            if generated_parameters != current_parameters:
                issues.append("已生成的物理流程顶层参数已过期，请重新探测并生成流程")
        if definition.get("memory_images", {}) != detection.get("memory_images", {}):
            issues.append("ROM 初始化输入已变化，请重新探测并生成物理流程")
        current_sources = set(detection.get("sources", []))
        generated_sources = definition.get("sources", [])
        if not isinstance(generated_sources, list) or set(generated_sources) != current_sources:
            issues.append("已生成的物理流程源码集合已过期，请重新探测并生成流程")
        if set(definition.get("include_dirs", [])) != set(detection.get("include_dirs", [])):
            issues.append("已生成的物理流程 include 目录已过期，请重新探测并生成流程")
        if set(definition.get("defines", [])) != set(detection.get("defines", [])):
            issues.append("已生成的物理流程宏定义已过期，请重新探测并生成流程")
        preflight = definition.get("synthesis_preflight")
        if isinstance(preflight, dict) and preflight.get("status") != "passed":
            issues.append(
                "已生成流程尚未通过综合前端预检，请在工具就绪后重新探测并生成流程"
            )
        compilation_units = definition.get("compilation_units", [])
        if (
            isinstance(compilation_units, list)
            and (definition.get("memory_images") or any(
                Path(str(value)).suffix.lower() == ".sv"
                for value in compilation_units
            ))
        ):
            config_path = self.root / "physical/chip-nebula/config.mk"
            config_text = (
                config_path.read_text(encoding="utf-8", errors="replace")
                if config_path.is_file() else ""
            )
            if not re.search(
                r"(?m)^\s*export\s+SYNTH_HDL_FRONTEND\s*=\s*slang\s*$",
                config_text,
            ):
                issues.append(
                    "SystemVerilog 综合输入需要 Slang frontend，请重新生成物理流程"
                )
        config_path = self.root / "physical/chip-nebula/config.mk"
        config_text = (
            config_path.read_text(encoding="utf-8", errors="replace")
            if config_path.is_file() else ""
        )
        platform_match = re.search(
            r"(?m)^[ \t]*export[ \t]+PLATFORM[ \t]*=[ \t]*([^#\s]+)[ \t]*$",
            config_text,
        )
        if not platform_match or platform_match.group(1) != definition.get("platform"):
            issues.append("生成的 ORFS 平台与流程定义不一致，请重新生成物理流程")
        expected_sdc = (
            "$(NEBULA_PROJECT_ROOT)/physical/chip-nebula/constraints.sdc"
        )
        sdc_match = re.search(
            r"(?m)^[ \t]*export[ \t]+SDC_FILE[ \t]*=[ \t]*([^#\r\n]+)$",
            config_text,
        )
        if not sdc_match or sdc_match.group(1).strip() != expected_sdc:
            issues.append(
                "生成的 ORFS 约束路径与流程定义不一致，请重新生成物理流程"
            )
        parameter_match = re.search(
            r"(?m)^[ \t]*export[ \t]+VERILOG_TOP_PARAMS[ \t]*=[ \t]*(.*?)[ \t]*$",
            config_text,
        )
        expected_parameter_words = _render_top_parameter_words(
            generated_parameters, definition.get("memory_images", {}),
        )
        if not parameter_match or parameter_match.group(1).strip() != expected_parameter_words:
            issues.append("生成的 ORFS 顶层参数与流程定义不一致，请重新生成物理流程")

        clocks = candidate.get("clock_candidates", [])
        generated_clock = definition.get("clock", {})
        clock_port = (
            str(generated_clock.get("port", ""))
            if isinstance(generated_clock, dict) else ""
        )
        if len(clocks) > 1:
            issues.append(
                "已生成的物理流程不再安全：当前顶层检测到多个时钟端口（"
                + "、".join(clocks)
                + "），单时钟 SDC 已失效"
            )
        elif len(clocks) == 1 and clock_port != clocks[0]:
            issues.append(
                f"已生成的物理流程时钟已失效：当前时钟为 {clocks[0]}，"
                f"流程记录为 {clock_port or '空'}"
            )

        sdc_path = self.root / "physical/chip-nebula/constraints.sdc"
        if clock_port and sdc_path.is_file():
            sdc_text = sdc_path.read_text(encoding="utf-8", errors="replace")
            constrained = _sdc_clock_ports(sdc_text)
            if clock_port not in constrained:
                issues.append(
                    f"已生成的 SDC 没有为记录的时钟端口 {clock_port} 创建时钟"
                )
            periods = _sdc_clock_periods(sdc_text)
            try:
                expected_period = float(generated_clock["period_ns"])
            except (TypeError, ValueError, KeyError):
                expected_period = 0.0
            if len(periods) != 1 or abs(periods[0] - expected_period) > 1e-9:
                issues.append("已生成的 SDC 时钟周期与流程定义不一致，请重新生成物理流程")
        return list(dict.fromkeys(issues))

    def _configured_fileset(self) -> tuple[list[str], list[str], list[str]] | None:
        config_path = self._workbench_config_path()
        if not config_path.is_file():
            return None
        try:
            document = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError):
            return None
        if not isinstance(document, dict) or document.get("validation_mode") != "fileset":
            return None
        diagnostics: list[dict[str, str]] = []
        sources = self._safe_sources(document.get("design_files", []))
        filelist_includes: list[str] = []
        filelist_defines: list[str] = []
        for relative in document.get("filelists", []):
            if not isinstance(relative, str):
                continue
            path = self.root / relative
            if path.is_file():
                sources.extend(self._filelist_sources(path, diagnostics))
                includes, defines = self._filelist_compile_options(path, diagnostics)
                filelist_includes.extend(includes)
                filelist_defines.extend(defines)
        include_dirs = [
            value for value in document.get("include_dirs", [])
            if isinstance(value, str)
        ]
        defines = [
            value for value in document.get("defines", [])
            if isinstance(value, str)
        ]
        return (
            list(dict.fromkeys(sources)),
            list(dict.fromkeys([*include_dirs, *filelist_includes])),
            list(dict.fromkeys([*defines, *filelist_defines])),
        )

    def _workbench_config_path(self) -> Path:
        manifests = project_definition_files(self.root)
        if len(manifests) == 1:
            try:
                project = yaml.safe_load(
                    manifests[0].read_text(encoding="utf-8")
                ) or {}
            except (OSError, yaml.YAMLError):
                project = {}
            workbench = project.get("workbench", {}) if isinstance(project, dict) else {}
            for key in ("config", "template"):
                value = workbench.get(key) if isinstance(workbench, dict) else None
                if not isinstance(value, str):
                    continue
                relative = PurePosixPath(value.replace("\\", "/"))
                if relative.is_absolute() or ".." in relative.parts:
                    continue
                candidate = self.root / relative.as_posix()
                if candidate.is_file():
                    return candidate
        configured = self.root / ".chip_nebula/workbench.yaml"
        return configured if configured.is_file() else self.root / "workbench.yaml"

    def _declared_sources(
        self, diagnostics: list[dict[str, str]], declared: list[str] | None = None,
        graph: dict[str, Any] | None = None,
    ) -> tuple[list[str], str]:
        if declared is not None:
            sources = self._safe_sources(
                declared, diagnostics, "WORKBENCH_FILESET"
            )
            return sources, "workbench fileset"
        if graph is not None:
            if isinstance(graph.get("source_files"), list):
                sources = self._safe_sources(
                    graph["source_files"], diagnostics, "GRAPH_SOURCE"
                )
                return sources, "graph/source.json"
            else:
                diagnostics.append({
                    "severity": "warning", "code": "GRAPH_SOURCE_SCHEMA",
                    "message": "graph/source.json 的 source_files 必须是文件列表，已改用其他探测依据。",
                })
        metadata = self._read_json_with_diagnostics(
            "metadata.json", diagnostics, "METADATA_INVALID"
        )
        if metadata is not None:
            if isinstance(metadata.get("rtl_files"), list):
                sources = self._safe_sources(
                    metadata["rtl_files"], diagnostics, "METADATA_RTL"
                )
                return sources, "metadata.json"
            else:
                diagnostics.append({
                    "severity": "warning", "code": "METADATA_SCHEMA",
                    "message": "metadata.json 的 rtl_files 必须是文件列表，已改用其他探测依据。",
                })
        filelists = sorted(
            [*self.root.glob("**/*.f"), *self.root.glob("**/*.flist")],
            key=lambda path: (
                path.relative_to(self.root).as_posix() != "integration/nebula.f",
                path.relative_to(self.root).as_posix(),
            ),
        )
        for filelist in filelists:
            if any(part in _EXCLUDED_PARTS for part in filelist.relative_to(self.root).parts):
                continue
            before = len(diagnostics)
            sources = self._filelist_sources(filelist, diagnostics)
            if sources or len(diagnostics) > before:
                return sources, filelist.relative_to(self.root).as_posix()
        paths = []
        for suffix in ("*.sv", "*.v"):
            for path in self.root.rglob(suffix):
                relative = path.relative_to(self.root)
                if any(part in _EXCLUDED_PARTS for part in relative.parts):
                    continue
                paths.append(relative.as_posix())
        return sorted(dict.fromkeys(paths)), "filesystem fallback"

    def _safe_sources(
        self, values: list[Any],
        diagnostics: list[dict[str, str]] | None = None,
        code_prefix: str = "SOURCE",
    ) -> list[str]:
        result = []
        for value in values:
            if not isinstance(value, str):
                if diagnostics is not None:
                    diagnostics.append({
                        "severity": "warning", "code": f"{code_prefix}_INVALID_ENTRY",
                        "message": f"源码列表包含非字符串条目：{value!r}",
                    })
                continue
            candidate = PurePosixPath(value.replace("\\", "/"))
            if candidate.is_absolute() or ".." in candidate.parts:
                if diagnostics is not None:
                    diagnostics.append({
                        "severity": "warning", "code": f"{code_prefix}_UNSAFE_PATH",
                        "message": f"源码路径必须位于工程内，已忽略：{value}",
                    })
                continue
            path = self.root / candidate
            try:
                resolved = path.resolve()
            except (OSError, RuntimeError):
                resolved = None
            if resolved is not None and self.root not in resolved.parents:
                if diagnostics is not None:
                    diagnostics.append({
                        "severity": "error", "code": f"{code_prefix}_UNSAFE_PATH",
                        "message": f"源码路径通过符号链接越出工程：{candidate.as_posix()}",
                    })
                continue
            if not path.is_file():
                if diagnostics is not None:
                    diagnostics.append({
                        "severity": "warning", "code": f"{code_prefix}_FILE_MISSING",
                        "message": f"登记的源码文件不存在，已忽略：{candidate.as_posix()}",
                    })
                continue
            if path.suffix.lower() not in {".v", ".sv", ".vh", ".svh"}:
                if diagnostics is not None:
                    diagnostics.append({
                        "severity": "warning", "code": f"{code_prefix}_UNSUPPORTED_FILE",
                        "message": f"登记文件不是 Verilog/SystemVerilog，已忽略：{candidate.as_posix()}",
                    })
                continue
            result.append(candidate.as_posix())
        return list(dict.fromkeys(result))

    def _filelist_compile_options(
        self, filelist: Path, diagnostics: list[dict[str, str]],
    ) -> tuple[list[str], list[str]]:
        """Read only the bounded +incdir+ and +define+ subset from a filelist."""
        if filelist.is_symlink() or not filelist.is_file() or not filelist.resolve().is_relative_to(self.root):
            diagnostics.append({
                "severity": "error", "code": "FILELIST_UNSAFE_PATH",
                "message": f"filelist 不在工程内或经过符号链接：{filelist}",
            })
            return [], []
        includes: list[str] = []
        defines: list[str] = []
        for raw in filelist.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw.strip()
            if line.startswith("+incdir+"):
                values = line[len("+incdir+"):].split("+")
                for value in values:
                    candidate = PurePosixPath(value)
                    directory = self.root / candidate
                    if (
                        not value or chr(92) in value or any(c.isspace() for c in value)
                        or candidate.is_absolute() or any(part in {"", ".", ".."} for part in value.split("/"))
                        or directory.is_symlink() or not directory.is_dir()
                        or directory.resolve() != directory
                    ):
                        diagnostics.append({
                            "severity": "error", "code": "FILELIST_INCLUDE_INVALID",
                            "message": f"filelist 的 Include 目录缺失或不安全：{value!r}",
                        })
                    elif candidate.as_posix() not in includes:
                        includes.append(candidate.as_posix())
            elif line.startswith("+define+"):
                values = line[len("+define+"):].split("+")
                for value in values:
                    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*(?:=[^\s\x00+]+)?", value):
                        diagnostics.append({
                            "severity": "error", "code": "FILELIST_DEFINE_INVALID",
                            "message": f"filelist 的宏定义无效：{value!r}",
                        })
                    elif value not in defines:
                        defines.append(value)
        return includes, defines

    def _filelist_sources(
        self, filelist: Path, diagnostics: list[dict[str, str]],
    ) -> list[str]:
        result = []
        base = filelist.parent
        if filelist.is_symlink() or not filelist.is_file() or not filelist.resolve().is_relative_to(self.root):
            diagnostics.append({
                "severity": "error", "code": "FILELIST_UNSAFE_PATH",
                "message": f"filelist 缺失、不在工程内或经过符号链接：{filelist}",
            })
            return []
        for raw in filelist.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw.strip()
            if not line or line.startswith(("#", "//")):
                continue
            if line.startswith(("+incdir+", "+define+")):
                continue
            if line.startswith(("-", "+")):
                diagnostics.append({
                    "severity": "error", "code": "FILELIST_DIRECTIVE_UNSUPPORTED",
                    "message": (
                        f"filelist 指令尚未纳入物理输入清单：{line}；"
                        "请改用结构化 Fileset 声明源码、include 目录和宏定义"
                    ),
                })
                continue
            candidate = Path(line)
            # -f is normally evaluated from the tool working directory
            # (the project root). Retain nested-filelist relative paths as
            # a fallback for existing projects.
            candidates = (
                [candidate] if candidate.is_absolute()
                else [self.root / candidate, base / candidate]
            )
            found = False
            for path in candidates:
                try:
                    relative = path.resolve().relative_to(self.root)
                except (OSError, RuntimeError, ValueError):
                    continue
                if path.is_file() and path.suffix.lower() in {".v", ".sv", ".vh", ".svh"}:
                    result.append(relative.as_posix())
                    found = True
                    break
            if not found:
                diagnostics.append({
                    "severity": "error", "code": "FILELIST_SOURCE_MISSING",
                    "message": f"filelist 登记的工程内源码缺失或无效：{line}",
                })
        return list(dict.fromkeys(result))

    def _scan_modules(
        self, sources: list[str],
    ) -> tuple[dict[str, dict[str, Any]], set[str]]:
        modules: dict[str, dict[str, Any]] = {}
        instantiated: set[str] = set()
        for relative in sources:
            path = self.root / relative
            if path.suffix.lower() not in {".v", ".sv"}:
                continue
            text = _without_comments(path.read_text(encoding="utf-8", errors="replace"))
            for match in re.finditer(
                r"\bmodule\s+([A-Za-z_][A-Za-z0-9_$]*)\b(.*?)\bendmodule\b",
                text, re.DOTALL,
            ):
                name, body = match.group(1), match.group(2)
                inputs, vector_inputs = _input_port_details(body)
                modules[name] = {
                    "source": relative,
                    "inputs": inputs,
                    "vector_inputs": vector_inputs,
                }
                for instance in re.finditer(
                    r"(?:^|[;])\s*([A-Za-z_][A-Za-z0-9_$]*)\s*(?:#\s*\([^;]*?\)\s*)?"
                    r"[A-Za-z_][A-Za-z0-9_$]*\s*\(",
                    body, re.MULTILINE | re.DOTALL,
                ):
                    instantiated.add(instance.group(1))
        return modules, instantiated

    def order_compilation_units(self, sources: list[str]) -> list[str]:
        """Place files defining instantiated modules before their parents.

        The order from a reviewed filelist remains authoritative elsewhere;
        this helper is used for proposals derived from metadata or a filesystem
        scan, where the listed order is often only an inventory.
        """
        units = [
            source for source in sources
            if Path(source).suffix.lower() in {".v", ".sv"}
        ]
        source_index = {source: index for index, source in enumerate(units)}
        module_sources: dict[str, str] = {}
        source_instances: dict[str, list[str]] = {source: [] for source in units}
        instance_pattern = re.compile(
            r"(?:^|[;])\s*([A-Za-z_][A-Za-z0-9_$]*)\s*(?:#\s*\([^;]*?\)\s*)?"
            r"[A-Za-z_][A-Za-z0-9_$]*\s*\(",
            re.MULTILINE | re.DOTALL,
        )
        for relative in units:
            text = _without_comments(
                (self.root / relative).read_text(encoding="utf-8", errors="replace")
            )
            for match in re.finditer(
                r"\bmodule\s+([A-Za-z_][A-Za-z0-9_$]*)\b(.*?)\bendmodule\b",
                text, re.DOTALL,
            ):
                module_sources[match.group(1)] = relative
                source_instances[relative].extend(
                    item.group(1) for item in instance_pattern.finditer(match.group(2))
                )
        dependencies: dict[str, set[str]] = {source: set() for source in units}
        for source, instances in source_instances.items():
            for module_name in instances:
                dependency = module_sources.get(module_name)
                if dependency and dependency != source:
                    dependencies[source].add(dependency)
        ordered: list[str] = []
        remaining = set(units)
        while remaining:
            ready = sorted(
                (
                    source for source in remaining
                    if not (dependencies[source] & remaining)
                ),
                key=source_index.__getitem__,
            )
            if not ready:
                return units
            for source in ready:
                remaining.remove(source)
                ordered.append(source)
        return ordered

    def _graph_tops(
        self, graph: dict[str, Any] | None,
        diagnostics: list[dict[str, str]],
    ) -> list[str]:
        graph = graph or {}
        semantic = graph.get("semantic_elaboration", {})
        if semantic not in ({}, None) and not isinstance(semantic, dict):
            diagnostics.append({
                "severity": "warning", "code": "GRAPH_SEMANTIC_SCHEMA",
                "message": "graph/source.json 的 semantic_elaboration 必须是对象，已忽略顶层提示。",
            })
            return []
        values = semantic.get("top_instances", []) if isinstance(semantic, dict) else []
        if values and not isinstance(values, list):
            diagnostics.append({
                "severity": "warning", "code": "GRAPH_TOPS_SCHEMA",
                "message": "graph/source.json 的 top_instances 必须是列表，已从 RTL 层次推断顶层。",
            })
            return []
        return [value for value in values if isinstance(value, str)]

    def _include_dirs(
        self, sources: list[str], declared: list[str] | None = None,
        diagnostics: list[dict[str, str]] | None = None,
    ) -> list[str]:
        result = {str(PurePosixPath(path).parent) for path in sources}
        for value in declared or []:
            candidate = PurePosixPath(value.replace("\\", "/"))
            path = self.root / candidate
            try:
                resolved = path.resolve()
            except (OSError, RuntimeError):
                resolved = None
            unsafe = (
                candidate.is_absolute() or ".." in candidate.parts
                or resolved is not None and resolved != self.root
                and self.root not in resolved.parents
            )
            if unsafe:
                if diagnostics is not None:
                    diagnostics.append({
                        "severity": "error", "code": "INCLUDE_DIR_UNSAFE",
                        "message": f"include 目录越出工程：{value}",
                    })
                continue
            if not path.is_dir():
                if diagnostics is not None:
                    diagnostics.append({
                        "severity": "error", "code": "INCLUDE_DIR_MISSING",
                        "message": f"登记的 include 目录缺失：{value}",
                    })
                continue
            result.add(candidate.as_posix())
        for path in self.root.rglob("*"):
            if path.is_file() and path.suffix.lower() in {".vh", ".svh"}:
                relative = path.relative_to(self.root)
                if not any(part in _EXCLUDED_PARTS for part in relative.parts):
                    try:
                        resolved = path.resolve()
                    except (OSError, RuntimeError):
                        continue
                    if self.root in resolved.parents:
                        result.add(relative.parent.as_posix())
        result.discard(".")
        return sorted(result)

    def _simulation_candidates(self, configured: str) -> list[str]:
        result = [configured.strip()] if configured.strip() else []
        for relative in ("scripts/run.sh", "run.sh"):
            if (self.root / relative).is_file():
                result.append(f"bash {relative}")
        makefile = self.root / "Makefile"
        if makefile.is_file():
            text = makefile.read_text(encoding="utf-8", errors="replace")
            for target in ("test", "sim", "simulation", "regression"):
                if re.search(rf"(?m)^{re.escape(target)}\s*:", text):
                    result.append(f"make {target}")
        return list(dict.fromkeys(result))

    def _included_headers(
        self, compilation_units: list[str], include_dirs: list[str],
        diagnostics: list[dict[str, str]] | None = None,
    ) -> list[str]:
        """Resolve literal project-local Verilog includes, including recursion."""
        result: list[str] = []
        queue = list(compilation_units)
        visited: set[str] = set()
        reported: set[tuple[str, str]] = set()
        while queue:
            relative = queue.pop(0)
            if relative in visited:
                continue
            visited.add(relative)
            path = self.root / relative
            if not path.is_file():
                continue
            text = _without_comments(
                path.read_text(encoding="utf-8", errors="replace")
            )
            for literal in re.findall(r"`include\s+\"([^\"\r\n]+)\"", text):
                include = PurePosixPath(literal.replace("\\", "/"))
                if include.is_absolute() or ".." in include.parts:
                    code = "INCLUDE_PATH_UNSAFE"
                    message = f"{relative} 引用工程外 include 路径：{literal}"
                    if diagnostics is not None and (code, message) not in reported:
                        diagnostics.append({"severity": "error", "code": code, "message": message})
                        reported.add((code, message))
                    continue
                candidates = [PurePosixPath(relative).parent / include]
                candidates.extend(PurePosixPath(directory) / include for directory in include_dirs)
                resolved = ""
                for candidate in candidates:
                    path = self.root / candidate.as_posix()
                    try:
                        target = path.resolve()
                    except (OSError, RuntimeError):
                        continue
                    if path.is_file() and self.root in target.parents:
                        resolved = candidate.as_posix()
                        break
                if not resolved:
                    code = "INCLUDE_FILE_MISSING"
                    message = f"{relative} 引用的 include 缺失或越界：{literal}"
                    if diagnostics is not None and (code, message) not in reported:
                        diagnostics.append({"severity": "error", "code": code, "message": message})
                        reported.add((code, message))
                    continue
                if resolved in result:
                    continue
                result.append(resolved)
                queue.append(resolved)
        return result

    def _top_parameters_from_scripts(self, top_module: str) -> dict[str, int]:
        """Read literal Verilator ``-G`` overrides without executing scripts."""
        candidates = [self.root / "scripts" / "run.sh", self.root / "run.sh"]
        candidates.extend(sorted(self.root.glob("scripts/**/*.sh")))
        makefile = self.root / "Makefile"
        if makefile.is_file():
            candidates.append(makefile)
        for path in dict.fromkeys(candidates):
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8", errors="replace")[:2_000_000]
            # Join ordinary shell continuation lines, then inspect only literal
            # Verilator invocations. Dynamic variables and command substitutions
            # are deliberately ignored because the proposal must be reviewable.
            logical = re.sub(r"\\\r?\n", " ", text)
            for raw_line in logical.splitlines():
                if "--top-module" not in raw_line or "-G" not in raw_line:
                    continue
                try:
                    words = shlex.split(raw_line, comments=True)
                except ValueError:
                    continue
                selected_top = ""
                parameters: dict[str, int] = {}
                for index, word in enumerate(words):
                    if word == "--top-module" and index + 1 < len(words):
                        selected_top = words[index + 1]
                    elif word.startswith("--top-module="):
                        selected_top = word.split("=", 1)[1]
                    if not word.startswith("-G") or "=" not in word[2:]:
                        continue
                    name, literal = word[2:].split("=", 1)
                    if not _IDENTIFIER.fullmatch(name):
                        continue
                    try:
                        value = (
                            int(literal, 10)
                            if re.fullmatch(r"[+-]?\d+", literal)
                            else int(literal, 0)
                        )
                    except ValueError:
                        continue
                    if -(2**63) <= value < 2**63:
                        parameters[name] = value
                if selected_top == top_module and parameters:
                    return normalize_top_parameters(parameters)
        return {}

    def _read_json(self, relative: str) -> dict[str, Any] | None:
        path = self.root / relative
        if not path.is_file():
            return None
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return value if isinstance(value, dict) else None

    def _read_json_with_diagnostics(
        self, relative: str, diagnostics: list[dict[str, str]], code: str,
    ) -> dict[str, Any] | None:
        path = self.root / relative
        if not path.is_file():
            return None
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            diagnostics.append({
                "severity": "warning", "code": code,
                "message": f"无法解析 {relative}：{exc}。已改用其他探测依据。",
            })
            return None
        if not isinstance(value, dict):
            diagnostics.append({
                "severity": "warning", "code": code,
                "message": f"{relative} 必须是 JSON 对象，已改用其他探测依据。",
            })
            return None
        return value

    @staticmethod
    def _write_json(path: Path, value: Any) -> None:
        path.write_text(
            json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


def _without_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.DOTALL)
    return re.sub(r"//[^\n]*", " ", text)


def _input_port_details(module_body: str) -> tuple[list[str], list[str]]:
    result: list[str] = []
    vectors: list[str] = []
    for match in re.finditer(
        r"\binput\b\s*(?:(?:wire|logic|reg|signed|unsigned)\s+)*"
        r"(\[[^\]]+\]\s*)?([A-Za-z_][A-Za-z0-9_$]*)",
        module_body,
    ):
        name = match.group(2)
        result.append(name)
        if match.group(1):
            vectors.append(name)
    return list(dict.fromkeys(result)), list(dict.fromkeys(vectors))


def _render_sdc(
    top: str, clock: str, period: float,
    input_ports: list[str], vector_inputs: list[str],
) -> str:
    data_inputs = [
        f"{name}[*]" if name in vector_inputs else name
        for name in input_ports if name != clock
    ]
    lines = [
        f"current_design {top}",
        f"create_clock -name nebula_clock -period {period:g} [get_ports {{{clock}}}]",
        "set_clock_uncertainty 0.1 [get_clocks nebula_clock]",
    ]
    if data_inputs:
        lines.append(
            "set_input_delay 0.5 -clock nebula_clock [get_ports {"
            + " ".join(data_inputs) + "}]"
        )
    lines.extend(["set_output_delay 0.5 -clock nebula_clock [all_outputs]", ""])
    return "\n".join(lines)


def _sdc_clock_periods(text: str) -> list[float]:
    periods: list[float] = []
    for line in text.splitlines():
        if not re.match(r"\s*create_clock\b", line):
            continue
        match = re.search(
            r"(?:^|\s)-period\s+([0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?)\b",
            line,
        )
        if not match:
            continue
        period = float(match.group(1))
        if math.isfinite(period) and period > 0:
            periods.append(period)
    return periods


def _sdc_clock_ports(text: str) -> list[str]:
    ports: list[str] = []
    for line in text.splitlines():
        if not re.search(r"\bcreate_clock\b", line):
            continue
        match = re.search(r"\[get_ports\s+\{([^}]+)\}\]", line)
        if match:
            ports.extend(match.group(1).split())
            continue
        match = re.search(r"\[get_ports\s+([^\]\s]+)\]", line)
        if match:
            ports.append(match.group(1))
    return list(dict.fromkeys(ports))


def _render_top_parameter_words(
    top_parameters: Mapping[str, int], memory_images: Mapping[str, str],
) -> str:
    words = [
        f"{name} {value}"
        for name, value in normalize_top_parameters(top_parameters).items()
    ]
    for name, relative in sorted(memory_images.items()):
        if not _IDENTIFIER.fullmatch(name) or not re.fullmatch(r"[A-Za-z0-9_./-]+", relative):
            raise PhysicalProjectError("ROM 初始化参数或路径无效")
        words.append(f'{name} {{"$(NEBULA_PROJECT_ROOT)/{relative}"}}')
    return " ".join(words)


def _render_config_mk(
    top: str, sources: list[str], include_dirs: list[str], defines: list[str],
    platform: str, top_parameters: Mapping[str, int] | None = None,
    memory_images: Mapping[str, str] | None = None,
) -> str:
    source_words = " ".join(sources)
    include_words = " ".join(include_dirs)
    define_words = " ".join(f"-D {value}" for value in defines)
    parameter_words = _render_top_parameter_words(
        top_parameters or {}, memory_images or {},
    )
    frontend = (
        "export SYNTH_HDL_FRONTEND = slang"
        if memory_images or any(Path(source).suffix.lower() == ".sv" for source in sources)
        else ""
    )
    return "\n".join([
        "NEBULA_PROJECT_ROOT := $(abspath $(dir $(lastword $(MAKEFILE_LIST)))/../..)",
        f"export DESIGN_NAME = {top}",
        f"export DESIGN_NICKNAME = {top}",
        f"export PLATFORM = {platform}",
        f"export VERILOG_FILES = $(addprefix $(NEBULA_PROJECT_ROOT)/,{source_words})",
        f"export VERILOG_INCLUDE_DIRS = $(addprefix $(NEBULA_PROJECT_ROOT)/,{include_words})",
        f"export VERILOG_DEFINES = {define_words}",
        f"export VERILOG_TOP_PARAMS = {parameter_words}",
        frontend,
        "export SDC_FILE = $(NEBULA_PROJECT_ROOT)/physical/chip-nebula/constraints.sdc",
        "export CORE_UTILIZATION = 10", "export CORE_MARGIN = 10",
        "export PLACE_DENSITY = 0.55", "export ABC_AREA = 1",
        "export TNS_END_PERCENT = 100", "export SYNTH_REPEATABLE_BUILD = 1",
        "export SYNTH_MEMORY_MAX_BITS = 65536", "",
    ])


def _render_runner(top: str, simulation_command: str) -> str:
    template = (
        Path(__file__).resolve().parents[1]
        / "configs" / "examples" / "rtl-to-gds-counter" / "run.sh"
    ).read_text(encoding="utf-8")
    template = template.replace("nebula_counter", top)
    template = template.replace("build/rtl-to-gds-counter", "build/rtl-to-gds")
    template = template.replace(
        'variant="${FLOW_VARIANT:-smoke}"',
        'variant="${FLOW_VARIANT:-nebula}"',
    )
    replacement = "\n".join([
        "run_simulation() {",
        '    echo "CHIP_NEBULA_STAGE simulation"',
        '    mkdir -p "$work_root/simulation/build"',
        "    (",
        '        cd "$repo_root"',
        "        set -o pipefail",
        f"        bash -c {shlex.quote(simulation_command.strip())} 2>&1 | tee \"$work_root/simulation/build/simulation.log\"",
        '        printf \'%s\\n\' CHIP_NEBULA_SIMULATION_PASSED | tee -a "$work_root/simulation/build/simulation.log"',
        "    )",
        "}",
        "",
        "run_physical() {",
    ])
    template, count = re.subn(
        r"run_simulation\(\) \{.*?\n\}\n\nrun_physical\(\) \{",
        lambda _match: replacement,
        template,
        count=1,
        flags=re.DOTALL,
    )
    if count != 1:
        raise PhysicalProjectError("无法生成物理流程：运行模板结构不兼容")
    template = template.replace(
        'if [[ "$actual_orfs_commit" != "$ORFS_COMMIT" ]]; then',
        'if [[ -n "$ORFS_COMMIT" && "$actual_orfs_commit" != "$ORFS_COMMIT" ]]; then',
    )
    template = re.sub(
        r'if grep -Fq "PASS: .*? functional simulation" \\\n\s*"\$work_root/simulation/build/simulation\.log" 2>/dev/null; then',
        'if grep -Fq "CHIP_NEBULA_SIMULATION_PASSED" \\\n        "$work_root/simulation/build/simulation.log" 2>/dev/null; then',
        template,
        count=1,
    )
    return template


def _render_tool_versions(environment: Mapping[str, Any]) -> str:
    tools = environment.get("tools", {}) if isinstance(environment, Mapping) else {}
    values = {
        "ORFS_COMMIT": (
            environment.get("orfs", {}).get("commit", "")
            if isinstance(environment.get("orfs", {}), Mapping) else ""
        ),
        "YOSYS_VERSION": tools.get("yosys", {}).get("version", ""),
        "OPENROAD_VERSION": tools.get("openroad", {}).get("version", ""),
        "KLAYOUT_VERSION": tools.get("klayout", {}).get("version", ""),
    }
    return "".join(f"{key}={shlex.quote(str(value))}\n" for key, value in values.items())


def _lint_command(
    top: str, sources: list[str], include_dirs: list[str], defines: list[str],
    top_parameters: Mapping[str, int] | None = None,
) -> str:
    return shlex.join([
        "verilator", "--lint-only", "-Wall", "-Wno-fatal",
        "--top-module", top,
        *[
            f"-G{name}={value}"
            for name, value in normalize_top_parameters(top_parameters or {}).items()
        ],
        *[f"-I{path}" for path in include_dirs],
        *[f"-D{value}" for value in defines],
        *[path for path in sources if Path(path).suffix.lower() in {".v", ".sv"}],
    ])


def _render_readme(definition: Mapping[str, Any]) -> str:
    clock = definition["clock"]
    return (
        "# Chip Nebula generated physical flow\n\n"
        "This directory is a versionable, deterministic RTL-to-GDS definition generated "
        "after user review. Do not edit generated files silently; regenerate them from the "
        "desktop wizard when sources, top, clock, platform, or simulation command changes.\n\n"
        f"- Top: `{definition['top_module']}`\n"
        f"- Top parameters: `{definition.get('top_parameters', {})}`\n"
        f"- Clock: `{clock['port']}`, `{clock['period_ns']}` ns\n"
        f"- Platform: `{definition['platform']}`\n"
        "- Constraint scope: exploratory OpenROAD/Sky130 flow, not foundry sign-off\n"
    )
