"""Frozen generic CSIR contract for a project-owned generated child module.

A generated child is not an IP package and is never accepted on the strength
of its generator's self-test. Its exact source bytes enter the IP lock and the
assembled parent must pass an independent acceptance contract.
"""

from __future__ import annotations

import hashlib
import json
import re
import threading
from pathlib import Path
from typing import Any, Mapping

from chip_nebula.taskgraph.generic_rtl import verify_generated_rtl


_SV_ID = re.compile(r"[A-Za-z_][A-Za-z0-9_$]*\Z")


class GeneratedSubmoduleError(ValueError):
    pass


def submodule_contract(
    spec: Mapping[str, Any], instance_name: str,
) -> dict[str, Any]:
    """Return the exact child contract from a valid frozen generic CSIR."""
    document = spec.get("document", {})
    if (
        not spec.get("valid") or not spec.get("frozen")
        or not isinstance(document, Mapping)
        or document.get("design_kind") not in {"generic_module", "single_clock_soc"}
    ):
        raise GeneratedSubmoduleError("生成子模块需要有效且冻结的 CSIR")
    matches = [
        item for item in document.get("instances", [])
        if isinstance(item, Mapping) and item.get("name") == instance_name
    ]
    if len(matches) != 1 or matches[0].get("capability") != "generated-rtl":
        raise GeneratedSubmoduleError(f"冻结规格未声明唯一的生成子模块实例：{instance_name}")
    instance = matches[0]
    generated = instance.get("generated_module")
    if not isinstance(generated, Mapping):
        raise GeneratedSubmoduleError("生成子模块缺少接口与行为契约")
    module = generated.get("name")
    if not isinstance(module, str) or not _SV_ID.fullmatch(module):
        raise GeneratedSubmoduleError("生成子模块名无效")
    ports = generated.get("ports")
    if not isinstance(ports, list) or not ports:
        raise GeneratedSubmoduleError("生成子模块没有端口契约")
    return {
        "instance": instance_name,
        "module": module,
        "source": f"rtl/{module}.sv",
        "ports": ports,
        "behavior": generated.get("behavior", ""),
        "requirement_ids": generated.get("requirement_ids", []),
        "spec_digest": str(spec["spec_digest"]),
    }


def generated_submodules(spec: Mapping[str, Any]) -> list[dict[str, Any]]:
    document = spec.get("document", {})
    return [
        submodule_contract(spec, str(item["name"]))
        for item in document.get("instances", [])
        if isinstance(item, Mapping) and item.get("capability") == "generated-rtl"
    ]


def source_record(
    root: Path, spec: Mapping[str, Any], instance_name: str,
) -> dict[str, Any]:
    """Bind one child source to frozen CSIR without claiming functional pass."""
    contract = submodule_contract(spec, instance_name)
    root = root.resolve()
    path = root / contract["source"]
    if (
        path.is_symlink() or not path.is_file() or path.stat().st_size == 0
        or not path.resolve().is_relative_to(root)
    ):
        raise GeneratedSubmoduleError(
            f"冻结规格要求的生成子模块 RTL 缺失或越界：{contract['source']}"
        )
    source_digest = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
    contract_digest = _digest(contract)
    generation_digest = _digest({
        "spec_digest": contract["spec_digest"],
        "instance": instance_name,
        "source_digest": source_digest,
        "contract_digest": contract_digest,
    })
    return {
        **contract,
        "contract_digest": contract_digest,
        "source_digest": source_digest,
        "generation_digest": generation_digest,
        "files": [contract["source"]],
        "file_hashes": {contract["source"]: source_digest},
    }


def verify_submodule(
    workspace: Path, spec: Mapping[str, Any], instance_name: str, *,
    timeout: int = 120, stop_event: threading.Event | None = None,
) -> dict[str, Any]:
    """Use real Verilator AST to check the exact child module and ports."""
    contract = submodule_contract(spec, instance_name)
    synthetic = {
        "configured": True,
        "valid": True,
        "frozen": True,
        "spec_digest": contract["spec_digest"],
        "document": {
            "design_kind": "generic_module",
            "name": contract["module"],
            "instances": [],
            "parameters": [],
            "ports": contract["ports"],
        },
    }
    return verify_generated_rtl(
        workspace, synthetic, timeout=timeout, stop_event=stop_event,
    )


def _digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        .encode("utf-8")
    ).hexdigest()
