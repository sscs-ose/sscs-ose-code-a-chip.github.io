"""Frozen-CSIR contract gate for a generated, independent RTL module.

This gate proves that a real HDL frontend elaborated the requested top and
that its external ports match the frozen interface. It deliberately makes no
functional-verification or physical-signoff claim.
"""

from __future__ import annotations

import json
import re
import shlex
import shutil
import subprocess
import threading
import xml.etree.ElementTree as ET
from dataclasses import asdict
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from chip_nebula.taskgraph.tool_executor import DeterministicToolExecutor, ToolCommand


_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_$]*\Z")
_XML_PATH = "build/chip-nebula-generation/design.xml"
_JSON_PATH = "build/chip-nebula-generation/design.json"
_JSON_META_PATH = "build/chip-nebula-generation/design.meta.json"


class GenericRTLContractError(ValueError):
    """The specification cannot be used for this generation gate."""


def generation_target(spec: Mapping[str, Any]) -> str:
    document = spec.get("document", {})
    if not isinstance(document, Mapping) or document.get("design_kind") != "generic_module":
        raise GenericRTLContractError("当前规格不是通用 RTL 模块")
    if not spec.get("configured") or not spec.get("valid") or not spec.get("frozen"):
        raise GenericRTLContractError("必须先检查并冻结有效的通用 CSIR 规格")
    if document.get("instances"):
        raise GenericRTLContractError(
            "该通用规格含 IP 实例；顶层须由 IP Integration 确定性装配，不能由设计 Agent 重写"
        )
    name = document.get("name")
    if not isinstance(name, str) or not _IDENTIFIER.fullmatch(name):
        raise GenericRTLContractError("规格顶层模块名无效")
    source = document.get("rtl_source", f"rtl/{name}.sv")
    path = PurePosixPath(source) if isinstance(source, str) else None
    if (
        not isinstance(source, str) or not source or "\\" in source
        or path is None or path.is_absolute()
        or any(part in {"", ".", ".."} for part in source.split("/"))
        or path.suffix.lower() not in {".v", ".sv"}
    ):
        raise GenericRTLContractError("冻结规格绑定的 RTL 源文件路径无效")
    return source


def generation_sources(spec: Mapping[str, Any]) -> list[str]:
    """Return the frozen compile order, with the top source present exactly once."""
    top = generation_target(spec)
    sources = spec["document"].get("rtl_sources")
    if sources is None:
        return [top]
    if (
        not isinstance(sources, list) or not 1 <= len(sources) <= 256
        or any(
            not isinstance(item, str) or not item or "\\" in item
            or "\x00" in item or PurePosixPath(item).is_absolute()
            or any(part in {"", ".", ".."} for part in item.split("/"))
            or PurePosixPath(item).suffix.lower() not in {".v", ".sv"}
            for item in sources
        )
        or len(set(sources)) != len(sources) or sources.count(top) != 1
    ):
        raise GenericRTLContractError("冻结规格的 RTL 编译清单无效或未包含顶层")
    return list(sources)


def generation_options(spec: Mapping[str, Any]) -> tuple[list[str], list[str]]:
    """Return frozen include paths and defines for standalone RTL."""
    generation_target(spec)
    document = spec["document"]
    include_dirs = document.get("rtl_include_dirs")
    defines = document.get("rtl_defines")
    include_dirs = [] if include_dirs is None else include_dirs
    defines = [] if defines is None else defines
    if (
        not isinstance(include_dirs, list) or len(include_dirs) > 64
        or any(
            not isinstance(item, str) or not item or "\\" in item
            or PurePosixPath(item).is_absolute()
            or any(part in {"", ".", ".."} for part in item.split("/"))
            for item in include_dirs
        )
        or len(set(include_dirs)) != len(include_dirs)
        or not isinstance(defines, list) or len(defines) > 128
        or any(
            not isinstance(item, str)
            or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*(?:=[^\s\x00]+)?", item)
            for item in defines
        )
        or len(set(defines)) != len(defines)
    ):
        raise GenericRTLContractError("冻结规格中的 Include 目录或宏定义无效")
    return list(include_dirs), list(defines)


def generation_include_files(root: Path, spec: Mapping[str, Any]) -> list[str]:
    """Inventory all files under frozen include directories for input binding."""
    directories, _ = generation_options(spec)
    root = root.resolve()
    headers: set[str] = set()
    for relative in directories:
        directory = root / relative
        try:
            if directory.resolve() != directory or directory.is_symlink() or not directory.is_dir():
                raise GenericRTLContractError(f"Include 目录缺失或经过符号链接：{relative}")
            for entry in directory.rglob("*"):
                if entry.is_symlink() and entry.is_dir():
                    raise GenericRTLContractError(f"Include 子目录不能是符号链接：{entry.relative_to(root)}")
                if entry.is_dir():
                    continue
                if entry.resolve() != entry or entry.is_symlink() or not entry.is_file():
                    raise GenericRTLContractError(f"Include 输入无效或经过符号链接：{entry.relative_to(root)}")
                headers.add(entry.relative_to(root).as_posix())
                if len(headers) > 4096:
                    raise GenericRTLContractError("Include 目录文件超过 4096 个，请收敛目录")
        except OSError as exc:
            raise GenericRTLContractError(f"无法读取 Include 目录 {relative}：{exc}") from exc
    return sorted(headers)


