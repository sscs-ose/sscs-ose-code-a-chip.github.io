from pathlib import Path
import json
import re
import operator
from chip_nebula.models.task_manifest import ExitCriterion
from chip_nebula.models.gate_report import GateReport

_NL = chr(10)

class MetricCheckGate:

    OPERATORS = {
        ">=": operator.ge,
        ">": operator.gt,
        "<=": operator.le,
        "<": operator.lt,
        "==": operator.eq,
        "!=": operator.ne,
    }

    @classmethod
    def check(cls, criterion: ExitCriterion, workspace_path: Path) -> GateReport:
        report = cls._evaluate(criterion, workspace_path)
        # Inject an Error-Class marker so the interpreter can route the
        # failure per the criterion's configured error_class (same
        # convention as regex_check / tool_check). Used only when the agent
        # did not self-classify — the interpreter prefers agent tags.
        if not report.passed and criterion.error_class:
            report.evidence = (report.evidence or "") + (
                _NL + f"Error-Class: {criterion.error_class}" + _NL
                + f"Error-Class-Reason: {criterion.type} failed for metric "
                  f"'{criterion.metric}' in {criterion.source}"
            )
        return report

    @classmethod
    def _evaluate(cls, criterion: ExitCriterion, workspace_path: Path) -> GateReport:
        passed = False
        evidence = ""
        suggestion = ""
        details = {}
        
        try:
            source_file = workspace_path / criterion.source
            if not source_file.exists():
                return GateReport(
                    level=criterion.level,
                    check_type=criterion.type,
                    passed=False,
                    evidence=f"Source file not found: {criterion.source}",
                    suggestion="Ensure previous steps generated the required metric file."
                )
                
            content = source_file.read_text()
            
            actual_values = cls._extract_metrics(content, criterion.metric)

            if not actual_values:
                return GateReport(
                    level=criterion.level,
                    check_type=criterion.type,
                    passed=False,
                    evidence=f"Could not extract metric '{criterion.metric}' from {criterion.source}",
                    suggestion="Check file format and metric name."
                )
                
            op_func = cls.OPERATORS.get(criterion.operator)
            if not op_func:
                return GateReport(
                    level=criterion.level,
                    check_type=criterion.type,
                    passed=False,
                    evidence=f"Unsupported operator: {criterion.operator}",
                    suggestion="Use >=, >, <=, <, ==, or !="
                )
                
            passed = all(op_func(value, criterion.threshold) for value in actual_values)
            actual_value = (
                min(actual_values)
                if criterion.operator in {">=", ">"}
                else max(actual_values)
                if criterion.operator in {"<=", "<"}
                else actual_values[0]
            )
            evidence = f"Metric {criterion.metric}: {actual_value} {criterion.operator} {criterion.threshold}"
            details = {
                "actual_value": actual_value,
                "actual_values": actual_values,
                "threshold": criterion.threshold,
            }
            
            if not passed:
                suggestion = f"Metric {criterion.metric} did not meet threshold. Expected {criterion.operator} {criterion.threshold}, got {actual_value}."

        except Exception as e:
            passed = False
            evidence = f"Exception evaluating metric: {str(e)}"
            suggestion = "Verify metric file exists and contains valid numeric data."
            
        return GateReport(
            level=criterion.level,
            check_type=criterion.type,
            passed=passed,
            evidence=evidence,
            details=details,
            suggestion=suggestion
        )

    @staticmethod
    def _extract_metric(content: str, metric_name: str) -> float | None:
        values = MetricCheckGate._extract_metrics(content, metric_name)
        return values[0] if values else None

    @staticmethod
    def _extract_metrics(content: str, metric_name: str) -> list[float]:
        """Read standard EDA metric IDs, dotted JSON paths, or legacy text.

        A result summary may contain the same metric for multiple corners.  A
        threshold Gate applies to every measured occurrence rather than
        silently selecting one favorable corner.
        """
        try:
            document = json.loads(content)
        except (TypeError, ValueError):
            document = None

        if isinstance(document, dict) and metric_name:
            metrics = document.get("metrics")
            if isinstance(metrics, list):
                values = [
                    item.get("value")
                    for item in metrics
                    if isinstance(item, dict)
                    and item.get("id") == metric_name
                    and item.get("status") == "measured"
                    and type(item.get("value")) in (int, float)
                ]
                if values:
                    return [float(value) for value in values]

            current = document
            for part in metric_name.split("."):
                if not isinstance(current, dict) or part not in current:
                    break
                current = current[part]
            else:
                if type(current) in (int, float):
                    return [float(current)]

        if not metric_name:
            match = re.search(r"-?\d+\.?\d*", content)
            if match:
                try:
                    return [float(match.group(0))]
                except ValueError:
                    return []
            return []

        # Require a separator (':' or '=' or whitespace) between the metric
        # name and its value. Crucially, the value pattern starts at the sign
        # character so a leading '-' is not swallowed by "skip" classes.
        pattern = re.compile(
            rf"\b{re.escape(metric_name)}\b\s*[:=]?\s*(-?\d+\.?\d*)",
            re.IGNORECASE,
        )
        match = pattern.search(content)
        if match:
            try:
                return [float(match.group(1))]
            except ValueError:
                return []

        return []
