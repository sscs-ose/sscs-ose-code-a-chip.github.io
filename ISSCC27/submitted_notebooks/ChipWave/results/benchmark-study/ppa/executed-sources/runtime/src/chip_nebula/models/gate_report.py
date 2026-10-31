from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class GateReport:
    level: str
    check_type: str
    passed: bool
    evidence: str = ""
    details: dict = field(default_factory=dict)
    suggestion: str = ""
    checked_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class GateResult:
    all_passed: bool
    reports: list[GateReport] = field(default_factory=list)

    @property
    def failed(self) -> list[GateReport]:
        return [r for r in self.reports if not r.passed]

    @property
    def passed(self) -> list[GateReport]:
        return [r for r in self.reports if r.passed]
