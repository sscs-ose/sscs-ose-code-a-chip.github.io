from pathlib import Path

from chip_nebula.models.task_manifest import ExitCriterion
from chip_nebula.models.gate_report import GateReport

_NL = chr(10)


class FileCheckGate:

    @classmethod
    def check(cls, criterion: ExitCriterion, workspace_path: Path) -> GateReport:
        passed = True
        evidence_parts = []
        found_count = 0

        for pattern in criterion.paths:
            matches = list(workspace_path.glob(pattern))
            if matches:
                found_count += len(matches)
                evidence_parts.append(
                    f"Found {pattern}: {len(matches)} file(s)"
                )
            else:
                evidence_parts.append(f"NOT FOUND: {pattern}")

        if criterion.min_files > 0 and found_count < criterion.min_files:
            passed = False

        evidence = _NL.join(evidence_parts)
        suggestion = ""
        if not passed:
            suggestion = (
                f"Expected at least {criterion.min_files} file(s), "
                f"found {found_count}"
            )

        return GateReport(
            level=criterion.level,
            check_type=criterion.type,
            passed=passed,
            evidence=evidence,
            suggestion=suggestion,
        )
