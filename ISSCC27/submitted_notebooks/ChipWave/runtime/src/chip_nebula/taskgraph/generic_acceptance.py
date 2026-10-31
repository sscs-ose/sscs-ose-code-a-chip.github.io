"""Independent checker gate for a frozen generic-module specification.

A checker is a separately authored project input. Passing the real RTL and
rejecting a zero-output mutant demonstrates basic sensitivity, not functional
correctness. Human review freezes its exact bytes before qualified validation.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import uuid
import shlex
import threading
from dataclasses import asdict
from pathlib import Path
from typing import Any, Mapping

from chip_nebula.taskgraph.generic_rtl import (
    GenericRTLContractError, generation_target, generation_sources,
    generation_options, generation_include_files,
)
from chip_nebula.taskgraph.assembly import AssemblyError, AssemblyService, _vendor_directory
from chip_nebula.taskgraph.ip_library import IPLibrary, IPLibraryError
from chip_nebula.taskgraph.tool_executor import DeterministicToolExecutor, ToolCommand


_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_$]*\Z")
_OUTPUT = "build/chip-nebula-acceptance"


class GenericAcceptanceError(ValueError):
    """The checker cannot qualify this frozen specification."""


def _assembly_inputs(root: Path, spec: Mapping[str, Any]) -> dict[str, Any]:
    library = IPLibrary(root)
    try:
        lock = library.read_lock()
        assembly = AssemblyService(root, library).verify_current(spec, lock)
    except (AssemblyError, IPLibraryError) as exc:
        raise GenericAcceptanceError(f"IP 装配尚未固定或已变化：{exc}") from exc
    paths = {"ip/nebula.lock.json", "integration/nebula-assembly.json", "integration/nebula.f", "integration/nebula_assembly.sv"}
    for entry in lock.get("packages", []):
        vendor = _vendor_directory(entry)
        paths.update(f"{vendor}/{item}" for item in entry.get("files", []))
    for entry in lock.get("generated_modules", []):
        paths.update(str(item) for item in entry.get("files", []))
    hashes: dict[str, str] = {}
    for relative in sorted(paths):
        path = root / relative
        if (
            Path(relative).is_absolute() or ".." in Path(relative).parts
            or path.is_symlink() or not path.is_file()
            or not path.resolve().is_relative_to(root)
        ):
            raise GenericAcceptanceError(f"锁定的 IP 装配输入缺失或越界：{relative}")
        hashes[relative] = _sha256(path)
    return {
        "rtl": "integration/nebula_assembly.sv",
        "filelist": "integration/nebula.f",
        "lock_digest": str(lock["lock_digest"]),
        "assembly_digest": str(assembly["assembly_digest"]),
        "source_hashes": hashes,
    }


def verify_assembly_source_hashes(root: Path, contract: Mapping[str, Any]) -> None:
    for relative, expected in contract.get("source_hashes", {}).items():
        path = root / relative
        if (
            not isinstance(relative, str) or Path(relative).is_absolute()
            or ".." in Path(relative).parts or path.is_symlink()
            or not path.is_file() or not path.resolve().is_relative_to(root)
            or _sha256(path) != expected
        ):
            raise GenericAcceptanceError(f"固定快照的 IP 装配输入缺失或已变化：{relative}")


def checker_contract(spec: Mapping[str, Any], root: Path | None = None) -> dict[str, Any]:
    document = spec.get("document", {})
    assembled = bool(document.get("instances"))
    if assembled:
        if root is None:
            raise GenericAcceptanceError("含 IP 实例的验收需要工程路径和已固定装配")
        if not spec.get("configured") or not spec.get("valid") or not spec.get("frozen"):
            raise GenericAcceptanceError("必须先冻结有效的通用 CSIR 规格")
        inputs = _assembly_inputs(root.resolve(), spec)
        source = inputs["rtl"]
    else:
        source = generation_target(spec)
        sources = generation_sources(spec)
        if root is not None:
            project_root = root.resolve()
            for relative in sources:
                source_path = project_root / relative
                if source_path.resolve() != source_path:
                    raise GenericAcceptanceError(
                        f"RTL 编译文件必须位于工程内且不能经过符号链接：{relative}"
                    )
        include_dirs, defines = generation_options(spec)
        # Keep legacy single-file checker contracts byte-for-byte compatible.
        inputs = {"sources": sources} if "rtl_sources" in document else {}
        if include_dirs:
            inputs["include_dirs"] = include_dirs
        if defines:
            inputs["defines"] = defines
    document = spec["document"]
    name = str(document["name"])
    if not _IDENTIFIER.fullmatch(name):
        raise GenericAcceptanceError("通用验收顶层模块名无效")
    all_checks = spec.get("acceptance_plan", {}).get("checks", [])
    if any(
        not isinstance(item, Mapping)
        or item.get("kind") not in {"simulation", "elaboration"}
        for item in all_checks
    ):
        raise GenericAcceptanceError("通用独立验收首期只支持 simulation/elaboration")
    simulation = [item for item in all_checks if item["kind"] == "simulation"]
    elaboration = [item for item in all_checks if item["kind"] == "elaboration"]
    simulation_ids = sorted(str(item.get("id", "")) for item in simulation)
    check_ids = sorted(str(item.get("id", "")) for item in all_checks)
    if not simulation_ids or any(not item for item in check_ids):
        raise GenericAcceptanceError("冻结规格没有独立仿真验收项")
    covered = {
        str(requirement)
        for item in all_checks for requirement in item.get("requirement_ids", [])
    }
    required = set(spec.get("acceptance_plan", {}).get("requirement_ids", []))
    if not required or not required <= covered:
        raise GenericAcceptanceError("独立仿真验收项未覆盖全部需求")
    if any(item.get("direction") == "inout" for item in document.get("ports", [])):
        raise GenericAcceptanceError("当前缺陷注入不支持 inout 端口")
    return {
        "spec_digest": spec["spec_digest"],
        "top_module": name,
        "rtl": source,
        **inputs,
        "testbench": f"tb/{name}_tb.sv",
        "testbench_top": f"{name}_tb",
        "check_ids": check_ids,
        "simulation_ids": simulation_ids,
        "elaboration_ids": sorted(str(item["id"]) for item in elaboration),
    }


def _sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _commands(contract: Mapping[str, Any], rtl: str, suffix: str, timeout: int) -> tuple[ToolCommand, ToolCommand]:
    output = f"{_OUTPUT}/{suffix}.out"
    if contract.get("filelist"):
        sources = ["-f", str(contract["filelist"] if suffix == "real" else f"{_OUTPUT}/mutant.f")]
    elif contract.get("sources"):
        sources = [
            rtl if suffix != "real" and item == contract["rtl"] else item
            for item in contract["sources"]
        ]
    else:
        sources = [rtl]
    compile_command = shlex.join([
        "iverilog", "-g2012", "-s", str(contract["testbench_top"]),
        "-o", output,
        *[f"-I{item}" for item in contract.get("include_dirs", [])],
        *[f"-D{item}" for item in contract.get("defines", [])],
        *sources, str(contract["testbench"]),
    ])
    return (
        ToolCommand(f"{suffix}-compile", compile_command, timeout=timeout),
        ToolCommand(f"{suffix}-simulation", shlex.join(["vvp", output]), timeout=timeout),
    )


def validation_command(contract: Mapping[str, Any]) -> str:
    """Return the exact fixed-snapshot command used for qualified validation."""
    compile_command, run_command = _commands(contract, str(contract["rtl"]), "real", 900)
    return f"mkdir -p {_OUTPUT} && {compile_command.command} && {run_command.command}"


def _zero_output_mutant(spec: Mapping[str, Any]) -> str:
    document = spec["document"]
    parameters = [
        f"parameter int {item['name']} = {item['default']}"
        for item in document.get("parameters", [])
    ]
    parameter_text = f" #({', '.join(parameters)})" if parameters else ""
    ports: list[str] = []
    assignments: list[str] = []
    for item in document.get("ports", []):
        width = item.get("width", 1)
        if isinstance(width, str):
            vector = f"[{width}-1:0] "
        elif type(width) is int and width > 1:
            vector = f"[{width - 1}:0] "
        elif width == 1:
            vector = ""
        else:
            raise GenericAcceptanceError(f"端口 {item.get('name')} 位宽不受缺陷注入支持")
        direction = str(item["direction"])
        name = str(item["name"])
        ports.append(f"{direction} logic {vector}{name}")
        if direction == "output":
            assignments.append(f"  assign {name} = '0;")
    if not assignments:
        raise GenericAcceptanceError("缺陷注入需要至少一个可观察输出端口")
    return (
        f"module {document['name']}{parameter_text}(\n  "
        + ",\n  ".join(ports)
        + "\n);\n"
        + "\n".join(assignments)
        + "\nendmodule\n"
    )


def verify_checker(
    workspace: Path, spec: Mapping[str, Any], *, timeout: int = 120,
    stop_event: threading.Event | None = None,
    contract: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Run the checker on real RTL, then require rejection of a simple mutant."""
    contract = dict(contract or checker_contract(spec, workspace))
    rtl = workspace / contract["rtl"]
    checker = workspace / contract["testbench"]
    diagnostics: list[str] = []
    sources = list(contract.get("sources") or [contract["rtl"]])
    try:
        headers = generation_include_files(workspace, spec) if contract.get("include_dirs") else []
    except GenericRTLContractError as exc:
        diagnostics.append(str(exc))
        headers = []
    for path, label in (
        *((workspace / relative, "RTL 编译文件") for relative in sources),
        (checker, "独立 checker"),
    ):
        if (
            path.resolve() != workspace.resolve() / path.relative_to(workspace)
            or path.is_symlink() or not path.is_file() or path.stat().st_size == 0
        ):
            diagnostics.append(f"{label} 缺失、为空或不是工程内普通文件：{path.relative_to(workspace)}")
    if contract.get("filelist"):
        try:
            verify_assembly_source_hashes(workspace, contract)
        except GenericAcceptanceError as exc:
            diagnostics.append(str(exc))
    if diagnostics:
        return {"status": "not_started", "verdict": "failed", "diagnostics": diagnostics,
                "contract": contract, "command_evidence": [], "tool_versions": {}, "log": ""}
    source_hashes = {relative: _sha256(workspace / relative) for relative in sources}
    header_hashes = {relative: _sha256(workspace / relative) for relative in headers}
    def finish(*args: Any) -> dict[str, Any]:
        report = _report(*args)
        if contract.get("sources"):
            report["rtl_source_hashes"] = source_hashes
        if contract.get("include_dirs"):
            report["rtl_header_hashes"] = header_hashes
        return report
    output = workspace / _OUTPUT
    output.mkdir(parents=True, exist_ok=True)
    executor = DeterministicToolExecutor(stop_event=stop_event)
    real = executor.execute(workspace, _commands(contract, contract["rtl"], "real", timeout))
    evidence = [asdict(item) for item in real.commands]
    versions = dict(real.tool_versions)
    logs = [real.log]
    if real.verdict != "passed":
        diagnostics.append("独立 checker 未能在当前 RTL 上完成编译和仿真")
        return finish(real.status, "failed", contract, checker, rtl, diagnostics, evidence, versions, logs)
    real_markers = set(re.findall(r"(?m)^NEBULA_CHECK[ \t]+([A-Za-z0-9_.-]+)[ \t]+PASS(?:[ \t].*)?$", real.commands[-1].log))
    missing = [
        check_id for check_id in contract["simulation_ids"]
        if check_id not in real_markers
    ]
    if missing:
        diagnostics.append("独立 checker 未报告验收标记：" + "、".join(missing))
        return finish(real.status, "failed", contract, checker, rtl, diagnostics, evidence, versions, logs)
    mutant_path = output / "mutant.sv"
    mutant_path.write_text(_zero_output_mutant(spec), encoding="utf-8")
    if contract.get("filelist"):
        filelist = (workspace / contract["filelist"]).read_text(encoding="utf-8").splitlines()
        original = contract["rtl"]
        if filelist.count(original) != 1:
            raise GenericAcceptanceError("装配 filelist 未唯一列出真实顶层，不能进行缺陷注入")
        (output / "mutant.f").write_text(
            "\n".join(mutant_path.relative_to(workspace).as_posix() if line == original else line
                      for line in filelist) + "\n", encoding="utf-8",
        )
    mutant_compile, mutant_run = _commands(
        contract, mutant_path.relative_to(workspace).as_posix(), "mutant", timeout,
    )
    compiled = executor.execute(workspace, [mutant_compile])
    evidence.extend(asdict(item) for item in compiled.commands)
    versions.update(compiled.tool_versions)
    logs.append(compiled.log)
    if compiled.verdict != "passed":
        diagnostics.append("缺陷注入 RTL 与 checker 未能编译；不能证明验收敏感度")
        return finish(compiled.status, "failed", contract, checker, rtl, diagnostics, evidence, versions, logs)
    rejected = executor.execute(workspace, [mutant_run])
    evidence.extend(asdict(item) for item in rejected.commands)
    versions.update(rejected.tool_versions)
    logs.append(rejected.log)
    if rejected.status in {"timeout", "stopped", "launch_failed"}:
        diagnostics.append("缺陷注入运行超时、停止或无法启动；不能作为有效拒绝")
    elif (
        rejected.status != "failed" or rejected.verdict != "failed"
        or not rejected.commands or not rejected.commands[-1].returncode
        or rejected.commands[-1].returncode < 0
    ):
        diagnostics.append("独立 checker 未拒绝零输出缺陷 RTL；缺陷运行必须以测试失败退出")
    else:
        mutant_log = rejected.commands[-1].log
        failed_checks = set(re.findall(
            r"(?m)^NEBULA_CHECK[ \t]+([A-Za-z0-9_.-]+)[ \t]+FAIL(?:[ \t].*)?$",
            mutant_log,
        ))
        if not re.search(r"(?m)^FATAL:", mutant_log) and not (
            failed_checks & set(contract["simulation_ids"])
        ):
            diagnostics.append("缺陷运行失败但没有 checker 断言证据；不能把工具故障当作验收敏感度")
    return finish(
        rejected.status if diagnostics else "succeeded", "failed" if diagnostics else "passed",
        contract, checker, rtl, diagnostics, evidence, versions, logs,
    )


