"""Read-only plan for qualifying an imported generic-module checker.

The checker and RTL are already present. This task only runs tools against a
fixed snapshot; it never grants an Agent write scope or freezes acceptance.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from chip_nebula.taskgraph.generic_acceptance import (
    GenericAcceptanceError, GenericAcceptanceWorkspace, checker_contract,
    validation_command,
)
from chip_nebula.taskgraph.generic_rtl import GenericRTLContractError, generation_include_files


def _sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def preview_existing_checker(
    root: Path, spec: Mapping[str, Any], *, git_repository: bool,
) -> dict[str, Any]:
    """Bind a tool-only self-test to exact existing inputs before it can run."""
    blockers: list[str] = []
    if not git_repository:
        blockers.append("工程尚未建立 Git 基线，无法创建固定快照")
    if not spec.get("frozen") or not spec.get("valid"):
        blockers.append("请先确认并冻结有效的通用模块规格")
    if spec.get("document", {}).get("design_kind") != "generic_module":
        blockers.append("现有 checker 自检仅支持已冻结的通用模块规格")
    contract: dict[str, Any] = {}
    try:
        contract = checker_contract(spec, root)
    except (GenericAcceptanceError, GenericRTLContractError, KeyError, TypeError) as exc:
        blockers.append(str(exc))
    rtl = str(contract.get("rtl", ""))
    checker = str(contract.get("testbench", ""))
    hashes: dict[str, str] = {}
    try:
        extra_inputs = (
            generation_include_files(root, spec) if contract.get("include_dirs") else []
        )
    except GenericRTLContractError as exc:
        blockers.append(str(exc))
        extra_inputs = []
    for relative in dict.fromkeys([
        rtl, checker, *contract.get("sources", []),
        *contract.get("source_hashes", {}), *extra_inputs,
    ]):
        if not relative:
            continue
        source = root / relative
        if (
            source.resolve() != root.resolve() / relative
            or source.is_symlink() or not source.is_file()
            or (relative in {rtl, checker} and source.stat().st_size == 0)
        ):
            blockers.append(f"现有 checker 自检输入缺失、为空或不是工程内普通文件：{relative}")
        else:
            hashes[relative] = _sha256(source)
    acceptance_path = ""
    if contract and spec.get("frozen") and spec.get("valid"):
        workspace = GenericAcceptanceWorkspace(root)
        acceptance = workspace.state(spec)
        acceptance_path = acceptance["path"]
        if acceptance.get("frozen"):
            blockers.append("当前规格的独立 checker 已冻结；可以直接运行正式验收")
        path = root / acceptance_path
        if path.exists() or path.is_symlink():
            try:
                if path.is_symlink() or not path.is_file():
                    raise ValueError("invalid acceptance contract path")
                previous = json.loads(path.read_text(encoding="utf-8"))
                if (
                    not isinstance(previous, dict)
                    or previous.get("schema_version") != 1
                    or type(previous.get("revision")) is not int
                    or previous["revision"] < 1
                ):
                    raise ValueError("invalid acceptance contract")
            except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
                blockers.append("旧版验收契约损坏；请先人工修复，不能生成可冻结候选")
    plan = {
        "schema_version": 1,
        "kind": "existing_checker_review",
        "spec_digest": str(spec.get("spec_digest", "")),
        "rtl": rtl,
        "checker": checker,
        "acceptance_path": acceptance_path,
        "input_hashes": hashes,
        "command": validation_command(contract) if contract else "",
        "write_paths": [],
        "ready": not blockers,
        "blockers": blockers,
        "review_gate": "工具自检通过后仍须审核 checker 与需求覆盖，再人工冻结",
    }
    plan["plan_digest"] = "sha256:" + hashlib.sha256(
        json.dumps(plan, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        .encode("utf-8")
    ).hexdigest()
    return plan
