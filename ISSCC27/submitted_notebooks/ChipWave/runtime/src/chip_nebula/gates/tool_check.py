import os
import re
import subprocess
import sys
from pathlib import Path

from chip_nebula.models.task_manifest import ExitCriterion
from chip_nebula.models.gate_report import GateReport

_NL = chr(10)


class ToolCheckGate:

    @staticmethod
    def _execution_environment() -> dict[str, str]:
        """Run Python-backed Gates with the platform's own interpreter first.

        Desktop launches inherit a minimal macOS PATH where ``python3`` can
        resolve to CommandLineTools even though Chip Nebula itself is running
        from its managed Python environment.  A frozen Task may legitimately
        contain a portable ``python3 -m ...`` command, so executable resolution
        is a runtime concern rather than a reason to mutate that Task.
        """
        environment = os.environ.copy()
        python_bin = str(Path(sys.executable).resolve().parent)
        current_path = environment.get("PATH", "")
        environment["PATH"] = (
            python_bin if not current_path
            else python_bin + os.pathsep + current_path
        )
        return environment

    @classmethod
    def check(cls, criterion: ExitCriterion, workspace_path: Path) -> GateReport:
        try:
            result = subprocess.run(
                criterion.command,
                shell=True,
                cwd=workspace_path,
                env=cls._execution_environment(),
                capture_output=True,
                text=True,
                timeout=criterion.timeout,
            )
            stdout_str = result.stdout or ""
            stderr_str = result.stderr or ""
            evidence = (
                "STDOUT:" + _NL + stdout_str[:500]
                + _NL + "STDERR:" + _NL + stderr_str[:500]
            )

            passed = cls._evaluate_expected(
                criterion.expected, result.returncode, stdout_str, stderr_str
            )

            suggestion = ""
            if not passed:
                suggestion = f"Command failed: {criterion.command}" + _NL
                if stderr_str:
                    suggestion += f"Error output: {stderr_str[:300]}"
                # Inject an Error-Class marker so the interpreter can route
                # the failure per the criterion's configured error_class
                # (same convention as regex_check). Used only when the agent
                # did not self-classify — the interpreter prefers agent tags.
                if criterion.error_class:
                    evidence += _NL + f"Error-Class: {criterion.error_class}" + _NL
                    evidence += (
                        f"Error-Class-Reason: tool_check failed: {criterion.command}"
                    )

            return GateReport(
                level=criterion.level,
                check_type=criterion.type,
                passed=passed,
                evidence=evidence,
                suggestion=suggestion,
            )

        except subprocess.TimeoutExpired:
            return GateReport(
                level=criterion.level,
                check_type=criterion.type,
                passed=False,
                evidence=f"Timed out after {criterion.timeout}s",
                suggestion="Increase timeout or optimize the command",
            )
        except Exception as exc:
            return GateReport(
                level=criterion.level,
                check_type=criterion.type,
                passed=False,
                evidence=f"Error: {exc}",
                suggestion="Verify command syntax and environment",
            )

    @staticmethod
    def _evaluate_expected(
        expected: str, returncode: int, stdout: str, stderr: str
    ) -> bool:
        if not expected:
            return returncode == 0

        expected = expected.strip()
        combined = stdout + " " + stderr

        if " AND " in expected:
            sub_checks = [c.strip() for c in expected.split(" AND ")]
            return all(
                ToolCheckGate._evaluate_single(s, returncode, stdout, stderr)
                for s in sub_checks
            )

        return ToolCheckGate._evaluate_single(expected, returncode, stdout, stderr)

    @staticmethod
    def _evaluate_single(
        expected: str, returncode: int, stdout: str, stderr: str
    ) -> bool:
        combined = stdout + " " + stderr

        exit_match = re.match(
            r"exit_code\s*(==|!=|>|<|>=|<=)\s*(-?\d+)", expected
        )
        if exit_match:
            op, val = exit_match.groups()
            val = int(val)
            comparisons = {
                "==": returncode == val,
                "!=": returncode != val,
                ">": returncode > val,
                "<": returncode < val,
                ">=": returncode >= val,
                "<=": returncode <= val,
            }
            return comparisons.get(op, False)

        if expected.startswith("no "):
            pattern = expected[3:]
            return pattern not in combined

        if expected.startswith("contains "):
            pattern = expected[9:]
            return pattern in combined

        if re.match(r"^[a-zA-Z_ ]+$", expected):
            return expected in combined

        return returncode == 0
