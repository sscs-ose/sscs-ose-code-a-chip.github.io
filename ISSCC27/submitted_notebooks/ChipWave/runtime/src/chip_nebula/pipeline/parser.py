import json
import re
import yaml
from pathlib import Path
from typing import Optional

from chip_nebula.models.task_manifest import ExitCriterion


class PipelineConfig:
    def __init__(
        self,
        name: str,
        stages: dict[str, dict],
        version: str = "1.0",
        description: str = "",
        global_rollback_budget: Optional[int] = None,
        source_path: Optional[Path] = None,
    ):
        self.name = name
        self.version = version
        self.description = description
        self.stages = stages
        self.global_rollback_budget = global_rollback_budget
        self.source_path = source_path

    @classmethod
    def from_dict(cls, data: dict) -> "PipelineConfig":
        return cls(
            name=data["name"],
            version=data.get("version", "1.0"),
            description=data.get("description", ""),
            stages=data.get("stages", {}),
            global_rollback_budget=data.get("global_rollback_budget"),
            source_path=data.get("source_path"),
        )

    @classmethod
    def from_yaml(cls, path: str | Path) -> "PipelineConfig":
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Pipeline config not found: {path}")
        with open(path) as f:
            data = yaml.safe_load(f)
        if not data:
            raise ValueError(f"Empty pipeline config: {path}")
        config = cls.from_dict(data)
        config.source_path = path.resolve()
        return config

    def get_stage_names(self) -> list[str]:
        return list(self.stages.keys())

    def get_stage_dependencies(self, stage_name: str) -> list[str]:
        stage = self.stages.get(stage_name, {})
        return stage.get("depends_on", [])

    def get_exit_criteria(self, stage_name: str) -> list[ExitCriterion]:
        stage = self.stages.get(stage_name, {})
        criteria_list = stage.get("exit_criteria", [])
        result: list[ExitCriterion] = []
        for crit in criteria_list:
            result.append(ExitCriterion(
                type=crit.get("type", "tool_check"),
                level=crit.get("level", "L1"),
                command=crit.get("command", ""),
                expected=crit.get("expected", ""),
                timeout=crit.get("timeout", 120),
                metric=crit.get("metric", ""),
                operator=crit.get("operator", ">="),
                threshold=crit.get("threshold", 0.0),
                source=crit.get("source", ""),
                paths=crit.get("paths", []),
                min_files=crit.get("min_files", 0),
            ))
        return result

    def to_dict(self) -> dict:
        out = {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "stages": self.stages,
        }
        if self.global_rollback_budget is not None:
            out["global_rollback_budget"] = self.global_rollback_budget
        return out


