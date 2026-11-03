"""Parameterized Gate templates materialized into self-contained Task bindings."""

from __future__ import annotations

import hashlib
import json
import shlex
import sys
from dataclasses import dataclass
from typing import Any, Callable, Mapping

from chip_nebula.models.task_manifest import ExitCriterion
class GateTemplateError(ValueError):
    pass


@dataclass(frozen=True)
class GateInstantiation:
    """Resolved template data used while freezing a static Task Gate.

    This is a compiler value, not a persisted runtime object.  Keeping it
    local avoids importing the retired mutable Task model merely to carry a
    resolved ExitCriterion between the template registry and Recipe compiler.
    """

    name: str
    template_id: str
    template_version: int
    parameters: Mapping[str, Any]
    resolved: Mapping[str, Any]
    template_digest: str


@dataclass(frozen=True)
class GateParameter:
    name: str
    value_type: str
    required: bool = False
    default: Any = None
    description: str = ""
    item_type: str = ""

    def document(self) -> dict[str, Any]:
        return {
            "name": self.name, "type": self.value_type,
            "required": self.required, "default": self.default,
            "description": self.description, "item_type": self.item_type,
        }


@dataclass(frozen=True)
class GateTemplate:
    id: str
    version: int
    title: str
    description: str
    parameters: tuple[GateParameter, ...]
    resolver: Callable[[Mapping[str, Any]], dict[str, Any]]

    @property
    def digest(self) -> str:
        document = {
            "id": self.id, "version": self.version, "title": self.title,
            "parameters": [item.document() for item in self.parameters],
        }
        encoded = json.dumps(document, sort_keys=True, separators=(",", ":")).encode()
        return "sha256:" + hashlib.sha256(encoded).hexdigest()

    def instantiate(
        self, *, name: str, parameters: Mapping[str, Any], on_failure: str
    ) -> GateInstantiation:
        if not name:
            raise GateTemplateError("Task Gate name must be non-empty")
        if on_failure not in {"retry", "agent_decides", "report"}:
            raise GateTemplateError("Gate on_failure must be retry, agent_decides or report")
        normalized = self._normalize(parameters)
        if self.id == "result-summary":
            from chip_nebula.taskgraph.result_summary import (
                ResultSummaryError, profile_metrics, safe_evidence_path,
            )
            try:
                safe_evidence_path(normalized["source"])
                normalized["required_metrics"] = sorted(set(
                    profile_metrics(normalized["profile"]) + normalized["required_metrics"]
                    + normalized["measured_metrics"]
                ))
            except ResultSummaryError as exc:
                raise GateTemplateError(str(exc)) from exc
        resolved = {
            **self.resolver(normalized),
            "level": normalized.get("level", "L1"),
            "error_class": normalized.get("error_class", ""),
        }
        criterion = ExitCriterion(**{**resolved, "on_failure": on_failure})
        return GateInstantiation(
            name=name, template_id=self.id, template_version=self.version,
            parameters=normalized, resolved=criterion.__dict__,
            template_digest=self.digest,
        )

    def _normalize(self, supplied: Mapping[str, Any]) -> dict[str, Any]:
        specs = {item.name: item for item in self.parameters}
        unknown = sorted(set(supplied) - set(specs))
        if unknown:
            raise GateTemplateError(
                f"Gate template {self.id} has unknown parameters: {', '.join(unknown)}"
            )
        result: dict[str, Any] = {}
        for name, spec in specs.items():
            value = supplied.get(name, spec.default)
            if spec.required and (value is None or value == "" or value == []):
                raise GateTemplateError(f"Gate template {self.id} requires parameter {name}")
            if value is None:
                continue
            _validate_parameter(spec, value, self.id)
            result[name] = value
        return result

    def document(self) -> dict[str, Any]:
        return {
            "id": self.id, "version": self.version, "title": self.title,
            "description": self.description, "digest": self.digest,
            "parameters": [item.document() for item in self.parameters],
        }


class GateTemplateRegistry:
    def __init__(self, templates: tuple[GateTemplate, ...]) -> None:
        self._templates = {(item.id, item.version): item for item in templates}

    def get(self, template_id: str, version: int = 1) -> GateTemplate:
        template = self._templates.get((template_id, version))
        if template is None:
            raise GateTemplateError(f"unknown Gate template: {template_id}@{version}")
        return template

    def describe(self) -> list[dict[str, Any]]:
        return [item.document() for item in sorted(self._templates.values(), key=lambda x: x.id)]


