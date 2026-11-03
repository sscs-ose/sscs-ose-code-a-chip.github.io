"""Durable, scoped preparation of generic RTL and independent acceptance.

The workflow stops at human acceptance review. It never freezes a checker or
turns a generator's self-test into a product validation verdict.
"""

from __future__ import annotations

import datetime as dt
import fcntl
import hashlib
import json
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Callable

from chip_nebula.adapters.scope_check import violations
from chip_nebula.taskgraph.generic_acceptance import (
    GenericAcceptanceError, GenericAcceptanceWorkspace, checker_contract,
)
from chip_nebula.taskgraph.generic_rtl import GenericRTLContractError, generation_include_files
from chip_nebula.taskgraph.generated_submodule import (
    GeneratedSubmoduleError, generated_submodules,
)
from chip_nebula.taskgraph.specs import SpecificationWorkspace


class GenericBootstrapError(ValueError):
    """A frozen generic design cannot be prepared safely."""


class GenericBootstrapRunner:
    """Connect existing Task Graph Agent operations under one root budget."""

    ACTIVE = {"starting", "running", "stop_requested"}
    MAX_REPAIRS = 3

    def __init__(
        self, project: Any, runs: Any, *,
        other_active: Callable[[], bool] | None = None,
    ) -> None:
        self.project = project
        self.runs = runs
        self.other_active = other_active or (lambda: False)
        self.root = project.root / ".chip_nebula" / "generic-bootstrap"
        self.root.mkdir(parents=True, exist_ok=True)
        self.lock_path = self.root / "active.lock"
        self._mutex = threading.RLock()
        self._stop_event = threading.Event()
        self._active_id = ""
        self._active_operation_id = ""
        self._lock_handle: Any = None
        self._thread: threading.Thread | None = None
        self._recover_interrupted()

    @staticmethod
    def _now() -> str:
        return dt.datetime.now(dt.timezone.utc).isoformat()

    def _path(self, identifier: str) -> Path:
        if not identifier.startswith("bootstrap-") or len(identifier) != 22 or not all(
            char in "0123456789abcdef" for char in identifier[10:]
        ):
            raise GenericBootstrapError("invalid generic bootstrap id")
        return self.root / f"{identifier}.json"

    def _write(self, record: dict[str, Any]) -> None:
        path = self._path(record["id"])
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(record, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary.replace(path)

    def get(self, identifier: str) -> dict[str, Any]:
        path = self._path(identifier)
        if not path.is_file():
            raise GenericBootstrapError("generic bootstrap not found")
        return json.loads(path.read_text(encoding="utf-8"))

    def list(self) -> list[dict[str, Any]]:
        records = []
        for path in self.root.glob("bootstrap-*.json"):
            try:
                records.append(json.loads(path.read_text(encoding="utf-8")))
            except (OSError, json.JSONDecodeError):
                continue
        return sorted(records, key=lambda item: item.get("created_at", ""), reverse=True)

    def _recover_interrupted(self) -> None:
        with self.lock_path.open("a+b") as handle:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return
            try:
                for record in self.list():
                    if record.get("status") not in self.ACTIVE:
                        continue
                    record.update({
                        "status": "interrupted",
                        "reason": "后端中断；已产生的 RTL、checker 与 Agent 记录保留，不自动重放",
                        "finished_at": self._now(),
                    })
                    self._write(record)
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def _preview_soc_adapter(self, state: dict[str, Any]) -> dict[str, Any]:
        """Plan exact generated SoC children before locked assembly.

        SoC checker inputs are already frozen separately. No checker is made or
        approved by this preparation path.
        """
        from chip_nebula.dashboard.design_delivery import DesignDeliveryService
        from chip_nebula.taskgraph.assembly import AssemblyError
        from chip_nebula.taskgraph.ip_library import IPLibraryError

        blockers: list[str] = []
        root = self.project.root
        if not state.get("valid") or not state.get("frozen"):
            blockers.append("需要先确认并冻结有效的 SoC CSIR 与独立验收")
        document = state.get("document", {})
        try:
            children = generated_submodules(state)
        except (GeneratedSubmoduleError, KeyError, TypeError) as exc:
            blockers.append(str(exc))
            children = []
        if not children:
            blockers.append("冻结 SoC 未声明需要生成的自有适配模块")
        generation_targets: list[str] = []
        existing_hashes: dict[str, str] = {}
        for child in children:
            relative = child["source"]
            source = root / relative
            if source.is_symlink() or (source.exists() and (
                not source.is_file() or not source.stat().st_size
            )):
                blockers.append(f"已有生成子模块不是普通非空文件：{relative}")
            elif source.is_file():
                existing_hashes[relative] = (
                    "sha256:" + hashlib.sha256(source.read_bytes()).hexdigest()
                )
            else:
                generation_targets.append(relative)
        service = DesignDeliveryService(root)
        try:
            service.assembly.verify_acceptance_contract(state)
        except AssemblyError as exc:
            blockers.append("独立 SoC 验收尚未冻结：" + str(exc))
        try:
            lock = service.library.read_lock(optional=True)
            if not lock:
                raise AssemblyError("尚未锁定 IP")
            service.assembly.verify_current(state, lock)
            assembly_pending = False
        except (AssemblyError, IPLibraryError, OSError):
            assembly_pending = True
        actions = ["rtl_generation"] * len(generation_targets)
        if assembly_pending:
            actions.append("assembly_preparation")
        if not actions:
            blockers.append("生成子模块与 IP 装配已就绪；请预览正式产品方案")
        for target in generation_targets:
            if violations([target], self.project.config().write_paths):
                blockers.append(f"工程 AI 写权限不包含 {target}")
        if not self.project.is_git_repository():
            blockers.append("工程尚未建立 Git 基线")
        plan = {
            "schema_version": 1,
            "design_kind": "single_clock_soc",
            "spec_digest": str(state.get("spec_digest", "")),
            "acceptance_sources_digest": str(state.get("acceptance_sources_digest", "")),
            "rtl": generation_targets[0] if generation_targets else "integration/nebula_assembly.sv",
            "checker": "",
            "generation_targets": generation_targets,
            "assembly_pending": assembly_pending,
            "existing_child_hashes": existing_hashes,
            "rtl_sha256": "", "checker_sha256": "",
            "actions": actions,
            "max_repairs": self.MAX_REPAIRS,
            "ready": not blockers,
            "blockers": blockers,
            "review_gate": "独立 SoC checker 已按规格版本冻结；准备完成后运行产品验证",
        }
        plan["plan_digest"] = "sha256:" + hashlib.sha256(
            json.dumps(plan, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            .encode("utf-8")
        ).hexdigest()
        return plan

    def preview(self) -> dict[str, Any]:
        state = SpecificationWorkspace(self.project.root).state()
        if state.get("document", {}).get("design_kind") == "single_clock_soc":
            return self._preview_soc_adapter(state)
        blockers: list[str] = []
        document = state.get("document", {})
        assembled = bool(document.get("instances"))
        if not state.get("valid") or not state.get("frozen"):
            blockers.append("需要先确认并冻结有效的通用 CSIR")
        if document.get("design_kind") != "generic_module":
            blockers.append("该准备流程仅适用于通用模块")
        root = self.project.root
        generation_targets: list[str] = []
        existing_hashes: dict[str, str] = {}
        assembly_pending = False
        contract: dict[str, Any] = {}
        if assembled:
            try:
                children = generated_submodules(state)
            except (GeneratedSubmoduleError, KeyError, TypeError) as exc:
                blockers.append(str(exc))
                children = []
            for child in children:
                relative = child["source"]
                source = root / relative
                if source.is_symlink() or (source.exists() and (
                    not source.is_file() or not source.stat().st_size
                )):
                    blockers.append(f"已有生成子模块不是普通非空文件：{relative}")
                elif source.is_file():
                    existing_hashes[relative] = (
                        "sha256:" + hashlib.sha256(source.read_bytes()).hexdigest()
                    )
                else:
                    generation_targets.append(relative)
            try:
                contract = checker_contract(state, root)
            except (GenericAcceptanceError, GenericRTLContractError, KeyError, TypeError) as exc:
                if str(exc).startswith("IP 装配尚未固定"):
                    assembly_pending = True
                else:
                    blockers.append(str(exc))
            rtl = generation_targets[0] if generation_targets else "integration/nebula_assembly.sv"
            checker = f"tb/{document.get('name', '')}_tb.sv"
        else:
            try:
                contract = checker_contract(state, root)
            except (GenericAcceptanceError, GenericRTLContractError, KeyError, TypeError) as exc:
                blockers.append(str(exc))
            rtl = str(contract.get("rtl", ""))
            checker = str(contract.get("testbench", ""))
        rtl_path = root / rtl if rtl else root
        checker_path = root / checker if checker else root
        if not assembled and rtl and rtl_path.is_symlink():
            blockers.append(f"RTL 是符号链接，不能由 Agent 写入：{rtl}")
        if checker and checker_path.is_symlink():
            blockers.append(f"checker 是符号链接，不能由 Agent 写入：{checker}")
        rtl_present = bool(rtl and (rtl_path.exists() or rtl_path.is_symlink()))
        if not assembled and not rtl_present and not document.get("rtl_source"):
            # A missing canonical path must not trigger a second top module when
            # an imported fileset already defines this module elsewhere.
            for item in self.project.source_model().get("modules", []):
                if item.get("name") == document.get("name") and item.get("file") != rtl:
                    blockers.append(
                        f"已导入顶层 {document.get('name')} 位于 {item['file']}；"
                        "请在需求规格中绑定该 RTL 源文件，保存新修订并重新冻结"
                    )
                    break
        compile_source_hashes: dict[str, str] = {}
        header_hashes: dict[str, str] = {}
        if not assembled and rtl and contract:
            if contract.get("include_dirs"):
                try:
                    header_hashes = {
                        relative: "sha256:" + hashlib.sha256((root / relative).read_bytes()).hexdigest()
                        for relative in generation_include_files(root, state)
                    }
                except GenericRTLContractError as exc:
                    blockers.append(str(exc))
            declared = set(contract.get("sources") or [rtl])
            for relative in contract.get("sources", []):
                path = root / relative
                if (
                    path.resolve() != path or path.is_symlink()
                    or not path.is_file() or not path.stat().st_size
                ):
                    blockers.append(f"RTL 编译依赖缺失或无效：{relative}")
                else:
                    compile_source_hashes[relative] = (
                        "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
                    )
            modules = {item["name"]: item for item in self.project.source_model().get("modules", [])}
            top = modules.get(str(document.get("name", "")))
            if top and top["file"] == rtl:
                pending = [top["name"]]
                seen: set[str] = set()
                required: set[str] = set()
                while pending:
                    module_name = pending.pop()
                    if module_name in seen or module_name not in modules:
                        continue
                    seen.add(module_name)
                    module = modules[module_name]
                    required.add(module["file"])
                    pending.extend(child["module"] for child in module["instances"])
                missing = sorted(required - declared)
                if missing:
                    blockers.append(
                        "顶层还依赖已登记设计文件：" + "、".join(missing)
                        + "；请在需求规格中绑定完整 RTL 编译清单并重新冻结"
                    )
        checker_present = bool(
            checker and (checker_path.exists() or checker_path.is_symlink())
        )
        rtl_exists = bool(rtl_present and rtl_path.is_file() and rtl_path.stat().st_size)
        checker_exists = bool(
            checker_present and checker_path.is_file() and checker_path.stat().st_size
        )
        if not assembled and rtl_present and not rtl_exists:
            blockers.append(f"已有 RTL 不是可用的普通非空文件：{rtl}")
        if checker_present and not checker_exists:
            blockers.append(f"已有 checker 不是可用的普通非空文件：{checker}")
        revisable = (
            GenericAcceptanceWorkspace(root).revisable_prior(state)
            if not assembled and rtl_exists and checker_exists else {}
        )
        if assembled:
            actions = ["rtl_generation"] * len(generation_targets)
            if assembly_pending:
                actions.append("assembly_preparation")
            if checker and not checker_present:
                actions.append("acceptance_generation")
            if (generation_targets or assembly_pending) and checker_exists:
                blockers.append(
                    "已有 checker 需要单独核对；自动准备不会在重新装配后覆盖现有验收文件"
                )
        else:
            actions = (["rtl_repair", "acceptance_generation"] if revisable else
                       (["rtl_generation"] if rtl and not rtl_present else []) +
                       (["acceptance_generation"] if checker and not checker_present else []))
            if rtl and not rtl_exists and checker_exists:
                blockers.append(
                    "已有 checker 需要单独核对；自动准备不会在生成 RTL 后覆盖现有验收文件"
                )
        if not actions:
            blockers.append("RTL 与 checker 均已存在；请审核冻结验收或预览正式产品方案")
        for target in generation_targets if assembled else ([rtl] if any(
            action in actions for action in ("rtl_generation", "rtl_repair")
        ) else []):
            if violations([target], self.project.config().write_paths):
                blockers.append(f"工程 AI 写权限不包含 {target}")
        if not self.project.is_git_repository():
            blockers.append("工程尚未建立 Git 基线")
        acceptance = (
            GenericAcceptanceWorkspace(root).state(state)
            if contract and state.get("frozen") and state.get("valid") else {}
        )
        if acceptance.get("frozen"):
            blockers.append("独立验收已冻结；请直接预览正式产品方案")
        if not acceptance.get("frozen") and not revisable and checker_exists:
            blockers.append("现有 checker 缺少可核对的旧版冻结记录；请先人工核对，自动流程不会覆盖")
        plan = {
            "schema_version": 1,
            "design_kind": "generic_module",
            "spec_digest": str(state.get("spec_digest", "")),
            "rtl": rtl,
            "checker": checker,
            "generation_targets": generation_targets,
            "assembly_pending": assembly_pending,
            "existing_child_hashes": existing_hashes,
            "rtl_source_hashes": compile_source_hashes,
            "rtl_header_hashes": header_hashes,
            "rtl_sha256": (
                "sha256:" + hashlib.sha256(rtl_path.read_bytes()).hexdigest()
                if rtl_exists else ""
            ),
            "checker_sha256": (
                "sha256:" + hashlib.sha256(checker_path.read_bytes()).hexdigest()
                if checker_exists else ""
            ),
            "actions": actions,
            "revision_of": revisable.get("spec_digest", ""),
            "max_repairs": self.MAX_REPAIRS,
            "ready": not blockers,
            "blockers": blockers,
            "review_gate": "独立 checker 自检后必须由用户审阅并冻结",
        }
        plan["plan_digest"] = "sha256:" + hashlib.sha256(
            json.dumps(plan, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            .encode("utf-8")
        ).hexdigest()
        return plan

    def start(self, plan_digest: str, *, framework: str = "codex") -> dict[str, Any]:
        if framework not in {"codex", "opencode", "claude-code", "qodercli"}:
            raise GenericBootstrapError("准备流程必须使用已安装认证的真实 Agent")
        plan = self.preview()
        if plan["plan_digest"] != plan_digest:
            raise GenericBootstrapError("规格或工程输入已变化；请重新预览准备方案")
        if not plan["ready"]:
            raise GenericBootstrapError("准备方案受阻：" + "；".join(plan["blockers"]))
        if self.other_active():
            raise GenericBootstrapError("当前工程已有产品流程在运行")
        with self._mutex:
            if self._active_id:
                raise GenericBootstrapError("当前工程已有通用设计准备流程")
            handle = self.lock_path.open("a+b")
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                handle.close()
                raise GenericBootstrapError("另一个后端正在准备当前工程") from exc
            identifier = "bootstrap-" + uuid.uuid4().hex[:12]
            record = {
                "schema_version": 1,
                "id": identifier,
                "status": "starting",
                "plan": plan,
                "plan_digest": plan_digest,
                "framework": framework,
                "created_at": self._now(),
                "started_at": self._now(),
                "finished_at": "",
                "wall_seconds": None,
                "current_stage": "",
                "operation_ids": [],
                "execution_plan_ids": [],
                "repair_count": 0,
                "max_repairs": self.MAX_REPAIRS,
                "reason": "",
            }
            self._write(record)
            self._lock_handle = handle
            self._active_id = identifier
            self._stop_event.clear()
            self._thread = threading.Thread(
                target=self._execute, args=(identifier,), daemon=True,
                name=f"generic-{identifier}",
            )
            self._thread.start()
            return record

    def _update(self, identifier: str, **fields: Any) -> dict[str, Any]:
        with self._mutex:
            record = self.get(identifier)
            record.update(fields)
            if record.get("finished_at") and record.get("started_at"):
                record["wall_seconds"] = round(
                    (
                        dt.datetime.fromisoformat(record["finished_at"])
                        - dt.datetime.fromisoformat(record["started_at"])
                    ).total_seconds(), 3,
                )
            self._write(record)
            return record

    def _wait_operation(self, identifier: str, timeout: int) -> dict[str, Any]:
        deadline = time.monotonic() + timeout
        while True:
            operation = self.project.operation(identifier)
            if operation.get("status") not in {"starting", "running", "pause_requested", "paused"}:
                worker = self.runs._threads.get(identifier)
                if worker is not None:
                    worker.join(timeout=30)
                    if worker.is_alive():
                        raise GenericBootstrapError("Agent 操作未完成资源清理")
                return operation
            if self._stop_event.is_set() or time.monotonic() >= deadline:
                self.runs.stop_agent(identifier)
                worker = self.runs._threads.get(identifier)
                if worker is not None:
                    worker.join(timeout=120)
                if self._stop_event.is_set():
                    raise GenericBootstrapError("用户停止了通用设计准备流程")
                raise GenericBootstrapError(f"Agent 操作 {identifier} 超过预算")
            self._stop_event.wait(0.25)

    def _execute(self, identifier: str) -> None:
        try:
            record = self.get(identifier)
            if self.preview()["plan_digest"] != record["plan_digest"]:
                raise GenericBootstrapError("准备启动前输入已变化")
            self._update(identifier, status="running")
            budget = self.MAX_REPAIRS
            generation_index = 0
            for stage in record["plan"]["actions"]:
                if self._stop_event.is_set():
                    raise GenericBootstrapError("用户停止了通用设计准备流程")
                current = self.preview()
                if current["spec_digest"] != record["plan"]["spec_digest"]:
                    raise GenericBootstrapError("准备期间冻结规格发生变化")
                if stage in {"rtl_generation", "rtl_repair"}:
                    targets = record["plan"].get("generation_targets", [])
                    if targets:
                        target = targets[generation_index]
                        generation_index += 1
                    else:
                        target = record["plan"]["rtl"]
                    source = self.project.root / target
                    if stage == "rtl_generation" and source.exists():
                        raise GenericBootstrapError(f"待生成 RTL 已由其他操作创建：{target}")
                    if stage == "rtl_repair" and (
                        source.is_symlink() or not source.is_file()
                        or "sha256:" + hashlib.sha256(source.read_bytes()).hexdigest()
                        != record["plan"]["rtl_sha256"]
                    ):
                        raise GenericBootstrapError(f"待修订 RTL 已被其他操作修改：{target}")
                    if generation_index <= 1 and current["plan_digest"] != record["plan_digest"]:
                        raise GenericBootstrapError("RTL 生成前工程输入已变化")
                elif stage == "assembly_preparation":
                    if self.other_active():
                        raise GenericBootstrapError("IP 装配前发现其他产品流程在运行")
                    self._update(identifier, current_stage=stage)
                    from chip_nebula.dashboard.design_delivery import DesignDeliveryService
                    service = DesignDeliveryService(self.project.root)
                    preparation = service.preview_preparation()
                    if not preparation["ready"]:
                        raise GenericBootstrapError(
                            "IP 装配输入仍不完整：" + "；".join(preparation["blockers"])
                        )
                    assembled = service.prepare_assembly(preparation["plan_digest"])
                    self._update(identifier, assembly_plan_digest=preparation["plan_digest"],
                                 assembly_digest=assembled["assembly"]["assembly"]["assembly_digest"])
                    if self._stop_event.is_set():
                        raise GenericBootstrapError("用户停止了通用设计准备流程")
                    continue
                else:
                    target = record["plan"]["checker"]
                    checker_source = self.project.root / target
                    if record["plan"].get("revision_of"):
                        if (
                            checker_source.is_symlink() or not checker_source.is_file()
                            or "sha256:" + hashlib.sha256(checker_source.read_bytes()).hexdigest()
                            != record["plan"]["checker_sha256"]
                        ):
                            raise GenericBootstrapError("旧版 checker 已被其他操作修改；请先审核")
                    elif checker_source.exists():
                        raise GenericBootstrapError("checker 已由其他操作创建；请先审核现有文件")
                    if record["plan"].get("assembly_pending"):
                        try:
                            checker_contract(
                                SpecificationWorkspace(self.project.root).state(),
                                self.project.root,
                            )
                        except (GenericAcceptanceError, GenericRTLContractError) as exc:
                            raise GenericBootstrapError(
                                "生成独立 checker 前装配未固定：" + str(exc)
                            ) from exc
                self._update(identifier, current_stage=stage)
                plan = self.runs.create_execution_plan(
                    f"按冻结规格准备 {target}；保持需求 ID 和独立验收边界。",
                    record["framework"],
                    workspace=(
                        "rtl-analysis" if stage in {"rtl_generation", "rtl_repair"}
                        else "simulation"
                    ),
                    write_paths=[target],
                )
                if (
                    plan.get("stage") != stage
                    or plan.get("write_paths") != [target]
                    or plan.get("blockers")
                ):
                    raise GenericBootstrapError(
                        "阶段执行方案未获得精确权限：" + "；".join(plan.get("blockers", []))
                    )
                plan["budgets"]["max_repairs"] = budget
                self.runs._write_execution_plan(plan)
                started = self.runs.start_execution_plan(plan["id"])
                operation = started["operation"]
                self._active_operation_id = operation["id"]
                current_record = self.get(identifier)
                current_record["execution_plan_ids"].append(plan["id"])
                current_record["operation_ids"].append(operation["id"])
                self._write(current_record)
                completed = self._wait_operation(
                    operation["id"],
                    max(120, self.project.config().agent_timeout * (budget + 1) + 300),
                )
                self._active_operation_id = ""
                # The Task Graph link records every claimed attempt, including
                # launches that failed before a checker report was produced.
                used = max(
                    0,
                    len(completed.get("taskgraph", {}).get("attempt_run_ids", [])) - 1,
                )
                budget = max(0, budget - used)
                self._update(identifier, repair_count=self.MAX_REPAIRS - budget)
                expected = (
                    "repaired_unverified" if stage == "rtl_repair" else
                    "generated_unverified" if stage == "rtl_generation"
                    else "candidate_review_required"
                )
                if (
                    completed.get("status") != "succeeded"
                    or completed.get("engineering_verdict") != expected
                ):
                    raise GenericBootstrapError(
                        f"{stage} 未完成真实工具门禁："
                        + str(completed.get("summary", completed.get("status", "")))[-500:]
                    )
                if self._stop_event.is_set():
                    raise GenericBootstrapError("用户停止了通用设计准备流程")
            soc_adapter = record["plan"].get("design_kind") == "single_clock_soc"
            self._update(
                identifier,
                status="prepared" if soc_adapter else "review_required",
                current_stage="product_preview" if soc_adapter else "acceptance_review",
                reason=(
                    "生成适配器与 IP 装配已锁定；请预览并启动固定快照系统验收"
                    if soc_adapter else
                    "RTL 展开与 checker 敏感度自检已完成；请审阅并冻结独立验收，再启动产品验证"
                ),
                finished_at=self._now(),
            )
        except Exception as exc:
            status = "stopped" if self._stop_event.is_set() else "failed"
            self._update(
                identifier, status=status, reason=str(exc),
                finished_at=self._now(),
            )
        finally:
            self._active_operation_id = ""
            with self._mutex:
                handle = self._lock_handle
                self._lock_handle = None
                self._active_id = ""
                if handle is not None:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
                    handle.close()

    def stop(self, identifier: str) -> dict[str, Any]:
        with self._mutex:
            if identifier != self._active_id:
                raise GenericBootstrapError("该准备流程当前未运行")
            self._stop_event.set()
            operation_id = self._active_operation_id
            self._update(identifier, status="stop_requested")
        if operation_id:
            self.runs.stop_agent(operation_id)
        return self.get(identifier)

    def stop_active(self) -> None:
        with self._mutex:
            identifier = self._active_id
        if identifier:
            self.stop(identifier)
            worker = self._thread
            if worker is not None and worker is not threading.current_thread():
                worker.join(timeout=120)
