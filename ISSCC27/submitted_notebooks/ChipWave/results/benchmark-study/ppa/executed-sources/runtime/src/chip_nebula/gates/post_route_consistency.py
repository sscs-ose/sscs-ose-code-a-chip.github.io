"""Deterministic contract check for post-route STA exports."""

from __future__ import annotations

import json
import math
from pathlib import Path, PurePosixPath
from typing import Any

from chip_nebula.models.gate_report import GateReport
from chip_nebula.models.task_manifest import ExitCriterion


class PostRouteConsistencyGate:
    """Reject a layout whose independently checked STA export diverges from ODB."""

    @classmethod
    def check(cls, criterion: ExitCriterion, workspace_path: Path) -> GateReport:
        source = criterion.source or "reports/pnr/post_route_export_consistency.json"
        try:
            report_path = cls._workspace_file(workspace_path, source)
            document = json.loads(report_path.read_text(encoding="utf-8"))
            if not isinstance(document, dict):
                raise ValueError("report root must be an object")
            errors = cls._validate(document, workspace_path, float(criterion.threshold))
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            errors = [str(exc)]
            document = {}
        passed = not errors
        evidence = (
            "post-route export consistency passed"
            if passed else "post-route export consistency failed: " + "; ".join(errors)
        )
        if not passed and criterion.error_class:
            evidence += f"\nError-Class: {criterion.error_class}"
        return GateReport(
            level=criterion.level,
            check_type="post_route_consistency",
            passed=passed,
            evidence=evidence,
            details={
                "report": source,
                "tolerance_ns": float(criterion.threshold),
                "errors": errors,
                "status": document.get("status", "") if isinstance(document, dict) else "",
            },
            suggestion=(
                "Re-export a STA netlist that retains every Liberty-timed signal cell, "
                "then rerun independent netlist+SPEF STA against the final ODB."
                if not passed else ""
            ),
        )

    @classmethod
    def _validate(
        cls, document: dict[str, Any], workspace: Path, tolerance_ns: float,
    ) -> list[str]:
        errors: list[str] = []
        if document.get("schema_version") != 1:
            errors.append("schema_version must be 1")
        if document.get("status") != "passed":
            errors.append("status must be passed")
        if not math.isfinite(tolerance_ns) or tolerance_ns < 0:
            errors.append("Gate tolerance must be a non-negative finite number")
            tolerance_ns = 0.0

        for field in ("database_odb", "sta_netlist", "spef", "sdc"):
            value = document.get(field)
            if not isinstance(value, str) or not value:
                errors.append(f"{field} must be a workspace-relative path")
                continue
            try:
                path = cls._workspace_file(workspace, value)
                if path.stat().st_size <= 0:
                    errors.append(f"{field} is empty: {value}")
            except (OSError, ValueError) as exc:
                errors.append(f"{field}: {exc}")

        missing = document.get("missing_spef_binding_count")
        if isinstance(missing, bool) or not isinstance(missing, int) or missing != 0:
            errors.append("missing_spef_binding_count must be integer 0")

        for field in ("timing_instances", "antenna_instances"):
            counts = document.get(field)
            if not isinstance(counts, dict):
                errors.append(f"{field} must contain database and sta_netlist counts")
                continue
            database = counts.get("database")
            netlist = counts.get("sta_netlist")
            if any(isinstance(value, bool) or not isinstance(value, int) or value < 0
                   for value in (database, netlist)):
                errors.append(f"{field} counts must be non-negative integers")
            elif database != netlist:
                errors.append(
                    f"{field} mismatch: database={database}, sta_netlist={netlist}"
                )

        odb_hold = cls._finite_number(document, "database_hold_slack_ns", errors)
        sta_hold = cls._finite_number(document, "sta_hold_slack_ns", errors)
        path_delta = cls._finite_number(
            document, "path_slack_max_abs_delta_ns", errors, non_negative=True,
        )
        if odb_hold is not None and sta_hold is not None:
            delta = abs(odb_hold - sta_hold)
            if delta > tolerance_ns:
                errors.append(
                    f"hold slack delta {delta:.12g}ns exceeds {tolerance_ns:.12g}ns"
                )
        if path_delta is not None and path_delta > tolerance_ns:
            errors.append(
                f"path slack delta {path_delta:.12g}ns exceeds {tolerance_ns:.12g}ns"
            )

        evidence = document.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            errors.append("evidence must contain at least one raw tool log")
        else:
            for value in evidence:
                if not isinstance(value, str) or not value:
                    errors.append("evidence paths must be non-empty strings")
                    continue
                try:
                    path = cls._workspace_file(workspace, value)
                    if path.stat().st_size <= 0:
                        errors.append(f"evidence is empty: {value}")
                except (OSError, ValueError) as exc:
                    errors.append(f"evidence {value}: {exc}")
        return errors

    @staticmethod
    def _finite_number(
        document: dict[str, Any], field: str, errors: list[str], *, non_negative: bool = False,
    ) -> float | None:
        value = document.get(field)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            errors.append(f"{field} must be a finite number")
            return None
        number = float(value)
        if not math.isfinite(number) or (non_negative and number < 0):
            errors.append(
                f"{field} must be a {'non-negative ' if non_negative else ''}finite number"
            )
            return None
        return number

    @staticmethod
    def _workspace_file(workspace: Path, relative: str) -> Path:
        candidate = PurePosixPath(relative.replace("\\", "/"))
        if candidate.is_absolute() or ".." in candidate.parts or not candidate.parts:
            raise ValueError(f"unsafe path: {relative}")
        root = workspace.resolve()
        path = (root / Path(*candidate.parts)).resolve()
        if root not in path.parents:
            raise ValueError(f"path escapes workspace: {relative}")
        if not path.is_file():
            raise ValueError(f"file does not exist: {relative}")
        return path