def default_gate_template_registry() -> GateTemplateRegistry:
    return GateTemplateRegistry((
        GateTemplate(
            "result-summary", 1, "EDA result summary",
            "Validate the versioned summary for a named output; measurement requirements are Task-bound.",
            _with_common_parameters((
                GateParameter("source", "string", True, description="Authorized summary JSON path"),
                GateParameter("output", "string", True, description="Task output name"),
                GateParameter("profile", "string", True, description="verification/synthesis/netlist/pnr/sta/gds/signoff/performance/power"),
                GateParameter("required_metrics", "list", False, [], item_type="string", description="Additional metric IDs; profile defaults are frozen into this Task"),
                GateParameter("measured_metrics", "list", False, [], item_type="string", description="IDs requiring actual measurements, not unavailable statuses"),
            )),
            _resolve_result_summary,
        ),
        GateTemplate(
            "file-check", 1, "File check",
            "Require files or glob patterns in the Task worktree.",
            _with_common_parameters(
                (
                GateParameter("paths", "list", True, item_type="string", description="Files or glob patterns"),
                GateParameter("min_files", "integer", False, 1, description="Minimum matching files"),
                ),
            ),
            lambda p: {"type": "file_check", "paths": p["paths"], "min_files": p["min_files"]},
        ),
        GateTemplate(
            "script-check", 1, "Script / command",
            "Execute a project script or command in the Task worktree.",
            _with_common_parameters(
                (
                GateParameter("script", "string", True, description="Script path or executable"),
                GateParameter("arguments", "list", False, [], item_type="string", description="Ordered arguments"),
                GateParameter("expected", "string", False, "", description="Expected output expression"),
                GateParameter("timeout", "integer", False, 120, description="Timeout in seconds"),
                ),
            ),
            _resolve_script,
        ),
        GateTemplate(
            "ut-regression", 1, "UT regression",
            "Run selected UT suite/cases with reproducible seed and timeout.",
            _with_common_parameters(
                (
                GateParameter("script", "string", False, "scripts/run_ut.sh", description="UT runner script"),
                GateParameter("suite", "string", False, "smoke", description="Suite name"),
                GateParameter("cases", "list", False, [], item_type="string", description="Case names"),
                GateParameter("seed", "integer", False, 1, description="Random seed"),
                GateParameter("expected", "string", False, "", description="Expected output expression"),
                GateParameter("timeout", "integer", False, 3600, description="Timeout in seconds"),
                ),
            ),
            _resolve_ut,
        ),
        GateTemplate(
            "metric-check", 1, "Metric threshold",
            "Extract a metric from a report and compare it with a threshold.",
            _with_common_parameters(_metric_parameters("wns", 0.0)),
            lambda p: {"type": "metric_check", **p},
        ),
        GateTemplate(
            "coverage-check", 1, "Coverage threshold",
            "Extract code coverage from a report and compare it with a threshold.",
            _with_common_parameters(_metric_parameters("code_coverage", 95.0)),
            lambda p: {"type": "coverage_check", **p},
        ),
        GateTemplate(
            "regex-check", 1, "Report regex",
            "Require a report file to contain, or not contain, a regular expression.",
            _with_common_parameters((
                GateParameter("source", "string", True, description="Report file path"),
                GateParameter("pattern", "string", True, description="Regular expression"),
                GateParameter("expect_match", "boolean", False, False, description="Require a match instead of forbidding one"),
            )),
            _resolve_regex,
        ),
        GateTemplate(
            "report-verdict", 1, "Engineering report verdict",
            "Require the report verdict to pass and reject failed or unsupported checks.",
            _with_common_parameters((
                GateParameter("source", "string", True, description="Structured report JSON path"),
            )),
            lambda p: {"type": "report_verdict", "source": p["source"]},
        ),
        GateTemplate(
            "post-route-export-consistency", 1, "Post-route export consistency",
            "Require ODB, STA netlist and SPEF to describe one timing design before layout publication.",
            _with_common_parameters((
                GateParameter(
                    "report", "string", False,
                    "reports/pnr/post_route_export_consistency.json",
                    description="Deterministic consistency report path",
                ),
                GateParameter(
                    "tolerance_ns", "number", False, 1e-6,
                    description="Maximum ODB versus exported STA slack delta",
                ),
            )),
            lambda p: {
                "type": "post_route_consistency",
                "source": p["report"],
                "threshold": p["tolerance_ns"],
            },
        ),
    ))