def elaboration_command(
    spec: Mapping[str, Any], *, parameters: Mapping[str, int] | None = None,
    ast_format: str = "xml",
) -> str:
    document = spec["document"]
    values = {
        item["name"]: item["default"]
        for item in document.get("parameters", [])
        if isinstance(item, dict) and isinstance(item.get("name"), str)
        and type(item.get("default")) is int
    }
    for name, value in (parameters or {}).items():
        if name not in values or type(value) is not int:
            raise GenericRTLContractError(f"未声明或无效的顶层参数：{name}")
        values[name] = value
    if ast_format not in {"xml", "json"}:
        raise GenericRTLContractError("不支持的 Verilator 展开格式")
    args = [
        "verilator", "--xml-only" if ast_format == "xml" else "--json-only",
        "--sv", "-Wall", "-Wno-fatal",
        "--top-module", str(document["name"]),
        "--xml-output" if ast_format == "xml" else "--json-only-output",
        _XML_PATH if ast_format == "xml" else _JSON_PATH,
        *(["--json-only-meta-output", _JSON_META_PATH] if ast_format == "json" else []),
        *[f"-G{name}={value}" for name, value in sorted(values.items())],
        *[f"-I{item}" for item in generation_options(spec)[0]],
        *[f"-D{item}" for item in generation_options(spec)[1]],
        *generation_sources(spec),
    ]
    return shlex.join(args)


def xml_artifact_path() -> str:
    return _XML_PATH


def ast_artifact_path(ast_format: str) -> str:
    return _JSON_PATH if ast_format == "json" else _XML_PATH


