"""Chip Nebula 内置 Compact SpecIR（.specir）编译器集成。

编译器源码随平台位于 :mod:`chip_nebula.csir`；语言前端和确定性检查
不调用 LLM，也不依赖开发机上的独立仓库、环境变量或额外 pip 包。
"""

from __future__ import annotations

import hashlib
import io
import json
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SKILL_NAME = "generate-csir-draft"


def csir_available() -> bool:
    try:
        from chip_nebula import csir  # noqa: F401

        return True
    except ImportError:
        return False


@dataclass(frozen=True, slots=True)
class _CompilerResult:
    returncode: int
    stdout: str
    stderr: str


def _run_compiler(arguments: list[str]) -> _CompilerResult:
    """在进程内调用随包分发的编译器 CLI。

    进程内执行同时适用于普通 Python 安装和 PyInstaller 冻结后端；
    后者的 ``sys.executable`` 不是可用 ``-m`` 重新启动的 Python 解释器。
    """
    try:
        from chip_nebula.csir.cli import main
    except ImportError as exc:
        return _CompilerResult(2, "", f"内置 Compact SpecIR 编译器不可用：{exc}")
    stdout = io.StringIO()
    stderr = io.StringIO()
    code = 0
    try:
        with redirect_stdout(stdout), redirect_stderr(stderr):
            main(arguments)
    except SystemExit as exc:
        code = int(exc.code) if isinstance(exc.code, int) else 1
    except Exception as exc:  # compiler boundary: surface a deterministic crash
        code = 2
        stderr.write(f"内置 Compact SpecIR 编译器异常：{exc}")
    return _CompilerResult(code, stdout.getvalue(), stderr.getvalue())


def _sidecar(source: Path, name: str) -> Path | None:
    """与 .specir 同目录的 sidecar（如 provenance.json），存在才返回。"""
    candidate = Path(source).parent / name
    return candidate if candidate.is_file() else None


# 待澄清类诊断前缀：hole / open conflict 是合法的"待用户对齐"标记。
# 它们以 error 严重级从编译器出来（会影响 signoff），但**不构成编译失败**——
# 草稿阶段文档没写清的设计细节就该保留为 hole/conflict，交给用户决策，
# 而不是逼 Agent 删除模块或编造默认值来换取"零 error"。
CLARIFICATION_CODE_PREFIXES = ("E-HOLE", "E-CONFLICT")


def is_clarification(diagnostic: dict[str, Any]) -> bool:
    """该诊断是否属于"待澄清"类（hole / open conflict）。"""
    return str(diagnostic.get("code", "")).startswith(CLARIFICATION_CODE_PREFIXES)


