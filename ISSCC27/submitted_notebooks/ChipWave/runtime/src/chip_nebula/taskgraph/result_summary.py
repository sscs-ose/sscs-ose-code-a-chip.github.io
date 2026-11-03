"""Versioned EDA summaries, explicit recipe gates and immutable publication.

Schema validity is independent of engineering verdict. A measured negative
slack is valid evidence; a recipe's engineering gates decide whether it passes.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from functools import lru_cache
from pathlib import Path, PurePosixPath
from typing import Any, Mapping


class ResultSummaryError(ValueError):
    pass


@lru_cache(maxsize=1)
def summary_contract() -> dict[str, Any]:
    path = Path(__file__).parents[1] / "configs/result_summaries/eda-result-summary.v1.json"
    return json.loads(path.read_text(encoding="utf-8"))


def profile_metrics(profile: str) -> list[str]:
    spec = summary_contract()["x-profiles"].get(profile)
    if spec is None:
        raise ResultSummaryError(f"unknown result summary profile: {profile}")
    return list(spec["required_metrics"])


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ResultSummaryError(f"{name} must be a nonempty string")
    return value


def _number(value: Any) -> bool:
    return type(value) in (int, float) and math.isfinite(value)


def safe_evidence_path(value: Any) -> str:
    path = _text(value, "evidence path")
    parsed = PurePosixPath(path)
    if parsed.is_absolute() or ".." in parsed.parts or "\\" in path or parsed.as_posix() != path:
        raise ResultSummaryError(f"evidence must be a canonical relative path: {path}")
    return path


def validate_result_summary(
    document: Any, *, profile: str = "", required_metrics: tuple[str, ...] | list[str] = (),
    measured_metrics: tuple[str, ...] | list[str] = (),
    workspace: Path | None = None, archived_paths: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    if not isinstance(document, Mapping):
        raise ResultSummaryError("result_summary must be an object")
    fields = {"schema_version", "stage", "status", "summary", "metrics"}
    if set(document) != fields:
        raise ResultSummaryError(f"result_summary fields must be {sorted(fields)}")
    if type(document["schema_version"]) is not int or document["schema_version"] != 1:
        raise ResultSummaryError("unsupported result_summary.schema_version; expected 1")
    stage = _text(document["stage"], "stage")
    if profile and stage != profile:
        raise ResultSummaryError(f"result_summary.stage must be {profile}, got {stage}")
    if not isinstance(document["status"], str) or document["status"] not in {"completed", "partial", "not_run"}:
        raise ResultSummaryError("invalid result_summary.status")
    _text(document["summary"], "summary")
    metrics = document["metrics"]
    if not isinstance(metrics, (list, tuple)):
        raise ResultSummaryError("metrics must be an array")
    catalog = summary_contract()["x-metrics"]
    seen: set[tuple[str, str]] = set()
    measured: set[str] = set()
    normalized = []
    for raw in metrics:
        if not isinstance(raw, Mapping):
            raise ResultSummaryError("metric must be an object")
        required = {"id", "label", "value", "unit", "status", "scope", "evidence"}
        if not required <= set(raw) or set(raw) - required - {"reason", "numerator", "denominator"}:
            raise ResultSummaryError(f"metric fields must include {sorted(required)}")
        metric_id = _text(raw["id"], "metric.id")
        if not re.fullmatch(r"[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+", metric_id):
            raise ResultSummaryError(f"invalid metric id: {metric_id}")
        spec = catalog.get(metric_id)
        if spec is None and not metric_id.startswith("custom."):
            raise ResultSummaryError(f"unknown metric {metric_id}; extensions must use custom.*")
        scope = _text(raw["scope"], "metric.scope")
        if (metric_id, scope) in seen:
            raise ResultSummaryError(f"duplicate metric id/scope: {metric_id}/{scope}")
        seen.add((metric_id, scope))
        _text(raw["label"], "metric.label")
        unit = _text(raw["unit"], "metric.unit")
        if spec and unit != spec["unit"]:
            raise ResultSummaryError(f"{metric_id} unit must be {spec['unit']}, got {unit}")
        status = raw["status"]
        if not isinstance(status, str) or status not in {"measured", "not_measured", "not_applicable", "unsupported"}:
            raise ResultSummaryError(f"invalid metric status: {status}")
        evidence = raw["evidence"]
        if not isinstance(evidence, (list, tuple)):
            raise ResultSummaryError("metric.evidence must be an array")
        paths = [safe_evidence_path(path) for path in evidence]
        if len(set(paths)) != len(paths):
            raise ResultSummaryError("duplicate evidence path")
        if "reason" in raw:
            _text(raw["reason"], "metric.reason")
        value = raw["value"]
        if status == "measured":
            if document["status"] == "not_run":
                raise ResultSummaryError("not_run summary cannot contain measured metrics")
            if not paths:
                raise ResultSummaryError(f"measured {metric_id} requires direct evidence")
            kind = spec["kind"] if spec else "scalar"
            valid = (
                (kind == "boolean" and type(value) is bool)
                or (kind == "string" and isinstance(value, str) and bool(value.strip()))
                or (kind in {"number", "nonnegative", "count", "percent"} and _number(value))
                or (kind == "scalar" and (_number(value) or isinstance(value, (str, bool))))
            )
            if not valid:
                raise ResultSummaryError(f"invalid value for {metric_id} ({kind})")
            if kind in {"count", "nonnegative", "percent"} and value < 0:
                raise ResultSummaryError(f"{metric_id} cannot be negative")
            if kind == "count" and int(value) != value:
                raise ResultSummaryError(f"{metric_id} must be an integer")
            if kind == "percent" and value > 100:
                raise ResultSummaryError(f"{metric_id} must be between 0 and 100")
            measured.add(metric_id)
        elif value is not None or not raw.get("reason"):
            raise ResultSummaryError(f"{metric_id}: unmeasured metrics require null value and reason")
        if ("numerator" in raw) != ("denominator" in raw):
            raise ResultSummaryError("numerator and denominator must be provided together")
        if "numerator" in raw:
            num, den = raw["numerator"], raw["denominator"]
            if not _number(num) or not _number(den) or num < 0 or den <= 0 or num > den:
                raise ResultSummaryError("invalid metric numerator/denominator")
            if status != "measured" or unit != "%" or abs(value - 100 * num / den) > 0.01:
                raise ResultSummaryError("coverage value disagrees with numerator/denominator")
        for path in paths:
            if workspace is not None:
                candidate = (workspace / path).resolve()
                if not candidate.is_relative_to(workspace.resolve()) or not candidate.is_file():
                    raise ResultSummaryError(f"evidence missing or outside workspace: {path}")
            if archived_paths is not None and path not in archived_paths:
                raise ResultSummaryError(f"evidence not archived in this Artifact: {path}")
        normalized.append({**raw, "evidence": paths})
    ids = {metric_id for metric_id, _ in seen}
    missing = set(required_metrics) - ids
    if missing:
        raise ResultSummaryError(f"missing required summary metrics: {', '.join(sorted(missing))}")
    unavailable = set(measured_metrics) - measured
    if unavailable:
        raise ResultSummaryError(f"required measurements unavailable: {', '.join(sorted(unavailable))}")
    return {**document, "metrics": normalized}


def read_result_summary(workspace: Path, source: str, **options: Any) -> dict[str, Any]:
    relative = safe_evidence_path(source)
    path = (workspace / relative).resolve()
    if not path.is_relative_to(workspace.resolve()):
        raise ResultSummaryError("result summary source escapes workspace")
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ResultSummaryError(f"cannot read result summary {source}: {exc}") from exc
    return validate_result_summary(document, workspace=workspace, **options)


def summary_gate_instructions(task: Any) -> list[str]:
    instructions = []
    for binding in task.gate_bindings:
        if binding.template_id != "result-summary":
            continue
        params = binding.parameters
        profile = params["profile"]
        outputs = {output.name: output.artifact_type for output in task.outputs}
        spec = summary_contract()["x-profiles"][profile]
        if outputs.get(params["output"]) not in spec["artifact_types"]:
            raise ResultSummaryError("result-summary Gate output/profile does not match Task outputs")
        instructions.append(
            f"Write EDA result summary v1 to {params['source']} for output {params['output']}. "
            f"Required shape: schema_version=1, stage={profile}, status=completed|partial|not_run, "
            "summary=<short execution summary>, metrics=<array>. Each metric must contain "
            "id,label,value,unit,status,scope,evidence (canonical relative file paths). "
            "scope must be one nonempty JSON string, never an object or array; encode the "
            "DUT, corner, clock/workload and analysis conditions in that string. "
            "status=measured requires real scalar value and evidence; not_measured, "
            "not_applicable or unsupported requires value=null and nonempty reason. "
            "Never invent measurements or use zero for unavailable data. Negative slack remains negative. "
            "Use a distinct scope string "
            "for distinct corners. Evidence files must belong to this output's authorized archived paths. "
            "For percentages, optionally include both numerator and denominator, consistent with value. "
            "Execution status does not replace engineering verdict. "
            "Required metric definitions: " + json.dumps({
                key: summary_contract()["x-metrics"].get(key, {"unit": "declare explicitly"})
                for key in params["required_metrics"]
            }, ensure_ascii=False)
            + ". Required measured IDs: " + json.dumps(params["measured_metrics"])
            + ". Extensions use custom.* IDs; do not rename standard IDs or units. "
            "The platform binds this file as payload.result_summary after validating the Gate."
        )
    return instructions


def task_output_summary(task: Any, output: str, workspace: Path, paths: tuple[str, ...]) -> dict | None:
    bindings = [binding for binding in task.gate_bindings
                if binding.template_id == "result-summary" and binding.parameters["output"] == output]
    if not bindings:
        return None
    if len(bindings) != 1:
        raise ResultSummaryError(f"multiple result summary Gates for output {output}")
    params = bindings[0].parameters
    if params["source"] not in paths:
        raise ResultSummaryError("result summary itself must be archived in its output Artifact")
    return read_result_summary(
        workspace, params["source"], profile=params["profile"],
        required_metrics=params["required_metrics"], measured_metrics=params["measured_metrics"],
        archived_paths=paths,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate an EDA result summary (no engineering verdict)")
    parser.add_argument("source")
    parser.add_argument("--profile", required=True)
    parser.add_argument("--required", action="append", default=[])
    parser.add_argument("--measured", action="append", default=[])
    args = parser.parse_args()
    try:
        read_result_summary(Path.cwd(), args.source, profile=args.profile,
                            required_metrics=args.required, measured_metrics=args.measured)
    except ResultSummaryError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print("EDA result summary v1: valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