class PipelineParser:
    # Keep in lockstep with ExitGate.GATE_REGISTRY (gates/exit_gate.py).
    _KNOWN_GATE_TYPES = {"tool_check", "metric_check", "coverage_check", "file_check", "regex_check"}
    # Each gate type's required (present + non-empty) YAML fields. Missing ones
    # surface as validate() issues so users don't learn about them mid-pipeline.
    _REQUIRED_BY_TYPE = {
        "tool_check": ("command",),
        "metric_check": ("source", "metric"),
        "coverage_check": ("source",),  # metric defaults to code_coverage
        "file_check": ("paths",),
        "regex_check": ("pattern",),
    }
    _LEVEL_RE = re.compile(r"^L\d+$")
    _VALID_OPERATORS = {">=", ">", "<=", "<", "==", "!="}

    def parse_file(self, path: str | Path) -> PipelineConfig:
        return PipelineConfig.from_yaml(path)

    def parse_string(self, yaml_str: str) -> PipelineConfig:
        data = yaml.safe_load(yaml_str)
        if not data:
            raise ValueError("Empty YAML string")
        return PipelineConfig.from_dict(data)

    def validate(self, config: PipelineConfig) -> list[str]:
        issues: list[str] = []
        stage_names = set(config.get_stage_names())

        for name in stage_names:
            deps = config.get_stage_dependencies(name)
            for dep in deps:
                if dep not in stage_names:
                    issues.append(f"Stage '{name}' depends on unknown stage '{dep}'")

        for name in stage_names:
            stage = config.stages[name]
            self._validate_stage(name, stage, stage_names, issues)

        return issues

    def _validate_stage(
        self, name: str, stage: dict, stage_names: set[str], issues: list[str],
    ) -> None:
        on_pass = stage.get("on_pass", "")
        if on_pass and on_pass != "done" and on_pass not in stage_names:
            issues.append(f"Stage '{name}' on_pass='{on_pass}' but '{on_pass}' is not defined")

        on_fail = stage.get("on_fail", {})
        if isinstance(on_fail, dict):
            target = on_fail.get("target", "")
            if target and target != name and target not in stage_names:
                issues.append(
                    f"Stage '{name}' on_fail.target='{target}' but '{target}' is not defined"
                )
            rules = on_fail.get("rules", [])
            if rules and not isinstance(rules, list):
                issues.append(f"Stage '{name}' on_fail.rules must be a list")
            else:
                for idx, rule in enumerate(rules or []):
                    if not isinstance(rule, dict):
                        issues.append(
                            f"Stage '{name}' on_fail.rules[{idx}] must be a mapping"
                        )
                        continue
                    route_to = rule.get("route_to", "")
                    if route_to and route_to not in stage_names:
                        issues.append(
                            f"Stage '{name}' on_fail.rules[{idx}].route_to='{route_to}' is not defined"
                        )
            target_map = on_fail.get("target_map", {})
            if target_map:
                if not isinstance(target_map, dict):
                    issues.append(f"Stage '{name}' on_fail.target_map must be a mapping")
                else:
                    for cls_name, tgt in target_map.items():
                        if tgt and tgt != name and tgt not in stage_names:
                            issues.append(
                                f"Stage '{name}' on_fail.target_map['{cls_name}']='{tgt}' is not defined"
                            )

        error_classes_override = stage.get("error_classes_override", {})
        if error_classes_override:
            if not isinstance(error_classes_override, dict):
                issues.append(f"Stage '{name}' error_classes_override must be a mapping")
            else:
                for cls_name, spec in error_classes_override.items():
                    if not isinstance(spec, dict):
                        issues.append(
                            f"Stage '{name}' error_classes_override['{cls_name}'] must be a mapping"
                        )
                        continue
                    route_to = spec.get("route_to", "")
                    if route_to and route_to not in ("self", name) and route_to not in stage_names:
                        issues.append(
                            f"Stage '{name}' error_classes_override['{cls_name}'].route_to='{route_to}' is not defined"
                        )

        receive_logs_from = stage.get("receive_logs_from", [])
        if isinstance(receive_logs_from, list):
            for upstream in receive_logs_from:
                if upstream not in stage_names:
                    issues.append(
                        f"Stage '{name}' receive_logs_from references unknown stage '{upstream}'"
                    )
        elif receive_logs_from:
            issues.append(
                f"Stage '{name}' receive_logs_from must be a list (got {receive_logs_from!r})"
            )

        max_iter = stage.get("max_iterations", None)
        if max_iter is not None:
            if not isinstance(max_iter, int) or isinstance(max_iter, bool) or max_iter < 1:
                issues.append(
                    f"Stage '{name}' max_iterations must be a positive integer (got {max_iter!r})"
                )

        timeout = stage.get("timeout", None)
        if timeout is not None:
            if not isinstance(timeout, (int, float)) or isinstance(timeout, bool) or timeout <= 0:
                issues.append(
                    f"Stage '{name}' timeout must be > 0 (got {timeout!r})"
                )

        if "agent" in stage and not stage["agent"]:
            issues.append(f"Stage '{name}' has empty 'agent'")

        criteria_list = stage.get("exit_criteria", [])
        if criteria_list and not isinstance(criteria_list, list):
            issues.append(f"Stage '{name}' exit_criteria must be a list")
            return

        for idx, crit in enumerate(criteria_list or []):
            self._validate_criterion(name, idx, crit, issues)

    def _validate_criterion(
        self, stage_name: str, idx: int, crit: object, issues: list[str],
    ) -> None:
        if not isinstance(crit, dict):
            issues.append(
                f"Stage '{stage_name}' exit_criteria[{idx}] must be a mapping"
            )
            return

        ctype = crit.get("type", "")
        if not ctype:
            issues.append(
                f"Stage '{stage_name}' exit_criteria[{idx}] missing 'type'"
            )
        elif ctype not in self._KNOWN_GATE_TYPES:
            issues.append(
                f"Stage '{stage_name}' exit_criteria[{idx}] unknown type '{ctype}' "
                f"(known: {sorted(self._KNOWN_GATE_TYPES)})"
            )

        level = crit.get("level", "L1")
        if not isinstance(level, str) or not self._LEVEL_RE.match(level):
            issues.append(
                f"Stage '{stage_name}' exit_criteria[{idx}].level must match 'L<int>' (got {level!r})"
            )

        timeout = crit.get("timeout", None)
        if timeout is not None:
            if not isinstance(timeout, (int, float)) or isinstance(timeout, bool) or timeout <= 0:
                issues.append(
                    f"Stage '{stage_name}' exit_criteria[{idx}].timeout must be > 0 (got {timeout!r})"
                )

        operator_str = crit.get("operator", None)
        if operator_str is not None and operator_str not in self._VALID_OPERATORS:
            issues.append(
                f"Stage '{stage_name}' exit_criteria[{idx}].operator '{operator_str}' not in "
                f"{sorted(self._VALID_OPERATORS)}"
            )

        threshold = crit.get("threshold", None)
        if threshold is not None and not isinstance(threshold, (int, float)):
            issues.append(
                f"Stage '{stage_name}' exit_criteria[{idx}].threshold must be numeric (got {threshold!r})"
            )

        min_files = crit.get("min_files", None)
        if min_files is not None:
            if not isinstance(min_files, int) or isinstance(min_files, bool) or min_files < 0:
                issues.append(
                    f"Stage '{stage_name}' exit_criteria[{idx}].min_files must be >= 0 (got {min_files!r})"
                )

        for required in self._REQUIRED_BY_TYPE.get(ctype, ()):
            value = crit.get(required, None)
            if value in (None, "", []):
                issues.append(
                    f"Stage '{stage_name}' exit_criteria[{idx}] type='{ctype}' missing required field '{required}'"
                )

        # regex_check needs a file target: either 'source' or 'paths'.
        if ctype == "regex_check":
            if not crit.get("source") and not crit.get("paths"):
                issues.append(
                    f"Stage '{stage_name}' exit_criteria[{idx}] type='regex_check' "
                    "must specify either 'source' or 'paths'"
                )
