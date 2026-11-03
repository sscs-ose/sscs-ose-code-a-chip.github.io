"""Deterministic engineering-verdict Gate for structured report outputs."""

from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
from typing import Any

from chip_nebula.models.gate_report import GateReport
from chip_nebula.models.task_manifest import ExitCriterion


_FAILING_VALUES = frozenset({"fail", "failed", "error", "unsupported"})


class ReportVerdictGate:
    """Require a report and all of its declared checks to have passed."""

    @classmethod
    def check(cls, criterion: ExitCriterion, workspace_path: Path) -> GateReport:
        source = criterion.source
        failures: list[str] = []
        try:
            report_path = cls._workspace_file(workspace_path, source)
            document = json.loads(report_path.read_text(encoding="utf-8"))
            if not isinstance(document, dict):
                raise ValueError("report root must be an object")
            report = document.get("report")
            if isinstance(report, dict) and report.get("type") == "verification.report":
                environment = document.get("environment")
                if (
                    set(document) != {"environment", "report"}
                    or not isinstance(environment, dict)
                    or environment.get("type") != "verification.environment"
                    or environment.get("schema_version") != 3
                    or report.get("schema_version") != 3
                ):
                    raise ValueError("invalid or ambiguous verification output envelope")
                document = report
            verdict = cls._normalized(document.get("verdict"))
            if verdict != "passed":
                failures.append(f"top-level verdict must be passed, got {verdict or 'missing'}")
            for collection in ("checks", "requirements"):
                cls._collect_failures(collection, document.get(collection), failures)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            document = {}
            failures = [str(exc)]

        passed = not failures
        evidence = (
            "engineering report verdict passed"
            if passed else "engineering report verdict failed: " + "; ".join(failures)
        )
        if not passed and criterion.error_class:
            evidence += f"\nError-Class: {criterion.error_class}"
        return GateReport(
            level=criterion.level,
            check_type="report_verdict",
            passed=passed,
            evidence=evidence,
            details={
                "report": source,
                "verdict": document.get("verdict", "") if isinstance(document, dict) else "",
                "failures": failures,
            },
            suggestion=(
                "Fix the reported engineering failures and publish a new passed report."
                if not passed else ""
            ),
        )

    @classmethod
    def _collect_failures(
        cls, collection: str, value: Any, failures: list[str],
    ) -> None:
        if value is None:
            return
        if not isinstance(value, list):
            failures.append(f"{collection} must be a list")
            return
        for index, item in enumerate(value):
            if not isinstance(item, dict):
                failures.append(f"{collection}[{index}] must be an object")
                continue
            status = cls._normalized(item.get("verdict", item.get("status")))
            if status not in _FAILING_VALUES:
                continue
            identity = item.get("id") or item.get("name") or item.get("requirement_id") or index
            failures.append(f"{collection}[{identity}] is {status}")

    @staticmethod
    def _normalized(value: Any) -> str:
        return str(value).strip().lower() if value is not None else ""

    @staticmethod
    def _workspace_file(workspace: Path, relative: str) -> Path:
        candidate = PurePosixPath(str(relative).replace("\\", "/"))
        if candidate.is_absolute() or ".." in candidate.parts or not candidate.parts:
            raise ValueError(f"unsafe path: {relative}")
        root = workspace.resolve()
        path = (root / Path(*candidate.parts)).resolve()
        if root not in path.parents or not path.is_file():
            raise ValueError(f"report file does not exist: {relative}")
        return path