def verilator_ast_format(executable: str | None = None) -> str:
    """Select the AST format supported by the actual Verilator executable."""
    selected = executable or shutil.which("verilator")
    if not selected:
        raise GenericRTLContractError("Verilator 未安装，无法检查接口契约")
    try:
        result = subprocess.run(
            [selected, "--version"], capture_output=True, text=True,
            timeout=5, errors="replace",
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise GenericRTLContractError(f"无法查询 Verilator 版本：{exc}") from exc
    match = re.search(r"Verilator\s+(\d+)[.]", result.stdout or result.stderr)
    if not match:
        raise GenericRTLContractError("无法识别 Verilator 版本，不能选择安全的展开格式")
    return "json" if int(match.group(1)) >= 5 else "xml"


def inspect_elaboration(
    ast_path: Path, spec: Mapping[str, Any], *,
    parameters: Mapping[str, int] | None = None,
) -> dict[str, Any]:
    """Compare Verilator's elaborated top port set with the CSIR contract."""
    generation_target(spec)
    document = spec["document"]
    values = {
        item["name"]: item["default"]
        for item in document.get("parameters", [])
        if isinstance(item, dict) and isinstance(item.get("name"), str)
        and type(item.get("default")) is int
    }
    values.update(parameters or {})
    expected: dict[str, dict[str, Any]] = {}
    for item in document.get("ports", []):
        width = item.get("width", 1)
        if isinstance(width, str):
            width = values.get(width)
        if type(width) is not int or width < 1:
            raise GenericRTLContractError(
                f"无法确定端口 {item.get('name', '')} 的精确位宽"
            )
        expected[str(item["name"])] = {
            "direction": str(item["direction"]), "width": width,
        }
    try:
        observed = (
            _observed_json(ast_path, str(document["name"]))
            if ast_path.suffix == ".json"
            else _observed_xml(ast_path, str(document["name"]))
        )
    except (OSError, ET.ParseError, json.JSONDecodeError, ValueError, TypeError) as exc:
        return {
            "verdict": "failed", "diagnostics": [f"HDL 展开 AST 缺失或无效：{exc}"],
            "expected_ports": expected, "observed_ports": {},
        }
    diagnostics: list[str] = []
    for name in sorted(set(expected) | set(observed)):
        if name not in expected:
            diagnostics.append(f"RTL 出现规格外端口：{name}")
        elif name not in observed:
            diagnostics.append(f"RTL 缺少规格端口：{name}")
        elif observed[name] != expected[name]:
            diagnostics.append(
                f"端口 {name} 不匹配：规格 {expected[name]}，RTL {observed[name]}"
            )
    return {
        "verdict": "passed" if not diagnostics else "failed",
        "diagnostics": diagnostics,
        "expected_ports": expected,
        "observed_ports": observed,
    }


def _observed_xml(path: Path, top: str) -> dict[str, dict[str, Any]]:
    root = ET.parse(path).getroot()
    modules = [item for item in root.iter("module") if item.get("topModule") == "1"]
    if len(modules) != 1 or modules[0].get("origName") != top:
        raise ValueError("HDL 展开顶层与冻结规格不一致")
    dtypes = {
        item.get("id"): item for item in root.iter()
        if item.tag.endswith("dtype") and item.get("id")
    }
    observed: dict[str, dict[str, Any]] = {}
    for variable in modules[0].findall("var"):
        direction = variable.get("dir")
        if direction not in {"input", "output", "inout"}:
            continue
        observed[str(variable.get("origName") or variable.get("name"))] = {
            "direction": direction,
            "width": _dtype_width(dtypes.get(variable.get("dtype_id"))),
        }
    return observed


def _observed_json(path: Path, top: str) -> dict[str, dict[str, Any]]:
    document = json.loads(path.read_text(encoding="utf-8"))
    modules = [
        item for item in document.get("modulesp", [])
        if isinstance(item, dict) and item.get("level") == 1
    ]
    if len(modules) != 1 or modules[0].get("origName") != top:
        raise ValueError("HDL 展开顶层与冻结规格不一致")
    type_tables = [
        item for item in document.get("miscsp", [])
        if isinstance(item, dict) and item.get("type") == "TYPETABLE"
    ]
    if len(type_tables) != 1:
        raise ValueError("Verilator JSON 缺少唯一类型表")
    dtypes = {
        item.get("addr"): item for item in type_tables[0].get("typesp", [])
        if isinstance(item, dict) and item.get("addr")
    }
    observed: dict[str, dict[str, Any]] = {}
    for variable in modules[0].get("stmtsp", []):
        if not isinstance(variable, dict) or variable.get("type") != "VAR":
            continue
        if variable.get("isPrimaryIO") is not True:
            continue
        direction = str(variable.get("direction", "")).lower()
        if direction not in {"input", "output", "inout"}:
            continue
        observed[str(variable.get("origName") or variable.get("name"))] = {
            "direction": direction,
            "width": _json_dtype_width(dtypes.get(variable.get("dtypep"))),
        }
    return observed


def _json_dtype_width(dtype: dict[str, Any] | None) -> int | None:
    if not isinstance(dtype, dict) or dtype.get("type") != "BASICDTYPE":
        return None
    value = dtype.get("range")
    if value is None:
        return 1
    if not isinstance(value, str) or not re.fullmatch(r"-?\d+:-?\d+", value):
        return None
    left, right = map(int, value.split(":"))
    return abs(left - right) + 1


def _dtype_width(dtype: ET.Element | None) -> int | None:
    if dtype is None or dtype.tag != "basicdtype":
        return None
    left, right = dtype.get("left"), dtype.get("right")
    if left is None and right is None:
        return 1
    try:
        return abs(int(left or "") - int(right or "")) + 1
    except ValueError:
        return None


def verify_generated_rtl(
    workspace: Path, spec: Mapping[str, Any], *,
    parameters: Mapping[str, int] | None = None,
    timeout: int = 900,
    stop_event: threading.Event | None = None,
) -> dict[str, Any]:
    """Run real Verilator elaboration and inspect its top interface."""
    sources = generation_sources(spec)
    try:
        generation_include_files(workspace, spec)
    except GenericRTLContractError as exc:
        return {
            "status": "not_started", "verdict": "failed",
            "diagnostics": [str(exc)], "command_evidence": [],
            "tool_versions": {}, "log": "",
        }
    invalid = [
        item for item in sources
        if (workspace / item).resolve() != workspace.resolve() / item
        or (workspace / item).is_symlink()
        or not (workspace / item).is_file()
        or not (workspace / item).stat().st_size
    ]
    if invalid:
        return {
            "status": "not_started", "verdict": "failed",
            "diagnostics": ["必需的 RTL 编译文件缺失或不是工程内普通非空文件：" + "、".join(invalid)],
            "command_evidence": [], "tool_versions": {}, "log": "",
        }
    ast_format = verilator_ast_format()
    command = elaboration_command(spec, parameters=parameters, ast_format=ast_format)
    (workspace / Path(ast_artifact_path(ast_format)).parent).mkdir(parents=True, exist_ok=True)
    result = DeterministicToolExecutor(stop_event=stop_event).execute(
        workspace, [ToolCommand("generic-rtl-elaboration", command, timeout=timeout)],
    )
    report: dict[str, Any] = {
        "status": result.status,
        "verdict": "failed",
        "diagnostics": [],
        "command_evidence": [asdict(item) for item in result.commands],
        "tool_versions": result.tool_versions,
        "log": result.log,
    }
    if result.status != "succeeded" or result.verdict != "passed":
        report["verdict"] = (
            result.status if result.status in {"stopped", "timeout", "launch_failed"}
            else "failed"
        )
        report["diagnostics"] = [
            result.commands[-1].reason or "Verilator 展开失败；请查看完整工具日志"
        ]
        return report
    contract = inspect_elaboration(
        workspace / ast_artifact_path(ast_format), spec, parameters=parameters,
    )
    report.update(contract)
    report["ast_format"] = ast_format
    report["ast_path"] = ast_artifact_path(ast_format)
    return report
