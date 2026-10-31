"""Read-only architecture and IP selection preview for a CSIR design."""

from __future__ import annotations

import re
from typing import Any, Mapping

from chip_nebula.taskgraph.ip_library import IPLibrary, supports_capability, supports_generic_named_port
from chip_nebula.taskgraph.memory_generator import MemoryGenerator
from chip_nebula.taskgraph.soc_assembly import supports_soc_package


class ArchitecturePlanner:
    """Explain reuse, adapter and missing-RTL decisions before any source write."""

    def __init__(self, library: IPLibrary) -> None:
        self.library = library

    def preview(self, spec: Mapping[str, Any]) -> dict[str, Any]:
        document = spec.get("document", {})
        if not isinstance(document, Mapping):
            document = {}
        lock = self.library.read_lock(optional=True)
        if document.get("design_kind") == "generic_module" and not document.get("instances"):
            name = str(document.get("name", ""))
            target = (
                f"rtl/{name}.sv"
                if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_$]*", name) else ""
            )
            present = bool(
                target and (self.library.project_root / target).is_file()
            )
            blockers = []
            if not spec.get("valid"):
                blockers.append("规格诊断未通过")
            if not spec.get("frozen"):
                blockers.append("规格与独立验收尚未冻结")
            blockers.append(
                "独立功能验收尚未完成" if present
                else "当前模块尚无 RTL；进入 RTL Analysis 生成并展开"
            )
            return {
                "schema_version": 1,
                "spec_digest": str(spec.get("spec_digest", "")),
                "lock_digest": str(lock.get("lock_digest", "")),
                "top_module": name,
                "design_kind": "generic_module",
                "clocks": list(document.get("clocks", [])),
                "resets": list(document.get("resets", [])),
                "address_windows": [],
                "connections": [],
                "decisions": [{
                    "instance": name, "capability": "generic-rtl-module",
                    "action": "inspect" if present else "generate",
                    "status": "rtl_present_unverified" if present else "generation_required",
                    "package_id": "", "version": "", "rtl": target,
                    "reason": (
                        "工程已有 RTL；必须核对其规格版本和独立验收证据"
                        if present else
                        "无 IP 实例；从冻结 CSIR 生成该独立模块的 RTL"
                    ),
                }],
                "blockers": blockers,
                "ready_for_assembly": False,
                "ready_for_rtl_generation": (
                    bool(spec.get("valid") and spec.get("frozen") and target)
                    and not present
                ),
            }
        packages = self.library.packages()
        generated = MemoryGenerator(self.library.project_root).current(spec)
        generated_by_instance = {
            item["instance"]: item for item in generated.get("modules", [])
        } if generated else {}
        decisions: list[dict[str, Any]] = []
        blockers: list[str] = []
        for instance in document.get("instances", []):
            if not isinstance(instance, Mapping):
                continue
            name = str(instance.get("name", ""))
            capability = str(instance.get("capability", ""))
            requested = str(instance.get("package", ""))
            requested_version = str(instance.get("version", ""))
            matching = [
                item for item in packages
                if (not requested or item.package_id == requested)
                and (not requested_version or item.version == requested_version)
                and (not capability or supports_capability(capability, item.manifest))
            ]
            candidates = self.library._candidates(instance, document, lock)
            if candidates:
                package, evidence = candidates[0]
                generator = package.manifest.get("generator", {})
                assembly_supported = (
                    supports_soc_package(capability, package.manifest["top_module"])
                    if document.get("design_kind") == "single_clock_soc"
                    else supports_generic_named_port(package.manifest)
                    if document.get("design_kind") == "generic_module"
                    else generator.get("kind") == "apb-gpio-wrapper-v1"
                )
                decision = {
                    "instance": name,
                    "capability": capability,
                    "action": "adapt" if capability == "native-apb-bridge" else "reuse",
                    "status": "selected" if assembly_supported else "assembly_required",
                    "package_id": package.package_id,
                    "version": package.version,
                    "content_digest": package.content_digest,
                    "top_module": package.manifest["top_module"],
                    "qualified_parameters": [item.get("parameters", {}) for item in evidence],
                    "alternatives": [item.key for item, _ in candidates[1:]],
                    "reason": "来源已审核，当前参数与接口有真实工具验证证据",
                }
                if not assembly_supported:
                    blockers.append(f"{name}：当前装配器尚不能连接该 IP 到系统顶层")
            elif matching:
                pending = [
                    item for item in matching
                    if item.manifest["source"]["review"]["status"] != "approved"
                ]
                hard_only = all(
                    item.manifest.get("implementation", {}).get("kind") == "hard_macro"
                    for item in matching
                )
                reason = (
                    "硬 IP 已登记物理视图，但物理宏集成尚未接入，不能自动复用"
                    if hard_only else
                    "IP 来源审核尚未通过，不能自动复用"
                    if pending else "缺少当前参数、接口或工具配置的合格证据"
                )
                decision = {
                    "instance": name, "capability": capability,
                    "action": "review" if pending or hard_only else "qualify",
                    "status": "blocked", "package_id": "", "version": "",
                    "available_packages": [item.key for item in matching],
                    "reason": reason,
                }
                blockers.append(f"{name}：{reason}")
            else:
                generated_module = generated_by_instance.get(name)
                decision = {
                    "instance": name, "capability": capability,
                    "action": "generate",
                    "status": "generated_unverified" if generated_module else "generation_required",
                    "package_id": "", "version": "",
                    "available_packages": [],
                    "reason": (
                        "冻结规格已生成版本化 RTL，可进入装配；独立验收尚未完成"
                        if generated_module else
                        "目录没有符合该功能的 IP；需要生成 RTL 和独立验收"
                    ),
                }
                if generated_module:
                    decision.update({
                        "top_module": generated_module["module"],
                        "generated_rtl": generated_module["rtl"],
                        "generation_digest": generated["generation_digest"],
                    })
                if not generated_module:
                    blockers.append(f"{name}：缺少可复用 IP，需要生成并验收 RTL")
            decisions.append(decision)
        if not spec.get("valid"):
            blockers.insert(0, "规格诊断未通过")
        if not spec.get("frozen"):
            blockers.insert(0, "规格与独立验收尚未冻结")
        if not decisions:
            blockers.append("规格没有可装配的实例")
        return {
            "schema_version": 1,
            "spec_digest": str(spec.get("spec_digest", "")),
            "lock_digest": str(lock.get("lock_digest", "")),
            "top_module": str(document.get("name", "")),
            "design_kind": str(document.get("design_kind", "")),
            "clocks": list(document.get("clocks", [])),
            "resets": list(document.get("resets", [])),
            "address_windows": list(document.get("address_windows", [])),
            "connections": list(document.get("connections", [])),
            "decisions": decisions,
            "blockers": blockers,
            "ready_for_assembly": not blockers,
        }
