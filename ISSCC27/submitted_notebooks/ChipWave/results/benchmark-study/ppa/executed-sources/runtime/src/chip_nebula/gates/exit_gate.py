from pathlib import Path
from typing import Dict, Type, Any

from chip_nebula.models.task_manifest import ExitCriterion
from chip_nebula.models.gate_report import GateReport, GateResult
from chip_nebula.gates.tool_check import ToolCheckGate
from chip_nebula.gates.metric_check import MetricCheckGate
from chip_nebula.gates.coverage_check import CoverageCheckGate
from chip_nebula.gates.file_check import FileCheckGate
from chip_nebula.gates.regex_check import RegexCheckGate
from chip_nebula.gates.post_route_consistency import PostRouteConsistencyGate
from chip_nebula.gates.report_verdict import ReportVerdictGate

class ExitGate:

    GATE_REGISTRY: Dict[str, Type[Any]] = {
        "tool_check": ToolCheckGate,
        "metric_check": MetricCheckGate,
        "coverage_check": CoverageCheckGate,
        "file_check": FileCheckGate,
        "regex_check": RegexCheckGate,
        "post_route_consistency": PostRouteConsistencyGate,
        "report_verdict": ReportVerdictGate,
    }

    @staticmethod
    def _level_rank(level: str) -> int:
        """Convert 'L1', 'L2', 'L10' to int for correct ordering."""
        if not level:
            return 99
        s = level.strip().upper()
        if s.startswith("L"):
            s = s[1:]
        try:
            return int(s)
        except ValueError:
            return 99

    @classmethod
    def check(cls, exit_criteria: list[ExitCriterion], workspace_path: Path) -> GateResult:

        sorted_criteria = sorted(exit_criteria, key=lambda c: cls._level_rank(c.level))
        reports: list[GateReport] = []
        all_passed = True

        for criterion in sorted_criteria:
            gate_class = cls.GATE_REGISTRY.get(criterion.type)
            if not gate_class:
                report = GateReport(
                    level=criterion.level,
                    check_type=criterion.type,
                    passed=False,
                    evidence=f"Unknown criterion type: {criterion.type}",
                    suggestion="Ensure criterion type is one of: tool_check, metric_check, coverage_check, file_check"
                )
                reports.append(report)
                all_passed = False
                if cls._level_rank(criterion.level) <= 1:
                    break
                continue

            report = gate_class.check(criterion, workspace_path)
            reports.append(report)

            if not report.passed:
                all_passed = False
                if cls._level_rank(criterion.level) <= 1:
                    break

        return GateResult(
            all_passed=all_passed,
            reports=reports
        )
