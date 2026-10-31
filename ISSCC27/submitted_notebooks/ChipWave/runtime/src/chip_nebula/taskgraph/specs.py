"""CSIR v1 compiler and frozen specification workspace.

CSIR deliberately covers a bounded RTL subset.  Unsupported semantics become
blocking diagnostics instead of assumptions made by an Agent.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import re
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

import yaml

from chip_nebula.taskgraph.soc_adapter import SoCAdapterError, gpio_output_adapter


_ID = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]*$")
_SV_ID = re.compile(r"^[A-Za-z_][A-Za-z0-9_$]*$")
_ACCESS = {"RO", "RW", "W1C"}


# The first SoC release supports the exact reviewed register/behavior contracts
# of these two built-in APB peripherals. A different UART/timer must introduce a
# new explicit profile, not silently inherit a familiar capability label.
_SOC_PERIPHERAL_PROFILES: dict[str, dict[str, Any]] = {
    "apb-uart": {
        "kind": "uart_8n1",
        "registers": (
            ("DATA", 0x00, "RW"), ("STATUS", 0x04, "RO_W1C"),
            ("BAUD", 0x08, "RW"), ("CONTROL", 0x0C, "RW"),
        ),
        "behavior": {
            "framing": "8N1",
            "baud_divisor_min": 4,
            "baud_divisor_reset": 16,
            "rx_buffer_bytes": 1,
            "rx_read_clears_valid": True,
            "tx_busy_write": "pslverr",
            "status_error_clear": "w1c",
            "irq_sources": ["rx_valid", "rx_overflow", "frame_error"],
            "pprot": "ignored",
            "invalid_access": "pslverr",
        },
    },
    "apb-timer": {
        "kind": "timer_32",
        "registers": (
            ("CONTROL", 0x00, "RW"), ("PERIOD", 0x04, "RW"),
            ("COUNT", 0x08, "RO"), ("STATUS", 0x0C, "W1C"),
        ),
        "behavior": {
            "counter_width": 32,
            "modes": ["one_shot", "auto_reload"],
            "period_zero": "disabled",
            "count_access": "RO",
            "event_clear_priority": "set_over_clear",
            "irq_source": "status_and_enable",
            "pprot": "ignored",
            "invalid_access": "pslverr",
        },
    },
}


class SpecificationError(ValueError):
    pass


@dataclass(frozen=True)
class SpecDiagnostic:
    code: str
    severity: str
    path: str
    message: str
    blocking: bool = True


@dataclass(frozen=True)
class CompiledSpecification:
    document: dict[str, Any]
    spec_digest: str
    diagnostics: tuple[SpecDiagnostic, ...]
    interface_contract: dict[str, Any]
    acceptance_plan: dict[str, Any]
    register_markdown: str

    @property
    def valid(self) -> bool:
        return not any(item.blocking for item in self.diagnostics)

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "spec_digest": self.spec_digest,
            "diagnostics": [asdict(item) for item in self.diagnostics],
            "interface_contract": self.interface_contract,
            "acceptance_plan": self.acceptance_plan,
            "register_markdown": self.register_markdown,
            "document": self.document,
        }


class SpecCompiler:
    schema_version = 1

    def compile(self, source: Mapping[str, Any]) -> CompiledSpecification:
        if not isinstance(source, Mapping):
            raise SpecificationError("CSIR root must be a mapping")
        document = copy.deepcopy(dict(source))
        diagnostics: list[SpecDiagnostic] = []
        self._header(document, diagnostics)
        parameters = self._parameters(document, diagnostics)
        self._clock_reset(document, diagnostics)
        generic = document.get("design_kind") == "generic_module"
        interfaces = [] if generic else self._interfaces(document, diagnostics)
        if generic and document.get("interfaces", []) != []:
            self._add(diagnostics, "CSIR_GENERIC_INTERFACE", "interfaces",
                      "通用模块首期用 ports 描述接口信号；协议自动装配尚未实现")
        requirements = self._requirements(document, diagnostics)
        registers = [] if generic else self._registers(document, parameters, diagnostics)
        if generic and document.get("registers", []) != []:
            self._add(diagnostics, "CSIR_GENERIC_REGISTER", "registers",
                      "通用模块的内部状态由需求和验收描述；地址寄存器映射仅用于外设")
        self._ports(document, parameters, diagnostics)
        self._instances(document, diagnostics)
        peripheral_contracts = self._peripheral_contracts(document, interfaces, diagnostics)
        self._windows(document, diagnostics)
        memories = self._memories(document, diagnostics)
        self._behaviors(document, diagnostics)
        self._soc_contract(document, interfaces, diagnostics)
        if document.get("design_kind") == "single_clock_soc":
            try:
                gpio_output_adapter(document)
            except (SoCAdapterError, TypeError, ValueError, AttributeError) as exc:
                self._add(diagnostics, "CSIR_SOC_ADAPTER", "instances", str(exc))
        if generic:
            self._generic_module_contract(document, diagnostics)
        elif document.get("internal_signals"):
            self._add(diagnostics, "CSIR_GENERIC_SIGNAL", "internal_signals",
                      "显式内部信号目前仅用于通用具名端口 IP 装配")
        checks = self._acceptance(document, requirements, diagnostics)
        if generic:
            for index, check in enumerate(checks):
                if check.get("kind") == "lint":
                    self._add(
                        diagnostics, "CSIR_GENERIC_ACCEPTANCE_KIND",
                        f"acceptance[{index}].kind",
                        "通用模块的独立验收只支持 simulation/elaboration；Lint 请单独运行",
                    )
            if not any(check.get("kind") == "simulation" for check in checks):
                self._add(
                    diagnostics, "CSIR_GENERIC_SIMULATION", "acceptance",
                    "通用模块必须包含至少一个独立 simulation 验收项",
                )
        self._acceptance_sources(document, diagnostics)
        self._questions(document, diagnostics)
        digest = _digest(_semantic_document(document))
        contract = {
            "name": str(document.get("name", "")),
            "contract_version": digest,
            "endpoints": interfaces,
            "parameters": list(document.get("parameters", [])),
            "ports": list(document.get("ports", [])),
            "internal_signals": copy.deepcopy(document.get("internal_signals", [])) if generic else [],
            "registers": registers,
            "memories": memories,
            "peripheral_contracts": peripheral_contracts,
            "address_windows": list(document.get("address_windows", [])),
            "exceptions": copy.deepcopy(document.get("exceptions", {})),
            "cycle_constraints": copy.deepcopy(document.get("cycle_constraints", [])),
            "technical_target": copy.deepcopy(document.get("technical_target", {})),
        }
        plan = {
            "spec_digest": digest,
            "requirement_ids": sorted(requirements),
            "checks": checks,
        }
        return CompiledSpecification(
            document=document,
            spec_digest=digest,
            diagnostics=tuple(diagnostics),
            interface_contract=contract,
            acceptance_plan=plan,
            register_markdown=_register_markdown(document, registers),
        )

    @staticmethod
    def _add(
        diagnostics: list[SpecDiagnostic], code: str, path: str, message: str,
        *, severity: str = "error", blocking: bool = True,
    ) -> None:
        diagnostics.append(SpecDiagnostic(code, severity, path, message, blocking))

    def _header(self, doc: dict[str, Any], out: list[SpecDiagnostic]) -> None:
        if doc.get("schema_version") != self.schema_version:
            self._add(out, "CSIR_SCHEMA", "schema_version", "仅支持 CSIR schema_version: 1")
        for field in ("spec_id", "name", "demand"):
            value = doc.get(field)
            if not isinstance(value, str) or not value.strip():
                self._add(out, "CSIR_REQUIRED", field, f"缺少 {field}")
        if isinstance(doc.get("spec_id"), str) and not _ID.fullmatch(doc["spec_id"]):
            self._add(out, "CSIR_ID", "spec_id", "spec_id 必须是稳定的字母数字标识")
        if isinstance(doc.get("name"), str) and not _SV_ID.fullmatch(doc["name"]):
            self._add(out, "CSIR_NAME", "name", "name 必须是合法的 SystemVerilog 标识符")
        revision = doc.get("revision")
        if not isinstance(revision, int) or revision < 1:
            self._add(out, "CSIR_REVISION", "revision", "revision 必须是正整数")
        design_kind = doc.get("design_kind", "register_peripheral")
        if not isinstance(design_kind, str) or design_kind not in {
            "register_peripheral", "single_clock_soc", "generic_module",
        }:
            self._add(out, "CSIR_DESIGN_KIND", "design_kind", "不支持的设计类型")

    def _parameters(
        self, doc: dict[str, Any], out: list[SpecDiagnostic]
    ) -> dict[str, dict[str, Any]]:
        result: dict[str, dict[str, Any]] = {}
        raw = doc.get("parameters", [])
        if not isinstance(raw, list):
            self._add(out, "CSIR_PARAMETERS", "parameters", "parameters 必须是列表")
            return result
        for index, item in enumerate(raw):
            path = f"parameters[{index}]"
            if not isinstance(item, dict):
                self._add(out, "CSIR_PARAMETER", path, "参数必须是对象")
                continue
            name = item.get("name")
            if not isinstance(name, str) or not _SV_ID.fullmatch(name):
                self._add(out, "CSIR_PARAMETER", f"{path}.name", "参数名无效")
                continue
            if name in result:
                self._add(out, "CSIR_DUPLICATE", f"{path}.name", f"参数 {name} 重复")
            if item.get("type") != "integer":
                self._add(out, "CSIR_UNSUPPORTED", f"{path}.type", "首期只支持 integer 参数")
            values = (item.get("min"), item.get("default"), item.get("max"))
            if any(type(value) is not int for value in values):
                self._add(out, "CSIR_PARAMETER_RANGE", path, "参数必须声明整数 min/default/max")
            elif not values[0] <= values[1] <= values[2]:
                self._add(out, "CSIR_PARAMETER_RANGE", path, "参数默认值不在合法范围内")
            allowed = item.get("allowed")
            if allowed is not None:
                if (
                    not isinstance(allowed, list)
                    or not allowed
                    or any(type(value) is not int for value in allowed)
                    or len(set(allowed)) != len(allowed)
                ):
                    self._add(
                        out, "CSIR_PARAMETER_ALLOWED", f"{path}.allowed",
                        "allowed 必须是非空、无重复的整数列表",
                    )
                elif all(type(value) is int for value in values):
                    if any(value < values[0] or value > values[2] for value in allowed):
                        self._add(
                            out, "CSIR_PARAMETER_ALLOWED", f"{path}.allowed",
                            "allowed 值必须位于 min/max 范围内",
                        )
                    if values[1] not in allowed:
                        self._add(
                            out, "CSIR_PARAMETER_ALLOWED", f"{path}.default",
                            "默认值必须包含在 allowed 中",
                        )
            result[name] = item
        return result

    def _clock_reset(self, doc: dict[str, Any], out: list[SpecDiagnostic]) -> None:
        clocks = doc.get("clocks", [])
        generic = doc.get("design_kind") == "generic_module"
        if not isinstance(clocks, list) or len(clocks) not in ({0, 1} if generic else {1}):
            self._add(out, "CSIR_CLOCK", "clocks", "仅支持组合逻辑或单时钟设计")
        elif not clocks:
            pass
        elif not isinstance(clocks[0], dict):
            self._add(out, "CSIR_CLOCK", "clocks[0]", "时钟必须是对象")
        else:
            if not isinstance(clocks[0].get("name"), str) or not _SV_ID.fullmatch(clocks[0]["name"]):
                self._add(out, "CSIR_CLOCK", "clocks[0].name", "时钟端口标识必须是合法 RTL 名称")
            if clocks[0].get("edge") != "rising":
                self._add(out, "CSIR_UNSUPPORTED", "clocks[0].edge", "首期只支持上升沿时钟")
        resets = doc.get("resets", [])
        if not isinstance(resets, list) or len(resets) not in ({0, 1} if generic else {1}):
            self._add(out, "CSIR_RESET", "resets", "复位最多一个，且必须明确极性与同步方式")
        elif not resets:
            pass
        elif not isinstance(resets[0], dict):
            self._add(out, "CSIR_RESET", "resets[0]", "复位必须是对象")
        else:
            if not isinstance(resets[0].get("name"), str) or not _SV_ID.fullmatch(resets[0]["name"]):
                self._add(out, "CSIR_RESET", "resets[0].name", "复位端口标识必须是合法 RTL 名称")
            if (
                resets[0].get("active") not in {"low", "high"}
                or resets[0].get("kind") not in {"async", "sync"}
            ):
                self._add(out, "CSIR_RESET", "resets[0]", "复位必须明确 active 与 kind")

    def _generic_module_contract(
        self, doc: dict[str, Any], out: list[SpecDiagnostic],
    ) -> None:
        rtl_source = doc.get("rtl_source")
        if rtl_source is not None:
            path = PurePosixPath(rtl_source) if isinstance(rtl_source, str) else None
            if (
                not isinstance(rtl_source, str) or not rtl_source
                or "\\" in rtl_source or path is None or path.is_absolute()
                or any(part in {"", ".", ".."} for part in rtl_source.split("/"))
                or path.suffix.lower() not in {".v", ".sv"}
            ):
                self._add(out, "CSIR_GENERIC_RTL_SOURCE", "rtl_source",
                          "RTL 源文件必须是工程内的 .v/.sv 相对路径")
            elif doc.get("instances"):
                self._add(out, "CSIR_GENERIC_RTL_SOURCE", "rtl_source",
                          "IP 装配顶层由系统生成，不能绑定已有 RTL 源文件")
        rtl_sources = doc.get("rtl_sources")
        if rtl_sources is not None:
            valid_sources = (
                isinstance(rtl_sources, list) and 1 <= len(rtl_sources) <= 256
                and all(
                    isinstance(value, str) and value
                    and "\\" not in value
                    and not PurePosixPath(value).is_absolute()
                    and all(part not in {"", ".", ".."} for part in value.split("/"))
                    and PurePosixPath(value).suffix.lower() in {".v", ".sv"}
                    for value in rtl_sources
                )
            )
            if not valid_sources or len(set(rtl_sources)) != len(rtl_sources):
                self._add(out, "CSIR_GENERIC_RTL_SOURCES", "rtl_sources",
                          "编译清单必须是 1..256 个不重复的工程内 .v/.sv 相对路径")
            elif doc.get("instances"):
                self._add(out, "CSIR_GENERIC_RTL_SOURCES", "rtl_sources",
                          "IP 装配使用系统锁定的 filelist，不能额外绑定工程编译清单")
            elif (rtl_source or f"rtl/{doc.get('name', '')}.sv") not in rtl_sources:
                self._add(out, "CSIR_GENERIC_RTL_SOURCES", "rtl_sources",
                          "编译清单必须包含绑定的顶层 RTL 源文件")
        include_dirs = doc.get("rtl_include_dirs")
        if include_dirs is not None:
            valid_dirs = (
                isinstance(include_dirs, list) and len(include_dirs) <= 64
                and all(
                    isinstance(value, str) and value and "\\" not in value
                    and "\x00" not in value
                    and not PurePosixPath(value).is_absolute()
                    and all(part not in {"", ".", ".."} for part in value.split("/"))
                    for value in include_dirs
                )
            )
            if not valid_dirs or len(set(include_dirs)) != len(include_dirs):
                self._add(out, "CSIR_GENERIC_INCLUDE_DIRS", "rtl_include_dirs",
                          "Include 目录必须是不重复的工程内相对路径（最多 64 个）")
            elif doc.get("instances") and include_dirs:
                self._add(out, "CSIR_GENERIC_INCLUDE_DIRS", "rtl_include_dirs",
                          "IP 装配使用锁定包内的 include 目录，不能额外绑定工程选项")
        defines = doc.get("rtl_defines")
        if defines is not None:
            valid_defines = (
                isinstance(defines, list) and len(defines) <= 128
                and all(
                    isinstance(value, str)
                    and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*(?:=[^\s\x00]+)?", value)
                    for value in defines
                )
            )
            if not valid_defines or len(set(defines)) != len(defines):
                self._add(out, "CSIR_GENERIC_DEFINES", "rtl_defines",
                          "宏定义必须是不重复的 NAME 或 NAME=value（最多 128 个）")
            elif doc.get("instances") and defines:
                self._add(out, "CSIR_GENERIC_DEFINES", "rtl_defines",
                          "IP 装配使用锁定包内的宏定义，不能额外绑定工程选项")
        ports = doc.get("ports", [])
        if not isinstance(ports, list) or not ports:
            self._add(out, "CSIR_GENERIC_PORTS", "ports", "通用模块必须声明端口")
            return
        names = {
            item.get("name"): item for item in ports
            if isinstance(item, dict) and isinstance(item.get("name"), str)
        }
        if not any(item.get("direction") == "output" for item in names.values()):
            self._add(out, "CSIR_GENERIC_OUTPUT", "ports", "通用模块至少需要一个输出端口")
        clocks = doc.get("clocks", [])
        resets = doc.get("resets", [])
        if resets and not clocks:
            self._add(out, "CSIR_GENERIC_RESET", "resets", "组合模块不能声明时序复位")
        for group, label in ((clocks, "clock"), (resets, "reset")):
            if isinstance(group, list):
                for index, item in enumerate(group):
                    if not isinstance(item, dict):
                        continue
                    name = item.get("name")
                    if not isinstance(name, str) or name not in names:
                        self._add(out, "CSIR_GENERIC_PORT", f"{label}s[{index}].name",
                                  f"{label} 必须是已声明的输入端口")
                    elif names[name].get("direction") != "input":
                        self._add(out, "CSIR_GENERIC_PORT", f"{label}s[{index}].name",
                                  f"{label} 端口方向必须为 input")
                    elif names[name].get("width", 1) != 1:
                        self._add(out, "CSIR_GENERIC_PORT_WIDTH", f"{label}s[{index}].name",
                                  f"{label} 端口位宽必须为 1")
        internal = doc.get("internal_signals", [])
        if not isinstance(internal, list):
            self._add(out, "CSIR_GENERIC_SIGNAL", "internal_signals", "内部信号必须是列表")
            internal = []
        parameter_contracts = {
            item.get("name"): item for item in doc.get("parameters", [])
            if isinstance(item, dict) and isinstance(item.get("name"), str)
        }
        instance_names = {
            item.get("name") for item in doc.get("instances", [])
            if isinstance(item, dict) and isinstance(item.get("name"), str)
        }
        signal_names: set[str] = set()
        for index, signal in enumerate(internal):
            path = f"internal_signals[{index}]"
            if not isinstance(signal, dict):
                self._add(out, "CSIR_GENERIC_SIGNAL", path, "内部信号必须是对象")
                continue
            name = signal.get("name")
            if (
                not isinstance(name, str) or not _SV_ID.fullmatch(name)
                or name in names or name in signal_names
                or name in parameter_contracts or name in instance_names
            ):
                self._add(out, "CSIR_GENERIC_SIGNAL", f"{path}.name",
                          "内部信号名必须合法且不能与端口、参数、实例或其他信号重复")
            else:
                signal_names.add(name)
            width = signal.get("width", 1)
            bounded = isinstance(width, str) and width in parameter_contracts and (
                type(parameter_contracts[width].get("min")) is int
                and type(parameter_contracts[width].get("max")) is int
                and 1 <= parameter_contracts[width]["min"] <= parameter_contracts[width]["max"] <= 4096
            )
            if not ((type(width) is int and 1 <= width <= 4096) or bounded):
                self._add(out, "CSIR_GENERIC_SIGNAL_WIDTH", f"{path}.width",
                          "内部信号位宽必须是 1..4096 或有界整数参数")
        if internal and not doc.get("instances"):
            self._add(out, "CSIR_GENERIC_SIGNAL", "internal_signals",
                      "内部信号需要具名端口 IP 实例作为驱动和接收端")
        if doc.get("address_windows", []):
            self._add(out, "CSIR_GENERIC_ASSEMBLY", "address_windows",
                      "通用模块的具名端口 IP 装配不支持地址窗口或隐式译码")
        if doc.get("connections", []):
            self._add(out, "CSIR_GENERIC_ASSEMBLY", "connections",
                      "通用模块首期仅支持实例端口直接绑定顶层端口")
        for index, instance in enumerate(doc.get("instances", [])):
            if not isinstance(instance, dict):
                continue
            path = f"instances[{index}]"
            if instance.get("addressable") is not False:
                self._add(out, "CSIR_GENERIC_ASSEMBLY", f"{path}.addressable",
                          "通用具名端口实例必须明确 addressable: false")
            if instance.get("interface_ids"):
                self._add(out, "CSIR_GENERIC_ASSEMBLY", f"{path}.interface_ids",
                          "通用具名端口实例不能隐式绑定协议接口")
            bindings = instance.get("port_bindings")
            if not isinstance(bindings, dict) or not bindings or any(
                not isinstance(key, str) or not _SV_ID.fullmatch(key)
                or not isinstance(value, str)
                or (value not in names and value not in signal_names)
                for key, value in bindings.items()
            ):
                self._add(out, "CSIR_GENERIC_BINDINGS", f"{path}.port_bindings",
                          "实例必须将每个子模块端口显式绑定到已声明的顶层端口或内部信号")
        generated_names: set[str] = set()
        requirement_ids = {
            item["id"] for item in doc.get("requirements", [])
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        }
        for index, instance in enumerate(doc.get("instances", [])):
            if not isinstance(instance, dict):
                continue
            path = f"instances[{index}]"
            generated = instance.get("generated_module")
            if instance.get("capability") != "generated-rtl" and generated is None:
                continue
            if instance.get("capability") != "generated-rtl" or not isinstance(generated, dict):
                self._add(out, "CSIR_GENERATED_MODULE", path,
                          "生成子模块必须声明 capability: generated-rtl 和 generated_module 契约")
                continue
            if instance.get("package") or instance.get("version") or instance.get("parameters", {}):
                self._add(out, "CSIR_GENERATED_MODULE", path,
                          "生成子模块不能伪装成已审核 IP 或声明未支持的参数")
            module = generated.get("name")
            if (
                not isinstance(module, str) or not _SV_ID.fullmatch(module)
                or module == doc.get("name") or module in generated_names
            ):
                self._add(out, "CSIR_GENERATED_MODULE", f"{path}.generated_module.name",
                          "子模块名无效、重复或与设计顶层冲突")
            else:
                generated_names.add(module)
            ports = generated.get("ports")
            declared: set[str] = set()
            if not isinstance(ports, list) or not ports:
                self._add(out, "CSIR_GENERATED_PORT", f"{path}.generated_module.ports",
                          "生成子模块必须声明完整具名端口")
            else:
                for port_index, port in enumerate(ports):
                    location = f"{path}.generated_module.ports[{port_index}]"
                    if not isinstance(port, dict):
                        self._add(out, "CSIR_GENERATED_PORT", location, "端口必须是对象")
                        continue
                    name = port.get("name")
                    if (
                        not isinstance(name, str) or not _SV_ID.fullmatch(name)
                        or name in declared
                        or not isinstance(port.get("direction"), str)
                        or port["direction"] not in {"input", "output"}
                        or type(port.get("width", 1)) is not int
                        or not 1 <= port.get("width", 1) <= 4096
                    ):
                        self._add(out, "CSIR_GENERATED_PORT", location,
                                  "端口名、方向或 1..4096 位宽无效")
                    else:
                        declared.add(name)
                bindings = instance.get("port_bindings", {})
                if not isinstance(bindings, dict) or set(bindings) != declared:
                    self._add(out, "CSIR_GENERATED_PORT", f"{path}.port_bindings",
                              "生成子模块全部端口必须具名绑定")
            ids = generated.get("requirement_ids")
            if (
                not isinstance(ids, list) or not ids
                or any(not isinstance(item, str) or item not in requirement_ids for item in ids)
                or len(ids) != len(set(ids))
            ):
                self._add(out, "CSIR_GENERATED_REQUIREMENT",
                          f"{path}.generated_module.requirement_ids",
                          "生成子模块必须关联已声明的功能需求 ID")
            behavior = generated.get("behavior")
            if not isinstance(behavior, str) or not behavior.strip():
                self._add(out, "CSIR_GENERATED_BEHAVIOR",
                          f"{path}.generated_module.behavior",
                          "生成子模块必须有可审查的行为说明")
        if doc.get("behaviors", []):
            self._add(out, "CSIR_GENERIC_BEHAVIOR", "behaviors",
                      "通用模块行为请用需求和独立验收项表达；当前不解释外设专用行为")

    def _interfaces(
        self, doc: dict[str, Any], out: list[SpecDiagnostic]
    ) -> list[dict[str, Any]]:
        raw = doc.get("interfaces", [])
        result: list[dict[str, Any]] = []
        if not isinstance(raw, list) or not raw:
            self._add(out, "CSIR_INTERFACE", "interfaces", "至少需要一个接口")
            return result
        seen: set[str] = set()
        for index, item in enumerate(raw):
            path = f"interfaces[{index}]"
            if not isinstance(item, dict):
                self._add(out, "CSIR_INTERFACE", path, "接口必须是对象")
                continue
            endpoint = str(item.get("id", ""))
            if not _ID.fullmatch(endpoint) or endpoint in seen:
                self._add(out, "CSIR_INTERFACE_ID", f"{path}.id", "接口 ID 缺失或重复")
            seen.add(endpoint)
            protocol = item.get("protocol")
            if not isinstance(protocol, str) or protocol not in {"APB4", "PicoRV32-native"}:
                self._add(out, "CSIR_UNSUPPORTED", f"{path}.protocol", "只支持 APB4 与 PicoRV32-native")
            if not isinstance(item.get("role"), str) or item.get("role") not in {"requester", "completer"}:
                self._add(out, "CSIR_INTERFACE_ROLE", f"{path}.role", "接口角色必须明确")
            capabilities = item.get("capabilities")
            if protocol == "APB4":
                if type(item.get("data_width")) is not int or item.get("data_width") not in {8, 16, 32}:
                    self._add(out, "CSIR_APB_WIDTH", f"{path}.data_width", "APB 数据宽度只支持 8/16/32")
                width = item.get("address_width")
                if type(width) is not int or not 1 <= width <= 32:
                    self._add(out, "CSIR_APB_WIDTH", f"{path}.address_width", "APB 地址宽度必须为 1..32")
                if not isinstance(capabilities, dict) or type(capabilities.get("pstrb")) is not bool:
                    self._add(out, "CSIR_APB_CAPABILITY", f"{path}.capabilities.pstrb", "必须明确 PSTRB 能力")
                if not isinstance(capabilities, dict) or capabilities.get("pprot") not in {
                    "enforced", "ignored", "absent",
                }:
                    self._add(out, "CSIR_APB_CAPABILITY", f"{path}.capabilities.pprot", "必须明确 PPROT 处理方式")
            elif protocol == "PicoRV32-native":
                if doc.get("design_kind") != "single_clock_soc":
                    self._add(out, "CSIR_UNSUPPORTED", f"{path}.protocol", "CPU 原生总线仅用于单时钟 SoC")
                if item.get("data_width") != 32 or item.get("address_width") != 32:
                    self._add(out, "CSIR_NATIVE_WIDTH", path, "PicoRV32 原生总线必须为 32 位数据和地址")
                if not isinstance(capabilities, dict) or any(
                    capabilities.get(key) is not True
                    for key in ("byte_strobes", "instruction_tag", "valid_ready")
                ):
                    self._add(out, "CSIR_NATIVE_CAPABILITY", f"{path}.capabilities", "必须明确字节写、取指标记和 valid/ready 握手")
            result.append(copy.deepcopy(item))
        return result

    def _requirements(
        self, doc: dict[str, Any], out: list[SpecDiagnostic]
    ) -> dict[str, dict[str, Any]]:
        result: dict[str, dict[str, Any]] = {}
        raw = doc.get("requirements", [])
        if not isinstance(raw, list) or not raw:
            self._add(out, "CSIR_REQUIREMENT", "requirements", "至少需要一条需求")
            return result
        for index, item in enumerate(raw):
            path = f"requirements[{index}]"
            if not isinstance(item, dict):
                self._add(out, "CSIR_REQUIREMENT", path, "需求必须是对象")
                continue
            req_id = item.get("id")
            if not isinstance(req_id, str) or not _ID.fullmatch(req_id) or req_id in result:
                self._add(out, "CSIR_REQUIREMENT_ID", f"{path}.id", "需求 ID 缺失、无效或重复")
                continue
            if not isinstance(item.get("text"), str) or not item["text"].strip():
                self._add(out, "CSIR_REQUIREMENT_TEXT", f"{path}.text", "需求正文不能为空")
            if item.get("status") != "confirmed":
                self._add(out, "CSIR_REQUIREMENT_UNCONFIRMED", f"{path}.status", f"需求 {req_id} 尚未确认")
            if not isinstance(item.get("source"), str) or not item["source"].strip():
                self._add(out, "CSIR_REQUIREMENT_SOURCE", f"{path}.source", "需求必须保留来源")
            result[req_id] = item
        return result

    def _registers(
        self, doc: dict[str, Any], parameters: dict[str, dict[str, Any]],
        out: list[SpecDiagnostic],
    ) -> list[dict[str, Any]]:
        raw = doc.get("registers", [])
        result: list[dict[str, Any]] = []
        if not isinstance(raw, list) or (
            not raw and doc.get("design_kind", "register_peripheral") != "single_clock_soc"
        ):
            self._add(out, "CSIR_REGISTER", "registers", "寄存器外设必须定义 registers")
            return result
        offsets: set[int] = set()
        names: set[str] = set()
        for index, item in enumerate(raw):
            path = f"registers[{index}]"
            if not isinstance(item, dict):
                self._add(out, "CSIR_REGISTER", path, "寄存器必须是对象")
                continue
            name = item.get("name")
            if not isinstance(name, str) or not _SV_ID.fullmatch(name) or name in names:
                self._add(out, "CSIR_REGISTER_NAME", f"{path}.name", "寄存器名缺失、无效或重复")
            names.add(str(name))
            try:
                offset = _integer(item.get("offset"))
            except (TypeError, ValueError):
                self._add(out, "CSIR_REGISTER_OFFSET", f"{path}.offset", "offset 必须是整数")
                continue
            if offset % 4 or offset in offsets:
                self._add(out, "CSIR_REGISTER_OFFSET", f"{path}.offset", "32 位寄存器地址必须四字节对齐且唯一")
            offsets.add(offset)
            access = str(item.get("access", "")).upper()
            if access not in _ACCESS:
                self._add(out, "CSIR_REGISTER_ACCESS", f"{path}.access", "访问属性只支持 RO/RW/W1C")
            width = item.get("width")
            if not _width_supported(width, parameters):
                self._add(out, "CSIR_REGISTER_WIDTH", f"{path}.width", "位宽必须是 1..32 或合法整数参数")
            reset = item.get("reset")
            if type(reset) is not int or reset < 0:
                self._add(out, "CSIR_REGISTER_RESET", f"{path}.reset", "reset 必须是非负整数")
            normalized = copy.deepcopy(item)
            normalized["offset"] = offset
            normalized["access"] = access
            result.append(normalized)
        return result

    def _ports(
        self, doc: dict[str, Any], parameters: dict[str, dict[str, Any]],
        out: list[SpecDiagnostic],
    ) -> None:
        raw = doc.get("ports", [])
        if not isinstance(raw, list):
            self._add(out, "CSIR_PORT", "ports", "ports 必须是列表")
            return
        seen: set[str] = set()
        for index, item in enumerate(raw):
            path = f"ports[{index}]"
            if not isinstance(item, dict):
                self._add(out, "CSIR_PORT", path, "端口必须是对象")
                continue
            name = item.get("name")
            if not isinstance(name, str) or not _SV_ID.fullmatch(name) or name in seen:
                self._add(out, "CSIR_PORT_NAME", f"{path}.name", "端口名缺失、无效或重复")
            seen.add(str(name))
            if item.get("direction") not in {"input", "output", "inout"}:
                self._add(out, "CSIR_PORT_DIRECTION", f"{path}.direction", "端口方向无效")
            width = item.get("width", 1)
            if doc.get("design_kind") == "generic_module":
                supported = (type(width) is int and 1 <= width <= 4096) or (
                    isinstance(width, str) and width in parameters
                    and type(parameters[width].get("min")) is int
                    and type(parameters[width].get("max")) is int
                    and 1 <= parameters[width]["min"] <= parameters[width]["max"] <= 4096
                )
            else:
                supported = _width_supported(width, parameters)
            if not supported:
                self._add(out, "CSIR_PORT_WIDTH", f"{path}.width", "端口位宽必须是 1..4096 或有界整数参数")

    def _instances(self, doc: dict[str, Any], out: list[SpecDiagnostic]) -> None:
        raw = doc.get("instances", [])
        if not isinstance(raw, list):
            self._add(out, "CSIR_INSTANCE", "instances", "instances 必须是列表")
            return
        seen: set[str] = set()
        interface_ids = {
            item["id"] for item in doc.get("interfaces", [])
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        }
        for index, item in enumerate(raw):
            path = f"instances[{index}]"
            if not isinstance(item, dict):
                self._add(out, "CSIR_INSTANCE", path, "实例必须是对象")
                continue
            name = item.get("name")
            if not isinstance(name, str) or not _SV_ID.fullmatch(name) or name in seen:
                self._add(out, "CSIR_INSTANCE_NAME", f"{path}.name", "实例名缺失、无效或重复")
            seen.add(str(name))
            selector = item.get("package")
            capability = item.get("capability")
            if not isinstance(selector, str) and not isinstance(capability, str):
                self._add(out, "CSIR_INSTANCE_SELECTOR", path, "实例必须指定 package 或 capability")
            version = item.get("version")
            if version is not None and (
                not isinstance(version, str)
                or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(?:[-+][A-Za-z0-9.-]+)?", version)
                or not isinstance(selector, str)
            ):
                self._add(out, "CSIR_INSTANCE_VERSION", f"{path}.version",
                          "显式 IP 版本必须为 package 对应的语义版本")
            if doc.get("design_kind") == "single_clock_soc" and (
                not isinstance(capability, str) or capability not in {
                    "rv32i-cpu", "native-apb-bridge", "program-rom", "register-ram",
                    "apb-gpio", "apb-uart", "apb-timer", "generated-rtl",
                }
            ):
                self._add(out, "CSIR_SOC_CAPABILITY", f"{path}.capability", "单时钟 SoC 实例必须明确首期支持的功能能力")
            if not isinstance(item.get("parameters", {}), dict):
                self._add(out, "CSIR_INSTANCE_PARAMETERS", f"{path}.parameters", "实例参数必须是对象")
            if "addressable" in item and type(item["addressable"]) is not bool:
                self._add(out, "CSIR_INSTANCE_ADDRESSABLE", f"{path}.addressable", "addressable 必须为布尔值")
            bindings = item.get("interface_ids")
            if (
                doc.get("design_kind") == "single_clock_soc" and not bindings
                and capability != "generated-rtl"
            ):
                self._add(out, "CSIR_INSTANCE_INTERFACE", f"{path}.interface_ids", "SoC 实例必须绑定接口端点")
            if bindings is not None:
                if (
                    not isinstance(bindings, list) or not bindings
                    or any(not isinstance(value, str) for value in bindings)
                    or len(bindings) != len(set(bindings))
                    or any(value not in interface_ids for value in bindings)
                ):
                    self._add(out, "CSIR_INSTANCE_INTERFACE", f"{path}.interface_ids", "接口绑定必须唯一且引用已声明端点")

    def _peripheral_contracts(
        self, doc: dict[str, Any], interfaces: list[dict[str, Any]],
        out: list[SpecDiagnostic],
    ) -> list[dict[str, Any]]:
        raw = doc.get("peripheral_contracts", [])
        if not isinstance(raw, list):
            self._add(out, "CSIR_PERIPHERAL", "peripheral_contracts", "外设契约必须是列表")
            return []
        if doc.get("design_kind") != "single_clock_soc":
            if raw:
                self._add(out, "CSIR_UNSUPPORTED", "peripheral_contracts", "外设实例契约仅用于单时钟 SoC")
            return []
        instances = {
            item["name"]: item for item in doc.get("instances", [])
            if isinstance(item, dict) and isinstance(item.get("name"), str)
        }
        expected = {
            name: item["capability"] for name, item in instances.items()
            if isinstance(item.get("capability"), str)
            and item["capability"] in _SOC_PERIPHERAL_PROFILES
        }
        bound: set[str] = set()
        result: list[dict[str, Any]] = []
        interface_map = {
            item.get("id"): item for item in interfaces
            if isinstance(item.get("id"), str)
        }
        for index, item in enumerate(raw):
            path = f"peripheral_contracts[{index}]"
            if not isinstance(item, dict):
                self._add(out, "CSIR_PERIPHERAL", path, "外设契约必须是对象")
                continue
            name = item.get("instance")
            if not isinstance(name, str) or name not in expected or name in bound:
                self._add(out, "CSIR_PERIPHERAL_INSTANCE", f"{path}.instance", "外设契约实例未知、重复或能力不受支持")
                continue
            bound.add(name)
            profile = _SOC_PERIPHERAL_PROFILES[expected[name]]
            if set(item) != {"instance", "kind", "registers", "behavior"}:
                self._add(out, "CSIR_PERIPHERAL_FIELDS", path, "外设契约字段必须是 instance/kind/registers/behavior")
            if item.get("kind") != profile["kind"]:
                self._add(out, "CSIR_PERIPHERAL_KIND", f"{path}.kind", "外设行为类型与已支持的 IP 不一致")
            actual_registers = item.get("registers")
            parsed_registers: list[tuple[str, int, str]] = []
            if isinstance(actual_registers, list):
                for number, register in enumerate(actual_registers):
                    if not isinstance(register, dict) or set(register) != {"name", "offset", "access"}:
                        self._add(out, "CSIR_PERIPHERAL_REGISTER", f"{path}.registers[{number}]", "寄存器必须明确名称、偏移和访问属性")
                        continue
                    try:
                        offset = _integer(register["offset"])
                    except (TypeError, ValueError):
                        self._add(out, "CSIR_PERIPHERAL_REGISTER", f"{path}.registers[{number}].offset", "寄存器偏移必须为整数")
                        continue
                    if not isinstance(register["name"], str) or not isinstance(register["access"], str):
                        self._add(out, "CSIR_PERIPHERAL_REGISTER", f"{path}.registers[{number}]", "寄存器名称和访问属性必须是字符串")
                        continue
                    parsed_registers.append((register["name"], offset, register["access"]))
            if (
                not isinstance(actual_registers, list)
                or len(parsed_registers) != len(profile["registers"])
                or set(parsed_registers) != set(profile["registers"])
            ):
                self._add(out, "CSIR_PERIPHERAL_REGISTER", f"{path}.registers", "寄存器映射与首期受支持的 IP 契约不一致")
            behavior = item.get("behavior")
            if not isinstance(behavior, dict):
                self._add(out, "CSIR_PERIPHERAL_BEHAVIOR", f"{path}.behavior", "必须明确外设行为契约")
            else:
                expected_behavior = profile["behavior"]
                for field, value in expected_behavior.items():
                    actual = behavior.get(field)
                    if type(actual) is not type(value) or actual != value:
                        self._add(out, "CSIR_PERIPHERAL_BEHAVIOR", f"{path}.behavior.{field}", f"{field} 与已支持的 IP 契约不一致或缺失")
                for field in set(behavior) - set(expected_behavior):
                    self._add(out, "CSIR_UNSUPPORTED", f"{path}.behavior.{field}", "未支持的外设行为，不能自动冻结")
            bindings = instances[name].get("interface_ids", [])
            bindings = bindings if isinstance(bindings, list) else []
            def supported_apb(endpoint: Any) -> bool:
                interface = interface_map.get(endpoint) if isinstance(endpoint, str) else None
                if not isinstance(interface, dict):
                    return False
                capabilities = interface.get("capabilities")
                return (
                    interface.get("protocol") == "APB4"
                    and interface.get("role") == "completer"
                    and isinstance(capabilities, dict)
                    and capabilities.get("pstrb") is True
                    and capabilities.get("pprot") == "ignored"
                )
            if not any(supported_apb(endpoint) for endpoint in bindings):
                self._add(out, "CSIR_PERIPHERAL_INTERFACE", f"{path}.instance", "外设必须绑定支持 PSTRB 且忽略 PPROT 的 APB4 从接口")
            result.append(copy.deepcopy(item))
        for name in sorted(set(expected) - bound):
            self._add(out, "CSIR_PERIPHERAL_REQUIRED", "peripheral_contracts", f"实例 {name} 缺少 UART/定时器行为与寄存器契约")
        return result

    def _windows(self, doc: dict[str, Any], out: list[SpecDiagnostic]) -> None:
        windows = doc.get("address_windows", [])
        if not isinstance(windows, list):
            self._add(out, "CSIR_ADDRESS", "address_windows", "地址窗口必须是列表")
            return
        parsed: list[tuple[int, int, int]] = []
        instance_names = {
            str(item.get("name")): item for item in doc.get("instances", [])
            if isinstance(item, dict) and isinstance(item.get("name"), str)
        }
        counts = {
            name: 0 for name, item in instance_names.items()
            if item.get("addressable", True) is not False
        }
        address_protocol = (
            "PicoRV32-native" if doc.get("design_kind") == "single_clock_soc" else "APB4"
        )
        address_widths = [
            item.get("address_width") for item in doc.get("interfaces", [])
            if isinstance(item, dict) and item.get("protocol") == address_protocol
            and type(item.get("address_width")) is int
        ]
        address_limit = 1 << min(address_widths) if address_widths else None
        for index, item in enumerate(windows):
            if not isinstance(item, dict):
                self._add(out, "CSIR_ADDRESS", f"address_windows[{index}]", "地址窗口必须是对象")
                continue
            instance = item.get("instance")
            if not isinstance(instance, str) or instance not in instance_names:
                self._add(
                    out, "CSIR_ADDRESS_INSTANCE", f"address_windows[{index}].instance",
                    "地址窗口必须引用已声明的 IP 实例",
                )
            elif instance not in counts:
                self._add(
                    out, "CSIR_ADDRESS_INSTANCE", f"address_windows[{index}].instance",
                    "非地址化实例不能分配地址窗口",
                )
            else:
                counts[str(instance)] += 1
            try:
                base, size = _integer(item["base"]), _integer(item["size"])
                if base < 0 or size <= 0 or base % size:
                    raise ValueError
            except (KeyError, TypeError, ValueError):
                self._add(out, "CSIR_ADDRESS", f"address_windows[{index}]", "窗口 base/size 必须合法且对齐")
                continue
            for other_base, other_size, other_index in parsed:
                if max(base, other_base) < min(base + size, other_base + other_size):
                    self._add(out, "CSIR_ADDRESS_OVERLAP", f"address_windows[{index}]", f"与窗口 {other_index} 重叠")
            if address_limit is not None and base + size > address_limit:
                self._add(
                    out, "CSIR_ADDRESS_RANGE", f"address_windows[{index}]",
                    f"地址窗口超出 {address_protocol} 地址宽度",
                )
            parsed.append((base, size, index))
        for instance, count in counts.items():
            if count != 1:
                self._add(
                    out, "CSIR_ADDRESS_INSTANCE", "address_windows",
                    f"实例 {instance} 必须且只能有一个地址窗口",
                )

    def _memories(
        self, doc: dict[str, Any], out: list[SpecDiagnostic],
    ) -> list[dict[str, Any]]:
        raw = doc.get("memories", [])
        if not isinstance(raw, list):
            self._add(out, "CSIR_MEMORY", "memories", "memories 必须是列表")
            return []
        soc = doc.get("design_kind") == "single_clock_soc"
        if soc and not raw:
            self._add(out, "CSIR_MEMORY", "memories", "SoC 必须声明 ROM 和寄存器 RAM")
        if not soc and raw:
            self._add(out, "CSIR_UNSUPPORTED", "memories", "存储阵列目前仅支持单时钟 SoC")
        windows = {
            item["instance"]: item for item in doc.get("address_windows", [])
            if isinstance(item, dict) and isinstance(item.get("instance"), str)
        }
        instances = {
            item.get("name") for item in doc.get("instances", [])
            if isinstance(item, dict)
        }
        capabilities = {
            item.get("name"): item.get("capability")
            for item in doc.get("instances", []) if isinstance(item, dict)
        }
        seen: set[str] = set()
        kinds: set[str] = set()
        result: list[dict[str, Any]] = []
        for index, item in enumerate(raw):
            path = f"memories[{index}]"
            if not isinstance(item, dict):
                self._add(out, "CSIR_MEMORY", path, "存储定义必须是对象")
                continue
            instance = item.get("instance")
            if not isinstance(instance, str) or instance not in instances or instance in seen:
                self._add(out, "CSIR_MEMORY_INSTANCE", f"{path}.instance", "存储必须唯一地引用已声明实例")
            if isinstance(instance, str):
                seen.add(instance)
                if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", instance):
                    self._add(
                        out, "CSIR_MEMORY_NAME", f"{path}.instance",
                        "存储器实例名仅支持字母、数字和下划线",
                    )
            kind = item.get("kind")
            if not isinstance(kind, str) or kind not in {"rom", "register_ram"}:
                self._add(out, "CSIR_MEMORY_KIND", f"{path}.kind", "仅支持 ROM 与寄存器 RAM")
            elif isinstance(kind, str):
                kinds.add(kind)
                expected = "program-rom" if kind == "rom" else "register-ram"
                if capabilities.get(instance) != expected:
                    self._add(
                        out, "CSIR_MEMORY_CAPABILITY", f"{path}.instance",
                        f"{kind} 必须引用 {expected} 实例",
                    )
            size = item.get("size_bytes")
            if type(size) is not int or not 4 <= size <= 65_536 or size % 4:
                self._add(out, "CSIR_MEMORY_SIZE", f"{path}.size_bytes", "容量必须是 4..65536 字节且四字节对齐")
            else:
                window = windows.get(instance) if isinstance(instance, str) else None
                try:
                    window_size = _integer(window["size"]) if window else None
                except (TypeError, ValueError, KeyError):
                    window_size = None
                if window_size != size:
                    self._add(out, "CSIR_MEMORY_WINDOW", path, "存储容量与地址窗口大小必须一致")
            if item.get("data_width") != 32:
                self._add(out, "CSIR_MEMORY_WIDTH", f"{path}.data_width", "首期存储数据宽度必须为 32")
            if kind == "rom":
                image = item.get("image")
                if (
                    not isinstance(image, str) or not image
                    or PurePosixPath(image).is_absolute()
                    or any(part in {".", ".."} for part in PurePosixPath(image).parts)
                ):
                    self._add(out, "CSIR_MEMORY_IMAGE", f"{path}.image", "ROM 必须声明工程内的相对固件镜像路径")
                elif (
                    not isinstance(doc.get("acceptance_sources"), list)
                    or image not in doc["acceptance_sources"]
                ):
                    self._add(
                        out, "CSIR_MEMORY_IMAGE_UNBOUND", f"{path}.image",
                        "ROM 镜像必须列入 acceptance_sources，以随规格冻结内容摘要",
                    )
                if item.get("writable") is not False:
                    self._add(out, "CSIR_MEMORY_ACCESS", f"{path}.writable", "ROM 必须为只读")
            if kind == "register_ram" and item.get("writable") is not True:
                self._add(out, "CSIR_MEMORY_ACCESS", f"{path}.writable", "寄存器 RAM 必须允许写入")
            result.append(copy.deepcopy(item))
        if soc and not {"rom", "register_ram"}.issubset(kinds):
            self._add(out, "CSIR_MEMORY", "memories", "SoC 必须同时声明程序 ROM 与寄存器 RAM")
        return result

    def _soc_contract(
        self, doc: dict[str, Any], interfaces: list[dict[str, Any]],
        out: list[SpecDiagnostic],
    ) -> None:
        if doc.get("design_kind") != "single_clock_soc":
            target = doc.get("technical_target")
            if target is not None:
                if not isinstance(target, dict) or (
                    target.get("platform") != "sky130hd" or target.get("pvt") != "tt"
                ):
                    self._add(out, "CSIR_TARGET", "technical_target",
                              "首期物理目标仅支持 Sky130HD TT")
                else:
                    period = target.get("clock_period_ns")
                    if (
                        isinstance(period, bool) or not isinstance(period, (int, float))
                        or not 0.01 <= period <= 1_000_000 or not math.isfinite(period)
                    ):
                        self._add(out, "CSIR_TARGET", "technical_target.clock_period_ns",
                                  "时钟周期必须为 0.01..1000000 ns 的有限数")
            return
        instance_list = doc.get("instances", [])
        if isinstance(instance_list, list):
            capabilities = [
                item.get("capability") for item in instance_list
                if isinstance(item, dict)
            ]
            for capability in (
                "rv32i-cpu", "native-apb-bridge", "program-rom", "register-ram",
            ):
                if capabilities.count(capability) != 1:
                    self._add(
                        out, "CSIR_SOC_TOPOLOGY", "instances",
                        f"单时钟 SoC 必须恰有一个 {capability} 实例",
                    )
            for capability in ("apb-gpio", "apb-uart", "apb-timer"):
                if capabilities.count(capability) > 1:
                    self._add(
                        out, "CSIR_SOC_TOPOLOGY", "instances",
                        f"首期最多支持一个 {capability} 实例",
                    )
            if not any(
                isinstance(item, str) and item in {"apb-gpio", "apb-uart", "apb-timer"}
                for item in capabilities
            ):
                self._add(
                    out, "CSIR_SOC_TOPOLOGY", "instances",
                    "单时钟 SoC 至少需要一个 APB 外设实例",
                )
        rom_names = {
            item.get("name") for item in instance_list
            if isinstance(item, dict) and item.get("capability") == "program-rom"
            and isinstance(item.get("name"), str)
        } if isinstance(instance_list, list) else set()
        peripheral_names = {
            item.get("name") for item in instance_list
            if isinstance(item, dict)
            and isinstance(item.get("capability"), str)
            and item.get("capability") in {"apb-gpio", "apb-uart", "apb-timer"}
            and isinstance(item.get("name"), str)
        } if isinstance(instance_list, list) else set()
        apb_pages: set[int] = set()
        windows = doc.get("address_windows", [])
        for index, window in enumerate(windows if isinstance(windows, list) else []):
            if not isinstance(window, dict):
                continue
            try:
                base, size = _integer(window["base"]), _integer(window["size"])
            except (KeyError, TypeError, ValueError):
                continue
            if window.get("instance") in rom_names and base != 0:
                self._add(
                    out, "CSIR_SOC_RESET_VECTOR", f"address_windows[{index}].base",
                    "固定 PicoRV32 的复位地址 0 必须映射到程序 ROM",
                )
            if window.get("instance") in peripheral_names:
                apb_pages.add(base >> 12)
                if size <= 0 or (base & 0xFFF) + size > 4096:
                    self._add(
                        out, "CSIR_SOC_APB_APERTURE", f"address_windows[{index}]",
                        "APB 外设窗口必须位于单个 4 KiB 地址页内",
                    )
        if len(apb_pages) > 1:
            self._add(
                out, "CSIR_SOC_APB_APERTURE", "address_windows",
                "首期桥接器的 APB 外设必须位于同一个 4 KiB 地址页",
            )
        if not any(
            item.get("protocol") == "PicoRV32-native"
            and item.get("role") == "requester" for item in interfaces
        ):
            self._add(out, "CSIR_SOC_BUS", "interfaces", "SoC 必须有一个 PicoRV32 原生主接口")
        if not any(
            item.get("protocol") == "APB4" and item.get("role") == "requester"
            for item in interfaces
        ):
            self._add(out, "CSIR_SOC_APB", "interfaces", "SoC 必须有 APB4 外设主接口")
        exceptions = doc.get("exceptions")
        policies = {
            "unmapped_access": "complete_zero",
            "misaligned_access": "cpu_trap",
            "illegal_instruction": "cpu_trap",
        }
        if not isinstance(exceptions, dict):
            self._add(out, "CSIR_SOC_EXCEPTION", "exceptions", "必须明确总线与 CPU 异常行为")
        else:
            for key, supported in policies.items():
                if exceptions.get(key) != supported:
                    self._add(
                        out, "CSIR_SOC_EXCEPTION", f"exceptions.{key}",
                        f"首期必须明确 {key}: {supported}",
                    )
        constraints = doc.get("cycle_constraints")
        ids = {
            item["id"] for item in interfaces
            if isinstance(item.get("id"), str)
        }
        if not isinstance(constraints, list) or not constraints:
            self._add(out, "CSIR_SOC_CYCLE", "cycle_constraints", "必须声明总线最大响应周期")
        else:
            seen: set[str] = set()
            for index, item in enumerate(constraints):
                path = f"cycle_constraints[{index}]"
                if not isinstance(item, dict):
                    self._add(out, "CSIR_SOC_CYCLE", path, "周期约束必须是对象")
                    continue
                interface_id = item.get("interface")
                if not isinstance(interface_id, str) or interface_id not in ids or interface_id in seen:
                    self._add(out, "CSIR_SOC_CYCLE", f"{path}.interface", "周期约束接口未知或重复")
                if isinstance(interface_id, str):
                    seen.add(interface_id)
                if item.get("kind") != "max_response_cycles":
                    self._add(out, "CSIR_SOC_CYCLE", f"{path}.kind", "仅支持最大响应周期约束")
                cycles = item.get("cycles")
                if type(cycles) is not int or not 1 <= cycles <= 256:
                    self._add(out, "CSIR_SOC_CYCLE", f"{path}.cycles", "响应周期必须为 1..256")
        target = doc.get("technical_target")
        if not isinstance(target, dict):
            self._add(out, "CSIR_SOC_TARGET", "technical_target", "必须冻结物理技术目标")
            return
        if target.get("platform") != "sky130hd" or target.get("pvt") != "tt":
            self._add(out, "CSIR_SOC_TARGET", "technical_target", "首期仅支持 Sky130HD TT")
        period = target.get("clock_period_ns")
        if (
            isinstance(period, bool) or not isinstance(period, (int, float))
            or not math.isfinite(period) or period <= 0
        ):
            self._add(out, "CSIR_SOC_TARGET", "technical_target.clock_period_ns", "时钟周期必须为正的有限数")

    def _behaviors(self, doc: dict[str, Any], out: list[SpecDiagnostic]) -> None:
        raw = doc.get("behaviors", [])
        if not isinstance(raw, list):
            self._add(out, "CSIR_BEHAVIOR", "behaviors", "behaviors 必须是列表")
            return
        ports = {
            item.get("name") for item in doc.get("ports", []) if isinstance(item, dict)
        }
        registers = {
            item.get("name") for item in doc.get("registers", []) if isinstance(item, dict)
        }
        for index, item in enumerate(raw):
            path = f"behaviors[{index}]"
            if not isinstance(item, dict):
                self._add(out, "CSIR_BEHAVIOR", path, "行为必须是对象")
                continue
            if item.get("kind") != "rising_edge_latch":
                self._add(
                    out, "CSIR_UNSUPPORTED", f"{path}.kind",
                    "首期行为只支持 rising_edge_latch",
                )
            if item.get("source") not in ports:
                self._add(out, "CSIR_BEHAVIOR_SOURCE", f"{path}.source", "行为源必须引用端口")
            if item.get("target") not in registers:
                self._add(out, "CSIR_BEHAVIOR_TARGET", f"{path}.target", "行为目标必须引用寄存器")
            if item.get("priority") != "set_over_clear":
                self._add(
                    out, "CSIR_UNSUPPORTED", f"{path}.priority",
                    "必须明确同周期冲突采用 set_over_clear",
                )

    def _acceptance(
        self, doc: dict[str, Any], requirements: dict[str, dict[str, Any]],
        out: list[SpecDiagnostic],
    ) -> list[dict[str, Any]]:
        raw = doc.get("acceptance", [])
        result: list[dict[str, Any]] = []
        covered: set[str] = set()
        seen: set[str] = set()
        if not isinstance(raw, list) or not raw:
            self._add(out, "CSIR_ACCEPTANCE", "acceptance", "至少需要一个独立验收检查")
            return result
        for index, item in enumerate(raw):
            path = f"acceptance[{index}]"
            if not isinstance(item, dict):
                self._add(out, "CSIR_ACCEPTANCE", path, "验收检查必须是对象")
                continue
            check_id = item.get("id")
            if not isinstance(check_id, str) or not _ID.fullmatch(check_id) or check_id in seen:
                self._add(out, "CSIR_ACCEPTANCE_ID", f"{path}.id", "验收 ID 缺失、无效或重复")
            seen.add(str(check_id))
            ids = item.get("requirement_ids")
            if not isinstance(ids, list) or not ids:
                self._add(out, "CSIR_ACCEPTANCE_REQUIREMENT", f"{path}.requirement_ids", "验收项必须引用需求")
                ids = []
            for req_id in ids:
                if req_id not in requirements:
                    self._add(out, "CSIR_ACCEPTANCE_REFERENCE", f"{path}.requirement_ids", f"未知需求 {req_id}")
                covered.add(str(req_id))
            if item.get("kind") not in {"simulation", "lint", "elaboration"}:
                self._add(out, "CSIR_ACCEPTANCE_KIND", f"{path}.kind", "验收类型只支持 simulation/lint/elaboration")
            if "status" in item and (
                not isinstance(item["status"], str)
                or item["status"] not in {"planned", "implemented"}
            ):
                self._add(out, "CSIR_ACCEPTANCE_STATUS", f"{path}.status", "验收状态只支持 planned/implemented")
            if "evidence_marker_required" in item and type(item["evidence_marker_required"]) is not bool:
                self._add(out, "CSIR_ACCEPTANCE_MARKER", f"{path}.evidence_marker_required", "标记要求必须为布尔值")
            result.append(copy.deepcopy(item))
        for req_id in sorted(set(requirements) - covered):
            self._add(out, "CSIR_REQUIREMENT_UNCOVERED", "acceptance", f"需求 {req_id} 没有验收检查")
        return result

    def _acceptance_sources(
        self, doc: dict[str, Any], out: list[SpecDiagnostic],
    ) -> None:
        if "acceptance_sources" not in doc:
            return
        sources = doc["acceptance_sources"]
        if not isinstance(sources, list) or not sources:
            self._add(out, "CSIR_ACCEPTANCE_SOURCES", "acceptance_sources",
                      "验收输入必须是非空的工程相对文件列表")
            return
        seen: set[str] = set()
        for index, value in enumerate(sources):
            path = f"acceptance_sources[{index}]"
            try:
                relative = _acceptance_relative_path(value)
            except SpecificationError as exc:
                self._add(out, "CSIR_ACCEPTANCE_SOURCE_PATH", path, str(exc))
                continue
            if relative in seen:
                self._add(out, "CSIR_ACCEPTANCE_SOURCE_DUPLICATE", path,
                          f"重复验收输入：{relative}")
            seen.add(relative)
        runner = doc.get("acceptance_runner")
        if runner is not None:
            try:
                relative = _acceptance_relative_path(runner)
            except SpecificationError as exc:
                self._add(out, "CSIR_ACCEPTANCE_RUNNER_PATH", "acceptance_runner", str(exc))
            else:
                if doc.get("design_kind") != "single_clock_soc" or relative not in seen:
                    self._add(
                        out, "CSIR_ACCEPTANCE_RUNNER", "acceptance_runner",
                        "SoC 独立验收入口必须列入冻结验收输入",
                    )

    def _questions(self, doc: dict[str, Any], out: list[SpecDiagnostic]) -> None:
        raw = doc.get("open_questions", [])
        if not isinstance(raw, list):
            self._add(out, "CSIR_QUESTIONS", "open_questions", "open_questions 必须是列表")
            return
        for index, item in enumerate(raw):
            if not isinstance(item, dict) or item.get("status") != "resolved":
                text = item.get("question", "未说明") if isinstance(item, dict) else "格式错误"
                self._add(out, "CSIR_OPEN_QUESTION", f"open_questions[{index}]", f"待确认：{text}")


class SpecificationWorkspace:
    def __init__(self, project_root: Path, compiler: SpecCompiler | None = None) -> None:
        self.root = project_root.resolve()
        self.compiler = compiler or SpecCompiler()
        self.path = self.root / "spec" / "design.csir.yaml"
        self.archive_root = self.root / ".chip_nebula" / "design" / "specs"

    def read(self) -> dict[str, Any]:
        if not self.path.is_file():
            return default_generic_module_spec()
        try:
            document = yaml.safe_load(self.path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            raise SpecificationError(f"cannot read CSIR: {exc}") from exc
        if not isinstance(document, dict):
            raise SpecificationError("CSIR document must be a mapping")
        return document

    def _source_hashes(self, document: Mapping[str, Any]) -> dict[str, str]:
        sources = document.get("acceptance_sources", [])
        if not isinstance(sources, list):
            raise SpecificationError("验收输入列表无效")
        hashes: dict[str, str] = {}
        for value in sources:
            relative = _acceptance_relative_path(value)
            source = self.root / relative
            try:
                resolved = source.resolve(strict=True)
                if resolved != source or not source.is_file():
                    raise SpecificationError(f"验收输入必须是工程内普通文件：{relative}")
                digest = hashlib.sha256()
                with source.open("rb") as stream:
                    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                        digest.update(chunk)
            except OSError as exc:
                raise SpecificationError(f"验收输入缺失或不可读取：{relative}") from exc
            hashes[relative] = "sha256:" + digest.hexdigest()
        return dict(sorted(hashes.items()))

    def state(self) -> dict[str, Any]:
        configured = self.path.is_file()
        compiled = self.compiler.compile(self.read())
        frozen = compiled.document.get("status") == "frozen"
        recorded = str(compiled.document.get("frozen_digest", ""))
        spec_integrity = not frozen or recorded == compiled.spec_digest
        source_integrity = True
        source_issue = ""
        source_digest = ""
        if frozen and "acceptance_sources" in compiled.document:
            expected = compiled.document.get("acceptance_sources_hashes")
            source_digest = str(compiled.document.get("acceptance_sources_digest", ""))
            try:
                actual = self._source_hashes(compiled.document)
                source_integrity = (
                    isinstance(expected, dict) and expected == actual
                    and source_digest == _digest(actual)
                )
                if not source_integrity:
                    changed = sorted(
                        path for path in set(actual) | set(expected if isinstance(expected, dict) else {})
                        if actual.get(path) != (expected.get(path) if isinstance(expected, dict) else None)
                    )
                    source_issue = "、".join(changed) or "验收输入摘要"
            except SpecificationError as exc:
                source_integrity = False
                source_issue = str(exc)
        integrity = spec_integrity and source_integrity
        result = compiled.to_dict()
        result.update({
            "configured": configured,
            "frozen": frozen and integrity,
            "integrity": integrity,
            "acceptance_sources_digest": source_digest if source_integrity else "",
            "path": "spec/design.csir.yaml",
        })
        if frozen and source_integrity and source_digest:
            result["acceptance_plan"]["acceptance_sources_digest"] = source_digest
        if frozen and not spec_integrity:
            result["diagnostics"].insert(0, asdict(SpecDiagnostic(
                "CSIR_FROZEN_MODIFIED", "error", "frozen_digest",
                "冻结规格已被修改；请创建新修订并重新冻结",
            )))
            result["valid"] = False
        if frozen and not source_integrity:
            result["diagnostics"].insert(0, asdict(SpecDiagnostic(
                "CSIR_ACCEPTANCE_SOURCE_MODIFIED", "error", "acceptance_sources",
                f"冻结验收输入已改变：{source_issue}；请创建新修订并重新冻结",
            )))
            result["valid"] = False
        return result

    def save(self, document: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(document, Mapping):
            raise SpecificationError("CSIR document must be a mapping")
        saved = copy.deepcopy(dict(document))
        current = self.read() if self.path.is_file() else None
        source_changed = False
        if current and current.get("status") == "frozen" and "acceptance_sources" in current:
            try:
                hashes = self._source_hashes(current)
                source_changed = (
                    hashes != current.get("acceptance_sources_hashes")
                    or _digest(hashes) != current.get("acceptance_sources_digest")
                )
            except SpecificationError:
                source_changed = True
        if current and current.get("status") == "frozen":
            current_semantic = _semantic_document(current)
            next_semantic = _semantic_document(saved)
            if current_semantic != next_semantic or source_changed:
                saved["revision"] = max(
                    int(current.get("revision", 1)) + 1,
                    int(saved.get("revision", 1)),
                )
                saved["status"] = "draft"
                for key in ("frozen_digest", "acceptance_digest",
                            "acceptance_sources_digest", "acceptance_sources_hashes"):
                    saved.pop(key, None)
        else:
            saved["status"] = "draft"
            for key in ("frozen_digest", "acceptance_digest",
                        "acceptance_sources_digest", "acceptance_sources_hashes"):
                saved.pop(key, None)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            yaml.safe_dump(saved, allow_unicode=True, sort_keys=False), encoding="utf-8"
        )
        return self.state()

    def freeze(self) -> dict[str, Any]:
        document = self.read()
        compiled = self.compiler.compile(document)
        if not compiled.valid:
            raise SpecificationError("规格存在阻断问题，不能冻结")
        if document.get("status") == "frozen" and not self.state()["integrity"]:
            raise SpecificationError("冻结规格或验收输入已改变；请创建新修订后再冻结")
        frozen = copy.deepcopy(document)
        frozen["status"] = "frozen"
        frozen["frozen_digest"] = compiled.spec_digest
        frozen["acceptance_digest"] = _digest(compiled.acceptance_plan)
        if "acceptance_sources" in document:
            source_hashes = self._source_hashes(document)
            frozen["acceptance_sources_hashes"] = source_hashes
            frozen["acceptance_sources_digest"] = _digest(source_hashes)
        archive = self.archive_root / str(frozen["spec_id"]) / f"{compiled.spec_digest.removeprefix('sha256:')}.json"
        if archive.exists():
            try:
                previous = json.loads(archive.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise SpecificationError("已冻结规格归档损坏，不能覆盖") from exc
            if previous.get("acceptance_sources_digest", "") != frozen.get("acceptance_sources_digest", ""):
                raise SpecificationError("验收输入已有不同的冻结版本；请创建新修订")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            yaml.safe_dump(frozen, allow_unicode=True, sort_keys=False), encoding="utf-8"
        )
        archive.parent.mkdir(parents=True, exist_ok=True)
        if not archive.exists():
            archive.write_text(
                json.dumps({
                    "document": frozen,
                    "spec_digest": compiled.spec_digest,
                    "interface_contract": compiled.interface_contract,
                    "acceptance_plan": compiled.acceptance_plan,
                    "acceptance_sources_hashes": frozen.get("acceptance_sources_hashes", {}),
                    "acceptance_sources_digest": frozen.get("acceptance_sources_digest", ""),
                    "register_markdown": compiled.register_markdown,
                }, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        return self.state()


def default_generic_module_spec() -> dict[str, Any]:
    """Neutral, unconfigured CSIR canvas for a new digital RTL project."""
    return {
        "schema_version": 1, "spec_id": "new-module", "name": "new_module",
        "revision": 1, "status": "draft", "design_kind": "generic_module",
        "demand": "", "parameters": [], "clocks": [], "resets": [],
        "interfaces": [], "ports": [], "internal_signals": [],
        "registers": [], "behaviors": [],
        "instances": [], "connections": [], "address_windows": [],
        "requirements": [], "acceptance": [], "open_questions": [],
    }


def default_apb_gpio_spec() -> dict[str, Any]:
    requirements = [
        ("REQ.APB", "实现 APB4 32 位 completer，支持 PSTRB，不实施 PPROT 权限过滤"),
        ("REQ.RESET", "PRESETn 低有效异步复位，全部可写状态清零"),
        ("REQ.GPIO", "GPIO 宽度可配置为 8、16 或 32 位"),
        ("REQ.REG", "提供 OUT、OE、IN、IRQ_EN、IRQ_STATUS 五个寄存器"),
        ("REQ.IRQ", "GPIO 输入上升沿置位 IRQ_STATUS，同周期置位优先于软件清除"),
        ("REQ.ERROR", "非法地址、未对齐访问和写只读寄存器返回 PSLVERR"),
    ]
    return {
        "schema_version": 1,
        "spec_id": "apb-gpio",
        "name": "apb_gpio",
        "revision": 1,
        "status": "draft",
        "demand": "可参数化 APB4 GPIO 外设，复用已审核的 APB 寄存器基础 IP。",
        "parameters": [{
            "name": "GPIO_WIDTH", "type": "integer", "min": 8,
            "default": 8, "max": 32, "allowed": [8, 16, 32],
        }],
        "clocks": [{"name": "PCLK", "edge": "rising"}],
        "resets": [{"name": "PRESETn", "active": "low", "kind": "async", "clock": "PCLK"}],
        "interfaces": [{
            "id": "apb_s", "protocol": "APB4", "role": "completer",
            "data_width": 32, "address_width": 12, "clock": "PCLK", "reset": "PRESETn",
            "capabilities": {"pstrb": True, "pprot": "ignored", "pready": True, "pslverr": True},
        }],
        "ports": [
            {"name": "gpio_i", "direction": "input", "width": "GPIO_WIDTH"},
            {"name": "gpio_o", "direction": "output", "width": "GPIO_WIDTH"},
            {"name": "gpio_oe", "direction": "output", "width": "GPIO_WIDTH"},
            {"name": "irq_o", "direction": "output", "width": 1},
        ],
        "registers": [
            {"name": "OUT", "offset": 0, "width": "GPIO_WIDTH", "access": "RW", "reset": 0},
            {"name": "OE", "offset": 4, "width": "GPIO_WIDTH", "access": "RW", "reset": 0},
            {"name": "IN", "offset": 8, "width": "GPIO_WIDTH", "access": "RO", "reset": 0},
            {"name": "IRQ_EN", "offset": 12, "width": "GPIO_WIDTH", "access": "RW", "reset": 0},
            {"name": "IRQ_STATUS", "offset": 16, "width": "GPIO_WIDTH", "access": "W1C", "reset": 0},
        ],
        "behaviors": [
            {"kind": "rising_edge_latch", "source": "gpio_i", "target": "IRQ_STATUS", "priority": "set_over_clear"}
        ],
        "instances": [{
            "name": "u_apb_regbank", "capability": "apb-register-bank",
            "parameters": {"GPIO_WIDTH": "$parameters.GPIO_WIDTH", "ADDR_WIDTH": 12},
        }],
        "connections": [],
        "address_windows": [{"instance": "u_apb_regbank", "base": 0, "size": 256}],
        "requirements": [
            {"id": req_id, "text": text, "source": "用户确认的 APB GPIO 首版范围", "status": "confirmed"}
            for req_id, text in requirements
        ],
        "acceptance": [
            {"id": "ACC.LINT", "kind": "lint", "requirement_ids": ["REQ.APB", "REQ.RESET", "REQ.GPIO"], "description": "所有参数配置通过 Verilator lint"},
            {"id": "ACC.REG", "kind": "simulation", "requirement_ids": ["REQ.REG", "REQ.APB"], "description": "读写、PSTRB、RO 与 W1C 语义"},
            {"id": "ACC.IRQ", "kind": "simulation", "requirement_ids": ["REQ.IRQ"], "description": "边沿与 set-over-clear 优先级"},
            {"id": "ACC.ERROR", "kind": "simulation", "requirement_ids": ["REQ.ERROR"], "description": "非法、未对齐及 RO 写错误响应"},
        ],
        "open_questions": [],
    }


def _acceptance_relative_path(value: Any) -> str:
    if not isinstance(value, str) or not value or any(
        character in value for character in "\x00\n\r\\"
    ):
        raise SpecificationError("验收输入必须是有效的工程相对文件路径")
    path = PurePosixPath(value)
    if (path.is_absolute() or path.as_posix() in {"", "."}
            or path.as_posix() != value
            or any(part in {".", ".."} for part in path.parts)):
        raise SpecificationError("验收输入不能越出工程或使用非规范路径")
    return value


def _semantic_document(document: Mapping[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(dict(document))
    for key in ("status", "frozen_digest", "acceptance_digest",
                "acceptance_sources_digest", "acceptance_sources_hashes"):
        result.pop(key, None)
    return result


def _digest(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _integer(value: Any) -> int:
    if type(value) is int:
        return value
    if isinstance(value, str):
        return int(value, 0)
    raise TypeError


def _width_supported(value: Any, parameters: Mapping[str, Any]) -> bool:
    return (type(value) is int and 1 <= value <= 32) or (
        isinstance(value, str) and value in parameters
    )


def _register_markdown(document: Mapping[str, Any], registers: list[dict[str, Any]]) -> str:
    if document.get("design_kind") == "generic_module":
        return ""
    lines = [f"# {document.get('name', 'IP')} 寄存器", "", "| 名称 | 地址 | 位宽 | 属性 | 复位值 |", "|---|---:|---:|---|---:|"]
    for item in registers:
        lines.append(
            f"| {item.get('name')} | 0x{int(item.get('offset', 0)):03X} | "
            f"{item.get('width')} | {item.get('access')} | {item.get('reset')} |"
        )
    return "\n".join(lines) + "\n"
