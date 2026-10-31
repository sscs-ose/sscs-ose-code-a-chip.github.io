"""Read-only preparation plan for a frozen standalone generic module."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping

from chip_nebula.taskgraph.generic_acceptance import (
    GenericAcceptanceError, GenericAcceptanceWorkspace, checker_contract,
)
from chip_nebula.taskgraph.generic_rtl import GenericRTLContractError, generation_include_files


def preview_generic_product(root: Path, spec: Mapping[str, Any]) -> dict[str, Any]:
    root = root.resolve()
    document = spec.get("document", {})
    blockers: list[str] = []
    if not spec.get("frozen") or not spec.get("valid"):
        blockers.append("通用 CSIR 必须由用户确认并保持冻结有效")
    if document.get("design_kind") != "generic_module":
        blockers.append("当前设计不是独立通用模块")
    target = document.get("technical_target")
    clocks = document.get("clocks", [])
    physical_blockers: list[str] = []
    if (
        not isinstance(target, dict)
        or target.get("platform") != "sky130hd"
        or target.get("pvt") != "tt"
        or type(target.get("clock_period_ns")) not in {int, float}
        or not 0.01 <= target["clock_period_ns"] <= 1_000_000
        or not math.isfinite(target["clock_period_ns"])
        or not isinstance(clocks, list) or len(clocks) != 1
    ):
        physical_blockers.append("GDS 需要冻结的单时钟 Sky130HD TT 目标和有效周期；功能验收可先运行")
    rtl = ""
    source_digest = ""
    source_hashes: dict[str, str] = {}
    checker_path = ""
    acceptance_digest = ""
    try:
        contract = checker_contract(spec, root)
        rtl = contract["rtl"]
        checker_path = contract["testbench"]
        source_hashes = {}
        for relative in contract.get("sources") or [rtl]:
            source = root / relative
            if (
                source.resolve() != source or source.is_symlink()
                or not source.is_file() or not source.stat().st_size
            ):
                blockers.append(f"设计 RTL 编译文件缺失或无效：{relative}")
            else:
                source_hashes[relative] = "sha256:" + hashlib.sha256(source.read_bytes()).hexdigest()
        if contract.get("include_dirs"):
            for relative in generation_include_files(root, spec):
                source_hashes[relative] = (
                    "sha256:" + hashlib.sha256((root / relative).read_bytes()).hexdigest()
                )
        source_digest = source_hashes.get(rtl, "")
        acceptance = GenericAcceptanceWorkspace(root).state(spec)
        if not acceptance.get("valid"):
            blockers.append(
                "独立 checker 未冻结或版本已失效：" + acceptance.get("reason", "")
            )
        else:
            acceptance_digest = str(acceptance["contract_digest"])
    except (GenericAcceptanceError, GenericRTLContractError, OSError, ValueError) as exc:
        blockers.append(str(exc))
    plan = {
        "schema_version": 1,
        "design_kind": "generic_module",
        "spec_digest": str(spec.get("spec_digest", "")),
        "acceptance_sources_digest": "",
        "top_module": str(document.get("name", "")),
        "technical_target": target if isinstance(target, dict) else {},
        "rtl": rtl,
        "rtl_sha256": source_digest,
        "source_hashes": source_hashes,
        "testbench": checker_path,
        "acceptance_contract_digest": acceptance_digest,
        "ready": not blockers,
        "blockers": blockers,
        "product_ready": not blockers,
        "product_blockers": blockers,
        "physical_ready": not blockers and not physical_blockers,
        "physical_blockers": physical_blockers,
        "decisions": [{
            "instance": str(document.get("name", "")),
            "action": "use-project-rtl",
            "source": rtl,
            "reason": "冻结通用 CSIR 的独立顶层源码",
        }] if rtl else [],
        "qualifications": [],
        "generated_instances": [],
        "final_steps": [
            "fixed-snapshot-acceptance", "frozen-target-physical-setup",
            "rtl-to-gds-signoff", "delivery-check",
        ],
    }
    plan["plan_digest"] = "sha256:" + hashlib.sha256(
        json.dumps(plan, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return plan