def _with_common_parameters(parameters: tuple[GateParameter, ...]) -> tuple[GateParameter, ...]:
    return (
        *parameters,
        GateParameter("level", "string", False, "L1", description="Gate severity level (L1 blocks later checks)"),
        GateParameter("error_class", "string", False, "", description="Error class reported when this Gate fails"),
    )


def _resolve_result_summary(parameters: Mapping[str, Any]) -> dict[str, Any]:
    arguments = ([sys.executable, "--result-summary-check"] if getattr(sys, "frozen", False)
                 else [sys.executable, "-m", "chip_nebula.taskgraph.result_summary"])
    arguments.extend([parameters["source"], "--profile", parameters["profile"]])
    for key in parameters["required_metrics"]:
        arguments.extend(["--required", key])
    for key in parameters["measured_metrics"]:
        arguments.extend(["--measured", key])
    return {"type": "tool_check", "command": shlex.join(arguments),
            "expected": "exit_code == 0", "timeout": 30}


def _metric_parameters(metric: str, threshold: float) -> tuple[GateParameter, ...]:
    return (
        GateParameter("source", "string", True, description="Report file path"),
        GateParameter("metric", "string", False, metric, description="Metric label"),
        GateParameter("operator", "string", False, ">=", description="Comparison operator"),
        GateParameter("threshold", "number", False, threshold, description="Required threshold"),
    )


def _resolve_script(parameters: Mapping[str, Any]) -> dict[str, Any]:
    command = shlex.join([
        *_runner_prefix(str(parameters["script"])),
        *map(str, parameters.get("arguments", [])),
    ])
    return {
        "type": "tool_check", "command": command,
        "expected": parameters.get("expected", ""), "timeout": parameters.get("timeout", 120),
    }


def _resolve_ut(parameters: Mapping[str, Any]) -> dict[str, Any]:
    arguments: list[str] = []
    if parameters.get("suite"):
        arguments.extend(["--suite", str(parameters["suite"])])
    for case in parameters.get("cases", []):
        arguments.extend(["--case", str(case)])
    arguments.extend(["--seed", str(parameters.get("seed", 1))])
    command = shlex.join([*_runner_prefix(str(parameters["script"])), *arguments])
    return {
        "type": "tool_check", "command": command,
        "expected": parameters.get("expected", ""), "timeout": parameters.get("timeout", 3600),
    }


def _resolve_regex(parameters: Mapping[str, Any]) -> dict[str, Any]:
    expect_match = bool(parameters.get("expect_match", False))
    return {
        "type": "regex_check",
        "source": parameters["source"],
        "pattern": parameters["pattern"],
        "must_match": expect_match,
        "must_not_match": not expect_match,
    }


def _runner_prefix(script: str) -> list[str]:
    """Resolve common project scripts without requiring executable bits."""
    parts = shlex.split(script)
    if len(parts) != 1:
        return parts
    if script.endswith(".sh"):
        return ["bash", script]
    if script.endswith(".py"):
        return ["python", script]
    return [script]


def _validate_parameter(spec: GateParameter, value: Any, template_id: str) -> None:
    valid = {
        "string": isinstance(value, str),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "number": isinstance(value, (int, float)) and not isinstance(value, bool),
        "boolean": isinstance(value, bool),
        "list": isinstance(value, (list, tuple)),
    }.get(spec.value_type, False)
    if not valid:
        raise GateTemplateError(
            f"Gate template {template_id} parameter {spec.name} must be {spec.value_type}"
        )
    if spec.value_type == "list" and spec.item_type == "string" and any(
        not isinstance(item, str) or not item for item in value
    ):
        raise GateTemplateError(
            f"Gate template {template_id} parameter {spec.name} must contain strings"
        )
