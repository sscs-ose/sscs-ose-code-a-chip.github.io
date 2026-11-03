"""Read-only, deterministic preparation plan for a frozen product design."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from chip_nebula.taskgraph.assembly import AssemblyError, AssemblyService, _validate_port_bindings, supports_soc_package
from chip_nebula.taskgraph.generic_acceptance import GenericAcceptanceError, GenericAcceptanceWorkspace
from chip_nebula.taskgraph.generic_rtl import GenericRTLContractError
from chip_nebula.taskgraph.ip_library import (
    IPLibrary, IPLibraryError, IPPackage, _resolve_instance_parameters,
    supports_capability, supports_generic_named_port,
)
from chip_nebula.taskgraph.memory_generator import MemoryGenerator, MemoryGenerationError
from chip_nebula.taskgraph.generated_submodule import (
    GeneratedSubmoduleError, generated_submodules, source_record, submodule_contract,
)


class ProductPreparationPlanner:
    def __init__(self, library: IPLibrary, *, project_root: Path | None = None) -> None:
        self.library = library
        self.project_root = (project_root or library.project_root).resolve()

    def preview(
        self, spec: Mapping[str, Any], *, current_lock: Mapping[str, Any] | None = None,
        acceptance_blocker: str = "",
        validation_config: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        document = spec.get("document", {})
        blockers: list[str] = []
        if not isinstance(document, Mapping):
            document = {}
            blockers.append("规格文档不是结构化 CSIR")
        if not spec.get("valid") or not spec.get("frozen"):
            blockers.append("必须先编译并由人冻结规格与独立验收")
        if acceptance_blocker:
            blockers.append(acceptance_blocker)
        current = current_lock if current_lock is not None else self.library.read_lock(optional=True) or {}
        decisions: list[dict[str, Any]] = []
        qualifications: dict[str, dict[str, Any]] = {}
        generated: list[str] = []
        generated_rtl: list[str] = []
        selected_versions: dict[str, str] = {}
        selected_modules: dict[str, str] = {}
        generic_bindings: list[dict[str, Any]] = []
        instances = document.get("instances", [])
        if not isinstance(instances, list) or not instances:
            blockers.append("规格没有可装配的 IP 或模块实例")
            instances = []
        for instance in instances:
            if not isinstance(instance, Mapping):
                blockers.append("规格存在无效模块实例")
                continue
            name = str(instance.get("name", ""))
            capability = str(instance.get("capability", ""))
            if capability == "generated-rtl":
                try:
                    contract = submodule_contract(spec, name)
                    record = source_record(self.project_root, spec, name)
                except GeneratedSubmoduleError as exc:
                    blockers.append(f"{name}：{exc}")
                    decisions.append({
                        "instance": name, "capability": capability,
                        "action": "generate", "reason": str(exc),
                    })
                    continue
                generated_rtl.append(name)
                decisions.append({
                    "instance": name, "capability": capability,
                    "action": "generated_rtl",
                    "source": record["source"],
                    "source_digest": record["source_digest"],
                    "generation_digest": record["generation_digest"],
                    "reason": "冻结规格约束的工程自有 RTL；尚须独立系统验收",
                })
                generic_bindings.append({
                    "instance": name, "ports": contract["ports"],
                    "parameters": {},
                    "port_bindings": dict(instance.get("port_bindings", {})),
                })
                continue
            # Lock resolution generates memory whenever no package was named.
            if capability in {"program-rom", "register-ram"} and not instance.get("package"):
                if not any(
                    item.get("instance") == name
                    for item in document.get("memories", [])
                    if isinstance(item, Mapping)
                ):
                    blockers.append(f"{name}：冻结规格缺少存储器契约")
                    continue
                generated.append(name)
                decisions.append({
                    "instance": name, "capability": capability,
                    "action": "generate", "reason": "冻结规格包含受支持的存储器契约",
                })
                continue
            candidates = self.library.qualification_candidates(instance, document, current)
            if not candidates:
                matching = [
                    package for package in self.library.packages()
                    if (not instance.get("package") or package.package_id == instance["package"])
                    and (not instance.get("version") or package.version == instance["version"])
                    and (not capability or supports_capability(capability, package.manifest))
                ]
                hard_only = bool(matching) and all(
                    package.manifest.get("implementation", {}).get("kind") == "hard_macro"
                    for package in matching
                )
                blockers.append(
                    f"{name}：硬 IP 物理宏集成尚未接入，不能自动复用"
                    if hard_only else
                    f"{name}：没有经过审核且与参数、接口兼容的 IP，"
                    "也没有已实现的 RTL 生成器"
                )
                continue
            selected = candidates[0]
            package: IPPackage = selected["package"]
            try:
                dependencies = self.library.dependency_closure(package)
            except IPLibraryError as exc:
                blockers.append(f"{name}：{exc}")
                continue
            if document.get("design_kind") == "single_clock_soc":
                if not supports_soc_package(capability, str(package.manifest["top_module"])):
                    blockers.append(f"{name}：选中 IP 没有受支持的 SoC 引脚契约")
            elif document.get("design_kind") == "generic_module":
                if not supports_generic_named_port(package.manifest):
                    blockers.append(f"{name}：选中 IP 没有完整具名端口装配契约")
            elif package.manifest.get("generator", {}).get("kind") != "apb-gpio-wrapper-v1":
                blockers.append(f"{name}：选中 IP 没有受支持的确定性装配器")
            if document.get("design_kind") == "generic_module":
                try:
                    locked_parameters, _ = _resolve_instance_parameters(
                        package.manifest, instance.get("parameters", {}), document,
                    )
                    generic_bindings.append({
                        "instance": name,
                        "ports": package.manifest["ports"],
                        "parameters": locked_parameters,
                        "port_bindings": dict(instance.get("port_bindings", {})),
                    })
                except (IPLibraryError, TypeError, ValueError) as exc:
                    blockers.append(f"{name}：参数或具名端口绑定无效：{exc}")
                if str(package.manifest["top_module"]) == str(document.get("name", "")):
                    blockers.append(f"{name}：IP 模块名与设计顶层重复")
            for member in [*dependencies, package]:
                previous = selected_versions.setdefault(member.package_id, member.version)
                if previous != member.version:
                    blockers.append(f"{name}：同一 IP 需要两个代码版本：{member.package_id}")
                top = str(member.manifest["top_module"])
                previous_module = selected_modules.setdefault(top, member.key)
                if previous_module != member.key:
                    blockers.append(f"{name}：重复模块名 {top}")
            decisions.append({
                "instance": name, "capability": capability,
                "action": "reuse", "package_id": package.package_id,
                "version": package.version, "content_digest": package.content_digest,
                "source_kind": package.manifest["source"]["kind"],
                "required_configurations": selected["configurations"],
                "missing_configurations": selected["missing_configurations"],
                "dependencies": [item.key for item in dependencies],
                "alternatives": [item["package"].key for item in candidates[1:]],
            })
            self._add_qualifications(
                qualifications, blockers, package,
                selected["missing_configurations"], name,
            )
            for owner in [*dependencies, package]:
                for declaration in owner.manifest.get("dependencies", []):
                    dependency = self.library.find(
                        str(declaration.get("package_id", "")),
                        str(declaration.get("version", "")),
                    )
                    if dependency is None:
                        blockers.append(f"{name}：缺少精确依赖 {declaration}")
                        continue
                    _parameters, configurations = _resolve_instance_parameters(
                        dependency.manifest, declaration.get("parameters", {}), owner.manifest,
                    )
                    evidence = self.library.evidence(dependency)
                    missing = [
                        configuration for configuration in configurations
                        if not any(
                            record.get("verdict") == "passed"
                            and record.get("parameters") == configuration
                            for record in evidence
                        )
                    ]
                    self._add_qualifications(
                        qualifications, blockers, dependency, missing,
                        f"{name} 的依赖",
                    )
        if document.get("design_kind") == "generic_module" and generic_bindings:
            try:
                _validate_port_bindings(document, generic_bindings, generic=True)
            except AssemblyError as exc:
                blockers.append(f"通用 IP 端口预检失败：{exc}")
        if generated and not blockers:
            try:
                MemoryGenerator(self.project_root).render(spec)
            except MemoryGenerationError as exc:
                blockers.append(f"存储器生成预检失败：{exc}")
        product_blockers: list[str] = []
        acceptance_digest = ""
        rtl_digest = ""
        assembly_digest = ""
        lock_digest = ""
        if document.get("design_kind") == "generic_module":
            try:
                project_library = IPLibrary(self.project_root)
                current_lock = project_library.read_lock()
                current_assembly = AssemblyService(
                    self.project_root, project_library,
                ).verify_current(spec, current_lock)
                assembly_digest = str(current_assembly["assembly_digest"])
                lock_digest = str(current_lock["lock_digest"])
            except (AssemblyError, IPLibraryError) as exc:
                product_blockers.append("IP 装配尚未固定或输入已变化：" + str(exc))
            if not product_blockers:
                try:
                    acceptance = GenericAcceptanceWorkspace(self.project_root).state(spec)
                    if acceptance.get("valid"):
                        acceptance_digest = str(acceptance["contract_digest"])
                        rtl_digest = str(acceptance["contract"].get("source_hashes", {}).get(
                            "integration/nebula_assembly.sv", "",
                        ))
                    else:
                        product_blockers.append(
                            "独立 checker 尚未审核冻结或已过期：" + acceptance.get("reason", "")
                        )
                except (GenericAcceptanceError, GenericRTLContractError) as exc:
                    product_blockers.append(str(exc))
        target = document.get("technical_target")
        clocks = document.get("clocks", [])
        generic_physical_ready = bool(
            acceptance_digest and assembly_digest
            and isinstance(target, dict)
            and target.get("platform") == "sky130hd"
            and target.get("pvt") == "tt"
            and type(target.get("clock_period_ns")) in {int, float}
            and 0.01 <= float(target["clock_period_ns"]) <= 1_000_000
            and isinstance(clocks, list) and len(clocks) == 1
        )
        if document.get("design_kind") == "generic_module" and not generic_physical_ready:
            product_blockers.append("GDS 需要冻结的单时钟 Sky130HD TT 技术目标与独立验收")
        physical_blockers: list[str] = []
        peripheral_ready = True
        peripheral_validation: dict[str, str] = {}
        if document.get("design_kind", "register_peripheral") == "register_peripheral":
            peripheral_validation = {
                key: str((validation_config or {}).get(key, ""))
                for key in ("lint_command", "simulation_command", "workdir", "success_pattern")
            }
            sources = document.get("acceptance_sources", [])
            if not spec.get("acceptance_sources_digest") or not isinstance(sources, list) or not sources:
                product_blockers.append("外设缺少随规格冻结的独立验收文件；请加入 checker 与运行脚本后重新冻结")
            if not validation_config or not str(validation_config.get("simulation_command", "")).strip():
                product_blockers.append("外设未配置独立仿真命令；请在工程 Settings 配置验证入口")
            peripheral_ready = not product_blockers
            target = document.get("technical_target")
            if not (
                isinstance(target, Mapping)
                and target.get("platform") == "sky130hd"
                and target.get("pvt") == "tt"
                and type(target.get("clock_period_ns")) in {int, float}
                and 0 < float(target["clock_period_ns"]) < float("inf")
            ):
                physical_blockers.append("GDS 需要冻结的 Sky130HD TT 时钟周期目标；功能验收可先运行")
        plan = {
            "schema_version": 1,
            "design_kind": str(document.get("design_kind", "register_peripheral")),
            "spec_digest": str(spec.get("spec_digest", "")),
            "acceptance_sources_digest": str(spec.get("acceptance_sources_digest", "")),
            "ready": not blockers,
            "blockers": blockers,
            "product_ready": not blockers and (
                bool(acceptance_digest and assembly_digest)
                if document.get("design_kind") == "generic_module"
                else peripheral_ready
            ),
            "physical_ready": (
                generic_physical_ready
                if document.get("design_kind") == "generic_module"
                else not physical_blockers
            ),
            "product_blockers": product_blockers,
            "physical_blockers": physical_blockers,
            "validation_commands": peripheral_validation,
            "acceptance_contract_digest": acceptance_digest,
            "rtl_sha256": rtl_digest,
            "assembly_digest": assembly_digest,
            "lock_digest": lock_digest,
            "decisions": decisions,
            "qualifications": list(qualifications.values()),
            "generated_instances": generated,
            "generated_rtl_instances": generated_rtl,
            "final_steps": ["resolve-ip-lock", "assemble-and-elaborate"],
        }
        plan["plan_digest"] = "sha256:" + hashlib.sha256(
            json.dumps(plan, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        return plan

    @staticmethod
    def _add_qualifications(
        qualifications: dict[str, dict[str, Any]], blockers: list[str],
        package: IPPackage, missing: list[dict[str, Any]], owner: str,
    ) -> None:
        if not missing:
            return
        verification = package.manifest.get("verification", {})
        if not verification.get("commands"):
            blockers.append(f"{owner}：选中 IP 没有真实资格验证入口")
            return
        entry = qualifications.setdefault(package.key, {
            "package_id": package.package_id,
            "version": package.version,
            "content_digest": package.content_digest,
            "source_kind": package.manifest["source"]["kind"],
            "configurations": [],
            "commands": verification["commands"],
            "timeout_seconds_per_command": verification.get("timeout", 120),
        })
        seen = {json.dumps(item, sort_keys=True) for item in entry["configurations"]}
        for configuration in missing:
            key = json.dumps(configuration, sort_keys=True)
            if key not in seen:
                entry["configurations"].append(configuration)
                seen.add(key)


class ProductFlowError(ValueError):
    """A reviewed product flow cannot start or continue."""


class ProductFlowBlocked(ProductFlowError):
    """A missing tool or unsupported environment prevents the next stage."""


class ProductFlowTimeout(ProductFlowError):
    """A child run exceeded the reviewed wall-clock budget."""


class ProductFlowStopped(ProductFlowError):
    """The user requested a stop before the next stage."""


class ProductFlowRunner:
    """Durable product-stage state machine around existing Task Graph runs.

    Qualification, generation, lock, assembly, validation and physical runs
    keep their own immutable Task/Run evidence. This record binds their IDs
    into one user-visible product attempt and never upgrades an unrun gate.
    """

    STAGES = ("preparation", "validation", "physical_setup", "physical", "delivery")
    ACTIVE = {"starting", "running", "stop_requested"}
    AUTO_REPAIR_LIMIT = 3

    def __init__(self, project: Any, design: Any, runs: Any) -> None:
        import threading

        self.project = project
        self.design = design
        self.runs = runs
        self.root = project.root / ".chip_nebula" / "product-flows"
        self.root.mkdir(parents=True, exist_ok=True)
        self.lock_path = self.root / "active.lock"
        self._mutex = threading.RLock()
        self._stop_event = threading.Event()
        self._thread: Any = None
        self._lock_handle: Any = None
        self._active_id = ""
        self._recover_interrupted()

    def _recover_interrupted(self) -> None:
        import fcntl

        with self.lock_path.open("a+b") as handle:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return  # Another backend still owns the live product attempt.
            try:
                for path in self.root.glob("flow-*.json"):
                    try:
                        record = json.loads(path.read_text(encoding="utf-8"))
                    except (OSError, json.JSONDecodeError):
                        continue
                    if record.get("status") not in self.ACTIVE:
                        continue
                    record["status"] = "interrupted"
                    record["verdict"] = "interrupted"
                    record["reason"] = "后端在产品流程执行期间退出；文件和子运行记录已保留，不自动重放"
                    record["finished_at"] = self._now()
                    for stage in record.get("stages", []):
                        if stage.get("status") == "running":
                            stage["status"] = "interrupted"
                            stage["finished_at"] = record["finished_at"]
                    self._write(record)
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    @staticmethod
    def _now() -> str:
        import datetime as dt
        return dt.datetime.now(dt.timezone.utc).isoformat()

    @staticmethod
    def _wall_seconds(record: Mapping[str, Any]) -> float | None:
        import datetime as dt
        try:
            start = dt.datetime.fromisoformat(str(record["started_at"]))
            finish = dt.datetime.fromisoformat(str(record["finished_at"]))
        except (KeyError, TypeError, ValueError):
            return None
        return round(max(0.0, (finish - start).total_seconds()), 3)

    def _write(self, record: Mapping[str, Any]) -> None:
        import os
        import uuid

        destination = self.root / f"{record['id']}.json"
        temporary = self.root / f".{record['id']}.{uuid.uuid4().hex}.tmp"
        with temporary.open("w", encoding="utf-8") as handle:
            json.dump(record, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)

    def get(self, flow_id: str) -> dict[str, Any]:
        import re
        if not re.fullmatch(r"flow-[0-9a-f]{12}", flow_id):
            raise ProductFlowError("无效的产品流程 ID")
        path = self.root / f"{flow_id}.json"
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ProductFlowError("找不到产品流程记录") from exc

    def inspect(self, flow_id: str) -> dict[str, Any]:
        """Overlay current-input validity without rewriting historical verdicts."""
        record = self.get(flow_id)
        if record["status"] in self.ACTIVE:
            record["current"] = True
            record["display_verdict"] = record["verdict"]
            return record
        try:
            state = self.design.specs.state()
        except Exception:
            state = {}
        current = (
            state.get("frozen") and state.get("valid")
            and state.get("spec_digest") == record.get("spec_digest")
            and state.get("acceptance_sources_digest") == record.get("acceptance_sources_digest")
        )
        if record.get("design_kind") == "generic_module":
            try:
                current_plan = self.design.preview_preparation()
                current = bool(
                    current and current_plan.get("ready")
                    and current_plan.get("plan_digest") == record.get("plan_digest")
                )
            except Exception:
                current = False
        for stage in record.get("stages", []):
            child_id = stage.get("child_run_id")
            if child_id and stage.get("status") == "passed":
                try:
                    child = self.runs.get_run(child_id)
                except Exception:
                    current = False
                else:
                    if child.get("verdict") != "passed":
                        current = False
        record["current"] = bool(current)
        record["display_verdict"] = (
            record["verdict"] if current or record["verdict"] not in {
                "ready", "functional_passed_physical_not_run",
            } else "stale"
        )
        return record

    def list(self) -> list[dict[str, Any]]:
        result = []
        for path in self.root.glob("flow-*.json"):
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            result.append(self.inspect(record["id"]))
        return sorted(result, key=lambda item: item.get("created_at", ""), reverse=True)

    def start(
        self, plan_digest: str, *, run_physical: bool = True,
        physical_timeout_seconds: int = 14400,
        auto_repair_framework: str = "",
    ) -> dict[str, Any]:
        import fcntl
        import threading
        import uuid

        if not 60 <= physical_timeout_seconds <= 86400:
            raise ProductFlowError("物理流程超时必须在 60 秒到 24 小时之间")
        plan = self.design.preview_preparation()
        if not plan_digest or plan["plan_digest"] != plan_digest:
            raise ProductFlowError("产品方案已变化；请重新预览规格、IP 与命令")
        if not plan["ready"]:
            raise ProductFlowError("产品方案受阻：" + "；".join(plan["blockers"]))
        if plan.get("product_ready") is False:
            raise ProductFlowBlocked("产品验收输入未就绪：" + "；".join(plan.get("product_blockers", [])))
        if run_physical and plan.get("physical_ready") is False:
            raise ProductFlowBlocked("物理技术目标未就绪：" + "；".join(plan.get("physical_blockers", [])))
        state = self.design.specs.state()
        document = state.get("document", {})
        kind = document.get("design_kind", "register_peripheral")
        if kind == "generic_module" and document.get("instances"):
            if not plan.get("product_ready"):
                raise ProductFlowBlocked("通用 IP 产品输入尚未就绪：" + "；".join(plan.get("product_blockers", [])))
            if run_physical and not plan.get("physical_ready"):
                raise ProductFlowBlocked("通用 IP 缺少已冻结的物理目标或独立验收")
            if auto_repair_framework:
                raise ProductFlowBlocked("含 IP 的通用装配暂不支持自动改写锁定 wrapper 或库源码")
        if kind not in {"single_clock_soc", "register_peripheral", "generic_module"}:
            raise ProductFlowBlocked("当前自动产品流程不支持此设计类型")
        repair_target = ""
        if auto_repair_framework:
            from chip_nebula.adapters.scope_check import violations

            if auto_repair_framework not in {"codex", "opencode", "claude-code", "qodercli"}:
                raise ProductFlowBlocked("产品级修复必须使用真实 Agent")
            if kind == "single_clock_soc":
                try:
                    generated = generated_submodules(state)
                except GeneratedSubmoduleError as exc:
                    raise ProductFlowBlocked(str(exc)) from exc
                if len(generated) != 1 or not state.get("acceptance_sources_digest"):
                    raise ProductFlowBlocked(
                        "SoC 自动修复仅支持一个精确授权的生成子模块及冻结独立验收"
                    )
                repair_target = generated[0]["source"]
                if violations([repair_target], self.project.config().write_paths):
                    raise ProductFlowBlocked("生成子模块不在工程授权的 RTL 写范围")
            elif kind != "generic_module":
                raise ProductFlowBlocked("当前设计类型尚无受控的产品级 AI 修复路径")
        if any(
            item.get("status") in {"starting", "running"}
            and item.get("kind") in {"validation", "physical", "formal"}
            for item in self.runs.list_runs()
        ):
            raise ProductFlowError("当前工程已有工具运行；请等待或先停止该运行")
        with self._mutex:
            if self._active_id:
                raise ProductFlowError("当前工程已有产品流程在运行")
            handle = self.lock_path.open("a+b")
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                handle.close()
                raise ProductFlowError("另一个桌面进程正在运行本工程的产品流程") from exc
            flow_id = "flow-" + uuid.uuid4().hex[:12]
            record = {
                "schema_version": 1, "id": flow_id,
                "status": "starting", "verdict": "not_run",
                "created_at": self._now(), "started_at": self._now(),
                "finished_at": "", "wall_seconds": None,
                "plan_digest": plan_digest,
                "initial_plan_digest": plan_digest,
                "taskgraph_workflow_id": f"product:{flow_id}",
                "plan": plan,
                "design_kind": kind,
                "spec_digest": plan["spec_digest"],
                "acceptance_sources_digest": plan["acceptance_sources_digest"],
                "run_physical": run_physical,
                "physical_timeout_seconds": physical_timeout_seconds,
                "manual_interventions": ["用户已冻结规格与验收并启动已审查的产品方案"],
                "retry_count": 0, "current_stage": "preparation",
                "auto_repair_framework": auto_repair_framework,
                "max_auto_repairs": self.AUTO_REPAIR_LIMIT if auto_repair_framework else 0,
                "repair_operations": [], "repair_preparations": [],
                "repair_target": repair_target, "active_repair_operation_id": "",
                "validation_run_ids": [],
                "child_run_id": "", "reason": "",
                "stages": [
                    {"id": name, "status": "pending", "verdict": "not_run",
                     "started_at": "", "finished_at": "", "child_run_id": ""}
                    for name in self.STAGES
                ],
            }
            try:
                self._write(record)
                self._lock_handle = handle
                self._active_id = flow_id
                self._stop_event.clear()
                worker = threading.Thread(
                    target=self._execute, args=(flow_id,), daemon=True,
                    name=f"product-{flow_id}",
                )
                self._thread = worker
                worker.start()
            except Exception:
                self._active_id = ""
                self._lock_handle = None
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
                handle.close()
                raise
            return record

    def _update(self, flow_id: str, **fields: Any) -> dict[str, Any]:
        with self._mutex:
            record = self.get(flow_id)
            record.update(fields)
            if record.get("finished_at"):
                record["wall_seconds"] = self._wall_seconds(record)
            self._write(record)
            return record

    def _stage(self, flow_id: str, name: str, status: str, *, verdict: str = "not_run",
               child_run_id: str = "", details: Mapping[str, Any] | None = None) -> None:
        with self._mutex:
            record = self.get(flow_id)
            stage = next(item for item in record["stages"] if item["id"] == name)
            stage["status"] = status
            stage["verdict"] = verdict
            if status == "running":
                stage["started_at"] = self._now()
                record["current_stage"] = name
                if record["status"] != "stop_requested":
                    record["status"] = "running"
            else:
                stage["finished_at"] = self._now()
            if child_run_id:
                stage["child_run_id"] = child_run_id
                record["child_run_id"] = child_run_id
            if details:
                stage["details"] = dict(details)
            self._write(record)

    def _halt_if_requested(self) -> None:
        if self._stop_event.is_set():
            raise ProductFlowStopped("用户停止了产品流程")

    def _wait_child(self, run_id: str, timeout_seconds: int) -> dict[str, Any]:
        import time
        deadline = time.monotonic() + timeout_seconds
        while True:
            current = self.runs.get_run(run_id)
            if current["status"] not in {"starting", "running"}:
                return current
            if self._stop_event.is_set():
                self.runs.stop(run_id)
                worker = self.runs._threads.get(run_id)
                if worker is not None:
                    worker.join(timeout=120)
                raise ProductFlowStopped("用户停止了产品流程")
            if time.monotonic() >= deadline:
                self.runs.stop(run_id)
                worker = self.runs._threads.get(run_id)
                if worker is not None:
                    worker.join(timeout=120)
                raise ProductFlowTimeout(f"子运行 {run_id} 超过 {timeout_seconds} 秒预算")
            self._stop_event.wait(1.0 if run_id.startswith("physical-") else 0.25)

    def _wait_repair_operation(self, operation_id: str, timeout_seconds: int) -> dict[str, Any]:
        import time

        deadline = time.monotonic() + timeout_seconds
        while True:
            operation = self.project.operation(operation_id)
            if operation.get("status") not in {"starting", "running"}:
                worker = self.runs._threads.get(operation_id)
                if worker is not None:
                    worker.join(timeout=30)
                    if worker.is_alive():
                        raise ProductFlowBlocked("AI 修复操作未完成资源清理，暂停后续写入")
                return operation
            if self._stop_event.is_set() or time.monotonic() >= deadline:
                self.runs.stop_agent(operation_id)
                worker = self.runs._threads.get(operation_id)
                if worker is not None:
                    worker.join(timeout=120)
                if self._stop_event.is_set():
                    raise ProductFlowStopped("用户停止了产品级 RTL 修复")
                raise ProductFlowTimeout(
                    f"AI 修复操作 {operation_id} 超过 {timeout_seconds} 秒预算"
                )
            self._stop_event.wait(0.25)

    def _repair_generic_validation(
        self, flow_id: str, record: Mapping[str, Any], checked: dict[str, Any],
    ) -> dict[str, Any]:
        """Bound all Agent revisions to one product attempt and frozen checker."""
        from chip_nebula.taskgraph.generic_acceptance import GenericAcceptanceWorkspace
        from chip_nebula.adapters.scope_check import violations

        framework = str(record.get("auto_repair_framework", ""))
        if not framework or record.get("design_kind") != "generic_module":
            return checked
        for _ in range(self.AUTO_REPAIR_LIMIT):
            failures = [
                item for item in checked.get("checks", [])
                if item.get("verdict") in {"failed", "inconclusive"}
            ]
            if (
                checked.get("status") != "finished"
                or checked.get("verdict") != "failed"
                or checked.get("spec_qualified") is not True
                or not failures
            ):
                break  # No Agent repair for missing tools or unqualified evidence.
            state = self.design.specs.state()
            acceptance = GenericAcceptanceWorkspace(self.project.root).state(state)
            current_plan = self.design.preview_preparation()
            rtl = str(record["plan"]["rtl"])
            if (
                not state.get("frozen") or not state.get("valid")
                or state.get("spec_digest") != record["spec_digest"]
                or not acceptance.get("valid")
                or acceptance.get("contract_digest") != record["plan"]["acceptance_contract_digest"]
                or not current_plan.get("ready") or current_plan.get("rtl") != rtl
                or current_plan.get("technical_target") != record["plan"]["technical_target"]
                or violations([rtl], self.project.config().write_paths)
            ):
                raise ProductFlowBlocked(
                    "AI 修复前规格、独立验收、技术目标或 RTL 写权限已变化"
                )
            self._halt_if_requested()
            failed_ids = [
                f"{item.get('id', '')}={item.get('verdict', '')}"
                for item in failures
            ]
            try:
                log_tail = self.runs.run_log(checked["id"])[-8_000:]
            except Exception:
                log_tail = ""
            instruction = (
                "产品流程固定快照独立验收失败。只修改冻结规格对应的 "
                f"{rtl}，分析检查 {', '.join(failed_ids)} 的直接失败或无法归因结果，再修复 RTL 行为。"
                "不得修改冻结规格、checker、验收用例、IP、工程配置或技术目标。"
                "修复后平台会在新固定快照上重跑同一独立验收。"
                f"\n失败的验证运行：{checked['id']}\n工具日志尾部：\n{log_tail}"
            )
            operation = self.runs.start_agent(
                instruction, framework, [rtl], stage="rtl", max_repairs=0,
            )
            operation_id = operation["id"]
            with self._mutex:
                current = self.get(flow_id)
                current["active_repair_operation_id"] = operation_id
                current["repair_operations"].append(operation_id)
                current["retry_count"] = len(current["repair_operations"])
                self._write(current)
            try:
                completed = self._wait_repair_operation(
                    operation_id, max(120, int(self.project.config().agent_timeout) + 300),
                )
            finally:
                with self._mutex:
                    current = self.get(flow_id)
                    current["active_repair_operation_id"] = ""
                    self._write(current)
            self._halt_if_requested()
            child_ids = completed.get("validation_run_ids", [])
            if not child_ids:
                raise ProductFlowError(
                    f"AI 修复操作 {operation_id} 未产生正式验证："
                    + str(completed.get("summary", ""))[-500:]
                )
            checked = self.runs.get_run(str(child_ids[-1]))
            with self._mutex:
                current = self.get(flow_id)
                current["validation_run_ids"].append(checked["id"])
                current["child_run_id"] = checked["id"]
                self._write(current)
            if (
                completed.get("status") == "succeeded"
                and checked.get("status") == "finished"
                and checked.get("verdict") == "passed"
                and checked.get("spec_qualified") is True
            ):
                final_plan = self.design.preview_preparation()
                if (
                    not final_plan.get("ready") or final_plan.get("rtl") != rtl
                    or final_plan.get("spec_digest") != record["spec_digest"]
                    or final_plan.get("acceptance_contract_digest")
                    != record["plan"]["acceptance_contract_digest"]
                    or final_plan.get("technical_target") != record["plan"]["technical_target"]
                ):
                    raise ProductFlowBlocked("修复后产品输入与冻结依据不一致")
                self._update(
                    flow_id, plan=final_plan, plan_digest=final_plan["plan_digest"],
                )
                break
        return checked

    def _repair_soc_validation(
        self, flow_id: str, record: Mapping[str, Any], checked: dict[str, Any],
    ) -> dict[str, Any]:
        """Repair one generated SoC child without changing frozen acceptance or IPs."""
        framework = str(record.get("auto_repair_framework", ""))
        target = str(record.get("repair_target", ""))
        if not framework or not target:
            return checked

        def reused_packages(plan: Mapping[str, Any]) -> list[tuple[str, str, str, str]]:
            return sorted(
                (
                    str(item["instance"]), str(item["package_id"]),
                    str(item["version"]), str(item["content_digest"]),
                )
                for item in plan.get("decisions", []) if item.get("action") == "reuse"
            )

        for _ in range(self.AUTO_REPAIR_LIMIT):
            failures = [
                item for item in checked.get("checks", [])
                if item.get("verdict") in {"failed", "inconclusive"}
            ]
            if (
                checked.get("status") != "finished"
                or checked.get("verdict") != "failed"
                or checked.get("spec_qualified") is not True
                or not failures
            ):
                break
            state = self.design.specs.state()
            try:
                generated = generated_submodules(state)
                before = source_record(self.project.root, state, generated[0]["instance"])
                lock = self.design.library.read_lock()
                self.design.assembly.verify_current(state, lock)
                current_plan = self.design.preview_preparation()
            except (GeneratedSubmoduleError, AssemblyError, IPLibraryError, IndexError) as exc:
                raise ProductFlowBlocked(f"SoC 修复前锁定输入无效：{exc}") from exc
            if (
                not state.get("valid") or not state.get("frozen")
                or state.get("spec_digest") != record["spec_digest"]
                or state.get("acceptance_sources_digest") != record["acceptance_sources_digest"]
                or len(generated) != 1 or before["source"] != target
                or not current_plan.get("ready")
                or reused_packages(current_plan) != reused_packages(record["plan"])
            ):
                raise ProductFlowBlocked(
                    "SoC 修复前规格、冻结验收、IP 版本、装配或授权 RTL 已变化"
                )
            self._halt_if_requested()
            failed_ids = ", ".join(
                f"{item.get('id', '')}={item.get('verdict', '')}" for item in failures
            )
            try:
                log_tail = self.runs.run_log(checked["id"])[-8_000:]
            except Exception:
                log_tail = ""
            instruction = (
                f"产品流程的冻结 SoC 独立验收失败：{failed_ids}。只修复 {target} "
                "使其满足冻结 CSIR 的生成子模块行为；保持端口、零周期延迟与所有 IP "
                "连接不变。不得修改规格、验收 checker、固件、库源码、装配文件、"
                "技术目标或签核规则。平台随后会重新锁定该源文件并在新固定快照中运行"
                "原独立验收，不得把本次端口检查视为功能通过。"
                f"\n失败运行：{checked['id']}\n原始日志尾部：\n{log_tail}"
            )
            operation = self.runs.start_agent(
                instruction, framework, [target], stage="rtl_repair", max_repairs=0,
            )
            operation_id = operation["id"]
            with self._mutex:
                current = self.get(flow_id)
                current["active_repair_operation_id"] = operation_id
                current["repair_operations"].append(operation_id)
                current["retry_count"] = len(current["repair_operations"])
                self._write(current)
            try:
                completed = self._wait_repair_operation(
                    operation_id, max(120, int(self.project.config().agent_timeout) + 300),
                )
            finally:
                with self._mutex:
                    current = self.get(flow_id)
                    current["active_repair_operation_id"] = ""
                    self._write(current)
            self._halt_if_requested()
            if (
                completed.get("status") != "succeeded"
                or completed.get("engineering_verdict") != "repaired_unverified"
            ):
                raise ProductFlowError(
                    f"SoC RTL 修复操作 {operation_id} 未通过权限或接口检查："
                    + str(completed.get("summary", ""))[-500:]
                )
            after = source_record(self.project.root, state, generated[0]["instance"])
            if after["source_digest"] == before["source_digest"]:
                raise ProductFlowError("AI 没有改变失败的授权 RTL；保留原失败验收")
            updated_plan = self.design.preview_preparation()
            if (
                not updated_plan.get("ready")
                or updated_plan.get("spec_digest") != record["spec_digest"]
                or updated_plan.get("acceptance_sources_digest")
                != record["acceptance_sources_digest"]
                or updated_plan.get("generated_rtl_instances") != [generated[0]["instance"]]
                or reused_packages(updated_plan) != reused_packages(record["plan"])
            ):
                raise ProductFlowBlocked("修复后规格、验收或 IP 选型不再匹配已审查方案")
            with self.design.workflow_context(record["taskgraph_workflow_id"]):
                prepared = self.design.prepare_assembly(updated_plan["plan_digest"])
            self._halt_if_requested()
            with self._mutex:
                current = self.get(flow_id)
                current["plan"] = updated_plan
                current["plan_digest"] = updated_plan["plan_digest"]
                current["repair_preparations"].append({
                    "operation_id": operation_id,
                    "source_before": before["source_digest"],
                    "source_after": after["source_digest"],
                    "lock_digest": prepared["resolution"]["lock"]["lock_digest"],
                    "assembly_digest": prepared["assembly"]["assembly"]["assembly_digest"],
                    "assembly_artifact_id": prepared["assembly"]["artifact_id"],
                })
                self._write(current)
            validation = self.runs.start_validation(
                "all", config_override=self.design.assembly_validation_config(),
                workflow_id=record["taskgraph_workflow_id"],
            )
            checked = self._wait_child(validation["id"], 300)
            with self._mutex:
                current = self.get(flow_id)
                current["validation_run_ids"].append(validation["id"])
                current["child_run_id"] = validation["id"]
                self._write(current)
            self._halt_if_requested()
            if (
                checked.get("status") == "finished"
                and checked.get("verdict") == "passed"
                and checked.get("spec_qualified") is True
            ):
                break
        return checked

    def _execute(self, flow_id: str) -> None:
        import fcntl

        try:
            record = self.get(flow_id)
            self._stage(flow_id, "preparation", "running")
            if record.get("design_kind") == "generic_module" and record["plan"].get("assembly_digest"):
                current_plan = self.design.preview_preparation()
                if (
                    not current_plan.get("product_ready")
                    or current_plan.get("plan_digest") != record["plan_digest"]
                ):
                    raise ProductFlowBlocked("锁定 IP、装配或冻结 checker 已变化；请重新预览产品方案")
                with self.design.workflow_context(record["taskgraph_workflow_id"]):
                    prepared = self.design.prepare_assembly(record["plan_digest"])
                self._stage(flow_id, "preparation", "passed", verdict="passed", details={
                    "lock_digest": prepared["resolution"]["lock"]["lock_digest"],
                    "assembly_digest": prepared["assembly"]["assembly"]["assembly_digest"],
                    "acceptance_contract_digest": current_plan["acceptance_contract_digest"],
                    "ip_instances": len(prepared["assembly"]["assembly"]["instances"]),
                    "qualification_artifact_ids": [
                        item["artifact_id"] for item in prepared["qualifications"]
                    ],
                    "assembly_artifact_id": prepared["assembly"]["artifact_id"],
                })
            elif record.get("design_kind") == "generic_module":
                current_plan = self.design.preview_preparation()
                if (
                    not current_plan.get("ready")
                    or current_plan.get("plan_digest") != record["plan_digest"]
                ):
                    raise ProductFlowBlocked(
                        "通用设计 RTL、冻结 checker 或运行目标已变化；请重新预览产品方案"
                    )
                self._stage(
                    flow_id, "preparation", "passed", verdict="passed",
                    details={
                        "rtl_sha256": current_plan["rtl_sha256"],
                        "acceptance_contract_digest": current_plan[
                            "acceptance_contract_digest"
                        ],
                        "ip_instances": 0,
                    },
                )
            else:
                with self.design.workflow_context(record["taskgraph_workflow_id"]):
                    prepared = self.design.prepare_assembly(record["plan_digest"])
                self._stage(flow_id, "preparation", "passed", verdict="passed", details={
                    "lock_digest": prepared["resolution"]["lock"]["lock_digest"],
                    "assembly_digest": prepared["assembly"]["assembly"]["assembly_digest"],
                    "qualification_artifact_ids": [
                        item["artifact_id"] for item in prepared["qualifications"]
                    ],
                    "assembly_artifact_id": prepared["assembly"]["artifact_id"],
                })
            self._halt_if_requested()
            self._stage(flow_id, "validation", "running")
            state = self.design.specs.state()
            config = (
                self.design.assembly_validation_config()
                if state["document"].get("design_kind") == "single_clock_soc"
                or state["document"].get("design_kind") == "generic_module"
                and bool(state["document"].get("instances"))
                else self.project.config()
            )
            validation = self.runs.start_validation(
                "all", config_override=config,
                workflow_id=record["taskgraph_workflow_id"],
            )
            self._stage(flow_id, "validation", "running", child_run_id=validation["id"])
            checked = self._wait_child(validation["id"], 300)
            with self._mutex:
                current = self.get(flow_id)
                current["validation_run_ids"].append(validation["id"])
                self._write(current)
            self._halt_if_requested()
            if checked.get("verdict") != "passed":
                checked = (
                    self._repair_soc_validation(flow_id, record, checked)
                    if record.get("design_kind") == "single_clock_soc"
                    else self._repair_generic_validation(flow_id, record, checked)
                )
            self._halt_if_requested()
            valid = (
                checked.get("status") == "finished"
                and checked.get("verdict") == "passed"
                and checked.get("spec_qualified") is True
            )
            self._stage(
                flow_id, "validation", "passed" if valid else "failed",
                verdict=checked.get("verdict", "unknown"),
                child_run_id=checked["id"], details={
                    "validation_run_ids": self.get(flow_id)["validation_run_ids"],
                    "repair_operations": self.get(flow_id)["repair_operations"],
                    "repair_preparations": self.get(flow_id).get("repair_preparations", []),
                    "snapshot": checked.get("snapshot", {}),
                    "requirements": checked.get("requirements", []),
                    "checks": checked.get("checks", []),
                    "failed_checks": [
                        item.get("id", "") for item in checked.get("checks", [])
                        if item.get("verdict") not in {"passed", "not_run"}
                    ],
                    "errors": checked.get("errors", []),
                    "tool_versions": checked.get("tool_versions", {}),
                },
            )
            if not valid:
                failed_checks = [
                    item.get("id", "") for item in checked.get("checks", [])
                    if item.get("verdict") not in {"passed", "not_run"}
                ]
                detail = "、".join(failed_checks[:8]) or str(checked.get("error", ""))
                raise ProductFlowError(
                    f"固定快照独立验收未通过：{checked.get('verdict', 'unknown')}"
                    + (f"；检查 {detail}" if detail else "")
                )
            self._halt_if_requested()
            if not record["run_physical"]:
                self._update(flow_id, status="finished", verdict="functional_passed_physical_not_run",
                             reason="仅运行到固定快照功能验收；物理签核未执行", finished_at=self._now())
                return
            self._stage(flow_id, "physical_setup", "running")
            state = self.design.specs.state()
            if (
                not state.get("frozen") or not state.get("valid")
                or state.get("spec_digest") != record["spec_digest"]
                or state.get("acceptance_sources_digest") != record["acceptance_sources_digest"]
            ):
                raise ProductFlowError("功能验收后冻结规格或验收输入已变化")
            document = state["document"]
            kind = document.get("design_kind", "register_peripheral")
            if kind not in {"single_clock_soc", "register_peripheral", "generic_module"}:
                raise ProductFlowBlocked("当前自动物理编排不支持此设计类型")
            detected = self.project.detect_physical_project()
            if kind == "generic_module":
                generic = self.project.frozen_generic_physical_contract()
                expected_authority = (
                    "frozen generic IP lock" if generic["filelist"]
                    else "frozen generic CSIR"
                )
                if (
                    detected.get("source_authority") != expected_authority
                    or detected.get("suggested_top") != document["name"]
                    or detected.get("sources") != generic["sources"]
                ):
                    raise ProductFlowBlocked("物理流程未选中冻结通用模块的精确锁定 RTL 集")
                simulation_command = generic["simulation_command"]
            else:
                if (
                    detected.get("source_authority") != "integration/nebula.f"
                    or detected.get("suggested_top") != document["name"]
                ):
                    raise ProductFlowBlocked("物理流程未选中当前锁定的 IP 装配源码")
                simulation_command = (
                    "bash integration/nebula-verify.sh"
                    if kind == "single_clock_soc"
                    else self.project.config().simulation_command
                )
            target = document["technical_target"]
            configured = self.project.configure_physical_project(
                top_module=document["name"],
                clock_port=document["clocks"][0]["name"],
                clock_period_ns=float(target["clock_period_ns"]),
                platform=target["platform"],
                simulation_command=simulation_command,
            )
            environment = self.runs.physical_environment()
            self._stage(flow_id, "physical_setup", "passed" if environment.get("ready") else "blocked",
                        verdict="passed" if environment.get("ready") else "missing_tool",
                        details={"definition": configured.get("definition", {}),
                                 "environment": environment})
            if not environment.get("ready"):
                raise ProductFlowBlocked("物理工具或 PDK 尚未就绪；配置和环境检查已保留")
            self._halt_if_requested()
            self._stage(flow_id, "physical", "running")
            physical = self.runs.start_physical(
                "all", workflow_id=record["taskgraph_workflow_id"],
            )
            self._stage(flow_id, "physical", "running", child_run_id=physical["id"])
            signed = self._wait_child(physical["id"], record["physical_timeout_seconds"])
            self._halt_if_requested()
            passed = signed.get("status") == "finished" and signed.get("verdict") == "passed"
            self._stage(flow_id, "physical", "passed" if passed else "failed",
                        verdict=signed.get("verdict", "unknown"), child_run_id=physical["id"],
                        details={"summary": signed.get("summary", {}),
                                 "snapshot": signed.get("snapshot", {}),
                                 "artifact_count": len(signed.get("artifacts", [])),
                                 "error": signed.get("error", ""),
                                 "failure_class": signed.get("failure_class", ""),
                                 "tool_versions": signed.get("tool_versions", {})})
            if not passed:
                raise ProductFlowError(
                    f"物理签核未通过：{signed.get('verdict', 'unknown')}"
                    + (f"；{signed['error']}" if signed.get("error") else "")
                )
            self._halt_if_requested()
            self._stage(flow_id, "delivery", "running")
            delivery = self.design.check_delivery(
                force_artifact_hash=True, require_physical=True,
            )
            self._stage(flow_id, "delivery", "passed" if delivery["ready"] else "blocked",
                        verdict="passed" if delivery["ready"] else "not_ready",
                        details={"blockers": delivery["blockers"],
                                 "physical_run_id": delivery.get("physical_run_id", ""),
                                 "physical_evidence_digest": delivery.get("physical_evidence_digest", "")})
            self._update(flow_id, status="finished" if delivery["ready"] else "blocked",
                         verdict="ready" if delivery["ready"] else "not_ready",
                         reason="" if delivery["ready"] else "；".join(delivery["blockers"]),
                         finished_at=self._now())
        except Exception as exc:
            import traceback
            with self._mutex:
                current = self.get(flow_id)
                stopped = (
                    isinstance(exc, ProductFlowStopped)
                    or self._stop_event.is_set()
                    or current.get("status") == "stop_requested"
                )
                stage = next((item for item in current["stages"]
                              if item["id"] == current["current_stage"]), None)
                if stage is not None and stage["status"] == "running":
                    stage["status"] = (
                        "stopped" if stopped
                        else "blocked" if isinstance(exc, ProductFlowBlocked)
                        else "timeout" if isinstance(exc, ProductFlowTimeout)
                        else "failed"
                    )
                    stage["verdict"] = stage["status"]
                    stage["finished_at"] = self._now()
                status = (
                    "stopped" if stopped
                    else "blocked" if isinstance(exc, ProductFlowBlocked)
                    else "failed"
                )
                current.update(
                    status=status,
                    verdict=(
                        "stopped" if stopped
                        else "timeout" if isinstance(exc, ProductFlowTimeout)
                        else status
                    ),
                    reason=(
                        "用户停止了产品流程" if stopped
                        else str(exc) or type(exc).__name__
                    ),
                    error_class=(
                        "ProductFlowStopped" if stopped else type(exc).__name__
                    ),
                    error_traceback=(
                        "" if stopped or isinstance(exc, ProductFlowError)
                        else traceback.format_exc()
                    ),
                    finished_at=self._now(),
                )
                current["wall_seconds"] = self._wall_seconds(current)
                self._write(current)
        finally:
            with self._mutex:
                self._active_id = ""
                self._stop_event.clear()
                if self._lock_handle is not None:
                    fcntl.flock(self._lock_handle.fileno(), fcntl.LOCK_UN)
                    self._lock_handle.close()
                    self._lock_handle = None

    def stop(self, flow_id: str) -> dict[str, Any]:
        with self._mutex:
            if flow_id != self._active_id:
                raise ProductFlowError("该产品流程不是当前后端拥有的活动流程")
            self._stop_event.set()
            record = self.get(flow_id)
            if record["status"] not in self.ACTIVE:
                return record
            record["status"] = "stop_requested"
            self._write(record)
            child = record.get("child_run_id", "")
            repair_operation = record.get("active_repair_operation_id", "")
        if repair_operation:
            try:
                self.runs.stop_agent(repair_operation)
            except Exception:
                pass  # Worker records the terminal state after Agent shutdown.
        if child:
            try:
                self.runs.stop(child)
            except Exception:
                pass  # Worker will observe the stop and record the actual state.
        return self.get(flow_id)

    def stop_active(self) -> None:
        with self._mutex:
            flow_id = self._active_id
            worker = self._thread
        if flow_id:
            self.stop(flow_id)
            if worker is not None:
                worker.join(timeout=120)
