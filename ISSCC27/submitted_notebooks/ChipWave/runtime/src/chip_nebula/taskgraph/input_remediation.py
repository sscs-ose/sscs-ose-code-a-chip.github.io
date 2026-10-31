"""Classify audited project-input gaps before proposing an Agent write.

An input audit is read-only. Only a missing, project-owned RTL module with a
valid frozen generic CSIR can become a design-Agent operation. Other inputs
keep their separate authority and are never synthesized from a model guess.
"""

from __future__ import annotations

from typing import Any, Mapping

from chip_nebula.taskgraph.generic_rtl import GenericRTLContractError, generation_target
from chip_nebula.taskgraph.generated_submodule import (
    GeneratedSubmoduleError, generated_submodules,
)


def propose_input_remediation(
    issue: Mapping[str, Any], specification: Mapping[str, Any],
) -> dict[str, Any]:
    """Return an exact-scope proposal, or an explicit reason it is unavailable."""
    path = str(issue.get("path", ""))
    result: dict[str, Any] = {
        "schema_version": 1,
        "issue_code": str(issue.get("code", "")),
        "path": path,
        "category": str(issue.get("category", "")),
        "spec_digest": str(specification.get("spec_digest", "")),
        "eligible": False,
        "stage": "",
        "workspace": "",
        "write_paths": [],
        "instruction": "",
        "blockers": [],
    }
    if issue.get("code") != "missing_required_input":
        result["blockers"].append("该缺项没有可核对的受控补全契约")
        return result
    if issue.get("category") != "design" or issue.get("agent_candidate") is not True:
        result["blockers"].append(
            "此输入须按其来源恢复或重新确认；设计 Agent 无权生成约束、验收依据、IP 或流程资产"
        )
        return result
    try:
        children = generated_submodules(specification)
        targets = [item["source"] for item in children]
        if not specification.get("document", {}).get("instances"):
            targets.append(generation_target(specification))
    except (GeneratedSubmoduleError, GenericRTLContractError, KeyError, TypeError) as exc:
        result["blockers"].append(str(exc))
        return result
    if path not in targets:
        result["blockers"].append(
            f"缺失路径 {path} 不在冻结规格授权生成的 RTL 清单中：{', '.join(targets) or '无'}"
        )
        return result
    target = path
    result.update({
        "eligible": True,
        "stage": "rtl_generation",
        "workspace": "rtl-analysis",
        "write_paths": [target],
        "instruction": (
            f"物理输入审查发现 {target} 缺失。根据冻结的 "
            f"spec/design.csir.yaml（规格摘要 {result['spec_digest']}）完整实现该模块。"
            "仅可写入授权的 RTL 文件；接口、复位、周期行为和需求 ID 必须以冻结规格为准。"
            "不得修改规格、独立 checker、验收用例、IP 库、物理约束或工具脚本。"
            "生成后由平台在固定快照检查 Verilator 展开与端口契约；"
            "功能验收须由独立冻结 checker 另行判定。"
        ),
    })
    return result