def _report(
    status: str, verdict: str, contract: dict[str, Any], checker: Path, rtl: Path,
    diagnostics: list[str], evidence: list[dict[str, Any]], versions: dict[str, str],
    logs: list[str],
) -> dict[str, Any]:
    return {
        "status": status, "verdict": verdict, "diagnostics": diagnostics,
        "contract": contract, "checker_sha256": _sha256(checker),
        "rtl_sha256": _sha256(rtl),
        "command_evidence": evidence, "tool_versions": versions,
        "log": "\n".join(logs),
    }


class GenericAcceptanceWorkspace:
    """Freeze a reviewed checker without changing the already-frozen CSIR."""

    def __init__(self, project_root: Path) -> None:
        self.root = project_root.resolve()

    def path(self, spec: Mapping[str, Any]) -> Path:
        return self.root / f"tb/{checker_contract(spec, self.root)['top_module']}.acceptance.json"

    def revisable_prior(self, spec: Mapping[str, Any]) -> dict[str, str]:
        """Identify a previously frozen checker whose bytes still match the old revision.

        Only an explicit plan may supersede this input. A changed checker or an
        unreadable contract requires human review rather than automatic overwrite.
        """
        if not spec.get("frozen") or not spec.get("valid"):
            return {}
        contract = checker_contract(spec, self.root)
        path = self.path(spec)
        checker = self.root / contract["testbench"]
        if (path.is_symlink() or not path.is_file() or checker.is_symlink()
                or not checker.is_file()):
            return {}
        try:
            previous = json.loads(path.read_text(encoding="utf-8"))
            if (
                previous.get("schema_version") != 1
                or not isinstance(previous.get("spec_digest"), str)
                or previous["spec_digest"] == contract["spec_digest"]
                or previous.get("checker") != contract["testbench"]
                or previous.get("checker_sha256") != _sha256(checker)
                or previous.get("self_test", {}).get("verdict") != "passed"
            ):
                return {}
        except (OSError, UnicodeError, json.JSONDecodeError, AttributeError, KeyError, TypeError):
            return {}
        return {"spec_digest": previous["spec_digest"], "checker": contract["testbench"]}

    def compiler_options_only_revision(self, spec: Mapping[str, Any]) -> bool:
        """Route an old checker straight to review only when behavior is unchanged."""
        prior = self.revisable_prior(spec)
        digest = prior.get("spec_digest", "")
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
            return False
        archive = (
            self.root / ".chip_nebula" / "design" / "specs"
            / str(spec["document"]["spec_id"]) / f"{digest.removeprefix('sha256:')}.json"
        )
        if archive.is_symlink() or not archive.is_file():
            return False
        try:
            previous = json.loads(archive.read_text(encoding="utf-8"))
            old_document = previous["document"]
            new_document = spec["document"]
            if previous.get("spec_digest") != digest or not isinstance(old_document, dict):
                return False
            ignored = {
                "revision", "status", "frozen_digest", "acceptance_digest",
                "rtl_include_dirs", "rtl_defines",
            }
            old_base = {key: value for key, value in old_document.items() if key not in ignored}
            new_base = {key: value for key, value in new_document.items() if key not in ignored}
            options_changed = any(
                old_document.get(key, []) != new_document.get(key, [])
                for key in ("rtl_include_dirs", "rtl_defines")
            )
            return options_changed and old_base == new_base
        except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError):
            return False

    def state(self, spec: Mapping[str, Any]) -> dict[str, Any]:
        contract = checker_contract(spec, self.root)
        path = self.path(spec)
        result = {"frozen": False, "valid": False, "path": path.relative_to(self.root).as_posix(),
                  "checker": contract["testbench"], "spec_digest": contract["spec_digest"],
                  "compiler_options_only_revision": self.compiler_options_only_revision(spec)}
        if not path.is_file() or path.is_symlink():
            result["reason"] = "独立 checker 尚未由用户审核冻结"
            return result
        try:
            frozen = json.loads(path.read_text(encoding="utf-8"))
            checker = self.root / contract["testbench"]
            valid = (
                frozen.get("schema_version") == 1
                and frozen.get("spec_digest") == contract["spec_digest"]
                and frozen.get("check_ids") == contract["check_ids"]
                and frozen.get("simulation_ids") == contract["simulation_ids"]
                and frozen.get("elaboration_ids") == contract["elaboration_ids"]
                and frozen.get("checker") == contract["testbench"]
                and frozen.get("runner") == validation_command(contract)
                and (not any(contract.get(key) for key in (
                    "filelist", "sources", "include_dirs", "defines",
                )) or frozen.get("checker_contract") == contract)
                and not checker.is_symlink() and checker.is_file()
                and frozen.get("checker_sha256") == _sha256(checker)
                and frozen.get("self_test", {}).get("verdict") == "passed"
            )
        except (OSError, UnicodeError, json.JSONDecodeError, AttributeError):
            valid = False
            frozen = {}
        if not valid:
            result["reason"] = "冻结 checker、规格或运行入口已变化；需要新版本审核"
            return result
        result.update({
            "frozen": True, "valid": True,
            "source_digest": str(frozen["checker_sha256"]),
            "contract_digest": _sha256(path),
            "revision": int(frozen.get("revision", 1)),
            "supersedes": str(frozen.get("supersedes", "")),
            "check_ids": list(frozen["check_ids"]),
            "runner": str(frozen["runner"]),
            "self_test": frozen["self_test"],
            "contract": contract,
        })
        return result

    def freeze(
        self, spec: Mapping[str, Any], report: Mapping[str, Any], *,
        snapshot_commit: str,
    ) -> dict[str, Any]:
        contract = checker_contract(spec, self.root)
        checker = self.root / contract["testbench"]
        if report.get("verdict") != "passed" or report.get("contract") != contract:
            raise GenericAcceptanceError("独立 checker 自检未通过，不能冻结")
        if checker.is_symlink() or not checker.is_file() or report.get("checker_sha256") != _sha256(checker):
            raise GenericAcceptanceError("checker 在自检后发生变化，请重新运行自检")
        rtl = self.root / contract["rtl"]
        if rtl.is_symlink() or not rtl.is_file() or report.get("rtl_sha256") != _sha256(rtl):
            raise GenericAcceptanceError("RTL 在 checker 自检后发生变化，请重新运行自检")
        if contract.get("sources"):
            current_sources = {
                relative: _sha256(self.root / relative)
                for relative in contract["sources"]
                if (self.root / relative).resolve() == self.root / relative
                and (self.root / relative).is_file()
            }
            if report.get("rtl_source_hashes") != current_sources or len(current_sources) != len(contract["sources"]):
                raise GenericAcceptanceError("RTL 编译依赖在 checker 自检后变化，请重新运行自检")
        if contract.get("include_dirs"):
            try:
                current_headers = {
                    relative: _sha256(self.root / relative)
                    for relative in generation_include_files(self.root, spec)
                }
            except GenericRTLContractError as exc:
                raise GenericAcceptanceError(str(exc)) from exc
            if report.get("rtl_header_hashes") != current_headers:
                raise GenericAcceptanceError("Include 头文件在 checker 自检后变化，请重新运行自检")
        path = self.path(spec)
        prior_bytes = b""
        prior_digest = ""
        prior_revision = 0
        prior_archive = ""
        if path.exists() or path.is_symlink():
            if path.is_symlink() or not path.is_file():
                raise GenericAcceptanceError("已有冻结 checker 契约不是普通文件，不能覆盖")
            prior_bytes = path.read_bytes()
            try:
                prior = json.loads(prior_bytes.decode("utf-8"))
                if not isinstance(prior, dict) or prior.get("schema_version") != 1:
                    raise ValueError("invalid schema")
                prior_revision = int(prior.get("revision", 1))
                if prior_revision < 1:
                    raise ValueError("invalid revision")
            except (UnicodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
                raise GenericAcceptanceError("已有冻结 checker 契约损坏，不能覆盖") from exc
            if self.state(spec).get("valid"):
                raise GenericAcceptanceError("已有冻结 checker；同一版本不能重复冻结")
            prior_digest = "sha256:" + hashlib.sha256(prior_bytes).hexdigest()
            archive = (
                self.root / "spec" / "acceptance" / contract["top_module"]
                / f"{prior_digest.removeprefix('sha256:')}.json"
            )
            if archive.exists():
                if archive.is_symlink() or not archive.is_file() or archive.read_bytes() != prior_bytes:
                    raise GenericAcceptanceError("历史验收契约归档冲突，不能覆盖")
            else:
                archive.parent.mkdir(parents=True, exist_ok=True)
                with archive.open("xb") as stream:
                    stream.write(prior_bytes)
            prior_archive = archive.relative_to(self.root).as_posix()
        document = {
            "schema_version": 1,
            "revision": prior_revision + 1,
            "supersedes": prior_digest,
            "previous_contract": prior_archive,
            "spec_digest": contract["spec_digest"],
            "check_ids": contract["check_ids"],
            "simulation_ids": contract["simulation_ids"],
            "elaboration_ids": contract["elaboration_ids"],
            "checker": contract["testbench"],
            "checker_sha256": report["checker_sha256"],
            "runner": validation_command(contract),
            "checker_contract": contract,
            "self_test": {
                "verdict": "passed", "snapshot_commit": snapshot_commit,
                "rtl_sha256": report["rtl_sha256"],
                **({"rtl_source_hashes": report["rtl_source_hashes"]}
                   if contract.get("sources") else {}),
                **({"rtl_header_hashes": report["rtl_header_hashes"]}
                   if contract.get("include_dirs") else {}),
                "tool_versions": report.get("tool_versions", {}),
                "mutation": "zero_output_stub_rejected",
            },
            "frozen_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        try:
            with temporary.open("x", encoding="utf-8") as stream:
                stream.write(json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
        return self.state(spec)
