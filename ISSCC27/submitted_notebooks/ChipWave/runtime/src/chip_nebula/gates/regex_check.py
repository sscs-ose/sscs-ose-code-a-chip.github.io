import re
from pathlib import Path

from chip_nebula.models.task_manifest import ExitCriterion
from chip_nebula.models.gate_report import GateReport

_NL = chr(10)


class RegexCheckGate:

    @classmethod
    def check(cls, criterion: ExitCriterion, workspace_path: Path) -> GateReport:
        pattern = criterion.pattern or ""
        if not pattern:
            return GateReport(
                level=criterion.level,
                check_type=criterion.type,
                passed=False,
                evidence="regex_check missing 'pattern' field",
                suggestion="Provide a regex pattern to search for.",
            )

        target_paths = []
        if criterion.source:
            target_paths.append(workspace_path / criterion.source)
        for p in criterion.paths:
            target_paths.extend(workspace_path.glob(p))

        if not target_paths:
            return GateReport(
                level=criterion.level,
                check_type=criterion.type,
                passed=False,
                evidence="No target file(s) specified for regex_check",
                suggestion="Use 'source' or 'paths' to specify the file(s) to scan.",
            )

        compiled = re.compile(pattern)
        matched_files: list[str] = []
        all_text_parts: list[str] = []

        for target in target_paths:
            if not target.exists():
                continue
            try:
                text = target.read_text(encoding="utf-8")
            except Exception as exc:
                return GateReport(
                    level=criterion.level,
                    check_type=criterion.type,
                    passed=False,
                    evidence=f"Could not read {target.relative_to(workspace_path)}: {exc}",
                    suggestion="Verify the file is readable text.",
                )

            all_text_parts.append(text)
            if compiled.search(text):
                matched_files.append(str(target.relative_to(workspace_path)))

        full_text = _NL.join(all_text_parts)
        found = bool(matched_files)
        must_not_match = criterion.must_not_match

        passed = (not found) if must_not_match else found

        evidence: str
        suggestion = ""
        if found:
            evidence = (
                f"Pattern '{pattern}' found in: {', '.join(matched_files)}"
            )
        else:
            evidence = f"Pattern '{pattern}' not found in scanned file(s)."

        if not passed:
            if must_not_match:
                suggestion = f"Forbidden pattern matched; remove the matched content from {', '.join(matched_files)}."
            else:
                suggestion = f"Required pattern not found; ensure the file contains a match for '{pattern}'."

            # Inject an Error-Class marker so the interpreter can route the
            # failure to the configured target stage (e.g. blocking_defect ->
            # rtl_coding) instead of treating it as a generic unknown failure.
            error_class = criterion.error_class or "unknown"
            evidence += _NL + f"Error-Class: {error_class}" + _NL
            evidence += (
                f"Error-Class-Reason: regex_check failed for pattern '{pattern}'"
            )

        return GateReport(
            level=criterion.level,
            check_type=criterion.type,
            passed=passed,
            evidence=evidence,
            suggestion=suggestion,
        )