def blocking_diagnostics(diagnostics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return compiler errors that are not explicit design-alignment markers."""
    return [
        item for item in diagnostics
        if item.get("severity") == "error" and not is_clarification(item)
    ]


def _sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def specir_input_digests(source: Path) -> dict[str, str]:
    """Digest the exact source bundle consumed by check/readiness evaluation."""
    source = Path(source)
    result: dict[str, str] = {}
    for key, candidate in (
        ("source", source),
        ("provenance", source.parent / "provenance.json"),
        ("contracts", source.parent / "contracts.json"),
    ):
        if candidate.is_file():
            result[key] = _sha256(candidate)
    return result


def specir_revision_id(source: Path) -> str:
    """Stable ID for the complete human-facing specification revision."""
    source = Path(source)
    digests = specir_input_digests(source)
    for key, candidate in (
        ("design_document", source.parent / "design_doc.md"),
        ("questions", source.parent / "questions.json"),
    ):
        if candidate.is_file():
            digests[key] = _sha256(candidate)
    encoded = json.dumps(digests, sort_keys=True, separators=(",", ":")).encode()
    return "specir:" + hashlib.sha256(encoded).hexdigest()


def run_check(source: Path) -> dict[str, Any]:
    """对 .specir 源文件执行 `specir check --format json`，返回结构化诊断。

    同目录存在 provenance.json sidecar 时自动带上 --provenance：sidecar 与
    draft 的一致性（如 E-PROV-STALE-NODE）属于确定性检查的一部分。
    """
    source = Path(source)
    if not source.is_file():
        return {
            "ok": False,
            "failure_class": "tool_execution",
            "error": f"SpecIR 文件不存在：{source}",
            "diagnostics": [],
        }
    if not csir_available():
        return {
            "ok": False,
            "failure_class": "tool_execution",
            "error": "Chip Nebula 安装中缺少内置 Compact SpecIR 编译器",
            "diagnostics": [],
        }
    arguments = ["check", "--format", "json"]
    provenance = _sidecar(source, "provenance.json")
    if provenance is not None:
        arguments += ["--provenance", str(provenance)]
    contracts = _sidecar(source, "contracts.json")
    if contracts is not None:
        arguments += ["--contracts", str(contracts)]
    arguments.append(str(source))
    completed = _run_compiler(arguments)
    raw = completed.stdout.strip()
    diagnostics: list[dict[str, Any]] = []
    # 编译器完整跑完 = 进程正常结束（rc 0/1）且 JSON 输出可解析。
    # rc=2（E-PARSE 等，文本输出）或崩溃 => 没能完成检查，这才是失败。
    completed_run = completed.returncode in (0, 1)
    try:
        parsed = json.loads(raw) if raw else []
        if isinstance(parsed, list):
            diagnostics = [item for item in parsed if isinstance(item, dict)]
        else:
            completed_run = False
    except json.JSONDecodeError:
        completed_run = False
    failure_class = ""
    if not completed_run and not diagnostics:
        # E-PARSE/E-TOOL are deterministic rejections of the supplied CSIR
        # bundle and belong to its Author.  A compiler exception or malformed
        # compiler protocol is platform/tool failure and must not be routed to
        # an Author who cannot repair the executable.
        compiler_error = completed.stderr.strip() or raw
        input_rejected = (
            "Error-[E-PARSE]" in compiler_error
            or "Error-[E-TOOL]" in compiler_error
        )
        failure_class = "source_compile" if input_rejected else "tool_execution"
        diagnostics = [{
            "code": "E-CSIR-COMPILE" if input_rejected else "E-COMPILER-CRASH",
            "severity": "error",
            "message": compiler_error[:2000] or "specir check 失败",
            "source": None,
        }]
    pending = [item for item in diagnostics if is_clarification(item)]
    blocking = blocking_diagnostics(diagnostics)
    return {
        # ok 的语义：编译器完整跑完了对 draft 的检查。
        # 草稿该怎样就怎样——Error/Warning/Note 诊断是编译器对 draft 与文档
        # 现状的如实陈述（包括文档缺失的语义），不构成平台意义上的失败。
        "ok": completed_run,
        "failure_class": failure_class,
        "input_digests": specir_input_digests(source),
        "revision_id": specir_revision_id(source),
        "diagnostics": diagnostics,
        "pending_clarifications": pending,
        "blocking_diagnostics": blocking,
        "counts": {
            "errors": sum(1 for item in diagnostics if item.get("severity") == "error"),
            "blocking": len(blocking),
            "pending": len(pending),
            "warnings": sum(1 for item in diagnostics if item.get("severity") == "warning"),
            "notes": sum(1 for item in diagnostics if item.get("severity") == "note"),
        },
    }


def load_skill_text(project_root: Path | None = None) -> str:
    """加载 generate-csir-draft SKILL 内容。

    优先读工程里随平台资产安装的副本（.claude/skills/，与 Agent 本地发现一致），
    其次包内置 configs。
    """
    candidates: list[Path] = []
    if project_root:
        candidates.append(
            Path(project_root) / ".claude" / "skills" / SKILL_NAME / "SKILL.md"
        )
    import chip_nebula
    candidates.append(
        Path(chip_nebula.__file__).parent / "configs" / "skills" / SKILL_NAME / "SKILL.md"
    )
    for candidate in candidates:
        if candidate.is_file():
            try:
                return candidate.read_text(encoding="utf-8")[:16000]
            except OSError:
                continue
    return ""


def build_generation_instruction(document_text: str, project_root: Path) -> str:
    """构造 Spec Compiler 生成阶段的注入提示词。

    文档类型（需求描述 vs 详细设计文档）由 Agent 自行判断分流：
    需求先展开详细设计文档，详细设计文档直接生成 CSIR。
    """
    skill_text = load_skill_text(project_root)
    pipeline = (
        "先判断这份文档的类型：\n"
        "- 若偏**需求描述**（只说要做什么、缺少实现决策）：先把需求展开为**详细设计"
        "文档**，写入 spec/design_doc.md——模块划分、接口信号、状态机、时钟/复位、"
        "时序约束、异常与边界条件，逐项落到可验证的设计决策；需求没覆盖的点显式列出，"
        "不得编造；然后依据详细设计文档生成 Compact SpecIR 草稿；\n"
        "- 若已是**详细设计文档**（接口、状态、时序等实现决策齐全）：直接依据它生成 "
        "Compact SpecIR 草稿，写入 spec/draft.specir。\n"
        "最后，使用平台内置的 `specir check spec/draft.specir` 自查。\n"
        "- 自查只需抓**你自己编码造成**的问题：draft 必须能被完整解析和检查"
        "（E-PARSE 说明草稿本身写坏了，必须修），文档里明明写了却抄错/自相矛盾的"
        "也必须改；\n"
        "- 除此之外，凡是**根源在文档本身**（没写、写含糊、有歧义）的诊断，无论"
        "级别——error、warning 还是 note——都原样保留：draft 该怎样就怎样，"
        "这些诊断如实反映文档缺失的语义，**禁止**通过编造默认值、补 assume "
        "假设、删内容来掩饰；\n"
        "- 每个这样的保留项都必须对应一个决策块（NEBULA_DECISION）交给用户裁定，"
        "并写入 spec/questions.json；不能只把问题埋在 Markdown 清单里。\n"
    )
    return (
        "你是需求抽取 Agent。严格按下面的流水线执行：\n\n"
        + pipeline
        + "\n硬性规则：\n"
        "1. evidence-first：SpecIR 每个语义节点必须能追溯到文档原文；不确定处用显式"
        " hole（?name）或 conflict 标记，不得编造默认值；保留的 hole/conflict "
        "是交付物的一部分，不是待消除的错误；\n"
        "2. 只写 spec/ 目录内的文件，不修改 RTL/testbench/工程配置；\n"
        "3. 编译器诊断是确定性权威——但草稿的目标是**忠实反映文档**，不是看起来"
        "干净；文档缺什么就让它缺着，用决策块问用户；\n"
        "4. spec/questions.json 必须是 JSON 数组；每个未决项包含稳定 id、title、context、"
        "至少两个 options（key/label/rationale/consequences）、recommendation、blocking=true、"
        "status=open。每项同时输出一个同内容的 NEBULA_DECISION 块；没有未决项则写 []。\n"
        "5. 全部完成后只回复一句确认及所需的决策块。\n\n"
        + (
            "生成 SpecIR 的完整规范与门禁（必须逐条遵循）：\n" + skill_text + "\n\n"
            if skill_text else ""
        )
        + "用户提供的文档：\n" + document_text
    )


def run_signoff(source: Path) -> dict[str, Any]:
    """对 .specir 执行 `specir build --signoff` 复核（独立临时输出目录）。

    check 只证明 draft 自洽；signoff 额外把 W-CHOICE-NOT-PROVEN 等视为阻断，
    并给出 RTL lowering / 验证契约就绪度。返回 manifest 摘要，绝不写工程目录。
    """
    import tempfile

    source = Path(source)
    if not source.is_file():
        return {"signoff_passed": False, "error": f"SpecIR 文件不存在：{source}"}
    if not csir_available():
        return {
            "signoff_passed": False,
            "error": "Chip Nebula 安装中缺少内置 Compact SpecIR 编译器",
        }
    with tempfile.TemporaryDirectory(prefix="chip-nebula-signoff-") as temporary:
        arguments = ["build", "--out", temporary, "--signoff"]
        provenance = _sidecar(source, "provenance.json")
        if provenance is not None:
            arguments += ["--provenance", str(provenance)]
        contracts = _sidecar(source, "contracts.json")
        if contracts is not None:
            arguments += ["--contracts", str(contracts)]
        arguments.append(str(source))
        completed = _run_compiler(arguments)
        manifest_path = Path(temporary) / "manifest.json"
        manifest: dict[str, Any] = {}
        if manifest_path.is_file():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                manifest = {}
    return {
        "signoff_passed": completed.returncode == 0
        and bool(manifest.get("signoff_passed")),
        "rtl_lowering_ready": bool(manifest.get("rtl_lowering_ready")),
        "verification_contracts_ready": bool(
            manifest.get("verification_contracts_ready")
        ),
        "abstract_symbols": manifest.get("abstract_symbols", []),
        "source_sha256": str(manifest.get("source_sha256", "")),
        "input_digests": specir_input_digests(source),
        "revision_id": specir_revision_id(source),
        "detail": (completed.stderr.strip() or completed.stdout.strip())[:2000],
    }
