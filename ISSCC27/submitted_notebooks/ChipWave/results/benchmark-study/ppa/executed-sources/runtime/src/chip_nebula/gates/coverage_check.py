from pathlib import Path
from chip_nebula.models.task_manifest import ExitCriterion
from chip_nebula.models.gate_report import GateReport
from chip_nebula.gates.metric_check import MetricCheckGate

class CoverageCheckGate(MetricCheckGate):
    
    @classmethod
    def check(cls, criterion: ExitCriterion, workspace_path: Path) -> GateReport:
        if not criterion.metric:
            criterion.metric = "code_coverage"
        if not criterion.operator:
            criterion.operator = ">="
        if criterion.threshold == 0.0:
            criterion.threshold = 95.0
        return super().check(criterion, workspace_path)
