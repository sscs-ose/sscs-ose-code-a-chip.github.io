"""Read-only readiness audit for project-owned SoC acceptance inputs.

This checks whether the declared checker inputs can be frozen and whether the
contract names the current CSIR. It does not infer that the checker is correct
or that any simulation has passed.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from chip_nebula.taskgraph.assembly import AssemblyError, AssemblyService
from chip_nebula.taskgraph.ip_library import IPLibrary
from chip_nebula.taskgraph.soc_assembly import SoCAssemblyError, render_soc_verification
from chip_nebula.taskgraph.specs import SpecificationError, SpecificationWorkspace


def audit_soc_acceptance(root: Path, spec: Mapping[str, Any]) -> dict[str, Any] | None:
    """Explain missing SoC checker inputs before attempting product preparation."""
    document = spec.get("document", {})
    if not isinstance(document, Mapping) or document.get("design_kind") != "single_clock_soc":
        return None

    blockers: list[str] = []
    if not spec.get("valid"):
        blockers.append("CSIR 编译或冻结输入完整性检查尚未通过")
    if not spec.get("frozen"):
        blockers.append("规格与验收输入尚未由用户冻结")

    sources = document.get("acceptance_sources")
    if not isinstance(sources, list) or not sources:
        blockers.append("缺少验收输入清单 acceptance_sources")
    else:
        try:
            SpecificationWorkspace(root)._source_hashes(document)
        except SpecificationError as exc:
            blockers.append(str(exc))

    contract_path = "tb/acceptance-contract.json"
    if not isinstance(sources, list) or contract_path not in sources:
        blockers.append(f"{contract_path} 未列入验收输入；当前检查点没有绑定规格版本")
    else:
        try:
            AssemblyService(root, IPLibrary(root)).verify_acceptance_contract(spec)
        except AssemblyError as exc:
            blockers.append(str(exc))

    # The built-in runner is only defined for its exact reviewed source set.
    # A project-specific runner must itself be present in acceptance_sources.
    try:
        render_soc_verification(document, (
            {"capability": "program-rom", "top_module": "program_rom"},
            {"capability": "register-ram", "top_module": "register_ram"},
        ))
    except (SoCAssemblyError, KeyError, TypeError, ValueError) as exc:
        blockers.append(f"独立验收入口不可复现：{exc}")

    checks = spec.get("acceptance_plan", {}).get("checks", [])
    planned = sorted(
        str(item.get("id", "")) for item in checks
        if isinstance(item, Mapping) and item.get("status", "planned") != "implemented"
    )
    if planned:
        blockers.append("尚未登记为已实现的验收项：" + "、".join(planned))
    if spec.get("frozen") and not spec.get("acceptance_sources_digest"):
        blockers.append("冻结验收输入缺少有效内容摘要")

    return {
        "status": "blocked" if blockers else "inputs_ready",
        "spec_digest": str(spec.get("spec_digest", "")),
        "acceptance_sources_digest": str(spec.get("acceptance_sources_digest", "")),
        "source_count": len(sources) if isinstance(sources, list) else 0,
        "check_ids": sorted(
            str(item.get("id", "")) for item in checks if isinstance(item, Mapping)
        ),
        "blockers": list(dict.fromkeys(blockers)),
    }
