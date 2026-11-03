"""Application service for the specification → IP reuse → delivery flow."""

from __future__ import annotations

import datetime as dt
from contextlib import contextmanager
import hashlib
import io
import itertools
import json
import re
import shlex
import shutil
import tarfile
import tempfile
import threading
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

import chip_nebula
import yaml

from chip_nebula.taskgraph import (
    Artifact, ArtifactContent, ArtifactProducer, StaticTaskGraphStore,
)
from chip_nebula.taskgraph.assembly import AssemblyError, AssemblyService
from chip_nebula.taskgraph.architecture import ArchitecturePlanner
from chip_nebula.taskgraph.generic_acceptance import (
    GenericAcceptanceError, GenericAcceptanceWorkspace, checker_contract,
)
from chip_nebula.taskgraph.generic_rtl import GenericRTLContractError
from chip_nebula.taskgraph.generic_product import preview_generic_product
from chip_nebula.taskgraph.ip_library import IPLibrary, IPLibraryError, IPPackage
from chip_nebula.taskgraph.memory_generator import MemoryGenerator, MemoryGenerationError
from chip_nebula.taskgraph.generated_submodule import verify_submodule
from chip_nebula.taskgraph.product_flow import ProductPreparationPlanner
from chip_nebula.taskgraph.soc_acceptance import audit_soc_acceptance
from chip_nebula.taskgraph.specs import SpecificationError, SpecificationWorkspace
from chip_nebula.taskgraph.tool_executor import DeterministicToolExecutor, ToolCommand


class DesignDeliveryError(ValueError):
    pass


