"""YAML configuration validator for Chip Nebula project configs.

Validates that all .yaml/.yml files under .chip_nebula/agents/ and
.chip_nebula/pipelines/ are syntactically valid and contain required
top-level fields.  Fails fast with clear file:line diagnostics so
that silent parse-fallback bugs (e.g. agent_cfg defaulting to {})
cannot hide broken configs again.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import NamedTuple, Optional

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore


class ValidationError(NamedTuple):
    path: Path
    line: int | None
    column: int | None
    message: str


def _scan_yaml_files(project_root: Path) -> list[Path]:
    files: list[Path] = []
    for subdir in ("agents", "pipelines", "roles", "recipes"):
        base = project_root / ".chip_nebula" / subdir
        if not base.exists():
            continue
        for path in sorted(base.rglob("*.yaml")):
            rel = path.relative_to(base)
            if any(part.startswith("_") for part in rel.parts):
                continue
            files.append(path)
    return files


def validate_yaml_syntax(
    path: Path, project_root: Optional[Path] = None
) -> list[ValidationError]:
    errors: list[ValidationError] = []
    if yaml is None:
        errors.append(
            ValidationError(
                path=path,
                line=None,
                column=None,
                message="PyYAML is not installed; cannot validate YAML syntax",
            )
        )
        return errors

    try:
        with open(path, encoding="utf-8") as fh:
            raw = fh.read()
    except Exception as exc:  # pragma: no cover
        errors.append(
            ValidationError(
                path=path, line=None, column=None, message=f"Cannot read file: {exc}"
            )
        )
        return errors

    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        mark = getattr(exc, "problem_mark", None)
        line = (mark.line + 1) if mark else None
        column = (mark.column + 1) if mark else None
        errors.append(
            ValidationError(
                path=path,
                line=line,
                column=column,
                message=f"YAML syntax error: {exc.problem if hasattr(exc, 'problem') else exc}",
            )
        )
        return errors

    kind = _config_kind(path, project_root)
    if kind == "agent":
        errors.extend(_check_agent_semantics(path, data))
    elif kind == "pipeline":
        errors.extend(_check_pipeline_semantics(path, data))
    elif kind == "role":
        errors.extend(_check_role_semantics(path, data))
    elif kind == "recipe":
        errors.extend(_check_recipe_semantics(path, data))

    return errors


def _config_kind(path: Path, project_root: Optional[Path]) -> Optional[str]:
    if project_root is None:
        return None
    for subdir, label in (
        ("agents", "agent"), ("pipelines", "pipeline"),
        ("roles", "role"), ("recipes", "recipe"),
    ):
        base = project_root / ".chip_nebula" / subdir
        try:
            path.relative_to(base)
            return label
        except ValueError:
            pass
    return None


def _check_agent_semantics(path: Path, data: object) -> list[ValidationError]:
    errors: list[ValidationError] = []
    if not isinstance(data, dict):
        errors.append(
            ValidationError(
                path=path,
                line=None,
                column=None,
                message="Agent config must be a YAML mapping (dict), not a list or scalar",
            )
        )
        return errors

    for key in ("type",):
        if key not in data:
            errors.append(
                ValidationError(
                    path=path,
                    line=None,
                    column=None,
                    message=f"Missing required field: '{key}'",
                )
            )

    timeout = data.get("timeout")
    if timeout is not None and not isinstance(timeout, (int, float)):
        errors.append(
            ValidationError(
                path=path,
                line=None,
                column=None,
                message=f"'timeout' must be a number, got {type(timeout).__name__}={timeout!r}",
            )
        )

    return errors


def _check_pipeline_semantics(path: Path, data: object) -> list[ValidationError]:
    errors: list[ValidationError] = []
    if not isinstance(data, dict):
        errors.append(
            ValidationError(
                path=path,
                line=None,
                column=None,
                message="Pipeline config must be a YAML mapping (dict), not a list or scalar",
            )
        )
        return errors

    for key in ("name", "stages"):
        if key not in data:
            errors.append(
                ValidationError(
                    path=path,
                    line=None,
                    column=None,
                    message=f"Missing required field: '{key}'",
                )
            )

    stages = data.get("stages")
    if stages is not None and not isinstance(stages, dict):
        errors.append(
            ValidationError(
                path=path,
                line=None,
                column=None,
                message=f"'stages' must be a mapping, got {type(stages).__name__}",
            )
        )

    return errors


def _check_role_semantics(path: Path, data: object) -> list[ValidationError]:
    if not isinstance(data, dict):
        return [ValidationError(path, None, None, "Role config must be a YAML mapping")]
    errors = []
    if not data.get("name"):
        errors.append(ValidationError(path, None, None, "Missing required field: 'name'"))
    version = data.get("version", 1)
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        errors.append(ValidationError(path, None, None, "'version' must be a positive integer"))
    return errors


def _check_recipe_semantics(path: Path, data: object) -> list[ValidationError]:
    if not isinstance(data, dict):
        return [ValidationError(path, None, None, "Recipe config must be a YAML mapping")]
    errors = []
    for key in ("name", "tasks"):
        if key not in data:
            errors.append(ValidationError(path, None, None, f"Missing required field: '{key}'"))
    if "tasks" in data and not isinstance(data["tasks"], dict):
        errors.append(ValidationError(path, None, None, "'tasks' must be a mapping"))
    if data.get("version", 2) != 2:
        errors.append(ValidationError(
            path, None, None,
            "TaskGraph Recipe must use version: 2 (fixed Tasks / continuing Attempts)",
        ))
    try:
        from chip_nebula.taskgraph.gate_templates import default_gate_template_registry

        registry = default_gate_template_registry()
        tasks = data.get("tasks", {}) if isinstance(data.get("tasks", {}), dict) else {}
        for task_key, task in tasks.items():
            if not isinstance(task, dict):
                continue
            gates = task.get("gates", [])
            if not isinstance(gates, list):
                raise ValueError(f"Task {task_key}.gates must be a list")
            for gate in gates:
                if not isinstance(gate, dict) or not gate.get("template"):
                    continue
                registry.get(
                    str(gate["template"]), int(gate.get("version", 1)),
                ).instantiate(
                    name=str(gate.get("name", "")),
                    parameters=gate.get("parameters", {}),
                    on_failure=(
                        "retry" if gate.get("on_failure", "retry") == "retry"
                        else "report"
                    ),
                )
    except Exception as exc:
        errors.append(ValidationError(path, None, None, str(exc)))
    return errors


def validate_project_yaml(project_root: Path) -> list[ValidationError]:
    all_errors: list[ValidationError] = []
    for path in _scan_yaml_files(project_root):
        all_errors.extend(validate_yaml_syntax(path, project_root=project_root))
    return all_errors


def print_validation_report(errors: list[ValidationError]) -> None:
    if not errors:
        return
    print("YAML validation FAILED", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    for err in errors:
        loc = f"{err.path}"
        if err.line is not None:
            loc += f":{err.line}"
            if err.column is not None:
                loc += f":{err.column}"
        print(f"  [{loc}] {err.message}", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    print(
        "Fix the errors above before running the pipeline. "
        "Silent YAML parse failures can hide critical config values (e.g. timeout).",
        file=sys.stderr,
    )
