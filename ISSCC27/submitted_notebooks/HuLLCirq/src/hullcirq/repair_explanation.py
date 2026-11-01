"""Display-only explanation of saved S05 repair evidence; never edits prompts.

Keep this projection outside frozen guidance and model messages. A parser that
stops on one error cannot establish that other errors have been corrected.
"""
from __future__ import annotations

import copy
import re

from .repair_guidance import actionable_diagnostics
from .verification import content_hash


def build_repair_explanation(guidance, run, job, jobs=(), runs=()):
    rtl = job.get("rtl") or ""
    lines = rtl.splitlines()
    status = copy.deepcopy(guidance.get("repeat_status") or {})
    outcome = status.get("outcome", "not_comparable")
    previous = next((value for value in jobs if value.get("id") == status.get("base_candidate_id")), None)
    baseline = next((value for value in runs if value.get("id") == status.get("base_run_id")), None)
    comparable = outcome in {"unchanged", "same_diagnostic", "new_diagnostic"} and previous is not None and baseline is not None
    comparison = {**status, "outcome": outcome,
                  "current_candidate_id": job["id"], "current_run_id": run["id"],
                  "current_rtl_sha256": content_hash(rtl),
                  "current_rtl_url": "/api/generation/jobs/" + job["id"],
                  "previous_candidate_id": previous["id"] if previous else None,
                  "previous_run_id": baseline["id"] if baseline else None,
                  "previous_rtl_sha256": content_hash(previous.get("rtl") or "") if previous else None,
                  "previous_rtl_url": "/api/generation/jobs/" + previous["id"] if previous else None,
                  "rtl_identical": content_hash(previous.get("rtl") or "") == content_hash(rtl) if comparable else None,
                  "baseline_available": comparable}
    comparison["explanation"] = {
        "unchanged": "The previous repair returned identical RTL. Requested source changes were not applied; the reported error remains.",
        "same_diagnostic": "RTL changed, but the same source-anchored diagnostics remain. This does not mean the entire RTL is identical.",
        "new_diagnostic": "RTL and reported diagnostics changed. Inspect the current errors; a missing earlier diagnostic is not proof of a fix.",
        "no_baseline": "No comparable earlier synthesis attempt is recorded.",
        "not_comparable": "The saved attempts cannot be compared under the same source and tool conditions.",
        "passed": "Synthesis passed; circuit behavior still requires S06 verification.",
    }.get(outcome, "No comparison is available.")
    diagnostics = guidance.get("evidence", {}).get("actionable_diagnostics", [])
    issues = []
    for diagnostic in diagnostics:
        number = diagnostic.get("line")
        valid = type(number) is int and 0 < number <= len(lines)
        def matches(change):
            if valid and any(location.get("line") == number for location in change.get("locations", [])):
                return True
            # Final CHECK can name a driver without a candidate.v location.
            # Associate only the qualified ownership rule and actual writes to
            # that exact signal; never attach unrelated line-less advice.
            target = (diagnostic.get("target") or "").split(".")[-1].lstrip("\\")
            if (change.get("rule_id") != "conflicting_driver_ownership"
                    or not re.search(r"conflicting\s+drivers", diagnostic.get("raw_message", ""), re.I)
                    or not re.fullmatch(r"[A-Za-z_$][\w$]*", target)):
                return False
            return any(type(location.get("line")) is int and 0 < location["line"] <= len(lines)
                       and re.match(r"\s*(?:assign\s+)?" + re.escape(target) + r"\s*(?:<=|=(?!=))", lines[location["line"] - 1])
                       for location in change.get("locations", []))
        changes = [change for change in guidance.get("changes", []) if matches(change)]
        fields = {key: list(dict.fromkeys(value for change in changes for value in change.get(key, []) if isinstance(value, str)))
                  for key in ("facts", "actions", "preserve", "assumptions")}
        causes = [change["cause"] for change in changes if isinstance(change.get("cause"), str)]
        explanation = " ".join(fields["facts"])
        if causes:
            explanation += (" " if explanation else "") + "Model-proposed cause (not validated): " + " ".join(causes)
        issues.append({"signature": diagnostic.get("signature"), "diagnostic": copy.deepcopy(diagnostic),
                       "code_context": [{"line": index + 1, "text": lines[index], "is_target": index + 1 == number}
                                        for index in range(max(0, number - 3), min(len(lines), number + 2))] if valid else [],
                       "explanation": explanation or "No source-backed cause has been qualified for this diagnostic. Inspect the saved source or preview model-assisted guidance.",
                       "expected_result": [change["expected_result"] for change in changes if isinstance(change.get("expected_result"), str)],
                       "actions": fields["actions"], "preserve": fields["preserve"], "assumptions": fields["assumptions"],
                       "confidence": "confirmed" if changes and all(change.get("confidence") == "confirmed" for change in changes) else "hypothesis" if changes else "unknown",
                       "related_locations": [{**copy.deepcopy(location), "source": lines[location["line"] - 1] if type(location.get("line")) is int and 0 < location["line"] <= len(lines) else location.get("source", "")}
                                             for change in changes for location in change.get("locations", [])]})
    old_diagnostics = actionable_diagnostics(baseline, previous.get("rtl") or "") if comparable else []
    current_signatures = {item.get("signature") for item in diagnostics}
    old_signatures = {item.get("signature") for item in old_diagnostics}
    diagnostic_comparison = {
        "baseline_run_id": baseline["id"] if comparable else None,
        "remaining": [copy.deepcopy(item) for item in diagnostics if item.get("signature") in old_signatures],
        "newly_reported": [copy.deepcopy(item) for item in diagnostics if comparable and item.get("signature") not in old_signatures],
        "not_reported": [copy.deepcopy(item) for item in old_diagnostics if item.get("signature") not in current_signatures],
        "limits": "Not reported in the latest run does not mean resolved. The tool may stop at the first error; comparison uses lexical source anchors, not functional equivalence.",
    }
    attempt = next((item for item in guidance.get("recent_attempts", []) if item.get("job_id") == job["id"]), None)
    return {"version": "s05-repair-explanation-v1", "source": copy.deepcopy(guidance["source"]),
            "comparison": comparison, "issues": issues, "diagnostic_comparison": diagnostic_comparison,
            "previous_instruction": {"text": attempt.get("instruction", ""), "job_id": attempt.get("job_id"),
                                     "base_job_id": attempt.get("base_job_id"), "run_id": attempt.get("run_id"),
                                     "diff": attempt.get("diff", "")} if attempt else None,
            "limits": "Saved S05 evidence and proposed edits only. No new model request, synthesis or S06 behavioral verification was performed by showing this explanation."}