class DesignDeliveryService:
    def __init__(
        self,
        project_root: Path,
        *,
        runs_provider: Callable[[], list[dict[str, Any]]] | None = None,
        physical_fingerprint_provider: Callable[[], str] | None = None,
    ) -> None:
        self.root = project_root.resolve()
        self.specs = SpecificationWorkspace(self.root)
        self.library = IPLibrary(self.root)
        self.assembly = AssemblyService(self.root, self.library)
        self.memory = MemoryGenerator(self.root)
        self.architecture = ArchitecturePlanner(self.library)
        self.runs_provider = runs_provider or (lambda: [])
        self.physical_fingerprint_provider = physical_fingerprint_provider
        self.database = (
            self.root / ".chip_nebula" / "shared" / "memory" / "taskgraph-v2.db"
        )
        self.deliveries_root = self.root / ".chip_nebula" / "deliveries"
        self._physical_digest_cache: dict[tuple[str, int, int, str], bool] = {}
        self._workflow_context = threading.local()

    @contextmanager
    def workflow_context(self, workflow_id: str):
        previous = getattr(self._workflow_context, "id", "")
        self._workflow_context.id = workflow_id
        try:
            yield
        finally:
            self._workflow_context.id = previous

    def bootstrap(self) -> dict[str, Any]:
        builtin_root = Path(chip_nebula.__file__).parent / "configs" / "ip"
        imported = self.library.import_builtins(builtin_root)
        for package in imported:
            self._record_package(package)
        return self.summary()

    def summary(self) -> dict[str, Any]:
        spec = self.specs.state()
        lock = self.library.read_lock(optional=True)
        assembly = self._read_json(self.root / "integration" / "nebula-assembly.json")
        coverage = self.coverage()
        generic_acceptance = None
        if (
            spec.get("frozen") and spec.get("valid")
            and spec.get("document", {}).get("design_kind") == "generic_module"
        ):
            try:
                generic_acceptance = GenericAcceptanceWorkspace(self.root).state(spec)
            except (GenericAcceptanceError, GenericRTLContractError) as exc:
                generic_acceptance = {"frozen": False, "valid": False, "reason": str(exc)}
        return {
            "spec": spec,
            "generic_acceptance": generic_acceptance,
            "soc_acceptance": audit_soc_acceptance(self.root, spec),
            "architecture": self.architecture.preview(spec),
            "catalog": self.library.catalog(),
            "lock": lock or None,
            "assembly": assembly or None,
            "generated_memory": self.memory.current(spec),
            "coverage": coverage,
            "delivery": self.check_delivery(),
        }

    def architecture_plan(self) -> dict[str, Any]:
        """Preview IP choices and missing modules without changing the project."""
        return self.architecture.preview(self.specs.state())

    def preview_preparation(self) -> dict[str, Any]:
        """Show exact IP choices and commands without changing the project."""
        from chip_nebula.dashboard.workbench import WorkbenchProject

        state = self.specs.state()
        if (
            state.get("document", {}).get("design_kind") == "generic_module"
            and not state.get("document", {}).get("instances")
        ):
            return preview_generic_product(self.root, state)
        try:
            self.assembly.verify_acceptance_contract(state)
            acceptance_blocker = ""
        except AssemblyError as exc:
            acceptance_blocker = str(exc)
        with tempfile.TemporaryDirectory(prefix="chip-nebula-product-preview-") as temporary:
            catalog = IPLibrary(Path(temporary))
            builtin_root = Path(chip_nebula.__file__).parent / "configs" / "ip"
            catalog.import_builtins(builtin_root)
            for package in self.library.packages():
                self.library.verify_package(package)
                catalog.import_package(package.root)
                source_evidence = (
                    self.library.evidence_root
                    / package.content_digest.removeprefix("sha256:")
                )
                if source_evidence.is_dir():
                    shutil.copytree(
                        source_evidence,
                        catalog.evidence_root / package.content_digest.removeprefix("sha256:"),
                        dirs_exist_ok=True,
                    )
            return ProductPreparationPlanner(catalog, project_root=self.root).preview(
                state, current_lock=self.library.read_lock(optional=True),
                acceptance_blocker=acceptance_blocker,
                validation_config=asdict(WorkbenchProject(self.root).config()),
            )

    def _check_preparation_inputs(self, plan: Mapping[str, Any]) -> None:
        state = self.specs.state()
        if (
            not state.get("valid") or not state.get("frozen")
            or state.get("spec_digest") != plan.get("spec_digest")
            or state.get("acceptance_sources_digest") != plan.get("acceptance_sources_digest")
        ):
            raise DesignDeliveryError("冻结规格或独立验收输入已改变；请重新预览方案")
        self.assembly.verify_acceptance_contract(state)

    def prepare_assembly(self, expected_plan_digest: str) -> dict[str, Any]:
        """Run reviewed package qualification, generation, lock and elaboration."""
        if not expected_plan_digest:
            raise DesignDeliveryError("必须先预览并提供准备方案摘要")
        plan = self.preview_preparation()
        if plan["plan_digest"] != expected_plan_digest:
            raise DesignDeliveryError("准备方案已变化；请重新预览并确认 IP 与工具命令")
        if not plan["ready"]:
            raise DesignDeliveryError("准备方案存在阻断项：" + "；".join(plan["blockers"]))
        self._check_preparation_inputs(plan)
        self.bootstrap()
        actual = self.preview_preparation()
        if actual["plan_digest"] != expected_plan_digest:
            raise DesignDeliveryError("IP 目录变化导致准备方案失效；请重新预览")
        qualifications = []
        for item in plan["qualifications"]:
            for configuration in item["configurations"]:
                self._check_preparation_inputs(plan)
                result = self.validate_ip(
                    item["package_id"], item["version"], configuration,
                )
                records = result["records"]
                qualifications.append({
                    "package_id": item["package_id"],
                    "version": item["version"],
                    "content_digest": item["content_digest"],
                    "parameters": configuration,
                    "records": records,
                    "artifact_id": result["artifact_id"],
                })
                if len(records) != 1 or records[0]["verdict"] != "passed":
                    raise DesignDeliveryError(
                        f"IP 资格验证失败：{item['package_id']}@{item['version']} {configuration}"
                    )
        self._check_preparation_inputs(plan)
        generation = self.generate_memories() if plan["generated_instances"] else None
        state = self.specs.state()
        generated_rtl_checks = []
        for name in plan.get("generated_rtl_instances", []):
            checked = verify_submodule(self.root, state, name)
            generated_rtl_checks.append({"instance": name, **checked})
            if checked.get("verdict") != "passed":
                raise DesignDeliveryError(
                    f"生成子模块 {name} 未通过真实 Verilator 接口契约："
                    + "；".join(checked.get("diagnostics", []))
                )
        resolution = self.library.resolve(state)
        expected = {
            item["instance"]: (item["package_id"], item["version"], item["content_digest"])
            for item in plan["decisions"] if item["action"] == "reuse"
        }
        selected = {
            item["instance"]: (item["package_id"], item["version"], item["content_digest"])
            for item in resolution.lock["packages"] if item["kind"] == "instance"
        }
        actual_generated = {item["instance"] for item in resolution.lock["generated_modules"]}
        expected_generated = {
            *plan["generated_instances"], *plan.get("generated_rtl_instances", []),
        }
        if selected != expected or actual_generated != expected_generated:
            raise DesignDeliveryError("IP 解析结果不同于已审查的方案；未写入依赖锁")
        self._check_preparation_inputs(plan)
        locked = self.resolve()
        self._check_preparation_inputs(plan)
        assembly = self.assemble()
        return {
            "plan": plan, "qualifications": qualifications,
            "generation": generation, "generated_rtl_checks": generated_rtl_checks,
            "resolution": locked, "assembly": assembly,
        }

    def save_spec(self, document: Mapping[str, Any]) -> dict[str, Any]:
        state = self.specs.save(document)
        self._mark_runs_stale()
        return state

    def compile_spec(self) -> dict[str, Any]:
        return self.specs.state()

    def freeze_spec(self) -> dict[str, Any]:
        state = self.specs.freeze()
        self._record_spec_artifacts(state)
        self._mark_runs_stale()
        return state

    def import_ip(self, source: Path) -> dict[str, Any]:
        package = self.library.import_package(source)
        artifact_id = self._record_package(package)
        return {"package": package.to_dict(evidence=self.library.evidence(package)), "artifact_id": artifact_id}

    def import_git_ip(
        self, repository: str, ref: str, *, subdirectory: str = "",
    ) -> dict[str, Any]:
        package = self.library.import_git(repository, ref, subdirectory=subdirectory)
        artifact_id = self._record_package(package)
        return {
            "package": package.to_dict(evidence=self.library.evidence(package)),
            "artifact_id": artifact_id,
        }

    def validate_ip(
        self, package_id: str, version: str, parameters: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        result = self.library.validate(package_id, version, parameters)
        records = result["records"]
        package = self.library.find(package_id, version)
        assert package is not None
        verdict = "passed" if records and all(item["verdict"] == "passed" for item in records) else "failed"
        checks = [
            {
                "id": f"IP.{index + 1}", "verdict": item["verdict"],
                "parameters": item["parameters"],
            }
            for index, item in enumerate(records)
        ]
        tool_versions: dict[str, str] = {}
        for item in records:
            tool_versions.update(item.get("tool_versions", {}))
        artifact_id = self._record(
            action="ip-qualification",
            outputs=[(
                "report", "verification.report", 2,
                {
                    "subject": package.content_digest, "verdict": verdict,
                    "spec_digest": package.content_digest,
                    "requirements": [], "checks": checks,
                    "input_digests": [package.content_digest],
                    "tool_versions": tool_versions,
                },
                ArtifactContent(kind="blob"),
                {
                    "package_id": package_id, "version": version,
                    "uri": str(self.library.evidence_root),
                },
            )],
        )[0]
        result["artifact_id"] = artifact_id
        return result

    def resolve(self, *, upgrade: bool = False) -> dict[str, Any]:
        state = self.specs.state()
        resolution = self.library.resolve(state, prefer_locked=not upgrade)
        lock = self.library.save_lock(resolution)
        spec_artifacts = self._record_spec_artifacts(state)
        package_artifacts = []
        for item in lock["packages"]:
            package = self.library.package_for_lock(item)
            package_artifacts.append(self._record_package(package))
        generated_artifacts: list[str] = []
        memory_entries = [
            item for item in lock.get("generated_modules", [])
            if item.get("kind") == "generated"
        ]
        child_entries = [
            item for item in lock.get("generated_modules", [])
            if item.get("kind") == "generated_rtl"
        ]
        if memory_entries:
            generation_digests = {
                item["generation_digest"] for item in memory_entries
            }
            if len(generation_digests) != 1:
                raise DesignDeliveryError("IP lock contains inconsistent generated memory versions")
            generated_artifacts = self._artifact_ids_for_digests(
                list(generation_digests), exact_type="rtl.generated",
            )
            if not generated_artifacts:
                generated_artifacts = [self.generate_memories()["artifact_id"]]
        for entry in child_entries:
            existing = self._artifact_ids_for_digests(
                [entry["generation_digest"]], exact_type="rtl.generated",
            )
            if existing:
                generated_artifacts.extend(existing)
                continue
            record = {
                "spec_digest": state["spec_digest"],
                "acceptance_sources_digest": str(state.get("acceptance_sources_digest", "")),
                "generation_digest": entry["generation_digest"],
                "modules": [{
                    "instance": entry["instance"],
                    "module": entry["top_module"],
                    "rtl": entry["files"][0],
                    "verification_status": "not_run",
                }],
                "file_hashes": entry["file_hashes"],
                "generated_files": entry["files"],
            }
            generated_artifacts.extend(self._record(
                action="generic-child-register",
                inputs=spec_artifacts,
                outputs=[(
                    "generated", "rtl.generated", 1, record,
                    ArtifactContent(kind="files", paths=tuple(entry["files"])),
                    {"semantic_digest": entry["generation_digest"],
                     "verification_status": "not_run"},
                )],
            ))
        artifact_id = self._record(
            action="ip-upgrade" if upgrade else "ip-resolve",
            inputs=[*spec_artifacts, *package_artifacts, *generated_artifacts],
            outputs=[(
                "lock", "ip.lock", 1, lock,
                ArtifactContent(kind="files", paths=("ip/nebula.lock.json",)),
                {"decisions": list(resolution.decisions)},
            )],
        )[0]
        self._mark_runs_stale()
        return {"lock": lock, "decisions": list(resolution.decisions), "artifact_id": artifact_id}

    def assemble(self) -> dict[str, Any]:
        state = self.specs.state()
        lock = self.library.read_lock()
        if state["document"].get("design_kind") == "generic_module" and state["document"].get("instances"):
            try:
                accepted = GenericAcceptanceWorkspace(self.root).state(state).get("valid")
            except (GenericAcceptanceError, GenericRTLContractError):
                accepted = False
            if accepted:
                record = self.assembly.verify_current(state, lock)
                existing = self._artifact_ids_for_digests(
                    [record["assembly_digest"]], exact_type="rtl.assembly",
                )
                if existing:
                    # Rewriting elaboration logs would invalidate the human-frozen checker inputs.
                    return {"assembly": record, "artifact_id": existing[-1]}
        record = self.assembly.materialize(state, lock)
        top = record["top_module"]
        strict_pins = (
            " -Werror-PINMISSING" if state["document"].get("design_kind") == "generic_module"
            else ""
        )
        result = DeterministicToolExecutor().execute(
            self.root,
            [ToolCommand(
                "elaboration",
                f"verilator --lint-only -Wall -Wno-fatal{strict_pins} --top-module {top} -f integration/nebula.f",
                ".", 120, "",
            )],
        )
        record["elaboration"] = {
            "status": result.status, "verdict": result.verdict,
            "tool_versions": result.tool_versions,
            "commands": [
                {
                    "name": item.name, "command": item.command,
                    "returncode": item.returncode, "reason": item.reason,
                }
                for item in result.commands
            ],
            "log": result.log,
        }
        (self.root / "integration" / "nebula-assembly.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        if result.verdict != "passed":
            raise DesignDeliveryError("装配已生成，但真实编译展开检查失败")
        inputs = self._artifact_ids_for_digests(
            [state["spec_digest"], lock["lock_digest"], *[
                item["content_digest"] for item in lock["packages"]
            ], *[
                item["generation_digest"] for item in lock.get("generated_modules", [])
            ]]
        )
        artifact_id = self._record(
            action="ip-assemble",
            inputs=inputs,
            outputs=[(
                "assembly", "rtl.assembly", 1,
                {
                    "spec_digest": record["spec_digest"],
                    "lock_digest": record["lock_digest"],
                    "instances": record["instances"],
                    "connections": record["connections"],
                    "assembly_digest": record["assembly_digest"],
                },
                ArtifactContent(kind="files", paths=tuple(record["generated_files"])),
                {"elaboration": record["elaboration"]},
            )],
        )[0]
        self._mark_runs_stale()
        return {"assembly": record, "artifact_id": artifact_id}

    def assembly_validation_config(self):
        """Build an ephemeral workbench run profile for the locked SoC top."""
        from chip_nebula.dashboard.workbench import WorkbenchConfig, WorkbenchProject

        state = self.specs.state()
        if not state.get("valid") or not state.get("frozen"):
            raise DesignDeliveryError("装配验证需要未改变的冻结规格")
        lock = self.library.read_lock()
        record = self.assembly.verify_current(state, lock)
        if record.get("elaboration", {}).get("verdict") != "passed":
            raise DesignDeliveryError("装配尚未通过真实编译展开")
        design_kind = state["document"].get("design_kind")
        if design_kind not in {"single_clock_soc", "generic_module"}:
            raise DesignDeliveryError("当前装配验证入口仅支持单时钟 SoC 或具名端口通用 IP")
        if design_kind == "single_clock_soc":
            try:
                self.assembly.verify_acceptance_contract(state)
            except AssemblyError as exc:
                raise DesignDeliveryError(str(exc)) from exc
        else:
            try:
                acceptance = GenericAcceptanceWorkspace(self.root).state(state)
            except (GenericAcceptanceError, GenericRTLContractError) as exc:
                raise DesignDeliveryError(str(exc)) from exc
            if not acceptance.get("valid"):
                raise DesignDeliveryError(
                    "装配设计的独立 checker 尚未冻结或已过期：" + acceptance.get("reason", "")
                )
        source_files = [
            relative for relative in (self.root / "integration/nebula.f").read_text(
                encoding="utf-8",
            ).splitlines()
            if relative and not relative.startswith(("+", "-"))
        ]
        project = WorkbenchProject(self.root)
        current = project.config()
        document = asdict(current)
        if design_kind == "generic_module":
            contract = acceptance["contract"]
            document.update({
                "top_module": record["top_module"],
                "validation_mode": "commands",
                "design_files": source_files,
                "testbench_files": [contract["testbench"]],
                "simulation_assets": [],
                "filelists": [contract["filelist"]],
                "source_globs": [
                    "integration/**", "ip/vendor/**", "tb/**", "spec/**",
                    "ip/nebula.lock.json",
                ],
                "lint_command": (
                    "verilator --lint-only --sv -Wall -Wno-fatal "
                    f"-Werror-PINMISSING --top-module {record['top_module']} "
                    "-f integration/nebula.f"
                ),
                "simulation_command": acceptance["runner"],
                "workdir": ".",
                "success_pattern": "",
                "success_evidence": {},
                "report_globs": list(dict.fromkeys([
                    *current.report_globs, "build/chip-nebula-acceptance/*.out",
                ])),
                "waveform_globs": list(dict.fromkeys([
                    *current.waveform_globs, "build/*.vcd",
                ])),
            })
            return WorkbenchConfig.from_document(document)
        document.update({
            "top_module": record["top_module"],
            "validation_mode": "commands",
            "design_files": source_files,
            "testbench_files": [
                path for path in state["document"].get("acceptance_sources", [])
                if path.startswith("tb/") and path.endswith((".sv", ".v"))
            ],
            "simulation_assets": [
                path for path in state["document"].get("acceptance_sources", [])
                if path.startswith("firmware/")
            ],
            "filelists": ["integration/nebula.f"],
            "source_globs": [
                "integration/nebula_assembly.sv", "integration/nebula.f",
                "integration/nebula-assembly.json", "integration/nebula-verify.sh",
                "ip/vendor/**", "generated/memory/**", "tb/**", "firmware/**",
            ],
            "lint_command": (
                "verilator --lint-only -Wall -Wno-fatal "
                f"--top-module {record['top_module']} -f integration/nebula.f"
            ),
            "simulation_command": "bash integration/nebula-verify.sh",
            "workdir": ".",
            "success_pattern": "SOC_ASSEMBLY_CHECKS_PASSED",
            "report_globs": list(dict.fromkeys([
                *current.report_globs, "build/chip-nebula-assembly/*.compile.log",
                "build/chip-nebula-assembly/*.simulation.log",
                "build/cpu-isa/*.log",
            ])),
            "waveform_globs": list(dict.fromkeys([
                *current.waveform_globs, "build/*.vcd",
            ])),
        })
        return WorkbenchConfig.from_document(document)

    def generate_memories(self) -> dict[str, Any]:
        """Publish versioned memory RTL without claiming independent verification."""
        state = self.specs.state()
        record = self.memory.materialize(state)
        existing = self._artifact_ids_for_digests(
            [record["generation_digest"]], exact_type="rtl.generated",
        )
        artifact_id = existing[0] if existing else self._record(
            action="memory-generate",
            inputs=self._record_spec_artifacts(state),
            outputs=[(
                "generated", "rtl.generated", 1, record,
                ArtifactContent(kind="files", paths=tuple(record["generated_files"])),
                {"semantic_digest": record["generation_digest"],
                 "verification_status": "not_run"},
            )],
        )[0]
        if not existing:
            self._mark_runs_stale()
        return {"generation": record, "artifact_id": artifact_id,
                "verification_status": "not_run"}

    def coverage(self) -> dict[str, Any]:
        runs = self.runs_provider()
        latest = next((item for item in runs if item.get("kind") == "validation"), None)
        state = self.specs.state()
        checks = latest.get("checks", []) if latest else []
        requirements = latest.get("requirements", []) if latest else []
        spec_qualified = bool(latest and latest.get("spec_qualified"))
        input_current = bool(latest and latest.get("verdict") != "stale")
        spec_current = bool(
            spec_qualified
            and latest.get("spec_digest") == state.get("spec_digest")
        )
        current = bool(
            input_current and (not spec_qualified or spec_current)
        )
        return {
            "run_id": latest.get("id", "") if latest else "",
            "verdict": latest.get("verdict", "not_run") if latest else "not_run",
            "current": current,
            "input_current": input_current,
            "spec_current": spec_current,
            "checks": checks,
            "requirements": requirements,
            "spec_qualified": spec_qualified,
        }

    def _qualified_soc_physical_run(
        self, runs: list[dict[str, Any]], *, force_artifact_hash: bool = False,
    ) -> tuple[dict[str, Any] | None, str]:
        """Require current complete-flow signoff and its archived offline outputs."""
        run = next((
            item for item in runs
            if item.get("kind") == "physical" and item.get("mode") == "all"
        ), None)
        if run is None:
            return None, "SoC 尚未运行完整 RTL→GDS、STA、DRC 和 LVS"
        if run.get("status") != "finished" or run.get("verdict") != "passed":
            return None, "SoC 最近一次完整物理运行未通过或已过期"
        from chip_nebula.dashboard.workbench import WorkbenchError, WorkbenchProject
        try:
            current_fingerprint = (
                self.physical_fingerprint_provider()
                if self.physical_fingerprint_provider is not None
                else WorkbenchProject(self.root).physical_fingerprint()
            )
        except (OSError, ValueError, WorkbenchError) as exc:
            return None, f"无法核对 SoC 当前物理输入：{exc}"
        if run.get("input_fingerprint") != current_fingerprint:
            return None, "SoC 物理证据对应旧的规格、RTL、依赖或技术目标"
        summary = run.get("summary")
        if not isinstance(summary, dict):
            return None, "SoC 物理运行缺少签核摘要"
        metrics = summary.get("metrics")
        if not isinstance(metrics, dict) or not (
            summary.get("status") in {"passed", "physical_passed"}
            and summary.get("functional_simulation") == "passed"
            and summary.get("detailed_routing_violations") == 0
            and summary.get("drc_violations") == 0
            and summary.get("lvs") == "matched"
            and metrics.get("setup_violations") == 0
            and metrics.get("hold_violations") == 0
        ):
            return None, "SoC 缺少通过的仿真、STA、DRC 或 LVS 签核结论"
        stages = run.get("physical_stages")
        if not isinstance(stages, list) or not any(
            isinstance(item, dict) and item.get("id") == "signoff"
            and item.get("status") == "passed" for item in stages
        ):
            return None, "SoC 签核阶段没有完成"
        run_id = run.get("id")
        if not isinstance(run_id, str) or not run_id or "/" in run_id or ".." in run_id:
            return None, "SoC 物理运行 ID 无效"
        base = (self.root / ".chip_nebula/workbench/runs" / run_id / "artifacts").resolve()
        artifacts = run.get("artifacts")
        if not isinstance(artifacts, list):
            return None, "SoC 物理运行缺少归档工件清单"
        suffixes: set[str] = set()
        for item in artifacts:
            if not isinstance(item, dict) or not isinstance(item.get("path"), str):
                continue
            relative = item["path"]
            suffix = Path(relative).suffix.lower()
            if suffix not in {".gds", ".v", ".def", ".odb", ".spef"}:
                continue
            path = (base / relative).resolve()
            if base not in path.parents or not path.is_file():
                continue
            expected_digest = str(item.get("sha256", "")).removeprefix("sha256:")
            if not expected_digest:
                continue
            stat = path.stat()
            cache_key = (str(path), stat.st_size, stat.st_mtime_ns, expected_digest)
            matching = self._physical_digest_cache.get(cache_key)
            if force_artifact_hash or matching is None:
                digest = hashlib.sha256()
                with path.open("rb") as source:
                    for chunk in iter(lambda: source.read(1024 * 1024), b""):
                        digest.update(chunk)
                matching = digest.hexdigest() == expected_digest
                self._physical_digest_cache[cache_key] = matching
            if matching:
                suffixes.add(suffix)
        missing = {".gds", ".v", ".def", ".odb", ".spef"} - suffixes
        if missing:
            return None, "SoC 离线交付工件缺失或摘要不符：" + ", ".join(sorted(missing))
        return run, ""

    def _check_generic_delivery(
        self, state: Mapping[str, Any], *,
        force_artifact_hash: bool, require_physical: bool,
    ) -> dict[str, Any]:
        assembled = bool(state.get("document", {}).get("instances"))
        plan = self.preview_preparation() if assembled else preview_generic_product(self.root, state)
        blockers = list(plan["blockers"])
        if assembled:
            if not plan.get("product_ready"):
                blockers.extend(
                    item for item in plan.get("product_blockers", [])
                    if not item.startswith("GDS 需要")
                )
            if require_physical and not plan.get("physical_ready"):
                blockers.append("通用 IP 尚无已冻结的单时钟物理技术目标")
        coverage = self.coverage()
        if (
            coverage["verdict"] != "passed"
            or not coverage["current"]
            or not coverage["spec_qualified"]
        ):
            blockers.append("当前通用规格和源码没有通过固定快照独立验收")
        expected_checks = {
            str(item.get("id")) for item in state.get("acceptance_plan", {}).get("checks", [])
            if isinstance(item, dict)
        }
        actual_checks = {
            str(item.get("id")): item.get("verdict")
            for item in coverage["checks"] if isinstance(item, dict)
        }
        expected_requirements = set(
            str(item) for item in state.get("acceptance_plan", {}).get("requirement_ids", [])
        )
        actual_requirements = {
            str(item.get("id")): item.get("verdict")
            for item in coverage["requirements"] if isinstance(item, dict)
        }
        if (
            not expected_checks or not expected_requirements
            or any(actual_checks.get(item) != "passed" for item in expected_checks)
            or any(actual_requirements.get(item) != "passed" for item in expected_requirements)
        ):
            blockers.append("通用模块需求证据矩阵仍有未通过、缺失或未执行项")
        physical_run: dict[str, Any] | None = None
        if require_physical:
            physical_run, physical_blocker = self._qualified_soc_physical_run(
                self.runs_provider(), force_artifact_hash=force_artifact_hash,
            )
            if physical_blocker:
                blockers.append(physical_blocker.replace("SoC ", "通用模块 ", 1))
        return {
            "ready": not blockers,
            "blockers": blockers,
            "spec_digest": state.get("spec_digest", ""),
            "lock_digest": plan.get("lock_digest", ""),
            "assembly_digest": plan.get("assembly_digest", ""),
            "rtl_sha256": plan.get("rtl_sha256", ""),
            "acceptance_contract_digest": plan.get("acceptance_contract_digest", ""),
            "validation_run_id": coverage["run_id"],
            "physical_run_id": physical_run.get("id", "") if physical_run else "",
            "physical_evidence_digest": (
                physical_run.get("evidence_digest", "") if physical_run else ""
            ),
        }

    def check_delivery(
        self, *, force_artifact_hash: bool = False, require_physical: bool = False,
    ) -> dict[str, Any]:
        blockers: list[str] = []
        try:
            state = self.specs.state()
        except SpecificationError as exc:
            return {"ready": False, "blockers": [str(exc)]}
        if (
            state.get("configured")
            and state.get("document", {}).get("design_kind") == "generic_module"
        ):
            return self._check_generic_delivery(
                state, force_artifact_hash=force_artifact_hash,
                require_physical=require_physical,
            )
        if not state.get("configured"):
            blockers.append("尚未创建项目规格")
        elif not state.get("frozen") or not state.get("valid"):
            blockers.append("规格与验收尚未冻结或存在阻断问题")
        if state.get("frozen") and state.get("valid") and (
            state.get("document", {}).get("design_kind") == "single_clock_soc"
        ):
            try:
                self.assembly.verify_acceptance_contract(state)
            except AssemblyError as exc:
                blockers.append(str(exc))
        try:
            lock = self.library.read_lock()
        except IPLibraryError as exc:
            lock = {}
            blockers.append(str(exc))
        if lock and lock.get("spec_digest") != state.get("spec_digest"):
            blockers.append("IP 锁文件对应旧规格")
        assembly = self._read_json(self.root / "integration" / "nebula-assembly.json")
        if not assembly:
            blockers.append("尚未生成装配结果")
        elif lock and (
            assembly.get("spec_digest") != state.get("spec_digest")
            or assembly.get("lock_digest") != lock.get("lock_digest")
        ):
            blockers.append("装配结果已过期")
        elif assembly.get("elaboration", {}).get("verdict") != "passed":
            blockers.append("装配结果未通过真实编译展开")
        if lock:
            changed = self.assembly.verify_vendor_integrity(lock)
            if changed:
                blockers.append("锁定源码被修改或缺失：" + ", ".join(changed[:5]))
            if assembly and state.get("valid") and state.get("frozen"):
                try:
                    self.assembly.verify_current(state, lock)
                except AssemblyError as exc:
                    blockers.append("装配产物完整性检查失败：" + str(exc))
        coverage = self.coverage()
        if coverage["verdict"] != "passed" or not coverage["current"]:
            blockers.append("当前规格和源码没有通过固定快照验收")
        if not coverage["spec_qualified"]:
            blockers.append("最新验证没有绑定冻结规格")
        planned_checks = [
            str(item.get("id"))
            for item in state.get("acceptance_plan", {}).get("checks", [])
            if isinstance(item, dict) and item.get("status") == "planned"
        ]
        if planned_checks:
            blockers.append("验收计划仍有未实现检查：" + ", ".join(planned_checks))
        expected_checks = {
            str(item.get("id")) for item in state.get("acceptance_plan", {}).get("checks", [])
            if isinstance(item, dict)
        }
        actual_checks = {
            str(item.get("id")): item.get("verdict")
            for item in coverage["checks"] if isinstance(item, dict)
        }
        expected_requirements = set(
            str(item) for item in state.get("acceptance_plan", {}).get("requirement_ids", [])
        )
        actual_requirements = {
            str(item.get("id")): item.get("verdict")
            for item in coverage["requirements"] if isinstance(item, dict)
        }
        if (
            not expected_checks or not expected_requirements
            or any(actual_checks.get(item) != "passed" for item in expected_checks)
            or any(actual_requirements.get(item) != "passed" for item in expected_requirements)
        ):
            blockers.append("需求证据矩阵仍有未通过、缺失或未执行项")
        physical_run: dict[str, Any] | None = None
        if require_physical or state.get("document", {}).get("design_kind") == "single_clock_soc":
            physical_run, physical_blocker = self._qualified_soc_physical_run(
                self.runs_provider(), force_artifact_hash=force_artifact_hash,
            )
            if physical_blocker:
                blockers.append(
                    physical_blocker.replace("SoC ", "外设 ", 1)
                    if state.get("document", {}).get("design_kind") != "single_clock_soc"
                    else physical_blocker
                )
        return {
            "ready": not blockers,
            "blockers": blockers,
            "spec_digest": state.get("spec_digest", ""),
            "lock_digest": lock.get("lock_digest", "") if lock else "",
            "assembly_digest": assembly.get("assembly_digest", "") if assembly else "",
            "validation_run_id": coverage["run_id"],
            "physical_run_id": physical_run.get("id", "") if physical_run else "",
            "physical_evidence_digest": physical_run.get("evidence_digest", "") if physical_run else "",
        }

    def export_delivery(
        self, *, confirmed: bool, include_physical: bool = False,
    ) -> dict[str, Any]:
        if not confirmed:
            raise DesignDeliveryError("最终交付需要用户明确确认")
        check = self.check_delivery(
            force_artifact_hash=True, require_physical=include_physical,
        )
        if not check["ready"]:
            raise DesignDeliveryError("交付门禁未通过：" + "；".join(check["blockers"]))
        delivery_id = f"delivery-{dt.datetime.now().strftime('%Y%m%dT%H%M%S')}-{uuid.uuid4().hex[:6]}"
        directory = self.deliveries_root / delivery_id
        directory.mkdir(parents=True, exist_ok=False)
        relative_files = sorted(set(
            self._delivery_files(check["validation_run_id"])
            + (self._delivery_files(check["physical_run_id"])
               if check.get("physical_run_id") else [])
        ))
        files = [
            {
                "path": relative,
                "sha256": hashlib.sha256((self.root / relative).read_bytes()).hexdigest(),
                "size": (self.root / relative).stat().st_size,
            }
            for relative in relative_files
        ]
        state = self.specs.state()
        kind = state["document"].get("design_kind")
        soc = kind == "single_clock_soc"
        generic = kind == "generic_module"
        physical_included = soc or bool(check.get("physical_run_id"))
        if generic:
            assembled = bool(state["document"].get("instances"))
            source = (
                "integration/nebula_assembly.sv" if assembled
                else preview_generic_product(self.root, state)["rtl"]
            )
            top = str(state["document"]["name"])
            checker_runner = GenericAcceptanceWorkspace(self.root).state(state)["runner"]
            lint = (
                f"verilator --lint-only --sv -Wall -Wno-fatal -Werror-PINMISSING "
                f"--top-module {top} -f integration/nebula.f"
                if assembled else
                f"verilator --lint-only --sv -Wall -Wno-fatal --top-module {top} {source}"
            )
            reproduce = [lint, checker_runner]
        else:
            reproduce = (
                ["bash integration/nebula-verify.sh"] if soc else ["make lint", "make test"]
            )
        if physical_included:
            reproduce.append("bash physical/chip-nebula/run.sh all")
        reproduce_body = (
            "bash integration/nebula-verify.sh\n" if soc else
            (
                'export PATH="$CHIP_NEBULA_RTL2GDS_TOOL_ROOT/oss-cad-suite/bin:'
                '$CHIP_NEBULA_RTL2GDS_TOOL_ROOT/bin:$PATH"\n'
                f"{lint}\n{checker_runner}\n"
            ) if generic else
            "make lint\nmake test\n"
        )
        if physical_included:
            reproduce_body += (
                ': "${CHIP_NEBULA_RTL2GDS_TOOL_ROOT:?set the pinned EDA tool root}"\n'
                ': "${ORFS_ROOT:?set the pinned OpenROAD-flow-scripts root}"\n'
                'export CHIP_NEBULA_RTL2GDS_TOOL_ROOT ORFS_ROOT\n'
                'export CHIP_NEBULA_RTL2GDS_WORK_ROOT="$bundle_root/build/rtl-to-gds"\n'
                "bash physical/chip-nebula/run.sh all\n"
            )
        reproduce_script = (
            "#!/usr/bin/env bash\nset -euo pipefail\n"
            'bundle_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"\n'
            'cd -- "$bundle_root"\n'
            + reproduce_body
        ).encode("utf-8")
        files.append({
            "path": "reproduce.sh",
            "sha256": hashlib.sha256(reproduce_script).hexdigest(),
            "size": len(reproduce_script),
        })
        manifest = {
            "schema_version": 1,
            "delivery_id": delivery_id,
            "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "verdict": "passed",
            "spec_digest": check["spec_digest"],
            "lock_digest": check["lock_digest"],
            "assembly_digest": check["assembly_digest"],
            "rtl_sha256": check.get("rtl_sha256", ""),
            "acceptance_contract_digest": check.get("acceptance_contract_digest", ""),
            "input_digests": [
                value for value in (
                    check["spec_digest"], check["lock_digest"],
                    check["assembly_digest"], check.get("rtl_sha256", ""),
                    check.get("acceptance_contract_digest", ""),
                ) if value
            ],
            "validation_run_id": check["validation_run_id"],
            "physical_run_id": check.get("physical_run_id", ""),
            "physical_evidence_digest": check.get("physical_evidence_digest", ""),
            "files": files,
            "reproduce": reproduce,
            "confirmation": "user-confirmed",
        }
        manifest_path = directory / "delivery-manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        archive = directory / f"{delivery_id}.tar.gz"
        with tarfile.open(archive, "w:gz") as bundle:
            bundle.add(manifest_path, arcname="delivery-manifest.json")
            script_info = tarfile.TarInfo("reproduce.sh")
            script_info.size = len(reproduce_script)
            script_info.mode = 0o755
            bundle.addfile(script_info, io.BytesIO(reproduce_script))
            for relative in relative_files:
                bundle.add(self.root / relative, arcname=relative, recursive=False)
        artifact_id = self._record(
            action="delivery-export",
            inputs=self._artifact_ids_for_digests(manifest["input_digests"]),
            outputs=[(
                "delivery", "delivery.manifest", 1, manifest,
                ArtifactContent(kind="blob"),
                {"confirmed": True, "uri": str(archive)},
            )],
        )[0]
        return {
            "delivery_id": delivery_id,
            "archive": str(archive),
            "manifest": manifest,
            "artifact_id": artifact_id,
        }

    def publish_ip(self, version: str, *, confirmed: bool) -> dict[str, Any]:
        """Publish a reviewed, independently qualified delivery as immutable IP."""
        if not confirmed:
            raise DesignDeliveryError("发布 IP 需要用户明确确认")
        if not isinstance(version, str) or not re.fullmatch(
            r"[0-9]+\.[0-9]+\.[0-9]+(?:[-+][A-Za-z0-9.-]+)?", version,
        ):
            raise DesignDeliveryError("IP 版本号必须是有效的语义版本")
        check = self.check_delivery()
        if not check["ready"]:
            raise DesignDeliveryError("IP 发布门禁未通过：" + "；".join(check["blockers"]))
        state = self.specs.state()
        document = state["document"]
        if document.get("design_kind") == "generic_module":
            return self._publish_generic_ip(version, check, state)
        name = str(document["name"])
        lock = self.library.read_lock()
        top_source = self.root / "integration" / "nebula_assembly.sv"
        if not top_source.is_file():
            raise DesignDeliveryError("装配顶层不存在")
        package_root = self.root / ".chip_nebula" / "published-ip" / name / version
        if not package_root.exists():
            (package_root / "rtl").mkdir(parents=True, exist_ok=False)
            (package_root / "tb").mkdir(parents=True, exist_ok=True)
            shutil.copy2(top_source, package_root / "rtl" / f"{name}.sv")
            template = (
                Path(chip_nebula.__file__).parent / "configs" / "ip"
                / "apb-gpio-regbank" / "tb" / "apb_gpio_regs_tb.sv"
            ).read_text(encoding="utf-8")
            testbench = template.replace("nebula_apb_gpio_regs", name).replace(
                f"{name} #(.GPIO_WIDTH(GPIO_WIDTH), .ADDR_WIDTH(12))",
                f"{name} #(.GPIO_WIDTH(GPIO_WIDTH))",
            )
            (package_root / "tb" / "apb_gpio_regs_tb.sv").write_text(
                testbench, encoding="utf-8"
            )
            dependencies: list[dict[str, Any]] = []
            seen: set[tuple[str, str]] = set()
            for entry in lock["packages"]:
                if entry.get("kind") == "dependency" or not entry.get("instance"):
                    continue
                key = (str(entry["package_id"]), str(entry["version"]))
                if key in seen:
                    continue
                seen.add(key)
                parameters = {
                    parameter: (
                        f"$parameters.{value['bind']}"
                        if isinstance(value, dict) and value.get("bind") else value
                    )
                    for parameter, value in entry.get("parameters", {}).items()
                }
                dependencies.append({
                    "package_id": entry["package_id"],
                    "version": entry["version"],
                    "content_digest": entry["content_digest"],
                    "parameters": parameters,
                })
            parameter_sets = _parameter_sets(document.get("parameters", []))
            interface = next(
                item for item in document.get("interfaces", [])
                if item.get("protocol") == "APB4"
            )
            manifest = {
                "schema_version": 1,
                "package": {
                    "vendor": "chip-nebula", "library": "generated",
                    "name": name, "version": version,
                },
                "source": {
                    "kind": "first_party",
                    "origin": f"Chip Nebula delivery {check['validation_run_id']}",
                    "license": "Proprietary",
                    "review": {
                        "status": "approved", "reviewed_by": "user delivery confirmation",
                    },
                },
                "top_module": name,
                "capabilities": ["apb-gpio-peripheral"],
                "parameters": document.get("parameters", []),
                "interfaces": [interface],
                "ports": document.get("ports", []),
                "files": [
                    {"path": f"rtl/{name}.sv", "type": "systemVerilogSource"},
                    {"path": "tb/apb_gpio_regs_tb.sv", "type": "systemVerilogTestbench"},
                ],
                "include_dirs": [], "defines": [], "dependencies": dependencies,
                "generator": {"kind": "apb-gpio-wrapper-v1"},
                "verification": {
                    "timeout": 120,
                    "parameter_sets": parameter_sets,
                    "commands": [
                        {
                            "name": "lint",
                            "command": (
                                f"verilator --lint-only -Wall -Wno-fatal --top-module {name} "
                                f"-GGPIO_WIDTH={{GPIO_WIDTH}} {{dependency_files}} rtl/{name}.sv"
                            ),
                        },
                        {
                            "name": "simulation",
                            "command": (
                                "mkdir -p build && iverilog -g2012 "
                                "-P apb_gpio_regs_tb.GPIO_WIDTH={GPIO_WIDTH} "
                                "-s apb_gpio_regs_tb -o build/ip_sim "
                                f"{{dependency_files}} rtl/{name}.sv tb/apb_gpio_regs_tb.sv "
                                "&& vvp build/ip_sim"
                            ),
                            "success_pattern": "IP_QUALIFICATION_PASSED",
                        },
                    ],
                },
                "delivery": {
                    "spec_digest": check["spec_digest"],
                    "lock_digest": check["lock_digest"],
                    "assembly_digest": check["assembly_digest"],
                    "validation_run_id": check["validation_run_id"],
                },
            }
            (package_root / "chip-nebula-ip.yaml").write_text(
                yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )
        else:
            existing = yaml.safe_load(
                (package_root / "chip-nebula-ip.yaml").read_text(encoding="utf-8")
            )
            delivery = existing.get("delivery", {}) if isinstance(existing, dict) else {}
            if any(delivery.get(key) != check[key] for key in (
                "spec_digest", "lock_digest", "assembly_digest", "validation_run_id",
            )):
                raise DesignDeliveryError(
                    f"发布版本 {version} 已存在且对应不同输入，请使用新版本号"
                )
        package = self.library.import_package(package_root, provenance={
            "kind": "delivery", "validation_run_id": check["validation_run_id"],
            "spec_digest": check["spec_digest"],
        })
        validation = self.validate_ip(package.package_id, package.version)
        if any(item.get("verdict") != "passed" for item in validation["records"]):
            raise DesignDeliveryError("发布包的独立参数化验证失败")
        return {
            "package": package.to_dict(evidence=self.library.evidence(package)),
            "package_path": str(package_root),
            "validation": validation,
            "artifact_id": self._record_package(package),
        }

    def _publish_generic_ip(
        self, version: str, check: Mapping[str, Any],
        state: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Package an independently accepted standalone plain-pin module.

        The frozen checker qualifies only its tested configuration. Until a
        parameter-aware checker contract exists, publishing a parameterized
        module would overstate its qualified configurations.
        """
        document = state["document"]
        if document.get("instances"):
            raise DesignDeliveryError("含 IP 实例的通用装配暂不能发布为独立 IP")
        if document.get("parameters"):
            raise DesignDeliveryError("通用模块发布暂只支持无参数的已验收配置")
        contract = checker_contract(state, self.root)
        acceptance = GenericAcceptanceWorkspace(self.root).state(state)
        if not acceptance.get("valid"):
            raise DesignDeliveryError("独立 checker 已失效，不能发布 IP")
        name = str(document["name"])
        source_files = [
            (contract["rtl"], "systemVerilogSource"),
            (contract["testbench"], "systemVerilogTestbench"),
            (acceptance["path"], "data"),
            ("spec/design.csir.yaml", "data"),
        ]
        package_root = self.root / ".chip_nebula" / "published-ip" / name / version
        delivery = {
            "spec_digest": check["spec_digest"],
            "rtl_sha256": check["rtl_sha256"],
            "acceptance_contract_digest": check["acceptance_contract_digest"],
            "validation_run_id": check["validation_run_id"],
        }
        if not package_root.exists():
            package_root.mkdir(parents=True, exist_ok=False)
            for relative, _kind in source_files:
                source = self.root / relative
                if source.is_symlink() or not source.is_file():
                    raise DesignDeliveryError(f"发布输入缺失或不是普通文件：{relative}")
                destination = package_root / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)
            rtl = shlex.quote(contract["rtl"])
            tb = shlex.quote(contract["testbench"])
            top = shlex.quote(name)
            tb_top = shlex.quote(contract["testbench_top"])
            check_script = (
                "import pathlib,sys; log=pathlib.Path('build/simulation.log').read_text(); "
                f"ids={contract['simulation_ids']!r}; "
                "ok=all(log.splitlines().count('NEBULA_CHECK '+item+' PASS') == 1 for item in ids); "
                "print('IP_QUALIFICATION_PASSED' if ok else 'IP_QUALIFICATION_FAILED'); "
                "sys.exit(0 if ok else 1)"
            )
            manifest = {
                "schema_version": 1,
                "package": {
                    "vendor": "chip-nebula", "library": "generated",
                    "name": name, "version": version,
                },
                "source": {
                    "kind": "first_party",
                    "origin": f"Chip Nebula delivery {check['validation_run_id']}",
                    "license": "Proprietary",
                    "review": {
                        "status": "approved",
                        "reviewed_by": "user delivery confirmation",
                    },
                },
                "top_module": name,
                "capabilities": ["generated-generic-module"],
                "parameters": [], "interfaces": [],
                "ports": document["ports"],
                "files": [
                    {"path": relative, "type": kind}
                    for relative, kind in source_files
                ],
                "include_dirs": [], "defines": [], "dependencies": [],
                "generator": {"kind": "generic-named-port-v1"},
                "verification": {
                    "timeout": 120,
                    "parameter_sets": [{}],
                    "commands": [
                        {
                            "name": "lint",
                            "command": (
                                "verilator --lint-only -Wall -Wno-fatal "
                                f"--top-module {top} {rtl}"
                            ),
                        },
                        {
                            "name": "simulation",
                            "command": (
                                "mkdir -p build && iverilog -g2012 "
                                f"-s {tb_top} -o build/ip_sim {rtl} {tb} "
                                "&& vvp build/ip_sim > build/simulation.log "
                                f"&& python3 -c {shlex.quote(check_script)}"
                            ),
                            "success_pattern": "IP_QUALIFICATION_PASSED",
                        },
                    ],
                },
                "delivery": delivery,
            }
            (package_root / "chip-nebula-ip.yaml").write_text(
                yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )
        else:
            manifest_path = package_root / "chip-nebula-ip.yaml"
            if not manifest_path.is_file():
                raise DesignDeliveryError("已有发布版本缺少 IP 清单，不能覆盖")
            existing = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
            if not isinstance(existing, dict) or existing.get("delivery") != delivery:
                raise DesignDeliveryError(
                    f"发布版本 {version} 已存在且对应不同输入，请使用新版本号"
                )
        package = self.library.import_package(package_root, provenance={
            "kind": "delivery", "validation_run_id": check["validation_run_id"],
            "spec_digest": check["spec_digest"],
        })
        validation = self.validate_ip(package.package_id, package.version)
        if any(item.get("verdict") != "passed" for item in validation["records"]):
            raise DesignDeliveryError("发布包的独立无参数验证失败")
        return {
            "package": package.to_dict(evidence=self.library.evidence(package)),
            "package_path": str(package_root),
            "validation": validation,
            "artifact_id": self._record_package(package),
        }

    def _delivery_files(self, run_id: str) -> list[str]:
        candidates = [
            "spec/design.csir.yaml", "ip/nebula.lock.json", "workbench.yaml",
            "Makefile", "verify_inputs.py",
        ]
        for directory in (
            "rtl", "tb", "spec", "integration", "generated", "ip/vendor", "vendor",
            "firmware", "constraints", "physical", "scripts",
        ):
            root = self.root / directory
            if root.is_dir():
                candidates.extend(
                    path.relative_to(self.root).as_posix()
                    for path in sorted(root.rglob("*"))
                    if path.is_file() and ".git" not in path.parts
                )
        run_root = self.root / ".chip_nebula" / "workbench" / "runs" / run_id
        for name in ("run.json", "run.log"):
            path = run_root / name
            if path.is_file():
                target = self.root / "evidence" / run_id / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, target)
                candidates.append(target.relative_to(self.root).as_posix())
        artifacts = run_root / "artifacts"
        if artifacts.is_dir():
            for path in sorted(artifacts.rglob("*")):
                if path.is_file():
                    target = self.root / "evidence" / run_id / "artifacts" / path.relative_to(artifacts)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(path, target)
                    candidates.append(target.relative_to(self.root).as_posix())
        return sorted(dict.fromkeys(
            item for item in candidates if (self.root / item).is_file()
        ))

    def _record_spec_artifacts(self, state: Mapping[str, Any]) -> list[str]:
        if not state.get("frozen"):
            raise DesignDeliveryError("specification is not frozen")
        existing = self._artifact_ids_for_digests(
            [str(state["spec_digest"])], exact_type="specification.csir",
        )
        if existing:
            return existing
        return self._record(
            action="spec-freeze",
            outputs=[
                (
                    "spec", "specification.csir", 1,
                    {
                        "spec_id": state["document"]["spec_id"],
                        "revision": state["document"]["revision"],
                        "status": "frozen", "spec_digest": state["spec_digest"],
                        "document": state["document"],
                    },
                    ArtifactContent(kind="files", paths=("spec/design.csir.yaml",)),
                    {"semantic_digest": state["spec_digest"]},
                ),
                (
                    "interface", "interface.contract", 2,
                    state["interface_contract"], ArtifactContent(kind="inline"),
                    {"semantic_digest": state["spec_digest"]},
                ),
                (
                    "acceptance", "acceptance.plan", 1,
                    state["acceptance_plan"], ArtifactContent(kind="inline"),
                    {"semantic_digest": state["spec_digest"]},
                ),
            ],
        )

    def _record_package(self, package: IPPackage) -> str:
        existing = self._artifact_ids_for_digests([package.content_digest], exact_type="ip.package")
        if existing:
            return existing[0]
        review = package.manifest["source"]["review"]["status"]
        return self._record(
            action="ip-import",
            outputs=[(
                "package", "ip.package", 1,
                {
                    "package_id": package.package_id, "version": package.version,
                    "content_digest": package.content_digest,
                    "top_module": package.manifest["top_module"],
                    "review_status": review, "manifest": package.manifest,
                },
                ArtifactContent(kind="blob"),
                {
                    "semantic_digest": package.content_digest,
                    "uri": str(package.root),
                },
            )],
        )[0]

    def _record(
        self,
        *,
        action: str,
        outputs: list[tuple[str, str, int, dict[str, Any], ArtifactContent, dict[str, Any]]],
        inputs: Iterable[str] = (),
    ) -> list[str]:
        suffix = uuid.uuid4().hex
        workflow_id = getattr(self._workflow_context, "id", "") or "design-delivery"
        task_id, attempt_id = (
            f"deterministic:{action}", f"evidence:{action}:{suffix}"
        )
        input_ids = tuple(dict.fromkeys(str(item) for item in inputs if item))
        artifacts: list[Artifact] = []
        with StaticTaskGraphStore(self.database) as store:
            for artifact_id in input_ids:
                if store.get_artifact(artifact_id) is None:
                    raise DesignDeliveryError(f"missing input Artifact {artifact_id}")
            for _name, artifact_type, version, payload, content, metadata in outputs:
                artifact = Artifact(
                    id=f"{action}-{uuid.uuid4().hex}", type=artifact_type,
                    schema_version=version,
                    producer=ArtifactProducer(
                        workflow_id, task_id, attempt_id,
                        f"deterministic-{action}", 1,
                    ),
                    content=content, payload=payload,
                    input_artifact_ids=input_ids,
                    metadata={"workflow_id": workflow_id, "action": action, **metadata},
                )
                artifacts.append(artifact)
            store.register_evidence_artifacts(artifacts)
        return [artifact.id for artifact in artifacts]

    def _artifact_ids_for_digests(
        self, digests: Iterable[str], *, exact_type: str = "",
    ) -> list[str]:
        wanted = {str(item) for item in digests if item}
        result: list[str] = []
        if not wanted or not self.database.is_file():
            return result
        with StaticTaskGraphStore(self.database) as store:
            for artifact in store.list_artifacts():
                if exact_type and artifact.type != exact_type:
                    continue
                values = {
                    str(artifact.payload.get("spec_digest", "")),
                    str(artifact.payload.get("content_digest", "")),
                    str(artifact.payload.get("lock_digest", "")),
                    str(artifact.payload.get("assembly_digest", "")),
                    str(artifact.payload.get("generation_digest", "")),
                    str(artifact.metadata.get("semantic_digest", "")),
                }
                if wanted & values:
                    result.append(artifact.id)
        return result

    def _mark_runs_stale(self) -> None:
        marker = self.root / ".chip_nebula" / "workbench" / "validation-state.json"
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(
            json.dumps({"stale": True}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}


def _parameter_sets(parameters: Iterable[Mapping[str, Any]]) -> list[dict[str, int]]:
    names: list[str] = []
    values: list[list[int]] = []
    for parameter in parameters:
        name = parameter.get("name")
        if not isinstance(name, str):
            continue
        allowed = parameter.get("allowed")
        if not isinstance(allowed, list) or not allowed:
            allowed = [parameter.get("default")]
        if any(type(value) is not int for value in allowed):
            raise DesignDeliveryError(f"参数 {name} 没有有限整数验证集合")
        names.append(name)
        values.append(list(allowed))
    return [dict(zip(names, combination)) for combination in itertools.product(*values)]
