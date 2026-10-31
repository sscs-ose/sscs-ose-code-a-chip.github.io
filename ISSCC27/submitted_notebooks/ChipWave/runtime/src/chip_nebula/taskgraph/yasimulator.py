"""YASimulator v1: deterministic RTL regression orchestration and evidence."""

from __future__ import annotations

import glob
import hashlib
import json
import re
import shutil
import threading
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any, Iterable, Mapping

from chip_nebula.taskgraph.tool_executor import (
    DeterministicToolExecutor, ToolCommand, ToolExecutionResult,
)


_CHECK = re.compile(r"(?m)^NEBULA_CHECK[ \t]+([A-Za-z][A-Za-z0-9_.-]*)[ \t]+(PASS|FAIL)(?:[ \t]+([^\r\n]*))?")


@dataclass(frozen=True)
class RegressionCommand:
    name: str
    command: str
    acceptance_ids: tuple[str, ...]
    cwd: str = "."
    timeout: int = 900
    success_pattern: str = ""
    success_evidence: Mapping[str, Any] = field(default_factory=dict)
    environment: Mapping[str, str] = field(default_factory=dict)


class YASimulator:
    def run(
        self,
        workspace: Path,
        commands: Iterable[RegressionCommand],
        *,
        spec_digest: str,
        acceptance_plan: Mapping[str, Any],
        input_digests: Iterable[str],
        stop_event: threading.Event | None = None,
        process_callback=None,
        log_callback=None,
    ) -> dict[str, Any]:
        command_list = list(commands)
        result = DeterministicToolExecutor(
            stop_event=stop_event, process_callback=process_callback,
            log_callback=log_callback,
        ).execute(
            workspace,
            [
                ToolCommand(
                    item.name, item.command, item.cwd, item.timeout,
                    item.success_pattern, item.environment,
                )
                for item in command_list
            ],
        )
        result, evidence_records = self._apply_success_evidence(
            workspace, command_list, result
        )
        command_documents = []
        for index, item in enumerate(result.commands):
            document = asdict(item)
            if evidence_records[index]:
                document["success_evidence"] = evidence_records[index]
            command_documents.append(document)
        checks = self._checks(command_list, result, acceptance_plan)
        requirements = self._requirements(acceptance_plan, checks)
        if result.status in {"not_started", "launch_failed", "timeout", "stopped"}:
            verdict = result.status
        else:
            verdict = "passed" if (
                result.status == "succeeded" and result.verdict == "passed"
                and checks and all(item["verdict"] == "passed" for item in checks)
            ) else "failed"
        return {
            "schema_version": 1,
            "executor": "YASimulator",
            "status": result.status,
            "verdict": verdict,
            "spec_digest": spec_digest,
            "input_digests": list(dict.fromkeys(str(item) for item in input_digests if item)),
            "commands": command_documents,
            "tool_versions": result.tool_versions,
            "checks": checks,
            "requirements": requirements,
            "log": result.log,
            "evidence_digest": _digest({
                "spec_digest": spec_digest,
                "inputs": list(input_digests),
                "commands": command_documents,
                "checks": checks,
            }),
        }

    @staticmethod
    def _apply_success_evidence(
        workspace: Path, commands: list[RegressionCommand],
        result: ToolExecutionResult,
    ) -> tuple[ToolExecutionResult, list[dict[str, Any]]]:
        updated = []
        records: list[dict[str, Any]] = []
        for command, command_result in zip(commands, result.commands):
            criterion = dict(command.success_evidence or {})
            record: dict[str, Any] = {}
            if criterion and command_result.verdict == "passed":
                record = _evaluate_success_evidence(workspace, criterion)
                if record["verdict"] != "passed":
                    command_result = replace(
                        command_result, verdict="failed",
                        reason=str(record.get("reason", "success evidence did not match")),
                    )
            updated.append(command_result)
            records.append(record)
        # A failed earlier command prevents later commands from running, so
        # keep the record list aligned with the commands that actually ran.
        records = records[:len(updated)]
        status = result.status
        verdict = (
            "passed"
            if status == "succeeded" and updated
            and all(item.verdict == "passed" for item in updated)
            else (updated[-1].verdict if updated else result.verdict)
        )
        return replace(result, commands=tuple(updated), verdict=verdict), records

    @staticmethod
    def archive(
        workspace: Path, destination: Path, patterns: Iterable[str]
    ) -> list[dict[str, Any]]:
        destination.mkdir(parents=True, exist_ok=True)
        artifacts: list[dict[str, Any]] = []
        seen: set[str] = set()
        for pattern in patterns:
            for value in glob.glob(str(workspace / pattern), recursive=True):
                source = Path(value)
                if not source.is_file():
                    continue
                relative = source.relative_to(workspace).as_posix()
                if relative in seen:
                    continue
                seen.add(relative)
                target = destination / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
                artifacts.append({
                    "path": relative,
                    "size": source.stat().st_size,
                    "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                    "kind": "waveform" if source.suffix.lower() in {".vcd", ".fst"} else "report",
                })
        return artifacts

    @staticmethod
    def _checks(
        commands: list[RegressionCommand], result: ToolExecutionResult,
        acceptance_plan: Mapping[str, Any],
    ) -> list[dict[str, Any]]:
        declared = {
            item.get("id"): item
            for item in acceptance_plan.get("checks", []) if isinstance(item, dict)
        }
        observed: dict[str, dict[str, Any]] = {}
        # A shared command can fail after some checks have printed PASS and
        # before others have run. Only an explicit FAIL marker identifies the
        # failing check; the remaining checks cannot inherit that failure.
        priority = {"passed": 0, "not_run": 1, "inconclusive": 2, "failed": 3}
        for command, command_result in zip(commands, result.commands):
            bound = [
                check_id for check_id in dict.fromkeys(command.acceptance_ids)
                if check_id in declared and declared[check_id].get("status") != "planned"
            ]
            markers: dict[str, tuple[str, str]] = {}
            for match in _CHECK.finditer(command_result.log):
                check_id = match.group(1)
                if check_id not in bound:
                    continue
                marker = (match.group(2), (match.group(3) or "").strip())
                if marker[0] == "FAIL" or markers.get(check_id, ("", ""))[0] != "FAIL":
                    markers[check_id] = marker  # Any explicit FAIL dominates PASS.
            for check_id in bound:
                marker = markers.get(check_id)
                if marker and marker[0] == "FAIL":
                    verdict = "failed"
                    evidence = marker[1] or "checker reported an explicit FAIL marker"
                elif command_result.verdict == "passed":
                    if marker:
                        verdict, evidence = "passed", marker[1] or "checker reported PASS"
                    elif declared[check_id].get("evidence_marker_required") is True:
                        verdict, evidence = "not_run", "命令成功但未报告必需的独立检查标记"
                    else:
                        verdict = "passed"
                        evidence = "command completed and its success criterion matched"
                elif (
                    command_result.status == "succeeded"
                    and len(bound) == 1
                    and (command.success_evidence or command.success_pattern)
                ):
                    # A criterion bound to one check is direct evidence even
                    # when the process exits zero but its report is wrong.
                    verdict = "failed"
                    evidence = command_result.reason or "该检查的独立成功判据未满足"
                elif command_result.status in {"not_started", "launch_failed"}:
                    verdict, evidence = "not_run", command_result.reason or "命令未启动"
                else:
                    verdict = "inconclusive"
                    reason = command_result.reason or f"exit code {command_result.returncode}"
                    evidence = (
                        f"已观察到 PASS，但命令未通过（{reason}）；无法确认该检查通过"
                        if marker else
                        f"命令未通过（{reason}），未观察到该检查的独立失败标记；无法归因"
                    )
                item = {
                    "id": check_id, "verdict": verdict,
                    "command": command.name, "evidence": evidence,
                    "requirement_ids": list(declared[check_id].get("requirement_ids", [])),
                }
                previous = observed.get(check_id)
                if previous is None or priority[verdict] >= priority[previous["verdict"]]:
                    observed[check_id] = item
        return [
            observed.get(check_id, {
                "id": check_id, "verdict": "not_run", "command": "",
                "evidence": (
                    "该验收项仍在计划中，尚未实现独立检查"
                    if item.get("status") == "planned"
                    else "没有执行与该验收项绑定的检查"
                ),
                "requirement_ids": list(item.get("requirement_ids", [])),
            })
            for check_id, item in declared.items()
        ]

    @staticmethod
    def _requirements(
        plan: Mapping[str, Any], checks: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        by_requirement: dict[str, list[str]] = {
            str(req_id): [] for req_id in plan.get("requirement_ids", [])
        }
        for check in checks:
            for req_id in check.get("requirement_ids", []):
                by_requirement.setdefault(str(req_id), []).append(check["verdict"])
        descriptions = plan.get("requirement_descriptions", {})
        if not isinstance(descriptions, Mapping):
            descriptions = {}
        result = []
        for req_id, verdicts in sorted(by_requirement.items()):
            if verdicts and all(item == "passed" for item in verdicts):
                verdict = "passed"
            elif "failed" in verdicts:
                verdict = "failed"
            elif "inconclusive" in verdicts:
                verdict = "inconclusive"
            else:
                verdict = "not_run"
            item: dict[str, Any] = {"id": req_id, "verdict": verdict}
            description = descriptions.get(req_id)
            if isinstance(description, str) and description.strip():
                related = [
                    check for check in checks
                    if req_id in check.get("requirement_ids", [])
                ]
                item.update({
                    "description": description.strip(),
                    "check_ids": [str(check.get("id", "")) for check in related],
                    "evidence": "；".join(
                        str(check.get("evidence", "")).strip()
                        for check in related if str(check.get("evidence", "")).strip()
                    ),
                })
            result.append(item)
        return result


def _evaluate_success_evidence(
    workspace: Path, criterion: Mapping[str, Any],
) -> dict[str, Any]:
    kind = str(criterion.get("type", ""))
    relative = str(criterion.get("path", ""))
    base = workspace.resolve()
    path = (workspace / relative).resolve()
    record: dict[str, Any] = {"type": kind, "path": relative, "verdict": "failed"}
    if not relative or (path != base and base not in path.parents):
        record["reason"] = "success evidence path escapes workspace"
        return record
    if not path.is_file():
        record["reason"] = f"success evidence file was not produced: {relative}"
        return record
    if path.stat().st_size > 10_000_000:
        record["reason"] = "success evidence file is larger than 10 MB"
        return record
    data = path.read_bytes()
    record["sha256"] = hashlib.sha256(data).hexdigest()
    try:
        if kind == "file_regex":
            pattern = str(criterion.get("pattern", ""))
            matched = re.search(
                pattern, data.decode("utf-8", errors="replace"), re.MULTILINE
            ) is not None
            record.update({"pattern": pattern, "verdict": "passed" if matched else "failed"})
            if not matched:
                record["reason"] = "success evidence regex did not match"
            return record
        if kind == "json_value":
            pointer = str(criterion.get("pointer", ""))
            actual = _json_pointer(json.loads(data), pointer)
            expected = criterion.get("equals")
            matched = actual == expected
            record.update({
                "pointer": pointer, "expected": expected, "actual": actual,
                "verdict": "passed" if matched else "failed",
            })
            if not matched:
                record["reason"] = "success evidence JSON value did not match"
            return record
        record["reason"] = f"unsupported success evidence type: {kind}"
        return record
    except (json.JSONDecodeError, KeyError, IndexError, TypeError, ValueError, re.error) as exc:
        record["reason"] = f"success evidence could not be evaluated: {exc}"
        return record


def _json_pointer(document: Any, pointer: str) -> Any:
    if pointer == "":
        return document
    if not pointer.startswith("/"):
        raise ValueError("JSON pointer must be empty or start with /")
    current = document
    for raw in pointer[1:].split("/"):
        token = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(current, list):
            current = current[int(token)]
        elif isinstance(current, dict):
            current = current[token]
        else:
            raise TypeError(f"cannot resolve {token!r} below a scalar value")
    return current


def _digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
