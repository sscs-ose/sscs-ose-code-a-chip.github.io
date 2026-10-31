"""Schema catalog for immutable TaskGraph artifacts."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping


class ArtifactValidationError(ValueError):
    """Raised when an artifact does not satisfy its registered schema."""


@dataclass(frozen=True)
class ArtifactSchema:
    artifact_type: str
    version: int
    required_fields: Mapping[str, type | tuple[type, ...]] = field(default_factory=dict)
    validator: Callable[[Mapping[str, Any]], None] | None = None
    field_descriptions: Mapping[str, str] = field(default_factory=dict)
    validation_notes: tuple[str, ...] = ()
    carries_engineering_verdict: bool = False

    def validate(self, payload: Mapping[str, Any]) -> None:
        for name, expected in self.required_fields.items():
            if name not in payload:
                raise ArtifactValidationError(
                    f"{self.artifact_type}@{self.version} requires payload.{name}"
                )
            choices = expected if isinstance(expected, tuple) else (expected,)
            matches = any(
                isinstance(payload[name], Mapping) if choice is dict
                else isinstance(payload[name], choice)
                for choice in choices
            )
            if not matches:
                raise ArtifactValidationError(
                    f"payload.{name} must be {expected}, got {type(payload[name]).__name__}"
                )
        if self.validator is not None:
            self.validator(payload)


class ArtifactSchemaRegistry:
    def __init__(self) -> None:
        self._schemas: dict[tuple[str, int], ArtifactSchema] = {}

    def register(self, schema: ArtifactSchema) -> None:
        key = (schema.artifact_type, schema.version)
        if key in self._schemas:
            raise ArtifactValidationError(f"schema already registered: {key[0]}@{key[1]}")
        self._schemas[key] = schema

    def validate(self, artifact_type: str, version: int, payload: Mapping[str, Any]) -> None:
        schema = self._schemas.get((artifact_type, version))
        if schema is None:
            raise ArtifactValidationError(f"unknown artifact schema: {artifact_type}@{version}")
        schema.validate(payload)
        if "result_summary" in payload:
            from chip_nebula.taskgraph.result_summary import ResultSummaryError, validate_result_summary
            try:
                validate_result_summary(payload["result_summary"])
            except ResultSummaryError as exc:
                raise ArtifactValidationError(str(exc)) from exc

    def has(self, artifact_type: str, version: int) -> bool:
        return (artifact_type, version) in self._schemas

    def get(self, artifact_type: str, version: int) -> ArtifactSchema | None:
        return self._schemas.get((artifact_type, version))

    def describe(self) -> list[dict[str, Any]]:
        """Return JSON-friendly schema metadata for UI/form generation."""
        result = []
        for (artifact_type, version), schema in sorted(self._schemas.items()):
            fields = {}
            for name, expected in schema.required_fields.items():
                choices = expected if isinstance(expected, tuple) else (expected,)
                fields[name] = [item.__name__ for item in choices]
            result.append({
                "type": artifact_type, "schema_version": version,
                "required_fields": fields,
                "field_descriptions": dict(schema.field_descriptions),
                "validation_notes": list(schema.validation_notes),
                "carries_engineering_verdict": schema.carries_engineering_verdict,
            })
        return result


def default_schema_registry() -> ArtifactSchemaRegistry:
    registry = ArtifactSchemaRegistry()
    schemas = [
        ArtifactSchema(
            "rtl.snapshot", 1, {"module": str, "commit": str, "paths": (list, tuple)},
            field_descriptions={
                "module": "RTL 模块名（顶层模块）",
                "commit": "该快照对应的 Git commit",
                "paths": "快照包含的源码路径列表",
            },
        ),
        ArtifactSchema(
            "rtl.integration", 1, {"components": (list, tuple), "commit": str},
            field_descriptions={
                "components": "参与集成的组件 Artifact id 列表",
                "commit": "集成结果的 Git commit",
            },
        ),
        ArtifactSchema(
            "verification.environment", 1,
            {"rtl_artifact_id": str, "commit": str, "paths": (list, tuple)},
            field_descriptions={
                "rtl_artifact_id": "被测 RTL 的 Artifact id",
                "commit": "验证环境对应的 Git commit",
                "paths": "验证环境（testbench/flist/脚本）的路径列表",
            },
        ),
        ArtifactSchema(
            "verification.environment", 2,
            {
                "spec_artifact_id": str, "commit": str,
                "paths": (list, tuple),
            },
            field_descriptions={
                "spec_artifact_id": "冻结的 CSIR 规格 Artifact id",
                "commit": "独立验收环境对应的 Git commit",
                "paths": "冻结的 checker/testbench/runner 路径",
            },
        ),
        ArtifactSchema(
            "verification.environment", 3,
            {
                "commit": str, "paths": (list, tuple),
                "compatibility": dict,
            },
            field_descriptions={
                "commit": "可维护验证源码快照对应的 Git commit",
                "paths": "testbench、checker、filelist 与 runner 源码路径",
                "compatibility": "规格、验收计划与接口兼容摘要；不绑定具体 DUT 修订",
            },
        ),
        ArtifactSchema(
            "timing.context", 1,
            {"rtl_artifact_id": str, "commit": str, "paths": (list, tuple)},
            field_descriptions={
                "rtl_artifact_id": "被分析的 RTL Artifact id",
                "commit": "时序上下文对应的 Git commit",
                "paths": "约束/时序输入文件的路径列表",
            },
        ),
        ArtifactSchema(
            "interface.contract", 1, {"name": str, "contract_version": (int, str)},
            field_descriptions={
                "name": "接口契约名（通常对应契约文件）",
                "contract_version": "契约版本；用契约文件最后一次修改的 commit 或整数版本号",
            },
        ),
        ArtifactSchema(
            "interface.contract", 2,
            {
                "name": str, "contract_version": (int, str),
                "endpoints": (list, tuple),
            },
            field_descriptions={
                "endpoints": "带协议能力、角色、位宽和时钟复位绑定的接口端点",
            },
        ),
        ArtifactSchema(
            "verification.report", 1, {"subject": str, "verdict": str},
            _validate_verdict,
            field_descriptions={
                "subject": "被验证的对象（通常是 RTL Artifact id）",
                "verdict": "验证结论：passed 或 failed",
            },
            carries_engineering_verdict=True,
        ),
        ArtifactSchema(
            "verification.report", 2,
            {
                "subject": str, "verdict": str, "spec_digest": str,
                "requirements": (list, tuple), "checks": (list, tuple),
                "input_digests": (list, tuple), "tool_versions": dict,
            },
            _validate_verdict,
            field_descriptions={
                "requirements": "本次执行覆盖的需求 ID 与逐项判定",
                "input_digests": "规格、RTL、IP 锁和验收环境的完整输入摘要",
            },
            carries_engineering_verdict=True,
        ),
        ArtifactSchema(
            "verification.report", 3,
            {
                "subject": str, "verdict": str, "spec_digest": str,
                "requirements": (list, tuple), "checks": (list, tuple),
                "input_digests": (list, tuple), "tool_versions": dict,
                "commands": (list, tuple), "evidence_digest": str,
            },
            _validate_verification_report_v3,
            field_descriptions={
                "subject": "被验证设计的名称或稳定引用；必须是 JSON string，不能是对象",
                "verdict": "真实工程结论：passed 或 failed",
                "spec_digest": "本次验证所依据的冻结规格摘要字符串",
                "requirements": "逐需求的覆盖与结论列表",
                "checks": "逐检查项的执行状态、结果与证据引用列表",
                "input_digests": "非空字符串数组；每项只填写一个输入摘要字符串，不能填写对象",
                "tool_versions": "本次实际使用的工具及版本映射",
                "commands": "本次真实执行的 lint、simulation 等工具任务名",
                "evidence_digest": "evidence manifest 所列直接运行证据集合的 SHA-256 摘要",
            },
            validation_notes=(
                "commands must be a non-empty array and every item must be a non-empty string",
                "input_digests must be an array and every item must be a non-empty string",
                "when verdict is passed, evidence_digest must match sha256:<64 lowercase hex digits>",
            ),
            carries_engineering_verdict=True,
        ),
        ArtifactSchema(
            "specification.source", 1,
            {
                "source_name": str, "media_type": str,
                "content_digest": str, "content": str, "received_at": str,
            },
            field_descriptions={
                "content_digest": "Immutable digest of the exact user-supplied source text",
                "content": "Exact source text used by the frozen PREPARE Workflow",
            },
        ),
        ArtifactSchema(
            "specification.source-analysis", 1,
            {
                "source_artifact_id": str, "source_digest": str,
                "document_kind": str, "classification_summary": str,
                "requirements_ledger_path": str,
                "requirements_ledger_digest": str,
                "requirement_count": int,
            },
        ),
        ArtifactSchema(
            "specification.bundle", 1,
            {
                "source_artifact_id": str,
                "source_analysis_artifact_id": str,
                "design_artifact_id": str,
                "document_kind": str, "revision_digest": str,
                "design_document_path": str, "draft_path": str,
                "provenance_path": str, "questions_path": str,
                "contracts_path": str, "requirements_ledger_path": str,
                "file_digests": dict,
            },
        ),
        ArtifactSchema(
            "requirements.review.report", 1,
            {
                "subject": str, "verdict": str,
                "repair_target": str, "repair_summary": str,
                "requirements": (list, tuple),
                "discovered_requirements": (list, tuple),
                "issues": (list, tuple), "input_digests": (list, tuple),
            },
            _validate_verdict,
            carries_engineering_verdict=True,
        ),
        ArtifactSchema(
            "spec.compiler.report", 1,
            {
                "subject": str, "verdict": str, "failure_kind": str,
                "repair_summary": str, "spec_revision_id": str,
                "diagnostics": (list, tuple), "questions": (list, tuple),
                "candidates": (list, tuple), "counts": dict,
                "signoff": dict, "input_digests": (list, tuple),
            },
            _validate_verdict,
            carries_engineering_verdict=True,
        ),
        ArtifactSchema(
            "specification.baseline", 1,
            {
                "source_artifact_id": str, "bundle_artifact_id": str,
                "review_artifact_id": str, "compiler_report_artifact_id": str,
                "spec_revision_id": str, "status": str,
                "input_digests": (list, tuple),
            },
        ),
        ArtifactSchema(
            "specification.csir", 1,
            {
                "spec_id": str, "revision": int, "status": str,
                "spec_digest": str, "document": dict,
            },
        ),
        ArtifactSchema(
            "design.specification", 1,
            {
                "source_artifact_id": str,
                "source_analysis_artifact_id": str,
                "document_kind": str,
                "design_document_path": str,
                "design_digest": str,
                "requirement_ids": (list, tuple),
                "unresolved_items": (list, tuple),
            },
            field_descriptions={
                "source_artifact_id": "产生详细设计的原始需求 Artifact；桌面旧修订导入时可为空",
                "source_analysis_artifact_id": "需求/详细设计分类 Artifact；桌面旧修订导入时可为空",
                "document_kind": "原始输入分类：requirements 或 detailed_design",
                "design_document_path": "详细设计文档在冻结快照中的路径",
                "design_digest": "详细设计文档内容摘要",
                "requirement_ids": "详细设计已经展开并保持追踪的需求 ID",
                "unresolved_items": "签署时仍未闭合的设计项；可执行规格应为空",
            },
        ),
        ArtifactSchema(
            "acceptance.plan", 1,
            {
                "spec_digest": str, "checks": (list, tuple),
                "requirement_ids": (list, tuple),
            },
        ),
        ArtifactSchema(
            "design.dependencies", 1,
            {
                "spec_digest": str, "mode": str,
                "dependencies": (list, tuple), "lock_digest": str,
            },
            _validate_design_dependencies,
            field_descriptions={
                "mode": "self_contained（无外部设计依赖）或 locked（已固定外部 IP/宏/库）",
                "dependencies": "外部 IP、hard macro、memory macro、技术库及其版本/配置/摘要；可为空",
                "lock_digest": "规范化依赖清单摘要；空依赖也必须有稳定摘要",
            },
        ),
        ArtifactSchema(
            "implementation.constraints", 1,
            {
                "spec_digest": str, "platform": str, "corner": str,
                "clocks": (list, tuple), "io": dict, "power": dict,
                "commit": str, "paths": (list, tuple),
            },
            field_descriptions={
                "platform": "实现使用的固定 PDK / standard-cell platform",
                "corner": "综合、STA 与物理签核共用的分析 corner",
                "clocks": "时钟端口、周期、波形与不确定度",
                "io": "输入/输出 delay、drive、load 与例外约束",
                "power": "电源域、供电电压和功耗目标；无 UPF 时也须显式为空",
                "commit": "约束文件与可复现流程脚本所在 Git commit",
                "paths": "SDC、平台配置和实现脚本路径",
            },
        ),
        ArtifactSchema(
            "ip.package", 1,
            {
                "package_id": str, "version": str, "content_digest": str,
                "top_module": str, "review_status": str, "manifest": dict,
            },
        ),
        ArtifactSchema(
            "ip.lock", 1,
            {
                "spec_digest": str, "packages": (list, tuple),
                "lock_digest": str,
            },
        ),
        ArtifactSchema(
            "rtl.generated", 1,
            {
                "spec_digest": str, "acceptance_sources_digest": str,
                "generation_digest": str, "modules": (list, tuple),
                "file_hashes": dict,
            },
        ),
        ArtifactSchema(
            "rtl.assembly", 1,
            {
                "spec_digest": str, "lock_digest": str,
                "instances": (list, tuple), "connections": (list, tuple),
            },
        ),
        ArtifactSchema(
            "delivery.manifest", 1,
            {
                "spec_digest": str, "input_digests": (list, tuple),
                "files": (list, tuple), "verdict": str,
            },
            _validate_verdict,
            carries_engineering_verdict=True,
        ),
        ArtifactSchema(
            "design.review.report", 1,
            {
                "subject": str, "verdict": str, "spec_digest": str,
                "findings": (list, tuple), "input_digests": (list, tuple),
                "tool_versions": dict,
            },
            _validate_verdict,
            field_descriptions={
                "findings": "绑定 requirement、CSIR node 或代码位置的设计审查发现",
                "input_digests": "冻结规格、RTL、IP 锁等输入 Artifact 摘要",
            },
            carries_engineering_verdict=True,
        ),
        ArtifactSchema(
            "verification.audit.report", 1,
            {
                "subject": str, "verdict": str, "spec_digest": str,
                "requirements": (list, tuple), "gaps": (list, tuple),
                "input_digests": (list, tuple),
            },
            _validate_verdict,
            field_descriptions={
                "requirements": "逐需求审计计划、测试实现、oracle 与执行证据的闭合结果",
                "gaps": "漏测、跳测、不可判定、覆盖造假或绕开 DUT 缺陷的发现",
            },
            carries_engineering_verdict=True,
        ),
        ArtifactSchema(
            "synthesis.report", 1,
            {
                "subject": str, "verdict": str, "spec_digest": str,
                "metrics": dict, "warnings": (list, tuple),
                "unconstrained": (list, tuple), "input_digests": (list, tuple),
                "tool_versions": dict,
            },
            _validate_verdict,
            field_descriptions={
                "metrics": "cell/area/clock 等综合指标",
                "warnings": "逐条分类并处置的综合告警",
                "unconstrained": "未受约束时钟、端口或路径；非空通常必须 failed",
            },
            carries_engineering_verdict=True,
        ),
        ArtifactSchema(
            "design.release", 1,
            {
                "subject": str, "verdict": str, "spec_digest": str,
                "report_ids": (list, tuple), "input_digests": (list, tuple),
            },
            _validate_passed_release,
            field_descriptions={
                "subject": "获准进入综合的 rtl.integration Artifact id",
                "report_ids": "构成前端放行结论的完整报告 Artifact id",
            },
            carries_engineering_verdict=True,
        ),
        ArtifactSchema(
            "netlist.release", 1,
            {
                "subject": str, "verdict": str, "spec_digest": str,
                "synthesis_report_id": str, "timing_report_id": str,
                "design_release_id": str, "input_digests": (list, tuple),
            },
            _validate_passed_release,
            field_descriptions={
                "subject": "获准进入 PnR 的 netlist Artifact id",
                "synthesis_report_id": "通过的 synthesis.report",
                "timing_report_id": "通过的 pre-layout timing.report",
                "design_release_id": "仍然有效的前端 design.release",
            },
            carries_engineering_verdict=True,
        ),
        ArtifactSchema(
            "tapeout.release", 1,
            {
                "subject": str, "verdict": str, "spec_digest": str,
                "physical_report_id": str, "netlist_release_id": str,
                "input_digests": (list, tuple),
            },
            _validate_passed_release,
            field_descriptions={
                "subject": "获准交付流片的 GDS Artifact id",
                "physical_report_id": "覆盖该 GDS 且全部 STA/DRC/LVS 通过的 physical.report",
                "netlist_release_id": "仍然有效的 netlist.release",
            },
            carries_engineering_verdict=True,
        ),
        ArtifactSchema(
            "timing.report", 1, {"subject": str, "verdict": str},
            _validate_verdict,
            field_descriptions={
                "subject": "被分析的对象（通常是 RTL Artifact id）",
                "verdict": "时序结论：passed 或 failed",
            },
            carries_engineering_verdict=True,
        ),
        ArtifactSchema(
            "timing.report", 2,
            {
                "subject": str, "verdict": str, "spec_digest": str,
                "corner": str, "clocks": (list, tuple), "metrics": dict,
                "violations": (list, tuple), "unconstrained": (list, tuple),
                "input_digests": (list, tuple), "tool_versions": dict,
            },
            _validate_verdict,
            carries_engineering_verdict=True,
        ),
        ArtifactSchema(
            "performance.report", 1, {"subject": str, "verdict": str},
            _validate_verdict,
            field_descriptions={
                "subject": "被测对象（通常是 RTL Artifact id）",
                "verdict": "性能指标结论：passed 或 failed",
            },
            carries_engineering_verdict=True,
        ),
        ArtifactSchema(
            "performance.report", 2,
            {
                "subject": str, "verdict": str, "spec_digest": str,
                "workloads": (list, tuple), "metrics": dict, "budgets": dict,
                "input_digests": (list, tuple), "tool_versions": dict,
            },
            _validate_verdict,
            carries_engineering_verdict=True,
        ),
        ArtifactSchema(
            "power.report", 1, {"subject": str, "verdict": str},
            _validate_verdict,
            field_descriptions={
                "subject": "被测对象（通常是 RTL Artifact id）",
                "verdict": "功耗预算结论：passed 或 failed",
            },
            carries_engineering_verdict=True,
        ),
        ArtifactSchema(
            "power.report", 2,
            {
                "subject": str, "verdict": str, "spec_digest": str,
                "activity_source": str, "conditions": dict, "metrics": dict,
                "budgets": dict, "assumptions": (list, tuple),
                "input_digests": (list, tuple), "tool_versions": dict,
            },
            _validate_verdict,
            carries_engineering_verdict=True,
        ),
        ArtifactSchema(
            "netlist", 1, {"commit": str, "paths": (list, tuple)},
            field_descriptions={
                "commit": "综合网表对应的 Git commit",
                "paths": "网表文件路径列表",
            },
        ),
        ArtifactSchema(
            "layout", 1, {"commit": str, "paths": (list, tuple)},
            field_descriptions={
                "commit": "布局布线结果对应的 Git commit",
                "paths": "版图/数据库文件路径列表",
            },
        ),
        ArtifactSchema(
            "physical.implementation", 1,
            {
                "spec_digest": str, "source_netlist_id": str,
                "netlist_release_id": str, "commit": str,
                "paths": (list, tuple),
                "post_route_netlist_paths": (list, tuple),
                "parasitic_paths": (list, tuple),
            },
            _validate_physical_implementation,
            field_descriptions={
                "source_netlist_id": "PnR 输入的已放行综合网表 Artifact id",
                "netlist_release_id": "授权该网表进入 PnR 的 netlist.release Artifact id",
                "commit": "完整物理实现快照所在 Git commit",
                "paths": "版图数据库、post-route 网表、寄生参数、脚本与报告的完整路径集合",
                "post_route_netlist_paths": "CTS/route/ECO 后供 LVS 使用的固定网表路径",
                "parasitic_paths": "供 post-route STA 使用的 SPEF/SDF 等寄生参数路径",
            },
        ),
        ArtifactSchema(
            "gds", 1, {"commit": str, "paths": (list, tuple)},
            field_descriptions={
                "commit": "GDSII 导出对应的 Git commit",
                "paths": "GDS 文件路径列表",
            },
        ),
        ArtifactSchema(
            "physical.report", 1,
            {
                "subject": str, "verdict": str, "design": str,
                "platform": str, "stages": (list, tuple), "metrics": dict,
                "artifacts": (list, tuple), "input_digests": (list, tuple),
                "tool_versions": dict,
            },
            _validate_verdict,
            field_descriptions={
                "subject": "参与物理实现的固定 RTL 快照 Artifact id",
                "stages": "综合、布局布线、时序、DRC、LVS 等阶段结论",
                "artifacts": "已归档的网表、报告、数据库和 GDSII",
                "input_digests": "RTL、约束、工具与流程配置摘要",
            },
            carries_engineering_verdict=True,
        ),
        ArtifactSchema(
            "assistant.response", 1,
            {
                "workspace": str, "mode": str, "question": str,
                "answer": str, "context_digest": str,
                "evidence": (list, tuple),
            },
            field_descriptions={
                "workspace": "回答所属的桌面设计阶段",
                "context_digest": "只读回答使用的固定工程快照摘要",
                "evidence": "回答引用的工程文件、报告或 Artifact",
            },
        ),
        ArtifactSchema(
            "optimization.plan", 1,
            {
                "baseline_artifact_id": str, "objectives": (list, tuple),
                "hard_constraints": dict, "tunables": dict, "budgets": dict,
                "input_digests": (list, tuple),
            },
        ),
        ArtifactSchema(
            "design.candidate", 1,
            {
                "plan_artifact_id": str, "baseline_artifact_id": str,
                "parent_candidate_id": str, "commit": str,
                "configuration": dict, "changed_paths": (list, tuple),
                "status": str,
            },
        ),
        ArtifactSchema(
            "equivalence.report", 1,
            {
                "gold_artifact_id": str, "candidate_artifact_id": str,
                "verdict": str, "contract": dict,
                "partitions": (list, tuple), "input_digests": (list, tuple),
                "tool_versions": dict,
            },
            _validate_equivalence_verdict,
        ),
        ArtifactSchema(
            "ppa.report", 1,
            {
                "candidate_artifact_id": str, "measurement_level": str,
                "conditions": dict, "metrics": dict, "gates": dict,
                "input_digests": (list, tuple), "tool_versions": dict,
                "resources": dict,
            },
        ),
        ArtifactSchema(
            "optimization.promotion", 1,
            {
                "plan_digest": str, "selected_candidate_ids": (list, tuple),
                "ranked_candidate_ids": (list, tuple),
                "rejected_candidates": dict, "screen_digests": dict,
                "gate_artifact_ids": dict, "selection_rule": str,
            },
        ),
        ArtifactSchema(
            "optimization.selection", 1,
            {
                "plan_artifact_id": str, "candidate_artifact_id": str,
                "pareto_candidate_ids": (list, tuple), "reason": str,
                "baseline_digest": str,
            },
        ),
        ArtifactSchema(
            "decision.request", 1,
            {"subject": str, "title": str, "options": (list, tuple)},
            field_descriptions={
                "subject": "决策关联的对象（Artifact id；无关联时为产生者 task id）",
                "title": "决策标题（一行）",
                "options": "可选项列表：[{key, label, rationale?, consequences?}]",
            },
        ),
        ArtifactSchema(
            "decision.request", 2,
            {
                "subject": str,
                "revision_id": str,
                "items": (list, tuple),
                "input_digests": (list, tuple),
            },
            _validate_decision_request_v2,
            field_descriptions={
                "subject": "整批决策绑定的 immutable Artifact id",
                "revision_id": "决策所针对的不可变修订",
                "items": "完整问题批次；没有未决选择时允许空列表。每项含稳定 id、title 和至少两个 options；每个选项含项内唯一的非空 key、label，可附 rationale、consequences。交付表示请求批次已生成，省略 verdict，保留全部未答问题和编译诊断",
                "input_digests": "形成该批次的全部输入摘要",
            },
        ),
        ArtifactSchema(
            "failure.report", 1, {"subject": str, "class": str, "summary": str},
            field_descriptions={
                "subject": "失败所属的对象（Task / Artifact id）",
                "class": "失败分类（对应 Role 的 error_classes）",
                "summary": "失败现象的一句话总结",
            },
        ),
        ArtifactSchema(
            "repair.plan", 1,
            {"subject_failure": str, "actions": (list, tuple)},
            _validate_repair_plan,
            field_descriptions={
                "subject_failure": "针对哪个 failure.report（其 Artifact id）",
                "actions": "修复动作列表，每项含 action_id / role / target / instruction / expected_output",
            },
        ),
        ArtifactSchema(
            "human.decision", 1, {"subject": str, "decision": str},
            field_descriptions={
                "subject": "决策针对的对象（通常是 failure.report 的 Artifact id）",
                "decision": "人工决策内容",
            },
        ),
        ArtifactSchema(
            "human.decision", 2,
            {
                "request_artifact_id": str,
                "subject": str,
                "revision_id": str,
                "answers": (list, tuple),
                "complete": bool,
                "input_digests": (list, tuple),
            },
            _validate_human_decision_v2,
            field_descriptions={
                "request_artifact_id": "被完整回答的 decision.request@2 Artifact id",
                "answers": "按 issue_id 绑定的整批最终选择",
                "complete": "仅允许 true；不完整选择保存在 Human Task draft projection",
            },
        ),
    ]
    for schema in schemas:
        registry.register(schema)
    for path in sorted((Path(__file__).parents[1] / "configs" / "schemas").glob("*.yaml")):
        schema = load_schema_file(path)
        if not registry.has(schema.artifact_type, schema.version):
            registry.register(schema)
    return registry


# ---------------------------------------------------------------------------
# Project-defined artifact schemas (YAML files in .chip_nebula/schemas/)
# ---------------------------------------------------------------------------

_FIELD_TYPE_NAMES: dict[str, type] = {
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    "list": list,
    "dict": dict,
}

_SCHEMA_TYPE_PATTERN = re.compile(r"^[A-Za-z0-9_-]+(\.[A-Za-z0-9_-]+)*$")


def schema_from_document(document: Mapping[str, Any]) -> ArtifactSchema:
    """Build an ArtifactSchema from a YAML document.

    Format::

        type: power.report
        version: 1
        required_fields:
          subject: str          # single type
          paths: [str]          # any of these types (tuple)
          score:                # mapping style, with a human description
            type: [int, float]
            description: 评分含义……
        carries_engineering_verdict: true
        validation_notes:
          - verdict must be passed or failed
    """
    artifact_type = str(document.get("type") or "").strip()
    if not artifact_type or not _SCHEMA_TYPE_PATTERN.match(artifact_type):
        raise ArtifactValidationError(
            f"invalid artifact type name: {artifact_type!r} "
            "(letters, digits, '_', '-', segments joined by '.')"
        )
    try:
        version = int(document.get("version") or 0)
    except (TypeError, ValueError) as exc:
        raise ArtifactValidationError("schema version must be an integer") from exc
    if version < 1:
        raise ArtifactValidationError("schema version must be >= 1")
    carries_verdict = document.get("carries_engineering_verdict", False)
    if not isinstance(carries_verdict, bool):
        raise ArtifactValidationError("carries_engineering_verdict must be a boolean")
    raw_notes = document.get("validation_notes", ())
    if (
        not isinstance(raw_notes, (list, tuple))
        or any(not isinstance(note, str) or not note.strip() for note in raw_notes)
    ):
        raise ArtifactValidationError(
            "validation_notes must be a list of non-empty strings"
        )
    raw_fields = document.get("required_fields") or {}
    if not isinstance(raw_fields, Mapping):
        raise ArtifactValidationError("required_fields must be a mapping of field name -> type")
    fields: dict[str, type | tuple[type, ...]] = {}
    descriptions: dict[str, str] = {}
    for field_name, raw_type in raw_fields.items():
        if not isinstance(field_name, str) or not field_name.strip():
            raise ArtifactValidationError("required_fields keys must be non-empty strings")
        if isinstance(raw_type, Mapping):
            # mapping style: {type: str | [str, ...], description: str}
            spec = raw_type
            raw_type = spec.get("type")
            description = spec.get("description")
            if description is not None:
                if not isinstance(description, str):
                    raise ArtifactValidationError(
                        f"description for {field_name!r} must be a string"
                    )
                if description.strip():
                    descriptions[field_name.strip()] = description.strip()
        type_names = raw_type if isinstance(raw_type, (list, tuple)) else [raw_type]
        resolved: list[type] = []
        for name in type_names:
            python_type = _FIELD_TYPE_NAMES.get(str(name).strip())
            if python_type is None:
                raise ArtifactValidationError(
                    f"unknown field type {name!r} for {field_name!r}; "
                    f"supported: {sorted(_FIELD_TYPE_NAMES)}"
                )
            resolved.append(python_type)
            if python_type is list:
                # Artifact freezes JSON lists into immutable tuples before
                # validation; YAML schemas must accept that representation.
                resolved.append(tuple)
        fields[field_name.strip()] = resolved[0] if len(resolved) == 1 else tuple(resolved)
    return ArtifactSchema(
        artifact_type, version, fields,
        field_descriptions=descriptions,
        validation_notes=tuple(note.strip() for note in raw_notes),
        carries_engineering_verdict=carries_verdict,
    )


def load_schema_file(path: Path) -> ArtifactSchema:
    import yaml

    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(document, Mapping):
        raise ArtifactValidationError(f"schema file {path.name} must contain a mapping")
    return schema_from_document(document)


def load_schema_registry(project_root: Path | None = None) -> ArtifactSchemaRegistry:
    """Builtin schemas plus project-defined schemas from .chip_nebula/schemas/.

    A project file whose (type, version) collides with an already-registered
    schema is skipped — the dashboard save endpoint rejects such collisions
    before they land on disk, so a skip here only guards hand-edited files.
    """
    registry = default_schema_registry()
    if project_root is None:
        return registry
    schemas_dir = Path(project_root) / ".chip_nebula" / "schemas"
    if not schemas_dir.is_dir():
        return registry
    for path in sorted(schemas_dir.glob("*.yaml")):
        try:
            schema = load_schema_file(path)
        except (ArtifactValidationError, OSError):
            continue
        if not registry.has(schema.artifact_type, schema.version):
            registry.register(schema)
    return registry


def _validate_verdict(payload: Mapping[str, Any]) -> None:
    if payload["verdict"] not in {"passed", "failed"}:
        raise ArtifactValidationError("report verdict must be passed or failed")


def _validate_design_dependencies(payload: Mapping[str, Any]) -> None:
    if payload["mode"] not in {"self_contained", "locked"}:
        raise ArtifactValidationError(
            "design.dependencies mode must be self_contained or locked"
        )
    if payload["mode"] == "self_contained" and payload["dependencies"]:
        raise ArtifactValidationError(
            "self_contained design.dependencies must have no external dependencies"
        )
    if payload["mode"] == "locked" and not payload["dependencies"]:
        raise ArtifactValidationError(
            "locked design.dependencies needs at least one external dependency"
        )


def _validate_passed_release(payload: Mapping[str, Any]) -> None:
    if payload["verdict"] != "passed":
        raise ArtifactValidationError("release artifact may only be published with verdict=passed")
    if not payload["subject"]:
        raise ArtifactValidationError("release artifact needs a non-empty subject")
    if any(not isinstance(item, str) or not item for item in payload["input_digests"]):
        raise ArtifactValidationError("release input digests must be nonempty strings")


def _validate_physical_implementation(payload: Mapping[str, Any]) -> None:
    paths = {str(item) for item in payload.get("paths", ())}
    post_route = [str(item) for item in payload.get("post_route_netlist_paths", ())]
    parasitics = [str(item) for item in payload.get("parasitic_paths", ())]
    if not str(payload.get("source_netlist_id", "")):
        raise ArtifactValidationError("physical.implementation requires source_netlist_id")
    if not str(payload.get("netlist_release_id", "")):
        raise ArtifactValidationError("physical.implementation requires netlist_release_id")
    if not post_route:
        raise ArtifactValidationError(
            "physical.implementation requires a post-route netlist"
        )
    if not parasitics:
        raise ArtifactValidationError(
            "physical.implementation requires post-route parasitic data"
        )
    missing = [item for item in (*post_route, *parasitics) if item not in paths]
    if missing:
        raise ArtifactValidationError(
            "physical.implementation paths do not contain: " + ", ".join(missing)
        )


def _validate_verification_report_v3(payload: Mapping[str, Any]) -> None:
    _validate_verdict(payload)
    commands = payload["commands"]
    if not commands or any(not isinstance(item, str) or not item for item in commands):
        raise ArtifactValidationError("verification report needs executed command names")
    if any(not isinstance(item, str) or not item for item in payload["input_digests"]):
        raise ArtifactValidationError("verification input digests must be nonempty strings")
    if payload["verdict"] == "passed" and not re.fullmatch(
        r"sha256:[0-9a-f]{64}", payload["evidence_digest"]
    ):
        raise ArtifactValidationError("passed verification report needs archived evidence digest")


def _validate_equivalence_verdict(payload: Mapping[str, Any]) -> None:
    allowed = {
        "proved", "counterexample", "inconclusive", "timeout",
        "resource_exhausted", "unsupported",
    }
    if payload["verdict"] not in allowed:
        raise ArtifactValidationError(
            "equivalence verdict must be proved, counterexample, inconclusive, "
            "timeout, resource_exhausted or unsupported"
        )


def _validate_decision_request_v2(payload: Mapping[str, Any]) -> None:
    if not payload["subject"] or not payload["revision_id"]:
        raise ArtifactValidationError("decision.request@2 needs subject and revision_id")
    items = payload["items"]
    seen: set[str] = set()
    for item in items:
        if not isinstance(item, Mapping):
            raise ArtifactValidationError("decision.request@2 items must be objects")
        issue_id = str(item.get("id", "")).strip()
        title = str(item.get("title", "")).strip()
        if not issue_id or not title:
            raise ArtifactValidationError("each decision item needs non-empty id and title")
        if issue_id in seen:
            raise ArtifactValidationError(f"duplicate decision item id: {issue_id}")
        seen.add(issue_id)
        options = item.get("options")
        if not isinstance(options, (list, tuple)) or len(options) < 2:
            raise ArtifactValidationError(
                f"decision item {issue_id} needs at least two options"
            )
        option_keys: set[str] = set()
        for option in options:
            if not isinstance(option, Mapping):
                raise ArtifactValidationError(
                    f"decision item {issue_id} options must be objects"
                )
            key = str(option.get("key", "")).strip()
            if not key or key in option_keys:
                raise ArtifactValidationError(
                    f"decision item {issue_id} has missing or duplicate option key"
                )
            option_keys.add(key)
    if any(not isinstance(item, str) or not item for item in payload["input_digests"]):
        raise ArtifactValidationError(
            "decision.request@2 input_digests must be non-empty strings"
        )


def _validate_human_decision_v2(payload: Mapping[str, Any]) -> None:
    if payload["complete"] is not True:
        raise ArtifactValidationError("human.decision@2 must be a complete batch")
    if not payload["request_artifact_id"] or not payload["subject"] or not payload["revision_id"]:
        raise ArtifactValidationError(
            "human.decision@2 needs request_artifact_id, subject and revision_id"
        )
    answers = payload["answers"]
    if not answers:
        raise ArtifactValidationError("human.decision@2 needs at least one answer")
    seen: set[str] = set()
    for answer in answers:
        if not isinstance(answer, Mapping):
            raise ArtifactValidationError("human.decision@2 answers must be objects")
        issue_id = str(answer.get("issue_id", "")).strip()
        selected = str(answer.get("selected", "")).strip()
        if not issue_id or not selected or issue_id in seen:
            raise ArtifactValidationError(
                "human.decision@2 answers need unique issue_id and non-empty selected"
            )
        seen.add(issue_id)
    if any(not isinstance(item, str) or not item for item in payload["input_digests"]):
        raise ArtifactValidationError(
            "human.decision@2 input_digests must be non-empty strings"
        )


def _validate_repair_plan(payload: Mapping[str, Any]) -> None:
    seen: set[str] = set()
    required = ("action_id", "role", "target", "instruction", "expected_output")
    for index, action in enumerate(payload["actions"]):
        if not isinstance(action, Mapping):
            raise ArtifactValidationError(f"repair.plan.actions[{index}] must be a mapping")
        for field_name in required:
            value = action.get(field_name)
            if not isinstance(value, str) or not value:
                raise ArtifactValidationError(
                    f"repair.plan.actions[{index}].{field_name} must be a non-empty string"
                )
        if action["action_id"] in seen:
            raise ArtifactValidationError(
                f"duplicate repair action_id: {action['action_id']}"
            )
        seen.add(action["action_id"])
